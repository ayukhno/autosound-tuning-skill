"""REW loopback-referenced sweep  →  Resonalyze "impulse response" JSON (format v7).

Resonalyze (https://github.com/DIMOSUS/Resonalyze, MIT) is a car-audio auto-alignment
tool whose whole method rests on one thing: every driver's transfer impulse response sits
on ONE absolute time base — sample 0 of the transfer IR is the loopback arrival, so a
sample-wise sum of the processed channels is what the microphone would hear
(`dsp/VirtualCrossoverAnalysis.cs`). A REW user with a two-input interface and a physical
loopback measures on exactly that base (REW: `timingReference: Loopback`), but until
this module the only way into Resonalyze was its own capture. This writes REW's IR as the
file Resonalyze saves itself, so Virtual DSP / Auto delay / Auto crossover open on REW
data with nothing retyped.

What the file gets, and where each number comes from (all verified against a live REW
5.40 β132 / API 0.9.6 and Resonalyze `source/Measurements/ImpulseResponseFile.cs` at
commit d11186e, 2026-08-19):

  * the RAW impulse response — `GET /measurements/{id}/impulse-response?normalised=false`.
    The endpoint's DEFAULT is `normalised=true`: every IR comes back with its peak at
    exactly ±1.0, which silently destroys the level relation between channels (a sub's
    IR peak really sits ~18 dB under a woofer's). Raw values are in PERCENT of full
    scale; the file carries them as a fraction of full scale (percent / 100). Relative
    channel levels — what Resonalyze's sum-loss alignment and gain balance read — are
    therefore exact for a set measured at one mic gain and one sweep level.
  * the time base — REW serves `startTime` (the time of sample 0, in s) with t = 0 at
    the loopback reference; the mic-IR peak is always placed at an INTEGER sample (1.0 s
    in at 96 kHz), so t = 0 usually falls at a FRACTIONAL sample index (95629.073 for a
    typical channel). Resonalyze wants t = 0 AT sample 0. Rounding would throw away
    ~0.5 sample = 5 µs = 1.8 mm — Resonalyze's arrival estimator resolves ~0.1 sample,
    so the transfer IR is rotated by the exact fractional amount with a linear-phase
    FFT shift (an integer shift stays a bit-exact roll). Negative time (REW's ~1 s of
    pre-roll, holding the Farina harmonic-distortion images) wraps to the tail of the
    buffer — the same circular convention Resonalyze's own H1 estimator leaves behind.
  * `transferRealSamples` + `transferPeakIndex` — the rotated IR (what alignment uses);
    `sweepDeconvolutionRealSamples` + `sweepDeconvolutionPeakIndex` — REW's buffer as
    served (peak deep inside, harmonics before it), which is what Resonalyze's raw
    "sweep deconvolution" IR looks like too. Both from ONE array, so the file is
    self-consistent by construction.
  * `measurementMode: LoopbackTransfer`, `timingReference: SynchronizedLoopback` — set
    ONLY when REW says `timingReference == "Loopback"` and `timingOffset == 0`; anything
    else is refused (a timing offset moves REW's zero off the loopback and would be a
    number that only looks like a delay).
  * `sweepDurationSeconds` — REW keeps the IR as long as the sweep, so it is inferred
    from the IR length (256k samples at 96 kHz = 2.731 s); `--sweep-seconds` overrides.
  * `lowFrequencyHz`/`highFrequencyHz` — the measurement's `startFreq`/`endFreq`.
  * a `rewSource` block per file (title, uuid, REW date, startTime, REW's own delay
    estimate, peak dBFS, the fractional shift, the protective high-pass in force) —
    Resonalyze's deserializer ignores unknown members, so it travels harmlessly and a
    reader can audit every number without the manifest.

NOT carried (REW has none of it): transfer coherence, mic/loopback level meters, the
SPL calibration, the audio-session record. All are optional in the format; Resonalyze's
consumers fall back without them (checked in `dsp/*.cs`).

Protective high-passes are NOT removed here. Resonalyze compensates them at capture time
(`ExpSweepMeasurement.ApplyAverageResult` → `ProtectiveHighPassCompensation`), so a saved
file is already compensated and carries no filter field; a REW set measured with a
protective HPF must say so — the manifest and `rewSource.protectiveHighPass` do — and be
de-embedded by whoever consumes it (their `ProtectiveHighPassCompensation
.RemoveFromImpulseResponse` from a small C# harness, or our own de-embed).

`validate_v7()` mirrors `ImpulseResponseFile.Validate()` field for field so a written
document is checked here against the same rules that would reject it there.

Deps: numpy (FFT). Live use needs REW with its API on; `--selftest` is offline.
CLI:
  python3 resonalyze_ir.py --title "w-L_01 (sw)=w_L" --title "sw_01 (sw)=sw" --out DIR
        [--bits 24] [--play-channel Left] [--sweep-seconds S] [--averages 1]
        [--hpf m_L=100:LR:24 ...] [--note "..."]
  python3 resonalyze_ir.py --selftest
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

CONVERTER = "autosound-tuning-skill rew_tool/resonalyze_ir.py"
CONVERTER_VERSION = "1.0 (2026-08-19, format v7 as of Resonalyze d11186e)"
FORMAT = "resonalyze-impulse-response"
VERSION = 7
PLAY_CHANNELS = ("Mono", "Left", "Right", "Stereo")


class ConversionError(ValueError):
    pass


# ----------------------------------------------------------------- signal helpers

def advance_circular(x, shift_samples):
    """y[k] = x[k + shift] on a circular buffer; `shift` may be fractional.

    Integer shifts are a bit-exact `np.roll`; fractional ones apply a linear phase ramp
    (band-limited sinc interpolation — exact for a signal band-limited below Nyquist,
    which a 20 kHz sweep at 96 kHz is). The Nyquist bin is forced real so the inverse
    stays a real signal without a discarded imaginary residue.
    """
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    whole = int(np.floor(shift_samples))
    frac = float(shift_samples - whole)
    y = np.roll(x, -whole)
    if abs(frac) < 1e-9:
        return y
    spec = np.fft.rfft(y)
    k = np.arange(spec.size)
    spec *= np.exp(2j * np.pi * k * frac / n)
    if n % 2 == 0:
        spec[-1] = spec[-1].real
    return np.fft.irfft(spec, n=n)


def peak_time_parabolic(y, fs):
    """Sub-sample position of the |y| peak (parabolic fit through 3 points), in seconds
    from sample 0 (circular indices allowed for a peak next to the seam)."""
    n = y.size
    i = int(np.argmax(np.abs(y)))
    a, b, c = abs(y[(i - 1) % n]), abs(y[i]), abs(y[(i + 1) % n])
    denom = a - 2 * b + c
    delta = 0.0 if denom == 0 else 0.5 * (a - c) / denom
    return (i + delta) / fs, i


# --------------------------------------------------------------- REW → document

def build_v7(ir_fraction_fs, sample_rate, start_time_s, *, timing_reference="Loopback",
             timing_offset_s=0.0, low_hz, high_hz, bits=24, play_channel="Left",
             sweep_seconds=None, averages=1, saved_at=None, rew_source=None):
    """Return (document, info): the JSON-ready dict for one file and the numbers behind it.

    ir_fraction_fs : REW's IR as a fraction of full scale (raw percent / 100), as served
                     — sample i sits at t = start_time_s + i / sample_rate, t = 0 being the
                     loopback reference.
    """
    if timing_reference != "Loopback":
        raise ConversionError(
            f"timingReference is {timing_reference!r}, not 'Loopback': the IR is not on the "
            "loopback time base and cannot be a SynchronizedLoopback transfer file")
    if abs(float(timing_offset_s)) > 0:
        raise ConversionError(
            f"timingOffset {timing_offset_s} s ≠ 0: REW's zero is displaced from the loopback; "
            "not converted (undo the offset in REW or state the base explicitly)")
    x = np.asarray(ir_fraction_fs, dtype=np.float64)
    if x.ndim != 1 or x.size == 0:
        raise ConversionError("empty impulse response")
    if not np.all(np.isfinite(x)):
        raise ConversionError("impulse response holds non-finite samples")
    fs = int(round(float(sample_rate)))
    if abs(fs - float(sample_rate)) > 1e-6:
        raise ConversionError(f"non-integer sample rate {sample_rate}")
    n = x.size
    i0 = -float(start_time_s) * fs            # index of t = 0 (fractional)
    if not (0 <= i0 < n):
        raise ConversionError(f"t = 0 lies outside the buffer (index {i0:.3f} of {n})")
    y = advance_circular(x, i0)               # sample 0 = loopback reference
    sweep_peak = int(np.argmax(np.abs(x)))
    transfer_peak = int(np.argmax(np.abs(y)))
    if sweep_seconds is None:
        sweep_seconds = n / fs                # REW: IR length == sweep length
    saved = saved_at or datetime.now(timezone.utc)
    doc = {
        "format": FORMAT,
        "version": VERSION,
        "savedAtUtc": saved.isoformat(timespec="microseconds")
        if isinstance(saved, datetime) else str(saved),
        "sampleRate": fs,
        "bits": int(bits),
        "octaves": 0,
        "lowFrequencyHz": float(low_hz),
        "highFrequencyHz": float(high_hz),
        "achievedLowFrequencyHz": float(low_hz),
        "achievedHighFrequencyHz": float(high_hz),
        "sweepDurationSeconds": float(sweep_seconds),
        "playChannel": play_channel,
        "measurementMode": "LoopbackTransfer",
        "timingReference": "SynchronizedLoopback",
        "sweepDeconvolutionPeakIndex": sweep_peak,
        "averageRunCount": int(averages),
        "acceptedAverageRunCount": int(averages),
        "transferPeakIndex": transfer_peak,
        "sweepDeconvolutionRealSamples": x,
        "transferRealSamples": y,
    }
    t_peak_transfer, _ = peak_time_parabolic(y, fs)
    info = {
        "samples": n,
        "t0_index": i0,
        "t0_index_fraction": i0 - math.floor(i0),
        "sweep_peak_index": sweep_peak,
        "transfer_peak_index": transfer_peak,
        "transfer_peak_time_s": t_peak_transfer,
        "peak_fs_fraction": float(x[sweep_peak]),
        "peak_dbfs": 20 * math.log10(abs(float(x[sweep_peak]))) if x[sweep_peak] != 0 else None,
    }
    src = dict(rew_source or {})
    src.update({
        "converter": CONVERTER,
        "converterVersion": CONVERTER_VERSION,
        "startTimeS": float(start_time_s),
        "timeZeroIndex": i0,
        "peakDbfs": info["peak_dbfs"],
        "amplitudeUnit": "fraction of full scale (REW percent / 100, normalised=false)",
        "sweepDurationInferredFromIrLength": sweep_seconds == n / fs,
    })
    doc["rewSource"] = src
    validate_v7(doc)
    return doc, info


def validate_v7(doc):
    """Port of ImpulseResponseFile.Validate() (Resonalyze d11186e) for the members this
    module writes; raises ConversionError with the same complaint the C# would."""
    def fail(msg):
        raise ConversionError(msg)
    if doc.get("format") != FORMAT:
        fail(f"Unsupported file format '{doc.get('format')}'.")
    v = doc.get("version")
    if not isinstance(v, int) or v < 4 or v > VERSION:
        fail(f"Unsupported impulse response version {v}.")
    fs = doc.get("sampleRate")
    if not isinstance(fs, int) or fs < 44_100 or fs > 768_000:
        fail("The sample rate is outside the supported range.")
    if doc.get("bits") not in (16, 24):
        fail("Only 16-bit and 24-bit measurements are supported.")
    lo, hi = float(doc.get("lowFrequencyHz", 0)), float(doc.get("highFrequencyHz", 0))
    if lo > 0 or hi > 0:
        if (not math.isfinite(lo) or not math.isfinite(hi) or lo <= 0 or hi <= lo
                or hi > fs / 2.0 * (1.0 + 1e-3)):
            fail("The sweep frequency band is invalid.")
    else:
        octaves = doc.get("octaves", 0)
        if octaves < 1 or octaves > 24:
            fail("The octave count is outside the supported range.")
    dur = float(doc.get("sweepDurationSeconds", 0))
    if not math.isfinite(dur) or dur <= 0 or dur > 3_600:
        fail("The sweep duration is invalid.")
    if doc.get("playChannel") not in PLAY_CHANNELS:
        fail("The playback channel is invalid.")
    if doc.get("measurementMode") not in ("SweepDeconvolution", "LoopbackTransfer"):
        fail("The measurement mode is invalid.")
    if doc.get("timingReference") not in ("SynchronizedLoopback", "RecordedSweep"):
        fail("The timing reference is invalid.")
    sweep = np.asarray(doc.get("sweepDeconvolutionRealSamples", ()), dtype=np.float64)
    if sweep.size == 0:
        fail("The sweep deconvolution impulse response contains no samples.")
    spk = doc.get("sweepDeconvolutionPeakIndex")
    if not isinstance(spk, int) or spk < 0 or spk >= sweep.size:
        fail("The sweep deconvolution peak index is outside the sample array.")
    runs, accepted = doc.get("averageRunCount", 1), doc.get("acceptedAverageRunCount", 1)
    if runs < 1 or accepted < 1:
        fail("The averaging run counts are invalid.")
    if accepted > runs:
        fail("Accepted averaging runs exceed requested runs.")
    transfer = doc.get("transferRealSamples")
    if transfer is not None:
        transfer = np.asarray(transfer, dtype=np.float64)
        if transfer.size == 0:
            fail("The transfer impulse response contains no samples.")
    if doc.get("measurementMode") == "LoopbackTransfer" and transfer is None:
        fail("Loopback transfer files must include transfer impulse response samples.")
    if transfer is not None:
        tpk = doc.get("transferPeakIndex")
        if not isinstance(tpk, int) or tpk < 0 or tpk >= transfer.size:
            fail("The transfer peak index is outside the sample array.")
    if not np.all(np.isfinite(sweep)):
        fail("Sweep deconvolution impulse response sample is not a finite number.")
    if transfer is not None and not np.all(np.isfinite(transfer)):
        fail("Transfer impulse response sample is not a finite number.")
    coh = doc.get("transferCoherence")
    if coh is not None:
        if transfer is None:
            fail("Transfer coherence requires transfer impulse response samples.")
        if len(coh) != transfer.size // 2 + 1:
            fail("Transfer coherence length does not match the transfer impulse response.")
    return True


