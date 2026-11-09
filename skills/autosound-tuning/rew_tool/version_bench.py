#!/usr/bin/env python3
"""version_bench -- whole ledger versions side by side, whichever path built them (#210).

A library, not the method (the Arbiter, 2026-11-08): it reads, compares and says what it could not read; it never banks
and never picks past `variant_front`'s own rule. Every threshold here is a named default, changed by a flag, and a
changed value is shown with what the default gives beside it. Versions on different point coverage refuse rather than compare.

    python3 rew_tool/version_bench.py table --project DIR (--solos DIR | --rew --ver N) [--house FILE] [--route VIRTUAL=out1,out2]
                                            [--phase-window DEG] [--width-span OCT] [--ring-ratio X] [--json] VERSION VERSION...
    python3 rew_tool/version_bench.py loudness --project DIR (--solos DIR | --rew --ver N) [--route VIRTUAL=out1,out2] [--phon N]
                                            [--level-db DB ...] [--field diffuse|free] [--bass-band LO:HI] [--bass-differs-db DB]
                                            [--gain-span DB] [--json] VERSION VERSION...
    python3 rew_tool/version_bench.py lr-phase --project DIR (--solos DIR | --rew --ver N) [--route VIRTUAL=out1,out2] [--band LO:HI]
                                            [--json] VERSION [VERSION...]
    python3 rew_tool/version_bench.py round-check --project DIR (--solos DIR | --rew --ver N) [--flag-rms-db DB] [--floor-db DB]
                                            [--sum-band CODE=LO:HI] [--json]
    python3 rew_tool/version_bench.py --selftest

VERSION is `PRESET/v_014`, `v_014` (on the active preset) or `PRESET` (its head). The preset's input gain goes into the chains once
(`predict.chains_from_snapshot(snap, trim=True)`), on the physical tier only.

  table        per version `predict.predict` -> `predict.to_json` -> `variant_front.terms`, then `variant_front.front`'s picks on its four
               terms, no argmax; a term missing for a version is named, and under two comparable terms no pick is printed. The joint widths,
               ear sums, decay, share and L/R phase stand beside them and take no part in the picks; what cannot be computed is named.
  loudness     Zwicker ISO 532-1 through a lazy `mosqito` (optional), the gain found by bisection; without it the install line, and ISO 226
               at 80 phon, labelled as less exact when the versions differ in the bass.
  lr-phase     L against R, 250-800 Hz: the phase and the group-delay difference, acoustic and electrical, centre and nine points.
  round-check  each tripod sum of the glossary against the complex sum of its solos: rms and maximum over 1/3-oct bands, no offset removed; over
               1 dB rms is flagged as a working threshold, not `verify_prediction`'s validated criterion, which means something else.

Read-only. Each refusal is one line, `refusing: <why>`, exit 3. Deps: numpy + scipy (through `predict`); `mosqito` is optional, imported only for Zwicker.
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import os
import sys
import warnings

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import dsp_profile                               # noqa: E402
import equal_loudness                            # noqa: E402
import joint_search as JS                        # noqa: E402
import naming                                    # noqa: E402
import predict as P                              # noqa: E402
import project as _pj                            # noqa: E402
import variant_front as VF                       # noqa: E402

#: Every threshold is a default, changed by a flag, its effect shown (the principle of #210).
LR_BAND_HZ = (250.0, 800.0)
ISO_PHON = 80.0
ZWICKER_LEVELS_DBC = (75.0, 81.0, 86.0)
ZWICKER_FIELDS = ("diffuse", "free")
#: Where "the versions differ in the bass" is read, and from how large a change of the bass against the rest.
BASS_BAND_HZ = (20.0, 125.0)
BASS_DIFFERS_DB = 1.0
#: The bisection's reach, either way from the reference: a match outside it is said, never clipped.
GAIN_SPAN_DB = 15.0
BISECT_STEPS = 24
#: A working threshold, named so: `verify_prediction`'s validated criterion is another quantity, on another reading.
ROUND_FLAG_RMS_DB = 1.0
#: The joint width's walk, either side of the crossing: past it one driver has left the sum and the phase difference means nothing.
WIDTH_SPAN_OCT = 1.5
#: A sum's own band: the 1/3-oct bands within this of its loudest band, contiguous around it.
ROUND_FLOOR_DB = 20.0
GRID = (20.0, 20000.0, 96)
#: A joint is read by its acoustic crossing, as in `joint_search`: under this the ±band, from it up the power sum.
ZWICKER_INSTALL = "-m pip install mosqito"
ISO_LABEL = "less exact when the versions differ in the bass (ISO 226 weights level only; Zwicker reads the masking)"
ROUND_THRESHOLD_WORDS = ("a working threshold, not `verify_prediction`'s validated criterion, "
                         "which means something else")
_TMP_PREFIX = "autosound_version_bench_"


class VersionBenchError(ValueError):
    """A refusal of this tool: one line, `refusing: <why>`, exit 3."""

    is_refusal = True


# ---------------------------------------------------------------- versions and curves
def _parse_ref(ref):
    """`PRESET/v_014`, `v_014` (the active preset) or `PRESET` (its head) -> (preset, version)."""
    if "/" in ref:
        preset, _, ver = ref.partition("/")
        return preset, ver
    if ref.startswith("v_") and ref[2:].isdigit():
        return None, ref
    return ref, None


def _routes_of(project_dir, specs):
    """The routing matrix, as `predict` reads it: what the run says, then what the project records, else none."""
    if specs:
        routes = {}
        for spec in specs:
            v, _, outs = spec.partition("=")
            routes[v.strip()] = [o.strip() for o in outs.split(",") if o.strip()]
        return routes, "--route"
    recorded = _pj.Project(project_dir).virtual_routing()
    return (recorded, "project.json hardware.virtual_routing") if recorded else ({}, None)


def load_versions(project_dir, refs, route_specs=()):
    """`[{"label", "preset", "version", "chains", "notes"}]`, the preset's trim in the chains once."""
    routes, route_from = _routes_of(project_dir, route_specs)
    out = []
    for ref in refs:
        preset, ver = _parse_ref(ref)
        try:
            preset, snap = P.load_project_state(project_dir, preset, ver)
        except (FileNotFoundError, ValueError) as exc:
            if getattr(type(exc), "is_refusal", False) or getattr(type(exc), "is_unreadable", False):
                raise
            raise VersionBenchError(f"version {ref}: {exc}") from None
        chains = P.chains_from_snapshot(snap, trim=True)
        notes = []
        trim = P.preset_trim_db(snap)
        if trim:
            notes.append(f"{ref}: the preset's input gain {trim:g} dB is in these chains, once")
        if routes:
            chains, route_notes = P.route_chains(chains, P.chains_from_snapshot(snap, tier="virtual_channels"), routes)
            notes.append(f"{ref}: virtual tier routed by {route_from}")
            notes += [f"{ref}: {n}" for n in route_notes]
        else:
            carried = [c for c, r in (snap.get("virtual_channels") or {}).items()
                       if isinstance(r, dict) and (r.get("eq") or r.get("ta_ms") or r.get("gain_db"))]
            if carried:
                notes.append(f"{ref}: the virtual tier carries EQ, gain or delay on {', '.join(sorted(carried))} and no routing is "
                             "recorded: it is left out of this reading (--route VIRTUAL=out1,out2, or record it in the project)")
        out.append({"label": ref, "preset": preset, "version": snap.get("version") or ver, "chains": chains, "notes": notes})
    return out


def _playing(chains):
    return [c for c, ch in chains.items() if not ch.get("muted") and not ch.get("unmodellable")]


def _load_curves(args, codes, freqs, short=False):
    """`joint_search.load_channels` over the channels the versions play: the protective filter out once, `info` kept."""
    if bool(args.solos) == bool(args.rew):
        raise VersionBenchError("say where the curves are: --solos DIR, or --rew --ver N")
    if args.rew and not args.ver:
        raise VersionBenchError("--rew needs --ver N, the series")
    record = None
    if args.rew:
        state_dir = os.path.join(_HERE, "state")
        if state_dir not in sys.path:
            sys.path.insert(0, state_dir)
        import process as _process
        try:
            record = _process.Process(os.path.join(args.project, "process")).protective_record_for(args.ver)
        except _process.ProcessError as exc:
            raise VersionBenchError(f"the capture record of series {args.ver}: {exc}") from None
    return JS.load_channels(sorted(codes), freqs, solos=args.solos, ver=args.ver, api=None, record=record, short=short)


def _curve(curves, code, pos):
    """A channel's reading at `pos`; a sub with no reading there is read at its tripod (a sub may stay at one point)."""
    ch = curves.get(code)
    if ch is None:
        return None
    if pos == "tripod":
        return ch["tripod"]
    h = ch["points"].get(pos)
    return h if h is not None or not P._is_sub(code) else ch["tripod"]


# ---------------------------------------------------------------- point coverage
def _coverage_of(chains, curves):
    """What this version's playing channels were measured on: the points every front channel has, the tripod, and what is left out."""
    playing = _playing(chains)
    no_curve = [c for c in playing if curves[c]["tripod"] is None and not curves[c]["points"]]
    measured = [c for c in playing if c not in no_curve]
    fronts = [c for c in measured if not P._is_sub(c)]
    points = set.intersection(*(set(curves[c]["points"]) for c in fronts)) if fronts else set()
    return {"points": [p for p in JS.POSITIONS if p in points],
            "tripod": bool(measured) and all(curves[c]["tripod"] is not None for c in measured),
            "left_out": sorted(no_curve + [c for c, ch in chains.items() if ch.get("unmodellable")]),
            "short": sorted(c for c in fronts if len(curves[c]["points"]) < max(len(curves[x]["points"]) for x in fronts))}


def check_coverage(versions, curves):
    """The points shared by every version's playing channels, or a refusal naming who has what: a sum read on other points is another sum."""
    cover = {v["label"]: _coverage_of(v["chains"], curves) for v in versions}
    keys = {(tuple(c["points"]), c["tripod"], tuple(c["left_out"])) for c in cover.values()}
    if len(keys) > 1:
        def words(c):
            where = f"{len(c['points'])} point(s) ({c['points'][0]}..{c['points'][-1]})" if c["points"] else "no shared points"
            extra = f", channels with fewer points: {', '.join(c['short'])}" if c["short"] else ""
            gone = f", left out: {', '.join(c['left_out'])}" if c["left_out"] else ""
            return f"{where}, tripod {'yes' if c['tripod'] else 'no'}{extra}{gone}"
        raise VersionBenchError("the versions are on different point coverage, not compared: "
                                + "; ".join(f"{label}: {words(c)}" for label, c in cover.items()))
    return next(iter(cover.values()))["points"]


def _dumps(doc):
    return json.dumps(doc, indent=2, default=_jsonable, ensure_ascii=False)


def _jsonable(x):
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    raise TypeError(f"{type(x).__name__} in the document")


