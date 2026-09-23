# Research 2026-09-23 — Junction alignment: which measurement at each step

## The question

In car-audio DSP tuning, how is a crossover junction (sub↔midbass, midbass↔midrange,
midrange↔tweeter) aligned in phase and then checked, and with which measurement at each
step? The owner's stated practice: *"the sub–midbass and midbass–mid junctions, after a
coarse alignment from impulses, are always corrected in PHASE — both need a SWEEP — and
then CHECKED by the SUM at the junction measured with RTA (moving-mic / MMM)."* Is this
confirmed, refined, or contradicted by the method's own docs, the research tree, and
outside practice — and what exactly is swept, what is read from it, what the RTA sum
checks, at what smoothing, whether mid↔tweeter is done the same way, and what to do when
sweep and RTA disagree?

## What the method's docs say now

**The owner's practice is confirmed in outline, but the docs split "phase" into two
different corrections with two different instruments, and they name the RTA/sweep
question as a recurring point of confusion — not a settled one.**

### Coarse alignment from impulses (sweep, IR onset)

`phases/phase_1_foundation.md:25` — required evidence for the whole phase: *"per-channel
MMM RTA (FR) + sweep-with-loopback (IR/phase/GD) for every isolated driver."*
`phases/phase_1_foundation.md:46-56` (§2, Gross/Arrival TA): coarse timing comes from the
**sweep's impulse response**, read by hand — *"Use the IR FIRST FRONT (leading edge, NOT
the global peak) of each solo channel"* — never REW's automatic delay estimate. Line 56:
*"Absolute IR time is crossover-independent and should be set early. Joint phase alignment
is a separate, second step done in Phase 2."* This is exactly the owner's "coarse alignment
from impulses" step, and the docs put it on the sweep, not the RTA.

### Fine phase alignment at the junction (sweep) — `phases/phase_2_eq.md` §2b

`phases/phase_2_eq.md:64-79` is the junction-phase section. Order:
*"Midbass (Reference) → Subwoofer → Midrange → Tweeter"* (`:71`), aligned with
*"All-pass filters (APF) or Helix Phase controls rather than shifting raw channel
delays"* (`:74`). Then the load-bearing line, `phases/phase_2_eq.md:76-77`:

> "The final verdict at any joint is determined by **SUMMATION** (uninverted vs.
> inverted polarity), not single-position phase values. ⚠️ **Recurring mix-up (tripped
> twice — this skill and `manual_step-by-step`): summation ≠ "needs sweep." The
> polarity/summation verdict is a **magnitude-only power-sum comparison**... via
> **RTA/MMM**... precisely *because* it's "a quick verdict without measuring phase" and
> avoids a single-mic-point combined **sweep** (comb-filtering from two spatially separate
> drivers, worse than the comb-filtering MMM/RTA exists to average out). **Sweep IS
> required**, but only for two *different* jobs at the joint: (a) Group Delay / phase
> rotation (`get_group_delay`, sweep-only — RTA has no phase key), and (b) the min- vs
> non-min-phase (excess-phase) decision on a dip."

This is the method's own explicit **refinement** of the owner's practice: "corrected in
phase" is not one sweep-based act. It is (a) an arrival/delay/APF computation that needs a
sweep (phase, GD, excess-phase — RTA cannot supply any of these, `analysis-playbook.md:9-10`
confirms RTA has no phase key), plus (b) a polarity call that is explicitly **not** read
from the sweep's phase curve — it is read from the **measured magnitude sum**, which can
come from a sweep pair or an RTA/MMM pair. The doc calls conflating these two "a recurring
mix-up," i.e. it anticipates and corrects the exact reading the owner's one-sentence
practice invites.

### The verification tool: sweep pair first, RTA pair as fallback

