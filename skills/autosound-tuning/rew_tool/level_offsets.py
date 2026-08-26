"""Preliminary per-channel LEVEL offsets from geometry (off-axis directivity + distance).

A physics-grounded STARTING level balance for Phase 1 — a hypothesis to verify by
RTA/ear, not a final answer. Ports the method Gemini used on the Passat B8, generalized:
inputs are PROJECT data (ask the user), nothing car-specific is baked in.

Model per channel:
  * off-axis loss  = band-averaged far-field piston directivity  D(f,θ) = 2·J1(kasinθ)/(kasinθ)
  * distance loss  = 10·n·log10(d)     (n=2 → inverse-square/free field; n<2 in a live cabin)
  * delivered      = −distance_loss − offaxis_loss   (louder = higher)
  * offset (apply) = min(delivered) − delivered      (≤ 0, CUT-ONLY; loudest driver cut most)

INPUTS (per driver, all PROJECT data — ask the user, store in autosound_context.md):
  d      — path distance driver→reference ear (m)
  theta  — off-axis angle between the driver's aim and the ear direction (deg)
  a      — effective piston radius (m) ≈ cone/dome radius (enclosure sets the LF band edge)
  band   — (f_min, f_max) the driver's working band (from the crossovers)
  n      — distance attenuation exponent (default 2.0; lower it if the cabin is reverberant)

stdlib-only. Self-test: `python3 level_offsets.py --selftest`.
"""
from __future__ import annotations
import math
import sys
from dataclasses import dataclass

C_AIR = 343.0  # m/s


def bessj1(x: float) -> float:
    """Bessel function of the first kind, order 1 (Numerical Recipes rational approx, ~1e-7)."""
    ax = abs(x)
    if ax < 8.0:
        y = x * x
        p1 = x * (72362614232.0 + y * (-7895059235.0 + y * (242396853.1 + y * (
            -2972611.439 + y * (15704.48260 + y * (-30.16036606))))))
        p2 = 144725228442.0 + y * (2300535178.0 + y * (18583304.74 + y * (
            99447.43394 + y * (376.9991397 + y * 1.0))))
        return p1 / p2
    z = 8.0 / ax
    y = z * z
    xx = ax - 2.356194491
    p1 = 1.0 + y * (0.183105e-2 + y * (-0.3516396496e-4 + y * (0.2457520174e-5 + y * (-0.240337019e-6))))
    p2 = 0.04687499995 + y * (-0.2002690873e-3 + y * (0.8449199096e-5 + y * (-0.88228987e-6 + y * 0.105787412e-6)))
    ans = math.sqrt(0.636619772 / ax) * (math.cos(xx) * p1 - z * math.sin(xx) * p2)
    return -ans if x < 0.0 else ans


def directivity(f: float, theta_deg: float, a: float, c: float = C_AIR) -> float:
    """Far-field circular-piston directivity magnitude D(f,θ) ∈ (0, 1]. On-axis (θ=0) → 1."""
    x = (2.0 * math.pi * f / c) * a * math.sin(math.radians(theta_deg))
    if abs(x) < 1e-9:
        return 1.0
    return abs(2.0 * bessj1(x) / x)


def band_offaxis_loss_db(f_min: float, f_max: float, theta_deg: float, a: float,
                         c: float = C_AIR, npts: int = 60) -> float:
    """Band-averaged off-axis loss (dB, ≥ 0). Log-spaced average over the driver's band."""
    if theta_deg == 0.0 or a == 0.0:
        return 0.0
    lo, hi = math.log10(f_min), math.log10(f_max)
    vals = []
    for i in range(npts):
        f = 10.0 ** (lo + (hi - lo) * i / (npts - 1))
        vals.append(20.0 * math.log10(directivity(f, theta_deg, a, c)))
    return -sum(vals) / len(vals)  # losses are negative dB → return positive loss


def distance_loss_db(d: float, n: float = 2.0) -> float:
    """Distance attenuation (dB, relative). n=2 → 20·log10(d) (6 dB/doubling)."""
    return 10.0 * n * math.log10(d)


@dataclass
class Driver:
    name: str
    d: float                 # distance to ear (m)
    theta: float             # off-axis angle (deg)
    a: float                 # piston radius (m)
    band: tuple[float, float]  # (f_min, f_max) Hz


def compute_offsets(drivers: list[Driver], n: float = 2.0, c: float = C_AIR) -> dict[str, float]:
    """Cut-only per-channel offsets (dB, ≤ 0), normalized so the quietest driver = 0."""
    delivered = {}
    for dr in drivers:
        oa = band_offaxis_loss_db(dr.band[0], dr.band[1], dr.theta, dr.a, c)
        delivered[dr.name] = -distance_loss_db(dr.d, n) - oa
    floor = min(delivered.values())
    return {name: round(floor - lvl, 1) for name, lvl in delivered.items()}


