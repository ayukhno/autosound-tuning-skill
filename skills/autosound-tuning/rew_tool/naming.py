"""Measurement naming as code — SCR-008.

The grammar and the per-car glossary have until now lived only as prose:
`naming-and-structure.md §3` for the grammar, `autosound_context.md §5` for the codes. Two readers
means two readings, and the front-end ended up hard-coding a capture series that no car actually
has.

    name = <channel|pair|combo|joint>[ <modifier>]_<N>[ (<method>)][ <clarification>]
         | <channel>[ <modifier>] (imp)[ <clarification>]

    sw_1 (sw)        w-L_2 (rta)      ALL+C_25 (rta)      L w+m_3 (sw)      tw-R_final (rta)
    sw-f_1 (sw)      sw-r_1 (sw)      SWs_1 (sw)          SWs+Ws_2 (rta)      (two subwoofers:
                     front and rear are channels, `SWs` is their pair, `SWs+Ws` the joint)
    r-L_17 (sw) noXO                  w-L (imp)           sw (imp) case35l, NO cotton wool

* **`_N` is the number of the measurement series.** Every capture of a series shares it
  (`_04 (sw)`, `_04 (rta)`). The relation runs one way: a DSP state has several series, and a
  changed DSP starts a new one -- `_N` does not number DSP states (the user, 2026-09-17). Saving to
  a DSP slot or a backup file does not move it, and it is not the ledger's `v_NNN`: that counter
  also moves for changes that are not the DSP's (skill #37, hub TCC-016). `final` is allowed.
* **Method suffix**: `(sw)` = acoustic sweep, for phase/time/distortion; `(rta)` = MMM RTA, for
  magnitude/tone; `(imp)` = impedance sweep, for a driver's resonance in the install -- the one
  method with no `_N`: an impedance measurement is not tied to a DSP state (skill #33). Phases 0 and 2 want sw and
  rta per driver.
* **Modifiers** (`FX`, `c FX`, …) and **transient experiment tags** (`INV`, `i`, `+Δτ`) sit
  between the code and `_N`. A tag is temporary by design: once the change is baked into the base
  it drops from the name, and `dsp-state-current` — not the title — says what is committed.
* **A clarification after the method** (`noXO`, `case35l, NO cotton wool`) is free-form text that
  says what a measurement is and what it is for. It makes ANOTHER measurement in the SAME series:
  `r-L_17 (sw) noXO` is not `r-L_17 (sw)`, and both are `_17` (the user, 2026-09-16). It is kept in
  `params`, and `name_key` counts it with the modifier. A position among it (`x0`, `p3`) is still a
  position (skill #34).

The glossary is per-car and **not** a fixed list: this is the module's whole point. One project
has no rear speakers and a disabled centre; generating `r-L_2` or `c_2` for it would invent
measurements nobody can take. `active` is therefore load-bearing, not decoration.

stdlib only, py3.9+.
"""
from __future__ import annotations

import json
import os
import re
import sys

SCHEMA_VERSION = 1

METHOD_SWEEP = "sw"
METHOD_RTA = "rta"
METHOD_IMPEDANCE = "imp"
METHODS = (METHOD_SWEEP, METHOD_RTA, METHOD_IMPEDANCE)

