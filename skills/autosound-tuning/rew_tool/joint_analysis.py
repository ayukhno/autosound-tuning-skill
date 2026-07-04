import cmath
import math
import statistics


def _in_band(hz, band):
    lo, hi = (band or (hz[0], hz[-1]))
    return [k for k, f in enumerate(hz) if lo <= f <= hi]


def incoherent_sum_db(*traces_db):
    if not traces_db:
        return []
    length = min(len(t) for t in traces_db)
    out = []
    for k in range(length):
        p = sum(10 ** (t[k] / 10.0) for t in traces_db)
        out.append(10 * math.log10(p) if p > 0 else -120.0)
    return out


def joint_summation_check(hz, driver_lo_db, driver_hi_db, measured_pair_db,
                          min_gap_db=2.0, band=None):
    keep = _in_band(hz, band)
    reference = incoherent_sum_db(driver_lo_db, driver_hi_db)
    bands = []
    for k in keep:
        if k >= len(reference):
            break
        gap = measured_pair_db[k] - reference[k]
        state = "cancelling" if gap <= -min_gap_db else \
                "reinforcing" if gap >= min_gap_db else "neutral"
        bands.append({"hz": round(hz[k], 1), "gap_db": round(gap, 2),
                      "state": state})
    cancelling = [b for b in bands if b["state"] == "cancelling"]
    reinforcing = [b for b in bands if b["state"] == "reinforcing"]
    deepest = min(bands, key=lambda b: b["gap_db"]) if bands else None
    call = ("phase cancellation -> polarity/delay/APF, do NOT boost"
            if cancelling else
            "in-phase overlap hump -> level/overlap, not a lone notch"
            if reinforcing else "summation benign across band")
    return {"bands": bands, "cancelling_bins": len(cancelling),
            "reinforcing_bins": len(reinforcing), "deepest_null": deepest,
            "call": call}


def _complex_trace(mag_db, phase_deg):
    return [10 ** (mag_db[k] / 20.0) * cmath.exp(1j * math.radians(phase_deg[k]))
            for k in range(min(len(mag_db), len(phase_deg)))]


def phase_trust_gate(hz, lo_mag_db, lo_phase_deg, hi_mag_db, hi_phase_deg,
                     measured_pair_db, band=None, max_rms_db=2.0):
    keep = _in_band(hz, band)
    A = _complex_trace(lo_mag_db, lo_phase_deg)
    B = _complex_trace(hi_mag_db, hi_phase_deg)
    model = []
    for k in keep:
        amp = abs(A[k] + B[k])
        model.append(20 * math.log10(amp) if amp > 0 else -120.0)
    seen = [measured_pair_db[k] for k in keep]
    if not model:
        return {"agreement": 0.0, "mismatch_rms_db": None,
                "phase_reliable": False, "n_bins": 0}
    gaps = [s - m for s, m in zip(seen, model)]
    bias = statistics.median(gaps)
    gaps = [g - bias for g in gaps]
    err = math.sqrt(sum(g * g for g in gaps) / len(gaps))
    agreement = max(0.0, min(1.0, 1.0 - err / (2.0 * max_rms_db)))
    return {"agreement": round(agreement, 3), "mismatch_rms_db": round(err, 3),
            "phase_reliable": err <= max_rms_db, "level_bias_db": round(bias, 2),
            "n_bins": len(keep)}


def _critical_bandwidth_hz(fc):
    return 24.7 * (4.37 * fc / 1000.0 + 1.0)


def perceptual_smooth(hz, y, span=1.0):
    length = min(len(hz), len(y))
    out = []
    for k in range(length):
        reach = 0.5 * span * _critical_bandwidth_hz(hz[k])
        lo, hi = hz[k] - reach, hz[k] + reach
        win = [y[j] for j in range(length) if lo <= hz[j] <= hi]
        out.append(sum(win) / len(win) if win else y[k])
    return out


