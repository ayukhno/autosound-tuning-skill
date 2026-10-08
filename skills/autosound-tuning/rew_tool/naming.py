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
* **One notation for codes**: written with `-` (`w-L`). A driver's side typed with `_` (`w_L_3 (sw)`,
  a file `w_L.json`) is read as `-`, and the parse says so in its `note` (S-079): `canonical_title`,
  `canonical_code`. Any other `_` in a code is refused -- the old configuration prefix `D_L_7 (rta)`
  among them, which is not a channel `D-L` (hub #232).
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


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.realpath(__file__))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


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


# S-079 (the Arbiter, 2026-10-01: «розуміти обидві назви. правільна "-"»): a code is WRITTEN with `-`, and a driver's
# side met with `_` -- a capture typed `w_L_3 (sw)`, a file `w_L.json`, a project id `w_L` -- is READ as `-`. `_` stays
# the series separator (`sw_1`, `ALL+C_25`), so the rule touches the code and never the `_N` after it. These two
# functions are its one home: until now each module that met a `w_L` turned it into `w-L` on its own (skill #81).
#
# Only a driver's side (hub #232 TCC-044, the Arbiter 2026-10-01: «це правило до драйвер-L/R і все»): a lowercase
# driver, `_`, then `L` or `R` as a whole token. v3.0.65 read every `_` in a code, and the old configuration prefix
# `D_L_7 (rta)` became a channel `D-L` the car does not have.
_FIRST_WORD_RE = re.compile(r"^\s*\S+")
_SIDE_UNDERSCORE_RE = re.compile(r"(?<![A-Za-z0-9])([a-z][a-z0-9]*)_([LR])(?![A-Za-z0-9])")
# The old configuration prefix (`D_L_7 (rta)`, `D_SW+Ws_9 (rta)`): one capital letter and `_` at the front of a code.
# The Arbiter, 2026-09-29: «наші префікси були помилкою» -- the letter now goes in front of the series number (`L_D7`).
_CONFIG_PREFIX_RE = re.compile(r"^(?P<letter>[A-Z])_(?=\S)")


def canonical_code(code):
    """A code in the one notation: `w_L` -> `w-L`, `m_L-ctl1` -> `m-L-ctl1` (S-079). None stays None.

    For a name that carries no series: a channel code or id, a ledger key, a capture file's stem (`w_L` of
    `irs_48/w_L.json`). Only a driver's side is read (hub #232): `sw_1`, `D_L` and `sw_f` keep their `_`. Only the
    first word is the code's: a modifier after it keeps what it was typed with (`w-L low_cut`). A TITLE carries a
    series; it goes through `canonical_title`, which splits the series off first.
    """
    if code is None:
        return None
    return _FIRST_WORD_RE.sub(lambda m: _SIDE_UNDERSCORE_RE.sub(r"\1-\2", m.group(0)), str(code), count=1)


def canonical_title(title):
    """A measurement title with its code in the one notation: `w_L_3 (sw)` -> `w-L_3 (sw)` (S-079).

    The series is split off where the grammar splits it -- the LAST `_` before `<N>` or `final` -- and only what is
    in front of it goes through `canonical_code`: `sw_1`, `w-L_2` and `ALL+C_25` come back as they are, `w_L (imp)`
    is `w-L (imp)`. A text with no series and no method is a bare name, read whole: `w_L` is `w-L`.
    """
    text = str(title or "")
    match = _NAME_RE.match(text) or _TAGGED_RE.match(text) or _UNVERSIONED_RE.match(text)
    end = match.end("body") if match else len(text)
    return canonical_code(text[:end]) + text[end:]


# A junction written side first with a sign between its members (skill #66, the Arbiter 2026-09-24): `L m-tw`,
# `L w-m+tw`. The member after `-` is inverted. Lowercase members only: the combos (`ALL+C`) are uppercase and keep
# their `+`, and a driver's own side (`m-L`) never follows a space.
_SIGNED_CHAIN_RE = re.compile(
    r"^(?P<side>\S+)\s+(?P<chain>[a-z][a-z0-9]*(?:[+-][a-z][a-z0-9]*)+)(?P<rest>(?:\s.*)?)$")


def _signed_chain(body, glossary):
    """`(body with every sign a plus, [inverted members])` -- or `(body, [])` when it is not a signed junction.

    Only with a glossary, and only when the side is one of its sides and every member is a driver it has
    (`m` of `m-L`, `sw`): a variant spelled `w-alt` is left alone rather than read as `w` plus an inverted `alt`.
    """
    m = _SIGNED_CHAIN_RE.match(body)
    if not glossary or not m or "-" not in m.group("chain") or m.group("side") not in glossary.sides:
        return body, []
    drivers = {code.split("-")[0] for code in glossary.channel_codes() + glossary.former_codes()}
    members = re.split(r"[+-]", m.group("chain"))
    if not all(member in drivers for member in members):
        return body, []
    signs = re.findall(r"[+-]", m.group("chain"))
    inverted = [member for sign, member in zip(signs, members[1:]) if sign == "-"]
    return f"{m.group('side')} {'+'.join(members)}{m.group('rest')}", inverted


class NamingError(ValueError):
    """A title that cannot be expressed in, or parsed from, the grammar."""


