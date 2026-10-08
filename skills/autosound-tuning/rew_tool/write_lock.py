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
is this process's thread lock alone, and makes nothing. The writer's own first write makes the folder (`make_folder`,
which refuses one it cannot make as `Unwritable`), and the next hold makes the lock and takes it. What that costs: a
hold that found no folder stays the thread lock alone until it ends, so what it writes once the folder is there is not
ordered against another process's writer of that project -- two processes creating one new project at the same moment
are not ordered by the lock.

A folder that cannot be locked at all (some shared or cloud folders refuse every lock) is written WITHOUT the lock,
and the writer says so on stderr, once per process for each folder: two writers there can still lose a change, as
before this module. Only another writer's lock is "held": on Windows, `LockFileEx`'s ERROR_LOCK_VIOLATION alone -- a
share that refuses the lock any other way (access denied, not supported) is a folder that cannot lock (R21). A folder
where the lock cannot even be MADE -- one this user may not write -- is refused, `Unwritable` (exit 1), before
anything is taken. `probe(project_dir)` tells, holding nothing and making nothing, which of these a project's folder is
now -- free, held, one that cannot lock, or one with no lock file yet (R26): `contract.py check` reports it.

TCC reads this file as TEXT, never imports it, for the line below (`core/project_lock.py` `locks_itself`): a copy
that declares it locks itself. Today's TCC keeps its own serialisation as it is -- its thread lock, and on POSIX a
flock on `process/.process-write.lock` held around the child it runs; on Windows the thread lock alone, nothing across
processes. This module never takes TCC's file (it would wait on its own parent).
"""
PROTOCOL = 1

import errno
import math
import os
import stat
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
_NOTED = set()                           # the folders this process has said it writes without the lock (R22a)


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
    project folder this user may not write, a read-only disk, a file where the folder belongs (#141, R6) -- or, by
    `make_folder`, the project's folder itself, which a creator's first write makes. A refusal, not a bug: raised
    before anything is taken, and nothing written. It carries what
    `project_io.Unreadable` carries -- `.path`, `.reason`, `.repair` -- and says itself the same way, so every command
    line that refuses that one in one line (exit 1) refuses this one too. Matched by `is_unreadable`, never by its
    class: a copy of this module loaded under another name has its own."""
    is_unreadable = True

    def __init__(self, path, reason, repair=None):
        super().__init__(path, reason, repair)
        self.path, self.reason, self.repair = path, reason, repair

    def __str__(self):
        return f"{self.path} {self.reason}" + (f" -- {self.repair}" if self.repair else "")


def _repair_for(exc, windows=_WINDOWS):
    """The repair for `exc`, an `OSError` met making the lock's folder or file: the one its cause allows, access
    named where `windows` or POSIX keeps it (a parameter, so that both run on every system). Said here, not loaded
    from `project_io`: this module loads no sibling (TCC reads it as text; the writers load it by path)."""
    if exc.errno in (errno.EEXIST, errno.ENOTDIR):
        return "a file stands where a folder of its path belongs: move that file aside and run again"
    if exc.errno == errno.EISDIR:
        return "a folder stands where the lock file belongs: move that folder aside and run again"
    if exc.errno == errno.EROFS:
        return "the disk is read-only: work on a copy of the project on a disk this user can write"
    if exc.errno in (errno.EACCES, errno.EPERM):
        where = "the folder's Properties, Security tab" if windows else "its owner and mode, `ls -l`"
        return f"this user may not write there: give it access ({where}) and run again"
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


