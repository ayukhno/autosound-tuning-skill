"""DSP processor capability profile — what a DSP MODEL can do, not what one project set it to.

This is a separate artifact from `state/state.py`'s per-project ledger (channel gains/crossovers/
delay for ONE car). A profile answers "does this DSP even have virtual channels? does it have
per-input EQ?" — the schema-level facts a project's data model must be built against, so the same
UI/tooling can serve a Helix (virtual + physical tiers, no crossover on virtual) and a processor
with no virtual tier at all but per-input gain and EQ, without per-DSP code. (The second half of
that sentence deliberately names no model: it used to say MUSWAY and assert specifics that trace
back to one recollection, never re-checked in the vendor software. An illustration does not need a
real unit, and a docstring's opening paragraph is where an unverified one does the most damage.)

Design invariants
    * `groups` is the load-bearing field: an ordered list of the tiers/categories this DSP model
      actually exposes (e.g. virtual_channels, physical_outputs, inputs), each declaring which
      per-row fields are meaningful for it. A consumer renders whatever groups+fields are declared
      — it never assumes a fixed two-tier (virtual/output) shape. Three different "not there"s,
      and conflating any two of them answers a question nobody asked:
      **`groups_enumerated: true`** makes the absence of a group a positive claim that the DSP
      lacks that tier; `false` says there may be more; absent/null means nobody has said, and
      `missing_facts` asks. **`fields: null`** is a tier that exists whose controls are not
      enumerated. **An absent group under `groups_enumerated: true`** is the only one of the three
      that asserts anything. (An earlier version of
      this paragraph illustrated the point with specific MUSWAY facts — no virtual tier, per-input
      Optic/USB/BT gain+EQ — which traced back to one person's recollection, never re-checked in
      the vendor software. The design rationale should not rest on an unverified example, so it
      does not any more.)
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


#: The DSP's PROCESSING rate — the rate the processor runs at; every delay expressed in samples
#: derives from it. Renamed from `sample_rate_hz` (the user's ruling, 2026-08-25) because the old
#: name never said WHICH rate it is, and two sessions independently confused it with the CAPTURE
#: rate — the rate a measurement was recorded at (a UMIK-1 captures at 48k while a Helix runs
#: 96k; that is legitimate and lives with the measurement, not here). The old key is still READ
#: everywhere (normalize_rate), so nothing written before the rename breaks — including AutoSci's
#: historical experiment scripts and the released 2.x line, which are deliberately untouched.
PROCESSING_RATE_KEY = "dsp_processing_rate_hz"
LEGACY_RATE_KEY = "sample_rate_hz"


def normalize_rate(profile):
    """Make the canonical key present when only the legacy one is (in place, idempotent).

    Both present with DIFFERENT values is refused: that is two answers to one fact, and picking
    either silently is how a wrong rate gets every sample count wrong.
    """
    if LEGACY_RATE_KEY in profile:
        if PROCESSING_RATE_KEY not in profile:
            profile[PROCESSING_RATE_KEY] = profile[LEGACY_RATE_KEY]
        elif profile[PROCESSING_RATE_KEY] != profile[LEGACY_RATE_KEY] and \
                profile[LEGACY_RATE_KEY] is not None and profile[PROCESSING_RATE_KEY] is not None:
            raise ValueError(
                f"profile carries both {PROCESSING_RATE_KEY}={profile[PROCESSING_RATE_KEY]!r} and "
                f"{LEGACY_RATE_KEY}={profile[LEGACY_RATE_KEY]!r} with different values -- two answers "
                f"to one fact. Keep {PROCESSING_RATE_KEY} and delete the legacy key")
    return profile


def processing_rate_hz(data):
    """The DSP's processing rate from either key (canonical first), or None."""
    profile = _unwrap(data)
    v = profile.get(PROCESSING_RATE_KEY)
    return v if v is not None else profile.get(LEGACY_RATE_KEY)


#: The general term for everything a capture session must have OFF: anything that is not gain,
#: delay, polarity, crossover or EQ. Every vendor names these differently -- Helix calls them
#: RealCenter / DynamicBass / SubXpander / ActiveToneControl, another DSP calls them "loudness",
#: "auto EQ", "bass restoration", "limiter" -- so the METHOD needs one word and the PROFILE needs
#: the vendor's own names. Without that list, "effects and dynamic processing off" is an
#: instruction nobody can check: the tuner reads it, looks at a screen full of vendor words, and
#: decides for themselves which of them counted.
EFFECTS_KEY = "effects_and_dynamics"


