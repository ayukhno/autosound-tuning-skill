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
#: A physical loopback or none. An acoustic "loopback" through a USB mic does NOT qualify
#: (`virtual-first.md`), so it is not a third choice here.
LOOPBACKS = ("physical", "none")
PURPOSES = ("competition", "enjoyment", "both")
#: Formats judge differently and some techniques are mutually exclusive, so several = several
#: presets, not one tune (`competition.md`). Multi-select.
FORMATS = ("EMMA", "AYA", "CARMusic")
#: ⚠️ THE field this ticket was opened over. Three choices, one control: asked as two turns it was
#: answered "driver only" and corrected five minutes later, and the decision already recorded had
#: to be voided (`tcc:docs/SESSION-ANALYSIS-2026-09-14.md` §4a).
REFERENCE_SEATS = ("driver", "driver_and_passenger", "all_seats")
STAGE_PRIORITIES = ("width", "depth", "height", "center_focus", "envelopment", "front_only")
LOVES = ("bass", "vocals", "winds_strings", "acoustic", "electronica")
LOUDNESS = ("loud", "moderate")
#: What the person can actually PLAY — Phase 4 proposes only from this (`test-tracks.md`).
TRACK_LIBRARIES = ("carmus", "chesky", "emma_aya", "streaming", "none")
TONE = ("warm", "neutral", "bright")
BASS = ("bass_heavy", "neutral")
PRESENTATION = ("forward", "neutral", "laid_back")
CHARACTER = ("accuracy", "balanced", "fun")
LANGUAGES = ("en", "uk", "de", "pl")
#: Provenance and rates come from the modules that own them — referenced, never retyped.
FACT_SOURCES = project.FACT_SOURCES
PLAUSIBLE_RATES_HZ = dsp_profile.PLAUSIBLE_RATES_HZ

#: The codes the method SUGGESTS (`naming-and-structure.md`). Not an enumeration: the glossary is
#: agreed with the person and written down (§0.5 step 5), and a car with two subs or no centre
#: names its own set. A form offers these and takes what it is told.
SUGGESTED_CHANNEL_CODES = ("sw", "sw-f", "sw-r", "w-L", "w-R", "m-L", "m-R", "tw-L", "tw-R", "c", "r")


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
}


# ── the field table ───────────────────────────────────────────────────────────
def _f(id, group, ask, *, required=False, enum=None, multi=False, writes=None, lands=None,
       ask_with=None, per=None, settled_by=None, checklist=None, note=None):
    """One row of the table. `writes` is the MACHINE destination and it is the load-bearing field:

    * `project:<dotted path>`       -> `project.json`, through this module's `save()`
    * `project:channels[].<field>`  -> one channel row, through `save_channel()` (`per="channel"`)
    * `project:amps[].<field>`      -> one amplifier, through `save_amp()` (`per="amp"`)
    * `dsp_profile.draft:<path>`    -> the profile's OWN writer (`dsp_profile.set_field`)
    * `glossary:`                   -> the agreed names (`glossary.json` / `project.json.glossary`)
    * `None`                        -> no machine home yet; `lands` says where the answer does go.
    """
    return {"id": id, "group": group, "ask": ask, "required": bool(required),
            "enum": tuple(enum) if enum else None, "multi": bool(multi), "writes": writes,
            "lands": lands, "ask_with": ask_with, "per": per, "settled_by": settled_by,
            "checklist": checklist, "note": note}


