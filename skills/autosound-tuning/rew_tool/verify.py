#!/usr/bin/env python3
"""Is this measurement there, and is it usable? — a machine verdict per title (SCR-013).

This replaced `verify_measurements.py`, a one-off script with hardcoded measurement ids (9-15),
`print`-driven output and no way to be called; that file was deleted on 2026-09-07 once it was
established that everything it did lives elsewhere -- arrivals in `timebase.py` + `analyze_impulse`,
corner candidates in `xover_candidates.py`, the usability verdict here. A front-end asking "can I
light this row green?" needs an answer, not a report.

The verdict is deliberately shallow. It says whether REW holds the measurement and whether what it
holds looks like a real capture — not whether the tune is good. Judging the sound is the method's
job and it happens elsewhere; this is the gate that stops a session analysing a sweep that never
completed, and stops a checklist showing a row as captured because a title exists.

    {"name": "tw-L_1 (sw)", "exists": true, "reachable": true, "valid": false,
     "issues": ["ir peak is 0.4 dB above the pre-ringing floor — no clear arrival"],
     "stats": {...}}

Two failure modes are kept apart on purpose. `exists: false` is "nobody measured it"; `valid:
false` is "it was measured and cannot be used", which is a different conversation with the Arbiter
and a different colour on the panel. REW itself is a third (#134): `reachable: false` is "REW did
not answer", and then `exists` is null, because nobody can say whether the title is there --
counting it "missing" sent the tuner to re-measure what REW, once started, still held. `exists:
null` with `reachable: true` is REW answering an error; with `reachable: null`, REW was not asked,
its address (`REW_API_URL`) being no address. A title REW holds more than once is `exists: true`,
`valid: false` and `ambiguous: <how many>`: there, and not usable until it is renamed.

stdlib only (plus this package's own `rew_api`/`analysis`), py3.9+.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import urllib.error

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:  # same convention as contract.py: importable by path, no install step
    sys.path.insert(0, _HERE)

import analysis as _analysis  # noqa: E402
import joint_analysis as _joint  # noqa: E402
import naming as _naming  # noqa: E402
import rew_api as _api  # noqa: E402

# The smoothing this check reads at, ASKED on the read -- the Arbiter's view is never touched (hub
# TCC-015). The level below is a mean over bins, so the GRID decides it more than the width does: REW's
# raw read is linear and put 69 % of a woofer's live bins above 1 kHz, which moved channel levels by up
# to 3 dB and changed their order on the reference car; every fractional read is log-spaced and agrees
# within 0.3 dB. 1/6 is the tone standard (docs/RESEARCH-2026-09-17-reader-smoothing.md §2.4, §6; the
# user's decision 2026-09-17). Without it the numbers followed whatever the view happened to hold.
READ_SMOOTHING = "1/6"

# An FR flat to within a fraction of a dB across the whole band is not a loudspeaker in a car; it
# is a loopback, a dead input, or REW handing back a placeholder. Seen as a "successful" capture.
_FLAT_RANGE_DB = 1.0
# Below this the sweep is in the noise: a capture whose in-band mean sits at the floor is what a
# muted channel or a disconnected mic produces.
_SILENT_MEAN_DB = -80.0
# A capture that stops short of the band it was asked for is a truncated one -- an RTA that never
# got above 200 Hz reads as "captured" by title alone.
_MIN_SPAN_FRACTION = 0.5

# What `verify.py` exits with when REW did not answer: sysexits' EX_UNAVAILABLE, the code `process.py` gives the
# same state (#134). 0 and 1 keep their meaning, so a gate that only knew those still stops on it.
EXIT_REW_UNAVAILABLE = 69


def _state(exc):
    """The `rew_state` `exc` carries, read off the exception's CLASS (#134), or None.

    Never the class itself -- a copy of `rew_api` loaded by path (TCC's) raises classes of its own -- and never the
    instance: on Python 3.9 an `HTTPError` built without a body answers any attribute it lacks with `KeyError:
    'file'`, which would turn REW's answer into a traceback here."""
    return getattr(type(exc), "rew_state", None)


def _rew_down(exc):
    """Whether `exc` is REW not answering (#134): its `rew_state`, read off the exception's class (`_state`)."""
    return _state(exc) == "unavailable"


def _from_rew(exc):
    """Whether `exc` is one of REW's states, not a bug (#134, H I-6): it carries a `rew_state` -- REW down, an answer
    that cannot be read, a title gone or held twice, an address that is none -- or it is REW's error answer, an
    `HTTPError` (the stdlib's one class, the same in every copy). Anything else is raised as it is, never a verdict."""
    return _state(exc) is not None or isinstance(exc, urllib.error.HTTPError)


def _unreached(name, exc):
    """The verdict for a title when REW's measurement list could not be read: whether REW holds the title is not
    known, so `exists` is None -- never False, which is "nobody measured it" (#134, audit T-2). By the state (H I-6):
    `reachable` False when REW did not answer; True when it answered with an error or with something it cannot read;
    None when it was not asked, its address being no address (`config`, H I-5) -- said in the address's own words."""
    state = _state(exc)
    if state == "unavailable":
        reachable, issue = False, f"REW unavailable: {exc}"
    elif state == "config":
        reachable, issue = None, str(exc)
    else:
        reachable, issue = True, f"REW answered an error: {exc}"
    return {"name": name, "exists": None, "reachable": reachable, "applicable": True, "kind": _api.UNKNOWN,
            "valid": False, "issues": [issue], "stats": {}}


def _no_impulse(exc):
    """Whether a failed impulse read is REW saying that it keeps no impulse response for this capture -- the one
    failed read that counts against nothing (audit T-4). REW answers it HTTP 400 with "<title> at index N uuid ...
    does not have an impulse response" (the live pass at REW, 2026-10-07, ruling R30); a 404 counts only when its
    words name the impulse response (F M-8, H minor 7) -- a 404 that does not is the id gone between the listing and
    the read. `code` is set on every `HTTPError` itself, so reading it never meets Python 3.9's `KeyError: 'file'`."""
    code = getattr(exc, "code", None)
    words = str(exc).lower()
    return (code == 404 and "impulse response" in words) or (code == 400 and "does not have an impulse response" in words)


def verdict(name, measurements=None, f_low=20, f_high=20000):
    """One measurement's verdict, by REW title. REW's own answers never raise -- a verdict is always an answer --
    and a bug in reading REW's list is never one (#134, H I-6): raised as it is.

    `measurements` is REW's own `get_measurements()` map, passed in when checking a list so the
    whole check costs one round trip plus one pull per title rather than two per title.

    A title REW holds more than once is its own verdict (H I-8): `exists` True, `valid` False, `ambiguous` the
    number of measurements holding it -- not missing, and not usable until it is renamed.
    """
    # THREE states, not two. `exists` and `valid` were split because "nobody measured it" and "it
    # was measured and cannot be used" are different conversations; `applicable` is the same split
    # one step earlier -- this check asks swept-capture questions (is the impulse there, does the
    # span cover the band), and an RTA answers none of them by its nature. Judging it against them
    # paints a row red where nothing is wrong (TCC-008). Defaults to True so a caller that never
    # looks at the field keeps the behaviour it had. `reachable` stands beside them all (#134): REW
    # not answering is no fact about the capture, and it is never read as one.
    out = {"name": name, "exists": False, "reachable": True, "applicable": True, "kind": _api.UNKNOWN,
           "valid": False, "issues": [], "stats": {}}
    try:
        ms = _api.get_measurements() if measurements is None else measurements
    except Exception as exc:  # noqa: BLE001 — REW down or answering an error is a verdict, not a traceback
        if not _from_rew(exc):
            raise                          # a bug: never a verdict on the title (H I-6)
        return _unreached(name, exc)
    try:
        mid = _api.find_measurement_id(name, ms, exact=True)
    except KeyError as exc:
        # Ambiguity is its own answer: two measurements with one title is a naming fault the
        # Arbiter has to fix, and silently picking either is how a wrong-channel pull happens.
        # `str(KeyError)` is the repr of its argument, quotes and all -- and the "have:" tail
        # lists every title in REW, which is a diagnostic, not a verdict.
        out["issues"].append(str(exc).split(" (have:")[0].strip('"'))
        if _state(exc) == "ambiguous":
            # REW holds it -- more than once (H I-8). Read as missing, it sent the tuner to measure a third copy.
            out["exists"] = True
            out["ambiguous"] = sum(1 for m in ms.values() if (m or {}).get("title", "") == name)
        return out
    out["exists"] = True
    # REW's own identity for this measurement. Its ordinal id is explicitly unstable (a reorder or
    # a delete reshuffles it), so a consumer recording "this graph was checked" has to pin the
    # uuid -- otherwise a re-take under the same title inherits the old verdict (SCR-040).
    entry = (ms.get(mid) or {})
    out["stats"]["uuid"] = entry.get("uuid")
    out["stats"]["date"] = entry.get("date")
    # The kind comes off the LISTING record, which is all a caller has before pulling anything --
    # the same place a front-end reads it when the tuner is still choosing rows at the car.
    out["kind"] = _api.measurement_kind(entry)
    if not _api.is_swept(entry):
        # Not a failure and not a pass: a row to grey out, not to colour. `valid` stays False
        # because nothing here was validated -- reading it as "bad" is what `applicable` exists
        # to prevent, and a caller that ignores the field sees exactly what it saw before.
        out["applicable"] = False
        out["issues"].append(f"this check is for swept captures; REW says this one is "
                             f"{out['kind']} — nothing here was checked")
        return out

    try:
        freqs, mag, phase = _api.get_fr(mid, smoothing=READ_SMOOTHING)
    except Exception as exc:  # noqa: BLE001
        if _rew_down(exc):
            # REW stopped answering after its list: the title is there, the curve was not read -- no word about it.
            out["reachable"] = False
            out["issues"].append(f"REW unavailable while reading the frequency response: {exc}")
        else:
            out["issues"].append(f"frequency response unreadable: {exc}")
        return out
    if not freqs or not mag:
        out["issues"].append("frequency response is empty")
        return out

    stats = _analysis.analyze_fr(freqs, mag, phase, f_low=f_low, f_high=f_high)
    if not stats:
        out["issues"].append(f"nothing in band {f_low}-{f_high} Hz")
        return out
    out["stats"].update(stats)
    # The channel's level where it PLAYS: the mean over the bins within 20 dB of its own maximum.
    # `mean_dB` averages the whole asked band, so a sub read over 20-20000 Hz comes out 20 dB
    # "quieter" than a woofer of the same level -- the session probe compared channels on that
    # once (2026-08-26) and called the sub the quietest. Live-band mean is what a level compare needs.
    inband = [(f_, m_) for f_, m_ in zip(freqs, mag) if f_low <= f_ <= f_high]
    if inband:
        top = max(m_ for _, m_ in inband)
        live = [m_ for _, m_ in inband if m_ >= top - 20.0]
        out["stats"]["live_mean_dB"] = round(sum(live) / len(live), 2)
    if stats["range_dB"] < _FLAT_RANGE_DB:
        out["issues"].append(
            f"flat to {stats['range_dB']} dB across the band — a loopback or a placeholder, "
            "not a driver in a car"
        )
    if stats["mean_dB"] < _SILENT_MEAN_DB:
        out["issues"].append(f"in-band mean {stats['mean_dB']} dB — silence, not a sweep")

    low, high = min(freqs), max(freqs)
    if high < f_high * _MIN_SPAN_FRACTION or low > f_low / _MIN_SPAN_FRACTION:
        out["issues"].append(
            f"covers {low:.0f}-{high:.0f} Hz, asked for {f_low:.0f}-{f_high:.0f} — truncated"
        )

    # The impulse is what time alignment is read off, and it only exists for a sweep. Reported,
    # never judged: `pre_ringing_dB` is everything before the peak, which on a real car sweep
    # includes the loopback reference and earlier arrivals -- gating on it marked both of this
    # project's real sweeps unusable, which is the failure this whole verdict exists to avoid.
    # A capture REW keeps no impulse for (REW says so, `_no_impulse`) counts against nothing. Any
    # other failed read is said (audit T-4): swallowed, a sweep whose impulse could not be read
    # passed as usable, and the arrivals read off it later had nothing under them.
    try:
        # Raw, so `peak_dB` is the impulse's real peak in dBFS. Read peak-normalised (the
        # endpoint's default until 2026-09-08) it was 0.0 on every row and said nothing between
        # titles; the level spread is still read on the live-band mean, because a single peak
        # sample is a worse ruler for loudness than a band -- but the number is at least true now.
        times, ir = _api.get_impulse_response(mid, normalised=False)
    except Exception as exc:  # noqa: BLE001 -- every failure is sorted below, none is dropped
        times, ir = None, None
        if _rew_down(exc):
            out["reachable"] = False
            out["issues"].append(f"REW unavailable while reading the impulse response: {exc}")
        elif not _no_impulse(exc):
            out["issues"].append(f"impulse response unreadable: {exc}")
    if times and ir:
        out["stats"].update(_analysis.analyze_impulse(times, ir))
        # The CAPTURE rate -- what this measurement was recorded at. A separate fact from the DSP's
        # processing rate (the user's ruling, 2026-08-25): a UMIK-1 captures at 48k under a 96k
        # Helix and that is legitimate. Reported so the round check can say ONCE when they differ;
        # never an issue by itself.
        if len(times) > 1 and times[1] > times[0]:
            out["stats"]["capture_rate_hz"] = int(round(1.0 / (times[1] - times[0])))

    out["valid"] = not out["issues"]
    return out


def verify(names, f_low=20, f_high=20000):
    """Verdicts for a list of titles, in the order given. One REW round trip for the index.

    An index REW does not give leaves every title's presence unknown: each verdict is `exists: None`, with
    `reachable: False` when REW did not answer (#134) -- never "missing", which is REW saying it holds no such title.
    A failure of that read that is none of REW's states is a bug, raised as it is (H I-6).
    """
    try:
        measurements = _api.get_measurements()
    except Exception as exc:  # noqa: BLE001 -- REW down or answering an error is a verdict for every title
        if not _from_rew(exc):
            raise                          # a bug: never a verdict on any title (H I-6)
        return [_unreached(n, exc) for n in names]
    verdicts = [verdict(n, measurements, f_low=f_low, f_high=f_high) for n in names]
    return _flag_outlier_sweeps(verdicts)


def _driver_of(title):
    """`w-L_02 (sw)` -> `w-L`. The skill's own naming convention, and the only thing that makes
    "the same driver measured twice" a question this module can ask."""
    return str(title).split("_", 1)[0].strip()


def _flag_outlier_sweeps(verdicts):
    """Compare each capture's pre-echo against the CLEANEST capture of the same driver.

    The post-sweep half of the quality gate (issue #9). `presweep_safety.require_safe()` is
    mandatory before a sweep; nothing was mandatory after one, so whether a capture that floated
    got noticed depended on the Generator remembering that `flag_remeasure_candidates` exists. It
    is called from here now, through the rule it shares with `joint_analysis`.

    Relative, never absolute — see `REMEASURE_MARGIN_DB`. And it needs two captures of one driver
    to say anything at all: with one, there is nothing to be an outlier of, and the verdict is
    silence rather than a guess.

    A flagged capture is NOT marked invalid. It exists and it is readable; what it is, is worse
    than its own sibling by a margin that says something happened during it. That is a judgement
    for the Arbiter — `capture-check` reports it, and re-taking is their call.
    """
    scored, by_name = [], {v["name"]: v for v in verdicts}
    for v in verdicts:
        pre = (v.get("stats") or {}).get("pre_ringing_dB")
        # Only a capture REW holds: a title nobody could read (`exists` None, #134) is no driver's cleanest capture.
        if v.get("exists") is True and isinstance(pre, (int, float)):
            scored.append((v["name"], _driver_of(v["name"]), float(pre)))
    if len(scored) < 2:
        return verdicts
    for flag in _joint.remeasure_verdicts(scored):
        target = by_name.get(flag["name"])
        if target is None or not flag["remeasure"]:
            continue
        target["remeasure"] = True
        target["stats"]["pre_echo_delta_db"] = flag["delta_db"]
        target["issues"].append(
            f"pre-echo is {flag['delta_db']} dB worse than the cleanest capture of "
            f"{flag['driver']} — worth re-taking before it is analysed"
        )
    return verdicts


DRIFT_HELD_SAMPLES = 0.5     # ctl1->ctl3 within half a CAPTURE sample: the time base held


def drift_samples_xcorr(ir_first, ir_last, oversample=16):
    """How many samples later `ir_last` arrives than `ir_first`, to a fraction of a sample.

    Two controls are the same driver swept twice, so their IRs differ by the drift and noise alone,
    and the cross-correlation peak IS the drift. The correlation is evaluated on a grid
    `oversample` times finer than a sample (zero-padded spectrum) and its peak refined by a
    parabola through the three top points -- a sinc is not a parabola at sample spacing (a
    3-point fit read a 0.3-sample shift as 0.07) but it is one at a sixteenth of a sample. A
    phase-slope fit was tried in between and fell over on noise at the bins where the driver does
    not play; the correlation integrates over them instead. The sheet's rule is "< 0.1 sample";
    this reads to a few hundredths (selftest, with and without noise)."""
    import numpy as np
    a = np.asarray(ir_first, dtype=float)
    b = np.asarray(ir_last, dtype=float)
    n = 1 << (2 * max(a.size, b.size) - 1).bit_length()
    cross = np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n))
    m = n * oversample
    r = np.fft.irfft(cross, m) * (m / n)          # r[k] peaks at k = drift * oversample
    i = int(np.argmax(r))
    y0, y1, y2 = r[(i - 1) % m], r[i], r[(i + 1) % m]
    denom = y0 - 2 * y1 + y2
    delta = 0.0 if denom == 0 else 0.5 * (y0 - y2) / denom
    lag = i + delta
    if lag > m / 2:
        lag -= m
    return float(lag / oversample)


