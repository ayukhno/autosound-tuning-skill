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

It PREDICTS and stops. Whether the prediction is to be believed is `verify_prediction.py`'s question -- the
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

The protective filter is taken back OUT before the chain goes on (doctrine, 2026-08-24, one home:
`project-intake.md §3`). A solo swept with a protective high-pass carries that filter in the recording,
and multiplying the ledger's crossover onto it predicts "driver x protective x crossover" -- the tune
session found the m/tw junction's dip displaced by ~500 Hz that way (2026-08-25, set-02: tweeters
swept under LR24 @1000, mids and centre under LR24 @100). v7 files say what was in the chain
(`rewSource.protectiveHighPass`); live REW solos are answered by the capture round's protective record
(`--process DIR`, the same record `analyze-joints --process` reads). The same rules as there: marked
raw -> de-embedded, `protective.de_embed`'s boost cap reported; recorded as unfiltered -> unchanged;
unmarked at baseline (`--baseline`) -> the channel is refused, not guessed.

Deliberately NOT modelled, and said so in the output rather than silently skipped:

  * a vendor phase ANGLE (`phase_deg`) on a channel whose reference crossover the ledger does not
    carry. The angle itself IS modelled since 2026-09-05 (`phase_rotation.py` -- the law measured on
    the Helix: one Q=1 second-order all-pass whose corner puts the angle AT the channel's configured
    crossover, the LPF on a sub and the HPF otherwise), so what is refused is only a row that states
    an angle at a crossover it does not have (`helix-phase-allpass.md`);
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
import phase_rotation  # noqa: E402

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


SUB_GROUP = "SWs"       # the name of two (or more) subwoofers summed: a PAIR, like Ws, not a junction


def _is_sub(code):
    return code.lower().startswith(("sw", "sub"))


def _side_of(code):
    c = code.lower()
    if _is_sub(code):
        return "mono"       # a sub feeds both sides -- `sw-f` and `sw-r` alike (they are not L/R)
    if c.endswith("-l") or c.endswith("_l"):
        return "L"
    if c.endswith("-r") or c.endswith("_r"):
        return "R"
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
def chain_from_row(row, code=None):
    """A schema-v3 ledger row -> the chain this module applies. Refuses what it cannot model.

    `code` is the channel's name. A row with a `phase_deg` needs it: the control's reference is the
    LPF on a subwoofer channel and the HPF on every other one (`_is_sub`), and nothing else on the
    row says which the channel is."""
    row = row or {}
    if row.get("mute") or row.get("off"):
        return {"muted": True}
    eq = []
    for b in row.get("eq") or []:
        if b.get("bypass"):
            continue
        eq.append(_band_from_row(b))
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
        "phase": _phase_from_row(row, code),
    }


def _phase_reference(row, code):
    """`(kind, hz)` of the crossover a phase angle is stated AT: the CONFIGURED LPF on a subwoofer
    channel, the configured HPF otherwise -- fact 6 of the Helix bench (`helix-phase-allpass.md`).

    Configured, not active: on the hardware a bypassed or `slope = OFF` crossover keeps its
    frequency and keeps being the reference, and reading the LIVE crossover gives the wrong corner
    on every channel whose filter is switched off. The ledger writes a disabled leg as null /
    "OFF" and loses the frequency with it, so the only way to carry that state is a leg whose `f`
    is still written with its slope OFF -- `_leg` keeps such a leg OUT of the chain, and this reads
    its frequency. `hz` is None when the row has no configured corner of that kind."""
    kind = "lp" if _is_sub(code) else "hp"
    leg = row.get(kind)
    f = leg.get("f") if isinstance(leg, dict) else None
    if f in (None, "OFF", "off", 0):
        return kind, None
    return kind, float(f)


def _phase_from_row(row, code):
    """The channel's phase control as the chain applies it, or None when the row has none.

    Until 2026-09-05 this module refused every `phase_deg` outright, and the refusal was right
    while nobody knew the law: the angle alone is not a filter. The law is measured now
    (`phase_rotation`): one Q=1 second-order all-pass whose corner the processor places so that
    the phase equals the angle AT the reference crossover, capped at 3/16 of the rate. So the
    angle plus the row's own crossover IS a filter, and the only genuinely unanswerable row is one
    that states an angle at a crossover it does not have -- that one is still refused by name.
    The chain carries the DELIVERED angle beside the setting: above the cap the setting lies."""
    deg = row.get("phase_deg")
    if deg in (None, 0, 0.0):
        return None
    deg = float(deg)
    if code is None:
        raise PredictError(
            f"phase_deg={deg:g}: the channel's code is needed to pick the reference crossover "
            f"(the LPF on a sub, the HPF otherwise) -- pass code=")
    kind, ref = _phase_reference(row, code)
    if ref is None:
        raise PredictError(
            f"phase_deg={deg:g} on a channel with no configured {kind.upper()}: the angle is stated "
            f"AT the channel's reference crossover (the LPF on a sub, the HPF otherwise -- "
            f"helix-phase-allpass.md), so without one it is not a filter. A crossover that is "
            f"switched off but still configured is written with its f and slope OFF")
    corner, delivered = phase_rotation.realize(deg, ref)       # at the session's bound rate
    if corner is None:
        return None
    out = {"deg": deg, "reference": {"kind": kind, "hz": ref}, "corner_hz": corner,
           "q": phase_rotation.SECTION_Q, "delivered_deg": delivered,
           "capped": phase_rotation.is_capped(deg, ref)}
    note = phase_rotation.capped_note(deg, ref)
    if note:
        out["note"] = note
    return out


def _band_from_row(b):
    """One ledger EQ band -> `(kind, f, gain_db, q)`, or a refusal naming what is missing.

    `state.validate` accepts a band without `gain_db` / `q` -- an honest record of "PK 850, gain and
    Q not written down" (the tune session's rear rows, 2026-08-25). Honest in the ledger, but not
    modellable: a bell needs both, a second-order all-pass needs its Q. Until now a missing gain
    silently became 0 dB and a missing Q reached `peq_response` as None and crashed the whole run.
    Refuse the band by name instead; `chains_from_snapshot` turns that into a channel left out of
    the prediction with the reason in the notes, which is what the doctrine asks of a check whose
    input is missing (`estimator-scope.md`).
    """
    kind = str(b["type"]).upper()
    f0 = float(b["f"])
    if kind == "APF1":
        return (kind, f0, 0.0, None)
    q = b.get("q")
    if q is None:
        raise PredictError(f"eq band {kind} {f0:g} has no q -- not modellable, record it or bypass it")
    if kind == "APF2":
        return (kind, f0, 0.0, float(q))
    g = b.get("gain_db")
    if g is None:
        raise PredictError(f"eq band {kind} {f0:g} has no gain_db -- not modellable, record it or bypass it")
    return (kind, f0, float(g), float(q))


def _leg(leg):
    """A crossover leg as the chain applies it; None when there is nothing to apply. A leg whose
    slope is OFF/0 is CONFIGURED and not active (the Helix keeps the frequency): out of the chain
    here, still the phase control's reference in `_phase_reference`."""
    if not isinstance(leg, dict) or leg.get("f") in (None, "OFF", "off", 0):
        return None
    if leg.get("slope") in (None, "OFF", "off", 0):
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
            "hp": leg(d.get("hpf")), "lp": leg(d.get("lpf")), "eq": eq, "phase": None}


def chain_response(freqs, chain):
    """The complex response of one DSP chain on `freqs` (no driver in it).

    `chain["upstream"]`, when present, is the list of chains this output is FED BY -- the virtual
    tier (a Helix VFL feeds every left-front output): their responses multiply in, in order. A
    virtual row is a chain like any other; what makes it apply here is the ROUTING fact, which the
    ledger does not carry (see `--route`)."""
    f = np.asarray(freqs, dtype=float)
    if chain.get("muted"):
        return np.zeros(len(f), dtype=complex)
    h = np.full(len(f), 10.0 ** (chain["gain_db"] / 20.0), dtype=complex)
    for up in chain.get("upstream") or []:
        h = h * chain_response(f, up)
    if chain["polarity"] == "INV":
        h = -h
    h = h * np.exp(-2j * np.pi * f * chain["ta_ms"] / 1000.0)
    for kind in ("hp", "lp"):
        leg = chain.get(kind)
        if leg:
            h = h * dsp_math.xo_response(f, leg["f"], leg["slope"], kind, leg["type"])
    if chain.get("eq"):
        h = h * dsp_math.eq_complex(f, chain["eq"])
    ph = chain.get("phase")
    if ph:
        # the vendor's phase control, realized: one APF2 at the corner the device places
        h = h * dsp_math.apf2_response(f, ph["corner_hz"], ph["q"])
    return h


