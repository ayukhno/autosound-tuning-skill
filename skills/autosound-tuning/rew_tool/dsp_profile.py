"""DSP processor capability profile — what a DSP MODEL can do, not what one project set it to.

This is a separate artifact from `state/state.py`'s per-project ledger (channel gains/crossovers/
delay for ONE car). A profile answers "does this DSP even have virtual channels? does it have
per-input EQ?" — the schema-level facts a project's data model must be built against, so the same
UI/tooling can serve a Helix (virtual + physical tiers, no crossover on virtual) and a MUSWAY (no
virtual tier at all, but per-input Optic/USB/BT gain+EQ) without per-DSP code.

Design invariants
    * `groups` is the load-bearing field: an ordered list of the tiers/categories this DSP model
      actually exposes (e.g. virtual_channels, physical_outputs, inputs), each declaring which
      per-row fields are meaningful for it. A consumer renders whatever groups+fields are declared
      — it never assumes a fixed two-tier (virtual/output) shape. Absence of a group means the DSP
      genuinely doesn't have that tier (e.g. MUSWAY has no virtual_channels group at all).
    * `max_count` per group is how many slots that tier PHYSICALLY has (SCR-042) — a model fact,
      like everything else here, not a count of what one car wired up. Optional and `null` until
      confirmed, but load-bearing when present: without it a consumer can only count the rows it
      was given, so a 12-output Helix with two slots spare reads "10/10" instead of "10/12" and
      the spares are invisible in the one panel whose job is showing the rig entire.
    * Unconfirmed facts are `null`, not omitted — `open_questions()` walks the whole structure and
      surfaces every null plus any declared `_open_questions` freeform notes. This is what makes
      profile-building incremental: a re-run only asks about what's still open. The "not omitted"
      half used to be a hope: a field the interview never reached was simply ABSENT, and a walk
      over nulls cannot see an absence, so a profile that knew almost nothing reported nothing
      left to ask. `missing_facts()` closes that — what a profile must describe is derived from
      what it declares, so the two kinds of unanswered are reported as one list.
    * A profile is the DSP MODEL's facts, not one car's install — no personal data, safe to
      contribute to the community as-is (see `gates/side_effect.py::post_dsp_profile`).
    * JSON, not YAML — this module stays stdlib-only (matches `rew_api.py`/`state.py`), and a
      project's `dsp_profile.json` sits next to its `presets/<preset>/state/v_NNN.json` ledger in
      the same serialization family.
"""

import copy
import glob
import hashlib
import json
import os
import sys

# ── schema ──────────────────────────────────────────────────────────────────
# One number across every machine file (see `project.py`'s own note). This file carried no version
# at all before 3.0 -- which meant a consumer could not tell a profile written by this skill from
# one hand-authored years earlier, the exact question `contract.py` exists to answer.
SCHEMA_VERSION = 3
TOP_REQUIRED = ("name", "vendor", "groups")
GROUP_REQUIRED = ("id", "label", "fields")


def _unwrap(data):
    """Accept either {"dsp_profile": {...}} (the on-disk shape) or the inner dict directly."""
    return data.get("dsp_profile", data) if isinstance(data, dict) else data


def ledger_tier(group_id):
    """The ledger's (and `project.json`'s `tier`) top-level key for a profile group id.

    One convention with two spellings, which is exactly why it lives in a function. `state/state.py`
    schema v2 keeps the physical-output tier under the key `channels` — the one tier every DSP
    profile has, and named that way since before there were tiers — while the profile calls the
    same thing `physical_outputs`. Every other group id names its own key unchanged.

    Both sides of SCR-042 depend on agreeing here: a `channels[]` entry that spelled its tier
    `physical_outputs` would match no ledger tier and the spare slot it describes would stay
    invisible, silently, which is the failure the field exists to fix.
    """
    return "channels" if group_id == "physical_outputs" else group_id


def tier_keys(data):
    """Every ledger tier key this profile declares, in `groups` order (see `ledger_tier`)."""
    return [ledger_tier(g["id"]) for g in _unwrap(data).get("groups", []) if isinstance(g, dict)]


def _validate_group(g):
    missing = [f for f in GROUP_REQUIRED if f not in g]
    if missing:
        raise ValueError(f"group {g.get('id', '?')!r} missing {missing}")
    if not isinstance(g["fields"], list) or not g["fields"]:
        raise ValueError(f"group {g['id']!r}.fields must be a non-empty list")
    unknown = [f for f in g["fields"] if not isinstance(f, str) or f not in FIELD_VOCABULARY]
    if unknown:
        raise ValueError(
            f"group {g['id']!r}.fields has token(s) no consumer knows: "
            + ", ".join(_field_token_hint(f) for f in unknown)
            + ". The vocabulary is closed: "
            + ", ".join(sorted(FIELD_VOCABULARY))
            + ". A capability that fits none of these belongs in `_open_questions`, not a new "
              "token — a consumer renders exactly these and an invented name renders as nothing."
        )
    # `max_count` is optional and null-until-confirmed (SCR-042), but a present one is a physical
    # slot count, so 0/negative/float/bool are all refusals rather than something to coerce.
    # (See `_validate_rate` for the same argument about `sample_rate_hz`.)
    n = g.get("max_count")
    if "max_count" in g and n is not None:
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError(
                f"group {g['id']!r}.max_count must be a positive int or null (how many slots this "
                f"tier physically has), got {n!r}")


#: Rates a DSP actually runs at. Not a closed list of the world's rates -- a closed list of the
#: ones that are not a typo. A profile claiming 96 kHz as `"96 kHz-ish"` or as `96` (kHz, not Hz)
#: is the same defect wearing two costumes, and phase 1 turns both into sample counts.
_PLAUSIBLE_RATES_HZ = (32000, 44100, 48000, 88200, 96000, 176400, 192000)


