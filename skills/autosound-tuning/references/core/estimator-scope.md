# When a number is not an answer

Every estimator here is valid over a range of conditions and silent outside it. This file is
about the seam: what a returned value is good for, where a tool has no vote, and why a
quantity you measured is not thereby a quantity you may set.

It exists because of a measured failure pattern, not a theory. Over one working session
(2026-08-21) a competent operator made six errors, and **five of them were the same error**:
a tool returned a confident-looking number outside the conditions it is valid in, and nothing
in the returned value said so. Three of the five were already documented in prose — in this
very reference set — and the prose did not fire at the moment the number was read.

> **Prose warns the reader. A value warns the user.** Under load a session is a user, not a
> reader: it reads the number, not the docstring the number came from. So scope belongs in
> the return value.

---

## 1. The convention: an estimator must be able to abstain

A tool that cannot say "not here" will be believed everywhere. Every estimator in `rew_tool`
that has a validity domain returns its verdict **alongside the value**, and an out-of-domain
answer **empties the value** rather than merely labelling it.

| Tool | Field | Abstains when | What governs instead |
|---|---|---|---|
| `eq_gate.ExcessPhaseGate.check` | `verdict` | `f0` outside the calibrated band (`trust`) | the flaw map's `no_boost` zones; §13 mic-shift |
| `analysis.arrival_triangulate` | `verdict` | the four estimators disagree by > `spread_ok_ms` | summation at the joint (§9, §10) |
| `analysis.relative_delay_xcorr` | `basis` | both inputs peak at the same index | fix the export first — nothing downstream is valid |
| `contract.check_glossary` | `valid` | two glossary sources disagree | reconcile them; no name check is trustworthy meanwhile |

`OUT_OF_SCOPE` is **not a weak ALLOW.** Record it by that name. "ALLOW 1.2 @ 145 Hz" reads
as permission a month later, and on the source build 145 Hz is a cabin null the flaw map says
never to boost. An abstention must also never act as a veto: a tool with no vote does not get
to block, either (`as_boost_gate` deliberately treats `OUT_OF_SCOPE` as no objection).

## 2. Where each tool is SILENT — so step order can be derived, not asked

Sequencing questions ("do I need the excess-phase gate before the sub↔midbass joint?") are
answerable from the table below and should not cost a round trip.

| Tool | Has a vote | Silent | Consequence for ordering |
|---|---|---|---|
| excess-phase gate | 150–4000 Hz (this calibration) | below ~150, above ~4 k | **not** on the critical path to the sub↔w joint; required before mid/tweeter EQ |
| pair coherence / Δφ climb (§26) | above the pair's own alignment | on an un-aligned pair (see §3) | must run before Phase-1 corner placement — corners avoid multipath pockets |
| `arrival_triangulate` | clean, band-limited drivers (mids, tweeters) | sub and door midbass (ILL-POSED) | delays for those come from summation, so the joint search cannot wait on onsets |
| single-point dips as evidence | below the Schroeder frequency (~150–200 Hz in a car) | above it — Rayleigh statistics, a dip is more likely mic position than car | above it, a peak outranks a dip; six-point mic-shift decides (§13) |
| MMM | tone, spatial truth | phase, timing, anything at one point | never mix an MMM magnitude with a point-sweep phase |

## 3. A measurement is not a setting

Two different quantities wear the same units, and the session that confuses them sets a knob
from a fit.

- **A best-fit delay is not a time alignment.** The τ that maximises a pair's weighted
  coherence is a *fit over a band*; the TA you enter is a *physical alignment*. When they
  agree, alignment is confirmed from two directions and removing the delay is honest. When
  they disagree, the fit is buying coherence by rotating phase, and §26's own trap applies —
  a detrended number understates the divergence. Real case: they agreed to 15 mm and 2.8 mm on
  two pairs and disagreed by **22.5 cm** on the third; adopting the fit there would have bought
  ~2 dB of coherence with 22.5 cm of image asymmetry, in a band where ITD barely works (§12).
- **A gate's statistic is not a permission.** `ALLOW` means "no phase objection", never "safe
  to boost".
- **A pocket measured before alignment is not a pocket.** §26's discriminator asks *what a
  delay cannot fix*; you can only ask it after removing the delay you will actually set. Its
  own field case had the DSP delay in place. Read on raw solos with modifiers zeroed — which is
  what Phase 0 captures — a pair's geometric offset (1.2–1.4 ms here) sits inside the metric and
  reads as divergence. Real case: a "−18.96 dB pocket, deepest in the pair" became **−1.9 dB**
  once the pair was aligned, and would have pushed a crossover corner away from a healthy region.
- **The arbiter for anything the estimators fight over is a measurement independent of all of
  them.** Four estimators disagreed about one pair's delay across a 4.3 ms span, including a
  sign flip between onset and peak. A tape measure from the listening point settles it in two
  minutes, because it is the only one measuring geometry rather than geometry ⊗ cabin.

## 4. What survives a "from scratch"

A restart that discards previous settings discards **decisions**, not **instrument facts**.
A measured constant that describes the rig — electronic latency of the chain, temperature
drift rate, microphone calibration, a driver's measured Fs/T-S — is data about the apparatus
and survives any number of restarts. It is not "an inherited tuning value", and refusing it
costs a re-measurement for nothing.

The test is one question: **would this number be the same if the DSP were factory-reset?**
Latency, drift, mic cal, Fs — yes, they would. Crossover corners, delays, gains, EQ — no.
The first set is a fact about the apparatus; the second is a decision, and only decisions are
what "from scratch" throws away.

Record which one a number is when you write it down, and a later session will not have to guess.