# ------------------------------------------------------------------- JSON I/O

def _fmt(v):
    return format(float(v), ".9g")


def dumps_v7(doc):
    """Serialise like System.Text.Json expects (camelCase members already), arrays on
    one line each with 9 significant digits (the source is float32; the shifted transfer
    keeps its extra digits)."""
    parts = ["{"]
    items = list(doc.items())
    for idx, (key, val) in enumerate(items):
        comma = "," if idx < len(items) - 1 else ""
        if isinstance(val, np.ndarray) or (isinstance(val, (list, tuple)) and val
                                           and isinstance(val[0], (float, np.floating))):
            body = ",".join(_fmt(v) for v in np.asarray(val).ravel())
            parts.append(f'  "{key}": [{body}]{comma}')
        else:
            parts.append(f'  "{key}": {json.dumps(val, ensure_ascii=False)}{comma}')
    parts.append("}")
    return "\n".join(parts) + "\n"


def write_v7(doc, path):
    validate_v7(doc)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dumps_v7(doc))
    os.replace(tmp, path)
    return path


def load_v7(path):
    """Read a file back (ours or Resonalyze's) into the same dict shape, arrays as numpy."""
    with open(path, encoding="utf-8-sig") as fh:
        doc = json.load(fh)
    for key in ("sweepDeconvolutionRealSamples", "sweepDeconvolutionImaginarySamples",
                "transferRealSamples", "transferImaginarySamples", "transferCoherence"):
        if doc.get(key) is not None:
            doc[key] = np.asarray(doc[key], dtype=np.float64)
    return doc