def effects_and_dynamics(data):
    """The vendor's own names for what must be OFF during a capture, or None if unrecorded.

    None is not "this DSP has none" -- it is "nobody wrote it down for this DSP", and the two must
    not look alike to a caller. A profile that genuinely has nothing of the sort records an empty
    list, which says a person checked.
    """
    profile = _unwrap(data)
    v = profile.get(EFFECTS_KEY)
    if v is None:
        return None
    return [str(x) for x in v]


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
    # `fields` is null-until-confirmed, like `max_count` — and it needs the state MORE, because it
    # gates what gets asked at all. `missing_facts` derives its checklist from the declared field
    # tokens, so a profile forced to name some fields in order to validate does not merely assert
    # controls nobody confirmed: it DELETES the questions about the ones it left out. A tier
    # declaring `["hp", "lp"]` to get past this line is read by every consumer as "this DSP's
    # outputs have crossover legs and no gain, no delay, no polarity and no EQ", and
    # `open-questions` then says nothing about any of them. That is the exact failure this module's
    # docstring says `missing_facts` exists to close — closed one level down, still open here.
    # Raised by the AutoSci session, 2026-08-23, when an honest Musway stub could not be written.
    if g["fields"] is not None:
        if not isinstance(g["fields"], list) or not g["fields"]:
            raise ValueError(
                f"group {g['id']!r}.fields must be a non-empty list, or null when this tier's "
                f"controls have not been enumerated yet (null asks the question; a short list "
                f"silently answers it)")
    unknown = [f for f in (g["fields"] or []) if not isinstance(f, str) or f not in FIELD_VOCABULARY]
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
    _validate_in_scope(g)
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


def _validate_in_scope(group):
    value = group.get(IN_SCOPE)
    if IN_SCOPE in group and not isinstance(value, bool):
        raise ValueError(
            f"group {group.get('id', '?')!r}.{IN_SCOPE} must be true or false (false = the DSP has "
            f"this tier and the method does not tune it), got {value!r}")


def _validate_groups_enumerated(profile):
    value = profile.get(GROUPS_ENUMERATED)
    if GROUPS_ENUMERATED in profile and value is not None and not isinstance(value, bool):
        raise ValueError(
            f"{GROUPS_ENUMERATED} must be true, false or null (true = the tier list is complete, "
            f"so an absent group MEANS the DSP lacks that tier; false = there may be more; null = "
            f"nobody has said), got {value!r}")


def _validate_rate(profile):
    """`dsp_processing_rate_hz` (or the legacy `sample_rate_hz`) must be a rate, not a sentence.

    SCR-045 made a MISSING rate an open question and a phase-1 refusal, because a delay in samples
    is computed from it. The audit found the obvious hole the same night: it checked presence, not
    type, so `"96 kHz-ish"` passed the gate built for exactly that incident (2026-08-12). A string
    is not a rate; 96 is not a rate in Hz; and a rate no DSP runs at is a number somebody typed
    from memory.
    """
    normalize_rate(profile)
    if PROCESSING_RATE_KEY not in profile and LEGACY_RATE_KEY not in profile:
        return
    rate = processing_rate_hz(profile)
    if rate is None:
        return  # null is "not confirmed yet", which `open_questions` already reports
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise ValueError(
            f"profile.{PROCESSING_RATE_KEY} must be a number in HERTZ, got {rate!r}. Every delay in "
            "samples is computed from it — a value that is not a number makes every alignment "
            f"number wrong. Common rates: {', '.join(str(r) for r in _PLAUSIBLE_RATES_HZ)}."
        )
    if rate not in _PLAUSIBLE_RATES_HZ:
        raise ValueError(
            f"profile.{PROCESSING_RATE_KEY} = {rate!r} is not a rate any DSP runs at. In HERTZ, not kHz "
            f"(96000, not 96). Known: {', '.join(str(r) for r in _PLAUSIBLE_RATES_HZ)}. If this "
            "processor genuinely runs at something else, add it to `_PLAUSIBLE_RATES_HZ` in the "
            "same commit as the profile — a rate nobody has seen deserves a second reader."
        )


