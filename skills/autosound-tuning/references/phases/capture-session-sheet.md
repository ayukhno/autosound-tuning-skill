# Capture-session sheet & session passport (virtual-first Phase 0)

> 🧩 The two paper artefacts of a [`virtual-first`](virtual-first.md) capture: the **sheet** you take
> into the car so nothing is decided there, and the **passport** that records the session's settings so
> a later session can read what was done — not reproduce it byte for byte, but understand it. Both are
> filled at the desk (−1.4) except the numbers only the car gives.

## Preparing the session (−1.4, the day before)

1. **Back up the current tune** to a file (the DSP slot is left alone — the car stays drivable, and it
   is the "before" for A/B in Phase 4).
2. **The `v0` preset**: every channel with the protective filters from −1.3 only, gains level, delays 0,
   polarity normal, EQ empty, effects and dynamic processing **off** (the vendor's names for those:
   `dsp_profile.py effects <profile.json>`; it exits 3 if this DSP has none recorded) → into the
   ledger as version 0
   (at the desk if PC-Tool allows it without the DSP, otherwise the first thing in 0.1). `v0` stays in
   its own permanent slot — near-field can be captured on it any time later.
3. **REW** — Measure → Sweep: Length **512k**, **Repetitions 4** (not "Sequential measurements"),
   Timing = **loopback**, offset 0, Mode = **Single measurement**; one sample rate for the whole
   session. RTA: **1/48**, No smoothing, FFT **64k** @48k (**128k** @96k), Averages **Forever**, window
   **Hann**; **Stop at** set by the *time of movement* (~20–30 s): t ≈ N·(FFT/fs)·(1−overlap) — at
   48k/64k/87.5 % that is 0.17 s per average, so 150 = 26 s, 100 = 17 s. On 96k take FFT 128k or more
   averages to keep the same dwell.
4. **The capture sheet** from the glossary (`naming.py <project> codes`), in the 0.2 → 0.5 order below.
5. **A blank passport** (below).
6. **The bag**: microphone, tripod, interface, loopback cables, tape measure, laptop + charger, ear
   plugs, a power bank if the sound card or laptop needs one.

## The capture sheet

Order of channels is the user's in TCC; the sheet only fixes the blocks and the controls. `<ch>` runs
over the project's glossary — `sw` (or `sw-f`, `sw-r`), `w-L/R`, `m-L/R`, `tw-L/R`, and `c`, `r-L/R`
where they exist.

```
BLOCK A · SESSION LEVELS (handheld, ~5 min, nothing saved)     [0.2]
  loudest driver (usually the sub): sweep → peak −5…−10 dBFS, knobs fixed
  quietest driver: sweep → above the cabin noise (capture-check sees it)
  one REW output level for ALL sweeps · one HU/Conductor level for ALL RTA
  → both numbers to the passport; the SAME numbers in Phase 3

BLOCK B · HANDHELD (before the tripod)                          [0.3]
  RTA:        <ch>_01 (rta)  for every channel        (~20–30 s of movement)
  ellipsoid:  <ch> p1…p9_01 (sw)  for w-L w-R m-L m-R (+ any channel with an
              EQ decision in 0.2–2 kHz)
  (near-field optional here or any time later on the v0 slot)

BLOCK C · TRIPOD P0                                             [0.4]
  place the tripod; tape (a) return set: capsule → windscreen, door glass,
    roof + seat-rail mark; tape (b) desk set: capsule → each driver centre
  timing = loopback
  drift pair:  m-L (sw) ×2 in a row → < 0.1 sample   (not saved)

BLOCK D · TRIPOD BLOCK (tripod does NOT move until Phase 3)     [0.5]
  m-L-ctl1_01 (sw)          (a CONTROL: opens the series; `m-L_01ctl (sw)` as typed in the car reads the same)
  <ch>_01 (sw)  for sw (or SWs_01 (sw) for two subs) · w-L · w-R · m-L · m-R
                · tw-L · tw-R · c · r-L · r-R
  m-L-ctl3_01 (sw)          (closes it; `m-L_01rep (sw)` reads the same)
  doors shut · an even tempo · do not air the cabin

BLOCK E · CHECK ON THE SPOT (laptop in the car)                [0.6]
  capture-check every measurement: present / usable — IR peak above the
    pre-ringing (a "broken" impulse fails), not a flat curve, not in the noise
  ctl1 vs ctl3 → the drift record
  re-take whatever failed NOW, while the tripod stands

BLOCK F · CLOSE                                                 [0.7]
  capture-protective — mark the protectives on the round
  save the .mdat into the project · finish the passport
  tripod untouched → the desk

APPENDIX · IMPEDANCE (a separate rig, another day)  — optional, not on the path
  what for: driver Fs in its box → protective ≥ 1.1·Fs; reveals a broken
  driver or wiring. Without a rig: Fs from the datasheet with margin, and say so.
```

Minimum viable set = **Block A + D** (~25 min). Cutting for time, drop from the bottom by block; the
tripod block (D) is the one that is mandatory.

## The session passport

Not a gate — the one-session rule (`diagnostic-techniques.md`) is what makes a set comparable; the
passport is the extra context that helps if a measurement ever has to be understood or approximately
reproduced. Fill what you can; a blank line is fine.

```
SESSION PASSPORT — <project> — <date>

Levels (the whole playback chain, because "by the indicator lights" is not exact):
  sweep:  REW output …  ·  interface out …  ·  Conductor …  ·  mic gain (interface) …
  RTA:    head-unit volume (if it affects) …  ·  Conductor …  ·  mic gain …
  sub knob position …

Geometry:
  seat rail mark …
  tripod P0 — tape (a): windscreen …  door glass …  roof …
  tape (b) capsule → driver centres:  tw-L …  tw-R …  m-L …  m-R …  w-L …  w-R …  sub …

Environment:
  cabin noise floor …  ·  temperature (by eye, optional) …
  effects/dynamic processing OFF: <list from the DSP profile> …
```

Why the whole chain, not one number: a measurement is unlikely to be reproduced to 100 % — that is
exactly why the one-session identity rule exists, and why these are *context, not a gate*. Seat and
microphone position can shift; the passport is what lets a later session tell whether a difference is
the tune or the setup.
