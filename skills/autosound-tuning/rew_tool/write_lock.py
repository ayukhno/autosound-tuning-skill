"""One writer at a time in a project (skill #141; PLAN-AUDIT §3 J2b; TCC's G8).

Every writer of the method takes `hold(project_dir)` around its load -> modify -> write -> append: the lock file is
`<project>/.autosound/write.lock`, and `.autosound/.gitignore` (`*`) keeps the folder out of the project's git. A
lock another writer holds is waited for `AUTOSOUND_LOCK_TIMEOUT_S` seconds (read per call; default 10), then the
writer answers `Busy` -- exit 75, "busy, nothing written, safe to retry" -- having taken nothing. The lock is
never held across REW, git, `gh` or any other subprocess: the slow part runs first, then the hold, a fresh load,
the merge and the write.

POSIX: `fcntl.flock` on the file. Windows: `msvcrt.locking` on its first byte. Both are tried without blocking and
polled, so one deadline covers this process's threads and the other processes. Re-entrant within a thread: a writer
that calls another writer (capture-import -> start/record/close) takes it once.

A folder that cannot be locked at all (some shared or cloud folders refuse every lock) is written WITHOUT the lock,
and the writer says so on stderr once: two writers there can still lose a change, as before this module.

TCC reads this file as TEXT, never imports it, for the line below: a copy that declares it locks itself, and TCC takes
no lock of its own around it (`core/project_lock.py` `locks_itself`).
"""
PROTOCOL = 1

import errno
import math
import os
import sys
import threading
import time
from contextlib import ExitStack, contextmanager

try:
    import fcntl
except ImportError:                      # Windows: msvcrt's byte-range lock instead
    fcntl = None
    import msvcrt

LOCK_DIR = ".autosound"
LOCK_FILE = "write.lock"
ENV_TIMEOUT = "AUTOSOUND_LOCK_TIMEOUT_S"
DEFAULT_TIMEOUT_S = 10.0
_POLL_S = 0.05
_HELD_ERRNOS = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, getattr(errno, "EDEADLOCK", errno.EDEADLK)}


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


class Busy(Exception):
    """Another writer held the project's lock past this one's wait. Nothing was taken and nothing written: safe to
    retry. Matched by `is_busy`, never by its class -- a copy of this module loaded under another name has its own."""
    is_busy = True
    exit_code = 75

    def __init__(self, path, waited_s):
        super().__init__(path, waited_s)
        self.path, self.waited_s = path, waited_s

    def __str__(self):
        return f"busy: {self.path} is held by another writer -- nothing was written, safe to retry"


class BadTimeout(Exception):
    """`AUTOSOUND_LOCK_TIMEOUT_S` holds no number of seconds: a usage error, raised before anything is taken."""
    exit_code = 2

    def __init__(self, value):
        super().__init__(value)
        self.value = value

    def __str__(self):
        return (f"{ENV_TIMEOUT}={self.value} is not a number of seconds (0 or more) -- unset it for the default "
                f"{DEFAULT_TIMEOUT_S:g}")


def lock_path(project_dir):
    """`<project>/.autosound/write.lock`, absolute."""
    return os.path.join(os.path.abspath(project_dir), LOCK_DIR, LOCK_FILE)


def timeout_s():
    """How long a writer waits for a held lock: `AUTOSOUND_LOCK_TIMEOUT_S` seconds, read at every call, or
    `DEFAULT_TIMEOUT_S` when it is unset. NaN, infinite, negative or no number at all raises `BadTimeout`."""
    value = os.environ.get(ENV_TIMEOUT)
    if value is None:
        return DEFAULT_TIMEOUT_S
    try:
        seconds = float(value)
    except ValueError:
        raise BadTimeout(value) from None
    if not math.isfinite(seconds) or seconds < 0:
        raise BadTimeout(value)
    return seconds


def _wait_s(given):
    """The wait of one `hold`: the environment's when `given` is None (`hold`'s own parameter hides `timeout_s()`
    there), else `given`, which must be seconds as the environment's are: NaN would never reach its deadline."""
    if given is None:
        return timeout_s()
    seconds = float(given)
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"timeout_s={given!r} is not a number of seconds (0 or more)")
    return seconds


