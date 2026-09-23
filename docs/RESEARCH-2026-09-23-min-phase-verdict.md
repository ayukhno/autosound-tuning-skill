# Research 2026-09-23 — The minimum-phase verdict: how it should be made

Marks used below: **[S]** sourced by two or more independent sources · **[S1]** one source ·
**[P]** project evidence (this repo or `autosound/research`) · **[I]** inference ·
**[syn]** a throwaway synthetic probe run for this note against `eq_gate.py` as shipped
(`64a2084`), not committed.

## The question

For a peak or dip in a car measurement, the method has to decide whether it is minimum-phase
(an EQ filter can correct it) or not (a reflection or cancellation that EQ must not chase).
`eq_gate.min_phase_verdict` (added in `64a2084`, #56 item 3) removes the bulk delay from the
excess phase over ±0.5 oct around the feature and calls the feature MIN_PHASE when the residual
is ≤ 10° rms and ≤ 30° at worst. Those two numbers were tuned on synthetic data only. This note
works out from the sources how the verdict should be made, and whether the helper should change.

## What the method already has

**1. A boost gate on the same signal, validated on one car.** `rew_tool/eq_gate.py:8-21`: a
boost is dangerous only where *"ALL THREE hold at once: dip(f) >= DIP_DB ... S(f) >= Z_WARN ...
w(f) >= 0.5"*. S is the sliding RMS of an excess-group-delay z-score against a ±1-oct rolling
median, normalised by the channel's own MAD over the trust band (`:97-121`). The rolling median
takes out the bulk delay implicitly, so S and the new helper measure the same thing: excess
phase that is not a delay. The gate's derivation is documented (`:27-50`, and the
`sound_AutoSci` suite in `research/wiki/ideas/excess-phase-extraction.md`): 90/90 on synthetic
min- and non-min-phase combs at matched magnitude, 20/25 real Passat anchors with the phase core
alone, *"NOT a certifier"*, calibrated on one vehicle, trust band 150–4000 Hz
(`eq_propose.py:94`, `estimator-scope.md:107`).

**2. Doctrine that scopes the question by frequency and by position.**
- `diagnostic-techniques.md:15` (§2): *"Cancellation vs minimum-phase: excess phase / a **GD
  spike** in the dip (sweep, not RTA); or a **micro mic-shift ±10 cm** (the bottom 'moves' = a
  positional reflective null = EQ won't take it)."*
- `diagnostic-techniques.md:84` (§13): *"the feature STAYS at the frequency = a mode (min-phase,
  cuttable); it MOVES = spatial interference/SBIR (NOT EQ)."*
- `diagnostic-techniques.md:88` (§13): the car's Schroeder frequency is ~150–200 Hz
  (Strauß/Treichel + Kessler, DAGA 2010); below it *"a single point is stable"*, above it a
  single-point dip *"must never be boosted on that evidence alone"* (Geddes & Blind 1984).
- `phase_2_eq.md:55` repeats that split. `estimator-scope.md:110,114-115`: single-point dips have
  a vote only below Schroeder; `eq_propose` resonance packages need *"a peak of medium width,
  staying, minimum-phase"*.

**3. Position stability as a measured verdict.** The ellipsoid (6 positions plus 3 centre
returns) gives stays/moves and σ(f) (`diagnostic-techniques.md:89-90`, `estimator-scope.md:114`),
and `flaw_map.classify` uses it (`flaw_map.py:143-146`).

**How the helper relates to these:**

- **It measures the same signal.** Delay-removed excess phase is the same quantity as the gate's
  excess-GD anomaly. The one difference that matters is **normalisation**: the helper's is
  absolute (degrees); the gate's is relative (z against the channel's own MAD).
- **It fills a real gap.** The gate asks only whether a boost may fill a dip. It fires only
  through a dip of 4 dB or more inside the filter's footprint (`eq_gate.py:178`), and it has no
  vote below 150 Hz. It never examines a peak as a peak. Two consequences:
  - `flaw_map.py:161` labels peaks *"minimum-phase at the gate"* on an ALLOW that the peak itself
    did not earn. **[syn]** On a reflection comb with r = 3.0 (non-minimum-phase), a PK query at
    a comb peak comes back ALLOW. The helper says NON_MIN_PHASE (27° rms).
  - Nothing phase-based exists below 150 Hz.
