# Research 2026-10-14 — Should the method's EQ ever boost, and how much (#173)

Marks: **[S]** two or more independent sources · **[S1]** one source · **[P]** this repo's own
code or data · **[I]** inference · **[low]** a practitioner guide or a forum, trust below a paper
or a tool's own help. Every source cited below was fetched and read for this note, except where
it says "not read".

## The question

`eq_propose` only cuts. `--allow-boost` is accepted and changes nothing. Should the method ever
propose a boost? If it should: which dips, how much, and against which headroom check? The answer
goes to the Arbiter as a proposal. Any code is a later task, after his ruling.

## What the method does today

- **Cuts only, everywhere.** `rew_tool/eq_propose.py:385` `package_res` drops a dip at
  `:417-422`: below Schroeder *"a dip: the packages do not boost -- a boost path is not built"*,
  above it *"the position, not the car (Rayleigh statistics)"*. A peak is cut by
  `gain = -min(height, MAX_CUT_DB)` (`:451`); `MAX_CUT_DB = 6.0` (`:96`), `SCHROEDER_HZ = 200`
  (`:89`). L/R (`:361`) and tone (`:509`) fit with `gain_hi=0.0`; tone reports a band under the
  target (`:520-521`): *"raise the pair's level or accept; a boost into a null burns headroom"*.
- **The flag.** `--allow-boost` (`:982`) only prints a warning (`:994-997`);
  `_check_no_boost_path_said` (`:1272-1295`) pins that it changes nothing.
- **A boost machine exists, unused.** `dsp_math.greedy_eq_fit` (`:853`) boosts only in the true
  passband (`:897`), not into `no_boost_zones` (`:899-917`), not past a `boost_gate` veto
  (`:918`), never twice within 1/3 oct (`:920-923`), and at most **4.5 dB summed per driver**,
  *"headroom + EQ-ability caution"* (`:925-926`). `eq_propose` closes it with `gain_hi=0`.
- **Method text.** `FAQ.md:133`: *"a dip that would need a boost is almost certainly a
  cancellation"*; `phase_2_eq.md:28,49`, `virtual-first.md:355`, `happy-paths.md:39`: cuts only,
  ≤ 6 dB. But below Schroeder `phase_2_eq.md:55` calls a dip *"a legitimate target"* and
  `diagnostic-techniques.md:127` says it *"may be worth a filter"*: the doctrine admits a boost
  there, the code does not.
- **The 09-23 verdict table** (`docs/RESEARCH-2026-09-23-min-phase-verdict.md:224-225`): *dip, MIN*
  below Schroeder is *"a legitimate boost candidate within the +6 dB ceiling"*, above it *"never
  boosted on single-point evidence"*; *dip, NON* is `cabin_null`, no boost. This note extends
  those rows.
- **A conflict inside the method.** `flaw_map.py:19,135` writes *every* dip below Schroeder as
  `cabin_null / no_boost` (flagged by 09-23).
- **The vendored reference.** `vendor/Resonalyze/dsp/EqAutoTuner.cs`: band gain up to **+6 dB**
  (`:20`); `TotalGainMaxDb`, *"a clip-safe cuts-only caller passes 0"* (`:28-32`); `CutsOnlyMode`,
  *"the EQ Wizard defaults it on (boosting a cabin's nulls does harm)"* (`:47-48`); a boost skirt
  may pour at most 0.5 dB into a masked bin (`:57`). `EqBoostabilityMask.cs:3` refuses *"narrow
  deep nulls and low-coherence bins"* (6 dB deep, ±1/4 oct). **[P]**

## What the sources say, by trust

**Tier 1: peer-reviewed papers and a tool author's own help.**

