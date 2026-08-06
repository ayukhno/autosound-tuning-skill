"""apply-change — the gate that turns a proposed hard-params delta into (a) a banked snapshot and
(b) the human-applicable SETTINGS SHEET the Arbiter keys into the PC-Tool screen.

Why this exists (the unlock both v3 reviews pointed at): the DSP is written by the Arbiter's HAND in
Helix — no script can interpose on that. So the gate does not "apply" to the device; it earns its
keep by being the ONLY producer of an artifact the human actually needs — the clean channel/param
old→new sheet (with samples derived for the active rate). Bypass the gate and you get nothing usable,
so the compliant path is also the easiest path. That inversion is what makes v3 hold where v2's
"you must" prose did not.

Lifecycle (AD-1): `propose` banks a 🟡 snapshot with the changed channels marked `proposed` and hands
back the settings sheet → the Arbiter enters it in Helix by HAND → `attest` banks a 🟢 snapshot
flipping those channels to `applied`. `measured` follows when a control measurement confirms effect.
The state file is truth for INTENT + ATTESTED-APPLIED, never a guaranteed device mirror.

Gate policy (per AD-2):
  * DETERMINISTIC REFUSALS (hard — correctness/process, not acoustic taste): unknown channel/field
    (typo protection), partial delta onto a non-existent channel, TA given as samples instead of the
    canonical ms, and any resulting state that fails `state.validate`.
  * ADVISORIES (soft — the old "rails on nouns" demoted to voice-with-waiver): a large gain jump, a
    polarity flip, a big delay or crossover move. Printed as ⚠️, never blocking — the Arbiter's ear
    and measurement are the authority on the acoustic nouns.

Tier-aware (schema v2, 2026-07-29): a delta may address any tier the ledger already has (any top-
level key `state.tier_names()` recognizes), not just `channels` — e.g.
`{"virtual_channels": {"VFL": {"gain_db": -1.0}}, "channels": {"w-L": {"ta_ms": 5.45}}}`. The old
FLAT form (`{channel: {field: value}}`) still means `channels`, unchanged — a delta is read as
tier-keyed only when every one of its top-level keys is already a known tier name, so an ordinary
channel-name delta is never misread. A tier a project's ledger doesn't have YET cannot be addressed
this way — intake seeds every profile-declared tier, even empty, at the first snapshot.
"""

import copy
import datetime
import json
import os

import state as _state

# advisory thresholds — voice, not veto
_GAIN_JUMP_DB = 6.0
_TA_JUMP_MS = 2.0
_XOVER_FACTOR = 1.5

_MERGEABLE = set(_state.CHANNEL_FIELDS)


def _split_by_tier(current, delta):
    """Classify `delta` as flat (`{channel: {field: value}}`, meaning `channels`) or tier-keyed
    (`{tier: {channel: {field: value}}}`) and return it normalized to `{tier: {channel: fields}}`.

    Deterministic, not guessed: tier-keyed ONLY when every top-level key of `delta` is already a
    tier `current` has (`state.tier_names`) — a delta naming an ordinary channel can never collide
    with this, since channel names are never also tier names.
    """
    if delta and set(delta) <= set(_state.tier_names(current)):
        return delta
    return {"channels": delta}


def apply_delta(current, delta):
    """Merge a delta onto `current`, marking every touched row `proposed`.

    Crossover legs (hp/lp) are replaced wholesale. Raises ValueError on the deterministic-refusal
    cases (typos, phantom channels, samples-not-ms) — see `_split_by_tier` for the flat-vs-tier-
    keyed delta shapes this accepts.
    """
    proposed = copy.deepcopy(current)
    tier_delta = _split_by_tier(current, delta)
    for tier, rows in tier_delta.items():
        chans = proposed.setdefault(tier, {})
        for ch_name, fields in rows.items():
            if not isinstance(fields, dict):
                raise ValueError(f"delta[{tier}][{ch_name!r}] must be an object of field→value")
            unknown = [f for f in fields if f not in _MERGEABLE]
            if unknown:
                if "ta_samples" in unknown or "ta_smp" in unknown:
                    raise ValueError(f"{tier}.{ch_name}: TA must be given as canonical `ta_ms`, not "
                                     f"samples (samples are derived at render for the active rate)")
                raise ValueError(f"{tier}.{ch_name}: unknown field(s) {unknown} — "
                                 f"valid: {sorted(_MERGEABLE)}")
            if ch_name not in chans:
                # Only `channels` (physical outputs) has required fields, so only there does a
                # brand-new row need a full definition; any other tier may start from a partial one.
                if tier == "channels":
                    missing = [f for f in ("hp", "lp", "gain_db", "ta_ms", "polarity") if f not in fields]
                    if missing:
                        raise ValueError(f"{ch_name} is not in the current state — to add a channel "
                                         f"give a full definition (missing {missing}); a partial "
                                         f"edit needs an existing channel (typo?)")
                chans[ch_name] = {}
            chans[ch_name].update(fields)
            chans[ch_name]["status"] = "proposed"
    return proposed


