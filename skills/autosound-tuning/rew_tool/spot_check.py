"""Independent spot-check of a model's cited numbers against live REW data.

The cheapest process-control habit (see references/core/process-control.md §2.3):
before applying a proposed package, read the SAME numbers the proposal cites —
levels at the cited frequencies, the L−R delta, the ACTUAL peak in a band vs the
claimed one, optionally the anchored deviation vs a target. Field-proven double
duty: it CONFIRMS honest numbers (a real run matched to the hundredth) and
CATCHES slips (a cut aimed at 2450 Hz when the measured peak sat at 2202 Hz).

Reads magnitude only (RTA-safe). Measurement titles are resolved by NAME right
before the pull (rew-api-quirks: ordinal ids are not stable).

CLI (REW running on :4735):
  python spot_check.py "L_09 (rta)" "R_09 (rta)" --at 160,2540 --peak 2000-3000 --claim 2543.8
  python spot_check.py "ALL_09 (rta)" --target "Jazzi_0db_REW" --at 2540 --anchor 300-3000
  python spot_check.py --selftest
"""
import argparse
import sys


def level_at(freqs, mag, f):
    """Magnitude at the bin nearest to f."""
    i = min(range(len(freqs)), key=lambda k: abs(freqs[k] - f))
    return mag[i]


def band_peak(freqs, mag, lo, hi):
    """(freq, level) of the maximum inside [lo, hi]."""
    best = None
    for f, m in zip(freqs, mag):
        if lo <= f <= hi and (best is None or m > best[1]):
            best = (f, m)
    return best


def pair_report(freqs_a, mag_a, freqs_b, mag_b, at_freqs, peak_band=None,
                claimed_peak_hz=None):
    """L-vs-R style numbers for two traces on their own grids."""
    rows = []
    for f in at_freqs:
        a = level_at(freqs_a, mag_a, f)
        b = level_at(freqs_b, mag_b, f)
        rows.append({"hz": f, "a_db": round(a, 2), "b_db": round(b, 2),
                     "delta_db": round(a - b, 2)})
    out = {"points": rows}
    if peak_band:
        pk = band_peak(freqs_a, mag_a, *peak_band)
        out["a_peak"] = {"hz": round(pk[0], 1), "db": round(pk[1], 2)}
        if claimed_peak_hz:
            off_oct = abs(_log2(pk[0] / claimed_peak_hz))
            out["a_peak"]["claimed_hz"] = claimed_peak_hz
            out["a_peak"]["claim_off_octaves"] = round(off_oct, 3)
            out["a_peak"]["claim_ok"] = off_oct <= 1.0 / 12.0   # within 1/12 oct
    return out


def target_report(freqs, mag, t_freqs, t_mag, at_freqs, anchor_band=(300.0, 3000.0)):
    """Shape-anchored deviation vs a target at the cited frequencies."""
    from target_curves import interpolate_target
    from joint_analysis import midband_level_anchor
    t_on_grid = interpolate_target(t_freqs, t_mag, freqs)
    anchor = midband_level_anchor(freqs, mag, t_on_grid, anchor_band)
    rows = []
    for f in at_freqs:
        i = min(range(len(freqs)), key=lambda k: abs(freqs[k] - f))
        rows.append({"hz": f,
                     "deviation_db": round((mag[i] - t_on_grid[i]) - anchor, 2)})
    return {"anchor_db": anchor, "anchor_band": list(anchor_band), "points": rows}


def _log2(x):
    import math
    return math.log2(x)


def _fetch(title):
    import rew_api
    mid, _ = rew_api.get_measurement_by_name(title)
    freqs, mag, _phase = rew_api.get_fr(mid)
    return freqs, mag


def _parse_freqs(s):
    return [float(x) for x in s.split(",") if x.strip()]


