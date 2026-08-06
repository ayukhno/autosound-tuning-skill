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
        "Record it: `set-target <preset> <curve>` (e.g. `set-target FULL EPY`)."
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
    }


def validate(state):
    """Raise `ProcessError` if `state` isn't a shape a reader can trust. Returns it otherwise."""
    if not isinstance(state, dict):
        raise ProcessError("process state must be a JSON object")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ProcessError(
            f"unsupported schema_version {state.get('schema_version')!r} (expected {SCHEMA_VERSION})"
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
        _require_target(phase, previous, state)
        if previous and previous != phase:
            state["phases"][previous]["status"] = PHASE_DONE
        state["phases"][phase]["status"] = PHASE_CURRENT
        state["active_phase"] = phase
        self._write(state)
        self._append(EV_PHASE_ENTERED, phase=phase, previous=previous, note=note)
        return state

    def add_step(self, step_id, name, source=SOURCE_SKILL, phase=None):
        """Add a plan step. Instantiated from the phase template (`skill`) or situational
        (`project`) — the distinction is what lets the UI show which steps this car needed."""
        state = self.load()
        if self.step(state, step_id):
            raise ProcessError(f"step {step_id!r} already exists; steps are never re-added")
        entry = {
            "id": step_id,
            "name": name,
            "status": STEP_TODO,
            "source": source,
            "attempt": 1,
            "skip": False,
            "phase": str(phase) if phase is not None else state.get("active_phase"),
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

    def record_reviewer(self, vendor, model, phase=None, step=None, outcome=None):
        """Who reviewed, on what model, when — the advisor panel's "last called" (TCC-Concept §4)."""
        state = self.load()
        state["reviewer"] = {
            "vendor": vendor,
            "model": model,
            "at": _now(),
            "phase": str(phase) if phase is not None else state.get("active_phase"),
            "step": step,
            "outcome": outcome,
        }
        self._write(state)
        self._append(EV_CRITIC_CALLED, vendor=vendor, model=model, step=step, outcome=outcome)
        return state["reviewer"]

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
  reviewer <vendor> <model> [step]      record a reviewer call
  target <preset> <curve>               set a preset's active target curve
  check                                 done steps with no evidence, and done steps whose
                                         evidence resolves to nothing on disk
"""


def _main(argv):
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
            p.record_reviewer(args[0], args[1], step=args[2] if len(args) > 2 else None)
            print(f"reviewer recorded: {args[0]} / {args[1]}")
        elif cmd == "target":
            p.set_target(args[0], args[1])
            print(f"target for {args[0]}: {args[1]}")
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