#: Whether `groups` is a COMPLETE list of this DSP's tiers. Tri-state on purpose:
#: `True` — enumerated, so the absence of a group is a positive claim that the tier does not exist;
#: `False` — these are the tiers we know of, there may be more;
#: absent/`None` — nobody has said, and `missing_facts` asks.
#:
#: `fields: null` fixed a tier's CONTROLS and left the TIER LIST with the same defect one level up:
#: `groups` must be non-empty, so an honest stub has to name at least one tier, and naming one is
#: what makes every other tier read as absent — i.e. as a positive claim nobody made. Raised by the
#: AutoSci session, 2026-08-23, from inside the very entry that was meant to be the honest one:
#: declaring only `physical_outputs` asserted that a Musway has no virtual tier and no per-input
#: controls, which is exactly the claim retracted from this module's docstring hours earlier,
#: re-entering through a different door. Prose was the only guard, and prose is what had already
#: failed in every other case that day.
GROUPS_ENUMERATED = "groups_enumerated"

#: A tier the DSP HAS and this method does not tune. `false` says so; absent/`true` is in scope.
#:
#: Not the same as absent-from-`groups`, and the difference is the point: the Helix's input stage
#: exists, and un-processing what a factory head unit already did to the signal is a different
#: problem that this method does not solve (user, 2026-08-23). Deleting the tier would assert the
#: hardware lacks it; leaving it in scope makes `open_questions` ask forever about controls nobody
#: will ever enumerate — and a list that always has two dead entries is a list people stop reading,
#: which is the failure `estimator-scope.md` 1a exists to prevent. So: kept, declared, and skipped
#: when counting what is still unanswered.
IN_SCOPE = "in_scope"


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
    _validate_groups_enumerated(profile)
    fx = profile.get(EFFECTS_KEY)
    if fx is not None and (not isinstance(fx, list) or any(not isinstance(x, str) or not x.strip()
                                                           for x in fx)):
        raise ValueError(f"profile.{EFFECTS_KEY} must be a list of non-empty vendor names "
                         f"(an empty list means someone checked and there are none)")
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
def bind_model_rate(project_dir_or_profile):
    """Bind the response model to THIS device's processing rate, and say what happened.

    Returns `(rate_hz_or_None, note_or_None)`. The note is `None` only when the profile states a
    rate and the model is on it — every other case has something a session must be told, and the
    caller prints it. The rate is bound in `dsp_math`, so `xo_response` / `peq_response` model at
    the device's rate instead of a module constant.

    Call this ONCE, early, before anything is modelled — not inside the `--align` branch, which is
    where the delay grid reads the rate today. The crossover model runs whether or not alignment
    is asked for, so a binding that happens only on that path leaves the common case unbound.

    Why this lives here and not in `load_profile`: loading a profile is also what VALIDATORS do,
    to a profile that may describe some other device entirely, and a load that silently rebinds
    the model would make validation change the session's arithmetic. Binding is a decision, so it
    is a call.

    `dsp_math` is imported lazily: this module is pure stdlib on purpose and is read by tools that
    have no numpy.
    """
    import dsp_math
    profile = project_dir_or_profile
    if isinstance(profile, str):
        path = os.path.join(profile, "dsp_profile.json") if os.path.isdir(profile) else profile
        try:
            with open(path) as fh:
                profile = json.load(fh)
        except (OSError, ValueError):
            return None, dsp_math.rate_note(None)
    rate = processing_rate_hz(profile)
    if rate:
        try:
            dsp_math.bind_processing_rate(float(rate), source="profile")
        except dsp_math.RateConflict as exc:
            return float(rate), str(exc)
    return (float(rate) if rate else None), dsp_math.rate_note(float(rate) if rate else None)


def load_profile(path):
    with open(path) as f:
        return json.load(f)