# ---------------------------------------------------------------- L against R
def _chain_sum(freqs, curves, chains, codes, pos):
    """The coherent sum of `codes` at `pos` through their chains; `pos` None is the electrical part alone; None when a reading is missing."""
    y = np.zeros(len(freqs), dtype=complex)
    for code in codes:
        h = 1.0 if pos is None else _curve(curves, code, pos)
        if h is None:
            return None
        y = y + h * P.chain_response(freqs, chains[code])
    return y


def _band_gd_ms(f, y, lo, hi):
    """Power-weighted group delay over the band, the phase unwrapped inside it only (a bulk delay aliases above it on this grid)."""
    m = (f >= lo) & (f <= hi)
    gd = -np.gradient(np.unwrap(np.angle(y[m])), 2.0 * np.pi * f[m]) * 1e3
    p = np.abs(y[m]) ** 2
    return float(np.sum(gd * p) / max(np.sum(p), 1e-30))


def _lr_numbers(f, left, right, band):
    m = (f >= band[0]) & (f <= band[1])
    dphi = float(np.median(np.abs(np.degrees(np.angle(left[m] * np.conj(right[m]))))))
    return dphi, _band_gd_ms(f, left, band[0], band[1]) - _band_gd_ms(f, right, band[0], band[1])


def _lr_row(version, f, curves, band):
    """One version, L against R (`lr_tracking.py`, any stack): the medians over the points of |phase difference| and of the group-delay difference, L minus R."""
    chains = version["chains"]
    row = {"version": version["label"], "acoustic": None, "electrical": None, "why": None}
    codes = {s: [c for c in _playing(chains) if P._side_of(c) == s] for s in ("L", "R")}
    if not codes["L"] or not codes["R"]:
        row["why"] = "L against R needs channels on both sides"
        return row

    def over(points):
        if not points:
            return None
        phis, gds = [], []
        for pos in points:
            left, right = _chain_sum(f, curves, chains, codes["L"], pos), _chain_sum(f, curves, chains, codes["R"], pos)
            phi, gd = _lr_numbers(f, left, right, band)
            phis.append(phi)
            gds.append(gd)
        return {"dphi_deg": round(float(np.median(phis)), 2), "dgd_ms": round(float(np.median(gds)), 3), "points": list(points)}

    everywhere = lambda p: all(p in curves[c]["points"] for c in codes["L"] + codes["R"])  # noqa: E731
    centre = [p for p in JS.CENTRE_POINTS if everywhere(p)]
    if not centre and all(curves[c]["tripod"] is not None for c in codes["L"] + codes["R"]):
        centre = ["tripod"]
    nine = [p for p in JS.POSITIONS if everywhere(p)]
    row["acoustic"] = {"centre": over(centre), "nine": over(nine)}
    if not nine:
        row["why"] = "no shared points: the nine-point reading cannot be computed"
    phi, gd = _lr_numbers(f, _chain_sum(f, curves, chains, codes["L"], None), _chain_sum(f, curves, chains, codes["R"], None), band)
    row["electrical"] = {"dphi_deg": round(phi, 2), "dgd_ms": round(gd, 3)}
    return row


def lr_doc(versions, freqs, curves, band, th=None):
    f = np.asarray(freqs, float)
    if int(np.sum((f >= band[0]) & (f <= band[1]))) < 3:
        raise VersionBenchError(f"--band {band[0]:g}:{band[1]:g}: under three grid points, too narrow for a group delay")
    doc = {"band_hz": list(band), "rows": [_lr_row(v, f, curves, band) for v in versions], "default_band": None,
           "notes": [n for v in versions for n in v["notes"]]}
    if tuple(band) != LR_BAND_HZ:
        doc["default_band"] = {"band_hz": list(LR_BAND_HZ), "rows": [_lr_row(v, f, curves, LR_BAND_HZ) for v in versions]}
    return doc


def _lr_lines(rows):
    lines = []
    for r in rows:
        if r["acoustic"] is None:
            lines.append(f"  {r['version'][:22]:22} cannot be computed: {r['why']}")
            continue
        for name in ("centre", "nine"):
            a = r["acoustic"][name]
            lines.append(f"  {r['version'][:22]:22} acoustic {name:6} "
                         + (f"|dphi| {a['dphi_deg']:6.1f} deg   dGD L-R {a['dgd_ms']:+.3f} ms   ({len(a['points'])} point(s))" if a else "cannot be computed"))
        e = r["electrical"]
        lines.append(f"  {r['version'][:22]:22} electrical (the same at every point) |dphi| {e['dphi_deg']:6.1f} deg   dGD L-R {e['dgd_ms']:+.3f} ms")
        if r["why"]:
            lines.append(f"  {r['version'][:22]:22} {r['why']}")
    return lines


def render_lr(doc):
    lines = [f"  L against R, {doc['band_hz'][0]:g}-{doc['band_hz'][1]:g} Hz: the median |phase difference| and the group-delay difference L minus R; the electrical part is the chains alone, what a "
             "crossover choice controls"]
    lines += _lr_lines(doc["rows"])
    if doc["default_band"]:
        lines.append(f"  changed from the default band; at the default {doc['default_band']['band_hz'][0]:g}-{doc['default_band']['band_hz'][1]:g} Hz:")
        lines += _lr_lines(doc["default_band"]["rows"])
    lines += _notes_lines(doc["notes"])
    lines.append("  Reads and compares; nothing is entered from here.")
    return "\n".join(lines)


def _notes_lines(notes):
    return [f"  note: {n}" for n in dict.fromkeys(notes)]


# ---------------------------------------------------------------- loudness
def _power_mean(f, curves, chains, points):
    """The power over the points of the coherent sum of every playing channel, the centre included (what is heard)."""
    keys = points or ["tripod"]
    total = np.zeros(len(f))
    for pos in keys:
        y = np.zeros(len(f), dtype=complex)
        for code in _playing(chains):
            h = _curve(curves, code, pos)
            if h is not None:
                y = y + h * P.chain_response(f, chains[code])
        total = total + np.abs(y) ** 2
    return total / len(keys)


def _iso_weight(f, phon):
    """The power weight of the ISO 226 contour at `phon`, 0 dB at 1 kHz."""
    ref = equal_loudness.iso226_spl(phon, 1000.0)
    spl = np.array([equal_loudness.iso226_spl(phon, float(x)) for x in np.clip(f, 20.0, 12500.0)])
    return 10.0 ** ((ref - spl) / 10.0)


def _iso_rows(labels, powers, weight):
    """Level on the log grid (equal weight per octave: pink), against the first version. `match_gain_db` is what that version's input takes to match."""
    level = [10.0 * math.log10(float(np.mean(p * weight))) for p in powers]
    return [{"version": lab, "level_db": round(x - level[0], 3), "match_gain_db": round(level[0] - x, 3)} for lab, x in zip(labels, level)]


def _band_level(f, p, lo, hi):
    m = (f >= lo) & (f <= hi)
    return 10.0 * math.log10(max(float(np.mean(p[m])), 1e-30)) if m.any() else None


def _bass_diff_db(f, powers, band):
    """The largest change, across the versions, of the bass band's level against the rest of the range, dB."""
    def shape(p):
        bass, rest = _band_level(f, p, band[0], band[1]), _band_level(f, p, band[1], f[-1])
        return None if bass is None or rest is None else bass - rest
    shapes = [shape(p) for p in powers]
    if any(s is None for s in shapes):
        return None
    return max(abs(s - shapes[0]) for s in shapes)


_FL = np.arange(10.0, 20000.0, 2.0)


def _c_weight_power(f):
    """IEC 61672 C weighting as a power weight, 0 dB at 1 kHz: the level a meter reads, to set the reference version's level."""
    f1, f4 = 20.598997, 12194.217
    r = (f4 ** 2 * f ** 2) / ((f ** 2 + f1 ** 2) * (f ** 2 + f4 ** 2))
    return (r / ((f4 ** 2 * 1e6) / ((1e6 + f1 ** 2) * (1e6 + f4 ** 2)))) ** 2


def _psd(f, p):
    """A pink power curve on the log grid as a density on `_FL`, Pa^2/Hz up to a constant."""
    return np.interp(np.log(_FL), np.log(f), p, left=0.0, right=0.0) / _FL


def _zwicker_fn():
    """`mosqito`'s stationary loudness, imported only when asked for: `(function, None)` or `(None, why)`."""
    try:
        with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from mosqito.sq_metrics import loudness_zwst_freq
    except Exception as exc:  # noqa: BLE001 -- a library that cannot be imported, for any reason, is the same answer: the install line
        return None, f"{type(exc).__name__}: {exc}"
    return loudness_zwst_freq, None


def _zwicker_blocks(fn, labels, powers, f, levels, fields, span):
    """Per reference level and sound field: the gain each version takes for the reference's sones, by bisection (`loudness_match.py`)."""
    psd = [_psd(f, p) for p in powers]
    cw = _c_weight_power(_FL)
    dbc = lambda x: 10.0 * math.log10(max(float(np.sum(x * cw * 2.0)), 1e-30))  # noqa: E731

    def sones(x, field):
        with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(np.atleast_1d(fn(np.sqrt(x * 2.0), _FL, field_type=field)[0])[0])

    blocks = []
    for level in levels:
        k = 10.0 ** ((level - dbc(psd[0])) / 10.0) * (2e-5) ** 2
        for field in fields:
            ref = sones(psd[0] * k, field)
            rows = []
            for lab, x in zip(labels, psd):
                def at(g):
                    return sones(x * k * 10.0 ** (g / 10.0), field)
                lo, hi = -span, span
                if at(lo) > ref or at(hi) < ref:
                    rows.append({"version": lab, "level_db": None, "match_gain_db": None, "why": f"its match lies outside +-{span:g} dB (--gain-span)"})
                    continue
                for _ in range(BISECT_STEPS):
                    g = (lo + hi) / 2.0
                    if at(g) < ref:
                        lo = g
                    else:
                        hi = g
                g = (lo + hi) / 2.0
                rows.append({"version": lab, "level_db": round(-g, 3), "match_gain_db": round(g, 3)})
            blocks.append({"level_dbc": level, "field": field, "ref_sones": round(ref, 2), "rows": rows})
    return blocks


