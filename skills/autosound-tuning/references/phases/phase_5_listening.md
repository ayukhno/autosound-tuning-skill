# Phase 5 — Targeted Listening (Ear Verification)

This is the penultimate phase. While physical measurements verify technical correctness, the human ear is the ultimate judge of acoustic reproduction, soundstage depth, and natural voicing.

---

## Core Guidelines
* **On-Demand Ear Checks:** Listening checks are not just restricted to this phase — they are a cross-cutting diagnostic tool. Use them during crossover selection, time-alignment, and joint phasing to cross-check measurement anomalies.
* **Curated Diagnostic Tracks:** Always refer to the index in [test-tracks.md](file:///skills/autosound-tuning/references/test-tracks.md) to pick the exact track tailored to expose specific acoustic traits (e.g., soundstage depth, lateral focus, midbass punch, or vocal sibilance).
* **Hypothesis-Driven Instruction:** Do **not** dump a long, overwhelming list of songs on the user. Propose **one track at a time**, instructing the user exactly:
  1. **What song** to play.
  2. **At what timecode** (timestamp) to focus their attention.
  3. **What specific binary auditory marker** to listen for (e.g., "Is the upright bass localized centered on the dashboard, or does it drift left below 50 Hz?").

---

## The Standard Listening Pass Runbook
When performing a final verification of a newly finished tune or preparing for an SQ competition, guide the Arbiter through the following systematic, standardized pass:

### 1. Tonal Balance & Spectral Integration
* **Check:** Subwoofer-to-midbass blending, low-end extension, and presence/treble glare.
* **Symptom fix:** If the low bass drags behind or localizes in the trunk, re-verify sub-to-midbass phase alignment.

### 2. Mono-Center Soundstage Focus
* **Check:** Centering, phantom focus size, and height stability across the entire frequency range.
* **Symptom fix:** Focus drift usually points to level differences or asymmetrical phase rotation at a joint.

### 3. Soundstage Lateral Localization
* **Check:** Left, Center-Left, Center, Center-Right, and Right positions (e.g., using EMMA/AYA acoustic localization tracks).
* **Symptom fix:** If horizontal positions are squished together, adjust level balance or crossover slopes in the midrange overlap region.

### 4. Soundstage Depth & Layering (Echelons)
* **Check:** Front-to-back depth, vocal placement, and separation of physical instruments in space.
* **Symptom fix:** A "forward" or flat stage is often caused by hot upper-midrange/highs relative to the bass, or phase misalignment at the midrange-to-tweeter joint. Review [staging-depth.md](file:///skills/autosound-tuning/references/staging-depth.md).

### 5. Midbass Punch & Transient Attack
* **Check:** Kick-drum impact, speed, and tactile feel in the doors.
* **Symptom fix:** Lack of punch is typically a cabinet resonance issue or a phase cancellation between left/right doors in the 100 Hz–200 Hz region.

### 6. High-Frequency Sibilance & Glare
* **Check:** Female vocal sibilance ("s", "sh" sounds), horn glare, and cymbal airiness.
* **Symptom fix:** Ringing or harshness around 3 kHz–5 kHz should be corrected with surgical virtual-layer EQ notches.

---

## Verdict Logging
Compile the Arbiter's binary verdicts into a structured checklist:
* **Item:** [Track & Timecode] — [Acoustic Attribute] ──► **[🟢 Passed / ❌ Failed]**
* Any failed items are added directly to the active tuning backlog, triggering targeted adjustments in Phase 2 or 6.

Once all core technical listening traits pass, proceed to **Phase 6**.