def make_folder(path):
    """Make `path`, a folder of a project, with its parents: what a creator's first write does where the project folder
    is not there yet, the lock never making it (R23). One there already is passed over. One that cannot be made -- under
    a folder this user may not write, on a read-only disk, a file where a folder of the path belongs -- is `Unwritable`
    (#141), as a lock that cannot be made is: every command line says it in one line, exit 1. It was a raw `OSError` --
    a traceback, or a bug's 70."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        raise Unwritable(exc.filename or os.path.abspath(path),
                         f"cannot be made ({exc.strerror or exc}), so nothing was written", _repair_for(exc)) from exc


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
    """The OS lock let go. An unlock that fails is passed over: closing the file lets go of it all the same. The hold
    closes it as it ends -- after the thread lock's release when the file was opened first, so a thread let in
    between the two polls the OS lock until the close."""
    try:
        _os_unlock(fd)
    except OSError:
        pass


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


def _note_cannot_lock(project_dir, exc):
    """Say on stderr that `project_dir` is written without the lock -- once per process for each folder (R22a): a
    long-lived caller writing there again and again is told once."""
    folder = os.path.abspath(project_dir)
    key = os.path.normcase(os.path.realpath(folder))
    with _ENTRIES_GUARD:
        if key in _NOTED:
            return
        _NOTED.add(key)
    print(f"note: {folder} cannot be locked ({exc.strerror or exc}) -- writing without the project lock; two writers "
          f"at once can lose a change here", file=sys.stderr)


def _take(fd, project_dir, path, start, deadline):
    """The OS lock on `fd`, polled until `deadline`: True once taken, `Busy` past the deadline, False -- said on
    stderr, once per process for each folder -- where the folder cannot be locked at all."""
    while True:
        try:
            _os_lock(fd)
            return True
        except OSError as exc:
            if not _held(exc):
                _note_cannot_lock(project_dir, exc)
                return False
        now = time.monotonic()
        if now >= deadline:
            raise Busy(path, now - start)
        time.sleep(min(_POLL_S, deadline - now))


def _opened(project_dir, path, undo):
    """The lock file, open, its folder made first -- its close put on `undo` -- or None where the project folder itself
    is not there: the lock never makes it (R23). Not there is nothing standing at the path, `FileNotFoundError` alone: a
    path that cannot be looked at -- a parent this user may not search, a file where a folder of it belongs, a loop of
    links, a name too long, the disk's error -- goes on to be made, and is refused there. An `OSError` making either is
    `Unwritable`, a refusal (R6)."""
    try:
        os.lstat(os.path.abspath(project_dir))
    except FileNotFoundError:
        return None
    except OSError:
        pass                             # cannot be looked at: making the lock's folder meets it too, and refuses it
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
    nothing -- but a folder made while this thread waited for that lock is locked as any other. Not there is nothing
    at the path: one that cannot be looked at (a parent this user may not search) is `Unwritable` too."""
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


def probe(project_dir):
    """Can the project's writer lock be taken here? `(answer, why)` (#141, R26), what `contract.py check` reports:

    * `("free", None)` -- the OS lock was taken, and let go at once;
    * `("held", None)` -- another writer holds it: the lock working;
    * `("cannot_lock", <the OS's reason>)` -- the OS refuses the lock itself: the writers write here WITHOUT it, each
      saying so in a `note:` line;
    * `("cannot_lock", "<path> is not a file")`, or `"<path> is not a folder"` -- something that is not a file stands
      at the lock file's path (a folder), or something that is not a folder at its folder's, `.autosound` (a file):
      the lock cannot be made there, and every writer refuses to write, `Unwritable`, until it is moved aside;
    * `("no_lock_file", None)` -- `<project>/.autosound/write.lock` is not there: no writer has made it yet, or the
      project folder is not there. It is not tried, for it would have to be made.

    The existing file is opened read-write, never created: nothing is made, nothing in it changes. The OS lock is tried
    without waiting, as a hold tries it, and a refusal read as a hold reads it -- on Windows only ERROR_LOCK_VIOLATION
    is held. No thread lock is taken, so this process's own hold reads as held too. Any other error -- the file there
    and not to be opened, a folder on its path not to be searched -- is raised as it is."""
    path = lock_path(project_dir)
    for where, kind, what in ((os.path.dirname(path), stat.S_ISDIR, "a folder"), (path, stat.S_ISREG, "a file")):
        try:
            mode = os.stat(where).st_mode
        except FileNotFoundError:
            return "no_lock_file", None
        if not kind(mode):
            return "cannot_lock", f"{where} is not {what}"
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            _os_lock(fd)
        except OSError as exc:
            return ("held", None) if _held(exc) else ("cannot_lock", exc.strerror or str(exc))
        _let_go(fd)
        return "free", None
    finally:
        os.close(fd)


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


