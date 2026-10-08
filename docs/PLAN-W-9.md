# W-9 · v3.1.3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the October audit's second wave in the skill — the method's own writer lock, installers that trust
only a real signature and say what they left undone, what the model is told, the user's path in the text, SKILL.md
back under the re-attach budget, subprocesses with timeouts, and what W-8's reviews left. Issues #141–#148 on
milestone `W-9 · v3.1.3`, all with the Arbiter's `ok` (2026-10-08).

**Architecture:** One new stdlib module, `rew_tool/write_lock.py`: a re-entrant project lock (`flock` on POSIX,
`msvcrt.locking` on Windows) on `<project>/.autosound/write.lock`, which every writer CLI TCC runs takes around its
read-modify-write; a held lock answers exit **75** "busy", nothing written. The file declares `PROTOCOL = 1` on a line
of its own: TCC's `core/project_lock.py` `locks_itself` reads exactly that. The installers classify git's own
sentences and accept only `Good "git" signature for <principal>`, and gain an exit contract with **3** = installed,
not ready. The text changes land with the `docs-check.py` rules that hold them; SKILL.md's cut is held by a budget
check and a move-check.

**Tech Stack:** Python 3.9+ stdlib; bash, PowerShell and cmd in the installers; each module's own `_selftest()`;
`scripts/run-selftests.sh` as the one entry; ruff 0.12.0.

**Spec:** `docs/PLAN-AUDIT-2026-10.md` §3 (groups J2, J6, J7, J8, S2, S6), §4, §5 row W-9, §8; the issues #141–#148.
The audit reports: `git show origin/claude/charming-faraday-dcn0ez:docs/AUDIT-TOOLING-2026-10-04.md` (T-*, K-*, F-*,
E-*) and `git show origin/claude/relaxed-ritchie-pk2nci:docs/AUDIT-INSTRUCTIONS-2026-10-04.md` (I-*, §5.1). The
user-path audit (P-*) is private: it is cited by its IDs only, never copied. TCC's side, read-only:
`~/dev/autosound/tcc` `src/autosound_tcc/core/project_lock.py` and `tests/test_writer_race.py`. The code maps this
plan was written from: `hub/scratch/skill/w9/maps/` (sonnet, read-only, 2026-10-08).

## Global Constraints

- Everything tracked, and every commit message, in English (the commit-msg hook refuses Cyrillic). The exception is
  the uk/de/pl language files, and the Ukrainian lines the tools already print.
- Branch `wave-2026-10-08` in the main tree `~/dev/autosound/skill`. No worktree (the hub's board reads the main tree).
- Tests first, red before the code. New tests are separate functions `_check_*()`, called from the module's
  `_selftest()` through a loop that collects every failure — never appended to its one long chain of asserts:
  ```python
  failures = []
  for check in (_check_a, _check_b):
      try:
          check()
      except AssertionError as exc:
          failures.append(f"{check.__name__}: {exc}")
  assert not failures, "\n".join(failures)
  ```
- While working, run only the selftest of the module you changed (`python3 <module> <its argv from
  scripts/selftests.txt>`), plus `python3 scripts/docs-check.py` when a document changes. The full
  `scripts/run-selftests.sh` runs once per group, at the group review, and never while files are being edited
  (the tests read source). Every run with `REW_API_URL=http://127.0.0.1:1`; never REW's port 4735.
- Python 3.9 compatible (Apple's `python3` runs the method). New modules are stdlib only.
- Contract 1 = the v3.1.x surface (PLAN-AUDIT §8 M5); everything here is additive under it. No `### Breaking`; the
  release is the patch `v3.1.3`.
- Exit codes: **0** yes/done · **1** no/refused · **2** usage · 3 and 4 per tool, as today · **69** REW unavailable,
  nothing written · **70** unexpected error (a bug; the traceback on stderr) · **75** busy: the project's writer lock
  is held, nothing written, safe to retry (Task 1). The installers keep their own table (Task 7): 0 ready · 1
  stopped, nothing changed · 2 usage · 3 installed, not ready.
- The lock's sign is TCC's probe, verbatim: the file `rew_tool/write_lock.py` holds a line `PROTOCOL = 1` on its own
  (TCC's regex: `^PROTOCOL\s*=\s*1[ \t]*(?:#.*)?$`, multiline). The method's lock file is
  `<project>/.autosound/write.lock`, never TCC's `process/.process-write.lock` (TCC holds that one around the child it
  runs; the method taking it would wait on its own parent).
- The lock is never held across REW, git, `gh` or any other subprocess.
- `AUTOSOUND_LOCK_TIMEOUT_S` is read per call (seconds; default 10 when unset; a value that does not parse is a usage
  error, exit 2, naming the variable). No `--lock-timeout` flag (PLAN-AUDIT §6).
- No new sibling import at module level in `rew_api.py` (TCC loads it by path).
- Never match an exception by class across module copies: read its attribute (`rew_state`, `is_unreadable`,
  `exit_code`, `is_busy`).
- `capture-check`'s existing Ukrainian output lines stay as they are (TCC parses them).
- Flags stay string literals in `process.py` (TCC finds them in the source text, N19).
- uk/de/pl files are translated by the Advisor (`python3 skills/autosound-tuning/scripts/autosound_ai.py ask …`),
  never by a session or a subagent; the session checks the structure.
- A new script with a command line needs a `NOT_ON_BOARD` line in `rew_tool/capabilities.py` (its reverse pass fails
  the suite otherwise), a line in `scripts/selftests.txt`, and, for a tree check, a line in `scripts/run-selftests.sh`.
- `CHANGELOG.md`: one `## [Unreleased]` section above `## [v3.1.2]`; each task, or its group's last task, adds its bullets; `### Upgrading`
  collects what a user or TCC must know. Its "Plugin users" line says the catalogue moves when the audit's waves are
  done, not to this version (the Arbiter, 2026-10-08).
- Models: implementers **opus**; every reviewer — per task and per group — **opus**; **sonnet** only for reading and
  grep; the final review of the writers-and-the-lock group **Fable**.
- Paths below are relative to the repo root; `SK` = `skills/autosound-tuning`, `RT` = `SK/rew_tool`.
## Order, groups, reviews

| # | task | issue | group |
|---|---|---|---|
| 1 | `write_lock.py` — one writer at a time | #141 | writers and the lock |
| 2 | Every `process.py` writer under the lock; REW, git and `gh` outside it | #141 | writers and the lock |
| 3 | The close in the state first; a mistyped process folder starts nothing; the plan file said | #141 | writers and the lock |
| 4 | The other writers under the lock; `Project.save` counts from the disk; `Project.update` | #141 | writers and the lock |
| 5 | The lock in CONTRACT.md, process-schema.md, the CHANGELOG | #141 | writers and the lock |
| — | group review: `silent-failure-hunter` + `pr-test-analyzer`, one fix round; **Fable** final; full suite | | |
| 6 | A signature is the author's or nothing | #142 | installs |
| 7 | No readable tag, no install; one release-tag rule; a clone is the tag it checked | #142 | installs |
| 8 | The exit contract and the receipt | #142 | installs |
| 9 | What a re-run repairs; the engine's codes; one install time, one example pair | #142 | installs |
| — | group review: `silent-failure-hunter` + `pr-test-analyzer`, one fix round; full suite | | |
| 10 | What the reviewer is told | #143 | what a session reads |
| 11 | One home for each prose file | #143 | what a session reads |
| 12 | The slot rule; the reviewer at the desk; the visits | #144 | what a session reads |
| 13 | SKILL.md's budget as checks; the trigger baseline | #145 | what a session reads |
| 14 | The cut | #145 | what a session reads |
| 15 | The § index, the report words, the evals and the trigger runs | #145 | what a session reads |
| — | group review: one opus reviewer over the moved rules, the sources, the trigger runs; full suite | | |
| 16 | Subprocesses with a timeout; helpers that say their failures | #146 | silent failures, round 2 |
| 17 | Refusals and reads that still say the wrong thing | #147 | silent failures, round 2 |
| 18 | Checks that can fail, round 2 | #148 | silent failures, round 2 |
| — | group review: `silent-failure-hunter` + `pr-test-analyzer`, one fix round; full suite | | |
| 19 | Close the wave: CHANGELOG, PR, the VM run, candidate, TCC's run, release | all | — |

**Why the lock first:** Tasks 10 and 16 write through it (the door records the reviewer step; the helpers that write
project files), and Task 19's candidate is what TCC's race harness was waiting for.

## What needs the Arbiter

- **Before «го»:** read Task 12's two text decisions (the slot rule's sentence; P9 moves Phase 3's cross-vendor
  verdicts from the car session to the desk after it) and Task 14's list of what leaves SKILL.md.
- **Tasks 13 and 15:** the trigger runs must not see the other car-audio skill (`anthropic-skills:rew-car-audio-tuning`).
  If no setting hides it for `claude -p`, about a minute of his to switch it off for the runs.
- **Task 19:** the Windows VM run, about 20–30 minutes: two writers at once on a project, and `install.cmd` fresh and
  re-run with its exit codes and receipt.
- **Task 19:** the release word, after TCC has run its suite on the candidate.

## Cost

| block | tasks | machine time |
|---|---|---|
| writers and the lock | 1–5 + review + Fable | ~6 h |
| installs | 6–9 + review | ~5 h |
| what a session reads | 10–15 + review, with six trigger runs (~1.5 h) | ~6 h |
| silent failures, round 2 | 16–18 + review | ~4 h |
| close | 19 | ~1 h, then the VM run and TCC's run |
| **total** | 19 | **~22 h**, sequential; three days with the stops |

## Where this plan departs from PLAN-AUDIT (found by the code maps, 2026-10-08)

1. The lock lives in `rew_tool/write_lock.py`, not `project_io.py`: TCC's `locks_itself` reads that file for
   `PROTOCOL = 1` (tcc `core/project_lock.py:51-74`), and the names follow TCC's own plan (§5.4: `hold`, `held_here`,
   `Busy`). Issue #141's text said `project_io.py`.
2. 75 is already declared (`process.py:195-200`, `CONTRACT.md:37`, `process-schema.md:291`); this wave raises it. The
   schema file is `RT/state/process-schema.md`, not `docs/process-schema.md`.
3. A mistyped process folder (W-8's ruling R46) is refused by a rule, not by a list of starting verbs: a folder that
   does not exist is written only when it is a project's `process` folder (and, before `project.json` exists, only by
   `enter-phase -1`). TCC's answer on hub #267 is checked against it when Task 3 starts.
4. The close goes to the state before the journal (Task 3); W-8's tests pinned the old order and are marked "J2b's to
   change" (`process.py:6520`).
5. `Project.update` has no TCC caller at TCC's HEAD (`car_library` spawns `intake.py set-car`); the skill's own
   load-and-save paths move into it, so the lock covers the load too (Task 4).
6. `check_captures` writes the very object it loaded before reading REW; under the lock it re-loads and merges by round
   (Task 2), as TCC's plan says ("merges its verdicts under a second hold").
7. Installers: "stopped, nothing changed" cannot be promised — the method's stops come after Claude Code (and, on
   Windows, Git, uv and Python) are installed. Exit 1 promises the method's copy only (Task 8).
8. The receipt keeps `installer_sha256` — the Arbiter's decision (`docs/W-2-DECISIONS.md:34`, row 26) — and adds
   `installer_version`; PLAN-AUDIT said "replacing the hash".
9. `installer-consistency.py` is the installers' test (no `--selftest`) and runs in TCC's suite under 120 s: the new
   cases stay offline and fast; no real `gpg` — the OpenPGP direction is shown with a fake `gpg.program` (Task 6).
10. Every Linux job says `ubuntu-latest`; the exit-3 job names `ubuntu-24.04` (Task 8).
11. J8's "ledger HEAD in every package": no code builds a package (the Generator writes it), so the door adds a LEDGER
    HEAD block itself (Task 10).
12. J8's I-5: nothing in code copies the contract — prose does; the instructions stop, the door reads the skill's own
    copy, and `doctor` and `contract.py check` name a copy that differs (Task 10).
13. I-21: the home of the prose files is the project root (the structure doc's tree); every reader falls back to
    `rew_analitic/` and says so (Task 11).
14. P9 reaches Phase 3: three documents put the cross-vendor verdicts in the car session; they move to the desk after
    it (Task 12) — a text decision for the Arbiter to read before «го».
15. S2: the Map is not last today (6th of 8); keeping the order with the Map last moves Review Channel and Output Style
    before it, and the cut to 17,500 bytes before the Map is ~13.7 KB (Task 14).
16. N3 is answered by TCC's code: TCC does not read SKILL.md (its six mentions are comments); asked anyway on hub #267.
17. S6: one `run()` for every subprocess does not fit their shapes (bytes, stdin, `Popen`, an interactive editor):
    each call gets its timeout where it is, and a tree check holds the rule (Task 16). K-5's runner is a contract-1
    default: its name and `(rc, out, err)` stay.
18. #147 as the tree has it: the shadow read already reads a BOM, six other readers do not; the form's
    `missing_files` is already strict; `flaw_map`'s traceback comes from `load_solos_dir`, and `level_offsets` and
    `xover_candidates` have the same one (taken); the cut-file wording also in `Project.load` and the changelog read
    (taken).
19. #148: no `_check_*` is orphaned today — the check holds the future; the temp folders are held by the runner (a
    fresh `TMPDIR` per selftest that must stay empty); Python 3.11 is not on this Mac (`uv python install 3.11`).

