# Phase 1 variants on Resonalyze's engines — design (issue #38)

**Status:** agreed with the user in conversation on 2026-09-17. The engine-independent steps are built (§6, 1–4); the
engine wrapper is being built on the Resonalyze fork session's answer (PAS-008, hub #159). The decisions are the user's;
where this file says "recommended", it is the session's advice the user accepted or left open (§5).

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
9. **Scene centring: Phase 1 builds the BASE by level, and the ear decides in Phase 2** (research's answer, RES-011 /
   hub #161, on the user's plan of 2026-09-17). The base: the arrivals aligned to the seat (scene offset 0) and the
   near-side pull as channel gain (Resonalyze's gain balance, "levels only"; the Passat's is 2 / 4 / 4 dB on midbass /
   mid / tweeter). No choice is asked here. The second preset — the same pull by time: the near side later by
   0.15–0.30 ms with its cut reduced 16 dB per ms, loudness matched — is built from the base after Phase 2's "each side
   whole" and compared by ear before "everything together" (`rew_tool/scene_presets.py`; `phase_2_eq.md` 2c). Lee 2010:
   0.25 ms ≈ 4 dB ≈ a third of the half-stage, so the two differ in mechanism, not in where the centre lands; the
   user's trial on Resonalyze's data (the author's two presets, Δf +8 %) said the same.
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

The fork session's integration brief answers this section (PAS-008, hub #159; the brief and the goldens sit in the
fork's untracked `scratchpad/phase1-engines/`, read at fork `b0ce9fb`).

- **What it is.** `Resonalyze.Dsp` (`dsp/Resonalyze.Dsp.csproj`): a `net10.0` class library, MIT, depending on
  MathNet.Numerics and YamlDotNet, with no Windows API in it. Auto crossover (`CrossoverAutoSetup`) and Auto delay
  (`AutoAlignmentEngine`) live there. There is no headless entry point: the Agent Bridge is a clipboard protocol
  (`docs/agent/PROTOCOL.md`).
- **The engines alone are not the window's answer** (the brief, §0). How the window reads the magnitude, groups and
  orders the channels, plans the stereo run, places the centre and the rear and normalises the delays lives in
  `source/Tools/VirtualCrossover/`. Eight of those files compile unchanged into a console; about 600 lines sit inside
  WinForms classes and are **copied**, each method naming its origin (`engines/resonalyze/WindowReplica.cs`). Copying,
  not rewriting: nothing in `dsp/` is copied, and the maths is called.
- **Call it, don't rewrite it** (the user): new features and processors then arrive almost by themselves, through a
  review.
- **Where the code lives** (the user): in the skill's tree. The whole fork is the submodule — a submodule is one
  repository anyway — at `vendor/Resonalyze`, pinned to `b0ce9fb`, with `update = none` so a recursive clone of the skill
  (TCC's, a developer's) does not fetch it; the engine's build asks for it. The thin C# console wrapper is
  `engines/resonalyze/`: JSON in (the impulse files, the blocks with zones and driver types, the protective filters, the
  device's rate and delay range, the Auto delay request), JSON out (the proposals, the delays with each decision and its
  confidence). .NET in the skill's CI; installs get a prebuilt self-contained binary per platform (§5).
- **What the wrapper's caller must supply** — each of these changes the result on the Passat (the brief, §1 and §4):
  - **driver types from the channel map, never the engine's suggestion** (`EstimateBand`): the suggestion read the mid
    as a midbass and the centre as a tweeter, which put the centre's high-pass at 2300 Hz on the tweeter's Fs floor;
    with the right types the woofer/mid junction moves 500 → 200 Hz and the centre 2300 → 1050 Hz, and every delay
    moves;
  - **the protective high-pass divided out of the impulse before the engines**
    (`ProtectiveHighPassCompensation.RemoveFromImpulseResponse`, as Resonalyze's own capture does). The skill's
    converter leaves it in on purpose (`rew_tool/resonalyze_ir.py`). Left in, `ir-v7_49` carries two filters where the
    car will have one: the polarity of all four mids and tweeters flips and their delays move ~0.3 ms;
  - **no distortion curve for REW-converted files**: the harmonic positions in REW's buffer are a guess; on the Passat
    removing it changed nothing;
  - **the delay range from the project's device profile.** Resonalyze's catalog has no range for the HELIX DSP ULTRA S
    and falls back to the engine default, 50 ms. The Helix holds 20.82 ms on a driver output and 20.82 ms on a virtual
    channel, and the two add (the user's PC-Tool reading, `dsp_profile.json`; "they can be summed, on the rear for
    sure", 2026-09-17): an output fed by a virtual channel reaches 41.64 ms, split free only where that virtual channel
    feeds it alone. The window-default golden's rear at 23.67 ms fits as 20.82 + 2.85. The fork has the facts for its
    catalog (a note handed over on the user's word, 2026-09-17).
- **The tuner's wishes go through the junction tuner, not the wizard.** `ProposeRanked` takes only global families and a
  global corner window. `CrossoverJunctionTuner.Probe` reads any variants of one junction, each after its own best delay —
  "what the wish costs against the best", directly; `Tune` searches one junction under families, slopes and a corner
  window at the current delays, so it belongs after Auto delay.
- **Hard limits are the skill's, checked on the engine's output.** The engine enforces its own floors (a tweeter
  high-pass at ≥ Fs·2^(22/slope), slopes ≥ 12 dB/oct, group delay ≤ 10 ms, 0.5 octave between junctions); it does not
  know the skill's Fs floor or the device profile. Every proposal goes through `xover_wishes`' check, which refuses or
  names the nearest allowed setting.
- **Updates:** move the pin, rebuild, review the diff and the outputs on the reference data. `scripts/upstream-drift.py`
  watches the copied window code (`VirtualCrossoverPanel.cs`, `VirtualCrossoverAutoSetupDialog.cs`), the eight compiled
  files and the engines' files, not only `dsp/`. The author changes this maths often — `dsp/` took 40 commits in the month
  to 2026-09-17, Auto delay four in one day on 2026-09-05, and two more Auto delay changes landed the week of the pin —
  so the pin is what keeps a tune reproducible.
- **Determinism** (the brief, §3): no random numbers, clocks or time budgets; three runs on one machine, one of them on a
  single core, give byte-identical JSON. Across operating systems it is not measured, so goldens are compared with a
  tolerance: kinds, families, slopes, corners and polarity identical; delays ±0.01 ms; gains ±0.1 dB.
- **Still to check on data:** coherence (Resonalyze computes it from its own repeated sweeps; REW does not export it);
  the junction tuner and probe; the single-side path, right-hand drive, PEQ in the chains.
- **This changes the decision of 2026-09-08** (`research/experiments/designs/virtual-dsp-decision-2026-09-08.md` §4):
  Resonalyze was kept as an oracle, a source of definitions and "eyes"; it now also computes Phase 1's variants.
  `predict` stays the virtual DSP for prediction and verification.

## 4. Asked of the Resonalyze fork session — answered

Answered 2026-09-17 by PAS-008 (hub #159): the integration brief, the reference call and goldens on the Passat's
`ir-v7_49` solos, run headless through the engines and a copy of the window's code. Nothing went to the upstream author or
the upstream repository.

- **An integration brief:** the `Resonalyze.Dsp` types and calls the wrapper needs for Auto crossover and Auto delay;
  how their inputs are built from impulse responses (`AutoSetupSource`, `AlignmentSnapshot`); units, defaults and
  optional fields; zones for centre and rear; the Offset, Near-side-cut and gain-balance parameters; determinism.
- **A minimal reference call** (in the fork, not in the skill's tree) and **golden outputs**: the Passat's solos, and the
  settings the window's defaults propose, as the wrapper's acceptance test. The goldens are headless until the user
  confirms them in the window on Windows (the brief, §6).
- **Nothing to the upstream author or the upstream repository.**

## 5. Open

- ~~The .NET 10 SDK on the development Mac~~ — settled 2026-09-17: the user-level SDK the fork already builds with,
  `~/.dotnet` (10.0.301, the version the fork's `global.json` pins). The wrapper's build script takes `dotnet` from
  PATH and falls back to `~/.dotnet/dotnet`; nothing is installed or changed system-wide (the user's choice).
- ~~How installs get the binary~~ — decided 2026-09-17 (the user): CI builds one self-contained executable per platform
  and the release carries them, so a user needs no .NET. The skill's half is built (§6, 5c); attaching them to a release
  is the hub's release role (`gh release` is that role's, hub `RELEASE-CHANNEL.md`), and so is whether the installers
  fetch one.
- The window confirmation of the goldens — the user's step on Windows (the brief, §6): open the session, Auto crossover →
  Apply, Auto delay → Run → Apply, export. Until then the acceptance test compares the wrapper with a copy of the
  window's code, not with the window.
- The centre and the rear come out at Low confidence on the Passat (rear r = 0.08 / 0.16, one centre reading on the
  refinement edge): numbers to show with their confidence, not to enter blind.
- ~~SQ practice for centring the scene by time or by level~~ — answered by research (hub #158 → RFC RES-011, #161,
  `research/docs/SKL-040-scene-centring.md`): the base by level, the time preset of the same pull, the ear in Phase 2;
  built as `rew_tool/scene_presets.py` and the cheat-sheet's protocol (§6, 6). One question back to research: piece 4's
  "|Δf| < 10 % → probably inaudible, no choice" cannot apply to the ladder, whose presets have the base's pull by
  construction — there the ear compares the mechanism; the module says so instead of refusing the choice.
- Analysing a tune that already exists: noted, not started (`docs/TODO.md` S-017).
- Resonalyze's session file is at v11 on the pin while `rew_tool/resonalyze_vc.py` reads v7–v10: the ordinary drift
  check, apart from this design.

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
3. ~~**`eq_propose` in two parts.**~~ Done 2026-09-17: `--part 1` (the coarse per-driver resonances, Phase 1's) and
   `--part 2` (the pairs' L/R shape, then tone); every package names the junctions its bands reach into
   (`recheck_junctions`), so the delay there is re-read before it is banked. Phase 2's later steps — junctions per
   side, sub with mids, sides, everything, centre, rear — are read on the sums (`predict`, `verify_prediction`, the
   MMM), not proposed by this module; the phase document carries the order.
4. ~~**Predicted sums for the target-curve visualizer.**~~ Done 2026-09-17: `rew_tool/sums_export.py` writes ALL, L, R and
   ALL+C from `predicted.json` as visualizer files (named in the header, the variant's label in each), smoothed 1/6 by
   default, or 1/3 · 1/12 · 1/24 · 1/48 · REW's psychoacoustic (1/3 → 1/6, cubic mean) · none.
5. **The engine wrapper**, on the fork's brief and goldens (§4):
   - ~~**5a.**~~ Done 2026-09-17. The whole fork as the submodule `vendor/Resonalyze` at `b0ce9fb` (`update = none`); the
     wrapper `engines/resonalyze/` (contracts `autosound.resonalyze-layout.v1` / `-result.v1`; Auto crossover → Auto
     delay as the window runs them; PEQ bands and given crossovers honoured in the chains; a delay the device cannot
     hold refused with its numbers); `rew_tool/resonalyze_engine.py` (the layout from the project, the run, every edge
     through `xover_wishes.check_setting`, the rear fill that fits, Low confidence named); four goldens in
     `engines/resonalyze/golden/` — the fork's window defaults, types and gains, each reproduced identically through
     the skill's own layout, and the Helix's two delay tiers — `acceptance` 4 of 4; `upstream-drift.py` reads the `//` headers
     (21 files, all current); CI builds the pin and runs a synthetic set. On the Passat with the skill's layout the
     engine's best puts the mids' high-pass at LR24 200 Hz, under their 217 Hz floor — REFUSED, which is what 5b's
     constrained search is for.
   - ~~**5b.**~~ Done 2026-09-17. The wrapper's junction stage (`engines/resonalyze/JunctionStage.cs`): Auto delay committed
     to the settings as the window's Apply does; **repairs** — a `Tune` whose best is written back, then Auto delay again;
     **junctions** — `Probe` of named variants and `Tune` of a family, slopes and a window, read-only. `resonalyze_engine.py
     run` became two passes: Auto crossover alone; then the front-chain junctions whose edge broke a limit are re-searched
     inside it (the device's families and slopes, the window from the floor up), a lone block's edge is set to the nearest
     allowed, Auto delay runs, the wishes are read (`--wishes`: a corner → a probe, a family or slope → a tune held to the
     limits). A default rear fill that does not fit the device is lowered to the largest that fits, and said so; a fill
     the tuner gave is not touched. On the Passat with the rear: the mids' 200 Hz becomes 250 Hz (the score +0.01 dB,
     CAUTION until 278 Hz); counted on one delay tier the rear fill had to drop 15 → 12.5 ms, on the Helix's two tiers
     (20.82 + 20.82 ms) it stays 15; the user's sentence reads "BE4
     between tweeter and mid" at its best as BE24 1050 Hz, −1.25 dB against what stands but in CAUTION on the tweeters,
     and "BW2 between sub and midbass" as BW12 110 Hz at the window's edge, +9.40 dB. Not measured yet: a wish's full
     variant with its own Auto delay (the probe gives the junction's own delay only).
   - **5c.** Per-platform binaries for installs (§5). The skill's half, 2026-09-17: `.github/workflows/engine-binaries.yml`
     publishes a single-file self-contained engine for linux-x64, win-x64, osx-arm64 and osx-x64 (≈80 MB each) as workflow
     artifacts named for the pin, on a tag push and by hand, and runs the synthetic set through the Linux and Apple
     Silicon ones; `resonalyze_engine.py` runs a prebuilt engine (`AUTOSOUND_RESONALYZE_ENGINE`, or `install-binary --from
     <zip>` into a folder per pin and platform) before it reaches for the .NET SDK. The release half — attaching the
     artifacts to a release, and the installers fetching one — waits for the hub's release channel (SKL-041).
6. ~~**Scene presets** (RES-011, hub #161).~~ Done 2026-09-17: `rew_tool/scene_presets.py` — from the ledger version the base
   stands in after 2c and the near-side cut Phase 1 gave it, one preset per rung (0.15 / 0.20 / 0.25 / 0.30 ms): the
   near side later by t on the device's grid, its cut reduced to max(0, cut − 16 t), both channels of the pair trimmed
   so the centred (coherent L+R) level stays the base's; each described by its pull with the time and level parts
   apart, the difference from the base per pair (a band whose cut ran out pulls more, and is named), deltas for
   `apply.propose`, a rung over the device's ceiling refused. `phase_2_eq.md` 2c holds the comparison between "each
   side whole" and "everything together" and reads the L/R balance relative to the deliberate cut; `virtual-first.md`
   1.6 / 2.1 and the listening cheat-sheet (en, uk, de, pl) carry the protocol.
