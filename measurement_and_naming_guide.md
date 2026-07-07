# Measurement, Naming & Action Guide

This manual is your practical guide to taking professional acoustic measurements in a car cabin using **REW (Room EQ Wizard)**. It explains in detail **how to measure, how to name, and how to proceed** so that your manual AI companion in a web chat receives clean data and outputs accurate calculations.

---

## 1. 📊 HOW TO MEASURE: REW Measurement Techniques

To calibrate a digital sound processor (DSP), two completely different types of measurements are used. They are never interchangeable:

*   **Acoustic Sweep Method:** Used **strictly to measure arrival times, impulse responses, phase curves, and distortion**.
*   **MMM RTA (Moving Microphone Measurement / Spatial Averaging):** Used **strictly to measure amplitude (frequency response) and tonal balance**.

---

### Method A: Single Sweeps — `(sw)` (for Time & Phase)

A sweep measurement plays a short, rising sine wave (sine sweep) to determine the exact microsecond the sound arrives from the speaker to the microphone.

#### 🔧 Physical Setup:
1.  **Microphone:** Must be fixed on a tripod or mount in a single point—**at the nose/ear level of the listener** in their usual driving position.
2.  **Orientation:** Point the microphone capsule **straight up (towards the ceiling, at a 90° angle)** and be sure to load the corresponding $90^\circ$ calibration file in REW. This minimizes the influence of reflections from the windshield.
3.  **Hardware Timing (Timing Reference) — CRITICAL:**
    *   **For XLR Microphones (ECM8000 + Scarlett 2i2):** Use a **physical loopback cable**. Connect Output 2 of your sound card to Input 2. In REW settings, select `Use loopback as timing reference` (Input 2). This provides sample-accurate timing precision.
    *   **For USB Microphones (UMIK-1):** Because USB has floating digital lag, a physical loopback is impossible. Use `Acoustic timing reference`. REW will play a short "chirp" from a designated reference speaker (usually the right tweeter) as a start time reference, followed by the sweep from the speaker being measured.

