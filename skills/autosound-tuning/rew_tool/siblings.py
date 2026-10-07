"""One module object per file of the method, loaded by its path (skill #137; audit T-19, T-27).

The front ends load the method's modules by FILE PATH (TCC's `vendor_loader`), and until W-8 the modules loaded each
other three ways: a bare `import` that needs `rew_tool/` on `sys.path`, private loaders that ran a FRESH copy on every
call, and `sys.path` edits at import. One file then lived as several module objects -- two `NamingError` classes,
several `rew_api` modules each with its own `BASE_URL`.

`load(rel)` is the one way in:
  * a module already in `sys.modules` whose file is this one is ADOPTED, whatever its module name -- a bare
    `import naming`, TCC's `autosound_tcc._vendor.naming`, an earlier `load`. Its file NAME must match first, then
    its real path: a module whose `__file__` is a symlink under another name is not adopted;
  * otherwise the file runs once, under a name tied to this copy of the method, registered in `sys.modules` BEFORE it
    runs (a cycle finds it) and removed again if it fails;
  * one re-entrant lock around both, so two threads never run one file twice.

A missing file, or one that fails, RAISES. A caller that reads "cannot load" as "cannot tell" says so at its own call
site, where the choice can be seen. Consumers reach this file through `_siblings()`, a fixed bootstrap copied into each
of them (scripts/contract-guard.py holds the copies identical): it cannot be imported, since importing is the problem.
"""
import hashlib
import importlib.util
import os
import sys
import threading

#: `rew_tool/` of THIS copy of the method, real path.
HERE = os.path.dirname(os.path.realpath(__file__))
#: Ties module names to this copy: two copies of the method in one process never share a name.
COPY = hashlib.sha1(HERE.encode("utf-8")).hexdigest()[:8]
_LOCK = threading.RLock()
_BY_PATH = {}


def _real(path):
    return os.path.normcase(os.path.realpath(path))


def path_of(rel):
    """`rew_tool/<rel>` of this copy; `rel` is written with `/` ("state/process.py")."""
    return os.path.join(HERE, *rel.split("/"))


def module_name(rel):
    """The name `load(rel)` registers: `_autosound_<copy>_<rel without .py, "__" for "/">`."""
    stem = rel[:-3] if rel.endswith(".py") else rel
    return f"_autosound_{COPY}_" + stem.replace("/", "__").replace("-", "_")


def find_loaded(path):
    """The module already in `sys.modules` for `path`, or None: its file NAME must match first, then its real path
    (a module whose `__file__` is a symlink under another name is not adopted)."""
    want = _real(path)
    module = _BY_PATH.get(want)
    if module is not None and sys.modules.get(module.__name__) is module:
        return module
    name = os.path.basename(want)
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        # The file's name first: a miss would otherwise take the real path of every module loaded (1-2k under TCC).
        if file and os.path.normcase(os.path.basename(file)) == name and _real(file) == want:
            _BY_PATH[want] = module
            return module
    return None


def load(rel):
    """`rew_tool/<rel>` as ONE module object per process. Raises if the file is missing or fails."""
    path = path_of(rel)
    with _LOCK:
        module = find_loaded(path)
        if module is not None:
            return module
        if not os.path.isfile(path):
            raise ImportError(f"siblings: {rel} is not in {HERE}")
        name = module_name(rel)
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"siblings: {path} cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        _BY_PATH[_real(path)] = module
        return module


