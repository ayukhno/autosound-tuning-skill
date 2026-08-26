#!/usr/bin/env python3
"""xover_candidates -- two or three crossover candidates for one driver, DESCRIBED, not chosen.

The dry run of 2026-08-25 settled how a crossover is picked: the tools put 2-3 candidates on the
table, each evaluated on magnitude, phase and impulse, with the driver's strengths and weaknesses
named -- and the tuner chooses. `xover_select.realize_driver` already finds the candidates that
fit a target. This is the DESCRIPTION half: for each one, the numbers a person weighs, every one
of them computed from the candidate's own electrical response or the driver's own measurement, and
the family's character stated as a definition rather than as taste.

For each candidate:
  magnitude   fit against the driver's target (RMS in the trust band); the level AT each corner,
              which for LR is -6.02 dB and for BW -3.01 dB by definition (an anchor, not a result)
  phase       the electrical phase at each corner and how far it turns across the corner octave --
              the number the junction alignment (1.3) will have to absorb
  impulse     the group delay the filters ADD (max in the trust band), against Blauert & Laws via
              `crossover_checks.gd_budget`; a family's ringing character by definition
  the driver  how far each corner sits from the driver's OWN -6 dB points on the measured solo:
              positive = the corner is inside the band the driver actually delivers; negative =
              the corner asks the driver for a region it does not have
  checks      `crossover_checks`: Fs margin at the high-pass corner (needs `--fs`), junction cost

    python3 rew_tool/xover_candidates.py --solos DIR --project DIR --house FILE --channel m-L \\
        --hp 200:400:5 --lp 2500:4000:10 [--fs 90] [--top 3] [--json]
    python3 rew_tool/xover_candidates.py --selftest

It refuses without a solo for the channel, and it never picks: the last line says so.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import crossover_checks                          # noqa: E402
import dsp_math                                  # noqa: E402
import predict as P                              # noqa: E402
import xover_select                              # noqa: E402

#: What each family IS, by definition. Stated once, here, so the description never presents a
#: property of the family as a finding about this car.
FAMILY_CHARACTER = {
    "LR": "Linkwitz-Riley: -6.02 dB at its corner; a matching LR pair sums to flat magnitude at the "
          "corner with both legs in phase. Butterworth squared, so the phase turns twice as fast.",
    "BW": "Butterworth: -3.01 dB at its corner; a matching BW pair sums +3 dB at the corner "
          "(a bump) unless the legs are offset. Maximally flat magnitude.",
    "BE": "Bessel: the gentlest phase and no overshoot in the impulse -- the best transient; the "
          "level at the corner is not -3/-6 dB, read the number. Shallow near the corner.",
}
DRIVER_EDGE_DB = 6.0             # the driver's own band edge: where its solo falls this far below its mid-band


def electrical(freqs, cand):
    """The candidate's own complex response on `freqs` (both legs), from `dsp_math.xo_response`."""
    h = np.ones(len(freqs), dtype=complex)
    for leg in ("hp", "lp"):
        spec = cand.get(leg)
        if spec:
            fam, order, corner = spec
            h = h * dsp_math.xo_response(np.asarray(freqs, float), float(corner), int(order), leg, fam)
    return h


def group_delay_ms(freqs, h):
    """-dphi/domega of a complex response, in ms, on a log grid (numerical, unwrapped)."""
    f = np.asarray(freqs, float)
    phi = np.unwrap(np.angle(h))
    gd = -np.gradient(phi, 2 * np.pi * f)
    return gd * 1000.0


