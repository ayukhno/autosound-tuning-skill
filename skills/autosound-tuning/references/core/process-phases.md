# Tuning Process Phases — Modular Directory Index

The tuning process consists of seven chronological phases. To optimize large language model (LLM) context windows and prevent attention dilution, the monolithic `process-phases.md` has been split into individual, focused reference files.

---

## 🔄 The "Phase Sliding Window" Protocol

When assisting with a tuning session, the AI **MUST** follow this context-minimizing protocol:
1. **Identify current phase.** Quoted from `SKILL.md` § 🧭 Phase Sliding Window rather than
   restated, because a restatement is what drifted:
   > Read the active phase from `process/process-state.json`
   > (`python3 rew_tool/state/process.py <project>/process show`) — the same source step 2 names.
   > `tuning-changelog`'s ▶️ CONTINUE block is the human-readable cross-check to read alongside
   > it, and where they disagree the machine file wins.

   Until 2026-09-09 this line said the opposite — the changelog's ▶️ CONTINUE block AS the
   source. In normal work both agree and the contradiction is invisible; they separate exactly
   when the rule is needed (a session cut off between writing the state and writing the note, or
   a changelog nobody updated). `SKILL.md` had already been fixed of that same mistake inside
   itself, and this file kept the old text — so the words above are now checked by
   `scripts/docs-check.py`, not left to two texts agreeing (autosound-hub `HUB-035`).
2. **Load active & adjacent phases:** **read** **ONLY** the active phase file and the next
   logical phase file (e.g., `phase_1_foundation.md` and `phase_2_eq.md`) — with whatever your
   harness reads files with. The instruction is the ACTION, never one harness's tool name: this
   line used to order the reader to use a file-viewing tool that exists in another harness and
   not in Claude Code, and an agent met with a tool it does not have either ignores the line,
   imitates it, or tells the user it cannot comply. (Checked: no reference file may name that
   tool again — `scripts/docs-check.py`.)
3. **Ignore out-of-scope phases:** Do not load or process instructions for prior or future phases unless explicitly requested by the user or required for global context reconciliation.

> ⚙️ **Quality Gates are re-entrant, not one-way locks.** Tuning is iterative and non-linear: a later change that touches a **crossover joint band** (±~1 octave of a joint, e.g. 230–350 Hz or 3–5 kHz), or a failed Phase-5/6 ear check, **re-opens** the affected earlier gate (typically phase/joint alignment) — re-measure and re-verify the summation; never treat a passed gate as permanent. An EQ move inside a joint band rotates local phase/group-delay and can undo a prior alignment.

---

## 🗺️ Process Phase Directory

| Phase | Reference File Path | Purpose & Core Content |
| :---: | :--- | :--- |
| **Phase -1** | [phase_-1_intake.md](references/phases/phase_-1_intake.md) | New project onboarding, equipment/goals interview, choosing target curve, safety checks. |
| **Phase 0** | [phase_0_baseline.md](references/phases/phase_0_baseline.md) | Glossary setup, measurement naming conventions, target curve imports, raw vehicle baseline. |
| **Phase 1** | [phase_1_foundation.md](references/phases/phase_1_foundation.md) | Crossovers, levels, preliminary gross time-alignment (arrival TA), Nono per-band target generation. |
| **Phase 2** | [phase_2_eq.md](references/phases/phase_2_eq.md) | Hygiene EQ (minimum-phase peaks only), joint phase alignment (APF/fine delay), summed group alignment, final technical virtual EQ. |
| **Phase 3** | [phase_3_control.md](references/phases/phase_3_control.md) | Final RTA verification scans, independent AI verdicts (Claude/Gemini), Technical Lock & backups. |
| **Phase 4** | [phase_4_listening.md](references/phases/phase_4_listening.md) | Systematic test-track listening pass → **satisfied with the sound** → feedback → **session close** (backup · experience via a GitHub Issue). |
| **Phase 5** | [phase_5_variations.md](references/phases/phase_5_variations.md) | **Variations (cyclical):** client voicing presets (genre/context) + the optional **center & rear** (envelopment). Return anytime to add/tweak a preset. |

> 🗺️ **The virtual-first happy path** (one capture session → design at the desk → verify → lock) crosses Phases 0–3 without renumbering them: [`virtual-first.md`](references/phases/virtual-first.md), with the [`capture-session-sheet.md`](references/phases/capture-session-sheet.md). Phase −1 picks it (or the iterative fallback) per the gear it has.

---

## 🛠️ Combined Method & General Guidelines

The core architecture combines **Instrument Measurements (REW)**, **Hashimoto By-Ear Secrets** (`method-hashimoto.md`), and **Industry Installer Experience** (`voicing-by-ear.md`). 
At each stage:
* **Measurements** provide objective physical realities (frequency response, joint summation, impulse delays, acoustic polarity).
* **The Ear** validates subjective performance (filter slope choices, phantom center focus, staging depth, voicing).
* **Cross-checking** between both ensures the final tune is robust and free of technical and acoustic compromises.
