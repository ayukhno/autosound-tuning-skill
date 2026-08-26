#!/usr/bin/env python3
"""path_check -- the virtual-first path END TO END, on synthetic drivers nobody measured.

Every module has its own selftest; none of them checks the SEAM between two commands, and that is
where the path broke on its first dry run (2026-08-26): a v7 file read one way by `predict` and
another by `verify_prediction`, a name the sheet prescribes and the grammar refuses, a search that
finds a beautiful score one cycle off. So this file walks the whole path the way a tuner does --
through the real command-line entry points, in a temporary project, against drivers whose
arrivals, polarities and protectives are DEFINED here -- and asserts the answers the definitions
imply. No project data, no REW, no network.

    python3 rew_tool/path_check.py --selftest      (what scripts/run-selftests.sh runs)

What is walked, and what would fail if the seam broke:

  -1  project + profile + ledger v_001 -> `contract.py check` is clean
   0  a capture round with protective marks; v7 solos WITH the protectives in the recording;
      the session probe pairs the controls and reads the drift
  1   `predict --baseline`: the protectives come OUT (a flat driver reads flat again);
      `predict --align`: the defined arrivals come back as delays on the DSP's grid, the one
      driver wired backwards comes back INV, nothing arrives early
  2   the proposal banks through `apply.propose` (v_002, sheet in samples), an EQ band through a
      second proposal (v_003), `eq_export` renders it; the prediction of v_003 sums clean
  3   `verify_prediction --entry` on `_2` solos taken WITH the tune: an entry error (a delay typed
      10 ms off, a corner typed an octave off) is CHECK by name; the clean set is ENTRY OK; the
      junction verdict is TRUSTED on clean pair sums and NOT trusted at the one pair moved 0.6 ms
  4   `listening-verdict` writes, `listening-verdicts` reads it back
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_STATE = os.path.join(_HERE, "state")
if _STATE not in sys.path:
    sys.path.insert(0, _STATE)

import analysis as _analysis  # noqa: E402
import dsp_math  # noqa: E402
import dsp_profile as _dp  # noqa: E402
import predict as P  # noqa: E402
import project as _project  # noqa: E402
import resonalyze_ir as _ir  # noqa: E402
import verify as _verify  # noqa: E402
import apply as _apply  # noqa: E402
import state as _state  # noqa: E402

FS = 96000
PY = sys.executable

# ---------------------------------------------------------------- the definitions
# Arrival of each driver at the seat, in CAPTURE samples (integers, so a synthetic impulse is one
# sample and the answer has no sub-sample ambiguity); the polarity it is WIRED with; the
# protective HPF that was in the chain when the `_1` solos were taken.
DRIVERS = {
    #  code   arrival  wired  protective
    "sw":   (768,  +1, None),
    "w-L":  (96,   +1, None),
    "w-R":  (138,  +1, None),
    "m-L":  (156,  +1, {"hz": 100.0, "family": "LR", "slopeDbPerOct": 24}),
    "m-R":  (184,  -1, {"hz": 100.0, "family": "LR", "slopeDbPerOct": 24}),   # wired backwards
    "tw-L": (150,  +1, {"hz": 1000.0, "family": "LR", "slopeDbPerOct": 24}),
    "tw-R": (180,  +1, {"hz": 1000.0, "family": "LR", "slopeDbPerOct": 24}),
}
# The design at the desk: Linkwitz-Riley 24 everywhere, so an in-phase junction sums to 0 dB and the
# ideal delay is exactly the arrival difference.
DESIGN = {
    "sw":   {"hp": "OFF", "lp": {"f": 80, "type": "LR", "slope": 24}},
    "w-L":  {"hp": {"f": 80, "type": "LR", "slope": 24}, "lp": {"f": 300, "type": "LR", "slope": 24}},
    "w-R":  {"hp": {"f": 80, "type": "LR", "slope": 24}, "lp": {"f": 300, "type": "LR", "slope": 24}},
    "m-L":  {"hp": {"f": 300, "type": "LR", "slope": 24}, "lp": {"f": 3000, "type": "LR", "slope": 24}},
    "m-R":  {"hp": {"f": 300, "type": "LR", "slope": 24}, "lp": {"f": 3000, "type": "LR", "slope": 24}},
    "tw-L": {"hp": {"f": 3000, "type": "LR", "slope": 24}, "lp": "OFF"},
    "tw-R": {"hp": {"f": 3000, "type": "LR", "slope": 24}, "lp": "OFF"},
}
ROLES = {"sw": "sub", "w-L": "woofer", "w-R": "woofer", "m-L": "midrange", "m-R": "midrange",
         "tw-L": "tweeter", "tw-R": "tweeter"}


def _fail(msg):
    raise AssertionError(msg)


def _run(*args, env=None, ok=(0,)):
    """Run a rew_tool command line; return (rc, stdout+stderr). Fails loudly on an unexpected rc."""
    proc = subprocess.run([PY, *args], capture_output=True, text=True, env=env)
    out = proc.stdout + proc.stderr
    if ok is not None and proc.returncode not in ok:
        _fail(f"`{' '.join(os.path.basename(a) if i == 0 else a for i, a in enumerate(args))}` "
              f"returned {proc.returncode}, expected {ok}:\n{out[-2000:]}")
    return proc.returncode, out


# ---------------------------------------------------------------- synthetic measurements
def _ir_from_response(H_linear, n):
    """Time-domain IR (n samples) from a complex response on the rfft grid of n samples."""
    return np.fft.irfft(H_linear, n=n)


def _driver_response(fb, code, chain=None, protective=None, extra_delay_samples=0.0, polarity=None):
    """A flat driver at its defined arrival, wired as defined, through `chain` (the DSP as entered)
    and through `protective` (what was in the recording chain), on the linear grid `fb`."""
    arrival, wired, _ = DRIVERS[code]
    pol = wired if polarity is None else polarity
    H = pol * np.exp(-2j * np.pi * fb * (arrival + extra_delay_samples) / FS)
    if protective:
        H = H * dsp_math.xo_response(fb, protective["hz"], protective["slopeDbPerOct"], "hp",
                                     protective["family"])
    if chain is not None:
        H = H * P.chain_response(fb, chain)
    return H


def _write_v7(path, H_linear, n, *, protective, state):
    ir = _ir_from_response(H_linear, n)
    doc, _ = _ir.build_v7(ir, FS, 0.0, low_hz=20, high_hz=20000,
                          rew_source={"protectiveHighPass": protective, "protectiveState": state,
                                      "rewTitle": os.path.basename(path)[:-5]})
    _ir.write_v7(doc, path)


def _make_capture_set(directory, chains=None, protectives=True, errors=None, pairs=(),
                      all_front=False, control=None):
    """A v7 directory. `chains`: the DSP as entered (None = raw, protectives only).
    `errors`: {code: {"delay_samples": d, "hp_f": f}} deliberately mis-entered in the DSP."""
    os.makedirs(directory, exist_ok=True)
    n = 1 << 17
    fb = np.fft.rfftfreq(n, 1.0 / FS)
    errors = errors or {}
    responses = {}
    for code, (arrival, wired, prot) in DRIVERS.items():
        chain = None
        if chains is not None:
            chain = dict(chains[code])
            if code in errors and "hp_f" in errors[code]:
                chain["hp"] = dict(chain["hp"], f=errors[code]["hp_f"])
        extra = errors.get(code, {}).get("delay_samples", 0.0)
        H = _driver_response(fb, code, chain=chain, protective=prot if protectives else None,
                             extra_delay_samples=extra)
        responses[code] = H
        _write_v7(os.path.join(directory, code.replace("-", "_") + ".json"), H, n,
                  protective=(prot if protectives else None),
                  state=("raw" if (protectives and prot) else "bare"))
    if control:
        code, shift = control
        for tag, d in (("ctl1", 0.0), ("ctl3", shift)):
            H = _driver_response(fb, code, protective=DRIVERS[code][2] if protectives else None,
                                 extra_delay_samples=d)
            _write_v7(os.path.join(directory, code.replace("-", "_") + f"-{tag}.json"), H, n,
                      protective=DRIVERS[code][2] if protectives else None, state="raw")
    for lo, hi, extra_hi in pairs:
        H = responses[lo] + responses[hi] * np.exp(-2j * np.pi * fb * extra_hi / FS)
        _write_v7(os.path.join(directory, f"{lo}+{hi}".replace("-", "_") + ".json"), H, n,
                  protective=None, state="bare")
    if all_front:
        H = sum(responses[c] for c in responses)
        _write_v7(os.path.join(directory, "ALL.json"), H, n, protective=None, state="bare")
    return responses


# ---------------------------------------------------------------- the walk
def _selftest():
    root = tempfile.mkdtemp(prefix="autosound_path_")
    proj = os.path.join(root, "project")
    os.makedirs(os.path.join(proj, "process"))
    env = dict(os.environ, AUTOSOUND_PROJECT_DIR=proj)
    tool = lambda *parts: os.path.join(_HERE, *parts)  # noqa: E731

    # ---- -1 · intake: project, profile, ledger v_001 (the desk design, delays 0) ----------------
    pj = _project.Project(proj)
    data = pj.load()
    data["car"] = {"make": "Synthetic", "model": "Path", "year": 2026}
    data["dsp"] = {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S",
                   "dsp_processing_rate_hz": FS}
    data["mic"] = {"model": "synthetic", "sample_rate_hz": FS}
    data["channels"] = [{"code": c, "role": ROLES[c], "tier": "channels"} for c in DRIVERS]
    data["glossary"] = {"channels": [{"code": c, "active": True} for c in DRIVERS],
                        "pairs": {"Ws": ["w-L", "w-R"], "Ms": ["m-L", "m-R"], "TWs": ["tw-L", "tw-R"]},
                        "sides": {"L": ["w-L", "m-L", "tw-L"], "R": ["w-R", "m-R", "tw-R"]}}
    pj.save(data)
    bundled = _dp.find_bundled("Audiotec-Fischer", "Helix DSP Ultra S")
    if bundled is None:
        _fail("the bundled Helix profile is not found -- the path needs a processing rate and a delay ceiling")
    src = bundled if isinstance(bundled, str) else bundled.get("path") if isinstance(bundled, dict) and "path" in bundled else None
    if src and os.path.isfile(src):
        shutil.copy(src, os.path.join(proj, "dsp_profile.json"))
    else:
        _dp.save_profile(os.path.join(proj, "dsp_profile.json"), bundled)
    state_root = os.path.join(proj, "state")
    hist = _state.PresetHistory(state_root, "SQ", project_dir=proj)
    v1 = {"schema_version": 3, "preset": "SQ", "sample_rate": FS, "channels": {}}
    for code, legs in DESIGN.items():
        v1["channels"][code] = {"hp": legs["hp"], "lp": legs["lp"], "gain_db": 0.0, "ta_ms": 0.0,
                                "polarity": "NORM", "eq": []}
    hist.snapshot(v1, note="the desk design: crossovers, delays 0 -- before alignment")
    _state.Registry(state_root).set_active("SQ")
    rc, out = _run(tool("contract.py"), "check", proj, env=env)
    assert "OK" in out, out[-800:]

    # ---- 0 · the capture session: a round with protective marks, solos WITH the protectives in ---
    titles = [f"{c}_1 (sw)" for c in DRIVERS] + ["m-L-ctl1_1 (sw)", "m-L-ctl3_1 (sw)"]
    _run(tool("state", "process.py"), os.path.join(proj, "process"), "capture-start", "1", *titles, env=env)
    for code, (_, _, prot) in DRIVERS.items():
        if prot:
            _run(tool("state", "process.py"), os.path.join(proj, "process"), "capture-protective", code,
                 "--hp", f"{prot['hz']:g}", prot["family"], str(prot["slopeDbPerOct"]), env=env)
        else:
            _run(tool("state", "process.py"), os.path.join(proj, "process"), "capture-protective", code, "OFF", env=env)
    set1 = os.path.join(root, "set_1")
    _make_capture_set(set1, chains=None, protectives=True, control=("m-L", 0.3))
    # the session probe, on the verdicts a REW-less check can build from the files' own peaks
    verdicts = []
    for name in sorted(os.listdir(set1)):
        doc = json.load(open(os.path.join(set1, name)))
        x = list(doc["transferRealSamples"])
        imp = _analysis.analyze_impulse([i / FS for i in range(len(x))], x)   # the tool's own reader
        title = name[:-5].replace("_", "-") + "_1 (sw)"
        if "-ctl" in name:
            title = name[:-5].replace("_", "-", 1) + "_1 (sw)"      # m_L-ctl1 -> m-L-ctl1_1 (sw)
        verdicts.append({"name": title, "exists": True, "valid": True, "issues": [],
                         "stats": {"live_mean_dB": 80.0 + (5.0 if name.startswith("sw") else 0.0),
                                   "peak_dB": 0.0, "pre_ringing_dB": -60.0,
                                   "peak_time_ms": imp["peak_time_ms"], "capture_rate_hz": FS}})
    def ir_of(title):                                   # the files stand in for REW here
        stem = title.split("_1 (sw)")[0]
        stem = stem.replace("-ctl", "|ctl").replace("-", "_").replace("|ctl", "-ctl")
        path = os.path.join(set1, stem + ".json")
        return json.load(open(path))["transferRealSamples"] if os.path.isfile(path) else None
    probe = _verify.session_report(verdicts, processing_rate_hz=FS, ir_of=ir_of)
    d = probe["drift"]
    assert d and d.get("ctl3") == "m-L-ctl3_1 (sw)" and d["held"] is True and d["method"] == "xcorr" \
        and abs(d["delta_samples"] - 0.3) < 0.03, d
    assert probe["spread"]["loudest"] == "sw_1 (sw)" and abs(probe["spread"]["spread_dB"] - 5.0) < 0.01, probe["spread"]

    # ---- 1 · the desk: de-embed, then align ---------------------------------------------------
    out1 = os.path.join(root, "out1")
    _run(tool("predict.py"), "--solos", set1, "--project", proj, "--baseline", "--out", out1, env=env)
    pred1 = json.load(open(os.path.join(out1, "predicted.json")))
    f = np.asarray(pred1["freqs_hz"], float)
    for code in ("m-L", "tw-L"):
        # the protective came OUT: a flat driver x the design chain is the design chain ALONE, so
        # the predicted magnitude equals the chain's own response to within a hundredth of a dB
        # (the chain droops a tenth or two inside its passband -- that is the chain, not the
        # protective; a first draft expected a flat 0 dB and was wrong by exactly that droop)
        mag = np.asarray(pred1["channels"][code]["mag_db"], float)
        probe_f = 1000.0 if code == "m-L" else 8000.0
        k = int(np.argmin(np.abs(f - probe_f)))
        chain = P.chain_from_row(dict(DESIGN[code], gain_db=0, ta_ms=0, polarity="NORM"))
        expect = 20 * np.log10(abs(P.chain_response(np.array([f[k]]), chain)[0]))
        assert abs(mag[k] - expect) < 0.02, (code, probe_f, mag[k], expect)
    assert all(j["sum_loss_avg_db"] < -0.3 for j in pred1["junctions"]), \
        "delays 0 with these arrivals must read as mis-aligned junctions"
    out2 = os.path.join(root, "out2")
    _run(tool("predict.py"), "--solos", set1, "--project", proj, "--baseline", "--align", "--out", out2, env=env)
    delta = json.load(open(os.path.join(out2, "aligned-delta.json")))
    aligned = json.load(open(os.path.join(out2, "aligned.json")))
    step = 1000.0 / FS
    assert abs(aligned["step_ms"] - step) < 1e-9, "delays must land on the DSP's grid, from the profile's rate"
    # What the definitions imply -- and what they do NOT. A first draft expected every delay to be
    # the raw arrival difference (the sub arrives last, at 768); the tool answered 5.19 ms for w-L
    # where 7.0 was expected, and it was RIGHT: the woofer's own 300 Hz low-pass bends phase at the
    # 80 Hz junction (-44 deg there, 1.5 ms at 80 Hz), and an in-phase junction is what the design
    # asks for, not equal arrivals. So the anchors are the physics, side by side:
    #   (a) every junction sums close to perfect after alignment;
    #   (b) left and right agree: the two sides' drivers differ only in arrival (42 / 28 / 30
    #       samples), so their delays differ by exactly that, once the one driver wired backwards is
    #       taken into account -- the ENTERED polarity times the WIRED one must match across sides;
    #   (c) nothing arrives early, no answer is an alias, every delay sits on the DSP's grid.
    for st in aligned["steps"]:
        assert st["after"]["score_db"] > -0.3 and st["after"]["dip_db"] > -0.6, (st["lo"], st["hi"], st["after"])
        assert st["cycles_off"] is None or abs(st["cycles_off"]) < 0.75, (st["lo"], st["hi"], st["cycles_off"])
    got = {c: delta["channels"].get(c, {}).get("ta_ms", 0.0) for c in DRIVERS}
    entered = {c: (-1 if delta["channels"].get(c, {}).get("polarity") == "INV" else 1) for c in DRIVERS}
    for left, right in (("w-L", "w-R"), ("m-L", "m-R"), ("tw-L", "tw-R")):
        want = (DRIVERS[left][0] - DRIVERS[right][0]) * step     # the later arrival needs LESS delay
        assert abs((got[right] - got[left]) - want) <= 1.5 * step, (left, right, got[left], got[right], want)
        assert entered[left] * DRIVERS[left][1] == entered[right] * DRIVERS[right][1], \
            f"{left}/{right}: the sides must end up with the same effective polarity " \
            f"(entered x wired) -- {entered[left]}x{DRIVERS[left][1]} vs {entered[right]}x{DRIVERS[right][1]}"
    assert min(got.values()) >= 0, got
    for c, v in got.items():
        assert abs(v / step - round(v / step)) < 0.01, (c, v, "off the DSP grid")   # 4-decimal ms in the delta
    assert got["sw"] == 0.0 and all(v > 4.0 for c, v in got.items() if c != "sw"), got

    # ---- 2 · bank the proposal, add an EQ band, export it; the aligned prediction sums clean ----
    res = _apply.propose(hist, delta, note="aligned at the desk", registry=_state.Registry(state_root))
    assert res["version"] == "v_002" and "smp" in res["sheet"], res["sheet"][:400]
    res3 = _apply.propose(hist, {"channels": {"tw-L": {"eq": [{"type": "PK", "f": 5000, "gain_db": -3.0, "q": 2.0}]}}},
                          note="one hygiene band", registry=_state.Registry(state_root))
    assert res3["version"] == "v_003"
    atf = os.path.join(root, "tw-L.atf")
    rc, out = _run(tool("eq_export.py"), proj, "tw-L", "--out", atf, env=env, ok=(0, 3))
    assert "5000" in open(atf).read() and "format:" in out, out[-400:]
    out3 = os.path.join(root, "out3")
    _run(tool("predict.py"), "--solos", set1, "--project", proj, "--baseline", "--out", out3, env=env)
    pred3 = json.load(open(os.path.join(out3, "predicted.json")))
    for j in pred3["junctions"]:
        # the same physics tolerance as the align step: non-adjacent filters leave a tenth or two
        assert j["sum_loss_avg_db"] > -0.3 and j["worst_null_db"] > -2.0, j
    chains3 = P.chains_from_snapshot(hist.load())

    # ---- 3 · in the car: entry control on `_2` solos taken WITH the tune, then the sums ---------
    # (a) two entry errors: tw-R's delay typed 10 ms off, m-L's HPF typed an octave up
    set2_bad = os.path.join(root, "set_2_bad")
    _make_capture_set(set2_bad, chains=chains3, protectives=False,
                      errors={"tw-R": {"delay_samples": 960}, "m-L": {"hp_f": 600}})
    rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                   "--measured", set2_bad, "--entry", "--json", env=env, ok=(1,))
    rep = json.loads(out[out.index("{"):])
    ch = {c["channel"]: c for c in rep["channels"]}
    assert ch["tw-R"]["status"] == "CHECK" and abs(ch["tw-R"]["delay_error_ms"] - 10.0) < 0.1, ch["tw-R"]
    assert ch["m-L"]["status"] == "CHECK" and "HP 300" in (ch["m-L"]["hint"] or ""), ch["m-L"]
    assert all(ch[c]["status"] == "as designed" for c in ("sw", "w-L", "w-R", "m-R", "tw-L")), \
        {c: ch[c]["status"] for c in ch}
    assert rep["verdict"].startswith("ENTRY CHECK"), rep["verdict"]
    # (b) the clean set: ENTRY OK, and the junction verdict TRUSTED on the pair sums
    set2 = os.path.join(root, "set_2")
    pairs = [(j["lo"], j["hi"], 0.0) for j in pred3["junctions"]]
    _make_capture_set(set2, chains=chains3, protectives=False, pairs=pairs, all_front=True)
    rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                   "--measured", set2, "--entry", env=env, ok=(0,))
    assert "ENTRY OK" in out, out[-600:]
    rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                   "--measured", set2, "--json", env=env, ok=(0,))
    rep_ok = json.loads(out[out.index("{"):])
    assert rep_ok["verdict"].startswith("TRUSTED"), rep_ok["verdict"]
    assert all(j["status"] == "trusted" for j in rep_ok["junctions"]), rep_ok["junctions"]
    # (c) one pair moved 0.6 ms (the mid arrives late only in the pair): NOT trusted THERE only
    set2_moved = os.path.join(root, "set_2_moved")
    pairs_moved = [(lo, hi, (0.6e-3 * FS if (lo, hi) == ("w-L", "m-L") else 0.0)) for lo, hi, _ in pairs]
    _make_capture_set(set2_moved, chains=chains3, protectives=False, pairs=pairs_moved, all_front=True)
    rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                   "--measured", set2_moved, "--json", env=env, ok=(1,))
    rep_m = json.loads(out[out.index("{"):])
    bad = [f"{j['lo']}↔{j['hi']}" for j in rep_m["junctions"] if j["status"] == "NOT trusted"]
    assert bad == ["w-L↔m-L"], (bad, rep_m["verdict"])

    # ---- 4 · ears: one verdict written by the one writer, read back ---------------------------
    import listening as _listening
    tracks = _listening.tracks()
    chars = _listening.characteristics("en")
    tid = sorted(tracks)[0]
    cid = sorted(chars)[0]
    _run(tool("state", "process.py"), os.path.join(proj, "process"), "listening-verdict",
         "--pair", f"{tid}:{cid}:ok", "--text", "path check", "--ledger-version", "v_003", env=env)
    rc, out = _run(tool("state", "process.py"), os.path.join(proj, "process"), "listening-verdicts", env=env)
    assert tid in out and cid in out, out[-400:]

    shutil.rmtree(root, ignore_errors=True)
    print("selftest[path] OK -- the virtual-first path end to end on synthetic drivers: contract clean; "
          "protectives marked on the round and taken out of the solos (flat reads flat); the drift "
          "record pairs the controls to a tenth of a sample; --align sums every junction clean on the DSP's "
          "grid with the two sides agreeing to a sample once the backwards driver is accounted for, "
          "nothing early, no alias; the proposal banks (v_002, sheet in samples), an EQ "
          "band banks and exports; the aligned prediction sums clean; the entry control names a delay "
          "typed 10 ms off and a corner typed an octave off and passes the clean set; the junction "
          "verdict is TRUSTED on clean sums and NOT trusted at the one pair moved 0.6 ms; a listening "
          "verdict writes and reads back.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
