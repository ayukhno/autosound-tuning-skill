# PLAN W-12 · v3.2.1 — #210 and the critical fixes, without the engine

**The composition, the Arbiter 2026-11-08 («так, патч»):** 11 issues, a patch. #210 joined with `ok`; #200, #201, #202
and #204 went back to the pool for the next wave (their plan text, tasks T2–T3, T6, T7 and questions 1–3, is at `1f33687`);
the question of the version is closed: `v3.2.1`.

**Status:** written 2026-10-30 on branch `wave-2026-10-30` from three code maps (sonnet · medium, at `393fcf2`); not yet
reviewed. The Arbiter, 2026-10-30: «збір закінчено» → 14 issues on `W-12 · v3.2.1` (#196–#209), `ok` on all 14 (first
the fixes and TCC's asks, then «це треба брати!» for the five features: the freeze of 2026-10-21, hub #295 HUB-090, is
lifted for this wave by his word). «Пиши план, план збережемо і будемо робити в новій сесії»: the build starts in a new
session, after the plan review and his «го». Built without `superpowers` (hub H-022): the PR carries `Engine: none`;
the ledger is `docs/W-12-LEDGER.md` (started with the build).

Paths: `SK` = `skills/autosound-tuning`, `RT` = `SK/rew_tool`, `S` = `RT/state/state.py`, `A` = `RT/state/apply.py`,
`P` = `RT/state/process.py`, `N` = `RT/naming.py`, `V` = `RT/verify.py`, `C` = `RT/contract.py`, `PR` =
`RT/project_repo.py`, `AI` = `SK/scripts/autosound_ai.py`, `IC` = `scripts/installer-consistency.py`. TCC = the tcc tree,
`src/autosound_tcc`. Line numbers are the maps' at `393fcf2`; an implementer re-reads before editing.

## Open questions for the Arbiter — before «го»

None. #210's design may raise some: they come with its advice, before its build.

## The W-12 trial: the PMO method's review weight, and the numbers (the Arbiter, 2026-11-08)

