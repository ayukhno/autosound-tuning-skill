"""One writer at a time in a project (skill #141; PLAN-AUDIT §3 J2b; TCC's G8).

Every writer of the method takes `hold(project_dir)` around its load -> modify -> write -> append: the lock file is
`<project>/.autosound/write.lock`, and `.autosound/.gitignore` (`*`) keeps the folder out of the project's git. A
lock another writer holds is waited for `AUTOSOUND_LOCK_TIMEOUT_S` seconds (read per call; default 10), then the
writer answers `Busy` -- exit 75, "busy, nothing written, safe to retry" -- having taken nothing. The lock is
never held across REW, git, `gh` or any other subprocess: the slow part runs first, then the hold, a fresh load,
the merge and the write.

POSIX: `fcntl.flock` on the file. Windows: `LockFileEx` on its first byte, through ctypes. Both are tried without
blocking and polled, so one deadline covers this process's threads and the other processes. Re-entrant within a
thread: a writer that calls another writer (capture-import -> start/record/close) takes it once.

The lock never makes the project folder (R23). A hold on a folder that is not there -- a mistyped path, one gone --
is this process's thread lock alone, and makes nothing. The writer's own first write makes the folder, and the next
hold makes the lock and takes it; two processes creating one new project at the same moment are not ordered by it.

A folder that cannot be locked at all (some shared or cloud folders refuse every lock) is written WITHOUT the lock,
and the writer says so on stderr once: two writers there can still lose a change, as before this module. Only
another writer's lock is "held": on Windows, `LockFileEx`'s ERROR_LOCK_VIOLATION alone -- a share that refuses
the lock any other way (access denied, not supported) is a folder that cannot lock (R21). A folder where the lock
cannot even be MADE -- one this user may not write -- is refused, `Unwritable` (exit 1), before anything is
taken.

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
except ImportError:                      # Windows: LockFileEx on the file's first byte, through ctypes
    fcntl = None
    import ctypes
    import msvcrt
    from ctypes import wintypes

LOCK_DIR = ".autosound"
LOCK_FILE = "write.lock"
ENV_TIMEOUT = "AUTOSOUND_LOCK_TIMEOUT_S"
DEFAULT_TIMEOUT_S = 10.0
_POLL_S = 0.05
_HELD_ERRNOS = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, getattr(errno, "EDEADLOCK", errno.EDEADLK)}
# Windows by what imported, not by `os.name`: project_io's selftest fakes `os.name = "nt"` on POSIX.
_WINDOWS = fcntl is None
_ERROR_LOCK_VIOLATION = 33               # LockFileEx's answer when another handle holds the byte: the one "held" there


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


class Unwritable(Exception):
    """The lock cannot be made in the project -- its folder `.autosound/`, the `.gitignore` there, or `write.lock`: a
    project folder this user may not write, a read-only disk, a file where the folder belongs (#141, R6). A refusal,
    not a bug: raised before anything is taken, and nothing written. It carries what
    `project_io.Unreadable` carries -- `.path`, `.reason`, `.repair` -- and says itself the same way, so every command
    line that refuses that one in one line (exit 1) refuses this one too. Matched by `is_unreadable`, never by its
    class: a copy of this module loaded under another name has its own."""
    is_unreadable = True

    def __init__(self, path, reason, repair=None):
        super().__init__(path, reason, repair)
        self.path, self.reason, self.repair = path, reason, repair

    def __str__(self):
        return f"{self.path} {self.reason}" + (f" -- {self.repair}" if self.repair else "")


def _repair_for(exc):
    """The repair for `exc`, an `OSError` met making the lock's folder or file: the one its cause allows. Said here,
    not loaded from `project_io`: this module loads no sibling (TCC reads it as text; the writers load it by path)."""
    if exc.errno in (errno.EEXIST, errno.ENOTDIR):
        return "a file stands where a folder of its path belongs: move that file aside and run again"
    if exc.errno == errno.EISDIR:
        return "a folder stands where the lock file belongs: move that folder aside and run again"
    if exc.errno == errno.EROFS:
        return "the disk is read-only: work on a copy of the project on a disk this user can write"
    if exc.errno in (errno.EACCES, errno.EPERM):
        return "this user may not write there: give it access (its owner and mode, `ls -l`) and run again"
    return "check the disk and the folder it is on (a network share, a sync client's folder) and run again"


def _unwritable(project_dir, exc):
    """The `Unwritable` for `exc`, an `OSError` met making the lock's folder or file in `project_dir`: what could not
    be made (the `OSError`'s own file, else `.autosound/`), why, and its repair."""
    path = exc.filename or os.path.join(os.path.abspath(project_dir), LOCK_DIR)
    return Unwritable(path, f"cannot be made for the project's writer lock ({exc.strerror or exc}), so nothing was "
                            "written", _repair_for(exc))


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
    """`<project>/.autosound/`, and its `.gitignore` of `*`, written once: the folder stays out of the project's git.
    The folder alone, never its parents (R23): a project folder gone since the hold looked is refused, not made."""
    folder = os.path.join(os.path.abspath(project_dir), LOCK_DIR)
    try:
        os.mkdir(folder)
    except FileExistsError:
        if not os.path.isdir(folder):
            raise                        # a file where the folder belongs: `Unwritable`, its repair EEXIST's
    try:
        with open(os.path.join(folder, ".gitignore"), "x", encoding="utf-8", newline="\n") as f:
            f.write("*\n")
    except FileExistsError:
        pass                             # there already -- another writer may have made it a moment ago


if not _WINDOWS:
    def _os_lock(fd):
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _os_unlock(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)
else:
    # LockFileEx, not msvcrt.locking (R21): the C runtime under `locking` gives a holder (ERROR_LOCK_VIOLATION) and a
    # share that refuses locks (ERROR_ACCESS_DENIED, ERROR_NETWORK_ACCESS_DENIED, ERROR_LOCK_FAILED) one EACCES, and
    # only the Windows error, which ctypes keeps, tells them apart.
    _LOCKFILE_FAIL_IMMEDIATELY = 0x1
    _LOCKFILE_EXCLUSIVE_LOCK = 0x2

    class _Overlapped(ctypes.Structure):
        """OVERLAPPED (minwinbase.h): where the locked bytes start, zeroed -- the file's first byte. Its union of
        Offset/OffsetHigh with a pointer is laid out as the two DWORDs: the same size and place on 32 and 64 bits."""
        _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t), ("Offset", wintypes.DWORD),
                    ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)    # its own: the argtypes below touch no one else's
    _LockFileEx = _kernel32.LockFileEx
    _LockFileEx.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                            ctypes.POINTER(_Overlapped))
    _LockFileEx.restype = wintypes.BOOL
    _UnlockFileEx = _kernel32.UnlockFileEx
    _UnlockFileEx.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                              ctypes.POINTER(_Overlapped))
    _UnlockFileEx.restype = wintypes.BOOL

    def _os_lock(fd):
        """The file's first byte, exclusive, refused at once when held: an `OSError` carrying `.winerror`."""
        first = _Overlapped()
        if not _LockFileEx(msvcrt.get_osfhandle(fd), _LOCKFILE_EXCLUSIVE_LOCK | _LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0,
                           ctypes.byref(first)):
            raise ctypes.WinError(ctypes.get_last_error())

    def _os_unlock(fd):
        first = _Overlapped()
        if not _UnlockFileEx(msvcrt.get_osfhandle(fd), 0, 1, 0, ctypes.byref(first)):
            raise ctypes.WinError(ctypes.get_last_error())


