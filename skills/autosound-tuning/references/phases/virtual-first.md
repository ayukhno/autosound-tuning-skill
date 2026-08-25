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

## Two modes, one path

- **Full** (a new tune): −1 → 0 → desk (1–2) → 3 → 4.
- **Improve an existing tune**: −1 → 3 → 4, with no new solos — Phase 3 already holds a sum
  measurement, MMM, fine EQ and a verdict. Both modes **read the current DSP settings into the
  ledger** first. ⚠️ On a Helix there is no reader for PC-Tool 6 — the current setup is transcribed
  from its screens (EQ is the slowest); say this cost in the intake, it is one-time.

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
- **−1.1** log Phase −1; run the intake (`project-intake.md §0.5`); pick the **mode** (new → full;
  improve an existing tune → the −1 → 3 → 4 route); read the current DSP settings into the ledger;
  show the loss table above.
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
- **0.1** `v0` into the DSP (a permanent slot — near-field any time later), effects/dynamics off per
  the profile list, seat, log Phase 0.
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
- **0.5** **tripod block**: `m-L-ctl1 (sw)` → the solos `<ch>_01 (sw)` of **every** channel (subs, w,
  m, tw, centre, rear — a couple of minutes while the base is set; two subs → also `SWs_01 (sw)`) →
  `m-L-ctl3 (sw)`. Doors shut, an even tempo.
- **0.6** **check on the spot**: each measurement present / usable — the IR peak above the pre-ringing
  ("broken impulse"), not a flat curve (loopback or a dead input), not in the noise; ctl1/ctl3 → a
  drift record. Re-take whatever failed now, while the tripod stands.
- **0.7** mark the protectives on the round (`capture-protective`); the `.mdat` into the project;
  finish the passport (temperature by eye, optional). **Tripod untouched** → the desk.

*Appendix, not on the path:* **impedance** — what for (driver Fs in its box → protective ≥ 1.1·Fs;
reveals a broken driver or wiring); without a rig, Fs from the datasheet with margin, and say so.

### Phases 1–2 · Desk (one sitting) — *goal: a full preset and a predicted sum before anything is entered*
- **1.1** de-embed the protectives from the solos (the round record is read by both the joint analysis
  and the prediction — `analyze-joints --process`, `predict --process`); the **flaw map** (Phase 0
  §3.5): per channel the peaks/nulls, stands/moves (from the ellipsoid), minimum-phase or not,
  below/above Schroeder → the sole right to an EQ band.
- **1.2** **crossovers**: 2–3 candidates, scored automatically on magnitude, phase and impulse, each
  with its drivers' strengths and weaknesses and a plain description → **the user chooses**.
- **1.3** **joints bottom-up** (sub↔sub → subs↔midbass → midbass↔mid → mid↔tweeter): delay × polarity
  by how much the pair loses when summed vs the ideal; near-tie through both polarities; an all-pass if
  a null remains. L/R: the pair-arrival difference against tape set (b) — the tape is the arbiter.
- **1.4** **levels**: from geometry (distances and angles from the tape), cut-only — a first estimate;
  a second from the measurement; a divergence is a finding, not an error.
- **1.5** **predict the sums** (`predict`): L, R, ALL; the sum loss per joint; L−R per band; a graph. A
  bad joint → back to 1.2/1.3 — iterations exist, but at the desk.
- **2.1** **coarse EQ** (`target_bands`): only cuts of minimum-phase peaks from bands that have a flaw-map
  row; below ~150–200 Hz free, above only what survives the ellipsoid; zero boosts.
- **2.2** **check after EQ**: predict again — joints and L/R on the same rulers (EQ inside a joint band
  rotates phase).
- **2.3** **preset to disk**: the settings sheet — what is entered in PC-Tool per channel (HPF/LPF,
  gain, delay, polarity, APF, EQ), old → new, samples for the DSP rate, a "why" per row; the EQ file in
  the DSP format to import; the predicted graph. Into the project (+git if configured).

### Phase 3 · Car, a short session — *goal: verify the desk against what the mic hears, do what the desk can't (MMM), and lock*
- **3.1** **enter and check entry**: the preset into the DSP per the sheet (EQ by file import); "entered"
  in the ledger. Levels from the passport. Two controls, from the tripod: *base* — `m-L (sw)` vs
  `m-L-ctl3` from Phase 0 → the drift between capture and today, recorded; *entry* — 1–2 solos `_02 (sw)`
  (e.g. tw-L, w-L) vs the predicted processed channel — catches a PC-Tool entry error before it becomes
  a "bad joint".
- **3.2** **all sums from the tripod** `_02 (sw)`, at the same levels: the joints (sub+midbass L/R,
  midbass+mid L/R, mid+tweeter L/R), L, R, ALL. Predicted/measured delta per joint band: ≤ 1 dB
  trusted; more → a **warning** (joint, band) + a "not trusted" mark, and we go on. For a warned joint,
  the decision is checked on the spot against the measured sum (delay/polarity/all-pass as today), a
  change in the DSP, the joint switch repeated. The only in-car iteration, and only for such joints.
  *Improve mode:* the same without a prediction — joints read straight from the measured sums.
- **3.3** **tripod down.** MMM `_02 (rta)` handheld: L, R, ALL, groups. Fine EQ over MMM as today
  (2c/2d): group targets, the residual to target, only what stands in the MMM → enter → `_final (rta)`:
  every channel, groups, L, R, ALL.
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

Noted so a later session does not mistake them for done: the flaw map as a command; joint alignment by
sum-loss as a command (the function exists); crossover checks (group-delay budget, the 2–4 kHz junction
penalty, tweeter fc from Fs); the **candidate description** for crossovers (2–3, magnitude/phase/impulse,
per-driver strengths); levels from the measurement as a second estimate; a whole-session probe (max
peak / min SNR of every channel in one go); the entry control (`_02` solo vs prediction); the Helix
setup reader (screens only; EQ = ATF); a general term "effects and dynamic processing" in DSP profiles;
the ellipsoid diagram.
