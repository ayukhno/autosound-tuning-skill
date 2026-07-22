# Deviation-analysis audit — how much can the reported numbers be trusted?

Audit of the Analyze panel's comparison math, run against a real measurement.
Date: 2026-07-22.

**The question:** not "how do we improve the car" — whether the numbers the panel prints
are stable enough to be worth printing.

**The answer:** the *detector* is solid. The *reporting* is not. Every dB figure carries
roughly ±0.5 dB (worst case 1.4 dB) of purely numerical arbitrariness, coverage swings 7
points, and a +8 dB feature is shown only half the time — while the UI prints `+8.1 dB`,
`−6.2 dB`, `51%` as if exact.

## 1. Method

- Baseline `SQ-Comp-Ref`, compare `ALL_32 SQ-CRv3.txt` (REW RTA, 1/48-oct steps, already
  1/24-oct smoothed by REW, 150 averages).
- The page's math was ported to Python and validated against the live browser: coverage
  74%, tilt +0.8232, band means −9.56 / −7.03 / −3.33 / +1.63 / +1.19 matched to the last
  digit. All numbers below describe the shipping code.
- Robustness was measured by re-running the *same data* under 8 combinations of choices
  that are all equally defensible and none of which change anything physical:
  level anchor `mean` vs `median` × grid phase `0` vs `half-bin` × resampling
  `point-sample` vs `bin-average`.

## 2. What is trustworthy

| quantity | spread across the 8 variants | verdict |
|---|---|---|
| Tilt | +0.456 … +0.464 dB/oct (0.01) | **solid.** OLS vs robust Theil-Sen also differ by only 0.02 |
| Feature *detection* | every real feature fires 8/8 | **solid** |
| Classification at a *fixed* smoothing | no class changed in any variant | **solid** |

The detector itself is not the problem. Nothing below is about it.

## 3. What is not trustworthy

### N1 — the smoothing window is not a constant width (bug)

The 1/N-oct pass selects its window by frequency multiplication with an inclusive float
compare (`q.f >= f/2^h && q.f <= f*2^h`). Tap counts actually used across the 1/6-oct pass:

```
5 taps: 115 bins | 4 taps: 106 bins | 3 taps: 18 bins | 2 taps: 1 bin
```

It should be a constant 5. The effective smoothing flutters bin to bin, which injects
ripple into the exact signal the feature detector then looks for. Fix: select the window by
**index** (±k bins), not by frequency comparison.

### N2 — the top-8 cap silently drops real features

The detector fires on **9–10** candidates per run; the report is hard-capped at 8. So 1–2
real features are dropped every single run, and *which* ones is decided by sub-0.1
differences in a severity score. Detected vs actually reported, across the 8 variants:

| feature | detected | reported |
|---|---|---|
| 40 Hz peak **+8.1 dB** | 8/8 | **4/8** |
| 57 Hz peak +3.7 dB | 8/8 | 6/8 |
| 80 Hz peak +5.3 dB | 8/8 | 8/8 |
| 155 Hz dip −6.2 dB | 8/8 | 8/8 |
| 1.1 kHz dip −6.3 dB | 8/8 | 8/8 |
| 2.8 kHz peak +2.8 dB | 8/8 | 8/8 |
| 3.7 kHz dip −3.2 dB | 8/8 | 8/8 |
| 14.5 kHz peak +2.9 dB | 7/8 | 7/8 |

The single largest deviation in the whole measurement — **+8.1 dB at 40 Hz** — is found
every time and shown half the time. That is not a ranking preference, it is a coin flip.

Root cause is the severity formula, `|h| × min(width,1.2) × audibility(f) × (0.55 if dip)`:

```
sev 2.43  peak   2792 Hz  +2.8 dB   <- ranked #1
sev 1.34  peak     40 Hz  +8.1 dB   <- ranked #3, first to fall off the cap
sev 1.21  peak  14482 Hz  +2.9 dB   <- outranks BOTH −6 dB nulls
sev 1.13  dip     155 Hz  −6.2 dB
sev 1.00  dip    1108 Hz  −6.3 dB
```

Three compounding causes: the width multiplier rewards a wide HF ripple; the audibility
weights (0.25 below 40 Hz, 0.5 below 80 Hz) de-rate bass twice; a flat 0.55 `dipPenalty`
halves every deficit. Fix: cut on an **absolute** significance threshold rather than a
fixed count, and stop letting a +2.9 dB ripple at 14.5 kHz outrank a −6.3 dB hole.