def _held(exc, windows=_WINDOWS):
    """Does this refusal of `_os_lock` mean another writer holds the lock? Any other one is a folder that cannot be
    locked at all. Windows: `LockFileEx`'s ERROR_LOCK_VIOLATION alone, read off `.winerror` -- its errno is EACCES, as
    a share's refusal's is. POSIX: EWOULDBLOCK, or an errno some systems give a held lock. `windows` is a parameter
    so that both systems' table runs on each."""
    if windows:
        return getattr(exc, "winerror", None) == _ERROR_LOCK_VIOLATION
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


def _opened(project_dir, path, undo):
    """The lock file, open, its folder made first -- its close put on `undo` -- or None where the project folder itself
    is not there: the lock never makes it (R23). An `OSError` making either is `Unwritable`, a refusal (R6)."""
    if not os.path.lexists(os.path.abspath(project_dir)):
        return None
    try:
        _prepare(project_dir)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as exc:
        raise _unwritable(project_dir, exc) from exc
    undo.callback(os.close, fd)
    return fd


@contextmanager
def hold(project_dir, timeout_s=None):
    """Hold the project's writer lock for the block: this process's other threads and every other process wait.

    `timeout_s` seconds to wait (None: `timeout_s()`, the environment's), one deadline over both; past it `Busy`,
    with nothing taken. A free lock is taken at once, even with no wait. A thread already holding it passes
    straight in, and its outer hold lets go. The wait is read before anything is touched: a `BadTimeout` makes
    nothing. The lock's folder and file are made next, before anything is taken: ones that cannot be made -- a
    project folder this user may not write -- are `Unwritable`, a refusal (#141, R6). A project folder that is not
    there is never made (R23): the hold is this process's thread lock alone, under the same deadline, and makes
    nothing -- but a folder made while this thread waited for that lock is locked as any other."""
    start = time.monotonic()
    deadline = start + _wait_s(timeout_s)
    path = lock_path(project_dir)
    entry = _entry(path)
    me = threading.get_ident()
    if entry.owner == me:
        yield
        return
    with ExitStack() as undo:            # each step's undo, run last-first however the block ends
        fd = _opened(project_dir, path, undo)
        if not entry.rlock.acquire(timeout=_left(deadline)):
            raise Busy(path, time.monotonic() - start)
        undo.callback(entry.rlock.release)
        if fd is None:                   # no project folder when this thread came: one may have been made since
            fd = _opened(project_dir, path, undo)
        if fd is not None and _take(fd, project_dir, path, start, deadline):
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


