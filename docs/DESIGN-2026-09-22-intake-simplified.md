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

---

## Round 2: the Arbiter's review of the page (same day)

He went through the regenerated page and made 12 corrections. They are applied here. Where they
conflict with a row in the table above, **this section wins**. It adds a `place` attribute next to
`when` (`intake.PLACES`). `when` still says which step needs the answer. `place` says whether the
page asks a person at all: `now` · `goal` (optional) · `new_dsp` (only for a processor with no
profile) · `equipment` (optional fold) · `memo` (not asked: a list the person can read).

| # | his point | what changed |
|---|---|---|
| 1 | pick the car from a list, still editable, and an edited car is a new car | `intake.known_cars(project_dir)`: the cabin library (`knowledge/cars/`, today one body: VW Passat B8 sedan) plus the sibling projects next to this one that record all four parts. **No other car catalogue exists in the skill, and none was invented.** The hub `#185` car package is TCC's import and ships no list. A pick fills the four fields, and the page flags an edit as a new car |
| 2 | vendor and model are linked | `intake.known_dsps()` from the bundled profiles. The model list shows only the chosen vendor's models, "another…" opens free text, and both are saved together (`{"dsp": …}`) |
| 3 | drop "can each output be soloed" | `dsp.per_channel_measurable` is derived ("always yes") and sits in the memo |
| 4 | a slot's tier comes only from this processor's tiers, and the page first asks which tiers exist and which are used | `intake.dsp_state()` reads the tiers from the project profile, the bundled match or the draft. New field `dsp.tiers_used` (`project.json` `dsp.tiers_used`) is asked before the channel rows, and the row's tier list is narrowed to it. For a new processor, "which tiers exist" is `dsp.tiers`, written into the draft profile (`{"dsp_tiers": …}` → `dsp_profile.set_field`) |
| 5 | mic type and cal file do not matter; the question is physical vs acoustic loopback | `LOOPBACKS` = physical / acoustic / none (`none` kept for a rig with neither). Mic model, cal files and capture rate lost `required` and moved to the memo |
| 6 | the hardware channel map is optional; «Карта каналів» means the DSP layout; the hardware section is «Інше обладнання»; the DSP is always required | the drivers (make/model/Fs/condition/position/enclosure) and the remote controls are `equipment`, an optional fold whose table shows only once channel rows exist. The channel section is «Карта каналів процесора». The DSP stays required |
| 7 | do not ask: the clip check, the measurement input and routing, the listening input, the signal chain, REW and mic | all of these are in the memo and no longer `required` (`source.*`, `dsp.measurement_input`, amps, mic, capture rate, REW API) |
| 8 | goal = EMMA / AYA / for myself / other + free text, not required | one optional control. The form maps the ticks onto `goal.formats` / `goal.purpose` and the text onto `goal.wishes`, now stored in `project.json` `goal` |
| 9 | «Яка цільова крива?» | reworded (EN: "Which target curve?") and stored in `goal.target_curve` |
| 10 | genres as checkboxes, several allowed | `GENRES` is a multi-select enum with `other` |
| 11 | everything from Phase 1 on: read it from the processor, or ask it once for a NEW processor | the capability checklist (processing rate, tiers, slot counts, EQ, crossovers, delays, presets) is `new_dsp`, shown only when `dsp_state()["new"]` (or live, when "another…" is picked). Routing is read off the processor, and design path and mode are derived. Positions and enclosures went to equipment, the rest to the memo |
| 12 | choose the test-track libraries (checkboxes) from what the skill describes | `TRACK_LIBRARIES` is read off the `library` column of `references/patterns/test-tracks.md` (CarMus, Chesky, mono, EMMA, AYA, own) plus `streaming`, as a multi-select |

**Counts after round 2** (empty project, `--lang uk`; the table has 72 fields with `dsp.tiers_used`):
17 fields asked now, 11 of them choices (the car picker fills make/model/generation as well). 6
optional goal fields in 4 controls. 7 new-processor fields, hidden unless the processor is new. 7
optional equipment fields. 35 memo items that are not asked. Before any of this there were 68
questions on the page.

**The gate:** `contract.GATE_REQUIRED` is unchanged, and nothing in round 2 needed it weakened.
Two things to know:
- `dsp_profile.json` must still exist before Phase 0. For a known processor the session copies the
  bundled profile. For a new one the page writes only the draft's tiers, and the session finishes
  the draft (`dsp_profile.py finalize`). That is the same as before, now started from the page.
- Moving the input questions out of the intake does not remove Phase 0's pre-session checklist #4
  (the preset switch that resets the input). That check still runs at the car, in Phase 0. The
  intake no longer asks it in advance.

## Decision 2026-09-22: one form for every front-end

The user's decision: **one page, the skill's own** (`intake_form.py serve`, stdlib only). A terminal
session on macOS or Windows opens it in the browser; TCC opens the same served page in the system
browser from a button. TCC does not embed it, because TCC ships PySide6-Essentials without
WebEngine on purpose, and it does not draw a second native form. The questions exist once, and there
is one form to test. This supersedes the "TCC renders its own form from `intake.py` data" reading
of SCR-059 (hub #178).