def _prepare(project_dir):
    """`<project>/.autosound/`, and its `.gitignore` of `*`, written once: the folder stays out of the project's git."""
    folder = os.path.join(os.path.abspath(project_dir), LOCK_DIR)
    os.makedirs(folder, exist_ok=True)
    try:
        with open(os.path.join(folder, ".gitignore"), "x", encoding="utf-8", newline="\n") as f:
            f.write("*\n")
    except FileExistsError:
        pass                             # there already -- another writer may have made it a moment ago


if fcntl is not None:
    def _os_lock(fd):
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _os_unlock(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)
else:
    def _os_lock(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _os_unlock(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def _held(exc):
    """Does this refusal of `_os_lock` mean another writer holds the lock? Any other one is a folder that cannot
    be locked at all."""
    return isinstance(exc, BlockingIOError) or exc.errno in _HELD_ERRNOS


def _let_go(fd):
    try:
        _os_unlock(fd)
    except OSError:
        pass                             # closing the file, next, lets go of it all the same


class _Entry:
    """This process's side of one lock file: the lock its threads queue on, and the thread holding it."""
    __slots__ = ("rlock", "owner")

    def __init__(self):
        self.rlock = threading.RLock()
        self.owner = None


_ENTRIES = {}
_ENTRIES_GUARD = threading.Lock()


def _entry(path, make=True):
    """The `_Entry` of a lock file, by its real path (case folded where the OS folds it); None if never held and
    `make` is False."""
    key = os.path.normcase(os.path.realpath(path))
    with _ENTRIES_GUARD:
        entry = _ENTRIES.get(key)
        if entry is None and make:
            entry = _ENTRIES[key] = _Entry()
        return entry


def _left(deadline):
    """Seconds until `deadline`: never negative, never more than a thread lock's wait accepts."""
    return min(max(0.0, deadline - time.monotonic()), threading.TIMEOUT_MAX)


def _take(fd, project_dir, path, start, deadline):
    """The OS lock on `fd`, polled until `deadline`: True once taken, `Busy` past the deadline, False -- said once
    on stderr -- where the folder cannot be locked at all."""
    while True:
        try:
            _os_lock(fd)
            return True
        except OSError as exc:
            if not _held(exc):
                print(f"note: {os.path.abspath(project_dir)} cannot be locked ({exc.strerror or exc}) -- writing "
                      f"without the project lock; two writers at once can lose a change here", file=sys.stderr)
                return False
        now = time.monotonic()
        if now >= deadline:
            raise Busy(path, now - start)
        time.sleep(min(_POLL_S, deadline - now))


@contextmanager
def hold(project_dir, timeout_s=None):
    """Hold the project's writer lock for the block: this process's other threads and every other process wait.

    `timeout_s` seconds to wait (None: `timeout_s()`, the environment's), one deadline over both; past it `Busy`,
    with nothing taken. A free lock is taken at once, even with no wait. A thread already holding it passes
    straight in, and its outer hold lets go. The wait is read before anything is touched: a `BadTimeout` makes
    nothing."""
    start = time.monotonic()
    deadline = start + _wait_s(timeout_s)
    path = lock_path(project_dir)
    entry = _entry(path)
    me = threading.get_ident()
    if entry.owner == me:
        yield
        return
    if not entry.rlock.acquire(timeout=_left(deadline)):
        raise Busy(path, time.monotonic() - start)
    with ExitStack() as undo:            # each step's undo, run last-first however the block ends
        undo.callback(entry.rlock.release)
        _prepare(project_dir)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
        undo.callback(os.close, fd)
        if _take(fd, project_dir, path, start, deadline):
            undo.callback(_let_go, fd)
        entry.owner = me
        undo.callback(setattr, entry, "owner", None)
        yield


def held_here(project_dir):
    """Does this thread hold the project's writer lock now?"""
    entry = _entry(lock_path(project_dir), make=False)
    return entry is not None and entry.owner == threading.get_ident()


def busy_exit(exc, stream=None):
    """Say `exc` as one line (stderr unless `stream` is given) and return its exit code: 75 for `Busy`."""
    print(str(exc), file=sys.stderr if stream is None else stream)
    return exc.exit_code


# -- selftest ------------------------------------------------------------------------------------------------------

def _scratch():
    import tempfile
    return tempfile.mkdtemp(prefix="write_lock_")


def _drop(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


def _raised(call):
    """The exception `call()` raised, or None: a check judges it by its attributes, never by its class."""
    try:
        call()
    except Exception as exc:  # noqa: BLE001 -- returned to the check, which reads what it got
        return exc
    return None


def _enter(project_dir, **kw):
    with hold(project_dir, **kw):
        pass


def _check_protocol_line():
    """TCC reads this file as TEXT for its sign (core/project_lock.py locks_itself): keep the line it matches."""
    import re
    with open(__file__, encoding="utf-8") as f:
        src = f.read()
    assert re.search(r"^PROTOCOL\s*=\s*1[ \t]*(?:#.*)?$", src, re.MULTILINE), "TCC's probe would read False"


def _check_folder_ignores_itself():
    """`.autosound/` holds the lock and a .gitignore of `*`: `git add -A` in the project stages nothing from it.
    True when git was there to ask; without git the git half is not checked, and the OK line says so."""
    import shutil
    import subprocess
    p = _scratch()
    try:
        _enter(p)
        assert os.path.isfile(lock_path(p)), f"no lock file at {lock_path(p)}"
        with open(os.path.join(p, LOCK_DIR, ".gitignore"), encoding="utf-8", newline="") as f:
            ignore = f.read()
        assert ignore == "*\n", f"{LOCK_DIR}/.gitignore holds {ignore!r}, not '*\\n'"
        git = shutil.which("git")
        if git is None:
            return False
        with open(os.path.join(p, "project.json"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        # A git a hook runs in carries GIT_DIR and GIT_INDEX_FILE: kept, they would point this probe at that repo.
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

        def git_says(*args):
            r = subprocess.run([git, *args], cwd=p, env=env, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=60)
            assert r.returncode == 0, f"git {' '.join(args)}: rc {r.returncode}: {r.stderr.strip()[-300:]}"
            return r.stdout

        git_says("init", "-q")
        git_says("add", "-A")
        listed = git_says("status", "--porcelain", "--ignored=no").splitlines()
        # The probe must see something before its silence about .autosound/ means anything.
        assert any(line.endswith("project.json") for line in listed), f"git staged nothing at all: {listed}"
        assert not [line for line in listed if LOCK_DIR in line], f"git staged the lock's folder: {listed}"
        return True
    finally:
        _drop(p)


def _check_reentrant_and_held_here():
    """A writer that calls another writer takes the lock once: the inner hold neither waits nor lets go."""
    p = _scratch()
    try:
        assert not held_here(p), "held before any hold"
        with hold(p):
            assert held_here(p), "not held inside the hold"
            with hold(p, timeout_s=0):
                assert held_here(p), "not held inside the inner hold"
            assert held_here(p), "the inner hold's end let the outer one go"
            fd = os.open(lock_path(p), os.O_RDWR)        # another descriptor of this process: refused meanwhile
            try:
                caught = _raised(lambda: _os_lock(fd))
                assert caught is not None, "the inner hold's end let the OS lock go"
                assert _held(caught), f"the probe was refused for another reason: {caught!r}"
            finally:
                os.close(fd)
        assert not held_here(p), "still held after the hold"
        fd = os.open(lock_path(p), os.O_RDWR)            # ...and taken once the outer hold is over
        try:
            _os_lock(fd)
            _os_unlock(fd)
        finally:
            os.close(fd)
    finally:
        _drop(p)


def _check_another_thread_waits():
    """Another thread of this process waits its deadline, answers Busy, and gets the lock once it is let go."""
    p = _scratch()
    held, release, errors = threading.Event(), threading.Event(), []

    def holder():
        try:
            with hold(p):
                held.set()
                release.wait(60)
        except Exception as exc:  # noqa: BLE001 -- carried to the main thread, which names it
            errors.append(exc)
            held.set()

    t = threading.Thread(target=holder, daemon=True)
    t.start()
    try:
        assert held.wait(60) and not errors, f"the other thread never held the lock: {errors}"
        caught = _raised(lambda: _enter(p, timeout_s=0.3))
        assert caught is not None, "a lock another thread holds was taken"
        assert getattr(type(caught), "is_busy", False) is True, f"not busy: {type(caught).__name__}: {caught}"
        assert caught.exit_code == 75, f"exit code {caught.exit_code}"
        assert 0.25 <= caught.waited_s < 5, f"waited {caught.waited_s:.3f}s for a deadline of 0.3s"
        assert not held_here(p), "held here after a Busy"
        release.set()
        t.join(60)
        assert not t.is_alive() and not errors, f"the other thread did not let go: {errors}"
        with hold(p, timeout_s=2):
            assert held_here(p), "not held after the other thread let go"
    finally:
        release.set()
        t.join(60)
        _drop(p)


def _holder(project_dir, signals):
    """The other writer of `_check_another_process_is_busy`. At the top level, so that `spawn` finds it by name. It
    holds the lock, says so (`held`), and lets go when the parent says `go`."""
    with hold(project_dir):
        with open(os.path.join(signals, "held"), "w", encoding="utf-8"):
            pass
        deadline = time.monotonic() + 60
        while not os.path.exists(os.path.join(signals, "go")):
            if time.monotonic() > deadline:
                raise SystemExit("the parent never said go")
            time.sleep(0.002)


def _check_another_process_is_busy():
    """The lock is a lock between PROCESSES: a spawned holder makes this one answer Busy, then lets it in."""
    import multiprocessing
    ctx = multiprocessing.get_context("spawn")
    p, signals = _scratch(), _scratch()
    child = ctx.Process(target=_holder, args=(p, signals))
    child.start()
    try:
        deadline = time.monotonic() + 60
        while not os.path.exists(os.path.join(signals, "held")):
            assert time.monotonic() < deadline and child.is_alive(), f"the holder never held (exit {child.exitcode})"
            time.sleep(0.002)
        caught = _raised(lambda: _enter(p, timeout_s=0.5))
        assert caught is not None, "a lock another process holds was taken"
        assert getattr(type(caught), "is_busy", False) is True, f"not busy: {type(caught).__name__}: {caught}"
        assert caught.exit_code == 75, f"exit code {caught.exit_code}"
        said = f"busy: {lock_path(p)} is held by another writer -- nothing was written, safe to retry"
        assert str(caught) == said, f"said {str(caught)!r}"
        assert caught.path == lock_path(p), f"path {caught.path!r}"
        assert 0.4 <= caught.waited_s < 5, f"waited {caught.waited_s:.3f}s for a deadline of 0.5s"
        with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
            pass
        child.join(60)
        assert child.exitcode == 0, f"the holder failed: exit {child.exitcode}"
        # Let in -- from another thread: this one's thread lock is re-entrant, so only another thread would meet
        # one that the Busy above left taken.
        after = []
        t = threading.Thread(target=lambda: after.append(_raised(lambda: _enter(p, timeout_s=5))), daemon=True)
        t.start()
        t.join(60)
        assert after == [None], f"not let in after the other process let go: {after}"
    finally:
        with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
            pass
        child.join(60)
        if child.is_alive():
            child.terminate()
            child.join(10)
        _drop(p)
        _drop(signals)


def _check_timeout_from_the_environment():
    """AUTOSOUND_LOCK_TIMEOUT_S, read at each call: unset is 10 s; a value that is no number of seconds is a usage
    error (exit 2) naming the variable, raised by `hold` before it takes or makes anything."""
    saved = os.environ.get(ENV_TIMEOUT)
    p = _scratch()
    try:
        os.environ.pop(ENV_TIMEOUT, None)
        assert timeout_s() == 10.0 == DEFAULT_TIMEOUT_S, f"unset read as {timeout_s()!r}"
        for value, want in (("2.5", 2.5), ("0", 0.0)):
            os.environ[ENV_TIMEOUT] = value
            got = timeout_s()
            assert got == want, f"{value!r} read as {got!r}"
        for value in ("abc", "-1", "nan", "", "inf"):
            os.environ[ENV_TIMEOUT] = value
            for label, call in (("timeout_s()", timeout_s), ("hold", lambda: _enter(p))):
                caught = _raised(call)
                assert caught is not None, f"{label} took {value!r}"
                assert getattr(caught, "exit_code", None) == 2, f"{label}, {value!r}: {caught!r}"
                said = f"{ENV_TIMEOUT}={value} is not a number of seconds (0 or more) -- unset it for the default 10"
                assert str(caught) == said, f"{label}, {value!r} said {str(caught)!r}"
            assert not os.path.exists(os.path.join(p, LOCK_DIR)), f"a bad {value!r} made the lock's folder"
    finally:
        if saved is None:
            os.environ.pop(ENV_TIMEOUT, None)
        else:
            os.environ[ENV_TIMEOUT] = saved
        _drop(p)


def _check_a_wait_given_in_code_is_checked_too():
    """`hold(p, timeout_s=...)` takes seconds, 0 or more: NaN would never reach its deadline, and an infinite or
    negative wait is no wait the environment could give either. Refused before anything is made."""
    p = _scratch()
    try:
        for value in (float("nan"), float("inf"), -1):
            caught = _raised(lambda: _enter(p, timeout_s=value))
            assert isinstance(caught, ValueError), f"timeout_s={value!r}: {caught!r}"
            assert not os.path.exists(os.path.join(p, LOCK_DIR)), f"timeout_s={value!r} made the lock's folder"
    finally:
        _drop(p)


def _check_a_free_lock_with_zero_wait():
    """A free lock is taken at once, even with no wait at all."""
    p = _scratch()
    try:
        start = time.monotonic()
        with hold(p, timeout_s=0):
            assert held_here(p), "not held inside a hold with no wait"
        took = time.monotonic() - start
        assert took < 1, f"a free lock took {took:.2f}s"
    finally:
        _drop(p)


def _check_a_folder_that_cannot_lock():
    """A Parallels shared folder, SMB, a cloud folder: the OS refuses the lock itself. The write goes ahead, said once."""
    import contextlib
    import io
    global _os_lock
    real = _os_lock

    def refuse(fd):
        raise OSError(errno.ENOLCK, "No locks available")

    p = _scratch()
    err = io.StringIO()
    _os_lock = refuse
    try:
        with contextlib.redirect_stderr(err):
            with hold(p):
                assert held_here(p), "not held here, without the OS lock"
        lines = err.getvalue().splitlines()
        assert len(lines) == 1 and lines[0].startswith("note: "), f"stderr: {lines}"
        assert p in lines[0] and "without the project lock" in lines[0], f"the note: {lines[0]!r}"
    finally:
        _os_lock = real
        _drop(p)


def _check_busy_exit_says_one_line():
    """`busy_exit` prints the refusal as one line, on stderr unless told otherwise, and returns its exit code."""
    import contextlib
    import io
    exc = Busy(lock_path("project"), 0.5)
    out = io.StringIO()
    assert busy_exit(exc, stream=out) == 75, "not 75"
    assert out.getvalue() == str(exc) + "\n", f"said {out.getvalue()!r}"
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert busy_exit(exc) == 75, "not 75 on stderr"
    assert err.getvalue() == str(exc) + "\n", f"said on stderr {err.getvalue()!r}"


def _selftest():
    failures, seen = [], {}
    for check in (_check_protocol_line, _check_folder_ignores_itself, _check_reentrant_and_held_here,
                  _check_another_thread_waits, _check_another_process_is_busy, _check_timeout_from_the_environment,
                  _check_a_wait_given_in_code_is_checked_too, _check_a_free_lock_with_zero_wait,
                  _check_a_folder_that_cannot_lock, _check_busy_exit_says_one_line):
        try:
            seen[check.__name__] = check()
        except Exception as exc:  # noqa: BLE001 -- each check is reported by name; one failing must not hide the rest
            failures.append(f"{check.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        print("\n".join(failures))
        print(f"write_lock selftest FAILED -- {len(failures)} check(s)")
        return 1
    git = seen["_check_folder_ignores_itself"]
    if not git:                                    # the OK line below claims only what ran
        print("write_lock: git add -A in a project was not checked here -- no git on PATH")
    print(f"write_lock selftest OK -- PROTOCOL = 1 on a line of its own, as TCC's probe reads it; a hold makes "
          f".autosound/write.lock and a .gitignore of '*'{' (git add -A stages nothing from it)' if git else ''}; "
          f"re-entrant in a thread, the OS lock kept until the outer hold ends; another thread and another "
          f"(spawned) process holding it make a hold wait its deadline and answer Busy -- exit 75, the lock file "
          f"named, nothing taken -- and get in once it is let go; {ENV_TIMEOUT} read at every call (unset 10 s), "
          f"a value that is no number of seconds exit 2 naming it, before anything is made, and a wait given in "
          f"code held to the same; a free lock taken at once with no wait; a folder that cannot be locked written "
          f"without the lock, said in one note line; busy_exit says one line and returns 75")
    return 0


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: write_lock.py --selftest  (a library: the method's writers call it)", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
