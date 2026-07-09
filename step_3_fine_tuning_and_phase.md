# Step 3: Subjective Fine-Tuning & Listening Feedback

Use this template in a **new, clean chat session** after you have applied the settings from Step 2 (EQ, micro-delays, and Helix Phase angles) to your DSP, taken combined verification measurements, and evaluated the sound stage by ear.

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

I am at **Step 3: Subjective Fine-Tuning & Listening Feedback**.

My goal is to obtain subtle, highly targeted adjustments to EQ bands and channel levels based on my subjective listening feedback and combined verification measurements.

### ⚠️ Verification Gate:
* I confirm that all crossovers, per-channel EQ, micro-delays, and Helix Phase angles from Step 2 are fully applied to my DSP.

I am uploading the text exports of my combined MMM RTA measurements with 1/6 oct smoothing (L_3 rta, R_3 rta, ALL_3 rta as .txt / .csv files). Step 3 is subjective/tonal work in the RTA domain — no combined-side sweeps are needed (a sweep of two spatially separated sides at one fixed mic point suffers the comb-filtering MMM exists to average out). My locked target curve is included in the upload set for reference:
* *(Drag and drop your lightweight REW measurement text files directly into the chat)*

### 🎧 My Subjective Listening Feedback on Test Tracks:

1. **Staging & Imaging:**
   * *For example: Does the center image sit exactly in the center of the dash? Do certain vocal frequencies "pull" towards the left or right speaker? Is the image razor-sharp or blurry?*
   * **Your Feedback:** [Describe here]

2. **Stage Parameters:**
   * *For example: What is the height of the stage (at eye level, or does it drop)? What is the width (does it stretch beyond the A-pillars)? How is the depth and instrument separation?*
   * **Your Feedback:** [Describe here]

3. **Tonal Balance:**
   * *For example: Is there any harshness or glare in female vocals at high volumes? Do you hear too much sibilance ("s", "t", "sh" sounds)? Are high frequencies smooth? Is the bass punchy and well-integrated, or boomy?*
   * **Your Feedback:** [Describe here]

Please correlate my subjective complaints and observations with the provided measurement graphs, analyze them according to your system instructions, and output your recommendations in the defined structure:
1. 🔍 Correlation Audit (Subjective Feedback vs. Acoustic Curves)
2. 🎛️ Targeted EQ Adjustments Sheet (DSP Output EQ Updates)
3. 🔊 Targeted Level Adjustments Sheet (Gain Updates)
4. 🔄 Next Listening Plan (what to focus on after applying changes)
5. 📋 The COMPLETE regenerated passport (whole file, per your State Discipline protocol) — fold EVERY change from this iteration (including any gain/delay/EQ edit) into the CURRENT DSP STATE block, and append an Iteration entry to the [STEP 3] change history (each change as delta + absolute). I will save it as `autosound_context_v3.N.md`.

Here is my active system passport (paste the contents of my latest passport file — `autosound_context_v2.md` on the first Step-3 pass, or the previous iteration's `autosound_context_v3.N.md` on a repeat):
==================================================
<PASTE THE CONTENTS OF YOUR autosound_context.md FILE HERE>
==================================================