`phases/phase_2_eq.md:79` — `rew_tool.py analyze-joints` computes delay/polarity/APF only
when "a measured `pair` reproduces the complex solos (`phase_trust_gate` ✓)"; gate trips →
BLOCK, fall back to the magnitude power-sum verdict. In the tool itself
(`skills/autosound-tuning/rew_tool/rew_tool.py:397-403`), the pair is looked up as a sweep
first, RTA second (`PAIR_METHODS = (naming.METHOD_SWEEP, naming.METHOD_RTA)`), with the
reasoning inline: *"a pair swept from the same point goes through that same window — like
against like... An MMM `(rta)` pair is taken too, but it has no impulse, so it turns the
whole junction steady... and an average over the head cannot show the point nulls the
solos' model carries."* `_read_joint_rew` (`rew_tool.py:706-759`) makes this literal: when
the attached pair is an RTA measurement, the reading is downgraded to `STEADY`
(magnitude-only, no phase/delay/APF computed) and the row says why. So the sweep pair is
preferred, not merely tried; the RTA pair is a degraded fallback that still produces a
polarity verdict but no delay/APF number.

### Where the docs are internally in tension (not a contradiction, a scope split)

- `core/diagnostic-techniques.md:19-22` (§3) and `:52-57` (§9) both describe the joint
  polarity/summation verdict the same way as `phase_2_eq.md`: measured sum vs the
  phase-blind power-sum, "a quick verdict without measuring phase," decided by
  **summation**, never by "impulse up/down" or by a vector-sum/phase-math prediction.
  `:57` adds the one place RTA is *required* over a point: *"HF polarity/summation through
  the windshield: use MMM, not a single point. A fixed-mic read above ~4k is corrupted by
  the glass reflection."*
- `core/diagnostic-techniques.md:164-168` (§24) says the opposite emphasis for a different
  question — confirming that a *computed* phase repair (APF/delay) actually reaches its
  predicted null depth: *"MMM spatial averaging MASKS point nulls (−12 dB sweep-predicted
  joints showed as −3..−4 in MMM): verify joint-phase work with a POINT sweep at the LP;
  use MMM for magnitude/tonality (the two-spaces rule: magnitude on RTA/MMM, phase on
  sweeps)."*
- `core/diagnostic-techniques.md:83-96` (§13) cites Ohl's own restriction on MMM, in his
  words: *"MMM is quick and efficient for equalization of a loudspeaker but because it is
  missing the time and phase information, it is not a tool to set up crossovers, time
  align speakers."*
