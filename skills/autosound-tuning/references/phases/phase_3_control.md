# Phase 3 — Control Measurement & Technical Verdict

This phase acts as the final technical gate before proceeding to subjective listening or surround integration.

## 🎯 Goal-node

**Purpose:** the final technical gate — verification scans + independent cross-vendor verdicts + Technical Lock, before subjective/multichannel work.

**Questions this phase answers:** does the measured system meet target/joint/symmetry criteria? do independent reviewers agree? is it stable enough to lock?

**Required evidence:** the full verification MMM set (each `_final` channel, Ws/Ms/TWs, sw+Ws, L/R sides, `ALL_final`); independent Claude + Gemini analyses.

**✅ Quality gate → Phase 4/5 (Technical Lock):** verification scans captured; **two independent (cross-vendor) verdicts**; disagreements resolved or escalated to the Arbiter (Disagreement Table at 3/3); config backed up to `dsp-config/`, changelog/dsp-state/audit-trail updated.

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
* **The Data Pull:** Use the REW API to query the measurement files directly, analyzing magnitude trends, joint summation quality, and L/R symmetry.
* **The Verdict:** Each AI issues an independent report assessing target-curve accuracy, joint alignment, and imaging trends. Claude acts as the primary contact, compiling the results for the user.
* **Deadlock Escalation:** If Claude and Gemini disagree on a critical alignment step, do not engage in endless rounds. If Iteration 3/3 is reached without agreement, compile a standard **Disagreement Table** (Contract §5) and hand the decision to the Arbiter (the User).

---

## 3. Configuration Backup & Handoff
Once the technical alignment is accepted by the Arbiter:
* Save the final DSP configuration file. Copy it to `rew_analitic/dsp-config/` with an updated `README.md` cataloging the changes.
* Back up the project's REW `.mdat` file.
* Update `tuning-changelog`, `dsp-state-current`, and the iCloud `audit-trail.md`.

Proceed to **Phase 4** (multi-channel integration, if applicable) or **Phase 5** (listening tests).
