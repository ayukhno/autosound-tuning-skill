"""A child whose deadline ends the call, on Windows too (skill #167).

`subprocess.run(..., capture_output=True, timeout=N)` kills the child at the deadline and then, on Windows, reads its
pipes to the end with no deadline at all: a grandchild that inherited them -- `gh`'s, a CLI's node, a `cmd.exe /c`'s
program -- holds them open, and the call waits for as long as that grandchild lives. The window that asked for it waits
with it. Here nothing a grandchild can hold is waited on:

  * stdout and stderr go to temporary files, not pipes -- a file has no end of stream to wait for;
  * stdin is a temporary file holding `input`, or the null device -- never a pipe either;
  * the child starts in a process group of its own (`start_new_session` / `CREATE_NEW_PROCESS_GROUP`);
  * the deadline is `communicate(timeout=...)` on the child alone; past it the whole tree is killed -- `os.killpg`
    with SIGKILL, `taskkill /F /T /PID` -- and its end is waited for `REAP_S` seconds more, never without a bound;
  * an interrupt (Ctrl+C) while it waits kills the tree too, then goes on up: a group of its own no longer gets the
    console's Ctrl+C, so it would outlive the run.

    run_bounded(argv, timeout, input=None, **kw) -> (returncode, stdout, stderr, timed_out)
    run(argv, timeout, input=None, **kw)          -> subprocess.CompletedProcess, or raises subprocess.TimeoutExpired

`kw` is Popen's (`cwd`, `env`, `shell`, ...), plus `encoding` and `errors` for the text (utf-8, replace) and `stdin`
when there is no `input`. The text is read as `text=True` reads it: `\\r\\n` and `\\r` become `\\n`. A program that
cannot be started raises Popen's `OSError`, as `subprocess.run` does. `returncode` is None when a killed tree did not
end within `REAP_S`. A grandchild of a child that ENDED in time is left alone: what it writes after is not read.

Stdlib only; loaded by path like every sibling. `python3 bounded_run.py --selftest`.
"""
import contextlib
import os
import signal
import subprocess
import sys
import tempfile
import time

#: How long the end of a tree killed at its deadline is waited for, in seconds.
REAP_S = 5


