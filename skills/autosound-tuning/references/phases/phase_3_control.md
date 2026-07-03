# Phase 3 — Control Measurement & Technical Verdict

This phase acts as the final technical gate before proceeding to subjective listening or surround integration.

## 🎯 Goal-node

**Purpose:** the final technical gate — verification scans + independent cross-vendor verdicts + Technical Lock, before subjective/multichannel work.

**Questions this phase answers:** does the measured system meet target/joint/symmetry criteria? do independent reviewers agree? is it stable enough to lock?

**Required evidence:** the full verification MMM set (each `_final` channel, Ws/Ms/TWs, sw+Ws, L/R sides, `ALL_final`); independent Claude + Gemini analyses.

**✅ Quality gate → Phase 4/5 (Technical Lock):** verification scans captured; **two independent (cross-vendor) verdicts**; **a minimum ear assessment passed** — **stage** (mono-center / EMMA) **and overall tonal balance** — with an honest read of the result logged and the **Arbiter satisfied** (or the dissatisfaction resolved by an adjustment / a step back); disagreements resolved or escalated to the Arbiter (Disagreement Table at 3/3); config backed up to `dsp-config/`, changelog/dsp-state/audit-trail updated.

**⚠️ Failure modes:** endless review rounds (cap at 3/3 → Disagreement Table) · locking without a backup · a single-perspective verdict (must be cross-vendor).

**🧩 Refs:** [`review-loop.md`](file:///skills/autosound-tuning/references/core/review-loop.md) (loop, deadlock, Disagreement Table §5).

---

## Step-by-Step Runbook

### 1. Verification Measurement Checklist
Instruct the user to run a complete, disciplined series of MMM RTA measurements using the locked spatial pattern. Collect and save the following:
* **Each individual channel:** `sw_final`, `w-L_final`, `w-R_final`, `m-L_final`, `m-R_final`, `tw-L_final`, `tw-R_final`.
* **The summed band pairs (L+R):** `Ws_final`, `Ms_final`, `TWs_final`.
* **The low-frequency joint:** `sw+Ws_final` (Subwoofer + both Midbasses).
* **The individual sides:** Left-side-only (no sub), Right-side-only (no sub).
* **The complete front system:** `ALL_final` (all front channels active together).

---

## 2. Independent Technical Verdicts
Claude (the Orchestrator) and Gemini (the Critic/Advisor) perform separate, unbiased analyses of the data:
* **The Data Pull:** Use the REW API to query the measurement files directly, analyzing magnitude trends, joint summation quality, and L/R symmetry. **Include the band-integrated deviation-vs-target scan** on `ALL_final` (mean deviation per half-decade after level-normalizing to the target — method in [`analysis-playbook.md`](file:///skills/autosound-tuning/references/core/analysis-playbook.md)): a **broad tilt ≥~1–1.5 dB off target** — in *any* region (a hot lower-mid over a light midbass, a hot 2–5 kHz, a bloated/shy bass shelf, a rolled/hot top) — is a voicing error even when no single peak is large and the RMS looks done. It is the residual that fatigues on a long listen, so a verdict that only checks peaks/joints/symmetry **misses it**. Flag it here, not after the customer tires of the sound — and flag it as a *broad gentle* fix, never as narrow deep cuts (which would trade fatigue for a dead, over-processed sound).
* **The Verdict:** Each AI issues an independent report assessing target-curve accuracy, joint alignment, and imaging trends. Claude acts as the primary contact, compiling the results for the user.
* **Deadlock Escalation:** If Claude and Gemini disagree on a critical alignment step, do not engage in endless rounds. If Iteration 3/3 is reached without agreement, compile a standard **Disagreement Table** (Contract §5) and hand the decision to the Arbiter (the User).

---

## 2.5 Minimum ear assessment + an honest read of the result — MANDATORY before the lock

A config is **not a "tuned version" until it's confirmed by ear** — don't lock on measurements alone. Do a **brief but real listen** (the full pass is Phase 4) covering the two things that matter:
* **Stage** — a **mono track** must image tight and **dead-centre** (ONE point); + EMMA localization tracks ([`test-tracks.md`](file:///skills/autosound-tuning/references/patterns/test-tracks.md)) for L / C-L / C / C-R / R. Smears or pulls to a side → the L/R timing/level/phase isn't right.
* **Overall tonal balance** — a couple of familiar tracks: bass weight & control · vocal naturalness/placement · top-end transparency (no glare/harshness). Is the whole balanced, or is something clearly off?

Then **read the result honestly with the Arbiter** and record it:
* **What came out** — the strengths **and** the remaining limitations/potential (a lock is a *good base with room*, not "perfect"). Log it to `audit-trail`/`changelog`.
* **The Arbiter's impression** — how the user *feels* about the work so far is a first-class signal, not an afterthought.

**Branch on satisfaction:**
* **Satisfied** (with a clear-eyed view of what's still open) → lock.
* **Not satisfied** → either a **small adjustment** here, or **step back** (re-open Phase 1/2 — the gate is re-entrant) and **search for a solution** first. **Don't lock over a known dissatisfaction.**

---

## 3. Configuration Backup & Handoff
Once the technical alignment is accepted by the Arbiter:
* Save the final DSP configuration file. Copy it to `rew_analitic/dsp-config/` with an updated `README.md` cataloging the changes.
* Back up the project's REW `.mdat` file.
* Update `tuning-changelog`, `dsp-state-current`, and `audit-trail.md` (project-local, in the project's `rew_analitic/`).

Proceed to **Phase 4** (front listening & fine-tuning) + any **Phase 5** voicing — get the **FRONT** to satisfy the user first. **Center/rear (Phase 5) is optional and comes only once the front satisfies** — don't jump to it straight from the lock.
