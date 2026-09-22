#!/usr/bin/env python3
"""eq_propose -- EQ as PACKAGES through the gates; never a curve fit to a target.

Phase 2.1 (the desk) and 3.3 (the car) had no command: every band was a decision made in
conversation. This makes the decision a package -- "yes" or "no" to a group of bands that belong
together, banked as ONE ledger version (one action to revert) -- and lets the tool do only what
a measurement can justify. The doctrine it codifies is already in the references
(`diagnostic-techniques.md` §2/§13 and the Q-ceiling rule, `analysis-playbook.md`,
`phase_2_eq.md` 2a, `estimator-scope.md`): a curve is TRUE at a certain width, and the width
decides what a deviation is.

  * broad (> 2/3 oct)             -> TONE: the pair moves toward the target, together, gently
  * medium (1/6..2/3 oct), a PEAK, present in every position (the ellipsoid), minimum-phase (the
    excess-phase gate), away from a junction (+-1 oct: that is the delay's business, 1.3),
    above Schroeder a peak only   -> a DRIVER RESONANCE: cut it, Q no narrower than the ceiling
  * narrow, or a dip, or moving   -> the POSITION, not the car: not a filter (listed, not proposed)

and what skews the stage is the L/R DIFFERENCE, not the distance from the target -- so the first
package makes left and right one shape (broadly), and only then does the pair go to the target.

Packages, in the order they are computed and decided, each read on the curves as the earlier
packages leave them. EQ is in TWO PARTS since 2026-09-17 (the user's order; docs/DESIGN-2026-09-17-
phase1-variants.md): the coarse per-driver part belongs to Phase 1 and goes in BEFORE the delays,
because a PEQ rotates phase and a delay computed without it is a delay redone after it; the rest
is Phase 2. `--part 1` / `--part 2` emit one part; `--part all` (the default) everything in order.
  part 1  `res:<group>`  resonances, one per driver group (sub+midbass / mids / tweeters), cuts only,
                         Q <= the measured ceiling (borrowed 6 when the ellipsoid is absent) (c14/c05, c08, c07)
  part 2  `lr:<pair>`    L/R shape, one per stereo pair (Ws, Ms, TWs): shelves / Q <= 1, cut the louder
                         side, until |L-R| <= 1 dB per 1/3 oct in 300-4000 Hz          (listen: c01, c02)
          `tone:<pair>`  the pair toward the target on the 1/3-oct macro scale, identically on both
                         sides, tolerance max(1 dB, 2 sigma(f)) from the ellipsoid           (c04)
Phase 2's later steps -- the junctions of each side, sub with mids, each side whole, everything,
the centre, the rear -- are read on the SUMS (`predict`, `verify_prediction`, the MMM in the car),
not proposed here. What this module does say is when a package's bands reach into a junction's
band (+-1 oct of its corner): `recheck_junctions` names the junction, and the delay there is
re-read (`predict --align`) before the package is banked -- otherwise the delays stay.

Budgets: <= 6 bands per channel, <= 6 dB per band, no boosts unless `--allow-boost` AND the
excess-phase gate allows. Every package carries WHY (which gates said yes) and a score before /
after on the scale where the curve is true (1/3-oct residual vs target, and L-R per band).

Where a channel PLAYS bounds everything it is given (skill #56 item 7): each channel's live band is
read on its own curve (within LIVE_BAND_DB of its passband level, anchored on its ledger corners),
a band outside it is dropped and named, and a pair's L/R -- its level offset included -- is read
only where both members play. Part 2 reads a series measured AS CONFIGURED, through the designed
crossovers: its magnitude is each channel's `(rta)` (the MMM, `phase_2_eq.md` 2a), its excess phase
the `(sw)`; a channel whose `(rta)` is missing refuses the run by name rather than falling back to
the sweep, and nothing in it is a baseline (#56 item 8).

    python3 rew_tool/eq_propose.py --project P --solos DIR [--ellipsoid DIR] [--route VFL=w-L,m-L,tw-L ...]
                                   --house curve.txt [--part 1|all] [--out DIR] [--accept lr:Ms,res:mid]
    python3 rew_tool/eq_propose.py --project P --rew --ver N [--process DIR] --house curve.txt --part 2 ...

Proposes; banks nothing. The delta files it writes are what `apply.propose` takes. The numbers
(tolerances, budgets, Schroeder 150-200 Hz, the borrowed Q 6) are the doctrine's starting values,
named as constants here so a later measurement can move them.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_STATE = os.path.join(_HERE, "state")
if _STATE not in sys.path:
    sys.path.insert(0, _STATE)

import curve_view  # noqa: E402
import dsp_math  # noqa: E402
import eq_gate  # noqa: E402
import predict as P  # noqa: E402
import target_bands  # noqa: E402

LR_BAND = (300.0, 4000.0)         # where the image lives (diagnostic §23/§6): L-R is judged here
LR_TOL_DB = 1.0                   # |L-R| per 1/3 oct: an ILD of ~1 dB already moves an image
TONE_TOL_DB = 1.0                 # floor of the target tolerance; max(1, 2 sigma) with an ellipsoid
SCHROEDER_HZ = 200.0              # a car's Schroeder frequency is ~150-200 Hz (DAGA 2010)
JUNCTION_EXCL_OCT = 1.0           # +-1 oct of a junction: the delay's business, not EQ's
LIVE_BAND_DB = 20.0               # a channel PLAYS where its 1/3-oct curve is within this of its
                                  # passband level -- the margin `_live` gives the target, now on the curve
RES_WIDTH = (1.0 / 6.0, 2.0 / 3.0)  # a resonance is a medium-width feature; narrower is the position
RES_TREND_FRAC = 1                  # ...read against a one-octave trend (1/3 absorbs a Q 4 hump)
MAX_BANDS_PER_CHANNEL = 6
MAX_CUT_DB = 6.0
MIN_PROMINENCE_DB = 2.0
Q_BORROWED = 6.0
EP_TRUST = (150.0, 4000.0)        # the excess-phase gate's calibrated band (estimator-scope.md)
LISTEN = {"lr": ["c01", "c02"], "res:low": ["c14", "c05"], "res:mid": ["c08"], "res:high": ["c07"],
          "tone": ["c04"]}
GROUP_OF_ROLE = {"sub": "low", "subwoofer": "low", "woofer": "low", "midbass": "low",
                 "midrange": "mid", "mid": "mid", "tweeter": "high", "tw": "high"}
GROUP_LABEL = {"low": "sub+midbass", "mid": "mids", "high": "tweeters"}


class ProposeError(ValueError):
    pass


# ---------------------------------------------------------------- helpers
def _db(h):
    return 20.0 * np.log10(np.abs(h) + 1e-12)


def _smooth(f, y, frac):
    view = curve_view.multiscale(f, y, (float(f[0]), float(f[-1])), macro_frac=frac, fine_frac=24)
    return np.interp(f, view["grid"], view["macro"])


def _third_bands(lo=20.0, hi=20000.0):
    edges = lo * 2.0 ** (np.arange(int(np.log2(hi / lo) * 3) + 1) / 3.0)
    return list(zip(edges[:-1], edges[1:]))


def band_dict(kind, f0, gain, q):
    """A `dsp_math` band tuple -> the ledger's dict (`state.EQ_TYPES` spells shelves LSH/HSH)."""
    kind = {"LS": "LSH", "HS": "HSH"}.get(kind, kind)
    return {"type": kind, "f": round(float(f0), 1), "gain_db": round(float(gain), 1), "q": round(float(q), 2)}


def band_tuple(b):
    kind = {"LSH": "LS", "HSH": "HS"}.get(b["type"], b["type"])
    return (kind, float(b["f"]), float(b.get("gain_db") or 0.0), float(b.get("q") or 0.71))


def excess_phase_from_ir(ir, fs):
    """(f_lin, mag_db, excess_phase_deg) of an impulse response: total phase minus the
    minimum phase implied by the magnitude (Hilbert of log-magnitude). A pure delay leaves a
    LINEAR excess term, which `eq_gate.analyze` removes as a constant group-delay baseline."""
    try:
        from scipy.signal import hilbert
    except ImportError:
        return None
    x = np.asarray(ir, dtype=float)
    n = x.size
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    logm = np.log(np.abs(X) + 1e-9)
    pad = len(logm) // 4
    ext = np.pad(logm, pad, mode="reflect")
    mp = -np.imag(hilbert(ext))[pad:-pad]
    excess = np.unwrap(np.angle(X)) - mp
    return f, 20.0 * np.log10(np.abs(X) + 1e-12), np.degrees(excess)


def gate_from_ir(ir, fs, trust=EP_TRUST):
    r = excess_phase_from_ir(ir, fs)
    if r is None:
        return None
    f, mag, ep = r
    m = (f >= 10.0)
    return eq_gate.ExcessPhaseGate(f[m], mag[m], ep[m], trust)