# --------------------------------------------------------------- live REW path

def _floats_be(b64):
    return np.frombuffer(base64.b64decode(b64), dtype=">f4").astype(np.float64)


def fetch_rew(mid, base_url=None):
    """Pull one REW measurement (by index or uuid) — metadata + RAW impulse response.
    Read-only (GET). Returns a dict ready for `convert_rew_record`."""
    import rew_api
    if base_url:
        rew_api.BASE_URL = base_url
    meta = rew_api.get_measurement(mid)
    ir = rew_api._get(f"/measurements/{mid}/impulse-response?normalised=false")
    if ir.get("unit") != "percent":
        raise ConversionError(f"expected the raw IR in percent, REW served unit={ir.get('unit')!r}")
    return {
        "rew_id": str(mid),
        "meta": meta,
        "ir_percent": _floats_be(ir["data"]),
        "sample_rate": ir["sampleRate"],
        "start_time_s": ir["startTime"],
        "timing_reference": ir.get("timingReference"),
        "timing_ref_time_s": ir.get("timingRefTime"),
        "timing_offset_s": ir.get("timingOffset", 0.0),
        "delay_s": ir.get("delay"),
    }


def convert_rew_record(rec, *, bits=24, play_channel="Left", sweep_seconds=None,
                       averages=1, protective_hpf=None, extra=None):
    """A `fetch_rew` record (or an equivalent dict) → (document, info)."""
    meta = rec.get("meta") or {}
    src = {
        "rewTitle": meta.get("title"),
        "rewUuid": meta.get("uuid"),
        "rewMeasuredAt": meta.get("date"),
        "rewVersion": meta.get("rewVersion"),
        "rewNotes": meta.get("notes"),
        "rewDelayS": rec.get("delay_s"),
        "rewTimeOfIrPeakS": meta.get("timeOfIRPeakSeconds"),
        "rewTimeOfIrStartS": meta.get("timeOfIRStartSeconds"),
        "rewTimingReference": rec.get("timing_reference"),
        "rewTimingOffsetS": rec.get("timing_offset_s"),
        "rewSignalToNoiseDb": meta.get("signalToNoisedB"),
        "rewSplOffsetDb": meta.get("splOffsetdB"),
        "protectiveHighPass": protective_hpf,
    }
    if extra:
        src.update(extra)
    x = np.asarray(rec["ir_percent"], dtype=np.float64) / 100.0
    return build_v7(
        x, rec["sample_rate"], rec["start_time_s"],
        timing_reference=rec.get("timing_reference"),
        timing_offset_s=rec.get("timing_offset_s") or 0.0,
        low_hz=meta.get("startFreq"), high_hz=meta.get("endFreq"),
        bits=bits, play_channel=play_channel, sweep_seconds=sweep_seconds,
        averages=averages, rew_source=src)


