#!/usr/bin/env python3
"""The intake as DATA — every field Phase −1 asks, its enumeration, and what the gate needs (SCR-059).

Phase −1 is already a fixed set of questions with fixed answers. The DSP half says so out loud —
`dsp_profile.CAPABILITY_CHECKLIST` is a checklist with enumerated answers — and the rest of the
phase is the same material in a different state: `references/phases/phase_-1_intake.md` §1–§2 is a
list of fields (the car's four parts, the channel map, the measurement chain, the reference seat,
the curve seed) that exists only as prose and as a conversation.

**What that costs, watched twice on the Arbiter's own machine** (`tcc:docs/SESSION-ANALYSIS-2026-09-14.md`,
two cars, two processors): a front-end cannot render the questions, cannot check an answer before
the session starts, and cannot tell a person what is still missing — so the car half was not asked
by any window and arrived in long free-text messages AFTER the Phase-0 gate refused, with the
project already open and the interview already run. And the seat was answered "driver only", revised
to "driver and front passenger" five minutes later, and a recorded decision had to be voided: two
turns in a dialogue, one control on a form.

So: the same intake, offered as data. Three tables and a writer —

* `FIELDS` — every field: its id, its group, the question in the method's own words, whether it is
  required, its enumeration where it has one, and **where the answer lands** (`writes`).
* `WHEN` — the step that first needs each field. Only `now` (what starting to measure needs) is
  asked up front; the rest waits for its phase and stays in the table (2026-09-22,
  `docs/DESIGN-2026-09-22-intake-simplified.md`).
* `COUPLINGS` — which fields are ONE question, and why. A form renders a couple as one control;
  that is the whole fix for the voided seat decision.
* `gate_requirements()` — the files and keys `contract.py check --gate` decides on, read off
  `contract.GATE_REQUIRED` rather than copied, so the list cannot drift from the gate that enforces it.
* `save()` / `save_car()` / `save_channel()` / `save_amp()` — the writer for the half that had
  none. `dsp_profile.set_field` already takes the processor's answers; the car, the channel map and
  the measurement chain had no route in that did not go through a conversation.

⛔ **What this is NOT.** Not a second copy of anything: the DSP's vocabulary stays in
`dsp_profile`, the gate's list stays in `contract`, the naming stays in `naming`, and the field
table points at them. Not a move of Phase −1 into a front-end either — the order of work, the gates
and the doctrine stay the method's (`phase_-1_intake.md` §0.5). What a front-end may do with this is
COLLECT; what it still owes the session is unchanged and written in that file.

    intake.py fields [--group car] [--required] [--json]
    intake.py couplings [--json]
    intake.py gate [<project-dir>] [--json]
    intake.py missing <project-dir> [--json]
    intake.py set <project-dir> <field-id> <value> [--source user]
    intake.py set-channel <project-dir> <code> key=value ... [--source user]

stdlib only, py3.9+.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import contract  # noqa: E402  -- the gate's own list, never a copy of it
import dsp_profile  # noqa: E402
import naming  # noqa: E402
import project  # noqa: E402


class IntakeError(ValueError):
    """A refused answer: an unknown field, a value outside its enumeration, a half-given couple."""


# ── the groups ────────────────────────────────────────────────────────────────
#: What a field BELONGS to. A form renders one page per group; `project` is the one group a
#: front-end answers about itself (`project-intake.md` §0: what `get_tcc_state` reports is settled,
#: not a question to re-ask).
GROUPS = (
    ("project", "what the front-end already settled: language, reviewer, where the project lives"),
    ("car", "the cabin — the four parts that identify it, and which side the driver sits on"),
    ("dsp", "the processor and what it can do (the capability profile's half)"),
    ("channel_map", "what is wired where: codes, slots, tiers, drivers, routing"),
    ("measurement_chain", "how the signal reaches the DSP, and which input carries the sweep"),
    ("rew", "the measurement rig: mic, calibration, loopback, capture rate, the API"),
    ("goal", "what the tune is FOR — engineering, not taste"),
    ("target_curve", "the curve seed and the taste that shapes it (Phase 5's material)"),
)

# ── the enumerations ──────────────────────────────────────────────────────────
# KEYS, not labels. A consumer shows them in its own four languages (the same split the Arbiter's
# form keeps: `gates/side_effect.py` FORM_KINDS are keys, FORM_LABELS are the form's own words), so
# a key that changes is news for every consumer and a label that changes is nobody's business here.
BODIES = ("sedan", "hatchback", "wagon", "coupe", "suv", "van", "pickup", "other")
DRIVE_SIDES = ("LHD", "RHD")
SOURCE_KINDS = ("head_unit", "streamer", "phone", "laptop", "other")
#: How the signal ENTERS the DSP (`phase_-1_intake.md` §1.2).
CONNECTIONS = ("optical", "coax", "rca", "bt", "usb", "aux")
#: `project-intake.md` §4 — what you CAN do, decided by the two questions below it, not declared.
CAPABILITY_LEVELS = ("1", "2", "3")
#: The INTENT on top of the level: how much of the tune this session is (`project-intake.md` §4,
#: Level 0 and "pick the MODE here"). Orthogonal to the level — which is why it is its own field.
MODES = ("new_tune", "improve_existing", "light_touch")
#: How the tune is DESIGNED (`virtual-first.md`). Needs level 1 + a loopback on one clock + a
#: hardware-verified filter model; miss one and the desk half degrades, the capture does not.
DESIGN_PATHS = ("virtual_first", "iterative")
#: Where a driver sits and how it is loaded (§1.5–§1.6). `position` and `enclosure` are asked of
#: every channel, and both vary on the same car — a profile is a checklist, never a fact to cite.
POSITIONS = ("door", "a_pillar", "kick", "dash", "deck", "rear_shelf", "under_seat", "trunk", "other")
ENCLOSURES = ("sealed", "ported", "free_air", "pod", "infinite_baffle")
#: New drivers get a break-in before a precise alignment (`project-intake.md` §3.6).
CONDITIONS = ("new", "broken_in")
#: THE rig question (the Arbiter, 2026-09-22: mic type and calibration file do not matter, the
#: loopback does). `acoustic` is REW's acoustic timing reference through the mic: it gives timing,
#: but it does NOT qualify for virtual-first (`virtual-first.md`) -- which is why it is its own key
#: and not a kind of `physical`. `none` stays for a rig with neither.
LOOPBACKS = ("physical", "acoustic", "none")
PURPOSES = ("competition", "enjoyment", "both")
#: Formats judge differently and some techniques are mutually exclusive, so several = several
#: presets, not one tune (`competition.md`). Multi-select.
FORMATS = ("EMMA", "AYA", "CARMusic")
#: ⚠️ THE field this ticket was opened over. Three choices, one control: asked as two turns it was
#: answered "driver only" and corrected five minutes later, and the decision already recorded had
#: to be voided (`tcc:docs/SESSION-ANALYSIS-2026-09-14.md` §4a).
#: S-032: the six kinds of project, from `project.py` so the question and the stored answer cannot
#: drift. The field id stays `goal.reference_seat` because a consumer's form is keyed by it; what
#: changed is what it MEANS — not a goal inside a project, but what the project IS.
REFERENCE_SEATS = project.PROJECT_TYPES
STAGE_PRIORITIES = ("width", "depth", "height", "center_focus", "envelopment", "front_only")
LOVES = ("bass", "vocals", "winds_strings", "acoustic", "electronica")
LOUDNESS = ("loud", "moderate")
#: What the person can actually PLAY — Phase 4 proposes only from this (`test-tracks.md`). Read off
#: the `library` column of that file's track table, so a library described there becomes a choice
#: without an edit here; `streaming` is the one way to play them that is not a disc of its own.
TRACK_LIBRARIES_DOC = os.path.join(_HERE, "..", "references", "patterns", "test-tracks.md")


def _track_libraries(path=TRACK_LIBRARIES_DOC):
    found = []
    try:
        with open(path, encoding="utf-8") as fh:
            in_table = False
            for line in fh:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if line.startswith("| id | library"):
                    in_table = True
                    continue
                if in_table and not line.startswith("|"):
                    break
                if in_table and len(cells) > 1 and cells[1] and not cells[1].startswith("-"):
                    key = cells[1].lower()
                    if key not in found:
                        found.append(key)
    except OSError:
        pass
    return tuple(found or ("carmus", "chesky", "emma", "aya", "mono", "own")) + ("streaming",)


TRACK_LIBRARIES = _track_libraries()
TONE = ("warm", "neutral", "bright")
BASS = ("bass_heavy", "neutral")
PRESENTATION = ("forward", "neutral", "laid_back")
CHARACTER = ("accuracy", "balanced", "fun")
LANGUAGES = project.LANGUAGES  # one list, so the question and the stored answer cannot drift
#: Provenance and rates come from the modules that own them — referenced, never retyped.
FACT_SOURCES = project.FACT_SOURCES
PLAUSIBLE_RATES_HZ = dsp_profile.PLAUSIBLE_RATES_HZ

#: The codes the method SUGGESTS (`naming-and-structure.md`). Not an enumeration: the glossary is
#: agreed with the person and written down (§0.5 step 5), and a car with two subs or no centre
#: names its own set. A form offers these and takes what it is told.
SUGGESTED_CHANNEL_CODES = ("sw", "sw-f", "sw-r", "w-L", "w-R", "m-L", "m-R", "tw-L", "tw-R", "c",
                           "r-L", "r-R")
#: The VIRTUAL tier's codes. The method names only `VFL` (the routing examples); the rest of the set
#: is the Arbiter's own, as his Helix build names it (2026-09-22) -- offered, never enforced.
SUGGESTED_VIRTUAL_CODES = ("VFL", "VFR", "VRL", "VRR", "VC", "VSW")
#: What an UNUSED slot is called: `off-<tier>-<slot>`, hidden, role `unused` -- the naming
#: `project.py` already uses for spare slots (SCR-042) and TCC shows as `off-virt-F` / `off-out-A`.
OFF_PREFIX = {"channels": "off-out", "virtual_channels": "off-virt"}
#: The ledger tiers a channel row names most often (`dsp_profile.ledger_tier`). Suggested, not
#: enumerated: a profile may declare a tier of its own.
SUGGESTED_TIERS = ("channels", "virtual_channels", "inputs")
SUGGESTED_ROLES = ("sub", "woofer", "midbass", "midrange", "tweeter", "fullrange", "unused")
#: Common measurement mics. An open set -- the form offers these and takes what it is told.
SUGGESTED_MICS = ("miniDSP UMIK-1", "miniDSP UMIK-2", "Dayton Audio EMM-6", "Dayton Audio iMM-6")
SUGGESTED_CONSTRAINTS = ("no_door_work", "no_trim_changes", "budget", "time")
#: A closed list with an escape (`other`), so a form can offer checkboxes -- several may apply.
GENRES = ("rock", "pop", "jazz", "classical", "electronic", "hip_hop", "acoustic", "metal", "other")
#: The target curves as the Nono Tuning Tool offers its presets (the Arbiter, 2026-09-22), spelled
#: as NTT spells them. They are their authors' and are NOT bundled: the file is downloaded at
#: nonotuningtool.com (SKILL.md, `target_curves_guide.md`).
NTT_CURVE_PRESETS = ("Audiofrog", "Whitledge", "Half Whitledge", "Harman", "JBL", "JL Audio", "Jazzi",
                     "Jazzi v2", "RAW-Cat", "ResoNix Accurate", "ResoNix Laid-Back", "ResoNix 2026",
                     "ATF Daily", "ATF SQ", "EPY", "Hanatsu")
NTT_URL = "https://nonotuningtool.com"
#: The one curve that SHIPS with the skill -- "ours", always there, nothing to download.
BUNDLED_CURVE = "SQ-Comp-Ref"
BUNDLED_CURVE_FILE = os.path.join(_HERE, "..", "references", "patterns", "target-curves", "curves",
                                  "SQ-Comp-Ref_0db_REW.txt")
SUGGESTED_CURVES = (BUNDLED_CURVE,) + NTT_CURVE_PRESETS


def _bundled_dsps():
    """Vendors and models of the bundled DSP profiles -- the choices a form offers for the DSP.

    Read off the library, so a profile added there becomes a choice without an edit here. A
    library that cannot be read offers nothing, and the field stays a free-text answer.
    """
    try:
        rows = dsp_profile.list_bundled()
    except OSError:
        rows = []
    return (tuple(sorted({v for v, _m, _p in rows if v})),
            tuple(sorted({m for _v, m, _p in rows if m})))


BUNDLED_DSP_VENDORS, BUNDLED_DSP_MODELS = _bundled_dsps()


def known_dsps():
    """`[{"vendor", "model", "tiers"}]` -- every processor the skill ships a profile for.

    A form offers the vendor first and then only THAT vendor's models, so a Musway vendor with a
    Helix model cannot be picked: the pair is one identity (`COUPLINGS["dsp_identity"]`).
    """
    out = []
    for vendor, model, path in dsp_profile.list_bundled():
        try:
            tiers = dsp_profile.tier_keys(dsp_profile.load_profile(path))
        except (OSError, ValueError):
            tiers = []
        try:
            groups = _groups_of(dsp_profile.load_profile(path))
        except (OSError, ValueError):
            groups = []
        try:
            knobs = dsp_knobs(dsp_profile.load_profile(path))
        except (OSError, ValueError):
            knobs = []
        out.append({"vendor": vendor, "model": model, "tiers": tiers, "groups": groups,
                    "knobs": knobs})
    return out


def _same_dsp(profile, vendor, model):
    """Does this profile describe THIS processor? Case-insensitive, exact -- `find_bundled`'s rule."""
    p = dsp_profile._unwrap(profile)
    return (str(p.get("vendor") or "").strip().lower() == vendor.strip().lower()
            and str(p.get("name") or "").strip().lower() == model.strip().lower())


def _groups_of(profile):
    """The tiers a profile declares, as a form needs them: key, label, slot count, slot style."""
    out = []
    for g in dsp_profile._unwrap(profile).get("groups") or []:
        if not isinstance(g, dict) or not g.get("id"):
            continue
        row = {"tier": dsp_profile.ledger_tier(g["id"]), "label": g.get("label") or g["id"],
               "max_count": g.get("max_count"), "letters": g.get("row_id_style") == "letter",
               "in_scope": g.get("in_scope", True) is not False}
        row["slots"] = slot_names(row)
        out.append(row)
    return out


def slot_names(group):
    """The slot labels of one tier: `A, B, ...` on a letter-style processor, `1, 2, ...` otherwise;
    none when the tier's size is not known (a new processor before its slot count is answered)."""
    n = group.get("max_count")
    if not isinstance(n, int) or n <= 0:
        return []
    if group.get("letters"):
        return [chr(ord("A") + i) if i < 26 else f"A{chr(ord('A') + i - 26)}" for i in range(n)]
    return [str(i + 1) for i in range(n)]


def off_code(tier, slot):
    """`off-out-A`, `off-virt-F`: the name of a slot nothing is wired to."""
    return f"{OFF_PREFIX.get(tier, 'off-' + str(tier))}-{slot}"


def dsp_state(project_dir):
    """What the project's processor is, and whether the skill knows it -- `{"vendor", "model",
    "source", "tiers", "groups", "new"}`.

    `source` is where the tier list came from: the project's own `dsp_profile.json`, the bundled
    library on an exact vendor+model match, or the interview draft. `new` is True only when a
    vendor and model are recorded and nothing describes them -- that is when the processor's base
    questions are asked, once (`place="new_dsp"`). None means "not chosen yet".
    """
    data = _read_project(project_dir) or {}
    dsp = data.get("dsp") or {}
    vendor, model = dsp.get("vendor") or "", dsp.get("model") or ""
    out = {"vendor": vendor, "model": model, "source": None, "tiers": [], "groups": [], "knobs": [],
           "new": None}

    def take(profile, source, new):
        out.update(source=source, tiers=dsp_profile.tier_keys(profile), groups=_groups_of(profile),
                   knobs=dsp_knobs(profile))
        if new is not None:
            out["new"] = new

    # A profile on disk counts only when it describes the processor project.json names: after a
    # processor change the old one is not this project's any more (round 4, `change_dsp`).
    own = dsp_profile.profile_path(project_dir)
    if os.path.isfile(own):
        try:
            prof = dsp_profile.load_profile(own)
            if not (vendor and model) or _same_dsp(prof, vendor, model):
                take(prof, "project", False)
                return out
        except (OSError, ValueError):
            pass
    if vendor and model:
        bundled = dsp_profile.find_bundled(vendor, model)
        if bundled is not None:
            take(bundled, "bundled", False)
            return out
        out["new"] = True
    draft = dsp_profile.draft_path(project_dir)
    if os.path.isfile(draft):
        try:
            prof = dsp_profile.load_profile(draft)
            if not (vendor and model) or _same_dsp(prof, vendor, model):
                take(prof, "draft", None)
        except (OSError, ValueError):
            pass
    return out


