#!/usr/bin/env python3
"""Full-state prediction: the solos on ONE time base x the ledger's chains -> what the mic would hear.

The `virtual-first` path's engine (the user's ruling, 2026-08-24): measure every driver once, on a
loopback-referenced time base, then design the whole DSP setup at the desk. Sound pressure adds
linearly, so at the microphone position the sum of the individually measured drivers, each passed
through its own DSP chain, IS what the microphone would record -- not an approximation of it.
Resonalyze's Virtual DSP rests on the same fact; this is the method's own reading of it, on the
method's own ledger, with the method's own filter models (hardware-verified on the Helix).

What it produces, per run:

  * every channel's PROCESSED response -- solo x gain x polarity x delay x crossover x EQ;
  * the per-side sums (L, R) and the whole-front sum (ALL), as the complex sum of the members;
  * every junction the ledger's crossovers imply, read with BOTH rulers side by side --
    the Resonalyze sum-loss (average / 1/6-oct dip / score) and the method's own worst null --
    because neither replaces the other (the same ruling);
  * the L-R level difference per band, the level half of the image.

It PREDICTS and stops. Whether the prediction is to be believed is `verify.py`'s question -- the
delta against a measurement taken on the same terms -- and what to change is the tuner's.

Where the solos come from, and the one thing they must share:

  * Resonalyze v7 files (`--solos DIR`): `transferRealSamples` with sample 0 = the loopback
    reference, so every file is already on one absolute base. `resonalyze_ir.py` writes them from
    REW; Resonalyze writes them itself.
  * REW, live (`--rew --ver N`): `<ch>_N (sw)` through `rew_api.get_impulse_response`, whose
    `startTime` puts sample 0 at its absolute time. Refused unless the capture is on the loopback
    base with no timing offset -- a solo on another base is a driver that appears to have moved.

The state comes from the project's ledger (`--project DIR`, the active slot's HEAD, schema v3 rows)
or, for reproducing an experiment, from an anchors-style JSON (`--state-json FILE`, the
`{hpf, lpf, delay_ms, inverted, gain_db, peq}` shape `sound_AutoSci` used for stage 0).

Deliberately NOT modelled, and said so in the output rather than silently skipped:

  * a vendor phase ANGLE (`phase_deg`) -- one control of one vendor (`helix-phase-allpass.md`);
    an all-pass belongs in `eq` as `APF1`/`APF2`, which IS modelled;
  * the virtual tier -- its routing onto outputs is a project fact this module does not hold;
    the output tier is what stage 0 validated and what this predicts;
  * centre and rear (`c`, `r-*`) -- Phase 5 work; they are loaded if present and left out of the
    sums, and the report names them.

Stage 0 of the plan (2026-08-21) validated exactly this arithmetic against the car: junction
interference matched to 0.3-0.45 dB in band means, and the predictor identified the car's sub state
blind. The self-test below anchors on facts about waves; the reproduction of stage 0 on the real
set-02 files is a separate script, since it needs the measurements.

numpy + scipy (via `dsp_math`).
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp_math  # noqa: E402

PPO_DEFAULT = 96
FMIN_DEFAULT, FMAX_DEFAULT = 20.0, 20000.0
LR_BANDS = ((20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
            (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000))


class PredictError(ValueError):
    pass


# ---------------------------------------------------------------- grid & helpers
def grid(fmin=FMIN_DEFAULT, fmax=FMAX_DEFAULT, ppo=PPO_DEFAULT):
    n = int(round(math.log2(fmax / fmin) * ppo)) + 1
    return np.geomspace(fmin, fmax, n)


def _db(h):
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))


def _side_of(code):
    c = code.lower()
    if c.endswith("-l") or c.endswith("_l"):
        return "L"
    if c.endswith("-r") or c.endswith("_r"):
        return "R"
    if c.startswith(("sw", "sub")):
        return "mono"
    return "other"          # centre / rear: Phase 5, left out of the front sums


def _edge_f(edge):
    if isinstance(edge, dict):
        f = edge.get("f")
        return float(f) if f not in (None, "OFF", "off") else None
    return None


def canon(code):
    """`w_L` (file names) and `w-L` (ledger codes) are one channel."""
    return str(code).replace("_", "-")


# ---------------------------------------------------------------- chains
def chain_from_row(row):
    """A schema-v3 ledger row -> the chain this module applies. Refuses what it cannot model."""
    row = row or {}
    if row.get("mute") or row.get("off"):
        return {"muted": True}
    if row.get("phase_deg") not in (None, 0, 0.0):
        raise PredictError(
            f"phase_deg={row['phase_deg']!r}: a vendor phase angle is not modelled "
            f"(helix-phase-allpass.md); express the all-pass as an APF1/APF2 band in `eq`")
    eq = []
    for b in row.get("eq") or []:
        if b.get("bypass"):
            continue
        eq.append((str(b["type"]).upper(), float(b["f"]), float(b.get("gain_db") or 0.0),
                   float(b["q"]) if b.get("q") is not None else None))
    pol = str(row.get("polarity") or "NORM").upper()
    if pol not in ("NORM", "INV"):
        raise PredictError(f"polarity {pol!r}: expected NORM or INV")
    return {
        "muted": False,
        "gain_db": float(row.get("gain_db") or 0.0),
        "polarity": pol,
        "ta_ms": float(row.get("ta_ms") or 0.0),
        "hp": _leg(row.get("hp")),
        "lp": _leg(row.get("lp")),
        "eq": eq,
    }


def _leg(leg):
    if not isinstance(leg, dict) or leg.get("f") in (None, "OFF", "off", 0):
        return None
    return {"f": float(leg["f"]), "type": str(leg.get("type", "LR")).upper(),
            "slope": int(leg["slope"])}


def chain_from_anchor(d):
    """The anchors-style state stage 0 used: {hpf, lpf, delay_ms, inverted, gain_db, peq}."""
    d = d or {}
    eq = [(str(b["type"]).upper(), float(b["hz"]), float(b.get("gain_db") or 0.0),
           float(b["q"]) if b.get("q") is not None else None) for b in d.get("peq") or []]

    def leg(x):
        if not x:
            return None
        return {"f": float(x["hz"]), "type": str(x.get("family", "LR")).upper(),
                "slope": int(x["slope"])}
    return {"muted": False, "gain_db": float(d.get("gain_db") or 0.0),
            "polarity": "INV" if d.get("inverted") else "NORM",
            "ta_ms": float(d.get("delay_ms") or 0.0),
            "hp": leg(d.get("hpf")), "lp": leg(d.get("lpf")), "eq": eq}


def chain_response(freqs, chain):
    """The complex response of one DSP chain on `freqs` (no driver in it)."""
    f = np.asarray(freqs, dtype=float)
    if chain.get("muted"):
        return np.zeros(len(f), dtype=complex)
    h = np.full(len(f), 10.0 ** (chain["gain_db"] / 20.0), dtype=complex)
    if chain["polarity"] == "INV":
        h = -h
    h = h * np.exp(-2j * np.pi * f * chain["ta_ms"] / 1000.0)
    for kind in ("hp", "lp"):
        leg = chain.get(kind)
        if leg:
            h = h * dsp_math.xo_response(f, leg["f"], leg["slope"], kind, leg["type"])
    if chain.get("eq"):
        h = h * dsp_math.eq_complex(f, chain["eq"])
    return h


def chain_label(chain):
    if chain.get("muted"):
        return "MUTED"
    parts = [f"{chain['gain_db']:+.1f} dB", chain["polarity"], f"{chain['ta_ms']:.2f} ms"]
    for kind in ("hp", "lp"):
        leg = chain.get(kind)
        parts.append(f"{kind.upper()} {leg['f']:g} {leg['type']}{leg['slope']}" if leg
                     else f"{kind.upper()} off")
    parts.append(f"EQ x{len(chain.get('eq') or [])}")
    return " · ".join(parts)


# ---------------------------------------------------------------- solos
def _spectrum_on_grid(ir, fs, t0_s, freqs, drift_samples=0.0):
    """The complex response of an IR whose sample 0 sits at absolute time `t0_s`, on `freqs`.

    Sampled at the grid frequencies from the dense FFT (bins ~0.4 Hz apart on a 2.7 s record),
    so the interpolation only ever bridges adjacent bins. `drift_samples` re-times the capture by
    the drift measured on a control channel (set-02's manifest carries one per channel)."""
    x = np.asarray(ir, dtype=float)
    X = np.fft.rfft(x)
    fb = np.fft.rfftfreq(len(x), 1.0 / fs)
    f = np.asarray(freqs, dtype=float)
    H = np.interp(f, fb, X.real) + 1j * np.interp(f, fb, X.imag)
    t0 = float(t0_s) - float(drift_samples) / fs
    return H * np.exp(-2j * np.pi * f * t0)


def load_solo_v7(path, freqs, drift_samples=0.0):
    """A Resonalyze v7 impulse-response file: sample 0 of `transferRealSamples` is t = 0."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("format") not in (None, "resonalyze-impulse-response") and \
            "transferRealSamples" not in doc:
        raise PredictError(f"{path}: not a Resonalyze impulse-response file")
    fs = int(doc["sampleRate"])
    return _spectrum_on_grid(doc["transferRealSamples"], fs, 0.0, freqs, drift_samples), {
        "source": "v7", "path": path, "sample_rate": fs,
        "timing_reference": doc.get("timingReference"),
        "protective": (doc.get("rewSource") or {}).get("protectiveHighPass"),
    }


def load_solo_rew(title, freqs, api=None):
    """`<ch>_N (sw)` from a live REW, refused unless on the loopback base with no offset."""
    if api is None:
        import rew_api as api  # noqa: F811
    mid = api.find_measurement_id(title)
    timing = api.get_timing(mid)
    if not timing.get("has_ir", True):
        raise PredictError(f"{title!r} has no impulse response (an RTA?) -- a solo must be a sweep")
    ref = (timing.get("reference") or "").lower()
    off = float(timing.get("offset_s") or 0.0)
    if "loopback" not in ref or abs(off) > 1e-9:
        raise PredictError(
            f"{title!r}: timing reference {timing.get('reference')!r} with offset {off:.6f} s -- "
            f"not on the shared loopback base, so its arrival is not comparable (timebase.py)")
    times, ir = api.get_impulse_response(mid)
    fs = 1.0 / (times[1] - times[0])
    return _spectrum_on_grid(ir, fs, times[0], freqs), {
        "source": "rew", "title": title, "id": str(mid), "sample_rate": fs,
        "timing_reference": timing.get("reference"), "ir_start_s": times[0],
    }


def load_solos_dir(directory, freqs, drift=None):
    """Every `<name>.json` in DIR that is a v7 file -> {canonical code: (H, info)}."""
    out = {}
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json") or name == "manifest.json":
            continue
        code = canon(name[:-5])
        if "-ctl" in code or code.endswith("-nf") or code.endswith("-rta"):
            continue                       # controls, near-field, RTA twins: not solos
        try:
            H, info = load_solo_v7(os.path.join(directory, name), freqs,
                                   drift_samples=(drift or {}).get(code, 0.0))
        except (PredictError, KeyError, ValueError):
            continue
        out[code] = (H, info)
    if not out:
        raise PredictError(f"{directory}: no Resonalyze v7 impulse-response files found")
    return out


def drift_from_manifest(path, block="blockB_REW"):
    """Per-channel drift samples from a set manifest (`drift.<block>.perChannel.<ch>.driftSamples`)."""
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    per = ((m.get("drift") or {}).get(block) or {}).get("perChannel") or {}
    return {canon(k): float(v.get("driftSamples") or 0.0) for k, v in per.items()}


# ---------------------------------------------------------------- state
def chains_from_snapshot(snapshot, tier="channels"):
    rows = snapshot.get(tier) or {}
    return {canon(code): chain_from_row(row) for code, row in rows.items()}


def chains_from_anchors(d):
    return {canon(code): chain_from_anchor(v) for code, v in d.items()
            if isinstance(v, dict) and not code.startswith("_")}


def load_project_state(project_dir, preset=None, version=None):
    state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import state as st
    root = os.path.join(project_dir, "state")
    if preset is None:
        preset = st.Registry(root).get_active()
        if not preset:
            raise PredictError(f"no active slot in {root}/registry; pass --preset")
    snap = st.PresetHistory(root, preset, project_dir=project_dir).load(version)
    return preset, snap


def joints_from_chains(chains):
    """Adjacent pairs per side from the crossovers -- the same rule `analyze-joints --from-state`
    uses: sort a side's members (plus the mono ones) by their low-pass corner, and the joint
    frequency is the lower member's LPF. A member with no LPF is the top."""
    edges = {ch: (c.get("hp", {}) or {}).get("f") if not c.get("muted") else None
             for ch, c in chains.items()}
    lps = {ch: (c.get("lp") or {}).get("f") if not c.get("muted") else None
           for ch, c in chains.items()}
    joints, seen = [], set()
    for side in ("L", "R"):
        grp = [ch for ch in chains if _side_of(ch) in (side, "mono") and not chains[ch].get("muted")]
        grp.sort(key=lambda ch: lps[ch] if lps[ch] is not None else float("inf"))
        for lo, hi in zip(grp, grp[1:]):
            fc = lps[lo]
            if fc is None or (lo, hi) in seen:
                continue
            seen.add((lo, hi))
            joints.append((lo, hi, float(fc)))
    return joints


# ---------------------------------------------------------------- the prediction
def predict(freqs, solos, chains, joints=None, band_oct=1.0):
    """`solos`: {code: complex response on freqs}; `chains`: {code: chain}. Returns a dict."""
    f = np.asarray(freqs, dtype=float)
    processed, notes = {}, []
    for code, H in solos.items():
        chain = chains.get(code)
        if chain is None:
            notes.append(f"{code}: solo present, no ledger row -- left out")
            continue
        processed[code] = H * chain_response(f, chain)
    for code in chains:
        if code not in solos:
            notes.append(f"{code}: ledger row present, no solo -- left out")

    sides = {}
    for side in ("L", "R"):
        members = [c for c in processed if _side_of(c) in (side, "mono")]
        sides[side] = {"members": members,
                       "sum": (sum(processed[c] for c in members) if members
                               else np.zeros(len(f), dtype=complex))}
    front = [c for c in processed if _side_of(c) != "other"]
    left_out = [c for c in processed if _side_of(c) == "other"]
    if left_out:
        notes.append(f"{', '.join(left_out)}: centre/rear -- loaded, not summed (Phase 5)")
    all_sum = sum(processed[c] for c in front) if front else np.zeros(len(f), dtype=complex)

    if joints is None:
        joints = joints_from_chains({c: chains[c] for c in processed})
    junctions = []
    for lo, hi, fc in joints:
        if lo not in processed or hi not in processed:
            continue
        band = (fc / 2 ** band_oct, fc * 2 ** band_oct)
        A, B = processed[lo], processed[hi]
        sl = dsp_math.sum_loss(f, A, B, band)                       # search definition
        m = (f >= band[0]) & (f <= band[1])
        ceil = np.abs(A[m]) + np.abs(B[m])
        ok = ceil > 0
        null = 20.0 * np.log10(np.abs(A[m] + B[m])[ok] / ceil[ok] + 1e-12)
        k = int(np.argmin(null)) if ok.any() else None
        junctions.append({
            "lo": lo, "hi": hi, "fc": fc, "band": [band[0], band[1]],
            "sum_loss_avg_db": sl["avg_db"], "sum_loss_dip_db": sl["dip_db"],
            "sum_loss_dip_hz": sl["dip_hz"], "sum_loss_score_db": sl["score_db"],
            "worst_null_db": (float(null[k]) if k is not None else None),
            "worst_null_hz": (float(f[m][ok][k]) if k is not None else None),
        })

    lr = []
    for lo_f, hi_f in LR_BANDS:
        m = (f >= lo_f) & (f <= hi_f)
        if not m.any():
            continue
        w = dsp_math._log_weights(f[m])
        d = _db(sides["L"]["sum"][m]) - _db(sides["R"]["sum"][m])
        lr.append({"band": [lo_f, hi_f], "delta_db": float(np.sum(w * d) / np.sum(w))})

    return {"freqs_hz": f, "processed": processed, "chains": {c: chains[c] for c in processed},
            "sides": sides, "all": all_sum, "junctions": junctions, "lr_delta": lr,
            "notes": notes}


# ---------------------------------------------------------------- output
def to_json(result, decimate=1):
    f = result["freqs_hz"][::decimate]
    out = {
        "freqs_hz": [round(float(v), 3) for v in f],
        "channels": {c: {"chain": result["chains"][c],
                         "mag_db": [round(float(v), 3) for v in _db(h)[::decimate]],
                         "phase_deg": [round(float(v), 2)
                                       for v in np.degrees(np.angle(h))[::decimate]]}
                     for c, h in result["processed"].items()},
        "sides": {s: {"members": v["members"],
                      "sum_mag_db": [round(float(x), 3) for x in _db(v["sum"])[::decimate]]}
                  for s, v in result["sides"].items()},
        "all_mag_db": [round(float(x), 3) for x in _db(result["all"])[::decimate]],
        "junctions": result["junctions"],
        "lr_delta": result["lr_delta"],
        "notes": result["notes"],
        "not_modelled": ["phase_deg (vendor phase angle)", "virtual tier routing",
                         "centre / rear in the sums"],
    }
    return out


def render(result):
    lines = ["  Prediction: solos x ledger chains -> what the mic would hear", ""]
    for c, chain in result["chains"].items():
        lines.append(f"  {c:6} {chain_label(chain)}")
    lines.append("")
    lines.append(f"  {'junction':14}{'fc':>6}{'band':>12}{'sum-loss avg':>13}{'dip':>8}"
                 f"{'@Hz':>7}{'score':>7} | {'worst null':>10}{'@Hz':>7}")
    lines.append("  " + "-" * 88)
    for j in result["junctions"]:
        name = j["lo"] + "↔" + j["hi"]
        band_s = "%.0f-%.0f" % (j["band"][0], j["band"][1])
        lines.append(
            f"  {name:14}{j['fc']:>6.0f}{band_s:>12}"
            f"{j['sum_loss_avg_db']:>+13.2f}{j['sum_loss_dip_db']:>+8.1f}"
            f"{(j['sum_loss_dip_hz'] or 0):>7.0f}{j['sum_loss_score_db']:>+7.2f} | "
            f"{j['worst_null_db']:>+10.1f}{(j['worst_null_hz'] or 0):>7.0f}")
    lines.append("")
    lines.append("  L-R level difference (dB, + = left louder): " + "  ".join(
        f"{b['band'][0]:.0f}-{b['band'][1]:.0f}:{b['delta_db']:+.1f}" for b in result["lr_delta"]))
    for n in result["notes"]:
        lines.append(f"  note: {n}")
    return "\n".join(lines)


def plot(result, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, FuncFormatter
    f = result["freqs_hz"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), dpi=130, sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.4]})
    ax = axes[0]
    for c, h in result["processed"].items():
        ax.semilogx(f, _db(h), lw=1, alpha=0.7, label=c)
    for s, v in result["sides"].items():
        ax.semilogx(f, _db(v["sum"]), lw=2.2, label=f"sum {s}")
    ax.semilogx(f, _db(result["all"]), lw=2.6, color="k", alpha=0.6, label="ALL")
    top = float(np.nanmax(_db(result["all"])))
    ax.set_ylim(top - 60, top + 6)
    ax.set_ylabel("dB (relative)")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(loc="lower left", ncol=4, fontsize=8)
    ax.set_title("predicted: solos × ledger chains")
    ax2 = axes[1]
    for j in result["junctions"]:
        A, B = result["processed"][j["lo"]], result["processed"][j["hi"]]
        r = dsp_math.sum_loss(f, A, B, tuple(j["band"]), level_gate_db=dsp_math.SUM_LOSS_LEVEL_GATE_DB)
        ax2.semilogx(r["freqs_hz"], r["curve_db"], lw=1.6,
                     label=f"{j['lo']}↔{j['hi']} avg {j['sum_loss_avg_db']:+.1f} dip {j['sum_loss_dip_db']:+.1f}")
    ax2.set_ylim(-24, 1)
    ax2.set_ylabel("sum loss (dB)")
    ax2.set_xlabel("Hz")
    ax2.grid(True, which="both", ls=":", alpha=0.4)
    ax2.legend(loc="lower left", fontsize=8)
    ax2.set_xlim(f[0], f[-1])
    ax2.xaxis.set_major_locator(LogLocator(base=10, subs=[1, 2, 5]))
    ax2.xaxis.set_major_formatter(FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if x >= 1000 else f"{x:.0f}"))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--solos", metavar="DIR", help="directory of Resonalyze v7 solo files")
    src.add_argument("--rew", action="store_true", help="read <ch>_<ver> (sw) from a live REW")
    ap.add_argument("--ver", default="1", help="solo version for --rew (default 1)")
    ap.add_argument("--channels", default=None,
                    help="comma list of channel codes for --rew (default: the ledger's rows)")
    ap.add_argument("--drift", metavar="MANIFEST", default=None,
                    help="set manifest with per-channel driftSamples (v7 sets)")
    st = ap.add_mutually_exclusive_group()
    st.add_argument("--project", metavar="DIR", help="project dir: the ledger's active slot HEAD")
    st.add_argument("--state-json", metavar="FILE",
                    help="anchors-style state ({hpf,lpf,delay_ms,inverted,gain_db,peq} per channel)")
    ap.add_argument("--state-key", default=None,
                    help="key inside --state-json holding the state (e.g. current_G1_...)")
    ap.add_argument("--preset", default=None)
    ap.add_argument("--state-ver", default=None)
    ap.add_argument("--joint", action="append", default=[], metavar="lo,hi,fc",
                    help="override/add a junction (default: derived from the crossovers)")
    ap.add_argument("--band-oct", type=float, default=1.0)
    ap.add_argument("--ppo", type=int, default=PPO_DEFAULT)
    ap.add_argument("--fmin", type=float, default=FMIN_DEFAULT)
    ap.add_argument("--fmax", type=float, default=FMAX_DEFAULT)
    ap.add_argument("--out", metavar="DIR", default=None, help="write predicted.json here")
    ap.add_argument("--plot", action="store_true", help="also write predicted.png (matplotlib)")
    ap.add_argument("--json", action="store_true", help="print the JSON instead of the table")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not (args.solos or args.rew) or not (args.project or args.state_json):
        ap.error("need a solo source (--solos DIR | --rew) and a state (--project DIR | --state-json FILE)")

    f = grid(args.fmin, args.fmax, args.ppo)
    if args.state_json:
        with open(args.state_json, encoding="utf-8") as fh:
            d = json.load(fh)
        if args.state_key:
            d = d[args.state_key]
        chains = chains_from_anchors(d)
        state_label = f"{args.state_json}" + (f"[{args.state_key}]" if args.state_key else "")
    else:
        preset, snap = load_project_state(args.project, args.preset, args.state_ver)
        chains = chains_from_snapshot(snap)
        state_label = f"{args.project} slot {preset} {snap.get('version') or 'HEAD'}"

    drift = drift_from_manifest(args.drift) if args.drift else None
    if args.solos:
        loaded = load_solos_dir(args.solos, f, drift)
    else:
        codes = [c.strip() for c in args.channels.split(",")] if args.channels else list(chains)
        loaded = {}
        for code in codes:
            title = f"{code}_{args.ver} (sw)"
            try:
                loaded[code] = load_solo_rew(title, f)
            except (PredictError, KeyError) as e:
                print(f"  {code}: {e}", file=sys.stderr)
    solos = {c: H for c, (H, _) in loaded.items()}

    joints = None
    if args.joint:
        joints = []
        for spec in args.joint:
            lo, hi, fc = [p.strip() for p in spec.split(",")]
            joints.append((canon(lo), canon(hi), float(fc)))
    result = predict(f, solos, chains, joints=joints, band_oct=args.band_oct)
    result["notes"].insert(0, f"state: {state_label}")
    result["notes"].insert(1, "solos: " + ", ".join(
        f"{c} ({i['source']})" for c, (_, i) in loaded.items()))
    if args.json:
        print(json.dumps(to_json(result), indent=1))
    else:
        print(render(result))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "predicted.json"), "w", encoding="utf-8") as fh:
            json.dump(to_json(result), fh, indent=1)
        if args.plot:
            plot(result, os.path.join(args.out, "predicted.png"))
        print(f"  wrote {args.out}/predicted.json" + (" + predicted.png" if args.plot else ""),
              file=sys.stderr)
    return 0


