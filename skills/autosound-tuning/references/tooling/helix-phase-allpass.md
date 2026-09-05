# Helix DSP — the channel Phase control, and the AP1/AP2 bands of the EQ bank

Two different controls share the word "phase" on this processor, and this file keeps them apart:

* **the channel Phase control** (0–354.375° in the "Phase, Polarity & Time" block) — the user dials
  an ANGLE and the processor builds the filter. Its law was **measured on the bench** in 2026-09
  (§1); it is modelled by `rew_tool/phase_rotation.py` and applied by `predict.py` to any ledger
  row that carries `phase_deg` beside its crossover;
* **explicit AP1/AP2 bands** in the PEQ bank — the user types a corner (and a Q). Hardware-verified
  in 2026-07 and re-measured electrically in 2026-09 (§3).

Until 2026-09-05 this file was compiled from forums and the user's practice, and said so. The
first half is now measurement: Helix DSP Ultra S, 96 kHz, ~60 electrical sweeps over 2026-09-01/02
(processor output straight into the interface — no microphone, no cabin), curves published under
CC BY 4.0 in `ayukhno/autosound-measurements` (`hardware/helix/dsp-ultra-s/`, fact 6), the law
implemented independently by Resonalyze's author (`dsp/PhaseRotationControl.cs`, `bc957c8`,
DIMOSUS/Resonalyze#88) and his compiled library checked against all 32 published cases: median
phase residual **0.19° rms**, median corner agreement **0.10 %**, worst delivered-angle error
**0.75°**. The method's port is checked against the same 32 cases in its selftest
(`testdata/helix-bench/phase-control-vectors.json`). One earlier statement of this file was wrong
and is corrected in §1.4.

## 1. The channel Phase control — the law

**One RBJ second-order all-pass with Q = 1.0000**, whose corner the processor places so that the
filter's phase equals the dialled angle **at the channel's reference crossover**:

```
corner = solve f  such that  arg(AP2(f_ref; f, Q = 1)) == −angle        # the angle as a positive lag
```

Q holds at 1.0000 across the whole reachable range (45° → 1.0000, 354.375° → 1.0001); magnitude is
flat to 0.02 dB; the fitted corners land on the solved ones to 0.2 % (7961 Hz measured against 7977
solved for 90° at a 5 kHz reference; 4999 against 5000 for 180°; 3109 against 3107 for 270°).
Three things make it unlike every other filter in the method:

### 1.1 The angle alone is not a filter

It needs the channel's reference crossover to become one. A ledger row carrying `phase_deg` and
nothing else genuinely cannot be modelled — the row **plus the channel's own `hp`/`lp`** can, and
that is what `predict.chain_from_row` reads. The same 90° is a different filter on a channel
crossed elsewhere: 90° at a 5 kHz reference is a 7977 Hz corner; at a 2 kHz reference, 3229 Hz.

### 1.2 The reference is the crossover AS CONFIGURED, not as active

**Which corner:** the **low-pass on a subwoofer channel, the high-pass on every other channel that
has the control.** Bypass and `slope = OFF` leave the phase reference exactly in place — three
states measured, 0.018 dB and 0.12° apart. Reading the *live* crossover is the trap: it gives the
wrong corner on every channel whose filter is switched off. The ledger writes a disabled leg as
`null`/`"OFF"` and loses the frequency with it, so a crossover that is switched off in PC-Tool but
still configured is written **with its `f` and `slope: "OFF"`** — `predict` keeps such a leg out of
the chain and still reads it as the reference (`_phase_reference`).

**Which channels have it:** per Audiotec-Fischer the control exists on subwoofer channels and on
the mid/high channels of a fully active system; `fullrange` and `low` channels get plain 0/180
polarity instead. That is a hardware statement about channel TYPE. The method rule of §2 — "the
midbass is the anchor you do not rotate" — is a different kind of statement, and both stand.

### 1.3 The corner is capped at 3/16 of the processing rate — 18 kHz at 96 kHz

Undocumented by the manufacturer. Above the cap, **settings collapse onto one filter**: at a 5000 Hz
reference the settings 5.625°, 11.25° and 28.125° are literally the same measurement, and all three
deliver **29.5°** — a value that is not even on the control's own grid. So a tuner who dials one
small step gets five, and the UI tells them otherwise.

How many positions that costs is arithmetic from the ceiling and the 5.625° step, not a separate
measurement (`phase_rotation.lost_settings`):

| reference | positions lost to the ceiling |
|---|---|
| ≤ 1000 Hz | **0 — the documented grid works exactly** (one step measures −5.54° against 5.625, two steps −11.29° against 11.25) |
| 2000 Hz | 2 |
| 3000 Hz | 3 |
| 5000 Hz | 5 |
| 8000 Hz | 9 |

This is why `phase_rotation.realize()` returns the **delivered** angle beside the setting, and why
`predict` puts a note on the channel when the two differ: a report that echoes the setting is lying
to the tuner in exactly the region where the control stops behaving.