# ── the SECOND estimate: levels read off the measurement ──────────────────────
# The geometry above is a hypothesis from distances and angles. The measurement knows what the
# cabin actually did to them -- boundary gain, a door that loads a woofer, an off-axis tweeter
# firing into glass -- and none of that is in d and theta. Two independent estimates that agree
# are worth far more than either alone; when they DISAGREE, that disagreement is the finding, and
# it usually names an install problem rather than a level to type in.
#
# One precondition, and it is the reason this is not automatic: every channel must have been swept
# at the SAME REW output level and the same head-unit level, knobs untouched (the capture sheet's
# 0.2, `phases/capture-session-sheet.md`). If the levels moved between sweeps, these numbers
# compare the knob, not the car. Nothing in a v7 file records the knob, so the caller asserts it.

def band_level_db(freqs, mag_db, f_min, f_max):
    """Energy-average level (dB) of one channel inside its own band.

    Energy average, not an average of decibels: doubling the power in half the band must show as
    +3 dB, which an arithmetic mean of dB values does not give. Raises when the band holds no
    points -- a level from an empty band is the "no objection" answer this method refuses.
    """
    if not (f_max > f_min):
        raise ValueError(f"band ({f_min}, {f_max}) is empty or inverted")
    pwr = [10.0 ** (float(m) / 10.0) for f, m in zip(freqs, mag_db) if f_min <= float(f) <= f_max]
    if not pwr:
        raise ValueError(f"no measured points inside ({f_min}, {f_max}) Hz — wrong band or wrong grid")
    return 10.0 * math.log10(sum(pwr) / len(pwr))


def measured_offsets(levels: dict) -> dict:
    """Cut-only offsets from measured band levels, same convention as `compute_offsets`.

    The quietest channel is the reference and gets 0; everything louder is cut to meet it, because
    a boost spends headroom that a car does not have and the quietest driver is the one that sets
    what the system can do.
    """
    if not levels:
        raise ValueError("no channels to balance")
    floor = min(levels.values())
    return {name: round(floor - lvl, 1) for name, lvl in levels.items()}


def _selftest() -> None:
    assert abs(bessj1(0.0)) < 1e-9, "J1(0)=0"
    assert abs(bessj1(1.0) - 0.4400505857) < 1e-6, f"J1(1)={bessj1(1.0)}"
    assert abs(directivity(1000, 0.0, 0.05) - 1.0) < 1e-9, "on-axis → 1"
    assert directivity(10000, 45.0, 0.05) < 1.0, "off-axis HF attenuates"
    # a nearer + more on-axis driver must be cut MORE (more negative) than a far/off-axis one
    drv = [
        Driver("near_onaxis", d=1.5, theta=10.0, a=0.03, band=(300, 3500)),
        Driver("far_offaxis", d=2.0, theta=40.0, a=0.03, band=(300, 3500)),
    ]
    off = compute_offsets(drv)
    assert off["near_onaxis"] <= off["far_offaxis"], off
    assert max(off.values()) == 0.0 and min(off.values()) <= 0.0, "cut-only, floor=0"
    # the measured estimate, anchored on definitions rather than on its own output
    f = [20.0 * (2 ** (i / 24.0)) for i in range(int(24 * math.log2(20000 / 20)) + 1)]
    flat = [80.0] * len(f)
    assert abs(band_level_db(f, flat, 300, 3000) - 80.0) < 1e-9, "a constant band averages to itself"
    louder = [83.0] * len(f)
    assert abs(band_level_db(f, louder, 300, 3000) - 83.0) < 1e-9
    # energy average, not a mean of decibels: half the band at +10 dB is +7.4 dB, not +5
    half = [90.0 if v < 300 else 80.0 for v in f]
    _lo, _hi = 20.0, 20000.0
    _n = len([v for v in f if _lo <= v <= _hi])
    _split = len([v for v in f if v < 300 and v >= _lo]) / _n
    _expect = 10 * math.log10(_split * 10 ** 9.0 + (1 - _split) * 10 ** 8.0)
    assert abs(band_level_db(f, half, _lo, _hi) - _expect) < 1e-9, "must average POWER, not dB"
    # what lies outside the band cannot move the answer
    spiky = [120.0 if v < 200 else 80.0 for v in f]
    assert abs(band_level_db(f, spiky, 300, 3000) - 80.0) < 1e-9, "out-of-band energy leaked in"
    # offsets: cut-only, quietest is the reference, and 3 dB louder is exactly −3
    mo = measured_offsets({"m-L": 80.0, "m-R": 83.0})
    assert mo == {"m-L": 0.0, "m-R": -3.0}, mo
    for bad in ((3000, 300), (1000, 1000)):
        try:
            band_level_db(f, flat, *bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"band {bad} must be refused")
    try:
        band_level_db([100.0, 200.0], [80.0, 80.0], 300, 3000)
    except ValueError:
        pass
    else:
        raise AssertionError("a band with no points in the grid must be refused")

    print("selftest OK —",
          f"J1(1)={bessj1(1.0):.6f}; D(10k,45°,5cm)={directivity(10000,45,0.05):.3f}; offsets={off}; "
          f"measured: energy-averaged, out-of-band ignored, cut-only ({mo})")


