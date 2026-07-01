# Phase -1 — New Project & Setup Intake

This phase bootstraps a brand-new tuning project or a fresh system installation.

## 🎯 Goal-node

**Purpose:** bootstrap a brand-new project — workspace + language, equipment/goals interview, install verification, target-curve seed — so measurement can start safely on a known system.

**Questions this phase answers:** what's the car/drivers/DSP/mic rig? what are the goals (competition/enjoyment, reference seat, taste)? is the install safe and correct to measure?

**Required evidence:** the user interview (no guessing); driver `Fs` (datasheet/ask); routing · electrical polarity · gain · noise checks.

**✅ Quality gate → Phase 0:** language set; `autosound_context.md` (Engineering Profile) + `preference-profile.md` created; install verified + protective HPFs set for fragile drivers; a candidate target curve **seeded** (no default).

**⚠️ Failure modes:** skipping install verification (costs a session) · filing reference seat / competition format as a "preference" (they're engineering) · enforcing a default curve.

**🧩 Patterns / refs:** full flow → [`project-intake.md`](file:///skills/autosound-tuning/references/core/project-intake.md); curve→character → [`voicing-by-ear.md`](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md).

---

## Runbook — the authoritative sequence is `project-intake.md §0.5`

Do **not** re-derive the steps here. Run the gated first-start flow in [`project-intake.md §0.5`](file:///skills/autosound-tuning/references/core/project-intake.md) **in order**, clearing each ⛔ gate:

**Language** (§0) → **Reviewer channel** (§0 · Claude+Gemini) → **Interview** (§1–§2) → **REW rig** → ⛔ **Naming/glossary** (before any measurement) → ⛔ **Install verification** (§3 · protective HPFs, ≥1.1×Fs safety minimum) → **Generate project files** (§5 · incl. `preference-profile.md`) → **First baseline** (Phase 0).

The detail for each step lives in the `project-intake.md` section noted — this phase file is only the goal-node + this pointer.
