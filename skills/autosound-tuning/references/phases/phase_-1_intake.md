# Phase -1 — New Project & Setup Intake

This phase bootstraps a brand-new tuning project or a fresh system installation.

## 🎯 Goal-node

**Purpose:** bootstrap a brand-new project — workspace + language, equipment/goals interview, install verification, target-curve seed — so measurement can start safely on a known system.

**Questions this phase answers:** what's the car/drivers/DSP/mic rig? what are the goals (competition/enjoyment, reference seat, taste)? is the install safe and correct to measure?

**Required evidence:** the user interview (no guessing); driver `Fs` (datasheet/ask); routing · electrical polarity · gain · noise checks.

**✅ Quality gate → Phase 0:** language set; `autosound_context.md` (Engineering Profile) + `preference-profile.md` created; install verified + protective HPFs set for fragile drivers; a candidate target curve **seeded** (no default).

**⚠️ Failure modes:** skipping install verification (costs a session) · filing reference seat / competition format as a "preference" (they're engineering) · enforcing a default curve.

**🧩 Patterns / refs:** full flow → [`project-intake.md`](file:///skills/autosound-tuning/references/core/project-intake.md); curve→character → [`voicing-by-ear.md`](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md).

---

## Step-by-Step Runbook

For a comprehensive walkthrough, you **MUST** refer to and follow [project-intake.md](file:///skills/autosound-tuning/references/core/project-intake.md).

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
Audit the user's taste and map it to a target curve. Do **not** enforce a default curve. Present the curve-to-character mapping table in [voicing-by-ear.md](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md) to help them decide.

### 5. File & Workspace Creation
Create the baseline project files:
* `autosound_context.md` (reconciled single source of truth)
* `tuning-changelog` (session memory log)
* `dsp-state-current` (actual DSP register)

Once complete, the project is officially ready to transition to **Phase 0**.
