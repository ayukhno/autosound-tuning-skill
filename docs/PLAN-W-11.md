# PLAN W-11 · v3.2.0 — the last development wave, without the engine

**Status:** written 2026-10-21 on branch `wave-2026-10-21` from four code maps (sonnet · medium, 10:31–10:41 local);
reviewed by Codex (the W-11 trial, below): 17 findings, 1 blocker and 9 important, each checked against the code
and taken into this text (T1, T2, T4, T5, T7, T8, T10–T12, T14, the lanes, the cost); no finding on T3, T6, T9, T13.
The Arbiter, 2026-10-21: «го»; the control capture — the method adds it itself; #190 taken; the seats on Opus and Gemini, Codex's limits being out.
`ok` on 15 issues (#176–#190). Built without `superpowers` (hub H-022): the PR
carries `Engine: none`; the ledger is `docs/W-11-LEDGER.md`.

Paths: `SK` = `skills/autosound-tuning`, `RT` = `SK/rew_tool`, `P` = `RT/state/process.py`, `V` = `RT/verify.py`,
`AI` = `SK/scripts/autosound_ai.py`, `IC` = `scripts/installer-consistency.py`. Line numbers are the maps' at
`6012290`; an implementer re-reads before editing.

## Rules for every task

- **Weight by risk** (`hub:seam` «Process weight»). `Risk: high`: a test first, red on the old code → implementer →
  task review (opus · high) → one fix round → re-review of the fix. Ordinary code: implementer with one test per
  behaviour the issue asks for, no task review. Text: `docs-check`, no new tests, at most one review. Each group ends
  with its seats on the shared diff and one fix round. The wave ends with ONE final branch review.
- **The seats.** The Codex trial ran this plan's review only: Codex's limits ran out the same day, and the Arbiter
  (2026-10-21, with his «го»): «Кодекс не доступний — закінчились ліміти, тому використовуй Опус або Джеміні». So the
  group seats are the two Opus seats (`pr-review-toolkit:silent-failure-hunter`, `pr-review-toolkit:pr-test-analyzer`,
  opus · high), one seat for a small risky diff, and the final branch review is on opus · high. User-facing text
  (README, FAQ, the description, the CHANGELOG) goes to Gemini through the Advisor (`AI ask --model
  gemini-3.8-flash-high`). Every finding is checked against the code before acting. The ledger counts findings, real
  ones and fix rounds per seat.
- **Models**: implementer `Risk: high` opus · high; ordinary opus · medium; T11 is the Sonnet trial (sonnet · medium,
  beside T10 on opus — the same kind of work, `AI`'s reviewer door); the release bookkeeping's version bumps are the
  Haiku trial against Sonnet (haiku · high and sonnet · medium on one half each, `hub:seam` «Haiku: mechanical only»).
  XS items the session builds itself.
- **Tests**: the changed modules' selftests (`python3 <module> <argv from scripts/selftests.txt>`; `AI selftest` via
  `scripts/run-selftests.sh:407`), `IC` for installer work, `scripts/docs-check.py` and `scripts/i18n-check.py` for
  text. No local full suite: it runs once, on the PR's CI, on every system (`WAVES.md` §1 step 3). A new test fails
  on the old code: the report shows the red run. Behaviour, not timing.
- **Contract 1**: every name in `RT/contract.py` `IMPORTABLE` keeps its signature (`scripts/contract-guard.py` holds
  the literals and their digest). A trailing parameter with a default is allowed; a new key in a returned dict or in
  the state file is an addition (CONTRACT.md §12). `V` `verdict(name, measurements=None, f_low=20, f_high=20000)`
  stays as it is.
- **What TCC reads stays**: `UNUSABLE <title> — `, `OK`/`SKIP`/`N/A` line forms, exit codes 1/69/70/75, the
  `verified` and `capture_verified` keys, `PROTOCOL = 1`, the text probes in tcc `core/method_features.py`.
- **One tree, one branch.** Lanes run in parallel only on disjoint files; an implementer commits only its own paths
  (`git add <paths>`), never `-A`. Implementers do not touch `CHANGELOG.md`: the session writes each group's bullets
  under `## [Unreleased]` when the group closes. Every commit message in English; each commit names its issue.

## Lanes and order

| lane | files | first | then |
|---|---|---|---|
| **A** | `P`, `V`, `RT/contract.py`, `RT/verify_prediction.py`, `RT/compare.py`, `RT/predict.py` (read, tests only), `RT/provenance.py`, new `RT/levelbase.py`, `RT/rew_stub.py`, `RT/testdata/rew/`, `RT/state/process-schema.md`, `scripts/selftests.txt` | Captures T3–T5 | Journal T6, then Rounds and levels T1–T2 (after the Arbiter's answer on the control) |
| **B** | `install.sh`, `install.ps1`, `commands/install-tcc.md`, `IC` | Installers T7–T9 | — |
| **C** | `AI`, `RT/project.py`, `SK/references/tooling/setup-critic-channel.md`, `README*.md`, `FAQ*.md`, `SK/SKILL.md`, `SK/evals/` | Reviewer T10, then T11 (one writer on `AI` at a time), CI T12 | Method text T13, Agent start T14, the test audit T15 (`RT/target_bands.py`) |

Captures go first in lane A: small, they settle `V`'s verdict fields that T1 then extends. T14's eval runs read the
skill from the working tree, so they run while nothing edits `SK/SKILL.md` and no other agent is working: its baseline
first, at a quiet moment, its second set after the description change.

## Group Rounds and levels — `Risk: high`, lane A

**T1 · #176 (hub #285, tcc #198/#220) — rounds on one level base.** L.
The method reads REW's `splOffsetdB` nowhere today (only a comment at `RT/rew_api.py:461`, and a copy into a v7 file
at `RT/resonalyze_ir.py:471`); the jump warning is TCC's alone (tcc #198). Mirrored from the bench's
`car/passat-b8-2026-aya/scripts/levelbase.py`, not invented:
- **One helper, `RT/levelbase.py`** (numpy, loaded lazily as `_load_verifier` is; a line in `scripts/selftests.txt`;
  the guard's `_siblings()` bootstrap): `spl_shift(offset, base_offset)` = their difference (0 when either is
  missing); `to_base(mag, shift)`; `band_offsets(f_cur, m_cur, f_ref, m_ref, bands)` = per band the mean and spread
  of the cur − ref difference over 1/6-octave cells, power mean in ±1/12 oct — the bench's `_band_db` and
  `CONTROL_BANDS` (low 125–500, mid 560–1000, presence 1600–3150, top 4000–10000 Hz); `chain_change(offsets,
  changed)` = the common mean over the bands the round did not change, named a chain change above `DAILY_SPREAD_DB =
  0.7` (the bench's daily spread, 0.5–0.7 dB, its upper end).
- **Only SPL-calibrated readings move** (Codex's plan review, blocker): `splOffsetdB` is REW's SPL calibration, so it
  is in REW's frequency response (`get_fr`, dB SPL) and an RTA, and NOT in an impulse read as a fraction of full scale
  (`RT/rew_api.py:715–735`, `normalised=False`). The sweep path of `RT/verify_prediction.py` (`measured_from_rew` with
  `freqs`, through `predict.load_solo_rew`, L124) and `predict --rew` (`RT/predict.py:558`) read impulses and are not
  shifted; shifting them would invent a residual. Each reader is checked for its unit before it is touched.
- **Recorded**: `V` `verdict` puts `stats["spl_offset_db"]` from the listing's entry (`V:179`, before the early
  returns, so an RTA carries it too); `P` `check_captures` copies it into `verified` and `checks` (`P:3035–3056`)
  and the `capture_verified` event carries `spl_offsets_db` {title: offset} (`P:3125`), the only record that
  survives the round. `capture_rounds()` (`P:2653`) today replays issued/taken events only: it learns to replay the
  offset records too — per title the latest check wins, a partial check adds what it checked, a repeated one replaces.
- **The base**: the project's first round that recorded offsets, or one named: `capture-start --level-base <round>`
  (`VERB_FLAGS` `P:3834`, `_VERB_ARGS` `P:3899`), recorded in the `capture_task_issued` event so it survives the
  close (`P:3231`). A round is named by its id as `capture_rounds()` gives it — not by a ledger version or a series
  number, which are different counters (`P:1886`, `naming-and-structure.md` §1a/§5); either is refused as
  ambiguous, with the round ids listed. A project with no recorded round: this round becomes the base, said so.
- **`capture-check` names the change** (ask 3): `capture.level_base` written beside `capture.session` (`P:3127`) =
  {`status` (`ok` · `no_base` · `missing` · `mixed`), `base_round`, `previous_round`, and per title `offset_db`,
  `to_base_db` (the shift applied: this capture against the base round's offset) and `to_previous_db` (the jump to
  name: against the previous round's)}; a round whose captures agree also carries the one `offset_db`, a `mixed`
  round does not. One line on stdout when any `to_previous_db` is not 0 — a prefix that is none of
  `OK`/`SKIP`/`N/A`/`UNUSABLE`, in the language of the lines around it. Not a refusal: the check's exit is unchanged.
- **Where rounds stand side by side** (ask 1), each says the shift it applied, on SPL readings only: `RT/compare.py`
  `main` shifts each title to the first one's offset (after `get_fr`, L143) and `render` says it;
  `RT/verify_prediction.py`'s FR/RTA path (no `freqs`, `allow_rta`) gets `rew_calibration_db` beside `knob_db` and
  amp; `V` `session_report` compares `mean_dB` on the shifted level when its source is REW's FR and offsets differ
  within one round, and `render_session` says so.
- **The control** (ask 2): the method has no level control across rounds — its `ctl1`/`ctl3` pair (`RT/naming.py:146`)
  is a time-base drift check inside one session. **The method adds it itself** (the Arbiter, 2026-10-21: «Метод
  додає його сам»): `capture-start` puts one optional capture on every round's `optional` list — an RTA of the whole
  system as it plays, in the round's state and at the round's volume (the bench's `ALL+C+FX_N (rta)`; its title from
  `naming`'s grammar for the full system, read in `naming-and-structure.md` first), marked as the round's `control`.
  `capture.level_base.control` = {`title`, `taken`, `verdict` (`same_chain` · `chain_change` · `unattributed` ·
  `not_taken`), `common_db`, per band `mean_db`, `spread_db`, `used`}. Not taken → «chain change not checked», no
  verdict. `band_offsets` on the shifted control against the base round's, over the bands the
  round did not change — taken from the ledger's diff between the base version and the round's (the bands under
  changed EQ filters and crossovers). A chain change is named only when at least two bands survive and their means
  agree within `DAILY_SPREAD_DB` of each other and their common mean exceeds it; then an alignment on those bands is
  offered. A diff that cannot be read, fewer than two surviving bands, or bands that disagree: the difference is
  reported as unattributed — no chain-change verdict.
- TCC's half (tcc #220) shows the base and does no level math: the field shape above goes to TCC as a ticket at «го»,
  so TCC builds against it in its W-11.
Tests first: `RT/levelbase.py`'s own selftest against the bench's numbers (cap_003 → cap_004: +16.65 dB); `V`
selftest, a `_SWEPT_RECORD` with `splOffsetdB` 120.0 → `stats.spl_offset_db`; `P` selftest near `P:7157`: round one
at 103.35 checked, closed, round two at 120.0 checked in a fresh `Process` → `to_previous_db` 16.65, the stdout line,
the journal field; a `mixed` round; a named base that survives the close; a version or series given as the base →
refused; identical impulses under two listing offsets → no shift (`verify_prediction`, `predict --rew`), FR under
two offsets → the shift (`compare`); the control: changed bands left out, no surviving band → unattributed,
nonuniform residuals → unattributed, a uniform +1.2 dB → a chain change. `RT/rew_stub.py` serves `splOffsetdB`
(`Measurement.record()`, L55), and a fixture at 120.0 joins `RT/testdata/rew/` beside 0.0 and 103.35.

**T2 · #177 (hub #260, PAS-013) — unplanned takes' verdict.** S.
Named: `under` and `level` are round-level (`P:1873`, stored `P:2049`), an unplanned take inherits them; `capture-check`
with no titles checks and prints only `expected` (`P:2985`, `P:10192`), so an unplanned take has no verdict until
`capture-close` (`P:10566–10589`). Decision: `capture-check` also checks and prints the round's unplanned takes —
the standing ones, superseded rows filtered and titles canonical, as `_taken_rows` gives them (`P:1182`) — and keeps
them out of the totals, the exit code and `unusable_captures` (`P:3167`): PAS-013's point 3. The «unplanned» mark
stands outside the title TCC parses: after ` — ` in an `UNUSABLE <title> — ` line, and in the same place in the
other forms (the implementer reads TCC's parse, tcc `main_window._on_capture_check_done`, first). Point 2 (three
presets in one round) is the method's rule, not a gap: one round is one DSP state, three presets are three rounds
(`capture-import --bind` for imports); said on the issue, no code. TCC learns the new lines from the receipt.
Tests first: a round with one planned and one unplanned sweep, and a superseded unplanned row → the standing two
printed, exact line forms asserted, the totals and exit planned-only (exit 0 when only the unplanned one is unusable).

Group seats on T1–T2's diff: the two Opus seats, one fix round.

## Group Captures — lane A, first

**T3 · #182 — the AMBIGUOUS issue says the fix.** XS, the session. `P:3019`: the stored issue ends «— keep one: rename
or delete the other in REW»; both spellings stay in it. Test: `_check_a_check_asks_rew_by_key` (`P:7385`) asserts the
fix in `issues[0]` (red before). TCC's fixture `tests/test_measurement_panel.py:2560` holds the old text as data, not
an assertion: named in the receipt.

**T4 · #183 — capture-check judges one snapshot of REW.** S–M, `Risk: high`.
Today: read 1 (`P:3002`, titles → spelling and ambiguity) and read 2 (`P:3021` → `V:291`, uuids and the ordinals the
curves are pulled by). Decision: one listing for both — `_rew_listing` returns the records, and `V`
`verify(names, f_low=20, f_high=20000, measurements=None)` (the real signature, `V:291`, with the new parameter
appended; not `IMPORTABLE`) passes them to `verdict`; the `_main` caller (`V:685`) and the selftest stand-ins that
define `verify(titles)` (`P:8196`, `P:8453`) are called without the keyword, as today. After the curves are pulled the
listing is read once more — two index reads for a successful check — and the title → uuid → ordinal mapping used for
the pulls is compared with it: a moved ordinal, a vanished title or a newly ambiguous one refuses with nothing
written — «REW changed while it was read — run capture-check again» — exit 69, as its own subclass of
`RewUnavailableError` with an attribute that tells it from REW being down. `capture-close`'s inner handler
(`P:10560`, which today swallows `RewUnavailableError` and goes on) lets this one through to `_close_stopped`
(`P:4088`): the close stops, the round stays open, the checks unchanged, and the line says the reconcile landed; an
ordinary offline close behaves as today.
Tests first: a counting stub (`P:7321`'s pattern): two reads on success; a second listing that moves an ordinal with
the uuids unchanged, drops a title, or adds a second spelling → the refusal, nothing in state; `capture-close` on a
moved snapshot → exit 69, the round open, the line naming the landed reconcile; REW down at close → as today.

**T5 · #184 — not-checked says why.** S, ordinary. A `why` key on the verdict at its two producers — `not_a_sweep`
(`V:190`) and `outside_band` (`V:205`) — an addition to the returned dict; `summary` (`V:613`) keeps `not_applicable` as
the total and adds `not_applicable_band`; one helper builds the phrase for `V:538` and `V:712`: «N not checked (not a
sweep)», «N not checked (outside the band)». The reason travels with the session rows (`V:437`) and through
`capture-check --session`'s reconstruction of verdicts (`P:10185`); a legacy row without `why` counts as «not
checked», no reason claimed. TCC does not read the phrase. Tests: `V:1287` and `_check_counts_add_up` (`V:1013`); the
outside-band case at `V:1181–1187`; a mixed session (an RTA and an outside-band sweep) through the process CLI, and a
legacy row.

Group seats on T3–T5: the two Opus seats, one fix round.

## Group Journal — `Risk: high`, lane A

**T6 · #187 (hub #289) — a missed git writes no header.** S.
`_stamp` (`P:3614`): a sha of `""` writes no header when the journal's last header carries a real one — the ask as
written. The cost, said in the CHANGELOG: a move to a copy with no git after a real sha is no longer recorded. `""` on a
fresh journal still gets its header (`P:9513–9515`).
Tests first: in the HUB-002 block (`P:9482–9517`), `_writer_sha` patched to a×40 → `""` → a×40 over three `Process`
runs → one header (red before: three).

One seat (a small risky diff): `silent-failure-hunter`, opus · high.

## Group Installers — `Risk: high`, lane B

**T7 · #179 (hub #280) — a fresh TCC install keeps to the tag's constraints.** S–M.
Mirrors TCC's own updater (tcc `core/updates.py`: `_tag_constraints` L1689–1720, the uv probe in the generated script
L495–531, `TCC_CONSTRAINTS_FROM = (1, 1, 4)` L1681):
- the file comes from the tag the installer already fetched and verified — `check_tcc_tag` (`install.sh:1765–1785`) and
  `Test-TccTag` (`install.ps1:1264–1292`) read `git show refs/tags/<tag>:constraints.txt` (a regular file only) into a
  temp file before they delete their scratch repo; no new download, and the bytes are the signed commit's;
- a tag without it installs as today; a tag at or above v1.1.4 without it warns `nopins` and installs plain; a tag that
  settles by name (no fetch: dry run, a non-release name, `AUTOSOUND_SKIP_TAG_VERIFY=1`, before v0.1.45) installs plain
  and says so;
- before the install, `uv tool install --help` is probed for ` --constraints `; an old uv installs plain, with its
  `uv --version`; never a retry after a failed pinned install (TCC's lesson, `updates.py:332–342`);
- the install line gets `--constraints <file>` (`install.sh:1884`, `install.ps1:1886`); a fallback is a warning, not a
  refusal (`TCC_REFUSED` untouched);
- `commands/install-tcc.md:20–22` (pinned at v1.1.2) gets `--constraints https://raw.githubusercontent.com/ayukhno/autosound-tcc/<tag>/constraints.txt`
  when its pin moves to TCC v1.2.0 in the release bookkeeping; `IC`'s check (`IC:3533–3552`) keeps `--python 3.12` and
  one shared tag.
Tests first (`IC`): the REAL extraction functions — `check_tcc_tag` and `Test-TccTag`, not the stub `app_problems`
puts in their place (`IC:1378`) — run against local tag fixtures (a bare repo with a tag holding the file, one without
it, one holding a directory by that name), and the file's bytes, type and lifetime are asserted; ps1 under PowerShell
where present (`ps1_run_problems`'s pattern), its READ tuple (`IC:1428`) kept. `STUB_UV` answers `tool install
--help` with and without `-c, --constraints` (today its `tool install)` case would «install» on the probe, `IC:1332`)
and records the constraints bytes it was given; new `app_problems` cases — a tag with the file (pinned), a v1.1.3 tag
(plain), a v1.2.0 tag without it (`nopins`, plain), an old uv (plain, said), a pinned install that fails → exactly
one install attempt.

**T8 · #180 — install.ps1 arms the receipt after the change.** S.
Each `Enter-Change` before a download that can fail with nothing changed moves after it, armed on success or when the
binary is left (install.sh's Claude step, `install.sh:1201–1206`): Git (`install.ps1:1070` — on winget's exit 0 or the
downloaded installer's run, armed on `Have git` after `Sync-ProcessPath`), Claude's `Invoke-Upstream` (`:1126`), uv's
(`:1151`), and `uv python install 3.12` (`:1167`, the same class). `:1681`'s blanket arm and install.sh's
`after_method` pin (`IC:2585–2592`) stay. `IC`'s `befores` READ check (`IC:2658–2661`, «within 400 chars above»)
becomes «after the call, before the next step», and RUN cases join `ps1_run_problems` (`IC:2302–2520`) on the
pattern of `claude_step_problems` (`IC:2071–2108`), for Claude, uv, Python and Git: a failed step with nothing left
→ an existing receipt unchanged; a failed step that left its binary → armed; a successful step → armed after the
change.

**T9 · #181 — uninstall removes the empty folders it made.** XS, opus · medium. After the link is removed
(`codex_unlink`, `install.sh:863–876`; `Remove-CodexLink`, `install.ps1:814–831`): `rmdir ~/.agents/skills`, then
`rmdir ~/.agents` — non-recursive, only when empty, never on a dry run. No manifest change (`IC`'s
`_codex_manifest_problems`, `IC:1644`, holds its format). Tests: `CODEX_UNLINK_CASES` (`IC:1535`) — empty folders
gone; a sibling file keeps both; a `.agents` with other content kept; a dry run removes nothing; the ps1 twin in
`ps1_codex_link_problems` (`IC:1820`).

Group seats on T7–T9: the two Opus seats, one fix round.

## Group Reviewer — ordinary, lane C

**T10 · #178 (hub #281, tcc #182) — failure_reason finds Codex's ERROR: line.** XS–S, opus · medium. `AI:1566`: the
prefix is matched case-insensitively, the last such line taken (Codex prints it twice), and when the rest parses as
a JSON object whose `error.message` is a string the reason is that message; otherwise the current block stands — the
line and its continuation up to a blank line or an `at …` frame (`AI:1569`) — as TCC's `core/critic.py:818–836` reads
it. The docstring follows. Tests in `AI selftest` beside the omp case (`AI:4143–4165`): Codex's refusal inlined from
tcc `tests/fixtures/codex-0.162.1-exec-unsupported-model.txt` (paths and ids stripped) → the model's message, not the
banner; a multi-line `ERROR:` block; malformed JSON and a JSON array → the line as it stands.

**T11 · #186 — the reviewer CLIs and stdin: checked, written down.** XS, sonnet · medium (the trial). Found by the map:
every reviewer CLI goes through `_run_child` → `bounded_run`; claude, codex, omp and agy read their prompt from stdin
and get it as a file (`input=`); the gemini fallback takes the prompt by path and gets the null device; none waits on a
terminal. Build: a characterization check — it passes on today's code by design, so the red-before rule does not
apply, and the report says so — at the subprocess boundary: through `_run_child` → `bounded_run` a stand-in child
echoes what it read, and each stdin-reading provider's child receives the prompt, the gemini fallback's receives EOF;
one paragraph in `setup-critic-channel.md` (near `:221`); the CHANGELOG entry says it plainly: «stdin is the prompt or
the null device, never the terminal».

Group seat on T10–T11: one Opus seat (`pr-test-analyzer`).

## Group CI — ordinary, lane C

**T12 · #185 — the two-writers selftest checks behaviour, not speed.** S, opus · medium. `RT/project.py:2396–2448`
races 2 × 40 writes against an unfair 50 ms poller (`write_lock._take`, `:343`) under a fixed 60 s. Rewritten as a
handoff between two PROCESSES, as today (the cross-process coverage stays): writer A pauses inside `update` after its
load (a file signal), B is started and shown to be in contention on the lock (B's probe finds it held), A saves and
releases, and B's update lands on A's — two channels, `project_rev` 2. Deadlines are generous and guard only against
a deadlock; nothing asserts elapsed time (unlike `write_lock`'s `_check_another_thread_waits`, `:602`, which is not
the model to copy). The lock's acquire path is not touched (production, out of scope). Test: the new check, shown red
once with `update`'s hold split between load and save (a local edit, not committed).

## Group Method text — docs, lane C

**T13 · #188 — two visits give the first result.** S, the session; uk/de/pl through the Advisor. The unconditional
claim stands at `README*.md:104` («Two visits make the tune») and `FAQ*.md:120`, and `README*.md:8` («A tune takes two
visits»). English: two visits give the first result; after it the tune improves round by round, as far as you take it.
The «first of two visits» / «second visit» labels (`:102`, `:119`) stay: they are still true of the first result. The
three translations through `AI ask`, then Gemini reads the four; `i18n-check` keeps the skeleton.

## Group Agent start — lane C

**T14 · #189 — the description's recall on a neutral folder.** M, opus · high. Measure first:
`SK/evals/run_trigger_eval.py` on `SK/evals/trigger-eval-set.json` (68 queries: 26 neutral should-fire, 31 neutral
should-not, 11 project) with #170's command (`SK/evals/README.md`, last section), `--model` named, the skill linked from
the working tree and `rew-car-audio-tuning` hidden; **three runs**, since the run-to-run spread is 2–3 queries. The
per-query results go into `SK/evals/` as a file (today only a table, so which 16 missed is not on record). Then the
description (`SK/SKILL.md:3–14`, 1017 of 1024 characters: every added word is paid for by a cut) is rewritten with the
missed query kinds first — resume, de/pl, EMMA, TCC bug reports — and three runs again. Declared before the first
run: the new description stays only if the neutral should-fire recall, summed over the three runs, rises by at least
9 of 78 (three queries a run), the neutral false fires, summed, rise by no more than 3 of 93, and the project set
stays 11/11 in every run; otherwise the old description stays and the numbers are recorded. Every per-query result
is kept, and a void or timed-out run is rerun, not counted. The runs go when no other agent is working (the lanes
idle), since earlier runs timed out under agent load (`SK/evals/README.md:234`). Gemini reads the new description.
The bench queries that fire 0/7 whatever the wording are not chased (`SK/evals/README.md`, «does NOT ask for»).

## #190 — the test audit, lane C

**T15 · #190.** XS + a report. `band_target` retired (the session; `target_bands.py --selftest`), and the sweep
resumed on the lock's overlap — report only; what it finds is a separate `ok`.

## The end of the wave

1. The bookkeeping on the branch (the Haiku/Sonnet trial): `## [v3.2.0]` from `## [Unreleased]` with its Upgrading
   (T4's new refusal, T5's `why`, T1's fields and stdout line, T6's header rule, T2's unplanned lines), `plugin.json`
   3.2.0, `INSTALLER_VERSION`/`$InstallerVersion` 3.2.0, the install pins and `commands/install-tcc.md` on TCC
   v1.2.0 with `--constraints`; Gemini reads the CHANGELOG entry.
2. The final branch review, opus · high, on `main..wave-2026-10-21` — after the bookkeeping, since it changes executable
   installer commands and release pins; one fix round.
3. One PR with `Engine: none` in its body → its full CI on every system → `git merge --ff-only` → the candidate
   `beta-v3.2.0-rc1` on that commit.
4. The joint release through the train (hub #246; TCC's half tcc #226): TCC's N2 on the candidate, the Arbiter's VM run
   (a fresh install with the constraints, the receipt on a failed step, an uninstall), then the minor pair — the skill
   v3.2.0 with TCC v1.2.0 (`minor-pair` in `release-preflight.py`). `Latest` set by the skill; the catalog move from
   v3.1.1 is the release role's. Receipts on hub #280, #281, #285, #289 name the tag.
5. Then the freeze: only bug fixes users report.

## Cost

14 tasks for 14 issues in eight groups (#190 adds one XS task and one report on its `ok`). By vendor, roughly:
- **Claude agent runs ~50** (the seats on Opus now: +8 against the Codex plan): Rounds and levels 11 (T1 and T2: implementer, task review, fix, re-review; the two Opus
  seats and their fix round), Installers 10, Captures 6, Journal 4, Reviewer 3, CI 2, Agent start 2, the bookkeeping
  2 (Haiku and Sonnet halves), the final fix round 2 — against W-10's ~60 for 19 tasks.
- **Codex calls 1**: this plan's review (done); the seats moved to Opus when Codex's limits ran out.
- **Advisor (Gemini) calls ~6**: three translations, the method text, the description, the CHANGELOG.
- **T14's eval**: six runs of 68 queries (~400 `claude -p` calls), ~1–1.5 h, plus a rerun for any void run.

Time: lane A is the critical path — ~21 of the runs, ~7–8 h of machine time, T1 alone ~4 h. Lanes B and C finish inside it. With the CI rounds, the eval and the release
bookkeeping: ~9–11 h of wall clock, two days with the stops.