- `phases/virtual-first.md:309-321` (Phase 3, the desk path's in-car verification): the
  junction check that actually happens in the car is a **point sweep from the tripod**
  (`_02 (sw)`), predicted vs measured, per junction band, *"tripod down"* only afterward
  for MMM (`_02 (rta)`) — and that MMM pass is scoped to L/R/ALL/groups and "fine EQ,"
  not to the junction polarity/delay decision.

None of these four contradict each other outright — each names the frequency band or the
question (polarity magnitude vs. null-depth confirmation vs. predicted-model verification)
where its preferred instrument applies — but a reader taking only the owner's one-line
summary would not see that the method reserves RTA/MMM for specific cases (HF polarity,
group-level tonal sums) and defaults to the point sweep everywhere the desk/virtual-first
path's prediction has to be checked "on the same base."

### Mid↔tweeter: same method, one added caution

`phases/virtual-first.md:186` and `phases/phase_2_eq.md:71` both list mid↔tweeter in the
same bottom-up sequence as the other joints, same delay×polarity-by-summation method. The
one addition is `phases/phase_1_foundation.md:107` (also `virtual-first.md:190-193`):
*"Above 1 kHz a joint delay is banked only after the TUNED pair is measured... whole cycles
look alike on a sum and on a phase view, so when the direct-sound reading of a mid↔tweeter
joint (a 2-cycle cut) disagrees with the whole-record one... `predict --align` marks it
UNVERIFIED."* So above ~1 kHz the same sweep/RTA instruments apply, but the window used to
read the sweep must be short (direct-sound gate) because whole cycles of a short wavelength
are easy to mistake for each other; `virtual-first.md:253-259` states the general rule
("Junctions, phase and arrival read through the **gate**... magnitude against a target
reads the **whole record**") and gives the failure mode measured on the reference car: a
6-cycle gate misreads by 5 dB at 215 Hz while it is accurate to 0.03 dB at 2 kHz.

## What the research tree has

Role `research`'s own out-of-sample check on the sweep-window question
(`research/docs/SKL-039-five-questions.md` §4, S-005) **tests the skill's own 6-cycle FDW
window** used by `analyze-joints` and finds it still misleading on 3 of 10 cells above
1 kHz; a 1.5–3 cycle window held on all ten in-sample cells, but the out-of-sample Passat
check (§4, "refuted by the letter") found both hand tunes were simply off the drivers'
raw arrival by ~0.7 ms, so it did not actually test the window question — *"S-005 still
needs a car whose hand tune sits on the arrival."* This is a live, unresolved item, not a
confirmed method fact: the skill uses a 6-cycle gate today, and the tree's own probing says
that number is not yet validated end to end.

`research/docs/SKL-039-sources/q5-junction-rules.md` and `q5-car-practice.md` are dossiers
of outside sources (crossover slope theory and car-practice respectively), gathered by the
`research` role for a different but adjacent question (which crossover *slope/frequency*,
not which measurement instrument at the junction). They contain the Audiofrog, Rane,
BestCarAudio, Resonalyze-source, and AES material used below in "What external sources
say" — cited here under their original locators rather than re-derived, since this file's
question is upstream of theirs (how you *measure and verify* an alignment, not which
crossover to pick).

No file in the research tree addresses "sweep vs RTA at a junction" as its own question;
the closest is the alias-witness window study above, which is about the sweep-side gate
width, not the RTA/sweep choice itself.

## What external sources say

**Audiofrog / Andy Wehmeyer, "Time Alignment Part Three: Delays and Crossovers for
Tweeters and Mids"** (https://www.audiofrog.com/time-alignment-part-three-delays-and-crossovers-for-tweeters-and-mids/):
states the target plainly — *"the band of frequencies that both speakers play should sum
flat... we are trying to come up with filter shapes and filter phase that are complements,
so that the sound we hear (or the mic hears) seems like it comes from one speaker with flat
response."* The corner is chosen from the driver's **off-axis curve at the real listening
angle** (a worked 30°-off-axis, 2.7 kHz example), and a distance/time error at the junction
is shown to produce comb-filter dips in the *summed* response — i.e. the diagnosis runs
through the sum, and correcting it is a time/delay question. The article does not name RTA
vs. sweep as separate tools; it treats "the sum" as the one thing to get flat, measured at
the listening position.

**Rane Note 160 ("Linkwitz-Riley Crossovers: A Primer"),**
https://www.ranecommercial.com/legacy/pdf/ranenotes/Linkwitz_Riley_Crossovers_Primer.pdf:
pure filter theory — an LR pair at matched cutoffs sums flat in magnitude because each leg
contributes 360° (≡0°) of phase shift at the corner; a Butterworth pair at −3 dB/side sums
to a +3 dB bump. This is the electrical *reason* a flat sum is achievable, not a
measurement-practice statement; it says nothing about RTA vs sweep.

**BestCarAudio.com (Dave MacKinnon), "Car Audio Crossover Slopes, Alignments and Summing"**
(https://www.bestcaraudio.com/crossover-slopes-alignments-and-summing/) and **"How Audio
Signals Sum Around Crossover Points"**
(https://www.bestcaraudio.com/how-audio-signals-sum-around-crossover-points/): same
arithmetic as Rane, in plain trade-press language, plus the practical corollary that a
2nd-order Butterworth pair needs one driver's polarity inverted to sum flat. Again framed
purely around the summed magnitude at the crossover; does not distinguish RTA from a point
sweep as instruments.

**Resonalyze (DIMOSUS/Resonalyze, GitHub source, read via `gh api`)** — the closest outside
source to this method's own tooling, and the most direct confirmation that "sum" and
"phase" are different computations there too. Its junction tuner
(`dsp/CrossoverJunctionTuner.cs`) scores a candidate crossover on the **coherent sum**
(loss + dip + ripple) computed from the pair's measured impulse responses, never from an
RTA/array capture — and its own docs (`docs/tech/spatial-average.md`, quoted in
`research/docs/SKL-039-sources/q5-car-practice.md` §2.5) state this as a design principle:
*"The average is a refinement of what is drawn, never the basis of a computation: delays,
polarity, junctions and the summation loss keep reading the impulse responses... a
one-position dip a tune must not chase."* This is a partial **contradiction** of the
"checked by RTA" half of the owner's practice, from the one outside tool built specifically
for this job: Resonalyze never lets a moving-mic/array read feed the junction decision at
all — it stays on point impulse responses throughout, and uses the spatial spread only as a
confidence figure, never as the score.

**AES Technical Committee on Automotive Audio (TC-AA), in-car measurement white paper**
(secondary reporting: https://audioxpress.com/article/standardized-automotive-audio-measurements,
corroborated at https://www.grasacoustics.com/blog/standardizing-in-vehicle-acoustic-measurements-with-aes-tc-aa-guidelines):
formally requires a 6-microphone power-averaged array for *overall* in-car frequency
response reporting (>10 dB seat-to-seat differences documented), because a single mic near
a driver reads "bumpy," especially 200–400 Hz. This backs the case for spatial averaging in
general, but — like the AES material found — says nothing about ranking or verifying a
*crossover junction* specifically; it is about representing the whole system's response,
which lines up with this method's use of MMM for group-level tonal sums (Ws/Ms/TWs) rather
than for the junction polarity call itself.

**Jean-Luc Ohl, "MMM" (moving-mic method), v1.7, Dec 2014** — already in this method's own
`diagnostic-techniques.md` §13 and requoted here because it is the single most direct
outside statement bearing on the owner's claim: MMM's own author states it is *"not a tool
to set up crossovers, time align speakers,"* and separately excludes "R&D of loudspeaker
boxes, crossovers, positions, diffraction, time-alignment" from what MMM is for. This is a
genuine, named **contradiction** of "checked by the sum at the junction measured with
RTA/MMM" if read as the whole story — Ohl's own restriction says the junction decision
itself should not rest on MMM. The method's own docs already treat this as an authority to
respect, which is exactly why they route the *polarity* call through a magnitude-only
comparison (which MMM can supply) while keeping delay/APF/GD strictly on the sweep — Ohl's
restriction covers time-alignment and crossover *setup*, not the coarser
in-phase/out-of-phase magnitude check the method uses MMM for.

**REW (Room EQ Wizard) help — "Alignment Tool," All SPL Graph page**
(https://www.roomeqwizard.com/help/help_en-GB/html/graph_allspl.html): REW's own alignment
tool takes each source as a separate solo sweep (each carrying an impulse response and
phase), and aligns a **pair** by adjusting one measurement's gain/delay/polarity against the
other — either by *"Align phase at cursor"* (matching the two phase traces around a chosen
frequency, with the tool noting *"a better overall alignment might be achieved by inverting
one of the measurements and then aligning phase"*) or by cross-correlating band-filtered
impulse responses (*"Align IRs at cursor"*). The check is a **live-computed sum**: *"a dotted
trace which shows the result of a summation of the measurements ignoring phase"* alongside
the true (phase-aware) predicted sum, and *"Aligned sum generates a new measurement with the
summed results of the alignment settings."* REW itself also warns that trace arithmetic only
means anything once the two are time-aligned: *"For meaningful results measurements that
have impulse responses or phase data should be properly time aligned before they are
combined."* This is the closest external match to the owner's practice as stated: two solo
sweeps, phase/delay set from the sweep, checked by the (predicted, then re-measured) sum.

**Merlijn van Veen, "Subwoofer Alignment: the Foolproof Relative/Absolute Method"**
(https://www.merlijnvanveen.nl/en/nl/studiezaal/166-subwoofer-alignment-the-foolproof-relative-absolute-method):
the reference driver is measured solo and its arrival is fixed as the timing base —
*"Solo the main loudspeaker and use the delay finder to synchronize to its arrival time...
it's absolutely mission critical that you don't touch the delay finder ever again"* — then
the subwoofer's delay and polarity are derived from the **phase overlay** against that fixed
reference at a chosen pivot frequency (Δt = (φ/360)×(1000/f); a worked example needs "5 ms
... in combination with a polarity reversal"). The alignment is checked with a **phase-
corridor criterion** — both traces held within 60° of each other, which he ties to roughly
5 dB or better of summation — rather than by re-measuring the actual summed magnitude on
this page. This confirms the sweep/phase half of the owner's practice essentially verbatim
(solo sweeps, one fixed timing reference, phase overlay decides delay and polarity), but its
stated *check* is a phase-tracking tolerance, not a re-measured RTA/MMM sum — a partial
match, not a full one.

**Audiotec Fischer / HELIX DSP PC-Tool knowledge base, "Time" (Phase & Time Alignment)**
(https://www.audiotec-fischer.de/en/knowledge-base/dsp-pc-tool/time/; live page is a
JS-rendered SPA that would not serve to a fetch, recovered via the Wayback Machine's
2026-05-19 snapshot of the same URL): mandates the same **bottom-up junction order** this
method uses — *"always start with the phase relation between subwoofer and woofer in the
crossover frequency range, followed by the phase relation between woofer and midrange.
Finally the phase between midrange and tweeter has to be adjusted. If you don't follow this
order, you'll get crazy."* It documents the phase **control** itself (a 2nd-order all-pass
at a variable corner, 5.625° steps on sub/mid-high channels, 0°/180° only on full-range/low
channels), but is a controls manual, not a measurement-methodology page: it does not itself
say sweep-vs-RTA sets the value. Elsewhere in the same knowledge base, RTA is named
specifically for *"verification of Time Alignment"* — consistent with "phase set, then
checked by RTA/sum," though the manual never spells out a sweep step by name the way REW and
van Veen do. Manufacturer confirmation of the **junction order**, silence on the
**instrument**.

### Gaps

The three sources above closed the gaps this pass set out to fill. What remains open: no
outside source (this pass or the research tree's) explicitly states the method's own
HF-through-windshield exception for a car cabin specifically, or validates a particular
sweep-window cycle count — those stay internal, single-source claims (see Synthesis).

## Synthesis

Step by step, with the instrument used at each step and its citation:

1. **Coarse arrival (TA), per driver, from the sweep's impulse.** Read the IR leading edge
   by hand (never REW's auto-estimate), against a shared Time Offset across all channels so
   relative timing is comparable (`phase_1_foundation.md:46-56`; `tooling/rew-api-quirks.md:52`).
   **Well-supported**: stated identically in the method's docs, and matches the general
   practice of using impulse/step-response timing for arrival (`analysis-playbook.md:9`).

2. **Fine phase at the junction: delay/APF sized from a sweep.** The two solos (before and
   after the crossover filters, `phase_2_eq.md:68-69`) are read for group delay through a
   short direct-sound window (a few cycles of the junction frequency — 2 cycles above 1 kHz,
   wider below, `virtual-first.md:190-193,253-259`), and this feeds the delay/APF search
   (`predict --align`, `phases/virtual-first.md:186-194`). RTA cannot supply this — it has
   no phase key (`analysis-playbook.md:9-10`). **Well-supported**, and now cross-confirmed
   outside: REW's own alignment tool and van Veen's method both work from solo sweeps
   against a fixed timing reference and set delay/polarity from a phase read (cursor-
   frequency phase match / cross-correlated impulses for REW; a phase-overlay pivot-frequency
   calculation for van Veen) — the same shape as this step, independently arrived at. **One
   source only, and still open**, on the exact window width — the research tree's own
   out-of-sample test (S-005) has not yet confirmed the 6-cycle default the tool ships with.

3. **Polarity at the junction: read from the measured magnitude SUM, not from the sweep's
   phase curve.** In-phase sum exceeds the phase-blind power-sum by ~3–6 dB; a dip means
   flip (`diagnostic-techniques.md:19-22,52-57`; `phase_2_eq.md:76-77`). This sum can come
   from a sweep-pair or an RTA/MMM pair — the tool tries sweep first and falls back to RTA,
   downgrading the reading to "steady" (magnitude only, no delay/APF) when it does
   (`rew_tool.py:397-403,706-759`). **Well-supported**, and this is the point where the
   owner's "both need a sweep" needs the sharpest refinement: the method's own doc calls
   conflating "phase correction" with "the polarity verdict needs a sweep" a *recurring
   mix-up*. REW's own alignment tool treats the sum the same dual way — it draws both a
   phase-aware and a phase-blind ("ignoring phase") sum side by side and explicitly offers
   inverting one measurement as part of finding the better alignment, which is the same
   phase-vs-magnitude split under one roof.

   The **junction order itself** (sub↔midbass → midbass↔mid → mid↔tweeter, bottom-up) is
   independently mandated by Audiotec Fischer's own HELIX manual — *"always start with the
   phase relation between subwoofer and woofer... followed by... woofer and midrange.
   Finally the phase between midrange and tweeter"* — which is a manufacturer confirmation
   of the sequence (`phase_2_eq.md:71`; `virtual-first.md:186`) independent of this method.

4. **Which check-instrument, by band and by question — this is where sources genuinely
   split:**
   - **HF (>~4 kHz, through the windshield): use MMM, not a point** — a fixed mic is
     corrupted by the glass reflection (`diagnostic-techniques.md:57`). This is the one
     place the docs require RTA/MMM outright, and it is **one source only** internally
     (no outside confirmation found for the windshield-specific claim, though the general
     principle that a single point misrepresents a car cabin is corroborated by AES TC-AA).
   - **Confirming a computed phase repair reaches its predicted null depth: use a point
     sweep, not MMM** — MMM's spatial averaging masks narrow interference nulls
     (`diagnostic-techniques.md:164-168`, a measured −12 dB point vs. −3…−4 dB in MMM on
     the same joint). **Well-supported internally** and reinforced by the desk/virtual-first
     path's own in-car protocol, which verifies predicted junction sums against a **point
     sweep from the tripod**, not MMM, precisely because the prediction is itself a point
     model (`virtual-first.md:309-321`, "same base or no comparison").
   - **Group-level tonal/target sums (Ws, Ms, TWs, SW+Ws), band-to-band balance, overlap
     humps: use MMM/RTA**, at 1/6-oct (tone) or `Var` (EQ decisions) smoothing, from a
     six-position hand-held ellipsoid captured at 1/48 oct raw and smoothed afterward
     (`phase_2_eq.md:97-108`; `analysis-playbook.md:50-51`; `diagnostic-techniques.md:89`).
     **Well-supported**, and this is the sense in which "checked by the sum... measured with
     RTA/MMM" is straightforwardly true — for the *whole-group* sum, not the single-junction
     polarity call.
   - **Outside confirmation is thin and one voice (Resonalyze) actively disagrees** with
     using any spatial average to *decide* a junction at all, keeping delay/polarity/loss
     strictly on point impulse responses and using spread only as a confidence figure
     (`research/docs/SKL-039-sources/q5-car-practice.md` §2.5). MMM's own author (Ohl) states
     outright that MMM is not a tool for crossover/time-alignment setup
     (`diagnostic-techniques.md:94`). Audiofrog and the trade-press sources describe "the
     sum" without naming an instrument, so they neither confirm nor contradict the RTA/sweep
     split — that is **our own inference layered onto a source that is silent on it**.

5. **When sweep and RTA disagree — no single tiebreak; the two are answering different
   questions, and the docs give a decision rule, not a default:**
   - A feature (hump or null) visible on a fixed-point sweep but **absent or different in
     MMM**: check whether it is narrow and moves with a small mic shift (~10–30 cm) — if so
     it is positional/spatial interference, not a property of the system, and it must not
     be chased with EQ or a crossover/delay change (`diagnostic-techniques.md:83-96`, the Q-
     ceiling and stay/moves test; also §13's own worked case, a −12 dB solo-fixed null that
     MMM shows only as +5.7 dB).
   - A **predicted** junction sum (from `predict.py`, a point model) is compared only
     against a **point sweep from the same base** — an RTA/MMM pair is refused as a
     verification pair by default and only accepted with an explicit override, and every row
     built on it is labelled `rta` so nobody mistakes it for a same-base check
     (`verify_prediction.py:25-29`).
   - A **computed phase repair** (APF/delay) that measures deep on a point sweep but shallow
     on MMM is not a contradiction to resolve by picking a winner — MMM is expected to show
     less because it averages the null away; the point sweep is authoritative for "did the
     repair reach the depth the model predicted," MMM is authoritative for "does this still
     read as a problem across the head" (`diagnostic-techniques.md:164-168`).
   - The one band where the method reverses this and trusts MMM over a point outright is HF
     through the windshield (`diagnostic-techniques.md:57`) — there the point is the one
     known to be wrong.

**What is well-supported:** the two-instrument split itself (sweep for phase/delay/GD/
excess-phase; a magnitude sum, from either instrument, for the coarse polarity call); the
HF-through-glass exception for MMM; the point-sweep requirement for verifying a predicted
junction null; the group-level use of MMM/RTA for tonal sums. **What rests on one source
each:** the specific 6-cycle sweep window (contradicted by the tree's own preliminary
out-of-sample probing, not yet resolved); the windshield-reflection claim itself (internal
only, no outside confirmation found). **What is our own inference, not stated by any
source:** mapping "which band/question gets MMM vs. sweep" onto the outside sources' silence
on the RTA/sweep distinction — Audiofrog, Rane and BestCarAudio all describe "the sum"
without saying which instrument measures it. **Where a source flatly disagrees with the
practice as stated:** Resonalyze's own design principle and Ohl's own restriction both say a
spatial average should not decide a junction — which the method's docs already anticipate
by keeping delay/APF/GD strictly on the sweep and using MMM only for the polarity magnitude
check (a narrower claim than "checked by RTA") and for group-level sums.

## What this means for two tools

**(a) `rew_tool.py analyze-joints`.** Its current order — look for the measured pair as
`(sw)` first, `(rta)` second (`rew_tool.py:397-403`) — matches the synthesis: a sweep pair
lets it compute the full phase-verified answer (delay, polarity, APF suggestion, residual);
an RTA pair only ever produces the degraded "steady" magnitude-only polarity verdict
(`_read_joint_rew`, `rew_tool.py:706-759`), which is correct for the coarse in/out-of-phase
call but cannot stand in for the delay/GD/APF computation. Two things worth naming rather
than changing, since the design already tracks the research above: the tool does not
special-case the HF-through-windshield exception (`diagnostic-techniques.md:57`) — an RTA
pair above ~4 kHz is currently read the same degraded way as an RTA pair anywhere else,
even though the docs treat MMM as *more* trustworthy than a point up there, not less; and
the 6-cycle FDW default it reads junctions through is the same window the research tree's
own out-of-sample check has not yet validated (S-005) — a caution to carry forward, not a
call to change the number without the still-missing car.

**(b) `state.py verification-set`.** Its rule — a delay/crossover-edge change asks for the
junction pair as `(sw)` (summed); a polarity change asks for the pair as `(rta)`, both
normal and with the moved member inverted (`state.py:706-719`) — is exactly the two-
instrument split found above: delay is a phase quantity (sweep-only), polarity is a
magnitude-sum call that the docs and diagnostic techniques both route through RTA/MMM by
default (reserving the point sweep for confirming a computed null's depth, which is a
different, narrower check this command does not ask for). The "normal vs. one member
inverted" pair is precisely the null/notch-with-inversion check the question asked about,
and it matches `diagnostic-techniques.md:52-57`'s "polarity by SUMMATION... coherent vs
power-sum." Nothing here contradicts the research; the one gap is the HF exception again —
a polarity change on a mid↔tweeter joint already gets `(rta)`, which is the *right* call for
that band per `diagnostic-techniques.md:57`, but the same `(rta)` request for a low-frequency
sub↔midbass polarity change is the routine default rather than a band-specific choice, and
nothing in `verification-set` currently distinguishes "MMM because it's required here" from
"MMM because it's the default."