def _raise_inside(project_dir):
    with hold(project_dir, timeout_s=0):
        raise RuntimeError("inside")


def _refusal(err, winerror=None):
    """An `OSError` as the OS lock raises it: `err` its errno, and `winerror` the Windows error that `ctypes.WinError`
    sets beside the errno it maps it to -- set here as an attribute, which any system's `OSError` can carry, so the
    table of both systems runs on each."""
    exc = OSError(err, os.strerror(err))
    if winerror is not None:
        exc.winerror = winerror
    return exc


def _a_held_refusal():
    """What `_os_lock` raises on this system when another writer holds the lock."""
    return _refusal(errno.EACCES, _ERROR_LOCK_VIOLATION) if _WINDOWS else _refusal(errno.EWOULDBLOCK)


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
    global _opened
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
        # OS lock as every hold on a folder that is there does. The folder is made once the waiter has LOOKED and found
        # none -- its `_opened` answered None -- never after a sleep: a waiter slow to start under load found the
        # folder made, and the leg passed without the case it is for.
        real_opened = _opened
        got, looked = [], threading.Event()

        def opened(project_dir, path, undo):
            fd = real_opened(project_dir, path, undo)
            if fd is None and project_dir == later:
                looked.set()
            return fd

        def waiter():
            try:
                with hold(later, timeout_s=30):
                    got.append(_probe(later))
            except Exception as exc:  # noqa: BLE001 -- carried to the main thread, which names it
                got.append(exc)
        with hold(later, timeout_s=0):
            _opened = opened                               # after this thread's own look: the waiter's alone is seen
            try:
                t = threading.Thread(target=waiter, daemon=True)
                t.start()
                assert looked.wait(60), "the waiter never looked for the folder"
                os.makedirs(later)                         # it found no folder, and waits on the thread lock
            finally:
                _opened = real_opened
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


def _check_the_note_once_per_folder():
    """A folder that cannot lock is said once per process (#141, R22a): a long-lived caller writing there again and
    again -- TCC, a batch of the form's answers -- is told once, not at every write. Another folder is told its own."""
    import contextlib
    import io
    global _os_lock
    real = _os_lock

    def refuse(fd):
        raise _refusal(errno.ENOLCK)

    p, q = _scratch(), _scratch()
    err = io.StringIO()
    _os_lock = refuse
    try:
        with contextlib.redirect_stderr(err):
            for folder in (p, p, q, p, q):
                with hold(folder):
                    assert held_here(folder), "not held here, without the OS lock"
        lines = err.getvalue().splitlines()
        assert len(lines) == 2, f"{len(lines)} note(s) for five holds on two folders: {lines}"
        assert p in lines[0] and q in lines[1], f"the notes: {lines}"
    finally:
        _os_lock = real
        _drop(p)
        _drop(q)


def _check_an_error_inside_lets_go():
    """An error inside the hold is its caller's, and lets everything go -- the owner, the thread lock, the OS lock and
    the file: another thread gets in at once, a second descriptor gets the OS lock, and this thread holds again with no
    wait. A hold that let go of the owner alone would keep every other writer out until the process ended."""
    p = _scratch()
    try:
        caught = _raised(lambda: _raise_inside(p))
        assert isinstance(caught, RuntimeError) and str(caught) == "inside", f"the error became {caught!r}"
        assert not held_here(p), "held here after an error inside"
        other = []
        t = threading.Thread(target=lambda: other.append(_raised(lambda: _enter(p, timeout_s=0))), daemon=True)
        t.start()
        t.join(60)
        assert other == [None], f"another thread was kept out after an error inside: {other}"
        refused = _probe(p)
        assert refused is None, f"the OS lock was kept after an error inside: {refused!r}"
        again = _raised(lambda: _enter(p, timeout_s=0))
        assert again is None, f"this thread could not hold again: {again!r}"
    finally:
        _drop(p)