def _set_aside(path, vendor, model):
    """Move a file that describes ANOTHER processor out of the way, never delete it."""
    import car_profile

    slug = car_profile.body_slug(vendor or "unknown", model or "dsp") or "previous"
    stem, ext = os.path.splitext(path)
    target, n = f"{stem}.replaced-{slug}{ext}", 1
    while os.path.exists(target):
        n += 1
        target = f"{stem}.replaced-{slug}-{n}{ext}"
    os.replace(path, target)
    return target


def change_dsp(project_dir, vendor, model, replace_map=False):
    """Record the project's processor -- and say what happens to the old one's channel map.

    The rule (the Arbiter, round 4): slots are a PROCESSOR's, so a new processor gets a new map and
    nothing is merged across processors. When the processor changes and the old one's map has
    slots, this refuses unless `replace_map` -- and with it:

    * the old map is kept as a RECORD, `dsp.previous_maps[]` ({vendor, model, slots}), not deleted;
    * spare rows (`off-…`, never measured, no history) are removed; live channels keep their code,
      driver and history, and lose `slot`/`tier`/`hidden`: they are the car's speakers, and they
      are placed again on the new processor's slots;
    * `dsp.tiers_used` is cleared (it named the old processor's tiers);
    * a `dsp_profile.json` or draft that describes the OLD processor is moved aside
      (`…replaced-<vendor>-<model>.json`), so the Phase-0 gate cannot pass on another unit's profile.
      One that cannot be read, or that a newer method wrote, is moved aside the same way, unread and
      byte for byte, and one line on stderr names it and where it went (#136, ruling R26): this step
      exists to replace that profile, and a refusal walled the person out of the one step that sets
      the damage aside. Nothing is ever carried over from a profile here, readable or not: it is read
      only to tell whose it is.

    Returns `{"vendor", "model", "replaced": <slots moved to the record>, "set_aside": [paths]}`, and
    `"said": [lines]` when a profile that could not be read was set aside.

    One writer's from its read to its last move (#141): the project's lock is held over the change of `project.json`
    (`Project.update`) and the profiles it sets aside after, so what it read is what it changes.
    """
    vendor, model = str(vendor or "").strip(), str(model or "").strip()
    if not (vendor and model):
        raise IntakeError("the DSP is a vendor AND a model — nothing was written")
    out = {"vendor": vendor, "model": model, "replaced": 0, "set_aside": []}
    old, others, unread = {}, [], {}

    def change(data):
        dsp = dict(data.get("dsp") or {})
        old_v, old_m = dsp.get("vendor") or "", dsp.get("model") or ""
        old.update(vendor=old_v, model=old_m)
        same = old_v.lower() == vendor.lower() and old_m.lower() == model.lower()
        rows = [c for c in data.get("channels") or [] if isinstance(c, dict)]
        slotted = [c for c in rows if c.get("slot") and c.get("tier")]
        if same:
            return project.UNCHANGED
        if slotted and (old_v or old_m) and not replace_map:
            raise IntakeError(
                f"the processor changes from {old_v} {old_m} to {vendor} {model}, and the old one's "
                f"channel map has {len(slotted)} slot(s). Slots are a processor's: the map is REPLACED "
                "(the old one kept as a record in dsp.previous_maps). Confirm to go on — nothing was written")
        if slotted:
            dsp.setdefault("previous_maps", []).append({
                "vendor": old_v, "model": old_m,
                "slots": [{k: c.get(k) for k in ("code", "tier", "slot", "hidden") if k in c}
                          for c in slotted]})
            kept = []
            for c in rows:
                spare = (c.get("role") == "unused" and str(c.get("code", "")).startswith("off-")
                         and not c.get("id") and not c.get("previous_names"))
                if spare:
                    continue
                if c in slotted:
                    c = {k: v for k, v in c.items() if k not in ("slot", "tier", "hidden")}
                kept.append(c)
            data["channels"] = kept
            out["replaced"] = len(slotted)
        dsp.pop("tiers_used", None)
        dsp.update(vendor=vendor, model=model)
        data["dsp"] = dsp
        # Which profiles on disk to set aside is settled BEFORE anything is written. One that cannot be read (#136:
        # `load_profile` raises for it now) is not taken as this processor's: it is set aside with the rest, never read
        # for anything (ruling R26). Raised after the save, it left the change half made.
        for path in (dsp_profile.profile_path(project_dir), dsp_profile.draft_path(project_dir)):
            if not os.path.isfile(path):
                continue
            try:
                mine = _same_dsp(dsp_profile.load_profile(path), vendor, model)
            except Exception as exc:  # noqa: BLE001 -- matched below; anything else still raises
                if not getattr(exc, "is_unreadable", False):
                    raise
                mine, unread[path] = False, exc.reason
            if not mine:
                others.append(path)

    with project._hold(project_dir):
        project.Project(project_dir).update(change)
        for path in others:
            target = _set_aside(path, old["vendor"], old["model"])
            out["set_aside"].append(target)
            if path in unread:
                line = (f"{path} {unread[path]} -- set aside as {target}, unread and byte for byte; "
                        "nothing in it was carried over")
                out.setdefault("said", []).append(line)
                print(line, file=sys.stderr)
    return out


#: The new-processor form's closed choices -- read off what the bundled profiles already record,
#: not invented: the Helix's band types, the crossover families the maths can model, and the slope
#: menu a Musway offers (every order a family is recorded at in the library).
EQ_BAND_TYPES = ("PK", "LSH", "HSH", "APF1", "APF2")
XO_FAMILIES = ("LR", "BW", "BE")
XO_SLOPES = (6, 12, 18, 24, 30, 36, 42, 48)
TIER_LABELS = {"channels": "Output channels", "virtual_channels": "Virtual channels", "inputs": "Inputs"}


def _group_id(tier):
    return "physical_outputs" if tier == "channels" else tier


def _pos_int(value, what):
    if value in (None, ""):
        return None
    try:
        n = int(str(value).strip())
    except ValueError:
        raise IntakeError(f"{what} is a whole number, not {value!r} — nothing was written") from None
    if n < 1:
        raise IntakeError(f"{what} must be at least 1, not {n} — nothing was written")
    return n


def _pos_float(value, what):
    if value in (None, ""):
        return None
    try:
        x = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise IntakeError(f"{what} is a number, not {value!r} — nothing was written") from None
    if x <= 0:
        raise IntakeError(f"{what} must be above zero — nothing was written")
    return x


def save_new_dsp(project_dir, answers):
    """The NEW processor's base, from its own form, into the interview draft -- once.

    Only for a processor the skill has no profile of (`dsp_state()["new"]`). Everything goes into
    `dsp_profile.draft.json` through the profile's own writer (`dsp_profile.set_field`), under the
    keys `dsp_profile.missing_facts` expects: per tier `max_count`, `row_id_style`, `fields`, `eq`,
    `crossover_filters`; at the top `parametric_eq`, `delay`, `polarity`, `phase_control`,
    `presets`, the processing rate and `groups_enumerated`. The session finalises the draft
    (`dsp_profile.py finalize`); this writes what the person answered and nothing it did not.

    `answers`: {"tiers": {tier: {"count", "letters", "fields"}}, "eq": {"bands", "types",
    "file_import"}, "crossover": {"types", "slopes", "independent"}, "delay": {"step_ms", "max_ms"},
    "presets": {"count", "input_switches"}, "rate"}.

    One writer's from its first read to its last field (#141, R20): the project's lock is held over the read of what
    the processor is, the draft or profile of another processor set aside, the draft started and every field set.
    The set-aside ran with no lock, and each later write took it for itself: a lock held past the wait moved the old
    draft aside, then said "nothing was written".
    """
    with project._hold(project_dir):
        return _save_new_dsp(project_dir, answers)


def _save_new_dsp(project_dir, answers):
    """`save_new_dsp`'s work, under its hold."""
    st = dsp_state(project_dir)
    if not st["new"]:
        raise IntakeError("the base is asked only for a processor the skill has no profile of; this "
                          "one is read off its profile — nothing was written")
    tiers = answers.get("tiers") or {}
    if not tiers:
        raise IntakeError("a processor has at least one tier — nothing was written")
    for tier, row in tiers.items():
        bad = [f for f in row.get("fields") or [] if f not in dsp_profile.FIELD_VOCABULARY]
        if bad:
            raise IntakeError(f"{tier}: unknown control(s) {bad} — nothing was written")
    rate = answers.get("rate")
    if rate not in (None, ""):
        rate = int(rate)
        if rate not in PLAUSIBLE_RATES_HZ:
            raise IntakeError(f"{rate} is not a processing rate a DSP runs at — nothing was written")
    eq = answers.get("eq") or {}
    xo = answers.get("crossover") or {}
    eq_block = {k: v for k, v in (("bands_per_channel", _pos_int(eq.get("bands"), "EQ bands")),
                                   ("band_types", [t for t in eq.get("types") or [] if t in EQ_BAND_TYPES] or None),
                                   ("file_import", eq.get("file_import"))) if v is not None}
    slopes = sorted({int(x) for x in xo.get("slopes") or [] if int(x) in XO_SLOPES})
    xo_block = {}
    if xo.get("types"):
        xo_block["types"] = {t: ({"orders_db_per_oct": slopes} if slopes else {})
                             for t in xo["types"] if t in XO_FAMILIES}
    if xo.get("independent") is not None:
        xo_block["independent_hp_lp"] = bool(xo["independent"])
    delay = {k: v for k, v in (("step_ms", _pos_float((answers.get("delay") or {}).get("step_ms"), "delay step")),
                                ("max_ms", _pos_float((answers.get("delay") or {}).get("max_ms"), "delay maximum")))
             if v is not None}
    counts = {t: _pos_int(row.get("count"), f"{t} slot count") for t, row in tiers.items()}
    presets = answers.get("presets") or {}
    preset_count = _pos_int(presets.get("count"), "preset count")

    # A draft or profile left by ANOTHER processor would seed this one's draft (`load_draft` falls
    # back to the finished profile): moved aside first, as `change_dsp` does.
    for path in (dsp_profile.draft_path(project_dir), dsp_profile.profile_path(project_dir)):
        if os.path.isfile(path):
            try:
                mine = _same_dsp(dsp_profile.load_profile(path), st["vendor"], st["model"])
            except (OSError, ValueError):
                mine = False
            if not mine:
                _set_aside(path, "other", "dsp")
    data = dsp_profile.start_draft(project_dir, st["vendor"], st["model"])
    have = {g.get("id"): g for g in dsp_profile._unwrap(data).get("groups") or [] if isinstance(g, dict)}
    groups, declared = [], set()
    for tier, row in tiers.items():
        gid = _group_id(tier)
        g = dict(have.get(gid) or {"id": gid, "label": TIER_LABELS.get(tier, tier)})
        fields = [f for f in dsp_profile.FIELD_VOCABULARY if f in (row.get("fields") or [])]
        g["fields"] = fields or None
        g["max_count"] = counts[tier]
        g["row_id_style"] = "letter" if row.get("letters", True) else "number"
        if "eq" in fields and eq_block:
            g["eq"] = dict(eq_block)
        if ({"hp", "lp"} & set(fields)) and xo_block:
            g["crossover_filters"] = dict(xo_block)
        declared |= set(fields)
        groups.append(g)
    dsp_profile.set_field(project_dir, "groups", groups)
    dsp_profile.set_field(project_dir, "groups_enumerated", True)
    if eq_block and "eq" in declared:
        dsp_profile.set_field(project_dir, "parametric_eq", eq_block)
    if delay and "ta_ms" in declared:
        dsp_profile.set_field(project_dir, "delay", dict(delay, min_ms=0))
    if "polarity" in declared:
        dsp_profile.set_field(project_dir, "polarity", {"values": ["NORM", "INV"]})
    if "phase_deg" in declared:
        dsp_profile.set_field(project_dir, "phase_control", {"continuous": True})
    if preset_count is not None or presets.get("input_switches") is not None:
        block = {}
        if preset_count is not None:
            block["count"] = preset_count
        if presets.get("input_switches") is not None:
            block["input_selection_switches_with_preset"] = bool(presets["input_switches"])
        dsp_profile.set_field(project_dir, "presets", block)
    if rate not in (None, ""):
        dsp_profile.set_field(project_dir, dsp_profile.PROCESSING_RATE_KEY, rate)
    return dsp_state(project_dir)


def new_dsp_answers(project_dir):
    """What the new-processor form already recorded, in the shape it posts -- for pre-filling."""
    st = dsp_state(project_dir)
    out = {"tiers": {}, "eq": {}, "crossover": {}, "delay": {}, "presets": {}, "rate": None}
    if st["source"] != "draft":
        return out
    p = dsp_profile._unwrap(dsp_profile.load_profile(dsp_profile.draft_path(project_dir)))
    for g in p.get("groups") or []:
        if not isinstance(g, dict):
            continue
        out["tiers"][dsp_profile.ledger_tier(g["id"])] = {
            "count": g.get("max_count"), "letters": g.get("row_id_style", "letter") == "letter",
            "fields": list(g.get("fields") or [])}
        xo = g.get("crossover_filters") or {}
        if xo and not out["crossover"]:
            types = xo.get("types") or {}
            out["crossover"] = {"types": list(types),
                                "slopes": sorted({s for t in types.values() for s in (t or {}).get("orders_db_per_oct") or []}),
                                "independent": xo.get("independent_hp_lp")}
    eq = p.get("parametric_eq") or {}
    out["eq"] = {"bands": eq.get("bands_per_channel"), "types": eq.get("band_types") or [],
                 "file_import": eq.get("file_import")}
    out["delay"] = {k: (p.get("delay") or {}).get(k) for k in ("step_ms", "max_ms")}
    pr = p.get("presets") or {}
    out["presets"] = {"count": pr.get("count"), "input_switches": pr.get("input_selection_switches_with_preset")}
    out["rate"] = dsp_profile.processing_rate_hz(p)
    return out


def channel_map(project_dir):
    """The processor's channel map as TCC draws it: one entry per tier in use, one row per slot.

    `[{"tier", "label", "total", "used", "rows": [{"slot", "code", "on"}]}]`. The tiers are the ones
    the person said this car uses (`dsp.tiers_used`), else every in-scope tier the processor has.
    A tier of known size lists EVERY slot -- a spare one is a row, not an absence; a tier whose
    size is not known yet lists only the rows the project already has.
    """
    dsp = dsp_state(project_dir)
    data = _read_project(project_dir) or {}
    used = [t for t in ((data.get("dsp") or {}).get("tiers_used") or [])]
    channels = [c for c in data.get("channels") or [] if isinstance(c, dict)]
    out = []
    for g in dsp["groups"]:
        if (used and g["tier"] not in used) or (not used and not g["in_scope"]):
            continue
        mine = {str(c.get("slot")): c for c in channels if c.get("tier") == g["tier"] and c.get("slot")}
        slots = slot_names(g) or sorted(mine)
        rows = []
        for slot in slots:
            c = mine.get(slot) or {}
            code = c.get("code") or ""
            on = bool(code) and not c.get("hidden") and c.get("role") != "unused"
            rows.append({"slot": slot, "code": code, "on": on})
        out.append({"tier": g["tier"], "label": g["label"], "total": len(slots),
                    "used": sum(1 for r in rows if r["on"]), "rows": rows,
                    "sized": bool(slot_names(g))})
    return out


def save_slot(project_dir, tier, slot, code=None, on=True):
    """Switch one slot on under `code`, or off -- through `Project`'s own writers.

    On: the slot's existing row (if any) is RENAMED to `code` (`rename_channel`, so a spare that
    becomes a channel keeps one identity), then given `tier`/`slot` and un-hidden. Off: the row is
    renamed to `off-<tier>-<slot>`, hidden, `role: unused` -- the row stays, because it is the only
    record that the slot exists (SCR-042). A code already used by ANOTHER slot is refused.

    One writer's from its first read to its last write (#141): the project's lock is held over the whole switch -- the
    read that decides it and each write after, each one `Project.update` or a `Project` writer -- so the slot it read
    is the slot it writes.
    """
    tier, slot = str(tier or "").strip(), str(slot or "").strip()
    if not tier or not slot:
        raise IntakeError("a slot needs its tier and its label — nothing was written")
    target = str(code or "").strip() if on else off_code(tier, slot)
    if on and (not target or target.startswith("off-")):
        raise IntakeError(f"slot {slot}: pick or type the channel's code to switch it on "
                          "— nothing was written")
    handle = project.Project(project_dir)

    def slot_row(data):
        return next((c for c in data.get("channels") or []
                     if isinstance(c, dict) and c.get("tier") == tier and str(c.get("slot")) == slot), None)

    def drop_spare(data):
        gone = slot_row(data)
        data["channels"] = [c for c in data["channels"] if c is not gone]

    def back_on(data):                           # a spare switched back on is no longer unused
        row = handle.resolve_channel(target, data)
        if row.get("role") != "unused":
            return project.UNCHANGED
        del row["role"]

    with project._hold(project_dir):
        data = handle.load()
        here = slot_row(data)
        other = handle.resolve_channel(target, data)
        if other is not None and other is not here:
            raise IntakeError(f"the code {target!r} is already slot {other.get('slot')} of "
                              f"{other.get('tier')} — one code, one channel. Nothing was written")
        if here is not None and here.get("code") != target:
            spare = (here.get("role") == "unused" and str(here.get("code", "")).startswith("off-")
                     and not here.get("id") and not here.get("previous_names"))
            if on and spare:
                # A spare slot has no history -- no ledger row, no capture under its name -- so it is
                # REPLACED rather than renamed: a rename would make `off-virt-F` the new channel's
                # permanent id (SCR-039), and the first snapshot would key VRL under it.
                handle.update(drop_spare)
            else:
                handle.rename_channel(here["code"], target)
        fields = {"slot": slot, "tier": tier, "hidden": not on}
        if not on:
            fields["role"] = "unused"
        handle.set_channel(target, **fields)
        if on:
            handle.update(back_on)
        return handle.resolve_channel(target)


