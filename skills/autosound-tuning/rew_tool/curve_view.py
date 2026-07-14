"""Multi-scale curve viewer — one disciplined way to look at a response
from three distances (the user's "zoom" insight, 2026-07-14):

  1. BAND   — always analyze inside an explicit from-to window;
  2. MACRO  — the tonal trend (default 1/3 oct — ~critical-band, what the
              ear hears as "balance"); broad moves belong to VOICING
              (virtual layer / shelves, diagnostic §6);
  3. FINE   — the residual (fine smoothing MINUS macro trend) exposes
              narrow defects that coarse views average away (§21 lesson:
              1/12 binning hid a +9 dB peak at 520 Hz).

Every detected feature is ROUTED to the doctrine that owns it — the tool
answers "what am I ALLOWED to do about this?", not just "what is there":

  width > 2/3 oct            -> voicing territory (broad EQ / shelf, §6);
  1/6..2/3 oct, peak         -> point-EQ candidate (cut; §2 "peak or null");
  1/6..2/3 oct, dip          -> NULL-SUSPECT: check before any boost
                                (eq_gate / excess phase / mic shift, §2/§13);
  width < 1/6 oct            -> VERIFY FIRST: must survive MMM / a mic
                                shift before it exists at all (§13; the
                                +8.7 dB @ 2950 spike that evaporated).

Works on any dB curve: a response, an L−R difference, a new-vs-old delta.
Pure numpy. Skill home: rew_tool/curve_view.py. Selftest: --selftest.
"""
import numpy as np

PPO = 96  # analysis grid density (points per octave)


