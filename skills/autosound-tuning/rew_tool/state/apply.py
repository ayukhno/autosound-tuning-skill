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
"""

import copy

import state as _state

# advisory thresholds — voice, not veto
_GAIN_JUMP_DB = 6.0
_TA_JUMP_MS = 2.0
_XOVER_FACTOR = 1.5

_MERGEABLE = set(_state.CHANNEL_FIELDS)


def apply_delta(current, delta):
    """Merge a per-channel partial delta onto `current`, marking touched channels `proposed`.

    delta = {channel: {field: value, ...}}. Crossover legs (hp/lp) are replaced wholesale.
    Raises ValueError on the deterministic-refusal cases (typos, phantom channels, samples-not-ms).
    """
    proposed = copy.deepcopy(current)
    chans = proposed.setdefault("channels", {})
    for ch_name, fields in delta.items():
        if not isinstance(fields, dict):
            raise ValueError(f"delta[{ch_name!r}] must be an object of field→value")
        unknown = [f for f in fields if f not in _MERGEABLE]
        if unknown:
            if "ta_samples" in unknown or "ta_smp" in unknown:
                raise ValueError(f"{ch_name}: TA must be given as canonical `ta_ms`, not samples "
                                 f"(samples are derived at render for the active rate)")
            raise ValueError(f"{ch_name}: unknown field(s) {unknown} — valid: {sorted(_MERGEABLE)}")
        if ch_name not in chans:
            # a full channel dict may seed a NEW channel (enabling center/rear); a partial cannot.
            missing = [f for f in ("hp", "lp", "gain_db", "ta_ms", "polarity") if f not in fields]
            if missing:
                raise ValueError(f"{ch_name} is not in the current state — to add a channel give a "
                                 f"full definition (missing {missing}); a partial edit needs an "
                                 f"existing channel (typo?)")
            chans[ch_name] = {}
        chans[ch_name].update(fields)
        chans[ch_name]["status"] = "proposed"
    return proposed


def advisories(current, proposed):
    """Soft ⚠️ notes on the acoustic nouns — voice, waivable, never blocking."""
    out = []
    cch, pch = current.get("channels", {}), proposed["channels"]
    for ch in sorted(set(cch) & set(pch)):
        a, b = cch[ch], pch[ch]
        if isinstance(a.get("gain_db"), (int, float)) and isinstance(b.get("gain_db"), (int, float)):
            if abs(b["gain_db"] - a["gain_db"]) >= _GAIN_JUMP_DB:
                out.append(f"{ch}: gain jump {a['gain_db']:g}→{b['gain_db']:g} dB "
                           f"(≥{_GAIN_JUMP_DB:g}) — double-check it's intended.")
        if a.get("polarity") != b.get("polarity"):
            out.append(f"{ch}: polarity {a.get('polarity')}→{b.get('polarity')} — verify by "
                       f"SUMMATION, not by eye (a flip that helps one joint can wreck another).")
        if isinstance(a.get("ta_ms"), (int, float)) and isinstance(b.get("ta_ms"), (int, float)):
            if abs(b["ta_ms"] - a["ta_ms"]) >= _TA_JUMP_MS:
                out.append(f"{ch}: TA jump {a['ta_ms']:g}→{b['ta_ms']:g} ms (≥{_TA_JUMP_MS:g}) — big move.")
        for leg in ("hp", "lp"):
            fa, fb = a.get(leg), b.get(leg)
            if isinstance(fa, dict) and isinstance(fb, dict) and fa.get("f") and fb.get("f"):
                hi, lo = max(fa["f"], fb["f"]), min(fa["f"], fb["f"])
                if lo and hi / lo >= _XOVER_FACTOR:
                    out.append(f"{ch}: {leg.upper()} {fa['f']:g}→{fb['f']:g} Hz — large crossover move; "
                               f"re-check the joint phase/summation.")
    return out


def _fmt_val(field, val, rate):
    if field == "ta_ms" and isinstance(val, (int, float)):
        return f"{val:g} ms ({_state.samples_for(val, rate)} smp)"
    if field in ("hp", "lp"):
        return _state._fmt_filter(val)
    if field == "gain_db" and isinstance(val, (int, float)):
        return f"{val:g} dB"
    return str(val)


_FIELD_LABEL = {"hp": "HP", "lp": "LP", "gain_db": "Gain", "ta_ms": "TA",
                "polarity": "Polarity", "helix_ch": "Helix ch", "eq_ptr": "EQ", "status": "status"}


def settings_sheet(diff, rate, preset, version):
    """The compact 'APPLY THIS at the PC-Tool screen' table — only the changed fields, old→new.

    This is the artifact the Arbiter keys in; ms is the source of truth, samples shown for the rate.
    Generated-only — it is a view of the diff, never edited by hand.
    """
    lines = [f"## APPLY THIS in Helix PC-Tool — {preset} · {version} (proposed)",
             "Enter only these. ms is the source of truth; samples shown for the active rate.", "",
             "| Channel | Param | Old → New |", "|---|---|---|"]
    any_row = False
    for ch, fields in diff["channels"].items():
        if fields.get("__added__"):
            lines.append(f"| {ch} | — | ➕ NEW channel — enable & set all params (see full sheet) |")
            any_row = True
            continue
        if fields.get("__removed__"):
            lines.append(f"| {ch} | — | ➖ mute/remove channel |")
            any_row = True
            continue
        for fld, (o, n) in fields.items():
            if fld == "status":
                continue
            lines.append(f"| {ch} | {_FIELD_LABEL.get(fld, fld)} | "
                         f"{_fmt_val(fld, o, rate)} → {_fmt_val(fld, n, rate)} |")
            any_row = True
    if not any_row:
        lines.append("| — | — | _(no hard-param changes)_ |")
    return "\n".join(lines)


def propose(history, delta, note=None, provenance=None):
    """Gate: validate the delta against current HEAD, bank a 🟡 proposed snapshot, return the sheet.

    Returns {version, sheet, full_render, diff, advisories}. Raises ValueError on a deterministic
    refusal (the state is NOT banked on refusal — a garbage change can't slip through)."""
    current = history.load()  # read-before-edit (raises if no baseline — seed via history.snapshot first)
    proposed = apply_delta(current, delta)          # deterministic refusals fire here
    if provenance is not None:
        proposed["provenance"] = provenance
    d = _state.diff_states(current, proposed)        # note current has no version yet in-memory
    adv = advisories(current, proposed)
    version = history.snapshot(proposed, note=note or "proposed change")   # validates again + versions
    rate = proposed["sample_rate"]
    sheet = settings_sheet({**d, "to": version}, rate, history.preset, version)
    if adv:
        sheet += "\n\n⚠️ **Advisories (double-check, not blocking):**\n" + "\n".join("- " + a for a in adv)
    sheet += (f"\n\nAfter entering these in Helix, run `attest {version}` to bank it 🟢 applied, "
              f"then take a control measurement (→ 📏 measured).")
    return {"version": version, "sheet": sheet, "full_render": history.render(version),
            "diff": d, "advisories": adv}


def attest(history, version=None, note=None):
    """Arbiter confirms the proposed change was entered in Helix → flip its channels 🟡→🟢 applied.

    Banks a new snapshot (immutable audit trail: proposed at v_N, applied at v_N+1). Attested =
    INTENT, not a device mirror — device-truth remains the latest measurement.
    """
    version = version or history.head()
    s = history.load(version)
    flipped = [ch for ch, c in s["channels"].items() if c.get("status") == "proposed"]
    for ch in flipped:
        s["channels"][ch]["status"] = "applied"
    v = history.snapshot(s, note=note or f"attested applied ({', '.join(flipped) or 'no proposed channels'})")
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

    # DETERMINISTIC REFUSALS — and none of them bank a snapshot.
    n_before = len(h.versions())
    for bad, why in [
        ({"w-L": {"gaindb": -7}}, "unknown field (typo gaindb)"),
        ({"w-L": {"ta_samples": 520}}, "TA as samples not ms"),
        ({"c": {"gain_db": -9}}, "partial edit of a non-existent channel"),
    ]:
        try:
            propose(h, bad)
            raise AssertionError(f"gate accepted bad delta: {why}")
        except ValueError:
            pass
    assert len(h.versions()) == n_before, "a refused delta must NOT bank a snapshot"

    # adding a NEW full channel is allowed (enabling center).
    full_c = {"c": {"helix_ch": "B", "hp": {"f": 400, "type": "LR", "slope": 24},
                    "lp": {"f": 1200, "type": "LR", "slope": 24}, "gain_db": -9.0,
                    "ta_ms": 6.0, "polarity": "NORM", "eq_ptr": {}}}
    rc = propose(h, full_c, note="enable center")
    assert h.load(rc["version"])["channels"]["c"]["status"] == "proposed"
    assert "NEW channel" in rc["sheet"]

    print(f"selftest OK — propose banked 🟡 + settings-sheet (old→new, 5.45 ms=523 smp@96k), "
          f"advisory on polarity flip, attest flipped 🟡→🟢 (w-L,sub), 3 deterministic refusals "
          f"banked nothing, new-channel add allowed. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
