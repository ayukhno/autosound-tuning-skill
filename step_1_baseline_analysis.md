# Step 1: Baseline Analysis (Crossovers & Delays)

Use this template in a **new, clean chat session** after you have taken your first baseline measurements of speakers without crossovers or EQ (with temporary safe HPFs enabled to protect your tweeters and midranges).

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

I am at **Step 1: Baseline Analysis (Crossovers & Delays)**.

My goal is to obtain baseline crossover recommendation points, initial gain levels, and exact time-alignment delays (in ms and digital samples) calculated from the impulse response peaks of my speakers.

I am uploading the text exports of my baseline measurements using optimized 24 PPO resolution and 1/6 or 1/12 oct smoothing (.txt or .csv files).

Please analyze these measurements according to your system instructions and output your recommendations in the defined structure:
1. 🔍 Acoustic Analysis Summary
2. 🔧 Crossover Recommendations (DSP Software Crossovers Menu)
3. ⏱️ Time Alignment Sheet (DSP Software Delay Menu)
4. 🔊 Initial Gain/Level Sheet (DSP Software Gain Menu)
5. 📋 The COMPLETE regenerated passport (whole file, per your State Discipline protocol) with the CURRENT DSP STATE block filled in and a [STEP 1] change-history entry — I will save it as `autosound_context_v1.md`.

Here is my static system passport (the contents of my base `autosound_context.md` file after Step 0):
==================================================
<PASTE THE CONTENTS OF YOUR autosound_context.md FILE HERE>
==================================================

* *(Drag and drop your lightweight REW measurement text files directly into the chat)*