def driver_edges(freqs, mag_db, trust_band):
    """The driver's own -6 dB points (low, high) relative to its mid-band median on the solo."""
    f = np.asarray(freqs, float)
    m = np.asarray(mag_db, float)
    inside = (f >= trust_band[0]) & (f <= trust_band[1])
    if not inside.any():
        raise ValueError(f"trust band {trust_band} holds no points")
    ref = float(np.median(m[inside]))
    k_mid = int(np.argmin(np.abs(f - math.sqrt(trust_band[0] * trust_band[1]))))
    lo = f[0]
    for k in range(k_mid, -1, -1):
        if m[k] < ref - DRIVER_EDGE_DB:
            lo = f[k]
            break
    hi = f[-1]
    for k in range(k_mid, len(f)):
        if m[k] < ref - DRIVER_EDGE_DB:
            hi = f[k]
            break
    return float(lo), float(hi), ref


def describe(freqs, cand, mag_db, trust_band, fs_installed=None, phon=70.0):
    f = np.asarray(freqs, float)
    h = electrical(f, cand)
    hdb = dsp_math.mag_db(h)
    phi = np.degrees(np.unwrap(np.angle(h)))
    lo_edge, hi_edge, _ref = driver_edges(f, mag_db, trust_band)
    d = {"hp": cand.get("hp"), "lp": cand.get("lp"), "trim_db": cand.get("trim_db"),
         "fit_rms_db": cand.get("fit_rms_db"), "score": cand.get("score"), "corners": {}}
    for leg in ("hp", "lp"):
        spec = cand.get(leg)
        if not spec:
            continue
        fam, order, corner = spec
        k = int(np.argmin(np.abs(f - corner)))
        k_lo = int(np.argmin(np.abs(f - corner / math.sqrt(2))))
        k_hi = int(np.argmin(np.abs(f - corner * math.sqrt(2))))
        edge = lo_edge if leg == "hp" else hi_edge
        margin_oct = math.log2(corner / edge) if leg == "hp" else math.log2(edge / corner)
        entry = {"family": fam, "order_db_oct": int(order), "corner_hz": float(corner),
                 "mag_at_corner_db": round(float(hdb[k]), 2),
                 "phase_at_corner_deg": round(float(phi[k]), 1),
                 "phase_turn_across_octave_deg": round(float(phi[k_hi] - phi[k_lo]), 1),
                 "driver_edge_hz": round(edge, 1),
                 "margin_from_driver_edge_oct": round(margin_oct, 2),
                 "junction": crossover_checks.junction_cost(corner, phon),
                 "character": FAMILY_CHARACTER.get(fam, "")}
        if leg == "hp" and fs_installed:
            entry["fs_margin"] = crossover_checks.fs_margin(corner, fs_installed, order=max(int(order) // 6, 1))
        d["corners"][leg] = entry
    gd = group_delay_ms(f, h)
    inside = (f >= trust_band[0]) & (f <= trust_band[1])
    d["gd_added_max_ms"] = round(float(np.max(np.abs(gd[inside]))), 3)
    d["gd_budget"] = crossover_checks.gd_budget(f[inside], gd[inside])
    return d


#: Borrowed, and said so in the refusal: the largest positive channel trim a common processor
#: offers is single digits (the Helix profile says +5 dB). Used only when no DSP profile is at
#: hand -- the CLI passes the profile's own `channel_gain.range_db` and this is never consulted.
TRIM_LIMIT_BORROWED_DB = (-30.0, 12.0)


def candidates(freqs, mag_db, target_db, hp_slot, lp_slot, trust_band, xo_options=None,
               top=3, min_hp_order=None, trim_range_db=None):
    """Distinct top candidates from `realize_driver`, crossovers only (no EQ bands).

    `trim_range_db`: the DSP's channel gain range, (lo, hi). A candidate whose trim falls outside
    it is not a candidate: `realize_driver` fits the target with an UNBOUNDED trim, and on slots
    that make no sense it will happily report a 1.6 dB fit reached with a +127 dB trim -- a
    high-pass at 5 kHz and a low-pass at 65 Hz leave a -130 dB passband, and the trim lifts the
    floor back up. The number that exposes it is the trim, so the trim is what is checked.
    """
    f = np.asarray(freqs, float)
    mag = np.asarray(mag_db, float)
    tgt = np.asarray(target_db, float)
    reals = xover_select.realize_driver(f, mag, tgt, hp_slot=hp_slot, lp_slot=lp_slot,
                                        trust_band=trust_band, xo_options=xo_options or dsp_math.XO_OPTIONS,
                                        eq_bands=0, top_k=max(top * 4, 8), min_hp_order=min_hp_order)
    # `realize_driver` returns the least bad of what the slots allow, always. "Least bad" is not
    # "realises the target": the anchor is NO crossover at all -- if the best candidate fits the
    # target worse than leaving the driver bare (level-trimmed), the slots are wrong, and saying so
    # beats handing over a ranked list of things that all make it worse.
    w = xover_select.fit_weight(f, tgt, trust_band)
    resid_none = mag - tgt
    resid_none = resid_none - np.average(resid_none, weights=w + 1e-12)      # a trim is free
    fit_none = xover_select._wrms(resid_none, w)
    if reals and reals[0]["fit_rms_db"] >= fit_none:
        raise ValueError(f"no candidate in those slots beats NO crossover at all ({reals[0]['fit_rms_db']:.1f} "
                         f"vs {fit_none:.1f} dB RMS): widen a slot or check the target's band against the driver's")
    lo_t, hi_t = trim_range_db or TRIM_LIMIT_BORROWED_DB
    borrowed = trim_range_db is None
    kept = [r for r in reals if lo_t <= float(r["trim_db"]) <= hi_t]
    if reals and not kept:
        worst = reals[0]["trim_db"]
        raise ValueError(f"every candidate needs a trim outside the DSP's range ({lo_t:+.0f}..{hi_t:+.0f} dB"
                         f"{', borrowed default -- pass the profile' if borrowed else ''}): the best wants "
                         f"{worst:+.1f} dB, which means the slots leave no passband and the fit is the "
                         f"floor lifted, not the target realised. Widen a slot or check the target's band")
    seen, out = set(), []
    for r in kept:
        key = (tuple(r["hp"]) if r["hp"] else None, tuple(r["lp"]) if r["lp"] else None)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= top:
            break
    if not out:
        raise ValueError("no candidate realises the target in those slots -- widen a slot or "
                         "check the target's band against the driver's")
    return out


def render(descs, channel):
    lines = [f"{channel}: {len(descs)} candidate(s), best fit first. This describes; the choice is the tuner's.\n"]
    for i, d in enumerate(descs, 1):
        legs = " · ".join(f"{leg.upper()} {c['family']}{c['order_db_oct']} @ {c['corner_hz']:.0f} Hz"
                          for leg, c in d["corners"].items())
        lines.append(f"[{i}] {legs}   fit {d['fit_rms_db']:.2f} dB RMS, trim {d['trim_db']:+.1f} dB")
        for leg, c in d["corners"].items():
            lines.append(f"    {leg}: {c['mag_at_corner_db']:+.2f} dB at the corner, phase {c['phase_at_corner_deg']:+.0f}°, "
                         f"turns {c['phase_turn_across_octave_deg']:+.0f}° across the corner octave; "
                         f"driver's own edge {c['driver_edge_hz']:.0f} Hz -> margin {c['margin_from_driver_edge_oct']:+.2f} oct"
                         + (" (INSIDE the driver's roll-off)" if c['margin_from_driver_edge_oct'] < 0 else ""))
            lines.append(f"        junction {c['junction']['verdict']}: {c['junction']['why']}")
            if "fs_margin" in c:
                lines.append(f"        Fs {c['fs_margin']['verdict']}: {c['fs_margin']['why']}")
        lines.append(f"    impulse: adds {d['gd_added_max_ms']:.2f} ms group delay at most -> "
                     f"{d['gd_budget']['verdict']} ({d['gd_budget']['why']})")
        fams = {c["family"] for c in d["corners"].values()}
        for fam in sorted(fams):
            lines.append(f"    {FAMILY_CHARACTER[fam]}")
        lines.append("")
    lines.append("Not a pick. Weigh the margins against the driver's edges, the phase turn the junction "
                 "must absorb, and the impulse -- then decide, and bank the one you chose.")
    return "\n".join(lines)


def _selftest():
    f = P.grid(20, 20000, 96)
    flat = np.zeros(len(f))
    tgt = dsp_math.mag_db(dsp_math.xo_response(f, 80, 24, "hp", "LR")) \
        + dsp_math.mag_db(dsp_math.xo_response(f, 300, 24, "lp", "LR"))
    cands = candidates(f, flat, tgt, hp_slot=(60, 100, 2), lp_slot=(250, 350, 5), trust_band=(30, 2000), top=3)
    assert 1 <= len(cands) <= 3 and cands[0]["hp"] and cands[0]["lp"], cands
    assert abs(cands[0]["hp"][2] - 80) <= 8 and abs(cands[0]["lp"][2] - 300) <= 30, cands[0]
    descs = [describe(f, c, flat, (30, 2000)) for c in cands]
    # definitions, not results: the level at the corner is the family's own number
    for d in descs:
        for leg, c in d["corners"].items():
            if c["family"] == "LR":
                assert abs(c["mag_at_corner_db"] + 6.02) < 0.35, (leg, c)
            elif c["family"] == "BW":
                assert abs(c["mag_at_corner_db"] + 3.01) < 0.35, (leg, c)
        assert d["gd_added_max_ms"] >= 0 and d["gd_budget"]["verdict"] in ("OK", "CAUTION", "REFUSE")
        # a flat driver has no edge inside the grid: both margins comfortably positive
        assert all(c["margin_from_driver_edge_oct"] > 1.0 for c in d["corners"].values()), d["corners"]
    # order and group delay: same family, same corner, a steeper slope adds MORE delay (definition)
    gd = {}
    for order in (12, 24, 36):
        gd[order] = describe(f, {"hp": ("LR", order, 80.0), "lp": None, "trim_db": 0.0, "fit_rms_db": 0.0,
                                 "score": 0.0}, flat, (30, 2000))["gd_added_max_ms"]
    assert gd[12] < gd[24] < gd[36], gd
    # the driver's own edge is read off the SOLO: a driver rolling off below 100 Hz gets a negative
    # margin for an 80 Hz corner, i.e. the corner is inside its roll-off -- named, not hidden
    rolled = dsp_math.mag_db(dsp_math.xo_response(f, 160, 24, "hp", "LR"))
    d = describe(f, {"hp": ("LR", 24, 80.0), "lp": ("LR", 24, 300.0), "trim_db": 0.0, "fit_rms_db": 0.0,
                     "score": 0.0}, rolled, (60, 2000))
    assert d["corners"]["hp"]["margin_from_driver_edge_oct"] < 0, d["corners"]["hp"]
    assert "INSIDE" in render([d], "w-L")
    # the fs check rides along when Fs is given, and refuses a corner at the driver's resonance
    d2 = describe(f, cands[0], flat, (30, 2000), fs_installed=78.0)
    assert d2["corners"]["hp"]["fs_margin"]["verdict"] == "REFUSE", d2["corners"]["hp"]["fs_margin"]
    try:
        candidates(f, flat, tgt, hp_slot=(5000, 6000, 100), lp_slot=(60, 70, 5), trust_band=(30, 2000))
    except ValueError as exc:
        assert "trim" in str(exc) and "borrowed" in str(exc), str(exc)
    else:
        raise AssertionError("slots that cannot realise the target must refuse, not return the least bad")
    try:
        candidates(f, flat, tgt, hp_slot=(5000, 6000, 100), lp_slot=(60, 70, 5), trust_band=(30, 2000),
                   trim_range_db=(-30.0, 5.0))
    except ValueError as exc:
        assert "-30..+5" in str(exc) and "borrowed" not in str(exc), str(exc)
    else:
        raise AssertionError("with the profile's range the refusal must still fire, naming that range")
    print(f"selftest OK -- {len(cands)} distinct candidates for a flat driver against LR24 80/300, best "
          f"at {cands[0]['hp'][2]:.0f}/{cands[0]['lp'][2]:.0f}; corner levels match the family definitions; "
          f"group delay grows with order ({gd[12]:.2f} < {gd[24]:.2f} < {gd[36]:.2f} ms); a corner "
          f"inside the driver's own roll-off is named; Fs at the corner refuses; nothing is picked")
    return 0


def _slot(spec):
    lo, hi, step = (float(x) for x in spec.split(":"))
    return (lo, hi, step)


def _main(argv=None):
    import argparse
    from eq_propose import channel_targets, _load_house
    import project as _project
    ap = argparse.ArgumentParser(description="crossover candidates for one driver, described, not chosen")
    ap.add_argument("--solos", required=True, metavar="DIR")
    ap.add_argument("--project", required=True)
    ap.add_argument("--house", required=True, metavar="FILE", help="the house curve (REW text)")
    ap.add_argument("--channel", required=True)
    ap.add_argument("--hp", metavar="LO:HI:STEP", help="high-pass corner search, Hz (omit = no high-pass)")
    ap.add_argument("--lp", metavar="LO:HI:STEP", help="low-pass corner search, Hz (omit = no low-pass)")
    ap.add_argument("--fs", type=float, help="the driver's INSTALLED Fs (Hz) -- enables the Fs check")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--preset")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.hp and not args.lp:
        ap.error("at least one of --hp / --lp")

    f = P.grid(20, 20000, 96)
    preset, snap = P.load_project_state(args.project, args.preset)
    chains = P.chains_from_snapshot(snap)
    code = P.canon(args.channel)
    if code not in chains:
        print(f"refusing: {args.channel} is not a channel of preset {preset}", file=sys.stderr)
        return 3
    loaded = P.load_solos_dir(args.solos, f)
    solos, notes, refused = P.de_embed_solos(loaded, f, baseline=True)
    if code not in solos:
        print(f"refusing: no usable solo for {code} in {args.solos}"
              + (f" (refused at de-embed: {', '.join(sorted(refused))})" if refused else ""), file=sys.stderr)
        return 3
    pdata = _project.Project(args.project).load()
    roles = {c["code"]: c.get("role") for c in (pdata.get("channels") or []) if isinstance(c, dict)}
    pairs_of = {}
    for name, members in ((pdata.get("glossary") or {}).get("pairs") or {}).items():
        for m in members:
            pairs_of[m] = name
    targets = channel_targets(f, _load_house(args.house), chains, roles, pairs_of)
    if code not in targets:
        print(f"refusing: no target for {code} (muted or unmodellable in the ledger)", file=sys.stderr)
        return 3
    mag = dsp_math.mag_db(solos[code])
    hp = _slot(args.hp) if args.hp else None
    lp = _slot(args.lp) if args.lp else None
    lo = (hp[0] / 2) if hp else 20.0
    hi = (lp[1] * 2) if lp else 20000.0
    trust = (max(20.0, lo), min(20000.0, hi))
    trim_range = None
    try:
        import dsp_profile
        prof = dsp_profile.load_profile(dsp_profile.profile_path(args.project))
        rng = (dsp_profile._unwrap(prof).get("channel_gain") or {}).get("range_db")
        if rng and len(rng) == 2:
            trim_range = (float(rng[0]), float(rng[1]))
    except (OSError, ValueError):
        pass
    try:
        cands = candidates(f, mag, targets[code], hp, lp, trust, top=args.top, trim_range_db=trim_range)
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 3
    descs = [describe(f, c, mag, trust, fs_installed=args.fs) for c in cands]
    if not args.fs and hp:
        print("note: no --fs, so the one check that can refuse a high-pass corner outright (the "
              "driver's installed Fs) was not run\n", file=sys.stderr)
    print(json.dumps(descs, indent=2) if args.json else render(descs, code))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