1. **Toole, *The Measurement and Calibration of Sound Reproducing Systems*, JAES 63(7/8) 2015**
   ([PDF](https://www.linkwitzlab.com/Toole-Room%20calibration.pdf), text extracted and read).
   - Above the transition frequency, interference peaks and dips *"are non-minimum-phase
     phenomena that are not correctable by minimum-phase equalization."*
   - Below it, *"equalization has a role to play"*. Two uses:
     - upper-bass boundary (Allison) fluctuations *"can be corrected for by equalization, using a
       spatially-averaged measurement to reveal the underlying curve"*;
     - in the low bass, EQ is *"very useful as a means of attenuating prominent room resonances
       at a single listening location"*.
   - A crossover interference dip *"cannot be corrected by equalization"*, while transducer
     resonances, being minimum-phase, *"can be attenuated by using matched parametric filters"*.
   - The only boost this paper endorses is the spatially averaged upper-bass one. Its words for
     single-point use are *attenuate*. **[S1]**
2. **REW help, *Minimum Phase*** (J. Mulcahy;
   [link](https://www.roomeqwizard.com/help/help_en-GB/html/minimumphase.html)).
   - *"the peaks in a response are a result of features that are correctible through
     equalisation"*.
   - For sharp dips in non-minimum-phase regions, there are *"poor results which are often found
     when trying to lift such regions with EQ"*, and *"That zero level cannot be restored ... by
     any amount of EQ"*.
   - *"Low frequency peaks ... are usually in minimum phase regions"*. A dip can go either way.
     **[S1]**
3. **REW help, *EQ window***
   ([link](https://www.roomeqwizard.com/help/help_en-GB/html/eqwindow.html)). REW boosts, but
   with brakes:
   - *Individual Max Boost* and *Overall Max Boost*, each *"can be set to zero"*;
   - the headroom an overall boost needs *"will be shown on the EQ filters panel"*;
   - *"boost filters are subject to Q limits to avoid inadvertently creating artificial
     resonances"*: the 60 dB decay time is capped at about 500 ms;
   - by default, no filters *"below the frequency at which the measurement first exceeds the
     target"*;
   - *"beware of exceeding the excursion limits or headroom of the woofer."*

   No default number is stated. **[S1]**
4. **Mulcahy, AV Nirvana** (a forum, but the author of REW).
   - [EQ thread](https://www.avnirvana.com/threads/minimum-phase-and-eq-filters.8801/): *"don't
     try and tackle sharp dips"*. In non-minimum-phase regions, results are *"likely to be quite
     different at other measurement positions"*.
   - [Car thread](https://www.avnirvana.com/threads/car-environment-minimum-phase.5342/): *"A car
     environment is no more minimum phase than a room"*. **[S1]**
5. **Linkwitz Lab, *Rooms*** ([link](https://www.linkwitzlab.com/rooms.htm)).
   - *"It is best to attenuate peaks in the bass response with parametric equalization."*
   - *"Holes in the response cannot be filled in"*.
   - *"The response should not be optimized merely at the listening position."* **[S1]**

   With 1, 2 and 4: **[S]** cut peaks; do not fill sharp dips.
6. **Binelli & Farina, *Digital equalization of automotive sound systems employing spectral
   smoothed FIR filters*, AES 125 (2008)**
   ([PDF](https://angelofarina.it/Public/papers/245-AES125.pdf), text extracted).
   - Car EQ by regularised inversion, `S = G*/(|G|²+ε)·T`, with *"ε ... typically equal to
     0.01"*, raised *"up to a much higher value (typically 1.0) at extreme frequencies, where the
     system cannot be controlled"*.
   - **[I]** Regularisation is itself a boost cap. The gain of `G*/(|G|²+ε)` peaks at
     `1/(2√ε)`, which is +14 dB at ε = 0.01 relative to a normalised G. Automotive FIR practice
     does fill dips, but only up to a bound, and only on a smoothed response. **[S1]**
7. **Cecchi et al., *Evaluation of a Multipoint Equalization System based on Impulse Responses
   Prototype Extraction*, AES 127 poster**
   ([link](https://www.slideshare.net/slideshow/poster-aes127/23785515)).
   - In a high-end car, multipoint EQ reduced spectral deviation more than single-point EQ: ΔSD
     1.27 against 0.73 (fast deconvolution).
   - *"the performance inside the equalization zone decreases but the outer positions take
     advantage of the broader equalization"*.
   - EQ designed on several positions is more robust in a car. **[S1]**

**Tier 2: psychoacoustics, read only second-hand.**

8. **Bücklein (1962; JAES 29, 1981)**, *The Audibility of Frequency Response Irregularities*.
   The AES page answered 403, so neither paper was read. The 1962 result, as quoted in Myung &
   Sung, 1995
   ([PDF](https://koreascience.kr/article/JAKO199515875835942.pdf), text extracted): *"a peak in
   the frequency response curve is audible and very irritating, a dip that has the same
   amplitude and width is barely audible"*. **[S1, second-hand]**

   Toole & Olive, *The Modification of Timbre by Resonances* (AES), also returned 403 and was not
   read. Its conclusion that *"the spectral bump ... is the most reliable indicator of
   audibility"* reaches this note only through Toole 2015 (source 1).

**Tier 3: manufacturers and practitioners.** **[low]**

9. **Car-audio guide**, audiointensity.com,
   [*Car Audio EQ Guide*](https://audiointensity.com/blogs/how-to-tune/car-audio-dsp-step-by-step-eq).
   - *"Cut, do not boost. ... mostly cuts, with no single boost above 3 dB."*
   - On a cancellation dip: *"Do not boost it"*, because it risks *"amp clipping at high volume
     with the dip still measurably there"*. Instead, *"Move the speaker, change the crossover, or
     accept the dip."*

   A retailer's blog: practice, not evidence.
10. **Auto-EQ products: not verified, not evidence.** Genelec's AutoCal2 positive-gain article
    returned 403 (its snippet: per-model limits, aimed at *"a low-Q notch in the range
    100...300 Hz"*); its [RRC page](https://www.genelec.com/key-technologies/room-response-compensation)
    gives no numbers. Dirac (~+10 dB) and Audyssey (+9 dB) exist only as forum snippets. Audison
    and Helix manuals were not found.

## Where they agree, and where they do not

**They agree on these points.** **[S]**
- **Peaks are cut, and sharp dips are left alone.** Sources 1, 2, 4, 5 and 9 say so, and the
  method's resonance rule already follows it.
- **Above Schroeder, a single-point dip is not a target.** Sources 1, 2 and 4 say so, and so do
  the method's own Geddes & Blind and Rayleigh notes (`diagnostic-techniques.md:127`).
- **Boosting is a budget, not a ban.** Every tool that boosts caps it:
  - REW: per-filter, overall, and a Q/decay limit (source 3);
  - FIR regularisation (source 6);
  - Resonalyze: +6 dB, and `TotalGainMaxDb` (vendor code);
  - this repo's own `greedy_eq_fit`: 4.5 dB summed per driver.
- **Headroom and excursion are the price of a boost** (sources 3 and 9, and `level_offsets.py:125`).
- **Position robustness decides whether a correction is real** (sources 4, 5 and 7, and the
  09-23 note's sources 7, 10 and 11).

**They disagree, or leave a gap, here.**
- **Whether a minimum-phase dip below Schroeder may be filled.**
  - REW's help implies yes: a minimum-phase region takes EQ either way (2).
  - Linkwitz's *"cannot be filled in"* is about holes, meaning sharp nulls (5).
  - Toole endorses only a spatially averaged upper-bass lift (1).
  - Nobody publishes a criterion that tells a fillable bass dip from a null by number. The 09-23
    note found the same gap for the minimum-phase threshold.
- **How much.** The numbers run from 3 dB (9, low trust), through 4.5 dB summed (this repo) and
  6 dB (Resonalyze), to about 10 dB (products, unverified). No source derives its number. They
  are all engineering choices.
- **Why so little is lost by not filling.** Dips are far less audible than peaks of the same
  size (8). This argues for *partial* fills, and against chasing the last decibel.

## What the method's own machinery already gives

Each test a boost would need is built and already in use somewhere. **[P]** Only the assembly is
missing.

| need | machinery | where |
|---|---|---|
| minimum-phase at this dip, measured against its own floor | `min_phase_verdict`, and `min_phase_across` over the 3 centre returns (MIN / NON / UNSTABLE / PROVISIONAL; `scope` decisive below Schroeder) | `eq_gate.py:287`, `:436` |
| no phase anomaly where the filter delivers gain (150–4000 Hz) | `ExcessPhaseGate.check` → ALLOW / WARN / BLOCK / OUT_OF_SCOPE | `eq_gate.py:124`, `:156` |
| the dip is the car's, not the mic's | ellipsoid `stays` (present in enough positions, depth σ bounded by the depth) | `ellipsoid.py:203-206` |
| tolerance against the target | max(1 dB, 2σ(f)) | `eq_propose.py:88`, `:501` |
| Q no narrower than the space supports | `q_ceiling_at` | `eq_propose.py:436` |
| away from a junction, and where the channel plays | `_junction_mask`, `live_band` | `eq_propose.py:395-397` |
| a boost budget and a no-stacking rule | `greedy_eq_fit` (4.5 dB, 1/3 oct) | `dsp_math.py:920-926` |

**What is not built is a headroom check.** Nothing reads the channel's summed EQ maximum against
its gain trim or the DSP's input headroom. Nothing reads a boost against the driver's HPF corner,
which is where excursion lives.

## Proposal (advice to the Arbiter)

**Advice: option B, a narrow, opt-in `fill` path for one dip class, with the default left at
cuts only until the Passat check (below) has run.** Reasons:
- the doctrine (`phase_2_eq.md:55`) and the 09-23 table already admit the class;
- REW's help allows EQ in minimum-phase regions (2); Toole only a spatially averaged bass lift
  (1), which the ellipsoid condition approximates; REW and FIR practice bound the amount (3, 6);
- dips are cheap to leave partly unfilled (8), so a low cap loses little.

**B. The class: all of these must hold at once.**
1. **Below `SCHROEDER_HZ`** (200 Hz). Above it: none in this path — a narrowing of the 09-23 row, which
   bars only single-point evidence.
2. **`min_phase_across` = MIN_PHASE**, agreed on ≥ 2 of 3 centre returns, with a measured floor.
   NON or UNSTABLE means no boost, and so does a take flagged PROVISIONAL (no floor measured).
3. **Ellipsoid `stays`** for the dip, matched as `package_res` already matches peaks (±1/6 oct).
   A dip that moves is the position.
4. **Gate, read over the same 3 centre returns.** Where it is in scope (≥ 150 Hz): BLOCK on
   ≥ 2 of 3 returns means no boost; BLOCK on 1 of 3 makes the dip UNSTABLE (no boost); WARN does
   **not** bar the fill once item 2 reads MIN on ≥ 2 of 3, and the package says so. Why: below
   Schroeder the 09-23 note makes the minimum-phase verdict *decisive*; the gate is strong as a
   BLOCK detector (90/90 on matched combs, at z_warn 5.0) but *"NOT a certifier"*, and at the default z_warn
   *"deep min-phase dips tip to WARN ... an abstention, not a false block"* (`eq_gate.py:30-38`).
   Requiring ALLOW would bar exactly the deep minimum-phase dip this path exists for. Below
   150 Hz the gate has no vote, and items 2 and 3 decide.
5. **Width 1/6 to 2/3 oct**, the same window as `RES_WIDTH`. Narrower is a null (2, 4, 5; the
   Resonalyze mask). Broader is tone, and goes to option C.
6. **Inside where the channel plays, and ≥ ½ oct above its HPF corner.** This follows REW's
   *"first exceeds the target"* rule and its excursion warning (3). It is also ±1 oct from any
   junction, as for cuts.

**Cap.**
- **+3 dB per band, and at most half the dip's measured depth**, whichever is smaller.
- **At most one fill per channel**, and the existing **4.5 dB summed budget** never applies in
  full.
- Q is capped at the ellipsoid's ceiling, and at REW's decay-time rule for boosts (3).
- Why +3, not 09-23's +6: +6 looks like the cut budget borrowed **[I]** (or `diagnostic-techniques.md:58`, *"Depth > +6 dB to 'fix' ⇒
  almost certainly cancellation"*), derived by no source; a half fill takes
  most of the audible gain (8); REW, the guide and car FIR practice all bound it (3, 6, 9). This
  **narrows** the 09-23 row; it does not contradict it.

**Headroom check (new, required).**
- Report the channel's summed EQ maximum, cuts plus fill, on the 1/48 grid.
- If it is above 0 dB, the package carries a channel gain trim of minus that maximum, the
  Resonalyze `TotalGainMaxDb = 0` contract. Otherwise it says so and is refused.
- The settings sheet names the trim. Without the trim, the Arbiter is told the boost spends
  amplifier headroom at full volume.

**Process.**
- A separate package, `fill:<channel>`, with its own `why`, accepted or refused whole.
- Only with `--allow-boost`, which finally means something.
- The predicted lift is checked at **all** ellipsoid positions in 2.2. The `listen` id is one
  pair, one question.

**Alternatives.**
- **A — none (today).**
  - For: simplest; matches the guide and Linkwitz; no headroom risk.
  - Against: a real, stable, minimum-phase cabin deficit stays; the dead flag and the `flaw_map`
    contradiction stay. If A is chosen, `phase_2_eq.md:55` should say "none".
- **C — a broad lift by level or shelf, not by PK.**
  - The tone package's own advice (*"raise the pair's level"*), and Toole's spatially averaged
    case (1), judged on the ellipsoid **mean**. Robust, but moves everything under the shelf and
    costs the same headroom. Beside B, not instead of it.
- **D — fix it at the source** (delay, polarity, crossover, position; 1, 9). Always first; B is
  for what D cannot reach.
- **E — B with the 09-23 +6 dB cap.** Twice the headroom for little audible gain (8).

## What a later code task would change (no code here)

- **`eq_propose.py`.**
  - A `package_fill`, reached from `package_res`'s dip branch (`:417-422`) only when
    `allow_boost`.
  - The reason text says which of B1–B6 failed.
  - `_check_no_boost_path_said` (`:1272-1295`) is replaced by checks that hold the class:
    a synthetic MIN, stays dip fills at +3; a NON, moves or WARN dip does not; above 200 Hz,
    never.
  - The `--allow-boost` help and its stderr note change.
- **`flaw_map.py:133-137`.** The blanket `cabin_null` gives way to the verdict, as 09-23 already
  asked.
- **The headroom report**, new, in `eq_propose` or `apply.propose`.
- **The method text**, in one pass: `FAQ.md:133`, `phase_2_eq.md:28,49,54-55`,
  `virtual-first.md:355`, `happy-paths.md:39`, and this repo's header text at
  `eq_propose.py:38-39`.

## What would refute the proposal

1. **The 09-23 Passat check.** Its §5 asks for the w-L ~150 Hz dip over one ellipsoid round,
   9 sweeps, read by `min_phase_across` **and** the gate per return (B2, B4). The car record has
   it gate BLOCK on 5/5 takes with S = 3.3 … 589 (09-23); if BLOCK holds on ≥ 2 of 3 returns, or
   the verdict is NON or UNSTABLE, B has no member on this car so far. Only MIN with no majority
   BLOCK adds it to B.
   - If the next ellipsoid round on a second car also yields **no** dip passing B1–B6, the path
     is dead code: choose A.
2. **A fill that does not arrive at the head.**
   - Apply a +3 dB fill to a dip that passes all six tests, then re-measure the ellipsoid.
   - If the mean lift across the 6 positions is under **half the applied gain**, or the spread
     σ at the dip grows by more than 1 dB, the dip was not fillable in practice. The class is
     wrong, whatever the verdicts said.
3. **The ear.** One blind pair, fill against no fill, on 2–3 tracks with content at the dip. If
   there is no preference across two sessions, the dip asymmetry (8) has won. Keep A, and close
   #173 with that sentence in the FAQ.
4. **Headroom in use.** If the trimmed channel limits or clips at the Arbiter's working volume,
   or the trim audibly costs level he wants, the cap is too high for this install. Lower it, or
   choose A.
