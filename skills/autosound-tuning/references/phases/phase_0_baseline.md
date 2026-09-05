# Phase 0 — Baseline & Target Preparation

This phase establishes the raw baseline measurement of the car's current acoustic response and prepares the target curves for comparison.

> 🗺️ **Virtual-first?** If Phase −1 chose the virtual-first path (one capture session → design at the desk), the ORDER of work in Phases 0–3 changes — the phase numbers do not. Read [`virtual-first.md`](references/phases/virtual-first.md) alongside this file; it is the one home of that path. This file stays the authority on the iterative fallback and on every gate.

> On virtual-first, Phase 0 is the ONE disciplined **capture session** (handheld levels → RTA + ellipsoid → tripod solos, tripod untouched until Phase 3): [`capture-session-sheet.md`](references/phases/capture-session-sheet.md).

## 🎯 Goal-node

**Purpose:** capture the raw, uncorrected baseline and prepare the target — so tuning starts from measured reality, not assumptions.

**Questions this phase answers:** what channel names/conventions do we agree? what does the system currently do (raw)? is the signal chain clean (no clipping)?

**Required evidence:** agreed naming/glossary; a clean base DSP profile (`v0`, zeroed modifiers); **per-driver** `<ch>_1 (sw)` + `<ch>_1 (rta)` for each driver we'll work with; a locked, repeatable MMM pattern.

**✅ Quality gate → Phase 1:** names agreed **before** measuring; target curve imported (shape only, not level) **and recorded** — `python3 rew_tool/state/process.py <project>/process target <preset> <curve>`; raw baseline captured with all modifiers zeroed; no clipping; MMM pattern locked; **the acoustic flaw map recorded** (§3.5) — `python3 rew_tool/project.py <project> flaw <f_hz> <level_db> <kind> <action> …`, one entry per feature, and a feature you decided to leave alone is still an entry (`action=leave`). `enter-phase 1` refuses while `acoustics.flaws[]` is empty: phase 2 equalises against this map, and in the transcript it is lost by the next session.

> ⛔ `enter-phase 1` **refuses** while no target has been recorded. Importing a curve into REW and
> naming it in chat is not the record: the next session reads `process-state.json`, not this
> conversation.

**⚠️ Failure modes:** measuring before names are agreed (unusable history) · generating per-band targets now (they depend on Phase-1 crossovers) · applying TA/level tricks during the baseline (stay observational).

**🧩 Refs:** naming/history → [`naming-and-structure.md`](references/core/naming-and-structure.md).

---

## Step-by-Step Runbook

### 1. Agree on Naming Conventions (ONCE)
Before any measurements are taken, establish the channel abbreviations (`sw / w-L/R / m-L/R / tw-L/R / c / r`) and the file naming convention:
* Suffix **`(sw)`** = loopback sweep.
* Suffix **`(rta)`** = Multiple Mic Measurement (MMM) RTA.
* Suffix **`_N`** = configuration/measurement version (starts at `_1`, NOT "baseline").
* *Examples:* `m-L_1 (sw)`, `w-R_1 (rta)`.

Give the user copy-paste-ready specifics containing the exact save PATH, short comma-separated measurement names, and a brief explanation of the immediate goal. Follow the history hygiene details in [naming-and-structure.md](references/core/naming-and-structure.md).

### 2. Import Target Curve
Load the chosen house curve into REW, **then write down which one it is**:

```

> **Two facts wear the name "target", and this command feeds the one the readers use for CURRENT.** `process target` writes the active pointer to `process/process-state.json` (`targets[preset]`) — what the enter-phase-1 gate, the plan audit, the settings-sheet header and the TCC header all now read as the current curve. A ledger snapshot ALSO carries a `target`, but that is historical — *what that version was designed against* — and is the fallback, not the current pointer. Set the curve with this command and every reader is current; a snapshot is not rewritten for it (2026-08-25).
python3 rew_tool/state/process.py <project>/process target <preset> <curve>
# e.g. …/process target FULL EPY
```

Name it so it resolves later — a bundled curve's name, or the path under
`rew_analitic/target-curves/<name>/` for an imported one. "The one we agreed" is not a name.
* **The target curve defines only the SHAPE**, not the absolute level.
* Anchoring of curves and target levels is handled relative to the measured midrange level.
* **Do NOT generate per-band targets yet!** Per-band targets depend on the final acoustic crossovers and are generated in Phase 1 (Step 5b) after crossovers are finalized.

