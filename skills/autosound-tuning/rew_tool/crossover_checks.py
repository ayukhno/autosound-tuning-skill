#!/usr/bin/env python3
"""crossover_checks -- the three questions asked of a crossover BEFORE it is entered.

`xover_select` finds a crossover that fits a target. Fitting is not the whole question: a corner
can fit beautifully and still ask a driver to work below where it can, put a junction where the ear
is least forgiving, or pile up group delay a listener hears as smearing. These three checks are the
ones a tuner would ask by hand, and they are here so they are asked every time rather than when
somebody remembers.

Each one answers in three states -- OK / CAUTION / REFUSE -- and none of them is silent about where
its numbers come from, because two of the three rest on OUTSIDE sources rather than on this
method's own measurements:

  * **Fs margin** -- the floor (`>= 1.1 x Fs`, protective) is this method's own doctrine
    (`references/phases/virtual-first.md`, `core/impedance-ts.md`: "cross above it; the installed Fs
    is the real number"). The working margin (default 2x) is craft convention, not measured here,
    so it is a parameter and it is labelled as convention in the output.
  * **Group-delay budget** -- Blauert & Laws (1978) audibility thresholds, an external result.
    Quoted, interpolated in log frequency, and named as external in every line it produces.
  * **Junction cost** -- derived from ISO 226 through this repo's own `equal_loudness`, not from a
    remembered "avoid 2-4 kHz" rule: the cost of putting a junction at fc is how loudly the ear
    hears trouble there, relative to 1 kHz. The familiar 2-4 kHz answer falls out of the curve
    instead of being asserted.

    python3 rew_tool/crossover_checks.py --fc 2500 --fs 900 --order 2
    python3 rew_tool/crossover_checks.py --selftest

stdlib only (it borrows `equal_loudness`, which is also stdlib).
"""
from __future__ import annotations

import math
import sys

try:
    from . import equal_loudness
except ImportError:                                   # run as a script, not as a package member
    import equal_loudness

#: This method's own floor: a protective high-pass sits at or above 1.1 x the INSTALLED Fs, and a
#: working crossover cannot be lower than the protection. Below it the answer is REFUSE, not advice.
FS_FLOOR = 1.1

#: Craft convention, not a measurement: a second-order corner an octave above Fs still lets the
#: driver work where its excursion and distortion rise steeply. Steeper slopes relax it, which is
#: why `order` is an input rather than an assumption.
FS_MARGIN_DEFAULT = 2.0

#: Blauert & Laws (1978), group-delay audibility thresholds, in ms at the frequency given. EXTERNAL
#: source: this repo has measured neither these thresholds nor its own.
BLAUERT_LAWS_MS = ((250.0, 8.0), (500.0, 3.2), (1000.0, 2.0), (2000.0, 1.5), (4000.0, 1.0),
                   (8000.0, 1.0))

OK, CAUTION, REFUSE = "OK", "CAUTION", "REFUSE"


def gd_threshold_ms(f):
    """The audible group-delay threshold at f, interpolated in log frequency (Blauert & Laws)."""
    f = float(f)
    pts = BLAUERT_LAWS_MS
    if f <= pts[0][0]:
        return pts[0][1]
    if f >= pts[-1][0]:
        return pts[-1][1]
    for (f0, t0), (f1, t1) in zip(pts, pts[1:]):
        if f0 <= f <= f1:
            w = (math.log(f / f0)) / (math.log(f1 / f0))
            return t0 + w * (t1 - t0)
    raise AssertionError("unreachable")


