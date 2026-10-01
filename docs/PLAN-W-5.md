# W-5 · v3.0.65 — the plan

Collection opened 2026-10-01 (the Arbiter: «відкривай веху W-5», then «я мав на увазі не milestone а збір») and
closed the same day («збір закінчено»). `ok` on #101–#105; #106 and #107 joined from tcc afterwards (hub #226, #227)
and got his `ok` the same day. **The build waits for his word**: «почекай йти в розробку від ТСС можуть бути додаткові
тікети, або будь готовий їх додати по ходу роботи». A patch: v3.1.0 with TCC v1.1.0 comes after it (hub #220).

"How" below was read from the code on 2026-10-01; names marked *(name in code)* are decided while building.

## The tasks

### #101 — TCC's tag verified before the installers install it (hub #224)

Today `verify_tag` (`install.sh:795-829`) and `Test-TagSignature` (`install.ps1:845-880`) verify the method's tag in
the method's own clone; TCC goes in by `uv tool install … git+$TCC_REPO@$TCC_REF` (`install.sh:1160`,
`install.ps1:1217`) with no check, and there is no TCC clone on disk at that moment.

- **Mirror TCC's own updater** (`tcc core/updates.py` `check_tcc_tag`, 994-1033): a temporary bare repo, fetch
  `+refs/tags/<tag>:refs/tags/<tag>` from `$TCC_REPO`, verify against the same key, resolve the commit, and before
  `uv` check that the tag still peels to that commit (TCC's "moved" check).
- `verify_tag` / `Test-TagSignature` take the first-signed tag as a parameter; a new constant `TCC_SIGNED_FROM="v0.1.45"`
  beside `SKILL_SIGNED_FROM` (TCC's `signed_tags.py` has the same value). `installer-consistency.py` §5d compares it
  across both installers.
- The app's block says «✓ v0.1.45 is signed by TCC's author», «predates signed tags», or the skip line. A tag that
  does not verify is not installed; the method's install goes on and the run ends with the reason. Git too old → said.
- `install.ps1` already skips the whole TCC install while TCC runs; `install.sh` has no such path (macOS does not lock
  the files) — unchanged.
- Tests: the signing fixtures (author / stranger keys) gain TCC-shaped tags: `v0.1.44` unsigned (predates), `v0.1.45`
  signed, `v0.1.46` by a stranger, `v0.1.47` unsigned.
- **Needs the Arbiter:** a run on the Windows VM and on the Mac before the tag. TCC has no beta tags today; the beta
  path verifies the same way.

### #102 — an inherited Fs warns before the sweep (hub #225)

`check_presweep` (`gates/presweep_safety.py:26-70`) returns problems only, and nothing in code calls it: the session
runs `require_safe` as `phases/phase_0_baseline.md:81` says. The inherited-Fs branch (:46-51) moves to warnings
*(name in code)* with the same sentence; `require_safe` prints them and raises on problems only. HPF ≥ 1.1 × Fs at
≥ 24 dB/oct stays a refusal. The selftest (:124-133), the docstring (:31-36) and `phase_0_baseline.md:81` change with
it. `contract.py` already reports inherited facts as a warning (:1203-1208).

### #103 — channel names: both notations read, the hyphen written (S-079, hub #196)

No central resolver today: `Project.resolve_channel` matches exactly, `naming.parse_name` refuses a code with `_`
(since S-042, `naming.py:387-393`), and at least eight local `_`→`-` fixes grew one by one (`predict.py:157`,
`scene_presets.py:89`, `rew_tool.py:618`, `level_offsets.py:303`, `rew_stub.py:209`, `path_check.py:338`,
`resonalyze_engine.py:470`, `:703`).

- One canonical form in `naming.py` (stdlib-only): `_`→`-` **in the code part only**, after the last `_N` series is
  split off — `w_L_3` → `w-L_3`, while `sw_1` and `ALL+C_25` are unchanged (`_` is the series separator,
  `naming-and-structure.md:75`). A file stem carries no series and is canonicalised whole.
- `parse_name` reads a `_` code through it, with a note; `resolve_channel` and `state/apply.py`'s identity map compare
  canonical forms; the local fixes call it.
- `project.py fix-ids --apply` still writes the hyphen into `project.json`, so hub #196 shrinks to one optional command
  for car.
- Tests on the Passat's shape: code `w-L`, id `w_L`, ledger rows, titles `w_L_3`, `w-L_3`, `sw_1`, `ALL+C_25`.

### #104 — translations level with English (S-078)

Structure compared on 2026-10-01: README and FAQ in uk/de/pl, the de and pl cheat sheets — level. The `test-tracks`
translations are partial by design (only the cue table; the file says so). **One gap:**
`listening-cheat-sheet.uk.md` lacks "Which correction points at which characteristic" (English :73, 7 table rows).
That file goes through the Advisor (`autosound_ai.py ask`); the session checks the structure after.

### #105 — the existing-tune route (S-017, S-080)

The Arbiter's route: the car as it is, its settings and curves; then raw solos under protective filters; at the desk,
several improvements against the current tune and a proposal from scratch.

**There already:** `setup_import.py` (the transcription into the ledger with provenance; EQ from the ATF bank);
`predict.py --project P --state-ver V` (any ledger version from raw solos, the protective filters taken out first);
`verify_prediction.py` (predicted against measured, ≤ 1 dB per junction band); `variant_front.py` (four terms, picks
named by what they buy and spend); `resonalyze_engine.py run` (the best, alternatives, wishes); and `goal.mode` in
the intake (`new_tune` / `improve_existing` / `light_touch`, `intake.py:96`), which nothing reads yet.

**To build:**
1. **One voice.** The route written once (`phases/virtual-first.md` or its own page *(decided in code)*):
   −1 (mode `improve_existing`, `setup_import`, the backup) → 0 (an "as is" block, then the usual tripod solos under
   protectives) → desk (the current tune predicted from the solos and checked against the "as is" capture; the
   engine's best and alternatives; the current tune as a candidate on the same front) → 3 → 4. The "not laid out"
   lines (`phase_-1_intake.md:5`, `virtual-first.md:27-37`) and `project-intake.md:145`'s "−1 → 3 → 4, no new
   solos" give way to it; Level 0 stays the light-touch door.
2. **The "as is" block** in `capture-session-sheet.md` and in the plan code (`naming._CAPTURE_PLAN`, keyed by phase,
   or round titles on `capture-start`) *(decided in code)*; its round records `under` = the transcribed version.
3. **The current tune as a candidate**: chains from a ledger version into `variant_front.terms` / `front` beside the
   engine's (`resonalyze_engine.py` `variant_front_from`, 1122) — an option on `run` *(name in code)*.
4. `handoff` / the start check name the route when `goal.mode` is `improve_existing`.

To check while building: a Phase-0 round opened `--under v0` plus `--from-state`'s default may divide the protective
chain out twice. **The walk:** the Passat after AYA 17.10; v3.1.0 waits for it.

### #106 — the run's reviewer model wins (hub #226)

`autosound_ai.py` gains `--model` and `--provider` for one run, beside `--via`: the run's model beats a pinned
`AUTOSOUND_CRITIC_MODEL` in any critic-env; the provider follows the run's model unless `--provider` is given; one line
names the pin that lost and its file. A pin stays the default for runs that name none. The flag names go onto hub
#226 **before** TCC builds its half.

### #107 — `session-close` as a check, a close taken back, a stale CONTINUE (hub #227)

TCC calls `session-close` itself on the way out and reads its exit code (`tcc core/process_writer.py`
`close_session`), so its behaviour stays. Beside it: a read-only form *(name in code: `--check`)* with the same
report and exit code and no write; a reopening event with a reason *(name in code)* — the close stays in the
journal, the reopening follows it; and the CONTINUE block's named HEAD compared with the ledger's in `handoff` and
`contract.py check` (today `process.py:582` checks only that the block exists).

## Order

1. **Contracts first, so TCC can build in parallel:** #106's flags and #107's event named on hub #226 / #227.
2. Small and local: #102, #104.
3. #107, #106, #103.
4. #101 — then the Arbiter's runs on the VM and the Mac.
5. #105 — the largest; built here so the Passat walk after AYA meets it.

One branch, one PR, the full suite once before it; skill's tag first, then TCC pins it (a shared wave: the vendored
skill moves, `WAVES.md` §1 step 4).

## What TCC is asked for

| from | what | when |
|---|---|---|
| #106 (hub #226) | pass the footer's pick as `--model` (and `--provider` if it has one); refuse it to a skill older than v3.0.65, like `process_writer`'s version table | after the flags are named on #226; built against our tag |
| #107 (hub #227) | read the reopening event, so a close taken back reads as an open session | after the event is named on #227 |
| #102 (hub #225) | its comments that say the gate holds an inherited Fs until confirmed (`diagnostics_panel.py:1255`, `project_view.py:65-66`) become stale — text only | with our tag |
| #101 (hub #224) | nothing to build; every TCC tag from now on stays signed, betas included | — |
| #105 | nothing for W-5: the "as is" block reaches TCC through the skill's plan. Later (3.2): a window for the transcription `setup_import` takes | — |
| the release | pin skill v3.0.65 in its next release | after our tag |

## Built (2026-10-01, branch `wave-2026-10-01`)

All eight tasks, #108 added on the Arbiter's word after the plan (S-085: a tag that is not release-shaped was picked
and installed unchecked). #101, #103, #106 and #107 were built by four agents in worktrees and brought onto the
branch by this session (the role guard refuses a commit in a tree under `hub/`); #102, #104, #105, #108 here. A
second model (Fable) reviewed the two places where a mistake costs most: the installers' signature check (one
finding — the same hole as #108) and the ledger's channel keys (three edge cases, fixed in `67642ea`). The full
suite found one flaky selftest outside the wave (`upkeep`'s `describe` between two tags on one commit), fixed in
`0edd429`.

**Before the tag:** the Arbiter's runs of the installers on the Windows VM and on the Mac — `install.ps1` has only
been read. TCC's half after the tag: `--model` (hub #226), the reopening event (hub #227), the stale comment on the
pre-sweep gate (hub #225), and the vendored skill pinned to v3.0.65.
