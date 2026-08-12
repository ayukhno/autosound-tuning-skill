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
EV_CAPTURE_SKIPPED = "capture_skipped"
EV_CAPTURE_CLOSED = "capture_round_closed"
# What the arithmetic said about the curves themselves (SCR-040). A separate event from
# `capture_taken`: one says a measurement came back, the other says it is usable.
EV_CAPTURE_VERIFIED = "capture_verified"
# Who sat down to work, on what model, and when. Written by the front-end when it attaches a
# session -- the journal otherwise starts at whatever the model happened to record first, so
# "when did this session begin, and did it record anything at all" had no answer.
EV_SESSION_STARTED = "session_started"
#: A phase gate found something missing and let the move through anyway. Only ever emitted for a
#: MIGRATED project — see `_gates_are_advisory`. On the record rather than on stderr alone,
#: because "we went into phase 2 without a flaw map" is exactly the kind of thing a later reader
#: needs to know and nobody remembers.
EV_GATE_WAIVED = "gate_waived"
# What the Arbiter ruled, as itself. Their half of the conversation was in no machine file at all:
# the only surviving trace of an answer was a hand-typed evidence string, and a constraint the user
# set was invisible to the next session unless it happened to be re-read out of prose (SCR-030).
EV_USER_DECISION = "user_decision"


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
        f"phase {phase} needs a target curve: nothing has been recorded with `set-target`. "
        "Phase 0 chooses it and every later phase is measured against it, so a curve that exists "
        "only in the conversation is lost on the next session. "
        # The command is `target`, and this line said `set-target` — a refusal that instructs a
        # command which does not exist teaches the reader that the refusal is noise (2026-08-12).
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
        with open(os.path.join(project_dir, "project.json")) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    profile = data.get("project", data)
    return list(((profile.get("acoustics") or {}).get("flaws")) or [])


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
    if _flaw_map_entries(project_dir):
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
        "intake flow in `references/core/project-intake.md §0.5` rather than working around this."
    )


