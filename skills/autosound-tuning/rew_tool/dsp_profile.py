"""DSP processor capability profile — what a DSP MODEL can do, not what one project set it to.

This is a separate artifact from `state/state.py`'s per-project ledger (channel gains/crossovers/
delay for ONE car). A profile answers "does this DSP even have virtual channels? does it have
per-input EQ?" — the schema-level facts a project's data model must be built against, so the same
UI/tooling can serve a Helix (virtual + physical tiers, no crossover on virtual) and a MUSWAY (no
virtual tier at all, but per-input Optic/USB/BT gain+EQ) without per-DSP code.

Design invariants
    * `groups` is the load-bearing field: an ordered list of the tiers/categories this DSP model
      actually exposes (e.g. virtual_channels, physical_outputs, inputs), each declaring which
      per-row fields are meaningful for it. A consumer renders whatever groups+fields are declared
      — it never assumes a fixed two-tier (virtual/output) shape. Absence of a group means the DSP
      genuinely doesn't have that tier (e.g. MUSWAY has no virtual_channels group at all).
    * Unconfirmed facts are `null`, not omitted — `open_questions()` walks the whole structure and
      surfaces every null plus any declared `_open_questions` freeform notes. This is what makes
      profile-building incremental: a re-run only asks about what's still null.
    * A profile is the DSP MODEL's facts, not one car's install — no personal data, safe to
      contribute to the community as-is (see `gates/side_effect.py::post_dsp_profile`).
    * JSON, not YAML — this module stays stdlib-only (matches `rew_api.py`/`state.py`), and a
      project's `dsp_profile.json` sits next to its `presets/<preset>/state/v_NNN.json` ledger in
      the same serialization family.
"""

import copy
import glob
import hashlib
import json
import os

# ── schema ──────────────────────────────────────────────────────────────────
TOP_REQUIRED = ("name", "vendor", "groups")
GROUP_REQUIRED = ("id", "label", "fields")


def _unwrap(data):
    """Accept either {"dsp_profile": {...}} (the on-disk shape) or the inner dict directly."""
    return data.get("dsp_profile", data) if isinstance(data, dict) else data


def _validate_group(g):
    missing = [f for f in GROUP_REQUIRED if f not in g]
    if missing:
        raise ValueError(f"group {g.get('id', '?')!r} missing {missing}")
    if not isinstance(g["fields"], list) or not g["fields"]:
        raise ValueError(f"group {g['id']!r}.fields must be a non-empty list")


def validate_profile(data):
    """Raise ValueError on malformed profile; return `data` unchanged if OK."""
    profile = _unwrap(data)
    missing = [k for k in TOP_REQUIRED if k not in profile]
    if missing:
        raise ValueError(f"profile missing required key(s) {missing}")
    if not isinstance(profile["name"], str) or not profile["name"].strip():
        raise ValueError("profile.name must be a non-empty string")
    if not isinstance(profile["vendor"], str) or not profile["vendor"].strip():
        raise ValueError("profile.vendor must be a non-empty string")
    groups = profile["groups"]
    if not isinstance(groups, list) or not groups:
        raise ValueError("profile.groups must be a non-empty list")
    seen = set()
    for g in groups:
        _validate_group(g)
        if g["id"] in seen:
            raise ValueError(f"duplicate group id {g['id']!r}")
        seen.add(g["id"])
    return data


# ── read/write ────────────────────────────────────────────────────────────────
def load_profile(path):
    with open(path) as f:
        return json.load(f)


def save_profile(path, data):
    """Validate, then write. Refuses to write a malformed profile (same discipline as
    state.py's snapshot() — a garbage profile can't be silently banked)."""
    validate_profile(data)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
    return path


