#!/usr/bin/env python3
"""The two windows a measured impulse is read through, and the one place their definitions live.

A car's impulse response holds two different measurements, and reading both through one window is
how a junction number stops being comparable between days:

  * **`steady`** — the WHOLE record: the driver plus everything the cabin does with it. This is
    what a magnitude is judged against a target curve, because that is what a listener hears in
    that seat over time. It is what `predict._spectrum_on_grid` has always read, and nothing about
    it changes here.
  * **`gate`** — the first few milliseconds after the response STARTS: the direct sound, before
    the first boundary comes back. Phase, arrival and the junctions read through this one, because
    a cancellation between two drivers is a property of what leaves them, and a reflection 3 ms
    later is not part of that question -- it is a comb laid over the answer.

Bought on the desk of the Passat, 02-07.09.2026 (autosound-hub `RES-006`, the user's ruling
2026-09-08): a junction read across the whole record predicted −1.2 dB at 3775 Hz for a mid↔tweeter
change that measured −3.8, and the L−R arrival of the mids was stable at −0.24…−0.31 ms through
gates of 0.7…5 ms while an ungated read of 400-1000 Hz jumped by whole periods. Two windows are not
an refinement of one; they answer two questions, and the answer has to say which it answered.

WHAT ANCHORS THE GATE, and why not the peak. The window opens at the **detected start** of the
response (`analysis.first_arrival`, the leading edge at −20 dB of the peak, minus a margin), never
at the peak: the global peak of a door midbass can BE a reflection, and a window hung on it starts
after the direct sound it was supposed to keep (`analysis.arrival_triangulate` exists for exactly
this doubt, and its `ILL-POSED` verdict -- a sub -- is passed through here rather than papered
over: a channel whose start cannot be located has no gated reading, and that is said).

WHAT THE WINDOW LOOKS LIKE, and what its LENGTH is measured from. Full weight from a margin before
the arrival through the arrival itself, then a decay to zero over the gate as the second half of a
Hann. No rise, and no taper on the margin: attenuating the direct sound is the one thing a gate must
not do -- and a gate length is therefore "how long AFTER the arrival we listen", not a slot the
arrival has to fit inside. (Measured from the window's own start instead, the direct sound lands at
a different point of the taper at every frequency, and an FDW read comes out with several dB of
frequency-dependent scale that is the margin, not the car. Found in this module's own selftest.)
Beyond the shape, the independent path this is checked against
(`car/…/scripts-2026-09-05/gate_sweep.py`) anchors on the band's envelope PEAK -- two anchors and
two rulers agreeing on the mids' arrival to a hundredth of a millisecond is the evidence that
neither is an artefact.

FDW (`cycles=N`) is the same read with a window that is N cycles long AT EACH FREQUENCY: 6 cycles
is 300 ms at 20 Hz and 0.6 ms at 10 kHz, which is what makes one curve show the bass with its room
and the treble without it. Implemented as it is defined -- one DFT per grid frequency over that
frequency's own window -- not as a smoothing that approximates it.

Deps: numpy. `--selftest` is offline and synthetic.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import analysis  # noqa: E402

#: The names every number carries. A junction read one way and compared with one read the other is
#: the mistake this vocabulary exists to make visible.
STEADY = "steady"
GATE = "gate"

#: How far before the detected start the window opens. The start is an estimate with a leading
#: edge's uncertainty; opening exactly on it risks shaving the first cycle of the direct sound,
#: and 0.3 ms of margin costs nothing (11 cm of path -- shorter than any first reflection in a
#: car). The independent path uses the same margin.
PRE_MS = 0.3

#: A gate this short holds less than one cycle below ~1 kHz; the read is refused rather than
#: returned as a number. (0.7 ms is the shortest gate the desk's sweep used, and at 300 Hz it is
#: a fifth of a cycle -- which is why the desk read the ARRIVAL there, a cross-correlation over a
#: band, and not a per-bin phase.)
MIN_GATE_MS = 0.2


def onset_index(ir, fs, *, t0_s=0.0, band=None, rel_db=-20.0, pre_ms=PRE_MS):
    """`(index, info)` of where the window opens: the detected start of the response, minus a margin.

    `band` band-limits the IR before the edge is looked for -- for a channel whose own crossover
    already band-limits it this changes little, and it is how a SHARED read (two channels, one
    band) is made to anchor on the same physics.

    `info["verdict"]` is `analysis.arrival_triangulate`'s, and it is INFORMATION, not a refusal:
    the four estimators disagreeing is what happens when the biggest peak is a reflection -- which
    is the very case a gate is for, and where the leading edge is the estimator you want. It is
    passed through so a reader sees it beside the number (a sub, four estimators 13 ms apart, has
    no meaningful gated read at all and the spread says so). `t0_s` only shifts the reported times
    onto the absolute base; the index does not depend on it.
    """
    x = np.asarray(ir, dtype=float)
    fs = float(fs)
    probe = _bandpass(x, fs, band) if band else x
    times = float(t0_s) + np.arange(x.size) / fs
    tri = analysis.arrival_triangulate(times.tolist(), probe.tolist())
    edge = analysis.first_arrival(times.tolist(), probe.tolist(), rel_threshold_db=rel_db)
    if edge is None:
        return None, {"verdict": "NO EDGE", "why": "no sample within the threshold of the peak"}
    i0 = int(edge["index"]) - int(round(pre_ms / 1000.0 * fs))
    return max(0, i0), {"verdict": tri["verdict"], "spread_ms": tri["spread_ms"],
                        "edge_ms": edge["arrival_time_ms"], "pre_ms": pre_ms,
                        "band_hz": list(band) if band else None}


def _bandpass(x, fs, band):
    """4th-order zero-phase band-pass. Zero-phase on purpose: the anchor is a TIME, and a filter
    that delays the signal moves the very thing being located."""
    from scipy.signal import butter, sosfiltfilt
    lo, hi = float(band[0]), float(band[1])
    nyq = fs / 2.0
    sos = butter(4, [max(lo, 1.0) / nyq, min(hi, nyq * 0.999) / nyq], btype="band", output="sos")
    return sosfiltfilt(sos, x)


def window_lengths_ms(freqs, *, gate_ms=None, cycles=None, min_ms=MIN_GATE_MS, max_ms=None):
    """The window length at each grid frequency: a constant (`gate_ms`) or `cycles`/f (FDW).

    Clamped into `[min_ms, max_ms]` and the clamp is visible in the returned array, because a
    reader of a number needs the length that was actually used, not the one that was asked for.
    """
    f = np.asarray(freqs, dtype=float)
    if (gate_ms is None) == (cycles is None):
        raise ValueError("name exactly one of gate_ms (a fixed gate) or cycles (FDW)")
    lens = (np.full(f.shape, float(gate_ms)) if gate_ms is not None
            else float(cycles) * 1000.0 / np.maximum(f, 1e-9))
    lens = np.maximum(lens, float(min_ms))
    if max_ms is not None:
        lens = np.minimum(lens, float(max_ms))
    return lens


def _taper(n):
    """Open at 1.0, decay to 0 over the window -- the second half of a Hann."""
    if n <= 1:
        return np.ones(max(n, 1))
    return np.hanning(2 * n)[n:]


def windowed_spectrum(ir, fs, t0_s, freqs, *, gate_ms=None, cycles=None, band=None,
                      drift_samples=0.0, i_edge=None, max_ms=None):
    """`(H, info)` -- the complex response through the GATE, on `freqs`, phase referenced to t = 0.

    One DFT per grid frequency over that frequency's own window, which is the definition of a
    windowed spectrum and (for FDW) the only way to get one without approximating it. The phase
    keeps the ABSOLUTE time base (`t0_s` is the time of sample 0, the loopback reference), so a
    gated reading still carries arrival -- which is what the L−R arrival check reads.

    The window: full weight from `PRE_MS` before the detected arrival, then the decay over
    `gate_ms` (or `cycles`/f) FROM THE ARRIVAL. `i_edge` pins that arrival from outside -- two
    channels compared over one band should be anchored the same way, and a caller that has already
    located it (or wants the pair anchored on one member) says so rather than having it re-derived.
    """
    x = np.asarray(ir, dtype=float)
    fs = float(fs)
    f = np.asarray(freqs, dtype=float)
    t0 = float(t0_s) - float(drift_samples) / fs
    info = {"window": GATE, "gate_ms": gate_ms, "cycles": cycles, "sample_rate": fs}
    if i_edge is None:
        i0, anchor = onset_index(x, fs, t0_s=t0, band=band)
        info["anchor"] = anchor
        if i0 is None:
            return None, dict(info, refused=anchor["why"])
        i_edge = i0 + int(round(PRE_MS / 1000.0 * fs))
    else:
        i_edge = int(i_edge)
        i0 = max(0, i_edge - int(round(PRE_MS / 1000.0 * fs)))
        info["anchor"] = {"verdict": "GIVEN", "edge_index": i_edge}
    info["edge_index"] = int(i_edge)
    info["arrival_ms"] = (t0 + i_edge / fs) * 1000.0
    info["pre_ms"] = PRE_MS
    room = x.size - i_edge
    lens = window_lengths_ms(f, gate_ms=gate_ms, cycles=cycles,
                             max_ms=min(room / fs * 1000.0, max_ms or np.inf))
    info["length_ms"] = [float(v) for v in lens]
    flat = x[i0:i_edge]                                  # the margin, at full weight
    H = np.zeros(f.size, dtype=complex)
    # Grouped by window length: every frequency asking for the same number of samples shares one
    # windowed segment, so a fixed gate is ONE segment and an FDW is one per distinct length.
    n_by_len = np.maximum(np.round(lens / 1000.0 * fs).astype(int), 1)
    for n in np.unique(n_by_len):
        which = np.nonzero(n_by_len == n)[0]
        seg = np.concatenate([flat, x[i_edge:i_edge + n] * _taper(int(n))])
        t = t0 + (i0 + np.arange(seg.size)) / fs
        H[which] = np.exp(-2j * np.pi * np.outer(f[which], t)) @ seg
    return H, info


def gate_ir(ir, fs, *, t0_s=0.0, band=None, gate_ms=1.0, i_edge=None):
    """`(gated, i_edge, info)` -- the IR band-limited and windowed IN PLACE (absolute sample
    positions kept, everything outside the window zero), for a reading that lives in time.

    Kept in place rather than cut out because the thing being read is a TIME: a cross-correlation
    of two cut-out segments answers a question about the cuts (`gate_sweep.py` corrects for its own
    two offsets, and that correction is where a time base goes missing).
    """
    x = np.asarray(ir, dtype=float)
    fs = float(fs)
    y = _bandpass(x, fs, band) if band else x.copy()
    info = {}
    if i_edge is None:
        i0, anchor = onset_index(y, fs, t0_s=t0_s)
        info["anchor"] = anchor
        if i0 is None:
            return None, None, dict(info, refused=anchor["why"])
        i_edge = i0 + int(round(PRE_MS / 1000.0 * fs))
    else:
        i_edge = int(i_edge)
        i0 = max(0, i_edge - int(round(PRE_MS / 1000.0 * fs)))
        info["anchor"] = {"verdict": "GIVEN", "edge_index": i_edge}
    n = max(int(round(float(gate_ms) / 1000.0 * fs)), 1)
    out = np.zeros_like(y)
    out[i0:i_edge] = y[i0:i_edge]
    seg = y[i_edge:i_edge + n]
    out[i_edge:i_edge + seg.size] = seg * _taper(n)[:seg.size]
    info.update({"edge_index": int(i_edge), "arrival_ms": (float(t0_s) + i_edge / fs) * 1000.0,
                 "gate_ms": float(gate_ms), "band_hz": list(band) if band else None})
    return out, int(i_edge), info


def arrival_between(ir_a, ir_b, fs, *, band, gate_ms, t0_a=0.0, t0_b=0.0, max_lag_ms=5.0):
    """How much later A arrives than B over `band`, read through the gate: `(ms, info)`.

    The cross-correlation of the two gated, band-limited responses, refined to a fraction of a
    sample by a parabola through the peak -- the ruler the desk used (`gate_sweep.py`) and the one
    that answers on a 0.7 ms gate, where a SPECTRUM over the same band has barely one resolution
    cell and its matched filter locks a whole cycle away (measured on the `_60` mids: +0.57 ms
    against +0.26, one cycle at 2.2 kHz -- so `predict.arrival_difference_ms` stays what it is,
    the alias guard on FULL-band solos over a junction band, and this is the gated read).

    **`t0_a` / `t0_b` are each measurement's own time base** (REW's `startTime`, the time of its
    sample 0) and they are not optional decoration: on the `_60` mids the two buffers begin
    0.535 ms apart, and a reading that assumes one shared origin comes out with the WRONG SIGN --
    L 0.27 ms early instead of 0.26 late (the desk's 05.09 sweep; REW's own `delay` field settles
    it, +0.535 ms peak to peak). A v7 file has this folded in already (sample 0 IS t = 0), so its
    `t0` is zero; a live REW pull carries it per measurement.

    `info` carries the edge difference and both triangulation verdicts beside the number: when the
    two disagree the question is ill-posed in that band, and the number is not to be pinned. On the
    `_60` mids they disagree by the whole answer -- edge +0.32 ms, a 0.7 ms gate 0.00, the energy
    peaks 0.53 apart -- and `arrival_triangulate` calls both channels ILL-POSED, which is the
    honest state of that question in that band and not something a ruler can settle.

    Two limits, both measured on a synthetic pure delay in this module's selftest:
      * a gate SHORTER than the two arrivals are apart cannot hold both, and the read is refused
        rather than returned (1.0 ms of delay through a 1.0 ms gate reads 0.50 -- half, and shaped
        exactly like a measurement);
      * one shared window weights the two arrivals differently, which biases the shortest gates
        LOW by about a tenth of the answer (0.238 against 0.260 at 0.7 ms, 0.256 at 1.5 ms,
        0.260 from 5 ms). Read the trend, not one gate -- which is what a gate sweep is for.
    """
    fs = float(fs)
    # ONE window over both, in ABSOLUTE time, opened at the EARLIER of the two arrivals. Anchoring
    # each channel on its own arrival is the trap: the two windows then start exactly the delay
    # apart, and the windows absorb the very shift being measured -- on the `_60` mids that read
    # 0.00 ms at a 0.7 ms gate and only crept back to +0.25 by 3 ms, against +0.23…+0.29 from the
    # shared window (measured while writing this, and the reason the anchor is shared).
    _, edge_a, ia = gate_ir(ir_a, fs, t0_s=t0_a, band=band, gate_ms=gate_ms)
    _, edge_b, ib = gate_ir(ir_b, fs, t0_s=t0_b, band=band, gate_ms=gate_ms)
    if edge_a is None or edge_b is None:
        return None, {"refused": (ia.get("refused") or ib.get("refused")), "a": ia, "b": ib}
    open_ms = min(ia["arrival_ms"], ib["arrival_ms"])
    shared_a = int(round((open_ms / 1000.0 - float(t0_a)) * fs))
    shared_b = int(round((open_ms / 1000.0 - float(t0_b)) * fs))
    ga, _, ia2 = gate_ir(ir_a, fs, t0_s=t0_a, band=band, gate_ms=gate_ms, i_edge=shared_a)
    gb, _, ib2 = gate_ir(ir_b, fs, t0_s=t0_b, band=band, gate_ms=gate_ms, i_edge=shared_b)
    edge_delta = ia["arrival_ms"] - ib["arrival_ms"]
    # Compared in SAMPLES, not in floating milliseconds: two arrivals exactly one gate apart come
    # out 0.9999999999999998 ms against a 1.0 ms gate, and a boundary this check exists to hold
    # must not turn on the last bit of a float.
    apart = abs(round((edge_delta / 1000.0) * fs))
    if apart >= max(int(round(float(gate_ms) / 1000.0 * fs)), 1):
        return None, {"refused": f"the two arrivals are {edge_delta:+.3f} ms apart and the gate is "
                                 f"{float(gate_ms):g} ms -- one of them is at or outside the window's "
                                 f"end; ask for a gate longer than {abs(edge_delta):.2f} ms",
                      "edge_difference_ms": edge_delta, "a": ia, "b": ib}
    from scipy.signal import correlate
    c = correlate(ga, gb, mode="full", method="fft")
    k = int(np.argmax(c))
    frac = 0.0
    if 0 < k < c.size - 1:
        y0, y1, y2 = float(c[k - 1]), float(c[k]), float(c[k + 1])
        den = y0 - 2.0 * y1 + y2
        frac = 0.0 if den == 0 else 0.5 * (y0 - y2) / den
    lag = (k + frac) - (gb.size - 1)                      # A[n] ~ B[n - lag]: A later by lag
    ms = lag / fs * 1000.0 + (float(t0_a) - float(t0_b)) * 1000.0
    if abs(ms) > max_lag_ms:
        return None, {"refused": f"the correlation peaks {ms:+.2f} ms out, beyond the "
                                 f"{max_lag_ms:g} ms this read allows", "a": ia, "b": ib}
    return float(ms), {
        "window": GATE, "gate_ms": float(gate_ms), "band_hz": [float(band[0]), float(band[1])],
        "opened_at_ms": open_ms, "arrival_a_ms": ia["arrival_ms"], "arrival_b_ms": ib["arrival_ms"],
        "edge_difference_ms": edge_delta,
        "verdict_a": ia["anchor"]["verdict"], "verdict_b": ib["anchor"]["verdict"],
    }


def steady_note():
    """What the other window is, for a report that has to name it."""
    return ("the whole record (the cabin included) -- what a magnitude is judged against a target; "
            "our records run 2.73 s, where Resonalyze's own magnitude window is ~680 ms from the "
            "detected start (`resonalyze-virtual-dsp.md`), a deviation that matters only for the "
            "very late tail")


def _selftest():
    fs = 96000.0
    n = 1 << 15
    t0 = -0.001                              # sample 0 sits 1 ms before the loopback reference
    fgrid = 20.0 * 2.0 ** (np.arange(int(np.floor(np.log2(20000.0 / 20.0) * 48)) + 1) / 48.0)

    # A direct arrival at 2.0 ms and a BIGGER reflection 3.0 ms after it -- the shape a gate
    # exists for, and the shape that fools a peak-anchored window.
    def build(direct_ms, refl_gain=1.4, refl_ms=3.0):
        x = np.zeros(n)
        i_d = int(round((direct_ms / 1000.0 - t0) * fs))
        x[i_d] = 1.0
        x[i_d + int(round(refl_ms / 1000.0 * fs))] = refl_gain
        return x, i_d

    x, i_d = build(2.0)
    i0, anchor = onset_index(x, fs, t0_s=t0)
    # The anchor is the DIRECT arrival minus the margin, not the (larger) reflection -- and the
    # reported edge is on the ABSOLUTE base (2.0 ms), not counted from sample 0.
    assert abs(i0 - (i_d - PRE_MS / 1000.0 * fs)) <= 1, (i0, i_d)
    assert abs(anchor["edge_ms"] - 2.0) < 0.02, anchor
    # Four estimators 3 ms apart, because the biggest peak IS the reflection: the verdict says so
    # and the edge is still right. Information, not a refusal -- this is the case a gate is for.
    assert anchor["verdict"] == "ILL-POSED" and abs(anchor["spread_ms"] - 3.0) < 0.05, anchor
    quiet, qi = build(2.0, refl_gain=0.35)
    _, q_anchor = onset_index(quiet, fs, t0_s=t0)
    assert q_anchor["verdict"] == "TRUSTED", q_anchor

    # A 2 ms gate excludes the reflection 3 ms after the arrival: the magnitude of a single
    # impulse is flat. The steady read of the same record combs -- the difference the two windows
    # exist to keep apart.
    Hg, info = windowed_spectrum(x, fs, t0, fgrid, gate_ms=2.0)
    mag = 20 * np.log10(np.abs(Hg))
    assert info["window"] == GATE and info["gate_ms"] == 2.0
    assert abs(info["arrival_ms"] - 2.0) < 0.02, info["arrival_ms"]
    assert float(np.ptp(mag)) < 0.5, f"a gated single impulse must read flat, got {np.ptp(mag):.2f} dB"
    Xs = np.fft.rfft(x)
    fb = np.fft.rfftfreq(n, 1.0 / fs)
    steady = 20 * np.log10(np.abs(np.interp(fgrid, fb, np.abs(Xs))) + 1e-12)
    assert float(np.ptp(steady)) > 6.0, "the whole record must show the comb the gate removed"

    # ARRIVAL survives the gate: the same impulse 0.25 ms later reads 0.25 ms later, and the
    # absolute time base is kept (phase referenced to t = 0, not to the anchor).
    y, _ = build(2.25)
    Hy, _ = windowed_spectrum(y, fs, t0, fgrid, gate_ms=2.0)
    band = (300.0, 2500.0)
    m = (fgrid >= band[0]) & (fgrid <= band[1])
    slope = np.polyfit(fgrid[m], np.unwrap(np.angle(Hy[m] * np.conj(Hg[m]))), 1)[0]
    got_ms = -slope / (2 * np.pi) * 1000.0
    assert abs(got_ms - 0.25) < 0.01, f"gated arrival difference {got_ms:.4f} ms, expected 0.250"

    # ...and the phase at t = 0 is the physical one: a 2 ms arrival is 2 ms of delay, not 2 ms
    # measured from wherever the window happened to open.
    tau = -np.polyfit(fgrid[m], np.unwrap(np.angle(Hg[m])), 1)[0] / (2 * np.pi) * 1000.0
    assert abs(tau - 2.0) < 0.01, f"absolute arrival {tau:.4f} ms, expected 2.000"

    # FDW: the length at each frequency is cycles/f, clamped by the record and by MIN_GATE_MS.
    lens = window_lengths_ms(np.array([20.0, 100.0, 1000.0, 10000.0]), cycles=6.0)
    assert np.allclose(lens, [300.0, 60.0, 6.0, 0.6]), lens
    clamped = window_lengths_ms(np.array([20.0, 10000.0]), cycles=6.0, max_ms=50.0, min_ms=1.0)
    assert np.allclose(clamped, [50.0, 1.0]), clamped
    Hf, fi = windowed_spectrum(x, fs, t0, fgrid, cycles=6.0)
    assert fi["cycles"] == 6.0 and len(fi["length_ms"]) == fgrid.size
    # 6 cycles at 20 Hz is 300 ms -- the reflection is inside it, so the bass combs; at 10 kHz the
    # window is 0.6 ms and the reflection is outside, so the top does not. One curve, both truths.
    lo = (fgrid < 60.0)
    hi = (fgrid > 5000.0)
    assert float(np.ptp(20 * np.log10(np.abs(Hf[hi])))) < 0.5, "FDW must exclude the reflection up top"
    assert float(np.ptp(20 * np.log10(np.abs(Hf[lo])))) > 1.0, "FDW must keep the room in the bass"

    # A gate longer than what is left of the record is clamped, not read past the end.
    # (`build` puts the arrival 3 ms before its reflection, so the record has room either way.)
    late, _ = build(2.0)
    Hl, li = windowed_spectrum(late, fs, t0, fgrid, gate_ms=10_000.0)
    assert max(li["length_ms"]) <= (n / fs) * 1000.0 + 1e-6, max(li["length_ms"])

    # The direct sound keeps FULL weight at every frequency: an FDW read of a single impulse is
    # flat up top, where a taper measured from the window's start would scale it by several dB.
    top = 20 * np.log10(np.abs(Hf[fgrid > 3000.0]))
    assert float(np.ptp(top)) < 0.5, f"FDW scale artefact at the top: {np.ptp(top):.2f} dB"

    # A shared arrival: two channels compared over one band can be pinned to one index, and the
    # arrival between them is then read on identical windows.
    i_edge = info["edge_index"]
    Ha, _ = windowed_spectrum(x, fs, t0, fgrid, gate_ms=2.0, i_edge=i_edge)
    Hb, ib = windowed_spectrum(y, fs, t0, fgrid, gate_ms=2.0, i_edge=i_edge)
    assert ib["anchor"]["verdict"] == "GIVEN" and ib["edge_index"] == i_edge
    slope2 = np.polyfit(fgrid[m], np.unwrap(np.angle(Hb[m] * np.conj(Ha[m]))), 1)[0]
    assert abs(-slope2 / (2 * np.pi) * 1000.0 - 0.25) < 0.01

    # The gated ARRIVAL ruler, on a pure delay it must recover at every gate: a band-limited
    # burst and the same burst 0.26 ms later. And on two records whose own time bases differ --
    # the `_60` mids' two buffers begin 0.535 ms apart -- where ignoring `t0` is what put the
    # desk's 05.09 sweep on the wrong side of zero.
    from scipy.signal import butter, sosfilt
    burst = sosfilt(butter(4, [300.0 / (fs / 2), 2500.0 / (fs / 2)], btype="band", output="sos"),
                    np.concatenate([np.zeros(int(0.002 * fs)), [1.0], np.zeros(n - int(0.002 * fs) - 1)]))
    late = np.roll(burst, int(round(0.00026 * fs)))
    for g, tol in ((0.7, 0.03), (1.0, 0.02), (1.5, 0.006), (2.0, 0.005), (5.0, 0.002)):
        got, info = arrival_between(late, burst, fs, band=(300.0, 2500.0), gate_ms=g)
        assert abs(got - 0.26) < tol, f"gate {g} ms: pure delay read {got:+.4f} ms, expected +0.260"
        assert info["window"] == GATE and info["gate_ms"] == g
    # A gate that cannot hold both arrivals is REFUSED, not answered: 1 ms of delay read through a
    # 1 ms gate comes out 0.50 -- half the truth, and shaped exactly like a measurement.
    far = np.roll(burst, int(round(0.001 * fs)))
    for g in (0.7, 1.0):
        got, info = arrival_between(far, burst, fs, band=(300.0, 2500.0), gate_ms=g)
        assert got is None and "outside the window" in info["refused"], (g, got, info)
    got, _ = arrival_between(far, burst, fs, band=(300.0, 2500.0), gate_ms=1.5)
    assert abs(got - 1.0) < 0.04, got
    # ...and the same pair with 0.535 ms of time-base difference between the two records: the
    # answer must not move, because `t0` says where each buffer begins.
    shift = int(round(0.000535 * fs))
    got, info = arrival_between(np.roll(late, shift), burst, fs, band=(300.0, 2500.0), gate_ms=2.0,
                                t0_a=-shift / fs, t0_b=0.0)
    assert abs(got - 0.26) < 0.02, f"with two time bases the read moved to {got:+.4f} ms"
    blind, _ = arrival_between(np.roll(late, shift), burst, fs, band=(300.0, 2500.0), gate_ms=2.0)
    assert abs(blind - (0.26 + 0.535)) < 0.03, f"ignoring t0 must cost exactly the offset: {blind:+.4f}"

    # A sub-shaped response: the same arrival through a causal 60 Hz low-pass, so the envelope
    # peaks many milliseconds after the edge. The four estimators then disagree by more than the
    # question can bear, and the verdict says so instead of handing back a number that looks like
    # a measurement -- the case `arrival_triangulate` was written for (a sub: 13 ms of spread).
    from scipy.signal import butter, sosfilt
    sub = sosfilt(butter(4, 60.0 / (fs / 2), btype="low", output="sos"), x)
    _, sub_anchor = onset_index(sub, fs, t0_s=t0)
    assert sub_anchor["verdict"] == "ILL-POSED" and sub_anchor["spread_ms"] > 1.0, sub_anchor

    print("selftest[windows] OK -- the gate is anchored on the DETECTED START (a bigger reflection "
          "does not move it, and the triangulation verdict says the peak would have been wrong), "
          "a 2 ms gate reads a single impulse flat where the whole record combs, "
          "arrival survives the window and stays on the absolute base (2.000 ms, and 0.250 between "
          "two channels), FDW is cycles/f clamped by the record (room in the bass, none up top) with "
          "the direct sound at full weight at every frequency, "
          "the gated arrival ruler recovers a pure 0.260 ms delay at gates 0.7-5 ms and only when "
          "each record's own t0 is given (ignoring it costs exactly the 0.535 ms offset -- the "
          "desk's 05.09 sign error), and a response with no locatable start returns its verdict "
          "instead of a number")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(_selftest() if "--selftest" in sys.argv else _selftest())
