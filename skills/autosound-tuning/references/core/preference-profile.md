# Preference Profile (layer 4) — the per-project subjective layer

The Preference Profile isolates the user's **subjective voicing preferences** from the objective
engineering. It is seeded at intake and applied **only after** the objective tune is complete
(Phase 5 voicing). It never overrides measurement-driven engineering.
See [`knowledge-architecture.md`](file:///skills/autosound-tuning/references/core/knowledge-architecture.md).

## What IS a preference (goes here)

- **Taste axes:** warm↔bright · bass-heavy↔neutral · forward↔laid-back · accuracy↔fun
- **Loudness habit** (how loud you usually listen → equal-loudness weighting)
- **Favourite reference tracks** + "what you love most" (bass / vocals / strings / …)
- **Preferred target-curve character** (a start and a shape, finalized by ear)

## What is NOT a preference (stays in the Engineering Profile — `autosound_context.md`)

These **shape the engineering**, so they are objective goals, not skippable tastes:

- **Reference seat** (driver / passenger / all) → drives centering & TA strategy
- **Competition format(s)** (EMMA / AYA / CARMusic) → drives preset architecture & allowed techniques (Engineering). ⚠️ *Also* seeds a format-specific **voicing target** (stage weight, echelons, the tonal balance the format rewards) — that part is a format-driven **preference**, finalized by ear in Phase 5. So the format spans both layers.
- **Hard constraints** ("don't cut the doors", TÜV, budget) → hard limits
- **Physical ceilings** (depth limited by mid geometry; envelopment needs a rear)

> ⚠️ The classic trap: filing the reference seat or competition format as a "preference" and then
> skipping/overriding it. They are engineering inputs — keep them in the Engineering Profile.

## Where it's used

- **Seeded** at intake — [`project-intake.md` §2](file:///skills/autosound-tuning/references/core/project-intake.md).
- **Held out** of Phases 0–5 (the objective tune).
- **Applied** in **Phase 5** — [`phase_5_variations.md`](file:///skills/autosound-tuning/references/phases/phase_5_variations.md)
  via [`voicing-by-ear.md`](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md),
  often as a separate voicing preset ([`preset-strategy.md`](file:///skills/autosound-tuning/references/core/preset-strategy.md)).

## Why separate

Mixing preference into engineering is how a tune drifts to "what I like today" and loses
reproducibility. The split keeps the objective result stable and the subjective layer a clean,
reversible overlay.
