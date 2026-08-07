"""Project-level facts — SCR-001/011/014/016/017 (autosound-tcc sync, 2026-07-29).

Objective, machine-checkable facts about ONE car+install that used to live only in prose
(`autosound_context.md`): car/source/DSP/amps/mic/paths/presets, per-channel driver assignments
(make/model/Fs — SCR-001), the naming glossary (SCR-008's `naming.Glossary.for_project` already
reads this file's `glossary` key), DSP-hardware-level controls that are constant across presets
(RearRC/SubRC/RealCenter — SCR-017: those are knob positions on the device, NOT preset state, so
they do NOT belong in the per-preset ledger, and they must stay optional since a MUSWAY/other
vendor has no equivalent), and a project-scoped channel-tier summary (SCR-016, e.g. "8 virtual channels, 1 off").

Same split as `state/state.py` / `dsp_profile.py`: DATA is project-local (`<project>/project.json`,
the project-folder root — SKILL-SYNC-PLAN.md D1), CODE is in the skill.

This file holds FACTS, never their presentation. A `param_sections` key used to carry ready-made
label/value rows for a consumer UI's panels — the same DSP/mic/source values that are already
fields here, in a second, hand-maintained shape. Dropped in schema v3 for the reason `slot` and
`descr` left the ledger: one fact, one home. A UI renders its panels from the facts.

Provenance (SCR-014): most facts are file-scoped — a top-level `sources` free-text list, the same
convention `dsp_profile.json` already uses in the wild (confirmed once, rarely revisited). The
handful of facts that individually drift MID-PROJECT (amp gain, a driver's Fs, a DSP hardware
control's dialled position) are wrapped `fact(value, source, at)` instead, since those are exactly
what a `config_change` journal event (`record_change`) needs to point back at. Unconfirmed facts
are `null` (wrapped or bare) — `open_questions()` walks the whole structure for them, the same
walker `dsp_profile.py.open_questions()` uses, so incremental intake asks only about what's still
missing.

stdlib only, py3.9+.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# One number across every machine file this skill writes (project.json, the ledger,
# process-state.json, dsp_profile.json), moving together with the skill's own major version.
# "Which format is this project in?" is then one question with one answer, and `contract.py` can
# reject a whole tree in one comparison instead of consulting a matrix of per-file versions.
# 3 is the first break: identity left the ledger for `channels[]` here (SCR-001) and snapshots
# started stamping `project_rev` (SCR-024). 2.x files are read by `state/migrate.py`, not by this.
SCHEMA_VERSION = 3
# `state/process.py`'s own event-type constant, mirrored here rather than imported: project.py
# lives at `rew_tool/` top level, `process.py` under `rew_tool/state/` (a separate, sys.path-
# synthetic package by convention -- see `rew_tool.py`'s own selftest for the same lazy-import
# pattern). Keeping this a literal avoids a cross-directory import for one constant; a caller
# that already has a live `Process` instance never needs the module import at all.
_EV_CONFIG_CHANGE = "config_change"
FACT_SOURCES = ("user", "measured", "datasheet")

IMPACT_NONE = "none"
IMPACT_REBASELINE = "full_rebaseline"


class ProjectError(ValueError):
    """A `project.json` shape a reader can't trust."""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fact(value, source=None, at=None):
    """Wrap one individually-provenanced fact (SCR-014) — amp gain, driver Fs, a hardware
    control's dialled position: the ones a `config_change` event will point back at later.
    `source` should be one of `FACT_SOURCES` when given, but isn't enforced here (see `validate`'s
    "lenient on free-text" split) — a typo'd source is a code-review nit, not a corrupted file."""
    return {"value": value, "source": source, "at": at or (_now() if value is not None else None)}


def fact_value(x):
    """Unwrap a `fact()` object OR pass a bare value through — most fields in this file are bare;
    only the ones that drift mid-project are wrapped, and a reader shouldn't have to know which."""
    return x.get("value") if isinstance(x, dict) and "value" in x else x


