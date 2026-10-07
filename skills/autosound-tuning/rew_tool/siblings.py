"""One module object per file of the method, loaded by its path (skill #137; audit T-19, T-27).

The front ends load the method's modules by FILE PATH (TCC's `vendor_loader`), and until W-8 the modules loaded each
other three ways: a bare `import` that needs `rew_tool/` on `sys.path`, private loaders that ran a FRESH copy on every
call, and `sys.path` edits at import. One file then lived as several module objects -- two `NamingError` classes,
several `rew_api` modules each with its own `BASE_URL`.

`load(rel)` is the one way in:
  * a module already in `sys.modules` whose file is this one (by real path) is ADOPTED, whatever its name -- a bare
    `import naming`, TCC's `autosound_tcc._vendor.naming`, an earlier `load`;
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
    """The module already in `sys.modules` for `path` (by real path), or None."""
    want = _real(path)
    module = _BY_PATH.get(want)
    if module is not None and sys.modules.get(module.__name__) is module:
        return module
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        if file and _real(file) == want:
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
    for label, fn in (("one object", one_object), ("adopts a loaded copy", adopts), ("fails clean", fails_clean),
                      ("cycle", cycle), ("threads", threads)):
        check(label, fn)
    assert not failures, "\n".join(failures)
    print("siblings selftest OK -- one object per file, adoption, clean failure, cycles, threads")


if __name__ == "__main__":
    _selftest()