---

## Task 1: `write_lock.py` — one writer at a time (#141; PLAN-AUDIT §3 J2b item 1, §8 M1)

**Files:**
- Create: `RT/write_lock.py`
- Modify: `scripts/selftests.txt` (`skills/autosound-tuning/rew_tool/write_lock.py --selftest`), `RT/capabilities.py`
  (`NOT_ON_BOARD`: `write_lock.py`, its command line is its selftest — as `project_io.py` at `:60`)
- Modify: `.github/workflows/checks.yml` — after the last step (`:191-192`, project_io's), a step
  `- name: the project lock on Windows (write_lock's selftest)` / `run: python skills/autosound-tuning/rew_tool/write_lock.py --selftest`
- Modify: `RT/state/process.py:4892-4902` (`_project_bytes`) and `RT/state/migrate.py:797-807` (`_bytes_under`): skip a
  top-level `.autosound/` folder (the lock's bookkeeping, not project content), so the 30 byte-identity comparisons hold

**Interfaces:**
- Consumes: `_siblings()` (W-8) — the module is stdlib only and loads nothing.
- Produces (what TCC's own plan names, §5.4 of its `docs/PLAN-AUDIT-2026-10.md`):
  - `PROTOCOL = 1` on a line of its own (TCC's `locks_itself` regex, verbatim in the Global Constraints)
  - `LOCK_DIR = ".autosound"`, `LOCK_FILE = "write.lock"`, `ENV_TIMEOUT = "AUTOSOUND_LOCK_TIMEOUT_S"`,
    `DEFAULT_TIMEOUT_S = 10.0`
  - `class Busy(Exception)`: `is_busy = True`, `exit_code = 75`, `.path` (the lock file), `.waited_s`;
    `str()` = `busy: <lock file> is held by another writer -- nothing was written, safe to retry`
  - `class BadTimeout(Exception)`: `exit_code = 2`; `str()` = `AUTOSOUND_LOCK_TIMEOUT_S=<value> is not a number of
    seconds (0 or more) -- unset it for the default 10`
  - `lock_path(project_dir) -> str`; `timeout_s() -> float` (read per call; raises `BadTimeout`)
  - `hold(project_dir, timeout_s=None)` — a context manager, re-entrant within a thread; `held_here(project_dir) -> bool`
  - `busy_exit(exc, stream=None) -> int`: prints `str(exc)` as one line on stderr, returns `exc.exit_code`

- [ ] **Step 1: Write the failing tests** — `write_lock.py`'s own `_selftest()` with the collecting loop:

```python
def _check_protocol_line():
    """TCC reads this file as TEXT for its sign (core/project_lock.py locks_itself): keep the line it matches."""
    import re
    src = open(__file__, encoding="utf-8").read()
    assert re.search(r"^PROTOCOL\s*=\s*1[ \t]*(?:#.*)?$", src, re.MULTILINE), "TCC's probe would read False"


def _check_folder_ignores_itself():
    """`.autosound/` holds the lock and a .gitignore of `*`: `git add -A` in the project stages nothing from it."""
    <tmp project; with hold(p): pass; assert os.path.isfile(lock_path(p));
     assert open(<p>/.autosound/.gitignore).read() == "*\n";
     if shutil.which("git"): git init + git add -A; `git status --porcelain --ignored=no` lists nothing under .autosound/>


def _check_reentrant_and_held_here():
    <with hold(p): assert held_here(p); with hold(p, timeout_s=0): assert held_here(p); assert not held_here(p)>


def _check_another_thread_waits():
    <thread A holds and waits on an Event; in the main thread hold(p, timeout_s=0.3) raises an exception whose
     getattr(type(e), "is_busy") is True and e.exit_code == 75; A releases; hold(p, timeout_s=2) succeeds>


def _check_another_process_is_busy():
    """The lock is a lock between PROCESSES: a spawned holder makes this one answer Busy, then lets it in."""
    <multiprocessing.get_context("spawn"); a top-level worker _holder(p, signals) takes hold(p), creates
     <signals>/held, polls for <signals>/go (60 s limit), returns; the parent waits for `held`,
     asserts hold(p, timeout_s=0.5) raises Busy with lock_path(p) in str(e) and 0.4 <= e.waited_s < 5,
     writes `go`, joins (exitcode 0), then hold(p, timeout_s=5) succeeds — pattern: project_io's
     _check_two_writers_one_reader (`project_io.py:1193-1248`), marker files and short polls, no sleeps as sync>


def _check_timeout_from_the_environment():
    <unset → 10.0; "2.5" → 2.5; "0" → 0.0; "abc", "-1", "nan", "" → BadTimeout with exit_code 2 and the variable's
     name in str(); restore the environment in a finally>


def _check_a_free_lock_with_zero_wait():
    <hold(p, timeout_s=0) on a free lock enters at once>


def _check_a_folder_that_cannot_lock():
    """A Parallels shared folder, SMB, a cloud folder: the OS refuses the lock itself. The write goes ahead, said once."""
    <replace the module's _os_lock with a function raising OSError(errno.ENOLCK, "No locks available");
     capture stderr; with hold(p): pass — no exception; stderr has exactly one line starting "note: " that names
     the folder and says "without the project lock"; restore _os_lock in a finally>
```

- [ ] **Step 2: Run — expect FAIL**: `python3 RT/write_lock.py --selftest` (the module has only the stubs:
  `def hold(...): raise NotImplementedError`).

- [ ] **Step 3: Build `RT/write_lock.py`**

```python
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
import os
import sys
import threading
import time
from contextlib import contextmanager

LOCK_DIR = ".autosound"
LOCK_FILE = "write.lock"
ENV_TIMEOUT = "AUTOSOUND_LOCK_TIMEOUT_S"
DEFAULT_TIMEOUT_S = 10.0
_POLL_S = 0.05
_HELD_ERRNOS = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, getattr(errno, "EDEADLOCK", errno.EDEADLK)}
```

Then, in order:
- `Busy` and `BadTimeout` as in Interfaces.
- `lock_path(project_dir)`: `os.path.join(os.path.abspath(project_dir), LOCK_DIR, LOCK_FILE)`.
- `timeout_s()`: `os.environ.get(ENV_TIMEOUT)`; unset → `DEFAULT_TIMEOUT_S`; `float(v)`; NaN, infinite, negative or
  unparsable → `BadTimeout(v)`.
- `_prepare(project_dir)`: `os.makedirs(<project>/.autosound, exist_ok=True)`; write `.gitignore` = `*\n` once if
  absent (a plain `open(..., "x")` and `FileExistsError` ignored: two writers may race to create it).
- `_os_lock(fd)` / `_os_unlock(fd)`: POSIX `fcntl.flock(fd, LOCK_EX | LOCK_NB)` / `LOCK_UN`; Windows
  `os.lseek(fd, 0, 0)`; `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` / `LK_UNLCK`. An `OSError` whose errno is in
  `_HELD_ERRNOS` (or a `BlockingIOError`) means "held"; any other `OSError` means "cannot lock here".
- A per-path registry `{realpath(lock file): _Entry(rlock=threading.RLock(), count=0, fd=None, owner=None)}` guarded
  by one module `threading.Lock`.
- `hold(project_dir, timeout_s=None)`: `deadline = time.monotonic() + (timeout_s() if timeout_s is None else
  timeout_s)`; if `entry.owner == threading.get_ident()`: `count += 1`, yield, `count -= 1` (re-entry). Else acquire
  `entry.rlock` with `timeout=max(0, deadline - now)` (False → `Busy`); `_prepare`; `fd = os.open(path, os.O_RDWR |
  os.O_CREAT, 0o644)`; loop: `_os_lock(fd)` → done; held → if past the deadline: close fd, release rlock, raise
  `Busy(path, waited)`; else `time.sleep(min(_POLL_S, left))`; cannot lock → one `note:` line on stderr (`note:
  <project> cannot be locked (<strerror>) -- writing without the project lock; two writers at once can lose a change
  here`), proceed without the OS lock. Yield; in `finally`: `_os_unlock` if taken, `os.close(fd)`, owner None, release.
- `held_here(project_dir)`, `busy_exit(exc, stream=None)`.
- `__main__`: `--selftest` only, else usage on stderr and exit 2 (as `project_io.py:1289-1295`).

- [ ] **Step 4: Run — expect PASS**: `python3 RT/write_lock.py --selftest`; `python3 RT/state/process.py selftest`
  and `python3 RT/state/migrate.py <its argv>` (the byte walks skip `.autosound/`); `python3 RT/capabilities.py <argv>`.

- [ ] **Step 5: Commit**

```bash
git add RT/write_lock.py RT/capabilities.py RT/state/process.py RT/state/migrate.py scripts/selftests.txt .github/workflows/checks.yml
git commit -m "#141: write_lock.py -- one writer at a time per project, 75 busy, PROTOCOL = 1 as TCC reads it"
```

---

## Task 2: Every `process.py` writer under the lock; the slow calls outside it (#141; J2b item 2)

**Files:**
- Modify: `RT/state/process.py` — a `_write_lock()` loader beside `_project_io()` (`:67-69`); a decorator `_locked`
  on every public writer method; `check_captures` (`:2464-2596`) and `enter_phase` (`:1285-1311`) split; `_main`
  (`:7650-8311`): `Busy` → 75, `BadTimeout` → 2; `_stamp`'s sha asked before the hold; the usage footer (`:3165-3166`)
  says 75 is raised

**Interfaces:**
- Consumes: Task 1's `hold`, `held_here`, `Busy`, `BadTimeout`, `busy_exit`.
- Produces: `Process` writers that take `hold(self.project_dir)` themselves, so a caller in-process (TCC's,
  `Project.record_change`) is covered as well as the CLI. Exit **75** from `process.py` for a held lock.

Today a writer's read-modify-write is unguarded: a bare CLI and TCC can each load the state, and the later write drops
the other's change (TCC's `tests/test_writer_race.py` pins it as an expected failure). `check_captures` loads at
`:2491`, reads REW at `:2502` and `:2573` (5 s timeout per call), and writes that same object at `:2576`;
`enter_phase` loads at `:1294` and its intake gate runs git (up to 60 s) and `gh` (up to 30 s) before the write
(`contract.check_project` → `project_repo.status`); the first `_append` of a run asks git for the skill's sha (3 s).

- [ ] **Step 1: Write the failing tests** (process.py selftest, the collecting loop at `:6752-6780`):

```python
def _check_every_writer_holds_the_lock():
    """By AST: every public Process method that reaches _write/_append (the set _writer_methods derives) is decorated
    @_locked, or is one of the two that take the hold themselves after their slow part."""
    <reuse _writer_methods(src) (:4322-4358); for each, the FunctionDef's decorator_list names `_locked`, or the
     name is in {"check_captures", "enter_phase"} and its body has a `with` whose call is `_hold(...)`; else fail
     naming the method>


def _check_a_held_lock_answers_75_with_nothing_written():
    <d = a project at phase 2 (the fixture the writer tests use); hold the lock from a spawned child (Task 1's
     _holder pattern); run `_cli_env(d, ["add-step", "2.7", "x"], AUTOSOUND_LOCK_TIMEOUT_S="0.3")` (:4865-4873);
     assert rc == 75, stderr's last line starts "busy:", _project_bytes(d) == before; release; the same command
     → rc 0 and the step is in the plan>


def _check_a_bad_timeout_is_a_usage_error():
    <AUTOSOUND_LOCK_TIMEOUT_S="soon" → rc 2, the variable named, nothing written>


def _check_capture_check_reads_rew_unlocked():
    """REW is read with the lock free; the verdicts merge under the hold into the state as it is THEN."""
    <a verifier stub whose verify() asserts not held_here(project_dir) and, while it runs, adds a step through a
     second Process on the same folder (which must not block); check_captures then writes: the plan holds that step
     AND the round's verdicts>


def _check_enter_phase_gates_run_unlocked():
    <patch the intake gate (_require_intake) to assert not held_here(...) and to add a step through a second
     Process; enter_phase(...) lands; the step survives; and a phase entered by the second writer meanwhile makes
     this enter_phase refuse (ProcessError naming the phase now active) instead of writing over it>


def _check_the_sha_is_asked_before_the_hold():
    <patch provenance.skill_sha to record held_here(project_dir) at its call; a first writing verb of a fresh Process
     → recorded False>
```

- [ ] **Step 2: Run — expect FAIL**: `python3 RT/state/process.py selftest`.

- [ ] **Step 3: Build**
  1. `_write_lock()` loads `write_lock.py` through `_siblings()`; `_hold(project_dir)` = `_write_lock().hold(project_dir)`.
  2. `_locked(method)`: `functools.wraps`; `with _hold(self.project_dir): return method(self, *a, **kw)` — but first,
     outside the hold, warm `provenance.skill_sha()` through `_writer_sha()` (`:937-946`, cached per process) so
     `_stamp`'s git call never runs inside it. Decorate all 25 writer methods the table at `:4361-4506` lists, except
     `check_captures` and `enter_phase`. Nested writer calls (capture_import → start/record/knobs/close;
     supersede_capture → record_capture) re-enter.
  3. `check_captures`: the REW part (`:2492-2573` — load the verifier, `verify`, the profile reads, `session_report`)
     runs on a strict load taken WITHOUT the hold; then `with _hold(...)`: load strictly again; the round must still be
     the same open round (id equal) — else `ProcessError("round <id> was closed or replaced while REW was read --
     nothing was written; run capture-check again")`; merge the verdicts into that fresh state by title; `_write`;
     `_append(EV_CAPTURE_VERIFIED, ...)`.
  4. `enter_phase`: the gates (`:1301-1304`) run on an unlocked strict load; then the hold, a fresh strict load; if
     the active phase differs from the one the gates saw → refuse (`ProcessError`, naming both, nothing written);
     else the mutation and the write as today.
  5. `_main`: before the `ProcessError` branch (`:8263-8265`), an exception with `is_busy` → `return
     _write_lock().busy_exit(exc)` (75); an exception from `BadTimeout` (`exit_code == 2` and not a `ProcessError`) →
     its line on stderr and `EXIT_USAGE`. Match by attribute, never by class.
  6. The `capture-close` CLI (`:8161-8240`) keeps its REW read (`:8180`) outside; `reconcile_captures`,
     `check_captures` and `close_capture` each take their own hold (the decorator, and Step 3's split).

- [ ] **Step 4: Run — expect PASS**: `python3 RT/state/process.py selftest`; `python3 RT/write_lock.py --selftest`.

- [ ] **Step 5: Commit**

```bash
git commit -m "#141: every process.py writer under the project lock; REW, git and gh read outside it; 75 busy"
```

---

## Task 3: The close goes to the journal after the state; a mistyped folder starts nothing; the plan file is said (#141; W-8's review items, S-101)

**Files:**
- Modify: `RT/state/process.py` — `close_capture` (`:2622-2628`), `_close_capture` (`:2625` → its append at `:2661`),
  `start_capture`'s close of the round it supersedes (`:1657-1673`), `_write`'s `landed` wording (`:2928-2957`),
  `_write_capture_plan` (`:1700-1719`) and the `capture-start` branch (`:7847-7859`); a home check for every writer
- Modify (tests that pin today's order, marked "J2b's to change"): `:6399-6473`, `:6505-6524`, `:4205-4240`

**Interfaces:**
- Consumes: Task 2's `_locked`.
- Produces: `Process._require_home(verb)` — raises `ProcessError` (exit 1) before anything is created.

Three things W-8's review left to this group:
- The close is in the journal before the state is written (`close_capture` appends at `:2661`, writes at `:2626`;
  `start_capture` the same for the round it supersedes). A held write then says "it is as it was" while the journal
  says closed, and a retry closes the round a second time.
- A writer on a process folder that does not exist creates it (the code map's probe: `enter-phase -1`, `reviewer`,
  `target`, `capture-start` write state and journal into `<project>/process-typo`; `decision`, `session-start`,
  `session-close`, `amp-gain`, `listening-verdict` write a journal there).
- A capture plan that cannot be written after the state landed is said nowhere (`_write_capture_plan` returns None on
  `OSError`, and `start_capture` drops the value).

- [ ] **Step 1: Write the failing tests**

```python
def _check_a_close_lands_state_first():
    <close_capture with project_io.atomic_write_json replaced by one that raises PermissionError (the fault through
     the writer, as :6411 does): ProcessError says "it is as it was"; the journal has NO capture_round_closed for the
     round; restore; close_capture again → exactly one capture_round_closed>


def _check_a_mistyped_process_folder_starts_nothing():
    """W-8's ruling R46: a write verb on a process folder that does not exist creates nothing there."""
    <for verb argv in the probe's eleven (enter-phase -1, reviewer gemini m, target FULL EPY, capture-start 1
     "a_1 (sw)", decision ..., session-start, session-close, amp-gain sw=+3, listening-verdict --text heard, ...):
     run the CLI on <tmp>/proj/process-typo → rc 1, stderr names the folder, and os.listdir(<tmp>/proj) == [] >


def _check_a_new_project_still_starts():
    <<tmp>/proj/process (named `process`, absent) with no project.json: `enter-phase -1` → rc 0, state written;
     any other write verb there first → rc 1 ("not a project yet"); with <tmp>/proj2/project.json present and
     <tmp>/proj2/process absent: `session-start`, `reviewer`, `decision` → rc 0>


def _check_the_plan_file_is_said():
    <capture-start with docs/plans made unwritable (a file named `plans` in its place) → rc 0 (the round is open),
     stderr has one line naming the plan path and the reason; with it writable, stdout names the plan path>
```

Update the three tests that pin the old order to the new one; each keeps its name and says in its docstring what
changed and why.

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Build**
  1. `_close_capture(state, round_, reason)` mutates the state and RETURNS the event payload instead of appending;
     `close_capture`: `_write(state)` then `_append(EV_CAPTURE_CLOSED, **payload)`; `start_capture` the same for the
     superseded round: write the state (the old round closed, the new one open), then the close event, then
     `capture_task_issued`. `_write`'s `landed` stays for the one caller that still needs it, or goes if none does.
  2. `_require_home()`, called by `_locked` before the hold (so nothing is created for a refusal):
     - the folder exists → nothing to check;
     - absent, and its name is not `process` → `ProcessError("<folder> does not exist, and the method's process folder
       is called process -- a mistyped path? nothing was written")`;
     - absent, named `process`, and its parent holds `project.json` → a project's first process write: allowed;
     - absent, named `process`, no `project.json` beside it → allowed only for `enter_phase` to `-1` (the intake
       starts the project); any other writer → `ProcessError("<parent> holds no project.json: not a project yet --
       the intake starts one with enter-phase -1; nothing was written")`.
     TCC passes `<project>/process` for a project its dialog has already seeded with `project.json`; its answer on
     hub #267 (which verbs it runs first) is checked against this rule when the task starts — a verb TCC needs
     before `project.json` exists is a ruling for the controller, recorded in the ledger.
  3. `_write_capture_plan` returns `(path, None)` or `(path, reason)`; `start_capture` keeps it; the `capture-start`
     branch prints `plan: <path>` on stdout, or `note: the round is open, but its plan <path> could not be written
     (<reason>) -- process.py <dir> plan shows it` on stderr; exit 0 either way (the round is open).

- [ ] **Step 4: Run — expect PASS**: `python3 RT/state/process.py selftest`.

- [ ] **Step 5: Commit**

```bash
git commit -m "#141: a close lands in the state before the journal; a mistyped process folder starts nothing; the plan file is said"
```

---

## Task 4: The other writers under the lock; `Project.save` counts from the disk (#141; J2b items 3–4)

**Files:**
- Modify: `RT/project.py` — `Project.save` (`:856-881`), a new `Project.update(fn)`, the mutators that load and save
  (`:885-1358`: `migrate_fields`, `backfill_tiers`, `catch_up`, `set_project_type`, `mark_imported`, `set_channel`,
  `rename_channel`, `add_flaw`, `set_hardware_control`, `set_path`, `set_virtual_route`, `set_control_mapping`),
  `fix_ids` (`:237-251`), `_main` (`:1616-1839`)
- Modify: `RT/intake.py` — `change_dsp` (`:365-421`), `save_slot`, `move_slot`, `save_controls`, `save`,
  `save_car`, `save_channel`, `save_amp` (`:630-1624`): their load-and-save through `Project.update`; `_main`
  (`:1663-1777`): `Busy` → 75
- Modify: `RT/state/state.py` — `PresetHistory.snapshot` (`:1240-1305`), `_set_head` (`:1199-1208`), `save_config`
  (`:680-713`), `seal_all` (`:788-800`), `repair_version` (`:921-944`), `Registry._write`/`set_active`/
  `describe_slot` (`:1590-1623`), `repair_encoding`/`set_aside` (`:1977-2118`), `migrate_line` (`:1019-1120`) under
  the hold; `_main` (`:2153-2235`): `Busy` → 75
- Modify: `RT/dsp_profile.py` — `save_profile`, `save_draft`, `start_draft`, `set_field`, `reset_field`,
  `set_setting`, `finalize`, `refresh_project` (`:536-1022`) under the hold; `_main`/`_run` (`:1238-1432`): `Busy` → 75
- Modify: `RT/state/apply.py` — `propose`/`attest` (`:446-552`) under one hold (snapshot, delta, sheet); `_main`
  (`:867-922`): `Busy` → 75
- Modify: `RT/contract.py` (`IMPORTABLE`, `:120-`) — `Project.update(fn)` added if `scripts/contract-guard.py` accepts
  an addition under contract 1 (it refuses removals and renames); otherwise CONTRACT.md says it is there but not yet
  in contract 1's table

**Interfaces:**
- Consumes: Task 1's `hold`, `busy_exit`.
- Produces: `Project.update(fn) -> dict` — under the hold: load, `fn(data)` (mutates in place or returns a new dict),
  save; returns what was saved. `Project.save(data)` under the hold, `project_rev` = the rev ON DISK + 1 (0 + 1 for no
  file), whatever the caller loaded. Every listed CLI exits **75** for a held lock with one `busy:` line.

The lock only orders writes; a caller that loads, waits, then saves still writes over a change made meanwhile. So the
skill's own load-and-save paths move inside the hold, through `update`. TCC at HEAD writes `project.json` only by
spawning `intake.py set-car` (`car_library.record`), which this task covers; its plan names `Project.update` for later.

- [ ] **Step 1: Write the failing tests**
  - `project.py` selftest: two spawned processes, each `set_channel` on its own channel 40 times → both sets of
    channels are in `project.json`, and `project_rev` == 80 (red today: lost updates). `save` with a stale dict (rev 3
    while the disk says 7) → saved with rev 8.
  - `state.py` selftest: a held lock (spawned holder) → `config save` exits 75 with `busy:` and the ledger
    byte-identical; `seal` the same.
  - `dsp_profile.py` and `intake.py` selftests: `set-field` and `set-car` under a held lock → 75, nothing written.
  - `apply.py` selftest: `propose` under a held lock → 75; no version claimed, no delta, no sheet.
  - Each module: by AST, no function both calls `Project(...).load()` and `.save(` outside `update` (a guard against a
    new load-and-save path appearing later).

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Build** — each writer takes `hold(<project>)`: `Project.dir`; for the ledger,
  `PresetHistory.project_dir` (`state.py:1143-1145`; the ledger root and the project can differ through
  `AUTOSOUND_STATE_ROOT`, and the lock follows the project); for profiles, the folder that holds `dsp_profile.json`.
  The reads inside a writer happen inside its hold. A CLI's handler matches `getattr(type(exc), "is_busy", False)`
  before its other branches. `intake.py` gains a handler for `Busy` and `BadTimeout` only; its other errors keep
  today's traceback (TCC's `car_library._sentence` reads its last line).

- [ ] **Step 4: Run — expect PASS**: the selftests of `project.py`, `intake.py`, `state/state.py`, `dsp_profile.py`,
  `state/apply.py`, `contract.py`, and `python3 scripts/contract-guard.py`.

- [ ] **Step 5: Commit**

```bash
git commit -m "#141: every writer CLI TCC runs takes the project lock; Project.save counts from the disk, Project.update"
```

---

## Task 5: The lock in the contract and the docs (#141; J2b item 5)

**Files:**
- Modify: `RT/CONTRACT.md` — `:37` (75 raised now), §8 (`:229-300`: the lock), §10 (`:375-405`:
  `AUTOSOUND_LOCK_TIMEOUT_S`), the IMPORTABLE note if Task 4 added `Project.update`
- Modify: `RT/state/process-schema.md` — `:291` (75 raised), the close order, a mistyped folder
- Modify: `RT/project_io.py:213-215` (the docstring that says the lock comes in W-9)
- Modify: `SK/references/tooling/installation.md` (one line: a project on a folder that cannot lock, such as a
  Parallels shared folder, is written without the lock, and the method says so)
- Modify: `CHANGELOG.md` (`## [Unreleased]` created above `## [v3.1.2]` if Task 1 did not), `### Upgrading`

- [ ] **Step 1:** CONTRACT.md §8 says: the file (`<project>/.autosound/write.lock`, `.autosound/.gitignore` = `*`); the
  sign (`rew_tool/write_lock.py`, `PROTOCOL = 1` on its own line, read as text); who takes it (every writer CLI the
  table lists, and `Process`/`Project`/`PresetHistory`/profile writers in-process); never across REW, git, `gh` or a
  subprocess; `AUTOSOUND_LOCK_TIMEOUT_S` per call (default 10; a bad value exits 2); exit 75 with one `busy:` line,
  nothing written, safe to retry; a folder that cannot lock is written without it, said once; the close order (state,
  then journal); a missing process folder refused unless it is a project's `process` folder. `python3
  scripts/docs-check.py` and `python3 scripts/contract-guard.py` green.
- [ ] **Step 2:** CHANGELOG bullets (one per Task 1–4) and `### Upgrading` lines for TCC: `write_lock.py` declares
  `PROTOCOL = 1` (TCC's `locks_itself` now reads True on this copy); the method's writers exit 75 when busy; set
  `AUTOSOUND_LOCK_TIMEOUT_S` per call, never in `child_env()`; `capture-close` now writes the close to the state before
  the journal; `process.py` refuses a write on a process folder that does not exist unless it is a project's
  `process` folder; `Project.save` counts the revision from the disk; `.autosound/` appears in projects and ignores
  itself.
- [ ] **Step 3: Commit**

```bash
git commit -m "#141: the lock in CONTRACT.md, process-schema.md and the CHANGELOG"
```

### Group review — writers and the lock (Tasks 1–5)

`pr-review-toolkit:silent-failure-hunter` and `pr-review-toolkit:pr-test-analyzer` (both **opus**) on the group's
diff; one fix round; then the **Fable** final review (PLAN-AUDIT §3 J2b; the hub's seam rule 5 for locks): the
re-entrancy across threads, the one deadline, Windows' `msvcrt` half, the open point — a folder that cannot lock is
written with a `note:` line rather than refused (advised by PLAN-AUDIT; TCC's §5.4 names the Mac↔VM shared folder as
the case). Then `scripts/run-selftests.sh | tail -1`.

---

## Task 6: A signature is the author's or nothing (#142; audit T-35; PLAN-AUDIT §3 J6a items 1–2)

**Files:**
- Modify: `install.sh:870-895` (`verify_tag`), `install.ps1:926-953` (`Test-TagSignature`), `SK/scripts/upkeep.py:102-125`
  (`verify_tag`)
- Modify: `scripts/installer-consistency.py:175-268` (`signing_problems`: new cases), `SK/scripts/upkeep.py` selftest
  (`:814-1068`)
- Modify: `SECURITY.md:23-37` (what the check accepts), `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing new.
- Produces: one accepted sentence in all three verifiers — exit 0 from `git verify-tag` AND a line that starts with
  `Good "git" signature for <principal> with ` (the principal from the file's own signing constant). Tasks 7–8 keep it.

Today all three accept any exit-0 output that contains `Good` (`install.sh:880`, `install.ps1:941`, `upkeep.py:121`),
and none pins `gpg.ssh.program`, so a sign-only helper in the person's git config (1Password's, for one) makes a good
release fail, and the classifier blames git's age because the helper's text contains `-Y` (`install.sh:885`). The
code map reproduced both on git 2.54.0. The reverse direction — an OpenPGP signature from the person's own keyring
passing as the author's — is closed by the exact sentence whatever git does, and the test below shows it without a real
`gpg`.

- [ ] **Step 1: Write the failing cases in `installer-consistency.py`**

Beside the existing fixtures (`IC:195-228`), keep `GIT_CONFIG_GLOBAL=os.devnull` for the existing cases and add three
fixtures, each a file in the same temp dir:

1. `hostile.gitconfig`: `[gpg "ssh"]\n\tprogram = <tmp>/sign-only.sh` where `sign-only.sh` prints
   `helper: sign-only (try -Y sign)` to stderr and exits 1. Case: `verify_tag` on the author-signed `v3.0.64` with
   `GIT_CONFIG_GLOBAL=<tmp>/hostile.gitconfig` → rc 0 and the words `signed by the skill's author` (red today: rc 1,
   "too old").
2. `pgp.gitconfig`: `[gpg]\n\tprogram = <tmp>/fake-gpg.sh` where `fake-gpg.sh` reads its stdin, prints to stdout
   (`--status-fd=1`) the lines `[GNUPG:] NEWSIG`, `[GNUPG:] GOODSIG 0123456789ABCDEF Mallory <m@example.org>`,
   `[GNUPG:] VALIDSIG 0123456789ABCDEF0123456789ABCDEF01234567 2026-10-08 0 0 0 0 0 1 0 0123456789ABCDEF0123456789ABCDEF01234567`,
   `[GNUPG:] TRUST_ULTIMATE 0 pgp` and to stderr `gpg: Good signature from "Mallory <m@example.org>" [ultimate]`, then
   exits 0. A new tag `v3.0.67` whose message ends in a block `-----BEGIN PGP SIGNATURE-----` … `-----END PGP
   SIGNATURE-----` (any base64 body: git hands it to the fake). Case: `verify_tag` on `v3.0.67` with
   `GIT_CONFIG_GLOBAL=<tmp>/pgp.gitconfig` → rc 1 and `does not check out` (red today: git exits 0 with "Good").
   Confirm first, by hand in the temp repo, that `git verify-tag v3.0.67` under that config exits 0 — that is the
   hole; if this git does not exit 0, the case still asserts the refusal and the commit message says the hole was not
   reproduced on this git.
3. `stub-git/git`: a script that answers `verify-tag` with `Good signature from "anyone"` on stderr and exit 0, and
   runs `/usr/bin/git "$@"` for every other subcommand; prepended to `PATH` for this case only. Case: `verify_tag` on
   `v3.0.64` → rc 1, `does not check out` (red today).

The same three cases in `upkeep.py`'s selftest against its `verify_tag` (it takes `env`; Step 3 makes it pass that
`env` to git — today it is built and ignored, `UP:105` against `UP:118`).

- [ ] **Step 2: Run — expect FAIL**

`python3 scripts/installer-consistency.py` → `FAIL` lines for the three new cases; `python3 SK/scripts/upkeep.py
selftest` → the same three.

- [ ] **Step 3: One accepted sentence, in three languages**

`install.sh` (`verify_tag`, today `:873-895`):

```bash
  _vt_rc=0
  _vt_said="$(git -C "$_vt_dir" -c gpg.format=ssh -c gpg.ssh.program=ssh-keygen \
                -c gpg.ssh.allowedSignersFile="$_vt_signers" verify-tag "$_vt_ref" 2>&1)" || _vt_rc=$?
  rm -f "$_vt_signers"
  if [ "$_vt_rc" = 0 ] && printf '%s\n' "$_vt_said" \
       | grep -q "^Good \"git\" signature for $SKILL_SIGNING_PRINCIPAL with "; then
    say "  ✓ $_vt_ref is signed by $_vt_whose's author"; return 0
  fi
  case "$_vt_said" in
    *"illegal option -- Y"*|*"unknown option -- Y"*|*"cannot run ssh-keygen"*|*"cannot spawn ssh-keygen"*)
      # git's own sentences for an ssh-keygen that cannot verify (OpenSSH before 8.2, or none on PATH)
      warn "..."; return 1 ;;   # keep today's text: "too old: 2.34 or newer is needed"
  esac
```

Keep the glyph and every word the harness asserts (`IC` 13.3 in the code map: "signed by the skill's author", "does
not check out", "a release of TCC is signed by its author", "predates signed tags", "not a release tag"). The
principal in the pattern is a constant, not user text; `grep -q` with the literal is enough.

`install.ps1` (`Test-TagSignature`, `:936-952`): add `-c gpg.ssh.program=ssh-keygen`; accept
`$rc -eq 0 -and $said -cmatch ('(?m)^Good "git" signature for ' + [regex]::Escape($SkillSigningPrincipal) + ' with ')`
(case-sensitive: `-match` is not); the "cannot check" class matches the same four sentences with `-cmatch`. ASCII only
in the file's strings; no `exit` word (`IC:271-295`).

`upkeep.py` (`verify_tag`, `:102-125`): pass `env` to `git(...)`; add `"-c", "gpg.ssh.program=ssh-keygen"`; accept
`rc == 0 and re.search(rf'(?m)^Good "git" signature for {re.escape(principal)} with ', said)`.

- [ ] **Step 4: Run — expect PASS**: `python3 scripts/installer-consistency.py` (`installer-consistency OK`),
  `python3 SK/scripts/upkeep.py selftest`.

- [ ] **Step 5: Docs and commit** — `SECURITY.md`: the installers accept only the author's SSH signature, whatever
  the person's git or GPG configuration says. CHANGELOG bullet; `### Upgrading`: a person whose git signs through a
  helper (`gpg.ssh.program`) no longer sees a good release refused as "git too old".

```bash
git add install.sh install.ps1 SK/scripts/upkeep.py scripts/installer-consistency.py SECURITY.md CHANGELOG.md
git commit -m "#142: a signature is the author's or nothing -- one sentence accepted, gpg.ssh.program pinned (T-35)"
```

---

## Task 7: No readable tag, no install; a clone is the tag it checked (#142; audit T-37, T-45; J6a item 3)

**Files:**
- Modify: `install.sh:1000-1056` (the method's selection and checkout; `checkout_method` `:935-998`),
  `install.sh:1255-1275` (TCC's selection), `install.sh:855-859` (`settled_by_name`), `install.sh:191,194`
  (`newest_on_channel`), `install.sh:945`
- Modify: `install.ps1:1093-1192`, `:1323-1352`, `:914-915` (`Test-SettledByName`), `:273,275`, `:1047`, `:1122`,
  `:1335`; `:1165-1166` (a failed clone only warns today)
- Modify: `SK/scripts/upkeep.py:56,79-91,110-111` (the rule's third copy)
- Modify: `commands/install-tcc.md:20-28`
- Modify: `scripts/installer-consistency.py` (new `selection_problems`, `tag_rule_problems`; the `main` case at
  `IC:242`; `install-tcc.md` check `IC:684-696`)
- Modify: `ADVANCED.md:87`, `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 6's `verify_tag` / `Test-TagSignature`.
- Produces: `pick_method_ref` (sh) / `Select-MethodRef` (ps1): prints the ref to install, or fails with exit 1 and
  nothing changed for the method. `is_release_tag` (sh) / `Test-ReleaseTag` (ps1) / `upkeep.is_release_tag(name)`:
  one rule. Task 8's exit table uses the stop.

Today an empty `ls-remote` (no network, a proxy) makes both installers install `main`, unchecked
(`install.sh:1026`, `install.ps1:1125`), and on a re-run moves an already verified clone to `main`; TCC goes the same
way to its default branch (`install.sh:1270-1275`, `install.ps1:1347-1352`). Any non-release name passes
`settled_by_name` unchecked. The rule "is a release tag" is spelled seven ways (code map 4.2). A fresh clone takes
`clone --branch <ref>`, which prefers a branch of that name over the tag it then verifies.

- [ ] **Step 1: Write the failing cases**

In `installer-consistency.py`, a new `selection_problems(sh)` that cuts `pick_method_ref` and `is_release_tag` like
the signing harness does (`IC:187`) and runs them with `git` on `PATH` replaced by a stub whose `ls-remote` prints
nothing and exits 0 (and, second case, exits 128 with `fatal: unable to access`):
- no tag, no `--skill-ref` → rc 1, the words `could not read the method's release tags` and `nothing was installed`;
- no tag, `--skill-ref main` → rc 0, prints `main` and the word `UNSIGNED`;
- tags `v3.0.9 v3.1.10 v3.1.2 beta-v3.1.3-rc1 v3.1.2-x v03.1.1` → `v3.1.10` on stable.

`tag_rule_problems()`: one table of names answered the same by `is_release_tag` (sh, run), `upkeep.is_release_tag`
(imported by path) and the ps1 pattern (read from the file and applied with Python's `re` in .NET's terms: the
pattern must be the ASCII class `[0-9]` and end in `\z`, so the two engines agree):

```python
TAG_RULE_CASES = (("v3.1.2", True), ("beta-v3.1.3-rc1", True), ("v3.1.2-x", False), ("v3.1", False),
                  ("v3.1.2\n", False), ("v3.١.2", False), ("main", False), ("V3.1.2", False))
```

`IC:242`'s case `("main", "", 0, "not a release tag")` becomes `("main", "", 0, "UNSIGNED")` (an explicit `main` is
still allowed, and said).

The `install-tcc.md` check (`IC:684-696`) also requires `--python 3.12` on every `uv tool install` line.

- [ ] **Step 2: Run — expect FAIL** (`pick_method_ref` does not exist; `install-tcc.md` has no `--python`).

- [ ] **Step 3: Build**

1. `is_release_tag` (sh) with bash 3.2's `[[ =~ ]]`:
   `[[ "$1" =~ ^(beta-)?v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]]`, and the `-rc` part only with `beta-` (two
   patterns, as today's awk pair). `newest_on_channel`'s awk keeps its two patterns (they are already ASCII and
   anchored); `settled_by_name` and the fetch spec (`:945`) call `is_release_tag`. ps1: one `Test-ReleaseTag` with
   `-cmatch '^v[0-9]+\.[0-9]+\.[0-9]+\z'` and `'^beta-v[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+\z'`, used at `:914-915`, `:1047`,
   `:1122`, `:1335` (keep `Select-NewestOnChannel`'s two patterns as `IC:93-94` reads them, rewritten to `[0-9]` and
   `\z` together with `PS1_CHANNEL_SHAPES`). `upkeep.py`: `_TAG_RE`/`_CANDIDATE_RE` to `[0-9]` with `re.fullmatch`, and
   a public `is_release_tag(name)`.
2. `pick_method_ref` / `Select-MethodRef`: `--skill-ref` given → that name; a release name goes on to the signature,
   any other name is installed with one line `<name> is not a release: it is installed UNSIGNED, unchecked`.
   Not given → the newest stable tag; none readable → `stop 1 "could not read the method's release tags (no
   network?) -- nothing was installed or changed for the method; run again when GitHub answers, or name a tag with
   --skill-ref"` (sh; `Stop-Installer 1; return` in ps1, with the same words).
3. TCC: no readable TCC tag → TCC is not installed (`warn` with the same reason) and counts as missing (Task 8); the
   default-branch fallback goes. `--tcc-ref <name>` keeps the explicit path, printed UNSIGNED when not a release.
4. The clone takes the tag, not a branch: `git init`, `git fetch --depth 1 <repo> +refs/tags/<tag>:refs/tags/<tag>`,
   `git checkout --quiet refs/tags/<tag>^{commit}` (sh `checkout_method`'s fresh branch, ps1 `:1073-1090`); after
   checkout, `git rev-parse HEAD` must equal `git rev-parse "refs/tags/<tag>^{commit}"`, or the fresh clone is removed
   (the update restores the old HEAD) and the install stops with 1.
5. ps1: a failed fresh clone stops with 1, as sh does (`:1165-1166`).
6. `commands/install-tcc.md`: the three lines pin TCC's newest release at build time
   (`git ls-remote --tags --refs https://github.com/ayukhno/autosound-tcc 'v*'`, newest by version) and carry
   `--python 3.12`; `:24-28` says what `installer-consistency.py` really checks (the lines agree with each other and
   carry the flag; the installers resolve TCC's tag at run time).

- [ ] **Step 4: Run — expect PASS**: `python3 scripts/installer-consistency.py`, `python3 SK/scripts/upkeep.py
  selftest`, `bash -n install.sh`.

- [ ] **Step 5: Docs and commit** — `ADVANCED.md:87`: `--skill-ref`/`--tcc-ref` with a name that is not a release
  install it unsigned and say so; with no network the installer stops instead of installing `main`. CHANGELOG
  (Upgrading: an offline first install now stops with exit 1 where it used to install `main`).

```bash
git commit -m "#142: no readable tag, no install; one release-tag rule; a clone is the tag it checked (T-37, T-45)"
```

---

## Task 8: The exit contract and the receipt (#142; audit T-44 part, T-45 part; J6a items 4–5)

**Files:**
- Modify: `install.sh` — every `exit 1` after the option parsing (`:670, 675, 820, 1010, 1015, 1046, 1051, 1052`)
  through a new `stop`; the "Checking" block `:1490-1563`; the receipt `:1765-1777`; `plugin-ready` `:1779-1783`; the
  end `:1792-1795`; the libraries `:1081-1119`
- Modify: `install.ps1` — `Stop-Installer` (`:94-102`); "Checking" `:1570-1635`; receipt `:1807-1820`;
  `plugin-ready` `:1822-1826`; the end `:1834-1840`; the libraries `:1195-1227`
- Modify: `scripts/installer-consistency.py` (new `exit_contract_problems`), `SK/scripts/autosound_ai.py:3173-3214`
  (the receipt's reader: the new fields), `.github/workflows/checks.yml` (a new job), `README.md:62-68` and `FAQ.md`
  (the exit codes, one line each), `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 7's `stop 1 …` / `Stop-Installer 1`.
- Produces: the installers' exit table — **0** ready · **1** stopped: the method was not installed or changed
  (steps before it, such as Claude Code, may have run) · **2** usage · **3** installed, not ready, the missing parts
  named. `INSTALLER_VERSION="3.1.2"` in `install.sh` and `$InstallerVersion = "3.1.2"` in `install.ps1`, held equal to
  `.claude-plugin/plugin.json`'s version by `installer-consistency.py` (the release's bookkeeping moves all three).
  The receipt (`install-receipt.json`): today's fields kept, `installer_sha256` included (the Arbiter's decision,
  `docs/W-2-DECISIONS.md:34`, row 26), plus `installer_version`, `status` (`ready` · `not ready` · `stopped`),
  `missing` (a list of short names), `python` (`"<path> <version>"` of the `python3` the method runs on).

Today no exit code depends on the result: both installers end "Installed, with the warnings above." and exit 0
(`install.sh:1562`, `install.ps1:1635`); `plugin-ready` is written either way, so a broken plugin install is never
told again; the receipt is written only at the end, never on a stop, and `install.sh` builds its JSON with no
escaping. "Stopped, nothing changed" cannot be promised: the method's stops come after Claude Code (and, on Windows,
Git, uv and Python) are installed (code map §6), so exit 1 promises only the method's copy.

- [ ] **Step 1: Write the failing cases** — `exit_contract_problems(sh)` cuts a new `finish` function (Step 3) and
  runs it with `MISSING` empty → rc 0, `Installed.`; `MISSING="numpy"` → rc 3, `Installed, NOT ready: numpy`; and
  checks the receipt it writes into a temp `XDG_DATA_HOME` parses as JSON (`json.loads`) with `status`, `missing`,
  `installer_version`, `installer_sha256`, `python`, even when `ENGINE_DID` carries a quote and a backslash. ps1: the
  file's end calls `Stop-Installer 3; return` under `-not $ok` (string presence, as `IC:560-584` reads ps1), and
  `plugin-ready` sits inside `if ($ok)`. A new check: `INSTALLER_VERSION` = `$InstallerVersion` =
  `plugin.json`'s `version`.

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Build**

1. `install.sh`: `MISSING=""` and a helper `missing() { MISSING="${MISSING:+$MISSING, }$1"; ok=0; }` used at every
   place that sets `ok=0` today (`:1500, 1504, 1507, 1514, 1522, 1530, 1538`) with the short names `numpy`, `scipy`,
   `the method`, `the method (2.x line)`, `the beta copy`, `TCC`, `Claude Code`. The libraries are judged by importing
   with the `python3` the method runs on: `numpy` and `scipy` missing is `missing`; `matplotlib` missing is a warning
   (plots only).
2. `write_receipt <status>`: builds the JSON with `python3 -c 'import json,sys; …'` when `python3` runs, otherwise
   with a shell function that escapes `\` and `"` and drops control characters; same fields in the same order as
   ps1's `ConvertTo-Json`. Called by `stop` (status `stopped`) and by `finish`.
3. `stop <code> <text>`: `warn` the text, `write_receipt stopped`, `exit <code>`. Every `exit 1` after the options
   becomes `stop 1 "<today's text>"`; the `exit 2` usage lines stay as they are (no receipt for a typo).
4. `finish`: prints `Installed.` (rc 0) or `Installed, NOT ready: $MISSING` with one line per missing part saying
   what to do (today's warn lines), writes the receipt, writes `plugin-ready` only when ready, and ends with
   `exit 3` when not ready. It is the script's last statement.
5. ps1: the same in its own terms — `$Missing` list, `Write-Receipt`, `Stop-Installer` writes the receipt with
   `stopped`, the end runs `if (-not $ok) { Stop-Installer 3; return }` after the receipt and before nothing else;
   `plugin-ready` only `if ($ok)`.
6. `autosound_ai.py`'s `receipt_line` (`:3181-3194`) prints `status` and `missing` when present (older receipts
   without them still read, as today).
7. `.github/workflows/checks.yml`: a job `installers-ubuntu` on `ubuntu-24.04`, `needs: gate`, no `setup-python`
   (so `python3` is `/usr/bin/python3`, externally managed), runs
   `bash install.sh --terminal --no-engine --yes` with `timeout-minutes: 20`, then asserts the exit code is 3 and
   that `~/.local/share/autosound/install-receipt.json` says `"status": "not ready"` with `numpy` in `missing`
   (PLAN-AUDIT §3 J6a item 5). Read `install.sh --help` first for the exact flag names of the terminal mode and the
   unattended answer; if the job finds the install ready (a runner image that changed), it fails naming that.

- [ ] **Step 4: Run — expect PASS**: `python3 scripts/installer-consistency.py`, `bash -n install.sh`,
  `python3 SK/scripts/autosound_ai.py selftest` (its argv from `scripts/selftests.txt`). The new CI job runs in the PR.

- [ ] **Step 5: Docs and commit** — README and FAQ: one line, the four codes. CHANGELOG `### Upgrading`: a script or
  person that runs the installer can now tell ready (0) from installed-but-not-ready (3); the plugin's set-up note
  keeps coming back until an install is ready.

```bash
git commit -m "#142: the installers' exit contract -- 0 ready, 1 stopped, 2 usage, 3 not ready -- and an honest receipt"
```

---

## Task 9: What a re-run repairs, and what the installers say (#142; audit T-38, T-39, T-40, T-44, E-time, E-pair)

**Files:**
- Modify: `install.sh:1032-1056` (the update branch links nothing, T-38), `:1127-1180` (engine: T-40, T-44),
  `:41,46,169,173` (E-pair), `:744,748` (E-time)
- Modify: `install.ps1:1128-1161` (T-38), `:1235-1298` (T-40, T-44), `:47,52,201,205` (E-pair), `:750,754` (E-time)
- Modify: `install.cmd:31` (E-pair)
- Modify: `SK/scripts/upkeep.py:242-257` (`plugin_ready`, T-39) and its selftest `:970-988`
- Modify: `SK/rew_tool/resonalyze_engine.py:2968-2972` (`fetch-binary` exit codes), `:353-398` (`fetch_binary`)
- Modify: `README.md:48` and `FAQ.md:94` with their uk/de/pl copies (E-time; the Advisor translates),
  `scripts/installer-consistency.py` (`IC:586-615` engine shapes; `IC:443-469` the example pair), `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 8's `missing` and `finish`.
- Produces: `fetch-binary` exits **0** installed (or already installed at this pin) · **3** refused (the digest does
  not match; nothing installed) · **4** this release carries no engine for this machine · **5** the release could not
  be reached. The installers record each in the receipt's `engine` in those words.

- [ ] **Step 1: Write the failing tests**
  - `upkeep.py` selftest: `plugin_ready` writes `v3.1.2\n` byte for byte (read in binary; red on Windows today,
    `\r\n`); the hook `hooks/session-start.sh` with a ready file present prints nothing — on every platform where
    `bash` runs (Git Bash on the Windows job), not only `os.name != "nt"` (`UP:977`).
  - `resonalyze_engine.py` selftest: `fetch_binary` against a local fake release folder — a missing asset → 4, an
    unreachable URL (`http://127.0.0.1:1/…`) → 5, a digest mismatch → 3 with nothing installed, the same pin already
    installed → 0 without a download (the download function is the module's own; inject it, do not patch `urllib`).
  - `installer-consistency.py`: the update branch (`install.sh:1043-1046`) links `SKILL_HOME` when the link is
    missing (string shape, both installers); the example pair is one pair in all nine places; the engine shapes add
    `5)` (sh) and `$engineRc -eq 5` (ps1).

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Build**
  1. T-38: the update path re-creates a missing `~/.claude/skills/autosound-tuning` link (sh `ln -s`, ps1
     `New-Item -ItemType Junction`), with the same guards the fresh path has (a link that is not ours, or a real
     folder, is left and warned about, `:1032-1042`, `:1128-1141`).
  2. T-39: `plugin_ready` opens the file with `newline="\n"`.
  3. T-40: in a plugin copy (no `.git` above `SK`), the engine's `auto` policy fetches the binary instead of
     building (a build runs `git submodule update`, which a plugin copy cannot).
  4. T-44: `fetch-binary` returns the four codes above; `fetch_binary` returns `installed` without a download when
     the installed engine's pin equals the requested tag; the installers' `case` gains `5)` / `-eq 5` with the words
     `the release could not be reached -- run the installer again later`.
  5. E-time: the README/FAQ line says what the installers say: "10–20 minutes the first time on a Mac without the
     developer tools, a few minutes otherwise" (the uk/de/pl lines by the Advisor).
  6. E-pair: the example pair is the minor pair the hub's tag ledger records, `v3.1.0` / `v1.1.0` (hub #239), in all
     nine places.

- [ ] **Step 4: Run — expect PASS**: the three selftests, `python3 scripts/installer-consistency.py`,
  `python3 scripts/i18n-check.py`, `python3 scripts/docs-check.py`.

- [ ] **Step 5: Commit**

```bash
git commit -m "#142: a re-run repairs the link; plugin-ready on Windows; the engine's codes; one install time, one example pair"
```

### Group review — installs (Tasks 6–9)

`pr-review-toolkit:silent-failure-hunter` and `pr-review-toolkit:pr-test-analyzer` (both **opus**) on the group's
diff, one fix round; then `scripts/run-selftests.sh | tail -1`. Before the tag (Task 19): the Arbiter's run on the
Windows VM — `install.cmd` twice (a fresh folder and a re-run), the exit code each time, and the receipt.

---

## Task 10: What the reviewer is told (#143; audit I-2, I-5, the template's rows, G1; PLAN-AUDIT §3 J8)

**Files:**
- Modify: `SK/scripts/autosound_ai.py` — `compile_prompt` (`:3368-3390`), a new `ledger_head_block(project_dir)`,
  `main` (`:3543-3564`, where the layers are read), `_persist_review` (`:3264-3297`, G1), the clipboard rung
  (`:3751-3752`), `run_doctor` (`:2938-2943`, the contract line), the selftest (`:1749`, block `:1829-1888`)
- Modify: `SK/scripts/reviewer-tuning.txt:1-2`
- Modify: `SK/assets/data-contract-template.md` — `:11` (a template that is copied), `:26` against `:155` (role
  rotation), `:30-37` (its "Single source of truth" heading), `:40`, `:62`, `:156` (Trace IDs the resolver refuses)
- Modify: `SK/references/phases/phase_-1_intake.md:176-178` (the `cp` of the contract), `SK/references/tooling/
  setup-critic-channel.md:351-357` (project-local first), `SK/references/core/process-control.md:26` (the round's
  reviewer task)
- Modify: `RT/contract.py` (`check_project`: a project copy of the reviewer's contract that differs from the
  skill's, as a warning row), `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 2's `Process.record_reviewer` under the lock (G1 records through it).
- Produces: the prompt's header `====== AUTOSOUND CONTEXT (prose view — the machine files win) ======` and a block
  `====== LEDGER HEAD (the machine files: what is banked) ======` in critic and advisor prompts.

Today the reviewer reads "the AUTOSOUND CONTEXT is the single source of truth" (`reviewer-tuning.txt:1`, the header at
`autosound_ai.py:3380`) while the method's truth is the ledger (`data-contract-template.md:30-37`, `SKILL.md:83`); no
code gives the reviewer the ledger (the Generator writes the package; nothing in the door opens `state/`); the
sessions are told to copy the contract into `rew_analitic/` (prose only), and that copy is read first
(`find_file`, `:247-269`); the template teaches Trace IDs the resolver refuses (`m-L_split_320Hz_LR4`,
`<channel>_baseline`: `parse_name` gives None) and "rotate afterward" against "No role rotation"; the door prints
`process.py ... reviewer <vendor> ...` with `<vendor>` literal instead of recording the step.

- [ ] **Step 1: Write the failing tests** (`autosound_ai.py` selftest, new `_check_*` in its loop):

```python
def _check_the_machine_files_win_once():
    <an assembled critic prompt (tuning, an empty context and package): "the machine files win" occurs exactly once
     (case-insensitive) and "single source of truth" not at all; advisor the same; ask carries neither>


def _check_the_ledger_head_rides_in_the_prompt():
    <a temp project with a ledger (PresetHistory.snapshot of a minimal state, as state.py's own fixtures do): the
     critic prompt holds "====== LEDGER HEAD" with the HEAD's id; a project with no ledger: the block says
     "no ledger in <project> yet"; ask: no block>


def _check_the_template_teaches_titles_that_resolve():
    <every Trace ID example in data-contract-template.md (the backticked token after "e.g." on the Trace ID lines)
     parses with naming.parse_name WITH a method; "rotate" does not occur in the template>


def _check_the_door_records_the_review():
    <a temp project at phase 1; _persist_review(...) for vendor "gemini", model "m": the journal has one
     critic_called whose review path is the file it wrote; a second call for the same file adds none>
```

- [ ] **Step 2: Run — expect FAIL**: `python3 SK/scripts/autosound_ai.py selftest`.

- [ ] **Step 3: Build**
  1. I-2: the header text above; `reviewer-tuning.txt:1-2` → "TUNING — a regulated task: the DATA CONTRACT below is
     the protocol. The LEDGER HEAD is what is banked; the AUTOSOUND CONTEXT is its prose view, and where they disagree
     the ledger wins — say the divergence." The template's `## 1.` heading becomes "## 1. The machine files are the
     truth; the prose is a view of it" (its body already says so).
  2. `ledger_head_block(project_dir)`: the project is `$AUTOSOUND_PROJECT_DIR`, else the parent of `PROJECT_MIRROR`
     when that is `<dir>/rew_analitic`, else the working folder; the ledger is read through `state.py`
     (`_siblings().load`, `PresetHistory` on `<project>/state`), never parsed by hand: the HEAD's id, its slot, its
     note and date, and the per-channel rows the ledger's own render prints for that version, cut at 60 lines with a
     last line saying how many were left out. An unreadable ledger is said in the block (`is_unreadable`), never a
     traceback; no ledger → `no ledger in <project> yet`. Tuning tasks only.
  3. I-5: the contract is the skill's own: `find_file` keeps its order for the CONTEXT but reads
     `data-contract-template.md` from `SK/assets/` only; `doctor` prints `! a project copy <path> differs from the
     skill's contract — the reviewer gets the skill's; delete the copy` for a differing `rew_analitic/` or project
     copy (a warning, not `ok = False`); `contract.py check` reports the same as a warning row (its `--json` gains one
     `warnings` entry; `ok` unchanged). The template's `:11` and `phase_-1_intake.md:178` stop telling anyone to copy
     it; `setup-critic-channel.md:351-357` says where the door reads each file now. The template's `<DSP>`
     placeholders become a sentence: the system's specifics come from the AUTOSOUND CONTEXT and the LEDGER HEAD.
  4. The template: Trace ID examples in the grammar (`naming-and-structure.md:72`): `w-L_1 (sw)` for a capture,
     `<code>_1 (<method>)` for the first one; `:155` "Round 1: Generator — AI-A, Critic — AI-B; the seats hold for
     the session (§ No role rotation)". `process-control.md:26`: Mode A's call is one Critic pass on the round's whole
     batch; an Advisor call is for an open question at a solution-search node (as `review-loop.md:39,54` and
     `SKILL.md:58` say).
  5. G1: `_persist_review` records the step itself after writing the review file —
     `Process(<project>/process).record_reviewer(<vendor>, <model>, review=<rel>, mode=<mode>)` loaded by path
     (`state/process.py` through `_siblings()`), with `<vendor>` the provider's name as `process.py reviewer` takes it;
     skipped when the journal's last `critic_called` already names that review file (TCC's `call_critic` may record
     the same call); a refusal (`is_busy`, `is_unreadable`, a missing process folder) prints today's instruction line
     with the vendor and model filled in, and the review answer is still returned. The clipboard rung keeps printing
     its line (the answer comes later), with the vendor and model filled in.

- [ ] **Step 4: Run — expect PASS**: `python3 SK/scripts/autosound_ai.py selftest`, `python3 RT/contract.py <argv>`,
  `python3 scripts/docs-check.py`.

- [ ] **Step 5: Commit**

```bash
git commit -m "#143: the reviewer is told the machine files win and is given the ledger HEAD; one contract; the door records its review"
```

---

## Task 11: One home for each prose file (#143; audit I-21)

**Files:**
- Modify: `RT/state/process.py` — `_changelog_read` (`:662-677`) and `handoff` (`:2853-2866`)
- Modify: `SK/scripts/harvest_inbox.py` (`:18-19`, `:34-35`, `:94-100`, `:152-155`)
- Modify: `SK/scripts/autosound_ai.py` — `AUDIT_TRAIL` (`:274-277`), `find_file` for `autosound_context.md`
  (`:247-269`), `run_doctor` (a differing `rew_analitic/autosound_context.md`)
- Modify: `SK/references/phases/phase_-1_intake.md:158-178`, `SK/references/phases/phase_3_control.md:67`,
  `SK/SKILL.md:125`, `SK/references/core/naming-and-structure.md:128-137`, `SK/references/core/feedback-loop.md:121-122`,
  `SK/references/tooling/setup-critic-channel.md:351-357`, `CHANGELOG.md`

**Interfaces:**
- Produces: the project root is the home of `tuning-changelog` (`.md` or none), `audit-trail.md`, `skill-inbox.md` and
  `autosound_context.md` (the structure doc's tree, `naming-and-structure.md:128`); `rew_analitic/` holds measurements,
  exports and target curves, and the reviewer's own memory file. Every reader looks at the root, then at
  `rew_analitic/` with one warning line naming the file to move.

Today `handoff` reads the changelog at the root only and says nothing when it is not there (`:2861-2865`: no
`missing`, no HEAD-drift warning); `harvest_inbox.py` reads `rew_analitic/` only; the door writes
`rew_analitic/audit-trail.md` and reads `rew_analitic/autosound_context.md` before the root's; the documents name
both folders.

- [ ] **Step 1: Write the failing tests**
  - process.py: a project whose changelog is only in `rew_analitic/` → `handoff --json` reads its CONTINUE block and
    has one `warnings` entry naming the move; no changelog anywhere → one `warnings` entry ("no tuning-changelog at
    <root>: the ▶️ CONTINUE block lives there"), `ok` unchanged.
  - harvest_inbox.py: an inbox at the root is harvested; one only in `rew_analitic/` is harvested with a warning; none
    → today's error, naming the root.
  - autosound_ai.py: the audit trail lands at `<project>/audit-trail.md`; a root `autosound_context.md` wins over a
    `rew_analitic/` copy, and `doctor` names a copy that differs.
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Build** the readers and the writer as above; the documents say the one tree (the intake creates the
  three prose files at the root; nothing is copied into `rew_analitic/`).
- [ ] **Step 4: Run — expect PASS**: the selftests of `process.py`, `harvest_inbox.py`, `autosound_ai.py`;
  `python3 scripts/docs-check.py`.
- [ ] **Step 5: Commit**

```bash
git commit -m "#143: one home for each prose file -- the project root; readers fall back to rew_analitic/ and say so"
```

---

## Task 12: The user's path in the text — the slot rule, the reviewer and the car, the visits (#144; P3, P9, P10)

**Files:**
- Modify: `SK/references/core/naming-and-structure.md` §1a (`:34-41`) and §5 (`:184-185`),
  `SK/references/core/preset-strategy.md:3,11-16,21`, `SK/references/phases/phase_5_variations.md:49-50` (P3)
- Modify: `SK/SKILL.md` (Review Channel, `:194-202`), `SK/references/core/review-loop.md`,
  `SK/references/phases/virtual-first.md:372,397-398`, `SK/references/phases/phase_3_control.md:7,11,15,17,19,39-43`,
  `SK/references/core/process-control.md:26` (P9)
- Modify: `README.md:8,101,103`, `FAQ.md:117-118` and the uk/de/pl files at the same lines (P10; the Advisor
  translates)
- Modify: the stale cites the code map found in these files: `preset-strategy.md:3,21` (a base/voicing rule SKILL.md
  does not hold) and "Pre-session #4" for the input-reset trap (`RT/intake.py:857,1014,1171,1176` and its
  `intake_i18n/*.json` copies if they carry the note, `SK/references/core/project-intake.md:175-176`,
  `preset-strategy.md:16`) — the input check is SKILL.md's Pre-Session item 1
- Modify: `scripts/docs-check.py` (a rule for each: P3's sentence in its home; P9's line in both homes),
  `CHANGELOG.md`

The user-path audit is private: these items are worked from `docs/PLAN-AUDIT-2026-10.md:156,159,160` and the files
they name, never from its text.

- [ ] **Step 1: Write the failing rules** — `docs-check.py`: rule `slot-names`: `naming-and-structure.md` §1a holds the
  slot rule's sentence ("a DSP slot is named by its preset number and its configuration's name"), and no method file
  calls a slot "memory N", "slot N" or "Preset N" alone (the pattern: the word followed by a bare number, outside code
  spans and REW's own "EQ slot"); rule `reviewer-at-desk`: SKILL.md's Review Channel and `review-loop.md` each carry
  "never from inside a car session". Fixtures in the rule selftests for a red and a green case each.
- [ ] **Step 2: Run — expect FAIL** (`python3 scripts/docs-check.py`).
- [ ] **Step 3: Write the text**
  1. P3, one home (`naming-and-structure.md` §1a): "A DSP slot is named by its preset number and its configuration's
     name — `3.S-shelf`, `1.SQ-1`: the number the device shows, the name `state.py … config save` gave the
     configuration. Never a bare number ('memory 3', 'slot 3') or 'Preset 2'." §5, `preset-strategy.md` and
     `phase_5_variations.md:49` point to it; `:49`'s example becomes `2.FULL-v1` beside `1.SQ-1`.
  2. P9: one line in the Review Channel and in `review-loop.md`: "The reviewer is called at the desk, never from
     inside a car session: the car session measures and listens; what needs a verdict goes into the next desk round."
     Phase 3 follows it: the car session (3.1–3.3) captures, does MMM and the ear's minimum pass, and backs up the
     DSP's configuration before leaving; 3.4's two independent cross-vendor verdicts run at the desk after it, and the
     technical lock is banked there (`virtual-first.md:397`, `phase_3_control.md` §2 and its gate, `process-control.md:26`).
     The two places stop calling these A/B: those letters are the reviewer modes `process-control.md` owns.
  3. P10: README `:8,101,103` and FAQ `:117-118` say the count the method prescribes: read `virtual-first.md`'s phases
     for which ones happen in the car and write that number ("two visits make a tune: one to measure, one to enter the
     numbers, verify and lock; the fine-tuning by ear after it takes as many as you like" — adjust to what the phases
     say). English first; uk/de/pl through the Advisor (`autosound_ai.py ask <package.md>`, one package per
     language with the four lines); `python3 scripts/i18n-check.py` green.
- [ ] **Step 4: Run — expect PASS**: `python3 scripts/docs-check.py`, `python3 scripts/i18n-check.py`,
  `python3 RT/intake.py <argv>` if its strings changed.
- [ ] **Step 5: Commit**

```bash
git commit -m "#144: the slot rule, the reviewer at the desk and never in the car, and how many visits a tune takes"
```

---

## Task 13: SKILL.md's budget as checks, and the trigger baseline (#145; S2 tasks 1 and 3's first half)

**Files:**
- Modify: `scripts/docs-check.py` — a new rule `skill-budget` (its constants beside `GUARDRAILS`, `:100-116`;
  registered in `RULES`, `:876-889`; selftest fixtures with the others, `:1340-`)
- Create: `scripts/reading-cost.py` (`--selftest`; `--check` against `scripts/reading-cost-baseline.json`)
- Create: `scripts/reading-cost-baseline.json` (today's table)
- Modify: `scripts/run-selftests.sh` (`reading-cost ok scripts/reading-cost.py --selftest`, `reading-cost-in-tree
  ok scripts/reading-cost.py --check`), `RT/capabilities.py` (`NOT_ON_BOARD`; remove the `skill_metrics.sh` row,
  `:114`)
- Delete: `SK/scripts/skill_metrics.sh` (F15: wired nowhere, fails on its own cap)
- Modify: `SK/evals/README.md` (the baseline runs)

**Interfaces:**
- Produces: `skill-budget` — (a) the frontmatter description folds to ≤ 1,024 characters; (b) `## 📁 Reference Map`
  is the last `##` section; (c) the bytes from the file's start to that heading are ≤ 17,500; (d) the rule manifest:
  `SKILL_RULE_PHRASES`, the phrase of every rule SKILL.md carries today (each Core Guardrails bullet's bold head, each
  Pre-Session item, the Phase Sliding Window sentence, the Review Channel's cadence and ladder, each Output Style
  rule), each present in SKILL.md before the Map. A rule moved out of SKILL.md leaves the manifest in the same
  commit, and the commit names where it went.
- Produces: `reading-cost.py` — per phase, the tokens (characters / 4) a session reads: SKILL.md, the active phase's
  file, the next phase's file (to its `## 🎯 Goal-node` once Task 14 lands that rule), and the files every phase reads
  (the audit's §3.2 model); `--check` fails when a phase reads more than its baseline.

The code map: SKILL.md is 37,763 bytes; the first 5,000 tokens Claude Code re-attaches after a summary end at line
`:124` (chars/4) or `:169` (words × 1.3), so the Review Channel (`:194`) and Output Style (`:206`) are lost either
way; the Map is the 6th of 8 sections; the description is 1,807 characters and the listing shows 1,536; nothing
checks any of it.

- [ ] **Step 1: Write the failing checks** — the rule's selftest fixtures (a description of 1,025 characters, a Map that
  is not last, 17,501 bytes before it, a manifest phrase missing — each red; a small SKILL.md that passes — green).
  The in-tree run is RED on today's SKILL.md, by design: Task 14 makes it green. `reading-cost.py --selftest` on
  fixtures; its baseline is written from today's tree (`--write-baseline`), so `--check` is green now and holds every
  later commit to it.
- [ ] **Step 2: The trigger baseline (I-4's "before")** — three runs of `python3 SK/evals/run_trigger_eval.py
  --eval-set SK/evals/trigger-eval-set.json --model claude-sonnet-4-6 --workers 4` on today's description, in an
  environment where `claude -p` does not see the other car-audio skill (`anthropic-skills:rew-car-audio-tuning`):
  find the setting that hides it for one run (a `--settings` file with that plugin disabled); if none works without
  the Arbiter, the controller asks him to disable it for the runs (a stop named in "What needs the Arbiter"). The
  three scores go into `SK/evals/README.md` with the date and the description's commit.
- [ ] **Step 3: Run** — `python3 scripts/docs-check.py --selftest` green; `python3 scripts/docs-check.py` red on
  `skill-budget` only; `python3 scripts/reading-cost.py --check` green.
- [ ] **Step 4: Commit**

```bash
git commit -m "#145: SKILL.md's budget as a docs-check rule, a reading-cost check, the trigger baseline; skill_metrics.sh retired"
```

---

## Task 14: The cut — SKILL.md back under the budget, every moved sentence accounted for (#145; S2 task 2; I-3, I-4, I-19, I-26, I-30)

**Files:**
- Modify: `SK/SKILL.md` (all of it)
- Modify (homes the moved text lands in): `SK/references/core/why-these-rules.md` (stories, history lines),
  `SK/references/core/process-control.md:63-97` (the stop's one home), `SK/references/core/review-loop.md:48-72`
  (cadence), `SK/references/tooling/capture-session-sheet.md` or `process-control.md` (capture mechanics),
  `SK/references/core/naming-and-structure.md` (step ids), `SK/references/tooling/helix-dsp-ultra-s.md` (the Helix
  example), `SK/references/core/feedback-loop.md:58` (the side-effect gate's clause)
- Modify (pointers into SKILL.md that must still land): `RT/state/process.py:7802` (the printed "EXIT CHECKLIST
  (SKILL.md)"), `RT/car_profile.py:70` (a line cite), `SK/references/core/process-control.md:86`,
  `phases/phase_4_listening.md:75`, `core/review-loop.md:17,81`, `phases/phase_0_baseline.md:215`,
  `core/process-phases.md:10-15`, `phases/virtual-first.md:149`, `phases/phase_-1_intake.md:167`,
  `core/feedback-loop.md:142`, `core/happy-paths.md:12,25`, `tooling/installation.md:128-129`, `CLAUDE.md:102`
- Modify: the Map rows for the 494 KB visualizer and `core/knowledge-architecture.md` (I-26): off the Map, each with
  the `ORPHAN_MARK` line in its head, or reached from a reference that names it
- Create: `scripts/move-check.py` (`--selftest`; `python3 scripts/move-check.py <base> <head>`)

**Interfaces:**
- Consumes: Task 13's `skill-budget`, `SKILL_RULE_PHRASES`, `reading-cost.py`.
- Produces: SKILL.md with the Map last, ≤ 17,500 bytes before it, a description ≤ 1,024 characters; `move-check.py`:
  every sentence removed from SKILL.md between two commits appears, normalised (whitespace, markdown emphasis), in
  another tracked file at `<head>`, or is listed after `dropped:` in a commit message of the range.

- [ ] **Step 1:** `move-check.py` with its selftest (a moved sentence passes, a lost one fails naming it, a dropped one
  named in a message passes).
- [ ] **Step 2: The order and the cut** (advised: PLAN-AUDIT's smallest variant):
  1. Review Channel and Output Style move before the Map; the other sections keep their order.
  2. Out of SKILL.md, each to its home, SKILL.md keeping the rule's sentence and a pointer: the language anecdote
     (`:74-79`), the stop procedure (`:85-93` → `process-control.md`, its one home; SKILL.md keeps the order's one
     line and the phrase `EXIT CHECKLIST`, or `process.py:7802` names the new home), the capture mechanics (`:106`),
     the step-id detail (`:103`), the Helix example (`:100`, `:110`), the history lines (`skill #N`, dates, `S-NNN`,
     `HUB-`, `TCC-` at `:68,83,87,99,103,106,109,110,119,133,222-225`), the second copy of "stateless reviewer"
     (`:58` against `:196`), the cadence's copy of `review-loop.md:48-72` (`:199`).
  3. I-19: each doctrine one home — the language rule (SKILL.md keeps it; `project-intake.md:89-91`,
     `why-these-rules.md:90-102`, `phase_-1_intake.md:40` point to it), the stop procedure (`process-control.md`).
  4. I-3: near the top, one line: "After a context summary, read this file again before the next step — the summary
     keeps only its first part."
  5. The next phase is read only to its `## 🎯 Goal-node` (`:135`'s rule; the PHASE_SOURCE and PHASE_WINS sentences
     stay word for word on one line — `docs-check` rule `phase-source`).
  6. I-4: the description to ≤ 1,024 characters — the Nono/ResoNix parenthesis, the example parentheses and the gate
     clause (its home is `feedback-loop.md:58`) go; the triggers in uk/de/pl stay.
  7. I-30: the Arbiter is "they" / "the Arbiter", never "he", in SKILL.md and in every sentence this task rewrites
     (`project-intake.md:89`, `phase_-1_intake.md`).
  8. I-26: the two Map rows above.
  9. Every pointer in the Files list lands where it says.
- [ ] **Step 3: Run** — `python3 scripts/docs-check.py` all green (`skill-budget` included; `references-orphans`,
  `phase-source`, `data-not-instructions`, `step-ids` untouched); `python3 scripts/move-check.py <base> HEAD` green;
  `python3 scripts/reading-cost.py --check` green, and its new table into the baseline with `--write-baseline`;
  `python3 RT/state/process.py selftest` if `:7802` changed.
- [ ] **Step 4: Commit** — one commit per section moved is fine; each message ends with a `dropped:` list (possibly
  empty).

```bash
git commit -m "#145: SKILL.md under the re-attach budget -- the Map last, the rules first, each moved sentence in its home"
```

---

## Task 15: The § index, the report words, the evals and the trigger runs (#145; S2 tasks 3–6; I-4, I-14, I-24, I-25, I-26)

**Files:**
- Modify: `SK/references/core/diagnostic-techniques.md` (a generated § index after its intro, `:3`),
  `SK/references/phases/phase_2_eq.md:77` (`§50` → the section it means)
- Create or modify: the index's generator and check — a rule `section-index` in `scripts/docs-check.py` (the index
  lists every numbered `##` with its title, in order; a `§N` pointer to the file names a section that exists)
- Modify: `SK/references/core/naming-and-structure.md:34-41` — the word table gains de and pl columns beside uk
  (I-14; the Advisor translates); `SK/SKILL.md:219` keeps pointing to it
- Modify: `SK/evals/trigger-eval-set.json` (cases: an issue or bug report about the skill or TCC in en/uk/de/pl, a
  resume inside a project folder, a TCC opener), `SK/evals/README.md` (its counts, `:3`; the runs)
- Modify: `RT/project_seed.py:283-299` (`CLAUDE_MD`: "Load the `autosound-tuning` skill for every request in this
  folder.") (I-24)

- [ ] **Step 1: Write the failing rule** `section-index` (fixtures red/green); run it red on today's tree.
- [ ] **Step 2: Build** the index (generated by `docs-check.py --write-index`, so it is never typed), the `§50` fix, the
  word table (English first; de and pl through the Advisor), the eval cases and the project `CLAUDE.md` line.
- [ ] **Step 3: The trigger runs (I-4's "after")** — three runs, as Task 13 Step 2, on the new description and the new
  set; and three on the new set at the old description (`git stash` of SKILL.md's frontmatter only, or a checkout of
  the base's SKILL.md into the hidden copy the runs read), so the before/after compare like with like. The six
  scores and their dates into `SK/evals/README.md`. A drop larger than the spread the README records (2–3 on 22
  queries) is a finding for the group review, with the queries that changed.
- [ ] **Step 4: Run — expect PASS**: `python3 scripts/docs-check.py`, `python3 scripts/i18n-check.py`,
  `python3 RT/project_seed.py <argv>`.
- [ ] **Step 5: Commit**

```bash
git commit -m "#145: the diagnostic techniques' section index, the report words in four languages, current evals and the trigger runs"
```

### Group review — what a session reads (Tasks 10–15)

One opus reviewer over the group's diff with three questions: does each rule that left SKILL.md still reach the phase
that needs it (S2's medium risk); does each J8/J7 change say what its source says; do the trigger runs show a recall
drop. `python3 scripts/move-check.py <group base> HEAD`; then `scripts/run-selftests.sh | tail -1`.

---

## Task 16: Subprocesses with a timeout; helpers that report their failures (#146; audit K-5, T-41, T-42, T-49, T-50, F8)

**Files:**
- Modify (timeouts, code map §1.1 — the 21 production calls without one): `RT/gates/side_effect.py:95-97`
  (`_subprocess_runner`), `RT/path_check.py:146`, `RT/resonalyze_engine.py:134,139,410,414,432`,
  `SK/scripts/autosound_ai.py:143,145,150,283-295,3044`, `SK/scripts/issue_triage.py:43,60,170,190,207`,
  `SK/scripts/upkeep.py:285` (bytes), `:594` (`urlretrieve`), `:607` (`tarfile.extractall`)
- Modify: `SK/scripts/autosound_ai.py:128-154` (T-41, the key guard), `:280-300` (T-50, the clipboard),
  `:3446-3513` (T-50, `--help`)
- Modify: `SK/scripts/issue_triage.py:50-69, 181-223` (T-50)
- Modify: `RT/deployment.py:144-184` (T-42), and the same guard in `RT/gates/side_effect.py:296-308`
  (`method_version`) and `RT/resonalyze_engine.py:134,139,312` (`pin`, `_checkout_tag`)
- Modify: `RT/rew_tool.py:22-24` and its users (`:1849-1850`, `:1855`, `:1920`, `:2034`), `RT/target_curves.py:112-135` (F8)
- Create: `scripts/subprocess-check.py` (`--selftest`; in-tree: no production `subprocess.run`/`Popen` under `SK/`
  without a `timeout=`, or a `communicate(timeout=…)` for `Popen`, but a named allow-list: the interactive editor in
  `issue_triage.py`); `scripts/run-selftests.sh` (two lines), `RT/capabilities.py` (`NOT_ON_BOARD`)

**Interfaces:**
- Keeps: `side_effect._subprocess_runner` — its NAME and its shape `runner(argv) -> (returncode, stdout, stderr)`:
  it is the frozen default of contract 1's `upload_issue_asset(..., runner=_subprocess_runner)`, and
  `scripts/contract-guard.py` compares the default's text. Only its body changes (a timeout; `(124, "", "no answer in
  N s")` on one, as `upkeep.run` answers).
- Produces: the timeouts — `git` reads 10 s; `gh` 60 s (an asset upload 300 s); a fresh interpreter (`path_check`) 120 s;
  `git submodule update` 300 s; `dotnet build` 900 s; the engine run 1,800 s; `xattr` 10 s; the clipboard 10 s.

PLAN-AUDIT names one `run()` for every subprocess, modelled on `upkeep.py:66`; the calls do not share a shape (bytes in
`make_patch`, stdin in the keychain and the reviewer CLI, `Popen` with `communicate` in the clipboard, an interactive
editor), so each call gets its timeout where it is and a tree check holds the rule.

- [ ] **Step 1: Write the failing tests**
  - `subprocess-check.py --selftest` (a fixture tree with a call without a timeout — red; with one — green); in-tree
    run red today (21 calls).
  - `autosound_ai.py` selftest: the key guard in a repository git refuses to read (`GIT_TEST_ASSUME_DIFFERENT_OWNER=1`,
    rc 128 with "dubious ownership" — reproduced by the code map) with a project `.critic-env` carrying a key → exit
    2 naming git's line (red today: the guard passes, `:143-144`); outside a repository → passes; `git` missing →
    passes, as today. The clipboard with a fake `pbcopy`/`xclip` on `PATH` that exits 1 → `False` and a stderr line
    (red today: `True`). `autosound_ai.py --help` → the usage on stdout, exit 0 (today: "unknown task", exit 1).
  - `issue_triage.py` selftest: a fake `gh` whose `issue list` exits 1 → `main` exits 1 with gh's line and never
    prints "nothing new"; a failing `add_comment_to_issue` is reported.
  - `deployment.py` selftest: a plugin copy inside a home folder that is a git repository → `describe()` takes the
    registry's sha and says `plugin`, never the home's HEAD (reproduced by the code map, red today); the same for
    `side_effect.method_version` and the engine's `pin`.
  - `rew_tool.py` selftest: `analyze-batch` with no `--curves-dir` and no `rew_analitic/target-curves/` in the project
    → one line naming what to pass, and no author's folder anywhere (`grep -n "EMMA_2026" RT/rew_tool.py` empty).
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Build**
  1. Timeouts as above; each timeout answers in its caller's own terms (a returncode where the caller reads one, the
     caller's own message where it raises).
  2. T-41: `rev-parse --is-inside-work-tree` with `text=True` and `LC_ALL=C` in its environment; rc 128 whose stderr
     says `not a git repository` → not a repository (pass); any other failure, a timeout or an `OSError` → exit 2:
     "git could not say whether <file> would be committed (<git's line>) — move the key to the machine file
     (`autosound_ai.py key move …`) or fix git, then run again".
  3. T-50: the clipboard reads each program's return code and answers `False` with its stderr; `issue_triage.py`
     exits 1 on a failed `gh` with its line, reports a failed comment or label, and catches a failing editor with one
     line; `autosound_ai.py --help`/`-h` prints the usage (all tasks: `critic|advisor|ask|doctor|key|selftest`) and
     exits 0.
  4. T-42: `describe()` trusts `rev-parse HEAD`, `describe` and `symbolic-ref` only when `git rev-parse
     --show-toplevel` is the copy's root (`os.path.samefile`, as `provenance._answer_at`, `provenance.py:97-133`, does);
     otherwise the registry's sha for a plugin copy, or none. The same guard in `method_version` and the engine's `pin`
     and `_checkout_tag`.
  5. `upkeep.py`: `make_patch`'s bytes call gets `timeout=120` and maps a timeout to its refusal; `:594` downloads with
     `urlopen(..., timeout=60)`; `:607` extracts with `filter="data"` where `tarfile` takes it (3.12+) and, on 3.9,
     refuses a member whose path is absolute, climbs out with `..`, or is a link out of the folder, before extracting.
  6. F8: no default folder in the code: `--curves-dir` defaults to `<project>/rew_analitic/target-curves` when
     `--project`/`$AUTOSOUND_PROJECT_DIR` names a project that has it; otherwise the run says once "targets: none —
     pass --curves-dir <folder> (the intake writes them to rew_analitic/target-curves/<name>/)" and goes on without
     targets.
- [ ] **Step 4: Run — expect PASS**: the selftests of each module touched; `python3 scripts/subprocess-check.py`;
  `python3 scripts/contract-guard.py`.
- [ ] **Step 5: Commit**

```bash
git commit -m "#146: every subprocess with a timeout; the key guard, the clipboard and issue_triage say their failures; HEAD only of the copy's own repository"
```

---

## Task 17: Refusals and reads that still say the wrong thing (#147; W-8's review pool, S-101)

**Files:**
- Modify: `RT/state/process.py:1601-1603` (item 1), `RT/state/apply.py:499-501` and its test `:663` (item 2),
  `RT/predict.py:87` (`PredictError` gains `is_refusal = True`), `RT/eq_propose.py:953-962`, `RT/flaw_map.py:590-615`,
  `RT/level_offsets.py:376`, `RT/xover_candidates.py:410-436` (item 3), `RT/state/state.py:503-534`,
  `RT/project.py:829-840`, `RT/state/process.py:671-674` (item 4), `RT/rew_tool.py:1916-1925, 1986-2003`,
  `RT/intake.py:1448-1450` and `RT/intake_form.py:141-147` (item 5), `RT/state/state.py:264-271`,
  `RT/state/process.py:757-772`, `RT/car_profile.py:133-160, 201-207`, `RT/project_seed.py:161-171`,
  `RT/predict.py:2263-2271` (item 6), `RT/naming.py:282-288` (item 7), `FAQ.md:131` and `FAQ.uk.md`, `FAQ.de.md`,
  `FAQ.pl.md` `:131` (item 8; the Advisor translates), `CHANGELOG.md`

Each item: its test first (in its module's `_check_*` loop), red, then the fix, then green. What each must do:

1. `capture-start final --plan` → "--plan builds titles from a SERIES number (`capture-start 55 --plan`); `final` is
   the closing round's label — start it with its titles (`capture-start final "<title>" …`, phase_3_control.md:35)";
   a ledger version keeps today's sentence (the test at `:5124` holds it).
2. apply's "APPLY THIS" rows and `proposals/<v>.json` take the PROFILE's processing rate
   (`state.processing_rate(project_dir)`, the Arbiter's ruling of 2026-08-25 in its docstring) when a project is
   given, the snapshot's otherwise — and say which, as `PresetHistory.render` does; an unreadable profile leaves the
   samples empty and says so. Test: snapshot 96000 Hz, profile 48000 Hz, `ta_ms 5.45` → `5.45 ms (262 smp)` (the code
   map reproduced 523 today).
3. `PredictError` carries `is_refusal = True`; `eq_propose.main`, `flaw_map._main`, `level_offsets._main` and
   `xover_candidates._main` print `error: <exc>` and exit 1 for it (matched by the attribute, as `predict.main` does by
   class today), never a traceback. Tests as `predict.py:2886-2915` `_check_predict_refusals_are_one_line`.
4. A ledger version, a `project.json` or a changelog cut inside a character is said as cut — "is cut off inside a
   character: a write was cut off; restore it from git (`<restore_line>`)" — through
   `project_io.cut_inside_a_character`; a file that is not UTF-8 keeps the `repair-encoding` sentence. The tests that
   name today's text (`state.py:3729-3731`, `contract.py:3361,3376`) split into the two cases.
5. `rew_tool.py analyze-batch` and `analyze-joints` read the glossary strictly (`for_project(..., strict=True)`): an
   unreadable one is `error: <file> <reason> -- <repair>`, exit 1 (`analyze-batch`'s `except` stops calling every
   failure a REW one: it reads `is_unreadable` first); `intake._answered` tells an unreadable glossary from an
   unanswered one, and the form shows that field as unreadable with the repair. The lenient
   `Glossary.for_project(project_dir)` stays as it is: it is TCC's read in contract 1.
6. The six readers open `project.json` with `encoding="utf-8-sig"`; one test per reader: the same answer with and
   without a BOM (the code map reproduced the difference for five).
7. The lenient `for_project` over a `project.json` that is not an object (an array, a string, a number) is "no
   glossary" — the same as unreadable — never an `AttributeError`.
8. FAQ `:131`: "The method's EQ only cuts — at most 6 dB per band — and leaves a dip alone: a dip that would need a
   boost is almost certainly a cancellation." uk/de/pl through the Advisor.

- [ ] **Steps:** for each item, the failing test → run red → fix → run green (`python3 <module> <its argv>`); then
  `python3 scripts/docs-check.py` and `python3 scripts/i18n-check.py` for item 8.
- [ ] **Commit** — one per item or per pair:

```bash
git commit -m "#147: <item>"
```

---

## Task 18: Checks that can fail, round 2 (#148)

**Files:**
- Create: `scripts/selftest-reach-check.py` (`--selftest`; in-tree) — `scripts/run-selftests.sh`,
  `RT/capabilities.py` (`NOT_ON_BOARD`)
- Modify: `scripts/docs-check.py` — `step-ids` (`_step_named`, `:700-714`)
- Modify: `scripts/run-selftests.sh` — each module's selftest under its own empty `TMPDIR`, which must be empty after it
- Modify: the 15 `_selftest` functions that leave folders (code map §3.17: `process.py` 17, `project.py` 16,
  `contract.py` 6, `state.py` 5, `dsp_profile.py` 3, `apply.py` 3, `car_profile.py` 2, `resonalyze_engine.py` 2,
  `migrate.py` 2, `side_effect.py` 1 + 1, `eq_propose.py` 1, `intake_form.py` 1, `rew_tool.py` 1, `autosound_ai.py` 1)
- Modify: `.github/workflows/checks.yml` (a Python 3.11 step: `rew_api.py`'s and `process.py`'s selftests)

1. **No `_check_*` defined and never called.** A module-level `def _check_*()` with no parameters that nothing in its
   module references is an orphan (W-8 had two, `001b639`). Production helpers with that prefix take parameters or
   are referenced (`rew_api._check_address`, `resonalyze_vc`'s ten), so they pass. Today: none (the code map). The
   check's selftest: an orphan in a fixture → red, the same function in the loop → green.
2. **`step-ids` lands a pointer by any word of the step's name**, not only its first (`:705`): `1.4 EQ` lands on
   "coarse EQ"; a word that belongs to ANOTHER step's name still fails and names that step. Fixtures for both.
3. **Temp folders.** The runner gives each selftest a fresh `TMPDIR` (`mktemp -d`) and fails it when something is left
   there, naming the count. The 15 functions clean what they make: each sets `tempfile.tempdir` (and `TMPDIR` for the
   children it spawns) to one folder of its own at its start and removes it in a `finally`, restoring both.
4. **The `Trap` tests on 3.11.** `uv python install 3.11` (the code map: none on this Mac; `cpython-3.11.15` is
   downloadable); run `RT/rew_api.py --selftest` and `RT/state/process.py selftest` with it, record the result in the
   commit; a CI step in the `selftests` job runs the same two on `actions/setup-python` 3.11. A failure on 3.11 is a
   finding for this task, fixed here.

- [ ] **Steps:** each item test-first as above; `scripts/run-selftests.sh` runs once at the end of the task (it is the
  runner that changed), not while files are being edited.
- [ ] **Commit** — one per item.

### Group review — silent failures, round 2 (Tasks 16–18)

`pr-review-toolkit:silent-failure-hunter` and `pr-review-toolkit:pr-test-analyzer` (both **opus**) on the group's
diff, one fix round; `scripts/run-selftests.sh | tail -1`.

---

## Task 19: Close the wave

- [ ] **Step 1:** `scripts/run-selftests.sh | tail -1` → `all N checks passed`.
- [ ] **Step 2:** CHANGELOG `## [Unreleased]` reads as the release note (not a one-liner); `### Upgrading` complete:
  a user line, the plugin-users line (the catalogue moves when the audit's waves are done; v3.1.2's line said "to
  v3.1.2", which will not happen), and the TCC lines of each task.
- [ ] **Step 3:** push `wave-2026-10-08`; one PR to `main` with the wave's description; the full CI on it (the
  Windows job runs `write_lock.py`'s and `project_io.py`'s selftests and the installers' check; the new
  `installers-ubuntu` job; the 3.11 step).
- [ ] **Step 4: The Arbiter on the Windows VM** (~20–30 min): two writers at once on a project (the lock answers 75 and
  then lets the second in); `install.cmd` on a fresh folder and again on the same one — the exit code each time, and
  the receipt (`%LOCALAPPDATA%\autosound\install-receipt.json`). The commands are one line each (PowerShell takes no
  multi-line paste).
- [ ] **Step 5:** merge `--ff-only`, push `main`.
- [ ] **Step 6: the candidate** — `scripts/tag-check.sh --candidate v3.1.3`, then the signed tag `beta-v3.1.3-rc1` on
  `main`'s HEAD. A bus ticket to `tcc`: run your suite with `AUTOSOUND_SKILL_DIR` at `beta-v3.1.3-rc1`; what changes
  for TCC: `rew_tool/write_lock.py` with `PROTOCOL = 1` (your `locks_itself` reads True: the race harness's expected
  failure flips), exit 75 from every writer CLI, `AUTOSOUND_LOCK_TIMEOUT_S` per call, the close order (state first),
  a missing process folder refused unless it is a project's `process`, `Project.save` counting from the disk and
  `Project.update`, `intake.py set-car`'s 75, the reviewer prompt's header and LEDGER HEAD block and the door's own
  reviewer record (your N5 checks: opener, system prompt, `reviewer.configured`, the MCP tool list against SKILL.md's
  tool map), `.autosound/` in projects.
- [ ] **Step 7: the release, on the Arbiter's word after TCC's answer** — the bookkeeping commit (`## [v3.1.3]`,
  `plugin.json` 3.1.3, `INSTALLER_VERSION` and `$InstallerVersion` 3.1.3, `install.cmd`'s PS1URL, the front-page
  install lines; `docs/TODO.md` S-102 → `done` in that same commit — the preflight's `pool-closed`),
  `scripts/tag-check.sh v3.1.3`, the signed tag, `Latest` set by the skill (`gh release edit v3.1.3
  --prerelease=false --latest` once the tag's run has published it), #141–#148 and the milestone closed with `git tag
  --contains <commit>`. The catalog stays on v3.1.1 until the audit's waves are done (the Arbiter, 2026-10-08): no
  ticket to the release role.
