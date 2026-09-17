#!/usr/bin/env python3
"""scene_presets -- the two ways to centre the stereo scene, as presets of the same pull, for the ear.

Research's answer to "by time or by level" (hub RES-011 / SKL-040, 2026-09-17; the user's decision): the BASE is
built by level -- the arrivals aligned to the seat (scene offset 0) and the near side cut by channel gain (Phase 1;
Resonalyze's "levels only") -- and the second preset pulls the scene the same amount BY TIME: the near side delayed a
little more (0.15-0.30 ms), its cut reduced so the pull stays the base's. Lee 2010 (Table 4) gives the trade:
0.25 ms ~ 4 dB ~ 10 degrees, a third of the half-stage, so a preset's pull is

    f = dt / 0.75 ms + cut / 12 dB          (a fraction of the half-stage; 16 dB of cut per ms of lead)

The ear decides between them in Phase 2, after "each side whole" and before "everything together" (a time offset
between the sides changes the L+R sum, which that step tunes), with the centre channel off, at matched loudness
(AES20 section 7.3: within 0.5 dB), A-B-B-A three rounds (`references/patterns/listening-cheat-sheet.md`).

What this module does with a ledger version -- the base as it stands after 2c -- and the near-side cut the tuner
gave it in Phase 1 (the Passat's: 2 / 4 / 4 dB on midbass / mid / tweeter):

  * one preset per rung of the ladder: the near side's delay +t on the device's grid, its cut reduced to
    max(0, cut - 16 t), BOTH channels of the pair trimmed so the centred (coherent L+R) level stays the base's;
  * each preset described by its pull, the time and the level parts named apart, and the difference from the base
    per pair -- a band whose cut ran out before the offset did (the Passat's midbass at 0.25 ms) pulls MORE than
    the base, and the report says so rather than calling it the same;
  * the deltas for `apply.propose`, one file per rung; a delay the device cannot hold is refused by name.

Nothing here is entered: the presets go to the sheet as A and B, and the tuner's ear picks (or keeps A).

    python3 rew_tool/scene_presets.py --project DIR --cut w=2,m=4,tw=4 [--preset SQ] [--ver N]
                                      [--steps 0.15,0.2,0.25,0.3] [--out DIR] [--json]
    python3 rew_tool/scene_presets.py --selftest

stdlib only (`project`, `dsp_profile`, `state/state.py`).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_STATE = os.path.join(_HERE, "state")
if _STATE not in sys.path:
    sys.path.insert(0, _STATE)

import dsp_profile as _dp  # noqa: E402
import project as _pj  # noqa: E402

#: Lee 2010, Table 4, through RES-011: 0.25 ms or 4 dB per 10 degrees, a third of the half-stage.
MS_PER_THIRD = 0.75
DB_PER_THIRD = 12.0
CUT_PER_MS_DB = DB_PER_THIRD / MS_PER_THIRD          # 16 dB of cut per ms of lead
#: The rungs RES-011 names for the time preset.
LADDER_MS = (0.15, 0.20, 0.25, 0.30)
#: Below this difference of pull two presets are "probably inaudible" as a pair (RES-011 piece 4).
INAUDIBLE_FRAC = 0.10
#: AES20 section 7.3: the presets' loudness matched within this.
LOUDNESS_TOL_DB = 0.5
PAIR_ROLES = ("woofer", "midrange", "tweeter")
#: The tuner's words for a pair, by role.
PAIR_LABEL = {"woofer": "midbass", "midrange": "mid", "tweeter": "tweeter"}


def pull(dt_ms, cut_db):
    """A preset's pull toward the far side, as a fraction of the half-stage; the two parts add."""
    return float(dt_ms) / MS_PER_THIRD + float(cut_db) / DB_PER_THIRD


def centred_level_db(gain_near_db, gain_far_db):
    """The level of centred (coherent L+R) content from the pair's two gains, relative to both at 0 dB."""
    return 20.0 * math.log10((10 ** (gain_near_db / 20.0) + 10 ** (gain_far_db / 20.0)) / 2.0)


def _snap(value, step):
    return round(round(value / step) * step, 6) if step else value


def near_side(car):
    """The side the driver sits on: L for LHD (the default), R for RHD."""
    return "R" if str((car or {}).get("wheel", "")).upper() == "RHD" else "L"


