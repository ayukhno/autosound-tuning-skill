"""Two `.pct6` files side by side, or one file against expected values. Read only.

Every difference lands in one category, so what changes the sound is never mixed with what does not:

* `audio` -- gain, delay, phase, polarity, mute, filters, crossovers, routing;
* `system` -- effects, remote, CONDUCTOR, source selection: stored settings outside the channels;
* `save_metadata` -- the save date and the path PC-Tool wrote (ATF D/FN, ATFCOND D);
* `naming` -- a channel's name and position label (CHS, the legacy CN code): known, but not sound;
* `ui_state` -- PC-Tool's window state (LG), not sound;
* `unknown` -- fields whose meaning is not established; never counted as a match;
* `structure` -- an element that is in one file and not in the other.

Attribute order and indentation never make a difference; the order of filters and matrix indices does.
"""

import math
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from . import models
from .container import Document
from .inventory import SAVE_METADATA, flatten

_AUDIO_TAGS = {"OC", "IC", "Vol", "T", "Fil", "R"}
_SYSTEM_TAGS = {"STX", "ABP", "MCV2", "DCM", "DC", "SW", "V", "ATFCOND", "GLB", "VOL", "TC"}
_ROOT_UNKNOWN = {"AV", "VM", "VCO", "JPT", "IOR", "IGL", "IGM", "FV", "TM", "ICT"}
_CHANNEL_UNKNOWN = {"DG", "GD", "EqBy", "CE", "Finit"}


def _last_tag(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.startswith(("@", "#"))]
    return re.sub(r"\[.*\]$", "", parts[-1]) if parts else ""


def category(path: str) -> str:
    if path in SAVE_METADATA:
        return "save_metadata"
    if path.endswith("/#element"):
        return "structure"
    key = path.rsplit("/@", 1)[1] if "/@" in path else ""
    tag = _last_tag(path)
    if tag in ("OC", "IC") and key == "LG":
        return "ui_state"
    if tag == "CHS" or (tag in ("OC", "IC") and key == "CN"):
        return "naming"
    if tag == "ATF" and key in _ROOT_UNKNOWN:
        return "unknown"
    if tag in ("OC", "IC") and key in _CHANNEL_UNKNOWN:
        return "unknown"
    if tag in _AUDIO_TAGS:
        return "audio"
    if tag in _SYSTEM_TAGS or path.startswith("/ATF/ATFCOND"):
        return "system"
    return "unknown"


def differences(left: Document, right: Document, ignore_save_metadata: bool = False) -> dict:
    """`{"device": ..., "warning": ..., "counts": {category: n}, "differences": [...]}` between two files."""
    a, b = flatten(left.root), flatten(right.root)
    rows = []
    for path in sorted(a.keys() | b.keys()):
        if a.get(path) == b.get(path):
            continue
        cat = category(path)
        if ignore_save_metadata and cat == "save_metadata":
            continue
        rows.append({"path": path, "left": a.get(path), "right": b.get(path), "category": cat})
    counts = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    notes = []
    if left.dev != right.dev:
        notes.append("the two files are for different models (Dev %s and %s)" % (left.dev, right.dev))
    return {"warning": models.WARNING, "devices": [models.describe(left.dev), models.describe(right.dev)],
            "notes": notes, "counts": counts, "differences": rows}


def check(doc: Document, expected: Iterable[dict]) -> list:
    """One file against expected values: `[{path, expected, policy[, unit]}]` -> a verdict per row.

    `policy` says what is compared: `raw` -- the stored string; `display_delay_ms` -- a delay as PC-Tool shows it
    (half up to 0.01 ms at the model's clock); `db` -- a level in dB to the given `tolerance` (default: the
    precision the expected value is written with); `number` -- the stored value as a number, to the same `tolerance`.
    A path the file does not hold is `missing`, never a match.
    """
    values = flatten(doc.root)
    device = models.describe(doc.dev)
    clock = device["clock_hz"] or device["clock_assumed_hz"]
    out = []
    for row in expected:
        path, want, policy = row["path"], row["expected"], row.get("policy", "raw")
        got = values.get(path)
        verdict = {"path": path, "expected": want, "actual_raw": got, "policy": policy}
        if got is None:
            verdict["result"] = "missing"
        elif policy == "raw":
            verdict["result"] = "match" if str(want) == got else "differs"
        elif policy == "display_delay_ms":
            shown = (Decimal(got) * 1000 / Decimal(clock)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            verdict["actual"] = float(shown)
            verdict["result"] = "match" if Decimal(str(want)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == shown \
                else "differs"
        elif policy in ("db", "number"):
            try:
                number = float(got)
            except ValueError:
                number = None
            if policy == "db":
                actual = 20 * math.log10(number) if number is not None and number > 0 else None
            else:
                actual = number
            verdict["actual"] = actual
            tol = row.get("tolerance")
            if tol is None:
                text = str(want)
                places = len(text.split(".")[1]) if "." in text else 0
                tol = 0.5 * 10 ** (-places)
            if number is None:
                verdict["result"] = "unknown"
                verdict["reason"] = "the stored value %r is not a number" % got
            else:
                verdict["result"] = "differs" if actual is None else (
                    "match" if abs(actual - float(want)) <= tol + 1e-9 else "differs")
        else:
            verdict["result"] = "unknown"
            verdict["reason"] = "policy %r is not known" % policy
        verdict["category"] = category(path)
        if verdict["category"] == "unknown" and verdict["result"] == "match":
            verdict["result"] = "unknown"            # an unknown field never counts as a match
        out.append(verdict)
    return out