### N3 — the level anchor is a non-robust mean

Everything in the report is relative to one number: `mean(delta)` over 300 Hz–3 kHz. That
band contains this car's −4.9 dB notch at 1140 Hz and +4.4 dB at 570 Hz, so the mean is
dragged by exactly the features being measured. Across defensible estimators:

```
mean 300-3k (shipping) +56.84 | median 300-3k +57.21 | mean 100-10k +56.21
median 100-10k         +56.49 | median 20-20k +57.22 | energy mean 300-3k +57.50
                                                          spread 1.28 dB
```

Fix: use the **median** (equivalently, the least-absolute-deviation optimum), which a few
deep narrow notches cannot drag.

### N4 — resampling decimated by point-sampling — FIXED

The 1/48-oct measurement was resampled onto the 1/24-oct grid by *sampling* the interpolated
value, so half the measured points were skipped rather than averaged. Difference vs
bin-averaging: median 0.05 dB, 95th pct 0.38 dB, **max 0.78 dB at 1016 Hz** — right on the
edge of the deepest notch. Now averages every source point falling in the bin, which also
normalises whatever resolution a file arrives at down to the grid's own 1/24 oct — the
finest the psychoacoustic setting ever asks for — so the analysis starts from the same
resolution regardless of the smoothing the file was exported with. Sparse target curves
leave most bins empty and still fall back to interpolation.

### N5 — coverage is reported with precision it does not have

`51%` in the UI. Across the 8 variants it ranges **48–55%**. It also moves 49→53% for a
±0.1 dB change in the hard ±1.5 dB threshold, and it is measured only over 100 Hz–10 kHz,
which excludes the band where this car's largest errors live.

### N6 — resulting uncertainty on the printed numbers

```
metric                  shipping     min     max   spread
coverage %                    51      48      55       7
tilt dB/oct                 0.46    0.46    0.46    0.01
band mean 20-60 Hz         +3.53   +3.15   +3.60     0.44
band mean 100-200 Hz       -2.58   -2.98   -2.58     0.40
band mean 1000-2000 Hz     -1.39   -1.80   -1.39     0.41
band mean 2000-4000 Hz     +0.51   +0.13   +0.56     0.43

feature depth spread:  40 Hz 0.50 | 80 Hz 0.44 | 155 Hz 1.40 | 1.1 kHz 0.69 | 2.8 kHz 0.39
```

So a printed `−6.2 dB` is really `−6 to −7.6 dB`, and `51%` is really `≈50%`.

### N7 — classification flips with the smoothing dropdown