class _ImpulseNotRead(Exception):
    """REW gave no impulse for a control (`_rew_ir_of`): its words, said beside the drift's peak-time fallback (H 11).
    Matched by `impulse_not_read` on the class, as every state here is."""
    impulse_not_read = True


def _rew_ir_of(title):
    """The impulse response REW holds under `title`, or None when REW gives it with no samples.

    REW's own answer -- down, no such title, a title held twice, an error, something it cannot read -- raises
    `_ImpulseNotRead` naming the title and REW's words: the drift record falls back to the peak times it already
    has and says why (H 11); it swallowed every failure and said "peak times" alone. Anything else is a bug, raised
    as it is."""
    try:
        mid = _api.find_measurement_id(title, exact=True)
        # Raw, the same convention as every reader; the cross-correlation below is scale-free.
        times, ir = _api.get_impulse_response(mid, normalised=False)
    except Exception as exc:  # noqa: BLE001 -- sorted: REW's states are said, anything else is raised as it is
        if not _from_rew(exc):
            raise
        said = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc   # a KeyError's words, no quotes
        raise _ImpulseNotRead(f"{title}: {said}") from exc
    return ir if ir else None


def session_report(verdicts, processing_rate_hz=None, ir_of=_rew_ir_of):
    """The whole capture session in one table (Phase 0.6): every sweep's level and impulse side
    by side, the loudest and the quietest channel, and the ctl1->ctl3 drift as the DRIFT RECORD.

    Per-title verdicts say whether one curve is usable; this says whether the SESSION is -- the
    things only visible across titles. Level spread is read on each channel's LIVE-band mean
    (`live_mean_dB`: the bins within 20 dB of its own maximum -- a sub read over the whole band
    would come out 20 dB "quiet"), not the IR peak: one sample is a poor ruler for loudness, and
    until 2026-09-08 the impulse arrived peak-normalised, so the column read 0.0 on every row
    (it is the raw peak in dBFS now, `rew_api.get_impulse_response`). The
    drift is the arrival difference between `<x>-ctl1 (sw)` and `<x>-ctl3 (sw)`, the same driver
    swept first and last in the tripod block, in CAPTURE samples: within half a sample the base
    held; beyond it the solos taken between them are not on one base -- said, not judged, because
    accepting that delta as the base's uncertainty is the tuner's call.

    `ir_of(title)` fetches an impulse response (REW by default; a file reader offline): with both
    controls' IRs the drift is their cross-correlation peak to a fraction of a sample; without
    them it falls back to the peak times in the verdicts and the record says which -- and, when REW
    gave no impulse, why (`ir_not_read`, H 11).

    A control is "missing" only when it was asked for and REW holds no such title. Not asked for, or
    asked while REW's list could not be read, it is `not_read`, never missing (T I5); held twice in
    REW, the record names it (`ambiguous`, H I-8).
    """
    rows = []
    for v in verdicts:
        st = v.get("stats") or {}
        # `exists` None stays None: REW's list was not read, and the row must not say "missing" (#134).
        row = {"name": v["name"], "exists": None if v.get("exists") is None else bool(v.get("exists")),
               "reachable": v.get("reachable", True) is not False, "valid": bool(v.get("valid")),
               "mean_dB": st.get("live_mean_dB", st.get("mean_dB")), "peak_dB": st.get("peak_dB"),
               "peak_time_ms": st.get("peak_time_ms"), "pre_ringing_dB": st.get("pre_ringing_dB"),
               "capture_rate_hz": st.get("capture_rate_hz"),
               "applicable": v.get("applicable", True) is not False,
               "issues": list(v.get("issues") or [])}
        if v.get("ambiguous"):
            row["ambiguous"] = v["ambiguous"]          # REW holds it more than once (H I-8)
        rows.append(row)
    _p = {r["name"]: _naming.parse_name(r["name"]) for r in rows}
    sweeps = [r for r in rows if r["valid"] and r["mean_dB"] is not None
              and (_p[r["name"]] or {}).get("method") == "sw" and not (_p[r["name"]] or {}).get("control")]
    spread = None
    if len(sweeps) >= 2:
        loud = max(sweeps, key=lambda r: r["mean_dB"])
        quiet = min(sweeps, key=lambda r: r["mean_dB"])
        spread = {"loudest": loud["name"], "loudest_dB": loud["mean_dB"],
                  "quietest": quiet["name"], "quietest_dB": quiet["mean_dB"],
                  "spread_dB": round(loud["mean_dB"] - quiet["mean_dB"], 1)}
    # The controls are found through the grammar, not a substring: `m-L-ctl1_49 (sw)` (the sheet)
    # and `m-L_49ctl (sw) x0` (as typed in the car) are the same kind of thing, and the close of
    # the series is whichever of `ctl3` / `rep` the same channel+version+method carries.
    drift, parsed = None, _p
    for r in rows:
        pr = parsed.get(r["name"])
        if not pr or pr.get("control") not in _naming.CONTROL_OPEN:
            continue
        same = lambda q: (q and q["code"] == pr["code"] and q["version_n"] == pr["version_n"]
                          and q["method"] == pr["method"] and q["position"] == pr["position"])
        closers = [x for x in rows if same(parsed.get(x["name"]))
                   and parsed[x["name"]].get("control") in _naming.CONTROL_CLOSE]
        p = closers[0] if closers else None
        partner = p["name"] if p else _naming.generate_name(
            pr["code"], pr["version"], pr["method"], pr["modifier"], position=pr["position"],
            control="ctl3" if pr["control"] == "ctl1" else "rep")
        if r["exists"] is None or (p is not None and p["exists"] is None):
            # REW's list was not read (#134): neither control can be called there or missing -- the close of the
            # series included when it was never asked for (T I5: it read "<ctl1> present, <ctl3> missing").
            drift = {"ctl1": r["name"], "ctl3": partner, "not_read": True}
        elif p is None:
            # REW was read, but nobody asked it for the close of the series: not read, never "missing" (T I5).
            drift = {"ctl1": r["name"], "ctl3": partner, "not_read": True, "not_asked": True}
        elif p["exists"] is False:
            drift = {"ctl1": r["name"], "ctl3": partner, "missing": partner}
        elif r.get("ambiguous") or p.get("ambiguous"):
            # REW holds a control more than once (H I-8): which one the drift is read on is not knowable.
            drift = {"ctl1": r["name"], "ctl3": partner, "ambiguous": r["name"] if r.get("ambiguous") else partner}
        elif r["peak_time_ms"] is None or p["peak_time_ms"] is None:
            drift = {"ctl1": r["name"], "ctl3": partner, "missing": "an impulse on both"}
        else:
            rate = p["capture_rate_hz"] or r["capture_rate_hz"]
            ir1 = ir3 = not_read = None
            if ir_of:
                try:
                    ir1 = ir_of(r["name"])
                    ir3 = ir_of(partner) if ir1 is not None else None
                except Exception as exc:  # noqa: BLE001 -- REW's own answer is said below; anything else is raised
                    if not getattr(type(exc), "impulse_not_read", False):
                        raise
                    not_read = str(exc)
            if ir1 is not None and ir3 is not None and rate:
                smp = drift_samples_xcorr(ir1, ir3)
                delta_ms = smp / rate * 1000.0
                method = "xcorr"
            else:
                delta_ms = float(p["peak_time_ms"]) - float(r["peak_time_ms"])
                smp = delta_ms / 1000.0 * rate if rate else None
                method = "peak"
            drift = {"ctl1": r["name"], "ctl3": partner, "delta_ms": round(delta_ms, 4),
                     "capture_rate_hz": rate, "method": method,
                     "delta_samples": (round(smp, 2) if smp is not None else None),
                     "held": (abs(smp) <= DRIFT_HELD_SAMPLES) if smp is not None else None}
            if not_read:
                drift["ir_not_read"] = not_read      # why the cross-correlation was not read (H 11)
        break
    rates = sorted({r["capture_rate_hz"] for r in rows if r["capture_rate_hz"]})
    rate_note = None
    if processing_rate_hz and rates and any(rt != processing_rate_hz for rt in rates):
        rate_note = (f"captured at {'/'.join(str(r) for r in rates)} Hz; the DSP processes at "
                     f"{processing_rate_hz:g} Hz -- fine, working with it")
    return {"rows": rows, "spread": spread, "drift": drift, "capture_rates_hz": rates,
            "processing_rate_hz": processing_rate_hz, "rate_note": rate_note,
            "counts": summary(verdicts)}