def pairs_of(rows):
    """{pair code: {"role", "L": code, "R": code}} for the front pairs of the channel map (woofer, midrange, tweeter)."""
    out = {}
    for r in rows or []:
        code, role = r.get("code") or "", r.get("role")
        if role not in PAIR_ROLES or r.get("hidden"):
            continue
        if code.endswith("-L") or code.endswith("-R"):
            out.setdefault(code[:-2], {"role": role})[code[-1]] = code
    return {k: v for k, v in out.items() if "L" in v and "R" in v}


def parse_cuts(text, pairs):
    """`w=2,m=4,tw=4` (by pair code or by the tuner's word) or one number for every pair -> {pair: cut dB}."""
    by_label = {PAIR_LABEL[v["role"]]: k for k, v in pairs.items()}
    out = {}
    if "=" not in text:
        value = float(text.replace(",", "."))
        return {k: value for k in pairs}
    for item in text.split(","):
        key, val = item.split("=", 1)
        key = key.strip()
        code = key if key in pairs else by_label.get(key.lower())
        if code is None:
            raise ValueError(f"--cut names {key!r}, which is no front pair ({', '.join(sorted(pairs)) or 'none'})")
        out[code] = float(val.strip())
    missing = [k for k in pairs if k not in out]
    if missing:
        raise ValueError(f"--cut names no cut for {', '.join(missing)} -- 0 is a number too")
    return out


def base_of(snapshot, pairs, near, cuts):
    """The base preset as the ledger holds it: per pair the near and far rows' gain and delay, the deliberate cut, its pull."""
    far = "R" if near == "L" else "L"
    rows = snapshot.get("channels") or {}
    out, notes = {}, []
    for pair, spec in pairs.items():
        n, f = rows.get(spec[near]), rows.get(spec[far])
        if n is None or f is None:
            notes.append(f"{pair}: {spec[near]} or {spec[far]} is not in the version -- pair left out")
            continue
        gn, gf = float(n.get("gain_db") or 0.0), float(f.get("gain_db") or 0.0)
        tn, tf = float(n.get("ta_ms") or 0.0), float(f.get("ta_ms") or 0.0)
        cut = float(cuts[pair])
        if cut < 0:
            notes.append(f"{pair}: a cut of {cut:g} dB is a boost of the near side -- the base pulls the wrong way")
        actual = gf - gn
        if actual + 0.05 < cut:
            notes.append(f"{pair}: the version has the near side only {actual:+.1f} dB under the far one, "
                         f"less than the {cut:g} dB cut named -- is the base entered?")
        out[pair] = {"role": spec["role"], "label": PAIR_LABEL[spec["role"]], "near": spec[near], "far": spec[far],
                     "gain_near_db": gn, "gain_far_db": gf, "ta_near_ms": tn, "ta_far_ms": tf,
                     "cut_db": cut, "gain_diff_db": round(actual, 2), "f": round(pull(0.0, cut), 4),
                     "centred_db": round(centred_level_db(gn, gf), 3)}
    return out, notes


