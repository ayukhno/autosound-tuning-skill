# Phase 1 — Crossovers, Coarse EQ, Levels & Delays

This phase establishes the physical foundation of the tune: the tuner's wishes checked, the crossovers as variants, band-specific targets, the coarse per-driver EQ, and the levels and delays computed with it — the tuner choosing at the end (the order the user set on 2026-09-17, `docs/DESIGN-2026-09-17-phase1-variants.md`).

> 🗺️ **Virtual-first?** If Phase −1 chose the virtual-first path (one capture session → design at the desk), the ORDER of work in Phases 0–3 changes — the phase numbers do not. Read [`virtual-first.md`](references/phases/virtual-first.md) alongside this file; it is the one home of that path. This file stays the authority on the iterative fallback and on every gate.

> On virtual-first, Phases 1–2 are one desk sitting that ends in a **predicted sum** (`predict.py`; the junctions by `predict --align`, the virtual tier through `--route`, the EQ as packages by `eq_propose` with `ellipsoid` for what stays) before anything is entered into the DSP — see [`virtual-first.md`](references/phases/virtual-first.md) §"Phases 1–2". Its order: the wishes (1.2) → the variants, best first (1.3) → coarse EQ per driver (1.4) → the joints with that EQ in the chains, front and sub first (1.5) → levels and how the scene is centred (1.6) → the sums predicted, the variants described, the tuner chooses (1.7). Phase 2 is the second part of EQ.

## 🎯 Goal-node

> ⛔ **Entry precondition — confirm BEFORE any Phase-1 measurement/analysis:** the Phase −1 / `project-intake.md §3` install verification is actually done — routing · electrical polarity · protective crossovers · **gain staging (amp gain up to the first THD jump, backed off ~10%)** · noise floor · safe sweep level. **Gain staging is the one most often skipped silently**, and every later level/EQ/target decision inherits a bad gain structure if it was — so name it explicitly and confirm it with the user. If you can't confirm a step was done, **stop and clear it (`§3`) before continuing** — don't tune on an unverified install. (This entry gate exists because a real run walked into Phase 1 with gains never set.)
>
> ⛔ **And the DSP's own numbers must be on record:** `enter-phase 1` refuses while the profile has no `dsp_processing_rate_hz` (the DSP's PROCESSING rate; the legacy name `sample_rate_hz` is still read — and it is NOT the capture rate: a UMIK-1 capturing at 48k under a 96k DSP is legitimate, said once, never refused), no `delay` step, or no `crossover_filters` for a tier whose `fields` declare `hp`/`lp`. Every delay in samples is computed from that rate — a rate nobody wrote down is a rate the next session assumes. Record with `dsp_profile.py set-field`, then `finalize`; `dsp_profile.py open-questions <project>/dsp_profile.json` lists everything still open.

> **The word in the report is «варіант»** — one of the 2–3 candidate sets the desk proposes here, not yet in the DSP. Never «конфігурація»: that word belongs to the ledger version standing in the processor (`naming-and-structure.md` §1a).

**Purpose:** establish the physical foundation — the tuner's wishes checked, crossovers as variants, per-band targets, the coarse per-driver EQ, raw driver timing (arrival TA), the levels — so Phase 2's EQ works on a correctly-aligned system whose delays already carry the coarse EQ's phase.

**Questions this phase answers:**
- Who arrives latest (the TA reference), and what is each driver's true acoustic arrival?
- What crossover frequencies/slopes/types suit these drivers + this cabin geometry?
- What per-band targets sum to the house curve without a joint hump?
- What does each of the tuner's wishes cost against the best the maths finds — and which of at most three variants does the tuner choose?

**Required evidence:** per-channel MMM RTA (FR) + sweep-with-loopback (IR/phase/GD) for every isolated driver; the active DSP delay state during measurement.

**✅ Quality gate → Phase 2:** the tuner's wishes checked (`xover_wishes`) and the variants described — at most three, the choice recorded with the tuner's OK; arrival TA set from **manually-inspected IR onsets** (not REW auto-estimates); L/R-symmetric crossovers agreed via the review loop and applied to the DSP; the coarse per-driver EQ (§5.5) banked with them, the delays computed with it in the chains; per-band NTT targets generated, verified (`_SUM` +3…6 dB vs single) and loaded; `<prefix>_v1_foundation.pct6` saved to `rew_analitic/dsp-config/`.