def render_session(report):
    counts = report["counts"]
    lines = [f"  session probe -- {counts['total']} titles, {counts['ok']} usable, "
             f"{counts['missing']} missing, {counts['invalid']} unusable"
             + (f", {counts['ambiguous']} ambiguous" if counts.get("ambiguous") else "")
             + (f", {counts['not_applicable']} not checked (not a sweep)"
                if counts.get("not_applicable") else "")
             + (f", {counts['unreachable']} unreachable" if counts.get("unreachable") else ""), ""]
    lines.append(f"  {'title':24}{'live dB':>9}{'IR peak':>9}{'pre-ring':>10}{'arrival ms':>12}{'rate':>7}  ")
    lines.append("  " + "-" * 74)
    for r in report["rows"]:
        if r["exists"] is None:              # REW's list was not read (#134): not "missing"
            lines.append(f"  {r['name']:24}  -- not read: {(r['issues'] or ['REW did not answer'])[0]}")
            continue
        if not r["exists"]:
            lines.append(f"  {r['name']:24}  -- missing")
            continue
        def _f(v, fmt):
            return (fmt % v) if isinstance(v, (int, float)) else "--"
        mark = "" if r["valid"] else "  ✗ " + "; ".join(r["issues"])
        lines.append(f"  {r['name']:24}{_f(r['mean_dB'], '%9.1f')}{_f(r['peak_dB'], '%9.1f')}"
                     f"{_f(r['pre_ringing_dB'], '%10.1f')}{_f(r['peak_time_ms'], '%12.3f')}"
                     f"{_f(r['capture_rate_hz'], '%7d')}{mark}")
    lines.append("")
    sp = report["spread"]
    if sp:
        lines.append(f"  loudest {sp['loudest']} {sp['loudest_dB']:.1f} dB / quietest {sp['quietest']} "
                     f"{sp['quietest_dB']:.1f} dB -> spread {sp['spread_dB']:.1f} dB (each channel's "
                     f"live-band mean; the passport says what the loudest was set to)")
    d = report["drift"]
    if d is None:
        lines.append("  drift: no `-ctl1 (sw)` title in this set -- the drift record needs ctl1 and ctl3")
    elif d.get("not_read"):
        why = (f"{d['ctl3']} was not among the titles checked: check it beside {d['ctl1']} for the drift record"
               if d.get("not_asked") else "REW's measurement list was not read")
        lines.append(f"  drift: {d['ctl1']} -> {d['ctl3']} not read -- {why}")
    elif d.get("ambiguous"):
        lines.append(f"  drift: {d['ctl1']} -> {d['ctl3']} not read -- REW holds {d['ambiguous']} more than once: "
                     "rename so titles are unique")
    elif d.get("missing"):
        lines.append(f"  drift: {d['ctl1']} present, {d['missing']} missing -- no drift record")
    else:
        smp = d["delta_samples"]
        held = ("the time base HELD" if d["held"] else
                "the base MOVED between the first and last sweep -- the solos between them are not on "
                "one base; re-take the block or carry this as the base's uncertainty")
        lines.append(f"  drift {d['ctl1']} -> {d['ctl3']}: {d['delta_ms']:+.4f} ms = "
                     + (f"{smp:+.2f} samples @ {d['capture_rate_hz']} Hz" if smp is not None else "? samples (no rate)")
                     + f" -- {held} (rule: within {DRIFT_HELD_SAMPLES:g} capture sample; "
                     + ("cross-correlation" if d.get("method") == "xcorr" else "peak times")
                     + (f" -- the impulse responses were not read: {d['ir_not_read']}" if d.get("ir_not_read") else "")
                     + ")")
    if report["rate_note"]:
        lines.append(f"  ⚠ {report['rate_note']}")
    return "\n".join(lines)