def gate_from_kept_ir(raw, trust=EP_TRUST):
    """The gate from an impulse `predict.load_solo_rew(..., keep_ir=True)` kept. REW's buffer starts
    about a second BEFORE t = 0 (`t0_s`, its `startTime`), so the record is rolled to put t = 0 at
    sample 0 first -- the convention of a v7 file, which `gate_from_ir` reads -- rather than handing
    the excess phase a second of pure delay to unwrap (`predict._spectrum_on_grid`, the same roll)."""
    x = np.asarray(raw["ir"], dtype=float)
    fs = int(raw["sample_rate"])
    k = int(round(-float(raw.get("t0_s") or 0.0) * fs))
    return gate_from_ir(np.roll(x, -k) if k else x, fs, trust)


# ---------------------------------------------------------------- inputs
def channel_targets(f, house, chains, roles, pairs_of):
    """Per-channel target on `f`: house - summation offset (stereo pairs) + the ledger's own
    crossover shape (exact family and slope, `dsp_math.xo_response`) + gain."""
    out = {}
    for code, ch in chains.items():
        if ch.get("muted") or ch.get("unmodellable"):
            continue
        t = np.array([house.at(float(v)) for v in f])
        if pairs_of.get(code):
            t = t - np.array([target_bands.summation_offset(float(v)) for v in f])
        for kind in ("hp", "lp"):
            leg = ch.get(kind)
            if leg:
                t = t + _db(dsp_math.xo_response(f, leg["f"], leg["slope"], kind, leg["type"]))
        out[code] = t + float(ch.get("gain_db") or 0.0)
    return out


def _absorbed_fraction(f, f0, q, trend_frac):
    """How much of a PEQ (f0, q) the trend smoothing absorbs at f0: smooth(PEQ)[f0] / PEQ[f0].

    The residual a feature leaves against a smoothed trend is the feature MINUS the part the
    smoothing kept, so a cut sized from the residual alone falls short by exactly that part (a
    Q 4 peak against a one-octave trend: a third of it; a +5 dB peak cut by 3.3 left 1.7 dB --
    path_check). Divide the residual by (1 - fraction) and the cut is the peak."""
    shape = _db(dsp_math.peq_response(f, "PK", f0, 6.0, q))
    sm = _smooth(f, shape, trend_frac)
    k = int(np.argmin(np.abs(f - f0)))
    return float(np.clip(sm[k] / max(shape[k], 1e-6), 0.0, 0.9))


def _live(target_db, margin_db=20.0):
    return target_db >= np.nanmax(target_db) - margin_db


def _junction_mask(f, code, joints):
    """True where EQ on `code` is NOT allowed: within +-JUNCTION_EXCL_OCT of any junction it belongs to."""
    excl = np.zeros(f.size, dtype=bool)
    for lo, hi, fc in joints:
        if code in (lo, hi):
            excl |= (f >= fc / 2 ** JUNCTION_EXCL_OCT) & (f <= fc * 2 ** JUNCTION_EXCL_OCT)
    return excl


def live_band(f, meas_db, chain=None, within_db=LIVE_BAND_DB):
    """`(lo_hz, hi_hz)` -- where this channel actually PLAYS, read on its own curve -- or None.

    Its passband level is the loudest point of its one-octave trend between its own ledger corners
    (the whole grid on a side with no corner); it plays wherever its 1/3-oct curve is within
    `within_db` of that level. Runs of such points that reach into the ledger's passband are ONE
    band -- a dip inside the channel's own crossovers does not cut it in two -- while past a corner
    only what is contiguous counts, so a bump two octaves into a stopband does not stretch it. A
    side with no corner is anchored at the loudest point instead, for the same reason.

    Why the curve and not only the target (`_live`): the target says where a channel SHOULD play,
    the curve says where it does, and a band is a statement about the curve. Nothing held a band to
    either before: the greedy fit places a band anywhere in the range it is handed -- the whole
    grid, for the tone package -- and `--part 2` came back with `tw-R PK 845.5 Hz -5.4 dB` where
    that tweeter was 31 dB below its own band, and with two woofers' L/R matched over 300-4000 Hz
    where both sat 43-46 dB down (skill #56 item 7)."""
    y = np.asarray(meas_db, dtype=float)
    macro = _smooth(f, y, 3)
    trend = _smooth(f, y, 1)
    hp, lp = (chain or {}).get("hp"), (chain or {}).get("lp")
    lo_c = float(hp["f"]) if hp else float(f[0])
    hi_c = float(lp["f"]) if lp else float(f[-1])
    span = (f >= lo_c) & (f <= hi_c)
    if not span.any():
        return None
    level = float(np.max(trend[span]))
    peak = float(f[span][int(np.argmax(trend[span]))])
    core = (f >= (lo_c if hp else peak)) & (f <= (hi_c if lp else peak))
    idx = np.flatnonzero(macro >= level - within_db)
    if idx.size == 0:
        return None
    cut = np.flatnonzero(np.diff(idx) > 1)
    runs = zip(np.r_[idx[0], idx[cut + 1]], np.r_[idx[cut], idx[-1]])
    runs = [(a, b) for a, b in runs if core[a:b + 1].any()]
    if not runs:
        return None
    return float(f[min(a for a, _ in runs)]), float(f[max(b for _, b in runs)])


def _in_band(f, band):
    if band is None:
        return np.zeros(f.size, dtype=bool)
    return (f >= band[0]) & (f <= band[1])


def _overlap(*bands):
    """The band every one of `bands` covers, or None -- one missing band means no overlap at all."""
    if not bands or any(b is None for b in bands):
        return None
    lo, hi = max(b[0] for b in bands), min(b[1] for b in bands)
    return (lo, hi) if lo < hi else None


def _hz(band):
    return f"{band[0]:.0f}-{band[1]:.0f} Hz" if band else "nowhere"


def _clamp_to_live(bands, live_bands, shared=None, whose=None):
    """`(kept, dropped)`: every band held inside the band its channel plays in, or dropped and named.

    The last word on a package, after whatever fit produced it -- a fit weighted on the live band
    can still centre a band outside it, where the skirt alone earns its keep (#56 item 7). `shared`
    (the tone package: ONE set of bands for the whole pair) holds every member to the band they all
    play in, so the pair keeps one shape rather than losing a band on one side only; `whose` names
    that band in the reason."""
    kept, dropped = {}, []
    for code, bs in bands.items():
        band = shared if shared is not None else live_bands.get(code)
        kept[code] = []
        for b in bs:
            if band is not None and band[0] <= float(b["f"]) <= band[1]:
                kept[code].append(b)
                continue
            where = whose or code
            dropped.append(dict(b, channel=code, live_band_hz=list(band) if band else None,
                                reason=(f"outside where {where} plays ({_hz(band)}, within {LIVE_BAND_DB:g} dB "
                                        f"of its passband level): a cut where a channel is silent moves only "
                                        f"its stopband" if band else
                                        f"{where} plays nowhere within {LIVE_BAND_DB:g} dB of its passband level")))
    return kept, dropped


def _dropped_why(dropped):
    return [f"{d['channel']} {d['type']} {d['f']:g} Hz {d['gain_db']:+.1f} dB DROPPED -- {d['reason']}"
            for d in dropped]


# ---------------------------------------------------------------- the three package kinds
def _score(f, resid, live):
    """The scale where the curve is true: 1/3-oct macro residual rms over the live band."""
    macro = _smooth(f, np.where(live, resid, 0.0), 3)
    return float(np.sqrt(np.mean(macro[live] ** 2))) if live.any() else float("nan")


def _apply_bands(f, meas_db, bands):
    if not bands:
        return meas_db
    return meas_db + _db(dsp_math.eq_complex(f, [band_tuple(b) if isinstance(b, dict) else b for b in bands]))


