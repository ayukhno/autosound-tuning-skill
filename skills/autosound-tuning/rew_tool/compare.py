"""compare -- two or more REW measurements side by side, at named frequencies and over a named band (#58 P9).

The Antigravity session compared curves with `python -c` one-liners, and four of them failed on
PowerShell's quoting before one ran. What it needed is one command with the questions a comparison
asks as flags:

    python3 rew_tool/compare.py --titles "w-L_51 (rta)" "w-R_51 (rta)" --at 60,125,250,500
    python3 rew_tool/compare.py --titles "ALL_51 (rta)" --target curves/house.txt --band 40-16000

Every number says what it is: the smoothing it was read at (REW computes it on the way out and the
measurement's own view is left alone, hub TCC-015), and an RMS says over which band, with the level
taken out when a target is the reference (a target is a SHAPE, `naming-and-structure.md` §6).
"""

from __future__ import annotations

import argparse
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _log_interp(freqs, values, hz):
    """The value at `hz`, interpolated on log frequency; None outside the data."""
    if not freqs or hz < freqs[0] or hz > freqs[-1]:
        return None
    lo, hi = 0, len(freqs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if freqs[mid] <= hz:
            lo = mid
        else:
            hi = mid
    f0, f1 = freqs[lo], freqs[hi]
    if f1 == f0:
        return values[lo]
    t = (math.log(hz) - math.log(f0)) / (math.log(f1) - math.log(f0))
    return values[lo] + t * (values[hi] - values[lo])


def band_stats(freqs, mag, lo, hi, reference=None):
    """`{"mean", "rms_vs", "points"}` over [lo, hi], read on a log grid so each octave has the same say: the mean
    of the dB, and against `reference` (`[(hz, db)]`) the RMS of the difference with its mean removed."""
    grid = [lo * (hi / lo) ** (i / 95.0) for i in range(96)]
    own = [_log_interp(freqs, mag, f) for f in grid]
    pts = [(f, v) for f, v in zip(grid, own) if v is not None]
    if len(pts) < 3:
        return None
    mean = sum(v for _, v in pts) / len(pts)
    out = {"mean": mean, "points": len(pts), "rms_vs": None}
    if reference:
        rf = [h for h, _ in reference]
        rv = [d for _, d in reference]
        diff = [v - r for (f, v) in pts if (r := _log_interp(rf, rv, f)) is not None]
        if len(diff) >= 3:
            m = sum(diff) / len(diff)
            out["rms_vs"] = math.sqrt(sum((d - m) ** 2 for d in diff) / len(diff))
    return out


def compare(curves, at=(), band=None, target=None):
    """`curves`: `{title: (freqs, mag)}`. Returns rows for the table and the band lines, as data."""
    rows = []
    for hz in at:
        vals = {t: _log_interp(f, m, hz) for t, (f, m) in curves.items()}
        rows.append({"hz": hz, "db": vals})
    bands = {}
    if band:
        first = next(iter(curves))
        ref_curve = list(zip(*curves[first])) if len(curves) > 1 and not target else None
        for title, (f, m) in curves.items():
            reference = target if target else (ref_curve if title != first else None)
            bands[title] = band_stats(f, m, band[0], band[1], reference)
    return {"rows": rows, "bands": bands}


class MissingTitle(KeyError):
    """REW holds no measurement under the title asked for (`read_curves`)."""


def read_curves(titles, smoothing, api=None):
    """`(curves, shifts, base_offset)`: `{title: (freqs, mag)}` as REW's frequency response gives them -- dB SPL, on
    each measurement's own SPL calibration -- each brought to the FIRST title's calibration (#176, hub #285 TCC-060):
    REW 5.40 beta 135 reset `splOffsetdB` 103.35 -> 120.0 between two rounds, and two rounds side by side then read
    16.65 dB apart for no reason in the car. `shifts` is `{title: dB subtracted}`; a title that could not be brought --
    no `splOffsetdB` on it or on the first -- is None there, said by `render`, when any title carries one (the task
    review, #176); with none carrying one, nothing is said and every shift is 0. `base_offset` is the first title's
    `splOffsetdB`, or None. Raises `MissingTitle` for REW's "no such title" only -- a title REW holds twice
    (`AmbiguousTitle`) is raised as REW said it."""
    if api is None:
        import rew_api as api  # noqa: F811
    import levelbase
    listing = api.get_measurements()
    not_found = getattr(api, "MeasurementNotFound", None)
    curves, shifts, base, offsets = {}, {}, None, {}
    for i, title in enumerate(titles):
        try:
            mid = api.find_measurement_id(title, listing)
        except Exception as exc:  # noqa: BLE001 -- REW's "no such title" only; anything else is raised as it is
            if not_found is None or not isinstance(exc, not_found):
                raise
            mid = None
        if mid is None:
            raise MissingTitle(title)
        freqs, mag, _phase = api.get_fr(mid, smoothing=smoothing)
        offsets[title] = levelbase._number((listing.get(mid) or {}).get("splOffsetdB"))
        if i == 0:
            base = offsets[title]
        shifts[title] = levelbase.spl_shift(offsets[title], base)
        curves[title] = (list(freqs), levelbase.to_base(list(mag), shifts[title]))
    if any(v is not None for v in offsets.values()):
        for title, off in offsets.items():
            if off is None or base is None:
                shifts[title] = None                   # not brought: said by `render`
    return curves, shifts, base


def render(result, titles, smoothing, band=None, target_name=None, shifts=None, base_offset=None):
    lines = [f"  read at {smoothing} smoothing (computed by REW on the way out; the view is untouched)"]
    moved = [(t, d) for t, d in (shifts or {}).items() if t in titles and d is not None and round(d, 2) != 0]
    unbrought = [t for t in titles if t in (shifts or {}) and shifts[t] is None]
    if unbrought:
        lines.append("  levels not brought (no splOffsetdB): " + ", ".join(unbrought)
                     + (f" -- the first, {titles[0]}, carries none, so none is brought" if titles[0] in unbrought
                        else ""))
    if moved:
        # The shift applied, said (#176): the levels are on the first title's SPL calibration, not REW's.
        lines.append(f"  levels brought to {titles[0]}'s REW SPL calibration"
                     + (f" (splOffsetdB {base_offset:.2f})" if base_offset is not None else "") + ": "
                     + ", ".join(f"{t} {-d:+.2f} dB" for t, d in moved))
    if result["rows"]:
        lines.append("  " + f"{'Hz':>8}  " + "  ".join(f"{t[:22]:>22}" for t in titles)
                     + ("  " + f"{'2nd - 1st':>10}" if len(titles) == 2 else ""))
        for r in result["rows"]:
            vals = [r["db"][t] for t in titles]
            cells = "  ".join(f"{'--' if v is None else f'{v:.1f} dB':>22}" for v in vals)
            delta = ""
            if len(titles) == 2 and None not in vals:
                delta = f"  {vals[1] - vals[0]:>+9.1f} dB"
            lines.append(f"  {r['hz']:>8g}  {cells}{delta}")
    if band and result["bands"]:
        ref = f"against {target_name}" if target_name else f"against {titles[0]}"
        for title in titles:
            b = result["bands"].get(title)
            if not b:
                lines.append(f"  {title}: no points in {band[0]:g}-{band[1]:g} Hz")
                continue
            rms = ("" if b["rms_vs"] is None
                   else f"; RMS {ref}, level removed: {b['rms_vs']:.2f} dB")
            lines.append(f"  {title}: {band[0]:g}-{band[1]:g} Hz, log-weighted mean {b['mean']:.1f} dB{rms}")
    return "\n".join(lines)


def _selftest():
    f = [20.0 * 2 ** (i / 24.0) for i in range(240)]
    a = [80.0 for _ in f]
    b = [80.0 + (3.0 if 200 <= x <= 400 else 0.0) for x in f]
    res = compare({"a": (f, a), "b": (f, b)}, at=(100.0, 300.0), band=(100.0, 1000.0))
    assert abs(res["rows"][1]["db"]["b"] - 83.0) < 0.2 and abs(res["rows"][0]["db"]["b"] - 80.0) < 0.2, res
    assert res["bands"]["a"]["rms_vs"] is None and res["bands"]["b"]["rms_vs"] > 0.5, res["bands"]
    shown = render(res, ["a", "b"], "1/6", band=(100.0, 1000.0))
    assert "+3.0 dB" in shown and "level removed" in shown and "1/6" in shown, shown
    flat = compare({"a": (f, a)}, band=(40.0, 16000.0), target=[(20.0, 5.0), (20000.0, 5.0)])
    assert abs(flat["bands"]["a"]["rms_vs"]) < 1e-9, "a target is a shape: a level offset is not an error"
    # #176 (hub #285): two titles REW calibrated apart -- the 08.10 reset, 103.35 then 120.0 -- are one curve 16.65 dB
    # apart as read; brought to the first one's calibration they read the same, and the table says the shift.
    class _Rew:
        FINEST_SMOOTHING = "1/48"
        listing = {"1": {"title": "ALL_3 (rta)", "splOffsetdB": 103.34649658203125},
                   "2": {"title": "ALL_4 (rta)", "splOffsetdB": 120.0}, "3": {"title": "ALL_5 (rta)"}}

        def get_measurements(self):
            return self.listing

        def find_measurement_id(self, title, measurements=None, exact=True):
            return next((k for k, v in self.listing.items() if v["title"] == title), None)

        def get_fr(self, mid, smoothing=None):
            return f, [m + (self.listing[mid].get("splOffsetdB") or 0.0) for m in a], None
    curves, shifts, base = read_curves(["ALL_3 (rta)", "ALL_4 (rta)", "ALL_5 (rta)"], "1/6", api=_Rew())
    assert round(shifts["ALL_4 (rta)"], 2) == 16.65 and shifts["ALL_3 (rta)"] == 0.0 and shifts["ALL_5 (rta)"] is None
    res = compare(curves, at=(300.0,))
    assert abs(res["rows"][0]["db"]["ALL_4 (rta)"] - res["rows"][0]["db"]["ALL_3 (rta)"]) < 1e-6, res
    shown = render(res, ["ALL_3 (rta)", "ALL_4 (rta)"], "1/6", shifts=shifts, base_offset=base)
    assert "brought to ALL_3 (rta)'s REW SPL calibration (splOffsetdB 103.35): ALL_4 (rta) -16.65 dB" in shown, shown
    assert "brought to" not in render(res, ["ALL_3 (rta)"], "1/6", shifts={"ALL_3 (rta)": 0.0})
    # A title REW lists no calibration for, among calibrated ones, is said as not brought (the task review, #176) --
    # the first one too, when it is the one without: then nothing is brought, and that is said.
    said = render(res, ["ALL_3 (rta)", "ALL_4 (rta)", "ALL_5 (rta)"], "1/6", shifts=shifts, base_offset=base)
    assert "not brought (no splOffsetdB): ALL_5 (rta)" in said, said
    _, s2, b2 = read_curves(["ALL_5 (rta)", "ALL_4 (rta)"], "1/6", api=_Rew())
    assert b2 is None and s2 == {"ALL_5 (rta)": None, "ALL_4 (rta)": None}, s2
    assert "not brought (no splOffsetdB): ALL_5 (rta), ALL_4 (rta)" in render(
        res, ["ALL_5 (rta)", "ALL_4 (rta)"], "1/6", shifts=s2, base_offset=b2)
    # Only REW's "no such title" is a missing title; a title REW holds twice is raised as REW said it.
    class _Twice(_Rew):
        class AmbiguousTitle(KeyError):
            pass

        class MeasurementNotFound(KeyError):
            pass

        def find_measurement_id(self, title, measurements=None, exact=True):
            if title == "gone":
                raise self.MeasurementNotFound(title)
            raise self.AmbiguousTitle(f"Ambiguous: 2 measurements titled {title!r}")
    try:
        read_curves(["gone"], "1/6", api=_Twice())
    except MissingTitle:
        pass
    else:
        raise AssertionError("REW's 'no such title' was not a missing title")
    try:
        read_curves(["ALL_3 (rta)"], "1/6", api=_Twice())
    except MissingTitle:
        raise AssertionError("a title REW holds twice was called missing")
    except KeyError as exc:
        assert "Ambiguous" in str(exc), exc
    # ...and the command line says it, exit 1, no traceback (the re-review, #176).
    import contextlib
    import io
    import rew_api
    saved = {n: getattr(rew_api, n) for n in ("get_measurements", "find_measurement_id")}
    try:
        rew_api.get_measurements = lambda: {"1": {"title": "ALL_3 (rta)"}, "2": {"title": "ALL_3 (rta)"}}
        rew_api.find_measurement_id = lambda title, measurements=None, exact=True: (_ for _ in ()).throw(
            rew_api.AmbiguousTitle(f"Ambiguous: 2 measurements titled {title!r}"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["--titles", "ALL_3 (rta)"])
        assert rc == 1 and "REW holds ALL_3 (rta) twice -- rename one" in err.getvalue(), (rc, err.getvalue())
    finally:
        for n, fn in saved.items():
            setattr(rew_api, n, fn)
    print("selftest[compare] OK -- values at named frequencies with the difference, a band's log-weighted mean, "
          "the RMS against a target or the first curve with the level removed, and the smoothing named; titles REW "
          "calibrated apart brought to the first one's splOffsetdB, the shift said (#176)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="REW measurements side by side (#58 P9)")
    ap.add_argument("--titles", nargs="+", help="the measurement titles, as REW holds them")
    ap.add_argument("--at", default="", help="comma list of frequencies (Hz)")
    ap.add_argument("--band", default=None, help="lo-hi (Hz) for the band lines")
    ap.add_argument("--target", default=None, help="a REW-style text curve; the band's RMS is taken against it")
    ap.add_argument("--smoothing", default="1/6", help="what REW computes on the way out (default 1/6)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.titles:
        ap.error("--titles is required")
    import variant_front
    try:
        curves, shifts, base_offset = read_curves(args.titles, args.smoothing)
    except MissingTitle as exc:
        print(f"refusing: REW holds no measurement titled {exc.args[0]!r}", file=sys.stderr)
        return 3
    except KeyError as exc:
        import rew_api
        if not isinstance(exc, rew_api.AmbiguousTitle):
            raise
        # A title REW holds twice (the re-review, #176): which one was meant is not knowable -- said, never a traceback.
        title = next((t for t in args.titles if repr(t) in str(exc)), "a title")
        print(f"refusing: REW holds {title} twice -- rename one ({exc.args[0] if exc.args else exc})",
              file=sys.stderr)
        return 1
    at = [float(x) for x in args.at.split(",") if x.strip()]
    band = tuple(float(x) for x in args.band.split("-")) if args.band else None
    target = variant_front.read_target(args.target) if args.target else None
    print(render(compare(curves, at=at, band=band, target=target), args.titles, args.smoothing, band=band,
                 target_name=os.path.basename(args.target) if args.target else None, shifts=shifts,
                 base_offset=base_offset))
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    raise SystemExit(main())