def _parse_hpf(spec):
    """'100:LR:24' → {'hz': 100.0, 'family': 'LR', 'slopeDbPerOct': 24}"""
    hz, fam, slope = spec.split(":")
    return {"hz": float(hz), "family": fam, "slopeDbPerOct": int(slope)}


def _hpf_from_record(record, channel):
    """The protective high-pass the capture round recorded for `channel`, in `--hpf` shape.

    ONE source for one fact (2026-08-24): the round's record (`process.py capture-protective`)
    is where the chain in force during a sweep is written down, and the v7 manifest repeats it
    rather than being told separately. Returns `(state, value)`: `("raw", {...})` for a recorded
    high-pass, `("bare", None)` when the record says nothing was in the chain, `("unknown", None)`
    when nobody recorded the channel -- a manifest must then carry nothing rather than a guess.
    A recorded LOW-pass has no slot in this format and is reported in the manifest note instead.
    """
    import protective as prot
    legs = prot.legs_of(record, channel)
    if legs is None:
        return "unknown", None
    hp = legs.get("hp")
    if not isinstance(hp, dict) or not hp.get("f"):
        return "bare", None
    return "raw", {"hz": float(hp["f"]), "family": str(hp.get("type", "LR")),
                   "slopeDbPerOct": int(hp["slope"])}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--title", action="append", default=[],
                    help='REW measurement title, optionally "=outname" (repeatable)')
    ap.add_argument("--id", action="append", default=[],
                    help='REW index/uuid, optionally "=outname" (titles are safer; index order is not stable)')
    ap.add_argument("--out", help="output directory")
    ap.add_argument("--bits", type=int, default=24)
    ap.add_argument("--play-channel", default="Left", choices=PLAY_CHANNELS)
    ap.add_argument("--sweep-seconds", type=float, default=None)
    ap.add_argument("--averages", type=int, default=1)
    ap.add_argument("--hpf", action="append", default=[],
                    help="protective high-pass in force during the sweep: NAME=HZ:FAMILY:SLOPE, e.g. m_L=100:LR:24")
    ap.add_argument("--process", default=None, metavar="DIR",
                    help="the project's process/ dir: each title's protective high-pass is read "
                         "from the capture round recorded for its _N version (capture-protective), "
                         "so the manifest and the round never disagree; --hpf still overrides")
    ap.add_argument("--note", default=None, help="free-text provenance note for the manifest")
    ap.add_argument("--rew", default=None, help="REW API base URL (default http://localhost:4735)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.out or not (args.title or args.id):
        ap.error("--out and at least one --title/--id are required (or --selftest)")
    import rew_api
    if args.rew:
        rew_api.BASE_URL = args.rew
    hpf = {k: _parse_hpf(v) for k, v in (s.split("=", 1) for s in args.hpf)}
    os.makedirs(args.out, exist_ok=True)
    manifest = {
        "converter": CONVERTER, "converterVersion": CONVERTER_VERSION,
        "createdAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rewApi": rew_api.BASE_URL, "note": args.note,
        "protectiveSource": ("the capture round's record (process.py capture-protective), "
                             "--hpf overriding where given" if args.process else
                             "--hpf only; no process round consulted"),
        "timeBase": "transferRealSamples[0] is the loopback reference (t = 0); "
                    "sweepDeconvolutionRealSamples is REW's buffer as served (t_i = startTimeS + i / sampleRate)",
        "amplitude": "fraction of full scale (REW percent / 100, normalised=false) — relative channel "
                     "levels are meaningful within one set",
        "files": {},
    }
    jobs = []
    proc = None
    if args.process:
        _state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
        if _state_dir not in sys.path:
            sys.path.insert(0, _state_dir)
        from process import Process
        import naming
        proc = Process(args.process)
    for spec in args.title:
        title, _, name = spec.partition("=")
        mid = rew_api.find_measurement_id(title)
        name = name or title
        if proc is not None:
            parsed = naming.parse_name(title)
            record = proc.protective_record_for(parsed["version"]) if parsed else None
            state, from_round = (_hpf_from_record(record, parsed["code"]) if parsed and record
                                 else ("unknown", None))
            if name in hpf and from_round and hpf[name] != from_round:
                ap.error(f"{name}: --hpf {hpf[name]} disagrees with the round's record "
                         f"{from_round} for {title!r}; one fact, one source -- fix the round")
            if name not in hpf and state == "raw":
                hpf[name] = from_round
            print(f"{name:8} protective from round: {state}"
                  + (f" {from_round['hz']:g}:{from_round['family']}:{from_round['slopeDbPerOct']}"
                     if from_round else ""), file=sys.stderr)
        jobs.append((mid, name))
    for spec in args.id:
        mid, _, name = spec.partition("=")
        jobs.append((mid, name or f"rew_{mid}"))
    for mid, name in jobs:
        rec = fetch_rew(mid)
        doc, info = convert_rew_record(
            rec, bits=args.bits, play_channel=args.play_channel,
            sweep_seconds=args.sweep_seconds, averages=args.averages,
            protective_hpf=hpf.get(name))
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        path = os.path.join(args.out, safe + ".json")
        write_v7(doc, path)
        entry = {k: v for k, v in doc["rewSource"].items()}
        entry.update({"file": os.path.basename(path), "rewId": str(mid),
                      "sampleRate": doc["sampleRate"], "samples": info["samples"],
                      "transferPeakIndex": info["transfer_peak_index"],
                      "transferPeakTimeS": info["transfer_peak_time_s"],
                      "sweepDeconvolutionPeakIndex": info["sweep_peak_index"]})
        manifest["files"][name] = entry
        print(f"{name:8} ← #{mid} {rec['meta'].get('title')!r}: fs {doc['sampleRate']} n {info['samples']} "
              f"t0@{info['t0_index']:.3f} peak {info['peak_dbfs']:.2f} dBFS "
              f"transfer peak {info['transfer_peak_time_s'] * 1e3:.4f} ms (REW delay "
              f"{(rec.get('delay_s') or 0) * 1e3:.4f} ms) → {path}", file=sys.stderr)
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"wrote {len(jobs)} file(s) + manifest.json to {args.out}", file=sys.stderr)
    return 0


