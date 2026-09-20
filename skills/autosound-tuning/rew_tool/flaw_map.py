#!/usr/bin/env python3
"""flaw_map -- the acoustic flaw map as a COMMAND: rows proposed from the measurements, not typed.

`project.py flaw` writes a row of `acoustics.flaws` (a frequency, a signed level, a kind, what may
be done about it, why, and the capture it was read off). Until now every row was composed by a
person reading curves. The analysers that read those curves already exist -- `curve_view` finds
the features, `ellipsoid` says which of them stay put as the microphone moves, the excess-phase
gate says which are minimum-phase -- so this turns their findings into rows a later session can
act on, and leaves every finding it cannot classify OUT, saying why.

What it writes, and on what grounds (each rule is doctrine that already exists; see the pointers):

  kind                 action     grounds
  driver_resonance     notch      a PEAK, 1/6-2/3 oct wide, that STAYS across positions and is
                                  minimum-phase at the gate (`diagnostic-techniques.md` Q ceiling;
                                  `phase_2_eq.md` 2a)
  modal_peak           notch      a peak below Schroeder (~200 Hz) that stays: the cabin's mode
  cabin_null           no_boost   a DIP below Schroeder: interference, cannot be filled
  non_min_phase        no_boost   any feature the excess-phase gate BLOCKS (r > 1 reflection):
                                  a filter there is physics-fighting (`eq_gate`)

What it does NOT write, and says so: a dip above Schroeder (the position, not the car -- Rayleigh
statistics), a feature narrower than 1/6 oct (what fails to survive a mic move is always narrow --
Wehmeyer), a peak the ellipsoid says MOVES, anything for a channel whose solo was refused at
de-embed. Every row is written as `status: hypothesis` -- a command can find, it cannot confirm;
confirming is a person's verdict after the car has been heard, and `project.py flaw` is where that
is recorded.

    python3 rew_tool/flaw_map.py --project DIR --solos DIR [--ellipsoid DIR] [--write] [--json]
    python3 rew_tool/flaw_map.py --project DIR --rew N [--channels a,b] [--process DIR] [--write] [--json]
    python3 rew_tool/flaw_map.py --selftest

`--rew N` reads the solos a Phase-0 round left IN REW (`<code>_N (sw)`), which is where they are:
the v7 files `--solos` wants come from a different pipeline that Phase 0 never asks for (skill #35).
What was in each chain comes from the round's own protective record (`capture-protective`), the
same source `predict.py --rew` reads; the ellipsoid, where REW holds positions, comes along. The
solos are read as impulse responses, so REW's display smoothing does not reach them (hub TCC-015).

Without `--write` the rows are printed and nothing changes. With it they go through
`project.Project.add_flaw`, which validates each row again and replaces a row at the same
frequency for the same channels rather than adding a second one.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import curve_view                                # noqa: E402
import predict as P                              # noqa: E402
import project as _project                       # noqa: E402
from eq_propose import gate_from_ir, SCHROEDER_HZ, RES_WIDTH  # noqa: E402

MIN_PROMINENCE_DB = 3.0          # below this a feature is tone, not a flaw (ear_suspects uses the same)
MATCH_OCT = 1 / 6                # an ellipsoid feature within this of ours is the same feature


def q_of_width(width_oct):
    """Equivalent Q of a feature `width_oct` wide (the bandwidth-to-Q identity)."""
    w = max(float(width_oct), 1 / 48)
    return (2 ** (w / 2)) / (2 ** w - 1)


#: What a PEAK row says when nobody measured the positions. One string, in one place, because the
#: phase-0 gate reads rows back and has to recognise it (S-047) -- two spellings of it would mean a
#: gate that silently stops firing the next time this sentence is edited.
ASSUMED_NOTE = "no positions measured -- staying is ASSUMED, not shown"


def settling_request(rows, version=None):
    """What would settle the ASSUMED rows — the channels, the titles, and the one command (S-047).

    The tool already KNOWS the question was not asked: `classify` writes `ASSUMED_NOTE` on every
    peak row it could not check, and `status: hypothesis` on all of them. On a live project that
    was computed 43 times and carried nowhere, while the reader for the data (`ellipsoid.py`) and
    the way to ask for it both existed — the Arbiter had the nine-position set on disk the whole
    time and asked «чому скіл сам не запитав про такий замір?». A rule that lives only in prose
    does not fire; a run that produced assumed rows now ends with the REQUEST.

    **What settles WHICH row, and it is not all of them.** Only a peak's verdict depends on the
    positions: `modal_peak` and `driver_resonance` say "stays" on an assumption, and the ellipsoid
    of that channel — `<ch> p1…p9_<N> (sw)` — is what shows it. A `cabin_null` (a dip below
    Schroeder) and a `non_min_phase` row do not turn on the microphone moving, so they ask for
    nothing here and are not counted.

    Returns None when nothing is assumed.
    """
    channels = sorted({r["channels"][0] for r in rows
                       if ASSUMED_NOTE in (r.get("why") or "") and r.get("channels")})
    if not channels:
        return None
    n = version if version is not None else "<N>"
    titles = [f"{code} p{i}_{n} (sw)" for code in channels for i in range(1, 10)]
    return {
        "channels": channels,
        "rows": sum(1 for r in rows if ASSUMED_NOTE in (r.get("why") or "")),
        "version": n,
        "pattern": [f"{code} p1..p9_{n} (sw)" for code in channels],
        "titles": titles,
        "capture_start": "python3 rew_tool/state/process.py <project>/process capture-start "
                         + f"{n} " + " ".join(f'"{t}"' for t in titles),
    }


def classify(feature, gate=None, ellipsoid_feature=None):
    """One feature -> a flaw row (dict) or (None, reason). Pure: every rule is testable alone.

    `feature`: a `curve_view.find_features` record. `gate`: an `ExcessPhaseGate` for this channel
    or None (no impulse -> the gate is out of scope and the minimum-phase question stays open).
    `ellipsoid_feature`: the matching `ellipsoid.analyse` feature, or None when no positions were
    measured -- absence of positions does not mean "stays"; it means the question was not asked,
    and the row says so.
    """
    fc, w, level, kind = feature["f_center"], feature["width_oct"], feature["extremum_db"], feature["kind"]
    q = q_of_width(w)
    verdict = None
    if gate is not None and gate.in_scope(fc):
        verdict, _metric, _ = gate.check(fc, q)

    if verdict == "BLOCK":
        return {"kind": "non_min_phase", "action": "no_boost", "f_hz": round(fc, 1),
                "level_db": round(level, 1), "width_oct": round(w, 3),
                "why": f"the excess-phase gate BLOCKS a filter at {fc:.0f} Hz (a reflection stronger "
                       f"than the direct sound -- not minimum-phase); a boost here fights physics"}, None
    if kind == "dip":
        if fc < SCHROEDER_HZ:
            return {"kind": "cabin_null", "action": "no_boost", "f_hz": round(fc, 1),
                    "level_db": round(level, 1), "width_oct": round(w, 3),
                    "why": f"a dip of {level:.1f} dB below Schroeder: interference, not a driver "
                           f"-- it cannot be filled by boosting"}, None
        return None, f"a dip above Schroeder ({fc:.0f} Hz): the position, not the car (Rayleigh)"
    # a peak
    if w < RES_WIDTH[0]:
        return None, (f"narrower than 1/6 oct ({w:.2f}): what fails to survive a mic move is "
                      f"always narrow (Wehmeyer)")
    if ellipsoid_feature is not None and not ellipsoid_feature.get("stays"):
        return None, (f"the ellipsoid says it MOVES ({ellipsoid_feature.get('present_in')} positions): "
                      f"that spot, not the system")
    stays_note = "stays across the positions" if ellipsoid_feature is not None else ASSUMED_NOTE
    if fc < SCHROEDER_HZ:
        return {"kind": "modal_peak", "action": "notch", "f_hz": round(fc, 1),
                "level_db": round(level, 1), "width_oct": round(w, 3),
                "why": f"a peak of +{level:.1f} dB below Schroeder, {stays_note}: the cabin's mode"}, None
    if w > RES_WIDTH[1]:
        return None, f"wider than 2/3 oct ({w:.2f}): tone, for the target and the tone package -- not a flaw"
    if verdict == "WARN":
        return {"kind": "driver_resonance", "action": "leave", "f_hz": round(fc, 1),
                "level_db": round(level, 1), "width_oct": round(w, 3),
                "why": f"a peak of +{level:.1f} dB, {stays_note}, but the excess-phase gate only "
                       f"WARNS: leave it until a boost/cut can be shown safe on a second capture"}, None
    return {"kind": "driver_resonance", "action": "notch", "f_hz": round(fc, 1),
            "level_db": round(level, 1), "width_oct": round(w, 3),
            "why": f"a peak of +{level:.1f} dB, {w:.2f} oct wide (Q~{q:.1f}), {stays_note}"
                   + (", minimum-phase at the gate" if verdict == "ALLOW" else
                      "; the gate had no impulse to judge it (no IR)")}, None


def _match_ellipsoid(fc, ell):
    for ft in (ell or {}).get("features") or []:
        if abs(math.log2(ft["f_center"] / fc)) <= MATCH_OCT and ft.get("kind") == "peak":
            return ft
    return None


LIVE_BELOW_PEAK_DB = 25.0        # where the RAW record is further below its own peak, there is no signal


def rows_for(freqs, mag_db, code, evidence, gate=None, ell=None, raw_db=None):
    """All rows and all refusals for one channel's curve.

    `raw_db` is the record BEFORE de-embedding. De-embedding divides by the protective filter, and
    where that filter had removed the signal the quotient is noise wearing the driver's shape --
    the first run of this found a "+3.9 dB resonance at 317 Hz" on a tweeter whose protective
    high-pass sits at 1 kHz. A feature is judged only where the raw record shows signal.
    """
    view = curve_view.multiscale(freqs, mag_db, (float(freqs[0]), float(freqs[-1])), macro_frac=1, fine_frac=24)
    feats = curve_view.find_features(view, min_prominence_db=MIN_PROMINENCE_DB, source="sweep")
    rows, left = [], []
    f_arr = np.asarray(freqs, float)
    raw = None if raw_db is None else np.asarray(raw_db, float)
    for ft in feats:
        if raw is not None:
            k = int(np.argmin(np.abs(f_arr - ft["f_center"])))
            if raw[k] < float(raw.max()) - LIVE_BELOW_PEAK_DB:
                left.append({"channel": code, "f_hz": ft["f_center"], "level_db": ft["extremum_db"],
                             "reason": f"no signal there in the raw record ({raw[k] - raw.max():.0f} dB "
                                       f"below the channel's peak -- the protective filter's region)"})
                continue
        row, why_not = classify(ft, gate, _match_ellipsoid(ft["f_center"], ell) if ell else None)
        if row is None:
            left.append({"channel": code, "f_hz": ft["f_center"], "level_db": ft["extremum_db"],
                         "reason": why_not})
            continue
        row.update({"channels": [code], "status": "hypothesis", "evidence": list(evidence)})
        # The owner's line, as a DRAFT. Until 2026-09-05 this module never wrote `symptom` at all
        # -- the word did not appear in the file -- so every map made the standard way was born
        # without the one line a car's owner reads, and the requirement lived in prose elsewhere
        # (autosound-hub CAR-007). We know the kind, the band and the channel, which is what the
        # sentence is made of; we do NOT know what the car sounds like, so the draft is marked as
        # one. It is a communication line and nothing more: the row stands on `evidence`, and the
        # phase-0 gate asks for that, not for a person's words (the user's ruling, #22).
        draft = _project.symptom_draft(row["kind"], row.get("f_hz"), row["channels"])
        if draft and row["action"] in _project.OWNER_FACING_ACTIONS:
            row["symptom"] = draft
        rows.append(row)
    return rows, left


def _load_from_rew(project_dir, ver, f, channels=None, process_dir=None):
    """`(loaded, record, notes)` for `--rew`: the round's solos out of REW and its protective record.

    Refuses rather than guesses where the answer is not on record: no channel codes to ask for, none
    of the solos in REW, or no capture round for `_N` -- reading a baseline solo "as configured" on
    top of a missing record is how a protective filter stays in a flaw row unseen."""
    import naming
    codes = list(channels) if channels else naming.Glossary.for_project(project_dir).channel_codes(active_only=True)
    if not codes:
        raise SystemExit("refusing: --rew needs the channel codes -- a glossary in the project, or --channels")
    loaded, notes = {}, []
    for code in codes:
        title = f"{code}_{ver} (sw)"
        try:
            loaded[code] = P.load_solo_rew(title, f, keep_ir=True)
        except (P.PredictError, KeyError, ValueError) as exc:
            notes.append(f"{code}: not read from REW ({exc})")
    if not loaded:
        raise SystemExit("refusing: REW holds none of the round's solos -- " + "; ".join(notes))
    proc_dir = process_dir or os.path.join(project_dir, "process")
    record = None
    if os.path.isdir(proc_dir):
        state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
        if state_dir not in sys.path:
            sys.path.insert(0, state_dir)
        from process import Process
        proc = Process(proc_dir)
        record = proc.protective_record_for(ver)
        rounds = proc.capture_rounds()
    else:
        rounds = []
    if record is None:
        raise SystemExit(
            f"refusing: no capture round on record for _{ver} in {proc_dir} -- what was in each chain "
            "is the round's to say (`capture-protective`), and a baseline solo read without it can carry "
            "a protective filter into a row. Rounds on record: "
            + ("; ".join(f"{r['id']} version {r['version']!r}" for r in rounds) or "none"))
    return loaded, record, notes


def run(project_dir, solos_dir=None, ellipsoid_dir=None, write=False, rew_ver=None, channels=None,
        process_dir=None):
    f = P.grid(20, 20000, 96)
    record, rew_notes = None, []
    if rew_ver is not None:
        loaded, record, rew_notes = _load_from_rew(project_dir, rew_ver, f, channels, process_dir)
    else:
        loaded = P.load_solos_dir(solos_dir, f)
        if not loaded:
            raise SystemExit(f"refusing: no solo v7 files in {solos_dir}")
    solos, notes, refused = P.de_embed_solos(loaded, f, record=record, baseline=True)
    result = {"rows": [], "left_out": [], "refused": sorted(refused), "notes": rew_notes + notes}
    for code, H in sorted(solos.items()):
        if "+" in code or code == "ALL":
            continue
        info = loaded[code][1]
        gate = None
        if info.get("source") == "rew":
            ir = info.get("ir") or {}
            if ir.get("ir") is not None:
                gate = gate_from_ir(ir["ir"], ir["sample_rate"])
        else:
            try:
                import resonalyze_ir
                doc = resonalyze_ir.load_file(info["path"])           # v7 numbers or v8 base64 alike
                gate = gate_from_ir(doc["transferRealSamples"], doc["sampleRate"])
            except (OSError, KeyError, ValueError):
                pass
        ell = None
        if ellipsoid_dir or rew_ver is not None:
            import ellipsoid as E
            try:
                positions = (E.load_positions_rew(code, rew_ver, f) if rew_ver is not None
                             else E.load_positions_v7(ellipsoid_dir, code, f))
                ell = E.analyse(f, positions)
            except Exception as exc:         # a channel without positions is not an error, it is unasked
                if ellipsoid_dir:
                    result["notes"].append(f"{code}: no ellipsoid ({exc})")
        if rew_ver is not None:
            evidence = [info["title"]] + ([f"{code} p1..p9_{rew_ver} (sw)"] if ell else [])
        else:
            evidence = [os.path.basename(info["path"])] + ([os.path.basename(ellipsoid_dir.rstrip("/"))]
                                                           if ell else [])
        raw_H = loaded[code][0]
        rows, left = rows_for(f, 20 * np.log10(np.abs(H) + 1e-12), code, evidence, gate, ell,
                              raw_db=20 * np.log10(np.abs(raw_H) + 1e-12))
        result["rows"] += rows
        result["left_out"] += left
    result["settle"] = settling_request(result["rows"], rew_ver)
    if write and result["rows"]:
        pj = _project.Project(project_dir)
        for row in result["rows"]:
            pj.add_flaw(**{k: v for k, v in row.items() if k != "width_oct"})
        result["written"] = len(result["rows"])
    return result


def render(result):
    out = []
    if result["refused"]:
        out.append(f"refused at de-embed (no recorded protective state): {', '.join(result['refused'])}")
    if not result["rows"]:
        out.append("no flaw rows proposed")
    else:
        out.append(f"{'channel':8} {'f Hz':>7} {'dB':>6} {'kind':17} {'action':9} why")
        for r in result["rows"]:
            out.append(f"{r['channels'][0]:8} {r['f_hz']:7.0f} {r['level_db']:+6.1f} {r['kind']:17} "
                       f"{r['action']:9} {r['why']}")
            if r.get("symptom"):
                out.append(f"{'':8} {'':>7} {'':>6} {'':17} {'':9} ⟵ {r['symptom']}")
        drafts = sum(1 for r in result["rows"] if _project.symptom_is_draft(r))
        if drafts:
            out.append(f"\n{drafts} owner-facing row(s) carry a DRAFT symptom: it is what the kind "
                       f"sounds like, not what THIS car sounds like. A person's line, if the owner "
                       f"gives one after hearing the finished tune, replaces it (`project.py <dir> "
                       f"flaw … --symptom \"…\"`); the rows stand on their measurements either way, "
                       f"and the phase-0 gate asks for those, not for words (#22).")
    if result["left_out"]:
        out.append("\nfound but NOT written (and why):")
        for l in result["left_out"]:
            out.append(f"  {l['channel']:8} {l['f_hz']:7.0f} {l['level_db']:+6.1f}  {l['reason']}")
    out.append(f"\n{'written ' + str(result['written']) + ' row(s) as hypothesis' if 'written' in result else 'dry run -- --write to record them as hypotheses'}")
    ask = result.get("settle")
    if ask:
        # The run ENDS with the request, not with the rows (S-047). The rows are the answer to a
        # question nobody asked; this is the question.
        out.append(f"\nASK FOR THE MEASUREMENT THAT SETTLES THESE — {ask['rows']} row(s) on "
                   f"{len(ask['channels'])} channel(s) say a peak STAYS because nobody moved the "
                   f"microphone. Only a peak's verdict turns on that; the dips and the "
                   f"non-minimum-phase rows ask for nothing here.")
        for pattern in ask["pattern"]:
            out.append(f"  {pattern}")
        out.append(f"  {len(ask['titles'])} titles. Offer to open the round:")
        out.append(f"  {ask['capture_start']}")
        if ask["version"] == "<N>":
            out.append("  (the series number is <N> because this run read files, not REW — put "
                       "the series the positions will be taken in)")
    return "\n".join(out)


def _selftest():
    import shutil
    import tempfile

    # --- the classifier, rule by rule, on definitions ---
    peak = {"f_center": 1000.0, "width_oct": 0.33, "extremum_db": 5.0, "kind": "peak", "route": "x"}
    row, why = classify(peak)                                    # no gate, no ellipsoid
    assert row and row["kind"] == "driver_resonance" and row["action"] == "notch", (row, why)
    assert "ASSUMED" in row["why"], row["why"]                   # staying was not shown
    row, why = classify(peak, ellipsoid_feature={"stays": True, "present_in": "6/6"})
    assert row and "stays across" in row["why"]
    row, why = classify(peak, ellipsoid_feature={"stays": False, "present_in": "2/6"})
    assert row is None and "MOVES" in why, why
    row, why = classify(dict(peak, width_oct=0.08))
    assert row is None and "narrow" in why, why
    row, why = classify(dict(peak, width_oct=1.2))
    assert row is None and "tone" in why, why
    row, why = classify(dict(peak, f_center=63.0))
    assert row and row["kind"] == "modal_peak", row
    dip_lo = {"f_center": 80.0, "width_oct": 0.4, "extremum_db": -8.0, "kind": "dip", "route": "x"}
    row, why = classify(dip_lo)
    assert row and row["kind"] == "cabin_null" and row["action"] == "no_boost", row
    row, why = classify(dict(dip_lo, f_center=2500.0))
    assert row is None and "position" in why, why

    class _Gate:                                                 # the gate's contract, not its maths
        def __init__(self, v): self.v = v
        def in_scope(self, f): return True
        def check(self, f, q): return self.v, 0.0, None
    row, why = classify(peak, gate=_Gate("BLOCK"))
    assert row and row["kind"] == "non_min_phase" and row["action"] == "no_boost", row
    row, why = classify(peak, gate=_Gate("WARN"))
    assert row and row["action"] == "leave", row
    row, why = classify(peak, gate=_Gate("ALLOW"))
    assert row and row["action"] == "notch" and "minimum-phase" in row["why"], row
    assert abs(q_of_width(1 / 3) - 4.36) < 0.05, q_of_width(1 / 3)   # 1/3 oct ~ Q 4.4 (bandwidth identity)

    # --- end to end on path_check's synthetic set: a planted +5 dB Q4 resonance on m-L is found,
    #     written for m-L only, and the ledger rejects nothing it wrote ---
    import path_check
    tmp = tempfile.mkdtemp(prefix="flaw_map_")
    try:
        solos = os.path.join(tmp, "set1")
        path_check._make_capture_set(solos, chains=None, protectives=True, resonance=("m-L", 1000.0, 5.0, 4.0))
        proj = os.path.join(tmp, "proj")
        os.makedirs(proj)
        pj = _project.Project(proj)
        pj.save(pj.load())                                       # a fresh, valid project.json
        r = run(proj, solos, write=True)
        mine = [x for x in r["rows"] if x["channels"] == ["m-L"] and abs(math.log2(x["f_hz"] / 1000)) < 0.2]
        assert mine and mine[0]["kind"] == "driver_resonance" and mine[0]["action"] == "notch", r["rows"]
        assert mine[0]["status"] == "hypothesis" and mine[0]["evidence"], mine[0]
        others = [x for x in r["rows"] if x["channels"] != ["m-L"] and x["kind"] == "driver_resonance"]
        assert not others, ("a resonance planted on m-L must not appear on another driver", others)
        assert r.get("written") == len(r["rows"])
        saved = pj.load()["acoustics"]["flaws"]
        assert any(abs(math.log2(e["f_hz"] / 1000)) < 0.2 and e["channels"] == ["m-L"] for e in saved), saved
        # running it again REPLACES the row instead of adding a twin (add_flaw's own rule)
        run(proj, solos, write=True)
        again = [e for e in pj.load()["acoustics"]["flaws"] if e["channels"] == ["m-L"] and abs(math.log2(e["f_hz"] / 1000)) < 0.2]
        assert len(again) == 1, again

        # --- skill #35: the same set, where a Phase-0 round leaves it -- IN REW (the stub serves the
        #     very impulses above), with what was in each chain from the round's own record ---
        import rew_api
        import rew_stub
        state_dir = os.path.join(_HERE, "state")
        if state_dir not in sys.path:
            sys.path.insert(0, state_dir)
        from process import Process
        grid = P.grid(20, 20000, 96)
        from_files = P.load_solos_dir(solos, grid)
        codes = sorted(c for c in from_files if "+" not in c and c != "ALL")
        rew_proj = os.path.join(tmp, "proj_rew")
        os.makedirs(rew_proj)
        rp = _project.Project(rew_proj)
        rp.save(rp.load())
        url, server = rew_stub.serve(rew_stub.measurements_from_v7_dir(solos, "1"))
        saved_url = rew_api.BASE_URL
        try:
            rew_api.BASE_URL = url
            try:
                run(rew_proj, rew_ver="1", channels=codes)
                raise AssertionError("--rew ran with no capture round on record")
            except SystemExit as refusal:
                assert "no capture round on record for _1" in str(refusal), refusal
            proc = Process(os.path.join(rew_proj, "process"))
            proc.start_capture("1", expected=[f"{c}_1 (sw)" for c in codes], phase="0")
            for code in codes:
                legs = from_files[code][1].get("protective")
                proc.set_protective(code, legs if legs and any(legs.get(k) for k in ("hp", "lp")) else "OFF")
            via_rew = run(rew_proj, rew_ver="1", channels=codes)
        finally:
            rew_api.BASE_URL = saved_url
            server.shutdown()
        found = [x for x in via_rew["rows"] if x["channels"] == ["m-L"] and abs(math.log2(x["f_hz"] / 1000)) < 0.2]
        assert found and found[0]["kind"] == "driver_resonance" and found[0]["evidence"] == ["m-L_1 (sw)"], via_rew["rows"]
        same = lambda rows: sorted((x["channels"][0], x["kind"], x["action"], round(math.log2(x["f_hz"]), 1)) for x in rows)
        assert same(via_rew["rows"]) == same(r["rows"]), (same(via_rew["rows"]), same(r["rows"]))
        assert not via_rew["refused"], via_rew["refused"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # -- S-047: a run that produced ASSUMED rows ends with the REQUEST ---------------------------
    # Fails on the old code at the first line: `settling_request` did not exist, and the 43 rows
    # `classify` stamped as assumed were computed and carried nowhere.
    ask = settling_request([
        {"channels": ["m-L"], "kind": "driver_resonance", "why": "a peak of +6 dB, " + ASSUMED_NOTE},
        {"channels": ["tw-R"], "kind": "modal_peak", "why": "x " + ASSUMED_NOTE},
        {"channels": ["w-L"], "kind": "cabin_null", "why": "a dip below Schroeder: not the mic"},
    ], 49)
    assert ask["channels"] == ["m-L", "tw-R"], ask          # only a PEAK's verdict turns on it
    assert ask["rows"] == 2 and len(ask["titles"]) == 18, ask
    assert ask["pattern"] == ["m-L p1..p9_49 (sw)", "tw-R p1..p9_49 (sw)"], ask
    assert '"m-L p1_49 (sw)"' in ask["capture_start"] and "capture-start 49" in ask["capture_start"]
    # A map with nothing assumed asks for nothing -- the request is not a habit.
    assert settling_request([{"channels": ["w-L"], "why": "a dip below Schroeder"}]) is None
    # Without a series number the titles say so rather than inventing one.
    assert settling_request([{"channels": ["m-L"], "why": ASSUMED_NOTE}])["version"] == "<N>"
    # The phase gate reads this exact sentence back out of the WRITTEN rows, so the two copies of
    # it are held together here: a silent drift would stop the gate firing.
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "_flawmap_process",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "process.py"))
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    assert _mod._ASSUMED_NOTE == ASSUMED_NOTE, (_mod._ASSUMED_NOTE, ASSUMED_NOTE)

    print("selftest OK -- every classifier rule on definitions (stays/moves, narrow, tone, Schroeder, "
          "gate BLOCK/WARN/ALLOW); the planted 1 kHz resonance is written for m-L alone as a "
          "hypothesis with evidence, and a second run replaces rather than duplicates it; the same set "
          "read from REW (--rew) with the round's protective record gives the same rows, and with no "
          "round on record it refuses; a run with ASSUMED rows ends with the REQUEST -- the peak "
          "channels, `<ch> p1..p9_<N> (sw)` and the capture-start line -- and the phase gate reads "
          "the same sentence back (S-047)")
    return 0


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the acoustic flaw map, proposed from the measurements")
    ap.add_argument("--project", required=True)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--solos", metavar="DIR", help="v7 solos (protectives marked in the files)")
    source.add_argument("--rew", metavar="N", help="the round's solos in REW, `<code>_N (sw)` (skill #35)")
    ap.add_argument("--channels", metavar="a,b", help="with --rew: the codes to read (default: the glossary's active channels)")
    ap.add_argument("--process", metavar="DIR", help="with --rew: the process dir holding the round (default: <project>/process)")
    ap.add_argument("--ellipsoid", metavar="DIR", help="v7 positions `<code>-pN.json` -- stays/moves")
    ap.add_argument("--write", action="store_true", help="record the rows (as hypotheses) in project.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    channels = [c.strip() for c in args.channels.split(",") if c.strip()] if args.channels else None
    r = run(args.project, args.solos, args.ellipsoid, args.write, rew_ver=args.rew, channels=channels,
            process_dir=args.process)
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else render(r))
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
