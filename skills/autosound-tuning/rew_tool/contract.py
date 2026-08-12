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
    entry = _entry("glossary.json (or project.json.glossary)", present, None, present or None,
                    [] if present else ["no glossary yet -- naming/measurement checks are inert"])
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
    return {"project_dir": project_dir, "ok": ok, "complete": complete, "missing": missing,
            "files": files, "cross_checks": cross}


# ── rendering ───────────────────────────────────────────────────────────────────
def render_report(report):
    lines = [f"# Project contract check — {report['project_dir']}", ""]
    if report.get("missing"):
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

    print(f"selftest OK — empty project reports missing files without crashing; a seeded project "
          f"(project.json+glossary, dsp_profile.json, ledger, process) validates at the right "
          f"schema versions; cross-checks caught a glossary/ledger mismatch, a profile missing "
          f"the virtual_channels tier, and a spare slot naming an undeclared tier (SCR-042); "
          f"REW check reported as skipped, not attempted. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