def midband_level_anchor(hz, measured_db, target_db, band=(300.0, 3000.0)):
    keep = _in_band(hz, band)
    diffs = [measured_db[k] - target_db[k] for k in keep]
    return round(statistics.median(diffs), 3) if diffs else 0.0


def shape_deviation(hz, measured_db, target_db, band=(300.0, 3000.0)):
    anchor = midband_level_anchor(hz, measured_db, target_db, band)
    return hz, [(m - t) - anchor for m, t in zip(measured_db, target_db)]


def _leading_edge(ir, rel_db=-20.0):
    peak = max((abs(v) for v in ir), default=0.0)
    if peak <= 0:
        return None
    thr = peak * 10 ** (rel_db / 20.0)
    for i, v in enumerate(ir):
        if abs(v) >= thr:
            return i
    return None


def impulse_polarity(ir, rel_db=-20.0):
    i = _leading_edge(ir, rel_db)
    if i is None:
        return {"polarity": 0, "onset_amp": 0.0, "onset_index": None}
    return {"polarity": 1 if ir[i] >= 0 else -1,
            "onset_amp": ir[i], "onset_index": i}


def _pre_echo_db(ir, fs):
    n = len(ir)
    absir = [abs(v) for v in ir]
    peak = max(absir)
    if peak <= 0:
        return None
    sp = fs / 1000.0
    noise = sorted(absir)[int(0.10 * n)]
    onset = next((i for i, v in enumerate(absir)
                  if v >= max(0.12 * peak, 6 * noise)), 0)
    a = max(0, int(onset - 12 * sp))
    b = min(n, int(onset - 0.7 * sp))
    if b <= a:
        return -120.0
    pre = math.sqrt(sum(absir[i] ** 2 for i in range(a, b)) / (b - a))
    return 20 * math.log10(pre / peak) if pre > 0 else -120.0


def flag_remeasure_candidates(captures, margin_db=15.0):
    scored = []
    for c in captures:
        scored.append((c["name"], c["driver"], _pre_echo_db(c["ir"], c["fs"])))
    best = {}
    for _, drv, pe in scored:
        if pe is not None:
            best[drv] = min(best.get(drv, pe), pe)
    out = []
    for name, drv, pe in scored:
        delta = (pe - best[drv]) if pe is not None else 0.0
        out.append({"name": name, "driver": drv, "pre_echo_db": round(pe, 1),
                    "delta_db": round(delta, 1), "remeasure": delta >= margin_db})
    return out


def _best_lag(a, b, fs, max_lag_ms=8.0):
    n = min(len(a), len(b))
    la = _leading_edge(a) or 0
    lb = _leading_edge(b) or 0
    guard = int(0.001 * fs)
    start = max(0, min(la, lb) - guard)
    win = int(0.030 * fs)
    a = a[start:start + win]
    b = b[start:start + win]
    m = min(len(a), len(b))
    a = a[:m]; b = b[:m]
    max_lag = max(1, min(int(max_lag_ms * 1e-3 * fs), m - 1))
    best_lag, best = 0, None
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            s = sum(a[i] * b[i + lag] for i in range(m - lag))
        else:
            s = sum(a[i] * b[i + lag] for i in range(-lag, m))
        if best is None or s > best:
            best, best_lag = s, lag
    return best_lag


def timing_drift_audit(ir_a, start_a, ir_b, start_b, fs, real_change_ms=0.05):
    d_start_ms = (start_b - start_a) * 1000.0
    xcorr_ms = _best_lag(ir_a, ir_b, fs) / fs * 1000.0
    real = abs(xcorr_ms) >= real_change_ms
    verdict = ("real timing change -> apply as delay"
               if real else
               "reference drift (label only) -> ignore Δstart, compare by xcorr"
               if abs(d_start_ms) >= real_change_ms else
               "stable")
    return {"delta_start_ms": round(d_start_ms, 4),
            "waveform_shift_ms": round(xcorr_ms, 4),
            "real_change": real, "verdict": verdict}