- **It conflicts with the method in three places:**
  - **Threshold type.** It uses an absolute threshold. The research ablation found relative
    normalisation ESSENTIAL: `research/wiki/experiments/excess-phase-eq-ability-gate-ablation.md:165`, noF2 0.729 vs FULL 0.923 **[P]**. The caveat:
    that arm also dropped the *local* baseline (`research/experiments/code/excess-phase-eq-ability-gate-ablation/gate_variants.py:48-50`, a global median with a
    45° / 1 ms fixed scale), and its scored set was BLOCK-only. It is evidence against "absolute
    and non-local", not a clean test of "absolute" alone.
  - **No frequency scope.** It is not scoped by Schroeder, although the doctrine above is.
  - **Wording.** Its docstring promises too much: *"MIN_PHASE -- ... EQ can undo what it sees"*
    (`eq_gate.py:282-283`). That holds at the measured point only (see Mulcahy below).
- **A second contradiction, inside the method.** `flaw_map.py:133-137` writes *every* dip below
  Schroeder as `cabin_null / no_boost — "interference ... it cannot be filled"`. `§13` and
  `phase_2_eq.md:55` say the opposite: below Schroeder *"a dip there is a property of the cabin
  and can be a legitimate target"*. The minimum-phase verdict is exactly the evidence that should
  settle this, and it is not wired there.

**The research tree disagrees with itself on the Passat's key anchor.** The car record and the
gate call the w-L dip at ~150 Hz non-minimum-phase (`vw-passat-b8-sedan.md:33`; gate BLOCK 5/5
takes, but with S = 3.3, 3.5, 106, 12, 589, `research/wiki/experiments/excess-phase-gate-deep-analysis.md:201`).
`research/wiki/ideas/installation-geometry-vs-cabin-response.md:331-333` calls *"−9 at 160 ... position-stable,
legitimately EQ-able"*. The check at the end of this note is built to settle this.

## What the sources say

