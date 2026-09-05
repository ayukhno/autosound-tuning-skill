#!/usr/bin/env python3
"""The channel PHASE control of an Audiotec-Fischer processor (HELIX / MATCH / BRAX), as the
hardware realizes it -- ported from Resonalyze, verified against the bench.

WHAT THIS CONTROL IS. The user does not choose a corner frequency -- they choose an ANGLE, and the
device solves for the corner of a second-order all-pass that delivers that angle at the channel's
own crossover. So the angle alone is not a filter: it needs the channel's reference crossover to
become one, which is why a ledger row carrying `phase_deg` and nothing else cannot be modelled,
and a row carrying it beside its `hp`/`lp` can (`predict.chain_from_row`).

MEASURED, not documented (Helix DSP Ultra S, 96 kHz, ~60 electrical sweeps, 2026-09-01/02; the
curves are published under CC BY 4.0 in `ayukhno/autosound-measurements`, `hardware/helix/dsp-ultra-s/`,
and the 32 cases the port is checked against are in `testdata/helix-bench/phase-control-vectors.json`):

  * one RBJ second-order all-pass with Q = 1.0000 across the whole reachable range;
  * the reference is the crossover AS CONFIGURED, not as active -- Bypass and slope = OFF leave it
    in place (three states, 0.018 dB and 0.12 deg apart). The low-pass on a subwoofer channel, the
    high-pass on every other channel that has the control;
  * the corner is CAPPED at 3/16 of the processing rate (18 kHz at 96 kHz), which the manufacturer
    documents nowhere. Above that, settings COLLAPSE: at a 5000 Hz reference 5.625 / 11.25 / 28.125
    deg are literally the same filter and all deliver 29.5 deg -- a value not on the control's own
    grid. `realize` therefore returns the DELIVERED angle, never an echo of the setting;
  * it is not a polarity flip (180 deg at a 5 kHz reference is -23 deg at 1 kHz) and it is not free:
    180 deg at a 500 Hz reference costs 640-690 us of group delay below 200 Hz -- about 22 cm of path,
    in the band the control is usually being used to fix (`group_delay_us`).

NOT established, and not to be inferred (04-data-and-provenance of the 2026-09-05 handoff):

  * the ceiling at any rate other than 96 kHz. Three recoveries at two references gave 18007-18011 Hz,
    which is 3/16 of the rate AND an absolute 18 kHz to within the spread. Resonalyze takes the
    rate-relative reading (the corner is placed in the digital domain, so one coefficient generator
    serving both device generations would most naturally clamp there) and so does this port. On a
    48 kHz unit the two readings differ -- `MAX_CORNER_FRACTION` is the one line to correct if one is
    ever measured;
  * the 5.625 deg step on mid/high channels: measured on a subwoofer channel; the mid/high block only
    captured 180 deg, which sits on a 5.625 grid and an 11.25 one alike;
  * whether the ceiling is deliberate or a firmware defect.

    python3 phase_rotation.py 180 500            # corner, delivered angle, cost, at the bound rate
    python3 phase_rotation.py 5.625 5000 --fs 96000
    python3 phase_rotation.py --selftest
"""
# upstream: DIMOSUS/Resonalyze dsp/PhaseRotationControl.cs @ bc957c8 (MIT) --
#   PhaseRotationControl.{Realize,DeliveredDegrees,RotationAt,SolveCornerHz,SnapToGrid,
#   MaximumCornerHz}, StepDegrees, MaximumDegrees, SectionQ, MaximumCornerFraction.
#   Written by the upstream author from the published bench data (DIMOSUS/Resonalyze#88); this
#   port is checked against his compiled library on 32 cases, see `_selftest`.
# deviation: the biquad is `dsp_math.apf2_response` rather than AllPassFilter.Response -- the
#            same RBJ section at the same rate, and the one this tree already verifies against
#            the hardware; see `rotation_at`.
# deviation: `realize` returns (corner_hz, delivered_deg) in one call where upstream has Realize
#            and DeliveredDegrees separately -- one solve, both numbers; see `realize`.
# deviation: `lost_settings` and `group_delay_us` have no upstream -- the arithmetic a tuner needs
#            next to the law (how many positions a reference loses to the ceiling, what a turn
#            costs in the bass); see those functions.
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp_math  # noqa: E402