# `<body>_<version>[ctl|rep][ (method)][ <position>]`. `body` is greedy up to the LAST underscore
# so codes that contain one still parse; version is digits or the literal `final`.
#
# Two tokens the virtual-first capture session added (the user's ruling, 2026-08-25/26):
#   * a POSITION -- `p1`…`p9` (the ellipsoid around the head), `x0` (the tripod point) -- sits
#     between the code and the version (`m-L p1_49 (sw)`) or, as REW titles were typed, after the
#     method (`w-L_49 (sw) x0`). Both parse; the canonical form is the first. It is NOT part of the
#     code: nine positions of one driver are one channel, and a checker keyed on the code would
#     otherwise see nine channels nobody has.
#   * a CONTROL -- the reference measurement repeated to read drift, for a sweep series and for the
#     ellipsoid alike: `-ctl1`/`-ctl3` in the code (the capture sheet's first/last of the tripod
#     block) or `ctl`/`rep` glued to the version as typed in the car (`m-L_49ctl`, `m-L_49rep`).
#     `ctl1`/`ctl` open a series, `ctl3`/`rep` close it.
_NAME_RE = re.compile(
    r"^(?P<body>.+)_(?P<version>\d+|final)(?P<control>ctl|rep)?"
    r"(?:\s*\((?P<method>[A-Za-z]+)\))?(?:\s+(?P<pos2>p[1-9]|x0))?\s*$"
)
# Two more forms, tried only when `_NAME_RE` has refused -- so every title that parsed before still
# parses to the same parts:
#   * a CLARIFICATION after the method (skill #34; the user, 2026-09-16): `r-L_17 (sw) noXO`.
#     `_NAME_RE` takes a lone position there and nothing else, so a whole solo set typed this way
#     read as "not ours" while `process.py` read its `_N` as unknown.
#   * an IMPEDANCE sweep, the one method with no `_N` (skill #33): `w-L (imp)`,
#     `sw2 (imp) case35l, NO cotton wool`. Its body holds no bracket, so the method is the first one.
_TAGGED_RE = re.compile(
    r"^(?P<body>.+)_(?P<version>\d+|final)(?P<control>ctl|rep)?"
    r"\s*\((?P<method>[A-Za-z]+)\)\s+(?P<tail>\S.*?)\s*$"
)
_UNVERSIONED_RE = re.compile(
    r"^(?P<body>[^()]+?)\s*\((?P<method>[A-Za-z]+)\)(?:\s+(?P<tail>\S.*?))?\s*$"
)
_POS_RE = re.compile(r"^(?P<code>.+?)\s+(?P<pos>p[1-9]|x0)$")
_POS_WORD_RE = re.compile(r"(?<!\S)(?:p[1-9]|x0)(?!\S)")
_CTL_RE = re.compile(r"^(?P<code>.+?)-(?P<ctl>ctl[0-9])$")
POSITIONS = tuple(f"p{i}" for i in range(1, 10)) + ("x0",)
CONTROL_OPEN = ("ctl1", "ctl")
CONTROL_CLOSE = ("ctl3", "rep")


class NamingError(ValueError):
    """A title that cannot be expressed in, or parsed from, the grammar."""


class Glossary:
    """The agreed codes for ONE car (`autosound_context.md §5`), as data.

    Kept deliberately shallow: a channel is a code plus whether it is currently in play. A car
    with the centre disconnected still *has* the code — excluding it from generated series is a
    per-preset fact, not a reason to forget the name exists.
    """

    def __init__(self, data=None):
        data = data or {}
        self.channels = list(data.get("channels") or [])
        self.pairs = dict(data.get("pairs") or {})
        self.combos = dict(data.get("combos") or {})
        self.joints = dict(data.get("joints") or {})
        self.sides = dict(data.get("sides") or {})

    # -- loading --
    @classmethod
    def load(cls, path):
        """Read `glossary.json`. A project without one gets an empty glossary, not an error —
        naming still parses, it just cannot check codes against anything."""
        try:
            with open(path, encoding="utf-8") as f:
                return cls(json.load(f))
        except (OSError, ValueError):
            return cls()

    @classmethod
    def for_project(cls, project_dir):
        """`<project>/glossary.json`, or the `glossary` key of `project.json` (SCR-011)."""
        standalone = os.path.join(project_dir, "glossary.json")
        if os.path.isfile(standalone):
            return cls.load(standalone)
        combined = os.path.join(project_dir, "project.json")
        try:
            with open(combined, encoding="utf-8") as f:
                return cls((json.load(f) or {}).get("glossary") or {})
        except (OSError, ValueError):
            return cls()

    # -- queries --
    def channel_codes(self, active_only=False):
        return [
            c["code"]
            for c in self.channels
            if c.get("code") and (not active_only or c.get("active", True))
        ]

    def is_active(self, code):
        code = self.resolve_code(code)
        for c in self.channels:
            if c.get("code") == code:
                return bool(c.get("active", True))
        return True  # a code we don't know about isn't ours to exclude

    def resolve_code(self, code):
        """The name a channel goes by TODAY, given any name it has ever gone by — SCR-039.

        A REW title is typed by a human and cannot be rewritten afterwards, so a channel renamed
        mid-project (a `m-L` that turned out to be a woofer) keeps its old captures under the old
        name forever. Those captures are still that channel's, taken in that series, so
        a checker that cannot resolve them reports missing work that is sitting right there.

        An unknown code comes back unchanged — a name this glossary never heard of is not ours to
        reinterpret (the same rule `is_active` follows). A live code always wins over some other
        channel's history, so a name that was handed on resolves to whoever holds it now.
        """
        if not code:
            return code
        for c in self.channels:
            if c.get("code") == code:
                return code
        for c in self.channels:
            if code in (c.get("previous_names") or []) and c.get("code"):
                return c["code"]
        return code

    def former_codes(self):
        """Every name that is no longer any channel's current one (SCR-039).

        Parsing fodder only: these are never generated into a capture plan (that would ask for a
        measurement under a name the project has retired), but a title already in REW carries one,
        and `parse_name` has to be able to split it off the modifier.
        """
        live = {c.get("code") for c in self.channels}
        return [
            str(old)
            for c in self.channels
            for old in (c.get("previous_names") or [])
            if str(old) and str(old) not in live
        ]

    def all_codes(self):
        """Every code the grammar may legally use, longest first.

        Longest-first matters for parsing: `ALL+C` must win over `ALL`, and `L w+m` over `L`, or a
        joint gets read as a side plus a stray modifier.

        Retired names (SCR-039) are in here for the same reason: `m-L FX_2 (sw)` was a legal title
        the day it was typed, and it still has to parse into a code and a modifier rather than one
        run-on body.
        """
        codes = (
            self.channel_codes()
            + self.former_codes()
            + list(self.pairs)
            + list(self.combos)
            + list(self.joints)
            + list(self.sides)
        )
        return sorted(set(codes), key=len, reverse=True)

    def as_dict(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "channels": self.channels,
            "pairs": self.pairs,
            "combos": self.combos,
            "joints": self.joints,
            "sides": self.sides,
        }