def advisories(current, proposed):
    """Soft ⚠️ notes on the acoustic nouns — voice, waivable, never blocking. Walks every tier."""
    out = []
    for tier in sorted(set(_state.tier_names(current)) | set(_state.tier_names(proposed))):
        cch, pch = current.get(tier) or {}, proposed.get(tier) or {}
        for ch in sorted(set(cch) & set(pch)):
            a, b = cch[ch], pch[ch]
            label = ch if tier == "channels" else f"{tier}:{ch}"
            if isinstance(a.get("gain_db"), (int, float)) and isinstance(b.get("gain_db"), (int, float)):
                if abs(b["gain_db"] - a["gain_db"]) >= _GAIN_JUMP_DB:
                    out.append(f"{label}: gain jump {a['gain_db']:g}→{b['gain_db']:g} dB "
                               f"(≥{_GAIN_JUMP_DB:g}) — double-check it's intended.")
            if a.get("polarity") != b.get("polarity"):
                out.append(f"{label}: polarity {a.get('polarity')}→{b.get('polarity')} — verify by "
                           f"SUMMATION, not by eye (a flip that helps one joint can wreck another).")
            if isinstance(a.get("ta_ms"), (int, float)) and isinstance(b.get("ta_ms"), (int, float)):
                if abs(b["ta_ms"] - a["ta_ms"]) >= _TA_JUMP_MS:
                    out.append(f"{label}: TA jump {a['ta_ms']:g}→{b['ta_ms']:g} ms "
                               f"(≥{_TA_JUMP_MS:g}) — big move.")
            for leg in ("hp", "lp"):
                fa, fb = a.get(leg), b.get(leg)
                if isinstance(fa, dict) and isinstance(fb, dict) and fa.get("f") and fb.get("f"):
                    hi, lo = max(fa["f"], fb["f"]), min(fa["f"], fb["f"])
                    if lo and hi / lo >= _XOVER_FACTOR:
                        out.append(f"{label}: {leg.upper()} {fa['f']:g}→{fb['f']:g} Hz — large "
                                   f"crossover move; re-check the joint phase/summation.")
    return out


def _fmt_val(field, val, rate):
    if field == "ta_ms" and isinstance(val, (int, float)):
        return f"{val:g} ms ({_state.samples_for(val, rate)} smp)"
    if field in ("hp", "lp"):
        return _state._fmt_filter(val)
    if field == "gain_db" and isinstance(val, (int, float)):
        return f"{val:g} dB"
    if field == "eq" and isinstance(val, (list, tuple)):
        # Bands are structured objects (schema v2) -- render them the way the human keys them
        # into the EQ screen, not a Python list/dict repr. Empty = say so explicitly rather than
        # render "[]", since "no bands" is a real, enterable state.
        bands = _state.eq_str(val)
        return " · ".join(bands) if bands else "(no bands)"
    return str(val)


# Identity fields are absent on purpose (schema v3): they cannot appear in a ledger diff any
# more, so a label for them would describe a row this sheet can never contain.
_FIELD_LABEL = {"hp": "HP", "lp": "LP", "gain_db": "Gain", "ta_ms": "TA",
                "polarity": "Polarity", "eq": "EQ bands", "eq_ptr": "EQ export",
                "status": "status", "tag": "Tag",
                "mute": "Mute", "off": "Off"}


_DIFF_RESERVED_KEYS = ("from", "to", "preset")


def _row_label(tier, ch):
    """`channels` rows stay bare (unchanged sheet format); any other tier is prefixed so a mixed
    proposal never reads as if two tiers shared one channel namespace."""
    return ch if tier == "channels" else f"{tier}:{ch}"


