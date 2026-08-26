#!/usr/bin/env python3
"""ellipsoid -- what STAYS and what MOVES across the positions around the head.

The six-point ear ellipsoid (Geddes; `diagnostic-techniques.md` §13) is captured hand-held as nine
sweeps per driver: p1 / p5 / p9 at the centre (the tripod point, returned to three times), p2-p4
and p6-p8 around it (±9 cm sideways, ±7 cm up/down). Averaging them gives the curve the literature
trusts; keeping them SEPARATE gives the thing averaging destroys -- whether a feature is a
property of the system (it stays put as the microphone moves) or of one position (it moves).
Measured 2026-08-20: a dip near 800 Hz sat at 800 / 818 / 800 Hz across the three centre returns
(scatter 1 %) and at 688...1080 Hz across the six positions (9-14 %) -- an order of magnitude
between the two, which is what makes this a verdict rather than a tendency.

Two things come out of it that the EQ decision needs (`eq_propose`):

  * **sigma(f)** -- the spread across positions at each frequency (1/6-oct smoothed). The
    tolerance for matching a target is not a constant: nothing smaller than 2*sigma(f) is worth
    a filter, because the measurement cannot tell it from where the microphone was.
  * **stays / moves per feature**, and from it the **Q ceiling per octave band**: the narrowest
    feature that survives the positions sets how narrow a corrective filter may be there
    (`diagnostic-techniques.md`, the Q-ceiling rule of 2026-08-22: narrowness, not frequency,
    predicts "this is the position, not the system"). Where no feature survives, the ceiling
    is the borrowed default Q <= 6 (DIMOSUS, #91) and the output SAYS it is borrowed.

    python3 rew_tool/ellipsoid.py --solos <v7 dir> --channel m-L [--json]
    python3 rew_tool/ellipsoid.py --rew --ver 49 --channel m-L        # titles `m-L p1_49 (sw)` ...

The protective filters are NOT taken out here: they are common to every position of a channel
and cancel in every comparison this module makes (a stays/moves verdict, a spread, a width).
Read-only towards REW.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import curve_view  # noqa: E402
import naming  # noqa: E402

POSITIONS = tuple(f"p{i}" for i in range(1, 10))
CENTRE = ("p1", "p5", "p9")           # the three returns to the tripod point
MIN_POSITIONS = 2                     # two positions is the old minimum (§13); six is the right number
SMOOTH_FRAC = 6                       # decisions are read at 1/6 oct (analysis-playbook)
STAY_PRESENT_FRACTION = 0.8           # the feature is there (same sign, >= half its depth) in this share
                                      # of the positions -- 5 of 6, the odd one being the hand
STAY_SIGMA_DB = 2.0                   # ...and its depth holds to this across them
Q_DEFAULT = 6.0                       # the borrowed ceiling where nothing measured sets one (#91)
Q_BANDS = ((20, 80), (80, 300), (300, 1200), (1200, 5000), (5000, 20000))
DRIFT_OK_DB = 1.0                     # centre returns further apart than this: the set is not one set
FMIN, FMAX, PPO = 20.0, 20000.0, 96


class EllipsoidError(ValueError):
    pass


# ---------------------------------------------------------------- loading
def grid(fmin=FMIN, fmax=FMAX, ppo=PPO):
    return fmin * 2.0 ** (np.arange(int(np.log2(fmax / fmin) * ppo) + 1) / ppo)


def load_positions_v7(directory, channel, freqs):
    """{position: complex H on freqs} from `<code>-pN.json` files (`m_L-p1.json` for `m-L`)."""
    import predict as P
    stem = channel.replace("-", "_")
    out = {}
    for pos in POSITIONS:
        path = os.path.join(directory, f"{stem}-{pos}.json")
        if os.path.isfile(path):
            H, _ = P.load_solo_v7(path, freqs)
            out[pos] = H
    if not out:
        raise EllipsoidError(f"{directory}: no `{stem}-p1..p9.json` files for {channel}")
    return out


def load_positions_rew(channel, version, freqs, api=None):
    """{position: complex H} from REW titles `<code> pN_<version> (sw)` (the capture sheet's form)."""
    import predict as P
    if api is None:
        import rew_api as api  # noqa: F811
    ms = api.get_measurements()
    have = {(m or {}).get("title") for m in ms.values()}
    out = {}
    for pos in POSITIONS:
        title = naming.generate_name(channel, version, "sw", position=pos)
        if title in have:
            H, _ = P.load_solo_rew(title, freqs, api=api)
            out[pos] = H
    if not out:
        raise EllipsoidError(f"REW holds no `{channel} p1.._{version} (sw)` titles")
    return out


# ---------------------------------------------------------------- the analysis
def _q_of_width(width_oct):
    """PEQ Q whose −3 dB bandwidth equals a feature `width_oct` octaves wide."""
    w = max(float(width_oct), 1e-6)
    return 1.0 / (2.0 ** (w / 2.0) - 2.0 ** (-w / 2.0))


def _distinct(positions):
    """The centre returns are ONE position (their mean); the rest are one each."""
    centre = [p for p in CENTRE if p in positions]
    others = [p for p in positions if p not in CENTRE]
    out = {}
    if centre:
        out["centre"] = np.mean([positions[p] for p in centre], axis=0)
    for p in others:
        out[p] = positions[p]
    return out, centre


def analyse(freqs, positions, band=(FMIN, FMAX), smooth_frac=SMOOTH_FRAC, min_prominence_db=2.0):
    """`positions`: {pN: mag_db on freqs (or complex H)}. Returns the report dict."""
    f = np.asarray(freqs, float)
    mags = {}
    for p, H in positions.items():
        H = np.asarray(H)
        mags[p] = 20.0 * np.log10(np.abs(H) + 1e-12) if np.iscomplexobj(H) else np.asarray(H, float)
    # Two scales, on purpose: the SPREAD (sigma, the band table, the centre drift) is read on the
    # 1/6-oct curves the method decides on; FEATURES are found and tracked on the 1/24-vs-1/3
    # residual `curve_view` defines them on (a 1/6 residual against 1/3 is nearly flat and hides
    # every mode -- the first draft found nothing on a real set for exactly that reason).
    views = {p: curve_view.multiscale(f, m, band, macro_frac=3, fine_frac=smooth_frac) for p, m in mags.items()}
    fine_views = {p: curve_view.multiscale(f, m, band, macro_frac=3, fine_frac=24) for p, m in mags.items()}
    g = next(iter(views.values()))["grid"]
    smooth = {p: v["fine"] for p, v in views.items()}
    distinct, centre = _distinct(smooth)
    n = len(distinct)
    notes = []
    if n < MIN_POSITIONS:
        notes.append(f"only {n} distinct position(s): no spread can be read -- two is the old minimum, "
                     f"six is the right number (§13)")
    stack = np.array(list(distinct.values()))
    mean = stack.mean(axis=0)
    sigma = stack.std(axis=0, ddof=1) if n > 1 else np.zeros_like(mean)

    # The centre returns against each other: the floor the spread is judged against.
    drift_db = None
    if len(centre) >= 2:
        c = np.array([smooth[p] for p in centre])
        drift_db = float(np.sqrt(np.mean((c - c.mean(axis=0)) ** 2)))
        if drift_db > DRIFT_OK_DB:
            notes.append(f"the centre returns disagree by {drift_db:.2f} dB rms (> {DRIFT_OK_DB:g}): the hand "
                         f"or the base moved during the set -- read the verdicts as rough")
    elif len(centre) == 1:
        notes.append("one centre sweep only: no floor for the spread (the sheet asks for three returns)")

    # Features on the MEAN curve (spatially averaged -> narrow features are real in space), then
    # each tracked through every position: does its centre stay, does its depth hold.
    raw_distinct, _ = _distinct({p: v["raw"] for p, v in views.items()})
    mean_raw = np.array(list(raw_distinct.values())).mean(axis=0)
    mean_view = curve_view.multiscale(g, mean_raw, band, macro_frac=3, fine_frac=24)
    feats = curve_view.find_features(mean_view, min_prominence_db=min_prominence_db, source="mmm")
    residuals = {p: v["residual"] for p, v in fine_views.items() if p in distinct or p in centre}
    for ft in feats:
        fc = ft["f_center"]
        sign = 1.0 if ft["kind"] == "peak" else -1.0
        # PRESENCE at the feature's own frequency, position by position: the residual within a
        # 24th of an octave of f_center, same sign and at least half the mean's depth. That is
        # what "a property of the system" means -- it is THERE wherever the microphone is. (A
        # first draft tracked the extremum inside a window and measured its frequency scatter:
        # too wide a window and a moving comb captures it, too narrow and nothing can scatter, so
        # every narrow spike "stayed". Presence cannot be gamed by the window.)
        near = (g >= fc / 2 ** (1 / 24)) & (g <= fc * 2 ** (1 / 24))
        wide = (g >= fc / 2 ** (1 / 6)) & (g <= fc * 2 ** (1 / 6))
        depths, fs = [], []
        series = [np.mean([residuals[p] for p in centre], axis=0)] if ("centre" in distinct) else []
        series += [residuals[p] for p in residuals if p not in CENTRE]
        for r in series:
            seg = r[near]
            depths.append(float(seg.max() if sign > 0 else seg.min()))
            segw = r[wide]
            k = int(np.argmax(segw)) if sign > 0 else int(np.argmin(segw))
            fs.append(float(g[wide][k]))
        depths = np.array(depths)
        present = (sign * depths >= 0.5 * abs(ft["extremum_db"]))
        e_sigma = float(np.std(depths, ddof=1)) if len(depths) > 1 else 0.0
        scatter = float(np.std(fs, ddof=1) / fc * 100.0) if len(fs) > 1 else 0.0
        # The depth must hold RELATIVE to the feature: a +2.3 dB spike whose depth wanders by 1.5 dB
        # across positions is noise wearing a peak's shape (a live set showed a dozen such "stays"
        # at 6/7 presence before this half-of-depth bound went in).
        stays = (n >= MIN_POSITIONS) and present.mean() >= STAY_PRESENT_FRACTION \
            and e_sigma <= min(STAY_SIGMA_DB, 0.5 * abs(ft["extremum_db"]))
        ft.update({"present_in": f"{int(present.sum())}/{len(depths)}", "depth_sigma_db": round(e_sigma, 2),
                   "scatter_pct": round(scatter, 1), "positions": len(depths), "stays": bool(stays),
                   "q_equiv": round(_q_of_width(ft["width_oct"]), 1),
                   "verdict": ("STAYS -- a property of the system (EQ may address it)" if stays else
                               "MOVES -- a property of the position (not for a filter)")})

    # The Q ceiling per octave band: the narrowest feature that STAYS sets it; else the borrowed default.
    ceilings = []
    for lo, hi in Q_BANDS:
        inside = [ft for ft in feats if ft["stays"] and lo <= ft["f_center"] < hi]
        if inside:
            narrowest = min(inside, key=lambda x: x["width_oct"])
            ceilings.append({"band": [lo, hi], "q_max": round(min(_q_of_width(narrowest["width_oct"]), 12.0), 1),
                             "from": f"{narrowest['kind']} @ {narrowest['f_center']:g} Hz, {narrowest['width_oct']:.2f} oct",
                             "measured": True})
        else:
            ceilings.append({"band": [lo, hi], "q_max": Q_DEFAULT, "from": "borrowed default (no staying feature here)",
                             "measured": False})

    return {"grid": g, "mean_db": mean, "sigma_db": sigma, "positions": sorted(positions),
            "distinct_positions": n, "centre_returns": centre, "centre_drift_db": drift_db,
            "features": feats, "q_ceiling": ceilings, "notes": notes,
            "bands": _band_table(g, mean, sigma)}


def _band_table(g, mean, sigma, per_octave=3):
    edges = FMIN * 2.0 ** (np.arange(int(np.log2(FMAX / FMIN) * per_octave) + 1) / per_octave)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (g >= lo) & (g < hi)
        if m.any():
            rows.append({"f_lo": round(float(lo), 1), "f_hi": round(float(hi), 1),
                         "mean_db": round(float(mean[m].mean()), 2), "sigma_db": round(float(sigma[m].mean()), 2),
                         "tolerance_db": round(max(1.0, 2.0 * float(sigma[m].mean())), 2)})
    return rows


def sigma_at(result, f_hz):
    """sigma(f) at one frequency, from the result -- the tolerance rule's input (max(1 dB, 2 sigma))."""
    return float(np.interp(np.log(f_hz), np.log(result["grid"]), result["sigma_db"]))


def q_ceiling_at(result, f_hz):
    for c in result["q_ceiling"]:
        if c["band"][0] <= f_hz < c["band"][1]:
            return float(c["q_max"]), bool(c["measured"])
    return Q_DEFAULT, False


def to_json(result):
    out = dict(result)
    out["grid"] = [round(float(v), 2) for v in result["grid"]]
    out["mean_db"] = [round(float(v), 3) for v in result["mean_db"]]
    out["sigma_db"] = [round(float(v), 3) for v in result["sigma_db"]]
    return out


def render(result, channel=""):
    lines = [f"  Ellipsoid {channel}: {result['distinct_positions']} distinct position(s) from "
             f"{len(result['positions'])} sweeps; centre returns {', '.join(result['centre_returns']) or 'none'}"
             + (f", drift {result['centre_drift_db']:.2f} dB rms" if result['centre_drift_db'] is not None else ""),
             ""]
    lines.append(f"  {'band Hz':>16}{'mean dB':>9}{'sigma':>8}{'tolerance':>11}")
    for b in result["bands"]:
        lines.append(f"  {b['f_lo']:>7.0f}-{b['f_hi']:<8.0f}{b['mean_db']:>9.2f}{b['sigma_db']:>8.2f}{b['tolerance_db']:>11.2f}")
    lines.append("")
    lines.append("  features on the mean curve, tracked through the positions:")
    for ft in result["features"]:
        lines.append(f"    {ft['kind']:4} {ft['f_center']:>8.1f} Hz  {ft['extremum_db']:+5.1f} dB  width {ft['width_oct']:.2f} oct "
                     f"(Q~{ft['q_equiv']:g})  present {ft['present_in']}  depth sigma {ft['depth_sigma_db']:.2f}  "
                     f"f scatter {ft['scatter_pct']:.1f} %  -> {ft['verdict']}")
    if not result["features"]:
        lines.append("    (none above the prominence threshold)")
    lines.append("")
    lines.append("  Q ceiling per band (the narrowest feature that STAYS; else the borrowed default):")
    for c in result["q_ceiling"]:
        lines.append(f"    {c['band'][0]:>6}-{c['band'][1]:<6}  Q <= {c['q_max']:g}   {c['from']}")
    for n in result["notes"]:
        lines.append(f"  note: {n}")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--solos", metavar="DIR", help="v7 files `<code>-pN.json`")
    src.add_argument("--rew", action="store_true", help="titles `<code> pN_<ver> (sw)` from REW")
    ap.add_argument("--ver", default=None, help="the `_N` of the REW titles")
    ap.add_argument("--channel", required=False, help="channel code, e.g. m-L")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.channel or not (args.solos or args.rew):
        ap.error("need --channel and a source (--solos DIR | --rew --ver N)")
    f = grid()
    if args.solos:
        positions = load_positions_v7(args.solos, args.channel, f)
    else:
        if not args.ver:
            ap.error("--rew needs --ver")
        positions = load_positions_rew(args.channel, args.ver, f)
    result = analyse(f, positions)
    if args.json:
        print(json.dumps(to_json(result), indent=1))
    else:
        print(render(result, args.channel))
    return 0


# ---------------------------------------------------------------- selftest
def _selftest():
    """Anchored to what the positions are DEFINED to do: a mode sits at one frequency in every
    position, a reflection comb moves with the microphone, a driver resonance stays."""
    import dsp_math
    f = grid()
    rng = np.random.default_rng(7)

    def position(offset_cm, jitter=0.3):
        # driver: gentle band; a cabin mode at 60 Hz (+6 dB, Q 8 -- modes below Schroeder are
        # sparse and narrow; a Q 4 hump reads as TONE on the 1/24-vs-1/3 ruler, residual 1.6 dB,
        # which is the ruler working) that stays; a driver resonance at 2 kHz (+5 dB, Q 6) that
        # stays; a floor-bounce comb whose first null moves with the path difference (0.50 m at
        # the centre, +offset): nulls at c/(2d) x (1, 3, 5...) = 343, 1029, 1715, 2401 Hz -- the
        # 2 kHz resonance sits BETWEEN nulls (a first draft used 0.43 m and put a null on it)
        H = (dsp_math.xo_response(f, 40.0, 12, "hp", "LR") * dsp_math.xo_response(f, 16000.0, 12, "lp", "LR")
             * dsp_math.peq_response(f, "PK", 60.0, 6.0, 8.0) * dsp_math.peq_response(f, "PK", 2000.0, 8.0, 6.0))
        d = 0.50 + offset_cm / 100.0
        tau = d / 343.0
        H = H * (1.0 + 0.5 * np.exp(-2j * np.pi * f * tau))          # one reflection, 0.5 relative
        mag = 20 * np.log10(np.abs(H)) + jitter * rng.standard_normal(f.size)
        return mag

    pos = {"p1": position(0.0), "p5": position(0.0), "p9": position(0.0),
           "p2": position(-4.0), "p3": position(-6.0), "p4": position(-2.0),
           "p6": position(+4.0), "p7": position(+6.0), "p8": position(+2.0)}
    r = analyse(f, pos)
    assert r["distinct_positions"] == 7 and r["centre_returns"] == ["p1", "p5", "p9"], r["distinct_positions"]
    assert r["centre_drift_db"] is not None and r["centre_drift_db"] < 0.5, r["centre_drift_db"]
    by = {}
    for ft in r["features"]:
        for name, fc in (("mode", 60.0), ("resonance", 2000.0)):
            if abs(np.log2(ft["f_center"] / fc)) < 1 / 6 and ft["kind"] == "peak":
                by[name] = ft
    assert "mode" in by and by["mode"]["stays"], by.get("mode")
    assert "resonance" in by and by["resonance"]["stays"], by.get("resonance")
    # the comb's first null sits at c/(2d): 343 Hz at the centre, moving 306..390 Hz across the
    # positions. On the MEAN it averages into a shallow, broad trough (that is what averaging is
    # for) -- so the claim is not "a dip is found", it is: NOTHING in that band STAYS, and the
    # spread sigma(f) there is several times what it is where the mode sits still.
    assert not [ft for ft in r["features"] if ft["stays"] and 250 <= ft["f_center"] <= 450], \
        [ft for ft in r["features"] if 250 <= ft["f_center"] <= 450]
    s_mode, s_comb = sigma_at(r, 60.0), sigma_at(r, 343.0)
    assert s_comb > 2 * s_mode, (s_mode, s_comb)
    # the Q ceiling in 1200-5000 comes from the 2 kHz resonance's own width, measured -- and the
    # band 300-1200 (only a MOVING dip) falls back to the borrowed default and says so
    q_hi, measured_hi = q_ceiling_at(r, 2000.0)
    assert measured_hi and 3.0 <= q_hi <= 12.0, (q_hi, measured_hi)
    q_mid, measured_mid = q_ceiling_at(r, 600.0)
    assert not measured_mid and q_mid == Q_DEFAULT, (q_mid, measured_mid)
    # a set with one position only cannot say anything, and says that
    r1 = analyse(f, {"p1": pos["p1"]})
    assert r1["distinct_positions"] == 1 and any("no spread" in n for n in r1["notes"]), r1["notes"]
    assert all(not ft["stays"] for ft in r1["features"])
    txt = render(r, "m-L")
    assert "STAYS" in txt and "borrowed default" in txt and "MOVES" in render(r1, "m-L")
    json.dumps(to_json(r))
    print("selftest[ellipsoid] OK -- three centre returns read as one position with a drift floor; a 60 Hz "
          "mode and a 2 kHz resonance STAY, a floor-bounce comb MOVES with the microphone and says so; "
          "sigma(f) is larger where the comb moves; the Q ceiling is measured from the staying resonance "
          "where one exists and borrowed (and said) where not; one position alone reads no spread.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
