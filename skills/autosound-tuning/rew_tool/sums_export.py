#!/usr/bin/env python3
"""sums_export -- the predicted sums as curves the target-curve visualizer draws beside the target.

A variant is chosen on what it will sound like, and a number does not say that; a curve beside the
target does (the user, 2026-09-17: "numbers do not help me much ... a picture of the sum, where it
can help, beside the target with 1/6 or psychoacoustic smoothing"). `predict --out DIR` leaves
`predicted.json` with the sums on a 96-per-octave grid; this writes each of them -- ALL, L, R, and
ALL+C where a centre was summed -- as a REW-style text file the visualizer accepts on a drop
(`references/patterns/target-curves/target_curves_visualizer.html`: `# NTT: Name - ...` names the
curve, then `frequency dB` lines), smoothed the way a person would look at it:

  * `1/6` (the default), `1/3`, `1/12`, `1/24`, `1/48` -- a Gaussian of that width in octaves, in dB,
    the same kernel `curve_view` uses for its scales;
  * `psy` -- REW's psychoacoustic smoothing as it documents it: 1/3 octave below 100 Hz, 1/6 above
    1 kHz, between them in between (log-interpolated), and a CUBIC mean of the amplitude so peaks
    weigh more than dips -- what the ear is said to read;
  * `none` -- the grid as predicted.

Each file carries the variant's label in its name, so two variants dropped together are two lines
the visualizer levels to one another (its own 200-500 Hz reference). The file says which smoothing
it carries: a curve compared at another smoothing is a different curve.

    python3 rew_tool/sums_export.py --predicted DIR/predicted.json --out DIR/curves [--label v_012]
                                    [--smoothing 1/6|psy|none] [--ppo 24] [--curves ALL,L,R]
    python3 rew_tool/sums_export.py --selftest

Deps: numpy (through `curve_view`).
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

import curve_view  # noqa: E402

SMOOTHINGS = ("1/3", "1/6", "1/12", "1/24", "1/48", "psy", "none")
#: REW's psychoacoustic smoothing as its help states it: 1/3 octave below 100 Hz, 1/6 above 1 kHz,
#: varying between, and a cubic mean (docs/RESEARCH-2026-09-17-reader-smoothing.md §4).
PSY_LOW_HZ, PSY_LOW_OCT = 100.0, 1.0 / 3.0
PSY_HIGH_HZ, PSY_HIGH_OCT = 1000.0, 1.0 / 6.0
PPO = curve_view.PPO


def _grid(lo=20.0, hi=20000.0):
    return np.geomspace(lo, hi, int(round(math.log2(hi / lo) * PPO)) + 1)


def psy_width_oct(f):
    """The psychoacoustic window width in octaves at f."""
    f = float(f)
    if f <= PSY_LOW_HZ:
        return PSY_LOW_OCT
    if f >= PSY_HIGH_HZ:
        return PSY_HIGH_OCT
    t = math.log(f / PSY_LOW_HZ) / math.log(PSY_HIGH_HZ / PSY_LOW_HZ)
    return PSY_LOW_OCT + t * (PSY_HIGH_OCT - PSY_LOW_OCT)


def smooth(freqs, mag_db, smoothing):
    """`mag_db` smoothed on a 96-per-octave log grid; returns (grid, smoothed_db)."""
    if smoothing not in SMOOTHINGS:
        raise ValueError(f"smoothing must be one of {SMOOTHINGS}, not {smoothing!r}")
    f = np.asarray(freqs, dtype=float)
    y = np.asarray(mag_db, dtype=float)
    g = _grid(float(f[0]), float(f[-1]))
    yg = np.interp(g, f, y)
    if smoothing == "none":
        return g, yg
    if smoothing != "psy":
        return g, curve_view._smooth_frac(yg, float(smoothing.split("/")[1]))
    amp3 = (10.0 ** (yg / 20.0)) ** 3
    csum = np.concatenate([[0.0], np.cumsum(amp3)])
    out = np.empty_like(yg)
    n = yg.size
    for i, fc in enumerate(g):
        half = psy_width_oct(fc) * PPO / 2.0
        lo, hi = max(0, int(round(i - half))), min(n, int(round(i + half)) + 1)
        out[i] = 20.0 * math.log10(max(((csum[hi] - csum[lo]) / (hi - lo)) ** (1.0 / 3.0), 1e-12))
    return g, out


def curves_of(predicted):
    """{name: mag_db list} for every sum `predicted.json` carries, on its own grid."""
    out = {"ALL": predicted["all_mag_db"]}
    for side, v in (predicted.get("sides") or {}).items():
        out[side] = v["sum_mag_db"]
    if predicted.get("all_plus_c_mag_db") is not None:
        out["ALL+C"] = predicted["all_plus_c_mag_db"]
    return out


def rew_text(name, freqs, mag_db, smoothing, note=None, ppo=24):
    """A REW-style text curve the visualizer names from its header, decimated to `ppo`."""
    step = max(1, int(round(PPO / ppo)))
    lines = [f"# NTT: Name - {name}", f"# smoothing: {smoothing}", "# from predicted.json (sums_export.py)"]
    if note:
        lines.append(f"# {note}")
    lines.append("# Frequency(Hz) Magnitude(dB)")
    lines += [f"{float(f):.2f} {float(d):.2f}" for f, d in zip(freqs[::step], mag_db[::step])]
    return "\n".join(lines) + "\n"


def export(predicted, out_dir, label, smoothing="1/6", ppo=24, wanted=None):
    """Write one file per sum; returns [(name, path)]."""
    os.makedirs(out_dir, exist_ok=True)
    f = predicted["freqs_hz"]
    note = None
    if predicted.get("window"):
        note = f"junctions read {predicted['window']}; the sums are the whole record"
    written = []
    for curve, mag in curves_of(predicted).items():
        if wanted and curve not in wanted:
            continue
        g, y = smooth(f, mag, smoothing)
        name = f"{curve} {label} ({smoothing})"
        fname = f"{curve.replace('+', 'plus')}_{label}_{smoothing.replace('/', '-')}.txt"
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(rew_text(name, g, y, smoothing, note, ppo))
        written.append((name, path))
    return written


# ---------------------------------------------------------------- selftest
def _selftest():
    import tempfile
    import target_curves
    g = _grid()
    flat = 80.0 * np.ones_like(g)

    def bell(f0, gain, q):
        return gain / (1.0 + (q * (g / f0 - f0 / g)) ** 2)      # a peaking bell, in dB, good enough here
    y = flat + bell(2000.0, 6.0, 10.0) + bell(45.0, 6.0, 10.0) - bell(400.0, 4.0, 10.0)
    at = lambda arr, f: float(arr[np.argmin(np.abs(g - f))])   # noqa: E731

    # none: what went in comes out
    _, y0 = smooth(g, y, "none")
    assert np.allclose(y0, y), "none must not touch the curve"
    # 1/6: a Q 10 bell keeps roughly two thirds of its height (the retention table of the research)
    _, y6 = smooth(g, y, "1/6")
    kept = (at(y6, 2000.0) - 80.0) / 6.0
    assert 0.5 < kept < 0.85, kept
    # 1/48 keeps almost all of it, 1/3 less than 1/6
    _, y48 = smooth(g, y, "1/48")
    _, y3 = smooth(g, y, "1/3")
    assert (at(y48, 2000.0) - 80.0) / 6.0 > 0.95 and at(y3, 2000.0) < at(y6, 2000.0)
    # psy: wider in the bass than in the treble -- the same bell keeps less at 45 Hz than at 2 kHz;
    # and the cubic mean weighs a peak more than a dip of the same size
    _, yp = smooth(g, y, "psy")
    assert (at(yp, 45.0) - 80.0) < (at(yp, 2000.0) - 80.0), (at(yp, 45.0), at(yp, 2000.0))
    _, yp_peak = smooth(g, flat + bell(400.0, 4.0, 10.0), "psy")
    _, yp_dip = smooth(g, flat - bell(400.0, 4.0, 10.0), "psy")
    assert (at(yp_peak, 400.0) - 80.0) > (80.0 - at(yp_dip, 400.0)), "a cubic mean favours the peak"
    assert abs(psy_width_oct(50.0) - 1 / 3) < 1e-9 and abs(psy_width_oct(4000.0) - 1 / 6) < 1e-9
    assert 1 / 6 < psy_width_oct(316.0) < 1 / 3
    try:
        smooth(g, y, "1/7")
        raise AssertionError("an unknown smoothing was accepted")
    except ValueError:
        pass

    # the files: one per sum, named for the visualizer, read back by the skill's own reader
    predicted = {"freqs_hz": [float(v) for v in g], "all_mag_db": [float(v) for v in y],
                 "sides": {"L": {"members": ["w-L"], "sum_mag_db": [float(v) for v in y - 3.0]},
                           "R": {"members": ["w-R"], "sum_mag_db": [float(v) for v in y - 3.5]}},
                 "window": "gate"}
    with tempfile.TemporaryDirectory() as d:
        written = export(predicted, d, "v_012", "1/6", ppo=24)
        assert [n for n, _ in written] == ["ALL v_012 (1/6)", "L v_012 (1/6)", "R v_012 (1/6)"], written
        fr, mg = target_curves.load_target_curve(written[0][1])
        assert 200 < len(fr) < 260, len(fr)                                   # ~10 octaves at 24 per octave
        assert abs(mg[np.argmin(np.abs(np.array(fr) - 2000.0))] - at(y6, 2000.0)) < 0.3
        text = open(written[0][1], encoding="utf-8").read()
        assert text.startswith("# NTT: Name - ALL v_012 (1/6)\n# smoothing: 1/6\n") and "junctions read gate" in text
        only = export(predicted, d, "v_013", "psy", wanted=("L",))
        assert [n for n, _ in only] == ["L v_013 (psy)"], only
        withc = export(dict(predicted, all_plus_c_mag_db=[float(v) for v in y + 1.0]), d, "v_014", "none")
        assert any(n.startswith("ALL+C ") for n, _ in withc) and os.path.basename(withc[-1][1]).startswith("ALLplus")
    print("selftest[sums_export] OK -- a Q 10 bell keeps ~2/3 at 1/6, nearly all at 1/48, less at 1/3; psy is "
          "1/3 wide in the bass and 1/6 in the treble and its cubic mean favours a peak over a dip; each sum is "
          "one visualizer file, named in its header, read back by target_curves; ALL+C only when it was summed")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predicted", metavar="FILE", help="predicted.json from `predict --out DIR`")
    ap.add_argument("--out", metavar="DIR", help="where the curve files go")
    ap.add_argument("--label", default=None, help="the variant's label in every file (default: the json's folder)")
    ap.add_argument("--smoothing", default="1/6", choices=SMOOTHINGS)
    ap.add_argument("--ppo", type=int, default=24, help="points per octave in the files (default 24)")
    ap.add_argument("--curves", default=None, help="comma list of ALL,L,R,ALL+C (default: every sum present)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.predicted or not a.out:
        ap.error("need --predicted FILE and --out DIR")
    with open(a.predicted, encoding="utf-8") as fh:
        predicted = json.load(fh)
    label = a.label or os.path.basename(os.path.dirname(os.path.abspath(a.predicted))) or "predicted"
    wanted = tuple(s.strip() for s in a.curves.split(",")) if a.curves else None
    for name, path in export(predicted, a.out, label, a.smoothing, a.ppo, wanted):
        print(f"  {name:28} -> {path}")
    print("  drop them into the target-curve visualizer beside the target; the picture, not the number, is the argument")
    return 0


if __name__ == "__main__":
    sys.exit(main())