Width at −3 dB is the only thing separating NULL ("never boost") from DIP ("a gentle boost
is fair"), and width is not smoothing-invariant, while smoothing is a user dropdown:

| feature | None | 1/12 | 1/6 | 1/3 | psycho |
|---|---|---|---|---|---|
| ~155 Hz | 0.21 → **NULL** | 0.38 → DIP | 0.42 → DIP | 0.46 → DIP | 0.21 → **NULL** |
| ~1.1 kHz | 0.29 → **NULL** | 0.29 → **NULL** | 0.29 → **NULL** | 0.50 → DIP | 0.50 → DIP |

Smoothing trades depth for width: 155 Hz reads −7.8 dB / 0.21 oct un-smoothed and
−6.2 dB / 0.42 oct at 1/6. `|depth| × width` is roughly conserved across 1/12…1/3
(2.55 / 2.58 / 2.65), which makes it a better invariant than width alone — but not a fix on
its own. Fix: run the classification on a **fixed internal smoothing**, so the dropdown
changes what you see and never what you are told.

### N8 — boundary dead zone

The ±4-bin extremum window makes a feature impossible below **22.45 Hz** and above
**17.7 kHz**. This car's **+6.5 dB at 21.8 Hz** can never appear. Fix: clamp the window at
the array ends.

### N9 — "None" smoothing implied raw data the page never had — FIXED

The REW export declares `Smoothing: 1/24 octave` in its own header. Choosing "None" showed
1/24-smoothed data while implying it was raw. The option has been removed; the default was
already 1/6 oct. Surfacing the header value is still open.

### N10 — "Resonance control" is a single-feature lottery

The grade sums severity of **narrow peaks only**. Here that is exactly one feature — the
40 Hz peak, score 1.34 against an "Excellent" edge of 1.5 — so a car with two −6 dB holes
is graded "Excellent", and the grade is decided by the same feature that N2 shows is a coin
flip. The name also over-promises: resonance is ringing over time, invisible in magnitude
data.

## 4. Fixes, ordered by trust gained per unit of work

1. **N2** — cut on an absolute threshold instead of a top-8 cap, and rebalance severity.
   Stops the biggest deviation in the measurement from vanishing half the time.
2. **N1** — index-based smoothing window. Pure bug, small change, removes injected ripple.
3. **N3** — median level anchor. Removes ~0.4 dB of arbitrary shift from *every* number.
4. **N7** — classify on a fixed internal smoothing.
5. **N5/N6** — print the precision the data supports (`≈50%`, `−6 dB near 160 Hz`), or run
   the 4–8 variant ensemble internally and print median ± spread. It is cheap, fully
   offline, and turns the instability from a hidden flaw into the honesty mechanism.
6. **N4, N8, N9, N10** — resampling, dead zone, header parsing, grade rename.

## 4a. Implemented (fixes 1–3) and what they bought

Same 8-variant robustness test, before and after. The anchor axis collapses after the fix
because the median is now the definition rather than one defensible choice among several,
so "after" is 4 variants (grid phase × resampling).

```
metric                       OLD range      NEW range
coverage %                       48-55          52-54
band mean 20-60 Hz             0.44 dB        0.13 dB
band mean 100-200 Hz           0.40 dB        0.20 dB
band mean 1000-2000 Hz         0.41 dB        0.23 dB
band mean 2000-4000 Hz         0.43 dB        0.14 dB

feature          shown OLD   shown NEW    depth spread OLD -> NEW
40 Hz  +8.0            4/8         4/4          0.50 -> 0.14
57 Hz  +3.6            6/8         4/4          0.37 -> 0.17
80 Hz  +5.0            8/8         4/4          0.44 -> 0.12
160 Hz -6.0            8/8         4/4          1.40 -> 0.31
1.1 kHz -6.3           8/8         4/4          0.69 -> 0.25
3.7 kHz -2.8           8/8         4/4          0.69 -> 0.10
14.5 kHz +2.8          7/8         4/4          0.41 -> 0.13
```

Every feature is now reported in every run, and the arbitrary component of each printed dB
figure dropped by roughly 3–4×. The +8.1 dB at 40 Hz is now the first row of the report
instead of a coin flip.

Two visible consequences worth knowing about:

- **The ~2.8 kHz peak is no longer listed.** With the smoothing window fixed to a constant
  width, its prominence measures 0.79–0.97 dB against the detector's 1.0 dB gate —
  consistently below it, not flickering. It was partly an artifact of the fluttering
  window; the region reads as a broad plateau (+1.3 / +2.1 / +1.9 / +0.6 dB), and the
  2–4 kHz band still appears in the table via its 3.7 kHz dip.
- **Coverage on the built-in Flat comparison moved 74% → 63%**, purely because the anchor
  definition changed. The median anchor is nevertheless the better alignment by its own
  criterion — for that curve it halves the median |delta| inside the anchor band (0.918 →
  0.462 dB) and lowers the total absolute deviation (72.3 → 68.2). The coverage number
  moving that far on a 0.49 dB shift is a demonstration of N5, not a regression.

`analyzeAudib` and the resonance-control grade were deliberately left on the old scale (via
a separate `resW` term) so that rebalancing the ranking did not silently move that grade's
thresholds. Reworking the grade is still open (N10).

## 4b. Second round: features that were never found, and the boost rule

Found by the user looking at the 200–500 Hz row: it printed **−1.1 dB** ("slightly drier")
while the highlight on the chart sat on a **+3.6 dB** excursion at the top of the same band.

**N11 — prominence was probed at a fixed offset, so broad-based features were invisible.**
The gate read the delta at exactly ±4 bins (±0.17 oct). A feature sitting on a broad base
therefore measured almost no step however large it was:

```
554 Hz peak, +4.2 dB   left probe (494 Hz) +3.6   right probe (622 Hz) -0.1
                       prominence = min(0.60, 4.24) = 0.60  <  gate 1.00  -> REJECTED
                       true topographic prominence = 10.2 dB
```

So a +4.2 dB peak at 554 Hz and a −4.1 dB dip at 690 Hz — an 8.3 dB swing across vocal
fundamentals — were both absent from the report, and the 500 Hz–1 kHz band was then skipped
as "within ±1.5 dB" because the mean of that swing is +0.07 dB. Replaced with true
topographic prominence (walk out until the curve crosses the candidate's level, take the
shallower side). Feature count 7 → 10, still 4/4 stable across the numerical variants, and
now every band with real content carries a real feature instead of a band average.

**N12 — the highlight could point at the opposite sign to the number.** `analyzeFocusRange`
picked the largest |delta| in the band regardless of sign while the row printed the band
mean. Fixed by passing the sign of the printed number.

**N13 — the boost rule was not tied to what an EQ can actually do.** The panel said
*"broad shelf dip — a gentle wide boost is fair"* for a −6.0 dB notch at 160 Hz. Per
competition practice a deficit may only be lifted when it is low-Q, and even then only
partly. Using `Q = √(2^N)/(2^N − 1)`:

| Q | bandwidth |
|---|---|
| 1 | 1.39 oct |
| 2 | 0.71 oct |
| 3 | 0.48 oct |
| 4.3 | 0.34 oct ← the panel's old narrow/broad split |

The old threshold called everything above Q 4.3 "broad" and offered a boost, i.e. it
recommended lifting notches up to Q 4.3 and of unlimited depth. Now: below 0.48 oct
(Q > 3) a deficit is never offered a boost; above it, a deficit deeper than 3 dB gets
"take about 3 dB at most and leave the rest"; only a low-Q deficit within 3 dB keeps the
original "a gentle wide boost is fair". Cuts are unchanged — a cut is always physically
safe. The Q a tuner would actually dial is now printed on every feature row.

On the reference car exactly one of the four deficits still qualifies for a boost
(3.7 kHz, Q 1.3, −2.8 dB). Caveat: Q is derived from the −3 dB width, which is the fragile
quantity in N7 — it still moves with the smoothing dropdown, so treat the printed Q as
approximate until N7 is fixed.

## 5. Downstream: the advice layer (secondary to the above)

Separate from arithmetic trustworthiness, one output is actively dangerous: at 155 Hz the
panel says *"broad shelf dip — a gentle wide **boost** is fair"*. At 155 Hz a car is in its
modal region (first cabin mode `c/2L` ≈ 57–71 Hz; car Schroeder `2000·√(RT60/V)` ≈ 260 Hz),
so that deficit is a position-dependent cancellation: boosting spends excursion and buys
almost no SPL.

More generally the NULL/DIP/PEAK labels make a claim about **cause** that magnitude-only
data cannot support. The defensible reframing is to classify by **risk of acting** — a
positive deviation is always safe to cut, so only audibility matters; a negative deviation
is governed by a frequency prior, and below ~300 Hz should never be told "boosting is
fair". This is worth doing, but it is downstream of §4: better advice on numbers that move
±1 dB between runs is still not trustworthy.

## 6. Notes from the Critic review

Two rounds against `Gemini 3.1 Pro (High)`. It independently found N8, and contributed the
observation that smoothing trades depth for width (N7).

Its concrete replacement rule — *"detect on raw 1/48 data; `max_slope > 18 dB/oct` and
`depth > 4 dB` ⇒ null"* — was **refuted on the data**: measured max adjacent-bin slope
within ±0.5 oct is 68.7 / 52.1 / 67.5 / 79.8 / 62.4 / 48.9 / 35.5 dB/oct for the seven
features, i.e. everything exceeds 18 dB/oct by 2–4×, including the deliberately broad
1.5-oct one. On 1/48-step RTA data, adjacent-bin slope measures noise, not the envelope.
Conceded on re-review.

It also first argued that a never-boost default "destroys amplifier headroom"; in car SQ
the opposite holds — cutting preserves electrical and DSP headroom and costs only maximum
SPL, which is not the binding constraint at judging levels. Conceded on re-review.

**Lesson worth keeping:** the advisor argues well in prose but its numeric thresholds were
not checked against a real trace. Port the math and test the rule before adopting it.