STEP_DEG = 360.0 / 64.0           #: the grid the control steps on: 5.625 deg
MAX_DEG = 360.0 - STEP_DEG        #: 354.375 -- a full 360 is not offered (it is the same filter as 0)
SECTION_Q = 1.0                   #: measured 1.0000 on six curves across the range; a constant, not a setting
MAX_CORNER_FRACTION = 3.0 / 16.0  #: the ceiling, as a fraction of the processing rate (18 kHz at 96 kHz)
CAP_TOLERANCE_DEG = 0.05          #: a delivered angle this far from the setting is "as asked"

VECTORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata", "helix-bench",
                       "phase-control-vectors.json")


def max_corner_hz(fs=None):
    """The highest corner the control will place at this processing rate."""
    return dsp_math._fs(fs) * MAX_CORNER_FRACTION


def snap_to_grid(deg):
    """The nearest setting the control can actually hold, clamped into its range."""
    if not np.isfinite(deg) or deg <= 0:
        return 0.0
    return float(min(round(deg / STEP_DEG) * STEP_DEG, MAX_DEG))


def rotation_at(corner_hz, reference_hz, fs=None):
    """How far a Q=1 all-pass with this corner turns the phase at the reference, as a positive lag
    in (0, 360). MONOTONICALLY DECREASING in the corner. The unfolding matters: an arctangent
    reports the section's 360 deg of swing folded into (-180, 180], so without it a solver would
    see the curve jump from 180 back to 0 in the middle of its search."""
    h = dsp_math.apf2_response(np.array([float(reference_hz)]), corner_hz, SECTION_Q, fs=fs)[0]
    lag = -np.degrees(np.angle(h))
    return float(lag + 360.0 if lag < 0 else lag)


def solve_corner(degrees, reference_hz, fs=None):
    """The corner the device places for this setting -- or the ceiling, when the setting would need
    a higher one. Bisection on the log of the corner: the curve is smooth and monotone over the
    whole range, so there is no cleverer root to find; a hundred halvings put the corner well
    inside the 0.2 % the bench itself resolves."""
    degrees = min(float(degrees), MAX_DEG)
    high = max_corner_hz(fs)
    if rotation_at(high, reference_hz, fs) >= degrees:
        return high                                    # capped: every smaller setting lands here too
    low = float(reference_hz) / 64.0
    for _ in range(8):
        if rotation_at(low, reference_hz, fs) >= degrees:
            break
        low /= 8.0
    for _ in range(100):
        mid = np.sqrt(low * high)
        if rotation_at(mid, reference_hz, fs) >= degrees:
            low = mid
        else:
            high = mid
    return float(np.sqrt(low * high))


def realize(degrees, reference_hz, fs=None):
    """`(corner_hz, delivered_deg)` for a setting, or `(None, 0.0)` when it is transparent.

    `delivered_deg` is what the channel ACTUALLY gets. It equals the setting unless the corner hit
    the ceiling -- report it, never echo back what was asked for: a UI that echoes the setting is
    lying to the tuner in exactly the region where the control stops behaving."""
    if (not np.isfinite(degrees) or degrees <= 0
            or not np.isfinite(reference_hz) or reference_hz <= 0):
        return None, 0.0
    corner = solve_corner(degrees, reference_hz, fs)
    return corner, rotation_at(corner, reference_hz, fs)


def is_capped(degrees, reference_hz, fs=None):
    corner, _ = realize(degrees, reference_hz, fs)
    return corner is not None and corner >= max_corner_hz(fs) * (1 - 1e-9)


def response(freqs_hz, degrees, reference_hz, fs=None):
    """The channel's phase-control response on `freqs_hz`. Unity magnitude; ones when transparent."""
    corner, _ = realize(degrees, reference_hz, fs)
    if corner is None:
        return np.ones(np.shape(freqs_hz), dtype=complex)
    return dsp_math.apf2_response(freqs_hz, corner, SECTION_Q, fs=fs)