def _empty_project():
    return {
        "schema_version": SCHEMA_VERSION,
        # SCR-024: bumped on every write (see `Project.save`). A ledger snapshot copies the value
        # in force when it was taken, so a consumer joining `channels[]` onto an old snapshot can
        # tell whether it is reading the facts of that day or today's. 0 = nothing written yet.
        "project_rev": 0,
        "sources": [],
        "car": {}, "source": {}, "dsp": {}, "amps": [], "mic": {},
        "paths": {}, "presets": [],
        "channels": [], "hardware": {"controls": {}},
        "glossary": {}, "channel_summary": {},
        # SCR-015: the phase-0 Acoustic Flaw Map as data. What this cabin and this install do to
        # the sound -- and, per entry, what may and may not be done about it.
        "acoustics": {"flaws": []},
        "_open_questions": [],
    }


def validate(data):
    """Raise `ProjectError` on a malformed file; return `data` unchanged if OK.

    Lenient by design (same split as `state.py`/`dsp_profile.py`): this checks SHAPE (right
    collection types, no duplicate channel codes), not that any particular fact is filled in — an
    unconfirmed fact is `null`/absent and belongs in `_open_questions`, not a validation error.
    """
    if not isinstance(data, dict):
        raise ProjectError("project.json must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ProjectError(
            f"unsupported schema_version {data.get('schema_version')!r} (expected {SCHEMA_VERSION})"
            + (" -- 2.x project, run `python3 rew_tool/state/migrate.py`"
               if isinstance(data.get("schema_version"), int)
               and data["schema_version"] < SCHEMA_VERSION else ""))
    rev = data.get("project_rev")
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 0:
        raise ProjectError(f"project_rev must be a non-negative int, got {rev!r}")
    for key in ("amps", "presets", "channels", "sources", "_open_questions"):
        if key in data and not isinstance(data[key], list):
            raise ProjectError(f"{key!r} must be a list")
    seen = set()
    for ch in data.get("channels", []):
        if not isinstance(ch, dict) or not ch.get("code"):
            raise ProjectError(f"every channels[] entry needs a code, got {ch!r}")
        if ch["code"] in seen:
            raise ProjectError(f"duplicate channel code {ch['code']!r}")
        seen.add(ch["code"])
    if "hardware" in data and not isinstance(data["hardware"], dict):
        raise ProjectError("hardware must be an object")
    if "glossary" in data and not isinstance(data["glossary"], dict):
        raise ProjectError("glossary must be an object")
    return data


# What a flaw IS. A closed list because a front-end colours by it and a model picks from it: free
# text here would be a field nobody can render and everybody words differently.
FLAW_KINDS = (
    "room_gain", "modal_peak", "cabin_null", "sbir", "floor_bounce",
    "driver_resonance", "non_min_phase", "thd_spike", "pair_suckout",
)
# What may be DONE about it -- the load-bearing half. Closed for the same reason, and because the
# whole point of writing the map down is that "don't EQ-boost this null" survives the session that
# discovered it.
FLAW_ACTIONS = ("notch", "leave", "no_boost", "geometry", "delay", "crossover")