def _validate_rate(profile):
    """`sample_rate_hz` must be a rate, not a sentence.

    SCR-045 made a MISSING rate an open question and a phase-1 refusal, because a delay in samples
    is computed from it. The audit found the obvious hole the same night: it checked presence, not
    type, so `"96 kHz-ish"` passed the gate built for exactly that incident (2026-08-12). A string
    is not a rate; 96 is not a rate in Hz; and a rate no DSP runs at is a number somebody typed
    from memory.
    """
    if "sample_rate_hz" not in profile:
        return
    rate = profile["sample_rate_hz"]
    if rate is None:
        return  # null is "not confirmed yet", which `open_questions` already reports
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise ValueError(
            f"profile.sample_rate_hz must be a number in HERTZ, got {rate!r}. Every delay in "
            "samples is computed from it — a value that is not a number makes every alignment "
            f"number wrong. Common rates: {', '.join(str(r) for r in _PLAUSIBLE_RATES_HZ)}."
        )
    if rate not in _PLAUSIBLE_RATES_HZ:
        raise ValueError(
            f"profile.sample_rate_hz = {rate!r} is not a rate any DSP runs at. In HERTZ, not kHz "
            f"(96000, not 96). Known: {', '.join(str(r) for r in _PLAUSIBLE_RATES_HZ)}. If this "
            "processor genuinely runs at something else, add it to `_PLAUSIBLE_RATES_HZ` in the "
            "same commit as the profile — a rate nobody has seen deserves a second reader."
        )


def validate_profile(data):
    """Raise ValueError on malformed profile; return `data` unchanged if OK."""
    profile = _unwrap(data)
    missing = [k for k in TOP_REQUIRED if k not in profile]
    if missing:
        raise ValueError(f"profile missing required key(s) {missing}")
    if not isinstance(profile["name"], str) or not profile["name"].strip():
        raise ValueError("profile.name must be a non-empty string")
    if not isinstance(profile["vendor"], str) or not profile["vendor"].strip():
        raise ValueError("profile.vendor must be a non-empty string")
    _validate_rate(profile)
    groups = profile["groups"]
    if not isinstance(groups, list) or not groups:
        raise ValueError("profile.groups must be a non-empty list")
    seen = set()
    for g in groups:
        _validate_group(g)
        if g["id"] in seen:
            raise ValueError(f"duplicate group id {g['id']!r}")
        seen.add(g["id"])
    return data


# ── read/write ────────────────────────────────────────────────────────────────
def load_profile(path):
    with open(path) as f:
        return json.load(f)


def save_profile(path, data):
    """Stamp the schema version, validate, then write. Refuses to write a malformed profile (same
    discipline as state.py's snapshot() — a garbage profile can't be silently banked).

    Stamped at the wrapper level (beside `dsp_profile`, not inside it) so a bundled reference
    profile keeps the same inner shape it has always had — the version describes the FILE.
    """
    validate_profile(data)
    if isinstance(data, dict):
        data = dict(data)
        data["schema_version"] = SCHEMA_VERSION
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
    return path


# ── bundled-library lookup ─────────────────────────────────────────────────────
#: The method's own reference profiles — the machine-readable half of `knowledge/dsp/`'s prose,
#: paired with it by basename. NOT `community-inbox/dsp-profiles/`, which is a landing zone for
#: other people's contributions and a different job entirely.
#:
#: This directory existed only as an argument for a long time: `find_bundled` took a path,
#: `project-intake.md §4` and this module's own selftest both assumed a library, and none shipped.
#: So every consumer built a private one, and the same processor ended up described four times in
#: three serialisations, diverging silently. Code that assumes a thing exists and ships without it
#: is a defect, not a missing feature.
BUNDLED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "knowledge", "dsp", "profiles")


def bundled_dir():
    """The library's absolute path, resolved from this module rather than from the caller's cwd."""
    return os.path.normpath(BUNDLED_DIR)


def find_bundled(vendor, model, dir_=None):
    """Exact vendor+model match only against a directory of reference profiles.

    No fuzzy/sibling matching — same rule as project-intake.md §4: another model's profile,
    even a platform sibling's, must never be assumed to apply. Returns None if no exact match.

    `dir_` defaults to the method's own library (`bundled_dir()`); pass one to search somebody
    else's. It stays an argument because a consumer may legitimately ship its own.
    """
    for path in sorted(glob.glob(os.path.join(dir_ or bundled_dir(), "*.json"))):
        try:
            data = load_profile(path)
        except (OSError, ValueError):
            continue
        profile = _unwrap(data)
        if (profile.get("vendor", "").strip().lower() == vendor.strip().lower()
                and profile.get("name", "").strip().lower() == model.strip().lower()):
            return data
    return None


def list_bundled(dir_=None):
    """Every reference profile in the library, as (vendor, model, path), vendor+model sorted."""
    out = []
    for path in sorted(glob.glob(os.path.join(dir_ or bundled_dir(), "*.json"))):
        try:
            profile = _unwrap(load_profile(path))
        except (OSError, ValueError):
            continue
        out.append((profile.get("vendor", ""), profile.get("name", ""), path))
    return sorted(out)


def refresh_project(project_dir, dir_=None, write=False):
    """Bring a project's `dsp_profile.json` back in line with the library's copy of its DSP.

    A COMMAND rather than a copy-paste, and that is the whole point. The facts for one processor
    had reached four files in three serialisations and drifted apart in every direction; pasting
    them into a fifth fixes today and guarantees the same divergence next month. This is the thing
    somebody can run again.

    Returns `(status, detail)`:
      * `("no-project", path)`      — no `dsp_profile.json` to refresh
      * `("no-dsp", None)`          — the profile names no vendor+model, so nothing can be matched
      * `("no-match", (v, m))`      — the library has no exact entry for that processor
      * `("current", diff={})`      — already identical to the library
      * `("stale", diff)`           — differs; written only when `write` is true

    It never invents: with no library entry it reports `no-match` and changes nothing, because an
    approximate profile is worse than an incomplete one — a wrong limit is enforced by code, while
    a missing one is reported as unchecked.
    """
    path = profile_path(project_dir)
    if not os.path.exists(path):
        return "no-project", path
    current = load_profile(path)
    inner = _unwrap(current)
    vendor = str(inner.get("vendor") or "").strip()
    model = str(inner.get("name") or "").strip()
    if not (vendor and model):
        return "no-dsp", None
    library = find_bundled(vendor, model, dir_)
    if library is None:
        return "no-match", (vendor, model)
    delta = diff_profile(current, library)
    # `diff_profile` always returns {"top": {...}, "groups": {...}}, so the dict is truthy even
    # when nothing differs. Testing it directly made refresh report every up-to-date project as
    # stale and rewrite it on every run -- churn that looks like drift, in the one command whose
    # job is to end drift.
    if not (delta.get("top") or delta.get("groups")):
        return "current", {}
    if write:
        save_profile(path, library)
    return "stale", delta


