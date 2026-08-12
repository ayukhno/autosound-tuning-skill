"""One-shot 2.x -> 3.0 project migration — the bridge an existing tune crosses once.

3.0 is a format break, not an evolution: the 2.x skill stays usable as its own release for anyone
who wants it (no GUI, no TCC), and nothing in 3.x reads a 2.x file. This script is the only thing
that reads both, and it is deliberately a separate script rather than a compatibility layer inside
the readers — a shim never gets removed, a migration finishes.

What it does, per project:

1. **EQ strings -> band objects** (the old v1 -> v2 step, still needed: a 2.x project may hold
   ledgers older than its own writer). `"PK 1000 -9 Q2"` -> `{"type": "PK", "f": 1000, ...}`,
   including the `LS`/`HS` shorthand the hand-authored files actually use.
2. **Identity out of the ledger, into `project.json`** (SCR-001). `slot`/`descr`/`role`/`order`/
   `hidden` become `channels[]` entries keyed by `code`; `tag_value` becomes
   `hardware.controls[<tag>]`. The newest snapshot carrying a field wins, and a value already in
   `project.json` is never overwritten — that file is the owner, and a human who has already
   answered intake outranks whatever a year-old snapshot said.
3. **`project_rev` stamped on every snapshot** (SCR-024). All history gets the SAME revision — the
   one this migration produces — because 2.x recorded nothing about which facts were in force
   when, and inventing a per-snapshot revision would be fabricating provenance. What that costs is
   stated plainly rather than hidden: after migrating, a pre-migration snapshot cannot tell you
   that its driver was replaced halfway through. Snapshots taken from here on can.
4. **Every machine file's `schema_version` -> 3**, the one number that now answers "which format
   is this project in" (`contract.py`'s `FORMAT_VERSION`).

Idempotent: re-running moves no further fields, and refuses to write any file that does not
validate afterwards — a migration that produces an invalid project is worse than one that stops.

Usage:
    python3 migrate.py <project-dir>              migrate one project in place
    python3 migrate.py <project-dir> --dry-run    report what would change, write nothing
    python3 migrate.py selftest
"""
from __future__ import annotations

import copy
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

import process as _process  # noqa: E402
import state as _state  # noqa: E402

import dsp_profile as _dsp_profile  # noqa: E402
import project as _project  # noqa: E402


#: 2.x row field -> the `project.json` field it becomes, where the NAME changed too.
#: `MOVED_TO_PROJECT_JSON` covers the fields that kept their name; this covers the one that did
#: not — and it is the one the released 2.x line actually used. `helix_ch` holds the DSP output
#: letter; `slot` is the same fact under the vendor-neutral name 3.0 gave it (a MUSWAY has slots
#: too, and calling the column "Helix" was always wrong for anything else).
RENAMED_TO_PROJECT_JSON = {"helix_ch": "slot"}


def migrate_snapshot(raw):
    """Pure transform: one 2.x snapshot -> 3.0, returned with the identity it gave up.

    Returns `(snapshot, identity)` — `identity` is `{code: {field: value}}` for whatever this
    snapshot was carrying, so the caller can fold it into `project.json`. The snapshot itself comes
    back without those fields, with structured EQ, and at the current schema version.
    """
    out = copy.deepcopy(raw)
    out["schema_version"] = _state.SCHEMA_VERSION
    identity = {}
    for tier in _state.tier_names(out):
        for code, row in (out.get(tier) or {}).items():
            eq = row.get("eq")
            if isinstance(eq, list) and eq and isinstance(eq[0], str):
                row["eq"] = [_state.eq_band_from_str(s) for s in eq]
            renamed = {}
            for field in _state.MOVED_TO_PROJECT_JSON:
                if field not in row:
                    continue
                value = row.pop(field)
                if value is None:
                    continue
                target = RENAMED_TO_PROJECT_JSON.get(field)
                if target is None:
                    identity.setdefault(code, {})[field] = value
                else:
                    renamed[target] = value
            # Renamed fields fill gaps only. A row carrying BOTH `helix_ch` and `slot` keeps
            # `slot`: whatever wrote the newer name did so deliberately, and the old one beside it
            # is leftover.
            for target, value in renamed.items():
                identity.setdefault(code, {}).setdefault(target, value)
            # `tag` stays on the row (it is structural: WHICH control affects this channel), but a
            # `tag_value` that travelled with it needs the tag name to find its new home.
            if "tag_value" in identity.get(code, {}) and row.get("tag"):
                identity[code]["_tag"] = row["tag"]
    return out, identity