def group_delay_us(degrees, reference_hz, fs=None, at_hz=(100.0,)):
    """Group delay of the realized section at `at_hz`, in microseconds. The control is NOT free:
    270 deg at a 5 kHz reference costs about 0.1 ms in the bass, 180 deg at a 500 Hz reference
    0.64-0.69 ms over 20-100 Hz and 1.27 ms at the corner. A plateau below the corner, a peak at
    it, and a fall away above it -- so the cost lands BELOW the reference, not above it."""
    corner, _ = realize(degrees, reference_hz, fs)
    f = np.atleast_1d(np.asarray(at_hz, dtype=float))
    if corner is None:
        return np.zeros(f.shape)
    d = np.maximum(f * 1e-4, 1e-3)
    ph = lambda x: np.unwrap(np.angle(dsp_math.apf2_response(x, corner, SECTION_Q, fs=fs)))  # noqa: E731
    return -(ph(f + d) - ph(f - d)) / (2 * d) / (2 * np.pi) * 1e6


def lost_settings(reference_hz, fs=None):
    """How many of the 63 positions collapse onto the ceiling at this reference -- arithmetic from
    the ceiling and the step, not a measurement: 0 below a 1001 Hz reference at 96 kHz, 2 at
    2000, 3 at 3000, 5 at 5000, 9 at 8000. All of them deliver ONE angle (the ceiling's), so a
    tuner who dials one small step gets that many, and the UI says otherwise."""
    return sum(1 for k in range(1, 64) if is_capped(k * STEP_DEG, reference_hz, fs))


def capped_note(degrees, reference_hz, fs=None):
    """One sentence for a report when the setting does not deliver what it says; None otherwise."""
    corner, delivered = realize(degrees, reference_hz, fs)
    if corner is None or abs(delivered - float(degrees)) <= CAP_TOLERANCE_DEG:
        return None
    return (f"phase {degrees:g} deg at a {reference_hz:g} Hz reference is capped: the corner stops at "
            f"{corner:.0f} Hz and the channel gets {delivered:.1f} deg, not {degrees:g} "
            f"({lost_settings(reference_hz, fs)} of the control's positions collapse there)")


