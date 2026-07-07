# YOUR SYSTEM PASSPORT (`autosound_context.md`)

This is your **live, working passport** — it starts as a blank copy of `autosound_context_template.md` and gets updated after every step. Two ways to fill it in:

* **Path 1 (AI-guided, recommended):** Copy `step_0_intake_and_setup.md`'s prompt into a new chat, pasting the contents of `autosound_context_template.md` (the pristine copy) where indicated. The AI will interview you and generate a fully populated Markdown block — **replace this entire file's contents** with that block.
* **Path 2 (Manual quick start):** Already know your gear? Replace the `[Placeholder]` fields below yourself with your real hardware/measurement details, then delete this note.

After Step 0, this file holds your equipment + a blank Step 1/2/3 structure. After each later step, paste the AI's returned block over that step's section in this same file — never in the template.

---

# PROJECT CONTEXT: AUDIOSYSTEM CALIBRATION

## 1. Hardware Configuration
* **Vehicle:** [e.g., VW Passat B8, Sedan, 2018, LHD (Left-Hand Drive)]
* **Head Unit (HU):** [e.g., Stock HU / Android HU Isudar T78 via S/PDIF Optical output]
* **DSP Processor:** [e.g., Helix DSP Ultra S, native 96 kHz sample rate]
* **Amplifiers:**
  - [e.g., Ground Zero GZPA 4SQ -> for MF/HF]
  - [e.g., Ground Zero GZA 125.4 -> for LF]
  - [e.g., Audison SR 1.500 -> for Subwoofer]

## 2. Channel Map (Wiring & Routing)
| DSP Channel | Speaker | Frequency Band | Amplifier | Physical Placement & Aiming |
| :--- | :--- | :--- | :--- | :--- |
| CH1 (A) | tw-L (Tweeter Left) | High (HF) | [Amp Model] | [e.g., A-pillars, aimed at cabin center] |
| CH2 (B) | tw-R (Tweeter Right) | High (HF) | [Amp Model] | [e.g., A-pillars, aimed at driver] |
| CH3 (C) | m-L (Midrange Left) | Middle (MF) | [Amp Model] | [e.g., A-pillars, coplanar with tweeter] |
| CH4 (D) | m-R (Midrange Right) | Middle (MF) | [Amp Model] | [e.g., A-pillars, coplanar with tweeter] |
| CH5 (E) | w-L (Woofer/Midbass L) | Low (LF) | [Amp Model] | [e.g., Doors, treated, stock locations] |
| CH6 (F) | w-R (Woofer/Midbass R) | Low (LF) | [Amp Model] | [e.g., Doors, treated, stock locations] |
| CH7 (G) | sw (Subwoofer) | Sub-bass (SUB) | [Amp Model] | [e.g., Sealed Box 35L in trunk] |

## 3. Measurement Equipment
* **Microphone:** [e.g., UMIK-1 (USB, 48 kHz) / Behringer ECM8000 (XLR)]
* **Timing Reference:** [e.g., Acoustic Timing Reference in REW / Physical Loopback cable (XLR)]

## 4. Current Settings & Target Curve (Current DSP State)
* **Target Curve:** [e.g., ResoNix Accurate / Audiofrog / Harman]

### ⏱️ [STEP 1] Crossovers, Delays & Gains (v1)
*<!-- To be populated after completing Step 1 from the AI's copy-paste block -->*
* **Crossovers (Crossovers Menu):**
  - **tw-L / tw-R:** HPF = [Placeholder] Hz LR4 | LPF = none
  - **m-L / m-R:** HPF = [Placeholder] Hz | LPF = [Placeholder] Hz
  - **w-L / w-R:** HPF = [Placeholder] Hz | LPF = [Placeholder] Hz
  - **sw:** HPF = 20 Hz BW2 | LPF = [Placeholder] Hz
* **Delays (Delay Menu):**
  - tw-L: --- ms (--- samples) | tw-R: --- ms (--- samples)
  - m-L: --- ms (--- samples) | m-R: --- ms (--- samples)
  - w-L: --- ms (--- samples) | w-R: --- ms (--- samples)
  - sw: 0.00 ms (0 samples)
* **Initial Gains (Gain Menu):**
  - tw-L: --- dB | tw-R: --- dB
  - m-L: --- dB | m-R: --- dB
  - w-L: --- dB | w-R: --- dB
  - sw: --- dB

### 🎛️ [STEP 2] Per-Channel EQ & Phase Alignment (v2)
*<!-- To be populated after completing Step 2 from the AI's copy-paste block -->*
* **Parametric EQ (Output PEQ):**
  - **tw-L:** [No PEQ]
  - **tw-R:** [No PEQ]
  - **m-L:** [No PEQ]
  - **m-R:** [No PEQ]
  - **w-L:** [No PEQ]
  - **w-R:** [No PEQ]
  - **sw:** [No PEQ]
* **Micro-Delays & Phase Controls (Helix Phase 0-360° / All-pass):**
  - tw-L / tw-R: micro-delay = 0.00 ms (0 samples)
  - m-L / m-R: micro-delay = 0.00 ms (0 samples) | Helix Phase = 0°
  - w-L / w-R: micro-delay = 0.00 ms (0 samples)
  - sw: Helix Phase = 0°

### 🎧 [STEP 3] Subjective Fine-Tuning & Iterations Log (v3+)
*<!-- To be populated during Step 3 listening loops -->*
* **Iteration 1:**
  - *Subjective Feedback:* [Describe the initial listening impressions]
  - *Applied Micro-Corrections:* [List any adjustments to EQ or level settings]

## 5. Channel and Measurement Naming Convention
* tw-L / tw-R (Tweeter L/R) · m-L / m-R (Midrange L/R) · w-L / w-R (Woofer L/R) · sw (Subwoofer).
* Suffixes: `(sw)` — sweep measurement on a tripod, `(rta)` — MMM RTA spatial average measurement around your head.

## 6. System Knowledge & Known Cabin Anomalies
* **Anomaly 1:** [e.g., Left woofer dip at ~150 Hz due to floor reflections/door-card cancellation — EQ boost forbidden!]
* **Anomaly 2:** [e.g., Cabin resonance peak at ~190 Hz — cut with a narrow Q-factor filter.]
* **Notes & Observations:** [e.g., Bessel (BE4) crossovers sound smoother on the MF/HF transition than Linkwitz-Riley LR4.]
