# Capture-session sheet & session passport (virtual-first Phase 0)

> 🧩 The two paper artefacts of a [`virtual-first`](virtual-first.md) capture: the **sheet** you take
> into the car so nothing is decided there, and the **passport** that records the session's settings so
> a later session can read what was done — not reproduce it byte for byte, but understand it. Both are
> filled at the desk (−1.4) except the numbers only the car gives.

## Preparing the session (−1.4, the day before)

1. **Back up the current tune** to a file (the DSP slot is left alone — the car stays drivable, and it
   is the "before" for A/B in Phase 4).
2. **The `v0` preset, the raw state**: every channel with the protective filters from −1.3 only, gains level, delays 0,
   polarity normal, EQ empty, **every enhancer, filter and EQ off (the protective filters stay on), equal levels in the DSP**,
   and preferably the amplifier gains already set (the method does not do that part; say so, any AI can advise how). The vendor's
   names for what to switch off: `dsp_profile.py effects <profile.json>` (it exits 3 if this DSP has none recorded). On an
   Audiotec Fischer DSP that list, from its profile, is RealCenter, DynamicBass, SubXpander, ActiveToneControl,
   RemoteToneControl, SubRC and RearRC, and the input levels are set equal too. On another DSP: every enhancer, loudness or
   bass tool and dynamic block off, the input levels equal, as far as its screens show them. A save that can be read back
   is checked against this list; otherwise the screen is. → into the ledger as version 0
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

