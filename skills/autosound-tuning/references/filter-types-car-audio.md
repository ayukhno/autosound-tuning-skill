# Crossover filter types for car audio

## Quick comparison

| Type | FR slope | Phase | Impulse | For what |
|---|---|---|---|---|
| **Linkwitz-Riley (LR4)** | Sharp knee, −6 dB at the cutoff | Steep rotation | Medium | Precise crossover alignment, sum = 0 dB |
| **Bessel (BE4)** | Gentle knee, early roll-off | Linear delay | Best | Naturalness, "air" |
| **Butterworth (BW4)** | Flattest passband, −3 dB at the cutoff | Compromise | Good | Sub LP, general use |

---

> **Slope choice also maps to the whole-system GOAL** (a by-ear variant, field-confirmed): **LR4 on EVERY joint + time-align by IR first-arrival = a precise STAGE** — the pick for strict imaging rulesets (EMMA-type, where the image/centre must lock). **Gentle / Bessel with wider overlaps = a natural, coherent blend = "beautiful"** — the pick where the stage is less demanding (AYA-type). The per-joint tradeoffs below refine this. The impedance angle (each HP above the driver's installed Fs — the margin scales with the slope; never cross on coincident neighbour resonances) → `impedance-ts.md`.

> **Three layers of a crossover number — keep the PROVENANCE straight (a unifying frame).** A crossover value comes from THREE different sources; conflating them is how anchoring sneaks in:
> 1. **START frequency ← the DRIVER's physics** — impedance / installed Fs: where it naturally rolls off, a safe HP above Fs. An anechoic / NTT starting guess (`impedance-ts.md`).
> 2. **TYPE & slope ← the GOAL** — EMMA → LR4 every joint; AYA → gentle/Bessel (the slope↔goal note above; `method-hashimoto.md`).
> 3. **FINAL frequency ← the CABIN's physics** — the in-car phase-summation: where the SUM is flat on **both** sides (minimax, §L/R symmetry). NOT the start number, NOT a table.
> **Provenance discipline:** always be clear WHERE a number came from — an arbiter/brief decision (START) vs derived-from-measurement vs final-verified-by-summation. **Never present a start/arbiter number as if it were "found from analysing the curves."** **Pre-flight sanity (Phase 0→1):** before entering the start crossovers, glance the raw per-channel roll-offs (is a crossover landing in a neighbour's roll-off? does the driver reach with margin? which side is the minimax constraint?) — not to finalise (summation finalises, after applying), but to catch an obvious problem early.

## Linkwitz-Riley (LR)

**Character:** mathematically exact, an ideal sum (0 dB at the joint with the right cutoff).

**When to use:**
- Midbass/mid joint (the drivers are physically far apart → a wide overlap region is dangerous)
- When you need a predictable, stable stage
- If the drivers are in different acoustic conditions (door vs pod)

**Quirks in a car:**
- With identical L and R cutoffs it gives a reproducible stage
- If one driver has a resonance at the cutoff frequency, LR will emphasize it (needs EQ)

---

## Bessel (BE)

**Character:** linear group delay → the best transient response → a "fast", natural sound.

**When to use:**
- Sub/midbass joint (gives a "cohesive", articulate bass)
- Mid/tweeter joint **when the drivers sit close together** (< 5–10 cm between centers)
- If LR gives a "sterile" or "processed" flavor

**Quirks in a car:**
- Gentle knee → a large overlap region → risky with physically spaced-apart drivers
- You need to spread the cutoff frequencies: where LR would put 300 Hz on both — for BE: LP 250 Hz / HP 400 Hz
- Sub/midbass on BE: sub LP 45–50 Hz, midbass HP 65–75 Hz (asymmetric)

**Bessel 12 dB/oct (BE2) vs 24 dB/oct (BE4):**
- BE2 — a very gentle roll-off, risk of overloading the drivers with below-cutoff frequencies
- BE4 — the safer choice, keeps Bessel's advantages

---

## Butterworth (BW)

**Character:** maximally flat passband up to the cutoff.

**When to use:**
- Sub LP (a slightly harder cut than LR)
- Subsonic to protect the sub (BW 12 dB/oct — a gentle protective roll-off)

---

## Hybrid strategy (a candidate for 3-way + sub)

```
Sub (LP) ←─── BE4 ───→ Midbass (HP)    [Bessel: cohesive, natural bass]
                           ↓
Midbass (LP) ←── LR4 ──→ Mid (HP)      [LR: precise alignment, stable stage]
                              ↓
Mid (LP) ←──── BE4 ────→ Tweeter (HP)  [Bessel: if close; LR if far apart]
```

**Why this way:**
- BE on the sub removes the bass's "drag" and "boominess" from behind
- LR on midbass/mid gives control even with spaced-apart drivers
- BE on mid/tweeter (if in the same pod) gives incredible cohesion and "air"

---

## Starting crossover sets (variants — there can be several)

These are **starting points**, not law: the sets grow over time and get refined by measurement (RTA magnitude + slopes → frequency; joint summation → phase/polarity) and by ear (slope → `method-hashimoto.md`). **A specific project's current choice lives in `dsp-state-current` + profile §4**, not here.

**Set A — "measured hybrid" (3-way + sub; proven on the Passat B8):**
| Joint | Start | Why |
|---|---|---|
| Sub LP ↔ Midbass HP | BE4 45–50 / BE4 65–75 — or LR4 60–63 / LR4 60–80 | BE = cohesive, articulate bass; LR = control |
| Midbass LP ↔ Mid HP | LR4 250–350 symmetric | spaced-apart drivers → a wide overlap is dangerous |
| Mid LP ↔ Tweeter HP | BE4 2500–3500 / BE4 4000–5000 (drivers close) — or LR4 3000–3500 (spaced apart) | Bessel gives "air" on close drivers |
| Subsonic (sealed) | BW2 15–20 | protection |
| + HSF on the midbass at the top | ~400–450 Hz, −4..−6 dB | "trims" the driver's tail above the LP |

**Set B — Hashimoto start (by-ear):** sub↔midbass 60–80 · midbass↔mid 200–1000 (lower for a large-cone midrange, up to 1000 for a small/dome one) · mid↔tweeter 3–6k; **the slope is chosen by ear BEFORE the frequency** (`method-hashimoto.md`). Each driver's HPF — at/above its resonance.

> L/R symmetry of types/orders is the default rule (below), but measured exceptions happen: an asymmetric mid HPF in the winning config, the Hashimoto variant "L/R frequencies/orders need not match" (`diagnostic §15`). The judge — joint summation + the ear.

---

## Practical tips

### How to check you chose right

1. Set up one preset with LR4, another with BE4 on the same joint
2. Listen to a double bass or a plucked guitar — on BE4 the attack is crisper and "faster"
3. Check the Impulse Response in REW: the BE4 peak is cleaner, fewer "tails"

### L/R symmetry — the SQ default

**Default:** the left and right channel of one band have the **same type, order AND frequency** of crossover.

Different ones (BE4 on the left / LR4 on the right — or 3.2k left / 3.5k right) = different L/R phase rotation = the phantom center drifts and smears. Compensate cabin asymmetry with **EQ and Gain** (+ delays for centering), **not with crossovers**.

**Choosing the symmetric value when the sides differ — minimax:** the cabin is L/R-asymmetric, but the crossover stays symmetric — so place the shared frequency to satisfy the **WORSE (more-constrained) side**, so the joint holds on BOTH, not at the better/average side. ⚠️ And don't read that from one channel's **in-cabin** slope near the band edge: an installed per-channel FR there is driver × cabin × mic-path and is distorted **differently L vs R for the SAME driver** — the apparent "natural rolloff" can be all cabin. Read the real joint slope/level from the **both-sides SUMMATION** in the car, not one channel's in-cabin LP/HP.

> **Variant (Hashimoto):** asymmetric L/R crossovers, tuned by ear each side separately — allowed **only when symmetry won't image**; then verify the imaging carefully (`method-hashimoto.md`). The default stays symmetry.

### Driver protection with Bessel

Because of the gentle knee, BE passes more energy below the cutoff:
- On the midbass: HP cutoff a bit higher (65–75 Hz instead of 60 Hz)
- On the mid: HP cutoff higher than with LR (350–400 Hz instead of 300 Hz)
- Watch the midbass cone excursion on loud bass

### Acoustic summation at the joint: LR4 "at one frequency" is a SPECIAL case

The electrical crossover frequency ≠ the acoustic summation point. At the joint TWO curves add (driver+filter each), and the result is set by their mutual **PHASE** in the overlap region — and each filter order adds ~45° of phase near the knee.

- **LR4 (4th order each leg) — the convenient case:** both legs at the SAME frequency give an in-phase sum ≈ 0 dB (a flat joint). That's exactly why "LP = HP in frequency" works for LR.
- **Any other type/order** at one frequency gives **EITHER a dip** (the phases diverge) **OR a hump** (Bessel summation ≠ 0 dB). This isn't a "mistake" — it's the phase behavior of the type/order.

**So the task is not "symmetric vs spread" by a table, but to PREDICT the cutoff frequencies (accounting for type, order AND phase/paths IN THE CABIN) so the ACOUSTIC sum at the joint comes out right → and to verify it by MEASURING the sum, not just by electrical numbers.** The examples below illustrate the principle, not universal numbers:

- LR4: both legs at 3500 Hz → sum ≈ 0 dB.
- BE4 by hand: spread them (e.g. mid LP 2500 / tweeter HP 4000–5000) **or** drop one leg's level a touch — so the hump disappears.
- Via NTT (`process-phases.md` step 5b): you give the tool type/frequency/order → it computes per-band targets with summation coefficients. But cabin phase/path matter too → the resulting targets = **a starting prediction, verify by measuring the real sum**.

⚠️ Don't confuse this with **L/R symmetry** (§above: the same type+order on the left and right — remains the law). Here we're talking about choosing the FREQUENCIES at the joint BETWEEN bands, not L vs R.

> **Slope predictability (why crossover ↔ linearization are iterative):** the raw crossing point of two drivers **lies** if there's a breakup peak/hump in the joint region — the electrical filter on top will give the WRONG acoustic slope. So clear the gross peaks in the overlap region first (Output EQ, `process-phases` 2a) to make the acoustic slope predictable, then refine the crossover. This isn't strictly linear (crossover Phase 1 → EQ Phase 2) but **iterative**: if you touched EQ near the joint — re-check the joint summation.
