# PLAN W-12 · v3.3.0 — #210, the critical fixes and the four returned features, without the engine

**The composition, the Arbiter 2026-11-08:** 15 issues, the minor `v3.3.0` (milestone `W-12 · v3.3.0`). Earlier that day it was 11 issues and the patch
`v3.2.1` («так, патч»), with #200, #201, #202 and #204 sent to the pool; the patch is dropped and the four are back. **The order:** build everything with no
release tag → a release candidate → TCC does its work on it (hub #331, SKL-091) → when TCC is done, the minors, skill `v3.3.0` and TCC `v1.3.0`. No ear test by
the Arbiter before the candidate.

**Status:** written 2026-10-30 on branch `wave-2026-10-30` from three code maps (sonnet · medium, at `393fcf2`). Codex's plan review at `9daab88` (report: `hub/scratch/skill/codex-w12-plan-report.md`): each finding checked at its main site and taken in (not every line of its inventories). T2's #200 half, T3, T6 and T7 came back after it; Gemini 4 and an Opus seat reviewed them side by side while Codex was out of tokens, each finding checked at its main site (`docs/W-12-LEDGER.md`). The Arbiter, 2026-10-30: «збір закінчено» → 14 issues on `W-12 · v3.2.1` (#196–#209), `ok` on all 14 (first
the fixes and TCC's asks, then «це треба брати!» for the five features: the freeze of 2026-10-21, hub #295 HUB-090, is
lifted for this wave by his word). «Пиши план, план збережемо і будемо робити в новій сесії»: the build starts in a new
session, after the plan review and his «го». Built without `superpowers` (hub H-022): the PR carries `Engine: none`;
the ledger is `docs/W-12-LEDGER.md` (started with the build).

Paths: `SK` = `skills/autosound-tuning`, `RT` = `SK/rew_tool`, `S` = `RT/state/state.py`, `A` = `RT/state/apply.py`,
`P` = `RT/state/process.py`, `N` = `RT/naming.py`, `V` = `RT/verify.py`, `C` = `RT/contract.py`, `PR` =
`RT/project_repo.py`, `AI` = `SK/scripts/autosound_ai.py`, `IC` = `scripts/installer-consistency.py`. TCC = the tcc tree,
`src/autosound_tcc`. Line numbers are the maps' at `393fcf2`; an implementer re-reads before editing.

## Open questions for the Arbiter — before «го»