def generate_name(code, version, method=None, modifier=None, position=None, control=None,
                  params=None):
    """Build a measurement title. `version` is the series number -- an int, its digits, or
    `"final"` -- and None only for `(imp)`, which has no `_N`.

    >>> generate_name("w-L", 2, "sw")
    'w-L_2 (sw)'
    >>> generate_name("ALL+C", "final", "rta")
    'ALL+C_final (rta)'
    >>> generate_name("m-L", 49, "sw", position="p1")
    'm-L p1_49 (sw)'
    >>> generate_name("m-L", 49, "sw", control="ctl1")
    'm-L-ctl1_49 (sw)'
    >>> generate_name("w-L", None, "imp")
    'w-L (imp)'
    >>> generate_name("r-L", 17, "sw", params="noXO")
    'r-L_17 (sw) noXO'
    """
    if not code:
        raise NamingError("a measurement name needs a channel/pair/combo/joint code")
    if method is not None and method not in METHODS:
        raise NamingError(f"unknown method {method!r}; expected one of {', '.join(METHODS)}")
    if version is None:
        if method != METHOD_IMPEDANCE:
            raise NamingError("a sweep or an RTA needs `_N`, the number of the series it belongs "
                              "to; only `(imp)` goes without")
        if control in ("ctl", "rep"):
            raise NamingError(f"control {control!r} is glued to `_N`, and `(imp)` has none")
    elif isinstance(version, bool) or not (str(version).isdigit() or version == "final"):
        # A string interpolated as given built `tw-L_v_001 (sw)`: a plausible list no panel will
        # ever emit, and a capture round opened against it without a word (skill #37).
        raise NamingError(
            f"version {version!r} is not a series number: `_N` is an integer or `final`, and a "
            "ledger version such as `v_001` is a different counter (naming-and-structure.md §3)")
    if position is not None and position not in POSITIONS:
        raise NamingError(f"unknown position {position!r}; expected one of {', '.join(POSITIONS)}")
    if control is not None and control not in CONTROL_OPEN + CONTROL_CLOSE:
        raise NamingError(f"unknown control {control!r}; expected one of "
                          f"{', '.join(CONTROL_OPEN + CONTROL_CLOSE)}")
    body = str(code)
    if control in ("ctl1", "ctl3"):
        body = f"{body}-{control}"
    if modifier:
        body = f"{body} {modifier}"
    if position:
        body = f"{body} {position}"
    name = body if version is None else f"{body}_{version}"
    if control in ("ctl", "rep"):
        name = f"{name}{control}"
    if params and not method:
        raise NamingError("a clarification follows the method, and this title has none")
    name = f"{name} ({method})" if method else name
    return f"{name} {params}" if params else name


def parse_name(title, glossary=None):
    """Split a title into its parts, or return None if it isn't in the grammar.

    Returning None rather than raising is deliberate: REW lists contain things nobody named to
    this convention (imports, room-sim results), and a reader must be able to say "not one of
    ours" without treating it as an error. Where a person reads the verdict, `explain_name` says
    WHY a title is not one.

    With a glossary the code and modifier are separated properly (`L w+m` is a joint, not the side
    `L` with a modifier). Without one, the whole body is reported as the code, since guessing
    where a code ends is exactly the ambiguity the glossary exists to remove.

    This is the grammar's ONE reader. A module that needs the `_N` of a title asks here: a second
    pattern in `process.py` did not know the position typed after the method, and a whole solo set
    (`c_49 (sw) x0`) read as version-unknown there while this function accepted it (skill #34).
    """
    return explain_name(title, glossary)[0]


