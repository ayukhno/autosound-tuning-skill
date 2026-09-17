# Phase 1 variants on Resonalyze's engines — design (issue #38)

**Status:** agreed with the user in conversation on 2026-09-17; nothing built yet. The decisions are the user's; where
this file says "recommended", it is the session's advice the user accepted or left open (§5).

## 1. The process

1. **Intake** (Phase −1).
2. **Capture** (Phase 0): one impulse per driver from the tripod (loopback, REW sweep *Repetitions 4*), centre and rear
   channels too when the car has them; RTA/MMM feeds EQ only. The capture sheet already asks for this, and it is what
   Resonalyze's engines take (`MANUAL.md:275-297`, `:203-204`, `:308-309`).
3. **The tuner's crossover wishes in free words** — e.g. "BE4 between tweeter and mid, BW2 between sub and midbass,
   not sure between midbass and mid". That is enough; no form.
4. **The best mathematical configuration first**, without the wishes.
5. **A second pass with the wishes**, so each shows what it costs against the best.
6. **A wish that breaks a hard limit is not computed;** the tuner is told the nearest allowed setting ("BW2 on your
   tweeter from 3400 Hz").
7. **Coarse EQ per driver toward its own target** — broad cuts of position-stable features, minimum-phase, never a boost
   into a dip (as `eq_propose` does) — BEFORE the delays, because a PEQ changes phase (Resonalyze's order, `MANUAL.md:782`).
8. **Delays and levels** on the virtual DSP with that EQ in the chains: front and sub first, then centre and rear placed
   against the settled front (Resonalyze's staging, `MANUAL.md:1015-1028`; centre read against both sides at 1–4 kHz).
9. **Scene centring, its own step on the chosen variant, after the coarse EQ and the delays:** arrival aligned, against a time offset plus a near-side cut
   (Resonalyze's *Offset*, default 0.25 ms — "the factory default, not tuned for a cabin" — and *Near side cut*). The
   virtual DSP shows both; the ear decides (two presets, A/B). The user's own trial on Resonalyze's data: the two
   differed by small changes of gain and delay.
10. **What is shown:** one mathematical variant and up to two built from the tuner's wishes; a fully automatic run keeps
    at most three. More only if the tuner wants to dig, and then the Resonalyze app itself is the better place.
11. **The breakdown in words** — what changes and how it will sound — written by the generator and reviewed by the
    critic; the predicted sums can go into the target-curve visualizer beside the target (1/6 or psychoacoustic
    smoothing); listening is offered, not required. **The tuner chooses.**
12. **Entered into the DSP only with the tuner's OK.** Phase 3's control measurement is compared with the prediction;
    a deviation the tuner accepts (the body, and whatever else) is recorded as accepted, not as a failure.
13. **Free play:** the tuner changes settings as they like; where the virtual DSP can compute it, the AI compares it with
    the chosen variant — or the tuner decides alone.

That is Phase 1.

**Phase 2 — the second part of EQ:** L/R pairs per band → the band junctions of each side → sub with mids → each side
whole → everything together → centre under everything → rear under everything. A step whose EQ touched a junction's
band re-checks that junction's delay; otherwise the delays stay.

## 2. Rules it rests on

- **The desk proposes, the Arbiter decides** — the virtual-DSP desk spec's requirement 8 (2026-09-05) as the user put it
  on 2026-09-17: nothing into the DSP or the ledger without the Arbiter's OK, no EQ into a cancellation, no improvement
  claimed without a measurement after (`references/phases/virtual-first.md`).
- **Hard limits are never traded:** the protective floor (HPF ≥ 1.1 × Fs, ≥ 24 dB/oct, `gates/presweep_safety.py`) and the
  device's limits from its profile. An optimiser once "won" by using a de-embedded protective filter to pick an unsafe
  tweeter slope (research's Optuna pilot, `research/wiki/experiments/complex-vector-sum-crossover-optimization-pilot.md`).
- **Cost is described and drawn, not hidden behind a threshold.** Resonalyze's margins — a challenger must beat the
  all-24 dB/oct baseline by 0.25 dB (`dsp/CrossoverAutoSetup.cs:93-106`), a kept junction by 0.5 dB
  (`dsp/CrossoverJunctionTuner.cs:242-248`) — are a reference, not a cut-off.

## 3. The engine

- **What it is.** `Resonalyze.Dsp` (`dsp/Resonalyze.Dsp.csproj`): a `net10.0` class library, MIT, depending on
  MathNet.Numerics and YamlDotNet, with no Windows API in it. Auto crossover (`CrossoverAutoSetup`) and Auto delay
  (`AutoAlignmentEngine`) live there. There is no headless entry point: the Agent Bridge is a clipboard protocol
  (`docs/agent/PROTOCOL.md`).
- **Call it, don't rewrite it** (the user): new features and processors then arrive almost by themselves, through a
  review.
- **Where the code lives** (the user): in the skill's tree — `Resonalyze.Dsp` as a submodule pinned to a commit of our
  fork, and a thin C# console wrapper: JSON in (impulses, channel layout with zones, wishes, limits), JSON out (variants
  with their numbers). .NET in the skill's CI; installs get a prebuilt self-contained binary per platform.
- **Updates:** move the pin, rebuild, review the diff and the outputs on the reference data (`scripts/upstream-drift.py`
  already tracks the fork). The author changes this maths often — `dsp/` took 40 commits in the month to 2026-09-17, and
  Auto delay four in one day on 2026-09-05 — so the pin is what keeps a tune reproducible.
- **Check first, on a prototype:** coherence (Resonalyze computes it from its own repeated sweeps, REW does not export
  it); distortion curves; whether the engines give the same answer for the same input.
- **This changes the decision of 2026-09-08** (`research/experiments/designs/virtual-dsp-decision-2026-09-08.md` §4):
  Resonalyze was kept as an oracle, a source of definitions and "eyes"; it now also computes Phase 1's variants.
  `predict` stays the virtual DSP for prediction and verification.

## 4. Asked of the Resonalyze fork session

- **An integration brief:** the `Resonalyze.Dsp` types and calls the wrapper needs for Auto crossover and Auto delay;
  how their inputs are built from impulse responses (`AutoSetupSource`, `AlignmentSnapshot`); units, defaults and
  optional fields; zones for centre and rear; the Offset, Near-side-cut and gain-balance parameters; determinism.
- **A minimal reference call** (in the fork, not in the skill's tree) and **golden outputs**: the Passat's solos run
  through the Resonalyze app, and the settings it proposes, as the wrapper's acceptance test.
- **Nothing to the upstream author or the upstream repository.**

## 5. Open

- ~~The .NET 10 SDK on the development Mac~~ — settled 2026-09-17: the user-level SDK the fork already builds with,
  `~/.dotnet` (10.0.301, the version the fork's `global.json` pins). The wrapper's build script takes `dotnet` from
  PATH and falls back to `~/.dotnet/dotnet`; nothing is installed or changed system-wide (the user's choice).
- How installs get the binary.
- SQ practice for centring the scene by time or by level, with sources: asked of research, hub #158 (SKL-040).
- Analysing a tune that already exists: noted, not started (`docs/TODO.md` S-017).

## 6. Work plan (skill side)

Engine-independent steps first, on `wave-2026-09-17b`; each with its selftest, the full suite once at the end.

1. ~~**Wishes against hard limits.**~~ Done 2026-09-17: `rew_tool/xover_wishes.py` reads the tuner's free-form wishes per
   junction (family, slope, frequency, "not sure"), checks each against the device profile and the fragile driver's Fs
   floor (`crossover_checks.fs_margin`: REFUSE under 1.1 × Fs, CAUTION up to the craft convention, which relaxes with the
   slope), and names the nearest allowed setting ("→ enter BW2 from 1044 Hz"). Phase 1 §3, the capabilities board and
   `rew-tool-docs.md` say so.
2. ~~**The phase documents.**~~ Done 2026-09-17: `virtual-first.md` 1.2–1.7 and 2.1 carry the §1 order (wishes → variants,
   best first → coarse per-driver EQ → joints with it in the chains, front and sub first → levels and centring → the sums,
   the description, the choice); `phase_1_foundation.md` (§5.5 coarse EQ before the delays, the gate), `phase_2_eq.md`
   (2a–2d in the new order), SKILL.md's map and the FAQ's roadmap say the same. Where a step names the engine, it says
   the engine is not built yet (§3).
3. **`eq_propose` in two parts:** Phase 1's coarse per-driver package; Phase 2's sequence (L/R pairs per band → junctions
   per side → sub with mids → sides → everything → centre → rear), with the junction re-check when a step touches a
   junction's band.
4. **Predicted sums for the target-curve visualizer**, smoothed 1/6 or psychoacoustically, beside the target.
5. **The engine wrapper** — after the fork's integration brief and golden outputs (§4): `Resonalyze.Dsp` as a pinned
   submodule, the C# console wrapper and its JSON contract, the Python caller, the acceptance test on the Passat's data,
   `setup-dotnet` in CI, and per-platform binaries for installs.