def validate_flaw(entry):
    """Raise `ProjectError` unless this is a flaw a later session can act on.

    The one rule with teeth: **a dip cannot be notched**. A cabin null or an SBIR notch is
    interference, not minimum-phase -- cutting it does nothing and boosting it burns headroom
    against physics, which is exactly the mistake the map exists to prevent. Everything else is
    shape: a frequency, a signed level, a kind and an action from the lists above, a reason, and
    evidence, because a flaw with no measurement behind it is a rumour.
    """
    if not isinstance(entry, dict):
        raise ProjectError("a flaw must be an object")
    f = entry.get("f_hz")
    if not isinstance(f, (int, float)) or isinstance(f, bool) or f <= 0:
        raise ProjectError(f"f_hz must be a positive Hz, got {f!r}")
    level = entry.get("level_db")
    if not isinstance(level, (int, float)) or isinstance(level, bool):
        raise ProjectError(
            f"level_db must be a number: the FEATURE, signed — + a hump, - a dip. Not the "
            f"correction you would apply to it (got {level!r})"
        )
    if entry.get("kind") not in FLAW_KINDS:
        raise ProjectError(
            f"kind must be one of {', '.join(FLAW_KINDS)} (got {entry.get('kind')!r})"
        )
    if entry.get("action") not in FLAW_ACTIONS:
        raise ProjectError(
            f"action must be one of {', '.join(FLAW_ACTIONS)} (got {entry.get('action')!r})"
        )
    if level < 0 and entry.get("action") == "notch":
        raise ProjectError(
            f"{f:g} Hz is a dip ({level:g} dB) and cannot be notched: a null is interference, not "
            "minimum-phase — cutting it changes nothing and boosting it burns headroom against "
            "physics. Use `leave`/`no_boost`, or `geometry`/`delay`/`crossover` if the fix is one "
            "of those. If you meant a HUMP you intend to cut, `level_db` is the feature itself "
            f"({abs(level):g}, positive), not the correction you would apply to it."
        )
    if not str(entry.get("why") or "").strip():
        raise ProjectError("a flaw needs `why` — the next session reads the reason, not the number")
    if not [e for e in (entry.get("evidence") or []) if str(e).strip()]:
        raise ProjectError(
            "a flaw needs evidence (the capture it was read off) — a flaw with no measurement "
            "behind it is a rumour, and the map is consumed as fact"
        )
    return entry