None. Answered by the Arbiter 2026-11-08: #210's three (lane F's section), and the three the return of the four reopened: **#200** by hand, checked against the saved preset when the skill can read one (below, T2); **#201** a dated, sourced record (T3); **#204** the session sends, TCC's button is the spare (T7).

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
- **A silent reviewer:** 20 minutes without a report → the next one at once (code: Codex → the Opus seat),
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
  **The Arbiter, 2026-11-08, after a side-by-side on T2, T3, T6, T7 (`docs/W-12-LEDGER.md`): «для коду беремо Опус. Джемені на переклади і роздумʼя, пошук ідей». Wherever this plan says Codex for a code pass, read one Opus seat (`feature-dev:code-reviewer`, opus · high, the whole tree).** Gemini 4 (`gemini-4-argon-high`) takes translations, thinking-through and ideas.
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
| **A** | `S`, `A`, `RT/state/schema.md`, `RT/levelbase.py`, `RT/predict.py` (T2's readers) | T1 #199 → T2 #197 + #200 → T3 #201 |
| **B** | `P`, `N`, `V`, `C`, `RT/CONTRACT.md`, `RT/rew_api.py` (read), `PR`, `RT/project_seed.py`, the three references of T5 | T4 #203 → T5 #198 → T7 #204 → T6 #202 |
| **D** | `install.sh`, `install.ps1`, `IC`, `FAQ*.md` (one line) | T8 #205 → T9 #206 |
| **E** | `AI`, `README*.md`, `SK/SKILL.md`, `SK/references/**`, `RT/capabilities.py`, `scripts/docs-check.py` | T10–T13 |
| **F** | `RT/joint_search.py`, `RT/version_bench.py`, `SK/references/phases/joint-by-joint.md`, then `RT/intake.py`, `RT/intake_i18n/*`, `RT/state/process.py` (`_route_line`), `SK/SKILL.md` (Map row), `project-intake.md`, `capture-session-sheet.md`, `virtual-first.md`, `capabilities.md`, `rew-tool-docs.md` | T14 #210 → T15 → T16, after lane E |

**F's new modules run after E; its edits to `P` and `capture-session-sheet.md` wait for B as well.** B's three reference edits (T5) and F's `scripts/selftests.txt` and `reading-cost-baseline.json` belong to the lanes' file lists. T4 first in lane B: TCC builds against it in its own W-12, and it settles `P`'s exit table. Lane E's `SK/SKILL.md` edit (T12) runs while no other agent edits it.

## Group Versions ledger — `Risk: high`, lane A

**T1 · #199 — `propose` after an unplaced candidate.** S.
`A` `_propose` loads HEAD (`current = history.load()`, `A`:535) whatever the newest version is; a candidate is banked
with `place=False` (`A`:567-568), so «candidate + fix» lands on HEAD in silence. Build: `propose(…, on=None)` and the
CLI `--on <version|HEAD>`. With no `on`, when the slot's newest version is an unplaced candidate (`variant ==
"candidate"`, not HEAD), **refuse**: «the newest version v_002 is a candidate not in the slot; this delta would land on
HEAD v_001 — pass --on v_002 to build on the candidate, or --on HEAD». With `on`, load that version and pass
`parent=<it>` to `snapshot` (`S`:1308, `parent` exists). The sheet header (`settings_sheet`, `A`:359-368) names the
base: «v_003 = v_002 + …». **Promotion, the blocker of the plan review.** With `--on <candidate>`: `structural_moves` is measured against the candidate's own base (HEAD at its making), not the candidate, so
its unreviewed moves stay held (`A`:547-557 compares only the last step today); the result stays a candidate until evidence and a reviewer are there, and then every row
`candidate` becomes `proposed` and `variant` is cleared (no branch clears it today, `A`:563-568), so `attest` (`A`:622-625) covers them. The sheet is measured against what is in the DSP, the
last placed version, because «Enter only these» (`A`:371-372) on candidate → fix would leave out the candidate's changes. `parent` holds on both layouts (`S`:1344-1346 sets it only under `project_line`).
The refusal reaches a person as the CLI's `error: …` on stderr, exit 1 (`A`:1274-1276); TCC calls no `apply.propose` and hands a request to the model. `parent` stays the true base (TCC's
`ledger_line.parent_of`). Tests: `A --selftest` — a refused propose after a candidate (red on the old code); candidate + small fix with and without evidence and a reviewer; `attest` after it; the whole
entry sheet; the header line; `parent` on both layouts.

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
naming grammar's `+FX` (`N`) and the references say it means RealCenter; no alias for the other two. Loudness between versions: T14's `version_bench.py loudness` reads the field. TCC: an unknown top-level non-tier key is ignored (tcc `state/dsp_state.py` `ProjectView.from_dict`); its
tab is hub #324 (SKL-090), and the field shape goes to TCC on #324 when T2 closes. Tests: `S selftest` — validate
accepts and refuses shapes, diff and render with and without; `A --selftest` — a trim is a row with no reviewer.
Docs: `RT/state/schema.md`, the naming reference where `+FX` is defined.

**The Arbiter on #200, 2026-11-08: the tier is Audiotec Fischer's** («специфіка тільки ATF»), Helix and its kin. The fields beyond `input_gain_db` are filled only on a DSP whose profile names them (`effects_and_dynamics`, `RT/dsp_profile.py:209`); on any other DSP nobody sees them. That is the method's text: `validate` and the renderers get no profile. They are filled by the session or the person; **when the skill can read a saved preset it checks them against it**, and until then the check is the screen (`screen-read-dsp.md`). No file reader in this wave. The raw state before the capture is T15's.

**Its write path and consumers, from the plan review.** `preset_settings` is not a tier, so a delta today becomes a channel delta and fails on `_MERGEABLE` (`A`:142-144, :216-222): the delta path takes it explicitly.
The diff keeps the existing envelope and the writers and renderers handle it by name (`S`:1429-1451; the CLI's walk `S`:1594-1606 assumes channel → field). A master trim is decided at each reader, once: verification (`S`:1050-1059), the capture-level
comparison (`RT/levelbase.py:369-380`, called from `P`:3791-3797), the prediction (`chains_from_snapshot(snap, trim=False)`, `RT/predict.py:757-763`: off by default, so the engine, `eq_propose.py:1020` and `path_check.py:518` stay as they are, the engine's candidates carrying no trim either, `resonalyze_engine.py:1463`; on for the `predict` view and the bench, once, never on both tiers), TCC's proposal view (the generic `settings` rows, tcc `state/proposal_view.py:51-61`). `version_bench.py loudness` reads it.
Added tests: trim-only and mixed deltas; missing = 0; non-zero → 0; two versions that differ only by the trim, in the prediction (the bench's case is T14's, which comes later); `attest` after a trim-only proposal.

**The representation, from the Critic (Gemini 4).** In a diff the whole field goes under `out["preset"]` as one key, `preset_settings: (old, new)`: every tier walk already skips `preset` (`A`:350, `S`:1594, `RT/levelbase.py:373`), the sheet and `delta_rows` print it by name, and `_WHOLE_PRESET` gets the key, so a trim reads as every band changed (`RT/levelbase.py:369`). In a delta it is taken out before `_split_by_tier` (`A`:142-144 would wrap it under channels) and merged two levels deep, so one `fx` field does not wipe the others. It carries its own `status`, `proposed` → `applied` by `attest`, which flips only tier rows (`A`:622-625). `_fmt_val` and `_FIELD_LABEL` (`A`:331, :344) learn its dB fields.

**From the Opus seat.** The source file is `preset_settings.source_file`, not `provenance.source_file`: `propose`'s only door replaces the whole `provenance` and switches off the structural hold (`A`:541, :549), and `provenance` may be a string. It is dropped by `propose`, since a new version was not compared to that file, kept by `attest`, and given by a new `attest --source-file`. `_LEDGER_NON_TIERS` (`RT/project.py:821`) gets the key. **Not harmless to an older copy:** `SCHEMA_VERSION` stays 3, so a 3.2 copy reads the dict as a tier and refuses the float (tcc vendor `state/state.py:163`, `:461`). It fails loud, only on a project a newer copy has written, in a minor: `### Upgrading` says so, and a project bound to an older copy (tcc `core/method_cli.py:337`) moves up before using the field.

**T3 · #201 — «in the DSP now».** M. After the Arbiter's answer to question 2; as advised: `slots.json`
`slots[slot].loaded = {version, since, source}`, additive (TCC reads `slots.json` and watches it — `slots()` must still
read `{}` on a half-written file); written by `attest` (`A`:610-628, under the same lock) and by `state.py loaded`;
`slots.json` keeps one writer (the method). `schema.md` AD-1: one paragraph — HEAD is the pointer, `loaded` is a dated
claim with its source, neither is a mirror. `loaded` is written only on a project-line ledger (`S`:741, :1268): a `slots.json` beside per-preset folders makes the ledger unreadable (`S`:624) and switches TCC's layout (tcc `state/ledger_line.py:51`). `config save` (`S`:736-760) writes it too. It names the newly banked version, which equals HEAD (`A`:627). The `{}` on a half-written file is TCC's reader only: the skill's writers do not fall back to it. Answer hub #325 with the field. Tests: `S selftest` (the verb, the attest write, `config save`, no `slots.json` on the old layout), `C selftest` if the CONTINUE check reads HEAD (`C`:1010, :3534).

Group passes: Codex on the lane's diff; one fix round; the narrow check of fixes (the trial above).

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
   null`, set where «frequency/impulse response unreadable» is made (`V`:229-231, :286-288) by a mapping, because `rew_api.rew_state` is `None` for an `HTTPError` (`RT/rew_api.py:169-177`): an
   `HTTPError` is `"error"`, the state `unavailable` is `"unavailable"`, a programming error and `protocol`/`config` stay out of the field (`null`), and `_no_impulse` (`V`:124-132) stays what it is, no failure. All sites: `V`:108-121, :158-159, :223-232, :281-288, `P`:3344-3348, :3369-3392.
   Stored with the check in `round["checks"]` and `taken[…]["verified"]`, **and additively in the `capture_verified` event** (`P`:3516-3542), since after the next round the history has only that (`P`:2958-2961; tcc `state/process_view.py:442-449`). The final locked check (`P`:3461-3467) stays. The
   issue text stays (TCC may match it — grep tcc `unreadable` first).
4. `RT/CONTRACT.md` §3 (:105) and §10 (:592) headings out of «planned (W-10)» — the bodies already say «as built»;
   `"rew_state(exc)"` added to `IMPORTABLE`'s `rew_api.py` tuple (`C`:121-129; defined `RT/rew_api.py:168-177`); §9's
   row stays as it says.
Tests: `P selftest` — `--round` refused on a moved round for each verb (red first), `_check_exit_table`,
`_check_flags_tcc_sends`, `_check_unknown_flags`, check → close → open another round → replay keeps `rew`; `V selftest` — the `rew` field for an HTTP error, unavailable, a malformed answer, an expected missing impulse and a programming error, on both curve reads; `C selftest`; `contract-guard`.
Then a comment on hub #297 with the flags and the field for TCC's #218/#219.

**T5 · #198 — the p1–p9 points as their own group.** S.
`N`: `KIND_POINTS` and the label «Points» (`N`:892-897); `place_in_groups` (`N`:945-971) puts a parsed position `p1`…`p9`
into `points`, and **`x0` stays with the tripod** (`N`:87-88: it is a position too). One setup identity (tripod sweeps · hand-held sweeps · RTA) replaces the method-only partition and count (`N`:935-942), and `"sw"`/`"rta"` stay the method values; a late points group is placed in order, not appended (`N`:964-969). `_last_method_taken` (`P`:1242 on) uses the same identity; order solo → group → points → rta. The tripod → hand-held
switch is written where switches are rendered: `render_round_list` (`P`:1215-1235) and `setup["switches"]`
(`P`:2270) — «<- switch: tripod → hand-held». `expected_groups`' signature stays (`IMPORTABLE`). The «four columns at
most» text becomes five in `N`:888-891, `references/core/naming-and-structure.md:113`, `why-these-rules.md:139`,
`phases/capture-session-sheet.md:43`. TCC: `_round_groups` keeps `label, method, names` — a new group shows as a column
without TCC code; its fallback `groups_from_titles` (rounds without `groups`) still groups by method — said to TCC in one
bus comment when T5 closes, no ticket unless TCC asks. Tests: `N selftest` (`N`:1695-1750 — the order and the label, no prior setup, starting from either method, late optional points, `x0` on the tripod),
`P selftest` (`rnd["groups"]` ~12060-12101).

**T7 · #204 — `project_repo.py save` and `status`.** M.
`PR` has `init` and `status` only (`PR`:233-253); `status` returns `{repo, remote, gh, init, offer}` (`PR`:129-143),
which TCC requires (tcc `core/project_repo.py:84-109`) — kept, keys added. Build: (1) `save <project> [--dry-run]`:
commit the tuning files with the method's message, push; refuse with a reason — nothing to send, no remote, the remote
ahead (pull first); never `.claude/skills/autosound-tuning`. (2) `status --json` adds `changes: {tuning: […],
housekeeping: […]}`, `ahead: [{hash, time, subject}]`, `remote_head: {hash, time}`, `sends` (question 3). The
housekeeping list is new (`.sessions.log`, `.tcc/`, `*.tmp`, …) beside `GITIGNORE_LINES` (`RT/project_seed.py:~267-285`);
the `.claude/skills/autosound-tuning` link goes into the seeded `.gitignore` and `init`'s `git add -A` stops taking it.
**`save`, from the Critic (Gemini 4).** It stages only `changes.tuning`, never `git add -A` (`PR`:119 would take `.sessions.log`, which the seed does not ignore, and the skill link on an older repo). The order: no remote → fetch → the remote ahead refuses → commit → push; all checks before any commit, so a refusal and `--dry-run` change nothing. Nothing new to commit but commits not pushed is a push, not «nothing to send». `status`'s early return for a folder with no repo (`PR`:134-137) carries the new keys empty.

**From the Opus seat.** The network stays out of `status`: `status_lines` runs at every `contract.py check` and TCC's GUI thread waits on it (`RT/contract.py:406`, tcc `ui/tcc/main_window.py:2924`), so `status --json` reads the last-known tracking ref and says when it was fetched; `--fetch` and `save` go to the network. `save` gives the push ten minutes, as TCC does (tcc `core/project_repo.py:25`; `_git` has 60 s, `PR`:42). A push that fails after the commit names the commit and says it is not sent, and the next `save` pushes it; a test with a remote that refuses. `save` excludes the link and `.sessions.log` itself, since the seed leaves an existing `.gitignore` alone (`RT/project_seed.py:384`), and untracks a link already tracked. `sends` is `"session"` when either seeded file has the rule line. The identity comes from `_identity_for_this_repo` (`PR`:114); a refusal is exit 1 with its line; a held git lock answers as a refusal.

**Who sends (the Arbiter, 2026-11-08): the session; TCC's button is the spare.** The rule goes into the project seed (`project_seed.py`'s `CLAUDE.md`/`AGENTS.md`): commit and push after each banked version and at session close when a remote exists; `status --json` `sends` is `"session"` for a project seeded with it, `"person"` otherwise.
`status_lines` (used by `contract.py check`) unchanged when there is nothing to report. Tests: `PR --selftest` with
`AUTOSOUND_NO_GH=1` and a bare local remote (save, refusals, dry-run, the link excluded — red first);
`project_seed.py --selftest`. Then a comment on hub #326 for TCC's button.

**T6 · #202 — a step's note.** M.
`add_step` (`P`:1876-1926) gains `note=None` = `{do, expect, if_not}`, kept in the step entry and in `step_added`;
the CLI `add-step --note-do/--note-expect/--note-if-not` (`VERB_FLAGS` `P`:4493). The answer: `finish_step`
(`P`:1944-2003) takes `--heard "<the Arbiter's words>"`, kept as `note.answer` beside `expect`. A decision tied to a step does not fill it: its question may be about anything, and `record_decision` stays journal-only (`P`:3913, the step positional, `P`:12298). `session-close` (`P`:12304-12363) lists steps with an
`expect` and no `answer` as owed lines — **not** owed for the exit code (TCC reads the exit as the answer): printed
only. A step with no note gets one when `--heard` lands, and `--heard` also goes into `step_done` (`P`:2001). A redo clears the old answer (`P`:1936). The owed lines read the plan, because `open_work` carries only steps in progress (`P`:4010): in progress or done, never todo or skipped; they print apart from `lines`, so the clean stop's own line stays (`P`:12345). The flag also goes in `"done": ()` (`P`:4495), `_FLAG_TAKES_VALUE` (`P`:4525) and the parsing at `P`:12252, which takes every word as evidence. `state/process-schema.md` documents the shape. TCC reads none of these keys (its `_to_step` reads a fixed list) —
additive; hub #312 (PAS-019) gets the shape when T6 closes. Tests: `P selftest` — the note kept, the answer kept, the
close lines; the flag guards.

Group passes: Codex on lanes B and C's diff; one fix round; the narrow check of fixes (the trial above).

Group passes: Codex on lane B's diff; one fix round; the narrow check of fixes (the trial above).

## Group Installers — `Risk: high`, lane D

**T8 · #205 — Flash (High) and run-together lines.** S.
First the Arbiter's re-check: a one-line probe of `gemini-3.8-flash-high` under ADC (`agy`, 3 tries, timed); the
result in the ledger. Still silent → `install.sh:2475-2477`, `install.ps1:2556-2558` and `FAQ*.md:117` name the tier
the guides name (`SK/references/tooling/setup-critic-channel.md:66`: Flash Medium) and separate «Pro not offered where
you are» from the ADC reviewer. Answers → the text stays, the ledger says why. Lines: the paths differ, so a fixture with no final line break comes first, at the real boundary: live upstream `install.ps1:532`, captured `:527`, winget captured `:1177` (shown by `Warn` `:1185`), uv through `Run` `:1305`, `:2145`, the wrapper `:488-493`. The fix is a host-only line break at the boundary that proves it; the wrapper keeps its Boolean and the exit code. Claude Code's «✔» mojibake is its own, not touched. Tests: `IC` (the ps1 case runs on CI's
Windows job).

**T9 · #206 — a running TCC during the macOS update.** S.
`install.ps1:2040-2044` already refuses on a running TCC («Close it and run this line again»); `install.sh` has nothing.
Build the same on macOS before the app block (`install.sh` ~:1920, before `uv tool install … --upgrade` at :2024):
`pgrep -f autosound-tcc` → a warning naming the command to close it, the app left as it is, `DRY_RUN` respected. No
`pkill` by the installer: a hung process is the user's to end, and the line says how. Tests: `IC` `app_problems`
(`IC`:1554) with a stand-in `pgrep` **and its own macOS case**, because that harness sets `on_mac() { return 1; }` (`IC`:1589): TCC running, neither `uv tool install` nor `--install-desktop` runs; TCC not running; dry-run (red first).

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
selftest, by the research table's own three classes (`docs/RESEARCH-2026-10-25-rew-quantities.md`): a quantity a tool reads → that module; waterfall/CSD, spectrogram, RT60 → REW's own view, said as such; coherence → an explicit «not read», not the arrival search; «ringing» does not land first on `verify.py`. `SK/SKILL.md:148` names the quantities; the playbook's ringing row
(`references/core/analysis-playbook.md:12`) names `ear_suspects.py` and the diagnostics page. The non-interactive
report stays out (a feature, not asked). Checks: `capabilities.py --selftest`, `doc-commands-check`, `docs-check`,
`reading-cost` (SKILL.md's budget).

**T13 · #207 — README «3.1».** XS (Sonnet trial). Line 16 of `README.md`, `README.uk.md`, `README.de.md`, `README.pl.md`:
«3.1» → «3.x» in each language's own sentence; grep `FAQ*.md` for the same claim. Check: `i18n-check`, `docs-check`.

Group review: Gemini reads the changed user-facing lines (README, SKILL.md row, test-tracks line) once.

## Group Joint-by-joint approach — `Risk: high`, lane F (#210)

**Design, 2026-11-08** (three code maps, each claim that carries a decision re-checked against the code). Codex read it at `95abb06`: 14 findings, each
checked at its main site and taken in, one in part (the caches it found absent exist in the local project, outside git); the report is `hub/scratch/skill/codex-210-report.md`. The build waits for the plan
review and the Arbiter's «го».

**The Arbiter's answers (2026-11-08).** (1) «це один з двух шляхів (другий через бібліотеки Resonalyze) - користувач може вибрати
як йти, або зробити два підаходи і вибрати найкращий результат»: two paths, and a third choice of running both. (2) The method
holds for any stack: «навіть з переднім сабом можна робити. і 2 смуги вирівнювання спрацює теж». (3) `mosqito` is optional.

**The source is the project's GitHub head, not the local copy.** The local `car/passat-b8-2026_afterAYAfinal` stands at `dc68111`;
`rev-list` over `dc68111..4d4f845` (`gh api …/compare`) is 58 commits. The earlier «13 scripts» came from the old copy and is wrong
both ways:
- Not part of it: `gate.py` (the aya-merge entry gate) and `levelbase.py` (the round's level base; `RT/levelbase.py` exists).
- Missing from it: `stage_sym.py` (the symmetric variant), `stage_v6.py` (the blend, the woofer's share), `lr_tracking.py` (L vs R phase,
  the chain's and the electrical part's), `centre_timing.py` (its `gd_ms`), `s4_6b_vs_model.py:161-168` (a sum against the complex sum of
  its solos), `rta5_vs_epy.py` (the 1.66 / 1.90 rms 80 Hz–10 kHz).
- The decay figures of #210 have no script at the head: `stage_v6.py:8` names a `diag` that is not in the file. The definition is
  in `docs/2026-10-29-variant6-analysis.md:11` (−20 dB, 1/3 oct), which is `ear_suspects.ringdown_ms`'s default.

**The shape: one search engine and a joint table, not a port of each script.** The scripts repeat one skeleton (leak test → crossing →
a shortlist → scoring on the points → dip → re-score the joint below) and differ in band, window, pruning and metric; `fit_eq` exists in three
copies. A port script by script keeps that and the car in the code. Extending `xover_select.select_neighbor_pair` does not fit: it takes
ready branches, one point, and scores against the house curve.

Two new modules, numpy + scipy, not in `IMPORTABLE`:

**`RT/joint_search.py`.** Read-only analysis: prints the table, `--json`, `--out DIR`. It never banks and never picks.
- *Joints from roles.* The stack is `xover_wishes.ROLE_ORDER` over the channels present; each adjacent pair is one joint. 3-way + sub, 2-way +
  sub and a front sub are the same code. A sub joins the summed L+R of the next role, with one front delay and the L−R offset held. The delay is
  searched both ways and reported as which side takes it: `delay.max_ms` bounds it, and «the sub delayed, not the front» was this car's
  result, not a rule (front sub).
- *The space from the project.* Families `dsp_math.options_for`, corners from `crossover_filters` snapped to its step (a public wrapper over
  `xover_wishes._profile_xo`), gain `dsp_profile.gain_range_db`, delay `predict._profile_limits`, Fs `xover_wishes._fs_of`. A missing Fs or an
  unreadable profile refuses in one line, exit 3. This drops the scripts' LR48, which the Helix does not offer (`swws_xo.py:32-33`).
- *The input.* Solos at the points through `predict.load_solo_*`, by a new all-channels loader that keeps `info` (IR, timing, protection), since `ellipsoid.load_positions_*` drop it (`ellipsoid.py:80-81`); the protective filter comes out once, by
  `predict.de_embed_solos` from the round's record, and its refusal is passed on as it stands. One capture session is assumed: curves from two sessions
  refuse unless `--level-step <band>` names the control band, since a session's offset otherwise reads as a driver's imbalance. A front driver without
  the nine points refuses; `--single-point` runs on the centre point and marks every row. A sub may stay at one point while its crossing is under 100 Hz
  (λ > 3.4 m, `swws_xo.py:69`), a front sub included; above that it needs the points.
- *The grid is the joint's, not the hardware's.* The Helix allows 20–20,480 Hz in 1 Hz steps, which is ~121 billion pairs. Corner bounds per joint from a
  role table, overridable by flags (bass 40–125 Hz, woofer↔mid 150–600, mid↔tweeter LP 1.6–5 kHz and HP 2–5 kHz), in 1/6-oct steps snapped to the
  profile's, then ±1/12 oct around the shortlist: ~10 × 10 corners × 17² families ≈ 29,000 pairs a joint. The count is printed before the run, and over a
  ceiling it refuses without a flag. Run time is measured in slice 1 and goes in the ledger.
- *Method constants, named at the top with their source:* ±30°; dip −3.5 dB; leak −24 dB an octave out (bass: −24 at 100 Hz and −30 over 125–200 Hz,
  `swws_search2.py:44`); HP floors 1.45 × Fs (mid, the run's value) and 2 × Fs (tweeter, `crossover_checks.fs_margin`); the bass re-score −0.1 oct;
  the L and R acoustic crossings within 1/3 oct (`stage_lock.py:217`). The run's 4.5 kHz ceiling was its 3–4″ mid: a project bound, `--max-crossing`, off by default.
- *The metric follows each candidate's acoustic crossing.* Under 1 kHz, on the 5/500 ms window: the ±30° band through the crossing, worst then median of
  the points, then the summation loss (`dsp_math.sum_loss`). From 1 kHz, on the 1/4 ms window (it reads from 1 kHz up, `mt_search.py:14-15`): the power sum
  over the points, then the worst of the left-ear, right-ear and centre groups must not cancel, then the flattest response to the target. A joint whose
  bounds straddle 1 kHz gets two lists, one per class, because their scores do not compare; a candidate whose ±½ oct scoring band itself crosses 1 kHz is scored in the upper class, on the band clipped at 1 kHz, and marked.
- *The ear groups.* The run's groups were fixed by hand after reading the arrivals (`mt_search.py:264-267`). The rule here: at each point the L−R arrival of the mids and of the tweeters (`windows.arrival_between`, 1–4 kHz),
  minus the centre points' mean of the same pair; both below −0.1 ms left, both above +0.1 ms right; between, or the two pairs disagreeing, unassigned. A group needs two points; otherwise only the nine-point
  sum applies and the output says so. Centre stays p1/p5/p9.
- *Shortlists by joint class.* Bass: all pairs on the reference point, vectorised over delay, then the best per crossing band on every point. Woofer↔mid and
  above: every pair that passes the leak test on both sides is scored on all the points with its delay curve kept (`stage_lock.py:157-159`,
  `stage_sym.py:88-96`), because the L−R conditions couple the sides and a one-point shortlist can lose the only pair that meets them. Curves are held in float32, chunked by family pair; the top 200 per crossing band per side survive; the count is capped by the same ceiling as the grid.
- *Align first:* `--align` runs one flatten on the points' power mean, replacing the three `fit_eq` copies: gain up ≤ 6 dB and ≤ 4 cuts of ≤ 6 dB against the
  target, then the channel put back to its own passband level, so only the shape changes (`wm_flat.py:83-90`). The fit and anchor bands are a role table, overridable (woofer 100–560 / 100–200 Hz, mid 200–1250 / 700–1500, upper-joint mid 1250–5000, tweeter 1600–10000 / 5000–10000, sub 25–130). A channel left outside the gain range brings every
  channel down alike (`global_trim_db`, `wm_flat.py:184`), not a cap per channel, which took one side to 0 oct; both ends of the range are checked. Cross-first is
  compared with the same EQ budget on the sum (`wm_flat.py:115-130`). `dsp_math.greedy_eq_fit` is not it: it fits a residual with a boost budget.
- *Stage conditions, only on real L/R pairs, on by default, each with a flag off:* the signed rule is (delay L − delay R) = −(raw arrival L − raw arrival R)
  ± 0.10 ms at the centre points (raw m-L − m-R −1.37 → DSP +1.37, `stage_lock.py:7-12`); the same absolute polarity L and R; the same family and order L and
  R. Corners may differ per side only with a flag. A single sub is one branch, with no L/R rule.
- *Carried upward:* `--fixed <joint.json>` holds the joints below and re-scores them, the mid↔tweeter search too, which the scripts did not. Recovery exists for
  the bass joint only, by the sub's delay and polarity, the knob that leaves the rest in place (`wm_search.py:189-198`); any other joint that falls past its limit
  rejects the candidate.
- *The blend:* `--move lower|upper` says which group's delay moves. The group above moves as one: the tweeter keeps its relative delay and flips with the mid
  (`stage_v6.py:129-138`). A delay outside 0…`max_ms` rejects the candidate.
- *Decay:* `ear_suspects.ringdown_ms` of each raw driver, once per driver, from the impulse (`keep_ir=True`). Per candidate: the lower driver's share where it rings
  ≥ 1.5× longer, and the filter's group delay there (`stage_v6.py:193`), both as the issue's explanation of the blend. Reported, not ranked.

**`RT/version_bench.py`.** Compares whole ledger versions, whichever path built them, so the Resonalyze path, the joint path and both in one
table need nothing more. Versions on different point coverage refuse rather than compare. Subcommands: `table` (`predict.predict` per version → `predict.to_json` (`terms` reads that shape) → `variant_front.terms`
→ `front`'s picks on its four terms, with no argmax; a term missing for any version is named and fewer than two comparable terms print no pick (`variant_front.py:183,197-198`); the joint widths, ear sums, decay, share and L/R phase are shown beside them and take no part in the picks, and
a term that cannot be computed is named); `loudness` (Zwicker through a lazy `mosqito` import; absent, it prints the install line and gives ISO 226 at 80 phon, labelled as less
exact when versions differ in the bass); `lr-phase` (L vs R, 250–800 Hz, phase and group-delay difference, acoustic and electrical, centre and nine points, as `lr_tracking.py`);
`round-check` (each tripod sum against the complex sum of its solos: rms and maximum over 1/3-oct bands, no offset removed, as `s4_6b_vs_model.py:165-168`; over 1 dB rms is
flagged as a working threshold, not as `verify_prediction`'s validated criterion, which means something else).

**Out of this wave, said in the runbook:** a tool for the five-sum RTA discriminator (not in #210's list; the step is described); the centre's delay
(the existing steps run after the joints); a preset decoder (#200: the runbook falls back to `screen-read-dsp.md`); a tool for the blend, which is a
re-run with `--fixed` and `--move`.

**T14 · the tools, in four slices** (the plan had three: the bench is its own). Each adds a line to `scripts/selftests.txt`, a board row in
`core/capabilities.md` (en/uk) and an entry in `rew-tool-docs.md`.
1. Engine and the bass joint: roles, the space from the profile, stage conditions.
2. Woofer↔mid: `--align`, decay, `--fixed`, `--move`.
3. Above 1 kHz: the power sum, the ear groups, the short window.
4. `version_bench.py`.

Tests, red on behaviour and not on a missing import, each on synthetic curves whose best variant is known by construction (the `xover_select` selftest's form), with a
score margin or a named equivalence set where flat drivers tie: the search finds a planted delay, polarity and corner pair; a family outside the profile is never returned;
a missing Fs refuses; a 2-way, a front sub and a single sub give the right joints; the L−R condition rejects the planted best when it breaks the offset; a one-point
shortlist would lose the pair the coupled search keeps; a bass joint that falls is recovered and one that cannot be is rejected; the upper group survives a `--move`; a delay
past the ceiling rejects; a group that cancels is rejected from 1 kHz while the nine-point sum passes, with ear groups inferred from planted arrivals and an ambiguous set falling back;
a straddling joint gives two lists; missing points refuse. Bench: `lr-phase` and `round-check` on planted differences; ISO 226 and, where `mosqito` is present, a Zwicker match on a
known level step; without it the install line and the label; two versions differing only by T2's trim; `table` on planted versions, including a term missing for one. T16: all three choices, an absent legacy value, save and reload, `_route_line` under all three modes.

**The replay, a session's check and not CI, with an adapter in the session's scratch:** the local caches `scripts/results/{swws_raw_0615,joint_wm_raw,mt_raw}.npz` (outside git;
complex responses on three grids, protective filters still in, two sessions, no impulses, so decay is not replayable from them). Two separate claims, because the conditions
were added after the first search and exclude its best (`docs/2026-10-26-swws-analysis.md:116-132`). Without the leak and dip conditions, the score of banked candidate B is
reproduced within 0.05 oct. With them, candidate C (BW36 60 / BE24 90, 0.98 / 1.00 oct) is in the top 10, within 0.1 oct of the run's best. Results in the ledger.

**T15 · the runbook, `SK/references/phases/joint-by-joint.md`,** in the phase files' form (Goal-node, then steps). It holds what the path needs, the capture,
the order of joints, align-then-cross, the search and metric per joint, the conditions, the tournament and the blend, «both paths», the three lessons from
the ear. It replaces the desk steps of Phases 1–2 only; 0, 3 and 4 stay. **One full raw capture for every project, whichever path** (the Arbiter, 2026-11-08: «знімати все що потрібно щоб мати сиру машину для всіх варіацій
проекта далі»; the same capture served more than ten desk variants on the Passat). Nothing the engine reads differs: it takes the tripod solos (`resonalyze_engine.py:1446`), and the joints need
those plus the points. So block B of `capture-session-sheet.md` (and `virtual-first.md:131-132`) lists the nine points for every front driver and the centre, tweeters included, as the
default; on a 3-way + centre that is 63 sweeps against the sheet's 36. This changes the sheet's «the ellipsoid is the one optional part» of 2026-10-02: it can still be cut for time, and the sheet
then names the cost: the engine loses nothing, the joints only run with `--single-point`. The sub may stay at one point (above). **The order (the Arbiter, 2026-11-08):** either block may go first; what holds is that all tripod sweeps are one block and the RTA with the nine points another, since those are taken by hand (T5's order keeps it). **The nine points get a fixed order, written out by the skill** in the sheet and the runbook, because the sheet's «yours to fix» left even the Arbiter having to recall it; TCC shows it as a picture or GIF (to TCC on hub #331). The order (the Arbiter's words, 2026-11-08), a hand-held path in the vertical plane in front of the nose, parallel to the windscreen: p1 at the centre, then left (p2), up (p3), down (p4), back to the nose (p5), right (p6), up (p7), down (p8), back to the nose (p9). Each step is 10–15 cm (down: twice that), written so in the sheet, the runbook and TCC's picture in place of the sheet's ±9 / ±7 cm; the Arbiter: the point is to keep them alike between sets, they cannot be exact, and what is read from them is relative. So p2–p4 are the left side, p6–p8 the right, p1/p5/p9 the centre: the ear groups follow from the order, and the arrival rule checks it. **The raw state before the capture** (the Arbiter, 2026-11-08), added to the `v0` preset of the sheet (:12) and `phase_0_baseline.md:61`: every enhancer, filter and EQ off, protective filters on, equal levels in the DSP, and preferably the amplifier gains already set (the method does not do that part: say so, any AI can advise how). On an Audiotec Fischer DSP the list is named from the profile (RealCenter, Dynamic Bass, SubXpander, RTC, input levels), for another DSP it is the general sentence; a readable save is checked, otherwise the screen. **A refusal is the person's, informed** (the Arbiter, 2026-11-08): the session says the limits in words before the capture, and the decision is recorded with them
(`record_decision`; `_positions_asked`, `process.py:455-479`, already counts it). `joint_search.py --single-point` needs that record and refuses without it. The round itself: the sheet's recipe adds the titles on the `capture-start` line (the existing door, sheet :43), and its loopback timing line moves above block B, because `predict.load_solo_rew` refuses a sweep off the loopback base (`predict.py:550-553`). Light touch has no capture session (`virtual-first.md:56-57`) and is not offered the joints. Test: the same capture list for all three approaches and after changing the approach, tweeters, centre and the sub exception included. Steps through `add_step`, source `skill`, phase 1; TCC renders an unknown step id
(`state/process_view.py:610-635`). It stays outside `reading-cost`'s `ORDERED` and is read when the path is chosen, so the budget does not count this path's reading; the runbook
says so at its head. Gemini reads it. English only: `i18n-check` does not cover `references/`.

**T16 · the offer at the first step.** A new field beside `goal.design_path`, because this is a choice inside the desk half, with the same three
requirements as virtual-first: `goal.desk_approach`, enum `joint_by_joint | resonalyze_engine | both`, `writes="project:goal.desk_approach"`, `when="now"`
(asked at the project's start, at the desk; the capture does not depend on it, so it can still be changed after the capture), no default: the person picks. Its note says what each needs and gives: several DSP memories, reading a
saved preset back, time for A/B; a ranked set with the reasons, against the engine's front; both = more time, and the best of two. It also states the
evidence: one car, 3-way + centre + sub. `_route_line` dispatches on mode × approach instead of its one fixed sentence (`process.py:989-992`): an improved car on the engine keeps
today's line; with joints it names block X and the runbook; both names both; a new tune names the runbook only for joints or both; an absent value keeps today's behaviour; light touch adds nothing. Labels in
`intake_i18n/{en,uk,de,pl}.json`, the three through the Advisor. `project-intake.md` §4 gets the offer. **`SK/SKILL.md` only a Reference Map row:** before the Map it holds 17,416 of 17,500 bytes
(`docs-check` rule 17). `reading-cost-baseline.json` is rewritten in that commit, as its own visible diff. The archived way stays unoffered and `DESIGN_PATHS` is not touched.

**One order of phases, two ways of doing the desk.** The decision of 2026-09-09 that there is one path, which `docs-check` enforces (`ONE_PATH_BANNER` in four phase files, `TWO_PATHS`), stays:
−1, 0, desk, 3, 4 is one order, and nothing in the new text says «If Phase −1 chose». The Arbiter's two paths are inside the desk. `virtual-first.md`'s desk section (:48-50 and §1.3) gets one
sentence: the desk runs the engine, the joints or both, per `goal.desk_approach`, and the current tune is a candidate on either.

**TCC:** no code. The form is the skill's page (`core/intake_form.py:71`), and TCC reads neither `goal.mode` nor a route. At T16's close one ticket to TCC says
so and asks whether its first step should name the two paths.

Group passes: Codex per slice of T14, one fix round each; the narrow check of fixes (the trial above). T15–T16's text: Gemini.

## The end of the wave

1. The bookkeeping on the branch: `## [v3.3.0]` from `## [Unreleased]` with its
   Upgrading (T1's refusal and `--on`, T2's `preset_settings`, T4's `--round` and `rew` field, #210's tools and the new
   route), `plugin.json`, `INSTALLER_VERSION`/`$InstallerVersion`; Gemini reads the
   CHANGELOG entry.
2. Codex on the head of `main..wave-2026-10-30`, after the bookkeeping; one fix round; **Fable** on those fixes only.
3. One PR with `Engine: none` → its full CI on every system → acceptance (the trial above) → **the release candidate**, announced on hub #331. No release tag yet.
4. TCC does its W-12 (`v1.3.0`) on the candidate. Fixes it asks for ride on the branch, as a new candidate.
5. When TCC is done, **both minors through the `release` role** (`WAVES.md`, the minor pair: skill `v3.3.0`, then TCC pins it, then `v1.3.0`). Receipts on hub #297, #303, #313, #325, #326 name the tag.

## Cost

15 issues in 16 tasks, five groups. An estimate under the trial; the ledger measures it, and nothing here includes the first measured search time (slice 1).

- **Claude agent runs ~30**: implementers 14 (T10/T11 by the session; T14 is four), #210's design 3 (spent), the group fix rounds
  and narrow checks ~10, the final fix and Fable's check 2, the bookkeeping 1, acceptance 1.
- **Codex calls ~10**: the plan review, #210's design, three group passes, T14's four slices, the final pass on the head.
- **Advisor (Gemini) calls ~6**: the text group, the CHANGELOG, the FAQ line, translations if the README line needs one, the runbook and intake text, the three intake translations in one batch. While Codex is out, its calls above go to Gemini 4.

Time: lane F is the critical path, after lane E. All together ~9 h of machine time, plus the stops.

## The first steps of the new session

1. `bin/ticket queue` — the wave block shows 11 `ОК`.
2. Read this plan; #210's design (lane F's section) first, its questions to the Arbiter with advice.
3. The plan review by Codex (the brief: this file + the three maps' facts it cites); findings checked and taken in.
4. His «го» → lanes A–E as above; the ledger `docs/W-12-LEDGER.md` from the first run.
