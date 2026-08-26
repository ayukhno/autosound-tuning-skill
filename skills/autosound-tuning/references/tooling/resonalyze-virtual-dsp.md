# Resonalyze Virtual DSP — how the instrument works

> 🧩 **TOOL MECHANICS, not method doctrine.** This describes how DIMOSUS's Resonalyze computes a
> virtual tune, so a session can operate it and read its report. **What of this becomes advice the
> method GIVES is a decision only the user makes — this file records how the tool behaves, not what the
> method should do; nothing here is a rule of the method until the user rules it in. Resonalyze stays an
> external Windows/.NET program —
> the skill never takes a .NET dependency and runs no AI at tune time. The maths the method has
> already ported lives in `rew_tool/` (`predict.py`, `dsp_math.sum_loss`, `analyze-joints`); this
> file is the READING of the tool those ports were checked against.
>
> **Provenance.** Every number below is a named constant read from the source of `DIMOSUS/Resonalyze`
> at `ad404ab` (`dsp/AutoAlignmentEngine.cs`, `dsp/VirtualCrossoverAnalysis.cs`,
> `source/Tools/VirtualCrossover/VirtualCrossoverProjectFile.cs`), relayed by the fork session
> 2026-08-25 — not from the README. A constant that moves upstream moves this file; re-read against
> the fork before trusting a number in a decision (`scripts/upstream-drift.py` covers the ported
> code, not this prose).

## 1. The model

One channel = a driver's measurement (loopback-referenced transfer IR) × its DSP chain. Sums are the
**complex** sum. Filters are computed as the **digital biquad cascades the real DSP runs**, so the
prediction tracks miniDSP-class hardware to Nyquist — not a textbook analogue curve. Channels are
stereo **L/R pairs**; `mono: true` means one driver feeds both sums (the usual single sub).

## 2. Two different windows — the most common confusion

The skill must hold these apart:

- **Phase and impulse** are read through a **gate** (Fixed / FDW, 4 / 6 / 8 cycles, detrend
  Off / Auto / Manual).
- **Magnitude** — the channels, the Sum, the Sum-loss and the whole report built from them — is read
  through a **long stationary window ≈ 680 ms** (clipped to 32768 samples at high frequencies). From
  the gate it takes ONLY the offset — where the window opens.

Why, from the code: phase is timed on the direct sound, where cutting to the first reflection is the
whole point; tonal balance is what the ear hears **together with** the cabin. A window as short as a
junction would not even contain the ringing of a bass-band EQ band — a Q5 cut at 100 Hz would draw as
a fraction of its true depth under it.

Every magnitude window opens on the detected **START** of the response (a band-limited first edge),
**never on the IR peak**: a woofer's peak lags its own onset by several ms of group delay, so a
window on the peak opens after the response has already begun.

The same window definition drives Frequency Response and EQ Wizard — that is what keeps both tools on
ONE curve for a given channel.

## 3. The stereo scene

`SceneOffsetMs` (`AutoAlignmentEngine.cs:116`): positive = the **far side must lead** (arrive
earlier). Named "image toward the dash centre".

**Left and Right in the engine are ROLES, not sides.** Left = the reference (driver's side, aligned
first); Right = the far side, fitted to it. LHD maps sides to roles directly; RHD maps the plan
**mirrored**, so the same positive number there makes the LEFT side lead. That is why the UI never
asks for a sign. On the wire the sign carries the layout (`stereoSceneOffsetMs` negative = RHD), plus
an explicit `StereoRightHandDrive` flag so a zero offset still remembers the layout; RHD-with-zero
serialises as −0.001 ms (a marker: a tenth of the UI grid, a twentieth of a sample at 48 kHz — an
exact zero to any consumer). The level twin is `StereoLevelDifferenceDb`, stored as LEFT minus RIGHT,
edited in the UI as a non-negative "near-side cut".

**The localisation zone, hard numbers:**
- `SceneLockLocalizationLowHz = 300`
- a pair binds to the scene only if the top of its band ≥ max(band bottom, 300) × 2^(1/3) — i.e.
  ≥ 378 Hz for any pair whose bottom is ≤ 300
- bound pairs may deviate from target by only `SceneLockToleranceMs = 0.05`
- a pair wholly below the zone binds **looser** — to the arrival lobe — because the ear does not
  localise there, but the delay split between identical drivers is still physical
- `MaximumSceneOffsetMs = 5`: beyond this it is not an image shift but an audible echo

**The time↔level trade, measured on real files.** Compare two Virtual DSP sessions of one tune that
differ in exactly 10 numbers (crossovers, PEQ and polarity byte-identical) — one balanced by level
alone, the other with the stereo scene offset switched on. Switching the offset on grew the L−R
delay difference by that same 0.25 ms on every pair and took ~3 dB of near-side cut back out, so
0.25 ms of tilt replaced ~3 dB of cut → **≈ 12 dB per millisecond**. Textbook for a ±30° pair is
~15 dB/ms (a full image shift at ~1 ms or ~15–18 dB); the order of magnitude agrees, the exact
number does not transfer to a cabin.