def move_slot(project_dir, tier, code, to_slot):
    """Move a live channel to another slot of the same tier -- the wire moved, the channel did not.

    Switching the old slot off and the new one on under the same code cannot do this: the off step
    renames the row to `off-…`, the code lands in its `previous_names`, and the on step then finds
    the code taken by that very row and refuses. So a move is one write: the channel's row keeps its
    code, id and history and gets the new slot; the slot it left gets a spare row (the record that
    the slot exists, SCR-042). The target slot's own row, if any, must be a spare without history --
    a switched-off channel with history there is a channel of its own and is not overwritten.

    One writer's from its read to the spare row it leaves (#141): the project's lock is held over the move
    (`Project.update`) and that row's write.
    """
    tier, to_slot, code = (str(x or "").strip() for x in (tier, to_slot, code))
    if not tier or not to_slot or not code:
        raise IntakeError("a move needs the tier, the code and the new slot — nothing was written")
    handle = project.Project(project_dir)
    left = []

    def move(data):
        row = next((c for c in data.get("channels") or []
                    if isinstance(c, dict) and c.get("code") == code and c.get("tier") == tier), None)
        if row is None:
            raise IntakeError(f"no channel {code!r} in {tier} to move — nothing was written")
        from_slot = str(row.get("slot") or "")
        if from_slot == to_slot:
            return project.UNCHANGED
        there = next((c for c in data["channels"] if isinstance(c, dict) and c is not row
                      and c.get("tier") == tier and str(c.get("slot")) == to_slot), None)
        if there is not None:
            spare = (there.get("role") == "unused" and str(there.get("code", "")).startswith("off-")
                     and not there.get("id") and not there.get("previous_names"))
            if not spare:
                raise IntakeError(f"slot {to_slot} of {tier} holds {there.get('code')!r}, a channel with "
                                  "its own history — switch it off or rename it first. Nothing was written")
            data["channels"] = [c for c in data["channels"] if c is not there]
        row["slot"] = to_slot
        left.append(from_slot)

    with project._hold(project_dir):
        handle.update(move)
        if left and left[0]:
            handle.set_channel(off_code(tier, left[0]), slot=left[0], tier=tier, hidden=True,
                               role="unused")
        return handle.resolve_channel(code)


def known_cars(project_dir=None):
    """`[{"make", "model", "generation", "body", "drive_side", "label", "source"}]` -- cars the
    skill has seen.

    Two sources, and nothing invented: the cabin library (`knowledge/cars/`, one file per body,
    its own heading read by `car_profile`) and the other projects next to this one (a sibling
    directory whose `project.json` records all four parts). There is no car catalogue beyond these;
    a picked car fills the four fields, and an EDITED one is a new car, not a variant of the entry.

    `drive_side` comes with the car when its source records it (round 5): a sibling project's
    `car.drive_side`, or the ONE drive side a library entry's build line names (the Passat file's
    "…; LHD, 2026"). None when the source does not say -- then the form asks, as for a new car.
    """
    import car_profile

    out, seen = [], set()

    def add(make, model, generation, body, source, drive_side=None):
        parts = [str(x or "").strip() for x in (make, model, generation, body)]
        if not all(parts):
            return
        slug = car_profile.body_slug(*parts)
        if slug in seen:
            # The same car from a second source may know what the first did not (a neighbour
            # project without a drive side, the library entry with one).
            entry = next(c for c in out if car_profile.body_slug(c["make"], c["model"],
                                                                 c["generation"], c["body"]) == slug)
            if entry["drive_side"] is None and drive_side in DRIVE_SIDES:
                entry["drive_side"] = drive_side
            return
        seen.add(slug)
        out.append({"make": parts[0], "model": parts[1], "generation": parts[2], "body": parts[3],
                    "drive_side": drive_side if drive_side in DRIVE_SIDES else None,
                    "label": " ".join(parts), "source": source})

    if project_dir:
        here = os.path.abspath(project_dir)
        parent = os.path.dirname(here)
        try:
            siblings = sorted(os.listdir(parent))
        except OSError:
            siblings = []
        for name in siblings:
            d = os.path.join(parent, name)
            if d == here or not os.path.isfile(os.path.join(d, "project.json")):
                continue
            car = (_read_project(d) or {}).get("car") or {}
            add(car.get("make"), car.get("model"), car.get("generation"), car.get("body"),
                f"project:{name}", car.get("drive_side"))
    for _slug, path, title in car_profile.list_bundled():
        words = title.split(" — ", 1)[0].split()
        if len(words) == 4 and words[3] in BODIES:
            add(*words, source="library", drive_side=_library_drive_side(path))
    return out


def _library_drive_side(path):
    """The drive side a library entry's opening lines name, if they name exactly one."""
    import re

    try:
        with open(path, encoding="utf-8") as fh:
            head = "".join(fh.readline() for _ in range(6))
    except OSError:
        return None
    found = set(re.findall(r"\b(LHD|RHD)\b", head))
    return found.pop() if len(found) == 1 else None


def dsp_knobs(profile):
    """The remote knobs a processor's profile names -- the rows the form pre-seeds (round 5).

    Read off the profile's own `effects_and_dynamics` / `features`: the entries named `…RC`, the
    remote controls (a Helix: SubRC, RearRC). The rest of that list are effects switched in the
    software, not knobs a person turns in the car. Anything else -- a head unit's bass knob -- is
    added on the form by name.
    """
    p = dsp_profile._unwrap(profile or {})
    names = list(p.get(dsp_profile.EFFECTS_KEY) or [])
    names += [f.get("key") for f in p.get("features") or [] if isinstance(f, dict)]
    return [n for n in dict.fromkeys(str(x) for x in names if x) if n.endswith("RC")]


def save_controls(project_dir, positions, source="user"):
    """Where the knobs outside the DSP stand -- `hardware.controls`, through `Project`'s own writer.

    `{name: position}`; a position is free text ("4/4", "7", "ON"). A blank one is skipped, not
    written as blank. What a step is WORTH is a separate fact (`set-control-mapping`), and where a
    knob stood FOR A CAPTURE belongs to the round (`process.py capture-knobs`) -- RES-007.

    Every knob under one hold of the project's lock (#141, R20): another writer cannot land between two, and a lock
    held past the wait is met before the first, so its "nothing was written" is true.
    """
    handle = project.Project(project_dir)
    written = {}
    with project._hold(project_dir):
        for name, pos in (positions or {}).items():
            name, pos = str(name or "").strip(), str(pos if pos is not None else "").strip()
            if not name:
                raise IntakeError("a knob needs its name — nothing was written for it")
            if not pos:
                continue
            handle.set_hardware_control(name, pos, source=source)
            written[name] = pos
    return written


# ── WHEN a field is asked ─────────────────────────────────────────────────────
#: The intake used to front-load every field. The fast sessions did not: they asked what the next
#: step needed and picked up the rest when it mattered (`docs/REVIEW-2026-09-22-antigravity-session.md`,
#: `docs/DESIGN-2026-09-22-intake-simplified.md`). So each field names the step that FIRST needs it.
#: `now` is what starting to measure needs -- the Phase-0 gate's files and the channel names. A
#: deferred field stays in the table (nothing is lost); a form shows it collapsed under its step.
WHEN = (
    ("now", "before the first measurement: the Phase-0 gate's files and the channel names"),
    ("install", "Phase -1 step 6, install verification -- right before the first sweep"),
    ("0", "Phase 0 -- the capture session's pre-session checklist, and the target after the baseline"),
    ("1", "Phase 1 -- crossovers, levels and delays"),
    ("2", "Phase 2 -- EQ"),
    ("4", "Phase 4 -- listening"),
    ("5", "Phase 5 -- variations and taste"),
)
#: WHERE a form shows a field (the Arbiter's review of the page, 2026-09-22). `when` says which
#: step needs the answer; `place` says whether a person is asked for it on the intake page at all.
PLACES = (
    ("now", "asked on the page: what starting to measure needs"),
    ("goal", "asked on the page, optional: what the tune is for and what is played"),
    ("new_dsp", "asked only for a processor the skill has no profile of -- the base, once"),
    ("equipment", "optional: the drivers and the hardware outside the DSP, if the person has them written down"),
    ("memo", "not asked: a tool reads it, or the session asks when the step comes -- listed in a memo"),
)


# ── the couples: fields that are ONE question ─────────────────────────────────
#: A form renders each of these as ONE control. Asked apart, every one of them has produced the
#: same damage: an answer that had to be revised, or a value that is legal and ambiguous.
COUPLINGS = {
    "car_identity": "The four parts are one identity (SCR-043). A make+model with no generation and "
                    "no body cannot be matched against the cabin library or against an earlier build "
                    "on this car — and a project that recorded no body reads as `unknown`, not as "
                    "`no`. Asked one at a time, the body is the part that gets skipped as obvious.",
    "seat": "Who the tune is FOR, and which side they sit on. Three choices in one control — a "
            "single seat can be fully centred, all seats is a deliberate compromise, and the car's "
            "LHD/RHD sets the direction of the L/R asymmetry. Asked apart, 'driver only' was "
            "corrected to 'driver and front passenger' five minutes later and a recorded decision "
            "had to be voided.",
    "purpose": "The first fork and the formats it opens. Competition without a format names no goal, "
               "and 'several or all' means separate presets rather than one tune (`competition.md`).",
    "dsp_identity": "Vendor and model together, or the bundled profile cannot be looked up "
                    "(`dsp_profile.find_bundled`) — and a model with no vendor matches nothing "
                    "while looking like an answer.",
    "capability": "Is the state readable, and can you measure per-channel? The two together ARE the "
                  "level (`project-intake.md` §4); either one alone decides nothing.",
    "channel_slot": "A slot letter and its tier. Slot letters REPEAT across tiers (a Helix: virtual "
                    "A–H, outputs B–K), so `slot: F` is legal in both and a guess files a spare "
                    "output among the virtual channels (SCR-042).",
    "inputs": "Which input is for listening and which carries the measurement signal. One question "
              "with two answers — it is what SKILL.md's Pre-Session item 1 checks, and a preset "
              "switch silently resetting the input is the trap it exists for.",
    "taste": "Four axes of one taste -- warm/bright, bass, forward/laid-back, accuracy/fun. Asked "
             "apart they read as four questions; they are one picture of what the person likes, "
             "each pre-set to the neutral middle, so only the axes that differ are touched.",
}


# ── the field table ───────────────────────────────────────────────────────────
def _f(id, group, ask, *, required=False, enum=None, multi=False, writes=None, lands=None,
       ask_with=None, per=None, settled_by=None, checklist=None, note=None,
       when="now", default=None, suggest=None, derive=None, place=None):
    """One row of the table. `writes` is the MACHINE destination and it is the load-bearing field:

    * `project:<dotted path>`       -> `project.json`, through this module's `save()`
    * `project:channels[].<field>`  -> one channel row, through `save_channel()` (`per="channel"`)
    * `project:amps[].<field>`      -> one amplifier, through `save_amp()` (`per="amp"`)
    * `dsp_profile.draft:<path>`    -> the profile's OWN writer (`dsp_profile.set_field`)
    * `glossary:`                   -> the agreed names (`glossary.json` / `project.json.glossary`)
    * `None`                        -> no machine home yet; `lands` says where the answer does go.

    And four that make the intake SHORT (2026-09-22):

    * `when`    -- the step that first needs the answer (`WHEN`); `now` unless a later one does.
    * `default` -- the answer a form pre-selects ("change it if yours differs"). A default is
                   shown, never written behind the person's back: it lands only when confirmed.
    * `suggest` -- choices for an OPEN set (a datalist, not an enumeration): the form offers them
                   and takes any other answer. `enum` stays the closed set that `check_value` enforces.
    * `derive`  -- how a tool or the bundled profile answers it instead of the person.
    * `place`   -- where a form shows it (`PLACES`). Defaults to `now` for a `now` field nobody
                   derives, else to the memo.
    """
    if place is None:
        place = "now" if when == "now" and derive is None else "memo"
    return {"id": id, "group": group, "ask": ask, "required": bool(required),
            "enum": tuple(enum) if enum else None, "multi": bool(multi), "writes": writes,
            "lands": lands, "ask_with": ask_with, "per": per, "settled_by": settled_by,
            "checklist": checklist, "note": note, "when": when, "default": default,
            "suggest": tuple(suggest) if suggest else None, "derive": derive, "place": place}


