# Phase 5 — Targeted Listening (Ear Verification)

This is the penultimate phase. While physical measurements verify technical correctness, the human ear is the ultimate judge of acoustic reproduction, soundstage depth, and natural voicing.

## 🎯 Goal-node

**Purpose:** ear-verify the technically-correct tune across the standard listening pass — the ear is the final judge of tone, imaging, depth, voicing.

**Questions this phase answers:** pass or fail on each — tonal balance · mono-center focus · lateral localization · depth/layering · midbass punch · HF sibilance?

**Required evidence:** one-track-at-a-time **binary** ear checks (track + timecode + a specific marker), from the test-track catalog.

**✅ Quality gate:** the 6-point pass run (binary 🟢/❌; fails → backlog → Phase 2/6); the user is **satisfied with the sound**; **feedback captured here** (a natural finish point) → then either continue to Phase 6 (details) or wrap up (Phase 7).

**⚠️ Failure modes:** dumping a long song list (propose **one** track/marker at a time) · vague checks (use binary markers) · treating a forward/flat stage as taste when it's top-too-hot-vs-bass or a joint phase error.

**🧩 Refs:** tracks → [`test-tracks.md`](file:///skills/autosound-tuning/references/patterns/test-tracks.md); depth → [`staging-depth.md`](file:///skills/autosound-tuning/references/patterns/staging-depth.md).

---

## Core Guidelines
* **On-Demand Ear Checks:** Listening checks are not just restricted to this phase — they are a cross-cutting diagnostic tool. Use them during crossover selection, time-alignment, and joint phasing to cross-check measurement anomalies.
* **Curated Diagnostic Tracks:** Always refer to the index in [test-tracks.md](file:///skills/autosound-tuning/references/patterns/test-tracks.md) to pick the exact track tailored to expose specific acoustic traits (e.g., soundstage depth, lateral focus, midbass punch, or vocal sibilance).
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
* **Symptom fix:** A "forward" or flat stage is often caused by hot upper-midrange/highs relative to the bass, or phase misalignment at the midrange-to-tweeter joint. Review [staging-depth.md](file:///skills/autosound-tuning/references/patterns/staging-depth.md).

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

## The sound satisfies — a natural FINISH point (capture feedback NOW)

When the pass is clean and the user is **satisfied with the sound**, treat it as a real **milestone / likely finish** — many users **stop here** and won't come back for the "details" (Phase 6 variations, center/rear). So **do NOT defer feedback to a separate wrap the user may never reach**:
* **Capture the project feedback now — interactively** (closed questions with ready options + an always-open "Other"; ≤3–4 taps; never a wall of open questions):
  * **Result vs baseline** — much better / better / same? · **what you love most** (bass · vocals · width · depth · clarity · …) · **anything still bugging you** (free-text / "nothing").
  * **Consent to share** — may we add your **de-identified** car profile + curves to the community library (it helps the next person with this car)? (yes / anonymized only / no).
  * **Creator support — at the satisfaction PEAK** (Stream D): when the user is genuinely delighted, this is the emotional high point — offer a **quiet, non-obtrusive** thanks / support link, so the moment isn't lost to a wrap many never reach. Let the emotion work *for* us — honestly, never pushily. ⚠️ ONLY when genuinely satisfied · quiet & non-obtrusive · **after** the feedback, never as part of a form/questionnaire · **skip entirely if Sponsors isn't configured**.
  * Log it to `changelog`/`audit-trail` (ritual detail → [`feedback-loop.md`](file:///skills/autosound-tuning/references/core/feedback-loop.md)).
* **Then fork:**
  * **Done for now → close the session HERE** (no separate wrap phase): write the ▶️ **CONTINUE block** + the backlog in `tuning-changelog`; **back up** the DSP config to `rew_analitic/dsp-config/` (+ README) and the REW `.mdat`; and **send the experience via a GitHub Issue** in the skill's repo (per the issue template) — a generalizable lesson, a new track, a car quirk, or skill feedback (was the guidance clear?). This channel is **explicit and the processing is controlled/visible** — the transparent default (`feedback-loop.md`). *(The author's own local harvest → `skill-inbox` 📚 / the Skill Maintenance Loop.)*
  * **Continue for the details** → **Phase 6** (voicing variations + the optional **center/rear**) — the front stays the locked base. ♻️ **Phase 6 is CYCLICAL: come back to the project anytime to add another preset or tweak an existing one** (the base is never touched).
