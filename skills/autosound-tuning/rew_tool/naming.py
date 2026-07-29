"""Measurement naming as code — SCR-008.

The grammar and the per-car glossary have until now lived only as prose:
`naming-and-structure.md §3` for the grammar, `autosound_context.md §5` for the codes. Two readers
means two readings, and the front-end ended up hard-coding a capture series that no car actually
has.

    name = <channel|pair|combo|joint>[ <modifier>]_<version>[ (<method>)]

    sw_1 (sw)        w-L_2 (rta)      ALL+C_25 (rta)      L w+m_3 (sw)      tw-R_final (rta)

* **`_N` is the DSP config version the measurement was taken under**, not a counter. Bump it when
  the config changes; that is what lets "before vs after" line up. `final` is allowed (phase 3).
* **Method suffix**: `(sw)` = acoustic sweep, for phase/time/distortion; `(rta)` = MMM RTA, for
  magnitude/tone. Phases 0 and 2 want both per driver.
* **Modifiers** (`FX`, `c FX`, …) and **transient experiment tags** (`INV`, `i`, `+Δτ`) sit
  between the code and `_N`. A tag is temporary by design: once the change is baked into the base
  it drops from the name, and `dsp-state-current` — not the title — says what is committed.

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
METHODS = (METHOD_SWEEP, METHOD_RTA)

# `<body>_<version>` with an optional ` (method)`. `body` is non-greedy up to the LAST underscore
# so codes that contain one still parse; version is digits or the literal `final`.
_NAME_RE = re.compile(
    r"^(?P<body>.+)_(?P<version>\d+|final)(?:\s*\((?P<method>[A-Za-z]+)\))?\s*$"
)


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
        for c in self.channels:
            if c.get("code") == code:
                return bool(c.get("active", True))
        return True  # a code we don't know about isn't ours to exclude

    def all_codes(self):
        """Every code the grammar may legally use, longest first.

        Longest-first matters for parsing: `ALL+C` must win over `ALL`, and `L w+m` over `L`, or a
        joint gets read as a side plus a stray modifier.
        """
        codes = (
            self.channel_codes()
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


def generate_name(code, version, method=None, modifier=None):
    """Build a measurement title. `version` is an int or `"final"`.

    >>> generate_name("w-L", 2, "sw")
    'w-L_2 (sw)'
    >>> generate_name("ALL+C", "final", "rta")
    'ALL+C_final (rta)'
    """
    if not code:
        raise NamingError("a measurement name needs a channel/pair/combo/joint code")
    if method is not None and method not in METHODS:
        raise NamingError(f"unknown method {method!r}; expected one of {', '.join(METHODS)}")
    body = f"{code} {modifier}".strip() if modifier else str(code)
    name = f"{body}_{version}"
    return f"{name} ({method})" if method else name


def parse_name(title, glossary=None):
    """Split a title into its parts, or return None if it isn't in the grammar.

    Returning None rather than raising is deliberate: REW lists contain things nobody named to
    this convention (imports, room-sim results), and a reader must be able to say "not one of
    ours" without treating it as an error.

    With a glossary the code and modifier are separated properly (`L w+m` is a joint, not the side
    `L` with a modifier). Without one, the whole body is reported as the code, since guessing
    where a code ends is exactly the ambiguity the glossary exists to remove.
    """
    if not title:
        return None
    match = _NAME_RE.match(title.strip())
    if not match:
        return None
    method = match.group("method")
    if method is not None and method.lower() not in METHODS:
        return None  # `(foo)` is not a method suffix; the title isn't ours
    body = match.group("body").strip()

    code, modifier = body, None
    if glossary:
        for candidate in glossary.all_codes():
            if body == candidate:
                code, modifier = candidate, None
                break
            if body.startswith(candidate + " "):
                code, modifier = candidate, body[len(candidate) + 1 :].strip() or None
                break

    version = match.group("version")
    return {
        "code": code,
        "modifier": modifier,
        "version": version,
        # Numeric form, so `_01` and `_1` are recognised as the same DSP config version. REW
        # titles are typed by hand and zero-padding is common; comparing raw strings makes a
        # captured measurement look missing, which is the checker crying wolf.
        "version_n": int(version) if version.isdigit() else None,
        "method": method.lower() if method else None,
        "title": title.strip(),
    }


def name_key(parsed):
    """Identity of a measurement for comparison: code, modifier, version, method.

    Matching on this rather than on the raw title is what makes `c_01 (rta)` and `c_1 (rta)` the
    same measurement, and what lets a checker survive the padding a human happens to type.
    """
    if not parsed:
        return None
    version = parsed.get("version_n")
    if version is None:
        version = parsed.get("version")
    return (parsed.get("code"), parsed.get("modifier"), version, parsed.get("method"))


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
        return [j for j in glossary.joints if j.upper().startswith("SW+")]
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
  parse <title>                  split a title into code/modifier/version/method
  expect <phase> <version>       the capture series a phase expects
  check <phase> <version>        compare that series against what REW currently holds
"""


def _main(argv):
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    project, cmd, args = argv[1], argv[2], argv[3:]
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
            parsed = parse_name(args[0], g)
            print(json.dumps(parsed, ensure_ascii=False) if parsed else "not a measurement name")
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
                # isn't in the convention at all, so no analysis will ever find it by name.
                print(f"  ?name   {name}")
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
    sys.exit(_main(sys.argv))