def _gates_are_advisory(project_dir):
    """Do this project's phase gates warn instead of refuse.

    True only for a project the migration brought across from 2.x, and only because it says so
    itself: `migrate.py` stamps `migrated_from` into `project.json`. Inferring it from "has a
    ledger" or "has a long journal" would eventually soften a project nobody migrated, which is
    the one case these gates are for.
    """
    path = os.path.join(project_dir, "project.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    body = data.get("project") if isinstance(data.get("project"), dict) else data
    return bool(body.get("migrated_from"))


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
    "1": ("sample_rate_hz", "delay", "crossover_filters"),
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
        with open(os.path.join(project_dir, "dsp_profile.json")) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return  # no readable profile at all is contract.py's complaint, not this gate's
    blocking = [path for path in module.missing_facts(data) if path.split(".")[-1] in wanted]
    if not blocking:
        return
    raise ProcessError(
        f"phase {phase} needs facts the DSP profile has never recorded: "
        + ", ".join(blocking)
        + ". These are not paperwork: phase 1 turns delays into samples with `sample_rate_hz`, and "
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


def _load_naming():
    """`naming.py` from the same checkout, by path.

    Not `import naming`: that needs `rew_tool/` on `sys.path`, and the consumer front-end loads
    these modules by explicit path precisely to keep names like `state` off the global import path.
    Returns None when it cannot be loaded -- an unreadable grammar must not make evidence
    unrecordable, it just means one of the three shapes cannot be recognised here.
    """
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
        # A capture is `<code>_<version> (sw|rta)`, and the METHOD is what makes it one. The
        # grammar leaves it optional -- it also describes DSP-config version strings -- but here
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
        if title not in round_.get("taken", {}) and title not in round_.get("skipped", {})
    ]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    """The migration, as a line somebody can paste.

    An absolute path, not `rew_tool/state/migrate.py`. That relative form only resolves for
    someone standing inside a checkout of the skill; the people who need this most installed it as
    a plugin and have no such directory anywhere near their project.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return f"python3 {os.path.join(here, 'migrate.py')} {project_dir}"


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
        waived = []
        for gate in (lambda: _require_intake(phase, previous, self.project_dir),
                     lambda: _require_target(phase, previous, state),
                     lambda: _require_flaw_map(phase, previous, self.project_dir),
                     lambda: _require_profile_facts(phase, previous, self.project_dir)):
            try:
                gate()
            except ProcessError as refusal:
                # A project that came from 2.x is let through, loudly. These gates were written
                # after it was already being tuned, and every one of them asks for a file or a
                # fact the older line never collected — so on a migrated project they do not
                # protect a beginner from a fabricated tune, they stop somebody months in from
                # continuing work that is real (user, 2026-08-12: "пускати вперед, але
                # попереджати чого бракує").
                #
                # NOT softened for a project started under 3.0. The gates exist because a cheap
                # model once closed phases −1 to 3 and reported a finished tune with
                # `dsp_profile.json` alone on disk; turning them into advice everywhere would
                # hand that back.
                if not _gates_are_advisory(self.project_dir):
                    raise
                waived.append(str(refusal))
        if previous and previous != phase:
            state["phases"][previous]["status"] = PHASE_DONE
        state["phases"][phase]["status"] = PHASE_CURRENT
        state["active_phase"] = phase
        self._write(state)
        self._append(EV_PHASE_ENTERED, phase=phase, previous=previous, note=note)
        for refusal in waived:
            print(f"⚠️  phase {phase}: {refusal}", file=sys.stderr)
            self._append(EV_GATE_WAIVED, phase=phase, reason=refusal)
        return state

    def add_step(self, step_id, name, source=SOURCE_SKILL, phase=None):
        """Add a plan step. Instantiated from the phase template (`skill`) or situational
        (`project`) — the distinction is what lets the UI show which steps this car needed."""
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
        }
        state["plan"].append(entry)
        self._write(state)
        self._append(EV_STEP_ADDED, step=step_id, name=name, source=source)
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
        """Supersede a step. It stays in the plan, dimmed — never removed (SCR-004)."""
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
    def start_capture(self, version, expected=(), phase=None, note=None, step=None):
        """Open a capture round: what was asked for, at which ledger version, in which phase.

        A ROUND, not a version. The task was keyed by the ledger HEAD, which is right for naming
        the measurements (`_N` is the config they were taken under) and wrong for identifying the
        pass: two rounds at the same config are then the same thing, and what the Arbiter asks
        about is "this session's task". Opening a second round while one is open closes the first
        -- a round nobody closed is a round that ended when the next one began.
        """
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
            expected=expected,
            step=step,
            note=note,
        )
        return round_

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
        round_["skipped"][title] = {"at": _now(), "reason": reason}
        self._write(state)
        self._append(EV_CAPTURE_SKIPPED, capture=round_["id"], title=title, reason=reason)
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

    def check_captures(self, titles=None, verifier=None):
        """Run the skill's own verdict over the open round and record it (SCR-040).

        The arithmetic lives in `verify.py` and is called here rather than reimplemented by a
        front-end: two implementations of "is this curve usable" would drift, and the one that
        drifts is the one nobody runs standalone.

        Each verdict pins REW's `uuid`. The title is not identity -- re-take `sw_1 (sw)` and the
        name is unchanged while the data is not, so a verdict keyed by title would outlive the
        graph it judged. A measurement REW no longer holds records no uuid and reads as not ok.
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
                "uuid": (verdict.get("stats") or {}).get("uuid"),
                "at": _now(),
                "issues": list(verdict.get("issues") or []),
            }
        self._write(state)
        self._append(
            EV_CAPTURE_VERIFIED,
            capture=round_["id"],
            step=round_.get("step"),
            ok=sorted(v["name"] for v in verdicts if v.get("valid")),
            bad=sorted(v["name"] for v in verdicts if not v.get("valid")),
        )
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
            if not entry or not (entry.get("verified") or {}).get("ok"):
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

    def _append(self, event_type, **payload):
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
  add-step <id> <name> [--project]      add a plan step (--project = situational insert)
  start <id>                            begin/re-begin a step (a re-begin is attempt N+1)
  done <id> <evidence> [evidence ...]    mark done; evidence is REQUIRED and must RESOLVE
                                         (a capture name `c_1 (rta)`, a ledger `v_003` that
                                          exists, or a project file that exists)
  skip <id> [superseded-by]             supersede a step (kept visible, never deleted)
  block <id> <reason>                   mark blocked
  reviewer <vendor> <model> [step] [--review PATH] [--mode clipboard]
                                        record a reviewer call and WHERE its text is
  target <preset> <curve>               set a preset's active target curve
  session-start <harness> <model> [resumed]   a working session began (written by the front-end)
  decision <question> <answer> [step] [--invalidates X]   what the Arbiter ruled, as itself
  capture-start <version> [title ...] [--step ID]   open a capture round; titles = what was
                                         asked for, --step binds it to the plan step it satisfies
  capture-check [title ...]             run the verdict over the round and record it (SCR-040)
  capture-taken <title>                 a measurement came back (unplanned ones are flagged)
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
        "name": "Fixture", "vendor": "Fixture", "sample_rate_hz": 96000,
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
    refuses("evidence that resolves to nothing",
            lambda: proc.finish_step("s1", ["I looked at the graphs and they seemed fine"]))
    with open(os.path.join(root, "autosound_context.md"), "w") as f:
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
    with open(os.path.join(root, "dsp_profile.json"), "w") as f:
        json.dump(profile, f)
    refuses("entering phase 1 with no sample rate on record", lambda: proc.enter_phase("1"))
    profile["dsp_profile"]["sample_rate_hz"] = 48000
    with open(os.path.join(root, "dsp_profile.json"), "w") as f:
        json.dump(profile, f)
    proc.enter_phase("1")
    # ...and phase 2 asks for what phase 2 needs, not for everything at once: this profile
    # declares no `eq` field, so there is nothing for it to owe.
    proc.enter_phase("2")
    assert proc.load()["active_phase"] == "2"

    # A MIGRATED project is let through the same gates with a warning, and the waiver goes on the
    # record. Every one of these gates asks for something the 2.x line never collected, so on a
    # project months into a tune they stop real work rather than prevent a fabricated one (user,
    # 2026-08-12). A project nobody migrated is NOT softened — that is the whole distinction.
    import tempfile as _tempfile

    legacy = _tempfile.mkdtemp(prefix="autosound_process_2x_")
    legacy_proc = Process(os.path.join(legacy, "process"))
    refuses("a fresh project is still refused", lambda: legacy_proc.enter_phase("1"))
    with open(os.path.join(legacy, "project.json"), "w", encoding="utf-8") as handle:
        json.dump({"schema_version": 3, "project_rev": 1, "migrated_from": "2.x"}, handle)
    legacy_proc.enter_phase("1")  # same missing files, now a warning
    assert legacy_proc.load()["active_phase"] == "1", legacy_proc.load()
    waived = [json.loads(line) for line in open(legacy_proc.journal_path, encoding="utf-8")
              if json.loads(line)["type"] == EV_GATE_WAIVED]
    assert waived, "a waived gate that leaves no trace is a gate nobody can audit later"
    assert "intake has not produced" in waived[0]["reason"], waived[0]

    print(
        "selftest OK — evidence refused when empty and when it resolves to nothing (SCR-035), "
        "phase -1 refused to end on a folder intake never touched, "
        "phase 0 refused to exit without a target (SCR-036) and without a flaw map (SCR-044) "
        "and opened once the map was recorded; "
        "phase 1 refused a profile with no `sample_rate_hz` (SCR-045) and phase 2 asked only for "
        "what a profile declaring no EQ actually owes; a migrated project passed the same gates "
        "with a journalled warning while a fresh one was still refused. "
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
            positional = [a for a in args if a != "--project"]
            p.add_step(positional[0], positional[1], source=source)
            print(f"added {positional[0]}")
        elif cmd == "start":
            entry = p.start_attempt(args[0])
            print(f"{args[0]} in progress (attempt {entry['attempt']})")
        elif cmd == "done":
            entry = p.finish_step(args[0], args[1:])
            print(f"{args[0]} done, evidence: {', '.join(entry['evidence'])}")
        elif cmd == "skip":
            p.skip_step(args[0], superseded_by=args[1] if len(args) > 1 else None)
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
        elif cmd == "capture-start":
            step = None
            rest = list(args)
            if "--step" in rest:
                i = rest.index("--step")
                step = rest[i + 1] if len(rest) > i + 1 else None
                rest = rest[:i] + rest[i + 2:]
            round_ = p.start_capture(rest[0], expected=rest[1:], step=step)
            print(
                f"{round_['id']} open at {round_['version']}, "
                f"{len(round_['expected'])} capture(s) expected"
            )
        elif cmd == "capture-check":
            round_ = p.check_captures(args or None)
            for title in round_.get("expected", []):
                verdict = ((round_.get("taken") or {}).get(title) or {}).get("verified") or {}
                if verdict.get("ok"):
                    print(f"OK      {title}")
                elif title in (round_.get("skipped") or {}):
                    print(f"SKIP    {title}")
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
    sys.exit(_main(sys.argv))
