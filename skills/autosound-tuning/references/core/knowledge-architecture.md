# Knowledge Architecture — the 5 layers

The skill's knowledge is organized in five layers across two locations. This keeps the
normative method separate from per-project data, and starting hypotheses separate from rules.

## The five layers

| # | Layer | Lives in | Nature | Holds |
|---|---|---|---|---|
| 1 | **Core Methodology** | skill · `references/core/` | normative, author-owned | rules, decision logic, process, techniques, quality gates |
| 2 | **Pattern Repository** | skill · `references/patterns/` (+ `target-curves/`) | hypotheses, accumulated | "in similar conditions this often worked" — starting points, incl. standard target curves |
| 3 | **Engineering Profile** | project · `autosound_context.md` | objective, per-car | car/body, install, DSP, drivers, config, constraints, engineering-constraining goals |
| 4 | **Preference Profile** | project · `preference-profile.md` | subjective, per-car | pure voicing preferences — applied ONLY after the objective tune (Phase 6) |
| 5 | **Project State** | project · `dsp-state` · `tuning-changelog` · `audit-trail` | dynamic, per-session | measurements, decisions, history, current DSP state |

**Skill = layers 1–2 (shared, model-agnostic). Project = layers 3–5 (per-car, dynamic.)**

## The two governing rules

1. **Patterns are hypotheses, never rules.** A pattern proposes a *starting point*; measurement
   or the ear decides. (See the banner atop every `references/patterns/` file.) Core Methodology
   rules and safety steps are firm; patterns are not.
2. **Objective before subjective.** Layer 4 (preferences) never overrides layers 1–3 engineering.
   Engineering-constraining goals (reference seat, competition format, hard constraints, physical
   ceilings) are **not** preferences — they belong to the Engineering Profile (layer 3). Only pure
   taste (warm↔bright, loudness habit, favourite tracks, curve character) is Preference Profile.
   Detail: [`preference-profile.md`](file:///skills/autosound-tuning/references/core/preference-profile.md).

## Evolution (governance)

The methodology changes only via the Owner-approved loop — Observation → Hypothesis → Validation
→ Proposal → Review → **Approval** — never automatically. A new tuning insight starts as a
*provisional* pattern, and is promoted into Core only after it holds up. See
[`review-loop.md`](file:///skills/autosound-tuning/references/core/review-loop.md) and the Skill
Maintenance Loop in `SKILL.md`.