# ── the interview's own vocabulary (SCR-010) ──────────────────────────────────
# The fixed capability questions an onboarding interview covers. Here, not in a consumer app: the
# interview is the skill's, and a UI that shipped its own copy would drift from the schema it is
# filling in.
CAPABILITY_CHECKLIST = (
    "Is there a virtual/group layer above the per-channel one?",
    "How many slots does EACH tier physically have (`max_count`)? Count the processor's own "
    "outputs/virtual channels/inputs, not the ones this car uses — the spares are the point",
    "EQ: bands per channel, types (PK/shelf/all-pass), file import + format",
    "Crossovers: types (LR/BW/BE), orders, independent HP/LP",
    "Delays: step and limits; polarity per-channel; a phase control (all-pass)",
    "Presets: how many; what resets on a switch (the input!)",
    "Input routing: a separate input for the measurement signal?",
)

# The ONLY field-name tokens a group's `fields` list may contain. A consumer's generic renderer
# reads exactly these (`autosound-tcc`'s `dsp_state._field_label`); an invented name renders as
# nothing, silently. A capability that doesn't fit belongs in `_open_questions`, not a new token.
FIELD_VOCABULARY = {
    "hp": "high-pass crossover leg ({f, type, slope} or null/OFF on the ledger row)",
    "lp": "low-pass crossover leg (same shape as hp)",
    "gain_db": "gain in dB, a number",
    "ta_ms": "delay in milliseconds, a number (canonical delay field; ms, not samples)",
    "polarity": '"NORM" or "INV"',
    "phase_deg": "continuous phase/all-pass angle in degrees, a number",
    "mute": "boolean",
    "eq_bypass": "boolean",
    "eq": 'a list of PEQ band objects, e.g. [{"type": "PK", "f": 1000, "gain_db": -2.0, '
          '"q": 2.0}] — structured objects, not the pre-v2 inline string form',
}

# Wrong spellings that are plausible enough to be typed on purpose, and too far from the canonical
# token for `difflib` to reach ("delay" -> "ta_ms" is a synonym, not a typo). Refusing without
# naming the right spelling is what makes a validator something to work around; SCR-042 landed
# because `validate()` said the word it wanted, not because the docs got more insistent.
FIELD_NEAR_MISSES = {
    "delay": "ta_ms",
    "delay_ms": "ta_ms",
    "ta": "ta_ms",
    "time_alignment": "ta_ms",
    "time_alignment_ms": "ta_ms",
    "distance_cm": "ta_ms",  # a distance is not a delay: convert, don't declare
    "level_db": "gain_db",
    "volume_db": "gain_db",
    "invert": "polarity",
    "inverted": "polarity",
    "phase": "phase_deg",
    "allpass": "phase_deg",
    "bands": "eq",
    "peq_bands": "eq",
    "xover": "hp/lp",  # one leg each, so this one is a split rather than a rename
    "crossover": "hp/lp",
}


def _field_token_hint(token):
    """`'delay_ms'` -> `"'delay_ms' (did you mean 'ta_ms'?)"`."""
    import difflib

    if not isinstance(token, str):
        return f"{token!r} (not a string)"
    suggestion = FIELD_NEAR_MISSES.get(token)
    if suggestion is None:
        close = difflib.get_close_matches(token, list(FIELD_VOCABULARY), n=1, cutoff=0.6)
        suggestion = close[0] if close else None
    return f"{token!r}" + (f" (did you mean {suggestion!r}?)" if suggestion else "")


# ── the writer: an interview that survives a lost session ──────────────────────
def draft_path(project_dir):
    """Where an in-progress interview lives.

    On disk, not in the interviewer's context (SKILL.md's own rule for every other kind of state):
    an interview is dozens of questions long, and a session that dies halfway — a crash, a
    `/clear`, a token limit — must not take the answers with it. `finalize()` is what promotes the
    draft to the real profile.
    """
    return os.path.join(project_dir, "dsp_profile.draft.json")


def profile_path(project_dir):
    return os.path.join(project_dir, "dsp_profile.json")


def empty_draft(vendor, model):
    return {"dsp_profile": {"name": model, "vendor": vendor, "groups": [], "_open_questions": []}}


def load_draft(project_dir, vendor=None, model=None):
    """The in-progress draft: the draft file, else the finished profile as a starting point (a
    re-interview corrects an existing profile rather than starting blank), else an empty draft.

    Never raises on a missing file — "no draft yet" is the normal state of a project that has not
    been interviewed.
    """
    for path in (draft_path(project_dir), profile_path(project_dir)):
        if os.path.isfile(path):
            try:
                return load_profile(path)
            except (OSError, ValueError):
                break
    return empty_draft(vendor, model)


def start_draft(project_dir, vendor, model):
    """Begin or resume an interview: seed the draft with vendor+model and persist it.

    Separate from `load_draft` because it WRITES. Calling `set_field` first would work but would
    leave `name`/`vendor` null until the end, and `finalize` would then refuse with a message about
    the name rather than about the missing step — so the interview starts here.
    """
    data = load_draft(project_dir, vendor, model)
    profile = _unwrap(data)
    if not profile.get("name"):
        profile["name"] = model
    if not profile.get("vendor"):
        profile["vendor"] = vendor
    save_draft(project_dir, data)
    return data


