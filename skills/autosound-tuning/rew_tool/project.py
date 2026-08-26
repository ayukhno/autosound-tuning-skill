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


def channel_id(row):
    """The channel's STABLE identity (SCR-039) — `id` when the row has one, otherwise its `code`.

    `code` used to do three jobs at once: the ledger's row key, the join key between this file and
    a snapshot, and the label a human reads (and types into REW). That is fine until something is
    renamed for an ordinary reason — a `m-L` that turns out to be a woofer, a "rear" pair that is
    really a centre — at which point every historical snapshot is either rewritten (so much for
    immutable) or left keyed by a name nobody uses.

    The id splits identity from the name. **It defaults to today's code**, so no existing project
    changes and no file needs migrating: a project that never renames anything cannot tell the
    difference. The two only diverge after a rename, and then the ledger keeps keying on the id it
    always had while `code` carries the current name.

    Returns `""` for a row with neither, which callers treat the same way they already treat a row
    with no code: not captured, never guessed at.
    """
    row = row or {}
    return str(row.get("id") or row.get("code") or "")


def previous_names(row):
    """Every name this channel has been called before (SCR-039), oldest first.

    Load-bearing rather than sentimental: REW measurement titles are typed by a human and cannot
    be rewritten retroactively, so the captures a channel took under its old name are the only
    ones it has. A consumer matching titles to channels resolves through this list.
    """
    names = (row or {}).get("previous_names") or []
    return [str(n) for n in names if str(n).strip()]


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


def _validate_acoustics(data):
    """Every flaw in the map, on every write.

    `validate_flaw` existed and was called from `add_flaw` alone, so any other path to disk — a
    model editing the file, a merge, any load-modify-`save()` — banked whatever it liked. A dip
    marked `notch` with no `why` and no `evidence` passed three separate refusals by not going
    through them (found by audit, 2026-08-12), and TCC then coloured it "correctable".
    """
    flaws = ((data.get("acoustics") or {}).get("flaws")) or []
    if not isinstance(flaws, list):
        raise ProjectError(f"acoustics.flaws must be a list, got {type(flaws).__name__}")
    for index, entry in enumerate(flaws):
        try:
            validate_flaw(dict(entry) if isinstance(entry, dict) else entry)
        except (ProjectError, ValueError, TypeError) as exc:
            raise ProjectError(f"acoustics.flaws[{index}]: {exc}") from exc


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
            + (f" -- 2.x project. Migrate once:\n    python3 "
               f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state', 'migrate.py')}"
               f" <project-dir> --into <new-project-dir>"
               if isinstance(data.get("schema_version"), int)
               and data["schema_version"] < SCHEMA_VERSION else ""))
    rev = data.get("project_rev")
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 0:
        raise ProjectError(f"project_rev must be a non-negative int, got {rev!r}")
    for key in ("amps", "presets", "channels", "sources", "_open_questions"):
        if key in data and not isinstance(data[key], list):
            raise ProjectError(f"{key!r} must be a list")
    by_code, ids = {}, {}
    for ch in data.get("channels", []):
        if not isinstance(ch, dict) or not ch.get("code"):
            raise ProjectError(f"every channels[] entry needs a code, got {ch!r}")
        if ch["code"] in by_code:
            raise ProjectError(f"duplicate channel code {ch['code']!r}")
        by_code[ch["code"]] = ch
        if "previous_names" in ch and not isinstance(ch["previous_names"], list):
            raise ProjectError(
                f"channel {ch['code']!r}: previous_names must be a list of names, got "
                f"{ch['previous_names']!r}"
            )
        # `tier` is the LEDGER tier key (`dsp_profile.ledger_tier`), not the profile's group id:
        # `channels` for physical outputs, `virtual_channels`/`inputs`/... for the rest. Optional
        # (a project written before SCR-042 stays valid), but refused when spelled as the group id
        # — `physical_outputs` would match no tier and simply drop the row from every panel, which
        # is the silent failure this field exists to end.
        if "tier" in ch and ch["tier"] is not None:
            if not isinstance(ch["tier"], str) or not ch["tier"].strip():
                raise ProjectError(
                    f"channel {ch['code']!r}: tier must be a non-empty string (the ledger tier key "
                    f"this channel belongs to), got {ch['tier']!r}"
                )
            if ch["tier"] == "physical_outputs":
                raise ProjectError(
                    f"channel {ch['code']!r}: tier is the LEDGER key, so the physical-output tier "
                    "is spelled 'channels', not 'physical_outputs' (the profile's group id). See "
                    "dsp_profile.ledger_tier — SCR-042"
                )
        cid = channel_id(ch)
        if cid in ids:
            raise ProjectError(
                f"duplicate channel id {cid!r} (channels {ids[cid]!r} and {ch['code']!r}) — an id "
                "is what every snapshot and every historical capture is keyed on, so two channels "
                "sharing one would merge their histories (SCR-039)"
            )
        ids[cid] = ch["code"]
    # A previous name is a join key for captures taken before a rename, so it may not also be some
    # OTHER channel's live name — that is the one shape where a title genuinely cannot be resolved
    # (code swaps between two channels being the realistic way to get here). Checked in a second
    # pass because the collision can point forward as easily as back.
    for ch in data.get("channels", []):
        for old in previous_names(ch):
            if old == ch["code"]:
                raise ProjectError(
                    f"channel {ch['code']!r} lists its own current code as a previous name"
                )
            if by_code.get(old) not in (None, ch):
                raise ProjectError(
                    f"channel {ch['code']!r} lists {old!r} as a previous name, but {old!r} is the "
                    "current code of another channel — a capture titled with it could belong to "
                    "either (SCR-039)"
                )
    if "hardware" in data and not isinstance(data["hardware"], dict):
        raise ProjectError("hardware must be an object")
    if "glossary" in data and not isinstance(data["glossary"], dict):
        raise ProjectError("glossary must be an object")
    _validate_acoustics(data)
    return data