### 2.5 Prepare the Base DSP Profile (Arbiter)
Before taking raw baseline measurements, prepare the clean starting preset in Helix PC-Tool:
* **Clean Baseline Profile:** Start with a clean/reset preset in Helix PC-Tool (representing version `v0`).
* **Basic Configuration Only:** Configure the input-to-output routing matrix (Input/Output Matrix) and assign correct output names (`tw-L/R`, `m-L/R`, `w-L/R`, `sw`) according to the glossary.
* **Zero Acoustic Modifiers:** Ensure all acoustic modifiers are cleared: all delays set to exactly `0 ms / 0 cm / 0 samples`, all polarities set to NORM, all output EQs flat (bypass/0 dB), and initial output gains set to 0 dB (with protective crossovers applied to ВЧ/СЧ as described in Phase 1).
* This forms the "pure routing preset" baseline from which all subsequent acoustic tuning is built.

### 3. Capture the Baseline (per-driver)
Instruct the user to measure **each driver we'll work with**, solo, on the clean `v0` profile (protective HPFs on fragile drivers; no TA/EQ). ⚠️ **Before any sweep, run the pre-sweep safety gate** `rew_tool/gates/presweep_safety.py` → `require_safe([...])`: a full-range sweep with no/too-low/too-gentle HPF on a fragile driver (tweeter/mid) can destroy it, so the gate refuses unless HPF ≥ 1.1×Fs @ ≥24 dB/oct + level under the safe ceiling + clip headroom. Hardware safety is acoustic-domain but HARD — no waiver (a blown tweeter isn't recoverable).

**Record the protection on the round, in the same breath as the sweep:** `python3 rew_tool/state/process.py <project>/process capture-protective <ch> --hp 1000 LR 24` for every driver swept behind a protective filter, `… capture-protective <ch> OFF` for one swept bare. Doctrine (2026-08-24) → [`project-intake.md §3`](references/core/project-intake.md), the after-the-sweep half: a joint-phase decision read through an unrecorded protective filter is invalid, and Phase 1 answers `check` for an unmarked baseline solo instead of a number.

⚠️ **After the pass, run the post-sweep quality gate** — `python3 rew_tool/state/process.py <project>/process capture-check --session` (`--session` adds the whole-session table and the ctl1 → ctl3 drift record, written onto the round). It asks two things of every capture in the round: is it there and readable at all, and is its pre-echo far worse than the CLEANEST capture of the same driver (`REMEASURE_MARGIN_DB`, 15 dB). The second is why the comparison is a driver against itself rather than against a number: on a real car sweep the pre-echo includes the loopback reference and earlier arrivals, so an absolute threshold condemns good sweeps. A flagged capture is still readable — re-taking it is the Arbiter's call — but the step cannot close until the round has been checked (SCR-040). The pre-sweep gate protects the hardware; this one protects the conclusions.
* For every front channel — `sw` (or `sw-f` and `sw-r`), `w-L/R`, `m-L/R`, `tw-L/R` — capture `<ch>_1 (sw)` (loopback sweep → IR/phase/GD) **and** `<ch>_1 (rta)` (MMM). **Two subs: also `SWs_1 (sw)` from the tripod** — their mutual phase decision needs a measured pair like any other. *(Center/rear are integrated later, Phase 5.)*
* This per-driver set **is** the raw baseline **and** the input for Phase 1 (TA, crossovers, levels, per-band targets) — **Phase 1 does not re-collect it.**
* Do **NOT** perform time-alignment, delay, or level-matching yet. This phase is purely observational.

### 3.5 Acoustic Flaw Map — one analytical pass over the raw baseline (NEW CAR: mandatory; same car with a CHANGED install: redo)

From the SAME `_1` captures (no extra measuring), build the install/cabin flaw map that every later phase consumes. Three tools, three artifacts:

1. **EQ-ability map (per channel):** create REW excess-phase versions of each `<ch>_1 (sw)` (`rew_api.excess_phase_version`) → build `eq_gate.ExcessPhaseGate` per channel. This replaces guessing later: Phase-2 EQ fits take the gate directly (`boost_gate=`), and known-bad zones land in the car record as data, not lore.
2. **Pair coherence maps (per L/R pair):** weighted pair coherence `20·log10(|L+R|/(|L|+|R|))` over each pair's band + the unwrapped Δφ climb test (`diagnostic §26`). ⚠️ **Align the pair FIRST.** The metric asks what a delay CANNOT fix, so the delay must be out of the way before you ask: apply each pair's own relative delay (the one you will actually set — from arrivals where `arrival_triangulate` says TRUSTED, from summation where it says ILL-POSED), and use a **physical** alignment, not a best-fit τ (`estimator-scope.md` §3). Phase 0 captures solos with modifiers zeroed, so nothing is aligned by default and the pair's geometric offset — 1.2–1.4 ms on the source build — sits inside the number and reads as divergence. Measured cost of skipping it: a "−18.96 dB pocket, deepest in the pair" that was **−1.9 dB** once aligned, and would have pushed a crossover corner out of a healthy region. Pockets < −3 dB with a >1-rotation climb = **multipath — flagged NOW**: no one burns APF bands on it later, and the center-fill/physics decision (§26 remedy) enters the plan early instead of surfacing as a Phase-4 listening mystery.
3. **Three-distance reads (per channel + pairs' L−R):** `curve_view.report` (band → macro trend → fine features with doctrine routing) — macro anomalies inform crossover/level planning; routed fine features seed the verify list.

4. **Distortion floor map (per driver):** `rew_api.get_distortion` on each `<ch>_1 (sw)` (THD comes free with the sweep). Mark where in-band THD exceeds ~1 % (caution) / ~3 % (avoid) — **crossover corners in Phase 1 need low measured THD with margin**, which replaces datasheet-only floors; in-band spikes are install findings for the car record. Below-HPF rows are noise — ignore. **⚠️ Disqualify null-artifact spikes before blaming mechanics:** in a deep interference null the fundamental drops 20+ dB while the harmonics (radiated at 2f/3f, outside the null) don't → THD % explodes with a *quiet* fundamental. Rule: a THD spike counts as a driver/install fault only if the fundamental there is within ~10 dB of its neighbors; high-THD-only-where-the-fundamental-collapses + clean THD at loud neighboring points = healthy driver, null artifact (field case: a woofer's 4.4 % @ 160 Hz at fundamental 53 dB vs 0.2-0.5 % at 100-125 Hz at 81-84 dB — mechanics cleared).

**These four are a LIST, not a sequence — pick the order by what is blocked.** They are numbered
for reference, and a session read the numbering as an order, ran all four, and only then learned
that the first one cannot speak about the joint it needed (inbox 3.6). Each artifact has a
frequency scope and a Phase-1 decision that consumes it; that is what decides what to do first:

| artifact | scope | SILENT about | the Phase-1 decision that consumes it |
|---|---|---|---|
| 1. EQ-ability map | the `eq_gate` calibrated band — **not below ~150 Hz**, where it returns `OUT_OF_SCOPE` with no metric (`estimator-scope.md`) | anything sub-territory | Phase-2 EQ fits (`boost_gate=`), **not** the sub↔midbass joint |
| 2. Pair coherence | each pair's own band, wherever the pair overlaps | one channel alone; anything before the pair is aligned | whether a pocket is multipath — i.e. whether to spend a crossover corner or an APF on it at all |
| 3. Three-distance reads | full band, per channel and per pair's L−R | phase and timing entirely | voicing territory vs point-EQ vs null-suspect — the routing every later EQ decision starts from |
| 4. Distortion floor | full band, per driver | anything about summation | how low a driver may be crossed, and whether a "flaw" is really the driver protesting |

**The usual first Phase-1 decision is the sub↔midbass joint, and artifact 1 is silent there.** If
that is your first decision, artifacts 2 and 4 are on its critical path and artifact 1 is not — do
them first and let the EQ-ability map follow. Reading the list top-to-bottom cost a session exactly
that, and the cost is real work: the excess-phase versions are one REW round trip per channel.

**Record the map as DATA, not only as prose** (SCR-015). The rows can be PROPOSED from the solos
first — `python3 rew_tool/flaw_map.py --project <project> --solos DIR [--ellipsoid DIR]` reads the
features, asks the ellipsoid what stays and the excess-phase gate what is minimum-phase, and prints
the rows it would write (driver resonance / cabin mode → `notch`, a null below Schroeder or a
non-minimum-phase feature → `no_boost`) **and every finding it will NOT write, with the reason**;
`--write` records them as `hypothesis`. A person confirms or rejects each after the car has been
heard — that verdict is written with the manual command, which each finding gets as a row:

