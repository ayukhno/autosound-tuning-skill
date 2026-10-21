#!/usr/bin/env python3
"""One level base for the rounds of a project, instead of REW's absolute SPL calibration (#176, hub #285 TCC-060).

REW's SPL calibration is one constant per measurement, `splOffsetdB` on its listing record, and it moves for reasons
that have nothing to do with the car: REW 5.40 beta 135 reset it to 120.0 dB on 08.10, against 103.35 under beta 134
two days before, so every level of round cap_004 read 16.65 dB above cap_003 and the round check said nothing (PAS-015,
hub #268). The Arbiter's rule (08.10): do not chase the calibration -- bring the rounds to a common base. The bench did
it by hand in `car/passat-b8-2026-aya/scripts/levelbase.py`; this is that file, mirrored, not invented, with the base
made a parameter (the bench pinned cap_003's offset as a constant) and the control's verdict written down as a rule.
`analysis-playbook.md`'s «Level-normalize before comparing SHAPE» is the same idea said for one comparison.

Two steps, as the bench takes them:

1. **The shift** (`spl_shift`, `to_base`): every curve moves by its own offset's distance from the base round's. Exact
   for REW's own changes; blind to a turned input-gain knob or a swapped mic. **Only an SPL-calibrated reading moves**
   (Codex's plan review, the blocker): `splOffsetdB` is in REW's frequency response (`get_fr`, dB SPL) and in an RTA,
   and NOT in an impulse read as a fraction of full scale (`rew_api.get_impulse_response(normalised=False)`), so a
   reader of impulses -- `predict --rew`, `verify_prediction`'s sweep path -- is never shifted: shifting it would
   invent a residual.
2. **The control** (`band_offsets`, `chain_change`): one capture of the same state at the same volume in every round
   (the bench's `ALL+C+FX_N (rta)`; the method's round control, `process.py capture-start`). After step 1 it should
   sit on the base round's control, in every band the round did not change, within the day-to-day spread
   (`DAILY_SPREAD_DB`); a common remainder over the bands the round did not change is the chain changing (the gain
   knob, the mic) and is aligned on THOSE bands -- aligning inside what the round changed erases the change being
   measured. Which bands a round changed is read off the ledger (`changed_bands`, the diff between the two rounds'
   versions); a diff that cannot be read leaves the verdict unattributed, never a chain change.

The offset arithmetic is stdlib; numpy is imported where the curves are read (`band_offset`), so a reader of offsets
alone (`process.py capture-check`'s `level_base`) needs nothing more than the method's own code.

    python3 rew_tool/levelbase.py --selftest
"""
from __future__ import annotations

import math
import os
import sys

#: The bands the control is read in, Hz -- the bench's `CONTROL_BANDS`. A round names the one it changed and the
#: verdict is read on the others.
CONTROL_BANDS = {"low": (125.0, 500.0), "mid": (560.0, 1000.0), "presence": (1600.0, 3150.0),
                 "top": (4000.0, 10000.0)}
#: The cells a band is read in: 1/6 octave, each a power mean over ±1/12 octave around its centre (the bench's
#: `_band_db(f, m, fc, 1/6)`).
CELL_OCT = 1.0 / 6.0
#: The day-to-day spread of one control taken twice, dB: the bench measured 0.5-0.7, and this is its upper end. Over
#: it, a common remainder is the chain; under it, the same chain.
DAILY_SPREAD_DB = 0.7
#: How far one band's own 1/6-octave cells may scatter about its mean and still be read as one number, dB -- a
#: spread INSIDE a band, not the spread of band means `DAILY_SPREAD_DB` is (the re-review, #176). From the bench: the
#: 08.10 controls, read at 1/48, scattered 0.66-0.74 dB inside the bands the round did not change; about twice that.
IN_BAND_SPREAD_LIMIT_DB = 1.5
#: Two offsets closer than this are one offset (REW writes a float32: 103.34649658203125 is 103.35).
SAME_OFFSET_DB = 0.005

#: `chain_change`'s verdicts. `not_taken` is the caller's (the control was not measured), never this module's.
SAME_CHAIN, CHAIN_CHANGE, UNATTRIBUTED, NOT_TAKEN = "same_chain", "chain_change", "unattributed", "not_taken"


