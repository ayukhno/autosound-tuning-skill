"""Machine-readable process state — SCR-004.

Where the tuning method *is* at any moment: which phase, which plan steps, what the reviewer last
said. Until now that lived only as prose — the `tuning-changelog`'s ▶️ CONTINUE block and
`audit-trail.md` — which a human reads fine and a front-end cannot.

Same split as the ledger (`state.py`), for the same reason: **history is append-only, the current
view is derived and rewritable.**

    process/journal.jsonl      append-only events; the source of truth for how we got here
    process/process-state.json the current slice, rewritten after every transition

Two rules are enforced in code rather than left to discipline, because both failure modes are
silent and expensive:

* **Steps are never deleted.** Superseding one marks it skipped and leaves it visible, so the
  attempt history stays legible instead of a plan that quietly rewrites itself.
* **`step_done` requires evidence that resolves** (SCR-035) — a REW measurement name in the
  grammar, a ledger version that exists, or a project file that exists. Prose may accompany those;
  it may not be the whole of it. A step marked done with nothing to point at is exactly the drift
  that resume is supposed to catch: on the next session the reconciler compares the plan against
  disk, and a done step whose measurement never existed is a flag, not a fact.

  Requiring *something* was not enough. Watched end to end: a cheap model closed phases −1 to 3 and
  reported a finished tune -- crossovers per driver, delays to 0.1 ms, a listening verdict -- with
  `dsp_profile.json` alone on disk, no ledger, no measurement, the Critic never called. Every step
  passed, because "baseline measurements analysed" is a non-empty evidence list. Prose is free; a
  name that has to parse and a path that has to exist are not.

`tuning-changelog` and `audit-trail.md` become generated views over the journal, the same move
`state.py` made for `dsp-state-current`.

stdlib only, py3.9+.
"""
from __future__ import annotations

import contextlib
import functools
import json
import math
import os
import re
import sys
import traceback
import urllib.error
from datetime import datetime, timezone


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def _project_io():
    """`rew_tool/project_io.py`: how this module writes the files it owns (skill #135)."""
    return _siblings().load("project_io.py")


def _write_lock():
    """`rew_tool/write_lock.py`: one writer at a time in a project (skill #141)."""
    return _siblings().load("write_lock.py")


def _hold(project_dir):
    """The project's writer lock for a `with` (#141): `write_lock.hold`, waiting `AUTOSOUND_LOCK_TIMEOUT_S` for it."""
    return _write_lock().hold(project_dir)


# One number across every machine file (see `project.py`'s own note) -- this file's own shape did
# not change in the 3.0 break, but "which format is this project in?" has to have one answer.
SCHEMA_VERSION = 3

# The method's fixed skeleton (`references/core/process-phases.md`). Phases are the skill's, not
# the project's: a project never edits this list, only the status of each entry and which one is
# active. Keys are strings because they land in JSON objects, where "-1" is a key, not a number.
PHASES = ("-1", "0", "1", "2", "3", "4", "5")
PHASE_TITLES = {
    "-1": "Project intake & checklist",
    "0": "Baseline & target selection",
    "1": "Crossovers, levels & delays",
    "2": "EQ & acoustic alignment",
    "3": "Technical verdict & lock",
    "4": "Targeted listening → feedback → close",
    "5": "Variations (cyclical)",
}

PHASE_TODO, PHASE_CURRENT, PHASE_DONE = "todo", "cur", "done"

STEP_TODO = "todo"
STEP_IN_PROGRESS = "in_progress"
STEP_DONE = "done"
STEP_SKIPPED = "skipped"
STEP_BLOCKED = "blocked"
STEP_STATUSES = (STEP_TODO, STEP_IN_PROGRESS, STEP_DONE, STEP_SKIPPED, STEP_BLOCKED)

# A step instantiated from the phase template vs. one inserted because this car needed it.
SOURCE_SKILL, SOURCE_PROJECT = "skill", "project"

# Journal event types (SCR-004). Adding one is cheap; renaming one breaks every reader.
EV_PHASE_ENTERED = "phase_entered"
EV_STEP_ADDED = "step_added"
EV_ATTEMPT_STARTED = "attempt_started"
EV_STEP_SKIPPED = "step_skipped"
EV_STEP_DONE = "step_done"
EV_STEP_BLOCKED = "step_blocked"
EV_CRITIC_CALLED = "critic_called"
EV_CONFIG_CHANGE = "config_change"
# A capture round: what was asked for, what came back, what was deliberately not taken (SCR-034).
EV_CAPTURE_ISSUED = "capture_task_issued"
EV_CAPTURE_RECONCILED = "capture_reconciled"   # skill #77: the round read against REW's list
EV_CAPTURE_TAKEN = "capture_taken"
#: A capture round was declared RAW -- swept with protective filters that are not part of the tune
#: (`rew_tool/protective.py`). Journalled rather than only stored, because it changes how every
#: phase decision made from those measurements is read, and a round whose classification changed
#: silently is a round nobody can re-litigate.
EV_CAPTURE_PROTECTIVE = "capture_protective"
#: The HARDWARE CONTROLS as they stood for a capture round -- the remote knobs, the switches: a
#: fact ABOUT THE SERIES, not about the tune, and one nothing recorded until 2026-09-08. An hour
#: went on "why is +4 dB on the virtual sub not in the measurement": it was not in the measurement
#: because the sub's knob stood at −4, and no reader could have known (hub RES-007).
EV_CAPTURE_KNOBS = "capture_knobs"
EV_CAPTURE_SKIPPED = "capture_skipped"
#: An AMPLIFIER gain the user turned (the Arbiter, 2026-09-23). Levels always live in the DSP; an amp gain moves
#: only when the DSP's plus runs out, it is his decision, and he tells the session. Per channel, in dB, at its
#: place in the journal: a level compared across it is corrected by it instead of being called calibration.
EV_AMP_GAIN = "amp_gain_changed"
#: S-039: a capture recorded under a title that turned out to be wrong. The row STAYS, dimmed and
#: naming what it was corrected to -- the same move the plan's steps have had since SCR-004, and
#: for the same reason: a round that quietly loses a row is a round nobody can audit.
EV_CAPTURE_SUPERSEDED = "capture_superseded"
EV_CAPTURE_CLOSED = "capture_round_closed"
# What the arithmetic said about the curves themselves (SCR-040). A separate event from
# `capture_taken`: one says a measurement came back, the other says it is usable.
EV_CAPTURE_VERIFIED = "capture_verified"
#: A listening verdict (Phase 4, 2026-08-25): the Arbiter's own words plus the pairs they ticked
#: (track x characteristic x ok/bad), stamped with the ledger version they were listening to.
#: One writer -- this journal; `banked_ear_verdicts` in a ledger snapshot is derived from it at the
#: lock and only ever ADDS. The journal is the protocol one looks back into: a filter by track or
#: characteristic across versions IS the A/B history, no other structure.
EV_LISTENING_VERDICT = "listening_verdict"
# Who sat down to work, on what model, and when. Written by the front-end when it attaches a
# session -- the journal otherwise starts at whatever the model happened to record first, so
# "when did this session begin, and did it record anything at all" had no answer.
EV_SESSION_STARTED = "session_started"
# A session that stopped in order left NO trace at all: `session-close` reported what was open and
# exited, so the journal could not tell "we stopped here, cleanly" from "the process was killed
# mid-step". Written only on a clean close -- with work still open there is nothing to record but
# the report itself (release review 2026-09-09). `session-close --check` asks the same question and
# writes nothing (S-084).
EV_SESSION_CLOSED = "session_closed"
# A close taken back, with its reason (S-084, hub #227). A session reconciling state ran
# `session-close` to look and it wrote the close. The close STAYS -- the journal is append-only --
# and this follows it: wherever the last session event is read, a reopening after a close means
# the session is open again (`Process.session_closed`).
EV_SESSION_REOPENED = "session_reopened"
#: The events that say whether a session is open, read together by `Process.last_session_event`.
SESSION_EVENTS = (EV_SESSION_STARTED, EV_SESSION_CLOSED, EV_SESSION_REOPENED)
# What the Arbiter ruled, as itself. Their half of the conversation was in no machine file at all:
# the only surviving trace of an answer was a hand-typed evidence string, and a constraint the user
# set was invisible to the next session unless it happened to be re-read out of prose (SCR-030).
EV_USER_DECISION = "user_decision"
# Which checkout of the method wrote what follows (autosound-hub HUB-002). The header of the
# journal, and of every later run that came from a different commit -- see `Process._stamp`.
EV_WRITTEN_BY = "written_by"



# A label a caller typed at the head of a step's name: a section of a phase document (`2d:`, `2c —`) or another
# number (`2.8`). skill #72: the session cited `2.8` while the panel showed `2d: фінальний EQ`, one step under two
# labels, so the id now leads every name and any other label there is dropped.
_LEADING_LABEL_RE = re.compile(r"^\s*(?:\d+\.\d+(?:\.\d+)*[a-z]?|\d+[a-z])\s*(?:[:\u2014\u2013-]\s*|\s+)")


def _named_by_id(step_id, name):
    """`<id> <name>`: the one label a step goes by, in the text and on every screen that shows the plan (skill #72)."""
    name = str(name or "").strip()
    head = f"{step_id} "
    if name.startswith(head):
        return name
    return head + _LEADING_LABEL_RE.sub("", name, count=1)


class ProcessError(ValueError):
    """A transition the process model refuses — e.g. a done step with no evidence."""


# The command line's exit table (#134, audit T-23). 0, 1 and 2 keep their meaning: done (or yes), refused (or no, the
# reason on stderr), usage. 69, 70 and 75 are sysexits' -- `EX_UNAVAILABLE`, `EX_SOFTWARE`, `EX_TEMPFAIL` -- and no
# tool of the method returned them before (PLAN-AUDIT §8 M1): REW did not answer, and nothing was written; an
# unexpected error, a bug, with its traceback on stderr above the line that names it -- where it exited 1 like a
# refusal, or escaped as a traceback; the project busy: another writer held the project's lock past the wait
# (`write_lock.py`, #141), nothing written, safe to retry -- but by `capture-close` stopped past its first hold, whose
# own `busy:` line says what had landed by then (R9, `_close_stopped`).
EXIT_OK = 0
EXIT_NO = 1
EXIT_USAGE = 2
EXIT_REW_UNAVAILABLE = 69
EXIT_UNEXPECTED = 70
EXIT_BUSY = 75


class UsageError(ProcessError):
    """A command line the verb does not take: a flag it does not know, a value on a flag that takes none (#134,
    N19). Exit 2. Its words never contain `usage: process.py`, which TCC reads as "the method is too old"."""
    exit_code = EXIT_USAGE


class RewUnavailableError(ProcessError):
    """REW did not answer, and nothing was recorded (#134): exit 69. Carries `rew_state` as `rew_api`'s own
    `RewUnavailable` does, so a caller matching the attribute reads both the same."""
    exit_code = EXIT_REW_UNAVAILABLE
    rew_state = "unavailable"


class _StateWithoutItsEvent(ProcessError):
    """The state is written in this run, and its journal line is not (#134, F M-7): the refusal says what landed and
    the line to append. `state_written` on the class, so a caller that goes on past a failure -- `capture-close`'s
    checks -- tells it from one that wrote nothing, and refuses with it (batch 3's re-review O3): swallowed, it was
    cut to 160 characters, the line to append lost, and the round closed."""
    state_written = True


class _RoundMoved(ProcessError):
    """The capture round a writer read was closed or replaced by another writer before its hold (#141): refused,
    nothing written by it. `round_moved` on the class, so that `capture-close` -- whose reconcile, checks and close each
    take the lock for themselves -- tells it from a refusal it may go on past, and stops (Task 2's review): it was read
    as "checks not run", and the close went on over the round that replaced it. On the instance, the round read
    (`read`) and the one open now (`now`, None when none is), for the line that says what landed before it."""
    round_moved = True

    def __init__(self, message, read, now=None):
        super().__init__(message)
        self.read, self.now = read, now


# Phase 0 selects the target curve and every later phase is measured against it, so leaving 0
# without one means the whole EQ stage has no reference. Watched happening: the Arbiter named a
# curve out loud, the model repeated it back and wrote it into a free-text profile field, and
# `targets` was still `{}` afterwards -- the choice lived in the transcript, and a transcript does
# not survive a `/clear`. Same shape as `finish_step` refusing an empty evidence list: the refusal
# is the record's, not the model's.
_TARGET_REQUIRED_FROM = 1


def _require_target(phase, previous, state):
    """Refuse to move past phase 0 while no target curve has been recorded."""
    if state.get("targets"):
        return
    try:
        going, came_from = int(phase), int(previous) if previous is not None else -99
    except (TypeError, ValueError):
        return
    if going < _TARGET_REQUIRED_FROM or came_from >= going:
        return  # not a forward move out of baseline; re-entry and going back are always allowed
    raise ProcessError(
        f"phase {phase} needs a target curve: nothing has been recorded with `target`. "
        "Phase 0 chooses it and every later phase is measured against it, so a curve that exists "
        "only in the conversation is lost on the next session. "
        # `target`, not `set-target`. Both this sentence and phase_0_baseline.md named a
        # subcommand that does not exist, so following the gate as written produced a usage error
        # — and a refusal that instructs an invalid command teaches its reader that refusals are
        # noise, which is the opposite of what a gate is for (2026-08-12).
        "Record it: `python3 rew_tool/state/process.py <project>/process target <preset> <curve>`"
        " (e.g. `target FULL EPY`).")


# Phase 0 §3.5 PRODUCES the acoustic flaw map, and phase 2 is supposed to EQ against it — what may
# be cut, what must be left, what is not an EQ problem at all. SCR-015 built the writer
# (`project.py flaw`, closed `action` list, refuses a dip recorded as notchable) and the consumer
# panel. Nothing forced the write, and the predictable happened on a real project (2026-08-11): the
# step "Acoustic flaw map: distortion floor + raw pair coherence" was closed `done`, `acoustics`
# was absent from `project.json`, and the findings — "w-L 160 Hz and w-R 250-315 Hz are acoustic
# nulls, settled by absolute harmonic SPL" — sat in a journal decision as prose. Analysis nobody
# can compute against is analysis that will be redone or, worse, guessed at.
_FLAW_MAP_REQUIRED_FROM = 1


def _flaw_map_entries(project_dir):
    """`acoustics.flaws[]` from `project.json`, or None when there is no `project.json` -- "no opinion": a missing
    file is the intake check's to name.

    Read as plain JSON rather than through `project.py`: this module is imported BY consumers that
    already load these files their own way. A `project.json` that is there and cannot be read raises
    `Unreadable`, naming it and its repair (#136, audit T-10): read as "no opinion", it let the phase in with no flaw
    map to equalise against, and one holding an array stopped the gate with a traceback.
    """
    io_ = _project_io()
    path = os.path.join(project_dir, "project.json")
    data = io_.read_json(path, None, repair=io_.restore_line(path), repair_encoding=io_.reencode_line(project_dir))
    if data is None:
        return None
    profile = data.get("project", data)
    return list(((profile.get("acoustics") or {}).get("flaws")) or [])


#: `flaw_map.classify` writes this on a peak row it could not check, and this gate reads it back.
#: Imported by VALUE rather than by module, as `_flaw_map_entries` reads `project.json` itself
#: rather than through `project.py`: a gate that depends on an import cannot run where the import
#: fails -- and a gate that cannot run refuses the phase (#136). The two copies are held together
#: by `flaw_map`'s own selftest.
_ASSUMED_NOTE = "no positions measured -- staying is ASSUMED, not shown"
#: `p1`…`p9` as the grammar writes it -- `m-L p3_49 (sw)`. NOT `\bp[1-9]\b`: `_` is a word
#: character, so that pattern never matches a real title, and the gate would have passed every
#: round ever opened. Caught by the selftest, not by reading.
_POSITION_IN_TITLE = re.compile(r"(?<![\w-])p[1-9](?=[_\s])")


def _positions_asked(project_dir):
    """Has the request for the positions been MADE — the round opened, or the answer recorded?

    Two records count, and both are ones that already exist (S-047):

    * a capture round was opened asking for a position title (`<ch> p3_49 (sw)`) — the offer taken;
    * a ruling was recorded whose words name the ellipsoid or the positions — the offer declined,
      which is an answer and closes the question as firmly as taking it.

    Anything else is the question never having been put, which is exactly the state this gate is
    about: 43 rows written on an assumption while the set that would settle them sat on the disk.
    """
    # Strictly (#134, F I-2, H I-2): a torn line -- cut inside a character too -- is skipped, not fatal (R23), but a
    # journal that cannot be opened, or holds a line in another code page, refuses the gate naming itself: read as
    # empty, the gate refused for a question it never saw asked, or let it through without the line that asked it.
    for event in Process(os.path.join(project_dir, "process"))._events(kinds=(EV_CAPTURE_ISSUED, EV_USER_DECISION)):
        kind = event.get("type")
        if kind == EV_CAPTURE_ISSUED:
            if any(_POSITION_IN_TITLE.search(str(t)) for t in (event.get("expected") or [])):
                return True
        elif kind == EV_USER_DECISION:
            words = f"{event.get('question', '')} {event.get('answer', '')}".lower()
            if "ellipsoid" in words or "p1..p9" in words or "position" in words:
                return True
    return False


#: WHO wrote a protective record. `user` is a person's word; `front_end` is an app writing what it
#: captured; `default` is a bulk write that decided nothing per channel. The distinction exists
#: because ten channels marked OFF within one second, rears included that were not in the series at
#: all, is a default being read downstream as ten answers (S-036, skill `#48`).
PROTECTIVE_SOURCES = ("user", "front_end", "default")


def _clean_origin(origin):
    """`{"project": ..., "series": ...}` for measurements taken in ANOTHER project, or None.

    Both halves are required when either is given: "from somewhere else" with no name is the same
    unanswered question as no origin at all, and the series it was THERE is what a later reader
    needs to go back and look.
    """
    if not origin:
        return None
    if isinstance(origin, str):
        name, _, series = origin.partition(":")
        origin = {"project": name, "series": series}
    if not isinstance(origin, dict):
        raise ProcessError(f"origin must be <project>:<their _N> or {{project, series}}, got {origin!r}")
    project = str(origin.get("project") or "").strip()
    series = str(origin.get("series") or "").strip().lstrip("_")
    if not project or not series:
        raise ProcessError(
            f"an origin needs BOTH the project these measurements were taken in and the series "
            f"they were `_N` of there, got {origin!r}. 'From somewhere else' with no name is the "
            "same unanswered question as no origin at all")
    return {"project": project, "series": series}


def _protective_source(source):
    source = str(source or "").strip().lower()
    if source not in PROTECTIVE_SOURCES:
        raise ProcessError(
            f"protective source {source!r} is not one of {', '.join(PROTECTIVE_SOURCES)}. "
            "It says WHO answered: a person, the front-end for a channel it captured, or a bulk "
            "default that decided nothing — and a default is read as a question, not an answer")
    return source


def _refuse_channel_outside_round(round_, channel):
    """A round cannot record protection for a channel it never captured (S-036).

    `set_protective` checked that a round was open and not that the channel was in it, so a bulk
    import wrote the rears — which were not in the series — alongside the channels that were. A
    round with no explicit `expected` asked for nothing in particular and is left alone.
    """
    expected = [str(t) for t in (round_.get("expected") or [])]
    if not expected:
        return
    if any(str(channel) == str(t).split("_")[0].split(" ")[0] or f"{channel}_" in str(t)
           or str(t).startswith(f"{channel} ") for t in expected):
        return
    # Only what the round took and still stands by: a superseded row is a typo's trace (N17).
    taken = [t for t in (round_.get("taken") or {}) if _is_taken(round_, t)]
    if channel in taken or any(str(t).startswith(f"{channel}_") or str(t).startswith(f"{channel} ") for t in taken):
        return
    raise ProcessError(
        f"round {round_.get('id')} never asked for {channel!r} and did not take it — it expected "
        + ", ".join(sorted({str(t).split("_")[0].split(" ")[0] for t in expected}))
        + ". A protective record for a channel outside the round is a fact about a pass that did "
          "not happen, and every reader downstream takes it as one. Record it on the round that "
          "captured that channel, or amend that round (`capture-protective --amend <cap_id> …`)")


def _require_flaw_map(phase, previous, project_dir):
    """Refuse to move past phase 0 while the flaw map is empty (SCR-044)."""
    try:
        going, came_from = int(phase), int(previous) if previous is not None else -99
    except (TypeError, ValueError):
        return
    if going < _FLAW_MAP_REQUIRED_FROM or came_from >= going:
        return  # re-entry and going back are always allowed, same rule as the target gate
    entries = _flaw_map_entries(project_dir)        # one that cannot be read raises, naming it (#136)
    if entries is None:
        return  # no project.json at all is the intake check's complaint, not this one
    if entries:
        # S-047: the map exists, and some of its rows stand on an assumption nobody tested. The
        # tool computed that and carried it nowhere; the phase does not close over it in silence.
        assumed = [e for e in entries if _ASSUMED_NOTE in str((e or {}).get("why") or "")]
        if assumed and not _positions_asked(project_dir):
            codes = sorted({c for e in assumed for c in ((e or {}).get("channels") or [])})
            raise ProcessError(
                f"phase {phase}: {len(assumed)} flaw row(s) on {len(codes)} channel(s) say a peak "
                f"STAYS because nobody moved the microphone — "
                + (", ".join(codes) if codes else "no channel named")
                + ". `flaw_map` writes that on every peak it could not check ('"
                + _ASSUMED_NOTE + "'), and phase 2 equalises against those rows. ASK for the "
                "measurement that settles them before the phase closes:\n"
                + "".join(f"    {c} p1..p9_<N> (sw)\n" for c in codes)
                + "    (`flaw_map.py --project <dir> --rew <N>` prints the exact "
                  "`capture-start` line, titles and all)\n"
                "Or record the Arbiter's answer if he decides against it — `decision \"the "
                "ellipsoid for <channels>\" \"<his words>\"` — because a decision is an answer "
                "and closes the question; an unasked question is not."
            )
        return
    raise ProcessError(
        f"phase {phase} needs the acoustic flaw map: `acoustics.flaws[]` in project.json is empty. "
        "Phase 0 measures what this cabin does to the sound and phase 2 equalises against it — "
        "which features may be cut, which must be left alone, which are not EQ problems at all. "
        "In the transcript that knowledge is lost on the next session; the panel that should show "
        "it renders nothing. "
        "Record each one: `project.py <dir> flaw <f_hz> <level_db> <kind> <action> "
        "[--q N|--bw-oct N] [--channels a,b] [--why ...] [--evidence ...]`. "
        "A feature you decided to leave alone is still an entry — `action=leave` is in the list "
        "precisely so that decision is recorded rather than implied by its absence."
    )


#: Leaving phase −1 means intake is done. `references/phases/phase_-1_intake.md` has said so from
#: the beginning — project.json, dsp_profile.json, the glossary, a first ledger snapshot, a clean
#: contract check — and nothing enforced it, so a brand-new folder walked to phase 1 with none of
#: them (measured 2026-08-12: `enter-phase -1`, `enter-phase 0`, `set-target`, `enter-phase 1`,
#: all OK, on an empty directory). The gate was a paragraph.
_INTAKE_REQUIRED_FROM = 0


def _require_intake(phase, previous, project_dir):
    """Refuse to leave phase −1 until the machine files intake is supposed to produce exist.

    Computed by the same code `contract.py check --gate` runs (`check_project`) — two
    implementations of "is intake finished" would eventually disagree, and the one nobody runs
    would be the one that says yes. Not yet the same ANSWER: this gate refuses on `missing` alone,
    and on a `project.json` or a standalone `glossary.json` that is there and cannot be read (the
    report's `unreadable`, #134, F M-5, batch 4's re-review N4: named first, with its repair -- the
    glossary inside the one, and the other itself, read as "not produced"), while `--gate`
    also wants nothing there invalid (`complete`), so a `dsp_profile.json` that is there and cannot
    be read, or that a newer method wrote, passes here and is NOT READY there. Gating on
    `complete`, with a parity test, is J3b (W-11).

    A check that cannot run refuses the phase (#136, audit T-10). It used to pass it -- "cannot check is not the same
    as failed", "a checker that raises must not become a wall" -- and so a gate that could not check let the phase
    in, on the damaged projects most of all: the files it trips on are the ones it exists to stop. A `contract.py`
    that cannot be loaded is the install's fault and is said so; a check that raises names what it raised; a file it
    found unreadable raises as itself, with its own repair.
    """
    try:
        going, came_from = int(phase), int(previous) if previous is not None else -99
    except (TypeError, ValueError):
        return
    if going < _INTAKE_REQUIRED_FROM or came_from >= going:
        return  # re-entry and going back are always allowed, same rule as every gate here
    try:
        contract = _siblings().load("contract.py")
    except Exception as exc:  # noqa: BLE001 -- any failure to load is the install's, and refuses the phase
        raise ProcessError(f"phase {phase} is not entered: the intake check could not be loaded "
                           f"({type(exc).__name__}: {exc}) -- the install is broken, not the project") from exc
    try:
        report = contract.check_project(project_dir, skip_rew=True)
    except Exception as exc:  # noqa: BLE001 -- refused, never passed (#136, audit T-10: a gate that cannot check let
        # the phase in): an unreadable file raises as itself, with its repair; anything else is named.
        if getattr(exc, "is_unreadable", False):
            raise
        raise ProcessError(f"phase {phase} is not entered: the intake check raised {type(exc).__name__}: {exc}") \
            from exc
    # A `project.json` that is there and cannot be read refuses as itself, with its repair (#134, F M-5): the glossary
    # it carries read as "not produced", and the person was sent to redo an intake that is done. So does a standalone
    # `glossary.json` (batch 4's re-review N4): read as no glossary, it let the phase in beside the one in project.json.
    for entry in report.get("unreadable") or []:
        raise ProcessError(f"phase {phase} is not entered: {entry['issue']}")
    missing = report.get("missing") or []
    if not missing:
        return
    raise ProcessError(
        f"phase {phase} cannot start: intake has not produced "
        + ", ".join(missing)
        + ". This is the phase −1 quality gate, and it is the whole reason a consumer front-end "
        "has something to render — a prose-only intake is not a complete one. Run "
        "`python3 rew_tool/contract.py check <project> --gate` to see it yourself; finish the "
        "intake flow in `references/phases/phase_-1_intake.md §0.5` rather than working around this."
    )


#: Why a sibling could not be loaded, by its name: the failure `_load_sibling` last met, dropped once it loads (#134,
#: H 12). A caller that refuses over the None says it (`_load_failure`): numpy missing, a syntax error in the sibling.
_LOAD_FAILURES = {}


def _load_sibling(name):
    """A `rew_tool/` module through `siblings` -- one object per file. None when it cannot be loaded: the
    callers here read that as "cannot tell", and say so at their call site, with the reason (`_load_failure`)."""
    try:
        module = _siblings().load(name)
    except Exception as exc:  # noqa: BLE001
        _LOAD_FAILURES[name] = exc
        return None
    _LOAD_FAILURES.pop(name, None)
    return module


def _load_failure(name):
    """` (<type>: <message>)`: why `_load_sibling` last failed to load `name`; "" when nothing is on record."""
    exc = _LOAD_FAILURES.get(name)
    return "" if exc is None else f" ({type(exc).__name__}: {exc})"


# Which profile facts a phase cannot honestly run without. The other half of "learning instead of
# softer gates" (ARCHITECTURE-NOTES §4): the phase -1 gate has always wanted a VALID profile rather
# than a complete one -- `open_questions` is deliberately not part of `contract.py`'s `ok`, so a DSP
# nobody knows everything about can start -- and the missing piece was that an open question was
# never raised again at the step that depends on it. It sat 🟡 in a report forever.
#
# Phase-scoped, not step-scoped, for the same reason `_CAPTURE_PLAN` is: a phase's needs are a
# property of the method and identical on every car, while a step's name is written per project.
# Group-scoped paths (`groups.N.x`) are matched by their last segment.
_PHASE_FACTS = {
    "1": ("dsp_processing_rate_hz", "delay", "crossover_filters"),
    "2": ("parametric_eq", "eq"),
}


def _load_dsp_profile_module():
    """`dsp_profile.py` from the same checkout, by path — same reason as `_load_naming`. None when it
    cannot be loaded: the capture check's rate note then says nothing. The phase gate loads it itself, and refuses
    when it cannot (`_require_profile_facts`)."""
    return _load_sibling("dsp_profile.py")


def _require_profile_facts(phase, previous, project_dir):
    """Refuse to enter a phase whose arithmetic needs a fact the profile has never recorded.

    The one that hurts is `sample_rate_hz`: phase 1 converts every delay into samples, and a rate
    nobody wrote down is a rate somebody assumes. Observed on a real project (2026-08-11) — a Helix
    profile with no rate, no slot counts and no EQ or crossover description at all, reporting
    nothing open because those keys were absent rather than null.

    A check that cannot run refuses, as the intake gate's does (#136, audit T-10): a `dsp_profile.json` that is there
    and cannot be read -- or that a newer method wrote -- raises `load_profile`'s `Unreadable`, naming it and its
    repair (read as "no profile", it let phase 1 in with no rate on record), and a `dsp_profile.py` that cannot be
    loaded is the install's fault. No profile at all is still the intake check's to name.
    """
    wanted = _PHASE_FACTS.get(str(phase))
    if not wanted:
        return
    try:
        going, came_from = int(phase), int(previous) if previous is not None else -99
    except (TypeError, ValueError):
        return
    if came_from >= going:
        return  # re-entry and going back are always allowed, same rule as the other two gates
    try:
        module = _siblings().load("dsp_profile.py")
    except Exception as exc:  # noqa: BLE001 -- any failure to load is the install's, and refuses the phase
        raise ProcessError(f"phase {phase} is not entered: the profile check could not be loaded "
                           f"({type(exc).__name__}: {exc}) -- the install is broken, not the project") from exc
    try:
        data = module.load_profile(os.path.join(project_dir, "dsp_profile.json"))
    except FileNotFoundError:
        return  # no profile at all is the intake check's complaint, not this gate's
    blocking = [path for path in module.missing_facts(data) if path.split(".")[-1] in wanted]
    if not blocking:
        return
    raise ProcessError(
        f"phase {phase} needs facts the DSP profile has never recorded: "
        + ", ".join(blocking)
        + ". These are not paperwork: phase 1 turns delays into samples with the DSP's processing "
        "rate (`dsp_processing_rate_hz`; the old name `sample_rate_hz` is still read), and "
        "phase 2 sizes its filters against what the EQ can actually do. A number nobody wrote down "
        "is a number the next session assumes. "
        "Ask the Arbiter and record each one: "
        "`dsp_profile.py set-field <project> <path> <value>` — then `finalize`. "
        "Everything still open is listed by `dsp_profile.py open-questions <project>/dsp_profile.json`."
    )


# --- evidence that resolves (SCR-035) ---------------------------------------------------------
#
# Three shapes count. Each is something a later session can go and check; a sentence is not.
_LEDGER_RE = re.compile(r"\bv_?(\d{1,4})\b", re.IGNORECASE)
# Loose on purpose: a path only counts once it is found on disk, so over-matching costs nothing
# and under-matching would reject a real file over its spelling.
_PATH_RE = re.compile(r"[\w./\\-]+\.(?:json|jsonl|md|mdat|txt|csv|yml|yaml|req|png|pdf)\b")


def _load_rew_tool_module(name):
    """A `rew_tool/<name>.py` module from the same checkout, by path (see `_load_naming`). None when
    it cannot be loaded -- the caller decides whether "cannot load" is fatal."""
    return _load_sibling(name + ".py")


_NAMING = []


def _load_naming():
    """`naming.py` from the same checkout, by path -- loaded once per process.

    Not `import naming`: that needs `rew_tool/` on `sys.path`, and the consumer front-end loads
    these modules by explicit path precisely to keep names like `state` off the global import path.
    Returns None when it cannot be loaded -- an unreadable grammar must not make evidence
    unrecordable, it just means one of the three shapes cannot be recognised here.

    Once, because `_title_version` asks it for every title of every round a lookup replays.
    """
    if not _NAMING:
        _NAMING.append(_load_naming_uncached())
    return _NAMING[0]


def _load_naming_uncached():
    """None when `naming.py` cannot be loaded: any failure here means "cannot tell", never "invalid"."""
    return _load_sibling("naming.py")


def _naming_unloaded():
    """`naming.py could not be loaded (<type>: <message>) -- a capture name cannot be recognised` when the grammar did
    not load, else "" (the final review's M2): what the evidence verdicts (`done`, `check`, `handoff`) say beside a
    capture name that resolves to nothing for want of a grammar, never only that the evidence resolves to nothing."""
    if _load_naming() is not None:
        return ""
    return f"naming.py could not be loaded{_load_failure('naming.py')} -- a capture name cannot be recognised"


def _state_root(project_dir):
    env = os.environ.get("AUTOSOUND_STATE_ROOT")
    return env if env else os.path.join(project_dir, "state")


_SERIES_RE = re.compile(r"_?(\d{1,4})$")


def version_kind(version):
    """Which of the TWO counters a round's `version` names — `"ledger"`, `"series"` or `None`.

    They are different counters and neither is derived from the other (`naming-and-structure.md`
    §1a/§5): a **series** `_N` numbers a set of measurements, a **ledger version** `v_NNN` is the
    DSP configuration they were taken under. `capture-start` takes either, and until TCC-022 the
    round recorded the string and left every later reader to guess from its spelling — which is
    also why nothing could check it.
    """
    text = str(version if version is not None else "").strip()
    if _LEDGER_RE.fullmatch(text):
        return "ledger"
    if _SERIES_RE.fullmatch(text):
        return "series"
    return None


def _changelog_read(project_dir):
    """`(path, text, why, mend)` for `tuning-changelog`: its text, or why it cannot be read -- `cannot be opened (...)`,
    `is not UTF-8` -- and what mends that, with the text None; `(None, None, None, None)` when there is no such file.
    The mend for a file that cannot be opened is its cause's (m2, `project_io.repair_for`): "close what holds it" where
    something can hold it, Windows -- closing an editor cannot mend a permission."""
    for name in ("tuning-changelog.md", "tuning-changelog"):
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    return path, fh.read(), None, None
            except UnicodeDecodeError:
                return path, None, "is not UTF-8", "save it as UTF-8 and run this again"
            except OSError as exc:
                return path, None, f"cannot be opened ({exc})", _project_io().repair_for(exc)
    return None, None, None, None


def _changelog_text(project_dir):
    """The text of `tuning-changelog`, or None when there is no such file or it cannot be read -- a warning's
    source; `handoff` asks `_changelog_read`, which says why."""
    return _changelog_read(project_dir)[1]


def _continue_block(project_dir):
    """Does `tuning-changelog` carry its ▶️ CONTINUE block? None when there is no such file.

    None means "no opinion", the same answer `_flaw_map_entries` gives for a project with no
    `project.json`: a project that keeps no prose changelog is not failing a check it never opted into.
    """
    text = _changelog_text(project_dir)
    return None if text is None else "CONTINUE" in text


#: A ledger version as the ledger spells it, `v_NNN`. Stricter than `_LEDGER_RE` on purpose: that one
#: also takes `v3`, and in a changelog's prose `v3.0.64` is the method's version far more often.
_CONTINUE_VERSION_RE = re.compile(r"\bv_(\d{1,4})\b")
_HEADING_RE = re.compile(r"^(#{1,6})\s")
_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def continue_block_heads(project_dir):
    """The ledger versions the ▶️ CONTINUE block names as HEAD, as `v_NNN`; [] when it names none (S-084).

    The block is the first line carrying `CONTINUE` and what follows it, up to the next heading of its
    level or above (any heading, when the block is not one) or a rule. A version counts when it follows
    the word `HEAD` on a line; a block that never writes `HEAD` but names exactly one version is read as
    naming that one. Anything else -- several versions and no `HEAD`, or none -- is no answer, and no
    answer warns of nothing: this is a cross-check on prose, and prose is written many ways.
    """
    text = _changelog_text(project_dir)
    lines = (text or "").splitlines()
    start = next((i for i, line in enumerate(lines) if "CONTINUE" in line), None)
    if start is None:
        return []
    heading = _HEADING_RE.match(lines[start])
    level = len(heading.group(1)) if heading else 6
    block = [lines[start]]
    for line in lines[start + 1:]:
        found = _HEADING_RE.match(line)
        if (found and len(found.group(1)) <= level) or _RULE_RE.match(line):
            break
        block.append(line)
    named = []
    for line in block:
        for word in re.finditer(r"\bHEAD\b", line):
            version = _CONTINUE_VERSION_RE.search(line, word.end())
            if version and f"v_{int(version.group(1)):03d}" not in named:
                named.append(f"v_{int(version.group(1)):03d}")
    if named:
        return named
    every = {int(n) for n in _CONTINUE_VERSION_RE.findall("\n".join(block))}
    return [f"v_{every.pop():03d}"] if len(every) == 1 else []


def _ledger_heads(project_dir):
    """`{slot: "v_NNN"}`: each slot's HEAD as `state.py` reads it, in either ledger layout.

    `state.py` rather than a second reader of HEAD files: there are two layouts (`HEAD` per preset,
    `slots.json` on the per-project line) and one module that knows both. {} when there is no ledger,
    or it will not load -- this feeds a warning, and a ledger that cannot be read is reported by the
    checks that own it (`handoff`, `contract.py check`).
    """
    root = _state_root(project_dir)
    state_mod = _load_sibling("state/state.py") if os.path.isdir(root) else None
    if state_mod is None:
        return {}
    try:
        heads = {slot: state_mod.PresetHistory(root, slot, project_dir=project_dir).head()
                 for slot in state_mod.Registry(root).list_presets()}
    except Exception:  # noqa: BLE001 -- any failure here means "cannot tell", never a mismatch
        return {}
    return {slot: head for slot, head in heads.items() if head}


def _route_line(project_dir):
    """" The route: …" when the project is a car that is already tuned (`goal.mode`, skill #105), else "".

    The route changes what the next session does in Phase 0 (block X) and at the desk (`run --current`), and
    the mode lives in `project.json`, which a resumed session may not open before it acts."""
    try:
        with open(os.path.join(project_dir, "project.json"), encoding="utf-8") as fh:
            mode = ((json.load(fh) or {}).get("goal") or {}).get("mode")
    except (OSError, ValueError):
        return ""
    if isinstance(mode, dict):
        mode = mode.get("value")
    if mode != "improve_existing":
        return ""
    return (" The route: a car that is already tuned (goal.mode improve_existing) — `virtual-first.md`, "
            "«Two ways in»: block X after the raw capture, `resonalyze_engine.py run --current` at the desk.")


def continue_head_drift(project_dir):
    """The ▶️ CONTINUE block names a HEAD the ledger is not at: `{named, heads, stale, warning}`, or None (S-084).

    Found on the Windows VM (hub #227): the block named `v_010` while the ledger stood at `v_013`, and
    the only check was that the block exists. A WARNING, never a refusal: the block is the
    human-readable cross-check and the ledger is what resume trusts, so a stale block is prose to bring
    up to the ledger, not a state that stops anything. None when the block names no version it can be
    read for, or there is no ledger to compare with -- both are "no opinion", as in `_continue_block`.
    """
    named = continue_block_heads(project_dir)
    heads = _ledger_heads(project_dir) if named else {}
    if not heads:
        return None
    stale = [v for v in named if v not in set(heads.values())]
    if not stale:
        return None
    at = (f"{next(iter(heads.values()))} ({next(iter(heads))})" if len(heads) == 1
          else ", ".join(f"{slot} {head}" for slot, head in sorted(heads.items())))
    warning = (f"`tuning-changelog`'s ▶️ CONTINUE block names HEAD {', '.join(stale)}, and the ledger's HEAD is "
               f"{at} — the block was written before the ledger moved. The ledger is what resume trusts; bring "
               f"the block up to it")
    return {"named": named, "heads": heads, "stale": stale, "warning": warning}


def _ledger_versions(project_dir):
    """Every snapshot on disk as a bare number ("7" for `v_007.json`)."""
    out = set()
    root = _state_root(project_dir)
    try:
        presets = [p for p in os.listdir(root) if os.path.isdir(os.path.join(root, p))]
    except OSError:
        return out
    for preset in presets:
        try:
            names = os.listdir(os.path.join(root, preset))
        except OSError:
            continue
        for name in names:
            match = _LEDGER_RE.match(os.path.splitext(name)[0])
            if name.endswith(".json") and match:
                out.add(str(int(match.group(1))))
    return out


def _refuse_unbanked(project_dir, version, said):
    """`ProcessError` unless `version` names a ledger version banked on disk (#57 P0): the configuration a series was
    taken under has to exist. `said` is how the caller's line named it (`--under 'v_009'`, `--bind C=v_009`)."""
    banked = _ledger_versions(project_dir)
    match = _LEDGER_RE.fullmatch(str(version).strip())
    if not match or str(int(match.group(1))) not in banked:
        raise ProcessError(f"{said}: not a banked ledger version"
                           + (f" (banked: {', '.join('v_%03d' % int(v) for v in sorted(banked, key=int))})"
                              if banked else " -- this project has no ledger yet"))


def _series_number(series):
    """The series a capture-import names, `49` or `_49`, as an int (#134, H I-7). A typed mistake (`1a`) is the verb's
    refusal, exit 1: it reached `int()` unguarded, inside the import and before REW was asked, and exited 70."""
    try:
        return int(str(series).strip().lstrip("_"))
    except ValueError:
        raise ProcessError(f"capture-import: {series!r} is not a number -- the series the titles carry, e.g. "
                           "capture-import 49 ...") from None


def resolves(item, project_dir, versions=None, naming=None):
    """True when `item` points at something checkable rather than describing one.

    A measurement name is accepted on its grammar alone: whether REW actually holds it is a
    question only REW can answer, and the front-end that talks to REW checks that (`plan_audit`).
    Typed here means typed there -- a field to resolve rather than a sentence to grep.
    """
    text = str(item).strip()
    if not text:
        return False
    versions = _ledger_versions(project_dir) if versions is None else versions
    for match in _LEDGER_RE.finditer(text):
        if str(int(match.group(1))) in versions:
            return True
    for match in _PATH_RE.finditer(text):
        if os.path.exists(os.path.join(project_dir, match.group())):
            return True
    naming = _load_naming() if naming is None else naming
    if naming is not None:
        # A capture is a title in the grammar WITH a method (`naming-and-structure.md §3`). The
        # grammar leaves the method optional -- it also describes version strings -- but here
        # optional means "banked as v_003" parses as a measurement called "banked as v", and the
        # sentence walks straight through the gate it was written to stop.
        for candidate in (text,) + tuple(text.split(" + ")):
            parsed = naming.parse_name(candidate.strip())
            if parsed and parsed.get("method"):
                return True
    return False


def _outstanding(round_, optional=False):
    """Expected captures of one round that are neither taken nor skipped -- the REQUIRED ones; the optional ones
    ("if you have time", skill #80) with `optional=True`. An optional capture left untaken is not a gap: it is on
    the list so that it is not forgotten in the car and so that its taking is recorded, not so that its absence
    holds a stop."""
    wanted = set(round_.get("optional") or [])
    return [
        title
        for title in round_.get("expected", [])
        if (title in wanted) == optional
        and not _is_taken(round_, title) and title not in round_.get("skipped", {})
    ]


def render_round_list(round_):
    """The round's list as the Arbiter reads it (skill #75): column by column, the switch of setup named, optional
    captures marked. This is what `capture-start` prints, and the message that asks him to measure is this text."""
    lines = []
    optional = set(round_.get("optional") or [])
    setup = round_.get("setup") or {}
    if setup.get("first"):
        lines.append(f"  set up for {setup['first']}"
                     + (f" (last taken: {setup['from']})" if setup.get("from") else " (--start)"))
    last_method = None
    for group in round_.get("groups") or []:
        switch = last_method is not None and group.get("method") != last_method
        lines.append(f"  {group.get('label')}" + ("   <- switch: " + ("tripod in, driver out" if group.get("method") == "sw"
                                                                       else "tripod out, driver in") if switch else ""))
        for name in group.get("names") or []:
            lines.append(f"    {name}" + ("   (optional)" if name in optional else ""))
        last_method = group.get("method")
    if not round_.get("groups"):
        for name in round_.get("expected") or []:
            lines.append(f"    {name}" + ("   (optional)" if name in optional else ""))
    return lines


def _outstanding_optional(round_):
    return _outstanding(round_, optional=True)


def _last_method_taken(round_):
    """`(method, title)` of the last capture a round recorded, by its `at` -- the setup the car is in (skill #78)."""
    naming = _load_naming()
    if not round_ or naming is None:
        return None, None
    last = None
    for title, entry in (round_.get("taken") or {}).items():
        if not _is_taken(round_, title):
            continue           # a superseded row is a typo's trace, not the setup the car was left in (N17)
        parsed = naming.parse_name(title)
        if parsed and parsed.get("method") and (last is None or str((entry or {}).get("at") or "") > last[0]):
            last = (str((entry or {}).get("at") or ""), parsed["method"], title)
    return (last[1], last[2]) if last else (None, None)


def _is_taken(round_, title):
    """Taken AND still standing: a superseded row is evidence of a typo, not of a measurement. Every reader of a
    round's `taken` asks this, and none counts the row itself (N17, #134)."""
    entry = (round_.get("taken") or {}).get(title)
    return isinstance(entry, dict) and not entry.get("superseded_by")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _writer_sha():
    """Which checkout of the method is doing the writing — the one call site (`Process._stamp`).

    A function rather than an inline load so the header logic can be exercised against sha values
    a test chooses. `provenance` proves it can read a real checkout on real repositories; what has
    to be proved HERE is when a header is written and when it is not, and that is a different
    question from what git says.
    """
    prov = _load_rew_tool_module("provenance")
    return prov.skill_sha() if prov is not None else ""


def _empty_state():
    return {
        "schema_version": SCHEMA_VERSION,
        "updated": _now(),
        "active_phase": None,
        "phases": {p: {"status": PHASE_TODO, "title": PHASE_TITLES[p]} for p in PHASES},
        "plan": [],
        "reviewer": None,
        "targets": {},
        # The capture round currently open, or None. Only the ACTIVE one is here, the same way
        # only the active phase is: every round that ever happened is in the journal (SCR-034).
        "capture": None,
    }


#: Versions this file wrote before 3.0. A file at one of these is not corrupt, it is old — and
#: the difference decides whether the reader is told to fix something or to migrate.
_MIGRATABLE_SCHEMA_VERSIONS = (1, 2)


def migration_command(project_dir="<project-dir>"):
    """The way across, as a line somebody can paste.

    An absolute path, not `rew_tool/state/migrate.py`: that relative form only resolves for
    someone standing inside a checkout, and the people who need this most installed the skill as
    a plugin and have no such directory near their project.

    It IMPORTS into a new project rather than converting this one. The old project is left exactly
    as it is and still opens in 2.x, which is where its history stays readable.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return f"python3 {os.path.join(here, 'migrate.py')} {project_dir} --into <new-project-dir>"


def validate(state):
    """Raise `ProcessError` if `state` isn't a shape a reader can trust. Returns it otherwise."""
    if not isinstance(state, dict):
        raise ProcessError("process state must be a JSON object")
    found = state.get("schema_version")
    if found != SCHEMA_VERSION:
        if found in _MIGRATABLE_SCHEMA_VERSIONS:
            # Named, with a command that runs. This used to say only "unsupported schema_version 1
            # (expected 3)", which stops every write — `add-step`, `done`, `enter-phase`, every
            # `capture-*` — with no way out stated, while `show` and `plan` still read fine, so it
            # looks half-alive rather than out of date (2026-08-12).
            raise ProcessError(
                f"this project's process state is schema v{found}; 3.0 reads v{SCHEMA_VERSION}. "
                f"Nothing is wrong with it — it is a 2.x project. Migrate once and carry on:\n"
                f"    {migration_command()}"
            )
        raise ProcessError(
            f"unsupported schema_version {found!r} (expected {SCHEMA_VERSION})"
        )
    active = state.get("active_phase")
    if active is not None and active not in PHASES:
        raise ProcessError(f"unknown phase {active!r}; known: {', '.join(PHASES)}")
    seen = set()
    for step in state.get("plan", []):
        sid = step.get("id")
        if not sid:
            raise ProcessError("every plan step needs an id")
        if sid in seen:
            raise ProcessError(f"duplicate step id {sid!r}")
        seen.add(sid)
        if step.get("status") not in STEP_STATUSES:
            raise ProcessError(f"step {sid!r} has unknown status {step.get('status')!r}")
        if step.get("status") == STEP_DONE and not step.get("evidence"):
            raise ProcessError(f"step {sid!r} is done with no evidence")
    return state


COVERS_IN_NAME = 3


def _clean_covers(covers):
    """The covered facts as a list: blanks dropped, order kept, no duplicate."""
    if isinstance(covers, str):
        covers = [covers]
    out = []
    for item in covers or []:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def covers_summary(covers, keep=COVERS_IN_NAME):
    """`a, b, c +5` — what a step's name says about what it covers.

    A number alone is not a subject (the Arbiter's standing rule, and S-031's whole finding), so
    the first few are NAMED and only the tail is counted. The full list stays on the step, for a
    window to expand and a session to tick off.
    """
    covers = _clean_covers(covers)
    shown = covers[:keep]
    rest = len(covers) - len(shown)
    return ", ".join(shown) + (f" +{rest}" if rest else "")


def _locked(method):
    """`method`, a writer of `Process`, under the project's writer lock (#141, J2b): its load, its change, its write and
    its event as one step, so another writer -- TCC, a second command line -- cannot write in between and lose this
    one's change or have its own lost. What must run with the lock free runs first (`Process._ready_to_hold`), and
    before that the folder is checked to be a project's (`Process._require_home`): the hold makes the project's
    `.autosound/`, so a refusal there must come first. A writer that calls another (`capture_import` ->
    `start_capture`, `supersede_capture` -> `record_capture`) takes the lock once: the hold is re-entrant within a
    thread. `enter_phase` and `check_captures` are not decorated: they read git, `gh` or REW first, and take the hold
    themselves after."""
    @functools.wraps(method)
    def locked(self, *args, **kwargs):
        self._require_home(method.__name__)
        self._ready_to_hold()
        with _hold(self.project_dir):
            return method(self, *args, **kwargs)
    return locked


class Process:
    """Read and advance one project's process state.

    `root` is the project's `process/` directory — the DATA is project-local, the CODE is in the
    skill, same division as `PresetHistory`.
    """

    def __init__(self, root):
        # Deliberately does NOT create `root`: merely ASKING about a project's process state must
        # not write to it. `contract.py` constructs this to report "process-state.json: missing",
        # and a consumer UI runs that check on every launch -- creating an empty `process/` in
        # whatever folder the user happened to open would be the audit inventing the thing it is
        # auditing. The write paths (`_write`, `_append`) create the directory instead.
        self.dir = root
        # Whether this run has already decided about its header event (`_stamp`). One decision per
        # instance: the sha is a property of the code that is running, and that does not change
        # under it.
        self._stamped = False
        # A state change written and its event not yet appended (F M-7): `_write` sets it, `_append` clears it, and
        # says what landed when the append is refused in between.
        self._unjournaled = False
        # The sha `_stamp` writes, asked of git before this writer's first hold (`_ready_to_hold`, #141): git is never
        # asked with the project's lock held.
        self._sha = None
        # The events still owed after the one being appended, `[(type, payload)]`, when one state write owes two
        # (`start_capture` superseding a round, #141): a refusal of the first names them too (`_append_refused`).
        self._owed_after = []
        # `(path, reason)` of the plan file the last `start_capture` wrote -- reason None once it is written -- for
        # `capture-start` to say (S-101): one that could not be written was said nowhere.
        self._plan_written = None

    # -- paths --
    @property
    def project_dir(self):
        """The project this `process/` belongs to — what evidence paths are resolved against."""
        return os.path.dirname(os.path.abspath(self.dir))

    @property
    def state_path(self):
        return os.path.join(self.dir, "process-state.json")

    @property
    def journal_path(self):
        return os.path.join(self.dir, "journal.jsonl")

    # -- reads --
    def load(self, strict=False):
        """The current slice. A missing file reads as an empty process in both modes: a project that has never run
        shows an empty plan, not a traceback.

        A file that is THERE and cannot be read -- empty, cut off, not UTF-8, not a JSON object -- is where the two
        modes part (#136, audit K-2):

        * lenient, the default: the empty process, as before. For readers -- a screen, a lookup -- where an empty
          plan beats a traceback: the callers outside this module, TCC, and the display-only verbs
          (`_DISPLAY_VERBS`).
        * `strict=True`: `project_io.Unreadable`, naming the file and its repair; match it by its `is_unreadable`
          attribute. Every other verb reads so before it does anything (`_main`); every writer method reads so
          itself (R25: an open refused for a moment must not become an empty process the writer builds on), and so
          do `handoff()` and `contract.py check`.

        Nothing is written from what a lenient read made of such a file: `_write` and `_append` read the file
        strictly once more before they write.

        A state a newer method wrote (`schema_version` above this copy's) is refused by the strict read with
        `ProcessError`, naming both numbers and the way to a newer method (#136, audit T-21); `validate` refused it
        only at the write, after the reads before it had taken it for this copy's. The lenient read returns it as
        it did.
        """
        try:
            state = self._read_state()
        except Exception as exc:  # noqa: BLE001 -- only the unreadable file is read as empty; anything else raises
            if strict or not getattr(exc, "is_unreadable", False):
                raise
            state = None
        if strict:
            self._refuse_newer(state)
        base = _empty_state()
        if state is None:
            return base
        base.update(state)
        for phase, entry in base["phases"].items():
            entry.setdefault("title", PHASE_TITLES.get(phase, phase))
        return base

    def _read_state(self):
        """`process-state.json` read strictly: its JSON object, None when there is no file, and `Unreadable` naming
        the file and its repair when there is one that cannot be read."""
        return _project_io().read_json(self.state_path, None, repair=self._repair(),
                                       repair_encoding=self._repair(encoding=True))

    def _refuse_newer(self, state):
        """`state` as read, unless a newer method wrote it: `ProcessError` then (#136, audit T-21) -- this copy
        cannot read it, and a write from here would write it down to v3."""
        io_ = _project_io()
        newer = io_.newer_schema(state, SCHEMA_VERSION)
        if newer is not None:
            raise ProcessError(f"{self.state_path} is schema v{newer}; this method reads v{SCHEMA_VERSION} -- "
                               f"{io_.UPDATE_THE_METHOD}")
        return state

    def _repair(self, encoding=False):
        """The line that puts an unreadable `process-state.json` right, said with the refusal (#136): the committed
        copy back, or, for a file in another code page (`encoding`), the rewrite as UTF-8 that `contract.py
        repair-encoding` offers.

        Said as what it gives (H 13): the committed copy can be far older than the journal -- a project's repository
        may hold only its first commit -- and nothing replays the events since into it; a project with no committed
        copy (not a repository) gets `fatal` from git. There the file is moved aside and the process starts empty,
        the journal keeping every event."""
        if encoding:
            contract_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract.py")
            return f"rewrite it as UTF-8: python3 {contract_py} repair-encoding {self.project_dir}"
        return (f"restore the last committed copy: git -C {os.path.abspath(self.dir)} checkout HEAD -- "
                f"process-state.json -- it may be older than the journal, and nothing replays the events since into "
                f"it; with no committed copy, move process-state.json aside: the process starts empty, and the "
                f"journal keeps every event")

    def events(self, limit=None, kinds=None):
        """Journal entries oldest-first. `kinds` filters by event type.

        The reader for a screen (TCC), lenient as `load()` is (#134, R53): no journal, and a journal that is there and
        cannot be opened -- held by another program, a permission, a folder in its place -- are no events, `[]`. The
        method's own readers read the journal through `_events`, which refuses both what cannot be opened and a line
        in another code page, naming it and its repair.

        Read as bytes, split on "\\n" alone (T I8: U+2028, U+2029 and U+0085 inside an event's text are not line
        ends), each line decoded by itself (R23). A line that is not an event -- torn by a cut write, inside a
        character too, or not JSON -- is skipped, and so, here, is a line written in another code page; both are
        counted in `journal_skipped`, `{"torn": [line numbers], "not_utf8": [...]}`, from 1 (both empty for a journal
        that could not be opened). A byte-order mark stays part of its line, as with `encoding="utf-8"` before."""
        try:
            events, torn, foreign = self._read_journal()
        except Exception as exc:  # noqa: BLE001 -- the journal that cannot be opened alone is no events here
            if not getattr(type(exc), "is_unreadable", False):
                raise
            events, torn, foreign = [], [], []
        self.journal_skipped = {"torn": torn, "not_utf8": [number for number, _line in foreign]}
        return self._pick(events, limit, kinds)

    def _events(self, limit=None, kinds=None):
        """`events()` read strictly (#134, F I-2, H I-2, R53): what every reader of the method reads -- each writer,
        each verdict, `amp-changes` and `listening-verdicts`, `session_closed`, `_stamp`, the flaw-map gate, and what
        the other tools ask (`capture_rounds`, `protective_record_for`, ...). A journal that is there and cannot be
        opened raises `Unreadable` (`project_io.cannot_open`): read as empty, a held journal was a project with no
        history. So does a line written in another code page, naming the line(s) and the repair (`contract.py
        repair-encoding`): skipped, a round, a series, a protective record or a ruling was gone from what the method
        decided and recorded, without a word. A torn line is skipped as in `events()`."""
        events, torn, foreign = self._read_journal()
        self.journal_skipped = {"torn": torn, "not_utf8": [number for number, _line in foreign]}
        if foreign:
            raise self._not_utf8(foreign)
        return self._pick(events, limit, kinds)

    def _read_journal(self):
        """`(events, torn, foreign)`: every event of the journal, and the lines skipped -- `torn`, their numbers (not
        JSON, not an object, or cut inside its last character), and `foreign`, `[(number, bytes)]` (not UTF-8 before
        its end: another code page, or none -- R56). `[]`s when there is no journal; `Unreadable`
        (`project_io.cannot_open`) when there is one and it cannot be opened."""
        io_ = _project_io()
        try:
            with open(self.journal_path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return [], [], []
        except OSError as exc:
            raise io_.cannot_open(self.journal_path, exc) from exc
        events, torn, foreign = [], [], []
        for number, line in enumerate(raw.split(b"\n"), 1):
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError:
                # Cut inside its last character (R23) is a torn append; a wrong byte before the end is a code page.
                if io_.cut_inside_a_character(line.rstrip(b"\r")):
                    torn.append(number)
                else:
                    foreign.append((number, line))
                continue
            if not text.strip():
                continue
            try:
                event = json.loads(text)
            except ValueError:
                torn.append(number)   # a torn line must not hide the rest of the history
                continue
            if not isinstance(event, dict):
                torn.append(number)   # JSON, but no event: every reader asks an event for its type
                continue
            events.append(event)
        return events, torn, foreign

    @staticmethod
    def _pick(events, limit, kinds):
        if kinds:
            events = [e for e in events if e.get("type") in kinds]
        return events[-limit:] if limit else events

    def _not_utf8(self, foreign):
        """The refusal for journal lines that are not UTF-8 (H I-2), `foreign` as `_read_journal` gives them: the lines,
        and the way each is mended. A line a code page makes JSON of is rewritten line by line (`repair-encoding`), the
        lines in UTF-8 left as they are; one no code page makes JSON of -- an old append cut inside a character, the
        next event glued on -- cannot be rewritten, and is set aside, bytes kept (`repair-encoding --set-aside`, R56):
        named so, the refusal no longer sends the person to a survey that offers nothing. Told apart by `state.py`'s
        `page_reads`, the rule the survey uses; with `state.py` not loadable, every line is told the rewrite."""
        io_ = _project_io()
        state_mod = _load_sibling("state/state.py")

        def shown(numbers):
            return ", ".join(str(n) for n in numbers[:10]) + (f" and {len(numbers) - 10} more" if len(numbers) > 10
                                                               else "")
        numbers = [number for number, _line in foreign]
        nowhere = [number for number, line in foreign
                   if state_mod is not None and not state_mod.page_reads(line.rstrip(b"\r"))]
        if not nowhere:
            return io_.Unreadable(
                self.journal_path, f"has {len(numbers)} line(s) not in UTF-8 -- written in another code page: line "
                                   f"{shown(numbers)}", io_.reencode_line(self.project_dir))
        repair = io_.set_aside_line(self.project_dir)
        if len(nowhere) < len(numbers):
            repair += "; then rewrite the rest as UTF-8: " + io_.reencode_line(self.project_dir).split(": ", 1)[1]
        return io_.Unreadable(
            self.journal_path, f"has {len(numbers)} line(s) not in UTF-8: line {shown(numbers)} -- no code page makes "
                               f"JSON of line {shown(nowhere)} (a write cut off in it, perhaps with the next "
                               f"glued on)", repair)

    def _require_journal(self):
        """Before a state write, what would keep its event from following it (F M-7): a journal that cannot be read
        whole -- held, a permission, a line in another code page (`_events`) -- or cannot be appended to. Refused here,
        nothing is written; the append's own refusal, after the write, would leave the change in the state with no
        line in the journal for it. A journal that reads and refuses the append is said as that, as the append's own
        refusal says it (`cannot_append`, m4)."""
        self._events(limit=1)
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, "ab"):
                    pass
            except OSError as exc:
                raise _project_io().cannot_append(self.journal_path, exc) from exc

    def step(self, state, step_id):
        for entry in state.get("plan", []):
            if entry.get("id") == step_id:
                return entry
        return None

    # -- transitions --
    def enter_phase(self, phase, note=None):
        """Make `phase` active, marking every earlier phase done and later ones todo.

        Re-entry is normal (Phase 5 is explicitly cyclical), so this is not a one-way ratchet:
        entering an earlier phase again makes it current and leaves the later ones' history alone.

        The gates run with the project's lock free (#141, J2b): the intake gate asks git and `gh`, for up to a minute
        and a half, and no other writer waits that long behind it. Then, under the hold, the state is read again and
        the phase entered into it as it is THEN -- a step another writer added meanwhile stays. A phase another writer
        made active meanwhile refuses this one, nothing written: the gates answered for the phase they saw. A folder
        that is no project's is refused before the gates (#141, R46): `enter-phase -1` alone starts a project where
        none is yet.
        """
        phase = str(phase)
        if phase not in PHASES:
            raise ProcessError(f"unknown phase {phase!r}; known: {', '.join(PHASES)}")
        self._require_home(f"enter-phase {phase}")
        self._ready_to_hold()
        state = self.load(strict=True)  # a writer reads strictly itself (#136, R25): see `_write`
        previous = state.get("active_phase")
        # No exemptions. A project brought over from 2.x is a NEW project — `migrate.py --into`
        # imports the car's current state and nothing else — so it starts at phase −1 and earns
        # each gate like any other. There was briefly a softened path for projects migrated in
        # place; the in-place migration is gone, and a waiver nothing can grant is a waiver that
        # only waits to be granted by mistake (2026-08-12).
        _require_intake(phase, previous, self.project_dir)
        _require_target(phase, previous, state)
        _require_flaw_map(phase, previous, self.project_dir)
        _require_profile_facts(phase, previous, self.project_dir)
        with _hold(self.project_dir):
            state = self.load(strict=True)
            now = state.get("active_phase")
            if now != previous:
                def said(key):
                    return "no phase" if key is None else f"phase {key}"
                raise ProcessError(f"phase {phase} is not entered: {said(now)} is active now, and its gates were "
                                   f"checked with {said(previous)} active -- another writer moved the process "
                                   f"meanwhile; nothing was written, run enter-phase {phase} again")
            if previous and previous != phase:
                state["phases"][previous]["status"] = PHASE_DONE
            state["phases"][phase]["status"] = PHASE_CURRENT
            state["active_phase"] = phase
            self._write(state)
            self._append(EV_PHASE_ENTERED, phase=phase, previous=previous, note=note)
        return state

    @_locked
    def add_step(self, step_id, name, source=SOURCE_SKILL, phase=None, covers=None):
        # (skill #72) The name leads with the step's id -- `_named_by_id`, below the class.
        """Add a plan step. Instantiated from the phase template (`skill`) or situational
        (`project`) — the distinction is what lets the UI show which steps this car needed.

        `covers` names WHAT the step closes — the facts themselves, as `project.py open-questions`
        and `dsp_profile.py open-questions` print them (dotted paths). It exists because a step had
        nowhere to carry its content and so carried a COUNT: the Arbiter read `Закрити відкриті
        поля: project.json (8) і dsp_profile.json (5)` in his window and answered «зовсім не
        зрозумілий» — thirteen facts, named nowhere he could see, in the one artefact he acts on
        (S-031). The names existed the whole time; the plan dropped them.

        The step's NAME is then composed here, not typed: the first `COVERS_IN_NAME` covered facts
        and `+N` for the rest. Generated, because a caller free to write the summary by hand is a
        caller free to write the count again.
        """
        covers = _clean_covers(covers)
        if covers:
            summary = covers_summary(covers)
            if summary not in name:
                name = f"{name}: {summary}"
        name = _named_by_id(step_id, name)
        state = self.load(strict=True)
        if self.step(state, step_id):
            raise ProcessError(f"step {step_id!r} already exists; steps are never re-added")
        phase_key = str(phase) if phase is not None else state.get("active_phase")
        if phase_key not in PHASES:
            # A step whose phase is not one of the skeleton's is a step in NO phase: `plan_for`
            # only ever asks for real ones, so it is written, counted by nothing and displayed
            # nowhere — not in `plan`, not in a consumer front-end (found by audit, 2026-08-12).
            raise ProcessError(
                f"step {step_id!r} names phase {phase_key!r}, which is not a phase. "
                f"Known: {', '.join(PHASES)}. A step outside them is written and then invisible "
                "to every reader, including this project's own plan."
            )
        entry = {
            "id": step_id,
            "name": name,
            "status": STEP_TODO,
            "source": source,
            "attempt": 1,
            "skip": False,
            "phase": phase_key,
            "evidence": [],
            "covers": covers,
        }
        state["plan"].append(entry)
        self._write(state)
        self._append(EV_STEP_ADDED, step=step_id, name=name, source=source, covers=covers)
        return entry

    @_locked
    def start_attempt(self, step_id):
        """Begin (or re-begin) a step. A second call is attempt 2 — the redo is recorded, not
        hidden, so "we tried this twice" survives into the plan the Arbiter reads."""
        state = self.load(strict=True)
        entry = self._require(state, step_id)
        if entry["status"] == STEP_IN_PROGRESS:
            return entry
        if entry["status"] in (STEP_DONE, STEP_SKIPPED):
            entry["attempt"] = int(entry.get("attempt", 1)) + 1
        entry["status"] = STEP_IN_PROGRESS
        entry["skip"] = False
        self._write(state)
        self._append(EV_ATTEMPT_STARTED, step=step_id, attempt=entry["attempt"])
        return entry

    @_locked
    def finish_step(self, step_id, evidence):
        """Mark a step done. `evidence` is required, and at least one item must RESOLVE (SCR-035).

        Evidence is a list of pointers to something a later session can check — a REW measurement
        name in the grammar, a ledger version that exists, a project file that exists. Prose may
        ride along; it may not be the whole list. This is the rule that makes resume trustworthy:
        the reconciler compares each done step against reality, and "done" with nothing checkable
        is indistinguishable from a model that merely said so -- which is exactly what one did,
        for four phases, with an empty project folder.
        """
        if isinstance(evidence, str):
            evidence = [evidence]
        evidence = [e for e in (evidence or []) if str(e).strip()]
        if not evidence:
            raise ProcessError(
                f"step {step_id!r} cannot be done without evidence "
                "(measurement names, ledger vNNN, or an audit entry)"
            )
        # A step that asked for captures is done when they came back AND passed (SCR-040). The
        # refusal is the record's, not the model's judgement: "I looked at the graphs and they seem
        # fine" is exactly the sentence this gate exists to stop being load-bearing.
        state_now = self.load(strict=True)
        round_ = state_now.get("capture") or {}
        if round_ and not round_.get("closed") and round_.get("step") == step_id:
            unusable = self.unusable_captures(state_now)
            if unusable:
                raise ProcessError(
                    f"step {step_id!r} asked for captures that are not usable yet: "
                    + ", ".join(unusable)
                    + ". Run `capture-check` (and re-take what it fails) before closing the step — "
                    "a capture that exists is not a capture that can be analysed."
                )
        versions = _ledger_versions(self.project_dir)
        naming = _load_naming()
        if not any(resolves(item, self.project_dir, versions, naming) for item in evidence):
            if naming is None:
                # The grammar's absence, not the evidence (the final review's M2): a name in the grammar resolves to
                # nothing only because nothing here can recognise it.
                raise ProcessError(
                    f"step {step_id!r} has evidence, but none of it resolves here: "
                    + "; ".join(repr(str(e)) for e in evidence)
                    + f". {_naming_unloaded()}, so a REW measurement name resolves to nothing until it loads; a "
                    "ledger version that exists (`v_003`) or a project file that exists still resolves")
            raise ProcessError(
                f"step {step_id!r} has evidence, but none of it resolves: "
                + "; ".join(repr(str(e)) for e in evidence)
                + ". At least one item must be checkable rather than described — a REW measurement "
                "name in the grammar (`tw-L_1 (rta)`), a ledger version that exists (`v_003`), or "
                "a project file that exists (`autosound_context.md`). Describing the work is not "
                "recording it: write the artefact first, then close the step against it."
            )
        state = self.load(strict=True)
        entry = self._require(state, step_id)
        entry["status"] = STEP_DONE
        entry["skip"] = False
        entry["evidence"] = sorted(set(entry.get("evidence", [])) | set(map(str, evidence)))
        self._write(state)
        self._append(EV_STEP_DONE, step=step_id, evidence=entry["evidence"])
        return entry

    @_locked
    def skip_step(self, step_id, superseded_by=None, reason=None):
        """Supersede a step. It stays in the plan, dimmed — never removed (SCR-004).

        A skip says WHY, or it is refused: either the step that supersedes it or a sentence.
        On the live project every one of the nine skips on record carried neither, so a later
        session reading the plan cannot tell a step that was decided against from one that was
        dropped by accident -- and proposes it again. Same shape as `done` requiring evidence:
        the refusal belongs to the record, not to the model's discipline (release review
        2026-09-09).
        """
        if not (superseded_by or (reason or "").strip()):
            raise ProcessError(
                f"skip {step_id!r} needs a reason: either the step that supersedes it "
                "(`--superseded-by <id>`) or a sentence saying why it is not being done. "
                "A skip with no reason is indistinguishable from a step forgotten, and the next "
                "session proposes it again.")
        state = self.load(strict=True)
        entry = self._require(state, step_id)
        entry["status"] = STEP_SKIPPED
        entry["skip"] = True
        self._write(state)
        self._append(EV_STEP_SKIPPED, step=step_id, superseded_by=superseded_by, reason=reason)
        return entry

    @_locked
    def block_step(self, step_id, reason):
        """Mark a step blocked — waiting on a measurement, a part, the car being available."""
        state = self.load(strict=True)
        entry = self._require(state, step_id)
        entry["status"] = STEP_BLOCKED
        entry["blocked_reason"] = reason
        self._write(state)
        self._append(EV_STEP_BLOCKED, step=step_id, reason=reason)
        return entry

    @_locked
    def record_reviewer(self, vendor, model, phase=None, step=None, outcome=None,
                        review=None, mode=None):
        """Who reviewed, on what model, when — and WHAT THEY ARGUED (SCR-027).

        `review` is a project-relative path to the critique text (`process/reviews/<ts>-<role>.md`).
        Without it the record said a critique happened and how it was resolved, and lost the
        reasoning — which is the part worth reading back a week later, and the part an audit needs.

        `mode` distinguishes a channel that ran from one worked by hand: `"clipboard"` means the
        package was compiled and answered by a human paste, which must not look like no review at
        all.
        """
        state = self.load(strict=True)
        state["reviewer"] = {
            "vendor": vendor,
            "model": model,
            "at": _now(),
            "phase": str(phase) if phase is not None else state.get("active_phase"),
            "step": step,
            "outcome": outcome,
            "review": review,
            "mode": mode,
        }
        self._write(state)
        self._append(EV_CRITIC_CALLED, vendor=vendor, model=model, step=step, outcome=outcome,
                     review=review, mode=mode)
        return state["reviewer"]

    # -- capture rounds (SCR-034) --
    @_locked
    def start_capture(self, version, expected=(), phase=None, note=None, step=None, origin=None, under=None,
                      level=None, level_read_as=None, plan=False, optional=(), start_method=None):
        """Open a capture round: what was asked for, at which `_N`, in which phase.

        **The list comes from the plan, not from a message** (skill #77, #75): with `plan=True` the round's
        `expected` is `naming.expected_groups(phase, glossary, version)` -- what the method says this phase
        measures, for the channels the project has on -- and the titles given beside it are added in their
        place; without it, the titles given are the list. Either way the round carries its columns (`groups`,
        skill #79/#83: Solo/Group by sw/rta, what a front-end draws), ordered by SETUP (skill #78): the method the
        car is set up for first -- `start_method`, else the last capture the previous round recorded -- then one
        switch. `optional` names the captures that go on the list "if there is time" (skill #80): listed, ordered,
        recorded when taken, and not a gap when not.

        `version` is the series number the titles carry (`_N`); a round opened with a ledger version
        (`v_001`) is still found, since `protective_record_for` matches either -- but the two are
        different counters (`naming-and-structure.md §1a/§5), and neither is derived from the other.
        Which one this round means is now RECORDED (`version_kind`) instead of left to a reader's
        guess, and a ledger version is CHECKED against the snapshots on disk.

        **The ledger is a precondition of a ledger-bound round; this call does not check it for a series
        round** (TCC-022, the Arbiter's stopper 2026-09-20). A Phase-0 baseline opens at its SERIES number,
        which names no configuration -- but by the one recipe (`capture-session-sheet.md` Block 0), whose
        first line, `enter-phase 0`, is the Phase -1 gate and refuses while `state/<preset>/` is missing:
        the first snapshot is banked before the baseline is measured. Naming a `v_NNN` says more: that
        these measurements were taken under a CONFIGURATION, and a round pointing at a version nobody
        banked cannot answer which one, while still looking complete. Four such rounds were opened in a row on a project made by TCC's Copy car -- which
        carries `project.json` and the profile and deliberately no `state/` -- and the flow's other
        half failed silently on the same fact: `apply.propose` could not produce a settings sheet
        and never said why. One half was lenient, the other mute; now both name the ledger.

        A ROUND, not a version: two rounds on the same DSP state are two passes, and what the
        Arbiter asks about is "this session's task". Opening a second round while one is open
        closes the first -- a round nobody closed is a round that ended when the next one began.
        """
        kind = version_kind(version)
        origin = _clean_origin(origin)
        if kind == "series" and not origin:
            self._refuse_foreign_series(version)
        if kind == "ledger":
            banked = _ledger_versions(self.project_dir)
            match = _LEDGER_RE.fullmatch(str(version).strip())
            if str(int(match.group(1))) not in banked:
                raise ProcessError(
                    f"capture round at {version!r}: no such ledger version on disk"
                    + (f" (banked: {', '.join('v_%03d' % int(v) for v in sorted(banked, key=int))})"
                       if banked else " -- this project has no ledger at all, which is what TCC's "
                                      "Copy car produces by design")
                    + ". A `v_NNN` round says these measurements were taken under that "
                      "CONFIGURATION, so the snapshot has to exist first. Two ways on, and they "
                      "are different questions:\n"
                      "  - the measurements are of a banked state -> bank it first "
                      "(`apply.propose`; phase -1's first ledger snapshot for a new project), then "
                      "open the round at the version it wrote;\n"
                      "  - the measurements are a baseline -> bank the first snapshot "
                      "(`phase_-1_intake.md` §5), enter Phase 0 and open the round at its SERIES number "
                      "(`capture-session-sheet.md` Block 0)."
                )
        # The ledger version these measurements were taken UNDER (#57 P0). A series names the measurements; the
        # configuration in the processor while they were taken is a second fact, and the tools that divide it
        # back out (`predict --from-state`) were typed it by hand -- one omitted flag applied the chain twice
        # and proposed +9.8 ms. Given, it is checked against the ledger and recorded. NOT given, nothing is
        # recorded: an early version of this bound every series round to the active slot's head, and a
        # baseline taken on the bare `v0` preset was then divided by a chain it was never measured through
        # (path_check: -240 dB where the file read -31 dB). A guess about the processor is the one thing this
        # field exists to replace.
        under_note = None
        if under is not None:
            _refuse_unbanked(self.project_dir, under, f"--under {under!r}")
        # S-026: the level a series was measured at is a condition of the SERIES, as a quantity. It sat in the
        # taste profile as «7 лампочок майстра», unreadable as dB and gone the moment the file stayed behind.
        level_rec = None
        if level is not None or level_read_as is not None:
            if level is not None and not re.search(r"-?\d+(\.\d+)?\s*dB", str(level)):
                raise ProcessError(f"--level {level!r}: a level is a quantity in dB (\"-25 dB rel. max\"); "
                                   "how it is read off the device goes in --level-read-as")
            level_rec = {"value": None if level is None else str(level).strip(),
                         "read_as": None if level_read_as is None else str(level_read_as).strip()}
        state = self.load(strict=True)
        previous = state.get("capture")
        number = int(previous.get("n", 0)) + 1 if previous else 1
        expected = [str(item) for item in (expected or []) if str(item).strip()]
        optional = [str(item) for item in (optional or []) if str(item).strip()]
        phase_key = str(phase) if phase is not None else state.get("active_phase")
        naming = _load_naming()
        # Read strictly (#134, batch 4's re-review, Out of Scope 6): a `glossary.json` or a `project.json` that
        # cannot be read refuses the round as itself, its file and repair, before anything is written -- read as no
        # glossary, `--plan` said it "needs the project's glossary", and a round opened, its titles placed by no codes.
        glossary = naming.Glossary.for_project(self.project_dir, strict=True) if naming is not None else None
        groups = []
        if plan:
            if naming is None:
                # The load failure, with why (#134, batch 4's re-review, Out of Scope 2; m4's form): it read as a
                # glossary nobody wrote.
                raise ProcessError(f"--plan builds its titles with the title grammar (naming.py), which cannot be "
                                   f"loaded{_load_failure('naming.py')} -- the round is not opened")
            if glossary is None or not glossary.channel_codes():
                raise ProcessError("--plan needs the project's glossary (project.json `glossary`, or glossary.json): "
                                   "the list is what the method says this phase measures, for the channels the "
                                   "project has -- with no glossary there is nothing to derive it from")
            if kind != "series":
                raise ProcessError("--plan builds titles from a SERIES number (`capture-start 55 --plan`); a ledger "
                                   "version names no `_N` (naming-and-structure.md §3)")
            if phase_key is None:
                raise ProcessError("--plan needs the phase the round measures for: `enter-phase <N>` first, or "
                                   "`--phase <N>`")
            groups = naming.expected_groups(phase_key, glossary, version)
            if not groups:
                raise ProcessError(f"the method's plan for phase {phase_key!r} captures nothing -- open the round "
                                   "with its titles instead")
        if naming is not None:
            groups = naming.place_in_groups(groups, expected + optional, glossary)
            first, from_title = (start_method, None) if start_method else _last_method_taken(previous)
            groups = naming.order_by_setup(groups, first)
            setup = {"first": first, "from": from_title,
                     "switches": naming.method_switches([g["method"] for g in groups])}
            expected = naming.flatten_groups(groups)
        else:
            setup = None
            expected = expected + [t for t in optional if t not in expected]
        round_ = {
            "id": "cap_%03d" % number,
            "n": number,
            "phase": phase_key,
            # The plan step this round satisfies (SCR-040). Without it a retake is a loose
            # measurement; with it, it is visibly attempt N of the step that asked for it.
            "step": step,
            "version": str(version),
            # WHICH counter that string is (TCC-022). `series` is explicitly NOT ledger-bound --
            # the round says so rather than leaving a reader to infer it from the spelling.
            "version_kind": kind,
            # Where these measurements were taken, when it was NOT this project (S-048). `_N` is
            # scoped to one project: two projects both have a `_49` and they mean different DSP
            # states on different days.
            "origin": origin,
            "under": None if under is None else str(under).strip(),
            "under_note": under_note,
            "level": level_rec,
            "issued": _now(),
            "closed": None,
            "expected": expected,
            # The columns the list is read in (skill #79/#83): `[{"kind", "label", "method", "names"}]`, the same
            # names as `expected`, in the order the car is taken in. A front-end draws THESE, not the phase plan.
            "groups": groups,
            # "If you have time" captures (skill #80): on the list, not a gap when left.
            "optional": optional,
            # Why the list is in this order (skill #78): the method taken first, from which capture it was read.
            "setup": setup,
            "taken": {},
            "skipped": {},
            "note": note,
        }
        # A round still open closes only now, past every refusal above (#134, H I-3), and in this one state write: its
        # close goes to the journal after the write (#141, J2b). Appended before it, a `--plan` refused after the close
        # left the journal saying the round closed while the state held it open, and a write a holder refused said
        # "it is as it was" over that journal -- the retry closed the round there a second time (part A's re-review,
        # N-1; W-8's review).
        closed = None
        if previous and not previous.get("closed"):
            closed = self._close_capture(state, previous, reason="superseded")
        state["capture"] = round_
        # One state write, the plan path in it (the final review's M3). The round went in first and its plan path in a
        # second write, and that one refused -- a Windows holder past the retries -- said "it is as it was" over a
        # state holding the round, with no `capture_issued`: the next round closed it as superseded. The plan FILE goes
        # down once the round is recorded (part A's re-review, N-3): written before the move, a move a holder refused
        # left the plan of a round that never opened, over the open round's own on the same series. Best effort, as
        # ever: the round is the record, and the file is where he reads it -- said either way by `capture-start`.
        round_["plan_path"] = self._capture_plan_path(round_)
        self._write(state)
        issued = dict(capture=round_["id"], phase=round_["phase"], version=round_["version"], version_kind=kind,
                      origin=origin, under=round_["under"], level=level_rec, expected=expected, groups=groups,
                      optional=optional, setup=setup, step=step, note=note)
        if closed is not None:
            # Two lines owed to the one write, the close's first: refused, it names the round's own too (F M-7).
            self._owed_after = [(EV_CAPTURE_ISSUED, issued)]
            try:
                self._append(EV_CAPTURE_CLOSED, **closed)
            finally:
                self._owed_after = []
            self._unjournaled = True              # the round's own line is owed still
        self._append(EV_CAPTURE_ISSUED, **issued)
        self._plan_written = self._write_capture_plan(round_)
        return round_

    @staticmethod
    def _capture_plan_label(round_):
        return round_["version"] if round_.get("version_kind") == "ledger" else f"_{round_['version']}"

    def _capture_plan_path(self, round_):
        """Where the round's plan file goes, relative to the project: `docs/plans/<_N|v_NNN>-capture.md` (skill #61)."""
        return f"docs/plans/{self._capture_plan_label(round_)}-capture.md"

    def _write_capture_plan(self, round_):
        """The round's list as a file the person can take to the car, at its `plan_path` (skill #61). Best effort: the
        round is the record, this is where he reads it -- written once the round is recorded, so a round a refusal
        never opened leaves no file, and never rewrites the open round's. Returns `(path, None)` once written, the path
        absolute, or `(path, reason)` when it could not be: the caller says that (S-101) -- it returned None, and
        `start_capture` dropped it, so a round opened with no word of its plan."""
        label = self._capture_plan_label(round_)
        rel = round_.get("plan_path") or self._capture_plan_path(round_)
        path = os.path.join(self.project_dir, *rel.split("/"))
        folder = os.path.dirname(path)
        try:
            os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(f"# {round_['id']} — captures at {label}"
                         + (f", phase {round_['phase']}" if round_.get("phase") else "")
                         + (f", step {round_['step']}" if round_.get("step") else "") + "\n\n")
                fh.write("\n".join(render_round_list(round_)) + "\n")
                if round_.get("note"):
                    fh.write(f"\n{round_['note']}\n")
        except OSError as exc:
            return path, str(exc)
        return path, None

    @_locked
    def reconcile_captures(self, rew_titles, round_id=None):
        """Close the open round's list against what REW holds, however it was captured (skill #77, rule 3).

        The Arbiter measures outside TCC as often as inside it, so the round is not told what was taken -- it
        READS it: a title REW holds that the list asked for is taken (under the list's spelling, with REW's own
        spelling kept beside it when they differ, so the rename is named and nothing is re-measured); a title of
        THIS series the list did not ask for is taken unplanned (the extra he took because he could); one he had
        skipped and then took after all is taken; what REW does not hold stays open, yellow. Another series' titles
        are not this round's business. A row the round SUPERSEDED is skipped (N17, #134): it is a typo's trace, so
        REW still holding its title takes nothing back and counts nowhere -- not among the titles held, the renames,
        or the extra taken beyond the list. Returns the verdict (`naming.validate_series` plus `missing_optional`),
        those titles left out. `round_id`, given, is the round the caller read (`capture-close`, #141, R7): another
        open by this hold is refused, `round_moved`, nothing written.
        """
        state, round_ = self._require_capture(round_id)
        naming = _load_naming()
        if naming is None:
            raise ProcessError(f"naming.py could not be loaded{_load_failure('naming.py')} -- the round cannot be read "
                               "against REW")
        # Strictly: a glossary cut off is refused, never read as none (#134, batch 4's re-review, Out of Scope 6).
        glossary = naming.Glossary.for_project(self.project_dir, strict=True)
        expected = [str(x) for x in round_.get("expected") or []]
        verdict = naming.validate_series([str(t) for t in rew_titles], expected, glossary)
        gone = {t for t in round_.get("taken") or {} if not _is_taken(round_, t)}
        verdict["matched"] = {n: a for n, a in verdict["matched"].items() if n not in gone}
        verdict["found"] = [n for n in verdict["found"] if n not in gone]
        verdict["renames"] = {a: n for a, n in verdict["renames"].items() if n not in gone}
        verdict["extra"] = [t for t in verdict["extra"] if t not in gone]
        now = _now()
        for name, actual in verdict["matched"].items():
            entry = round_["taken"].setdefault(name, {"at": now, "planned": True})
            if actual != name:
                entry["as_in_rew"] = actual
            round_["skipped"].pop(name, None)
        series = {naming.parse_name(n, glossary).get("version_n") for n in expected if naming.parse_name(n, glossary)}
        series.discard(None)
        for title in verdict["extra"]:
            parsed = naming.parse_name(title, glossary)
            if parsed and parsed.get("version_n") in series:
                round_["taken"].setdefault(title, {"at": now, "planned": False})
                round_["skipped"].pop(title, None)
        optional = set(round_.get("optional") or [])
        verdict["missing_optional"] = [t for t in verdict["missing"] if t in optional]
        verdict["missing"] = [t for t in verdict["missing"] if t not in optional]
        round_["reconciled"] = {"at": now, "rew": True, "matched": len(verdict["matched"]),
                                "extra": [t for t in verdict["extra"] if _is_taken(round_, t)],
                                "renames": verdict["renames"], "missing": verdict["missing"],
                                "missing_optional": verdict["missing_optional"]}
        self._write(state)
        self._append(EV_CAPTURE_RECONCILED, capture=round_["id"], version=round_["version"], **round_["reconciled"])
        return verdict

    def series_used(self):
        """Every series number this project's rounds have used, as ints."""
        seen = set()
        for round_ in self.capture_rounds():
            for value in [round_.get("version")] + list(round_.get("title_versions") or []):
                text = str(value).strip().lstrip("_")
                if text.isdigit():
                    seen.add(int(text))
        return seen

    def next_series(self):
        """This project's next series number: one past its highest, or 1 for a project with none (#56 item 10).

        The car checklist once said `_2` -- the number the documentation's examples use -- while the project's
        counter stood at `_49`; 47 measurements came back under `_2`/`_3` and were renamed twice. The refusal
        already knew the answer (`_refuse_foreign_series`); it arrived after the measurements existed."""
        seen = self.series_used()
        return max(seen) + 1 if seen else 1

    def _refuse_foreign_series(self, version):
        """A series number that is not this project's own is refused until its ORIGIN is on record.

        `_N` is project-scoped in fact and, until S-048, nowhere in writing. The session saw it and
        said it — «це серія `_49` зі старого проєкту, не червнева `_1`, на якій стоїть карта» — and
        then opened the round AS series 49, writing another project's numbering into this project's
        record as if it were its own. Joining a foreign `_49` to a flaw map built on this project's
        `_1` is the same class as an imported `fs_hz` that still says `measured`: data from another
        build arriving with nothing on it that says so.

        What counts as this project's own: a number it has already used, or the next one after its
        highest. A project with no rounds yet has no sequence to be outside of, and the first round
        is accepted whatever it is numbered.
        """
        seen = self.series_used()
        if not seen:
            return
        n = int(str(version).strip().lstrip("_"))
        if n in seen or n == max(seen) + 1:
            return
        raise ProcessError(
            f"series _{n} is not this project's: it has used "
            + ", ".join(f"_{v}" for v in sorted(seen))
            + f", so its own next one is _{max(seen) + 1}. `_N` numbers the series of ONE project "
              "— two projects both have a `_49` and they mean different DSP states on different "
              "days, and a foreign number joined to this project's flaw map is another build's "
              "data wearing this build's label. Either open the round at this project's own "
              f"number (`capture-start {max(seen) + 1} …`), or, if these measurements really were "
              "taken elsewhere, record where: `capture-start <N> --origin <project>:<their _N> …`."
        )

    @_locked
    def record_capture(self, title, at=None):
        """A measurement was taken. Unplanned ones are recorded too, flagged as such.

        `planned` is the whole point of recording rather than re-deriving: a capture that was not
        on the list is a fact about the round, and the derivation (`naming.expected_groups`) can
        only ever say what SHOULD have been taken.
        """
        state, round_ = self._require_capture()
        title = str(title).strip()
        if not title:
            raise ProcessError("a capture needs its REW title")
        planned = title in round_["expected"]
        round_["taken"][title] = {"at": at or _now(), "planned": planned}
        round_["skipped"].pop(title, None)  # taken after all
        self._write(state)
        self._append(
            EV_CAPTURE_TAKEN,
            capture=round_["id"],
            title=title,
            planned=planned,
            version=round_["version"],
        )
        return round_

    @_locked
    def capture_import(self, series, titles, binds, knobs, late=None):
        """Register measurements REW already holds as rounds of THIS project, one round per DSP state (#58 P3).

        A fast session registered 21 titles in 5 seconds as one round covering TWO DSP states (variants B and C),
        ignored the knobs warning three times, and got past a foreign-series refusal by inventing a round. The
        honest form of all three: the series is this project's (`_refuse_foreign_series` applies); each title's
        MODIFIER is bound to the ledger version it was measured under (`binds`, `{"": "v_012", "C": "v_013"}` --
        "" is the plain title), and a title whose modifier is not bound refuses the whole import rather than land
        in the wrong round; the knobs are required, not warned about; and a registration after the fact says so,
        with its reason (`late`), instead of looking like it happened in the car. Returns the rounds opened.

        Everything is checked before the first round is opened (#134, H I-3): the series, every title, every bind
        against the ledger. A bind was checked only when its DSP state's round opened, so a bad second bind was
        refused with the first round already on disk -- opened, taken, its knobs, closed -- and a re-run imported it
        again."""
        number = _series_number(series)
        _naming = _load_naming()
        if _naming is None:
            raise ProcessError(f"the title grammar (naming.py) cannot be loaded{_load_failure('naming.py')} -- nothing "
                               "was imported")
        if not isinstance(knobs, dict) or not knobs:
            raise ProcessError("capture-import needs the knobs as they stood (NAME=POS): two series cannot be "
                               "compared on the assumption that nobody touched anything")
        # Strictly: a glossary cut off is refused, never read as none (#134, batch 4's re-review, Out of Scope 6).
        glossary = _naming.Glossary.for_project(self.project_dir, strict=True)
        groups, stray = {}, []
        for title in titles:
            parts = _naming.parse_name(title, glossary)
            if not parts or str(parts.get("version_n")) != str(number):
                stray.append(title)
                continue
            modifier = parts.get("modifier")
            if modifier is None and " " in str(parts.get("code") or ""):
                # No glossary to split on: everything after the code's first word is the modifier, so two DSP
                # states cannot fall into one round just because the glossary is missing.
                modifier = str(parts["code"]).split(" ", 1)[1]
            groups.setdefault(modifier or "", []).append(title)
        if stray:
            raise ProcessError(f"not series _{series} in the grammar: {', '.join(stray)} -- nothing was imported")
        unbound = sorted(m for m in groups if m not in (binds or {}))
        if unbound:
            raise ProcessError("titles with no DSP state bound: " + ", ".join(repr(m or "(plain)") for m in unbound)
                               + " -- bind each to the ledger version it was measured under (--bind "
                               "MODIFIER=v_NNN; the plain title is --bind =v_NNN). One round is one DSP state.")
        for modifier in sorted(groups):
            if binds[modifier] is not None:
                try:
                    _refuse_unbanked(self.project_dir, binds[modifier], f"--bind {modifier}={binds[modifier]}")
                except ProcessError as exc:
                    raise ProcessError(f"{exc} -- nothing was imported") from None
        opened = []
        for modifier, group in sorted(groups.items()):
            note = "registered after the fact" + (f": {late}" if late else "")
            round_ = self.start_capture(str(series), expected=group, under=binds[modifier], note=note)
            for title in group:
                self.record_capture(title)
            self.set_knobs(knobs)
            self.close_capture(reason="imported" + (f" late: {late}" if late else ""))
            opened.append(round_["id"])
        return opened

    @_locked
    def set_protective(self, channel, legs, source="user"):
        """Declare what was in the chain for one channel of the OPEN round, and that it was RAW.

        Working-by-default is the rule (`protective.py`): a round nobody marks measured the system
        as configured, and nothing is de-embedded. This is how a round says otherwise.

        **Two answers, not three** (user's ruling 2026-09-06, hub TCC-005). `"OFF"` is the default
        and it means leave the capture alone — whether the chain was bare or carried a working
        crossover, which is part of the tune and read as it is; a recorded filter is the one case
        the maths removes before analysis. The front-end writes one of those two for every channel
        it captures, so a channel with NO record here did not come from the front-end: it came
        through MCP or a typed CLI call, or the front-end failed to write what it thought it did.
        That is what `protective.should_de_embed(..., baseline=True)` still answers `"check"` for.

        It lives on the ROUND rather than on a measurement because that is the granularity it
        actually has -- one protective set covers the sweeps of one pass, and it differs by channel
        within that pass (100 Hz on a mid, 1 kHz on a tweeter, nothing on a woofer). And it lives
        here rather than in a file of its own because the round already carries `phase` and
        `version`, which is exactly what a reader needs to know whether de-embedding is even
        appropriate: a phase-0 read wants it, a verification against a banked version does not.

        `legs` is `{"hp": ..., "lp": ...}` in the ledger's crossover vocabulary, or `"OFF"` to say
        plainly that this channel was swept with nothing in the chain. `"OFF"` is an ANSWER and is
        stored; leaving a channel out is a different thing and stays unanswered.
        """
        state, round_ = self._require_capture()
        channel = str(channel).strip()
        if not channel:
            raise ProcessError("a protective record needs the channel it applies to")
        if legs != "OFF":
            if not isinstance(legs, dict) or not any(k in legs for k in ("hp", "lp")):
                raise ProcessError(
                    f"{channel}: protective legs must be \"OFF\" or {{hp, lp}} in the ledger's "
                    f"crossover vocabulary ({{f, type, slope}} per leg), got {legs!r}. \"OFF\" "
                    f"means it was swept with nothing in the chain, which is an answer; omitting "
                    f"the channel means nobody said, which is not")
            for kind in ("hp", "lp"):
                leg = legs.get(kind)
                if leg in (None, "OFF"):
                    continue
                missing = [k for k in ("f", "type", "slope") if k not in leg]
                if missing:
                    raise ProcessError(f"{channel}.{kind}: a protective leg needs {missing} — "
                                       f"without them the filter cannot be taken back out")
        source = _protective_source(source)
        _refuse_channel_outside_round(round_, channel)
        round_.setdefault("protective", {})[channel] = legs
        round_.setdefault("protective_source", {})[channel] = source
        self._write(state)
        self._append(EV_CAPTURE_PROTECTIVE, capture=round_["id"], channel=channel, legs=legs,
                     source=source, phase=round_["phase"], version=round_["version"])
        return round_

    @_locked
    def amend_protective(self, capture_id, channel, legs, reason, source="user"):
        """Correct a CLOSED round's protective record, visibly as a correction (skill `#48`).

        `set_protective` requires an OPEN round, and the round most likely to need a correction is
        exactly the one an exporter has already read. On a live project a nine-position series was
        captured with 100 Hz LR24 on the mids and 1 kHz LR24 on the tweeters, and the round said
        `OFF` for all ten channels — the measurements themselves show the roll-off, matching a
        tripod set of the same install to within a decibel. There was no way to say so: the
        workaround was to open a NEW round on the same version and close it with a reason saying
        nothing was measured in it, which makes "capture round" mean two different things and
        misleads the next reader in a second way.

        No state is written — a closed round is not in the slice. The correction is a
        `capture_protective` event carrying the round's id, so `protective_record_for`, which
        replays those events in order, picks it up as the last word on that channel; and it carries
        `amends` plus the required `reason`, so a reader sees a correction rather than a record
        that was always this way.
        """
        reason = str(reason or "").strip()
        if not reason:
            raise ProcessError(
                "an amendment needs a reason — it is a correction of something already read by "
                "somebody, and a correction with no why is indistinguishable from a second opinion")
        capture_id = str(capture_id).strip()
        known = {r["id"] for r in self.capture_rounds()}
        if capture_id not in known:
            raise ProcessError(
                f"no capture round {capture_id!r} in this project's journal"
                + (f" (rounds: {', '.join(sorted(known))})" if known else " (no rounds at all)"))
        source = _protective_source(source)
        self._append(EV_CAPTURE_PROTECTIVE, capture=capture_id, channel=str(channel).strip(),
                     legs=legs, source=source, amends=capture_id, reason=reason)
        return {"capture": capture_id, "channel": channel, "legs": legs, "reason": reason}

    @_locked
    def set_knobs(self, controls):
        """The hardware controls as they stood for THIS round: `{name: position}`.

        On the ROUND, like the protective record and for the same reason: one set of knob positions
        covers one pass, and the round already carries the phase and the ledger version a reader
        needs. `project.json.hardware.controls` holds where a knob stands TODAY (SCR-017); this
        holds where it stood when these sweeps were taken, which is the only thing that makes two
        series comparable -- or tells a reader they are not (hub RES-007).

        Positions are stored verbatim, as the device shows them ("4/4", "-4", "ON"): what a step
        is worth in dB is a different fact, with a different provenance, and it lives in
        `project.json.hardware.control_mapping`.
        """
        if not isinstance(controls, dict) or not controls:
            raise ProcessError("a knob record needs {name: position} -- an empty record says "
                               "nothing, and nobody having said is what it would look like")
        state, round_ = self._require_capture()
        clean = {str(k).strip(): (v if isinstance(v, (int, float)) else str(v).strip())
                 for k, v in controls.items() if str(k).strip()}
        round_.setdefault("knobs", {}).update(clean)
        self._write(state)
        self._append(EV_CAPTURE_KNOBS, capture=round_["id"], knobs=clean,
                     phase=round_["phase"], version=round_["version"])
        return round_

    @_locked
    def amend_knobs(self, capture_id, controls, reason):
        """Record the knobs for a CLOSED round, visibly as a correction (#56 item 9).

        `capture-close` warns that no knobs were recorded, and by then the round is closed: the sub remote's 7/12
        on `_50` was known and on record in a decision, and `verify_prediction` still refused the series,
        because the one field it reads could not be written. Same shape as `amend_protective`: an event on the
        round's id, carrying `amends` and the required reason; `knobs_for` replays it."""
        reason = str(reason or "").strip()
        if not reason:
            raise ProcessError("an amendment needs a reason -- it corrects a round somebody may already have read")
        if not isinstance(controls, dict) or not controls:
            raise ProcessError("a knob record needs {name: position}")
        capture_id = str(capture_id).strip()
        known = {r["id"] for r in self.capture_rounds()}
        if capture_id not in known:
            raise ProcessError(f"no capture round {capture_id!r} in this project's journal"
                               + (f" (rounds: {', '.join(sorted(known))})" if known else " (no rounds at all)"))
        clean = {str(k).strip(): (v if isinstance(v, (int, float)) else str(v).strip())
                 for k, v in controls.items() if str(k).strip()}
        self._append(EV_CAPTURE_KNOBS, capture=capture_id, knobs=clean, amends=capture_id, reason=reason)
        return {"capture": capture_id, "knobs": clean, "reason": reason}

    AMP_READ_AS = ("said", "measured")

    @_locked
    def record_amp_gain(self, changes, read_as="said", note=None, amends=None):
        """The user turned an amplifier gain: `{channel: dB}`. Returns the record, with `open_round` when a round
        was open (its titles before this are at the old gain, so the re-measure belongs to a new series).

        `read_as` says where the number came from: `said` -- his estimate off the knob, which an amplifier does not
        calibrate -- or `measured`, the channel's solo after against before, same DSP state and position. A
        measured value for a said change is recorded with `amends=<id>` and replaces its dB."""
        if read_as not in self.AMP_READ_AS:
            raise ProcessError(f"read_as is one of {', '.join(self.AMP_READ_AS)}, not {read_as!r}")
        clean = {}
        for code, db in (changes or {}).items():
            code = str(code).strip()
            try:
                db = float(str(db).replace("dB", "").strip())
            except ValueError:
                raise ProcessError(f"{code}: {db!r} is not a number of dB") from None
            if not code or db == 0:
                raise ProcessError(f"{code or '?'}: an amp change needs a channel and a non-zero dB")
            clean[code] = round(db, 2)
        if not clean:
            raise ProcessError("an amp change needs at least one CHANNEL=dB (sw=+3)")
        known = [e.get("id") for e in self._events(kinds=(EV_AMP_GAIN,))]
        if amends and amends not in known:
            raise ProcessError(f"no amp change {amends!r} on record" + (f" (on record: {', '.join(known)})" if known else ""))
        change_id = f"amp-{len(known) + 1}"
        live = self.load(strict=True).get("capture") or {}
        open_round = live.get("id") if live and not live.get("closed") else None
        self._append(EV_AMP_GAIN, id=change_id, channels=clean, read_as=read_as, note=note, amends=amends,
                     open_round=open_round)
        return {"id": change_id, "channels": clean, "read_as": read_as, "amends": amends, "open_round": open_round}

    def amp_changes(self):
        """Every amp change on record, oldest first, with a later `amends` folded into the change it corrects."""
        out, by_id = [], {}
        for pos, e in enumerate(self._events()):
            if e.get("type") != EV_AMP_GAIN:
                continue
            if e.get("amends") in by_id:
                target = by_id[e["amends"]]
                target.update(channels=dict(e.get("channels") or {}), read_as=e.get("read_as"),
                              amended_by=e.get("id"))
                continue
            rec = {"id": e.get("id"), "at": e.get("at"), "pos": pos, "channels": dict(e.get("channels") or {}),
                   "read_as": e.get("read_as"), "note": e.get("note")}
            by_id[rec["id"]] = rec
            out.append(rec)
        return out

    def amp_gain_between(self, version_a, version_b):
        """`{channel: dB}` the amplifiers moved between series `_<a>` and `_<b>` (b later: positive is louder at b).

        A series is placed in the journal by the round it was issued in; a version with no round cannot be
        placed, and says so with None rather than with `{}`, which would read "nothing moved"."""
        key = self._version_key
        events = self._events()
        issued = {}
        for pos, e in enumerate(events):
            if e.get("type") == EV_CAPTURE_ISSUED:
                issued[e.get("capture")] = pos

        def place(version):
            v = key(version)
            ids = [r["id"] for r in self.capture_rounds()
                   if key(r["version"]) == v or any(key(t) == v for t in r.get("title_versions") or [])]
            return max((issued[i] for i in ids if i in issued), default=None)

        pa, pb = place(version_a), place(version_b)
        if pa is None or pb is None:
            return None
        lo, hi, sign = (pa, pb, 1.0) if pa <= pb else (pb, pa, -1.0)
        total = {}
        for ch in self.amp_changes():
            if lo < ch["pos"] < hi:
                for code, db in ch["channels"].items():
                    total[code] = round(total.get(code, 0.0) + sign * float(db), 2)
        return total

    def under_for(self, version):
        """The ledger version series `_<version>` was taken under (#57 P0), or None when no round says."""
        key = self._version_key
        version = key(version)
        found = None
        for r in self.capture_rounds():
            if key(r["version"]) == version or any(key(v) == version for v in r.get("title_versions") or []):
                found = r.get("under") or found
        # The live round is read strictly (#134, batch 2's re-review, Out of Scope 3): a state that cannot be read was
        # an empty one, and predict then read a series taken under a version "as it is" -- the chain applied twice.
        live = (self._read_state() or {}).get("capture") or {}
        if key(live.get("version")) == version and live.get("under"):
            found = live["under"]
        return found

    def knobs_for(self, version):
        """The knob positions recorded for the round the `_<version>` titles were taken in, or None.

        `None` is "nobody recorded the knobs", never "the knobs were at zero" -- and a reader that
        compares two series must treat it as the refusal it is (`verify_prediction`).
        """
        key = self._version_key
        version = key(version)
        matches = {r["id"] for r in self.capture_rounds()
                   if key(r["version"]) == version
                   or any(key(v) == version for v in r["title_versions"])}
        rounds, order = {}, []
        for event in self._events(kinds=(EV_CAPTURE_ISSUED, EV_CAPTURE_KNOBS)):
            cid = event.get("capture")
            if cid not in matches:
                continue
            if event.get("type") == EV_CAPTURE_ISSUED:
                rounds[cid] = {"series": cid, "phase": event.get("phase"),
                               "version": str(event.get("version")), "knobs": {}}
                order.append(cid)
            elif cid in rounds:
                rounds[cid]["knobs"].update(event.get("knobs") or {})
        for cid in reversed(order):
            if rounds[cid]["knobs"]:
                return rounds[cid]
        live = (self._read_state() or {}).get("capture") or {}      # strictly, as `under_for` (Out of Scope 3)
        if live.get("knobs") and key(live.get("version")) == version:
            return {"series": live["id"], "phase": live.get("phase"),
                    "version": str(live.get("version")), "knobs": dict(live["knobs"])}
        return None

    def protective_record(self, state=None):
        """The open round's protective record, in the shape `protective.legs_of` reads.

        `{"series": <round id>, "phase": ..., "channels": {...}}`. `None` when no round is open --
        which a caller must not read as "there was no protection", only as "there is no round to
        ask about".
        """
        round_ = (state or self.load()).get("capture")
        if not round_:
            return None
        return {"series": round_["id"], "id": round_["id"], "phase": round_.get("phase"),
                "version": round_.get("version"),
                "channels": dict(round_.get("protective") or {}),
                # WHO answered, per channel (S-036). A reader that wants only the legs ignores it;
                # `protective.should_de_embed` does not, because a bulk `default` is a question.
                "sources": dict(round_.get("protective_source") or {}),
                "amended": {}}

    @staticmethod
    def _version_key(v):
        # `_01` and `_1` are one series number (`naming.parse_name` says the same): REW
        # titles are typed by hand and zero-padding is common, and a string compare here would
        # make a recorded round invisible to the solos it was recorded for.
        v = str(v).strip()
        return int(v) if v.isdigit() else v

    @staticmethod
    def _title_version(title):
        """The `_N` of a measurement title (`m-L_49 (sw)` -> `49`), or None -- as `naming.parse_name`
        reads it, and never by a pattern of this module's own. A second pattern here did not know
        what follows the method (`c_49 (sw) x0`, `r-L_17 (sw) noXO`), so a whole solo set read as
        version-unknown while naming accepted every title of it (skill #34)."""
        naming = _load_naming()
        parsed = naming.parse_name(str(title)) if naming is not None else None
        return parsed.get("version") if parsed else None

    def capture_rounds(self):
        """Every round ever opened, oldest first: id, the version it was keyed by, its phase, and
        the `_N` versions of the titles it expected or took. What a lookup failure lists."""
        rounds, order = {}, []
        for event in self._events(kinds=(EV_CAPTURE_ISSUED, EV_CAPTURE_TAKEN)):
            cid = event.get("capture")
            if event.get("type") == EV_CAPTURE_ISSUED:
                rounds[cid] = {"id": cid, "version": str(event.get("version")),
                               "phase": event.get("phase"), "titles": list(event.get("expected") or [])}
                order.append(cid)
            elif cid in rounds and event.get("title"):
                rounds[cid]["titles"].append(event["title"])
        out = []
        for cid in order:
            r = rounds[cid]
            seen = []
            for t in r["titles"]:
                v = self._title_version(t)
                if v is not None and v not in seen:
                    seen.append(v)
            r["title_versions"] = seen
            out.append(r)
        return out

    def _titles_on_record(self, state):
        """Every title a round of this project took, as REW may hold it (#134, R47a): what `capture-import <N>` with no
        titles passes over. Four sources, each for what the others miss: the journal's `capture_taken` (a superseded
        typo too -- REW may still hold it, and it is this project's trace, not a capture to import); a closed round's
        `taken` (what the read against REW added, with no `capture_taken` of its own); REW's own spelling of a title
        that read matched (`capture_reconciled`'s `renames`); and the open round's `taken` rows in `state`."""
        titles = set()
        for event in self._events(kinds=(EV_CAPTURE_TAKEN, EV_CAPTURE_CLOSED, EV_CAPTURE_RECONCILED)):
            if event.get("title"):
                titles.add(str(event["title"]))
            titles.update(str(t) for t in event.get("taken") or [])
            titles.update(str(t) for t in (event.get("renames") or {}))
        titles.update(str(t) for t in ((state.get("capture") or {}).get("taken") or {}))
        return titles

    def protective_record_for(self, version):
        """The protective record of the round the solos `<ch>_<version> (sw)` were taken in.

        Replayed from the journal rather than read from the state slice, because the slice only
        holds the OPEN round and the solos a joint decision reads (`<ch>_1 (sw)`) are usually from
        a round closed sessions ago. Two rounds match: the LAST one wins, since a retake supersedes
        what it retook. `None` when no round matches -- which a caller must not read as "nothing
        was in the chain", only as "nobody recorded a round" (and, since 2026-08-25, must REFUSE on
        when it was told a round exists).

        A round matches by EITHER key it carries: the `version` it was opened with, OR the `_N` of
        any title it expected or took. The two are different numbers in real projects -- the tune
        session opened `capture-start v_001 "m-L_49 (sw)" ...` (ledger version `v_001`, captures
        `_49`), and every reader asked for `_49` and got nothing; the exporter then wrote
        `protectiveHighPass: null` for a fully recorded round, and the junction phase carried a
        67-degree protective filter nobody could see. The titles were on the round the whole time.
        """
        key = self._version_key
        version = key(version)
        matches = {r["id"] for r in self.capture_rounds()
                   if key(r["version"]) == version
                   or any(key(v) == version for v in r["title_versions"])}
        rounds, order = {}, []
        for event in self._events(kinds=(EV_CAPTURE_ISSUED, EV_CAPTURE_PROTECTIVE)):
            cid = event.get("capture")
            if cid not in matches:
                continue
            if event.get("type") == EV_CAPTURE_ISSUED:
                rounds[cid] = {"series": cid, "id": cid, "phase": event.get("phase"),
                               "version": str(event.get("version")), "channels": {},
                               "sources": {}, "amended": {}}
                order.append(cid)
            elif cid in rounds and event.get("channel"):
                channel = event["channel"]
                rounds[cid]["channels"][channel] = event.get("legs")
                rounds[cid]["sources"][channel] = event.get("source") or "user"
                # An amendment is the last word on that channel AND says so: a correction read as
                # if the record had always said this is a second way to mislead the next reader.
                if event.get("amends"):
                    rounds[cid]["amended"][channel] = event.get("reason") or ""
        if not order:
            # The open round, read strictly (Out of Scope 3): read as empty, a state that cannot be read was "no round",
            # and a solo was read as configured. `protective_record()` itself stays a screen's lenient read.
            state = self._read_state()
            live = self.protective_record(state) if state else None
            return live if live and key(live.get("version")) == version else None
        return rounds[order[-1]]

    def protective_by_channel(self):
        """`{channel: {"legs", "round", "version", "source"}}`: for EACH channel, the newest round in which a protective
        filter was recorded in its chain (the Arbiter, 2026-09-23). The front may be taken raw in one round and the
        centre raw in another, so "the last round" alone loses one of them; a record of OFF (nothing in the chain) is
        not a protective filter and does not hide an older one. Within a round, an amendment is the last word."""
        issued = [r["id"] for r in self.capture_rounds()]
        per_round = {}
        for event in self._events(kinds=(EV_CAPTURE_PROTECTIVE,)):
            if event.get("channel"):
                per_round.setdefault(event.get("capture"), {})[event["channel"]] = event
        out = {}
        for cid in reversed(issued):
            for channel, event in (per_round.get(cid) or {}).items():
                legs = event.get("legs")
                if channel in out or not legs or str(legs).upper() == "OFF":
                    continue
                version = next((r["version"] for r in self.capture_rounds() if r["id"] == cid), None)
                out[channel] = {"legs": legs, "round": cid, "version": version,
                                "source": event.get("source") or "user"}
        return out

    # -- listening verdicts (Phase 4) --
    @_locked
    def record_listening_verdict(self, pairs, text=None, route=None, ledger_version=None, note=None):
        """Bank what the Arbiter heard: `pairs` = [(track_id, characteristic_id, "ok"|"bad"), ...]
        as ticked, `text` = their own words after editing (the two are kept apart on purpose -- the
        text may drift from the ticks, and the record must not pretend they are one).

        `ledger_version` is what they were listening to; the caller (a front-end, the session) passes
        the ledger HEAD it has -- a version typed by hand is the number people get wrong, so a
        front-end should pass what it read, never what it remembers. Ids are validated against the
        vocabulary (`listening.py`), so a typo is refused now, not found in a filter a month later.
        """
        listening = _load_rew_tool_module("listening")
        if listening is None:
            raise ProcessError("cannot load rew_tool/listening.py from this checkout -- the ids of a "
                               "verdict are validated against it, and an unvalidated id is a typo "
                               "found a month later in a filter")
        pairs = [tuple(p) for p in (pairs or [])]
        if not pairs and not (text or "").strip():
            raise ProcessError("a listening verdict needs at least one pair (track:characteristic:ok|bad) "
                               "or some text -- an empty verdict records nothing")
        ch = listening.characteristics()
        tr = listening.tracks()
        clean = []
        for item in pairs:
            if len(item) != 3:
                raise ProcessError(f"a pair is track:characteristic:ok|bad, got {item!r}")
            track, cid, verdict = item
            verdict = str(verdict).lower()
            if verdict in ("🟢", "✓", "pass", "good", "yes"):
                verdict = "ok"
            if verdict in ("❌", "✗", "fail", "no"):
                verdict = "bad"
            if verdict not in ("ok", "bad"):
                raise ProcessError(f"verdict must be ok or bad, got {item[2]!r}")
            if track not in tr:
                raise ProcessError(f"unknown track id {track!r} -- the ids are in test-tracks.md")
            if cid not in ch:
                raise ProcessError(f"unknown characteristic id {cid!r} -- the ids are in "
                                   f"listening-cheat-sheet.md")
            clean.append({"track": track, "characteristic": cid, "verdict": verdict})
        state = self.load(strict=True)
        entry = {
            "at": _now(),
            "phase": state.get("active_phase"),
            "route": route,
            "ledger_version": str(ledger_version) if ledger_version is not None else None,
            "pairs": clean,
            "text": (text or "").strip() or None,
            "note": note,
        }
        self._append(EV_LISTENING_VERDICT, **entry)
        return entry

    def listening_verdicts(self, track=None, characteristic=None, ledger_version=None):
        """The protocol, filtered: every verdict entry oldest-first, optionally only those that
        mention `track` / `characteristic` / were heard at `ledger_version`. This is how one looks
        back -- `bad` at v_003, `ok` at v_005, and the ledger diff between them says what changed."""
        out = []
        for e in self._events(kinds=(EV_LISTENING_VERDICT,)):
            pairs = e.get("pairs") or []
            if track and not any(p.get("track") == track for p in pairs):
                continue
            if characteristic and not any(p.get("characteristic") == characteristic for p in pairs):
                continue
            if ledger_version is not None and str(e.get("ledger_version")) != str(ledger_version):
                continue
            out.append(e)
        return out

    def banked_ear_lines(self, ledger_version=None):
        """The lines a ledger snapshot banks at the technical lock, derived from the journal: one
        per pair, `[v_004] CarMus#07 c09 ok -- <text>`. A snapshot copies these in ADDITION to what it
        already holds; hand-written lines in older projects are never overwritten."""
        lines = []
        for e in self.listening_verdicts(ledger_version=ledger_version):
            stamp = e.get("ledger_version") or "?"
            for p in e.get("pairs") or []:
                line = f"[{stamp}] {p['track']} {p['characteristic']} {p['verdict']}"
                if e.get("text"):
                    line += f" -- {e['text']}"
                lines.append(line)
        return lines

    @_locked
    def supersede_capture(self, title, corrected_to, reason=None):
        """A capture was recorded under the wrong title; the right one replaces it (S-039).

        A ghost `r-R_1 (se)` sat in a round after the typo had been fixed in REW, and there was no
        move that could say so: `record_capture` and `skip_capture` are all a round has, so the only
        states were «taken» and «never mentioned», and a typo became permanent evidence of a
        measurement that does not exist.

        The plan's steps solved this and solved it well — `skip_step` keeps the step in the plan,
        dimmed, never removed (SCR-004) — so this is the same move: the mistyped row STAYS, marked
        `superseded_by` with the title it was corrected to, and the correct title is recorded in the
        same breath. Nothing is deleted, because a round that quietly loses a row is a round nobody
        can audit; and `_outstanding` stops counting the ghost as a capture that exists.
        """
        state, round_ = self._require_capture()
        title = str(title).strip()
        corrected_to = str(corrected_to).strip()
        if not title or not corrected_to:
            raise ProcessError("superseding a capture needs the wrong title AND the right one")
        if title == corrected_to:
            raise ProcessError(
                f"{title!r} is corrected to itself — nothing to supersede. If the title is right and "
                "the measurement is not, re-take it: a second `capture-taken` under the same title "
                "updates the row.")
        taken = round_.get("taken") or {}
        if title not in taken:
            raise ProcessError(
                f"round {round_.get('id')} never took {title!r}"
                + (f" (it took: {', '.join(sorted(taken))})" if taken else " (it has taken nothing)")
                + ". Superseding is for a row that EXISTS and is wrong; a title nobody recorded is "
                  "recorded, not corrected.")
        entry = dict(taken[title])
        entry["superseded_by"] = corrected_to
        if reason:
            entry["reason"] = str(reason).strip()
        round_["taken"][title] = entry
        self._write(state)
        self._append(EV_CAPTURE_SUPERSEDED, capture=round_["id"], title=title,
                     corrected_to=corrected_to, reason=reason, version=round_["version"])
        # The corrected title is a capture like any other -- same event, same `planned` test.
        return self.record_capture(corrected_to)

    @_locked
    def skip_capture(self, title, reason):
        """A capture deliberately NOT taken, and why.

        Skipped and not-yet-taken rendered identically before this, so a tuner who decided a
        capture was unnecessary had no way to say so and the next session proposed it again.
        A reason is required for the same reason evidence is: a decision with no record is a
        decision that has to be made again.
        """
        state, round_ = self._require_capture()
        title, reason = str(title).strip(), str(reason or "").strip()
        if not reason:
            raise ProcessError(f"skipping {title!r} needs a reason -- it is a decision, not a gap")
        # `planned` for the same reason `record_capture` carries it (TCC-022): `expected[]` is not
        # a closed set, so a reader of a round cannot assume everything in `skipped` was ever asked
        # for. Four rear titles were skipped into rounds that never expected them, and a skip of a
        # title that was never expected used to vanish from `contract.py`'s report entirely --
        # neither taken, nor missing, nor listed as skipped.
        planned = title in round_["expected"]
        round_["skipped"][title] = {"at": _now(), "reason": reason, "planned": planned}
        self._write(state)
        self._append(EV_CAPTURE_SKIPPED, capture=round_["id"], title=title, reason=reason,
                     planned=planned)
        return round_

    def _load_verifier(self):
        """`verify.py` from the same checkout, by path — same reason `_load_naming` does it. None when
        it cannot be loaded: unavailable arithmetic is "cannot tell", never "bad"."""
        return _load_sibling("verify.py")

    def check_captures(self, titles=None, verifier=None, session=False, round_id=None):
        """Run the skill's own verdict over the open round and record it (SCR-040).

        The arithmetic lives in `verify.py` and is called here rather than reimplemented by a
        front-end: two implementations of "is this curve usable" would drift, and the one that
        drifts is the one nobody runs standalone.

        Each verdict pins REW's `uuid`. The title is not identity -- re-take `sw_1 (sw)` and the
        name is unchanged while the data is not, so a verdict keyed by title would outlive the
        graph it judged. A measurement REW no longer holds records no uuid and reads as not ok.

        **A check reads; it does not take** (#134, audit T-1). Every title's verdict goes into the
        round's `checks` (`{title: verified}`), `exists` as the check said it: True or False. A
        `taken` row is created only for a title REW HOLDS (the rule `capture-close` closes by, skill
        #77) -- one REW holds more than once too, `ambiguous` on its verdict (H I-8) -- and a row
        already there gets the new verdict. A check used to create a `taken` row for every title it
        was handed, so a title nobody had measured stood as a capture the round took, outstanding
        nowhere. And REW not answering is no verdict at all: when any title went unanswered
        (`reachable` False) this raises `RewUnavailableError` (exit 69) before anything is written.
        Nor is a list of REW's nobody read (`exists` None: REW answered it with an error or with
        something it cannot read, or its address is none): `ProcessError`, exit 1, nothing written
        (H I-6) -- it was recorded as REW's verdict on every title.

        `session=True` adds the whole-session probe (Phase 0.6, `verify.session_report`) and
        records it on the round as `session` -- the ctl1->ctl3 drift is the DRIFT RECORD the
        capture sheet asks for, and it lives with the round it measured.

        REW is read with the project's lock free (#141, J2b): the verdicts, the profile's rate and the session probe
        are worked out on a strict read taken without the hold -- REW may take seconds a title -- and then merged,
        under it, into the state as it is THEN, by title: a writer that wrote meanwhile keeps its change. The round
        must still be the one the check was asked of, open: closed or replaced while REW was read, it is refused and
        nothing is written -- its verdicts would land on a round that did not ask for them. A folder that is no
        project's is refused first, before REW is read (#141, R46). `round_id`, given, is the round the caller read
        (`capture-close`, R7): another open by this check's own read is refused the same way. Either refusal is
        `round_moved` on its class, which `capture-close` stops at.
        """
        self._require_home("check_captures")
        self._ready_to_hold()
        round_ = self._require_capture(round_id)[1]
        verifier = self._load_verifier() if verifier is None else verifier
        if verifier is None:
            # With the reason (H 12): what to install, or which file to mend, is in it.
            raise ProcessError(
                f"verify.py could not be loaded{_load_failure('verify.py')} — cannot check captures. "
                "The curves are still there; this is the checker, not the data."
            )
        wanted = [str(t) for t in (titles or round_.get("expected") or [])]
        if not wanted:
            raise ProcessError("this round expects no captures — nothing to check")
        verdicts = verifier.verify(wanted)
        # REW not answering is no verdict on any title (#134): refused before anything is written, so the round and
        # the journal stay as they were and the check is run again once REW is up. What to do next is the caller's to
        # say: `capture-check` says "run it again", `capture-close` closes the round, unchecked.
        down = next((v for v in verdicts if v.get("reachable") is False), None)
        if down is not None:
            raise RewUnavailableError(
                f"REW did not answer ({(down.get('issues') or ['no answer'])[0]}) -- nothing was recorded")
        # Nor is REW's list unread (`exists` null): REW answered it with an error or with something it cannot read, or
        # was never asked -- its address no address (H I-6, H I-5). Every title was recorded as REW's verdict, `bad` in
        # a `capture_verified` and over a verdict already on a taken row. Refused, exit 1, with what was said; a bug in
        # that read never comes back as a verdict (`verify` raises it).
        unread = next((v for v in verdicts if v.get("exists") is None), None)
        if unread is not None:
            raise ProcessError(f"REW's measurement list was not read ({(unread.get('issues') or ['no answer'])[0]}) "
                               "-- nothing was recorded")
        checked = []                                # (title, verified) in REW's order: merged under the hold, below
        for verdict in verdicts:
            title = verdict["name"]
            exists = verdict.get("exists")
            exists = None if exists is None else bool(exists)   # None: REW's list was not read -- never "missing"
            verified = {
                "ok": bool(verdict.get("valid")),
                "exists": exists,
                # False for a capture the check does not apply to (an RTA): not bad, not good, and
                # not a reason to hold a step (skill #29). Dropped here, it read as "bad" below.
                "applicable": verdict.get("applicable", True) is not False,
                "uuid": (verdict.get("stats") or {}).get("uuid"),
                "at": _now(),
                "issues": list(verdict.get("issues") or []),
            }
            if verdict.get("ambiguous"):
                verified["ambiguous"] = verdict["ambiguous"]   # REW holds it more than once (H I-8): rename it
            checked.append((title, verified))
        # The capture rate vs the DSP's PROCESSING rate -- said ONCE per check, never a failure
        # (the user's ruling, 2026-08-25): a UMIK-1 captures at 48k under a 96k Helix, and if
        # capturing at the processing rate is impossible, we work with what there is. What must
        # never happen silently is the two being confused -- delays in samples derive from the
        # PROCESSING rate regardless of what the microphone recorded at.
        #
        # The rate is read by the one rule the settings sheet and the model read it by (`load_profile`, then
        # `stated_rate_hz`; the final review's I2). A profile that cannot be read, or a rate stated that is no rate,
        # is said in the note with its file and repair, never a failure: it was a plain `json.load` read leniently,
        # so a text rate exited 70 at the note's `:g`, `true` was noted as 1 Hz, and a cut or BOM'd profile said
        # nothing. No profile at all, or no rate stated in it, is no note, as before.
        rate_note, proc_rate = None, None
        capture_rates = sorted({v["stats"]["capture_rate_hz"] for v in verdicts
                                if v.get("stats", {}).get("capture_rate_hz")})
        if capture_rates:
            captured = "/".join(str(r) for r in capture_rates)
            module = _load_dsp_profile_module()
            if module is not None:
                path = os.path.join(self.project_dir, "dsp_profile.json")
                try:
                    proc_rate = module.stated_rate_hz(module.load_profile(path), path, self.project_dir)
                except FileNotFoundError:
                    proc_rate = None
                except Exception as exc:  # noqa: BLE001 -- matched by its attribute below; anything else still raises
                    if not getattr(type(exc), "is_unreadable", False):
                        raise
                    rate_note = f"captured at {captured} Hz; the DSP's processing rate NOT READ -- {exc}"
            if proc_rate and any(r != proc_rate for r in capture_rates):
                rate_note = (f"captured at {captured} Hz; the DSP "
                             f"processes at {proc_rate:g} Hz -- fine, working with it. Delays in "
                             f"samples derive from the PROCESSING rate; the capture rate stays with "
                             f"the measurement")
        session_probe = None
        if session and hasattr(verifier, "session_report"):
            probe = verifier.session_report(verdicts, processing_rate_hz=proc_rate if capture_rates else None)
            session_probe = {"at": _now(), "spread": probe["spread"], "drift": probe["drift"],
                             "capture_rates_hz": probe["capture_rates_hz"], "rows": probe["rows"]}
        with _hold(self.project_dir):
            state = self.load(strict=True)
            live = state.get("capture") or {}
            if live.get("id") != round_["id"] or live.get("closed"):
                raise _RoundMoved(f"round {round_['id']} was closed or replaced while REW was read -- nothing was "
                                  "written; run capture-check again", round_["id"],
                                  None if live.get("closed") else live.get("id"))
            taken, checks = live.setdefault("taken", {}), live.setdefault("checks", {})
            for title, verified in checked:
                checks[title] = dict(verified)          # every title checked, held or not (T-1)
                if title in taken:
                    taken[title]["verified"] = verified
                elif verified["exists"] is True:        # taken only when REW holds it (#77) -- never invented
                    taken[title] = {"at": _now(), "planned": title in live.get("expected", []), "verified": verified}
            if session_probe is not None:
                live["session"] = session_probe
            self._write(state)
            self._append(
                EV_CAPTURE_VERIFIED,
                capture=live["id"],
                step=live.get("step"),
                ok=sorted(v["name"] for v in verdicts if v.get("valid")),
                bad=sorted(v["name"] for v in verdicts
                           if not v.get("valid") and v.get("applicable", True) is not False),
                not_applicable=sorted(v["name"] for v in verdicts if v.get("applicable", True) is False),
                rate_note=rate_note,
            )
        # Told AFTER the record is on disk, never before -- issue #21. This print used to sit
        # where `rate_note` is computed, and on a cp1252 console the warning glyph raised
        # `UnicodeEncodeError` between the verdicts and `_write`: the gate ran, the result was
        # thrown away, and TCC reported `recorded: false`. `console.install()` keeps that from
        # raising at all now; the ORDER is what makes it not matter if something else ever does.
        # And the note only fires when the rates differ -- so the gate was reliable right up to
        # the moment it had something to say.
        if rate_note:
            print(f"  ⚠ {rate_note}")
        return live

    def unusable_captures(self, state=None):
        """Expected captures of the open round that are missing, unchecked, or checked and bad.

        The list a step's own gate reads: "done" means every capture it asked for came back AND
        passed, so an unchecked capture counts against it exactly as a failed one does.
        """
        state = state or self.load()
        round_ = state.get("capture") or {}
        if not round_ or round_.get("closed"):
            return []
        out = []
        for title in round_.get("expected", []):
            if title in (round_.get("skipped") or {}):
                continue  # a decision, and decisions are recorded, not re-litigated
            # A superseded row is a typo's trace, never the capture (N17): it counted here as taken -- and as usable
            # when it had been checked under the wrong title.
            entry = (round_.get("taken") or {}).get(title) if _is_taken(round_, title) else None
            verified = (entry or {}).get("verified") or {}
            if verified.get("applicable") is False:
                continue  # checked, and the check does not apply to it (an RTA): not unusable (#29)
            if not entry or not verified.get("ok"):
                out.append(title)
        return out

    @_locked
    def close_capture(self, reason=None, round_id=None):
        """Close the open round. What is neither taken nor skipped stays that way, on the record.

        The state is written first, the close's event after it (#141, J2b; W-8's review): the event went first, and a
        state write a holder refused said "it is as it was" over a journal that said closed -- the retry closed the
        round there a second time. `round_id`, given, is the round the caller read: `capture-close` reads it before
        REW, then takes the lock three times -- the reconcile, the checks, the close -- and another writer may close or
        replace the round between them (R7). Another round open, or none, the close is refused, naming both, nothing
        written: it closed the round open by then, one that verb never read against REW nor checked."""
        state, round_ = self._require_capture(round_id)
        event = self._close_capture(state, round_, reason=reason)
        self._write(state)
        self._append(EV_CAPTURE_CLOSED, **event)
        return round_

    def capture_outstanding(self, state=None):
        """Expected captures of the OPEN round that are neither taken nor skipped."""
        state = state or self.load()
        round_ = state.get("capture") or {}
        if not round_ or round_.get("closed"):
            return []
        return _outstanding(round_)

    def _require_capture(self, round_id=None):
        """`(state, its open round)`, read strictly: every caller writes (#136, R25). `round_id`, given, is the round
        the caller read before (`capture-close`, #141, R7): another open now, or none, is refused naming both --
        another writer closed or replaced it since -- and nothing is written."""
        state = self.load(strict=True)  # every caller writes (#136, R25)
        round_ = state.get("capture")
        if round_id is not None and (not round_ or round_.get("id") != round_id or round_.get("closed")):
            now = round_["id"] if round_ and not round_.get("closed") else None
            raise _RoundMoved(f"round {round_id} was closed or replaced after capture-close read it "
                              f"({f'{now} is the open round now' if now else 'no round is open now'}) -- nothing was "
                              "written", round_id, now)
        if not round_ or round_.get("closed"):
            raise ProcessError(
                "no capture round is open: `capture-start <version> [expected ...]` first. "
                "A round says which pass these measurements belong to -- without one they are "
                "loose titles that only REW remembers."
            )
        return state, round_

    def _close_capture(self, state, round_, reason=None):
        """Mark `round_` closed in `state` and return its `capture_round_closed` event's fields. The caller writes the
        state, then appends the event (#141, J2b): the close is in the journal only once it is in the state."""
        # Worked out BEFORE the round is marked closed: `capture_outstanding` answers about the
        # open round, and it is the closing event that most needs the answer.
        outstanding = _outstanding(round_)
        round_["closed"] = _now()
        round_["closed_reason"] = reason
        # What the closing was CHECKED against (skill #77): REW's list, through `reconcile_captures`, or nothing --
        # a round closed on a session's word alone says so, because its taken/missing are then only what was typed.
        rec = round_.get("reconciled") or {}
        round_["closed_against"] = ({"rew": True, "missing": rec.get("missing") or [],
                                     "extra": rec.get("extra") or [], "renames": rec.get("renames") or {}}
                                    if rec.get("rew") else {"rew": False})
        return dict(
            capture=round_["id"],
            version=round_["version"],
            taken=sorted(t for t in round_.get("taken", {}) if _is_taken(round_, t)),   # never a superseded row (N17)
            skipped=sorted(round_.get("skipped", {})),
            # Named rather than left to be worked out: a round that ends with expected captures
            # neither taken nor skipped is the shape план-факт exists to show.
            outstanding=outstanding,
            outstanding_optional=_outstanding_optional(round_),
            rew_checked=bool(rec.get("rew")),
            # A round with no knob record closes anyway -- refusing would strand a session mid-car
            # -- but it closes SAYING so, at the one moment the answer is still in the room. The
            # knobs are the part of the setup that lives outside every file, so a reader months
            # later has no way to recover them (hub RES-007).
            knobs=dict(round_.get("knobs") or {}),
            reason=reason,
        )

    @_locked
    def record_decision(self, question, answer, step=None, phase=None, invalidates=None):
        """The Arbiter answered something, recorded as the answer rather than as prose about it.

        `invalidates` has the same shape as `config_change.impact` on purpose: a ruling that
        supersedes a measurement ("the 48 kHz baseline no longer counts") should be legible to the
        same reader that handles a config change. A ruling is NOT a config change, though, and
        forcing it into that event would lie about where the fact came from.

        Nothing in the current slice changes. An answer is history: what it constrains shows up as
        the target, the plan step or the config change it leads to.
        """
        question, answer = str(question).strip(), str(answer).strip()
        if not question or not answer:
            raise ProcessError("a decision needs both the question and the answer as given")
        self._append(
            EV_USER_DECISION,
            question=question,
            answer=answer,
            step=step,
            phase=str(phase) if phase is not None else self.load(strict=True).get("active_phase"),
            invalidates=invalidates,
        )
        return {"question": question, "answer": answer, "step": step}

    @_locked
    def record_session(self, harness, model, resumed=False, phase=None):
        """A working session began. Not a transition -- nothing in the current slice changes.

        This is the anchor план-факт was missing at the start: a journal whose first entry is a
        `step_done` cannot distinguish a session that recorded nothing from a session that never
        happened. Written by the front-end, which is the only party that knows a session was
        attached at all.
        """
        self._append(
            EV_SESSION_STARTED,
            harness=harness,
            model=model,
            resumed=bool(resumed),
            phase=str(phase) if phase is not None else self.load(strict=True).get("active_phase"),
        )
        return {"harness": harness, "model": model, "resumed": bool(resumed)}

    def last_session_event(self):
        """The journal's last `session_started` / `session_closed` / `session_reopened`, or None."""
        seen = self._events(kinds=SESSION_EVENTS)
        return seen[-1] if seen else None

    def session_closed(self):
        """Is the session closed? True only when the last session event is `session_closed`.

        The one place this module reads the close, so a reopening (S-084) is read wherever the
        question is asked: a `session_reopened` after the close means open again, and so does a
        `session_started` after it.
        """
        return (self.last_session_event() or {}).get("type") == EV_SESSION_CLOSED

    @_locked
    def reopen_session(self, reason):
        """Take a close back: `session_reopened` with its reason, after the close (S-084, hub #227).

        A session reconciling state ran `session-close` to look, and with nothing open it wrote the
        close. The journal is append-only, so the close is not removed: the reopening follows it, and
        both stay legible. Refused with no reason -- a reopening with no why reads like a close nobody
        meant -- and refused unless the last session event IS a close, because there is nothing else to
        take back.
        """
        reason = str(reason or "").strip()
        if not reason:
            raise ProcessError(
                "a reopening needs its reason: `session-reopen <reason>` (e.g. «session-close was run as "
                "a check»). The close stays in the journal either way, and a reopening with no why reads "
                "like a close nobody meant")
        last = self.last_session_event()
        if (last or {}).get("type") != EV_SESSION_CLOSED:
            raise ProcessError(
                "nothing to reopen: "
                + (f"the journal's last session event is `{last['type']}` ({last.get('at', '?')}), not "
                   "`session_closed` — the session is open" if last
                   else "the journal records no session event at all, so no close to take back")
                + ". To ask what is open without closing anything: `session-close --check`")
        return self._append(EV_SESSION_REOPENED, reason=reason, closed_at=last.get("at"))

    def open_work(self, state=None):
        """What this project still has OPEN — the list a session owes before it stops.

        `session_start` had no pair. Stopping was a pause in a conversation rather than an event
        with a closing order, and the cost lands on the NEXT session, which resumes and reconciles
        against things that were never written (autosound-hub HUB-023, from the hub, on the owner's
        ask that the skill understand "добраніч" the way the hub does).

        Reports, never closes. Each of these is a decision with an argument the machine does not
        have — which evidence closes a step, whether a capture was skipped or is still owed, what
        the Arbiter actually ruled — so naming them is this function's whole job. It adds no
        carrier: the round, the steps and the session anchor are already here, and the fifth item
        below deliberately lives elsewhere and is only pointed at.
        """
        state = state or self.load()
        round_ = state.get("capture")
        # A CLOSED round stays in `state["capture"]` carrying `closed` -- the slice holds the last
        # round, not only a live one, the same way it holds the active phase. `capture_outstanding`
        # and `_require_capture` both test that flag; testing only for presence (the first draft of
        # this) reports every finished round as open forever, which would train a reader to ignore
        # the line. Caught by the probe, not by reading.
        if round_ and round_.get("closed"):
            round_ = None
        steps = [s for s in state.get("plan", []) if s.get("status") == STEP_IN_PROGRESS]
        out = {"capture_round": None, "steps_in_progress": [], "phase": state.get("active_phase")}
        if round_:
            out["capture_round"] = {
                "id": round_.get("id"), "version": round_.get("version"),
                "outstanding": _outstanding(round_),
                "taken": sum(1 for t in round_.get("taken", {}) if _is_taken(round_, t)),   # N17
                "skipped": len(round_.get("skipped", {})),
            }
        for entry in steps:
            out["steps_in_progress"].append({
                "id": entry.get("id"), "name": entry.get("name"),
                "attempt": entry.get("attempt", 1),
                "covers": entry.get("covers", []),
            })
        return out

    def handoff(self):
        """Is everything the NEXT session needs on disk — and the line to say when it is (S-044).

        The Arbiter asked what to do about clearing the chat at a phase boundary («раніше ми
        обговорювали, що добре кожну фазу починати з чистої сесії — що можемо зробити?») and there
        was no procedure. A session can neither restart itself nor `/clear`, and the half that makes
        clearing SAFE was missing entirely: nothing checked that what the next session needs is
        written before the chat holding the only copy is thrown away.

        So this REFUSES, naming what is missing, and the session keeps working instead. When it
        passes it prints the resume line — what he says next, and what must stay open — so the
        instruction is not improvised a second time.

        `{"ok", "missing": [...], "phase", "resume", "warnings": [...]}`. It checks and writes nothing:
        which evidence closes a step is a decision, the same split `session-close` already has.
        `warnings` never moves `ok`: a ▶️ CONTINUE block that names a HEAD the ledger is not at (S-084)
        is prose to bring up to date, not state the next session lacks.
        """
        state = self.load(strict=True)  # a verdict never stands on a read that failed (#136)
        missing = []
        phase = state.get("active_phase")
        if not phase:
            missing.append("no phase is recorded — `enter-phase <N>` is the entry condition, and a "
                           "session that never opened one leaves the next with nothing to resume")
        round_ = state.get("capture") or {}
        if round_ and not round_.get("closed"):
            miss = _outstanding(round_)
            missing.append(
                f"capture round {round_.get('id')} is OPEN at {round_.get('version')}"
                + (f", {len(miss)} still expected ({', '.join(miss)})" if miss else "")
                + " — an open round's status lives in REW's measurement list and goes when REW does: "
                  "`capture-skip <title> <reason>` for each one not coming, then `capture-close`")
        unfinished = [e for e in self.plan_for(phase, state)
                      if e.get("status") in (STEP_TODO, STEP_IN_PROGRESS)]
        if unfinished:
            missing.append(
                "plan steps of phase " + str(phase) + " are neither closed nor decided against: "
                + ", ".join(f"{e['id']} {e.get('name') or ''} [{e['status']}]" for e in unfinished)
                + " — `done <id> <evidence that RESOLVES>`, `skip <id> <reason>`, or `block <id> "
                  "<reason>`. A step left `todo` across a clear is a step the next session cannot "
                  "tell from one nobody ever thought of")
        unbacked = self.unbacked_done_steps(state)
        if unbacked:
            unloaded = _naming_unloaded()            # the grammar's absence, not the prose's (the final review's M2)
            missing.append(
                "done steps whose evidence resolves to nothing on disk: "
                + ", ".join(str(e.get("id")) for e in unbacked)
                + (f" — {unloaded}, so a step closed on one reads so here" if unloaded else
                   " — the chat is about to go, and prose that pointed at it goes with it"))
        if not _ledger_versions(self.project_dir):
            missing.append(
                "no ledger snapshot on disk (`state/<preset>/v_NNN.json`) — the next session reads "
                "the DSP state from there, and from nowhere else. `apply.propose` banks one")
        changelog = _continue_block(self.project_dir)
        log_path, _, log_why, mend = _changelog_read(self.project_dir)
        if log_why:
            # Said, not read as no changelog (H 15): "no opinion" passed the handoff over a block nobody could see. The
            # mend is the cause's (m2): a permission is not mended by closing an editor.
            missing.append(
                f"`{log_path}` {log_why} — its ▶️ CONTINUE block cannot be checked, and it is the human-readable "
                f"cross-check the next session reads beside the machine files: {mend}")
        elif changelog is not None and not changelog:
            missing.append(
                "`tuning-changelog` has no ▶️ CONTINUE block — it is the human-readable cross-check "
                "the next session reads beside the machine files, and the one a person opens first")
        drift = continue_head_drift(self.project_dir) if changelog else None
        warnings = [drift["warning"]] if drift else []
        resume = None
        if not missing:
            keep = ""
            last = state.get("capture") or {}
            if any(_is_taken(last, t) for t in last.get("taken") or {}):
                keep = (" Keep the REW session with this round's captures open — the titles are the "
                        "only identity they have.")
            resume = (f"State is on disk: phase {phase}, "
                      f"{len(self.plan_for(phase, state))} step(s) in its plan, ledger HEAD present. "
                      f"Clear the chat and say «продовжуй» in the new one.{keep}{_route_line(self.project_dir)}")
        return {"ok": not missing, "missing": missing, "phase": phase, "resume": resume, "warnings": warnings}

    @_locked
    def set_target(self, preset, curve):
        """The active target curve for a preset — a pointer, the curve itself lives elsewhere."""
        state = self.load(strict=True)
        state["targets"][preset] = curve
        self._write(state)
        self._append(EV_CONFIG_CHANGE, field="target", preset=preset, value=curve, impact="voicing")
        return state["targets"]

    # -- derived views --
    def plan_for(self, phase=None, state=None):
        """The plan steps belonging to one phase (default: the active one), in insertion order."""
        state = state or self.load()
        phase = str(phase) if phase is not None else state.get("active_phase")
        return [s for s in state.get("plan", []) if s.get("phase") == phase]

    def unevidenced_done_steps(self, state=None):
        """Done steps with nothing to point at — the drift check to run on resume."""
        state = state or self.load()
        return [s for s in state.get("plan", []) if s.get("status") == STEP_DONE and not s.get("evidence")]

    def unbacked_done_steps(self, state=None):
        """Done steps whose evidence resolves to nothing NOW.

        Distinct from having no evidence at all, and worth its own answer: `finish_step` refuses
        both, so a step here was either closed by an older writer, or closed against a file that
        has since been moved or deleted. A capture name is not judged -- only REW knows whether it
        holds one -- so this reports what the disk can actually contradict.
        """
        state = state or self.load()
        versions = _ledger_versions(self.project_dir)
        naming = _load_naming()
        out = []
        for step in state.get("plan", []):
            if step.get("status") != STEP_DONE or not step.get("evidence"):
                continue
            if not any(
                resolves(item, self.project_dir, versions, naming)
                for item in step.get("evidence", [])
            ):
                out.append(step)
        return out

    # -- internals --
    def _require(self, state, step_id):
        entry = self.step(state, step_id)
        if entry is None:
            raise ProcessError(f"no such step {step_id!r}")
        return entry

    def _write(self, state):
        """Write the state, once its guards pass. A move refused by a holder says "it is as it was" -- of the journal
        too: every transition writes its state before its events (#141, J2b). A round's close went to the journal
        first, and this write was told what had landed there (`landed`, part A's re-review, N-1); nothing lands before
        it now, so nothing is told."""
        state["updated"] = _now()
        validate(state)
        # Strictly first (#136, audit K-2): a file that is there and cannot be read is never replaced. Each transition
        # reads the state strictly itself (R25); this is the last line, for a file damaged between that read and this
        # write -- what the transition built is not put over it. Before #136 the transitions read through a lenient
        # `load()`, which gave the empty process for such a file, and this write put that -- no plan, no round -- over
        # the one on disk. `Unreadable` names the file and the repair; no file at all is a fresh project, and passes.
        # A state a newer method wrote there since the read is not written down to v3 either (audit T-21).
        self._refuse_newer(self._read_state())
        # The journal too, before the state (F M-7): every write here is followed by its event, and one refused after
        # the write left the change in the state with no line in the journal.
        self._require_journal()
        os.makedirs(self.dir, exist_ok=True)  # first real write is what creates `process/`
        # A temp of this writer's own, then one move (skill #135): a crash mid-write would otherwise leave truncated
        # JSON, and the next session would read an empty process and think nothing had happened; a fixed temp name
        # was shared by every writer of the file (audit T-8).
        io_ = _project_io()
        try:
            io_.atomic_write_json(self.state_path, state, indent=2, ensure_ascii=False, trailing_newline=True)
        except OSError as exc:
            # A refusal, exit 1, not a bug (H minor 2): on Windows a holder past the retries -- a sync client, a scanner
            # -- as the same hold is on the read. The move either lands or leaves the file whole, and no temp behind.
            raise ProcessError(f"{self.state_path} could not be written ({exc}) -- "
                               f"{io_.repair_for(exc, writing=True)}; it is as it was") from exc
        # Owed from here: the event that goes with this change (`_append` says it, if it cannot be appended).
        self._unjournaled = True

    def _require_home(self, verb):
        """Refuse a write into a process folder that is no project's, before anything is made (#141, W-8's R46): the
        writer lock's hold makes `.autosound/` in a project folder that is there, and the first write the process folder
        itself, so a mistyped path -- `<project>/process-typo` -- got a process of its own. `verb` names the writer
        asking: a method's name, or `enter-phase <N>`, `session-close` and `capture-close` for the command line's own.
        Two writers start a project where there is none yet.

        * the folder is there: nothing to check;
        * it is not, and is not called `process`: refused -- the method's process folder is called process;
        * it is not, is called `process`, and `project.json` stands beside it: the project's first process write;
        * it is not, is called `process`, and no `project.json` is beside it: `enter-phase -1`, the intake, starts a
          project there; `session-start` (`record_session`) does too where the project folder itself is there (R19):
          TCC's gate takes an empty folder and runs `session-start`, then `enter-phase -1`, in one `try`, so a refusal
          of the first skipped the second. Any other writer is refused, not a project yet -- and `session-start` on a
          project folder that is not there."""
        folder = os.path.abspath(self.dir)
        if os.path.isdir(folder):
            return
        if os.path.basename(folder) != "process":
            raise ProcessError(f"{folder} does not exist, and the method's process folder is called process -- a "
                               "mistyped path? nothing was written")
        if verb == "enter-phase -1" or os.path.isfile(os.path.join(self.project_dir, "project.json")):
            return
        if verb == "record_session" and os.path.isdir(self.project_dir):
            return
        raise ProcessError(f"{self.project_dir} holds no project.json: not a project yet -- the intake starts one with "
                           "enter-phase -1; nothing was written")

    def _ready_to_hold(self):
        """What a writer does with the project's lock still free, before it takes it (#141): reads the wait -- an
        `AUTOSOUND_LOCK_TIMEOUT_S` that is no number of seconds is a usage error (exit 2) before REW, git or `gh` is
        asked -- and asks git for the sha `_stamp` writes, once per writer, so that git never runs under the lock. A
        caller that takes the hold around this process's writes itself calls this first."""
        _write_lock().timeout_s()
        if getattr(self, "_sha", None) is None:
            self._sha = _writer_sha()

    def _last_written_by(self):
        """The sha in the last header event, or None when the journal carries no header at all.

        None is not `""`: a journal that has never recorded a writer must get a header even when
        the writer cannot be told, otherwise "asked, could not be told" and "never asked" are the
        same silence. Read strictly (`_events`): a header lost to a skipped line would be written twice.
        """
        seen = self._events(kinds=(EV_WRITTEN_BY,))
        return seen[-1].get("skill_sha", "") if seen else None

    def _stamp(self):
        """Write the header event when this run's writer is not the one the journal last recorded.

        Not once, at creation. The journal grows across runs, and a header written when the file
        was born says only which method STARTED it — while the thing that has to be answerable is
        "were these two runs made by the same method?" (autosound-hub HUB-002). So the header sits
        at the top of each run's slice, and only where the sha actually CHANGES: a car tuned over a
        weekend on one version carries one header, not one line per event.

        The sha is read from this checkout, never accepted from a caller — `provenance` says why.
        A `provenance` that will not load stamps `""`, the same as a machine with no git: the
        journal records that the question was asked and had no answer, rather than losing the
        event it was riding on.
        """
        if self._stamped:
            return
        # Asked before this writer's first hold (`_ready_to_hold`, #141); a caller that appends with no writer of
        # its own around the append is asked here.
        sha = getattr(self, "_sha", None)
        sha = _writer_sha() if sha is None else sha
        last = self._last_written_by()     # strict: a journal that cannot be read refuses here, and is asked again
        self._stamped = True  # decided once read: one attempt per run, whatever it finds
        if sha == last:
            return
        self._append(EV_WRITTEN_BY, skill_sha=sha)

    def _append(self, event_type, **payload):
        if event_type == EV_WRITTEN_BY:          # `_stamp`'s header: the `_append` it rides on says a refusal
            return self._append_event(event_type, payload)
        try:
            # Strictly first, as `_write` (#136): no event is appended beside a state that cannot be read, or that a
            # newer method wrote -- several carry what they read of it (the phase, the open round), and `project.py
            # record-change` and any other caller outside `_main` write through here.
            self._refuse_newer(self._read_state())
            self._stamp()
            event = self._append_event(event_type, payload)
        except Exception as exc:  # noqa: BLE001 -- matched below; anything else still raises as it was
            refusal = self._append_refused(event_type, payload, exc)
            if refusal is None:
                raise
            raise refusal from exc
        self._unjournaled = False
        return event

    def _append_event(self, event_type, payload):
        event = {"at": _now(), "type": event_type}
        event.update({k: v for k, v in payload.items() if v is not None})
        os.makedirs(self.dir, exist_ok=True)
        # After a torn last line the event starts on a fresh one instead of being glued to it and lost (audit T-14).
        _project_io().append_line(self.journal_path, json.dumps(event, ensure_ascii=False))
        return event

    def _append_refused(self, event_type, payload, exc):
        """The refusal for an event that could not be appended, or None to let `exc` raise as it is (#134, F M-7).

        Only a file that could not be read or written is this one's to say -- an exception with `is_unreadable` (the
        journal or the state held, a permission, a line in another code page) or an `OSError` from the append itself
        (a read-only journal, a full disk). After a state write in this run (`_write`), it says what landed: the state
        holds the change, the journal has no line for it, and the line to append once the journal can be written --
        nothing replays it. It was a bare `PermissionError`, exit 70, "a bug". With no state write before it, an
        `OSError` is said as the event not recorded; an `Unreadable` raises as it is."""
        io_ = _project_io()
        unreadable = getattr(type(exc), "is_unreadable", False)
        if not (unreadable or isinstance(exc, OSError)):
            return None
        why = str(exc if unreadable else io_.cannot_append(self.journal_path, exc))     # one wording (m4)
        if getattr(self, "_unjournaled", False):
            # This line, and any the same write owes after it (`_owed_after`: a superseded round's close, then the new
            # round's own, #141): each is said, in order -- nothing replays one left out.
            owed = [(event_type, payload)] + list(getattr(self, "_owed_after", None) or [])
            lines = []
            for kind, fields in owed:
                event = {"at": _now(), "type": kind}
                event.update({k: v for k, v in fields.items() if v is not None})
                lines.append(json.dumps(event, ensure_ascii=False))
            if len(lines) == 1:
                return _StateWithoutItsEvent(
                    f"{self.state_path} is written, but its journal line is not: {why}. The state holds this change "
                    f"and the journal has no `{event_type}` event for it, and nothing replays it: once the journal can "
                    f"be written, append this line to {self.journal_path}: {lines[0]}")
            return _StateWithoutItsEvent(
                f"{self.state_path} is written, but its journal lines are not: {why}. The state holds this change and "
                f"the journal has no {' or '.join(f'`{kind}`' for kind, _ in owed)} event for it, and nothing replays "
                f"them: once the journal can be written, append these lines to {self.journal_path}, in order:\n"
                + "\n".join(lines))
        if unreadable:
            return None
        return ProcessError(f"{why}; the `{event_type}` event was not recorded")


# --------------------------------------------------------------------------- CLI
# The skill drives its tooling from Bash (SKILL.md's guardrails run `python rew_tool/...`), so the
# writer needs a command line, not just an importable class -- same reason `state.py` has one.

_USAGE = """usage: process.py <process-dir> <command> [args]
       process.py <process-dir> <command> --help    that command's lines below; nothing is read or written
       A command takes the flags written beside it, as `--flag value` or `--flag=value`, the value as it
       stands (never another of its flags, -h or --help); any other flag, a flag with no value after it, one
       of its flags with the two hyphens autocorrected to a dash (`—origin`) and fewer arguments than its
       line names are a usage error (exit 2), never a title or a reason -- but `skip <id>` with neither a
       reason nor --superseded-by, which `skip` refuses itself (exit 1). Text that only begins with `--` and
       holds a space (`--bass hums`, `--bass=45 Hz`) is a word, unless the name before its `=` is a flag of
       the command (`--invalidates=w-L_1 (sw)`).

  show                                  print the current state as JSON
  plan [phase]                          print the plan (default: active phase)
  enter-phase <phase>                   make a phase current (-1..5)
  add-step <id> <name> [--project] [--covers a.b,c.d]
                                        add a plan step (--project = situational insert).
                                         --covers names the facts it closes (dotted paths, as
                                         `open-questions` prints them); the name then carries the
                                         first three and `+N` — generated, because a count is not
                                         a subject (S-031)
  start <id>                            begin/re-begin a step (a re-begin is attempt N+1)
  done <id> <evidence> [evidence ...]    mark done; evidence is REQUIRED and must RESOLVE
                                         (a capture name `c_1 (rta)`, a ledger `v_003` that
                                          exists, or a project file that exists)
  skip <id> <reason ...> [--superseded-by ID]   supersede a step (kept visible, never deleted).
                                         The reason is REQUIRED: a skip with no why is
                                         indistinguishable from a step forgotten, and the next
                                         session proposes it again
  block <id> <reason>                   mark blocked
  reviewer <vendor> <model> [step] [--review PATH] [--mode clipboard]
                                        record a reviewer call and WHERE its text is
  target <preset> <curve>               set a preset's active target curve
  session-start <harness> <model> [resumed]   a working session began (written by the front-end)
  session-close                               STOPPING: what is still open — the capture round,
                                              any step left in progress — and what else stopping
                                              owes that this file does not hold. Reports, never
                                              closes: which evidence ends a step is a decision.
                                              Exits non-zero while anything is open, so "we
                                              stopped" cannot be said over an open round.
                                              With nothing open it RECORDS session_closed:
                                              this is the stop itself, not a look
  session-close --check                       the same report and exit code, and writes nothing:
                                              the read-only question, for reconciling state
  session-reopen <reason>                     take a mistaken close back: session_reopened with its
                                              reason. Only right after session_closed; the close
                                              stays in the journal and the session reads as open
  decision <question> <answer> [step] [--invalidates X]   what the Arbiter ruled, as itself
  capture-start <version> [title ...] [--plan] [--phase N] [--start sw|rta] [--optional <title>]...
      [--step ID] [--origin <project>:<their _N>]
      [--under v_NNN] [--level "-25 dB rel. max"] [--level-read-as "7 lamps"]
                                        --plan: the list from the method's plan for the phase (skill #77),
                                        titles beside it added in their place; --start: the setup the car is
                                        in (else the last capture's, skill #78); --optional: on the list,
                                        no gap when left (skill #80). Prints the list, column by column,
                                        then `plan: <path>`, its file in docs/plans/ (one not written:
                                        a `note:` on stderr, why -- the round is open either way)
                                        --under: the ledger version the series is taken under (#57 P0;
                                        recorded only when given); --level: the level as a quantity (S-026)
                                        open a capture round; titles = what was
                                         asked for, --step binds it to the plan step it satisfies
  capture-check [title ...] [--session]  run the verdict over the round and record it (SCR-040);
                                         --session adds the whole-session probe (levels side by
                                         side, loudest/quietest, ctl1->ctl3 drift) and records it
  capture-taken <title>                 a measurement came back (unplanned ones are flagged)
  capture-import <N> [title ...] --bind MOD=v_NNN [--bind =v_NNN] --knob NAME=POS [...] [--late "why"]
                                        register what REW holds as this project's rounds, one per DSP
                                        state; unbound modifiers and missing knobs refuse (#58 P3).
                                        No titles: what REW holds of series N and this project has not
                                        on record yet -- none held refuses, all on record is "nothing new"
  capture-knobs --amend <cap_id> --reason "..." <NAME>=<POS> [...]
                                        the knobs of a CLOSED round, as a correction (#56 item 9)
  amp-gain <CH>=<dB> [...] [--measured] [--amends amp-N] [--note "..."]
                                        the user turned an amplifier gain (sw=+3): levels live in the DSP,
                                        an amp moves only when its plus runs out. Said by default;
                                        --measured when read off the re-measured solo
  amp-changes                           the amp changes on record, oldest first
  capture-knobs <NAME>=<POS> [...]      the hardware controls as they stood for THIS round
                                        (SubRC=4/4 RealCenter=ON): a fact about the SERIES, so two
                                        series taken at different positions can be told apart
                                        instead of the difference landing in a calibration offset
  capture-protective <ch> OFF [--source user|front_end|default]
                                        this round was RAW for that channel: what was in the
  capture-protective <ch> --hp 100 LR 24    chain and is NOT part of the tune, so it can be taken
      [--lp 4000 BW 36]                 back out before a phase decision. OFF = leave it alone,
  capture-protective --amend <cap_id> --reason "..." <ch> OFF|--hp ...
                                        correct a CLOSED round's record, visibly as a correction
                                        (skill #48); the reason is required. --source says WHO
                                        answered: a bulk `default` is read as a QUESTION, not as
                                        an answer (S-036)
                                        which is an ANSWER and the default; not running this at
                                        all means the round measured the system as configured --
                                        and since 2026-09-06 the front-end always writes one of
                                        the two, so an absent record means this was not it
  listening-verdict --pair <track>:<char>:ok|bad [--pair ...] [--text "..."] [--ledger-version vN]
      [--route full] [--note ...]        what the Arbiter heard (Phase 4): the ticked pairs AND their
                                        own words, stamped with the ledger version listened to; ids
                                        are validated against listening-cheat-sheet / test-tracks
  listening-verdicts [--track ID] [--characteristic cNN] [--ledger-version vN] [--bank]
                                        look back: the verdicts, filtered; --bank prints the lines a
                                        snapshot banks at the lock (derived, additive)
  capture-supersede <wrong> <right> [reason]
                                        the capture was recorded under the wrong title: the row
                                        STAYS, dimmed, naming what it was corrected to, and the
                                        right title is recorded (S-039). Never deletion
  handoff [--json]                      is everything the NEXT session needs on disk? Prints the
                                        resume line when it is, names what is missing when it is
                                        not (exit 1), and writes nothing either way (S-044).
                                        Warns, never refuses, when the ▶️ CONTINUE block names a
                                        HEAD the ledger is not at (S-084).
                                        --json: {ok, missing, phase, resume, warnings, next_message}
  capture-skip <title> <reason>         deliberately NOT taken, and why
  capture-close [reason]                close the round; what is outstanding is named
                                        reads REW first (skill #77): held -> taken, extra of the series ->
                                        taken unplanned, absent -> left open; --no-rew closes on the record alone
  check                                 done steps with no evidence, and done steps whose
                                         evidence resolves to nothing on disk
  selftest                              this module's own gates, on a throwaway project

exit  0 done · 1 refused · 2 usage · 69 REW did not answer, nothing written
      · 70 unexpected error (a bug: the traceback is above it)
      · 75 project busy: another writer holds its lock, nothing written, safe to retry
           (capture-close stopped past its first hold says what had landed: its reconcile, maybe its checks)
"""

#: The verbs that only DISPLAY (#136, the read rule): they write nothing and show a `process-state.json` that cannot
#: be read as an empty process. Every other verb -- each that writes the state or the journal, each verdict, and
#: `show` -- reads the file strictly before it does anything, so a verb not listed here is strict.
_DISPLAY_VERBS = ("plan", "amp-changes", "listening-verdicts")

#: Every verb of the command line and the flags it takes (#134, N19) -- the flags `_main` reads, branch by branch. A
#: verb not here is unknown (exit 2); a flag its verb does not list is a usage error (exit 2) and never reaches it,
#: where it became a title, a reason or a piece of evidence. String literals on purpose: a front end finds a flag in
#: this file's text (TCC's N19), and `_check_unknown_flags` holds every `"--..."` the dispatcher reads to this table.
VERB_FLAGS = {
    "show": (),
    "plan": (),
    "enter-phase": (),
    "add-step": ("--project", "--covers"),
    "start": (),
    "done": (),
    "skip": ("--superseded-by",),
    "block": (),
    "reviewer": ("--review", "--mode"),
    "target": (),
    "decision": ("--invalidates",),
    "session-start": (),
    "session-close": ("--check",),
    "session-reopen": (),
    "capture-start": ("--origin", "--step", "--under", "--level", "--level-read-as", "--start", "--phase",
                      "--optional", "--plan"),
    "capture-check": ("--session",),
    "capture-taken": (),
    "capture-import": ("--bind", "--late", "--knob"),
    "amp-gain": ("--measured", "--amends", "--note"),
    "amp-changes": (),
    "capture-knobs": ("--amend", "--reason"),
    "capture-protective": ("--source", "--amend", "--reason", "--hp", "--lp"),
    "listening-verdict": ("--pair", "--text", "--route", "--ledger-version", "--note"),
    "listening-verdicts": ("--track", "--characteristic", "--ledger-version", "--bank"),
    "capture-supersede": (),
    "handoff": ("--json",),
    "capture-skip": (),
    "capture-close": ("--no-rew",),
    "check": (),
}

#: Whether each flag of `VERB_FLAGS` takes a value: the one table that says it (T m13, H 21), every flag in it once.
#: `_check_unknown_flags` holds it to `VERB_FLAGS` both ways, so a flag added there and not here turns the selftest
#: red -- `_args_checked` would read a valueless flag missing here as one that takes the next word for its value.
_FLAG_TAKES_VALUE = {
    "--project": False, "--covers": True, "--superseded-by": True, "--review": True, "--mode": True,
    "--invalidates": True, "--check": False, "--origin": True, "--step": True, "--under": True, "--level": True,
    "--level-read-as": True, "--start": True, "--phase": True, "--optional": True, "--plan": False, "--session": False,
    "--bind": True, "--late": True, "--knob": True, "--measured": False, "--amends": True, "--note": True,
    "--amend": True, "--reason": True, "--source": True, "--hp": True, "--lp": True, "--pair": True, "--text": True,
    "--route": True, "--ledger-version": True, "--track": True, "--characteristic": True, "--bank": False,
    "--json": False, "--no-rew": False,
}

#: The flags that take no value, read off `_FLAG_TAKES_VALUE`. `--flag=value` is read as `--flag value`, and for one of
#: these the value would reach the verb on its own -- a title to check, a reason, a step's id -- so `=` on one is a
#: usage error too.
_FLAGS_WITHOUT_VALUE = tuple(flag for flag, takes in _FLAG_TAKES_VALUE.items() if not takes)

#: What asks for help: the whole text after the folder (`process.py <dir> --help`), a verb's own lines right after
#: the verb (`<verb> --help`). `-h` is the same.
_HELP = ("--help", "-h")

#: The flags whose values their verb parses itself: capture-protective's filter legs, three values each (`--hp 100 LR
#: 24`), read by the branch, not by `_args_checked`. One with nothing after it is the verb's to answer -- "--hp needs
#: three values", exit 1 -- where any other value-taking flag left last is a usage error (#134, R40).
_LEG_FLAGS = {"capture-protective": ("--hp", "--lp")}

#: The arguments each verb cannot run without, by the names its lines in `_USAGE` give them (#134, R36). Fewer is a
#: usage error, exit 2, naming them, before the project is touched: it raised IndexError -- "list index out of
#: range", exit 1 like a refusal with no reason. Every verb has its row, so `_check_too_few_arguments` finds a verb
#: added to `_main` without one. `skip` needs a reason OR `--superseded-by`, which no count can say: `skip_step`
#: refuses a skip with neither (exit 1, its own words).
_VERB_ARGS = {
    "show": (),
    "plan": (),
    "enter-phase": ("<phase>",),
    "add-step": ("<id>", "<name>"),
    "start": ("<id>",),
    "done": ("<id>", "<evidence>"),
    "skip": ("<id>",),
    "block": ("<id>", "<reason>"),
    "reviewer": ("<vendor>", "<model>"),
    "target": ("<preset>", "<curve>"),
    "decision": ("<question>", "<answer>"),
    "session-start": ("<harness>", "<model>"),
    "session-close": (),
    "session-reopen": ("<reason>",),
    "capture-start": ("<version>",),
    "capture-check": (),
    "capture-taken": ("<title>",),
    "capture-import": ("<N>",),
    "amp-gain": ("<CH>=<dB>",),
    "amp-changes": (),
    "capture-knobs": ("<NAME>=<POS>",),
    "capture-protective": ("<ch>",),
    "listening-verdict": (),
    "listening-verdicts": (),
    "capture-supersede": ("<wrong>", "<right>"),
    "handoff": (),
    "capture-skip": ("<title>", "<reason>"),
    "capture-close": (),
    "check": (),
}


def _flag_shaped(token, known=()):
    """A token the command line reads as a flag (#134, R35, M-b): `--`, an ASCII letter, and no whitespace anywhere --
    `--origin`, `--hp=100` -- or, holding whitespace after its `=`, one whose name before the `=` is one of the verb's
    own flags (`known`): TCC's `--invalidates=w-L_1 (sw)`, the value the value's, spaces and all. A bare `--`, a
    negative number (`-25`, `--5`) and a word stay arguments, and so does text that only begins with two dashes:
    `--бас гуде`, `--bass hums`, `-- note`, `--bass=45 Hz hums?` -- the last was refused as a flag `decision` does not
    take, when it was the Arbiter's question. A flag's name is never Cyrillic and never holds a space; the Arbiter's
    own words, typed into TCC, can be both."""
    name = token.partition("=")[0]
    if not (len(name) > 2 and name.startswith("--") and name[2].isascii() and name[2].isalpha()):
        return False
    return not any(ch.isspace() for ch in token) or name in known


def _asks_help(token):
    """`--help` (`--help=...` too) or `-h`: a question about the command line, wherever it stands."""
    return token == "-h" or token.partition("=")[0] == "--help"


#: The dashes an editor's autocorrect makes of two hyphens: an em dash and an en dash (#134, H 20).
_DASHES = "\u2014\u2013"


def _refuse_autocorrected(cmd, token, known):
    """`UsageError` for a word that is one of the verb's flags with its two hyphens autocorrected into a dash (#134,
    H 20): it starts with an em or an en dash and names, past its dashes and before any `=`, one of the verb's own
    flags or `--help` (`—origin`, `–origin=other:49`, `–-optional`). Read as a word it became a title or a reason,
    and the flag was never set: `capture-start 1 a —origin other:49` opened a round expecting `—origin` and
    `other:49`. Any other word passes, a dash before it or not."""
    if not token[:1] or token[0] not in _DASHES:
        return
    name = token.partition("=")[0]
    meant = "--" + name.lstrip(_DASHES + "-")
    if meant in known or meant == "--help":
        raise UsageError(f"{cmd}: {name} looks like {meant} with its dashes autocorrected; type two hyphens")


def _args_checked(cmd, args):
    """`args` as the verb `cmd` reads them (#134, N19, R35, R37, R40, R41). A flag's value passes as it is, whatever
    it looks like: after `=` (`--flag=value` becomes `--flag`, `value`), or as the next word when the flag takes one
    (`--text --loud`) -- unless, in either form, it is one of the verb's own flags, `-h` and `--help` among them, or
    there is nothing after the flag: then the value is missing. capture-protective's legs (`_LEG_FLAGS`) with nothing
    after them are the verb's to answer. A missing value, a flag-shaped token (`_flag_shaped`) the verb does not
    take, one of its flags with the hyphens autocorrected to a dash (`_refuse_autocorrected`, where a flag stands: a
    value is taken as it stands), `=` on a flag that takes no value, and `--help` or `-h` anywhere else here (they
    are asked right after the verb, `_main`) raise `UsageError`, exit 2. A bare `--` and the words pass. The words of
    a refusal never contain `usage: process.py`: TCC reads that as "the method is too old"."""
    known = VERB_FLAGS.get(cmd, ())
    out, i = [], 0
    while i < len(args):
        token = args[i]
        i += 1
        if _asks_help(token):
            word = token.partition("=")[0]
            raise UsageError(f"{word} is asked right after the command: process.py <process-dir> {cmd} {word}")
        if not _flag_shaped(token, known):
            _refuse_autocorrected(cmd, token, known)
            out.append(token)
            continue
        flag, eq, value = token.partition("=")
        if flag not in known:
            raise UsageError(f"{cmd} does not take {flag}"
                             + (f" -- it takes {', '.join(known)}" if known else " -- it takes no flags"))
        if eq and flag in _FLAGS_WITHOUT_VALUE:
            raise UsageError(f"{flag} takes no value ({token!r}): `{flag}` alone")
        out.append(flag)
        if flag in _FLAGS_WITHOUT_VALUE:
            continue
        if eq:
            given = value
        elif i < len(args):
            given = args[i]
            i += 1
        elif flag in _LEG_FLAGS.get(cmd, ()):
            continue            # a leg with nothing after it: its verb says what is missing (R40)
        else:
            # Nothing after it (R40): before the verb runs. Taken as unset, `decision <q> <a> --invalidates` recorded
            # the decision without its link, and `capture-import <N> --bind` went on to ask REW.
            raise UsageError(f"{cmd}: {flag} needs a value")
        # One test for both forms (R35, R37): a value that is one of the verb's own flags is no value -- and `-h` and
        # `--help` are among every verb's flags (R41). A branch that scans for its flags read `--note=--measured` as
        # `--measured`, and recorded no note.
        if _asks_help(given) or (_flag_shaped(given, known) and given.partition("=")[0] in known):
            raise UsageError(f"{cmd}: {flag} needs a value")
        out.append(given)
    return out


def _args_counted(cmd, args):
    """Refuses (`UsageError`, exit 2) fewer arguments than `_VERB_ARGS` names for `cmd`, naming them (#134, R36).
    `args` as `_args_checked` returns them: a flag of the verb and its value are not arguments, and a leg's values
    (`_LEG_FLAGS`, up to three, up to the next of the verb's flags) are the leg's (M-a). Counted as arguments, they
    let `capture-protective --hp 100 LR 24` run with no channel: the channel became `--hp`, and the verb answered
    "expected --hp or --lp ... got '100'", exit 1."""
    known, given, i = VERB_FLAGS.get(cmd, ()), 0, 0
    legs = _LEG_FLAGS.get(cmd, ())
    while i < len(args):
        if args[i] in legs:
            i += 1
            for _ in range(3):
                if i < len(args) and args[i] not in known:
                    i += 1
        elif args[i] in known:
            i += 1 if args[i] in _FLAGS_WITHOUT_VALUE else 2
        else:
            given += 1
            i += 1
    needs = _VERB_ARGS.get(cmd, ())
    if given < len(needs):
        raise UsageError(f"{cmd} needs {' '.join(needs)}: {given} of {len(needs)} given -- process.py <process-dir> "
                         f"{cmd} --help")


#: The filter types a protective leg can be (#134, R47b, R48): `dsp_math.MODELLABLE_FAMILIES` (the docs' "types
#: (LR/BW/BE)") and the Chebyshev, `CH`, recorded as typed -- it is what was in the chain: TCC's dialog offers it, a
#: Helix offers the family, and refusing it stopped the person recording the filter really there. `dsp_math` models no
#: Chebyshev. The selftest holds this to the modellable families and CH, so a family `dsp_math` comes to model is a
#: type a leg can carry.
_LEG_TYPES = ("LR", "BW", "BE", "CH")
#: Those the de-embedding can take back out: every leg type but the Chebyshev, which `protective.de_embed` refuses
#: (#134, R49, R52) -- the method never takes another family out in its place.
_MODELLED_LEG_TYPES = tuple(t for t in _LEG_TYPES if t != "CH")


def _leg(kind, values):
    """One filter leg of capture-protective, `{f, type, slope}`, from the values typed after `--hp` or `--lp` (#134, F
    I-1, T I1, H I-7, R47b, R48). A typed mistake is the verb's refusal, exit 1, in its words: a value missing --
    fewer than three, or a flag where a value stands (`--hp 100 LR --lp 4000 BW 36`) -- a frequency that is no number
    (`abc`, `100Hz`, `nan`) or not above 0, a type that is none of `_LEG_TYPES` (empty, `XX`; any letter case is the
    type), a slope that is no whole number (`24.5`) or not above 0. They reached `float()` and `int()` unguarded and
    exited 70, a bug's code, or were recorded; TCC sends a leg as the person typed it."""
    example = f"e.g. --{kind} 100 LR 24"
    if len(values) < 3 or any(_flag_shaped(v) for v in values):
        raise ProcessError(f"--{kind} needs three values: f type slope, {example}. "
                           "A leg missing any of them cannot be taken back out later")
    f, kind_of, slope = values
    try:
        f_hz = float(f)
    except ValueError:
        f_hz = math.nan
    if not math.isfinite(f_hz):
        raise ProcessError(f"--{kind}: {f!r} is not a number -- the frequency in Hz, {example}")
    if f_hz <= 0:
        raise ProcessError(f"--{kind}: {f!r} is not a frequency above 0 Hz, {example}")
    if kind_of.upper() not in _LEG_TYPES:
        raise ProcessError(f"--{kind}: {kind_of!r} is not a filter type: {', '.join(_LEG_TYPES[:-1])} or "
                           f"{_LEG_TYPES[-1]}, {example}")
    try:
        db_per_oct = int(slope)
    except ValueError:
        raise ProcessError(f"--{kind}: {slope!r} is not a whole number -- the slope in dB/oct, {example}") from None
    if db_per_oct <= 0:
        raise ProcessError(f"--{kind}: {slope!r} is not a slope above 0 dB/oct, {example}")
    return {"f": f_hz, "type": kind_of.upper(), "slope": db_per_oct}


def _verb_usage(verb):
    """`<verb> --help` (#138, I-15): every line of `_USAGE` that belongs to `verb` -- each entry it heads, which can
    lie apart in the text (`capture-knobs`, `session-close`), with the indented lines that continue it -- and the
    exit table, which every verb shares. It names the verb but never begins `usage: process.py`."""
    own, table, into = [], [], None
    for line in _USAGE.splitlines():
        if not line.startswith("   "):        # no continuation: an entry's head (two spaces), a blank, a header line
            words = line.split()
            into = (own if line.startswith("  ") and words[:1] == [verb]
                    else table if words[:1] == ["exit"] else None)
        if into is not None:
            into.append(line)
    return "\n".join(own + [""] + table)


def _close_stopped(exc, landed, missed):
    """`capture-close`'s own line, and its exit code, when a stage after its first is stopped (#141, R9; Task 2's
    review): another writer holds the project's lock past the wait (75), or closed or replaced the round (1). The
    reconcile has landed by then, and maybe the checks (`landed`); `missed` is what did not. Said so, with whether a
    retry is safe: write_lock's own line says "nothing was written", true at the first hold alone. None for anything
    else, and when nothing landed -- the exception says itself, truly."""
    if not landed:
        return None
    done = " and ".join(landed)
    if getattr(type(exc), "is_busy", False):
        safe = "the reconcile is" if len(landed) == 1 else "the reconcile and the checks are"
        return (f"busy: {getattr(exc, 'path', 'the project lock')} is held by another writer -- {done} landed; "
                f"{missed} did not; run capture-close again ({safe} safe to repeat)", EXIT_BUSY)
    if getattr(type(exc), "round_moved", False):
        now = getattr(exc, "now", None)
        return (f"error: round {getattr(exc, 'read', '?')} was closed or replaced by another writer while capture-close "
                f"ran ({f'{now} is the open round now' if now else 'no round is open now'}) -- {done} landed; {missed} "
                "did not", EXIT_NO)
    return None


def _seed_intake(root):
    """Write the files phase −1 is supposed to produce, so a fixture can get past its own gate.

    Deliberately built through the real writers rather than as literals: if `project.py` or
    `state.py` change what a valid file looks like, this fixture finds out at the same moment the
    rest of the skill does.
    """
    project_mod = _load_sibling("project.py")
    profile_mod = _load_sibling("dsp_profile.py")
    state_mod = _load_sibling("state/state.py")
    if not all((project_mod, profile_mod, state_mod)):
        return
    proj = project_mod.Project(root)
    proj.save({
        "schema_version": project_mod.SCHEMA_VERSION,
        "channels": [{"code": "w-L", "tier": "channels"}],
        "glossary": {"schema_version": 1, "channels": [{"code": "w-L", "active": True}]},
    })
    profile_mod.save_profile(os.path.join(root, "dsp_profile.json"), {"dsp_profile": {
        "name": "Fixture", "vendor": "Fixture", "dsp_processing_rate_hz": 96000,
        "delay": {"step_ms": 0.01}, "polarity": {"scope": []},
        "groups": [{"id": "physical_outputs", "label": "Outputs", "max_count": 2,
                    "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity"],
                    "crossover_filters": {"types": {"LR": {"orders_db_per_oct": [24]}}}}],
    }})
    history = state_mod.PresetHistory(os.path.join(root, "state"), "FULL", project_dir=root)
    history.snapshot({
        "preset": "FULL", "sample_rate": 96000,
        "channels": {"w-L": {"hp": None, "lp": None, "gain_db": 0.0, "ta_ms": 0.0,
                             "polarity": "NORM"}},
    }, note="fixture intake")


def _check_intake_gate_names_an_unreadable_project_json():
    """Leaving phase −1 over a `project.json` that is there and cannot be read is refused naming that file and its
    repair (#134, F M-5): the gate said "intake has not produced glossary.json (or project.json.glossary)" -- the
    glossary inside the file it could not read -- and sent the person to finish an intake already done. Refused before
    anything is written; a `project.json` that reads still passes."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_cut_project_")
    try:
        root = os.path.join(top, "p")
        os.makedirs(root)
        _seed_intake(root)
        p = Process(os.path.join(root, "process"))
        p.enter_phase("-1")
        path = os.path.join(root, "project.json")
        with open(path, "rb") as f:
            whole = f.read()
        with open(path, "wb") as f:
            f.write(whole[: len(whole) // 2])
        rc, said, kept = _gate_run(p.dir, ["enter-phase", "0"])
        last = (said.strip().splitlines() or [""])[-1]
        assert rc == 1 and kept and p.load()["active_phase"] == "-1", (rc, kept, last)
        assert last.startswith(f"error: phase 0 is not entered: {path} exists and cannot be read") \
            and "glossary" not in last, last
        with open(path, "wb") as f:
            f.write(whole)
        rc, said, _kept = _gate_run(p.dir, ["enter-phase", "0"])
        assert rc == 0 and p.load()["active_phase"] == "0", (rc, said[-300:])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_intake_gate_names_an_unreadable_glossary():
    """Leaving phase −1 over a standalone `glossary.json` that is there and cannot be read is refused naming that file
    and its repair (#134, batch 4's re-review N4 and Out of Scope 4): the check read it leniently, as no glossary,
    so the gate let phase 0 in beside `project.json`'s own glossary, or refused it as "not produced" without one.
    Refused before anything is written; the file whole again, the phase is entered."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_cut_glossary_")
    try:
        root = os.path.join(top, "p")
        os.makedirs(root)
        _seed_intake(root)
        p = Process(os.path.join(root, "process"))
        p.enter_phase("-1")
        path = os.path.join(root, "glossary.json")
        whole = json.dumps({"schema_version": 1, "channels": [{"code": "w-L", "active": True, "label": "Низ"}]},
                           ensure_ascii=False).encode("utf-8")
        with open(path, "wb") as f:
            f.write(whole[: whole.index("Низ".encode("utf-8")) + 1])         # inside `Н`: a write cut off
        rc, said, kept = _gate_run(p.dir, ["enter-phase", "0"])
        last = (said.strip().splitlines() or [""])[-1]
        assert rc == 1 and kept and p.load()["active_phase"] == "-1", (rc, kept, last)
        assert last.startswith(f"error: phase 0 is not entered: {path} ") and "checkout HEAD -- glossary.json" in last \
            and "not produced" not in last, last
        with open(path, "wb") as f:
            f.write(whole)
        rc, said, _kept = _gate_run(p.dir, ["enter-phase", "0"])
        assert rc == 0 and p.load()["active_phase"] == "0", (rc, said[-300:])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_plan_names_the_naming_load_error():
    """`capture-start --plan` over a `naming.py` that cannot be loaded says that, and why (#134, batch 4's re-review,
    Out of Scope 2; m4's form): it said "--plan needs the project's glossary", the load failure read as a glossary
    nobody wrote. Nothing is opened."""
    import shutil
    import tempfile
    global _load_naming
    real_naming = _load_naming
    top = tempfile.mkdtemp(prefix="autosound_process_plan_naming_")
    try:
        root = os.path.join(top, "p")
        os.makedirs(root)
        _seed_intake(root)
        p = Process(os.path.join(root, "process"))
        p.enter_phase("-1")

        def broken():
            _LOAD_FAILURES["naming.py"] = SyntaxError("invalid syntax (naming.py, line 3)")
            return None
        _load_naming = broken
        try:
            p.start_capture("55", plan=True, phase="0")
        except ProcessError as exc:
            said = str(exc)
        else:
            said = "went through"
        assert "naming.py" in said and "(SyntaxError: invalid syntax (naming.py, line 3))" in said \
            and "needs the project's glossary" not in said, said
        assert not p.load().get("capture"), "a round was opened"
    finally:
        _load_naming = real_naming
        _LOAD_FAILURES.pop("naming.py", None)
        shutil.rmtree(top, ignore_errors=True)


def _cut_glossary(root):
    """Write `<root>/glossary.json` cut inside a character (a write cut off); returns `(path, whole bytes)`."""
    path = os.path.join(root, "glossary.json")
    whole = json.dumps({"schema_version": 1, "channels": [{"code": "w-L", "active": True, "label": "Низ"}]},
                       ensure_ascii=False).encode("utf-8")
    with open(path, "wb") as f:
        f.write(whole[: whole.index("Низ".encode("utf-8")) + 1])            # inside `Н`
    return path, whole


def _check_phase1_gate_names_an_unreadable_glossary():
    """Leaving phase 0 over a standalone `glossary.json` that is there and cannot be read is refused naming that file
    and its repair (#134, batch 4's re-review I1): `contract.py check --phase0-gate` ended NOT READY over it and exited
    0. `enter-phase 1` reads the check's `unreadable` through the intake check, which runs on every move forward, so
    the gate and the move answer one rule. The flaw map here stands on a measurement and a target is recorded: the
    glossary is the one thing that stops it. Refused before anything is written; the file whole again, phase 1 is
    entered."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_phase1_cut_glossary_")
    try:
        root = os.path.join(top, "p")
        os.makedirs(root)
        _seed_intake(root)
        p = Process(os.path.join(root, "process"))
        p.enter_phase("-1")
        p.enter_phase("0")
        p.set_target("FULL", "EPY")
        pj = os.path.join(root, "project.json")
        with open(pj, encoding="utf-8") as f:
            data = json.load(f)
        data["acoustics"] = {"flaws": [{"f_hz": 150.0, "level_db": -9.0, "kind": "cabin_null", "action": "no_boost",
                                        "why": "a null", "evidence": ["w-L_01 (sw)"], "channels": ["w-L"],
                                        "at": "2026-01-01T00:00:00Z"}]}
        with open(pj, "w", encoding="utf-8") as f:
            json.dump(data, f)
        path, whole = _cut_glossary(root)
        rc, said, kept = _gate_run(p.dir, ["enter-phase", "1"])
        last = (said.strip().splitlines() or [""])[-1]
        assert rc == 1 and kept and p.load()["active_phase"] == "0", (rc, kept, last)
        assert last.startswith(f"error: phase 1 is not entered: {path} is cut off inside a character") \
            and "checkout HEAD -- glossary.json" in last, last
        with open(path, "wb") as f:
            f.write(whole)
        rc, said, _kept = _gate_run(p.dir, ["enter-phase", "1"])
        assert rc == 0 and p.load()["active_phase"] == "1", (rc, said[-300:])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_capture_verbs_read_the_glossary_strictly():
    """The capture verbs read the glossary as the method reads its files, strictly (#134, batch 4's re-review, Out of
    Scope 6): a `glossary.json` that is there and cannot be read refuses them naming the file and its repair,
    `error: <file> <reason> -- <repair>`, exit 1, nothing written. Read as no glossary, `capture-start --plan` said it
    "needs the project's glossary" over one cut after phase 0 was entered; `capture-start` opened its round, its
    titles placed by no codes; the close read the round against REW, and `capture-import` split its titles, with none.
    The file whole again, each goes through. (`Glossary.for_project` stays lenient by default: a screen's read.)"""
    import shutil
    import tempfile
    rew_api = _siblings().load("rew_api.py")
    real = rew_api.get_measurements
    top = tempfile.mkdtemp(prefix="autosound_capture_cut_glossary_")
    try:
        root = os.path.join(top, "p")
        os.makedirs(root)
        _seed_intake(root)
        p = Process(os.path.join(root, "process"))
        p.enter_phase("-1")
        p.enter_phase("0")
        path, whole = _cut_glossary(root)
        failures = []

        def refused(label, argv):
            rc, said, kept = _gate_run(p.dir, argv)
            last = (said.strip().splitlines() or [""])[-1]
            if rc != 1 or not kept or not last.startswith(f"error: {path} is cut off inside a character") \
                    or "checkout HEAD -- glossary.json" not in last or "needs the project's glossary" in said:
                failures.append(f"{label}: rc {rc!r}, kept {kept}, said {said.strip()[-300:]!r}")
        refused("capture-start --plan", ["capture-start", "55", "--plan"])
        refused("capture-start", ["capture-start", "55", "w-L_55 (sw)"])
        # A joint's title is split by the glossary's codes: with none, `w+m` read as a modifier no bind names.
        refused("capture-import", ["capture-import", "55", "w-L_55 (sw)", "L w+m_55 (sw)", "--bind", "=v_001",
                                   "--knob", "SubRC=4/4"])
        with open(path, "wb") as f:
            f.write(whole)
        rc, said, _kept = _gate_run(p.dir, ["capture-start", "55", "--plan"])
        if rc != 0 or not (p.load().get("capture") or {}).get("expected"):
            failures.append(f"capture-start --plan over the whole file: rc {rc!r}, said {said[-300:]!r}")
        # The close reads the open round against REW's list through the glossary (`reconcile_captures`).
        rew_api.get_measurements = lambda: {"1": {"title": "w-L_55 (sw)"}}
        _cut_glossary(root)
        refused("capture-close", ["capture-close"])
        if not p.load().get("capture") or p.load()["capture"].get("closed"):
            failures.append("capture-close over the cut file closed the round")
        assert not failures, "\n  ".join(["a capture verb over a glossary.json it cannot read:"] + failures)
    finally:
        rew_api.get_measurements = real
        shutil.rmtree(top, ignore_errors=True)


def _check_one_naming():
    sib = _siblings()
    assert _load_naming() is sib.load("naming.py")
    assert _load_sibling("contract.py") is _load_sibling("contract.py")


def _check_every_loader_shares():
    """Each loader here hands out THE module object `siblings` holds for its file (skill #137) -- none runs a fresh
    copy any more. Not None first: two Nones are `is` each other, and a loader that loads nothing would pass."""
    sib = _siblings()
    verifier = Process(os.path.join("never-written", "process"))._load_verifier()   # the constructor writes nothing
    for rel, got in (("contract.py", _load_sibling("contract.py")),
                     ("state/state.py", _load_sibling("state/state.py")),
                     ("dsp_profile.py", _load_dsp_profile_module()),
                     ("provenance.py", _load_rew_tool_module("provenance")),
                     ("write_lock.py", _write_lock()),
                     ("verify.py", verifier)):
        assert got is not None, f"{rel} did not load"
        assert got is sib.load(rel), f"{rel}: the loader ran a copy of its own"


def _check_load_sibling_reads_a_failure_as_none():
    """`_load_sibling` is None when a sibling cannot be loaded -- a file that is not there, or one that fails at import
    (verify.py needs numpy) -- and never raises (J1 review): its callers read None as "cannot tell", and a gate must
    not crash on it. Through `Process._load_verifier` too, the one a capture check calls. Not through `_load_naming`:
    that caches the None for the whole process."""
    import types

    def loaded(fn, *args):
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001 -- the contract under test is "None, never a raise"
            return f"raised {type(exc).__name__}: {exc}"

    got = loaded(_load_sibling, "no_such_module.py")
    assert got is None, f"a sibling that is not there: {got}"
    real = globals()["_siblings"]

    def failing(exc):
        def load(rel):
            raise exc
        return lambda: types.SimpleNamespace(load=load)
    try:
        for exc in (RuntimeError("verify.py fails at import"), ModuleNotFoundError("No module named 'numpy'")):
            globals()["_siblings"] = failing(exc)
            got = loaded(_load_sibling, "verify.py")
            assert got is None, f"{exc!r}: _load_sibling gave {got}"
            got = loaded(Process(os.path.join("never-written", "process"))._load_verifier)
            assert got is None, f"{exc!r}: Process._load_verifier gave {got}"
    finally:
        globals()["_siblings"] = real


def _check_verifier_load_error_named():
    """`verify.py could not be loaded` says why (#134, H 12): the load error's type and message -- numpy missing, a
    syntax error in the sibling -- as the phase gates name theirs. It said only that it could not, and the person was
    left to guess what to install. Exit 1, nothing written."""
    import shutil
    import tempfile
    real = globals()["_siblings"]
    top = tempfile.mkdtemp(prefix="autosound_process_verifier_")

    def siblings():
        sib = real()

        def load(rel):
            if rel == "verify.py":
                raise ModuleNotFoundError("No module named 'numpy'")
            return sib.load(rel)
        return type("S", (), {"load": staticmethod(load)})
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["a (sw)"])
        before = _project_bytes(d)
        globals()["_siblings"] = siblings
        try:
            rc, out, err = _run_main(["process.py", d, "capture-check"])
        finally:
            globals()["_siblings"] = real
        want = "error: verify.py could not be loaded (ModuleNotFoundError: No module named 'numpy')"
        assert rc == EXIT_NO and want in err and "Traceback" not in err, (rc, out, err[-300:])
        assert _project_bytes(d) == before, "a check that could not run wrote something"
    finally:
        globals()["_siblings"] = real
        shutil.rmtree(top, ignore_errors=True)


def _check_foreign_tmp_untouched():
    """Two writers never share a temp file (audit T-8): a `process-state.json.tmp` that is not ours stays as it is."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_tmp_")
    try:
        d = os.path.join(top, "process")
        os.makedirs(d)
        foreign = os.path.join(d, "process-state.json.tmp")
        with open(foreign, "wb") as f:
            f.write(b"someone else's half-written file")
        assert _main(["process.py", d, "enter-phase", "-1"]) == 0
        assert os.path.isfile(foreign), "the writer moved another writer's temp file over process-state.json"
        with open(foreign, "rb") as f:
            assert f.read() == b"someone else's half-written file", "the writer used a temp name another writer uses"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_state_bytes():
    """The same bytes as before the change: json.dumps(indent=2, ensure_ascii=False) and a final newline."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_bytes_")
    try:
        p = Process(os.path.join(top, "process"))
        p.enter_phase("-1")
        with open(p.state_path, encoding="utf-8") as f:
            text = f.read()
        assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_torn_journal_line():
    """A journal whose last line was cut keeps the NEXT event readable (audit T-14): the event used to be glued to the
    torn line, one line that does not parse, and skipped with it. The bytes stay the old append's -- each event
    `json.dumps(event, ensure_ascii=False)` and the platform's line ending -- with one line ending more after the torn
    line, and nothing else."""
    import contextlib
    import io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_torn_")
    real_sha = _writer_sha
    try:
        d = os.path.join(top, "process")
        os.makedirs(d)
        journal = os.path.join(d, "journal.jsonl")
        # The header names this run's checkout, so `_stamp` adds nothing: the decision is the next line written.
        head = json.dumps({"at": "2026-10-06T00:00:00+00:00", "type": EV_WRITTEN_BY, "skill_sha": "a" * 40})
        torn = '{"at": "2026-10-06T00:00:01+00:00", "type": "' + EV_USER_DECISION + '", "question": "q1"'
        with open(journal, "w", encoding="utf-8") as f:
            f.write(head + "\n" + torn)                     # no newline after the last line: torn
        globals()["_writer_sha"] = lambda: "a" * 40
        with contextlib.redirect_stdout(io.StringIO()):
            assert _main(["process.py", d, "decision", "q2 — лишаємо 45°?", "yes", "-1.1"]) == 0
            assert any(e.get("type") == EV_USER_DECISION and e.get("question") == "q2 — лишаємо 45°?"
                       for e in Process(d).events()), "the event after a torn line was glued to it and lost"
            assert _main(["process.py", d, "decision", "q3", "no"]) == 0
        events = Process(d).events()
        assert [e["type"] for e in events] == [EV_WRITTEN_BY, EV_USER_DECISION, EV_USER_DECISION], events
        lines = [head, torn] + [json.dumps(e, ensure_ascii=False) for e in events[1:]]
        with open(journal, "rb") as f:
            written = f.read()
        assert written == ("\n".join(lines) + "\n").replace("\n", os.linesep).encode("utf-8"), written
    finally:
        globals()["_writer_sha"] = real_sha
        shutil.rmtree(top, ignore_errors=True)


def _check_line_torn_inside_a_character():
    """A journal whose last write was cut INSIDE a multi-byte character keeps working (R23): the events before the cut
    are read, the gate that reads the journal answers, and the next event is appended and read back. The journal was
    decoded whole, so the cut raised `UnicodeDecodeError` -- out of `events()`, out of `_stamp` before the write (no
    event could follow it), and out of `_positions_asked`."""
    import contextlib
    import io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_cut_char_")
    real_sha = _writer_sha

    def survives(label, fn):
        try:
            return fn()
        except ValueError as exc:                          # UnicodeDecodeError is a ValueError
            raise AssertionError(f"{label} raised {type(exc).__name__}: {exc}") from None
    try:
        d = os.path.join(top, "process")
        os.makedirs(d)
        journal = os.path.join(d, "journal.jsonl")
        head = {"at": "2026-10-06T00:00:00+00:00", "type": EV_WRITTEN_BY, "skill_sha": "a" * 40}
        asked = {"at": "2026-10-06T00:00:01+00:00", "type": EV_USER_DECISION,
                 "question": "the ellipsoid positions?", "answer": "так"}
        cut = json.dumps({"at": "2026-10-06T00:00:02+00:00", "type": EV_USER_DECISION, "question": "лишаємо 45°?"},
                         ensure_ascii=False).encode("utf-8")
        cut = cut[:cut.index("л".encode("utf-8")) + 1]     # the write stopped after the first byte of "л"
        before = b"".join((json.dumps(e, ensure_ascii=False) + os.linesep).encode("utf-8") for e in (head, asked))
        with open(journal, "wb") as f:
            f.write(before + cut)
        globals()["_writer_sha"] = lambda: "a" * 40
        assert survives("events()", lambda: Process(d).events()) == [head, asked], "the events before the cut"
        assert survives("_positions_asked", lambda: _positions_asked(top)) is True, "the decision before the cut"
        with contextlib.redirect_stdout(io.StringIO()):
            assert survives("decision", lambda: _main(["process.py", d, "decision", "q2", "yes"])) == 0
        events = Process(d).events()
        assert [e.get("question") for e in events[1:]] == ["the ellipsoid positions?", "q2"], events
        with open(journal, "rb") as f:
            written = f.read()
        assert written == before + cut + (os.linesep + json.dumps(events[-1], ensure_ascii=False) + os.linesep).encode(
            "utf-8"), written[len(before):]
    finally:
        globals()["_writer_sha"] = real_sha
        shutil.rmtree(top, ignore_errors=True)


class _Held:
    """While the `with` lasts, opening `path` in a mode `refuses` matches raises what Windows raises for a file another
    program holds: a sharing violation reaches `open()` as `PermissionError`, errno 13. `refuses(mode)` is every mode by
    default. How the tests hold the journal or the changelog (F I-2, F M-7, m2) without a second program."""

    def __init__(self, path, refuses=lambda mode: True):
        self.path, self.refuses = os.path.abspath(path), refuses

    def __enter__(self):
        import builtins
        self.builtins, self.real = builtins, builtins.open

        def held(file, mode="r", *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)) and os.path.abspath(os.fsdecode(file)) == self.path \
                    and self.refuses(mode):
                raise PermissionError(13, "The process cannot access the file because it is being used by another "
                                          "process", os.fsdecode(file))
            return self.real(file, mode, *args, **kwargs)
        builtins.open = held
        return self

    def __exit__(self, *exc_info):
        self.builtins.open = self.real
        return False


def _check_journal_that_cannot_be_opened():
    """A journal that is there and cannot be opened is never read as empty by the method (#134, F I-2, H minor 4,
    R53): held by another program (Windows), a permission, a folder in its place. Every reader read it as `[]` -- no
    file and no events alike -- so `amp-changes` said "no amp changes on record", `amp-gain` numbered its change
    `amp-1` again, `session_closed()` answered False, the flaw-map gate refused for the wrong reason, `session-reopen`
    said the journal held no session event, and a state writer wrote its change before its event's append failed. Now
    the method's reads (`_events`) raise an exception with `is_unreadable` naming the journal and the repair its cause
    allows, and every verb that reads or writes the journal exits 1 on it with nothing on stdout and nothing written --
    the state writers before their write. `events()`, the reader a screen (TCC) calls, stays lenient, as `load()`
    does (R53): such a journal is `[]` there. No file at all is no events."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_held_journal_")
    failures = []
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        with contextlib.redirect_stdout(_io.StringIO()):
            p.enter_phase("-1")
            p.add_step("-1.9", "a step")
            p.record_decision("the ellipsoid positions?", "later")
            p.record_amp_gain({"sw": "+3"})
            p._append(EV_SESSION_CLOSED)
        journal = p.journal_path
        before = _project_bytes(d)

        def refused(label, call):
            try:
                got = call()
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                if not (getattr(exc, "is_unreadable", False) and exc.path == journal
                        and exc.reason.startswith("cannot be opened (")):
                    failures.append(f"{label}: {type(exc).__name__}: {exc}")
            else:
                failures.append(f"{label}: answered {got!r}")
        def lenient(label):
            try:
                got = Process(d).events()
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                got = f"raised {type(exc).__name__}: {exc}"
            if got != []:
                failures.append(f"{label}: events(), the screen's reader, answered {got!r} -- it stays lenient (R53)")
        with _Held(journal):
            lenient("held")
            refused("the method's read (_events)", lambda: Process(d)._events())
            refused("session_closed()", lambda: Process(d).session_closed())
            refused("the flaw-map gate", lambda: _positions_asked(top))
            for argv in (["amp-changes"], ["listening-verdicts"], ["amp-gain", "sw=+3"], ["decision", "q", "a"],
                         ["enter-phase", "-1"], ["start", "-1.9"], ["session-reopen", "it was a check"],
                         ["capture-start", "1", "w-L_1 (sw)"], ["session-close"]):
                rc, out, err = _run_main(["process.py", d, *argv])
                if rc != EXIT_NO or "journal.jsonl cannot be opened" not in err or "Traceback" in err or out.strip():
                    failures.append(f"{' '.join(argv)}: rc {rc}, out {out.strip()[:80]!r}, err {err.strip()[-200:]!r}")
        if _project_bytes(d) != before:
            failures.append("something was written beside the journal that could not be opened")
        if _mode_refuses("a mode-0 journal, met for real"):     # the same, met for real: a permission
            os.chmod(journal, 0)
            try:
                refused("_events() on a mode-0 journal", lambda: Process(d)._events())
                lenient("mode 0")
                try:
                    Process(d)._events()
                except Exception as exc:  # noqa: BLE001
                    if "close what holds it" in str(exc):
                        failures.append(f"a permission told to close what holds it: {exc}")
            finally:
                os.chmod(journal, 0o644)
        os.remove(journal)
        os.makedirs(journal)                                     # a folder where the journal belongs
        try:
            Process(d)._events()
        except Exception as exc:  # noqa: BLE001
            if not (getattr(exc, "is_unreadable", False) and exc.reason == "is a directory, not a file"):
                failures.append(f"a folder in the journal's place: {type(exc).__name__}: {exc}")
        else:
            failures.append("a folder in the journal's place read as a journal")
        lenient("a folder in its place")
        os.rmdir(journal)
        # No file at all is no events, and no session event: a fresh project, not a fault.
        if Process(d).events() != [] or Process(d).session_closed() is not False:
            failures.append("no journal at all is not the empty journal")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a journal that cannot be opened:"] + failures)


def _check_journal_line_in_another_code_page():
    """A journal line in another code page is never dropped without a word (#134, H I-2). A journal begun before
    v3.0.45 on Windows holds lines in cp1251 beside the UTF-8 ones after; R23 skipped such a line like a torn one, so a
    `capture_task_issued` with a Ukrainian note was gone from every reader -- its round, its series (refused as
    foreign), its protective record -- without a word. Now the method's own readers read the journal strictly: a line
    that is not UTF-8 before its end refuses the read, naming the line and the repair (`repair-encoding`), and nothing
    is written. `events()`, TCC's reader, skips it and counts it in `journal_skipped`. A line torn inside its last
    character is torn, skipped as before. The lines are split on "\\n" alone, so a stray "\\r" does not shift the
    numbers a refusal names."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_cp1251_line_")
    failures = []
    try:
        d = os.path.join(top, "process")
        with contextlib.redirect_stdout(_io.StringIO()):
            Process(d).enter_phase("-1")
        head = {"at": "2026-10-06T00:00:00+00:00", "type": EV_WRITTEN_BY, "skill_sha": "a" * 40}
        issued = {"at": "2026-10-06T00:00:01+00:00", "type": EV_CAPTURE_ISSUED, "capture": "cap_001", "phase": "-1",
                  "version": "49", "expected": ["m-L_49 (sw)"], "note": "друга сесія, вікна зачинені"}
        protective = {"at": "2026-10-06T00:00:02+00:00", "type": EV_CAPTURE_PROTECTIVE, "capture": "cap_001",
                      "channel": "m-L", "legs": "OFF", "source": "user"}
        asked = {"at": "2026-10-06T00:00:03+00:00", "type": EV_USER_DECISION,
                 "question": "the ellipsoid positions?", "answer": "later"}
        lines = [json.dumps(head).encode("utf-8"),
                 b"half a line\rand the rest",                         # line 2: a stray "\r", and not JSON
                 json.dumps(issued, ensure_ascii=False).encode("cp1251"),   # line 3: another code page
                 json.dumps(protective).encode("utf-8"),
                 json.dumps(asked, ensure_ascii=False).encode("utf-8")]
        with open(os.path.join(d, "journal.jsonl"), "wb") as f:
            f.write(b"\n".join(lines) + b"\n")
        before = _project_bytes(d)

        def refused(label, call):
            try:
                got = call()
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                said = str(exc)
                if not (getattr(exc, "is_unreadable", False) and "line 3" in said and "line 2" not in said
                        and "repair-encoding" in said):
                    failures.append(f"{label}: {type(exc).__name__}: {said}")
            else:
                failures.append(f"{label}: answered {got!r} past the line in another code page")
        refused("capture_rounds()", lambda: Process(d).capture_rounds())
        refused("protective_record_for('49')", lambda: Process(d).protective_record_for("49"))
        refused("series_used()", lambda: Process(d).series_used())
        refused("session_closed()", lambda: Process(d).session_closed())
        refused("the flaw-map gate", lambda: _positions_asked(top))
        for argv in (["amp-changes"], ["decision", "q", "a"], ["enter-phase", "-1"],
                     ["capture-start", "50", "m-L_50 (sw)"]):
            rc, out, err = _run_main(["process.py", d, *argv])
            if rc != EXIT_NO or "line 3" not in err or "repair-encoding" not in err or "Traceback" in err \
                    or out.strip():
                failures.append(f"{' '.join(argv)}: rc {rc}, out {out.strip()[:80]!r}, err {err.strip()[-200:]!r}")
        same = Process(d)                        # one process, asked twice: a refused read is no stamp decided
        for attempt in (1, 2):
            refused(f"record_decision, attempt {attempt}", lambda: same.record_decision("q", "a"))
        if _project_bytes(d) != before:
            failures.append("something was written beside a journal line in another code page")
        lenient = Process(d)
        got = [e.get("type") for e in lenient.events()]
        if got != [EV_WRITTEN_BY, EV_CAPTURE_PROTECTIVE, EV_USER_DECISION]:
            failures.append(f"events() read {got}")
        if getattr(lenient, "journal_skipped", None) != {"torn": [2], "not_utf8": [3]}:
            failures.append(f"events() counted {getattr(lenient, 'journal_skipped', None)}")
        try:
            Process(d)._events()
        except Exception as exc:  # noqa: BLE001
            if "--set-aside" in str(exc):
                failures.append(f"a line a code page reads was sent to --set-aside: {exc}")
        # A line no code page makes JSON of (R56) -- an old append cut inside a character with the next event glued on
        # (before T-14) -- cannot be rewritten: the refusal names the way that takes it out, bytes kept, and no longer
        # sends the person to a survey that offers nothing.
        glued = b'{"type": "user_decision", "question": "\xd0' + json.dumps(asked).encode("utf-8")
        with open(os.path.join(d, "journal.jsonl"), "wb") as f:
            f.write(b"\n".join([lines[0], lines[2], glued, lines[3]]) + b"\n")
        try:
            Process(d)._events()
        except Exception as exc:  # noqa: BLE001
            said = str(exc)
            if not (getattr(exc, "is_unreadable", False) and "line 2, 3" in said
                    and "no code page makes JSON of line 3 " in said and " --set-aside" in said
                    and "then rewrite the rest as UTF-8" in said):
                failures.append(f"a line no code page reads: {said}")
        else:
            failures.append("a line no code page reads was read")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a journal line in another code page:"] + failures)


def _check_line_separators_inside_an_event():
    """An event holding U+2028, U+2029 or U+0085 is read whole (#134, T I8). The method writes them raw
    (`ensure_ascii=False`), and `str.splitlines()` splits there: a reader that decoded the journal and split it so lost
    the Arbiter's ruling from every reader -- the flaw-map gate, the handoff, the decision lists. The journal is split
    on "\\n" alone, as bytes."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_separators_")
    try:
        d = os.path.join(top, "process")
        with contextlib.redirect_stdout(_io.StringIO()):
            Process(d).enter_phase("-1")
        ls, ps, nel = (chr(c) for c in (0x2028, 0x2029, 0x85))     # built, not literals: data, never printed
        question = f"лишаємо 45°? the positions{ls}a second line{ps}a third{nel}a fourth"
        rc, out, err = _run_main(["process.py", d, "decision", question, "yes"])
        assert rc == 0, (rc, out, err)
        said = [e for e in Process(d).events() if e.get("type") == EV_USER_DECISION]
        assert [e.get("question") for e in said] == [question], said
        assert _positions_asked(top) is True, "the flaw-map gate lost the decision"
        with open(os.path.join(d, "journal.jsonl"), "rb") as f:
            written = f.read()
        assert written.endswith((json.dumps(said[-1], ensure_ascii=False) + os.linesep).encode("utf-8")), written[-200:]
        for raw in (b"\xe2\x80\xa8", b"\xe2\x80\xa9", b"\xc2\x85"):
            assert raw in written, (raw, "written escaped, not raw: the test would test nothing")
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_event_refused_after_the_state():
    """A journal held between a state write and its event's append exits 1 saying what landed (#134, F M-7): the
    state change is written, its journal line is not, and the line to append. It was a bare `PermissionError`, exit 70
    with a traceback -- a bug -- with the state changed and the journal silent. An append refused with no state write
    before it (`decision`) is a refusal too, the event not recorded, nothing written. And a journal that refuses the
    append before the state is written refuses the verb there, nothing written."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_unappended_")
    pio = _project_io()
    real_append = pio.append_line

    def refused(path, line):
        raise PermissionError(13, "The process cannot access the file because it is being used by another process",
                              path)
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        with contextlib.redirect_stdout(_io.StringIO()):
            p.enter_phase("-1")
            p.add_step("-1.9", "a step")
            p.add_step("-1.8", "another step")
        with open(p.journal_path, "rb") as f:
            journal_before = f.read()
        pio.append_line = refused                     # held after `_write`'s look at the journal: the race
        try:
            rc, out, err = _run_main(["process.py", d, "start", "-1.9"])
        finally:
            pio.append_line = real_append
        assert rc == EXIT_NO and "Traceback" not in err, (rc, err[-400:])
        for words in ("process-state.json is written", "its journal line is not", f"`{EV_ATTEMPT_STARTED}`",
                      '"step": "-1.9"', "journal.jsonl"):
            assert words in err, (words, err)
        assert Process(d).step(Process(d).load(strict=True), "-1.9")["status"] == STEP_IN_PROGRESS, \
            "the message says the state change is written"
        with open(p.journal_path, "rb") as f:
            assert f.read() == journal_before, "an event was appended"
        before = _project_bytes(d)
        pio.append_line = refused                     # an event with no state write before it
        try:
            rc, out, err = _run_main(["process.py", d, "decision", "q", "a"])
        finally:
            pio.append_line = real_append
        assert rc == EXIT_NO and "Traceback" not in err and not out.strip(), (rc, out, err[-400:])
        assert "journal.jsonl" in err and f"the `{EV_USER_DECISION}` event was not recorded" in err, err
        assert _project_bytes(d) == before, "a refused decision wrote something"
        with _Held(p.journal_path, refuses=lambda mode: "a" in mode):     # held for appending, readable
            rc, out, err = _run_main(["process.py", d, "start", "-1.8"])
        # One cause, one wording (m4): the journal reads, and refuses the append -- "cannot be appended to", as the
        # append's own refusal says it, never "cannot be opened".
        assert rc == EXIT_NO and "journal.jsonl cannot be appended to (" in err and "Traceback" not in err, (rc, err)
        assert _project_bytes(d) == before, "the state was written beside a journal that refused the append"
        if _mode_refuses("a read-only journal, met for real"):  # both ways in
            os.chmod(p.journal_path, 0o444)
            try:
                for argv in (["start", "-1.8"], ["decision", "q", "a"]):
                    rc, out, err = _run_main(["process.py", d, *argv])
                    assert rc == EXIT_NO and "journal.jsonl cannot be appended to (" in err \
                        and "may not write it" in err and "Traceback" not in err, (argv, rc, err)
            finally:
                os.chmod(p.journal_path, 0o644)
            assert _project_bytes(d) == before, "something was written beside a read-only journal"
        # A close writes its state, then appends its event (#141, J2b): once that event is in, the write owes no line,
        # and a refusal after it -- in the same process, as a caller in code keeps one -- is not said as a state change
        # missing its event.
        q = Process(d)
        with contextlib.redirect_stdout(_io.StringIO()):
            q.start_capture("1", expected=["w-L_1 (sw)"])
            q.close_capture("done")
        pio.append_line = refused
        try:
            q.record_decision("q2", "a2")
        except ProcessError as exc:
            said = str(exc)
            assert f"the `{EV_USER_DECISION}` event was not recorded" in said and "is written" not in said, said
        else:
            raise AssertionError("a refused append went through")
        finally:
            pio.append_line = real_append
    finally:
        pio.append_line = real_append
        shutil.rmtree(top, ignore_errors=True)


def _check_state_replace_refused():
    """A replace refused past the retries -- Windows, a sync client or a scanner holding `process-state.json` -- is a
    refusal naming what holds it, exit 1, the file as it was (#134, H minor 2): it was a `PermissionError`, exit 70, "a
    bug", while the same hold on the read was exit 1. Faked here as Windows: the move is retried as there, then
    refused; nothing is written and no temp is left.

    A round's close refused so is as it was in the journal too (#141, J2b): its event follows the state write now.
    The close's event went first -- W-8's order -- and this "it is as it was" stood over a journal that said closed;
    the byte walk below would have found that line."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_replace_held_")
    pio = _project_io()
    real_replace, real_name, real_waits = os.replace, os.name, pio._REPLACE_RETRIES_S
    tries = []

    def held(src, dst):
        tries.append(dst)
        raise PermissionError(13, "Access is denied", dst)
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        with contextlib.redirect_stdout(_io.StringIO()):
            p.enter_phase("-1")
            p.add_step("-1.9", "a step")
        before = _project_bytes(d)
        try:
            os.name, os.replace, pio._REPLACE_RETRIES_S = "nt", held, (0.001,) * len(real_waits)
            rc, out, err = _run_main(["process.py", d, "start", "-1.9"])
        finally:
            os.name, os.replace, pio._REPLACE_RETRIES_S = real_name, real_replace, real_waits
        assert rc == EXIT_NO and "Traceback" not in err and not out.strip(), (rc, out, err[-400:])
        assert p.state_path in err and "close what holds it" in err and "it is as it was" in err, err
        assert len(tries) == len(real_waits) + 1, f"tried {len(tries)} times, not as on Windows"
        assert _project_bytes(d) == before, "a refused replace left something behind"
        with contextlib.redirect_stdout(_io.StringIO()):
            p.start_capture("1", expected=["w-L_1 (sw)"])
        before = _project_bytes(d)
        del tries[:]
        try:
            os.name, os.replace, pio._REPLACE_RETRIES_S = "nt", held, (0.001,) * len(real_waits)
            rc, out, err = _run_main(["process.py", d, "capture-close", "--no-rew"])
        finally:
            os.name, os.replace, pio._REPLACE_RETRIES_S = real_name, real_replace, real_waits
        assert rc == EXIT_NO and "Traceback" not in err and not out.strip(), (rc, out, err[-400:])
        assert err.rstrip().endswith("it is as it was") and len(tries) == len(real_waits) + 1, (len(tries), err)
        assert _project_bytes(d) == before, "a refused close left something behind: its event in the journal"
    finally:
        os.name, os.replace, pio._REPLACE_RETRIES_S = real_name, real_replace, real_waits
        shutil.rmtree(top, ignore_errors=True)


_UNREADABLE = {
    "empty": b"",
    "truncated": b'{"schema_version": 3, "pla',
    "cp1251": '{"schema_version": 3, "note": "тест"}'.encode("cp1251"),
    "a list": b"[1, 2]",
    "null": b"null",
}


def _state_dir_with(content, top=None):
    """A `process/` folder whose `process-state.json` holds exactly `content`, in a new folder under `top`."""
    import tempfile
    d = os.path.join(tempfile.mkdtemp(dir=top), "process")
    os.makedirs(d)
    with open(os.path.join(d, "process-state.json"), "wb") as f:
        f.write(content)
    return d


class _StateReads:
    """While the `with` lasts, `project_io.read_json` answers for `process-state.json` through `on_read(n, read)`:
    `n` counts this file's reads from 1, `read()` is the real one. Every other file is read as it is. How the race
    tests put a moment between two reads of the state (#136)."""

    def __init__(self, on_read):
        self.on_read, self.count = on_read, 0

    def __enter__(self):
        self.pio = _project_io()
        self.real = self.pio.read_json

        def read_json(path, *args, **kwargs):
            if os.path.basename(path) != "process-state.json":
                return self.real(path, *args, **kwargs)
            self.count += 1
            return self.on_read(self.count, lambda: self.real(path, *args, **kwargs))
        self.pio.read_json = read_json
        return self

    def __exit__(self, *exc_info):
        self.pio.read_json = self.real
        return False


def _check_write_guard_catches_damage_after_the_read():
    """`_write` and `_append` read the file once more before they write (#136, K-2's own guard): a writer whose read
    found the state whole, a moment before the file was damaged, still never writes over the damage -- the guard
    meets it and refuses, the file byte for byte as it was, no event appended. Driven here with the writer's own
    read answered by the state as it was, because `_main`'s read and the writers' own refuse first and hid this one
    (fix round 1: the guard replaced by `pass` kept every selftest green)."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_guard_")
    failures = []
    try:
        for label, content in _UNREADABLE.items():
            for what, call in (("enter_phase", lambda p: p.enter_phase("-1")),
                               ("set_target", lambda p: p.set_target("FULL", "Jazzi")),
                               ("record_reviewer", lambda p: p.record_reviewer("Gemini", "g-3")),
                               ("record_decision", lambda p: p.record_decision("keep 45 degrees?", "yes"))):
                p = Process(_state_dir_with(content, top))
                with _StateReads(lambda n, read: _empty_state() if n == 1 else read()):
                    try:
                        call(p)
                    except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                        if not getattr(exc, "is_unreadable", False):
                            failures.append(f"{label}: {what} raised {type(exc).__name__}: {exc}")
                    else:
                        failures.append(f"{label}: {what} went through")
                with open(p.state_path, "rb") as f:
                    if f.read() != content:
                        failures.append(f"{label}: {what} wrote over the damaged state")
                if os.path.exists(p.journal_path):
                    failures.append(f"{label}: {what} appended an event beside it")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} write(s) past the guard:\n  " + "\n  ".join(failures)


def _writer_methods(src):
    """The public methods of `Process` in the source `src` that write -- that call `_write` or `_append` themselves, or
    through this file's own functions: a method of `Process` (`self._close_capture(...)`), or a function of the module
    (`_helper(self, ...)`) -- and a method that function calls on the process it was handed (`p._close_capture(...)`,
    m6) -- one level down or more (T m14). The table of `_check_writers_read_strictly` is held to this, so a writer
    cannot slip past it by writing through a private helper."""
    import ast
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Process")
    methods = {f.name: f for f in cls.body if isinstance(f, ast.FunctionDef)}
    functions = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}

    def reaches(fn):
        """`fn`'s calls: `("w", None)` for `_write`/`_append` on anything, `("m", name)` for `<anything>.<name>(...)`
        where `name` is a method of `Process` -- `self.<name>` in a method, and the process a function was handed,
        `p.<name>`, in a function (m6: `_helper(p)` -> `p._close_capture(...)` slipped) -- and `("f", name)` for a
        function of this module. A call on something that is no process but shares a method's name is followed too:
        a writer table asked to drive one method more is a red test, never a writer missed."""
        out = set()
        for call in (c for c in ast.walk(fn) if isinstance(c, ast.Call)):
            if isinstance(call.func, ast.Attribute):
                if call.func.attr in ("_write", "_append"):
                    out.add(("w", None))
                elif call.func.attr in methods:
                    out.add(("m", call.func.attr))
            elif isinstance(call.func, ast.Name) and call.func.id in functions:
                out.add(("f", call.func.id))
        return out
    graph = {("m", name): reaches(fn) for name, fn in methods.items()}
    graph.update({("f", name): reaches(fn) for name, fn in functions.items()})
    writing = {("w", None)}
    while True:
        more = {node for node, out in graph.items() if node not in writing and out & writing}
        if not more:
            break
        writing |= more
    return {name for kind, name in writing if kind == "m" and not name.startswith("_")}


def _check_writers_read_strictly():
    """A writer's OWN read of the state is strict (#136, R25). An open refused for a moment -- Windows, while another
    writer replaces the file -- read as an empty process: the writer built on it, and `_write`'s guard, reading the
    file again a moment later and finding it whole, let the empty plan over it. Now every writer method refuses at
    its own read, nothing written. The methods are every public one of `Process` that calls `_write` or `_append`,
    itself or through this file's own functions (`_writer_methods`), read off the source, so a new writer cannot slip
    past the table -- through a private helper neither (T m14). And the verdicts that read the state again after
    `_main`'s read (`check`, `handoff --json`, `capture-close`'s count, `session-close`'s look at what is open, and
    `capture-check`'s exit code, its last read) read it strictly: a check never says 0 off a read that failed,
    `session-close` never records a clean stop off one (T I3), `handoff --json` answers in its own shape."""
    import contextlib
    import io as _io
    import shutil
    import tempfile

    class Verifier:                          # `check_captures`' arithmetic, without REW
        def verify(self, titles):
            return [{"name": t, "exists": True, "valid": True, "issues": [], "stats": {}} for t in titles]

    top = tempfile.mkdtemp(prefix="autosound_process_strict_writers_")
    failures = []
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        with contextlib.redirect_stdout(_io.StringIO()):
            p.enter_phase("-1")
            p.add_step("-1.9", "a step")
            p.start_capture("1", expected=["w-L_1 (sw)", "w-R_1 (sw)"])
            p.record_capture("w-L_1 (sw)")
            p.close_capture("the first pass")
            p.start_capture("2", expected=["w-L_2 (sw)", "w-R_2 (sw)"])
            p.record_capture("w-L_2 (sw)")
            p._append(EV_SESSION_CLOSED)

        def raw(path):
            with open(path, "rb") as f:
                return f.read()
        files = {path: raw(path) for path in (p.state_path, p.journal_path)}
        writers = (
            ("enter_phase", lambda: p.enter_phase("-1")),
            ("add_step", lambda: p.add_step("-1.8", "another step")),
            ("start_attempt", lambda: p.start_attempt("-1.9")),
            ("finish_step", lambda: p.finish_step("-1.9", ["w-L_2 (sw)"])),
            ("skip_step", lambda: p.skip_step("-1.9", reason="not needed")),
            ("block_step", lambda: p.block_step("-1.9", "waiting")),
            ("record_reviewer", lambda: p.record_reviewer("Gemini", "g-3")),
            ("set_target", lambda: p.set_target("FULL", "Jazzi")),
            ("start_capture", lambda: p.start_capture("3", expected=["w-L_3 (sw)"])),
            ("reconcile_captures", lambda: p.reconcile_captures(["w-L_2 (sw)"])),
            ("record_capture", lambda: p.record_capture("w-R_2 (sw)")),
            ("set_protective", lambda: p.set_protective("w-L", "OFF")),
            ("set_knobs", lambda: p.set_knobs({"SubRC": "4/4"})),
            ("supersede_capture", lambda: p.supersede_capture("w-L_2 (sw)", "w-L_2 (rta)")),
            ("skip_capture", lambda: p.skip_capture("w-R_2 (sw)", "later")),
            ("check_captures", lambda: p.check_captures(verifier=Verifier())),
            ("close_capture", lambda: p.close_capture("done")),
            ("amend_protective", lambda: p.amend_protective("cap_001", "w-L", "OFF", "late")),
            ("amend_knobs", lambda: p.amend_knobs("cap_001", {"SubRC": "4/4"}, "late")),
            ("record_amp_gain", lambda: p.record_amp_gain({"sw": "+3"})),
            ("record_listening_verdict", lambda: p.record_listening_verdict([], text="fine")),
            ("record_decision", lambda: p.record_decision("keep 45 degrees?", "yes")),
            ("record_session", lambda: p.record_session("tcc", "opus")),
            ("reopen_session", lambda: p.reopen_session("it was a check")),
            ("capture_import", lambda: p.capture_import("2", ["w-L_2 (sw)"], {"": None}, {"SubRC": "4/4"})),
        )
        writes = _writer_methods(open(os.path.abspath(__file__), encoding="utf-8").read())
        table = {name for name, _ in writers}
        assert table == writes, f"writers this table does not drive: {sorted(writes - table)}; gone: " \
                                f"{sorted(table - writes)}"

        def failed_once(n, read):
            if n == 1:
                raise _project_io().Unreadable(p.state_path, "cannot be opened (held a moment by another writer)")
            return read()

        def failed_second(n, read):
            return failed_once(n - 1, read)

        def restore():
            for path, data in files.items():
                with open(path, "wb") as f:
                    f.write(data)

        def kept():
            return all(raw(path) == data for path, data in files.items())

        for name, call in writers:
            with _StateReads(failed_once), contextlib.redirect_stdout(_io.StringIO()):
                try:
                    call()
                except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                    if not getattr(exc, "is_unreadable", False):
                        failures.append(f"{name}: refused for another reason: {type(exc).__name__}: {exc}")
                else:
                    failures.append(f"{name}: built on an empty process")
            if not kept():
                failures.append(f"{name}: wrote")
                restore()
        # The verdicts read the state again after `_main`'s read: that second read is the one that fails here -- and
        # for `capture-check` its LAST read, the one its exit code stands on, after its checks are written (T I3): a
        # lenient one gave exit 0 off an empty process, and `session-close` recorded a clean stop over an open round.
        want = _handoff_json_keys(top)
        real_verifier = Process._load_verifier
        Process._load_verifier = lambda self: Verifier()
        try:
            for argv in (["check"], ["handoff", "--json"], ["capture-close", "--no-rew"], ["session-close"],
                         ["capture-check"]):
                fail = failed_second
                if argv[0] == "capture-check":
                    counted = _StateReads(lambda n, read: read())       # a dry run counts its reads; then restored
                    with counted, contextlib.redirect_stdout(_io.StringIO()):
                        _main(["process.py", d, *argv])
                    restore()

                    def fail(n, read, last=counted.count):
                        if n == last:
                            raise _project_io().Unreadable(p.state_path, "cannot be opened (held a moment by another "
                                                                         "writer)")
                        return read()
                out, err = _io.StringIO(), _io.StringIO()
                with _StateReads(fail), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main(["process.py", d, *argv])
                said = err.getvalue()
                if rc != 1 or "process-state.json" not in said:
                    failures.append(f"{' '.join(argv)}: rc {rc}, said {(said or out.getvalue()).strip()[-120:]!r}")
                if argv[0] == "handoff":
                    try:
                        answer = json.loads(out.getvalue())
                    except ValueError:
                        answer = {}
                    if set(answer) != want or answer.get("ok") is not False \
                            or "process-state.json" not in " ".join(answer.get("missing") or []):
                        failures.append(f"handoff --json: answered {out.getvalue().strip()[:160]!r}")
                elif argv[0] == "capture-check":            # its verdicts are on disk before the exit's read
                    restore()
                    continue
                elif out.getvalue():
                    failures.append(f"{' '.join(argv)}: printed {out.getvalue().strip()[:120]!r}")
                if not kept():
                    failures.append(f"{' '.join(argv)}: wrote")
                    restore()
        finally:
            Process._load_verifier = real_verifier
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} writer(s) read the state leniently:\n  " + "\n  ".join(failures)


def _handoff_json_keys(top):
    """The keys `handoff --json` answers with, read off a fresh project's real answer: a refusal answers with them
    too, so a front-end reading the one reads the other (TCC shows `missing`)."""
    import contextlib
    import io as _io
    import tempfile
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        _main(["process.py", os.path.join(tempfile.mkdtemp(dir=top), "process"), "handoff", "--json"])
    return set(json.loads(out.getvalue()))


def _check_unreadable_state():
    """K-2 (#136): a `process-state.json` that is there and cannot be read is not an empty process. The lenient read
    still gives one (a `[1, 2]` or a `null` raised `TypeError` there); the strict read raises an exception with
    `is_unreadable`; `enter-phase` (a write), `show` and `session-close` exit 1 naming the file and its repair, its
    bytes left as they were -- the write put an empty process over it, `show` printed one, and `session-close` found
    nothing open and recorded a close. A fresh project has no file, and that is not a fault; a UTF-8 BOM is an
    editor's marker, not damage."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_unreadable_")
    try:
        for label, content in _UNREADABLE.items():
            d = _state_dir_with(content, top)
            p = Process(d)
            assert p.load()["plan"] == [], f"{label}: the lenient read is an empty process"
            try:
                p.load(strict=True)
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                assert getattr(exc, "is_unreadable", False), (label, exc)
            else:
                raise AssertionError(f"{label}: strict load read it")
            repair = "repair-encoding" if label == "cp1251" else "checkout HEAD -- process-state.json"
            for argv in (["enter-phase", "-1"], ["show"], ["session-close"]):
                err = _io.StringIO()
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(_io.StringIO()):
                    rc = _main(["process.py", d, *argv])
                said = err.getvalue()
                assert rc == 1 and "process-state.json" in said and repair in said, (label, argv, rc, said)
                # The committed copy is not the journal's last word (H 13): a project's repository may hold only its
                # first commit, nothing replays the events since, and a project with no repository has no copy at all.
                if label != "cp1251":
                    assert "it may be older than the journal" in said and "move process-state.json aside" in said, \
                        (label, argv, said)
                with open(p.state_path, "rb") as f:
                    assert f.read() == content, f"{label}: {argv[0]} rewrote the unreadable file"
            assert not any(e.get("type") == EV_SESSION_CLOSED for e in p.events()), \
                f"{label}: session-close wrote a close"
        # A fresh project has no file, and that is not a fault -- in either mode.
        fresh = os.path.join(tempfile.mkdtemp(dir=top), "process")
        assert Process(fresh).load(strict=True)["plan"] == [], "no file is the empty process, strict too"
        with contextlib.redirect_stdout(_io.StringIO()):
            assert _main(["process.py", fresh, "enter-phase", "-1"]) == 0
        # A BOM is an editor's marker, not damage: read, and replaced by the next transition.
        d = _state_dir_with(b'\xef\xbb\xbf' + json.dumps(_empty_state()).encode(), top)
        assert Process(d).load(strict=True)["schema_version"] == SCHEMA_VERSION
        with contextlib.redirect_stdout(_io.StringIO()):
            assert _main(["process.py", d, "enter-phase", "-1"]) == 0, "the write refused a state with a BOM"
        assert Process(d).load(strict=True)["active_phase"] == "-1"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_every_writer_refuses_unreadable():
    """The read rule, verb by verb (#136, R24). On a `process-state.json` that is there and cannot be read, every verb
    that writes -- the state or the journal -- and every verdict (`check`, `handoff`, `session-close`, and `show`)
    exits 1 naming the file and its repair before it does anything: nothing on stdout (`handoff --json` answers in its
    own JSON, `ok: false` and the file in `missing`), the state and the journal byte for byte as they were. Each
    used to run on an empty process: the journal-only verbs appended, `check` said
    0 and exit 0, the others refused for a step or a round the empty process lacked. The verbs are read off `_main`'s
    dispatch, so a new one cannot slip past this table; only `_DISPLAY_VERBS` still read such a file as an empty
    process, and they write nothing. In code, `_append` refuses as `_write` does (`project.py record-change` appends
    through it)."""
    import ast
    import contextlib
    import io as _io
    import shutil
    import tempfile
    strict = (["show"], ["enter-phase", "-1"], ["add-step", "2.9", "a step", "--project"], ["start", "2.3"],
              ["done", "2.3", "v_001"], ["skip", "2.3", "not needed"], ["block", "2.3", "waiting"],
              ["reviewer", "Gemini", "g-3"], ["target", "FULL", "Jazzi"], ["decision", "keep 45 degrees?", "yes"],
              ["session-start", "tcc", "opus"], ["session-close"], ["session-close", "--check"],
              ["session-reopen", "it", "was", "a", "check"], ["capture-start", "2", "w-L_2 (sw)"], ["capture-check"],
              ["capture-taken", "w-L_2 (sw)"],
              ["capture-import", "2", "w-L_2 (sw)", "--bind", "=v_001", "--knob", "SubRC=4/4"],
              ["amp-gain", "sw=+3"], ["capture-knobs", "SubRC=4/4"],
              ["capture-knobs", "--amend", "cap_001", "--reason", "late", "SubRC=4/4"],
              ["capture-protective", "w-L", "OFF"],
              ["capture-protective", "--amend", "cap_001", "--reason", "late", "w-L", "OFF"],
              ["listening-verdict", "--text", "fine"], ["capture-supersede", "w-L_2 (sw)", "w-L_2 (rta)"],
              ["handoff"], ["handoff", "--json"], ["capture-skip", "w-L_2 (sw)", "later"],
              ["capture-close", "--no-rew"], ["check"])
    display = (["plan"], ["amp-changes"], ["listening-verdicts"], ["listening-verdicts", "--bank"])
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_main")
    verbs = {c.comparators[0].value for c in ast.walk(main)
             if isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) and c.left.id == "cmd"
             and isinstance(c.comparators[0], ast.Constant)}
    named = {a[0] for a in strict} | {a[0] for a in display}
    assert named == verbs, f"verbs this table does not drive: {sorted(verbs - named)}; gone: {sorted(named - verbs)}"
    assert {a[0] for a in display} == set(_DISPLAY_VERBS), ("display-only", sorted(_DISPLAY_VERBS))
    # A closed round and a close: what `session-reopen` and the `--amend` forms would write after, were they let.
    journal = "".join(json.dumps(e) + "\n" for e in (
        {"at": "2026-10-01T00:00:00+00:00", "type": EV_CAPTURE_ISSUED, "capture": "cap_001", "version": "1",
         "phase": "0", "expected": ["w-L_1 (sw)"]},
        {"at": "2026-10-01T00:00:01+00:00", "type": EV_CAPTURE_CLOSED, "capture": "cap_001", "version": "1"},
        {"at": "2026-10-01T00:00:02+00:00", "type": EV_SESSION_CLOSED})).encode("utf-8")
    top = tempfile.mkdtemp(prefix="autosound_process_every_verb_")
    failures = []
    try:
        keys = _handoff_json_keys(top)
        for label, content in _UNREADABLE.items():
            repair = "repair-encoding" if label == "cp1251" else "checkout HEAD -- process-state.json"
            for argv in strict + display:
                d = _state_dir_with(content, top)
                with open(os.path.join(d, "journal.jsonl"), "wb") as f:
                    f.write(journal)
                out, err = _io.StringIO(), _io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main(["process.py", d, *argv])
                with open(os.path.join(d, "process-state.json"), "rb") as f:
                    state_kept = f.read() == content
                with open(os.path.join(d, "journal.jsonl"), "rb") as f:
                    journal_kept = f.read() == journal
                if argv in display:
                    ok = rc == 0 and state_kept and journal_kept
                else:
                    printed = out.getvalue()
                    if argv == ["handoff", "--json"]:   # its own shape: a front-end reads stdout (TCC shows `missing`)
                        try:
                            answer = json.loads(printed)
                        except ValueError:
                            answer = {}
                        printed_ok = (set(answer) == keys and answer.get("ok") is False
                                      and repair in " ".join(answer.get("missing") or []))
                    else:
                        printed_ok = not printed
                    ok = (rc == 1 and printed_ok and "process-state.json" in err.getvalue()
                          and repair in err.getvalue() and state_kept and journal_kept)
                if not ok:
                    failures.append(f"{label}: {' '.join(argv)} -> rc {rc}, state kept {state_kept}, journal kept "
                                    f"{journal_kept}, said {(err.getvalue() or out.getvalue()).strip()[-90:]!r}")
        # In code: the two primitives refuse, so a writer that does not come through `_main` cannot write either.
        d = _state_dir_with(_UNREADABLE["truncated"], top)
        with open(os.path.join(d, "journal.jsonl"), "wb") as f:
            f.write(journal)
        p = Process(d)
        for what, call in (("_append", lambda: p._append(EV_CONFIG_CHANGE, file="project.json", what="a swap")),
                           ("record_decision", lambda: p.record_decision("q?", "yes")),
                           ("record_session", lambda: p.record_session("tcc", "opus"))):
            try:
                call()
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                if not getattr(exc, "is_unreadable", False):
                    failures.append(f"{what}: raised {type(exc).__name__}: {exc}")
            else:
                failures.append(f"{what}: wrote beside an unreadable state")
        with open(os.path.join(d, "journal.jsonl"), "rb") as f:
            if f.read() != journal:
                failures.append("in code: the journal changed")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} verb run(s) read an unreadable state as empty:\n  " + "\n  ".join(failures)


def _gate_run(d, argv):
    """`_main` on `process/` folder `d`: (exit code, stderr, whether the state and the journal kept their bytes). A
    traceback is no exit code: it comes back as the text `raised <type>: <message>` in the code's place."""
    import contextlib
    import io as _io

    def held():
        out = {}
        for name in ("process-state.json", "journal.jsonl"):
            path = os.path.join(d, name)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    out[name] = f.read()
        return out
    before = held()
    err = _io.StringIO()
    with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(err):
        try:
            rc = _main(["process.py", d, *argv])
        except Exception as exc:  # noqa: BLE001 -- a traceback is what some of these runs gave; it is reported
            rc = f"raised {type(exc).__name__}: {exc}"
    return rc, err.getvalue(), held() == before


def _check_gates_refuse_unreadable():
    """A gate that cannot check refuses (#136, audit T-10). "A checker that raises must not become a wall" let the phase
    in whenever the intake check itself failed or could not be loaded; a `project.json` holding `[1, 2]` stopped phase
    1 with a traceback; a `dsp_profile.json` cut off let phase 1 in with no rate on record. Each now exits 1, naming
    what failed, and writes nothing -- an unreadable file raised inside the check as itself, with its own repair. A
    file that is not there is still no wall: that is the intake check's to name."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_gates_")
    contract = _siblings().load("contract.py")
    real_check, real_siblings = contract.check_project, globals()["_siblings"]
    unreadable = _project_io().Unreadable
    failures = []

    def at_phase_minus_one():
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(d).enter_phase("-1")
        return d
    try:
        for label, boom, want in (
                ("the check raised", RuntimeError("the checker broke"),
                 "phase 0 is not entered: the intake check raised RuntimeError: the checker broke"),
                ("a file it read is unreadable", unreadable("/x/glossary.json", "is empty -- a write was cut off",
                                                            "REPAIR"),
                 "error: /x/glossary.json is empty -- a write was cut off -- REPAIR")):
            def raiser(*args, _boom=boom, **kwargs):
                raise _boom
            contract.check_project = raiser
            try:
                rc, said, kept = _gate_run(at_phase_minus_one(), ["enter-phase", "0"])
            finally:
                contract.check_project = real_check
            if not (rc == 1 and want in said and kept):
                failures.append(f"{label}: rc {rc}, files kept {kept}, said {said.strip()[-160:]!r}")

        def without(missing):
            """A `_siblings` whose `load` fails for `missing` at import and loads every other file as the real one."""
            def siblings():
                sib = real_siblings()

                def load(rel):
                    if rel == missing:
                        raise ImportError(f"{missing} fails at import")
                    return sib.load(rel)
                return type("S", (), {"load": staticmethod(load)})
            return siblings
        d = at_phase_minus_one()
        globals()["_siblings"] = without("contract.py")
        try:
            rc, said, kept = _gate_run(d, ["enter-phase", "0"])
        finally:
            globals()["_siblings"] = real_siblings
        if not (rc == 1 and kept and "phase 0 is not entered: the intake check could not be loaded (ImportError: "
                                     "contract.py fails at import) -- the install is broken, not the project" in said):
            failures.append(f"contract.py not loaded: rc {rc}, files kept {kept}, said {said.strip()[-160:]!r}")
        globals()["_siblings"] = without("dsp_profile.py")
        try:
            _require_profile_facts("1", "0", top)
        except ProcessError as exc:
            if str(exc) != ("phase 1 is not entered: the profile check could not be loaded (ImportError: "
                            "dsp_profile.py fails at import) -- the install is broken, not the project"):
                failures.append(f"dsp_profile.py not loaded: refused with {exc}")
        else:
            failures.append("dsp_profile.py not loaded: the phase 1 profile check passed")
        finally:
            globals()["_siblings"] = real_siblings
        # Phase 1's gates, on a project that passes everything else: intake, a target, a flaw map with evidence.
        for name, raw, reason in (("project.json", b"[1, 2]", "holds an array where an object belongs"),
                                  ("dsp_profile.json", b'{"dsp_profile": {"name": "Fixture", "gro',
                                   "is not valid JSON")):
            root = tempfile.mkdtemp(dir=top)
            _seed_intake(root)
            p = Process(os.path.join(root, "process"))
            p.enter_phase("-1")
            p.enter_phase("0")
            p.set_target("FULL", "Jazzi")
            _load_sibling("project.py").Project(root).add_flaw(
                f_hz=160, level_db=-12, kind="cabin_null", action="leave", why="fixture", evidence=["w-L_01 (sw)"])
            path = os.path.join(root, name)
            with open(path, "wb") as f:
                f.write(raw)
            rc, said, kept = _gate_run(p.dir, ["enter-phase", "1"])
            if not (rc == 1 and kept and p.load()["active_phase"] == "0"):
                failures.append(f"{name} {raw[:12]!r}: rc {rc}, files kept {kept}, phase {p.load()['active_phase']}, "
                                f"said {said.strip()[-160:]!r}")
            if name == "dsp_profile.json" and not (f"error: {path} {reason}" in said
                                                   and "checkout HEAD -- dsp_profile.json" in said):
                failures.append(f"{name}: enter-phase 1 said {said.strip()[-160:]!r}")
            # The gate of its own, asked directly: the file, the reason and the repair (the intake check, run first by
            # `enter_phase`, may refuse such a `project.json` before it -- it reads the glossary from it too).
            gate = _flaw_map_entries if name == "project.json" else (lambda r: _require_profile_facts("1", "0", r))
            try:
                gate(root)
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                if not (getattr(exc, "is_unreadable", False) and str(exc).startswith(f"{path} {reason}")
                        and f"checkout HEAD -- {name}" in str(exc)):
                    failures.append(f"{name}: its gate raised {type(exc).__name__}: {exc}")
            else:
                failures.append(f"{name}: its gate read it")
        # No file is not a wall: an absent `project.json` is no flaw map to judge, an absent profile no facts to ask.
        bare = tempfile.mkdtemp(dir=top)
        if _flaw_map_entries(bare) is not None:
            failures.append("an absent project.json read as a flaw map")
        try:
            _require_profile_facts("1", "0", bare)
        except Exception as exc:  # noqa: BLE001 -- any refusal here is the failure
            failures.append(f"an absent dsp_profile.json refused: {type(exc).__name__}: {exc}")
    finally:
        contract.check_project = real_check
        globals()["_siblings"] = real_siblings
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} gate(s) let a phase in that they could not check:\n  " + "\n  ".join(failures)


def _check_newer_state_refused():
    """A `process-state.json` a newer method wrote is refused by every strict read (#136, audit T-21). Its version was
    checked only at the write ("unsupported"), after the reads before it had taken the state for this copy's. `load(
    strict=True)` raises `ProcessError` naming the file, both numbers and the way to a newer method, so every verb but
    the display-only ones exits 1 before it does anything; and `_write` and `_append` refuse one that a newer method
    wrote between a writer's read and its write. The lenient read is as it was."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_newer_")
    newer = json.dumps(dict(_empty_state(), schema_version=SCHEMA_VERSION + 1)).encode("utf-8")
    want = f"is schema v{SCHEMA_VERSION + 1}; this method reads v{SCHEMA_VERSION} -- update the method: "
    failures = []
    try:
        p = Process(_state_dir_with(newer, top))
        try:
            p.load(strict=True)
        except ProcessError as exc:
            if not (str(exc).startswith(f"{p.state_path} {want}") and "/autosound-tuning:setup" in str(exc)):
                failures.append(f"load(strict=True) said {exc}")
        else:
            failures.append("load(strict=True) read a state a newer method wrote")
        if p.load()["schema_version"] != SCHEMA_VERSION + 1:
            failures.append("the lenient read changed")
        for argv in (["enter-phase", "-1"], ["add-step", "1.1", "a step"], ["decision", "keep 45 degrees?", "yes"],
                     ["session-start", "tcc", "opus"], ["show"], ["check"], ["handoff"]):
            rc, said, kept = _gate_run(_state_dir_with(newer, top), argv)
            if not (rc == 1 and kept and want in said):
                failures.append(f"{argv[0]}: rc {rc}, files kept {kept}, said {said.strip()[-120:]!r}")
        for what, call in (("enter_phase", lambda q: q.enter_phase("-1")),
                           ("set_target", lambda q: q.set_target("FULL", "Jazzi")),
                           ("record_decision", lambda q: q.record_decision("keep 45 degrees?", "yes"))):
            q = Process(_state_dir_with(newer, top))
            with _StateReads(lambda n, read: _empty_state() if n == 1 else read()):
                try:
                    call(q)
                except ProcessError as exc:
                    if want not in str(exc):
                        failures.append(f"{what}: refused with {exc}")
                else:
                    failures.append(f"{what}: wrote beside a state a newer method wrote")
            with open(q.state_path, "rb") as f:
                if f.read() != newer:
                    failures.append(f"{what}: wrote the newer state down")
            if os.path.exists(q.journal_path):
                failures.append(f"{what}: appended an event beside it")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} read(s) took a newer state:\n  " + "\n  ".join(failures)


def _cli_env(d, argv, **env):
    """This file's command line on the `process/` folder `d`, run as a process of its own: `subprocess.run`'s
    result. `env` is added to the environment. REW is the dead port unless `env` names another, so no check
    reaches a REW open on this machine (T-30)."""
    import subprocess
    return subprocess.run([sys.executable, os.path.abspath(__file__), d, *argv], capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8", "REW_API_URL": "http://127.0.0.1:1",
                               **env})


#: What this run of the selftest could not check on this machine, `(case, why)`, said one line each above its OK line
#: (the final review's m-5): an OK line claims only what ran.
_NOT_CHECKED_HERE = []


def _mode_refuses(case):
    """True where a file's mode refuses this user -- POSIX, not root -- so `case`, which needs that, runs. Elsewhere it
    is recorded in `_NOT_CHECKED_HERE` and skipped: root opens and writes a mode-0 file all the same, and Windows keeps
    no POSIX mode."""
    if os.name == "posix" and os.geteuid() != 0:
        return True
    _NOT_CHECKED_HERE.append((case, "run as root, whom no file mode refuses" if os.name == "posix" else
                              "Windows keeps no POSIX mode"))
    return False


def _project_bytes(d):
    """`{path: bytes}` of every file in the project the `process/` folder `d` belongs to -- the state, the journal,
    and what a verb writes beside them (a round's plan in `docs/plans/`). Not the top `.autosound/`: the writer
    lock's bookkeeping (write_lock.py), not the project's content."""
    top = os.path.dirname(os.path.abspath(d))
    out = {}
    for folder, dirs, names in os.walk(top):
        if folder == top and ".autosound" in dirs:
            dirs.remove(".autosound")
        for name in names:
            path = os.path.join(folder, name)
            with open(path, "rb") as f:
                out[os.path.relpath(path, top)] = f.read()
    return out


def _check_project_bytes_leave_the_lock_out():
    """`.autosound/` at the project's top is the writer lock's bookkeeping (write_lock.py, #141), made by whichever
    writer takes the lock: `_project_bytes` leaves it out, so taking the lock never reads as a change to the project.
    Only the top one: a `.autosound/` deeper down is the project's like any other folder."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_bytes_")
    try:
        for rel in ("process/journal.jsonl", ".autosound/write.lock", ".autosound/.gitignore", "docs/.autosound/x"):
            path = os.path.join(top, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")
        got = sorted(rel.replace(os.sep, "/") for rel in _project_bytes(os.path.join(top, "process")))
        assert got == ["docs/.autosound/x", "process/journal.jsonl"], f"the walk read {got}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _at_phase(top, phase):
    """A `process/` folder in a new project under `top`, its state at `phase` -- written as it stands, by no writer: no
    gate is crossed on the way and no lock is taken. What the lock's checks start from (#141)."""
    state = _empty_state()
    at = PHASES.index(phase)
    for i, key in enumerate(PHASES):
        state["phases"][key]["status"] = PHASE_DONE if i < at else PHASE_CURRENT if i == at else PHASE_TODO
    state["active_phase"] = phase
    return _state_dir_with(json.dumps(state, indent=2, ensure_ascii=False).encode("utf-8"), top)


def _lock_holder(project_dir, signals):
    """The other writer of `_check_a_held_lock_answers_75_with_nothing_written`, in a process of its own: it holds the
    project's lock, says so (`<signals>/held`) and lets go when the parent says `go` -- or after a minute, so a parent
    that broke cannot leave it holding. At the top level, so that `spawn` finds it: the child runs this file by its
    path, and reaches `write_lock.py` by its path too, as every writer here does."""
    import time
    with _hold(project_dir):
        with open(os.path.join(signals, "held"), "w", encoding="utf-8"):
            pass
        deadline = time.monotonic() + 60
        while not os.path.exists(os.path.join(signals, "go")):
            if time.monotonic() > deadline:
                raise SystemExit("the parent never said go")
            time.sleep(0.002)


def _raised(call):
    """The exception `call()` raised, or None."""
    try:
        call()
    except Exception as exc:  # noqa: BLE001 -- returned to the check, which reads what it got
        return exc
    return None


def _from_another_thread(write):
    """`write()` run in another thread, as another writer of the project runs it, and waited for: what it raised, None,
    or `never returned` past 30 s."""
    import threading
    out = []
    t = threading.Thread(target=lambda: out.append(_raised(write)), daemon=True)
    t.start()
    t.join(30)
    return out[0] if out else "never returned"


def _run_main(argv):
    """`_main(argv)` in this process: (exit code, stdout, stderr)."""
    import contextlib
    import io as _io
    out, err = _io.StringIO(), _io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = _main(argv)
    return rc, out.getvalue(), err.getvalue()


def _check_exit_table():
    """The exit table (#134, audit T-23): a bug exits 70 with its traceback, where it exited 1 like a refusal; REW
    not answering is 69 with nothing written -- `capture-check`, and a REW error that reaches `_main` itself; a close
    with REW down still closes on the record alone (0). The bug is a planted one, in a run of its own: a typed
    mistake in a leg was this check's example, and it is the verb's refusal now (`_check_typed_values_refused`)."""
    import shutil
    import subprocess
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_exits_")
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")              # a bare folder: leaving -1 is the intake gate's, and it refuses
        here = os.path.abspath(__file__)
        planted = (f"import importlib.util, sys\n"
                   f"sys.path.insert(0, {os.path.dirname(os.path.dirname(here))!r})\n"
                   f"spec = importlib.util.spec_from_file_location('process_planted', {here!r})\n"
                   f"m = importlib.util.module_from_spec(spec)\n"
                   f"spec.loader.exec_module(m)\n"
                   f"m.Process.record_decision = lambda self, *args, **kwargs: [][0]\n"
                   f"sys.exit(m._main(['process.py', {d!r}, 'decision', 'keep 45 degrees?', 'yes']))\n")
        before = _project_bytes(d)
        r = subprocess.run([sys.executable, "-c", planted], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8",
                                                  "REW_API_URL": "http://127.0.0.1:1"})
        assert r.returncode == 70 and "Traceback" in r.stderr, (r.returncode, r.stderr[-300:])
        assert r.stderr.rstrip().splitlines()[-1] == "error: unexpected IndexError: list index out of range", \
            r.stderr[-300:]
        assert _project_bytes(d) == before, "a bug wrote something"
        Process(d).start_capture("1", expected=["a (sw)"])
        before = _project_bytes(d)
        r = _cli_env(d, ["capture-check"], REW_API_URL="http://127.0.0.1:1")
        assert r.returncode == 69, (r.returncode, r.stderr[-300:])
        assert "REW did not answer" in r.stderr and "nothing was recorded" in r.stderr \
            and "start REW and run capture-check again" in r.stderr, r.stderr[-300:]
        assert _project_bytes(d) == before, "REW down wrote something"
        # REW's own exception, met by a verb that asks REW itself (the titles of a series, for an import).
        r = _cli_env(d, ["capture-import", "1", "--bind", "=v_001", "--knob", "SubRC=4/4"])
        assert r.returncode == 69 and "nothing was written" in r.stderr and "Traceback" not in r.stderr, \
            (r.returncode, r.stderr[-300:])
        assert _project_bytes(d) == before, "REW down wrote something (capture-import)"
        r = _cli_env(d, ["capture-close"], REW_API_URL="http://127.0.0.1:1")
        assert r.returncode == 0, ("capture-close closes on the record alone with REW down, as before", r.stderr)
        assert "REW not reached" in r.stdout and "not checked against REW" in r.stdout, r.stdout[-300:]
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_typed_values_refused():
    """A typed mistake in a value the verb parses itself is the verb's refusal, exit 1 in its own words -- never a
    bug's 70 (#134, F I-1, T I1, H I-7). capture-protective's legs reached `float()` and `int()` unguarded: a flag in a
    value's place (`--hp 100 LR --lp 4000 BW 36`), a frequency that is no number (`abc`, `100Hz`), a slope that is no
    whole number (`24.5`) each exited 70 with a traceback, and TCC sends a leg as the person typed it
    (`protective_dialog.read_leg`). So did capture-import's series (`1a`) -- with titles given, and with none, where
    REW was asked first. Nothing is written, nothing goes to stdout, no traceback, and REW is not asked. A value that
    parses is checked too (R47b, R48): a frequency above 0, a type of the four (`dsp_math`'s modellable families LR,
    BW and BE, and CH, recorded as typed: a Chebyshev is what a Helix and TCC's dialog offer; any letter case), a slope
    above 0 -- an empty type, `XX`, a zero slope were each recorded."""
    import shutil
    import tempfile
    import types
    top = tempfile.mkdtemp(prefix="autosound_process_typed_")
    asked = []

    def listing():
        asked.append("get_measurements")
        return {}
    stand_in = types.ModuleType("rew_api")
    stand_in.get_measurements = listing
    saved = sys.modules.get("rew_api")
    failures = []
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["m-L_1 (sw)"])
        p.set_protective("m-L", "OFF")
        cap_id = p.protective_record()["id"]
        p.close_capture("the pass is over")
        p.start_capture("2", expected=["m-L_2 (sw)"])       # open: a leg that parsed would be recorded on it
        before = _project_bytes(d)
        three = "--hp needs three values: f type slope, e.g. --hp 100 LR 24"
        sys.modules["rew_api"] = stand_in
        for argv, said in (
                (["capture-protective", "m-L", "--hp", "100", "LR", "--lp", "4000", "BW", "36"], three),
                (["capture-protective", "m-L", "--hp", "100", "--lp", "4000", "BW", "36"], three),
                (["capture-protective", "m-L", "--hp", "abc", "LR", "24"], "--hp: 'abc' is not a number"),
                (["capture-protective", "m-L", "--hp", "100Hz", "LR", "24"], "--hp: '100Hz' is not a number"),
                (["capture-protective", "m-L", "--hp", "nan", "LR", "24"], "--hp: 'nan' is not a number"),
                (["capture-protective", "m-L", "--hp", "100", "LR", "24.5"], "--hp: '24.5' is not a whole number"),
                (["capture-protective", "m-L", "--lp", "4000", "BW", "36", "--hp", "100", "LR", "x"],
                 "--hp: 'x' is not a whole number"),
                # R47b, R48: each value checked -- a frequency above 0, a type of the four (LR, BW, BE, CH; empty is
                # none), a slope above 0.
                (["capture-protective", "m-L", "--hp", "0", "LR", "24"], "--hp: '0' is not a frequency above 0 Hz"),
                (["capture-protective", "m-L", "--hp", "-100", "LR", "24"],
                 "--hp: '-100' is not a frequency above 0 Hz"),
                (["capture-protective", "m-L", "--hp", "100", "", "24"],
                 "--hp: '' is not a filter type: LR, BW, BE or CH"),
                (["capture-protective", "m-L", "--lp", "4000", "XX", "36"],
                 "--lp: 'XX' is not a filter type: LR, BW, BE or CH"),
                (["capture-protective", "m-L", "--hp", "100", "LR", "0"], "--hp: '0' is not a slope above 0 dB/oct"),
                (["capture-protective", "m-L", "--hp", "100", "LR", "-24"],
                 "--hp: '-24' is not a slope above 0 dB/oct"),
                (["capture-protective", "--amend", cap_id, "--reason", "the roll-off shows", "m-L", "--lp", "4k",
                  "BW", "36"], "--lp: '4k' is not a number"),
                (["capture-import", "1a", "m-L_1 (sw)", "--bind", "=v_001", "--knob", "SubRC=4/4"],
                 "capture-import: '1a' is not a number"),
                (["capture-import", "1a", "--bind", "=v_001", "--knob", "SubRC=4/4"],
                 "capture-import: '1a' is not a number")):
            try:
                rc, out, err = _run_main(["process.py", d, *argv])
            except Exception as exc:  # noqa: BLE001 -- what is under test is that nothing escapes
                rc, out, err = f"raised {type(exc).__name__}: {exc}", "", ""
            if rc != EXIT_NO or said not in err or out or "Traceback" in err:
                failures.append(f"{' '.join(argv)}: rc {rc}, said {(err or out).strip()[-160:]!r}")
        if asked:
            failures.append("capture-import asked REW before reading its series")
        if _project_bytes(d) != before:
            failures.append("a typed mistake wrote something")
        try:
            p.capture_import("1a", ["m-L_1 (sw)"], {"": None}, {"SubRC": "4/4"})
        except ProcessError as exc:
            if "'1a' is not a number" not in str(exc):
                failures.append(f"capture_import('1a') refused with {exc}")
        except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
            failures.append(f"capture_import('1a') raised {type(exc).__name__}: {exc}")
        else:
            failures.append("capture_import('1a') went through")
        # A type in any letter case is the type (R47b): `be` is recorded as `BE`. A Chebyshev is recorded as typed
        # (R48): it is what was in the chain -- TCC's dialog offers `CH`, a Helix offers the family -- though `dsp_math`
        # models no Chebyshev.
        rc, out, err = _run_main(["process.py", d, "capture-protective", "m-L", "--hp", "80", "be", "12",
                                  "--lp", "4000", "ch", "36"])
        legs = (p.protective_record() or {}).get("channels", {}).get("m-L")
        if rc != 0 or legs != {"hp": {"f": 80.0, "type": "BE", "slope": 12},
                               "lp": {"f": 4000.0, "type": "CH", "slope": 36}}:
            failures.append(f"capture-protective m-L --hp 80 be 12 --lp 4000 ch 36: rc {rc}, recorded {legs}, "
                            f"said {err.strip()!r}")
        # Recorded, and said for what it is (#134, R49, R52): a Chebyshev cannot be taken back out -- the method has no
        # model for it -- so its sweeps are not "de-embedded before any phase decision", as the line said. The way on
        # is the person's, on the DSP. A leg the method models keeps the old line.
        if "de-embedded before any phase decision" in out or "LP 4000 CH36" not in out \
                or "cannot be de-embedded" not in out or "LR, BW or BE" not in out:
            failures.append(f"capture-protective m-L ... --lp 4000 ch 36 said {out.strip()!r}")
        rc, out, err = _run_main(["process.py", d, "capture-protective", "m-L", "--hp", "80", "lr", "24"])
        if rc != 0 or "de-embedded before any phase decision" not in out or "cannot be de-embedded" in out:
            failures.append(f"capture-protective m-L --hp 80 lr 24: rc {rc}, said {out.strip()!r} {err.strip()!r}")
        # An amendment to a Chebyshev says the same (a closed round's record, corrected).
        round_id = p.protective_record()["id"]
        _run_main(["process.py", d, "capture-close", "--no-rew"])
        rc, out, err = _run_main(["process.py", d, "capture-protective", "--amend", round_id, "--reason",
                                  "it was a Chebyshev", "m-L", "--hp", "80", "CH", "24"])
        if rc != 0 or "corrected to HP 80 CH24" not in out or "cannot be de-embedded" not in out:
            failures.append(f"capture-protective --amend ... m-L --hp 80 CH 24: rc {rc}, said {out.strip()!r} "
                            f"{err.strip()!r}")
        # The leg types are dsp_math's modellable families and the Chebyshev, nothing else: a family `dsp_math` comes
        # to model is a type a leg can carry. Read off `dsp_math.py`'s text, not imported: it needs numpy, and this
        # module's checks do not.
        import ast
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dsp_math.py"),
                  encoding="utf-8") as fh:
            families = next((ast.literal_eval(n.value) for n in ast.parse(fh.read()).body
                             if isinstance(n, ast.Assign)
                             and any(isinstance(t, ast.Name) and t.id == "MODELLABLE_FAMILIES" for t in n.targets)),
                            None)
        if not set(families or ()) <= set(_LEG_TYPES) or set(_LEG_TYPES) - set(families or ()) != {"CH"}:
            failures.append(f"the leg types {_LEG_TYPES} are not dsp_math's modellable families {families} and CH")
    finally:
        if saved is None:
            sys.modules.pop("rew_api", None)
        else:
            sys.modules["rew_api"] = saved
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} typed mistake(s) not refused as such:\n  " + "\n  ".join(failures)


def _check_refused_capture_writes_nothing():
    """A refused capture verb writes nothing (#134, H I-3): the journal and the state byte for byte as they were.
    `capture-start <N> --plan` closed the open round -- `capture_round_closed`, "superseded", its titles outstanding --
    before its own refusals (no glossary, a ledger version, no phase, a phase that captures nothing): exit 1, the state
    still holding the round open, the journal saying it closed, and the next round closed it a second time.
    `capture-import` checked a bind only when it opened that DSP state's round: a bad second bind was refused after the
    first round was on disk -- opened, taken, its knobs, closed -- and a re-run imported it again."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_refused_capture_")
    failures = []

    def refused(d, argv, said):
        before = _project_bytes(d)
        rc, out, err = _run_main(["process.py", d, *argv])
        if rc != EXIT_NO or said not in err:
            failures.append(f"{' '.join(argv)}: rc {rc}, said {(err or out).strip()[-160:]!r}")
        if _project_bytes(d) != before:
            journal = os.path.join(d, "journal.jsonl")
            tail = [e.get("type") for e in Process(d).events()][-3:] if os.path.exists(journal) else []
            failures.append(f"{' '.join(argv)}: refused, and wrote (the journal ends {tail})")
    try:
        # No glossary: a bare folder with a round open.
        bare = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(bare).enter_phase("-1")
        Process(bare).start_capture("1", expected=["m-L_1 (sw)"])
        refused(bare, ["capture-start", "2", "--plan"], "--plan needs the project's glossary")
        # A glossary, a banked v_001, and a round open with no phase on record.
        root = tempfile.mkdtemp(dir=top)
        _seed_intake(root)
        d = os.path.join(root, "process")
        Process(d).start_capture("1", expected=["w-L_1 (sw)"])
        refused(d, ["capture-start", "2", "--plan"], "--plan needs the phase the round measures for")
        refused(d, ["capture-start", "v_001", "--plan"], "--plan builds titles from a SERIES number")
        refused(d, ["capture-start", "2", "--plan", "--phase", "-1"],
                "the method's plan for phase '-1' captures nothing")
        # capture-import: the plain titles bound to a banked version, the `C` ones to a version nobody banked.
        root = tempfile.mkdtemp(dir=top)
        _seed_intake(root)
        d = os.path.join(root, "process")
        Process(d).enter_phase("-1")
        refused(d, ["capture-import", "1", "w-L_1 (sw)", "w-L C_1 (sw)", "--bind", "=v_001", "--bind", "C=v_009",
                    "--knob", "SubRC=4/4"], "--bind C=v_009: not a banked ledger version (banked: v_001)")
        if Process(d).capture_rounds():
            failures.append(f"capture-import opened rounds before its refusal: {Process(d).capture_rounds()}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} refused capture verb(s) wrote:\n  " + "\n  ".join(failures)


def _check_import_of_a_whole_series():
    """`capture-import <N>` with no titles imports what REW holds of series N and this project has not on record
    (#134, R47a). REW holding nothing of series N is exit 1, `REW holds no measurement of series _N; nothing was
    imported` -- it said "imported 0 title(s)", exit 0, and wrote nothing. Every title REW holds of it on record already
    is exit 0, `nothing new`, and nothing written -- a re-run imported the series again, as rounds of their own. With
    some on record, only the rest is imported. REW is a stand-in `rew_api` in `sys.modules`, which `_main`'s
    `import rew_api` finds first."""
    import shutil
    import tempfile
    import types
    listing = {}
    stand_in = types.ModuleType("rew_api")
    stand_in.get_measurements = lambda: dict(listing)
    saved = sys.modules.get("rew_api")
    top = tempfile.mkdtemp(prefix="autosound_process_import_series_")
    failures = []

    def run(*argv):
        before = _project_bytes(d)
        rc, out, err = _run_main(["process.py", d, "capture-import", *argv, "--bind", "=v_001", "--knob", "SubRC=4/4"])
        return rc, out, err, _project_bytes(d) == before
    try:
        os.makedirs(os.path.join(top, "state", "SQ"))
        with open(os.path.join(top, "state", "SQ", "v_001.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        sys.modules["rew_api"] = stand_in
        listing.update({"1": {"title": "m-L_2 (sw)"}, "2": {"title": "a note"}})
        rc, out, err, kept = run("1")
        if rc != EXIT_NO or "REW holds no measurement of series _1; nothing was imported" not in err or out or not kept:
            failures.append(f"none of series _1 held: rc {rc}, kept {kept}, said {(err or out).strip()!r}")
        listing.update({"3": {"title": "m-L_1 (sw)"}, "4": {"title": "m-R_1 (sw)"}})
        rc, out, err, kept = run("1")
        rounds = Process(d).capture_rounds()
        if rc != 0 or "imported 2 title(s) of _1" not in out or len(rounds) != 1:
            failures.append(f"the first import: rc {rc}, rounds {rounds}, said {(err or out).strip()!r}")
        rc, out, err, kept = run("_1")
        if rc != 0 or "nothing new" not in out or not kept or len(Process(d).capture_rounds()) != 1:
            failures.append(f"all on record: rc {rc}, kept {kept}, rounds {len(Process(d).capture_rounds())}, "
                            f"said {(err or out).strip()!r}")
        listing.update({"5": {"title": "w-L_1 (sw)"}})
        rc, out, err, kept = run("1")
        rounds = Process(d).capture_rounds()
        if rc != 0 or "imported 1 title(s) of _1" not in out or "2 already on record" not in out \
                or len(rounds) != 2 or set(rounds[-1]["titles"]) != {"w-L_1 (sw)"}:
            failures.append(f"one new: rc {rc}, rounds {rounds}, said {(err or out).strip()!r}")
        # On record by every road a title takes: a typo superseded (only its `capture_taken` names it), a title read
        # against REW under REW's own spelling (`renames`) and one taken beyond the list (only the closed round's
        # `taken` names it) -- and, in a round still open, what the read against REW took (only the state names it).
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        os.makedirs(os.path.join(os.path.dirname(d), "state", "SQ"))
        with open(os.path.join(os.path.dirname(d), "state", "SQ", "v_001.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["m-L_1 (sw)"])
        p.record_capture("m-R_1 (sw)")
        p.supersede_capture("m-R_1 (sw)", "m-L_1 (sw)", "typed R for L")
        p.reconcile_captures(["m-L_01 (sw)", "m-R_1 (sw)", "w-L_1 (sw)"])
        p.close_capture("done")
        p.start_capture("1", expected=["tw-L_1 (sw)"])
        p.reconcile_captures(["tw-L_1 (sw)", "tw-R_1 (sw)"])
        listing.clear()
        listing.update({str(i): {"title": t} for i, t in enumerate(
            ("m-L_01 (sw)", "m-R_1 (sw)", "w-L_1 (sw)", "tw-L_1 (sw)", "tw-R_1 (sw)"))})
        rc, out, err, kept = run("1")
        if rc != 0 or "nothing new: the 5 measurement(s) of series _1" not in out or not kept:
            failures.append(f"on record by every road: rc {rc}, kept {kept}, said {(err or out).strip()!r}")
    finally:
        if saved is None:
            sys.modules.pop("rew_api", None)
        else:
            sys.modules["rew_api"] = saved
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} import(s) of a whole series misread:\n  " + "\n  ".join(failures)


def _check_catch_all_reads_the_type():
    """The catch-all reads `rew_state` and `is_unreadable` off the exception's CLASS (#134): REW down raised by any
    copy of `rew_api` (another class, the same attribute) is 69; REW answering something this method cannot read is
    REW's answer, not a bug -- 1, REW's words and "nothing was written", where it was 70 (`capture-import` met it on
    REW's list); so is REW answering with an error (F M-4, H minor 1): a stdlib `HTTPError`, REW's 4xx/5xx with its
    words, and an exception whose class says `rew_state` "error" -- 1, where the `HTTPError` was a bug's 70 with a
    traceback. One built without a body -- whose instance, on Python 3.9, answers every attribute it lacks with
    `KeyError: 'file'` -- is said the same way, never a crash of the handler itself. Every other state REW's
    exceptions name is REW's answer as well (R47c): `write_mismatch`, `not_found`, `ambiguous` and `config` (a
    `REW_API_URL` that is no address) exit 1 with their message -- a `not_found` or an `ambiguous` a `KeyError`, its
    words without the quotes a `KeyError` puts round them -- read off the class, so a foreign copy of `rew_api`
    raising its own `RewWriteMismatch` is said the same way. Only "unavailable" is 69. An IndexError raised inside a
    verb (R36) is a bug's 70 with its traceback: it exited 1 like a refusal, with no traceback. A write REW took is
    never "nothing was written" (m3, H 10): a `write_mismatch` says REW may hold part of it, and a write REW
    acknowledged and nobody could read back (`rew_unchecked`) is said in its own words. The traps raise for any
    attribute their instance lacks on every Python, as an `HTTPError` built without a body does on 3.9 alone, so
    the class-read rule is held on 3.12 too (T m1)."""
    import importlib.util
    import shutil
    import tempfile
    import urllib.error

    class Down(Exception):                     # REW down as another copy of `rew_api` raises it
        rew_state = "unavailable"

    class Unreadable(Exception):               # REW's answer unreadable, as another copy of `rew_api` raises it
        rew_state = "protocol"

    class Answered(Exception):                 # REW answering with an error, as a copy that names the state raises it
        rew_state = "error"

    class Misread(Exception):                  # a filter write REW did not keep
        rew_state = "write_mismatch"

    class Gone(KeyError):                      # a title REW does not hold, as `find_measurement_id` raises it
        rew_state = "not_found"

    class Twice(KeyError):                     # a title REW holds twice
        rew_state = "ambiguous"

    class Misconfigured(ValueError):           # a `REW_API_URL` that is no address (`rew_api.RewAddressError`)
        rew_state = "config"

    class SentUnchecked(OSError):              # a filter write REW acknowledged, its read-back unanswered (H 10)
        rew_state = "unavailable"
        rew_unchecked = True

    class Trap(Exception):                     # an instance that raises for any attribute it lacks, on every Python:
        def __getattr__(self, name):           # what an `HTTPError` built without a body does on 3.9 (T m1)
            raise KeyError("file")

    class TrapHTTP(urllib.error.HTTPError):    # REW's error answer whose instance raises so
        def __getattr__(self, name):
            raise KeyError("file")

    # A foreign copy of `rew_api`, loaded by its path under another name: its classes are not the sibling's.
    spec = importlib.util.spec_from_file_location(
        "autosound_rew_api_foreign_copy", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                       "rew_api.py"))
    foreign = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foreign)
    assert foreign.RewWriteMismatch is not _siblings().load("rew_api.py").RewWriteMismatch, "not a foreign copy"
    top = tempfile.mkdtemp(prefix="autosound_process_catch_all_")
    real = Process.record_decision
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        nothing = " -- nothing was written"
        # A write REW took is never "nothing was written" (m3, H 10): REW may hold part of a write it did not keep,
        # and a write it acknowledged and nobody could read back says so in its own words.
        took = " -- REW may hold part of the write: check REW's EQ before going on"
        sent = ("REW acknowledged the filter write to measurement 3 ('Filters set'), and reading the filters back "
                "failed (refused): the write was sent and acknowledged but not checked -- check REW's EQ before going "
                "on")
        for exc, code, said in ((Down("REW is not answering at http://127.0.0.1:1"), 69,
                                 "error: REW is not answering at http://127.0.0.1:1" + nothing),
                                (Unreadable("REW's measurement list is not a map of measurements: list"), 1,
                                 "error: REW's measurement list is not a map of measurements: list -- nothing was "
                                 "written"),
                                (urllib.error.HTTPError("http://127.0.0.1:1/x", 500, "boom", {}, None), 1,
                                 "error: REW answered with an error: HTTP Error 500: boom -- nothing was written"),
                                (TrapHTTP("http://127.0.0.1:1/x", 500, "boom", {}, None), 1,
                                 "error: REW answered with an error: HTTP Error 500: boom -- nothing was written"),
                                (Answered("HTTP Error 404: Not Found -- REW said: no such measurement"), 1,
                                 "error: REW answered with an error: HTTP Error 404: Not Found -- REW said: no such "
                                 "measurement -- nothing was written"),
                                (Misread("slot 3: REW holds gaindB +12.0 where +14.0 was sent"), 1,
                                 "error: slot 3: REW holds gaindB +12.0 where +14.0 was sent" + took),
                                (SentUnchecked(sent), 69, f"error: {sent}\n"),
                                (Gone("No measurement titled 'w-L_1 (sw)' (REW holds 3)"), 1,
                                 "error: No measurement titled 'w-L_1 (sw)' (REW holds 3)" + nothing),
                                (Twice("Ambiguous: 2 measurements titled 'w-L_1 (sw)'"), 1,
                                 "error: Ambiguous: 2 measurements titled 'w-L_1 (sw)'" + nothing),
                                (Misconfigured("REW_API_URL 'localhost:4735' is not an address: no scheme"), 1,
                                 "error: REW_API_URL 'localhost:4735' is not an address: no scheme" + nothing),
                                (foreign.RewWriteMismatch("slot 2 missing from REW's filters after the write"), 1,
                                 "error: slot 2 missing from REW's filters after the write" + took),
                                (foreign.MeasurementNotFound("No measurement titled 'm-L_1 (sw)' (REW holds 0)"), 1,
                                 "error: No measurement titled 'm-L_1 (sw)' (REW holds 0)" + nothing),
                                (IndexError("list index out of range"), 70,
                                 "error: unexpected IndexError: list index out of range"),
                                (Trap("the handler reads no instance"), 70,
                                 "error: unexpected Trap: the handler reads no instance")):
            def boom(self, *args, _exc=exc, **kwargs):
                raise _exc
            Process.record_decision = boom
            before = _project_bytes(d)
            try:
                rc, _, err = _run_main(["process.py", d, "decision", "keep 45 degrees?", "yes"])
            except Exception as e:  # noqa: BLE001 -- what is under test is that nothing escapes the handler
                rc, err = f"raised {type(e).__name__}: {e}", ""
            assert rc == code and said in err, (type(exc).__name__, rc, err[-300:])
            assert ("Traceback" in err) is (code == 70), (type(exc).__name__, err[-300:])
            assert (nothing in err) is (said.endswith(nothing)), ("'nothing was written' where a write was sent",
                                                                  type(exc).__name__, err[-300:])
            assert _project_bytes(d) == before, f"{type(exc).__name__}: something was written"
        Process.record_decision = real
        # `capture-import` asks REW for a series' titles itself, through its own `import rew_api` -- which finds
        # `sys.modules` first, so a stand-in there answers it: REW's list unreadable reached the catch-all as a bug
        # (70, a traceback), and so did REW answering the listing with an error. REW's own class, from the sibling
        # copy; REW's error as `rew_api._open` raises it, its words on the message.
        import types
        protocol = _siblings().load("rew_api.py").RewProtocolError

        def unreadable():
            raise protocol("REW's measurement list is not a map of measurements: list")

        def answered_500():
            raise urllib.error.HTTPError("http://127.0.0.1:1/measurements", 500,
                                         "Internal Server Error -- REW said: the measurement list is being rebuilt",
                                         {}, None)
        saved = sys.modules.get("rew_api")
        rebuilt = ("REW answered with an error: HTTP Error 500: Internal Server Error -- REW said: the measurement "
                   "list is being rebuilt")
        for listing, words in ((unreadable, "not a map of measurements"), (answered_500, rebuilt)):
            stand_in = types.ModuleType("rew_api")
            stand_in.get_measurements = listing
            sys.modules["rew_api"] = stand_in
            try:
                before = _project_bytes(d)
                rc, out, err = _run_main(["process.py", d, "capture-import", "1", "--bind", "=v_001", "--knob",
                                          "SubRC=4/4"])
            finally:
                if saved is None:
                    sys.modules.pop("rew_api", None)
                else:
                    sys.modules["rew_api"] = saved
            assert rc == 1 and words in err and "nothing was written" in err and "Traceback" not in err, \
                (listing.__name__, rc, out, err[-300:])
            assert _project_bytes(d) == before, f"capture-import wrote beside REW's answer ({listing.__name__})"
    finally:
        Process.record_decision = real
        shutil.rmtree(top, ignore_errors=True)


def _check_unknown_flags():
    """N19 (#134): a flag the verb does not take is a usage error -- exit 2, nothing written, and never the words
    TCC reads as "the method is too old". It used to become a title, a reason or evidence. `--flag=value` is read as
    `--flag value`; a flag that takes no value takes no `=`. Every flag the dispatcher reads is in `VERB_FLAGS`."""
    import ast
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_flags_")
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        r = _cli_env(d, ["capture-start", "1", "a (sw)", "--origni", "x"])
        assert r.returncode == 2 and "--origni" in r.stderr and "usage: process.py" not in r.stderr, r.stderr
        assert "--origin" in r.stderr, f"the refusal names the flags the verb takes: {r.stderr}"
        assert Process(d).load().get("capture") is None, "an unknown flag opened a round"
        Process(d).add_step("1.1", "a")
        Process(d).add_step("2.1", "b")
        assert _cli_env(d, ["skip", "1.1", "--superseded-by=2.1"]).returncode == 0
        # The skip records its link on the event (`skip_step`): the value is the link, not the reason's text.
        skipped = [e for e in Process(d).events() if e.get("type") == EV_STEP_SKIPPED][-1]
        assert (skipped.get("step"), skipped.get("superseded_by"), skipped.get("reason")) == ("1.1", "2.1", None), \
            skipped
        before = _project_bytes(d)
        for argv, flag in ((["done", "1.1", "--evidence", "v_001"], "--evidence"),
                           (["capture-check", "--session=yes"], "--session"),
                           (["handoff", "--json=1"], "--json"),
                           (["show", "--json"], "--json")):
            rc, out, err = _run_main(["process.py", d, *argv])
            assert rc == 2 and flag in err and not out and "usage: process.py" not in err, (argv, rc, err, out)
        assert _project_bytes(d) == before, "a refused flag wrote something"
        # A word after a flag's value is still the verb's: `decision`'s step given after `--invalidates X` was dropped.
        rc, _, err = _run_main(["process.py", d, "decision", "keep it?", "no", "--invalidates", "w-L_1 (sw)", "1.1"])
        said = [e for e in Process(d).events() if e.get("type") == EV_USER_DECISION][-1]
        assert rc == 0 and (said["step"], said["invalidates"]) == ("1.1", "w-L_1 (sw)"), (rc, err, said)
        # The split and its edges, on the function itself.
        assert _args_checked("decision", ["q", "a", "--invalidates=w-L_1 (sw)"]) == \
            ["q", "a", "--invalidates", "w-L_1 (sw)"]
        assert _args_checked("capture-import", ["9", "--bind==v_001", "--knob=SubRC=4/4"]) == \
            ["9", "--bind", "=v_001", "--knob", "SubRC=4/4"]
        assert _args_checked("enter-phase", ["-1"]) == ["-1"] and _args_checked("skip", ["2.3", "--", "x"]) == \
            ["2.3", "--", "x"], "a bare `--`, a negative number and a word pass"
        assert _args_checked("amp-gain", ["sw=+3", "--note=--loud"]) == ["sw=+3", "--note", "--loud"], \
            "a value given with `=` is the flag's, whatever it looks like"
        assert _args_checked("amp-gain", ["sw=+3", "--note", "--loud"]) == ["sw=+3", "--note", "--loud"], \
            "...and so is the word after the flag (R35): the two forms are one"
        for cmd, argv, said in (("show", ["--json"], "show does not take --json -- it takes no flags"),
                                ("capture-close", ["--no-rew=1"], "--no-rew takes no value")):
            try:
                _args_checked(cmd, argv)
            except UsageError as exc:
                assert said in str(exc) and getattr(exc, "exit_code", None) == EXIT_USAGE, (cmd, str(exc))
            else:
                raise AssertionError(f"{cmd} {argv} went through")
        # every flag literal the dispatcher reads is in VERB_FLAGS (TCC finds them in this file's text)
        src = open(os.path.abspath(__file__), encoding="utf-8").read()
        main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_main")
        literals = {n.value for n in ast.walk(main) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and n.value.startswith("--") and len(n.value) > 2 and n.value[2].isalpha()}
        known = {f for flags in VERB_FLAGS.values() for f in flags} | {"--help"}
        assert literals <= known, sorted(literals - known)
        # Every flag is classified, taking a value or not, in the one table that says it (T m13, H 21): a flag added
        # to `VERB_FLAGS` alone took the next word as its value, and `_check_value_flag_last` blessed it.
        every = {f for flags in VERB_FLAGS.values() for f in flags}
        classified = set(_FLAG_TAKES_VALUE)
        assert classified == every, ("flags not classified as taking a value or not", sorted(every - classified),
                                     "classified, and no verb takes them", sorted(classified - every))
        assert all(v is True or v is False for v in _FLAG_TAKES_VALUE.values()), _FLAG_TAKES_VALUE
        assert set(_FLAGS_WITHOUT_VALUE) == {f for f, takes in _FLAG_TAKES_VALUE.items() if not takes}, \
            _FLAGS_WITHOUT_VALUE
        # ...and verb by verb, both ways: a flag a verb's branch reads is in that verb's row (or the verb refuses it --
        # `--note` is amp-gain's and listening-verdict's), and a flag a row lists is read by its branch (or it would
        # pass and be ignored). `--hp` and `--lp` are read as legs (`lstrip("-")`), not as literals.
        read = {}
        for node in ast.walk(main):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) \
                    and node.test.left.id == "cmd" and isinstance(node.test.ops[0], ast.Eq) \
                    and isinstance(node.test.comparators[0], ast.Constant):
                read[node.test.comparators[0].value] = {
                    n.value for stmt in node.body for n in ast.walk(stmt)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and _flag_shaped(n.value)
                    and not any(ch.isspace() for ch in n.value)}
        assert set(read) == set(VERB_FLAGS), sorted(set(read) ^ set(VERB_FLAGS))
        for verb, flags in VERB_FLAGS.items():
            assert read[verb] <= set(flags), (verb, "reads flags its row lacks", sorted(read[verb] - set(flags)))
            legs = set(_LEG_FLAGS.get(verb, ()))
            assert set(flags) - legs <= read[verb], (verb, "lists flags it never reads", sorted(set(flags) - read[verb]))
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_flag_values_as_they_stand():
    """R35, R37 (#134): the word after a flag that takes a value is that value, whatever it looks like -- as after
    `=` -- unless, in either form, it is one of the verb's own flags: then the value is missing, exit 2. A flag is
    `--`, an ASCII letter and no whitespace -- after an `=`, whitespace is the value's only when the name before it is
    one of the verb's own flags (M-b) -- so text that only begins with two dashes, or holds a space, is a word. TCC
    sends the Arbiter's own words both ways: after `--text` and `--note` (listening_dialog), after `--reason`
    (protective_dialog, an amendment), and as arguments -- `decision`'s question and answer, the reasons of
    `capture-skip`, `block`, `capture-close`. Each was refused as a flag the verb does not take; `--text "--бас гуде"`
    was recorded before."""
    import shutil
    import tempfile
    bass = "--бас гуде"                 # data: the Arbiter's own words, as TCC passes them on
    bass_word = "--бас"                 # the same with no space: not ASCII, so still a word
    top = tempfile.mkdtemp(prefix="autosound_process_values_")
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        # TCC's listening dialog: the pairs, then --text, --ledger-version, --note (process_writer.py).
        for text, note in (("--loud", bass), (bass, "--quiet"), ("--loud vocals", bass_word)):
            rc, _, err = _run_main(["process.py", d, "listening-verdict", "--pair", "CarMus#07:c09:bad", "--text", text,
                                    "--ledger-version", "v_003", "--note", note])
            assert rc == 0, (text, note, rc, err[-300:])
            got = p.events(kinds=(EV_LISTENING_VERDICT,))[-1]
            assert (got["text"], got["note"]) == (text, note), (text, note, got)
        # TCC's protective dialog on a closed round: --amend, --reason, then the channel and its legs.
        p.start_capture("1", expected=["m-L_1 (sw)"])
        p.set_protective("m-L", "OFF", source="front_end")
        cap_id = p.protective_record()["id"]
        p.close_capture("the pass is over")
        for reason in ("--typo", bass):
            rc, _, err = _run_main(["process.py", d, "capture-protective", "--amend", cap_id, "--reason", reason,
                                    "m-L", "--hp", "100", "LR", "24"])
            assert rc == 0, (reason, rc, err[-300:])
            got = [e for e in p.events(kinds=(EV_CAPTURE_PROTECTIVE,)) if e.get("amends")][-1]
            assert got["reason"] == reason, (reason, got)
        # The Arbiter's words as arguments: with a space, or not ASCII, they are words.
        rc, _, err = _run_main(["process.py", d, "decision", "--bass hums at 45 Hz?", bass_word])
        assert rc == 0, (rc, err[-300:])
        said = p.events(kinds=(EV_USER_DECISION,))[-1]
        assert (said["question"], said["answer"]) == ("--bass hums at 45 Hz?", bass_word), said
        p.add_step("1.1", "a")
        rc, _, err = _run_main(["process.py", d, "block", "1.1", "--waiting for the amp"])
        assert rc == 0 and p.step(p.load(), "1.1")["blocked_reason"] == "--waiting for the amp", (rc, err)
        p.start_capture("2", expected=["a_2 (sw)", "b_2 (sw)", "c_2 (sw)"])
        rc, _, err = _run_main(["process.py", d, "capture-skip", "a_2 (sw)", "--door open, retake", bass])
        assert rc == 0 and p.load()["capture"]["skipped"]["a_2 (sw)"]["reason"] == "--door open, retake " + bass, \
            (rc, err, p.load()["capture"]["skipped"])
        # Whitespace anywhere makes a word (M-b), after an `=` too, unless the name before it is one of the verb's own
        # flags -- TCC's `--invalidates=w-L_1 (sw)` (`_check_flags_tcc_sends`). `--bass=45 Hz hums?` was refused as a
        # flag `decision` does not take, exit 2.
        rc, _, err = _run_main(["process.py", d, "decision", "--bass=45 Hz hums?", "yes"])
        said = p.events(kinds=(EV_USER_DECISION,))[-1]
        assert rc == 0 and (said["question"], said["answer"]) == ("--bass=45 Hz hums?", "yes"), (rc, err, said)
        rc, _, err = _run_main(["process.py", d, "capture-skip", "c_2 (sw)", "--door=open, retake"])
        assert rc == 0 and p.load()["capture"]["skipped"]["c_2 (sw)"]["reason"] == "--door=open, retake", \
            (rc, err, p.load()["capture"]["skipped"])
        # Still refused, nothing written: an ASCII `--word` as an argument or where a flag stands, and a flag whose
        # value is missing -- one of the verb's own flags in its place.
        before = _project_bytes(d)
        for argv, said in ((["capture-skip", "b_2 (sw)", "--loud"], "capture-skip does not take --loud"),
                           (["decision", "--bass=45", "yes"], "decision does not take --bass"),
                           (["capture-start", "3", "a (sw)", "--origni", "x"], "capture-start does not take --origni"),
                           (["capture-start", "3", "--optional", "--plan"], "capture-start: --optional needs a value"),
                           (["amp-gain", "sw=+3", "--note", "--amends=amp-1"], "amp-gain: --note needs a value"),
                           (["capture-protective", "m-L", "--hp", "--lp", "4000", "BW", "36"],
                            "capture-protective: --hp needs a value"),
                           (["listening-verdict", "--pair", "CarMus#07:c09:ok", "--text", "--route", "full"],
                            "listening-verdict: --text needs a value"),
                           # R37: after `=` the same test -- the two forms stay one. A scanning branch read
                           # `--note=--measured` as the flag `--measured` and recorded no note.
                           (["amp-gain", "sw=+3", "--note=--measured"], "amp-gain: --note needs a value"),
                           (["capture-start", "3", "a (sw)", "--optional=--plan"],
                            "capture-start: --optional needs a value"),
                           (["capture-protective", "--amend", cap_id, "--reason=--source", "m-L", "OFF"],
                            "capture-protective: --reason needs a value"),
                           # R41: `-h` and `--help` are among every verb's own flags, in both forms. `--text=-h` was
                           # recorded as the text "-h".
                           (["listening-verdict", "--pair", "CarMus#07:c09:ok", "--text=-h"],
                            "listening-verdict: --text needs a value"),
                           (["listening-verdict", "--pair", "CarMus#07:c09:ok", "--text", "-h"],
                            "listening-verdict: --text needs a value"),
                           (["amp-gain", "sw=+3", "--note=--help"], "amp-gain: --note needs a value"),
                           (["amp-gain", "sw=+3", "--note", "--help"], "amp-gain: --note needs a value")):
            rc, out, err = _run_main(["process.py", d, *argv])
            assert rc == EXIT_USAGE and said in err and not out and "usage: process.py" not in err, (argv, rc, err, out)
        assert _project_bytes(d) == before, "a refused command line wrote something"
        assert p.amp_changes() == [], p.amp_changes()
        # ...while a value after `=` that is no flag of the verb is the value, whatever it looks like.
        rc, _, err = _run_main(["process.py", d, "amp-gain", "sw=+3", "--note=--loud"])
        assert rc == 0 and [c.get("note") for c in p.amp_changes()] == ["--loud"], (rc, err[-300:], p.amp_changes())
        assert not _flag_shaped(bass) and not _flag_shaped(bass_word) and not _flag_shaped("--bass hums") \
            and not _flag_shaped("-- note") and _flag_shaped("--origni") and _flag_shaped("--note=--loud")
        known = VERB_FLAGS["decision"]
        assert _flag_shaped("--invalidates=w-L_1 (sw)", known) and not _flag_shaped("--invalidates=w-L_1 (sw)") \
            and not _flag_shaped("--bass=45 Hz hums?", known) and _flag_shaped("--bass=45", known) \
            and not _flag_shaped("--bass hums=x", known), "whitespace makes a word unless the name is the verb's"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_autocorrected_dashes():
    """Two hyphens an editor autocorrected into a dash (#134, H 20): in a flag's place, a token that starts with an em
    dash or an en dash and names, past its dashes, one of the verb's own flags (`--help` among them, R41) is a usage
    error, exit 2, naming the flag it looks like -- `—origin other:49` opened a round expecting `—origin` and
    `other:49`, the origin never recorded. Nothing is written. After a flag that takes a value, the token is that
    value as it stands (R35), and a dash before a word that is no flag of the verb is the word."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_dashes_")
    failures = []
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        before = _project_bytes(d)
        em, en = "\u2014", "\u2013"
        for argv, said in ((["capture-start", "1", "m-L_1 (sw)", f"{em}origin", "other:49"], f"{em}origin"),
                           (["capture-start", "1", "m-L_1 (sw)", f"{en}origin", "other:49"], f"{en}origin"),
                           (["capture-start", "1", "m-L_1 (sw)", f"{em}origin=other:49"], f"{em}origin"),
                           (["capture-start", "1", "m-L_1 (sw)", f"{en}-optional", "w-L_1 (sw)"], f"{en}-optional"),
                           (["decision", "keep it?", "no", f"{em}invalidates", "w-L_1 (sw)"], f"{em}invalidates"),
                           (["capture-start", "1", f"{em}help"], f"{em}help")):
            name = said.lstrip(em + en + "-")
            want = (f"{argv[0]}: {said} looks like --{name} with its dashes autocorrected; type two hyphens")
            rc, out, err = _run_main(["process.py", d, *argv])
            if rc != EXIT_USAGE or want not in err or out:
                failures.append(f"{' '.join(argv)}: rc {rc}, said {(err or out).strip()[-160:]!r}")
        if _project_bytes(d) != before:
            failures.append("an autocorrected flag wrote something")
        # After a flag that takes a value it is the value, as it stands; a dash before a word no flag of the verb
        # names is that word.
        rc, _, err = _run_main(["process.py", d, "amp-gain", "sw=+3", "--note", f"{em}measured"])
        if rc != 0 or [c.get("note") for c in p.amp_changes()] != [f"{em}measured"]:
            failures.append(f"amp-gain --note {em}measured: rc {rc}, notes {[c.get('note') for c in p.amp_changes()]}")
        rc, _, err = _run_main(["process.py", d, "decision", f"{em}origin of the 45 Hz hum?", f"{em}plan"])
        said = (p.events(kinds=(EV_USER_DECISION,)) or [{}])[-1]
        if rc != 0 or (said.get("question"), said.get("answer")) != (f"{em}origin of the 45 Hz hum?", f"{em}plan"):
            failures.append(f"decision with dashed words: rc {rc}, {err.strip()[-120:]!r}, recorded {said}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} autocorrected dash(es) misread:\n  " + "\n  ".join(failures)


def _check_too_few_arguments():
    """R36 (#134): a verb given fewer arguments than its line names is a usage error -- exit 2, naming what it needs,
    nothing written, no traceback -- where it raised IndexError and exited 1, "list index out of range" (`target`,
    `decision`, `capture-skip` with none). Every verb `_main` dispatches has its row in `_VERB_ARGS`, so a verb added
    there cannot slip past; each name in a row is on the verb's own lines; a flag and its value are not arguments; and
    with exactly the arguments named no verb meets an IndexError, which is a bug's 70 now."""
    import ast
    import shutil
    import tempfile
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_main")
    verbs = sorted({c.comparators[0].value for c in ast.walk(main)
                    if isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) and c.left.id == "cmd"
                    and isinstance(c.comparators[0], ast.Constant)})
    assert set(verbs) == set(_VERB_ARGS), ("the dispatcher's verbs and _VERB_ARGS differ",
                                           sorted(set(verbs) ^ set(_VERB_ARGS)))
    top = tempfile.mkdtemp(prefix="autosound_process_args_")
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["a_1 (sw)"])
        before = _project_bytes(d)
        short = [[verb, *["1"] * (len(_VERB_ARGS[verb]) - 1)] for verb in verbs if _VERB_ARGS[verb]]
        short += [["capture-start", "--step", "2.1", "--plan"], ["reviewer", "Gemini", "--review", "r.md"],
                  ["capture-knobs", "--amend", "cap_001", "--reason", "known in the car"],
                  # A leg's values are the leg's (M-a): with no channel they were counted as arguments, the channel
                  # became `--hp`, and the verb said "expected --hp or --lp ... got '100'", exit 1.
                  ["capture-protective", "--hp", "100", "LR", "24"],
                  ["capture-protective", "--hp", "100", "LR", "24", "--lp", "4000", "BW", "36"],
                  ["capture-protective", "--amend", "cap_001", "--reason", "late", "--lp", "4000", "BW", "36"]]
        for argv in short:
            needs = _VERB_ARGS[argv[0]]
            assert all(name in _verb_usage(argv[0]) for name in needs), (argv[0], needs)
            rc, out, err = _run_main(["process.py", d, *argv])
            assert rc == EXIT_USAGE and f"{argv[0]} needs {' '.join(needs)}" in err, (argv, rc, err, out)
            assert "Traceback" not in err and "usage: process.py" not in err and not out, (argv, err)
        assert _project_bytes(d) == before, "too few arguments wrote something"
        # Exactly the arguments named: run as processes, on the dead port -- some of these ask REW.
        for verb in verbs:
            r = _cli_env(d, [verb, *["1"] * len(_VERB_ARGS[verb])])
            assert r.returncode not in (EXIT_USAGE, EXIT_UNEXPECTED) and "Traceback" not in r.stderr, \
                (verb, r.returncode, r.stderr[-300:])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_value_flag_last():
    """R40 (#134, revising R38): a flag that takes a value, last on the line with nothing after it, is a usage error --
    "<verb>: <flag> needs a value", exit 2, R35's words -- before the verb runs. It was the verb's: twelve took the
    flag as unset and ran (`decision <q> <a> --invalidates` recorded the decision without its link), three asked REW
    (`capture-import <N> --bind`), the rest refused it in words of their own, exit 1. capture-protective's legs
    (`_LEG_FLAGS`) are the one exception: the verb parses them, and says "needs three values", exit 1. Every
    value-taking flag of every verb is swept, last after the arguments the verb needs (`_VERB_ARGS`): never 70, no
    traceback, nothing written. The cases come from the tables, so a verb or a flag added later is swept too. Run as
    processes on the dead port: a verb that went on could ask REW."""
    import shutil
    import tempfile
    cases = [(verb, flag) for verb, flags in VERB_FLAGS.items() for flag in flags if flag not in _FLAGS_WITHOUT_VALUE]
    top = tempfile.mkdtemp(prefix="autosound_process_flag_last_")
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["a_1 (sw)"])
        before = _project_bytes(d)
        failures = []
        for verb, flag in cases:
            argv = [verb, *["1"] * len(_VERB_ARGS[verb]), flag]
            r = _cli_env(d, argv)
            leg = flag in _LEG_FLAGS.get(verb, ())
            code, said = (EXIT_NO, f"{flag} needs three values") if leg else (EXIT_USAGE, f"{verb}: {flag} needs a value")
            if r.returncode != code or said not in r.stderr or "Traceback" in r.stderr:
                failures.append(f"{' '.join(argv)}: exit {r.returncode}, "
                                f"{(r.stderr.strip() or r.stdout.strip()).splitlines()[-1:]}")
        assert not failures, f"{len(failures)} of {len(cases)}:\n  " + "\n  ".join(failures)
        assert _project_bytes(d) == before, "a value flag left last wrote something"
    finally:
        shutil.rmtree(top, ignore_errors=True)


#: Every flag TCC sends to this command line, by verb -- read from tcc fd11ba9: `core/process_writer.py` (add_step,
#: skip_step, record_reviewer, set_protective / amend_protective, record_listening_verdict, listening_verdicts,
#: record_decision, start_capture, check_captures) and `core/handoff.py` (handoff). Each must be one `VERB_FLAGS`
#: gives that verb, or TCC's call is refused as a usage error, exit 2 (#134, N19).
_TCC_FLAGS = (
    ("add-step", "--project"),
    ("skip", "--superseded-by"),
    ("reviewer", "--review"), ("reviewer", "--mode"),
    ("capture-protective", "--hp"), ("capture-protective", "--lp"), ("capture-protective", "--source"),
    ("capture-protective", "--amend"), ("capture-protective", "--reason"),
    ("listening-verdict", "--pair"), ("listening-verdict", "--text"), ("listening-verdict", "--route"),
    ("listening-verdict", "--ledger-version"), ("listening-verdict", "--note"),
    ("listening-verdicts", "--track"), ("listening-verdicts", "--characteristic"),
    ("listening-verdicts", "--ledger-version"),
    ("decision", "--invalidates"),
    ("capture-start", "--plan"), ("capture-start", "--optional"), ("capture-start", "--start"),
    ("capture-start", "--step"), ("capture-start", "--origin"),
    ("capture-check", "--session"),
    ("handoff", "--json"),
)


def _check_flags_tcc_sends():
    """Every flag TCC sends is one its verb takes (#134, N19), and the two TCC sends as `--flag=value` (`reviewer`'s
    `--review=` and `--mode=`, `decision`'s `--invalidates=`) are read as the flag and its value."""
    import shutil
    import tempfile
    unknown = [(verb, flag) for verb, flag in _TCC_FLAGS if flag not in VERB_FLAGS.get(verb, ())]
    assert not unknown, f"flags TCC sends that their verb would refuse: {unknown}"
    top = tempfile.mkdtemp(prefix="autosound_process_tcc_flags_")
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        rc, _, err = _run_main(["process.py", d, "reviewer", "Gemini", "g-3", "-1.1",
                                "--review=process/reviews/2026-10-07T10-00-00-critic.md", "--mode=clipboard"])
        assert rc == 0, err
        got = Process(d).load()["reviewer"]
        assert (got["step"], got["review"], got["mode"]) == \
            ("-1.1", "process/reviews/2026-10-07T10-00-00-critic.md", "clipboard"), got
        rc, _, err = _run_main(["process.py", d, "decision", "keep the 48 kHz baseline?", "no", "-1.1",
                                "--invalidates=w-L_1 (sw)"])
        assert rc == 0, err
        said = [e for e in Process(d).events() if e.get("type") == EV_USER_DECISION][-1]
        assert (said["question"], said["answer"], said["step"], said["invalidates"]) == \
            ("keep the 48 kHz baseline?", "no", "-1.1", "w-L_1 (sw)"), said
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_help_writes_nothing():
    """#138 I-15: `<verb> --help` prints that verb's lines and writes nothing -- for every verb. It ran the verb:
    `session-close --help` recorded a close, `capture-start --help` opened `cap_001 at --help` and wrote its plan,
    `decision --help` and `target --help` exited 1 with "list index out of range". `process.py --help` and
    `<dir> --help` print the whole text on stdout, exit 0; an unknown verb prints it on stderr, exit 2."""
    import ast
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_help_")
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["a (sw)"])
        src = open(os.path.abspath(__file__), encoding="utf-8").read()
        main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_main")
        verbs = sorted({c.comparators[0].value for c in ast.walk(main)
                        if isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) and c.left.id == "cmd"
                        and isinstance(c.comparators[0], ast.Constant)})
        assert set(verbs) == set(VERB_FLAGS), ("the dispatcher's verbs and VERB_FLAGS differ",
                                               sorted(set(verbs) ^ set(VERB_FLAGS)))
        before = _project_bytes(d)
        for verb in verbs:
            r = _cli_env(d, [verb, "--help"])
            # The verb's OWN lines -- each entry `_USAGE` heads with it -- not its name anywhere: `done` is in the
            # exit table's "0 done", so a `done --help` that printed the table alone passed.
            own = [line for line in _USAGE.splitlines() if line.startswith(f"  {verb} ") or line == f"  {verb}"]
            assert own and r.returncode == 0 and all(line in r.stdout.splitlines() for line in own), \
                (verb, own, r.returncode, r.stdout[:300], r.stderr[-200:])
            assert "exit  0 done" in r.stdout and "usage: process.py" not in r.stdout, (verb, r.stdout[-300:])
            missing = [f for f in VERB_FLAGS[verb] if f not in r.stdout]
            assert not missing, f"{verb} --help does not name {missing}"
        assert _project_bytes(d) == before, "a --help wrote to the project"
        # Anywhere but right after the verb, `--help` and `-h` are a usage error and run nothing: `-h` was data there --
        # `capture-start 1 -h` opened a round expecting a capture titled "-h", a reason became "-h". Where a flag's
        # value stands they are among the verb's own flags (R41): the value is missing.
        asked = "is asked right after the command"
        for argv, said in ((["capture-start", "1", "-h"], asked), (["capture-skip", "a (sw)", "-h"], asked),
                           (["capture-start", "1", "--help"], asked), (["capture-close", "done in the car", "-h"], asked),
                           (["listening-verdict", "--pair", "CarMus#07:c09:ok", "--text", "-h"],
                            "listening-verdict: --text needs a value"),
                           (["capture-start", "1", "--optional", "--help"], "capture-start: --optional needs a value")):
            rc, out, err = _run_main(["process.py", d, *argv])
            assert rc == EXIT_USAGE and said in err and not out, (argv, rc, err, out)
        assert _project_bytes(d) == before, "a help asked out of place wrote to the project"
        for argv in (["process.py", "--help"], ["process.py", "-h"], ["process.py", d, "--help"],
                     ["process.py", d, "-h"]):
            rc, out, err = _run_main(argv)
            assert rc == 0 and out.startswith("usage: process.py") and "exit  0 done" in out and not err, (argv, rc)
        rc, out, err = _run_main(["process.py", d, "target", "-h"])
        assert rc == 0 and "target <preset> <curve>" in out and "capture-start" not in out, (rc, out, err)
        rc, out, err = _run_main(["process.py", d, "no-such-verb"])
        assert rc == 2 and not out and err.startswith("usage: process.py"), (rc, out, err[:200])
        assert _project_bytes(d) == before, "a usage answer wrote to the project"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_usage_before_the_read():
    """The usage answers come before the strict read (#134, #136): on a state that cannot be read, `--help` still
    answers (0) and an unknown verb or flag is still a usage error (2) -- they exited 1, blaming the file -- with
    the state as it was and no journal written."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_usage_first_")
    try:
        content = _UNREADABLE["truncated"]
        d = _state_dir_with(content, top)
        for argv, code, stream, said in ((["--help"], 0, "out", "usage: process.py"),
                                         (["show", "--help"], 0, "out", "show"),
                                         (["capture-start", "-h"], 0, "out", "capture-start"),
                                         (["no-such-verb"], 2, "err", "usage: process.py"),
                                         (["capture-start", "1", "--origni", "x"], 2, "err", "--origni"),
                                         (["capture-check", "--session=yes"], 2, "err", "--session"),
                                         (["target", "FULL"], 2, "err", "target needs <preset> <curve>")):
            rc, out, err = _run_main(["process.py", d, *argv])
            text = out if stream == "out" else err
            assert rc == code and said in text, (argv, rc, (err or out)[-200:])
            assert "process-state.json" not in err, (argv, "the usage answer blamed the file", err[-200:])
            with open(os.path.join(d, "process-state.json"), "rb") as f:
                assert f.read() == content, f"{argv}: the state changed"
            assert not os.path.exists(os.path.join(d, "journal.jsonl")), f"{argv}: a journal was written"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_handoff_says_an_unreadable_changelog():
    """`handoff` says a `tuning-changelog` it cannot read (#134, H 15): one in another code page, or one that cannot be
    opened, is an item in `missing` naming the file and why -- the ▶️ CONTINUE block in it cannot be checked. It read
    as no changelog at all, "no opinion", and the handoff passed over a block nobody could see."""
    import shutil
    import stat
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_changelog_")
    try:
        root = tempfile.mkdtemp(dir=top)
        _seed_intake(root)
        p = Process(os.path.join(root, "process"))
        p.enter_phase("-1")
        p.enter_phase("0")
        assert p.handoff()["ok"] is True, p.handoff()["missing"]
        path = os.path.join(root, "tuning-changelog.md")
        with open(path, "wb") as f:
            f.write("# Журнал\n\n## ▶️ CONTINUE\n- HEAD v_001\n".encode("utf-8"))
        assert p.handoff()["ok"] is True, ("a readable block", p.handoff()["missing"])
        with open(path, "wb") as f:
            f.write("# Журнал налаштування\n\n## CONTINUE\n- HEAD v_001, далі A/B\n".encode("cp1251"))
        got = p.handoff()
        said = [m for m in got["missing"] if path in m]
        assert got["ok"] is False and said and "is not UTF-8" in said[0] and "CONTINUE" in said[0], got
        rc, out, err = _run_main(["process.py", p.dir, "handoff", "--json"])
        answer = json.loads(out)
        assert rc == 1 and answer["ok"] is False and any(path in m for m in answer["missing"]), (rc, out, err)
        if _mode_refuses("a mode-0 changelog at handoff"):
            with open(path, "wb") as f:
                f.write("## ▶️ CONTINUE\n".encode("utf-8"))
            os.chmod(path, 0)
            try:
                got = p.handoff()
            finally:
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            said = [m for m in got["missing"] if path in m]
            assert got["ok"] is False and said and "cannot be opened" in said[0], got
            # The advice is the errno's (m2, as H minor 3): closing an editor cannot mend a permission.
            assert "close what holds it" not in said[0] and _project_io()._REPAIR_PERMISSION in said[0], said[0]
        real_name = os.name
        os.name = "nt"                                   # a program holding it, as Windows refuses the open
        try:
            with _Held(path):
                got = p.handoff()
        finally:
            os.name = real_name
        said = [m for m in got["missing"] if path in m]
        assert got["ok"] is False and said and "cannot be opened" in said[0] and "close what holds it" in said[0], got
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_superseded_not_taken():
    """N17 (#134): a superseded row is a typo's trace, not a measurement -- in every reader of `taken`. One checked
    and passed under the wrong title counted as taken and usable: in the step gate's list, in the closing event, in
    the counts `session-close` and `capture-close` print, and in `capture-check`'s lines, as OK."""
    import shutil
    import tempfile

    class Verifier:
        def verify(self, titles):
            return [{"name": t, "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}}
                    for t in titles]

    top = tempfile.mkdtemp(prefix="autosound_process_superseded_")
    real = Process._load_verifier
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["a (sw)"])
        p.record_capture("a (sw)")
        p.check_captures(["a (sw)"], verifier=Verifier())        # checked and passed, under the wrong title
        p.supersede_capture("a (sw)", "a2 (sw)", "typed a for a2")
        assert "a (sw)" in p.unusable_captures(), p.unusable_captures()
        assert p.open_work()["capture_round"]["taken"] == 1, p.open_work()
        Process._load_verifier = lambda self: Verifier()
        rc, out, err = _run_main(["process.py", d, "capture-check", "a2 (sw)"])
        assert "UNUSABLE a (sw) — superseded by a2 (sw)" in out.splitlines(), out
        assert rc == 1 and "0/1 придатні" in out, (rc, out, err)
        rc, out, err = _run_main(["process.py", d, "capture-close", "--no-rew"])
        assert rc == 0 and "closed: 1 taken" in out, (rc, out, err)
        closed = [e for e in p.events() if e.get("type") == EV_CAPTURE_CLOSED][-1]
        assert closed["taken"] == ["a2 (sw)"], closed
        # ...nor is it the setup the car was left in, nor a channel the round captured.
        round_ = {"expected": ["m-L_1 (sw)"],
                  "taken": {"m-L_1 (rta)": {"at": "2026-10-07T10:00:00"},
                            "r-R_1 (sw)": {"at": "2026-10-07T10:05:00", "superseded_by": "m-L_1 (sw)"},
                            "m-L_1 (sw)": {"at": "2026-10-07T10:04:00"}}}
        assert _last_method_taken(round_) == ("sw", "m-L_1 (sw)"), _last_method_taken(round_)
        try:
            _refuse_channel_outside_round(round_, "r-R")
        except ProcessError:
            pass
        else:
            raise AssertionError("a superseded row let the round record a channel it never captured")
    finally:
        Process._load_verifier = real
        shutil.rmtree(top, ignore_errors=True)


def _check_close_says_what_rew_did():
    """`capture-close` says which REW it closed without (#134): REW down is "REW not reached", REW answering something
    that is no measurement list is said so -- it was "REW not reached" too -- and either way the round closes on the
    record alone, exit 0. With REW's list read, the checks it runs are run on what the round took and still stands
    by, never on a superseded row (N17)."""
    import shutil
    import tempfile
    rew_api = _siblings().load("rew_api.py")
    real, real_verifier = rew_api.get_measurements, Process._load_verifier
    top = tempfile.mkdtemp(prefix="autosound_process_close_rew_")
    try:
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["m-L_1 (sw)"])
        p.record_capture("m-L_1 (sw)")
        p.supersede_capture("m-L_1 (sw)", "m-R_1 (sw)", "the channel was mislabelled")
        asked = []

        class Verifier:
            def verify(self, titles):
                asked.extend(titles)
                return [{"name": t, "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}}
                        for t in titles]
        rew_api.get_measurements = lambda: {"1": {"title": "m-R_1 (sw)"}}
        Process._load_verifier = lambda self: Verifier()
        rc, out, err = _run_main(["process.py", d, "capture-close"])
        assert rc == 0 and asked == ["m-R_1 (sw)"] and "checks run on 1 taken capture(s)" in out \
            and "closed: 1 taken" in out, (rc, asked, out, err)
        for exc, said in ((rew_api.RewUnavailable("refused", "http://127.0.0.1:1/measurements"), "REW not reached"),
                          (rew_api.RewProtocolError("REW's measurement list is not a map of measurements: list"),
                           "REW answered something that is not a measurement list")):
            d = os.path.join(tempfile.mkdtemp(dir=top), "process")
            Process(d).enter_phase("-1")
            Process(d).start_capture("1", expected=["a (sw)"])

            def answer(_exc=exc):
                raise _exc
            rew_api.get_measurements = answer
            rc, out, err = _run_main(["process.py", d, "capture-close"])
            assert rc == 0 and said in out and "not checked against REW" in out, (type(exc).__name__, rc, out, err)
            assert f"({type(exc).__name__}: " in out, ("the line names what was raised", out)
            if "not reached" not in said:
                assert "REW not reached" not in out, out

        # REW answered its list, then stopped before the checks: the round closes on the record, unchecked -- said
        # so, with what was raised. It said "run capture-check again", and the round it would run on was closing.
        class Dropped:
            def verify(self, titles):
                return [{"name": t, "exists": True, "reachable": False, "valid": False,
                         "issues": ["REW unavailable while reading the frequency response: refused"], "stats": {}}
                        for t in titles]
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["m-L_1 (sw)"])
        rew_api.get_measurements = lambda: {"1": {"title": "m-L_1 (sw)"}}
        Process._load_verifier = lambda self: Dropped()
        rc, out, err = _run_main(["process.py", d, "capture-close"])
        assert rc == 0 and "checks not run on the taken captures (RewUnavailableError: REW did not answer" in out \
            and "the round closes on the record, unchecked" in out and "capture-check again" not in out \
            and "closed: 1 taken" in out, (rc, out, err)
        Process._load_verifier = lambda self: Verifier()
        # A superseded row whose title REW still holds -- the typo not yet renamed there -- is skipped by the
        # reconcile (N17): it was "1 taken beyond it", in the record's `extra` and the close's.
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["m-L_1 (sw)"])
        p.record_capture("m-R_1 (sw)")
        p.supersede_capture("m-R_1 (sw)", "m-L_1 (sw)", "typed R for L")
        rew_api.get_measurements = lambda: {"1": {"title": "m-L_1 (sw)"}, "2": {"title": "m-R_1 (sw)"}}
        rc, out, err = _run_main(["process.py", d, "capture-close"])
        round_ = p.load()["capture"]
        assert rc == 0 and "1 of 1 on the list held, 0 taken beyond it" in out and "closed: 1 taken" in out, \
            (rc, out, err)
        assert round_["reconciled"]["extra"] == [] and round_["closed_against"]["extra"] == [], round_
        assert round_["taken"]["m-R_1 (sw)"]["superseded_by"] == "m-L_1 (sw)", round_["taken"]
        # ...and a superseded title on the list that REW holds under it is not held for the round: no rename named
        # for it, no `as_in_rew` written on the row, not counted among the held.
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["m-L_1 (sw)", "m-R_1 (sw)"])
        p.record_capture("m-L_1 (sw)")
        p.supersede_capture("m-L_1 (sw)", "m-R_1 (sw)", "typed L for R")
        verdict = p.reconcile_captures(["m-L_01 (sw)"])
        round_ = p.load()["capture"]
        assert verdict["matched"] == {} and verdict["renames"] == {} and round_["reconciled"]["matched"] == 0, \
            (verdict, round_["reconciled"])
        assert "as_in_rew" not in round_["taken"]["m-L_1 (sw)"], round_["taken"]
    finally:
        rew_api.get_measurements, Process._load_verifier = real, real_verifier
        shutil.rmtree(top, ignore_errors=True)


def _check_check_never_invents_taken():
    """T-1 (#134): a check records a verdict for every title (`round.checks`), and creates a `taken` row only for a
    title REW holds (#77) -- a title REW does not hold stays outstanding; a row already there is updated. A check
    whose listing of REW was not read records nothing at all (H I-6): REW answering the list with an error is 1, and
    it was recorded as REW's verdict on every title -- `checks` with `exists` null, a `capture_verified` naming each
    in `bad`; REW not answering is 69."""
    import shutil
    import tempfile

    class Verifier:
        def verify(self, titles):
            return [{"name": "a (sw)", "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}},
                    {"name": "b (sw)", "exists": False, "reachable": True, "valid": False,
                     "issues": ["No measurement titled 'b (sw)' (REW holds 1)"], "stats": {}}]

    class Unread:                              # REW answered an error: whether it holds the title is not known
        def verify(self, titles):
            return [{"name": t, "exists": None, "reachable": True, "valid": False,
                     "issues": ["REW answered an error: HTTP Error 500"], "stats": {}} for t in titles]

    class Down:                                # REW stopped answering after its list: nothing may be recorded
        def verify(self, titles):
            return [{"name": "a (sw)", "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}},
                    {"name": "b (sw)", "exists": True, "reachable": False, "valid": False,
                     "issues": ["REW unavailable while reading the frequency response: refused"], "stats": {}}]

    top = tempfile.mkdtemp(prefix="autosound_process_no_invention_")
    real = Process._load_verifier
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["a (sw)", "b (sw)"])
        p.check_captures(verifier=Verifier())
        round_ = Process(d).load()["capture"]
        assert "a (sw)" in round_["taken"] and "b (sw)" not in round_["taken"], round_["taken"]
        assert round_["taken"]["a (sw)"]["planned"] is True and round_["taken"]["a (sw)"]["verified"]["ok"], round_
        assert round_["checks"]["b (sw)"]["exists"] is False and round_["checks"]["a (sw)"]["ok"] is True, round_
        assert "b (sw)" in p.capture_outstanding(), p.capture_outstanding()
        Process._load_verifier = lambda self: Verifier()
        rc, out, err = _run_main(["process.py", d, "capture-check"])
        lines = out.splitlines()
        assert "UNUSABLE b (sw) — No measurement titled 'b (sw)' (REW holds 1)" in lines and "OK      a (sw)" in lines \
            and rc == 1, (rc, out, err)
        before = _project_bytes(d)
        try:
            p.check_captures(["a (sw)", "b (sw)"], verifier=Unread())
        except ProcessError as exc:
            assert getattr(exc, "exit_code", EXIT_NO) == EXIT_NO and str(exc) == (
                "REW's measurement list was not read (REW answered an error: HTTP Error 500) -- nothing was "
                "recorded"), str(exc)
        else:
            raise AssertionError("a check whose listing of REW was not read was recorded as REW's verdict")
        assert _project_bytes(d) == before, "a listing that was not read wrote something"
        p.record_capture("b (sw)")                               # taken by hand: a check updates the row
        p.check_captures(["b (sw)"], verifier=Verifier())
        round_ = Process(d).load()["capture"]
        assert round_["taken"]["b (sw)"]["verified"]["exists"] is False, round_["taken"]["b (sw)"]
        before = _project_bytes(d)
        try:
            p.check_captures(verifier=Down())
        except ProcessError as exc:
            assert getattr(exc, "exit_code", None) == EXIT_REW_UNAVAILABLE and "nothing was recorded" in str(exc) \
                and "refused" in str(exc), str(exc)
        else:
            raise AssertionError("a check with REW down recorded its verdicts")
        assert _project_bytes(d) == before, "a check with REW down wrote something"
    finally:
        Process._load_verifier = real
        shutil.rmtree(top, ignore_errors=True)


def _check_listing_never_read_as_rew():
    """A listing read that never reached REW is never recorded as REW's answer (#134, H I-6, H I-5), and the verb
    exits by its state. `REW_API_URL` that is no address, through the real `verify` and `rew_api`: `capture-check`
    is 1 with the address's words, where it was 69 ("start REW", which mends no typo), `capture-close` is 1 with the
    round left open, where it closed it unchecked, and `capture-import <N>` asking REW itself is 1. REW answering the
    list with an error: `capture-check` is 1 with REW's words, where every title was recorded as its verdict. A bug
    in reading the list is 70 with its traceback. Each writes nothing."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_listing_unread_")
    real = Process._load_verifier
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["a (sw)"])
        before = _project_bytes(d)
        address = ("REW_API_URL 'localhost:4735' is not an address: it does not start with http:// or https:// — "
                   "set it right, or unset it for REW's default (http://localhost:4735)")
        for argv in (["capture-check"], ["capture-close"],
                     ["capture-import", "1", "--bind", "=v_001", "--knob", "SubRC=4/4"]):
            r = _cli_env(d, argv, REW_API_URL="localhost:4735")
            assert r.returncode == EXIT_NO and address in r.stderr and "Traceback" not in r.stderr \
                and "start REW" not in r.stderr and "closing on the record alone" not in r.stdout, \
                (argv, r.returncode, r.stdout[-300:], r.stderr[-400:])
            assert _project_bytes(d) == before, f"{argv[0]}: an address that is none wrote something"
        assert not Process(d).load()["capture"].get("closed"), "the round closed over an address that is none"

        class Answered:                        # REW answered its list with an error: no title was read
            def verify(self, titles):
                return [{"name": t, "exists": None, "reachable": True, "valid": False, "stats": {},
                         "issues": ["REW answered an error: HTTP Error 500: Internal Server Error -- REW said: boom"]}
                        for t in titles]

        class Buggy:                           # the listing's reader broke: no verdict at all
            def verify(self, titles):
                raise TypeError("a bug in the listing's reader")
        for verifier, code, said in (
                (Answered(), EXIT_NO, "error: REW's measurement list was not read (REW answered an error: HTTP Error "
                                      "500: Internal Server Error -- REW said: boom) -- nothing was recorded"),
                (Buggy(), EXIT_UNEXPECTED, "error: unexpected TypeError: a bug in the listing's reader")):
            Process._load_verifier = lambda self, _verifier=verifier: _verifier
            rc, out, err = _run_main(["process.py", d, "capture-check"])
            assert rc == code and said in err and ("Traceback" in err) is (code == EXIT_UNEXPECTED) \
                and not out.strip(), (type(verifier).__name__, rc, out, err[-400:])
            assert _project_bytes(d) == before, f"{type(verifier).__name__}: a listing nobody read wrote something"
    finally:
        Process._load_verifier = real
        shutil.rmtree(top, ignore_errors=True)


def _check_ambiguous_capture():
    """A title REW holds twice is its own verdict in the round too (#134, H I-8, T m4), through the real `verify`:
    REW holds it, so the check takes it -- a `taken` row, `exists` true -- where it was left outstanding as nobody's
    measurement and the tuner measured a third copy; and it is not usable until it is renamed. `capture-check` says
    AMBIGUOUS with the count on an UNUSABLE line, in the form TCC's strip reads (`UNUSABLE <title> — `, R57), exit 1;
    the step gate counts it unusable, and `--session` counts it apart."""
    import contextlib
    import io as _io
    import shutil
    import tempfile
    api = _load_sibling("verify.py")._api
    real = api.get_measurements
    top = tempfile.mkdtemp(prefix="autosound_process_ambiguous_")
    try:
        api.get_measurements = lambda: {"1": {"title": "a (sw)", "uuid": "u1"}, "2": {"title": "a (sw)", "uuid": "u2"}}
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["a (sw)"])
        with contextlib.redirect_stdout(_io.StringIO()):
            p.check_captures()
        round_ = Process(d).load()["capture"]
        verified = (round_["taken"].get("a (sw)") or {}).get("verified") or {}
        assert verified.get("ambiguous") == 2 and verified["exists"] is True and verified["ok"] is False, round_
        assert round_["checks"]["a (sw)"].get("ambiguous") == 2, round_["checks"]
        assert p.capture_outstanding() == [] and p.unusable_captures() == ["a (sw)"], \
            (p.capture_outstanding(), p.unusable_captures())
        rc, out, err = _run_main(["process.py", d, "capture-check", "--session"])
        said = [line for line in out.splitlines() if "a (sw)" in line and not line.startswith(" ")]
        # An UNUSABLE line, so TCC's strip shows it with no change of TCC's (R57): it keeps the lines that start
        # `UNUSABLE <title> — ` for a title it handed in (`main_window._on_capture_check_done`). AMBIGUOUS and the
        # count ride in the reason.
        assert rc == EXIT_NO and len(said) == 1 and said[0].startswith("UNUSABLE a (sw) — ") \
            and "AMBIGUOUS" in said[0] and "REW holds 2 measurements" in said[0], (rc, out, err)
        assert said[0] == ("UNUSABLE a (sw) — AMBIGUOUS: REW holds 2 measurements under this title; rename so titles "
                           "are unique, then run capture-check again"), said
        assert "titles, 0 usable, 0 missing, 0 unusable, 1 ambiguous" in out, out
    finally:
        api.get_measurements = real
        shutil.rmtree(top, ignore_errors=True)


def _check_close_swallows_only_rew():
    """`capture-close` closes on the record alone over REW's own states only (#134, T I4, F M-11, H minor 5, T m17):
    REW down, REW answering something that is no measurement list, and REW answering an error -- an `HTTPError`,
    untested before, said as "not read against REW" -- each named, exit 0 (the design). Anything else is raised
    before a line is printed: the state refused at the reconcile's own read (the round closed, unchecked, under
    "not read against REW" -- T I4's probe), the reconcile's own refusal, an address that is none -- exit 1, the
    round open, nothing written -- and a bug, 70 with its traceback."""
    import contextlib
    import shutil
    import tempfile
    import urllib.error
    global _load_naming
    rew_api = _siblings().load("rew_api.py")
    real_list, real_naming = rew_api.get_measurements, _load_naming
    top = tempfile.mkdtemp(prefix="autosound_process_close_only_rew_")

    def fresh():
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["m-L_1 (sw)"])
        return d

    def answer(exc):
        def listing():
            raise exc
        return listing

    class Misaddressed(ValueError):          # `rew_api.RewAddressError`, as any copy raises it
        rew_state = "config"
    try:
        d = fresh()
        rew_api.get_measurements = answer(urllib.error.HTTPError(
            "http://127.0.0.1:1/measurements", 500, "Internal Server Error -- REW said: boom", {}, None))
        rc, out, err = _run_main(["process.py", d, "capture-close"])
        assert rc == EXIT_OK and "REW answered with an error (HTTPError: HTTP Error 500: Internal Server Error -- REW " \
            "said: boom): closing on the record alone" in out and "not checked against REW" in out \
            and Process(d).load()["capture"].get("closed"), (rc, out, err)

        def refused_at_the_reconcile(n, read):          # `_main`'s read is the first; the reconcile's own, the second
            if n == 2:
                raise _project_io().Unreadable(os.path.join(d, "process-state.json"),
                                               "cannot be opened (held a moment by another writer)",
                                               "close what holds it and run again")
            return read()
        cases = (   # (what fails, the listing REW gives, the state's reads, naming, the exit, what stderr says)
            ("a read refused at the reconcile", lambda: {"1": {"title": "m-L_1 (sw)"}}, refused_at_the_reconcile,
             real_naming, EXIT_NO, "cannot be opened (held a moment by another writer)"),
            ("the reconcile's own refusal", lambda: {"1": {"title": "m-L_1 (sw)"}}, None, lambda: None, EXIT_NO,
             "naming.py could not be loaded"),
            ("an address that is none", answer(Misaddressed("REW_API_URL 'localhost:4735' is not an address: it "
                                                            "does not start with http:// or https://")),
             None, real_naming, EXIT_NO, "error: REW_API_URL 'localhost:4735' is not an address"),
            ("a bug", answer(TypeError("a bug in the listing's reader")), None, real_naming, EXIT_UNEXPECTED,
             "error: unexpected TypeError: a bug in the listing's reader"),
        )
        for what, listing, reads, naming, code, said in cases:
            d = fresh()
            rew_api.get_measurements, _load_naming = listing, naming
            before = _project_bytes(d)
            with (_StateReads(reads) if reads else contextlib.nullcontext()):
                rc, out, err = _run_main(["process.py", d, "capture-close"])
            _load_naming = real_naming
            assert rc == code and said in err and not out.strip() and ("Traceback" in err) is (code == EXIT_UNEXPECTED), \
                (what, rc, out, err[-400:])
            assert _project_bytes(d) == before and not Process(d).load()["capture"].get("closed"), \
                f"{what}: the round was closed, or something written"
    finally:
        rew_api.get_measurements, _load_naming = real_list, real_naming
        shutil.rmtree(top, ignore_errors=True)


def _check_round_lookups_read_the_state_strictly():
    """The round lookups the method's readers call read the live round strictly (#134, batch 2's re-review, Out of
    Scope 3): `under_for` (predict's default `--from-state`), `knobs_for` (the knobs when no journal round carries
    them) and `protective_record_for` (the open round, when the journal holds none) read `process-state.json`
    leniently behind their strict journal reads -- a state that cannot be read was an empty one, so predict read the
    solos "as they are" over a round taken under a ledger version (the chain applied twice, #57 P0). Each raises the
    read's `Unreadable` now. `protective_record()` -- TCC's, for a screen, and contract 1's -- stays lenient."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_lookups_")
    failures = []
    try:
        _seed_intake(top)                                  # a banked v_001 for the round to be taken under
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["w-L_1 (sw)"], under="v_001")
        p.set_knobs({"SubRC": "4/4"})
        assert p.under_for("1") == "v_001" and (p.knobs_for("1") or {}).get("knobs") == {"SubRC": "4/4"}, "fixture"
        with open(p.journal_path, "wb"):                   # no round in the journal: the live round is the answer
            pass
        assert p.protective_record_for("1") is not None and (p.knobs_for("1") or {}).get("knobs"), "fixture"
        with open(p.state_path, "rb") as f:
            whole = f.read()
        with open(p.state_path, "wb") as f:
            f.write(whole[: len(whole) // 2])
        for name, call in (("under_for", lambda: p.under_for("1")), ("knobs_for", lambda: p.knobs_for("1")),
                           ("protective_record_for", lambda: p.protective_record_for("1"))):
            try:
                got = call()
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                if not (getattr(type(exc), "is_unreadable", False) and str(exc).startswith(p.state_path + " ")):
                    failures.append(f"{name} raised {type(exc).__name__}: {exc}")
            else:
                failures.append(f"{name} read a state it could not read as {got!r}")
        assert p.protective_record() is None, "protective_record() is a screen's read: lenient, as contract 1 says"
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a round lookup read the state leniently:"] + failures)


def _check_naming_load_error_named():
    """Every refusal over a `naming.py` that cannot be loaded names why (#134, batch 1's re-review m4): its type and
    message -- a syntax error in it, numpy missing. `capture-import <N>` with no titles said it; the same import with
    titles, and capture-close's read against REW, said only "cannot be loaded"."""
    import shutil
    import tempfile
    global _load_naming
    real_naming = _load_naming
    top = tempfile.mkdtemp(prefix="autosound_process_naming_error_")
    failure = SyntaxError("invalid syntax (naming.py, line 3)")
    failures = []
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.start_capture("1", expected=["m-L_1 (sw)"])

        def broken():
            _LOAD_FAILURES["naming.py"] = failure
            return None
        _load_naming = broken
        named = "(SyntaxError: invalid syntax (naming.py, line 3))"
        for label, call in (("capture-import with titles", lambda: p.capture_import("1", ["m-L_1 (sw)"], {"": None},
                                                                                     {"SubRC": "4/4"})),
                            ("the read against REW", lambda: p.reconcile_captures(["m-L_1 (sw)"]))):
            try:
                call()
            except ProcessError as exc:
                if named not in str(exc):
                    failures.append(f"{label}: {exc}")
            else:
                failures.append(f"{label}: went through")
    finally:
        _load_naming = real_naming
        _LOAD_FAILURES.pop("naming.py", None)
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a naming.py that cannot be loaded, said without why:"] + failures)


def _check_evidence_verdicts_name_the_naming_load_error():
    """`done`, `check` and `handoff` over a `naming.py` that cannot be loaded name it and why (the final review's M2,
    batch 1's m4 form), never only the evidence: with no grammar a capture name resolves to nothing. `done` refused
    "none of it resolves ... a REW measurement name in the grammar" over a name that is one; `check` said a step
    closed on a capture while the grammar loaded is UNBACKED, and `handoff` that its evidence resolves to nothing,
    with no word of the load. Each still refuses -- nothing can vouch for the name -- and says the cause."""
    import shutil
    import tempfile
    global _load_naming
    real_naming = _load_naming
    top = tempfile.mkdtemp(prefix="autosound_process_naming_evidence_")
    said = ("naming.py could not be loaded (SyntaxError: invalid syntax (naming.py, line 12)) -- a capture name "
            "cannot be recognised")
    failures = []
    try:
        d = os.path.join(top, "process")
        p = Process(d)
        p.enter_phase("-1")
        p.add_step("0.1", "baseline sweeps")
        p.finish_step("0.1", ["w-L_1 (sw)"])             # closed while the grammar loads
        p.add_step("0.2", "more sweeps")

        def broken():
            _LOAD_FAILURES["naming.py"] = SyntaxError("invalid syntax (naming.py, line 12)")
            return None
        _load_naming = broken
        for argv in (["done", "0.2", "w-R_1 (sw)"], ["check"]):
            rc, out, err = _run_main(["process.py", d, *argv])
            if rc != EXIT_NO or said not in (out + err) or "Traceback" in err:
                failures.append(f"{argv[0]}: rc {rc}, out {out.strip()[-300:]!r}, err {err.strip()[-300:]!r}")
        missing = [m for m in Process(d).handoff()["missing"] if m.startswith("done steps whose evidence")]
        if not missing or said not in missing[0]:
            failures.append(f"handoff: {missing}")
        if Process(d).step(Process(d).load(), "0.2").get("status") == STEP_DONE:
            failures.append("done: the step was closed over evidence nothing could recognise")
    finally:
        _load_naming = real_naming
        _LOAD_FAILURES.pop("naming.py", None)
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a naming.py that cannot be loaded, the evidence blamed:"] + failures)


def _check_says_what_it_did_not_check():
    """A case this machine cannot make is said one line above the OK line, never passed in silence (the final review's
    m-5; the form siblings.py's selftest uses). Run as root a file's mode refuses nothing, so the four cases met for
    real through one -- a mode-0 journal, a read-only journal, a mode-0 changelog at handoff, a journal capture-close
    cannot open with REW down -- are skipped there, each recorded for that line. Made here with root faked."""
    saved = list(_NOT_CHECKED_HERE)
    real_euid = getattr(os, "geteuid", None)
    try:
        del _NOT_CHECKED_HERE[:]
        os.geteuid = lambda: 0
        for check in (_check_journal_that_cannot_be_opened, _check_event_refused_after_the_state,
                      _check_handoff_says_an_unreadable_changelog, _check_close_checks_stage_refusals):
            check()
    finally:
        if real_euid is None:
            del os.geteuid
        else:
            os.geteuid = real_euid
        said = [case for case, _why in _NOT_CHECKED_HERE]
        _NOT_CHECKED_HERE[:] = saved
    assert said == ["a mode-0 journal, met for real", "a read-only journal, met for real",
                    "a mode-0 changelog at handoff", "a journal capture-close cannot open, REW down"], said


def _check_capture_start_said_as_it_landed():
    """`capture-start` refused at a state write says what landed (the final review's M3): it wrote the state twice --
    the round, then its plan path -- and a second write refused (a Windows holder past the retries) said "it is as it
    was" over a state holding the open round, with no `capture_issued` in the journal; the next round then closed it
    as superseded, a close for a round never issued. Now the state is written once, and nothing goes to the journal
    before it -- the close of a round it supersedes neither. That close was appended first, W-8's order, and the
    refusal had to name it (`_check_capture_start_held_names_the_close_that_landed`); W-9 (J2b, #141) turned it round,
    and this check now runs with a round open before as well as without. Refused, the state and the journal are as
    they were, byte for byte. Through, the round is open, its plan path recorded, and its `capture_issued` in the
    journal after the close of the round it supersedes. And the journal refusing a line once the state landed says
    every line still owed, in order (F M-7): with the close's refused, the round's own is owed too."""
    import shutil
    import tempfile
    io_ = _project_io()
    real = io_.atomic_write_json
    real_event = Process._append_event
    top = tempfile.mkdtemp(prefix="autosound_process_capture_start_landed_")
    failures = []

    def held_at(n):
        """`atomic_write_json` with the `n`-th write of `process-state.json` refused, as a holder past the retries."""
        seen = []

        def write(path, data, *args, **kwargs):
            if os.path.basename(path) == "process-state.json":
                seen.append(path)
                if len(seen) == n:
                    raise PermissionError(13, "The process cannot access the file because it is being used by "
                                              "another process", path)
            return real(path, data, *args, **kwargs)
        return write

    def state_and_journal(p):
        out = {}
        for path in (p.state_path, p.journal_path):
            with open(path, "rb") as fh:
                out[path] = fh.read()
        return out
    try:
        for over in (None, "cap_001"):
            for refused_at in (1, 2):
                d = os.path.join(top, f"held-at-{refused_at}-over-{over}", "process")
                p = Process(d)
                p.enter_phase("-1")
                if over:
                    p.start_capture("1", expected=["w-L_1 (sw)"])
                before = state_and_journal(p)
                io_.atomic_write_json = held_at(refused_at)
                try:
                    rc, out, err = _run_main(["process.py", d, "capture-start", "1", "w-R_1 (sw)"])
                finally:
                    io_.atomic_write_json = real
                want = "cap_002" if over else "cap_001"
                round_ = Process(d).load().get("capture") or {}
                rounds = [(e.get("type"), e.get("capture")) for e in Process(d).events()
                          if e.get("type") in (EV_CAPTURE_ISSUED, EV_CAPTURE_CLOSED)]
                label = f"the state's write {refused_at} held, over {over or 'no round'}"
                if refused_at == 1:                     # the one state write: refused, nothing has landed anywhere
                    if rc != EXIT_NO or not err.rstrip().endswith("it is as it was") \
                            or state_and_journal(p) != before:
                        failures.append(f"{label}: rc {rc}, the state and the journal "
                                        f"{'as they were' if state_and_journal(p) == before else 'changed'}, "
                                        f"{rounds} -- {err.strip()[-200:]!r}")
                    continue
                landed = ([(EV_CAPTURE_ISSUED, "cap_001"), (EV_CAPTURE_CLOSED, "cap_001"), (EV_CAPTURE_ISSUED, want)]
                          if over else [(EV_CAPTURE_ISSUED, want)])
                if rc != EXIT_OK or round_.get("id") != want or round_.get("closed") or rounds != landed \
                        or round_.get("plan_path") != "docs/plans/_1-capture.md":
                    failures.append(f"{label}: rc {rc}, round {round_.get('id')!r} closed {round_.get('closed')!r}, "
                                    f"plan {round_.get('plan_path')!r}, the journal {rounds}, err "
                                    f"{err.strip()[-200:]!r}")
        # The journal refusing a line once the state landed (F M-7) says each line still owed, in order: the close of
        # the round superseded refused, the new round's `capture_issued` is owed after it, and nothing replays either.
        decoder = json.JSONDecoder()
        for refused in (EV_CAPTURE_CLOSED, EV_CAPTURE_ISSUED):
            d = os.path.join(top, f"journal-refuses-{refused}", "process")
            p = Process(d)
            p.enter_phase("-1")
            p.start_capture("1", expected=["w-L_1 (sw)"])
            with open(p.journal_path, "rb") as fh:
                journal = fh.read()

            def refusing(self, event_type, payload, refused=refused):
                if event_type == refused:
                    raise PermissionError(13, "Permission denied", self.journal_path)
                return real_event(self, event_type, payload)
            Process._append_event = refusing
            try:
                rc, out, err = _run_main(["process.py", d, "capture-start", "1", "w-R_1 (sw)"])
            finally:
                Process._append_event = real_event
            said, at = [], err.find('{"at"')
            while at != -1:
                event, end = decoder.raw_decode(err, at)
                said.append((event.get("type"), event.get("capture")))
                at = err.find('{"at"', end)
            owed = ([(EV_CAPTURE_CLOSED, "cap_001"), (EV_CAPTURE_ISSUED, "cap_002")] if refused == EV_CAPTURE_CLOSED
                    else [(EV_CAPTURE_ISSUED, "cap_002")])
            with open(p.journal_path, "rb") as fh:
                appended = [json.loads(line).get("type") for line in fh.read()[len(journal):].splitlines()
                            if line.strip()]
            round_ = Process(d).load().get("capture") or {}
            if rc != EXIT_NO or "Traceback" in err or "process-state.json is written, but its journal line" not in err \
                    or said != owed or round_.get("id") != "cap_002" \
                    or appended != ([] if refused == EV_CAPTURE_CLOSED else [EV_CAPTURE_CLOSED]):
                failures.append(f"the journal refusing {refused} after the state: rc {rc}, said {said}, appended "
                                f"{appended}, open {round_.get('id')!r} -- {err.strip()[-300:]!r}")
        # The plan file goes down only once the state's guards pass: a state damaged after the round's own read is
        # refused by `_write`'s guard, and nothing -- the plan's list included -- is left beside it.
        p = Process(_state_dir_with(_UNREADABLE["truncated"], top))
        before = _project_bytes(p.dir)
        with _StateReads(lambda n, read: _empty_state() if n == 1 else read()):
            try:
                p.start_capture("1", expected=["w-L_1 (sw)"])
            except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                if not getattr(type(exc), "is_unreadable", False):
                    failures.append(f"damaged after its read: raised {type(exc).__name__}: {exc}")
            else:
                failures.append("damaged after its read: the round opened")
        if _project_bytes(p.dir) != before:
            failures.append(f"damaged after its read: left {sorted(set(_project_bytes(p.dir)) - set(before))}")
    finally:
        io_.atomic_write_json = real
        Process._append_event = real_event
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["capture-start refused at a state write:"] + failures)


def _second_capture_start_held(top):
    """`cap_001` open on series 1, its plan file written; then a second `capture-start 1` whose one state write a holder
    refuses past the retries (`PermissionError` 13). Returns (exit code, stderr, the process, the open round's plan file
    before and after) -- the case of part A's re-review, N-1 and N-3."""
    io_ = _project_io()
    real = io_.atomic_write_json
    d = os.path.join(top, "process")
    p = Process(d)
    p.enter_phase("-1")
    p.start_capture("1", ["w-L_1 (sw)"])
    plan = os.path.join(p.project_dir, "docs", "plans", "_1-capture.md")
    with open(plan, "rb") as fh:
        before = fh.read()

    def held(path, data, *args, **kwargs):
        if os.path.basename(path) == "process-state.json":
            raise PermissionError(13, "The process cannot access the file because it is being used by another "
                                      "process", path)
        return real(path, data, *args, **kwargs)
    io_.atomic_write_json = held
    try:
        rc, _out, err = _run_main(["process.py", d, "capture-start", "1", "w-R_1 (sw)", "tw-R_1 (sw)"])
    finally:
        io_.atomic_write_json = real
    with open(plan, "rb") as fh:
        after = fh.read()
    return rc, err, Process(d), before, after


def _check_capture_start_held_names_the_close_that_landed():
    """`capture-start` over an open round closes that round, and a holder refuses its one state write (part A's
    re-review, N-1). The close was a journal event appended before that write, so the refusal said "it is as it was"
    over a journal that said closed, and a retry closed the round there a second time; W-8 had the refusal name that
    close, the order left to W-9. W-9 (J2b, #141) turned the order round: the close is in the state write and its
    event follows it. Refused now, no close has landed to name -- "it is as it was" is true of the journal too -- and
    the retry closes the round once."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_supersede_held_")
    try:
        rc, err, p, _before, _after = _second_capture_start_held(top)
        said = " ".join(err.split())
        round_ = p.load().get("capture") or {}

        def closes():
            return [(e.get("capture"), e.get("reason")) for e in p.events() if e.get("type") == EV_CAPTURE_CLOSED]
        assert rc == EXIT_NO, (rc, said)
        assert round_.get("id") == "cap_001" and not round_.get("closed"), round_
        assert closes() == [], closes()                       # nothing in the journal before the state (J2b)
        assert said.endswith("it is as it was") and "in the journal already" not in said, said
        rc, _out, err = _run_main(["process.py", p.dir, "capture-start", "1", "w-R_1 (sw)", "tw-R_1 (sw)"])
        round_ = p.load().get("capture") or {}
        assert rc == EXIT_OK and round_.get("id") == "cap_002" and not round_.get("closed"), (rc, round_, err)
        assert closes() == [("cap_001", "superseded")], f"the retry closed cap_001 {closes()}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_capture_start_held_leaves_the_open_rounds_plan():
    """The plan file goes down once the state is written (part A's re-review, N-3): written before the state's move, a
    move a holder refused left the plan of a round that never opened -- on the same series, over the open round's
    own `docs/plans/_1-capture.md`, which then listed the refused round's captures."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_plan_held_")
    try:
        rc, err, _p, before, after = _second_capture_start_held(top)
        assert rc == EXIT_NO, (rc, err)
        assert after == before, f"the open round's plan file, after a refused capture-start: {after[:160]!r}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_close_checks_stage_refusals():
    """capture-close's checks run after its read against REW, in an `except` that lets the close go on: REW stopping
    before them, or a bug in them, is said with its type and the round closes unchecked, exit 0 (as built). Two
    things there are not bugs, and are the verb's refusal now (#134, batch 3's re-review O3): exit 1, said whole, the
    round open. The state held at that stage -- the line said "the round closes on the record, unchecked" and the
    close went on over a read it could not make (or refused at the next one); and the checks' journal line refused
    after their state write landed -- "is written, but its journal line is not", cut to 160 characters with its line
    to append lost, and the round closed. The project's lock held past the wait there is 75, the round open (#141): the
    checks take their own hold, and a busy one is no reason to close unchecked -- said as what landed before it, the
    reconcile and maybe the checks (R9), never "nothing was written", which only the first hold may say. So is the
    round another writer replaced while the checks read REW: exit 1, the round as that writer left it, where it was
    "checks not run" and the close went on over the round that replaced it. And a `rew_api.py` that cannot be loaded
    refuses the close before anything is read or written, naming why and `--no-rew` (M1): it closed the round unchecked
    under "not read against REW"."""
    import shutil
    import tempfile
    global _load_sibling
    rew_api = _siblings().load("rew_api.py")
    real_list, real_verifier, real_check = rew_api.get_measurements, Process._load_verifier, Process.check_captures
    real_event, real_load, real_close = Process._append_event, _load_sibling, Process.close_capture
    top = tempfile.mkdtemp(prefix="autosound_process_close_checks_")

    class Verifier:
        def verify(self, titles):
            return [{"name": t, "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}}
                    for t in titles]

    class Buggy:
        def verify(self, titles):
            raise TypeError("a bug in the verifier")

    def fresh():
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["m-L_1 (sw)"])
        return d

    def held_during_checks(self, *args, **kwargs):
        def refused():
            raise _project_io().Unreadable(self.state_path, "cannot be opened (held by another writer)",
                                           "close what holds it and run again")
        self._read_state = refused
        try:
            return real_check(self, *args, **kwargs)
        finally:
            del self._read_state

    def journal_refuses_the_check(self, event_type, payload):
        if event_type == EV_CAPTURE_VERIFIED:
            raise PermissionError(13, "Permission denied", self.journal_path)
        return real_event(self, event_type, payload)
    failures = []
    try:
        rew_api.get_measurements = lambda: {"1": {"title": "m-L_1 (sw)"}}
        Process._load_verifier = lambda self: Verifier()
        for what, patch, said in (
                ("the state held at the checks", ("check_captures", held_during_checks),
                 "cannot be opened (held by another writer)"),
                ("the checks' journal line refused after their state write", ("_append_event", journal_refuses_the_check),
                 "is written, but its journal line is not")):
            d = fresh()
            setattr(Process, *patch)
            try:
                rc, out, err = _run_main(["process.py", d, "capture-close"])
            finally:
                Process.check_captures, Process._append_event = real_check, real_event
            closed = Process(d).load()["capture"].get("closed")
            if rc != EXIT_NO or said not in err or "the round closes on the record, unchecked" in out or closed:
                failures.append(f"{what}: rc {rc}, closed {closed!r}, out {out.strip()[-160:]!r}, err {err.strip()[-200:]!r}")
            if patch[0] == "_append_event" and f"append this line to {Process(d).journal_path}" not in err:
                failures.append(f"{what}: the line to append is not said: {err.strip()[-300:]!r}")
        # The project's lock held past the wait at a hold after the first (#141; R9): 75, the round left open -- never
        # closed unchecked because another writer held the lock for a moment -- and one line saying what landed: the
        # reconcile has, and the checks may have, so write_lock's own "nothing was written" would be false there. The
        # journal holds what the line says. The first hold's busy -- the close's own, REW not read -- keeps that line:
        # there it is true.
        lock = _write_lock()
        for what, argv, at, landed, said in (
                ("busy at the checks", [], "check_captures", [EV_CAPTURE_RECONCILED],
                 "the reconcile of cap_001 landed; the checks and the close did not; run capture-close again (the "
                 "reconcile is safe to repeat)"),
                ("busy at the close, the checks in", [], "close_capture", [EV_CAPTURE_RECONCILED, EV_CAPTURE_VERIFIED],
                 "the reconcile of cap_001 and its checks landed; the close did not; run capture-close again (the "
                 "reconcile and the checks are safe to repeat)"),
                ("busy at the close, its first hold", ["--no-rew"], "close_capture", [], None)):
            d = fresh()
            busy = lock.Busy(lock.lock_path(os.path.dirname(d)), 0.3)

            def busy_here(self, *args, busy=busy, **kwargs):
                raise busy
            n = len(Process(d).events())
            setattr(Process, at, busy_here)
            try:
                rc, out, err = _run_main(["process.py", d, "capture-close", *argv])
            finally:
                Process.check_captures, Process.close_capture = real_check, real_close
            want = str(busy) if said is None else f"busy: {busy.path} is held by another writer -- {said}"
            kinds = [e.get("type") for e in Process(d).events()[n:]]
            closed = Process(d).load()["capture"].get("closed")
            if rc != EXIT_BUSY or err.strip().splitlines()[-1:] != [want] or "closes on the record" in out or closed \
                    or kinds != landed:
                failures.append(f"{what}: rc {rc}, closed {closed!r}, the journal {kinds}, out {out.strip()[-160:]!r}, "
                                f"err {err.strip()[-300:]!r}")
        # Another writer replacing the round while the checks read REW (Task 2's review): the checks refuse, and the
        # verb with them -- exit 1, the round as the other writer left it, nothing closed, one line saying what landed.
        # The refusal was read as "checks not run", and the close went on over the round that replaced it, exit 0.
        d = fresh()
        n, raised = len(Process(d).events()), []

        class Replacing(Verifier):
            def verify(self, titles, d=d):
                raised.append(_from_another_thread(lambda: Process(d).start_capture("1", expected=["m-R_1 (sw)"])))
                return Verifier.verify(self, titles)
        Process._load_verifier = lambda self: Replacing()
        try:
            rc, out, err = _run_main(["process.py", d, "capture-close"])
        finally:
            Process._load_verifier = lambda self: Verifier()
        live = Process(d).load()["capture"]
        rounds = [(e.get("type"), e.get("capture")) for e in Process(d).events()[n:]
                  if e.get("type") in (EV_CAPTURE_RECONCILED, EV_CAPTURE_VERIFIED, EV_CAPTURE_CLOSED, EV_CAPTURE_ISSUED)]
        want = ("error: round cap_001 was closed or replaced by another writer while capture-close ran (cap_002 is the "
                "open round now) -- the reconcile of cap_001 landed; the checks and the close did not")
        if rc != EXIT_NO or err.strip().splitlines()[-1:] != [want] or "closes on the record" in out \
                or live.get("id") != "cap_002" or live.get("closed") or raised != [None] \
                or rounds != [(EV_CAPTURE_RECONCILED, "cap_001"), (EV_CAPTURE_CLOSED, "cap_001"),
                              (EV_CAPTURE_ISSUED, "cap_002")]:
            failures.append(f"the round replaced while the checks read REW: rc {rc}, open {live.get('id')!r} closed "
                            f"{live.get('closed')!r}, the journal {rounds}, the other writer {raised}, out "
                            f"{out.strip()[-160:]!r}, err {err.strip()[-300:]!r}")
        # A journal the close cannot append to is refused before a line is printed (batch 2's re-review, Out of Scope
        # 5): with REW down, "REW not reached ...: closing on the record alone" was printed, and then the close refused.
        if _mode_refuses("a journal capture-close cannot open, REW down"):
            d = fresh()

            def down():
                raise rew_api.RewUnavailable(ConnectionRefusedError(61, "Connection refused"),
                                             "http://127.0.0.1:1/measurements")
            rew_api.get_measurements = down
            journal = Process(d).journal_path
            os.chmod(journal, 0)
            try:
                rc, out, err = _run_main(["process.py", d, "capture-close"])
            finally:
                os.chmod(journal, 0o644)
                rew_api.get_measurements = lambda: {"1": {"title": "m-L_1 (sw)"}}
            if rc != EXIT_NO or out.strip() or f"error: {journal} cannot be opened" not in err \
                    or Process(d).load()["capture"].get("closed"):
                failures.append(f"a journal that cannot be opened, REW down: rc {rc}, out {out.strip()[-200:]!r}, "
                                f"err {err.strip()[-200:]!r}")
        # A bug in the checks is still said with its type, and the round closes unchecked (as built).
        d = fresh()
        Process._load_verifier = lambda self: Buggy()
        rc, out, err = _run_main(["process.py", d, "capture-close"])
        if rc != EXIT_OK or "checks not run on the taken captures (TypeError: a bug in the verifier)" not in out \
                or not Process(d).load()["capture"].get("closed"):
            failures.append(f"a bug in the checks: rc {rc}, out {out.strip()[-200:]!r}")
        # rew_api.py that cannot be loaded (M1): refused before anything is read or written.
        d = fresh()
        before = _project_bytes(d)

        def no_rew_api(name):
            if name == "rew_api.py":
                _LOAD_FAILURES[name] = ImportError("No module named 'numpy'")
                return None
            return real_load(name)
        _load_sibling = no_rew_api
        try:
            rc, out, err = _run_main(["process.py", d, "capture-close"])
        finally:
            _load_sibling = real_load
            _LOAD_FAILURES.pop("rew_api.py", None)
        if rc != EXIT_NO or out.strip() or _project_bytes(d) != before or Process(d).load()["capture"].get("closed") \
                or not err.strip().startswith("error: rew_api.py could not be loaded (ImportError: No module named "
                                              "'numpy') -- the round cannot be read against REW, and nothing was "
                                              "written; `capture-close --no-rew` closes it on the record alone"):
            failures.append(f"rew_api.py not loaded: rc {rc}, out {out.strip()[-160:]!r}, err {err.strip()[-300:]!r}")
    finally:
        rew_api.get_measurements, Process._load_verifier = real_list, real_verifier
        Process.check_captures, Process._append_event, _load_sibling = real_check, real_event, real_load
        Process.close_capture = real_close
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["capture-close's checks stage:"] + failures)


def _check_rate_note_reads_the_rule():
    """`capture-check`'s rate note reads the profile by the one rule the settings sheet and the model read it by (the
    final review's I2): `dsp_profile.load_profile`, then `stated_rate_hz`. A rate stated that is no rate -- text,
    `true`, 0, a negative number -- and a profile cut off are said in the note, `captured at <rate> Hz; the DSP's
    processing rate NOT READ -- <file> <reason> -- <repair>`, on stdout and in the journal's
    `capture_verified.rate_note`; the check is recorded and exits by its verdicts, and the session probe is handed no
    rate. A text rate exited 70 (the note's `:g` stood outside the `try`) with nothing recorded, `true` was noted as "the
    DSP processes at 1 Hz", a negative rate as a rate, and a profile cut off, or saved with a UTF-8 BOM, said nothing.
    A BOM'd profile is read, as every other reader reads it; no profile at all says nothing, as before."""
    import shutil
    import tempfile

    class Verifier:                              # one capture at 48 kHz; REW is not asked
        given = []

        def verify(self, titles):
            return [{"name": t, "exists": True, "reachable": True, "valid": True, "issues": [],
                     "stats": {"uuid": "u-" + t, "capture_rate_hz": 48000}} for t in titles]

        def session_report(self, verdicts, processing_rate_hz=None):
            Verifier.given.append(processing_rate_hz)
            return {"spread": None, "drift": None, "capture_rates_hz": [48000], "rows": []}

        def summary(self, rows):
            return {}

        def render_session(self, probe):
            return "(the session probe)"

    top = tempfile.mkdtemp(prefix="autosound_process_rate_note_")
    real = Process._load_verifier
    failures = []
    unread = "captured at 48000 Hz; the DSP's processing rate NOT READ -- "
    noted = ("captured at 48000 Hz; the DSP processes at 96000 Hz -- fine, working with it. Delays in samples derive "
             "from the PROCESSING rate; the capture rate stays with the measurement")
    try:
        Process._load_verifier = lambda self: Verifier()
        for n, (label, raw, said) in enumerate((
                ("96000", json.dumps({"dsp_processing_rate_hz": 96000}).encode(), noted),
                ("96000 after a UTF-8 BOM", b"\xef\xbb\xbf" + json.dumps({"dsp_processing_rate_hz": 96000}).encode(),
                 noted),
                ('"48000", text', json.dumps({"dsp_processing_rate_hz": "48000"}).encode(),
                 'states dsp_processing_rate_hz "48000", which is no processing rate'),
                ('"96 kHz"', json.dumps({"dsp_processing_rate_hz": "96 kHz"}).encode(),
                 'states dsp_processing_rate_hz "96 kHz", which is no processing rate'),
                ("true", json.dumps({"dsp_processing_rate_hz": True}).encode(),
                 "states dsp_processing_rate_hz true, which is no processing rate"),
                ("0", json.dumps({"dsp_processing_rate_hz": 0}).encode(),
                 "states dsp_processing_rate_hz 0, which is no processing rate"),
                ("-96000", json.dumps({"dsp_processing_rate_hz": -96000}).encode(),
                 "states dsp_processing_rate_hz -96000, which is no processing rate"),
                ("cut off", b'{"dsp_processing_rate_hz": 96000, "na', "is not valid JSON"),
                ("no profile", None, None))):
            d = os.path.join(top, f"p{n}", "process")
            p = Process(d)
            p.enter_phase("-1")
            p.start_capture("1", expected=["w-L_1 (sw)"])
            profile = os.path.join(p.project_dir, "dsp_profile.json")
            if raw is not None:
                with open(profile, "wb") as fh:
                    fh.write(raw)
            del Verifier.given[:]
            rc, out, err = _run_main(["process.py", d, "capture-check", "--session"])
            events = [e for e in Process(d).events() if e.get("type") == EV_CAPTURE_VERIFIED]
            note = events[-1].get("rate_note") if events else "(no capture_verified)"
            if said is None:
                ok = note is None and rc == EXIT_OK and "⚠" not in out
            elif said == noted:
                ok = note == noted and f"  ⚠ {noted}" in out.splitlines() and Verifier.given == [96000]
            else:
                ok = (isinstance(note, str) and note.startswith(unread + profile + " ") and said in note
                      and note.endswith(f"set-field {os.path.abspath(p.project_dir)} dsp_processing_rate_hz <Hz>, "
                                        "then finalize" if "no processing rate" in said else
                                        f"git -C {os.path.abspath(p.project_dir)} checkout HEAD -- dsp_profile.json")
                      and f"  ⚠ {note}" in out.splitlines() and Verifier.given == [None])
            if not ok or rc != EXIT_OK or "Traceback" in err:
                failures.append(f"{label}: rc {rc}, note {note!r}, rate handed on {Verifier.given}, "
                                f"out {out.strip()[-200:]!r}, err {err.strip()[-200:]!r}")
    finally:
        Process._load_verifier = real
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["capture-check's rate note:"] + failures)


def _check_every_writer_holds_the_lock():
    """Every writer of `Process` holds the project's lock around its load, its change, its write and its event (#141,
    J2b), read off the source: each public method that reaches `_write` or `_append` (`_writer_methods`) is decorated
    `@_locked` -- or is one of the two that read REW, git or `gh` first and take the hold themselves after, in a
    `with _hold(...)`. Those two are never decorated: that would hold the lock across what they read."""
    import ast
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        src = f.read()
    writers = _writer_methods(src)
    cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "Process")
    methods = {f.name: f for f in cls.body if isinstance(f, ast.FunctionDef)}
    themselves = {"check_captures", "enter_phase"}

    def holds(fn):
        return any(isinstance(node, ast.With) and any(
            isinstance(item.context_expr, ast.Call) and isinstance(item.context_expr.func, ast.Name)
            and item.context_expr.func.id == "_hold" for item in node.items) for node in ast.walk(fn))
    assert themselves <= writers, f"no longer writers here, or renamed: {sorted(themselves - writers)}"
    bare, held_over = [], []
    for name in sorted(writers):
        decorated = any(isinstance(d, ast.Name) and d.id == "_locked" for d in methods[name].decorator_list)
        if name in themselves:
            if decorated:
                held_over.append(name)
            elif not holds(methods[name]):
                bare.append(name)
        elif not decorated:
            bare.append(name)
    assert not bare, f"{len(bare)} writer(s) of {len(writers)} take no hold: {bare}"
    assert not held_over, f"decorated, so the lock is held across what they read first: {held_over}"


def _check_a_held_lock_answers_75_with_nothing_written():
    """Another writer holding the project's lock -- in a process of its own -- makes each writing verb wait
    `AUTOSOUND_LOCK_TIMEOUT_S` and exit 75 (#141, J2b): its last line `busy: <the lock file> ...`, nothing written, safe
    to retry. Each kind of writer: one `@_locked` (`add-step`), one that appends only (`decision`), `enter-phase` (its
    hold after its gates), `session-close`'s stop, and `capture-close`'s close after its read of REW (REW is down here:
    it closes on the record alone). The question `session-close --check` waits for nobody. Let go, the same command
    lands."""
    import multiprocessing
    import shutil
    import tempfile
    import time
    lock = _write_lock()
    top = tempfile.mkdtemp(prefix="autosound_process_busy_")
    signals = tempfile.mkdtemp(prefix="autosound_process_busy_signals_")
    child, failures = None, []
    try:
        d = _at_phase(top, "2")
        project = os.path.dirname(d)
        Process(d).start_capture("1", expected=["a_1 (sw)"])        # the round capture-close closes
        child = multiprocessing.get_context("spawn").Process(target=_lock_holder, args=(project, signals))
        child.start()
        deadline = time.monotonic() + 60
        while not os.path.exists(os.path.join(signals, "held")):
            assert time.monotonic() < deadline and child.is_alive(), f"the holder never held (exit {child.exitcode})"
            time.sleep(0.002)
        before = _project_bytes(d)
        for argv in (["add-step", "2.7", "x"], ["decision", "keep 45 degrees?", "yes"], ["enter-phase", "2"],
                     ["session-close"], ["capture-close"]):
            r = _cli_env(d, argv, AUTOSOUND_LOCK_TIMEOUT_S="0.3")
            last = (r.stderr.strip().splitlines() or [""])[-1]
            if r.returncode != EXIT_BUSY or not last.startswith("busy: ") or lock.lock_path(project) not in last \
                    or "Traceback" in r.stderr:
                failures.append(f"{argv[0]}: rc {r.returncode}, said {r.stderr.strip()[-200:]!r}")
            if _project_bytes(d) != before:
                failures.append(f"{argv[0]}: wrote under another writer's lock")
                before = _project_bytes(d)
        r = _cli_env(d, ["session-close", "--check"], AUTOSOUND_LOCK_TIMEOUT_S="0.3")
        if r.returncode != EXIT_NO or "OPEN ROUND cap_001" not in r.stdout:
            failures.append(f"session-close --check: rc {r.returncode}, said {(r.stderr or r.stdout).strip()[-160:]!r}")
        with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
            pass
        child.join(60)
        assert child.exitcode == 0, f"the holder failed: exit {child.exitcode}"
        r = _cli_env(d, ["add-step", "2.7", "x"], AUTOSOUND_LOCK_TIMEOUT_S="0.3")
        if r.returncode != EXIT_OK or "2.7" not in [s["id"] for s in Process(d).load()["plan"]]:
            failures.append(f"let go, add-step did not land: rc {r.returncode}, said {r.stderr.strip()[-160:]!r}")
    finally:
        with open(os.path.join(signals, "go"), "w", encoding="utf-8"):
            pass
        if child is not None:
            child.join(60)
            if child.is_alive():
                child.terminate()
                child.join(10)
        shutil.rmtree(top, ignore_errors=True)
        shutil.rmtree(signals, ignore_errors=True)
    assert not failures, f"{len(failures)} verb run(s) under a held lock:\n  " + "\n  ".join(failures)


def _check_a_bad_timeout_is_a_usage_error():
    """An `AUTOSOUND_LOCK_TIMEOUT_S` that is no number of seconds is a usage error (#141): exit 2, the variable named,
    nothing written and the lock's folder not made -- said first, before REW, git or `gh` is asked: `capture-check`
    answers 2 here, where REW, down, would have been its 69."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_bad_wait_")
    failures = []

    def refused(d, argv):
        before = _project_bytes(d)
        r = _cli_env(d, argv, AUTOSOUND_LOCK_TIMEOUT_S="soon")
        if r.returncode != EXIT_USAGE or "AUTOSOUND_LOCK_TIMEOUT_S=soon" not in r.stderr \
                or "usage: process.py" in r.stderr or "Traceback" in r.stderr:
            failures.append(f"{' '.join(argv)}: rc {r.returncode}, said {r.stderr.strip()[-200:]!r}")
        if _project_bytes(d) != before:
            failures.append(f"{' '.join(argv)}: wrote")
    try:
        d = _at_phase(top, "2")
        for argv in (["add-step", "2.7", "x"], ["decision", "keep 45 degrees?", "yes"], ["enter-phase", "2"],
                     ["session-close"]):
            refused(d, argv)
        if os.path.exists(os.path.join(os.path.dirname(d), ".autosound")):
            failures.append("the lock's folder was made")
        Process(d).start_capture("1", expected=["a_1 (sw)"])
        refused(d, ["capture-check"])
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} run(s) with a wait that is no number:\n  " + "\n  ".join(failures)


def _check_capture_check_reads_rew_unlocked():
    """REW is read with the project's lock free (#141, J2b): `verify` and the session probe run before the hold, and a
    writer that writes meanwhile -- a step added from another thread, which must not wait -- keeps its change: the
    verdicts merge under the hold into the state as it is THEN, by title. A round closed or replaced while REW was read
    is refused, nothing written: its verdicts would land on a round that did not ask for them."""
    import io as _io
    import shutil
    import tempfile
    lock = _write_lock()
    saved = os.environ.get("AUTOSOUND_LOCK_TIMEOUT_S")
    top = tempfile.mkdtemp(prefix="autosound_process_check_unlocked_")
    failures = []

    class Verifier:                  # REW holds `w-L_1 (sw)`, not `w-R_1 (sw)`; another writer writes while it answers
        def __init__(self, d, meanwhile):
            self.d, self.meanwhile, self.held, self.raised, self.after = d, meanwhile, [], [], None

        def verify(self, titles):
            self.held.append(lock.held_here(os.path.dirname(self.d)))
            self.raised.append(_from_another_thread(self.meanwhile))
            self.after = _project_bytes(self.d)
            return [{"name": t, "exists": t == "w-L_1 (sw)", "reachable": True, "valid": t == "w-L_1 (sw)",
                     "issues": [] if t == "w-L_1 (sw)" else ["REW holds no such title"], "stats": {"uuid": "u-" + t}}
                    for t in titles]

        def session_report(self, verdicts, processing_rate_hz=None):
            self.held.append(lock.held_here(os.path.dirname(self.d)))
            return {"spread": None, "drift": None, "capture_rates_hz": [], "rows": []}

    def with_round():
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["w-L_1 (sw)", "w-R_1 (sw)"])
        return d
    try:
        os.environ["AUTOSOUND_LOCK_TIMEOUT_S"] = "2"      # a hold taken across REW by mistake costs 2 s here, not 10
        d = with_round()
        v = Verifier(d, lambda: Process(d).add_step("-1.5", "added while REW was read", phase="-1"))
        with contextlib.redirect_stdout(_io.StringIO()):
            round_ = Process(d).check_captures(verifier=v, session=True)
        state = Process(d).load(strict=True)
        live = state.get("capture") or {}
        taken = live.get("taken") or {}
        verified = [e for e in Process(d).events() if e.get("type") == EV_CAPTURE_VERIFIED]
        if v.held != [False, False] or v.raised != [None]:
            failures.append(f"REW read under the lock: {v.held}; the other writer raised {v.raised}")
        if "-1.5" not in [s["id"] for s in state["plan"]]:
            failures.append("the step another writer added while REW was read is gone")
        if sorted(live.get("checks") or {}) != ["w-L_1 (sw)", "w-R_1 (sw)"] or "w-R_1 (sw)" in taken \
                or ((taken.get("w-L_1 (sw)") or {}).get("verified") or {}).get("ok") is not True \
                or not live.get("session"):
            failures.append(f"the round's verdicts: {json.dumps(live, ensure_ascii=False)[:300]}")
        if round_ != live:
            failures.append("check_captures returned another round than the one it wrote")
        if not verified or verified[-1].get("ok") != ["w-L_1 (sw)"] or verified[-1].get("bad") != ["w-R_1 (sw)"]:
            failures.append(f"capture_verified: {verified[-1:]}")
        # The round gone while REW was read -- closed, or replaced by the next one: refused, nothing written.
        want = "round cap_001 was closed or replaced while REW was read -- nothing was written; run capture-check again"
        for what, meanwhile in (("closed", lambda q: q.close_capture("closed while REW was read")),
                                ("replaced", lambda q: q.start_capture("2", expected=["w-L_2 (sw)"]))):
            d = with_round()
            v = Verifier(d, lambda d=d, meanwhile=meanwhile: meanwhile(Process(d)))
            caught = _raised(lambda: Process(d).check_captures(verifier=v))
            if not isinstance(caught, ProcessError) or str(caught) != want or v.raised != [None]:
                failures.append(f"{what}: {type(caught).__name__}: {caught} (the other writer raised {v.raised})")
            if _project_bytes(d) != v.after:
                failures.append(f"{what}: wrote")
    finally:
        if saved is None:
            os.environ.pop("AUTOSOUND_LOCK_TIMEOUT_S", None)
        else:
            os.environ["AUTOSOUND_LOCK_TIMEOUT_S"] = saved
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["capture-check and the lock:"] + failures)


def _check_enter_phase_gates_run_unlocked():
    """`enter_phase`'s gates run with the project's lock free (#141, J2b) -- the intake gate asks git and `gh`, for up
    to a minute and a half -- and the phase is entered under the hold into the state as it is THEN: a step another
    writer added meanwhile (from another thread, which must not wait) survives, and a phase another writer entered
    meanwhile refuses this one, naming the phase now active, nothing written."""
    import shutil
    import tempfile
    lock = _write_lock()
    real_gate = globals()["_require_intake"]
    saved = os.environ.get("AUTOSOUND_LOCK_TIMEOUT_S")
    top = tempfile.mkdtemp(prefix="autosound_process_gates_unlocked_")
    d = os.path.join(top, "process")
    failures, seen, raised, after = [], [], [], []

    def gate(meanwhile):
        """An intake gate that asks nothing: it says whether the lock is held while it runs, and lets another writer
        write. Once -- the other writer's own `enter_phase` passes it straight through."""
        def run(phase, previous, project_dir):
            if seen:
                return
            seen.append(lock.held_here(project_dir))
            raised.append(_from_another_thread(meanwhile))
            after.append(_project_bytes(d))
        return run
    try:
        os.environ["AUTOSOUND_LOCK_TIMEOUT_S"] = "2"      # gates run under the lock by mistake cost 2 s here, not 10
        Process(d).enter_phase("-1")
        globals()["_require_intake"] = gate(lambda: Process(d).add_step("-1.5", "added while the gates ran",
                                                                        phase="-1"))
        caught = _raised(lambda: Process(d).enter_phase("0"))
        state = Process(d).load(strict=True)
        if seen != [False] or raised != [None] or caught is not None:
            failures.append(f"the gates ran under the lock: {seen}; the other writer raised {raised}; enter_phase "
                            f"raised {caught!r}")
        if state["active_phase"] != "0" or "-1.5" not in [s["id"] for s in state["plan"]]:
            failures.append(f"phase {state['active_phase']}, plan {[s['id'] for s in state['plan']]}: the step added "
                            "while the gates ran is gone")
        del seen[:], raised[:], after[:]
        globals()["_require_intake"] = gate(lambda: Process(d).enter_phase("-1"))
        caught = _raised(lambda: Process(d).enter_phase("0"))
        if not isinstance(caught, ProcessError) or "phase -1" not in str(caught) \
                or "nothing was written" not in str(caught) or raised != [None]:
            failures.append(f"a phase entered meanwhile: {type(caught).__name__}: {caught} (the other writer raised "
                            f"{raised})")
        if not after or _project_bytes(d) != after[-1] or Process(d).load()["active_phase"] != "-1":
            failures.append(f"written over the phase another writer entered: phase "
                            f"{Process(d).load()['active_phase']}")
    finally:
        globals()["_require_intake"] = real_gate
        if saved is None:
            os.environ.pop("AUTOSOUND_LOCK_TIMEOUT_S", None)
        else:
            os.environ["AUTOSOUND_LOCK_TIMEOUT_S"] = saved
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["enter_phase and the lock:"] + failures)


def _check_the_sha_is_asked_before_the_hold():
    """Git is never asked under the project's lock (#141): the sha `_stamp` writes in the journal's header is asked of
    `provenance` by a writer's first verb with the lock still free -- once, never again under the hold -- and the
    journal line it stamps is written with the lock held. For each kind of writer, each a fresh `Process`: one
    `@_locked`, one that appends only, the two that take the hold themselves, and `session-close`'s stop in `_main`."""
    import io as _io
    import shutil
    import tempfile
    lock = _write_lock()
    prov = _load_rew_tool_module("provenance")
    real_sha, real_event = prov.skill_sha, Process._append_event
    top = tempfile.mkdtemp(prefix="autosound_process_sha_first_")
    project, asked, written, failures = [None], [], [], []

    class Verifier:
        def verify(self, titles):
            return [{"name": t, "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}}
                    for t in titles]

    def bare():
        return os.path.join(tempfile.mkdtemp(dir=top), "process")

    def at_minus_one():
        d = bare()
        Process(d).enter_phase("-1")
        return d

    def round_open():
        d = at_minus_one()
        Process(d).start_capture("1", expected=["a_1 (sw)"])
        return d

    def sha():
        asked.append(lock.held_here(project[0]))
        return "c" * 40

    def event(self, event_type, payload):
        written.append(lock.held_here(self.project_dir))
        return real_event(self, event_type, payload)
    try:
        # Each project is made first, stamped with the real sha: what is under test is its next writer, a fresh one.
        made = [(label, make(), first) for label, make, first in (
            ("add_step", at_minus_one, lambda d: Process(d).add_step("-1.1", "a step")),
            ("record_decision", at_minus_one, lambda d: Process(d).record_decision("keep 45 degrees?", "yes")),
            ("enter_phase", bare, lambda d: Process(d).enter_phase("-1")),
            ("check_captures", round_open, lambda d: Process(d).check_captures(verifier=Verifier())),
            ("session-close", at_minus_one, lambda d: _run_main(["process.py", d, "session-close"])))]
        prov.skill_sha, Process._append_event = sha, event
        for label, d, first in made:
            project[0] = os.path.dirname(os.path.abspath(d))
            del asked[:], written[:]
            with contextlib.redirect_stdout(_io.StringIO()):
                caught = _raised(lambda: first(d))
            heads = [e.get("skill_sha") for e in Process(d).events() if e.get("type") == EV_WRITTEN_BY]
            if caught is not None or asked != [False] or not written or not all(written) or heads[-1:] != ["c" * 40]:
                failures.append(f"{label}: the sha asked {asked} (True: under the lock), its lines written under the "
                                f"lock {written}, the last header {heads[-1:]}, raised {caught!r}")
    finally:
        prov.skill_sha, Process._append_event = real_sha, real_event
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the sha and the lock:"] + failures)


def _check_a_close_lands_state_first():
    """A round's close goes to the journal only once it is in the state (#141, J2b; W-8's review): its event went
    first, and a state write a holder refused -- Windows, past the retries -- said "it is as it was" over a journal
    that said closed; the retry closed the round there a second time. Now the refused write leaves both files as
    they were, and the retry closes the round once."""
    import shutil
    import tempfile
    io_ = _project_io()
    real = io_.atomic_write_json
    top = tempfile.mkdtemp(prefix="autosound_process_close_first_")

    def held(path, data, *args, **kwargs):
        if os.path.basename(path) == "process-state.json":
            raise PermissionError(13, "The process cannot access the file because it is being used by another "
                                      "process", path)
        return real(path, data, *args, **kwargs)

    def closes(d):
        return [(e.get("capture"), e.get("reason")) for e in Process(d).events() if e.get("type") == EV_CAPTURE_CLOSED]
    try:
        d = os.path.join(top, "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["w-L_1 (sw)"])
        before = _project_bytes(d)
        io_.atomic_write_json = held
        try:
            caught = _raised(lambda: Process(d).close_capture("done"))
        finally:
            io_.atomic_write_json = real
        said = str(caught)
        assert isinstance(caught, ProcessError) and said.endswith("it is as it was"), f"{type(caught).__name__}: {said}"
        assert closes(d) == [], f"the journal says closed, the state as it was: {closes(d)}"
        assert _project_bytes(d) == before, "a refused close wrote something"
        Process(d).close_capture("done")
        assert closes(d) == [("cap_001", "done")], f"the retry: {closes(d)}"
        assert Process(d).load(strict=True)["capture"].get("closed"), "the retry did not close the round"
    finally:
        io_.atomic_write_json = real
        shutil.rmtree(top, ignore_errors=True)


def _check_capture_close_closes_the_round_it_read():
    """`capture-close` reads the open round, then takes the project's lock three times -- the reconcile, the checks,
    the close -- and another writer can close or replace the round between them (#141, R7): the close closed the round
    open by then, one this verb never read against REW nor checked. Now the close is of the round it read, or refused
    naming both, nothing written. `close_capture` with no round given closes the open one, as ever."""
    import shutil
    import tempfile
    rew_api = _siblings().load("rew_api.py")
    real_list, real_verifier, real_check = rew_api.get_measurements, Process._load_verifier, Process.check_captures
    top = tempfile.mkdtemp(prefix="autosound_process_close_read_")
    failures = []

    class Verifier:
        def verify(self, titles):
            return [{"name": t, "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}}
                    for t in titles]

    def fresh():
        d = os.path.join(tempfile.mkdtemp(dir=top), "process")
        Process(d).enter_phase("-1")
        Process(d).start_capture("1", expected=["m-L_1 (sw)"])
        return d

    def closes(d):
        return [(e.get("capture"), e.get("reason")) for e in Process(d).events() if e.get("type") == EV_CAPTURE_CLOSED]

    def checks_then_a_new_round(self, *args, **kwargs):
        got = real_check(self, *args, **kwargs)
        raised = _from_another_thread(lambda: Process(self.dir).start_capture("1", expected=["m-R_1 (sw)"]))
        if raised is not None:
            failures.append(f"the other writer: {raised!r}")
        return got
    try:
        # In code, each of the three stages held to the round read (the reconcile and the checks too, so that what a
        # stopped capture-close says landed is said of the right round): another open, or none, is refused naming
        # both, `round_moved` on its class, nothing written.
        stages = (("close_capture", lambda q: q.close_capture("done", round_id="cap_001")),
                  ("reconcile_captures", lambda q: q.reconcile_captures(["m-L_1 (sw)"], round_id="cap_001")),
                  ("check_captures", lambda q: q.check_captures(verifier=Verifier(), round_id="cap_001")))
        for what, meanwhile, now in (
                ("replaced", lambda q: q.start_capture("1", expected=["m-R_1 (sw)"]), "(cap_002 is the open round now)"),
                ("closed", lambda q: q.close_capture("closed meanwhile"), "(no round is open now)")):
            for stage, call in stages:
                d = fresh()
                meanwhile(Process(d))
                before = _project_bytes(d)
                caught = _raised(lambda: call(Process(d)))
                said = str(caught)
                if not isinstance(caught, ProcessError) or not getattr(type(caught), "round_moved", False) \
                        or not said.startswith("round cap_001 ") or now not in said or "nothing was written" not in said:
                    failures.append(f"{stage}, {what}, in code: {type(caught).__name__}: {said}")
                if _project_bytes(d) != before:
                    failures.append(f"{stage}, {what}, in code: wrote")
        d = fresh()
        closed = _raised(lambda: Process(d).close_capture("done", round_id="cap_001"))
        if closed is not None or closes(d) != [("cap_001", "done")]:
            failures.append(f"the round given, open: {closed!r}, closes {closes(d)}")
        # The command line: another writer opens the next round between the checks and the close.
        rew_api.get_measurements = lambda: {"1": {"title": "m-L_1 (sw)"}}
        Process._load_verifier = lambda self: Verifier()
        d = fresh()
        Process.check_captures = checks_then_a_new_round
        try:
            rc, out, err = _run_main(["process.py", d, "capture-close"])
        finally:
            Process.check_captures = real_check
        last = (err.strip().splitlines() or [""])[-1]
        live = Process(d).load()["capture"]
        if rc != EXIT_NO or "cap_001" not in last or "cap_002" not in last or live.get("id") != "cap_002" \
                or live.get("closed") or closes(d) != [("cap_001", "superseded")]:
            failures.append(f"replaced after the checks: rc {rc}, open {live.get('id')!r} closed "
                            f"{live.get('closed')!r}, closes {closes(d)}, said {last!r}")
    finally:
        rew_api.get_measurements, Process._load_verifier, Process.check_captures = real_list, real_verifier, real_check
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["capture-close and the round it read:"] + failures)


#: A run of each verb that writes -- the state, the journal or a plan beside them -- as the checks of a folder that
#: does not exist drive them (#141, R46), and of each verb that only reads. Together they are `VERB_FLAGS`: a verb
#: added there and classed in neither turns `_check_a_mistyped_process_folder_starts_nothing` red.
_WRITING_RUNS = (
    ["enter-phase", "-1"], ["enter-phase", "0"], ["add-step", "1.1", "x"], ["start", "1.1"],
    ["done", "1.1", "project.json"], ["skip", "1.1", "not needed"], ["block", "1.1", "waiting"],
    ["reviewer", "gemini", "m"], ["target", "FULL", "EPY"], ["decision", "keep 45 degrees?", "yes"],
    ["session-start", "tcc", "opus"], ["session-close"], ["session-reopen", "it was a check"],
    ["capture-start", "1", "a_1 (sw)"], ["capture-check"], ["capture-taken", "a_1 (sw)"],
    ["capture-import", "1", "a_1 (sw)", "--bind", "=v_001", "--knob", "K=1"], ["amp-gain", "sw=+3"],
    ["capture-knobs", "SubRC=4/4"], ["capture-knobs", "--amend", "cap_001", "--reason", "late", "SubRC=4/4"],
    ["capture-protective", "w-L", "OFF"], ["capture-protective", "--amend", "cap_001", "--reason", "late", "w-L", "OFF"],
    ["listening-verdict", "--text", "heard"], ["capture-supersede", "a_1 (sw)", "a_1 (rta)"],
    ["capture-skip", "a_1 (sw)", "later"], ["capture-close"], ["capture-close", "--no-rew"])
_READING_RUNS = (["show"], ["plan"], ["check"], ["handoff"], ["handoff", "--json"], ["amp-changes"],
                 ["listening-verdicts"], ["session-close", "--check"])


def _made(d):
    """The process folder `d`, made, for a fixture whose first write is not `enter-phase -1`: a writer starts a process
    only in a folder that is there, or in one called `process` beside `project.json` (#141, R46)."""
    os.makedirs(d, exist_ok=True)
    return d


def _check_a_mistyped_process_folder_starts_nothing():
    """W-8's ruling R46 (#141): a write verb on a process folder that does not exist creates nothing there. A mistyped
    path, `<project>/process-typo`, got a state and a journal of its own from `enter-phase -1`, `reviewer`, `target`
    and `capture-start`, a journal from `decision`, `session-start`, `session-close`, `amp-gain` and
    `listening-verdict`; beside a whole project `enter-phase 0` and `capture-import` would have written too. Now each
    verb that writes refuses there, exit 1, naming the folder, and nothing is made -- no folder, no plan, and no
    `.autosound/`: the lock's hold makes that one, so the refusal comes before the hold (the byte walks leave a top
    `.autosound/` out, so it is looked for here by name). The verbs that only read make nothing either."""
    import shutil
    import tempfile
    runs = _WRITING_RUNS + _READING_RUNS
    assert {argv[0] for argv in runs} == set(VERB_FLAGS), \
        f"verbs classed nowhere here: {sorted(set(VERB_FLAGS) - {argv[0] for argv in runs})}"
    top = tempfile.mkdtemp(prefix="autosound_process_typo_")
    failures = []

    def made(proj, kept):
        extra = sorted(set(os.listdir(proj)) - set(kept))
        for name in extra:                      # cleared, so that the next verb is judged on its own
            path = os.path.join(proj, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        return extra
    try:
        for kept in ((), ("project.json",)):
            proj = os.path.join(top, "beside-a-project" if kept else "bare")
            os.makedirs(proj)
            for name in kept:
                with open(os.path.join(proj, name), "w", encoding="utf-8") as f:
                    f.write("{}\n")
            d = os.path.join(proj, "process-typo")
            want = (f"error: {d} does not exist, and the method's process folder is called process -- a mistyped "
                    "path? nothing was written")
            for argv in runs:
                rc, out, err = _run_main(["process.py", d, *argv])
                label = " ".join(argv) + (" beside a project" if kept else "")
                last = (err.strip().splitlines() or [""])[-1]
                if argv in _WRITING_RUNS and (rc != EXIT_NO or last != want or out.strip()):
                    failures.append(f"{label}: rc {rc}, said {(err or out).strip()[-200:]!r}")
                extra = made(proj, kept)
                if extra:
                    failures.append(f"{label}: made {extra}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} run(s) on a folder that does not exist:\n  " + "\n  ".join(failures)


def _check_a_new_project_still_starts():
    """The rule against a mistyped folder stops no project starting (#141, R46). A folder called `process` that is not
    there yet is a project's first process write where `project.json` stands beside it -- TCC's new-project dialog
    writes that file first -- and, with none, the intake's own `enter-phase -1`, which starts the project, as
    `session-start` does in a project folder that is there (R19, `_check_session_start_starts_a_project`). The intake
    starts one where the project folder is not there yet either, making it: the lock makes nothing there (R23), the
    first write does. Any other verb there first is refused, exit 1, "not a project yet", and nothing is made."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_new_project_")
    failures = []
    try:
        d = os.path.join(top, "intake", "process")
        os.makedirs(os.path.dirname(d))
        rc, out, err = _run_main(["process.py", d, "enter-phase", "-1"])
        if rc != EXIT_OK or Process(d).load(strict=True).get("active_phase") != "-1":
            failures.append(f"enter-phase -1, the intake: rc {rc}, said {err.strip()[-200:]!r}")
        d = os.path.join(top, "gone", "process")
        rc, out, err = _run_main(["process.py", d, "enter-phase", "-1"])
        if rc != EXIT_OK or Process(d).load(strict=True).get("active_phase") != "-1":
            failures.append(f"enter-phase -1 on a project folder that is not there: rc {rc}, said "
                            f"{err.strip()[-200:]!r}")
        for n, argv in enumerate(a for a in _WRITING_RUNS if a != ["enter-phase", "-1"] and a[0] != "session-start"):
            proj = os.path.join(top, f"first-{n}")
            os.makedirs(proj)
            rc, out, err = _run_main(["process.py", os.path.join(proj, "process"), *argv])
            want = (f"error: {proj} holds no project.json: not a project yet -- the intake starts one with "
                    "enter-phase -1; nothing was written")
            if rc != EXIT_NO or (err.strip().splitlines() or [""])[-1] != want or out.strip():
                failures.append(f"{' '.join(argv)} first: rc {rc}, said {(err or out).strip()[-200:]!r}")
            if os.listdir(proj):
                failures.append(f"{' '.join(argv)} first: made {sorted(os.listdir(proj))}")
        for argv in (["session-start", "tcc", "opus"], ["reviewer", "gemini", "m"], ["decision", "keep 45?", "yes"]):
            proj = os.path.join(top, f"seeded-{argv[0]}")
            os.makedirs(proj)
            with open(os.path.join(proj, "project.json"), "w", encoding="utf-8") as f:
                f.write("{}\n")
            d = os.path.join(proj, "process")
            rc, out, err = _run_main(["process.py", d, *argv])
            if rc != EXIT_OK or not os.path.isfile(Process(d).journal_path):
                failures.append(f"{argv[0]} beside project.json: rc {rc}, said {err.strip()[-200:]!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a new project:"] + failures)


def _check_session_start_starts_a_project():
    """TCC's first two verbs on an empty folder go through (#141, R19). TCC's project gate takes an empty folder -- the
    intake fills it -- and at a session's start runs `session-start`, then `enter-phase -1`, in one `try`
    (main_window.py): `session-start` was refused there, "holds no project.json", and `enter-phase -1` never ran. So
    `session-start` starts a project as `enter-phase -1` does, where the project folder itself is there: its process
    folder is called `process`, and no `project.json` is beside it yet. A mistyped `process-typo` stays refused, and so
    does a project folder that is not there, with nothing made."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_session_first_")
    failures = []
    try:
        proj = os.path.join(top, "empty")
        os.makedirs(proj)
        d = os.path.join(proj, "process")
        rc, out, err = _run_main(["process.py", d, "session-start", "tcc", "opus"])
        started = [e for e in Process(d).events() if e.get("type") == EV_SESSION_STARTED]
        if rc != EXIT_OK or out.strip() != "session recorded: tcc / opus" or err.strip() or len(started) != 1:
            failures.append(f"session-start on an empty folder: rc {rc}, said {(err or out).strip()[-200:]!r}, "
                            f"{len(started)} session event(s)")
        rc, out, err = _run_main(["process.py", d, "enter-phase", "-1"])
        if rc != EXIT_OK or Process(d).load(strict=True).get("active_phase") != "-1":
            failures.append(f"enter-phase -1 after it: rc {rc}, said {(err or out).strip()[-200:]!r}")
        proj = os.path.join(top, "bare")
        os.makedirs(proj)
        typo = os.path.join(proj, "process-typo")
        rc, out, err = _run_main(["process.py", typo, "session-start", "tcc", "opus"])
        want = (f"error: {typo} does not exist, and the method's process folder is called process -- a mistyped "
                "path? nothing was written")
        if rc != EXIT_NO or err.strip().splitlines() != [want] or out.strip() or os.listdir(proj):
            failures.append(f"session-start on process-typo: rc {rc}, said {(err or out).strip()[-200:]!r}, "
                            f"made {sorted(os.listdir(proj))}")
        gone = os.path.join(top, "gone")
        rc, out, err = _run_main(["process.py", os.path.join(gone, "process"), "session-start", "tcc", "opus"])
        want = (f"error: {gone} holds no project.json: not a project yet -- the intake starts one with enter-phase -1; "
                "nothing was written")
        if rc != EXIT_NO or err.strip().splitlines() != [want] or out.strip() or os.path.lexists(gone):
            failures.append(f"session-start on a project folder that is not there: rc {rc}, said "
                            f"{(err or out).strip()[-200:]!r}, made it: {os.path.lexists(gone)}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["TCC's first verbs:"] + failures)


def _check_the_plan_file_is_said():
    """A round's plan file is said (#141; W-8's review, S-101). The round is the record, the file is where the person
    reads it, written once the round landed -- and one that could not be written was said nowhere: `_write_capture_plan`
    returned None and `start_capture` dropped it. Now `capture-start` names the file on stdout once it is written, and
    one it could not write in one line on stderr, with why and where the list is; exit 0 either way, the round open."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_process_plan_said_")
    try:
        d = os.path.join(top, "blocked", "process")
        Process(d).enter_phase("-1")
        os.makedirs(os.path.join(top, "blocked", "docs"))
        with open(os.path.join(top, "blocked", "docs", "plans"), "w", encoding="utf-8") as f:
            f.write("a file where the plans folder belongs\n")
        plan = os.path.join(top, "blocked", "docs", "plans", "_1-capture.md")
        rc, out, err = _run_main(["process.py", d, "capture-start", "1", "w-L_1 (sw)"])
        round_ = Process(d).load(strict=True).get("capture") or {}
        lines = err.strip().splitlines()
        head, tail = f"note: the round is open, but its plan {plan} could not be written (", \
            f") -- process.py {d} show holds its list"
        assert rc == EXIT_OK and round_.get("id") == "cap_001" and not round_.get("closed"), (rc, round_, err)
        assert len(lines) == 1 and lines[0].startswith(head) and lines[0].endswith(tail) \
            and lines[0][len(head):-len(tail)].strip(), f"stderr: {lines}"
        assert "plan:" not in out, out
        d = os.path.join(top, "open", "process")
        Process(d).enter_phase("-1")
        plan = os.path.join(top, "open", "docs", "plans", "_1-capture.md")
        rc, out, err = _run_main(["process.py", d, "capture-start", "1", "w-L_1 (sw)"])
        assert rc == EXIT_OK and f"plan: {plan}" in out.splitlines() and not err.strip(), (rc, out[-300:], err)
        assert os.path.isfile(plan), f"no plan at {plan}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_a_project_folder_that_cannot_be_written():
    """A project folder this user may not write cannot hold the writer lock's `.autosound/` (#141, R6): `hold` let the
    `OSError` out -- exit 70 and a bug's traceback, over a folder that is only as it is. Now it is a refusal: exit 1,
    one line naming the folder and its repair, nothing written and nothing made. Met for real, so POSIX and not root
    (`_mode_refuses`)."""
    import shutil
    import tempfile
    if not _mode_refuses("a project folder this user may not write, met for real"):
        return
    top = tempfile.mkdtemp(prefix="autosound_process_read_only_")
    failures, proj = [], None
    try:
        d = _at_phase(top, "-1")
        proj = os.path.dirname(d)
        want = (f"error: {os.path.join(proj, '.autosound')} cannot be made for the project's writer lock (Permission "
                "denied), so nothing was written -- this user may not write there: give it access (its owner and "
                "mode, `ls -l`) and run again")
        before = _project_bytes(d)
        os.chmod(proj, 0o555)
        for argv in (["add-step", "-1.1", "x"], ["decision", "keep 45 degrees?", "yes"], ["session-close"],
                     ["enter-phase", "-1"], ["capture-start", "1", "w-L_1 (sw)"]):
            rc, out, err = _run_main(["process.py", d, *argv])
            if rc != EXIT_NO or err.strip().splitlines() != [want] or out.strip():
                failures.append(f"{' '.join(argv)}: rc {rc}, said {(err or out).strip()[-300:]!r}")
        if _project_bytes(d) != before:
            failures.append("wrote")
        if os.path.exists(os.path.join(proj, ".autosound")):
            failures.append("made the lock's folder")
    finally:
        if proj is not None:
            os.chmod(proj, 0o755)
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a project folder this user may not write:"] + failures)


def _selftest():
    """The refusals, exercised. This module is the one with the most of them — evidence must exist
    and must resolve (SCR-035), a round's captures must be usable (SCR-040), phase 0 must record a
    target (SCR-036) and now its flaw map (SCR-044) — and it was the only one of the seven with no
    selftest at all, so every one of those gates was a thing nobody had run since it was written.
    """
    failures = []
    for check in (_check_one_naming, _check_every_loader_shares, _check_load_sibling_reads_a_failure_as_none,
                  _check_verifier_load_error_named, _check_foreign_tmp_untouched, _check_state_bytes,
                  _check_torn_journal_line, _check_line_torn_inside_a_character,
                  _check_journal_that_cannot_be_opened, _check_journal_line_in_another_code_page,
                  _check_line_separators_inside_an_event, _check_event_refused_after_the_state,
                  _check_state_replace_refused, _check_unreadable_state,
                  _check_every_writer_refuses_unreadable, _check_write_guard_catches_damage_after_the_read,
                  _check_writers_read_strictly, _check_gates_refuse_unreadable, _check_newer_state_refused,
                  _check_exit_table, _check_typed_values_refused, _check_refused_capture_writes_nothing,
                  _check_import_of_a_whole_series, _check_catch_all_reads_the_type, _check_unknown_flags,
                  _check_flags_tcc_sends,
                  _check_flag_values_as_they_stand, _check_autocorrected_dashes, _check_too_few_arguments,
                  _check_value_flag_last, _check_help_writes_nothing, _check_usage_before_the_read,
                  _check_handoff_says_an_unreadable_changelog, _check_superseded_not_taken,
                  _check_check_never_invents_taken, _check_close_says_what_rew_did,
                  _check_listing_never_read_as_rew, _check_ambiguous_capture, _check_close_swallows_only_rew,
                  _check_intake_gate_names_an_unreadable_project_json, _check_close_checks_stage_refusals,
                  _check_naming_load_error_named, _check_round_lookups_read_the_state_strictly,
                  _check_intake_gate_names_an_unreadable_glossary, _check_plan_names_the_naming_load_error,
                  _check_phase1_gate_names_an_unreadable_glossary, _check_capture_verbs_read_the_glossary_strictly,
                  _check_rate_note_reads_the_rule, _check_evidence_verdicts_name_the_naming_load_error,
                  _check_capture_start_said_as_it_landed, _check_capture_start_held_names_the_close_that_landed,
                  _check_capture_start_held_leaves_the_open_rounds_plan, _check_says_what_it_did_not_check,
                  _check_project_bytes_leave_the_lock_out, _check_every_writer_holds_the_lock,
                  _check_a_held_lock_answers_75_with_nothing_written, _check_a_bad_timeout_is_a_usage_error,
                  _check_capture_check_reads_rew_unlocked, _check_enter_phase_gates_run_unlocked,
                  _check_the_sha_is_asked_before_the_hold, _check_a_close_lands_state_first,
                  _check_capture_close_closes_the_round_it_read, _check_a_mistyped_process_folder_starts_nothing,
                  _check_a_new_project_still_starts, _check_session_start_starts_a_project,
                  _check_the_plan_file_is_said, _check_a_project_folder_that_cannot_be_written):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    import tempfile

    # skill #105: the route of a car that is already tuned is named at handoff; any other mode, a missing or an
    # unreadable project.json says nothing.
    routed = tempfile.mkdtemp(prefix="autosound_route_")
    assert _route_line(routed) == ""
    for mode, said in (("improve_existing", True), ({"value": "improve_existing"}, True), ("new_tune", False)):
        with open(os.path.join(routed, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"goal": {"mode": mode}}, fh)
        assert ("Two ways in" in _route_line(routed)) is said, mode
    with open(os.path.join(routed, "project.json"), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert _route_line(routed) == ""

    root = tempfile.mkdtemp(prefix="autosound_process_")
    _seed_intake(root)  # the phase -1 gate is real now; a fixture has to pass it like anyone else
    proc = Process(os.path.join(root, "process"))
    proc.enter_phase("-1")
    proc.enter_phase("0")

    def refuses(what, fn):
        try:
            fn()
        except ProcessError:
            return
        raise AssertionError(f"process accepted {what}")

    proc.add_step("s1", "A step")
    refuses("a done step with no evidence", lambda: proc.finish_step("s1", []))
    # a skip says WHY, or it is not a skip (release review 2026-09-09)
    refuses("a skip with no reason", lambda: proc.skip_step("s1"))
    refuses("a skip whose reason is blank", lambda: proc.skip_step("s1", reason="   "))
    proc.skip_step("s1", reason="the front-end answered it")           # a sentence is enough
    proc.add_step("s2", "Another step")
    proc.skip_step("s2", superseded_by="s1")                            # so is a superseding step
    refuses("evidence that resolves to nothing",
            lambda: proc.finish_step("s1", ["I looked at the graphs and they seemed fine"]))
    with open(os.path.join(root, "autosound_context.md"), "w", encoding="utf-8") as f:
        f.write("# context\n")
    proc.finish_step("s1", ["autosound_context.md"])  # a file that exists resolves

    # SCR-036: no target curve, no phase 1.
    refuses("leaving phase 0 with no target", lambda: proc.enter_phase("1"))
    proc.set_target("FULL", "EPY")

    # SCR-044: the seeded project has every file intake owes and still no flaw map, so phase 1
    # is refused for that alone -- which is the case worth having, now that the intake gate can no
    # longer be satisfied by the files simply being absent.
    refuses("leaving phase 0 with an empty flaw map", lambda: proc.enter_phase("1"))
    _load_sibling("project.py").Project(root).add_flaw(
        f_hz=160, level_db=-12, kind="cabin_null", action="leave",
        why="fixture: a feature decided against is still an entry",
        evidence=["w-L_01 (sw)"],
    )
    proc.enter_phase("1")
    assert proc.load()["active_phase"] == "1"

    # -- S-047: the phase does not close over a row that STANDS on an unasked question -----------
    # `flaw_map` writes `_ASSUMED_NOTE` on every peak it could not check -- it computed that 43
    # times on a live project and carried it nowhere, while the nine-position set that would have
    # settled it sat on the Arbiter's disk. Fails on the old code at the first refusal: the gate
    # asked only whether the map had ANY row.
    assumed_root = tempfile.mkdtemp(prefix="autosound_assumed_")
    ap = Process(os.path.join(assumed_root, "process"))
    _seed_intake(assumed_root)
    ap.enter_phase("-1"); ap.enter_phase("0"); ap.set_target("SQ", "Jazzi")
    _load_sibling("project.py").Project(assumed_root).add_flaw(
        f_hz=1000, level_db=6, kind="driver_resonance", action="notch", channels=["m-L"],
        why="a peak of +6.0 dB, 0.30 oct wide (Q~3.0), " + _ASSUMED_NOTE,
        evidence=["m-L_01 (sw)"],
    )
    try:
        ap.enter_phase("1")
        raise AssertionError("phase 1 opened over a peak nobody checked")
    except ProcessError as exc:
        # The refusal has to carry the REQUEST, not just the complaint -- that is the whole item.
        assert "m-L p1..p9_<N> (sw)" in str(exc), str(exc)
        assert "m-L" in str(exc) and "decision" in str(exc), str(exc)
    # Asking IS the answer: a round opened for the positions closes the question.
    ap.start_capture("49", [f"m-L p{i}_49 (sw)" for i in range(1, 10)], phase="0")
    ap.enter_phase("1")
    assert ap.load()["active_phase"] == "1"
    # ...and so does the Arbiter deciding against it, on a project where no round was ever opened.
    declined_root = tempfile.mkdtemp(prefix="autosound_declined_")
    dp = Process(os.path.join(declined_root, "process"))
    _seed_intake(declined_root)
    dp.enter_phase("-1"); dp.enter_phase("0"); dp.set_target("SQ", "Jazzi")
    _load_sibling("project.py").Project(declined_root).add_flaw(
        f_hz=1000, level_db=6, kind="driver_resonance", action="notch", channels=["m-L"],
        why="a peak, " + _ASSUMED_NOTE, evidence=["m-L_01 (sw)"])
    refuses("phase 1 over an unasked ellipsoid", lambda: dp.enter_phase("1"))
    dp.record_decision("the ellipsoid for m-L", "not this session -- the tripod is packed")
    dp.enter_phase("1")
    assert dp.load()["active_phase"] == "1"
    # A map with no assumed row asks for nothing: the gate is about the unasked question, not
    # about ellipsoids in general.
    assert _positions_asked(root) is False and _flaw_map_entries(root), "the earlier project"

    # -- the phase -1 gate is a gate, not a paragraph (2026-08-12) ------------------------------
    # An empty folder used to walk to phase 1 with no project.json, no profile, no glossary and no
    # ledger: `enter-phase -1`, `enter-phase 0`, `set-target`, `enter-phase 1`, all OK. The quality
    # gate was documented and enforced by nobody.
    bare = Process(os.path.join(tempfile.mkdtemp(prefix="autosound_intake_"), "process"))
    bare.enter_phase("-1")
    try:
        bare.enter_phase("0")
        raise AssertionError("phase 0 started on a folder intake had never touched")
    except ProcessError as exc:
        assert "project.json" in str(exc), exc
    # ...and going nowhere is still free: re-entering -1 is not a forward move.
    bare.enter_phase("-1")

    # -- a step must live in a phase that exists (2026-08-12) ----------------------------------
    # `plan_for` only ever asks for real phases, so a step in phase "6" is written, counted by
    # nothing and displayed nowhere -- in the plan or in a consumer front-end.
    refuses("a step in a phase that is not a phase",
            lambda: proc.add_step("ghost", "A step nowhere", phase="6"))
    assert proc.step(proc.load(), "ghost") is None

    # SCR-045: a phase does not start on facts nobody recorded. Phase 1 turns delays into samples.
    proc.enter_phase("0")
    profile = {"dsp_profile": {"name": "M6V4", "vendor": "Musway", "groups": [
        {"id": "physical_outputs", "label": "Outputs",
         "fields": ["hp", "lp", "gain_db", "ta_ms"], "max_count": 6,
         "crossover_filters": {"types": {"LR": {"orders_db_per_oct": [24]}}}},
    ], "delay": {"step_ms": 0.02}}}
    with open(os.path.join(root, "dsp_profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f)
    refuses("entering phase 1 with no sample rate on record", lambda: proc.enter_phase("1"))
    # Deliberately the LEGACY key: the phase-1 gate must accept a profile written before the
    # rename (normalize_rate reads it), or every old project would refuse phase 1 for a fact it has.
    profile["dsp_profile"]["sample_rate_hz"] = 48000
    with open(os.path.join(root, "dsp_profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f)
    proc.enter_phase("1")
    # ...and phase 2 asks for what phase 2 needs, not for everything at once: this profile
    # declares no `eq` field, so there is nothing for it to owe.
    proc.enter_phase("2")
    assert proc.load()["active_phase"] == "2"

    # -- protective filters on a capture round (2026-08-23) --------------------
    # It lives on the ROUND because that is the granularity it has: one protective set per pass,
    # differing by channel inside it. And the round already carries `phase` and `version`, which
    # is what a reader needs to know whether de-embedding is appropriate at all.
    pr = proc                       # the fixture that already passed the phase -1 intake gate
    # The round asks for the channels this block records protection FOR -- which is the real
    # shape: protection is recorded for what was swept, and S-036's refusal below depends on it.
    pr.start_capture("0", expected=["m-L_0 (sw)", "w-L_0 (sw)", "tw-L_0 (sw)", "c_0 (sw)",
                                    "m-R_0 (sw)"], phase="0")
    pr.set_protective("m-L", {"hp": {"f": 100, "type": "LR", "slope": 24}})
    pr.set_protective("w-L", "OFF")
    rec = pr.protective_record()
    assert rec["channels"]["m-L"]["hp"]["f"] == 100, rec
    # "OFF" is an ANSWER and is stored; a channel nobody spoke for stays absent, and the two must
    # not collapse -- the whole de-embed decision turns on telling them apart.
    assert rec["channels"]["w-L"] == "OFF", rec
    assert "tw-L" not in rec["channels"], "an unanswered channel must not be invented as OFF"
    # The round carries what a reader needs to decide whether de-embedding applies at all.
    assert rec["phase"] == "0" and rec["version"] == "0", rec
    # The by-VERSION reader is what `analyze-joints --process` uses, and the solos it reads are
    # usually from a round closed sessions ago -- so it must find the record in the journal, not
    # only in the open slice, and must say None for a version nobody ever opened a round at.
    by_ver = pr.protective_record_for("0")
    assert by_ver and by_ver["channels"]["m-L"]["hp"]["f"] == 100 and by_ver["phase"] == "0", by_ver
    assert by_ver["channels"]["w-L"] == "OFF" and "tw-L" not in by_ver["channels"], by_ver
    assert pr.protective_record_for("7") is None, "no round at that version must read as None"
    assert pr.protective_record_for("00")["channels"]["m-L"]["hp"]["f"] == 100, \
        "`_00` and `_0` are one version -- a zero-padded title must still find its round"

    # A leg that cannot be reconstructed is refused at write time, not discovered at read time.
    for bad in ({"hp": {"f": 100, "type": "LR"}}, {"hp": {"type": "LR", "slope": 24}}, "maybe", 5):
        try:
            pr.set_protective("m-R", bad)
        except ProcessError:
            pass
        else:
            raise AssertionError(f"protective legs {bad!r} must be refused")
    assert "m-R" not in pr.protective_record()["channels"], "a refused write leaves no trace"

    # -- S-036 / skill #48: WHO answered, and a channel the round never captured ----------------
    # Fails on the old code at the first assertion: the record carried the legs and nothing about
    # their author, so ten channels written OFF in one second -- rears included, which were not in
    # the series at all -- were read downstream as ten of the Arbiter's answers.
    assert pr.protective_record()["sources"] == {"m-L": "user", "w-L": "user"}, pr.protective_record()
    assert pr.protective_record_for("0")["sources"]["m-L"] == "user"
    refuses("a protective record for a channel the round never captured",
            lambda: pr.set_protective("r-L", "OFF"))
    assert "r-L" not in pr.protective_record()["channels"], "a refused write leaves no trace"
    refuses("a source that is not one of the three", lambda: pr.set_protective("m-L", "OFF", source="tcc"))
    pr.set_protective("w-L", "OFF", source="default")
    assert pr.protective_record()["sources"]["w-L"] == "default", pr.protective_record()
    assert pr.protective_record_for("0")["sources"]["w-L"] == "default"

    pr.set_protective("w-L", "OFF", source="user")   # the fixture's own round stays as it was

    # The amendment path a CLOSED round needs (skill #48), on a project of its own so the fixture
    # above keeps its open round: no state write, a required reason, and `protective_record_for`
    # reads the correction as the last word on that channel.
    am = Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_amend_"), "process")))
    am.start_capture("49", expected=["m-L_49 (sw)"], phase="0")
    am.set_protective("m-L", "OFF", source="front_end")
    cap_id = am.protective_record()["id"]
    am.close_capture("the pass is over")
    refuses("a protective write on a CLOSED round", lambda: am.set_protective("m-L", "OFF"))
    refuses("an amendment with no reason", lambda: am.amend_protective(cap_id, "m-L", "OFF", ""))
    refuses("an amendment to a round that does not exist",
            lambda: am.amend_protective("cap_999", "m-L", "OFF", "typo"))
    am.amend_protective(cap_id, "m-L",
                        {"hp": {"f": 100, "type": "LR", "slope": 24}},
                        "the import wrote OFF for every channel in one second; the mids measurably "
                        "carry a 100 Hz LR24", source="user")
    fixed = am.protective_record_for("49")
    assert fixed["channels"]["m-L"]["hp"]["f"] == 100, fixed
    assert fixed["sources"]["m-L"] == "user", fixed
    assert fixed["amended"]["m-L"].startswith("the import wrote OFF"), fixed
    # ...and the amendment left the CLOSED round's own slice alone -- it is history, not state.
    assert am.load()["capture"]["protective"]["m-L"] == "OFF", am.load()["capture"]

    # The CLI verb, because autosound-tcc cannot reach a Python method here: it routes every
    # process WRITE through this command line under an exclusive lock, so a verb that only exists
    # in-process is a writer they cannot use.
    import subprocess
    _mod = os.path.abspath(__file__)
    def _cli(*argv):
        return subprocess.run([sys.executable, _mod, pr.dir, *argv],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    # The knobs of a round: recorded verbatim, found by the `_N` of the titles the round took, and
    # `None` when nobody recorded them -- which is not "they were at zero" (hub RES-007).
    assert _cli("capture-knobs", "SubRC=4/4", "RealCenter=ON").returncode == 0
    kn = proc.knobs_for("0")                       # this round was opened for version "0"
    assert kn and kn["knobs"] == {"SubRC": "4/4", "RealCenter": "ON"}, kn
    assert _cli("capture-knobs", "SubRC=3/4").returncode == 0, "a second write UPDATES the round"
    assert proc.knobs_for("0")["knobs"]["SubRC"] == "3/4"
    assert proc.knobs_for("999") is None, "a version with no round has no knobs, not empty ones"
    assert _cli("capture-knobs").returncode != 0 and _cli("capture-knobs", "SubRC").returncode != 0
    # #56 item 9: a CLOSED round's knobs can be written, as a correction with a reason, and are then read.
    amend_p = Process(_made(os.path.join(root, "process-amend")))
    amend_p.enter_phase("0")
    closed_id = amend_p.start_capture("5", expected=["m-L_5 (sw)"], phase="0")["id"]
    amend_p.close_capture(reason="done")

    def _amend_cli(*argv):
        return subprocess.run([sys.executable, _mod, amend_p.dir, *argv], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert _amend_cli("capture-knobs", "--amend", closed_id, "SubRC=7/12").returncode != 0, "no reason"
    assert _amend_cli("capture-knobs", "--amend", closed_id, "--reason", "known in the car, on record",
                      "SubRC=7/12").returncode == 0
    assert amend_p.knobs_for("5")["knobs"]["SubRC"] == "7/12", amend_p.knobs_for("5")
    # #58 P3: REW titles registered after the fact -- one round per DSP state, knobs required, lateness said.
    imp = Process(_made(os.path.join(root, "process-import")))
    imp.enter_phase("0")
    for bad_binds, bad_knobs in (({"": "v_404"}, {"SubRC": "4/4"}), ({}, {"SubRC": "4/4"}),
                                 ({"": None, "C": None}, {})):
        try:
            imp.capture_import("9", ["m-L_9 (sw)", "m-L C_9 (sw)"], bad_binds, bad_knobs)
            raise AssertionError(f"capture_import took binds={bad_binds} knobs={bad_knobs}")
        except ProcessError:
            pass
    try:
        imp.capture_import("9", ["m-L_8 (sw)"], {"": None}, {"SubRC": "4/4"})
        raise AssertionError("a title of another series was imported")
    except ProcessError:
        pass
    ids = imp.capture_import("9", ["m-L_9 (sw)", "m-L C_9 (sw)", "m-R C_9 (sw)"], {"": None, "C": None},
                             {"SubRC": "4/4"}, late="registered at the desk the next day")
    assert len(ids) == 2, ids                                   # two DSP states, two rounds
    notes = {e.get("capture"): e.get("note") for e in imp.events(kinds=(EV_CAPTURE_ISSUED,))}
    assert all("after the fact" in (notes.get(i) or "") for i in ids), notes
    assert imp.knobs_for("9")["knobs"] == {"SubRC": "4/4"}
    # The Arbiter, 2026-09-23: an amp gain he turned is on record per channel, between the rounds either side
    # of it, and a measured value replaces a said one. A series with no round cannot be placed (None, not {}).
    amp = Process(_made(os.path.join(root, "process-amp")))
    amp.enter_phase("0")
    amp.start_capture("50", expected=["sw_50 (sw)"], phase="0")
    amp.close_capture(reason="done")
    said_ = amp.record_amp_gain({"sw": "+3"}, note="sub amp a quarter turn up")
    assert said_["id"] == "amp-1" and said_["open_round"] is None, said_
    amp.start_capture("51", expected=["sw_51 (sw)"], phase="0")
    assert amp.amp_gain_between("50", "51") == {"sw": 3.0}
    assert amp.amp_gain_between("51", "50") == {"sw": -3.0}
    assert amp.amp_gain_between("51", "51") == {}
    assert amp.amp_gain_between("50", "97") is None
    assert amp.record_amp_gain({"sw": 1})["open_round"], "a change with a round open says so"
    amp.record_amp_gain({"sw": 2.6}, read_as="measured", amends="amp-1")
    assert amp.amp_changes()[0]["channels"] == {"sw": 2.6} and amp.amp_changes()[0]["read_as"] == "measured"
    for bad in ({"sw": "loud"}, {"sw": 0}, {}):
        try:
            amp.record_amp_gain(bad)
            raise AssertionError(f"amp change {bad} was taken")
        except ProcessError:
            pass
    # The Arbiter, 2026-09-23: protective history is gathered PER CHANNEL, from the newest round where the channel
    # had one -- the front raw in one round and the centre raw in another are both kept, and an OFF hides nothing.
    ph = Process(_made(os.path.join(root, "process-prot-hist")))
    ph.enter_phase("0")
    ph.start_capture("40", expected=["m-L_40 (sw)", "tw-L_40 (sw)"], phase="0")
    ph.set_protective("m-L", {"hp": {"f": 100.0, "type": "LR", "slope": 24}})
    ph.set_protective("tw-L", {"hp": {"f": 1000.0, "type": "LR", "slope": 24}})
    ph.close_capture(reason="front raw")
    ph.start_capture("41", expected=["c_41 (sw)", "m-L_41 (sw)"], phase="0")
    ph.set_protective("c", {"hp": {"f": 100.0, "type": "LR", "slope": 24}})
    ph.set_protective("m-L", "OFF")
    ph.close_capture(reason="centre raw")
    got = ph.protective_by_channel()
    assert set(got) == {"m-L", "tw-L", "c"}, got
    assert got["m-L"]["version"] == "40" and got["c"]["version"] == "41" and got["tw-L"]["legs"]["hp"]["f"] == 1000.0, got
    # #57 P0 / S-026: a round records the ledger version it was taken under and the level as a quantity; a
    # level with no dB in it, or an under that is not banked, is refused.
    lvl = Process(_made(os.path.join(root, "process-level")))
    lvl.enter_phase("0")
    r_ = lvl.start_capture("3", expected=["m-L_3 (sw)"], phase="0", level="-25 dB rel. max",
                           level_read_as="7 lamps on the Conductor")
    assert r_["level"] == {"value": "-25 dB rel. max", "read_as": "7 lamps on the Conductor"}, r_
    for bad in ({"level": "7 lamps"}, {"under": "v_404"}):
        try:
            lvl.start_capture("4", expected=["m-L_4 (sw)"], phase="0", **bad)
            raise AssertionError(f"start_capture took {bad}")
        except ProcessError:
            pass
    # A round that closes with no knobs recorded says so, at the one moment the answer is still in
    # the room -- and closes anyway, because refusing would strand a session mid-car. REW is a dead
    # port here (T-30): the close runs with REW down whatever listens on 4735 on this machine.
    bare = Process(_made(os.path.join(root, "process-bare")))
    bare.enter_phase("0")
    bare.start_capture("7", expected=["m-L_7 (sw)"], phase="0")
    bare_out = subprocess.run([sys.executable, _mod, bare.dir, "capture-close"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8", "REW_API_URL": "http://127.0.0.1:1"})
    # ...and REW really was down for it: a REW that answered would have closed the round against its list instead.
    assert bare_out.returncode == 0 and "NO KNOBS RECORDED" in bare_out.stdout \
        and "not checked against REW" in bare_out.stdout, bare_out
    out = _cli("capture-protective", "tw-L", "--hp", "1000", "LR", "24")
    assert out.returncode == 0, out.stderr
    assert pr.protective_record()["channels"]["tw-L"]["hp"]["f"] == 1000.0, out.stdout
    assert _cli("capture-protective", "c", "OFF").returncode == 0
    assert pr.protective_record()["channels"]["c"] == "OFF"
    both = _cli("capture-protective", "m-R", "--hp", "100", "LR", "24", "--lp", "4000", "BW", "36")
    assert both.returncode == 0, both.stderr
    assert pr.protective_record()["channels"]["m-R"]["lp"]["slope"] == 36, both.stdout
    # A half-given leg is refused on the command line too, with the reason -- not silently dropped
    # to a partial record that cannot be undone later.
    bad = _cli("capture-protective", "m-L", "--hp", "100", "LR")
    assert bad.returncode != 0 and "cannot be taken back out" in (bad.stderr + bad.stdout), bad
    empty = _cli("capture-protective", "m-L")
    assert empty.returncode != 0 and "is a different thing" in (empty.stderr + empty.stdout), empty

    # It is journalled, because it changes how every phase decision from those sweeps is read.
    kinds = [e.get("type") or e.get("event") or e.get("kind") for e in pr.events()]
    assert EV_CAPTURE_PROTECTIVE in kinds, kinds

    # -- listening verdicts (Phase 4, 2026-08-25): one writer, ids validated, look-back by filter --
    e1 = pr.record_listening_verdict([("CarMus#07", "c09", "bad"), ("CarMus#07", "c03", "ok")],
                                     text="stage flat, vocal holds", ledger_version="v_003", route="full")
    assert e1["pairs"][0]["verdict"] == "bad" and e1["ledger_version"] == "v_003"
    e2 = pr.record_listening_verdict([("CarMus#07", "c09", "🟢")], ledger_version="v_005")
    assert e2["pairs"][0]["verdict"] == "ok", "an emoji tick is normalised, not stored as-is"
    hist = pr.listening_verdicts(track="CarMus#07", characteristic="c09")
    assert [h["pairs"][0]["verdict"] for h in hist] == ["bad", "ok"], hist
    assert [h["ledger_version"] for h in hist] == ["v_003", "v_005"]
    assert pr.listening_verdicts(track="CarMus#24") == []
    for bad in ([("nope", "c09", "ok")], [("CarMus#07", "c99", "ok")], [("CarMus#07", "c09", "meh")]):
        try:
            pr.record_listening_verdict(bad)
            raise AssertionError(f"{bad} was accepted")
        except ProcessError:
            pass
    try:
        pr.record_listening_verdict([])
        raise AssertionError("an empty verdict was accepted")
    except ProcessError:
        pass
    lines = pr.banked_ear_lines()
    assert lines[0].startswith("[v_003] CarMus#07 c09 bad -- stage flat") and lines[-1] == "[v_005] CarMus#07 c09 ok", lines
    out = _cli("listening-verdict", "--pair", "mono/merrill:c01:ok", "--text", "tight point", "--ledger-version", "v_005")
    assert out.returncode == 0 and "mono/merrill c01 ok" in out.stdout, out.stderr + out.stdout
    out = _cli("listening-verdicts", "--track", "mono/merrill")
    assert out.returncode == 0 and "tight point" in out.stdout, out.stdout
    out = _cli("listening-verdict", "--pair", "mono/merrill:c01")
    assert out.returncode != 0 and "track:characteristic:ok|bad" in (out.stderr + out.stdout), out
    assert EV_LISTENING_VERDICT in [e.get("type") for e in pr.events()]

    # A round opened under the LEDGER version (`v_001`) whose titles carry the capture number
    # (`_49`) must be found by that number -- the tune session's real case (2026-08-25), where the
    # lookup returned None and a fully recorded round was exported as "no filter". Both keys work,
    # a number nobody captured under still reads as None, and the lookup failure can list rounds.
    pr.start_capture("v_001", expected=["m-L_49 (sw)", "tw-L_49 (sw)"], phase="0")
    pr.set_protective("m-L", {"hp": {"f": 100, "type": "LR", "slope": 24}})
    pr.record_capture("c_49 (sw)")
    by_title = pr.protective_record_for("49")
    assert by_title and by_title["version"] == "v_001" and \
        by_title["channels"]["m-L"]["hp"]["f"] == 100, by_title
    assert pr.protective_record_for("v_001")["channels"]["m-L"]["hp"]["f"] == 100
    assert pr.protective_record_for("50") is None, "a capture number nobody recorded under is None"
    rounds = pr.capture_rounds()
    assert rounds[-1]["id"] == by_title["series"] and rounds[-1]["title_versions"] == ["49"], rounds[-1]
    assert Process._title_version("m-L p3_01 (sw)") == "01" and Process._title_version("ALL_final (rta)") == "final"
    assert Process._title_version("c_49 (sw) x0") == "49" and \
        Process._title_version("r-L_17 (sw) noXO") == "17", "what follows the method keeps the `_N` (#34)"
    assert Process._title_version("w-L (imp)") is None and Process._title_version("sweep 49") is None
    # No open round is "no round to ask about", never "there was no protection".
    pr.close_capture(reason="done")
    assert pr.protective_record()["channels"]["m-L"]["hp"]["f"] == 100, "a closed round still says"

    # -- the journal says which method wrote it (autosound-hub HUB-002) -------------------------
    # The stamp is the journal's own, so what has to hold HERE is when it is written: at the top of
    # a fresh journal, once per run, and again only when the writing checkout changed. What git
    # actually says is `provenance`'s business and is proved there, on real repositories — a header
    # test that also asked git would be one ruler measuring itself.
    real_sha = _writer_sha
    try:
        globals()["_writer_sha"] = lambda: "a" * 40
        stamped = _made(os.path.join(tempfile.mkdtemp(prefix="autosound_stamp_"), "process"))
        run = Process(stamped)
        run.record_session("selftest", "-")
        run.record_session("selftest", "-")
        head = run.events()[0]
        assert head["type"] == EV_WRITTEN_BY and head["skill_sha"] == "a" * 40, head
        assert [e["type"] for e in run.events()].count(EV_WRITTEN_BY) == 1, "one header per run"

        # A new run from the SAME checkout adds nothing: the header marks a change, not a start-up.
        Process(stamped).record_session("selftest", "-")
        assert [e["type"] for e in Process(stamped).events()].count(EV_WRITTEN_BY) == 1, \
            "a second run from the same checkout re-headed the journal"

        # The method moved under the project — which is the whole case the header exists for.
        globals()["_writer_sha"] = lambda: "b" * 40
        Process(stamped).record_session("selftest", "-")
        kinds = [e["type"] for e in Process(stamped).events()]
        heads = [e["skill_sha"] for e in Process(stamped).events() if e["type"] == EV_WRITTEN_BY]
        assert heads == ["a" * 40, "b" * 40], heads
        # ...and it stands IN FRONT of the run it describes, not at the tail of the one before.
        assert kinds.index(EV_WRITTEN_BY, 1) == len(kinds) - 2, kinds

        # "Asked and could not be told" is recorded, not skipped: a journal with no header at all
        # means nobody ever asked, and the two must not look the same.
        globals()["_writer_sha"] = lambda: ""
        blind = _made(os.path.join(tempfile.mkdtemp(prefix="autosound_blind_"), "process"))
        Process(blind).record_session("selftest", "-")
        first = Process(blind).events()[0]
        assert first["type"] == EV_WRITTEN_BY and first["skill_sha"] == "", first
        Process(blind).record_session("selftest", "-")
        assert [e["type"] for e in Process(blind).events()].count(EV_WRITTEN_BY) == 1, "'' repeated"
    finally:
        globals()["_writer_sha"] = real_sha

    # ── stopping is an event: what is still open when a session ends (HUB-023) ────────────────
    # `session_start` had no pair, so "we stopped" could be said over an open round whose status
    # lives only in REW's measurement list. `open_work` REPORTS; closing each thing stays a
    # decision (which evidence, which reason), which is why nothing here writes.
    stop_root = _made(os.path.join(tempfile.mkdtemp(prefix="autosound_stop_"), "process"))
    sp = Process(stop_root)
    assert sp.open_work() == {"capture_round": None, "steps_in_progress": [], "phase": None}, \
        "a project that has done nothing owes nothing"
    sp.add_step("0.1", "baseline sweeps", phase="0")
    sp.start_attempt("0.1")
    sp.start_capture("1", ["w-L_1 (sw)", "w-R_1 (sw)"])
    sp.record_capture("w-L_1 (sw)")
    open_ = sp.open_work()
    assert open_["capture_round"]["outstanding"] == ["w-R_1 (sw)"], open_
    assert [s["id"] for s in open_["steps_in_progress"]] == ["0.1"], open_
    sp.skip_capture("w-R_1 (sw)", "not taken today")
    sp.close_capture()
    # A CLOSED round stays in the slice carrying `closed` -- reporting it as open forever is the
    # bug this line exists for, and the probe found it before this assertion did.
    assert sp.open_work()["capture_round"] is None, sp.open_work()
    assert sp.open_work()["steps_in_progress"], "the step is still in progress"
    sp.block_step("0.1", "the mic moved")
    assert sp.open_work()["steps_in_progress"] == [], sp.open_work()
    # ...and a step picked up again is owed again: stopping is not a one-way latch. The attempt
    # number does NOT move here, and that is this module's existing rule rather than an oversight
    # -- `start_attempt` counts a redo only after `done` or `skipped`; resuming a BLOCKED step is
    # the same attempt continuing. Asserted as it is, not as first assumed.
    sp.start_attempt("0.1")
    assert [(s["id"], s["attempt"]) for s in sp.open_work()["steps_in_progress"]] == [("0.1", 1)], \
        sp.open_work()
    sp.finish_step("0.1", ["w-L_1 (sw)"])
    sp.start_attempt("0.1")
    assert [s["attempt"] for s in sp.open_work()["steps_in_progress"]] == [2], sp.open_work()

    # ── S-084 (hub #227): `session-close --check` asks and writes nothing; a close is taken back ─
    # Fails on the old code at the first `--check` on a clean stop: the flag was ignored, and a
    # session reconciling state on the VM wrote `session_closed` by asking. Plain `session-close`
    # must keep writing -- TCC calls it on the way out and reads its exit code as the answer.
    def _cli(*argv):
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = _main(["process.py", sp.dir, *argv])
        return code, out.getvalue()

    def _journal():
        with open(sp.journal_path, encoding="utf-8") as fh:
            return fh.read()

    sp.record_session("selftest", "-")
    before = _journal()
    checked, said = _cli("session-close", "--check")          # a step is still in progress
    assert checked == 1 and "STEP IN PROGRESS 0.1" in said and "nothing recorded" in said, said
    assert _journal() == before, "--check wrote to the journal over open work"
    assert _cli("session-close")[0] == checked and _journal() == before, "the plain form owes the same answer"
    sp.finish_step("0.1", ["w-L_1 (sw)"])
    before = _journal()
    checked, said = _cli("session-close", "--check")          # nothing open: the case the VM met
    assert checked == 0 and "nothing open" in said and "nothing recorded" in said, said
    assert _journal() == before and not sp.session_closed(), "--check recorded a close"
    refuses("a reopening with no close before it", lambda: sp.reopen_session("ran it as a check"))
    closed, said = _cli("session-close")
    assert closed == checked and "recorded: session_closed" in said, said
    assert sp.session_closed() and sp.last_session_event()["type"] == EV_SESSION_CLOSED, sp.last_session_event()
    # A reopening needs its reason, and follows the close rather than replacing it.
    refuses("a reopening with no reason", lambda: sp.reopen_session("  "))
    # No reason given at all is too few arguments (R36): a usage error, 2; a blank one is refused above.
    assert _cli("session-reopen")[0] == EXIT_USAGE and sp.session_closed(), "a bare session-reopen was taken"
    code, said = _cli("session-reopen", "session-close", "was", "run", "as", "a", "check")
    assert code == 0 and "session_reopened" in said, said
    kinds = [e["type"] for e in sp.events(kinds=SESSION_EVENTS)]
    assert kinds[-2:] == [EV_SESSION_CLOSED, EV_SESSION_REOPENED], kinds
    assert sp.events(kinds=(EV_SESSION_REOPENED,))[-1]["reason"] == "session-close was run as a check"
    assert not sp.session_closed(), "the module still reads the session as closed after the reopening"
    refuses("a second reopening of one close", lambda: sp.reopen_session("again"))
    _cli("session-close")
    assert sp.session_closed(), "a close after a reopening is a close again"

    # ── S-039: a capture under the wrong title is SUPERSEDED, never deleted ──────────────────
    # Fails on the old code at the call: a round had `record_capture` and `skip_capture` and nothing
    # else, so a ghost `r-R_1 (se)` -- a typo already fixed in REW -- stayed as permanent evidence of
    # a measurement that does not exist.
    ty_root = tempfile.mkdtemp(prefix="autosound_typo_")
    ty = Process(os.path.join(ty_root, "process"))
    _seed_intake(ty_root)
    ty.enter_phase("-1")
    ty.enter_phase("0")
    ty.start_capture("1", ["r-R_1 (sw)", "r-L_1 (sw)"], phase="0")
    ty.record_capture("r-R_1 (se)")                     # the typo, as REW had it at the time
    assert _outstanding(ty.load()["capture"]) == ["r-R_1 (sw)", "r-L_1 (sw)"], "the typo is not one of them"
    ty.supersede_capture("r-R_1 (se)", "r-R_1 (sw)", "typed (se) for (sw); fixed in REW")
    round_now = ty.load()["capture"]
    # The wrong row STAYS -- dimmed, naming what it was corrected to. A round that loses a row is a
    # round nobody can audit.
    assert "r-R_1 (se)" in round_now["taken"], round_now["taken"]
    assert round_now["taken"]["r-R_1 (se)"]["superseded_by"] == "r-R_1 (sw)", round_now["taken"]
    assert round_now["taken"]["r-R_1 (sw)"]["planned"] is True, round_now["taken"]
    # ...and it stops counting as a capture that exists.
    assert _outstanding(round_now) == ["r-L_1 (sw)"], _outstanding(round_now)
    sup = [e for e in ty.events() if e["type"] == EV_CAPTURE_SUPERSEDED]
    assert sup and sup[0]["corrected_to"] == "r-R_1 (sw)" and sup[0]["reason"], sup
    refuses("superseding a title the round never took",
            lambda: ty.supersede_capture("nosuch_1 (sw)", "r-L_1 (sw)"))
    refuses("a correction to itself", lambda: ty.supersede_capture("r-R_1 (se)", "r-R_1 (se)"))

    # ── S-044: the handoff REFUSES, so a chat is not cleared over work that is only in it ─────
    # Fails on the old code at the call: `handoff` did not exist, and nothing checked that what the
    # next session needs was written before the chat holding the only copy was thrown away.
    ho = ty.handoff()
    assert ho["ok"] is False, ho
    assert any("is OPEN" in m for m in ho["missing"]), ho["missing"]
    assert ho["resume"] is None, ho
    ty.skip_capture("r-L_1 (sw)", "rears not wired in this pass")
    ty.close_capture("done")
    # A step left `todo` across a clear is a step the next session cannot tell from one nobody
    # ever thought of, so it is named too.
    ty.add_step("0.9", "read the arrivals", phase="0")
    assert any("neither closed nor decided against" in m for m in ty.handoff()["missing"]), \
        ty.handoff()["missing"]
    ty.skip_step("0.9", reason="Phase 1 does this with the tools built for it")
    ho = ty.handoff()
    assert ho["ok"] is True, ho["missing"]
    # The line it prints is what he SAYS next, plus what must stay open -- so the instruction is not
    # improvised a second time.
    assert "продовжуй" in ho["resume"] and "REW session" in ho["resume"], ho["resume"]
    assert "phase 0" in ho["resume"], ho["resume"]
    # It writes nothing: which evidence closes a step is a decision, the same split session-close has.
    assert ty.handoff() == ho, "handoff must be pure"
    # hub #201 (TCC-028): the machine form a front-end reads, with the message the new session starts with.
    hj = subprocess.run([sys.executable, _mod, ty.dir, "handoff", "--json"], capture_output=True, text=True,
                        encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    got_j = json.loads(hj.stdout)
    assert hj.returncode == 0 and got_j["ok"] and got_j["next_message"] == "продовжуй" and got_j["resume"], hj.stdout
    assert got_j["warnings"] == [], got_j

    # ── S-084 (hub #227): a ▶️ CONTINUE block behind the ledger is WARNED of, never refused ──────
    # Fails on the old code at the first warning: the block was only checked to exist, and on the
    # VM it named `v_010` with the ledger at `v_013`. What would still pass with a reader that took
    # every version in the file, or the method's own `v3.0.64` for a ledger version: the silent
    # cases below, which put both after or beside a block that names none.
    ty_head = _ledger_heads(ty_root)
    assert list(ty_head.values()) == ["v_001"], ty_head

    def _changelog(text):
        with open(os.path.join(ty_root, "tuning-changelog.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return ty.handoff()

    later = "\n## 2026-09-28\n- banked v_007, listened on method v3.0.64\n"
    ho = _changelog("# Tuning changelog\n\n## ▶️ CONTINUE\n- HEAD: v_009 (FULL), was v_001\n- next: the A/B\n" + later)
    assert ho["ok"] is True and ho["resume"], "a stale block refused the handoff -- it is a warning"
    assert len(ho["warnings"]) == 1 and "HEAD v_009" in ho["warnings"][0] and "v_001 (FULL)" in ho["warnings"][0], \
        ho["warnings"]
    hw = subprocess.run([sys.executable, _mod, ty.dir, "handoff"], capture_output=True, text=True,
                        encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert hw.returncode == 0 and "WARNING:" in hw.stdout and "v_009" in hw.stdout, hw.stdout
    assert _changelog("## ▶️ CONTINUE\n**HEAD = v_001** · FULL\n" + later)["warnings"] == [], "a matching HEAD warned"
    assert _changelog("## ▶️ CONTINUE\n- next: the A/B on method v3.0.64\n" + later)["warnings"] == [], \
        "a block naming no version warned"
    assert _changelog("**▶️ CONTINUE** — compare v_001 and v_009 by ear\n\n---\n- HEAD v_009\n")["warnings"] == [], \
        "a block naming two versions and no HEAD was read as naming one"
    assert continue_block_heads(ty_root) == [], "the rule ends the block"
    assert _changelog("▶️ CONTINUE: v_009 is where we are\n")["warnings"], "a block's one version is its HEAD"
    os.remove(os.path.join(ty_root, "tuning-changelog.md"))

    # ── S-048: another project's series number does not walk in unannounced ──────────────────
    # Fails on the old code at the refusal: `start_capture` took any number, and a session that
    # had ALREADY SAID the set was «серія _49 зі старого проєкту» opened the round as series 49,
    # writing another build's numbering into this project's record as its own.
    fs = Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_series_"), "process")))
    fs.start_capture("1", ["m-L_1 (sw)"])          # a first round has no sequence to be outside of
    fs.close_capture("done")
    fs.start_capture("2", ["m-L_2 (sw)"])          # the next number is this project's own
    fs.close_capture("done")
    try:
        fs.start_capture("49", ["m-L p1_49 (sw)"])
        raise AssertionError("another project's series walked in")
    except ProcessError as exc:
        assert "_49 is not this project's" in str(exc) and "--origin" in str(exc), str(exc)
        assert "capture-start 3" in str(exc), "the refusal names this project's own next number"
    # With the origin on record it opens, and the round CARRIES where the measurements came from.
    foreign = fs.start_capture("49", ["m-L p1_49 (sw)"], origin="passat-b8-2026:49")
    assert foreign["origin"] == {"project": "passat-b8-2026", "series": "49"}, foreign
    issued = [e for e in fs.events() if e["type"] == EV_CAPTURE_ISSUED][-1]
    assert issued["origin"]["project"] == "passat-b8-2026", issued
    # Half an origin is no origin: "from somewhere else" with no name answers nothing.
    for half in ("passat-b8-2026", {"project": "x"}, {"series": "49"}, ":49"):
        try:
            Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_half_"), "process"))).start_capture(
                "1", ["m-L_1 (sw)"], origin=half)
            raise AssertionError(f"accepted half an origin: {half!r}")
        except ProcessError:
            pass
    # A number this project has already used is its own, and needs nothing.
    fs.close_capture("done")
    fs.start_capture("2", ["m-L_2 (rta)"])

    # ── TCC-022: the two counters are told apart, and a ledger version is CHECKED ────────────
    # Fails on the old code at the first refusal: `start_capture` wrote the string and checked
    # nothing, so four rounds were opened at a `v_001` that had never been banked.
    assert (version_kind("v_001"), version_kind("1"), version_kind("_17")) == \
        ("ledger", "series", "series"), "the two counters"
    assert version_kind("ir-v7_49") is None and version_kind(None) is None
    cap = Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_cap_"), "process")))
    try:
        cap.start_capture("v_001", ["w-L_1 (sw)"])
        raise AssertionError("a round was opened at a ledger version nobody had banked")
    except ProcessError as exc:
        # The refusal has to carry BOTH ways on, because they are different questions -- bank the
        # state, or a baseline: the first snapshot, Phase 0 entered, the round at its series number by the
        # one recipe. Never "capture-start 1 ... needs no ledger": the recipe's first line, `enter-phase 0`,
        # is the Phase -1 gate and refuses while `state/<preset>/` is missing (the S1 review, Important 4).
        assert "no ledger at all" in str(exc) and "apply.propose" in str(exc), str(exc)
        assert "bank the first snapshot (`phase_-1_intake.md` §5), enter Phase 0 and open the round at its " \
               "SERIES number (`capture-session-sheet.md` Block 0)" in str(exc), str(exc)
        assert "capture-start 1" not in str(exc) and "needs no ledger" not in str(exc), str(exc)
    # A series round is not ledger-bound, and this call opens one with no ledger: the gate before a baseline is
    # `enter-phase 0`'s, not this call's.
    baseline = cap.start_capture("1", ["w-L_1 (sw)"])
    assert baseline["version_kind"] == "series", baseline
    issued = [e for e in cap.events() if e["type"] == EV_CAPTURE_ISSUED][-1]
    assert issued["version_kind"] == "series", issued
    # An unplanned SKIP is marked the way an unplanned arrival is -- on the round and on the event.
    cap.skip_capture("r-L_1 (sw)", "rears not wired in this pass")
    cap.skip_capture("w-L_1 (sw)", "driver buzzing, retake next session")
    assert cap.load()["capture"]["skipped"]["r-L_1 (sw)"]["planned"] is False, cap.load()["capture"]
    assert cap.load()["capture"]["skipped"]["w-L_1 (sw)"]["planned"] is True, cap.load()["capture"]
    skips = {e["title"]: e for e in cap.events() if e["type"] == EV_CAPTURE_SKIPPED}
    assert skips["r-L_1 (sw)"]["planned"] is False and skips["w-L_1 (sw)"]["planned"] is True, skips
    # Once the snapshot EXISTS, the same ledger round opens -- the check is about the fact on disk,
    # not about the spelling.
    banked_dir = os.path.join(_state_root(cap.project_dir), "SQ")
    os.makedirs(banked_dir, exist_ok=True)
    with open(os.path.join(banked_dir, "v_001.json"), "w", encoding="utf-8") as fh:
        fh.write("{}")
    bound = cap.start_capture("v_001", ["w-L_2 (sw)"])
    assert bound["version_kind"] == "ledger", bound

    # ── S-031: a step carries WHAT it covers, and its name names it ──────────────────────────
    # The old behaviour: `add_step("0.4", "Закрити відкриті поля: project.json (8)")` and the
    # eight fields live nowhere a reader can reach. Fails on the old code at the first line --
    # `covers` was not a parameter.
    cv = Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_covers_"), "process")))
    facts = ["project.json:sources.sweep_input", "project.json:amps.front.gain_db",
             "project.json:channels.r-L.driver", "project.json:channels.r-R.driver",
             "dsp_profile.json:eq.bands_total"]
    entry = cv.add_step("0.4", "Закрити відкриті поля", phase="0", covers=facts)
    assert entry["covers"] == facts, entry
    assert entry["name"] == (
        "0.4 Закрити відкриті поля: project.json:sources.sweep_input, "
        "project.json:amps.front.gain_db, project.json:channels.r-L.driver +2"), entry["name"]
    # The name is GENERATED: passing it back composed a second time changes nothing, so a
    # front-end that re-reads and re-adds cannot stutter the summary into the title.
    again = Process(cv.dir).add_step("0.5", entry["name"], phase="0", covers=facts)
    assert again["name"] == "0.5" + entry["name"][3:], again["name"]
    assert again["name"].count("+2") == 1, again["name"]
    # Blanks and duplicates are not facts; order is the caller's.
    assert cv.add_step("0.6", "x", phase="0", covers=["a", "", "a", " b "])["covers"] == ["a", "b"]
    # A step with nothing to cover is unchanged -- the field exists, the name is what was typed.
    plain = cv.add_step("0.7", "Raw baseline sweeps", phase="0")
    assert plain["covers"] == [] and plain["name"] == "0.7 Raw baseline sweeps", plain
    # skill #72: one label per step, the same on every screen. The session cited `2.8` while the panel showed
    # `2d: фінальний EQ` -- the section letter of phase_2_eq.md typed into the name. The id now leads the name and a
    # different label is dropped; a name that already leads with its id is left alone.
    assert cv.add_step("2.8", "2d: фінальний EQ до цілі", phase="2")["name"] == "2.8 фінальний EQ до цілі"
    assert cv.add_step("2.7", "2c — два пресети сцени", phase="2")["name"] == "2.7 два пресети сцени"
    assert cv.add_step("2.9", "2.9 центр", phase="2")["name"] == "2.9 центр"
    assert cv.add_step("2.10", "4 тони на драбині рівня", phase="2")["name"] == "2.10 4 тони на драбині рівня"   # content, not a label
    # The printers show it: `open_work` carries the full list, `plan`/`show` are raw JSON.
    cv.start_attempt("0.4")
    assert cv.open_work()["steps_in_progress"][0]["covers"] == facts, cv.open_work()
    assert covers_summary([]) == "" and covers_summary(["one"]) == "one"
    # The journal carries it too, so a plan rebuilt from events is not poorer than the state file.
    added = [e for e in cv.events() if e["type"] == EV_STEP_ADDED and e["step"] == "0.4"]
    assert added and added[0]["covers"] == facts, added

    # -- skill #29: phase 0 asks for (sw) AND (rta). The verdict marks an RTA `applicable: False`
    #    ("nothing here was checked"); the round must KEEP that and the step must not read it as
    #    bad. Round-trip, the way a producer's field is owed: verdict -> disk -> gate.
    na = Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_na_"), "process")))
    na.start_capture("1", ["w-L_1 (sw)", "w-L_1 (rta)", "w-R_1 (sw)"], phase="0")

    class _Verdicts:
        def verify(self, titles):
            return [{"name": "w-L_1 (sw)", "exists": True, "valid": True, "applicable": True,
                     "stats": {"uuid": "a"}, "issues": []},
                    {"name": "w-L_1 (rta)", "exists": True, "valid": False, "applicable": False,
                     "stats": {"uuid": "b"}, "issues": ["this check is for swept captures"]},
                    {"name": "w-R_1 (sw)", "exists": True, "valid": False, "applicable": True,
                     "stats": {"uuid": "c"}, "issues": ["flat to under a dB"]}]

    na.check_captures(verifier=_Verdicts())
    taken = Process(na.dir).load()["capture"]["taken"]
    assert taken["w-L_1 (rta)"]["verified"]["applicable"] is False, taken["w-L_1 (rta)"]
    assert taken["w-L_1 (sw)"]["verified"]["applicable"] is True, taken["w-L_1 (sw)"]
    assert na.unusable_captures() == ["w-R_1 (sw)"], "an RTA is not unusable; a flat sweep is"
    verified = [e for e in na.events() if e.get("type") == EV_CAPTURE_VERIFIED][-1]
    assert (verified["bad"], verified["not_applicable"]) == (["w-R_1 (sw)"], ["w-L_1 (rta)"]), verified

    # ── skill #77 / #78 / #80 / #83: the round gets its list from the plan, ordered by setup, carries its
    #    columns, keeps optional captures on the list, and closes against what REW holds ──────────────
    rr_root = tempfile.mkdtemp(prefix="autosound_round_")
    with open(os.path.join(rr_root, "project.json"), "w", encoding="utf-8") as fh:
        json.dump({"channels": [{"code": c} for c in ("sw", "w-L", "w-R", "m-L", "m-R")] + [{"code": "c", "hidden": True}],
                   "glossary": {"channels": [{"code": c, "active": True} for c in ("sw", "w-L", "w-R", "m-L", "m-R", "c")],
                                "pairs": {"Ws": ["w-L", "w-R"], "Ms": ["m-L", "m-R"]},
                                "sides": {"L": ["w-L", "m-L"], "R": ["w-R", "m-R"]},
                                "joints": {"SW+Ws": ["sw", "w-L", "w-R"]}}}, fh)
    rr = Process(os.path.join(rr_root, "process"))
    # The previous pass ended on an RTA, so the car is set up for RTA: the list takes every RTA first, then ONE
    # switch to the sweeps. `c` is hidden in the project's rows, so it is no task whatever the glossary says (#83).
    rr.start_capture("54", ["m-L_54 (sw)", "m-L_54 (rta)"], phase="2")
    rr.record_capture("m-L_54 (sw)", at="2026-09-26T10:00:00")
    rr.record_capture("m-L_54 (rta)", at="2026-09-26T10:05:00")
    rnd = rr.start_capture("55", ["c_55 (rta)"], phase="2", plan=True, optional=["Ws_55 (sw)"], step="2.3")
    assert [g["label"] for g in rnd["groups"]] == ["Solo (rta)", "Group (rta)", "Solo (sw)", "Group (sw)"], rnd["groups"]
    assert rnd["expected"] == [n for g in rnd["groups"] for n in g["names"]], "the list IS the columns, flattened"
    assert rnd["expected"][0] == "sw_55 (rta)" and "c_55 (sw)" not in rnd["expected"], rnd["expected"]
    assert "c_55 (rta)" in rnd["groups"][0]["names"], "a title typed beside the plan is on the list, in its place"
    assert rnd["optional"] == ["Ws_55 (sw)"] and rnd["groups"][-1]["names"] == ["Ws_55 (sw)"], rnd
    assert rnd["setup"] == {"first": "rta", "from": "m-L_54 (rta)", "switches": 1}, rnd["setup"]
    # skill #61: the list is also a file in the project's docs/plans/, the one he takes to the car.
    assert rnd["plan_path"] == "docs/plans/_55-capture.md", rnd["plan_path"]
    plan_text = open(os.path.join(rr_root, "docs", "plans", "_55-capture.md"), encoding="utf-8").read()
    assert "cap_002" in plan_text and "Solo (rta)" in plan_text and "Ws_55 (sw)   (optional)" in plan_text, plan_text
    issued = [e for e in rr.events() if e.get("type") == EV_CAPTURE_ISSUED][-1]
    assert issued["groups"] == rnd["groups"] and issued["optional"] == ["Ws_55 (sw)"], issued
    # --start overrides what the last round says; with nothing known, the plan's order (sweeps first).
    assert rr.start_capture("56", phase="2", plan=True, start_method="sw")["groups"][0]["label"] == "Solo (sw)"
    fresh = Process(_made(os.path.join(tempfile.mkdtemp(prefix="autosound_fresh_"), "process")))
    refuses("a plan with no glossary", lambda: fresh.start_capture("1", plan=True, phase="2"))
    # A round opened without the plan still carries its columns (#83): by kind and method of its titles.
    plain_r = rr.start_capture("57", ["m-L_57 (sw)", "Ms_57 (rta)", "w-L_57 (sw)"], phase="2")
    assert [(g["label"], g["names"]) for g in plain_r["groups"]] == \
        [("Solo (sw)", ["m-L_57 (sw)", "w-L_57 (sw)"]), ("Group (rta)", ["Ms_57 (rta)"])], plain_r["groups"]
    # Optional captures do not count as a gap: outstanding names the required ones, the optional apart.
    opt = rr.start_capture("58", ["m-L_58 (sw)"], phase="2", optional=["w-L_58 (sw)"])
    assert opt["expected"] == ["m-L_58 (sw)", "w-L_58 (sw)"] and rr.capture_outstanding() == ["m-L_58 (sw)"]
    assert _outstanding_optional(opt) == ["w-L_58 (sw)"]
    rr.record_capture("m-L_58 (sw)")
    assert rr.capture_outstanding() == [] and rr.open_work()["capture_round"]["outstanding"] == []
    # Closing against REW (#77 rule 3): what REW holds is taken, extra of THIS series is taken unplanned, a title
    # under another spelling is matched and named, a skipped one found after all is taken, missing stays open.
    rec = rr.start_capture("59", ["m-L_59 (sw)", "w-L_59 (sw)", "tw-L_59 (sw)", "Ms_59 (rta)"], phase="2",
                           optional=["Ws_59 (rta)"])
    rr.skip_capture("w-L_59 (sw)", "door open")
    verdict = rr.reconcile_captures(["m-L_59 (sw)", "w-L_59 (sw)", "Ms_059 (rta)", "sw_59 (sw)", "m-L_58 (sw)",
                                     "room sim", "sw_59 (sw) x0"])
    rec = rr.load()["capture"]
    assert sorted(rec["taken"]) == ["Ms_59 (rta)", "m-L_59 (sw)", "sw_59 (sw)", "sw_59 (sw) x0", "w-L_59 (sw)"], rec["taken"]
    assert rec["taken"]["Ms_59 (rta)"]["as_in_rew"] == "Ms_059 (rta)" and verdict["renames"] == {"Ms_059 (rta)": "Ms_59 (rta)"}
    assert rec["taken"]["sw_59 (sw)"]["planned"] is False and rec["taken"]["m-L_59 (sw)"]["planned"] is True
    assert "w-L_59 (sw)" not in rec["skipped"], "found in REW after all: taken, not skipped"
    assert "m-L_58 (sw)" not in rec["taken"], "another series is not this round's extra"
    assert verdict["missing"] == ["tw-L_59 (sw)"] and verdict["missing_optional"] == ["Ws_59 (rta)"], verdict
    assert rr.capture_outstanding() == ["tw-L_59 (sw)"]
    closed = rr.close_capture("done in the car")
    assert closed["closed_against"]["rew"] is True and closed["closed_against"]["missing"] == ["tw-L_59 (sw)"]
    ev = [e for e in rr.events() if e.get("type") == EV_CAPTURE_CLOSED][-1]
    assert ev["outstanding"] == ["tw-L_59 (sw)"] and ev["outstanding_optional"] == ["Ws_59 (rta)"] and ev["rew_checked"] is True
    # ...and a round closed with no REW in reach says so on the record.
    rr.start_capture("60", ["m-L_60 (sw)"], phase="2")
    assert rr.close_capture("no REW today")["closed_against"] == {"rew": False}
    # The CLI: `capture-start --plan` prints the list the Arbiter reads, column by column, with the switch named.
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _main(["process.py", rr.dir, "capture-start", "61", "--plan", "--phase", "2", "--start", "rta",
               "--optional", "Ws_61 (sw)", "--step", "2.3"])
    text = buf.getvalue()
    assert "Solo (rta)" in text and "Group (sw)" in text and text.index("Solo (rta)") < text.index("Solo (sw)"), text
    assert "1 optional" in text and "Ws_61 (sw)" in text and "switch" in text.lower(), text
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        _main(["process.py", rr.dir, "capture-close", "--no-rew", "desk only"])
    assert "not checked against REW" in buf.getvalue(), buf.getvalue()

    for case, why in _NOT_CHECKED_HERE:              # the OK line below claims only what ran (m-5)
        print(f"process: {case} was not checked here -- {why}")
    print(
        "selftest OK — a skip refused without a reason and taken with either a sentence or a "
        "superseding step; evidence refused when empty and when it resolves to nothing (SCR-035), "
        "phase -1 refused to end on a folder intake never touched, "
        "phase 0 refused to exit without a target (SCR-036) and without a flaw map (SCR-044) "
        "and opened once the map was recorded; "
        "phase 1 refused a profile with no `sample_rate_hz` (SCR-045) and phase 2 asked only for "
        "what a profile declaring no EQ actually owes; "
        "the journal headed itself with the writing checkout and re-headed only when it changed; "
        "and STOPPING is an event: `open_work` names the open round and every step left in "
        "progress, drops a round once it is closed, and owes a step again when it is picked "
        "back up; an RTA the check does not apply to is kept as such and holds no step (#29); a step CARRIES what it covers and its name names the first three and counts the rest (S-031); a capture under the wrong title is SUPERSEDED and stops counting, never deleted (S-039); the handoff REFUSES while anything the next session needs is only in the chat, and prints the resume line when it is not (S-044); `session-close --check` gives the same report and exit code and writes nothing, the plain form still records a clean stop, and a close is taken back only with a reason and only right after it, staying in the journal while the session reads as open; a ▶️ CONTINUE block naming a HEAD the ledger is not at is warned of and refuses nothing (S-084); a series number that is not this project's is refused until its ORIGIN is on record (S-048); a round records WHICH counter its version is, refuses a `v_NNN` nobody banked with both ways on, and marks a skip planned or not (TCC-022); and a phase does not close over a flaw row that stands on an UNASKED question -- the refusal carries the titles that would settle it, and a round opened or a ruling recorded closes it (S-047); a process-state.json that is there and cannot be read is refused before anything is done by every verb but the three display-only ones -- each writer of the state or the journal, each verdict, and show; handoff --json in its own JSON -- naming it and its repair and leaving the state and the journal byte for byte; every writer method reads it strictly itself, so a read that fails once never becomes an empty process written over the plan, and _write and _append refuse a file damaged after that read; a missing one is a fresh project and a BOM is read (#136); the phase gates refuse what they cannot check -- an intake check that raised or would not load, a profile check that would not load, a project.json or a dsp_profile.json that cannot be read -- writing nothing, and a state a newer method wrote is refused by every strict read and by both guards (#136, T-10, T-21); "
        "the command line exits by its table -- a bug 70 with its traceback (an IndexError too), REW down 69 with "
        "nothing written, every other answer of REW's 1 (an error, a list it cannot read, a write it did not keep, a "
        "title missing or held twice, an address that is none), a typed mistake in a leg or a series and a leg value "
        "out of range the verb's own 1, the catch-all reading the exception's class -- refuses a flag "
        "its verb does not take, a flag given another flag for its value (`--note --measured` and "
        "`--note=--measured` alike, `-h` among them), a flag whose hyphens were autocorrected to a dash, a value "
        "flag left last (but capture-protective's legs, the verb's own) and too few arguments -- a leg's values "
        "counting as the leg's -- with 2 before the state is read, takes "
        "the word after a flag as its value as `--flag=value` does and the Arbiter's words that begin `--` and hold a "
        "space as words, takes every flag TCC sends, classifies every flag as taking a value or not, and answers "
        "`<verb> --help` writing nothing (`-h` and `--help` elsewhere are 2); a refused capture-start or "
        "capture-import writes nothing, and an import of a whole series imports what is not on record, refuses a "
        "series REW holds nothing of and says when nothing is new; a writer reached through a private helper is driven "
        "by the strict-read table, and so is one reached through a function handed the process; "
        "a verifier that will not load is named with why; the handoff says a changelog it cannot read, its mend by "
        "the cause; "
        "a superseded row counts nowhere as taken, the reconcile's extra included, and a check never invents a "
        "capture REW does not hold (#134, #138 I-15); the journal is never read as empty by the method: one that cannot "
        "be opened, or that holds a line in another code page, refuses every reader of the method with its repair "
        "(events(), a screen's reader, stays lenient: such a journal is no events there, such a line skipped and "
        "counted), split on \\n alone so an event holding U+2028, U+2029 or U+0085 reads whole; "
        "a state writer refuses such a journal before it writes, an append refused after the write says what landed "
        "and the line to append, and a replace refused past the retries is a refusal, the file as it was; "
        "session-close's and capture-check's own reads are strict; a line no code page makes JSON of is refused "
        "naming --set-aside, and a journal that refuses the append is said as one (#134, the silent-failures "
        "review, batch 2). "
        f"root={root}"
    )
    return 0


def _main(argv):
    if len(argv) == 2 and argv[1] == "selftest":
        return _selftest()
    if len(argv) >= 2 and argv[1] in _HELP:
        print(_USAGE)
        return EXIT_OK
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return EXIT_USAGE
    root, cmd, args = argv[1], argv[2], argv[3:]
    # The command line is answered first (#134, #138 I-15): before `Process(root)`, before the strict read, before
    # REW. A question about the command is not a question about the project -- `--help` touches nothing, and an
    # unknown verb or flag is a usage error (2) on a damaged state too, where it exited 1 naming the file.
    if cmd in _HELP:
        print(_USAGE)
        return EXIT_OK
    if cmd not in VERB_FLAGS:
        print(_USAGE, file=sys.stderr)
        return EXIT_USAGE
    if args[:1] and args[0] in _HELP:
        print(_verb_usage(cmd))
        return EXIT_OK
    try:
        args = _args_checked(cmd, args)
        _args_counted(cmd, args)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    p = Process(root)
    try:
        if cmd not in _DISPLAY_VERBS:
            # The read rule (#136): every verb but the display-only ones reads the state strictly FIRST -- before its
            # own refusals, which would blame a step or a round the empty process lacks, before REW, before anything
            # is printed or written. One line for all of them, so a new verb is strict unless it is listed there.
            p.load(strict=True)
        if cmd == "show":
            # Strict (#136): printed as JSON, an unreadable file was an empty process to every screen that read it.
            print(json.dumps(p.load(strict=True), indent=2, ensure_ascii=False))
        elif cmd == "plan":
            phase = args[0] if args else None
            print(json.dumps(p.plan_for(phase), indent=2, ensure_ascii=False))
        elif cmd == "enter-phase":
            p.enter_phase(args[0])
            print(f"phase {args[0]} is current")
        elif cmd == "add-step":
            source = SOURCE_PROJECT if "--project" in args else SOURCE_SKILL
            rest, covers = [], []
            i = 0
            while i < len(args):
                if args[i] == "--project":
                    i += 1
                elif args[i] == "--covers":
                    covers += (args[i + 1] if i + 1 < len(args) else "").split(",")
                    i += 2
                else:
                    rest.append(args[i])
                    i += 1
            entry = p.add_step(rest[0], rest[1], source=source, covers=covers)
            print(f"added {rest[0]} {entry['name']}")
        elif cmd == "start":
            entry = p.start_attempt(args[0])
            print(f"{args[0]} in progress (attempt {entry['attempt']})")
        elif cmd == "done":
            entry = p.finish_step(args[0], args[1:])
            print(f"{args[0]} done, evidence: {', '.join(entry['evidence'])}")
        elif cmd == "skip":
            rest = list(args[1:])
            superseded_by = None
            if "--superseded-by" in rest:
                i = rest.index("--superseded-by")
                superseded_by = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            p.skip_step(args[0], superseded_by=superseded_by, reason=" ".join(rest) or None)
            print(f"{args[0]} skipped (kept in the plan)")
        elif cmd == "block":
            p.block_step(args[0], " ".join(args[1:]))
            print(f"{args[0]} blocked")
        elif cmd == "reviewer":
            flags = {}
            rest = []
            i = 0
            while i < len(args):
                token = args[i]
                if token in ("--review", "--mode"):          # `--review=PATH` arrives split (`_args_checked`)
                    i += 1
                    flags[token[2:]] = args[i] if i < len(args) else None
                else:
                    rest.append(token)
                i += 1
            p.record_reviewer(rest[0], rest[1], step=rest[2] if len(rest) > 2 else None,
                              review=flags.get("review"), mode=flags.get("mode"))
            print(f"reviewer recorded: {rest[0]} / {rest[1]}"
                  + (f" -> {flags['review']}" if flags.get("review") else " (no text recorded)"))
        elif cmd == "target":
            p.set_target(args[0], args[1])
            print(f"target for {args[0]}: {args[1]}")
        elif cmd == "decision":
            invalidates = None
            rest = list(args)
            for i, token in enumerate(rest):
                if token == "--invalidates":                 # `--invalidates=X` arrives split (`_args_checked`)
                    invalidates = rest[i + 1] if len(rest) > i + 1 else None
                    rest = rest[:i] + rest[i + 2:]            # a step given after it is the step, not dropped
                    break
            p.record_decision(rest[0], rest[1], step=rest[2] if len(rest) > 2 else None,
                              invalidates=invalidates)
            print(f"decision recorded: {rest[1]}")
        elif cmd == "session-start":
            p.record_session(args[0], args[1], resumed=(len(args) > 2 and args[2] == "resumed"))
            print(f"session recorded: {args[0]} / {args[1]}")
        elif cmd == "session-close":
            # S-084: `--check` is the same question with no write. Run as a look, the plain form
            # wrote `session_closed` on the VM; it stays as it is, because TCC calls it on the way out
            # and reads its exit code as the answer.
            check_only = "--check" in args
            # The stop reads what is open and records the close under the project's lock (#141): read apart, a round
            # or a step another writer opened in between was stopped over. `--check` writes nothing, waits for nobody.
            # A folder that is no project's is refused before the hold makes anything (R46).
            if not check_only:
                p._require_home("session-close")
                p._ready_to_hold()
            with contextlib.nullcontext() if check_only else _hold(p.project_dir):
                # Strict, before anything is written (#136): read as an empty process, an unreadable file had nothing
                # open, and the plain form recorded a clean stop over a round or a step it could not see.
                open_ = p.open_work(state=p.load(strict=True))
                lines, owed = [], 0
                round_ = open_["capture_round"]
                if round_:
                    owed += 1
                    miss = round_["outstanding"]
                    lines.append(
                        f"OPEN ROUND {round_['id']} at {round_['version']}: "
                        f"{round_['taken']} taken, {round_['skipped']} skipped"
                        + (f", {len(miss)} still expected ({', '.join(miss)})" if miss else "")
                        + "\n    close it: capture-skip <title> <reason> for each one not coming, "
                          "then capture-close"
                        + "\n    why now: an open round's status lives in REW's measurement list and "
                          "goes when REW does")
                for entry in open_["steps_in_progress"]:
                    owed += 1
                    lines.append(
                        f"STEP IN PROGRESS {entry['id']} {entry.get('name') or ''} "
                        f"(attempt {entry['attempt']})"
                        + (f"\n    covers: {', '.join(entry['covers'])}" if entry.get("covers") else "")
                        + "\n    close it: done <id> <evidence that RESOLVES>, or block <id> <reason>, "
                          "or skip <id> <reason>")
                if not check_only and not owed:
                    # Only a CLEAN stop is an event, recorded before the report is printed (#134, F I-2): an append
                    # refused -- a journal that cannot be opened -- is the verb's refusal then, with nothing printed
                    # before it, as `check_captures` records before it tells (issue #21).
                    p._append(EV_SESSION_CLOSED)
            print("\n".join(lines) if lines else
                  "nothing open in the process record — round closed, no step left in progress")
            # Two carriers this module does not own, named rather than checked: saying "also do X"
            # is honest, pretending to have verified it would not be.
            print("\nNot checked here, and still part of stopping:"
                  "\n  - a ruling the Arbiter made out loud -> `decision <question> <answer>`"
                  "\n  - an agreed change not yet banked (🟡) -> `apply.propose` (the ledger, not this file)"
                  "\n  - the session log / handoff line for the next session"
                  "\n  - the car itself: the in-car EXIT CHECKLIST (SKILL.md) — test values reverted, "
                  "knobs back, config backed up")
            if check_only:
                print("\nnothing recorded (--check): this asked what is open and wrote nothing. "
                      "`session-close` without --check is the stop itself")
            elif not owed:
                # Only a CLEAN stop is an event (appended above): with work still open the honest record
                # is the report above, and `session-close` exits non-zero so "we stopped" cannot be said
                # over an open round.
                print("\nrecorded: session_closed")
            return 1 if owed else 0
        elif cmd == "session-reopen":
            event = p.reopen_session(" ".join(args))
            print(f"recorded: session_reopened — {event['reason']}. The close ({event.get('closed_at', '?')}) "
                  "stays in the journal; the session reads as open from here")
        elif cmd == "capture-start":
            step = None
            rest = list(args)
            origin = None
            if "--origin" in rest:
                i = rest.index("--origin")
                origin = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            if "--step" in rest:
                i = rest.index("--step")
                step = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            flags = {}
            for flag in ("--under", "--level", "--level-read-as", "--start", "--phase"):
                if flag in rest:
                    i = rest.index(flag)
                    flags[flag] = rest[i + 1] if len(rest) > i + 1 else None
                    rest = rest[:i] + rest[i + 2:]
            optional = []
            while "--optional" in rest:            # repeatable: one title per flag (a title carries spaces)
                i = rest.index("--optional")
                if len(rest) > i + 1:
                    optional.append(rest[i + 1])
                rest = rest[:i] + rest[i + 2:]
            plan = "--plan" in rest
            rest = [a for a in rest if a != "--plan"]
            round_ = p.start_capture(rest[0], expected=rest[1:], step=step, origin=origin,
                                     under=flags.get("--under"), level=flags.get("--level"),
                                     level_read_as=flags.get("--level-read-as"), phase=flags.get("--phase"),
                                     plan=plan, optional=optional, start_method=flags.get("--start"))
            print(
                f"{round_['id']} open at {round_['version']}, "
                f"{len(round_['expected'])} capture(s) expected"
                + (f" ({len(round_['optional'])} optional)" if round_.get("optional") else "")
                + (f", under {round_['under']}" + (f" ({round_['under_note']})" if round_.get("under_note") else "")
                   if round_.get("under") else "")
                + (f", level {round_['level']['value'] or '?'}" if round_.get("level") else "")
                + (f" — taken in {round_['origin']['project']} as _{round_['origin']['series']}, "
                   "not this project's own series"
                   if round_.get("origin") else "")
            )
            for line in render_round_list(round_):
                print(line)
            # The plan file, said either way (S-101): written, where it is; not, why -- the round is open all the same.
            plan_path, unwritten = p._plan_written
            if unwritten is None:
                print(f"plan: {plan_path}")
            else:
                print(f"note: the round is open, but its plan {plan_path} could not be written ({unwritten}) -- "
                      f"process.py {p.dir} show holds its list", file=sys.stderr)
        elif cmd == "capture-check":
            session = "--session" in args
            args = [a for a in args if a != "--session"]
            try:
                round_ = p.check_captures(args or None, session=session)
            except RewUnavailableError as exc:
                # The advice is this verb's (#134): `capture-close` runs the same check and then closes the round, so
                # "run capture-check again" cannot be followed there.
                print(f"error: {exc}; start REW and run capture-check again", file=sys.stderr)
                return EXIT_REW_UNAVAILABLE
            if session and round_.get("session"):
                verifier = p._load_verifier()
                # `reachable` kept (#134): a row REW did not answer for is counted unreachable, never unusable; and
                # `ambiguous`, a title REW holds more than once, counted apart (H I-8).
                probe = dict(round_["session"], counts=verifier.summary(
                    [{"exists": r["exists"], "valid": r["valid"], "applicable": r.get("applicable", True),
                      "reachable": r.get("reachable", True), "ambiguous": r.get("ambiguous")}
                     for r in round_["session"]["rows"]]),
                    processing_rate_hz=None, rate_note=None)
                print(verifier.render_session(probe))
                print()
            taken, checks = round_.get("taken") or {}, round_.get("checks") or {}
            for title in round_.get("expected", []):
                row = taken.get(title) or {}
                # A taken title reads its own verdict; one the round did not take reads its check (T-1). A superseded
                # row is no capture (N17): the line says what it was corrected to.
                superseded = row.get("superseded_by")
                verdict = {} if superseded else (row.get("verified") if title in taken else checks.get(title)) or {}
                if verdict.get("ok"):
                    print(f"OK      {title}")
                elif title in (round_.get("skipped") or {}):
                    print(f"SKIP    {title}")
                elif superseded:
                    print(f"UNUSABLE {title} — superseded by {superseded}")
                elif verdict.get("applicable") is False:
                    print(f"N/A     {title} — {'; '.join(verdict.get('issues') or [])}")
                elif verdict.get("ambiguous"):
                    # Its own verdict (H I-8): REW holds it, so it is not missing -- and not usable until renamed. On
                    # an UNUSABLE line, `UNUSABLE <title> — `, the form TCC's strip keeps (R57): it shows there as it is.
                    print(f"UNUSABLE {title} — AMBIGUOUS: REW holds {verdict['ambiguous']} measurements under this "
                          "title; rename so titles are unique, then run capture-check again")
                else:
                    reason = "; ".join(verdict.get("issues") or ["не перевірено"])
                    print(f"UNUSABLE {title} — {reason}")
            left = p.unusable_captures(p.load(strict=True))   # the exit code is a verdict (#136)
            print(f"{len(round_.get('expected', [])) - len(left)}/"
                  f"{len(round_.get('expected', []))} придатні")
            return 1 if left else 0
        elif cmd == "capture-taken":
            round_ = p.record_capture(args[0])
            entry = round_["taken"][args[0].strip()]
            print(
                f"{args[0]} recorded"
                + ("" if entry["planned"] else " (unplanned -- not on this round's list)")
            )
        elif cmd == "capture-import":
            rest, binds, knobs, late = list(args), {}, {}, None
            while "--bind" in rest:
                i = rest.index("--bind")
                mod, _, ver = (rest[i + 1] if len(rest) > i + 1 else "").partition("=")
                binds[mod.strip()] = ver.strip()
                rest = rest[:i] + rest[i + 2:]
            if "--late" in rest:
                i = rest.index("--late")
                late = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            while "--knob" in rest:
                i = rest.index("--knob")
                name, _, pos = (rest[i + 1] if len(rest) > i + 1 else "").partition("=")
                knobs[name.strip()] = pos.strip()
                rest = rest[:i] + rest[i + 2:]
            if not rest:
                raise ProcessError("capture-import <N> [title ...]: the series, then the titles (default: every "
                                   "title of that series REW holds)")
            series, titles = rest[0], rest[1:]
            number = _series_number(series)        # a typed mistake is refused before REW is asked (H I-7)
            on_record = 0
            if not titles:
                # The whole series as REW holds it (R47a): none of it is a refusal -- it read "imported 0 title(s)",
                # exit 0 -- and a title already on record is passed over: a re-run imported the series again.
                import rew_api as _rew_api
                _naming = _load_naming()
                if _naming is None:
                    raise ProcessError(f"the title grammar (naming.py) cannot be loaded{_load_failure('naming.py')} "
                                       "-- nothing was imported")
                held = [m.get("title", "") for m in _rew_api.get_measurements().values()
                        if (_naming.parse_name(m.get("title", "")) or {}).get("version_n") == number]
                if not held:
                    raise ProcessError(f"REW holds no measurement of series _{number}; nothing was imported")
                known = p._titles_on_record(p.load(strict=True))
                titles = [t for t in held if t not in known]
                on_record = len(held) - len(titles)
                if not titles:
                    print(f"nothing new: the {len(held)} measurement(s) of series _{number} REW holds are on record "
                          "already -- nothing was imported")
                    return EXIT_OK
            ids = p.capture_import(series, titles, binds, knobs, late=late)
            print(f"imported {len(titles)} title(s) of _{number} as {', '.join(ids)}"
                  + (f" ({on_record} already on record, left as they are)" if on_record else "")
                  + (f" -- late: {late}" if late else ""))
        elif cmd == "amp-gain":
            rest, read_as, amends, note = list(args), "said", None, None
            if "--measured" in rest:
                rest.remove("--measured")
                read_as = "measured"
            for flag in ("--amends", "--note"):
                if flag in rest:
                    i = rest.index(flag)
                    val = rest[i + 1] if len(rest) > i + 1 else None
                    rest = rest[:i] + rest[i + 2:]
                    if flag == "--amends":
                        amends = val
                    else:
                        note = val
            changes = {}
            for item in rest:
                if "=" not in item:
                    raise ProcessError(f"expected CHANNEL=dB, got {item!r}")
                code, _, db = item.partition("=")
                changes[code] = db
            rec = p.record_amp_gain(changes, read_as=read_as, note=note, amends=amends)
            print(f"{rec['id']}: amp gain " + ", ".join(f"{c} {v:+.2f} dB" for c, v in sorted(rec["channels"].items()))
                  + f" ({read_as})" + (f", replaces {amends}" if amends else ""))
            if rec["open_round"]:
                print(f"  round {rec['open_round']} is open: its titles before this change are at the old gain. "
                      f"Close it and take the re-measure as a new series.")
            else:
                print("  re-measure these channels as a new series: a level compared across this change is "
                      "corrected by it (verify_prediction), and the re-measure gives the real dB (`--measured "
                      f"--amends {rec['id']}`)")
        elif cmd == "amp-changes":
            changes = p.amp_changes()
            if not changes:
                print("no amp changes on record")
            for ch in changes:
                print(f"{ch['id']}  {ch['at']}  " + ", ".join(f"{c} {v:+.2f} dB" for c, v in sorted(ch["channels"].items()))
                      + f"  ({ch['read_as']}{', amended by ' + ch['amended_by'] if ch.get('amended_by') else ''})"
                      + (f"  -- {ch['note']}" if ch.get("note") else ""))
        elif cmd == "capture-knobs":
            rest, amend, reason = list(args), None, None
            if "--amend" in rest:
                i = rest.index("--amend")
                amend = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            if "--reason" in rest:
                i = rest.index("--reason")
                reason = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            args = rest
            if not args:
                raise ProcessError("capture-knobs needs at least one NAME=POSITION")
            knobs = {}
            for item in args:
                if "=" not in item:
                    raise ProcessError(f"expected NAME=POSITION, got {item!r}")
                name, _, pos = item.partition("=")
                knobs[name] = pos
            if amend:
                p.amend_knobs(amend, knobs, reason)
                print(f"{amend}: knobs amended -- " + ", ".join(f"{k}={v}" for k, v in sorted(knobs.items())))
                return 0
            p.set_knobs(knobs)
            print("knobs recorded: " + ", ".join(f"{k}={v}" for k, v in sorted(knobs.items())))
        elif cmd == "capture-protective":
            # Out-of-process on purpose: `autosound-tcc` routes every process WRITE through this
            # CLI under an exclusive lock, because its window and its model's MCP surface can both
            # write. One implementation of "record a move" beats an in-process copy that drifts.
            if not args:
                raise ProcessError("capture-protective needs a channel")
            rest = list(args)
            source, amend, reason = "user", None, None
            for flag, into in (("--source", "source"), ("--amend", "amend"), ("--reason", "reason")):
                if flag in rest:
                    i = rest.index(flag)
                    value = rest[i + 1] if len(rest) > i + 1 else None
                    if value is None:
                        raise ProcessError(f"{flag} needs a value")
                    rest = rest[:i] + rest[i + 2:]
                    if into == "source":
                        source = value
                    elif into == "amend":
                        amend = value
                    else:
                        reason = value
            if not rest:
                raise ProcessError("capture-protective needs a channel")
            channel, rest = rest[0], rest[1:]
            if rest and rest[0].upper() == "OFF":
                legs = "OFF"
            else:
                legs, i = {}, 0
                while i < len(rest):
                    kind = rest[i].lstrip("-").lower()
                    if kind not in ("hp", "lp"):
                        raise ProcessError(
                            f"expected --hp or --lp (or a bare OFF), got {rest[i]!r}")
                    legs[kind] = _leg(kind, rest[i + 1:i + 4])
                    i += 4
                if not legs:
                    raise ProcessError(
                        "give --hp/--lp, or the bare word OFF to say this channel was swept with "
                        "nothing in the chain. Saying nothing at all is a different thing and is "
                        "recorded by NOT running this command")
            # A leg the method has no model for -- a Chebyshev, recorded as typed (R48) -- is said as what it means for
            # the sweeps (#134, R49, R52): they cannot be de-embedded, so no phase decision is read through them. The
            # line said they were "de-embedded before any phase decision", and they were, as a Butterworth.
            unmodelled = [] if legs == "OFF" else [
                f"{k.upper()} {v['f']:g} {v['type']}{v['slope']}" for k, v in sorted(legs.items())
                if v["type"] not in _MODELLED_LEG_TYPES]
            cannot = ("" if not unmodelled else
                      f"; {', '.join(unmodelled)} is recorded as typed, and the method has no Chebyshev model verified "
                      f"on a DSP: the sweeps cannot be de-embedded, and every phase decision on them is refused -- "
                      f"set LR, BW or BE as the protective on the DSP and sweep again, or sweep with the protective "
                      f"filter OFF where the driver is safe without it")
            if amend:
                done = p.amend_protective(amend, channel, legs, reason or "", source=source)
                shown_legs = "OFF" if legs == "OFF" else ", ".join(
                    f"{k.upper()} {v['f']:g} {v['type']}{v['slope']}" for k, v in sorted(legs.items()))
                print(f"{amend} {channel}: corrected to {shown_legs} ({source}) — {done['reason']}{cannot}")
                return 0
            round_ = p.set_protective(channel, legs, source=source)
            shown = "OFF" if legs == "OFF" else ", ".join(
                f"{k.upper()} {v['f']:g} {v['type']}{v['slope']}" for k, v in sorted(legs.items()))
            print(f"{round_['id']} {channel}: protective {shown} — this round is RAW for that channel"
                  + (cannot or ", so its sweeps are de-embedded before any phase decision"))
        elif cmd == "listening-verdict":
            pairs, text, route, lv, note = [], None, None, None, None
            i = 0
            while i < len(args):
                a = args[i]
                if a == "--pair" and i + 1 < len(args):
                    parts = args[i + 1].split(":")
                    if len(parts) != 3:
                        raise ProcessError(f"listening-verdict: --pair is track:characteristic:ok|bad, got "
                                           f"{args[i + 1]!r}")
                    pairs.append(tuple(parts)); i += 2
                elif a == "--text" and i + 1 < len(args):
                    text = args[i + 1]; i += 2
                elif a == "--route" and i + 1 < len(args):
                    route = args[i + 1]; i += 2
                elif a == "--ledger-version" and i + 1 < len(args):
                    lv = args[i + 1]; i += 2
                elif a == "--note" and i + 1 < len(args):
                    note = args[i + 1]; i += 2
                else:
                    raise ProcessError(f"listening-verdict: unexpected {a!r}")
            e = p.record_listening_verdict(pairs, text=text, route=route, ledger_version=lv, note=note)
            shown = ", ".join(f"{x['track']} {x['characteristic']} {x['verdict']}" for x in e["pairs"])
            print(f"listening verdict banked at {e['ledger_version'] or '?'}: {shown or '(text only)'}")
        elif cmd == "listening-verdicts":
            track = characteristic = lv = None
            bank = False
            i = 0
            while i < len(args):
                a = args[i]
                if a == "--track" and i + 1 < len(args):
                    track = args[i + 1]; i += 2
                elif a == "--characteristic" and i + 1 < len(args):
                    characteristic = args[i + 1]; i += 2
                elif a == "--ledger-version" and i + 1 < len(args):
                    lv = args[i + 1]; i += 2
                elif a == "--bank":
                    bank = True; i += 1
                else:
                    raise ProcessError(f"listening-verdicts: unexpected {a!r}")
            if bank:
                for line in p.banked_ear_lines(ledger_version=lv):
                    print(line)
            else:
                for e in p.listening_verdicts(track=track, characteristic=characteristic, ledger_version=lv):
                    pairs = ", ".join(f"{x['track']} {x['characteristic']} {x['verdict']}" for x in e.get("pairs") or [])
                    print(f"{e.get('at')} [{e.get('ledger_version') or '?'}] {pairs or '(text only)'}"
                          + (f" -- {e['text']}" if e.get("text") else ""))
        elif cmd == "capture-supersede":
            if len(args) < 2:
                raise ProcessError("capture-supersede needs the WRONG title and the right one")
            p.supersede_capture(args[0], args[1], " ".join(args[2:]) or None)
            print(f"{args[0]!r} superseded by {args[1]!r} — the wrong row stays, dimmed, and the "
                  f"corrected title is recorded")
        elif cmd == "handoff":
            got = p.handoff()
            if "--json" in args:
                # hub #201 (TCC-028): the machine form a front-end reads. `next_message` is what the new
                # session is started with; TCC starts it itself instead of asking the person to type it.
                print(json.dumps(dict(got, next_message="продовжуй" if got["ok"] else None), ensure_ascii=False))
                return 0 if got["ok"] else 1
            if got["ok"]:
                print(got["resume"])
            else:
                print("NOT ready to clear the chat — what the next session would not find:")
                for item in got["missing"]:
                    print(f"  - {item}")
                print("\nNothing was written: which evidence closes a step is a decision, not this "
                      "command's. Fix what is named and run it again.")
            # S-084: said either way and never a refusal -- the exit code stays the answer above.
            for item in got["warnings"]:
                print(f"\nWARNING: {item}")
            return 0 if got["ok"] else 1
        elif cmd == "capture-skip":
            p.skip_capture(args[0], " ".join(args[1:]))
            print(f"{args[0]} skipped: {' '.join(args[1:])}")
        elif cmd == "capture-close":
            # The round closes AGAINST REW (skill #77, rule 3), whatever captured the measurements: what REW holds is
            # taken, the extra of this series is recorded, what it does not hold stays open -- and the checks run on
            # what was taken. `--no-rew` closes on the record alone, and the record says so.
            no_rew = "--no-rew" in args
            args = [a for a in args if a != "--no-rew"]
            checked = None
            # A folder that is no project's is said as such (#141, R46), before the look for an open round below.
            p._require_home("capture-close")
            # The journal the close appends to is read and opened for appending first (batch 2's re-review, Out of
            # Scope 5): one that cannot be refuses before a line is printed. With REW down the verb said "closing on
            # the record alone" and then refused at the close's own append.
            p._require_journal()
            # The round this verb closes, read once, before REW (#141, R7): the reconcile, the checks and the close each
            # take the project's lock for themselves, and another writer can close or replace the round between them.
            # The close is of this round or refused, naming both -- it closed the round open by then, one this verb
            # never read against REW nor checked. No round open is refused here, before a line is printed.
            pinned = p._require_capture()[1]["id"]
            # What this verb wrote before a later hold stopped it, for the line that says so (R9, `_close_stopped`).
            landed = []
            if not no_rew:
                rew_api = _load_sibling("rew_api.py")
                if rew_api is None:
                    raise ProcessError(f"rew_api.py could not be loaded{_load_failure('rew_api.py')} -- the round "
                                       "cannot be read against REW, and nothing was written; `capture-close "
                                       "--no-rew` closes it on the record alone")
                try:
                    # A listing that is not a map of measurements raises (`RewProtocolError`, #134): never `{}`.
                    titles = [m.get("title", "") for m in rew_api.get_measurements().values()]
                except Exception as exc:  # noqa: BLE001 -- REW's own states are said below; anything else is raised
                    # Only REW's states close on the record alone (#134, T I4, F M-11, H minor 5), each said as what
                    # it was, by the state on the exception's class, with what was raised: REW down, REW answering
                    # something that is no measurement list, REW answering with an error. Anything else -- an
                    # address that is none, a bug -- is raised before a line is printed, the round left open.
                    rew_said = getattr(type(exc), "rew_state", None)
                    raised = f"{type(exc).__name__}: {str(exc)[:120]}"
                    if rew_said == "unavailable":
                        print(f"  REW not reached ({raised}): closing on the record alone")
                    elif rew_said == "protocol":
                        print(f"  REW answered something that is not a measurement list ({raised}): closing on the "
                              "record alone")
                    elif rew_said == "error" or isinstance(exc, urllib.error.HTTPError):
                        print(f"  REW answered with an error ({raised}): closing on the record alone")
                    else:
                        raise
                else:
                    # Outside the `try`: the reconcile's own refusals -- the state it cannot read, naming.py that
                    # cannot be loaded -- are this verb's refusal (1), never "not read against REW" over a round that
                    # then closed unchecked (T I4's probe), and a bug in it is 70.
                    checked = p.reconcile_captures(titles, round_id=pinned)
                    landed.append(f"the reconcile of {pinned}")
            missed = "the close"
            try:
                if checked is not None:
                    print(f"  read against REW: {len(checked['matched'])} of {len(checked['expected'])} on the list "
                          "held"
                          + (f", {len(p.load(strict=True)['capture'].get('reconciled', {}).get('extra') or [])} taken "
                             "beyond it")
                          + (f", {len(checked['renames'])} under another spelling" if checked["renames"] else ""))
                    for actual, canonical in sorted(checked["renames"].items()):
                        print(f"    REW holds `{actual}` for `{canonical}` -- rename it there (REW's uuid survives)")
                    now = p.load(strict=True)["capture"]
                    taken_now = sorted(t for t in now.get("taken") or {} if _is_taken(now, t))   # N17: no superseded
                    if taken_now:
                        missed = "the checks and the close"
                        try:
                            p.check_captures(taken_now, round_id=pinned)
                            landed.append("its checks")
                            print(f"  checks run on {len(taken_now)} taken capture(s) (capture-check for the verdicts)")
                        except Exception as exc:  # noqa: BLE001 -- the close goes on (exit 0): the checks are not the close
                            # ...but never over a refusal (#134, batch 3's re-review O3): the state that cannot be read
                            # at this stage, and the checks' journal line refused after their state write landed, are
                            # this verb's refusal, whole, the round left open. They read as "checks not run", and the
                            # close went on over a read it could not make, or over a state write whose event is missing.
                            # So is the project's lock held past the wait at the checks (#141): 75, safe to retry, the
                            # round open -- never a round closed unchecked because another writer held the lock for a
                            # moment. And so is the round another writer closed or replaced meanwhile (Task 2's review):
                            # read as "checks not run", the close went on over the round that replaced it.
                            if getattr(type(exc), "is_unreadable", False) or getattr(type(exc), "state_written", False) \
                                    or getattr(type(exc), "is_busy", False) or getattr(type(exc), "round_moved", False):
                                raise
                            # Said as what happens (#134): the round is closing, so a check cannot be run on it again.
                            print(f"  checks not run on the taken captures ({type(exc).__name__}: {str(exc)[:160]}): "
                                  "the round closes on the record, unchecked")
                        missed = "the close"
                outstanding = p.capture_outstanding(p.load(strict=True))   # what the close is about to say (#136)
                round_ = p.close_capture(" ".join(args) or None, round_id=pinned)
            except Exception as exc:  # noqa: BLE001 -- a later hold's stop is said below; anything else raises as it is
                # The reconcile landed, and maybe the checks: a busy lock or a moved round at a later hold says that
                # (R9), never write_lock's "nothing was written", nor the checks' "run capture-check again".
                stopped = _close_stopped(exc, landed, missed)
                if stopped is None:
                    raise
                print(stopped[0], file=sys.stderr)
                return stopped[1]
            print(
                f"{round_['id']} closed: {sum(1 for t in round_['taken'] if _is_taken(round_, t))} taken, "
                f"{len(round_['skipped'])} skipped, {len(outstanding)} outstanding"
                + (f", {len(_outstanding_optional(round_))} optional left" if _outstanding_optional(round_) else "")
                + ("" if round_["closed_against"]["rew"] else " -- not checked against REW")
            )
            for title in outstanding:
                print(f"  OUTSTANDING: {title}")
            if not round_.get("knobs"):
                print("  NO KNOBS RECORDED for this round. Whatever sits outside the DSP -- a "
                      "remote knob, a bass control, a fader -- is part of what these sweeps "
                      "measured, and nothing else on disk carries it. Two series taken at "
                      "different positions cannot be compared later, and the difference will "
                      "look like a calibration offset. `capture-knobs SubRC=4/4 …` (RES-007)")
        elif cmd == "check":
            state = p.load(strict=True)   # a verdict: never 0 off a read that failed (#136)
            bad = p.unevidenced_done_steps(state)
            for entry in bad:
                print(f"NO EVIDENCE: {entry['id']} {entry.get('name','')}")
            unbacked = [e for e in p.unbacked_done_steps(state) if e not in bad]
            for entry in unbacked:
                print(
                    f"UNBACKED: {entry['id']} {entry.get('name','')} "
                    f"-- evidence resolves to nothing: {'; '.join(map(str, entry['evidence']))}"
                )
            unloaded = _naming_unloaded() if unbacked else ""
            if unloaded:                              # the grammar's absence, not the evidence (the final review's M2)
                print(f"  {unloaded}: a step closed on one reads as UNBACKED here")
            print(
                f"{len(bad)} done step(s) without evidence, "
                f"{len(unbacked)} whose evidence resolves to nothing"
            )
            return 1 if (bad or unbacked) else 0
        else:      # a verb `VERB_FLAGS` lists and nothing here dispatches -- refused above, kept as the last word
            print(_USAGE, file=sys.stderr)
            return EXIT_USAGE
    except ProcessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", EXIT_NO)      # 2 for a usage error, 69 for REW down, else 1
    except Exception as exc:  # noqa: BLE001 -- the catch-all (#134, audit T-23): a bug exits 70, not 1
        # An IndexError is one of them (R36): too few arguments are refused before the verb runs (`_args_counted`), so
        # one raised inside a verb is a bug, and its traceback is printed -- it exited 1, with no traceback.
        # Read off the exception's CLASS, never the instance (#134): on Python 3.9 an `HTTPError` built without a body
        # answers any attribute it lacks with `KeyError: 'file'`, which would crash this handler instead of naming it.
        # The project's writer lock first (#141, `write_lock.py`), neither of its two a `ProcessError`: another writer
        # held it past the wait -- 75, its one `busy:` line, nothing written, safe to retry -- or the wait,
        # AUTOSOUND_LOCK_TIMEOUT_S, is no number of seconds: a usage error, said before anything was taken.
        if getattr(type(exc), "is_busy", False):
            return _write_lock().busy_exit(exc)
        if getattr(type(exc), "exit_code", None) == EXIT_USAGE:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        if getattr(type(exc), "is_unreadable", False):
            if cmd == "handoff" and "--json" in args:
                # Its own shape, the keys of its answer (#136): a front-end reads this verb's stdout, and an empty one
                # read as "this method cannot answer" (TCC: "update the method"). TCC shows `missing`.
                print(json.dumps({"ok": False, "missing": [str(exc)], "phase": None, "resume": None, "warnings": [],
                                  "next_message": None}, ensure_ascii=False))
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_NO
        rew_said = getattr(type(exc), "rew_state", None)
        # A filter write REW acknowledged and nobody could read back (`rew_unchecked`, rew_api's H 10) says so in its
        # own words, and a write REW did not keep may be partly in REW (m3): neither is "nothing was written". No verb
        # writes filters today; the line stays true the day one does.
        if getattr(type(exc), "rew_unchecked", False):
            after = ""
        elif rew_said == "write_mismatch":
            after = " -- REW may hold part of the write: check REW's EQ before going on"
        else:
            after = " -- nothing was written"
        if rew_said == "unavailable":
            print(f"error: {exc}{after}", file=sys.stderr)
            return EXIT_REW_UNAVAILABLE
        if rew_said == "error" or isinstance(exc, urllib.error.HTTPError):
            # REW answered with an error, its 4xx/5xx and its words (`rew_api._open` puts them on the message): REW's
            # answer too, a refusal in its words (F M-4, H minor 1), where it was a bug's 70 with a traceback. Matched
            # as the stdlib's one `HTTPError` class -- one in every copy -- or by the state its class names.
            print(f"error: REW answered with an error: {exc}{after}", file=sys.stderr)
            return EXIT_NO
        if rew_said is not None:
            # Every other state of REW's is REW's answer, not a bug of the method (#134, R47c): "protocol" (an answer
            # this method cannot read -- `capture-import` reading REW's list itself), "config" (a `REW_API_URL` that
            # is no address: `capture-import` asking REW meets it, H I-5), and "write_mismatch", "not_found" and
            # "ambiguous", which no verb meets here today: a refusal in its own words, exit 1, where it was a bug's
            # 70. A `not_found` or an `ambiguous` is a `KeyError`, whose `str` puts quotes round its words; its words
            # are said as they are.
            said = exc.args[0] if isinstance(exc, KeyError) and len(exc.args) == 1 else exc
            print(f"error: {said}{after}", file=sys.stderr)
            return EXIT_NO
        traceback.print_exc()
        print(f"error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_UNEXPECTED
    return EXIT_OK


if __name__ == "__main__":
    # issue #21: a code page must not destroy a result. Run from a subdirectory, so the sibling
    # modules' own directory has to go on the path before `console` can be found at all.
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import console
    console.install()
    sys.exit(_main(sys.argv))
