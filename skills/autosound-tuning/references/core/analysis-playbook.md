# Analysis playbook — which measurement answers which question

A map: decision → data → REW API function. The API is in `rew_tool/rew_api.py` (`localhost:4735`).

| Tuning question | Which measurement/graph | Measurement method | REW API function |
|---|---|---|---|
| Where to put the crossover frequency (L=R, min loss vs target) | FR (magnitude), the existing slopes | MMM RTA | `get_fr`, `get_slopes`, `get_target_response` |
| Is a dip fixable with EQ | Excess phase / minimum-phase decomposition | Sweep (loopback) | `excess_phase_version(mid)` → REW builds the `-EP` curve → `get_fr` reads it (native REW Hilbert, not a home-brew scan) |
| Delays / time alignment | Impulse / step response, ETC | Sweep (loopback) | `get_impulse_response` |
| Phase rotation / excess GD at joints | Group delay | Sweep | `get_group_delay` |
| Safe band limits (where to put the HPF) | Distortion (THD + harmonics) | Sweep at the working level | `get_distortion` |
| Resonances / "ringing" (doors, 150 Hz) | CSD / waterfall | Sweep | (REW UI; IR from `get_impulse_response`) |
| Driver/box T-S (Fs, Qts/Qtc, Vas, Re), L/R match, enclosure QC, box verify | Impedance (Z vs freq) | Impedance sweep (jig + ref resistor) | `get_fr` on the imp measurement (`unit=ohm`); method → `impedance-ts.md` |
| Predicting the L+R or band+band sum | Trace arithmetic A+B | — | REW trace math (UI/API) |
| A channel's current filters / EQ | Filters / EQ | — | `get_filters`, `get_equaliser`, `get_equalisers` |
| Apply EQ/filters | — | — | `set_filters`, `set_equaliser` |
| Available crossover types and slopes | — | — | `get_crossover_types`, `get_slopes` |
| Which of 2–3 crossover candidates, and why — fit, corner level/phase, phase turn, added GD, margin from the driver's own edge | the driver's de-embedded solo, its target, the corner slots | — | `xover_candidates.py --solos --project --house --channel --hp --lp [--fs]` (describes; the tuner picks) |
| The flaw map, from the measurements: what is a driver resonance, a cabin mode, a null, non-minimum-phase — and what is NOT a flaw | de-embedded solos (+ the ellipsoid positions for stays/moves) | — | `flaw_map.py --project --solos [--ellipsoid] [--write]` (rows as hypotheses with evidence) |
| Is this corner allowed at all — driver Fs, added group delay, ear sensitivity at the junction | installed Fs (impedance sweep), the filter's own GD | — | `crossover_checks.py --fc --fs --order [--gd]` |
| Target (house curve) for comparison | Target | — | `get_target_settings`, `get_target_response` |
| Junction delay / polarity at the DESK (virtual-first 1.3) | solos × ledger chains, sum loss per junction, the arrival difference | Sweep (loopback), one base | `predict.py --align` (alias said by name; `aligned-delta.json` → `apply.propose`) |
| Which features stay and which move; how narrow a filter may be; the tolerance to the target | nine positions around the head, σ(f), presence per feature, the Q ceiling | Sweep, hand-held ellipsoid `p1…p9` | `ellipsoid.py --solos DIR \| --rew --ver N --channel m-L` |
| Coarse EQ at the desk / fine EQ in the car as packages | resonances per driver group, L/R shape per pair, tone per pair | Sweep (desk) or MMM (car) + the ellipsoid + the impulse for the phase gate | `eq_propose.py` (each package: why, listening id, score, delta) |
| What cuts the ear / what booms | peaks above a ±1-oct trend, classed and ear-weighted | MMM `ALL_N (rta)` (a sweep adds ring-down) | `ear_suspects.py` → A/B one band at a time, `listening-verdict` |
| Was the preset ENTERED as designed | `_2` solo vs predicted solo × chain: shape (1/6 oct) + arrival | Sweep from the tripod | `verify_prediction.py --entry` |
| Did the time base hold through the capture session | ctl1 → ctl3 drift by cross-correlation; levels side by side | Sweep, the round's control titles | `capture-check --session` / `verify.py --session` |

---

## Reading rules