def package_lr(f, pair, members, meas, targets, tol_db=LR_TOL_DB, live_bands=None):
    """One shape for left and right: cut the louder side, shelves / Q <= 1, until |L-R| per
    1/3-oct band in LR_BAND is within `tol_db`. The difference is read on 1/3-oct macro curves --
    the scale a single point tells the truth at -- and only where BOTH members play (`live_bands`,
    each channel's own, from `live_band`; read off the curves here when not given)."""
    L, R = members
    if L not in meas or R not in meas:
        return None
    lb = live_bands if live_bands is not None else {c: live_band(f, meas[c]) for c in (L, R)}
    # The pair is read where BOTH play, inside LR_BAND -- not over LR_BAND whole. A level offset is
    # a median of L-R, and a median taken where either side is silent is the median of two noise
    # floors: two woofers 43-46 dB down across 300-4000 Hz reported +12.3 dB against a real
    # difference of 0.55 dB, and the shape matched to it was matched to nothing (#56 item 7).
    shared = _overlap(lb.get(L), lb.get(R), LR_BAND)
    live = _live(targets[L]) & _live(targets[R]) & _in_band(f, shared)
    if not live.any():
        return {"id": f"lr:{pair}", "kind": "lr", "pair": pair, "channels": [L, R], "bands": {L: [], R: []},
                "why": [f"not read: {L} plays {_hz(lb.get(L))} and {R} {_hz(lb.get(R))} (within {LIVE_BAND_DB:g} dB "
                        f"of each one's passband level), so the two share nothing in {LR_BAND[0]:g}-{LR_BAND[1]:g} Hz "
                        f"where the image lives -- no L/R shape and no level offset to report"],
                "listen": LISTEN["lr"], "score": None, "needed": False, "dropped": []}
    read = (float(f[live].min()), float(f[live].max()))
    d = _smooth(f, meas[L], 3) - _smooth(f, meas[R], 3)
    # A level difference is not a shape difference (analysis-playbook): the pair's overall offset
    # is the GAIN's business (1.4) and is reported, not equalised; what is left is shape.
    level_diff = float(np.median(d[live]))
    d = d - level_diff
    before = [(lo, hi, float(np.mean(d[(f >= lo) & (f < hi) & live])))
              for lo, hi in _third_bands(*LR_BAND) if ((f >= lo) & (f < hi) & live).any()]
    worst = max(abs(b[2]) for b in before) if before else 0.0
    bands = {L: [], R: []}
    why = [f"|L-R| read on 1/3-oct macro curves over {_hz(read)} -- where both play (each within "
           f"{LIVE_BAND_DB:g} dB of its passband level) inside {LR_BAND[0]:g}-{LR_BAND[1]:g} Hz -- after the "
           f"pair's level offset ({level_diff:+.1f} dB, {L} vs {R}, read over the same band -- a GAIN matter, "
           f"not EQ) is taken out; worst band {worst:+.2f} dB"]
    if worst > tol_db:
        w = live.astype(float)
        for code, sign in ((L, 1.0), (R, -1.0)):
            resid = np.where(live, np.maximum(sign * d, 0.0), 0.0)   # what this side is LOUDER by
            fit, _ = dsp_math.greedy_eq_fit(f, resid, w, n_bands=2, gain_lo=-MAX_CUT_DB, gain_hi=0.0,
                                            q_set=(0.5, 0.7, 1.0), n_f0=16, band=read, allow_shelf=True)
            bands[code] = _merge_same_f([band_dict(*b) for b in fit if b[2] < 0])
        why.append("cuts only, on the louder side, no narrower than Q 1 (the widest that works -- "
                   "narrow L/R matching injects a group-delay asymmetry the ear reads as a drifting image)")
    bands, dropped = _clamp_to_live(bands, lb)
    why += _dropped_why(dropped)
    after_L = _apply_bands(f, meas[L], bands[L])
    after_R = _apply_bands(f, meas[R], bands[R])
    d2 = _smooth(f, after_L, 3) - _smooth(f, after_R, 3)
    d2 = d2 - float(np.median(d2[live]))
    after = [(lo, hi, float(np.mean(d2[(f >= lo) & (f < hi) & live])))
             for lo, hi in _third_bands(*LR_BAND) if ((f >= lo) & (f < hi) & live).any()]
    worst_after = max(abs(b[2]) for b in after) if after else 0.0
    return {"id": f"lr:{pair}", "kind": "lr", "pair": pair, "channels": [L, R], "bands": bands,
            "why": why, "listen": LISTEN["lr"],
            "score": {"worst_lr_db_before": round(worst, 2), "worst_lr_db_after": round(worst_after, 2),
                      "tolerance_db": tol_db, "level_diff_db": round(level_diff, 2),
                      "read_band_hz": [round(read[0], 1), round(read[1], 1)]},
            "needed": worst > tol_db and any(bands.values()), "dropped": dropped,
            "lr_bands_before": [(round(a), round(b), round(v, 2)) for a, b, v in before],
            "lr_bands_after": [(round(a), round(b), round(v, 2)) for a, b, v in after]}


def package_res(f, group, codes, meas, targets, joints, ellipsoids, gates, allow_boost=False,
                live_bands=None):
    """Driver resonances per group: medium-width PEAKS that stay in the ellipsoid, pass the
    excess-phase gate, sit away from junctions, inside the band the channel plays in; cut by their
    prominence, Q at most the ceiling."""
    bands, why, left_out = {}, [], []
    for code in codes:
        if code not in meas:
            continue
        live = _live(targets[code])
        band = live_bands.get(code) if live_bands is not None else live_band(f, meas[code])
        plays = _in_band(f, band)
        excl = _junction_mask(f, code, joints)
        # A resonance is read against a ONE-octave trend: the 1/3-oct macro `curve_view` uses for
        # tone absorbs most of a Q 4 hump (a +5 dB Q 4 peak leaves 1.3 dB against 1/3, 4 dB against
        # 1/1), and a Q 4 resonance is exactly the thing this package exists for.
        view = curve_view.multiscale(f, meas[code], (float(f[0]), float(f[-1])), macro_frac=RES_TREND_FRAC, fine_frac=24)
        feats = curve_view.find_features(view, min_prominence_db=MIN_PROMINENCE_DB, source="sweep")
        ell = ellipsoids.get(code)
        gate = gates.get(code)
        chosen = []
        for ft in feats:
            fc, w, e = ft["f_center"], ft["width_oct"], ft["extremum_db"]
            k = int(np.argmin(np.abs(f - fc)))
            reason = None
            if not live[k]:
                reason = "outside the channel's passband"
            elif not plays[k]:
                reason = (f"outside where the channel plays ({_hz(band)}, within {LIVE_BAND_DB:g} dB of its "
                          f"passband level) -- the target says it should, the curve says it does not (#56 item 7)")
            elif excl[k]:
                reason = "within an octave of a junction -- delay/polarity/APF territory (1.3), not EQ"
            elif ft["kind"] == "dip":
                reason = ("a dip: a boost needs --allow-boost and the excess-phase gate"
                          if fc < SCHROEDER_HZ else
                          "a dip above Schroeder: the position, not the car (Rayleigh statistics)")
            elif w < RES_WIDTH[0]:
                reason = "narrower than 1/6 oct: what fails to survive a mic move is always narrow (Wehmeyer)"
            elif w > RES_WIDTH[1]:
                reason = "broader than 2/3 oct: that is tone, package `tone`"
            if reason is None and ell is not None:
                match = [x for x in ell["features"] if x["kind"] == "peak" and abs(math.log2(x["f_center"] / fc)) <= 1 / 6]
                if not match:
                    reason = "not found on the ellipsoid's mean curve -- verify-first"
                elif not match[0]["stays"]:
                    reason = f"MOVES across the positions ({match[0]['present_in']} present) -- the position, not the car"
            q_ceiling = Q_BORROWED
            if ell is not None:
                import ellipsoid as E
                q_ceiling, _measured = E.q_ceiling_at(ell, fc)
            w_q = max(w, 1.0 / 48.0)                   # a one-point feature has no width to speak of
            q_feature = 1.0 / (2.0 ** (w_q / 2.0) - 2.0 ** (-w_q / 2.0))
            q = min(q_feature, q_ceiling)
            if reason is None and gate is not None:
                verdict, metric, _ = gate.check(fc, q)
                if verdict in ("BLOCK", "WARN"):
                    reason = f"excess-phase gate {verdict} (S={metric:.1f}): not minimum-phase here"
                elif verdict == "OUT_OF_SCOPE":
                    why.append(f"{code} {fc:g} Hz: the excess-phase gate is out of its calibrated band -- unverified")
            if reason is not None:
                left_out.append({"channel": code, "f": fc, "db": e, "width_oct": w, "reason": reason})
                continue
            absorbed = _absorbed_fraction(f, fc, q, RES_TREND_FRAC)
            height = abs(e) / (1.0 - absorbed)
            gain = -min(height, MAX_CUT_DB)
            chosen.append(band_dict("PK", fc, gain, q))
            why.append(f"{code} PK {fc:g} Hz {gain:+.1f} dB Q {q:g}: peak {e:+.1f} dB above a 1-oct trend "
                       f"(~{height:.1f} dB tall once the trend's share is put back), {w:.2f} oct"
                       + (", stays in the ellipsoid" if ell is not None else
                          ", no ellipsoid: unverified in space (a single point; capture the ellipsoid to confirm)")
                       + (", phase gate ALLOW" if gate is not None else ", no phase gate")
                       + (f", Q capped at the measured ceiling {q_ceiling:g}" if q_feature > q_ceiling else ""))
        if len(chosen) > MAX_BANDS_PER_CHANNEL:
            chosen = sorted(chosen, key=lambda b: b["gain_db"])[:MAX_BANDS_PER_CHANNEL]
            why.append(f"{code}: budget {MAX_BANDS_PER_CHANNEL} bands -- the deepest kept")
        bands[code] = chosen
    score = {}
    for code in codes:
        if code in meas:
            live = _live(targets[code])
            before = meas[code] - targets[code]
            after = _apply_bands(f, meas[code], bands.get(code, [])) - targets[code]
            score[code] = {"fine_rms_before": round(float(np.sqrt(np.mean((before - _smooth(f, before, RES_TREND_FRAC))[live] ** 2))), 2),
                           "fine_rms_after": round(float(np.sqrt(np.mean((after - _smooth(f, after, RES_TREND_FRAC))[live] ** 2))), 2)}
    return {"id": f"res:{group}", "kind": "res", "group": group, "channels": [c for c in codes if c in meas],
            "bands": bands, "why": why, "left_out": left_out, "listen": LISTEN[f"res:{group}"],
            "score": score, "needed": any(bands.values()), "dropped": []}


