# AUDIOSYSTEM CONTEXT TEMPLATE (`autosound_context.md`)

Fill out this file with basic information about your system. It serves as your single source of truth (static context) for your AI assistant during each manual step in web chats. Copy its contents and paste them along with the corresponding step prompt.

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
*The `DSP Channel` column below is illustrative, not your real wiring — replace every cell with your own DSP's actual output channel numbers/letters. They don't have to be sequential or start at CH1: if your DSP has more physical outputs than speakers (e.g. a 12-channel unit driving 7 speakers), state the real, possibly non-adjacent channels used and list the rest as `None / Unused` rows.*
| DSP Channel | Speaker | Frequency Band | Amplifier | Physical Placement & Aiming |
| :--- | :--- | :--- | :--- | :--- |
| [e.g., CH1 (A)] | tw-L (Tweeter Left) | High (HF) | [Amp Model] | [e.g., A-pillars, aimed at cabin center] |
| [e.g., CH2 (B)] | tw-R (Tweeter Right) | High (HF) | [Amp Model] | [e.g., A-pillars, aimed at driver] |
| [e.g., CH3 (C)] | m-L (Midrange Left) | Middle (MF) | [Amp Model] | [e.g., A-pillars, coplanar with tweeter] |
| [e.g., CH4 (D)] | m-R (Midrange Right) | Middle (MF) | [Amp Model] | [e.g., A-pillars, coplanar with tweeter] |
| [e.g., CH5 (E)] | w-L (Woofer/Midbass L) | Low (LF) | [Amp Model] | [e.g., Doors, treated, stock locations] |
| [e.g., CH6 (F)] | w-R (Woofer/Midbass R) | Low (LF) | [Amp Model] | [e.g., Doors, treated, stock locations] |
| [e.g., CH7 (G)] | sw (Subwoofer) | Sub-bass (SUB) | [Amp Model] | [e.g., Sealed Box 35L in trunk] |

## 3. Measurement Equipment
* **Microphone:** [e.g., UMIK-1 (USB, 48 kHz) / Behringer ECM8000 (XLR)]
* **Timing Reference:** [e.g., Acoustic Timing Reference in REW / Physical Loopback cable (XLR)]

## 4. Current Settings & Target Curve

> [!IMPORTANT]
> **This file is the SINGLE SOURCE OF TRUTH for the live DSP state.** Each step's
> AI output is a COMPLETE regenerated copy of this whole file — save it as a
> **new version** (`autosound_context_v1.md` after Step 1, `_v2.md` after Step 2,
> `_v3.1.md` / `_v3.2.md` per Step 3 iteration) and feed the *latest* file into
> the next step. The chain of files is your history; the latest file is the
> truth. **Never hand-merge or partially edit sections.** The CURRENT DSP STATE
> block below always carries the full, live, **absolute** values — including any
> change a later step makes to a parameter an earlier step first set (e.g. a
> Step-3 delay or gain edit updates this block, not just the history log).

* **Target Curve:** [e.g., ResoNix Accurate / Audiofrog / Harman] — the actual curve DATA is uploaded each step as a REW text export (imported + LOCKED in REW; see the measurement guide), not inferred from this name.
* **Crossover Filter Scheme:** [e.g., a) All LR4 / b) BE4-LR4-BE4 (default) / c) BW2-LR4-BW2 / d) Own — describe]

### ✅ CURRENT DSP STATE (complete, absolute — the source of truth)
*<!-- Regenerated IN FULL every step. Every value here is the live ABSOLUTE setting currently in the DSP. Before Step 1 the delay/gain/EQ rows stay as placeholders. -->*
* **Crossovers (Crossovers Menu):**
  - **tw-L / tw-R:** HPF = [Placeholder] Hz LR4 | LPF = none
  - **m-L / m-R:** HPF = [Placeholder] Hz | LPF = [Placeholder] Hz
  - **w-L / w-R:** HPF = [Placeholder] Hz | LPF = [Placeholder] Hz
  - **sw:** HPF = 20 Hz BW2 | LPF = [Placeholder] Hz
* **Delays (Delay Menu) — absolute:**
  - tw-L: --- ms (--- samples) | tw-R: --- ms (--- samples)
  - m-L: --- ms (--- samples) | m-R: --- ms (--- samples)
  - w-L: --- ms (--- samples) | w-R: --- ms (--- samples)
  - sw: 0.00 ms (0 samples)
* **Gains (Gain Menu) — absolute:**
  - tw-L: --- dB | tw-R: --- dB
  - m-L: --- dB | m-R: --- dB
  - w-L: --- dB | w-R: --- dB
  - sw: --- dB
  - *Polarity (if any channel inverted):* [e.g., tw-R = Inverted]
* **Parametric EQ (Output PEQ) — absolute, ALL active bands per channel:**
  - **tw-L:** [No PEQ]
  - **tw-R:** [No PEQ]
  - **m-L:** [No PEQ]
  - **m-R:** [No PEQ]
  - **w-L:** [No PEQ]
  - **w-R:** [No PEQ]
  - **sw:** [No PEQ]
* **Micro-Delays & Phase (Helix Phase 0-360° / All-pass) — absolute:**
  - tw-L / tw-R: micro-delay = 0.00 ms (0 samples)
  - m-L / m-R: micro-delay = 0.00 ms (0 samples) | Helix Phase = 0°
  - w-L / w-R: micro-delay = 0.00 ms (0 samples)
  - sw: Helix Phase = 0°

### 📜 CHANGE HISTORY & RATIONALE (append-only)
*<!-- WHY each change was made. Every delay/gain/level/EQ change is written as DELTA + resulting ABSOLUTE, e.g. `w-R delay: 5.141 → 4.500 ms (−0.641 ms / −62 samples)`. Never overwrite earlier entries — append. -->*
#### [STEP 1] Baseline crossovers, delays & gains (v1)
*<!-- To be populated after Step 1: what was set and why. -->*
#### [STEP 2] Per-channel EQ & phase alignment (v2)
*<!-- To be populated after Step 2: EQ/phase decisions, each change as Δ + absolute. -->*
#### [STEP 3] Subjective fine-tuning iterations (v3+)
*<!-- To be populated during Step 3 listening loops. -->*
* **Iteration 1:**
  - *Subjective Feedback:* [Describe the initial listening impressions]
  - *Applied Micro-Corrections (Δ + resulting absolute):* [e.g., m-L EQ4: added 2500 Hz, −2.5 dB, Q=4.0; w-R delay: 5.141 → 4.500 ms (−0.641 ms / −62 samples)]

## 5. Channel and Measurement Naming Convention
* tw-L / tw-R (Tweeter L/R) · m-L / m-R (Midrange L/R) · w-L / w-R (Woofer L/R) · sw (Subwoofer).
* Suffixes: `(sw)` — sweep measurement on a tripod, `(rta)` — MMM RTA spatial average measurement around your head.

## 6. System Knowledge & Known Cabin Anomalies
* **Anomaly 1:** [e.g., a narrow, non-minimum-phase null on one channel caused by a physical reflection/diffraction path — do not attempt to boost it.]
* **Anomaly 2:** [e.g., a cabin resonance (room mode) peak at a specific frequency — cut with a narrow Q-factor filter.]
* **Notes & Observations:** [e.g., Bessel (BE4) crossovers sound smoother on the MF/HF transition than Linkwitz-Riley LR4.]