**⚠️ Failure modes:** trusting REW auto-delay (locks onto reflections / prior DSP offsets) → inspect IR onset by hand · assuming the midbass is latest → measure it · detuning crossovers L/R to fix a cabin asymmetry (kills the phantom center) → fix with EQ instead.

**🧩 Common patterns (hypotheses):** filter type by driver spacing (BE4 close/coplanar · LR4 far-apart) → [`filter-types-car-audio.md`](references/core/filter-types-car-audio.md); heavy midbass → align to IR peak → [`car-eq-patterns.md`](references/patterns/car-eq-patterns.md).

---

## Step-by-Step Runbook

### 1. Use the Phase-0 per-driver baseline
Phase 0 already captured each isolated driver raw (`<ch>_1 (sw)` + `<ch>_1 (rta)`, protective HPFs, clean `v0`) — the sweep carries IR/phase/distortion/GD, the MMM carries FR magnitude. **Analyze that baseline here; do not re-collect it.** (Only re-measure a driver if its baseline is missing or the install changed.)

* **De-embed before reading phase (doctrine 2026-08-24).** The `_1` solos were taken behind protective filters, and those filters are in the recording. `python3 rew_tool/rew_tool.py analyze-joints --process <project>/process --ver 1 --no-pair …` takes them back out from the capture round's record before any delay / polarity / APF is computed, and answers **`check`** for a channel nobody recorded — that is the Arbiter's question, not a number to enter. `--no-pair` because the baseline has no measured pairs yet: the reading is asked for without one and every row says **NOT BANKABLE** — the pair that verifies a junction comes with the Phase-2 capture, and without the flag the tool gives no verdict and names it. Since a front-end writes `OFF` or a filter for every channel it captures (ruling 2026-09-06), `check` means the record came from somewhere else, or did not get written; `OFF` itself is the default answer and asks for nothing. One home for the rule: [`project-intake.md §3`](references/core/project-intake.md).

> [!IMPORTANT]
> **Set a consistent Time Offset on the sweeps BEFORE reading phase:**
> Set a shared Time Offset ≈ the physical arrival of the reference speaker, applied to all sweeps. This keeps the phase flat and readable (especially at HF) instead of wrapping into a dense linear ramp. Read `rew-api-quirks.md` "Timing" for details.

### 2. Gross / Arrival Time-Alignment (TA)
Equalize the physical flight times of sound from each driver to the microphone.
* **⚠️ CRITICAL RULE: NEVER BLINDLY TRUST REW'S AUTOMATED DELAY ESTIMATES (Lesson 2026-06-27):**
  * **The situation is always such that we MUST inspect the impulse response graphs manually in the REW GUI, rather than trusting REW's automated numbers, because REW's internal estimation logic is fixed (фіксована логіка).**
  * REW's automatic delay-estimation logic easily locks onto strong late reflections (windshield, floor, or console) instead of the true direct sound, or can be skewed by pre-existing active DSP delays.
  * **How to manually inspect/verify:** Open the Impulse Response (IR) graph in the REW GUI. Locate the true geometric beginning of the impulse (**onset** — the very first deviation of the leading edge from the zero-amplitude line).
  * **Accounting for DSP offsets:** Always check if any time delays or phase adjustments were active in the DSP during measurement. If the DSP had active delays (e.g., from a prior tune), the acoustic arrival will be measured on top of those existing delays. We must manually subtract/account for those pre-existing delays to find the true physical acoustic paths.
