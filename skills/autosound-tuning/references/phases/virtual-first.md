# Virtual-first — one capture session, then design at the desk

> 🗺️ **A HAPPY PATH across the existing phases, not a new set of them.** The phase numbers −1…5 do
> not change (`process-state.json`, TCC and session memory keep them); what changes is the *content*
> and the *order of work inside* Phases 0–3. This file is the one home of that path; each phase file
> carries a short pointer here. The older **iterative** path (measure → change one thing → re-measure)
> is not removed — it is the fallback the loss table below routes to. Codified 2026-08-25 from a
> step-by-step dry run with the author; the engine it rests on is `rew_tool/predict.py` (validated
> against the car at stage 0, 2026-08-21: junction interference matched to 0.3–0.45 dB in band means,
> and the sub state identified blind).

## The idea

The cabin is not modelled — it is **in the measurement**: each driver's solo IR from the listening
seat already contains every reflection and mode. Delays, polarity, crossovers and EQ are linear
operations, so the complex sum of the individually measured drivers, each passed through its own DSP
chain, **is** what the microphone would record. So the whole measurement budget goes into ONE
disciplined capture session; the tune is then designed at the desk against a predicted sum; the car is
needed once more, briefly, to verify the prediction and do the fine EQ the desk cannot see.

## One way in: from scratch

**−1 → 0 → desk (1–2) → 3 → 4.** That is the method: every driver is measured on its own, the tune
is designed at the desk against a predicted sum, and the car verifies it. Whatever state the DSP is
in, it is **read into the ledger first**.

**Improving somebody else’s existing tune is NOT a route this method lays out** (user’s ruling
2026-09-09). People do want it, and the tools here serve it — a transcribed setup enters the ledger
(`setup_import.py`), `predict.py --from-state` predicts a change from the series already in hand,
and neither the flaw map nor the EQ proposer cares where the state came from. What is not laid out
is the ORDER of that work, and pretending otherwise would sell a path nobody has walked end to end.
A tuner who wants it builds that route with their own AI, out of these tools.

Say so plainly when it is asked for, and do **not** improvise a shortened phase order: an
`enter-phase 3` that skipped the baseline still meets the gates asking for a target curve and a
flaw map, and answering those with hand-typed placeholders is how a tune ends up built on numbers
nobody measured.

⚠️ **Reading the current setup costs time, and it is one-time.** On a Helix there is no reader for
  PC-Tool 6 — the current setup is transcribed from its screens (EQ is the slowest); say that cost
  in the intake. The
  transcription goes through `setup_import.py <project> transcription.json [--atf code=file.atf]
  --write`: every value is checked against the DSP profile (a delay off the 0.01 ms grid, a gain
  outside the range, an EQ type the DSP does not have — each refused by name, nothing rounded), the
  EQ is taken from the ATF bank where one exists, and the version carries
  `provenance: transcription, verified_by_file=false` so nobody later mistakes it for a read-back.

There is no separate "iterative path" to choose. The path is one; the intake states what the available
gear **costs** you:

| what's missing | consequence for the path |
|---|---|
| a loopback rig on one clock (a USB mic + acoustic loopback in REW) | a shared time base exists but through the air — worse precision; the drift pair in 0.4 shows whether you're inside it |
| a hardware-verified DSP filter model (Helix today) | the filter phase in the prediction is approximate → the predicted/measured delta in Phase 3 is larger, warnings expected |
| a tripod | P0 cannot be reproduced → the `_2` verification sums are advisory only |

None of these blocks the path; they widen the delta the verification must forgive.

## The ledger is the one source of truth

Every change to the DSP is written to the ledger at the moment it is entered; nothing is asked twice.
A question to the user is warranted only when the alternative is a **guess** — an error is not a
problem, it is fixed together. (This matters most in "improve" mode, where the whole current tune is
transcribed once from the PC-Tool screens.)

## The path, phase by phase (input → action → output)

