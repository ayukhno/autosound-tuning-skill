# Phase 4 — Targeted Listening (Ear Verification)

This is the penultimate phase. While physical measurements verify technical correctness, the human ear is the ultimate judge of acoustic reproduction, soundstage depth, and natural voicing.

## 🎯 Goal-node

**Purpose:** ear-verify the technically-correct tune across the standard listening pass — the ear is the final judge of tone, imaging, depth, voicing.

**Questions this phase answers:** pass or fail on each — tonal balance · mono-center focus · lateral localization · depth/layering · midbass punch · HF sibilance?

**Required evidence:** one-track-at-a-time **binary** ear checks (track + timecode + a specific marker), from the test-track catalog.

**✅ Quality gate:** the 6-point pass run (binary 🟢/❌; fails → backlog → Phase 2/5); the user is **satisfied with the sound**; **feedback captured here** (a natural finish point) → then either continue to Phase 5 (details) or wrap up (close the session here).

**⚠️ Failure modes:** dumping a long song list (propose **one** track/marker at a time) · vague checks (use binary markers) · treating a forward/flat stage as taste when it's top-too-hot-vs-bass or a joint phase error · **declaring done from short spot-checks when a broad tonal tilt only reveals itself as fatigue on a long listen** (add the fatigue pass, item 7).

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

### 7. Long-Listen / Fatigue Check (broadband tonal balance) — the one the spot-checks miss
The six checks above are short, focused probes — they catch imaging, joints, and narrow glare, but a
**broad tonal tilt is inaudible as "wrong" in a 30-second A/B and only shows up as fatigue.** The ear
adapts to a slow warm/bright/muddy slope for a minute, then tires of it over 15–20+ minutes. So before
you call it done, do a **relaxed album-length listen** (≥15–20 min, familiar acoustic + vocal
material, comfortable level — not analytical): does it stay easy and inviting, or does it get tiring,
thick/muddy, thin, or shouty as time passes?
* **If it fatigues, first tell which KIND** (they call for opposite fixes):
  * **Tired from a tilt** (too thick/muddy, too bright/shouty, too warm/dark) → re-run the
    **band-integrated deviation-vs-target scan** ([`analysis-playbook.md`](file:///skills/autosound-tuning/references/core/analysis-playbook.md)); a broad band riding ≥~1–1.5 dB off target is the culprit — in *any* region (lower-mid mud, hot 2–5 kHz shout, bloated/shy bass, rolled/hot top). Fix as a **gentle broadband tilt, never narrow notches**.
  * **Tired from deadness** (dry, clinical, lifeless, no air) → that's **over-correction, not a tilt** —
    too many/too-deep EQ cuts chasing reflections the ear ignored. The fix is to **remove EQ, not add
    it**: relax or pull filters and let transparency back in (`car-eq-patterns.md` → judge-by-audibility,
    Fail B). Adding more EQ here makes it worse.
* **Why it belongs by ear, not only on the trace:** the trace tells you *where* the broadband tilt is;
  the long listen tells you it *matters*. A tune that measures 1.5 dB RMS "done" but tires the listener
  isn't done — this is the check that separates a lock from a keeper.

---

## Verdict Logging
Compile the Arbiter's binary verdicts into a structured checklist:
* **Item:** [Track & Timecode] — [Acoustic Attribute] ──► **[🟢 Passed / ❌ Failed]**
* Any failed items are added directly to the active tuning backlog, triggering targeted adjustments in Phase 2 or 5.

## The sound satisfies — a natural FINISH point (capture feedback NOW)

When the pass is clean and the user is **satisfied with the sound**, treat it as a real **milestone / likely finish** — many users **stop here** and won't come back for the "details" (Phase 5 variations, center/rear). So **do NOT defer feedback to a separate wrap the user may never reach**:
* **Capture the project feedback now — interactively** (closed questions with ready options + an always-open "Other"; ≤3–4 taps; never a wall of open questions):
  * **Result vs baseline** — much better / better / same? · **what you love most** (bass · vocals · width · depth · clarity · …) · **anything still bugging you** (free-text / "nothing").
  * **Consent to share** — may we add your **de-identified** car profile + curves to the community library (it helps the next person with this car)? (yes / anonymized only / no).
  * **Creator support — at the satisfaction PEAK** (Stream D): when the user is genuinely delighted, this is the emotional high point — offer a **quiet, non-obtrusive** thanks / support link, so the moment isn't lost to a wrap many never reach. Let the emotion work *for* us — honestly, never pushily. ⚠️ ONLY when genuinely satisfied · quiet & non-obtrusive · **after** the feedback, never as part of a form/questionnaire · **skip entirely if Sponsors isn't configured**.
  * Log it to `changelog`/`audit-trail` (ritual detail → [`feedback-loop.md`](file:///skills/autosound-tuning/references/core/feedback-loop.md)).
* **Then fork:**
  * **Done for now → close the session HERE** (no separate wrap phase): write the ▶️ **CONTINUE block** + the backlog in `tuning-changelog`; **back up** the DSP config to `rew_analitic/dsp-config/` (+ README) and the REW `.mdat`; and — **if the user consented** (above) — **contribute the experience via a GitHub Issue** in the skill's repo (per the issue template): the **de-identified car + equipment + tuning experience** — what worked, the curves, cabin quirks, the outcome — for the **community library** so it helps the next person with the same car/gear (feeds `knowledge/cars` + `knowledge/dsp`). Add any skill feedback (was the guidance clear?) too. The GitHub Issue is **explicit and the author's processing is controlled/visible** — the transparent default (`feedback-loop.md`). *(The author's own local harvest → `skill-inbox` 📚.)*
  * **Continue for the details** → **Phase 5** (voicing variations + the optional **center/rear**) — the front stays the locked base. ♻️ **Phase 5 is CYCLICAL: come back to the project anytime to add another preset or tweak an existing one** (the base is never touched).