⚠️ **0.25 is the program's DEFAULT** (`StereoSceneOffsetMs = 0.25`), not a value anybody tuned to a
car. **The skill must not present it as justified.** The transferable rule is one lever **in place
of** the other, never on top: adding tilt and keeping the old cuts is a double dose. (The method's own
stance on the stereo scene is `diagnostic-techniques.md §23` — a zero of the measured pair-arrival difference, with the tape as
arbiter; whether Resonalyze's scene offset enters the method at all is a user decision.)

## 4. Auto delay: why two stages

The idea the whole design follows: the summation surface at a junction is a **comb**. A shift of
exactly one period of the crossover frequency gives almost the same result — the minima stand a
period apart and differ by fractions of a dB. **The sum cannot pick the lobe; only arrival time can.**

**Stage 1 picks the lobe (physics). Stage 2 polishes inside it and picks polarity (acoustics).**
Locks stop stage 2 from hopping into the neighbouring lobe.

Stage 1 — the seed:
- band-limited first arrival = the coarse anchor
- refined by GCC-PHAT (whitened cross-correlation); it takes the strongest extremum, **peak OR
  trough**, and only its POSITION. Polarity is left to stage 2 on purpose — an inverted junction (sub
  vs midbass) seats on a trough.
- `PhatSeedMinCoefficient = 0.15` — below this the extremum is noise, the arrival estimate stands
- `PhatSeedMinRivalDominance = 0.05` — it must beat the rival A PERIOD AWAY: the cycle-skip guard
- `SeedReachMs = max(3 ms, 500/fc)` — the seed may not move the anchor more than half a period from
  the arrival
- correlation window `max(3 ms, 1.25 periods)` — so both polarity partners fit as whole lobes

**A historical lesson in the code, worth carrying into the method as a caution:** the seed used to be
gated by a "peak vs trough" margin as well. Measurement killed it. On an IDEAL synthetic junction
(two filters from one impulse, no room, no noise, perfectly aligned) that margin = 0.167 at two
octaves of overlap and falls to 0.100 / 0.049 / 0.012 at 1.5 / 1.0 / 0.5 octaves — on any fc, family
or slope. **It measures the bandwidth, not confidence in the extremum.** The old 0.1 threshold
demanded 60 % of what a flawless junction can even produce, and on archived cabins it refused 34 of
40 junctions — including every one the owner's hand-tune later sat on. That number is now only in the
log.

Stage 2 — the fine search:
- a fractional-delay search for the minimum of the sum loss
- range: half a period of fc, but `MinFineAlignmentRangeMs = 0.5`, `MaxFineAlignmentRangeMs = 2.5`.
  The 0.5 floor exists because arrival error has its own floor (the filter's group-delay asymmetry,
  the driver's rise time) that does not shrink with the period
- on a LOW junction the ceiling is raised by `LowJunctionReachFraction = 0.97` of a half-period — so
  the half-period polarity partner fits but the whole-period same-polarity rival does not
- read through a **direct-sound window**, one per junction: it opens on the earlier edge of the two
  channels in their SHARED band, never later than the peak, and its SIZE is set by the band (a 60 Hz
  junction needs milliseconds a tweeter does not)
- the window **travels with the channel** as the search moves it: a fixed window over moving content
  measures itself, not the sum
- scored on TWO numbers — the mean loss in band AND the depth of the deepest smoothed null — plus an
  arrival-prior weight
- `MaxDelayMs = 50` — a feasibility gate: car processors cap delay at tens of ms

## 5. The locks

**ONSET LOCK** — `OnsetLockMinCrossoverHz = 700`. Above this fc the search is pinned to the measured
wideband edge: window = the edge anchor ± `OnsetLockReachPeriods = 0.75` period, and every escape
(edge retry, wide promotion) is shut. The sum is left to polish inside the correct lobe and pick
polarity.
- Why 700 — field data from the comment: at 1.5–2.3 kHz the edge spread between the 10 % and 50 %
  thresholds ≈ 0.3 period (lock engages); at 220 Hz it is already milliseconds (the thresholds catch
  a mode building, not an edge); at 80 Hz there is no edge at all.
- Why 0.75 period: fit the true lobe with edge error (~0.3 period) plus the legitimate group-delay
  split between drivers, PLUS the half-period polarity partner (so inversion rules decide polarity),
  but EXCLUDE the whole-period same-polarity lobe.
- **An honest gate before the lock** — `OnsetLockMaxSpreadPeriods = 0.5`: the edge is read at the
  10 / 25 / 50 % thresholds, and the lock engages only if all three agree within half a period. A
  smeared edge, or one a reflection leads (off-axis driver, modal bass), makes the lock STAND DOWN
  rather than pin the search to a guess.

**WIDE-WINDOW PROMOTION** — `WideWindowPromotionMarginDb = 1.6`, `PromotionReachPeriods = 2.5`. Only
where onset lock is not in charge. Lets a wide diagnostic window overrule the arrival-pinned choice
when the gain exceeds the threshold. Calibrated by measurement: the comb noise between true lobes
reaches ~1.4 dB (a false jump proposed 1.40), a genuine arrival error gives ~2 dB across the null (a
real rescue proposed 1.91); the comment states a sloped threshold cannot separate those two at any
slope — a flat 1.6 does. The 2.5-period ceiling rejects the alias ~3.9 periods out that won on a
0.25 dB "improvement".

**SUB PRECEDENCE** — `SubPrecedenceMarginDb = 1.0`, `SubPrecedenceSlackMs = 0.5`. The ONE place
psychoacoustics beats the summer. On a junction with a shared mono sub, the tie between the lobe where
the sub LAGS the stack and the one where it LEADS is acoustically unresolvable but perceptually
one-sided: the first wavefront binds the bass to the midbass's localised transient (precedence), so a
sub that leads slightly is heard as "bass up front", one that lags as limp and detached. The
threshold sits above the tie scale and just below the ~1.4 dB comb-noise ceiling. Calibrated by the
owner on cabin v3, where the leading lobe lost by 0.66–0.73 dB — and was the one that localised the
bass to the front stage. ⚠️ The 0.5 ms slack: precedence re-decides only a true lobe choice, not
sub-millisecond polish near an envelope-aligned point.

**DIRECT-COHERENCE WITNESS (polarity)** — `DirectCoherenceMinCrossoverHz = 120`,
`DirectCoherenceTieMarginDb = 0.3`, `DirectCoherenceMinR = 0.6`, `DirectCoherenceMinAdvantage = 0.05`.
When the sum score cannot tell a lobe from its polarity partner (thin spectral overlap ties them
within hundredths of a dB), the whitened cross-correlation of the two channels' DIRECT sound decides —
the part of the recording the drivers made while the room had not yet answered.

## 6. What the report symbols mean

**Junction phase**, per junction:
- `φfc` — the lower channel's phase minus the upper's at the crossover frequency. ≈ 0° = in phase.
  **±180° by itself does NOT demand a flip**: an inverted channel and a half-period delay at fc are
  indistinguishable.
- `fix ms` — the extra delay on the LOWER channel that maximises the phase score across the overlap
  - `i` = recommends a flip
  - `~` = a flip is near a tie
  - `!` = the overlap band is too narrow to rule out a whole-period jump — `fix` is NOT to be trusted,
    read the coherence ladder
  - `·` = the correction is worth less than 10° of phase at fc (0.03 dB in the sum); a settled tune
    has nothing to apply there
- `score` (−1…+1) — where the junction stands NOW. 1.00 = aligned, 0 = in vain, negative = the
  drivers subtract. It moves live as you drag the delay, so it, not `fix`, answers "is this getting
  better or worse" — `fix` says only which way, not how far along you already are.

**Auto delay report:** `before -> after` for a changed value, `value (kept)` for an untouched one;
a confidence per delay, `ref` = the anchor, `locked` = the choice was made by an onset/scene
constraint, not by acoustics; `LOW` is raised as its own warning.

**Δ L−R:** positive = the RIGHT side leads (the scene-offset convention).

## 7. Practical, about the instrument

- **There is NO Undo in Virtual DSP.** `Ctrl+Z` / `Ctrl+Shift+Z` exist only in the EQ Wizard, on the
  PEQ band bank (`EqWizardPanel.Bank.cs:638`).
- Everything auto-saves to `%LOCALAPPDATA%\Resonalyze\tools\virtual-crossover.json` and survives a
  restart. "Close without saving" does not work. To roll back: `Load session…`.
- The Auto delay / Auto crossover dialogs write nothing to the project until `Apply` — the code:
  "the inputs the proposal was computed with become the persisted values only now, so a discarded
  experiment does not overwrite them". So flipping switches and pressing Cancel is safe, and the best
  way to learn a dialog.
- Auto delay writes delays and polarity but not levels, until `Balance channel gains (cut-only)` is
  set. Cut-only never raises — headroom cannot be lost.
- The session format is now **VERSION 8**; a version 7 session migrates on load. **Saving over the
  original destroys the v7** — keep the original if it is a shared record.
- The mic calibration travels **inside the session** as the curve itself, not a reference to a list:
  it describes the microphone the measurement was made with, so it belongs to the measurements and
  moves with them.

## Where this meets the skill's own tools

`rew_tool/resonalyze_ir.py` writes v7 files REW → Resonalyze; `resonalyze_vc.py` reads a Virtual DSP
session back as ledger rows; `predict.py` is the method's own full-state predictor, checked against
this engine's arithmetic to 3·10⁻¹⁴ dB on the real set-02. The **sum-loss** metric and the **two-stage
delay** idea are already ours in `dsp_math`/`analyze-joints`; the **arrival-first, sum-second** split,
the **long magnitude window vs gated phase**, and the **precedence exception for a shared sub** are the
readings this file records so a later session does not "fix them back" or re-derive them from scratch.