def save_draft(project_dir, data):
    """Write the draft WITHOUT validating: a half-finished interview is invalid by definition (no
    groups yet, a name still null), and refusing to save it would defeat the point of having one."""
    os.makedirs(project_dir, exist_ok=True)
    path = draft_path(project_dir)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def maybe_decode_json(value):
    """A string that parses as JSON is almost certainly meant to BE that value.

    Observed live: a tool-calling round-trip handed back a whole `groups` list as the STRING
    '[{"id": ...}]', silently turning a list into a str — and the type error then surfaced far
    away, at validation, for reasons invisible from the conversation. Same for booleans arriving
    as "false". A genuine free-text answer fails to parse and is kept as-is.
    """
    if isinstance(value, str):
        try:
            return json.loads(value.strip())
        except ValueError:
            return value
    return value


def _strip_stray_prefix(path):
    """`dsp_profile.sample_rate_hz` -> `sample_rate_hz`.

    Paths are relative to the profile object itself, but an interviewer that has also seen the
    on-disk `{"dsp_profile": {...}}` wrapper guesses the prefix (observed live, 2026-07-29: "Wrong
    nesting — path made dsp_profile.dsp_profile"). Correcting it here is more robust than hoping
    the instructions prevent every case.
    """
    return path[len("dsp_profile."):] if path.startswith("dsp_profile.") else path


def set_field(project_dir, path, value):
    """Set one confirmed field in the draft by dotted path (`groups.0.fields`), and save.

    One field per call, saved immediately — the same discipline the ledger uses, for the same
    reason: what is not on disk did not happen.
    """
    path = _strip_stray_prefix(path)
    if not path:
        raise ValueError("path must not be empty")
    data = load_draft(project_dir)
    root = data.setdefault("dsp_profile", {})
    value = maybe_decode_json(value)
    parts = path.split(".")
    node = root
    for i, part in enumerate(parts[:-1]):
        key = int(part) if part.isdigit() else part
        next_is_index = parts[i + 1].isdigit()
        if isinstance(node, list):
            while len(node) <= key:
                node.append([] if next_is_index else {})
        elif key not in node:
            node[key] = [] if next_is_index else {}
        node = node[key]
    last = int(parts[-1]) if parts[-1].isdigit() else parts[-1]
    if isinstance(node, list):
        while len(node) <= last:
            node.append(None)
    node[last] = value
    save_draft(project_dir, data)
    return value


def reset_field(project_dir, path):
    """Delete a field from the draft so it can be re-answered — recovery from a wrong shape (a list
    written as a string), not part of the normal flow. Returns True if something was removed."""
    path = _strip_stray_prefix(path)
    data = load_draft(project_dir)
    node = data.get("dsp_profile", {})
    parts = path.split(".")
    for part in parts[:-1]:
        key = int(part) if part.isdigit() else part
        try:
            node = node[key]
        except (KeyError, IndexError, TypeError):
            return False
    last = int(parts[-1]) if parts[-1].isdigit() else parts[-1]
    if isinstance(node, dict) and last in node:
        del node[last]
    elif isinstance(node, list) and isinstance(last, int) and 0 <= last < len(node):
        node[last] = None
    else:
        return False
    save_draft(project_dir, data)
    return True


def finalize(project_dir):
    """Validate the draft and promote it to `dsp_profile.json`, removing the draft.

    Refuses on an invalid draft (same discipline as `state.snapshot()`): a profile is consumed by
    code, and a half-answered one that validated would produce a UI rendering fields the DSP does
    not have. The draft survives the refusal, so the interview can fix and retry.
    """
    data = load_draft(project_dir)
    validate_profile(data)
    path = save_profile(profile_path(project_dir), data)
    try:
        os.remove(draft_path(project_dir))
    except OSError:
        pass  # no draft (finalizing an edited profile directly) -- not an error
    return path


# ── incremental interview support ──────────────────────────────────────────────
# ── what a profile is expected to describe, given what it declares ────────────────────────────
# "Unconfirmed facts are `null`, not omitted" is this module's own stated invariant, and nothing
# enforced it — so a field the interview never reached was ABSENT, and `open_questions()` walks
# nulls. Result, on a real project (2026-08-11): a Helix profile with no `sample_rate_hz`, no
# `max_count`, no EQ or crossover description at all reported `_open_questions: []` and `open-
# questions -> []`. The mechanism that exists to make onboarding incremental was reporting a
# profile that knows almost nothing as a profile with nothing left to ask.
#
# What must be described is DERIVED from what the profile itself declares, rather than being a new
# list to keep in sync: a group's `fields` already says which capabilities this DSP has, and each
# of those has a block that explains how it behaves. No new vocabulary — `FIELD_VOCABULARY` is the
# vocabulary, and SCR-043 made it trustworthy.
_FACTS_ALWAYS = {
    "sample_rate_hz": "the DSP's native rate — every delay in samples is computed from it, so a "
                      "wrong or missing rate makes every alignment number wrong",
}
# field token in ANY group -> the top-level block that has to describe it
_FACTS_BY_FIELD = {
    "ta_ms": "delay",
    "phase_deg": "phase_control",
    "polarity": "polarity",
    "eq": "parametric_eq",
}
# ...and per group, given that group's own fields
_GROUP_FACTS_ALWAYS = {
    "max_count": "how many slots this tier physically has (SCR-042) — without it a consumer can "
                 "only count the rows it was given, and the spares are invisible",
}
_GROUP_FACTS_BY_FIELD = {"hp": "crossover_filters", "lp": "crossover_filters", "eq": "eq"}