def package_tone(f, pair, members, meas, targets, ellipsoids, live_bands=None):
    """The pair toward the target on the macro scale, identically on both sides: bands only where
    the 1/3-oct residual exceeds max(TONE_TOL_DB, 2 sigma(f)); shelves and Q <= 1.4; cuts only --
    and only where every member plays (`live_bands`; read off the curves when not given)."""
    present = [c for c in members if c in meas]
    if not present:
        return None
    lb = live_bands if live_bands is not None else {c: live_band(f, meas[c]) for c in present}
    # One set of bands for the pair, so ONE band they all play in: the fit's candidates are placed
    # inside it and whatever still lands outside is dropped from every member (#56 item 7). Before,
    # the candidates spanned the whole grid, and a Q 1.4 cut centred where a tweeter is silent
    # earned its place on the skirt alone.
    shared = _overlap(*(lb.get(c) for c in present))
    live = np.logical_and.reduce([_live(targets[c]) for c in present]) & _in_band(f, shared)
    if not live.any():
        return None
    def _shape(c, m):
        r = m - targets[c]
        return r - float(np.median(r[live]))         # one offset per channel: level is the master's / gain's job
    resid = np.mean([_shape(c, meas[c]) for c in present], axis=0)
    macro = _smooth(f, np.where(live, resid, 0.0), 3)
    tol = np.full(f.size, TONE_TOL_DB)
    for c in present:
        if ellipsoids.get(c) is not None:
            import ellipsoid as E
            tol = np.maximum(tol, np.array([2.0 * E.sigma_at(ellipsoids[c], float(v)) for v in f]))
    over = live & (macro > tol)                       # above the target beyond tolerance: cut
    under = live & (macro < -tol)                     # below: not a boost -- said
    why = [f"1/3-oct residual vs target over the live band; tolerance max({TONE_TOL_DB:g} dB, 2 sigma)"
           + (" from the ellipsoid" if any(ellipsoids.get(c) is not None for c in present) else " (no ellipsoid: 1 dB)")]
    bands, dropped = [], []
    if over.any():
        w = live.astype(float)
        fit, _ = dsp_math.greedy_eq_fit(f, np.where(over, macro, 0.0), w, n_bands=3, gain_lo=-MAX_CUT_DB, gain_hi=0.0,
                                        q_set=(0.5, 0.7, 1.0, 1.4), n_f0=24, band=shared, allow_shelf=True)
        bands = _merge_same_f([band_dict(*b) for b in fit if b[2] < 0])
        why.append("cuts only, identically on both sides (a level offset is the master's job); "
                   "nothing narrower than Q 1.4 -- the target lives at the macro scale")
        kept, dropped = _clamp_to_live({present[0]: bands}, lb, shared=shared, whose=f"the pair {pair}")
        bands = kept[present[0]]
        dropped = [dict(d, channel=", ".join(present)) for d in dropped]    # one band, every member
        why += _dropped_why(dropped)
    if under.any():
        lo_u, hi_u = float(f[under].min()), float(f[under].max())
        why.append(f"below the target beyond tolerance in {lo_u:.0f}-{hi_u:.0f} Hz: NOT boosted -- raise the "
                   f"pair's level or accept; a boost into a null burns headroom")
    before = _score(f, resid, live)
    after = _score(f, np.mean([_shape(c, _apply_bands(f, meas[c], bands)) for c in present], axis=0), live)
    return {"id": f"tone:{pair}", "kind": "tone", "pair": pair, "channels": present,
            "bands": {c: list(bands) for c in present}, "why": why, "listen": LISTEN["tone"],
            "score": {"macro_rms_before": round(before, 2), "macro_rms_after": round(after, 2)},
            "needed": bool(bands), "dropped": dropped}


# ---------------------------------------------------------------- assembly
PARTS = ("1", "2", "all")


def _recheck_junctions(pk, joints):
    """The junctions whose band (+-JUNCTION_EXCL_OCT of the corner) a package's bands reach into,
    on a channel that belongs to the junction -- their delay is re-read before the package is
    banked (the user's rule, 2026-09-17: a step whose EQ touched a junction's band re-checks it;
    otherwise the delays stay). A resonance package never reaches one by construction."""
    hit = []
    for code, bands in pk.get("bands", {}).items():
        for b in bands:
            f0 = float(b["f"])
            for lo, hi, fc in joints:
                if code not in (lo, hi):
                    continue
                if fc / 2 ** JUNCTION_EXCL_OCT <= f0 <= fc * 2 ** JUNCTION_EXCL_OCT:
                    label = f"{lo}↔{hi}"
                    if label not in hit:
                        hit.append(label)
    return hit


def propose(f, meas, targets, chains, roles, pairs, joints, ellipsoids=None, gates=None,
            allow_boost=False, routes=None, part="all"):
    """The packages of `part` ("1": the coarse per-driver resonances, Phase 1's, before the delays;
    "2": L/R shape then tone per pair, Phase 2's; "all": both, in order), in decision order.
    `pairs`: {name: [L, R]}. Returns the list."""
    if part not in PARTS:
        raise ValueError(f"part must be one of {PARTS}, not {part!r}")
    ellipsoids = ellipsoids or {}
    gates = gates or {}
    out = []
    # Sequential on purpose, in the doctrine's order (phase_2_eq 2a -> 2c -> 2d): each package is
    # read on the curves AS THE EARLIER PACKAGES LEAVE THEM. Resonances first -- they are the
    # driver's own, medium-width -- or a +5 dB Q 4 peak on one side reads as a 2.5 dB L/R shape
    # difference and gets a broad cut it does not deserve; then the pair's shape; then the pair's
    # tone. The report says which packages each one assumes accepted.
    meas = {c: np.array(v, dtype=float) for c, v in meas.items()}
    # Where each channel PLAYS, read once on the curves as they arrive -- before any package has cut
    # anything, since a cut of at most MAX_CUT_DB does not move where a channel plays -- and anchored
    # on its own ledger corners. Every package is held to it (#56 item 7).
    live_bands = {c: live_band(f, meas[c], chains.get(c)) for c in meas}
    groups = {}
    for code in meas:
        g = GROUP_OF_ROLE.get(str(roles.get(code, "")).lower())
        if g is None:
            g = "low" if P._is_sub(code) else ("high" if code.startswith("tw") else "mid")
        groups.setdefault(g, []).append(code)
    # Part 1 -- the coarse per-driver resonances. In part 2 they are not recomputed: the ledger's
    # chains carry the bands Phase 1 banked, and part 2's `meas` is a series measured THROUGH those
    # chains (the `(rta)` of each channel, as configured -- `main`).
    if part in ("1", "all"):
        for g in ("low", "mid", "high"):
            if g in groups:
                pk = package_res(f, g, sorted(groups[g]), meas, targets, joints, ellipsoids, gates, allow_boost,
                                 live_bands=live_bands)
                pk["part"] = "1"
                out.append(pk)
                for code, bands in pk["bands"].items():
                    meas[code] = _apply_bands(f, meas[code], bands)
    if part in ("2", "all"):
        for name, members in pairs.items():
            pk = package_lr(f, name, members, meas, targets, live_bands=live_bands)
            if pk:
                pk["part"] = "2"
                pk["assumes"] = [p["id"] for p in out if p.get("needed")]
                out.append(pk)
                for code, bands in pk["bands"].items():
                    meas[code] = _apply_bands(f, meas[code], bands)
        for name, members in pairs.items():
            pk = package_tone(f, name, members, meas, targets, ellipsoids, live_bands=live_bands)
            if pk:
                pk["part"] = "2"
                pk["assumes"] = [p["id"] for p in out if p.get("needed")]
                out.append(pk)
    for pk in out:
        pk["live_bands_hz"] = {c: (list(live_bands[c]) if live_bands.get(c) else None)
                               for c in pk.get("channels", []) if c in live_bands}
        pk["delta"] = to_delta(pk, chains, routes)
        pk["recheck_junctions"] = _recheck_junctions(pk, joints)
    return out


def to_delta(pk, chains, routes=None):
    """The package as an `apply.propose` delta: EQ bands APPENDED to each channel's existing bank
    (the ledger row's `eq`), on the `channels` tier -- or, when `routes` maps the pair's virtual
    channel, the broad L/R and tone moves go to the VIRTUAL row that feeds them."""
    delta = {}
    for code, bands in pk["bands"].items():
        if not bands:
            continue
        tier, row = "channels", code
        if routes and pk["kind"] in ("lr", "tone"):
            for vcode, outs in routes.items():
                if code in outs:
                    tier, row = "virtual_channels", vcode
                    break
        existing = list((chains.get(code) or {}).get("eq_rows") or []) if tier == "channels" else []
        delta.setdefault(tier, {}).setdefault(row, {})
        merged = existing + bands
        prev = delta[tier][row].get("eq")
        delta[tier][row]["eq"] = (prev or []) + bands if prev else merged
    return delta


def _merge_same_f(bands):
    """Two bands the greedy fit put on one frequency and Q become one (gains add)."""
    out = []
    for b in bands:
        for o in out:
            if o["type"] == b["type"] and abs(o["f"] - b["f"]) < 1e-6 and abs(o["q"] - b["q"]) < 1e-6:
                o["gain_db"] = round(o["gain_db"] + b["gain_db"], 1)
                break
        else:
            out.append(dict(b))
    return out


def merge_deltas(packages):
    delta = {}
    for pk in packages:
        for tier, rows in (pk.get("delta") or {}).items():
            for row, fields in rows.items():
                d = delta.setdefault(tier, {}).setdefault(row, {})
                d["eq"] = (d.get("eq") or []) + [b for b in fields.get("eq") or [] if b not in (d.get("eq") or [])]
    return delta