- **MMM RTA → magnitude; Sweep (loopback) → phase/time.** Don't draw phase/time conclusions from MMM.
- **Level-normalize before comparing SHAPE.** Different measurements can sit at different absolute levels (mic gain, session, day). When comparing **L vs R**, **before/after**, or **vs a target**, **offset the traces to overlay first** — a level difference is not a real shape difference (this is how you read *shape* independent of level). **But when the LEVEL itself is the answer** (level balance, summation gain, matching the target level) you can't normalize it away → tell the user to capture the compared measurements **at the same reference level**, or **re-capture** the ones that matter for that comparison at a matched level.
- **Judge "how close to target" by BAND-INTEGRATED deviation — never by peak dB or RMS.** The ear
  weights a deviation by its *width*: a broad half-decade tilt of even ~1–1.5 dB is an audible
  tonal error, while the same dB in a narrow notch is not (and a big RMS can be all harmless narrow
  wiggle). So after overlaying the measured trace onto the target (level-normalize first, above),
  compute the **mean deviation per half-decade/octave band** (20–40, 40–80, 80–160, 160–315,
  315–630, 630–1250, 1250–2500, 2500–5000, 5000–10000, 10000–20000) and flag any band whose *mean*
  rides ≥~1–1.5 dB off target. That broad tilt is a real voicing error even when no single peak is
  large and the RMS "looks done" — it is exactly the residual a flat-chasing or peak-hunting read
  walks past, and it surfaces only as long-listening fatigue (see `car-eq-patterns.md` → judge-by-
  audibility). The band grid above is illustrative — the tilt can sit in **any** region (a hot lower-
  mid over a light midbass = mud/fatigue; a hot 2–5 kHz = shouty; a bloated or shy bass shelf; a
  rolled or hot top octave). Tool: `get_fr` + `get_target_response` → `analysis.compute_deviation` →
  average per band; don't declare a lock without this scan (`phase_3_control.md §2`). ⚠️ The flip side:
  do **not** turn a flagged band into narrow deep cuts — fix a broad tilt with a broad gentle move, and
  first confirm it's not an uncorrectable null / off-axis dip (below) that the ear ignores anyway.
