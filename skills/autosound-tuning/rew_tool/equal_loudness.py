#!/usr/bin/env python3
"""Equal-loudness (ISO 226:2003) sub-bass targeting — stdlib only.

WHY: a flat SPL sub sounds bass-light, because the ear is far less sensitive at low
frequencies — and that sensitivity depends on the *listening level* (the equal-loudness
contours flatten as you go louder, Fletcher-Munson). So the "right" sub shape is not flat;
it is an equal-LOUDNESS contour, anchored to the system's actual measured level.

METHOD (validated in the field — this approach helped win an AYA SQ round):
  1. Pick an anchor: one sub frequency + its measured SPL (e.g. 27.4 Hz @ 108.2 dB).
  2. Solve for the phon level L_N whose ISO-226 contour passes through that anchor
     (`calibrate_phon`). This ties the perceptual target to how loud you actually play.
  3. Read the target SPL at the other sub frequencies off that same contour (`targets`).
  4. target - measured = the EQ adjustment per frequency to reach equal loudness
     (`eq_from_measurements`). Cut-only discipline still applies — realize the shape by
     cutting the over-loud bands, not boosting, then bring level back with the master.

Generic: no car/DSP specifics. Table = the full ISO 226:2003 Table 1 (20 Hz–12.5 kHz);
the sub range (20–250 Hz) is the primary, field-validated use.

CLI:
  python equal_loudness.py --spl 40 --freqs 27.4 40 63          # contour SPLs at 40 phon
  python equal_loudness.py --anchor 27.4 108.2 \
      --measure 27.4=108.2 36=108.2 45=109.5 54=106.5           # sub EQ from measurements
  python equal_loudness.py --selftest
"""
import argparse
import math
import sys

# ISO 226:2003 Table 1 — alpha_f, L_U (dB), T_f (threshold, dB) per 1/3-oct frequency.
ISO226 = {
    20:    (0.532, -31.6, 78.5),
    25:    (0.506, -27.2, 68.7),
    31.5:  (0.480, -23.0, 59.5),
    40:    (0.455, -19.1, 51.1),
    50:    (0.432, -15.9, 44.0),
    63:    (0.409, -13.0, 37.5),
    80:    (0.387, -10.3, 31.5),
    100:   (0.367,  -8.1, 26.5),
    125:   (0.349,  -6.2, 22.1),
    160:   (0.330,  -4.5, 17.9),
    200:   (0.315,  -3.1, 14.4),
    250:   (0.301,  -2.0, 11.4),
    315:   (0.288,  -1.1,  8.6),
    400:   (0.276,  -0.4,  6.2),
    500:   (0.267,   0.0,  4.4),
    630:   (0.259,   0.3,  3.0),
    800:   (0.253,   0.5,  2.2),
    1000:  (0.250,   0.0,  2.4),
    1250:  (0.246,  -2.7,  3.5),
    1600:  (0.244,  -4.1,  1.7),
    2000:  (0.243,  -1.0, -1.3),
    2500:  (0.243,   1.7, -4.2),
    3150:  (0.243,   2.5, -6.0),
    4000:  (0.242,   1.2, -5.4),
    5000:  (0.242,  -2.1, -1.5),
    6300:  (0.245,  -7.1,  6.0),
    8000:  (0.254, -11.2, 12.6),
    10000: (0.271, -10.7, 13.9),
    12500: (0.301,  -3.1, 12.3),
}
_FREQS = sorted(ISO226)


def _param(f):
    """Linear-in-frequency interpolation of (alpha, L_U, T_f) — matches the field-tested rig."""
    if f <= _FREQS[0]:
        return ISO226[_FREQS[0]]
    if f >= _FREQS[-1]:
        return ISO226[_FREQS[-1]]
    for i in range(len(_FREQS) - 1):
        f0, f1 = _FREQS[i], _FREQS[i + 1]
        if f0 <= f <= f1:
            t = (f - f0) / (f1 - f0)
            return tuple(a + (b - a) * t for a, b in zip(ISO226[f0], ISO226[f1]))
    return ISO226[_FREQS[-1]]


