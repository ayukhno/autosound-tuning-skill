# Intake simplified: ask what the next step needs (2026-09-22)

**Asked for by:** the Arbiter, 2026-09-22: "the Intake has far too much in it; the Antigravity session
shows you do not have to take every small detail at once. Simplify it, and offer choices wherever possible."
**Lesson applied:** `docs/REVIEW-2026-09-22-antigravity-session.md`. The fast session asked for what the
next step needed and picked up the rest when it mattered (it only needed rear geometry once the rear
was being tuned). The slow sessions asked for everything up front.

## The rule

Up front, Phase −1 asks only what **starting to measure** needs: whatever makes the Phase-0 gate pass
(`contract.py check --gate`: `project.json`, `dsp_profile.json`, the glossary) and whatever names the
channels. Every other field stays in `intake.FIELDS`, so nothing is lost, and names the step that
first needs it (`when`). Three more attributes keep the up-front set small:

| attribute | meaning |
|---|---|
| `when` | `now` · `install` (Phase −1 step 6) · `0` · `1` · `2` · `4` · `5` (`intake.WHEN`) |
| `derive` | a tool, a probe or the bundled DSP profile answers it, so the person is not asked |
| `default` | pre-selected on the form ("change it if yours differs"). It is written only when confirmed, never stored silently |
| `suggest` | choices for an open set: a datalist with free text still accepted. `enum` is still the closed set that `check_value` enforces |

The form (`intake_form.py`) shows the `now` set as an open page, with a choice wherever one exists
(radio buttons for up to 6 options, a list for more, checkboxes for multi-select, a datalist for
open sets). Below that come the folded sections: "the tool answers these", then one per later step
("asked later: Phase 1, crossovers, levels, delays"). A key written by two fields
(`dsp.measurement_input` and `source.measurement_input`) is shown as one question.

## Counts (empty project, `--lang uk`)

| | before | after |
|---|---|---|
| fields in the table | 71 | 71 (none dropped) |
| shown as questions to answer now | 68 (all groups, as tabs; only the 3 probes were marked) | **21** |
| of those, a choice (enum/radio or suggestion list) | 27 of 68 | **14 of 21** |
| answered by a tool, probe or bundled profile | 3 | 17 (8 of them now, 9 in later steps) |
| pre-selected defaults | 0 | 15 |
| folded under "asked later" | 0 | 42 |

Across the whole table, 34 of the 54 fields a person still answers are choices. Of the 21 up-front
fields, 7 stay free text: make, model, generation, year (optional), the slot letter, the 0° cal
file, and the glossary (a note, because the glossary has its own writer).

## Gate: nothing moved in code, one prose item moved and flagged

- **`contract.py check --gate` is unchanged.** It checks files. Every field that feeds those files
  (`channel_map.glossary_agreed` → glossary; `dsp.tiers` → profile groups) stays `now`. A new
  selftest in `intake.py` fails if one of them is ever deferred. The profile's per-tier `fields`,
  EQ, crossover and delay details can stay null and still validate (`dsp_profile._validate_group`),
  so moving them to Phase 1 and 2 does not shut the gate.
- **Flagged and moved: the target-curve seed and the preference profile.** Phase −1's prose quality gate
  listed "a candidate target curve seeded" and "`preference-profile.md` created". Nothing in the
  Phase-0 baseline capture reads either. The curve is already finalised after the baseline (§2.6),
  Phase 0 is "Baseline & *Target Preparation*", and the machine gate that holds the target is
  `enter-phase 1`, which refuses without `process target`. So the seed and the taste interview now
  belong to Phase 0 after the baseline, and `phase_-1_intake.md`'s gate line says so. **This is the
  one change to the method's order, and the Arbiter may revert it.** §2's closing line, "goals →
  equipment → baseline → finalise curve", still describes his picture. Only the timing of the taste
  questions moved.
- **Not given a default: the reference seat.** It decides where the mic stands for the first capture,
  so it stays `now`. It is written once (S-032), so a pre-selected answer that gets saved without
  thought could not be undone.

## Field decisions

