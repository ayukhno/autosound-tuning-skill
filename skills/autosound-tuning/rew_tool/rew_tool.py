#!/usr/bin/env python3
"""
REW Analysis Tool — car audio EQ helper.
Usage: python3 rew_tool.py [--curves-dir PATH]
"""

import sys
import os
import argparse
import cmath
import math

sys.path.insert(0, os.path.dirname(__file__))

import rew_api as api
import analysis as an
import joint_analysis as ja
from target_curves import find_target_curve, load_target_curve, interpolate_target

DEFAULT_CURVES_DIR = os.path.expanduser(
    "~/Documents/home/EMMA_2026-05/7. HelixDSP v4 ResoNix_ACС/ResoNix_Accurate_50db_REW 2"
)

SEP = "─" * 70

# Canonical analysis bands (short labels for the batch matrix columns).
BANDS = [
    ("Суббас",  20,    80),
    ("Бас",     80,   250),
    ("Мідбас", 250,   500),
    ("СЧ-н",   500,  2000),
    ("СЧ-в",  2000,  8000),
    ("ВЧ",    8000, 20000),
]


def print_header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def list_measurements(measurements):
    print_header("Виміри в REW")
    for mid, info in sorted(measurements.items(), key=lambda x: int(x[0])):
        title = info.get("title", "—")
        date = info.get("date", "")
        print(f"  [{mid:>2}]  {title:<30}  {date}")


def detect_mode(title):
    """x0 in title → crossover mode (Generic/Extended), else EQ mode."""
    return "crossover" if "x0" in title.lower() else "eq"


def print_fr_analysis(freqs, mag, phase, title="АЧХ / Фаза"):
    print_header(title)

    bands = [
        ("Суббас",    20,   80),
        ("Бас",       80,  250),
        ("Мідбас",   250,  500),
        ("СЧ нижні", 500, 2000),
        ("СЧ верхні",2000, 8000),
        ("ВЧ",       8000,20000),
    ]
    for name, f_lo, f_hi in bands:
        stats = an.analyze_fr(freqs, mag, phase, f_lo, f_hi)
        if stats:
            print(f"  {name:<12} {f_lo:>5}–{f_hi:<6} Hz  "
                  f"mid={stats['mean_dB']:6.1f} dB  "
                  f"min={stats['min_dB']:6.1f} @ {stats['min_freq']:>7.1f} Hz  "
                  f"max={stats['max_dB']:6.1f} @ {stats['max_freq']:>7.1f} Hz  "
                  f"Δ={stats['range_dB']:.1f} dB")

    if phase is None:
        print(f"\n  Фаза: недоступна (RTA-вимір — лише магнітуда)")
    else:
        anomalies = an.find_phase_anomalies(freqs, phase)
        if anomalies:
            print(f"\n  Фазові аномалії (>30°/окт):")
            for f, rate in anomalies[:10]:
                print(f"    {f:>8.1f} Hz  {rate:.0f}°/окт")


def print_ir_analysis(times, ir):
    print_header("Імпульсна відповідь")
    stats = an.analyze_impulse(times, ir)
    print(f"  Пік:         {stats['peak_time_ms']:.3f} мс  ({stats['peak_dB']:.1f} dB)")
    print(f"  Предімпульс: {stats['pre_ringing_dB']:.1f} dB відносно піку")


def print_gd_analysis(freqs, gd):
    print_header("Group Delay")
    bands = [(20, 100), (100, 500), (500, 2000), (2000, 10000)]
    for f_lo, f_hi in bands:
        stats = an.analyze_group_delay(freqs, gd, f_lo, f_hi)
        if stats:
            print(f"  {f_lo:>5}–{f_hi:<6} Hz  "
                  f"mean={stats['mean_ms']:6.2f} мс  "
                  f"max={stats['max_ms']:6.2f} мс @ {stats['peak_freq']:.0f} Hz  "
                  f"Δ={stats['range_ms']:.2f} мс")


def print_distortion(dist_data):
    if not dist_data:
        print_header("Спотворення")
        print("  Дані недоступні для цього виміру.")
        return
    print_header("Спотворення")
    # Show top THD peaks
    freqs_key = None
    for k in dist_data:
        if "freq" in k.lower():
            freqs_key = k
            break
    print(f"  Дані отримано: {list(dist_data.keys())[:5]}")


def print_deviation(meas_freqs, meas_mag, target_freqs, target_mag, target_file):
    print_header(f"Відхилення від цілі: {os.path.basename(target_file)}")
    from target_curves import interpolate_target
    target_at_meas = interpolate_target(target_freqs, target_mag, meas_freqs)

    bands = [(20, 80), (80, 250), (250, 500), (500, 2000), (2000, 8000), (8000, 20000)]
    for f_lo, f_hi in bands:
        zone = [(f, m - t) for f, m, t in zip(meas_freqs, meas_mag, target_at_meas)
                if f_lo <= f <= f_hi]
        if not zone:
            continue
        devs = [d for _, d in zone]
        mean_dev = sum(devs) / len(devs)
        max_cut = min(devs)
        max_boost = max(devs)
        f_cut = zone[devs.index(max_cut)][0]
        f_boost = zone[devs.index(max_boost)][0]
        print(f"  {f_lo:>5}–{f_hi:<6} Hz  "
              f"mean={mean_dev:+6.1f}  "
              f"max cut={max_cut:+5.1f}@{f_cut:.0f}  "
              f"max boost={max_boost:+5.1f}@{f_boost:.0f}")

    # Find largest deviations — EQ candidates (only negative = cuts)
    all_devs = [(f, m - t) for f, m, t in zip(meas_freqs, meas_mag, target_at_meas)
                if 20 <= f <= 20000]
    cuts = sorted([(f, d) for f, d in all_devs if d > 1.5], key=lambda x: -x[1])
    if cuts:
        print(f"\n  Ділянки що перевищують ціль (>+1.5 dB) → кандидати на зрізання:")
        for f, d in cuts[:8]:
            print(f"    {f:>8.1f} Hz  {d:+.1f} dB")


