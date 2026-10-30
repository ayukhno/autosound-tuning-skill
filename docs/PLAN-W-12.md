# PLAN W-12 · v3.2.1 — fixes, TCC's two asks and five features, without the engine

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

Each has the session's advice; the build follows the advice unless he says otherwise.

1. **#200 — the `.pct6` decoder.** The skill has no decoder (only prose; `SK/references/tooling/screen-read-dsp.md`
   calls the file encrypted). The issue wants `attest` to fill and check the tier from a decoded file «once the decoder
   is in the skill». **Advice:** W-12 builds the tier, its diff/sheet rows and the source-file provenance fields, filled
   by the session or the user; bringing a decoder into the skill is its own task for a later wave, on his word. Then
   `screen-read-dsp.md`'s «encrypted» line is left as it is in W-12.
2. **#201 — «in the DSP now».** AD-1 (`RT/state/schema.md:111-114`) says the ledger is not a device mirror. **Advice:**
   the method records a dated, sourced *claim*, not a mirror: per slot in `slots.json`, `loaded: {version, since,
   source}` with `source` one of `attest` · `pct6` · `user`, written by `attest` and by a new verb `state.py loaded
   <slot> <version> --source user`; never inferred from file times. HEAD keeps its meaning: the slot's pointer, the
   newest placed version, which may be `proposed` and not in the DSP. AD-1 gets one paragraph saying so; TCC draws «in
   the DSP» from `loaded` only (hub #325's answer).
3. **#204 — who sends.** No rule in the skill says the session commits and pushes after every step (the map found
   none). **Advice:** the rule is written into the project seed (`project_seed.py`'s project `CLAUDE.md`/`AGENTS.md`):
   the session commits and pushes after each banked version and at session-close when a remote exists; `status --json`
   carries `sends: "session"` for a project seeded with the rule, `"person"` otherwise.
4. **The version.** Five features in a patch. **Advice:** keep `v3.2.1` while building; the name is settled at the
   release with TCC (a minor `v3.3.0` pairs with a TCC `v1.3.0`, `RELEASE-CHANNEL.md` §3.1; TCC's wave is `W-12 · v1.2.2`).

## Rules for every task

- **Weight by risk** (`hub:seam` «Process weight»). `Risk: high`: a test first, red on the old code → implementer →
  task review (opus · high) → one fix round → re-review of the fix. Ordinary code: one test per behaviour the issue
  asks for, no task review. Text: `docs-check`, no new tests, at most one review. Each group ends with its seats on the
  shared diff and one fix round. ONE final branch review.
- **The seats (the Codex trial, W-11's design).** Plan review, group seats, final branch review: Codex (`codex exec -m
  gpt-6-astra -c model_reasoning_effort=high -s read-only --ephemeral -o <file> -`, the brief on stdin). On the first
  `Risk: high` group (Versions ledger) the two Opus seats (`pr-review-toolkit:silent-failure-hunter`,
  `pr-review-toolkit:pr-test-analyzer`, opus · high) run beside it, to compare. Codex out of limits → the Opus seats.
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
| **A** | `S`, `A`, `RT/state/schema.md`, `RT/state/migrate.py` (read) | T1 #199 → T2 #197+#200 → T3 #201 |
| **B** | `P`, `N`, `V`, `C`, `RT/CONTRACT.md`, `RT/state/process-schema.md`, `RT/rew_api.py` (read) | T4 #203 → T5 #198 → T6 #202 |
| **C** | `PR`, `RT/project_seed.py` | T7 #204 |
| **D** | `install.sh`, `install.ps1`, `IC`, `FAQ*.md` (one line) | T8 #205 → T9 #206 |
| **E** | `AI`, `README*.md`, `SK/SKILL.md`, `SK/references/**`, `RT/capabilities.py`, `scripts/docs-check.py` | T10–T13 |

T4 first in lane B: TCC builds against it in its own W-12, and it settles `P`'s exit table before T5/T6 add flags.
T3 waits for the Arbiter's answer to question 2. Lane E's `SK/SKILL.md` edit (T12) runs while no other agent edits it.

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

**T2 · #197 + #200 — the preset settings and the source file.** L.
Key: **`preset_settings`** (a top-level dict; `preset` is taken by the slot name, and a dict outside
`_NON_TIER_KEYS` would be read as a tier — `S`:136-165). Added to `_NON_TIER_KEYS` and validated on its own:
`input_gain_db` (#197), `sources: {main, hec, digital}` (dB), `fx: {realcenter, dynamic_bass, subxpander}`, `rtc: {on,
curve}`, `bt: {source, auto_switch}`, `conductor: {sub_lamps}`. Every field optional; a missing field reads as the
default (0 dB, off) **except** `dynamic_bass`/`subxpander` in records that do not state them: unknown, not off (the
tuner's naming). No migration, `SCHEMA_VERSION` stays 3.
`provenance.source_file: {name, path, md5, saved (PC-Tool's root @D), pctool (@V), device (@Dev), read_at,
compared}` — filled by the session or the user (question 1). Shown: `diff_states` (`S`:1421-1453; the scalar list at
:1430 and a dict walk), `render_state` (`S`:1471-1583) and `settings_sheet`/`delta_rows` (`A`:325-432) print a field
only when set or different; a change to it is an ordinary row — `structural_moves` (`A`:72-90) does not count it, so
no reviewer. A delta path for non-tier fields beside `apply_delta`/`_split_by_tier` (`A`:198, :134). Legacy «FX»: the
naming grammar's `+FX` (`N`) and the references say it means RealCenter; no alias for the other two. Loudness between
versions: no such code exists (`RT/equal_loudness.py` is ISO 226 targets) — the field is there for it; nothing to
extend now. TCC: an unknown top-level non-tier key is ignored (tcc `state/dsp_state.py` `ProjectView.from_dict`); its
tab is hub #324 (SKL-090), and the field shape goes to TCC on #324 when T2 closes. Tests: `S selftest` — validate
accepts and refuses shapes, diff and render with and without; `A --selftest` — a trim is a row with no reviewer.
Docs: `RT/state/schema.md`, the naming reference where `+FX` is defined.

**T3 · #201 — «in the DSP now».** M. After the Arbiter's answer to question 2; as advised: `slots.json`
`slots[slot].loaded = {version, since, source}`, additive (TCC reads `slots.json` and watches it — `slots()` must still
read `{}` on a half-written file); written by `attest` (`A`:610-628, under the same lock) and by `state.py loaded`;
`slots.json` keeps one writer (the method). `schema.md` AD-1: one paragraph — HEAD is the pointer, `loaded` is a dated
claim with its source, neither is a mirror. Answer hub #325 with the field. Tests: `S selftest` (the verb, the attest
write, a half-written file), `C selftest` if the CONTINUE check reads HEAD (`C`:1010, :3534).

Group seats: Codex and the two Opus seats beside it (the comparison) on the lane's diff; one fix round.

## Group TCC contract — `Risk: high`, lanes B and C

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

**T7 · #204 — `project_repo.py save` and `status`.** M.
`PR` has `init` and `status` only (`PR`:233-253); `status` returns `{repo, remote, gh, init, offer}` (`PR`:129-143),
which TCC requires (tcc `core/project_repo.py:84-109`) — kept, keys added. Build: (1) `save <project> [--dry-run]`:
commit the tuning files with the method's message, push; refuse with a reason — nothing to send, no remote, the remote
ahead (pull first); never `.claude/skills/autosound-tuning`. (2) `status --json` adds `changes: {tuning: […],
housekeeping: […]}`, `ahead: [{hash, time, subject}]`, `remote_head: {hash, time}`, `sends` (question 3). The
housekeeping list is new (`.sessions.log`, `.tcc/`, `*.tmp`, …) beside `GITIGNORE_LINES` (`RT/project_seed.py:~267-285`);
the `.claude/skills/autosound-tuning` link goes into the seeded `.gitignore` and `init`'s `git add -A` stops taking it.
`status_lines` (used by `contract.py check`) unchanged when there is nothing to report. Tests: `PR --selftest` with
`AUTOSOUND_NO_GH=1` and a bare local remote (save, refusals, dry-run, the link excluded — red first);
`project_seed.py --selftest`. Then a comment on hub #326 for TCC's button.

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

**T6 · #202 — a step's note.** M.
`add_step` (`P`:1876-1926) gains `note=None` = `{do, expect, if_not}`, kept in the step entry and in `step_added`;
the CLI `add-step --note-do/--note-expect/--note-if-not` (`VERB_FLAGS` `P`:4493). The answer: `finish_step`
(`P`:1944-2003) takes `--heard "<the Arbiter's words>"`, kept as `note.answer` beside `expect`; a `decision` with
`--step <id>` (`record_decision`, `P`:3905-3928) fills it too. `session-close` (`P`:12304-12363) lists steps with an
`expect` and no `answer` as owed lines — **not** owed for the exit code (TCC reads the exit as the answer): printed
only. `state/process-schema.md` documents the shape. TCC reads none of these keys (its `_to_step` reads a fixed list) —
additive; hub #312 (PAS-019) gets the shape when T6 closes. Tests: `P selftest` — the note kept, the answer kept, the
close lines; the flag guards.

Group seats: Codex on lanes B and C's diff; one fix round.

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

## The end of the wave

1. The bookkeeping on the branch: `## [v3.2.1]` (or the release's name, question 4) from `## [Unreleased]` with its
   Upgrading (T1's refusal and `--on`, T2's `preset_settings`, T3's `loaded`, T4's `--round` and `rew` field, T6's
   flags, T7's `save` and status keys), `plugin.json`, `INSTALLER_VERSION`/`$InstallerVersion`; Gemini reads the
   CHANGELOG entry.
2. The final branch review on `main..wave-2026-10-30`: **Fable** (the wave holds `Risk: high` code), after the
   bookkeeping; one fix round.
3. One PR with `Engine: none` → its full CI on every system → `git merge --ff-only` → the candidate `beta-v3.2.1-rc1`
   on that commit → a ticket to TCC for its run on the candidate (its W-12 builds against T4/T7) → the release with
   TCC through the train. Receipts on hub #297, #303, #313, #325, #326 name the tag.

## Cost

14 issues in 13 tasks, four groups. Roughly:
- **Claude agent runs ~45**: Versions ledger 15 (three `Risk: high` tasks × implementer, review, fix, re-review; the
  Opus seats beside Codex and their fix round), TCC contract 16 (four `Risk: high` tasks; one fix round), Installers 7,
  Texts 3 (T12, T13; T10/T11 by the session), the final review and its fix 2, the bookkeeping 1.
- **Codex calls ~6**: the plan review, three group seats, (the final review is Fable), checks of fixes as needed.
- **Advisor (Gemini) calls ~4**: the text group, the CHANGELOG, the FAQ line, translations if the README line needs one.

Time: lane B is the critical path (T4 → T5 → T6 on `P`, ~5–6 h of machine time), lane A beside it (~4–5 h, T3 after
the Arbiter's answer). With the seats, CI and the bookkeeping: ~9–11 h of wall clock, two days with the stops.

## The first steps of the new session

1. `bin/ticket queue` — the wave block shows 14 `ОК`.
2. Read this plan; get the Arbiter's answers to the four questions above (his words into this file's status).
3. The plan review by Codex (the brief: this file + the three maps' facts it cites); findings checked and taken in.
4. His «го» → lanes A–E as above; the ledger `docs/W-12-LEDGER.md` from the first run.
