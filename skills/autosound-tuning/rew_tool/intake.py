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
SUGGESTED_CHANNEL_CODES = ("sw", "sw-f", "sw-r", "w-L", "w-R", "m-L", "m-R", "tw-L", "tw-R", "c", "r")
#: The ledger tiers a channel row names most often (`dsp_profile.ledger_tier`). Suggested, not
#: enumerated: a profile may declare a tier of its own.
SUGGESTED_TIERS = ("channels", "virtual_channels", "inputs")
SUGGESTED_ROLES = ("sub", "woofer", "midbass", "midrange", "tweeter", "fullrange", "unused")
#: Common measurement mics. An open set -- the form offers these and takes what it is told.
SUGGESTED_MICS = ("miniDSP UMIK-1", "miniDSP UMIK-2", "Dayton Audio EMM-6", "Dayton Audio iMM-6")
SUGGESTED_CONSTRAINTS = ("no_door_work", "no_trim_changes", "budget", "time")
#: A closed list with an escape (`other`), so a form can offer checkboxes -- several may apply.
GENRES = ("rock", "pop", "jazz", "classical", "electronic", "hip_hop", "acoustic", "metal", "other")
#: Third-party curves the method names (`voicing-by-ear.md`); none is bundled and none is a default.
SUGGESTED_CURVES = ("harman", "resonix", "jazzi", "audiofrog", "own")


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
        out.append({"vendor": vendor, "model": model, "tiers": tiers})
    return out


def dsp_state(project_dir):
    """What the project's processor is, and whether the skill knows it -- `{"vendor", "model",
    "source", "tiers", "new"}`.

    `source` is where the tier list came from: the project's own `dsp_profile.json`, the bundled
    library on an exact vendor+model match, or the interview draft. `new` is True only when a
    vendor and model are recorded and nothing describes them -- that is when the processor's base
    questions are asked, once (`place="new_dsp"`). None means "not chosen yet".
    """
    data = _read_project(project_dir) or {}
    dsp = data.get("dsp") or {}
    vendor, model = dsp.get("vendor") or "", dsp.get("model") or ""
    out = {"vendor": vendor, "model": model, "source": None, "tiers": [], "new": None}
    own = dsp_profile.profile_path(project_dir)
    if os.path.isfile(own):
        try:
            out.update(source="project", tiers=dsp_profile.tier_keys(dsp_profile.load_profile(own)),
                       new=False)
            return out
        except (OSError, ValueError):
            pass
    if vendor and model:
        bundled = dsp_profile.find_bundled(vendor, model)
        if bundled is not None:
            out.update(source="bundled", tiers=dsp_profile.tier_keys(bundled), new=False)
            return out
        out["new"] = True
    if os.path.isfile(dsp_profile.draft_path(project_dir)):
        try:
            out.update(source="draft",
                       tiers=dsp_profile.tier_keys(dsp_profile.load_profile(dsp_profile.draft_path(project_dir))))
        except (OSError, ValueError):
            pass
    return out


