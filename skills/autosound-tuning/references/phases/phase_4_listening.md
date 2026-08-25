# Phase 4 — Targeted Listening (Ear Verification)

This is the penultimate phase. While physical measurements verify technical correctness, the human ear is the ultimate judge of acoustic reproduction, soundstage depth, and natural voicing.

## 🎯 Goal-node

**Purpose:** ear-verify the technically-correct tune across the standard listening pass — the ear is the final judge of tone, imaging, depth, voicing.

**Questions this phase answers:** pass or fail on each — tonal balance · mono-center focus · lateral localization · depth/layering · midbass punch · HF sibilance?

**Required evidence:** one-track-at-a-time **binary** ear checks (track + timecode + a specific cue), from the test-track catalog — **recorded in the project journal the moment they are said** (`process.py listening-verdict`), never only in the conversation.

**✅ Quality gate:** the 6-point pass run (binary 🟢/❌; fails → backlog → Phase 2/5); the user is **satisfied with the sound**; **feedback captured here** (a natural finish point) → then either continue to Phase 5 (details) or wrap up (close the session here).

**⚠️ Failure modes:** dumping a long song list (propose **one** track/marker at a time) · vague checks (use binary markers) · treating a forward/flat stage as taste when it's top-too-hot-vs-bass or a joint phase error · **declaring done from short spot-checks when a broad tonal tilt only reveals itself as fatigue on a long listen** (add the fatigue pass, item 7).

**🧩 Refs:** the words → [`listening-cheat-sheet.md`](references/patterns/listening-cheat-sheet.md) (the ONE home of every "sounds right / sounds wrong" phrase, and the routes `first` · `short` · `full` · `league`); tracks and cues → [`test-tracks.md`](references/patterns/test-tracks.md); depth → [`staging-depth.md`](references/patterns/staging-depth.md). Both files are read by tools through `rew_tool/listening.py`; a translation of the cheat sheet carries the same ids.

---

## Core Guidelines
* **On-Demand Ear Checks:** Listening checks are not just restricted to this phase — they are a cross-cutting diagnostic tool. Use them during crossover selection, time-alignment, and joint phasing to cross-check measurement anomalies.
* **Curated Diagnostic Tracks:** Always refer to the index in [test-tracks.md](references/patterns/test-tracks.md) to pick the exact track tailored to expose specific acoustic traits (e.g., soundstage depth, lateral focus, midbass punch, or vocal sibilance).
* **Hypothesis-Driven Instruction:** Do **not** dump a long, overwhelming list of songs on the user. Propose **one track at a time**, instructing the user exactly:
  1. **What song** to play.
  2. **At what timecode** (timestamp) to focus their attention.
  3. **What specific binary auditory marker** to listen for (e.g., "Is the upright bass localized centered on the dashboard, or does it drift left below 50 Hz?").

---

## Before any track — three things the session must know (the cheat sheet, §1)

1. **Which library the user actually has** — every track named carries its library; none of the known ones → their own favourite tracks and a description of the material (`own/*` in `test-tracks.md`).
2. **What "was" means** — a comparison with the previous tune exists only if they came in with one (its slot was kept at intake) or on a second pass of this phase; a tune built from nothing has no "was".
3. **What they compare against** — for themselves, A/B with the previous slot; for competition, a **reference** (their experience, a good home system, prize-winning cars they have sat in) — and since sound cannot be remembered for long, **the emotion the reference gave them**, not the detail.

## The routes — first, short, full, league

The order and the pairs (track × characteristic) are the `routes` table of the cheat sheet; the words for each characteristic are its `characteristics` table; where to listen in the track is the `links` table of `test-tracks.md`. Do not restate them here — read them.

* **`first` (5 min, no verdicts)** — right after the technical lock: one favourite track of the user's, then a **real mono track from streaming** with one question — *where is the image?* — a tight point at the centre at dash height is the first achievement to take home; then CarMus #01 if they have it. Then they go for a drive.
* **`short` (10 min)** — one sitting between drives: mono centre · tonal balance · punch and the sub↔midbass seam · top and sibilants. Enough to tell whether the foundation holds and whether the tune is livable.
* **`full`** — before closing or before a competition, **split over several sittings** with drives between them (listening tires; ears reset on the road), the long listen as its own drive. `c01`–`c03` first: if the centre or the positions fail, the rest is too early to judge.
* **`league`** — stage height, width and depth: a second visit to this phase once the foundation holds.