def loudness_doc(versions, freqs, curves, points, th):
    f = np.asarray(freqs, float)
    labels = [v["label"] for v in versions]
    powers = [_power_mean(f, curves, v["chains"], points) for v in versions]
    bass = _bass_diff_db(f, powers, th["bass_band"])
    bass_default = _bass_diff_db(f, powers, BASS_BAND_HZ)
    iso = {"phon": th["phon"], "rows": _iso_rows(labels, powers, _iso_weight(f, th["phon"])), "label": ISO_LABEL,
           "bass_band_hz": list(th["bass_band"]), "bass_diff_db": None if bass is None else round(bass, 2),
           "bass_differs": bool(bass is not None and bass >= th["bass_differs_db"]),
           "bass_differs_at_default": bool(bass_default is not None and bass_default >= BASS_DIFFERS_DB),
           "bass_differs_db": th["bass_differs_db"], "default": None}
    changed = []
    if th["phon"] != ISO_PHON:
        iso["default"] = {"phon": ISO_PHON, "rows": _iso_rows(labels, powers, _iso_weight(f, ISO_PHON))}
        changed.append(f"--phon {th['phon']:g} (default {ISO_PHON:g}): the contour moves every level below")
    if th["bass_differs_db"] != BASS_DIFFERS_DB or tuple(th["bass_band"]) != BASS_BAND_HZ:
        changed.append(f"bass read at {th['bass_band'][0]:g}-{th['bass_band'][1]:g} Hz, {th['bass_differs_db']:g} dB; at the defaults "
                       f"({BASS_BAND_HZ[0]:g}-{BASS_BAND_HZ[1]:g} Hz, {BASS_DIFFERS_DB:g} dB) the versions {'do' if iso['bass_differs_at_default'] else 'do not'} differ in the bass")
    doc = {"reference": labels[0], "points": list(points) or ["tripod"], "iso226": iso, "zwicker": None, "install_line": None,
           "changed": changed, "notes": [n for v in versions for n in v["notes"]]}
    fn, why = _zwicker_fn()
    if fn is None:
        doc["install_line"] = f'"{sys.executable}" {ZWICKER_INSTALL}'
        doc["zwicker_absent"] = why
        return doc
    try:
        fields, levels = tuple(th["fields"]), list(th["levels"])
        z = {"blocks": _zwicker_blocks(fn, labels, powers, f, levels, fields, th["gain_span_db"]), "default": None}
        if fields != ZWICKER_FIELDS or levels != list(ZWICKER_LEVELS_DBC) or th["gain_span_db"] != GAIN_SPAN_DB:
            z["default"] = _zwicker_blocks(fn, labels, powers, f, list(ZWICKER_LEVELS_DBC), ZWICKER_FIELDS, GAIN_SPAN_DB)
            changed.append("Zwicker levels, field or gain span changed: the default run is shown beside it")
        doc["zwicker"] = z
    except Exception as exc:  # noqa: BLE001 -- a library's failure is said and the ISO 226 reading stands; never a traceback over a working number
        doc["zwicker_failed"] = f"{type(exc).__name__}: {exc}"
        doc["install_line"] = f'"{sys.executable}" {ZWICKER_INSTALL}'
    return doc


def _loud_rows(rows):
    return [f"    {r['version'][:24]:24} {('--' if r['level_db'] is None else format(r['level_db'], '+.2f')):>8} dB   its input takes {('--' if r['match_gain_db'] is None else format(r['match_gain_db'], '+.2f')):>8} dB to match"
            + (f"   {r['why']}" if r.get("why") else "") for r in rows]


def _zwicker_lines(blocks):
    lines = []
    for b in blocks:
        lines.append(f"  Zwicker, {b['level_dbc']:g} dB(C), {b['field']} field ({b['ref_sones']:g} sone):")
        lines += _loud_rows(b["rows"])
    return lines


def render_loudness(doc):
    iso = doc["iso226"]
    where = "the nine points" if len(doc["points"]) == len(JS.POSITIONS) else ", ".join(doc["points"])
    lines = [f"  loudness against {doc['reference']}: every playing channel summed coherently, power over {where}; pink. A prediction: confirm on a real RTA before an A/B"]
    if doc["zwicker"]:
        lines += _zwicker_lines(doc["zwicker"]["blocks"])
        if doc["zwicker"]["default"]:
            lines.append("  at the default levels and fields:")
            lines += _zwicker_lines(doc["zwicker"]["default"])
    else:
        lines.append("  Zwicker ISO 532-1 needs the optional `mosqito`: " + str(doc["install_line"]))
        if doc.get("zwicker_failed"):
            lines.append(f"  it was there and failed: {doc['zwicker_failed']}")
    lines.append(f"  ISO 226 at {iso['phon']:g} phon -- {iso['label']}:")
    lines += _loud_rows(iso["rows"])
    if iso.get("default"):
        lines.append(f"  at the default {iso['default']['phon']:g} phon:")
        lines += _loud_rows(iso["default"]["rows"])
    if iso["bass_differs"]:
        lines.append(f"  the versions differ in the bass here ({iso['bass_diff_db']:.1f} dB, {iso['bass_band_hz'][0]:g}-{iso['bass_band_hz'][1]:g} Hz against the rest, "
                     f"--bass-differs-db {iso['bass_differs_db']:g}): read ISO 226 as less exact here" + ("" if doc["zwicker"] else ", or install mosqito"))
    lines += [f"  changed: {c}" for c in doc["changed"]]
    lines += _notes_lines(doc["notes"])
    lines.append("  Reads and compares; a trim is entered by the tuner.")
    return "\n".join(lines)


# ---------------------------------------------------------------- the round-check
def _third_bands(freqs):
    """The 1/3-octave centres inside the grid, and each band's mask."""
    f = np.asarray(freqs, float)
    k = 2.0 ** (1.0 / 6.0)
    centres = [c for c in 1000.0 * 2.0 ** (np.arange(-20, 15) / 3.0) if f[0] * k <= c <= f[-1] / k]
    return np.asarray(centres), [(f >= c / k) & (f <= c * k) for c in centres]


def _band_levels(h, masks):
    return np.array([10.0 * math.log10(max(float(np.mean(np.abs(h[m]) ** 2)), 1e-30)) for m in masks])


def _sum_rows(freqs, sums, band_of, floor_db):
    """Per sum: the measured level against the complex sum of its solos over 1/3-oct bands, rms and maximum, no offset removed (`s4_6b_vs_model.py:165-168`)."""
    centres, masks = _third_bands(freqs)
    rows = []
    for code, (measured, members, solo_sum) in sums.items():
        have, want = _band_levels(measured, masks), _band_levels(solo_sum, masks)
        if code in band_of:
            keep = (centres >= band_of[code][0]) & (centres <= band_of[code][1])
        else:
            peak = int(np.argmax(want))
            lo = hi = peak
            while lo > 0 and want[lo - 1] >= want[peak] - floor_db:
                lo -= 1
            while hi < len(want) - 1 and want[hi + 1] >= want[peak] - floor_db:
                hi += 1
            keep = np.zeros(len(want), bool)
            keep[lo:hi + 1] = True
        if not keep.any():
            rows.append({"sum": code, "members": members, "band_hz": None, "bands": 0, "rms_db": None, "max_db": None, "flagged": False, "why": "no 1/3-oct band in its band"})
            continue
        err = (have - want)[keep]
        rows.append({"sum": code, "members": members, "band_hz": [round(float(centres[keep][0]), 1), round(float(centres[keep][-1]), 1)], "bands": int(keep.sum()),
                     "rms_db": round(float(np.sqrt(np.mean(err ** 2))), 3), "max_db": round(float(np.max(np.abs(err))), 3), "flagged": False})
    return rows


def round_doc(loader, glossary, freqs, th):
    cache = {}

    def load(code):
        if code not in cache:
            cache[code] = loader(code)
        return cache[code]

    groups = {}
    for section in (glossary.pairs, glossary.sides, glossary.joints, glossary.combos):
        groups.update({k: list(v) for k, v in section.items() if isinstance(v, (list, tuple))})
    unknown = sorted(set(th["sum_band"]) - set(groups))
    if unknown:
        raise VersionBenchError(f"--sum-band {', '.join(unknown)}: not a sum of the project's glossary (it has {', '.join(sorted(groups)) or 'none'})")
    sums, not_checked = {}, []
    for code, members in groups.items():
        measured = load(code)
        if measured is None:
            continue
        missing = [m for m in members if load(m) is None]
        if missing:
            not_checked.append(f"{code}: its solo(s) {', '.join(missing)} were not found in this round")
            continue
        sums[code] = (measured, members, sum(load(m) for m in members))
    if not sums and not not_checked:
        raise VersionBenchError("no tripod sum of the project's glossary was found in this round: nothing to check")
    rows = _sum_rows(freqs, sums, th["sum_band"], th["floor_db"])
    for r in rows:
        r["flagged"] = bool(r["rms_db"] is not None and r["rms_db"] > th["flag_rms_db"])
    default = None
    if th["flag_rms_db"] != ROUND_FLAG_RMS_DB or th["floor_db"] != ROUND_FLOOR_DB:
        base = _sum_rows(freqs, sums, th["sum_band"], ROUND_FLOOR_DB)
        default = {"flag_rms_db": ROUND_FLAG_RMS_DB, "floor_db": ROUND_FLOOR_DB,
                   "flagged": [r["sum"] for r in base if r["rms_db"] is not None and r["rms_db"] > ROUND_FLAG_RMS_DB]}
    return {"rows": rows, "flag_rms_db": th["flag_rms_db"], "floor_db": th["floor_db"], "words": ROUND_THRESHOLD_WORDS, "not_checked": not_checked, "default": default}


def render_round(doc):
    lines = ["  each tripod sum against the complex sum of its solos, 1/3-oct bands, no offset removed:",
             f"  {'sum':16}{'band Hz':>16}{'bands':>7}{'rms dB':>9}{'max dB':>9}"]
    for r in doc["rows"]:
        band = f"{r['band_hz'][0]:g}-{r['band_hz'][1]:g}" if r["band_hz"] else "--"
        lines.append(f"  {r['sum'][:16]:16}{band:>16}{r['bands']:>7}"
                     f"{('--' if r['rms_db'] is None else format(r['rms_db'], '.2f')):>9}{('--' if r['max_db'] is None else format(r['max_db'], '.2f')):>9}"
                     + ("  FLAG" if r["flagged"] else "") + (f"  {r['why']}" if r.get("why") else ""))
    flagged = [r["sum"] for r in doc["rows"] if r["flagged"]]
    lines.append(f"  over {doc['flag_rms_db']:g} dB rms: {', '.join(flagged) or 'none'} -- {doc['words']}")
    if doc["default"]:
        lines.append(f"  changed from the default; at the default {doc['default']['flag_rms_db']:g} dB rms and {doc['default']['floor_db']:g} dB floor it would flag: "
                     f"{', '.join(doc['default']['flagged']) or 'none'}")
    lines += [f"  not checked: {w}" for w in doc["not_checked"]]
    lines.append("  Reads a round; nothing is entered from here.")
    return "\n".join(lines)


# ---------------------------------------------------------------- the table
def _width_oct(f, a, b, fx, window_deg, span_oct=None):
    """The ±band's width through the acoustic crossing, octaves: 0 if the crossing itself is outside it. The walk stops `span_oct` either side, where one
    driver has left the sum and its phase says nothing."""
    span_oct = WIDTH_SPAN_OCT if span_oct is None else span_oct
    dp = np.degrees(np.angle(a * np.conj(b)))
    i = int(np.argmin(np.abs(f - fx)))
    if abs(dp[i]) > window_deg:
        return 0.0
    floor, ceil = fx / 2.0 ** span_oct, fx * 2.0 ** span_oct
    lo = hi = i
    while lo > 0 and f[lo - 1] >= floor and abs(dp[lo - 1]) <= window_deg:
        lo -= 1
    while hi < len(f) - 1 and f[hi + 1] <= ceil and abs(dp[hi + 1]) <= window_deg:
        hi += 1
    return math.log2(f[hi] / f[lo])