def _apply_delay(trace, hz, delay_ms):
    tau = delay_ms / 1000.0
    return [trace[k] * cmath.exp(-1j * 2 * math.pi * hz[k] * tau)
            for k in range(len(hz))]


def align_by_summation(hz, lo_mag_db, lo_phase_deg, hi_mag_db, hi_phase_deg,
                       band=None, max_delay_ms=1.5, step_ms=0.01,
                       null_floor_db=-6.0):
    keep = _in_band(hz, band)
    A = _complex_trace(lo_mag_db, lo_phase_deg)
    B = _complex_trace(hi_mag_db, hi_phase_deg)
    f = [hz[k] for k in keep]
    a = [A[k] for k in keep]
    b = [B[k] for k in keep]
    steps = int(2 * max_delay_ms / step_ms) + 1
    best = None
    for pol in (1, -1):
        for s in range(steps):
            tau = (-max_delay_ms + s * step_ms) / 1000.0
            energy = 0.0
            for k in range(len(f)):
                sk = a[k] + pol * b[k] * cmath.exp(-1j * 2 * math.pi * f[k] * tau)
                energy += abs(sk) ** 2
            if best is None or energy > best[0]:
                best = (energy, pol, tau)
    _, pol, tau = best
    worst = 0.0
    for k in range(len(f)):
        sk = a[k] + pol * b[k] * cmath.exp(-1j * 2 * math.pi * f[k] * tau)
        ceil = abs(a[k]) + abs(b[k])
        if ceil > 0:
            r = 20 * math.log10(abs(sk) / ceil)
            worst = min(worst, r)
    return {"polarity": pol, "delay_ms": round(tau * 1000.0, 4),
            "residual_null_db": round(worst, 2),
            "needs_allpass": worst < null_floor_db}


def _ap2(f, f0, q):
    x = f / f0
    phase = -2.0 * math.atan2(x / q, 1.0 - x * x)
    return cmath.exp(1j * phase)


def allpass_for_residual_null(hz, lo_mag_db, lo_phase_deg,
                              hi_mag_db, hi_phase_deg, apply_to="lo",
                              band=None, q_set=(0.5, 0.7, 1.0, 1.5, 2.0),
                              n_f0=48):
    keep = _in_band(hz, band)
    A = [_complex_trace(lo_mag_db, lo_phase_deg)[k] for k in keep]
    B = [_complex_trace(hi_mag_db, hi_phase_deg)[k] for k in keep]
    f = [hz[k] for k in keep]
    base = sum(abs(A[k] + B[k]) ** 2 for k in range(len(f)))
    flo, fhi = f[0], f[-1]
    grid = [flo * (fhi / flo) ** (i / (n_f0 - 1)) for i in range(n_f0)]
    best = (base, None, None)
    for f0 in grid:
        for q in q_set:
            energy = 0.0
            for k in range(len(f)):
                ap = _ap2(f[k], f0, q)
                if apply_to == "lo":
                    sk = A[k] * ap + B[k]
                else:
                    sk = A[k] + B[k] * ap
                energy += abs(sk) ** 2
            if energy > best[0]:
                best = (energy, f0, q)
    gain = 10 * math.log10(best[0] / base) if base > 0 else 0.0
    return {"f0_hz": round(best[1], 1) if best[1] else None,
            "q": best[2], "apply_to": apply_to,
            "sum_gain_db": round(gain, 2), "improved": best[1] is not None}


def _biquad_mag_db(hz, b0, b1, b2, a0, a1, a2, fs):
    out = []
    for f in hz:
        w = 2 * math.pi * f / fs
        z1 = cmath.exp(-1j * w)
        z2 = z1 * z1
        h = (b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2)
        out.append(20 * math.log10(abs(h)) if abs(h) > 0 else -120.0)
    return out


