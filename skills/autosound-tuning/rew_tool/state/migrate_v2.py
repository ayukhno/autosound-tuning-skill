"""One-shot v1 -> v2 ledger migration (SCR-005/006, autosound-tcc sync 2026-07-29).

v1 ledgers (this repo's two hand-edited dogfood files, `data/private/state/{FULL,SQ}/v_001.json`
in the `autosound-tcc` project) have no `schema_version` and carry `eq` as inline strings
(`"PK 1000 -9 Q2"`, and the `LS`/`HS` shorthand in the wild). v2 requires `schema_version` and
structured EQ band objects (`{"type": "PK", "f": 1000, "gain_db": -9, "q": 2}`). Everything else --
channels, virtual_channels, features, slot_label, save -- is copied as-is; this script only
touches what the schema actually changed. No backward-compat shim is kept: v1 files that are never
migrated simply fail `state.validate()` from here on, which is the point (SKILL-SYNC-PLAN.md §0).

Usage:
    python migrate_v2.py <root> [<preset> ...]   # every preset dir under <root> if none given
    python migrate_v2.py selftest
"""
from __future__ import annotations

import copy
import json
import os
import sys

import state as _state


def migrate_snapshot(raw: dict) -> dict:
    """Pure transform: v1 snapshot dict -> v2. Idempotent -- a v2 snapshot passes through
    unchanged (checked by `eq` band shape, not just `schema_version`, so a partially-hand-patched
    file doesn't get skipped with strings still inside it)."""
    out = copy.deepcopy(raw)
    out["schema_version"] = _state.SCHEMA_VERSION
    for tier in _state.tier_names(out):
        for row in (out.get(tier) or {}).values():
            eq = row.get("eq")
            if isinstance(eq, list) and eq and isinstance(eq[0], str):
                row["eq"] = [_state.eq_band_from_str(s) for s in eq]
    return out


def _needs_migration(raw: dict) -> bool:
    if raw.get("schema_version") != _state.SCHEMA_VERSION:
        return True
    for tier in _state.tier_names(raw):
        for row in (raw.get(tier) or {}).values():
            eq = row.get("eq")
            if isinstance(eq, list) and eq and isinstance(eq[0], str):
                return True
    return False


def migrate_preset(root: str, preset: str) -> list:
    """Rewrite every v_NNN.json for one preset in place. Returns the versions actually touched."""
    d = os.path.join(root, preset)
    touched = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(d, fn)
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not _needs_migration(raw):
            continue
        migrated = migrate_snapshot(raw)
        _state.validate(migrated)  # refuse to write a v2 file that doesn't actually validate as v2
        with open(path, "w", encoding="utf-8") as f:
            json.dump(migrated, f, indent=2, sort_keys=True, ensure_ascii=False)
        touched.append(fn[:-5])
    return touched


def _main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] == "selftest":
        return _selftest()
    root = argv[0]
    presets = argv[1:] or sorted(
        n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))
    )
    if not presets:
        print(f"no preset directories found under {root!r}")
        return 1
    for preset in presets:
        touched = migrate_preset(root, preset)
        print(f"{preset}: migrated {touched or '(nothing to do -- already v2)'}")
    return 0


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest():
    import tempfile

    root = tempfile.mkdtemp(prefix="autosound_migrate_")
    preset_dir = os.path.join(root, "SQ_Jazzi")
    os.makedirs(preset_dir)
    v1 = {
        "preset": "SQ_Jazzi", "version": "v_001", "sample_rate": 96000,
        "channels": {
            "w-L": {"hp": {"f": 70, "type": "BW", "slope": 12},
                    "lp": {"f": 270, "type": "BW", "slope": 12},
                    "gain_db": -7.8, "ta_ms": 5.38, "polarity": "NORM",
                    "eq": ["PK 1000 -9 Q2", "LS 150 +2.5 Q0.71"]},
        },
        "virtual_channels": {
            "VFL": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM", "eq": ["APF2 2177 Q1.5"]},
        },
    }
    with open(os.path.join(preset_dir, "v_001.json"), "w", encoding="utf-8") as f:
        json.dump(v1, f)
    with open(os.path.join(preset_dir, "HEAD"), "w", encoding="utf-8") as f:
        f.write("v_001\n")

    touched = migrate_preset(root, "SQ_Jazzi")
    assert touched == ["v_001"], touched

    migrated = _state.PresetHistory(root, "SQ_Jazzi").load("v_001")
    assert migrated["schema_version"] == _state.SCHEMA_VERSION, migrated
    assert migrated["channels"]["w-L"]["eq"][0] == {
        "type": "PK", "f": 1000.0, "gain_db": -9.0, "q": 2.0}, migrated
    # the `LS` shorthand actually used in the wild normalizes to canonical `LSH`.
    assert migrated["channels"]["w-L"]["eq"][1]["type"] == "LSH", migrated
    assert migrated["virtual_channels"]["VFL"]["eq"][0]["type"] == "APF2", migrated
    _state.validate(migrated)  # must pass v2 validation post-migration

    # idempotent: a second pass touches nothing.
    again = migrate_preset(root, "SQ_Jazzi")
    assert again == [], f"re-migrating an already-v2 file must be a no-op, touched {again}"

    print(f"selftest OK — v1 ledger (string EQ incl. LS/HS shorthand, no schema_version) migrated "
          f"to v2 (structured EQ, schema_version={_state.SCHEMA_VERSION}), virtual tier converted "
          f"too, validates post-migration, re-run is a no-op. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
