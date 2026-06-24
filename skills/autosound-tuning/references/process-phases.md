# The tuning process — phases, package format, refinements

This is the working schedule of the process, agreed with the user (14 steps), grouped into phases.
Each phase = one or more Generator↔Critic cycles with escalation to the Arbiter.

> **A session = tuning toward ONE curve**, possibly multi-day and with breaks (a Mac restart wipes the chat) — keep the state in project memory, reconcile against it on resume. **Phases 0–1 (crossovers, TA, phase, levels, the anomaly map) are the foundation, curve-agnostic, done once.** Changing the target curve mostly re-runs **only Phase 2** (per-channel EQ + level shaping to the new curve) → a second curve is much faster. The session lifecycle is in `SKILL.md` §Session lifecycle.

Protective crossovers for the raw measurements — **a conservative PROTECTION of FRAGILE drivers ONLY** (tweeter, mid; center — depending on ITS driver), so as not to burn them with excessive excursion on the sweep: HP **at/above the REAL resonance (Fs) of EACH driver**. ⚠️ **The HP frequency = a function of the SPECIFIC driver — NOT a fixed number, NOT "typical", NOT from a profile as fact.** No Fs → **ask the user** (or from the datasheet), then set it conservatively higher; **don't hand out a frequency table in advance**. **The midbass and sub don't need a protective HP** — they're made to play low; **a subsonic — only for a PORTED sub** (the cone unloads below the port tuning), **a sealed box limits excursion itself** → not needed. ⚠️ **The final crossover points/types — Phase 1, AFTER the measurements** (propose / derive from measurement+summation, do NOT prescribe by a table; don't introduce drivers the user didn't give) — and **don't show/announce them earlier**: announcing "candidates" in Phase 0 = getting ahead + anchoring. Curve names — per the `autosound_context.md` §5 glossary.

---

## Three sources — one method (measurement × ear × experience)