def missing_facts(data):
    """Dotted paths a profile is expected to carry and does not have at all.

    Absent is not the same as null, and this module's whole incremental-interview story assumes
    they are: `null` means "asked, not answered yet", and a key that was never created means the
    question was never asked. Both are open questions; only one of them was being reported.
    """
    profile = _unwrap(data)
    groups = [g for g in profile.get("groups", []) if isinstance(g, dict)]
    declared = {f for g in groups for f in (g.get("fields") or []) if isinstance(f, str)}
    out = [key for key in _FACTS_ALWAYS if key not in profile]
    out += [
        block for field, block in _FACTS_BY_FIELD.items()
        if field in declared and block not in profile
    ]
    for i, group in enumerate(groups):
        fields = {f for f in (group.get("fields") or []) if isinstance(f, str)}
        for key in _GROUP_FACTS_ALWAYS:
            if key not in group:
                out.append(f"groups.{i}.{key}")
        for field, block in _GROUP_FACTS_BY_FIELD.items():
            # A tier that declares no crossover legs is not missing a crossover description.
            if field in fields and block not in group:
                out.append(f"groups.{i}.{block}")
    return sorted(set(out))


def open_questions(data):
    """Every unanswered fact (dotted path) plus any declared `_open_questions` freeform notes.

    Unanswered means BOTH still-null and never-created — see `missing_facts` for why the second
    kind had been invisible.

    Drives incremental onboarding: a resumed interview asks only about what this returns, not
    the whole checklist again.
    """
    profile = _unwrap(data)
    out = list(profile.get("_open_questions") or [])

    def walk(prefix, obj):
        if isinstance(obj, dict):
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

    walk("", profile)
    out += [path for path in missing_facts(data) if path not in out]
    return out


# ── diff (mirrors state.py's diff_states shape) ────────────────────────────────
def _diff_scalar(a, b):
    return None if a == b else [a, b]


def diff_profile(old, new):
    """Structured deltas old -> new at top-level-field and per-group granularity. Only changed
    things appear — used to decide whether a community contribution is `new` or `update`."""
    op, npf = _unwrap(old), _unwrap(new)
    out = {"top": {}, "groups": {}}
    for k in sorted((set(op) | set(npf)) - {"groups", "_contributed"}):
        d = _diff_scalar(op.get(k), npf.get(k))
        if d is not None:
            out["top"][k] = d
    og = {g["id"]: g for g in op.get("groups", [])}
    ng = {g["id"]: g for g in npf.get("groups", [])}
    for gid in sorted(set(og) | set(ng)):
        if gid not in og:
            out["groups"][gid] = {"__added__": True}
            continue
        if gid not in ng:
            out["groups"][gid] = {"__removed__": True}
            continue
        fields = {}
        for fk in sorted(set(og[gid]) | set(ng[gid])):
            d = _diff_scalar(og[gid].get(fk), ng[gid].get(fk))
            if d is not None:
                fields[fk] = d
        if fields:
            out["groups"][gid] = fields
    return out