- **Smoothing for decisions:** **1/6 oct is the standard for level/shape decisions in the mid-treble** (300–3000+; it damps cabin reflections, keeps driver peaks Q>2). **Raw/None — only for finding narrow resonances** (Q>5, e.g. a driver breakup) and sharp modes; on None, single-position data is wild (real case: m-R −10 at 1117 = a reflection, not the driver). 1/48 — diagnosing sharp resonances; don't flatten everything visible at 1/48. ⚠️ **The REW API returns whatever smoothing is active in the session** — check it at the start of the analysis; if it's None, set REW's own via **`set_smoothing(mid, '1/6')`** (authoritative — matches REW exactly) then re-pull, or apply 1/6 mathematically, before deciding. Agree the smoothing standard with the critic before the first EQ proposal (otherwise it reads different numbers). ⚠️ **Smoothing = POST-PROCESS, NEVER a reason to re-measure:** raw is captured once (1/48 / None) → apply any smoothing **mathematically** (REW main window / `rew_tool` numerically) for EACH decision (1/6 — tone · 1/48/raw — resonances/nulls). Don't ask the user to re-measure the MMM for a different resolution/smoothing.
- **RTA config for correlated pink (ResoNix practice):** RTA **1/48 oct**, Averages **Forever** + **Stop at ~150** (auto-stop after ~150 averages → a consistent count across channels + a clear "MMM done" signal; move the mic until the auto-stop, not by eye), Window **Hann**, Max Overlap **93.75%**. ⚠️ **FFT = the length of the periodic/correlated noise** (here **128k**, because the ResoNix noise is 128k too; if your noise is 64k → FFT **64k**) — this is NOT a fixed number; longer is justified only for low-freq THD resolution. **Capture at full resolution, smooth LATER** (don't trim the data at the input). MMM = spatial averaging around the head/ears at the LP.
- **An RTA dip ≠ a HEARD dip when dispersion/off-axis is involved.** E.g. a high crossover (tweeter/mid 5k to dodge a reflection) → narrow upper-mid dispersion → the mic sees a dip, the ear doesn't (off-axis energy interacts with the cabin). The same measured response **sounds DIFFERENT depending on the driver's distortion profile**. → don't chase RTA-flat blindly; the curve = a start, the ear decides.
- **Measurement integrity before analysis:** the IR gate doesn't cut the direct sound; the noise floor; the cal file is loaded; no clipping during the sweep.
- **Token diet for the critic:** the package gets the digitized anomalies (numbers), and the raw trace — a **decimated CSV as a separate file** (the 2nd arg to `gemini_critic.sh`), so the critic can challenge the reading of the data without drowning in the dump.

## Decimated trace for the critic

Export FR/phase from REW (or from `rew_tool`) as CSV, decimated to ~1/6–1/12 oct (tens-to-hundreds of points, not thousands). Columns: `Freq[Hz], SPL[dB], Phase[deg]`. Pass it as the second argument to `gemini_critic.sh`.

## FSAF (REW 5.40+) — distortion under a real load, NOT a replacement for the sweep
The stimulus = noise or music → TD+N under "combat" conditions of a dense spectrum (a sweep measures distortion with one tone). ✅ The question "does a breakup/hump actually DISTORT under music, or is it a harmless FR feature" (a joint with a "detail/air" complaint). ❌ NOT for linear resonances/reflections (λ/4, SBIR, diffraction — a gated sweep sees them just as well; "FSAF catches hidden reflections" = a myth) and NOT for an A/B against a sweep baseline (the method must match). Requirement: a shared replay/record clock (ECM8000+Scarlett+loopback ✅; UMIK-1 ❌). Level ≤ −14 dB (noise crest). Impedance/Qtc — a separate tab (sweep) → `impedance-ts.md`.

## ETC (Energy-Time Curve) — a reflection map, an underused tool
From the sweep's IR (REW GUI). A discrete arrival with a delay τ after the direct → a path difference Δd = τ·343 m/s → predicted comb nulls at n·c/(2Δd); a match of the predicted nulls with the measured ones in the FR = the reflector is identified BY DISTANCE. + a gate test (gate out the IR → the dip filled in = late reflections). The question "WHERE is the reflector that makes the dip" → ETC, not FR. Detail/case → `enclosure-install-diagnostics.md §2`.

## Configuration under test — measure what the listener hears

- **The two-snapshot rule.** A measurement convention that mutes the centre/fill and turns processing off protects series comparability, and it can also mean the configuration people actually listen to is never measured at all. Field case: a whole tuning arc ran on `ALL` (centre muted, effects off) while the judged configuration was centre ON + effects ON; the centre's own contribution measured **+4.3…+5.7 dB** in two bands and sat outside every tonal verdict of that arc. From then on each series carries **both**: the legacy invariant (comparability) and the **combat** snapshot (truth). **Tonal verdicts come only from the combat snapshot.**
- **Attribute a summed excess before choosing where to cut — the loud band is not always where the energy came from.** A cluster measured +6.3 dB over target, so a symmetric narrow cut went on the both-sides layer. It behaved exactly as modelled on the solo sides and moved the combat curve by **nothing**. Only the intermediate snapshot (centre on / effects off) showed why: the centre alone contributed +8.0 dB there while the sides sat within ±2.5 dB of target. Without that middle member the next move would have been a deeper cut on the wrong surface. **For any multi-source excess, capture the intermediate snapshot and split the contribution before placing a filter.**
- **Discrete test tones are read AT THE TONE FREQUENCIES, never as band medians.** A tone-test band summarised as "on target, 1.9 dB spread" hid a **+3.0 dB** peak sitting exactly on one of the test tones. Band statistics are the right tool for voicing and the wrong tool for a test that scores four specific frequencies.
- **Measured group delay ≠ filter group delay.** A reviewer called an 18.4 ms measured GD range on the midbass "five overlapping filters, consolidation will fix it". Modelling the actual banks: the right side's filters contribute 8.15 ms, while the left — with **half** the filter count and 4.51 ms of filter GD — measures 30.5 ms. The bulk was door-null acoustics. A refactor would have surrendered five individually ear-attested wins for ~6-8 ms. **Separate filter-modelled GD from measured GD before treating a filter bank as the culprit.**

## Knowing your own error bars

- **Measure the repeatability floor once per rig, and quote it whenever a difference is called real.** Typical shape from one build (RMS over 450-2500, same session): MMM RTA capture-to-capture **0.25 ± 0.07 dB** · static sweep **0.38 ± 0.14** · sweep after a 2 cm mic shift **0.95** · after 5 cm **2.92**. Numbers are install-specific; the *practice* transfers. Without them, "the two series disagree by 0.95 dB" has no meaning.
- **Between-series scatter can dwarf within-series scatter, and the cause is usually an unrecorded global.** Two series of the same configuration 40 minutes apart disagreed by **3-7×** the within-series σ, because the master volume had moved and the loudness/tilt compensation is global and level-dependent. Neither measurement recorded it. → record the system state **in the measurement's own notes** (`process-control.md`).
- **A set with no replicate can still have an error bar if it contains a physical identity.** Above the fill channel's low-pass, a full-system capture must equal the **power sum** of the solo sides captured at the same place. The residual of that identity is the set's internal inconsistency — free, requires no extra capture, and it caught a 2.4 dB looseness at one position while the other closed to 0.55 dB. Verify first that nothing else is live in the band (here: the effects layer contributed −0.24…+0.54 dB, so the identity held).
- **Spread *within* an MMM traversal can be the signal, not the noise.** MMM measures a **volume**; not holding an exact point is the method's design. So when one position's captures disagree more than another's, ask what the volume is doing before blaming the operator. Decompose the residual: **narrow (notch-like) structure = undersampled comb**, i.e. a real averaging failure; **broad-shaped structure = a spatial gradient across the volume**, i.e. directivity. In the field case the narrow parts were nearly equal on both sides (1.28 vs 1.82 dB) while the broad part was 2.3× larger at one ear (0.71 vs 1.61) — the on-axis tweeter's beam had a gradient across that ear's volume. **The generator's first reading was "sloppy captures"; it was wrong, and the decomposition is what settled it.**