def _refusal(err, winerror=None):
    """An `OSError` as the OS lock raises it: `err` its errno, and `winerror` the Windows error that `ctypes.WinError`
    sets beside the errno it maps it to -- set here as an attribute, which any system's `OSError` can carry, so the
    table of both systems runs on each."""
    exc = OSError(err, os.strerror(err))
    if winerror is not None:
        exc.winerror = winerror
    return exc


def _probe(project_dir):
    """The OS lock tried through a descriptor of its own: None when it was free (taken, and let go again), else what
    refused it."""
    fd = os.open(lock_path(project_dir), os.O_RDWR)
    try:
        caught = _raised(lambda: _os_lock(fd))
        if caught is None:
            _os_unlock(fd)
        return caught
    finally:
        os.close(fd)


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


def _check_a_project_that_cannot_be_written():
    """A project folder this user may not write cannot hold the lock's folder (#141, R6): `hold` refuses with
    `Unwritable` -- `is_unreadable` on its class, `.path` (what could not be made), `.reason` and `.repair`, said in one
    line as `project_io.Unreadable` says itself, so every command line refuses with it, exit 1 -- before anything is
    taken, and making nothing. It let the `OSError` out, a bug's 70 with a traceback. Met for real, so POSIX and not
    root; elsewhere it is not checked, and the OK line says so (False)."""
    if os.name != "posix" or os.geteuid() == 0:
        return False
    p = _scratch()
    try:
        os.chmod(p, 0o555)
        caught = _raised(lambda: _enter(p))
        assert caught is not None, "a hold in a folder this user may not write went through"
        assert getattr(type(caught), "is_unreadable", False) is True, f"no refusal: {type(caught).__name__}: {caught}"
        folder = os.path.join(p, LOCK_DIR)
        assert caught.path == folder, f"path {caught.path!r}"
        assert caught.reason == "cannot be made for the project's writer lock (Permission denied), so nothing was " \
                                "written", f"reason {caught.reason!r}"
        assert caught.repair == "this user may not write there: give it access (its owner and mode, `ls -l`) and " \
                                "run again", f"repair {caught.repair!r}"
        assert str(caught) == f"{folder} {caught.reason} -- {caught.repair}", f"said {str(caught)!r}"
        assert not os.path.exists(folder), "the lock's folder was made"
        assert not held_here(p), "held here after the refusal"
        os.chmod(p, 0o755)
        # Let in once the folder can be written -- from another thread: this one's thread lock is re-entrant, so only
        # another thread would meet one the refusal left taken.
        after = []
        t = threading.Thread(target=lambda: after.append(_raised(lambda: _enter(p, timeout_s=5))), daemon=True)
        t.start()
        t.join(60)
        assert after == [None], f"not let in once the folder could be written: {after}"
    finally:
        os.chmod(p, 0o755)
        _drop(p)
    return True


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