def _crossing(f, a, b, fc):
    """Where the two levels cross nearest the ledger's corner, inside an octave of it; the corner when they do not."""
    span = np.flatnonzero((f >= fc / 2.0) & (f <= fc * 2.0))
    if span.size < 2:
        return float(fc)
    d = 20.0 * np.log10(np.maximum(np.abs(a[span]), 1e-12)) - 20.0 * np.log10(np.maximum(np.abs(b[span]), 1e-12))
    cross = span[np.flatnonzero(np.signbit(d[:-1]) != np.signbit(d[1:]))]
    return float(f[cross[np.argmin(np.abs(np.log(f[cross] / fc)))]]) if cross.size else float(fc)


def _joints_of(chains, curves):
    """`predict`'s joints on the playing channels as members, a sub's joint read against the summed L+R of the next role: `[(label, lower, upper, fc)]`."""
    live = [c for c in _playing(chains) if curves[c]["tripod"] is not None or curves[c]["points"]]
    subs = [c for c in live if P._is_sub(c)]
    out, seen = [], set()
    for lo, hi, fc in P.joints_from_chains({c: chains[c] for c in live}):
        lower = subs if lo == P.SUB_GROUP else [lo]
        if P._is_sub(lo) or lo == P.SUB_GROUP:
            role = hi.split("-")[0]
            upper = [c for c in live if c.split("-")[0] == role and not P._is_sub(c)]
            key = (lo, role)
        else:
            upper = [hi]
            key = (lo, hi)
        if key in seen:
            continue
        seen.add(key)
        out.append((f"{'+'.join(lower)} ↔ {'+'.join(upper)}", lower, upper, fc))
    return out


def _at_points(f, curves, chains, codes, points):
    rows = [_chain_sum(f, curves, chains, codes, p) for p in points]
    return None if any(r is None for r in rows) else np.array(rows)


def _ear_numbers(lower, upper, points, band_mask):
    """The power sum 10 log10(|a+b|^2 / (|a|^2+|b|^2)) over the band: nine points, and each ear group that has two points."""
    def over(idx):
        a, b = lower[idx][:, band_mask], upper[idx][:, band_mask]
        return float(10.0 * np.log10(np.sum(np.abs(a + b) ** 2) / max(np.sum(np.abs(a) ** 2 + np.abs(b) ** 2), 1e-30)))
    index = {p: i for i, p in enumerate(points)}
    groups = {}
    for name, members in JS.EAR_GROUPS.items():
        have = [index[p] for p in members if p in index]
        groups[name] = round(over(have), 2) if len(have) >= 2 else None
    known = [v for v in groups.values() if v is not None]
    return {"nine_db": round(over(list(range(len(points)))), 2), "groups_db": groups, "robust_db": min(known) if known else None}


def _decay_row(label, lower_code, upper_code, table, fx, ratio):
    """A joint's two raw drivers: the ring times where the lower rings longest relative to the upper, and the band where it rings `ratio` times longer."""
    freqs = table["freqs_hz"]
    span = [i for i, x in enumerate(freqs) if fx / 2.5 <= x <= fx * 2.5]
    lo, up = table["ms"][lower_code], table["ms"][upper_code]
    usable = [i for i in span if lo[i] is not None and up[i] is not None and up[i] > 0]
    if not usable:
        return {"joint": label, "at_hz": None, "lower_ms": None, "upper_ms": None, "ratio": None, "ring": None}
    i = max(usable, key=lambda k: lo[k] / up[k])
    ring = JS.ring_band([lo[k] for k in span], [up[k] for k in span], [freqs[k] for k in span], ratio)
    return {"joint": label, "at_hz": round(freqs[i], 1), "lower_ms": round(lo[i], 1), "upper_ms": round(up[i], 1), "ratio": round(lo[i] / up[i], 2),
            "ring": None if ring is None else [round(ring["band"][0], 1), round(ring["band"][1], 1)]}


def _beside(version, f, curves, load_short, points, decay, th):
    """The metrics shown beside the four terms. They take no part in the picks; what cannot be computed comes back in words."""
    chains = version["chains"]
    label = version["label"]
    widths, ears, decays, shares, cannot = [], [], [], [], []
    for joint, lower, upper, fc in _joints_of(chains, curves):
        pts = [p for p in points if all(p in curves[c]["points"] or P._is_sub(c) for c in lower + upper)]
        if not pts:
            cannot.append(f"{label}: joint widths of {joint}: no points shared by its channels (the widths are read over the points)")
            continue
        a, b = _at_points(f, curves, chains, lower, pts), _at_points(f, curves, chains, upper, pts)
        fxs = [_crossing(f, a[i], b[i], fc) for i in range(len(pts))]
        fx = float(np.median(fxs))
        if fx < JS.CLASS_SPLIT_HZ:
            w = [_width_oct(f, a[i], b[i], fxs[i], th["phase_window_deg"], th["width_span_oct"]) for i in range(len(pts))]
            widths.append({"joint": joint, "fx_hz": round(fx, 1), "worst_oct": round(min(w), 2), "median_oct": round(float(np.median(w)), 2), "points": len(pts)})
            if decay is None:
                cannot.append(f"{label}: decay of {joint}: no impulse to read it from")
                continue
            row = _decay_row(joint, lower[0], upper[0], decay, fx, th["ring_ratio"])
            decays.append(row)
            if row["ring"] is None:
                shares.append({"joint": joint, "band_hz": None, "share_db": None,
                               "why": f"no band where the lower driver rings {th['ring_ratio']:g} times longer than the upper"})
                cannot.append(f"{label}: share of {joint}: {shares[-1]['why']}")
            else:
                band = tuple(row["ring"])
                shares.append({"joint": joint, "band_hz": list(band), "share_db": round(JS._lower_share(f, a, b, band), 1), "why": None})
        else:
            short = load_short()
            sa, sb = _at_points(f, short, chains, lower, pts), _at_points(f, short, chains, upper, pts)
            if sa is None or sb is None:
                cannot.append(f"{label}: ear sums of {joint}: the short window could not read its channels at the points")
                continue
            ears.append(dict({"joint": joint, "fx_hz": round(fx, 1)}, **_ear_numbers(sa, sb, pts, (f >= fx / math.sqrt(2.0)) & (f <= fx * math.sqrt(2.0)))))
    lr = _lr_row(version, f, curves, LR_BAND_HZ)
    if lr["acoustic"] is None:
        cannot.append(f"{label}: L/R phase: {lr['why']}")
    return {"joint_widths": widths, "ear_sums": ears, "decay": decays, "share": shares, "lr_phase": lr}, cannot


def table_doc(versions, freqs, curves, load_short, target, th):
    f = np.asarray(freqs, float)
    points = [p for p in JS.POSITIONS if any(p in ch["points"] for ch in curves.values())]
    live = sorted({c for v in versions for c in _playing(v["chains"]) if curves[c]["tripod"] is not None or curves[c]["points"]})
    centres = [round(float(c), 1) for c in _third_bands(f)[0] if 50.0 <= c <= 2500.0]
    decay = JS.decay_table(curves, live, centres) if live else None
    rows, cannot = [], []
    notes = [n for v in versions for n in v["notes"]]
    for v in versions:
        solos = {c: curves[c]["tripod"] for c in _playing(v["chains"]) if curves[c]["tripod"] is not None}
        pred = P.predict(f, solos, {c: v["chains"][c] for c in solos})
        terms = VF.terms(P.to_json(pred), target)
        beside, why = _beside(v, f, curves, load_short, points, decay, th)
        cannot += why
        rows.append({"version": v["label"], "terms": terms, "beside": beside, "predict_notes": pred["notes"][:5]})
    missing = {t: [r["version"] for r in rows if r["terms"].get(t) is None] for t in VF.TERMS}
    missing = {t: names for t, names in missing.items() if names}
    usable = [t for t in VF.TERMS if t not in missing]
    changed, default_beside = [], None
    defaults = {"phase_window_deg": JS.PHASE_WINDOW_DEG, "width_span_oct": WIDTH_SPAN_OCT, "ring_ratio": JS.RING_RATIO}
    if any(th[k] != v for k, v in defaults.items()):
        changed = [f"{k} {th[k]:g} (default {v:g})" for k, v in defaults.items() if th[k] != v]
        base = dict(th, **defaults)
        default_beside = {}
        for v in versions:
            b = _beside(v, f, curves, load_short, points, decay, base)[0]
            default_beside[v["label"]] = {"joint_widths": b["joint_widths"], "decay": b["decay"], "share": b["share"]}
    front, no_pick = None, None
    if len(usable) >= 2:
        front = VF.front([{"name": r["version"], "terms": r["terms"]} for r in rows])
    else:
        said = "; ".join(f"{t} (missing for {', '.join(names)})" for t, names in missing.items())
        no_pick = f"no pick: {len(usable)} comparable term(s) ({', '.join(usable) or 'none'}), a pick needs two; {said}"
    return {"rows": rows, "front": front, "missing": missing, "no_pick": no_pick, "not_computed": list(dict.fromkeys(cannot)), "notes": notes, "purpose": th.get("purpose"),
            "changed": changed, "default_beside": default_beside}


def _fmt(v, spec=".2f"):
    return "--" if v is None else format(v, spec)