The ceiling was measured **only at 96 kHz** — three recoveries at two references gave 18007, 18009
and 18010 Hz, which is 3/16 of the rate to within the spread *and* an absolute 18 kHz to within the
same spread; one rate cannot separate them. The method takes the rate-relative reading, as
Resonalyze does (the corner is placed in the digital domain, and one coefficient generator serving
both device generations would most naturally clamp there). **If a 48 kHz unit is ever measured,
`phase_rotation.MAX_CORNER_FRACTION` is the one line to correct.** Whether the ceiling is deliberate
or a firmware defect is not established.

### 1.4 What it costs — and it is the bass, not the top

**It is not a polarity flip:** 180° here is 180° only at the reference — at 1 kHz the same setting
on a 5 kHz reference measures −23°.

**And it is not free.** Group delay, computed from the fitted filter (`phase_rotation.group_delay_us`),
is a **plateau below the corner, a peak at it, and a fall away above it**:

| setting | corner | 20–100 Hz | peak | 8 kHz |
|---|---|---|---|---|
| 180° at a 5000 Hz reference | 5000 Hz | 63 µs | 130 µs at the corner | 46 µs |
| 270° at a 5000 Hz reference | 3107 Hz | 102 µs | 213 µs near 3 kHz | 21 µs |
| 180° at a **500 Hz** reference | 500 Hz | **640–690 µs** | 1273 µs at the corner | 3 µs |

⚠️ **Corrected 2026-09-05.** This file used to say the all-pass "adds delay to everything ABOVE the
turn frequency". The measured shape is the other way round: the cost lands **below** the corner,
and it scales with how low the reference sits. The last row is the one to hand a tuner: a phase
turn on a channel crossed low costs most of a millisecond in the bass — about 22 cm of path — and
that lands squarely in the sub/midbass joint the control is usually being used to fix. A delay
change that crosses a turned joint is therefore a package with the phase setting, the same rule as
`diagnostic-techniques.md` §25 states for an APF.

### 1.5 The grid

5.625° steps (360/64), 0 … 354.375°; a full 360° is not offered. The step is **measured on a
subwoofer channel**; the mid/high block only ever captured the 180° setting, which sits on a 5.625°
grid and an 11.25° one alike, and older generations of the PC-Tool are reported to step mid and
high channels by 11.25°. So the step is measured for one channel type and assumed for the others
(`phase_control.step_note` in the DSP profile).

### 1.6 In the method's tools

* **`rew_tool/phase_rotation.py`** — `realize(deg, ref_hz, fs)` → `(corner_hz, delivered_deg)`;
  `capped_note`, `lost_settings`, `group_delay_us`, `snap_to_grid`; the CLI
  `python3 rew_tool/phase_rotation.py 180 500` prints what a setting builds and what it costs.
* **`predict.py`** models a ledger row's `phase_deg` as one APF2 at that corner, refuses only a row
  with no configured reference crossover (the angle is stated AT a crossover), and notes a capped
  setting with the angle the channel actually gets.
* **`knowledge/dsp/profiles/audiotec-fischer-helix-dsp-ultra-s.json`**, `phase_control` — the
  machine-readable half: roles, step, range, reference rule, ceiling fraction.
* An all-pass does **not** fill a magnitude null — it is flat in FR and rotates only the PHASE. A
  single-source dip at the listening position (a positional / path null) cannot be lifted by
  rotating phase; an all-pass is useful only to change how two overlapping sources SUM at a joint.
  A single-source null is moved only by physics (re-aiming the driver, treating the reflection).

## 2. Phase-alignment methodology (the practice)

* **Midbass is the anchor** — the channel you do NOT rotate. On this hardware a `low` channel has no
  Phase control at all (§1.2), so the practice and the hardware agree, for different reasons.
  * ⚠️ This anchor is the PHASE-tuning reference — it is **not** the arrival-TA reference. The
    arrival-TA reference is the **measured latest-arriving driver** (`process-phases.md` Phase 1),
    which is often NOT the midbass (it frequently arrives early). Two different "midbass =
    reference" roles — a real bug once pinned the midbass as the TA zero and delayed everyone else,
    when the midbass was the EARLY arriver that needed delaying.
* Rule: **of the 4 drivers you adjust only 3.**
* **Order:** from the midbass (the anchor) → first the **sub** (the sub↔midbass joint is the most
  important) → then the **mid** → then the **tweeter**.
* **How to set it:** with **RTA** on, watching the **overlap region at the joint**, rotate the
  channel's phase to **maximum summation** (the dip disappears) at the crossover frequency. Now
  that the law is known, `predict.py --align --apf` and the virtual-first path can find the turn at
  the desk first and the RTA confirms it.
* Phase problems most often sit in the **crossover region** and in the **midbass range**.
* **Mind the reference before you dial:** the angle is stated at the channel's *configured*
  crossover. A sub channel's reference is its LPF; a mid's is its HPF. Change that crossover and the
  same angle is a different filter (§1.1) — re-check the turn after any crossover change.
* **Mind the ceiling:** on a channel crossed above ~1 kHz, the first few positions do nothing the
  UI claims (§1.3). Read the delivered angle from `phase_rotation`, not from the screen.