def _kill_tree(proc):
    """Kill `proc` and every process of its group or tree. Never raises: a tree already gone is a tree killed."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=REAP_S)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def _text(data, encoding, errors):
    return data.decode(encoding, errors).replace("\r\n", "\n").replace("\r", "\n")


def run_bounded(argv, timeout, input=None, **kw):
    """`(returncode, stdout, stderr, timed_out)` of `argv`, ended at `timeout` seconds with its whole tree."""
    encoding = kw.pop("encoding", None) or "utf-8"
    errors = kw.pop("errors", None) or "replace"
    stdin = kw.pop("stdin", subprocess.DEVNULL)
    for name in ("stdout", "stderr", "capture_output", "text", "universal_newlines", "timeout"):
        if name in kw:
            raise TypeError(f"run_bounded takes no {name}=: the output is always captured, as text")
    if input is not None and stdin is not subprocess.DEVNULL:
        raise TypeError("run_bounded takes input= or stdin=, not both")
    if os.name == "nt":
        kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, contextlib.ExitStack() as stack:
        if input is not None:
            fin = stack.enter_context(tempfile.TemporaryFile())
            fin.write(input.encode(encoding) if isinstance(input, str) else input)
            fin.seek(0)
            stdin = fin
        proc = subprocess.Popen(argv, stdin=stdin, stdout=out, stderr=err, **kw)
        timed_out = False
        try:
            proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            try:
                proc.communicate(timeout=REAP_S)
            except subprocess.TimeoutExpired:
                pass
        except BaseException:
            _kill_tree(proc)
            raise
        out.seek(0)
        err.seek(0)
        return proc.returncode, _text(out.read(), encoding, errors), _text(err.read(), encoding, errors), timed_out


def run(argv, timeout, input=None, **kw):
    """`run_bounded` in `subprocess.run`'s answer: a `CompletedProcess`, or `subprocess.TimeoutExpired` past the
    deadline (its tree killed) -- for a caller written against `subprocess.run(..., capture_output=True, text=True)`.
    Its `capture_output` and `text` are accepted and dropped: both are always so here."""
    kw.pop("capture_output", None)
    kw.pop("text", None)
    rc, out, err, timed_out = run_bounded(argv, timeout, input=input, **kw)
    if timed_out:
        raise subprocess.TimeoutExpired(argv, timeout, output=out, stderr=err)
    return subprocess.CompletedProcess(argv, rc, out, err)


def _alive(pid):
    """True while process `pid` runs (a zombie is not running). Windows: asked through the process handle, never
    `os.kill(pid, 0)`, which there ends the process."""
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT: still running
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # a zombie answers kill(0); `ps` says it is one
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return True
    return bool(state) and not state.startswith("Z")


def _check_answers_and_input():
    """A child that answers: its code, stdout and stderr as text, `\\r\\n` read as `\\n`; `input` reaches its stdin;
    with no input its stdin is empty, never the terminal's."""
    py = sys.executable
    got = run_bounded([py, "-c", "import sys; sys.stdout.write('a\\r\\nb\\n'); sys.stderr.write('said'); sys.exit(3)"],
                      30)
    assert got == (3, "a\nb\n", "said", False), got
    got = run_bounded([py, "-c", "import sys; print(sys.stdin.read().upper())"], 30, input="über")
    assert got[:2] == (0, "ÜBER\n") and not got[3], got
    got = run_bounded([py, "-c", "import sys; print(repr(sys.stdin.read()))"], 30)
    assert got[1] == "''\n", got
    done = run([py, "-c", "print('ok')"], 30, capture_output=True, text=True)
    assert isinstance(done, subprocess.CompletedProcess) and (done.returncode, done.stdout) == (0, "ok\n"), done
    try:
        run_bounded(["/no/such/program-167"], 5)
        raise AssertionError("a program that is not there started")
    except OSError:
        pass


def _check_a_grandchild_holding_stdout_does_not_hold_the_call():
    """#167: the stand-in starts a grandchild (`sleep 30`; a 30 s Python on Windows) that inherits its stdout, says a
    line, and sleeps itself. With a 2 s deadline the call returns within the deadline plus `REAP_S`, timed out, with the
    line it said -- and the grandchild is gone. `subprocess.run` waited there, on Windows, for the grandchild's 30 s."""
    py = sys.executable
    top = tempfile.mkdtemp(prefix="bounded_run_")
    pid_file = os.path.join(top, "grandchild.pid")
    sleeper = "['sleep', '30']" if os.name != "nt" else "[sys.executable, '-c', 'import time; time.sleep(30)']"
    stand_in = ("import subprocess, sys, time\n"
                f"p = subprocess.Popen({sleeper})\n"
                f"open({pid_file!r}, 'w').write(str(p.pid))\n"
                "print('started', flush=True)\n"
                "time.sleep(30)\n")
    try:
        t0 = time.monotonic()
        rc, out, _err, timed_out = run_bounded([py, "-c", stand_in], 2)
        took = time.monotonic() - t0
        assert timed_out and took < 2 + REAP_S + 3, (timed_out, took)
        assert "started" in out, out
        with open(pid_file, encoding="utf-8") as fh:
            grandchild = int(fh.read())
        deadline = time.monotonic() + 5
        while _alive(grandchild) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not _alive(grandchild), f"the grandchild {grandchild} outlived the call"
        try:
            run([py, "-c", "import time; time.sleep(30)"], 1)
            raise AssertionError("run() past its deadline returned")
        except subprocess.TimeoutExpired as exc:
            assert exc.timeout == 1, exc
    finally:
        import shutil
        shutil.rmtree(top, ignore_errors=True)


