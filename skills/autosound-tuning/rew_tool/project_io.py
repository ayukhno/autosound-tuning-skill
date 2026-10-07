"""How the method writes, and reads, the files it owns (skill #135, #136; audit T-8, T-17, K-2).

WRITES go through `atomic_write_text` / `atomic_write_json`: a temp file with a name no other writer uses, opened
exclusively, written, flushed and fsynced, then moved over the target in one `os.replace`. A reader sees the old file
or the new one, never half of either; two writers never share a temp file. A Windows `PermissionError` on the move (an
editor, an antivirus scan or TCC holding the target open) is retried for under a second.

Stdlib only. Loaded by path like every sibling: `_siblings().load("project_io.py")`.

    python3 project_io.py --selftest
"""
import io
import json
import os
import secrets
import sys
import time


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.realpath(__file__))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


#: Waits before the next `os.replace` attempt on Windows. A holder that outlives them is a real conflict.
_REPLACE_RETRIES_S = (0.05, 0.1, 0.2, 0.4)


def _temp_name(path):
    # Ends in `.tmp`, never `.json`/`.jsonl`: `contract.project_text_files` lists those, and a leftover must not be
    # read as a project file. The pid and the token make it unique per writer.
    return f"{path}.{os.getpid()}-{secrets.token_hex(4)}.tmp"


def _replace(src, dst):
    for delay in _REPLACE_RETRIES_S + (None,):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if delay is None or os.name != "nt":
                raise
            time.sleep(delay)


def atomic_write_text(path, text, *, newline=None, mode=None, makedirs=False):
    """Write `text` to `path` so that no reader ever sees a half-written file.

    `newline` is `open()`'s: None writes the platform's line ending -- what `open(path, "w")` did at every site this
    replaces -- while "" and "\\n" keep the text's own. `mode` (POSIX only) is set on the temp BEFORE the move, so the
    target never exists with looser permissions.
    """
    if makedirs:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = _temp_name(path)
    # O_BINARY (Windows; 0 elsewhere): a descriptor from `os.open` is otherwise in the C runtime's text mode, which
    # turns each "\n" the text layer writes into "\r\n" once more -- "\r\r\n", and "\r\n" where `newline` asked for
    # the text's own. `open(path, "w")` opens binary underneath too; so does `tempfile.mkstemp`.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o666)
    try:
        with io.open(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None and os.name != "nt":
            os.chmod(tmp, mode)
        _replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, data, *, indent=2, sort_keys=False, ensure_ascii=False, trailing_newline=False,
                      newline=None, mode=None, makedirs=False):
    """`json.dumps(data, ...)` through `atomic_write_text` -- the same text `json.dump` wrote at each old site."""
    text = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    if trailing_newline:
        text += "\n"
    atomic_write_text(path, text, newline=newline, mode=mode, makedirs=makedirs)


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def _scratch():
    import tempfile
    return tempfile.mkdtemp(prefix="autosound_project_io_")


def _drop(folder):
    import shutil
    shutil.rmtree(folder, ignore_errors=True)


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _two_writers_worker(path, signals, me, rounds):
    """One writer of `_check_two_writers_one_reader`. At the top level, so that `spawn` finds it by name. It says it
    is up (`ready-<me>`) and waits for the reader's `go`: both writers start together, and the reader is reading."""
    with open(os.path.join(signals, f"ready-{me}"), "w", encoding="utf-8"):
        pass
    deadline = time.monotonic() + 60
    while not os.path.exists(os.path.join(signals, "go")):
        if time.monotonic() > deadline:
            raise SystemExit("the reader never said go")
        time.sleep(0.002)
    for i in range(rounds):
        atomic_write_json(path, {"n": i, "pad": "x" * 4000})