«так пробуємо і збираємо статистику». The skill only: TCC's W-12 keeps the standing weight, so the two halves of one wave
are the comparison. It decides whether this weight goes into the PMO cube. Where it differs from `hub:seam` «Process
weight», it holds for W-12. It replaces the full per-task loop on `Risk: high` (the user's word 2026-10-14) by his word,
and keeps the part of that loop that paid: the check of fixes (9 regressions in ~43 re-reviews, 5 user-facing).

- **Per task:** the implementer; on `Risk: high` a test first, red on the old code. No task review, no per-task re-review.
- **Per group, at most two passes on its shared diff.** Pass 1: Codex, read-only, fresh context; its brief: no finding
  without a `file:line` quote, an inventory of every site of each class it finds, a «checked → clean» row per category.
  One fix round. Pass 2, only when a fix touched `Risk: high` code: a narrow check of the fixes (opus · high), on pass 1's
  classes only. A third pass is the Arbiter's word.
- **A silent reviewer:** 20 minutes without a report → the next one at once (code: Codex → the Opus seats, never Gemini),
  the reason in the ledger. W-11 lost 44 minutes to one.
- **The end of the wave:** Codex on the branch head after the bookkeeping, one fix round, then Fable on those fixes only.
- **A finding's place:** W-12 reaches people. Stops the main process → blocks the release; hinders, with a workaround →
  fixed before the release, or the Arbiter's word; a rare case → the backlog, named in the act.
- **Acceptance:** a fresh session on the exact PR head. It reads the reviews and CI instead of repeating them, marks each
  issue's asks done / no / not checked with a quote, installs the candidate into a clean HOME and runs it as a person
  would, and fills «who found what». It decides nothing for the Arbiter; the session commits its act.

**`docs/W-12-LEDGER.md`, from the first run:**

| what | columns |
|---|---|
| per group | Claude runs by model and effort, wall clock, commits, fix commits |
| per external reviewer (Codex, Gemini) | calls, minutes, silences, findings, real after the check against the code, false, real ones no other seat found, severity |
| CI | runs by workflow, minutes, each red by cause (product · test · runner), what it found that no local check had |
| who found what | stage, found, critical, its fate. The alarm: a critical found only in acceptance, or by a person after the tag |
| the estimate | ~30 runs and ~9 h for this composition; against the standing weight, per task, and against TCC's W-12 |

At the wave's end the numbers go to the hub as one ticket, for the Arbiter's review between waves.

## Rules for every task

- **Weight by risk:** the trial above. Ordinary code: one test per behaviour the issue asks for. Text: `docs-check`, no
  new tests, at most one review.
- **The seats.** Plan review, group passes, the final pass on the head: Codex (`codex exec -m gpt-6-astra -c
  model_reasoning_effort=high -s read-only --ephemeral -o <file> -`, the brief on stdin). Codex out of limits or silent →
  the Opus seats (`pr-review-toolkit:silent-failure-hunter`, `pr-review-toolkit:pr-test-analyzer`, opus · high).
  User-facing text (README, FAQ, the CHANGELOG, the method's text) → Gemini via the Advisor (`AI ask --model
  gemini-3.8-flash-medium`). Every finding is checked against the code before acting.
- **Models** (`hub:seam` «Models by role»): implementer `Risk: high` opus · high; ordinary opus · medium; T13 is a
  Sonnet trial (sonnet · medium); T12 and T14 are mechanical — the Haiku-against-Sonnet trial (haiku · high on T12,
  sonnet · medium on T14). XS items the session may build itself.
- **Tests**: the changed modules' selftests (`python3 <module> <argv from scripts/selftests.txt>`), `IC` for installer
  work, `scripts/docs-check.py`, `scripts/i18n-check.py`, `scripts/doc-commands-check.py`, `scripts/reading-cost.py`
  for text, `scripts/contract-guard.py` (plain and `--selftest`) for anything touching `C`. No local full suite: once,
  on the PR's CI. A new test fails on the old code; the report shows the red run. Behaviour, not timing. The `.ps1`
  cases of `IC` need PowerShell; on the Mac they skip — CI's Windows job runs them (do not install `pwsh`).
- **Contract 1**: every name in `C` `IMPORTABLE` keeps its signature (`scripts/contract-guard.py`); additions only. A
  new key in a state file or a returned dict is an addition (CONTRACT.md §12).
- **What TCC reads stays** (from the maps): snapshot keys `preset` (the slot name, a string), `sample_rate`, `version`,
  `note`, `target`, `features`, `slot_label`, `save`, `channels`, the profile's tiers, per-row `status`, `created`,
  `parent`, `schema_version`; `slots.json` `slots[slot].{version, dsp_preset}`, `configs[…]`; process steps `id, name,
  status, source, skip, attempt, covers, evidence`; the events `step_added`, `step_done`, `user_decision`;
  `round["groups"][].{label, method, names}`; `project_repo.py status --json` keys `repo, remote, gh, init, offer`;
  TCC's `_REW_ANSWERED` prefixes (`core/process_writer.py:201-203`); exit codes 1/69/70/75; `PROTOCOL = 1`.
- **One tree, one branch** (`wave-2026-10-30`, the main tree). Lanes run in parallel only on disjoint files; an
  implementer commits only its own paths, never `-A`. Implementers do not touch `CHANGELOG.md`: the session writes each
  group's bullets under `## [Unreleased]` when the group closes. Commit messages in English, each names its issue.

## Lanes and order

| lane | files | tasks, in order |
|---|---|---|
| **A** | `S`, `A`, `RT/state/schema.md` | T1 #199 → T2 #197 |
| **B** | `P`, `N`, `V`, `C`, `RT/CONTRACT.md`, `RT/rew_api.py` (read) | T4 #203 → T5 #198 |
| **D** | `install.sh`, `install.ps1`, `IC`, `FAQ*.md` (one line) | T8 #205 → T9 #206 |
| **E** | `AI`, `README*.md`, `SK/SKILL.md`, `SK/references/**`, `RT/capabilities.py`, `scripts/docs-check.py` | T10–T13 |
| **F** | new modules under `RT/`, a new runbook under `SK/references/`, then `SK/SKILL.md`, `project-intake.md` | T14 #210 → T15 → T16, after lane E |

T4 first in lane B: TCC builds against it in its own W-12, and it settles `P`'s exit table. Lane E's `SK/SKILL.md` edit (T12) runs while no other agent edits it.

## Group Versions ledger — `Risk: high`, lane A

**T1 · #199 — `propose` after an unplaced candidate.** S.
`A` `_propose` loads HEAD (`current = history.load()`, `A`:535) whatever the newest version is; a candidate is banked
with `place=False` (`A`:567-568), so «candidate + fix» lands on HEAD in silence. Build: `propose(…, on=None)` and the
CLI `--on <version|HEAD>`. With no `on`, when the slot's newest version is an unplaced candidate (`variant ==
"candidate"`, not HEAD), **refuse**: «the newest version v_002 is a candidate not in the slot; this delta would land on
HEAD v_001 — pass --on v_002 to build on the candidate, or --on HEAD». With `on`, load that version and pass
`parent=<it>` to `snapshot` (`S`:1308, `parent` exists). The sheet header (`settings_sheet`, `A`:359-368) names the
base: «v_003 = v_002 + …». TCC: `propose` refusals reach it as a `ValueError` («the method's gate», tcc
`ui/tcc/main_window.py:2100, 2673, 2785`) — check the message shows whole; `parent` stays the true base (TCC's
`ledger_line.parent_of`). Tests: `A --selftest` — a refused propose after a candidate (red on the old code), `--on`
building on the candidate with `parent` set, the header line.

**T2 · #197 — a version keeps its input gain.** S.
Key: **`preset_settings`** (a top-level dict; `preset` is taken by the slot name, and a dict outside `_NON_TIER_KEYS` would
be read as a tier — `S`:136-165), added to `_NON_TIER_KEYS` and validated on its own. Only `input_gain_db` for now, default
0 dB, never asked for; #200 adds its fields to the same key in its wave. No migration, `SCHEMA_VERSION` stays 3. Shown by
`diff_states` (`S`:1421-1453), `render_state` (`S`:1471-1583) and `settings_sheet`/`delta_rows` (`A`:325-432) only when set
or different; a change is an ordinary row, `structural_moves` (`A`:72-90) does not count it, so no reviewer. TCC ignores an
unknown top-level non-tier key (tcc `state/dsp_state.py` `ProjectView.from_dict`). Tests: `S selftest` — validate accepts
and refuses, diff and render with and without; `A --selftest` — a trim is a row with no reviewer. Docs: `RT/state/schema.md`.

Group passes: Codex on the lane's diff; one fix round; the narrow check of fixes (the trial above).

## Group TCC contract — `Risk: high`, lane B

**T4 · #203 — four guarantees.** M.
1. `--round <id>` on `capture-check`, `capture-taken`, `capture-protective` (the issue's record-capture /
   set-protective). `record_capture` (`P`:2528) and `set_protective` (`P`:2633) gain `round_id=None`; with it,
   `_require_capture(round_id)` (`P`:3852-3870) inside the method's own lock raises `_RoundMoved` (exit 1, «round X was
   closed or replaced … -- nothing was written»). `check_captures` takes `round_id` already. `VERB_FLAGS` and
   `_FLAG_TAKES_VALUE` (`P`:~4493-4536) get `--round`; `_TCC_FLAGS` (`P`:7214) lists it.
2. The REW-error lines (`P` `_main` ~12940-12960: `error: REW answered with an error: …`; `_refuse_rew_state`
   `P`:1311-1326: `REW's measurement list was not read …`) pinned as fixed prefixes in `RT/CONTRACT.md` §2's exit-1 row
   (no new exit code: TCC already matches three prefixes, tcc `core/process_writer.py:201-203`).
3. A recorded verdict says REW answered an error: `V`'s skeleton (`V`:158-179) gains `rew: "error" | "unavailable" |
   null`, set where «frequency/impulse response unreadable» is made (`V`:229-231, :286-288) from `rew_api.rew_state`;
   stored with the check in `round["checks"]` and `taken[…]["verified"]` (`P` ~3300-3500 — read before editing). The
   issue text stays (TCC may match it — grep tcc `unreadable` first).
4. `RT/CONTRACT.md` §3 (:105) and §10 (:592) headings out of «planned (W-10)» — the bodies already say «as built»;
   `"rew_state(exc)"` added to `IMPORTABLE`'s `rew_api.py` tuple (`C`:121-129; defined `RT/rew_api.py:168-177`); §9's
   row stays as it says.
Tests: `P selftest` — `--round` refused on a moved round for each verb (red first), `_check_exit_table`,
`_check_flags_tcc_sends`, `_check_unknown_flags`; `V selftest` — the `rew` field; `C selftest`; `contract-guard`.
Then a comment on hub #297 with the flags and the field for TCC's #218/#219.

**T5 · #198 — the p1–p9 points as their own group.** S.
`N`: `KIND_POINTS` and the label «Points» (`N`:892-897); `place_in_groups` (`N`:945-971) puts a parsed position
(`parse_name`'s `position`, `N`:142-145, :566) into `points`; order solo → group → points → rta. The tripod → hand-held
switch is written where switches are rendered: `render_round_list` (`P`:1215-1235) and `setup["switches"]`
(`P`:2270) — «<- switch: tripod → hand-held». `expected_groups`' signature stays (`IMPORTABLE`). The «four columns at
most» text becomes five in `N`:888-891, `references/core/naming-and-structure.md:113`, `why-these-rules.md:139`,
`phases/capture-session-sheet.md:43`. TCC: `_round_groups` keeps `label, method, names` — a new group shows as a column
without TCC code; its fallback `groups_from_titles` (rounds without `groups`) still groups by method — said to TCC in one
bus comment when T5 closes, no ticket unless TCC asks. Tests: `N selftest` (`N`:1695-1750 — the order and the label),
`P selftest` (`rnd["groups"]` ~12060-12101).

Group passes: Codex on lane B's diff; one fix round; the narrow check of fixes (the trial above).

## Group Installers — `Risk: high`, lane D

**T8 · #205 — Flash (High) and run-together lines.** S.
First the Arbiter's re-check: a one-line probe of `gemini-3.8-flash-high` under ADC (`agy`, 3 tries, timed); the
result in the ledger. Still silent → `install.sh:2475-2477`, `install.ps1:2556-2558` and `FAQ*.md:117` name the tier
the guides name (`SK/references/tooling/setup-critic-channel.md:66`: Flash Medium) and separate «Pro not offered where
you are» from the ADC reviewer. Answers → the text stays, the ledger says why. Lines: `Invoke-Upstream`
(`install.ps1:514-535`) ends the relayed child's output with a line break (`Write-Host ""` after `Out-Host` when the
last chunk has none); Claude Code's «✔» mojibake is its own, not touched. Tests: `IC` (the ps1 case runs on CI's
Windows job).

**T9 · #206 — a running TCC during the macOS update.** S.
`install.ps1:2040-2044` already refuses on a running TCC («Close it and run this line again»); `install.sh` has nothing.
Build the same on macOS before the app block (`install.sh` ~:1920, before `uv tool install … --upgrade` at :2024):
`pgrep -f autosound-tcc` → a warning naming the command to close it, the app left as it is, `DRY_RUN` respected. No
`pkill` by the installer: a hung process is the user's to end, and the line says how. Tests: `IC` `app_problems`
(`IC`:1554) with a stand-in `pgrep` (red first).

Group seat: one (a small risky diff) — Codex.

## Group Texts and small fixes — ordinary / docs, lane E

**T10 · #209 — the agy announcement.** XS. `AI`:6245 `{PROBE_WAIT_S}` → `{probe_wait()}`; check the line is not reached
when `probe_wait()` is 0. Test: `AI selftest` with `AUTOSOUND_PROBE_TIMEOUT` set (stderr names its value). Session.

**T11 · #196 — the EMMA reference.** XS. `SK/references/core/project-intake.md:151` → `test-tracks.md` `EMMA/positions`
(EMMA 2026 tr.2–6); one line in `SK/references/patterns/test-tracks.md` near :26-35: a competition-disc track from a
project profile is matched to a row with its year, and a missing or contradicting year is said to the user. The
optional `docs-check` rule: a track id (`EMMA/…`) named in `references/` resolves to a row of `test-tracks.md` — a new
`_check_*` with a selftest case (one test). Session.

**T12 · #208 — THD and ringing from the entry points.** S (Haiku trial, the brief holds the text).
`SK/references/core/capabilities.md`: the distortion row's words (THD, harmonics), a ringing / decay / waterfall / CSD /
RT60 / дзвін / затухання row → `ear_suspects.py` ring-down, REW's waterfall, `references/core/enclosure-install-diagnostics.md`;
a single-measurement report row (`rew_tool.py` with no arguments — it passes `check()`'s module test). `RT/capabilities.py`
selftest: `find()` of each quantity in `docs/RESEARCH-2026-10-25-rew-quantities.md` §1 names the intended module, and
«ringing» does not land first on `verify.py`. `SK/SKILL.md:148` names the quantities; the playbook's ringing row
(`references/core/analysis-playbook.md:12`) names `ear_suspects.py` and the diagnostics page. The non-interactive
report stays out (a feature, not asked). Checks: `capabilities.py --selftest`, `doc-commands-check`, `docs-check`,
`reading-cost` (SKILL.md's budget).

**T13 · #207 — README «3.1».** XS (Sonnet trial). Line 16 of `README.md`, `README.uk.md`, `README.de.md`, `README.pl.md`:
«3.1» → «3.x» in each language's own sentence; grep `FAQ*.md` for the same claim. Check: `i18n-check`, `docs-check`.

Group review: Gemini reads the changed user-facing lines (README, SKILL.md row, test-tracks line) once.

## Group Joint-by-joint approach — `Risk: high`, lane F (#210)

The wave's only new feature, and the only part not yet designed. **Before the build:** `feature-dev:feature-dev` — a code
map of the Passat project's `scripts/` against `RT/`, architects only if there is more than one way; the result replaces
this section and goes through Codex like the rest of the plan.

What is known. The tools exist as 13 scripts, ~2560 lines, numpy and `dsp_math`: `swws_search2`, `swws_xo`, `swws_epy`,
`swws_flat`, `swws_gd_thd` (sub↔woofer); `wm_search`, `joint_wm`, `wm_flat` (woofer↔mid); `mt_search` (mid↔tweeter);
`stage_lock`, `loudness_match`, `levelbase`, `gate` (conditions, loudness, the round check). They were written for one car,
so **the port is a generalisation**: channel names, Fs floors, the DSP's filter families, gain and delay limits come from
the project's profile, not from the code.

**T14 · the tools into `RT/`, in three slices** (bass joint · woofer↔mid with flatten-first and decay · mid↔tweeter on the
nine-point power sum), each with the stage conditions as options, the L-vs-R phase metric, the loudness match of versions
and the round-level check of a tripod sum against the complex sum of its solos. Registered in `RT/capabilities.py`.
Tests: a selftest per slice on a synthetic set of curves whose best variant is known, red first.

**T15 · the runbook** under `SK/references/`: the order of joints, align-then-cross, the search space and metric per joint,
the conditions carried upward, the tournament and the blend, the three lessons from the ear. Gemini reads it; the uk/de/pl
versions through the Advisor if the route names them.

**T16 · the offer at the first step**, by name, next to the Resonalyze path, with what it needs and what the user gets
(`project-intake.md`, `SK/SKILL.md`, within `reading-cost`). The approach archived by the Arbiter is not offered. #210 needs a
way to read back a saved preset, and the skill has none: the runbook names the need and falls back to reading the screen
(`screen-read-dsp.md`); a decoder stays with #200. Whether TCC's first step changes is asked on the bus ticket to TCC.

Group passes: Codex per slice of T14, one fix round each; the narrow check of fixes (the trial above).

## The end of the wave

1. The bookkeeping on the branch: `## [v3.2.1]` from `## [Unreleased]` with its
   Upgrading (T1's refusal and `--on`, T2's `preset_settings`, T4's `--round` and `rew` field, #210's tools and the new
   route), `plugin.json`, `INSTALLER_VERSION`/`$InstallerVersion`; Gemini reads the
   CHANGELOG entry.
2. Codex on the head of `main..wave-2026-10-30`, after the bookkeeping; one fix round; **Fable** on those fixes only.
3. One PR with `Engine: none` → its full CI on every system → acceptance (the trial above) → `git merge --ff-only` → the
   tag `v3.2.1` on that commit. The skill's own patch: it does not wait for TCC's wave; TCC pins the published tag. Receipts
   on hub #297, #303 name the tag; hub #313, #325, #326 are deferred to the next wave.

## Cost

11 issues in 13 tasks, five groups. An estimate under the trial; the ledger measures it.

- **Claude agent runs ~30**: implementers 13 (T10/T11 by the session; T14 is three), #210's design ~3, the group fix rounds
  and narrow checks ~10, the final fix and Fable's check 2, the bookkeeping 1, acceptance 1.
- **Codex calls ~9**: the plan review, #210's design, three group passes, T14's three slices, the final pass on the head.
- **Advisor (Gemini) calls ~4**: the text group, the CHANGELOG, the FAQ line, translations if the README line needs one.

Time: lane F is the critical path, after lane E. All together ~9 h of machine time, plus the stops.

## The first steps of the new session

1. `bin/ticket queue` — the wave block shows 11 `ОК`.
2. Read this plan; #210's design (lane F's section) first, its questions to the Arbiter with advice.
3. The plan review by Codex (the brief: this file + the three maps' facts it cites); findings checked and taken in.
4. His «го» → lanes A–E as above; the ledger `docs/W-12-LEDGER.md` from the first run.