def content_hash(data):
    """Stable hash of the profile's substantive content, excluding `_contributed` bookkeeping —
    lets a caller detect "nothing new since the last post" without a network round-trip."""
    profile = copy.deepcopy(_unwrap(data))
    profile.pop("_contributed", None)
    blob = json.dumps(profile, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ── CLI ───────────────────────────────────────────────────────────────────────
def _main(argv=None):
    import argparse

    p = argparse.ArgumentParser(description="DSP processor capability profile")
    sub = p.add_subparsers(dest="cmd")

    vp = sub.add_parser("validate")
    vp.add_argument("path")

    oq = sub.add_parser("open-questions")
    oq.add_argument("path")

    fb = sub.add_parser("find-bundled")
    fb.add_argument("vendor")
    fb.add_argument("model")
    fb.add_argument("bundled_dir", nargs="?",
                    help="where to look (default: the method's own library)")

    ls = sub.add_parser("list-bundled", help="every reference profile the method ships")
    ls.add_argument("bundled_dir", nargs="?")

    rf = sub.add_parser("refresh", help="update a project's dsp_profile.json from the library")
    rf.add_argument("project_dir")
    rf.add_argument("--bundled-dir")
    rf.add_argument("--write", action="store_true",
                    help="actually write; without it the differences are only reported")

    dp = sub.add_parser("diff")
    dp.add_argument("old_path")
    dp.add_argument("new_path")

    # -- the writer (SCR-025). The interview runs THROUGH these, so a profile is written by the
    # skill's own tooling like every other machine file, not by whatever app is hosting the chat.
    st = sub.add_parser("start", help="begin/resume an interview draft for a vendor+model")
    st.add_argument("project_dir")
    st.add_argument("vendor")
    st.add_argument("model")

    sf = sub.add_parser("set-field", help="set one confirmed field in the draft")
    sf.add_argument("project_dir")
    sf.add_argument("path")
    sf.add_argument("value")

    rf = sub.add_parser("reset-field", help="drop a field so it can be re-answered")
    rf.add_argument("project_dir")
    rf.add_argument("path")

    dr = sub.add_parser("draft", help="print the current draft + what is still open")
    dr.add_argument("project_dir")

    fz = sub.add_parser("finalize", help="validate the draft and write dsp_profile.json")
    fz.add_argument("project_dir")

    sub.add_parser("checklist", help="the fixed capability questions + the field vocabulary")

    sub.add_parser("selftest")
    args = p.parse_args(argv)

    if args.cmd == "selftest" or args.cmd is None:
        return _selftest()
    if args.cmd == "validate":
        validate_profile(load_profile(args.path))
        print("OK")
        return 0
    if args.cmd == "open-questions":
        for q in open_questions(load_profile(args.path)):
            print(q)
        return 0
    if args.cmd == "find-bundled":
        found = find_bundled(args.vendor, args.model, args.bundled_dir)
        print(json.dumps(found, indent=2, ensure_ascii=False) if found else "no exact match")
        return 0
    if args.cmd == "list-bundled":
        rows = list_bundled(args.bundled_dir)
        for vendor, model, path in rows:
            print(f"{vendor} · {model}  ->  {os.path.basename(path)}")
        if not rows:
            print(f"no profiles in {args.bundled_dir or bundled_dir()}")
        return 0
    if args.cmd == "refresh":
        status, detail = refresh_project(args.project_dir, args.bundled_dir, write=args.write)
        if status == "no-project":
            print(f"no dsp_profile.json at {detail}", file=sys.stderr)
            return 1
        if status == "no-dsp":
            print("the project's profile names no vendor+model, so nothing can be matched",
                  file=sys.stderr)
            return 1
        if status == "no-match":
            print(f"the library has no exact entry for {detail[0]} {detail[1]!r} — "
                  f"nothing changed (an approximate profile is worse than an incomplete one: "
                  f"a wrong limit is enforced, a missing one is reported as unchecked)",
                  file=sys.stderr)
            return 1
        if status == "current":
            print("already current with the library")
            return 0
        print(json.dumps(detail, indent=2, ensure_ascii=False))
        print(("WROTE " if args.write else "would change ")
              + f"{profile_path(args.project_dir)}"
              + ("" if args.write else " — re-run with --write"))
        return 0 if args.write else 2
    if args.cmd == "diff":
        print(json.dumps(diff_profile(load_profile(args.old_path), load_profile(args.new_path)),
                          indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "checklist":
        print("# Capability checklist — ask 2-3 per turn, never the whole list at once")
        for q in CAPABILITY_CHECKLIST:
            print(f"- {q}")
        print("\n# Field vocabulary — a group's `fields` may contain ONLY these tokens")
        for token, meaning in FIELD_VOCABULARY.items():
            print(f"- {token}: {meaning}")
        return 0
    if args.cmd == "start":
        data = start_draft(args.project_dir, args.vendor, args.model)
        print(json.dumps({"draft": _unwrap(data), "open_questions": open_questions(data)},
                          indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "set-field":
        value = set_field(args.project_dir, args.path, args.value)
        print(json.dumps({"set": args.path, "value": value}, ensure_ascii=False))
        return 0
    if args.cmd == "reset-field":
        ok = reset_field(args.project_dir, args.path)
        print(json.dumps({"reset": args.path, "found": ok}, ensure_ascii=False))
        return 0
    if args.cmd == "draft":
        data = load_draft(args.project_dir)
        print(json.dumps({"draft": _unwrap(data), "open_questions": open_questions(data)},
                          indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "finalize":
        try:
            path = finalize(args.project_dir)
        except ValueError as exc:
            print(f"draft is not a valid profile yet, kept as-is: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {path}")
        return 0


# ── self-test ─────────────────────────────────────────────────────────────────
def _musway_stub():
    """A deliberately incomplete profile — the interview's starting point for a new DSP."""
    return {
        "dsp_profile": {
            "name": "M6V4",
            "vendor": "Musway",
            "groups": [
                {"id": "physical_outputs", "label": "Output channels",
                 "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity"]},
                {"id": "inputs", "label": "Inputs", "no_crossover": True,
                 "fields": ["gain_db", "eq", "ta_ms"]},
            ],
            "sample_rate_hz": None,
            "_open_questions": ["confirm from vendor software UI, not just user memory"],
        }
    }


def _selftest():
    import tempfile

    helix = {
        "dsp_profile": {
            "name": "Helix DSP Ultra S",
            "vendor": "Audiotec-Fischer",
            "groups": [
                {"id": "virtual_channels", "label": "Virtual channels", "no_crossover": True,
                 "fields": ["gain_db", "ta_ms", "polarity", "phase_deg", "mute", "eq"],
                 "eq": {"bands_per_channel": 30, "band_types": ["PK", "LSH", "HSH"]}},
                {"id": "physical_outputs", "label": "Output channels",
                 "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity", "phase_deg", "eq"],
                 "eq": {"bands_per_channel": 30, "band_types": ["PK", "LSH", "HSH"]},
                 "crossover_filters": {"types": {"LR": {"orders_db_per_oct": [12, 24]}}}},
            ],
            # A COMPLETE profile, so `open_questions` on it is empty below -- which is also this
            # fixture's job: it is the worked example of what "described" means. Each block is here
            # because some group's `fields` declares the capability it explains (see
            # `missing_facts`), not because a list somewhere says so.
            "sample_rate_hz": 96000,
            "delay": {"step_ms": 0.01, "scope": ["per driver output"]},
            "polarity": {"scope": ["per driver output"]},
            "phase_control": {"scope": "per driver output", "implementation": "all-pass"},
            "parametric_eq": {"q_range": [0.5, 15.0], "gain_range_db": [-30.0, 12.0]},
        }
    }
    validate_profile(helix)  # must not raise

    # a malformed profile (group missing "fields") must be refused, not silently banked.
    bad = copy.deepcopy(helix)
    del bad["dsp_profile"]["groups"][0]["fields"]
    try:
        validate_profile(bad)
        raise AssertionError("validate_profile accepted a group with no fields")
    except ValueError:
        pass

    # ── the field vocabulary is closed, and now it is enforced ────────────────────────────────
    # It had been declared closed since SCR-010 and checked nowhere: a group could declare
    # `delay_ms`, validate clean, be banked, and then render as nothing in every consumer forever.
    # The same class of silent-wrong as SCR-042, and the same fix — refuse, and say which spelling.
    for wrong, wanted in (("delay_ms", "ta_ms"), ("level_db", "gain_db"), ("nonsense", None)):
        invented = copy.deepcopy(helix)
        invented["dsp_profile"]["groups"][0]["fields"] = ["gain_db", wrong]
        try:
            validate_profile(invented)
            raise AssertionError(f"validate_profile accepted fields token {wrong!r}")
        except ValueError as exc:
            assert wrong in str(exc), exc
            # A refusal that doesn't name the right token is a refusal to be worked around.
            assert wanted is None or wanted in str(exc), exc

    # A non-string in `fields` is the tool-call round-trip failure maybe_decode_json exists for,
    # arriving one level deeper -- refused here rather than crashing a consumer's renderer.
    typed = copy.deepcopy(helix)
    typed["dsp_profile"]["groups"][0]["fields"] = ["gain_db", 7]
    try:
        validate_profile(typed)
        raise AssertionError("validate_profile accepted a non-string fields token")
    except ValueError:
        pass

    # ── absent is unanswered too, not just null ────────────────────────────────────────────────
    # The interview is incremental because `open_questions()` says what is left. It walked nulls,
    # and a question never asked leaves no null behind — so a real Helix profile carrying neither
    # `sample_rate_hz` nor any EQ/crossover description reported an empty list.
    bare = {"dsp_profile": {"name": "M6V4", "vendor": "Musway", "groups": [
        {"id": "physical_outputs", "label": "Outputs", "fields": ["hp", "lp", "gain_db", "ta_ms"]},
    ]}}
    validate_profile(bare)  # still a VALID profile: incomplete is not malformed
    questions = open_questions(bare)
    # Always expected...
    assert "sample_rate_hz" in questions, questions
    assert "groups.0.max_count" in questions, questions
    # ...and these only because the group's own `fields` declare the capability.
    assert "delay" in questions, questions
    assert "groups.0.crossover_filters" in questions, questions
    # A tier that declares no EQ and no phase control is not missing their descriptions.
    assert "parametric_eq" not in questions, questions
    assert "phase_control" not in questions, questions
    assert "groups.0.eq" not in questions, questions
    # Answered is answered: a fact that is present stops being asked about.
    answered = copy.deepcopy(bare)
    answered["dsp_profile"]["sample_rate_hz"] = 96000
    assert "sample_rate_hz" not in open_questions(answered)
    # ...but present-and-null is still open, which is the case that always worked.
    nulled = copy.deepcopy(bare)
    nulled["dsp_profile"]["sample_rate_hz"] = None
    assert open_questions(nulled).count("sample_rate_hz") == 1, open_questions(nulled)

    # ── SCR-042: how many slots the tier physically has, and what the ledger calls that tier ──
    # The real case: a Helix Ultra S with 10 outputs wired reads "10/10" without this, when it is
    # a 12-output processor with two slots spare.
    counted = copy.deepcopy(helix)
    counted["dsp_profile"]["groups"][0]["max_count"] = 8    # virtual A-H
    counted["dsp_profile"]["groups"][1]["max_count"] = 12   # outputs B-K, 12 physical
    validate_profile(counted)
    assert open_questions(counted) == [], open_questions(counted)

    # a slot count is a count: 0, negative, float and bool are refusals, null is "not asked yet".
    for bad_count in (0, -1, 2.5, True, "12"):
        broken_count = copy.deepcopy(counted)
        broken_count["dsp_profile"]["groups"][1]["max_count"] = bad_count
        try:
            validate_profile(broken_count)
            raise AssertionError(f"validate_profile accepted max_count={bad_count!r}")
        except ValueError:
            pass
    nulled = copy.deepcopy(counted)
    nulled["dsp_profile"]["groups"][1]["max_count"] = None
    validate_profile(nulled)  # null is legal -- and surfaces itself as an open question
    assert "groups.1.max_count" in open_questions(nulled), open_questions(nulled)

    # the ledger calls the physical-output tier `channels`; every other group id is its own key.
    assert ledger_tier("physical_outputs") == "channels"
    assert ledger_tier("virtual_channels") == "virtual_channels"
    assert ledger_tier("inputs") == "inputs"
    assert tier_keys(helix) == ["virtual_channels", "channels"], tier_keys(helix)

    # MUSWAY has genuinely no virtual_channels group — that must be representable, not an error.
    musway = _musway_stub()
    validate_profile(musway)
    ids = [g["id"] for g in musway["dsp_profile"]["groups"]]
    assert "virtual_channels" not in ids, ids
    assert "inputs" in ids, ids

    # open_questions surfaces the null sample_rate_hz plus the freeform note.
    oq = open_questions(musway)
    assert "sample_rate_hz" in oq, oq
    assert any("vendor software" in q for q in oq), oq
    # Complete in every capability it declares, and still owing its two slot counts (SCR-042) --
    # the `counted` copy below closes exactly those, and asserts an empty list afterwards.
    assert open_questions(helix) == ["groups.0.max_count", "groups.1.max_count"], \
        open_questions(helix)

    # find_bundled: exact match only, no sibling/fuzzy match.
    tmp = tempfile.mkdtemp(prefix="dsp_profiles_")
    save_profile(os.path.join(tmp, "helix-dsp-ultra-s.json"), helix)
    found = find_bundled("Audiotec-Fischer", "Helix DSP Ultra S", tmp)
    assert found is not None and found["dsp_profile"]["name"] == "Helix DSP Ultra S"
    assert find_bundled("Musway", "M6V4", tmp) is None, "must not fuzzy-match a different vendor"
    assert find_bundled("Audiotec-Fischer", "Helix DSP Ultra", tmp) is None, \
        "must not match on a partial/sibling model name"

    # ── the SHIPPED library (2026-08-23) ──────────────────────────────────────
    # `find_bundled` took a directory for months while the method shipped none, so every consumer
    # built a private one and the same processor ended up described four times in three
    # serialisations. The default is the repair; these pin that it is real and reachable.
    assert os.path.isdir(bundled_dir()), f"the method ships no profile library at {bundled_dir()}"
    shipped = list_bundled()
    assert shipped, "the library is empty -- a default pointing at nothing is the old defect"
    assert ("Audiotec-Fischer", "Helix DSP Ultra S") in [(v, m) for v, m, _ in shipped], shipped
    # ...and the default is what an argument-less call actually uses.
    helix = find_bundled("Audiotec-Fischer", "Helix DSP Ultra S")
    assert helix is not None, "find_bundled must default to the shipped library"
    assert validate_profile(helix) or True
    validate_profile(helix)                      # a shipped profile that fails our own validator
                                                 # would be worse than shipping none
    inner = _unwrap(helix)
    # The facts the library exists to stop diverging. Each is one a checker enforces.
    peq = inner["parametric_eq"]
    assert peq["freq_range_hz"] == [10.0, 40000.0] and peq["q_range"] == [0.5, 50.0], peq
    assert peq["freq_step_hz"] == 0.01, peq
    assert inner["channel_gain"]["range_db"] == [-30.0, 5.0], inner["channel_gain"]
    assert inner["delay"]["max_ms"] == 20.82, inner["delay"]
    xo = [g for g in inner["groups"] if g["id"] == "physical_outputs"][0]["crossover_filters"]
    assert xo["corner_freq_range_hz"] == [20.0, 20480.0], xo
    assert xo["types"]["LR"]["orders_db_per_oct"] == [12, 24, 36], xo["types"]["LR"]
    # The derived pairing must stay labelled as derived. A plausible number becomes a measured
    # fact simply by sitting in a field that only records measured facts.
    assert "DERIVED" in peq["mode_note"], peq["mode_note"]
    assert any("co-occur" in q for q in inner["_open_questions"]), inner["_open_questions"]

    # refresh: a COMMAND, so the facts stop diverging instead of being pasted a fifth time.
    with tempfile.TemporaryDirectory() as proj:
        assert refresh_project(proj)[0] == "no-project"
        stale = copy.deepcopy(helix)
        _unwrap(stale)["parametric_eq"]["q_range"] = [0.5, 15.0]     # a real past divergence
        save_profile(profile_path(proj), stale)
        status, delta = refresh_project(proj)
        assert status == "stale" and delta, (status, delta)
        assert refresh_project(proj, write=True)[0] == "stale"
        assert refresh_project(proj)[0] == "current", "refresh must be idempotent"
        # An unknown processor is reported, never approximated: a wrong limit is enforced by code,
        # a missing one is merely reported as unchecked.
        odd = copy.deepcopy(helix)
        _unwrap(odd)["name"] = "Some Other DSP"
        save_profile(profile_path(proj), odd)
        assert refresh_project(proj)[0] == "no-match", refresh_project(proj)
        assert _unwrap(load_profile(profile_path(proj)))["name"] == "Some Other DSP", \
            "a no-match must change nothing"

    # diff_profile: filling sample_rate_hz shows up as a top-level change; nothing else moves.
    filled = copy.deepcopy(musway)
    filled["dsp_profile"]["sample_rate_hz"] = 48000
    d = diff_profile(musway, filled)
    assert d["top"]["sample_rate_hz"] == [None, 48000], d
    assert d["groups"] == {}, "unrelated groups must not appear in the diff"

    # content_hash ignores _contributed bookkeeping so a post-then-rehash round-trip is stable.
    h1 = content_hash(filled)
    stamped = copy.deepcopy(filled)
    stamped["dsp_profile"]["_contributed"] = {"url": "https://example/1", "sha256": h1}
    assert content_hash(stamped) == h1, "content_hash must ignore _contributed bookkeeping"

    # ── the writer (SCR-025): an interview that survives a lost session ──
    proj = tempfile.mkdtemp(prefix="dsp_profile_proj_")
    load_draft(proj, "Musway", "M6V4")
    assert not os.path.exists(draft_path(proj)), "merely READING a draft must not create one"

    start_draft(proj, "Musway", "M6V4")
    set_field(proj, "sample_rate_hz", "96000")          # a JSON-encoded number arrives as a string
    set_field(proj, "groups.0.id", "physical_outputs")  # list indices build the list as needed
    set_field(proj, "groups.0.label", "Output channels")
    set_field(proj, "dsp_profile.groups.0.fields", '["hp", "lp", "gain_db"]')  # stray prefix + JSON
    draft = _unwrap(load_draft(proj))
    assert draft["sample_rate_hz"] == 96000, draft          # decoded to an int, not left "96000"
    assert draft["groups"][0]["fields"] == ["hp", "lp", "gain_db"], draft  # a list, not a string
    assert draft["name"] == "M6V4" and draft["vendor"] == "Musway", draft

    # THE point of a draft on disk: everything above survives a session that never came back.
    assert os.path.isfile(draft_path(proj)), "every set-field must have hit the disk"
    assert not os.path.exists(profile_path(proj)), "an unfinished interview is not a profile yet"

    # a wrong shape is recoverable without restarting the interview.
    set_field(proj, "groups.0.fields", "not-a-list")
    assert reset_field(proj, "groups.0.fields") is True
    assert reset_field(proj, "groups.0.fields") is False, "resetting a gone field reports nothing"
    set_field(proj, "groups.0.fields", '["hp", "lp", "gain_db"]')

    # finalize promotes the draft and clears it; the profile is stamped with the format version.
    written = finalize(proj)
    assert os.path.isfile(written) and not os.path.exists(draft_path(proj)), written
    assert load_profile(written)["schema_version"] == SCHEMA_VERSION, load_profile(written)

    # an invalid draft is REFUSED, and the draft survives the refusal so it can be fixed.
    broken = tempfile.mkdtemp(prefix="dsp_profile_broken_")
    start_draft(broken, "Musway", "Half-answered")
    try:
        finalize(broken)
        raise AssertionError("finalize accepted a draft with no groups")
    except ValueError:
        pass
    assert os.path.isfile(draft_path(broken)), "a refused finalize must not destroy the draft"

    # re-interviewing a FINISHED profile starts from it rather than blank.
    resumed = _unwrap(load_draft(proj, "Musway", "M6V4"))
    assert resumed["sample_rate_hz"] == 96000, resumed

    print(f"selftest OK — max_count validated as a physical slot count (null = still open, 0/float/"
          f"bool/str refused) and physical_outputs mapped to the ledger's `channels` key (SCR-042); "
          f"validate rejects malformed groups, MUSWAY's missing virtual_channels "
          f"tier is representable (not an error), open_questions found the null field + freeform "
          f"note, find_bundled matched exactly and refused a sibling/partial name, diff_profile "
          f"isolated the one changed field, content_hash is stable across _contributed stamping; "
          f"writer: every set-field hit the disk (a lost session keeps its answers), JSON-encoded "
          f"values and a stray `dsp_profile.` prefix were decoded, a wrong shape was recoverable, "
          f"finalize promoted the draft and refused a half-answered one without destroying it. "
          f"tmp={tmp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