def _check_text_and_json():
    """The bytes each old site wrote: `json.dump(...)` (and a "\\n") through `open(path, "w")`, so the platform's line
    ending; `newline=""` and "\\n" keep the text's own, byte for byte, on Windows too."""
    d = _scratch()
    try:
        data = {"b": [1, 2.5, None, True], "a": {"ключ": "→ 45°"}, "z": "two\nlines"}
        path, ref = os.path.join(d, "x.json"), os.path.join(d, "ref.json")
        for kw, final in ((dict(indent=2, sort_keys=True, ensure_ascii=False), False),     # project.json, the ledger
                          (dict(indent=2, ensure_ascii=False), True),                      # process-state.json
                          (dict(indent=1, sort_keys=True, ensure_ascii=True), False),      # seals.json
                          (dict(indent=None, ensure_ascii=True), False)):                  # the DPAPI key store
            atomic_write_json(path, data, trailing_newline=final, **kw)
            with open(ref, "w", encoding="utf-8") as f:                                   # how the old sites wrote
                json.dump(data, f, **kw)
                if final:
                    f.write("\n")
            assert _read_bytes(path) == _read_bytes(ref), (kw, final, _read_bytes(path)[:120])
        text = "v_003\nline two\r\nend\n"
        atomic_write_text(path, text)
        with open(ref, "w", encoding="utf-8") as f:
            f.write(text)
        assert _read_bytes(path) == _read_bytes(ref), ("newline=None", _read_bytes(path))
        for newline in ("", "\n"):
            atomic_write_text(path, text, newline=newline)
            assert _read_bytes(path) == text.encode("utf-8"), (newline, _read_bytes(path))
        deep = os.path.join(d, "a", "b", "c.json")
        atomic_write_json(deep, {"v": 1}, makedirs=True)
        assert json.loads(_read_bytes(deep).decode("utf-8")) == {"v": 1}, _read_bytes(deep)
        assert sorted(os.listdir(d)) == ["a", "ref.json", "x.json"], os.listdir(d)       # no temp left behind
    finally:
        _drop(d)


def _check_foreign_tmp():
    """A `<path>.tmp` beside the target -- another writer's, or the temp this method used before #135 -- survives a
    write byte for byte, and no two temp names are the same."""
    d = _scratch()
    try:
        path = os.path.join(d, "process-state.json")
        foreign = path + ".tmp"
        with open(foreign, "wb") as f:
            f.write(b"another writer's half")
        atomic_write_json(path, {"v": 1})
        atomic_write_text(path, "{}\n")
        assert os.path.isfile(foreign), "the writer moved another writer's temp file over the target"
        assert _read_bytes(foreign) == b"another writer's half", _read_bytes(foreign)
        assert sorted(os.listdir(d)) == ["process-state.json", "process-state.json.tmp"], os.listdir(d)
        names = {_temp_name(path) for _ in range(50)}
        assert len(names) == 50, "a temp name came twice"
        assert all(n.endswith(".tmp") and f".{os.getpid()}-" in n for n in names), sorted(names)[:3]
    finally:
        _drop(d)


def _check_replace_fails_clean():
    """A crash between the temp and the move leaves the old file whole and no temp behind; so does a write that
    fails half way."""
    d = _scratch()
    try:
        path = os.path.join(d, "x.json")
        atomic_write_json(path, {"v": 1})
        before = _read_bytes(path)
        real = os.replace

        def broken(src, dst):
            raise OSError("disk pulled")
        os.replace = broken                      # the writer's own move fails: a fault injected through the writer
        try:
            try:
                atomic_write_json(path, {"v": 2})
            except OSError:
                pass
            else:
                raise AssertionError("a failed move was reported as written")
        finally:
            os.replace = real
        assert _read_bytes(path) == before
        assert [f for f in os.listdir(d) if f.endswith(".tmp")] == [], os.listdir(d)
        try:
            atomic_write_text(path, "half of it " + chr(0xD800))   # a lone surrogate: UTF-8 cannot carry it
        except UnicodeEncodeError:
            pass
        else:
            raise AssertionError("a failed write was reported as written")
        assert _read_bytes(path) == before
        assert os.listdir(d) == ["x.json"], os.listdir(d)
    finally:
        _drop(d)


def _check_replace_retry():
    """A `PermissionError` on the move is retried on Windows, where a reader, an editor or an antivirus scan holding
    the target refuses it; a holder that outlives the retries is raised, the old file whole and no temp behind.
    Elsewhere it is raised at once: there an open file never refuses a replace."""
    global _REPLACE_RETRIES_S
    d = _scratch()
    real_replace, real_name, real_waits = os.replace, os.name, _REPLACE_RETRIES_S
    tries = len(real_waits) + 1
    calls = []

    def held(times):
        def replace(src, dst):
            calls.append(dst)
            if len(calls) <= times:
                raise PermissionError(13, "held open by another process", dst)
            real_replace(src, dst)
        return replace
    try:
        path = os.path.join(d, "x.json")
        _REPLACE_RETRIES_S = (0.001,) * len(real_waits)          # as many tries, without the waits
        for platform, refusals, lands, attempts in (("nt", 2, True, 3), ("nt", tries, False, tries),
                                                    ("posix", 1, False, 1)):
            atomic_write_json(path, {"v": 1})
            before = _read_bytes(path)
            del calls[:]
            os.name, os.replace = platform, held(refusals)
            try:
                atomic_write_json(path, {"v": 2})
                landed = True
            except PermissionError:
                landed = False
            finally:
                os.name, os.replace = real_name, real_replace
            assert (landed, len(calls)) == (lands, attempts), (platform, refusals, landed, len(calls))
            if lands:
                assert json.loads(_read_bytes(path).decode("utf-8")) == {"v": 2}
            else:
                assert _read_bytes(path) == before, (platform, refusals)
            assert os.listdir(d) == ["x.json"], (platform, os.listdir(d))
    finally:
        os.name, os.replace, _REPLACE_RETRIES_S = real_name, real_replace, real_waits
        _drop(d)