def render(packages):
    parts = sorted({pk.get("part", "?") for pk in packages})
    which = ("part 1, the coarse per-driver EQ -- Phase 1's, before the delays" if parts == ["1"] else
             "part 2, the pairs and the tone -- Phase 2's" if parts == ["2"] else "both parts")
    lines = [f"  EQ proposals -- packages, in decision order ({which}); say yes or no to a package, not a band", ""]
    for pk in packages:
        head = f"  [{pk['id']}]  " + ("PROPOSED" if pk.get("needed") else "nothing to do")
        if pk["kind"] == "lr" and pk["score"]:
            s = pk["score"]
            head += f"   worst |L-R| {s['worst_lr_db_before']:+.2f} -> {s['worst_lr_db_after']:+.2f} dB (tol {s['tolerance_db']:g})"
        elif pk["kind"] == "tone":
            s = pk["score"]
            head += f"   macro rms {s['macro_rms_before']:.2f} -> {s['macro_rms_after']:.2f} dB"
        lines.append(head)
        for code, bands in pk["bands"].items():
            for b in bands:
                lines.append(f"      {code:6} {b['type']:3} {b['f']:>8.1f} Hz {b['gain_db']:+5.1f} dB  Q {b['q']:g}")
        if pk["kind"] == "res":
            for code, sc in pk["score"].items():
                lines.append(f"      {code:6} fine residual rms {sc['fine_rms_before']:.2f} -> {sc['fine_rms_after']:.2f} dB")
            for lo in pk.get("left_out", [])[:12]:
                lines.append(f"      - {lo['channel']:6} {lo['f']:>8.1f} Hz {lo['db']:+5.1f} dB ({lo['width_oct']:.2f} oct): {lo['reason']}")
        for w in pk["why"]:
            lines.append(f"      why: {w}")
        if pk.get("assumes"):
            lines.append(f"      assumes accepted: {', '.join(pk['assumes'])}")
        if pk.get("recheck_junctions"):
            lines.append(f"      → re-check the delay at {', '.join(pk['recheck_junctions'])} before banking this "
                         f"(predict --align): its bands reach into the junction's band")
        lines.append(f"      listen: {', '.join(pk['listen'])}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def _load_house(path):
    return target_bands.HouseCurve.from_file(path)


def baseline_for(part, record=None):
    """Is the series this run reads a BASELINE -- captured before any crossover was designed?

    The question `protective.should_de_embed` needs answered, and this module used to answer it
    `True` at both call sites whatever it read (skill #56 item 8, the audit's root cause). So a
    Phase-2 series measured THROUGH the designed crossovers was treated as a Phase-0 baseline, every
    channel without a protective record came back "refused at de-embed", and the only record the
    CLI could then take was `OFF` -- "swept with nothing in the chain" -- which is false for a series
    measured with the tune in place: the round came to carry an untrue statement about the car.

    Part 2 is by definition not a baseline: it reads the system as configured. Otherwise the round's
    own phase decides where the caller has its record (`0`/`-1` are baselines, as in
    `rew_tool.analyze_joints`). Without one, parts 1 and `all` stay baselines, as they always were:
    they read the solos as bare drivers and put the ledger's chain on top (`H x chain_response`),
    which presumes nothing of that chain was in the capture."""
    if str(part) == "2":
        return False
    phase = (record or {}).get("phase")
    if phase is not None:
        return str(phase) in ("0", "-1")
    return True


def load_part2_rew(codes, ver, f, api=None):
    """Part 2's series from a live REW: `(loaded, gates, notes)`.

    `loaded` is {code: (H, info)} with H the channel's `<code>_<ver> (rta)` MAGNITUDE as a zero-phase
    response -- the MMM, which `phase_2_eq.md` 2a EQs against -- in the shape
    `predict.de_embed_solos` takes, so the protective question is asked of it exactly as of a solo.
    `gates` is the excess-phase gate of each channel's `<code>_<ver> (sw)`: the sweep says what is
    EQ-able, the RTA what to EQ, and neither stands in for the other.

    Until 2026-09-23 part 2 took its magnitude from the `(sw)` -- a single point, with the ledger's
    chain put on top of a series already measured through it -- and that is the reading that put a
    band in a tweeter's stopband and a +12.3 dB offset on a pair 0.55 dB apart (#56 item 7). So a
    channel whose `(sw)` is in the series and whose `(rta)` is not REFUSES the run, by name --
    falling back to the sweep would be that same reading again, only quieter. A channel with
    neither is not in this series at all: named in `notes` and left out, as a missing sweep always
    was. A missing or unreadable `(sw)` costs only its gate, and says so."""
    if api is None:
        import rew_api as api  # noqa: F811
    loaded, gates, notes, missing = {}, {}, [], []
    for code in codes:
        rta_t, sw_t = f"{code}_{ver} (rta)", f"{code}_{ver} (sw)"
        try:
            mag, info = P.load_rta_rew(rta_t, f, api=api)
        except KeyError:
            try:
                api.find_measurement_id(sw_t)
            except KeyError:
                notes.append(f"{code}: not in series _{ver} -- neither {rta_t!r} nor {sw_t!r}; no EQ proposed for it")
                continue
            missing.append(f"{code} ({rta_t!r} is missing, {sw_t!r} is there)")
            continue
        except P.PredictError as exc:
            raise ProposeError(str(exc)) from exc
        loaded[code] = (10.0 ** (np.asarray(mag, float) / 20.0) + 0j, info)
        try:
            _H, sinfo = P.load_solo_rew(sw_t, f, api=api, keep_ir=True)
        except (KeyError, P.PredictError) as exc:
            notes.append(f"{code}: no excess-phase gate -- {sw_t!r}: {exc}")
            continue
        g = gate_from_kept_ir(sinfo["ir"])
        if g is not None:
            gates[code] = g
    if missing:
        raise ProposeError(
            f"part 2 reads each channel's MAGNITUDE from its (rta) and only the excess phase from its "
            f"(sw) (phase_2_eq.md 2a); series _{ver} has no (rta) for: {'; '.join(missing)}. Measure it "
            f"(MMM), or name the series that has it with --ver -- the sweep is not read in its place")
    return loaded, gates, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--solos", metavar="DIR", help="v7 solos (raw, protectives marked in the files); "
                                                    "parts 1 / all only -- a directory holds no (rta)")
    src.add_argument("--rew", action="store_true", help="series _<ver> from REW: solos `<ch>_<ver> (sw)` "
                                                        "(parts 1 / all); part 2 takes the magnitude from "
                                                        "`<ch>_<ver> (rta)` and the excess phase from the (sw)")
    ap.add_argument("--ver", default="1")
    ap.add_argument("--process", default=None, help="process dir for the round record (REW solos)")
    ap.add_argument("--house", metavar="FILE", help="the house curve (REW text)")
    ap.add_argument("--ellipsoid", metavar="DIR", default=None, help="v7 dir with `<code>-pN.json` positions")
    ap.add_argument("--route", action="append", default=[], metavar="VIRTUAL=out1,out2")
    ap.add_argument("--preset", default=None)
    ap.add_argument("--allow-boost", action="store_true")
    ap.add_argument("--part", default="all", choices=PARTS,
                    help="1 = the coarse per-driver EQ (Phase 1, before the delays); 2 = pairs and tone (Phase 2); all")
    ap.add_argument("--accept", default=None, help="comma list of package ids to merge into eq-delta.json")
    ap.add_argument("--out", metavar="DIR", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    # The response model is bound to THIS device's processing rate before anything is modelled.
    # Not inside a branch: the crossover model runs on every path, and a binding that happens only
    # where the delay grid is computed leaves the common case on a module constant (hub #28).
    if getattr(args, "project", None):
        import dsp_profile as _dp_bind
        _rate_hz, _rate_note = _dp_bind.bind_model_rate(args.project)
        if _rate_note:
            print(f"  \u26a0 {_rate_note}", file=sys.stderr)
    if args.selftest:
        return _selftest()
    if not args.project or not args.house or not (args.solos or args.rew):
        ap.error("need --project, --house and a solo source (--solos DIR | --rew)")

    f = P.grid(20, 20000, 96)
    preset, snap = P.load_project_state(args.project, args.preset)
    chains = P.chains_from_snapshot(snap)
    for code, row in (snap.get("channels") or {}).items():
        if P.canon(code) in chains:
            chains[P.canon(code)]["eq_rows"] = list(row.get("eq") or [])
    routes = {}
    for spec in args.route:
        v, _, outs = spec.partition("=")
        routes[v.strip()] = [o.strip() for o in outs.split(",") if o.strip()]
    if routes:
        chains, _notes = P.route_chains(chains, P.chains_from_snapshot(snap, "virtual_channels"), routes)
    joints = P.joints_from_chains(chains)
    import project as _project
    pdata = _project.Project(args.project).load()
    roles = {c["code"]: c.get("role") for c in (pdata.get("channels") or []) if isinstance(c, dict)}
    pairs = {}
    for name, members in ((pdata.get("glossary") or {}).get("pairs") or {}).items():
        if len(members) == 2 and not any(P._is_sub(m) for m in members):
            pairs[name] = list(members)
    if not pairs:
        for code in chains:
            if code.endswith("-L") and code[:-2] + "-R" in chains:
                pairs[code[:-2].upper() + "s"] = [code, code[:-2] + "-R"]

    gates = {}
    live_codes = [c for c in chains if not chains[c].get("muted") and not chains[c].get("unmodellable")]
    if args.part == "2" and args.solos:
        # Part 2's magnitude is the `(rta)` of the series, and a solo directory carries impulses --
        # sweeps -- only. Refused by name rather than read as the sweep it is (#56 item 7).
        print(f"  REFUSING part 2 on {args.solos}: part 2 reads each channel's MAGNITUDE from its (rta) "
              f"of the series and only the excess phase from its (sw) (phase_2_eq.md 2a), and a solo "
              f"directory carries sweeps only -- no (rta) there for {', '.join(live_codes) or 'any channel'}. "
              f"Read the series from REW: --rew --ver N.", file=sys.stderr)
        return 2
    # The baseline question is the PART's and the round's to answer, not a constant (#56 item 8):
    # part 2 is measured as configured, so nothing in it is a baseline.
    if args.solos:
        loaded = P.load_solos_dir(args.solos, f)
        solos, notes, refused = P.de_embed_solos(loaded, f, baseline=baseline_for(args.part))
        for code, (_H, info) in loaded.items():
            try:
                import resonalyze_ir
                doc = resonalyze_ir.load_file(info["path"])       # v7 numbers or v8 base64 alike
                g = gate_from_ir(doc["transferRealSamples"], doc["sampleRate"])
                if g is not None:
                    gates[code] = g
            except (OSError, KeyError, ValueError):
                pass
    else:
        import rew_api as api
        record = None
        if args.process:
            from process import Process
            record = Process(args.process).protective_record_for(args.ver)
        if args.part == "2":
            try:
                loaded, gates, load_notes = load_part2_rew(live_codes, args.ver, f, api=api)
            except ProposeError as e:
                print(f"  REFUSING part 2: {e}", file=sys.stderr)
                return 2
            for n in load_notes:
                print(f"  {n}", file=sys.stderr)
        else:
            loaded = {}
            for code in chains:
                try:
                    # The impulse is kept for the excess-phase gate: the `(sw)` is what says what is
                    # EQ-able on this path too, as the v7 files always did on the other one.
                    loaded[code] = P.load_solo_rew(f"{code}_{args.ver} (sw)", f, api=api, keep_ir=True)
                except (P.PredictError, KeyError) as e:
                    print(f"  {code}: {e}", file=sys.stderr)
                    continue
                g = gate_from_kept_ir(loaded[code][1]["ir"])
                if g is not None:
                    gates[code] = g
        solos, notes, refused = P.de_embed_solos(loaded, f, record=record,
                                                 baseline=baseline_for(args.part, record))
    # Parts 1 / all read the solos as bare drivers and put the ledger's chain on them; part 2's series
    # was measured THROUGH that chain (as configured), so its magnitude is used as measured -- putting
    # the chain on top again would count every crossover twice.
    through = args.part != "2"
    meas = {c: _db(H * P.chain_response(f, chains[c]) if through else H) for c, H in solos.items()
            if c in chains and not chains[c].get("muted") and not chains[c].get("unmodellable")}
    house = _load_house(args.house)
    pairs_of = {m: name for name, ms in pairs.items() for m in ms}
    targets = channel_targets(f, house, chains, roles, pairs_of)
    ellipsoids = {}
    if args.ellipsoid:
        import ellipsoid as E
        for code in meas:
            try:
                ellipsoids[code] = E.analyse(f, E.load_positions_v7(args.ellipsoid, code, f))
            except E.EllipsoidError:
                continue
    packages = propose(f, meas, targets, chains, roles, pairs, joints, ellipsoids, gates,
                       allow_boost=args.allow_boost, routes=routes, part=args.part)
    # A channel refused at de-embed gets no EQ package, and until 2026-09-01 that was ALL that
    # happened: `refused` was bound and never read, and the note explaining it rode in `notes`,
    # which is truncated to eight lines and printed only in the human mode. So under `--json` a
    # channel could vanish from the proposal in silence -- the same shape of silence the refusal
    # exists to prevent (autosound-hub #31). It goes to stderr in BOTH modes; stdout is untouched,
    # so the JSON contract is exactly what it was.
    for code in refused:
        print(f"  {code}: refused at de-embed -- no EQ proposed for it. "
              f"Record the capture round's protective state (or say there was none) and re-run.",
              file=sys.stderr)
    if args.json:
        print(json.dumps(packages, indent=1, default=float))
    else:
        print(render(packages))
        for n in notes[:8]:
            print(f"  note: {n}")
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "eq-propose.json"), "w", encoding="utf-8") as fh:
            json.dump(packages, fh, indent=1, default=float)
        for pk in packages:
            if pk.get("needed"):
                with open(os.path.join(args.out, f"eq-{pk['id'].replace(':', '-')}.json"), "w", encoding="utf-8") as fh:
                    json.dump(pk["delta"], fh, indent=1)
        if args.accept:
            want = {s.strip() for s in args.accept.split(",")}
            merged = merge_deltas([pk for pk in packages if pk["id"] in want])
            with open(os.path.join(args.out, "eq-delta.json"), "w", encoding="utf-8") as fh:
                json.dump(merged, fh, indent=1)
            print(f"  wrote {args.out}/eq-delta.json for {', '.join(sorted(want))}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- selftest
def _selftest():
    """Anchored to the definitions: a driver resonance is cut where it is, a comb is not boosted,
    a moving peak is not proposed, an L/R shelf difference goes to the pair package, a tonal
    offset moves the pair on the macro scale and leaves the fine residual alone."""
    import tempfile
    import ellipsoid as E
    f = P.grid(20, 20000, 96)

    class House:
        def at(self, v):
            return 0.0 - 1.5 * math.log2(max(v, 20.0) / 1000.0)      # a gentle downward tilt

    house = House()
    row = {"hp": {"f": 300, "type": "LR", "slope": 24}, "lp": {"f": 3000, "type": "LR", "slope": 24},
           "gain_db": 0, "ta_ms": 0, "polarity": "NORM", "eq": []}
    chains = {"m-L": P.chain_from_row(row), "m-R": P.chain_from_row(row)}
    roles = {"m-L": "midrange", "m-R": "midrange"}
    pairs = {"Ms": ["m-L", "m-R"]}
    joints = []                                      # no junction inside the mids' band here
    pairs_of = {"m-L": "Ms", "m-R": "Ms"}
    targets = channel_targets(f, house, chains, roles, pairs_of)

    def driver(extra=None):
        H = np.ones_like(f, dtype=complex)
        for kind, f0, g, q in (extra or []):
            H = H * dsp_math.peq_response(f, kind, f0, g, q)
        return H

    def meas_of(HL, HR):
        return {"m-L": _db(HL * P.chain_response(f, chains["m-L"])) + targets["m-L"] - _db(P.chain_response(f, chains["m-L"])),
                "m-R": _db(HR * P.chain_response(f, chains["m-R"])) + targets["m-R"] - _db(P.chain_response(f, chains["m-R"]))}
    # 1. Both drivers ON target except a +5 dB Q 4 resonance at 1 kHz on m-L: one cut on m-L near
    #    1 kHz, none on m-R; no L/R package needed at the macro scale (a Q 4 peak is not a shape
    #    difference on 1/3 oct... it is, by ~1 dB -- so the L/R package may or may not fire; the
    #    resonance package must), and the tone package has nothing to do.
    res = ("PK", 1000.0, 5.0, 4.0)
    meas = meas_of(driver([res]), driver())
    pk = {p["id"]: p for p in propose(f, meas, targets, chains, roles, pairs, joints)}
    r = pk["res:mid"]
    assert r["bands"]["m-L"] and not r["bands"]["m-R"], r["bands"]
    b = r["bands"]["m-L"][0]
    assert abs(math.log2(b["f"] / 1000.0)) < 1 / 6 and -5.5 <= b["gain_db"] <= -2.0 and b["q"] <= Q_BORROWED, b
    assert r["score"]["m-L"]["fine_rms_after"] < r["score"]["m-L"]["fine_rms_before"], r["score"]
    assert not pk["tone:Ms"]["needed"], pk["tone:Ms"]
    assert any("no ellipsoid" in w for w in r["why"]), r["why"]
    # 2. A comb (a reflection) on m-R: dips are NOT boosted and are listed with the reason; the
    #    comb's narrow peaks above Schroeder are not resonances either.
    HR = driver() * (1.0 + 0.5 * np.exp(-2j * np.pi * f * 1.2e-3))
    meas2 = meas_of(driver(), HR)
    pk2 = {p["id"]: p for p in propose(f, meas2, targets, chains, roles, pairs, joints)}
    assert not any(b["gain_db"] > 0 for bs in pk2["res:mid"]["bands"].values() for b in bs)
    assert any("dip" in lo["reason"] or "narrow" in lo["reason"] for lo in pk2["res:mid"]["left_out"]), pk2["res:mid"]["left_out"][:3]
    # 3. With an ellipsoid where the 1 kHz peak MOVES, it is not proposed; where it STAYS, it is.
    def positions(moving):
        out = {}
        for i, pos in enumerate(E.POSITIONS):
            shift = (1.0 + (0.12 * (i - 4) / 4.0 if (moving and pos not in E.CENTRE) else 0.0))
            out[pos] = _db(driver([("PK", 1000.0 * shift, 5.0, 4.0)]))
        return out
    ell_move = E.analyse(f, positions(True))
    ell_stay = E.analyse(f, positions(False))
    pk3m = {p["id"]: p for p in propose(f, meas, targets, chains, roles, pairs, joints, {"m-L": ell_move})}
    pk3s = {p["id"]: p for p in propose(f, meas, targets, chains, roles, pairs, joints, {"m-L": ell_stay})}
    assert not pk3m["res:mid"]["bands"]["m-L"] and any("MOVES" in lo["reason"] or "verify-first" in lo["reason"]
                                                      for lo in pk3m["res:mid"]["left_out"]), pk3m["res:mid"]["left_out"]
    assert pk3s["res:mid"]["bands"]["m-L"], pk3s["res:mid"]
    # 4. L/R: the right mid 2.5 dB louder above 1 kHz (a shelf difference): the L/R package cuts
    #    the RIGHT side broadly and brings the worst band inside the tolerance; the tone package
    #    then sees the pair's mean, not the difference.
    HR4 = driver([("HS", 1000.0, 2.5, 0.71)])
    meas4 = meas_of(driver(), HR4)
    pk4 = {p["id"]: p for p in propose(f, meas4, targets, chains, roles, pairs, joints)}
    lr = pk4["lr:Ms"]
    # the level half of the shelf is reported as a GAIN matter, the shape half is equalised --
    # on whichever side is louder in each region, cuts only, no narrower than Q 1
    assert lr["needed"] and abs(lr["score"]["level_diff_db"]) > 0.5, lr["score"]
    assert lr["score"]["worst_lr_db_after"] <= LR_TOL_DB + 0.3 < lr["score"]["worst_lr_db_before"], lr["score"]
    assert all(b["q"] <= 1.0 and b["gain_db"] < 0 for bs in lr["bands"].values() for b in bs), lr["bands"]
    # 5. Tone: both mids 2 dB above target over the top of their band (a broad hump): the tone
    #    package proposes an identical broad cut on both, the macro rms falls, and it is cuts only.
    HT = driver([("HS", 1500.0, 2.0, 0.71)])
    meas5 = meas_of(HT, HT)
    pk5 = {p["id"]: p for p in propose(f, meas5, targets, chains, roles, pairs, joints)}
    t = pk5["tone:Ms"]
    assert t["needed"] and t["bands"]["m-L"] == t["bands"]["m-R"] and all(b["gain_db"] < 0 for b in t["bands"]["m-L"]), t
    assert t["score"]["macro_rms_after"] < t["score"]["macro_rms_before"], t["score"]
    assert not pk5["lr:Ms"]["needed"], pk5["lr:Ms"]["score"]
    # 6. The delta shape: appended to the row's existing bank, dict bands the ledger spells.
    chains["m-L"]["eq_rows"] = [{"type": "PK", "f": 500, "gain_db": -1.0, "q": 2.0}]
    d = to_delta(pk["res:mid"], chains)
    assert d["channels"]["m-L"]["eq"][0]["f"] == 500 and d["channels"]["m-L"]["eq"][-1]["type"] == "PK", d
    dv = to_delta(pk4["lr:Ms"], chains, routes={"VFR": ["m-R", "tw-R"]})
    assert "virtual_channels" in dv and "VFR" in dv["virtual_channels"], dv
    merged = merge_deltas([pk["res:mid"], pk5["tone:Ms"]])
    assert set(merged["channels"]) == {"m-L", "m-R"}, merged
    # 7. The excess-phase gate from an impulse: a minimum-phase resonance is ALLOWed; a comb whose
    #    reflection is STRONGER than the direct sound (r = 1.25 -- the non-minimum-phase case; with
    #    r < 1 a single reflection is minimum-phase and the gate rightly allows it, which a first
    #    draft of this test did not know) is BLOCKed at its null -- the gate built from the IR
    #    alone, no REW.
    fs, n = 96000, 1 << 15
    fb = np.fft.rfftfreq(n, 1.0 / fs)
    ir_res = np.fft.irfft(dsp_math.peq_response(fb, "PK", 1000.0, 5.0, 4.0) * np.exp(-2j * np.pi * fb * 0.002), n=n)
    ir_comb = np.fft.irfft((1.0 + 1.25 * np.exp(-2j * np.pi * fb * 1.2e-3)) * np.exp(-2j * np.pi * fb * 0.002), n=n)
    g_res, g_comb = gate_from_ir(ir_res, fs), gate_from_ir(ir_comb, fs)
    if g_res is not None:
        assert g_res.check(1000.0, 4.0)[0] in ("ALLOW", "WARN"), g_res.check(1000.0, 4.0)
        null = 1.0 / (2 * 1.2e-3)                     # 417 Hz, the comb's first null
        assert g_comb.check(null, 4.0)[0] in ("BLOCK", "WARN"), g_comb.check(null, 4.0)
    txt = render(list(pk.values()))
    assert "res:mid" in txt and "listen: c08" in txt and "why:" in txt
    tmp = tempfile.mkdtemp(prefix="autosound_eqp_")
    json.dump(list(pk.values()), open(os.path.join(tmp, "p.json"), "w", encoding="utf-8"), default=float)
    # 6. Two parts (2026-09-17): part 1 is the resonances only, part 2 the pairs only -- and a part-2
    #    package whose bands reach into a junction's band names the junction for a delay re-check,
    #    while a resonance package never does (its mask excludes the band by construction).
    ids1 = [p["id"] for p in propose(f, meas4, targets, chains, roles, pairs, joints, part="1")]
    ids2 = [p["id"] for p in propose(f, meas4, targets, chains, roles, pairs, joints, part="2")]
    assert ids1 == ["res:mid"] and ids2 == ["lr:Ms", "tone:Ms"], (ids1, ids2)
    with_joint = [("m-L", "tw-L", 2000.0), ("m-R", "tw-R", 2000.0)]     # the shelf at 1 kHz sits within +-1 oct
    pk6 = {p["id"]: p for p in propose(f, meas4, targets, chains, roles, pairs, with_joint)}
    assert pk6["lr:Ms"]["recheck_junctions"] == ["m-R↔tw-R"], pk6["lr:Ms"]["recheck_junctions"]
    assert pk6["res:mid"]["recheck_junctions"] == [], pk6["res:mid"]["recheck_junctions"]
    assert "re-check the delay at m-R↔tw-R" in render([pk6["lr:Ms"]]) and "part 2" in render([pk6["lr:Ms"]])
    try:
        propose(f, meas4, targets, chains, roles, pairs, joints, part="3")
        raise AssertionError("part 3 accepted")
    except ValueError:
        pass
    # 8. Every band of every package above sits inside the band its channel plays in (#56 item 7) --
    #    a property, not a case: the clamp is the last word whichever fit produced the band.
    for run in (pk, pk2, pk3m, pk3s, pk4, pk5, pk6):
        for p in run.values():
            for code, bs in p["bands"].items():
                band = p["live_bands_hz"][code]
                assert all(band[0] <= b["f"] <= band[1] for b in bs), (p["id"], code, band, bs)
    # 9. The issue's own band: a tweeter measured through HP 2800 BE24 is 28 dB down at 845 Hz, so its
    #    live band starts above 1 kHz, and `tw-R PK 845.5 Hz -5.4 dB` is DROPPED and named -- the
    #    channel, the band it plays in, the margin -- while a band inside it is kept. A resonance the
    #    TARGET calls live but the curve does not (a ledger HP an octave below where the tweeter really
    #    starts) is left out of the resonance package with the same reason.
    tw_row = {"hp": {"f": 2800, "type": "BE", "slope": 24}, "gain_db": 0, "ta_ms": 0, "polarity": "NORM", "eq": []}
    tw_chain = P.chain_from_row(tw_row)
    tw_curve = _db(P.chain_response(f, tw_chain))
    k845 = int(np.argmin(np.abs(f - 845.5)))
    band_tw = live_band(f, tw_curve, tw_chain)
    assert band_tw is not None and band_tw[0] > 1000.0 and band_tw[1] > 15000.0 and tw_curve[k845] < -25.0, \
        (band_tw, tw_curve[k845])
    kept, dropped = _clamp_to_live({"tw-R": [band_dict("PK", 845.5, -5.4, 1.4), band_dict("PK", 6000.0, -2.0, 1.0)]},
                                   {"tw-R": band_tw})
    assert [b["f"] for b in kept["tw-R"]] == [6000.0] and len(dropped) == 1, (kept, dropped)
    why9 = _dropped_why(dropped)[0]
    assert "tw-R" in why9 and "845.5" in why9 and "DROPPED" in why9 and f"{LIVE_BAND_DB:g} dB" in why9 \
        and f"{band_tw[0]:.0f}" in why9, why9
    _k2, d_none = _clamp_to_live({"tw-R": [band_dict("PK", 6000.0, -2.0, 1.0)]}, {"tw-R": None})
    assert d_none and "plays nowhere" in d_none[0]["reason"], d_none
    lowhp = {"tw-L": P.chain_from_row(dict(tw_row, hp={"f": 700, "type": "LR", "slope": 24}))}
    tgt_low = channel_targets(f, house, lowhp, {"tw-L": "tweeter"}, {})
    # the real tweeter rolls off on its own below 2.5 kHz (LR24 on top of the ledger's); a +8 dB
    # resonance at 1 kHz sits where the target says "live" (half an octave from a 700 Hz ledger
    # corner) and where the curve, resonance and all, is more than 20 dB down
    real = tgt_low["tw-L"] + _db(dsp_math.xo_response(f, 2500.0, 24, "hp", "LR")) \
        + _db(dsp_math.peq_response(f, "PK", 1000.0, 8.0, 4.0))
    tw_band = live_band(f, real, lowhp["tw-L"])
    r9 = package_res(f, "high", ["tw-L"], {"tw-L": real}, tgt_low, [], {}, {}, live_bands={"tw-L": tw_band})
    assert tw_band is not None and tw_band[0] > 1100.0, tw_band
    assert not any(b["f"] < tw_band[0] for b in r9["bands"]["tw-L"]), r9["bands"]
    assert any("outside where the channel plays" in lo["reason"] and abs(math.log2(lo["f"] / 1000.0)) < 0.3
               for lo in r9["left_out"]), r9["left_out"]
    # 10. A pair's level offset is read ONLY where both play. Two woofers whose ledger LP says 1 kHz
    #     but which roll off acoustically at 350 Hz (LR48), w-L 0.5 dB louder where they play, and
    #     noise floors 12 dB apart above that: read over the target's live band inside 300-4000 Hz the
    #     offset is the floors' +12 dB (the +12.3 dB of #56 item 7), read over the shared band it is
    #     the 0.5 dB that is there.
    w_row = {"hp": {"f": 60, "type": "LR", "slope": 24}, "lp": {"f": 1000, "type": "LR", "slope": 24},
             "gain_db": 0, "ta_ms": 0, "polarity": "NORM", "eq": []}
    wch = {"w-L": P.chain_from_row(w_row), "w-R": P.chain_from_row(w_row)}
    wtg = channel_targets(f, house, wch, {"w-L": "woofer", "w-R": "woofer"}, {"w-L": "Ws", "w-R": "Ws"})
    acoustic = _db(dsp_math.xo_response(f, 350.0, 48, "lp", "LR"))

    def with_floor(sig_db, floor_db):
        return 10.0 * np.log10(10.0 ** (sig_db / 10.0) + 10.0 ** (floor_db / 10.0))
    top = float(np.max(wtg["w-L"]))
    wmeas = {"w-L": with_floor(wtg["w-L"] + acoustic + 0.5, top - 33.0),
             "w-R": with_floor(wtg["w-R"] + acoustic, top - 45.0)}
    old_mask = _live(wtg["w-L"]) & _live(wtg["w-R"]) & (f >= LR_BAND[0]) & (f <= LR_BAND[1])
    old_offset = float(np.median((_smooth(f, wmeas["w-L"], 3) - _smooth(f, wmeas["w-R"], 3))[old_mask]))
    assert old_offset > 6.0, old_offset                       # the test has teeth: the old read is the floors
    p10 = {p["id"]: p for p in propose(f, wmeas, wtg, wch, {"w-L": "woofer", "w-R": "woofer"},
                                       {"Ws": ["w-L", "w-R"]}, [], part="2")}
    s10 = p10["lr:Ws"]["score"]
    assert abs(s10["level_diff_db"] - 0.5) < 0.3 and s10["read_band_hz"][1] < 700.0, s10
    assert "where both play" in p10["lr:Ws"]["why"][0] and "read over the same band" in p10["lr:Ws"]["why"][0]
    # ...and a pair that shares nothing inside 300-4000 Hz is SAID, not dropped from the list in silence
    sub_like = {c: with_floor(wtg[c] + _db(dsp_math.xo_response(f, 120.0, 48, "lp", "LR")), top - 60.0) for c in wch}
    p10b = {p["id"]: p for p in propose(f, sub_like, wtg, wch, {}, {"Ws": ["w-L", "w-R"]}, [], part="2")}
    assert not p10b["lr:Ws"]["needed"] and p10b["lr:Ws"]["score"] is None and "not read" in p10b["lr:Ws"]["why"][0]
    assert "nothing to do" in render([p10b["lr:Ws"]])
    # 11. Part 2 reads the (rta) for magnitude and the (sw) for excess phase -- and a channel whose (sw)
    #     is in the series but whose (rta) is not REFUSES the run by name; a channel with neither is
    #     not in the series (a note); a sweep filed under an (rta) title is refused, not read as MMM.
    import types
    fs_, n_ = 96000, 1 << 15
    t0_ = -0.25                                         # REW's buffer starts before t = 0

    def ir_at(t_s):
        x = np.zeros(n_)
        x[int(round((t_s - t0_) * fs_))] = 0.1
        return x
    f_rta = np.arange(0.0, 24000.0, 2.0)                # a linear RTA axis from 0 Hz, as REW serves one
    served_ir = {"m-L_51 (sw)": ir_at(0.002), "m-R_51 (sw)": ir_at(0.002), "tw-L_51 (rta)": ir_at(0.002)}
    served_rta = {"m-L_51 (rta)": (f_rta, 70.0 - 1.0 * np.log2(np.maximum(f_rta, 1.0) / 1000.0), None)}

    def find(title, measurements=None, exact=True):
        if title in served_ir or title in served_rta:
            return title
        raise KeyError(f"No measurement titled {title!r}")
    fake = types.SimpleNamespace(
        FINEST_SMOOTHING="1/48", find_measurement_id=find,
        get_timing=lambda mid: {"has_ir": mid in served_ir, "reference": "Loopback", "offset_s": 0.0},
        get_impulse_response=lambda mid, normalised=False: ([t0_ + i / fs_ for i in range(n_)], served_ir[mid]),
        get_fr=lambda mid, smoothing=None: served_rta[mid])
    loaded11, gates11, notes11 = load_part2_rew(["m-L"], "51", f, api=fake)
    k1k = int(np.argmin(np.abs(f - 1000.0)))
    assert abs(_db(loaded11["m-L"][0])[k1k] - 70.0) < 0.05 and loaded11["m-L"][1]["source"] == "rew-rta", loaded11
    if gate_from_ir(served_ir["m-L_51 (sw)"], fs_) is not None:          # scipy present
        assert "m-L" in gates11 and gates11["m-L"].check(1000.0, 4.0)[0] == "ALLOW", gates11
    try:
        load_part2_rew(["m-L", "m-R", "c"], "51", f, api=fake)
        raise AssertionError("a series without m-R's (rta) was read")
    except ProposeError as e:
        msg = str(e)
        assert "m-R" in msg and "m-R_51 (rta)" in msg and "m-L" not in msg.split("for:")[1], msg
        assert "c_51" not in msg, msg                               # absent altogether: not the refusal
    _l, _g, notes_c = load_part2_rew(["m-L", "c"], "51", f, api=fake)
    assert any(n.startswith("c: not in series _51") for n in notes_c), notes_c
    try:
        load_part2_rew(["tw-L"], "51", f, api=fake)
        raise AssertionError("a sweep under an (rta) title was read as the MMM")
    except ProposeError as e:
        assert "tw-L_51 (rta)" in str(e) and "impulse" in str(e), e
    # 12. Part 2 is never a baseline (#56 item 8): an unmarked channel of an as-configured series is
    #     used as measured, not refused at de-embed; parts 1 / all stay baselines unless the round's
    #     own phase says otherwise.
    assert baseline_for("2") is False and baseline_for("2", {"phase": "0"}) is False
    assert baseline_for("1") is True and baseline_for("all") is True
    assert baseline_for("1", {"phase": 2}) is False and baseline_for("all", {"phase": "0"}) is True
    s12, n12, r12 = P.de_embed_solos(loaded11, f, record=None, baseline=baseline_for("2"))
    assert r12 == [] and "m-L" in s12 and "as configured" in n12[0], n12
    _s, _n, r12b = P.de_embed_solos(loaded11, f, record=None, baseline=baseline_for("1"))
    assert r12b == ["m-L"], r12b                                  # what every part-2 run used to get
    print("selftest[eq_propose] OK -- a +5 dB Q4 resonance is cut where it is and only on its channel; a "
          "comb is not boosted and its dips are listed with the reason; a peak that MOVES in the "
          "ellipsoid is not proposed and one that STAYS is; a 2.5 dB shelf difference is cut on the louder "
          "side broadly (Q <= 1) into tolerance; a shared 2 dB hump moves both sides identically at the "
          "macro scale; deltas append to the row's bank and route broad moves to the virtual tier; the "
          "excess-phase gate built from an impulse allows a resonance and blocks a comb null; every band "
          "sits where its channel plays, and one outside (tw-R PK 845.5 Hz) is dropped and named; a pair's "
          "level offset is read where both play (0.5 dB, not the floors' +12); part 2 reads the (rta), "
          "refuses a series without it by name, and is never a baseline.")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(main())