def settings_sheet(diff, rate, preset, version, slot_note=None):
    """The compact 'APPLY THIS at the PC-Tool screen' table — only the changed fields, old→new,
    across EVERY tier the diff touched (schema v2 — a virtual-tier change used to be invisible here).

    This is the artifact the Arbiter keys in; ms is the source of truth, samples shown for the rate.
    Generated-only — it is a view of the diff, never edited by hand. `slot_note` (issue #5) stamps
    the header with the preset's active-slot status so the human never keys a change into the wrong slot.
    """
    header = f"## APPLY THIS in Helix PC-Tool — {preset} · {version} (proposed)"
    if slot_note:
        header += f" · {slot_note}"
    lines = [header,
             "Enter only these. ms is the source of truth; samples shown for the active rate.", "",
             "| Channel | Param | Old → New |", "|---|---|---|"]
    any_row = False
    for tier in sorted(k for k in diff if k not in _DIFF_RESERVED_KEYS):
        for ch, fields in diff[tier].items():
            label = _row_label(tier, ch)
            if fields.get("__added__"):
                lines.append(f"| {label} | — | ➕ NEW row — enable & set all params (see full sheet) |")
                any_row = True
                continue
            if fields.get("__removed__"):
                lines.append(f"| {label} | — | ➖ mute/remove row |")
                any_row = True
                continue
            for fld, (o, n) in fields.items():
                if fld == "status":
                    continue
                lines.append(f"| {label} | {_FIELD_LABEL.get(fld, fld)} | "
                             f"{_fmt_val(fld, o, rate)} → {_fmt_val(fld, n, rate)} |")
                any_row = True
    if not any_row:
        lines.append("| — | — | _(no hard-param changes)_ |")
    return "\n".join(lines)



def delta_rows(diff, rate):
    """The change, as rows, in the SAME words the settings sheet prints (SCR-026).

    The sheet is built from these; so is the front-end's card. Two renderers over one structure,
    rather than a front-end diffing two snapshots and guessing at intent -- a `gain_db` that moved
    could be a level-match trim or a banked decision, and the snapshots do not say which.
    """
    rows = []
    for tier in sorted(k for k in diff if k not in _DIFF_RESERVED_KEYS):
        for ch, fields in diff[tier].items():
            if fields.get("__added__"):
                rows.append({"tier": tier, "channel": ch, "param": None,
                             "was": None, "value": None, "added": True})
                continue
            if fields.get("__removed__"):
                rows.append({"tier": tier, "channel": ch, "param": None,
                             "was": None, "value": None, "removed": True})
                continue
            for fld, (o, n) in fields.items():
                if fld == "status":
                    continue
                rows.append({
                    "tier": tier, "channel": ch,
                    "param": _FIELD_LABEL.get(fld, fld), "field": fld,
                    # Rendered, not raw: these are the values the Arbiter keys in, and the sheet's
                    # own formatter is what turns 620.0 into "620 Hz LR36" and ms into samples.
                    "was": _fmt_val(fld, o, rate), "value": _fmt_val(fld, n, rate),
                    "was_raw": o, "value_raw": n,
                })
    return rows