def _check_one_deadline():
    """One deadline covers both waits (#141): a hold that queued 0.6 s behind another thread has what is left of its
    1 s for the OS lock, not a fresh second -- Busy at 1 s, never at 1.6. The OS lock is faked as held, so only the
    deadline ends the wait."""
    global _os_lock
    real = _os_lock
    p = _scratch()
    held, go, errors = threading.Event(), threading.Event(), []

    def holder():
        try:
            with hold(p, timeout_s=0):
                held.set()
                go.wait(60)
                time.sleep(0.6)
        except Exception as exc:  # noqa: BLE001 -- carried to the main thread, which names it
            errors.append(exc)
            held.set()

    def still_held(fd):
        raise _a_held_refusal()

    t = threading.Thread(target=holder, daemon=True)
    t.start()
    try:
        assert held.wait(60) and not errors, f"the other thread never held the lock: {errors}"
        _os_lock = still_held
        go.set()
        caught = _raised(lambda: _enter(p, timeout_s=1.0))
        assert getattr(type(caught), "is_busy", False) is True, f"not busy: {caught!r}"
        assert 0.9 <= caught.waited_s < 1.4, f"Busy after {caught.waited_s:.2f}s of a 1 s wait"
    finally:
        _os_lock = real
        go.set()
        t.join(60)
        _drop(p)


def _check_a_file_where_the_lock_folder_belongs():
    """A FILE named `.autosound` in the project: the lock's folder cannot be made, and `hold` refuses with `Unwritable`
    -- `.path` that file, the EEXIST repair -- before anything is taken, the file as it was. No file mode is involved,
    so it is met on every system and as root."""
    p = _scratch()
    try:
        blocker = os.path.join(p, LOCK_DIR)
        with open(blocker, "w", encoding="utf-8") as f:
            f.write("a file, not the lock's folder\n")
        caught = _raised(lambda: _enter(p, timeout_s=0))
        assert getattr(type(caught), "is_unreadable", False) is True, f"no refusal: {caught!r}"
        assert caught.path == blocker, f"path {caught.path!r}"
        assert caught.repair == "a file stands where a folder of its path belongs: move that file aside and run " \
                               "again", f"repair {caught.repair!r}"
        assert caught.reason.startswith("cannot be made for the project's writer lock (") \
            and caught.reason.endswith("), so nothing was written"), f"reason {caught.reason!r}"
        assert not held_here(p), "held here after the refusal"
        with open(blocker, encoding="utf-8") as f:
            assert f.read() == "a file, not the lock's folder\n", "the file was changed"
        os.remove(blocker)
        after = []                                   # nothing was taken: another thread gets in at once
        t = threading.Thread(target=lambda: after.append(_raised(lambda: _enter(p, timeout_s=0))), daemon=True)
        t.start()
        t.join(60)
        assert after == [None], f"not let in once the file was moved aside: {after}"
    finally:
        _drop(p)


