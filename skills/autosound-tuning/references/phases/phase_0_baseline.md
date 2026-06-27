# Phase 0 — Baseline & Target Preparation

This phase establishes the raw baseline measurement of the car's current acoustic response and prepares the target curves for comparison.

## Core Objectives
1. **Name Channels & Set Conventions:** Align on standard channel tags and measurement file naming rules.
2. **Import Target Curve:** Load the chosen session target curve into Room EQ Wizard (REW).
3. **Capture Baseline:** Measure the uncorrected, current state of the vehicle (both via Loopback Sweeps and MMM RTA).
4. **Ensure Signal Hygiene:** Confirm gain settings and mic patterns are locked down.

---

## Step-by-Step Runbook

### 1. Agree on Naming Conventions (ONCE)
Before any measurements are taken, establish the channel abbreviations (`sw / w-L/R / m-L/R / tw-L/R / c / r`) and the file naming convention:
* Suffix **`(sw)`** = loopback sweep.
* Suffix **`(rta)`** = Multiple Mic Measurement (MMM) RTA.
* Suffix **`_N`** = configuration/measurement version (starts at `_1`, NOT "baseline").
* *Examples:* `m-L_1 (sw)`, `w-R_1 (rta)`.

Give the user copy-paste-ready specifics containing the exact save PATH, short comma-separated measurement names, and a brief explanation of the immediate goal. Follow the history hygiene details in [naming-and-structure.md](file:///skills/autosound-tuning/references/naming-and-structure.md).

### 2. Import Target Curve
Load the chosen house curve into REW.
* **The target curve defines only the SHAPE**, not the absolute level.
* Anchoring of curves and target levels is handled relative to the measured midrange level.
* **Do NOT generate per-band targets yet!** Per-band targets depend on the final acoustic crossovers and are generated in Phase 1 (Step 5b) after crossovers are finalized.

### 3. Capture the Baseline
Instruct the user to measure the current whole-system response.
* Capture `ALL_1 (sw)` and `ALL_1 (rta)`.
* This represents the **raw baseline** of the system.
* Do **NOT** perform time-alignment, delay adjustments, or level-matching yet. This phase is purely observational.

### 4. Gain Staging & Environmental Hygiene
* Check for clipping (DSP outputs vs. amplifier inputs). Measurements must remain clean and undistorted.
* Lock down a repeatable **MMM measurement pattern** (spatial boundaries, speed, volume coverage). Successive RTA tests must use this identical pattern to be comparable.

Once the baseline is saved, analyzed, and logged in the `tuning-changelog`, proceed to **Phase 1**.