**The series number is the PROJECT's, never an example's** (#56 item 10, #57 P4): `naming.py <project>
next-series` prints it (`1` for a new project, the number after its highest for any other). A sheet that
said `_2` from these examples, on a project at `_49`, brought 47 measurements back under the wrong number.
The tripod block and the hand-held block of one visit are ONE series unless the DSP changes between them, and
all the tripod sweeps are one block, the RTA with the nine points the other, either first. The questions the tools will ask later go on the page and are
answered in the car: the level as a quantity (`capture-start … --level "-25 dB rel. max"`), the knobs
(`capture-knobs`), and what protective filter was in the chain (`capture-protective`).

**A request to measure IS a round, never words** (SKILL.md's guardrail; the round's mechanics are here). **One recipe opens it**, [`capture-session-sheet.md`](references/phases/capture-session-sheet.md) Block 0 — the phase entered first, N from `naming.py next-series`, then `capture-start <N> --plan [title…]`, a capture the phase file names and the plan does not give typed on the same line (Phase 3's tripod sweeps); Phase 3's `_final` set is the one round `--plan` cannot build, `_final` being no series number (`phase_3_control.md` §1) — and the round `cap_NNN` carries its list from the method's plan for the phase, the channels the project has on, ordered by setup (the setup the car is in first, each switch named — skill #78), in five columns at most (Solo/Group × sw/rta — skill #79 — and Points (sw) for the hand-held `p1`…`p9`, #198); **what it prints is the message to the Arbiter** — nothing is asked for in prose only, and "if you have time" captures go on the list as `--optional` (skill #80), never in the sentence. A capture the list should not have: `capture-skip <title> <reason>`. `capture-taken <title>` as each comes back. **`capture-close` closes against REW, whatever captured**: held → taken, taken beyond the list → recorded, absent → left open (yellow), the checks run on what was taken; `--no-rew` says on the record that it was not checked.

```
BLOCK 0 · OPEN THE ROUND (laptop, ~1 min)                      [0.0]
  process.py <project>/process enter-phase 0
                                        → first: the round is stamped Phase 0, and --plan reads it
  naming.py <project> next-series       → N, this project's own (1 on a new one)
  process.py <project>/process capture-start <N> --plan "<ch> p1_<N> (sw)" … [--level "<dB rel. max>"]
                                        → the titles this session owes, from the method's plan;
                                          what it prints is the message to the Arbiter.
                                          The plan does not list the nine points: their titles
                                          are typed on this same line (block B's channels, p1…p9)
  without it blocks E and F have nothing to write on: capture-taken,
    -protective, -knobs and -check all refuse while no round is open

BLOCK A · SESSION LEVELS (handheld, ~5 min, nothing saved)     [0.2]
  loudest driver (usually the sub): sweep → the INPUT peak −5…−10 dBFS (REW's input meter);
    the output level is a separate number · knobs fixed
  quietest driver: sweep → above the cabin noise (capture-check sees it)
  one REW output level for ALL sweeps · one HU/Conductor level for ALL RTA
  → both numbers to the passport; the SAME numbers in Phase 3

  timing = loopback, from here on, for every sweep that is saved:
    `predict.load_solo_rew` refuses a sweep off the loopback base, the hand-held ones too

BLOCK B · HANDHELD, ONE BLOCK: THE RTA AND THE NINE POINTS      [0.3]
  (the tripod sweeps, blocks C–D, are the other block; either may go first. If the
   tripod went first, it comes out for this block and tape set (a) brings it back)
  RTA:          <ch>_N (rta)  for every channel       (~20–30 s of movement)
  nine points:  <ch> p1…p9_N (sw)  for w-L w-R m-L m-R tw-L tw-R c (every front driver and the centre, the default)
                on a 3-way + centre that is 63 sweeps. The sub stays at one point while
                its crossing is under 100 Hz (a front sub included); above that it needs them too
  (near-field optional here or any time later on the v0 slot)

      the nine sweeps of one driver: a fixed hand-held path, in a vertical plane
      in front of the nose, parallel to the windscreen (seen from the seat):

             p3 ·                               · p7      a step above the side point
                |                               |
      left   p2 · ──step── p1 · p5 · p9 ──step── · p6   right     p1/p5/p9 = the centre, in front
                |                               |                 of the nose: the tripod point
             p4 ·                               · p8      a step below the side point

      p1 centre → p2 left → p3 up → p4 down → p5 back to the nose → p6 right → p7 up →
      p8 down → p9 back to the nose. Each step is 10–15 cm; each "down" is twice that,
      so it ends a step below the side point. Keep them alike between sets, they
      cannot be exact; what is read from them is relative.

      p1/p5/p9 are not three positions: they are ONE position returned to at the
      start, the middle and the end. Their spread is the drift of the set (over
      1 dB = not one set). The six around it are what shows which features STAY (the
      driver, the cabin) and which MOVE (that spot). p2–p4 are the left side, p6–p8 the
      right, p1/p5/p9 the centre: the ear groups of the joints above 1 kHz follow from
      this order (`joint_search`), and the arrival rule checks it.

BLOCK C · TRIPOD P0                                             [0.4]
  place the tripod; tape (a) return set: capsule → windscreen, door glass,
    roof + seat-rail mark; tape (b) desk set: capsule → each driver centre
  drift pair:  m-L (sw) ×2 in a row → < 0.1 sample   (not saved)

BLOCK D · TRIPOD BLOCK (tripod does NOT move until Phase 3)     [0.5]
  m-L-ctl1_N (sw)           (a CONTROL: opens the series; `m-L_Nctl (sw)` as typed in the car reads the same)
  <ch>_N (sw)  for sw (or SWs_N (sw) for two subs) · w-L · w-R · m-L · m-R
               · tw-L · tw-R · c · r-L · r-R
  m-L-ctl3_N (sw)           (closes it; `m-L_Nrep (sw)` reads the same)
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

BLOCK X · AS IS — only for a car that is already tuned          [0.7b]
  (virtual-first.md, "Two ways in"; goal.mode improve_existing)
  the tripod still at P0 · the same levels as block A
  close the raw round; DSP → the slot holding the CURRENT tune (never edited:
    v0 lives in its own slot), the version setup_import banked at −1
  naming.py <project> next-series → M
  process.py <project>/process capture-start <M> --under <current version> "<title>" ...
  <ch>_M (sw) for every channel, through its current chain
  L_M (sw) · R_M (sw) · ALL_M (sw)
  capture-check as in block E · close the round · save the .mdat again
  the car leaves the session on its own tune

APPENDIX · IMPEDANCE (a separate rig, another day)  — optional, not on the path
  what for: driver Fs in its box → protective ≥ 1.1·Fs; reveals a broken
  driver or wiring. Without a rig: Fs from the datasheet with margin, and say so.
```

**One full raw capture for every project, whichever way the desk goes** (the Arbiter, 2026-11-08: «знімати все що потрібно щоб мати
сиру машину для всіх варіацій проекта далі»): blocks A, B with the nine points, C and D, plus **block X** on a car that is already tuned
(~10 min). On a 3-way + centre that is 63 point sweeps against the 36 this sheet used to ask for. Until 2026-11-08 the nine points
were the one optional part; they are now the default.

**They can still be cut for time, and that is the person's call, informed.** Before the capture the session says the limits in
words: the Resonalyze engine loses nothing (it reads the tripod solos); the joints run only with `joint_search.py --single-point`, on
the centre point, every row marked, with no margin over the head's positions and no left/right ear groups; the EQ has no
stay-or-move reading of its own. If the person still says no, the decision is recorded so the joints accept it, in these words:

```
python3 rew_tool/state/process.py <project>/process decision "ellipsoid positions: nine points skipped; the joints run on one point" "agreed: <the person's words>"
```

The exact phrase is the one `joint_search.py --single-point` asks for, and it refuses without it; an answer that opens with a bare no reads as no decision, so the
answer opens with «agreed». The RTA and the tripod block (D) are mandatory either way: minimum viable set = **Block A, the RTA of block B, and D** (~30 min).

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