def explain_name(title, glossary=None):
    """`(parts, None)` for a title in the grammar, `(None, reason)` naming what could not be placed.

    The parts are `parse_name`'s -- same keys, same values. The reason is for the places a person
    reads the verdict (`naming.py parse`, `naming.py check`): a refusal nobody can see is how a
    title's `_N` went missing without a word (skill #34).
    """
    text = str(title or "").strip()
    if not text:
        return None, "an empty title"
    match = _NAME_RE.match(text) or _TAGGED_RE.match(text) or _UNVERSIONED_RE.match(text)
    if not match:
        return None, ("not in the grammar: `<code>_<N> (sw|rta)` or `<code> (imp)`, a clarification "
                      "after the method (naming-and-structure.md §3)")
    parts = match.groupdict()
    method = parts.get("method")
    if method is not None and method.lower() not in METHODS:
        return None, f"`({method})` is not a method: {', '.join(METHODS)}"
    method = method.lower() if method else None
    version = parts.get("version")
    if version is None and method != METHOD_IMPEDANCE:
        return None, (f"no `_N` before `({method})`: a measurement is named for the series it "
                      f"belongs to (`w-L_1 ({method})`), and only `(imp)` goes without")
    body = parts["body"].strip()
    position = parts.get("pos2")
    tail = parts.get("tail")
    if tail:
        found = _POS_WORD_RE.findall(tail)
        if len(found) > 1:
            return None, f"two positions after the method: {', '.join(found)}"
        if found:
            position = found[0]
            tail = _POS_WORD_RE.sub(" ", tail)
        tail = " ".join(tail.split()) or None
    pm = _POS_RE.match(body)
    if pm:
        if position:
            # a position on both sides of the method is not a title, it is a typo
            return None, (f"a position on both sides of the method: `{pm.group('pos')}` and "
                          f"`{position}`")
        body, position = pm.group("code").strip(), pm.group("pos")
    control = parts.get("control")
    cm = _CTL_RE.match(body)
    if cm:
        if control:
            # `m-L-ctl1_49ctl` says two things about one measurement
            return None, f"two controls on one measurement: `-{cm.group('ctl')}` and `{control}`"
        body, control = cm.group("code").strip(), cm.group("ctl")

    code, modifier = body, None
    if glossary:
        for candidate in glossary.all_codes():
            if body == candidate:
                code, modifier = candidate, None
                break
            if body.startswith(candidate + " "):
                code, modifier = candidate, body[len(candidate) + 1 :].strip() or None
                break

    return {
        "code": code,
        # The channel's name TODAY (SCR-039). Equal to `code` for every title but one taken before
        # a rename — `code` stays as typed, because that is what REW shows and what a person
        # looking at the two side by side has to be able to match up.
        "code_current": glossary.resolve_code(code) if glossary else code,
        "modifier": modifier,
        # Where the microphone was (`p1`…`p9` on the ellipsoid, `x0` the tripod point) and whether
        # this is a CONTROL of a series (`ctl1`/`ctl` open it, `ctl3`/`rep` close it) -- both part
        # of the measurement's identity, neither part of the channel's code.
        "position": position,
        "control": control,
        # None only for `(imp)`, which is named for a driver rather than for a series.
        "version": version,
        # Numeric form, so `_01` and `_1` are recognised as the same series number. REW
        # titles are typed by hand and zero-padding is common; comparing raw strings makes a
        # captured measurement look missing, which is the checker crying wolf.
        "version_n": int(version) if version and version.isdigit() else None,
        "method": method,
        # The clarification typed after the method (`noXO`), or None: what the measurement is and
        # what it is for. Part of which measurement it is -- `name_key` counts it with the modifier.
        "params": tail,
        "title": text,
    }, None


