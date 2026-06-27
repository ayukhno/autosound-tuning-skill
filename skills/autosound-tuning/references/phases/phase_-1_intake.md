# Phase -1 — New Project & Setup Intake

This phase bootstraps a brand-new tuning project or a fresh system installation.

## Core Objectives
1. **Bootstrap the Project:** Set up the user environment, workspace directory structure, and language preferences.
2. **Collect Setup Context:** Run the equipment and goals interview.
3. **Verify the Installation:** Check speaker wiring, routing, electrical polarities, gain staging, safe sweep levels, and background noise.
4. **Choose the Target Curve:** Select the sonic house curve in alignment with the user's taste (no defaults!).

---

## Step-by-Step Runbook

For a comprehensive walkthrough, you **MUST** refer to and follow [project-intake.md](file:///skills/autosound-tuning/references/project-intake.md).

### 1. Welcome & Language Gate
Identify the user's preferred working language (EN/UK/DE/PL) at first contact. All subsequent dialogue and generated files must adhere to this preference, while the underlying skill instructions and protocol headers remain in English.

### 2. Equipment & Goals Interview
Collect details on:
* **The Vehicle:** Body style, cabin peculiarities, and speaker placement.
* **The Drivers:** Models, sizes, mounting locations, orientation, and manufacturer datasheets (specifically resonance frequencies, $F_s$).
* **The Amplification & DSP:** Channels, power, routing, and capabilities.
* **The Microphone Rig:** Models and maximum native sample rate (e.g., ECM8000 + Scarlett @ 96 kHz, or UMIK-1 @ 48 kHz).
* **The Goal:** Audio competition (EMMA, AYA) vs. daily enjoyment, musical taste, and listening habits.

### 3. Installation Verification & Safety Gate
* **Driver Protection:** Establish conservative **protective high-pass filters (HPFs)** for fragile drivers (tweeter and midrange) to prevent physical excursion damage during sweeps.
  > [!WARNING]
  > The protective HPF frequency is a function of the SPECIFIC driver's physical resonance ($F_s$) — do **not** use typical arbitrary frequencies. If $F_s$ is unknown, ask the user or look up the datasheet, and set it conservatively higher. Subwoofers and midbasses do not need protective HPFs.
* **Acoustic Integrity Check:** Verify routing (left/right channels aren't swapped), gain staging (no clipping on outputs), and ambient noise level.

### 4. Target Curve Selection
Audit the user's taste and map it to a target curve. Do **not** enforce a default curve. Present the curve-to-character mapping table in [voicing-by-ear.md](file:///skills/autosound-tuning/references/voicing-by-ear.md) to help them decide.

### 5. File & Workspace Creation
Create the baseline project files:
* `autosound_context.md` (reconciled single source of truth)
* `tuning-changelog` (session memory log)
* `dsp-state-current` (actual DSP register)

Once complete, the project is officially ready to transition to **Phase 0**.