def fold_identity(data, identity):
    """Merge collected identity into a `project.json` dict. Existing values are never overwritten.

    Returns the number of fields actually added, so a caller can tell "nothing to do" from "done".
    """
    added = 0
    rows = data.setdefault("channels", [])
    by_code = {r.get("code"): r for r in rows if isinstance(r, dict)}
    controls = data.setdefault("hardware", {}).setdefault("controls", {})
    for code, fields in identity.items():
        fields = dict(fields)
        tag = fields.pop("_tag", None)
        tag_value = fields.pop("tag_value", None)
        if tag and tag_value is not None and tag not in controls:
            controls[tag] = _project.fact(tag_value, source="user")
            added += 1
        if not fields:
            continue
        row = by_code.get(code)
        if row is None:
            row = {"code": code}
            rows.append(row)
            by_code[code] = row
        for field, value in fields.items():
            if row.get(field) in (None, ""):
                row[field] = value
                added += 1
    return added


def rename_profile_fields(profile):
    """Rewrite field tokens 2.x wrote to the names 3.0's vocabulary knows. Returns what changed.

    3.0 closed `FIELD_VOCABULARY`, and the token it refuses most often is `delay_ms` — which is
    what 2.x's OWN examples wrote (its `dsp_profile.py` selftest fixture and MUSWAY stub both use
    it). So a profile written exactly as the released skill demonstrated is invalid at 3.0, and
    the migration used to leave it that way with a warning: the run reported success and
    `contract.py check` called the profile broken from then on, forever, until somebody hand-edited
    a file they had no reason to suspect (2026-08-12).

    Only the near-miss table is applied — the same mapping the validator already uses to say "did
    you mean". Renaming on a guess would be worse than refusing: a token nobody recognises may be
    a real capability this profile is the only record of.
    """
    # The file is `{"dsp_profile": {...}}`; a hand-written one is sometimes the body alone. Both
    # shapes exist in the wild and `validate_profile` accepts either, so this has to as well —
    # reading only the top level found no groups and silently renamed nothing.
    body = profile.get("dsp_profile") if isinstance(profile.get("dsp_profile"), dict) else profile
    renames = []
    for index, group in enumerate(body.get("groups") or []):
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for at, token in enumerate(fields):
            better = _dsp_profile.FIELD_NEAR_MISSES.get(token)
            if better and token not in _dsp_profile.FIELD_VOCABULARY:
                fields[at] = better
                renames.append(f"groups.{index}.fields: {token} -> {better}")
    return renames


def channel_summary(snapshots):
    """`{tier: {"total": n, "off": n}}` derived from the snapshots being migrated (SCR-016).

    Derived, not invented: the codes are the ones this migration just read, and `off` is a real
    ledger field. Without this a migrated project opens with an empty "Project params" panel —
    found by running the real thing, not by a test — even though the count was sitting in the very
    files being rewritten.

    Newest snapshot wins for a code's `off` flag; the code set is the union across snapshots, so a
    channel that exists in one preset and not another is still counted once.
    """
    seen = {}
    for snap in snapshots:  # oldest first, so later writes overwrite earlier ones
        for tier in _state.tier_names(snap):
            rows = snap.get(tier) or {}
            for code, row in rows.items():
                seen.setdefault(tier, {})[code] = bool(row.get("off"))
    return {
        tier: {"total": len(codes), "off": sum(1 for is_off in codes.values() if is_off)}
        for tier, codes in seen.items()
        if codes
    }


def snapshot_paths(project_dir):
    """Every `v_NNN.json` under `<project>/state/`, oldest first per preset.

    Ordered because "the newest snapshot carrying a field wins" is only meaningful in order.
    Dot-directories are skipped for the same reason `contract.py` skips them — a consumer app's
    scratch directory is not a preset.
    """
    root = os.path.join(project_dir, "state")
    if not os.path.isdir(root):
        return []
    out = []
    for preset in sorted(n for n in os.listdir(root)
                         if not n.startswith(".") and os.path.isdir(os.path.join(root, n))):
        d = os.path.join(root, preset)
        versions = sorted(fn for fn in os.listdir(d)
                          if fn.endswith(".json") and _state._VER_RE.match(fn[:-5]))
        out.extend(os.path.join(d, fn) for fn in versions)
    return out


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, path)