KEEP = asked now · DEFAULT = asked now, pre-selected · DERIVE = not asked (tool/probe/profile) ·
DEFER(x) = asked at step x. Nothing is DROPPED: every field has a reader (code or the session's prose).

| field | decision | reason |
|---|---|---|
| project.language | DEFAULT (page language) | settled by the front-end; the page's language is the obvious answer |
| project.reviewer_channel | DERIVE | closed by a live doctor run, not by a person's word |
| project.dir | DERIVE | the directory the form was opened for |
| car.make / model / generation | KEEP | cabin identity (SCR-043); the car library is matched on it |
| car.body | KEEP (choice) | the part that gets skipped; room gain differs |
| car.drive_side | DEFAULT LHD | one control with the seat; sets the L/R direction |
| car.year | KEEP, optional | one box in the car control; classifies nothing |
| dsp.vendor / dsp.model | KEEP (list of bundled profiles + free text) | the bundled profile answers the whole checklist on an exact match |
| dsp.readable | DERIVE (probe) | a dump either works or it does not |
| dsp.per_channel_measurable | DEFAULT yes | Phase 0 measures every driver solo, so it is needed now |
| dsp.capability_level | DERIVE | follows from the two answers above |
| dsp.processing_rate_hz | DERIVE / DEFER(1) | bundled profile; the desk maths reads it |
| dsp.tiers, dsp.max_count | DERIVE (now) | the gate needs groups; the bundled profile has them, the session asks only when none matches |
| dsp.eq | DERIVE / DEFER(2) | first used in EQ |
| dsp.crossovers, dsp.delays | DERIVE / DEFER(1) | first used in Phase 1 |
| dsp.presets | DERIVE / DEFER(0) | the pre-session checklist (the input reset) reads it |
| dsp.measurement_input | DEFER(0) | same key as `source.measurement_input`; shown once |
| channel_map.glossary_agreed | DEFAULT (suggested codes) | ⛔ measure only after naming; needed by the gate |
| channel_map.code | KEEP (suggested codes) | names every capture |
| channel_map.slot | KEEP | the ledger's address |
| channel_map.tier | DEFAULT channels (suggested tiers) | slot letters repeat across tiers (SCR-042) |
| channel_map.hidden | DEFAULT no | empty slots still get a row |
| channel_map.role | DERIVE | follows from the code prefix |
| channel_map.descr | DERIVE / DEFER(0) | read off the DSP software when its state is imported |
| channel_map.driver_make / driver_model | DEFER(install) | fragile drivers' protective HPF is set at install verification |
| channel_map.fs_hz | DERIVE (datasheet) / DEFER(install) | the HPF ≥ 1.1 × Fs rule applies at install verification |
| channel_map.condition | DEFER(install), DEFAULT broken_in | break-in is an install-verification step (§3.6) |
| channel_map.position, enclosure, routing | DEFER(1) | time alignment, crossovers and the virtual routing come first in Phase 1 |
| channel_map.hardware_controls | DEFER(0) | recorded on the capture round (`capture-knobs`) |
| source.kind, connection, listening_input, measurement_input | DEFER(0) | pre-session checklist #4, at the car; inputs get suggestions |
| amps.make / model / channels / gain_db | DEFER(install) | gain staging is verified there |
| rew.mic_model | KEEP (common mics listed) | needed to measure |
| rew.mic_cal_0 | KEEP | needed to measure |
| rew.mic_cal_90, rew.interface | DEFER(0) | capture set-up; the usual USB mic needs neither |
| rew.loopback | DEFAULT none | a real fork, but most rigs are a USB mic with no loopback |
| rew.capture_rate_hz | DEFAULT 48000 | change it only if the DSP's native rate differs |
| rew.api_reachable | DERIVE (probe) | a GET on localhost:4735 |
| rew.input_clip_checked | DERIVE (probe) / DEFER(install) | checked at the capture set-up (§3.8) |
| goal.reference_seat | KEEP (no default) | decides the mic position; written once (S-032) |
| goal.mode | DEFAULT new_tune | the method has one way in (from scratch) |
| goal.purpose (DEFAULT enjoyment), goal.formats | DEFER(0) | shape the target and presets, not the raw baseline |
| goal.design_path | DERIVE / DEFER(1) | follows from level 1, a loopback and a verified filter model |
| goal.constraints | DEFER(1), suggestions | matters the first time a physical change is proposed |
| goal.stage_priorities, goal.wishes | DEFER(4) | listening decides them |
| target_curve.candidate (suggestions), genres (suggestions), loves_most | DEFER(0) | chosen with the baseline in hand; never a default |
| target_curve.reference_tracks, track_library | DEFER(4) | Phase 4 proposes tracks only from what the person can play |
| target_curve.loudness, tone, bass, presentation, character | DEFER(5), DEFAULT neutral/moderate/balanced | pure taste, applied in Phase 5; the four axes are one couple (`taste`) |

## Where it lives

- `rew_tool/intake.py`: `WHEN` and the `when`/`default`/`suggest`/`derive` attributes, `fields(when=...)`,
  `fields --now`, and `missing()`'s new `required_missing_now` (`required_missing` keeps its old meaning).
  The new `taste` couple. Selftests: every `when` is known, every default passes its field's own enum,
  gate-feeding fields stay `now`, and fewer than half the fields are asked up front.
- `rew_tool/intake_form.py`: the page as described above. Selftests: the up-front section holds the
  mic, the seat and the channel codes and not the taste, the positions, the amps or the probes; the
  seat and the drive side are one control; a default is pre-selected and not stored.
- `rew_tool/intake_i18n/uk.json`: the step names, the new UI lines, and Ukrainian labels for `derive`
  and `suggest`.
- Prose: `phases/phase_-1_intake.md` (the gate line, §0.5 step 3, §0.6, the §1 and §2 intros),
  `core/project-intake.md`, `core/capabilities.md`.
- **TCC** vendors `intake.py` and will pick this up on its next vendoring. The change only adds to
  the output (new keys on every field row, one new key in `missing()`), so the existing reads keep working.
