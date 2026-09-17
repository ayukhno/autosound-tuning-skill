# Which smoothing each REW reader should ask for (S-013)

Research on the user's request of 2026-09-17: decide per analysis, not per tool habit. Inputs: the
live REW session, math, scientific sources, external practice. **Nothing in the code changed**; the
decisions are the Arbiter's (§6).

All REW reads here were GETs with `?smoothing=`; the view of every measurement was recorded before
and after each run and never changed (hub TCC-015). Scripts and raw output:
`hub/scratch/skill/s013/` (`coherence.py`, `readers_effect.py`).

## 1. What REW hands back (REW 5.40 beta 132, API 0.9.6, 102 measurements)

| read | grid | points | notes |
|---|---|---|---|
| sweep, `smoothing=None` | linear, step 0.3662 Hz | 54,559 (20.1–20,000 Hz) | ~0.55 s per read |
| sweep, any fraction / `Var` / `Psy` | log, 96 per octave | 957 (20.1–20,038 Hz) | same grid for every fraction |
| RTA, any ask | log, 96 per octave | 1,286 (4.4–47,025 Hz) | asked `None`: returns **`1/48`** when its view is smoothed, `None` when its view is `None` |
| no parameter | whatever the view holds | | this session: sweeps 77 × `1/24`, 8 × `1/6` (all `_01 (sw)`); RTA 7 × `None`, 2 × `1/48`, 1 × `Psy` |

So today every reader reads what each measurement's view happens to hold, and one table can mix
`1/6` and `1/24` rows.

## 2. Math on this car

### 2.1 What each finer resolution adds, and whether every head position sees it

Seven channels (w-L/R, m-L/R, tw-L/R, c), nine tripod positions each (`<ch> p1..p9_49 (sw)`). For a
step fine → coarse, the detail the finer read adds at position *i* is `d_i(f) = fine_i − coarse_i`.
Per octave band it splits into a **common** part (equal at all nine positions: the driver and the
car, what an EQ can act on) and a **random** part (changes from head to head: interference).
`P_common = max(0, rms(mean_i d)² − rms(std_i d)²/9)`; *share* = `P_common / (P_common + P_random)`.
Medians over the channels live in the band (within 15 dB of their top). `None@pt` is raw resampled
by picking points, as the readers do now; `None@1/96` is raw power-averaged over 1/96 octave.

Detail added, rms dB · common share:

| band, Hz | None@pt → 1/48 | None@1/96 → 1/48 | 1/48 → 1/24 | 1/24 → 1/12 | 1/12 → 1/6 | 1/6 → 1/3 |
|---|---|---|---|---|---|---|
| 20–40 | 0.54 · 0.90 | 0.60 · 0.84 | 0.26 · 0.93 | 0.57 · 0.94 | 0.88 · 0.97 | 1.00 · 0.99 |
| 40–80 | 0.09 · 0.88 | 0.12 · 0.90 | 0.06 · 0.89 | 0.15 · 0.89 | 0.30 · 0.86 | 0.54 · 0.89 |
| 80–160 | 0.51 · 0.56 | 0.48 · 0.53 | 0.24 · 0.65 | 0.68 · 0.69 | 1.42 · 0.79 | 1.90 · 0.94 |
| 160–320 | 0.10 · 0.45 | 0.09 · 0.48 | 0.06 · 0.59 | 0.15 · 0.76 | 0.30 · 0.74 | 0.63 · 0.72 |
| 320–640 | 0.46 · 0.30 | 0.43 · 0.29 | 0.21 · 0.35 | 0.52 · 0.39 | 0.99 · 0.46 | 1.48 · 0.53 |
| 640–1250 | 1.45 · 0.17 | 1.21 · 0.19 | 0.55 · 0.26 | 1.11 · 0.29 | 1.45 · 0.35 | 1.42 · 0.48 |
| 1250–2500 | 2.00 · 0.14 | 1.68 · 0.15 | 0.63 · 0.21 | 1.01 · 0.24 | 1.14 · 0.20 | 1.18 · 0.20 |
| 2500–5000 | 3.21 · 0.13 | 2.27 · 0.15 | 0.67 · 0.15 | 0.99 · 0.16 | 1.12 · 0.21 | 1.10 · 0.27 |
| 5000–10000 | 3.76 · 0.12 | 2.31 · 0.12 | 0.61 · 0.11 | 0.90 · 0.11 | 1.06 · 0.21 | 1.09 · 0.34 |
| 10000–20000 | 4.04 · 0.13 | 2.27 · 0.12 | 0.59 · 0.14 | 0.92 · 0.23 | 1.18 · 0.49 | 1.27 · 0.69 |