# ── bundled-library lookup ─────────────────────────────────────────────────────
def find_bundled(vendor, model, bundled_dir):
    """Exact vendor+model match only against a directory of reference profiles.

    No fuzzy/sibling matching — same rule as project-intake.md §4: another model's profile,
    even a platform sibling's, must never be assumed to apply. Returns None if no exact match.
    """
    for path in sorted(glob.glob(os.path.join(bundled_dir, "*.json"))):
        try:
            data = load_profile(path)
        except (OSError, ValueError):
            continue
        profile = _unwrap(data)
        if (profile.get("vendor", "").strip().lower() == vendor.strip().lower()
                and profile.get("name", "").strip().lower() == model.strip().lower()):
            return data
    return None


# ── incremental interview support ──────────────────────────────────────────────
def open_questions(data):
    """Every still-null field (dotted path) plus any declared `_open_questions` freeform notes.

    Drives incremental onboarding: a resumed interview asks only about what this returns, not
    the whole checklist again.
    """
    profile = _unwrap(data)
    out = list(profile.get("_open_questions") or [])

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "_open_questions":
                    continue
                if v is None:
                    out.append(f"{prefix}{k}")
                else:
                    walk(f"{prefix}{k}.", v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(f"{prefix}{i}.", v)

    walk("", profile)
    return out


# ── diff (mirrors state.py's diff_states shape) ────────────────────────────────
def _diff_scalar(a, b):
    return None if a == b else [a, b]


def diff_profile(old, new):
    """Structured deltas old -> new at top-level-field and per-group granularity. Only changed
    things appear — used to decide whether a community contribution is `new` or `update`."""
    op, npf = _unwrap(old), _unwrap(new)
    out = {"top": {}, "groups": {}}
    for k in sorted((set(op) | set(npf)) - {"groups", "_contributed"}):
        d = _diff_scalar(op.get(k), npf.get(k))
        if d is not None:
            out["top"][k] = d
    og = {g["id"]: g for g in op.get("groups", [])}
    ng = {g["id"]: g for g in npf.get("groups", [])}
    for gid in sorted(set(og) | set(ng)):
        if gid not in og:
            out["groups"][gid] = {"__added__": True}
            continue
        if gid not in ng:
            out["groups"][gid] = {"__removed__": True}
            continue
        fields = {}
        for fk in sorted(set(og[gid]) | set(ng[gid])):
            d = _diff_scalar(og[gid].get(fk), ng[gid].get(fk))
            if d is not None:
                fields[fk] = d
        if fields:
            out["groups"][gid] = fields
    return out


def content_hash(data):
    """Stable hash of the profile's substantive content, excluding `_contributed` bookkeeping —
    lets a caller detect "nothing new since the last post" without a network round-trip."""
    profile = copy.deepcopy(_unwrap(data))
    profile.pop("_contributed", None)
    blob = json.dumps(profile, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ── CLI ───────────────────────────────────────────────────────────────────────
def _main(argv=None):
    import argparse

    p = argparse.ArgumentParser(description="DSP processor capability profile")
    sub = p.add_subparsers(dest="cmd")

    vp = sub.add_parser("validate")
    vp.add_argument("path")

    oq = sub.add_parser("open-questions")
    oq.add_argument("path")

    fb = sub.add_parser("find-bundled")
    fb.add_argument("vendor")
    fb.add_argument("model")
    fb.add_argument("bundled_dir")

    dp = sub.add_parser("diff")
    dp.add_argument("old_path")
    dp.add_argument("new_path")

    sub.add_parser("selftest")
    args = p.parse_args(argv)

    if args.cmd == "selftest" or args.cmd is None:
        return _selftest()
    if args.cmd == "validate":
        validate_profile(load_profile(args.path))
        print("OK")
        return 0
    if args.cmd == "open-questions":
        for q in open_questions(load_profile(args.path)):
            print(q)
        return 0
    if args.cmd == "find-bundled":
        found = find_bundled(args.vendor, args.model, args.bundled_dir)
        print(json.dumps(found, indent=2, ensure_ascii=False) if found else "no exact match")
        return 0
    if args.cmd == "diff":
        print(json.dumps(diff_profile(load_profile(args.old_path), load_profile(args.new_path)),
                          indent=2, ensure_ascii=False))
        return 0


# ── self-test ─────────────────────────────────────────────────────────────────
def _musway_stub():
    """A deliberately incomplete profile — the interview's starting point for a new DSP."""
    return {
        "dsp_profile": {
            "name": "M6V4",
            "vendor": "Musway",
            "groups": [
                {"id": "physical_outputs", "label": "Output channels",
                 "fields": ["hp", "lp", "gain_db", "delay_ms", "polarity"]},
                {"id": "inputs", "label": "Inputs", "no_crossover": True,
                 "fields": ["gain_db", "eq", "delay_ms"]},
            ],
            "sample_rate_hz": None,
            "_open_questions": ["confirm from vendor software UI, not just user memory"],
        }
    }


def _selftest():
    import tempfile

    helix = {
        "dsp_profile": {
            "name": "Helix DSP Ultra S",
            "vendor": "Audiotec-Fischer",
            "groups": [
                {"id": "virtual_channels", "label": "Virtual channels", "no_crossover": True,
                 "fields": ["gain_db", "delay_ms", "polarity", "phase_deg", "mute", "eq"]},
                {"id": "physical_outputs", "label": "Output channels",
                 "fields": ["hp", "lp", "gain_db", "delay_ms", "polarity", "phase_deg", "eq"]},
            ],
            "sample_rate_hz": 96000,
        }
    }
    validate_profile(helix)  # must not raise

    # a malformed profile (group missing "fields") must be refused, not silently banked.
    bad = copy.deepcopy(helix)
    del bad["dsp_profile"]["groups"][0]["fields"]
    try:
        validate_profile(bad)
        raise AssertionError("validate_profile accepted a group with no fields")
    except ValueError:
        pass

    # MUSWAY has genuinely no virtual_channels group — that must be representable, not an error.
    musway = _musway_stub()
    validate_profile(musway)
    ids = [g["id"] for g in musway["dsp_profile"]["groups"]]
    assert "virtual_channels" not in ids, ids
    assert "inputs" in ids, ids

    # open_questions surfaces the null sample_rate_hz plus the freeform note.
    oq = open_questions(musway)
    assert "sample_rate_hz" in oq, oq
    assert any("vendor software" in q for q in oq), oq
    assert open_questions(helix) == [], "a fully-confirmed profile should have no open questions"

    # find_bundled: exact match only, no sibling/fuzzy match.
    tmp = tempfile.mkdtemp(prefix="dsp_profiles_")
    save_profile(os.path.join(tmp, "helix-dsp-ultra-s.json"), helix)
    found = find_bundled("Audiotec-Fischer", "Helix DSP Ultra S", tmp)
    assert found is not None and found["dsp_profile"]["name"] == "Helix DSP Ultra S"
    assert find_bundled("Musway", "M6V4", tmp) is None, "must not fuzzy-match a different vendor"
    assert find_bundled("Audiotec-Fischer", "Helix DSP Ultra", tmp) is None, \
        "must not match on a partial/sibling model name"

    # diff_profile: filling sample_rate_hz shows up as a top-level change; nothing else moves.
    filled = copy.deepcopy(musway)
    filled["dsp_profile"]["sample_rate_hz"] = 48000
    d = diff_profile(musway, filled)
    assert d["top"]["sample_rate_hz"] == [None, 48000], d
    assert d["groups"] == {}, "unrelated groups must not appear in the diff"

    # content_hash ignores _contributed bookkeeping so a post-then-rehash round-trip is stable.
    h1 = content_hash(filled)
    stamped = copy.deepcopy(filled)
    stamped["dsp_profile"]["_contributed"] = {"url": "https://example/1", "sha256": h1}
    assert content_hash(stamped) == h1, "content_hash must ignore _contributed bookkeeping"

    print(f"selftest OK — validate rejects malformed groups, MUSWAY's missing virtual_channels "
          f"tier is representable (not an error), open_questions found the null field + freeform "
          f"note, find_bundled matched exactly and refused a sibling/partial name, diff_profile "
          f"isolated the one changed field, content_hash is stable across _contributed stamping. "
          f"tmp={tmp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