def migrate_project(project_dir, dry_run=False):
    """Migrate one project in place. Returns a report dict; writes nothing when `dry_run`."""
    report = {"project_dir": project_dir, "snapshots": [], "identity_fields": 0,
              "channel_summary": {}, "files": [], "warnings": []}

    # 1. Read every snapshot and collect what it was carrying. Oldest first, so a newer snapshot's
    #    value simply overwrites an older one in the accumulator.
    migrated, identity = {}, {}
    for path in snapshot_paths(project_dir):
        snap, found = migrate_snapshot(_read_json(path))
        migrated[path] = snap
        for code, fields in found.items():
            identity.setdefault(code, {}).update(fields)

    # 2. Fold identity into project.json and write it. Saving is what assigns the new revision,
    #    and every snapshot is then stamped with that one number.
    proj = _project.Project(project_dir)
    data = proj.load()
    data["schema_version"] = _project.SCHEMA_VERSION
    report["identity_fields"] = fold_identity(data, identity)
    if not data.get("channel_summary"):
        data["channel_summary"] = channel_summary(list(migrated.values()))
    report["channel_summary"] = data.get("channel_summary") or {}
    if dry_run:
        rev = data.get("project_rev", 0) + 1
    else:
        proj.save(data)
        rev = proj.load()["project_rev"]
    report["project_rev"] = rev
    report["files"].append("project.json")

    # 3. Write the snapshots, all stamped with that revision (see the module docstring on why
    #    history collapses to a single revision here).
    for path, snap in migrated.items():
        snap["project_rev"] = rev
        _state.validate(snap)  # refuse to write a file that isn't actually 3.0
        if not dry_run:
            _write_json(path, snap)
        report["snapshots"].append(os.path.relpath(path, project_dir))

    # 4. The remaining machine files carry a version; nothing else in them changed.
    process_state = os.path.join(project_dir, "process", "process-state.json")
    if os.path.isfile(process_state):
        state = _read_json(process_state)
        state["schema_version"] = _process.SCHEMA_VERSION
        _process.validate(state)
        if not dry_run:
            _write_json(process_state, state)
        report["files"].append("process/process-state.json")

    profile_path = os.path.join(project_dir, "dsp_profile.json")
    if os.path.isfile(profile_path):
        profile = _read_json(profile_path)
        renames = rename_profile_fields(profile)
        if renames:
            report["field_renames"] = renames
        try:
            _dsp_profile.validate_profile(profile)
        except ValueError as exc:
            report["warnings"].append(f"dsp_profile.json left alone — it does not validate: {exc}")
        else:
            if not dry_run:
                _dsp_profile.save_profile(profile_path, profile)  # stamps schema_version
            report["files"].append("dsp_profile.json")

    return report


def render_report(report, dry_run=False):
    what = "would migrate" if dry_run else "migrated"
    lines = [f"# 2.x → 3.0 migration — {report['project_dir']}", ""]
    lines.append(f"- project_rev now: **{report['project_rev']}** (stamped onto every snapshot)")
    lines.append(f"- identity fields moved into project.json: {report['identity_fields']}")
    for rename in report.get("field_renames") or []:
        lines.append(f"  - dsp_profile.json field renamed: {rename}")
    for tier, counts in (report.get("channel_summary") or {}).items():
        lines.append(f"  - {tier}: {counts['total']} ({counts['off']} off)")
    lines.append(f"- snapshots {what}: {len(report['snapshots'])}")
    for rel in report["snapshots"]:
        lines.append(f"  - {rel}")
    lines.append(f"- files {what}: {', '.join(report['files'])}")
    for warning in report["warnings"]:
        lines.append(f"- ⚠️ {warning}")
    lines.append("")
    lines.append("Confirm with: `python3 rew_tool/contract.py check <project>`")
    return "\n".join(lines)