Step names describe the action, not a command. The joint and L/R **phase** is the foundation: it is
**set in 1.3, checked on the prediction in 1.5, and checked again after EQ in 2.2**.

### Phase −1 · Intake (desk) — *goal: decide nothing in the car, and be surprised by nothing*
- **−1.1** log Phase −1; run the intake (`phase_-1_intake.md §0.5`); read the current DSP settings
  into the ledger; show the loss table above.
- **−1.2** *new DSP* (only if not in the knowledge base): the question session → a profile (rate,
  delay step, crossover families, Q convention, the list of "effects and dynamic processing" to turn
  off) → into the knowledge base with consent (a GitHub Issue; email when the author publishes one).
- **−1.3** channels (subs 1/2, centre, rear) → the glossary; **protective filters** for the capture:
  the user says, or we remind — HPF on m/tw/c ≥ 1.1·Fs from the datasheet (this IS the protection; a
  moderate level is a second layer, not a replacement) → recorded as intent. `contract.py check --gate`.
- **−1.4** *prepare the session the day before* — see [`capture-session-sheet.md`](capture-session-sheet.md):
  back up the current tune to a file; a `v0` preset (protectives only, gains level, delays 0, polarity
  normal, EQ empty, effects off) into the ledger; REW configured; the capture sheet from the glossary;
  a blank passport; the bag.

### Phase 0 · Capture session (car, once) — *goal: one disciplined capture, then back only for Phase 3*
Order of channels is the user's in TCC; the path only constrains: handheld before the tripod; the whole
tripod block in one go, **tripod untouched until Phase 3**; `m-L-ctl1` first and `m-L-ctl3` last in the
tripod block; every channel both `(sw)` and `(rta)`.
- **0.0** **open the capture round** — `python3 rew_tool/state/process.py <project>/process
  capture-start 1 "<title>" ...` (the expected titles: `python3 rew_tool/naming.py <project> expect
  0 1`). Not a formality and not renumbered into 0.1: 0.6 and 0.7 below, and every `capture-taken`
  between them, REFUSE while no round is open — the round is what makes these sweeps one series
  instead of loose titles only REW remembers.
- **0.1** `v0` into the DSP (a permanent slot — near-field any time later), **effects and dynamic
  processing off** — everything that is not gain, delay, polarity, crossover or EQ. The vendor's own
  names for them are in the profile: `python3 rew_tool/dsp_profile.py effects <profile.json>` prints
  the list, and **exits 3 saying so when the DSP has none recorded** — that is a thing to go and read
  off the DSP's screens, not a reason to guess which switches counted. Then the seat, then log Phase 0.
- **0.2** **session levels, handheld**: one REW output level for all sweeps, one head-unit/Conductor
  level for all RTA; then the knobs are not touched. Set by the **loudest-driver test** (usually the
  sub): peak −5…−10 dBFS in; the quietest driver above the cabin noise (example: sub −5, centre −15…−20,
  garage noise −40 works, because a 12 s sweep × 4 reps accumulates; garage noise is low-frequency, so
  the sub and midbass suffer, not the tweeters). The judge is `capture-check` per measurement, not a
  number. **The same numbers in Phase 3.**
- **0.3** **handheld**: RTA `<ch>_01 (rta)` of every channel (~20–30 s of movement); the ellipsoid
  `<ch> p1…p9_01 (sw)` for w-L/R, m-L/R and any channel with EQ decisions in 0.2–2 kHz. Near-field
  optional here or any time on the `v0` slot (the working sub LPF hides exactly the natural roll-off
  near-field is taken to see).