Spread between the nine positions at each resolution (rms over the band of the per-frequency
standard deviation, dB):

| band, Hz | None@pt | None@1/96 | 1/48 | 1/24 | 1/12 | 1/6 | 1/3 |
|---|---|---|---|---|---|---|---|
| 20–40 | 0.59 | 0.65 | 0.48 | 0.43 | 0.37 | 0.31 | 0.27 |
| 80–160 | 2.09 | 2.08 | 1.88 | 1.78 | 1.52 | 1.21 | 1.16 |
| 320–640 | 3.46 | 3.42 | 3.18 | 3.08 | 2.83 | 2.46 | 2.12 |
| 640–1250 | 5.46 | 5.24 | 4.41 | 4.05 | 3.40 | 2.83 | 2.33 |
| 2500–5000 | 5.39 | 4.78 | 3.59 | 3.26 | 2.75 | 2.19 | 1.60 |
| 10000–20000 | 5.36 | 3.89 | 2.76 | 2.46 | 2.01 | 1.56 | 1.24 |

Read-out:

* **Below ~320 Hz raw and 1/48 are the same curve**: the difference is 0.1–0.6 dB rms. Below 25 Hz
  REW's raw bin (0.366 Hz) is wider than 1/48 octave, below 51 Hz wider than 1/96, so there is
  nothing finer to see.
* **Above ~640 Hz what is finer than 1/48 is 81–88 % position-random**: 1.2–4.0 dB rms of detail,
  of which 0.5–1.4 dB is common. The raw single-point spread between positions, 5.2–5.5 dB above
  640 Hz, is the textbook value for a diffuse field (§3).
* Picking points from the raw curve, as the readers' resampling does now, is worse than averaging
  it: 3.2–4.0 dB rms of added detail above 2.5 kHz against 2.3 dB.
* The stable part is at its finest in the bass and coarsens with frequency. Detail stays mostly
  common (share ≥ 0.5) down to 1/48 below ~300 Hz, and to 1/6 → 1/3 up to ~650 Hz. Between ~640 Hz and
  10 kHz even the 1/6 → 1/3 detail is only 20–48 % common. The top octave (the tweeter's direct
  sound) is again 0.69 common at 1/6 → 1/3.

### 2.2 How much of a resonance survives a smoothing (analytic)

Share of a +6 dB peaking bell's height kept after smoothing (box kernel / Gaussian kernel, dB domain):

| Q | width, oct | 1/48 | 1/24 | 1/12 | 1/6 | 1/3 |
|---|---|---|---|---|---|---|
| 2 | 0.71 | 1.00/1.00 | 1.00/1.00 | 0.99/0.99 | 0.98/0.96 | 0.93/0.88 |
| 4 | 0.36 | 1.00/1.00 | 0.99/0.99 | 0.98/0.96 | 0.93/0.89 | 0.80/0.73 |
| 6 | 0.24 | 1.00/0.99 | 0.99/0.98 | 0.96/0.93 | 0.87/0.80 | 0.68/0.60 |
| 10 | 0.14 | 0.99/0.98 | 0.97/0.95 | 0.90/0.84 | 0.73/0.66 | 0.50/0.45 |
| 15 | 0.10 | 0.98/0.97 | 0.93/0.90 | 0.81/0.74 | 0.60/0.53 | 0.37/0.33 |
| 30 | 0.05 | 0.93/0.90 | 0.80/0.74 | 0.59/0.53 | 0.37/0.33 | 0.21/0.19 |