def render_table(doc):
    lines = ["  VERSIONS SIDE BY SIDE -- the four terms of `variant_front`, then what stands beside them; the versions in the order given",
             f"  {'version':24}{'tonal rms':>10}{'stage |L-R|':>13}{'junction loss':>15}{'ripple':>8}"]
    for r in doc["rows"]:
        t = r["terms"]
        lines.append(f"  {r['version'][:24]:24}{_fmt(t.get('tonal')):>10}{_fmt(t.get('stage')):>13}{_fmt(t.get('junctions'), '+.2f'):>15}{_fmt(t.get('ripple')):>8}")
    lines.append("  beside them, taking no part in the picks:")
    for r in doc["rows"]:
        b = r["beside"]
        lines.append(f"  {r['version']}:")
        for w in b["joint_widths"]:
            lines.append(f"    joint width {w['joint']}: {w['worst_oct']:.2f} / {w['median_oct']:.2f} oct (worst / median of {w['points']} points, crossing {w['fx_hz']:.0f} Hz)")
        for e in b["ear_sums"]:
            g = e["groups_db"]
            lines.append(f"    ear sums {e['joint']}: nine {e['nine_db']:+.2f} dB, left {_fmt(g['left'], '+.2f')}, right {_fmt(g['right'], '+.2f')}, centre {_fmt(g['centre'], '+.2f')} (crossing {e['fx_hz']:.0f} Hz)")
        for d in b["decay"]:
            if d["at_hz"] is not None:
                lines.append(f"    decay {d['joint']}: lower {d['lower_ms']:.0f} ms against upper {d['upper_ms']:.0f} ms at {d['at_hz']:.0f} Hz (x{d['ratio']:.1f})")
        for s in b["share"]:
            if s["share_db"] is not None:
                lines.append(f"    the lower driver's share {s['joint']}: {s['share_db']:+.1f} dB over {s['band_hz'][0]:.0f}-{s['band_hz'][1]:.0f} Hz")
        a = (b["lr_phase"] or {}).get("acoustic")
        if a and (a["nine"] or a["centre"]):
            read = a["nine"] or a["centre"]
            e = b["lr_phase"]["electrical"]
            lines.append(f"    L/R phase 250-800 Hz: {read['dphi_deg']:.1f} deg, {read['dgd_ms']:+.2f} ms ({len(read['points'])} point(s)); electrical {e['dphi_deg']:.1f} deg, {e['dgd_ms']:+.2f} ms")
    if doc["changed"]:
        lines.append("  changed from the default: " + "; ".join(doc["changed"]) + ". At the defaults:")
        for label, b in doc["default_beside"].items():
            for w in b["joint_widths"]:
                lines.append(f"    {label}: joint width {w['joint']}: {w['worst_oct']:.2f} / {w['median_oct']:.2f} oct (worst / median)")
            for s in b["share"]:
                if s["share_db"] is not None:
                    lines.append(f"    {label}: the lower driver's share {s['joint']}: {s['share_db']:+.1f} dB over {s['band_hz'][0]:.0f}-{s['band_hz'][1]:.0f} Hz")
    for t, names in doc["missing"].items():
        lines.append(f"  term missing: {t} for {', '.join(names)}")
    lines += [f"  cannot be computed: {w}" for w in doc["not_computed"]]
    if doc["front"]:
        lines.append(VF.render(doc["front"], doc.get("purpose")))
    else:
        lines.append(f"  {doc['no_pick']}")
        lines.append("  The tuner chooses; nothing is entered without the tuner's OK.")
    lines += _notes_lines(doc["notes"])
    return "\n".join(lines)


# ---------------------------------------------------------------- the command line
def _band(spec, label):
    try:
        lo, hi = (float(x) for x in spec.split(":"))
    except ValueError:
        raise VersionBenchError(f"{label} {spec!r}: LO:HI in Hz") from None
    if not (0.0 < lo < hi):
        raise VersionBenchError(f"{label} {spec!r}: LO:HI in Hz, LO under HI")
    return (lo, hi)


def _bind_rate(project_dir):
    """The model on this device's rate, the profile read once and strictly (`xover_candidates`'s order)."""
    path = dsp_profile.profile_path(project_dir)
    try:
        prof = dsp_profile.load_profile(path)
    except FileNotFoundError:
        prof = None
    _rate, note = dsp_profile.bind_model_rate(prof if prof is not None else project_dir, path=path)
    if note:
        print(f"  ⚠ {note}", file=sys.stderr)


def _common(sub):
    sub.add_argument("--project", required=True, metavar="DIR")
    sub.add_argument("--solos", metavar="DIR", help="v7 impulse files, `m_L.json` and `m_L-p1.json`")
    sub.add_argument("--rew", action="store_true", help="read live REW: --ver N is the series")
    sub.add_argument("--ver", help="series number for --rew")
    sub.add_argument("--json", action="store_true")


def _parser():
    import argparse
    ap = argparse.ArgumentParser(description="whole ledger versions side by side, whichever path built them")
    sp = ap.add_subparsers(dest="cmd")
    table = sp.add_parser("table", help="the front's picks on its four terms, the other metrics beside them")
    _common(table)
    table.add_argument("--house", metavar="FILE", help="the target curve (REW text); without it the tonal term is missing, named")
    table.add_argument("--route", action="append", default=[], metavar="VIRTUAL=out1,out2")
    table.add_argument("--phase-window", dest="phase_window_deg", type=float, default=JS.PHASE_WINDOW_DEG, metavar="DEG",
                       help=f"the ±band of the joint widths (default {JS.PHASE_WINDOW_DEG:g})")
    table.add_argument("--width-span", dest="width_span_oct", type=float, default=WIDTH_SPAN_OCT, metavar="OCT",
                       help=f"how far the joint width's walk goes either side of the crossing (default {WIDTH_SPAN_OCT:g})")
    table.add_argument("--ring-ratio", dest="ring_ratio", type=float, default=JS.RING_RATIO, metavar="X",
                       help=f"the lower driver ringing this many times longer names the share's band (default {JS.RING_RATIO:g})")
    table.add_argument("versions", nargs="+", metavar="VERSION")
    loud = sp.add_parser("loudness", help="the versions matched in loudness")
    _common(loud)
    loud.add_argument("--route", action="append", default=[], metavar="VIRTUAL=out1,out2")
    loud.add_argument("--phon", type=float, default=ISO_PHON, help=f"ISO 226 contour (default {ISO_PHON:g})")
    loud.add_argument("--level-db", dest="level_db", type=float, nargs="+", default=list(ZWICKER_LEVELS_DBC), metavar="DB",
                      help="Zwicker: the reference version's level, dB(C) (default " + " ".join(f"{x:g}" for x in ZWICKER_LEVELS_DBC) + ")")
    loud.add_argument("--field", choices=ZWICKER_FIELDS, help="Zwicker: one sound field (default both)")
    loud.add_argument("--bass-band", dest="bass_band", default=None, metavar="LO:HI",
                      help=f"where the versions are compared in the bass (default {BASS_BAND_HZ[0]:g}:{BASS_BAND_HZ[1]:g})")
    loud.add_argument("--bass-differs-db", dest="bass_differs_db", type=float, default=BASS_DIFFERS_DB, metavar="DB",
                      help=f"the bass against the rest changing by this much reads as a difference (default {BASS_DIFFERS_DB:g})")
    loud.add_argument("--gain-span", dest="gain_span_db", type=float, default=GAIN_SPAN_DB, metavar="DB",
                      help=f"Zwicker: the bisection's reach either way (default {GAIN_SPAN_DB:g})")
    loud.add_argument("versions", nargs="+", metavar="VERSION")
    lrp = sp.add_parser("lr-phase", help="L against R: phase and group-delay difference")
    _common(lrp)
    lrp.add_argument("--route", action="append", default=[], metavar="VIRTUAL=out1,out2")
    lrp.add_argument("--band", default=None, metavar="LO:HI", help=f"default {LR_BAND_HZ[0]:g}:{LR_BAND_HZ[1]:g}")
    lrp.add_argument("versions", nargs="+", metavar="VERSION")
    rnd = sp.add_parser("round-check", help="each tripod sum against the complex sum of its solos")
    _common(rnd)
    rnd.add_argument("--flag-rms-db", dest="flag_rms_db", type=float, default=ROUND_FLAG_RMS_DB, metavar="DB",
                     help=f"flag a sum over this rms: a working threshold (default {ROUND_FLAG_RMS_DB:g})")
    rnd.add_argument("--floor-db", dest="floor_db", type=float, default=ROUND_FLOOR_DB, metavar="DB",
                     help=f"a sum's band: the 1/3-oct bands within this of its loudest (default {ROUND_FLOOR_DB:g})")
    rnd.add_argument("--sum-band", dest="sum_band", action="append", default=[], metavar="CODE=LO:HI", help="one sum's band, by hand")
    return ap


def _round_loader(args, freqs, api=None):
    """`code -> H or None`, the tripod reading of a channel or a sum: whole record, no window, nothing de-embedded (one series, one state)."""
    if bool(args.solos) == bool(args.rew):
        raise VersionBenchError("say where the curves are: --solos DIR, or --rew --ver N")
    if args.solos:
        def load(code):
            path = os.path.join(args.solos, code.replace(" ", "_").replace("-", "_") + ".json")
            return P.load_solo_v7(path, freqs)[0] if os.path.isfile(path) else None
        return load
    if not args.ver:
        raise VersionBenchError("--rew needs --ver N, the series")
    if api is None:
        import rew_api as api  # noqa: F811
    have = {(m or {}).get("title") for m in api.get_measurements().values()}

    def load_rew(code):
        title = naming.generate_name(code, args.ver, "sw")
        return P.load_solo_rew(title, freqs, api=api)[0] if title in have else None
    return load_rew


def _cli(argv=None):
    """`_main`'s work; its refusals are `_main`'s to say."""
    args = _parser().parse_args(argv)
    if not args.cmd:
        raise VersionBenchError("a subcommand: table, loudness, lr-phase or round-check")
    _bind_rate(args.project)
    freqs = P.grid(*GRID)
    if args.cmd == "round-check":
        loader = _round_loader(args, freqs)
        glossary = naming.Glossary.for_project(args.project, strict=True)
        doc = round_doc(loader, glossary, freqs, {"flag_rms_db": args.flag_rms_db, "floor_db": args.floor_db,
                                                  "sum_band": dict(_sum_band(s) for s in args.sum_band)})
        print(_dumps(doc) if args.json else render_round(doc))
        return 0
    if args.cmd in ("table", "loudness") and len(args.versions) < 2:
        raise VersionBenchError(f"{args.cmd} compares versions: give at least two, got {len(args.versions)}")
    versions = load_versions(args.project, args.versions, args.route)
    codes = {c for v in versions for c in _playing(v["chains"])}
    curves, load_notes = _load_curves(args, codes, freqs)
    points = check_coverage(versions, curves)
    if args.cmd == "lr-phase":
        doc = lr_doc(versions, freqs, curves, _band(args.band, "--band") if args.band else LR_BAND_HZ)
        doc["notes"] = load_notes + doc["notes"]
        print(_dumps(doc) if args.json else render_lr(doc))
        return 0
    if args.cmd == "loudness":
        th = {"phon": args.phon, "levels": list(args.level_db), "fields": (args.field,) if args.field else ZWICKER_FIELDS,
              "bass_band": _band(args.bass_band, "--bass-band") if args.bass_band else BASS_BAND_HZ,
              "bass_differs_db": args.bass_differs_db, "gain_span_db": args.gain_span_db}
        doc = loudness_doc(versions, freqs, curves, points, th)
        doc["notes"] = load_notes + doc["notes"]
        print(_dumps(doc) if args.json else render_loudness(doc))
        return 0
    target = VF.read_target(args.house) if args.house else None
    held = {}

    def load_short():
        if "short" not in held:
            held["short"] = _load_curves(args, codes, freqs, short=True)[0]
        return held["short"]

    purpose = _pj.fact_value((_pj.Project(args.project).load().get("goal") or {}).get("purpose"))
    th = {"phase_window_deg": args.phase_window_deg, "width_span_oct": args.width_span_oct, "ring_ratio": args.ring_ratio, "purpose": purpose}
    doc = table_doc(versions, freqs, curves, load_short, target, th)
    doc["notes"] = load_notes + doc["notes"]
    print(_dumps(doc) if args.json else render_table(doc))
    return 0


def _sum_band(spec):
    code, _, band = spec.partition("=")
    if not code.strip() or not band:
        raise VersionBenchError(f"--sum-band {spec!r}: CODE=LO:HI")
    return code.strip(), _band(band, "--sum-band")


