"""Whole-project machine-contract checker (SKILL-SYNC-PLAN.md §2.3).

The one command both repos key off: "is this project's machine data consistent, and at what
schema version". Walks every machine file this skill's tooling owns — `project.json`,
`dsp_profile.json`, `process/process-state.json` + `journal.jsonl`, each preset's hard-params
ledger — and reports, per file: exists / schema_version / valid / issues. Then runs the CROSS-file
checks no single module can do alone: glossary codes vs ledger channels vs (best-effort) REW
titles, process-state done-steps missing evidence, ledger tiers vs the DSP profile's declared
groups.

Human table for a skill/terminal session (`check`); `--json` for a consumer UI's diagnostics panel
(TCC-TZ.md §8: "what did TCC find on disk, what's missing" belongs in one machine-checkable place,
not scattered chat bubbles). Read-only — nothing here writes to any file.

`state/`'s modules (`state.py`, `process.py`) live in a sys.path-synthetic sub-package by this
repo's own convention (see `rew_tool.py`'s selftest for the same lazy-import technique); the REW
check is best-effort — REW not running is REPORTED, never a crash.

This file's own directory is ensured on `sys.path` before importing its siblings (`dsp_profile`,
`naming`, `project`) below — a no-op when run as `python3 rew_tool/contract.py` (Python already
puts the script's directory there), but load-bearing when a consumer imports this file by explicit
path instead (e.g. a host app's isolated-module loader) rather than running it as a script.

stdlib only, py3.9+.
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import dsp_profile
import naming
import project

# `state/state.py` schema_version this contract expects — kept as a literal constant table
# (`CONTRACT`) rather than re-deriving it from the module on every run, so a version bump is a
# one-line diff both repos read (SKILL-SYNC-PLAN.md §2.3's "CONTRACT table" ask).
# One format number for the whole project (3.0): every versioned machine file carries the same
# `schema_version`, so "which format is this project in?" is one comparison rather than a matrix.
FORMAT_VERSION = 3
#: Row fields the ledger owned in 2.x and `project.json` owns now — the same list as
#: `state/state.py::MOVED_TO_PROJECT_JSON`, spelled out here for the same reason `CONTRACT` is:
#: this module deliberately does not import the state layer, so that a checker still runs on a
#: project whose ledger code is the thing that is broken. `helix_ch` is the one that matters —
#: the only identity field the RELEASED 2.x line ever wrote.
_MOVED_OUT_OF_LEDGER = ("helix_ch", "slot", "descr", "role", "order", "hidden", "tag_value")
#: What phase −1 cannot be left without. Not every row of CONTRACT: the registry is only for a
#: multi-slot DSP, and the journal is written by the first event rather than by intake.
_GATE_REQUIRED = (
    "project.json",
    "dsp_profile.json",
    "glossary.json (or project.json.glossary)",
)
#: NOT in the list, deliberately: `process/process-state.json` is written BY `enter_phase`, so
#: requiring it of a phase transition is a gate demanding its own output. The phase −1 doc lists
#: the intake ARTEFACTS — the project's facts, the DSP's capabilities, the names, the first
#: snapshot — and the process file is the bookkeeping that records the transition itself.

CONTRACT = (
    # (relative path, label, owner, expected schema_version -- None where the file carries no
    # version because it has no envelope to put one in: the glossary lives inside project.json,
    # the journal is append-only JSONL, the registry is a two-key pointer)
    ("project.json", "project facts", "skill", FORMAT_VERSION),
    ("dsp_profile.json", "DSP capability profile", "skill", FORMAT_VERSION),
    ("glossary.json (or project.json.glossary)", "naming glossary", "skill", None),
    ("process/process-state.json", "process state", "skill", FORMAT_VERSION),
    ("process/journal.jsonl", "process journal (append-only)", "skill", None),
    ("state/<preset>/HEAD ledger", "hard-params ledger", "skill", FORMAT_VERSION),
    ("state/registry.json", "multi-slot active-slot pointer", "skill", None),
)


def _state_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")


def _load_vendored(name):
    """Import a `state/` module (`state` or `process`) via the same lazy sys.path technique
    `rew_tool.py`'s selftest and `project.py`'s CLI already use."""
    d = _state_dir()
    if d not in sys.path:
        sys.path.insert(0, d)
    return __import__(name)


def _ledger_version_number(snap):
    """`"v_002"` -> `"2"` -- the plain version token `naming.expected_series` expects, matching
    the measurement-name grammar's `_N` (config vN <-> measurements `_N`, `naming-and-structure.md
    §5`). `None` if the snapshot has no parseable version (e.g. never seeded)."""
    m = re.match(r"^v_0*(\d+)$", str(snap.get("version") or ""))
    return m.group(1) if m else None


# ── per-file checks ────────────────────────────────────────────────────────────
def _entry(file, exists, schema_version=None, valid=None, issues=None, **extra):
    e = {"file": file, "exists": exists, "schema_version": schema_version, "valid": valid,
         "issues": issues or []}
    e.update(extra)
    return e


def check_project_json(project_dir):
    path = os.path.join(project_dir, "project.json")
    if not os.path.isfile(path):
        return _entry("project.json", False, issues=["missing -- run intake"]), None
    try:
        data = project.Project(project_dir).load()
    except project.ProjectError as exc:
        # Unreadable is a REPORT here, not a crash: diagnostics exists to say what is wrong with a
        # project, and a checker that dies on the worst case is a checker that is absent for it.
        return _entry("project.json", True, None, False, [str(exc)]), None
    try:
        project.validate(data)
        entry = _entry("project.json", True, data.get("schema_version"), True)
    except project.ProjectError as exc:
        entry = _entry("project.json", True, data.get("schema_version"), False, [str(exc)])
    oq = project.open_questions(data)
    if oq:
        entry["open_questions"] = oq
    return entry, data


def check_dsp_profile(project_dir):
    path = os.path.join(project_dir, "dsp_profile.json")
    if not os.path.isfile(path):
        return _entry("dsp_profile.json", False, issues=["missing -- run intake/onboarding"]), None
    try:
        data = dsp_profile.load_profile(path)
        dsp_profile.validate_profile(data)
    except (OSError, ValueError) as exc:
        return _entry("dsp_profile.json", True, None, False, [str(exc)]), None
    # The version lives at the wrapper level, beside `dsp_profile` -- it describes the FILE, and a
    # profile written before 3.0 simply has none, which reads as "—" rather than as an error.
    schema = data.get("schema_version") if isinstance(data, dict) else None
    entry = _entry("dsp_profile.json", True, schema, True)
    oq = dsp_profile.open_questions(data)
    if oq:
        entry["open_questions"] = oq
    return entry, data


def check_glossary(project_dir):
    glossary = naming.Glossary.for_project(project_dir)
    present = bool(glossary.channels or glossary.pairs or glossary.combos
                   or glossary.joints or glossary.sides)
    # TWO SOURCES, ONE WINNER, NO WORD ABOUT IT: `naming.Glossary.for_project` returns the
    # standalone `glossary.json` the moment that file exists and never opens `project.json`.
    # So any stray write of a standalone file SHADOWS the project's own glossary silently --
    # observed 2026-08-21, when a consumer's test fixture (7 channels) landed on a live project
    # (8 channels) and the centre channel simply ceased to exist for every name check and every
    # derived checklist, while this checker reported present/valid. The precedence itself is
    # deliberate (SCR-011) and is NOT changed here: a documented rule other projects lean on is
    # worse to flip quietly than to leave. What was missing is the alarm.
    shadow = None
    standalone = os.path.join(project_dir, "glossary.json")
    if os.path.isfile(standalone) and os.path.isfile(os.path.join(project_dir, "project.json")):
        try:
            with open(os.path.join(project_dir, "project.json"), encoding="utf-8") as f:
                inline = (json.load(f) or {}).get("glossary") or {}
        except (OSError, ValueError):
            inline = {}
        hidden = naming.Glossary(inline)
        if (hidden.channels or hidden.pairs or hidden.combos or hidden.joints or hidden.sides) \
                and hidden.channel_codes() != glossary.channel_codes():
            lost = [c for c in hidden.channel_codes() if c not in glossary.channel_codes()]
            shadow = ("glossary.json SHADOWS project.json's `glossary` key and they disagree"
                      + (" -- channels only in project.json: " + ", ".join(lost) if lost else "")
                      + ". The standalone file wins (naming.Glossary.for_project); delete it, or"
                      " reconcile the two, before trusting any name check.")
    # An EMPTY standalone file over a real glossary is the worst form of this, not an absent
    # one: everything vanishes. So the shadow decides `valid`, and it also replaces the generic
    # "no glossary yet" line -- that line would send the reader off to write a glossary they
    # already have.
    if shadow:
        return _entry("glossary.json (or project.json.glossary)", True, None, False, [shadow]), \
            glossary
    issues = [] if present else ["no glossary yet -- naming/measurement checks are inert"]
    entry = _entry("glossary.json (or project.json.glossary)", present, None,
                   present or None, issues)
    return entry, glossary


def check_process(project_dir):
    process_mod = _load_vendored("process")
    process_dir = os.path.join(project_dir, "process")
    proc = process_mod.Process(process_dir)
    state = proc.load()  # never raises -- empty skeleton if the project has no process yet
    exists = os.path.isfile(proc.state_path)
    try:
        process_mod.validate(state)
        entry = _entry("process/process-state.json", exists, state.get("schema_version"), True)
    except process_mod.ProcessError as exc:
        entry = _entry("process/process-state.json", exists, state.get("schema_version"), False,
                        [str(exc)])
    unevidenced = proc.unevidenced_done_steps(state)
    if unevidenced:
        entry["issues"].append(
            f"{len(unevidenced)} done step(s) with no evidence: "
            + ", ".join(s["id"] for s in unevidenced)
        )
    journal_exists = os.path.isfile(proc.journal_path)
    journal_entry = _entry("process/journal.jsonl", journal_exists, None, journal_exists or None,
                            events=len(proc.events()) if journal_exists else 0)
    return entry, journal_entry, state


def check_ledgers(project_dir):
    """One entry per preset directory under `state/` (D1's canonical layout).

    Dot-directories are skipped: a consumer app's own scratch (`.tcc/`) or a VCS directory sitting
    beside the presets is not a preset, and reporting it as one ("no snapshot history yet") sends
    the reader looking for a ledger that was never supposed to exist. Found live against the
    dogfood project, which has a `state/.tcc/`.
    """
    state_mod = _load_vendored("state")
    root = os.path.join(project_dir, "state")
    entries, snapshots = [], {}
    if not os.path.isdir(root):
        return entries, snapshots
    for preset in sorted(
        n for n in os.listdir(root)
        if not n.startswith(".") and os.path.isdir(os.path.join(root, n))
    ):
        h = state_mod.PresetHistory(root, preset)
        head = h.head()
        if head is None:
            entries.append(_entry(f"state/{preset}/", False,
                                   issues=["no snapshot history yet"]))
            snapshots[preset] = None
            continue
        snap = h.load(head)
        try:
            state_mod.validate(snap)
            entry = _entry(f"state/{preset}/{head}.json", True, snap.get("schema_version"), True)
        except ValueError as exc:
            entry = _entry(f"state/{preset}/{head}.json", True, snap.get("schema_version"), False,
                            [str(exc)])
        entries.append(entry)
        snapshots[preset] = snap
    return entries, snapshots


# ── cross-file checks ──────────────────────────────────────────────────────────
def cross_check_glossary_vs_ledgers(glossary, snapshots):
    """Every active channel has a ledger row, and every ledger row is a channel we know.

    A ledger row's key is the channel's id (SCR-039), so after a rename it is the name the channel
    USED to have while the glossary carries the current one. Both sides are resolved through
    `resolve_code` before comparing — without it, a rename would report the same channel as both
    missing from the ledger and foreign to the glossary, which is one correct label looking like
    two structural faults.
    """
    issues = []
    resolve = glossary.resolve_code
    active = {resolve(c) for c in glossary.channel_codes(active_only=True)}
    known = {resolve(c) for c in glossary.channel_codes()}
    for preset, snap in snapshots.items():
        if not snap:
            continue
        ledger_codes = {resolve(c) for c in snap.get("channels", {})}
        missing = sorted(active - ledger_codes)
        foreign = sorted(ledger_codes - known) if known else []
        if missing:
            issues.append(f"{preset}: glossary has active channel(s) with no ledger row: {missing}")
        if foreign:
            issues.append(f"{preset}: ledger channel(s) not in the glossary: {foreign}")
    return issues


def cross_check_tiers_vs_profile(profile_data, snapshots, project_data=None):
    """Every tier named by a ledger or by a `channels[]` entry must be one the profile declares.

    Both halves matter for the same reason (SCR-042): a tier name that matches nothing does not
    fail, it disappears — the rows keyed under it are simply never rendered. The `channels[]` half
    is the newer one and the likelier to rot, since a spare slot's `tier` is the ONLY thing tying
    it to a tier and there is no ledger row to contradict a typo.
    """
    if not profile_data:
        return []
    state_mod = _load_vendored("state")
    declared = set(dsp_profile.tier_keys(profile_data))
    issues = []
    for preset, snap in snapshots.items():
        if not snap:
            continue
        present = set(state_mod.tier_names(snap))
        extra = sorted(present - declared)
        if extra:
            issues.append(f"{preset}: ledger tier(s) not declared in dsp_profile.json: {extra}")
    for ch in (project_data or {}).get("channels", []) or []:
        if not isinstance(ch, dict):
            continue
        tier = ch.get("tier")
        if tier and tier not in declared:
            issues.append(
                f"project.json: channel {ch.get('code')!r} names tier {tier!r}, which "
                f"dsp_profile.json does not declare (declared: {sorted(declared)}) — the row would "
                "render nowhere")
    return issues


def cross_check_rew(process_state, glossary, snapshots):
    """Best-effort: REW not running/reachable is reported, not a crash (`contract.py` runs as a
    static project audit; requiring a live REW connection would make it useless offline)."""
    try:
        import rew_api

        titles = [m.get("title", "") for m in rew_api.get_measurements().values()]
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any REW-unreachable reason
        return {"reachable": False, "note": f"REW not reachable ({exc}) -- skipped"}
    phase = (process_state or {}).get("active_phase")
    if not phase:
        return {"reachable": True, "note": "no active phase in process-state -- skipped"}
    version = next((_ledger_version_number(s) for s in snapshots.values() if s), None)
    if not version:
        return {"reachable": True, "note": "no ledger version to check REW titles against"}
    expected = naming.expected_series(phase, glossary, version)
    verdict = naming.validate_series(titles, expected, glossary)
    return {"reachable": True, "phase": phase, "version": version, **verdict}


# ── the whole report ────────────────────────────────────────────────────────────
def check_project(project_dir, skip_rew=False):
    files = []
    project_entry, project_data = check_project_json(project_dir)
    files.append(project_entry)
    profile_entry, profile_data = check_dsp_profile(project_dir)
    files.append(profile_entry)
    glossary_entry, glossary = check_glossary(project_dir)
    files.append(glossary_entry)
    process_entry, journal_entry, process_state = check_process(project_dir)
    files.append(process_entry)
    files.append(journal_entry)
    ledger_entries, snapshots = check_ledgers(project_dir)
    files.extend(ledger_entries)

    cross = {
        "glossary_vs_ledgers": cross_check_glossary_vs_ledgers(glossary, snapshots),
        "tiers_vs_profile": cross_check_tiers_vs_profile(profile_data, snapshots, project_data),
        "rew": ({"reachable": False, "note": "skipped (--no-rew)"} if skip_rew
                else cross_check_rew(process_state, glossary, snapshots)),
    }
    ok = all(f["valid"] is not False for f in files) and not cross["glossary_vs_ledgers"] and \
        not cross["tiers_vs_profile"]
    # `ok` and `complete` answer two different questions, and conflating them made the phase −1
    # gate endorse its own bypass: an EMPTY project has nothing broken, so `ok` was True, and the
    # gate names this check as its verifier (found 2026-08-12 — `check_project(<empty dir>)`
    # returned `ok=True` with every file absent).
    #
    # `ok`       — nothing here is WRONG. A fresh folder qualifies, and should: intake has not run.
    # `complete` — everything the method needs before phase 0 EXISTS and is valid. That is the
    #              gate's question, and only that one.
    missing = [f["file"] for f in files if not f["exists"] and f["file"] in _GATE_REQUIRED]
    # The ledger has no fixed row name — `check_ledgers` reports one row per preset directory, and
    # a project with no `state/` at all reports none. Absence of the row IS the missing ledger,
    # which a name-based check cannot see.
    if not any(f["file"].startswith("state/") and f["exists"] for f in files):
        missing.append("state/<preset>/ (first ledger snapshot)")
    complete = ok and not missing
    prose = looks_like_prose(project_dir, files)
    if prose:
        # The per-file hint is "run intake", which is right for an empty folder and wrong here —
        # and a table that contradicts the banner above it teaches the reader to trust neither.
        for entry in files:
            entry["issues"] = [
                "not written yet — it is in the prose above" if "run intake" in issue else issue
                for issue in (entry.get("issues") or [])
            ]
    return {"project_dir": project_dir, "ok": ok, "complete": complete, "missing": missing,
            "legacy": looks_like_2x(project_dir, files), "prose": prose,
            "files": files, "cross_checks": cross}


#: The files a pre-ledger project keeps its state in. Before `state/state.py` existed (v2.1.0) —
#: and in projects that simply never adopted it — the tune lived in prose: the context file, the
#: audit trail, the changelog with its ▶️ CONTINUE block. SCR-004 and SCR-008 were written to
#: replace exactly these, which is why 3.0 has no reader for them.
_PROSE_STATE_FILES = ("autosound_context.md", "audit-trail.md", "tuning-changelog.md",
                      "tuning-changelog.txt")


def looks_like_prose(project_dir, files):
    """A project whose state is prose, with no machine files at all.

    Indistinguishable from an empty folder to a file-existence check, and it needs the OPPOSITE
    advice: not "run intake", which would re-ask what a competition-winning tune already answered,
    and not "migrate", because there is no ledger to migrate (found on a real project, 2026-08-13).

    Deliberately narrow: prose present AND nothing machine-readable. A 3.0 project that also keeps
    an `autosound_context.md` around is not this.
    """
    if any(entry.get("exists") for entry in files):
        return False
    found = []
    for name in _PROSE_STATE_FILES:
        for candidate in (os.path.join(project_dir, name),
                          os.path.join(project_dir, "rew_analitic", name)):
            if os.path.isfile(candidate):
                found.append(os.path.relpath(candidate, project_dir))
                break
    return found


def looks_like_2x(project_dir, files):
    """Is this a project the 2.x line wrote, rather than one intake never touched?

    The two look identical to a file-existence check and need OPPOSITE advice, which is how a user
    months into a tune came to be told they had never started one and should run intake — a wrong
    instruction, and a destructive one, since intake re-asks questions they already answered
    (2026-08-12).

    Three tells, any one of which settles it. A `schema_version` below the current one on any file
    that carries one; a ledger row holding an identity field the ledger no longer owns (`helix_ch`
    above all — the only one the released 2.x line wrote); or ledgers present while `project.json`,
    a file 2.x had no concept of, is absent.
    """
    for entry in files:
        version = entry.get("schema_version")
        if isinstance(version, int) and not isinstance(version, bool) and version < FORMAT_VERSION:
            return True
    has_ledger = any(f["file"].startswith("state/") and f["exists"] for f in files)
    has_project = any(f["file"] == "project.json" and f["exists"] for f in files)
    if has_ledger and not has_project:
        return True
    for path in _ledger_snapshots(project_dir):
        try:
            with open(path, encoding="utf-8") as handle:
                snap = json.load(handle)
        except (OSError, ValueError):
            continue
        for key, rows in snap.items():
            if not isinstance(rows, dict):
                continue
            for row in rows.values():
                if isinstance(row, dict) and any(f in row for f in _MOVED_OUT_OF_LEDGER):
                    return True
    return False


def _ledger_snapshots(project_dir):
    """Every `v_NNN.json` under `state/`. Its own walker rather than `migrate.snapshot_paths`:
    importing the migration from the checker would make the checker depend on the thing it is
    supposed to tell you to run."""
    root = os.path.join(project_dir, "state")
    if not os.path.isdir(root):
        return []
    out = []
    for preset in sorted(n for n in os.listdir(root) if not n.startswith(".")):
        directory = os.path.join(root, preset)
        if not os.path.isdir(directory):
            continue
        out.extend(os.path.join(directory, fn) for fn in sorted(os.listdir(directory))
                   if fn.endswith(".json") and fn.startswith("v_"))
    return out


# ── rendering ───────────────────────────────────────────────────────────────────
def _migration_command(project_dir):
    here = os.path.dirname(os.path.abspath(__file__))
    return (f"python3 {os.path.join(here, 'state', 'migrate.py')} {project_dir} "
            f"--into <new-project-dir>")


def render_report(report):
    lines = [f"# Project contract check — {report['project_dir']}", ""]
    if report.get("prose"):
        # Before the file table and before any mention of intake. A tune already exists here; the
        # only thing missing is a machine-readable form of it.
        lines.append(
            "**This project's state is in prose** — "
            + ", ".join(f"`{name}`" for name in report["prose"])
            + " — and 3.0 reads machine files. There is nothing to migrate (no ledger was ever "
              "written) and nothing to re-ask: everything below already exists, in sentences."
        )
        lines.append("")
        lines.append("Bring it across by READING those files rather than interviewing again: the "
                     "channel map becomes `project.json.channels[]`, the DSP settings become the "
                     "first ledger snapshot, the naming convention becomes the glossary, and the "
                     "cabin anomalies become `acoustics.flaws[]`. Confirm each before it is "
                     "written. The prose files are not modified.")
        lines.append("")
    elif report.get("legacy"):
        # BEFORE the file table, and before any talk of intake. This is the one thing a reader in
        # this situation has to act on, and everything below it is a consequence of it.
        lines.append(
            "**This is a 2.x project.** 3.0 reads a different format, so the rows below will "
            "look broken or missing. Nothing is lost and nothing here will be changed — import "
            "this car's current state into a NEW 3.0 project, and keep this one for its history:"
        )
        lines.append("")
        lines.append(f"    {_migration_command(report['project_dir'])}")
        lines.append("")
        lines.append("Do NOT run intake here, and do not convert this folder — the import leaves "
                     "it untouched and still openable in 2.x.")
        lines.append("")
    elif report.get("missing"):
        lines.append(
            "**Not ready for phase 0** — intake has not produced: "
            + ", ".join(report["missing"])
            + ". (`--gate` exits non-zero on this; plain `check` reports only whether what EXISTS "
              "is wrong.)"
        )
        lines.append("")
    lines.append("| File | Exists | Schema | Valid | Issues |")
    lines.append("|---|---|---|---|---|")
    for f in report["files"]:
        exists = "✅" if f["exists"] else "—"
        valid = {"True": "✅", "False": "❌", "None": "—"}[str(f["valid"])]
        sv = f["schema_version"] if f["schema_version"] is not None else "—"
        issues = "; ".join(f["issues"]) or "—"
        lines.append(f"| {f['file']} | {exists} | {sv} | {valid} | {issues} |")
        if f.get("open_questions"):
            lines.append(f"|  |  |  |  | 🟡 open: {', '.join(f['open_questions'])} |")
    lines.append("")
    cross = report["cross_checks"]
    lines.append("**Cross-file checks:**")
    for note in cross["glossary_vs_ledgers"] + cross["tiers_vs_profile"]:
        lines.append(f"- ⚠️ {note}")
    rew = cross["rew"]
    if rew.get("reachable"):
        if "note" in rew:
            lines.append(f"- REW: {rew['note']}")
        else:
            lines.append(f"- REW (phase {rew['phase']}, v{rew['version']}): "
                         f"{len(rew['found'])}/{len(rew['expected'])} captured"
                         + ("" if rew["complete"] else f" — MISSING {rew['missing']}"))
    else:
        lines.append(f"- REW: {rew.get('note', 'not reachable')}")
    lines.append("")
    lines.append("**OK — nothing to fix.**" if report["ok"] else "**Issues found — see above.**")
    return "\n".join(lines)


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: contract.py check <project-dir> [--json] [--no-rew]
       contract.py table                       print the CONTRACT (file -> owner -> schema version)
       contract.py selftest
"""


def _main(argv):
    if len(argv) < 2:
        print(_USAGE, file=sys.stderr)
        return 2
    if argv[1] == "selftest":
        return _selftest()
    if argv[1] == "table":
        for path, label, owner, sv in CONTRACT:
            print(f"{path:35s} {label:32s} owner={owner:6s} schema_version={sv}")
        return 0
    if argv[1] != "check" or len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    project_dir = argv[2]
    as_json = "--json" in argv
    skip_rew = "--no-rew" in argv
    # `--gate` is the phase −1 question: is everything the method needs actually here. Without it
    # the caller gets "nothing is wrong", which an empty folder satisfies.
    gate = "--gate" in argv
    report = check_project(project_dir, skip_rew=skip_rew)
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_report(report))
    if gate:
        return 0 if report["complete"] else 1
    return 0 if report["ok"] else 1


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest():
    import tempfile

    root = tempfile.mkdtemp(prefix="autosound_contract_")

    # an empty project: every file reports missing, nothing crashes. Missing is not the same as
    # INVALID (a brand-new project hasn't been intake'd yet, which is normal, not broken) -- so
    # `ok` stays True; only a file that exists AND fails validation flips it.
    empty = check_project(root, skip_rew=True)
    assert empty["ok"] is True, empty
    assert any(f["file"] == "project.json" and not f["exists"] for f in empty["files"]), empty

    # seed a consistent project: project.json + glossary, dsp_profile.json, ledger, process.
    proj = project.Project(root)
    data = proj.load()
    data["glossary"] = {"channels": [{"code": "w-L", "active": True},
                                     {"code": "c", "active": False}]}
    proj.save(data)

    helix = {"dsp_profile": {"name": "Helix DSP Ultra S", "vendor": "Audiotec-Fischer", "groups": [
        {"id": "virtual_channels", "label": "Virtual channels", "fields": ["gain_db"]},
        {"id": "physical_outputs", "label": "Output channels", "fields": ["hp", "lp", "gain_db"]},
    ]}}
    dsp_profile.save_profile(os.path.join(root, "dsp_profile.json"), helix)

    state_mod = _load_vendored("state")
    h = state_mod.PresetHistory(os.path.join(root, "state"), "SQ_Jazzi")
    snap = state_mod._sample_state()  # has "channels": sub/w-L/tw-R + a "virtual_channels" tier
    h.snapshot(snap, note="seed")

    process_mod = _load_vendored("process")
    proc = process_mod.Process(os.path.join(root, "process"))
    proc.enter_phase("0")

    # A consumer app's scratch dir sitting next to the presets is not a preset (found live: TCC's
    # `state/.tcc/` was reported as a ledger with "no snapshot history yet").
    os.makedirs(os.path.join(root, "state", ".tcc"), exist_ok=True)

    report = check_project(root, skip_rew=True)
    assert not any(f["file"].startswith("state/.tcc") for f in report["files"]), report["files"]
    project_f = next(f for f in report["files"] if f["file"] == "project.json")
    assert project_f["exists"] and project_f["valid"] is True, project_f
    ledger_f = next(f for f in report["files"] if f["file"].startswith("state/SQ_Jazzi/"))
    assert ledger_f["valid"] is True and ledger_f["schema_version"] == state_mod.SCHEMA_VERSION, ledger_f

    # cross-check: glossary says "w-L" active but ledger also has "sub"/"tw-R" -- those are
    # foreign to this (deliberately tiny) glossary fixture, and "c" (inactive) is correctly NOT
    # flagged as missing.
    assert any("not in the glossary" in n for n in report["cross_checks"]["glossary_vs_ledgers"]), report
    assert not any("active channel(s) with no ledger row" in n
                   for n in report["cross_checks"]["glossary_vs_ledgers"]), report

    # cross-check: the ledger's virtual_channels tier IS declared in this profile -- no complaint.
    assert report["cross_checks"]["tiers_vs_profile"] == [], report["cross_checks"]

    # SCR-042: a spare slot's `tier` is the only thing tying it to a tier -- no ledger row exists
    # to contradict a typo -- so a tier the profile does not declare has to be caught here.
    proj.set_channel("off-out-L", slot="L", hidden=True, role="unused", tier="channels")
    assert check_project(root, skip_rew=True)["cross_checks"]["tiers_vs_profile"] == [], \
        "a spare slot on a declared tier must not be flagged"
    proj.set_channel("off-out-L", tier="outputs")  # plausible, declared nowhere
    tier_issues = check_project(root, skip_rew=True)["cross_checks"]["tiers_vs_profile"]
    assert any("off-out-L" in n and "outputs" in n for n in tier_issues), tier_issues
    proj.set_channel("off-out-L", tier="channels")  # back to consistent for the checks below

    # SCR-039: rename the glossary's `w-L` and the ledger keeps its key (an id, never rewritten).
    # Compared raw, that one correct rename reads as two structural faults at once -- the channel
    # missing from every ledger AND a foreign row in every ledger.
    proj_data = proj.load()
    proj_data["glossary"] = {"channels": [{"code": "wf-L", "active": True,
                                            "previous_names": ["w-L"]}]}
    proj.save(proj_data)
    renamed = check_project(root, skip_rew=True)["cross_checks"]["glossary_vs_ledgers"]
    assert not any("wf-L" in n or "w-L" in n for n in renamed), renamed

    # a profile that does NOT declare virtual_channels flags the ledger's tier as undeclared.
    musway = {"dsp_profile": {"name": "M6V4", "vendor": "Musway", "groups": [
        {"id": "physical_outputs", "label": "Output channels", "fields": ["hp", "lp", "gain_db"]},
    ]}}
    dsp_profile.save_profile(os.path.join(root, "dsp_profile.json"), musway)
    report2 = check_project(root, skip_rew=True)
    assert any("virtual_channels" in n for n in report2["cross_checks"]["tiers_vs_profile"]), report2

    # REW check, explicitly skipped, is reported as such rather than attempted.
    assert report["cross_checks"]["rew"] == {"reachable": False, "note": "skipped (--no-rew)"}, report

    # render_report doesn't crash on either shape and mentions the cross-check findings.
    text = render_report(report2)
    assert "virtual_channels" in text, text

    # -- `ok` and `complete` are different questions (2026-08-12) -------------------------------
    # An empty project has nothing WRONG with it, so `ok` is True and should be. The phase -1 gate
    # names this check as its verifier, and on that reading the gate endorsed its own bypass.
    empty = check_project(tempfile.mkdtemp(prefix="autosound_contract_empty_"), skip_rew=True)
    assert empty["ok"] is True, empty
    assert empty["complete"] is False, empty
    assert "project.json" in empty["missing"], empty["missing"]
    # The ledger has no fixed row name, so its absence is detected by absence of any state/ row.
    assert any("ledger" in name for name in empty["missing"]), empty["missing"]
    # ...and a project the selftest itself seeded owes nothing: `missing` is empty even though
    # `complete` is False here, because this fixture also carries a deliberate glossary/ledger
    # mismatch. Two separate facts, which is the whole point of splitting them.
    assert report["missing"] == [], report["missing"]
    assert report["complete"] is False and report["ok"] is False, report
    assert report["legacy"] is False, "a 3.0 project must not be mistaken for a 2.x one"

    # A 2.x project and an un-intaken one look identical to a file-existence check and need
    # OPPOSITE advice. Telling somebody months into a tune to run intake is not just unhelpful, it
    # re-asks what they already answered (2026-08-12).
    legacy_root = tempfile.mkdtemp(prefix="autosound_contract_2x_")
    legacy_preset = os.path.join(legacy_root, "state", "FULL")
    os.makedirs(legacy_preset)
    with open(os.path.join(legacy_preset, "v_001.json"), "w", encoding="utf-8") as handle:
        json.dump({"preset": "FULL", "version": "v_001", "sample_rate": 96000,
                   "channels": {"w-L": {"helix_ch": "C", "gain_db": -2.0}}}, handle)
    with open(os.path.join(legacy_preset, "HEAD"), "w", encoding="utf-8") as handle:
        handle.write("v_001\n")

    legacy = check_project(legacy_root, skip_rew=True)
    assert legacy["legacy"] is True, legacy
    rendered = render_report(legacy)
    assert "This is a 2.x project" in rendered, rendered
    assert "migrate.py" in rendered and "Do NOT run intake" in rendered, rendered
    assert "intake has not produced" not in rendered, "the wrong advice must not survive"

    # ...and an EMPTY folder is not a 2.x project: it is one nobody has started.
    assert check_project(tempfile.mkdtemp(prefix="autosound_contract_new_"),
                         skip_rew=True)["legacy"] is False

    # A STANDALONE glossary.json shadowing project.json's `glossary` key, dropping a channel:
    # the incident of 2026-08-21 in miniature (a consumer's test fixture landed on a live
    # project and the centre channel vanished from every name check while this checker still
    # said "present"). The shadow must be NAMED, and the lost code named with it.
    gl_path = os.path.join(root, "glossary.json")
    live = project.Project(root).load()["glossary"]["channels"]
    with open(gl_path, "w", encoding="utf-8") as f:
        json.dump({"channels": live[:-1]}, f)   # ...emptied, the worst form: everything vanishes
    shadowed = check_project(root, skip_rew=True)
    gl_entry = next(e for e in shadowed["files"] if e["file"].startswith("glossary.json"))
    assert gl_entry["valid"] is False, gl_entry
    assert any("SHADOWS" in i and live[-1]["code"] in i for i in gl_entry["issues"]), gl_entry
    assert not any("no glossary yet" in i for i in gl_entry["issues"]), \
        "a shadowed project HAS a glossary -- do not send the reader off to write one"
    # ...and an AGREEING standalone file is not an error -- the precedence is legitimate.
    with open(gl_path, "w", encoding="utf-8") as f:
        json.dump({"channels": live}, f)
    agree = next(e for e in check_project(root, skip_rew=True)["files"]
                 if e["file"].startswith("glossary.json"))
    assert agree["valid"] is True and agree["issues"] == [], agree
    os.remove(gl_path)

    print(f"selftest OK — empty project reports missing files without crashing; a seeded project "
          f"(project.json+glossary, dsp_profile.json, ledger, process) validates at the right "
          f"schema versions; cross-checks caught a glossary/ledger mismatch, a profile missing "
          f"the virtual_channels tier, and a spare slot naming an undeclared tier (SCR-042); "
          f"REW check reported as skipped, not attempted; a 2.x project is recognised as one and "
          f"told to migrate rather than to re-run intake. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
