import math


def analyze_fr(freqs, mag, phase=None, f_low=20, f_high=20000):
    """Return summary stats for FR in a given frequency range.

    Magnitude stats are always returned. When `phase` is provided (sweep
    measurements — RTA has none, pass ``None``), the in-band phase is collected
    and exposed on demand as ``mean_phase_deg`` so a caller that needs a rough
    band phase reference can read it without a second pass. It is a raw
    arithmetic mean and phase wraps at ±180°, so treat it as a coarse marker —
    for meaningful phase behaviour use :func:`find_phase_anomalies` (wrap-aware
    rate of change). When phase is absent the key is simply omitted (RTA-safe)."""
    zone = [(f, m) for f, m in zip(freqs, mag) if f_low <= f <= f_high]
    if not zone:
        return {}
    mags = [m for _, m in zone]
    mean_mag = sum(mags) / len(mags)
    min_mag = min(mags)
    max_mag = max(mags)
    min_f = zone[mags.index(min_mag)][0]
    max_f = zone[mags.index(max_mag)][0]
    stats = {
        "mean_dB": round(mean_mag, 2),
        "min_dB": round(min_mag, 2),
        "max_dB": round(max_mag, 2),
        "range_dB": round(max_mag - min_mag, 2),
        "min_freq": round(min_f, 1),
        "max_freq": round(max_f, 1),
    }
    if phase is not None:
        phases = [p for f, p in zip(freqs, phase) if f_low <= f <= f_high]
        if phases:
            stats["mean_phase_deg"] = round(sum(phases) / len(phases), 1)
    return stats


def find_phase_anomalies(freqs, phase, threshold_deg=30, f_low=20, f_high=20000):
    """Find zones with rapid phase change (> threshold per octave).

    Returns [] when phase is absent (RTA measurements have no phase)."""
    anomalies = []
    if phase is None:
        return anomalies
    prev_f, prev_p = None, None
    for f, p in zip(freqs, phase):
        if not (f_low <= f <= f_high):
            prev_f, prev_p = f, p
            continue
        if prev_f is not None and f > prev_f:
            octaves = math.log2(f / prev_f)
            delta = abs(p - prev_p)
            if delta > 180:
                delta = 360 - delta
            if octaves > 0 and (delta / octaves) > threshold_deg:
                anomalies.append((round(f, 1), round(delta / octaves, 1)))
        prev_f, prev_p = f, p
    return anomalies


def analyze_impulse(times, ir):
    """Find IR peak time and pre-ringing."""
    peak_val = max(ir, key=abs)
    peak_idx = ir.index(peak_val)
    peak_time_ms = times[peak_idx] * 1000
    peak_db = 20 * math.log10(abs(peak_val)) if abs(peak_val) > 0 else -120

    # pre-ringing: max before peak
    pre = ir[:peak_idx] if peak_idx > 0 else [0]
    pre_max = max(pre, key=abs)
    pre_db = 20 * math.log10(abs(pre_max)) if abs(pre_max) > 0 else -120
    pre_relative = pre_db - peak_db

    return {
        "peak_time_ms": round(peak_time_ms, 3),
        "peak_dB": round(peak_db, 1),
        "pre_ringing_dB": round(pre_relative, 1),
    }


def analyze_group_delay(freqs, gd, f_low=20, f_high=20000):
    """Find mean GD and zones with excessive delay variation."""
    zone = [(f, g) for f, g in zip(freqs, gd) if f_low <= f <= f_high]
    if not zone:
        return {}
    gd_vals = [g * 1000 for _, g in zone]  # convert to ms
    mean_gd = sum(gd_vals) / len(gd_vals)
    max_gd = max(gd_vals)
    min_gd = min(gd_vals)
    max_f = zone[gd_vals.index(max_gd)][0]
    return {
        "mean_ms": round(mean_gd, 2),
        "max_ms": round(max_gd, 2),
        "min_ms": round(min_gd, 2),
        "range_ms": round(max_gd - min_gd, 2),
        "peak_freq": round(max_f, 1),
    }


def compute_deviation(meas_freqs, meas_mag, target_freqs, target_mag):
    """Compute deviation (measured - target) at measurement frequencies."""
    from target_curves import interpolate_target
    target_at_meas = interpolate_target(target_freqs, target_mag, meas_freqs)
    deviation = [m - t for m, t in zip(meas_mag, target_at_meas)]
    return meas_freqs, deviation


# ── IR timing (see rew-api-quirks.md "Timing", diagnostic §10) ──────────────

def _leading_edge_index(ir, rel_threshold_db=-20.0):
    """Index of the DIRECT sound's leading edge — the FIRST sample crossing a
    fraction of the GLOBAL peak (default −20 dB). NOT the global max, which can
    sit on a late reflection (a fixed buffer index a few ms after onset)."""
    if not ir:
        return None
    peak = max(abs(v) for v in ir)
    if peak <= 0:
        return None
    thresh = peak * (10 ** (rel_threshold_db / 20.0))
    for i, v in enumerate(ir):
        if abs(v) >= thresh:
            return i
    return None


