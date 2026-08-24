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

## 1a. An abstention is half an answer — ASK, and say what it costs

Abstaining stops a tool being believed where it has no vote. It does not get the tuner any closer
to an answer, and on its own it quietly moves the work onto whoever reads the output: they now
have to work out **what** is missing, **who** can supply it, and **whether it matters**. Left
there long enough, "unknown" becomes wallpaper — a column of question marks nobody acts on,
which is the same fate as a warning nobody reads.

**This applies to a missing INPUT, and only to that.** A tool silent because it is out of its
domain (§2) is a different thing: nobody can supply "the excess-phase gate's opinion below 150 Hz",
because it does not have one — something else governs there, and the table in §2 says what. Asking
the Arbiter for a fact that does not exist is worse than silence, since it reads as a real gap and
gets a real answer invented for it. **Ask only where an answer exists and somebody holds it.**

So a tool that abstains for want of an INPUT must, in the same breath:

1. **Name the missing fact precisely** — the profile key, the field, the measurement. Not "the
   profile is incomplete": `channel_gain.step_db`. A gap that cannot be named cannot be filled,
   and it is indistinguishable from a shrug.
2. **Say what it costs** — what is blocked outright, what is merely unverified, and what is
   unaffected. This is the part that decides whether the Arbiter interrupts the session or writes
   it on a list, and it is the part most often left out.
3. **Address it to the Arbiter, when only they can supply it.** A fact that lives on a PC-Tool
   screen, in the car, or in the tuner's own decision is not going to be derived. Asking is the
   only path, and asking late is what makes it expensive.
4. **Roll repeats up.** Thirty-six identical "not stated" lines are one missing fact, and printed
   per item they bury the one finding that actually blocks.

**Grade the ask by what it stops, because that is what the Arbiter is deciding:**

| grade | when | what it looks like |
|---|---|---|
| **STOPPER** | the work cannot proceed, or would proceed on a guess | ask immediately, name what halts, and wait |
| **DEGRADED** | it proceeds, but a specific check cannot run | ask now, state what is going unchecked meanwhile |
| **SLOW** | nothing is blocked; the answer makes a derived thing observed | put it in the queue, do not interrupt |

⚠️ **The grade is about the WORK, not about how interesting the fact is.** A missing crossover
range blocks nothing when every corner is far inside any plausible range — that is SLOW, however
much it looks like a hole. A missing channel-gain step blocks nothing either, until somebody
enters a half-decibel trim, and then it was always a STOPPER. **Re-grade when the work changes;
a gap does not keep the grade it was born with.**

⚠️ **And never let an ask become a guess with a question mark after it.** "Presumably 0.1 dB —
confirm?" is how a plausible number enters the record: the next reader keeps the number and drops
the query. State the gap, state the cost, propose nothing.

Worked example — `resonalyze_vc.py` reading a tune against an incomplete DSP profile. It reports
`enterable: null` per field, each verdict naming the profile key that would settle it, and rolls
them up: *"`parametric_eq.freq_range_hz` not stated → 36 checks on eq"*. Four named gaps instead
of fifty-three shrugs. That framing is what got them answered in an afternoon rather than filed.

## 1b. ENTERABLE and MODELLABLE are two questions — never one field

A capability list gets asked two different things by two different callers, and they need opposite
answers:

* a tool that **VALIDATES** something a person already chose asks *can the device be given this?*
* a tool that **PROPOSES** asks *can we predict what it does?*

Chebyshev on a Helix answers yes to the first and no to the second: the processor accepts the
family, an experiment was run and could not identify its mathematics, so the ripple is unidentified
and the filter is not DETERMINED. Validating an entered one as enterable is correct. Recommending
one is not — a search that offers a filter we cannot predict is worse than a search that offers
nothing, because the tuner enters it and then neither party can account for the result.

**They live in different places, and that is the whole fix.** *Enterable* is a fact about a
PROCESSOR and belongs in its `dsp_profile.json`. *Modellable* is a fact about US — which
realisations this code has and trusts — and belongs in `dsp_math.MODELLABLE_FAMILIES`. Putting
"we cannot model this" into a device profile would be recording our own limitation in a file that
describes somebody's hardware, identical across every copy of that profile and stale the day our
maths improves. `dsp_math.options_for(profile_types)` is the intersection, and a proposing tool
should search that rather than either list alone.

This is the sub's 20–300 Hz UI range in mirror image. There, one field answering two questions
would have made a tool REFUSE something possible; here it makes a tool PROPOSE something
unpredictable. Same defect, opposite damage — so when a list is about to be consulted, ask which
of the two questions is being put to it.

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
| joint delay / polarity / APF (`analyze-joints`) | solos whose protective chain is recorded on the capture round, or working captures | a **baseline** solo nobody marked — `check`, no number | record the round first (`capture-protective`); a phase read through an unrecorded `LR4 @100` is out by tens of degrees and looks fine (`project-intake.md §3`) |

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