def _main(argv=None):
    """The command line. Every refusal is one line, `refusing: <why>`, exit 3: this tool's, predict's, joint_search's, REW's own and an
    unreadable profile's."""
    try:
        return _cli(argv)
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
        if getattr(type(exc), "rew_state", None) is not None:
            print(f"refusing: REW: {exc.args[0] if exc.args else exc}", file=sys.stderr)
            return 3
        if not (getattr(type(exc), "is_refusal", False) or getattr(type(exc), "is_unreadable", False)):
            raise
        print(f"refusing: {exc}", file=sys.stderr)
        return 3


# ---------------------------------------------------------------- selftests
_FX = {}


def _top():
    """The shared throwaway folder, made once: `_selftest` removes it."""
    import tempfile
    if "top" not in _FX:
        _FX["top"] = tempfile.mkdtemp(prefix=_TMP_PREFIX)
    return _FX["top"]


def _write_ir(path, x, fs=48000):
    import resonalyze_ir as ri
    doc = ri.build_v7(np.asarray(x, float), fs, 0.0, low_hz=20.0, high_hz=20000.0)
    ri.write_v7(doc[0] if isinstance(doc, tuple) else doc, path)


def _impulse(at, level=0.5, n=1 << 13):
    x = np.zeros(n)
    x[at] = level
    return x


def _row(hp, lp, **extra):
    leg = lambda f: {"f": f, "type": "LR", "slope": 24} if f else None  # noqa: E731
    row = {"hp": leg(hp), "lp": leg(lp), "gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM", "eq": []}
    row.update(extra)
    return row


def _snapshot_of(channels, **extra):
    return dict({"schema_version": 3, "preset": "SQ", "sample_rate": 96000, "channels": channels}, **extra)


def _project_on_disk(name, ledger, irs, glossary=None):
    """`(project, solos)` of a small project under the shared throwaway folder: `ledger` is `{preset: [snapshot, ...]}` (first preset active)
    and `irs` is `{file stem: samples}`."""
    state_dir = os.path.join(_HERE, "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import state as st
    proj = os.path.join(_top(), name, "project")
    solos = os.path.join(_top(), name, "solos")
    os.makedirs(proj)
    os.makedirs(solos)
    pj = _pj.Project(proj)
    data = pj.load()
    if glossary:
        data["glossary"] = glossary
    pj.save(data)
    root = os.path.join(proj, "state")
    for i, (preset, snaps) in enumerate(ledger.items()):
        history = st.PresetHistory(root, preset, project_dir=proj)
        for snap in snaps:
            history.snapshot(dict(snap, preset=preset), note="a planted version")
        if i == 0:
            st.Registry(root).set_active(preset)
    for stem, x in irs.items():
        _write_ir(os.path.join(solos, stem + ".json"), x)
    return proj, solos


#: The main fixture's stack, its six fronts on the tripod and the nine points, the sub and a centre on the tripod only.
_FRONTS = ("w-L", "w-R", "m-L", "m-R", "tw-L", "tw-R")


def _base_channels():
    return {"sw": _row(None, 80), "w-L": _row(80, 400), "w-R": _row(80, 400), "m-L": _row(400, 3000), "m-R": _row(400, 3000),
            "tw-L": _row(3000, None), "tw-R": _row(3000, None), "c": _row(400, 3000, mute=True)}


def _fx():
    """The shared throwaway project, built once: `_selftest` removes it."""
    if _FX.get("main"):
        return _FX
    base = _base_channels()
    both = {code: dict(row, gain_db=6.0) for code, row in base.items()}
    no_lp = {code: dict(row, lp=None) for code, row in base.items()}
    wide = {code: dict(row, gain_db=-3.0 if code.endswith("-R") else 0.0) for code, row in base.items()}
    louder_sub = dict(base, sw=dict(base["sw"], gain_db=6.0))
    centre_on = dict(base, c=_row(400, 3000))
    a = [_snapshot_of(base), _snapshot_of(both), _snapshot_of(base, preset_settings={"input_gain_db": -6.0}), _snapshot_of(louder_sub),
         _snapshot_of(no_lp), _snapshot_of(centre_on), _snapshot_of(wide),
         _snapshot_of(base, virtual_channels={"VFL": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}}),
         _snapshot_of(base, preset_settings={"input_gain_db": -6.0},
                      virtual_channels={"VFL": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}})]
    irs = {"sw": _impulse(144), "c": _impulse(96)}
    for code in _FRONTS:
        stem = code.replace("-", "_")
        irs[stem] = _impulse(96)
        for pos in JS.POSITIONS:
            irs[f"{stem}-{pos}"] = _impulse(96)
    _FX["main"] = _project_on_disk("main", {"A": a}, irs)
    house = os.path.join(_top(), "house.txt")
    with open(house, "w", encoding="utf-8") as fh:
        fh.write("20 6\n1000 0\n20000 -3\n")
    _FX["house"] = house
    return _FX


def _run(argv):
    """`(rc, stdout, stderr)` of `_main`; a traceback is rc "raised <type>: <message>"."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _main(argv)
    except BaseException as exc:  # noqa: BLE001 -- a traceback is the failure under test
        rc = f"raised {type(exc).__name__}: {exc}"
    return rc, out.getvalue(), err.getvalue()


def _doc(argv):
    rc, out, err = _run(list(argv) + ["--json"])
    assert rc == 0, (rc, err[-800:], argv)
    return json.loads(out)


def _main_args(cmd):
    proj, solos = _fx()["main"]
    return [cmd, "--project", proj, "--solos", solos]


@contextlib.contextmanager
def _mosqito(mode, sones=None):
    """`mosqito` for one block: `"absent"` makes its import fail; `"standin"` plants a module whose loudness is a known law of the spectrum."""
    saved = {k: sys.modules.get(k) for k in ("mosqito", "mosqito.sq_metrics")}
    try:
        if mode == "absent":
            sys.modules["mosqito"] = None
            sys.modules["mosqito.sq_metrics"] = None
        else:
            import types
            top, sq = types.ModuleType("mosqito"), types.ModuleType("mosqito.sq_metrics")
            sq.loudness_zwst_freq = sones
            top.sq_metrics = sq
            sys.modules["mosqito"], sys.modules["mosqito.sq_metrics"] = top, sq
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def _stevens(spectrum, freqs, field_type="free"):
    """The stand-in's loudness: a power law of the total power, as sones grow with level, so a bisection on gain has one answer."""
    assert field_type in ZWICKER_FIELDS, field_type
    spec, fl = np.asarray(spectrum, float), np.asarray(freqs, float)
    assert spec.shape == fl.shape and np.all(np.isfinite(spec)) and fl[0] > 0, (spec.shape, fl.shape)
    return float(np.sum(spec ** 2) ** 0.3), np.zeros(240), np.arange(240) * 0.1


def _check_table_picks_are_the_fronts():
    """`table` on planted versions: the versions in their own order, each with the four terms from `variant_front.terms`; the picks are exactly
    `variant_front.front` over those terms, no argmax; the other metrics stand beside and are not in the terms."""
    fx = _fx()
    doc = _doc(_main_args("table") + ["--house", fx["house"], "A/v_001", "A/v_007"])
    assert [r["version"] for r in doc["rows"]] == ["A/v_001", "A/v_007"], doc["rows"]
    for row in doc["rows"]:
        assert all(row["terms"].get(t) is not None for t in VF.TERMS), row["terms"]
        for key in ("joint_widths", "ear_sums", "decay", "share", "lr_phase"):
            assert key in row["beside"], (key, row["beside"].keys())
            assert key not in row["terms"], key
    cands = [{"name": r["version"], "terms": r["terms"]} for r in doc["rows"]]
    expect = VF.front(cands)
    assert [p["name"] for p in doc["front"]["picks"]] == [p["name"] for p in expect["picks"]], doc["front"]
    assert doc["no_pick"] is None and doc["front"]["missing"] == [], doc["front"]
    # the wide version loses the stage term by construction: 3 dB between the sides, the mono sub's bands diluting the mean
    assert doc["rows"][1]["terms"]["stage"] > doc["rows"][0]["terms"]["stage"] + 2.0, [r["terms"]["stage"] for r in doc["rows"]]
    rc, text, _err = _run(_main_args("table") + ["--house", fx["house"], "A/v_001", "A/v_007"])
    assert rc == 0 and "A/v_001" in text and "A/v_007" in text and "joint" in text.lower() and VF.CANNOT_SEE in text, text[-900:]
    assert "The tuner chooses" in text, text[-400:]


def _check_table_names_a_missing_term():
    """A term missing for one version is named, with the version; the picks stand on the terms all share, and under two comparable terms there is no pick."""
    fx = _fx()
    doc = _doc(_main_args("table") + ["--house", fx["house"], "A/v_001", "A/v_005"])
    assert doc["missing"].get("junctions") == ["A/v_005"] and doc["missing"].get("ripple") == ["A/v_005"], doc["missing"]
    assert doc["front"]["missing"] == ["junctions", "ripple"] and doc["front"]["picks"], doc["front"]
    assert doc["no_pick"] is None, doc["no_pick"]
    rc, text, _e = _run(_main_args("table") + ["--house", fx["house"], "A/v_001", "A/v_005"])
    assert rc == 0 and "junctions" in text and "A/v_005" in text, text[-700:]
    # no target: tonal is missing for both; junctions and ripple for one: one comparable term, no pick
    doc = _doc(_main_args("table") + ["A/v_001", "A/v_005"])
    assert doc["front"] is None or not doc["front"].get("picks"), doc["front"]
    assert doc["no_pick"] and "stage" in doc["no_pick"] and "tonal" in doc["no_pick"] and "junctions" in doc["no_pick"], doc["no_pick"]
    rc, text, _e = _run(_main_args("table") + ["A/v_001", "A/v_005"])
    assert rc == 0 and "no pick" in text and "tonal" in text and "wins under" not in text, text[-700:]