def _check_private_mode():
    """`mode` is set on the temp before the move: on POSIX the file is 0600 from the moment it has its name. Without a
    mode it gets what `open(path, "w")` gave -- the umask's default, never 0600 by accident (a `mkstemp` temp would
    make every `project.json` private)."""
    if os.name == "nt":
        return
    import stat
    d = _scratch()
    try:
        private, plain = os.path.join(d, "critic-env"), os.path.join(d, "project.json")
        atomic_write_text(private, "export KEY=1\n", mode=0o600)
        assert stat.S_IMODE(os.stat(private).st_mode) == 0o600, oct(os.stat(private).st_mode)
        atomic_write_text(plain, "{}")
        umask = os.umask(0)
        os.umask(umask)
        assert stat.S_IMODE(os.stat(plain).st_mode) == 0o666 & ~umask, (oct(os.stat(plain).st_mode), oct(umask))
    finally:
        _drop(d)


def _check_two_writers_one_reader():
    """Audit T-8's test: two processes write one file 100 times each while a third reads it: every read parses.

    The processes are spawned, never forked. On Windows the reader pauses between reads: there a reader holding the
    file refuses the writers' move, and a refusal the retries outlast is the conflict `_replace` raises, not a torn
    read -- and an open refused while the name is being replaced is counted as busy, not as a failure."""
    import multiprocessing
    ctx = multiprocessing.get_context("spawn")
    d, signals = _scratch(), _scratch()
    try:
        path, rounds = os.path.join(d, "process-state.json"), 100
        atomic_write_json(path, {"n": -1, "pad": ""})
        writers = [ctx.Process(target=_two_writers_worker, args=(path, signals, me, rounds)) for me in (0, 1)]
        for w in writers:
            w.start()
        tries, reads, failures = 0, 0, []
        try:
            deadline = time.monotonic() + 60
            while not all(os.path.exists(os.path.join(signals, f"ready-{me}")) for me in (0, 1)):
                assert time.monotonic() < deadline and all(w.is_alive() for w in writers), "a writer never started"
                time.sleep(0.002)
            with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
                pass
            while any(w.is_alive() for w in writers):
                tries += 1
                try:
                    with open(path, encoding="utf-8") as f:
                        doc = json.load(f)
                    if isinstance(doc, dict) and isinstance(doc.get("n"), int):
                        reads += 1
                    else:
                        failures.append(f"read {doc!r:.60}")
                except PermissionError as exc:
                    if os.name != "nt":          # Windows: the name is being replaced -- busy, not a torn read
                        failures.append(f"PermissionError: {exc}")
                except (OSError, ValueError) as exc:
                    failures.append(f"{type(exc).__name__}: {exc}")
                if os.name == "nt":
                    time.sleep(0.01)
        finally:
            for w in writers:
                w.join(120)
                if w.is_alive():
                    w.terminate()
        assert [w.exitcode for w in writers] == [0, 0], f"a writer failed: exit codes {[w.exitcode for w in writers]}"
        assert not failures, f"{len(failures)} of {tries} reads failed: {failures[:3]}"
        with open(path, encoding="utf-8") as f:
            assert json.load(f)["n"] == rounds - 1
        assert os.listdir(d) == ["process-state.json"], os.listdir(d)
        return reads
    finally:
        _drop(d)
        _drop(signals)


def _selftest():
    failures, seen = [], {}
    for check in (_check_text_and_json, _check_foreign_tmp, _check_replace_fails_clean, _check_replace_retry,
                  _check_private_mode, _check_two_writers_one_reader):
        try:
            seen[check.__name__] = check()
        except Exception as exc:  # noqa: BLE001 -- each check is reported by name; one failing must not hide the rest
            failures.append(f"{check.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        print("\n".join(failures))
        print(f"project_io selftest FAILED -- {len(failures)} check(s)")
        return 1
    reads = seen["_check_two_writers_one_reader"]
    print(f"project_io selftest OK -- text and JSON land with the old sites' bytes; a foreign <file>.tmp is left alone "
          f"and no temp name repeats; a failed move or write leaves the old file whole and no temp behind; a held move "
          f"is retried on Windows only; a private mode is set before the move; two writers x 100 and a reader: "
          f"{reads} reads, every one whole")
    return 0


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: project_io.py --selftest  (a library: the method's writers call it)", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