1/48 keeps ≥ 97 % of any resonance up to Q 15; 1/6 keeps 80–87 % at the skill's Q ceiling of 6.

### 2.3 Grid and double smoothing (analytic)

* **The grid is a weight.** An arithmetic mean over a band gives each point one vote. On REW's
  linear raw grid the upper half (by octaves) of a band holds 59–67 % of its points (0.50 on a log
  grid), and over 20–20,000 Hz it holds 97 %.
* **Smoothing twice adds in quadrature** (exact for Gaussians, an estimate for REW's kernel).
  `ear_suspects` (own 1/12): input 1/48 → effective 1/11.6, 1/6 → 1/5.4. `verify_prediction` (own
  1/6 mean): 1/48 → 1/6.0, 1/6 → 1/4.2. `curve_view` fine (own 1/24): 1/48 → 1/21.5.
* **Smoothing ↔ time window.** A window of T seconds resolves 1/T Hz, so 1/B octave at f
  corresponds to about 1/(B·ln 2) cycles: 1/48 ≈ 69, 1/24 ≈ 35, 1/12 ≈ 17, 1/6 ≈ 8.7, 1/3 ≈ 4.3.

### 2.4 Two readers, on this car

**`ear_suspects`**, the top 10 suspects per position; *stable* = found again within 1/12 octave at
≥ 5 of the 9 positions (counted per instance):

| channel | None | 1/48 | 1/24 | 1/12 | 1/6 |
|---|---|---|---|---|---|
| w-L | 69 · 33 | 66 · 35 | 62 · 32 | 54 · 16 | 29 · 12 |
| m-L | 50 · 22 | 52 · 24 | 50 · 24 | 45 · 22 | 30 · 15 |
| m-R | 51 · 30 | 52 · 37 | 51 · 35 | 42 · 25 | 31 · 15 |
| tw-L | 70 · 18 | 66 · 18 | 63 · 17 | 53 · 13 | 37 · 12 |
| c | 54 · 27 | 50 · 20 | 48 · 19 | 46 · 20 | 38 · 14 |

(total · stable). On the moving-mic RTAs, `None`/`1/48`/`1/24` give the same count, and `1/6`
roughly halves it (w-L 4 → 2, m-R 5 → 2). The sub's two suspects vanish from `1/24` on. Today the
`_01 (sw)` views sit at `1/6`, so this reader already sees only a third to two thirds of
the stable suspects it finds at `1/48`.

**`verify` live-band level** (mean of the bins within 20 dB of the top), `_01 (sw)`:

| channel | None | 1/48 | 1/6 | live bins above 1 kHz, None vs 1/48 |
|---|---|---|---|---|
| sw | 103.89 | 106.16 | 106.09 | 0.00 vs 0.00 |
| w-L | 96.89 | 99.88 | 99.69 | 0.69 vs 0.23 |
| w-R | 98.40 | 100.74 | 100.82 | 0.73 vs 0.25 |
| m-L | 101.51 | 101.29 | 101.57 | 0.95 vs 0.57 |
| m-R | 100.37 | 98.61 | 98.62 | 0.96 vs 0.60 |
| tw-L | 100.91 | 100.61 | 100.89 | 0.99 vs 0.92 |
| tw-R | 101.39 | 100.82 | 100.97 | 0.99 vs 0.92 |
| c | 97.27 | 98.97 | 98.91 | 0.94 vs 0.55 |

On raw the level moves by up to 3.0 dB and the channels change order: m-R reads above w-L, w-R
and c, while on a log grid it is the quietest channel. Any
fractional read agrees within 0.3 dB, because it is the grid that matters here, not the width.

### 2.5 What each decision smoothing removes from 1/48

The same nine positions per channel. Removed from the 1/48 read: *common* rms dB (the car — what is
lost) / *random* rms dB (interference — what is gained), then the spread left between positions
(`coherence2.py`):

| band, Hz | 1/6 | 1/3 | Var | Psy | ERB | spread at 1/48 |
|---|---|---|---|---|---|---|
| 20–40 | 1.63 / 0.32 · 0.31 | 2.55 / 0.38 · 0.27 | 0.07 / 0.02 · 0.47 | 3.07 / 0.41 · 0.27 | 3.67 / 0.47 · 0.35 | 0.48 |
| 80–160 | 1.88 / 1.23 · 1.21 | 3.65 / 1.61 · 1.16 | 0.23 / 0.24 · 1.75 | 4.46 / 1.69 · 1.16 | 4.80 / 1.73 · 1.09 | 1.88 |
| 320–640 | 1.08 / 1.19 · 2.46 | 2.06 / 1.84 · 2.12 | 1.15 / 1.29 · 2.46 | 1.90 / 1.74 · 2.22 | 1.89 / 1.79 · 2.17 | 3.18 |
| 640–1250 | 1.60 / 2.55 · 2.83 | 2.45 / 3.40 · 2.33 | 1.94 / 2.99 · 2.63 | 2.37 / 3.16 · 2.54 | 2.16 / 3.13 · 2.54 | 4.41 |
| 2500–5000 | 1.16 / 2.23 · 2.19 | 1.71 / 2.83 · 1.60 | 1.81 / 2.94 · 1.51 | 1.83 / 2.63 · 1.89 | 1.36 / 2.49 · 1.96 | 3.59 |
| 10000–20000 | 1.50 / 1.94 · 1.56 | 2.45 / 2.39 · 1.24 | 2.96 / 2.54 · 1.16 | 2.66 / 2.30 · 1.45 | 2.20 / 2.17 · 1.44 | 2.76 |

* **In the bass every fixed or perceptual smoothing removes mostly the car.** 1/6 takes 1.6–1.9 dB
  of common detail at 20–40 and 80–160 Hz against 0.3–1.2 dB of interference. Psy and ERB take
  3–4.8 dB: they show what is heard, and they hide the modes an EQ acts on. Var removes almost
  nothing there, because it is 1/48 below 100 Hz.
* **Between ~640 Hz and 10 kHz every smoothing removes more interference than car**: 1.3–2.0 dB of
  random per 1 dB of common for 1/6. 1/3 and Var leave the least spread (1.2–2.6 dB). In the top
  octave (the tweeter's direct sound), 1/3, Var and Psy remove as much car as interference or more.

## 3. Science

Existence and bibliographic data of every paper below were confirmed live. The publishers blocked
full text, so what a paper *says* is marked `[summary]` where it rests on secondary sources.

* **The ear resolves no finer than about 1/6 octave, and much coarser in the bass.** ERB(f) =
  24.7·(4.37·f/1000 + 1) Hz (Glasberg & Moore 1990, *Hearing Research* 47:103–138, formula verified):
  0.52 octave at 100 Hz, 0.23 at 500 Hz, 0.19 at 1 kHz, 0.16 at 4–10 kHz.
* **Audibility of a resonance depends on its width and sign** `[summary]`: broad peaks are heard
  at lower levels than narrow peaks of equal height, and peaks more readily than dips (Bücklein 1981,
  *JAES* 29:126; Toole & Olive 1988, *JAES* 36:122; Olive et al. 1997, *JAES* 45:116, for the bass).
* **Above the Schroeder frequency a single-point response is statistical.** f_s ≈ 2000·√(RT60/V)
  (Schroeder 1996, *JASA* 99:3240, formula verified). Level at one point fluctuates with a standard
  deviation ≈ 5.57 dB in a diffuse field (Schroeder 1954/1987, the textbook constant). Averaging N
  independent positions or bands cuts the variance by ~1/N (Schroeder 1969, *JASA* 46:277)
  `[summary]`. No automotive RT60 source was found. For V ≈ 3 m³ and RT60 0.05–0.15 s the formula
  gives 250–450 Hz (arithmetic only). **This car agrees with that**: raw position spread 5.2–5.5 dB
  above 640 Hz (§2.1), and the common share of fine detail falls between 320 and 640 Hz.
* **Smoothing a complex response equals windowing its impulse response in frequency-dependent
  time** (Hatziantoniou & Mourjopoulos 2000, *JAES* 48:259) `[summary]`. REW states the practical
  difference itself (§4): a window *excludes* late sound, a smoothing *averages it in*.
* **Equalisation is built on spatially averaged or smoothed data**; position-specific notches are
  not corrected (Cecchi, Carini & Spors 2018, *Applied Sciences* 8:16, review) `[summary]`.

## 4. REW's own documentation (verified on roomeqwizard.com help pages)

* **Kernel**: *"multiple forward and backward passes of first order IIR filters to implement a
  Gaussian smoothing kernel"*. **Phase and group delay are smoothed with the magnitude**
  (`graph_splphase.html`, `graph_groupdelay.html`). Whether it averages power or dB is not documented.
* **Var** — *"1/48 octave below 100 Hz, 1/3 octave above 10 kHz ... reaching 1/6 octave at 1 kHz"*;
  *"recommended for responses that are to be equalised"*. The EQ window says: *"It is best to apply
  the 'variable' smoothing to the response before running the target match."*
* **Psy** — 1/3 octave below 100 Hz, 1/6 above 1 kHz, *"cubic mean"* (weights peaks); *"more
  closely corresponds to the perceived frequency response"*.
* **ERB** — (107.77·f + 24.673) Hz, f in kHz: about 1 octave at 50 Hz, 1/2 at 100 Hz, 1/3 at 200 Hz,
  ~1/6 above 1 kHz.
* **Bass**: *"Smoothing should rarely be used for low frequency measurements as it obscures the true
  shape of the response."*
* **Nothing finer than 1/48 exists on REW's log grid**: *"to avoid sampling artefacts log-spaced data
  will be smoothed to ppo/2"* (API). A sweep converted to 96 ppo gets *"a 1/48th octave smoothing
  filter ... to remove any high frequency combing"* (`analysis.html`).
* **FDW**: *"The corresponding octave fraction has an effect similar to applying a smoothing of the
  same octave fraction, except the variable window excludes progressively more of the late arriving
  sound as frequency increases rather than just averaging it out"* (`impulseresponse.html`). 15
  cycles appears as the example; whether it is the default is not stated.
* **RTA** resolution is fixed at capture (up to 1/48 octave); smoothing stacks on top of it.
* Choices, read live from `GET /measurements/frequency-response/smoothing-choices`:
  `1/1 1/2 1/3 1/6 1/12 1/24 1/48 Var Psy ERB None`.

## 5. Practice

Verified on fetched pages:

* **Audiofrog (Andy Wehmeyer)**: multi-mic averages correlate better with hearing, but *"a single
  mic measurement with 1/6 octave smoothing is sufficient to approximate a spatial average around the
  listener's head"*; keep parametric filters at Q < 6.
* **Harman (Sean Olive)**: spatial averages over six mic positions *"to avoid equalizing spectral
  artifacts that are very localized to the position of the microphone"*.
* **Genelec AccuSmooth**: narrower than 1/3 octave at low frequencies, about 1/3 at high ones.
* **DRC-FIR**: *"above 1-2 kHz only the direct sound gets corrected"*.

Not verified (secondary sources only):

* diyMobileAudio's working consensus is 1/6, with 1/12 as the finest worth EQ.
* IASCA scores RTA in 1/3 octaves.
* Acourate's FDW is 15 cycles.
* Helix PC-Tool has 30 PEQ bands per channel (confirmed twice) with Q 0.5–15 (later 50).
* Practitioners read phase through an FDW of ~6–15 cycles.

Nothing found recommends finer than 1/12 octave for a tuning decision, and no car DSP publishes an
auto-EQ resolution.

## 6. Proposals — decided by the Arbiter 2026-09-17

**Decided in the conversation of 2026-09-17**: 2 → `1/6`, 3 → `Var`, 5 → the impulse through a window
(`1/48` until then; which window is a decision of its own), 7 → `1/6` with `--smoothing`, each the
recommended option. 1, 4 and 6 follow from the Arbiter's `None` = `1/48` and were put to him with
"say if not"; no objection came.

**Built the same day** on `wave-2026-09-16` (`c7c8e17`, and the joints commit after it); on the
reference car's six `_01` junctions the impulse reading turned m-L↔tw-L at 4 kHz from INV with a −21 dB
residual to NORM with −3 dB, moved m-R↔tw-R from −1.17 to −0.35 ms, and asks for an all-pass at two
junctions instead of five. No measured pair was on the session, so neither reading is verified there.

**Standing position of the Arbiter (2026-09-17): `None` and `1/48` are one level.** Finer than 1/48
brings nothing for this chain (Scarlett, Helix) and adds interference. §2.1, §2.2 and §4 agree:

* in the bass the two are the same curve;
* above 640 Hz what is finer is 81–88 % position-random;
* 1/48 keeps ≥ 97 % of a Q 15 resonance;
* REW's own log grid stops at 1/48.

So a reader that wants "unsmoothed" asks **`1/48`**, never `None`. `None` would bring a linear grid
the readers pick points from, level shifts up to 3 dB, an RTA that answers `1/48` anyway, and
55k-point reads.

| # | analysis | reader | ask | why | alternative |
|---|---|---|---|---|---|
| 1 | Is the capture usable, and the channel's level | `verify` | `1/6` | the grid decides the level, not the width (fractions agree ≤ 0.3 dB); one tone standard | any fraction |
| 2 | Tonal balance against the target, in bands | `rew_tool analyze-batch`, `run` (deviation) | `1/6` | skill doctrine; Audiofrog; the ear's ERB ≥ 1/6 | `Psy` — the perceived curve, peaks weighted |
| 3 | EQ cut suggestions | `rew_tool run` | `Var` | REW's recommendation for EQ. In the bass it keeps 1/48, where 59–97 % of the detail is the car. From ~1 kHz it is as coarse as 1/6–1/3, where most detail is interference | `1/6` everywhere: simpler, removes 0.4–1.9 dB of real modal detail in the bass |
| 4 | Audible-peak suspects; fine features | `ear_suspects`, `curve_view.find_features` | `1/48` | both smooth themselves; a `1/6` input cuts the stable suspects by 30–66 % (§2.4); `None` adds none | — |
| 5 | Polarity, delay, all-pass at a junction; group delay | `rew_tool analyze-joints`, `run` (GD) | the impulse through a frequency-dependent window, as `flaw_map` and `predict` already read it; `1/48` until then | REW smooths phase with magnitude; a window excludes late sound instead of averaging it in; doctrine: junction timing through the direct sound | `1/48` for good |
| 6 | Measured channel against the prediction (RTA only) | `verify_prediction` | `1/48` | its criterion is defined after its own 1/6 mean; a `Psy` or `1/6` view widens that to ~1/4.2 | — |
| 7 | Checking a number someone quoted | `spot_check` | `1/6` by default, `--smoothing` to match the claim, the smoothing printed | a claim is checked at the smoothing it was made at; 1/6 is the standard agreed with the critic | the view |

Consequences if accepted:

* `curve_view`'s refusal accepts `1/48` as clean (effective fine 1/21.5 against its own 1/24) and
  names `1/48` in its message.
* Every call names its ask, and a selftest pins the query each reader sends (`rew_stub` always
  answers `None`, so CI sees none of this today).
* `analysis-playbook.md`'s smoothing line gains `Var` for EQ and `1/48` as the finest read.

## 7. Open

* REW does not document whether its smoothing averages power or dB.
* Helix PEQ Q limits are not verified from Audiotec Fischer's own documents.
* No published car-cabin RT60 was found. This car's own transition, from §2.1, is ~320–650 Hz.
* Which frequency-dependent window a junction should be read through is a decision of its own, not a
  smoothing (proposal 5).
