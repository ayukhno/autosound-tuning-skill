"""How the method writes, and reads, the files it owns (skill #135, #136; audit T-8, T-17, K-2).

WRITES go through `atomic_write_text` / `atomic_write_json` / `atomic_write_bytes`, which share one path: a temp file
with a name no other writer uses, opened exclusively, written, flushed and fsynced, then moved over the target in one
`os.replace`. A reader sees the old file or the new one, never half of either; two writers never share a temp file. A
private file (`mode`) is private from its first byte: the temp is created with that mode. A Windows `PermissionError`
on the move (an editor, an antivirus scan or TCC holding the target open) is retried for under a second.

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


def atomic_write_bytes(path, data, *, mode=None, makedirs=False):
    """Write `data` to `path` so that no reader ever sees a half-written file: the one path every writer here takes.

    `mode` (POSIX only) is the temp's mode from its creation, so a private file -- a key -- is never readable by
    others, not even while it is being written; it is set again before the move, since the umask may have narrowed it.
    Without a mode the file gets the umask's default, as `open(path, "w")` gave it.
    """
    if makedirs:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = _temp_name(path)
    private = mode is not None and os.name != "nt"
    # O_BINARY (Windows; 0 elsewhere): a descriptor from `os.open` is otherwise in the C runtime's text mode, which
    # turns each "\n" written into "\r\n": a copy of bytes would not be the original's, a text with the platform's
    # ending would get "\r\r\n", and `newline=""` would not keep the text's own. `open(path, "w")` opens binary
    # underneath too; so does `tempfile.mkstemp`.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), mode if private else 0o666)
    try:
        with io.open(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if private:
            os.chmod(tmp, mode)
        _replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write_text(path, text, *, newline=None, mode=None, makedirs=False):
    """Write `text` to `path` so that no reader ever sees a half-written file: UTF-8, through `atomic_write_bytes`.

    `newline` is `open()`'s: None writes the platform's line ending -- what `open(path, "w")` did at every site this
    replaces -- while "" and "\\n" keep the text's own, and "\\r" or "\\r\\n" write that. `mode`: `atomic_write_bytes`.
    A text UTF-8 cannot carry is refused before anything is written.
    """
    if newline not in (None, "", "\n", "\r", "\r\n"):
        raise ValueError(f"illegal newline value: {newline!r}")
    ending = os.linesep if newline is None else newline
    if ending not in ("", "\n"):
        text = text.replace("\n", ending)            # what a text file opened with this `newline` writes
    atomic_write_bytes(path, text.encode("utf-8"), mode=mode, makedirs=makedirs)


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
        for newline, ending in (("\r\n", b"\r\n"), ("\r", b"\r")):                     # open()'s other two
            atomic_write_text(path, "a\nb\n", newline=newline)
            assert _read_bytes(path) == b"a" + ending + b"b" + ending, (newline, _read_bytes(path))
        try:
            atomic_write_text(path, "a\n", newline="\t")
        except ValueError:
            pass
        else:
            raise AssertionError("a newline open() refuses was taken")
        # Bytes as they are: a backup of a file in another code page, line endings of every kind, not one changed.
        raw = "нуль\r\none\ntwo\r".encode("cp1251") + b"\x00\xff"
        atomic_write_bytes(path, raw)
        assert _read_bytes(path) == raw, _read_bytes(path)
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
    """A crash between the temp and the move leaves the old file whole and no temp behind; a text UTF-8 cannot carry is
    refused before anything is written. (A write that fails with its bytes in the temp: `_check_write_fails_clean`.)"""
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
    """A private file is private from its first byte (POSIX): the temp is CREATED with `mode`, so a key is never
    readable by others while it is written -- at the fsync, with the key in it, the temp is already 0600 (a reader that
    opened it in a wider window would keep reading after any chmod). `mode` is set again before the move, since the
    umask may have narrowed the create: under umask 077 a 0640 file is 0640 by the time it has its name. Without a mode
    a file gets what `open(path, "w")` gave -- the umask's default, never 0600 by accident (a `mkstemp` temp would make
    every `project.json` private)."""
    if os.name == "nt":
        return
    import stat
    d = _scratch()
    real_fsync, real_replace = os.fsync, os.replace
    umask = os.umask(0)
    os.umask(umask)
    at_fsync, at_replace = [], []

    def fsync(fd):                               # the temp as it is when its bytes are all in it
        st = os.fstat(fd)
        at_fsync.append((stat.S_IMODE(st.st_mode), st.st_size))
        real_fsync(fd)

    def replace(src, dst):                       # the temp as it is when it takes the file's name
        at_replace.append(stat.S_IMODE(os.stat(src).st_mode))
        real_replace(src, dst)
    try:
        os.fsync, os.replace = fsync, replace
        private, wide, plain = (os.path.join(d, n) for n in ("critic-env", "group.txt", "project.json"))
        key = "export GEMINI_API_KEY=" + "k" * 39 + "\n"
        atomic_write_text(private, key, mode=0o600)
        assert at_fsync == [(0o600, len(key))], \
            f"the key was in a temp of mode {oct(at_fsync[0][0])} (size {at_fsync[0][1]}): readable by others"
        assert at_replace == [0o600], [oct(m) for m in at_replace]
        assert stat.S_IMODE(os.stat(private).st_mode) == 0o600, oct(os.stat(private).st_mode)
        del at_fsync[:], at_replace[:]
        os.umask(0o077)
        try:
            atomic_write_text(wide, "shared\n", mode=0o640)
        finally:
            os.umask(umask)
        assert [m for m, _ in at_fsync] == [0o600] and at_replace == [0o640], \
            f"umask 077, mode 0640: {[oct(m) for m, _ in at_fsync]} at the fsync, {[oct(m) for m in at_replace]} at " \
            f"the move -- the mode is set before the move, not after"
        assert stat.S_IMODE(os.stat(wide).st_mode) == 0o640, oct(os.stat(wide).st_mode)
        atomic_write_text(plain, "{}")
        assert stat.S_IMODE(os.stat(plain).st_mode) == 0o666 & ~umask, (oct(os.stat(plain).st_mode), oct(umask))
    finally:
        os.fsync, os.replace = real_fsync, real_replace
        os.umask(umask)
        _drop(d)


def _check_write_fails_clean():
    """A write that fails once its bytes are in the temp -- at the fsync, as a full disk would -- leaves the old file
    whole and no temp behind; so does a Ctrl-C there: the clean-up takes a `BaseException`, not only an `Exception`."""
    d = _scratch()
    real_fsync = os.fsync
    try:
        path = os.path.join(d, "x.json")
        atomic_write_json(path, {"v": 1})
        before = _read_bytes(path)
        for exc in (OSError(28, "No space left on device"), KeyboardInterrupt()):
            sizes = []

            def failing(fd, exc=exc):
                sizes.append(os.fstat(fd).st_size)
                raise exc
            os.fsync = failing
            try:
                atomic_write_json(path, {"v": 2, "pad": "x" * 1000})
            except BaseException as got:  # noqa: BLE001 -- a KeyboardInterrupt is the case under test
                if got is not exc:
                    raise
            else:
                raise AssertionError(f"a write that failed with {exc!r} was reported as written")
            finally:
                os.fsync = real_fsync
            assert sizes and sizes[0] > 1000, f"{type(exc).__name__}: the temp held {sizes} bytes, not the write"
            assert _read_bytes(path) == before, type(exc).__name__
            assert os.listdir(d) == ["x.json"], (type(exc).__name__, os.listdir(d))
    finally:
        os.fsync = real_fsync
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
    for check in (_check_text_and_json, _check_foreign_tmp, _check_replace_fails_clean, _check_write_fails_clean,
                  _check_replace_retry, _check_private_mode, _check_two_writers_one_reader):
        try:
            seen[check.__name__] = check()
        except Exception as exc:  # noqa: BLE001 -- each check is reported by name; one failing must not hide the rest
            failures.append(f"{check.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        print("\n".join(failures))
        print(f"project_io selftest FAILED -- {len(failures)} check(s)")
        return 1
    reads = seen["_check_two_writers_one_reader"]
    print(f"project_io selftest OK -- text, JSON and bytes land with the old sites' bytes; a foreign <file>.tmp is "
          f"left alone and no temp name repeats; a failed move, a write failing with its bytes in the temp and a "
          f"Ctrl-C there leave the old file whole and no temp behind; a held move is retried on Windows only; a "
          f"private file is private from its first byte, its mode set again before the move; two writers x 100 and "
          f"a reader: {reads} reads, every one whole")
    return 0


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: project_io.py --selftest  (a library: the method's writers call it)", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