# ---------------------------------------------------------------- selftest
def _selftest():
    """Against the upstream's compiled library, against the bench, and against the physics."""
    import json
    fs = 96000.0
    dsp_math.reset_processing_rate()

    # 1. The port IS the upstream: vectors from Resonalyze's own compiled PhaseRotationControl
    #    (bc957c8) at 96 kHz, every one of which is also a published bench measurement.
    for deg, ref, corner, delivered in [
            (90.0,     2000.0,  3228.6287,  90.0000),
            (180.0,    2000.0,  2000.0000, 180.0000),
            (180.0,     500.0,   500.0000, 180.0000),
            (45.0,     5000.0, 13126.4754,  45.0000),
            (90.0,     5000.0,  7976.8816,  90.0000),
            (180.0,    5000.0,  5000.0000, 180.0000),
            (270.0,    5000.0,  3107.2919, 270.0000),
            (354.375,  5000.0,   247.2494, 354.3750),
            (5.625,    5000.0, 18000.0000,  29.4871),   # capped
            (11.25,    5000.0, 18000.0000,  29.4871),   # capped, same filter
            (28.125,   5000.0, 18000.0000,  29.4871),   # capped, same filter
            (5.625,     500.0,  9847.4793,   5.6250),
            (11.25,     500.0,  5078.5396,  11.2500),
            (5.625,    3000.0, 18000.0000,  17.1374),   # capped
            (180.0,    3000.0,  3000.0000, 180.0000)]:
        c, d = realize(deg, ref, fs)
        assert abs(c - corner) < 5e-4, (deg, ref, c, corner)
        assert abs(d - delivered) < 5e-4, (deg, ref, d, delivered)

    # 2. The 32 published cases: the model side is the upstream's, the bench side is the
    #    measurement, and the two are kept apart on purpose (`how_to_read` in the file).
    with open(VECTORS, encoding="utf-8") as fh:
        vectors = json.load(fh)
    cases = vectors["cases"]
    assert len(cases) == 32, len(cases)
    trusted, flagged = [], []
    for case in cases:
        rate = float(case["sample_rate_hz"])
        c, d = realize(case["setting_deg"], case["reference"]["hz"], rate)
        # model side: the file carries the corner to 0.1 Hz and the angle to 1e-4 deg
        assert abs(c - case["solved_corner_hz"]) <= 0.06, (case["case"], c, case["solved_corner_hz"])
        assert abs(d - case["delivered_deg"]) <= 1e-4, (case["case"], d, case["delivered_deg"])
        assert is_capped(case["setting_deg"], case["reference"]["hz"], rate) == case["capped"], case["case"]
        # bench side: where the free fit is identifiable, its corner is the model's
        pct = abs(case["bench"]["free_fit_corner_hz"] - c) / c * 100.0
        (trusted if case["free_fit_trustworthy"] else flagged).append((case["case"], pct))
    assert len(flagged) == 4, [n for n, _ in flagged]
    pcts = sorted(p for _, p in trusted)
    assert pcts[len(pcts) // 2] <= 0.2, ("median corner agreement", pcts[len(pcts) // 2])
    assert max(pcts) <= 4.0, ("worst trusted case", max(trusted, key=lambda t: t[1]))
    assert sum(1 for p in pcts if p <= 0.5) >= 24, pcts
    # The four flagged cases are flagged for a reason the file states: the capped corner sits
    # ABOVE the band their crossover left usable, so the fitted corner is an extrapolation. The
    # flag is load-bearing -- every one of them would FAIL the 4 % line above if it were used.
    for name, pct in flagged:
        assert pct > 5.0, ("a flagged case fits -- the flag is no longer doing anything", name, pct)
        note = next(k["note"] for k in cases if k["case"] == name)
        assert note and "usable band" in note, (name, note)
    # ...and the residual, which does not depend on the fit, is small on every case but the two
    # 354.375-deg ones at 247 Hz, where the corner sits at the bottom of the measured band.
    assert all(k["bench"]["phase_rms_deg"] < 0.6 for k in cases if k["setting_deg"] != MAX_DEG), \
        [(k["case"], k["bench"]["phase_rms_deg"]) for k in cases if k["bench"]["phase_rms_deg"] >= 0.6]

    # 3. The grid, the range, the transparent cases.
    assert snap_to_grid(7.0) == 5.625 and snap_to_grid(400.0) == MAX_DEG and snap_to_grid(-3.0) == 0.0
    assert realize(0.0, 5000.0, fs) == (None, 0.0)
    assert realize(180.0, 0.0, fs) == (None, 0.0)
    assert realize(float("nan"), 500.0, fs) == (None, 0.0)
    assert realize(400.0, 5000.0, fs)[1] == realize(MAX_DEG, 5000.0, fs)[1], "above the range clamps"
    assert np.allclose(response(np.array([100.0, 1000.0]), 0.0, 5000.0, fs), 1.0)

    # 4. The physics of the realized section.
    f = np.array([20.0, 100.0, 1000.0, 5000.0, 12000.0])
    h = response(f, 270.0, 5000.0, fs)
    assert np.allclose(np.abs(h), 1.0, atol=1e-12), "an all-pass has unit magnitude"
    # the delivered angle is the phase AT the reference, by construction -- and it is only there
    assert abs(response(np.array([5000.0]), 180.0, 5000.0, fs)[0] + 1.0) < 1e-9, "180 at the reference is -1"
    at_1k = np.degrees(np.angle(response(np.array([1000.0]), 180.0, 5000.0, fs)[0]))
    assert -30.0 < at_1k < -15.0, ("180 deg is not a polarity flip: at 1 kHz it is about -23 deg", at_1k)
    corners = np.geomspace(100.0, 18000.0, 300)
    turns = [rotation_at(c, 5000.0, fs) for c in corners]
    assert all(np.diff(turns) < 0), "the turn at the reference must fall monotonically with the corner"
    assert 0.0 < turns[-1] < turns[0] < 360.0, (turns[0], turns[-1])

    # 5. The ceiling is rate-relative, and the rate is load-bearing: the same setting is a
    #    different corner on a 48 kHz device (the upstream's own worked figure, 7674 Hz).
    assert max_corner_hz(96000.0) == 18000.0 and max_corner_hz(48000.0) == 9000.0
    c48, d48 = realize(90.0, 5000.0, 48000.0)
    assert abs(c48 - 7674.06) < 0.1 and abs(d48 - 90.0) < 1e-6, (c48, d48)
    # ...and with no rate given the session's bound rate is used, like every other response here.
    assert realize(90.0, 5000.0)[0] == realize(90.0, 5000.0, fs)[0]
    dsp_math.bind_processing_rate(48000.0, source="explicit")
    try:
        assert abs(realize(90.0, 5000.0)[0] - c48) < 1e-9, "the bound rate must reach the solve"
    finally:
        dsp_math.reset_processing_rate()

    # 6. What the ceiling costs, by arithmetic: nothing below 1001 Hz, then 2 / 3 / 5 / 9 positions.
    for ref, lost in ((500.0, 0), (1000.0, 0), (1001.0, 1), (2000.0, 2), (3000.0, 3), (5000.0, 5), (8000.0, 9)):
        assert lost_settings(ref, fs) == lost, (ref, lost_settings(ref, fs))
    assert capped_note(180.0, 5000.0, fs) is None
    note = capped_note(5.625, 5000.0, fs)
    assert note and "29.5 deg" in note and "18000 Hz" in note and "5 of" in note, note
    # the collapsed settings are ONE filter: the same response, not merely the same number
    assert np.allclose(response(f, 5.625, 5000.0, fs), response(f, 28.125, 5000.0, fs))

    # 7. The cost, from the fitted filter: a plateau below the corner, a peak at it, a fall above.
    gd = group_delay_us(270.0, 5000.0, fs, [100.0, 3107.3, 8000.0])
    assert 95.0 < gd[0] < 110.0 and 190.0 < gd[1] < 220.0 and gd[2] < 30.0, gd
    gd = group_delay_us(180.0, 500.0, fs, [20.0, 50.0, 100.0, 500.0, 8000.0])
    assert all(600.0 < v < 720.0 for v in gd[:3]) and 1200.0 < gd[3] < 1350.0 and gd[4] < 10.0, gd
    assert np.all(group_delay_us(0.0, 500.0, fs, [100.0]) == 0.0)

    print("selftest[phase_rotation] OK -- 15 upstream vectors to 5e-4, 32 published cases (model side "
          "to the file's precision, 28 trustworthy free fits at median %.2f %% / worst %.1f %%, the 4 "
          "flagged ones >5 %% off so the flag is load-bearing), unit magnitude, 180 at the reference "
          "is -1 and -23 deg at 1 kHz, the turn falls monotonically with the corner, the ceiling is "
          "3/16 of the rate (9 kHz at 48 kHz, 7674 Hz for 90 deg at 5 kHz), 0/2/3/5/9 positions lost "
          "at 1000/2000/3000/5000/8000 Hz, and 180 deg at a 500 Hz reference costs 0.64-0.69 ms over "
          "20-100 Hz" % (pcts[len(pcts) // 2], max(pcts)))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="what a HELIX channel Phase setting actually builds")
    ap.add_argument("degrees", nargs="?", type=float, help="the setting, 0..354.375 (5.625-deg grid)")
    ap.add_argument("reference_hz", nargs="?", type=float,
                    help="the channel's reference crossover AS CONFIGURED: LPF on a sub, HPF otherwise")
    ap.add_argument("--fs", type=float, default=None,
                    help="the DSP's processing rate (default: the session's bound rate, 96 kHz assumed)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        _selftest()
        return 0
    if args.degrees is None or args.reference_hz is None:
        ap.print_usage()
        return 2
    fs = args.fs
    if fs is not None:
        dsp_math.bind_processing_rate(fs, source="explicit")
    rate, source = dsp_math.processing_rate()
    setting = snap_to_grid(args.degrees)
    if setting != args.degrees:
        print(f"  {args.degrees:g} deg is not on the control's 5.625-deg grid; nearest setting {setting:g}")
    corner, delivered = realize(setting, args.reference_hz, fs)
    print(f"  rate {rate:g} Hz ({source}); ceiling {max_corner_hz(fs):.0f} Hz")
    if corner is None:
        print("  transparent: no filter")
        return 0
    print(f"  setting {setting:g} deg at a {args.reference_hz:g} Hz reference -> APF2 corner "
          f"{corner:.1f} Hz, Q {SECTION_Q:g}; delivered {delivered:.2f} deg at the reference")
    note = capped_note(setting, args.reference_hz, fs)
    if note:
        print(f"  ! {note}")
    pts = [50.0, 100.0, 200.0, 500.0, 1000.0, corner, 8000.0]
    gd = group_delay_us(setting, args.reference_hz, fs, pts)
    print("  group delay: " + ", ".join(f"{p:.0f} Hz {g:.0f} us" for p, g in zip(pts, gd))
          + f"  ({gd[1] * 0.343:.1f} cm of path at 100 Hz)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.argv[1] = "--selftest"
    sys.exit(main())