def _check_a_project_folder_not_to_be_looked_at():
    """Only a project folder where NOTHING stands is one that is not there (#141, R23): a path that cannot be looked at
    -- a file where a folder of the path belongs, a loop of links, a name too long, a parent this user may not search
    -- is no missing folder. Its lock's folder is made, and refused: `Unwritable` (R6), nothing taken, nothing made.
    Each was read as missing, and the hold went through as the thread lock alone with no word; the writer's own I/O
    then failed raw. POSIX's errors, so POSIX alone; the parent's search right needs a mode and a user it refuses (not
    root). Returns what ran -- "all", "no search" (root), or None (not POSIX) -- and the OK line claims only that."""
    if os.name != "posix":
        return None
    top = _scratch()
    failures = []
    access = "this user may not write there: give it access (its owner and mode, `ls -l`) and run again"

    def refused(project_dir, label, repair=None):
        caught = _raised(lambda: _enter(project_dir, timeout_s=0))
        if not getattr(type(caught), "is_unreadable", False):
            failures.append(f"{label}: {'the hold went through' if caught is None else repr(caught)}")
        elif not caught.reason.startswith("cannot be made for the project's writer lock (") \
                or (repair is not None and caught.repair != repair):
            failures.append(f"{label}: said {str(caught)!r}")
        if held_here(project_dir):
            failures.append(f"{label}: held here after it")
    try:
        a_file = os.path.join(top, "a-file")
        with open(a_file, "w", encoding="utf-8") as f:
            f.write("not a folder\n")
        refused(os.path.join(a_file, "car"), "a file where a folder of the path belongs",
                "a file stands where a folder of its path belongs: move that file aside and run again")
        os.symlink("loop", os.path.join(top, "loop"))
        refused(os.path.join(top, "loop", "car"), "a loop of links")
        refused(os.path.join(top, "x" * 300), "a name too long")
        ran = "no search"
        if os.geteuid() != 0:
            locked = os.path.join(top, "locked")
            os.makedirs(os.path.join(locked, "car"))
            os.chmod(locked, 0o600)                        # read and write, no search
            try:
                refused(os.path.join(locked, "car"), "a project folder whose parent this user may not search", access)
                refused(os.path.join(locked, "gone"), "a path under a parent this user may not search", access)
            finally:
                os.chmod(locked, 0o755)
            if os.listdir(os.path.join(locked, "car")) or os.listdir(locked) != ["car"]:
                failures.append(f"made under the parent: {sorted(os.listdir(locked))}, "
                                f"{sorted(os.listdir(os.path.join(locked, 'car')))}")
            ran = "all"
        with open(a_file, encoding="utf-8") as f:
            if f.read() != "not a folder\n":
                failures.append("the file in the path was changed")
        if sorted(os.listdir(top)) != sorted(["a-file", "loop"] + (["locked"] if ran == "all" else [])):
            failures.append(f"made {sorted(os.listdir(top))}")
    finally:
        _drop(top)
    assert not failures, "\n  ".join(["a project folder that cannot be looked at:"] + failures)
    return ran


def _check_a_folder_that_cannot_be_made():
    """`make_folder` makes a folder of a project -- the project folder itself where a creator's first write meets none,
    the lock never making it (R23) -- with its parents, and passes over one that is there. One that cannot be made is
    `Unwritable` (#141), as a lock that cannot be made is: `.path` what could not be made, `.reason` `cannot be made
    (<why>), so nothing was written`, the repair its cause allows -- so every command line says it in one line, exit 1.
    A creator met a raw `OSError`: a traceback, or a bug's 70. A file where the folder belongs is met on every system;
    a parent this user may not write needs a POSIX mode and a user it refuses (not root): elsewhere it is not checked,
    and the OK line says so (False)."""
    top = _scratch()
    try:
        deep = os.path.join(top, "new", "process")
        make_folder(deep)
        assert os.path.isdir(deep), "not made, with its parent"
        make_folder(deep)                                  # there already: passed over
        a_file = os.path.join(top, "a-file")
        with open(a_file, "w", encoding="utf-8") as f:
            f.write("not a folder\n")
        caught = _raised(lambda: make_folder(a_file))
        assert getattr(type(caught), "is_unreadable", False) is True, f"a file where the folder belongs: {caught!r}"
        assert caught.path == a_file, f"path {caught.path!r}"
        assert caught.reason.startswith("cannot be made (") and caught.reason.endswith("), so nothing was written"), \
            f"reason {caught.reason!r}"
        assert caught.repair == "a file stands where a folder of its path belongs: move that file aside and run " \
                               "again", f"repair {caught.repair!r}"
        with open(a_file, encoding="utf-8") as f:
            assert f.read() == "not a folder\n", "the file was changed"
        if os.name != "posix" or os.geteuid() == 0:
            return False
        ro = os.path.join(top, "ro")
        os.makedirs(ro)
        os.chmod(ro, 0o555)
        try:
            new = os.path.join(ro, "car")
            caught = _raised(lambda: make_folder(os.path.join(new, "process")))
            said = (f"{new} cannot be made (Permission denied), so nothing was written -- this user may not write "
                    "there: give it access (its owner and mode, `ls -l`) and run again")
            assert getattr(type(caught), "is_unreadable", False) is True and str(caught) == said, \
                f"under a parent this user may not write: {caught!r}"
            assert os.listdir(ro) == [], f"made {sorted(os.listdir(ro))}"
        finally:
            os.chmod(ro, 0o755)
        return True
    finally:
        _drop(top)


