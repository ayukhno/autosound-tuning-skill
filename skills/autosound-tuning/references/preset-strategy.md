# Preset strategy — which preset library to build

One DSP config = **one OUTPUT base (correctness, curve-agnostic)** + **several VIRTUAL voicing presets** for different goals (the base+voicing mechanism → `diagnostic-techniques.md §6`, `SKILL.md §Session lifecycle`). Switching a preset = swapping the **voicing/upper-layer settings**, not the base. Here — *which presets* are worth setting up and how they differ.

> The specific preset set is a project decision (determined at intake: purpose + the DSP's preset-count limit, `project-intake.md §2/§4`). Below — a typical reference library, not dogma.

## What varies BETWEEN presets (and what doesn't)
- **The base (does NOT vary):** crossovers, TA, polarity, joint phase, per-channel linearization, L/R shape-match. This is the "correct instrument" — one for all presets.
- **Varies in a preset:** voicing (curve/tilt/shelves on virtual) · center/rear on-off · sub level/extension · DSP-FX · **the source/input** · special stage techniques (crossfeed — below).

## A typical preset library
1. **SQ / reference** — the exact target curve, neutral voicing (Accurate/the chosen reference), often front-only. For critical listening and judging.
2. **FULL / "for yourself" / enjoyment** — envelopment: center + rear on, a warmer voicing (Laid-back type), a hotter sub. For daily enjoyment.
3. **SQL (SQ + Loud)** — like SQ, but with level/headroom margin and a slightly reduced subsonic (so it doesn't boom at volume). Loud, but quality.
4. **Surround / DSP-FX** *(if the DSP has it, e.g. Virtual X / sound-field)* — a separate preset, because FX changes the phase/measurement (measurements with the `FX` suffix). **Capability-driven:** it appears from the hardware's abilities — e.g. a Goldhorn processor with a surround DSP opens a surround preset. So **the set of available presets depends on the project's equipment** (determined at intake §4; hardware experience → `knowledge/dsp/`).
5. **Source / input preset** — for a **different source**: e.g. a daily preset where **navigation comes from the head unit, and music — via BT/USB from the phone**. Here the input routing differs (and sometimes the mix of navigation prompts). ⚠️ A preset here is **bound to the input** — document the "preset → active input" pair; switching a preset can **silently reset the input** (Pre-session §4, `competition.md`) — the most annoying loss of sound/points.

## Competition presets — for the RULES, not "in general"
Different formats judge differently → competition presets for **EMMA / AYA / CARMusic differ**, and the techniques can be **mutually exclusive**. Keep them separate, not "one competition".

- ⚠️ **A different format can need a different FOUNDATION, not just a different voicing.** EMMA (LR4 on every joint, a locked stage) vs AYA (gentle/Bessel, a natural blend) differ at the **crossover/TA** level — so the second format's preset is **not a voicing swap on the same base**; it carries only the curve-agnostic foundation (drivers/T-S/box, the cabin map, measurements) and **rebuilds crossovers + voicing from scratch** (`SKILL.md §Session lifecycle`). Its **NTT per-band targets are crossover-dependent → regenerate them**, don't copy the other format's targets (`process-phases.md` step 5b); keep each format's artifacts in its **own `target-curves/<preset>/`** so they don't leak.

- **Crossfeed (L↔R blending)** — mix a fraction of the opposite channel into the front (a bit of L into R and vice versa) → **stabilizes/compresses the stage toward the center**, removes extreme lateralization; the cost — less width and separation.
  - **EMMA — applicable** (per the user's practice): L→R and R→L blending to **stabilize the stage**.
  - **AYA — NEVER** (a different judging philosophy — natural width/separation is prized).
  - ⚠️ This is a **by-practice variant**, bound to a specific format and season (format rules change — `competition.md`); keep it as a conscious preset choice, not a general rule. Don't confuse it with the **rear-fill differential L−R matrix** (that's for the REAR, for envelopment — `voicing-by-ear.md §Rear`); crossfeed is for the FRONT, to narrow the image.

## Discipline
- **Keep all presets at once** for an on-the-spot A/B with fresh ears (pick for the day/category/source).
- **Log in the changelog:** each preset = name + goal + (input, if specific) + special techniques (crossfeed, etc.). Naming `voicing:<intent>` → `naming-and-structure.md §5`.
- **Back up each** named state in `dsp-config/` (+ the README map).
- ⚠️ **The preset-count limit** in the DSP is finite (intake §4) — prioritize which ones this owner actually needs.