FIELDS = (
    # ── project: the front-end's own half (`project-intake.md` §0) ────────────────────────────
    _f("project.language", "project", "Which language should the session WRITE in — EN / UK / DE / PL?",
       required=True, enum=LANGUAGES, settled_by="front_end", writes="project:language.reply",
       lands="`project.json` `language.reply` + a recorded decision (-1.1)",
       note="The AI's language IS the interface language, always (the Arbiter, 2026-09-22): the "
            "language the front-end was started in -- TCC's, or the skill's own form's `--lang`. "
            "It is written here so a session after a `/clear` reads it (S-045), and it is never "
            "offered as a question. The USER's own language, when it differs, is `project.user_"
            "language` and switches nothing; the language the person TYPES changes nothing either "
            "-- he had no Ukrainian layout on the Windows VM, typed English, and the reply stayed "
            "Ukrainian.",
       derive="the interface language (`--lang` of the form, or the front-end's), written on "
              "Save -- never asked"),
    _f("project.user_language", "project",
       "The user's own language — if it differs from the interface (optional)",
       suggest=LANGUAGES, writes="project:language.user",
       lands="`project.json` `language.user` -- recorded, and never used to switch the AI's language",
       note="The person's own language, for the record: a Polish speaker running an English "
            "interface. It does NOT change what the session writes in -- that is the interface "
            "language, always (the Arbiter, 2026-09-22). Empty by default, nothing pre-filled."),
    _f("project.reviewer_channel", "project", "Which reviewer channel, and does it answer?",
       required=True, settled_by="front_end",
       lands="`rew_analitic/reviewer-check.md` (a live doctor run) + a recorded decision (-1.2)",
       note="Closed by an ANSWER, not by a setting: 'configured' resolves to nothing and the gate "
            "refuses it. An unreachable channel is blocked with its reason, not marked done.",
       derive="a live reviewer check (`scripts/autosound_ai.py doctor`) -- an answer, not a setting"),
    _f("project.dir", "project", "Where does this project live?", required=True,
       settled_by="front_end", writes="project:paths.project_dir",
       derive="the directory the session or the form was opened for"),

    # ── car: the cabin (§1.1) ─────────────────────────────────────────────────────────────────
    _f("car.make", "car", "Make", required=True, writes="project:car.make", ask_with="car_identity"),
    _f("car.model", "car", "Model", required=True,
       writes="project:car.model", ask_with="car_identity"),
    _f("car.generation", "car", "Generation", required=True,
       writes="project:car.generation", ask_with="car_identity",
       note="The generation IS the span of years over which the acoustics count as the same, which "
            "is why the year classifies nothing."),
    _f("car.body", "car", "Body", required=True, enum=BODIES, writes="project:car.body",
       ask_with="car_identity",
       note="Record it even when it feels obvious: without it this cabin cannot be told from a "
            "wagon's, and room gain and low-frequency behaviour are exactly what differs."),
    _f("car.drive_side", "car", "Left- or right-hand drive?", required=True, enum=DRIVE_SIDES,
       writes="project:car.drive_side", ask_with="seat",
       note="The listener's side sets the DIRECTION of the L/R asymmetry.",
       default="LHD"),
    _f("car.year", "car", "Year (optional — it describes this car and classifies nothing)",
       writes="project:car.year"),

    # ── dsp: the processor (§1.3 + `project-intake.md` §4) ────────────────────────────────────
    _f("dsp.vendor", "dsp", "DSP vendor", required=True, writes="project:dsp.vendor",
       ask_with="dsp_identity",
       suggest=BUNDLED_DSP_VENDORS),
    _f("dsp.model", "dsp", "DSP model", required=True, writes="project:dsp.model",
       ask_with="dsp_identity",
       note="Before asking anything below: `dsp_profile.py find-bundled <vendor> <model>` and "
            "`knowledge/dsp/<vendor>-<model>.md` may already answer the whole checklist.",
       suggest=BUNDLED_DSP_MODELS),
    _f("dsp.tiers_used", "dsp", "Which of the processor's tiers will this car use?", enum=SUGGESTED_TIERS,
       multi=True, writes="project:dsp.tiers_used",
       note="Asked BEFORE the channel rows, so a row's tier is picked from the tiers in use rather "
            "than typed: a Helix declares virtual channels, outputs and inputs, and the inputs "
            "tier is outside the method's scope. A processor the skill knows offers its own tiers; "
            "a new one offers all of them."),
    _f("dsp.readable", "dsp", "Is the DSP's state readable (a dump, a screen-read, a file export)?",
       required=True, enum=("yes", "no"), ask_with="capability",
       lands="the capability level in `autosound_context.md` + a recorded decision",
       derive="probed: a dump, a screen-read or a file export either works or it does not"),
    _f("dsp.per_channel_measurable", "dsp", "Can each output be measured on its own (solo)?",
       required=True, enum=("yes", "no"), ask_with="capability",
       lands="the capability level in `autosound_context.md` + a recorded decision",
       note="This is the hinge, not readability: no per-channel access is Level 3, where joint and "
            "phase surgery is impossible and the ceiling is recorded honestly.",
       derive="always yes on a DSP: any output can be soloed by muting the rest (the Arbiter, "
              "2026-09-22) -- asked only if a session finds it cannot"),
    _f("dsp.capability_level", "dsp", "Which level does that make it — 1 full / 2 black-box / 3 sum only?",
       required=True, enum=CAPABILITY_LEVELS, ask_with="capability",
       lands="`autosound_context.md` + a recorded decision",
       note="Decided BY the two answers above, not asked instead of them.",
       derive="from the two answers above (`project-intake.md` §4)"),
    _f("dsp.processing_rate_hz", "dsp", "The DSP's own processing rate", enum=PLAUSIBLE_RATES_HZ,
       writes="project:dsp.dsp_processing_rate_hz",
       note="The processing rate, not the capture rate — two rates, one name each. The capture "
            "rate is `rew.capture_rate_hz`.",
       when="1", derive="the bundled profile on an exact vendor+model match", place="new_dsp"),
    _f("dsp.tiers", "dsp", dsp_profile.CAPABILITY_CHECKLIST[0], required=True, checklist=0,
       writes="dsp_profile.draft:groups",
       note="No virtual layer -> voicing is linked L=R on the output EQ, and voicing presets cost "
            "more (`diagnostic-techniques.md §6`).",
       multi=True, suggest=SUGGESTED_TIERS,
       derive="the bundled profile on an exact vendor+model match; asked only when none matches",
       place="new_dsp"),
    _f("dsp.max_count", "dsp", dsp_profile.CAPABILITY_CHECKLIST[1], required=True, checklist=1,
       per="tier", writes="dsp_profile.draft:groups.<i>.max_count",
       note="Left null, a 12-output processor with ten in use reads 10/10 and its spare slots are "
            "invisible.",
       derive="the bundled profile on an exact vendor+model match; asked only when none matches",
       place="new_dsp"),
    _f("dsp.eq", "dsp", dsp_profile.CAPABILITY_CHECKLIST[2], required=True, checklist=2,
       per="tier", writes="dsp_profile.draft:groups.<i>.eq",
       note="The band vocabulary is the profile's own (`dsp_profile.FIELD_VOCABULARY`); file "
            "import + format decides whether the REW->DSP path is a file or the copy-paste assistant.",
       when="2", derive="the bundled profile on an exact vendor+model match", place="new_dsp"),
    _f("dsp.crossovers", "dsp", dsp_profile.CAPABILITY_CHECKLIST[3], required=True, checklist=3,
       per="tier", writes="dsp_profile.draft:groups.<i>.crossover_filters",
       note="Families are `dsp_math.MODELLABLE_FAMILIES` (LR/BW/BE) — enterable on the device is "
            "what is being asked, modellable here is what the profile then marks.",
       when="1", derive="the bundled profile on an exact vendor+model match", place="new_dsp"),
    _f("dsp.delays", "dsp", dsp_profile.CAPABILITY_CHECKLIST[4], required=True, checklist=4,
       per="tier", writes="dsp_profile.draft:groups.<i>.fields",
       note="Step and limits decide TA accuracy; an all-pass decides the phase method.",
       when="1", derive="the bundled profile on an exact vendor+model match", place="new_dsp"),
    _f("dsp.presets", "dsp", dsp_profile.CAPABILITY_CHECKLIST[5], required=True, checklist=5,
       writes="dsp_profile.draft:presets",
       note="What resets on a switch — the INPUT above all: a preset silently resetting it is "
            "the input check's whole reason for existing (SKILL.md's Pre-Session item 1).",
       when="0", derive="the bundled profile on an exact vendor+model match", place="new_dsp"),
    # skill #52: three switches on the vendor software's settings panel -- what THIS machine is set to, asked when
    # the step that needs it comes, and written to the finalised profile by `dsp_profile.set_setting`.
    _f("dsp.channel_gain_step", "dsp", "Channel gain step on this machine (settings panel: Channel Gain Resolution)",
       enum=("1.0", "0.5", "0.25", "0.1"), writes="dsp_profile:channel_gain.step_db",
       note="A setting, not a property of the device: a sheet at 0.1 dB typed on a machine set to 1.00 is rounded "
            "by whoever types it. Asked before the first trim with decimals.", when="1", place="memo"),
    _f("dsp.eq_gain_step", "dsp", "EQ gain step on this machine (settings panel: EQ Gain Resolution)",
       enum=("1.0", "0.5", "0.25", "0.1"), writes="dsp_profile:parametric_eq.gain_step_db",
       note="The EQ band's own switch, beside the channel gain's.", when="2", place="memo"),
    _f("dsp.eq_link_mode", "dsp", "EQ Link Mode on this machine (settings panel)", enum=("absolute", "relative"),
       writes="dsp_profile:parametric_eq.link_mode",
       note="Changes what a typed EQ value MEANS, so it is asked before an EQ band is typed.", when="2", place="memo"),
    _f("dsp.measurement_input", "dsp", dsp_profile.CAPABILITY_CHECKLIST[6], checklist=6,
       writes="project:source.measurement_input", ask_with="inputs",
       when="0"),

    # ── channel_map: what is wired where (§1.5–§1.7, §5) ──────────────────────────────────────
    _f("channel_map.glossary_agreed", "channel_map",
       "Are the channel codes and the title grammar agreed AND written down?", required=True,
       writes="glossary:",
       note="⛔ The gate before any measurement (§0.5 step 5). Agreed-but-not-written is the "
            "recurring slip: the history it produces is unusable.",
       default="the suggested codes"),
    _f("channel_map.code", "channel_map", "The channel's code", required=True, per="channel",
       writes="project:channels[].code",
       note=f"Suggested set: {', '.join(SUGGESTED_CHANNEL_CODES)} — the glossary is agreed, not fixed.",
       suggest=SUGGESTED_CHANNEL_CODES),
    _f("channel_map.slot", "channel_map", "Which slot on the processor", required=True, per="channel",
       writes="project:channels[].slot", ask_with="channel_slot"),
    _f("channel_map.tier", "channel_map", "Which tier that slot belongs to", required=True,
       per="channel", writes="project:channels[].tier", ask_with="channel_slot",
       note="The LEDGER key (`dsp_profile.ledger_tier`): `channels` for a physical output, "
            "`virtual_channels`/`inputs`/... for the rest. `physical_outputs` is refused.",
       default="channels", suggest=SUGGESTED_TIERS),
    _f("channel_map.role", "channel_map", "What it drives (woofer / midrange / tweeter / sub / ...)",
       per="channel", writes="project:channels[].role",
       note="`role: unused` for an empty slot — and write the row anyway: it is the only record "
            "that the slot exists (SCR-042).",
       suggest=SUGGESTED_ROLES, derive="from the channel code (`w-` woofer, `m-` midrange, `tw-` tweeter, `sw` sub)"),
    _f("channel_map.descr", "channel_map", "How the DSP's own software labels it", per="channel",
       writes="project:channels[].descr",
       when="0", derive="read off the DSP software when its current state is imported"),
    _f("channel_map.driver", "channel_map", "Driver — make and model", per="channel",
       writes="project:channels[].driver.name",
       note="One line as the person writes it (\"Audiofrog GB25\") -- the Arbiter, 2026-09-22: make and "
            "model are one column. A row written before keeps `driver.make`/`driver.model` and is read "
            "as \"make model\".",
       when="install", place="equipment"),
    _f("channel_map.fs_hz", "channel_map", "The driver's Fs", per="channel",
       writes="project:channels[].fs_hz",
       note="Carries provenance: a datasheet number is `source=datasheet` and a later impedance "
            f"sweep upgrades it to `measured` (sources: {', '.join(FACT_SOURCES)}). The protective "
            "HPF is bound to it (>= 1.1 x Fs, >= 24 dB/oct), so an Fs carried in from another "
            "project is not this build's until it is confirmed here (skill #36).",
       when="install", derive="the driver's datasheet, from its make and model", place="equipment"),
    _f("channel_map.amp", "channel_map", "Amplifier and its channel", per="channel",
       writes="project:channels[].amp",
       note="Free text (\"GZPA 4SQ, ch 3\"): which amplifier drives this output, and on which of its "
            "channels. Asked beside the driver, 2026-09-22.",
       when="install", place="equipment"),
    _f("channel_map.install", "channel_map", "How it is installed", per="channel",
       writes="project:channels[].install",
       note="Free text, in the person's words (\"kick panel, aimed at the far side\", \"stock door, "
            "sealed pod\"). The Arbiter, 2026-09-22: ONE text column, and the list form of mount "
            "and aim is dropped (docs/TODO.md S-051); the session reads this text where an aim matters.",
       when="install", place="equipment"),
    _f("channel_map.position", "channel_map", "Where it sits and where it points", per="channel",
       enum=POSITIONS, writes="project:channels[].position",
       note="Take it from the person or from a measurement — never from a car/DSP profile: "
            "placement varies on the same body. NOT on the form (the Arbiter, 2026-09-22): nothing "
            "in the method computes from it yet, so a person describes it in «Інше обладнання»'s "
            "free text; the list form of mount and aim is dropped (docs/TODO.md S-051).",
       when="1", place="memo"),
    _f("channel_map.enclosure", "channel_map", "How it is loaded", per="channel", enum=ENCLOSURES,
       writes="project:channels[].enclosure",
       note="NOT on the form, for the same reason as the position (2026-09-22): no tool computes "
            "from it; the free-text description carries it.",
       when="1", place="memo"),
    _f("channel_map.condition", "channel_map", "New, or broken in?", per="channel", enum=CONDITIONS,
       writes="project:channels[].condition",
       note="New drivers get a rough tune, a break-in and only then a precise one "
            "(`project-intake.md` §3.6).",
       when="install", default="broken_in", place="equipment"),
    _f("channel_map.hidden", "channel_map", "Is the slot empty (nothing wired to it)?", per="channel",
       enum=("yes", "no"), writes="project:channels[].hidden",
       default="no"),
    _f("channel_map.routing", "channel_map", "Which outputs does each VIRTUAL channel feed?",
       per="virtual_channel", writes="project:hardware.virtual_routing",
       note="Never inferable from names — `VFL` looking like 'virtual front left' is a convention, "
            "not a wiring diagram (RES-007). Required where the DSP has a virtual tier.",
       when="1", derive="read off the processor's routing matrix when its state is imported"),
    # The Arbiter, round 4: the equipment is described in the person's OWN words first; the
    # structured driver rows stay, optional, for whoever has them written down.
    _f("hardware.description", "channel_map",
       "Describe the rest of the equipment in your own words (speakers, amplifiers, anything)",
       writes="project:hardware.description", when="install", place="equipment",
       lands="`project.json` `hardware.description` -> `autosound_context.md` §1"),
    _f("channel_map.hardware_controls", "channel_map",
       "Remote knobs and switches outside the DSP (SubRC / RearRC / a bass control), and where they stand",
       per="control", writes="project:hardware.controls",
       note="Two facts, not one: the POSITION is read off the device, what a step is WORTH is "
            "somebody's opinion (`set-control-mapping`). Without the mapping, a comparison across "
            "positions is refused rather than folded into an offset (RES-007). The form offers "
            "the processor's own remote knobs (`dsp_knobs`) as rows, plus any other by name.",
       when="0", place="equipment"),

    # ── measurement_chain: how the signal gets in (§1.2, §1.4) ────────────────────────────────
    _f("source.kind", "measurement_chain", "What plays the music (head unit / streamer / phone / ...)",
       enum=SOURCE_KINDS, writes="project:source.kind",
       when="0"),
    _f("source.connection", "measurement_chain", "How the signal enters the DSP",
       enum=CONNECTIONS, writes="project:source.connection",
       when="0"),
    _f("source.listening_input", "measurement_chain", "Which input is for listening",
       writes="project:source.listening_input", ask_with="inputs",
       when="0", suggest=CONNECTIONS),
    _f("source.measurement_input", "measurement_chain",
       "Which input carries the measurement signal",
       writes="project:source.measurement_input", ask_with="inputs",
       when="0", suggest=CONNECTIONS),
    _f("amps.make", "measurement_chain", "Amplifier make", per="amp", writes="project:amps[].make",
       when="install"),
    _f("amps.model", "measurement_chain", "Amplifier model", per="amp", writes="project:amps[].model",
       when="install"),
    _f("amps.channels", "measurement_chain", "Which channels it drives", per="amp",
       writes="project:amps[].channels",
       when="install"),
    _f("amps.gain_db", "measurement_chain", "Its input sensitivity / gain setting", per="amp",
       writes="project:amps[].gain_db",
       note="Gain staging is verified in `project-intake.md` §3.4, not decided here; this records "
            "where it was left.",
       when="install"),

    # ── rew: the rig (§0.5 step 4, §1.8) ──────────────────────────────────────────────────────
    # The Arbiter, 2026-09-22: the mic's type and its calibration file do not change the tune --
    # REW holds the file, and the loopback below is the rig question. Kept, never asked.
    _f("rew.mic_model", "rew", "Measurement mic", writes="project:mic.model",
       suggest=SUGGESTED_MICS, when="0", place="memo"),
    _f("rew.mic_cal_0", "rew", "Its 0° calibration file",
       writes="project:mic.calibration_file", when="0", place="memo"),
    _f("rew.mic_cal_90", "rew", "Its 90° calibration file", writes="project:mic.calibration_file_90",
       when="0"),
    _f("rew.interface", "rew", "Audio interface", writes="project:measurement.interface",
       when="0"),
    _f("rew.loopback", "rew", "The timing reference: a PHYSICAL loopback, or an acoustic one?",
       required=True, enum=LOOPBACKS, writes="project:measurement.loopback",
       note="Without a physical one, phase and timing reads lean on summation and the ear. An "
            "acoustic reference through a USB mic gives timing but does not qualify for "
            "virtual-first."),
    _f("rew.capture_rate_hz", "rew", "The capture sample rate", enum=PLAUSIBLE_RATES_HZ,
       writes="project:measurement.sample_rate_hz",
       note="The DSP's native rate where possible. This is the CAPTURE rate and keeps its own name; "
            "the processing rate is `dsp.processing_rate_hz`.",
       default=48000, when="0", place="memo"),
    _f("rew.api_reachable", "rew", "Does REW's API answer at localhost:4735?", required=True,
       enum=("yes", "no"), lands="SKILL.md's Pre-Session item 1 (a live check, not a setting)",
       note="Reading is free; FIRING a sweep needs a Pro licence, so a human runs the session "
            "either way.",
       when="0", derive="probed: a GET on localhost:4735"),
    _f("rew.input_clip_checked", "rew", "Has the measurement input been checked for clipping?",
       required=True, enum=("yes", "no"), lands="the install verification (`project-intake.md` §3.8)",
       when="install", derive="probed at the capture set-up (`project-intake.md` §3.8)"),

    # ── goal: what the tune is FOR (§2.1–§2.4, §2.7) ──────────────────────────────────────────
    # The Arbiter, 2026-09-22: one optional control -- EMMA / AYA / for yourself / other + words.
    # The form maps the ticks onto these two keys (and "other" onto `goal.wishes`).
    _f("goal.purpose", "goal", "Competition, for yourself, or both?", enum=PURPOSES,
       ask_with="purpose", writes="project:goal.purpose",
       lands="`project.json` `goal` -> `autosound_context.md` (Engineering Profile) + a recorded decision",
       when="0", place="goal"),
    _f("goal.formats", "goal", "Which format(s) — EMMA / AYA / CARMusic?", enum=FORMATS, multi=True,
       ask_with="purpose", writes="project:goal.formats",
       lands="`project.json` `goal` -> `autosound_context.md` + a recorded decision",
       note="Required once `goal.purpose` includes competition. Several formats = separate presets, "
            "not one tune: crossfeed stabilises an EMMA stage and is never used for AYA.",
       when="0", place="goal"),
    _f("goal.reference_seat", "goal",
       "Who is the tune for — driver / passenger / both / all / rear left / rear right?",
       required=True, enum=REFERENCE_SEATS, ask_with="seat",
       writes="project:project_type",
       lands="`project.json` `project_type` + `autosound_context.md` + a recorded decision",
       note="This is WHAT THE PROJECT IS, not a goal inside it, and it is written ONCE (S-032, the "
            "Arbiter 2026-09-20). A single seat can be fully centred and imaged; `all` is a "
            "deliberate compromise with no perfect phantom centre for anyone. Tuning another seat "
            "means taking every raw curve again, so it is ANOTHER project — started from this "
            "one's description and none of its measurements. Not the presets: SQ and FULL live in "
            "one project on one measurement base, and FULL is the rears and surround, not a seat."),
    _f("goal.mode", "goal", "A tune from scratch, improving an existing one, or a light touch?",
       required=True, enum=MODES, writes="project:goal.mode",
       lands="`project.json` `goal.mode` -> `autosound_context.md` + a recorded decision",
       note="An INTENT, orthogonal to the capability level. Both modes read the current DSP state "
            "into the ledger first. Written to project.json so `handoff` can name the route (skill #105).",
       default="new_tune", derive="from scratch, unless the car is already tuned and the tuner wants that tune improved (`virtual-first.md`, two ways in)"),
    _f("goal.design_path", "goal", "Virtual-first at the desk, or iterative?", enum=DESIGN_PATHS,
       lands="`autosound_context.md` + a recorded decision",
       note="Virtual-first needs all three: level 1, a loopback on one clock, a hardware-verified "
            "filter model. Miss one and only the DESK half degrades — the Phase-0 capture session "
            "is run the same way regardless.",
       when="1", derive="virtual_first when level 1 + a loopback on one clock + a verified filter model, else iterative"),
    _f("goal.stage_priorities", "goal", "What stage are we building (you cannot maximise everything)?",
       enum=STAGE_PRIORITIES, multi=True, lands="`autosound_context.md` (Engineering Profile)",
       note="State the physical ceilings honestly: depth is limited by the mid's geometry, "
            "envelopment needs a rear.",
       when="4"),
    _f("goal.constraints", "goal", "Anything that must NOT be touched (doors, trim, budget, time)?",
       lands="`autosound_context.md` (Engineering Profile) as a hard constraint",
       when="1", suggest=SUGGESTED_CONSTRAINTS),
    _f("goal.wishes", "goal", "Anything else you want from this system — in your own words?",
       writes="project:goal.wishes", lands="`project.json` `goal` -> `autosound_context.md` as an explicit project goal",
       note="⚠️ The branches above are the COMMON ones, not a closed list. A free-form wish is "
            "captured in the person's words and then MAPPED to where it lands in the tune; one "
            "that fits no box is recorded as a goal on its own terms (§2.7).",
       when="0", place="goal"),

    # ── target_curve: the seed and the taste (§2.3, §2.5, §2.6) ───────────────────────────────
    _f("target_curve.candidate", "target_curve", "Which target curve?", required=True,
       writes="project:goal.target_curve",
       lands="`project.json` `goal` -> `rew_analitic/target-curves/<name>/` + `autosound_context.md` §4",
       note="ONE choice (the Arbiter, 2026-09-22): SQ-Comp-Ref, the skill's own and bundled; one of "
            "the Nono Tuning Tool presets, spelled as NTT lists them and downloaded there "
            "(`NTT_CURVE_PRESETS`, `NTT_URL`); or one's own file, named in words. "
            "⛔ Chosen TOGETHER with the person — there is no default. Narrow by genres and taste to "
            "2–3 candidates (`voicing-by-ear.md`). It is SEEDED here and finalised after the Phase-0 "
            "baseline: a curve is a start and a shape, not a finish and not a level.",
       when="0", suggest=SUGGESTED_CURVES, place="goal"),
    _f("target_curve.genres", "target_curve", "What do you listen to?", enum=GENRES, multi=True,
       writes="project:goal.genres", lands="`project.json` `goal` -> `preference-profile.md` (applied in Phase 5)",
       when="0", place="goal"),
    _f("target_curve.loves_most", "target_curve", "What do you love most in the sound?", enum=LOVES,
       multi=True, lands="`preference-profile.md`",
       when="0"),
    _f("target_curve.loudness", "target_curve", "How loud do you usually listen?", enum=LOUDNESS,
       lands="`preference-profile.md`",
       note="Decides how much equal-loudness weighting the voicing carries (`staging-depth.md §3`).",
       when="5", default="moderate"),
    _f("target_curve.reference_tracks", "target_curve", "3–5 reference tracks you know well",
       lands="`preference-profile.md`",
       when="4"),
    _f("target_curve.track_library", "target_curve", "Which test-track libraries do you have?",
       enum=TRACK_LIBRARIES, multi=True, writes="project:goal.track_libraries",
       lands="`project.json` `goal` -> `preference-profile.md`",
       note="Phase 4 proposes only from what you can actually play (`test-tracks.md`); the choices "
            "are the libraries that file describes.",
       when="4", place="goal"),
    _f("target_curve.tone", "target_curve", "Warm or bright?", enum=TONE, lands="`preference-profile.md`",
       when="5", default="neutral", ask_with="taste"),
    _f("target_curve.bass", "target_curve", "Bass-heavy or neutral?", enum=BASS,
       lands="`preference-profile.md`",
       when="5", default="neutral", ask_with="taste"),
    _f("target_curve.presentation", "target_curve", "Forward or laid-back?", enum=PRESENTATION,
       lands="`preference-profile.md`",
       when="5", default="neutral", ask_with="taste"),
    _f("target_curve.character", "target_curve", "Accuracy or fun?", enum=CHARACTER,
       lands="`preference-profile.md`",
       when="5", default="balanced", ask_with="taste"),
)