def _check_refusals_are_no_oserror_or_valueerror():
    """`Busy`, `BadTimeout` and `Unwritable` subclass neither `OSError` nor `ValueError`: the command lines catch those
    two by class BEFORE they read the lock's refusals by attribute (project.py, state/apply.py, setup_import.py,
    dsp_profile.py's set-setting), so a refusal under either base would be said as their own error, exit 1 or 2 or 3,
    never 75."""
    under = [f"{cls.__name__} < {base.__name__}" for cls in (Busy, BadTimeout, Unwritable)
             for base in (OSError, ValueError) if issubclass(cls, base)]
    assert not under, f"caught by class before its attribute is read: {under}"


def _check_the_access_repair_fits_the_system():
    """A folder this user may not write is repaired where that system keeps its access: `ls -l` on POSIX, the folder's
    Security tab on Windows -- never `ls -l` to a Windows user."""
    denied = _refusal(errno.EACCES)
    posix, windows = _repair_for(denied, windows=False), _repair_for(denied, windows=True)
    assert posix == "this user may not write there: give it access (its owner and mode, `ls -l`) and run again", \
        f"POSIX: {posix!r}"
    assert "ls -l" not in windows and "Security" in windows, f"Windows: {windows!r}"


def _check_a_broken_check_shows_its_traceback():
    """A check that breaks -- any error but an AssertionError -- is reported with its traceback (CI's Windows step has
    only this output to read); a check that fails, with its message alone. Both are counted, and neither hides the
    next."""
    def broken():
        raise KeyError("missing")

    def failed():
        raise AssertionError("not so")

    def passed():
        return True

    failures, seen = _run_checks((broken, failed, passed))
    assert len(failures) == 2 and seen == {"passed": True}, f"{failures} / {seen}"
    assert failures[0].startswith("broken: KeyError: 'missing'\nTraceback (most recent call last):") \
        and failures[0].rstrip().endswith("KeyError: 'missing'"), f"the broken check said {failures[0]!r}"
    assert failures[1] == "failed: AssertionError: not so", f"the failed check said {failures[1]!r}"


