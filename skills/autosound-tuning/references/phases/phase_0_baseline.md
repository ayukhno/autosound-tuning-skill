# Phase 0 — Baseline & Target Preparation

This phase establishes the raw baseline measurement of the car's current acoustic response and prepares the target curves for comparison.

## 🎯 Goal-node

**Purpose:** capture the raw, uncorrected baseline and prepare the target — so tuning starts from measured reality, not assumptions.

**Questions this phase answers:** what channel names/conventions do we agree? what does the system currently do (raw)? is the signal chain clean (no clipping)?

**Required evidence:** agreed naming/glossary; a clean base DSP profile (`v0`, zeroed modifiers); **per-driver** `<ch>_1 (sw)` + `<ch>_1 (rta)` for each driver we'll work with; a locked, repeatable MMM pattern.

**✅ Quality gate → Phase 1:** names agreed **before** measuring; target curve imported (shape only, not level); raw baseline captured with all modifiers zeroed; no clipping; MMM pattern locked.

**⚠️ Failure modes:** measuring before names are agreed (unusable history) · generating per-band targets now (they depend on Phase-1 crossovers) · applying TA/level tricks during the baseline (stay observational).

**🧩 Refs:** naming/history → [`naming-and-structure.md`](file:///skills/autosound-tuning/references/core/naming-and-structure.md).

---

## Step-by-Step Runbook

### 1. Agree on Naming Conventions (ONCE)
Before any measurements are taken, establish the channel abbreviations (`sw / w-L/R / m-L/R / tw-L/R / c / r`) and the file naming convention:
* Suffix **`(sw)`** = loopback sweep.
* Suffix **`(rta)`** = Multiple Mic Measurement (MMM) RTA.
* Suffix **`_N`** = configuration/measurement version (starts at `_1`, NOT "baseline").
* *Examples:* `m-L_1 (sw)`, `w-R_1 (rta)`.

Give the user copy-paste-ready specifics containing the exact save PATH, short comma-separated measurement names, and a brief explanation of the immediate goal. Follow the history hygiene details in [naming-and-structure.md](file:///skills/autosound-tuning/references/core/naming-and-structure.md).

### 2. Import Target Curve
Load the chosen house curve into REW.
* **The target curve defines only the SHAPE**, not the absolute level.
* Anchoring of curves and target levels is handled relative to the measured midrange level.
* **Do NOT generate per-band targets yet!** Per-band targets depend on the final acoustic crossovers and are generated in Phase 1 (Step 5b) after crossovers are finalized.

### 2.5 Prepare the Base DSP Profile (Arbiter)
Before taking raw baseline measurements, prepare the clean starting preset in Helix PC-Tool:
* **Clean Baseline Profile:** Start with a clean/reset preset in Helix PC-Tool (representing version `v0`).
* **Basic Configuration Only:** Configure the input-to-output routing matrix (Input/Output Matrix) and assign correct output names (`tw-L/R`, `m-L/R`, `w-L/R`, `sw`) according to the glossary.
* **Zero Acoustic Modifiers:** Ensure all acoustic modifiers are cleared: all delays set to exactly `0 ms / 0 cm / 0 samples`, all polarities set to NORM, all output EQs flat (bypass/0 dB), and initial output gains set to 0 dB (with protective crossovers applied to ВЧ/СЧ as described in Phase 1).
* This forms the "pure routing preset" baseline from which all subsequent acoustic tuning is built.

### 3. Capture the Baseline (per-driver)
Instruct the user to measure **each driver we'll work with**, solo, on the clean `v0` profile (protective HPFs on fragile drivers; no TA/EQ):
* For every front channel — `sw`, `w-L/R`, `m-L/R`, `tw-L/R` — capture `<ch>_1 (sw)` (loopback sweep → IR/phase/GD) **and** `<ch>_1 (rta)` (MMM). *(Center/rear are integrated later, Phase 4.)*
* This per-driver set **is** the raw baseline **and** the input for Phase 1 (TA, crossovers, levels, per-band targets) — **Phase 1 does not re-collect it.**
* Do **NOT** perform time-alignment, delay, or level-matching yet. This phase is purely observational.

### 4. Gain Staging & Environmental Hygiene
* Check for clipping (DSP outputs vs. amplifier inputs). Measurements must remain clean and undistorted.
* Lock down a repeatable **MMM measurement pattern** (spatial boundaries, speed, volume coverage). Successive RTA tests must use this identical pattern to be comparable.

Once the baseline is saved, analyzed, and logged in the `tuning-changelog`, proceed to **Phase 1**.
