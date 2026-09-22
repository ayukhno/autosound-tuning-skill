"""compare -- two or more REW measurements side by side, at named frequencies and over a named band (#58 P9).

The Antigravity session compared curves with `python -c` one-liners, and four of them failed on
PowerShell's quoting before one ran. What it needed is one command with the questions a comparison
asks as flags:

    python3 rew_tool/compare.py --titles "w-L_51 (rta)" "w-R_51 (rta)" --at 60,125,250,500
    python3 rew_tool/compare.py --titles "ALL_51 (rta)" --target curves/house.txt --band 40-16000

Every number says what it is: the smoothing it was read at (REW computes it on the way out and the
measurement's own view is left alone, hub TCC-015), and an RMS says over which band, with the level
taken out when a target is the reference (a target is a SHAPE, `naming-and-structure.md` §6).
"""

from __future__ import annotations

import argparse
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _log_interp(freqs, values, hz):
    """The value at `hz`, interpolated on log frequency; None outside the data."""
    if not freqs or hz < freqs[0] or hz > freqs[-1]:
        return None
    lo, hi = 0, len(freqs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if freqs[mid] <= hz:
            lo = mid
        else:
            hi = mid
    f0, f1 = freqs[lo], freqs[hi]
    if f1 == f0:
        return values[lo]
    t = (math.log(hz) - math.log(f0)) / (math.log(f1) - math.log(f0))
    return values[lo] + t * (values[hi] - values[lo])


def band_stats(freqs, mag, lo, hi, reference=None):
    """`{"mean", "rms_vs", "points"}` over [lo, hi], read on a log grid so each octave has the same say: the mean
    of the dB, and against `reference` (`[(hz, db)]`) the RMS of the difference with its mean removed."""
    grid = [lo * (hi / lo) ** (i / 95.0) for i in range(96)]
    own = [_log_interp(freqs, mag, f) for f in grid]
    pts = [(f, v) for f, v in zip(grid, own) if v is not None]
    if len(pts) < 3:
        return None
    mean = sum(v for _, v in pts) / len(pts)
    out = {"mean": mean, "points": len(pts), "rms_vs": None}
    if reference:
        rf = [h for h, _ in reference]
        rv = [d for _, d in reference]
        diff = [v - r for (f, v) in pts if (r := _log_interp(rf, rv, f)) is not None]
        if len(diff) >= 3:
            m = sum(diff) / len(diff)
            out["rms_vs"] = math.sqrt(sum((d - m) ** 2 for d in diff) / len(diff))
    return out


def compare(curves, at=(), band=None, target=None):
    """`curves`: `{title: (freqs, mag)}`. Returns rows for the table and the band lines, as data."""
    rows = []
    for hz in at:
        vals = {t: _log_interp(f, m, hz) for t, (f, m) in curves.items()}
        rows.append({"hz": hz, "db": vals})
    bands = {}
    if band:
        first = next(iter(curves))
        ref_curve = list(zip(*curves[first])) if len(curves) > 1 and not target else None
        for title, (f, m) in curves.items():
            reference = target if target else (ref_curve if title != first else None)
            bands[title] = band_stats(f, m, band[0], band[1], reference)
    return {"rows": rows, "bands": bands}


def render(result, titles, smoothing, band=None, target_name=None):
    lines = [f"  read at {smoothing} smoothing (computed by REW on the way out; the view is untouched)"]
    if result["rows"]:
        lines.append("  " + f"{'Hz':>8}  " + "  ".join(f"{t[:22]:>22}" for t in titles)
                     + ("  " + f"{'2nd - 1st':>10}" if len(titles) == 2 else ""))
        for r in result["rows"]:
            vals = [r["db"][t] for t in titles]
            cells = "  ".join(f"{'--' if v is None else f'{v:.1f} dB':>22}" for v in vals)
            delta = ""
            if len(titles) == 2 and None not in vals:
                delta = f"  {vals[1] - vals[0]:>+9.1f} dB"
            lines.append(f"  {r['hz']:>8g}  {cells}{delta}")
    if band and result["bands"]:
        ref = f"against {target_name}" if target_name else f"against {titles[0]}"
        for title in titles:
            b = result["bands"].get(title)
            if not b:
                lines.append(f"  {title}: no points in {band[0]:g}-{band[1]:g} Hz")
                continue
            rms = ("" if b["rms_vs"] is None
                   else f"; RMS {ref}, level removed: {b['rms_vs']:.2f} dB")
            lines.append(f"  {title}: {band[0]:g}-{band[1]:g} Hz, log-weighted mean {b['mean']:.1f} dB{rms}")
    return "\n".join(lines)


def _selftest():
    f = [20.0 * 2 ** (i / 24.0) for i in range(240)]
    a = [80.0 for _ in f]
    b = [80.0 + (3.0 if 200 <= x <= 400 else 0.0) for x in f]
    res = compare({"a": (f, a), "b": (f, b)}, at=(100.0, 300.0), band=(100.0, 1000.0))
    assert abs(res["rows"][1]["db"]["b"] - 83.0) < 0.2 and abs(res["rows"][0]["db"]["b"] - 80.0) < 0.2, res
    assert res["bands"]["a"]["rms_vs"] is None and res["bands"]["b"]["rms_vs"] > 0.5, res["bands"]
    shown = render(res, ["a", "b"], "1/6", band=(100.0, 1000.0))
    assert "+3.0 dB" in shown and "level removed" in shown and "1/6" in shown, shown
    flat = compare({"a": (f, a)}, band=(40.0, 16000.0), target=[(20.0, 5.0), (20000.0, 5.0)])
    assert abs(flat["bands"]["a"]["rms_vs"]) < 1e-9, "a target is a shape: a level offset is not an error"
    print("selftest[compare] OK -- values at named frequencies with the difference, a band's log-weighted mean, "
          "the RMS against a target or the first curve with the level removed, and the smoothing named")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="REW measurements side by side (#58 P9)")
    ap.add_argument("--titles", nargs="+", help="the measurement titles, as REW holds them")
    ap.add_argument("--at", default="", help="comma list of frequencies (Hz)")
    ap.add_argument("--band", default=None, help="lo-hi (Hz) for the band lines")
    ap.add_argument("--target", default=None, help="a REW-style text curve; the band's RMS is taken against it")
    ap.add_argument("--smoothing", default="1/6", help="what REW computes on the way out (default 1/6)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.titles:
        ap.error("--titles is required")
    import rew_api
    import variant_front
    curves = {}
    for title in args.titles:
        mid = rew_api.find_measurement_id(title)
        if mid is None:
            print(f"refusing: REW holds no measurement titled {title!r}", file=sys.stderr)
            return 3
        freqs, mag, _phase = rew_api.get_fr(mid, smoothing=args.smoothing)
        curves[title] = (list(freqs), list(mag))
    at = [float(x) for x in args.at.split(",") if x.strip()]
    band = tuple(float(x) for x in args.band.split("-")) if args.band else None
    target = variant_front.read_target(args.target) if args.target else None
    print(render(compare(curves, at=at, band=band, target=target), args.titles, args.smoothing, band=band,
                 target_name=os.path.basename(args.target) if args.target else None))
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    raise SystemExit(main())