def _check_the_probe_answers():
    """`probe(project_dir)` says whether the project's writer lock can be taken here (#141, R26) -- what `contract.py
    check` asks, on every system TCC shows that check on, a Windows VM among them: `("no_lock_file", None)` where no
    writer has made the lock file yet (a project folder that is not there too), and the probe makes nothing;
    `("free", None)`, the lock taken and let go at once; `("held", None)` while another (spawned) process holds it;
    `("cannot_lock", <the OS's reason>)` where the OS refuses the lock itself, faked at the call with the refusal this
    system gives such a folder. It keeps nothing: after it the lock is free and the folder holds what it held."""
    import multiprocessing
    global _os_lock
    real = _os_lock
    top, signals = _scratch(), _scratch()
    p, gone = os.path.join(top, "car"), os.path.join(top, "gone")
    child = None
    failures = []

    def refuse(fd):
        raise _refusal(errno.EACCES, 5) if _WINDOWS else _refusal(errno.ENOLCK)    # a share's refusal, never "held"
    try:
        os.makedirs(p)
        for folder in (p, gone):
            got = probe(folder)
            if got != ("no_lock_file", None):
                failures.append(f"no lock file yet ({os.path.basename(folder)}): {got!r}")
        if os.listdir(top) != ["car"] or os.listdir(p):
            failures.append(f"the probe made something: {sorted(os.listdir(top))}, {sorted(os.listdir(p))}")
        _enter(p)                                          # a first write's hold: the lock file is there from now on
        made = sorted(os.listdir(os.path.join(p, LOCK_DIR)))
        got = probe(p)
        if got != ("free", None):
            failures.append(f"a free lock: {got!r}")
        refused = _probe(p)
        if refused is not None or sorted(os.listdir(os.path.join(p, LOCK_DIR))) != made:
            failures.append(f"the probe kept something: the lock refused {refused!r}, the folder holds "
                            f"{sorted(os.listdir(os.path.join(p, LOCK_DIR)))}")
        child = multiprocessing.get_context("spawn").Process(target=_holder, args=(p, signals))
        child.start()
        deadline = time.monotonic() + 60
        while not os.path.exists(os.path.join(signals, "held")):
            assert time.monotonic() < deadline and child.is_alive(), f"the holder never held (exit {child.exitcode})"
            time.sleep(0.002)
        got = probe(p)
        if got != ("held", None):
            failures.append(f"held by another process: {got!r}")
        with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
            pass
        child.join(60)
        _os_lock = refuse
        try:
            answer, why = probe(p)
        finally:
            _os_lock = real
        said = os.strerror(errno.EACCES if _WINDOWS else errno.ENOLCK)
        if (answer, why) != ("cannot_lock", said):
            failures.append(f"a folder that cannot lock: {(answer, why)!r}, not ('cannot_lock', {said!r})")
        if probe(p) != ("free", None):
            failures.append(f"free again once the OS takes the lock: {probe(p)!r}")
        # Something that is not a file where the lock belongs -- a folder at the lock file's path, a file at its
        # folder's -- is refused by every writer, `Unwritable`: cannot lock, naming it, and nothing changes. It read as
        # no lock file yet, and `check` said nothing while every writer refused.
        a_folder, a_file = os.path.join(top, "a-folder"), os.path.join(top, "a-file")
        os.makedirs(lock_path(a_folder))
        os.makedirs(a_file)
        with open(os.path.join(a_file, LOCK_DIR), "w", encoding="utf-8") as f:
            f.write("not the lock's folder\n")
        for folder, said in ((a_folder, f"{lock_path(a_folder)} is not a file"),
                             (a_file, f"{os.path.dirname(lock_path(a_file))} is not a folder")):
            got = probe(folder)
            if got != ("cannot_lock", said):
                failures.append(f"{said}: {got!r}")
        if os.listdir(lock_path(a_folder)) or os.listdir(a_file) != [LOCK_DIR]:
            failures.append(f"the probe changed what stands there: {sorted(os.listdir(a_file))}")
    finally:
        _os_lock = real
        with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
            pass
        if child is not None:
            child.join(60)
            if child.is_alive():
                child.terminate()
                child.join(10)
        _drop(top)
        _drop(signals)
    assert not failures, "\n  ".join(["the probe:"] + failures)


def _run_checks(checks):
    """Each check run, every failure collected: (failures, {name: what it returned}). A check that fails says its
    message; one that BREAKS -- any error but an AssertionError -- says its traceback too, all that CI's Windows step
    leaves to read."""
    import traceback
    failures, seen = [], {}
    for check in checks:
        try:
            seen[check.__name__] = check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: AssertionError: {exc}")
        except Exception as exc:  # noqa: BLE001 -- each check is reported by name; one failing must not hide the rest
            failures.append(f"{check.__name__}: {type(exc).__name__}: {exc}\n{traceback.format_exc().rstrip()}")
    return failures, seen


