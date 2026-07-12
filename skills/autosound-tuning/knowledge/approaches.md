# Approaches — a classifier of tuning/crossover schemes (variants + success stories)

> **The core idea (read this first).** An "approach" (what a tuner means by "an EMMA tune" or "an AYA tune") is **not a slope recipe**. It's about **what's most important to FIND and address in THIS setup** to reach a GOAL. The slope scheme (LR4 everywhere · BW12+BE12 · LR4+BE4 …) is a **consequence** of (goal × setup), not the definition of the approach. So the competition format names a **goal**, never a fixed set of slopes.
>
> ⚠️ **Don't apply a format→slope recipe.** "EMMA = LR4 on every joint", "AYA = gentle/Bessel" are **shorthands and success stories**, not laws. A real counter-example sits right in this file: a builder's **AYA win used LR4 + BE4** — which *contains* an LR4, contradicting "AYA = gentle". The win came from that car+install+gear, not from the format.

## What actually decides the scheme — by DECREASING priority

1. **Body shape** — sedan / hatch / wagon / SUV → room gain, reflection geometry, the dominant cabin behaviour.
2. **Install — where each driver sits** (door / A-pillar / kick / dash / pod), spacing, on/off-axis, coplanarity → the joint geometry and the achievable overlap.
3. **Number of ways** — 2-way / 3-way / + sub / + center / + rear → how many joints there are to manage.
4. **Equipment** — drivers (Fs, breakup, dispersion) + DSP capability (which slopes/types exist at all).

> The GOAL (locked precise stage vs natural coherent blend vs "fun") sits *above* these — it's what the user wants. The four factors then decide **which slopes reach that goal on THIS car.** Find the constraint first; the slope follows.

## The catalog (variants — grows over time; each tagged with its setup + confidence)

| Scheme | Goal it served | Setup context (where it worked) | Result / achievement | Confidence |
|---|---|---|---|---|
| **LR4 (midbass↔mid) + BE4 (mid↔tw)** | natural blend + stable stage | VW Passat B8 sedan · 3-way + sub · mids ≈ coplanar with tweeters on the A-pillar (close) | **Won AYA (junior group)** | **Confirmed by competition — but SETUP-SPECIFIC** (the win is this car+install+gear, *not* "the AYA recipe") |
| **BW2 + BE2 (gentle, wide overlap)** | natural blend (AYA) | same car · a newer attempt | — | **Unconfirmed** — not yet validated by time or competition; a hypothesis |
| **Acoustic-plan decomposition ("v3"): NTT acoustic plan (70/320/3500 LR4) → per-driver electrical realization (mixed LR12/BW24/BW36 by band) + joint-aware pair selection + analytic delay/polarity/APF** | coherent joints + tonality realized from a measured plan | VW Passat B8 sedan · 3-way + sub · Helix Ultra S · mids on A-pillar (method rules → `filter-types-car-audio.md` §Acoustic-plan-first) | attested in hardware: balance ≤1.1 dB residual, healthiest joints in the build's history, "wow, transparent" by ear; center collapsed to a tennis-ball image | **field-confirmed** (one build, no competition yet) |
| **LR4 on every joint** | a locked, precise stage (strict imaging) | — | — | **Unconfirmed as a "format law"** — a goal-driven shorthand ("EMMA-type"); validate per setup |
| **BW12 + BE12** | moderate control + air | — | — | a known variant; log where it's tried |
| **Hashimoto by-ear (slope BEFORE frequency)** | by-ear cohesion | any · `method-hashimoto.md` | — | a method, field-used (`Set B` in `filter-types-car-audio.md`) |

**Confidence ladder:** `confirmed-by-competition` > `field-confirmed` (repeatable in real tunes) > `by-ear` (one tuner's taste) > `unconfirmed` (an attempt / a hypothesis, no result yet). Carry the tag — a scheme without its confidence + setup context is just folklore.

## How to use this file

- **Choosing a start:** name the goal, read the four setup factors for THIS car, then pick a scheme whose **setup context resembles** it — as a **starting hypothesis**, not a fact. ⚠️ Transplanting a scheme to a different setup = a hypothesis to verify by measurement + summation (the same discipline as `knowledge/cars` PART B), never "this won AYA so it's right for you".
- **After a tune:** add/append the scheme actually used + its setup + the outcome (and the competition result, if any) — that's how the catalog earns its ratings. Collected via the closing ritual (`feedback-loop.md`, stream C); winning crossover sets also land in `knowledge/cars/<body>.md`.

## Vision — a public, community-rated classifier (roadmap)

This file is the **seed**. The intent: grow it into a **public (GitHub) classifier of approaches** where each scheme accumulates **community success stories** tagged by setup (body/install/ways/gear), a **preference rating** from users, and **achievement notes** (competition placements). A new project would then surface "schemes that worked on a setup like yours, ranked" — a starting shortlist, still a hypothesis. The rating/leaderboard mechanics + the contribution flow are a roadmap item (`feedback-loop.md`); for now, **keep the catalog honest: variant + setup + result + confidence.**