def fs_margin(fc, fs_installed, order=2, margin=FS_MARGIN_DEFAULT):
    """Is this corner far enough above the driver's installed Fs?

    `fs_installed` is the resonance of the driver IN ITS BOX, in the car -- the number an impedance
    sweep gives (`core/impedance-ts.md`). A datasheet Fs is a different, usually lower, number: pass
    it only if that is all you have, and read the verdict as weaker for it.
    """
    fc, fs = float(fc), float(fs_installed)
    if fs <= 0:
        raise ValueError("installed Fs must be > 0 -- measure it, do not assume it")
    ratio = fc / fs
    # a steeper slope unloads the driver faster below the corner, so the same ratio buys more
    effective = margin * (2.0 / max(int(order), 1)) ** 0.5
    if ratio < FS_FLOOR:
        v = REFUSE
        why = (f"fc is {ratio:.2f} x Fs, below the protective floor of {FS_FLOOR} x -- this is not "
               f"a tuning choice, it is asking the driver to play its own resonance")
    elif ratio < effective:
        v = CAUTION
        why = (f"fc is {ratio:.2f} x Fs; convention wants about {effective:.2f} x at order {order} "
               f"(excursion and distortion rise steeply below that). Measure distortion at level "
               f"before accepting it")
    else:
        v = OK
        why = f"fc is {ratio:.2f} x Fs, clear of the {effective:.2f} x convention at order {order}"
    return {"verdict": v, "ratio": round(ratio, 2), "floor": FS_FLOOR,
            "convention": round(effective, 2), "why": why,
            "source": "floor: this method's doctrine; margin: craft convention, not measured here"}


def gd_budget(freqs, gd_ms):
    """Worst point of a group-delay curve against the Blauert & Laws thresholds.

    Feed it the DELTA a filter adds, not a measured absolute group delay: an absolute measurement
    carries the whole flight time from driver to microphone, which is not what a listener hears as
    smearing (`core/analysis-playbook.md` -- a reviewer once read 18.4 ms of that as filter GD).
    """
    if not len(freqs) or len(freqs) != len(gd_ms):
        raise ValueError("freqs and gd_ms must be the same non-empty length")
    worst, worst_f, worst_thr = -1e9, None, None
    for f, gd in zip(freqs, gd_ms):
        thr = gd_threshold_ms(f)
        over = abs(float(gd)) - thr
        if over > worst:
            worst, worst_f, worst_thr = over, float(f), thr
    if worst <= -0.5:
        v = OK
    elif worst <= 0.0:
        v = CAUTION
    else:
        v = REFUSE
    return {"verdict": v, "worst_f_hz": round(worst_f, 1), "threshold_ms": round(worst_thr, 2),
            "margin_ms": round(-worst, 2),
            "why": (f"the largest excursion toward the threshold is at {worst_f:.0f} Hz: "
                    f"{abs(worst + worst_thr):.2f} ms against {worst_thr:.2f} ms allowed"),
            "source": "Blauert & Laws (1978), external -- not measured by this method"}


def junction_cost(fc, phon=70.0):
    """How costly a junction at `fc` is, from ISO 226 rather than from a remembered rule.

    A crossover junction is where two drivers overlap, so it is where lobing, delay error and
    polarity error all show up first. How much that COSTS depends on how loudly the ear hears that
    region: the cost here is the ear's sensitivity at fc relative to 1 kHz, in dB, at a listening
    level. Positive = the ear is more sensitive there than at 1 kHz, so errors are more expensive.
    """
    ref = equal_loudness.iso226_spl(phon, 1000.0)
    here = equal_loudness.iso226_spl(phon, float(fc))
    cost = ref - here                                  # a LOWER SPL for the same loudness = more sensitive
    if cost >= 2.0:
        v = CAUTION
        why = (f"the ear is {cost:.1f} dB more sensitive at {float(fc):.0f} Hz than at 1 kHz -- every "
               f"error in this junction is heard at that advantage. Cross elsewhere if the drivers "
               f"allow it; if they do not, this junction earns the time budget in 1.3")
    else:
        v = OK
        why = (f"the ear is {cost:+.1f} dB relative to 1 kHz at {float(fc):.0f} Hz -- no sensitivity "
               f"premium on errors here")
    return {"verdict": v, "cost_db": round(cost, 1), "phon": phon, "why": why,
            "source": "ISO 226 via equal_loudness -- derived, not a remembered 2-4 kHz rule"}


def render(checks):
    """One block per check, verdict first, source last -- so a reader can weigh it."""
    out = []
    for name, r in checks.items():
        out.append(f"{r['verdict']:8} {name}")
        out.append(f"         {r['why']}")
        out.append(f"         ({r['source']})")
    worst = REFUSE if any(r["verdict"] == REFUSE for r in checks.values()) else (
        CAUTION if any(r["verdict"] == CAUTION for r in checks.values()) else OK)
    out.append(f"\noverall: {worst}")
    return "\n".join(out)