def _check_a_missing_project_is_not_made():
    """The lock never makes the project folder (#141, R23). A hold on a path where nothing stands -- a mistyped folder,
    one gone -- takes this process's thread lock alone, under the same deadline, and makes nothing: no folder, no
    `.autosound/`, no OS lock. Another thread waits its deadline and answers Busy; an inner hold re-enters; after the
    block nothing is there. The writer's own first write makes the folder, and the next hold the lock -- as does a
    hold that queued while the folder came. A file standing at the project path is no missing folder: `Unwritable`, as
    before. A hold made `<typo>/.autosound/`, under verbs that went on to say "nothing was written"."""
    top = _scratch()
    gone, later = os.path.join(top, "gone"), os.path.join(top, "later")
    try:
        with hold(gone, timeout_s=0):
            assert held_here(gone), "not held here on a missing project"
            assert not os.path.lexists(gone), f"the hold made the project folder: {sorted(os.listdir(top))}"
            other = []
            t = threading.Thread(target=lambda: other.append(_raised(lambda: _enter(gone, timeout_s=0.3))),
                                 daemon=True)
            t.start()
            t.join(60)
            busy = other[0] if other else None
            assert getattr(type(busy), "is_busy", False) is True, f"another thread got in, or: {busy!r}"
            assert 0.25 <= busy.waited_s < 5, f"waited {busy.waited_s:.3f}s for a deadline of 0.3s"
            with hold(gone, timeout_s=0):
                assert held_here(gone), "not held inside the inner hold"
            assert held_here(gone), "the inner hold's end let the outer one go"
        assert not held_here(gone), "still held after the hold"
        assert os.listdir(top) == [], f"a hold on a missing project made {sorted(os.listdir(top))}"
        os.makedirs(gone)                                  # the writer's own first write makes the folder...
        with hold(gone, timeout_s=0):                      # ...and the next hold makes the lock and takes it
            refused = _probe(gone)
            assert refused is not None and _held(refused), f"the next hold took no OS lock: {refused!r}"
        # A hold that queued on the thread lock while the folder was missing, let in once a writer made it, takes the
        # OS lock as every hold on a folder that is there does.
        got, queued = [], threading.Event()

        def waiter():
            queued.set()
            try:
                with hold(later, timeout_s=30):
                    got.append(_probe(later))
            except Exception as exc:  # noqa: BLE001 -- carried to the main thread, which names it
                got.append(exc)
        with hold(later, timeout_s=0):
            t = threading.Thread(target=waiter, daemon=True)
            t.start()
            queued.wait(60)
            time.sleep(0.2)                                # it found no folder, and waits on the thread lock
            os.makedirs(later)
        t.join(60)
        assert len(got) == 1 and got[0] is not None and _held(got[0]), \
            f"a hold let in once the folder came took no OS lock: {got}"
        a_file = os.path.join(top, "a-file")
        with open(a_file, "w", encoding="utf-8") as f:
            f.write("not a folder\n")
        caught = _raised(lambda: _enter(a_file, timeout_s=0))
        assert getattr(type(caught), "is_unreadable", False) is True, f"a file at the project path: {caught!r}"
        assert not held_here(a_file), "held here after the refusal"
        # Nor does making the lock's own folder make a parent: a project folder gone since the hold looked is refused.
        vanished = os.path.join(top, "vanished")
        caught = _raised(lambda: _prepare(vanished))
        assert getattr(caught, "errno", None) == errno.ENOENT, f"the lock's folder made in a gone project: {caught!r}"
        assert not os.path.lexists(vanished), "making the lock's folder made the project folder"
    finally:
        _drop(top)


def _check_which_refusals_are_held():
    """Which refusal of the OS lock means another writer holds it (#141, R21): a pure function, so both systems' table
    runs on each. POSIX as before -- EWOULDBLOCK, and EACCES that some systems give a held lock, are held; ENOLCK,
    ENOTSUP, EINVAL are a folder that cannot lock. Windows: `LockFileEx`'s ERROR_LOCK_VIOLATION (33) alone is held;
    ERROR_ACCESS_DENIED (5), ERROR_NOT_SUPPORTED (50), ERROR_NETWORK_ACCESS_DENIED (65), ERROR_INVALID_FUNCTION (1) are
    a share that cannot lock, and so is a refusal with no Windows error at all. The C runtime under `msvcrt.locking`
    mapped 33 and 5 and 65 to one EACCES, read as held: a share refusing locks answered 75 for ever."""
    posix = ((errno.EAGAIN, True), (errno.EWOULDBLOCK, True), (errno.EACCES, True), (errno.ENOLCK, False),
             (getattr(errno, "ENOTSUP", errno.EOPNOTSUPP), False), (errno.EINVAL, False), (errno.EIO, False))
    windows = ((33, errno.EACCES, True), (5, errno.EACCES, False), (50, errno.EINVAL, False),
               (65, errno.EACCES, False), (1, errno.EINVAL, False), (None, errno.EACCES, False))
    wrong = [f"POSIX {errno.errorcode[err]}: held={not want}" for err, want in posix
             if _held(_refusal(err), windows=False) is not want]
    wrong += [f"Windows winerror {code} ({errno.errorcode[err]}): held={not want}" for code, err, want in windows
              if _held(_refusal(err, code), windows=True) is not want]
    assert not wrong, f"read wrong: {wrong}"