FIELDS = (
    # ── project: the front-end's own half (`project-intake.md` §0) ────────────────────────────
    _f("project.language", "project", "Which language — EN / UK / DE / PL?", required=True,
       enum=LANGUAGES, settled_by="front_end", lands="a recorded decision (-1.1) + every project file",
       note="If the front-end reports it, it is ANSWERED, not suggested — and the step is closed "
            "with what it said, or the next session asks again."),
    _f("project.reviewer_channel", "project", "Which reviewer channel, and does it answer?",
       required=True, settled_by="front_end",
       lands="`rew_analitic/reviewer-check.md` (a live doctor run) + a recorded decision (-1.2)",
       note="Closed by an ANSWER, not by a setting: 'configured' resolves to nothing and the gate "
            "refuses it. An unreachable channel is blocked with its reason, not marked done."),
    _f("project.dir", "project", "Where does this project live?", required=True,
       settled_by="front_end", writes="project:paths.project_dir"),

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
       note="The listener's side sets the DIRECTION of the L/R asymmetry."),
    _f("car.year", "car", "Year (optional — it describes this car and classifies nothing)",
       writes="project:car.year"),

    # ── dsp: the processor (§1.3 + `project-intake.md` §4) ────────────────────────────────────
    _f("dsp.vendor", "dsp", "DSP vendor", required=True, writes="project:dsp.vendor",
       ask_with="dsp_identity"),
    _f("dsp.model", "dsp", "DSP model", required=True, writes="project:dsp.model",
       ask_with="dsp_identity",
       note="Before asking anything below: `dsp_profile.py find-bundled <vendor> <model>` and "
            "`knowledge/dsp/<vendor>-<model>.md` may already answer the whole checklist."),
    _f("dsp.readable", "dsp", "Is the DSP's state readable (a dump, a screen-read, a file export)?",
       required=True, enum=("yes", "no"), ask_with="capability",
       lands="the capability level in `autosound_context.md` + a recorded decision"),
    _f("dsp.per_channel_measurable", "dsp", "Can each output be measured on its own (solo)?",
       required=True, enum=("yes", "no"), ask_with="capability",
       lands="the capability level in `autosound_context.md` + a recorded decision",
       note="This is the hinge, not readability: no per-channel access is Level 3, where joint and "
            "phase surgery is impossible and the ceiling is recorded honestly."),
    _f("dsp.capability_level", "dsp", "Which level does that make it — 1 full / 2 black-box / 3 sum only?",
       required=True, enum=CAPABILITY_LEVELS, ask_with="capability",
       lands="`autosound_context.md` + a recorded decision",
       note="Decided BY the two answers above, not asked instead of them."),
    _f("dsp.processing_rate_hz", "dsp", "The DSP's own processing rate", enum=PLAUSIBLE_RATES_HZ,
       writes="project:dsp.dsp_processing_rate_hz",
       note="The processing rate, not the capture rate — two rates, one name each. The capture "
            "rate is `rew.capture_rate_hz`."),
    _f("dsp.tiers", "dsp", dsp_profile.CAPABILITY_CHECKLIST[0], required=True, checklist=0,
       writes="dsp_profile.draft:groups",
       note="No virtual layer -> voicing is linked L=R on the output EQ, and voicing presets cost "
            "more (`diagnostic-techniques.md §6`)."),
    _f("dsp.max_count", "dsp", dsp_profile.CAPABILITY_CHECKLIST[1], required=True, checklist=1,
       per="tier", writes="dsp_profile.draft:groups.<i>.max_count",
       note="Left null, a 12-output processor with ten in use reads 10/10 and its spare slots are "
            "invisible."),
    _f("dsp.eq", "dsp", dsp_profile.CAPABILITY_CHECKLIST[2], required=True, checklist=2,
       per="tier", writes="dsp_profile.draft:groups.<i>.eq",
       note="The band vocabulary is the profile's own (`dsp_profile.FIELD_VOCABULARY`); file "
            "import + format decides whether the REW->DSP path is a file or the copy-paste assistant."),
    _f("dsp.crossovers", "dsp", dsp_profile.CAPABILITY_CHECKLIST[3], required=True, checklist=3,
       per="tier", writes="dsp_profile.draft:groups.<i>.crossover_filters",
       note="Families are `dsp_math.MODELLABLE_FAMILIES` (LR/BW/BE) — enterable on the device is "
            "what is being asked, modellable here is what the profile then marks."),
    _f("dsp.delays", "dsp", dsp_profile.CAPABILITY_CHECKLIST[4], required=True, checklist=4,
       per="tier", writes="dsp_profile.draft:groups.<i>.fields",
       note="Step and limits decide TA accuracy; an all-pass decides the phase method."),
    _f("dsp.presets", "dsp", dsp_profile.CAPABILITY_CHECKLIST[5], required=True, checklist=5,
       writes="dsp_profile.draft:presets",
       note="What resets on a switch — the INPUT above all: a preset silently resetting it is "
            "Pre-session checklist #4's whole reason for existing."),
    _f("dsp.measurement_input", "dsp", dsp_profile.CAPABILITY_CHECKLIST[6], required=True, checklist=6,
       writes="project:source.measurement_input", ask_with="inputs"),

    # ── channel_map: what is wired where (§1.5–§1.7, §5) ──────────────────────────────────────
    _f("channel_map.glossary_agreed", "channel_map",
       "Are the channel codes and the title grammar agreed AND written down?", required=True,
       writes="glossary:",
       note="⛔ The gate before any measurement (§0.5 step 5). Agreed-but-not-written is the "
            "recurring slip: the history it produces is unusable."),
    _f("channel_map.code", "channel_map", "The channel's code", required=True, per="channel",
       writes="project:channels[].code",
       note=f"Suggested set: {', '.join(SUGGESTED_CHANNEL_CODES)} — the glossary is agreed, not fixed."),
    _f("channel_map.slot", "channel_map", "Which slot on the processor", required=True, per="channel",
       writes="project:channels[].slot", ask_with="channel_slot"),
    _f("channel_map.tier", "channel_map", "Which tier that slot belongs to", required=True,
       per="channel", writes="project:channels[].tier", ask_with="channel_slot",
       note="The LEDGER key (`dsp_profile.ledger_tier`): `channels` for a physical output, "
            "`virtual_channels`/`inputs`/... for the rest. `physical_outputs` is refused."),
    _f("channel_map.role", "channel_map", "What it drives (woofer / midrange / tweeter / sub / ...)",
       per="channel", writes="project:channels[].role",
       note="`role: unused` for an empty slot — and write the row anyway: it is the only record "
            "that the slot exists (SCR-042)."),
    _f("channel_map.descr", "channel_map", "How the DSP's own software labels it", per="channel",
       writes="project:channels[].descr"),
    _f("channel_map.driver_make", "channel_map", "Driver make", per="channel",
       writes="project:channels[].driver.make"),
    _f("channel_map.driver_model", "channel_map", "Driver model", per="channel",
       writes="project:channels[].driver.model"),
    _f("channel_map.fs_hz", "channel_map", "The driver's Fs", per="channel",
       writes="project:channels[].fs_hz",
       note="Carries provenance: a datasheet number is `source=datasheet` and a later impedance "
            f"sweep upgrades it to `measured` (sources: {', '.join(FACT_SOURCES)}). The protective "
            "HPF is bound to it (>= 1.1 x Fs, >= 24 dB/oct), so an Fs carried in from another "
            "project is not this build's until it is confirmed here (skill #36)."),
    _f("channel_map.position", "channel_map", "Where it sits and where it points", per="channel",
       enum=POSITIONS, writes="project:channels[].position",
       note="Take it from the person or from a measurement — never from a car/DSP profile: "
            "placement varies on the same body."),
    _f("channel_map.enclosure", "channel_map", "How it is loaded", per="channel", enum=ENCLOSURES,
       writes="project:channels[].enclosure"),
    _f("channel_map.condition", "channel_map", "New, or broken in?", per="channel", enum=CONDITIONS,
       writes="project:channels[].condition",
       note="New drivers get a rough tune, a break-in and only then a precise one "
            "(`project-intake.md` §3.6)."),
    _f("channel_map.hidden", "channel_map", "Is the slot empty (nothing wired to it)?", per="channel",
       enum=("yes", "no"), writes="project:channels[].hidden"),
    _f("channel_map.routing", "channel_map", "Which outputs does each VIRTUAL channel feed?",
       per="virtual_channel", writes="project:hardware.virtual_routing",
       note="Never inferable from names — `VFL` looking like 'virtual front left' is a convention, "
            "not a wiring diagram (RES-007). Required where the DSP has a virtual tier."),
    _f("channel_map.hardware_controls", "channel_map",
       "Remote knobs and switches outside the DSP (SubRC / RearRC / a bass control), and where they stand",
       per="control", writes="project:hardware.controls",
       note="Two facts, not one: the POSITION is read off the device, what a step is WORTH is "
            "somebody's opinion (`set-control-mapping`). Without the mapping, a comparison across "
            "positions is refused rather than folded into an offset (RES-007)."),

    # ── measurement_chain: how the signal gets in (§1.2, §1.4) ────────────────────────────────
    _f("source.kind", "measurement_chain", "What plays the music (head unit / streamer / phone / ...)",
       required=True, enum=SOURCE_KINDS, writes="project:source.kind"),
    _f("source.connection", "measurement_chain", "How the signal enters the DSP", required=True,
       enum=CONNECTIONS, writes="project:source.connection"),
    _f("source.listening_input", "measurement_chain", "Which input is for listening", required=True,
       writes="project:source.listening_input", ask_with="inputs"),
    _f("source.measurement_input", "measurement_chain",
       "Which input carries the measurement signal", required=True,
       writes="project:source.measurement_input", ask_with="inputs"),
    _f("amps.make", "measurement_chain", "Amplifier make", per="amp", writes="project:amps[].make"),
    _f("amps.model", "measurement_chain", "Amplifier model", per="amp", writes="project:amps[].model"),
    _f("amps.channels", "measurement_chain", "Which channels it drives", per="amp",
       writes="project:amps[].channels"),
    _f("amps.gain_db", "measurement_chain", "Its input sensitivity / gain setting", per="amp",
       writes="project:amps[].gain_db",
       note="Gain staging is verified in `project-intake.md` §3.4, not decided here; this records "
            "where it was left."),

    # ── rew: the rig (§0.5 step 4, §1.8) ──────────────────────────────────────────────────────
    _f("rew.mic_model", "rew", "Measurement mic", required=True, writes="project:mic.model"),
    _f("rew.mic_cal_0", "rew", "Its 0° calibration file", required=True,
       writes="project:mic.calibration_file"),
    _f("rew.mic_cal_90", "rew", "Its 90° calibration file", writes="project:mic.calibration_file_90"),
    _f("rew.interface", "rew", "Audio interface", writes="project:measurement.interface"),
    _f("rew.loopback", "rew", "Is a PHYSICAL loopback wired?", required=True, enum=LOOPBACKS,
       writes="project:measurement.loopback",
       note="Without one, phase and timing reads are unreliable — lean on summation and the ear. "
            "An acoustic loopback through a USB mic does not qualify, so virtual-first is out."),
    _f("rew.capture_rate_hz", "rew", "The capture sample rate", required=True, enum=PLAUSIBLE_RATES_HZ,
       writes="project:measurement.sample_rate_hz",
       note="The DSP's native rate where possible. This is the CAPTURE rate and keeps its own name; "
            "the processing rate is `dsp.processing_rate_hz`."),
    _f("rew.api_reachable", "rew", "Does REW's API answer at localhost:4735?", required=True,
       enum=("yes", "no"), lands="the Pre-session checklist (a live check, not a setting)",
       note="Reading is free; FIRING a sweep needs a Pro licence, so a human runs the session "
            "either way."),
    _f("rew.input_clip_checked", "rew", "Has the measurement input been checked for clipping?",
       required=True, enum=("yes", "no"), lands="the Pre-session checklist (`project-intake.md` §3.8)"),

    # ── goal: what the tune is FOR (§2.1–§2.4, §2.7) ──────────────────────────────────────────
    _f("goal.purpose", "goal", "Competition, for yourself, or both?", required=True, enum=PURPOSES,
       ask_with="purpose", lands="`autosound_context.md` (Engineering Profile) + a recorded decision"),
    _f("goal.formats", "goal", "Which format(s) — EMMA / AYA / CARMusic?", enum=FORMATS, multi=True,
       ask_with="purpose", lands="`autosound_context.md` + a recorded decision",
       note="Required once `goal.purpose` includes competition. Several formats = separate presets, "
            "not one tune: crossfeed stabilises an EMMA stage and is never used for AYA."),
    _f("goal.reference_seat", "goal", "Who is the tune for — the driver / the front passenger too / all seats?",
       required=True, enum=REFERENCE_SEATS, ask_with="seat",
       lands="`autosound_context.md` (Engineering Profile) + a recorded decision",
       note="A GOAL, not a detail: a single seat can be fully centred and imaged; all seats is a "
            "deliberate compromise with no perfect phantom centre for anyone. It decides the "
            "centering/TA strategy, so it is settled up front."),
    _f("goal.mode", "goal", "A tune from scratch, improving an existing one, or a light touch?",
       required=True, enum=MODES, lands="`autosound_context.md` + a recorded decision",
       note="An INTENT, orthogonal to the capability level. Both modes read the current DSP state "
            "into the ledger first."),
    _f("goal.design_path", "goal", "Virtual-first at the desk, or iterative?", enum=DESIGN_PATHS,
       lands="`autosound_context.md` + a recorded decision",
       note="Virtual-first needs all three: level 1, a loopback on one clock, a hardware-verified "
            "filter model. Miss one and only the DESK half degrades — the Phase-0 capture session "
            "is run the same way regardless."),
    _f("goal.stage_priorities", "goal", "What stage are we building (you cannot maximise everything)?",
       enum=STAGE_PRIORITIES, multi=True, lands="`autosound_context.md` (Engineering Profile)",
       note="State the physical ceilings honestly: depth is limited by the mid's geometry, "
            "envelopment needs a rear."),
    _f("goal.constraints", "goal", "Anything that must NOT be touched (doors, trim, budget, time)?",
       lands="`autosound_context.md` (Engineering Profile) as a hard constraint"),
    _f("goal.wishes", "goal", "Anything else you want from this system — in your own words?",
       lands="`autosound_context.md` as an explicit project goal",
       note="⚠️ The branches above are the COMMON ones, not a closed list. A free-form wish is "
            "captured in the person's words and then MAPPED to where it lands in the tune; one "
            "that fits no box is recorded as a goal on its own terms (§2.7)."),

    # ── target_curve: the seed and the taste (§2.3, §2.5, §2.6) ───────────────────────────────
    _f("target_curve.candidate", "target_curve", "Which target curve do we start from?", required=True,
       lands="`rew_analitic/target-curves/<name>/` + `autosound_context.md` §4",
       note="⛔ Chosen TOGETHER with the person — there is no default. Narrow by genres and taste to "
            "2–3 candidates (`voicing-by-ear.md`). It is SEEDED here and finalised after the Phase-0 "
            "baseline: a curve is a start and a shape, not a finish and not a level."),
    _f("target_curve.genres", "target_curve", "What do you listen to?",
       lands="`preference-profile.md` (applied in Phase 5)"),
    _f("target_curve.loves_most", "target_curve", "What do you love most in the sound?", enum=LOVES,
       multi=True, lands="`preference-profile.md`"),
    _f("target_curve.loudness", "target_curve", "How loud do you usually listen?", enum=LOUDNESS,
       lands="`preference-profile.md`",
       note="Decides how much equal-loudness weighting the voicing carries (`staging-depth.md §3`)."),
    _f("target_curve.reference_tracks", "target_curve", "3–5 reference tracks you know well",
       lands="`preference-profile.md`"),
    _f("target_curve.track_library", "target_curve", "Which test-track library do you have?",
       enum=TRACK_LIBRARIES, lands="`preference-profile.md`",
       note="Phase 4 proposes only from what you can actually play (`test-tracks.md`)."),
    _f("target_curve.tone", "target_curve", "Warm or bright?", enum=TONE, lands="`preference-profile.md`"),
    _f("target_curve.bass", "target_curve", "Bass-heavy or neutral?", enum=BASS,
       lands="`preference-profile.md`"),
    _f("target_curve.presentation", "target_curve", "Forward or laid-back?", enum=PRESENTATION,
       lands="`preference-profile.md`"),
    _f("target_curve.character", "target_curve", "Accuracy or fun?", enum=CHARACTER,
       lands="`preference-profile.md`"),
)