| # | Source | Criterion | Quantity, units | Conditions / limits |
|---|---|---|---|---|
| 1 | Neely & Allen, *Invertibility of a room impulse response*, JASA 66(1) 1979 — [abstract](https://experts.illinois.edu/en/publications/invertibility-of-a-room-impulse-response/) | *"Certain synthetic room impulse responses were found to be minimum phase when the initial delay was removed."* Minimum phase depends on reflectivity staying below a threshold. | Nyquist-plot test, binary | Synthetic image-method rooms. Removing the delay first is part of the test. **[S1]** |
| 2 | REW help, *Minimum Phase* (J. Mulcahy) — [link](https://www.roomeqwizard.com/help/help_en-GB/html/minimumphase.html) | *"Anywhere the excess group delay plot is flat is a minimum phase region of the response."* *"Constant time delays ... can be removed ... and they do not cause any problems with applying EQ."* LF dips at *"about 44 and 56Hz"* are not minimum-phase; *"the plot is fairly flat in the region of the 28Hz and 60Hz peaks"*. Peaks are usually minimum-phase. | Excess GD = slope of (measured − minimum phase); **no number for "flat"** | Qualitative. **[S1]**, and the tool we use. |
| 3 | REW help, *Group Delay* and *SPL & Phase* — [GD](https://www.roomeqwizard.com/help/help_en-GB/html/graph_groupdelay.html), [SPL](https://www.roomeqwizard.com/help/help_en-GB/html/graph_splphase.html) | *"if smoothing has been applied to the measurement that will also smooth the phase and group delay traces"*. *"the IR window settings are important as the minimum phase response is derived from the frequency (magnitude) response"*. *Estimate IR delay* compares the measurement with its minimum-phase version. | — | The verdict depends on the read's smoothing and the IR window. **[S1]** |
| 4 | REW help, *Impulse Responses* — [link](https://www.roomeqwizard.com/help/help_en-GB/html/impulseresponse.html) | The frequency-dependent window is set in **cycles** (15 cycles = 150 ms at 100 Hz, 1.5 ms at 10 kHz). | Periods | Practice scales time windows with 1/f. **[S1]** |
| 5 | J. Mulcahy, AV Nirvana forum — [car thread](https://www.avnirvana.com/threads/car-environment-minimum-phase.5342/), [EQ thread](https://www.avnirvana.com/threads/minimum-phase-and-eq-filters.8801/) | *"If a reflection ... equals or exceeds the direct sound the system will exhibit non-minimum phase behaviour."* *"A car environment is no more minimum phase than a room."* In a non-min-phase region EQ still gives the predicted magnitude at the point measured, but *"correcting the phase response would elude us"*, and the result *"is also likely to be quite different at other measurement positions"*. | — | No number. **[S1]** |
| 6 | Toole, *The Measurement and Calibration of Sound Reproducing Systems*, JAES 63(7/8) 2015 — [PDF](https://www.linkwitzlab.com/Toole-Room%20calibration.pdf) | Above the transition (Schroeder) frequency, interference peaks and dips *"are non-minimum-phase phenomena that are not correctable by minimum-phase equalization"*. Below it, EQ can attenuate *"prominent room resonances at a single listening location"*. Transducer resonances *"are minimum-phase ... can be attenuated by using matched parametric filters, thereby correcting both the amplitude and time-domain problems"*, identified from high-resolution anechoic data. | — | Rooms, not cars. The resonance/interference split is physical. **[S1]** |
| 7 | Radlović, Williamson & Kennedy, IEEE TSAP 8(3) 2000 — [PDF](https://users.cecs.anu.edu.au/~rod/papers/2000/00841213.pdf) | *"position changes on the order of one-tenth of the acoustic wavelength can cause significant degradation"*. *"Outside of such a region, equalization is ineffective and may actually have performance worse than having no equalizer at all."* | λ/10 (23 cm at 150 Hz, 3.4 cm at 1 kHz) | Diffuse field, i.e. above Schroeder; *"caution at low frequencies"*. **[S1]** |
| 8 | Radlović & Kennedy, IEEE TSAP 8(6) 2000 — [PDF](https://users.cecs.anu.edu.au/~rod/papers/2000/00876311.pdf) | Minimum-phase EQ of a mixed-phase response leaves all-pass group-delay spikes. The residual is inaudible while the magnitude-weighted GD stays below the ear's time constant (≥ ~2 ms). | ms, perceptual | Speech, reverberant room. This is an audibility criterion, not a classification test. **[S1]** |
| 9 | Blauert & Laws, JASA 63(5) 1978 — [ADS](https://ui.adsabs.harvard.edu/abs/1978ASAJ...63.1478B), numbers as usually reproduced | GD-distortion audibility ≈ 3.2 / 2 / 1 / 1.5 / 2 ms at 0.5 / 1 / 2 / 4 / 8 kHz | ms | Headphones. Numbers taken second-hand. **[S1]** |
| 10 | Brännmark & Ahlén, ICASSP 2008 — [IEEE](https://ieeexplore.ieee.org/document/4517627/) | *"A common strategy for robust ... equalization is ... to use minimum phase filters only"*. *"some non-minimum phase zeros are insensitive to receiver position, and can therefore be robustly inverted."* | — | Position insensitivity, not minimum phase alone, is what makes a correction robust. **[S1]** |
| 11 | DRC-FIR documentation (D. Sbragion) — [link](https://drc-fir.sourceforge.net/doc/drc.html) | Excess-phase correction is windowed and reduced with frequency because *"listening position sensitivity increase quite quickly with frequency"*. A perfect correction at one point gives *"unacceptable results for positions which are even few millimeters apart"*. | Windows shrinking with f | Practitioner tool. **[S1]**; agrees with 7 and 10, so the pattern is **[S]**. |
| 12 | Car Schroeder frequency (method's sources: DAGA 2010, Geddes & Blind 1984, `diagnostic-techniques.md:88`); own repeats `research/wiki/ideas/installation-geometry-vs-cabin-response.md:329` | 150–200 Hz. Tripod repeatability 0.19 dB RMS at 25–150 Hz against 3.01 dB at 500 Hz–1 kHz. | Hz, dB RMS | **[S]** plus **[P]** |

**What none of them gives: a number.** No source read here publishes a residual-phase (degrees)
or excess-GD (ms) threshold for calling a feature minimum-phase. That covers REW help, Mulcahy's
posts, Toole 2015, Radlović ×2, Brännmark & Ahlén, DRC, and a web search for published criteria.
The sourced criterion has three parts:
- **qualitative:** excess GD *flat* once the delay is removed (1, 2);
- **frequency-scoped:** at a single point it is decisive only below Schroeder (6, 7, 12);
- **positional:** above Schroeder, what a filter can robustly correct is decided by stability
  across positions (5, 7, 10, 11).

Genereux (AES 1992) and Johansen & Rubak (AES 1996) are paywalled and were not read; Genereux
enters only through Toole's quotation of him.

## Analysis

**What the verdict measures: right quantity.** **[S]**
- Theory: a minimum-phase system's magnitude and phase are a Hilbert pair, so its excess phase is
  zero. A pure delay is all-pass, so it lands wholly in the excess phase as a ramp (1, 2).
- Removing the delay and judging what is left is therefore the correct test. It is what the #56
  session got wrong by reading raw −122°.
- **[I]** A residual in degrees over a window of fixed octave width is, dimensionally, a
  threshold on excess GD in *periods*. An excess-GD bump Δτ spread over a window W = f0·(2^h − 2^−h)
  bends the phase by about 360·Δτ·W degrees, and W grows with f0.
- So the helper's degree scale is frequency-scaled, the way practice scales windows in cycles (4,
  11). A fixed-ms threshold would be too loose in the treble and too strict in the bass.
- The helper is right on this axis and should not switch to ms. The gate is the one that
  normalises GD in seconds by a single band-wide MAD; `analyze` computes `cycles` (`eq_gate.py:120`)
  and `check` does not use it.

**The threshold is a noise threshold, so the number must come from the measurement.** **[I]** A
true minimum-phase feature reads 0° at any depth, so any threshold only separates zero from
"zero plus noise". The noise in a cabin is not random: it is the reflection field (5), plus
smoothing, the IR window (3) and the grid. The 10°/30° pair stands on:
- 0.3° synthetic phase noise;
- noise-free reflection combs on a 96-ppo grid;
- four #56 features read at 1.2 / 0.0 / 0.4 / 2.3°, whose smoothing and IR window #56 does not
  record.

The synthetic probe shows how thin that is **[syn]**:

| probe | result |
|---|---|
| true min-phase PK (+6 dB, Q 4, 1 kHz), random phase noise per point | σ 6° → MIN (6.2° rms / 19.3° max); **σ 10° → NON (10.9 / 32.2)** |
| r = 1.05 comb at its 1667 Hz notch, read smoothed | none → NON 19.1°; 1/48 → NON 9.8°; **1/24, 1/12, 1/6 → MIN (6.5 / 3.9 / 4.7°)** |
| same comb, other notches | 333 / 1000 / 1667 / 3000 / 5000 Hz → 68 / 80 / **19** / 89 / 22° rms (grid alignment) |
| min-phase PK at 1 kHz + a non-min-phase notch 0.4 oct away | **±0.5 oct → NON (52° rms, +28° at f0)**; ±1/4 → MIN 1.9°; ±1/6 → MIN 0.6° |

Reading the table:
- The 10° line sits only 2× below the weakest non-min-phase case, and that case is the grid-luck
  one.
- Any read smoothed to 1/24 or coarser erases a real non-min-phase step. This agrees with
  REW's own warning (3).
- A ±0.5-oct window charges the feature with its neighbour's excess phase.

**This is not hypothetical on the Passat.** The w-L modal peak at 90–127 Hz and the w-L door null
at ~150 Hz (`vw-passat-b8-sedan.md:35`) are 0.3–0.7 oct apart. A ±0.5-oct window around 110 Hz
spans 78–156 Hz. **[I]** The helper as shipped can call the modal peak NON_MIN_PHASE because of
the door null beside it.

**The window should be the feature's own, and the delay the channel's.** **[I]**
- **Window.** The method already reads features on a 1/6–2/3-oct scale (`eq_propose.py:88`,
  `RES_WIDTH`) and matches them across positions within ±1/6 oct (`eq_propose.py:421`). A ±1/6-oct
  window (1/3 oct wide, 33 points at 96 ppo) judges the feature and little else.
- **Delay.** With a free line in every window, a *local* GD offset — which is REW's "not flat" —
  is absorbed as "delay". The helper's own docstring already says the delay should agree across one
  channel's features (7.3 ms on all four in #56, `eq_gate.py:290-292`). So take one bulk delay per
  channel, by the existing coherence search over the channel's live band, and hold it fixed. Report
  each window's free-line delay beside it as a diagnostic.

**Scope: the Schroeder split decides what the verdict may decide.** **[S]**
- **Below ~200 Hz** a single point is stable (6, 12). Modes are poles, so peaks are minimum-phase;
  dips can go either way (2: the 44–56 Hz example). Here a single-point minimum-phase verdict is
  *the* evidence. It is also where the gate is silent (< 150 Hz) and where `flaw_map` currently
  applies a blanket rule instead.
- **Above it** the verdict at one point says nothing about the head 10 cm away. The ellipsoid's
  14–18 cm spacing equals λ/10 at about 190–245 Hz **[I from 7]**, which is why stays/moves is
  informative exactly there. The sources place the licence for a filter in *position stability*
  (5, 7, 10, 11) and in the physics of the source: a transducer resonance is minimum-phase (6).
  At one point, a MIN_PHASE verdict up there is necessary for a matched cut, not sufficient; a
  NON_MIN_PHASE verdict up there confirms "leave it", which is the current doctrine.

**Stability across takes is part of the verdict, not an extra.** **[P]** On shallow features,
single-point excess phase in this cabin breathes by orders of magnitude between takes: w-L 155,
S = 3.3 … 589 (`research/wiki/experiments/excess-phase-gate-deep-analysis.md:199-205`). A verdict from one take is therefore a sample, not a
verdict. The ellipsoid's three centre returns exist to measure exactly this floor
(`diagnostic-techniques.md:89`, *"The anchors are the requirement"*).

## Decision for the method

1. **Keep the helper; do not fold it into the gate.**
   - They answer different questions. The gate: may a boost fill this dip (dips, 150–4000 Hz,
     calibrated on one car). The helper: is the excess phase at this feature only the delay (any
     feature, any band).
   - Folding would also import the gate's seconds-normalised statistic, which is the weaker of the
     two on frequency scaling.
   - **What must stop:** labelling a peak *"minimum-phase at the gate"* (`flaw_map.py:161`, the same
     reading in `eq_propose`). The gate never examined the peak. The label should come from this
     verdict.

2. **Change the criterion to the following defaults.**
   - **Input.** The `-EP` of a sweep, read at `None` or `1/48` only. Refuse anything coarser, as
     `curve_view` refuses smoothed input: REW smooths phase with magnitude (3), and 1/24 already
     erased a real step **[syn]**. Name the IR window in the result (3).
   - **Delay.** One bulk delay per channel (coherence search over the channel's live band), held
     fixed. Take out the delay and the mean only. Report each window's own line delay beside it,
     for comparison **[I; helper's own `:290-292`]**.
   - **Window.** Default `half_oct = 1/6` (not 0.5). A feature wider than 1/3 oct gets its own
     half-width. Judge only where the channel plays (`eq_propose`'s live-band mask) **[I; probe D;
     `RES_WIDTH`]**.
   - **Threshold.** rms ≤ **max(10°, 3·σ_rep)** and max ≤ **3 × that**.
     - σ_rep is the rms residual difference between repeat takes at one position (the ellipsoid's
       centre returns), divided by √2. Relative to the measurement's own floor: the ablation's
       direction **[P]**; 3σ as the detection convention **[I]**.
     - 10° is kept only as a floor under the floor: below it, grid and unwrap artefacts on 96 ppo
       cannot be told from signal (the helper's own r = 1.01 analysis, `eq_gate.py:211-216`).
       It is not a physical constant, and no source supplies one.
   - **Stability.** The verdict must agree on ≥ 2 of the 3 centre returns, otherwise the result is
     `UNSTABLE`: a verdict of its own, neither MIN nor NON **[P drift floor; S 5, 7]**. With no
     repeats, the result says `floor not measured — PROVISIONAL`.
   - **Scope field.** `decisive` below `SCHROEDER_HZ` (200, `eq_propose.py:84`); `corroborating`
     above it **[S 6, 7, 12]**.

3. **What the verdict licenses.** The logic is the one the sources give (6, 2, 5, 7).

   | | below Schroeder (decisive) | above Schroeder (corroborating) |
   |---|---|---|
   | **peak, MIN** | cut at matched Q: fixes magnitude and ringing (6, 2) | cut only if the ellipsoid says it STAYS: a driver resonance (6, §13) |
   | **peak, NON** | leave; report | leave (6: interference is not correctable by minimum-phase EQ) |
   | **dip, MIN** | a legitimate boost candidate within the +6 dB ceiling (§13, `phase_2_eq.md:55`, 2). The blanket `cabin_null` in `flaw_map.py:133-137` gives way to this verdict. | never boosted on single-point evidence (§13); the gate and mic-shift govern as now |
   | **dip, NON** | `cabin_null`, no boost (2: *"poor results ... when trying to lift such regions"*) | same |
   | **UNSTABLE / PROVISIONAL** | reported; no filter on it alone | reported |

4. **How the verdict is reported.** One line carries the named quantity, the window, the threshold
   and its origin, the read, the stability and the scope. For example:

   `MIN_PHASE at 112 Hz — residual excess phase 3.1° rms / 8.4° max after the channel delay
   7.30 ms, over ±1/6 oct (100–126 Hz); threshold max(10°, 3·σ_rep = 3.6°) rms — floor from 3
   centre returns, 3/3 agree; read -EP at smoothing None, IR window 125/500 ms; below Schroeder:
   decisive. Criterion: flat excess GD (REW help); delay removal (Neely & Allen 1979); no published
   threshold — the floor is measured.`

   The docstring's *"EQ can undo what it sees"* becomes *"at this point"*, and above Schroeder it
   adds *"— whether it holds at the head is the ellipsoid's question"* (5, 7).

5. **The one real-data check, on the Passat, when the next ellipsoid round exists.**
   - **Input.** For w-L and m-R: the 9 sweeps of one ellipsoid round (6 positions + 3 centre
     returns, `(sw)`); an `-EP` of each (`rew_api.excess_phase_version`), read with
     `get_fr(id, smoothing=None)`.
   - **Run** the verdict at three labelled features, each at ±0.5 and ±1/6 oct, with a per-window
     line and with the fixed channel delay:
     - the **w-L 90–127 Hz peak** (expected MIN: modal, position-stable);
     - the **w-L ~150 Hz dip** (the contested anchor);
     - the **m-R ~645–662 Hz SBIR** (expected NON: *"proven by moving the source"*,
       `vw-passat-b8-sedan.md:34`).
   - **Record** the residual per take, σ_rep and the verdict per take.
   - **This decides three things:**
     1. whether 3σ_rep ≤ 10° in each band, i.e. whether the 10° floor ever binds on real data;
     2. whether ±0.5 oct misreads the w-L peak through the door null (the default-window question);
     3. the w-L 150 Hz conflict. NON on ≥ 2/3 returns: the car record stands and the research
        note's "EQ-able" is corrected. MIN: the blanket `cabin_null` for that dip was wrong.
       `UNSTABLE`: the gate's S = 3.3…589 was the floor talking, not the car.
