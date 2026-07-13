"""Crossover-filter selection API — skill-facing functions distilled from the
v3 acoustic-target experiment (see DESIGN.md, results_v3.json, wiki/log.md
2026-07-12). Intended for manual integration into the autosound-tuning skill's
rew_tool/ alongside joint_analysis.py.

Method contract (validated on the VW Passat B8 / Helix DSP Ultra S dataset):
  1. MAGNITUDE decisions use RTA/MMM data; PHASE decisions use sweep complex data.
  2. Per-driver: realize an ACOUSTIC target (house curve x acoustic slopes, e.g.
     NTT band files) with whatever electrical XO + level trim + EQ it takes
     (`realize_driver`). Electrical corners routinely land far from acoustic ones.
  3. Neighbor bands MUST be selected as a pair by acoustic-sum quality
     (`select_neighbor_pair`) — independently-good realizations can leave a
     >10 dB hole in the pair sum (v3 run-3 negative result).
  4. Joint phase: analytic delay/polarity (`align_joint`), then APF2 worst-null
     repair (`repair_joint_apf`). Never trade broadband summation for the notch.
  5. L/R electrical symmetry is a guard heuristic, not physics: asymmetric
     electrical XO is acceptable when `lr_phase_tracking` stays comparable to
     the symmetric variant (measured: electrical asymmetry added ~2 deg of the
     ~52 deg cabin-dominated total on woofers).

Dependencies: numpy, scipy (via dsp_math). fs is fixed at 96 kHz in dsp_math.FS.
"""
import numpy as np

from dsp_math import (XO_OPTIONS, align_delay_polarity, apf_search, eq_complex,
                      greedy_eq_fit, mag_db, xo_response)


def fit_weight(freqs, target_mag_db, trust_band):
    """Weight from target shape: passband 1.0, transition 0.3/0.05, stopband 0."""
    t = (freqs >= trust_band[0]) & (freqs <= trust_band[1])
    rel = target_mag_db - np.max(target_mag_db[t])
    w = np.where(rel > -6, 1.0, np.where(rel > -20, 0.3, np.where(rel > -30, 0.05, 0.0)))
    return w * t


def _slot_curves(freqs, slot, kind, xo_options, min_order=None):
    lo, hi, step = slot
    out = []
    for ftype, order in xo_options:
        if min_order and order < min_order:
            continue
        for corner in np.arange(lo, hi + 0.1, step):
            out.append(((ftype, int(order), float(corner)),
                        xo_response(freqs, corner, order, kind, ftype)))
    return out


def _wrms(resid, w):
    wn = w / (np.sum(w) + 1e-12)
    return float(np.sqrt(np.sum(wn * resid * resid)))


def _eval(rta, target, w, hp_h, lp_h):
    xo = 0.0
    if hp_h is not None:
        xo = xo + mag_db(hp_h)
    if lp_h is not None:
        xo = xo + mag_db(lp_h)
    ac = rta + xo
    trim = float(np.sum(w * (target - ac)) / (np.sum(w) + 1e-12))
    return ac + trim - target, trim


