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
      second proposal (v_003), `eq_export` renders it; the prediction of v_003 sums clean;
      2.1: a resonance planted on one driver comes back as ONE cut in its group's package
      (`eq_propose`), banks as one version, and the prediction shows it gone
  3   `verify_prediction --entry` on `_2` solos taken WITH the tune: an entry error (a delay typed
      10 ms off, a corner typed an octave off) is CHECK by name; the clean set is ENTRY OK; the
      junction verdict is TRUSTED on clean pair sums and NOT trusted at the one pair moved 0.6 ms
  3.3 `ear_suspects` names what cuts and what booms on an MMM served by the stub; a verdict of
      "same" recorded through the one writer drops that band in the next round; round 4 is refused
  4   `listening-verdict` writes, `listening-verdicts` reads it back
"""
from __future__ import annotations

import json
import math
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


def _json_in(out):
    """The JSON object a command printed, with whatever it said on stderr around it ignored."""
    return json.JSONDecoder().raw_decode(out[out.index("{"):])[0]


def _run(*args, env=None, ok=(0,)):
    """Run a rew_tool command line; return (rc, stdout+stderr). Fails loudly on an unexpected rc.

    The command line is REAL either way -- the script's own `__main__` block, its own argument
    parsing, its own exit code, its own printed output. What differs is the interpreter:

      * in-process (`runpy`, the default): the script runs under this interpreter with `sys.argv`
        set and stdout/stderr captured. Every tool here ends in `sys.exit(main())`, so the exit code
        is the `SystemExit` it raises. This saves the ~0.6 s numpy/scipy start-up per call, which
        was 22 of this walk's 31 seconds (measured 2026-08-27; 36 calls).
      * a fresh process, ONLY when `env` carries `REW_API_URL`: `rew_api.BASE_URL` is read at
        import, so a tool that must see the stub's address needs an interpreter that has not
        imported `rew_api` yet. Running that stage in-process would silently talk to localhost:4735
        -- the exact quiet failure this walk exists to catch.

    A tool that raises anything other than `SystemExit` in-process is reported as rc 1 with its
    traceback in `out`, which is what the subprocess version would have shown.
    """
    if env and "REW_API_URL" in env:
        proc = subprocess.run([PY, *args], capture_output=True, text=True, env=env)
        rc, out = proc.returncode, proc.stdout + proc.stderr
    else:
        import contextlib
        import io
        import runpy
        import traceback
        script, argv = args[0], [str(a) for a in args[1:]]
        buf = io.StringIO()
        saved_argv, saved_env = sys.argv, dict(os.environ)
        if env:
            os.environ.update(env)
        sys.argv = [script, *argv]
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    runpy.run_path(script, run_name="__main__")
                    rc = 0
                except SystemExit as e:
                    rc = 0 if e.code in (None, 0) else (e.code if isinstance(e.code, int) else 1)
                except Exception:                        # a crash: rc 1, traceback in the output
                    traceback.print_exc()
                    rc = 1
        finally:
            sys.argv = saved_argv
            os.environ.clear()
            os.environ.update(saved_env)
        out = buf.getvalue()
    if ok is not None and rc not in ok:
        _fail(f"`{' '.join(os.path.basename(a) if i == 0 else str(a) for i, a in enumerate(args))}` "
              f"returned {rc}, expected {ok}:\n{out[-2000:]}")
    return rc, out


# ---------------------------------------------------------------- synthetic measurements
def _ir_from_response(H_linear, n):
    """Time-domain IR (n samples) from a complex response on the rfft grid of n samples."""
    return np.fft.irfft(H_linear, n=n)


_XO_CACHE = {}


def _xo(fb, corner, order, kind, family):
    """`dsp_math.xo_response` memoised on (the GRID's bytes, corner, order, kind, family): the five
    capture sets of this walk use one grid and two dozen filters, and recomputing them was 2.7 s.

    The key hashes the grid's contents, not its length. The first draft keyed on `len(fb)`, and
    the walk's own probes call `driver_shape(np.array([f]))` on one-point grids -- so the value at
    1000 Hz, cached for m-L, came back for the tweeter at 8000 Hz: a true number from the right
    function for the wrong frequency, and it failed a real assertion, which is the only reason it
    was found. Hashing 65537 floats costs well under a millisecond."""
    import hashlib
    key = (hashlib.blake2b(np.ascontiguousarray(fb).tobytes(), digest_size=16).digest(),
           float(corner), int(order), kind, family)
    h = _XO_CACHE.get(key)
    if h is None:
        h = _XO_CACHE[key] = dsp_math.xo_response(fb, corner, order, kind, family)
    return h


def driver_shape(fb):
    """Every synthetic driver's own response: a gentle band (40 Hz LR12 up, 16 kHz LR12 down) --
    not flat, because the capture gate rightly calls a flat response a loopback or a placeholder."""
    return _xo(fb, 40.0, 12, "hp", "LR") * _xo(fb, 16000.0, 12, "lp", "LR")


def _driver_response(fb, code, chain=None, protective=None, extra_delay_samples=0.0, polarity=None):
    """A driver (`driver_shape`) at its defined arrival, wired as defined, through `chain` (the DSP
    as entered) and through `protective` (what was in the recording chain), on the linear grid `fb`."""
    arrival, wired, _ = DRIVERS[code]
    pol = wired if polarity is None else polarity
    H = pol * driver_shape(fb) * np.exp(-2j * np.pi * fb * (arrival + extra_delay_samples) / FS)
    if protective:
        H = H * _xo(fb, protective["hz"], protective["slopeDbPerOct"], "hp",
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
                      all_front=False, control=None, resonance=None):
    """A v7 directory. `chains`: the DSP as entered (None = raw, protectives only).
    `errors`: {code: {"delay_samples": d, "hp_f": f}} deliberately mis-entered in the DSP."""
    os.makedirs(directory, exist_ok=True)
    # 65536 samples = 0.68 s at 96 kHz. A synthetic driver is a handful of filters and decays in
    # milliseconds, so the record is long by a factor of a hundred either way; halving it from
    # 1 << 17 took 3.5 s of float formatting out of the walk (51 files, 2026-08-27) and changed
    # no assertion -- each of which is anchored on a definition, not on the record's length.
    n = 1 << 16
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
        if resonance and resonance[0] == code:                 # a driver's own resonance (min-phase)
            _, f0, g, q = resonance
            H = H * dsp_math.peq_response(fb, "PK", f0, g, q)
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
        # the protective came OUT: the driver x the design chain is the driver's own shape x the
        # chain, to within a hundredth of a dB -- nothing of the protective is left in it
        # (the chain droops a tenth or two inside its passband -- that is the chain, not the
        # protective; a first draft expected a flat 0 dB and was wrong by exactly that droop)
        mag = np.asarray(pred1["channels"][code]["mag_db"], float)
        probe_f = 1000.0 if code == "m-L" else 8000.0
        k = int(np.argmin(np.abs(f - probe_f)))
        chain = P.chain_from_row(dict(DESIGN[code], gain_db=0, ta_ms=0, polarity="NORM"))
        expect = 20 * np.log10(abs(P.chain_response(np.array([f[k]]), chain)[0] * driver_shape(np.array([f[k]]))[0]))
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
    # ---- 1.4 · levels read off the measurement: refuses without the knob assertion, then gives
    #      cut-only offsets with the quietest driver at 0 -- every driver here was "swept" at the
    #      same level, so the offsets are the drivers' own sensitivities, not a knob ------------
    rc, out = _run(tool("level_offsets.py"), "--solos", set1, "--ver", "1", "--project", proj, env=env, ok=(3,))
    assert "refusing" in out and "knob" in out, out[-300:]
    rc, out = _run(tool("level_offsets.py"), "--solos", set1, "--ver", "1", "--project", proj,
                   "--levels-fixed", env=env)
    offs = [float(line.split()[3]) for line in out.splitlines()
            if line.split() and line.split()[0] in DRIVERS and len(line.split()) > 3]
    assert len(offs) == len(DRIVERS), (offs, out[-600:])
    assert max(offs) == 0.0 and all(o <= 0.0 for o in offs), ("cut-only, quietest = 0", offs)

    # ---- 1.5 · a setup transcribed from the DSP's screens: validated against the profile, refused
    #      by name when a value is one the DSP cannot hold, and carried with provenance ---------
    transcription = {"preset": "SQ", "source": "path_check screens", "read_on": "2026-08-26",
                     "channels": {c: {"hp": DESIGN[c]["hp"], "lp": DESIGN[c]["lp"], "gain_db": 0.0,
                                      "ta_ms": 0.0, "polarity": "NORM", "eq": []} for c in DRIVERS}}
    tpath = os.path.join(root, "transcription.json")
    json.dump(transcription, open(tpath, "w"))
    rc, out = _run(tool("setup_import.py"), proj, tpath, env=env)
    assert "would bank" in out and "verified_by_file=False" in out, out[-400:]
    transcription["channels"]["m-L"]["ta_ms"] = 2.355                    # off the 0.01 ms grid
    json.dump(transcription, open(tpath, "w"))
    rc, out = _run(tool("setup_import.py"), proj, tpath, "--write", env=env, ok=(3,))
    assert "2.355" in out and "grid" in out, out[-400:]
    assert hist.head() == "v_003", ("a refused import must not bank", hist.head())

    out3 = os.path.join(root, "out3")
    _run(tool("predict.py"), "--solos", set1, "--project", proj, "--baseline", "--out", out3, env=env)
    pred3 = json.load(open(os.path.join(out3, "predicted.json")))
    for j in pred3["junctions"]:
        # the same physics tolerance as the align step: non-adjacent filters leave a tenth or two
        assert j["sum_loss_avg_db"] > -0.3 and j["worst_null_db"] > -2.0, j
    chains3 = P.chains_from_snapshot(hist.load())

    # ---- 2.1 · EQ as packages: a driver resonance planted on m-L is proposed as ONE cut in the
    #      mids' resonance package, banked as one version, and the prediction shows it gone ------
    set1r = os.path.join(root, "set_1r")
    _make_capture_set(set1r, chains=None, protectives=True, resonance=("m-L", 1000.0, 5.0, 4.0))
    house = os.path.join(_HERE, "..", "references", "patterns", "target-curves", "curves", "SQ-Comp-Ref_0db_REW.txt")
    out_eq = os.path.join(root, "out_eq")
    rc, out = _run(tool("eq_propose.py"), "--project", proj, "--solos", set1r, "--house", house,
                   "--out", out_eq, "--json", env=env)
    pkgs = {p["id"]: p for p in json.loads(out[out.index("["):out.rindex("]") + 1])}
    assert len([p for p in pkgs.values() if p.get("needed")]) <= 5, [p["id"] for p in pkgs.values() if p.get("needed")]
    rm = pkgs["res:mid"]
    assert len(rm["bands"]["m-L"]) == 1 and not rm["bands"]["m-R"], rm["bands"]
    b = rm["bands"]["m-L"][0]
    assert abs(math.log2(b["f"] / 1000.0)) < 1 / 6 and -5.5 <= b["gain_db"] <= -2.0, b
    assert os.path.isfile(os.path.join(out_eq, "eq-res-mid.json"))
    res4 = _apply.propose(hist, json.load(open(os.path.join(out_eq, "eq-res-mid.json"))),
                          note="resonance package", registry=_state.Registry(state_root))
    assert res4["version"] == "v_004", res4["version"]
    out4 = os.path.join(root, "out4")
    _run(tool("predict.py"), "--solos", set1r, "--project", proj, "--baseline", "--out", out4, env=env)
    pred4 = json.load(open(os.path.join(out4, "predicted.json")))
    mag4 = np.asarray(pred4["channels"]["m-L"]["mag_db"], float)
    k1k = int(np.argmin(np.abs(f - 1000.0)))
    chain_m = P.chain_from_row(dict(DESIGN["m-L"], gain_db=0, ta_ms=0, polarity="NORM"))
    expect = 20 * np.log10(abs(P.chain_response(np.array([f[k1k]]), chain_m)[0] * driver_shape(np.array([f[k1k]]))[0]))
    assert abs(mag4[k1k] - expect) < 1.0, ("the resonance should be cut to within 1 dB", mag4[k1k], expect)
    hist.revert("v_003", note="path_check: back to the state the `_2` sets were made under")

    # ---- 3 · in the car: entry control on `_2` solos taken WITH the tune, then the sums ---------
    # (a) two entry errors: tw-R's delay typed 10 ms off, m-L's HPF typed an octave up
    set2_bad = os.path.join(root, "set_2_bad")
    _make_capture_set(set2_bad, chains=chains3, protectives=False,
                      errors={"tw-R": {"delay_samples": 960}, "m-L": {"hp_f": 600}})
    rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                   "--measured", set2_bad, "--entry", "--json", env=env, ok=(1,))
    rep = _json_in(out)
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
    rep_ok = _json_in(out)
    assert rep_ok["verdict"].startswith("TRUSTED"), rep_ok["verdict"]
    assert all(j["status"] == "trusted" for j in rep_ok["junctions"]), rep_ok["junctions"]
    # (c) one pair moved 0.6 ms (the mid arrives late only in the pair): NOT trusted THERE only
    set2_moved = os.path.join(root, "set_2_moved")
    pairs_moved = [(lo, hi, (0.6e-3 * FS if (lo, hi) == ("w-L", "m-L") else 0.0)) for lo, hi, _ in pairs]
    _make_capture_set(set2_moved, chains=chains3, protectives=False, pairs=pairs_moved, all_front=True)
    rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                   "--measured", set2_moved, "--json", env=env, ok=(1,))
    rep_m = _json_in(out)
    bad = [f"{j['lo']}↔{j['hi']}" for j in rep_m["junctions"] if j["status"] == "NOT trusted"]
    assert bad == ["w-L↔m-L"], (bad, rep_m["verdict"])

    import listening as _listening
    tid = sorted(_listening.tracks())[0]
    cid = sorted(_listening.characteristics("en"))[0]

    # ---- 3r · the same in-car commands THROUGH REW (the stub serving the same impulses) ---------
    # `capture-check --session`, `predict --rew`, `verify_prediction --rew` read REW's API; the stub
    # answers the four endpoints they use from the very files above, so the REW branch of each is
    # walked here and must agree with the file branch.
    import rew_stub as _stub
    served = []
    for directory, ver in ((set1, "1"), (set2, "2"), (set2_bad, "3")):
        served.extend(_stub.measurements_from_v7_dir(directory, ver))
    # ...and an MMM of the whole front with a cabin mode that booms and a peak that cuts (3.3)
    f_rta = np.arange(20.0, 20000.0, 5.0)
    mmm = (75.0 - 1.0 * np.log2(f_rta / 1000.0)
           + 20 * np.log10(np.abs(dsp_math.peq_response(f_rta, "PK", 63.0, 6.0, 5.0)
                                  * dsp_math.peq_response(f_rta, "PK", 3200.0, 4.5, 3.0))))
    served.append(_stub.Measurement("ALL_2 (rta)", rta=(f_rta, mmm)))
    url, server = _stub.serve(served)
    env_rew = dict(env, REW_API_URL=url)
    try:
        rc, out = _run(tool("state", "process.py"), os.path.join(proj, "process"), "capture-check", "--session",
                       env=env_rew, ok=(0,))
        assert "HELD" in out and "cross-correlation" in out and "UNUSABLE" not in out, out[-900:]
        assert f"{len(titles)}/{len(titles)}" in out, out[-300:]
        out_rew = os.path.join(root, "out_rew")
        _run(tool("predict.py"), "--rew", "--ver", "1", "--project", proj, "--baseline",
             "--process", os.path.join(proj, "process"), "--out", out_rew, env=env_rew)
        pred_rew = json.load(open(os.path.join(out_rew, "predicted.json")))
        for code in pred3["channels"]:                       # HEAD is v_003 now: compare like with like
            a = np.asarray(pred3["channels"][code]["mag_db"], float)
            b = np.asarray(pred_rew["channels"][code]["mag_db"], float)
            live = a > a.max() - 40.0
            d = np.where(live, np.abs(a - b), 0.0)
            k = int(np.argmax(d))
            assert d[k] < 0.02, (code, "file vs REW branch of predict disagree", round(float(f[k])), a[k], b[k])
        rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                       "--rew", "--ver", "2", "--entry", env=env_rew, ok=(0,))
        assert "ENTRY OK" in out, out[-600:]
        rc, out = _run(tool("verify_prediction.py"), "--predicted", os.path.join(out3, "predicted.json"),
                       "--rew", "--ver", "3", "--entry", "--json", env=env_rew, ok=(1,))
        rep_r = _json_in(out)
        chr_ = {c["channel"]: c for c in rep_r["channels"]}
        assert chr_["tw-R"]["status"] == "CHECK" and abs(chr_["tw-R"]["delay_error_ms"] - 10.0) < 0.1, chr_["tw-R"]
        assert chr_["m-L"]["status"] == "CHECK" and "HP 300" in (chr_["m-L"]["hint"] or ""), chr_["m-L"]

        # ---- 3.3 · what cuts and what booms, from the MMM, settled by A/B -------------------------
        rc, out = _run(tool("ear_suspects.py"), "--rew", "--title", "ALL_2 (rta)", "--json", env=env_rew)
        sus = _json_in(out)["suspects"]
        classes = {s["class"]: s for s in sus}
        assert "harsh" in classes and "boom" in classes, [s["id"] for s in sus]
        assert sus[0]["class"] == "harsh", "the ear's region ranks first"
        assert abs(classes["boom"]["f_hz"] - 63) < 6 and abs(classes["harsh"]["f_hz"] - 3200) < 200, classes
        assert classes["harsh"]["correction"]["gain_db"] < 0 and classes["harsh"]["listen"][0] == "c08"
        # the tuner A/B'd the harsh band and heard no difference: recorded through the one writer,
        # the next round leaves it out and the boom leads
        _run(tool("state", "process.py"), os.path.join(proj, "process"), "listening-verdict",
             "--pair", f"{tid}:c08:ok", "--text", f"suspect:{classes['harsh']['id']}=same",
             "--ledger-version", "v_003", env=env)
        rc, out = _run(tool("ear_suspects.py"), "--rew", "--title", "ALL_2 (rta)", "--json",
                       "--process", os.path.join(proj, "process"), "--round", "2", env=env_rew)
        r2 = _json_in(out)
        assert classes["harsh"]["id"] not in [s["id"] for s in r2["suspects"]] and r2["suspects"][0]["class"] == "boom", r2["suspects"]
        rc, out = _run(tool("ear_suspects.py"), "--rew", "--title", "ALL_2 (rta)", "--round", "4", env=env_rew, ok=(3,))
        assert "three rounds is the limit" in out, out[-300:]

        # ---- refusals: a check whose input is missing FAILS by name, never reads as no objection --
        # (a) solos asked from REW for a round nobody opened: refused, and the rounds on record named
        rc, out = _run(tool("predict.py"), "--rew", "--ver", "9", "--project", proj, "--baseline",
                       "--process", os.path.join(proj, "process"), env=env_rew, ok=None)
        assert rc != 0 and "no capture round on record for _9" in out and "cap_" in out, (rc, out[-500:])
        # (b) a route to a virtual row the ledger does not have: refused by that name
        rc, out = _run(tool("predict.py"), "--solos", set1, "--project", proj, "--baseline",
                       "--route", "VXX=w-L", env=env, ok=None)
        assert rc != 0 and "VXX" in out, (rc, out[-400:])
        # (c) a profile with no processing rate: the alignment SAYS its grid is not the DSP's
        noproj = os.path.join(root, "project_norate")
        shutil.copytree(proj, noproj)
        prof_path = os.path.join(noproj, "dsp_profile.json")
        prof = json.load(open(prof_path))
        inner = prof.get("dsp_profile", prof)
        inner.pop("dsp_processing_rate_hz", None)
        inner.pop("sample_rate_hz", None)
        json.dump(prof, open(prof_path, "w"))
        rc, out = _run(tool("predict.py"), "--solos", set1, "--project", noproj, "--baseline", "--align",
                       env=dict(env, AUTOSOUND_PROJECT_DIR=noproj), ok=(0,))
        assert "no processing rate known" in out and "0.0100 ms" in out, out[-600:]
    finally:
        server.shutdown()

    # ---- 4 · ears: one verdict written by the one writer, read back ---------------------------
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
          "band banks and exports; the aligned prediction sums clean; a planted resonance is proposed as one "
          "package cut and predicted gone; the entry control names a delay "
          "typed 10 ms off and a corner typed an octave off and passes the clean set; the junction "
          "verdict is TRUSTED on clean sums and NOT trusted at the one pair moved 0.6 ms; the same "
          "capture-check / predict --rew / verify_prediction --rew through a REW stub agree with the "
          "file branch; a round nobody opened, a route to a virtual row the ledger lacks, and a profile "
          "with no processing rate are refused or said by name; the ear suspects on an MMM are named and "
          "classed, a 'same' verdict drops one for the next round, a fourth round is refused; a listening "
          "verdict writes and reads back.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