# ---------------------------------------------------------------- selftest
def _selftest():
    """Anchored to facts about waves and to the ledger's own vocabulary, never to a stored run."""
    import tempfile
    f = grid(20, 20000, 48)
    fs = 96000

    # 1. The chain is the arithmetic it claims: gain, polarity, delay, crossover, EQ, each alone.
    one = {"muted": False, "gain_db": 0.0, "polarity": "NORM", "ta_ms": 0.0, "hp": None,
           "lp": None, "eq": []}
    assert np.allclose(chain_response(f, one), 1.0)
    assert np.allclose(chain_response(f, dict(one, gain_db=-6.0)), 10 ** (-6 / 20))
    assert np.allclose(chain_response(f, dict(one, polarity="INV")), -1.0)
    # Evaluated AT the frequency the claim is about, not at the grid's nearest point: 1 % off a
    # 24 dB/oct corner is already 0.3 dB, and a test that measures its grid is not a test.
    at = np.array([250.0, 100.0, 1000.0])
    d = chain_response(at, dict(one, ta_ms=1.0))
    assert np.allclose(np.abs(d), 1.0) and abs(np.degrees(np.angle(d[0])) + 90) < 1e-6
    hp = chain_response(at, dict(one, hp={"f": 100.0, "type": "LR", "slope": 24}))
    assert abs(_db(hp)[1] + 6.02) < 0.01, "LR is -6.02 dB at its corner (it is BW squared)"
    eq = chain_response(at, dict(one, eq=[("PK", 1000.0, -6.0, 2.0)]))
    assert abs(_db(eq)[2] + 6.0) < 0.01

    # 2. The two state shapes describe one chain: a ledger row and an anchors entry agree.
    row = {"hp": {"f": 80, "type": "BW", "slope": 24}, "lp": {"f": 300, "type": "LR", "slope": 12},
           "gain_db": -2.5, "ta_ms": 3.1, "polarity": "INV",
           "eq": [{"type": "PK", "f": 120, "gain_db": -3, "q": 4},
                  {"type": "LS", "f": 60, "gain_db": 2, "q": 0.71},
                  {"type": "PK", "f": 500, "gain_db": -9, "q": 1, "bypass": True}]}
    anc = {"hpf": {"family": "BW", "hz": 80, "slope": 24}, "lpf": {"family": "LR", "hz": 300, "slope": 12},
           "gain_db": -2.5, "delay_ms": 3.1, "inverted": True,
           "peq": [{"type": "PK", "hz": 120, "gain_db": -3, "q": 4},
                   {"type": "LS", "hz": 60, "gain_db": 2, "q": 0.71}]}
    assert np.allclose(chain_response(f, chain_from_row(row)), chain_response(f, chain_from_anchor(anc)))
    # A bypassed band is not in the chain; a vendor phase angle is refused, not ignored.
    assert len(chain_from_row(row)["eq"]) == 2
    try:
        chain_from_row(dict(row, phase_deg=45))
    except PredictError:
        pass
    else:
        raise AssertionError("phase_deg must be refused, not silently dropped")

    # 3. Two solos on one time base, aligned by the ledger: perfect summation, both rulers agree.
    #    w-L arrives at 1.0 ms, m-L at 1.5 ms; the ledger delays w-L by 0.5 -> in phase everywhere.
    sw = np.exp(-2j * np.pi * f * 1.0e-3)
    sm = np.exp(-2j * np.pi * f * 1.5e-3)
    chains = {"w-L": chain_from_row({"hp": "OFF", "lp": {"f": 300, "type": "LR", "slope": 24},
                                     "gain_db": 0, "ta_ms": 0.5, "polarity": "NORM"}),
              "m-L": chain_from_row({"hp": {"f": 300, "type": "LR", "slope": 24}, "lp": "OFF",
                                     "gain_db": 0, "ta_ms": 0.0, "polarity": "NORM"})}
    r = predict(f, {"w-L": sw, "m-L": sm}, chains)
    j = r["junctions"]
    assert len(j) == 1 and j[0]["lo"] == "w-L" and j[0]["hi"] == "m-L" and j[0]["fc"] == 300.0, j
    # LR24 halves sum flat and in phase: the loss is 0 to numerical precision on both rulers.
    assert j[0]["sum_loss_avg_db"] > -0.01 and j[0]["worst_null_db"] > -0.05, j[0]
    assert abs(_db(r["sides"]["L"]["sum"])[np.argmin(abs(f - 300))]) < 0.05, "LR24 sums to 0 dB at fc"
    # ...and with the ledger's delay removed the same pair no longer sums: the 0.5 ms offset puts
    # the 300 Hz junction 54 deg out, both rulers go negative, and the worst point sits INSIDE the
    # junction band. (A first draft asserted the null at the offset's half period, 1 kHz -- a
    # plausible number that lies outside the 150-600 band being read. Withdrawn.)
    chains_off = dict(chains, **{"w-L": dict(chains["w-L"], ta_ms=0.0)})
    r2 = predict(f, {"w-L": sw, "m-L": sm}, chains_off)
    j2 = r2["junctions"][0]
    assert j2["sum_loss_avg_db"] < -0.5 and j2["worst_null_db"] < -1.0, j2
    assert j2["band"][0] <= j2["worst_null_hz"] <= j2["band"][1], j2

    # 4. Sides: a mono sub joins both sides; centre is loaded and left out; a missing row is named.
    # The woofers get the sub's mirror HPF (80 LR24): below 60 Hz the shared sub dominates, so the
    # 3 dB the right woofer is down must show in the L-R delta where the woofers play and NOT
    # where the sub does. (A first draft left the woofers full-range and then blamed the delta.)
    w_row = {"hp": {"f": 80, "type": "LR", "slope": 24}, "lp": {"f": 300, "type": "LR", "slope": 24},
             "gain_db": 0, "ta_ms": 0.5, "polarity": "NORM"}
    chains3 = {"sw": chain_from_row({"hp": "OFF", "lp": {"f": 80, "type": "LR", "slope": 24},
                                     "gain_db": 0, "ta_ms": 0, "polarity": "NORM"}),
               "w-L": chain_from_row(w_row), "w-R": chain_from_row(w_row),
               "m-L": chains["m-L"], "m-R": chains["m-L"],
               "c": chains["m-L"]}                       # centre HAS a row: processed, not summed
    solos3 = {"sw": sw, "w-L": sw, "w-R": sw * 10 ** (-3 / 20), "m-L": sm, "m-R": sm, "c": sm,
              "tw-L": sm}                                # a solo with NO row: named, left out
    r3 = predict(f, solos3, chains3)
    assert r3["sides"]["L"]["members"] == ["sw", "w-L", "m-L"], r3["sides"]["L"]["members"]
    assert "sw" in r3["sides"]["R"]["members"] and "c" not in r3["sides"]["R"]["members"]
    assert any("centre/rear" in n for n in r3["notes"]) and any("no ledger row" in n for n in r3["notes"])
    lr = {tuple(b["band"]): b["delta_db"] for b in r3["lr_delta"]}
    assert 2.0 < lr[(120, 250)] < 3.5, lr        # w-R 3 dB down: the L-R delta shows it where w plays
    assert abs(lr[(20, 60)]) < 0.3, lr            # ...and not where only the shared sub plays
    fcs = sorted(jj["fc"] for jj in r3["junctions"])
    assert fcs == [80.0, 80.0, 300.0, 300.0], fcs

    # 5. A v7 file round-trips: an impulse at sample k reads as a pure delay of k/fs.
    import resonalyze_ir as ri
    # A real record's length (2.7 s at 96 kHz): the grid is sampled from the dense FFT and the
    # interpolation bridges 0.37 Hz bins. On an 8192-sample toy the bins are 11.7 Hz apart and a
    # 1 ms delay rotates 4 deg per bin, which linear interpolation shortens by 0.07 % -- the
    # test would then be measuring its own fixture, not the loader.
    n = 1 << 18
    x = np.zeros(n); k = 96; x[k] = 0.5
    doc = ri.build_v7(x, fs, 0.0, low_hz=20.0, high_hz=20000.0)
    doc = doc[0] if isinstance(doc, tuple) else doc          # (doc, info) on this build
    with tempfile.TemporaryDirectory() as tmp:
        ri.write_v7(doc, os.path.join(tmp, "w_L.json"))
        loaded = load_solos_dir(tmp, f)
        assert list(loaded) == ["w-L"], list(loaded)
        H = loaded["w-L"][0]
        assert np.allclose(np.abs(H), 0.5, atol=1e-6)
        ph = np.degrees(np.angle(H[np.argmin(abs(f - 250))]))
        assert abs(ph - (-360 * 250 * k / fs)) < 0.5, (ph, -360 * 250 * k / fs)

    # 6. JSON output is complete and the table renders.
    js = to_json(r3, decimate=4)
    assert set(js["sides"]) == {"L", "R"} and len(js["junctions"]) == 4 and js["not_modelled"]
    assert "w-L↔m-L" in render(r3)
    print("selftest[predict] OK -- chain arithmetic (gain/pol/delay/LR corner/PK), ledger row == anchors "
          "entry, an aligned LR24 pair sums to 0 dB on both rulers and the un-aligned one goes negative "
          "inside its band, mono sub on both sides / centre left out / missing rows named, v7 round trip "
          "reads a pure delay, JSON complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
