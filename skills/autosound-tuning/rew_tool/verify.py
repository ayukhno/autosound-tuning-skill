#!/usr/bin/env python3
"""Is this measurement there, and is it usable? — a machine verdict per title (SCR-013).

`verify_measurements.py` next door is what this replaces for anything but its own Passat session:
a one-off script with hardcoded measurement ids, `print`-driven output and no way to be called.
A front-end asking "can I light this row green?" needs an answer, not a report.

The verdict is deliberately shallow. It says whether REW holds the measurement and whether what it
holds looks like a real capture — not whether the tune is good. Judging the sound is the method's
job and it happens elsewhere; this is the gate that stops a session analysing a sweep that never
completed, and stops a checklist showing a row as captured because a title exists.

    {"name": "tw-L_1 (sw)", "exists": true, "valid": false,
     "issues": ["ir peak is 0.4 dB above the pre-ringing floor — no clear arrival"],
     "stats": {...}}

Two failure modes are kept apart on purpose. `exists: false` is "nobody measured it"; `valid:
false` is "it was measured and cannot be used", which is a different conversation with the Arbiter
and a different colour on the panel.

stdlib only (plus this package's own `rew_api`/`analysis`), py3.9+.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:  # same convention as contract.py: importable by path, no install step
    sys.path.insert(0, _HERE)

import analysis as _analysis  # noqa: E402
import joint_analysis as _joint  # noqa: E402
import naming as _naming  # noqa: E402
import rew_api as _api  # noqa: E402

# An FR flat to within a fraction of a dB across the whole band is not a loudspeaker in a car; it
# is a loopback, a dead input, or REW handing back a placeholder. Seen as a "successful" capture.
_FLAT_RANGE_DB = 1.0
# Below this the sweep is in the noise: a capture whose in-band mean sits at the floor is what a
# muted channel or a disconnected mic produces.
_SILENT_MEAN_DB = -80.0
# A capture that stops short of the band it was asked for is a truncated one -- an RTA that never
# got above 200 Hz reads as "captured" by title alone.
_MIN_SPAN_FRACTION = 0.5


def verdict(name, measurements=None, f_low=20, f_high=20000):
    """One measurement's verdict, by REW title. Never raises — a verdict is always an answer.

    `measurements` is REW's own `get_measurements()` map, passed in when checking a list so the
    whole check costs one round trip plus one pull per title rather than two per title.
    """
    out = {"name": name, "exists": False, "valid": False, "issues": [], "stats": {}}
    try:
        ms = _api.get_measurements() if measurements is None else measurements
    except Exception as exc:  # noqa: BLE001 — REW not running is a verdict, not a traceback
        out["issues"].append(f"REW unreachable: {exc}")
        return out
    try:
        mid = _api.find_measurement_id(name, ms, exact=True)
    except KeyError as exc:
        # Ambiguity is its own answer: two measurements with one title is a naming fault the
        # Arbiter has to fix, and silently picking either is how a wrong-channel pull happens.
        # `str(KeyError)` is the repr of its argument, quotes and all -- and the "have:" tail
        # lists every title in REW, which is a diagnostic, not a verdict.
        out["issues"].append(str(exc).split(" (have:")[0].strip('"'))
        return out
    out["exists"] = True
    # REW's own identity for this measurement. Its ordinal id is explicitly unstable (a reorder or
    # a delete reshuffles it), so a consumer recording "this graph was checked" has to pin the
    # uuid -- otherwise a re-take under the same title inherits the old verdict (SCR-040).
    entry = (ms.get(mid) or {})
    out["stats"]["uuid"] = entry.get("uuid")
    out["stats"]["date"] = entry.get("date")

    try:
        freqs, mag, phase = _api.get_fr(mid)
    except Exception as exc:  # noqa: BLE001
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
    # An RTA capture legitimately has no impulse at all, so its absence counts against nothing.
    try:
        times, ir = _api.get_impulse_response(mid)
    except Exception:  # noqa: BLE001
        times, ir = None, None
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
    """Verdicts for a list of titles, in the order given. One REW round trip for the index."""
    try:
        measurements = _api.get_measurements()
    except Exception as exc:  # noqa: BLE001
        return [
            {"name": n, "exists": False, "valid": False,
             "issues": [f"REW unreachable: {exc}"], "stats": {}}
            for n in names
        ]
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
        if v.get("exists") and isinstance(pre, (int, float)):
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


def session_report(verdicts, processing_rate_hz=None):
    """The whole capture session in one table (Phase 0.6): every sweep's level and impulse side
    by side, the loudest and the quietest channel, and the ctl1->ctl3 drift as the DRIFT RECORD.

    Per-title verdicts say whether one curve is usable; this says whether the SESSION is -- the
    things only visible across titles. Level spread is read on each channel's LIVE-band mean
    (`live_mean_dB`: the bins within 20 dB of its own maximum -- a sub read over the whole band
    would come out 20 dB "quiet"), not the IR peak (REW scales the impulse per measurement, so its
    peak says nothing between titles and reads 0.0 on every row). The
    drift is the arrival difference between `<x>-ctl1 (sw)` and `<x>-ctl3 (sw)`, the same driver
    swept first and last in the tripod block, in CAPTURE samples: within half a sample the base
    held; beyond it the solos taken between them are not on one base -- said, not judged, because
    accepting that delta as the base's uncertainty is the tuner's call.
    """
    rows = []
    for v in verdicts:
        st = v.get("stats") or {}
        rows.append({"name": v["name"], "exists": bool(v.get("exists")), "valid": bool(v.get("valid")),
                     "mean_dB": st.get("live_mean_dB", st.get("mean_dB")), "peak_dB": st.get("peak_dB"),
                     "peak_time_ms": st.get("peak_time_ms"), "pre_ringing_dB": st.get("pre_ringing_dB"),
                     "capture_rate_hz": st.get("capture_rate_hz"),
                     "issues": list(v.get("issues") or [])})
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
        if p is None or not p["exists"]:
            drift = {"ctl1": r["name"], "ctl3": partner, "missing": partner}
        elif r["peak_time_ms"] is None or p["peak_time_ms"] is None:
            drift = {"ctl1": r["name"], "ctl3": partner, "missing": "an impulse on both"}
        else:
            delta_ms = float(p["peak_time_ms"]) - float(r["peak_time_ms"])
            rate = p["capture_rate_hz"] or r["capture_rate_hz"]
            smp = delta_ms / 1000.0 * rate if rate else None
            drift = {"ctl1": r["name"], "ctl3": partner, "delta_ms": round(delta_ms, 4),
                     "capture_rate_hz": rate,
                     "delta_samples": (round(smp, 2) if smp is not None else None),
                     "held": (abs(smp) <= DRIFT_HELD_SAMPLES) if smp is not None else None}
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
    lines = [f"  session probe -- {report['counts']['total']} titles, {report['counts']['ok']} usable, "
             f"{report['counts']['missing']} missing, {report['counts']['invalid']} unusable", ""]
    lines.append(f"  {'title':24}{'live dB':>9}{'IR peak':>9}{'pre-ring':>10}{'arrival ms':>12}{'rate':>7}  ")
    lines.append("  " + "-" * 74)
    for r in report["rows"]:
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
    elif d.get("missing"):
        lines.append(f"  drift: {d['ctl1']} present, {d['missing']} missing -- no drift record")
    else:
        smp = d["delta_samples"]
        held = ("the time base HELD" if d["held"] else
                "the base MOVED between the first and last sweep -- the solos between them are not on "
                "one base; re-take the block or carry this as the base's uncertainty")
        lines.append(f"  drift {d['ctl1']} -> {d['ctl3']}: {d['delta_ms']:+.4f} ms = "
                     + (f"{smp:+.2f} samples @ {d['capture_rate_hz']} Hz" if smp is not None else "? samples (no rate)")
                     + f" -- {held} (rule: within {DRIFT_HELD_SAMPLES:g} capture sample)")
    if report["rate_note"]:
        lines.append(f"  ⚠ {report['rate_note']}")
    return "\n".join(lines)


def summary(verdicts):
    """Counts a caller can act on without walking the list."""
    return {
        "total": len(verdicts),
        "missing": sum(1 for v in verdicts if not v["exists"]),
        "invalid": sum(1 for v in verdicts if v["exists"] and not v["valid"]),
        "ok": sum(1 for v in verdicts if v["valid"]),
    }


_USAGE = """usage: verify.py <title> [title ...] [--json] [--band LOW HIGH] [--session]

  Verdict per REW measurement title: does it exist, is what REW holds usable.
  Exit code 0 when every title is valid, 1 otherwise — so a shell gate can branch on it.
  --session adds the whole-session table (Phase 0.6): level and impulse of every title side by
  side, loudest/quietest, and the ctl1->ctl3 drift record.