def _shelf_coeffs(kind, f0, gain_db, fs, slope=1.0):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * f0 / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / 2.0 * math.sqrt(max((A + 1 / A) * (1 / slope - 1) + 2, 0.0))
    tsa = 2 * math.sqrt(A) * alpha
    if kind == "low":
        b0 = A * ((A + 1) - (A - 1) * cw + tsa)
        b1 = 2 * A * ((A - 1) - (A + 1) * cw)
        b2 = A * ((A + 1) - (A - 1) * cw - tsa)
        a0 = (A + 1) + (A - 1) * cw + tsa
        a1 = -2 * ((A - 1) + (A + 1) * cw)
        a2 = (A + 1) + (A - 1) * cw - tsa
    else:
        b0 = A * ((A + 1) + (A - 1) * cw + tsa)
        b1 = -2 * A * ((A - 1) + (A + 1) * cw)
        b2 = A * ((A + 1) + (A - 1) * cw - tsa)
        a0 = (A + 1) - (A - 1) * cw + tsa
        a1 = 2 * ((A - 1) - (A + 1) * cw)
        a2 = (A + 1) - (A - 1) * cw - tsa
    return b0, b1, b2, a0, a1, a2


def _peak_coeffs(f0, gain_db, q, fs):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * f0 / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * q)
    return (1 + alpha * A, -2 * cw, 1 - alpha * A,
            1 + alpha / A, -2 * cw, 1 - alpha / A)


def shelf_vs_bell(hz, target_db, kind, band=None, fs=48000.0,
                  tol_db=0.75, n_f0=32):
    keep = _in_band(hz, band)
    f = [hz[k] for k in keep]
    t = [target_db[k] for k in keep]
    t0 = statistics.median(t)
    t = [v - t0 for v in t]
    flo, fhi = f[0], f[-1]
    grid = [flo * (fhi / flo) ** (i / (n_f0 - 1)) for i in range(n_f0)]
    gains = [g * 0.5 for g in range(-24, 25)]
    best = None
    for f0 in grid:
        for g in gains:
            if g == 0:
                continue
            coeffs = _shelf_coeffs(kind, f0, g, fs)
            model = _biquad_mag_db(f, *coeffs, fs)
            m0 = statistics.median(model)
            resid = math.sqrt(sum((model[k] - m0 - t[k]) ** 2
                                  for k in range(len(f))) / len(f))
            if best is None or resid < best[0]:
                best = (resid, f0, g)
    resid, f0, g = best
    return {"decision": "shelf" if resid <= tol_db else "bell",
            "residual_db": round(resid, 3),
            "shelf_f0_hz": round(f0, 1), "shelf_gain_db": round(g, 2)}