_BY_ID = {f["id"]: f for f in FIELDS}


# ── reading the table ─────────────────────────────────────────────────────────
def groups():
    """`[{"id", "what"}]` — the pages a form would render."""
    return [{"id": g, "what": what} for g, what in GROUPS]


def fields(group=None, required_only=False, per=None, when=None):
    """The table, filtered. `per=None` is every field; `per="channel"` only the repeated ones;
    `when="now"` only what starting to measure needs (`WHEN`)."""
    out = []
    for f in FIELDS:
        if group is not None and f["group"] != group:
            continue
        if required_only and not f["required"]:
            continue
        if per is not None and f["per"] != per:
            continue
        if when is not None and f["when"] != when:
            continue
        out.append(dict(f))
    return out


def field(field_id):
    """One row, or `IntakeError` naming the closest spellings — a validator that refuses without
    saying the right name is a validator people work around (`dsp_profile.FIELD_NEAR_MISSES`)."""
    try:
        return dict(_BY_ID[field_id])
    except KeyError:
        import difflib

        close = difflib.get_close_matches(str(field_id), list(_BY_ID), n=3, cutoff=0.5)
        hint = f" — did you mean {', '.join(close)}?" if close else ""
        raise IntakeError(f"no intake field {field_id!r}{hint}") from None


def couplings():
    """`[{"id", "why", "fields"}]` — the questions a form must put as ONE control."""
    out = []
    for cid, why in COUPLINGS.items():
        out.append({"id": cid, "why": why,
                    "fields": [f["id"] for f in FIELDS if f["ask_with"] == cid]})
    return out


def check_value(field_id, value):
    """Return `value` if the enumeration takes it; raise `IntakeError` naming the choices.

    Multi-select fields take a list; a single one refuses a list rather than storing the first
    element. The KEY is checked, never a label: a consumer shows its own words.
    """
    f = field(field_id)
    enum = f["enum"]
    if enum is None:
        return value
    values = value if isinstance(value, (list, tuple)) else [value]
    if not f["multi"] and isinstance(value, (list, tuple)):
        raise IntakeError(f"{field_id} takes one answer, not a list — the choices are "
                          f"{', '.join(map(str, enum))}")
    for v in values:
        if v not in enum and str(v) not in [str(e) for e in enum]:
            raise IntakeError(f"{field_id} is one of {', '.join(map(str, enum))}, not {v!r}")
    return value


# ── the gate, as data ─────────────────────────────────────────────────────────
#: The glossary's own collections, read off the class rather than retyped: a sixth one added there
#: should appear here without an edit.
def _glossary_collections():
    return tuple(vars(naming.Glossary()).keys())


def gate_requirements(project_dir=None):
    """What `contract.py check --gate` decides on — the files, the keys, and the first snapshot.

    The file list is `contract.GATE_REQUIRED` itself, so this cannot drift from the gate. The keys
    come from the modules that validate them (`dsp_profile.TOP_REQUIRED`, `GROUP_REQUIRED`, the
    glossary's collections) and from this table (which intake fields land in that file). Handed a
    project, it also answers the parts that are only knowable there: which ledger tiers this DSP
    profile declares, and what is missing right now.

    The point is the TIMING. The gate refusing is correct; that it fires after the interview is
    not. A form given this list asks for the missing half before anything opens.
    """
    labels = {path: label for path, label, _owner, _ver in contract.CONTRACT}
    by_file = {
        "project.json": {
            "validated_keys": ("schema_version", "project_rev"),
            "intake_keys": tuple(sorted(
                {f["writes"].split(":", 1)[1].split("[")[0].split(".")[0]
                 for f in FIELDS if (f["writes"] or "").startswith("project:")})),
            "why": "the car, the channel map, the measurement chain and the rig — the facts every "
                   "later phase joins onto by channel code",
        },
        "dsp_profile.json": {
            "validated_keys": dsp_profile.TOP_REQUIRED,
            "group_keys": dsp_profile.GROUP_REQUIRED,
            "why": "what the processor CAN do — it decides which of the method's tools apply",
        },
        "glossary.json (or project.json.glossary)": {
            "validated_keys": _glossary_collections(),
            "why": "the agreed names. ⛔ Nothing is measured before they are written down: "
                   "un-agreed codes produce a history nobody can read back",
        },
    }
    out = {
        "command": "python3 rew_tool/contract.py check <project> --gate",
        "files": [dict(by_file.get(path, {}), file=path, what=labels.get(path, ""))
                  for path in contract.GATE_REQUIRED],
        "ledger": {
            "what": "a first snapshot with a row for EVERY tier the DSP profile declares",
            "why": "`apply.propose` can only address a tier that is already there, so a Helix "
                   "project's first `v_001` needs `virtual_channels` as well as `channels` — "
                   "empty or hidden rows are fine, a missing tier key is not",
            "tiers": None,
        },
        "not_required": {
            "process/process-state.json":
                "written BY `enter_phase`, so requiring it of a phase transition would be a gate "
                "demanding its own output",
        },
    }
    if project_dir:
        profile_path = os.path.join(project_dir, "dsp_profile.json")
        if os.path.isfile(profile_path):
            try:
                out["ledger"]["tiers"] = dsp_profile.tier_keys(dsp_profile.load_profile(profile_path))
            except Exception as exc:  # noqa: BLE001 -- matched below; anything else still raises
                # A profile that cannot be read raises `Unreadable` now (#136): reported here like the rest.
                if not (isinstance(exc, (OSError, ValueError)) or getattr(exc, "is_unreadable", False)):
                    raise
                out["ledger"]["tiers_error"] = str(exc)
        report = contract.check_project(project_dir, skip_rew=True)
        out["missing_files"] = [f["file"] for f in report["files"]
                                if not f["exists"] and f["file"] in contract.GATE_REQUIRED]
        # A file that is there and cannot be read keeps the gate shut, as `enter-phase 0` does (#134, batch 4's re-review
        # N4): "no file missing" opened it over a `project.json` cut off -- and over a cut `glossary.json`, now that the
        # check reads it strictly. `unreadable_files` is the check's `unreadable`, `[{file, issue}]`.
        out["unreadable_files"] = report.get("unreadable") or []
        out["gate_open"] = not out["missing_files"] and not out["unreadable_files"]
    return out


# ── what is still missing ─────────────────────────────────────────────────────
def _read_project(project_dir):
    try:
        return project.Project(project_dir).load()
    except (project.ProjectError, OSError):
        return None


def _dig(data, dotted):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return project.fact_value(node) if project.is_fact(node) else node


def _answered(field_row, data, project_dir):
    """Is this field answered on disk? `None` = not machine-readable from here (say so, never
    report a prose answer as missing — an honest 'cannot see it' is the whole point of the bucket)."""
    writes = field_row["writes"]
    if writes is None:
        return None
    if writes.startswith("dsp_profile.draft:"):
        for path in (os.path.join(project_dir, "dsp_profile.json"),
                     dsp_profile.draft_path(project_dir)):
            if os.path.isfile(path):
                return True
        return False
    if writes.startswith("glossary:"):
        g = naming.Glossary.for_project(project_dir)
        return bool(g.channels or g.pairs or g.combos or g.joints or g.sides)
    if not writes.startswith("project:"):
        return None
    if data is None:
        return False
    path = writes.split(":", 1)[1]
    if "[]" in path:  # a repeated field: answered when at least one row carries it
        collection, _, leaf = path.partition("[].")
        rows = data.get(collection) or []
        return bool(rows) and all(_dig(row, leaf) not in (None, "", [], {}) for row in rows)
    return _dig(data, path) not in (None, "", [], {})


def missing(project_dir):
    """Three buckets: what is answered, what is still missing, and what cannot be seen from disk.

    A form shows the second bucket before the session opens. The third is not a gap — goals, taste
    and the curve seed land in prose and in a recorded decision, and pretending to read them would
    be worse than saying plainly that they are not machine-readable.
    """
    data = _read_project(project_dir)
    out = {"project_dir": project_dir, "answered": [], "missing": [], "not_machine_readable": []}
    for f in FIELDS:
        state = _answered(f, data, project_dir)
        row = {"id": f["id"], "group": f["group"], "required": f["required"],
               "ask": f["ask"], "enum": f["enum"], "lands": f["lands"] or f["writes"],
               "when": f["when"], "default": f["default"], "derive": f["derive"]}
        if state is None:
            out["not_machine_readable"].append(row)
        elif state:
            out["answered"].append(row)
        else:
            out["missing"].append(row)
    out["required_missing"] = [r["id"] for r in out["missing"] if r["required"]]
    # What to ask NOW: required, missing, needed before the first measurement, and not something a
    # tool answers. The rest of `required_missing` waits for the step that needs it (`WHEN`).
    out["required_missing_now"] = [r["id"] for r in out["missing"]
                                   if r["required"] and r["when"] == "now" and not r["derive"]]
    return out


# ── the writer ────────────────────────────────────────────────────────────────
def _set_path(data, dotted, value):
    node = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value


def save(project_dir, field_id, value):
    """Write one confirmed answer into `project.json`, through the method's own writer.

    Load-modify-save with `Project.update`, never a JSON dump: one step under the project's writer lock (#141), and
    that writer validates, writes atomically, bumps `project_rev`, and refuses to treat an unreadable file as an empty
    project.

    Refuses, rather than guessing: a value outside the field's enumeration (naming the choices), a
    field that belongs to a repeated collection (naming the function that takes it), and a field
    whose answer has no machine home (naming where it does land).
    """
    f = field(field_id)
    check_value(field_id, value)
    writes = f["writes"]
    if writes is None:
        raise IntakeError(f"{field_id} has no machine field — it lands in {f['lands']}")
    if writes.startswith("dsp_profile.draft:"):
        raise IntakeError(f"{field_id} belongs to the DSP profile; its writer is "
                          f"dsp_profile.set_field(<project>, '<path>', value)")
    if writes.startswith("dsp_profile:"):
        raise IntakeError(f"{field_id} is what this machine is set to; its writer is "
                          f"dsp_profile.set_setting(<project>, '{writes.split(':', 1)[1]}', value)")
    if writes.startswith("glossary:"):
        raise IntakeError(f"{field_id} is the agreed glossary; write it to glossary.json or "
                          f"project.json.glossary (naming.py <project> codes reads it back)")
    if f["per"] == "channel":
        raise IntakeError(f"{field_id} is asked per channel — save_channel(<project>, <code>, "
                          f"{field_id.split('.', 1)[1]}=...)")
    if f["per"] == "amp":
        raise IntakeError(f"{field_id} is asked per amplifier — save_amp(<project>, index, "
                          f"{field_id.split('.', 1)[1]}=...)")
    if f["per"]:
        raise IntakeError(f"{field_id} is asked per {f['per']} — see `writes`: {writes}")
    handle = project.Project(project_dir)
    if writes == "project:project_type":
        # Through its own writer, not `_set_path`: it is written ONCE, and a generic path write
        # would walk straight past the refusal that makes it mean anything (S-032).
        return handle.set_project_type(value)
    handle.update(lambda data: _set_path(data, writes.split(":", 1)[1], value))
    return value