def _check_a_share_refusing_the_lock_is_noted():
    """Windows only: `LockFileEx` refused with ERROR_ACCESS_DENIED -- a share that refuses locks, faked at the call --
    is a folder that cannot lock (#141, R21): the note, and the hold goes ahead at once, not Busy after its wait. The
    call is asked for the first byte, exclusive, failing at once. Elsewhere it is not checked, and the OK line says so
    (False)."""
    if not _WINDOWS:
        return False
    import contextlib
    import io
    global _LockFileEx
    real, asked = _LockFileEx, []

    def refuse(handle, flags, reserved, low, high, overlapped):
        asked.append((flags, reserved, low, high, overlapped._obj.Offset, overlapped._obj.OffsetHigh))
        ctypes.set_last_error(5)                       # ERROR_ACCESS_DENIED
        return 0

    p = _scratch()
    err = io.StringIO()
    _LockFileEx = refuse
    try:
        start = time.monotonic()
        with contextlib.redirect_stderr(err):
            with hold(p, timeout_s=5):
                assert held_here(p), "not held here, without the OS lock"
        took = time.monotonic() - start
        assert took < 2, f"a share refusing the lock was waited for {took:.1f}s, as if held"
        assert asked and set(asked) == {(3, 0, 1, 0, 0, 0)}, f"LockFileEx was asked {asked}"
        lines = err.getvalue().splitlines()
        assert len(lines) == 1 and lines[0].startswith(f"note: {p} cannot be locked ("), f"stderr: {lines}"
        assert "without the project lock" in lines[0], f"the note: {lines[0]!r}"
    finally:
        _LockFileEx = real
        _drop(p)
    return True


def _selftest():
    failures, seen = [], {}
    for check in (_check_protocol_line, _check_folder_ignores_itself, _check_reentrant_and_held_here,
                  _check_another_thread_waits, _check_another_process_is_busy, _check_timeout_from_the_environment,
                  _check_a_wait_given_in_code_is_checked_too, _check_a_free_lock_with_zero_wait,
                  _check_a_folder_that_cannot_lock, _check_a_project_that_cannot_be_written,
                  _check_busy_exit_says_one_line, _check_a_missing_project_is_not_made, _check_which_refusals_are_held,
                  _check_a_share_refusing_the_lock_is_noted):
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
    unwritable = seen["_check_a_project_that_cannot_be_written"]
    if not unwritable:
        print("write_lock: a project folder this user may not write was not checked here -- "
              + ("run as root, whom no file mode refuses" if os.name == "posix" else "Windows keeps no POSIX mode"))
    share = seen["_check_a_share_refusing_the_lock_is_noted"]
    if not share:
        print("write_lock: LockFileEx refused by a share (ERROR_ACCESS_DENIED, faked at the call) was not checked "
              "here -- Windows only; the table of which refusals are held ran")
    print(f"write_lock selftest OK -- PROTOCOL = 1 on a line of its own, as TCC's probe reads it; a hold makes "
          f".autosound/write.lock and a .gitignore of '*'{' (git add -A stages nothing from it)' if git else ''}; "
          f"re-entrant in a thread, the OS lock kept until the outer hold ends; another thread and another "
          f"(spawned) process holding it make a hold wait its deadline and answer Busy -- exit 75, the lock file "
          f"named, nothing taken -- and get in once it is let go; {ENV_TIMEOUT} read at every call (unset 10 s), "
          f"a value that is no number of seconds exit 2 naming it, before anything is made, and a wait given in "
          f"code held to the same; a free lock taken at once with no wait; a hold on a missing project makes "
          f"nothing -- the thread lock alone, Busy to another thread, re-entrant -- and the next hold on the made "
          f"folder takes the lock; only another writer's lock read as held (on Windows ERROR_LOCK_VIOLATION alone; "
          f"the table on every system{', and a share refusing LockFileEx written with the note' if share else ''}); "
          f"a folder that cannot be locked written "
          f"without the lock, said in one note line; "
          f"{'a project folder this user may not write refused as Unwritable, nothing taken or made; ' if unwritable else ''}"
          f"busy_exit says one line and returns 75")
    return 0


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: write_lock.py --selftest  (a library: the method's writers call it)", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