def suggest_eq_cuts(meas_freqs, meas_mag, target_freqs, target_mag):
    """Suggest PEQ bands (cuts only) to bring FR toward target."""
    from target_curves import interpolate_target
    target_at_meas = interpolate_target(target_freqs, target_mag, meas_freqs)
    deviation = [m - t for m, t in zip(meas_mag, target_at_meas)]

    # Find local maxima in deviation > 1.5 dB
    suggestions = []
    n = len(meas_freqs)
    for i in range(1, n - 1):
        d = deviation[i]
        if d > 1.5 and d >= deviation[i-1] and d >= deviation[i+1]:
            f = meas_freqs[i]
            if 20 <= f <= 20000:
                # Estimate Q: half-power bandwidth
                half = d / 2
                lo_idx = i
                while lo_idx > 0 and deviation[lo_idx] > half:
                    lo_idx -= 1
                hi_idx = i
                while hi_idx < n - 1 and deviation[hi_idx] > half:
                    hi_idx += 1
                f_lo = meas_freqs[lo_idx]
                f_hi = meas_freqs[hi_idx]
                bw = f_hi - f_lo if f_hi > f_lo else f * 0.3
                q = round(f / bw, 1) if bw > 0 else 2.0
                q = max(0.5, min(q, 10.0))
                suggestions.append({
                    "freq": round(f, 1),
                    "gain": round(-d, 1),
                    "Q": q,
                    "type": "PEQ",
                })
    return suggestions[:10]


def _band_mean_dev(freqs, dev, f_lo, f_hi):
    """Mean of the (measured − target) deviation within a band, or None if the
    band is empty for this measurement."""
    zone = [d for f, d in zip(freqs, dev) if f_lo <= f <= f_hi]
    if not zone:
        return None
    return sum(zone) / len(zone)


def analyze_batch(pattern, curves_dir, vs_targets=True):
    """Mass analysis: ONE consolidated deviation matrix for every measurement
    whose title contains `pattern` (e.g. "_2 (rta)").

    Speed vs the interactive REPL: one `get_measurements()` for the whole batch,
    then exactly ONE FR-only `get_fr` per driver (not the 5-endpoint per-measure
    fan-out) — cuts round-trips ~5× and collapses N verbose dumps into one
    review-ready table. Math is unchanged (`compute_deviation`); only the
    orchestration + rendering are new, so precision is identical to the REPL.

    RTA-safe: reads magnitude only (get_fr returns phase=None for RTA).
    """
    measurements = api.get_measurements()          # ONE call for the whole batch
    matches = [(int(mid), info.get("title", ""))
               for mid, info in measurements.items()
               if pattern.lower() in (info.get("title", "") or "").lower()]
    matches.sort()
    if not matches:
        print(f"\n  Немає замірів, що містять '{pattern}'.")
        return matches

    print_header(f"BATCH-АНАЛІЗ: '{pattern}'  ({len(matches)} замірів)")
    band_names = [b[0] for b in BANDS]
    if vs_targets:
        print(f"  Цілі з: {curves_dir}")
        print(f"  Клітинка = середнє відхилення (замір − ціль) у смузі, dB.")
        print(f"  anchor = офсет 300–3000 Гц (відніми від смуг → чиста форма); "
              f"ripple = розкид смуг після anchor (нерівність форми).\n")
        hdr = f"  {'Driver':<20}" + "".join(f"{bn:>8}" for bn in band_names)
        hdr += f"{'anchor':>8}{'ripple':>8}"
    else:
        print(f"  Середній рівень у смузі, dB (без цілі).\n")
        hdr = f"  {'Driver':<20}" + "".join(f"{bn:>8}" for bn in band_names)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    no_target = []
    for mid, title in matches:
        freqs, mag, phase = api.get_fr(mid)        # ONE GET per driver (FR-only)
        row = f"  {title:<20}"
        if vs_targets:
            tfile, tdata = find_target_curve(title, curves_dir)
            if not tdata:
                no_target.append(title)
                print(row + "".join(f"{'—':>8}" for _ in band_names) +
                      f"{'—':>8}{'—':>8}   (немає цілі)")
                continue
            tfreqs, tmag = tdata
            _, dev = an.compute_deviation(freqs, mag, tfreqs, tmag)
            band_means = [_band_mean_dev(freqs, dev, lo, hi) for _, lo, hi in BANDS]
            anchor = _band_mean_dev(freqs, dev, 300, 3000)
            for m in band_means:
                row += f"{m:>+8.1f}" if m is not None else f"{'—':>8}"
            if anchor is not None:
                shape = [bm - anchor for bm in band_means if bm is not None]
                ripple = (max(shape) - min(shape)) if shape else 0.0
                row += f"{anchor:>+8.1f}{ripple:>8.1f}"
            else:
                row += f"{'—':>8}{'—':>8}"
        else:
            for _, lo, hi in BANDS:
                st = an.analyze_fr(freqs, mag, None, lo, hi)
                row += f"{st['mean_dB']:>8.1f}" if st else f"{'—':>8}"
        print(row)

    if no_target:
        print(f"\n  ⚠️ Без відповідної per-band цілі: {', '.join(no_target)} "
              f"(перевір --curves-dir / іменування).")
    print(f"\n  Деталі по одному драйверу → інтерактивний режим (без аргументів).")
    print(f"{SEP}\n")
    return matches


