# Phase 2 — Linearization & Acoustic Alignment

This is the core technical execution phase. All operations **MUST** be performed in this exact chronological order: Hygiene EQ (2a) → Joint Phase Alignment (2b) → Summed Alignment (2c) → Final Technical EQ (2d).

## 🎯 Goal-node

**Purpose:** linearize + acoustically align the system to the target — hygiene EQ, joint phase, summed alignment, final target EQ.

**Questions this phase answers:** which peaks are minimum-phase (EQ-able) vs nulls (leave)? are the joints phase-aligned by summation? does the summed system match the target?

**Required evidence:** a **fresh re-measurement of the applied `v1` system** (`_2`, each channel **post-crossover** — not the raw `_1` baseline): per-channel FR + excess-phase (min vs non-min phase); joint summation (uninverted vs inverted); summed-group MMM (Ws/Ms/TWs, L vs R, SW+Ws).

**✅ Quality gate → Phase 3:** peaks cut / nulls untouched; joints aligned by **summation** (APF/fine delay, not raw-delay shifts); summed groups match target; final target EQ on the **virtual layer** only; strict order 2a→2d held; **two critic checkpoints passed** (after phase alignment · after EQ).

**⚠️ Failure modes:** boosting into nulls (non-min-phase → wasted headroom/distortion) · 30-band auto-banks (use minimal conscious EQ) · shifting raw channel delays for phase (breaks gross TA) · sneaking client taste in here (that's Phase 5).

**🧩 Refs:** min-vs-non-min phase, summation → [`diagnostic-techniques.md`](file:///skills/autosound-tuning/references/core/diagnostic-techniques.md).

---

## 2a — Hygiene EQ of Each Channel
Linearize each individual channel to its own **per-band target** (from Phase 1 §5 / `target_bands.py`), using its **`<ch>_2 (rta)`** for the magnitude to EQ and its **`<ch>_2 (sw)`** excess-phase to decide what is EQ-able. Calculate the correction from `analysis.py` **`compute_deviation`** (measured − target) — don't eyeball it; and **read the channel's current filters first** (`get_filters`/`get_equaliser`) — never assume it is raw (a real bug overwrote the user's manual notches).

> **⚡ Mass read in one shot:** get the whole-batch picture with `python3 rew_tool.py analyze-batch "_2 (rta)"` — one consolidated deviation matrix (every `_2` driver vs its per-band target, band means + `anchor` + `ripple`), one review pass, ~5× fewer API round-trips than pulling each driver in the interactive REPL. Read the matrix first to see which channels need hygiene EQ; drill into a specific driver interactively only where a cell looks off (or the excess-phase decision is needed).

> **⚙️ Batch the WHOLE 2a round — do not loop channel-by-channel.** Diagnose **every** channel that needs hygiene EQ in this pass, propose them all together for **one** review, apply them as **one** DSP import (`atf_eq.py` export → a single Helix file import), then take **one** comprehensive re-measurement pass to verify the whole batch. This mirrors Phase 1's cadence exactly (compute the full foundation → one `_2` re-measure), **not** a change-one → re-measure → change-next loop — that per-parameter granularity is only for a Level-2 black-box DSP with no read-back (`project-intake.md`), never here on a readable one. Hygiene EQ is per-channel *independent* (each channel to its own target), so batch application still lets you attribute per channel in the single re-measurement; the only cross-channel interactions live at the joints, which **2b** handles and the joint-band re-entrancy rule (`process-phases.md`) already guards. A convergent session computes the full round, ships one import, and verifies once.

### Rules of Action
1. **Min-Phase Peaks Only:** Cut narrow and wide minimum-phase peaks.
2. **Never Fill Nulls:** Do **NOT** EQ-boost acoustic nulls/dips. If a dip is deep and narrow, it is a phase cancellation or diffraction effect (non-minimum-phase). Equalizer boosting into nulls wastes amplifier headroom and introduces physical distortion.
   * *Example:* The VW Passat B8 left midbass has a null at ~150 Hz due to door diffraction. It is non-minimum-phase; EQ is strictly forbidden. Check the excess-phase curve in REW to separate minimum-phase from non-minimum-phase.
3. **L=R is a Trend, Not a Clone:** Cabin acoustics force natural asymmetry. Align the general shape/trend, but do not force identical per-channel curves where physics forbids it.
4. **Generate PEQ Files:** For more than 3 bands, build the EQ in REW and export the filter set. For Helix DSP, use the Audiotec-Fischer export format via `rew_tool/atf_eq.py` (this transfer already exists — never re-script it) for a clean, one-shot file import. Do **not** input 30-band auto-banks. Conscious, minimal EQ beats excessive bands.
5. **VCP over Output at junctions (field-proven):** place narrow high-Q cuts **near a crossover junction** on the **Virtual/VCP layer**, not the output channel — it preserves the driver's phase coherence at the joint (real case: mid cuts ~453/459 Hz on VCP saved the 300 Hz summation). ⚠️ On Helix the virtual EQ **sums electrically** with the output EQ — account for both layers.
6. **Editing existing EQ → show a was→became table:** whenever you touch already-entered EQ, output ALL affected bands (channel **and** virtual) as a `freq | was → became | Q` table, so nothing is silently lost. **Keep it on disk:** the band set lives in the channel's export (`atf_eq.py` → the snapshot's `eq_ptr`), and any **gain** move that rides with an EQ change goes through `apply.propose` (never let a gain drift silently while only the EQ file changes — that's the split-artifact misread the state file exists to kill). Re-point `eq_ptr` when you re-export.

---

## 2b — Joint Phase Alignment (Fine Delay)
Align the relative phase response of the channels in their overlap regions.

### Refined Phase Flow
1. **Raw Sweep:** Capture the phase of the raw signals (after gross TA, before crossover filters) as a reference.
2. **Crossover Filters applied:** Compare with crossovers enabled to analyze phase rotation introduced purely by the filters.
3. **Fine Alignment:** Align joints in the following physical sequence:
   $$\text{Midbass (Reference)} \longrightarrow \text{Subwoofer} \longrightarrow \text{Midrange} \longrightarrow \text{Tweeter}$$
   Then, align Left ↔ Right for mono summation.
4. **Tools & Methods:**
   * Align joints using **All-pass filters (APF)** or Helix Phase controls rather than shifting raw channel delays, which can break the gross time arrival.
   * The sub-to-midbass joint (~60 Hz) yields the largest subjective SQ gain. Verify carefully.
   * The final verdict at any joint is determined by **SUMMATION** (uninverted vs. inverted polarity), not single-position phase values.
   * ⚠️ **Recurring mix-up (tripped twice — this skill and `manual_step-by-step`): summation ≠ "needs sweep."** The polarity/summation verdict is a **magnitude-only power-sum comparison** — `power-sum = 10·log10(10^(A/10)+10^(B/10))` vs the actual measured combined level, via **RTA/MMM** (`diagnostic-techniques.md §3, §9, §50`) — precisely *because* it's "a quick verdict without measuring phase" and avoids a single-mic-point combined **sweep** (comb-filtering from two spatially separate drivers, worse than the comb-filtering MMM/RTA exists to average out). **Sweep IS required**, but only for two *different* jobs at the joint: (a) Group Delay / phase rotation (`get_group_delay`, sweep-only — RTA has no phase key), and (b) the min- vs non-min-phase (excess-phase) decision on a dip. Don't let "phase is involved somewhere at this joint" generalize into "therefore evaluate the joint via sweep" — polarity/summation and GD/excess-phase are different questions with different required measurement types.

> **⚡ Compute all joints in one pass:** `python3 rew_tool.py analyze-joints --joint "sw,w-L,60,<pair>" --joint "w-L,m-L,400" --joint "m-L,tw-L,3000" …` renders one table (polarity · drift-immune delay · residual · APF) for every joint, reusing `joint_analysis.py`. It is **honest by construction** and matches the rule above: a computed delay/APF is emitted **only** when a measured `pair` reproduces the complex solos (`phase_trust_gate` ✓); no pair → **UNVERIFIED** (confirm by summation); gate trips → **BLOCK** (no delay — flip polarity + re-measure, the magnitude power-sum is the verdict). Use it to get the whole-joint picture in one shot, then confirm each by the actual measured summation before entering it.

> 🔍 **Critic checkpoint (1 of 2):** with the joints/polarity set, run a cross-vendor review round on the phase alignment **before** EQ — a falsifiable challenge of the joints, the alignment sequence, and the summation verdicts.

---

## 2c — Summed Curve Alignment
Align the summed acoustic groups to match the target.

### Verification Steps
Measure and analyze the MMM RTA of the following combinations:
* **Ws, Ms, TWs** (L+R sums of each band pair).
* **L vs. R** (full left side vs. full right side, excluding the subwoofer).
* **SW + Ws** (subwoofer plus both midbasses).

### Correction Rules
* **Band-to-band alignment:** Adjust levels so they sum smoothly. An overlap hump is a summation issue, not a hot driver.
* **L vs. R Balance (compare by FR):** overlay left-side vs right-side FR **level-normalized** (a level offset ≠ a shape difference — `analysis-playbook.md`) in the imaging region ($200\text{ Hz}$ to $1.5\text{ kHz}$). A pure **level tilt** → balance by level ("take from the louder side, add to the quieter", don't overboost); a **shape** difference → cabin/geometry, handle per side (don't force a clone). Use **MMM**, not a single point, for the HF part of this compare (a fixed-mic read above ~4 kHz is corrupted by the windshield reflection — `diagnostic-techniques.md`).
* **Summation Checks:** Use REW's trace arithmetic ($A+B$) to predict summation outcomes prior to applying changes.

---

## 2d — Final EQ to Target
Shape the technical response of the entire summed system — the `(rta)` of the summed groups vs the target — to the session's target curve.

### Rules of Action
* Apply **broad, smooth acoustic moves** (tilts, shelves, high/low Q shaping).
* Work primarily on the **Virtual Layer** (L=R linked, identical on both sides).
* Since the Virtual Layer sits above crossovers in the DSP routing chain, its phase shifts are identical for both sides, **never breaking the acoustic joints** set in Step 2b.
* Save client-preference voicing requests for Phase 5. This layer is purely technical target accuracy.

> 🔍 **Critic checkpoint (2 of 2):** with the EQ done, run a cross-vendor review round on the linearized + target-matched result **before** the Phase-3 lock.

Once the final curve is aligned and verified, transition to the **Phase 3** control gate.