def open_questions(data):
    """Every still-null fact (dotted path) plus any `_open_questions` freeform notes.

    Mirrors `dsp_profile.py.open_questions()` exactly (a `fact()` wrapper's own `source`/`at`
    keys are never surfaced as separate open questions — only its `value` is inspected)."""
    out = list(data.get("_open_questions") or [])

    def walk(prefix, obj):
        if isinstance(obj, dict):
            if "value" in obj and "source" in obj and "at" in obj:  # a fact() wrapper
                if obj["value"] is None:
                    out.append(prefix.rstrip("."))
                return
            for k, v in obj.items():
                if k == "_open_questions":
                    continue
                if v is None:
                    out.append(f"{prefix}{k}")
                else:
                    walk(f"{prefix}{k}.", v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(f"{prefix}{i}.", v)

    walk("", {k: v for k, v in data.items() if k != "_open_questions"})
    return out


class Project:
    """Read/write one project's `project.json`. `root` is the project folder itself — the file
    sits at its top level, alongside `dsp_profile.json`, `process/`, `state/` (SKILL-SYNC-PLAN.md
    D1), not nested under a `presets/<preset>/` subtree."""

    def __init__(self, root):
        # No `makedirs`: reading a project must not create one (same rule as `Process` and
        # `PresetHistory`). `save()` creates the folder when there is finally something to put in it.
        self.dir = root

    @property
    def path(self):
        return os.path.join(self.dir, "project.json")

    def load(self):
        """The current facts, or an empty skeleton if this project has none yet — a brand-new
        project folder reads as "nothing known", not an error."""
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return _empty_project()
        base = _empty_project()
        base.update(data)
        return base

    def save(self, data):
        """Bump `project_rev`, validate, then write atomically (write-temp-then-rename — same
        discipline as `process.py`'s `_write`: a crash mid-write must not read back as an empty
        project).

        The revision counts WRITES, not semantic changes (SCR-024). A consumer only ever needs two
        things from it — ordering and equality — and deciding "did these facts really change?"
        would put this module in the business of diffing, with no reader asking for it.
        """
        data["schema_version"] = SCHEMA_VERSION
        rev = data.get("project_rev")
        data["project_rev"] = (rev if isinstance(rev, int) and not isinstance(rev, bool) else 0) + 1
        validate(data)
        os.makedirs(self.dir, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        os.replace(tmp, self.path)
        return data

    def set_channel(self, code, **fields):
        """Add or update one `channels[]` row by `code` (SCR-001) — `slot`/`descr`/`role`/`order`/
        `driver`/`fs_hz`/`impedance_ohm`/`hidden`, whatever the caller has; wrap `fact()`-worthy
        fields (e.g. `fs_hz`) before calling. An unknown code is appended, not refused — intake
        builds this list one confirmed fact at a time."""
        data = self.load()
        rows = data.setdefault("channels", [])
        row = next((r for r in rows if r.get("code") == code), None)
        if row is None:
            row = {"code": code}
            rows.append(row)
        row.update(fields)
        return self.save(data)

    def add_flaw(self, **fields):
        """Add (or replace, by frequency + channels) one acoustic-flaw entry — SCR-015.

        Replacing rather than appending on a repeat: re-measuring the same peak after an install
        change should correct the map, not leave two contradictory rows for a reader to pick
        between. A genuinely different finding at the same frequency belongs to different channels
        and therefore lands beside it.
        """
        entry = dict(fields)
        entry.setdefault("channels", [])
        validate_flaw(entry)
        entry["at"] = _now()
        data = self.load()
        flaws = data.setdefault("acoustics", {}).setdefault("flaws", [])
        key = (round(float(entry["f_hz"]), 1), tuple(sorted(entry.get("channels") or [])))
        for i, existing in enumerate(list(flaws)):
            same = (
                round(float(existing.get("f_hz", -1)), 1),
                tuple(sorted(existing.get("channels") or [])),
            )
            if same == key:
                flaws[i] = entry
                break
        else:
            flaws.append(entry)
        flaws.sort(key=lambda e: float(e.get("f_hz", 0)))
        self.save(data)
        return entry

    def flaws(self, data=None):
        """The map, lowest frequency first. Empty until phase 0 builds it."""
        data = data or self.load()
        return list((data.get("acoustics") or {}).get("flaws") or [])

    def set_hardware_control(self, name, value, source=None):
        """A DSP-hardware-level knob position (e.g. `RearRC`/`SubRC`/`RealCenter` — SCR-017),
        constant across this DSP's presets, so it lives here ONCE — not copy-pasted into every
        preset ledger where it can drift out of sync (the pilot bug this closes)."""
        data = self.load()
        controls = data.setdefault("hardware", {}).setdefault("controls", {})
        controls[name] = fact(value, source=source)
        return self.save(data)

    @staticmethod
    def parse_impact(impact):
        """One reading of a `config_change` event's `impact`, for every consumer.

        The field is a short string by design (it is written by hand as often as by code), which
        means somebody has to parse it — and the moment that somebody is a consumer app, the format
        has two readings and they drift. So the parse lives here, next to the writer:

            "none"                  -> {"kind": "none",            "codes": ()}
            "remeasure: [w-L, w-R]" -> {"kind": "remeasure",       "codes": ("w-L", "w-R")}
            "full_rebaseline"       -> {"kind": "full_rebaseline", "codes": ()}   # everything
            anything else           -> {"kind": "other",           "codes": ()}   # e.g. "voicing"

        `other` is not an error: `process.py::set_target` already writes `impact="voicing"`, and a
        human writing "check the sub once the amp is back" is doing something reasonable. An
        unrecognised impact means "a consumer cannot act on this automatically", never "ignore it"
        — the raw text comes back so it can still be shown.
        """
        raw = (impact or "").strip()
        low = raw.lower()
        if not raw or low == IMPACT_NONE:
            return {"kind": "none", "codes": (), "raw": raw}
        if low == IMPACT_REBASELINE:
            return {"kind": "full_rebaseline", "codes": (), "raw": raw}
        if low.startswith("remeasure"):
            inside = raw.split(":", 1)[1] if ":" in raw else ""
            codes = tuple(
                c.strip() for c in inside.strip().strip("[]").split(",") if c.strip()
            )
            return {"kind": "remeasure", "codes": codes, "raw": raw}
        return {"kind": "other", "codes": (), "raw": raw}

    def record_change(self, proc, file, what, why=None, source=None, impact=IMPACT_NONE):
        """Log a config-change journal event (SCR-014) for a mid-project correction to ANY machine
        config file (driver swap, amp re-gain, new preset, curve switch, a newly-discovered
        per-vendor EQ band order) — not just this one. `proc` is a `state.process.Process` for the
        SAME project; the event lands in ITS `journal.jsonl` (SCR-004's single process history),
        not a second log this module would own.

        `impact` is the machine form of `naming-and-structure.md §2`'s "what raw data survives"
        table: `IMPACT_NONE`, `"remeasure: [<codes>]"`, or `IMPACT_REBASELINE`. A consumer UI uses
        it to flag exactly the affected measurements/plan steps as stale, never silently.
        """
        return proc._append(_EV_CONFIG_CHANGE, file=file, what=what, why=why,
                             source=source, impact=impact)


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: project.py <project-dir> <command> [args]

  show                                         print project.json (or an empty skeleton)
  open-questions                               list unresolved facts (dotted paths)
  set-channel <code> [key=value ...]           add/update one channels[] row
      [--source S]                             values are JSON when they parse as JSON, so
                                               driver={"make":"Audiofrog","model":"GB25"} works;
                                               --source wraps fs_hz as a fact()
  set-hardware <name> <value> [--source S]     set a DSP-hardware control (RearRC/SubRC/...)
  record-change <process-dir> <file> <what>    log a config_change journal event
      [--why W] [--source S] [--impact I]
  flaw <f_hz> <level_db> <kind> <action>       add/replace an acoustic-flaw entry (SCR-015)
      [--q Q] [--bw-oct B] [--channels a,b]    level_db is the FEATURE, signed: + a hump,
                                                 - a dip. NOT the correction you would apply
      --why W --evidence "t1,t2"               kind: room_gain|modal_peak|cabin_null|sbir|
                                                 floor_bounce|driver_resonance|non_min_phase|
                                                 thd_spike|pair_suckout
                                               action: notch|leave|no_boost|geometry|delay|
                                                 crossover  (a dip can never be `notch`)
  flaws                                        print the map, lowest frequency first
"""


#: Channel fields the schema keeps as `fact(value, source, at)` because they drift mid-project
#: (a driver gets replaced, a datasheet number is superseded by a measured one). `--source` on
#: `set-channel` wraps exactly these; everything else is stored bare, since provenance on a slot
#: letter is noise.
CHANNEL_FACT_FIELDS = ("fs_hz",)


def _parse_kv(pairs, source=None):
    """`key=value` pairs from a command line into typed values.

    Values are JSON-decoded when they parse as JSON, so a nested fact is expressible from the
    shell: `driver={"make":"Audiofrog","model":"GB25"}` stores an OBJECT. It used to store the
    literal string, which no reader complains about and every reader then renders as a line of
    JSON where a speaker name should be — found by watching a live intake session route around
    this command with an inline Python script rather than use it.
    """
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"expected key=value, got {pair!r}")
        k, v = pair.split("=", 1)
        try:
            v = json.loads(v)
        except ValueError:
            pass  # a genuine free-text value ("Front L Woofer") is kept as-is
        if source and k in CHANNEL_FACT_FIELDS:
            v = fact(v, source=source)
        out[k] = v
    return out


def _flag(args, name, default=None):
    if name in args:
        i = args.index(name)
        args.pop(i)
        return args.pop(i)
    return default


def _load_process(process_dir):
    """Build a `state.process.Process` for `process_dir` — lazy sys.path import, same technique
    `rew_tool.py`'s own selftest uses to reach the `state/` sub-package from a top-level script."""
    state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import process as _proc_mod

    return _proc_mod.Process(process_dir)


def _main(argv):
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    root, cmd, args = argv[1], argv[2], list(argv[3:])
    proj = Project(root)
    try:
        if cmd == "show":
            print(json.dumps(proj.load(), indent=2, ensure_ascii=False))
        elif cmd == "open-questions":
            for q in open_questions(proj.load()):
                print(q)
        elif cmd == "set-channel":
            source = _flag(args, "--source")
            code, kv = args[0], _parse_kv(args[1:], source=source)
            proj.set_channel(code, **kv)
            print(f"channel {code} updated")
        elif cmd == "set-hardware":
            source = _flag(args, "--source")
            name, value = args[0], args[1]
            proj.set_hardware_control(name, value, source=source)
            print(f"hardware.controls.{name} = {value!r}")
        elif cmd == "record-change":
            why = _flag(args, "--why")
            source = _flag(args, "--source")
            impact = _flag(args, "--impact", IMPACT_NONE)
            process_dir, file, what = args[0], args[1], args[2]
            proc = _load_process(process_dir)
            proj.record_change(proc, file, what, why=why, source=source, impact=impact)
            print(f"config_change recorded: {file} — {what}")
        elif cmd == "flaw":
            # Each flag is read ONCE: `_flag` pops what it finds, so asking twice (the classic
            # `float(x) if x else None`) hands back None on the second call.
            q = _flag(args, "--q")
            bw = _flag(args, "--bw-oct")
            channels = _flag(args, "--channels") or ""
            why = _flag(args, "--why")
            evidence = _flag(args, "--evidence") or ""
            entry = proj.add_flaw(
                f_hz=float(args[0]),
                level_db=float(args[1]),
                kind=args[2],
                action=args[3],
                q=float(q) if q else None,
                bw_oct=float(bw) if bw else None,
                channels=[c.strip() for c in channels.split(",") if c.strip()],
                why=why,
                evidence=[e.strip() for e in evidence.split(",") if e.strip()],
            )
            width = f" Q{entry['q']:g}" if entry.get("q") else (
                f" {entry['bw_oct']:g}oct" if entry.get("bw_oct") else "")
            print(f"{entry['f_hz']:g} Hz{width} {entry['level_db']:+g} dB "
                  f"[{entry['kind']}] -> {entry['action']}")
        elif cmd == "flaws":
            for entry in proj.flaws():
                width = f" Q{entry['q']:g}" if entry.get("q") else (
                    f" {entry['bw_oct']:g}oct" if entry.get("bw_oct") else "")
                who = ", ".join(entry.get("channels") or []) or "—"
                print(f"{entry['f_hz']:>7.6g} Hz{width:>8} {entry['level_db']:+6g} dB  "
                      f"{entry['kind']:<16} {entry['action']:<10} {who:<12} {entry.get('why','')}")
        else:
            print(_USAGE, file=sys.stderr)
            return 2
    except (ProjectError, IndexError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest():
    import tempfile

    root = tempfile.mkdtemp(prefix="autosound_project_")
    proj = Project(root)

    # a brand-new project reads as an empty skeleton, not an error -- and reading it does not
    # create the folder (the audit must not invent what it audits).
    unwritten = os.path.join(root, "never_written")
    empty = Project(unwritten).load()
    assert not os.path.exists(unwritten), unwritten
    assert empty["schema_version"] == SCHEMA_VERSION, empty
    assert empty["project_rev"] == 0, empty
    assert empty["channels"] == [] and empty["hardware"] == {"controls": {}}, empty

    # the CLI's own value parsing: nested JSON stays structured, and --source wraps a fact field.
    # (A live intake session wrote an inline Python script rather than use `set-channel`, because
    # a driver object came back as a literal string -- silent, and unreadable to every consumer.)
    kv = _parse_kv(['driver={"make":"Audiofrog","model":"GB25"}', "fs_hz=62", "descr=Front L"],
                    source="datasheet")
    assert kv["driver"] == {"make": "Audiofrog", "model": "GB25"}, kv
    assert fact_value(kv["fs_hz"]) == 62 and kv["fs_hz"]["source"] == "datasheet", kv
    assert kv["descr"] == "Front L", kv  # free text is not JSON and stays as typed

    # set_channel: SCR-001 driver facts, appended for an unknown code.
    proj.set_channel("w-L", slot="C", descr="Front L Woofer", role="woofer", order=1,
                      driver={"make": "Audiofrog", "model": "GB25"},
                      fs_hz=fact(62, source="datasheet"), impedance_ohm=4, hidden=False)
    proj.set_channel("vfr", slot="B", hidden=True)  # e.g. an unused virtual slot (SCR-003)
    data = proj.load()
    wl = next(c for c in data["channels"] if c["code"] == "w-L")
    assert wl["driver"] == {"make": "Audiofrog", "model": "GB25"}, wl
    assert fact_value(wl["fs_hz"]) == 62, wl
    assert wl["fs_hz"]["source"] == "datasheet", wl
    vfr = next(c for c in data["channels"] if c["code"] == "vfr")
    assert vfr["hidden"] is True, vfr

    # updating an existing code merges fields rather than duplicating the row.
    proj.set_channel("w-L", order=2)
    data = proj.load()
    assert len([c for c in data["channels"] if c["code"] == "w-L"]) == 1
    assert next(c for c in data["channels"] if c["code"] == "w-L")["order"] == 2

    # a duplicate code is refused (deterministic, same discipline as state.py/process.py).
    dup = proj.load()
    dup["channels"].append({"code": "w-L"})
    try:
        validate(dup)
        raise AssertionError("validate accepted a duplicate channel code")
    except ProjectError:
        pass

    # set_hardware_control: SCR-017 -- a DSP-level knob position, recorded ONCE, not per-preset.
    proj.set_hardware_control("RearRC", "3/4", source="user")
    proj.set_hardware_control("RealCenter", "ON", source="user")
    hw = proj.load()["hardware"]["controls"]
    assert fact_value(hw["RearRC"]) == "3/4" and hw["RearRC"]["source"] == "user", hw
    assert fact_value(hw["RealCenter"]) == "ON", hw

    # open_questions: a bare null field, PLUS a fact() wrapper whose value is still null.
    data = proj.load()
    data["mic"] = {"model": "UMIK-1", "calibration_file": None}
    data["amps"] = [{"role": "front", "gain_db": fact(None, source=None)}]
    proj.save(data)
    oq = open_questions(proj.load())
    assert "mic.calibration_file" in oq, oq
    assert "amps.0.gain_db" in oq, oq
    assert "mic.model" not in oq, "a filled fact must not be an open question"

    # record_change: lands in the SAME project's process journal (SCR-004), not a second log.
    process_dir = os.path.join(root, "process")
    proc = _load_process(process_dir)
    ev = proj.record_change(proc, "project.json", "swapped front woofer driver",
                             why="blown voice coil", source="user",
                             impact="remeasure: [w-L, w-R]")
    assert ev["type"] == "config_change", ev
    events = proc.events(kinds=["config_change"])
    assert events and events[-1]["what"] == "swapped front woofer driver", events
    assert events[-1]["impact"] == "remeasure: [w-L, w-R]", events

    # parse_impact: one reading of the field, so a consumer never invents a second one.
    assert Project.parse_impact("remeasure: [w-L, w-R]") == {
        "kind": "remeasure", "codes": ("w-L", "w-R"), "raw": "remeasure: [w-L, w-R]"}
    assert Project.parse_impact(IMPACT_NONE)["kind"] == "none"
    assert Project.parse_impact("")["kind"] == "none"
    assert Project.parse_impact(IMPACT_REBASELINE)["kind"] == "full_rebaseline"
    # `process.py::set_target` already writes this one, and a human writes prose -- neither is an
    # error, both are "a consumer cannot act on this automatically".
    voicing = Project.parse_impact("voicing")
    assert voicing["kind"] == "other" and voicing["raw"] == "voicing", voicing

    # unsupported schema_version is a deterministic refusal.
    bad = proj.load()
    bad["schema_version"] = 99
    try:
        validate(bad)
        raise AssertionError("validate accepted an unsupported schema_version")
    except ProjectError:
        pass

    print(f"selftest OK — channels[] round-tripped driver/fs_hz facts (SCR-001), duplicate code "
          f"refused, hardware.controls recorded ONCE not per-preset (SCR-017), open_questions "
          f"found a bare null + an unfilled fact() wrapper, record_change landed in the project's "
          f"own process journal. root={root}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(_selftest())
    raise SystemExit(_main(sys.argv))