def _parse_band(s):
    lo, hi = s.split("-")
    return (float(lo), float(hi))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Spot-check cited numbers against live REW.")
    ap.add_argument("names", nargs="*", help="measurement title (1) or pair A B (2)")
    ap.add_argument("--at", default="", help="comma list of frequencies to read, e.g. 160,2540")
    ap.add_argument("--peak", default=None, help="band lo-hi to locate the actual peak, e.g. 2000-3000")
    ap.add_argument("--claim", type=float, default=None, help="the claimed peak frequency to verify")
    ap.add_argument("--target", default=None, help="target measurement title for anchored deviation")
    ap.add_argument("--anchor", default="300-3000", help="anchor band for --target (default 300-3000)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        _selftest()
        return

    at = _parse_freqs(a.at) if a.at else []
    if len(a.names) == 2:
        fa, ma = _fetch(a.names[0])
        fb, mb = _fetch(a.names[1])
        rep = pair_report(fa, ma, fb, mb, at,
                          peak_band=_parse_band(a.peak) if a.peak else None,
                          claimed_peak_hz=a.claim)
        print(f"== {a.names[0]}  vs  {a.names[1]} ==")
        for r in rep["points"]:
            print(f"{r['hz']:>7.0f} Hz:  A={r['a_db']:7.2f}  B={r['b_db']:7.2f}  A-B={r['delta_db']:+6.2f} dB")
        if "a_peak" in rep:
            p = rep["a_peak"]
            line = f"A peak {a.peak}: {p['db']:.2f} dB @ {p['hz']:.0f} Hz"
            if "claimed_hz" in p:
                line += (f"   claimed {p['claimed_hz']:.0f} Hz -> "
                         f"{'OK' if p['claim_ok'] else 'OFF by %.2f oct' % p['claim_off_octaves']}")
            print(line)
    elif len(a.names) == 1 and a.target:
        f, m = _fetch(a.names[0])
        tf, tm = _fetch(a.target)
        rep = target_report(f, m, tf, tm, at, _parse_band(a.anchor))
        print(f"== {a.names[0]} vs target {a.target} (anchored {a.anchor}, offset {rep['anchor_db']:+.2f} dB) ==")
        for r in rep["points"]:
            print(f"{r['hz']:>7.0f} Hz:  deviation {r['deviation_db']:+6.2f} dB")
    else:
        ap.print_help()
        sys.exit(2)


def _selftest():
    freqs = [20.0 * (10 ** (k * 3.0 / 255)) for k in range(256)]

    # pair: B = A - 3 dB everywhere; A has a +6 bump near 2200
    a = [0.0] * len(freqs)
    for k, f in enumerate(freqs):
        if 2000 <= f <= 2400:
            a[k] = 6.0
    b = [v - 3.0 for v in a]
    rep = pair_report(freqs, a, freqs, b, [160, 2200], peak_band=(2000, 3000),
                      claimed_peak_hz=2543.8)
    assert rep["points"][0]["delta_db"] == 3.0, rep["points"][0]
    assert rep["points"][1]["delta_db"] == 3.0
    assert 2000 <= rep["a_peak"]["hz"] <= 2400, rep["a_peak"]
    assert rep["a_peak"]["claim_ok"] is False, "2543.8 claim must be flagged OFF"
    rep2 = pair_report(freqs, a, freqs, b, [], peak_band=(2000, 3000),
                       claimed_peak_hz=rep["a_peak"]["hz"])
    assert rep2["a_peak"]["claim_ok"] is True

    # target: measured = target + 4 flat -> anchored deviation ~0 at any point
    tgt = [-2.0] * len(freqs)
    meas = [2.0] * len(freqs)
    tr = target_report(freqs, meas, freqs, tgt, [500, 2540])
    assert abs(tr["anchor_db"] - 4.0) < 1e-6, tr
    assert all(abs(r["deviation_db"]) < 0.01 for r in tr["points"]), tr

    # level_at nearest-bin
    assert level_at([100, 200, 300], [1.0, 5.0, 2.0], 210) == 5.0

    print("selftest OK -- pair deltas +3.00; peak found in-band, false claim "
          f"(2543.8 vs {rep['a_peak']['hz']}) flagged OFF by "
          f"{rep['a_peak']['claim_off_octaves']} oct, true claim OK; "
          "anchored deviation ~0 on a flat offset")


if __name__ == "__main__":
    main()