def name_key(parsed):
    """Identity of a measurement for comparison: code, modifier, version, method, position, control.
    The clarification typed after the method (`params`) is counted in the modifier's slot, so the
    tuple keeps its shape: `r-L_17 (sw) noXO` is `r-L noXO_17 (sw)`, and neither is `r-L_17 (sw)`.

    **The tuple's SHAPE is part of the contract, and it has changed once.** It was 4 fields
    (code, modifier, version, method) until v3.0.31, and is 6 since — `position` (`p1`…`p9`, `x0`)
    and `control` (`ctl`/`rep`) joined it when the grammar learned them. A caller that BUILDS a key
    by hand and looks it up in a map filled by this function will simply never match: no exception,
    every lookup a miss, and the caller reports "REW does not have this" for measurements that are
    right there. That is exactly what happened downstream in TCC (2026-08-26). Build both sides of
    any comparison through this function.

    Matching on this rather than on the raw title is what makes `c_01 (rta)` and `c_1 (rta)` the
    same measurement, and what lets a checker survive the padding a human happens to type.

    The code used is the channel's current name (SCR-039), so `m-L_2 (sw)` taken before a rename
    and `w-L_2 (sw)` taken after it are ONE measurement: same channel, same series number,
    same method. A rename is a label being corrected, not a reason to re-measure — and a checker
    that disagreed would mark work undone that is already on disk. `parse_name` needs a glossary
    for this; without one the code as typed is all there is, which is the same answer it has always
    given.
    """
    if not parsed:
        return None
    version = parsed.get("version_n")
    if version is None:
        version = parsed.get("version")
    code = parsed.get("code_current") or parsed.get("code")
    modifier = " ".join(part for part in (parsed.get("modifier"), parsed.get("params")) if part) or None
    return (code, modifier, version, parsed.get("method"),
            parsed.get("position"), parsed.get("control"))


# The capture plan of `naming-and-structure.md §3`, as a function rather than a table a human
# re-reads. Each entry is (scope, methods): scope names what to iterate, methods what to take of
# each. Phase 1 analyses `_1` and captures nothing — an empty plan is an answer, not a gap.
_CAPTURE_PLAN = {
    "0": [("channels", (METHOD_SWEEP, METHOD_RTA))],
    "1": [],
    "2": [
        ("channels", (METHOD_SWEEP, METHOD_RTA)),
        ("pairs", (METHOD_RTA,)),
        ("sides", (METHOD_RTA,)),
        ("joints_sw_ws", (METHOD_RTA,)),
    ],
    "3": [
        ("channels", (METHOD_RTA,)),
        ("pairs", (METHOD_RTA,)),
        ("joints_sw_ws", (METHOD_RTA,)),
        ("sides", (METHOD_RTA,)),
        ("combos_all", (METHOD_RTA,)),
    ],
}


def expected_series(phase, glossary, version):
    """Every measurement title a given phase expects at `version`, in capture order.

    Only *active* channels are generated: a disabled centre or an absent rear pair would otherwise
    appear as a task nobody can carry out, which is how a checklist stops being trusted.
    """
    plan = _CAPTURE_PLAN.get(str(phase))
    if not plan:
        return []
    out = []
    for scope, methods in plan:
        for code in _codes_for(scope, glossary):
            for method in methods:
                out.append(generate_name(code, version, method))
    return out


def _codes_for(scope, glossary):
    if scope == "channels":
        return glossary.channel_codes(active_only=True)
    if scope == "pairs":
        return list(glossary.pairs)
    if scope == "sides":
        return list(glossary.sides)
    if scope == "combos_all":
        return [c for c in glossary.combos if c == "ALL"] or list(glossary.combos)[:1]
    if scope == "joints_sw_ws":
        # `SW+Ws` with one sub, `SWs+Ws` with two: the joint whose lower member is the sub or
        # the sub pair. Matching `SW+` alone missed the pair (found 2026-08-24).
        return [j for j in glossary.joints if j.upper().startswith("SW") and "+" in j]
    return []


def validate_series(titles, expected, glossary=None):
    """Compare what REW actually holds against what a phase expects.

    Three buckets, and the third is not a failure: `extra` collects titles that parse as ours but
    weren't asked for (an experiment tag, another version), while `foreign` collects titles that
    aren't in the grammar at all. Flagging both as errors is what makes a checker annoying enough
    to be ignored.
    """
    present = {}
    foreign = []
    for title in titles:
        parsed = parse_name(title, glossary)
        if parsed is None:
            foreign.append(title)
        else:
            present[name_key(parsed)] = parsed

    expected = list(expected)
    wanted = {name_key(parse_name(name, glossary)): name for name in expected}
    missing = [name for key, name in wanted.items() if key not in present]
    extra = [p["title"] for key, p in present.items() if key not in wanted]
    return {
        "expected": expected,
        "found": [name for key, name in wanted.items() if key in present],
        "missing": missing,
        "extra": sorted(extra),
        "foreign": foreign,
        "complete": not missing,
    }