def rung(base, t_ms, delay_step_ms=0.01, gain_step_db=0.1, delay_max_ms=None, gain_range_db=None):
    """One time preset: the near side +t ms, its cut reduced so the pull holds, both channels trimmed for loudness."""
    t = _snap(float(t_ms), delay_step_ms)
    out = {"t_ms": t, "pairs": {}, "delta": {"channels": {}}, "problems": [], "notes": []}
    for pair, b in base.items():
        cut_t = max(0.0, b["cut_db"] - CUT_PER_MS_DB * t)
        # The pull's level part is the DELIBERATE cut, not the pair's whole gain difference: the version's gains also
        # carry per-driver corrections that pull nothing. The near side is raised by the cut that time replaces.
        raise_db = _snap(b["cut_db"] - cut_t, gain_step_db)
        gain_near = round(b["gain_near_db"] + raise_db, 6)
        cut_held = b["cut_db"] - raise_db                                 # on the grid, what the device holds
        trim = _snap(b["centred_db"] - centred_level_db(gain_near, b["gain_far_db"]), gain_step_db)
        gn, gf = gain_near + trim, b["gain_far_db"] + trim
        ta_near = _snap(b["ta_near_ms"] + t, delay_step_ms)
        f_time, f_level = t / MS_PER_THIRD, cut_held / DB_PER_THIRD
        f = f_time + f_level
        row = {"near": b["near"], "far": b["far"], "label": b["label"], "dt_ms": t, "cut_db": round(cut_held, 2),
               "cut_base_db": b["cut_db"], "f_time": round(f_time, 4), "f_level": round(f_level, 4), "f": round(f, 4),
               "f_base": b["f"], "df": round(f - b["f"], 4), "trim_db": trim,
               "gain_near_db": round(gn, 3), "gain_far_db": round(gf, 3), "ta_near_ms": ta_near,
               "centred_db": round(centred_level_db(gn, gf), 3), "centred_base_db": b["centred_db"]}
        if abs(row["centred_db"] - b["centred_db"]) > LOUDNESS_TOL_DB:
            out["problems"].append(f"{pair}: centred level {row['centred_db'] - b['centred_db']:+.2f} dB off the base's "
                                   f"after the trim -- more than {LOUDNESS_TOL_DB} dB")
        if delay_max_ms is not None and ta_near > float(delay_max_ms) + 1e-9:
            out["problems"].append(f"{pair}: {b['near']} would need {ta_near:.2f} ms, over the device's {delay_max_ms:g}")
        if gain_range_db and (gn < gain_range_db[0] - 1e-9 or gf < gain_range_db[0] - 1e-9 or
                              gn > gain_range_db[1] + 1e-9 or gf > gain_range_db[1] + 1e-9):
            out["problems"].append(f"{pair}: a gain leaves the device's range {gain_range_db}")
        if abs(row["df"]) >= INAUDIBLE_FRAC:
            out["notes"].append(f"{b['label']}: the cut ran out at {b['cut_db'] / CUT_PER_MS_DB:.2f} ms, so this rung pulls "
                                f"{row['df']:+.0%} of the half-stage MORE than the base there -- part of what the ear "
                                "hears on that band is a stronger pull, not the mechanism")
        out["pairs"][pair] = row
        out["delta"]["channels"][b["near"]] = {"ta_ms": ta_near, "gain_db": round(gn, 3)}
        out["delta"]["channels"][b["far"]] = {"gain_db": round(gf, 3)}
    return out


def ladder(base, steps=LADDER_MS, **limits):
    return [rung(base, t, **limits) for t in steps]


def pair_verdict(a_pairs, b_pairs):
    """RES-011 piece 4 on two presets: 'probably inaudible' when every pair's pull differs under 10 %."""
    diffs = {k: abs(float(b_pairs[k]["f"]) - float(a_pairs[k]["f"])) for k in a_pairs if k in b_pairs}
    if not diffs:
        return "no pair to compare"
    worst = max(diffs.values())
    if worst < INAUDIBLE_FRAC:
        return (f"the same pull within {worst:.0%} of the half-stage -- what the ear compares is the MECHANISM, "
                "time against level, not a stronger pull")
    over = ", ".join(f"{a_pairs[k]['label']} {diffs[k]:+.0%}" for k in diffs if diffs[k] >= INAUDIBLE_FRAC)
    return f"the pull differs by {INAUDIBLE_FRAC:.0%} or more on: {over}"


def _limits(project_dir):
    path = os.path.join(project_dir, "dsp_profile.json")
    if not os.path.isfile(path):
        return {}
    data = _dp._unwrap(_dp.load_profile(path))
    delay = data.get("delay") or {}
    out = {"delay_step_ms": float(delay.get("step_ms") or 0.01), "delay_max_ms": delay.get("max_ms")}
    for group in data.get("groups") or []:
        if _dp.ledger_tier((group or {}).get("id")) == "channels":
            gain = group.get("channel_gain") or {}
            if gain.get("step_db"):
                out["gain_step_db"] = float(gain["step_db"])
            if gain.get("range_db"):
                out["gain_range_db"] = [float(x) for x in gain["range_db"]]
    return out