def _resample_complex(freqs, mag_db, phase_deg, query_freqs):
    """Resample a (mag_db, phase_deg) trace onto `query_freqs` by linear
    interpolation of the COMPLEX real/imag parts (wrap-safe — never linear-
    interpolates raw wrapped phase). Two solo sweeps from different measurements
    can land on different grids; the joint math needs them index-aligned."""
    n = min(len(mag_db), len(phase_deg))
    re = [10 ** (mag_db[k] / 20.0) * math.cos(math.radians(phase_deg[k])) for k in range(n)]
    im = [10 ** (mag_db[k] / 20.0) * math.sin(math.radians(phase_deg[k])) for k in range(n)]
    re_q = interpolate_target(freqs[:n], re, query_freqs)
    im_q = interpolate_target(freqs[:n], im, query_freqs)
    mag_q, ph_q = [], []
    for r, i in zip(re_q, im_q):
        amp = math.hypot(r, i)
        mag_q.append(20 * math.log10(amp) if amp > 0 else -120.0)
        ph_q.append(math.degrees(math.atan2(i, r)))
    return mag_q, ph_q


def _parse_joint(spec):
    """'lo,hi,fc[,pairMeasurementName]' → (lo, hi, fc, pair_or_None)."""
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) < 3:
        raise ValueError(f"стик '{spec}': треба 'lo,hi,fc[,pair]'")
    lo, hi, fc = parts[0], parts[1], float(parts[2])
    pair = parts[3] if len(parts) > 3 and parts[3] else None
    return lo, hi, fc, pair


def _parse_apf(spec):
    """'ch,APF1,f0' | 'ch,APF2,f0,Q' → (ch, kind, f0, q_or_None).

    A candidate all-pass to VERIFY — one the Arbiter dialled by hand in TCC's curve window while
    watching the predicted sum (SCR-050 item 2), not one this tool computed. `APF1`/`APF2` are the
    ledger's own band types (`state.EQ_TYPES`); the Helix "Phase" angle is deliberately not
    accepted here — it is one vendor's control and takes an angle, not an f0."""
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) < 3:
        raise ValueError(f"all-pass '{spec}': треба 'ch,APF1,f0' або 'ch,APF2,f0,Q'")
    ch, kind = parts[0], parts[1].upper()
    if kind not in ("APF1", "APF2"):
        raise ValueError(f"all-pass '{spec}': тип має бути APF1 або APF2, не '{parts[1]}'")
    f0 = float(parts[2])
    if not f0 > 0:
        raise ValueError(f"all-pass '{spec}': f0 має бути > 0 Гц")
    if kind == "APF1":
        if len(parts) > 3 and parts[3]:
            raise ValueError(f"all-pass '{spec}': APF1 не має Q")
        return ch, kind, f0, None
    if len(parts) < 4 or not parts[3]:
        raise ValueError(f"all-pass '{spec}': APF2 потребує Q ('ch,APF2,f0,Q')")
    q = float(parts[3])
    if not q > 0:
        raise ValueError(f"all-pass '{spec}': Q має бути > 0")
    return ch, kind, f0, q


def _apf_label(kind, f0, q):
    return f"{kind} {f0:g} Hz" + (f" Q {q:g}" if q is not None else "")


def _apf_rotation(kind, f0, q, freqs):
    """The candidate's complex response on `freqs` — from `dsp_math`, the ONE implementation of
    the filter (numpy; imported here so the plain analyze-joints path stays pure Python)."""
    import numpy as np
    import dsp_math

    f = np.asarray(freqs, dtype=float)
    h = dsp_math.apf1_response(f, f0) if kind == "APF1" else dsp_math.apf2_response(f, f0, q)
    return [complex(v) for v in h]


def _rotate_trace(mag_db, phase_deg, rotation):
    """A (mag, phase) trace with a unit-magnitude rotation applied: the phase moves, the level
    does not — which is what makes it an all-pass, and what the Critic is asked to check."""
    n = min(len(mag_db), len(phase_deg), len(rotation))
    return (list(mag_db[:n]),
            [phase_deg[k] + math.degrees(cmath.phase(rotation[k])) for k in range(n)])


def _worst_null(f, a, b, pol=1, tau_ms=0.0):
    """(worst null in dB against |a|+|b|, at which Hz) of a + pol·b·delay, at ONE setting.

    `align_by_summation` searches the delay; this reads the joint AS IT STANDS — the solos were
    captured under the DSP's current delays, so tau=0, pol=+1 is "no further change"."""
    worst, where = 0.0, None
    tau = tau_ms / 1000.0
    for k in range(len(f)):
        sk = a[k] + pol * b[k] * cmath.exp(-1j * 2 * math.pi * f[k] * tau)
        ceil = abs(a[k]) + abs(b[k])
        if ceil > 0:
            r = 20 * math.log10(abs(sk) / ceil) if abs(sk) > 0 else -120.0
            if r < worst:
                worst, where = r, f[k]
    return round(worst, 2), (round(where, 1) if where is not None else None)


def _check_candidate(hz, mA, pA, mB, pB, band, lo, hi, candidates):
    """What a hand-dialled all-pass does to THIS joint, three ways, on the measured solos.

    `now`: the joint as it stands (no change). `with_apf`: the candidate applied and nothing else
    moved — the reading TCC's predicted sum showed. `with_apf_and_delay`: the candidate plus the
    best further delay/polarity, so the reader can tell "the rotation fixes it" from "the rotation
    plus a delay change would". Same band, same measured pair of solos as the row above it — the
    trust label of that row applies to all three."""
    keep = ja._in_band(hz, band)
    f = [hz[k] for k in keep]
    A = ja._complex_trace(mA, pA)
    B = ja._complex_trace(mB, pB)
    a = [A[k] for k in keep]
    b = [B[k] for k in keep]
    now_db, now_hz = _worst_null(f, a, b)
    mA2, pA2, mB2, pB2 = mA, pA, mB, pB
    applied = []
    if lo in candidates:
        kind, f0, q = candidates[lo]
        mA2, pA2 = _rotate_trace(mA, pA, _apf_rotation(kind, f0, q, hz))
        applied.append(f"{_apf_label(kind, f0, q)} on {lo}")
    if hi in candidates:
        kind, f0, q = candidates[hi]
        mB2, pB2 = _rotate_trace(mB, pB, _apf_rotation(kind, f0, q, hz))
        applied.append(f"{_apf_label(kind, f0, q)} on {hi}")
    A2 = ja._complex_trace(mA2, pA2)
    B2 = ja._complex_trace(mB2, pB2)
    with_db, with_hz = _worst_null(f, [A2[k] for k in keep], [B2[k] for k in keep])
    al2 = ja.align_by_summation(hz, mA2, pA2, mB2, pB2, band=band)
    return {"applied": applied,
            "now_null_db": now_db, "now_null_hz": now_hz,
            "with_null_db": with_db, "with_null_hz": with_hz,
            "with_delay_null_db": al2["residual_null_db"],
            "with_delay_ms": al2["delay_ms"], "with_polarity": al2["polarity"],
            "helps": with_db > now_db + 0.5}