"""


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
            mark = "OK  " if v["valid"] else ("MISSING" if not v["exists"] else "INVALID")
            print(f"{mark} {v['name']}")
            for issue in v["issues"]:
                print(f"      - {issue}")
        counts = summary(verdicts)
        print(f"{counts['ok']}/{counts['total']} usable, "
              f"{counts['missing']} missing, {counts['invalid']} unusable")
    return 0 if all(v["valid"] for v in verdicts) else 1


def _selftest():
    """The outlier rule, offline. Everything else here needs REW, which a selftest must not."""
    def cap(name, pre):
        return {"name": name, "exists": True, "valid": True, "issues": [],
                "stats": {} if pre is None else {"pre_ringing_dB": pre}}

    assert _driver_of("w-L_02 (sw)") == "w-L", _driver_of("w-L_02 (sw)")
    assert _driver_of("tw-R_01") == "tw-R"

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
                          sw("m-L-ctl3_01 (sw)", 70.1, 5.000 + 0.3 / 48.0)], processing_rate_hz=96000)
    assert rep["spread"]["loudest"] == "sw_01 (sw)" and rep["spread"]["quietest"] == "tw-R_01 (sw)", rep["spread"]
    assert abs(rep["spread"]["spread_dB"] - 17.3) < 0.05, rep["spread"]
    d = rep["drift"]
    assert d["ctl3"] == "m-L-ctl3_01 (sw)" and abs(d["delta_samples"] - 0.3) < 0.01 and d["held"] is True, d
    assert rep["rate_note"] and "96000" in rep["rate_note"], rep["rate_note"]
    moved = session_report([sw("m-L_49ctl (sw) x0", 70.0, 5.0), sw("m-L_49rep (sw) x0", 70.0, 5.0 + 2.0 / 48.0)])
    assert moved["drift"]["held"] is False and abs(moved["drift"]["delta_samples"] - 2.0) < 0.01, moved["drift"]
    assert moved["spread"] is None and moved["rate_note"] is None
    lone = session_report([sw("m-L-ctl1_01 (sw)", 70.0, 5.0), sw("sw_01 (sw)", 80.0, 9.0)])
    assert lone["drift"]["missing"] == "m-L-ctl3_01 (sw)", lone["drift"]
    txt = render_session(rep)
    assert "HELD" in txt and "spread 17.3" in txt and "no drift record" not in txt, txt
    assert "MOVED" in render_session(moved) and "no drift record" in render_session(lone)

    print("selftest OK — the post-sweep gate compares a driver against ITSELF: a 24 dB outlier "
          "flagged and still readable, a close pair left alone, a lone capture and an RTA (no "
          "impulse) judged not at all; the session table: spread on the solos' in-band mean, the "
          "ctl1->ctl3 drift in capture samples held/moved/missing, the capture-vs-processing rate said.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(_selftest())
    sys.exit(_main(sys.argv))
