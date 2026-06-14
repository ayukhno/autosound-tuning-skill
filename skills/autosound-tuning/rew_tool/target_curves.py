import os
import glob

# Map channel keywords in measurement name → target curve filename fragment
CHANNEL_MAP = {
    "sw":  "sw",
    "w-":  "w_60",
    "w_":  "w_60",
    " w":  "w_60",
    "m-":  "m_250",
    "m_":  "m_250",
    " m":  "m_250",
    "tw":  "tw",
}


def load_target_curve(filepath):
    freqs, mags = [], []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    freqs.append(float(parts[0]))
                    mags.append(float(parts[1]))
                except ValueError:
                    continue
    return freqs, mags


def find_target_curve(measurement_title, curves_dir, use_sum=False):
    title_lower = measurement_title.lower()

    channel = None
    for keyword, ch in CHANNEL_MAP.items():
        if keyword in title_lower:
            channel = ch
            break

    if channel is None:
        return None, None

    suffix = "_SUM" if use_sum else ""
    pattern = os.path.join(curves_dir, f"*_{channel}*{suffix}_REW.txt")
    matches = glob.glob(pattern)
    if not matches:
        return None, None

    filepath = matches[0]
    freqs, mags = load_target_curve(filepath)
    return filepath, (freqs, mags)


def interpolate_target(target_freqs, target_mags, query_freqs):
    """Linear interpolation of target curve at query frequencies."""
    result = []
    for f in query_freqs:
        if f <= target_freqs[0]:
            result.append(target_mags[0])
            continue
        if f >= target_freqs[-1]:
            result.append(target_mags[-1])
            continue
        for i in range(len(target_freqs) - 1):
            if target_freqs[i] <= f <= target_freqs[i + 1]:
                t = (f - target_freqs[i]) / (target_freqs[i + 1] - target_freqs[i])
                result.append(target_mags[i] + t * (target_mags[i + 1] - target_mags[i]))
                break
    return result