* Use the **IR FIRST FRONT** (leading edge, NOT the global peak) of each solo channel.
* **Where the drivers are and where they point** is in `channels[].install` (how each driver is installed, in the person's own words) and `hardware.description`. Read them before trusting an arrival: a driver aimed away from the seat, or firing off a surface, can put a reflection ahead of the weak direct sound, which is the lock-on this section warns about.
* **Reference Selection:** The latest-arriving driver gets `0.00 ms` added delay, and every earlier driver is delayed to match it. Find "who is latest" from the measurements — do **not** assume it is the midbass.
* *Note:* Absolute IR time is crossover-independent and should be set early. Joint phase alignment is a separate, second step done in Phase 2.

### 3. Crossover & Slope Selection
* **The tuner's wishes first, in their own words — checked, not obeyed.** Ask what they think about each junction ("BE4 between tweeter and mid, BW2 between sub and midbass, not sure between midbass and mid" is a complete answer) and run `python3 rew_tool/xover_wishes.py <project> "<the sentence>"`: it names the junction each wish is about and checks it against the hard limits — the DSP's families, slopes and corner range, and the fragile driver's Fs floor (`crossover_checks.fs_margin`). A wish that breaks a limit is not computed; the nearest allowed setting is offered instead ("BW2 on your tweeter from 1044 Hz"). The variants are then computed **without** the wishes first (the best the maths finds) and **with** them, so the tuner sees what each wish costs (`docs/DESIGN-2026-09-17-phase1-variants.md` §1).
* **Consult the Phase-0 Acoustic Flaw Map first (§3.5):** distortion floors bound the corners (a corner needs low MEASURED in-band THD with margin — `get_distortion`, free with the baseline sweeps); do not land a joint inside a measured multipath pocket or a non-min-phase zone — the joint's phase there is chaotic and its APF repair will not hold (`diagnostic §24/§26`); place corners so the overlap region sits in coherent territory where possible.
* **Two or three candidates on the table, described — then the tuner chooses.** `python3 rew_tool/xover_candidates.py --solos DIR --project DIR --house FILE --channel <code> --hp lo:hi:step --lp lo:hi:step [--fs <installed Fs>]` lists the candidates `xover_select` finds for that driver, each with its fit, the level and phase at every corner, how far the phase turns across the corner octave (what 1.3 will have to absorb), the group delay it adds, and **how far each corner sits from the driver's own −6 dB edge on its solo** — a negative margin means the corner asks the driver for a region it does not deliver. The family's character is stated as a definition, not as a finding. It does not pick. **Each candidate's junction also carries the crossover pair's group-delay swing against the Blauert & Laws threshold** (hub `RES-014`): where the pick is made by a ranking — `xover_select`'s pair selection, the engine's pool in `resonalyze_engine` — a swing over the threshold costs 1 dB per ms, and the report shows **two leaders**: Resonalyze's own and the alternative by this still-experimental term, with the gentler candidate's edges listed so the tuner can take either. Below 500 Hz the threshold is the 500 Hz value, clamped, and the report says so.
* **Three questions of every corner BEFORE it is entered — `python3 rew_tool/crossover_checks.py --fc <Hz> --fs <installed Fs> --order <n> [--gd f:ms,…]`.** (1) **Fs margin**: below 1.1× the driver's INSTALLED Fs the answer is REFUSE, not advice — that is the protective floor; up to ~2× (less at steeper orders) it is CAUTION, measure distortion at level before accepting. Installed Fs comes from an impedance sweep (`core/impedance-ts.md`); a datasheet Fs is a weaker stand-in and reads as one. (2) **Group-delay budget**: the delay the filter ADDS against the Blauert & Laws audibility thresholds — never a measured absolute GD, which carries the whole flight time. (3) **Junction cost**: how loudly the ear hears trouble at fc, derived from ISO 226 rather than from the remembered "avoid 2–4 kHz" — the familiar answer falls out of the curve. Each verdict names its source; without `--fs` the tool says the one refusing check was skipped.
* **L/R Symmetry is the default:** Crossover type, slope, and frequency must be identical on both sides. Cabin acoustic asymmetries are corrected using output EQ, not by detuning crossovers, which destroys the phantom center.
* **Asymmetry as a variant:** Asymmetric crossovers are used only as a Hashimoto by-ear variant when symmetric setups fail to image (`method-hashimoto.md`).
* **Selection Guidelines:** Propose filter types based on physical driver characteristics and cabin geometry:
  * **Bessel (BE4):** Exceptional for close, coplanar drivers (e.g., midrange ↔ tweeter on A-pillars).
  * **Linkwitz-Riley (LR4):** Preferred where drivers are physically far apart (e.g., midbass in door ↔ midrange on A-pillar), as it minimizes overlap.
  * For crossover tradeoffs, refer to [filter-types-car-audio.md](references/core/filter-types-car-audio.md).

### 3.5 Preliminary Level Balance (computed from geometry — a starting hypothesis)
Set an initial **cut-only** per-channel level from physics, then verify by RTA/ear (a start, not a verdict). The nearer / more on-axis driver is louder at the reference seat → cut it.
* **Method** ([`rew_tool/level_offsets.py`](rew_tool/level_offsets.py)): per driver, off-axis loss = band-averaged far-field piston directivity `D(f,θ)=2·J1(ka·sinθ)/(ka·sinθ)`, plus distance loss `10·n·log10(d)`; offsets normalized cut-only (loudest driver cut most). This is why the mid can differ from the tweeter/woofer — the directivity integral depends on the driver's radius, band, and angle.
* **Read what the intake already holds first:** `channels[].install` (how each driver is installed, in the person's own words) and `hardware.description`. «Направлено на водія в вухо» IS the aiming angle for that driver. Ask only what those notes leave out, and name what they said that the numbers below use (W-2 A.7).
* **Inputs are PROJECT data — ASK the user** (store in `autosound_context.md`, Engineering Profile): per-driver **distance** to the reference ear, **off-axis aiming angle** (pods/pillars: on-axis / cross-fired / to centre), **effective piston radius** (≈ cone/dome size; the **enclosure** sets the LF band edge), cabin **distance exponent `n`** (2 = free field; lower if reverberant).
* The computed gains are the **start**; the summed RTA (§5 / Phase 2c) and the ear confirm/trim them. Never treat the number as final.

### 4. Review and Discussion
Format a Generator proposal package (per the data contract §3) and send it to the Critic. Refine the levels, timing, and crossovers. Upon agreement, the user applies these values to the DSP.

* **Bank the change first, then key it in (Generator):** route every hard-param change (crossover / gain / TA / polarity) through `apply.propose` — it writes the versioned snapshot AND emits the exact **old→new settings sheet** the Arbiter enters; after the Arbiter enters it, `attest` (🟡→🟢). This keeps state on disk (A/B, revert, resume) instead of drifting, and it's what produces the clean sheet. Details: [`rew_tool/state/schema.md`](rew_tool/state/schema.md).
* **How to apply & save to the DSP (Arbiter):**
  1. Open Helix PC-Tool and load your **existing active baseline setup** (the current active profile you are starting from). Do *not* assume a `.pct6` file of version `v0` exists on disk if this is a fresh start.
  2. Enter the new parameters from the settings sheet (protective/preliminary crossovers, delays, and level adjustments) exactly as emitted by `apply.propose`.
  3. Save the modified profile as `<prefix>_v1_foundation.pct6` locally on your computer in the workspace directory **`rew_analitic/dsp-config/`** (so it can be committed to Git and tracked properly).
  4. Write/flash this configuration into an active, safe slot of your physical Helix DSP to make it active before running any sweeps.

### 5. Generate Band-Specific Targets (Step 5b)
Once crossovers + levels are set, generate the per-driver targets **locally** with
[`rew_tool/target_bands.py`](rew_tool/target_bands.py) — feed it the
project's house curve + the per-channel config (crossovers with their types as the DSP writes them —
`BE12`, `LR24`, `BW18` — + the gains from `level_offsets.py`). A type it cannot model is refused by
name, never drawn as an LR24: a Bessel's knee is not an LR's (#56).
It bakes in the crossover roll-off, the two-speaker **summation offset** (~6 dB LF → ~3 dB HF), and the
**asymmetric compensation** (so an asymmetric L/R sum still reconstructs the house curve).
* **The payoff:** change a crossover or a level → **regenerate in one shot**, no manual web round-trip.
* **Sanity check:** `_SUM` (L+R pair) targets sit ~+3…6 dB above a single side; the mono sub has no summation offset. **Two subs** (`sw-f`/`sw-r`) are a pair: give each `is_stereo: true` so the `SWs` target carries the summation offset.
* ⚠️ **Never generate from `target_bands.py`'s built-in `_DEMO_CFG` (or leave `gain` unset/0) for a real project.** A real incident: per-band targets were committed with the demo's placeholder crossovers/gains (tw HPF ~3500 Hz instead of the project's actual 1000 Hz, gains left at the demo's −1.5/−2.0/0.0 instead of `level_offsets.py`'s real numbers) — L/R came out looking flat/symmetric and the tweeter target's roll-off knee didn't match the DSP at all, silently. **The config passed to `generate()` must be THIS project's just-applied `v1` crossovers/types + the actual `level_offsets.py` gains — never the module's demo/example values.** `target_bands.py` warns (`UserWarning`) if a channel's config exactly matches `_DEMO_CFG`, but that's a last-resort net, not a substitute for feeding it the real config.
* **Regenerate whenever a crossover or gain changes** — a per-band target file is a *derived* artifact of the current `v1`/`vN` hard-params, not a one-time output; a stale target after a crossover move silently misguides Phase 2a hygiene EQ.
* `write_targets` saves one `<code>_target.txt` per channel into `rew_analitic/target-curves/<name>/` — the
  name `rew_tool.py analyze-batch --curves-dir <that dir> --project <project>` looks up. Load them into REW
  and use them for Phase 2a hygiene EQ.
* *(Alternative — manual:* [nonotuningtool.com](https://nonotuningtool.com) does the same in a web UI with a "Stereo" config — mention it to the user as an option.)

### 5.5 Coarse EQ per driver — before the delays
The first part of EQ is Phase 1's (the user's decision, 2026-09-17; Resonalyze's order too — `MANUAL.md` §7 → §8 → §9): a PEQ rotates phase, so a joint delay computed without it is a delay redone after it. On the `_1` solos with the `v1` crossovers in the chains, propose **only the per-driver resonance package** — `python3 rew_tool/eq_propose.py --project DIR --rew --ver 1 --process DIR/process --house FILE [--ellipsoid DIR] --part 1`: cuts of minimum-phase peaks that stay across the positions, away from the junctions (±1 oct is the delay's business), Q no narrower than the ellipsoid's ceiling, toward each driver's own per-band target (§5); **zero boosts**. Accept it whole (`--accept`), and it rides in the `v1` sheet with the crossovers and levels. The L/R shape, the tone and everything summed are Phase 2. The joint delays — 2b on this path, 1.5 at the desk — are then computed **with this EQ in the chains**.

**Above 1 kHz a joint delay is banked only after the TUNED pair is measured** (hub `RES-013`, the Arbiter 2026-09-17): whole cycles look alike on a sum and on a phase view, so when the direct-sound reading of a mid↔tweeter joint (a 2-cycle cut) disagrees with the whole-record one, or the proposal sits a cycle from it, or the score and the witness disagree (hub `RES-016`), `predict --align` marks it `UNVERIFIED` and proposes nothing for it. Settle it with one measurement of the pair — a sweep of the two playing together, or both solos through the proposed chains — record which candidate it picks, and bank that. Below 1 kHz the witness decides as before.

### 6. Apply `v1` explicitly, then capture `_2` (hand-off to Phase 2)
**Before capturing `_2`, command the user to enter the FULL `v1` config into the DSP and save it — no silently assumed state.** Output it as an explicit step-by-step list (Golden Standard Format):
* **Crossovers** — freq / slope / type per channel.
* **Delays (TA)** — per channel, in **samples AND ms** (state the assumed DSP sample rate).
* **Gains** — per-channel levels (from `level_offsets.py`).
* **EQ** — the coarse per-driver package of §5.5, as a file import (`atf_eq.py` on a Helix); the rest is Phase 2.
* **REW sweep Time Offset** — set it (≈ the reference driver's arrival) **before** the sweeps, so phase reads flat.

**Then re-measure each channel** post-`v1` — `<ch>_2 (sw)` + `<ch>_2 (rta)`. This `_2` set (not the raw `_1` baseline) is what Phase 2 works on.

> **⚡ Read the whole `_2` set at once** — `python3 rew_tool.py analyze-batch "_2 (rta)"` renders one deviation matrix (every driver vs its per-band target, band means + `anchor` + `ripple`) so you enter Phase 2a with the batch picture in a single review pass, not N interactive pulls.

Once completed and verified, transition to **Phase 2**.