def _pids_of(pid_file, deadline_s=5):
    """The pids the stand-in wrote to `pid_file` -- its own, then its grandchild's -- once both are there."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        try:
            with open(pid_file, encoding="utf-8") as fh:
                pids = [int(p) for p in fh.read().split()]
            if len(pids) == 2:
                return pids
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    raise AssertionError(f"the stand-in wrote no pids to {pid_file}")


def _stand_in(pid_file):
    """A child that starts a 30 s grandchild on its stdout, writes both pids, and sleeps 30 s itself."""
    return ("import os, subprocess, sys, time\n"
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            f"open({pid_file!r}, 'w', encoding='utf-8').write(f'{{os.getpid()}} {{p.pid}}')\n"
            "time.sleep(30)\n")


def _gone(pids, deadline_s=5):
    deadline = time.monotonic() + deadline_s
    while any(_alive(p) for p in pids) and time.monotonic() < deadline:
        time.sleep(0.1)
    return not any(_alive(p) for p in pids)


def _check_an_interrupt_kills_the_tree():
    """An interrupt (Ctrl+C) while the call waits kills the child and its grandchild, then goes on up: a group of its
    own gets no Ctrl+C from the console, so the tree would outlive the run. The wait is a stand-in that raises
    `KeyboardInterrupt` once both pids are written."""
    import shutil
    top = tempfile.mkdtemp(prefix="bounded_run_interrupt_")
    pid_file = os.path.join(top, "pids")
    real = subprocess.Popen.communicate

    def interrupted(self, *args, **kwargs):
        _pids_of(pid_file)
        raise KeyboardInterrupt
    subprocess.Popen.communicate = interrupted
    try:
        try:
            run_bounded([sys.executable, "-c", _stand_in(pid_file)], 30)
            raise AssertionError("the interrupt did not go on up")
        except KeyboardInterrupt:
            pass
    finally:
        subprocess.Popen.communicate = real
    try:
        pids = _pids_of(pid_file)
        assert _gone(pids), f"the tree {pids} outlived the interrupt"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_a_tree_that_does_not_end_is_none():
    """A tree that does not end within `REAP_S` after its kill answers `returncode` None, timed out -- never a wait
    without a bound. The kill is a stand-in that kills nothing, so the reap waits out `REAP_S`; the tree is killed after."""
    import shutil
    global REAP_S
    top = tempfile.mkdtemp(prefix="bounded_run_no_end_")
    pid_file = os.path.join(top, "pids")
    real_kill, real_reap = globals()["_kill_tree"], REAP_S
    globals()["_kill_tree"] = lambda proc: None
    REAP_S = 0.5
    try:
        t0 = time.monotonic()
        rc, _out, _err, timed_out = run_bounded([sys.executable, "-c", _stand_in(pid_file)], 1)
        took = time.monotonic() - t0
        assert (rc, timed_out) == (None, True) and took < 1 + 0.5 + 3, (rc, timed_out, took)
    finally:
        globals()["_kill_tree"], REAP_S = real_kill, real_reap
        for pid in (_pids_of(pid_file) if os.path.exists(pid_file) else ()):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        shutil.rmtree(top, ignore_errors=True)


def _selftest():
    failures = []
    for check in (_check_answers_and_input, _check_a_grandchild_holding_stdout_does_not_hold_the_call,
                  _check_an_interrupt_kills_the_tree, _check_a_tree_that_does_not_end_is_none):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    if failures:
        print("selftest[bounded_run] FAIL\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print("selftest[bounded_run] OK -- a child answers as text with its code, input reaches its stdin and no input "
          "is an empty one; a grandchild holding stdout past the deadline is killed with its tree and the call "
          "returns within the deadline plus REAP_S, timed out, with what was said (#167)")
    return 0


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


if __name__ == "__main__":
    console = _siblings().load("console.py")         # issue #21: a code page must not destroy a result
    console.install()
    if sys.argv[1:] != ["--selftest"]:
        print("usage: bounded_run.py --selftest  (a library: the method's callers of gh and the reviewer CLIs use it)",
              file=sys.stderr)
        sys.exit(2)
    sys.exit(_selftest())