def save_car(project_dir, make, model, generation, body, year=None):
    """The four parts, together, because they are one identity (`COUPLINGS["car_identity"]`).

    All four are required HERE — that is the difference between this and a generic field write.
    A build recorded without its body answers "no body recorded" forever, and then neither the
    cabin library nor any earlier build on this car can be matched against it; the part that gets
    skipped as obvious is exactly the body. `year` is kept when given and classifies nothing.
    """
    parts = {"make": make, "model": model, "generation": generation, "body": body}
    blank = [k for k, v in parts.items() if not str(v or "").strip()]
    if blank:
        raise IntakeError(
            f"the car is four parts and {', '.join(blank)} " + ("is" if len(blank) == 1 else "are")
            + " blank — a make+model with no generation and no body matches no cabin and no earlier "
              "build on this car (SCR-043). Nothing was written")
    check_value("car.body", body)

    def put(data):
        car = dict(data.get("car") or {})
        car.update(parts)
        if year is not None:
            car["year"] = year
        data["car"] = {k: v for k, v in car.items() if v not in ("", None)}

    return project.Project(project_dir).update(put)["car"]


def save_channel(project_dir, code, source=None, **row):
    """One channel row, through `Project.set_channel` — with the intake's couple enforced.

    `slot` without `tier` is refused: slot letters repeat across tiers (a Helix: virtual A–H,
    outputs B–K), so `F` is a legal address in both and a guess files a spare output among the
    virtual channels (SCR-042). Enumerated fields are checked against the table, and `fs_hz` keeps
    its provenance through `--source`.

    The tier a slot leans on is read with the project's writer lock held, over the write it decides (#141).
    """
    known = {f["id"].split(".", 1)[1]: f for f in FIELDS if f["per"] == "channel"}
    for key, value in row.items():
        f = known.get(key)
        if f is not None and f["enum"]:
            check_value(f["id"], value)
    fields = {k: (True if v == "yes" else False if v == "no" else v)
              if k == "hidden" else v for k, v in row.items()}
    # Provenance goes on the fields the schema keeps as facts (`fs_hz` today), wrapped here the
    # way `project.py`'s own CLI wraps them -- `set_channel` takes the value it is handed.
    for key in project.CHANNEL_FACT_FIELDS:
        if source and key in fields and not project.is_fact(fields[key]):
            fields[key] = project.fact(fields[key], source=source)
    handle = project.Project(project_dir)
    with project._hold(project_dir):
        if "slot" in fields and not fields.get("tier"):
            existing = next((c for c in (_read_project(project_dir) or {}).get("channels", [])
                             if c.get("code") == code), {})
            if not existing.get("tier"):
                raise IntakeError(
                    f"channel {code!r}: a slot needs its tier in the same breath — slot letters repeat "
                    "across tiers, so this one is a legal address in more than one of them. Pass "
                    "tier=channels for a physical output (`dsp_profile.ledger_tier`). Nothing was written")
        handle.set_channel(code, **fields)
        return handle.resolve_channel(code)


def save_amp(project_dir, index=None, **row):
    """One amplifier: appended when `index` is None, replaced in place when it names an existing one."""
    known = {f["id"].split(".", 1)[1] for f in FIELDS if f["per"] == "amp"}
    unknown = [k for k in row if k not in known]
    if unknown:
        raise IntakeError(f"amps take {', '.join(sorted(known))}; got {', '.join(unknown)}")
    written = []

    def put(data):
        amps = list(data.get("amps") or [])
        if index is None:
            amps.append(dict(row))
            at = len(amps) - 1
        else:
            if not 0 <= index < len(amps):
                raise IntakeError(f"no amps[{index}] — this project has {len(amps)}")
            at = index
            amps[at] = dict(amps[at], **row)
        data["amps"] = amps
        written.append(amps[at])

    project.Project(project_dir).update(put)
    return written[0]


# ── CLI ───────────────────────────────────────────────────────────────────────
_USAGE = """usage: intake.py <command> [args]

  fields [--group G] [--required] [--now] [--json]
                                             the intake's fields: id, question, enum, where it lands,
                                             and WHEN it is asked (`--now`: only before measuring)
  couplings [--json]                         the questions that must be asked as ONE control
  gate [<project-dir>] [--json]              what `contract.py check --gate` decides on, as data
  missing <project-dir> [--json]             answered / missing / not machine-readable
  set <project-dir> <field-id> <value>       write one confirmed answer to project.json
  set-car <project-dir> <make> <model> <generation> <body> [--year Y]
  set-channel <project-dir> <code> key=value ... [--source S]
  set-amp <project-dir> [--index N] key=value ...
"""


def _flag(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def _print_fields(rows):
    for r in rows:
        mark = "*" if r["required"] else " "
        enum = f"  [{', '.join(map(str, r['enum']))}]" if r["enum"] else ""
        where = r["writes"] or r["lands"] or ""
        when = "" if r["when"] == "now" else f"  (later: {r['when']})"
        print(f" {mark} {r['id']:<34} {r['ask']}{enum}{when}")
        if where:
            print(f"     -> {where}" + (f"   (per {r['per']})" if r["per"] else ""))


def _main(argv):
    """The command line. Of what its verbs let out, the project's writer lock alone is said here (#141,
    `write_lock.py`): another writer held it past the wait -- 75, its one `busy:` line, nothing written, safe to retry
    -- or the wait, AUTOSOUND_LOCK_TIMEOUT_S, is no number of seconds: a usage error, 2, said before anything was
    taken. Everything else keeps its traceback, as before: TCC reads a refusal's sentence off its last line
    (`car_library._sentence`)."""
    try:
        return _dispatch(argv)
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
        if getattr(type(exc), "is_busy", False):
            return project._write_lock().busy_exit(exc)
        if getattr(type(exc), "exit_code", None) == 2:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        raise


def _dispatch(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    as_json = "--json" in rest

    if cmd == "fields":
        rows = fields(group=_flag(rest, "--group"), required_only="--required" in rest,
                      when="now" if "--now" in rest else None)
        if as_json:
            print(json.dumps({"groups": groups(), "when": [{"id": w, "what": what} for w, what in WHEN],
                              "fields": rows}, ensure_ascii=False, indent=2))
        else:
            _print_fields(rows)
            print(f"\n  {len(rows)} fields, {sum(1 for r in rows if r['required'])} required "
                  f"(*). Couples: intake.py couplings")
        return 0

    if cmd == "couplings":
        data = couplings()
        if as_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            for c in data:
                print(f"  {c['id']}: {', '.join(c['fields'])}\n     {c['why']}\n")
        return 0

    if cmd == "gate":
        project_dir = next((a for a in rest if not a.startswith("-")), None)
        data = gate_requirements(project_dir)
        if as_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"  {data['command']}\n")
            for f in data["files"]:
                print(f"  {f['file']:<40} {f['what']}")
                print(f"     keys: {', '.join(map(str, f.get('validated_keys', ())))}")
                print(f"     why : {f['why']}")
            print(f"\n  ledger: {data['ledger']['what']}")
            if data["ledger"].get("tiers"):
                print(f"     tiers this profile declares: {', '.join(data['ledger']['tiers'])}")
            if "gate_open" in data:
                print(f"\n  gate open: {data['gate_open']}"
                      + (f" — missing {', '.join(data['missing_files'])}"
                         if data["missing_files"] else "")
                      + "".join(f"\n     cannot be read: {u['issue']}" for u in data["unreadable_files"]))
        return 0

    if cmd == "missing":
        if not rest:
            print(_USAGE, file=sys.stderr)
            return 2
        data = missing(rest[0])
        if as_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"  answered            {len(data['answered'])}")
            print(f"  missing             {len(data['missing'])}"
                  f"  (required: {len(data['required_missing'])}, "
                  f"of them needed before measuring: {len(data['required_missing_now'])})")
            print(f"  not machine-readable {len(data['not_machine_readable'])}"
                  f"  — prose and recorded decisions\n")
            for r in data["missing"]:
                if r["id"] in data["required_missing_now"]:
                    print(f"  * {r['id']:<34} {r['ask']}")
        return 0

    if cmd == "set":
        if len(rest) < 3:
            print(_USAGE, file=sys.stderr)
            return 2
        value = dsp_profile.maybe_decode_json(rest[2])
        print(json.dumps({"set": rest[1], "value": save(rest[0], rest[1], value)},
                         ensure_ascii=False))
        return 0

    if cmd == "set-car":
        if len(rest) < 5:
            print(_USAGE, file=sys.stderr)
            return 2
        car = save_car(rest[0], rest[1], rest[2], rest[3], rest[4], year=_flag(rest, "--year"))
        print(json.dumps({"car": car}, ensure_ascii=False))
        return 0

    if cmd == "set-channel":
        if len(rest) < 3:
            print(_USAGE, file=sys.stderr)
            return 2
        row = {}
        for pair in rest[2:]:
            if "=" in pair and not pair.startswith("-"):
                k, _, v = pair.partition("=")
                row[k] = dsp_profile.maybe_decode_json(v)
        print(json.dumps({"channel": save_channel(rest[0], rest[1],
                                                  source=_flag(rest, "--source"), **row)},
                         ensure_ascii=False))
        return 0

    if cmd == "set-amp":
        if len(rest) < 2:
            print(_USAGE, file=sys.stderr)
            return 2
        index = _flag(rest, "--index")
        row = {}
        for pair in rest[1:]:
            if "=" in pair and not pair.startswith("-"):
                k, _, v = pair.partition("=")
                row[k] = dsp_profile.maybe_decode_json(v)
        print(json.dumps({"amp": save_amp(rest[0], int(index) if index is not None else None, **row)},
                         ensure_ascii=False))
        return 0

    print(_USAGE, file=sys.stderr)
    return 2