#### 🎛️ REW Settings (Measure Window):
*   **Type:** `Sweep`
*   **Sample Rate:** Matches your mic/card (for Scarlett/ECM8000, **96 kHz** or **48 kHz** depending on your DSP's native rate is recommended; for UMIK-1, **48 kHz**).
*   **Length:** `256k` or `512k`
*   **Sweeps:** `1`
*   **Range:** Set a safe starting lower limit for tweeters and midranges (e.g., 300–20,000 Hz) to prevent damaging them with low frequencies.

---

### Method B: MMM RTA — `(rta)` (for Frequency Response & Tonal Balance)

A standard sweep in a single point is heavily distorted by local reflections from the glass, steering wheel, and dashboard (comb filtering). The brain ignores these micro-dips, but the AI might pointlessly try to boost them. The MMM method averages the frequency response in a 3D space around your head, providing a realistic picture of what you actually hear.

#### 🔧 Physical Setup:
1.  Turn on the noise generator in your DSP and play **Pink Noise**.
2.  Sit in the driver's seat in your normal driving position. Hold the microphone in your hand at arm's length (to minimize sound reflecting off your body near the capsule).
3.  Start slowly and continuously tracing a "figure-eight" or circular path in the air directly around your head and ears (zone diameter ~20-30 cm). Speed of movement: about one full loop every 2-3 seconds.

#### 🎛️ REW RTA Settings (RTA Window):
*   **Mode:** `RTA 1/48 oct` (or 1/24)
*   **Averages:** `150` or `Forever` (it is convenient to set an autostop after **150 averages** have accumulated—this automatically stops the measurement and freezes the curve).
*   **Update:** `Every update`
*   **Window:** `Hann`
*   **Max Overlap:** `93.75%`
*   **FFT Length:** Set to **64k** or **128k** for high resolution in the mid and low frequencies.
*   **How to Measure:** Click `Reset Average` in the RTA window, start moving the microphone around your head, and once the counter hits 150, the measurement stops. Click `Save` to transfer the curve to REW's main window.

---

### ⚠️ PRE-SWEEP SAFETY GATE

> [!CAUTION]
> A single full-range sweep without a filter played through a tweeter or midrange driver will instantly destroy it (burn the coil or tear the cone). **No exceptions to this safety rule!**

1.  **Always Double-Check Filters (HPF):** Before measuring any tweeter or midrange, make sure a safe high-pass filter (HPF) is active in your DSP:
    *   **For Tweeters (HF):** HPF not lower than 1000–2000 Hz (usually at least $1.1 \times F_s$ of the driver, e.g., 1500 Hz), with a slope of 24 dB/oct (e.g., LR4).
    *   **For Midranges (MF):** HPF not lower than 100–300 Hz (usually at least $1.1 \times F_s$ of the driver, e.g., 200 Hz), with a slope of 24 dB/oct (e.g., LR4).
2.  **Start at Low Volume:** Start your measurements with the amplifiers' volume turned down low, and gradually raise it to a level where the signal clearly rises above the cabin's noise floor (AC, street noise, etc.).
3.  **Listen for Distortion:** If you hear any crackling, scratching, or clicking during a sweep—stop immediately! Either the signal is clipping, or the driver is exceeding its physical excursion limit.

---

## 🏷️ 2. HOW TO NAME: Naming Conventions & Hygiene in REW

Measurement lists in REW are easy to accidentally sort or mix up. **List index ("measurement #5") means nothing.** Only the name serves as a stable identifier.

Use this naming formula:
$$\mathbf{\langle channel\_code \rangle\_ \langle dsp\_version \rangle \ (\langle method \rangle)}$$

### Name Components:
1.  **Channel Code:**
    *   `tw-L` / `tw-R` — Tweeter Left / Right
    *   `m-L` / `m-R` — Midrange Left / Right
    *   `w-L` / `w-R` — Woofer/Midbass Left / Right
    *   `sw` — Subwoofer
    *   `L` / `R` — Full Left / Right side combined (`tw` + `m` + `w` playing together)
    *   `ALL` — Full front stage (excluding rear/center)
    *   `L w+m` — Left midbass + midrange crossover summation check
    *   `R m+tw` — Right midrange + tweeter crossover summation check
    *   `SW+Ws` — Subwoofer + both midbasses summation check
2.  **DSP Version (`_N`):**
    *   `_1` — Baseline measurements (taken on clean `v0` DSP config without delays or EQ).
    *   `_2` — Measurements taken on `v1` config (after applying Step 1 crossovers and delays).
    *   `_3` — Measurements taken on `v2` config (after applying Step 2 per-channel EQ).
    *   `_final` — Final verification measurements after Step 3 phase alignment.
3.  **Measurement Method:**
    *   `(sw)` — Sweep on tripod.
    *   `(rta)` — MMM RTA moving microphone.

### 📝 Examples of Correct Names:
*   `tw-L_1 (sw)` — Left tweeter, baseline sweep on a tripod to determine arrival time.
*   `w-R_2 (rta)` — Right midbass, measured with MMM on the `v1` DSP configuration (crossovers/delays active) to calculate EQ.
*   `L w+m_2 (rta)` — Summed frequency response of the left midbass and midrange to check crossover summation.

---

## 🏃 3. HOW TO PROCEED: Step-by-Step Action Protocol

Follow this sequence to ensure your tuning session progresses smoothly and safely:

```
[ v0 in DSP ] ──► [ Measurements _1 ] ──► [ Step 1 Chat ] ──► [ v1 in DSP ]
                                                                   │
[ Measurements _3 ] ◄── [ Step 2 Chat ] ◄── [ Measurements _2 ] ◄──┘
    │
    └──► [ Step 3 Chat ] ──► [ Final in DSP ]
```

### Step 0: Preparation & Baseline Point (`v0`)
1.  **Create Preset:** Open your DSP software and create a clean preset (`v0`).
2.  **Reset Modifiers:** Ensure all delays = `0 ms`, EQ = `flat` (0 dB), gains = `0 dB`, and polarities = `NORM`.
3.  **Protect Drivers:** Set up temporary safe crossover filters (HPF) for tweeters and midranges (see safety section).
4.  **Create Context:** This is automated in Step 0 using AI. You can also fill out the local `autosound_context_template.md` manually and save it as `autosound_context.md` in your project folder. No absolute file paths are required.

### Step 1: Baseline Measurements (`_1`) & Core Calculations
1.  **Measurement Session (Compact Checklist):**
    *   **Single sweeps on tripod** (for impulse and delays):
        *   `tw-L_1 (sw)`, `tw-R_1 (sw)` (range 1000–20,000 Hz)
        *   `m-L_1 (sw)`, `m-R_1 (sw)` (range 100–20,000 Hz)
        *   `w-L_1 (sw)`, `w-R_1 (sw)` (range 20–20,000 Hz)
        *   `sw_1 (sw)` (range 20–200 Hz)
    *   **MMM RTA measurements around head** (for baseline frequency response and crossover points):
        *   `tw-L_1 (rta)`, `tw-R_1 (rta)`
        *   `m-L_1 (rta)`, `m-R_1 (rta)`
        *   `w-L_1 (rta)`, `w-R_1 (rta)`
        *   `sw_1 (rta)`
2.  **Hardware Timing (Timing Reference):** If you use an XLR mic with a loopback setup, make sure you configure your loopback correctly to get sample-accurate impulse and phase measurements.
3.  **Step 1 Chat:** Open a clean chat session. Paste `general_system_instructions.md` into System Instructions, send your `autosound_context.md`, upload your REW `.txt`/`.csv` export files (24 PPO, 1/6 oct), and paste the `step_1_baseline_analysis.md` prompt.
4.  **Result:** The AI will calculate crossover points, slopes, delays, and baseline level asymmetry.
5.  **DSP Entry:** Apply these parameters to your DSP and save the preset as `v1`. Copy the AI's copy-paste block to replace the Step 1 section in your local `autosound_context.md`. Close the chat.

### Step 2: Tonal Balance, Channel EQ & Crossover Fine-Tuning (`_2`)
1.  **DSP Verification:** Before measuring, confirm that all Step 1 (`v1`) settings are active in your DSP!
2.  **Measurement Session (Compact Checklist):**
    *   **MMM RTA measurements around head** (for per-channel PEQ calculation):
        *   `tw-L_2 (rta)`, `tw-R_2 (rta)`, `m-L_2 (rta)`, `m-R_2 (rta)`, `w-L_2 (rta)`, `w-R_2 (rta)`, `sw_2 (rta)`
    *   **Single sweeps on tripod** (for phase curves and micro-delays):
        *   `tw-L_2 (sw)`, `tw-R_2 (sw)`, `m-L_2 (sw)`, `m-R_2 (sw)`, `w-L_2 (sw)`, `w-R_2 (sw)`, `sw_2 (sw)`
        *   **Summation sweeps:** `L w+m_2 (sw)`, `R w+m_2 (sw)`, `L m+tw_2 (sw)`, `R m+tw_2 (sw)`, `SW+Ws_2 (sw)`
3.  **Step 2 Chat:** Open a clean chat session. Upload your REW exports, paste your updated `autosound_context.md`, and copy the `step_2_tonal_balance_eq.md` prompt.
4.  **Result:** The AI will calculate precise PEQ bands, micro-delays, and Helix Phase rotation angles.
5.  **DSP Entry:** Apply the PEQ bands, micro-delays, and phase settings to your DSP, then save as `v2`. Update your local `autosound_context.md` with the AI's copy-pasteable block. Close the chat.

### Step 3: Subjective Fine-Tuning & Listening Loops (`_3`)
1.  **Measurement Session:** With Step 2 (`v2`) settings active, measure:
    *   **MMM RTA around head:** `L_3 (rta)` (full left), `R_3 (rta)` (full right), `ALL_3 (rta)` (full front stage + sub)
    *   **Single sweeps on tripod:** `L_3 (sw)`, `R_3 (sw)`, `ALL_3 (sw)`
2.  **Listening Auditing:**
    *   Sit in the driver's seat in your normal listening position.
    *   Play high-quality test tracks (e.g., AYA, EMMA, Focal evaluation discs, or your favorite reference songs).
    *   Evaluate stage width, height, depth, center image focus, sibilance, and sub/bass integration.
3.  **Step 3 Chat:** Open a clean chat session. Copy the `step_3_fine_tuning_and_phase.md` prompt, attach your updated `autosound_context.md` file, upload combined measurements, and describe your listening feedback in detail.
4.  **Result:** The AI will analyze the graphs against your feedback and recommend subtle level or EQ adjustments.
5.  **Iteration:** Repeat this listening loop until you are completely satisfied with the sound stage and tonal balance. Save your final DSP preset!
