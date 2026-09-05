# Knowledge Architecture — the 5 layers

The skill's knowledge is organized in five layers across two locations. This keeps the
normative method separate from per-project data, and starting hypotheses separate from rules.

## The five layers

| # | Layer | Lives in | Nature | Holds |
|---|---|---|---|---|
| 1 | **Core Methodology** | skill · `references/core/` | normative, author-owned | rules, decision logic, process, techniques, quality gates |
| 2 | **Pattern Repository** | skill · `references/patterns/` (+ `target-curves/`) | hypotheses, accumulated | "in similar conditions this often worked" — starting points, incl. standard target curves |
| 3 | **Engineering Profile** | project · `autosound_context.md` | objective, per-car | car/body, install, DSP, drivers, config, constraints, engineering-constraining goals |
| 4 | **Preference Profile** | project · `preference-profile.md` | subjective, per-car | pure voicing preferences — applied ONLY after the objective tune (Phase 5) |
| 5 | **Project State** | project · `dsp-state` · `tuning-changelog` · `audit-trail` | dynamic, per-session | measurements, decisions, history, current DSP state |

**Skill = layers 1–2 (shared, model-agnostic). Project = layers 3–5 (per-car, dynamic.)**

## The knowledge base — the one place a per-car fact may sit in the skill

`knowledge/cars/<body>.md` and `knowledge/dsp/<model>.md` are in the skill and yet describe one
cabin and one processor, which reads like a contradiction of the line above. It is not, and the
boundary is narrow enough to state exactly (the owner's ruling, 2026-09-05):

**A project detail may live here only as supplementary reference about a CAR or a piece of
EQUIPMENT** — the standing, physical way the system is built. The mounting angle of a driver.
Whether passive filters sit in the path. Enclosure, placement, what is bolted where. These describe
**what the sound meets** before anyone tunes anything; they survive every session, and the next
build on the same body genuinely wants them.

**What may never sit here is anything DIALLED** — crossover corners, delays, EQ, the phase
control's angles. That is the tune's state, layer 5, and it lives in the project. The tell is
simple: if changing it is a tuning decision, it is not knowledge, it is state.

**And inside a car's file the two halves do not mix.** A flaw description is **physics** — what the
cabin or the driver does, measured, with its evidence (`flaw_map.py`, `acoustics.flaws`, PART B of
`knowledge/cars/_TEMPLATE.md`). Install facts are **logic** — how the build is put together. An
angle or a passive filter is not a flaw and does not belong in a flaw row, even when it explains
one; put it in the install description and let the flaw row point at it. Mixing them makes a
measured physical finding read as a configuration choice, and neither can then be trusted on its own.

Bought 2026-09-05: `references/tooling/helix-phase-allpass.md` carried one car's dialled phase
angles as "our practice" for months. A screen read showed the processor at 0° on all twelve
outputs, the project's own ledger agreed, and one of the two angles was not even on the control's
hardware grid — a number nothing could have re-measured, because a method file is never re-measured.

## The two governing rules

1. **Patterns are hypotheses, never rules.** A pattern proposes a *starting point*; measurement
   or the ear decides. (See the banner atop every `references/patterns/` file.) Core Methodology
   rules and safety steps are firm; patterns are not.
2. **Objective before subjective.** Layer 4 (preferences) never overrides layers 1–3 engineering.
   Engineering-constraining goals (reference seat, competition format, hard constraints, physical
   ceilings) are **not** preferences — they belong to the Engineering Profile (layer 3). Only pure
   taste (warm↔bright, loudness habit, favourite tracks, curve character) is Preference Profile.
   Detail: [`preference-profile.md`](references/core/preference-profile.md).

## Evolution (governance)

The methodology changes only via the Owner-approved loop — Observation → Hypothesis → Validation
→ Proposal → Review → **Approval** — never automatically. A new tuning insight starts as a
*provisional* pattern, and is promoted into Core only after it holds up. See
[`review-loop.md`](references/core/review-loop.md) and the Skill
Maintenance Loop in `SKILL.md`.
