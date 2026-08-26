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

Packages, in the order they are computed and decided (phase_2_eq: 2a -> 2c -> 2d; each read on
the curves as the earlier packages leave them):
  1. `res:<group>`      resonances, one per driver group (sub+midbass / mids / tweeters), cuts only,
                        Q <= the measured ceiling (borrowed 6 when the ellipsoid is absent) (c14/c05, c08, c07)
  2. `lr:<pair>`        L/R shape, one per stereo pair (Ws, Ms, TWs): shelves / Q <= 1, cut the louder
                        side, until |L-R| <= 1 dB per 1/3 oct in 300-4000 Hz          (listen: c01, c02)
  3. `tone:<pair>`      the pair toward the target on the 1/3-oct macro scale, identically on both
                        sides, tolerance max(1 dB, 2 sigma(f)) from the ellipsoid           (c04)

Budgets: <= 6 bands per channel, <= 6 dB per band, no boosts unless `--allow-boost` AND the
excess-phase gate allows. Every package carries WHY (which gates said yes) and a score before /
after on the scale where the curve is true (1/3-oct residual vs target, and L-R per band).

    python3 rew_tool/eq_propose.py --project P --solos DIR [--ellipsoid DIR] [--route VFL=w-L,m-L,tw-L ...]
                                   --house curve.txt [--out DIR] [--accept lr:Ms,res:mid]

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


def _live(target_db, margin_db=20.0):
    return target_db >= np.nanmax(target_db) - margin_db


def _junction_mask(f, code, joints):
    """True where EQ on `code` is NOT allowed: within +-JUNCTION_EXCL_OCT of any junction it belongs to."""
    excl = np.zeros(f.size, dtype=bool)
    for lo, hi, fc in joints:
        if code in (lo, hi):
            excl |= (f >= fc / 2 ** JUNCTION_EXCL_OCT) & (f <= fc * 2 ** JUNCTION_EXCL_OCT)
    return excl


# ---------------------------------------------------------------- the three package kinds
def _score(f, resid, live):
    """The scale where the curve is true: 1/3-oct macro residual rms over the live band."""
    macro = _smooth(f, np.where(live, resid, 0.0), 3)
    return float(np.sqrt(np.mean(macro[live] ** 2))) if live.any() else float("nan")


def _apply_bands(f, meas_db, bands):
    if not bands:
        return meas_db
    return meas_db + _db(dsp_math.eq_complex(f, [band_tuple(b) if isinstance(b, dict) else b for b in bands]))


def package_lr(f, pair, members, meas, targets, tol_db=LR_TOL_DB):
    """One shape for left and right: cut the louder side, shelves / Q <= 1, until |L-R| per
    1/3-oct band in LR_BAND is within `tol_db`. The difference is read on 1/3-oct macro curves --
    the scale a single point tells the truth at."""
    L, R = members
    if L not in meas or R not in meas:
        return None
    live = _live(targets[L]) & _live(targets[R]) & (f >= LR_BAND[0]) & (f <= LR_BAND[1])
    if not live.any():
        return None
    d = _smooth(f, meas[L], 3) - _smooth(f, meas[R], 3)
    before = [(lo, hi, float(np.mean(d[(f >= lo) & (f < hi) & live])))
              for lo, hi in _third_bands(*LR_BAND) if ((f >= lo) & (f < hi) & live).any()]
    worst = max(abs(b[2]) for b in before) if before else 0.0
    bands = {L: [], R: []}
    why = [f"|L-R| read on 1/3-oct macro curves in {LR_BAND[0]:g}-{LR_BAND[1]:g} Hz; worst band {worst:+.2f} dB"]
    if worst > tol_db:
        w = live.astype(float)
        for code, sign in ((L, 1.0), (R, -1.0)):
            resid = np.where(live, np.maximum(sign * d, 0.0), 0.0)   # what this side is LOUDER by
            fit, _ = dsp_math.greedy_eq_fit(f, resid, w, n_bands=2, gain_lo=-MAX_CUT_DB, gain_hi=0.0,
                                            q_set=(0.5, 0.7, 1.0), n_f0=16, band=LR_BAND, allow_shelf=True)
            bands[code] = [band_dict(*b) for b in fit if b[2] < 0]
        why.append("cuts only, on the louder side, no narrower than Q 1 (the widest that works -- "
                   "narrow L/R matching injects a group-delay asymmetry the ear reads as a drifting image)")
    after_L = _apply_bands(f, meas[L], bands[L])
    after_R = _apply_bands(f, meas[R], bands[R])
    d2 = _smooth(f, after_L, 3) - _smooth(f, after_R, 3)
    after = [(lo, hi, float(np.mean(d2[(f >= lo) & (f < hi) & live])))
             for lo, hi in _third_bands(*LR_BAND) if ((f >= lo) & (f < hi) & live).any()]
    worst_after = max(abs(b[2]) for b in after) if after else 0.0
    return {"id": f"lr:{pair}", "kind": "lr", "pair": pair, "channels": [L, R], "bands": bands,
            "why": why, "listen": LISTEN["lr"],
            "score": {"worst_lr_db_before": round(worst, 2), "worst_lr_db_after": round(worst_after, 2),
                      "tolerance_db": tol_db},
            "needed": worst > tol_db, "lr_bands_before": [(round(a), round(b), round(v, 2)) for a, b, v in before],
            "lr_bands_after": [(round(a), round(b), round(v, 2)) for a, b, v in after]}