# Human labels for the capture scopes, matching how the plan is read aloud ("solo sweeps, then the
# rta groups") and how a front-end columns them.
_SCOPE_LABELS = {
    "channels": "solo",
    "pairs": "pairs",
    "sides": "sides",
    "joints_sw_ws": "joints",
    "combos_all": "combos",
}


def expected_groups(phase, glossary, version):
    """`expected_series` split into the groups a checklist is actually read in.

    Returns `[{"scope", "label", "method", "names"}]`. A flat list is right for set comparison and
    wrong for display: "10 of 20 captured" tells a tuner nothing about whether the solo pass is
    done or the group pass hasn't started.
    """
    plan = _CAPTURE_PLAN.get(str(phase))
    if not plan:
        return []
    out = []
    for scope, methods in plan:
        codes = _codes_for(scope, glossary)
        if not codes:
            continue
        for method in methods:
            out.append(
                {
                    "scope": scope,
                    "label": f"{_SCOPE_LABELS.get(scope, scope)} ({method})",
                    "method": method,
                    "names": [generate_name(code, version, method) for code in codes],
                }
            )
    return out


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: naming.py <project-dir> <command> [args]

  codes                          list the glossary's codes (inactive channels marked)
  name <code> <version> [method] build one title
  parse <title>                  split a title into code/modifier/version/method, or say why not
  expect <phase> <version>       the capture series a phase expects
  check <phase> <version>        compare that series against what REW currently holds
  selftest                       run this module's own checks (no project needed)
