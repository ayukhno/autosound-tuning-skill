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


def summary(verdicts):
    """Counts a caller can act on without walking the list."""
    return {
        "total": len(verdicts),
        "missing": sum(1 for v in verdicts if not v["exists"]),
        "invalid": sum(1 for v in verdicts if v["exists"] and not v["valid"]),
        "ok": sum(1 for v in verdicts if v["valid"]),
    }


_USAGE = """usage: verify.py <title> [title ...] [--json] [--band LOW HIGH]

  Verdict per REW measurement title: does it exist, is what REW holds usable.
  Exit code 0 when every title is valid, 1 otherwise — so a shell gate can branch on it.
"""


def _main(argv):
    args = [a for a in argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        return 2
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
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
        print(json.dumps({"summary": summary(verdicts), "measurements": verdicts},
                         ensure_ascii=False, indent=2))
    else:
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

    print("selftest OK — the post-sweep gate compares a driver against ITSELF: a 24 dB outlier "
          "flagged and still readable, a close pair left alone, a lone capture and an RTA (no "
          "impulse) judged not at all.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(_selftest())
    sys.exit(_main(sys.argv))
