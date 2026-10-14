# PLAN W-10 · v3.1.4 — everything outside the audit, without the engine

**Status:** written 2026-10-14 on branch `wave-2026-10-14` from five code maps (sonnet · medium, 07:25–07:30 UTC);
waits for the Arbiter's «го». `ok` on 22 issues (his «бери все», 2026-10-14); #169 «learn to listen» is off the wave, deferred with hub #113 (his «відкладені задачі ми не беремо», the same day). Built without `superpowers`
(hub H-022, the second arm): the PR carries `Engine: none`; the ledger is `docs/W-10-LEDGER.md`.

Paths: `SK` = `skills/autosound-tuning`, `RT` = `SK/rew_tool`, `N` = `RT/naming.py`, `P` = `RT/state/process.py`,
`V` = `RT/verify.py`. Line numbers are the maps' at `5b0dfc7`; an implementer re-reads before editing.

## Rules for every task

- **Weight by risk** (`hub:seam` «Process weight»). `Risk: high`: test first → implementer → task review (opus · high)
  → one fix round → re-review of the fix. Ordinary code: implementer with its tests, no task review. Docs:
  `docs-check`, at most one review. Each group ends with two seats on its shared diff —
  `pr-review-toolkit:silent-failure-hunter` and `pr-review-toolkit:pr-test-analyzer` (opus · high) — and one fix round.
  The wave ends with ONE final branch review on Fable (the wave holds `Risk: high` code).
- **Models** (`hub:seam` «Models by role»): implementer `Risk: high` opus · high; ordinary opus · medium; #163 is the
  Sonnet trial (sonnet · medium, the brief holds the exact text). XS items the session builds itself.
- **Tests**: the changed modules' selftests (`python3 <module> <argv from scripts/selftests.txt>`), the installer
  consistency script for installer work, `scripts/docs-check.py` for text. No local full suite: it runs once, on the
  PR's CI, on every system (`WAVES.md` §1 step 3).
- **Contract 1**: every name in `RT/contract.py` `IMPORTABLE` keeps its signature (`scripts/contract-guard.py` holds
  the literals). A trailing parameter with a default is an allowed addition; a changed default or a rename is not.
- **One tree, one branch.** Lanes run in parallel only on disjoint files; an implementer commits only its own paths
  (`git add <paths>`), never `-A`. Implementers do not touch `CHANGELOG.md`: the session writes each group's bullets
  under `## [Unreleased]` when the group closes.
- Every commit message in English; each fix commit names its issue (`#153`).

## Lanes and order

Three lanes run at once, on files that do not overlap:

| lane | first | then |
|---|---|---|
| **A** — `N`, `P`, `V`, `RT/contract.py` | Captures (T1–T4) | Silent failures 3 (T13–T16), then Windows' text half (T12) |
| **B** — `install.sh`, `install.ps1`, `install.cmd`, `scripts/installer-consistency.py`, `checks.yml` | Installers (T5–T9) | Windows CI (T12's CI half), then #149's installer link (T17b) |
| **C** — `SK/references/`, `docs/`, `SK/SKILL.md`, `SK/evals/` | Method text #173 (T21) | Agent start #150, #170, #149 seed (T18, T20, T17a), then #168 (T22) |


## Group Captures — `Risk: high`, lane A

**T1 · #153 (hub #269) — a round matches titles by `name_key`.** S.
Decision: **normalise on write** (the map's option B). `record_capture`, `skip_capture`, `supersede_capture` map a
typed title onto the round's own expected or optional title when `naming.name_key(parse_name(...))` matches, store
under that title, and keep the typed one as `as_in_rew` (the convention `reconcile_captures` already uses, `P:1898`)
and in the journal event. A title off the list stays as typed (`planned: false`). Readers (`_outstanding`,
`_is_taken`, `unusable_captures`, `check_captures`, the CLI's `taken`/`skipped` lookups incl. the `KeyError` at
`P:9426`, `_close_capture`, `contract.round_verdict`) get a matcher fallback for rounds already on disk: exact first,
then by key. One helper, `title_key(title)` = `name_key(parse_name(t))`, falling back to `("raw", t)` when the title
is not in the grammar. Why not matcher-only: TCC's cards read `taken`/`expected` raw, so it would still show the
capture missing.
Tests first (`P` selftest near `:6657`, `:9066–9085`; `contract.py` near `:3483`): expected `w-R_1 (sw)`, taken
`w-R_01 (sw)` → nothing outstanding, close prints no OUTSTANDING, the CLI does not raise; the same for skipped and
optional; `round_verdict` with skipped `r-L_01` against expected `r-L_1`.

**T2 · #155 (hub #261) — a level before the method.** S. With T3 in the same lane: both edit `N:92–106` and
`explain_name`.
Decision: a regex tried last (like `_TAGGED_RE`) reads `body_N[ctl|rep] <level dB> (method)[ tail]`; the level folds
into `params` ahead of any tail, so `name_key` equals the after-form's. The `note` slot (`N:544–552`, `reason` None)
offers the after-form; `canonical_title` moves the level behind the method. Writing after is already what
`generate_name` does. `naming-and-structure.md` §3 gets the place: after the method, the before-form read. Unchanged
on purpose: a titled level stays a clarification, so `sw_3 (sw) 86dB` is not the plain expected `sw_3 (sw)` (the
2026-09-16 rule); the ruling does not ask to change that.
Tests first (`N` selftest near `_check_productions`): `sw_3 86dB (sw)` parses with `params` `86dB` and the same key as
`sw_3 (sw) 86dB`; the note names the after-form; `-3.5 dB` and a tail; `sw_3 86 (sw)` still refused.

**T3 · #156 (hub #259) — a letter in front of the series number.** S.
Decision: **name a form the grammar already reads** (the map's option B), not a letter inside `_N`. The letter is a
configuration or preset marker, and `_N` is the series number, not the DSP state; reading `D7` as a series would need
a new meaning for `_N` in every series consumer (`series_used`, `_refuse_foreign_series`, `next_series`, capture
import) and an open question whether `D7` and `7` share a counter. The form: the letter after the method, as a
clarification — `w-L_7 (sw) D` — the same slot T2 gives a level. The refusal (`N:530–543`) names that form for
`w-L_D7`, `D_L_7`, `sw_E3`, `ALL+C+FX_A3`; `naming-and-structure.md:89`, the comment at `N:129` and the pinned text at
`N:1413–1425` follow. Cost, said in the CHANGELOG's Upgrading: titles already in REW in the old form are renamed once
(the uuid survives).
Tests first: each refused title's message names its after-form, and that form parses.

**T4 · #154 (hub #247) — each sweep judged over its own range.** M.
Decision: `verdict` takes the measurement's band from REW's listing (`startFreq`/`endFreq`, already in
`entry = ms.get(mid)` at `V:163`); truncation compares the curve's extent with that band (the 0.5 tolerance kept) and
is skipped when either value is missing; the analysis band is the own band clamped by `f_low`/`f_high`, so a sub's
`mean_dB` is not diluted. The signature `verdict(name, measurements=None, f_low=20, f_high=20000)` stays (contract
1, `contract.py:195`, `contract-guard.py:135`): `f_low`/`f_high` become an outer clamp, so TCC gets the fix with no
change. `stats["band_hz"]` is an addition.
Tests first (`V` selftest): a 20–200 Hz sub over 20–200 → valid, no "truncated"; a 20–20000 record whose curve stops at
300 Hz → still truncated; no `endFreq` → no truncation issue; an RTA unchanged; an explicit `--band` clamps; a
`check_captures` case with a stub listing; the `rew_stub` fixtures do not shift.

Group seats on T1–T4's diff, one fix round.

## Group Installers — `Risk: high` but T8, lane B

**T5 · #157 + #172 (session, XS each).** `install.sh:1028`, `:524`, `:1032` pipe Claude's installer to `bash` (the
hint text equal to the command); `json_str` (`:398–400`) cleans with `iconv -c -f UTF-8 -t UTF-8`, falling back to
`LC_ALL=C sed 's/[^ -~]/?/g'`. CI `installers-ubuntu` (`checks.yml:209–251`) asserts that the log has no
`Syntax error`, and warns, without failing, when Claude Code is missing after a network failure. Consistency cases:
no `claude.ai/install.sh | sh` left; `json_str` on `a\xff"b` and `é` gives text `json.loads` reads; a receipt
written with no python3 and `--skill-ref $'v\xff'` loads.

**T6 · #164 + #171 — one warning, an explicit `^v`.** S. Both edit `pick_method_ref` (`install.sh:1282–1302`) and
`Select-MethodRef` (`install.ps1:1284–1300`). The UNSIGNED line is said once, in `settled_by_name` /
`Test-SettledByName`, which every ref passes; the pick drops it. Dry-run placeholders keep the "would …" wording
(guard on a glob in the ref). The stable channel filters `^v` after `read_tags` (`grep '^v'`,
`Where-Object { $_ -cmatch '^v' }`); the beta channel unchanged. Consistency cases (the selection table at `:595–720`):
exactly one "is not a release" for `--skill-ref main`, none for the placeholders, in both installers; `v3.1.2` +
`beta-v3.1.3-rc1` → stable picks `v3.1.2`, beta picks the candidate.

**T7 · #160 — a stop before any change keeps the last receipt.** S. A flag (`RECEIPT_ARMED` / `$script:ReceiptArmed`)
set by `going_ahead` (`install.sh:551–554`) and by the write at `install.ps1:860`; `write_receipt` / `Write-Receipt`
return early while it is unset. A stop after going ahead still writes `stopped`. Consistency case: a seeded `ready`
receipt stays byte-identical after a declined consent and after "no git", in both installers.

**T8 · #163 — the help names the installer's release.** XS · **the Sonnet trial.** `install.sh:196` and
`install.ps1:277` (and the header comment at `:32–33`) build the one-liner from `v$INSTALLER_VERSION` /
`v$InstallerVersion`, so there is no second literal to move. A consistency case next to the README block
(`:2249–2291`): both help lines name `v<INSTALLER_VERSION>`, none says `main`.

**T9 · #161 + #162 — Windows starts.** S each. #161: at the top of `install.ps1`, when `PSEdition` is `Desktop`,
`PSModulePath` is reset to 5.1's own (machine + user + `$PSHOME\Modules`); children inherit it. #162: `install.cmd`
tells a double click by Explorer's exact form, `/c ""%~f0" "` (full path, doubled quote), not by `/c` plus the
name. CI on `installers-windows`: from a `pwsh` step start `powershell.exe` with pwsh's module path and run
`Get-FileHash` and `Expand-Archive` through the reset; `& .\install.cmd -Help` from pwsh prints no "Finished with exit
code". A static case: the reset stands before the first cmdlet. The double click itself is the Arbiter's, on the VM,
with the candidate.

Group seats on T5–T9's diff, one fix round.

## Group Windows — ordinary, lanes A (text) and B (CI)

**T12 · #158 (hub #274, hub #278 ask 1).** S + M.
Text (lane A, after T1–T4): `RT/project_io.py` gets two pure helpers — `plain_path(p)` strips `\\?\` and `\\?\UNC\`;
`oserror_words(exc)` says `"<strerror>: <filename>"` as written, no repr. `N:205–217` (`read_glossary_file`) calls
`plain_path` on the `readlink` result; `RT/dsp_profile.py:1479`, `:1377`, `:1384`, `:1502` print `oserror_words`. Grep
`Errno` in `RT/` and `CONTRACT.md` first for texts that pin the old wording. Tests on the Mac with literal Windows
paths.
CI (lane B, after T9): `installers-windows` runs the manifest part of `scripts/run-selftests.sh`
(`SELFTEST_ONLY_TOOL=1`) under Git for Windows' bash called by path (never `bash`, which may be WSL's launcher), with
numpy, scipy, matplotlib and ruff installed as the ubuntu job does; a module that cannot run on Windows by its nature
gets a `skip-win <path> <reason>` line in `scripts/selftests.txt`, printed as `skip` lines are. First run with
`continue-on-error`, read the failures, fix the ones that are ours, then make the step required. The receipt on hub
#278 names the job.

## Group Silent failures 3 — lane A, after Captures

**T13 · #159 — the mirror follows the project.** `Risk: high`, S. `SK/scripts/autosound_ai.py:99`: a pure
`_default_mirror(environ, cwd)` — `PROJECT_MIRROR`, else `<AUTOSOUND_PROJECT_DIR>/rew_analitic`, else
`<cwd>/rew_analitic`; `contract_copies_that_differ` drops cwd when the project is set; one stderr line when a cwd
mirror exists and is not used. `RT/CONTRACT.md:600`, `setup-critic-channel.md:371` follow. Tests: the four cases of
the function; a scene with another car's context, `.critic-env` and advisor memory in cwd — none is read.

**T14 · #165 — REW down is REW down.** `Risk: high` (`Glossary.for_project` is TCC's read), S.
`RT/predict.py` `main` sorts exceptions as `process.py _main` does (`:9813–9868`): `rew_state == "unavailable"` → one
line, exit 69, and the per-channel loop (`:2303–2309`) lets it pass up; another REW state → 1; anything else →
traceback, `error: unexpected …`, 70. "nothing was written" only where true. `rew_tool.py`: `main` wrapped so an
unexpected error is a traceback and 70; its REW-down exit stays 1 (its Ukrainian text and callers hold it).
`Glossary.__init__` (`N:233–239`) and `follow_project_channels` keep only list rows that are dicts and dict sections,
so inner shapes give "no glossary" instead of `TypeError`/`AttributeError`; types and signatures unchanged; the
strict path unchanged. Tests: lenient `for_project` over `{"channels": 42}`, `[1]`, `{"pairs": [1]}` → no exception,
`channel_codes() == []`; a stub REW raising `RewUnavailable` → 69 without "Traceback"; a `TypeError` stub → 70 with it.

**T15 · #166 — one review round, one record.** `Risk: high`, M. The check moves into `Process.record_reviewer`
(`P:1611–1638`, under the lock): the round's key is the review file's base — `<ts>-<role>` with `-package` and `.md`
stripped, `\` read as `/` — with the vendor; a second record of the same round returns the existing one, and the CLI
says "reviewer already recorded (<review>): nothing added", exit 0. The door's unlocked look (`autosound_ai.py
:5045–5048`) defers to it. First read what TCC records at package time — `~/dev/autosound/tcc`, `call_critic`
(read-only) — and settle the key on that. `RT/CONTRACT.md:156–177` and `process-schema.md` follow. Tests: package
then answer of one round → one `critic_called`; the same review twice → one; two rounds → two; the CLI twice → the
second "already recorded"; `autosound_ai.py`'s clipboard and record checks stay green.

**T16 · #167 — a timeout ends the call on Windows.** ordinary, M. A stdlib-only `RT/bounded_run.py`:
`run_bounded(argv, timeout, input=None, **kw) -> (returncode, stdout, stderr, timed_out)`, stdout and stderr to
temporary files (no pipe a grandchild can hold), a new process group (`CREATE_NEW_PROCESS_GROUP` /
`start_new_session`), `wait(timeout)`, on expiry the tree killed (`taskkill /F /T /PID`, `os.killpg`), then a bounded
wait. Moved onto it: `RT/gates/side_effect.py:114` (`_subprocess_runner` keeps its name and `(rc, out, err)` shape —
contract 1), `RT/project_repo.py:51`, `SK/scripts/issue_triage.py:42`, `SK/scripts/upkeep.py:79`,
`autosound_ai.py:1623` (`call_cli`), `:1208`, `:1299`. git calls stay for a later step. It passes
`scripts/subprocess-check.py`; it joins `scripts/selftests.txt` and any module list the installers check. Test on the
Mac: a stand-in that leaves a `sleep 30` grandchild holding stdout → returns within the timeout plus a few seconds,
`timed_out`, the grandchild gone. The Windows proof is CI's (T12 runs the selftests there).

Group seats on T13–T16's diff, one fix round.

## Group Agent start — lane C (T17b in lane B)

**T18 · #150 — a capability map near the top of SKILL.md.** docs, S. First: SKILL.md's bullets at `:126` (the reply
after a desk computation → `references/core/process-control.md`) and `:127` (where a transcript lives and where a
request goes — keep one clause) go to their homes, ~700 bytes; then one block after "Three Roles", ~450 bytes: the
finder (`python3 rew_tool/capabilities.py find "<what you want>"`, `core/capabilities.md`) and the feedback route
(bug report, feature request, feedback on the skill or TCC: `post_feedback(channel="skill"|"tcc")`, never raw `gh`).
Both phrases join `SKILL_RULE_PHRASES`; the cut ones leave it in the same commit. `capabilities.md:176` gets the
person's words (report a bug, request a feature, повідомити про баг, запит функції); `capabilities.py`'s selftest:
`find "report a bug"` returns that row first. `docs-check.py`, `reading-cost.py --check`, `move-check`. Leaves ~250
bytes, which T22 uses.

**T20 · #170 — the trigger eval measures.** ordinary, M. `SK/evals/run_trigger_eval.py`: `--cwd DIR`, default a fresh
`tempfile.mkdtemp(prefix="trigger_eval_")`, printed in the JSON and the summary; a `--cwd` inside a git repo or whose
path names `autosound`, `hub` or `skill` is refused. A `--project-fixture` mode seeds a temp project (the real
`CLAUDE.md` from `project_seed.write_claude_md`, `autosound_context.md`, `process/` and `state/` stubs); each query
gets `"context": "neutral"|"project"`. ~8 queries (a TCC feature request, feedback to the maintainers, bare
«continue»/«продовжуємо»/"where were we" in a project, near-misses: another app's feature request, a GitHub task in a
repo named `hub`, «continue» in a neutral folder, a bare "file an issue" in both). Selftest with the stand-in
`claude`: it runs in the temp folder; an `autosound` cwd is refused; `context` values valid. Three runs of the set
(~51 + 8 queries each), the table in `evals/README.md`.

**T17 · #149 — Codex at project start.** `Risk: high` (it writes into the person's project and home), M.
Facts from OpenAI's docs (the map's citations, re-fetched by the implementer): Codex finds skills in `.agents/skills`
from the cwd up to the repo root and in `$HOME/.agents/skills`, follows symlinks, reads `SKILL.md` with `name` and
`description` (ours fits); it reads `AGENTS.md` per directory, not `CLAUDE.md`; MCP servers live in
`~/.codex/config.toml` or a trusted project's `.codex/config.toml`, not `.mcp.json`.
T17a (lane C): `project_seed.py` writes `AGENTS.md` beside `CLAUDE.md` for a new project — the same load-the-skill
line and the `post_feedback` rule, never over an existing file; a verb `project.py <project> agents-setup` writes it
into an existing project (the Passat) when missing and says what it did. T17b (lane B, after T12's CI): the installers
make the user-level link `$HOME/.agents/skills/autosound-tuning` → the installed skill when `codex` is on `PATH`, or
with `--codex` / `-Codex`; a junction on Windows; said in the receipt and in the dry run. The MCP line for TCC's
server goes into `references/tooling/installation.md` as a documented step (`codex mcp add …`); TCC's own side, if
any, is a ticket. Tests: `write_agents_md` writes, leaves an existing file, shares the load line and the feedback
sentence with `CLAUDE_MD` (a docs-check phrase); the installers' dry run names the link; consistency cases for both
installers. The Arbiter's check that `codex` lists the skill comes with the candidate.

Group seats on T17, T20 and T18's diff, one fix round.

## Group Method text — lane C

**T21 · #173 — a boost path: research first.** docs, M. `docs/RESEARCH-2026-10-14-eq-boost-path.md`, from the sources
— Toole, Toole & Olive on peaks and dips, REW's help on minimum phase and EQ, Linkwitz, the car-audio tuning guides,
the AES car-cabin EQ papers; every source fetched before it is cited, the method's own data only confirming. It ends
in a proposal with advice: which dip classes could ever be boosted (minimum phase, narrow, below Schroeder, the gate's
PASS, stable across the ellipsoid), a cap, a headroom check, or none. No code: the change, if any, is a later task on
the Arbiter's ruling.

**T22 · #168 — working from the phone.** docs, M. A section "Working from the phone, and when the link drops" in
`references/core/process-control.md` after "The phase boundary" (`:128`); one pointer in SKILL.md beside Pre-Session
item 4 (from T18's headroom) and one in `capture-session-sheet.md` before BLOCK 0. Content, from Anthropic's Remote
Control page (re-fetched, cited): start interactive (`claude --remote-control` / `/remote-control`), which retries a
network drop for as long as it lasts — server mode gives up after ~10 min; the laptop awake, on power, sleep off, REW
open, the `.mdat` saved; capture rounds short, `capture-check` before leaving the car; `session-close --check` at
each block boundary; recovery by `--continue`/`--resume` within ~4 h, else a fresh session reads `process show` and
the CONTINUE block; listening verdicts typed or spoken to the session. And one offer, built nowhere: the plan of the
day reachable on the web — the session offers to publish it as a page with Claude's own means (an Artifact, opened in
any browser), and the person says yes or no (the Arbiter, 2026-10-14: «того що вміє Клауд за замовчанням достатньо.
все що треба — запропонувати користувачу таку можливість»; «це не про телефон, а про доступ до плану через web»). No
page generator, no tool. Translations only where a translated file changes (the SKILL.md pointer).

Group seats on the Method text diff: one review (docs).

## The end of the wave

1. The final branch review, Fable, on `main..wave-2026-10-14`; one fix round.
2. The bookkeeping on the branch: `## [v3.1.4]` from `## [Unreleased]` with its Upgrading (the T3 rename, the T17
   link, T14's new exits), `plugin.json` 3.1.4, `INSTALLER_VERSION`/`$InstallerVersion` 3.1.4, the install pins.
3. One PR with `Engine: none` in its body → its full CI on every system → `git merge --ff-only` → the candidate
   `beta-v3.1.4-rc1` on that commit.
4. A ticket to TCC (hub #278 ask 2): N2 as TCC's re-pin PR run on all three systems, not a local run; and the receipts
   on hub #247, #259, #261, #269, #274, #258, #278 name the tag.
5. The Arbiter's VM run on the candidate: a double click on `install.cmd`, `/setup` from a pwsh 7 window, `codex`
   listing the skill. Then his release word; `Latest` set by the skill.

## Cost

19 tasks for 22 issues in six groups. Agent runs, roughly: Captures ~17, Installers ~14, Silent failures 3 ~13, Agent
start ~8, Method text ~3, Windows ~3 plus a few CI rounds, the final review 2 — about 60, against W-9's ~30 for seven
tasks under the old weight. Machine time ~20–24 h; with three lanes, ~10–13 h of wall clock, two days with the stops.
T20's three eval runs add model calls outside this count.