def _selftest():
    import shutil, tempfile, textwrap
    root = tempfile.mkdtemp()
    shutil.copy(os.path.realpath(__file__), os.path.join(root, "siblings.py"))
    def put(name, body):
        with open(os.path.join(root, name), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(body))
    put("a.py", "X = object()\n")
    put("boom.py", "raise RuntimeError('boom at import')\n")
    put("cyc1.py", "import siblings_probe\nB = siblings_probe.load('cyc2.py')\n")
    put("cyc2.py", "import siblings_probe\nA = siblings_probe.load('cyc1.py')\n")
    put("slow.py", "import time, os\ntime.sleep(0.2)\nopen(os.path.join(os.path.dirname(__file__), 'ran.txt'), 'a').write('x')\n")
    put("fa.py", "import siblings_probe\nB = siblings_probe.load('fb.py')\nraise RuntimeError('fa fails after fb took it')\n")
    put("fb.py", "import siblings_probe\nA = siblings_probe.load('fa.py')\n")
    put("gated.py", "import sys\ngate = sys.modules['siblings_load_gate']\ngate.entered.set()\ngate.release.wait(60)\n"
                    "DONE = True\n")
    put("linked.py", "N = object()\n")
    spec = importlib.util.spec_from_file_location("siblings_probe", os.path.join(root, "siblings.py"))
    sib = importlib.util.module_from_spec(spec); sys.modules["siblings_probe"] = sib; spec.loader.exec_module(sib)
    failures = []
    def check(label, fn):
        try:
            fn()
        except AssertionError as exc:
            failures.append(f"{label}: {exc}")
    def one_object():
        a1, a2 = sib.load("a.py"), sib.load("a.py")
        assert a1 is a2 and sys.modules[sib.module_name("a.py")] is a1
    def adopts():
        path = os.path.join(root, "a.py")
        other_spec = importlib.util.spec_from_file_location("someone_elses_name", path)
        # a copy registered under another name first is ADOPTED, not executed again
        sys.modules.pop(sib.module_name("a.py"), None); sib._BY_PATH.clear()
        other = importlib.util.module_from_spec(other_spec); sys.modules["someone_elses_name"] = other
        other_spec.loader.exec_module(other)
        assert sib.load("a.py") is other
    def same_name_elsewhere_is_not_adopted():
        # A front end holds files of the method's NAMES in folders of its own (TCC: core/listening.py,
        # core/eq_export.py, core/protective.py). One of the same file name from another folder is not this file:
        # loaded first, under a name of its own, it is never adopted for it.
        other_dir = tempfile.mkdtemp()
        want = os.path.normcase(os.path.realpath(os.path.join(root, "a.py")))
        earlier = {k: m for k, m in list(sys.modules.items())
                   if getattr(m, "__file__", None) and os.path.normcase(os.path.realpath(m.__file__)) == want}
        try:
            with open(os.path.join(other_dir, "a.py"), "w", encoding="utf-8") as f:
                f.write("X = 'not the method'\n")
            for k in earlier:                       # nothing of the method's a.py left to find first
                del sys.modules[k]
            sib._BY_PATH.clear()
            spec_ = importlib.util.spec_from_file_location("front_end_core_a", os.path.join(other_dir, "a.py"))
            foreign = importlib.util.module_from_spec(spec_)
            sys.modules[spec_.name] = foreign
            spec_.loader.exec_module(foreign)
            got = sib.load("a.py")
            assert got is not foreign, "a.py from another folder was adopted for the method's a.py"
            assert os.path.normcase(os.path.realpath(got.__file__)) == want, got.__file__
        finally:
            sys.modules.pop("front_end_core_a", None)
            sys.modules.update(earlier)
            sib._BY_PATH.clear()
            shutil.rmtree(other_dir, ignore_errors=True)
    no_symlinks = []
    def adopts_through_a_linked_folder():
        # An installed method is a link into the clone, and a front end loads it through that link: a module whose
        # `__file__` runs through a linked FOLDER is this file, and is adopted. Pinned here, not by macOS's /var ->
        # /private/var alone: where the temporary folder is a real path (a Linux CI), nothing else tells the real
        # path's comparison from a plain one.
        links = tempfile.mkdtemp()
        link = os.path.join(links, "method")
        try:
            os.symlink(root, link)
        except (OSError, NotImplementedError):
            shutil.rmtree(links, ignore_errors=True)
            no_symlinks.append(True)                # Windows without the privilege: said above the last line
            return
        try:
            spec_ = importlib.util.spec_from_file_location("front_end_vendor_linked", os.path.join(link, "linked.py"))
            linked = importlib.util.module_from_spec(spec_)
            sys.modules[spec_.name] = linked
            spec_.loader.exec_module(linked)
            sib._BY_PATH.clear()
            assert sib.load("linked.py") is linked, "a copy loaded through a linked folder was run a second time"
        finally:
            sys.modules.pop("front_end_vendor_linked", None)
            sys.modules.pop(sib.module_name("linked.py"), None)
            (os.rmdir if os.name == "nt" else os.unlink)(link)     # the link only, never what it points at
            shutil.rmtree(links, ignore_errors=True)
    def fails_clean():
        try:
            sib.load("boom.py")
        except RuntimeError:
            assert sib.module_name("boom.py") not in sys.modules
        else:
            raise AssertionError("a module that raises at import was returned")
        try:
            sib.load("missing.py")
        except ImportError:
            pass
        else:
            raise AssertionError("a missing file did not raise")
        # fa.py fails AFTER a cycle took it (fb.py loads fa.py while fa.py runs), so the cache still holds the
        # half-built fa: a second load must run fa.py again and fail again, never hand that copy out.
        for attempt in (1, 2):
            try:
                sib.load("fa.py")
            except RuntimeError:
                assert sib.module_name("fa.py") not in sys.modules, attempt
            else:
                raise AssertionError(f"load #{attempt} returned fa.py, which fails at import (a half-built copy)")
    def a_miss_reads_only_that_name():
        # A miss in the cache scans sys.modules -- 1-2k modules under TCC, often on its GUI thread: only a file of
        # the wanted name may cost a realpath.
        read = []
        real = sib._real
        sib._real = lambda p: read.append(p) or real(p)
        try:
            sib._BY_PATH.clear()
            sib.find_loaded(os.path.join(root, "a.py"))
        finally:
            sib._real = real
        names = sorted({os.path.basename(p) for p in read})
        assert read and names == ["a.py"], names[:8]
    def bootstrap_publishes_after_run():
        # Every `_siblings()` copy in the method, against a throwaway siblings.py whose FIRST run blocks: a call
        # racing it gets a module that has run, never the half-run one, and both calls end with the one published.
        # A siblings.py that fails at import leaves nothing behind.
        import ast, threading, types
        fake = tempfile.mkdtemp()
        os.makedirs(os.path.join(fake, "rew_tool"))
        with open(os.path.join(fake, "rew_tool", "siblings.py"), "w", encoding="utf-8") as f:
            f.write("import sys\ngate = sys.modules['siblings_race_gate']\n"
                    "if gate.fail:\n    raise RuntimeError('siblings.py fails at import')\n"
                    "gate.runs += 1\nif gate.runs == 1:\n    gate.started.set()\n    gate.release.wait(60)\n"
                    "def load(rel):\n    return rel\n")
        here = os.path.realpath(os.path.join(fake, "rew_tool"))
        name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
        skill = os.path.dirname(HERE)
        copies = []
        for top in (HERE, os.path.join(skill, "scripts")):
            for dirpath, _dirs, files in os.walk(top):
                for fn in sorted(f for f in files if f.endswith(".py")):
                    with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                        text = f.read()
                    if "def _siblings(" not in text:
                        continue
                    for node in ast.parse(text).body:
                        if isinstance(node, ast.FunctionDef) and node.name == "_siblings":
                            rel = os.path.relpath(os.path.join(dirpath, fn), skill)
                            copies.append((rel, ast.get_source_segment(text, node)))
        assert copies, "no _siblings() bootstrap in the method to test"
        gate = types.ModuleType("siblings_race_gate")
        sys.modules[gate.__name__] = gate
        try:
            for rel, src in copies:
                ns = {"os": os, "sys": sys, "__file__": os.path.join(fake, rel)}
                exec(compile(src, rel, "exec"), ns)
                boot = ns["_siblings"]
                gate.fail, gate.runs = True, 0
                try:
                    boot()
                except RuntimeError:
                    assert name not in sys.modules, f"{rel}: a siblings.py that failed was left in sys.modules"
                else:
                    raise AssertionError(f"{rel}: a siblings.py that failed at import was returned")
                gate.fail, gate.started, gate.release = False, threading.Event(), threading.Event()
                got = {}
                first = threading.Thread(target=lambda: got.update(first=boot()))
                first.start()
                try:
                    assert gate.started.wait(60), f"{rel}: the first call never ran siblings.py"
                    second = boot()
                    assert hasattr(second, "load"), f"{rel}: a racing call got siblings.py before it had run"
                finally:
                    gate.release.set()
                    first.join(60)
                    published = sys.modules.pop(name, None)
                assert got.get("first") is second is published, f"{rel}: the racing calls ended with two objects"
        finally:
            sys.modules.pop(gate.__name__, None)
            shutil.rmtree(fake, ignore_errors=True)
    def cycle():
        c1 = sib.load("cyc1.py")
        assert c1.B.A is c1
    def threads():
        import threading
        ts = [threading.Thread(target=sib.load, args=("slow.py",)) for _ in range(8)]
        for t in ts: t.start()
        for t in ts: t.join()
        with open(os.path.join(root, "ran.txt")) as f:
            assert f.read() == "x", "slow.py ran more than once"
    def waits_for_a_load_in_progress():
        # A thread asking for a file another thread is still running waits until it has run -- never handed the
        # half-run module. Watched, not timed: `progress` is set when the asking thread has to wait for the lock, or
        # when it comes back without having waited (the half-run module, which the last assert then refuses).
        import threading, types
        gate = types.ModuleType("siblings_load_gate")
        gate.entered, gate.release, progress = threading.Event(), threading.Event(), threading.Event()
        lock, got = sib._LOCK, {}
        class Watched:
            def __enter__(self):
                if not lock.acquire(blocking=False):
                    progress.set()
                    lock.acquire()
            def __exit__(self, *exc):
                lock.release()
        def ask():
            got["complete"] = hasattr(sib.load("gated.py"), "DONE")
            progress.set()
        first = threading.Thread(target=sib.load, args=("gated.py",))
        second = threading.Thread(target=ask)
        sys.modules[gate.__name__] = gate
        sib._LOCK = Watched()
        try:
            first.start()
            assert gate.entered.wait(60), "gated.py never ran"
            second.start()
            assert progress.wait(60), "the asking thread neither waited nor came back"
        finally:
            gate.release.set()
            first.join(60)
            second.join(60)
            sib._LOCK = lock
            sys.modules.pop(gate.__name__, None)
        assert got.get("complete") is True, "a thread was handed gated.py while another was still running it"
    try:
        for label, fn in (("one object", one_object), ("adopts a loaded copy", adopts),
                          ("a file of the same name in another folder is not adopted",
                           same_name_elsewhere_is_not_adopted),
                          ("a copy loaded through a linked folder is adopted", adopts_through_a_linked_folder),
                          ("fails clean", fails_clean),
                          ("a miss reads only that name", a_miss_reads_only_that_name),
                          ("the bootstrap publishes after it has run", bootstrap_publishes_after_run),
                          ("cycle", cycle), ("threads", threads),
                          ("a load in progress is waited for", waits_for_a_load_in_progress)):
            check(label, fn)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    assert not failures, "\n".join(failures)
    if no_symlinks:
        print("siblings: this system refuses symlinks -- the linked-folder adoption was not checked here")
    print("siblings selftest OK -- one object per file, adoption (a copy through a linked folder too, never a file of "
          "the same name from another folder), clean failure, cycles, threads, a load in progress waited for; a miss "
          "reads only that name; every _siblings() copy publishes siblings.py only after it has run")


if __name__ == "__main__":
    _selftest()