def _counted_as(v):
    """The one count of `summary` a verdict goes in. Each goes in exactly one, so the counts add up to the total."""
    if v.get("reachable", True) is False:
        return "unreachable"               # REW did not answer: nothing is known of the title (#134)
    if v["valid"]:
        return "ok"
    if v.get("ambiguous"):
        return "ambiguous"                 # REW holds it more than once: not missing, not usable (H I-8)
    if v["exists"] is False:
        return "missing"                   # REW answered, and holds no such title
    if v["exists"] and v.get("applicable", True) is False:
        return "not_applicable"            # an RTA: not checked, never unusable (skill #29)
    return "invalid"                       # measured and unusable -- or REW answered an error (`exists` None)


def summary(verdicts):
    """Counts a caller can act on without walking the list.

    A capture this check does not apply to (an RTA, `applicable: False`) is counted apart, never
    as `invalid`: counting it there is how every `(rta)` of a phase-0 round read as unusable in
    the header of the very output whose rows said "nothing here was checked" (skill #29). And a
    title REW did not answer for (`reachable: False`) is `unreachable`, never `missing`: `missing`
    is REW answering that it holds no such title, `exists` False and nothing else (#134). A title
    REW holds more than once is `ambiguous` (H I-8): neither missing nor merely unusable.
    """
    counts = {"total": len(verdicts), "missing": 0, "invalid": 0, "not_applicable": 0, "ok": 0, "unreachable": 0,
              "ambiguous": 0}
    for v in verdicts:
        counts[_counted_as(v)] += 1
    return counts


_USAGE = """usage: verify.py <title> [title ...] [--json] [--band LOW HIGH] [--session]

  Verdict per REW measurement title: does it exist, is what REW holds usable.
  Exit 0 when every title is valid, 1 otherwise, 69 when REW did not answer — so a shell gate
  can branch on it. A capture this check does not apply to (an RTA) does not make it 1. A
  REW_API_URL that is no address is 1, never 69: REW was not asked.
  --session adds the whole-session table (Phase 0.6): level and impulse of every title side by
  side, loudest/quietest, and the ctl1->ctl3 drift record.
"""

# The mark a verdict line starts with, by its count; `ERROR  ` is an `invalid` whose title REW could not list.
_MARKS = {"ok": "OK  ", "missing": "MISSING", "not_applicable": "N/A ", "invalid": "INVALID",
          "unreachable": "NO REW ", "ambiguous": "AMBIGUOUS"}