def write_delta(history, diff, rate, version, note=None, advisories=()):
    """Bank the change beside the snapshot: `<preset>/proposals/<v_NNN>.json` (SCR-026).

    The ledger stores the state AFTER a change; the Arbiter's sheet is about the change itself, and
    the skill computed it, printed it and threw it away. Retyping numbers into chat is a
    transcription surface with no gate on it -- the same argument as `dsp-state-current` being
    generated rather than hand-written, applied to the sheet.

    Best effort by design: a proposal that is banked but whose delta file could not be written must
    not fail the proposal. The snapshot is the source of truth; this is a view.
    """
    out = {
        "schema_version": _state.SCHEMA_VERSION,
        "version": version,
        "from": diff.get("from"),
        "preset": history.preset,
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": note,
        "preset_changes": diff.get("preset") or {},
        "settings": delta_rows(diff, rate),
        "advisories": list(advisories or ()),
    }
    path = os.path.join(history.dir, "proposals", f"{version}.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except OSError:
        return None
    return path


def propose(history, delta, note=None, provenance=None, registry=None, allow_nonactive=False):
    """Gate: validate the delta against current HEAD, bank a 🟡 proposed snapshot, return the sheet.

    Returns {version, sheet, full_render, diff, advisories}. Raises ValueError on a deterministic
    refusal (the state is NOT banked on refusal — a garbage change can't slip through).

    Multi-slot integrity (issue #5): if `registry` is given and an active slot is set, REFUSE a
    proposal aimed at a different preset (the cross-slot anchoring trap — tuning Slot 3 off Slot 2's
    baseline), unless `allow_nonactive=True`. The settings sheet is stamped with the slot status."""
    slot_note = None
    if registry is not None:
        active = registry.get_active()
        if active is not None:
            if history.preset != active and not allow_nonactive:
                raise ValueError(
                    f"⛔ SLOT MISMATCH — proposing to preset {history.preset!r} but the ACTIVE slot "
                    f"in the DSP is {active!r}. This is the issue-#5 cross-slot anchoring trap. Either "
                    f"`registry set-active {history.preset}` (if you really switched slots) or pass "
                    f"allow_nonactive=True for a deliberate off-slot edit.")
            slot_note = ("ACTIVE SLOT ✅" if history.preset == active
                         else f"⚠️ NON-ACTIVE SLOT (active={active})")
    current = history.load()  # read-before-edit (raises if no baseline — seed via history.snapshot first)
    proposed = apply_delta(current, delta)          # deterministic refusals fire here
    if provenance is not None:
        proposed["provenance"] = provenance
    d = _state.diff_states(current, proposed)        # note current has no version yet in-memory
    adv = advisories(current, proposed)
    version = history.snapshot(proposed, note=note or "proposed change")   # validates again + versions
    rate = proposed["sample_rate"]
    sheet = settings_sheet({**d, "to": version}, rate, history.preset, version, slot_note=slot_note)
    write_delta(history, {**d, "to": version}, rate, version, note=note, advisories=adv)
    if adv:
        sheet += "\n\n⚠️ **Advisories (double-check, not blocking):**\n" + "\n".join("- " + a for a in adv)
    sheet += (f"\n\nAfter entering these in Helix, run `attest {version}` to bank it 🟢 applied, "
              f"then take a control measurement (→ 📏 measured).")
    return {"version": version, "sheet": sheet, "full_render": history.render(version),
            "diff": d, "advisories": adv}


def attest(history, version=None, note=None):
    """Arbiter confirms the proposed change was entered in Helix → flip its rows 🟡→🟢 applied,
    across EVERY tier (schema v2 — a virtual-tier row left 🟡 forever was the bug before this).

    Banks a new snapshot (immutable audit trail: proposed at v_N, applied at v_N+1). Attested =
    INTENT, not a device mirror — device-truth remains the latest measurement.
    """
    version = version or history.head()
    s = history.load(version)
    flipped = []
    for tier in _state.tier_names(s):
        for ch, c in (s.get(tier) or {}).items():
            if c.get("status") == "proposed":
                c["status"] = "applied"
                flipped.append(ch if tier == "channels" else f"{tier}:{ch}")
    v = history.snapshot(s, note=note or f"attested applied ({', '.join(flipped) or 'no proposed rows'})")
    return {"version": v, "applied_channels": flipped}


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest():
    import tempfile
    root = tempfile.mkdtemp(prefix="autosound_apply_")
    h = _state.PresetHistory(root, "SQ_Jazzi")
    h.snapshot(_state._sample_state(), note="baseline")   # seed HEAD (all applied)

    # propose a delta: w-L gain + TA, sub polarity flip.
    r = propose(h, {"w-L": {"gain_db": -7.5, "ta_ms": 5.45}, "sub": {"polarity": "INV"}},
                note="sub INV test + w-L trim")
    assert r["version"] == "v_002", r["version"]
    # settings sheet carries old→new with derived samples and the polarity flip.
    assert "5.38 ms (516 smp) → 5.45 ms (523 smp)" in r["sheet"], r["sheet"]
    assert "-7.8 dB → -7.5 dB" in r["sheet"]
    assert "NORM → INV" in r["sheet"]
    # polarity flip raised a (non-blocking) advisory.
    assert any("polarity" in a for a in r["advisories"]), r["advisories"]
    # the banked snapshot marks exactly the touched channels proposed; others stay applied.
    s2 = h.load("v_002")
    assert s2["channels"]["w-L"]["status"] == "proposed"
    assert s2["channels"]["sub"]["status"] == "proposed"
    assert s2["channels"]["tw-R"]["status"] == "applied", "untouched channel must stay applied"

    # attest → flips proposed→applied in a new snapshot.
    a = attest(h, "v_002")
    assert a["version"] == "v_003" and set(a["applied_channels"]) == {"w-L", "sub"}, a
    s3 = h.load("v_003")
    assert all(s3["channels"][c]["status"] == "applied" for c in ("w-L", "sub", "tw-R"))

    # ── virtual tier (schema v2): a TIER-KEYED delta addresses a tier other than `channels` ──
    # this is the thing the gate literally could not do before schema v2 -- a virtual-channel
    # change had nowhere to be proposed, so it could never be banked or attested.
    r_v = propose(h, {"virtual_channels": {"VFL": {"gain_db": -1.0}}}, note="VFL trim")
    assert h.load(r_v["version"])["virtual_channels"]["VFL"]["status"] == "proposed"
    assert "virtual_channels:VFL" in r_v["sheet"], r_v["sheet"]
    assert "0 dB → -1 dB" in r_v["sheet"], r_v["sheet"]
    a_v = attest(h, r_v["version"])
    assert "virtual_channels:VFL" in a_v["applied_channels"], a_v
    assert h.load(a_v["version"])["virtual_channels"]["VFL"]["status"] == "applied"

    # DETERMINISTIC REFUSALS — and none of them bank a snapshot.
    n_before = len(h.versions())
    for bad, why in [
        ({"w-L": {"gaindb": -7}}, "unknown field (typo gaindb)"),
        ({"w-L": {"ta_samples": 520}}, "TA as samples not ms"),
        ({"c": {"gain_db": -9}}, "partial edit of a non-existent channel"),
        ({"virtual_channels": {"VFL": {"gaindb": -1}}}, "unknown field, non-`channels` tier"),
    ]:
        try:
            propose(h, bad)
            raise AssertionError(f"gate accepted bad delta: {why}")
        except ValueError:
            pass
    assert len(h.versions()) == n_before, "a refused delta must NOT bank a snapshot"

    # adding a NEW full channel is allowed (enabling center).
    full_c = {"c": {"hp": {"f": 400, "type": "LR", "slope": 24},
                    "lp": {"f": 1200, "type": "LR", "slope": 24}, "gain_db": -9.0,
                    "ta_ms": 6.0, "polarity": "NORM", "eq_ptr": {}}}
    rc = propose(h, full_c, note="enable center")
    assert h.load(rc["version"])["channels"]["c"]["status"] == "proposed"
    assert "NEW row" in rc["sheet"]

    # ── identity is NOT proposable through the ledger any more (schema v3, SCR-001) ──
    # A driver's name/slot/role is a project fact; routing it through a tuning delta would bank it
    # into a snapshot, which is the two-homes-for-one-fact problem v3 removes. `project.py
    # set-channel` is where these go now.
    try:
        propose(h, {"c": {"role": "center", "descr": "Front Center Full"}}, note="identity")
        raise AssertionError("propose accepted identity fields")
    except ValueError as exc:
        assert "unknown field" in str(exc), exc

    # tuning fields on the same row still merge fine, including structured EQ bands.
    ann = propose(h, {"c": {"eq": [{"type": "PK", "f": 1000, "gain_db": -9, "q": 2},
                                   {"type": "PK", "f": 1450, "gain_db": -9, "q": 2}]}},
                  note="center EQ")
    c_after = h.load(ann["version"])["channels"]["c"]
    assert c_after["eq"][0]["type"] == "PK" and c_after["eq"][0]["f"] == 1000, c_after
    # the sheet is what the human keys in, so EQ bands must read as bands -- not a Python dict/list repr.
    assert "PK 1000 -9 Q2 · PK 1450 -9 Q2" in ann["sheet"], ann["sheet"]
    assert "{'type'" not in ann["sheet"], ann["sheet"]

    # ── multi-slot slot-guard (issue #5): propose to a NON-active slot is refused, banks nothing ──
    reg = _state.Registry(root)
    h2 = _state.PresetHistory(root, "ResoNix")
    h2.snapshot(_state._sample_state(), note="resonix baseline")
    reg.set_active("ResoNix")                              # active slot = ResoNix; h is SQ_Jazzi
    n0 = len(h.versions())
    try:
        propose(h, {"w-L": {"gain_db": -7.0}}, registry=reg)
        raise AssertionError("gate accepted a proposal aimed at a non-active slot")
    except ValueError as e:
        assert "SLOT MISMATCH" in str(e), e
    assert len(h.versions()) == n0, "a slot-mismatch refusal must NOT bank a snapshot"
    # deliberate override banks + stamps NON-ACTIVE; on the active slot the sheet stamps ACTIVE.
    r_over = propose(h, {"w-L": {"gain_db": -7.0}}, registry=reg, allow_nonactive=True)
    assert "NON-ACTIVE SLOT" in r_over["sheet"], r_over["sheet"]
    reg.set_active("SQ_Jazzi")
    r_act = propose(h, {"w-L": {"gain_db": -7.1}}, registry=reg)
    assert "ACTIVE SLOT ✅" in r_act["sheet"], r_act["sheet"]

    print(f"selftest OK — propose banked 🟡 + settings-sheet (old→new, 5.45 ms=523 smp@96k), "
          f"advisory on polarity flip, attest flipped 🟡→🟢 (w-L,sub); tier-keyed delta proposed+"
          f"attested a VIRTUAL-tier row (schema v2 — impossible before this), structured EQ bands "
          f"read as bands not a dict repr; 4 deterministic refusals banked nothing, new-channel add "
          f"allowed; slot-guard refused a non-active-slot propose (banked nothing) + stamped "
          f"ACTIVE/NON-ACTIVE. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