# -------------------------------------------------------------------- selftest

def _synthetic_ir(n, fs, t_peak_s, start_time_s, width_s=0.4e-3):
    """A band-limited pulse (Gaussian-windowed sinc, ~8 kHz) centred at t_peak on REW's
    axis t_i = start_time + i/fs, plus a small 'harmonic' image at negative time."""
    t = start_time_s + np.arange(n) / fs
    u = (t - t_peak_s) / width_s
    pulse = np.sinc(u * 2.0) * np.exp(-0.5 * u ** 2)
    tg = t - (t_peak_s - 0.008)                       # an image 8 ms before the peak (t < 0)
    ghost = 0.05 * np.sinc(tg / width_s) * np.exp(-0.5 * (tg / width_s) ** 2)
    return 0.3 * (pulse + ghost)


def _selftest():
    # One fact, one source: the round's record maps onto the manifest's --hpf shape, and the
    # three states stay distinct -- "bare" and "unknown" must never both come out as None-and-move-on.
    _rec = {"channels": {"m_L": {"hp": {"f": 100, "type": "LR", "slope": 24}}, "w_L": "OFF"}}
    assert _hpf_from_record(_rec, "m_L") == ("raw", {"hz": 100.0, "family": "LR", "slopeDbPerOct": 24})
    assert _hpf_from_record(_rec, "w_L") == ("bare", None)
    assert _hpf_from_record(_rec, "tw_L") == ("unknown", None)
    assert _hpf_from_record(None, "m_L") == ("unknown", None)
    fs, n = 96000, 1 << 15
    # 1. fractional t0: peak at +4.7788 ms, t = 0 at index 1000.37
    start = -1000.37 / fs
    x = _synthetic_ir(n, fs, 4.7788e-3, start)
    doc, info = build_v7(x, fs, start, low_hz=20.14, high_hz=20037.8, bits=24)
    assert doc["timingReference"] == "SynchronizedLoopback" and doc["measurementMode"] == "LoopbackTransfer"
    assert abs(info["t0_index_fraction"] - 0.37) < 1e-9
    err_samples = (info["transfer_peak_time_s"] - 4.7788e-3) * fs
    assert abs(err_samples) < 0.02, f"fractional shift lost timing: {err_samples:.4f} samples"
    assert info["sweep_peak_index"] == int(np.argmax(np.abs(x)))
    # 2. integer t0 stays a bit-exact roll of REW's samples
    start_i = -1000.0 / fs
    xi = _synthetic_ir(n, fs, 4.7788e-3, start_i)
    doc_i, _ = build_v7(xi, fs, start_i, low_hz=20.0, high_hz=20000.0)
    assert np.array_equal(doc_i["transferRealSamples"], np.roll(xi, -1000))
    # 3. amplitude and negative-time content are preserved (energy identical, tail = pre-roll)
    y = doc["transferRealSamples"]
    assert abs(np.sum(y ** 2) - np.sum(x ** 2)) < 1e-9 * np.sum(x ** 2)
    ghost_at = int(round((4.7788e-3 - 0.008) * fs))         # negative → wraps to the tail
    assert abs(y[(ghost_at) % n]) > 0.01, "pre-roll content did not wrap to the tail"
    # 4. JSON round trip through the exact bytes we write, then Validate() again
    text = dumps_v7(doc)
    back = json.loads(text)
    for key in ("sweepDeconvolutionRealSamples", "transferRealSamples"):
        back[key] = np.asarray(back[key])
    validate_v7(back)
    assert back["transferPeakIndex"] == info["transfer_peak_index"]
    assert np.max(np.abs(back["transferRealSamples"] - y)) < 1e-8 * np.max(np.abs(y))
    assert back["rewSource"]["converter"] == CONVERTER
    # 5. refusals: not on the loopback base / a timing offset / bad bits / bad band
    for kwargs, why in ((dict(timing_reference="Acoustic"), "timing reference"),
                        (dict(timing_offset_s=0.0077), "timing offset"),
                        (dict(bits=20), "bits"),
                        (dict(high_hz=60000.0), "band above Nyquist")):
        base = dict(low_hz=20.0, high_hz=20000.0)
        base.update(kwargs)
        try:
            build_v7(x, fs, start, **base)
        except ConversionError:
            pass
        else:
            raise AssertionError(f"accepted a file it must refuse: {why}")
    # 6. the Validate() port catches what the C# catches
    bad = dict(doc)
    bad["transferPeakIndex"] = n
    try:
        validate_v7(bad)
    except ConversionError as e:
        assert "transfer peak index" in str(e)
    else:
        raise AssertionError("out-of-range transfer peak index passed validation")
    print(f"selftest OK — fractional t0 kept to {abs(err_samples):.4f} samples, integer t0 bit-exact, "
          f"round trip + Validate() port + refusals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
