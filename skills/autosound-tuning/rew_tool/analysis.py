import math


def analyze_fr(freqs, mag, phase, f_low=20, f_high=20000):
    """Return summary stats for FR in given frequency range."""
    zone = [(f, m, p) for f, m, p in zip(freqs, mag, phase) if f_low <= f <= f_high]
    if not zone:
        return {}
    mags = [m for _, m, _ in zone]
    phases = [p for _, _, p in zone]
    mean_mag = sum(mags) / len(mags)
    min_mag = min(mags)
    max_mag = max(mags)
    min_f = zone[mags.index(min_mag)][0]
    max_f = zone[mags.index(max_mag)][0]
    return {
        "mean_dB": round(mean_mag, 2),
        "min_dB": round(min_mag, 2),
        "max_dB": round(max_mag, 2),
        "range_dB": round(max_mag - min_mag, 2),
        "min_freq": round(min_f, 1),
        "max_freq": round(max_f, 1),
    }


def find_phase_anomalies(freqs, phase, threshold_deg=30, f_low=20, f_high=20000):
    """Find zones with rapid phase change (> threshold per octave)."""
    anomalies = []
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