def _check_table_beside_metrics():
    """The joint widths come from the nine points, a width under 1 kHz and ear sums from 1 kHz up; decay and share from the impulse; what cannot be computed is named."""
    fx = _fx()
    doc = _doc(_main_args("table") + ["--house", fx["house"], "A/v_001", "A/v_002"])
    beside = doc["rows"][0]["beside"]
    widths = {j["joint"]: j for j in beside["joint_widths"]}
    assert "sw ↔ w-L+w-R" in widths and "w-L ↔ m-L" in widths, list(widths)
    assert widths["sw ↔ w-L+w-R"]["worst_oct"] is not None and widths["w-L ↔ m-L"]["worst_oct"] is not None, widths
    ears = {j["joint"]: j for j in beside["ear_sums"]}
    assert set(ears) == {"m-L ↔ tw-L", "m-R ↔ tw-R"}, list(ears)
    assert ears["m-L ↔ tw-L"]["nine_db"] is not None and {"left", "right", "centre"} <= set(ears["m-L ↔ tw-L"]["groups_db"]), ears
    assert beside["share"] and all("no band" in s["why"] for s in beside["share"]), beside["share"]
    assert any("share" in w for w in doc["not_computed"]), doc["not_computed"]
    assert beside["lr_phase"]["acoustic"]["nine"]["dphi_deg"] < 1.0, beside["lr_phase"]
    # a planted long ring in the woofers: the share is read over the band where they ring
    t = np.arange(1 << 13) / 48000.0
    ring = 0.4 * np.exp(-t / 0.06) * np.sin(2 * np.pi * 250.0 * t)
    irs = {}
    for code in ("w-L", "m-L"):
        stem = code.replace("-", "_")
        x = _impulse(96) + (ring if code == "w-L" else 0.0)
        irs[stem] = x
        for pos in JS.POSITIONS:
            irs[f"{stem}-{pos}"] = x
    chans = {"w-L": _row(None, 400), "m-L": _row(400, None)}
    proj, solos = _project_on_disk("ringing", {"R": [_snapshot_of(chans), _snapshot_of({k: dict(v, gain_db=-1.0) for k, v in chans.items()})]}, irs)
    doc = _doc(["table", "--project", proj, "--solos", solos, "R/v_001", "R/v_002"])
    assert any("L/R phase" in w and "both sides" in w for w in doc["not_computed"]), doc["not_computed"]
    share = doc["rows"][0]["beside"]["share"]
    assert share and share[0]["share_db"] is not None and share[0]["band_hz"][0] < 400.0, share
    assert doc["rows"][0]["beside"]["decay"][0]["lower_ms"] > 1.5 * doc["rows"][0]["beside"]["decay"][0]["upper_ms"], doc["rows"][0]["beside"]["decay"]
    # an LR pair on identical drivers at one arrival is in phase across the joint: a full-width reading, bounded by the span
    proj, solos = _lr_project()
    doc = _doc(["table", "--project", proj, "--solos", solos, "S/v_001", "S/v_002"])
    width = {j["joint"]: j for j in doc["rows"][0]["beside"]["joint_widths"]}["w-L ↔ m-L"]
    assert 2.5 < width["worst_oct"] <= 2.0 * WIDTH_SPAN_OCT + 0.02, width
    narrow = _doc(["table", "--project", proj, "--solos", solos, "--width-span", "0.5", "S/v_001", "S/v_002"])
    assert {j["joint"]: j for j in narrow["rows"][0]["beside"]["joint_widths"]}["w-L ↔ m-L"]["worst_oct"] <= 1.02, narrow["rows"][0]["beside"]["joint_widths"]
    # tripod-only: widths and ear sums cannot be computed, named
    irs = {"w_L": _impulse(96), "m_L": _impulse(96)}
    proj, solos = _project_on_disk("tripodonly", {"T": [_snapshot_of(chans), _snapshot_of(chans)]}, irs)
    doc = _doc(["table", "--project", proj, "--solos", solos, "T/v_001", "T/v_002"])
    assert any("joint widths" in w and "points" in w for w in doc["not_computed"]), doc["not_computed"]


def _check_coverage_refused():
    """A version that plays a channel measured only at the tripod and one that does not: not compared, each said by what it has."""
    rc, out, err = _run(_main_args("table") + ["A/v_001", "A/v_006"])
    said = _refusal_lines(err)
    assert rc == 3 and not out.strip() and len(said) == 1 and said[0].startswith("refusing:"), (rc, err[-500:])
    assert "point coverage" in said[0] and "A/v_001" in said[0] and "A/v_006" in said[0] and "fewer points: c" in said[0], said
    for cmd in ("loudness", "lr-phase"):
        rc, _o, err = _run(_main_args(cmd) + ["A/v_001", "A/v_006"])
        assert rc == 3 and "point coverage" in err, (cmd, rc, err[-300:])


def _lr_project():
    """Same drivers L and R, the right side later by 0.5 ms at p1/p5/p9, by 0.1 ms at five of the side points; v_002 adds 0.25 ms on the left in the DSP."""
    if _FX.get("lr"):
        return _FX["lr"]
    late = {p: (24 if p in JS.CENTRE_POINTS or p == "p8" else 5) for p in JS.POSITIONS}
    irs = {}
    for code in ("w-L", "m-L", "w-R", "m-R"):
        stem = code.replace("-", "_")
        irs[stem] = _impulse(96 + (24 if code.endswith("R") else 0))
        for pos in JS.POSITIONS:
            irs[f"{stem}-{pos}"] = _impulse(96 + (late[pos] if code.endswith("R") else 0))
    chans = {"w-L": _row(None, 500), "w-R": _row(None, 500), "m-L": _row(500, None), "m-R": _row(500, None)}
    later = {k: dict(v, ta_ms=0.25 if k.endswith("L") else 0.0) for k, v in chans.items()}
    _FX["lr"] = _project_on_disk("lr", {"S": [_snapshot_of(chans), _snapshot_of(later)]}, irs)
    return _FX["lr"]


def _check_lr_phase_on_planted_differences():
    """L against R on planted arrivals: the group-delay difference is the planted time, centre and nine read apart, and the electrical part sees only the DSP's own."""
    proj, solos = _lr_project()
    doc = _doc(["lr-phase", "--project", proj, "--solos", solos, "S/v_001", "S/v_002"])
    one, two = doc["rows"]
    assert one["version"] == "S/v_001", one
    assert abs(one["acoustic"]["centre"]["dgd_ms"] + 0.5) < 0.03, one["acoustic"]
    assert abs(one["acoustic"]["nine"]["dgd_ms"] + 0.5) > 0.2, one["acoustic"]   # five of the nine points are 0.1 ms: the median moves
    assert abs(one["electrical"]["dgd_ms"]) < 0.01 and one["electrical"]["dphi_deg"] < 0.5, one["electrical"]
    assert abs(two["electrical"]["dgd_ms"] - 0.25) < 0.02, two["electrical"]
    assert abs(two["acoustic"]["centre"]["dgd_ms"] + 0.25) < 0.03, two["acoustic"]
    f = P.grid(*GRID)
    m = (f >= LR_BAND_HZ[0]) & (f <= LR_BAND_HZ[1])
    want = float(np.median(np.abs(np.degrees(np.angle(np.exp(2j * np.pi * f[m] * 0.5e-3))))))
    assert abs(one["acoustic"]["centre"]["dphi_deg"] - want) < 3.0, (one["acoustic"]["centre"], want)
    rc, text, _e = _run(["lr-phase", "--project", proj, "--solos", solos, "S/v_001"])
    assert rc == 0 and "acoustic" in text and "electrical" in text and "centre" in text and "nine" in text, text


def _round_project():
    if _FX.get("round"):
        return _FX["round"]
    a, b = _impulse(96, 0.4), _impulse(120, 0.3)
    irs = {"w_L": a, "m_L": b, "L_w+m": a + b, "w_R": a, "m_R": b, "R_w+m": (a + b) * 10.0 ** (2.0 / 20.0), "Xw+m": a}
    glossary = {"joints": {"L w+m": ["w-L", "m-L"], "R w+m": ["w-R", "m-R"], "Xw+m": ["w-L", "nope"]}}
    _FX["round"] = _project_on_disk("round", {"R": [_snapshot_of({"w-L": _row(None, 500)})]}, irs, glossary=glossary)
    return _FX["round"]


def _check_round_check_on_planted_sums():
    """A sum equal to its solos' complex sum reads 0; a sum planted 2 dB up reads 2 dB rms and maximum, no offset removed, and is flagged by the working threshold; a sum with a solo gone is named."""
    proj, solos = _round_project()
    doc = _doc(["round-check", "--project", proj, "--solos", solos])
    rows = {r["sum"]: r for r in doc["rows"]}
    assert set(rows) == {"L w+m", "R w+m"}, list(rows)
    assert rows["L w+m"]["rms_db"] < 0.02 and rows["L w+m"]["max_db"] < 0.05 and not rows["L w+m"]["flagged"], rows["L w+m"]
    assert abs(rows["R w+m"]["rms_db"] - 2.0) < 0.05 and abs(rows["R w+m"]["max_db"] - 2.0) < 0.05 and rows["R w+m"]["flagged"], rows["R w+m"]
    assert any("Xw+m" in w and "nope" in w for w in doc["not_checked"]), doc["not_checked"]
    assert doc["words"] == ROUND_THRESHOLD_WORDS, doc["words"]
    rc, text, _e = _run(["round-check", "--project", proj, "--solos", solos])
    assert rc == 0 and ROUND_THRESHOLD_WORDS in text and "over 1 dB" in text and "R w+m" in text, text
    # the flag changed: what the default would flag, beside it
    doc = _doc(["round-check", "--project", proj, "--solos", solos, "--flag-rms-db", "3"])
    rows = {r["sum"]: r for r in doc["rows"]}
    assert not rows["R w+m"]["flagged"] and doc["default"]["flagged"] == ["R w+m"] and doc["default"]["flag_rms_db"] == ROUND_FLAG_RMS_DB, doc["default"]
    rc, text, _e = _run(["round-check", "--project", proj, "--solos", solos, "--flag-rms-db", "3"])
    assert rc == 0 and "default" in text and "R w+m" in text, text
    # a band by hand
    doc = _doc(["round-check", "--project", proj, "--solos", solos, "--sum-band", "L w+m=200:400"])
    row = next(r for r in doc["rows"] if r["sum"] == "L w+m")
    assert row["band_hz"][0] >= 200.0 and row["band_hz"][1] <= 400.0 and row["bands"] <= 4, row
    # nothing to check at all is a refusal, not a pass
    bare, solos_bare = _project_on_disk("roundbare", {"B": [_snapshot_of({"w-L": _row(None, 500)})]}, {"w_L": _impulse(96)},
                                        glossary={"joints": {"L w+m": ["w-L", "m-L"]}})
    rc, _o, err = _run(["round-check", "--project", bare, "--solos", solos_bare])
    said = _refusal_lines(err)
    assert rc == 3 and len(said) == 1 and said[0].startswith("refusing:") and "sum" in said[0], (rc, err[-300:])


def _check_round_check_reads_rew_titles():
    """The live door of the round-check: the sum's title by `naming.generate_name`, the tripod reading through `predict.load_solo_rew`, on the loopback base."""
    class Fake:
        titles = ["L w+m_7 (sw)", "w-L_7 (sw)", "m-L_7 (sw)"]

        def get_measurements(self):
            return {str(i): {"title": t} for i, t in enumerate(self.titles)}

        def find_measurement_id(self, title):
            return self.titles.index(title)

        def get_timing(self, mid):
            return {"has_ir": True, "reference": "loopback", "offset_s": 0.0}

        def get_impulse_response(self, mid, normalised=False):
            x = _impulse(96, 0.3) + (_impulse(120, 0.1) if mid == 0 else 0.0)
            return np.arange(x.size) / 48000.0, x

    class Args:
        solos, rew, ver = None, True, "7"

    freqs = P.grid(*GRID)
    load = _round_loader(Args, freqs, api=Fake())
    assert load("no such") is None
    h = load("w-L")
    assert h is not None and h.shape == freqs.shape, h is None