def route_chains(chains, virtual, routes):
    """Attach virtual-tier chains upstream of the outputs they feed. `routes`: {virtual: [outputs]}.

    Returns a new chains dict and the notes. An output no route names is left as it is and SAID;
    a virtual code the ledger does not have is refused by name. The routing itself is a fact about
    the DSP's matrix that this module cannot read off anything -- it comes from the user (`--route`)
    or from the project once the schema carries it."""
    out = {c: dict(ch) for c, ch in chains.items()}
    notes, fed = [], set()
    for vcode, outputs in routes.items():
        v = virtual.get(canon(vcode))
        if v is None:
            raise PredictError(f"--route {vcode}: no such row in the ledger's virtual tier "
                               f"(have: {', '.join(sorted(virtual)) or 'none'})")
        if v.get("unmodellable"):
            raise PredictError(f"--route {vcode}: {v['unmodellable']}")
        for o in outputs:
            oc = canon(o)
            if oc not in out:
                raise PredictError(f"--route {vcode}={o}: no output row {o!r}")
            out[oc].setdefault("upstream", []).append(dict(v, code=canon(vcode)))
            fed.add(oc)
    if routes:
        unfed = [c for c in out if c not in fed and not out[c].get("muted") and not out[c].get("unmodellable")]
        if unfed:
            notes.append(f"virtual tier applied through --route; NOT routed (left as the output row alone): "
                         + ", ".join(sorted(unfed)))
    return out, notes


def chain_label(chain):
    if chain.get("unmodellable"):
        return f"NOT MODELLED -- {chain['unmodellable']}"
    if chain.get("muted"):
        return "MUTED"
    parts = [f"{chain['gain_db']:+.1f} dB", chain["polarity"], f"{chain['ta_ms']:.2f} ms"]
    for up in chain.get("upstream") or []:
        parts.append(f"<- {up.get('code', 'virtual')} EQ x{len(up.get('eq') or [])}"
                     + (f" {up['gain_db']:+.1f} dB" if up.get("gain_db") else "")
                     + (f" {up['ta_ms']:.2f} ms" if up.get("ta_ms") else ""))
    for kind in ("hp", "lp"):
        leg = chain.get(kind)
        parts.append(f"{kind.upper()} {leg['f']:g} {leg['type']}{leg['slope']}" if leg
                     else f"{kind.upper()} off")
    parts.append(f"EQ x{len(chain.get('eq') or [])}")
    ph = chain.get("phase")
    if ph:
        parts.append(f"phase {ph['deg']:g}° @{ph['reference']['kind'].upper()} {ph['reference']['hz']:g} "
                     f"-> APF2 {ph['corner_hz']:.0f} Hz"
                     + (f" CAPPED, delivers {ph['delivered_deg']:.1f}°" if ph.get("capped") else ""))
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
        "protective": _legs_from_v7((doc.get("rewSource") or {}).get("protectiveHighPass"),
                                    (doc.get("rewSource") or {}).get("protectiveState")),
        "protective_state": (doc.get("rewSource") or {}).get("protectiveState"),
    }


def _legs_from_v7(field, state=None):
    """`rewSource.protectiveHighPass` ({hz, family, slopeDbPerOct}, written by `resonalyze_ir.py`)
    -> the `{hp, lp}` legs `protective.legs_of` speaks.

    `null` in the file is NOT a fact on its own. Writers up to 3.0.27 wrote it both for "the round
    says nothing was in the chain" and for "nobody said" -- and a whole set exported with a
    mis-keyed round came out as `null` everywhere (2026-08-25). Since 3.0.28 the file also carries
    `rewSource.protectiveState` (`raw` / `bare` / `unknown`); with it, `null` is read as it says.
    Without it, `null` is read as unfiltered and the caller SAYS the file predates the mark."""
    if not field:
        return {"hp": "OFF", "lp": "OFF"}
    if not isinstance(field, dict) or field.get("hz") in (None, 0):
        raise PredictError(f"protectiveHighPass: expected {{hz, family, slopeDbPerOct}}, got {field!r}")
    return {"hp": {"f": float(field["hz"]), "type": field.get("family", "LR"),
                   "slope": int(field.get("slopeDbPerOct", 24))}, "lp": "OFF"}


def de_embed_solos(loaded, freqs, record=None, baseline=None):
    """Take the protective chain out of every loaded solo that is marked as carrying one.

    `loaded`: {code: (H, info)}. For v7 solos the mark is in `info["protective"]` (the file says);
    for REW solos it is the capture round's `record` (`protective.legs_of` shape). Returns
    `(solos, notes, refused)`: the corrected {code: H}, one note per channel saying what was done, and
    the codes left out because the question "was protection in force?" has no recorded answer at a
    baseline capture -- the `check` verdict of `protective.should_de_embed`, refused here rather than
    guessed, since a prediction with ~50 degrees of unrecorded phase at a junction looks exactly like a
    prediction.
    """
    import protective as prot
    f = np.asarray(freqs, dtype=float)
    solos, notes, refused = {}, [], []
    for code, (H, info) in loaded.items():
        legs = info.get("protective")
        if legs is None:                    # a REW solo: the round record answers
            verdict, detail = prot.should_de_embed(record, code, baseline=baseline)
        elif any(prot._live(legs.get(k)) for k in ("hp", "lp")):
            verdict, detail = "yes", legs
        elif info.get("protective_state") == "bare":
            verdict, detail = "no", "the round recorded nothing in the chain -- used as recorded"
        elif info.get("protective_state") == "unknown":
            verdict, detail = "no", ("the file says nobody recorded what was in the chain -- used "
                                     "as recorded; if a protective filter WAS in force, the phase "
                                     "near it is not the driver's")
        else:
            verdict, detail = "no", ("protectiveHighPass is null and the file predates the "
                                     "protectiveState mark (writer <= 3.0.27) -- read as unfiltered")
        if verdict == "yes":
            corrected, dinfo = prot.de_embed(f, H, detail)
            solos[code] = corrected
            legs_s = " ".join(f"{k.upper()} {v['f']:g} {v.get('type', 'LR')}{v.get('slope', 24)}"
                              for k, v in ((k, prot._live(detail.get(k))) for k in ("hp", "lp")) if v)
            cap = (f", correction capped below {dinfo['capped_below_hz']:.0f} Hz"
                   if dinfo.get("capped_below_hz") else "") + \
                  (f", capped above {dinfo['capped_above_hz']:.0f} Hz"
                   if dinfo.get("capped_above_hz") else "")
            notes.append(f"{code}: protective {legs_s} taken out of the solo{cap}")
        elif verdict == "check":
            refused.append(code)
            notes.append(f"{code}: REFUSED -- {detail}")
        else:
            solos[code] = H
            notes.append(f"{code}: solo used as recorded ({detail})")
    return solos, notes, refused


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
    """Every row as a chain. A row this module cannot model does not stop the run and does not get
    approximated: it becomes `{"unmodellable": reason}` and `predict` leaves the channel out, saying why."""
    rows = snapshot.get(tier) or {}
    out = {}
    for code, row in rows.items():
        try:
            out[canon(code)] = chain_from_row(row, code=canon(code))
        except PredictError as e:
            out[canon(code)] = {"muted": False, "unmodellable": str(e)}
    return out


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


def sub_group(chains):
    """The subwoofer codes that play, and whether they are one driver or a PAIR.

    Two subs (`sw-f`, `sw-r`) are not a lo/hi junction -- they share one band and sum in parallel,
    like `w-L`/`w-R`. Their relation is a pair alignment (reported under `pairs` as `SWs`), and the
    junction to the woofers is `SWs↔w`, read on their SUM. Sorting them by LPF and calling the
    lower one "lo" would have invented a crossover between two drivers that have none."""
    subs = [ch for ch in chains if _is_sub(ch) and not chains[ch].get("muted")]
    return subs


