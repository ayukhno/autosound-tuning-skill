# Tuning Process Phases — Modular Directory Index

The tuning process consists of seven chronological phases. To optimize large language model (LLM) context windows and prevent attention dilution, the monolithic `process-phases.md` has been split into individual, focused reference files.

---

## 🔄 The "Phase Sliding Window" Protocol

When assisting with a tuning session, the AI **MUST** follow this context-minimizing protocol:
1. **Identify current phase:** At the start of every session, read the top **▶️ CONTINUE** block of the `tuning-changelog` to determine the user's active phase (e.g., Phase 1).
2. **Load active & adjacent phases:** Use the `view_file` tool to load **ONLY** the active phase file and the next logical phase file (e.g., `phase_1_foundation.md` and `phase_2_eq.md`).
3. **Ignore out-of-scope phases:** Do not load or process instructions for prior or future phases unless explicitly requested by the user or required for global context reconciliation.

> ⚙️ **Quality Gates are re-entrant, not one-way locks.** Tuning is iterative and non-linear: a later change that touches a **crossover joint band** (±~1 octave of a joint, e.g. 230–350 Hz or 3–5 kHz), or a failed Phase-5/6 ear check, **re-opens** the affected earlier gate (typically phase/joint alignment) — re-measure and re-verify the summation; never treat a passed gate as permanent. An EQ move inside a joint band rotates local phase/group-delay and can undo a prior alignment.

---

## 🗺️ Process Phase Directory

| Phase | Reference File Path | Purpose & Core Content |
| :---: | :--- | :--- |
| **Phase -1** | [phase_-1_intake.md](file:///skills/autosound-tuning/references/phases/phase_-1_intake.md) | New project onboarding, equipment/goals interview, choosing target curve, safety checks. |
| **Phase 0** | [phase_0_baseline.md](file:///skills/autosound-tuning/references/phases/phase_0_baseline.md) | Glossary setup, measurement naming conventions, target curve imports, raw vehicle baseline. |
| **Phase 1** | [phase_1_foundation.md](file:///skills/autosound-tuning/references/phases/phase_1_foundation.md) | Crossovers, levels, preliminary gross time-alignment (arrival TA), Nono per-band target generation. |
| **Phase 2** | [phase_2_eq.md](file:///skills/autosound-tuning/references/phases/phase_2_eq.md) | Hygiene EQ (minimum-phase peaks only), joint phase alignment (APF/fine delay), summed group alignment, final technical virtual EQ. |
| **Phase 3** | [phase_3_control.md](file:///skills/autosound-tuning/references/phases/phase_3_control.md) | Final RTA verification scans, independent AI verdicts (Claude/Gemini), Technical Lock & backups. |
| **Phase 4** | [phase_4_listening.md](file:///skills/autosound-tuning/references/phases/phase_4_listening.md) | Systematic test-track listening pass → **satisfied with the sound** → feedback → **session close** (backup · experience via a GitHub Issue). |
| **Phase 5** | [phase_5_variations.md](file:///skills/autosound-tuning/references/phases/phase_5_variations.md) | **Variations (cyclical):** client voicing presets (genre/context) + the optional **center & rear** (envelopment). Return anytime to add/tweak a preset. |

---

## 🛠️ Combined Method & General Guidelines

The core architecture combines **Instrument Measurements (REW)**, **Hashimoto By-Ear Secrets** (`method-hashimoto.md`), and **Industry Installer Experience** (`voicing-by-ear.md`). 
At each stage:
* **Measurements** provide objective physical realities (frequency response, joint summation, impulse delays, acoustic polarity).
* **The Ear** validates subjective performance (filter slope choices, phantom center focus, staging depth, voicing).
* **Cross-checking** between both ensures the final tune is robust and free of technical and acoustic compromises.
