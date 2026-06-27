# Phase 3 — Control Measurement & Technical Verdict

This phase acts as the final technical gate before proceeding to subjective listening or surround integration.

## Core Objectives
1. **Acquire Verification Scans:** Measure all individual, paired, and summed configurations to verify technical alignment.
2. **Execute Multi-AI Verdicts:** Run independent reviews (Claude and Gemini) on the final technical outcome.
3. **Establish Technical Lock:** Secure a stable baseline from which subjective voicing and multi-channel work can build.

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