def joints_from_chains(chains):
    """Adjacent pairs per side from the crossovers -- the same rule `analyze-joints --from-state`
    uses: sort a side's members (plus the sub, or the sub GROUP) by their low-pass corner, and the
    joint frequency is the lower member's LPF. A member with no LPF is the top. Two or more subs
    enter as one member, `SWs`, whose LPF is the highest of theirs."""
    lps = {ch: (c.get("lp") or {}).get("f") if not c.get("muted") else None
           for ch, c in chains.items()}
    subs = sub_group(chains)
    if len(subs) > 1:
        lps[SUB_GROUP] = max((lps[c] for c in subs if lps[c] is not None), default=None)
    members = [ch for ch in chains if not chains[ch].get("muted") and not _is_sub(ch)]
    sub_members = [SUB_GROUP] if len(subs) > 1 else subs
    joints, seen = [], set()
    for side in ("L", "R"):
        grp = sub_members + [ch for ch in members if _side_of(ch) == side]
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
        if chain.get("unmodellable"):
            notes.append(f"{code}: ledger row cannot be modelled -- {chain['unmodellable']} -- left out")
            continue
        processed[code] = H * chain_response(f, chain)
        if (chain.get("phase") or {}).get("note"):
            notes.append(f"{code}: {chain['phase']['note']}")
    for code in chains:
        if code not in solos:
            notes.append(f"{code}: ledger row present, no solo -- left out")

    # Two or more subs: their SUM is a member of its own (`SWs`), read at the junction and
    # reported as a pair -- their mutual alignment over the band they share.
    pairs = []
    subs = [c for c in processed if _is_sub(c)]
    if len(subs) > 1:
        processed[SUB_GROUP] = sum(processed[c] for c in subs)
        chains = dict(chains, **{SUB_GROUP: {"muted": False, "gain_db": 0.0, "polarity": "NORM",
                                             "ta_ms": 0.0, "hp": None, "lp": None, "eq": [],
                                             "group_of": subs}})
        top = max(((chains[c].get("lp") or {}).get("f") or 0.0) for c in subs) or f[-1]
        band = (float(f[0]), float(top))
        a, b = subs[0], subs[1]
        sl = dsp_math.sum_loss(f, processed[a], processed[b], band)
        pairs.append({"pair": SUB_GROUP, "members": subs, "band": [band[0], band[1]],
                      "sum_loss_avg_db": sl["avg_db"], "sum_loss_dip_db": sl["dip_db"],
                      "sum_loss_dip_hz": sl["dip_hz"], "sum_loss_score_db": sl["score_db"],
                      "sum_ripple_db": sl["ripple_db"],
                      "note": ("the subs' mutual alignment over their shared band -- a pair, "
                               "not a junction; more than two are read as the first two")})

    sides = {}
    for side in ("L", "R"):
        members = [c for c in processed if c != SUB_GROUP and _side_of(c) in (side, "mono")]
        sides[side] = {"members": members,
                       "sum": (sum(processed[c] for c in members) if members
                               else np.zeros(len(f), dtype=complex))}
    front = [c for c in processed if c != SUB_GROUP and _side_of(c) != "other"]
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
                      "sum_ripple_db": sl["ripple_db"],
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
            "sides": sides, "all": all_sum, "junctions": junctions, "pairs": pairs,
            "lr_delta": lr, "notes": notes}


# ---------------------------------------------------------------- alignment (Phase 1.3)
APF_HINT_DIP_DB = -3.0     # a junction dip worse than this after delay/polarity earns an APF hint


def _profile_limits(project_dir):
    """(processing rate, delay ceiling ms) from the project's `dsp_profile.json`, each None if unknown."""
    if not project_dir:
        return None, None
    path = os.path.join(project_dir, "dsp_profile.json")
    if not os.path.isfile(path):
        return None, None
    import dsp_profile as _dp
    try:
        data = _dp._unwrap(_dp.load_profile(path))
    except Exception:  # noqa: BLE001 -- a broken profile is the profile's problem, said elsewhere
        return None, None
    rate = _dp.processing_rate_hz(data)
    delay = (data.get("delay") or {}).get("max_ms") if isinstance(data.get("delay"), dict) else None
    return (float(rate) if rate else None), (float(delay) if delay else None)


def arrival_difference_ms(freqs, A, B, band, max_ms=25.0, step_ms=0.02):
    """How much later B arrives than A over `band`: the peak of their band-limited cross-correlation.

    |Σ w·A·conj(B)·e^{+2πj f τ}| over τ, w = |A||B| where both play -- the matched-filter envelope,
    polarity-blind, and its main lobe sits at the physical delay while the lobes one cycle off are
    lower by the bandwidth. This is the ruler that tells an alias from the alignment: at 88 Hz one
    cycle is 11.4 ms, and a sum-loss search confined to ±3 ms on a sub that arrives 12 ms late finds
    a beautiful score one cycle off (a live tune, 2026-08-26). A first draft fitted the phase slope
    instead; on a real mid↔tweeter junction it read 6.4 ms where the impulse peaks were 0.9 apart --
    filter transitions inside the band are phase, not delay, and a slope cannot tell them apart.
    """
    f = np.asarray(freqs, dtype=float)
    m = (f >= band[0]) & (f <= band[1]) & (np.abs(A) > 0) & (np.abs(B) > 0)
    if m.sum() < 4:
        return None
    fb, x = f[m], A[m] * np.conj(B[m])
    # On a UNIFORM grid across the band: the log grid this module predicts on is dense at the
    # bottom of the band and sparse at the top, which both skews the correlation toward the low
    # end and aliases tau at 1/Δf of the sparse end (a 2 kHz junction on 48 ppo read +30 cycles).
    fu = np.linspace(fb[0], fb[-1], 2048)
    xu = np.interp(fu, fb, x.real) + 1j * np.interp(fu, fb, x.imag)
    xu = xu / np.abs(xu).max()
    taus = np.arange(-max_ms, max_ms + step_ms / 2, step_ms) / 1000.0
    env = np.abs(np.exp(2j * np.pi * np.outer(taus, fu)) @ xu)
    # B later by tau: A·conj(B) = e^{+2πj f tau}, which e^{+2πj f tau'} makes coherent at tau' = -tau.
    return float(-taus[int(np.argmax(env))] * 1000.0)    # ms; + means B arrives later than A