Every ❌ has a route to a step (the cheat sheet's last column): **most fixes are made at the desk from the solos already captured** — the joints (1.3), the levels (1.4), the coarse EQ (2.1) or the fine EQ over MMM (3.3) — and a new capture is needed only when the hardware or the install changed. A joint touched at the desk gets its sum re-swept (3.2, that joint only).

### The long listen (`c13`) — the check the spot-checks miss
A **broad tonal tilt is inaudible as "wrong" in a 30-second A/B and only shows up as fatigue** over 15–20+ minutes of a familiar album at a comfortable level. If it fatigues, first tell which KIND, because they call for opposite fixes: **a tilt** (thick/muddy, bright/shouty, warm/dark) → the band-integrated deviation-vs-target scan ([`analysis-playbook.md`](references/core/analysis-playbook.md)) and a **gentle broadband tilt, never narrow notches**; **deadness** (dry, clinical, no air) → **over-correction — remove EQ, do not add it** (`car-eq-patterns.md`, Fail B). The trace tells you *where* the tilt is; the long listen tells you it *matters*.

## Verdict Logging — one writer, the project journal

**A verdict message = one command call, before any reply.** When the Arbiter says what they heard — from a TCC panel that composed the text from its templates, or in their own words — record it at once:

```
python3 rew_tool/state/process.py <project>/process listening-verdict \
    --pair CarMus#07:c09:bad --pair CarMus#07:c03:ok \
    --text "stage flat, the vocal holds" --ledger-version v_003 --route full
```

The entry keeps **both** the ticked pairs and the free text (they may disagree after editing; the record does not pretend they are one), and it is stamped with the **ledger version they were listening to** — pass the HEAD you read, never a number from memory. Ids are validated against the cheat sheet and the catalogue, so a typo is refused now, not found in a filter a month later. Looking back is a filter, not a structure: `listening-verdicts --track CarMus#07` shows ❌ at v_003 → 🟢 at v_005, and the ledger diff between them says what changed. At the technical lock, `listening-verdicts --bank` gives the lines a snapshot **adds** to `banked_ear_verdicts` — derived, additive, never overwriting a hand-written line in an older project.

Any ❌ goes to the active backlog with its route (the cheat sheet's last column).

## The sound satisfies — a natural FINISH point (capture feedback NOW)

When the pass is clean and the user is **satisfied with the sound**, treat it as a real **milestone / likely finish** — many users **stop here** and won't come back for the "details" (Phase 5 variations, center/rear). So **do NOT defer feedback to a separate wrap the user may never reach**:
* **Capture the project feedback now — interactively** (closed questions with ready options + an always-open "Other"; ≤3–4 taps; never a wall of open questions):
  * **Result vs baseline** — much better / better / same? · **what you love most** (bass · vocals · width · depth · clarity · …) · **anything still bugging you** (free-text / "nothing").
  * **Consent to share** — may we add your **de-identified** car profile and equipment to the community library (it helps the next person with this car)? (yes / anonymized only / no). **Only a description and the car/equipment parameters are ever sent — never measurements, the ledger, `.mdat` files or the DSP setup** (the author's rule, 2026-08-25).
  * **Creator support — at the satisfaction PEAK** (Stream D): when the user is genuinely delighted, this is the emotional high point — offer a **quiet, non-obtrusive** thanks / support link, so the moment isn't lost to a wrap many never reach. Let the emotion work *for* us — honestly, never pushily. ⚠️ ONLY when genuinely satisfied · quiet & non-obtrusive · **after** the feedback, never as part of a form/questionnaire · **skip entirely if Sponsors isn't configured**.
  * Log it to `changelog`/`audit-trail` (ritual detail → [`feedback-loop.md`](references/core/feedback-loop.md)).
* **Then fork:**
  * **Done for now → close the session HERE** (no separate wrap phase): write the ▶️ **CONTINUE block** + the backlog in `tuning-changelog`; **back up** the DSP config to `rew_analitic/dsp-config/` (+ README) and the REW `.mdat`; and — **if the user consented** (above) — **contribute the experience via a GitHub Issue** in the skill's repo (per the issue template): the **de-identified car + equipment + tuning experience** — what worked, cabin quirks, the outcome, in words — for the **community library** (no measurements, ledger, `.mdat` or DSP setup leave the project) so it helps the next person with the same car/gear (feeds `knowledge/cars` + `knowledge/dsp`). Add any skill feedback (was the guidance clear?) too. The GitHub Issue is **explicit and the author's processing is controlled/visible** — the transparent default (`feedback-loop.md`). *(The author's own local harvest → `skill-inbox` 📚.)*
  * **Continue for the details** → **Phase 5** (voicing variations + the optional **center/rear**) — the front stays the locked base. ♻️ **Phase 5 is CYCLICAL: come back to the project anytime to add another preset or tweak an existing one** (the base is never touched).
