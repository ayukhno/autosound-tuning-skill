# AUDIOSYSTEM CONTEXT (`autosound_context.md`)

## 1. Hardware Configuration
* **Vehicle:** VW Passat B8, Sedan, LHD (Left-Hand Drive)
* **Head Unit (HU):** Android HU Isudar T72X via S/PDIF Optical output
* **DSP Processor:** Helix DSP Ultra S (Native 96 kHz sample rate, Helix BT HD, Helix Conductor)
* **Amplifiers:**
  - Ground Zero GZPA 4SQ -> powering Midrange and Tweeter (MF/HF)
  - Ground Zero GZA 125.4 -> powering Midbass (LF)
  - Audison SR 1.500 -> powering Subwoofer (SUB)

## 2. Channel Map (Wiring & Routing)
| DSP Channel | Speaker | Frequency Band | Amplifier | Physical Placement & Aiming |
| :--- | :--- | :--- | :--- | :--- |
| CH1 (A) | tw-L (Tweeter Left) | High (HF) | GZPA 4SQ | A-pillars, aimed to the center between seats |
| CH2 (B) | tw-R (Tweeter Right) | High (HF) | GZPA 4SQ | A-pillars, aimed directly at driver's head |
| CH3 (C) | m-L (Midrange Left) | Middle (MF) | GZPA 4SQ | A-pillars, coplanar with tweeter, aimed to center |
| CH4 (D) | m-R (Midrange Right) | Middle (MF) | GZPA 4SQ | A-pillars, coplanar with tweeter, aimed at driver |
| CH5 (E) | w-L (Woofer/Midbass L) | Low (LF) | GZA 125.4 | Front doors, treated, stock locations |
| CH6 (F) | w-R (Woofer/Midbass R) | Low (LF) | GZA 125.4 | Front doors, treated, stock locations |
| CH7 (G) | sw (Subwoofer) | Sub-bass (SUB) | Audison SR 1.500 | GZUW-10SQ-D2 in Sealed Box 35L in trunk, rear-firing |

## 3. Measurement Equipment
* **Microphone:** Behringer ECM8000 (XLR) with 0-degree and 90-degree calibration files
* **Audio Interface:** Focusrite Scarlett 2i2 (4th Gen)
* **Timing Reference:** Physical Loopback cable (XLR)

## 4. Current Settings & Target Curve (Current DSP State)
* **Target Curve:** Audiofrog
* **Crossover Filter Scheme:** a) All LR4 (Linkwitz-Riley 24 dB/oct everywhere)

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
* **Anomaly 1:** Left-side A-pillar aiming is off-axis (to the center) while the right-side is on-axis (directly at the driver). This physical configuration will lead to a distinct high-frequency roll-off on the left channel due to driver directivity. Precise left/right asymmetric high-frequency EQ will be necessary to meet the Audiofrog target curve.
* **Anomaly 2:** Rear-firing trunk-mounted subwoofers in sedan configurations face cabin decoupling, loading effects from the trunk lid, and severe path-length delays. This will require precise phase manipulation to ensure correct summation across the crossover band.