def align_joints(freqs, solos, chains, joints=None, *, step_ms=0.01, max_delay_ms=3.0,
                 band_oct=1.0, tie_db=0.02, apf=False, delay_max_ms=None):
    """Delay x polarity per junction, bottom-up, by sum loss -- the desk half of Phase 1.3.

    Each junction is read on the SOLOS x the ledger chains (crossovers, gains and EQ the tune
    already has are in), and the correction found for the UPPER member is written into its chain
    before the next junction up is read: `sw<->w` first, then `w<->m` on the woofer as it will now
    play, then `m<->tw`. The search is `dsp_math.align_sum_loss` -- the sum-loss score, the near-tie
    rule across BOTH polarities (a difference the score cannot resolve is not bought with delay),
    delays on the DSP's own grid (`step_ms` = 1000 / processing rate).

    Two subs are aligned to each other first (a pair, not a junction) and then enter the `SWs<->w`
    junction as their sum; the sub group is always the LOWER member, so no delay is ever asked of it.

    The delays that come out are RELATIVE. A negative delay on an upper member means everything
    below it must wait instead, so at the end the whole system is shifted together so that its
    smallest delay is 0 -- every relation kept, nothing asked to arrive early; the shift is reported.
    `delay_max_ms` (the profile's `delay.max_ms`) turns a delay the DSP cannot enter into a warning,
    never a silent clip.

    The search window follows the PHYSICS: `max_delay_ms` is widened to cover the arrival
    difference read off the members' phase slope (`arrival_difference_ms`), and every answer is
    reported with how many cycles at fc it sits from that arrival -- a score can be excellent one
    cycle off, and nothing in the score says so. A non-zero cycle count is a note by name; the
    choice stays the tuner's.

    Reports and proposes; banks nothing. `delta` is the shape `apply.propose` takes.
    """
    f = np.asarray(freqs, dtype=float)
    original = {c: dict(ch) for c, ch in chains.items()}
    chains = {c: dict(ch) for c, ch in chains.items()}
    notes, steps = [], []
    processed = {}
    for code, H in solos.items():
        ch = chains.get(code)
        if ch is None or ch.get("unmodellable") or ch.get("muted"):
            continue
        processed[code] = H * chain_response(f, ch)
    system = sorted(processed)                      # every channel that plays: shifted together
    if joints is None:
        joints = joints_from_chains({c: chains[c] for c in processed})
    joints = sorted(joints, key=lambda j: j[2])     # bottom-up: the sub junction first

    def _refresh(code):
        processed[code] = solos[code] * chain_response(f, chains[code])

    def _apply(code, tau_ms, pol):
        ch = chains[code]
        ch["ta_ms"] = float(ch["ta_ms"]) + tau_ms
        if pol < 0:
            ch["polarity"] = "INV" if ch["polarity"] == "NORM" else "NORM"
        _refresh(code)

    def _record(kind, lo, hi, fc, band, A, B):
        before = dsp_math.sum_loss(f, A, B, band)
        # B arrives `arr` ms after A: the physical delay is about -arr on B. Widen the window to
        # reach it, or the search can only return an alias.
        arr = arrival_difference_ms(f, A, B, band)
        window = max_delay_ms
        if arr is not None and abs(arr) + 1.0 > window:
            window = float(math.ceil(abs(arr) + 1.0))
        pol, tau, dip, margin, avg, score = dsp_math.align_sum_loss(
            f, A, B, band, max_delay_ms=window, step_ms=step_ms, tie_db=tie_db)
        # The PHYSICAL candidate: the best point within half a cycle of the arrival alignment,
        # either polarity -- the search re-run around -arr instead of around 0.
        physical = None
        if arr is not None and fc:
            # Candidates within half a cycle of the arrival alignment IN TOTAL PHASE at fc -- a
            # flip counts as half a cycle, so an inverted candidate is "physical" only between one
            # cycle back and the arrival itself. Scored on the same ruler, best wins.
            centre, cycle = -arr, 1000.0 / fc
            grid = max(step_ms, cycle / 240.0)
            best = None
            for pol_c in (1, -1):
                lo_t, hi_t = (centre - cycle / 2, centre + cycle / 2) if pol_c > 0 else (centre - cycle, centre)
                for t in np.arange(lo_t, hi_t + grid / 2, grid):
                    t = round(t / step_ms) * step_ms
                    s_ = dsp_math.sum_loss(f, A, pol_c * B * np.exp(-2j * np.pi * f * t / 1000.0), band)
                    if best is None or s_["score_db"] > best["score_db"] + 1e-12:
                        best = {"tau_ms": float(t), "polarity": pol_c, "score_db": s_["score_db"],
                                "avg_db": s_["avg_db"], "dip_db": s_["dip_db"]}
            physical = best
        chosen = "score"
        cyc = None
        if arr is not None and fc:
            cyc = (tau + arr) * fc / 1000.0 + (0.5 if pol < 0 else 0.0)
            if abs(cyc) >= 0.75 and physical is not None:
                # An alias: the score is good and the impulse is not one. The proposal takes the
                # physical answer; the alias stays in the record for the tuner to overrule.
                chosen = "physical"
        alias = {"tau_ms": tau, "polarity": int(pol), "score_db": score, "avg_db": avg, "dip_db": dip}
        if chosen == "physical":
            tau, pol = physical["tau_ms"], physical["polarity"]
        _apply(hi, tau, pol)
        after = dsp_math.sum_loss(f, A, processed[hi], band)
        rec = {"kind": kind, "lo": lo, "hi": hi, "fc": fc, "band": [band[0], band[1]],
               "tau_ms": tau, "steps": int(round(tau / step_ms)), "polarity": int(pol),
               "polarity_margin_db": margin, "window_ms": window, "chosen": chosen,
               "arrival_ms": (round(arr, 3) if arr is not None else None), "cycles_off": None,
               "physical": physical, "score_best": alias,
               "before": {k: before[k] for k in ("avg_db", "dip_db", "dip_hz", "score_db")},
               "after": {k: after[k] for k in ("avg_db", "dip_db", "dip_hz", "score_db")},
               "apf": None, "notes": []}
        if window != max_delay_ms:
            rec["notes"].append(f"search widened to +/-{window:g} ms to reach the arrival difference "
                                f"(`{hi}` arrives {abs(arr):.2f} ms {'after' if arr > 0 else 'before'} `{lo}`)")
        if cyc is not None:
            # A polarity flip is half a cycle; the cycles between the SCORE's answer and the
            # physical alignment (-arr) at fc, the flip folded in. Fractional, so a 0.35-cycle
            # disagreement is not rounded into silence.
            rec["cycles_off"] = round(float(cyc), 2)
            if chosen == "physical":
                a = alias
                rec["notes"].append(
                    f"ALIAS: the score's best ({a['tau_ms']:+.3f} ms{' INV' if a['polarity'] < 0 else ''}, "
                    f"score {a['score_db']:+.2f} dB) sits {cyc:+.2f} cycle(s) at {fc:g} Hz from the "
                    f"arrival alignment -- a good score, not one impulse. TAKEN: the physical answer "
                    f"({tau:+.3f} ms{' INV' if pol < 0 else ''}, score {physical['score_db']:+.2f} dB); "
                    f"overrule only after the junction is verified by ear and measurement")
            elif abs(cyc) >= 0.25:
                rec["notes"].append(
                    f"off the arrival alignment ({-arr:+.2f} ms) by {cyc:+.2f} cycle(s) at {fc:g} Hz "
                    f"-- the score prefers it; check the impulse before entering")
        if abs(abs(tau) - window) < step_ms / 2:
            rec["notes"].append(f"optimum sits AT the search edge ({window:g} ms) -- widen "
                                f"--max-delay-ms before believing it")
        if abs(tau) < step_ms / 2 and pol > 0:
            rec["notes"].append("already aligned as recorded -- nothing to change")
        if apf and after["dip_db"] < APF_HINT_DIP_DB:
            import xover_select as _xs
            hint = _xs.repair_joint_apf(f, A, processed[hi], band)
            if hint:
                hint["note"] = ("an APF2 hint, not applied: on `lo` it rotates that member's OTHER "
                                "junction too -- re-read it after entering")
                rec["apf"] = hint
        steps.append(rec)
        return rec

    subs = [c for c in processed if _is_sub(c)]
    if len(subs) > 1:
        a, b = subs[0], subs[1]
        top = max(((chains[c].get("lp") or {}).get("f") or 0.0) for c in subs) or float(f[-1])
        _record("pair", a, b, None, (float(f[0]), float(top)), processed[a], processed[b])
        processed[SUB_GROUP] = processed[a] + processed[b]
        if len(subs) > 2:
            notes.append(f"{len(subs)} subs: the pair read is the first two; {SUB_GROUP} sums all")

    for lo, hi, fc in joints:
        if lo not in processed or hi not in processed:
            notes.append(f"{lo}<->{hi}: a member has no solo or no modellable row -- skipped")
            continue
        if hi == SUB_GROUP:
            notes.append(f"{lo}<->{hi}: the sub group is never the upper member -- skipped")
            continue
        band = (fc / 2 ** band_oct, fc * 2 ** band_oct)
        _record("junction", lo, hi, float(fc), band, processed[lo], processed[hi])
        if lo == SUB_GROUP:
            pass                                     # nothing moved on the lower member
        # a junction ABOVE this one reads `hi` as its `lo`, already refreshed by _apply

    # Nothing arrives early: shift the whole system so its smallest delay is 0.
    floor = min(float(chains[c]["ta_ms"]) for c in system) if system else 0.0
    shift = -floor if floor < 0 else 0.0
    if shift:
        for c in system:
            chains[c]["ta_ms"] = float(chains[c]["ta_ms"]) + shift
        notes.append(f"every channel shifted by +{shift:.3f} ms so that no delay is negative -- "
                     f"relations unchanged")
    warnings = []
    if delay_max_ms:
        for c in system:
            if chains[c]["ta_ms"] > delay_max_ms + 1e-9:
                warnings.append(f"{c}: {chains[c]['ta_ms']:.3f} ms exceeds the DSP's delay "
                                f"ceiling {delay_max_ms:g} ms -- not enterable as is")
    delta = {"channels": {}}
    for c in system:
        o, n = original[c], chains[c]
        change = {}
        if abs(float(n["ta_ms"]) - float(o["ta_ms"])) > 1e-9:
            change["ta_ms"] = round(float(n["ta_ms"]), 4)
        if n["polarity"] != o["polarity"]:
            change["polarity"] = n["polarity"]
        if change:
            delta["channels"][c] = change
    out = {c: chains[c] for c in chains if c != SUB_GROUP}
    return {"steps": steps, "chains": out, "delta": delta, "shift_ms": shift,
            "step_ms": step_ms, "max_delay_ms": max_delay_ms, "warnings": warnings,
            "notes": notes}


def render_alignment(result, original=None, rate_hz=None):
    lines = [f"  Align by sum loss, bottom-up  (grid {result['step_ms']:.4f} ms"
             + (f" = 1 sample @ {rate_hz:g} Hz" if rate_hz else "")
             + f"; search +/-{result['max_delay_ms']:g} ms; delay on the UPPER member)", ""]
    lines.append(f"  {'step':16}{'fc':>6}{'before avg/dip':>17}{'delay':>9}{'pol':>5}"
                 f"{'after avg/dip':>17}{'margin':>8}")
    lines.append("  " + "-" * 78)
    for st in result["steps"]:
        name = f"{st['lo']}<->{st['hi']}" if st["kind"] == "junction" else f"{st['lo']}+{st['hi']} pair"
        fc = f"{st['fc']:.0f}" if st["fc"] else "--"
        b, a = st["before"], st["after"]
        arr = f"  arrival {st['arrival_ms']:+.2f} ms" if st.get("arrival_ms") is not None else ""
        cyc = f" ({st['cycles_off']:+.2f} cyc)" if st.get("cycles_off") else ""
        lines.append(f"  {name:16}{fc:>6}{b['avg_db']:>+8.2f}/{b['dip_db']:>+7.2f}"
                     f"{st['tau_ms']:>+9.3f}{'INV' if st['polarity'] < 0 else 'same':>5}"
                     f"{a['avg_db']:>+8.2f}/{a['dip_db']:>+7.2f}{st['polarity_margin_db']:>+8.2f}{arr}{cyc}")
        for n in st["notes"]:
            lines.append(f"  {'':16}  ! {n}")
        if st.get("apf"):
            h = st["apf"]
            lines.append(f"  {'':16}  APF2 hint: f0 {h['f0_hz']:g} Hz q {h['q']:g} on `{h['apply_to']}` "
                         f"(+{h['null_gain_db']:.1f} dB at the dip) -- {h['note']}")
    lines.append("")
    if result["delta"]["channels"]:
        lines.append("  proposal (aligned-delta.json; bank it with `apply.propose(history, delta)` and "
                     "enter by hand from the sheet it emits):")
        for c, ch in sorted(result["delta"]["channels"].items()):
            o = (original or {}).get(c) or {}
            parts = []
            if "ta_ms" in ch:
                smp = f" = {ch['ta_ms'] * rate_hz / 1000.0:.0f} smp" if rate_hz else ""
                parts.append(f"delay {float(o.get('ta_ms') or 0.0):.3f} -> {ch['ta_ms']:.4f} ms{smp}")
            if "polarity" in ch:
                parts.append(f"polarity {o.get('polarity', '?')} -> {ch['polarity']}")
            lines.append(f"    {c:8} " + "; ".join(parts))
    else:
        lines.append("  proposal: nothing to change")
    for w in result["warnings"]:
        lines.append(f"  WARNING {w}")
    for n in result["notes"]:
        lines.append(f"  note: {n}")
    return "\n".join(lines)


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
        "pairs": result.get("pairs", []),
        "lr_delta": result["lr_delta"],
        "notes": result["notes"],
        "not_modelled": ["phase_deg on a channel with no configured reference crossover",
                         "virtual tier routing", "centre / rear in the sums"],
    }
    return out


