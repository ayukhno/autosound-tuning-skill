# W-2 · v3.0.60 — the plan

> Milestone: `W-2 · v3.0.60` in this repo · the wave's rules: hub `governance/WAVES.md` · the
> collection it came from: `docs/TODO.md` (W-1's leftovers S-019…S-052), the open issues of this repo,
> and the bus tickets `to:skill`.

**The number was read, not agreed:** tcc opened `W-2 · v0.1.43` on 2026-09-22 (its `docs/PLAN-W-2.md`),
so this is the same wave. `vendor/autosound-tuning-skill` moves in it, so the wave is shared and the
**skill tags first** (`WAVES.md` §1 step 4).

**The Arbiter's rule for this review, 2026-09-22:** «ціль — включити максимально все, що не відкладено.
що не включемо — то зрозуміти причину і відкласти». Everything below is in, except the few items under
*Not included*, and each of those has a reason and a condition that brings it back.

**The goal in one sentence, so a session can check itself against it:** a tuning round runs from the
intake form to a banked version on ONE record. Every tool reads the round instead of asking for it
again, refuses instead of guessing, and the reviewer is reachable from wherever the session was
launched.

## How the work is run

Same as W-1 (`docs/PLAN-W-1.md`), with one change:

- **One branch for the wave: `wave-2026-09-20`.** It already carries the intake form (rounds 1–8). It
  keeps its name because hub `#193` and `#194` cite it.
- **Tests while working:** targeted only (the module's own selftest and the files the change touches).
  The full suite runs once, before the PR, with the Windows VM suspended and `-n 4`.
- **CI:** once, on the PR. **Package C touches installing**, so it gets one `workflow_dispatch` on the
  branch when it lands (`WAVES.md` §2).
- **Models:** Opus for judgment (what a rule says, what a refusal names, reviewing a diff). Sonnet
  subagents for sweeps and scaffolding, at most four at a time, and their output is always read.
- **Order:** A, B and R's first step (the reader contract) come first, because tcc's half waits for
  them (see *Blockers*). Then R's migration, then F, which is small, then V, which reads F's level step.
  E is the largest package and goes last.

### Run without the Arbiter (his answers, 2026-09-22, before he left the session to work)

- **The session goes as far as a green PR** with the full CI, and stops there. The merge and the tag
  happen on his word.
- **Forks during the work are decided, not waited on.** Each decision follows the plan and his
  recorded decisions, and goes into its commit and into `docs/W-2-DECISIONS.md` for him to read
  afterwards. The session stops only on what cannot be undone.
- **The reader contract for tcc goes on hub `#195` as soon as it is decided**, without waiting for
  him.
- **The Windows VMs may be suspended by the session** (`prlctl suspend`, never stop) before the full
  suite.

## A — ship the intake form (built on the branch)

S-033 · S-037 · S-052 · the skill's half of hub `#193` / `#194` · S-025 · S-027 · S-030 · S-042.

1. **The form is built** (`docs/DESIGN-2026-09-22-intake-simplified.md`, rounds 1–8). What is owed:
   check S-037's eight points against the page one by one, then close S-033 and S-037 with the page's
   selftest as proof.
2. **Decided by the Arbiter at this review (S-052 item 1):** «ми в форму інтейка це вже додали. хай
   там і буде. але якщо не задано, то так запитати». The target curve and the goal/taste questions stay
   on the intake form, where rounds 2–3 put them as optional. **Whatever the person left empty there,
   Phase 0 asks after the baseline.** The work is prose: `phase_-1_intake.md` (the gate line and §2)
   and `phase_0_baseline.md` §2 must say "on the form; asked in Phase 0 only if it is still empty".
3. **S-025:** `hardware.controls` keeps the knobs (round 5) and refuses a key that is a processor
   feature (`RealCenter`, `VirtualX`) or unknown. The control module's logic is not modelled: the
   Arbiter's word is «просто OFF для налаштування».
4. **S-027:** a `sources` line is prose and is never checked as a path.
5. **S-030:** the knowledge row says it is AUX that does not hold across a configuration write or a
   reconnect, and the check moves to "after every write, every reconnect, and before every series".
6. **S-042:** `naming.py parse` refuses a code with `_` in it and resolves the code against the
   glossary and `previous_names`. A check reports an `id` that is not the code or one of its
   `previous_names`. The Arbiter, at this review: «для мене правильна назва через "-" давай кругом
   зробимо так». The hyphen is the notation everywhere, and the check says the fix (set the id to its
   code). **When a session meets such a project, it asks and offers to fix it right there** (the
   Arbiter: «якщо така ситуація трапляється то можна запитати користувача і запропонувати привести
   все до ладу прямо в сесії»). It shows the list (`w_L → w-L`, …), and on his OK one command writes
   it through the project's own writer: `project.py <project> fix-ids`, which prints what it would
   change unless it is given `--apply`. Nothing changes without the OK. The Passat's six ids and its other live names are the car role's tree: hub `#196`
   (SKL-050).
7. **The session reads how each driver is installed** (the Arbiter, at this review: the intake's
   free text «буде доступно сесії ШІ, і якщо там буде щось важливе, вона його обробить — наприклад,
   як у мене є "направлено на водія в вухо"»). The form writes `channels[].install` and
   `hardware.description`, but no phase text tells the session to read them yet. So each place where
   a mount or an aim changes the reading gets one line saying to read them there and name what
   matters: Phase 1 delays and levels, Phase 2 tweeter EQ, Phase 4 imaging, and a copied seat. A
   tweeter aimed at the driver's ear is off-axis at the passenger seat, which is V's test. S-051, the
   list form of mount and aim, is dropped (the Arbiter: «варіанти списком скасували»): the text is
   the model.

## B — the reviewer is reachable from any launch

hub `#187` (TCC-024) · skill `#54` · skill `#55` (`#57` P6 is their summary).

1. **The transport follows the model, not an exported key.** If the API answers that the model does
   not exist, the call falls through to the CLI that `_PROVIDERS` already lists, and one line says
   which path was taken (`#187` ask 1).
2. **The nested-session refusal names a way out that exists.** Under a TCC-launched session there is
   no separate terminal, so the message skips that rung. It stops advertising
   `AUTOSOUND_ALLOW_NESTED_CLI=1` where the host blocks it (`#54` 1–3, `#187` ask 2).
3. **A per-run route: `--via api|cli|clipboard`** (`#55` 3). `#54` 4, a detached helper with the agent
   markers stripped, is judged against this: build it only if `--via` does not close the TCC case.
4. **`doctor` tells a suppressed key from a missing one** (`#55` 1–2), and names where the model comes
   from (`GEMINI_CRITIC_MODEL` from TCC vs `critic-env`, the correction on `#54`).
5. **The raw exchange is kept on request:** a variable names a folder (`#187` ask 3).
6. **The installer's signal 5:** an exported key alone no longer counts as "reviewer set up"
   (`#187`, the comment of 2026-09-19).

## C — the machine and the installer

hub `#192` (TCC-024) · S-028 · S-049 (second half) · S-022 · S-020.

1. **`usable()` runs the tool once** after `xcode-select -p` answers, reads the exit code, and on a
   failure says what the tool printed and names `brew install git` (`#192` 1–2). The same check
   applies to `python3` (`#192` 3).
2. **S-028:** `doctor` names an x86_64 shell in which `python3` dies on `xcrun`, and gives the
   `arch -arm64` way out.
3. **S-049, the installer's receipt:** a file on the machine records which `install.sh` ran, at which
   tag, and what it did about the engine.
4. **S-022:** a prebuilt engine is found by the WRAPPER's identity (the tag it was built for), not by
   the fork pin alone, and `engine_command` says which one runs when the two disagree.
5. **S-020's last step is a run, not code:** the README one-liner on the Windows VM with no .NET SDK
   (it should fetch about 30 MB and check it), then `resonalyze_engine.py smoke`, then `-NoEngine`.
   This needs the Arbiter at the VM.

## D — what a car package may carry (`rew_tool/project_seed.py`)

hub `#185` (SKL-044) · hub `#186` (SKL-045). The Arbiter's decisions of 2026-09-19 are in the tickets.

1. The tune's purpose (`preference-profile.md`) and the control module's state (`hardware.controls`)
   never travel and get no checkbox.
2. The drivers' `fs_hz` travel behind their own flag, on by default, and each one says it was
   imported: which project it came from, and the date it was measured there.
3. `seeded_from` becomes the import record: where from, when, what was taken, what was skipped and
   by whose choice, and the protective filters and knob positions as history.
4. `sources` do not pile up from one copy to the next, and an absolute path never travels.

TCC's Fs checkbox (its F-068) waits for this flag, and tcc left it out of its W-2 for that reason. It
can follow in tcc's next wave.

## E — the round is the one record (Phases 1–2)

skill `#57` P0–P5 · `#56` items 1–10 · `#58` P1, P3–P12 · S-026.

The three issues overlap. They are one package so that one design covers them, not three patches.
The order below is the one `#58` proposes, merged with `#57`'s:

1. **Nothing can break the record** (`#58` P1, P5, P8). A banked `v_NNN` cannot be changed:
   `contract.py check` hashes it. Every number in a proposal names its source, and an assumption is
   never written to state. Replies follow the output contract: titles not ids, the quantity named, no
   emoji.
2. **The round record drives the tools** (`#57` P0, `#56` 8–10, `#58` P3, S-026). `capture-start`
   binds the ledger version, asks the protective state, and records the level as a quantity. Close
   asks the knobs, with `--amend` for a closed round. A tool takes `--round`/`--series` and refuses
   when a field is missing, naming it. `predict.py` defaults `--from-state` from the round.
3. **Refuse instead of degrade** (`#57` P1, `#56` 1–7). A junction without a measured pair is not
   given a verdict. `excess_phase_version` sends REW's real keys and checks the result appeared.
   There is a min-phase verdict helper. Per-band targets use one name spelling. `channel_of`
   resolves against the glossary. `target_bands` takes Bessel from `dsp_math`. `eq_propose --part 2`
   reads `(rta)` and clamps each band to the channel's own band.
4. **Banking needs evidence; the next capture is derived** (`#57` P2–P3, `#58` P6–P7, P11–P12). A
   candidate is fast and has its sources named. A banked version needs evidence, plus one reviewer
   call for a structural change. The minimal verification set is computed from the diff between
   versions. A proposal shows "yours → mine, why".
5. **The rest:** `#57` P4 (the car checklist gets its series number from the project), `#57` P5
   (a verdict in 5 lines or fewer), `#58` P4 (`rew_api` labels or refuses another file's data),
   `#58` P9 (`rew_tool compare`), `#58` P10 (where each front-end keeps its transcripts).

## R — versions numbered once per project, the preset is the slot

S-053 · hub `#195` (TCC-025) · `#58` P2. **tcc needs this in the same wave** (the Arbiter, 2026-09-22):
its W-2 left its half out only because the method had no ticket for it.

1. **The reader contract first, before any file moves** (`#195` ask 2). Decide the layout and post
   it on `#195` in one sentence of shape: where a version lives, how its slot is recorded, and what
   `HEAD` is. tcc reads the ledger directly (`config.state_root()` / `available_presets()`,
   `dsp_state`, `plan_audit`, the `<preset>/HEAD` watcher), and it builds its half against this
   sentence while the method builds the migration.
2. **The migration** (`#195` ask 1): one version line per project. A preset records which version it
   holds and since when. Each preset's old `v_NNN` stays findable, because journals, rounds and
   reports cite them.
3. **One-way and refusing** (`#195` ask 3): a half-migrated project is refused with the command that
   finishes it.
4. **Variants live inside the ledger** (`#58` P2): `state.py variant new/show/switch`, and no
   project-local switch scripts.

This is the migration `docs/PLAN-W-1.md` §A.3 left for W-2.

## F — the Phase-1 numbers

skill `#50` · `#51` · `#52`.

W-1 left these out because they needed the Arbiter's decisions. Read again, they no longer do:

- `#52` answers "what is a gain step" itself: a PC-Tool setting with four values. The profile models
  it as a setting, the sheet is checked against it, and the intake asks it for a new processor.
- `#51` asks the method to REPORT the trade, not to set a headroom policy. Above a 3 dB cut-only
  spread the output says it is a gain-structure finding and does the arithmetic, and the tuner
  chooses. The 3 dB is the issue's number, and the Arbiter can move it.
- `#50` is a label on the metric, a level-step column beside the loss, and a runbook line (a re-read
  after 1.6, or why none is needed).

## V — Phase 1 variants as a feature

skill `#38` · S-021. Deferred at first, then taken in by the Arbiter at the same review, 2026-09-22:
«давай це включемо в версію, щоб воно було реалізовано як фітча. а такий підхід потрібен не тільки на
іншій машині але і на новому налаштуванні … ми можемо запустити налаштування для пасажира — ось тобі і
нова "машина" і аналіз».

**What exists** (`docs/DESIGN-2026-09-17-phase1-variants.md` §6): the engine's best configuration, and a
whole variant per wish (the wish's edges, Auto delay again over the chain, every junction re-read, the
delays that moved and the polarity flips named). That answers "what does my wish cost". It does not
answer `#38`'s own question: which configurations win when the goals pull against each other.

**What V builds, from `#38`:**

1. **Every variant gets the same breakdown, per term:** tonal distance from the target curve, L−R
   balance per band (the Passat's +7.9 dB at 250–500 Hz is the case that no junction metric sees),
   junction sum loss with the level step beside it (F, `#50`), and ripple.
2. **Without wishes, 2–3 variants are chosen by different weightings of those terms**, as a trade-off
   front: each one is labelled by what it buys and what it spends. The tool does not pick a winner
   (`ladder_report`'s rule: a table sorted by the score is a proposal dressed up as a table).
3. **Each output says what the objective cannot see:** a junction the tool calls limited by
   multipath (for example the Passat's m/tw pair, 1.30 rotations), and imaging, depth and fatigue,
   which is why Phases 4–5 exist.
4. **The test is a new tuning, not a new car:** a passenger-seat project on the Passat, copied with
   its seat chosen at the copy (S-032, hub `#193`), run from the intake through Phase 0 to the choice
   in Phase 1. It is a fresh project with fresh captures. The only thing it does not exercise is a
   driver or processor the method has not seen. It is the Arbiter's test after the release, so S-021
   goes to `waiting` at the tag, naming this run.

## G — bookkeeping

- skill `#47`, `#49`: fixed in `7e648f7`, which `v3.0.59` contains. Closed with their selftests.
- hub `#178` (SCR-059): `9de1085` is in `v3.0.59`, which is what W-1 said it would close with
  (S-023).
- hub `#180` (SKL-043): the milestone is being tried again. The question owed after W-1 (keep,
  downgrade, or drop) is put to the Arbiter at this review.

## Not included, and why

| item | why | comes back when |
|---|---|---|
| already deferred, untouched: S-001, S-017, `#24`, `#26`, hub `#82`, `#113` | the user's earlier word | as each one's line says |

**Named once:** `#24`, `#26`, hub `#82` and `#113` wait for "tag `skill-v3.1.0`". On 2026-09-18 the
user decided that no minor version is cut to announce a capability (`WAVES.md` §3.1), so that tag
will not come on its own.

## Blockers

- **tcc builds its half of R against the reader contract** (R.1), so that sentence is due early in
  the wave, not at the tag.
- **The wave is shared, and the skill tags first.** tcc's `#193`, `#194`, S-044 and its half of the
  reviewer channel need a published skill tag. A and B go first for that reason. If tcc is ready
  before E is, whether to cut earlier is the Arbiter's decision.
- **S-020 needs the Arbiter at the Windows VM.**

## Exit

hub `governance/WAVES.md` §3.1. `release-preflight.py` passes on the merge commit. The CHANGELOG's top
heading names `v3.0.60`, and the release note says the reply language now follows the interface
(`DESIGN-2026-09-22-intake-simplified.md` round 5). The version bump and `uv.lock` are on the branch,
and the full suite is green locally.