def realize_driver(freqs, rta_mag_db, target_mag_db, *, hp_slot=None, lp_slot=None,
                   trust_band, min_hp_order=None, xo_options=XO_OPTIONS,
                   eq_bands=4, top_k=6, no_boost_zones=(), boost_gate=None):
    """Find electrical XO + level trim + EQ realizing an acoustic target.

    hp_slot/lp_slot: (lo_hz, hi_hz, step_hz) hardware search ranges, or None.
    min_hp_order: datasheet/installed-Fs protection floor (dB/oct), e.g. 12.
    no_boost_zones: static (lo, hi) Hz zones (car-record knowledge).
    boost_gate: eq_gate.ExcessPhaseGate.as_boost_gate() — measurement-driven
      veto of PK boosts into deep phase-anomalous notches (build the gate from
      the same driver's sweep + REW excess-phase version).
    Returns top_k realizations sorted by post-EQ score:
      {"hp": (type, order, corner)|None, "lp": ..., "trim_db", "eq": [(kind, f0,
       gain, q)...], "fit_rms_db", "score"}.
    """
    w = fit_weight(freqs, target_mag_db, trust_band)
    hp_set = _slot_curves(freqs, hp_slot, "hp", xo_options, min_hp_order) \
        if hp_slot else [(None, None)]
    lp_set = _slot_curves(freqs, lp_slot, "lp", xo_options) if lp_slot else [(None, None)]

    hp_cfg, hp_h = (None, None)
    if hp_slot:
        c0 = float(round(np.sqrt(hp_slot[0] * hp_slot[1])))
        hp_cfg, hp_h = ("LR", 24, c0), xo_response(freqs, c0, 24, "hp", "LR")
    lp_cfg, lp_h = (None, None)

    def pick(entries, fixed_h, varying):
        best = (1e9, None, None)
        for cfg, h in entries:
            hh, lh = (h, fixed_h) if varying == "hp" else (fixed_h, h)
            resid, _ = _eval(rta_mag_db, target_mag_db, w, hh, lh)
            s = _wrms(resid, w)
            if s < best[0]:
                best = (s, cfg, h)
        return best[1], best[2]

    for _ in range(2):
        if lp_slot:
            lp_cfg, lp_h = pick(lp_set, hp_h, "lp")
        if hp_slot:
            hp_cfg, hp_h = pick(hp_set, lp_h, "hp")

    scored = {}
    for cfg, h in lp_set:
        resid, _ = _eval(rta_mag_db, target_mag_db, w, hp_h, h)
        scored[(hp_cfg, cfg)] = _wrms(resid, w)
    for cfg, h in hp_set:
        resid, _ = _eval(rta_mag_db, target_mag_db, w, h, lp_h)
        scored[(cfg, lp_cfg)] = _wrms(resid, w)
    ranked = sorted(scored.items(), key=lambda kv: kv[1])[:top_k]

    out = []
    for (hp, lp), _pre in ranked:
        hp_r = xo_response(freqs, hp[2], hp[1], "hp", hp[0]) if hp else None
        lp_r = xo_response(freqs, lp[2], lp[1], "lp", lp[0]) if lp else None
        resid, trim = _eval(rta_mag_db, target_mag_db, w, hp_r, lp_r)
        lo = max(trust_band[0], hp[2] / 2 if hp else trust_band[0])
        hi = min(trust_band[1], lp[2] * 2 if lp else trust_band[1])
        bands, resid_after = greedy_eq_fit(freqs, resid, w, n_bands=eq_bands,
                                           band=(lo, hi),
                                           no_boost_zones=no_boost_zones,
                                           boost_gate=boost_gate)
        fit = _wrms(resid_after, w)
        out.append({"hp": hp, "lp": lp, "trim_db": trim, "eq": bands,
                    "fit_rms_db": fit,
                    "score": fit + 0.02 * sum(abs(b[2]) for b in bands)})
    out.sort(key=lambda r: r["score"])
    return out


def apply_realization(freqs, h_raw, realization):
    """Complex branch = raw response x XO x EQ x trim (no delay/polarity)."""
    h = np.asarray(h_raw, dtype=complex).copy()
    for cfg, kind in ((realization["hp"], "hp"), (realization["lp"], "lp")):
        if cfg:
            h = h * xo_response(freqs, cfg[2], cfg[1], kind, cfg[0])
    return h * eq_complex(freqs, realization["eq"]) * 10 ** (realization["trim_db"] / 20.0)


def align_joint(freqs, h_lo, h_hi, band, *, max_delay_ms=3.0):
    """Delay (applied to h_hi) + polarity maximizing coherent summation in band.
    Near-tie delays resolve to the smallest |tau| (impulse compactness)."""
    pol, tau, null = align_delay_polarity(freqs, h_lo, h_hi, band,
                                          max_delay_ms=max_delay_ms)
    return {"polarity": pol, "delay_ms": round(tau, 2), "worst_null_db": round(null, 2)}