def _edge_f(edge):
    """A crossover edge (hp/lp) → its frequency, or None when disabled/OFF/null."""
    if isinstance(edge, dict):
        f = edge.get("f")
        return float(f) if f not in (None, "OFF", "off") else None
    return None


def _is_sub(ch):
    return ch.lower().startswith(("sw", "sub"))


def _side_of(ch):
    if ch.endswith("-L"):
        return "L"
    if ch.endswith("-R"):
        return "R"
    return "sub" if _is_sub(ch) else "other"   # center/rear ('other') → Phase 5, skip


def _joints_from_state(state_root, preset=None, ver_state=None):
    """Derive the joint map (adjacent driver pairs + crossover freq) from a
    versioned state snapshot's crossovers — so `analyze-joints` needn't be
    hand-fed `lo,hi,fc`. Works against the ACTIVE slot by default (the multi-
    slot guardrail: never a neighbour slot). The measured `pair` for the phase-
    trust gate is a measurement-naming convention, not in state, so state-derived
    joints carry no pair (→ UNVERIFIED) until the user attaches one via --joint.

    Returns (preset, version, [(lo, hi, fc, None), …]) sorted low→high per side.
    """
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import state as st

    if preset is None:
        preset = st.Registry(state_root).get_active()
        if not preset:
            raise ValueError(f"active slot не задано в registry ({state_root}); "
                             f"вкажи --preset")
    snap = st.PresetHistory(state_root, preset).load(ver_state)
    channels = snap.get("channels", {})
    edges = {ch: (_edge_f(cfg.get("hp")), _edge_f(cfg.get("lp")))
             for ch, cfg in channels.items()}

    joints, seen = [], set()
    for side in ("L", "R"):
        grp = [ch for ch in channels
               if _side_of(ch) == side or _side_of(ch) == "sub"]
        # sort by high edge (lp); a full-range top (lp=None, e.g. tweeter) → last
        grp.sort(key=lambda ch: edges[ch][1] if edges[ch][1] is not None else float("inf"))
        for lo, hi in zip(grp, grp[1:]):
            fc = edges[lo][1]                    # lo's lp = the crossover at this joint
            if fc is None or (lo, hi) in seen:
                continue
            seen.add((lo, hi))
            joints.append((lo, hi, float(fc), None))
    return preset, snap.get("version"), joints


