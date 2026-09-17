#!/usr/bin/env python3
"""xover_wishes -- the tuner's crossover wishes, in free words, checked against the hard limits.

Phase 1 starts with what the tuner wants, said the way a tuner says it: "BE4 between tweeter and
mid, BW2 between sub and midbass, not sure between midbass and mid" (the user, 2026-09-17;
docs/DESIGN-2026-09-17-phase1-variants.md §1 steps 3-6). No form. This module reads that sentence,
finds the junction each clause is about, and asks of each wish the questions that have a hard
answer BEFORE any variant is computed:

  * does this DSP have the family, at that slope, at that corner (the profile's
    `crossover_filters`: types, orders, the corner range and step -- a filter the device will not
    accept is not a variant);
  * is the corner clear of the fragile driver's installed Fs (`crossover_checks.fs_margin`: below
    the protective floor the answer is REFUSE, up to the craft convention CAUTION -- and a gentler
    slope wants a higher corner, which is why the order goes in).

A wish that breaks a limit is NOT computed; the nearest allowed setting is named instead --
"BW2 on your tweeter from 1034 Hz (clear of caution from 1880)" -- so the tuner can say yes to that
or change their mind. A wish nobody can check (no Fs on record, or an Fs carried in from another
project) is reported as unchecked with what would settle it; it is never guessed past.

"Not sure" is a wish too: it says the desk proposes for that junction.

    python3 rew_tool/xover_wishes.py <project-dir> "BE4 between tweeter and mid, BW2 sub-midbass at 60"
    python3 rew_tool/xover_wishes.py <project-dir> "..." --json
    python3 rew_tool/xover_wishes.py --selftest

stdlib only (it borrows `crossover_checks`, `project` and `dsp_profile`, all stdlib).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import crossover_checks as _cc  # noqa: E402
import dsp_profile as _dp  # noqa: E402
import project as _pj  # noqa: E402

# ---------------------------------------------------------------- the words a tuner uses
#: Channel roles in the order they stack up a side, low to high. `project.json`'s `role` values.
ROLE_ORDER = ("sub", "woofer", "midrange", "tweeter")
#: Roles that stand outside the front chain and carry their own crossover (Resonalyze's zones).
OWN_ZONE_ROLES = ("center", "rear")
#: LF-fragile roles: a corner below their Fs is a broken driver, not a taste. Midbass and sub are
#: built for LF (`core/project-intake.md` §3, "Other Drivers").
FRAGILE_ROLES = ("tweeter", "midrange", "center", "rear")

_ROLE_WORDS = (
    # longest first inside each role, so "midbass" is not read as "mid" + "bass"
    ("sub", ("subwoofer", "sub", "сабвуфер", "саб", "sw")),
    ("woofer", ("midbass", "mid-bass", "woofer", "мідбас", "мидбас", "мід-бас", "нч", "w")),
    ("midrange", ("midrange", "mid-range", "mids", "mid", "середина", "середні", "сч", "m")),
    ("tweeter", ("tweeters", "tweeter", "твітер", "твитер", "пищалка", "вч", "tw")),
    ("center", ("center", "centre", "центр", "c")),
    ("rear", ("rear", "rears", "тил", "задні", "задние", "r")),
)
_FAMILY_WORDS = (
    ("BE", ("bessel", "бессел", "be")),
    ("BW", ("butterworth", "баттерворт", "батерворт", "bw")),
    ("LR", ("linkwitz-riley", "linkwitz", "лінквіц", "линквиц", "lr")),
)
_UNSURE = ("not sure", "don't know", "dont know", "no idea", "unsure", "не знаю", "не впевнен",
           "хз", "?")

_FAMILY_RE = re.compile(r"\b(bessel|butterworth|linkwitz(?:-riley)?|бессел[ья]?|баттерворт[а]?|"
                        r"батерворт[а]?|лінквіц[а]?|линквиц[а]?|be|bw|lr)\s*-?\s*(\d{1,2})?\b", re.I)
_ORDER_RE = re.compile(r"\b(\d{1,2})\s*(?:db(?:/oct)?|дб(?:/окт)?|th\s*order|nd\s*order|rd\s*order|"
                       r"st\s*order|-го\s*порядку|порядк)", re.I)
_FREQ_RE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(khz|kгц|кгц|k|hz|гц)?(?![\w])", re.I)
_RANGE_RE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(k|khz|hz|гц|кгц)?\s*(?:-|–|—|\.\.\.?|to|до)\s*"
                       r"(\d+(?:[.,]\d+)?)\s*(k|khz|hz|гц|кгц)?(?![\w])", re.I)


def _num(text, unit):
    v = float(text.replace(",", "."))
    if unit and unit.lower().startswith("k") or (unit and unit.lower() == "кгц"):
        v *= 1000.0
    return v


def _roles_in(clause):
    """The roles named in a clause, in the order they appear -- by whole word, longest form first."""
    low = clause.lower()
    # "mid-bass" is one word; "sub-midbass", "mid/tweeter", "sub ↔ w" are two channels with a
    # separator between them. Fold the compounds first, then every separator becomes a space.
    for compound, one in (("mid-bass", "midbass"), ("mid-range", "midrange"), ("мід-бас", "мідбас")):
        low = low.replace(compound, one)
    low = " " + re.sub(r"[^\w]+", " ", low) + " "
    found = []
    for role, words in _ROLE_WORDS:
        best = None
        for w in words:
            # a Cyrillic word is read in any case ending ("мідбасом", "саба", "твітером"); a Latin
            # one whole, so "mid" never matches inside "midbass"
            tail = r"[а-яіїєґ]{0,3}" if re.search(r"[а-яіїєґ]", w) else ""
            for m in re.finditer(r"(?<!\w)" + re.escape(w) + tail + r"(?!\w)", low):
                if best is None or m.start() < best:
                    best = m.start()
        if best is not None:
            found.append((best, role))
    found.sort()
    out = []
    for _, role in found:
        if role not in out:
            out.append(role)
    return out


def _order_db(number, family_present):
    """`4` -> 24 (poles x 6), `24` -> 24 (dB/oct); `6` is both and is refused as ambiguous."""
    n = int(number)
    if n == 6:
        return None, "6 is 6 dB/oct and a 6th order alike -- say 'BE36' or 'BE1'"
    if n <= 8:
        return n * 6, None
    if n % 6 == 0 and n <= 48:
        return n, None
    return None, f"{n} is neither a pole count (1-8) nor a slope in dB/oct (6..48)"


def parse_wishes(text):
    """Free words -> a list of wishes, one per clause.

    Each: `{"clause", "roles", "family", "order_db", "f_hz", "f_range_hz", "unsure", "problems"}`.
    `roles` are the channel roles the clause names, in order; a family without an order and an
    order without a family are kept as they are -- the check says what is missing.
    """
    wishes = []
    for raw in re.split(r"[,;\n]+|\s+(?:and then|then)\s+", text or ""):
        clause = raw.strip(" .")
        if not clause:
            continue
        low = clause.lower()
        w = {"clause": clause, "roles": _roles_in(clause), "family": None, "order_db": None,
             "f_hz": None, "f_range_hz": None, "unsure": any(u in low for u in _UNSURE),
             "problems": []}
        consumed = []
        m = _FAMILY_RE.search(clause)
        if m:
            word = m.group(1).lower()
            for family, words in _FAMILY_WORDS:
                if any(word.startswith(x) for x in words):
                    w["family"] = family
            if m.group(2):
                w["order_db"], err = _order_db(m.group(2), True)
                if err:
                    w["problems"].append(err)
            consumed.append(m.span())
        m = _ORDER_RE.search(clause)
        if m and w["order_db"] is None:
            w["order_db"], err = _order_db(m.group(1), w["family"] is not None)
            if err:
                w["problems"].append(err)
            consumed.append(m.span())

        def free(span):
            return not any(a <= span[0] < b or a < span[1] <= b for a, b in consumed)

        m = _RANGE_RE.search(clause)
        if m and free(m.span()):
            lo, hi = _num(m.group(1), m.group(2) or m.group(4)), _num(m.group(3), m.group(4))
            if 10 <= lo < hi <= 25000:
                w["f_range_hz"] = [lo, hi]
                w["f_hz"] = round(math.sqrt(lo * hi), 1)      # the geometric middle stands for the range
                consumed.append(m.span())
        if w["f_hz"] is None:
            for m in _FREQ_RE.finditer(clause):
                if not free(m.span()):
                    continue
                v = _num(m.group(1), m.group(2))
                if m.group(2) or 15 <= v <= 25000:
                    w["f_hz"] = v
                    consumed.append(m.span())
                    break
        wishes.append(w)
    return wishes


# ---------------------------------------------------------------- the project side
def _channels(project_dir):
    data = _pj.Project(project_dir).load()
    out = {}
    for row in data.get("channels") or []:
        if row.get("hidden") or row.get("role") in (None, "unused", "virtual"):
            continue
        out[row["code"]] = row
    return out


def _fs_of(row):
    """(Fs in Hz or None, the reason it cannot be used, or None)."""
    fs = row.get("fs_hz")
    if fs is None:
        return None, "no Fs on record -- measure it (`<code> (imp)`) or `project.py set-channel <code> fs_hz=<Hz>`"
    if isinstance(fs, dict) and fs.get("origin") == "inherited":
        return None, (f"Fs {_pj.fact_value(fs):g} Hz was carried in from {fs.get('inherited_from') or 'another project'} "
                      "-- confirm it (`set-channel <code> fs_hz=<Hz> --source user`) or measure it here")
    v = _pj.fact_value(fs)
    try:
        return (float(v) if v else None), (None if v else "Fs on record is empty")
    except (TypeError, ValueError):
        return None, f"Fs on record is not a number: {v!r}"


def _profile_xo(project_dir):
    """The physical outputs' crossover facts from the project's `dsp_profile.json`, or None."""
    path = os.path.join(project_dir, "dsp_profile.json")
    if not os.path.isfile(path):
        return None
    data = _dp._unwrap(_dp.load_profile(path))
    for group in data.get("groups") or []:
        if _dp.ledger_tier((group or {}).get("id")) == "channels":
            xo = group.get("crossover_filters") or {}
            return {"types": xo.get("types") or {}, "range": xo.get("corner_freq_range_hz"),
                    "step": xo.get("corner_freq_step_hz")}
    return None


def _members(channels, roles):
    """The channel codes a clause is about, per side: `{"L": (lo, hi), "R": (lo, hi)}` for a
    junction of two front roles, `{"own": (None, code)}` for a centre/rear/lone role."""
    by_role = {}
    for code, row in channels.items():
        by_role.setdefault(row.get("role"), []).append(code)
    front = [r for r in roles if r in ROLE_ORDER]
    if len(front) >= 2:
        lo, hi = sorted(front[:2], key=ROLE_ORDER.index)
        out = {}
        for side in ("L", "R"):
            lo_c = next((c for c in by_role.get(lo, []) if c.endswith("-" + side) or lo == "sub"), None)
            hi_c = next((c for c in by_role.get(hi, []) if c.endswith("-" + side) or hi == "sub"), None)
            if lo_c and hi_c:
                out[side] = (lo_c, hi_c)
        return (lo, hi), out
    if len(roles) == 1:
        role = roles[0]
        codes = by_role.get(role, [])
        return (role,), {c: (None, c) for c in codes}
    return tuple(roles), {}


def _snap(f, xo):
    """The corner as the device can hold it: within its range, on its step. Returns (f, note)."""
    if not xo:
        return f, None
    lo, hi = (xo.get("range") or [None, None])[:2]
    step = xo.get("step") or 0
    note = None
    if lo is not None and f < lo:
        f, note = float(lo), f"the device's corners start at {lo:g} Hz"
    if hi is not None and f > hi:
        f, note = float(hi), f"the device's corners end at {hi:g} Hz"
    if step:
        f = round(round(f / step) * step, 3)
    return f, note


def check_wishes(text, channels, xo=None):
    """Every clause of `text` against the channels' Fs and the device's crossover facts.

    `channels`: `{code: project.json row}` (role, fs_hz); `xo`: `_profile_xo()`'s dict or None.
    Returns a list of verdict rows, one per clause:
      verdict   OK | CAUTION | ADJUSTED | REFUSED | UNSURE | UNCHECKED | UNKNOWN
      allowed   {family, order_db, f_hz} -- the wish as it can be entered (ADJUSTED/REFUSED name
                the nearest allowed setting; OK/CAUTION repeat the wish, snapped to the step)
    """
    rows = []
    for w in parse_wishes(text):
        row = {"clause": w["clause"], "roles": w["roles"], "wish": {k: w[k] for k in ("family", "order_db", "f_hz", "f_range_hz")},
               "verdict": None, "allowed": None, "why": [], "junction": None, "members": {}}
        rows.append(row)
        if w["problems"]:
            row["why"].extend(w["problems"])
        if not w["roles"]:
            row["verdict"] = "UNKNOWN"
            row["why"].append("no channel named -- say which junction ('between mid and tweeter') or which channel")
            continue
        junction, members = _members(channels, w["roles"])
        row["junction"] = list(junction)
        row["members"] = {k: list(v) for k, v in members.items()}
        if not members:
            row["verdict"] = "UNKNOWN"
            row["why"].append(f"the project has no channel for {' / '.join(w['roles'])}")
            continue
        if w["unsure"] or (w["family"] is None and w["order_db"] is None and w["f_hz"] is None):
            row["verdict"] = "UNSURE"
            row["why"].append("no wish here -- the desk proposes for this junction")
            continue

        family, order, f = w["family"], w["order_db"], w["f_hz"]
        why, adjusted, refused = row["why"], False, False
        # 1. the device: family, slope, corner
        if xo is not None:
            types = xo["types"]
            if family and family not in types:
                have = ", ".join(sorted(types)) or "none on record"
                why.append(f"this DSP has no {family} family (it has: {have})")
                row["verdict"] = "REFUSED"
                continue
            if family and isinstance(types.get(family), dict) and types[family].get(_dp.MODELLABLE_KEY) is False:
                why.append(f"{family} is on the device but the method cannot predict it -- a variant on it cannot be computed")
                row["verdict"] = "REFUSED"
                continue
            orders = (types.get(family) or {}).get("orders_db_per_oct") if family else None
            if order and orders and order not in orders:
                steeper = [o for o in orders if o > order]
                nearest = min(steeper) if steeper else max(orders)
                why.append(f"{family} has no {order} dB/oct on this DSP (it has {', '.join(str(o) for o in orders)}); "
                           f"the nearest {'steeper' if steeper else 'available'} is {nearest}")
                order, adjusted = nearest, True
        if f is not None:
            f2, note = _snap(f, xo)
            if note:
                why.append(note)
                adjusted = True
            f = f2
        # 2. the fragile member's Fs: the high-pass side of the junction
        fragile = []
        for key, (lo_c, hi_c) in members.items():
            hi_row = channels[hi_c]
            if hi_row.get("role") in FRAGILE_ROLES:
                fragile.append((key, hi_c, hi_row))
        if f is not None and fragile:
            poles = max(1, int(round((order or 24) / 6)))
            unchecked = []
            strictest = None
            for key, code, hi_row in fragile:
                fs, reason = _fs_of(hi_row)
                if fs is None:
                    unchecked.append(f"{code}: {reason}")
                    continue
                if strictest is None or fs > strictest[1]:
                    strictest = (code, fs)
            if unchecked:
                why.extend(unchecked)
                row["verdict"] = "UNCHECKED"
                row["allowed"] = {"family": family, "order_db": order, "f_hz": f}
                continue
            code, fs = strictest
            verdict = _cc.fs_margin(f, fs, order=poles)
            floor_f, _ = _snap(math.ceil(_cc.FS_FLOOR * fs), xo)
            clear_f, _ = _snap(math.ceil(verdict["convention"] * fs), xo)
            label = f"{family or ''}{poles}".strip() or f"{order} dB/oct"
            if verdict["verdict"] == _cc.REFUSE:
                why.append(f"{code}: {verdict['why']} (Fs {fs:g} Hz)")
                why.append(f"nearest allowed: {label} on {code} from {floor_f:g} Hz -- clear of caution from {clear_f:g} Hz")
                f, refused = floor_f, True
            elif verdict["verdict"] == _cc.CAUTION:
                why.append(f"{code}: {verdict['why']} (Fs {fs:g} Hz); clear of caution from {clear_f:g} Hz")
            else:
                why.append(f"{code}: {verdict['why']} (Fs {fs:g} Hz)")
            if not refused and not adjusted and verdict["verdict"] == _cc.CAUTION:
                row["verdict"] = "CAUTION"
        elif f is None and fragile and (family or order):
            why.append("no corner named -- the family and slope are checked, the Fs floor waits for a frequency")
        row["allowed"] = {"family": family, "order_db": order, "f_hz": f}
        if row["verdict"] is None:
            row["verdict"] = "REFUSED" if refused else "ADJUSTED" if adjusted else "OK"
    return rows


def render(rows):
    lines = []
    for r in rows:
        j = " ↔ ".join(r["junction"]) if r.get("junction") else "?"
        wish = r["wish"]
        said = " ".join(x for x in (
            f"{wish['family'] or ''}{int(round((wish['order_db'] or 0) / 6)) if wish['order_db'] else ''}".strip() or None,
            (f"{wish['f_range_hz'][0]:g}-{wish['f_range_hz'][1]:g} Hz" if wish.get("f_range_hz")
             else f"at {wish['f_hz']:g} Hz" if wish.get("f_hz") else None)) if x) or "(no setting)"
        head = f"{j}: {said} -- {r['verdict']}"
        a = r.get("allowed")
        if a and r["verdict"] in ("ADJUSTED", "REFUSED") and a.get("f_hz") is not None:
            fam = f"{a['family'] or ''}{int(round((a['order_db'] or 0) / 6)) if a['order_db'] else ''}".strip()
            head += f" → enter {fam} from {a['f_hz']:g} Hz"
        lines.append(head)
        for w in r["why"]:
            lines.append(f"    · {w}")
    lines.append("The wishes are checked, not chosen: the desk computes the variants next, with and without them.")
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest
def _selftest():
    ch = {"sw": {"code": "sw", "role": "sub", "fs_hz": 43.9},
          "w-L": {"code": "w-L", "role": "woofer", "fs_hz": 52.4}, "w-R": {"code": "w-R", "role": "woofer", "fs_hz": 52.4},
          "m-L": {"code": "m-L", "role": "midrange", "fs_hz": {"value": 194.8, "source": "measured"}},
          "m-R": {"code": "m-R", "role": "midrange", "fs_hz": {"value": 196.7, "source": "measured"}},
          "tw-L": {"code": "tw-L", "role": "tweeter", "fs_hz": {"value": 939.7, "source": "measured"}},
          "tw-R": {"code": "tw-R", "role": "tweeter", "fs_hz": {"value": 948.9, "source": "measured"}},
          "c": {"code": "c", "role": "center", "fs_hz": None}}
    xo = {"types": {"BE": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42], "modellable": True},
                    "BW": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42], "modellable": True},
                    "LR": {"orders_db_per_oct": [12, 24, 36], "modellable": True}},
          "range": [20.0, 20480.0], "step": 1.0}

    # the user's own sentence: three clauses, two wishes and one "not sure"
    rows = check_wishes("думаю про BE4 між ВЧ та СЧ, BW2 на НЧ між саб і мідбас, і не знаю що краще між мідбасом і СЧ", ch, xo)
    assert [r["junction"] for r in rows] == [["midrange", "tweeter"], ["sub", "woofer"], ["woofer", "midrange"]], rows
    assert rows[0]["wish"]["family"] == "BE" and rows[0]["wish"]["order_db"] == 24 and rows[0]["verdict"] == "OK", rows[0]
    assert rows[1]["wish"] == {"family": "BW", "order_db": 12, "f_hz": None, "f_range_hz": None} and rows[1]["verdict"] == "OK", rows[1]
    assert rows[2]["verdict"] == "UNSURE", rows[2]
    assert rows[0]["members"] == {"L": ["m-L", "tw-L"], "R": ["m-R", "tw-R"]}, rows[0]["members"]

    # a corner below the tweeter's floor is REFUSED and the nearest allowed is named, in the user's form
    rows = check_wishes("BW2 between mid and tweeter at 900 Hz", ch, xo)
    r = rows[0]
    assert r["verdict"] == "REFUSED" and r["allowed"]["f_hz"] == 1044.0 and r["allowed"]["order_db"] == 12, r
    assert any("from 1044 Hz" in w and "1898 Hz" in w for w in r["why"]), r["why"]      # 1.1 x 948.9 / 2.0 x 948.9
    assert "tw-R" in "".join(r["why"]), "the stricter of the pair's two Fs decides"
    # ...the same corner with a steep slope is only CAUTION (the convention relaxes with order)
    r = check_wishes("LR4 between mid and tweeter at 1200", ch, xo)[0]
    assert r["verdict"] == "CAUTION" and r["allowed"]["f_hz"] == 1200.0, r
    r = check_wishes("LR4 mid/tweeter 3k", ch, xo)[0]
    assert r["verdict"] == "OK" and r["allowed"]["f_hz"] == 3000.0, r
    # a range is read at its geometric middle
    r = check_wishes("BE4 sub-midbass 60-80", ch, xo)[0]
    assert r["wish"]["f_range_hz"] == [60.0, 80.0] and abs(r["wish"]["f_hz"] - 69.3) < 0.1 and r["verdict"] == "OK", r

    # the device: a family it lacks, a slope it lacks (snapped steeper), a corner off its range
    r = check_wishes("LR3 between mid and tweeter at 3000", ch, xo)[0]          # LR has 12/24/36 here, not 18
    assert r["verdict"] == "ADJUSTED" and r["allowed"]["order_db"] == 24, r
    xo_nolr = {"types": {k: v for k, v in xo["types"].items() if k != "LR"}, "range": xo["range"], "step": xo["step"]}
    r = check_wishes("LR4 between mid and tweeter at 3000", ch, xo_nolr)[0]
    assert r["verdict"] == "REFUSED" and "no LR family" in r["why"][0], r
    r = check_wishes("BW4 sub and midbass at 12 Hz", ch, xo)[0]
    assert r["verdict"] == "ADJUSTED" and r["allowed"]["f_hz"] == 20.0, r
    # 24 dB/oct spelled as a slope, and a bare order word
    r = check_wishes("Bessel 24 dB/oct between mid and tweeter at 3500", ch, xo)[0]
    assert r["wish"]["order_db"] == 24 and r["verdict"] == "OK", r
    r = check_wishes("BE6 between mid and tweeter at 3500", ch, xo)[0]
    assert r["wish"]["order_db"] is None and any("ambiguous" in w or "6 is" in w for w in r["why"]), r

    # what cannot be checked is said, never guessed past: no Fs, an inherited Fs
    r = check_wishes("BW4 on the center at 300", ch, xo)[0]
    assert r["verdict"] == "UNCHECKED" and "no Fs on record" in r["why"][0], r
    ch2 = dict(ch, **{"tw-L": {"code": "tw-L", "role": "tweeter",
                               "fs_hz": {"value": 939.7, "origin": "inherited", "inherited_from": "/x"}}})
    r = check_wishes("BE4 mid-tweeter at 3000", ch2, xo)[0]
    assert r["verdict"] == "UNCHECKED" and "carried in" in r["why"][0], r
    # nothing named at all
    r = check_wishes("something gentle please", ch, xo)[0]
    assert r["verdict"] == "UNKNOWN", r
    # the rendering carries the nearest allowed in the form the user asked for
    text = render(check_wishes("BW2 between mid and tweeter at 900 Hz", ch, xo))
    assert "→ enter BW2 from 1044 Hz" in text and "not chosen" in text, text
    print("selftest[xover_wishes] OK -- the user's own sentence parses to two wishes and a 'not sure'; a "
          "corner under the tweeter's floor is refused with 'BW2 from 1044 Hz' named; a steep slope at the "
          "same corner is caution; a missing family is refused, a missing slope snapped steeper, a corner "
          "off the range snapped in; no Fs and an inherited Fs are unchecked, never guessed")
    return 0


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the tuner's crossover wishes, checked against the hard limits")
    ap.add_argument("project", nargs="?", help="the project folder (project.json, dsp_profile.json)")
    ap.add_argument("wishes", nargs="?", help="the wishes, in free words, one sentence")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.project or not a.wishes:
        ap.error("need <project-dir> and the wishes in one string")
    channels = _channels(a.project)
    if not channels:
        print(f"{a.project}: no channels with a role in project.json -- Phase -1 first", file=sys.stderr)
        return 2
    xo = _profile_xo(a.project)
    if xo is None:
        print(f"{a.project}: no dsp_profile.json -- the device's families and corners are not checked", file=sys.stderr)
    rows = check_wishes(a.wishes, channels, xo)
    print(json.dumps(rows, indent=1, ensure_ascii=False) if a.json else render(rows))
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(_main())
