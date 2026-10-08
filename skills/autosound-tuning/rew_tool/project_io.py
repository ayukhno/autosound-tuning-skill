"""How the method writes, and reads, the files it owns (skill #135, #136; audit T-8, T-9, T-14, T-17, T-21, K-2).

WRITES go through `atomic_write_text` / `atomic_write_json` / `atomic_write_bytes`, which share one path: a temp file
with a name no other writer uses, opened exclusively, written, flushed and fsynced, then moved over the target in one
`os.replace`, and the folder fsynced (POSIX), so the move survives a power loss. A reader sees the old file or the
new one, never half of either; two writers never share a temp file. On POSIX a private file (`mode`) is private from
its first byte: the temp is created with that mode. A Windows `PermissionError` on the move (an editor, an antivirus
scan or TCC holding the target open) is retried for under a second.

A file whose NAME is the claim -- a ledger version -- is made by `create_exclusive`: the same temp, linked into place,
never over a file that is there. `append_line` appends one line, fsynced, and after a torn last line starts on a
fresh one.

READS: `read_json` tells a file that is not there from one that is there and cannot be read (audit K-2). Absent is
the caller's default, the one quiet case -- a fresh project has no state yet. Empty, cut off (inside a character
too), not UTF-8, not JSON, the wrong top-level type, a directory, a file that cannot be opened: each raises
`Unreadable`, naming the file and the repair -- the caller's for damaged contents, its own where the file may be whole
(held open, a permission, a folder in its place: `cannot_open`, the repair its cause allows).
Read as empty instead, such a file was written over with an empty one by the next write. `Unreadable` is
neither an `OSError` nor a `ValueError`, so the `except (OSError, ValueError)` blocks that read "empty" do not catch
it, and it is matched by its attribute `is_unreadable`, never by its class: a copy of this module loaded under
another name has a class of its own. `restore_line` and `reencode_line` are the repairs a caller names for a project
file. A file a newer method wrote (`newer_schema`) is refused by its reader too, with `UPDATE_THE_METHOD` (T-21).

Stdlib only. Loaded by path like every sibling: `_siblings().load("project_io.py")`.

    python3 project_io.py --selftest
"""
import codecs
import errno
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