def iso226_spl(phon, f):
    """SPL (dB) that sounds equally loud to `phon` phons at frequency `f` (ISO 226:2003)."""
    a_f, l_u, t_f = _param(f)
    term1 = 4.47e-3 * (10 ** (0.025 * phon) - 1.15)
    term2 = (0.4 * 10 ** ((t_f + l_u) / 10.0 - 9.0)) ** a_f
    a_sum = term1 + term2
    if a_sum <= 0:
        return 0.0
    return (10.0 / a_f) * math.log10(a_sum) - l_u + 94.0


def calibrate_phon(anchor_freq, anchor_spl, lo=0.0, hi=120.0, iters=100):
    """Find the phon level whose ISO-226 contour passes through (anchor_freq, anchor_spl)."""
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if iso226_spl(mid, anchor_freq) < anchor_spl:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def targets(phon, freqs):
    """Target SPL at each freq on the `phon` equal-loudness contour."""
    return [(f, iso226_spl(phon, f)) for f in freqs]


def eq_from_measurements(anchor_freq, anchor_spl, measured):
    """measured = [(freq, measured_spl), ...] → per-freq (target_spl, adjustment_dB).

    adjustment = target - measured (negative = cut that band; realize cut-only + master up).
    """
    phon = calibrate_phon(anchor_freq, anchor_spl)
    out = []
    for f, m in measured:
        t = iso226_spl(phon, f)
        out.append((f, m, t, t - m))
    return phon, out


def _selftest():
    ok = True
    # 1) At 1 kHz, SPL == phon by definition (validates formula + reference row).
    for p in (40, 60, 80):
        v = iso226_spl(p, 1000)
        if abs(v - p) > 0.2:
            print(f"  FAIL 1kHz: iso226_spl({p},1000)={v:.2f} != {p}"); ok = False
    # 2) Round-trip: calibrate to an anchor, read it back.
    ph = calibrate_phon(27.4, 108.2)
    back = iso226_spl(ph, 27.4)
    if abs(back - 108.2) > 0.05:
        print(f"  FAIL round-trip: {back:.3f} != 108.2"); ok = False
    # 3) Contour rises toward low freq in the sub (equal loudness needs more SPL low down).
    if not (iso226_spl(80, 20) > iso226_spl(80, 80)):
        print("  FAIL monotonic: 20Hz target should exceed 80Hz on a contour"); ok = False
    print("selftest:", "OK" if ok else "FAILED", f"(anchor 27.4@108.2 → {ph:.2f} phon)")
    return ok


def _parse_measure(items):
    out = []
    for it in items:
        f, _, s = it.partition("=")
        out.append((float(f), float(s)))
    return out


def main():
    ap = argparse.ArgumentParser(description="Equal-loudness (ISO 226:2003) sub targeting")
    ap.add_argument("--spl", type=float, help="phon level: print contour SPLs at --freqs")
    ap.add_argument("--freqs", type=float, nargs="+", help="frequencies (Hz)")
    ap.add_argument("--anchor", type=float, nargs=2, metavar=("FREQ", "SPL"),
                    help="anchor freq + measured SPL to calibrate the contour")
    ap.add_argument("--measure", nargs="+", metavar="F=SPL",
                    help="measured freq=spl pairs → per-freq EQ adjustment")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if _selftest() else 1)

    if a.anchor and a.measure:
        phon, rows = eq_from_measurements(a.anchor[0], a.anchor[1], _parse_measure(a.measure))
        print(f"Calibrated contour: {phon:.2f} phon (anchor {a.anchor[0]} Hz @ {a.anchor[1]} dB)\n")
        print(f"{'Freq':>8} | {'Measured':>9} | {'Target':>8} | {'Adjust':>8}")
        print("-" * 42)
        for f, m, t, adj in rows:
            print(f"{f:8.1f} | {m:9.2f} | {t:8.2f} | {adj:+8.2f}")
        print("\n(negative Adjust = cut that band; realize cut-only, restore level with the master)")
        return

    if a.spl is not None and a.freqs:
        print(f"ISO 226:2003 contour @ {a.spl:.1f} phon:")
        for f, t in targets(a.spl, a.freqs):
            print(f"  {f:8.1f} Hz -> {t:7.2f} dB")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