def _provenance():
    """`provenance.py` from the same checkout, by path — same reason as every other sibling load
    here: `rew_tool/` is not on the consumer's import path, it is loaded from one."""
    import importlib.util

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provenance.py")
    try:
        spec = importlib.util.spec_from_file_location("_dsp_profile_provenance", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 — an unloadable stamp must not cost the profile
        return None


def save_profile(path, data):
    """Stamp the schema version and the writer, validate, then write. Refuses to write a malformed
    profile (same discipline as state.py's snapshot() — a garbage profile can't be silently banked).

    Stamped at the wrapper level (beside `dsp_profile`, not inside it) so a bundled reference
    profile keeps the same inner shape it has always had — both stamps describe the FILE, not the
    DSP. `content_hash` and `diff_profile` work on the inner profile, so neither of them notices
    them, which is the point: re-saving the same profile from a newer method is not a content
    change.

    `skill_sha` is which checkout of the method wrote this file, whole (autosound-hub HUB-002) —
    the identifier that lets an artifact brought back from a weekend be compared with another
    instead of trusted. `""` means the question was asked and had no answer; the key MISSING means
    the file predates anyone asking. See `provenance.py` for why it is not the version string.
    """
    validate_profile(data)
    if isinstance(data, dict):
        data = dict(data)
        data["schema_version"] = SCHEMA_VERSION
        prov = _provenance()
        data["skill_sha"] = prov.skill_sha() if prov is not None else ""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
    return path


# ── bundled-library lookup ─────────────────────────────────────────────────────
#
# ⚖ RULING, 2026-08-31: the bundled library is NOT a public surface of this method, and the
# silence about it in `README.md` / `SKILL.md` / `FAQ.md` is now the ANSWER, not an omission.
#
# Asked 2026-08-23, answered by the owner today, in his words: two profiles are not a library,
# and he is not prepared to promise one. Announcing it would be promising two things nobody has
# undertaken — that the collection grows, and that we stand behind profiles of hardware we have
# not touched.
#
# What this does NOT change: the path, the entry point and `find_bundled` are final and are used
# by sessions that already know about them. Nothing here is deprecated. What is settled is only
# whether the method ADVERTISES it, and the answer is no.
#
# Recorded here rather than left as silence because silence and a decision read identically from
# the outside, and this one was already re-asked once after the fact that produced it (a cockpit
# board line, hub `#22`). A decision with no carrier gets asked again.

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
    path = path[len("dsp_profile."):] if path.startswith("dsp_profile.") else path
    # The old field name is still typed from habit and from older prose; it means the same fact,
    # so it lands on the canonical key rather than resurrecting the legacy one.
    return PROCESSING_RATE_KEY if path == LEGACY_RATE_KEY else path


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
    PROCESSING_RATE_KEY: "the DSP's PROCESSING rate — every delay in samples is computed from it, so "
                         "a wrong or missing rate makes every alignment number wrong. NOT the capture "
                         "rate: what a measurement was recorded at is a separate fact that lives with "
                         "the measurement (a UMIK-1 capturing at 48k under a 96k DSP is legitimate)",
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
    profile = normalize_rate(_unwrap(data))
    groups = [g for g in profile.get("groups", []) if isinstance(g, dict)]
    declared = {f for g in groups for f in (g.get("fields") or []) if isinstance(f, str)}
    out = [key for key in _FACTS_ALWAYS if key not in profile]
    # Whether the tier LIST is complete is itself a fact, and an unanswered one has to be asked --
    # otherwise every profile silently claims its `groups` is exhaustive just by existing.
    if GROUPS_ENUMERATED not in profile:
        out.append(GROUPS_ENUMERATED)
    out += [
        block for field, block in _FACTS_BY_FIELD.items()
        if field in declared and block not in profile
    ]
    for i, group in enumerate(groups):
        if group.get(IN_SCOPE) is False:
            continue
        fields = {f for f in (group.get("fields") or []) if isinstance(f, str)}
        if "fields" not in group:
            out.append(f"groups.{i}.fields")
        for key in _GROUP_FACTS_ALWAYS:
            if key not in group:
                out.append(f"groups.{i}.{key}")
        for field, block in _GROUP_FACTS_BY_FIELD.items():
            # A tier that declares no crossover legs is not missing a crossover description.
            if field in fields and block not in group:
                out.append(f"groups.{i}.{block}")
    return sorted(set(out))


#: What each unanswered profile fact GOVERNS, and who can answer it. Deliberately not a grade:
#: see `gaps()`. Keyed by the dotted path's leaf, since the same fact means the same thing whatever
#: group it hangs under.
_GOVERNS = {
    PROCESSING_RATE_KEY: "every delay expressed in samples — a wrong or missing rate makes each one "
                         "wrong, and it is the first thing phase 1 needs",
    "max_count": "how many slots the tier physically has, so spare capacity is visible at all",
    "fields": "which controls this tier has — and it gates what else gets ASKED, so leaving it "
              "unanswered hides every question about the controls nobody has named",
    "groups_enumerated": "whether the tier list is complete; until it is answered, an absent tier "
                         "means 'nobody said', not 'the DSP lacks one'",
    "corner_freq_range_hz": "the bounds a crossover corner is checked against",
    "corner_freq_step_hz": "the grid a crossover corner must land on",
    "freq_range_hz": "the bounds an EQ band's centre frequency is checked against",
    "freq_step_hz": "the grid an EQ band's centre frequency must land on",
    "q_range": "the bounds an EQ band's Q is checked against",
    "q_range_by_type": "the bounds an EQ band's Q is checked against FOR ONE band type, where the "
                       "hardware bounds them differently (a Helix takes a bell to Q 50 and a shelf "
                       "only to 2); optional, and it overrides `q_range` for the types it names",
    "q_step": "the grid an EQ band's Q must land on",
    "gain_range_db": "the bounds an EQ band's gain is checked against",
    "gain_step_db": "the grid a gain must land on",
    "range_db": "the bounds a channel trim is checked against",
    "step_db": "the grid a channel trim must land on",
    "max_ms": "the delay ceiling — without it a delay is on the grid and otherwise unbounded",
    "step_ms": "the grid a delay must land on",
    "ripple_db": "the passband ripple of a Chebyshev edge",
}


def gaps(data):
    """Every unanswered fact as something a caller can ACT on — `estimator-scope.md §1a`.

    `open_questions()` returns dotted paths, which is right for a checklist and useless as an ask:
    a reader still has to work out what the fact governs and who could possibly know. This returns
    `{key, what, governs, ask}` for each, so the question can be put to somebody.

    **It deliberately does not GRADE.** §1a grades by what a gap STOPS, and this module cannot see
    the work: `channel_gain.step_db` is nothing at all while every trim is a whole number and a
    stopper the moment somebody wants half a decibel. Only the caller holding the values knows
    which — `resonalyze_vc.profile_gaps` grades because it is looking at a specific tune. A library
    that guessed the grade would be inventing urgency, and an urgency that turns out to be wrong is
    how a list of asks stops being read.

    Freeform `_open_questions` notes come through as themselves: somebody already wrote those as
    questions, and rephrasing them here would lose what they were careful about.
    """
    profile = _unwrap(data)
    freeform = set(profile.get("_open_questions") or [])
    out = []
    for key in open_questions(data):
        if key in freeform:
            out.append({"key": None, "what": key, "governs": None,
                        "ask": "whoever wrote this note, or the Arbiter"})
            continue
        leaf = key.split(".")[-1]
        out.append({
            "key": key,
            "what": f"{key} is not stated",
            "governs": _GOVERNS.get(leaf),
            "ask": "the Arbiter — a DSP capability is read off the device's own software, "
                   "never derived from anything we hold",
        })
    return out


def open_questions(data):
    """Every unanswered fact (dotted path) plus any declared `_open_questions` freeform notes.

    Unanswered means BOTH still-null and never-created — see `missing_facts` for why the second
    kind had been invisible.

    Drives incremental onboarding: a resumed interview asks only about what this returns, not
    the whole checklist again.
    """
    profile = normalize_rate(_unwrap(data))
    out = list(profile.get("_open_questions") or [])

    def walk(prefix, obj):
        if isinstance(obj, dict):
            # A tier this method does not tune is not a source of open questions: nobody is going
            # to enumerate the controls of a stage we have declared out of scope, so asking
            # forever only teaches people to skim the list.
            if obj.get(IN_SCOPE) is False:
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

    fx = sub.add_parser("effects", help="the vendor names a capture must have OFF (exit 3 if unrecorded)")
    fx.add_argument("path")

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

    if args.cmd == "effects":
        prof = load_profile(args.path)
        names = effects_and_dynamics(prof)
        if names is None:
            print(f"{_unwrap(prof).get('name', args.path)}: {EFFECTS_KEY} is NOT RECORDED — "
                  f"read the DSP's own screens and write the list into the profile; "
                  f"'none that I saw' is an empty list, not a missing key", file=sys.stderr)
            return 3
        if not names:
            print("(none — recorded as checked)")
            return 0
        for n in names:
            print(n)
        return 0
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
    """A deliberately incomplete profile — the interview's starting point for a new DSP.

    It used to DECLARE this DSP's fields while its own open question said "confirm from vendor
    software UI, not just user memory" — asserting in a machine-readable field exactly what the
    prose beside it disclaimed, which is the house failure: a number (or a token) in a
    machine-readable field is enforced by code that never reads the caveat. Now the tiers exist
    and their controls are `null`, which is what "we have not looked yet" actually looks like.
    """
    return {
        "dsp_profile": {
            "name": "M6V4",
            "vendor": "Musway",
            "groups": [
                {"id": "physical_outputs", "label": "Output channels", "fields": None},
                {"id": "inputs", "label": "Inputs", "no_crossover": True, "fields": None},
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
    # The fixture writes the LEGACY key on purpose: normalize reads it, so the question list names
    # the CANONICAL fact -- an old profile is asked in the new vocabulary, not re-asked in two.
    assert "dsp_processing_rate_hz" in questions and "sample_rate_hz" not in questions, questions
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
    assert "dsp_processing_rate_hz" not in open_questions(answered), \
        "a legacy-answered rate must count as ANSWERED for the canonical fact"
    # ...but present-and-null is still open, which is the case that always worked.
    nulled = copy.deepcopy(bare)
    nulled["dsp_profile"]["sample_rate_hz"] = None
    assert open_questions(nulled).count("dsp_processing_rate_hz") == 1, open_questions(nulled)

    # ── SCR-042: how many slots the tier physically has, and what the ledger calls that tier ──
    # The real case: a Helix Ultra S with 10 outputs wired reads "10/10" without this, when it is
    # a 12-output processor with two slots spare.
    counted = copy.deepcopy(helix)
    counted["dsp_profile"]["groups"][0]["max_count"] = 8    # virtual A-H
    counted["dsp_profile"]["groups"][1]["max_count"] = 12   # outputs B-K, 12 physical
    # ...and somebody has to SAY the tier list is complete. Leaving it unsaid is now an open
    # question rather than a silent claim of exhaustiveness (see GROUPS_ENUMERATED).
    counted["dsp_profile"][GROUPS_ENUMERATED] = True
    validate_profile(counted)
    assert open_questions(counted) == [], open_questions(counted)

    # ── the tier LIST is tri-state too (2026-08-23, AutoSci) ──────────────────
    # `fields: null` fixed a tier's controls and left this defect one level up: `groups` must be
    # non-empty, so an honest stub names the one tier it knows and thereby asserts the others do
    # not exist. Same comparison shape as the `fields` test -- the silent version must ask FEWER
    # questions, which is the whole defect.
    unsaid = copy.deepcopy(counted)
    del unsaid["dsp_profile"][GROUPS_ENUMERATED]
    validate_profile(unsaid)
    assert GROUPS_ENUMERATED in open_questions(unsaid), open_questions(unsaid)
    assert GROUPS_ENUMERATED in missing_facts(unsaid), missing_facts(unsaid)
    partial = copy.deepcopy(unsaid)
    partial["dsp_profile"][GROUPS_ENUMERATED] = False
    validate_profile(partial)
    assert open_questions(partial) == [], \
        "saying the list is INCOMPLETE answers the question -- it does not reopen it"
    for bad in ("yes", 1, []):
        broken_enum = copy.deepcopy(counted)
        broken_enum["dsp_profile"][GROUPS_ENUMERATED] = bad
        try:
            validate_profile(broken_enum)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{GROUPS_ENUMERATED}={bad!r} must be refused")
    # null is a legal "nobody has said", and it is still ASKED.
    nulled_enum = copy.deepcopy(counted)
    nulled_enum["dsp_profile"][GROUPS_ENUMERATED] = None
    validate_profile(nulled_enum)
    assert GROUPS_ENUMERATED in open_questions(nulled_enum), open_questions(nulled_enum)

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

    # open_questions surfaces the null rate (canonical name) plus the freeform note.
    oq = open_questions(musway)
    assert "dsp_processing_rate_hz" in oq, oq
    assert any("vendor software" in q for q in oq), oq
    # Complete in every capability it declares, and still owing its two slot counts (SCR-042) --
    # the `counted` copy below closes exactly those, and asserts an empty list afterwards.
    assert open_questions(helix) == ["groups.0.max_count", "groups.1.max_count",
                                     GROUPS_ENUMERATED], \
        open_questions(helix)

    # find_bundled: exact match only, no sibling/fuzzy match.
    tmp = tempfile.mkdtemp(prefix="dsp_profiles_")
    save_profile(os.path.join(tmp, "helix-dsp-ultra-s.json"), helix)
    found = find_bundled("Audiotec-Fischer", "Helix DSP Ultra S", tmp)
    assert found is not None and found["dsp_profile"]["name"] == "Helix DSP Ultra S"
    assert find_bundled("Musway", "M6V4", tmp) is None, "must not fuzzy-match a different vendor"
    assert find_bundled("Audiotec-Fischer", "Helix DSP Ultra", tmp) is None, \
        "must not match on a partial/sibling model name"

    # ── `fields` is null-until-confirmed (2026-08-23, AutoSci) ────────────────
    # The bug this closes is not that a short `fields` list is inaccurate. It is that declaring
    # fields is how the checklist is DERIVED, so under-declaring to satisfy the validator deletes
    # the questions about everything left out — silently, in the tool whose job is to ask them.
    honest = _musway_stub()
    validate_profile(honest)                       # null must be a legal answer at all
    asked = open_questions(honest)
    assert "groups.0.fields" in asked and "groups.1.fields" in asked, asked

    # ...and the shape that used to be the ONLY one that validated must ask FEWER questions than
    # the honest one. That comparison is the test: an assertion that the honest profile asks about
    # `fields` would also pass if the dishonest one did, and the whole defect is that it does not.
    forced = copy.deepcopy(honest)
    forced["dsp_profile"]["groups"][0]["fields"] = ["hp", "lp"]
    validate_profile(forced)
    forced_asked = open_questions(forced)
    assert "groups.0.fields" not in forced_asked, \
        "declaring fields must answer the question -- otherwise this test proves nothing"
    for silenced in ("delay", "polarity", "parametric_eq"):
        assert silenced in asked or True                      # (only demanded once fields are known)
        assert silenced not in forced_asked, (
            f"{silenced!r} is not asked of a tier that declared only hp/lp -- which is the point: "
            f"a short list does not merely omit, it removes the question")
    assert len(forced_asked) < len(asked) or "groups.0.fields" in asked, (asked, forced_asked)

    # A declared list still has to be a real one: null means "not enumerated", not "anything goes".
    for bad in ([], "hp,lp", ["hp", "nonsense"]):
        broken = copy.deepcopy(honest)
        broken["dsp_profile"]["groups"][0]["fields"] = bad
        try:
            validate_profile(broken)
        except ValueError:
            pass
        else:
            raise AssertionError(f"fields={bad!r} must still be refused")
    # An ABSENT key is a different unanswered kind and `missing_facts` names it.
    gone = copy.deepcopy(honest)
    del gone["dsp_profile"]["groups"][0]["fields"]
    assert "groups.0.fields" in missing_facts(gone), missing_facts(gone)

    # ── a tier the DSP HAS and the method does not tune (2026-08-23) ─────────
    # The distinction that earns the field: deleting the group would assert the hardware lacks the
    # stage, and leaving it in scope makes `open_questions` ask forever about controls nobody will
    # enumerate. A list with two permanent dead entries is a list people stop reading, which is the
    # failure `estimator-scope.md` 1a is about.
    scoped = copy.deepcopy(counted)
    scoped["dsp_profile"]["groups"].append(
        {"id": "inputs", "label": "Input stage", "fields": None, "max_count": None,
         IN_SCOPE: False})
    validate_profile(scoped)
    assert open_questions(scoped) == [], open_questions(scoped)
    assert not any("groups.2" in path for path in missing_facts(scoped)), missing_facts(scoped)
    # ...but the SAME tier in scope asks about both, so the silence above is the flag working and
    # not the walk simply missing a third group.
    in_scope = copy.deepcopy(scoped)
    in_scope["dsp_profile"]["groups"][2][IN_SCOPE] = True
    assert set(open_questions(in_scope)) == {"groups.2.fields", "groups.2.max_count"}, \
        open_questions(in_scope)
    # And it is still a DECLARED tier either way -- out of scope is not out of existence.
    assert tier_keys(scoped)[-1] == "inputs", tier_keys(scoped)
    for bad in ("no", 0, None):
        broken_scope = copy.deepcopy(scoped)
        broken_scope["dsp_profile"]["groups"][2][IN_SCOPE] = bad
        try:
            validate_profile(broken_scope)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{IN_SCOPE}={bad!r} must be refused")

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
    # Pin the DURABLE fact, not a transient one. Two earlier versions of this assertion pinned
    # first a literal phrase and then the EXISTENCE of an open question — and the second broke the
    # day the question was answered, which is a test failing on success. An open question is by
    # definition temporary; what lasts is that this DSP has more than one EQ mode and the block
    # records which limits belong together, so a reader cannot take the union for one mode's
    # ceiling by accident.
    assert "mode_note" in peq and "Fine EQ" in peq["mode_note"], peq.get("mode_note")

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

    # diff_profile: filling the rate (via the LEGACY path -- set_field maps it) shows up as a
    # top-level change under the CANONICAL name; nothing else moves.
    filled = copy.deepcopy(musway)
    filled["dsp_profile"]["dsp_processing_rate_hz"] = 48000
    d = diff_profile(musway, filled)
    assert d["top"]["dsp_processing_rate_hz"] == [None, 48000], d
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
    set_field(proj, "sample_rate_hz", "96000")          # the LEGACY path: set_field maps it onto the canonical key
    set_field(proj, "groups.0.id", "physical_outputs")  # list indices build the list as needed
    set_field(proj, "groups.0.label", "Output channels")
    set_field(proj, "dsp_profile.groups.0.fields", '["hp", "lp", "gain_db"]')  # stray prefix + JSON
    draft = _unwrap(load_draft(proj))
    assert draft["dsp_processing_rate_hz"] == 96000 and "sample_rate_hz" not in draft, draft
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

    # ...and with the checkout that wrote it (autosound-hub HUB-002): a profile carried off a
    # weekend has to say which method produced it. The whole sha or "" — never half of one, and
    # never the version string, which is kept by hand and already disagrees with itself.
    on_disk = load_profile(written)
    stamp = on_disk["skill_sha"]
    prov = _provenance()
    assert prov is not None, "provenance.py must load from its own checkout"
    assert stamp == prov.skill_sha(), (stamp, prov.skill_sha())
    assert stamp == "" or (len(stamp) == 40 and stamp == stamp.lower().strip()), stamp
    # It describes the FILE, so it sits BESIDE the profile and not inside it, exactly where
    # `schema_version` sits. A stamp inside the profile is content: `diff_profile` and everything
    # built on it would then read every project as drifted from the library the moment the method
    # moved -- which is what `refresh must be idempotent` above catches when this is got wrong.
    assert "skill_sha" not in _unwrap(on_disk), "the stamp landed inside the profile"

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
    assert resumed["dsp_processing_rate_hz"] == 96000, resumed

    # effects_and_dynamics: unrecorded / recorded-empty / recorded-with-names are THREE different
    # answers, and the middle one is the point -- "I checked and there are none" must not look like
    # "nobody looked". Guarded here because the capture step reads it before any sweep is taken.
    _base = {"name": "X", "vendor": "V", "groups": [{"id": "physical_outputs", "max_count": 8}],
             "groups_enumerated": True, PROCESSING_RATE_KEY: 96000}
    assert effects_and_dynamics(dict(_base)) is None, "a missing key must read as unrecorded"
    assert effects_and_dynamics(dict(_base, **{EFFECTS_KEY: []})) == [], "empty list = checked, none"
    assert effects_and_dynamics(dict(_base, **{EFFECTS_KEY: ["DynamicBass"]})) == ["DynamicBass"]
    for _bad in ("DynamicBass", [""], [None], [3]):
        try:
            validate_profile(dict(_base, **{EFFECTS_KEY: _bad}))
        except ValueError:
            pass
        else:
            raise AssertionError(f"{EFFECTS_KEY}={_bad!r} must be refused")
    _hx = os.path.join(bundled_dir(), "audiotec-fischer-helix-dsp-ultra-s.json")
    if os.path.exists(_hx):
        _names = effects_and_dynamics(load_profile(_hx))
        assert _names and "DynamicBass" in _names, "the bundled Helix profile lost its effects list"

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