def _number(x):
    """`x` as a finite float, or None: a bool, a string, a NaN or an infinity is no offset."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def spl_shift(offset, base_offset):
    """dB to SUBTRACT from a reading at `offset` to put it on `base_offset`: their difference -- 0 when either is
    missing, since a reading REW gave no calibration for is moved by nothing (the bench's `spl_shift`)."""
    a, b = _number(offset), _number(base_offset)
    return 0.0 if a is None or b is None else a - b


def to_base(mag_db, shift):
    """The magnitudes `mag_db` (dB SPL, REW's FR or an RTA) brought to the base: `mag_db - shift`. A list comes back as
    a list and a numpy array as an array, so a stdlib caller stays stdlib."""
    if hasattr(mag_db, "dtype"):
        return mag_db - float(shift)
    return [float(m) - float(shift) for m in mag_db]


def round_offset(offsets):
    """`(offset, agree)` of one round from its captures' `{title: splOffsetdB}`: the offset they share, and whether
    every capture shares it. A round whose captures disagree (`mixed`) gives the offset most of them carry -- ties to
    the first listed -- so its other captures still have something to be measured against. `(None, True)` when no
    capture carries one."""
    values = [v for v in (_number(x) for x in (offsets or {}).values()) if v is not None]
    if not values:
        return None, True
    groups = []                               # [(representative, count)] in the order first seen
    for v in values:
        for i, (rep, n) in enumerate(groups):
            if abs(v - rep) <= SAME_OFFSET_DB:
                groups[i] = (rep, n + 1)
                break
        else:
            groups.append((v, 1))
    best = max(groups, key=lambda g: g[1])    # `max` keeps the first of equals: ties to the first listed
    return best[0], len(groups) == 1


def _band_db(f, m, fc, oct_):
    """Power mean of `m` (dB) over fc·2^(±oct_/2), or None with no bin there."""
    import numpy as np
    sel = (f >= fc * 2 ** (-oct_ / 2)) & (f <= fc * 2 ** (oct_ / 2)) & np.isfinite(m)
    if not sel.any():
        return None
    return 10 * math.log10(float(np.mean(10 ** (m[sel] / 10))))


def _centres(lo, hi, oct_):
    out, c = [], lo
    while c <= hi * 1.0001:
        out.append(c)
        c *= 2 ** oct_
    return out


def band_offset(f_cur, m_cur, f_ref, m_ref, lo, hi, oct_=CELL_OCT):
    """`(mean, spread)` of the cell-by-cell differences cur - ref over `lo`..`hi`: 1/6-octave cells, each a power mean
    in ±1/12 octave, the spread their rms about the mean (the bench's `band_offset`). `(None, None)` when no cell has
    bins on both curves -- a band nobody measured is no number."""
    import numpy as np
    fc_, mc_ = np.asarray(f_cur, float), np.asarray(m_cur, float)
    fr_, mr_ = np.asarray(f_ref, float), np.asarray(m_ref, float)
    d = []
    for c in _centres(lo, hi, oct_):
        a, b = _band_db(fc_, mc_, c, oct_), _band_db(fr_, mr_, c, oct_)
        if a is not None and b is not None:
            d.append(a - b)
    if not d:
        return None, None
    return float(np.mean(d)), float(np.std(d))


def band_offsets(f_cur, m_cur, f_ref, m_ref, bands=None):
    """`{band: (mean, spread)}` for every control band (`CONTROL_BANDS` unless given): the control's numbers, read
    after both curves are on the base."""
    return {k: band_offset(f_cur, m_cur, f_ref, m_ref, lo, hi) for k, (lo, hi) in (bands or CONTROL_BANDS).items()}


def chain_change(offsets, changed=(), spread_db=DAILY_SPREAD_DB):
    """The control's verdict from `band_offsets`' `offsets`, over the bands the round did not change.

    `changed` is the set of bands the round changed (`changed_bands`), or None when that could not be read. The rule
    (#176, the plan's T1): a chain change is named only when at least two bands survive -- not changed, and measured --
    and their means agree within `spread_db` (each within it of their common mean: the bench's 08.10 control, +0.45,
    +0.26 and -0.32 about +0.13, is one chain), and that common mean is itself over `spread_db`; then an alignment of
    -common on those bands is offered. Under it, with the bands agreeing, it is the same chain. A changed set that
    could not be read, fewer than two surviving bands, or bands that disagree: unattributed -- the difference is said,
    and no cause is named for it.

    Returns `{verdict, common_db, bands: {band: {mean_db, spread_db, used}}, why}`, with `align_db` on a chain change.
    """
    bands = {}
    for name, pair in (offsets or {}).items():
        mean, spread = pair if isinstance(pair, (tuple, list)) else (pair, None)
        mean, spread = _number(mean), _number(spread)
        used = changed is not None and name not in changed and mean is not None
        bands[name] = {"mean_db": None if mean is None else round(mean, 2),
                       "spread_db": None if spread is None else round(spread, 2), "used": used}
    # `reason`: why it is unattributed, as a code -- `changes_unread`, `too_few_bands` (structural: the record says
    # them), `disagree`, `spread_wide` (a real doubt about the reading: said) -- None on a verdict.
    out = {"verdict": UNATTRIBUTED, "common_db": None, "bands": bands, "why": None, "reason": None}
    if changed is None:
        out["why"], out["reason"] = "which bands the round changed could not be read off the ledger", "changes_unread"
        return out
    means = [_number((offsets[n] if isinstance(offsets[n], (tuple, list)) else (offsets[n],))[0])
             for n in bands if bands[n]["used"]]
    if len(means) < 2:
        out["why"] = (f"{len(means)} band(s) left outside what the round changed -- the rule needs two")
        out["reason"] = "too_few_bands"
        return out
    common = sum(means) / len(means)
    out["common_db"] = round(common, 2)
    far = max(abs(m - common) for m in means)
    # A used band whose own cells scatter over `IN_BAND_SPREAD_LIMIT_DB` is no number to name a chain on (the group
    # seats, #176): its mean is read, and the verdict is not.
    wide = [n for n in bands if bands[n]["used"] and (bands[n]["spread_db"] or 0.0) > IN_BAND_SPREAD_LIMIT_DB]
    if wide:
        out["why"] = (f"the spread within {', '.join(wide)} is over {IN_BAND_SPREAD_LIMIT_DB:g} dB -- no common "
                      "remainder to read")
        out["reason"] = "spread_wide"
        return out
    if far > spread_db:
        out["why"] = (f"the bands outside the round's change disagree: one sits {far:.2f} dB from their common mean, "
                      f"over the daily spread of {spread_db:g} dB")
        out["reason"] = "disagree"
        return out
    if abs(common) > spread_db:
        out.update(verdict=CHAIN_CHANGE, align_db=round(-common, 2),
                   why=f"a common {common:+.2f} dB over the daily spread of {spread_db:g} dB, in every band the round "
                       "did not change -- the chain (gain knob, mic)")
    else:
        out.update(verdict=SAME_CHAIN,
                   why=f"within the daily spread of {spread_db:g} dB in every band the round did not change")
    return out


# ── which bands a round changed, from the ledger's diff ──────────────────────────────────────────────────────────
#: How far a crossover's corner reaches either side, octaves: a corner typed an octave off shows up to an octave away
#: (verify_prediction's `NEAR_CORNER_OCTAVES`).
_CORNER_OCT = 1.0
#: A peaking band's reach either side of its centre is one bandwidth (from Q), never less than this, octaves.
_MIN_PK_OCT = 1.0 / 3.0
#: An all-pass turns phase around its frequency: what it moves is the summation there, read as a corner.
_APF_OCT = 1.0
#: The fields of a channel row whose change moves its whole passband: its level and whether it plays at all -- a
#: DSP gain left out of the changed bands would be read back as the chain changing, the one verdict that must not be
#: wrong -- and `eq_ptr`, the pointer to an EQ file whose bands the ledger does not carry.
_WHOLE_ROW = ("mute", "off", "gain_db", "eq_ptr", "ta_ms")
#: A delay (`ta_ms`) is with them (the group seats, #176): one side delayed moves the L/R comb across the whole shared
#: passband, not only where the channel meets its neighbour. The fields whose change moves the summation with the
#: neighbours only -- polarity and phase -- read where it overlaps them: each leg out to where it is ~12 dB below its
#: passband (`_leg_reach`); a channel with no corner at all (full range) is its whole passband. `tag` (which hardware
#: control moves it) and `status` (bookkeeping) move nothing.
_CORNER_ROW = ("polarity", "phase_deg")
#: How far down a leg must be before a change of its channel's time no longer moves the sum with a neighbour, dB.
_SUM_FLOOR_DB = 12.0
#: The least reach a leg is given, octaves; and the slope read for a leg whose slope the ledger does not give -- the
#: shallowest a crossover has, so the reach is the widest it could be.
_MIN_REACH_OCT, _SHALLOWEST_DB_OCT = 0.5, 6.0


def _leg_reach(leg):
    """Octaves either side of a leg's corner where its channel still sums with its neighbour (the re-review, #176):
    out to ~12 dB down, `_SUM_FLOOR_DB / slope` -- 1/2 octave for 24 dB/oct (the bench's LR24 centre), 1 for 12 (its
    BW12 rear at 460 Hz), 2 for 6 -- rounded up to the half octave, never below 1/2. A slope the ledger does not give
    (`slope`, or the digits of a `type` such as `LR24`) is read as 6 dB/oct, the widest reach: an uncertain reach
    leaves more bands out and the verdict unattributed, never a chain change named on a band the change touched."""
    slope = _number(leg.get("slope")) if isinstance(leg, dict) else None
    if slope is None and isinstance(leg, dict):
        digits = "".join(ch for ch in str(leg.get("type") or "") if ch.isdigit())
        slope = float(digits) if digits else None
    if slope is None or slope <= 0:
        slope = _SHALLOWEST_DB_OCT
    reach = max(_MIN_REACH_OCT, math.ceil(_SUM_FLOOR_DB / slope * 2 - 1e-9) / 2)
    # A Bessel leg rolls off slower near its corner (a BE12 is ~10 dB down an octave out): half an octave wider.
    if str(leg.get("type") if isinstance(leg, dict) else "").strip().upper().startswith("BE"):
        reach += 0.5
    return reach
#: Preset-level fields whose change moves every band: the rate reshapes every filter, the virtual tier's EQ file is
#: bands nobody listed.
_WHOLE_PRESET = ("sample_rate", "virtual_eq_ptr")


def _leg_f(leg):
    """A crossover leg's corner, Hz, or None: OFF, missing, or a dict typed OFF (`{"f": 80, "type": "OFF"}`, the
    group seats' finding) -- a corner nobody switched on is no corner."""
    if not isinstance(leg, dict) or str(leg.get("type") or "").strip().upper() == "OFF":
        return None
    return _number(leg.get("f"))


def _passband(row):
    """`(lo, hi)` Hz a channel row plays over: its high-pass to its low-pass, an octave past each corner; a leg that is
    OFF or missing is open (0 or infinity)."""
    row = row if isinstance(row, dict) else {}
    hp, lp = _leg_f(row.get("hp")), _leg_f(row.get("lp"))
    return (0.0 if hp is None else hp / 2 ** _CORNER_OCT), (math.inf if lp is None else lp * 2 ** _CORNER_OCT)


def _band_reach(band):
    """`(lo, hi)` Hz an EQ band object reaches (`state/schema.md`: `{type, f, gain_db, q}`), or None when it names no
    frequency -- then the caller cannot say what it changed."""
    if not isinstance(band, dict):
        return None
    f = _number(band.get("f"))
    if f is None or f <= 0:
        return None
    kind = str(band.get("type") or "").upper()
    if kind in ("LSH", "LS"):
        return 0.0, f * 2.0
    if kind in ("HSH", "HS"):
        return f / 2.0, math.inf
    if kind.startswith("APF"):
        return f / 2 ** _APF_OCT, f * 2 ** _APF_OCT
    q = _number(band.get("q"))
    # A peaking band's bandwidth in octaves from its Q (RBJ): N = 2/ln2 · asinh(1/(2Q)); its reach is one N each side.
    bw = (2 / math.log(2)) * math.asinh(1 / (2 * q)) if q and q > 0 else 2.0
    reach = max(bw, _MIN_PK_OCT)
    return f / 2 ** reach, f * 2 ** reach


def _eq_changes(old, new):
    """The ranges the bands that differ between two `eq` lists reach: every band that plays in one list and not the
    other, by value. A bypassed band plays nowhere: bypassed on both sides, added bypassed or removed bypassed it
    changes nothing, and switched on or off it is the band appearing or going (the task review, #176: the bench's v_012
    added three bands bypassed on VFL/VFR, and they took `presence` out of the control). None when a band that plays
    names no frequency."""
    old = [b for b in (old or []) if isinstance(b, dict) and b.get("bypass") is not True]
    new = [b for b in (new or []) if isinstance(b, dict) and b.get("bypass") is not True]
    out = []
    for b in [b for b in old if b not in new] + [b for b in new if b not in old]:
        reach = _band_reach(b)
        if reach is None:
            return None
        out.append(reach)
    return out


def _corner_move(leg, was, now):
    """`(lo, hi)` Hz a crossover leg moved from corner `was` to `now` reaches (None = OFF): the whole way between the
    two, an octave past each -- every frequency between them changed level, not only the octave around each (the task
    review, #176: LP 8000 -> 500 left `presence` untouched). An OFF side runs open: a low-pass switched on or off moves
    everything above its corner, a high-pass everything below. None when neither side has a corner."""
    if was is None and now is None:
        return None
    if was is None or now is None:
        f = was if now is None else now
        return (f / 2 ** _CORNER_OCT, math.inf) if leg == "lp" else (0.0, f * 2 ** _CORNER_OCT)
    return min(was, now) / 2 ** _CORNER_OCT, max(was, now) * 2 ** _CORNER_OCT


def _uniform_delay(diff, before, after):
    """Whether the diff shifts EVERY output by one and the same delay (the re-review, #176): the whole system later by
    the same time changes nothing a microphone hears -- no sum moves -- so it is no change. The outputs are the
    `channels` tier, two at least -- a tier of one row is never alike on its own (a lone centre +0.7 ms moved its
    passband) -- each carrying a delay on both sides and moving by the same amount, to a microsecond; and no other
    tier's delay moved, since a virtual row feeding some outputs and not others breaks the likeness."""
    for tier, rows in diff.items():
        if tier in ("from", "to", "preset", "channels") or not isinstance(rows, dict):
            continue
        if any(isinstance(f, dict) and "ta_ms" in f for f in rows.values()):
            return False
    rows = diff.get("channels") if isinstance(diff.get("channels"), dict) else {}
    was = (before or {}).get("channels") or {}
    now = (after or {}).get("channels") or {}
    both = [ch for ch in was if ch in now]
    if len(both) < 2:
        return False
    deltas = []
    for ch in both:
        pair = (rows.get(ch) or {}).get("ta_ms") if isinstance(rows.get(ch), dict) else None
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return False                              # a channel whose delay did not move: not alike
        a, b = _number(pair[0]), _number(pair[1])
        if a is None or b is None:
            return False
        deltas.append(b - a)
    return max(deltas) - min(deltas) <= 1e-3 and abs(deltas[0]) > 0


def changed_ranges(diff, before, after):
    """`[(lo, hi)]` Hz the change between two ledger snapshots reaches, from `state.diff_states(before, after)`; None
    when the diff cannot be read (not a diff, or a band with no frequency). What counts (#176, the plan's T1: "the
    bands under changed EQ filters and crossovers"): an EQ band added, removed or changed reaches its own span; a
    crossover leg moved reaches from the lower corner to the higher, an octave past each, and switched on or off it runs
    open on its side. A band bypassed on both sides changes nothing. Beside them, so that no change of the DSP is read
    back as the chain: a channel's level (gain, mute, off), its delay or its `eq_ptr` reaches its passband, as does a
    channel added or removed; its polarity or phase reaches either side of each corner as far as that leg sums with its
    neighbour (`_leg_reach`: ~12 dB down by its own slope), a channel with no corner its passband. A delay
    that moves every output by the same amount is no change (`_uniform_delay`). A preset's rate or virtual
    EQ file reaches everything."""
    if not isinstance(diff, dict) or not isinstance(diff.get("preset", {}), dict):
        return None
    if any(k in (diff.get("preset") or {}) for k in _WHOLE_PRESET):
        return [(0.0, math.inf)]
    out = []
    for tier, rows in diff.items():
        if tier in ("from", "to", "preset"):
            continue
        if not isinstance(rows, dict):
            return None
        uniform = tier == "channels" and _uniform_delay(diff, before, after)
        for ch, fields in rows.items():
            if not isinstance(fields, dict):
                return None
            if uniform and "ta_ms" in fields:
                fields = {k: v for k, v in fields.items() if k != "ta_ms"}   # every channel alike: no change
            was = ((before or {}).get(tier) or {}).get(ch)
            now = ((after or {}).get(tier) or {}).get(ch)
            if fields.get("__added__") or fields.get("__removed__"):
                out.append(_passband(now if fields.get("__added__") else was))
                continue
            if any(k in fields for k in _WHOLE_ROW):
                lo1, hi1 = _passband(was)
                lo2, hi2 = _passband(now)
                out.append((min(lo1, lo2), max(hi1, hi2)))
            if any(k in fields for k in _CORNER_ROW):
                for row in (was, now):
                    corners = [(row or {}).get(leg) for leg in ("hp", "lp")] if isinstance(row, dict) else []
                    corners = [side for side in corners if _leg_f(side) is not None]
                    if not corners:
                        out.append(_passband(row))     # full range: no corner to sum at but everywhere it plays
                    for side in corners:
                        f, reach = _leg_f(side), _leg_reach(side)
                        out.append((f / 2 ** reach, f * 2 ** reach))
            for leg in ("hp", "lp"):
                if leg in fields:
                    pair = fields[leg] if isinstance(fields[leg], (list, tuple)) and len(fields[leg]) == 2 else None
                    if pair is None:
                        return None
                    reach = _corner_move(leg, _leg_f(pair[0]), _leg_f(pair[1]))
                    if reach is not None:
                        out.append(reach)
            if "eq" in fields:
                pair = fields["eq"] if isinstance(fields["eq"], (list, tuple)) and len(fields["eq"]) == 2 else None
                if pair is None:
                    return None
                reach = _eq_changes(pair[0], pair[1])
                if reach is None:
                    return None
                out.extend(reach)
    return out


def changed_bands(diff, before, after, bands=None):
    """The control bands (`CONTROL_BANDS` unless given) the change between two snapshots reaches (`changed_ranges`),
    as a set of names; None when the diff cannot be read -- the control's verdict is then unattributed."""
    ranges = changed_ranges(diff, before, after)
    if ranges is None:
        return None
    return {name for name, (lo, hi) in (bands or CONTROL_BANDS).items()
            if any(r_lo <= hi and r_hi >= lo for r_lo, r_hi in ranges)}


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _selftest():
    """Against the bench's own numbers (08.10, `car/passat-b8-2026-aya`, cap_003 -> cap_004): the two judge controls
    `ALL+C+FX_3 (rta)` and `ALL+C+FX_4 (rta)` as REW listed them and read them at 1/48 (`testdata/rew/
    spl-reset-controls.json`), the shift +16.65 dB, the band numbers `cap004_check.py` printed, and the verdict on
    them; then the rule's edges, and which bands a ledger diff changes."""
    import json

    import numpy as np
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "testdata", "rew", "spl-reset-controls.json"), encoding="utf-8") as fh:
        recorded = json.load(fh)
    c3, c4 = recorded["107"], recorded["121"]
    assert (c3["title"], c4["title"]) == ("ALL+C+FX_3 (rta)", "ALL+C+FX_4 (rta)"), (c3["title"], c4["title"])
    # 1. The shift: cap_004 at 120.0 against cap_003 at 103.35 is 16.65 dB, subtracted.
    shift = spl_shift(c4["splOffsetdB"], c3["splOffsetdB"])
    assert round(shift, 2) == 16.65, shift
    assert spl_shift(None, 103.35) == 0.0 and spl_shift(120.0, None) == 0.0 and spl_shift(True, 1.0) == 0.0
    assert to_base([100.0, 116.65], shift)[1] - 100.0 < 1e-9 and isinstance(to_base([1.0], 0), list)
    assert round(float(to_base(np.asarray([116.65]), shift)[0]), 2) == 100.0
    # 2. The control after the shift, band by band -- cap004_check.py's section E printed these (mean/spread):
    #    low +0.45/0.74 · mid -0.89/1.50 · presence +0.26/0.66 · top -0.32/0.73.
    f3, m3 = np.asarray(c3["fr"][0]), np.asarray(c3["fr"][1])
    f4, m4 = np.asarray(c4["fr"][0]), to_base(np.asarray(c4["fr"][1]), shift)
    got = band_offsets(f4, m4, f3, m3)
    bench = {"low": (0.45, 0.74), "mid": (-0.89, 1.50), "presence": (0.26, 0.66), "top": (-0.32, 0.73)}
    for band, (mean, spread) in bench.items():
        assert abs(got[band][0] - mean) < 0.006 and abs(got[band][1] - spread) < 0.006, (band, got[band], mean)
    # ...and the verdict on them: cap_004 changed the centre (PK 710, 560-1000 -- `mid`); the other three agree about
    # +0.13 within the daily spread -- the same chain, as the bench concluded by hand ("±0.5 dB against 0.7").
    v = chain_change(got, changed={"mid"})
    assert v["verdict"] == SAME_CHAIN and abs(v["common_db"] - 0.13) < 0.01, v
    assert [b for b, r in v["bands"].items() if r["used"]] == ["low", "presence", "top"] and "align_db" not in v, v
    # Unshifted, the same two controls read 16.65 dB apart everywhere: a chain change the size of REW's reset -- the
    # number the round check let through without a word (PAS-015).
    raw = chain_change(band_offsets(f4, np.asarray(c4["fr"][1]), f3, m3), changed={"mid"})
    assert raw["verdict"] == CHAIN_CHANGE and abs(raw["common_db"] - 16.78) < 0.02, raw
    # 3. The rule's edges. A uniform +1.2 dB is a chain change, the alignment offered on the bands that carry it.
    uniform = {b: (1.2, 0.3) for b in CONTROL_BANDS}
    cc = chain_change(uniform, changed=set())
    assert cc["verdict"] == CHAIN_CHANGE and cc["common_db"] == 1.2 and cc["align_db"] == -1.2, cc
    #    The band the round changed is left out, whatever it reads.
    cc2 = chain_change(dict(uniform, mid=(-6.0, 2.0)), changed={"mid"})
    assert cc2["verdict"] == CHAIN_CHANGE and cc2["bands"]["mid"]["used"] is False and cc2["common_db"] == 1.2, cc2
    #    Fewer than two bands left -> unattributed; so is a changed set nobody could read.
    one = chain_change(uniform, changed={"low", "mid", "presence"})
    assert one["verdict"] == UNATTRIBUTED and one["common_db"] is None and "two" in one["why"], one
    none_left = chain_change(uniform, changed=set(CONTROL_BANDS))
    assert none_left["verdict"] == UNATTRIBUTED, none_left
    unread = chain_change(uniform, changed=None)
    assert unread["verdict"] == UNATTRIBUTED and not any(r["used"] for r in unread["bands"].values()), unread
    #    Bands that disagree -> unattributed, never a chain change: +2.0 low beside -1.0 top is no one cause.
    mixed = chain_change({"low": (2.0, 0.4), "mid": (0.1, 0.4), "presence": (0.4, 0.4), "top": (-1.0, 0.4)},
                         changed=set())
    assert mixed["verdict"] == UNATTRIBUTED and "disagree" in mixed["why"], mixed
    #    A band nobody measured is not a band: it is not used.
    sparse = chain_change({"low": (None, None), "mid": (1.2, 0.1), "presence": (1.3, 0.1), "top": (1.1, 0.1)},
                          changed=set())
    assert sparse["verdict"] == CHAIN_CHANGE and sparse["bands"]["low"]["used"] is False, sparse
    # 4. One round's offset: shared, or the most common with `agree` False.
    assert round_offset({"a": 103.34649658203125, "b": 103.35}) == (103.34649658203125, True)
    assert round_offset({"a": 120.0, "b": 103.35, "c": 120.0}) == (120.0, False)
    assert round_offset({"a": None}) == (None, True) and round_offset({}) == (None, True)
    # 5. The bands a ledger diff changes. The bench's own change, a PK at 710 Hz Q2.5 deeper: its reach is one
    #    bandwidth (0.57 oct) each side, 480-1060 Hz, so it touches `low`'s top (125-500) as well as `mid` -- both left
    #    out; a narrow PK at 800 Hz Q6 stays inside `mid`.
    before = {"channels": {"c": {"hp": {"f": 200, "type": "LR", "slope": 24}, "lp": {"f": 4000}, "gain_db": 0,
                                 "eq": [{"type": "PK", "f": 710, "gain_db": -1.0, "q": 2.5}]},
                           "w-L": {"hp": None, "lp": {"f": 300}, "gain_db": 0, "eq": []}}}
    after = json.loads(json.dumps(before))
    after["channels"]["c"]["eq"] = [{"type": "PK", "f": 710, "gain_db": -2.5, "q": 2.5}]
    diff = {"from": "v_008", "to": "v_012", "preset": {}, "channels": {"c": {"eq": [before["channels"]["c"]["eq"],
                                                                                    after["channels"]["c"]["eq"]]}}}
    assert changed_bands(diff, before, after) == {"low", "mid"}, changed_bands(diff, before, after)
    narrow = json.loads(json.dumps(diff))
    narrow["channels"]["c"]["eq"] = [[], [{"type": "PK", "f": 800, "gain_db": -2.0, "q": 6.0}]]
    assert changed_bands(narrow, before, after) == {"mid"}, changed_bands(narrow, before, after)
    #    A crossover moved: from the lower corner to the higher, an octave past each -- 125-600 Hz.
    xo = {"preset": {}, "channels": {"w-L": {"lp": [{"f": 300}, {"f": 250}]}}}
    assert changed_bands(xo, before, after) == {"low", "mid"}, changed_bands(xo, before, after)
    #    A channel's gain: its passband, here the woofer up to 300 Hz and an octave past it.
    gain = {"preset": {}, "channels": {"w-L": {"gain_db": [0, -1.5]}}}
    assert changed_bands(gain, before, before) == {"low", "mid"}, changed_bands(gain, before, before)
    #    The centre's polarity flipped: its HP 200 LR24 reaches half an octave, 141-283 Hz (low); its LP 4000 names no
    #    slope, so it is read as 6 dB/oct and reaches two, 1-16 kHz (mid, presence, top) -- the widest it could be.
    flip = {"preset": {}, "channels": {"c": {"polarity": ["NORM", "INV"]}}}
    assert changed_bands(flip, before, before) == set(CONTROL_BANDS), changed_bands(flip, before, before)
    sloped = json.loads(json.dumps(before))
    sloped["channels"]["c"]["lp"] = {"f": 4000, "type": "LR", "slope": 24}
    #    ...and with its slope given, LR24, half an octave: 2.8-5.7 kHz (presence, top); `mid` between the corners is
    #    the centre playing alone, not where the flip sums.
    assert changed_bands(flip, sloped, sloped) == {"low", "presence", "top"}, changed_bands(flip, sloped, sloped)
    #    `status` and `tag` move nothing.
    assert changed_bands({"preset": {}, "channels": {"c": {"status": ["proposed", "applied"]}}}, before, before) == set()
    #    Nothing changed: no band. The rate, or a band with no frequency: everything / unreadable.
    assert changed_bands({"preset": {}, "channels": {}}, before, before) == set()
    assert changed_bands({"preset": {"sample_rate": [48000, 96000]}, "channels": {}}, before, before) \
        == set(CONTROL_BANDS)
    bad = {"preset": {}, "channels": {"c": {"eq": [[], [{"type": "PK", "gain_db": 1}]]}}}
    assert changed_bands(bad, before, before) is None and changed_bands("no diff", None, None) is None
    # 6. A crossover moved reaches the whole way between its two corners, an octave past each, and an OFF side runs
    #    open (the task review, #176): LP 8000 -> 500 reaches presence; LP OFF -> 1500 reaches top; HP 2000 -> OFF low.
    for leg, pair, must in (("lp", [{"f": 8000}, {"f": 500}], {"low", "mid", "presence", "top"}),
                            ("lp", ["OFF", {"f": 1500}], {"mid", "presence", "top"}),
                            ("hp", [{"f": 2000}, "OFF"], {"low", "mid", "presence", "top"})):
        got_x = changed_bands({"preset": {}, "channels": {"w-L": {leg: pair}}}, before, after)
        assert got_x == must, (leg, pair, got_x)
    # 7. A band bypassed on both sides, or added or removed bypassed, changes nothing; one switched on does.
    byp = {"type": "PK", "f": 3000, "gain_db": -3.0, "q": 1.0, "bypass": True}
    on = dict(byp, bypass=False)
    for old_eq, new_eq, must in (([byp], [dict(byp, gain_db=-6.0)], set()), ([], [byp], set()), ([byp], [], set()),
                                 ([byp], [on], {"presence", "top"})):
        got_b = changed_bands({"preset": {}, "channels": {"c": {"eq": [old_eq, new_eq]}}}, before, after)
        assert got_b == must, (old_eq, new_eq, got_b)
    # 9. A polarity or phase change reaches as far as the channel's own legs sum with their neighbours: the
    #    octave distance at which each leg is ~12 dB down -- 1/2 oct for 24 dB/oct, 1 for 12, 2 for 6 or a slope not
    #    given (the re-review, #176). The bench's rear: HP 460 BW12, LP 4000 LR12 -- 230-920 Hz and 2-8 kHz.
    assert _leg_reach({"f": 560, "type": "LR", "slope": 24}) == 0.5 and _leg_reach({"f": 460, "type": "BW",
                                                                                     "slope": 12}) == 1.0
    assert _leg_reach({"f": 460, "type": "BW", "slope": 18}) == 1.0 and _leg_reach({"f": 460, "type": "BW"}) == 2.0
    assert _leg_reach({"f": 460, "type": "LR24"}) == 0.5 and _leg_reach({"f": 460, "slope": 6}) == 2.0
    rear = {"channels": {"r-L": {"hp": {"f": 460, "type": "BW", "slope": 12},
                                 "lp": {"f": 4000, "type": "LR", "slope": 12}, "ta_ms": 1.0}}}
    rear_ta = {"preset": {}, "channels": {"r-L": {"polarity": ["NORM", "INV"]}}}
    assert changed_bands(rear_ta, rear, rear) == {"low", "mid", "presence", "top"}, changed_bands(rear_ta, rear, rear)
    lr24 = {"channels": {"c": {"hp": {"f": 1414, "type": "LR", "slope": 24}, "lp": None, "ta_ms": 1.0}}}
    c_ta = {"preset": {}, "channels": {"c": {"polarity": ["NORM", "INV"]}}}
    reach_c = changed_ranges(c_ta, lr24, lr24)
    assert all(abs(lo - 1414 / 2 ** 0.5) < 1e-6 and abs(hi - 1414 * 2 ** 0.5) < 1e-6 for lo, hi in reach_c), reach_c
    assert changed_bands(c_ta, lr24, lr24) == {"mid", "presence"}, changed_bands(c_ta, lr24, lr24)
    # 8. END TO END, the bench as built: its own ledger (v_008 under cap_003, v_012 under cap_004 --
    #    `testdata/rew/bench-ledger-v008-v012.json`) through `state.diff_states` and `changed_bands`, then its own two
    #    controls through `band_offsets` and `chain_change`. The bench's conclusion (08.10): the same chain.
    sys.path.insert(0, os.path.join(here, "state"))
    import state as _state
    with open(os.path.join(here, "testdata", "rew", "bench-ledger-v008-v012.json"), encoding="utf-8") as fh:
        ledger = json.load(fh)
    v8, v12 = ledger["v_008"], ledger["v_012"]
    bench_changed = changed_bands(_state.diff_states(v8, v12), v8, v12)
    e2e = chain_change(got, changed=bench_changed)
    # What the rule gives (the group seats' fix, #176): v_012 moved the centre's delay 1.8 -> 2.5 ms -- a delay moves
    # the sum over the channel's whole passband (HP 560 .. LP 1000, an octave past each: 280-2000 Hz), low, mid and
    # presence -- and flipped its polarity INV -> NORM, which alone reaches its corners' overlap, low and mid. One band
    # is left, top (-0.32); the rule needs two, so the verdict is unattributed -- the conservative answer when a change
    # reaches that far, against the bench's own same chain by hand. Not tuned to agree.
    assert bench_changed == {"low", "mid", "presence"}, bench_changed
    assert e2e["verdict"] == UNATTRIBUTED and e2e["reason"] == "too_few_bands" and "1 band(s)" in e2e["why"], e2e
    # 13. A delay shift by the same amount on every channel changes nothing acoustically (the re-review, #176): read
    #     as no change. Band counts left on the bench's own layout (v_012), +0.1 ms: one tweeter, the sub, all
    #     channels alike, one mid.
    def plus(chs):
        return {"preset": {}, "channels": {c: {"ta_ms": [v12["channels"][c].get("ta_ms") or 0.0,
                                                        (v12["channels"][c].get("ta_ms") or 0.0) + 0.1]}
                                           for c in chs}}
    left = {what: len(set(CONTROL_BANDS) - changed_bands(plus(chs), v12, v12))
            for what, chs in (("tweeter", ["tw-L"]), ("sub", ["sw"]), ("all", list(v12["channels"])),
                              ("mid", ["m-L"]))}
    # By hand: tw-L HP 3000 BW24, no LP -> passband 1500 Hz up -> presence (1600-3150) and top: low, mid left (2). sw
    # no HP, LP 80 LR24 -> 0-160 Hz -> low (125-500): mid, presence, top left (3). m-L HP 280 / LP 2500 -> 140-5000 Hz
    # -> all four: none left (0). Every output alike -> no change: all four left.
    assert left == {"tweeter": 2, "sub": 3, "all": 4, "mid": 0}, left
    uneven = plus(list(v12["channels"]))
    uneven["channels"]["sw"]["ta_ms"][1] += 0.05
    assert changed_bands(uneven, v12, v12) == set(CONTROL_BANDS), "not alike: every channel's passband"
    # 13b. "Alike" is every OUTPUT (the channels tier), two at least, and no other tier's delay moved (the re-review,
    #      #176): a tier of one row is never alike on its own -- a lone centre +0.7 ms, a lone virtual VC 0 -> 0.5 ms
    #      moved its passband -- and a virtual row moved beside the outputs breaks it. A flip or a mute beside a
    #      uniform shift still counts.
    lone_c = {"channels": {"c": {"hp": {"f": 560, "type": "LR", "slope": 24},
                                 "lp": {"f": 1000, "type": "LR", "slope": 24}, "ta_ms": 1.8}}}
    assert changed_bands({"preset": {}, "channels": {"c": {"ta_ms": [1.8, 2.5]}}}, lone_c, lone_c) == \
        {"low", "mid", "presence"}
    lone_v = dict(v12, virtual_channels={"VC": {"ta_ms": 0.0}})
    assert changed_bands({"preset": {}, "virtual_channels": {"VC": {"ta_ms": [0.0, 0.5]}}}, lone_v, lone_v) == \
        set(CONTROL_BANDS)
    outs_and_v = plus(list(v12["channels"]))
    outs_and_v["virtual_channels"] = {"VFL": {"ta_ms": [0.0, 0.1]}}
    assert changed_bands(outs_and_v, v12, v12) == set(CONTROL_BANDS), "a virtual delay beside the outputs"
    flip_too = plus(list(v12["channels"]))
    flip_too["channels"]["c"]["polarity"] = ["INV", "NORM"]
    assert changed_bands(flip_too, v12, v12) == {"low", "mid"}, changed_bands(flip_too, v12, v12)
    # 14. Each unattributed verdict names its reason, a code a reader can sort the real doubts by.
    assert chain_change(uniform, changed=None)["reason"] == "changes_unread"
    assert mixed["reason"] == "disagree" and cc["reason"] is None and chain_change(
        {"low": (1.2, 1.6), "top": (1.2, 0.3)}, changed=set())["reason"] == "spread_wide"
    assert IN_BAND_SPREAD_LIMIT_DB == 1.5 and chain_change({"low": (1.2, 1.5), "top": (1.2, 0.3)},
                                                           changed=set())["verdict"] == CHAIN_CHANGE
    # 10. Every branch of `changed_ranges`, the bands worked out by hand (the group test seat, #176). Rows: `w` a woofer
    #     HP 92 / LP 250 LR24 (passband 46-500: low); `t` a tweeter HP 5000 LR24, no LP (2500-inf: presence, top); `f`
    #     full range, both legs OFF (everything).
    rows = {"channels": {"w": {"hp": {"f": 92, "type": "LR", "slope": 24}, "lp": {"f": 250, "type": "LR", "slope": 24}},
                         "t": {"hp": {"f": 5000, "type": "LR", "slope": 24}, "lp": None},
                         "f": {"hp": "OFF", "lp": None}}}
    no_t = {"channels": {k: v for k, v in rows["channels"].items() if k != "t"}}
    no_w = {"channels": {k: v for k, v in rows["channels"].items() if k != "w"}}
    table = (  # (what, diff fields, before, after, the bands)
        ("t added", {"t": {"__added__": True}}, no_t, rows, {"presence", "top"}),
        ("w removed", {"w": {"__removed__": True}}, rows, no_w, {"low"}),
        ("w muted", {"w": {"mute": [False, True]}}, rows, rows, {"low"}),
        ("t off", {"t": {"off": [False, True]}}, rows, rows, {"presence", "top"}),
        ("w eq_ptr", {"w": {"eq_ptr": [None, "w.txt"]}}, rows, rows, {"low"}),
        ("LSH 200", {"w": {"eq": [[], [{"type": "LSH", "f": 200, "gain_db": 2}]]}}, rows, rows, {"low"}),
        ("HSH 6000", {"t": {"eq": [[], [{"type": "HSH", "f": 6000, "gain_db": 2}]]}}, rows, rows, {"presence", "top"}),
        ("APF1 700", {"w": {"eq": [[], [{"type": "APF1", "f": 700}]]}}, rows, rows, {"low", "mid"}),
        ("t phase", {"t": {"phase_deg": [0, 90]}}, rows, rows, {"top"}),
        ("t delay", {"t": {"ta_ms": [0.0, 0.3]}}, rows, rows, {"presence", "top"}),
        ("f polarity", {"f": {"polarity": ["NORM", "INV"]}}, rows, rows, set(CONTROL_BANDS)),
    )
    for what, fields, was, now, want in table:
        got_t = changed_bands({"preset": {}, "channels": fields}, was, now)
        assert got_t == want, (what, got_t, want)
    assert changed_bands({"preset": {"virtual_eq_ptr": [None, "v.txt"]}, "channels": {}}, rows, rows) == \
        set(CONTROL_BANDS)
    # 11. A leg typed OFF is no corner; a Bessel leg rolls off slower and reaches half an octave further.
    assert _leg_f({"f": 80, "type": "OFF"}) is None and _leg_f({"f": 80, "type": "LR"}) == 80.0
    assert _leg_reach({"f": 500, "type": "BE", "slope": 12}) == 1.5 and _leg_reach({"type": "BE24"}) == 1.0
    # 12. The boundaries: exactly the daily spread is still agreement, and a common mean of exactly it is the same
    #     chain; a used band whose own spread is over twice the daily spread is no number to name a chain on.
    edge = chain_change({"low": (1.4, 0.2), "top": (0.0, 0.2)}, changed=set())
    assert edge["verdict"] == SAME_CHAIN and edge["common_db"] == 0.7, edge
    over = chain_change({"low": (1.41, 0.2), "top": (0.0, 0.2)}, changed=set())
    assert over["verdict"] == UNATTRIBUTED and "disagree" in over["why"], over
    wide = chain_change({"low": (1.2, 1.6), "presence": (1.2, 0.3), "top": (1.2, 0.3)}, changed=set())
    assert wide["verdict"] == UNATTRIBUTED and "spread" in wide["why"], wide
    assert chain_change({"low": (1.2, 1.4), "presence": (1.2, 0.3)}, changed=set())["verdict"] == CHAIN_CHANGE
    assert round_offset({"a": 120.0, "b": 103.35}) == (120.0, False), "a tie goes to the first title"
    print("selftest[levelbase] OK -- the bench's 08.10 case: cap_004 at 120.0 against cap_003 at 103.35 is shifted "
          "16.65 dB; its judge control after the shift reads the bench's own band numbers (low +0.45, mid -0.89, "
          "presence +0.26, top -0.32) and, the centre's band left out, the same chain at +0.13 -- unshifted, a chain "
          "change of 16.78 dB; a uniform +1.2 dB is a chain change with -1.2 offered, fewer than two bands left, an "
          "unreadable change and bands that disagree are unattributed; a round's one offset or its most common; and "
          "the bands an EQ band, a crossover, a channel's gain and the rate change, a band with no frequency unread; the "
          "bench's own ledger end to end: the centre's delay reaches low, mid and presence, one band left -- "
          "unattributed; every branch of the diff, the reach by slope (Bessel wider, a leg typed OFF none), and the "
          "boundaries at exactly the daily spread")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("--selftest", "selftest"):
        sys.exit(_selftest())
    print(__doc__)
    sys.exit(2)