"""


def _selftest():
    """The grammar's own checks, and SCR-039's: a renamed channel keeps its captures.

    Run as `python3 naming.py . selftest` — the project argument is ignored, since nothing here
    touches disk.
    """
    assert generate_name("w-L", 2, "sw") == "w-L_2 (sw)"
    assert generate_name("ALL+C", "final", "rta") == "ALL+C_final (rta)"

    plain = Glossary({"channels": [{"code": "w-L", "active": True}]})
    assert parse_name("w-L_2 (sw)", plain)["code"] == "w-L"
    assert parse_name("not a measurement") is None
    # `_01` and `_1` are the same series number -- a human types the padding, not the tool.
    assert name_key(parse_name("c_01 (rta)", plain)) == name_key(parse_name("c_1 (rta)", plain))

    # -- SCR-039: `m-L` was renamed to `w-L`; its captures still say `m-L` and always will.
    g = Glossary({"channels": [
        {"code": "w-L", "active": True, "previous_names": ["m-L"]},
        {"code": "tw-L", "active": True},
    ]})
    assert g.resolve_code("m-L") == "w-L"
    assert g.resolve_code("w-L") == "w-L"
    assert g.resolve_code("sub") == "sub", "an unknown code is not ours to reinterpret"
    assert g.former_codes() == ["m-L"], g.former_codes()
    assert "m-L" in g.all_codes(), "an old title still has to parse into code + modifier"
    assert g.is_active("m-L") is True, "activity is the channel's, whatever it is called"

    # -- Two subwoofers (2026-08-24): `sw-f`/`sw-r` are channels, `SWs` their pair, `SWs+Ws` the
    #    joint the phase-2/3 plans read -- and it is all glossary DATA, so the grammar needs nothing
    #    new; this pins that the plan generator sees it through the same scopes as one sub.
    two = Glossary({"channels": [{"code": "sw-f"}, {"code": "sw-r"}, {"code": "w-L"}, {"code": "w-R"}],
                    "pairs": {"SWs": ["sw-f", "sw-r"], "Ws": ["w-L", "w-R"]},
                    "joints": {"SWs+Ws": ["SWs", "Ws"]}})
    s2 = expected_series("2", two, 2)
    assert "SWs_2 (rta)" in s2 and "SWs+Ws_2 (rta)" in s2 and "sw-f_2 (sw)" in s2, s2
    assert parse_name("SWs+Ws_2 (rta)", two)["code"] == "SWs+Ws"

    old = parse_name("m-L_2 (sw)", g)
    assert old["code"] == "m-L", "the title says what REW shows, unedited"
    assert old["code_current"] == "w-L", old
    assert name_key(old) == name_key(parse_name("w-L_2 (sw)", g)), \
        "one channel, one series, one method -- a rename does not make it two measurements"
    # the modifier still splits off an old code, which is why former names are in `all_codes`.
    assert parse_name("m-L FX_2 (sw)", g)["modifier"] == "FX"
    # without a glossary there is no history to consult, and the answer is what it always was.
    assert parse_name("m-L_2 (sw)")["code_current"] == "m-L"

    # the checker: a capture taken under the old name is FOUND, not missing. Getting this wrong
    # means telling a tuner to re-measure something already sitting in REW.
    verdict = validate_series(["m-L_2 (sw)", "tw-L_2 (sw)"],
                              ["w-L_2 (sw)", "tw-L_2 (sw)"], g)
    assert verdict["missing"] == [], verdict
    assert verdict["complete"], verdict
    # and a plan is never generated under a retired name.
    assert "m-L" not in expected_series("0", g, 2)[0], expected_series("0", g, 2)

    # -- Positions and controls (2026-08-26): the ellipsoid's `p1`…`p9`, the tripod's `x0`, and
    #    the control repeats -- both forms each, none of them part of the code.
    e1 = parse_name("m-L p1_49 (sw)", plain)
    assert (e1["code"], e1["position"], e1["version_n"], e1["method"]) == ("m-L", "p1", 49, "sw"), e1
    x0 = parse_name("w-L_49 (sw) x0")
    assert (x0["code"], x0["position"], x0["control"]) == ("w-L", "x0", None), x0
    assert name_key(parse_name("m-L p1_49 (sw)")) != name_key(parse_name("m-L p2_49 (sw)")), \
        "two positions of one driver are two measurements"
    assert name_key(parse_name("m-L p1_49 (sw)")) != name_key(parse_name("m-L_49 (sw)"))
    c1 = parse_name("m-L-ctl1_49 (sw)")
    assert (c1["code"], c1["control"], c1["position"]) == ("m-L", "ctl1", None), c1
    c2 = parse_name("m-L_49ctl (sw) x0")
    assert (c2["code"], c2["control"], c2["position"], c2["version_n"]) == ("m-L", "ctl", "x0", 49), c2
    c3 = parse_name("m-L_49rep (sw)")
    assert c3["control"] == "rep" and c3["control"] in CONTROL_CLOSE and c1["control"] in CONTROL_OPEN
    assert name_key(c1) != name_key(parse_name("m-L_49 (sw)")), "a control is not the solo"
    assert parse_name("m-L p1_49 (sw) x0") is None and parse_name("m-L-ctl1_49ctl (sw)") is None
    for title in ("m-L p1_49 (sw)", "m-L-ctl1_49 (sw)", "m-L_49rep (sw)", "w-L x0_49 (sw)"):
        pp = parse_name(title)
        assert generate_name(pp["code"], pp["version"], pp["method"], pp["modifier"],
                             position=pp["position"], control=pp["control"]) == title, (title, pp)
    assert parse_name("m-L FX p3_49 (sw)", g)["modifier"] == "FX", "a modifier and a position coexist"

    # -- skill #34, and the user 2026-09-16: a clarification typed after the method. "The
    #    measurement is always another one; the series is the same." The titles are the issue's
    #    own, from a live REW session; each used to be refused here or to lose its `_N` in
    #    `process.py`.
    car = Glossary({"channels": [{"code": c} for c in ("c", "m-L", "r-L")]})
    for title in ("c_49 (sw) x0", "m-L_49 (sw) x0"):
        p = parse_name(title, car)
        assert (p["version"], p["position"], p["modifier"], p["params"]) == ("49", "x0", None, None), p
    rear = parse_name("r-L_17 (sw) noXO", car)
    assert (rear["code"], rear["modifier"], rear["version_n"], rear["method"], rear["position"],
            rear["params"]) == ("r-L", None, 17, "sw", None, "noXO"), rear
    plain_rear = parse_name("r-L_17 (sw)", car)
    assert name_key(rear) != name_key(plain_rear) and rear["version"] == plain_rear["version"], \
        "another measurement, the same series"
    assert name_key(parse_name("r-L noXO_17 (sw)", car)) == name_key(rear), \
        "typed after the method or before `_N`, one measurement"
    spaced = parse_name("m-L_49 (sw) noXO  mic 2cm x0", car)
    assert (spaced["params"], spaced["position"]) == ("noXO mic 2cm", "x0"), spaced
    assert name_key(spaced) != name_key(parse_name("m-L_49 (sw) x0", car)), "the clarification is identity"
    assert parse_name("m-L_49 (sw) (mic at 2cm)", car)["params"] == "(mic at 2cm)"
    for title in ("r-L_17 (sw) noXO", "m-L_49ctl (sw) again", "m-L p3_49 (sw) 2nd try"):
        p = parse_name(title, car)
        again = generate_name(p["code"], p["version"], p["method"], p["modifier"],
                              position=p["position"], control=p["control"], params=p["params"])
        assert again == title, (title, again)
    # -- skill #33: an impedance sweep, the seven titles of the issue verbatim. No `_N`.
    seven = ["sw2 (imp) case35l, NO cotton wool", "w-L (imp)", "w-R (imp)", "m-L (imp)",
             "m-R (imp)", "tw-L (imp)", "tw-R (imp)"]
    for title in seven:
        p, why = explain_name(title)
        assert p and (p["method"], p["version"], p["version_n"]) == ("imp", None, None), (title, why)
    box = parse_name(seven[0])
    assert (box["code"], box["modifier"], box["params"]) == ("sw2", None, "case35l, NO cotton wool"), box
    assert generate_name("w-L", None, "imp") == "w-L (imp)"
    assert name_key(parse_name("w-L_1 (imp)")) != name_key(parse_name("w-L (imp)")) != \
        name_key(parse_name("w-L_1 (sw)"))
    # -- a refusal says what it could not place, and every title that parsed before still does.
    for title, words in (("w-L (sw)", "no `_N`"), ("w-L_1 (foo)", "not a method"),
                         ("m-L p1_49 (sw) x0", "both sides"), ("m-L-ctl1_49ctl (sw)", "two controls"),
                         ("m-L_49 (sw) x0 p3", "two positions"), ("Room sim", "not in the grammar"),
                         ("", "empty")):
        p, why = explain_name(title)
        assert p is None and words in why, (title, why)
    # -- skill #37: a ledger version is not `_N`. It is refused, not interpolated into a list of
    #    titles no panel will ever emit.
    for bad in ("v_001", None, True, -1):
        try:
            generate_name("tw-L", bad, "sw")
        except NamingError:
            continue
        raise AssertionError(f"generate_name took {bad!r} for `_N`")
    try:
        expected_groups("0", plain, "v_001")
    except NamingError:
        pass
    else:
        raise AssertionError("expected_groups built titles from a ledger version")
    assert expected_groups("0", plain, "01")[0]["names"] == ["w-L_01 (sw)"]

    print("selftest OK — grammar round-trips, padding-insensitive version match, and a renamed "
          "channel's old captures resolve to it (SCR-039); positions p1..p9/x0 and controls "
          "ctl1/ctl3/ctl/rep parse in both forms and are identity, not code; a clarification "
          "after the method is another measurement in the same series (#34), (imp) without `_N` (#33), refusals "
          "with a reason, and no ledger version for `_N` (#37)")
    return 0


def _main(argv):
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    project, cmd, args = argv[1], argv[2], argv[3:]
    if cmd == "selftest":
        return _selftest()
    g = Glossary.for_project(project)
    try:
        if cmd == "codes":
            for c in g.channels:
                flag = "" if c.get("active", True) else "   [inactive]"
                print(f"  {c.get('code')}{flag}")
            for kind in ("pairs", "combos", "joints", "sides"):
                values = getattr(g, kind)
                if values:
                    print(f"  {kind}: {', '.join(values)}")
        elif cmd == "name":
            print(generate_name(args[0], args[1], args[2] if len(args) > 2 else None))
        elif cmd == "parse":
            parsed, why = explain_name(args[0], g)
            print(json.dumps(parsed, ensure_ascii=False) if parsed else f"not a measurement name: {why}")
            return 0 if parsed else 1
        elif cmd == "expect":
            for name in expected_series(args[0], g, args[1]):
                print(name)
        elif cmd == "check":
            import rew_api

            titles = [m.get("title", "") for m in rew_api.get_measurements().values()]
            verdict = validate_series(titles, expected_series(args[0], g, args[1]), g)
            for name in verdict["found"]:
                print(f"  ok      {name}")
            for name in verdict["missing"]:
                print(f"  MISSING {name}")
            for name in verdict["extra"]:
                print(f"  extra   {name}")
            for name in verdict["foreign"]:
                # Not an error, but the one a tuner most needs to see: a title REW holds that
                # isn't in the convention at all, so no analysis will ever find it by name -- and
                # what in it could not be placed, so the fix is one rename rather than a hunt.
                print(f"  ?name   {name}  -- {explain_name(name, g)[1]}")
            print(f"{len(verdict['found'])}/{len(verdict['expected'])} captured")
            return 0 if verdict["complete"] else 1
        else:
            print(_USAGE, file=sys.stderr)
            return 2
    except (NamingError, IndexError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(_main(sys.argv))