def analyze_joints(joint_specs, ver="2", band_oct=1.0, candidates=None):
    """Batch joint/group analysis: walk every adjacent joint in ONE pass and
    render one consolidated table (polarity + drift-immune delay + residual +
    APF suggestion per joint), reusing joint_analysis.py unchanged.

    `candidates` = {channel: (kind, f0, q)} — all-passes to VERIFY rather than
    propose (SCR-050 item 2): the ones the Arbiter dialled by hand in TCC's
    curve window against the predicted sum. Every joint touching such a
    channel gets one more line — the joint as it stands, with the candidate
    and nothing else changed, and with the candidate plus the best further
    delay — under the SAME trust gate as the row above it: no pair → the
    candidate is UNVERIFIED too; gate tripped → nothing is computed for it.

    Honesty (matches the Phase-2b method + the core phase guardrail): a joint's
    computed delay/polarity/APF is trustworthy ONLY when the complex solos
    reproduce a measured pair (`phase_trust_gate`). So:
      • pair given + phase reliable → emit the phase-verified alignment.
      • pair given + phase UNreliable → BLOCK the computed delay/APF; fall back
        to the magnitude power-sum verdict (`joint_summation_check`) and tell the
        user to flip polarity + re-measure.
      • no pair given → still compute the alignment but flag it UNVERIFIED —
        confirm by summation before entering it.

    Speed: ONE get_measurements() for the whole batch; per joint, two FR pulls
    (the two solo sweeps) + an optional pair pull — every joint in one command
    instead of hand-driving joint_analysis.py pair-by-pair.
    """
    ms = api.get_measurements()                     # ONE call for the whole batch

    def resolve(name):
        return api.find_measurement_id(name, measurements=ms, exact=True)

    print_header(f"BATCH-АНАЛІЗ СТИКІВ  ({len(joint_specs)} стик(ів) · solo = _{ver} (sw))")
    print("  align_by_summation = дрейф-імунна полярність+затримка з сумування; "
          "trust = чи комплексні solo відтворюють виміряну пару.")
    print("  ⚠️ Без пари (nopair) або BLOCK → НЕ вводь обчислену затримку/APF: "
          "перекинь полярність і переміряй сумування.")
    candidates = dict(candidates or {})
    if candidates:
        print("  ↳ кандидати all-pass (виставлені вручну, ПЕРЕВІРЯЄМО, не пропонуємо): "
              + "; ".join(f"{ch}: {_apf_label(*spec)}" for ch, spec in candidates.items())
              + " — null «зараз» → «з APF» (без інших змін) → «з APF + найкраща затримка»,"
                " довіра та сама, що в рядку стику.")
    print()
    hdr = (f"  {'Joint':<15}{'fc':>6}{'band':>12}{'trust':>12}"
           f"{'pol':>5}{'delay_ms':>9}{'resid':>7}{'APF f0/Q':>10}  verdict")
    print(hdr)
    print("  " + "-" * 96)

    rows = []
    touched = set()
    for lo, hi, fc, pair_name in joint_specs:
        # An octave either side of the declared corner. Investigated 2026-08-23 and deliberately
        # LEFT ALONE — the note is here because this is where the next person will have the idea.
        #
        # The tempting change is "bound the band by the ELECTRICAL legs instead". As a rule it is
        # sound, but only once the right pair is picked: **the two legs that FACE EACH OTHER across
        # this junction**. For sub/w that is the sub's LPF and the midbass's HPF (88 and 86 on the
        # reference car) — NOT the midbass's own LPF (215), which belongs to the next junction
        # along. Taking both legs from one channel put the window's top at 215, where the sub is
        # already 46 dB down: not overlap, but a region where the junction has finished happening.
        #
        # And with the right pair the change buys nothing here: every defining corner on all three
        # junctions already falls inside this window (88/86 in 35–140, 215/460 in 160–640,
        # 2000/3625 in 1750–7000). The window is not OPTIMAL — at fc 70 the action is 86–140 and
        # the lower half is mostly quiet — but no measurement we have distinguishes the two, and
        # the sum-loss dip at 117 Hz was seen by this window and by the cross-check's independent
        # implementation alike. **Optimality with no failing case is the change that looks like
        # progress and cannot be tested.**
        band = (fc / (2 ** band_oct), fc * (2 ** band_oct))
        band_s = f"{band[0]:.0f}-{band[1]:.0f}"
        jl = f"{lo}↔{hi}"
        try:
            fA, mA, pA = api.get_fr(resolve(f"{lo}_{ver} (sw)"))
            fB, mB, pB = api.get_fr(resolve(f"{hi}_{ver} (sw)"))
        except KeyError as e:
            print(f"  {jl:<15}{fc:>6.0f}  — відсутній solo-замір: {e}")
            continue
        if pA is None or pB is None:
            print(f"  {jl:<15}{fc:>6.0f}  — потрібен sweep із фазою (RTA не має фази)")
            continue
        mB2, pB2 = _resample_complex(fB, mB, pB, fA)

        trusted, trust_lbl, js_call = None, "—(nopair)", ""
        if pair_name:
            try:
                fP, mP, _ = api.get_fr(resolve(pair_name))
                mP2 = interpolate_target(fP, mP, fA)     # pair magnitude (RTA-ok)
                tg = ja.phase_trust_gate(fA, mA, pA, mB2, pB2, mP2, band=band)
                js = ja.joint_summation_check(fA, mA, mB2, mP2, band=band)
                trusted = tg["phase_reliable"]
                trust_lbl = f"{tg['agreement']:.2f}" + ("✓" if trusted else " BLOCK")
                js_call = js["call"]
            except KeyError:
                trust_lbl = "pair?"

        if trusted is False:
            # Phase not trustworthy → do NOT compute/emit a delay. Magnitude only.
            print(f"  {jl:<15}{fc:>6.0f}{band_s:>12}{trust_lbl:>12}"
                  f"{'?':>5}{'—':>9}{'—':>7}{'—':>10}  "
                  f"phase unreliable → power-sum: {js_call}; flip polarity + remeasure")
            rows.append({"joint": jl, "fc": fc, "trust": trusted,
                         "polarity": None, "delay_ms": None, "verdict": "blocked"})
            continue

        al = ja.align_by_summation(fA, mA, pA, mB2, pB2, band=band)
        pol = "NORM" if al["polarity"] == 1 else "INV"
        apf = "—"
        if al["needs_allpass"]:
            ap = ja.allpass_for_residual_null(fA, mA, pA, mB2, pB2,
                                              apply_to="lo", band=band)
            if ap["improved"]:
                apf = f"{ap['f0_hz']:.0f}/{ap['q']}"
        verdict = ("apply (phase-verified)" if trusted is True
                   else "apply UNVERIFIED — confirm by summation")
        print(f"  {jl:<15}{fc:>6.0f}{band_s:>12}{trust_lbl:>12}"
              f"{pol:>5}{al['delay_ms']:>+9.2f}{al['residual_null_db']:>+7.1f}"
              f"{apf:>10}  {verdict}")
        rows.append({"joint": jl, "fc": fc, "trust": trusted,
                     "polarity": al["polarity"], "delay_ms": al["delay_ms"],
                     "residual_null_db": al["residual_null_db"],
                     "needs_allpass": al["needs_allpass"], "verdict": verdict})
        if lo in candidates or hi in candidates:
            # The hand-dialled all-pass against THIS joint's measured solos. Printed under the
            # row it belongs to and carrying that row's trust: a candidate on an UNVERIFIED
            # joint is an UNVERIFIED candidate, however good the number looks.
            touched.update(ch for ch in (lo, hi) if ch in candidates)
            cand = _check_candidate(fA, mA, pA, mB2, pB2, band, lo, hi, candidates)
            trust_word = ("phase-verified" if trusted is True
                          else "UNVERIFIED (nopair) — confirm by summation")
            where_now = f" @ {cand['now_null_hz']:.0f} Hz" if cand["now_null_hz"] else ""
            where_with = f" @ {cand['with_null_hz']:.0f} Hz" if cand["with_null_hz"] else ""
            print(f"  {'':<15}  ↳ {'; '.join(cand['applied'])}: null now "
                  f"{cand['now_null_db']:+.1f} dB{where_now} → with APF "
                  f"{cand['with_null_db']:+.1f} dB{where_with} (no other change) → "
                  f"with APF + best delay {cand['with_delay_null_db']:+.1f} dB "
                  f"({'NORM' if cand['with_polarity'] == 1 else 'INV'} "
                  f"{cand['with_delay_ms']:+.2f} ms)  "
                  f"{'HELPS' if cand['helps'] else 'does not help'} — {trust_word}")
            rows[-1]["candidate"] = cand
    for ch in candidates:
        if ch not in touched:
            print(f"  ↳ кандидат на {ch} ({_apf_label(*candidates[ch])}): жоден стик у списку "
                  f"не торкається {ch} — нема з чим перевірити.")

    print(f"\n  Порядок вирівнювання (метод §2b): midbass(ref) → sub → mid → tweeter, "
          f"тоді L↔R. Вводь через APF/Helix-phase, не raw-delay.")
    print(f"{SEP}\n")
    return rows