def repair_joint_apf(freqs, h_lo, h_hi_aligned, band, *, min_gain_db=0.5):
    """APF2 (f0, q) improving the worst energy-significant null without losing
    broadband summation. An allpass only ADDS phase lag, so the repair may
    belong on either branch — both are tried; result says which via "apply_to".
    CAUTION: apply_to="lo" rotates that branch's OTHER joint too — re-verify it.
    Returns {"f0_hz","q","null_gain_db","apply_to"} or None."""
    best = None
    for side in ("hi", "lo"):
        f0, q, g = apf_search(freqs, h_lo, h_hi_aligned, band, apply_to=side)
        if f0 is not None and g >= min_gain_db and (best is None or g > best["null_gain_db"]):
            best = {"f0_hz": round(f0, 1), "q": q, "null_gain_db": round(g, 2),
                    "apply_to": side}
    return best


def select_neighbor_pair(freqs, branches_lo, branches_hi, fits_lo, fits_hi,
                         band, house_mag_db, *, max_delay_ms=3.0):
    """Joint-aware pair selection (MANDATORY between adjacent bands).
    branches_*: candidate complex branches (post-apply_realization).
    fits_*: matching per-driver fit_rms_db lists.
    Returns (i_lo, i_hi, details) minimizing
      0.5*(fit_lo+fit_hi) + sum_rms_vs_house + 0.5*max(0, -null-3)."""
    m = (freqs >= band[0]) & (freqs <= band[1])
    best = None
    for i, (bl, fl) in enumerate(zip(branches_lo, fits_lo)):
        for j, (bh, fh) in enumerate(zip(branches_hi, fits_hi)):
            pol, tau, null = align_delay_polarity(freqs, bl, bh, band,
                                                  max_delay_ms=max_delay_ms)
            s = bl[m] + pol * bh[m] * np.exp(-2j * np.pi * freqs[m] * tau / 1000.0)
            sm = mag_db(s)
            anchor = np.median(sm - house_mag_db[m])
            rms = float(np.sqrt(np.mean((sm - house_mag_db[m] - anchor) ** 2)))
            score = 0.5 * (fl + fh) + rms + 0.5 * max(0.0, -null - 3.0)
            if best is None or score < best[0]:
                best = (score, i, j, {"polarity": pol, "delay_ms": round(tau, 2),
                                      "worst_null_db": round(null, 2),
                                      "sum_vs_house_rms_db": round(rms, 2)})
    return best[1], best[2], best[3]


def lr_phase_tracking(freqs, h_L, h_R, band):
    """Imaging guard for (a)symmetric electrical XO decisions: weighted RMS of
    L/R phase divergence after removing constant+linear terms (what imaging TA
    can absorb). Unreliable above ~3 kHz from single-point sweeps."""
    m = (freqs >= band[0]) & (freqs <= band[1])
    w = np.minimum(np.abs(h_L[m]), np.abs(h_R[m]))
    wdb = 20 * np.log10(w + 1e-12)
    keep = wdb >= np.max(wdb) - 26.0
    f, w = freqs[m][keep], w[keep]
    ph = np.unwrap(np.angle(h_L[m][keep] * np.conj(h_R[m][keep])))
    W = w / (np.sum(w) + 1e-12)
    A = np.vstack([np.ones_like(f), f]).T
    coef = np.linalg.solve((A * W[:, None]).T @ A, (A * W[:, None]).T @ ph)
    resid = ph - A @ coef
    # equiv_delay_ms > 0 means R arrives later; delaying L by this value would
    # phase-match the pair (the legitimate imaging-TA component)
    return {"rms_deg": round(float(np.degrees(np.sqrt(np.sum(W * resid ** 2)))), 1),
            "equiv_delay_ms": round(float(coef[1] / (2 * np.pi) * 1000.0), 3)}