def known_cars(project_dir=None):
    """`[{"make", "model", "generation", "body", "label", "source"}]` -- cars the skill has seen.

    Two sources, and nothing invented: the cabin library (`knowledge/cars/`, one file per body,
    its own heading read by `car_profile`) and the other projects next to this one (a sibling
    directory whose `project.json` records all four parts). There is no car catalogue beyond these;
    a picked car fills the four fields, and an EDITED one is a new car, not a variant of the entry.
    """
    import car_profile

    out, seen = [], set()

    def add(make, model, generation, body, source):
        parts = [str(x or "").strip() for x in (make, model, generation, body)]
        if not all(parts):
            return
        slug = car_profile.body_slug(*parts)
        if slug in seen:
            return
        seen.add(slug)
        out.append({"make": parts[0], "model": parts[1], "generation": parts[2], "body": parts[3],
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
                f"project:{name}")
    for _slug, _path, title in car_profile.list_bundled():
        words = title.split(" — ", 1)[0].split()
        if len(words) == 4 and words[3] in BODIES:
            add(*words, source="library")
    return out


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
              "with two answers — it is what the Pre-session checklist #4 reads, and a preset "
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
       note="This is the REPLY language and only that. The INTERFACE language is a front-end's own "
            "and is never stored here; the language the person TYPES changes neither — he had no "
            "Ukrainian layout on the Windows VM, typed English, and the reply stayed Ukrainian "
            "(S-045). If the front-end reports it, it is ANSWERED, not suggested — and it WINS over "
            "the stored value, because the app is where he set it."),
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
    _f("car.model", "car", "Model (the nameplate — Passat)", required=True,
       writes="project:car.model", ask_with="car_identity"),
    _f("car.generation", "car", "Generation (the model run — B8)", required=True,
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
            "Pre-session checklist #4's whole reason for existing.",
       when="0", derive="the bundled profile on an exact vendor+model match", place="new_dsp"),
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
    _f("channel_map.driver_make", "channel_map", "Driver make", per="channel",
       writes="project:channels[].driver.make",
       when="install", place="equipment"),
    _f("channel_map.driver_model", "channel_map", "Driver model", per="channel",
       writes="project:channels[].driver.model",
       when="install", place="equipment"),
    _f("channel_map.fs_hz", "channel_map", "The driver's Fs", per="channel",
       writes="project:channels[].fs_hz",
       note="Carries provenance: a datasheet number is `source=datasheet` and a later impedance "
            f"sweep upgrades it to `measured` (sources: {', '.join(FACT_SOURCES)}). The protective "
            "HPF is bound to it (>= 1.1 x Fs, >= 24 dB/oct), so an Fs carried in from another "
            "project is not this build's until it is confirmed here (skill #36).",
       when="install", derive="the driver's datasheet, from its make and model", place="equipment"),
    _f("channel_map.position", "channel_map", "Where it sits and where it points", per="channel",
       enum=POSITIONS, writes="project:channels[].position",
       note="Take it from the person or from a measurement — never from a car/DSP profile: "
            "placement varies on the same body.",
       when="1", place="equipment"),
    _f("channel_map.enclosure", "channel_map", "How it is loaded", per="channel", enum=ENCLOSURES,
       writes="project:channels[].enclosure",
       when="1", place="equipment"),
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
    _f("channel_map.hardware_controls", "channel_map",
       "Remote knobs and switches outside the DSP (SubRC / RearRC / a bass control), and where they stand",
       per="control", writes="project:hardware.controls",
       note="Two facts, not one: the POSITION is read off the device, what a step is WORTH is "
            "somebody's opinion (`set-control-mapping`). Without the mapping, a comparison across "
            "positions is refused rather than folded into an offset (RES-007).",
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
       enum=("yes", "no"), lands="the Pre-session checklist (a live check, not a setting)",
       note="Reading is free; FIRING a sweep needs a Pro licence, so a human runs the session "
            "either way.",
       when="0", derive="probed: a GET on localhost:4735"),
    _f("rew.input_clip_checked", "rew", "Has the measurement input been checked for clipping?",
       required=True, enum=("yes", "no"), lands="the Pre-session checklist (`project-intake.md` §3.8)",
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
       required=True, enum=MODES, lands="`autosound_context.md` + a recorded decision",
       note="An INTENT, orthogonal to the capability level. Both modes read the current DSP state "
            "into the ledger first.",
       default="new_tune", derive="the method has one way in -- a tune from scratch (`phase_-1_intake.md`)"),
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
       note="⛔ Chosen TOGETHER with the person — there is no default. Narrow by genres and taste to "
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
            except (OSError, ValueError) as exc:
                out["ledger"]["tiers_error"] = str(exc)
        report = contract.check_project(project_dir, skip_rew=True)
        out["missing_files"] = [f["file"] for f in report["files"]
                                if not f["exists"] and f["file"] in contract.GATE_REQUIRED]
        out["gate_open"] = not out["missing_files"]
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

    Load-modify-save with `Project`, never a JSON dump: that writer validates, writes atomically,
    bumps `project_rev`, and refuses to treat an unreadable file as an empty project.

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
    data = handle.load()
    _set_path(data, writes.split(":", 1)[1], value)
    handle.save(data)
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
    handle = project.Project(project_dir)
    data = handle.load()
    car = dict(data.get("car") or {})
    car.update(parts)
    if year is not None:
        car["year"] = year
    data["car"] = {k: v for k, v in car.items() if v not in ("", None)}
    handle.save(data)
    return data["car"]


def save_channel(project_dir, code, source=None, **row):
    """One channel row, through `Project.set_channel` — with the intake's couple enforced.

    `slot` without `tier` is refused: slot letters repeat across tiers (a Helix: virtual A–H,
    outputs B–K), so `F` is a legal address in both and a guess files a spare output among the
    virtual channels (SCR-042). Enumerated fields are checked against the table, and `fs_hz` keeps
    its provenance through `--source`.
    """
    known = {f["id"].split(".", 1)[1]: f for f in FIELDS if f["per"] == "channel"}
    for key, value in row.items():
        f = known.get(key)
        if f is not None and f["enum"]:
            check_value(f["id"], value)
    if "slot" in row and not row.get("tier"):
        existing = next((c for c in (_read_project(project_dir) or {}).get("channels", [])
                         if c.get("code") == code), {})
        if not existing.get("tier"):
            raise IntakeError(
                f"channel {code!r}: a slot needs its tier in the same breath — slot letters repeat "
                "across tiers, so this one is a legal address in more than one of them. Pass "
                "tier=channels for a physical output (`dsp_profile.ledger_tier`). Nothing was written")
    row = {k: (True if v == "yes" else False if v == "no" else v)
           if k == "hidden" else v for k, v in row.items()}
    # Provenance goes on the fields the schema keeps as facts (`fs_hz` today), wrapped here the
    # way `project.py`'s own CLI wraps them -- `set_channel` takes the value it is handed.
    for key in project.CHANNEL_FACT_FIELDS:
        if source and key in row and not project.is_fact(row[key]):
            row[key] = project.fact(row[key], source=source)
    handle = project.Project(project_dir)
    handle.set_channel(code, **row)
    return handle.resolve_channel(code)


def save_amp(project_dir, index=None, **row):
    """One amplifier: appended when `index` is None, replaced in place when it names an existing one."""
    known = {f["id"].split(".", 1)[1] for f in FIELDS if f["per"] == "amp"}
    unknown = [k for k in row if k not in known]
    if unknown:
        raise IntakeError(f"amps take {', '.join(sorted(known))}; got {', '.join(unknown)}")
    handle = project.Project(project_dir)
    data = handle.load()
    amps = list(data.get("amps") or [])
    if index is None:
        amps.append(dict(row))
        index = len(amps) - 1
    else:
        if not 0 <= index < len(amps):
            raise IntakeError(f"no amps[{index}] — this project has {len(amps)}")
        amps[index] = dict(amps[index], **row)
    data["amps"] = amps
    handle.save(data)
    return amps[index]


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
                         if data["missing_files"] else ""))
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
def _selftest():
    import tempfile

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
          "`missing` reports prose as unreadable rather than as a gap.")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        sys.exit(_selftest())
    sys.exit(_main(sys.argv[1:]))