# What a flaw IS. A closed list because a front-end colours by it and a model picks from it: free
# text here would be a field nobody can render and everybody words differently.
#: Time-domain INSTALL properties. Added 2026-08-22 because the map had no row shape for one and
#: the finding went into prose instead -- exactly what SCR-015 exists to prevent (inbox 3.12). The
#: case: one door's energy lags its own wavefront by ~1.1 ms relative to the other. That is a real,
#: measured property of the install and the time-domain face of anomalies already in the map as
#: frequency rows -- but every other `kind` is a frequency feature and `f_hz` is required, so there
#: was nowhere to put it that was not a lie.
#:
#: These rows carry `t_ms` instead of `level_db`, and `f_hz` is OPTIONAL (a lag may or may not be
#: confined to a band). ⚠️ A consumer that assumes every flaw has `f_hz` and `level_db` must skip
#: these -- check the kind, not the field.
TIME_DOMAIN_KINDS = ("energy_lag", "ringing", "decay_asymmetry")
FLAW_KINDS = (
    "room_gain", "modal_peak", "cabin_null", "sbir", "floor_bounce",
    "driver_resonance", "non_min_phase", "thd_spike", "pair_suckout",
) + TIME_DOMAIN_KINDS
# What may be DONE about it -- the load-bearing half. Closed for the same reason, and because the
# whole point of writing the map down is that "don't EQ-boost this null" survives the session that
# discovered it.
FLAW_ACTIONS = ("notch", "leave", "no_boost", "geometry", "delay", "crossover")
#: How sure we are. A tune generates suspicions constantly and they had nowhere to go: the
#: PART B pair-coherence findings on the live project sat in prose for a week, explicitly marked
#: "measured before TA, re-check afterwards", because recording them as facts would have been a
#: lie and there was no third option (user, 2026-08-12).
#:
#: Absent means `confirmed` — every map written before this field existed was written as fact, and
#: rewriting history to say otherwise would be its own lie.
FLAW_STATUSES = ("hypothesis", "confirmed")
DEFAULT_FLAW_STATUS = "confirmed"