- **0.4** **tripod P0**: two tape sets — (a) to return the tripod: three distances from the capsule to
  fixed body points (windscreen, driver's door glass, roof) + a seat-rail mark; (b) for the desk:
  capsule → each driver's centre (the L/R arbiter, §23). Timing = loopback. Drift pair `m-L (sw)` ×2 →
  < 0.1 sample (not saved).
- **0.5** **tripod block**: `m-L-ctl1_01 (sw)` → the solos `<ch>_01 (sw)` of **every** channel (subs, w,
  m, tw, centre, rear — a couple of minutes while the base is set; two subs → also `SWs_01 (sw)`) →
  `m-L-ctl3_01 (sw)`. Doors shut, an even tempo.
- **0.6** **check on the spot** (`capture-check --session`): each measurement present / usable — the
  IR peak above the pre-ringing ("broken impulse"), not a flat curve (loopback or a dead input), not
  in the noise; the whole session in one table (levels side by side, loudest/quietest); ctl1/ctl3 →
  the drift record, in capture samples, written on the round. Re-take whatever failed now, while the
  tripod stands. **What goes to the Arbiter is what the CHECK said** — usable, flagged, unchecked
  and why, the drift record — and then the step reply's one line about what is next. The arrivals
  are in the round and Phase 1 reads them (1.3); a prose reading here has none of that step's
  guards, and it is a habit of the text rather than one session's slip (SKILL.md `✍️ Output Style`).
- **0.7** mark the protectives on the round (`capture-protective`); the `.mdat` into the project;
  finish the passport (temperature by eye, optional). **Tripod untouched** → the desk.
- **0.8** **at the desk, before Phase 1 will open** — the two things `enter-phase 1` refuses without:
  the **target curve on the record** (`python3 rew_tool/state/process.py <project>/process target
  <preset> <curve>`, e.g. `target FULL EPY` — a curve named only in the conversation is lost on the
  next session) and a **non-empty flaw map** (`python3 rew_tool/flaw_map.py --project <project>
  --solos <dir> [--ellipsoid <dir>] --write`, the rows landing in `acoustics.flaws[]` as
  hypotheses; `project.py <project> flaw ...` adds one by hand). Both gates fire on the forward move
  out of Phase 0 (`process.py` `_require_target`, `_require_flaw_map`), so skipping them does not
  cost a warning — it costs the entry into Phase 1.

*Appendix, not on the path:* **impedance** — what for (driver Fs in its box → protective ≥ 1.1·Fs;
reveals a broken driver or wiring); without a rig, Fs from the datasheet with margin, and say so.

### Phases 1–2 · Desk (one sitting) — *goal: a full preset and a predicted sum before anything is entered*
- **1.1** de-embed the protectives from the solos (the round record is read by both the joint analysis
  and the prediction — `analyze-joints --process`, `predict --process`); **read the flaw map written
  in 0.8** (`project.py <project> flaws`) — per channel the peaks/nulls, stands/moves (from the
  ellipsoid), minimum-phase or not, below/above Schroeder → the sole right to an EQ band. Building it
  here is too late: the map is what the entry into this phase was gated on.
- **1.2** **the tuner's wishes first, in free words** — "BE4 between tweeter and mid, BW2 between sub and
  midbass, not sure between midbass and mid" is a complete answer. `rew_tool/xover_wishes.py <project>
  "<the sentence>"` names the junction each clause is about and checks it against the hard limits: the
  DSP's families, slopes and corner range (the profile) and the fragile driver's Fs floor
  (`crossover_checks.fs_margin` — REFUSE under 1.1 × Fs, CAUTION up to the craft convention, which a
  steeper slope relaxes). A wish that breaks a limit is **not computed**; the nearest allowed setting is
  offered instead ("BW2 on your tweeter from 1044 Hz"). "Not sure" says the desk proposes there.
- **1.3** **crossovers — the variants**: **the best the maths finds first, without the wishes**; then a
  pass **with** them, so each wish shows what it costs against the best. The whole configuration at once —
  every junction, both sides, the centre and the rear as their own zones — is Resonalyze's Auto crossover,
  called on the project's own layout: `resonalyze_engine.py run <project> <set> --out <dir>` (the driver types
  from the channel map, the protective filters divided out, the device's delay range;
  `docs/DESIGN-2026-09-17-phase1-variants.md` §3). Every edge it proposes is held to the same limits as a wish:
  on the Passat its best put the mids' high-pass at 200 Hz, under their 217 Hz floor, so that junction is
  searched again inside the limits by Resonalyze's junction tuner (250 Hz, the score +0.01 dB) before anything
  is shown. The wishes are read against that best with `--wishes "..."`: a wish with a corner by the junction
  probe (the score per side on one shared band, the sum loss after its own delay), a family or slope without a
  corner by the tuner (the best that wish can do, held to the same limits). The per-driver candidates stay
  beside it (`xover_candidates` → `xover_select`, `select_neighbor_pair`, every corner through `crossover_checks`).
  **At most three on the table**: one mathematical and up to two from the wishes; more is what the
  Resonalyze app is for.
  - **The engine is not required, and nobody is made to use it.** It is a binary the installer fetches
    only on a machine with no .NET SDK, and refuses to fetch on `--no-engine` / `-NoEngine`; nothing in
    the method turns it on by itself. Without one, `resonalyze_engine.py` says so and stops — *"no
    engine: no prebuilt one in `<that folder>`, and no .NET SDK to build one"* — it does not fall back
    silently, because a proposal from a tool that did not run is the one thing worse than no proposal.
    **Phase 1 then runs the per-driver way, which is the path this method had before the engine and
    still keeps in full:** candidates per driver (`xover_candidates` → `xover_select`, every corner
    through `crossover_checks` and the wish check), delays and polarity joint by joint bottom-up
    (`predict --align` with the RES-013/RES-016 guard at 1.5), levels from the geometry and then from
    the measurement (1.6), the sums and the description (1.7), EQ by `eq_propose`, the scene presets by
    `scene_presets`. What is NOT available without the engine, and should be said to the tuner rather
    than worked around: the whole configuration proposed at once (every junction, both sides, the centre
    and the rear as their own zones), Resonalyze's Auto delay staging and its gain balance, and what a
    wish costs — neither the junction probe nor the whole-configuration variant. Those are proposals,
    not measurements: a tune done without them is a tune done the way every tune here was done until
    2026-09-17. The choice is made at 1.7, after the sums are predicted. **Two leaders** (hub `RES-014`): beside the engine's best, the alternative by the experimental group-delay term — the crossover pair's swing against the Blauert & Laws threshold at each junction, 1 dB per ms over it, clamped below 500 Hz — shown with each junction's swing/threshold; the run continues with the engine's leader, the alternative's edges are on the table for the tuner.
- **1.4** **coarse EQ per driver — BEFORE the delays** (the user's decision, 2026-09-17; Resonalyze's
  order too): the first part of `eq_propose` (`--part 1`) — resonances per driver group — cuts of minimum-phase
  peaks that stay across the positions, away from the junctions, Q no narrower than the ellipsoid's
  ceiling, toward each driver's own per-band target; zero boosts. A PEQ rotates phase, so a delay
  computed without it is a delay redone after it. The rest of EQ is Phase 2.
- **1.5** **joints bottom-up, with the coarse EQ in the chains** (sub↔sub → subs↔midbass → midbass↔mid →
  mid↔tweeter): delay × polarity by how much the pair loses when summed vs the ideal (`predict --align`:
  each joint read on the member below AS IT WILL NOW PLAY, delays on the DSP's grid, the proposal as
  `aligned-delta.json` for `apply.propose`); near-tie through both polarities; an all-pass if a null
  remains (`--apf` hints one). **Above 1 kHz a delay candidate is confirmed on the TUNED pair's
  arrival, not banked off the desk** (hub `RES-013`): whole cycles look alike on a sum and on a
  phase view, so where the direct-sound reading (a 2-cycle cut) and the whole-record one disagree, or the proposal sits a cycle from the direct-sound reading (hub `RES-016`), the joint comes back
  `UNVERIFIED` with both candidates — measure the pair (a sweep of the two together, or both solos
  through these chains), record which candidate it picks, and only then bank that joint. **Front and sub first; then the centre and the rear are placed against
  the settled front** — the centre read against both sides where the front mids play (1–4 kHz), as
  Resonalyze stages it; its Auto delay does the same in the same `resonalyze_engine.py run`, and says when a
  placement is at Low confidence (the Passat's centre and rear are) or when the device cannot hold the
  delays — with the rear fill that would fit (the Helix holds 20.82 ms on an output and 20.82 on the virtual
  channel feeding it, and the two add: a rear delay past one tier is split between them). L/R: the pair-arrival difference
  against tape set (b) — the tape is the arbiter.
- **1.6** **levels, and how the scene is centred**: levels from geometry (distances and angles from the
  tape), cut-only — a first estimate; a second from the measurement; a divergence is a finding, not an
  error. **The scene is centred by level here, and that is the BASE** (research's answer, RES-011, on the
  user's plan): the arrivals aligned to the seat (scene offset 0) and the near-side pull as channel gain
  (Resonalyze's gain balance, "levels only" — `resonalyze_engine.py run --gains`; the Passat's is 2 / 4 / 4 dB on
  midbass / mid / tweeter). No choice is asked in Phase 1: the second preset — the same pull by time — is built
  from this base in Phase 2, after each side is whole, and the ear decides there (2.1; `scene_presets.py`).
  **Three reads once the levels exist** (skill #50, #51):
  - **Re-read each junction's LEVEL STEP** (the engine report prints it: own-band level plus gain, lower minus
    upper). The sum loss and the dip are level-normalised, so they do not move with the levels and cannot
    say whether the junction now sums flat.
  - **A level fitted over a band that holds cabin gain or the driver's own humps** (a sub over 30–55 Hz)
    moves once coarse EQ (1.4 / `eq_propose --part 1`) removes them. Re-read it after the EQ, because the
    GAIN moves and not the crossover.
  - **Before the first trim with decimals, ask what the machine is set to**: the gain step is a switch on
    the vendor software's settings panel, not a property of the device (Helix: *Channel Gain Resolution*
    1.00 / 0.50 / 0.25 / 0.10 dB). Record it with `dsp_profile.py set-setting <project> channel_gain.step_db
    <value>`, and do the same before EQ for `parametric_eq.gain_step_db` and `parametric_eq.link_mode`.
    `apply.propose` names a trim off the recorded step, or asks when none is recorded (#52).
  - **A cut-only spread wider than 3 dB is a gain-structure finding**, not a level decision.
    `level_offsets.py` does the arithmetic: raising the quiet channel's amplifier by N gives the same balance
    and keeps N dB of system headroom. Both costs are named (that channel's headroom, against the whole
    system's maximum SPL and SNR), and the tuner chooses.
- **1.7** **The variants as a TRADE-OFF FRONT** (issue #38, W-2): `resonalyze_engine.py run` ends with it.
  The best, each wish as a whole configuration and, with no wish, the engine's own ranked alternatives
  (`--alternatives N`, 3 by default; an edge under a limit is moved to the nearest allowed and said) are
  each predicted from the set's solos. Each gets the same four terms from `variant_front.py`: tonal RMS
  against the target with the level removed (`--target FILE`, else the recorded curve), |L−R| per band,
  the level-normalised junction loss with each junction's level step, and ripple. Then 2–3 are picked by
  three weightings (tone / stage / junctions first) and shown in their own order, each with what it buys
  and what it spends. A spread smaller than a term's tie margin is called a tie, not a trade. A junction
  that no candidate repairs is named as the ceiling. The output always ends with what the objective
  cannot see (imaging, depth, fatigue), and **no winner is chosen**.
- **1.7** **predict the sums, describe the variants, and the tuner chooses** (`predict`): L, R, ALL; the
  sum loss per joint; L−R per band; a graph — for each variant on the table, with its per-term numbers
  **and in words**: what changes and how it will sound, written by the generator and reviewed by the
  critic. The predicted sums go into the target-curve visualizer beside the target — `sums_export.py --predicted
  DIR/predicted.json --out DIR/curves --label <variant> --smoothing 1/6|psy`, one file per sum, two variants dropped
  together are two lines; listening is offered, not required. **The tuner chooses, and with that OK the variant goes to
  the sheet (2.3)** — nothing enters the DSP or the ledger before it. A bad joint → back to 1.3/1.5 —
  iterations exist, but at the desk. Free play afterwards: the tuner changes settings as they like, the
  desk computes and compares where it can, or the tuner decides alone.
  - **A junction at the desk is computed by `predict`, or it is not computed.** A script written for
    one evening is not evidence: the desk's own three misses of 02–07.09.2026 were all outside the
    tool — a summation done in magnitudes only (which cannot see a sign, and predicted −1.2 dB where
    the car gave −3.8), a centre added by hand, and a level bug in the IR pull. The arithmetic in
    `predict` reproduces the measured pairs of a real series to **0.36 dB** with no free parameter
    (hub `RES-006`, the `_60` set); what is missing when a desk misses is the call, not the model.
  - **The solos you have are the solos measured under the state you are in** — `--from-state v_031`
    divides that state out and applies the new one (`H × C_new/C_old`). A row that did not change
    cancels exactly; a band where the old chain was more than 30 dB down is ABSENT from the sum and
    named, because dividing by nothing amplifies the noise floor. No separate session of bare solos.
  - **Two windows, and every number says which.** Junctions, phase and arrival read through the
    **gate** — the direct sound (`--gate 2` for one band, `--fdw 6` across the spectrum); magnitude
    against a target reads the **whole record**, because that is what the seat hears. A window that
    holds under **5 cycles of the junction frequency**, or that is shorter than the two members'
    arrivals are apart, is refused for that junction and it falls back to steady with the arithmetic
    printed — measured: at 2 kHz a 3 ms gate (6 cycles) verifies to 0.03 dB, while at 215 Hz the same
    gate reads 5 dB of "cancellation" that is the window (hub `RES-006`).
  - **The centre is summed, under the condition it was measured in.** `ALL+C` sits beside `ALL`, the
    `c↔FRONT` pair reads on the same row as a junction, and `verify_prediction --all-plus-c` compares
    what the centre ADDS per third of an octave against the measurement. The condition travels with
    the number: one signal on both inputs, the centre playing the whole programme — for music it
    carries only the correlated part, so the coherent sum is an **upper bound**. (Resonalyze draws a
    centre and never sums it, for exactly this reason; we sum it because the `ALL+C` measurement
    exists and is what we check against, and we name the limit instead of skipping the sum.) A rear
    pair was always in its side's sum, by the side in its own code — that is now said rather than
    contradicted by a note.
  - **A knob is not a calibration.** The capture round records the hardware controls
    (`process.py … capture-knobs SubRC=4/4`), the prediction carries them, and
    `verify_prediction --project DIR` compares them: equal → the series are comparable; different
    with a mapping (`set-control-mapping`) → the expected shift on its own line and the calibration
    as what is left; different with no mapping, or not recorded at all → **a refusal, exit 4**. An
    hour went on "where did +4 dB on the virtual sub go" because nothing carried the sub knob's
    −4 (hub `RES-007`).
  - **`--delta-vs` for what a change does, `--ladder` for what the rungs give.** The delta reports only
    the rows that differ and the junctions they are in; the ladder prints one junction's variants in
    the order asked and **does not sort them** — a reading stays a reading, and a proposal says it is one
    (`--align` searches and proposes). **The desk proposes; the Arbiter decides:** a variant is shown,
    explained, advised and discussed, and nothing goes into the DSP or the ledger without the Arbiter's OK
    — no EQ into a cancellation, no improvement claimed without a measurement after (the virtual-DSP desk
    spec's requirement В8, as the user put it on 2026-09-17).
- **2.1** **the second part of EQ, in this order** (the user's decision, 2026-09-17), as packages
  (`eq_propose --part 2`, with `ellipsoid` for σ(f), stays/moves and the Q ceiling), each accepted or refused
  whole and banked as one version (`apply.propose`): **L/R pairs per band** (one shape, broadly, on the
  louder side, Q ≤ 1 — what skews the stage is the L/R difference, not the distance from the target) →
  **the junctions of each side**, left and right apart → **sub with mids** → **each side whole** → **everything
  together**, the tone per pair toward the target within max(1 dB, 2σ) → **the centre under everything** →
  **the rear under everything**. Only cuts of minimum-phase peaks that stay across the positions; below
  ~150–200 Hz a point is trusted, above only what survives the ellipsoid; zero boosts. **A step whose EQ
  touched a junction's band (±1 oct) re-checks that junction's delay (1.5); otherwise the delays stay** —
  a package says which junctions it reaches (`recheck_junctions`) before it is banked. **Between "each side
  whole" and "everything together" the scene's two presets go to the ear** (RES-011): A is the base as it stands,
  B the same pull by time — `scene_presets.py --project DIR --cut w=2,m=4,tw=4` builds the ladder (0.15–0.30 ms,
  the near side later, its cut reduced 16 dB/ms, both channels trimmed to the base's centred level) as deltas for
  the sheet; the comparison is the cheat-sheet's protocol (centre off, loudness matched, A-B-B-A three rounds; no
  consistent difference → keep A). The L+R sum is tuned only after the choice, because an offset between the
  sides changes it.
  Every package names the listening characteristic that checks it.
- **2.2** **check after EQ**: predict again — joints and L/R on the same rulers **and through the same
  windows** (EQ inside a joint band rotates phase). `verify_prediction` reads the measured set through
  the window the prediction carries (`predicted.json`'s `window_spec`), per junction, so a gated
  prediction is never compared against a steady measurement: those are two questions subtracted from
  each other, and on the `_60` woofer↔mid that looked like 5.2 dB of model error (hub `RES-006`).
- **2.3** **preset to disk**: the settings sheet — what is entered in PC-Tool per channel (HPF/LPF,
  gain, delay, polarity, APF, EQ), old → new, samples for the DSP rate, a "why" per row; the EQ file in
  the DSP format to import; the predicted graph. Into the project (+git if configured).

### Phase 3 · Car, a short session — *goal: verify the desk against what the mic hears, do what the desk can't (MMM), and lock*
- **3.1** **enter and check entry**: the preset into the DSP per the sheet (EQ by file import); "entered"
  in the ledger. Levels from the passport. Two controls, from the tripod: *base* — `m-L (sw)` vs
  `m-L-ctl3` from Phase 0 → the drift between capture and today, recorded; *entry* — 1–2 solos `_02 (sw)`
  (e.g. tw-L, w-L) vs the predicted processed channel (`verify_prediction --entry`: shape after one
  offset, the worst point and the chain feature nearest to it) — catches a PC-Tool entry error before it
  becomes a "bad joint".
- **3.2** **all sums from the tripod** `_02 (sw)`, at the same levels: the joints (sub+midbass L/R,
  midbass+mid L/R, mid+tweeter L/R), L, R, ALL. Predicted/measured delta per joint band: ≤ 1 dB
  trusted; more → a **warning** (joint, band) + a "not trusted" mark, and we go on. For a warned joint,
  the decision is checked on the spot against the measured sum (delay/polarity/all-pass as today), a
  change in the DSP, the joint switch repeated. The only in-car iteration, and only for such joints.
  *Improve mode:* the same without a prediction — joints read straight from the measured sums.
- **3.3** **tripod down.** MMM `_02 (rta)` handheld: L, R, ALL, groups. Fine EQ over MMM as today
  (2c/2d): group targets, the residual to target, only what stands in the MMM → enter → `_final (rta)`:
  every channel, groups, L, R, ALL. **What cuts and what booms** (`ear_suspects`): the top three peaks
  above the local trend on the MMM, classed (cuts 2–5 kHz, sibilant 5–9 kHz, nasal 0.8–2 kHz, boxy
  150–300 Hz, booms 40–120 Hz), ear-weighted, one conservative correction each (half the prominence,
  the widest Q that covers it) into the B slot — the technical tune stays in A. **A/B one band at a
  time** with the cheat-sheet phrase for that suspect; the answer is *better / same / worse*, recorded
  through `listening-verdict` (`--text "suspect:<id>=better"`); *same* → the band is not needed, *worse*
  → dropped and remembered. **Three suspects, three rounds at most** — the loop for a listener who
  cannot say how it should sound but can say which sounds better ("how I like it", not competition;
  for a judged tune the same loop runs against the target and the judges' characteristics). Taste
  corrections live in their own preset or on the virtual layer, never in the per-driver EQ (Phase 5).
- **3.4** two independent verdicts + the minimum ear pass (as today) → the technical lock → backup: the
  ledger snapshot, the PC-Tool setup file, the `.mdat` into the project (+git).

**Phase 4** (ears) and **Phase 5** (variations, centre/rear) — as today; the listening cheat sheet
([`listening-cheat-sheet.md`](references/patterns/listening-cheat-sheet.md)) is the vocabulary.

## The stage-0 lesson, without which Phase 3 lies

The measured half must be on the **same base** as the prediction — point switches from the tripod, not
MMM. MMM fills the nulls a point prediction shows (a real residual: w-L +27 dB @165 Hz was exactly
this), so it is kept **separate**, for the fine EQ and voicing. That is why the tripod stands from 0.4
to 3.2 and everything handheld is done before it.

## Degradation — when the path falls back to iterative

The desk half of the path (Phases 1–2 designed from a prediction, Phase 3 verifying it) needs all three
of: a loopback rig on one clock, a hardware-verified DSP filter model, and the capture discipline of
Phase 0. Miss one and that half degrades, per the loss table — but the **capture session (Phase 0) is
worth running either way**, and the fallback is the existing iterative content of Phases 1–3, not a
different process:

- **No shared clock** (a USB mic): delays and polarity are not taken from the prediction but measured
  in the car at the joints (today's 2b) — the desk still designs crossovers, levels and coarse EQ.
- **An unverified DSP** (not Helix): the prediction's filter phase is approximate; expect a larger
  Phase-3 delta and read the warnings as expected, not as a model error.
- **No tripod**: P0 is not reproducible, so the `_2` verification sums are advisory; lean on MMM and the
  ear.

The rule the intake applies: **run Phase 0 the same way regardless; degrade only the desk (1–2) and the
verification (3), never the capture.**

## Tool gaps still open on this path

None left open from the list of 2026-08-25. Closed last on 2026-08-26: the flaw map as a command
(`flaw_map` — rows proposed from the solos as hypotheses with evidence, and every finding NOT
written named with its reason), the candidate description for crossovers (`xover_candidates` — 2–3
per driver, magnitude/phase/impulse and the corner's margin from the driver's own edge; it describes
and never picks), the ellipsoid diagram (in `capture-session-sheet.md`, block B). Closed the same
afternoon: crossover checks (`crossover_checks`:
Fs margin, group-delay budget, junction cost), levels from the measurement as a second estimate
(`level_offsets --solos`), the setup reader as a validated transcription with provenance
(`setup_import`), "effects and dynamic processing" as a profile field (`dsp_profile effects`).
Closed earlier the same day: joint
alignment by sum loss (`predict --align`), the whole-session probe (`capture-check --session`), the entry
control (`verify_prediction --entry`), the ellipsoid's σ(f) / stays-moves / Q ceiling (`ellipsoid`),
coarse EQ as packages (`eq_propose`), what cuts and what booms with the A/B loop (`ear_suspects`).