def first_arrival(times, ir, rel_threshold_db=-20.0):
    """Leading-edge first-arrival time of the direct sound (NOT the global peak).

    The global max-abs can land on a late REFLECTION → timing off it is wrong.
    This walks forward to the first sample within `rel_threshold_db` of the peak
    = the direct onset. Use it for absolute per-channel arrival WITH a shared
    loopback Time Offset, then sanity-check (cm-scale, stable on a repeat). The
    SUB/LF onset is the weak spot — read those from summation instead."""
    i = _leading_edge_index(ir, rel_threshold_db)
    if i is None:
        return None
    return {"arrival_time_ms": round(times[i] * 1000, 4), "index": i,
            "threshold_dB": rel_threshold_db}


def relative_delay_xcorr(ir_a, ir_b, sample_rate, max_lag_ms=5.0, window_ms=10.0):
    """Relative delay between two IRs (e.g. w-L vs w-R) by CROSS-CORRELATION.

    Robust to impulse SHAPE — unlike an onset/threshold pick, which is fragile on
    a dirty/ragged impulse (a door midbass) and can be off by multiples (real
    bug: 3.5 ms vs ~0.9 ms on the GUI cursor). Returns the lag that best aligns
    B onto A: **positive = B arrives LATER than A**. Both IRs are cropped to a
    SHARED window around the earlier leading edge (one time base → the relative
    delay is preserved) to bound the cost. Always cross-check vs the REW GUI
    cursor before stating the number."""
    n = min(len(ir_a), len(ir_b))
    if n == 0:
        return None
    a = list(ir_a[:n]); b = list(ir_b[:n])
    if window_ms:
        ia = _leading_edge_index(a) or 0
        ib = _leading_edge_index(b) or 0
        guard = int(0.001 * sample_rate)
        start = max(0, min(ia, ib) - guard)
        end = min(n, start + int(window_ms * 1e-3 * sample_rate))
        a = a[start:end]; b = b[start:end]
    m = min(len(a), len(b))
    a = a[:m]; b = b[:m]
    max_lag = max(1, min(int(round(max_lag_ms * 1e-3 * sample_rate)), m - 1))
    best_lag, best_corr = 0, None
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            s = sum(a[i] * b[i + lag] for i in range(0, m - lag))
        else:
            s = sum(a[i] * b[i + lag] for i in range(-lag, m))
        if best_corr is None or s > best_corr:
            best_corr, best_lag = s, lag
    return {"delay_ms": round(best_lag / sample_rate * 1000.0, 4),
            "lag_samples": best_lag, "max_lag_ms": max_lag_ms}


def _selftest():
    fs = 48000
    dt = 1.0 / fs
    n = 1024
    # An IR with a DIRECT arrival at 5.0 ms (0.6) and a LARGER reflection at
    # 8.0 ms (1.0). The global peak is the reflection — first_arrival must NOT
    # be fooled by it; analyze_impulse (global peak) reports the reflection.
    d_idx, r_idx = int(0.005 * fs), int(0.008 * fs)
    ir = [0.0] * n
    ir[d_idx] = 0.6
    ir[r_idx] = 1.0
    times = [i * dt for i in range(n)]
    fa = first_arrival(times, ir)
    assert fa["index"] == d_idx, f"first_arrival caught {fa['index']}, not direct {d_idx}"
    assert abs(fa["arrival_time_ms"] - 5.0) < 0.05, fa
    pk = analyze_impulse(times, ir)
    assert abs(pk["peak_time_ms"] - 8.0) < 0.05, f"global peak should be the reflection: {pk}"

    # Cross-correlation: b = a delayed by +12 samples → recover +12 / −12.
    base, shift = int(0.005 * fs), 12
    a = [0.0] * n
    for k, amp in [(0, 1.0), (1, 0.7), (2, 0.4), (3, -0.3), (4, 0.2)]:
        a[base + k] = amp
    b = [a[i - shift] if 0 <= i - shift < n else 0.0 for i in range(n)]
    res = relative_delay_xcorr(a, b, fs)
    assert res["lag_samples"] == shift, f"xcorr lag {res['lag_samples']} != {shift}"
    assert abs(res["delay_ms"] - shift / fs * 1000) < 1e-6, res
    res2 = relative_delay_xcorr(b, a, fs)
    assert res2["lag_samples"] == -shift, f"reverse xcorr {res2['lag_samples']} != {-shift}"

    # RTA path (phase=None): the magnitude-only branch that used to be
    # unexercised. analyze_fr must skip mean_phase_deg and find_phase_anomalies
    # must return [] — neither may crash on a phase-less (RTA) measurement.
    freqs = [50, 100, 200, 400, 800, 1600]
    mag = [80, 82, 84, 83, 81, 79]
    phase = [0, -20, -50, -90, -140, -200]
    s_rta = analyze_fr(freqs, mag, None, 100, 1000)
    assert "mean_phase_deg" not in s_rta and s_rta["mean_dB"] > 0, s_rta
    assert find_phase_anomalies(freqs, None) == [], "phase=None must yield no anomalies"
    s_sw = analyze_fr(freqs, mag, phase, 100, 1000)
    assert "mean_phase_deg" in s_sw, "sweep: phase present → mean_phase_deg exposed"
    assert find_phase_anomalies(freqs, phase), "sweep: real phase should flag anomalies"

    print(f"selftest OK — first_arrival {fa['arrival_time_ms']} ms avoids the reflection "
          f"(global peak {pk['peak_time_ms']} ms); xcorr {res['delay_ms']} ms (+) / "
          f"{res2['delay_ms']} ms (−); FR phase-present/absent branches OK")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        print("usage: python analysis.py --selftest")