def package_res(f, group, codes, meas, targets, joints, ellipsoids, gates, allow_boost=False):
    """Driver resonances per group: medium-width PEAKS that stay in the ellipsoid, pass the
    excess-phase gate, sit away from junctions; cut by their prominence, Q at most the ceiling."""
    bands, why, left_out = {}, [], []
    for code in codes:
        if code not in meas:
            continue
        live = _live(targets[code])
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
            q_feature = 1.0 / (2.0 ** (w / 2.0) - 2.0 ** (-w / 2.0))
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
            gain = -min(abs(e), MAX_CUT_DB)
            chosen.append(band_dict("PK", fc, gain, q))
            why.append(f"{code} PK {fc:g} Hz {gain:+.1f} dB Q {q:g}: peak {e:+.1f} dB, {w:.2f} oct"
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
            "score": score, "needed": any(bands.values())}


def package_tone(f, pair, members, meas, targets, ellipsoids):
    """The pair toward the target on the macro scale, identically on both sides: bands only where
    the 1/3-oct residual exceeds max(TONE_TOL_DB, 2 sigma(f)); shelves and Q <= 1.4; cuts only."""
    present = [c for c in members if c in meas]
    if not present:
        return None
    live = np.logical_and.reduce([_live(targets[c]) for c in present])
    if not live.any():
        return None
    resid = np.mean([meas[c] - targets[c] for c in present], axis=0)
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
    bands = []
    if over.any():
        w = live.astype(float)
        fit, _ = dsp_math.greedy_eq_fit(f, np.where(over, macro, 0.0), w, n_bands=3, gain_lo=-MAX_CUT_DB, gain_hi=0.0,
                                        q_set=(0.5, 0.7, 1.0, 1.4), n_f0=24, allow_shelf=True)
        bands = [band_dict(*b) for b in fit if b[2] < 0]
        why.append("cuts only, identically on both sides (a level offset is the master's job); "
                   "nothing narrower than Q 1.4 -- the target lives at the macro scale")
    if under.any():
        lo_u, hi_u = float(f[under].min()), float(f[under].max())
        why.append(f"below the target beyond tolerance in {lo_u:.0f}-{hi_u:.0f} Hz: NOT boosted -- raise the "
                   f"pair's level or accept; a boost into a null burns headroom")
    before = _score(f, resid, live)
    after = _score(f, np.mean([_apply_bands(f, meas[c], bands) - targets[c] for c in present], axis=0), live)
    return {"id": f"tone:{pair}", "kind": "tone", "pair": pair, "channels": present,
            "bands": {c: list(bands) for c in present}, "why": why, "listen": LISTEN["tone"],
            "score": {"macro_rms_before": round(before, 2), "macro_rms_after": round(after, 2)},
            "needed": bool(bands)}


# ---------------------------------------------------------------- assembly
def propose(f, meas, targets, chains, roles, pairs, joints, ellipsoids=None, gates=None,
            allow_boost=False, routes=None):
    """All packages, in decision order. `pairs`: {name: [L, R]}. Returns the list."""
    ellipsoids = ellipsoids or {}
    gates = gates or {}
    out = []
    # Sequential on purpose, in the doctrine's order (phase_2_eq 2a -> 2c -> 2d): each package is
    # read on the curves AS THE EARLIER PACKAGES LEAVE THEM. Resonances first -- they are the
    # driver's own, medium-width -- or a +5 dB Q 4 peak on one side reads as a 2.5 dB L/R shape
    # difference and gets a broad cut it does not deserve; then the pair's shape; then the pair's
    # tone. The report says which packages each one assumes accepted.
    meas = {c: np.array(v, dtype=float) for c, v in meas.items()}
    groups = {}
    for code in meas:
        g = GROUP_OF_ROLE.get(str(roles.get(code, "")).lower())
        if g is None:
            g = "low" if P._is_sub(code) else ("high" if code.startswith("tw") else "mid")
        groups.setdefault(g, []).append(code)
    for g in ("low", "mid", "high"):
        if g in groups:
            pk = package_res(f, g, sorted(groups[g]), meas, targets, joints, ellipsoids, gates, allow_boost)
            out.append(pk)
            for code, bands in pk["bands"].items():
                meas[code] = _apply_bands(f, meas[code], bands)
    for name, members in pairs.items():
        pk = package_lr(f, name, members, meas, targets)
        if pk:
            pk["assumes"] = [p["id"] for p in out if p.get("needed")]
            out.append(pk)
            for code, bands in pk["bands"].items():
                meas[code] = _apply_bands(f, meas[code], bands)
    for name, members in pairs.items():
        pk = package_tone(f, name, members, meas, targets, ellipsoids)
        if pk:
            pk["assumes"] = [p["id"] for p in out if p.get("needed")]
            out.append(pk)
    for pk in out:
        pk["delta"] = to_delta(pk, chains, routes)
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


