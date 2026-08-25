# Phase -1 — New Project & Setup Intake

This phase bootstraps a brand-new tuning project or a fresh system installation.

> 🗺️ **Two modes and a path.** Intake now also picks the path: **full** (a new tune, virtual-first) or **improve an existing tune** (−1 → 3 → 4). Both read the current DSP settings into the ledger. The virtual-first happy path, the gear loss table, the degradation rule and the day-before preparation (−1.4) live in [`virtual-first.md`](references/phases/virtual-first.md) and [`capture-session-sheet.md`](references/phases/capture-session-sheet.md).

## 🎯 Goal-node

**Purpose:** bootstrap a brand-new project — workspace + language, equipment/goals interview, install verification, target-curve seed — so measurement can start safely on a known system.

**Questions this phase answers:** what's the car/drivers/DSP/mic rig? what are the goals (competition/enjoyment, reference seat, taste)? is the install safe and correct to measure?

**Required evidence:** the user interview (no guessing); driver `Fs` (datasheet/ask); routing · electrical polarity · gain · noise checks.

**✅ Quality gate → Phase 0:** language set; `autosound_context.md` (Engineering Profile) + `preference-profile.md` created; **the machine files exist and validate** — `project.json`, `dsp_profile.json`, the glossary, and a first ledger snapshot with every profile-declared tier populated (`python3 rew_tool/contract.py check <project> --gate` exits 0 — **`--gate`, not plain `check`**: plain `check` answers "is anything here wrong", which an EMPTY project satisfies, and this gate is asking whether everything it needs exists) — a prose-only intake is not a complete one, since a consumer front-end has nothing to render without them; install verified + protective HPFs set for fragile drivers; a candidate target curve **seeded** (no default).

**⚠️ Failure modes:** skipping install verification (costs a session) · filing reference seat / competition format as a "preference" (they're engineering) · enforcing a default curve.

**🧩 Patterns / refs:** full flow → [`project-intake.md`](references/core/project-intake.md); curve→character → [`voicing-by-ear.md`](references/patterns/voicing-by-ear.md).

---

## Runbook — the authoritative sequence is `project-intake.md §0.5`

Do **not** re-derive the steps here. Run the gated first-start flow in [`project-intake.md §0.5`](references/core/project-intake.md) **in order**, clearing each ⛔ gate:

**Language** (§0) → **Reviewer channel** (§0 · Claude+Gemini) → **Interview** (§1–§2) → **REW rig** → ⛔ **Naming/glossary** (before any measurement) → ⛔ **Install verification** (§3 · protective HPFs, ≥1.1×Fs safety minimum) → **Generate project files** (§5 · incl. `preference-profile.md`) → **First baseline** (Phase 0).

The detail for each step lives in the `project-intake.md` section noted — this phase file is only the goal-node + this pointer.
