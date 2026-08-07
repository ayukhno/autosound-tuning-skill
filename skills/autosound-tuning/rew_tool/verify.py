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
    return [verdict(n, measurements, f_low=f_low, f_high=f_high) for n in names]


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


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