def flaw_status(entry):
    """This flaw's status, defaulting for the files that predate the field."""
    return (entry or {}).get("status") or DEFAULT_FLAW_STATUS


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
    time_domain = entry.get("kind") in TIME_DOMAIN_KINDS
    f = entry.get("f_hz")
    if time_domain:
        # `f_hz` optional: an energy lag may be broadband. If given it still has to be a frequency.
        if f is not None and (not isinstance(f, (int, float)) or isinstance(f, bool) or f <= 0):
            raise ProjectError(f"f_hz, when given, must be a positive Hz, got {f!r}")
        t = entry.get("t_ms")
        if not isinstance(t, (int, float)) or isinstance(t, bool):
            raise ProjectError(
                f"a {entry['kind']} needs `t_ms` — the measured time, signed, and signed against "
                f"the channel named in `channels` (+ later, - earlier). It is the whole content of "
                f"a time-domain row; `level_db` does not describe it (got {t!r})"
            )
        if entry.get("level_db") is not None and not isinstance(entry["level_db"], (int, float)):
            raise ProjectError("level_db, when given on a time-domain row, must be a number")
    else:
        if not isinstance(f, (int, float)) or isinstance(f, bool) or f <= 0:
            raise ProjectError(f"f_hz must be a positive Hz, got {f!r}")
        level = entry.get("level_db")
        if not isinstance(level, (int, float)) or isinstance(level, bool):
            raise ProjectError(
                f"level_db must be a number: the FEATURE, signed — + a hump, - a dip. Not the "
                f"correction you would apply to it (got {level!r})"
            )
        if entry.get("t_ms") is not None:
            raise ProjectError(
                f"t_ms belongs to a time-domain kind ({', '.join(TIME_DOMAIN_KINDS)}), not to "
                f"{entry.get('kind')!r}"
            )
    if entry.get("kind") not in FLAW_KINDS:
        raise ProjectError(
            f"kind must be one of {', '.join(FLAW_KINDS)} (got {entry.get('kind')!r})"
        )
    if entry.get("action") not in FLAW_ACTIONS:
        raise ProjectError(
            f"action must be one of {', '.join(FLAW_ACTIONS)} (got {entry.get('action')!r})"
        )
    level = entry.get("level_db")
    if isinstance(level, (int, float)) and not isinstance(level, bool) \
            and level < 0 and entry.get("action") == "notch":
        raise ProjectError(
            f"{f:g} Hz is a dip ({level:g} dB) and cannot be notched: a null is interference, not "
            "minimum-phase — cutting it changes nothing and boosting it burns headroom against "
            "physics. Use `leave`/`no_boost`, or `geometry`/`delay`/`crossover` if the fix is one "
            "of those. If you meant a HUMP you intend to cut, `level_db` is the feature itself "
            f"({abs(level):g}, positive), not the correction you would apply to it."
        )
    if entry.get("status") is not None and entry["status"] not in FLAW_STATUSES:
        raise ProjectError(
            f"status must be one of {', '.join(FLAW_STATUSES)} or absent (got "
            f"{entry.get('status')!r}). Absent means {DEFAULT_FLAW_STATUS}."
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


#: Top-level ledger keys that hold metadata rather than a tier of rows. Mirrored from
#: `state/state.py`'s own list rather than imported, for the same reason `EVENT_CONFIG_CHANGE` is:
#: one constant is not worth a cross-directory import. A dict-of-dicts under any OTHER key is a
#: tier (`state.tier_names`).
_LEDGER_NON_TIERS = ("roles", "provenance", "virtual_eq_ptr", "banked_ear_verdicts")


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
        """The current facts, or an empty skeleton if this project has none yet.

        **A file that exists and cannot be read is NOT "nothing known".** Both used to return the
        skeleton, and that is data loss with extra steps: every mutator here is load-modify-save,
        so one `set_channel` against an unreadable file wrote the skeleton over it — the whole
        project replaced by an empty one, `project_rev` back to 1, no error anywhere (found by
        audit and reproduced, 2026-08-12). Atomic writes never protected against this; the write
        was perfectly atomic and perfectly wrong.

        A brand-new folder still reads as "nothing known", because that is true.
        """
        if not os.path.isfile(self.path):
            return _empty_project()
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            raise ProjectError(
                f"{self.path} exists and cannot be read: {exc}. Refusing to treat it as an empty "
                "project — the next write would replace it. Fix or move the file; a copy of the "
                "last good one may be in your editor's backups or in git."
            ) from exc
        if not isinstance(data, dict):
            raise ProjectError(
                f"{self.path} is valid JSON but not an object ({type(data).__name__}). Refusing "
                "to treat it as an empty project — the next write would replace it."
            )
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

    def migrate_fields(self, write=True):
        """Rename legacy field names in `project.json` (`rename_legacy_fields`); a dry run writes nothing."""
        data = self.load()
        renames = rename_legacy_fields(data)
        if renames and write:
            self.save(data)
        return renames

    def backfill_tiers(self, state_root=None, write=True):
        """Write `tier` onto every channel the LEDGER already places. Reads, never guesses.

        `tier` was introduced for spare slots (SCR-042), because a spare has no ledger row and so
        nothing else says which tier it is spare OF. A WORKING channel was left to be placed by its
        ledger row's tier key — and that was the split applied inconsistently rather than a
        boundary. A channel's tier cannot change between snapshots: no amount of tuning moves
        `w-L` from an output to a virtual channel. By schema v3's own test — the ledger holds what
        differs between two snapshots, `project.json` holds identity — tier is identity, for a
        working channel exactly as much as for a spare.

        What that cost, found by `autosound-tcc` on a real seeded project (2026-08-23): a project
        seeded from a fully described car has 20 channels and no ledger yet, so with the tier
        living only in ledger keys, not one working channel could be placed and the rig panel drew
        empty. A car that is completely described looked like no car at all.

        The fill is not a guess and must never become one. Every tier written here is READ from the
        ledger's own row keys — the source that is authoritative today. A channel with no row and
        no `tier` stays unplaced, which is honest: `role` would place most of them (`virtual`, or
        the presence of a driver) and that is precisely the inference this schema refuses, because
        slot letters repeat across tiers and a wrong placement is invisible once written.

        Returns `{code: tier}` for what was filled (or would be, when `write` is false).
        """
        import glob as _glob

        data = self.load()
        rows = [r for r in (data.get("channels") or []) if isinstance(r, dict)]
        by_key = {}
        root = state_root or os.path.join(self.dir, "state")
        for path in sorted(_glob.glob(os.path.join(root, "*", "v_*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    snap = json.load(f)
            except (OSError, ValueError):
                continue
            for tier, tier_rows in snap.items():
                if tier in _LEDGER_NON_TIERS or not isinstance(tier_rows, dict):
                    continue
                if not all(isinstance(v, dict) for v in tier_rows.values()):
                    continue
                for key in tier_rows:
                    by_key[key] = tier

        filled = {}
        for row in rows:
            if row.get("tier"):
                continue
            # The ledger keys on the channel's ID, which defaults to its code (SCR-039), so both
            # are tried — and a renamed channel resolves through neither, which is why
            # `previous_names` is consulted too rather than leaving it unplaced.
            for name in [row.get("code"), channel_id(row), *previous_names(row)]:
                if name and name in by_key:
                    filled[row["code"]] = by_key[name]
                    break
        if write and filled:
            for row in rows:
                if row["code"] in filled:
                    row["tier"] = filled[row["code"]]
            self.save(data)
        return filled


    def set_channel(self, code, **fields):
        """Add or update one `channels[]` row by `code` (SCR-001) — `slot`/`descr`/`role`/`order`/
        `tier`/`driver`/`fs_hz`/`impedance_ohm`/`hidden`, whatever the caller has; wrap
        `fact()`-worthy fields (e.g. `fs_hz`) before calling. An unknown code is appended, not
        refused — intake builds this list one confirmed fact at a time.

        `tier` (SCR-042) is the ledger tier key this channel belongs to — `channels` for a physical
        output, `virtual_channels`/`inputs`/… for the rest; `dsp_profile.ledger_tier()` converts a
        profile group id to it. Cheap for a channel that has a ledger row (it is the key that row
        already sits under) and load-bearing for one that does not: an unused slot has no tuning
        state, so `tier` is the only thing that says which tier it is a spare slot OF. It cannot be
        inferred, because slot letters repeat across tiers — on a Helix the virtual tier runs A–H
        and the outputs B–K, so `slot: "F"` is a legal address in both, and a guess would file a
        spare output among the virtual channels. `role: "virtual"` is not a substitute: an unused
        virtual slot is written `role: "unused"`, which is what loses the tier in the first place.

        A name the channel used to have resolves to the same row (SCR-039) rather than appending a
        second one: the caller is as often a language model working from a stale context as it is
        intake, and "record this driver against m-L" after m-L became w-L means the woofer, not a
        new channel."""
        data = self.load()
        rows = data.setdefault("channels", [])
        row = self.resolve_channel(code, data)
        if row is None:
            row = {"code": code}
            rows.append(row)
        row.update(fields)
        return self.save(data)

    def resolve_channel(self, name, data=None):
        """The `channels[]` row a name or id refers to — including a name it used to have (SCR-039).

        The whole point of the id/name split, from a consumer's side. Three lookups, in a fixed
        order so the answer never depends on row order: current `code` first (what a person means
        today), then `id` (what the ledger and every snapshot key on), then `previous_names` (what
        an old REW title says). `None` when nothing matches — an unknown code is not this module's
        to invent.

        Current-code-before-id matters in exactly one case: A was renamed to B's old name. Then
        "B" is A's live code and someone else's dead id, and the live name is the one a human
        typing it today means.
        """
        rows = (data or self.load()).get("channels") or []
        rows = [r for r in rows if isinstance(r, dict)]
        for match in (lambda r: r.get("code") == name,
                      lambda r: channel_id(r) == name,
                      lambda r: name in previous_names(r)):
            row = next((r for r in rows if match(r)), None)
            if row is not None:
                return row
        return None

    def rename_channel(self, old, new, data=None):
        """Give one channel a new name, keeping its identity and its history (SCR-039).

        What actually happens: the row's `id` is materialised (it was implicitly the old code all
        along), `code` becomes the new name, and the old name joins `previous_names`. The ledger is
        NOT touched — its row keys are ids, so every snapshot ever taken stays valid and immutable,
        which is the entire reason this exists. Neither are REW titles, which cannot be rewritten
        anyway; they resolve through `previous_names` from here on.

        The glossary entry (`glossary.channels[]`, keyed by the same name — `naming.Glossary`) is
        renamed in step, since a title generated tomorrow should carry the new name. Renaming to a
        name already in use is refused rather than merged: two channels' histories are not one.

        Returns the updated row. The caller decides whether this deserves a `config_change` event
        (`record_change`) — a rename corrects a label, so its `impact` is normally `none`: no
        measurement is invalidated, they simply carry the old name.
        """
        data = data or self.load()
        row = self.resolve_channel(old, data)
        if row is None:
            raise ProjectError(f"no channel {old!r} to rename")
        if not str(new or "").strip():
            raise ProjectError("a channel needs a name to be renamed to")
        new = str(new).strip()
        if new == row.get("code"):
            return row
        clash = self.resolve_channel(new, data)
        if clash is not None and clash is not row:
            raise ProjectError(
                f"cannot rename {row['code']!r} to {new!r}: that name is already "
                f"{'in use' if clash.get('code') == new else 'the history of another channel'} "
                f"(channel {clash.get('code')!r})"
            )
        was = str(row.get("code"))
        row.setdefault("id", channel_id(row))
        row["code"] = new
        history = [n for n in previous_names(row) if n != new]
        if was not in history:
            history.append(was)
        row["previous_names"] = history
        for entry in (data.get("glossary") or {}).get("channels") or []:
            if isinstance(entry, dict) and entry.get("code") == was:
                entry["code"] = new
                # The glossary carries its own copy of the history because it is also read
                # standalone (`glossary.json`, `naming.Glossary.for_project`), where `channels[]`
                # is not there to consult — and it is the glossary that has to recognise the old
                # name in an existing REW title.
                seen = [n for n in (entry.get("previous_names") or []) if n != new]
                if was not in seen:
                    seen.append(was)
                entry["previous_names"] = seen
        self.save(data)
        return row

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
        # Identity of a row: its position plus who it is about. For a frequency feature that is
        # the frequency; a time-domain row may have no frequency at all, so it is keyed by its
        # KIND instead -- one energy_lag per channel set, which is what such a property is.
        # (Found by the new time-domain rows walking straight into `entry["f_hz"]` here: the
        # comment on TIME_DOMAIN_KINDS warns consumers about exactly this, and the first consumer
        # to trip over it was this file.)
        def _key(e):
            who = tuple(sorted(e.get("channels") or []))
            if e.get("kind") in TIME_DOMAIN_KINDS:
                return ("kind", e.get("kind"), who)
            f_hz = e.get("f_hz")
            return ("f", round(float(f_hz), 1) if f_hz is not None else None, who)

        key = _key(entry)
        for i, existing in enumerate(list(flaws)):
            same = _key(existing)
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



def _rate_keys():
    """(canonical, legacy) names of the DSP's PROCESSING rate, from the module that owns them.

    Lazy for the same reason as `_process_for`: this file is imported from `state/migrate.py` and
    by consumers that load it by path, and `dsp_profile.py` lives beside it, not on their path.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import dsp_profile as _dsp_profile  # noqa: E402
    return _dsp_profile.PROCESSING_RATE_KEY, _dsp_profile.LEGACY_RATE_KEY


def rename_legacy_fields(data):
    """Move `dsp.sample_rate_hz` to `dsp.dsp_processing_rate_hz` in a project dict; return renames.

    ONLY the `dsp` block. `measurement.*` / `mic.*` carry the CAPTURE rate -- a different fact that
    keeps its name (two rates, one name each, 2026-08-25). Both keys present with different values
    are two answers to one question: refuse, do not pick. `dsp_profile.json` is renamed by its own
    reader on save; this is the project file's half, which no tool covered until a live project's
    copy showed `state/migrate.rename_profile_fields` returning [] on it (2026-08-26).
    """
    canonical, legacy = _rate_keys()
    dsp = data.get("dsp")
    if not isinstance(dsp, dict) or legacy not in dsp:
        return []
    if (dsp.get(canonical) is not None and dsp[legacy] is not None
            and dsp[canonical] != dsp[legacy]):
        raise ProjectError(
            f"project.json dsp carries both {canonical}={dsp[canonical]!r} and "
            f"{legacy}={dsp[legacy]!r} with different values -- two answers to one question; "
            f"settle it by hand, nothing was written")
    if dsp.get(canonical) is None:
        dsp[canonical] = dsp[legacy]
    del dsp[legacy]
    return [f"dsp.{legacy} -> dsp.{canonical}"]

# --------------------------------------------------------------------------- CLI
_USAGE = """usage: project.py <project-dir> <command> [args]

  show                                         print project.json (or an empty skeleton)
  open-questions                               list unresolved facts (dotted paths)
  migrate-fields [--dry-run]                   rename legacy field names in project.json
                                               (`dsp.sample_rate_hz` -> `dsp.dsp_processing_rate_hz`;
                                               `measurement`/`mic` rates are the CAPTURE rate and
                                               keep their name)
  backfill-tiers [--dry-run]                   write `tier` onto every channel the LEDGER
                                               already places — READ from its row keys,
                                               never inferred. A channel with no row and
                                               no tier stays unplaced rather than guessed
  set-channel <code> [key=value ...]           add/update one channels[] row
      [--source S]                             values are JSON when they parse as JSON, so
                                               driver={"make":"Audiofrog","model":"GB25"} works;
                                               --source wraps fs_hz as a fact()
  rename-channel <old> <new>                   rename a channel, keeping its identity and its
                                               captures (SCR-039). <old> may be a name it used
                                               to have; snapshots are not rewritten
  set-hardware <name> <value> [--source S]     set a DSP-hardware control (RearRC/SubRC/...)
  record-change <process-dir> <file> <what>    log a config_change journal event
      [--why W] [--source S] [--impact I]
  flaw <f_hz> <level_db> <kind> <action> [--status hypothesis]
  flaw --t-ms <ms> <kind> <action>       a TIME-domain install property (energy_lag,
                                         ringing, decay_asymmetry): no frequency, no dB
                                               add/replace an acoustic-flaw entry (SCR-015).
                                               A hypothesis is a finding not yet settled — say so
                                               rather than banking it as fact or losing it to prose
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
        elif cmd == "migrate-fields":
            renames = proj.migrate_fields(write="--dry-run" not in args)
            if not renames:
                print("nothing to rename — project.json already uses the canonical names")
            for line in renames:
                print(("would rename " if "--dry-run" in args else "renamed ") + line)
        elif cmd == "backfill-tiers":
            filled = proj.backfill_tiers(write="--dry-run" not in args)
            if not filled:
                print("nothing to fill — every channel with a ledger row already names its tier")
            else:
                for code, tier in sorted(filled.items()):
                    print(f"  {code} -> {tier}")
                print(("would fill " if "--dry-run" in args else "filled ")
                      + f"{len(filled)} channel(s) from the ledger's own row keys")
            # Exclude what was (or would be) filled: on a dry run the file is unchanged, so
            # reading it back would list the very channels just reported as fillable.
            unplaced = [c["code"] for c in (proj.load().get("channels") or [])
                        if isinstance(c, dict) and not c.get("tier")
                        and c.get("code") not in filled]
            if unplaced:
                print(f"still unplaced (no ledger row, no tier — NOT guessed): "
                      f"{', '.join(unplaced)}")
        elif cmd == "set-channel":
            source = _flag(args, "--source")
            code, kv = args[0], _parse_kv(args[1:], source=source)
            proj.set_channel(code, **kv)
            print(f"channel {code} updated")
        elif cmd == "rename-channel":
            old, new = args[0], args[1]
            # The name it goes by BEFORE the call, so a no-op doesn't report a rename that never
            # happened (`rename-channel w-L w-L` is a plausible thing to type twice).
            was = (proj.resolve_channel(old) or {}).get("code")
            row = proj.rename_channel(old, new)
            if was == row["code"]:
                print(f"channel {row['code']} already goes by that name — nothing written")
            else:
                print(f"channel {was} is now {row['code']} (id {channel_id(row)}, unchanged) — "
                      f"snapshots and existing captures keep the old name and still resolve")
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
            t_ms = _flag(args, "--t-ms")
            # A time-domain row has no frequency and no dB, so it cannot use the positional form:
            #   flaw --t-ms 1.1 energy_lag geometry --channels m-L --why … --evidence …
            if t_ms is not None:
                entry = proj.add_flaw(
                    kind=args[0], action=args[1], t_ms=float(t_ms),
                    channels=[c.strip() for c in channels.split(",") if c.strip()],
                    why=why,
                    evidence=[e.strip() for e in evidence.split(",") if e.strip()],
                )
                mark = ("" if flaw_status(entry) == DEFAULT_FLAW_STATUS
                        else f" ({flaw_status(entry)})")
                print(f"{entry['t_ms']:+g} ms [{entry['kind']}]{mark} -> {entry['action']}")
                return 0
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
            mark = "" if flaw_status(entry) == DEFAULT_FLAW_STATUS else f" ({flaw_status(entry)})"
            print(f"{entry['f_hz']:g} Hz{width} {entry['level_db']:+g} dB "
                  f"[{entry['kind']}]{mark} -> {entry['action']}")
        elif cmd == "flaws":
            for entry in proj.flaws():
                width = f" Q{entry['q']:g}" if entry.get("q") else (
                    f" {entry['bw_oct']:g}oct" if entry.get("bw_oct") else "")
                who = ", ".join(entry.get("channels") or []) or "—"
                if entry.get("kind") in TIME_DOMAIN_KINDS:
                    where = "broadband" if entry.get("f_hz") is None else f"{entry['f_hz']:.6g} Hz"
                    print(f"{where:>10}{'':>8} {entry['t_ms']:+6g} ms  "
                          f"{entry['kind']:<16} {entry['action']:<10} {who:<12} "
                          f"{entry.get('why','')}")
                    continue
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

    # -- a finding that is not settled yet says so (2026-08-12) --------------------------------
    # A tune generates suspicions constantly. The pair-coherence findings on a live project sat in
    # prose for a week -- "measured before TA, re-check afterwards" -- because banking them as
    # fact would have been a lie and there was no third option.
    status_root = tempfile.mkdtemp(prefix="autosound_project_status_")
    sp = Project(status_root)
    sp.add_flaw(f_hz=175, level_db=-31.7, kind="pair_suckout", action="leave",
                channels=["w-L", "w-R"], status="hypothesis",
                why="raw _01 coherence, before any TA -- re-check after alignment",
                evidence=["Ws pair coherence 40-500 Hz"])
    sp.add_flaw(f_hz=152, level_db=-12, kind="cabin_null", action="no_boost", channels=["w-L"],
                why="settled by absolute harmonic SPL", evidence=["w-L_01 (sw)"])
    got = {f["f_hz"]: flaw_status(f) for f in sp.flaws()}
    assert got == {175.0: "hypothesis", 152.0: "confirmed"}, got
    # Absent means confirmed: a map written before the field existed was written as fact, and
    # re-labelling history would be its own lie.
    assert flaw_status({"f_hz": 1}) == DEFAULT_FLAW_STATUS
    try:
        sp.add_flaw(f_hz=90, level_db=-3, kind="cabin_null", action="leave", status="maybe",
                    why="x", evidence=["y"])
        raise AssertionError("add_flaw accepted a status outside the list")
    except ProjectError as exc:
        assert "hypothesis" in str(exc), exc

    # -- time-domain install properties (inbox 3.12) -------------------------------------------
    # The row shape that did not exist: one door's energy lagging the other's is a real install
    # property with no frequency and no dB, and it went into prose because every kind was a
    # frequency feature. f_hz optional, t_ms required, level_db not applicable.
    sp.add_flaw(kind="energy_lag", action="geometry", t_ms=1.1, channels=["m-L"],
                why="left door's energy lags its own wavefront vs the right; four pair-delay "
                    "estimators spread 4.3 ms with a sign flip between two of them",
                evidence=["m-L_1 (sw)", "m-R_1 (sw)"])
    lag = [f for f in sp.flaws() if f["kind"] == "energy_lag"]
    assert len(lag) == 1 and lag[0]["t_ms"] == 1.1, lag
    assert lag[0].get("f_hz") is None, "a broadband lag must not be forced to invent a frequency"
    try:
        sp.add_flaw(kind="energy_lag", action="geometry", why="x", evidence=["y"])
        raise AssertionError("a time-domain row was accepted with no t_ms")
    except ProjectError as exc:
        assert "t_ms" in str(exc), exc
    try:
        sp.add_flaw(f_hz=109, level_db=-6, kind="cabin_null", action="leave", t_ms=1.1,
                    why="x", evidence=["y"])
        raise AssertionError("t_ms was accepted on a frequency-domain kind")
    except ProjectError as exc:
        assert "time-domain" in str(exc), exc
    # A frequency-domain row still needs both, exactly as before.
    try:
        sp.add_flaw(kind="cabin_null", action="leave", why="x", evidence=["y"])
        raise AssertionError("a frequency row was accepted with no f_hz")
    except ProjectError as exc:
        assert "f_hz" in str(exc), exc

    # -- the flaw map is validated on every write, not only by add_flaw (2026-08-12) -----------
    # `validate_flaw` was called from `add_flaw` alone, so any other path to disk banked whatever
    # it liked: a dip marked notchable, with no `why` and no `evidence`, passed three refusals by
    # not going through them -- and the consumer then coloured it "correctable".
    flawed_root = tempfile.mkdtemp(prefix="autosound_project_flaws_")
    flawed = Project(flawed_root)
    bad_map = {"schema_version": SCHEMA_VERSION, "project_rev": 1,
               "acoustics": {"flaws": [{"f_hz": 250, "level_db": -12, "kind": "cabin_null",
                                        "action": "notch", "channels": ["w-R"]}]}}
    try:
        flawed.save(dict(bad_map))
        raise AssertionError("save() banked a dip recorded as notchable")
    except ProjectError as exc:
        assert "notch" in str(exc) or "0" in str(exc), exc
    assert not os.path.isfile(flawed.path), "a refused save must not have written anything"

    # -- an unreadable project.json is not an empty one ----------------------------------------
    # Every mutator here is load-modify-save, so returning the skeleton for a file that exists and
    # failed to parse meant one `set_channel` replaced the whole project -- atomically, silently,
    # `project_rev` back to 1. Reproduced before fixing (2026-08-12).
    broken_root = tempfile.mkdtemp(prefix="autosound_project_broken_")
    broken_path = os.path.join(broken_root, "project.json")
    with open(broken_path, "w") as f:
        f.write('{"schema_version": 3, "channels": [ {"code": "w-L"} ,,, ]}')
    before = open(broken_path).read()
    broken = Project(broken_root)
    for what, call in (("load", broken.load),
                       ("set_channel", lambda: broken.set_channel("w-R", tier="channels"))):
        try:
            call()
            raise AssertionError(f"{what} accepted an unreadable project.json")
        except ProjectError:
            pass
    assert open(broken_path).read() == before, "the write must not have touched the file"
    # Valid JSON that is not an object is the same danger by another route.
    with open(broken_path, "w") as f:
        f.write('["not", "an", "object"]')
    try:
        broken.load()
        raise AssertionError("load accepted a JSON array as a project")
    except ProjectError:
        pass
    # ...while a folder with no project.json at all still reads as "nothing known", because it is.
    assert Project(tempfile.mkdtemp()).load().get("channels") == []

    # -- tier is identity for EVERY channel, not only spares (2026-08-23, autosound-tcc).
    # A project seeded from a fully described car has no ledger yet, so with the tier living only
    # in ledger row keys not one working channel could be placed and the rig panel drew empty:
    # a completely described car looked like no car at all.
    tier_root = tempfile.mkdtemp(prefix="autosound_project_tiers_")
    tproj = Project(tier_root)
    tproj.save({"channels": [{"code": "w-L"}, {"code": "VFL"}, {"code": "c"},
                             {"code": "off-x", "role": "unused", "tier": "channels"}]})
    ledger = os.path.join(tier_root, "state", "SQ")
    os.makedirs(ledger, exist_ok=True)
    with open(os.path.join(ledger, "v_001.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 3, "preset": "SQ", "sample_rate": 96000,
                   "roles": {"artist": "x"},                       # metadata, NOT a tier
                   "channels": {"w-L": {"gain_db": 0}},
                   "virtual_channels": {"VFL": {"gain_db": 0}}}, f)

    filled = tproj.backfill_tiers(write=False)
    assert filled == {"w-L": "channels", "VFL": "virtual_channels"}, filled
    # `roles` is a dict but metadata, not a tier -- reading it as one would invent a tier named
    # "roles" and place a channel into it.
    assert "roles" not in filled.values(), filled
    # `c` has no ledger row, so it stays UNPLACED. `role` would place most channels and that is
    # exactly the inference this schema refuses: slot letters repeat across tiers, so a wrong
    # placement is invisible once written.
    assert "c" not in filled, "a channel with no row must not be guessed into a tier"
    assert not any(ch.get("tier") for ch in tproj.load()["channels"]
                   if ch["code"] == "w-L"), "write=False must not write"

    tproj.backfill_tiers()
    got = {ch["code"]: ch.get("tier") for ch in tproj.load()["channels"]}
    assert got == {"w-L": "channels", "VFL": "virtual_channels", "c": None,
                   "off-x": "channels"}, got
    assert tproj.backfill_tiers() == {}, "idempotent -- a filled tier is not refilled"
    # An already-stated tier is never overwritten from the ledger: project.json is identity's home.
    tproj.set_channel("c", tier="virtual_channels")
    assert tproj.backfill_tiers() == {}, "a stated tier wins over anything the ledger implies"

    # -- SCR-042: a spare slot says which tier it is spare OF. The case that motivated it: slot
    # letters repeat across tiers, so these two are both legal "F" and only `tier` tells them apart.
    proj.set_channel("off-out-F", slot="F", hidden=True, role="unused", tier="channels")
    proj.set_channel("off-virt-F", slot="F", hidden=True, role="unused", tier="virtual_channels")
    data = proj.load()
    spares = {c["code"]: c for c in data["channels"] if c.get("role") == "unused"}
    assert spares["off-out-F"]["tier"] == "channels", spares
    assert spares["off-virt-F"]["tier"] == "virtual_channels", spares
    assert spares["off-out-F"]["slot"] == spares["off-virt-F"]["slot"] == "F", spares

    # the profile's group id is NOT the ledger key, and the wrong spelling must not round-trip:
    # it would match no tier and the row would vanish from every panel without a word.
    wrong = proj.load()
    next(c for c in wrong["channels"] if c["code"] == "off-out-F")["tier"] = "physical_outputs"
    try:
        validate(wrong)
        raise AssertionError("validate accepted the profile group id as a channels[] tier")
    except ProjectError as exc:
        assert "channels" in str(exc), exc

    # an empty/non-string tier is refused too; a project written before SCR-042 (no tier at all)
    # stays valid -- the field is additive, not a migration.
    blank = proj.load()
    next(c for c in blank["channels"] if c["code"] == "off-out-F")["tier"] = "  "
    try:
        validate(blank)
        raise AssertionError("validate accepted a blank tier")
    except ProjectError:
        pass
    legacy = proj.load()
    for c in legacy["channels"]:
        c.pop("tier", None)
    validate(legacy)  # must not raise

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

    # -- SCR-039: a channel's id is not its name. Its own project, so a rename here cannot quietly
    # change what the assertions above and below are talking about.
    ren = Project(os.path.join(root, "rename"))
    ren.set_channel("m-L", slot="C", descr="Front L Mid", role="mid")
    ren.set_channel("tw-L", slot="D")
    before = ren.load()
    # id defaults to the code, so a project that never renames anything is byte-identical to one
    # written before this existed -- the point of the whole design (no fourth format break).
    assert "id" not in next(c for c in before["channels"] if c["code"] == "m-L"), before
    assert channel_id({"code": "m-L"}) == "m-L"
    assert channel_id({"code": "w-L", "id": "m-L"}) == "m-L"

    row = ren.rename_channel("m-L", "w-L")
    assert row["code"] == "w-L", row
    assert channel_id(row) == "m-L", "the id is what the ledger keys on; a rename must not move it"
    assert previous_names(row) == ["m-L"], row
    assert row["descr"] == "Front L Mid", "a rename is a label change, not a new channel"

    # all three lookups reach the same row -- current name, id, and the name REW titles still carry.
    assert ren.resolve_channel("w-L") is not None
    assert ren.resolve_channel("m-L")["code"] == "w-L", "an old capture's code must still resolve"
    assert ren.resolve_channel("nope") is None
    # and a write addressed to the old name updates it rather than appending a second channel.
    ren.set_channel("m-L", impedance_ohm=4)
    assert len(ren.load()["channels"]) == 2, ren.load()["channels"]
    assert ren.resolve_channel("w-L")["impedance_ohm"] == 4

    # renaming onto a name in use would merge two histories; renaming back is fine.
    try:
        ren.rename_channel("w-L", "tw-L")
        raise AssertionError("rename_channel accepted a name already in use")
    except ProjectError:
        pass
    ren.rename_channel("w-L", "m-L")
    back = ren.resolve_channel("m-L")
    assert back["code"] == "m-L" and channel_id(back) == "m-L", back
    assert previous_names(back) == ["w-L"], back
    ren.rename_channel("m-L", "w-L")  # leave it renamed for the glossary check below

    # the glossary follows the rename: a title generated tomorrow carries the new name.
    g = ren.load()
    g["glossary"] = {"channels": [{"code": "w-L", "active": True}, {"code": "tw-L", "active": True}]}
    ren.save(g)
    ren.rename_channel("w-L", "wf-L")
    codes = [c["code"] for c in ren.load()["glossary"]["channels"]]
    assert codes == ["wf-L", "tw-L"], codes

    # a previous name that is ANOTHER channel's live code is refused: a capture titled with it
    # could belong to either, and the map exists to make that join unambiguous.
    bad = ren.load()
    next(c for c in bad["channels"] if c["code"] == "tw-L")["previous_names"] = ["wf-L"]
    try:
        validate(bad)
        raise AssertionError("validate accepted a previous name that is another channel's code")
    except ProjectError:
        pass
    # as is a duplicate id -- two channels sharing one would merge their snapshots.
    bad = ren.load()
    for c in bad["channels"]:
        c["id"] = "same"
    try:
        validate(bad)
        raise AssertionError("validate accepted a duplicate channel id")
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

    # migrate-fields: the DSP block's legacy rate name moves, the CAPTURE rate keeps its name, a
    # dry run writes nothing, a re-run renames nothing, and two different values are refused.
    mroot = tempfile.mkdtemp(prefix="autosound_project_mig_")
    mproj = Project(mroot)
    mdata = mproj.load()
    mdata["dsp"] = {"vendor": "V", "model": "M", "sample_rate_hz": 96000}
    mdata["measurement"] = {"sample_rate_hz": 48000}
    mproj.save(mdata)
    rev_before = mproj.load()["project_rev"]
    assert mproj.migrate_fields(write=False) == ["dsp.sample_rate_hz -> dsp.dsp_processing_rate_hz"]
    assert mproj.load()["project_rev"] == rev_before, "dry run wrote"
    assert "sample_rate_hz" in mproj.load()["dsp"], "dry run renamed on disk"
    assert mproj.migrate_fields() == ["dsp.sample_rate_hz -> dsp.dsp_processing_rate_hz"]
    after = mproj.load()
    assert after["dsp"] == {"vendor": "V", "model": "M", "dsp_processing_rate_hz": 96000}, after["dsp"]
    assert after["measurement"] == {"sample_rate_hz": 48000}, after["measurement"]
    assert after["project_rev"] == rev_before + 1, after["project_rev"]
    assert mproj.migrate_fields() == [], "re-run renamed again"
    conflict = mproj.load()
    conflict["dsp"]["sample_rate_hz"] = 48000
    mproj.save(conflict)
    try:
        mproj.migrate_fields()
        raise AssertionError("two different rates were not refused")
    except ProjectError as exc:
        assert "two answers" in str(exc), exc
    assert mproj.load()["dsp"]["sample_rate_hz"] == 48000, "refusal wrote"

    # unsupported schema_version is a deterministic refusal.
    bad = proj.load()
    bad["schema_version"] = 99
    try:
        validate(bad)
        raise AssertionError("validate accepted an unsupported schema_version")
    except ProjectError:
        pass

    print(f"selftest OK — an unreadable project.json is refused rather than replaced (load AND write); two spare slots sharing slot 'F' stayed apart by tier and the profile's "
          f"group id was refused as one (SCR-042), a tier-less project still validates; "
          f"channels[] round-tripped driver/fs_hz facts (SCR-001), duplicate code "
          f"refused, a rename kept the channel's id and resolved its old captures (SCR-039), "
          f"hardware.controls recorded ONCE not per-preset (SCR-017), open_questions "
          f"found a bare null + an unfilled fact() wrapper, record_change landed in the project's "
          f"own process journal. root={root}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(_selftest())
    raise SystemExit(_main(sys.argv))