### Practice for our system (Passat B8)

In the first successful configuration (AYA) the phase control is set: sub `174.375°`, left mid
`33°`, the rest `0°`; the midbasses — no rotation (the anchor). See `autosound_context.md` §4A.
Note that `33°` is not on the 5.625° grid (the nearest positions are 28.125° and 33.75°) — a
transcription to check against the PC-Tool screen (`screen-read-dsp.md`).

## 3. Explicit AP1/AP2 bands in the EQ bank — hardware-verified

Besides the auto Phase control above, the PEQ bank accepts explicit **AP1/AP2 bands at an arbitrary
f0/Q** (several allowed; `helix-eq-export.md`). These are a different control: the user types the
corner, and the corner does not move with the crossover.

* **AP2 is the RBJ second-order all-pass, as a bilinear-transformed DIGITAL biquad at the
  processor's rate** — `dsp_math.apf2_response`. First established 2026-07 on a tweeter channel by
  the same-session single-variable A/B protocol (sweep → change ONLY the APF, mic untouched → sweep;
  the complex ratio isolates the filter): the free fit recovered f0 4386 / Q 3.82 against 4414 /
  Q 4.0 entered, with 31° RMS residual over an in-cabin acoustic path. Re-measured **electrically**
  2026-09-01 (fact 1): a free fit recovers what was entered to **0.05 % in f0 and 0.3 % in Q**; the
  analogue formula `−2·atan2((f/f0)/Q, 1−(f/f0)²)` is 1.5° rms off at 4 kHz and **3.6° rms / 9.5°
  max at 8 kHz** — the digital form fits to 0.1–0.3° rms. (The 31° of 2026-07 was the cabin, not
  the filter.) An allpass-only change must ratio to **0 dB magnitude** — the protocol's built-in
  sanity check; 0.04 dB was the worst seen.
* ⚠️ **AP1's corner sits LOW, and the error grows with frequency** (fact 1, 2026-09-02): typed 250 →
  248.8 Hz (−0.5 %), 1000 → 993.2 (−0.7 %), 4000 → 3936 (−1.6 %), **8000 → 7611.6 (−4.9 %)**, while
  every AP2 corner in the same session landed within 0.05 %. The shape stays a clean first-order
  all-pass, so it is the frequency that is wrong, not the form; no simple law fits (not a constant
  percentage, not an offset, not the un-prewarped substitution, which would put 8 kHz at 7824).
  `dsp_math.apf1_response` models the TYPED corner, which costs 0.4° at 1 kHz, 0.9° at 4 kHz and
  **3.0° at 8 kHz** — where a tweeter all-pass lives. **Prefer AP2 in prescriptions**; where AP1 is
  used, carry the deviation as a known unmodelled error in the ledger.
* ⚠️ **Identifiability is set by the band TOGETHER with the Q, not by Q alone.** After removing the
  best-fit delay and offset, an 8 kHz Q 0.7 section leaves 42.1° rms over 1–20 kHz but only **0.8°
  over 2–8 kHz** — degenerate with delay + offset on a tweeter's band — while Q 4 still leaves 17.1°
  there. So "verify with a HIGH-Q setting" is the right instinct, and it needs the band named next
  to the Q: a clean fit over a narrow band is not a confirmation (`diagnostic-techniques.md` §35).
* **Rotation reach scales as ~f0/Q:** a Q4 APF at 4.4 kHz barely rotates at 3.2 kHz. Check the
  APF's phase AT THE JOINT frequency, not at f0 (`diagnostic-techniques.md` §25).
* Joint-repair APF choices must be **jitter-robust**, not razor-optimal (`diagnostic-techniques.md`
  §24).
* **REW mirroring:** the Generic Extended equaliser has "All pass" (freq+Q = AP2) but **no
  1st-order all-pass** — an AP1 band in the Helix cannot be mirrored in the REW panels
  (`rew-api-quirks.md`). One more reason to prefer AP2; if AP1 is ever used, record the mirroring
  gap in the ledger.

## Sources

* The bench: `ayukhno/autosound-measurements`, `hardware/helix/dsp-ultra-s/FACTS.md` (facts 1 and
  6), `bench3-manifest.json`, `phase-turns-manifest.json`, `measurements/README.md` (every defect in
  the data is documented there, in place) — CC BY 4.0.
* The upstream implementation: `DIMOSUS/Resonalyze`, `dsp/PhaseRotationControl.cs` at `bc957c8`,
  MIT; the reading and the author's response in DIMOSUS/Resonalyze#88.
* Audiotec-Fischer's knowledge base (*Phase and time alignment*): the 5.625° grid, the 0–354.375°
  range and the reference rule, in prose; nothing about a ceiling.
* The practice (§2): DIYMobileAudio — "Using the phase adjustment in Helix DSP"; "Helix DSP phase
  VS delay adjustment"; "Let's Phac our Helix DSP — how to set Phase degree/AllPass"; PASMAG's Helix
  P-DSP review; the order (midbass→sub→mid→tweeter) from the user, consistent with forum practice.
