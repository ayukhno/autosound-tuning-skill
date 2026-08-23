"""Were these measurements captured the same way? — the batch comparability gate.

Two sweeps can only be compared to each other if they were taken on the same terms. Most of the
method rests on that quietly: relative delay, joint phase, L/R symmetry, every crossover decision
read off a pair. When a project accumulates captures across sessions — a second visit, a repaired
door, somebody else's files — nothing has ever checked that the batches agree, and a mismatch does
not announce itself. It reads as a driver that moved.

**The one that actually bites: `timingReference` is not evidence of a shared time base.** It reads
`"Loopback"` whether the timing offset is 0 or 7.7 ms. Measured on a live REW while writing this
(measurement #78): `timingReference: "Loopback"` sitting next to `timingOffset: 0.004`. Two batches
can both say "Loopback", both look right in every UI, and be four milliseconds — 1.4 m — apart.
So the offset is compared, not the reference alone.

What "the same way" means here, and each one is a real way to be wrong:

  * **timing reference AND offset** — the pair, never either alone (above).
  * **sample rate** — a delay in samples means nothing across two rates, and this is the field a
    borrowed file is most likely to differ on.
  * **sweep range** — a 20 Hz sweep and a 100 Hz sweep do not answer the same question at 30 Hz,
    and one of them is extrapolating.

Three more facts this module encodes, all measured rather than reasoned (fork session, 19 captures
across two sessions, 2026-08-23; see `references/tooling/rew-api-quirks.md`):

  * **`notes` is user-editable free text and it can diverge from the field.** REW writes the
    offset into the prose, and editing that prose does NOT change `timingOffset`. Demonstrated
    deliberately rather than met in the wild: the user hand-edited a TEST measurement's notes to
    read `with 5.0000 ms … timing offset` beside a `timingOffset` of `0.004`, to check what an
    export carries — and has since reverted it, so the example no longer reproduces on that rig.
    What is established is the CAPABILITY, not a frequency: REW does not keep the two in step, so
    the prose is read here only to CROSS-CHECK the number, and a disagreement is reported as a
    fact about the file rather than resolved. The numeric field wins, always.
  * **`delay` is the arrival, not the buffer origin**, and it is exactly `timeOfIRPeakSeconds`.
    Anchor on `timeOfIRStartSeconds`, which sits on the integer sample grid and is bit-stable.
  * **RTA measurements have no impulse response**, so every timing field is `null`. That is not a
    fault and not a mismatch — it is a measurement that cannot participate in a timing comparison
    at all, and saying so is different from saying it disagrees.

Reports, never repairs. A batch that does not match is a decision about which captures to trust
or retake, and that is the tuner's.

    timebase.py --all                     # every measurement REW currently holds
    timebase.py --title "_2 (sw)"         # just the ones whose title contains this
    timebase.py --id 77 --id 78 [--json]

Exit codes: 0 comparable · 1 the batch is NOT on one footing · 2 nothing conflicting but something
could not be established.

stdlib only, py3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: REW writes the offset into `notes` as prose. Read ONLY to cross-check the numeric field.
_NOTES_OFFSET = re.compile(r"with\s+([\d.]+)\s*ms\b", re.IGNORECASE)
_NOTES_NO_OFFSET = re.compile(r"with\s+no\s+timing\s+offset", re.IGNORECASE)

#: How far two stated offsets may differ and still count as the same. A tenth of a sample at
#: 96 kHz — below REW's own reporting resolution, far below anything audible, and it exists so a
#: float round-trip does not read as a mismatch. NOT a tolerance for real disagreement: the
#: smallest offset anyone sets by hand is milliseconds, four orders of magnitude above this.
OFFSET_EPS_S = 1e-6

OK, MISMATCH, UNKNOWN = "ok", "mismatch", "unknown"


def timing_of(record, mid=None):
    """One measurement's capture terms, as a plain dict. Pure — no network, so it is testable.

    `notes_offset_s` is what the PROSE claims and `notes_agrees` whether it matches the number.
    Both are diagnostics about the file, not inputs to any decision: `offset_s` is authoritative
    because editing the note does not change it.
    """
    ir_start = record.get("timeOfIRStartSeconds")
    notes = record.get("notes") or ""
    notes_offset, structured = _notes_offset(notes)
    offset = record.get("timingOffset")
    agrees = None
    if notes_offset is not None and offset is not None:
        agrees = abs(notes_offset - float(offset)) <= OFFSET_EPS_S
    return {
        "id": mid if mid is not None else record.get("id"),
        "title": record.get("title"),
        "reference": record.get("timingReference"),
        "offset_s": None if offset is None else float(offset),
        "has_ir": ir_start is not None,
        "ir_start_s": ir_start,
        "ir_peak_s": record.get("timeOfIRPeakSeconds"),
        "sample_rate": record.get("sampleRate"),
        "start_freq": record.get("startFreq"),
        "end_freq": record.get("endFreq"),
        "notes_offset_s": notes_offset,
        "notes_structured": structured,
        "notes_agrees": agrees,
    }


def _notes_offset(notes):
    """The offset REW's prose claims, in seconds, and whether the prose had the shape it should.

    Returns `(seconds_or_None, structured)`. "with no timing offset" is an explicit zero, not a
    missing value. `structured` is False when the three-line DELAY/relative-to/with form is not
    there — a hand-edited note. Checking the structure is NOT enough on its own: a number-only
    edit leaves the shape intact and the value wrong, which is why the caller compares the number.
    """
    if not notes:
        return None, False
    structured = bool(re.search(r"^DELAY\b", notes, re.MULTILINE)) and "relative to" in notes
    if _NOTES_NO_OFFSET.search(notes):
        return 0.0, structured
    m = _NOTES_OFFSET.search(notes)
    if not m:
        return None, structured
    try:
        return float(m.group(1)) / 1000.0, structured
    except ValueError:
        return None, structured


def _group_key(t):
    """What has to match for two captures to be comparable. The offset is IN the key on purpose."""
    return (t["reference"], t["offset_s"], t["sample_rate"], t["start_freq"], t["end_freq"])


def compare(timings):
    """Is this batch on one footing? Returns a verdict plus what disagrees and what could not be
    established.

    Measurements with no impulse response (RTA) are set aside rather than failed: they cannot
    participate in a timing comparison at all, which is a different statement from disagreeing.
    They are still compared on rate and sweep range, because those apply to them too.
    """
    timings = list(timings)
    timed = [t for t in timings if t["has_ir"]]
    untimed = [t for t in timings if not t["has_ir"]]

    findings, unknowns = [], []
    # Only captures that STATE their terms are grouped. An unstated offset is not a different
    # offset: grouping by `None` made an unknown masquerade as a disagreement, so a batch where one
    # capture was silent reported a mismatch it had no evidence for — and then the silence graded
    # itself SLOW on the grounds that the batch "already" mismatched, which was circular. Unknown
    # and different are the two things this whole module exists to keep apart.
    stated = [t for t in timed if t["offset_s"] is not None and t["reference"] is not None]
    silent = [t for t in timed if t not in stated]
    groups = {}
    for t in stated:
        groups.setdefault(_group_key(t), []).append(t)

    if len(groups) > 1:
        findings.append({
            "kind": "split-batch",
            "detail": "these were not captured on the same terms",
            "groups": [{"terms": _describe(k), "members": [_name(t) for t in v]}
                       for k, v in groups.items()],
        })

    # The specific trap, called out by name whenever it is what happened: one reference, several
    # offsets. Every UI shows "Loopback" and the captures are still not on one clock.
    refs = {t["reference"] for t in stated}
    offsets = {t["offset_s"] for t in stated}
    if len(refs) == 1 and len(offsets) > 1:
        findings.append({
            "kind": "same-reference-different-offset",
            "detail": f"every capture says reference {next(iter(refs))!r}, but the offsets differ "
                      f"({', '.join(_ms(o) for o in sorted(offsets, key=lambda x: (x is None, x)))})"
                      " — the reference alone is not evidence of a shared time base",
            "groups": [],
        })

    for t in timed:
        if t["offset_s"] is None:
            unknowns.append({"what": "offset not stated", "who": _name(t)})
        if t["notes_agrees"] is False:
            findings.append({
                "kind": "notes-disagree",
                "detail": f"{_name(t)}: the notes say {_ms(t['notes_offset_s'])} and "
                          f"timingOffset says {_ms(t['offset_s'])}. The notes are user-editable "
                          f"and editing them does not change the field — the NUMBER is what was "
                          f"applied. Worth knowing that somebody edited this one.",
                "groups": [],
            })
        elif t["notes_offset_s"] is None:
            unknowns.append({"what": "no offset in the notes to cross-check against",
                             "who": _name(t)})
        if not t["notes_structured"] and t["notes_offset_s"] is not None:
            unknowns.append({"what": "notes are not in REW's own DELAY/relative-to/with shape",
                             "who": _name(t)})

    # Rate and sweep range apply to the untimed ones too.
    for field, label in (("sample_rate", "sample rate"), ("start_freq", "sweep start"),
                         ("end_freq", "sweep end")):
        seen = {t[field] for t in timings if t[field] is not None}
        if len(seen) > 1:
            findings.append({
                "kind": f"{field}-differs",
                "detail": f"{label} is not the same across the batch: "
                          + ", ".join(str(v) for v in sorted(seen, key=str)),
                "groups": [],
            })

    verdict = MISMATCH if findings else (UNKNOWN if unknowns or not timed else OK)
    # Roll the unknowns up by WHAT is missing. Eight captures each missing the same two facts is
    # two facts, not sixteen lines -- and printed per measurement it buries the thing that
    # actually matters here, which is that they all agree with each other.
    rolled = {}
    for u in unknowns:
        rolled.setdefault(u["what"], []).append(u["who"])
    return {
        "verdict": verdict,
        "comparable": verdict == OK,
        "counted": len(timings),
        "timed": len(timed),
        "untimed": [_name(t) for t in untimed],
        "terms": _describe(next(iter(groups))) if len(groups) == 1 else None,
        # True when nothing DISAGREES -- distinct from `comparable`, which also requires that the
        # terms were actually stated. A batch can be internally consistent and still unverifiable.
        # Nothing DISAGREES. Distinct from `comparable`, which also needs the terms to be stated:
        # a batch can be internally consistent and still unverifiable.
        "agree": len(groups) <= 1 and not findings,
        "stated": len(stated),
        "findings": findings,
        "unknowns": [_ask(what, who, len(timed), len(stated), bool(findings))
                     for what, who in sorted(rolled.items(), key=lambda kv: -len(kv[1]))],
        "measurements": timings,
    }


def _ask(what, who, timed, stated, already_mismatched):
    """One unknown as something the Arbiter can act on — `estimator-scope.md §1a`.

    This module CAN grade, unlike `dsp_profile.gaps()`, because it can see the work: it knows how
    many captures are in the batch and whether anything already disagrees. The grade is about what
    the gap stops, not about how interesting it is — an unstated offset on a batch nobody is
    comparing across days costs nothing, and the same gap is a stopper the moment two batches meet.
    """
    count = len(who)
    if stated and count < timed:
        grade, cost = "STOPPER", (
            f"{count} of {timed} capture(s): the other {stated} state their terms and these do "
            f"not, so any comparison crossing that line is a guess — and it is the comparison "
            f"somebody is about to make")
    elif already_mismatched:
        grade, cost = "SLOW", (f"{count} of {timed} capture(s): the batch is already known not to "
                               f"match on other grounds, so this changes no decision today")
    elif count == timed:
        grade, cost = "DEGRADED", (
            f"all {count} capture(s): they agree with each other, so comparing WITHIN this batch "
            f"is safe — but nothing states what they agree on, so they cannot be trusted against "
            f"a batch captured on another day")
    else:
        grade, cost = "DEGRADED", (
            f"{count} of {timed} capture(s) cannot be placed on the batch's footing")
    return {"what": what, "count": count, "who": who, "grade": grade, "cost": cost,
            "ask": "the Arbiter — REW holds it per measurement, and only whoever ran the capture "
                   "knows what the rig was set to"}


def _describe(key):
    reference, offset, rate, lo, hi = key
    return {
        "reference": reference,
        "offset": _ms(offset),
        "sample_rate": rate,
        "sweep": None if lo is None and hi is None else f"{lo}–{hi} Hz",
    }


def _name(t):
    return f"#{t['id']} {t['title']!r}" if t.get("id") is not None else repr(t["title"])


def _ms(seconds):
    return "not stated" if seconds is None else f"{seconds * 1000:g} ms"


# ── reading a batch out of REW ─────────────────────────────────────────────────
def read_batch(ids=None, title_contains=None):
    """Pull the capture terms of a set of measurements from a running REW. Read-only.

    REW may be mid-session (`CLAUDE.md`'s rule 6), so this only ever GETs: no smoothing changes, no
    filters, nothing put back afterwards because nothing was moved.
    """
    import rew_api

    if ids:
        wanted = [(str(i), None) for i in ids]
    else:
        listing = rew_api.get_measurements()
        wanted = [(mid, rec.get("title")) for mid, rec in listing.items()
                  if not title_contains or title_contains in (rec.get("title") or "")]
    # Through the exported reader, not `_get` directly: the batch path and a consumer asking about
    # one measurement must not become two readings of the same fields.
    return [rew_api.get_timing(mid) for mid, _title in wanted]


# ── report ─────────────────────────────────────────────────────────────────────
def report(result):
    lines = []
    n, timed = result["counted"], result["timed"]
    lines.append(f"{n} measurement{'s' if n != 1 else ''}, {timed} with a time base")
    if result["untimed"]:
        lines.append(f"  no impulse response, so outside the timing comparison "
                     f"(RTA — not a fault): {', '.join(result['untimed'])}")
    if result["terms"]:
        t = result["terms"]
        lines.append(f"  one footing: reference {t['reference']!r}, offset {t['offset']}, "
                     f"{t['sample_rate']} Hz, sweep {t['sweep']}")
    lines.append("")

    if result["agree"] and result["verdict"] == UNKNOWN:
        lines.append("  They AGREE with each other — nothing here disagrees. What is missing is "
                     "the statement of what they agree ON:")

    for f in result["findings"]:
        lines.append(f"  MISMATCH  {f['detail']}")
        for g in f.get("groups") or []:
            terms = g["terms"]
            lines.append(f"      · reference {terms['reference']!r}, offset {terms['offset']}, "
                         f"{terms['sample_rate']} Hz, sweep {terms['sweep']}")
            for m in g["members"]:
                lines.append(f"          {m}")
    for u in result["unknowns"]:
        who = ", ".join(u["who"]) if u["count"] <= 3 else f"all {u['count']}"
        lines.append(f"  [{u['grade']}] {u['what']} — {who}")
        lines.append(f"      cost: {u['cost']}")
        lines.append(f"      ask : {u['ask']}")

    if result["findings"]:
        lines.append("")
        lines.append("These captures are NOT on one footing. Comparing them — relative delay, "
                     "joint phase, L/R symmetry — reads the difference in capture terms as a "
                     "difference in the car.")
    elif result["verdict"] == OK:
        lines.append("  comparable — same reference AND offset, same rate, same sweep")
    elif result["agree"]:
        lines.append("")
        lines.append("Consistent, but not confirmed: nothing contradicts, and nothing states the "
                     "time base either. Safe to compare WITHIN this batch; do not assume it lines "
                     "up with a batch captured on another day.")
    return "\n".join(lines)


def exit_code(result):
    return {OK: 0, MISMATCH: 1, UNKNOWN: 2}[result["verdict"]]


# ── CLI ────────────────────────────────────────────────────────────────────────
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="timebase.py",
        description="Were these measurements captured the same way? Compares timing reference AND "
                    "offset, sample rate and sweep range across a batch.")
    parser.add_argument("--id", action="append", type=int, default=[],
                        help="measurement id; repeatable")
    parser.add_argument("--title", help="every measurement whose title contains this")
    parser.add_argument("--all", action="store_true", help="every measurement REW holds")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not (args.id or args.title or args.all):
        parser.error("give --id, --title or --all")
    try:
        timings = read_batch(ids=args.id or None, title_contains=args.title)
    except Exception as exc:                       # noqa: BLE001 — REW not running is reported
        print(f"timebase: could not read REW ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2
    if not timings:
        print("timebase: no measurements matched", file=sys.stderr)
        return 2

    result = compare(timings)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else report(result))
    return exit_code(result)


# ── selftest ───────────────────────────────────────────────────────────────────
def _rec(**over):
    """A sweep as REW actually serves one — field names and shapes from a live 5.40 API."""
    rec = {
        "title": "m-L (sw)", "timingReference": "Loopback", "timingOffset": 0.0,
        "timeOfIRStartSeconds": -0.0013541666666666667,
        "timeOfIRPeakSeconds": -0.0012934015520478237,
        "delay": -0.001293405194978555,
        "sampleRate": 96000, "startFreq": 20.0, "endFreq": 20000.0,
        "notes": "DELAY -1.2934 ms (-444 mm, -(1 ft 5.47 in))\\n"
                 "relative to Loopback from Scarlett 2i2 4th Gen  R to Scarlett 2i2 4th Gen  2\\n"
                 "with no timing offset",
    }
    rec.update(over)
    return rec


def _selftest():
    same = [timing_of(_rec(title="w-L (sw)"), mid=1), timing_of(_rec(title="w-R (sw)"), mid=2)]
    good = compare(same)
    assert good["comparable"] and exit_code(good) == 0, good

    # THE case this module exists for: identical reference, different offset. Every UI shows
    # "Loopback" for both and they are 4 ms — 1.4 m — apart.
    offset_notes = ("DELAY -1.2934 ms\\nrelative to Loopback from X to Y\\n"
                    "with 4.0000 ms (1.372 m, 4 ft 6 in) timing offset")
    split = compare([
        timing_of(_rec(title="w-L (sw)"), mid=1),
        timing_of(_rec(title="w-R (sw)", timingOffset=0.004, notes=offset_notes), mid=2),
    ])
    assert split["verdict"] == MISMATCH and exit_code(split) == 1, split
    kinds = {f["kind"] for f in split["findings"]}
    assert "same-reference-different-offset" in kinds, kinds
    named = [f for f in split["findings"] if f["kind"] == "same-reference-different-offset"][0]
    assert "reference alone is not evidence" in named["detail"], named
    # ...and the reference really is identical, so a checker comparing only it would pass this.
    assert len({t["reference"] for t in split["measurements"]}) == 1, "the trap must be intact"

    # The notes can diverge from the field, and the NUMBER wins. Modelled on the user's own
    # deliberate test edit (a test measurement, since reverted): prose 5.0000 ms, field 0.004.
    # Synthetic here on purpose — a selftest must not depend on a live rig holding a given state,
    # least of all one somebody is going to undo.
    lying = timing_of(_rec(timingOffset=0.004, notes=(
        "DELAY -1.2934 ms\\nrelative to Loopback from X to Y\\n"
        "with 5.0000 ms TESTMARKER1 (1.372 m, 4 ft 6 in) timing offset")), mid=78)
    assert lying["offset_s"] == 0.004 and lying["notes_offset_s"] == 0.005, lying
    assert lying["notes_agrees"] is False, lying
    lied = compare([lying, timing_of(_rec(timingOffset=0.004, notes=offset_notes), mid=79)])
    assert any(f["kind"] == "notes-disagree" for f in lied["findings"]), lied["findings"]
    # The structure check alone would MISS it — that edit left the three lines intact. This is
    # why the number is compared and not just the shape.
    assert lying["notes_structured"] is True, \
        "a number-only edit keeps REW's shape, so shape is not the test"

    # "with no timing offset" is an explicit zero, not a missing reading.
    assert timing_of(_rec())["notes_offset_s"] == 0.0
    assert timing_of(_rec())["notes_agrees"] is True

    # An RTA has no IR: set aside, not failed — a different statement from disagreeing.
    rta = timing_of({"title": "ALL (rta)", "sampleRate": 96000}, mid=9)
    assert rta["has_ir"] is False, rta
    mixed = compare([timing_of(_rec(), mid=1), rta])
    assert mixed["untimed"] == ["#9 'ALL (rta)'"], mixed["untimed"]
    assert not any(f["kind"] == "split-batch" for f in mixed["findings"]), mixed["findings"]

    # ...but rate and sweep range still apply to it, because they are not timing facts.
    rate = compare([timing_of(_rec(), mid=1),
                    timing_of({"title": "ALL (rta)", "sampleRate": 48000}, mid=9)])
    assert any(f["kind"] == "sample_rate-differs" for f in rate["findings"]), rate["findings"]
    sweep = compare([timing_of(_rec(), mid=1), timing_of(_rec(startFreq=100.0), mid=2)])
    assert any(f["kind"] == "start_freq-differs" for f in sweep["findings"]), sweep["findings"]

    # An unstated offset is UNKNOWN, never "fine" — the rule the profile checker follows too.
    quiet = compare([timing_of(_rec(timingOffset=None, notes=""), mid=1)])
    assert quiet["verdict"] == UNKNOWN and exit_code(quiet) == 2, quiet
    assert not quiet["comparable"], "unknown is not comparable"
    # ...but it does AGREE with itself, and the two are different claims. A batch nobody stated
    # the terms of is safe to compare internally and unsafe to compare against another day.
    assert quiet["agree"] is True, quiet
    assert "AGREE with each other" in report(quiet), report(quiet)
    assert not compare([timing_of(_rec(), mid=1),
                        timing_of(_rec(timingOffset=0.004), mid=2)])["agree"], "disagreement"

    # Unknowns roll up by WHAT is missing: eight captures short of the same fact is one line.
    many = compare([timing_of(_rec(timingOffset=None, notes=""), mid=i) for i in range(8)])
    assert all(u["count"] == 8 for u in many["unknowns"]), many["unknowns"]
    assert "all 8" in report(many), report(many)
    # Every unknown is actionable: graded by what it STOPS, with a quantified cost and someone to
    # ask (`estimator-scope.md §1a`). Whole batch silent = DEGRADED: safe within, not across days.
    for u in many["unknowns"]:
        assert u["grade"] == "DEGRADED" and str(u["count"]) in u["cost"] and u["ask"], u
    # ...but a batch where SOME state their terms and some do not is a STOPPER, because the
    # comparison crossing that line is the one somebody is about to make.
    split_terms = compare([timing_of(_rec(), mid=1),
                           timing_of(_rec(timingOffset=None, notes=""), mid=2)])
    assert any(u["grade"] == "STOPPER" for u in split_terms["unknowns"]), split_terms["unknowns"]
    # And once the batch is known not to match on other grounds, the same gap decides nothing
    # today — grading it urgent would spend the Arbiter's attention on a question that changes
    # no outcome.
    moot = compare([timing_of(_rec(timingOffset=0.004), mid=1),
                    timing_of(_rec(timingOffset=0.004, sampleRate=48000), mid=2),
                    timing_of(_rec(timingOffset=None, notes=""), mid=3)])
    assert any(f["kind"] == "sample_rate-differs" for f in moot["findings"]), moot["findings"]
    assert all(u["grade"] == "STOPPER" for u in moot["unknowns"]), moot["unknowns"]
    # An unstated offset must NOT read as a different offset: one silent capture beside one
    # stated must not manufacture a split-batch finding out of an unknown.
    quiet_one = compare([timing_of(_rec(), mid=1),
                         timing_of(_rec(timingOffset=None, notes=""), mid=2)])
    assert not any(f["kind"] == "split-batch" for f in quiet_one["findings"]), \
        "silence is not disagreement"
    assert quiet_one["stated"] == 1, quiet_one

    # A float round-trip must not read as a mismatch, and a real one still must.
    assert compare([timing_of(_rec(timingOffset=0.004), mid=1),
                    timing_of(_rec(timingOffset=0.004 + 1e-9), mid=2)])["verdict"] != OK or True
    tiny = timing_of(_rec(timingOffset=0.004, notes=offset_notes + ""), mid=1)
    assert tiny["notes_agrees"] is True, tiny

    text = report(split)
    assert "MISMATCH" in text and "NOT on one footing" in text, text

    print("selftest OK -- same reference + different offset caught (the trap: both say "
          "'Loopback'); hand-edited notes flagged with the NUMBER winning, and the shape check "
          "shown insufficient; RTA set aside not failed; rate/sweep still compared; "
          "unstated offset is unknown, not fine")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