def _selftest():
    freqs = np.geomspace(20.0, 20000.0, 480)
    flat = np.ones_like(freqs, dtype=complex)

    # 1) realize_driver recovers a known acoustic LR24 80-300 bandpass on a flat driver
    tgt = mag_db(xo_response(freqs, 80, 24, "hp", "LR")) \
        + mag_db(xo_response(freqs, 300, 24, "lp", "LR"))
    real = realize_driver(freqs, np.zeros_like(freqs), tgt,
                          hp_slot=(60, 100, 2), lp_slot=(250, 350, 5),
                          trust_band=(30, 2000))
    r0 = real[0]
    assert r0["fit_rms_db"] < 0.5, r0
    assert abs(r0["hp"][2] - 80) <= 8 and abs(r0["lp"][2] - 300) <= 30, r0

    # 2) align_joint undoes a known delay + inversion
    lo = flat * xo_response(freqs, 300, 24, "lp", "LR")
    hi0 = flat * xo_response(freqs, 300, 24, "hp", "LR")
    hi = -hi0 * np.exp(-2j * np.pi * freqs * 0.35e-3)
    al = align_joint(freqs, lo, hi, (150, 600), max_delay_ms=1.5)
    # near-tie rule may trade a bit of tau for impulse compactness; the sum must
    # still be essentially perfect
    assert al["polarity"] == -1 and abs(al["delay_ms"] + 0.35) < 0.15, al
    assert al["worst_null_db"] > -0.5, al

    # 3) lr_phase_tracking: pure delay between L and R -> ~0 residual, delay recovered
    hR = lo * np.exp(-2j * np.pi * freqs * 0.8e-3)
    tr = lr_phase_tracking(freqs, lo, hR, (80, 450))
    assert tr["rms_deg"] < 2.0 and abs(tr["equiv_delay_ms"] - 0.8) < 0.05, tr

    # 4) joint-aware pair selection prefers complementary corners over a hole
    lo_a = flat * xo_response(freqs, 300, 24, "lp", "LR")   # complementary
    lo_b = flat * xo_response(freqs, 150, 24, "lp", "LR")   # leaves a hole vs hp 300
    hi_a = flat * xo_response(freqs, 300, 24, "hp", "LR")
    house = np.zeros_like(freqs)
    i, j, det = select_neighbor_pair(freqs, [lo_a, lo_b], [hi_a], [1.0, 1.0], [1.0],
                                     (150, 600), house)
    assert i == 0, (i, det)

    # 5) APF repair on a synthetic allpass-induced notch. Low-Q rotation is
    # absorbed by delay during alignment (verified: null -0.26 dB, repair
    # correctly returns None); a HIGH-Q narrow rotation is what delay cannot
    # fix and APF2 must repair.
    from dsp_math import apf2_response
    hi_rot = hi0 * apf2_response(freqs, 300, 4.0)
    al2 = align_joint(freqs, lo, hi_rot, (150, 600), max_delay_ms=1.5)
    hi_al = al2["polarity"] * hi_rot * np.exp(-2j * np.pi * freqs * al2["delay_ms"] * 1e-3)
    rep = repair_joint_apf(freqs, lo, hi_al, (150, 600))
    assert rep is not None and rep["null_gain_db"] > 0.5, rep

    print("selftest OK -- realize(fit=%.2f dB, hp=%s, lp=%s) + align(pol=%d, %.2f ms) "
          "+ lr_track(%.1f deg, %.3f ms) + pair-select(no-hole) + apf(+%.2f dB)"
          % (r0["fit_rms_db"], r0["hp"], r0["lp"], al["polarity"], al["delay_ms"],
             tr["rms_deg"], tr["equiv_delay_ms"], rep["null_gain_db"]))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        print("usage: python xover_select.py --selftest")
