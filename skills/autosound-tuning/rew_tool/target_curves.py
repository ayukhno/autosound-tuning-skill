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


#: Keys longest-first. Two bugs lived in the ordering and the scope of the match, and neither
#: showed up in any output -- a wrong target curve reads as a driver that needs 8 dB of EQ.
_KEYS = sorted({k.strip() for k in CHANNEL_MAP}, key=len, reverse=True)
_BY_KEY = {k.strip(): v for k, v in CHANNEL_MAP.items()}


def channel_of(measurement_title):
    """The curve fragment a REW title asks for, or None.

    Matched against the CHANNEL TOKEN, not the whole title, and longest key first:

      * REW titles every sweep `<ch>_<ver> (sw)`. A substring search over the whole title found
        `sw` inside `(sw)`, so EVERY swept measurement -- woofer, mid, tweeter -- was handed the
        SUBWOOFER's target curve. Only RTA captures escaped, because they say `(rta)`.
      * `tw` contains `w`, and `w-` came first in the map, so a tweeter matched the woofer's key.

    Found 2026-09-07 while writing this module's first selftest (HUB-037), not by anything the
    tool printed."""
    token = measurement_title.strip().split("(")[0].strip().lower()
    for key in _KEYS:
        if token.startswith(key):
            return _BY_KEY[key]
    # Fall back to a contained match, still inside the token rather than the whole title, so a
    # name like `front-m-L` keeps working without `(sw)` being able to win.
    for key in _KEYS:
        if key in token:
            return _BY_KEY[key]
    return None


def find_target_curve(measurement_title, curves_dir, use_sum=False):
    channel = channel_of(measurement_title)
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


def _selftest():
    """The mapping and the interpolation, offline. First selftest this module ever had (HUB-037).

    It was written to close a coverage gap and found two live bugs on the first run -- both in
    `channel_of`, both invisible in the tool's output, and both asserted below as the cases that
    used to be wrong."""
    import tempfile

    # ── channel mapping: the two bugs this selftest was born finding ─────────────────────────
    # RED before the fix: every one of these returned "sw", because REW titles sweeps `(sw)`.
    assert channel_of("m-L_2 (sw)") == "m_250", channel_of("m-L_2 (sw)")
    assert channel_of("w-L_2 (sw)") == "w_60", channel_of("w-L_2 (sw)")
    assert channel_of("tw-L_2 (sw)") == "tw", channel_of("tw-L_2 (sw)")
    # RED before the fix: "w-" came first in the map and `tw` contains `w`.
    assert channel_of("tw-R_2 (rta)") == "tw", channel_of("tw-R_2 (rta)")
    # Still right, and the reason the bug survived: the subwoofer's own title happens to agree.
    assert channel_of("sw_1 (sw)") == "sw", channel_of("sw_1 (sw)")
    # A name the map does not cover stays None -- silence, not a guess at the nearest curve.
    assert channel_of("xyz_1 (sw)") is None, channel_of("xyz_1 (sw)")
    # The contained-match fallback, still scoped to the channel token.
    assert channel_of("front-m-L_2 (sw)") == "m_250", channel_of("front-m-L_2 (sw)")

    # ── the file reader: comments, blanks and junk rows are skipped, not crashed on ──────────
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "house_m_250_REW.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# a comment\n\n20 6.0\n1000 0.0\nnot a row\n20000 -3.0 extra-column\n")
        freqs, mags = load_target_curve(path)
        assert freqs == [20.0, 1000.0, 20000.0], freqs
        assert mags == [6.0, 0.0, -3.0], mags

        found, data = find_target_curve("m-L_2 (sw)", d)
        assert found == path and data == (freqs, mags), (found, data)
        # The same title before the fix picked the SUBWOOFER's file. Both exist here, so this
        # asserts the choice rather than the absence of an alternative.
        with open(os.path.join(d, "house_sw_REW.txt"), "w", encoding="utf-8") as fh:
            fh.write("20 10.0\n80 0.0\n")
        again, _ = find_target_curve("m-L_2 (sw)", d)
        assert again == path, again
        assert find_target_curve("xyz_1 (sw)", d) == (None, None)

    # ── interpolation: inside, on the knots, and clamped outside ─────────────────────────────
    tf, tm = [100.0, 200.0, 400.0], [0.0, 10.0, 0.0]
    got = interpolate_target(tf, tm, [50.0, 100.0, 150.0, 200.0, 300.0, 400.0, 800.0])
    assert got == [0.0, 0.0, 5.0, 10.0, 5.0, 0.0, 0.0], got

    print("selftest OK — channel_of maps the TOKEN not the title (a sweep is no longer read as "
          "'sw' and a tweeter no longer as a woofer); the reader skips comments, blanks and junk "
          "rows; interpolation is linear inside and clamped outside.")


if __name__ == "__main__":
    import sys
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        _selftest()
    else:
        print(__doc__ or "target_curves.py — run `target_curves.py selftest`")