def run(mid, curves_dir, show_all=True):
    measurements = api.get_measurements()
    if str(mid) not in measurements:
        print(f"Вимір {mid} не знайдено.")
        return

    info = measurements[str(mid)]
    title = info["title"]
    mode = detect_mode(title)

    print(f"\n{'='*70}")
    print(f"  Вимір [{mid}]: {title}")
    print(f"  Режим: {'КРОСОВЕР (x0 → Generic/Extended)' if mode=='crossover' else 'EQ (Audiotec Fischer / Full EQ 30-band)'}")
    print(f"{'='*70}")

    # FR + Phase
    freqs, mag, phase = api.get_fr(mid)
    print_fr_analysis(freqs, mag, phase)

    # Group Delay
    try:
        gd_freqs, gd = api.get_group_delay(mid)
        print_gd_analysis(gd_freqs, gd)
    except Exception as e:
        print(f"\n  Group Delay: недоступно ({e})")

    # Impulse Response
    try:
        times, ir = api.get_impulse_response(mid)
        print_ir_analysis(times, ir)
    except Exception as e:
        print(f"\n  Impulse Response: недоступно ({e})")

    # Distortion
    dist = api.get_distortion(mid)
    print_distortion(dist)

    # Target curve
    target_file, target_data = find_target_curve(title, curves_dir)
    if target_data:
        t_freqs, t_mag = target_data
        print_deviation(freqs, mag, t_freqs, t_mag, target_file)

        suggestions = suggest_eq_cuts(freqs, mag, t_freqs, t_mag)
        if suggestions:
            print_header("Рекомендовані PEQ фільтри (тільки зрізання)")
            print(f"  {'Freq (Hz)':>10}  {'Gain (dB)':>10}  {'Q':>6}  {'Type':<6}")
            print(f"  {'-'*10}  {'-'*10}  {'-'*6}  {'-'*6}")
            for s in suggestions:
                print(f"  {s['freq']:>10.1f}  {s['gain']:>+10.1f}  {s['Q']:>6.1f}  {s['type']}")
    else:
        print(f"\n  Цільова крива: не знайдено для '{title}' в {curves_dir}")

    print(f"\n{SEP}\n")