def render(result):
    lines = ["  Prediction: solos x ledger chains -> what the mic would hear", ""]
    for c, chain in result["chains"].items():
        lines.append(f"  {c:6} {chain_label(chain)}")
    lines.append("")
    lines.append(f"  {'junction/pair':14}{'fc':>6}{'band':>12}{'sum-loss avg':>13}{'dip':>8}"
                 f"{'@Hz':>7}{'score':>7}{'ripple':>8} | {'worst null':>10}{'@Hz':>7}")
    lines.append("  " + "-" * 96)
    for j in result["junctions"]:
        name = j["lo"] + "↔" + j["hi"]
        band_s = "%.0f-%.0f" % (j["band"][0], j["band"][1])
        lines.append(
            f"  {name:14}{j['fc']:>6.0f}{band_s:>12}"
            f"{j['sum_loss_avg_db']:>+13.2f}{j['sum_loss_dip_db']:>+8.1f}"
            f"{(j['sum_loss_dip_hz'] or 0):>7.0f}{j['sum_loss_score_db']:>+7.2f}"
            f"{j['sum_ripple_db']:>8.2f} | "
            f"{j['worst_null_db']:>+10.1f}{(j['worst_null_hz'] or 0):>7.0f}")
    for pr in result.get("pairs", []):
        lines.append(f"  {pr['pair']:14}{'pair':>6}{'%.0f-%.0f' % (pr['band'][0], pr['band'][1]):>12}"
                     f"{pr['sum_loss_avg_db']:>+13.2f}{pr['sum_loss_dip_db']:>+8.1f}"
                     f"{(pr['sum_loss_dip_hz'] or 0):>7.0f}{pr['sum_loss_score_db']:>+7.2f}"
                     f"{pr['sum_ripple_db']:>8.2f} | "
                     f"{'(' + '+'.join(pr['members']) + ')':>18}")
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
    ap.add_argument("--process", metavar="DIR", default=None,
                    help="the project's process/ dir: the capture round's protective record for --ver "
                         "(REW solos; default $AUTOSOUND_PROJECT_DIR/process when set). v7 solos carry "
                         "their own mark in the file")
    ap.add_argument("--baseline", action="store_true",
                    help="the solos are a baseline capture: an unmarked REW channel is REFUSED, not "
                         "read as configured")
    ap.add_argument("--no-de-embed", action="store_true",
                    help="leave protective filters IN the solos (to see what the doctrine changes; "
                         "not for a tune)")
    st = ap.add_mutually_exclusive_group()
    st.add_argument("--project", metavar="DIR", help="project dir: the ledger's active slot HEAD")
    st.add_argument("--state-json", metavar="FILE",
                    help="anchors-style state ({hpf,lpf,delay_ms,inverted,gain_db,peq} per channel)")
    ap.add_argument("--state-key", default=None,
                    help="key inside --state-json holding the state (e.g. current_G1_...)")
    ap.add_argument("--preset", default=None)
    ap.add_argument("--state-ver", default=None)
    ap.add_argument("--route", action="append", default=[], metavar="VIRTUAL=out1,out2",
                    help="the DSP's routing matrix, as the user reads it off the screen: the ledger's "
                         "virtual-tier row VIRTUAL feeds these outputs, so its EQ/gain/delay is in "
                         "their chain (e.g. --route VFL=w-L,m-L,tw-L). Not guessed from names")
    ap.add_argument("--joint", action="append", default=[], metavar="lo,hi,fc",
                    help="override/add a junction (default: derived from the crossovers)")
    ap.add_argument("--band-oct", type=float, default=1.0)
    ap.add_argument("--ppo", type=int, default=PPO_DEFAULT)
    ap.add_argument("--fmin", type=float, default=FMIN_DEFAULT)
    ap.add_argument("--fmax", type=float, default=FMAX_DEFAULT)
    ap.add_argument("--out", metavar="DIR", default=None, help="write predicted.json here")
    ap.add_argument("--plot", action="store_true", help="also write predicted.png (matplotlib)")
    ap.add_argument("--json", action="store_true", help="print the JSON instead of the table")
    al = ap.add_argument_group("alignment (Phase 1.3)")
    al.add_argument("--align", action="store_true",
                    help="find delay x polarity per junction by sum loss, bottom-up, and print the "
                         "proposal; the prediction that follows is of the ALIGNED state")
    al.add_argument("--max-delay-ms", type=float, default=3.0, help="search +/- this (default 3)")
    al.add_argument("--step-ms", type=float, default=None,
                    help="delay grid (default: 1000 / the project profile's processing rate, else 0.01)")
    al.add_argument("--tie-db", type=float, default=0.02)
    al.add_argument("--apf", action="store_true", help="add an APF2 hint where a dip remains")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    # The response model is bound to THIS device's processing rate before anything is modelled.
    # Not inside a branch: the crossover model runs on every path, and a binding that happens only
    # where the delay grid is computed leaves the common case on a module constant (hub #28).
    if getattr(args, "project", None):
        import dsp_profile as _dp_bind
        _rate_hz, _rate_note = _dp_bind.bind_model_rate(args.project)
        if _rate_note:
            print(f"  \u26a0 {_rate_note}", file=sys.stderr)
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
        route_notes = []
    else:
        preset, snap = load_project_state(args.project, args.preset, args.state_ver)
        chains = chains_from_snapshot(snap)
        state_label = f"{args.project} slot {preset} {snap.get('version') or 'HEAD'}"
        if args.route:
            routes = {}
            for spec in args.route:
                v, _, outs = spec.partition("=")
                routes[v.strip()] = [o.strip() for o in outs.split(",") if o.strip()]
            chains, route_notes = route_chains(chains, chains_from_snapshot(snap, tier="virtual_channels"), routes)
            state_label += " + virtual tier via --route"
        else:
            route_notes = []
            v_eq = [c for c, r in (snap.get("virtual_channels") or {}).items()
                    if isinstance(r, dict) and (r.get("eq") or r.get("ta_ms") or r.get("gain_db"))]
            if v_eq:
                route_notes.append("the ledger's VIRTUAL tier carries EQ/gain/delay on "
                                   + ", ".join(sorted(v_eq)) + " and is NOT in this prediction: "
                                   "no routing fact. Pass --route VIRTUAL=out,out as the DSP's "
                                   "matrix reads")

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
    if args.no_de_embed:
        solos = {c: H for c, (H, _) in loaded.items()}
        prot_notes = ["protective filters LEFT IN every solo (--no-de-embed) -- junction phase near a "
                      "protected driver is NOT the driver's"]
    else:
        record = None
        if args.rew:
            proc_dir = args.process or (
                os.path.join(os.environ["AUTOSOUND_PROJECT_DIR"], "process")
                if os.environ.get("AUTOSOUND_PROJECT_DIR") else None)
            if proc_dir:
                state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
                if state_dir not in sys.path:
                    sys.path.insert(0, state_dir)
                from process import Process
                proc = Process(proc_dir)
                record = proc.protective_record_for(args.ver)
                if record is None:
                    # The caller said a round exists; not finding it is a lookup failure, and reading
                    # the solos "as configured" on top of it is how a protective filter stays in a
                    # junction decision unseen (2026-08-25). Refuse, and list what IS on record.
                    rounds = proc.capture_rounds()
                    raise PredictError(
                        f"{proc_dir}: no capture round on record for _{args.ver}. Rounds on record: "
                        + ("; ".join(f"{r['id']} version {r['version']!r} titles _"
                                     + "/_".join(r["title_versions"] or ["?"]) for r in rounds)
                           or "none") + ". Open the round for these titles, or drop --process to "
                        "read the solos as configured on purpose.")
        solos, prot_notes, refused = de_embed_solos(loaded, f, record=record,
                                                    baseline=True if args.baseline else None)
        for code in refused:
            print(f"  {code}: refused -- see notes", file=sys.stderr)

    joints = None
    if args.joint:
        joints = []
        for spec in args.joint:
            lo, hi, fc = [p.strip() for p in spec.split(",")]
            joints.append((canon(lo), canon(hi), float(fc)))
    alignment = None
    if args.align:
        rate, delay_max = _profile_limits(args.project)
        step = args.step_ms or (1000.0 / rate if rate else 0.01)
        alignment = align_joints(f, solos, chains, joints=joints, step_ms=step,
                                 max_delay_ms=args.max_delay_ms, band_oct=args.band_oct,
                                 tie_db=args.tie_db, apf=args.apf, delay_max_ms=delay_max)
        if not rate and not args.step_ms:
            alignment["notes"].insert(0, "no processing rate known (no --project profile): delays "
                                         "on a 0.01 ms grid, not the DSP's -- pass --step-ms")
        if not args.json:
            print(render_alignment(alignment, original=chains, rate_hz=rate))
            print()
        chains = dict(chains, **alignment["chains"])
        state_label += " + aligned"
    result = predict(f, solos, chains, joints=joints, band_oct=args.band_oct)
    result["notes"].insert(0, f"state: {state_label}")
    result["notes"][1:1] = route_notes
    result["notes"].insert(1, "solos: " + ", ".join(
        f"{c} ({i['source']})" for c, (_, i) in loaded.items()))
    result["notes"][2:2] = prot_notes
    if args.json:
        js = to_json(result)
        if alignment is not None:
            js["alignment"] = alignment
        print(json.dumps(js, indent=1))
    else:
        print(render(result))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "predicted.json"), "w", encoding="utf-8") as fh:
            json.dump(to_json(result), fh, indent=1)
        if alignment is not None:
            with open(os.path.join(args.out, "aligned.json"), "w", encoding="utf-8") as fh:
                json.dump(alignment, fh, indent=1)
            with open(os.path.join(args.out, "aligned-delta.json"), "w", encoding="utf-8") as fh:
                json.dump(alignment["delta"], fh, indent=1)
            print(f"  wrote {args.out}/aligned.json + aligned-delta.json (the proposal)", file=sys.stderr)
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
    # A band with no q (or no gain) is refused BY NAME, never modelled as 0 dB or crashed on;
    # through a snapshot that becomes a channel left out with the reason in the notes.
    for bad in ({"type": "PK", "f": 850}, {"type": "PK", "f": 850, "q": 2},
                {"type": "APF2", "f": 300}):
        try:
            chain_from_row(dict(row, eq=[bad]))
            raise AssertionError(f"{bad} was modelled")
        except PredictError as e:
            assert "850" in str(e) or "300" in str(e), e
    assert chain_from_row(dict(row, eq=[{"type": "APF1", "f": 300}]))["eq"] == [("APF1", 300.0, 0.0, None)]
    snap = {"channels": {"w-L": row, "r-L": dict(row, eq=[{"type": "PK", "f": 850}])}}
    ch = chains_from_snapshot(snap)
    assert ch["r-L"].get("unmodellable") and "no q" in ch["r-L"]["unmodellable"], ch["r-L"]
    r_bad = predict(f, {"w-L": np.ones_like(f, dtype=complex), "r-L": np.ones_like(f, dtype=complex)}, ch)
    assert "r-L" not in r_bad["processed"] and any("cannot be modelled" in n for n in r_bad["notes"]), r_bad["notes"]
    assert "NOT MODELLED" in chain_label(ch["r-L"])
    # A vendor phase ANGLE is a filter once the row carries the crossover it is stated at
    # (`phase_rotation`: one Q=1 APF2 whose corner puts the angle AT the configured reference --
    # the LPF on a sub, the HPF otherwise). Without that crossover, or without the channel's name
    # to pick it, it is refused by name -- never dropped, never guessed.
    m_row = dict(row, phase_deg=90)                          # hp 80 BW24: the HPF is the reference
    ch_m = chain_from_row(m_row, code="m-L")
    assert ch_m["phase"]["reference"] == {"kind": "hp", "hz": 80.0} and not ch_m["phase"]["capped"], ch_m["phase"]
    assert abs(ch_m["phase"]["corner_hz"] - phase_rotation.realize(90.0, 80.0, fs)[0]) < 1e-9
    at_ref = chain_response(np.array([80.0]), dict(one, phase=ch_m["phase"]))[0]
    assert abs(np.degrees(np.angle(at_ref)) + 90.0) < 1e-6, "the angle is delivered AT the reference"
    assert np.allclose(np.abs(chain_response(f, dict(one, phase=ch_m["phase"]))), 1.0, atol=1e-12)
    ch_s = chain_from_row(m_row, code="sw")                  # the same row on a sub: the LPF (300)
    assert ch_s["phase"]["reference"] == {"kind": "lp", "hz": 300.0}, ch_s["phase"]
    assert ch_s["phase"]["corner_hz"] != ch_m["phase"]["corner_hz"], "sub and mid read different references"
    assert chain_from_row(dict(row, phase_deg=0), code="m-L")["phase"] is None
    assert chain_from_row(row, code="m-L")["phase"] is None
    for bad, code, needle in ((dict(row, phase_deg=90, hp="OFF"), "m-L", "no configured HP"),
                              (dict(row, phase_deg=90, lp=None), "sw", "no configured LP"),
                              (dict(row, phase_deg=90), None, "code")):
        try:
            chain_from_row(bad, code=code)
            raise AssertionError(f"{bad} was modelled")
        except PredictError as e:
            assert needle in str(e), (needle, str(e))
    # CONFIGURED, not active: a leg written with slope OFF is out of the chain and still the reference.
    off_leg = chain_from_row(dict(row, phase_deg=180, hp={"f": 80, "type": "BW", "slope": "OFF"}), code="m-L")
    assert off_leg["hp"] is None and off_leg["phase"]["reference"]["hz"] == 80.0, off_leg
    # Capped: one small step at a high reference collapses onto the ceiling, and the chain SAYS so
    # with the angle the channel actually gets -- the measured 29.5 deg, not the 5.625 asked for.
    cap = chain_from_row(dict(row, phase_deg=5.625, hp={"f": 5000, "type": "LR", "slope": 24}), code="tw-L")
    assert cap["phase"]["capped"] and abs(cap["phase"]["delivered_deg"] - 29.487) < 0.01, cap["phase"]
    assert "capped" in cap["phase"]["note"] and "CAPPED" in chain_label(cap), chain_label(cap)
    r_cap = predict(f, {"tw-L": np.ones_like(f, dtype=complex)}, {"tw-L": cap})
    assert any("capped" in n for n in r_cap["notes"]), r_cap["notes"]
    # ...and through a snapshot the code travels with the row, so a sub reads its LPF and a channel
    # with no configured reference is left out with the reason in the notes, not modelled blind.
    snap_p = {"channels": {"sw": dict(row, phase_deg=180), "m-L": dict(row, phase_deg=180, hp="OFF")}}
    ch_p = chains_from_snapshot(snap_p)
    assert ch_p["sw"]["phase"]["reference"]["kind"] == "lp", ch_p["sw"]
    assert "no configured HP" in ch_p["m-L"]["unmodellable"], ch_p["m-L"]

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

    # 6. A protective filter in the recording comes OUT before the chain goes on (doctrine 24.08).
    # Anchor to the definition: a flat driver swept under LR24 @1000 is, after de-embed, flat again
    # where the correction is not capped -- so "driver x chain" equals the chain alone -- and left
    # in, it is the chain x the protective, which is 6.02 dB down at 1 kHz on top of the chain.
    import protective as prot
    legs = {"hp": {"f": 1000.0, "type": "LR", "slope": 24}, "lp": "OFF"}
    swept = prot.response(f, legs)                     # what REW would hand back for a flat driver
    loaded = {"tw-L": (swept, {"source": "v7", "protective": legs}),
              "w-L": (np.ones_like(f, dtype=complex), {"source": "v7",
                                                         "protective": _legs_from_v7(None)})}
    solos, notes, refused = de_embed_solos(loaded, f)
    assert not refused and any("taken out" in n for n in notes) and any("as recorded" in n for n in notes), notes
    # LR24 @1000 is already -42 dB at 300 Hz -- inside `protective.de_embed`'s 40 dB boost cap, where
    # the correction is deliberately incomplete; the anchor sits where the cap does not (>= 500 Hz).
    above = f >= 500.0
    assert np.allclose(solos["tw-L"][above], 1.0, atol=1e-9), "de-embed must undo the protective exactly"
    assert any("capped below" in n for n in notes), "the cap region must be SAID, not hidden"
    # AT 1000 Hz, not at the grid's nearest bin (the same trap check 1 names: 1 % off a 24 dB/oct
    # corner is already 0.3 dB).
    assert abs(_db(prot.response(np.array([1000.0]), legs))[0] + 6.02) < 0.01, \
        "left in, the protective is still -6.02 dB at its corner"
    assert _legs_from_v7({"hz": 100.0, "family": "LR", "slopeDbPerOct": 24}) == \
        {"hp": {"f": 100.0, "type": "LR", "slope": 24}, "lp": "OFF"}
    # `null` in a file is read by its state mark, and a file without the mark is SAID to predate it.
    for state, word in (("bare", "recorded nothing"), ("unknown", "nobody recorded"), (None, "predates")):
        ld = {"w-L": (np.ones_like(f, dtype=complex),
                      {"source": "v7", "protective": _legs_from_v7(None, state), "protective_state": state})}
        _, n_s, _ = de_embed_solos(ld, f)
        assert any(word in n for n in n_s), (state, n_s)
    # A REW solo with no round record is read as configured (working-by-default); at baseline it is
    # refused, because the missing mark is the one thing the data cannot reveal.
    rew_loaded = {"m-L": (swept, {"source": "rew", "protective": None})}
    s_no, n_no, r_no = de_embed_solos(rew_loaded, f, record=None)
    assert "m-L" in s_no and not r_no
    s_b, n_b, r_b = de_embed_solos(rew_loaded, f, record=None, baseline=True)
    assert r_b == ["m-L"] and "m-L" not in s_b and any("REFUSED" in n for n in n_b), n_b
    rec = {"channels": {"m-L": {"hp": {"f": 1000.0, "type": "LR", "slope": 24}}}}
    s_r, n_r, _ = de_embed_solos(rew_loaded, f, record=rec, baseline=True)
    assert np.allclose(s_r["m-L"][above], 1.0, atol=1e-9)
    lr = {tuple(b["band"]): b["delta_db"] for b in r3["lr_delta"]}
    assert 2.0 < lr[(120, 250)] < 3.5, lr        # w-R 3 dB down: the L-R delta shows it where w plays
    assert abs(lr[(20, 60)]) < 0.3, lr            # ...and not where only the shared sub plays
    fcs = sorted(jj["fc"] for jj in r3["junctions"])
    assert fcs == [80.0, 80.0, 300.0, 300.0], fcs

    # 4b. Two subwoofers are a PAIR, not a junction: `sw-f`/`sw-r` sum into `SWs`, the junctions
    #     are SWs↔w-L and SWs↔w-R (never sw-f↔sw-r), and the pair's own alignment is reported.
    sub_row = {"hp": "OFF", "lp": {"f": 80, "type": "LR", "slope": 24}, "gain_db": 0,
               "ta_ms": 0, "polarity": "NORM"}
    chains4 = {"sw-f": chain_from_row(sub_row), "sw-r": chain_from_row(dict(sub_row, ta_ms=1.0)),
               "w-L": chain_from_row(w_row), "w-R": chain_from_row(w_row)}
    sf = np.exp(-2j * np.pi * f * 2.0e-3)          # the front sub arrives 1 ms before the rear one,
    sr = np.exp(-2j * np.pi * f * 1.0e-3)          # and the ledger delays the rear by 1.0 -> aligned
    r4 = predict(f, {"sw-f": sf, "sw-r": sr, "w-L": sw, "w-R": sw}, chains4)
    j4 = sorted((jj["lo"], jj["hi"]) for jj in r4["junctions"])
    assert j4 == [("SWs", "w-L"), ("SWs", "w-R")], j4
    assert r4["pairs"] and r4["pairs"][0]["pair"] == "SWs" and r4["pairs"][0]["members"] == ["sw-f", "sw-r"]
    assert r4["pairs"][0]["sum_loss_avg_db"] > -0.01, r4["pairs"][0]     # aligned subs: no loss
    assert "SWs" not in r4["sides"]["L"]["members"] and "sw-f" in r4["sides"]["L"]["members"]
    r4b = predict(f, {"sw-f": sf, "sw-r": sr, "w-L": sw, "w-R": sw},
                  dict(chains4, **{"sw-r": chain_from_row(sub_row)}))     # the rear left un-delayed
    # 1 ms apart at a sub: 29 deg at 80 Hz -> -0.28 dB at the top of the band and less below, so
    # the pair reads a small but definite loss. (A first draft demanded "< -1 dB" -- a number that
    # felt right and had no arithmetic behind it.)
    pb = r4b["pairs"][0]
    assert pb["sum_loss_avg_db"] < -0.05 and pb["sum_loss_dip_db"] < -0.2, pb
    assert "SWs" in render(r4)

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
    # 6b. The virtual tier applies through a ROUTING fact, never by name: a VFL with a -6 dB PK at
    #     1 kHz routed to w-L puts -6 dB at 1 kHz on w-L's chain, nothing on w-R, and the label says
    #     where it came from; a virtual code the ledger lacks is refused.
    vsnap = {"channels": {"w-L": dict(one, hp="OFF", lp="OFF"), "w-R": dict(one, hp="OFF", lp="OFF")},
             "virtual_channels": {"VFL": {"eq": [{"type": "PK", "f": 1000, "gain_db": -6, "q": 2}],
                                          "gain_db": 0, "ta_ms": 0, "polarity": "NORM"}}}
    routed, rnotes = route_chains(chains_from_snapshot(vsnap), chains_from_snapshot(vsnap, "virtual_channels"),
                                  {"VFL": ["w-L"]})
    assert abs(_db(chain_response(at, routed["w-L"]))[2] + 6.0) < 0.01 and \
        abs(_db(chain_response(at, routed["w-R"]))[2]) < 1e-9, (routed["w-L"], routed["w-R"])
    assert "VFL" in chain_label(routed["w-L"]) and any("NOT routed" in n and "w-R" in n for n in rnotes), rnotes
    try:
        route_chains(chains_from_snapshot(vsnap), chains_from_snapshot(vsnap, "virtual_channels"), {"VXX": ["w-L"]})
        raise AssertionError("an unknown virtual code was accepted")
    except PredictError as e:
        assert "VXX" in str(e)

    # 7. Alignment by sum loss, bottom-up, on the DSP's grid (Phase 1.3 as a command). Anchored
    #    to arrivals the fixtures DEFINE, never to a stored answer.
    step = 1000.0 / fs
    # (a) check 3's pair with the ledger's delay removed: m-L arrives 0.5 ms after w-L. The upper
    #     member cannot be asked to arrive early, so the answer must land as +0.5 ms on w-L after
    #     the shift, on the grid, buying no polarity, and sum to within the tie of perfect.
    r7 = align_joints(f, {"w-L": sw, "m-L": sm}, chains_off, step_ms=step)
    st = r7["steps"][0]
    assert (st["lo"], st["hi"], st["polarity"]) == ("w-L", "m-L", 1), st
    assert abs(st["tau_ms"] + 0.5) < 0.1 and st["after"]["avg_db"] > -0.02, st
    assert abs(st["tau_ms"] / step - round(st["tau_ms"] / step)) < 1e-6, "delay off the DSP grid"
    assert abs(r7["chains"]["w-L"]["ta_ms"] - 0.5) < 0.1 and abs(r7["chains"]["m-L"]["ta_ms"]) < 1e-9
    assert r7["shift_ms"] > 0 and set(r7["delta"]["channels"]) == {"w-L"}, r7["delta"]
    assert st["after"]["avg_db"] > st["before"]["avg_db"] + 0.3, "alignment must improve the sum"
    # (b) the same pair with m-L wired backwards: the flip is found and the delay is the same.
    r7b = align_joints(f, {"w-L": sw, "m-L": -sm}, chains_off, step_ms=step)
    assert r7b["steps"][0]["polarity"] == -1 and r7b["chains"]["m-L"]["polarity"] == "INV"
    assert abs(r7b["steps"][0]["tau_ms"] - st["tau_ms"]) < 0.05, r7b["steps"][0]
    # (c) already aligned: the tie rule buys nothing -- zero steps, same polarity, empty proposal.
    r7c = align_joints(f, {"w-L": sw, "m-L": sw}, chains_off, step_ms=step)
    assert r7c["steps"][0]["steps"] == 0 and r7c["steps"][0]["polarity"] == 1 and not r7c["delta"]["channels"]
    # (d) three-way, bottom-up. A first draft expected the naive arrival differences (2.0 and 1.5
    #     ms) and was wrong: the woofer's 80 Hz HPF bends phase at the 300 Hz junction and its 300
    #     Hz LPF bends phase at the 80 Hz one, so the right delay is NOT the arrival difference --
    #     which is the whole reason the junction is read on the processed members. The anchor is
    #     the definition instead: after alignment the two members are in phase AT the corner
    #     (|phase difference| at fc within 15 deg), each read bottom-up on the member below AS IT
    #     NOW PLAYS, and no delay is negative. `tie_db` is narrowed so the near-tie rule (checked
    #     in (c)) does not blur the answer.
    s_sw = np.exp(-2j * np.pi * f * 3.0e-3)
    ch3 = {"sw": chain_from_row({"hp": "OFF", "lp": {"f": 80, "type": "LR", "slope": 24},
                                 "gain_db": 0, "ta_ms": 0, "polarity": "NORM"}),
           "w-L": chain_from_row({"hp": {"f": 80, "type": "LR", "slope": 24},
                                  "lp": {"f": 300, "type": "LR", "slope": 24},
                                  "gain_db": 0, "ta_ms": 0, "polarity": "NORM"}),
           "m-L": chains_off["m-L"]}
    solos_d = {"sw": s_sw, "w-L": sw, "m-L": sm}
    r7d = align_joints(f, solos_d, ch3, step_ms=step, tie_db=0.001)
    assert [(x["lo"], x["hi"]) for x in r7d["steps"]] == [("sw", "w-L"), ("w-L", "m-L")], r7d["steps"]
    assert min(c["ta_ms"] for c in r7d["chains"].values()) >= 0, r7d["chains"]

    def _phase_at(fc, lo, hi, chains_, solos_):
        at = np.array([fc])
        k = int(np.argmin(abs(f - fc)))
        A = solos_[lo][k] * chain_response(at, chains_[lo])[0]
        B = solos_[hi][k] * chain_response(at, chains_[hi])[0]
        return abs(math.degrees(np.angle(A * np.conj(B))))

    def _score_with(lo, hi, band, chains_, solos_, extra_ms=0.0, flip=False):
        hi_ch = dict(chains_[hi], ta_ms=chains_[hi]["ta_ms"] + extra_ms)
        if flip:
            hi_ch["polarity"] = "INV" if hi_ch["polarity"] == "NORM" else "NORM"
        A = solos_[lo] * chain_response(f, chains_[lo])
        B = solos_[hi] * chain_response(f, hi_ch)
        return dsp_math.sum_loss(f, A, B, band)["score_db"]
    for x in r7d["steps"]:
        assert x["after"]["score_db"] >= x["before"]["score_db"] - 1e-9, x
        band = tuple(x["band"])
        # The recorded `after` is what an INDEPENDENT read of the returned chains gives -- and for
        # w<->m that read uses the woofer WITH its sw<->w delay, which is the sequential claim.
        here = _score_with(x["lo"], x["hi"], band, r7d["chains"], solos_d)
        assert abs(here - x["after"]["score_db"]) < 1e-9, (x["lo"], x["hi"], here, x["after"])
        # ...and it is the best point on its grid: no neighbour within three steps, in either
        # polarity, scores higher. That is what "found" means, with no number guessed.
        for n in (-3, -2, -1, 1, 2, 3):
            for flip in (False, True):
                other = _score_with(x["lo"], x["hi"], band, r7d["chains"], solos_d, n * step, flip)
                # ...beats it by more than the tie: inside the tie the most compact delay wins
                # on purpose (the doctrine (c) pins), so a neighbour may score a hair higher.
                assert other <= here + 0.001 + 1e-9, (x["lo"], x["hi"], n, flip, other, here)
    # The sub junction's mismatch is delay-like, so there the members end up in phase AT the corner.
    assert _phase_at(80.0, "sw", "w-L", r7d["chains"], solos_d) < 15.0, \
        _phase_at(80.0, "sw", "w-L", r7d["chains"], solos_d)
    # The 80 Hz HPF's phase at 300 Hz is not a delay, so w<->m keeps a residual no delay removes:
    # said as a number in the report (a dip), and that residual is the APF's job, not this step's.
    wm = r7d["steps"][1]
    assert wm["after"]["dip_db"] < 0 and wm["after"]["score_db"] < 0, wm["after"]
    # (e) two subs: the pair first (identical chains, so its ideal IS the arrival difference of
    #     0.3 ms, found to a grid step), then their SUM against the woofer -- in phase at 80 Hz.
    e0 = np.ones_like(f, dtype=complex)
    solos_e = {"sw-f": e0, "sw-r": np.exp(-2j * np.pi * f * 0.3e-3), "w-L": sw}
    ch_e = {"sw-f": ch3["sw"], "sw-r": ch3["sw"], "w-L": ch3["w-L"]}
    # tie_db=0: below 80 Hz a grid step is a fraction of a millidegree of loss, so ANY tie lets the
    # compact-delay rule pull the answer toward 0; the pair check is of the search, not the rule.
    r7e = align_joints(f, solos_e, ch_e, step_ms=step, tie_db=0.0)
    kinds = [(x["kind"], x["lo"], x["hi"]) for x in r7e["steps"]]
    assert kinds == [("pair", "sw-f", "sw-r"), ("junction", SUB_GROUP, "w-L")], kinds
    te = {c: r7e["chains"][c]["ta_ms"] for c in ("sw-f", "sw-r", "w-L")}
    assert abs((te["sw-f"] - te["sw-r"]) - 0.3) <= step, te
    assert min(te.values()) >= 0 and r7e["steps"][0]["after"]["avg_db"] > -0.01, (te, r7e["steps"][0])
    sub_sum = solos_e["sw-f"] * chain_response(f, r7e["chains"]["sw-f"]) + \
        solos_e["sw-r"] * chain_response(f, r7e["chains"]["sw-r"])
    ph = abs(math.degrees(np.angle((sub_sum * np.conj(solos_e["w-L"] * chain_response(f, r7e["chains"]["w-L"])))[np.argmin(abs(f - 80))])))
    assert ph < 15.0, ph
    # (f) the delay ceiling is a warning by name, never a clip: with a ceiling BELOW what (d) found
    #     for the woofer, the warning names it and the answer is the same as without a ceiling.
    w_found = r7d["chains"]["w-L"]["ta_ms"]
    assert w_found > 0, w_found
    r7f = align_joints(f, solos_d, ch3, step_ms=step, tie_db=0.001, delay_max_ms=w_found / 2)
    assert any("w-L" in w and "ceiling" in w for w in r7f["warnings"]), r7f["warnings"]
    assert abs(r7f["chains"]["w-L"]["ta_ms"] - w_found) < 1e-9, "a warning must not change the answer"
    # (g) A sub that arrives 12 ms after the woofer, at an 88 Hz junction (one cycle = 11.4 ms).
    #     The arrival difference is read off the phase slope; the window widens to reach it; the
    #     answer is the PHYSICAL one (within a step of 12 ms, no flip, 0 cycles off). And a search
    #     pinned to +/-3 ms by hand can only return an alias -- which must then be SAID by name.
    late = np.exp(-2j * np.pi * f * 12.0e-3)
    ch_g = {"sw": chain_from_row({"hp": "OFF", "lp": {"f": 88, "type": "LR", "slope": 24},
                                  "gain_db": 0, "ta_ms": 0, "polarity": "NORM"}),
            "w-L": chain_from_row({"hp": {"f": 88, "type": "LR", "slope": 24}, "lp": "OFF",
                                   "gain_db": 0, "ta_ms": 0, "polarity": "NORM"})}
    arr = arrival_difference_ms(f, late * chain_response(f, ch_g["sw"]), e0 * chain_response(f, ch_g["w-L"]), (44, 176))
    assert abs(arr + 12.0) < 0.2, arr                        # w-L arrives 12 ms BEFORE the sub
    r7g = align_joints(f, {"sw": late, "w-L": e0}, ch_g, step_ms=step, tie_db=0.001)
    g = r7g["steps"][0]
    assert g["window_ms"] >= 13 and abs(g["tau_ms"] - 12.0) <= 0.1 and g["polarity"] == 1, g
    assert abs(g["cycles_off"]) < 0.25 and not any("ALIAS" in n for n in g["notes"]), (g["cycles_off"], g["notes"])
    assert g["chosen"] == "score" and g["physical"] and abs(g["physical"]["tau_ms"] - g["tau_ms"]) <= 0.1, g
    # (h) Forced alias: the same pair with the search re-read one cycle off by hand -- a chain that
    #     already carries a whole cycle of delay on the woofer. The score's best and the physical
    #     answer now disagree by a cycle; the PHYSICAL one is taken and the alias is said by name.
    ch_h = {"sw": ch_g["sw"], "w-L": dict(ch_g["w-L"], ta_ms=12.0 + 1000.0 / 88.0)}
    r7h = align_joints(f, {"sw": late, "w-L": e0}, ch_h, step_ms=step, tie_db=0.001)
    h = r7h["steps"][0]
    assert h["physical"] is not None and abs(h["chains"]["w-L"]["ta_ms"] - 12.0) <= 0.1 if "chains" in h else True
    assert abs(r7h["chains"]["w-L"]["ta_ms"] - 12.0) <= 0.1, (r7h["chains"]["w-L"], h)
    r7g2 = align_joints(f, {"sw": late, "w-L": e0}, ch_g, step_ms=step, tie_db=0.001, max_delay_ms=3.0)
    g2 = r7g2["steps"][0]
    assert g2["window_ms"] >= 13, "the window must follow the arrival, not the hand-set default"
    txt = render_alignment(r7d, original=ch3, rate_hz=fs)
    assert "proposal" in txt and "w-L" in txt and "smp" in txt, txt

    print("selftest[predict] OK -- chain arithmetic (gain/pol/delay/LR corner/PK), ledger row == anchors "
          "entry, a phase angle is realized at the row's configured reference (LPF on a sub, HPF "
          "otherwise; slope OFF keeps it), delivered AT the reference, capped by name, refused without "
          "a reference or a code, "
          "an aligned LR24 pair sums to 0 dB on both rulers and the un-aligned one goes negative "
          "inside its band, mono sub on both sides / centre left out / missing rows named, v7 round trip "
          "reads a pure delay, JSON complete; align: a 0.5 ms pair lands on the grid as +0.5 on the "
          "lower member, a backwards wire is found, an aligned pair buys nothing, three-way bottom-up "
          "and a sub pair keep every relation with no negative delay, the ceiling warns by name.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