```bash
python3 rew_tool/project.py <project> flaw <f_hz> <level_db> <kind> <action> \
  [--q Q | --bw-oct B] [--channels w-R,w-L] --why "..." --evidence "w-R_1 (sw)" \
  [--status hypothesis] [--symptom "what the owner hears"]
```

**A row has two readers, and `--why` only serves one.** `why` is the audit trail — the measurement,
the cross-check, the doubt, the section it argues with — and the next session reads it. `--symptom`
is one sentence in the **owner's** words: *"the bass comes from both sides"*, *"a piano left of
centre wanders with pitch"*. Write it on every row an owner will be shown (`geometry`, `leave`,
`no_boost` — `project.OWNER_FACING_ACTIONS`, the rows that stay in the car after the tune is
finished); `project.py flaws --owner` prints exactly those and names the ones still missing it.

**The register to write in is `project.KIND_HEARD`** — one line per mechanism saying what it sounds
like, beside the `FLAW_KINDS` it belongs to. It used to say "borrow it from `knowledge/cars/<body>.md`",
which works for exactly the one body that folder holds; what a mechanism sounds like does not depend
on the cabin (autosound-hub `CAR-007`). **You do not start from nothing either:** `flaw_map.py`
writes a `DRAFT:` symptom on every owner-facing row it proposes, built from the kind, the band and
the channel. A draft is a placeholder so the row is not born empty — it is not the owner's words,
it does not close the row, and the gate below counts it as unwritten. Bought on a live 18-row map where not one
row said what a person hears, so a panel showed the owner an audit trail whose longest entry ran
763 characters.

`level_db` is the **feature** — `+` a hump, `−` a dip — not the correction you would apply to it.
`kind` and `action` come from closed lists (`project.py flaws` prints the map; the usage text lists
both), because a front-end colours by `action` and "what may NOT be done here" has to survive the
session that discovered it. **A dip can never be `notch`**: a null is interference, not
minimum-phase, so cutting it changes nothing and boosting it burns headroom against physics — the
writer refuses it, which is the one rule in this map with teeth. Re-measuring the same frequency on
the same channels REPLACES its row rather than appending a second, contradictory one.

Then also record it in the car record (PART-B style: each item phrased as a check) +
`autosound_context.md`; log in the changelog. **Downstream consumption (the map is not a report — it binds):** Phase 1 crossover corners avoid landing joints inside multipath pockets / non-min-phase zones; Phase 2 EQ passes the gate; imaging work knows which symptoms are electrically unfixable BEFORE chasing them.

### 4. Gain Staging & Environmental Hygiene
* Check for clipping (DSP outputs vs. amplifier inputs). Measurements must remain clean and undistorted.
* Lock down a repeatable **MMM measurement pattern** (spatial boundaries, speed, volume coverage). Successive RTA tests must use this identical pattern to be comparable.

### The boundary out of phase 0 — one command, not a memory

```bash
python3 rew_tool/contract.py check <project> --phase0-gate     # exits non-zero while a row owes its sentence
```

Once the baseline is saved, analyzed, and logged in the `tuning-changelog` — **and the map can be
read by the person it is shown to** — proceed to **Phase 1**. The gate asks one thing: every
owner-facing row carries the owner's own sentence, a machine `DRAFT:` not counting. It exists
because the requirement stood here in prose for two days and was met on one map out of four
(`CAR-007`), and because the map has exactly one other rule with teeth (a `dip` can never be
`notch`) — prose held neither.

The order stays what it was: the row is written when the measurement is made, **before** anyone has
listened; the sentence is added by the end of the phase, after they have. What the gate forbids is
leaving phase 0 with the sentence still owed.

**A schema change does not reach the cars on its own.** When a new field lands, the projects already
on disk become incomplete and nothing says so — `symptom` was filled on one of four copies of the
same car's map two days after it existed. Ask, across everything on disk:

```bash
python3 rew_tool/contract.py gaps                  # the projects around this one
python3 rew_tool/contract.py gaps <dir> [<dir> ...]  # or say where they live
```

With no path it scans `$AUTOSOUND_PROJECT_DIR`'s parent, or the working directory — so it runs on
somebody else's disk without knowing the author's folder layout. **The project you are IN needs no
separate run:** Pre-Session step 2 already calls `contract.py check <project>` every start, and that
report now names the owing rows. `gaps` is for the copies you are NOT in — which is where the four
maps of one car sat.