def _selftest():
    failures, seen = _run_checks((
        _check_protocol_line, _check_folder_ignores_itself, _check_reentrant_and_held_here, _check_another_thread_waits,
        _check_another_process_is_busy, _check_timeout_from_the_environment, _check_a_wait_given_in_code_is_checked_too,
        _check_a_free_lock_with_zero_wait, _check_a_folder_that_cannot_lock, _check_a_project_that_cannot_be_written,
        _check_busy_exit_says_one_line, _check_a_missing_project_is_not_made, _check_which_refusals_are_held,
        _check_a_share_refusing_the_lock_is_noted, _check_the_note_once_per_folder, _check_an_error_inside_lets_go,
        _check_one_deadline, _check_a_file_where_the_lock_folder_belongs, _check_a_project_folder_not_to_be_looked_at,
        _check_a_folder_that_cannot_be_made, _check_refusals_are_no_oserror_or_valueerror,
        _check_the_access_repair_fits_the_system, _check_a_broken_check_shows_its_traceback,
        _check_the_probe_answers))
    if failures:
        print("\n".join(failures))
        print(f"write_lock selftest FAILED -- {len(failures)} check(s)")
        return 1
    git = seen["_check_folder_ignores_itself"]
    if not git:                                    # the OK line below claims only what ran
        print("write_lock: git add -A in a project was not checked here -- no git on PATH")
    no_mode = "run as root, whom no file mode refuses" if os.name == "posix" else "Windows keeps no POSIX mode"
    unwritable = seen["_check_a_project_that_cannot_be_written"]
    if not unwritable:
        print(f"write_lock: a project folder this user may not write was not checked here -- {no_mode}")
    looked = seen["_check_a_project_folder_not_to_be_looked_at"]
    if looked is None:
        print("write_lock: a project path that cannot be looked at (a file in it, a loop of links, a name too long, a "
              "parent this user may not search) was not checked here -- POSIX's errors, asked on POSIX alone")
    elif looked != "all":
        print(f"write_lock: a project folder whose parent this user may not search was not checked here -- {no_mode}")
    made = seen["_check_a_folder_that_cannot_be_made"]
    if not made:
        print(f"write_lock: a project folder under a parent this user may not write was not checked here -- {no_mode}")
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
          f"code held to the same; one deadline over both waits; a free lock taken at once with no wait; a hold on a "
          f"missing project makes nothing -- the thread lock alone, Busy to another thread, re-entrant -- and the "
          f"next hold on the made folder takes the lock; only another writer's lock read as held (on Windows "
          f"ERROR_LOCK_VIOLATION alone; the table on every system"
          f"{', and a share refusing LockFileEx written with the note' if share else ''}); a folder that cannot be "
          f"locked written without the lock, said in one note line once per folder; an error inside lets every lock "
          f"go; a file where the lock's folder belongs refused as Unwritable (EEXIST); "
          f"{'a project folder this user may not write refused as Unwritable, nothing taken or made; ' if unwritable else ''}"
          + (f"a project path that cannot be looked at -- a file in it, a loop of links, a name too long"
             f"{', a parent this user may not search' if looked == 'all' else ''} -- refused as Unwritable, never taken "
             f"for a folder that is not there; " if looked else "")
          + f"make_folder makes a project's folder with its parents and refuses one it cannot make as Unwritable (a file "
          f"in its place{', a parent this user may not write' if made else ''}); "
          f"the access repair fits the system; the refusals are no OSError or ValueError; busy_exit says one line and "
          f"returns 75; a check that breaks shows its traceback; probe answers no_lock_file (making nothing), free, "
          f"held by a spawned process, cannot_lock with the OS's reason, and cannot_lock naming a folder at the lock "
          f"file's path or a file at its folder's, keeping nothing")
    return 0


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: write_lock.py --selftest  (a library: the method's writers call it)", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