def _selftest():
    """Offline check of the batch orchestration + rendering (no live REW).

    Monkeypatches the API + target lookup so the whole analyze_batch path
    (measurement filtering, per-band deviation, anchor/ripple, rendering)
    is exercised without a running REW server."""
    fake = {
        "1": {"title": "m-L_2 (rta)"},
        "2": {"title": "m-R_2 (rta)"},
        "3": {"title": "sw_1 (sw)"},          # excluded by pattern "_2 (rta)"
    }
    fr = {
        1: ([100, 500, 1000, 5000], [82, 84, 83, 80], None),
        2: ([100, 500, 1000, 5000], [80, 81, 80, 79], None),
    }
    tgt = ([100, 500, 1000, 5000], [80, 80, 80, 80])   # flat target

    orig_gm, orig_fr = api.get_measurements, api.get_fr
    import target_curves as tc
    orig_find = tc.find_target_curve
    globals()["find_target_curve"] = lambda title, cd: ("flat.txt", tgt)
    api.get_measurements = lambda: fake
    api.get_fr = lambda mid: fr[int(mid)]
    try:
        matches = analyze_batch("_2 (rta)", "/nonexistent", vs_targets=True)
        assert [t for _, t in matches] == ["m-L_2 (rta)", "m-R_2 (rta)"], matches
        # sw_1 (sw) must be filtered out by the pattern
        assert all("(sw)" not in t for _, t in matches), matches
        print("selftest[batch] OK — filtered to 2 rta measurements, "
              "one get_measurements + one get_fr each, matrix rendered.")
    finally:
        api.get_measurements, api.get_fr = orig_gm, orig_fr
        globals()["find_target_curve"] = orig_find

    # ── joints path: two solo sweeps where hi = lo inverted + delayed by tau.
    #    analyze_joints must recover polarity=-1 (INV) and delay≈-tau. ──────────
    hz = [20.0 * (10 ** (k * 3.0 / 511)) for k in range(512)]
    tau = 0.2  # ms
    magA = [0.0] * len(hz); phA = [0.0] * len(hz)
    magB = [0.0] * len(hz)
    phB = [180.0 - 360.0 * f * (tau / 1000.0) for f in hz]
    jmeas = {"10": {"title": "w-L_2 (sw)"}, "11": {"title": "m-L_2 (sw)"}}
    jfr = {10: (hz, magA, phA), 11: (hz, magB, phB)}
    orig_gm2, orig_fr2 = api.get_measurements, api.get_fr
    orig_find_id = api.find_measurement_id
    api.get_measurements = lambda: jmeas
    api.get_fr = lambda mid: jfr[int(mid)]
    api.find_measurement_id = lambda name, measurements=None, exact=True: \
        next(k for k, v in jmeas.items() if v["title"] == name)
    try:
        rows = analyze_joints([("w-L", "m-L", 400.0, None)], ver="2")
        assert rows and rows[0]["polarity"] == -1, rows          # INV recovered
        assert abs(rows[0]["delay_ms"] + tau) < 0.05, rows       # −tau recovered
        assert rows[0]["trust"] is None, rows                    # no pair → UNVERIFIED

        # BLOCK path (guardrail): a measured pair that does NOT reproduce the
        # near-cancelling complex model → phase_trust_gate unreliable → the
        # orchestrator must REFUSE to emit a delay (polarity None, blocked).
        jmeas["12"] = {"title": "Ws_2 (rta)"}
        jfr[12] = (hz, [0.0] * len(hz), None)                    # flat, wrong
        rows_b = analyze_joints([("w-L", "m-L", 400.0, "Ws_2 (rta)")], ver="2")
        assert rows_b[0]["trust"] is False, rows_b               # gate tripped
        assert rows_b[0]["delay_ms"] is None, rows_b             # NO computed delay
        assert rows_b[0]["verdict"] == "blocked", rows_b
        print(f"selftest[joints] OK — recovered pol=INV, delay={rows[0]['delay_ms']}ms "
              f"(≈−{tau}); nopair→UNVERIFIED; bad-pair→BLOCK (no delay emitted).")

        # ── a hand-dialled all-pass, VERIFIED not proposed (SCR-050 item 2). hi = lo rotated by
        #    an APF2 at 400 Hz: the joint nulls at 400 in phase. The candidate is the SAME APF2
        #    on lo — it un-rotates the pair, so the null closes with no delay change at all;
        #    the same candidate on hi doubles the rotation and does not help. ─────────────
        import cmath as _cm
        def _ap2_deg(f, f0, q):
            x = f / f0
            return math.degrees(-2.0 * math.atan2(x / q, 1.0 - x * x))
        phB_rot = [_ap2_deg(f, 400.0, 1.0) for f in hz]
        jfr[10] = (hz, magA, phA)
        jfr[11] = (hz, magA, phB_rot)
        del jmeas["12"]
        rows_c = analyze_joints([("w-L", "m-L", 400.0, None)], ver="2",
                                candidates={"w-L": ("APF2", 400.0, 1.0)})
        cand = rows_c[0]["candidate"]
        # −39.5 dB and not −inf: the grid's nearest point to 400 Hz is 402 Hz, where the
        # rotation is a shade under 180°. A real joint never cancels bit-for-bit either.
        assert cand["now_null_db"] < -30.0 and abs(cand["now_null_hz"] - 400.0) < 10.0, cand
        assert cand["with_null_db"] > -0.5, ("the same rotation on lo closes the null", cand)
        assert cand["helps"] is True and cand["applied"] == ["APF2 400 Hz Q 1 on w-L"], cand
        assert rows_c[0]["trust"] is None, "no pair → the candidate is UNVERIFIED like its row"
        rows_w = analyze_joints([("w-L", "m-L", 400.0, None)], ver="2",
                                candidates={"m-L": ("APF2", 400.0, 1.0)})
        wrong = rows_w[0]["candidate"]
        assert wrong["with_null_db"] < -30.0 and wrong["helps"] is False, wrong
        # ...and a first-order candidate on the same joint MOVES the null instead of closing it:
        # APF2 − APF1 leaves 0° far below f0, −90° at f0 (−3 dB there) and a full −180° far
        # above, so the band's worst point walks up to the top edge — the exact "does it fix the
        # joint or move the problem" that a candidate line exists to show.
        rows_1 = analyze_joints([("w-L", "m-L", 400.0, None)], ver="2",
                                candidates={"w-L": ("APF1", 400.0, None)})
        one = rows_1[0]["candidate"]
        assert -25.0 < one["with_null_db"] < -10.0 and one["with_null_hz"] > 600.0, one
        assert one["helps"] is True, "shallower than −39.5 counts as help, and the line says where"
        assert _parse_apf("m-L,apf2,300,0.71") == ("m-L", "APF2", 300.0, 0.71)
        assert _parse_apf("w-L, APF1, 80") == ("w-L", "APF1", 80.0, None)
        for bad in ("m-L,APF3,300,1", "m-L,APF2,300", "m-L,APF1,80,0.7", "m-L,APF2,-5,1"):
            try:
                _parse_apf(bad)
            except ValueError:
                pass
            else:
                raise AssertionError(f"_parse_apf accepted {bad!r}")
        print("selftest[joints:candidate] OK — hand-dialled APF2 on lo closes the 400 Hz null "
              f"({cand['now_null_db']:+.1f} → {cand['with_null_db']:+.1f} dB, no delay change), "
              "the same APF2 on hi does not help, an APF1 moves the null to the band's top, "
              "bad specs refused.")
    finally:
        api.get_measurements, api.get_fr = orig_gm2, orig_fr2
        api.find_measurement_id = orig_find_id

    # ── state-map: joints auto-derived from a snapshot's crossovers ───────────
    import tempfile
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import state as _st

    def _mkch(hp, lp):
        # No `slot` here: identity left the ledger in schema v3 (SCR-001) and `validate` refuses it.
        # This fixture had carried one since before that break, so the selftest died on its own
        # snapshot rather than on anything it meant to test.
        return {"hp": {"f": hp, "type": "BW", "slope": 12} if hp else "OFF",
                "lp": {"f": lp, "type": "BW", "slope": 12} if lp else "OFF",
                "gain_db": -6.0, "ta_ms": 5.0, "polarity": "NORM",
                "eq_ptr": {}, "status": "applied"}

    sstate = {"sample_rate": 96000, "target": "Jazzi",
              "roles": {"artist": None, "producer": None, "critic": None},
              "provenance": {}, "banked_ear_verdicts": [], "virtual_eq_ptr": None,
              "channels": {
                  "sub": _mkch(20, 45),
                  "w-L": _mkch(70, 270), "m-L": _mkch(270, 2800), "tw-L": _mkch(2800, None),
                  "w-R": _mkch(70, 270), "m-R": _mkch(270, 2800), "tw-R": _mkch(2800, None),
              }}
    tmp = tempfile.mkdtemp(prefix="autosound_jointmap_")
    _st.PresetHistory(tmp, "TESTP").snapshot(sstate, note="t")
    _st.Registry(tmp).set_active("TESTP")
    preset, ver_s, sp = _joints_from_state(tmp)          # active-slot path (no --preset)
    jset = {(lo, hi, fc) for lo, hi, fc, _ in sp}
    assert preset == "TESTP", preset
    for j in [("sub", "w-L", 45.0), ("w-L", "m-L", 270.0), ("m-L", "tw-L", 2800.0),
              ("sub", "w-R", 45.0), ("w-R", "m-R", 270.0), ("m-R", "tw-R", 2800.0)]:
        assert j in jset, (j, jset)
    assert len(sp) == 6, sp                              # no spurious cross-side joints
    print(f"selftest[state-map] OK — derived {len(sp)} joints from active slot "
          f"'{preset}' crossovers (sub↔w↔m↔tw per side).")


