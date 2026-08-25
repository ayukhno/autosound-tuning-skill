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


class CurveViewError(ValueError):
    """The input cannot be read at the FINE scale — chiefly: it is already smoothed.

    REW returns a frequency response with its own smoothing already applied (the payload carries a
    `smoothing` field), and the skill's own `rew_api.set_smoothing` defaults to `1/6`. Smoothing a
    second time here adds widths in quadrature: at REW `1/6` the effective fine becomes ~1/5.8, which
    nearly meets the 1/3 macro, so `residual = fine - macro -> 0` and `find_features` reports a CLEAN
    system that is not — silently, an empty list, no error. That is the trap this refusal makes loud
    (fork session, on live data, 2026-08-25). The FINE scale needs an UNSMOOTHED input.
    """


def _smoothing_frac(smoothing):
    """`"1/24"` -> 24.0; `None`/`"None"`/`"none"`/`""` -> None (unsmoothed, the clean case).
    A non-fractional REW mode (`Var`/`Psy`/`ERB`) is smoothing of unknown width -> returns `"?"`,
    which the fine guard treats as present-and-corrupting, since it cannot prove it negligible."""
    if smoothing is None:
        return None
    t = str(smoothing).strip()
    if t == "" or t.lower() in ("none", "no", "off", "unsmoothed"):
        return None
    if t.startswith("1/"):
        try:
            return float(t[2:])
        except ValueError:
            return "?"
    return "?"


def _effective_fine_frac(fine_frac, input_frac):
    """FWHMs add ~in quadrature (exact for Gaussians; REW smooths band-wise, so this is an ESTIMATE,
    right in direction and order, not a measurement). Returns the effective fine denominator."""
    if input_frac is None:
        return float(fine_frac)
    if input_frac == "?":
        return None
    fwhm = (1.0 / fine_frac ** 2 + 1.0 / input_frac ** 2) ** 0.5
    return 1.0 / fwhm


def _gauss_smooth(y, sigma_pts):
    n = int(max(3, round(sigma_pts * 8)) | 1)
    k = np.exp(-0.5 * ((np.arange(n) - n // 2) / sigma_pts) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(y, n // 2, mode="edge"), k, mode="valid")


def _smooth_frac(y, frac_oct):
    """Gaussian smoothing with FWHM = 1/frac_oct octave on the PPO grid."""
    return _gauss_smooth(y, PPO / frac_oct / 2.355)


def multiscale(freqs, mag_db, band, macro_frac=3, fine_frac=24, input_smoothing=None):
    """Resample to a log grid inside band and split into scales.

    Returns dict: grid, raw, macro (1/macro_frac trend), fine (1/fine_frac),
    residual (fine - macro), and the smoothing the INPUT already carried
    (`input_smoothing`, `input_frac`, `effective_fine_frac`).

    `input_smoothing` is the FR's own smoothing (`rew_api.fr_smoothing(mid)` / the
    payload `smoothing`). It barely touches the macro trend (1/24 input vs 1/3 macro
    = 1/2.99 in quadrature), so `macro_summary` stays valid on smoothed input — but it
    corrupts the FINE residual, and `find_features` refuses on it. See `CurveViewError`."""
    lo, hi = band
    grid = np.geomspace(lo, hi, max(int(np.log2(hi / lo) * PPO), 16))
    raw = np.interp(grid, freqs, mag_db)
    macro = _smooth_frac(raw, macro_frac)
    fine = _smooth_frac(raw, fine_frac)
    input_frac = _smoothing_frac(input_smoothing)
    return {"grid": grid, "raw": raw, "macro": macro, "fine": fine,
            "residual": fine - macro, "fine_frac": fine_frac, "macro_frac": macro_frac,
            "input_smoothing": input_smoothing, "input_frac": input_frac,
            "effective_fine_frac": _effective_fine_frac(fine_frac, input_frac)}


def find_features(view, min_prominence_db=2.0, source="sweep"):
    """Contiguous |residual| >= prominence runs -> features with doctrine
    routing. Each: {f_lo, f_hi, f_center, width_oct, extremum_db, kind,
    route}. kind: 'peak'|'dip'. source: 'sweep' (single-point — narrow
    features need MMM/mic-shift arbitration first, §13) or 'mmm' (already
    spatially averaged — narrow features are real in space, route by kind)."""
    if view.get("input_frac") is not None:
        eff = view.get("effective_fine_frac")
        eff_s = f"~1/{eff:.1f}" if eff else "unknown (a non-fractional REW mode)"
        raise CurveViewError(
            f"the input is already smoothed at {view.get('input_smoothing')!r}; smoothing it again at "
            f"1/{view.get('fine_frac')} makes the effective fine {eff_s} oct, so the fine residual "
            f"(vs the 1/{view.get('macro_frac')} macro) is understated or collapses to zero and this "
            f"would report a CLEAN system that is not. Pull the FR UNSMOOTHED for fine analysis: "
            f"`rew_api.set_smoothing(mid, 'None')` before `get_fr`, or read `rew_api.fr_smoothing(mid)` "
            f"and pass it as `input_smoothing`. MACRO / macro_summary is unaffected and may be used "
            f"on smoothed input.")
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
           min_prominence_db=2.0, title="", source="sweep", input_smoothing=None):
    """One-call human-readable multi-scale report (the three distances).

    Pass `input_smoothing` = the FR's own smoothing; `find_features` refuses a smoothed
    input rather than silently reporting a clean system (`CurveViewError`)."""
    v = multiscale(freqs, mag_db, band, macro_frac, fine_frac, input_smoothing=input_smoothing)
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

    # A pre-smoothed input must be REFUSED at the fine scale, not reported as clean (fork, 2026-08-25).
    # The narrow 2 kHz spike is exactly what double-smoothing would erase.
    for sm, must in (("1/6", "collapses to zero"), ("1/24", "understated"), ("Psy", "non-fractional")):
        vi = multiscale(f, curve, (100.0, 10000.0), input_smoothing=sm)
        try:
            find_features(vi)
            raise AssertionError(f"find_features accepted input smoothed at {sm}")
        except CurveViewError as e:
            assert str(sm) in str(e) or must in str(e), (sm, str(e))
    # None / "None" / "" are the clean case and pass; and the effective-fine estimate is right in order.
    for clean in (None, "None", "none", ""):
        find_features(multiscale(f, curve, (100.0, 10000.0), input_smoothing=clean))
    assert abs(_effective_fine_frac(24, 6) - 5.8) < 0.2, _effective_fine_frac(24, 6)
    assert _effective_fine_frac(24, None) == 24.0 and _effective_fine_frac(24, "?") is None
    # MACRO is unaffected by input smoothing and stays usable on a smoothed input.
    assert macro_summary(multiscale(f, curve, (100.0, 10000.0), input_smoothing="1/6"))
    print(f"selftest OK -- {len(feats)} fine features "
          f"(narrow peak -> verify-first; medium dip -> null-suspect); "
          f"broad 400 Hz hump correctly in MACRO (+{seg400[0]:.1f} dB), "
          f"absent from fine residual")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