def read_glossary_file(path, project_dir):
    """A standalone `glossary.json` as the method's own readers read it (`Glossary.for_project(..., strict=True)`) and as
    `contract.py check` does: its JSON object, or None when there is no such file.

    One that is there and cannot be read -- empty, cut off, not UTF-8, not JSON, not an object, held, a folder in its
    place -- or that a newer method wrote raises `project_io.Unreadable` (`is_unreadable` on its class), naming it, the
    reason and the repair. So does a link to nothing (#134, batch 4's third re-review, N-M2): `read_json` reads a link
    whose target is gone as no file, and the strict read said "no glossary" where the lenient one, which looks past the
    link, read `project.json`'s -- and `capture-start --plan` said it "needs the project's glossary" over one."""
    io_ = _siblings().load("project_io.py")
    own = io_.read_json(path, None, repair=io_.restore_line(path), repair_encoding=io_.reencode_line(project_dir))
    if own is None:
        if os.path.islink(path):
            try:
                target = os.readlink(path)
            except OSError:
                target = "its target"
            raise io_.Unreadable(path, f"is a link to {target}, which is not there",
                                 f"restore {target}, or point the link at the glossary -- or remove the link, and the "
                                 f"glossary project.json keeps is read")
        return None
    newer = io_.newer_schema(own, SCHEMA_VERSION)
    if newer is not None:
        raise io_.Unreadable(path, f"is schema v{newer}; this method reads v{SCHEMA_VERSION}", io_.UPDATE_THE_METHOD)
    return own


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
        naming still parses, it just cannot check codes against anything.

        A UTF-8 BOM is read, as `project_io.read_json` reads it (#134, batch 4's re-review, Out of Scope 1): older
        Windows Notepad saves one, and a valid glossary read as none."""
        try:
            with open(path, encoding="utf-8-sig") as f:
                return cls(json.load(f))
        except (OSError, ValueError):
            return cls()

    @classmethod
    def for_project(cls, project_dir, strict=False):
        """`<project>/glossary.json`, or the `glossary` key of `project.json` (SCR-011).

        **Whether a channel is active comes from the project's channel rows** (skill #83): `channels[]` in
        `project.json` is where the intake's slot switch writes `hidden` / role `unused`, and the glossary's own
        `active` flag stayed true for `r-L`/`r-R` after they were switched off, so the plan asked for captures of
        channels the car no longer had. A code the project has no row for keeps the glossary's flag.

        Read leniently by default -- a file that cannot be read is no glossary -- the read of a screen, which contract
        1 keeps for TCC. `strict` is the method's own readers' (#134, batch 4's re-review, Out of Scope 6): a
        `glossary.json` or a `project.json` that is there and cannot be read -- cut off, not UTF-8, not JSON, not an
        object, held, a folder in its place, or a glossary a newer method wrote -- raises `project_io.Unreadable`
        (`is_unreadable` on its class), naming the file, the reason and the repair, as `contract.py check` reads them;
        so does a `glossary.json` that is a link to nothing (`read_glossary_file`), which the default reads past, to
        `project.json`'s. Read as none, `capture-start --plan` said it "needs the project's glossary" over a glossary
        cut off.
        """
        standalone = os.path.join(project_dir, "glossary.json")
        combined = os.path.join(project_dir, "project.json")
        if strict:
            io_ = _siblings().load("project_io.py")
            data = io_.read_json(combined, {}, repair=io_.restore_line(combined),
                                 repair_encoding=io_.reencode_line(project_dir))
            own = read_glossary_file(standalone, project_dir) if os.path.lexists(standalone) else None
            glossary = cls(own) if own is not None else cls(data.get("glossary") or {})
        else:
            try:
                with open(combined, encoding="utf-8-sig") as f:
                    data = json.load(f) or {}
            except (OSError, ValueError):
                data = {}
            glossary = cls.load(standalone) if os.path.isfile(standalone) else cls(data.get("glossary") or {})
        glossary.follow_project_channels(data.get("channels") or [])
        return glossary

    def follow_project_channels(self, rows):
        """Set each channel's `active` from the project's row of the same code, where there is one (skill #83)."""
        on = {}
        for row in rows or []:
            if isinstance(row, dict) and row.get("code"):
                on[canonical_code(row["code"])] = not row.get("hidden") and row.get("role") != "unused"
        for c in self.channels:
            if canonical_code(c.get("code")) in on:
                c["active"] = on[canonical_code(c["code"])]

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

        Both notations are one name (S-079): `w_L` finds the channel `w-L`, and the answer is the
        glossary's own spelling of it.
        """
        if not code:
            return code
        for c in self.channels:
            if c.get("code") == code:
                return code
        key = canonical_code(code)
        for c in self.channels:
            if c.get("code") and canonical_code(c["code"]) == key:
                return c["code"]
        for c in self.channels:
            if c.get("code") and key in [canonical_code(n) for n in (c.get("previous_names") or [])]:
                return c["code"]
        return code

    def former_codes(self):
        """Every name that is no longer any channel's current one (SCR-039).

        Parsing fodder only: these are never generated into a capture plan (that would ask for a
        measurement under a name the project has retired), but a title already in REW carries one,
        and `parse_name` has to be able to split it off the modifier.

        A previous name that is a live code in the other notation (`w_L` beside `w-L`) is not
        retired: it is the same name (S-079).
        """
        live = {canonical_code(c.get("code")) for c in self.channels}
        return [
            str(old)
            for c in self.channels
            for old in (c.get("previous_names") or [])
            if str(old) and canonical_code(str(old)) not in live
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

    head = body.split()[0] if body.split() else body
    note = None
    if "_" in canonical_code(head):
        # S-042: `_` only begins the series. A driver's side is the one `_` read as `-` (hub #232); any other is
        # refused, as it was until v3.0.65, and the old configuration prefix says what it was.
        prefix = _CONFIG_PREFIX_RE.match(text)
        if prefix:
            letter = prefix.group("letter")
            rest = text[prefix.end():]
            if version is None:
                where = f"an impedance sweep is not tied to a configuration: `{rest}`"
            else:
                at = match.start("version") - prefix.end()
                where = f"the letter goes in front of the series number: `{rest[:at]}{letter}{rest[at:]}`"
            return None, (f"`{letter}_` is an old configuration prefix, not part of a code -- {where}, a form this "
                          f"grammar does not read either (naming-and-structure.md §3)")
        return None, (f"`{head}`: a code has no `_` -- `_` only begins the series number, and the one `_` read as "
                      f"`-` is a driver's side (`w_L` is `w-L`) (naming-and-structure.md §3)")
    if canonical_code(head) != head:
        # S-079 (the Arbiter, 2026-10-01): both notations are read, and the hyphen is the one written. From S-042
        # until then `w_L_1 (sw)` was refused here; it is read as `w-L_1 (sw)`, and the note says so, so a session
        # sees which code the title went to and what to rename it to. The reason slot stays None: a reader takes a
        # reason as a refusal.
        body = canonical_code(body)
        note = (f"`{head}` read as `{canonical_code(head)}`: a code is written with `-`, and `_` only begins the "
                f"series number -- this title in the one notation is `{canonical_title(text)}` "
                f"(naming-and-structure.md §3)")
    # `L m-tw` is `L m+tw` with the tweeter inverted -- the same measurement as `L m+tw_52 (rta) inv`, so the
    # inversion joins the clarification the way `inv` typed after the method does: `inv` for a two-member
    # junction, `inv:<member>` where a longer chain has to say which (skill #66).
    body, inverted = _signed_chain(body, glossary)
    if inverted:
        mark = "inv" if len(re.split(r"[+-]", body.split()[1])) == 2 else "inv:" + ",".join(inverted)
        tail = f"{mark} {tail}" if tail else mark
    code, modifier = body, None
    if glossary:
        for candidate in glossary.all_codes():
            candidate = canonical_code(candidate)     # a glossary written in the other notation (S-079)
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
        # The junction members typed after a `-` (`L m-tw` -> `["tw"]`): inverted for this take (skill #66).
        "inverted": inverted,
        "title": text,
        # None, or what the reader did to the title on the way in: a code typed with `_` read as `-` (S-079).
        # `code` is then the hyphen form and `title` stays what REW shows.
        "note": note,
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

    **A match whose TITLE differs is its own outcome, not a plain `ok`** (skill `#47`). The
    comparison runs on `name_key`, so `sw_01 (sw)` and `sw_1 (sw)` are the same measurement —
    arithmetically right, and the normalisation is wanted. The silence was the bug: `found`
    returned the EXPECTED name, and a front-end that has to FIND the measurement by its literal
    REW title then answered `0 usable, 16 missing` over the same session this check had just
    called `ok` on all 16. A wrong statement reached the tuner as fact and sixteen good
    measurements were registered as unusable.

    So the verdict now also carries:

    * `matched` — `{expected name: the title REW actually holds}`, for every found measurement;
    * `renames` — `{title on disk: canonical title}` for the subset where the two differ. The
      canonical form is whatever `generate_name` emits (one digit: `sw_1 (sw)`), and the fix is a
      RENAME, never a re-measurement: REW's `uuid` survives a rename, one measurement carried
      three titles in a session and kept the same id. This is the "new name" column a front-end's
      read-from-REW step fills in.
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
    matched = {name: present[key]["title"] for key, name in wanted.items() if key in present}
    renames = {actual: name for name, actual in matched.items() if actual != name}
    return {
        "expected": expected,
        "found": [name for key, name in wanted.items() if key in present],
        "matched": matched,
        "renames": renames,
        "missing": missing,
        "extra": sorted(extra),
        "foreign": foreign,
        "complete": not missing,
    }


# A round's columns (skill #79, the Arbiter 2026-09-24): what a capture is MADE OF -- one driver (solo) or several
# together (group) -- by how it is taken (sw / rta). Four at most: Solo (sw), Solo (rta), Group (sw), Group (rta).
# Pairs, sides, joints and combos are all groups; splitting them by what they are in the analysis gave five columns
# nobody in the car needed.
KIND_SOLO = "solo"
KIND_GROUP = "group"
_KIND_LABELS = {KIND_SOLO: "Solo", KIND_GROUP: "Group"}


def group_label(kind, method):
    return f"{_KIND_LABELS.get(kind, kind)} ({method})"


def expected_groups(phase, glossary, version):
    """`expected_series` split into the groups a checklist is actually read in: the four columns of skill #79.

    Returns `[{"kind", "label", "method", "names"}]`, in the plan's order (solo before group, sw before rta) -- a
    flat list is right for set comparison and wrong for display: "10 of 20 captured" tells a tuner nothing about
    whether the solo pass is done or the group pass hasn't started. `order_by_setup` reorders it for the car.
    """
    plan = _CAPTURE_PLAN.get(str(phase))
    if not plan:
        return []
    out = []
    for scope, methods in plan:
        codes = _codes_for(scope, glossary)
        if not codes:
            continue
        kind = KIND_SOLO if scope == "channels" else KIND_GROUP
        for method in methods:
            names = [generate_name(code, version, method) for code in codes]
            group = next((g for g in out if g["kind"] == kind and g["method"] == method), None)
            if group is None:
                out.append({"kind": kind, "label": group_label(kind, method), "method": method, "names": names})
            else:
                group["names"].extend(n for n in names if n not in group["names"])
    return out


def order_by_setup(groups, first):
    """The round's groups in the order the car is taken in (skill #78, the Arbiter's rule from the seat).

    A sweep is the mic on the tripod, the driver out of the seat; an RTA is the driver in the seat with the mic in
    hand. Every change of method is the tripod going in or out, so the list takes `first` -- the method the car is
    set up for, normally the last one captured -- in full, then switches ONCE and takes the rest. With `first`
    unknown the plan's order stands. Stable: within a method the plan's order (solo, then group) is kept.
    """
    if not first:
        return list(groups)
    return [g for g in groups if g.get("method") == first] + [g for g in groups if g.get("method") != first]


def method_switches(methods):
    """How many times the setup changes along a list of methods: the number a round's order keeps at one."""
    return sum(1 for a, b in zip(methods, methods[1:]) if a != b)


def place_in_groups(groups, titles, glossary):
    """`groups` with each of `titles` added in its place (skill #80): a solo with the solos of its method, a group
    capture with the groups, and a method the round has no column for as a new one at the end. A title already
    listed is not listed twice; one the grammar refuses is put in a group of its own so that it is still ON the
    list and visibly odd. Used for the titles typed beside `--plan`, for "if you have time" captures and for a round
    opened without a plan at all -- so every round carries its columns (skill #83)."""
    out = [dict(g, names=list(g.get("names") or [])) for g in groups]
    listed = {n for g in out for n in g["names"]}
    solos = set(glossary.channel_codes()) | set(glossary.former_codes()) if glossary else set()
    for title in titles:
        title = str(title).strip()
        if not title or title in listed:
            continue
        parsed = parse_name(title, glossary)
        if parsed and parsed.get("method"):
            kind = KIND_SOLO if (parsed.get("code_current") or parsed.get("code")) in solos else KIND_GROUP
            method = parsed["method"]
        else:
            kind, method = "other", "?"
        group = next((g for g in out if g.get("kind") == kind and g.get("method") == method), None)
        if group is None:
            group = {"kind": kind, "label": group_label(kind, method) if kind != "other" else "Not in the grammar",
                     "method": method, "names": []}
            out.append(group)
        group["names"].append(title)
        listed.add(title)
    return out


def flatten_groups(groups):
    """The round's list as `expected` holds it: every group's names, in the groups' order."""
    return [n for g in groups for n in (g.get("names") or [])]


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: naming.py <project-dir> <command> [args]

  codes                          list the glossary's codes (inactive channels marked)
  name <code> <version> [method] build one title
  parse <title>                  split a title into code/modifier/version/method, or say why not
  expect <phase> <version>       the capture series a phase expects
  next-series                    this project's next series number, from its own rounds (#56 item 10)
  check <phase> <version>        compare that series against what REW currently holds
  selftest                       run this module's own checks (no project needed)
"""


def _check_productions():
    """One title per production of the grammar at the top of this file, and the parts nothing else here asserts
    (`p4`…`p9`, `-ctl3`, `_final`) -- by value."""
    cases = {
        "w-L_3 (sw)":       {"code": "w-L", "version_n": 3, "method": "sw", "position": None, "control": None},
        "m-L p9_49 (sw)":   {"code": "m-L", "position": "p9", "version_n": 49},
        "w-L_49 (sw) p5":   {"code": "w-L", "position": "p5", "version_n": 49},
        "m-L-ctl3_49 (sw)": {"code": "m-L", "control": "ctl3", "version_n": 49},
        "sw_final (rta)":   {"code": "sw", "version": "final", "method": "rta"},
        "r-L_17 (sw) noXO": {"code": "r-L", "version_n": 17, "method": "sw"},
        "w-L (imp)":        {"code": "w-L", "method": "imp"},
    }
    for title, want in cases.items():
        got = parse_name(title)
        assert got is not None, f"{title!r} is in the documented grammar and parses to None"
        for key, value in want.items():
            assert got.get(key) == value, (title, key, got.get(key), value)
    # ...and the role the grammar gives each control: `ctl1`/`ctl` open a series, `ctl3`/`rep` close it. The parse
    # never reads these tuples (`_CTL_RE` takes any `ctl<digit>`), so `ctl3` dropped from `CONTROL_CLOSE` stayed
    # green above, while `verify.py` finds a series' closing control by that tuple.
    for title, role in (("m-L-ctl1_49 (sw)", CONTROL_OPEN), ("m-L_49ctl (sw)", CONTROL_OPEN),
                        ("m-L-ctl3_49 (sw)", CONTROL_CLOSE), ("m-L_49rep (sw)", CONTROL_CLOSE)):
        got = parse_name(title)
        assert got is not None, f"{title!r} is in the documented grammar and parses to None"
        assert got["control"] in role, (title, got["control"], role)


def _check_bom_glossary_read():
    """A `glossary.json` saved with a UTF-8 BOM -- older Windows Notepad saves so -- is a glossary (#134, batch 4's
    re-review, Out of Scope 1). `Glossary.load` opened it as `utf-8`, the BOM failed the JSON, and it read as no
    glossary: "no glossary yet" over a valid file, the intake gate shut, every name check inert. `project_io.read_json`
    reads a BOM as the editor's marker it is; so does every read here, `project.json`'s own included."""
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="autosound_naming_bom_")
    try:
        body = {"schema_version": 1, "channels": [{"code": "w-L", "active": True}, {"code": "m-L", "active": True}]}
        bom = b"\xef\xbb\xbf"
        path = os.path.join(d, "glossary.json")
        with open(path, "wb") as fh:
            fh.write(bom + json.dumps(body).encode("utf-8"))
        failures = []
        for label, got in (("Glossary.load", Glossary.load(path)), ("Glossary.for_project", Glossary.for_project(d))):
            if got.channel_codes() != ["w-L", "m-L"]:
                failures.append(f"{label} over a BOM'd glossary.json: {got.channel_codes()}")
        os.remove(path)
        with open(os.path.join(d, "project.json"), "wb") as fh:          # the glossary inside project.json, BOM'd
            fh.write(bom + json.dumps({"channels": [{"code": "m-L", "hidden": True}], "glossary": body}).encode())
        got = Glossary.for_project(d)
        if got.channel_codes() != ["w-L", "m-L"] or got.is_active("m-L") is not False:
            failures.append(f"Glossary.for_project over a BOM'd project.json: {got.channel_codes()}, "
                            f"m-L active {got.is_active('m-L')}")
        assert not failures, "; ".join(failures)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _check_for_project_strict():
    """`Glossary.for_project(project_dir, strict=True)` -- the method's own readers' -- refuses a file it cannot read
    (#134, batch 4's re-review, Out of Scope 6): a `glossary.json` or a `project.json` that is there and cannot be read
    raises `project_io.Unreadable` (`is_unreadable` on its class), naming the file, the reason and the repair, as
    `contract.py check` reads it. Read leniently, as no glossary, `capture-start --plan` said it "needs the project's
    glossary" over one cut after phase 0 was entered. The default stays lenient, a screen's read (contract 1: TCC calls
    `for_project(project_dir)`), and over a whole project both reads are one glossary."""
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="autosound_naming_strict_")
    try:
        body = {"schema_version": 1, "channels": [{"code": "w-L", "active": True, "label": "Низ ліво"}]}
        whole = json.dumps(body, ensure_ascii=False).encode("utf-8")
        gloss, proj = os.path.join(d, "glossary.json"), os.path.join(d, "project.json")
        with open(proj, "w", encoding="utf-8") as fh:
            json.dump({"channels": [{"code": "w-L"}], "glossary": body}, fh)
        failures = []

        def refused(label, path, why, repair):
            try:
                got = Glossary.for_project(d, strict=True)
            except Exception as exc:  # noqa: BLE001 -- the refusal is under test; matched by its type's attribute
                said = str(exc)
                if not getattr(type(exc), "is_unreadable", False) or not said.startswith(f"{path} ") \
                        or why not in said or repair not in said:
                    failures.append(f"{label}: raised {type(exc).__name__}: {said}")
            else:
                failures.append(f"{label}: read as {got.channel_codes()}")
            try:
                Glossary.for_project(d)
            except Exception as exc:  # noqa: BLE001 -- the default must not raise
                failures.append(f"{label}: the default raised {type(exc).__name__}: {exc}")
        for label, raw, why, repair in (
                ("cut inside a character", whole[: whole.index("ліво".encode("utf-8")) + 1],
                 "is cut off inside a character", "checkout HEAD -- glossary.json"),
                ("cut at an ASCII byte", whole[: whole.index(b'"channels"') + 4], "is not valid JSON",
                 "checkout HEAD -- glossary.json"),
                ("an array", b"[]", "holds an array where an object belongs", "checkout HEAD -- glossary.json"),
                ("a newer method's", json.dumps({"schema_version": SCHEMA_VERSION + 1}).encode(),
                 f"is schema v{SCHEMA_VERSION + 1}; this method reads v{SCHEMA_VERSION}", "update the method")):
            with open(gloss, "wb") as fh:
                fh.write(raw)
            refused(f"glossary.json {label}", gloss, why, repair)
        os.remove(gloss)
        os.makedirs(gloss)
        refused("a folder where glossary.json belongs", gloss, "is a directory", "move the folder aside")
        os.rmdir(gloss)
        with open(proj, "rb") as fh:
            pj = fh.read()
        with open(proj, "wb") as fh:
            fh.write(pj[: len(pj) // 2])
        refused("project.json cut off, no glossary.json", proj, "is not valid JSON", "checkout HEAD -- project.json")
        with open(proj, "wb") as fh:
            fh.write(pj)
        for label, raw in (("whole", whole), ("BOM'd", b"\xef\xbb\xbf" + whole)):
            with open(gloss, "wb") as fh:
                fh.write(raw)
            got = Glossary.for_project(d, strict=True)
            if got.channel_codes() != ["w-L"] or got.channels != Glossary.for_project(d).channels:
                failures.append(f"{label} glossary.json read strictly as {got.channel_codes()}")
        shutil.rmtree(d)
        os.makedirs(d)
        if Glossary.for_project(d, strict=True).channel_codes() != []:
            failures.append("no file at all is no glossary, and no refusal")
        assert not failures, "\n  ".join(["Glossary.for_project(strict=True):"] + failures)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _check_cli_reads_the_glossary_strictly():
    """`naming.py <project> codes|parse|expect|check` read the glossary as the method's readers do, strictly (#134,
    batch 4's re-review, Out of Scope 6): one that cannot be read is one line, `error: <file> <reason> -- <repair>`,
    exit 1, nothing on stdout -- `codes` printed nothing and exited 0, `parse` and `expect` worked to no codes. `name`
    reads no glossary and still answers."""
    import contextlib
    import io
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="autosound_naming_cli_")
    try:
        whole = json.dumps({"schema_version": 1, "channels": [{"code": "w-L", "active": True, "label": "Низ"}]},
                           ensure_ascii=False).encode("utf-8")
        path = os.path.join(d, "glossary.json")
        with open(path, "wb") as fh:
            fh.write(whole[: whole.index("Низ".encode("utf-8")) + 1])         # inside `Н`: a write cut off
        failures = []

        def run(*args):
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main(["naming.py", d, *args])
            except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
                rc = f"raised {type(exc).__name__}: {exc}"
            return rc, out.getvalue(), err.getvalue()
        for args in (("codes",), ("parse", "w-L_3 (sw)"), ("expect", "0", "3")):
            rc, out, err = run(*args)
            if rc != 1 or out or err.count("\n") != 1 or not err.startswith(f"error: {path} is cut off inside a "
                                                                             f"character") \
                    or "checkout HEAD -- glossary.json" not in err:
                failures.append(f"{args[0]}: rc {rc!r}, stdout {out[-120:]!r}, stderr {err[-300:]!r}")
        rc, out, err = run("name", "w-L", "3", "sw")
        if (rc, out.strip(), err) != (0, "w-L_3 (sw)", ""):
            failures.append(f"name: rc {rc!r}, stdout {out!r}, stderr {err!r}")
        with open(path, "wb") as fh:
            fh.write(whole)
        rc, out, err = run("codes")
        if rc != 0 or out.split() != ["w-L"] or err:
            failures.append(f"codes over the whole file: rc {rc!r}, stdout {out!r}, stderr {err!r}")
        assert not failures, "\n  ".join(["naming.py over a glossary.json it cannot read:"] + failures)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _check_dangling_glossary_link():
    """A `glossary.json` that is a link to nothing is refused by the strict read, naming the link, where it points and
    the repair -- never "no glossary" (#134, batch 4's third re-review, N-M2): `read_json` read the link as no file, so
    the strict read gave an empty glossary over a `project.json` that keeps one, while the lenient read and `contract.py
    check` read that one. The default read is unchanged: it reads past the link, to `project.json`'s glossary.
    `naming.py codes` says it in one line, exit 1. Where this system makes no links (Windows without the privilege), the
    check has nothing to make and says so."""
    import contextlib
    import io
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="autosound_naming_link_")
    try:
        with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"glossary": {"channels": [{"code": "w-L", "active": True}, {"code": "m-L", "active": True}]}},
                      fh)
        link, gone = os.path.join(d, "glossary.json"), os.path.join(d, "shared", "glossary.json")
        try:
            os.symlink(gone, link)
        except (OSError, NotImplementedError):
            print("  (no symbolic links on this system: the link to nothing was not made)")
            return
        failures = []
        try:
            got = Glossary.for_project(d, strict=True)
        except Exception as exc:  # noqa: BLE001 -- the refusal is under test; matched by its type's attribute
            want = (f"{link} is a link to {gone}, which is not there -- restore {gone}, or point the link at the "
                    f"glossary -- or remove the link, and the glossary project.json keeps is read")
            if not getattr(type(exc), "is_unreadable", False) or str(exc) != want:
                failures.append(f"strict: raised {type(exc).__name__}: {exc}")
        else:
            failures.append(f"strict: read as {got.channel_codes()}")
        if Glossary.for_project(d).channel_codes() != ["w-L", "m-L"]:
            failures.append(f"the default read: {Glossary.for_project(d).channel_codes()}")
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = _main(["naming.py", d, "codes"])
        except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
            rc = f"raised {type(exc).__name__}: {exc}"
        if rc != 1 or out.getvalue() or err.getvalue().count("\n") != 1 \
                or not err.getvalue().startswith(f"error: {link} is a link to {gone}"):
            failures.append(f"codes: rc {rc!r}, stdout {out.getvalue()!r}, stderr {err.getvalue()[-300:]!r}")
        assert not failures, "\n  ".join(["a glossary.json that is a link to nothing:"] + failures)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _selftest():
    """The grammar's own checks, and SCR-039's: a renamed channel keeps its captures.

    Run as `python3 naming.py . selftest` — the project argument is ignored, since nothing here
    touches disk.
    """
    failures = []
    for check in (_check_productions, _check_bom_glossary_read, _check_for_project_strict,
                  _check_cli_reads_the_glossary_strictly, _check_dangling_glossary_link):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

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
    # A rename IS a title that differs, so it is reported as one: the check says what REW holds.
    assert verdict["renames"] == {"m-L_2 (sw)": "w-L_2 (sw)"}, verdict

    # -- skill #47: a match the comparison NORMALISED is its own outcome. On a live session REW
    #    held `sw_01 (sw)` while the plan asked for `sw_1 (sw)`; `check` said `ok` on all 16 and
    #    the front-end, which finds a measurement by its literal title, said `0 usable, 16
    #    missing`. Both were right; the silence was the defect. Fails on the old code here --
    #    `matched` and `renames` did not exist and `found` returned the EXPECTED name.
    padded = validate_series(["sw_01 (sw)", "w-L_1 (sw)"],
                             ["sw_1 (sw)", "w-L_1 (sw)", "tw-L_1 (sw)"])
    assert padded["found"] == ["sw_1 (sw)", "w-L_1 (sw)"], padded
    assert padded["matched"]["sw_1 (sw)"] == "sw_01 (sw)", padded
    assert padded["renames"] == {"sw_01 (sw)": "sw_1 (sw)"}, padded
    assert padded["missing"] == ["tw-L_1 (sw)"], padded
    # A title that matches exactly is NOT a rename -- the outcome has to stay distinguishable.
    assert "w-L_1 (sw)" not in padded["renames"], padded
    # The canonical target is what `generate_name` emits, so the rename column is generated, not
    # typed (the tuner's own spec on #47).
    assert generate_name("sw", 1, "sw") == "sw_1 (sw)", generate_name("sw", 1, "sw")

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

    # -- skill #79 (the Arbiter, 2026-09-24): a round in FOUR columns -- Solo (sw), Solo (rta), Group (sw),
    #    Group (rta). Pairs, sides, joints and combos all go into Group of their method; five columns split by
    #    what a capture IS in the analysis were the screen he refused.
    car = Glossary({"channels": [{"code": c} for c in ("sw", "w-L", "w-R", "m-L", "m-R", "c", "r-L", "r-R")]
                    + [{"code": "tw-L", "active": False}],
                    "pairs": {"Ws": ["w-L", "w-R"], "Ms": ["m-L", "m-R"]},
                    "sides": {"L": ["w-L", "m-L"], "R": ["w-R", "m-R"]},
                    "joints": {"SW+Ws": ["sw", "w-L", "w-R"], "L w+m": ["w-L", "m-L"]},
                    "combos": {"ALL": ["sw", "w-L", "w-R", "m-L", "m-R"]}})
    g2 = expected_groups("2", car, 55)
    assert [x["label"] for x in g2] == ["Solo (sw)", "Solo (rta)", "Group (rta)"], [x["label"] for x in g2]
    assert [x["kind"] for x in g2] == ["solo", "solo", "group"]
    assert g2[2]["names"] == ["Ws_55 (rta)", "Ms_55 (rta)", "L_55 (rta)", "R_55 (rta)", "SW+Ws_55 (rta)"], g2[2]
    assert "tw-L_55 (sw)" not in g2[0]["names"], "an inactive channel is no task"
    assert [x["label"] for x in expected_groups("3", car, "final")] == ["Solo (rta)", "Group (rta)"]
    assert sum(len(x["names"]) for x in g2) == len(expected_series("2", car, 55)), "the same list, grouped"

    # -- skill #78: the list is ordered by SETUP -- the method the car is already set up for first, then ONE switch.
    #    A sweep is the tripod in the seat; an RTA is the driver in it with the mic in hand.
    assert [x["label"] for x in order_by_setup(g2, "rta")] == ["Solo (rta)", "Group (rta)", "Solo (sw)"]
    assert [x["label"] for x in order_by_setup(g2, "sw")] == ["Solo (sw)", "Solo (rta)", "Group (rta)"]
    assert order_by_setup(g2, None) == g2, "nothing known about the setup: the plan's order"
    assert method_switches([x["method"] for x in order_by_setup(g2, "rta")]) == 1

    # -- skill #80: a capture asked for beside the plan ("if you have time") goes INTO the list, in its place: a solo
    #    with the solos of its method, a group capture with the groups, a method the round did not have as a new
    #    column. Never prose only.
    placed = place_in_groups(g2, ["tw-L_55 (rta)", "L w+m_55 (rta)", "Ws_55 (sw)", "c_55 (rta)"], car)
    assert [x["label"] for x in placed] == ["Solo (sw)", "Solo (rta)", "Group (rta)", "Group (sw)"], placed
    assert placed[1]["names"][-1] == "tw-L_55 (rta)" and placed[2]["names"][-1] == "L w+m_55 (rta)", placed
    assert placed[3]["names"] == ["Ws_55 (sw)"]
    assert placed[1]["names"].count("c_55 (rta)") == 1, "a title already on the plan is not listed twice"
    assert place_in_groups(placed, ["tw-L_55 (rta)"], car) == placed
    assert [x["label"] for x in order_by_setup(placed, "rta")] == ["Solo (rta)", "Group (rta)", "Solo (sw)", "Group (sw)"]
    bare = place_in_groups([], ["m-L_5 (sw)", "Ms_5 (rta)"], car)      # a round opened without the plan
    assert [(x["label"], x["names"]) for x in bare] == [("Solo (sw)", ["m-L_5 (sw)"]), ("Group (rta)", ["Ms_5 (rta)"])]
    assert flatten_groups(placed) == [n for x in placed for n in x["names"]]

    # -- skill #83: ONE source for "active" -- the project's channel rows (`hidden`, role `unused`, what the intake's
    #    slot switch writes), read when the glossary is loaded for a project. The glossary kept `r-L`/`r-R` active
    #    while the registry had them off, and the plan asked for captures of channels that were switched off.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"channels": [{"code": "w-L", "hidden": False}, {"code": "r-L", "hidden": True},
                                    {"code": "r-R", "role": "unused"}, {"code": "c"}],
                       "glossary": {"channels": [{"code": "w-L", "active": True}, {"code": "r-L", "active": True},
                                                 {"code": "r-R", "active": True}, {"code": "c", "active": False},
                                                 {"code": "tw-L", "active": True}]}}, fh)
        pg = Glossary.for_project(d)
        assert pg.channel_codes(active_only=True) == ["w-L", "c", "tw-L"], pg.channel_codes(active_only=True)
        assert pg.is_active("r-L") is False and pg.is_active("c") is True, "the project's row decides, on or off"
        assert pg.is_active("tw-L") is True, "a code the project has no row for keeps the glossary's flag"

    # -- S-079 (the Arbiter, 2026-10-01): both notations are read, the hyphen is the one written. The Passat's shape:
    #    its channels are `w-L`…, and a capture typed `w_L_3` was refused here from S-042 on.
    #    `_` stays the series separator, so only the code in front of `_N` changes.
    for typed, one in (("w_L_3", "w-L_3"), ("w_L", "w-L"), ("w_L (imp)", "w-L (imp)"), ("sw_1", "sw_1"),
                       ("w-L_2", "w-L_2"), ("ALL+C_25", "ALL+C_25"), ("tw_R_final (rta) x0", "tw-R_final (rta) x0"),
                       ("m_L-ctl1_49 (sw)", "m-L-ctl1_49 (sw)"), ("m_L p3_49 (sw)", "m-L p3_49 (sw)"),
                       ("w_L low_cut_49 (sw)", "w-L low_cut_49 (sw)"), ("sw_01 (sw)", "sw_01 (sw)")):
        assert canonical_title(typed) == one, (typed, canonical_title(typed), one)
    # A file stem or an id has no series, so it is read whole -- the one place the two entry points differ.
    assert canonical_code("w_L") == "w-L" and canonical_code("m_L-ctl1") == "m-L-ctl1"
    assert canonical_code(None) is None and canonical_code("w-L low_cut") == "w-L low_cut"
    # -- hub #232 TCC-044 (the Arbiter, 2026-10-01: «це правило до драйвер-L/R і все»): only a driver's side. v3.0.65
    #    read every `_`, and the old configuration prefix of real captures (cap_010, cap_013) became a channel `D-L`.
    for kept in ("sw_1", "D_L", "D_SW+Ws", "sw_f", "c_H", "w_Lx", "W_L"):
        assert canonical_code(kept) == kept, (kept, canonical_code(kept))
    assert canonical_code("sw+w_L") == "sw+w-L" and canonical_code("D_w_L") == "D_w-L"
    assert canonical_title("D_L_7 (rta) m-L: lev=-4.5, PK=-2") == "D_L_7 (rta) m-L: lev=-4.5, PK=-2"
    for title, new in (("D_L_7 (rta) m-L: lev=-4.5, PK=-2", "`L_D7 (rta) m-L: lev=-4.5, PK=-2`"),
                       ("D_L w+m_7 (rta) inv", "`L w+m_D7 (rta) inv`"), ("D_SW+Ws_9 (rta)", "`SW+Ws_D9 (rta)`"),
                       ("D_w-L (imp) case35l", "`w-L (imp) case35l`"), ("D_w_L_7 (sw)", "`w_L_D7 (sw)`")):
        got, why = explain_name(title)
        assert got is None and "`D_` is an old configuration prefix" in why and new in why, (title, why)
    got, why = explain_name("sw_f_1 (sw)")
    assert got is None and "`sw_f`: a code has no `_`" in why, why
    assert parse_name("D_L_7 (rta)", Glossary({"channels": [{"code": "w-L"}], "sides": {"L": ["w-L"]}})) is None
    passat = Glossary({"channels": [{"code": c} for c in ("sw", "w-L", "w-R", "m-L", "tw-L", "c")],
                       "combos": {"ALL+C": ["sw", "w-L", "w-R", "m-L", "tw-L", "c"]}})
    got, why = explain_name("w_L_3 (sw)", passat)
    assert why is None, "a title the grammar reads carries no reason: a reader takes one as a refusal"
    assert (got["code"], got["code_current"], got["version_n"], got["title"]) == ("w-L", "w-L", 3, "w_L_3 (sw)"), got
    assert "`w-L`" in got["note"] and "`w-L_3 (sw)`" in got["note"], got["note"]
    assert name_key(got) == name_key(parse_name("w-L_3 (sw)", passat)), "one channel, one series, one method"
    assert parse_name("w-L_3 (sw)", passat)["note"] is None, "a title in the notation is not annotated"
    for title, code in (("sw_1 (sw)", "sw"), ("ALL+C_25 (rta)", "ALL+C"), ("w_L (imp)", "w-L"), ("w_L_3", "w-L")):
        assert parse_name(title, passat)["code"] == code, (title, parse_name(title, passat))
    assert parse_name("w_L_3 (sw)")["code"] == "w-L", "no glossary: still the hyphen form"
    assert parse_name("w_L FX_3 (sw)", passat)["modifier"] == "FX", "the code still splits off its modifier"
    imp = parse_name("w_L (imp)", passat)
    assert (imp["method"], imp["version"]) == ("imp", None) and name_key(imp) == name_key(parse_name("w-L (imp)"))
    # The check finds it, and the rename it offers is the Arbiter's «`_` міняти на `-`».
    seen = validate_series(["w_L_3 (sw)", "sw_1 (sw)"], ["w-L_3 (sw)", "sw_1 (sw)"], passat)
    assert seen["complete"] and seen["renames"] == {"w_L_3 (sw)": "w-L_3 (sw)"}, seen
    # A modifier's own `_` is not the code's, and a glossary in the other notation is the same names.
    assert parse_name("w-L low_cut_49 (sw)", Glossary({"channels": [{"code": "w-L"}]}))["modifier"] == "low_cut"
    older = Glossary({"channels": [{"code": "w-L", "previous_names": ["w_L"]}, {"code": "tw_L"}]})
    assert older.resolve_code("w_L") == "w-L" and older.resolve_code("tw-L") == "tw_L"
    assert older.former_codes() == [], "`w_L` is `w-L`'s own name, not a retired one"
    assert parse_name("tw-L FX_2 (sw)", older)["modifier"] == "FX"

    # -- skill #66 (the Arbiter, 2026-09-24): `+`/`-` between lowercase driver codes, side first; the member after
    # `-` is inverted. `L m-tw` is the junction `L m+tw` with the tweeter inverted -- it used to parse, silently, as
    # the side `L` with a modifier `m-tw`, and the round that asked for the inverted take reported it missing.
    jg = Glossary({"channels": [{"code": c} for c in ("tw-L", "m-L", "w-L", "sw")],
                   "sides": {"L": ["tw-L", "m-L", "w-L"]},
                   "joints": {"L m+tw": ["m-L", "tw-L"], "L w+m": ["w-L", "m-L"]}})
    got = parse_name("L m-tw_52 (rta)", jg)
    assert (got["code"], got["modifier"], got["params"], got["inverted"]) == ("L m+tw", None, "inv", ["tw"]), got
    assert name_key(got) == name_key(parse_name("L m+tw_52 (rta) inv", jg))
    assert name_key(got) != name_key(parse_name("L m+tw_52 (rta)", jg))
    assert validate_series(["L m-tw_52 (rta)"], ["L m+tw_52 (rta) inv"], jg)["complete"]
    three = parse_name("L w-m+tw_1 (rta)", jg)
    assert (three["params"], three["inverted"]) == ("inv:m", ["m"]), three
    assert parse_name("L m-tw_52 (rta) noXO", jg)["params"] == "inv noXO"
    # A hyphen that is a driver's side stays one, and a member no channel has is not guessed at.
    assert parse_name("m-L_52 (rta)", jg)["code"] == "m-L"
    assert parse_name("L m-xx_52 (rta)", jg)["modifier"] == "m-xx"
    assert parse_name("L m+tw_52 (rta)", jg)["inverted"] == []
    print("selftest OK — grammar round-trips, padding-insensitive version match, and a renamed "
          "channel's old captures resolve to it (SCR-039); positions p1..p9/x0 and controls "
          "ctl1/ctl3/ctl/rep parse in both forms and are identity, not code; a clarification "
          "after the method is another measurement in the same series (#34), (imp) without `_N` (#33), refusals "
          "with a reason, and no ledger version for `_N` (#37); a match the comparison NORMALISED says the title on disk differs and names the canonical one to rename it to (#47); "
          "a driver's side typed with `_` is read as `-`, with a note, and the series is left alone (S-079); any "
          "other `_` in a code is refused, the old `D_` prefix by name (#232)")
    return 0


def _main(argv):
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    project, cmd, args = argv[1], argv[2], argv[3:]
    if cmd == "selftest":
        return _selftest()
    try:
        # The commands that read the glossary read it as the method's readers do, strictly (#134, batch 4's re-review,
        # Out of Scope 6): one that cannot be read is said below, never worked to no codes. `name` and `next-series`
        # read none.
        g = Glossary.for_project(project, strict=True) if cmd in ("codes", "parse", "expect", "check") else None
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
        elif cmd == "next-series":
            # #56 item 10: the number a new sheet's titles carry, from THIS project's rounds -- never an example's.
            here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
            if here not in sys.path:
                sys.path.insert(0, here)
            import process as _process
            print(_process.Process(os.path.join(project, "process")).next_series())
        elif cmd == "check":
            import rew_api

            titles = [m.get("title", "") for m in rew_api.get_measurements().values()]
            verdict = validate_series(titles, expected_series(args[0], g, args[1]), g)
            for name in verdict["found"]:
                actual = verdict["matched"].get(name, name)
                # #47: a normalised match says so. `ok` alone is what let 16 measurements be
                # reported as present under titles REW does not hold.
                print(f"  ok      {name}" if actual == name else
                      f"  ok*     {name}  -- REW holds '{actual}'; rename it to the canonical "
                      f"title before a front-end looks for it by name")
            for name in verdict["missing"]:
                print(f"  MISSING {name}")
            for name in verdict["extra"]:
                print(f"  extra   {name}")
            for name in verdict["foreign"]:
                # Not an error, but the one a tuner most needs to see: a title REW holds that
                # isn't in the convention at all, so no analysis will ever find it by name -- and
                # what in it could not be placed, so the fix is one rename rather than a hunt.
                print(f"  ?name   {name}  -- {explain_name(name, g)[1]}")
            print(f"{len(verdict['found'])}/{len(verdict['expected'])} captured"
                  + (f", {len(verdict['renames'])} under another title (ok*)"
                     if verdict["renames"] else ""))
            if verdict["renames"]:
                print("  the renames, as `rew_api.rename_measurement(uuid, new)` would take them "
                      "(a rename keeps REW's uuid):")
                for actual, canonical in sorted(verdict["renames"].items()):
                    print(f"    {actual!r} -> {canonical!r}")
            return 0 if verdict["complete"] else 1
        else:
            print(_USAGE, file=sys.stderr)
            return 2
    except (NamingError, IndexError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute below; anything else still raises
        # `next-series` reads the journal as the method does, strictly (#134, R53), and the glossary's readers the
        # glossary: one it cannot read is a refusal in one line, `error: <file> <reason> -- <repair>`, exit 1, never a
        # traceback -- nor a number counted without it.
        if not getattr(type(exc), "is_unreadable", False):
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(_main(sys.argv))