def presets_for(project_dir, cut_text, preset=None, version=None, steps=LADDER_MS):
    """The base and its ladder from a project's ledger. Returns the report dict (with `problems` when it cannot run)."""
    import state as st
    data = _pj.Project(project_dir).load()
    pairs = pairs_of(data.get("channels") or [])
    if not pairs:
        return {"problems": ["the channel map has no front L/R pair (woofer, midrange, tweeter with -L/-R codes)"]}
    near = near_side(data.get("car"))
    root = os.path.join(project_dir, "state")
    preset = preset or st.Registry(root).get_active()
    if not preset:
        return {"problems": [f"no active slot in {root}/registry -- pass --preset"]}
    snapshot = st.PresetHistory(root, preset, project_dir=project_dir).load(version)
    cuts = parse_cuts(cut_text, pairs)
    base, notes = base_of(snapshot, pairs, near, cuts)
    if not base:
        return {"problems": notes or ["no pair of the map is in the version"]}
    rungs = ladder(base, steps, **_limits(project_dir))
    return {"preset": preset, "version": snapshot.get("version"), "near": near, "base": base, "rungs": rungs,
            "notes": notes, "verdicts": {f"{r['t_ms']:g} ms": pair_verdict(base, r["pairs"]) for r in rungs}}


def render(rep):
    if rep.get("problems"):
        return "\n".join(f"  ✗ {p}" for p in rep["problems"])
    lines = [f"  Scene presets on {rep['preset']} {rep['version']} -- the near side is {rep['near']}; "
             f"pull f = dt/0.75 ms + cut/12 dB (a fraction of the half-stage)", "",
             "  A, the base (arrivals aligned, the pull by level):"]
    for pair, b in rep["base"].items():
        lines.append(f"    {b['label']:8} {b['near']} {b['gain_near_db']:+.1f} dB / {b['far']} {b['gain_far_db']:+.1f} dB   "
                     f"cut {b['cut_db']:g} dB -> f {b['f']:.0%}   centred {b['centred_db']:+.2f} dB")
    for r in rep["rungs"]:
        lines.append("")
        lines.append(f"  B at {r['t_ms']:g} ms (the near side later by {r['t_ms']:g} ms, its cut reduced, both channels trimmed):")
        for pair, p in r["pairs"].items():
            lines.append(f"    {p['label']:8} {p['near']} +{p['dt_ms']:g} ms, cut {p['cut_db']:g} dB, trim {p['trim_db']:+.1f} dB"
                         f"   f {p['f']:.0%} = time {p['f_time']:.0%} + level {p['f_level']:.0%}   vs base {p['df']:+.0%}")
        key = f"{r['t_ms']:g} ms"
        lines.append(f"    -> {rep['verdicts'][key]}")
        for n in r["notes"]:
            lines.append(f"    ! {n}")
        for p in r["problems"]:
            lines.append(f"    ✗ {p}")
    for n in rep.get("notes") or []:
        lines.append(f"  ! {n}")
    lines += ["", "  Compare in Phase 2 after each side is whole, centre off, A-B-B-A three rounds; no consistent "
                  "difference -> keep A. The tuner chooses; nothing is entered before that."]
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest
def _selftest():
    import tempfile
    assert abs(pull(0.25, 0.0) - 1 / 3) < 1e-9 and abs(pull(0.0, 4.0) - 1 / 3) < 1e-9 and CUT_PER_MS_DB == 16.0
    assert abs(centred_level_db(-4.0, 0.0) - (-1.77)) < 0.01, centred_level_db(-4.0, 0.0)   # research's number
    rows = [{"code": "sw", "role": "sub"}, {"code": "w-L", "role": "woofer"}, {"code": "w-R", "role": "woofer"},
            {"code": "m-L", "role": "midrange"}, {"code": "m-R", "role": "midrange"},
            {"code": "tw-L", "role": "tweeter"}, {"code": "tw-R", "role": "tweeter"},
            {"code": "c", "role": "center"}, {"code": "r-L", "role": "rear", "hidden": True}, {"code": "r-R", "role": "rear", "hidden": True}]
    pairs = pairs_of(rows)
    assert sorted(pairs) == ["m", "tw", "w"] and pairs["m"] == {"role": "midrange", "L": "m-L", "R": "m-R"}, pairs
    assert near_side({"wheel": "LHD"}) == "L" and near_side({"wheel": "RHD"}) == "R" and near_side(None) == "L"
    assert parse_cuts("w=2,m=4,tw=4", pairs) == {"w": 2.0, "m": 4.0, "tw": 4.0}
    assert parse_cuts("midbass=2, mid=4, tweeter=4", pairs) == {"w": 2.0, "m": 4.0, "tw": 4.0}
    assert parse_cuts("3", pairs) == {"w": 3.0, "m": 3.0, "tw": 3.0}
    for bad in ("w=2,m=4", "sub=1,w=2,m=4,tw=4"):
        try:
            parse_cuts(bad, pairs)
            raise AssertionError(bad)
        except ValueError:
            pass

    # the Passat's base as research read it: near side 2 / 4 / 4 dB under the far one, arrivals aligned
    snap = {"version": 63, "channels": {
        "w-L": {"gain_db": -2.0, "ta_ms": 5.27}, "w-R": {"gain_db": 0.0, "ta_ms": 3.87},
        "m-L": {"gain_db": -4.0, "ta_ms": 6.36}, "m-R": {"gain_db": 0.0, "ta_ms": 5.03},
        "tw-L": {"gain_db": -4.0, "ta_ms": 6.27}, "tw-R": {"gain_db": 0.0, "ta_ms": 4.94}}}
    base, notes = base_of(snap, pairs, "L", {"w": 2.0, "m": 4.0, "tw": 4.0})
    assert not notes and abs(base["m"]["f"] - 1 / 3) < 1e-3 and abs(base["w"]["f"] - 1 / 6) < 1e-3, (notes, base)
    # a cut named that the version does not hold is a question
    _, notes2 = base_of(snap, pairs, "L", {"w": 2.0, "m": 6.0, "tw": 4.0})
    assert notes2 and "less than the 6 dB cut named" in notes2[0], notes2

    rungs = ladder(base, LADDER_MS, delay_step_ms=0.01, gain_step_db=0.1, delay_max_ms=20.82)
    r25 = rungs[2]
    assert r25["t_ms"] == 0.25 and not r25["problems"]
    m = r25["pairs"]["m"]
    # at 0.25 ms the mid's 4 dB cut is gone: the pull is all time, and equal to the base's
    assert m["cut_db"] == 0.0 and abs(m["f"] - 1 / 3) < 1e-3 and abs(m["df"]) < 1e-3 and m["ta_near_ms"] == 6.61, m
    # ... and the pair is trimmed so centred content stays where it was: the near side at -4 dB made it -1.77 dB
    # (research's number), the raised pair is trimmed by that on the 0.1 dB grid
    assert m["trim_db"] == -1.8 and abs(m["centred_db"] - m["centred_base_db"]) <= LOUDNESS_TOL_DB, m
    assert r25["delta"]["channels"]["m-L"] == {"ta_ms": 6.61, "gain_db": -1.8} and r25["delta"]["channels"]["m-R"] == {"gain_db": -1.8}
    # the midbass's 2 dB ran out at 0.125 ms: at 0.25 ms it pulls a sixth more than the base, and the rung says so
    w = r25["pairs"]["w"]
    assert w["cut_db"] == 0.0 and abs(w["df"] - 1 / 6) < 1e-3 and any("midbass" in n and "MORE" in n for n in r25["notes"]), (w, r25["notes"])
    # at 0.15 ms every band keeps some cut but the midbass, whose difference stays under 10 %
    r15 = rungs[0]
    assert r15["pairs"]["m"]["cut_db"] == 1.6 and r15["pairs"]["tw"]["cut_db"] == 1.6 and r15["pairs"]["w"]["cut_db"] == 0.0
    assert abs(r15["pairs"]["w"]["df"] - (0.2 - 1 / 6)) < 1e-3 and not r15["notes"], r15
    # a version whose gains carry other corrections keeps its own numbers: the cut named is what moves, not the difference
    other = dict(snap, channels=dict(snap["channels"], **{"tw-L": {"gain_db": -5.8, "ta_ms": 6.27}, "tw-R": {"gain_db": -4.2, "ta_ms": 4.94}}))
    base2, notes3 = base_of(other, pairs, "L", {"w": 2.0, "m": 4.0, "tw": 4.0})
    assert notes3 and "tw" in notes3[0] and "is the base entered" in notes3[0], notes3
    tw = rung(base2, 0.25)["pairs"]["tw"]
    assert tw["cut_db"] == 0.0 and abs(tw["df"]) < 1e-3 and tw["gain_near_db"] == round(-5.8 + 4.0 + tw["trim_db"], 3), tw
    assert "MECHANISM" in pair_verdict(base, r15["pairs"]) and "midbass" in pair_verdict(base, r25["pairs"])
    # the device's ceiling refuses a rung it cannot hold
    tight = ladder(base, (0.30,), delay_step_ms=0.01, gain_step_db=0.1, delay_max_ms=6.6)
    assert tight[0]["problems"] and "over the device's 6.6" in tight[0]["problems"][0], tight[0]["problems"]
    text = render({"preset": "SQ", "version": 63, "near": "L", "base": base, "rungs": rungs, "notes": [],
                   "verdicts": {f"{r['t_ms']:g} ms": pair_verdict(base, r["pairs"]) for r in rungs}})
    assert "A, the base" in text and "B at 0.25 ms" in text and "keep A" in text, text

    # the project path: the limits come from the profile, the version from the ledger
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "dsp_profile.json"), "w", encoding="utf-8") as fh:
            json.dump({"dsp_profile": {"delay": {"step_ms": 0.01, "max_ms": 20.82},
                                       "groups": [{"id": "physical_outputs", "channel_gain": {"step_db": 0.5, "range_db": [-30, 5]}}]}}, fh)
        lim = _limits(d)
        assert lim == {"delay_step_ms": 0.01, "delay_max_ms": 20.82, "gain_step_db": 0.5, "gain_range_db": [-30.0, 5.0]}, lim
        coarse = rung(base, 0.25, **lim)
        assert coarse["pairs"]["m"]["trim_db"] in (-1.5, -2.0) and abs(coarse["pairs"]["m"]["centred_db"] - coarse["pairs"]["m"]["centred_base_db"]) <= 0.5
    print("selftest[scene_presets] OK -- f = dt/0.75 + cut/12 (0.25 ms = 4 dB = a third); the front pairs from the "
          "map, the near side from the wheel; the base's cut checked against the version; the ladder's near side "
          "later by t with the cut reduced 16 dB/ms and both channels trimmed to the base's centred level (the mid at "
          "0.25 ms: cut gone, trim -1.3 dB, f unchanged); a band whose cut ran out is named as pulling more; the "
          "verdict says 'mechanism' at equal pull; a version whose gains carry other corrections moves by the cut named, "
          "not by its gain difference; a rung over the device's ceiling is refused; deltas for apply.propose")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project", metavar="DIR")
    ap.add_argument("--cut", metavar="w=2,m=4,tw=4", help="the near-side cut of the base per pair, in dB (Phase 1's number)")
    ap.add_argument("--preset", default=None, help="the ledger slot (default: the active one)")
    ap.add_argument("--ver", type=int, default=None, help="the version (default: the head)")
    ap.add_argument("--steps", default=",".join(f"{t:g}" for t in LADDER_MS), help="the ladder, ms")
    ap.add_argument("--out", metavar="DIR", help="write scene-presets.json and one apply.propose delta per rung")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.project or not a.cut:
        ap.error("need --project DIR and --cut (the base's near-side cut per pair, e.g. w=2,m=4,tw=4)")
    steps = tuple(float(s) for s in a.steps.split(",") if s.strip())
    try:
        rep = presets_for(a.project, a.cut, a.preset, a.ver, steps)
    except (ValueError, FileNotFoundError) as e:
        print(f"  ✗ {e}", file=sys.stderr)
        return 2
    if a.out and not rep.get("problems"):
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "scene-presets.json"), "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1, ensure_ascii=False)
        for r in rep["rungs"]:
            with open(os.path.join(a.out, f"scene-preset-{r['t_ms']:g}ms.json"), "w", encoding="utf-8") as fh:
                json.dump(r["delta"], fh, indent=1)
    if a.json:
        print(json.dumps(rep, indent=1, ensure_ascii=False))
    else:
        print(render(rep))
        if a.out and not rep.get("problems"):
            print(f"\n  wrote {a.out}/scene-presets.json and scene-preset-<t>ms.json (deltas for apply.propose)")
    return 2 if rep.get("problems") else 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(main())