def _selftest():
    hz = [20.0 * (10 ** (k * 3.0 / 255)) for k in range(256)]

    lo = [-6.0] * len(hz); hi = [-6.0] * len(hz)
    assert all(abs(v + 2.99) < 0.02 for v in incoherent_sum_db(lo, hi))
    pair = list(incoherent_sum_db(lo, hi))
    for k, f in enumerate(hz):
        if 250 <= f <= 350:
            pair[k] -= 8.0
        elif 2500 <= f <= 3500:
            pair[k] += 3.0
    v = joint_summation_check(hz, lo, hi, pair)
    assert v["cancelling_bins"] and v["reinforcing_bins"]
    assert 250 <= v["deepest_null"]["hz"] <= 350 and "do NOT boost" in v["call"]

    coh = [0.0] * len(hz)
    ok = phase_trust_gate(hz, lo, [0.0] * len(hz), hi, [0.0] * len(hz), coh,
                          band=(100, 10000))
    assert ok["phase_reliable"] and ok["agreement"] > 0.9
    noisy = [coh[k] + (6.0 if k % 2 else -6.0) for k in range(len(hz))]
    bad = phase_trust_gate(hz, lo, [0.0] * len(hz), hi, [0.0] * len(hz), noisy,
                           band=(100, 10000))
    assert not bad["phase_reliable"]

    assert all(abs(x) < 1e-9 for x in perceptual_smooth(hz, [0.0] * len(hz)))
    spike = [0.0] * len(hz); spike[128] = 12.0
    assert perceptual_smooth(hz, spike)[128] < 12.0
    assert _critical_bandwidth_hz(100) / 100 > _critical_bandwidth_hz(10000) / 10000

    tgt = [0.0] * len(hz); meas = [4.0] * len(hz); meas[5] = 40.0
    assert abs(midband_level_anchor(hz, meas, tgt, (300, 3000)) - 4.0) < 1e-6

    fs = 96000
    n = 4096; base = 2000
    posir = [0.0] * n
    for k, amp in [(0, 1.0), (1, 0.6), (2, -0.3)]:
        posir[base + k] = amp
    assert impulse_polarity(posir)["polarity"] == 1
    negir = [-v for v in posir]
    assert impulse_polarity(negir)["polarity"] == -1

    clean = [0.0] * n
    for k, amp in [(0, 1.0), (1, 0.5), (2, -0.2)]:
        clean[base + k] = amp
    dirty = list(clean)
    for k in range(base - 400, base - 100):
        dirty[k] = 0.08
    caps = [{"name": "wL_a", "driver": "w-L", "ir": clean, "fs": fs},
            {"name": "wL_b", "driver": "w-L", "ir": dirty, "fs": fs},
            {"name": "wR_a", "driver": "w-R", "ir": clean, "fs": fs}]
    flags = {c["name"]: c["remeasure"] for c in flag_remeasure_candidates(caps)}
    assert flags["wL_b"] and not flags["wL_a"] and not flags["wR_a"]

    dt = 1.0 / fs
    drift = timing_drift_audit(clean, -1.0, clean, -1.0 + 0.00013, fs)
    assert not drift["real_change"] and "drift" in drift["verdict"]
    shifted = [0.0] * n
    for i in range(n):
        j = i - 10
        shifted[i] = clean[j] if 0 <= j < n else 0.0
    moved = timing_drift_audit(clean, -1.0, shifted, -1.0, fs)
    assert moved["real_change"]

    magA = [0.0] * len(hz); phA = [0.0] * len(hz)
    tau0 = 0.2
    magB = [0.0] * len(hz)
    phB = [180.0 - 360.0 * f * (tau0 / 1000.0) for f in hz]
    al = align_by_summation(hz, magA, phA, magB, phB, band=(200, 8000))
    assert al["polarity"] == -1 and abs(al["delay_ms"] + tau0) < 0.05
    assert not al["needs_allpass"]

    phN = [math.degrees(cmath.phase(_ap2(f, 2000.0, 1.0))) for f in hz]
    magN = [0.0] * len(hz)
    ap = allpass_for_residual_null(hz, magA, phA, magN, phN, apply_to="lo",
                                   band=(500, 8000))
    assert ap["improved"] and ap["sum_gain_db"] > 0

    shelf_t = _biquad_mag_db(hz, *_shelf_coeffs("low", 200, -4.0, fs), fs)
    sd = shelf_vs_bell(hz, shelf_t, "low", band=(40, 4000), fs=fs)
    assert sd["decision"] == "shelf"
    bell_t = _biquad_mag_db(hz, *_peak_coeffs(1000, 5.0, 2.0, fs), fs)
    bd = shelf_vs_bell(hz, bell_t, "low", band=(200, 6000), fs=fs)
    assert bd["decision"] == "bell"

    print("selftest OK -- joint/trust/smooth/anchor + impulse_polarity(+/-) + "
          f"remeasure-gate + drift-audit(drift vs real) + align(pol={al['polarity']},"
          f"{al['delay_ms']}ms) + allpass(+{ap['sum_gain_db']}dB @{ap['f0_hz']}Hz) + "
          f"shelf_vs_bell(shelf={sd['residual_db']} / bell={bd['residual_db']})")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        print("usage: python joint_analysis.py --selftest")