def merge_deltas(packages):
    delta = {}
    for pk in packages:
        for tier, rows in (pk.get("delta") or {}).items():
            for row, fields in rows.items():
                d = delta.setdefault(tier, {}).setdefault(row, {})
                d["eq"] = (d.get("eq") or []) + [b for b in fields.get("eq") or [] if b not in (d.get("eq") or [])]
    return delta


def render(packages):
    lines = ["  EQ proposals -- packages, in decision order (say yes or no to a package, not a band)", ""]
    for pk in packages:
        head = f"  [{pk['id']}]  " + ("PROPOSED" if pk.get("needed") else "nothing to do")
        if pk["kind"] == "lr":
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
        lines.append(f"      listen: {', '.join(pk['listen'])}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def _load_house(path):
    return target_bands.HouseCurve.from_file(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--solos", metavar="DIR", help="v7 solos (raw, protectives marked in the files)")
    src.add_argument("--rew", action="store_true", help="solos `<ch>_<ver> (sw)` from REW")
    ap.add_argument("--ver", default="1")
    ap.add_argument("--process", default=None, help="process dir for the round record (REW solos)")
    ap.add_argument("--house", metavar="FILE", help="the house curve (REW text)")
    ap.add_argument("--ellipsoid", metavar="DIR", default=None, help="v7 dir with `<code>-pN.json` positions")
    ap.add_argument("--route", action="append", default=[], metavar="VIRTUAL=out1,out2")
    ap.add_argument("--preset", default=None)
    ap.add_argument("--allow-boost", action="store_true")
    ap.add_argument("--accept", default=None, help="comma list of package ids to merge into eq-delta.json")
    ap.add_argument("--out", metavar="DIR", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
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
    if args.solos:
        loaded = P.load_solos_dir(args.solos, f)
        solos, notes, refused = P.de_embed_solos(loaded, f, baseline=True)
        for code, (_H, info) in loaded.items():
            try:
                doc = json.load(open(info["path"], encoding="utf-8"))
                g = gate_from_ir(doc["transferRealSamples"], doc["sampleRate"])
                if g is not None:
                    gates[code] = g
            except (OSError, KeyError, ValueError):
                pass
    else:
        import rew_api as api
        loaded = {}
        for code in chains:
            try:
                loaded[code] = P.load_solo_rew(f"{code}_{args.ver} (sw)", f, api=api)
            except (P.PredictError, KeyError) as e:
                print(f"  {code}: {e}", file=sys.stderr)
        record = None
        if args.process:
            from process import Process
            record = Process(args.process).protective_record_for(args.ver)
        solos, notes, refused = P.de_embed_solos(loaded, f, record=record, baseline=True)
    meas = {c: _db(H * P.chain_response(f, chains[c])) for c, H in solos.items()
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
                       allow_boost=args.allow_boost, routes=routes)
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
    assert lr["needed"] and lr["bands"]["m-R"] and not lr["bands"]["m-L"], lr
    assert lr["score"]["worst_lr_db_after"] <= LR_TOL_DB + 0.3 < lr["score"]["worst_lr_db_before"], lr["score"]
    assert all(b["q"] <= 1.0 and b["gain_db"] < 0 for b in lr["bands"]["m-R"]), lr["bands"]
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
    json.dump(list(pk.values()), open(os.path.join(tmp, "p.json"), "w"), default=float)
    print("selftest[eq_propose] OK -- a +5 dB Q4 resonance is cut where it is and only on its channel; a "
          "comb is not boosted and its dips are listed with the reason; a peak that MOVES in the "
          "ellipsoid is not proposed and one that STAYS is; a 2.5 dB shelf difference is cut on the louder "
          "side broadly (Q <= 1) into tolerance; a shared 2 dB hump moves both sides identically at the "
          "macro scale; deltas append to the row's bank and route broad moves to the virtual tier; the "
          "excess-phase gate built from an impulse allows a resonance and blocks a comb null.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
