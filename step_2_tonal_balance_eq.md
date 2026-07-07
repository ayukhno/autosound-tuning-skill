# Step 2: Tonal Balance, Channel EQ & Phase Alignment

Use this template in a **new, clean chat session** after you have applied the crossovers and delays from Step 1 into your DSP and taken a new round of measurements.

---

### 📋 Prerequisite Action:
Ensure that you have copied the contents of **[step_-1_general_system_instructions.md](step_-1_general_system_instructions.md)** and pasted it into the **System Instructions** box of this new chat.

---

### 💡 Data Upload Format (AI Studio Token Optimization):
To prevent hitting chat input token limits (the `exceeds the maximum number of tokens` error) when uploading high-resolution measurements, adjust your export settings in REW as follows:

1. **Apply Smoothing in REW:**
   - Go to your measurement's graph page and apply **1/6 oct** smoothing (or maximum **1/12 oct** for sweeps): `Graph -> Apply 1/6 smoothing`.
2. **Configure REW Text Export Window (`File -> Export -> Export measurement as text`):**
   - 🔘 **Resolution:** Select `Use custom resolution` and set it to **24 PPO** (Points Per Octave) — this is the ideal compromise between accuracy and data size.
   - 🔘 **Smoothing:** Select `Use smoothing of measurement: 1/6 octave` (or `1/12 octave`).
   - 📄 Save the file. Each speaker's measurement will now take only ~200–300 lines of text, allowing the AI to easily process all of them together!
3. **Upload the Files:**
   - Drag and drop your lightweight `.txt` or `.csv` export files directly into your Google AI Studio chat window.

---

### 💬 Copy-Paste Prompt:
👉 **Copy the entire text below (everything after the divider line `--------------------------------------------------`):**

--------------------------------------------------

I am at **Step 2: Tonal Balance, Channel EQ & Phase Alignment**.

My goal is to obtain calculated per-channel parametric EQ (PEQ) filters matching my target curve, as well as micro-delays and phase rotation angles (Helix Phase) at the crossover summation points.

### 🎯 Target Curve Selection:
Please specify which target curve to use for the PEQ calculation (leave one or describe your preferences):
* **Target Curve:** [ResoNix Accurate (Default / Flat SQ) | Harman Car Target (Bass Boost) | Audiofrog (Smooth HF Roll-off) | Jazzi | Custom (describe: e.g., smooth treble roll-off -3dB and sub-bass boost +6dB)]

### ⚠️ Verification Gate:
* I confirm that all baseline crossovers, delays, and initial gains from Step 1 are fully activated in my DSP processor.

I am uploading the text exports of my new measurements in optimized 24 PPO resolution and 1/6 or 1/12 oct smoothing (individual RTA for each speaker, RTA of each crossover pair for the summation check, and individual per-channel sweeps as .txt / .csv files):
* *(Drag and drop your lightweight REW measurement text files directly into the chat)*

### 🔧 Joint Phase Values (optional — only if you already suspect a problem):
Leave this section blank on your first pass. Diagnose each joint's summation health from my RTA measurements (measured pair level vs. the power-sum of the two individual levels) first, and tell me exactly which joint(s), if any, need a phase reading before I go back to REW for it.

If you already suspect a specific joint (e.g. from a prior audit, or you're replying with the values I asked for), here are the exact phase values in degrees (read from the Phase tab in REW, on the two **individual** driver sweeps, at the crossover frequency):
* **MF/HF Crossover (at [Specify crossover frequency, e.g., 3500 Hz]):**
  - m-L Phase = [Value]° | tw-L Phase = [Value]°
  - m-R Phase = [Value]° | tw-R Phase = [Value]°
* **LF/MF Crossover (at [Specify crossover frequency, e.g., 300 Hz]):**
  - w-L Phase = [Value]° | m-L Phase = [Value]°
  - w-R Phase = [Value]° | m-R Phase = [Value]°
* **SUB/LF Crossover (at [Specify crossover frequency, e.g., 60 Hz]):**
  - sw Phase = [Value]° | Ws (sum of midbasses) Phase = [Value]°

Please analyze these measurements and any phase values according to your system instructions and output your recommendations in the defined structure:
1. 🔍 Acoustic Analysis & Crossover Summation Audit
2. 🎛️ Per-Channel Parametric EQ Sheet (DSP Output EQ)
3. ⏱️ Micro-Delays & Phase Rotation Sheet (Helix Phase & All-Pass)
4. 🔊 Gain/Level Fine-Tuning Sheet
5. 📋 Code Block for direct copy-pasting into `autosound_context.md`

Here is my active system passport (the contents of my `autosound_context.md` file updated with Step 1 values):
==================================================
<PASTE THE CONTENTS OF YOUR autosound_context.md FILE HERE>
==================================================
