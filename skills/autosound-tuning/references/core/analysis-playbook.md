# Analysis playbook — which measurement answers which question

A map: decision → data → REW API function. The API is in `rew_tool/rew_api.py` (`localhost:4735`).

| Tuning question | Which measurement/graph | Measurement method | REW API function |
|---|---|---|---|
| Where to put the crossover frequency (L=R, min loss vs target) | FR (magnitude), the existing slopes | MMM RTA | `get_fr`, `get_slopes`, `get_target_response` |
| Is a dip fixable with EQ | Excess phase / minimum-phase decomposition | Sweep (loopback) | `get_fr` (+ phase), analysis in REW |
| Delays / time alignment | Impulse / step response, ETC | Sweep (loopback) | `get_impulse_response` |
| Phase rotation / excess GD at joints | Group delay | Sweep | `get_group_delay` |
| Safe band limits (where to put the HPF) | Distortion (THD + harmonics) | Sweep at the working level | `get_distortion` |
| Resonances / "ringing" (doors, 150 Hz) | CSD / waterfall | Sweep | (REW UI; IR from `get_impulse_response`) |
| Driver/box T-S (Fs, Qts/Qtc, Vas, Re), L/R match, enclosure QC, box verify | Impedance (Z vs freq) | Impedance sweep (jig + ref resistor) | `get_fr` on the imp measurement (`unit=ohm`); method → `impedance-ts.md` |
| Predicting the L+R or band+band sum | Trace arithmetic A+B | — | REW trace math (UI/API) |
| A channel's current filters / EQ | Filters / EQ | — | `get_filters`, `get_equaliser`, `get_equalisers` |
| Apply EQ/filters | — | — | `set_filters`, `set_equaliser` |
| Available crossover types and slopes | — | — | `get_crossover_types`, `get_slopes` |
| Target (house curve) for comparison | Target | — | `get_target_settings`, `get_target_response` |

---

## Reading rules

- **MMM RTA → magnitude; Sweep (loopback) → phase/time.** Don't draw phase/time conclusions from MMM.
- **Level-normalize before comparing SHAPE.** Different measurements can sit at different absolute levels (mic gain, session, day). When comparing **L vs R**, **before/after**, or **vs a target**, **offset the traces to overlay first** — a level difference is not a real shape difference (this is how you read *shape* independent of level). **But when the LEVEL itself is the answer** (level balance, summation gain, matching the target level) you can't normalize it away → tell the user to capture the compared measurements **at the same reference level**, or **re-capture** the ones that matter for that comparison at a matched level.
- **Smoothing for decisions:** **1/6 oct is the standard for level/shape decisions in the mid-treble** (300–3000+; it damps cabin reflections, keeps driver peaks Q>2). **Raw/None — only for finding narrow resonances** (Q>5, e.g. a driver breakup) and sharp modes; on None, single-position data is wild (real case: m-R −10 at 1117 = a reflection, not the driver). 1/48 — diagnosing sharp resonances; don't flatten everything visible at 1/48. ⚠️ **The REW API returns whatever smoothing is active in the session** — check it at the start of the analysis; if it's None, **apply 1/6 mathematically** before deciding. Agree the smoothing standard with the critic before the first EQ proposal (otherwise it reads different numbers). ⚠️ **Smoothing = POST-PROCESS, NEVER a reason to re-measure:** raw is captured once (1/48 / None) → apply any smoothing **mathematically** (REW main window / `rew_tool` numerically) for EACH decision (1/6 — tone · 1/48/raw — resonances/nulls). Don't ask the user to re-measure the MMM for a different resolution/smoothing.
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
