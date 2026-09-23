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

import json
import os
import re
import sys
from datetime import datetime, timezone

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
# the report itself (release review 2026-09-09).
EV_SESSION_CLOSED = "session_closed"
# What the Arbiter ruled, as itself. Their half of the conversation was in no machine file at all:
# the only surviving trace of an answer was a hand-typed evidence string, and a constraint the user
# set was invisible to the next session unless it happened to be re-read out of prose (SCR-030).
EV_USER_DECISION = "user_decision"
# Which checkout of the method wrote what follows (autosound-hub HUB-002). The header of the
# journal, and of every later run that came from a different commit -- see `Process._stamp`.
EV_WRITTEN_BY = "written_by"


class ProcessError(ValueError):
    """A transition the process model refuses — e.g. a done step with no evidence."""


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
    """`acoustics.flaws[]` from `project.json`, or None if the file cannot be read.

    Read as plain JSON rather than through `project.py`: this module is imported BY consumers that
    already load these files their own way, and a gate that cannot run because an import failed is
    a gate that silently stops gating. None means "no opinion" for the same reason.
    """
    try:
        with open(os.path.join(project_dir, "project.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    profile = data.get("project", data)
    return list(((profile.get("acoustics") or {}).get("flaws")) or [])


#: `flaw_map.classify` writes this on a peak row it could not check, and this gate reads it back.
#: Imported by VALUE rather than by module, for the same reason `_flaw_map_entries` reads raw JSON:
#: a gate that cannot run because an import failed is a gate that silently stops gating. The two
#: copies are held together by `flaw_map`'s own selftest.
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
    root = os.path.join(project_dir, "process", "journal.jsonl")
    try:
        with open(root, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return False
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue                      # a torn last line is skipped, not fatal (the file's rule)
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
    if channel in (round_.get("taken") or {}) or any(
            str(t).startswith(f"{channel}_") or str(t).startswith(f"{channel} ")
            for t in (round_.get("taken") or {})):
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
    if _flaw_map_entries(project_dir) is None:
        return  # no readable project.json at all is contract.py's complaint, not this one
    entries = _flaw_map_entries(project_dir)
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

    Deliberately the SAME answer `contract.py check --gate` gives, computed by the same code —
    two implementations of "is intake finished" would eventually disagree, and the one nobody runs
    would be the one that says yes.
    """
    try:
        going, came_from = int(phase), int(previous) if previous is not None else -99
    except (TypeError, ValueError):
        return
    if going < _INTAKE_REQUIRED_FROM or came_from >= going:
        return  # re-entry and going back are always allowed, same rule as every gate here
    contract = _load_sibling("contract.py")
    if contract is None:
        return  # cannot check is not the same as failed
    try:
        report = contract.check_project(project_dir, skip_rew=True)
    except Exception:  # noqa: BLE001 — a checker that raises must not become a wall
        return
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


def _load_sibling(name):
    """Load a `rew_tool/` module by path. Same reason as `_load_naming`: these are loaded by path
    everywhere so that names like `state` stay off the global import path."""
    import importlib.util

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), name)
    try:
        spec = importlib.util.spec_from_file_location(f"_process_{name[:-3]}", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001
        return None


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
    """`dsp_profile.py` from the same checkout, by path — same reason as `_load_naming`."""
    import importlib.util

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dsp_profile.py"
    )
    try:
        spec = importlib.util.spec_from_file_location("_process_dsp_profile", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 — an unloadable sibling must not make the gate crash
        return None


def _require_profile_facts(phase, previous, project_dir):
    """Refuse to enter a phase whose arithmetic needs a fact the profile has never recorded.

    The one that hurts is `sample_rate_hz`: phase 1 converts every delay into samples, and a rate
    nobody wrote down is a rate somebody assumes. Observed on a real project (2026-08-11) — a Helix
    profile with no rate, no slot counts and no EQ or crossover description at all, reporting
    nothing open because those keys were absent rather than null.
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
    module = _load_dsp_profile_module()
    if module is None:
        return
    try:
        with open(os.path.join(project_dir, "dsp_profile.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return  # no readable profile at all is contract.py's complaint, not this gate's
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
    """A `rew_tool/<name>.py` module from the same checkout, by path (see `_load_naming`)."""
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), name + ".py")
    try:
        spec = importlib.util.spec_from_file_location("_process_" + name, path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 -- the caller decides whether "cannot load" is fatal
        return None


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
    import importlib.util

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "naming.py")
    try:
        spec = importlib.util.spec_from_file_location("_process_naming", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 -- any failure here means "cannot tell", never "invalid"
        return None


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


def _continue_block(project_dir):
    """Does `tuning-changelog` carry its ▶️ CONTINUE block? None when there is no such file.

    None means "no opinion", the same answer `_flaw_map_entries` gives for an unreadable project:
    a project that keeps no prose changelog is not failing a check it never opted into.
    """
    for name in ("tuning-changelog.md", "tuning-changelog"):
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    return "CONTINUE" in fh.read()
            except OSError:
                return None
    return None


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


def _outstanding(round_):
    """Expected captures of one round that are neither taken nor skipped."""
    return [
        title
        for title in round_.get("expected", [])
        if not _is_taken(round_, title) and title not in round_.get("skipped", {})
    ]


def _is_taken(round_, title):
    """Taken AND still standing: a superseded row is evidence of a typo, not of a measurement."""
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
    def load(self):
        """The current slice. A missing or unreadable file reads as an empty process, not an error:
        a project that has never run should show an empty plan, not a traceback."""
        try:
            with open(self.state_path, encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, ValueError):
            return _empty_state()
        base = _empty_state()
        base.update(state)
        for phase, entry in base["phases"].items():
            entry.setdefault("title", PHASE_TITLES.get(phase, phase))
        return base

    def events(self, limit=None, kinds=None):
        """Journal entries oldest-first. `kinds` filters by event type."""
        out = []
        try:
            with open(self.journal_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue  # a torn last line must not hide the rest of the history
                    if kinds and event.get("type") not in kinds:
                        continue
                    out.append(event)
        except OSError:
            return []
        return out[-limit:] if limit else out

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
        """
        phase = str(phase)
        if phase not in PHASES:
            raise ProcessError(f"unknown phase {phase!r}; known: {', '.join(PHASES)}")
        state = self.load()
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
        if previous and previous != phase:
            state["phases"][previous]["status"] = PHASE_DONE
        state["phases"][phase]["status"] = PHASE_CURRENT
        state["active_phase"] = phase
        self._write(state)
        self._append(EV_PHASE_ENTERED, phase=phase, previous=previous, note=note)
        return state

    def add_step(self, step_id, name, source=SOURCE_SKILL, phase=None, covers=None):
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
        state = self.load()
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

    def start_attempt(self, step_id):
        """Begin (or re-begin) a step. A second call is attempt 2 — the redo is recorded, not
        hidden, so "we tried this twice" survives into the plan the Arbiter reads."""
        state = self.load()
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
        state_now = self.load()
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
            raise ProcessError(
                f"step {step_id!r} has evidence, but none of it resolves: "
                + "; ".join(repr(str(e)) for e in evidence)
                + ". At least one item must be checkable rather than described — a REW measurement "
                "name in the grammar (`tw-L_1 (rta)`), a ledger version that exists (`v_003`), or "
                "a project file that exists (`autosound_context.md`). Describing the work is not "
                "recording it: write the artefact first, then close the step against it."
            )
        state = self.load()
        entry = self._require(state, step_id)
        entry["status"] = STEP_DONE
        entry["skip"] = False
        entry["evidence"] = sorted(set(entry.get("evidence", [])) | set(map(str, evidence)))
        self._write(state)
        self._append(EV_STEP_DONE, step=step_id, evidence=entry["evidence"])
        return entry

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
        state = self.load()
        entry = self._require(state, step_id)
        entry["status"] = STEP_SKIPPED
        entry["skip"] = True
        self._write(state)
        self._append(EV_STEP_SKIPPED, step=step_id, superseded_by=superseded_by, reason=reason)
        return entry

    def block_step(self, step_id, reason):
        """Mark a step blocked — waiting on a measurement, a part, the car being available."""
        state = self.load()
        entry = self._require(state, step_id)
        entry["status"] = STEP_BLOCKED
        entry["blocked_reason"] = reason
        self._write(state)
        self._append(EV_STEP_BLOCKED, step=step_id, reason=reason)
        return entry

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
        state = self.load()
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
    def start_capture(self, version, expected=(), phase=None, note=None, step=None, origin=None, under=None,
                      level=None, level_read_as=None):
        """Open a capture round: what was asked for, at which `_N`, in which phase.

        `version` is the series number the titles carry (`_N`); a round opened with a ledger version
        (`v_001`) is still found, since `protective_record_for` matches either -- but the two are
        different counters (`naming-and-structure.md §1a/§5), and neither is derived from the other.
        Which one this round means is now RECORDED (`version_kind`) instead of left to a reader's
        guess, and a ledger version is CHECKED against the snapshots on disk.

        **The ledger is a precondition of a ledger-bound round, not of the capture flow** (TCC-022,
        the Arbiter's stopper 2026-09-20). A Phase-0 baseline is measured before anything is banked
        and opens at `_1` with no ledger at all -- that is correct and stays correct. Naming a
        `v_NNN` says the opposite: that these measurements were taken under a CONFIGURATION, and a
        round pointing at a version nobody banked cannot answer which one, while still looking
        complete. Four such rounds were opened in a row on a project made by TCC's Copy car -- which
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
                      "  - the measurements are a baseline, taken before anything is banked -> "
                      "open the round at its SERIES number instead (`capture-start 1 ...`), which "
                      "is what Phase 0 does and needs no ledger."
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
            banked = _ledger_versions(self.project_dir)
            match = _LEDGER_RE.fullmatch(str(under).strip())
            if not match or str(int(match.group(1))) not in banked:
                raise ProcessError(f"--under {under!r}: not a banked ledger version"
                                   + (f" (banked: {', '.join('v_%03d' % int(v) for v in sorted(banked, key=int))})"
                                      if banked else " -- this project has no ledger yet"))
        # S-026: the level a series was measured at is a condition of the SERIES, as a quantity. It sat in the
        # taste profile as «7 лампочок майстра», unreadable as dB and gone the moment the file stayed behind.
        level_rec = None
        if level is not None or level_read_as is not None:
            if level is not None and not re.search(r"-?\d+(\.\d+)?\s*dB", str(level)):
                raise ProcessError(f"--level {level!r}: a level is a quantity in dB (\"-25 dB rel. max\"); "
                                   "how it is read off the device goes in --level-read-as")
            level_rec = {"value": None if level is None else str(level).strip(),
                         "read_as": None if level_read_as is None else str(level_read_as).strip()}
        state = self.load()
        previous = state.get("capture")
        if previous and not previous.get("closed"):
            self._close_capture(state, previous, reason="superseded")
        number = int(previous.get("n", 0)) + 1 if previous else 1
        expected = [str(item) for item in (expected or []) if str(item).strip()]
        round_ = {
            "id": "cap_%03d" % number,
            "n": number,
            "phase": str(phase) if phase is not None else state.get("active_phase"),
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
            "taken": {},
            "skipped": {},
            "note": note,
        }
        state["capture"] = round_
        self._write(state)
        self._append(
            EV_CAPTURE_ISSUED,
            capture=round_["id"],
            phase=round_["phase"],
            version=round_["version"],
            version_kind=kind,
            origin=origin,
            under=round_["under"],
            level=level_rec,
            expected=expected,
            step=step,
            note=note,
        )
        return round_

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

    def capture_import(self, series, titles, binds, knobs, late=None):
        """Register measurements REW already holds as rounds of THIS project, one round per DSP state (#58 P3).

        A fast session registered 21 titles in 5 seconds as one round covering TWO DSP states (variants B and C),
        ignored the knobs warning three times, and got past a foreign-series refusal by inventing a round. The
        honest form of all three: the series is this project's (`_refuse_foreign_series` applies); each title's
        MODIFIER is bound to the ledger version it was measured under (`binds`, `{"": "v_012", "C": "v_013"}` --
        "" is the plain title), and a title whose modifier is not bound refuses the whole import rather than land
        in the wrong round; the knobs are required, not warned about; and a registration after the fact says so,
        with its reason (`late`), instead of looking like it happened in the car. Returns the rounds opened."""
        _naming = _load_naming()
        if _naming is None:
            raise ProcessError("the title grammar (naming.py) cannot be loaded -- nothing was imported")
        if not isinstance(knobs, dict) or not knobs:
            raise ProcessError("capture-import needs the knobs as they stood (NAME=POS): two series cannot be "
                               "compared on the assumption that nobody touched anything")
        glossary = _naming.Glossary.for_project(self.project_dir)
        groups, stray = {}, []
        for title in titles:
            parts = _naming.parse_name(title, glossary)
            if not parts or str(parts.get("version_n")) != str(int(str(series).lstrip("_"))):
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
        known = [e.get("id") for e in self.events(kinds=(EV_AMP_GAIN,))]
        if amends and amends not in known:
            raise ProcessError(f"no amp change {amends!r} on record" + (f" (on record: {', '.join(known)})" if known else ""))
        change_id = f"amp-{len(known) + 1}"
        live = self.load().get("capture") or {}
        open_round = live.get("id") if live and not live.get("closed") else None
        self._append(EV_AMP_GAIN, id=change_id, channels=clean, read_as=read_as, note=note, amends=amends,
                     open_round=open_round)
        return {"id": change_id, "channels": clean, "read_as": read_as, "amends": amends, "open_round": open_round}

    def amp_changes(self):
        """Every amp change on record, oldest first, with a later `amends` folded into the change it corrects."""
        out, by_id = [], {}
        for pos, e in enumerate(self.events()):
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
        events = self.events()
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
        live = self.load().get("capture") or {}
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
        for event in self.events(kinds=(EV_CAPTURE_ISSUED, EV_CAPTURE_KNOBS)):
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
        live = (self.load().get("capture") or {})
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
        for event in self.events(kinds=(EV_CAPTURE_ISSUED, EV_CAPTURE_TAKEN)):
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
        for event in self.events(kinds=(EV_CAPTURE_ISSUED, EV_CAPTURE_PROTECTIVE)):
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
            live = self.protective_record()
            return live if live and key(live.get("version")) == version else None
        return rounds[order[-1]]

    # -- listening verdicts (Phase 4) --
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
        state = self.load()
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
        for e in self.events(kinds=(EV_LISTENING_VERDICT,)):
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
        """`verify.py` from the same checkout, by path — same reason `_load_naming` does it."""
        import importlib.util

        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify.py")
        try:
            spec = importlib.util.spec_from_file_location("_process_verify", path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:  # noqa: BLE001 -- unavailable arithmetic is "cannot tell", never "bad"
            return None

    def check_captures(self, titles=None, verifier=None, session=False):
        """Run the skill's own verdict over the open round and record it (SCR-040).

        The arithmetic lives in `verify.py` and is called here rather than reimplemented by a
        front-end: two implementations of "is this curve usable" would drift, and the one that
        drifts is the one nobody runs standalone.

        Each verdict pins REW's `uuid`. The title is not identity -- re-take `sw_1 (sw)` and the
        name is unchanged while the data is not, so a verdict keyed by title would outlive the
        graph it judged. A measurement REW no longer holds records no uuid and reads as not ok.

        `session=True` adds the whole-session probe (Phase 0.6, `verify.session_report`) and
        records it on the round as `session` -- the ctl1->ctl3 drift is the DRIFT RECORD the
        capture sheet asks for, and it lives with the round it measured.
        """
        state, round_ = self._require_capture()
        verifier = self._load_verifier() if verifier is None else verifier
        if verifier is None:
            raise ProcessError(
                "verify.py could not be loaded — cannot check captures. "
                "The curves are still there; this is the checker, not the data."
            )
        wanted = [str(t) for t in (titles or round_.get("expected") or [])]
        if not wanted:
            raise ProcessError("this round expects no captures — nothing to check")
        verdicts = verifier.verify(wanted)
        for verdict in verdicts:
            title = verdict["name"]
            entry = round_.setdefault("taken", {}).setdefault(
                title, {"at": _now(), "planned": title in round_.get("expected", [])}
            )
            entry["verified"] = {
                "ok": bool(verdict.get("valid")),
                "exists": bool(verdict.get("exists")),
                # False for a capture the check does not apply to (an RTA): not bad, not good, and
                # not a reason to hold a step (skill #29). Dropped here, it read as "bad" below.
                "applicable": verdict.get("applicable", True) is not False,
                "uuid": (verdict.get("stats") or {}).get("uuid"),
                "at": _now(),
                "issues": list(verdict.get("issues") or []),
            }
        # The capture rate vs the DSP's PROCESSING rate -- said ONCE per check, never a failure
        # (the user's ruling, 2026-08-25): a UMIK-1 captures at 48k under a 96k Helix, and if
        # capturing at the processing rate is impossible, we work with what there is. What must
        # never happen silently is the two being confused -- delays in samples derive from the
        # PROCESSING rate regardless of what the microphone recorded at.
        rate_note = None
        capture_rates = sorted({v["stats"]["capture_rate_hz"] for v in verdicts
                                if v.get("stats", {}).get("capture_rate_hz")})
        if capture_rates:
            module = _load_dsp_profile_module()
            proc_rate = None
            if module is not None:
                try:
                    with open(os.path.join(self.project_dir, "dsp_profile.json"), encoding="utf-8") as f:
                        proc_rate = module.processing_rate_hz(json.load(f))
                except (OSError, ValueError, AttributeError):
                    proc_rate = None
            if proc_rate and any(r != proc_rate for r in capture_rates):
                rate_note = (f"captured at {'/'.join(str(r) for r in capture_rates)} Hz; the DSP "
                             f"processes at {proc_rate:g} Hz -- fine, working with it. Delays in "
                             f"samples derive from the PROCESSING rate; the capture rate stays with "
                             f"the measurement")
        if session and hasattr(verifier, "session_report"):
            probe = verifier.session_report(verdicts, processing_rate_hz=proc_rate if capture_rates else None)
            round_["session"] = {"at": _now(), "spread": probe["spread"], "drift": probe["drift"],
                                 "capture_rates_hz": probe["capture_rates_hz"], "rows": probe["rows"]}
        self._write(state)
        self._append(
            EV_CAPTURE_VERIFIED,
            capture=round_["id"],
            step=round_.get("step"),
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
        return round_

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
            entry = (round_.get("taken") or {}).get(title)
            verified = (entry or {}).get("verified") or {}
            if verified.get("applicable") is False:
                continue  # checked, and the check does not apply to it (an RTA): not unusable (#29)
            if not entry or not verified.get("ok"):
                out.append(title)
        return out

    def close_capture(self, reason=None):
        """Close the open round. What is neither taken nor skipped stays that way, on the record."""
        state, round_ = self._require_capture()
        self._close_capture(state, round_, reason=reason)
        self._write(state)
        return round_

    def capture_outstanding(self, state=None):
        """Expected captures of the OPEN round that are neither taken nor skipped."""
        state = state or self.load()
        round_ = state.get("capture") or {}
        if not round_ or round_.get("closed"):
            return []
        return _outstanding(round_)

    def _require_capture(self):
        state = self.load()
        round_ = state.get("capture")
        if not round_ or round_.get("closed"):
            raise ProcessError(
                "no capture round is open: `capture-start <version> [expected ...]` first. "
                "A round says which pass these measurements belong to -- without one they are "
                "loose titles that only REW remembers."
            )
        return state, round_

    def _close_capture(self, state, round_, reason=None):
        # Worked out BEFORE the round is marked closed: `capture_outstanding` answers about the
        # open round, and it is the closing event that most needs the answer.
        outstanding = _outstanding(round_)
        round_["closed"] = _now()
        round_["closed_reason"] = reason
        self._append(
            EV_CAPTURE_CLOSED,
            capture=round_["id"],
            version=round_["version"],
            taken=sorted(round_.get("taken", {})),
            skipped=sorted(round_.get("skipped", {})),
            # Named rather than left to be worked out: a round that ends with expected captures
            # neither taken nor skipped is the shape план-факт exists to show.
            outstanding=outstanding,
            # A round with no knob record closes anyway -- refusing would strand a session mid-car
            # -- but it closes SAYING so, at the one moment the answer is still in the room. The
            # knobs are the part of the setup that lives outside every file, so a reader months
            # later has no way to recover them (hub RES-007).
            knobs=dict(round_.get("knobs") or {}),
            reason=reason,
        )

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
            phase=str(phase) if phase is not None else self.load().get("active_phase"),
            invalidates=invalidates,
        )
        return {"question": question, "answer": answer, "step": step}

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
            phase=str(phase) if phase is not None else self.load().get("active_phase"),
        )
        return {"harness": harness, "model": model, "resumed": bool(resumed)}

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
                "taken": len(round_.get("taken", {})), "skipped": len(round_.get("skipped", {})),
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

        `{"ok", "missing": [...], "phase", "resume"}`. It checks and writes nothing: which evidence
        closes a step is a decision, the same split `session-close` already has.
        """
        state = self.load()
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
            missing.append(
                "done steps whose evidence resolves to nothing on disk: "
                + ", ".join(str(e.get("id")) for e in unbacked)
                + " — the chat is about to go, and prose that pointed at it goes with it")
        if not _ledger_versions(self.project_dir):
            missing.append(
                "no ledger snapshot on disk (`state/<preset>/v_NNN.json`) — the next session reads "
                "the DSP state from there, and from nowhere else. `apply.propose` banks one")
        changelog = _continue_block(self.project_dir)
        if changelog is not None and not changelog:
            missing.append(
                "`tuning-changelog` has no ▶️ CONTINUE block — it is the human-readable cross-check "
                "the next session reads beside the machine files, and the one a person opens first")
        resume = None
        if not missing:
            keep = ""
            last = state.get("capture") or {}
            if last.get("taken"):
                keep = (" Keep the REW session with this round's captures open — the titles are the "
                        "only identity they have.")
            resume = (f"State is on disk: phase {phase}, "
                      f"{len(self.plan_for(phase, state))} step(s) in its plan, ledger HEAD present. "
                      f"Clear the chat and say «продовжуй» in the new one.{keep}")
        return {"ok": not missing, "missing": missing, "phase": phase, "resume": resume}

    def set_target(self, preset, curve):
        """The active target curve for a preset — a pointer, the curve itself lives elsewhere."""
        state = self.load()
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
        state["updated"] = _now()
        validate(state)
        os.makedirs(self.dir, exist_ok=True)  # first real write is what creates `process/`
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
        # Rename rather than write in place: a crash mid-write would otherwise leave truncated
        # JSON, and the next session would read an empty process and think nothing had happened.
        os.replace(tmp, self.state_path)

    def _last_written_by(self):
        """The sha in the last header event, or None when the journal carries no header at all.

        None is not `""`: a journal that has never recorded a writer must get a header even when
        the writer cannot be told, otherwise "asked, could not be told" and "never asked" are the
        same silence.
        """
        seen = self.events(kinds=(EV_WRITTEN_BY,))
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
        self._stamped = True  # decided first: one attempt per run, whatever it finds
        sha = _writer_sha()
        if sha == self._last_written_by():
            return
        self._append(EV_WRITTEN_BY, skill_sha=sha)

    def _append(self, event_type, **payload):
        if event_type != EV_WRITTEN_BY:
            self._stamp()
        event = {"at": _now(), "type": event_type}
        event.update({k: v for k, v in payload.items() if v is not None})
        os.makedirs(self.dir, exist_ok=True)
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event


# --------------------------------------------------------------------------- CLI
# The skill drives its tooling from Bash (SKILL.md's guardrails run `python rew_tool/...`), so the
# writer needs a command line, not just an importable class -- same reason `state.py` has one.

_USAGE = """usage: process.py <process-dir> <command> [args]

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
                                              stopped" cannot be said over an open round
  decision <question> <answer> [step] [--invalidates X]   what the Arbiter ruled, as itself
  capture-start <version> [title ...] [--step ID] [--origin <project>:<their _N>]
      [--under v_NNN] [--level "-25 dB rel. max"] [--level-read-as "7 lamps"]
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
                                        state; unbound modifiers and missing knobs refuse (#58 P3)
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
  handoff                               is everything the NEXT session needs on disk? Prints the
                                        resume line when it is, names what is missing when it is
                                        not (exit 1), and writes nothing either way (S-044)
  capture-skip <title> <reason>         deliberately NOT taken, and why
  capture-close [reason]                close the round; what is outstanding is named
  check                                 done steps with no evidence, and done steps whose
                                         evidence resolves to nothing on disk
  selftest                              this module's own gates, on a throwaway project
"""


def _seed_intake(root):
    """Write the files phase −1 is supposed to produce, so a fixture can get past its own gate.

    Deliberately built through the real writers rather than as literals: if `project.py` or
    `state.py` change what a valid file looks like, this fixture finds out at the same moment the
    rest of the skill does.
    """
    project_mod = _load_sibling("project.py")
    profile_mod = _load_sibling("dsp_profile.py")
    state_mod = _load_sibling(os.path.join("state", "state.py"))
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


def _selftest():
    """The refusals, exercised. This module is the one with the most of them — evidence must exist
    and must resolve (SCR-035), a round's captures must be usable (SCR-040), phase 0 must record a
    target (SCR-036) and now its flaw map (SCR-044) — and it was the only one of the seven with no
    selftest at all, so every one of those gates was a thing nobody had run since it was written.
    """
    import tempfile

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
    am = Process(os.path.join(tempfile.mkdtemp(prefix="autosound_amend_"), "process"))
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
    amend_p = Process(os.path.join(root, "process-amend"))
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
    imp = Process(os.path.join(root, "process-import"))
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
    amp = Process(os.path.join(root, "process-amp"))
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
    # #57 P0 / S-026: a round records the ledger version it was taken under and the level as a quantity; a
    # level with no dB in it, or an under that is not banked, is refused.
    lvl = Process(os.path.join(root, "process-level"))
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
    # the room -- and closes anyway, because refusing would strand a session mid-car.
    bare = Process(os.path.join(root, "process-bare"))
    bare.enter_phase("0")
    bare.start_capture("7", expected=["m-L_7 (sw)"], phase="0")
    bare_out = subprocess.run([sys.executable, _mod, bare.dir, "capture-close"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert bare_out.returncode == 0 and "NO KNOBS RECORDED" in bare_out.stdout, bare_out
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
        stamped = os.path.join(tempfile.mkdtemp(prefix="autosound_stamp_"), "process")
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
        blind = os.path.join(tempfile.mkdtemp(prefix="autosound_blind_"), "process")
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
    stop_root = os.path.join(tempfile.mkdtemp(prefix="autosound_stop_"), "process")
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

    # ── S-048: another project's series number does not walk in unannounced ──────────────────
    # Fails on the old code at the refusal: `start_capture` took any number, and a session that
    # had ALREADY SAID the set was «серія _49 зі старого проєкту» opened the round as series 49,
    # writing another build's numbering into this project's record as its own.
    fs = Process(os.path.join(tempfile.mkdtemp(prefix="autosound_series_"), "process"))
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
            Process(os.path.join(tempfile.mkdtemp(prefix="autosound_half_"), "process")).start_capture(
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
    cap = Process(os.path.join(tempfile.mkdtemp(prefix="autosound_cap_"), "process"))
    try:
        cap.start_capture("v_001", ["w-L_1 (sw)"])
        raise AssertionError("a round was opened at a ledger version nobody had banked")
    except ProcessError as exc:
        # The refusal has to carry BOTH ways on, because they are different questions -- bank the
        # state, or open the round at its series number because nothing is banked yet on purpose.
        assert "no ledger at all" in str(exc) and "capture-start 1" in str(exc), str(exc)
        assert "apply.propose" in str(exc), str(exc)
    # A baseline round needs no ledger and says so: `series` is explicitly not ledger-bound.
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
    cv = Process(os.path.join(tempfile.mkdtemp(prefix="autosound_covers_"), "process"))
    facts = ["project.json:sources.sweep_input", "project.json:amps.front.gain_db",
             "project.json:channels.r-L.driver", "project.json:channels.r-R.driver",
             "dsp_profile.json:eq.bands_total"]
    entry = cv.add_step("0.4", "Закрити відкриті поля", phase="0", covers=facts)
    assert entry["covers"] == facts, entry
    assert entry["name"] == (
        "Закрити відкриті поля: project.json:sources.sweep_input, "
        "project.json:amps.front.gain_db, project.json:channels.r-L.driver +2"), entry["name"]
    # The name is GENERATED: passing it back composed a second time changes nothing, so a
    # front-end that re-reads and re-adds cannot stutter the summary into the title.
    again = Process(cv.dir).add_step("0.5", entry["name"], phase="0", covers=facts)
    assert again["name"] == entry["name"], again["name"]
    assert again["name"].count("+2") == 1, again["name"]
    # Blanks and duplicates are not facts; order is the caller's.
    assert cv.add_step("0.6", "x", phase="0", covers=["a", "", "a", " b "])["covers"] == ["a", "b"]
    # A step with nothing to cover is unchanged -- the field exists, the name is what was typed.
    plain = cv.add_step("0.7", "Raw baseline sweeps", phase="0")
    assert plain["covers"] == [] and plain["name"] == "Raw baseline sweeps", plain
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
    na = Process(os.path.join(tempfile.mkdtemp(prefix="autosound_na_"), "process"))
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
        "back up; an RTA the check does not apply to is kept as such and holds no step (#29); a step CARRIES what it covers and its name names the first three and counts the rest (S-031); a capture under the wrong title is SUPERSEDED and stops counting, never deleted (S-039); the handoff REFUSES while anything the next session needs is only in the chat, and prints the resume line when it is not (S-044); a series number that is not this project's is refused until its ORIGIN is on record (S-048); a round records WHICH counter its version is, refuses a `v_NNN` nobody banked with both ways on, and marks a skip planned or not (TCC-022); and a phase does not close over a flaw row that stands on an UNASKED question -- the refusal carries the titles that would settle it, and a round opened or a ruling recorded closes it (S-047). "
        f"root={root}"
    )
    return 0


def _main(argv):
    if len(argv) == 2 and argv[1] == "selftest":
        return _selftest()
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    root, cmd, args = argv[1], argv[2], argv[3:]
    p = Process(root)
    try:
        if cmd == "show":
            print(json.dumps(p.load(), indent=2, ensure_ascii=False))
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
                if token.startswith("--review") or token.startswith("--mode"):
                    key = token.lstrip("-").split("=", 1)[0]
                    if "=" in token:
                        flags[key] = token.split("=", 1)[1]
                    else:
                        i += 1
                        flags[key] = args[i] if i < len(args) else None
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
                if token.startswith("--invalidates"):
                    invalidates = (
                        token.split("=", 1)[1] if "=" in token else (rest[i + 1] if len(rest) > i + 1 else None)
                    )
                    rest = rest[:i]
                    break
            p.record_decision(rest[0], rest[1], step=rest[2] if len(rest) > 2 else None,
                              invalidates=invalidates)
            print(f"decision recorded: {rest[1]}")
        elif cmd == "session-start":
            p.record_session(args[0], args[1], resumed=(len(args) > 2 and args[2] == "resumed"))
            print(f"session recorded: {args[0]} / {args[1]}")
        elif cmd == "session-close":
            open_ = p.open_work()
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
            if not owed:
                # Only a CLEAN stop is an event: with work still open the honest record is the
                # report above, and `session-close` exits non-zero so "we stopped" cannot be said
                # over an open round.
                p._append(EV_SESSION_CLOSED)
                print("\nrecorded: session_closed")
            return 1 if owed else 0
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
            for flag in ("--under", "--level", "--level-read-as"):
                if flag in rest:
                    i = rest.index(flag)
                    flags[flag] = rest[i + 1] if len(rest) > i + 1 else None
                    rest = rest[:i] + rest[i + 2:]
            round_ = p.start_capture(rest[0], expected=rest[1:], step=step, origin=origin,
                                     under=flags.get("--under"), level=flags.get("--level"),
                                     level_read_as=flags.get("--level-read-as"))
            print(
                f"{round_['id']} open at {round_['version']}, "
                f"{len(round_['expected'])} capture(s) expected"
                + (f", under {round_['under']}" + (f" ({round_['under_note']})" if round_.get("under_note") else "")
                   if round_.get("under") else "")
                + (f", level {round_['level']['value'] or '?'}" if round_.get("level") else "")
                + (f" — taken in {round_['origin']['project']} as _{round_['origin']['series']}, "
                   "not this project's own series"
                   if round_.get("origin") else "")
            )
        elif cmd == "capture-check":
            session = "--session" in args
            args = [a for a in args if a != "--session"]
            round_ = p.check_captures(args or None, session=session)
            if session and round_.get("session"):
                verifier = p._load_verifier()
                probe = dict(round_["session"], counts=verifier.summary(
                    [{"exists": r["exists"], "valid": r["valid"], "applicable": r.get("applicable", True)}
                     for r in round_["session"]["rows"]]),
                    processing_rate_hz=None, rate_note=None)
                print(verifier.render_session(probe))
                print()
            for title in round_.get("expected", []):
                verdict = ((round_.get("taken") or {}).get(title) or {}).get("verified") or {}
                if verdict.get("ok"):
                    print(f"OK      {title}")
                elif title in (round_.get("skipped") or {}):
                    print(f"SKIP    {title}")
                elif verdict.get("applicable") is False:
                    print(f"N/A     {title} — {'; '.join(verdict.get('issues') or [])}")
                else:
                    reason = "; ".join(verdict.get("issues") or ["не перевірено"])
                    print(f"UNUSABLE {title} — {reason}")
            left = p.unusable_captures()
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
            if not titles:
                import rew_api as _rew_api
                _naming = _load_naming()
                titles = [m.get("title", "") for m in _rew_api.get_measurements().values()
                          if (_naming.parse_name(m.get("title", "")) or {}).get("version_n") == int(series.lstrip("_"))]
            ids = p.capture_import(series, titles, binds, knobs, late=late)
            print(f"imported {len(titles)} title(s) of _{series} as {', '.join(ids)}"
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
                    if i + 3 >= len(rest):
                        raise ProcessError(
                            f"--{kind} needs three values: f type slope, e.g. --{kind} 100 LR 24. "
                            f"A leg missing any of them cannot be taken back out later")
                    legs[kind] = {"f": float(rest[i + 1]), "type": rest[i + 2].upper(),
                                  "slope": int(rest[i + 3])}
                    i += 4
                if not legs:
                    raise ProcessError(
                        "give --hp/--lp, or the bare word OFF to say this channel was swept with "
                        "nothing in the chain. Saying nothing at all is a different thing and is "
                        "recorded by NOT running this command")
            if amend:
                done = p.amend_protective(amend, channel, legs, reason or "", source=source)
                shown_legs = "OFF" if legs == "OFF" else ", ".join(
                    f"{k.upper()} {v['f']:g} {v['type']}{v['slope']}" for k, v in sorted(legs.items()))
                print(f"{amend} {channel}: corrected to {shown_legs} ({source}) — {done['reason']}")
                return 0
            round_ = p.set_protective(channel, legs, source=source)
            shown = "OFF" if legs == "OFF" else ", ".join(
                f"{k.upper()} {v['f']:g} {v['type']}{v['slope']}" for k, v in sorted(legs.items()))
            print(f"{round_['id']} {channel}: protective {shown} — this round is RAW for that "
                  f"channel, so its sweeps are de-embedded before any phase decision")
        elif cmd == "listening-verdict":
            pairs, text, route, lv, note = [], None, None, None, None
            i = 0
            while i < len(args):
                a = args[i]
                if a == "--pair" and i + 1 < len(args):
                    parts = args[i + 1].split(":")
                    if len(parts) != 3:
                        raise ProcessError(f"--pair is track:characteristic:ok|bad, got {args[i + 1]!r}")
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
            if got["ok"]:
                print(got["resume"])
                return 0
            print("NOT ready to clear the chat — what the next session would not find:")
            for item in got["missing"]:
                print(f"  - {item}")
            print("\nNothing was written: which evidence closes a step is a decision, not this "
                  "command's. Fix what is named and run it again.")
            return 1
        elif cmd == "capture-skip":
            p.skip_capture(args[0], " ".join(args[1:]))
            print(f"{args[0]} skipped: {' '.join(args[1:])}")
        elif cmd == "capture-close":
            outstanding = p.capture_outstanding()
            round_ = p.close_capture(" ".join(args) or None)
            print(
                f"{round_['id']} closed: {len(round_['taken'])} taken, "
                f"{len(round_['skipped'])} skipped, {len(outstanding)} outstanding"
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
            bad = p.unevidenced_done_steps()
            for entry in bad:
                print(f"NO EVIDENCE: {entry['id']} {entry.get('name','')}")
            unbacked = [e for e in p.unbacked_done_steps() if e not in bad]
            for entry in unbacked:
                print(
                    f"UNBACKED: {entry['id']} {entry.get('name','')} "
                    f"-- evidence resolves to nothing: {'; '.join(map(str, entry['evidence']))}"
                )
            print(
                f"{len(bad)} done step(s) without evidence, "
                f"{len(unbacked)} whose evidence resolves to nothing"
            )
            return 1 if (bad or unbacked) else 0
        else:
            print(_USAGE, file=sys.stderr)
            return 2
    except (ProcessError, IndexError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # issue #21: a code page must not destroy a result. Run from a subdirectory, so the sibling
    # modules' own directory has to go on the path before `console` can be found at all.
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import console
    console.install()
    sys.exit(_main(sys.argv))