def _loud(argv=()):
    return _doc(_main_args("loudness") + list(argv))


def _row_of(rows, label):
    return next(r for r in rows if r["version"] == label)


def _check_iso226_on_a_known_step():
    """The reference version reads 0, a version 6 dB up everywhere reads +6.00 and asks for -6.00 on its input; a coherent sum on the planted curves is exact."""
    with _mosqito("absent"):
        doc = _loud(["A/v_001", "A/v_002"])
    rows = doc["iso226"]["rows"]
    assert doc["reference"] == "A/v_001" and _row_of(rows, "A/v_001")["level_db"] == 0.0, rows
    assert abs(_row_of(rows, "A/v_002")["level_db"] - 6.0) < 0.01 and abs(_row_of(rows, "A/v_002")["match_gain_db"] + 6.0) < 0.01, rows
    assert doc["iso226"]["phon"] == ISO_PHON and doc["points"] == list(JS.POSITIONS), doc["points"]


def _check_install_line_and_label_when_absent():
    """Without mosqito: the install line (for this very interpreter), ISO 226, its standing label, and the bass marker only when the bass really moved."""
    with _mosqito("absent"):
        doc = _loud(["A/v_001", "A/v_002"])
        rc, text, _e = _run(_main_args("loudness") + ["A/v_001", "A/v_002"])
    assert doc["zwicker"] is None and doc["install_line"] and sys.executable in doc["install_line"] and "mosqito" in doc["install_line"], doc["install_line"]
    assert doc["iso226"]["label"] == ISO_LABEL and doc["iso226"]["bass_differs"] is False, doc["iso226"]
    assert rc == 0 and doc["install_line"] in text and ISO_LABEL in text and "differ in the bass here" not in text, text
    with _mosqito("absent"):
        doc = _loud(["A/v_001", "A/v_004"])
        rc, text, _e = _run(_main_args("loudness") + ["A/v_001", "A/v_004"])
    assert doc["iso226"]["bass_differs"] is True and doc["iso226"]["bass_diff_db"] > 1.0, doc["iso226"]
    assert rc == 0 and "differ in the bass here" in text, text


def _check_zwicker_match_on_a_known_step():
    """Through a stand-in `mosqito`: the bisection on gain finds a 6 dB step, in both sound fields, at each level, and says so; the install line is gone."""
    with _mosqito("standin", _stevens):
        doc = _loud(["A/v_001", "A/v_002"])
        rc, text, _e = _run(_main_args("loudness") + ["A/v_001", "A/v_002"])
    z = doc["zwicker"]
    assert z and doc["install_line"] is None, doc["install_line"]
    assert {(b["level_dbc"], b["field"]) for b in z["blocks"]} == {(l, f) for l in ZWICKER_LEVELS_DBC for f in ZWICKER_FIELDS}, z["blocks"]
    for block in z["blocks"]:
        row = _row_of(block["rows"], "A/v_002")
        assert abs(row["level_db"] - 6.0) < 0.02 and abs(row["match_gain_db"] + 6.0) < 0.02, block
        assert _row_of(block["rows"], "A/v_001")["level_db"] == 0.0, block
    assert rc == 0 and "Zwicker" in text and doc["iso226"]["label"] in text, text
    # a match the bisection cannot reach is said, not clipped
    with _mosqito("standin", _stevens):
        doc = _loud(["--gain-span", "3", "A/v_001", "A/v_002"])
    row = _row_of(doc["zwicker"]["blocks"][0]["rows"], "A/v_002")
    assert row["match_gain_db"] is None and "3" in row["why"], row


def _check_real_mosqito_when_installed():
    """Where the real library is installed, a known level step through it (skipped here otherwise: the stand-in covers the code path, not the library)."""
    import importlib.util
    if importlib.util.find_spec("mosqito") is None:
        return
    doc = _loud(["A/v_001", "A/v_002"])
    z = doc["zwicker"]
    assert z, "mosqito is installed and the Zwicker block is missing"
    for block in z["blocks"]:
        assert abs(_row_of(block["rows"], "A/v_002")["level_db"] - 6.0) < 0.2, block


def _check_input_trim_only():
    """Two versions that differ only by T2's input trim: the loudness match is the trim exactly, once, a routed virtual tier included; the four terms are the same; the trim is said."""
    with _mosqito("absent"):
        doc = _loud(["A/v_001", "A/v_003"])
    assert abs(_row_of(doc["iso226"]["rows"], "A/v_003")["level_db"] + 6.0) < 0.01, doc["iso226"]["rows"]
    assert any("input gain -6 dB" in n for n in doc["notes"]), doc["notes"]
    with _mosqito("absent"):
        doc = _loud(["--route", "VFL=w-L,m-L,tw-L", "A/v_008", "A/v_009"])
    assert abs(_row_of(doc["iso226"]["rows"], "A/v_009")["level_db"] + 6.0) < 0.01, doc["iso226"]["rows"]
    fx = _fx()
    doc = _doc(_main_args("table") + ["--house", fx["house"], "A/v_001", "A/v_003"])
    one, two = (r["terms"] for r in doc["rows"])
    for term in VF.TERMS:
        assert abs(one[term] - two[term]) < 0.02, (term, one[term], two[term])
    assert set(doc["front"]["ties"]) == set(VF.TERMS), doc["front"]


def _check_flags_show_their_effect():
    """Each changed threshold is listed with what the default gives: the band of lr-phase and the phon of ISO 226."""
    proj, solos = _lr_project()
    doc = _doc(["lr-phase", "--project", proj, "--solos", solos, "--band", "300:600", "S/v_001", "S/v_002"])
    assert doc["default_band"] and doc["default_band"]["band_hz"] == list(LR_BAND_HZ) and len(doc["default_band"]["rows"]) == 2, doc["default_band"]
    rc, text, _e = _run(["lr-phase", "--project", proj, "--solos", solos, "--band", "300:600", "S/v_001"])
    assert rc == 0 and "default" in text and "250" in text, text
    with _mosqito("absent"):
        doc = _loud(["--phon", "60", "A/v_001", "A/v_004"])
        rc, text, _e = _run(_main_args("loudness") + ["--phon", "60", "A/v_001", "A/v_004"])
    assert doc["iso226"]["phon"] == 60.0 and doc["iso226"]["default"]["phon"] == ISO_PHON and doc["iso226"]["default"]["rows"], doc["iso226"]
    assert abs(_row_of(doc["iso226"]["rows"], "A/v_004")["level_db"] - _row_of(doc["iso226"]["default"]["rows"], "A/v_004")["level_db"]) > 0.001, doc["iso226"]
    assert rc == 0 and "default" in text and "80 phon" in text, text
    fx = _fx()
    doc = _doc(_main_args("table") + ["--house", fx["house"], "--phase-window", "90", "A/v_001", "A/v_007"])
    assert doc["changed"] and "phase_window_deg 90" in doc["changed"][0], doc["changed"]
    wide = {j["joint"]: j["worst_oct"] for j in doc["rows"][0]["beside"]["joint_widths"]}
    base = {j["joint"]: j["worst_oct"] for j in doc["default_beside"]["A/v_001"]["joint_widths"]}
    assert wide["w-L ↔ m-L"] > base["w-L ↔ m-L"], (wide, base)
    rc, text, _e = _run(_main_args("table") + ["--house", fx["house"], "--phase-window", "90", "A/v_001", "A/v_007"])
    assert rc == 0 and "changed from the default" in text, text[-400:]
    with _mosqito("absent"):
        doc = _loud(["--bass-differs-db", "99", "A/v_001", "A/v_004"])
    assert doc["iso226"]["bass_differs"] is False and doc["iso226"]["bass_differs_at_default"] is True, doc["iso226"]


def _refusal_lines(err):
    """stderr without the model-rate warning a project with no profile gets first."""
    return [ln for ln in err.strip().splitlines() if not ln.strip().startswith("⚠")]


def _check_refusals_are_one_line():
    """A version the ledger does not have; one version where two are needed; no curves named: one line each, exit 3, nothing on stdout."""
    proj, solos = _fx()["main"]
    cases = ((["table", "--project", proj, "--solos", solos, "A/v_099", "A/v_001"], "v_099"),
             (["table", "--project", proj, "--solos", solos, "A/v_001"], "at least two"),
             (["loudness", "--project", proj, "--solos", solos, "A/v_001"], "at least two"),
             (["lr-phase", "--project", proj, "A/v_001"], "--solos"),
             (["round-check", "--project", proj, "--solos", solos, "--sum-band", "broken"], "CODE=LO:HI"),
             (["lr-phase", "--project", proj, "--solos", solos, "--band", "800:250", "A/v_001"], "--band"),
             (["lr-phase", "--project", proj, "--solos", solos, "--band", "500:501", "A/v_001"], "too narrow"))
    failures = []
    for argv, said in cases:
        rc, out, err = _run(argv)
        lines = _refusal_lines(err)
        if rc != 3 or out.strip() or len(lines) != 1 or not lines[0].startswith("refusing:") or said not in lines[0]:
            failures.append(f"{argv[:1] + argv[-2:]}: rc {rc!r}, said {lines[-2:]!r}")
    assert not failures, "\n  ".join([""] + failures)


def _selftest():
    import glob
    import shutil
    import tempfile
    import time
    started = time.time()
    failures = []
    try:
        for check in (_check_table_picks_are_the_fronts, _check_table_names_a_missing_term, _check_table_beside_metrics,
                      _check_coverage_refused, _check_lr_phase_on_planted_differences, _check_round_check_on_planted_sums,
                      _check_round_check_reads_rew_titles, _check_iso226_on_a_known_step, _check_install_line_and_label_when_absent,
                      _check_zwicker_match_on_a_known_step, _check_real_mosqito_when_installed, _check_input_trim_only,
                      _check_flags_show_their_effect, _check_refusals_are_one_line):
            try:
                check()
            except AssertionError as exc:
                failures.append(f"{check.__name__}: {exc}"[:900])
            except Exception as exc:  # noqa: BLE001 -- a crash is a failure of that check, the others still run
                failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}"[:900])
    finally:
        top = _FX.get("top")
        if top:
            shutil.rmtree(top, ignore_errors=True)
        _FX.clear()
    assert not failures, f"{len(failures)} check(s) failed:\n" + "\n".join(failures)
    left = glob.glob(os.path.join(tempfile.gettempdir(), _TMP_PREFIX + "*"))
    assert not left, ("left in TMPDIR", left)
    print(f"selftest[version_bench] OK -- table: the picks are variant_front.front over the four terms (a term missing for a version named; under two "
          f"comparable terms no pick), the other metrics beside them; loudness: ISO 226 and Zwicker (stand-in) match a known step, the trim counted once, "
          f"the install line and the label without mosqito; lr-phase and round-check on planted differences; differing coverage refuses "
          f"({time.time() - started:.1f} s)")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