def _main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] == "selftest":
        return _selftest()
    project_dir = argv[0]
    if not os.path.isdir(project_dir):
        print(f"no such project directory: {project_dir}", file=sys.stderr)
        return 2
    dry_run = "--dry-run" in argv
    report = migrate_project(project_dir, dry_run=dry_run)
    print(render_report(report, dry_run=dry_run))
    return 0


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest():
    import tempfile

    root = tempfile.mkdtemp(prefix="autosound_migrate_")
    preset_dir = os.path.join(root, "state", "SQ_Jazzi")
    os.makedirs(preset_dir)

    # A 2.x project as it actually looks in the wild. Two shapes on purpose, because two exist:
    #
    #   `w-L` and `sub` carry `helix_ch` — the ONLY identity field the RELEASED 2.x line ever
    #   wrote (`CHANNEL_FIELDS` at v2.8.1). This fixture used to use `slot` throughout, which no
    #   released version produced: the migration was being tested against a development state and
    #   passed while a real v2.8.1 project migrated to an empty Slot column (2026-08-12).
    #
    #   `VFL` carries `slot`/`descr`/`hidden`, the shape the development states between releases
    #   wrote. Some projects are in it, so it stays covered.
    #
    # Also 2.x-authentic: no schema_version, EQ as strings (incl. the LS shorthand), `tag_value`
    # beside its `tag`.
    v1 = {
        "preset": "SQ_Jazzi", "version": "v_001", "sample_rate": 96000,
        "channels": {
            "w-L": {"helix_ch": "C", "descr": "Front L Woofer", "role": "woofer", "order": 1,
                    "hp": {"f": 70, "type": "BW", "slope": 12},
                    "lp": {"f": 270, "type": "BW", "slope": 12},
                    "gain_db": -7.8, "ta_ms": 5.38, "polarity": "NORM",
                    "eq": ["PK 1000 -9 Q2", "LS 150 +2.5 Q0.71"]},
            "sub": {"helix_ch": "K", "tag": "SubRC", "tag_value": "-4dB",
                    "hp": {"f": 20, "type": "BE", "slope": 12},
                    "lp": {"f": 45, "type": "BW", "slope": 12},
                    "gain_db": -6.0, "ta_ms": 5.0, "polarity": "NORM"},
            # Both names at once — a project half-touched by a development build. The newer name
            # wins; the leftover must not overwrite it.
            "w-R": {"helix_ch": "OLD", "slot": "D",
                    "hp": {"f": 70, "type": "BW", "slope": 12},
                    "lp": {"f": 270, "type": "BW", "slope": 12},
                    "gain_db": -7.8, "ta_ms": 5.30, "polarity": "NORM"},
        },
        "virtual_channels": {
            "VFL": {"slot": "A", "descr": "Front L Full", "hidden": False,
                    "gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM",
                    "eq": ["APF2 2177 Q1.5"]},
        },
    }
    _write_json(os.path.join(preset_dir, "v_001.json"), v1)
    # a NEWER snapshot with a corrected description -- the newest value must win.
    v2 = copy.deepcopy(v1)
    v2["version"] = "v_002"
    v2["channels"]["w-L"]["descr"] = "Front L Woofer (corrected)"
    _write_json(os.path.join(preset_dir, "v_002.json"), v2)
    with open(os.path.join(preset_dir, "HEAD"), "w", encoding="utf-8") as f:
        f.write("v_002\n")

    # A DSP profile written exactly as the RELEASED 2.x skill demonstrated it — its own MUSWAY
    # stub used `delay_ms`, which 3.0's closed vocabulary refuses. Migration must fix the token,
    # not warn about it and move on.
    _write_json(os.path.join(root, "dsp_profile.json"), {
        "dsp_profile": {
            "name": "M6V4", "vendor": "Musway", "sample_rate_hz": 96000,
            "groups": [
                {"id": "physical_outputs", "label": "Output channels",
                 "fields": ["hp", "lp", "gain_db", "delay_ms", "polarity"]},
                {"id": "inputs", "label": "Inputs", "no_crossover": True,
                 "fields": ["gain_db", "eq", "delay_ms"]},
            ],
        }
    })

    # a fact the human already answered in project.json must NOT be clobbered by an old snapshot.
    proj = _project.Project(root)
    seeded = proj.load()
    seeded["channels"] = [{"code": "sub", "descr": "Subwoofer (from intake)"}]
    proj.save(seeded)
    rev_before = proj.load()["project_rev"]

    # --dry-run leaves every byte alone.
    before = _read_json(os.path.join(preset_dir, "v_001.json"))
    migrate_project(root, dry_run=True)
    assert _read_json(os.path.join(preset_dir, "v_001.json")) == before, "dry run wrote something"

    report = migrate_project(root)

    # identity landed in project.json, newest snapshot winning, intake's own answer untouched.
    data = _project.Project(root).load()
    by_code = {r["code"]: r for r in data["channels"]}
    assert by_code["w-L"]["descr"] == "Front L Woofer (corrected)", by_code["w-L"]
    # `helix_ch` -> `slot`: the DSP output letter, the one thing on a 2.x row the Arbiter types
    # into the processor. It used to be carried nowhere at all — the migration reported success
    # and left the Slot column empty (2026-08-12).
    assert by_code["w-L"]["slot"] == "C" and by_code["w-L"]["order"] == 1, by_code["w-L"]
    assert by_code["sub"]["slot"] == "K", by_code["sub"]
    assert by_code["sub"]["descr"] == "Subwoofer (from intake)", by_code["sub"]
    # both names on one row: the newer one wins, the leftover does not overwrite it.
    assert by_code["w-R"]["slot"] == "D", by_code["w-R"]
    assert by_code["VFL"]["slot"] == "A", by_code  # a virtual row's identity moves too
    assert _project.fact_value(data["hardware"]["controls"]["SubRC"]) == "-4dB", data["hardware"]
    # SCR-016: the tier counts a consumer's Project-params panel renders, derived from the very
    # snapshots being migrated rather than left for a human to re-enter.
    assert data["channel_summary"] == {"channels": {"total": 3, "off": 0},
                                        "virtual_channels": {"total": 1, "off": 0}}, data
    assert data["project_rev"] > rev_before, data["project_rev"]

    # the profile's 2.x token was renamed, the file now validates, and the run said so.
    assert report.get("field_renames"), report
    profile = _read_json(os.path.join(root, "dsp_profile.json"))
    fields = [f for g in profile["dsp_profile"]["groups"] for f in g["fields"]]
    assert "delay_ms" not in fields and fields.count("ta_ms") == 2, fields
    _dsp_profile.validate_profile(profile)  # raises if the migration left it broken
    assert "dsp_profile.json" in report["files"], report

    # the ledgers are 3.0: no identity, structured EQ, every snapshot stamped with one revision.
    hist = _state.PresetHistory(os.path.join(root, "state"), "SQ_Jazzi", project_dir=root)
    for version in ("v_001", "v_002"):
        snap = hist.load(version)
        _state.validate(snap)
        assert snap["schema_version"] == _state.SCHEMA_VERSION, snap
        assert snap["project_rev"] == report["project_rev"], snap
        for tier in _state.tier_names(snap):
            for row in (snap.get(tier) or {}).values():
                assert not any(f in row for f in _state.MOVED_TO_PROJECT_JSON), row
        assert snap["channels"]["w-L"]["eq"][0] == {
            "type": "PK", "f": 1000.0, "gain_db": -9.0, "q": 2.0}, snap
        assert snap["channels"]["w-L"]["eq"][1]["type"] == "LSH", snap  # LS shorthand normalized
        assert snap["virtual_channels"]["VFL"]["eq"][0]["type"] == "APF2", snap
        assert snap["channels"]["sub"]["tag"] == "SubRC", snap  # `tag` is structural, it stays

    # the settings sheet still prints slots -- they now come from project.json.
    sheet = hist.render("v_002")
    assert "| w-L | C |" in sheet, sheet

    # idempotent: a second run moves no further fields and changes no snapshot content (only
    # project_rev moves, because saving project.json is a write and the counter counts writes).
    snap_before = hist.load("v_002")
    again = migrate_project(root)
    after = hist.load("v_002")
    assert {k: v for k, v in after.items() if k != "project_rev"} == {
        k: v for k, v in snap_before.items() if k != "project_rev"}, after
    assert again["identity_fields"] == 0, again

    print(f"selftest OK — a 2.x project (string EQ incl. LS shorthand, `helix_ch` as the released "
          f"2.x line wrote it, identity on ledger rows, "
          f"tag_value beside its tag) migrated to 3.0: identity moved into project.json with the "
          f"newest snapshot winning and intake's own answer left intact, tag_value became a "
          f"hardware control, every snapshot stamped project_rev={report['project_rev']} and "
          f"validated, the settings sheet kept its Slot column, --dry-run wrote nothing, a re-run "
          f"moved no further fields. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