def _main(argv):
    args = [a for a in argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        return 2
    as_json = "--json" in args
    session = "--session" in args
    args = [a for a in args if a not in ("--json", "--session")]
    f_low, f_high = 20, 20000
    if "--band" in args:
        i = args.index("--band")
        try:
            f_low, f_high = float(args[i + 1]), float(args[i + 2])
        except (IndexError, ValueError):
            print("--band needs two numbers: --band 20 20000", file=sys.stderr)
            return 2
        args = args[:i] + args[i + 3:]
    if not args:
        print(_USAGE, file=sys.stderr)
        return 2

    verdicts = verify(args, f_low=f_low, f_high=f_high)
    if as_json:
        out = {"summary": summary(verdicts), "measurements": verdicts}
        if session:
            out["session"] = session_report(verdicts)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if session:
            print(render_session(session_report(verdicts)))
            print()
        for v in verdicts:
            counted = _counted_as(v)
            mark = "ERROR  " if counted == "invalid" and v["exists"] is None else _MARKS[counted]
            print(f"{mark} {v['name']}")
            for issue in v["issues"]:
                print(f"      - {issue}")
        counts = summary(verdicts)
        print(f"{counts['ok']}/{counts['total']} usable, "
              f"{counts['missing']} missing, {counts['invalid']} unusable"
              + (f", {counts['ambiguous']} ambiguous" if counts["ambiguous"] else "")
              + (f", {counts['not_applicable']} not checked (not a sweep)" if counts["not_applicable"] else "")
              + (f", {counts['unreachable']} unreachable" if counts["unreachable"] else ""))
    if any(v.get("reachable", True) is False for v in verdicts):
        return EXIT_REW_UNAVAILABLE       # REW did not answer: no verdict on those titles, so neither 0 nor 1
    return 0 if all(v["valid"] or v.get("applicable", True) is False for v in verdicts) else 1


# ── the selftest's stand-in REW ─────────────────────────────────────────────────────────────────
# An RTA and a sweep as REW lists them, a sweep-shaped curve and a 48 kHz impulse: what `verdict` reads, answered
# without REW, which a selftest must not reach.
_RTA_RECORD = {"title": "ALL_60 (rta)", "uuid": "u1",
               "notes": "65536-point 1/48 octave RTA using Hann window, no smoothing and 150 averages"}
_SWEPT_RECORD = {"title": "sw_60 (sw)", "uuid": "u2", "notes": "DELAY 22.6504 ms (7.769 m, 25 ft 5.9 in)"}


def _sweep_fr(mid, smoothing=None):
    """A real-looking sweep: rising then falling, nothing flat, nothing silent."""
    return [20 * (10 ** (k / 100.0)) for k in range(301)], [70 + 10 * (k % 7) for k in range(301)], None


def _impulse_48k(mid, normalised=True):
    """Three samples 1/48000 s apart: a 48 kHz capture."""
    return [0.0, 1 / 48000, 2 / 48000], [0.0, 1.0, 0.0]


@contextlib.contextmanager
def _rew_as(**readers):
    """`rew_api`'s readers replaced by `readers` for the length of a `with`, and put back however it ends."""
    saved = {name: getattr(_api, name) for name in readers}
    try:
        for name, reader in readers.items():
            setattr(_api, name, reader)
        yield
    finally:
        for name, reader in saved.items():
            setattr(_api, name, reader)


def _raising(exc):
    """A reader that fails with `exc`, whatever it is asked."""
    def reader(*_args, **_kwargs):
        raise exc
    return reader


def _run_main(argv):
    """`_main(argv)`'s exit code and what it printed."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = _main(argv)
    return rc, out.getvalue()


class _Down(OSError):
    """REW not answering, as any copy of `rew_api` raises it: matched by its `rew_state`, never by its class."""
    rew_state = "unavailable"


def _check_unreachable_state():
    """REW down is its own state (#134, audit T-2): `reachable` False and `exists` None -- nobody can say whether
    REW holds the title -- counted `unreachable`, never `missing`, and the command exits 69."""
    with _rew_as(get_measurements=_raising(_Down("refused"))):
        vs = verify(["a (sw)"])
        assert vs[0]["reachable"] is False and vs[0]["exists"] is None, vs
        assert vs[0]["valid"] is False and vs[0]["issues"][0].startswith("REW unavailable: "), vs
        s = summary(vs)
        assert (s["missing"], s["unreachable"], s["invalid"], s["ok"]) == (0, 1, 0, 0), s
        # Asked alone (no listing handed in), the verdict reads the listing itself and says the same.
        one = verdict("a (sw)")
        assert one["reachable"] is False and one["exists"] is None, one
        rc, out = _run_main(["verify.py", "a (sw)"])
        assert rc == 69, (rc, out)
        assert "NO REW  a (sw)" in out and "MISSING" not in out, out
        assert out.rstrip().endswith("0/1 usable, 0 missing, 0 unusable, 1 unreachable"), out
        rc, out = _run_main(["verify.py", "a (sw)", "--json"])
        doc = json.loads(out)
        assert rc == 69 and (doc["summary"]["unreachable"], doc["summary"]["missing"]) == (1, 0), (rc, doc)
        assert doc["measurements"][0]["exists"] is None and doc["measurements"][0]["reachable"] is False, doc
        # The session table says the same: no row and no drift record reads "missing" for a title nobody read --
        # the control asked for and its partner, or a control asked alone or beside a solo, its partner never asked
        # (T I5, H minor 6: `<ctl1> present, <ctl3> missing`, though neither was read).
        for asked in (["m-L-ctl1_1 (sw)", "m-L-ctl3_1 (sw)"], ["m-L-ctl1_1 (sw)"], ["m-L-ctl1_1 (sw)", "m-L_1 (sw)"]):
            rc, out = _run_main(["verify.py", *asked, "--session"])
            assert rc == 69 and "missing --" not in out and "present" not in out, (asked, rc, out)
            assert f"titles, 0 usable, 0 missing, 0 unusable, {len(asked)} unreachable" in out, (asked, out)
            assert "drift: m-L-ctl1_1 (sw) -> m-L-ctl3_1 (sw) not read -- REW's measurement list was not read" in out, \
                (asked, out)
            drift = session_report(verify(asked))["drift"]
            assert drift["not_read"] is True and "missing" not in drift, (asked, drift)
    # REW stops answering in the middle of a check: the title is in REW's list, the curve could not be read.
    with _rew_as(get_measurements=lambda: {"2": dict(_SWEPT_RECORD)}, get_fr=_raising(_Down("refused")),
                 get_impulse_response=_impulse_48k):
        v = verify(["sw_60 (sw)"])[0]
        assert v["exists"] is True and v["reachable"] is False and v["valid"] is False, v
        assert v["issues"][0].startswith("REW unavailable while reading the frequency response"), v
        assert summary([v])["unreachable"] == 1 and summary([v])["invalid"] == 0, summary([v])
        assert _run_main(["verify.py", "sw_60 (sw)"])[0] == 69
    # ...after answering for another title (T I6): one title unanswered is REW down, whatever the others said -- 69,
    # never 1, which sends the tuner to measure again a capture REW still holds.
    listing = {"1": dict(_SWEPT_RECORD, title="w-L_1 (sw)"), "2": dict(_SWEPT_RECORD, title="w-R_1 (sw)")}

    def answers_then_drops(mid, smoothing=None):
        if mid == "2":
            raise _Down("refused")
        return _sweep_fr(mid, smoothing)
    with _rew_as(get_measurements=lambda: listing, get_fr=answers_then_drops, get_impulse_response=_impulse_48k):
        rc, out = _run_main(["verify.py", "w-L_1 (sw)", "w-R_1 (sw)"])
        assert rc == 69 and "OK   w-L_1 (sw)" in out and "NO REW  w-R_1 (sw)" in out, (rc, out)
        assert out.rstrip().endswith("1/2 usable, 0 missing, 0 unusable, 1 unreachable"), out
    # The command line itself, run as a process at a dead port (T m16): 69, nothing "missing". And with an address
    # that is no address, 1, the address named: not REW down (H I-5). Neither opens a socket to REW.
    import subprocess
    for url, code, said in (("http://127.0.0.1:1", 69, "NO REW  a (sw)"),
                            ("localhost:4735", 1, "REW_API_URL 'localhost:4735' is not an address: it does not start "
                                                  "with http:// or https://")):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "a (sw)"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env={**os.environ, "REW_API_URL": url, "PYTHONIOENCODING": "utf-8"}, timeout=120)
        assert r.returncode == code and said in r.stdout and "MISSING" not in r.stdout and "Traceback" not in r.stderr, \
            (url, r.returncode, r.stdout[-400:], r.stderr[-400:])


def _check_protocol_error_state():
    """REW answered, with an error or with something that is not a measurement list: REW is there (`reachable`
    True), whether it holds the title is not known (`exists` None) -- unusable, never "missing", exit 1 (#134)."""
    import urllib.error

    class Garbled(ValueError):
        rew_state = "protocol"

    class Trapped(urllib.error.HTTPError):
        """An `HTTPError` whose instance raises for an attribute it lacks, on every Python (T m1): what one built
        without a body does on 3.9 only (`KeyError: 'file'`), so a state read off the instance fails here on 3.12 too."""
        def __getattr__(self, name):
            raise KeyError("file")
    # An HTTPError built without a body, as REW's 500 can arrive: on Python 3.9 reading `rew_state` off the instance
    # raises `KeyError: 'file'`, so the state is read off the exception's class.
    refused = urllib.error.HTTPError("http://127.0.0.1:1/measurements", 500, "Server Error -- REW said: boom", {}, None)
    trapped = Trapped("http://127.0.0.1:1/measurements", 500, "Server Error -- REW said: boom", {}, None)
    for exc in (Garbled("REW's measurement list is not a map of measurements: list"), refused, trapped):
        with _rew_as(get_measurements=_raising(exc)):
            v = verify(["a (sw)"])[0]
            assert v["reachable"] is True and v["exists"] is None and v["valid"] is False, (exc, v)
            assert v["issues"][0].startswith("REW answered an error: "), (exc, v)
            s = summary([v])
            assert (s["missing"], s["unreachable"], s["invalid"], s["ok"]) == (0, 0, 1, 0), (exc, s)
            rc, out = _run_main(["verify.py", "a (sw)"])
            assert rc == 1 and "ERROR   a (sw)" in out and "MISSING" not in out, (exc, rc, out)
    # REW's address is no address (`config`, H I-5): REW was not asked, so it neither answered nor stayed silent --
    # `reachable` null, `exists` null, the address's own words; 1, never 69 (REW down) and never "missing".
    class Misaddressed(ValueError):
        rew_state = "config"
    said = "REW_API_URL 'localhost:4735' is not an address: it does not start with http:// or https://"
    with _rew_as(get_measurements=_raising(Misaddressed(said))):
        v = verify(["a (sw)"])[0]
        assert v["reachable"] is None and v["exists"] is None and v["valid"] is False and v["issues"] == [said], v
        s = summary([v])
        assert (s["missing"], s["unreachable"], s["invalid"], s["ok"]) == (0, 0, 1, 0), s
        rc, out = _run_main(["verify.py", "a (sw)"])
        assert rc == 1 and "ERROR   a (sw)" in out and said in out and "MISSING" not in out, (rc, out)
    # A listing read that failed on something that is not REW's -- a bug -- is never a verdict (H I-6): raised as it
    # is, by `verify` and by `verdict` reading the list itself, so `capture-check` exits 70 on it and records nothing.
    for call in (lambda: verify(["a (sw)"]), lambda: verdict("a (sw)")):
        with _rew_as(get_measurements=_raising(TypeError("a bug in the listing's reader"))):
            try:
                got = call()
            except TypeError:
                pass
            else:
                raise AssertionError(f"a bug in the listing's read was made a verdict: {got}")


def _check_ir_failure_on_a_sweep():
    """Audit T-4: an impulse read that fails on a swept capture is an issue, not silence. REW's own answer for a
    capture it keeps no impulse for is the one let through: HTTP 400 whose words say so (the live pass at REW,
    2026-10-07, ruling R30), or a 404 whose words name the impulse response (F M-8, H minor 7). A 404 that does not
    -- the id moved between the listing and the read -- is an issue: it was let through whatever it said."""
    import urllib.error
    url = "http://127.0.0.1:1/measurements/2/impulse-response?normalised=false"

    def http(code, msg):          # built without a body, as a test builds one (Python 3.9's `KeyError: 'file'` trap)
        return urllib.error.HTTPError(url, code, msg, {}, None)
    no_impulse = "Bad Request -- REW said: sw_60 (sw) at index 2 uuid u2 does not have an impulse response"
    listing = {"1": dict(_RTA_RECORD), "2": dict(_SWEPT_RECORD)}
    cases = (  # exception, valid, reachable, the issue's start (None: no issue)
        (RuntimeError("the stream closed early"), False, True, "impulse response unreadable: "),
        (http(404, "Not Found"), False, True, "impulse response unreadable: HTTP Error 404"),
        (http(404, "Not Found -- REW said: Measurement 2 not found"), False, True, "impulse response unreadable: "),
        (http(404, "Not Found -- REW said: sw_60 (sw) has no Impulse Response"), True, True, None),
        (http(400, no_impulse), True, True, None),
        (http(400, "Bad Request -- REW said: The request is missing parameters: normalised"), False, True,
         "impulse response unreadable: "),
        (_Down("refused"), False, False, "REW unavailable while reading the impulse response"),
        (_api.RewUnavailable("refused", url), False, False, "REW unavailable while reading the impulse response"),
    )
    for exc, valid, reachable, issue in cases:
        with _rew_as(get_fr=_sweep_fr, get_impulse_response=_raising(exc)):
            v = verdict("sw_60 (sw)", measurements=listing)
        assert v["exists"] is True and v["valid"] is valid and v["reachable"] is reachable, (repr(exc), v)
        if issue is None:
            assert v["issues"] == [], (repr(exc), v["issues"])
        else:
            assert [i for i in v["issues"] if i.startswith(issue)], (repr(exc), v["issues"])
    # An RTA is never asked for an impulse: it is answered from the listing, before any read.
    with _rew_as(get_fr=_raising(RuntimeError("asked")), get_impulse_response=_raising(RuntimeError("asked"))):
        rta = verdict("ALL_60 (rta)", measurements=listing)
    assert rta["applicable"] is False and rta["reachable"] is True and not any("asked" in i for i in rta["issues"])


def _check_recorded_no_impulse():
    """REW's own answer for a capture it keeps no impulse for, recorded at the live pass at REW (2026-10-07,
    `testdata/rew/impulse-none.json`), replayed over HTTP through `rew_api`'s `_FakeRew`: the read fails with it, and
    the verdict counts it against nothing. Another 400 is still `impulse response unreadable` (#134, audit T-4). Here,
    not in `rew_api`'s selftest: run as a script, that module is `__main__`, and importing this one there would load
    a second `rew_api`, with a `BASE_URL` of its own. The listing carries no notes, so the kind is unknown and the
    impulse is asked for -- the case where REW's own answer is all there is."""
    with open(os.path.join(_HERE, "testdata", "rew", "impulse-none.json"), encoding="utf-8") as f:
        recorded = json.load(f)
    listing = {"39": {"title": "m6 (rta)", "uuid": "cf49fc57-66cf-4fd4-a389-3ededc4d5e8c"}}
    another = {"status": 400, "body": {"message": "The request is missing parameters: normalised"}}
    for answer, issue in ((recorded, None), (another, "impulse response unreadable: ")):
        asked = []

        def routes(method, path, _body, _fake, answer=answer):
            asked.append((method, path))
            return answer["status"], json.dumps(answer["body"]).encode()
        fake = _api._FakeRew(routes)
        try:
            with _rew_as(get_fr=_sweep_fr):
                v = _api._with_base(fake.url, lambda: verdict("m6 (rta)", measurements=listing))
        finally:
            fake.close()
        assert asked == [("GET", "/measurements/39/impulse-response?normalised=false")], asked
        assert v["exists"] is True and v["reachable"] is True, v
        if issue is None:
            assert v["valid"] is True and v["issues"] == [], (answer, v["issues"])
        else:
            assert v["valid"] is False and [i for i in v["issues"] if i.startswith(issue)], (answer, v["issues"])


def _check_ambiguous_title():
    """A title REW holds twice is its own verdict (H I-8, T m4): REW holds it, so it is never "missing" -- that sent the
    tuner to measure a third copy -- and nothing tells which of the two is meant, so it is not usable either: `exists`
    true, `valid` false, `ambiguous` the number of measurements holding it, counted `ambiguous` (never `missing`,
    `invalid` or `ok`) and marked AMBIGUOUS, the count in the issue. The session table counts it so, and a control
    held twice is no drift record: said, not "missing"."""
    two = {"1": dict(_SWEPT_RECORD, title="w-L_1 (sw)", uuid="u1"), "2": dict(_SWEPT_RECORD, title="w-L_1 (sw)", uuid="u2"),
           "3": dict(_SWEPT_RECORD, title="w-R_1 (sw)", uuid="u3")}
    with _rew_as(get_measurements=lambda: two, get_fr=_sweep_fr, get_impulse_response=_impulse_48k):
        v = verdict("w-L_1 (sw)", measurements=two)
        assert v["exists"] is True and v["valid"] is False and v["reachable"] is True and v.get("ambiguous") == 2, v
        assert v["issues"][0].startswith("Ambiguous: 2 measurements titled 'w-L_1 (sw)'"), v["issues"]
        vs = verify(["w-L_1 (sw)", "w-R_1 (sw)"])
        s = summary(vs)
        assert (s["ambiguous"], s["missing"], s["invalid"], s["ok"], s["total"]) == (1, 0, 0, 1, 2), s
        rc, out = _run_main(["verify.py", "w-L_1 (sw)", "w-R_1 (sw)"])
        assert rc == 1 and "AMBIGUOUS w-L_1 (sw)" in out and "MISSING" not in out, (rc, out)
        assert out.rstrip().endswith("1/2 usable, 0 missing, 0 unusable, 1 ambiguous"), out
        assert "titles, 1 usable, 0 missing, 0 unusable, 1 ambiguous" in render_session(session_report(vs, ir_of=None))
        # A control held twice: the drift record says so, never "<ctl3> missing".
        ctl = {"1": dict(_SWEPT_RECORD, title="m-L-ctl1_1 (sw)"), "2": dict(_SWEPT_RECORD, title="m-L-ctl3_1 (sw)"),
               "3": dict(_SWEPT_RECORD, title="m-L-ctl3_1 (sw)")}
        rep = session_report([verdict(t, measurements=ctl) for t in ("m-L-ctl1_1 (sw)", "m-L-ctl3_1 (sw)")],
                             ir_of=None)
        assert rep["drift"].get("ambiguous") == "m-L-ctl3_1 (sw)" and "missing" not in rep["drift"], rep["drift"]
        said = render_session(rep)
        assert "REW holds m-L-ctl3_1 (sw) more than once" in said and "missing --" not in said, said


def _check_drift_says_why():
    """The drift record says why it fell back to peak times (H 11): an impulse REW did not give -- REW stopped, the
    title gone or held twice, an error -- is named, title and REW's words, beside the fallback, where it said "peak
    times" and never why. A bug in the read is raised, never a fallback."""
    ctl1, ctl3 = "m-L-ctl1_1 (sw)", "m-L-ctl3_1 (sw)"
    listing = {"1": dict(_SWEPT_RECORD, title=ctl1), "2": dict(_SWEPT_RECORD, title=ctl3)}
    with _rew_as(get_measurements=lambda: listing, get_fr=_sweep_fr, get_impulse_response=_impulse_48k):
        verdicts = verify([ctl1, ctl3])
    for gone, words in ((_Down("refused"), "refused"), (lambda: {"1": dict(_SWEPT_RECORD, title=ctl3)}, None)):
        readers = ({"get_measurements": lambda: listing, "get_impulse_response": _raising(gone)}
                   if words else {"get_measurements": gone})
        with _rew_as(**readers):
            rep = session_report(verdicts)
        d, said = rep["drift"], render_session(rep)
        why = d.get("ir_not_read") or ""
        assert d["method"] == "peak" and ctl1 in why and (words or "No measurement titled") in why, d
        assert f"peak times -- the impulse responses were not read: {why}" in said, said
    with _rew_as(get_measurements=lambda: listing, get_impulse_response=_raising(TypeError("a bug in the reader"))):
        try:
            got = session_report(verdicts)
        except TypeError:
            pass
        else:
            raise AssertionError(f"a bug in the impulse read became a peak-time drift: {got['drift']}")


def _check_counts_add_up():
    """Each verdict is counted once -- usable, missing, unusable, not checked or unreachable -- so the counts add up
    to the total (#134); and a verdict the outlier rule reads is one REW holds (`exists` True), never one nobody
    could read, whatever numbers it carries."""
    def v(exists, valid=False, applicable=True, reachable=True):
        return {"name": "x", "exists": exists, "reachable": reachable, "applicable": applicable, "valid": valid,
                "issues": [] if valid else ["x"], "stats": {}}
    vs = [v(True, valid=True), v(False), v(True), v(True, applicable=False), v(None, reachable=False),
          v(True, reachable=False), v(None)]
    s = summary(vs)
    assert (s["ok"], s["missing"], s["invalid"], s["not_applicable"], s["unreachable"]) == (1, 1, 2, 1, 2), s
    assert s["ok"] + s["missing"] + s["invalid"] + s["not_applicable"] + s["unreachable"] == s["total"] == 7, s
    # A verdict made before `reachable` existed (a front end's own, process.py's recount of a round) counts as before.
    old = [{"exists": True, "valid": True}, {"exists": False, "valid": False},
           {"exists": True, "valid": False, "applicable": False}, {"exists": True, "valid": False}]
    s = summary(old)
    assert (s["ok"], s["missing"], s["invalid"], s["not_applicable"], s["unreachable"]) == (1, 1, 1, 1, 0), s
    unread = dict(v(None, reachable=False), name="w-L_00 (sw)", stats={"pre_ringing_dB": -80.0})
    pair = [dict(v(True, valid=True), name="w-L_01 (sw)", stats={"pre_ringing_dB": -42.0}),
            dict(v(True, valid=True), name="w-L_02 (sw)", stats={"pre_ringing_dB": -18.0})]
    flagged = {x["name"]: bool(x.get("remeasure")) for x in _flag_outlier_sweeps([unread] + pair)}
    assert flagged == {"w-L_00 (sw)": False, "w-L_01 (sw)": False, "w-L_02 (sw)": True}, flagged


def _selftest():
    """The outlier rule, offline. Everything else here needs REW, which a selftest must not."""
    failures = []
    for check in (_check_unreachable_state, _check_protocol_error_state, _check_ir_failure_on_a_sweep,
                  _check_recorded_no_impulse, _check_ambiguous_title, _check_drift_says_why, _check_counts_add_up):
        try:
            check()
        except Exception as exc:  # noqa: BLE001 -- a check that raises is reported by name, like one that fails
            failures.append(f"{check.__name__}: {type(exc).__name__}: {exc}")
    assert not failures, "\n".join(failures)

    def cap(name, pre):
        return {"name": name, "exists": True, "valid": True, "issues": [],
                "stats": {} if pre is None else {"pre_ringing_dB": pre}}

    assert _driver_of("w-L_02 (sw)") == "w-L", _driver_of("w-L_02 (sw)")
    assert _driver_of("tw-R_01") == "tw-R"

    # ── an RTA is not a failed sweep (TCC-008) ──────────────────────────────────────────────
    # The three states this verdict keeps apart, exercised without REW by stubbing the calls
    # that need it. `applicable: False` must NOT read as `valid: False` to anyone downstream:
    # a front-end colouring rows sees "grey", not "red", and the reason says which.
    _orig_gm, _orig_fr, _orig_ir = _api.get_measurements, _api.get_fr, _api.get_impulse_response
    listing = {"1": dict(_RTA_RECORD), "2": dict(_SWEPT_RECORD)}
    try:
        _api.get_measurements = lambda: listing
        # A real-looking sweep: rising then falling, nothing flat, nothing silent.
        asked = []
        _api.get_fr = lambda mid, smoothing=None: (asked.append(smoothing), _sweep_fr(mid, smoothing))[1]
        # The impulse too (T-30): unstubbed, the sweep's IR came from whatever REW runs here.
        _api.get_impulse_response = _impulse_48k
        v_rta = verdict("ALL_60 (rta)", measurements=listing)
        assert v_rta["exists"] is True, v_rta
        assert v_rta["applicable"] is False and v_rta["kind"] == _api.RTA, v_rta
        assert "swept captures" in v_rta["issues"][0], v_rta
        # Nothing was measured against sweep rules, so no sweep-shaped complaint appears.
        assert not any("truncated" in i or "flat to" in i for i in v_rta["issues"]), v_rta

        v_sw = verdict("sw_60 (sw)", measurements=listing)
        assert v_sw["applicable"] is True and v_sw["kind"] == _api.SWEEP, v_sw
        # S-013: the read names its smoothing, so the verdict no longer depends on the view.
        assert asked == [READ_SMOOTHING], asked
        # And the swept one really did get checked -- otherwise the assert above proves nothing.
        assert v_sw["stats"].get("range_dB") is not None, v_sw
        # ...and its impulse came from the stub: samples 1/48000 s apart read as a 48 kHz capture. Without the stub
        # the read fails (at the dead port) and the verdict swallows that, so nothing else here would notice.
        assert v_sw["stats"].get("capture_rate_hz") == 48000, v_sw
        # skill #29: the counts keep what the verdict said. An RTA is "not checked", never
        # "unusable" -- in the counts, in the session rows, and in the header a person reads.
        counts = summary([v_rta, v_sw])
        assert (counts["invalid"], counts["not_applicable"]) == (0, 1), counts
        probe = session_report([v_rta, v_sw])
        assert [r["applicable"] for r in probe["rows"]] == [False, True], probe["rows"]
        assert "0 unusable, 1 not checked (not a sweep)" in render_session(probe).splitlines()[0]
    finally:
        _api.get_measurements, _api.get_fr, _api.get_impulse_response = _orig_gm, _orig_fr, _orig_ir

    # Two captures of one driver, 24 dB apart: the worse one is flagged, the cleaner is not, and
    # a different driver's capture is judged only against its own.
    out = _flag_outlier_sweeps([cap("w-L_01 (sw)", -42.0), cap("w-L_02 (sw)", -18.0),
                                cap("w-R_01 (sw)", -30.0)])
    flagged = {v["name"]: v.get("remeasure", False) for v in out}
    assert flagged == {"w-L_01 (sw)": False, "w-L_02 (sw)": True, "w-R_01 (sw)": False}, flagged
    worse = next(v for v in out if v["name"] == "w-L_02 (sw)")
    assert worse["valid"] is True, "a floated sweep is readable — re-taking it is the Arbiter's call"
    assert "24.0 dB worse" in worse["issues"][0], worse["issues"]
    assert worse["stats"]["pre_echo_delta_db"] == 24.0

    # One capture of a driver is never an outlier: there is nothing to be an outlier OF.
    assert not _flag_outlier_sweeps([cap("w-L_01 (sw)", -18.0)])[0].get("remeasure", False)
    # ...and neither is a pair inside the margin.
    close = _flag_outlier_sweeps([cap("m-L_01 (sw)", -40.0), cap("m-L_02 (sw)", -32.0)])
    assert not any(v.get("remeasure") for v in close), close
    # An RTA capture has no impulse, so no pre-echo, so no verdict — not a failing one.
    assert not any(v.get("remeasure") for v in
                   _flag_outlier_sweeps([cap("c_01 (rta)", None), cap("c_01 (sw)", -12.0)]))

    # The session table, offline: spread on the in-band MEAN of the solos only (ctl titles and
    # RTA rows excluded), the drift from ctl1 to ctl3 in CAPTURE samples at the capture rate, held
    # within half a sample and said to have moved beyond it; a missing ctl3 is said, not guessed.
    def sw(name, mean, peak_ms, rate=48000, valid=True):
        return {"name": name, "exists": True, "valid": valid, "issues": [] if valid else ["x"],
                "stats": {"mean_dB": mean, "peak_dB": -3.0, "pre_ringing_dB": -30.0,
                          "peak_time_ms": peak_ms, "capture_rate_hz": rate}}
    rep = session_report([sw("m-L-ctl1_01 (sw)", 70.0, 5.000), sw("sw_01 (sw)", 84.2, 9.1),
                          sw("tw-R_01 (sw)", 66.9, 4.9), sw("c_01 (rta)", 99.0, 4.9),
                          sw("w-L_01 (sw)", 80.0, 5.2, valid=False),
                          sw("m-L-ctl3_01 (sw)", 70.1, 5.000 + 0.3 / 48.0)], processing_rate_hz=96000, ir_of=None)
    assert rep["spread"]["loudest"] == "sw_01 (sw)" and rep["spread"]["quietest"] == "tw-R_01 (sw)", rep["spread"]
    assert abs(rep["spread"]["spread_dB"] - 17.3) < 0.05, rep["spread"]
    d = rep["drift"]
    assert d["ctl3"] == "m-L-ctl3_01 (sw)" and abs(d["delta_samples"] - 0.3) < 0.01 and d["held"] is True, d
    assert rep["rate_note"] and "96000" in rep["rate_note"], rep["rate_note"]
    moved = session_report([sw("m-L_49ctl (sw) x0", 70.0, 5.0), sw("m-L_49rep (sw) x0", 70.0, 5.0 + 2.0 / 48.0)], ir_of=None)
    assert moved["drift"]["held"] is False and abs(moved["drift"]["delta_samples"] - 2.0) < 0.01, moved["drift"]
    assert moved["spread"] is None and moved["rate_note"] is None
    # The close of the series not asked for is not read, never "missing" (T I5): nothing asked REW for it. Asked for,
    # and REW holding none, it is missing.
    lone = session_report([sw("m-L-ctl1_01 (sw)", 70.0, 5.0), sw("sw_01 (sw)", 80.0, 9.0)], ir_of=None)
    assert lone["drift"].get("not_read") and lone["drift"].get("not_asked") and "missing" not in lone["drift"], \
        lone["drift"]
    assert "m-L-ctl3_01 (sw) was not among the titles checked" in render_session(lone), render_session(lone)
    gone = dict(sw("m-L-ctl3_01 (sw)", 0.0, None), exists=False, valid=False, stats={})
    lost = session_report([sw("m-L-ctl1_01 (sw)", 70.0, 5.0), gone], ir_of=None)
    assert lost["drift"]["missing"] == "m-L-ctl3_01 (sw)", lost["drift"]
    # The drift by cross-correlation, to a tenth of a sample: a band-limited impulse and the same
    # impulse 0.3 and 2.0 samples later (fractional delays by sinc interpolation), and a case with
    # noise on top; the sign says "later is positive".
    import numpy as np
    nn = 4096
    tt = np.arange(nn)
    def imp(shift):
        x = np.sinc((tt - 1000 - shift) / 1.0) * np.hanning(nn)   # band-limited, one main lobe
        return x
    assert abs(drift_samples_xcorr(imp(0), imp(0.3)) - 0.3) < 0.02
    assert abs(drift_samples_xcorr(imp(0), imp(2.0)) - 2.0) < 0.02
    assert abs(drift_samples_xcorr(imp(0.7), imp(0)) + 0.7) < 0.02, "earlier is negative"
    rng = np.random.default_rng(1)
    assert abs(drift_samples_xcorr(imp(0) + 0.01 * rng.standard_normal(nn),
                                   imp(0.3) + 0.01 * rng.standard_normal(nn)) - 0.3) < 0.05
    rep_x = session_report([sw("m-L-ctl1_01 (sw)", 70.0, 5.0), sw("m-L-ctl3_01 (sw)", 70.0, 5.0)],
                           ir_of=lambda t: imp(0.3) if "ctl3" in t else imp(0))
    assert rep_x["drift"]["method"] == "xcorr" and abs(rep_x["drift"]["delta_samples"] - 0.3) < 0.02, rep_x["drift"]
    assert "cross-correlation" in render_session(rep_x)
    txt = render_session(rep)
    assert "HELD" in txt and "spread 17.3" in txt and "no drift record" not in txt, txt
    assert "MOVED" in render_session(moved) and "no drift record" in render_session(lost)

    print("selftest OK — REW down is its own state (unreachable, `exists` null, exit 69), REW answering an error "
          "is unusable, an address that is none is 1 with its words, and none is ever \"missing\"; a bug in reading "
          "REW's list is raised, never a verdict; a title REW holds twice is AMBIGUOUS; a failed impulse read on a "
          "sweep is an issue, REW's own \"no impulse\" answer (400 in its words, or a 404 naming the impulse "
          "response) let through -- replayed as REW sent it at the live pass; the counts add up; the post-sweep gate "
          "compares a driver against ITSELF: a 24 dB outlier "
          "flagged and still readable, a close pair left alone, a lone capture and an RTA (no "
          "impulse) judged not at all; the session table: spread on the solos' in-band mean, the "
          "ctl1->ctl3 drift in capture samples held/moved/missing/not read, and why an impulse was not read, the "
          "capture-vs-processing rate said.")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(_selftest())
    sys.exit(_main(sys.argv))
