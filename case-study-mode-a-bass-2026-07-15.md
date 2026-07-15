# Case study: one hard bass problem through the Claude ↔ Gemini ↔ Human triangle

*A verbatim-based account of a single tuning round (2026-07-15, VW Passat B8 sedan / Helix DSP Ultra S), showing how the three-role review loop — **Claude as Generator/Orchestrator, Gemini 3.1 Pro as Critic, the human tuner as Arbiter** — turns a fuzzy listening complaint into a measured, non-obvious fix. Dialogue quotes are translated from Ukrainian; all numbers are the session's real measured values. The doctrine files this session updated shipped as skill v2.6.1.*

**Why this round is worth reading:** every role got something *wrong*, and the loop caught all of it. The human's ear proposed a fix the measurement refuted; Claude's first proposal contained an over-cut the critic didn't catch but the ear did; the critic's numeric predictions lost twice to a one-script check — while its *physics* objections reshaped the final settings twice for the better. No single participant would have landed where the triangle did.

---

## The setup

A locked, hardware-attested front stage (crossovers, delays, per-channel EQ, a validated complementary center-fill). Fresh-ear verdict at session start, driver's seat:

> "The double bass **booms** a little. The low end **pulls the stage corners down**. Low frequencies on the right-center are dragged right. The lower midrange leans left."

And one earlier data point from the tuner's own experimenting:

> "I moved all four mid+tweeter delays together by +0.12 ms and the right woofer by −0.07 — **the bass sounded better** to my ears. Not perfect, but better."

## Act 1 — the ear vs. the measurement

The obvious move — formalize the tuner's delay deltas and enter them properly. The Generator instead ran the skill's jitter-robust joint scan (`robust_worst_null`, ±20 µs / ±0.5 dB perturbations) over the fresh same-session sweeps:

| Joint | robust worst-null at current delays | with the ear's deltas |
|---|---|---|
| woofer↔mid L | −2.08 dB | −2.40 |
| woofer↔mid R | −3.64 dB | **−4.60** |
| sub↔woofers | −3.06 dB | −3.14 |

The layer-delay scan's optimum sat at **0.00…−0.04 ms — the delays were already optimal**, and the ear-preferred deltas measurably *worsened* the right joint. The delay branch was closed negatively: the ear had been reacting to something real, but the mechanism wasn't joint phase.

The real mechanism surfaced in the MMM shape data: a left-door null at 120–180 Hz with a **+4.2 dB modal ridge at 188 Hz** right beside it, a **+3.4 dB hump at 134 Hz** on the right woofer, and a broad **+5.3 dB left-side excess at 250–400 Hz**. THD tables cleared the drivers themselves (a scary "4.4 % @ 160 Hz" turned out to be the fundamental collapsing into the null while harmonics radiate outside it — 0.2–0.5 % at loud neighboring points; that disqualifier is now doctrine).

## Act 2 — the proposal and the first critique

**Claude's package (3 filters):** cut the 188 ridge (w-L, PK −3.5 Q5), cut the 134 hump (w-R, PK −3.0 Q5), and flatten the left skirt with PK 300 −2.5 Q2 on the left woofer.

**Gemini's strongest objection (iteration 1):**

> "A wide Q2 EQ at 300 Hz on w_L sits in the woofer's stop-band (LPF 215) and right in the middle of the w↔m acoustic joint. Equalizing a stop-band to fix the summed response will inevitably rotate w_L's phase in the summation zone — extremely risky for the joint's integrity."

Claude didn't argue — it computed. Applying the filter model to the measured complex responses:

| w↔m L joint | robust / clean / median |
|---|---|
| baseline | −2.08 / −1.99 / −0.23 |
| + PK 188 | **−1.78** / −1.70 / −0.35 |
| + PK 188 + PK 300 | **−1.59** / −1.51 / −0.27 |

The feared filter **improved** the joint — the cuts removed conflicting energy (max phase rotation: 8.2°). But the critique triggered a check that mattered: was the 250–400 excess really the woofer's? Measured per branch, **both** branches were hot (woofer +4.7, mid +5.2 dB L−R) — a broad near-side cabin gain, not one driver's resonance. Cutting only the woofer would fix ⅕ of the sum. Claude proposed moving the 300 Hz cut to the **virtual (per-side, pre-crossover) layer**: both branches rotate identically, the joint can't move by construction.

## Act 3 — the second critique: where the critic earns its seat

Gemini, iteration 2, rejected the virtual-layer elegance with a physical argument no number on hand could settle:

> "The door woofer and the pillar mid have radically different acoustic loading and reflection geometry. A virtual-layer cut will eat the mid's **direct** sound in its lower working band, while the door's **reverberant** excess stays — you'll get an even summed curve and a worse direct/reflected balance, thinning the vocal body on the left."

(The same reply also flagged a "context drift" that was actually a stale context file in the critic's own briefing mirror — the watchdog policing ghosts; the mirror-freshness ritual is now doctrine too.)

The resolution: **per-branch OUTPUT cuts, sized by each branch's measured share** — the woofer keeps PK 300 −2.5 Q2 (the joint *improves*, measured), the mid gets its own PK 320 −2.5 Q2 (joint still better than baseline: −1.77). Convergence in two rounds. The triage rule this produced: **verify a critic's numeric predictions by script before complying — but treat its physical-mechanism arguments as design input.** Gemini lost both numeric exchanges and still improved the final package twice.

## Act 4 — the Arbiter closes what no model could

The tuner entered the four filters and listened:

> "The booming is gone — Chopin, Caravan, Pink Floyd all clean. **But on Metallica the sub now localizes behind me.**"

Measurement found what the ear had caught: the two left-woofer cuts' skirts **stacked**, delivering −5.1 dB at 175–210 where −3.5 was intended — an over-cut of exactly the front punch zone whose harmonics forward-mask a trunk sub. Softening the ridge cut (−2.5, Q7) re-anchored the bass front. (New doctrine: score a package's *summed* curve per channel, never each filter alone.)

One symptom remained:

> "Everything is in the dash now, but low. I want the bass image up on the windshield, where it used to be."

The insight: the *disease* (the hot left 250–430) had been doing vertical work — pillar-height harmonic energy was holding the bass image up. The fix could not be to re-add the imbalance. Instead: a small **symmetric** in-band lift on the mid *pair* (PK 520 +1.2 Q1.8 both sides) — pillar-height harmonics restored without the left skew.

The Arbiter's final verdict, verbatim:

> **"Саб на капоті!"** *(The sub is on the hood!)* — the bass image projected forward and up, past the windshield.

## The scoreboard

| Role | What it contributed | What it got wrong (and who caught it) |
|---|---|---|
| **Human (Arbiter)** | The only source of "how it actually sounds": the initial symptom map, the sub-rearward regression, the height loss, the final verdict | The delay-experiment mechanism (caught by the robust scan) |
| **Claude (Generator)** | State discipline, measurement digests, every numeric claim settled by script within minutes, the symmetric-height insight | The stacked-skirt over-cut (caught by the Arbiter's ear), the virtual-layer shortcut (caught by the Critic's physics) |
| **Gemini (Critic)** | Two physics arguments that reshaped the final settings; honest drift-watchdog pressure | Both numeric predictions (settled by script against measured data) |

Five doctrine updates and two device-knowledge facts from this one session folded into [skill v2.6.1](CHANGELOG.md) the same day — that is the co-development loop the skill is built on.

---

*The method behind this: `references/core/review-loop.md` (cadence, triage, anti-anchoring) and `references/core/data-contract-universal.md` (the package format that forces falsifiable proposals). The full un-edited exchange lives in the project's `review-log.md`.*