def _selftest():
    # thresholds: the quoted anchors come back exactly, and between them it interpolates in log f
    assert gd_threshold_ms(1000) == 2.0 and gd_threshold_ms(2000) == 1.5
    mid = gd_threshold_ms(math.sqrt(1000 * 2000))
    assert abs(mid - 1.75) < 1e-9, mid                 # log-midpoint of a linear interpolation
    assert gd_threshold_ms(20) == 8.0 and gd_threshold_ms(20000) == 1.0, "clamped outside the data"

    # Fs margin: the floor is a refusal, not advice; and a steeper slope relaxes the convention
    assert fs_margin(950, 900)["verdict"] == REFUSE, "below 1.1 x Fs must refuse"
    assert fs_margin(1500, 900, order=2)["verdict"] == CAUTION
    assert fs_margin(2400, 900, order=2)["verdict"] == OK
    o2 = fs_margin(1500, 900, order=2)["convention"]
    o4 = fs_margin(1500, 900, order=4)["convention"]
    assert o4 < o2, (o2, o4)                           # order 4 asks for less headroom than order 2
    try:
        fs_margin(2000, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("Fs <= 0 must be refused, not defaulted")

    # GD budget: exactly at the threshold is not OK, and comfortably under it is
    f = [500.0, 1000.0, 2000.0]
    assert gd_budget(f, [0.5, 0.4, 0.3])["verdict"] == OK
    assert gd_budget(f, [3.2, 0.4, 0.3])["verdict"] == CAUTION, "at the threshold is not clearance"
    over = gd_budget(f, [0.5, 0.4, 2.0])
    assert over["verdict"] == REFUSE and over["worst_f_hz"] == 2000.0, over
    try:
        gd_budget([100.0], [1.0, 2.0])
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched lengths must be refused")

    # junction cost: derived from ISO 226, so the ear's most sensitive region must come out worst
    costs = {f: junction_cost(f)["cost_db"] for f in (200.0, 1000.0, 3500.0, 10000.0)}
    assert costs[3500.0] > costs[1000.0], costs        # the presence region is the sensitive one
    assert costs[3500.0] > costs[200.0] and costs[3500.0] > costs[10000.0], costs
    assert abs(costs[1000.0]) < 0.05, costs            # 1 kHz is the reference, by construction
    assert junction_cost(3500.0)["verdict"] == CAUTION and junction_cost(200.0)["verdict"] == OK

    print("selftest OK -- Blauert & Laws anchors exact and log-interpolated; the 1.1 x Fs floor "
          "refuses while the convention only cautions and moves with order; a GD exactly at the "
          f"threshold is not clearance; junction cost peaks at 3.5 kHz ({costs[3500.0]:+.1f} dB vs "
          f"1 kHz) because ISO 226 puts it there, not because a rule said 2-4 kHz")
    return 0


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the three questions asked of a crossover")
    ap.add_argument("--fc", type=float, required=True, help="the corner under consideration (Hz)")
    ap.add_argument("--fs", type=float, help="the driver's INSTALLED Fs (Hz), from an impedance sweep")
    ap.add_argument("--order", type=int, default=2, help="filter order at that corner (default 2)")
    ap.add_argument("--gd", help="group delay the filter ADDS, as f:ms pairs, e.g. 500:1.2,2000:0.8")
    ap.add_argument("--phon", type=float, default=70.0, help="listening level for the ear weighting")
    args = ap.parse_args(argv)

    checks = {}
    if args.fs:
        checks["Fs margin"] = fs_margin(args.fc, args.fs, args.order)
    if args.gd:
        pairs = [p.split(":") for p in args.gd.split(",") if p.strip()]
        checks["group-delay budget"] = gd_budget([float(a) for a, _ in pairs],
                                                 [float(b) for _, b in pairs])
    checks["junction cost"] = junction_cost(args.fc, args.phon)
    if not args.fs:
        print("note: no --fs given, so the driver's own limit was NOT checked -- that is the one "
              "check that can refuse a corner outright\n", file=sys.stderr)
    print(render(checks))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