# ── selftest ──────────────────────────────────────────────────────────────────
def _check_change_dsp_sets_an_unreadable_profile_aside():
    """A processor change sets a profile that cannot be read aside, as it sets aside any other old one (#136, ruling
    R26). `load_profile` raises for such a file now, and `change_dsp` met that after `project.json` was saved: the
    change half made. The step exists to replace that profile, so it goes aside unread and byte for byte, nothing in
    it carried over, and one line on stderr names it and where it went -- a cut profile and a draft a newer method
    wrote alike. The new processor's own profile is then made as for any other. `gate_requirements` reports such a
    profile as the tier list's error, as it reports any other."""
    import contextlib
    import io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_unreadable_")
    try:
        project.Project(top).save({"schema_version": project.SCHEMA_VERSION, "channels": [],
                                   "dsp": {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S"}})
        prof, draft = dsp_profile.profile_path(top), dsp_profile.draft_path(top)
        damaged = {prof: b'{"dsp_profile": {"name": "Helix DSP Ultra S", "gro',
                   draft: json.dumps({"schema_version": dsp_profile.SCHEMA_VERSION + 1, "dsp_profile": {
                       "name": "Helix DSP Ultra S", "vendor": "Audiotec-Fischer", "groups": []}}).encode("utf-8")}
        for path, raw in damaged.items():
            with open(path, "wb") as fh:
                fh.write(raw)
        tiers = gate_requirements(top)["ledger"]
        assert tiers["tiers"] is None and str(tiers.get("tiers_error")).startswith(prof + " "), tiers
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            done = change_dsp(top, "Acme", "X8")
        assert len(done["set_aside"]) == 2 and not os.path.exists(prof) and not os.path.exists(draft), done
        said = err.getvalue().splitlines()
        assert said == done.get("said") and len(said) == 2, (said, done)
        for (path, raw), target, line, reason in zip(damaged.items(), done["set_aside"], said, (
                "is not valid JSON", f"is schema v{dsp_profile.SCHEMA_VERSION + 1}; this method reads v")):
            assert os.path.basename(target).startswith(os.path.basename(path)[:-5] + ".replaced-"), target
            with open(target, "rb") as fh:
                assert fh.read() == raw, f"{target} is not the file set aside, byte for byte"
            assert line.startswith(f"{path} {reason}") and f"set aside as {target}," in line, line
        assert project.Project(top).load()["dsp"]["vendor"] == "Acme", "the processor did not change"
        save_new_dsp(top, {"tiers": {"channels": {"count": "4", "letters": True, "fields": ["hp", "lp", "ta_ms"]}},
                           "delay": {"step_ms": "0.02", "max_ms": "10"}, "rate": 48000})
        made = dsp_profile.load_draft(top)
        assert dsp_profile._unwrap(made)["vendor"] == "Acme" and "Helix" not in json.dumps(made), made
        for path, target in zip(damaged, done["set_aside"]):
            with open(target, "rb") as fh:
                assert fh.read() == damaged[path], f"{target} changed after it was set aside"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_gate_shut_over_an_unreadable_file():
    """`gate_requirements` keeps the gate shut while a gate file is there and cannot be read, and names it (#134, batch
    4's re-review N4 / Out of Scope 4): `gate_open` was "no file missing", so a `project.json` cut off opened the gate
    `enter-phase 0` refuses (`process._require_intake` refuses the check's `unreadable`) -- and, with `check` reading
    `glossary.json` strictly, a cut one would have too, where it used to read as missing. `unreadable_files` is the
    check's `unreadable`."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_gate_unreadable_")
    try:
        project.Project(top).save({"schema_version": project.SCHEMA_VERSION,
                                   "channels": [{"code": "w-L", "tier": "channels"}],
                                   "glossary": {"schema_version": 1, "channels": [{"code": "w-L", "active": True}]}})
        dsp_profile.save_profile(os.path.join(top, "dsp_profile.json"), {"dsp_profile": {
            "name": "Fixture", "vendor": "Fixture", "dsp_processing_rate_hz": 96000,
            "delay": {"step_ms": 0.01}, "polarity": {"scope": []},
            "groups": [{"id": "physical_outputs", "label": "Outputs", "max_count": 2,
                        "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity"],
                        "crossover_filters": {"types": {"LR": {"orders_db_per_oct": [24]}}}}]}})
        assert gate_requirements(top)["gate_open"] is True, gate_requirements(top)
        failures = []
        for name in ("glossary.json", "project.json"):
            path = os.path.join(top, name)
            before = None
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    before = fh.read()
            with open(path, "wb") as fh:
                fh.write(b'{"schema_version": 1, "chan')
            g = gate_requirements(top)
            if g["gate_open"] is not False or [u["file"] for u in g.get("unreadable_files") or []] != [name]:
                failures.append(f"{name} cut off: gate_open {g['gate_open']!r}, missing {g['missing_files']}, "
                                f"unreadable {g.get('unreadable_files')}")
            if before is None:
                os.remove(path)
            else:
                with open(path, "wb") as fh:
                    fh.write(before)
        assert not failures, "\n  ".join(["the gate over a file it cannot read:"] + failures)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_set_car_waits_for_the_lock():
    """`set-car` -- the writer TCC spawns from here (`car_library.record`) -- waits AUTOSOUND_LOCK_TIMEOUT_S for another
    writer's lock and exits 75 with one `busy:` line (#141, J2b): no traceback, `project.json` as it was, safe to
    retry. So do the other writing verbs, and the writers the form calls -- a processor changed, a slot switched or
    moved, the knobs. Let go, `set-car` lands. Its other refusals keep their traceback: TCC reads an `IntakeError`'s
    sentence off its last line (`car_library._sentence`)."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_busy_")
    failures = []
    try:
        proj = os.path.join(top, "car")
        project.Project(proj).save({"schema_version": project.SCHEMA_VERSION,
                                    "dsp": {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S"},
                                    "channels": [{"code": "w-L", "tier": "channels", "slot": "C"}]})
        before = project._files_in(proj)
        with project._held_elsewhere(proj):
            for argv in (["set-car", proj, "VW", "Passat", "B8", "sedan"], ["set", proj, "project.language", "uk"],
                         ["set-channel", proj, "m-L", "tier=channels", "slot=D"], ["set-amp", proj, "model=GZPA 4SQ"]):
                rc, out, err = project._run_cli(_main, argv, AUTOSOUND_LOCK_TIMEOUT_S="0.2")
                why = project._said_busy(rc, err, proj)
                if why:
                    failures.append(f"{argv[0]}: {why}")
            for label, call in (("change_dsp", lambda: change_dsp(proj, "Musway", "M6V4", replace_map=True)),
                                ("save_slot", lambda: save_slot(proj, "channels", "D", "m-L")),
                                ("move_slot", lambda: move_slot(proj, "channels", "w-L", "E")),
                                ("save_controls", lambda: save_controls(proj, {"SubRC": "4/4"}))):
                try:
                    with project._env(AUTOSOUND_LOCK_TIMEOUT_S="0.2"):
                        call()
                except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
                    if not getattr(type(exc), "is_busy", False):
                        failures.append(f"{label}: {type(exc).__name__}: {exc}")
                else:
                    failures.append(f"{label}: went through under another writer's lock")
            if project._files_in(proj) != before:
                failures.append("something was written under another writer's lock")
        rc, out, err = project._run_cli(_main, ["set-car", proj, "VW", "Passat", "B8", "sedan"],
                                        AUTOSOUND_LOCK_TIMEOUT_S="0.2")
        if rc != 0 or (project.Project(proj).load().get("car") or {}).get("make") != "VW":
            failures.append(f"let go, set-car did not land: rc {rc}, said {err.strip()[-200:]!r}")
        rc, out, err = project._run_cli(_main, ["set-car", proj, "VW", "", "B8", "sedan"])
        if rc != "raised" or "IntakeError: the car is four parts" not in (err.strip().splitlines() or [""])[-1]:
            failures.append(f"a blank part no longer ends in its IntakeError's traceback: rc {rc}, "
                            f"said {err.strip()[-200:]!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} run(s) under a held lock:\n  " + "\n  ".join(failures)


def _check_a_bad_timeout_is_a_usage_error():
    """An AUTOSOUND_LOCK_TIMEOUT_S that is no number of seconds makes `set-car` a usage error (#141): exit 2, one line
    naming the variable, no traceback, and nothing written or made -- not the lock's `.autosound/` either."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_bad_wait_")
    try:
        proj = os.path.join(top, "car")
        os.makedirs(proj)
        with open(os.path.join(proj, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema_version": project.SCHEMA_VERSION, "project_rev": 1, "channels": []}, fh)
        before = project._files_in(proj)
        rc, out, err = project._run_cli(_main, ["set-car", proj, "VW", "Passat", "B8", "sedan"],
                                        AUTOSOUND_LOCK_TIMEOUT_S="soon")
        lines = err.strip().splitlines()
        assert rc == 2 and len(lines) == 1 and "AUTOSOUND_LOCK_TIMEOUT_S=soon" in lines[0], (rc, err.strip()[-300:])
        assert project._files_in(proj) == before and sorted(os.listdir(proj)) == ["project.json"], \
            f"wrote or made something: {sorted(os.listdir(proj))}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_composite_writers_hold_once():
    """A writer here that reads `project.json` and then writes more than once -- a processor changed and its old
    profile set aside, a slot switched on or moved, a channel whose slot leans on the tier it has -- holds the project's
    lock from its first read to its last write (#141, J2b): what it decided on is what it writes. Watched at the
    `Project` writers it calls and at the set-aside: each is reached with the lock held already."""
    import shutil
    import tempfile
    lock = project._write_lock()
    top = tempfile.mkdtemp(prefix="autosound_intake_held_")
    proj = os.path.join(top, "car")
    real = {"set_channel": project.Project.set_channel, "rename_channel": project.Project.rename_channel}
    real_set_aside = _set_aside
    seen, failures = [], []

    def watched(name, fn):
        def call(*args, **kwargs):
            seen.append((name, lock.held_here(proj)))
            return fn(*args, **kwargs)
        return call
    try:
        project.Project(proj).save({"schema_version": project.SCHEMA_VERSION,
                                    "dsp": {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S"},
                                    "channels": [{"code": "w-L", "tier": "channels", "slot": "C"}]})
        dsp_profile.save_profile(dsp_profile.profile_path(proj), {"dsp_profile": {
            "name": "Helix DSP Ultra S", "vendor": "Audiotec-Fischer",
            "groups": [{"id": "physical_outputs", "label": "Outputs", "fields": ["hp", "lp", "gain_db"]}]}})
        for name, fn in real.items():
            setattr(project.Project, name, watched(name, fn))
        globals()["_set_aside"] = watched("_set_aside", real_set_aside)
        for label, call in (("change_dsp", lambda: change_dsp(proj, "Musway", "M6V4", replace_map=True)),
                            ("save_slot", lambda: save_slot(proj, "channels", "D", "m-L")),
                            ("save_slot, a rename", lambda: save_slot(proj, "channels", "D", "mid-L")),
                            ("move_slot", lambda: move_slot(proj, "channels", "mid-L", "E")),
                            ("save_channel", lambda: save_channel(proj, "mid-L", slot="F"))):
            del seen[:]
            call()
            if not seen or not all(held for _name, held in seen):
                failures.append(f"{label}: {seen}")
    finally:
        for name, fn in real.items():
            setattr(project.Project, name, fn)
        globals()["_set_aside"] = real_set_aside
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "reached with the project's lock free:\n  " + "\n  ".join(failures)


def _check_save_controls_holds_once():
    """The knobs the form saves are written under one hold of the project's lock (#141, R20): another writer -- a
    thread, through the real lock -- that tries once a knob is in cannot get in until the last one is written, and one
    that holds the lock first leaves the save busy with no knob written. Each knob took the lock for itself, so a busy
    at the second said "nothing was written" over the first. Then it lets go."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_knobs_once_")
    real, tried, failures = project.Project.set_hardware_control, [], []

    def watched(self, name, value, source=None):
        if tried or name != "SubRC":                    # a knob is in: another writer tries before the next one
            tried.append(project._another_writer_tries(proj))
        return real(self, name, value, source=source)
    try:
        for name in ("car", "held"):
            project.Project(os.path.join(top, name)).save({"schema_version": project.SCHEMA_VERSION, "channels": []})
        proj = os.path.join(top, "car")
        knobs = {"SubRC": "4/4", "RearRC": "2", "Bass": "7"}
        project.Project.set_hardware_control = watched
        try:
            written = save_controls(proj, knobs)
        finally:
            project.Project.set_hardware_control = real
        if len(tried) != 2 or not all(getattr(type(t), "is_busy", False) for t in tried):
            failures.append(f"another writer got in between the knobs: {tried}")
        on_disk = {k: project.fact_value(v) for k, v in
                   ((project.Project(proj).load().get("hardware") or {}).get("controls") or {}).items()}
        if written != knobs or on_disk != knobs:
            failures.append(f"the knobs did not land: {written} / {on_disk}")
        let_go = project._another_writer_tries(proj)
        if let_go is not None:
            failures.append(f"not let go after the knobs: {let_go!r}")
        proj = os.path.join(top, "held")
        before = project._files_in(proj)
        with project._held_elsewhere(proj), project._env(AUTOSOUND_LOCK_TIMEOUT_S="0.2"):
            busy = project._raised_by(lambda: save_controls(proj, knobs))
        if not getattr(type(busy), "is_busy", False) or project._files_in(proj) != before:
            failures.append(f"under another writer's lock: {busy!r}, written: {project._files_in(proj) != before}")
    finally:
        project.Project.set_hardware_control = real
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the knobs' one hold:"] + failures)


def _check_save_new_dsp_holds_once():
    """A new processor's base is written under one hold of the project's lock (#141, R20) -- the draft or profile of
    another processor set aside, the draft started, each field set: another writer -- a thread, through the real lock
    -- that tries once a part is in cannot get in until the last field is written, and one that holds the lock first
    leaves the save busy with nothing landed, the old draft where it was. The set-aside ran with no lock at all, and
    each later part took it for itself: under a held lock the old draft was moved, then the save said busy."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_new_dsp_once_")
    real_field, real_aside, tried, failures = dsp_profile.set_field, _set_aside, [], []
    answers = {"tiers": {"channels": {"count": "4", "letters": True, "fields": ["hp", "lp", "ta_ms"]}},
               "delay": {"step_ms": "0.02", "max_ms": "10"}, "rate": 48000}
    old = {"dsp_profile": {"name": "Old", "vendor": "Oldco", "groups": []}}

    def fixture(name):
        proj = os.path.join(top, name)
        project.Project(proj).save({"schema_version": project.SCHEMA_VERSION, "channels": [],
                                    "dsp": {"vendor": "Acme", "model": "X8"}})
        with open(dsp_profile.draft_path(proj), "w", encoding="utf-8") as fh:
            json.dump(old, fh)
        return proj

    def watched(fn):
        def call(*args, **kwargs):                      # another writer tries before each part
            tried.append(project._another_writer_tries(proj))
            return fn(*args, **kwargs)
        return call
    try:
        proj = fixture("car")
        dsp_profile.set_field = watched(real_field)
        globals()["_set_aside"] = watched(real_aside)
        try:
            save_new_dsp(proj, answers)
        finally:
            dsp_profile.set_field = real_field
            globals()["_set_aside"] = real_aside
        if len(tried) < 3 or not all(getattr(type(t), "is_busy", False) for t in tried):
            failures.append(f"another writer got in between the parts: {tried}")
        draft = dsp_profile._unwrap(dsp_profile.load_draft(proj))
        aside = [n for n in os.listdir(proj) if ".replaced-" in n]
        if draft.get("vendor") != "Acme" or len(aside) != 1:
            failures.append(f"the base did not land: vendor {draft.get('vendor')!r}, set aside {aside}")
        let_go = project._another_writer_tries(proj)
        if let_go is not None:
            failures.append(f"not let go after the base: {let_go!r}")
        proj = fixture("held")
        before = project._files_in(proj)
        with project._held_elsewhere(proj), project._env(AUTOSOUND_LOCK_TIMEOUT_S="0.2"):
            busy = project._raised_by(lambda: save_new_dsp(proj, answers))
        if not getattr(type(busy), "is_busy", False):
            failures.append(f"under another writer's lock: {busy!r}")
        if project._files_in(proj) != before:
            failures.append(f"landed under another writer's lock: {sorted(set(project._files_in(proj)) ^ set(before))}")
    finally:
        dsp_profile.set_field = real_field
        globals()["_set_aside"] = real_aside
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the new processor's one hold:"] + failures)


def _check_a_missing_project_makes_nothing():
    """A verb that does not create a project makes nothing on a project folder that is not there (#141, R23): no folder,
    no `.autosound/`, and the verb's own refusal -- its `IntakeError` in its traceback's last line, exit 1 from the
    command line -- which says "Nothing was written". The lock made `<typo>/.autosound/` under that sentence. The
    creator still creates: `set-car` makes the folder and its `project.json`; under a parent this user may not write
    it refuses as the lock does, the sentence the last line of its traceback, nothing made."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_intake_gone_")
    failures = []
    cases = ((["set-channel", "m-L", "slot=D"],
              "IntakeError: channel 'm-L': a slot needs its tier in the same breath — slot letters repeat across "
              "tiers, so this one is a legal address in more than one of them. Pass tier=channels for a physical "
              "output (`dsp_profile.ledger_tier`). Nothing was written"),
             (["set-amp", "model=GZPA 4SQ", "--index", "0"], "IntakeError: no amps[0] — this project has 0"))
    try:
        for n, (argv, line) in enumerate(cases):
            gone = os.path.join(top, f"gone-{n}")
            rc, out, err = project._run_cli(_main, [argv[0], gone, *argv[1:]])
            last = (err.strip().splitlines() or [""])[-1]
            if rc != "raised" or not last.endswith(line) or out.strip():
                failures.append(f"{argv[0]}: rc {rc}, said {last!r}")
            if os.path.lexists(gone):
                failures.append(f"{argv[0]}: made {sorted(os.listdir(gone)) if os.path.isdir(gone) else gone}")
        new = os.path.join(top, "new")
        rc, out, err = project._run_cli(_main, ["set-car", new, "VW", "Passat", "B8", "sedan"])
        made = sorted(os.listdir(new)) if os.path.isdir(new) else None
        if rc != 0 or (project.Project(new).load().get("car") or {}).get("make") != "VW" or made != ["project.json"]:
            failures.append(f"set-car on a new folder: rc {rc}, said {(out + err).strip()[-200:]!r}, made {made}")
        # Under a parent this user may not write the creator refuses as the lock does (`write_lock.make_folder`):
        # its traceback kept (R12), the refusal sentence its last line, exit 1, nothing made. That line was a raw
        # PermissionError's.
        if project._mode_refuses("set-car under a parent this user may not write", "intake"):
            with project._under_a_read_only_parent(top) as new:
                rc, out, err = project._run_cli(_main, ["set-car", new, "VW", "Passat", "B8", "sedan"])
                last = (err.strip().splitlines() or [""])[-1]
                if rc != "raised" or not last.endswith(".Unwritable: " + project._cannot_be_made(new)) \
                        or os.listdir(os.path.dirname(new)):
                    failures.append(f"set-car under a parent this user may not write: rc {rc}, said {last!r}, made "
                                    f"{sorted(os.listdir(os.path.dirname(new)))}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a project folder that is not there:"] + failures)


def _check_no_load_and_save_outside_update():
    """No function here loads `project.json` and saves it itself (#141, J2b): each write goes through `Project.update`
    or a `Project` writer, which hold the project's lock across the read and the write. Read off the source
    (`project._load_and_save_paths`, shown each shape it looks for by `project.py`'s own check)."""
    with open(os.path.realpath(__file__), encoding="utf-8") as fh:
        found = project._load_and_save_paths(fh.read())
    assert not found, f"load-and-save outside Project.update: {found}"


def _selftest():
    import tempfile

    failures = []
    for check in (_check_change_dsp_sets_an_unreadable_profile_aside, _check_gate_shut_over_an_unreadable_file,
                  _check_set_car_waits_for_the_lock, _check_a_bad_timeout_is_a_usage_error,
                  _check_composite_writers_hold_once, _check_save_controls_holds_once,
                  _check_save_new_dsp_holds_once, _check_a_missing_project_makes_nothing,
                  _check_no_load_and_save_outside_update):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    # ── the table is well formed, and every destination it names is REAL ──────────────────────
    ids = [f["id"] for f in FIELDS]
    assert len(ids) == len(set(ids)), "duplicate field id"
    group_ids = {g for g, _ in GROUPS}
    skeleton = set(project._empty_project())
    for f in FIELDS:
        assert f["group"] in group_ids, f
        assert f["ask"].strip(), f
        # A `project:` path that names a top-level key the schema does not have is a field nobody
        # will ever read back -- the kind of typo a table of strings makes easy and silent.
        if (f["writes"] or "").startswith("project:"):
            top = f["writes"].split(":", 1)[1].split("[")[0].split(".")[0]
            # `measurement` (SCR-059) and `goal` (the page's optional goal block, 2026-09-22) are
            # written by this module and documented in `project-schema.md`, not seeded empty.
            assert top in skeleton or top in ("measurement", "goal"), \
                f"{f['id']} writes to unknown key {top!r}"
        # Every field with no machine home says where the answer DOES go. "Nowhere" is not an
        # answer a form can act on, and prose that nobody names is prose nobody writes.
        if f["writes"] is None:
            assert f["lands"], f"{f['id']} has no writes and no lands"
        if f["ask_with"]:
            assert f["ask_with"] in COUPLINGS, f
    for c in couplings():
        assert len(c["fields"]) >= 2, f"a couple of one is not a couple: {c['id']}"
        assert c["why"].strip(), c

    # ── WHEN: the intake is short, and what it defers is still in the table ──────────────────
    when_ids = [w for w, _ in WHEN]
    for f in FIELDS:
        assert f["when"] in when_ids, f"{f['id']}: unknown step {f['when']!r}"
        # A default is an answer the form pre-selects, so it must be one the field would take.
        if f["default"] is not None and f["enum"]:
            check_value(f["id"], f["default"])
    # The Phase-0 gate decides on the glossary and the profile's tiers; deferring either would
    # have the form say "later" to a question the gate refuses without.
    for f in FIELDS:
        if (f["writes"] or "") in ("glossary:", "dsp_profile.draft:groups"):
            assert f["when"] == "now", f"{f['id']} feeds the Phase-0 gate and cannot wait"
    # The seat decides where the mic stands for the very first capture: never deferred.
    assert field("goal.reference_seat")["when"] == "now"
    now = fields(when="now")
    assert 0 < len(now) < len(FIELDS) // 2, f"{len(now)} of {len(FIELDS)} fields asked up front"
    # WHERE a form shows each field: a known place, and nothing a tool answers is put to a person.
    place_ids = [pl for pl, _ in PLACES]
    for f in FIELDS:
        assert f["place"] in place_ids, f"{f['id']}: unknown place {f['place']!r}"
        if f["place"] == "now":
            assert f["when"] == "now" and f["derive"] is None, f"{f['id']} is asked up front and is not a now question"
    # The processor's base questions are asked only for a NEW processor, and every capability
    # checklist question except the input routing (a memo, the Arbiter 2026-09-22) is among them.
    assert {f["checklist"] for f in FIELDS if f["place"] == "new_dsp" and f["checklist"] is not None} \
        == set(range(len(dsp_profile.CAPABILITY_CHECKLIST) - 1))
    # The choices are read off what the skill ships -- the DSP library and the test-track file.
    dsps = known_dsps()
    assert dsps and all(d["vendor"] and d["model"] for d in dsps), dsps
    assert {"carmus", "chesky", "emma", "aya", "streaming"} <= set(TRACK_LIBRARIES), TRACK_LIBRARIES
    assert any(c["source"] == "library" for c in known_cars()), "the cabin library offers no car"

    # ── the DSP half stays the profile's: every checklist question is CLAIMED by a field ──────
    # Not copied -- the questions come off `dsp_profile.CAPABILITY_CHECKLIST` at import. This
    # asserts coverage, so a new capability question fails here until a field carries it, rather
    # than being asked in prose for another year (which is what SCR-059 is about).
    claimed = {f["checklist"] for f in FIELDS if f["checklist"] is not None}
    assert claimed == set(range(len(dsp_profile.CAPABILITY_CHECKLIST))), (
        f"capability checklist questions with no intake field: "
        f"{sorted(set(range(len(dsp_profile.CAPABILITY_CHECKLIST))) - claimed)}")
    for f in FIELDS:
        if f["checklist"] is not None:
            assert f["ask"] == dsp_profile.CAPABILITY_CHECKLIST[f["checklist"]], (
                f"{f['id']} paraphrases the checklist instead of quoting it")

    # ── the gate list is the GATE's, not a copy ───────────────────────────────────────────────
    gate = gate_requirements()
    assert [f["file"] for f in gate["files"]] == list(contract.GATE_REQUIRED), gate
    assert all(f.get("why") and f.get("validated_keys") for f in gate["files"]), gate
    assert set(gate["files"][1]["validated_keys"]) == set(dsp_profile.TOP_REQUIRED)
    assert "channels" in gate["files"][2]["validated_keys"], "glossary collections read off the class"
    assert "project.json" in [f["file"] for f in gate["files"]]

    # ── the enumerations refuse, and say what they would take ─────────────────────────────────
    for bad, fid in (("saloon", "car.body"), ("RHS", "car.drive_side"),
                     # `driver_only` is the OLD spelling and is not one of the six (S-032)
                     ("driver_only", "goal.reference_seat"), ("4", "dsp.capability_level")):
        try:
            check_value(fid, bad)
            raise AssertionError(f"{fid} took {bad!r}")
        except IntakeError as exc:
            assert "one of" in str(exc) and bad in str(exc), exc
    check_value("goal.formats", ["EMMA", "AYA"])          # multi takes a list
    try:
        check_value("goal.purpose", ["competition", "enjoyment"])
        raise AssertionError("a single-answer field took a list")
    except IntakeError as exc:
        assert "one answer" in str(exc), exc
    # An unknown id names the closest real ones rather than just refusing.
    try:
        field("car.bodystyle")
        raise AssertionError("an unknown field id passed")
    except IntakeError as exc:
        assert "car.body" in str(exc), exc

    with tempfile.TemporaryDirectory() as root:
        # ── the writer: the car is four parts, and a blank one stops the write ────────────────
        for blank in (("VW", "Passat", "B8", ""), ("VW", "Passat", "", "sedan")):
            try:
                save_car(root, *blank)
                raise AssertionError(f"the car went in with a blank part: {blank}")
            except IntakeError as exc:
                assert "four parts" in str(exc) and "Nothing was written" in str(exc), exc
        assert not os.path.isfile(os.path.join(root, "project.json")), "a refusal wrote a file"
        car = save_car(root, "VW", "Passat", "B8", "sedan", year=2018)
        assert car == {"make": "VW", "model": "Passat", "generation": "B8", "body": "sedan",
                       "year": 2018}, car
        try:
            save_car(root, "VW", "Passat", "B8", "saloon")
            raise AssertionError("an invented body went in")
        except IntakeError as exc:
            assert "sedan" in str(exc), exc

        # ── flat fields go in; the enumeration is checked on the way ─────────────────────────
        save(root, "source.connection", "optical")
        save(root, "source.listening_input", "Optical 1")
        save(root, "source.measurement_input", "Coax 2")
        save(root, "rew.loopback", "acoustic")      # the Arbiter's second choice is a real one now
        save(root, "rew.loopback", "physical")
        save(root, "rew.capture_rate_hz", 48000)
        data = project.Project(root).load()
        assert data["source"]["measurement_input"] == "Coax 2", data["source"]
        assert data["measurement"]["loopback"] == "physical", data["measurement"]
        try:
            save(root, "rew.loopback", "usb")
            raise AssertionError("an invented loopback passed")
        except IntakeError as exc:
            assert "physical" in str(exc), exc

        # ── a field that is not this writer's says WHOSE it is ───────────────────────────────
        for fid, value, expect in (("channel_map.code", "w-R", "save_channel"),
                                   ("amps.make", "Helix", "save_amp"),
                                   ("dsp.eq", "10 PK bands", "dsp_profile.set_field"),
                                   ("channel_map.glossary_agreed", "yes", "glossary.json")):
            try:
                save(root, fid, value)
                raise AssertionError(f"{fid} was written by the wrong writer")
            except IntakeError as exc:
                assert expect in str(exc), (fid, exc)

        # ── S-032: the seat is what the project IS, and it is written ONCE ──────────────────
        # Fails on the old code at the first line: the field had `writes: None` (it "landed" in
        # prose and a recorded decision), and its enumeration was three values inside one project.
        assert field("goal.reference_seat")["writes"] == "project:project_type", field("goal.reference_seat")
        assert REFERENCE_SEATS == project.PROJECT_TYPES == (
            "driver", "passenger", "both", "all", "rear_left", "rear_right"), REFERENCE_SEATS
        save(root, "goal.reference_seat", "driver")
        assert project.project_type(project.Project(root).load()) == "driver"
        save(root, "goal.reference_seat", "driver")          # the same answer again is a no-op
        try:
            save(root, "goal.reference_seat", "passenger")
            raise AssertionError("a project changed which seat it is tuned for")
        except (IntakeError, project.ProjectError) as exc:
            # The refusal has to carry the ROUTE, or it is a dead end rather than a rule.
            assert "ANOTHER PROJECT" in str(exc) and "none of its measurements" in str(exc), exc
        assert project.project_type(project.Project(root).load()) == "driver", "nothing was written"

        # ── a slot with no tier is refused, and refused BEFORE anything is written ───────────
        try:
            save_channel(root, "w-L", slot="C")
            raise AssertionError("a slot went in without its tier")
        except IntakeError as exc:
            assert "repeat across tiers" in str(exc), exc
        assert not project.Project(root).load().get("channels"), "the refusal still wrote a row"
        save_channel(root, "w-L", slot="C", tier="channels", role="woofer",
                     position="door", enclosure="free_air", condition="broken_in",
                     driver={"make": "Audiofrog", "model": "GB25"}, fs_hz=62, source="datasheet")
        row = project.Project(root).load()["channels"][0]
        assert row["slot"] == "C" and row["tier"] == "channels", row
        assert project.fact_value(row["fs_hz"]) == 62 and row["fs_hz"]["source"] == "datasheet", row
        # A second write on the same channel does not have to repeat the tier it already has.
        save_channel(root, "w-L", slot="D")
        assert project.Project(root).load()["channels"][0]["slot"] == "D"
        try:
            save_channel(root, "m-L", slot="E", tier="channels", position="boot")
            raise AssertionError("an invented position went in")
        except IntakeError as exc:
            assert "trunk" in str(exc), exc

        # ── amps append and update in place ──────────────────────────────────────────────────
        amp = save_amp(root, None, make="Helix", model="P Six DSP", channels="front")
        assert amp["make"] == "Helix", amp
        save_amp(root, 0, gain_db=-6.0)
        amps = project.Project(root).load()["amps"]
        assert len(amps) == 1 and amps[0]["gain_db"] == -6.0, amps
        try:
            save_amp(root, None, brand="Helix")
            raise AssertionError("an unknown amp field went in")
        except IntakeError as exc:
            assert "make" in str(exc), exc

        # ── `missing` moves when an answer lands, and never calls prose a gap ────────────────
        before = missing(root)
        assert "car.make" in [r["id"] for r in before["answered"]], before["answered"]
        assert "dsp.vendor" in before["required_missing"], before["required_missing"]
        # S-032: it used to be the example of a field with no machine home. It has one now, and it
        # is ANSWERED above -- so the example moves to a field that still lands only in prose.
        assert "goal.reference_seat" in [r["id"] for r in before["answered"]], before["answered"]
        assert before["not_machine_readable"], "some fields still land in prose, and say so"
        # What to ask now is a subset of what is required, and never a tool's job or a later step's.
        assert set(before["required_missing_now"]) <= set(before["required_missing"])
        assert "dsp.vendor" in before["required_missing_now"]
        assert "rew.mic_model" not in before["required_missing"], "the mic is not asked (2026-09-22)"
        assert "target_curve.candidate" not in before["required_missing_now"], "the curve waits for Phase 0"
        assert "rew.api_reachable" not in before["required_missing_now"], "a probe is not a question"
        save(root, "dsp.vendor", "Musway")
        after = missing(root)
        assert "dsp.vendor" not in after["required_missing"]
        assert len(after["required_missing"]) == len(before["required_missing"]) - 1, (
            before["required_missing"], after["required_missing"])

        # ── the processor: known on an exact match, NEW otherwise; the goal block is writable ──
        assert dsp_state(root)["new"] is None, "a vendor with no model is not a processor yet"
        save(root, "dsp.model", "M6V4 (no 512K)")
        st = dsp_state(root)
        assert st["new"] is False and st["source"] == "bundled" and st["tiers"] == ["channels"], st
        save(root, "dsp.model", "Some Unknown 8")
        assert dsp_state(root)["new"] is True, "an unknown processor is not flagged as new"
        save(root, "goal.formats", ["EMMA"])
        save(root, "target_curve.genres", ["jazz", "rock"])
        save(root, "target_curve.track_library", ["chesky", "streaming"])
        assert project.Project(root).load()["goal"]["genres"] == ["jazz", "rock"]
        # A sibling project's car is offered to the next project; this one's own is not.
        sib = os.path.join(root, "sibling")
        save_car(sib, "Skoda", "Octavia", "A7", "wagon")
        labels = [c["label"] for c in known_cars(os.path.join(root, "third"))]
        assert "Skoda Octavia A7 wagon" in labels, labels
        assert "Skoda Octavia A7 wagon" not in [c["label"] for c in known_cars(sib)]

        # ── round 3: a slot is switched on under a code, or off as `off-<tier>-<slot>` ──────
        slots = os.path.join(root, "slots")
        save(slots, "dsp.vendor", "Audiotec-Fischer")
        save(slots, "dsp.model", "Helix DSP Ultra S")
        cmap = channel_map(slots)
        assert [(g["tier"], g["total"]) for g in cmap] == [("virtual_channels", 8), ("channels", 12)], cmap
        assert cmap[1]["rows"][0] == {"slot": "A", "code": "", "on": False}, cmap[1]["rows"][0]
        save_slot(slots, "channels", "A", on=False)
        save_slot(slots, "channels", "A", "w-L")            # a spare with no history is REPLACED
        row = project.Project(slots).load()["channels"]
        assert row == [{"code": "w-L", "slot": "A", "tier": "channels", "hidden": False}], row
        save_slot(slots, "channels", "A", on=False)         # a live channel is RENAMED, history kept
        row = project.Project(slots).load()["channels"][0]
        assert row["code"] == "off-out-A" and row["id"] == "w-L" and row["role"] == "unused", row
        for bad in ({"code": ""}, {"code": "off-out-B"}):
            try:
                save_slot(slots, "channels", "B", on=True, **bad)
                raise AssertionError(f"a slot went on with {bad}")
            except IntakeError as exc:
                assert "Nothing was written" in str(exc) or "nothing was written" in str(exc), exc
        # ── round 6: a code MOVES to another slot in one write, identity kept, old slot a spare ──
        moves = os.path.join(root, "moves")
        save(moves, "dsp.vendor", "Audiotec-Fischer")
        save(moves, "dsp.model", "Helix DSP Ultra S")
        save_slot(moves, "channels", "A", "w-L")
        save_slot(moves, "channels", "A", on=False)         # A: off-out-A carrying w-L's history
        save_slot(moves, "channels", "K", "sw")
        save_slot(moves, "channels", "C", on=False)          # C becomes a spare
        move_slot(moves, "channels", "sw", "C")              # the spare on C is replaced
        rows = {c["code"]: c for c in project.Project(moves).load()["channels"]}
        assert rows["sw"]["slot"] == "C" and "previous_names" not in rows["sw"], rows["sw"]
        assert rows["off-out-K"]["hidden"] and rows["off-out-K"]["role"] == "unused", rows
        assert "off-out-C" not in rows, "the spare the channel moved onto is still there"
        try:
            move_slot(moves, "channels", "sw", "A")          # A holds off-out-A with w-L's history
            raise AssertionError("a move overwrote a switched-off channel with history")
        except IntakeError as exc:
            assert "own history" in str(exc), exc
        save(slots, "dsp.tiers_used", ["channels"])
        assert [g["tier"] for g in channel_map(slots)] == ["channels"], "tiers in use do not narrow the map"
        # ── round 4: a processor change replaces the map (confirmed), a new one gets its base ──
        try:
            change_dsp(slots, "Acme", "X8")
            raise AssertionError("a saved map was replaced without confirmation")
        except IntakeError as exc:
            assert "REPLACED" in str(exc) and "nothing was written" in str(exc), exc
        prof = os.path.join(slots, "dsp_profile.json")
        with open(prof, "w", encoding="utf-8") as fh:        # the OLD processor's profile on disk
            json.dump({"dsp_profile": {"name": "Helix DSP Ultra S", "vendor": "Audiotec-Fischer",
                                       "groups": [{"id": "physical_outputs", "label": "Outputs",
                                                   "fields": None, "max_count": 12}]}}, fh)
        done = change_dsp(slots, "Acme", "X8", replace_map=True)
        assert done["replaced"] == 1 and len(done["set_aside"]) == 1, done
        assert not os.path.isfile(prof), "the old processor's profile could still pass the gate"
        d = project.Project(slots).load()
        assert d["dsp"]["previous_maps"][0]["slots"][0]["slot"] == "A", d["dsp"]
        assert "tiers_used" not in d["dsp"] and not [c for c in d["channels"] if c.get("slot")], d
        assert dsp_state(slots)["new"] is True and channel_map(slots) == [], "a map before the base"
        st = save_new_dsp(slots, {"tiers": {"channels": {"count": "4", "letters": True,
                                                         "fields": ["hp", "lp", "ta_ms"]}},
                                  "delay": {"step_ms": "0.02", "max_ms": "10"}, "rate": 48000})
        assert st["groups"][0]["slots"] == ["A", "B", "C", "D"], st
        assert [g["total"] for g in channel_map(slots)] == [4]
        assert new_dsp_answers(slots)["delay"] == {"step_ms": 0.02, "max_ms": 10.0}
        for bad in ({"tiers": {}}, {"tiers": {"channels": {"count": "0"}}},
                    {"tiers": {"channels": {"count": 2, "fields": ["delay"]}}}, {"tiers": {"channels": {}}, "rate": 97000}):
            try:
                save_new_dsp(slots, bad)
                raise AssertionError(f"a bad base went in: {bad}")
            except IntakeError as exc:
                assert "nothing was written" in str(exc), exc
        change_dsp(slots, "Audiotec-Fischer", "Helix DSP Ultra S")
        try:
            save_new_dsp(slots, {"tiers": {"channels": {"count": 2}}})
            raise AssertionError("a known processor's base was asked")
        except IntakeError as exc:
            assert "profile" in str(exc), exc

        # The curve list: NTT's sixteen as NTT spells them, and ours, which is actually bundled.
        assert len(NTT_CURVE_PRESETS) == 16 and "ResoNix 2026" in NTT_CURVE_PRESETS
        assert os.path.isfile(BUNDLED_CURVE_FILE), BUNDLED_CURVE_FILE

        # ── the gate, on a real project: the glossary and the profile are what is missing ────
        g = gate_requirements(root)
        assert g["gate_open"] is False and "dsp_profile.json" in g["missing_files"], g
        assert g["ledger"]["tiers"] is None, "no profile on disk, so no tier list -- not a guess"

    print("selftest OK (intake) — the field table names only real destinations; every capability "
          "question is claimed by a field and quoted, not paraphrased; the gate list is read off "
          "contract.GATE_REQUIRED; enumerations refuse and name the choices; the seat is WHAT THE "
          "PROJECT IS and is written once, a second different one refused with the route out "
          "(S-032); the car refuses three "
          "parts, a slot refuses to go in without its tier, and neither refusal writes anything; "
          "`missing` reports prose as unreadable rather than as a gap; a processor change sets a profile "
          "that cannot be read aside unread and byte for byte, saying where, and the gate list reports "
          "that profile (#136); under another writer's lock set-car and every other writer answer 75 with "
          "one busy line, writing nothing, the knobs and a new processor's base (its set-aside too) are written "
          "under one hold, no writer between two of their writes, a bad AUTOSOUND_LOCK_TIMEOUT_S is exit 2 "
          "making nothing, a refusal on a project folder that is not there makes nothing while set-car makes it, "
          "every other refusal keeps its traceback, and no function loads and saves outside Project.update "
          "(#141).")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        sys.exit(_selftest())
    sys.exit(_main(sys.argv[1:]))