_BY_ID = {f["id"]: f for f in FIELDS}


# ── reading the table ─────────────────────────────────────────────────────────
def groups():
    """`[{"id", "what"}]` — the pages a form would render."""
    return [{"id": g, "what": what} for g, what in GROUPS]


def fields(group=None, required_only=False, per=None):
    """The table, filtered. `per=None` is every field; `per="channel"` only the repeated ones."""
    out = []
    for f in FIELDS:
        if group is not None and f["group"] != group:
            continue
        if required_only and not f["required"]:
            continue
        if per is not None and f["per"] != per:
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
               "ask": f["ask"], "enum": f["enum"], "lands": f["lands"] or f["writes"]}
        if state is None:
            out["not_machine_readable"].append(row)
        elif state:
            out["answered"].append(row)
        else:
            out["missing"].append(row)
    out["required_missing"] = [r["id"] for r in out["missing"] if r["required"]]
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

  fields [--group G] [--required] [--json]   the intake's fields: id, question, enum, where it lands
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
        print(f" {mark} {r['id']:<34} {r['ask']}{enum}")
        if where:
            print(f"     -> {where}" + (f"   (per {r['per']})" if r["per"] else ""))


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    as_json = "--json" in rest

    if cmd == "fields":
        rows = fields(group=_flag(rest, "--group"), required_only="--required" in rest)
        if as_json:
            print(json.dumps({"groups": groups(), "fields": rows}, ensure_ascii=False, indent=2))
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
                  f"  (required: {len(data['required_missing'])})")
            print(f"  not machine-readable {len(data['not_machine_readable'])}"
                  f"  — prose and recorded decisions\n")
            for r in data["missing"]:
                if r["required"]:
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
            assert top in skeleton or top == "measurement", f"{f['id']} writes to unknown key {top!r}"
        # Every field with no machine home says where the answer DOES go. "Nowhere" is not an
        # answer a form can act on, and prose that nobody names is prose nobody writes.
        if f["writes"] is None:
            assert f["lands"], f"{f['id']} has no writes and no lands"
        if f["ask_with"]:
            assert f["ask_with"] in COUPLINGS, f
    for c in couplings():
        assert len(c["fields"]) >= 2, f"a couple of one is not a couple: {c['id']}"
        assert c["why"].strip(), c

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
        save(root, "rew.loopback", "physical")
        save(root, "rew.capture_rate_hz", 48000)
        data = project.Project(root).load()
        assert data["source"]["measurement_input"] == "Coax 2", data["source"]
        assert data["measurement"]["loopback"] == "physical", data["measurement"]
        try:
            save(root, "rew.loopback", "acoustic")
            raise AssertionError("an acoustic loopback passed as a physical one")
        except IntakeError as exc:
            assert "physical" in str(exc), exc

        # ── a field that is not this writer's says WHOSE it is ───────────────────────────────
        for fid, value, expect in (("channel_map.code", "w-R", "save_channel"),
                                   ("amps.make", "Helix", "save_amp"),
                                   ("dsp.eq", "10 PK bands", "dsp_profile.set_field"),
                                   ("goal.reference_seat", "driver", "autosound_context"),
                                   ("channel_map.glossary_agreed", "yes", "glossary.json")):
            try:
                save(root, fid, value)
                raise AssertionError(f"{fid} was written by the wrong writer")
            except IntakeError as exc:
                assert expect in str(exc), (fid, exc)

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
        assert "rew.mic_model" in before["required_missing"], before["required_missing"]
        assert "goal.reference_seat" in [r["id"] for r in before["not_machine_readable"]], before
        save(root, "rew.mic_model", "UMIK-1")
        after = missing(root)
        assert "rew.mic_model" not in after["required_missing"]
        assert len(after["required_missing"]) == len(before["required_missing"]) - 1, (
            before["required_missing"], after["required_missing"])

        # ── the gate, on a real project: the glossary and the profile are what is missing ────
        g = gate_requirements(root)
        assert g["gate_open"] is False and "dsp_profile.json" in g["missing_files"], g
        assert g["ledger"]["tiers"] is None, "no profile on disk, so no tier list -- not a guess"

    print("selftest OK (intake) — the field table names only real destinations; every capability "
          "question is claimed by a field and quoted, not paraphrased; the gate list is read off "
          "contract.GATE_REQUIRED; enumerations refuse and name the choices; the car refuses three "
          "parts, a slot refuses to go in without its tier, and neither refusal writes anything; "
          "`missing` reports prose as unreadable rather than as a gap.")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        sys.exit(_selftest())
    sys.exit(_main(sys.argv[1:]))