def _main(argv=None):
    """`--solos DIR --ver N`: the measured second estimate for a whole capture round.

    Bands come from the ledger's own crossovers, so the level is read where the driver actually
    works. The output is a PROPOSAL to compare with the geometry estimate and with the gains
    already in the ledger — it is not applied by anything here.
    """
    import argparse
    ap = argparse.ArgumentParser(description="levels read off the measurement (second estimate)")
    ap.add_argument("--solos", required=True, help="directory of Resonalyze v7 solo files")
    ap.add_argument("--ver", type=int, required=True, help="capture round number")
    ap.add_argument("--project", help="project dir — bands from its ledger, and the current gains")
    ap.add_argument("--preset", help="ledger preset (default: the registry's active slot)")
    ap.add_argument("--levels-fixed", action="store_true",
                    help="assert what no file records: one REW output level and one head-unit "
                         "level for the whole round, knobs untouched (capture sheet 0.2)")
    args = ap.parse_args(argv)
    if not args.levels_fixed:
        print("refusing: without --levels-fixed these numbers compare the volume knob, not the car."
              "\nNothing in a v7 file records the output level, so the assertion is yours to make.",
              file=sys.stderr)
        return 3

    import os as _os
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    import naming as _naming                         # the title grammar, for stem -> channel code
    import predict as _predict                       # numpy lives there, not here
    import verify_prediction as _vp                  # the SAME v7 reader the predictions use

    freqs = [20.0 * (2 ** (i / 48.0)) for i in range(int(48 * math.log2(20000 / 20)) + 1)]
    bands, gains = {}, {}
    if args.project:
        _preset, snap = _predict.load_project_state(args.project, args.preset)
        for code, ch in (snap.get("channels") or {}).items():
            hp = ch.get("hp") if isinstance(ch.get("hp"), dict) else None
            lp = ch.get("lp") if isinstance(ch.get("lp"), dict) else None
            bands[code] = (float((hp or {}).get("f") or 20.0), float((lp or {}).get("f") or 20000.0))
            if ch.get("gain_db") is not None:
                gains[code] = float(ch["gain_db"])

    def _code_of(stem):
        """The channel code of a SOLO stem, or None for anything that is not one.

        A level is read from the driver's baseline solo. A control (`ctl`), a position around the
        head (`p1`…`p9`, `x0`), a pair sum (`a+b`) or `ALL` is a measurement of something else, and
        counting it here would give one channel several levels -- the first walk of this command
        did exactly that (9 rows for 7 drivers) until this filter existed.
        """
        if "+" in stem or stem == "ALL":
            return None
        try:
            parsed = _naming.parse_name(stem)
        except Exception:
            parsed = None
        if parsed and parsed.get("code"):
            if parsed.get("control") or parsed.get("position"):
                return None
            return parsed["code"]
        if "-" in stem:                                # path_check's `m_L-ctl1` / `m_L-p5`: a tag
            return None
        return stem.replace("_", "-")

    rows = []
    try:
        measured = _vp.measured_from_v7_dir(args.solos, freqs)
    except FileNotFoundError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 3
    for stem, (_f, mag, _method, _H) in sorted(measured.items()):
        code = _code_of(stem)
        if code is None:
            continue
        lo, hi = bands.get(code, (20.0, 20000.0))
        try:
            rows.append((code, band_level_db(list(_f), list(mag), lo, hi), (lo, hi), None))
        except ValueError as exc:
            rows.append((code, None, (lo, hi), str(exc)))
    if not rows:
        print(f"refusing: no solo v7 files in {args.solos}", file=sys.stderr)
        return 3

    good = {c: lvl for c, lvl, _b, err in rows if err is None and lvl is not None}
    off = measured_offsets(good) if good else {}
    print(f"{'channel':10} {'band Hz':>16} {'measured dB':>12} {'offset dB':>10} {'ledger gain':>12} {'delta':>7}")
    for code, lvl, band, err in rows:
        if err:
            print(f"{code:10} {'—':>16} {'—':>12} {'—':>10}   {err}")
            continue
        g = gains.get(code)
        d = "" if g is None else f"{off[code] - g:+.1f}"
        print(f"{code:10} {band[0]:7.0f}–{band[1]:<8.0f} {lvl:12.1f} {off[code]:10.1f} "
              f"{'—' if g is None else f'{g:12.1f}'} {d:>7}")
    print("\nSecond estimate only. Where it disagrees with the geometry estimate by more than a "
          "couple of dB, the disagreement is the finding — read the install, do not just type the "
          "number in.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif "--solos" in sys.argv:
        raise SystemExit(_main())
    else:
        print(__doc__)
        print("Run with --selftest, or --solos DIR --ver N --levels-fixed, "
              "or import compute_offsets(drivers, n).")