Our process = **measurement "by the instruments" (REW) ⊕ Hashimoto's by-ear secrets (`method-hashimoto.md`) ⊕ the experience of Arkadij/ResoNix/Wehmeyer (`voicing-by-ear.md`, `diagnostic §16-17`)**, interwoven. The principle: at each phase **MEASUREMENT gives what's reliable** (magnitude, crossover frequency, joint summation, excess-phase, mic-shift), **the EAR — what measurement doesn't get** (filter slope, image/depth/transients, voicing), and they **CROSS-CHECK** each other.
- **Crossovers (Phase 1):** measurement picks the FREQUENCY (RTA magnitude + slopes); **Hashimoto adds the SLOPE** by ear ("slope→frequency"; mid/treble + mid/low tracks) + the rule **HPF at/above the driver's resonance** (not below 40–50; tweeter HPF > the tweeter's resonance). **L/R symmetry = the DEFAULT** (the same type+order+frequency on the left and right): different L/R phase rotation destroys the phantom center — critical for SQ (EMMA/AYA); compensate cabin asymmetry with EQ/Gain (+ delays for the center), not with crossovers (`filter-types §L/R symmetry`). **Asymmetric L/R crossovers, tuned by ear each side separately = a deliberate Hashimoto VARIANT** — only when symmetry won't image; then verify the imaging carefully (`method-hashimoto.md`).
- **Polarity/joints:** Hashimoto does it EARLY by ear (image fusion) — that's a **VARIANT**; our reliable arbiter = **SUMMATION** (`diagnostic §9`). On conflict → summation.
- **Delays:** the base — **geometry / first arrival** (tape measure to the dust cap + the first-arrival peak of the light mid/tweeter); ⚠️ **IR-peak TA via the REW API is unreliable** (`rew-api-quirks` — junk timing) → don't trust API peaks, check against geometry. By-ear "verticals→center" on mono, the sub by a double bass. **A stereo pair's delays are set ONCE for centering; do NOT detune one side for an FR dip** (ITD 200 Hz–1.5 kHz → the image drifts; cabin dips are often SBIR/non-min-phase — can't be closed by time/EQ). Align joints with an **all-pass** (`helix-phase-allpass`), not by shifting the channel's delay. Image-center = LEVEL not time (Wehmeyer §16); a broadband shift = time (§15).
- **EQ:** measurement (RTA to target · excess-phase: EQ-fixable? · mic-shift mode-vs-reflection · 1/6 oct) + by-ear centering with mono sines (⚠️ **don't touch 2.5–5k** — hearing sensitivity/equal-loudness) + symptom→fix (`voicing-by-ear.md`).
- **Listening (Phase 5):** a curated track for the measurement (`test-tracks.md`). **Client voicing (Phase 6):** curve→character + by-ear taste axes.
- **Hygiene (Hashimoto):** break in new components before the precise tune; **breaks** (hearing fatigues, the untrained ear faster).
> No source is dogma: where by-ear contradicts measurement — keep it as a **variant** (a different geometry/situation may make it right; the unexpected one unlocks a solution — proven in a session).

---

## Phase −1 — New project / new install (intake)

If the project is new (no profile/files), the install was just done/reworked, or "we're tuning from scratch" → first **`references/project-intake.md`**: the briefing (a quickstart for new hands) · the equipment and goals interview · **choosing the target curve TOGETHER with the user (no default)** · install verification (routing, electrical polarity, protective crossovers, gain staging, noise, break-in of new drivers, a safe sweep level) · creating the project files. Only after that — Phase 0.

---

## Phase 0 — Baseline and target (preparation)

> This was added by Claude before Phase 1 — without it, the "loss vs target" comparison has no reference point.
>
> **FIRST — the glossary + naming convention (ONCE, with the user), BEFORE the measurements.** Agree the channel codes (`autosound_context.md §5`: `sw / w-L/R / m-L/R / tw-L/R / c / r`) and the convention `<channel>_<vN> (sw|rta)` — the method suffix **`(sw)`** = loopback sweep, **`(rta)`** = MMM RTA; **`_N` = the config version** (NOT "baseline", NOT `_MMM`). Examples: `m-L_1 (sw)`, `w-R_1 (rta)`. Then **don't repeat the rules** — at the moment of action give **copy-paste-ready specifics**: the exact save PATH + the measurement list short and comma-separated (`sw_1, w-L_1, w-R_1, m-L_1…`) + a brief goal (`naming-and-structure §3`).
>
> ⚠️ **Baseline = a RAW measurement in the current state.** TA techniques (aligning heavy midbasses to the IR peak, delays) are **Phase 1/2b**, NOT here; at baseline we only measure.

1. Import **the current session's target curve** into REW as the target (chosen at the start of every tune **with the user — no default**; choice help: the curve→character table in `voicing-by-ear.md` + genres/taste from intake). **The target sets only the SHAPE, not the level** — level is worked separately, from the measured levels. Compare with the target by shape, not with a flat line.
   > ⚠️ **Here — ONLY the session's full curve.** Per-band/per-channel targets (w/m/tw) — don't look for or generate them now — they depend on the crossover summation, so they're generated at **step 5b AFTER the crossovers are fixed**. A common slip (from the test session): having the full curve, running off to look for per-band targets before the crossovers.
2. Capture a baseline of the whole system in the current state + save the REW file with an explicit Trace ID **per the convention above** (e.g. `ALL_1 (sw)` + `ALL_1 (rta)` — NOT `m-ALL_baseline`).
3. Check gain staging / clipping (DSP output levels vs amp sensitivity) — so the measurements have no distortion from overload.
4. Fix a **fixed MMM pattern** (speed, the mic's coverage volume, the bounds) — otherwise successive MMMs aren't comparable.

---

## Phase 1 — Crossovers + level + preliminary delay

**User (step 1):** raw measurements with protective HPFs.
- **MMM RTA** — for the precise FR: (a) choosing the crossover points between bands so that L=R and the loss vs target is minimal (use the existing slopes + the target slopes; in the midbass the target often has a rise — take more energy from the drivers there); (b) a preliminary correction of channel level/gains.
- **SWEEP (loopback)** — for: the impulse (preliminary delay alignment), distortion (choosing safe band ranges), + other graphs per `analysis-playbook.md`.
  > ⚠️ **Set a consistent Time Offset on the sweeps BEFORE reading phase / joint summation — an explicit step, easy to skip.** Loopback alone isn't enough: if the IR t=0 sits far from the actual arrival, the bulk delay spins the phase into a fast linear ramp → "strong wrapping", unreadable noise (real symptom from the test session: right-side joints undiagnosable). Set a **shared Time Offset ≈ the arrival**, the SAME reference on every channel (**NOT** each to its own peak — that erases the relative arrivals) → phase goes flat/readable (esp. HF) AND relative inter-channel timing is preserved, so the joints and TA become diagnosable. Mechanism/fix detail → `rew-api-quirks.md` "Timing".

**Claude (step 2):** REW API → analysis → a proposal on (a) signal level, (b) delay, (c) crossover frequencies for maximum SQ by an efficient means: without deep loss-cuts, minimizing/balancing phase distortion, joining the bands for clarity/detail/transparency. → a package to Gemini. Up to 3 rounds → escalation.

**Gemini (step 3):** analyzes the proposed variant + 2–3 alternatives, asks questions or proposes better ones, given the Phase-1 goals.

**Claude (step 4):** builds a General-type EQ in REW on each raw RTA curve: HPF, LPF; PK to cut peaks; SHELF if needed. If REW doesn't allow it — produces a **filter table** for manual entry.

**User (step 5):** transfers the gains/levels, delays, filters from REW (or the table) into the DSP. Questions/ideas — discuss and adjust on the spot.

**Step 5b — per-band targets (nonotuningtool):** after the crossovers are fixed, generate in **https://nonotuningtool.com** the target curves **per band — w (midbass), m (mid), tw (tweeter), stereo**: the session's house curve + the chosen crossovers (type/frequency/order) → the tool computes EACH band's target **accounting for the acoustic-summation coefficients in the overlap regions at the joints**. ⚠️ So this is **NOT a "slicing" of the full curve** — in the overlaps the targets are lowered so the **SUM** of the bands gives the house curve (otherwise a double contribution at the joint = a hump). Export for REW → **load the files into `rew_analitic/target-curves/<name>/`** (next to the full #1; the per-band files with crossover frequencies in the names) → import into REW (= the "Nono" sub-targets #2–9; the loaded exports are read by `rew_tool/nono_curves.py`: full=`freq mag`, per-band=`freq mag phase`). Phase-2a hygiene EQ levels a channel to ITS OWN nono target, not to the full house curve. ⚠️ Out of band the sub-targets carry junk — sample only in-band (`rew-api-quirks.md`); anchor levels to the FULL target #1, not the sub-targets (`diagnostic §1`). A later crossover change = regenerate the targets.

> **Reading & exporting NTT targets (field gotchas):** on the graph the **dashed line = the predicted SUM**, **bold black = the target**. Export gives two curves per band: **non-SUM = the SINGLE-channel target** (tune each side alone to it) · **`_SUM` = the L+R-PAIR target**, carrying the summation vector (+6 dB <80 Hz coherent → +3 dB >1 kHz power, approximation between). A **mono** channel (sub) → non-SUM = `_SUM` (no L+R sum) — correct. ⚠️ **Silent trap:** the export checkboxes ("Driver sum (L+R)" / "Single driver") are SEPARATE from the per-driver **Stereo** config upstream — if the driver wasn't set Stereo, `_SUM` exports as a COPY of non-SUM **even with the box ticked**, and a measured PAIR then reads +3/+6 "hot" against the wrong target. Set **Stereo BEFORE export**; verify **delta(non-SUM, `_SUM`) ≈ +6/+3 for pairs, 0 for mono**. And the band is the sacred **acoustic** target, but the **electric** XO you set in the DSP ≠ NTT's electric number — a real driver pre-rolls-off, so set the electric XO so the MEASURED acoustic lands in the band (often HIGHER) and correct by measurement; per-side cabin reality is an in-car summation question, not a per-side NTT re-run.

---

## Phase 2 — Linearization → joint phase → summed-curve alignment → final EQ (sub-steps in THIS exact order)

> The order isn't accidental (synced with the user 2026-06-12): **hygiene EQ (2a) BEFORE phase alignment (2b)** — cutting min-phase peaks rotates the phase locally, so the joints are aligned on already-cleaned channels (otherwise later EQ breaks the just-set phases). **Aligning the SUMMED curves (2c)** makes sense only after clean joints. **Final EQ (2d)** — the final technical accuracy to the session's target. **The listener's wishes are NOT here**: that's Phase 6, entirely on the virtual preset. If EQ near a joint changes later — re-check that joint's summation.

### 2a — Hygiene EQ of each channel (to ITS OWN nono target)
**User (step 6):** MMM RTA of each channel. **Claude (step 7):** analysis of the deviations from the per-channel nono target → EQ: **cut min-phase peaks, do NOT fill nulls** (peak-vs-null `diagnostic §2`, mic-shift §13; don't re-diagnose anomalies from the profile) → a package to Gemini (**step 8**, goals as in step 3), 3 rounds → escalation. Before loading — the **summed curve of the filter bank + fine 1/24 localization (§21)**. **≥3 bands — never by hand:** build the EQ in REW → transfer by file (for Helix → `helix-eq-export.md`).

### 2b — Joint phase (sweep)
**User/Claude (step 9):** SWEEP (loopback) → final TA + phase alignment across the joints in the order **midbass (reference) → sub → mid → tweeter** (`helix-phase-allpass.md`; Wehmeyer `diagnostic §16`), then **L↔R** (mono summation). The verdict at each joint — by SUMMATION (`diagnostic §3/§9`), not by single-position phase (§10); the predicted phases can be viewed on the sweep curves with the EQ applied.

### 2c — Aligning the summed curves (pairs → sides → joints)
**User:** MMM RTA of the sums: **Ws / Ms / TWs** (L+R of each band) · **L vs R** (full front sides) · **SW+Ws**. **Claude:** align:
- **(a) band pairs** to each other — level/shape, especially in the summation regions (an overlap hump ≠ a hot driver, `diagnostic §3`);
- **(b) L vs R** — to a match of **SHAPE** in the image region (§11; "take from the louder one AND add to the quieter one" §17);
- **(c) SW+Ws** — a joint without a dip/hump (§3, polarity §9).
**The tool by purpose (§6):** L/R asymmetry → **OUTPUT** (per-channel); shared or deliberately per-side moves → **VIRTUAL** (symmetric L=R, or per side — e.g. a broadband image shift §15); don't re-notch what the output already did.

### 2d — Final EQ to target by RTA
**Claude (step 10):** the residual SHAPE of ALL to the house curve — **with broad moves (shelves/tilt), mostly on the virtual (L=R linked)**. This is still a **technical** layer (accuracy to the session's target), not taste: taste deviations ("warmer", "more bass") are left to Phase 6 as a separate preset. The user analyzes the predicted curves → transfers them into the DSP or discusses doubts.

---

## Phase 3 — Control measurement and verdict

**User (step 11):** a control MMM RTA: each channel; L+R pairs; the sub + both midbasses; the left side and the right side without the sub; all channels together.

**Claude + Gemini (step 12):** analyze the result, each forms an **independent verdict**. The organizer and the user's contact is Claude.

---

## Phase 4 — Center and rear (optional, after the front is aligned)

**Step 13:** first align the front PERFECTLY (Phases 0–3), ONLY then add the center and rear as a separate process. The center's and rear's levels/polarity/APF are **PROJECT state** (`dsp-state-current`); at the start of work **verify by measurement, not from memory** (real case 2026-06-12: the log said −12/NORM, the DSP had −3/INV).

- **Center — the full method → `diagnostic-techniques.md §20`:** a manual-L+R center = a 3rd source → a comb with the mids; treat it by **narrowing the band to the body of the voice (LP~1000–1200)**, a quiet level (a complement, not an accomplice), polarity by the SUM/ear, APF carefully. For an **FX/RealCenter** (algorithmic) — a level that "supports the focus, doesn't dominate"; a delay so it doesn't lead the front; if it "compresses" the stage → the phase control. A center tweeter (if present): HP high (6–8k), level −6..−10 dB (by-ear variants — judge by ear).
- **Rear (rear-fill) — the method → `voicing-by-ear.md` §Rear:** the goal = envelopment, NOT a rear image; HP above the doors' boom zone (~300–315), LP ~4–5k, a differential L−R matrix by default, a quiet level, delay TA + 8–10 ms (Haas).

---

## Phase 5 — Targeted listening (verification by ear) [PENULTIMATE]

After the measured tune is loaded and verified (Phase 3 + optional Phase 4) — **a structured listening pass over curated test tracks** (`test-tracks.md`), to check EVERY SQ measure by ear: tonal balance, center/phantom, L/R imaging, **depth**, width, height, punch/attack, sibilants, separation, spatial coherence. It catches what measurement doesn't see (depth/imaging/transients — ear-driven; cabin phase/GD unreliable, `diagnostic §10`).
- **Method (targeted):** for each measure, take a track from the `test-tracks.md` index → tell the Arbiter **WHAT to play + where (timecode) + WHAT to listen for** (a binary good/bad). One marker at a time; don't dump the whole list.
- **The standard PASS (a full check at milestones):** when the tune is "ready" (after Phase 3/4) or before a competition — take the Arbiter along a **fixed route** `test-tracks.md §Standard pass` (balance → mono-center → EMMA positions → focus → depth → punch/joint → sub<40 → sibilants → load → universality). Each item = track+marker+a binary verdict into a checklist; everything ✗ — the next iteration's backlog. This is the structured "path" of listening verification.
- **Targeted listening is also a cross-cutting TOOL throughout the WHOLE process**, not only here: anywhere a hypothesis needs the ear (joint phase, heavy-midbass polarity, punch, center, diffuseness) — pick a track and check, without waiting for Phase 5.
- Residuals the DSP can't take (physics/reflections/geometry) — record as a **limit**, don't fight blindly.

---

## Phase 6 — Voicing to the CLIENT's preferences [LAST]

The final **SUBJECTIVE** layer on top of the technically-correct base: tune the voicing (the target's shape / the virtual layer) to the client's taste — warmer/brighter, more bass, less presence, etc. Here "accuracy" deliberately yields to "what's pleasant to the client". Done on the **VIRTUAL layer as a switchable preset** (the base untouched — `SKILL.md` §Session lifecycle, base+voicing). Keep BOTH (the technical + the client one) → A/B.

**Method (full → `references/voicing-by-ear.md`):**
1. **Capture the client's taste.** Axes: warm↔bright · bass-heavy↔neutral · forward↔laid-back · accuracy↔fun. + what music and how they listen (genres, loudness, long trips). *(Future: an intake questionnaire at the project start — roadmap.)*
2. **Curve audition:** flatten (±1 dB) → apply the house curves in turn as an EQ profile → listen to a familiar track (Diana Krall "Temptation" · Dire Straits "Private Investigations" · Daft Punk "Giorgio by Moroder") → the client chooses. Curve→character — the table in `voicing-by-ear.md`.
3. **Fine-tune by ear** along the taste axes (drier/fuller, stage height, voice closer/farther, crystalline/softer top) — symptom→EQ move in `voicing-by-ear.md`.
4. **Save as a separate voicing preset**; keep the technical one (Accurate/reference) alongside for A/B and competitions.

---

## Phase 7 — Project wrap-up: knowledge → the skill and the author [CLOSING]

At milestones (the end of a session/project, after the listening work) Claude **proactively** runs the closing ritual — FOUR distinct streams, interactively, with an always-optional free comment (full logic + rules → `references/feedback-loop.md`):
- **A. Feedback on the PROJECT** (the tune's goal + the car's backlog) → the session log. *("Fine-tuning" — here, not to be confused with the skill.)*
- **B. Feedback on the SKILL** — what's good/not so, **ONLY about what was used** in this project → material to improve the skill.
- **C. Consent to share the work with the COMMUNITY** — the list is pre-selected (opt-out) → "I agree to send it for the community's benefit!"; **a human sends it** (no personal data/measurements).
- **D. AFTER submit** — thanks, and only on a positive (A) a quiet donation link. ⚠️ The donation is **not a form item, not a word before submit**; skip it if Sponsors isn't active.
- Plus **session-log discipline**: changelog / dsp-state / ▶️ CONTINUE / skill-inbox (SKILL.md §Session log).

---

## Package format (Generator → Critic), Contract §3

```
[Iteration N/3]  Generator: <Claude|Gemini>
Trace ID: <the measurement's name in REW>

Current state (delta): <what changed: filters / EQ / delays>
Digitized anomalies: <numbers: FR / phase / impulse>   (+ attached CSV trace)
Hypothesis: <the cause of the problem>
Proposal: <type, frequency, Q, channel>
Expected effect:
  • The filter's direct action: <e.g. APF — phase rotation, 0 dB in FR>
  • Prediction after summation: <e.g. +3 dB in the L/R overlap region>
Math rationale: <short numbers / time deltas>
My assumptions: <what I take as given>
What I ask you to challenge first: <ONE specific thing>
```

> "Expected effect" **must** separate the filter's direct action from the summation result — an all-pass is flat in FR, any FR change comes through source summation.

---

## Claude's refinements to the process (the answer to step 14)

Accepted; where relevant — already woven into the phases above.

1. **Order: delays → hygiene EQ → joint phase → summed alignment (pairs/sides/SW+Ws) → final EQ → [Phase 6] voicing wishes** (updated 2026-06-12; earlier this read "delays → phase → EQ"). Delay interacts with the crossover phase at the joint; but cutting min-phase peaks also rotates the phase locally — so we align the joints AFTER linearizing the channels (2a→2b), the summed alignment — after clean joints (2c), the final EQ — the technical finale (2d), and the listener's taste — as a separate virtual preset (Phase 6). In Phase 1 the delay is **preliminary** (from the impulse/sweep); the final TA + phase — Phase 2b. Draw conclusions about the mutual L/R phase **after** TA, not on the baseline (Gemini confirmed this in a test round too).

   **The refined phase flow (from the user):**
   `raw sweep → TA → raw sweep → phase (for info) → crossover filters → phase → RTA → EQ`
   The point: capture the phase of the **raw** signals (after TA, before the crossovers) as a reference, then the phase **with the crossovers** — to see **how much distortion the crossover filters introduced**, rather than confusing it with geometry/cabin. The first "raw sweep" — before TA (for the delays), the second "raw sweep" — after TA (the reference phase without filters).

2. **MMM RTA — for the FR, SWEEP — for phase/time.** MMM averages the magnitude across the cabin, but the phase in it is unreliable. Choosing the crossover **frequency** = RTA magnitude + slopes; checking the phase **joint** and the delays = a loopback sweep. Don't confuse the data sources.

3. **Excess-phase / minimum-phase decomposition.** In REW, look at the excess phase to tell EQ-fixable (minimum-phase) dips from unfixable ones. This directly decides "touch it or not" for the 150 Hz dip (diffraction → not minimum-phase → EQ forbidden).

4. **L=R is a trend, not a clone.** The cabin geometry makes L/R naturally asymmetric (a 150 Hz dip on the left). Align the trends and the joint region, but allow per-channel EQ; don't chase identical curves where physics forbids it.

5. **Predict the summation before applying.** Before committing, use REW's trace arithmetic (A+B) — predict the L+R sum and the band+band sum at the joint, so you don't get a hole/hump after the fact.

6. **Sub↔Midbass — a separate focus.** The sub's joint with the midbass (polarity + delay + ~60 Hz) often gives the biggest SQ gain; in the control measurement (step 11) the "sub + both midbasses" pair is already there — add an explicit phase/polarity check at this joint.

7. **Sweep data that's useful (the answer to the step-1 question):**
   - **GD (group delay):** excess GD at joints and resonances — where phase rotation is permissible.
   - **CSD / waterfall:** resonances and "ringing" (doors, 150 Hz) — EQ against mechanics.
   - **Step response:** the drivers' time integration (the rule "midbass by the peak, not the nose").
   - **Distortion (THD + individual harmonics):** safe band limits (where THD rises → put the HPF there).
   - **ETC / impulse:** delays and reflections.
   - **Excess phase:** what's EQ-fixable (see point 3).

8. **Transport (fixed 2026-06-01).** REW runs **natively on macOS** → the API `localhost:4735` is reachable **directly from the host** where Claude/Gemini live; no port-forwarding is needed, we pull data live. Parallels (the Windows VM) is needed **only for the Helix DSP PC-Tool** (Windows-only) — the single "courier" step is handing the EQ export from REW (Mac) to Helix via a shared folder. The critic channel: `gemini_critic.sh` on the same macOS host. (Earlier this wrongly said "the REW API is inside the VM" — an artifact of early assumptions, removed.)

9. **Role rotation.** Periodically make Gemini the Generator and Claude the Critic — so one model's bias doesn't accumulate (Contract §0).