def main():
    parser = argparse.ArgumentParser(description="REW Analysis Tool")
    parser.add_argument("--curves-dir", default=DEFAULT_CURVES_DIR,
                        help="Шлях до папки з цільовими кривими")
    sub = parser.add_subparsers(dest="cmd")
    pb = sub.add_parser("analyze-batch",
                        help="Масовий аналіз усіх замірів за патерном → одна таблиця")
    pb.add_argument("pattern", help="Підрядок у назві заміру, напр. '_2 (rta)'")
    pb.add_argument("--curves-dir", default=DEFAULT_CURVES_DIR)
    pb.add_argument("--no-targets", action="store_true",
                    help="Лише середні рівні у смугах, без порівняння з ціллю")
    pj = sub.add_parser("analyze-joints",
                        help="Масовий аналіз усіх стиків → одна таблиця (полярність/затримка/APF)")
    pj.add_argument("--joint", action="append", default=[], metavar="lo,hi,fc[,pair]",
                    help="Стик: 'w-L,m-L,400' або з парою 'sw,w-L,60,SW+Ws_2 (rta)'. Повторюваний.")
    pj.add_argument("--from-state", action="store_true",
                    help="Автодеривація стиків із кросоверів активного слота (state/); "
                         "--joint тоді доповнює/уточнює (напр. чіпляє виміряну пару)")
    pj.add_argument("--preset", default=None,
                    help="Пресет для --from-state (дефолт = активний слот у registry)")
    pj.add_argument("--state-root",
                    default=os.environ.get("AUTOSOUND_STATE_ROOT", "state"),
                    help="Каталог зі снапшотами state (env AUTOSOUND_STATE_ROOT; дефолт 'state')")
    pj.add_argument("--state-ver", default=None,
                    help="Версія снапшота для --from-state (дефолт = HEAD)")
    pj.add_argument("--ver", default="2",
                    help="Версія solo-замірів (назва = <ch>_<ver> (sw)); дефолт 2")
    pj.add_argument("--band-oct", type=float, default=1.0,
                    help="Півширина смуги стику в октавах навколо fc (дефолт 1.0)")
    pj.add_argument("--apf", action="append", default=[], metavar="ch,APF1,f0 | ch,APF2,f0,Q",
                    help="Кандидат all-pass ПЕРЕВІРИТИ (не запропонувати): виставлений вручну "
                         "в TCC. Напр. --apf 'm-L,APF2,300,0.71'. Повторюваний, один на канал.")
    sub.add_parser("selftest", help="Офлайн-перевірка batch/joints режимів (без REW)")
    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return
    if args.cmd == "analyze-batch":
        try:
            analyze_batch(args.pattern, args.curves_dir,
                          vs_targets=not args.no_targets)
        except Exception as e:
            print(f"Помилка підключення до REW API: {e}")
            print("Переконайся що REW запущений з -api і API сервер увімкнений.")
            sys.exit(1)
        return
    if args.cmd == "analyze-joints":
        if not args.joint and not args.from_state:
            print("Вкажи --from-state (авто зі state/) або хоча б один "
                  "--joint 'lo,hi,fc[,pair]' (напр. --joint 'w-L,m-L,400').")
            sys.exit(1)
        try:
            specs = []
            if args.from_state:
                preset, ver_s, specs = _joints_from_state(
                    args.state_root, args.preset, args.state_ver)
                print(f"\n  Стики з кросоверів слота '{preset}' ({ver_s or 'HEAD'}): "
                      f"{len(specs)} шт.")
            # user --joint entries override/add by (lo,hi) — e.g. to attach a pair
            by_key = {(lo, hi): (lo, hi, fc, pair) for (lo, hi, fc, pair) in specs}
            for lo, hi, fc, pair in (_parse_joint(s) for s in args.joint):
                by_key[(lo, hi)] = (lo, hi, fc, pair)
            specs = list(by_key.values())
            if not specs:
                print("  Жодного стику не отримано (порожній state?).")
                sys.exit(1)
            candidates = {}
            for ch, kind, f0, q in (_parse_apf(a) for a in args.apf):
                if ch in candidates:
                    raise ValueError(f"--apf: канал {ch} названо двічі; один кандидат на канал")
                candidates[ch] = (kind, f0, q)
            analyze_joints(specs, ver=args.ver, band_oct=args.band_oct,
                           candidates=candidates)
        except ValueError as e:
            print(f"Помилка: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Помилка підключення до REW API / state: {e}")
            print("Переконайся що REW запущений з -api і API сервер увімкнений.")
            sys.exit(1)
        return

    try:
        measurements = api.get_measurements()
    except Exception as e:
        print(f"Помилка підключення до REW API: {e}")
        print("Переконайся що REW запущений з -api і API сервер увімкнений.")
        sys.exit(1)

    while True:
        print()
        list_measurements(measurements)
        print(f"\n  Введи номер виміру (або 'q' для виходу): ", end="")
        choice = input().strip()
        if choice.lower() == "q":
            break
        try:
            mid = int(choice)
        except ValueError:
            # A name instead of a number → resolve title→id FRESH (substring ok),
            # never a cached index (rew-api-quirks.md).
            try:
                mid = api.find_measurement_id(choice, exact=False)
            except KeyError as e:
                print(f"  {e}")
                continue
        try:
            run(mid, args.curves_dir)
        except Exception as e:
            print(f"  Помилка: {e}")


if __name__ == "__main__":
    main()