def _discard(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _sync_folder(path):
    """fsync the folder `path` is in (POSIX), so that a move or a link into it, or a file just made there, survives a
    power loss (F M-6): until the folder is on the disk, the move can be undone, the file back at its old contents.
    Windows has no folder fsync and is not asked for one. Best effort: a filesystem that refuses a folder's fsync (some
    network shares) changes nothing about the write, which has landed -- raising here would report it as failed."""
    if os.name == "nt":
        return
    try:
        fd = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _create(path, data, mode=None):
    """Create `path`, which must not exist, holding `data`, flushed and fsynced: the first step of a replace
    (`atomic_write_bytes`) and of an exclusive create (`create_exclusive`).

    `FileExistsError` when the name is taken, the file there untouched. A failure once the name is created removes it
    again: a failed write leaves no name behind. `mode`: `atomic_write_bytes`.
    """
    private = mode is not None and os.name != "nt"
    # O_BINARY (Windows; 0 elsewhere): a descriptor from `os.open` is otherwise in the C runtime's text mode, which
    # turns each "\n" written into "\r\n": a copy of bytes would not be the original's, a text with the platform's
    # ending would get "\r\r\n", and `newline=""` would not keep the text's own. `open(path, "w")` opens binary
    # underneath too; so does `tempfile.mkstemp`.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), mode if private else 0o666)
    try:
        with io.open(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if private:
            os.chmod(path, mode)
    except BaseException:
        _discard(path)
        raise


def _encoded(text, newline):
    """`text` as the bytes a UTF-8 text file opened with `newline` writes (`open()`'s rule): None writes the
    platform's line ending, "" and "\\n" keep the text's own, "\\r" and "\\r\\n" write that. A text UTF-8 cannot carry
    is refused here, before anything is written."""
    if newline not in (None, "", "\n", "\r", "\r\n"):
        raise ValueError(f"illegal newline value: {newline!r}")
    ending = os.linesep if newline is None else newline
    if ending not in ("", "\n"):
        text = text.replace("\n", ending)            # what a text file opened with this `newline` writes
    return text.encode("utf-8")


def atomic_write_bytes(path, data, *, mode=None, makedirs=False):
    """Write `data` to `path` so that no reader ever sees a half-written file: the one path every writer here takes.

    `mode` (POSIX only) is the temp's mode from its creation, so a private file -- a key -- is never readable by
    others, not even while it is being written; it is set again before the move, since the umask may have narrowed it.
    Without a mode the file gets the umask's default, as `open(path, "w")` gave it. After the move the folder is
    fsynced (POSIX), so the move survives a power loss (`_sync_folder`).
    """
    if makedirs:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = _temp_name(path)
    _create(tmp, data, mode)
    try:
        _replace(tmp, path)
    except BaseException:
        _discard(tmp)
        raise
    _sync_folder(path)


def atomic_write_text(path, text, *, newline=None, mode=None, makedirs=False):
    """Write `text` to `path` so that no reader ever sees a half-written file: UTF-8, through `atomic_write_bytes`.

    `newline` is `open()`'s: None writes the platform's line ending -- what `open(path, "w")` did at every site this
    replaces -- while "" and "\\n" keep the text's own, and "\\r" or "\\r\\n" write that. `mode`: `atomic_write_bytes`.
    A text UTF-8 cannot carry is refused before anything is written.
    """
    atomic_write_bytes(path, _encoded(text, newline), mode=mode, makedirs=makedirs)


def atomic_write_json(path, data, *, indent=2, sort_keys=False, ensure_ascii=False, trailing_newline=False,
                      newline=None, mode=None, makedirs=False):
    """`json.dumps(data, ...)` through `atomic_write_text` -- the same text `json.dump` wrote at each old site."""
    text = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    if trailing_newline:
        text += "\n"
    atomic_write_text(path, text, newline=newline, mode=mode, makedirs=makedirs)


def create_exclusive(path, text, *, newline=None):
    """Create `path` holding `text`, or raise `FileExistsError` -- never overwrite (audit T-9).

    For files whose NAME is the claim (a ledger version `v_NNN.json`): of two writers that picked one number, one
    wins and the other is told, the file there left as it was. The text becomes bytes as in `atomic_write_text`
    (UTF-8, `newline` as `open()`'s) and goes into a temp of its own, fsynced, which is then LINKED into place, so the
    name never appears empty or half-written. Where the filesystem cannot hard-link (FAT, some network shares), the
    name is created exclusively and written in place -- a reader can then meet it mid-write for an instant; said, not
    hidden -- and a write that fails there removes the name again. The temp is removed afterwards, best effort: one a
    remove could not take (a Windows scanner holding it) stays beside the version with its bytes -- a second link to
    it, or a copy where links are refused -- under a `.tmp` name no lister reads.
    """
    data = _encoded(text, newline)
    tmp = _temp_name(path)
    _create(tmp, data)
    try:
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise
        except OSError:
            _create(path, data)                 # no hard links here: the name itself, exclusively, in place
    finally:
        _discard(tmp)
    _sync_folder(path)                          # the new name survives a power loss (F M-6)


def append_line(path, line):
    """Append `line` and a newline. If the file's last write was cut before its newline, start on a fresh line, so
    the torn line stays one skipped line and the new one is read (audit T-14).

    Text mode, UTF-8: the line ending is the platform's, as the `open(path, "a")` this replaces wrote it. The append
    itself is a plain one and takes no lock of its own: its one caller, `process.py`'s journal append, runs inside a
    writer that holds the project's writer lock (`write_lock.py`, #141). The line is fsynced, and the folder too when
    the append made the file (F M-6): an event survives a power loss once this returns.

    A journal that is there and cannot be opened raises `Unreadable` (`cannot_open`), nothing appended (F M-7): it
    was a bare `PermissionError`, which a command reports as a bug. An append refused once the file is open -- a
    read-only file, a full disk -- raises its `OSError`, for the caller to say.
    """
    torn, made = False, False
    try:
        with open(path, "rb") as f:
            if f.seek(0, os.SEEK_END):
                f.seek(-1, os.SEEK_END)
                torn = f.read(1) != b"\n"
    except FileNotFoundError:
        made = True
    except OSError as exc:
        raise cannot_open(path, exc) from exc
    with open(path, "a", encoding="utf-8") as f:
        f.write(("\n" if torn else "") + line + "\n")
        f.flush()
        os.fsync(f.fileno())
    if made:
        _sync_folder(path)


class Unreadable(Exception):
    """A file that is THERE and cannot be read (K-2). Deliberately neither a `ValueError` nor an `OSError`: the method
    has dozens of `except (OSError, ValueError)` blocks that would turn it back into "empty". Matched by the attribute
    `is_unreadable` -- module copies make `except Unreadable` unreliable."""
    is_unreadable = True

    def __init__(self, path, reason, repair=None):
        self.path, self.reason, self.repair = path, reason, repair
        super().__init__(f"{path} {reason}" + (f" -- {repair}" if repair else ""))


#: The repairs `read_json` says itself, whatever the caller's: the file may be whole there (Windows refusing an open
#: while another program holds it, a permission, a cloud placeholder; a folder where the file belongs), and the
#: caller's repair for damaged contents -- an older copy restored over it -- would replace a good file.
_REPAIR_HELD = "close what holds it (an editor, a sync client, another tool) and run again"
_REPAIR_FOLDER = "move the folder aside"
#: Where nothing can hold a file against its reader -- POSIX has no mandatory locks -- "close what holds it" cannot be
#: followed (H minor 3): a permission refuses it, a file stands where a folder of its path belongs, or the disk does.
_REPAIR_PERMISSION = "this user may not open it: give it access (its owner and mode, `ls -l`) and run again"
_REPAIR_WRITE_PERMISSION = "this user may not write it: give it access (its owner and mode, `ls -l`) and run again"
_REPAIR_NOT_A_FOLDER = "a file stands where a folder of its path belongs: move that file aside"
_REPAIR_RETRY = "check the disk and the folder it is in (a network share, a sync client's folder) and run again"


def repair_for(exc, writing=False):
    """The repair for `exc`, an `OSError` met opening or writing one of the method's files: the one its cause allows
    (H minor 3, m2). A file standing where a folder of the path belongs, and a folder where the file belongs, are said
    as such everywhere. A permission refusal (EACCES, EPERM) is, on Windows, most often another program holding the
    file -- a sharing violation reaches `open()` as a plain EACCES -- so it is told to close what holds it; on POSIX,
    where nothing holds a file against a reader, it is a permission, to read or (`writing`) to write. Anything else --
    a full disk, the disk's own error -- is the disk's, on both: no holder causes it."""
    if exc.errno == errno.ENOTDIR:
        return _REPAIR_NOT_A_FOLDER
    if exc.errno == errno.EISDIR:
        return _REPAIR_FOLDER
    if exc.errno in (errno.EACCES, errno.EPERM):
        if os.name == "nt":
            return _REPAIR_HELD
        return _REPAIR_WRITE_PERMISSION if writing else _REPAIR_PERMISSION
    return _REPAIR_RETRY


def cannot_open(path, exc):
    """The `Unreadable` to raise for `path`, which `exc` -- an `OSError` other than `FileNotFoundError` -- refused to
    open: a folder in its place said as one, anything else with the repair its cause allows (`repair_for`). For a
    reader that opens one of the method's files itself (`process.py`'s journal), as `read_json` and `append_line` do."""
    if os.path.isdir(path):
        return Unreadable(path, "is a directory, not a file", _REPAIR_FOLDER)
    return Unreadable(path, f"cannot be opened ({exc})", repair_for(exc))


def cannot_append(path, exc):
    """The `Unreadable` to raise for `path`, which reads and refused the append `exc` names (m4): `cannot be appended to
    (...)`, with a write's repair -- a read-only journal is not one that "cannot be opened". One wording for one cause,
    whether the look before a state write or the append itself meets it."""
    return Unreadable(path, f"cannot be appended to ({exc})", repair_for(exc, writing=True))


#: What a refusal calls a JSON value: JSON's words, not Python's type names ("null", not "NoneType").
_JSON_KINDS = ((bool, "true or false"), (dict, "an object"), (list, "an array"), (str, "a string"),
               ((int, float), "a number"), (type(None), "null"))


def cut_inside_a_character(raw):
    """True when the only fault UTF-8 finds in `raw` is an unfinished last character: a write cut inside a multi-byte
    character, not text in another code page. Asked of bytes that did not decode. An incremental decoder holds such
    an end back instead of raising; a byte in another code page is wrong before the end, and it raises there."""
    try:
        codecs.getincrementaldecoder("utf-8")().decode(raw)
    except UnicodeDecodeError:
        return False
    return True


def _json_kind(kind):
    """`kind`, a type or a tuple of them, in JSON's words."""
    if isinstance(kind, tuple):
        return " or ".join(_json_kind(k) for k in kind)
    for types, name in _JSON_KINDS:
        if kind in (types if isinstance(types, tuple) else (types,)):
            return name
    return getattr(kind, "__name__", str(kind))


def read_json(path, default=None, *, want=dict, repair=None, repair_encoding=None):
    """The JSON in `path`; `default` if there is no such file; `Unreadable` for anything else that cannot be read.

    Absent is the one quiet case: a fresh project has no state yet. Empty, truncated, not UTF-8, not JSON, the wrong
    top-level type (`want`: a type or a tuple of them; None takes any), a directory, a file that cannot be opened --
    each raises `Unreadable` naming the file and its repair. `repair` is the caller's, for damaged contents; a file
    that is not UTF-8 gets `repair_encoding` when given -- a file in another code page is mended by re-encoding it, not
    by an older copy -- but one cut inside its last character is cut off, and gets `repair` (F M-2). A file that
    cannot be opened, and a directory, get their own (`cannot_open`: the repair its cause allows, `_REPAIR_FOLDER`):
    the file may be whole there. A UTF-8 BOM is read: it is an editor's marker, not damage. The bytes are decoded
    here, so the platform's code page plays no part.
    """
    if os.path.isdir(path):
        raise Unreadable(path, "is a directory, not a file", _REPAIR_FOLDER)
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return default
    except OSError as exc:
        raise cannot_open(path, exc) from exc
    if not raw.strip():
        raise Unreadable(path, "is empty -- a write was cut off", repair)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        if cut_inside_a_character(raw):
            # UTF-8 up to an unfinished last character (F M-2): a write cut off, not another code page --
            # `repair-encoding` finds no page that makes JSON of it, so the caller's repair for damage is the one.
            raise Unreadable(path, "is cut off inside a character -- a write was cut off", repair) from exc
        raise Unreadable(path, f"is not UTF-8 (byte {exc.start})", repair_encoding or repair) from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise Unreadable(path, f"is not valid JSON ({exc})", repair) from exc
    if want is not None and not isinstance(data, want):
        raise Unreadable(path, f"holds {_json_kind(type(data))} where {_json_kind(want)} belongs", repair)
    return data


#: What a file a newer method wrote is answered with (#136, audit T-21): this copy cannot read it, and a write from
#: here would write it down to this copy's schema. The way out is a newer method, by any of its three routes.
UPDATE_THE_METHOD = "update the method: /autosound-tuning:setup, the installer, or TCC's «Оновити Скіл»"


def newer_schema(data, reads):
    """The `schema_version` of `data` when it is an int above `reads` -- a file a newer method wrote -- else None.

    Only that: a bool, a text, a float, a missing key or a value that is not an object is no claim to be newer, and
    each reader judges those as it did. An older version is the migration's business, not this one's."""
    found = data.get("schema_version") if isinstance(data, dict) else None
    if isinstance(found, int) and not isinstance(found, bool) and found > reads:
        return found
    return None


def restore_line(path):
    """The repair for a project file whose contents are damaged: its last committed copy back (a project is a git
    repository, hub #199). For `read_json`'s `repair`."""
    folder, name = os.path.split(os.path.abspath(path))
    return f"restore the last committed copy: git -C {folder} checkout HEAD -- {name}"


def reencode_line(project_dir):
    """The repair for a project file written in another code page: `contract.py repair-encoding`, which shows what each
    candidate page makes it say and rewrites it as UTF-8. For `read_json`'s `repair_encoding`."""
    contract_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract.py")
    return f"rewrite it as UTF-8: python3 {contract_py} repair-encoding {os.path.abspath(project_dir)}"


def set_aside_line(project_dir):
    """The way out for journal lines no code page makes JSON of (#134, R56): `contract.py repair-encoding --set-aside`,
    which moves them, bytes kept and numbered, into `<journal>.set-aside` -- no repair can rewrite them."""
    contract_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract.py")
    return (f"set such lines aside, bytes kept: python3 {contract_py} repair-encoding {os.path.abspath(project_dir)} "
            f"--set-aside")


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────────────────

#: What this run of the selftest could not check on this machine, `(case, why)`, said one line each above its OK line
#: (the final review's m-5): an OK line claims only what ran.
_NOT_CHECKED_HERE = []


def _mode_refuses(case):
    """True where a file's mode refuses this user -- POSIX, not root -- so `case`, which needs that, runs. Elsewhere it
    is recorded in `_NOT_CHECKED_HERE` and skipped: root opens a mode-0 file all the same, and Windows keeps no POSIX
    mode."""
    if os.name == "posix" and os.geteuid() != 0:
        return True
    _NOT_CHECKED_HERE.append((case, "run as root, whom no file mode refuses" if os.name == "posix" else
                              "Windows keeps no POSIX mode"))
    return False


def _scratch():
    import tempfile
    return tempfile.mkdtemp(prefix="autosound_project_io_")


def _drop(folder):
    import shutil
    shutil.rmtree(folder, ignore_errors=True)


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _moved_into_place(label, path, call):
    """For a writer's own selftest (CONTRACT.md item 8; the final review's I-1): `call` replaces `path`, a file that is
    there, and must do it through this module's move -- the one way a reader never meets half of it.

    Run twice. First with the move onto `path` failing, as a pulled disk or a Windows holder past the retries would:
    the writer must raise, the file keep its bytes, and no temp of it be left. A move onto any other file goes through,
    so a writer that writes another file first is judged on this one. Then watched, the move working: when the move
    comes the file still holds its old bytes -- nothing was written into it first -- and the file moved over it holds
    every byte it ends with. A writer gone back to writing in place does neither: it writes with its move failing, and
    its file is never moved. Returns the failures, one line each, `label` first; empty when the writer holds."""
    target = os.path.abspath(path)
    folder, base = os.path.split(target)
    real = os.replace
    failures, moves = [], []

    def failing(src, dst):
        if os.path.abspath(dst) == target:
            raise OSError(errno.EIO, "the move failed (a fault injected here)", dst)
        return real(src, dst)

    def watching(src, dst):
        if os.path.abspath(dst) == target:
            moves.append((_read_bytes(target), _read_bytes(src)))
        return real(src, dst)

    before, names = _read_bytes(target), set(os.listdir(folder))
    os.replace = failing
    try:
        call()
        raised = False
    except Exception:  # noqa: BLE001 -- any refusal will do; the file and its folder are what is judged
        raised = True
    finally:
        os.replace = real
    if not raised:
        failures.append(f"{label}: wrote with its move failing -- in place")
    if _read_bytes(target) != before:
        failures.append(f"{label}: with its move failing, the file's bytes changed")
    left = sorted(n for n in set(os.listdir(folder)) - names if n.startswith(base + ".") and n.endswith(".tmp"))
    if left:
        failures.append(f"{label}: with its move failing, a temp was left: {left}")
    before = _read_bytes(target)
    os.replace = watching
    try:
        call()
    except Exception as exc:  # noqa: BLE001 -- said as this writer's failure, beside the others
        return failures + [f"{label}: with its move working, the write failed: {type(exc).__name__}: {exc}"]
    finally:
        os.replace = real
    if not moves:
        failures.append(f"{label}: the file was never moved into place -- written in place")
    elif moves[0][0] != before:
        failures.append(f"{label}: the file changed before its move -- a reader could meet half of it")
    elif moves[-1][1] != _read_bytes(target):
        failures.append(f"{label}: the file holds bytes its move did not bring -- written after the move")
    return failures


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


def _check_binary_temp():
    """#135's Windows half (the final review's I-2): every temp is opened binary -- `O_BINARY`, Windows' flag; POSIX
    has none and needs none -- so a byte written is the byte read back. A descriptor `os.open` gives is otherwise in
    the C runtime's text mode, which turns each "\\n" written into "\\r\\n": a copy of bytes would not be the
    original's, a text with the platform's ending would get "\\r\\r\\n", and `newline=""` would not keep the text's
    own. Two halves: each create asks for the flag -- on POSIX one is lent to `os` for the look and taken off before
    the real open, so the line is held here too -- and what each writer wrote reads back byte for byte, the half that
    bites where the flag is real: CI runs this selftest on Windows."""
    d = _scratch()
    real_open = os.open
    had = hasattr(os, "O_BINARY")
    flag = os.O_BINARY if had else 0x8000           # Windows' value, lent where the platform has none
    asked = []

    def recording(path, flags, *args, **kwargs):
        if flags & os.O_CREAT:                       # a create; the folder's own open for its fsync is not one
            asked.append((os.path.basename(path), bool(flags & flag)))
        return real_open(path, flags if had else flags & ~flag, *args, **kwargs)
    data = b"a\nb\r\nc\rd\x1a\n\x00\xff end\n"
    try:
        if not had:
            os.O_BINARY = flag
        os.open = recording
        try:
            atomic_write_bytes(os.path.join(d, "bytes.bin"), data)
            create_exclusive(os.path.join(d, "v_001.json"), "one\ntwo\r\nthree\n", newline="")
            atomic_write_text(os.path.join(d, "lf.txt"), "x\ny\n", newline="\n")
            atomic_write_text(os.path.join(d, "crlf.txt"), "x\ny\n", newline="\r\n")
        finally:
            os.open = real_open
            if not had:
                del os.O_BINARY
        assert len(asked) >= 4 and all(binary for _name, binary in asked), \
            f"a temp opened without O_BINARY -- text mode on Windows: {asked}"
        for name, want in (("bytes.bin", data), ("v_001.json", b"one\ntwo\r\nthree\n"), ("lf.txt", b"x\ny\n"),
                           ("crlf.txt", b"x\r\ny\r\n")):
            got = _read_bytes(os.path.join(d, name))
            assert got == want, f"{name}: written {want!r}, read back {got!r}"
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
    every `project.json` private). Windows keeps no POSIX mode: there it is said, one line above the OK line."""
    if os.name == "nt":
        _NOT_CHECKED_HERE.append(("a private file's mode from its first byte", "Windows keeps no POSIX mode"))
        return
    import stat
    d = _scratch()
    real_fsync, real_replace = os.fsync, os.replace
    umask = os.umask(0)
    os.umask(umask)
    at_fsync, at_replace = [], []

    def fsync(fd):                               # the temp as it is when its bytes are all in it
        st = os.fstat(fd)
        if not stat.S_ISDIR(st.st_mode):         # the folder's own fsync after the move is not the temp's
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


def _check_create_exclusive():
    """Audit T-9: `create_exclusive` makes the file with the bytes `open(path, "w")` wrote -- the platform's line
    ending, the text's own with `newline=""` -- and a second create of that name raises `FileExistsError`, the first
    file as it was; no temp is left either way -- but where the temp's own remove is refused (a scanner holding it),
    which leaves it beside the version on purpose, a `*.tmp` no lister reads. Where hard links are refused
    (`os.link` raising EPERM, as on FAT), the name is still created exclusively, written in place, and a write that
    fails there leaves no name behind."""
    import errno
    d = _scratch()
    real_link, real_fsync, real_remove = os.link, os.fsync, os.remove
    refused = []

    def no_links(src, dst):                      # FAT, some network shares: the filesystem refuses a hard link
        refused.append(dst)
        raise OSError(errno.EPERM, "Operation not permitted", dst)
    try:
        text = '{\n  "note": "нуль — 45°",\n  "version": "v_002"\n}'
        ref = os.path.join(d, "ref.json")
        with open(ref, "w", encoding="utf-8") as f:            # how a ledger version was written before #135
            f.write(text)
        for label, link in (("linked", real_link), ("no-links", no_links)):
            sub = os.path.join(d, label)
            os.makedirs(sub)
            path, own = os.path.join(sub, "v_002.json"), os.path.join(sub, "own.txt")
            os.link = link
            try:
                create_exclusive(path, text)
                assert _read_bytes(path) == _read_bytes(ref), (label, _read_bytes(path)[:80])
                try:
                    create_exclusive(path, "the second writer's version")
                except FileExistsError:
                    pass
                else:
                    raise AssertionError(f"{label}: a second create of one name was taken")
                assert _read_bytes(path) == _read_bytes(ref), f"{label}: the second create changed the first's file"
                create_exclusive(own, "a\r\nb\n", newline="")
                assert _read_bytes(own) == b"a\r\nb\n", (label, _read_bytes(own))
            finally:
                os.link = real_link
            assert sorted(os.listdir(sub)) == ["own.txt", "v_002.json"], (label, os.listdir(sub))   # no temp left
        assert len(refused) == 3, f"the fallback was reached {len(refused)} times, not 3"
        # A write that fails in place -- a full disk at its fsync -- leaves no name behind, and no temp.
        sub = os.path.join(d, "failing")
        os.makedirs(sub)
        syncs = []

        def full_at_the_second(fd):              # the temp's fsync passes; the one in place fails
            syncs.append(fd)
            if len(syncs) == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
            real_fsync(fd)
        os.link, os.fsync = no_links, full_at_the_second
        try:
            create_exclusive(os.path.join(sub, "v_003.json"), text)
        except OSError as exc:
            assert exc.errno == errno.ENOSPC, exc
        else:
            raise AssertionError("a create that failed in place was reported as written")
        finally:
            os.link, os.fsync = real_link, real_fsync
        assert os.listdir(sub) == [], os.listdir(sub)
        # Removing the temp is best effort: refused (a Windows scanner holding it), the version is created all the
        # same, and the temp stays beside it with the version's bytes -- a second link to it -- under a name no
        # lister reads.
        sub = os.path.join(d, "held")
        os.makedirs(sub)

        def held(p):
            raise PermissionError(13, "held by a scanner", p)
        os.remove = held
        try:
            create_exclusive(os.path.join(sub, "v_004.json"), text)
        finally:
            os.remove = real_remove
        left = sorted(os.listdir(sub))
        assert len(left) == 2 and left[0] == "v_004.json" and left[1].endswith(".tmp"), left
        assert _read_bytes(os.path.join(sub, left[0])) == _read_bytes(os.path.join(sub, left[1])) == _read_bytes(ref)
    finally:
        os.link, os.fsync, os.remove = real_link, real_fsync, real_remove
        _drop(d)


def _check_append_line():
    """Audit T-14: `append_line` writes what `open(path, "a")` wrote -- the line and the platform's line ending, into
    a new file, an empty one and after a whole last line ("\\r\\n" too) -- and after a torn last line (no newline: a
    write cut short) it starts on a fresh line first: the torn line stays one line a reader skips, the new one whole."""
    d = _scratch()
    try:
        path, ref = os.path.join(d, "journal.jsonl"), os.path.join(d, "ref.jsonl")

        def old_append(target, text):                       # how process.py appended before #135
            with open(target, "a", encoding="utf-8") as f:
                f.write(text)
        lines = ['{"at": "2026-10-07T00:00:00+00:00", "type": "user_decision", "question": "нуль → 45°?"}',
                 '{"type": "session_start"}']
        for line in lines:                                 # a new file, then after a whole last line
            append_line(path, line)
            old_append(ref, line + "\n")
            assert _read_bytes(path) == _read_bytes(ref), _read_bytes(path)
        torn = '{"at": "2026-10-07T00:00:01+00:00", "type": "user_dec'
        old_append(path, torn)                             # a write cut before its newline
        old_append(ref, torn)
        append_line(path, '{"type": "after"}')
        old_append(ref, '\n{"type": "after"}\n')
        assert _read_bytes(path) == _read_bytes(ref), _read_bytes(path)
        with open(path, encoding="utf-8") as f:
            read = [line.rstrip("\n") for line in f]
        assert read == lines + [torn, '{"type": "after"}'], read
        for name, start in (("empty.jsonl", b""), ("crlf.jsonl", b'{"a": 1}\r\n')):
            target, target_ref = os.path.join(d, name), os.path.join(d, "ref-" + name)
            for f_ in (target, target_ref):
                with open(f_, "wb") as f:
                    f.write(start)
            append_line(target, "{}")
            old_append(target_ref, "{}\n")
            assert _read_bytes(target) == _read_bytes(target_ref), (name, _read_bytes(target))
    finally:
        _drop(d)


def _check_read_json():
    """K-2's matrix (#136): no file is the default; a file that is there and cannot be read -- empty, blank, cut off,
    a cp1251 byte, an array or null where an object belongs, a directory -- raises `Unreadable` naming the file and
    the repair it was given (the encoding repair for the code page). A UTF-8 BOM is read. `Unreadable` is neither an
    `OSError` nor a `ValueError`: the `except (OSError, ValueError)` blocks that read "empty" do not catch it."""
    d = _scratch()
    try:
        assert not issubclass(Unreadable, (OSError, ValueError)), Unreadable.__mro__
        path = os.path.join(d, "process-state.json")
        absent = object()
        assert read_json(path, absent) is absent and read_json(path) is None, "an absent file is not its default"
        # A write cut inside a multi-byte character (F M-2) is cut off, not another code page: its repair is the
        # caller's older copy -- `repair-encoding` finds no page that makes JSON of it, a dead end.
        cut = '{"schema_version": 3, "note": "тест'.encode("utf-8")[:-1]     # after the first byte of the last "т"
        for label, raw in (("empty", b""), ("blank", b" \r\n\t"),
                           ("truncated", b'{"schema_version": 3, "pla'),
                           ("cp1251", '{"schema_version": 3, "note": "тест"}'.encode("cp1251")),
                           ("cut inside a character", cut), ("BOM, then cut inside a character", b"\xef\xbb\xbf" + cut),
                           ("an array", b"[1, 2]"), ("null", b"null"), ("not JSON", b"schema_version: 3")):
            with open(path, "wb") as f:
                f.write(raw)
            try:
                read_json(path, {}, repair="REPAIR", repair_encoding="RE-ENCODE")
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                assert getattr(exc, "is_unreadable", False), (label, repr(exc))
                repair = "RE-ENCODE" if label == "cp1251" else "REPAIR"
                assert (exc.path, exc.repair) == (path, repair), (label, exc.path, exc.repair)
                assert str(exc).startswith(path + " ") and str(exc).endswith(" -- " + repair), (label, str(exc))
                if "cut inside" in label:
                    assert exc.reason == "is cut off inside a character -- a write was cut off", (label, exc.reason)
                elif label == "cp1251":
                    assert exc.reason.startswith("is not UTF-8 (byte "), (label, exc.reason)
            else:
                raise AssertionError(f"{label}: read as JSON")
            assert _read_bytes(path) == raw, f"{label}: the read changed the file"
        with open(path, "wb") as f:
            f.write(b"[1, 2]")
        assert read_json(path, want=None) == [1, 2] and read_json(path, want=list) == [1, 2], "want= is the type"
        with open(path, "wb") as f:
            f.write(b"\xef\xbb\xbf" + json.dumps({"note": "нуль"}, ensure_ascii=False).encode("utf-8"))
        assert read_json(path) == {"note": "нуль"}, "a UTF-8 BOM is an editor's marker, not damage"
        # A file that cannot be OPENED, and a folder where the file belongs, may hold nothing wrong (Windows refusing
        # an open while another program holds the file, a permission, a cloud placeholder): each is told its own
        # repair, never the caller's -- an older copy restored over a good file is the damage it would cause. Which
        # one is the cause's (H minor 3): "close what holds it" only where something can hold a file, Windows; on
        # POSIX nothing holds a file against a reader, and a permission or a file standing where a folder of the path
        # belongs is told what it is.
        real_name = os.name
        for platform, error, repair in (
                ("nt", PermissionError(13, "The process cannot access the file because it is being used by another "
                                           "process"), _REPAIR_HELD),
                ("posix", PermissionError(13, "Permission denied"), _REPAIR_PERMISSION),
                ("posix", NotADirectoryError(20, "Not a directory"), _REPAIR_NOT_A_FOLDER),
                ("nt", NotADirectoryError(20, "Not a directory"), _REPAIR_NOT_A_FOLDER),
                ("posix", OSError(5, "Input/output error"), _REPAIR_RETRY),
                # m2: on Windows too, only what a holder causes is told to close it -- a sharing violation reaches
                # `open()` as EACCES; a full disk or the disk's own error is the disk's.
                ("nt", OSError(28, "No space left on device"), _REPAIR_RETRY),
                ("nt", OSError(5, "Input/output error"), _REPAIR_RETRY)):
            def refused(p, *args, error=error, **kwargs):
                raise type(error)(error.errno, error.strerror, p)
            globals()["open"], os.name = refused, platform      # read_json's own open() resolves here first
            try:
                read_json(path, {}, repair="REPAIR", repair_encoding="RE-ENCODE")
            except Exception as exc:  # noqa: BLE001
                assert getattr(exc, "is_unreadable", False) and exc.reason.startswith("cannot be opened ("), \
                    (platform, repr(exc))
                assert exc.repair == repair and str(exc).endswith(" -- " + repair), (platform, error, str(exc))
            else:
                raise AssertionError("a file that could not be opened was read")
            finally:
                del globals()["open"]
                os.name = real_name
        # A write's repair (m2, m4): a POSIX permission to WRITE is not "may not open it", and a full disk is the disk's
        # on both platforms; a Windows EACCES or EPERM, a holder's, is told to close what holds it.
        try:
            os.name = "posix"
            assert repair_for(PermissionError(13, "Permission denied"), writing=True) == _REPAIR_WRITE_PERMISSION
            assert repair_for(OSError(28, "No space left on device"), writing=True) == _REPAIR_RETRY
            os.name = "nt"
            assert repair_for(PermissionError(13, "Access is denied"), writing=True) == _REPAIR_HELD
            assert repair_for(PermissionError(1, "Operation not permitted"), writing=True) == _REPAIR_HELD
            assert repair_for(OSError(28, "No space left on device"), writing=True) == _REPAIR_RETRY
        finally:
            os.name = real_name
        appended = cannot_append(path, PermissionError(13, "Permission denied", path))
        assert getattr(appended, "is_unreadable", False) and appended.reason.startswith("cannot be appended to ("), \
            repr(appended)
        if os.name != "nt":                      # the same two, met for real: POSIX gives them their own errno
            through = os.path.join(path, "x.json")                     # `path` is a file: a folder of the path
            try:
                read_json(through, {}, repair="REPAIR")
            except Exception as exc:  # noqa: BLE001
                assert getattr(exc, "is_unreadable", False) and exc.repair == _REPAIR_NOT_A_FOLDER, repr(exc)
            else:
                raise AssertionError("a path through a file was read as no file")
        if _mode_refuses("a file this user may not open (mode 0)"):
            os.chmod(path, 0)
            try:
                read_json(path, {}, repair="REPAIR")
            except Exception as exc:  # noqa: BLE001
                assert getattr(exc, "is_unreadable", False) and exc.repair == _REPAIR_PERMISSION, repr(exc)
            else:
                raise AssertionError("a file this user may not open was read")
            finally:
                os.chmod(path, 0o600)
        os.remove(path)
        os.makedirs(path)
        try:
            read_json(path, {}, repair="REPAIR")
        except Exception as exc:  # noqa: BLE001
            # Said as a directory everywhere: opening one raises IsADirectoryError on POSIX, PermissionError on Windows.
            assert getattr(exc, "is_unreadable", False) and exc.reason == "is a directory, not a file", repr(exc)
            assert exc.repair == _REPAIR_FOLDER and str(exc) == f"{path} {exc.reason} -- {_REPAIR_FOLDER}", str(exc)
        else:
            raise AssertionError("a directory was read as JSON")
    finally:
        _drop(d)


def _check_newer_schema():
    """A file a newer method wrote is told by its `schema_version`, an int above the one this copy reads (#136, audit
    T-21) -- not a bool, a text, a float, an equal or lower number, a missing key, or a value that is not an object.
    The answer names the three ways to a newer method; the repair lines name the file and the command."""
    assert newer_schema({"schema_version": 4}, 3) == 4, newer_schema({"schema_version": 4}, 3)
    for data in ({"schema_version": 3}, {"schema_version": 1}, {"schema_version": True}, {"schema_version": "4"},
                 {"schema_version": 4.0}, {"schema_version": None}, {}, [{"schema_version": 4}], None, "4"):
        assert newer_schema(data, 3) is None, data
    assert newer_schema({"schema_version": True}, 0) is None, "a bool is no version, though True > 0"
    for route in ("update the method", "/autosound-tuning:setup", "the installer", "«Оновити Скіл»"):
        assert route in UPDATE_THE_METHOD, (route, UPDATE_THE_METHOD)
    folder = os.path.abspath(os.path.join("car", "state"))
    assert restore_line(os.path.join("car", "state", "seals.json")) == \
        f"restore the last committed copy: git -C {folder} checkout HEAD -- seals.json", restore_line("x")
    contract_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract.py")
    assert reencode_line("car") == f"rewrite it as UTF-8: python3 {contract_py} repair-encoding " \
                                   f"{os.path.abspath('car')}", reencode_line("car")


def _check_durable():
    """F M-6: what landed stays landed after a power loss. On POSIX the folder is fsynced after the move -- the move
    is an entry in the folder, and until the folder is on the disk a power cut can undo it, the file back at its old
    contents -- and after an exclusive create's link; Windows has no folder fsync and is not asked for one. An appended
    journal line is fsynced, and so is the folder when the append made the file."""
    import stat
    d = _scratch()
    real_fsync, real_replace, real_link, real_name = os.fsync, os.replace, os.link, os.name
    seen = []

    def fsync(fd):
        seen.append("fsync folder" if stat.S_ISDIR(os.fstat(fd).st_mode) else "fsync file")
        real_fsync(fd)

    def replace(src, dst):
        seen.append("replace")
        real_replace(src, dst)

    def link(src, dst):
        seen.append("link")
        real_link(src, dst)
    # A folder cannot be opened for its fsync on Windows: there only the Windows half is asked.
    platforms = ("nt",) if os.name == "nt" else ("posix", "nt")
    try:
        os.fsync, os.replace, os.link = fsync, replace, link
        for platform in platforms:
            sub = os.path.join(d, platform)
            os.makedirs(sub)
            folder = ["fsync folder"] if platform != "nt" else []
            os.name = platform
            try:
                del seen[:]
                atomic_write_json(os.path.join(sub, "x.json"), {"v": 1})
                assert seen == ["fsync file", "replace"] + folder, ("atomic_write_json", platform, seen)
                del seen[:]
                create_exclusive(os.path.join(sub, "v_001.json"), "{}")
                assert seen == ["fsync file", "link"] + folder, ("create_exclusive", platform, seen)
                journal = os.path.join(sub, "journal.jsonl")
                del seen[:]
                append_line(journal, '{"type": "first"}')                   # the append makes the file
                assert seen == ["fsync file"] + folder, ("append_line, a new journal", platform, seen)
                del seen[:]
                append_line(journal, '{"type": "second"}')
                assert seen == ["fsync file"], ("append_line", platform, seen)
            finally:
                os.name = real_name
            assert _read_bytes(journal) == ('{"type": "first"}\n{"type": "second"}\n').replace(
                "\n", os.linesep).encode("utf-8"), _read_bytes(journal)
    finally:
        os.fsync, os.replace, os.link, os.name = real_fsync, real_replace, real_link, real_name
        _drop(d)


def _check_append_refused():
    """F M-7: a journal that is there and cannot be opened -- held by another program on Windows, a permission on
    POSIX -- is `Unreadable` from `append_line`, naming the file and its repair, never a bare `PermissionError` (which
    `process.py` reported as a bug, exit 70); nothing is appended. A refusal of the append itself is an `OSError` the
    caller says, never swallowed."""
    import builtins
    d = _scratch()
    try:
        path = os.path.join(d, "journal.jsonl")
        append_line(path, '{"type": "first"}')
        before = _read_bytes(path)
        for refused_mode in ("rb", "a"):
            def refusing(p, mode="r", *args, refused_mode=refused_mode, **kwargs):
                if mode == refused_mode:
                    raise PermissionError(13, "held by another program", p)
                return builtins.open(p, mode, *args, **kwargs)
            globals()["open"] = refusing                     # append_line's own open() resolves here first
            try:
                append_line(path, '{"type": "second"}')
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                if refused_mode == "rb":
                    assert getattr(exc, "is_unreadable", False) and exc.path == path, repr(exc)
                    assert exc.reason.startswith("cannot be opened (") and exc.repair, str(exc)
                else:
                    assert isinstance(exc, PermissionError), repr(exc)
            else:
                raise AssertionError(f"an append whose {refused_mode!r} open was refused went through")
            finally:
                del globals()["open"]
            assert _read_bytes(path) == before, (refused_mode, _read_bytes(path))
    finally:
        _drop(d)


def _check_every_writer_moves():
    """T I2: the writers CONTRACT.md item 8 names write through the move, as this module's own tests are -- not only
    that the module is atomic, but that `Project.save`, `Process._write`, the seals and `save_profile` use it. Each
    replaces a file that is there, judged by `_moved_into_place`: while the move fails, as a pulled disk or a Windows
    holder past the retries would, the writer must raise, the old file keep its bytes, and no temp be left; watched,
    the file is whole until its move. A writer that went back to writing in place does not raise, and the old bytes
    are gone -- a crash in the middle of that write leaves the file torn. The rest of item 8's writers are held by
    their own modules' selftests through the same judge."""
    sib = _siblings()
    project, process = sib.load("project.py"), sib.load("state/process.py")
    state, dsp_profile = sib.load("state/state.py"), sib.load("dsp_profile.py")
    top = _scratch()
    real = os.replace
    failures = []

    def judge(label, path, call):
        failures.extend(_moved_into_place(label, path, call))
    try:
        proj = project.Project(top)
        proj.save({"schema_version": 3, "channels": []})
        judge("project.json (Project.save)", proj.path, lambda: proj.save(proj.load()))
        proc = process.Process(os.path.join(top, "process"))
        proc.enter_phase("-1")
        judge("process-state.json (Process._write)", proc.state_path, lambda: proc.enter_phase("-1"))
        root = os.path.join(top, "state")
        state.PresetHistory(root, "SQ", project_dir=top).snapshot(state._sample_state(), note="v1")
        seals = os.path.join(root, state.SEALS_FILE)
        with open(seals, "w", encoding="utf-8") as f:            # a version with no seal: `seal` has one to write
            f.write("{}")
        judge("state/seals.json (seal_all)", seals, lambda: state.seal_all(root))
        profile = os.path.join(top, "dsp_profile.json")
        body = {"dsp_profile": {"name": "M", "vendor": "V", "groups": [
            {"id": "physical_outputs", "label": "Out", "fields": ["hp", "lp", "gain_db"]}]}}
        dsp_profile.save_profile(profile, body)
        judge("dsp_profile.json (save_profile)", profile, lambda: dsp_profile.save_profile(profile, body))
    finally:
        os.replace = real
        _drop(top)
    assert not failures, "\n  ".join(["a writer item 8 lists does not go through the move:"] + failures)


def _check_says_what_it_did_not_check():
    """A case this machine cannot make is said one line above the OK line, never passed in silence (the final review's
    m-5; the form siblings.py's selftest uses): run as root a mode-0 file opens all the same, and Windows keeps no POSIX
    mode, so a file this user may not open (`_check_read_json`) and a private file's mode from its first byte
    (`_check_private_mode`) are skipped there, each recorded for that line. Both made here: root faked for the first,
    Windows for the second."""
    saved = list(_NOT_CHECKED_HERE)
    real_euid, real_name = getattr(os, "geteuid", None), os.name
    try:
        del _NOT_CHECKED_HERE[:]
        os.geteuid = lambda: 0
        _check_read_json()
        os.name = "nt"
        _check_private_mode()
    finally:
        os.name = real_name
        if real_euid is None:
            del os.geteuid
        else:
            os.geteuid = real_euid
        said = [case for case, _why in _NOT_CHECKED_HERE]
        _NOT_CHECKED_HERE[:] = saved
    assert said == ["a file this user may not open (mode 0)", "a private file's mode from its first byte"], said


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
        # A zero is not a result until the counter moves (the final review's m-4): a reader that read nothing while the
        # writers ran -- started after them, or refused every time -- proved nothing about a torn read.
        assert reads > 0, f"the reader read the file 0 times in {tries} tries while the two writers ran"
        with open(path, encoding="utf-8") as f:
            assert json.load(f)["n"] == rounds - 1
        assert os.listdir(d) == ["process-state.json"], os.listdir(d)
        return reads
    finally:
        _drop(d)
        _drop(signals)


def _selftest():
    failures, seen = [], {}
    for check in (_check_text_and_json, _check_binary_temp, _check_foreign_tmp, _check_replace_fails_clean,
                  _check_write_fails_clean,
                  _check_replace_retry, _check_private_mode, _check_create_exclusive, _check_append_line,
                  _check_durable, _check_append_refused, _check_read_json, _check_newer_schema,
                  _check_every_writer_moves, _check_says_what_it_did_not_check, _check_two_writers_one_reader):
        try:
            seen[check.__name__] = check()
        except Exception as exc:  # noqa: BLE001 -- each check is reported by name; one failing must not hide the rest
            failures.append(f"{check.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        print("\n".join(failures))
        print(f"project_io selftest FAILED -- {len(failures)} check(s)")
        return 1
    for case, why in _NOT_CHECKED_HERE:            # the OK line below claims only what ran (m-5)
        print(f"project_io: {case} was not checked here -- {why}")
    reads = seen["_check_two_writers_one_reader"]
    print(f"project_io selftest OK -- text, JSON and bytes land with the old sites' bytes, every temp opened binary "
          f"(O_BINARY) and read back as written; a foreign <file>.tmp is "
          f"left alone and no temp name repeats; a failed move, a write failing with its bytes in the temp and a "
          f"Ctrl-C there leave the old file whole and no temp behind; a held move is retried on Windows only; a "
          f"private file is private from its first byte, its mode set again before the move; an exclusive create "
          f"never writes over a name, linked or (no hard links) in place, and a failed one leaves no name; a line "
          f"appended after a torn one starts on a fresh line, the old append's bytes otherwise; the folder is fsynced "
          f"after a move and a link (POSIX, never on Windows), an appended line too, and a journal that cannot be "
          f"opened is Unreadable from the append, nothing appended; read_json gives the "
          f"default for no file, reads a BOM, and refuses an empty, cut-off, cp1251, wrong-type, held or directory one "
          f"as Unreadable, naming it and its repair -- never the caller's older copy for a file that may be whole, the "
          f"repair by its cause (close what holds it for a permission refusal on Windows, a permission or a file in "
          f"the path's place on POSIX, the disk's for anything else on both; a refused append said as one), "
          f"and a file cut inside a character as cut off, not re-encoded; Project.save, Process._write, the seals and "
          f"save_profile go through the move: with it failing each raises, the old bytes whole and no temp left; "
          f"newer_schema tells a file a newer method wrote by an int version alone; "
          f"two writers x 100 and a reader: {reads} reads, every one whole")
    return 0


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: project_io.py --selftest  (a library: the method's writers call it)", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