def _gauss_smooth(y, sigma_pts):
    n = int(max(3, round(sigma_pts * 8)) | 1)
    k = np.exp(-0.5 * ((np.arange(n) - n // 2) / sigma_pts) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(y, n // 2, mode="edge"), k, mode="valid")


def _smooth_frac(y, frac_oct):
    """Gaussian smoothing with FWHM = 1/frac_oct octave on the PPO grid."""
    return _gauss_smooth(y, PPO / frac_oct / 2.355)


def multiscale(freqs, mag_db, band, macro_frac=3, fine_frac=24):
    """Resample to a log grid inside band and split into scales.

    Returns dict: grid, raw (grid-resampled), macro (1/macro_frac oct trend),
    fine (1/fine_frac oct), residual (fine - macro).
    macro_frac=3 ~ critical band (tonal balance); fine_frac=24 or 48 for
    narrow-defect hunting (per §21 use >= 24 to localize targets)."""
    lo, hi = band
    grid = np.geomspace(lo, hi, max(int(np.log2(hi / lo) * PPO), 16))
    raw = np.interp(grid, freqs, mag_db)
    macro = _smooth_frac(raw, macro_frac)
    fine = _smooth_frac(raw, fine_frac)
    return {"grid": grid, "raw": raw, "macro": macro, "fine": fine,
            "residual": fine - macro}


def find_features(view, min_prominence_db=2.0, source="sweep"):
    """Contiguous |residual| >= prominence runs -> features with doctrine
    routing. Each: {f_lo, f_hi, f_center, width_oct, extremum_db, kind,
    route}. kind: 'peak'|'dip'. source: 'sweep' (single-point — narrow
    features need MMM/mic-shift arbitration first, §13) or 'mmm' (already
    spatially averaged — narrow features are real in space, route by kind)."""
    g, r = view["grid"], view["residual"]
    hot = np.abs(r) >= min_prominence_db
    out, i = [], 0
    while i < len(hot):
        if not hot[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(hot) and hot[j + 1]:
            j += 1
        seg = r[i:j + 1]
        k = i + int(np.argmax(np.abs(seg)))
        # width = FWHM around the extremum (threshold-crossing width is
        # fragile: the macro trend absorbs part of a feature's depth, so a
        # medium feature can show a sliver above threshold)
        half = np.abs(r[k]) / 2.0
        wl = k
        while wl > 0 and np.abs(r[wl - 1]) >= half and np.sign(r[wl - 1]) == np.sign(r[k]):
            wl -= 1
        wr = k
        while wr < len(r) - 1 and np.abs(r[wr + 1]) >= half \
                and np.sign(r[wr + 1]) == np.sign(r[k]):
            wr += 1
        width = float(np.log2(g[wr] / g[wl]))
        kind = "peak" if r[k] > 0 else "dip"
        if width > 2 / 3:
            route = ("voicing: broad move -> virtual layer / shelf "
                     "(diagnostic §6), not point EQ")
        elif width < 1 / 6 and source == "sweep":
            route = ("verify-first: must survive MMM / a mic shift before "
                     "acting (§13) — single-point narrow spikes evaporate")
        elif kind == "peak":
            route = "point-EQ candidate: cut at fine-localized f0 (§21, §2)"
        else:
            route = ("null-suspect: NO boost until eq_gate / excess-phase / "
                     "mic-shift clears it (§2, §13)")
        out.append({"f_lo": round(float(g[i]), 1), "f_hi": round(float(g[j]), 1),
                    "f_center": round(float(g[k]), 1),
                    "width_oct": round(width, 3),
                    "extremum_db": round(float(r[k]), 2),
                    "kind": kind, "route": route})
        i = j + 1
    return out


def macro_summary(view, seg_frac=3):
    """The from-a-distance read: per ~1/seg_frac-oct segment medians of the
    macro trend (band-anchored), i.e. the tonal shape a target/house
    comparison would argue about."""
    g, m = view["grid"], view["macro"]
    anchor = float(np.median(m))
    rows, f0 = [], g[0]
    while f0 < g[-1] * 0.999:
        f1 = min(f0 * 2 ** (1 / seg_frac), g[-1])
        mm = (g >= f0) & (g <= f1)
        if mm.any():
            rows.append((round(float(f0), 1), round(float(f1), 1),
                         round(float(np.median(m[mm]) - anchor), 2)))
        f0 = f1
    return rows


def report(freqs, mag_db, band, macro_frac=3, fine_frac=24,
           min_prominence_db=2.0, title="", source="sweep"):
    """One-call human-readable multi-scale report (the three distances)."""
    v = multiscale(freqs, mag_db, band, macro_frac, fine_frac)
    lines = [f"=== {title or 'curve'} @ {band[0]:.0f}-{band[1]:.0f} Hz ==="]
    lines.append(f"-- MACRO (1/{macro_frac} oct, band-anchored):")
    for lo, hi, d in macro_summary(v, macro_frac):
        bar = "#" * min(40, int(abs(d) * 4))
        lines.append(f"   {lo:7.0f}-{hi:7.0f}: {d:+6.2f} dB {bar}")
    feats = find_features(v, min_prominence_db, source=source)
    lines.append(f"-- FINE residual (1/{fine_frac} - 1/{macro_frac} oct), "
                 f"|>{min_prominence_db}| dB features: {len(feats)}")
    for f in feats:
        lines.append(f"   {f['kind']:4s} {f['extremum_db']:+6.2f} dB @ "
                     f"{f['f_center']:.0f} ({f['f_lo']:.0f}-{f['f_hi']:.0f}, "
                     f"{f['width_oct']:.2f} oct)\n        -> {f['route']}")
    return "\n".join(lines), feats


def _selftest():
    f = np.geomspace(20.0, 20000.0, 4000)
    curve = 3.0 * np.log2(f / 1000.0) / np.log2(20.0)          # gentle tilt
    curve += 6.0 / (1 + ((np.log2(f / 400.0)) / 0.5) ** 2)     # broad 1-oct hump
    curve += 8.0 * np.exp(-0.5 * (np.log2(f / 2000.0) / 0.04) ** 2)   # narrow spike
    curve -= 7.0 * np.exp(-0.5 * (np.log2(f / 5000.0) / 0.12) ** 2)   # medium dip

    _, feats = report(f, curve, (100.0, 10000.0), title="selftest")
    kinds = {(x["kind"], x["route"].split(":")[0]) for x in feats}
    spikes = [x for x in feats if abs(np.log2(x["f_center"] / 2000)) < 0.15]
    dips = [x for x in feats if abs(np.log2(x["f_center"] / 5000)) < 0.2]
    assert spikes and spikes[0]["kind"] == "peak", feats
    assert spikes[0]["width_oct"] < 1 / 6 and "verify-first" in spikes[0]["route"], spikes
    assert dips and dips[0]["kind"] == "dip" and "null-suspect" in dips[0]["route"], dips
    # the broad hump must NOT appear as a fine feature (it belongs to macro)
    assert not any(abs(np.log2(x["f_center"] / 400)) < 0.3 and x["width_oct"] > 2 / 3
                   for x in feats), feats
    v = multiscale(f, curve, (100.0, 10000.0))
    mac = macro_summary(v)
    seg400 = [d for lo, hi, d in mac if lo <= 400 <= hi]
    assert seg400 and seg400[0] > 2.0, mac  # the hump lives in the macro view
    print(f"selftest OK -- {len(feats)} fine features "
          f"(narrow peak -> verify-first; medium dip -> null-suspect); "
          f"broad 400 Hz hump correctly in MACRO (+{seg400[0]:.1f} dB), "
          f"absent from fine residual")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
