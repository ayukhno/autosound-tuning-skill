# Tooling audit — 2026-10-04

**Base:** `7b3232b` — `main` on 2026-10-04 = `v3.1.1` (`e8dabf7`) + 7 commits. Every `file:line` below is at
that commit. Paths without a prefix are relative to the repo root; `S/` = `skills/autosound-tuning/`,
`RT/` = `skills/autosound-tuning/rew_tool/`.

**Lens:** the tooling — modules, boundaries, failure handling, tests, installers, packaging, CI. The tuning
method itself (acoustics, targets, thresholds) is out of scope.

**Mode:** read-only. Nothing in the tree was changed; this file is the only addition. Findings and proposals
only — what gets built is the owner's call.

**What changed since the tag.** `git diff --stat v3.1.1 7b3232b -- skills/` is empty: the 7 commits touch
`marketplace.json`, `CLAUDE.md`, `docs/TODO.md` and `scripts/{docs-check.py, installer-consistency.py,
run-selftests.sh, tag-check.sh}` only. So every `RT/` line cited here is also the line at `v3.1.1`, which is
what TCC pins.

**How it was done.** Code read at the base; every High and most Medium findings were reproduced on throwaway
projects in a scratch directory (outside the tree) — the reproduction is named in each finding. The fixtures
were built with the repo's own writers. A fake REW (a small HTTP server answering 200/500/empty/malformed/slow)
stood in for REW. Concurrency was tested with two real processes. Windows and macOS behaviour is marked
*unverified* wherever it was inferred, not run. The audit ran as parallel read-only sessions on the same commit, one
per question; "reproduced" marks a result re-run for this report, "reproduced by the auditing session" one of
theirs (fixtures and commands kept in the scratch directory). Every line number was re-checked at the base.

---

## 0. Verdict in one paragraph

The tools are carefully built at the level of one process doing one thing: every REW call has a timeout, every
project-file write names `utf-8` and renames into place, `Project.load` refuses an unreadable file, signatures are
checked at install and update, and 85 selftests run green on a clean machine. What is missing is the layer where
**two writers, or one unreadable file, meet those tools.** Every "atomic" writer uses the same fixed temp-file name
and nothing takes a lock, so two concurrent writers — TCC and a CLI run, or two TCC threads — leave `project.json`
permanently unparseable (reproduced 4/4) and can give one ledger version number to two snapshots. And in several
places an unreadable input still reads as "nothing there": the phase gates let a project with an unparseable
`project.json` and `dsp_profile.json` advance while `contract.py check --gate` refuses it (reproduced), a torn
`seals.json` switches tamper detection off, and `capture-check` with REW down records every expected title as
taken (reproduced). The surface TCC depends on — 30 `process.py` verbs, a dozen JSON shapes, seven file formats,
~22 environment variables, 14 modules imported by path — is documented in pieces and versioned nowhere, and the
by-path import route TCC uses is not exercised by any test (two lazy bare imports fail on it; five modules edit
`sys.path`). On the install side, `install.sh`'s pip step fails on any PEP 668 Python (current Debian/Ubuntu,
Homebrew) and still ends "Installed".

Counts: **50 new findings** (T-1 … T-50: 7 High, 29 Medium, 14 Low), the **6 known items** confirmed at the base
with extensions (§3), and the **2026-09-09 review** re-checked (§2: of 34 findings in this lens, 5 fixed, 2 gone, 9 changed, 18 still open).

---

## 1. Setup and the selftest run

`pip install numpy scipy ruff==0.12.0` (numpy 2.4.6, scipy 1.17.1; Python 3.11.15; `uvx` present, so the runner
used `uvx ruff@0.12.0`), then `scripts/run-selftests.sh`, three times (~2 min each):

| run | environment | last line |
|---|---|---|
| 1 | the sandbox as given (no `ssh-keygen`) | `FAILED: 3 of 85 -- installers tag-check upkeep` |
| 2 | `openssh-client` installed | `FAILED: 1 of 85 -- upkeep` |
| 3 | same, with `HOME` pointed at an empty directory | `all 85 checks passed` |

- **Run 1** failed honestly: `installer-consistency.py` said *"the signature check's fixtures could not be made
  ([Errno 2] No such file or directory: 'ssh-keygen') -- unrun is not agreed"*, and `upkeep.py selftest` raised on
  the same missing program. A missing input failing loudly is the repo's own rule working (`CLAUDE.md` "Tests").
- **Run 2** failed on something real, not on the sandbox: the sandbox's `~/.gitconfig` sets
  `gpg.ssh.program` to a sign-only helper, and `upkeep.verify_tag` does not hand its isolated environment to git.
  That is finding **T-35** (the installers have the same exposure, reproduced against the real `v3.1.1` tag).
- **Run 3** is the clean result: **85 checks** (21 repo and skill-script checks + 63 `rew_tool` module selftests + ruff).

**What this sandbox lacks:** no REW (a fake HTTP server stood in), no Windows (no PowerShell, no DPAPI, no Git
Bash, no `clip`), no macOS (no Apple Python 3.9.6, no Homebrew, no `pbcopy`), no .NET SDK (the `engine` CI job was
not reproduced), no access to the TCC repo (`ayukhno/autosound-tcc`), and the checkout is shallow (50 commits) —
history lookups for §2 were done in a full scratch clone at the same commit.

Also run, outside the suite: Python 3.9.23 and 3.8.20 venvs (uv) — **3.9: 85/85; 3.8: 84/85** (only
`scripts/secret-scan.py:121`, `str.removeprefix`). No 3.10-only construct exists in the tree (AST scan).

---

## 2. The 2026-09-09 review, re-checked at the base

Source: `docs/review-2026-09-09/review-F-tooling.md` (F), `review-B-doc-vs-cli.md` (B), `review-C-tcc.md` (C),
summary `docs/REVIEW-2026-09-09-release-readiness.md` §3.5–3.7 (G = §3.7, E = the installer half of §3.5).
Only findings in this lens. Fix commits were found with `git log -S` in a full clone.

**Tally over the 34 rows below: 5 fixed · 2 gone · 9 changed · 18 still open.** The shape of what is left: every finding that was a
*code* fix with a selftest got done; most that were a *documentation* fix without a checker are still open, and
two got worse (F12, F15). The checkers added since (`tool-docs-check.py`, `doc-commands-check.py --run`) run in
CI only as `--selftest` — see T-47.

| ID | 2026-09-09 | status | at `7b3232b` |
|---|---|---|---|
| F1 | `rew-tool-docs.md:16` "standard library only" | **fixed** (`8777917`, guarded by `scripts/tool-docs-check.py`, `3613e30`) | `S/references/tooling/rew-tool-docs.md:16` now counts numpy users — "21 of its 54 modules"; the count has aged (64 modules, 24 import numpy) |
| F2 | `resonalyze_ir.py` command without `--out`/`--session…`; `capabilities.py` checks only that flags exist | **changed** | `capabilities.md:41` fixed (`8777917`, `3495fd8`); `rew-tool-docs.md:80` still has no `--session…` → argparse exit 2 (`RT/resonalyze_ir.py:629-633`). `doc-commands-check.py --run` skips that line as partial ("…") |
| F3 | `_claude/_codex_common.sh` source the project `.critic-env` | **gone** | shared parser `7207010`, then every shell wrapper deleted in `599be46`; the one door is `S/scripts/autosound_ai.py` (`load_env_file` 132-183 parses, never sources) |
| F4 | three model contradictions in `setup-critic-channel.md` | **changed** (1 of 3) | no default model now (`:76`); still stale `:453` "Both roles now default to Pro"; `:101` vs `.critic-env.example:46-47` (2.5 ids); `:459` vs `:101/106/190`; new: `:65-66` (ADC = flash) vs `:10`, `:103` (Pro) |
| F5 | §4 missing, "manual §6" → smoke test | **open** | `setup-critic-channel.md:268` is `###`; `:71`, `:72` still say §6 |
| F6 | two doctors; agy slug as model; API mode on key presence; `--help` → error | **changed** | one doctor (`599be46`); no model → list (`autosound_ai.py:934-951`, `:2692`); mode follows the live call (`:2747-2758`) except `--no-smoke` with a key (`:2759-2760`); **`--help`/`-h` still answer "unknown task: --help" (in Ukrainian), exit 1** (`:3114-3116`); usage `:3051` omits `key`, `selftest` |
| F7 | 3 broken links in `rew-tool-docs.md` | **open** | `:130`, `:131`, `:134` — a repo-wide convention split (84 skill-root vs 22 file-relative links); no link checker |
| F8 | `DEFAULT_CURVES_DIR` = the author's folder | **changed** | still `RT/rew_tool.py:22-24`, used at `:1754/:1760`; no longer silent — it names the curves folder it read (`:297`) and a per-row reason (`RT/target_curves.py:126`, `9f6064c`) |
| F9 | `start_gemini_tuner.sh` for the closed CLI | **changed** | script deleted (`7207010`); `references/core/driver-discipline.md:3` still recommends it |
| F10 | gemini doctor sources `.critic-env` | **gone** | `599be46` |
| F11 | `capabilities.md` → `helix-eq-export.md` for `eq_export` | **open** | `capabilities.md:115`; 0 mentions in the target |
| F12 | 14 pointers into a 59 KB file | **open, worse** | 18 rows → `rew-tool-docs.md`, now 82,337 B |
| F13 | three launch conventions | **open** | `rew-tool-docs.md:17-20`; `phase_1_foundation.md:119`; `phase_2_eq.md:30,79` |
| F14 | agy login described twice | **open** | `setup-critic-channel.md:45-56` and `:418-449` |
| F15 | `skill_metrics.sh` dead and failing | **open, worse** | "SKILL.md words: 4815 (max 1500) … 46 (max 15) … METRICS FAIL", exit 1; wired nowhere |
| F16 | `smoke_test.py` "stdlib-only"; looks for `gemini` | **open** | `S/scripts/smoke_test.py:6`, `:107`, `:133`, `:136` |
| F17 | minimum Python named nowhere | **open** | no `requires-python`; `requirements.txt:15-16` "known-good 3.12"; CI 3.12 only; `install.sh:1110` takes any `python3` — see T-46 |
| F18 | 12 modules missing from "Module Overview"; unchecked | **open, worse** | 16 of 64 missing; `tool-docs-check.py` checks claims inside an entry, not coverage ("47 module entries · 0 wrong") |
| B1 | sample `done -1.2 "get_tcc_state…"` refused | **fixed** (`f5e1b1c`) | `project-intake.md:43-46` uses a file that exists |
| B2 | `state.py registry render` without `--root` → "NO ACTIVE SLOT", exit 0 | **fixed** (`00e114c`) | root order `RT/state/state.py:1705-1712`; missing root refused, exit 2 (`:1715-1722`) |
| B3 | "predates a schema field" never printed | **open** | `SKILL.md:82`; hint only for a flaw row without symptom (`RT/contract.py:1208-1212`) |
| B4 | `python3 rew_tool.py …` from the skill root | **open** | `phase_1_foundation.md:119`; `phase_2_eq.md:30,79` |
| B5 | `analyze-joints --from-state` without `--state-root` → "give --preset" (in Ukrainian) | **open** | `capabilities.md:66`; `RT/rew_tool.py:1785-1787` has no `$AUTOSOUND_PROJECT_DIR` fallback (unlike `state.py`); message `:647-648` |
| B6/B7 | `find_bundled`; project before the subcommand | **open** | `project-intake.md:163`; `intake-from-prose.md:60` |
| B8 | repo scripts written as skill-relative | **open** | `capabilities.md:193-194` |
| C1 | `deployment.py` blind to plugin copies | **changed** (skill side fixed, `af0e8c8`) | `RT/deployment.py:187-211` adds `declared` and `plugin` (`installed_plugins.json`, `:116-141`); but see T-42 |
| C2 | `AUTOSOUND_SKILL_ROOT` vs `AUTOSOUND_SKILL_DIR` | **changed** | `_ROOT` now means "the copy a front-end declares" (`SKILL.md:37,47`; `RT/deployment.py:68`); `commands/install-tcc.md:53` names `_DIR` as TCC's own lookup |
| C3 | `capture-check --session` not reachable from TCC | **open** (TCC side) | CLI keeps it: `RT/state/process.py:2637`, dispatch `:3747-3758` |
| G1 | `skip` without reason; `session-close` writes nothing; no `reviewer` record from the door | **changed** (2 of 3, `00e114c`) | skip needs a reason (`process.py:1161-1175`); `session_closed` recorded (`:124`); **`autosound_ai.py` still only prints an instruction (in Ukrainian) to run `process.py … reviewer …`** (`:2900-2901`) — the record depends on the model obeying |
| E-pw | password wording | **changed** (self-consistent) | `install.sh:735`, `:744`, `:793` |
| E-omp | omp installed by default | **fixed** (`317dd6e`) | `install.sh:117` `WANT_OMP=0`; opt-in `--with-omp` |
| E-disk | "~700 MB" | **fixed** | `FAQ.md:74`; installer prints its own total (`install.sh:740-748`) |
| E-time | install time strings disagree | **open** | `install.ps1:750/754`, `install.sh:744/748`, `README.md:48` |
| E-pair | example pair `v3.0.33`/`v0.1.22` | **open** | `install.sh:41,46,169,173`; `install.ps1:47,52,201,205`; `install.cmd:31` |

Also from those files, still in lens: `rew-api-quirks.md:7` points into another repo (**open**); "API connectivity"
duplicated in `rew-tool-docs.md:5-11` (**open**); `capabilities.md:173` names only `.critic-env` (**open**);
change history inside `rew-tool-docs.md` (23 dates, 26 hub ids — **open, larger**); `setup-critic-channel.md:294`
lists the closed `gemini` CLI (**open**); `--help` without "how to read the output" in `eq_propose`,
`ear_suspects`, `ellipsoid` (**open**); `rew_tool.py --help` in Ukrainian (`:1753-1766`, **open**); the 5-line happy
path was added (`bf288c6`, **fixed**) but its `:10` `printf … > ~/.config/autosound/critic-env` *overwrites* the
machine file (drops an existing key line) and fails if the directory is missing — new, Low.

---

## 3. Already known (TCC architecture audit, 2026-10-03) — confirmed at the base, with extensions

These six were handed to the skill already. They are **not** counted among the new findings; each is confirmed at
`7b3232b` (the `RT/` lines are identical at `v3.1.1`) and extended only where the extension is new information.

**K-1. `set_filters` stores a flat filter at 0 dB with HTTP 200 — confirmed; it is wider than one function.**
The function is `RT/rew_api.py:473-493` (warning `:486-491`, the unguarded `return _post(...)` at `:493`; the
"478-490" in the hand-over is off by a few lines). Extensions:
- `set_filter` (`:496-502`) takes the same FilterSetting shape with no warning and no check.
- **No REW write in the module reads back**: `set_equaliser` (`:509-523`), `rename_measurement` (`:120-132`),
  `delete_measurement` (`:135-149`, addressed by a bare ordinal id with no expected title), `measurement_command`
  (`:553-559`). The only write that confirms its effect is `_create_version` (`:578-623`).
- Three filter dialects coexist and none is REW's: `RT/rew_tool.py:248-253` emits `{freq, gain, Q, type:"PEQ"}`,
  `RT/eq_propose.py:128` emits `{type, f, gain_db, q}`, REW wants `{index, type, frequency, gaindB, q}`; there is no
  converter, so every caller maps by hand — and the `gain` key is exactly the flat-filter trap.
- REW silently truncates surplus slots (`references/tooling/rew-api-quirks.md:29`); `set_filters` never compares
  counts.
- `rename_measurement` PUTs `/measurements/{id}`, which the quirks reference says **replaces the notes field**
  (`rew-api-quirks.md:71`); `measurement_kind` classifies RTA vs sweep from notes (`RT/rew_api.py:184-186`,
  `:211-217`). If that holds, a renamed RTA is judged as a sweep afterwards (unverified live). `RT/naming.py:1109`
  tells users to call it with a uuid; the function takes the ordinal id.
- No in-repo caller and no test exercises any write; the stub answers writes with 405 (`RT/rew_stub.py:176-179`).
  Reproduced by the auditing session against a fake REW that drops `gain`: `set_filters` and `set_filter` both
  returned the success body.
- **Proposal (S–M):** a `filter_setting(...)` builder; refuse unknown keys (`gain`, `freq`, `Q`, `gain_db`) before
  sending; after the POST, `get_filters` and compare type/frequency/gaindB/q per slot within a tolerance, raise on
  mismatch (also catches truncation); read back title *and* notes after a rename. **Test:** stub `_post`/`_get` as
  REW (gain dropped) — `set_filters` must raise; a `gain` entry must be refused before any POST.

**K-2. `Process.load` returns an empty state for an unreadable file — confirmed (`RT/state/process.py:974-986`,
the `except (OSError, ValueError): return _empty_state()` at `:977-981`).** `RT/project.py:781-820` refuses the
same case, and says why in its docstring. Extensions, reproduced by the auditing sessions on a truncated
`process-state.json`:
- `contract.py check --json` reports it `{"exists": true, "valid": true}` with `ok` and `complete` true, exit 0 —
  `RT/contract.py:189-192` validates the empty skeleton `load()` returned, not the file.
- `session-close --check` exits **1** on the healthy state and **0** on the torn one; TCC reads that exit code as
  "may the session stop".
- `UnicodeDecodeError` is a `ValueError`, so a cp1251-damaged file (the TCC-007 population) also reads as empty.
- The next write verb (`enter-phase -1`) writes the skeleton over the file. **The journal is kept** (separate,
  append-only), but nothing rebuilds the state from it, and step ids already used can be added again, breaking
  "steps are never re-added" (`process.py:1067`).
- Proposal unchanged from the hand-over (missing → empty, exists-but-unreadable → `ProcessError`), plus: make
  `contract.check_process` read strictly so the report says `valid: false`.

**K-3. Two writers of `process-state.json` are not serialised — confirmed; worse than a lost update.** No lock
anywhere in `RT/` or `S/scripts/` (`grep fcntl|msvcrt|flock|lockf` — nothing); no revision field; temp file
`self.state_path + ".tmp"` at `RT/state/process.py:2533`, `os.replace` at `:2539`. Extensions:
- **The fixed temp name corrupts, not just loses.** Both writers `open(tmp, "w")` the same inode; whichever renames
  first publishes a half-written file, the other's `os.replace` then raises `FileNotFoundError` after its bytes
  landed, and a shorter document written over a longer one leaves the longer tail behind ("Extra data"). Measured
  by the auditing session — two CLI loops: lost updates and tracebacks in most runs; TCC-style `flock` on one side and a bare CLI on the other: the
  state ended unparseable 3 of 3 runs. Combined with K-2 the next write then wipes it.
- The widest window is `check_captures`: load at `:2138`, REW HTTP at `:2148`, write at `:2190` — a TCC
  `capture-taken` under its lock, recorded and exit 0, is erased by an unlocked `capture-check` (reproduced by the auditing session).
- `RT/state/process-schema.md:203` still says "The **skill** is the only writer in v1".
- The same pattern in the other writers is new: **T-8** (every atomic writer), **T-9** (ledger versions),
  **T-12** (`project.json`).

**K-4. The seed preview runs `git init` + commit — confirmed and refined.** There is no separate preview path in
`RT/project_seed.py` at this commit: `seed()` always calls `project_repo.init` (`:521-528`), which runs `git init`
(`RT/project_repo.py:98`), writes `user.name`/`user.email` into `.git/config` (`:104-105`), `git add -A` (`:107`,
return code unchecked), commit (`:111`), writes `CLAUDE.md` (`:95`, not listed in `Seeded.written`), and calls
`gh api user` over the network (`:77`) unless `AUTOSOUND_NO_GH=1`. Any preview TCC builds on `seed()` inherits all
of it (TCC's side unverified). **Proposal (S):** `seed(..., dry_run=True)` returning the `Seeded` record without
touching disk, and `repo=False`.

**K-5. `gh` runs without a timeout — confirmed at `RT/gates/side_effect.py:95-97`** (`_subprocess_runner`; the
hand-over's "93-95" is off by two; same lines at `v3.1.1`). Every `gh` call goes through it (`:184`, `:265`,
`:269`, `:382`, `:476`, `:528`, `:602-608`). The other subprocesses without a timeout are **T-49**.

**K-6. No contract-version constant — confirmed.** No `CONTRACT_VERSION`, `API_VERSION` or `__version__` anywhere.
What exists is six unrelated format constants — `SCHEMA_VERSION = 3` in `RT/project.py:49`,
`RT/state/state.py:62`, `RT/state/process.py:45`, `RT/dsp_profile.py:57`; `FORMAT_VERSION = 3` in
`RT/contract.py:48`; `SCHEMA_VERSION = 1` in `RT/naming.py:51` — tied together by no test. The release identity
is `.claude-plugin/plugin.json`'s version, found by walking up to four parents from the skill folder
(`RT/deployment.py:93-110`) or by spawning git. Extensions: **T-21** (version checks inconsistent across files),
**T-22** (no JSON output is versioned), and the proposed contract in §7.

---

## 4. Module map (question 1)

**Size.** `RT/` holds 86 tracked files, 64 of them Python: **52,606 lines**, of which **12,329 (23 %) are
selftests** shipped inside the modules (and imported by TCC with them). The 14 modules TCC imports by path come to
~20,500 lines.

**Who imports whom** (AST over every `import`, top-level and function-level; the script is in the scratch dir):
- `console` is imported by 62 of 64 modules (fan-in); then `dsp_profile` 17, `naming` 17, `dsp_math` 16,
  `rew_api` 16, `project` 15, `predict` 11, `state/process` 10, `state/state` 9.
- **No cycle at import time.** Three cycles close through function-level imports only:
  `rew_api ⇄ timebase` (`RT/rew_api.py:331`); `state/state ⇄ state/apply` (`RT/state/state.py:1989`);
  `contract → project_repo → project_seed → project → intake → contract` (`RT/contract.py:226`,
  `RT/project_repo.py:93`, `RT/project_seed.py:409/524`, `RT/project.py:2423` [selftest], `RT/intake.py:58`).
- Two import styles coexist, and the difference is load-bearing for TCC: most modules put `rew_tool/` on
  `sys.path` and import siblings by bare name; `state/process.py` deliberately loads siblings **by path**
  (`_load_sibling`, `RT/state/process.py:416-433`; also `:448`, `:516`, `:534-560`) "so that names like `state` stay
  off the global import path" — while five modules TCC also imports do the opposite at import time (**T-19**).
- **Dynamic loads** (importlib by path or name): `state/process.py` ×5, `contract.py:93`, `dsp_profile.py:348`,
  `path_check.py:159`, `flaw_map.py:480`, `state/state.py:256`.

**The largest modules and what each does too much of** (line ranges at the base):

| module | lines | what it holds | too much of |
|---|---|---|---|
| `state/process.py` | 4,077 | phase gates that read `project.json`, the DSP profile and the flaw map (`:157-506`); evidence resolution and a parser for the prose ▶️ CONTINUE block (`:507-940`, parser `:589-735`); the `Process` class — plan/steps (`:1008-1224`), capture rounds incl. protective filters, knobs, amp gain, listening verdicts (`:1224-2291`, ~1,070 lines), sessions/handoff (`:2291-2480`); selftest (`:2728-3563`); hand-written CLI (`:3564-4077`) | capture rounds + amp gain + listening verdicts are a module of their own; the CONTINUE prose parser is a reader of prose inside the journal writer; gates reach into three other file formats |
| `predict.py` | 3,135 | ledger rows → filter chains (`:109-383`); loading solos from REW / v7 / RTA (`:383-729`); prediction (`:798-1063`); alignment optimiser (`:1063-1452`); verdict/delta/ladder/arrival reports (`:1452-1790`); JSON/render/plot (`:1790-2009`); CLI (`:2010-2416`); selftest | I/O, the optimiser and rendering sit in the maths module |
| `resonalyze_engine.py` | 2,984 | .NET toolchain: find `dotnet`, submodule pin, download/install/build/run (`:118-444`); input layout (`:444-632`); checks and variant generation/ranking (`:632-1942`); golden acceptance, smoke, render (`:1942-2314`); selftest | binary distribution and acceptance testing beside variant planning |
| `state/state.py` | 2,634 | validation and reads of `project.json`/target (`:60-446`); the store — versions, saved configs, seals, identity repair, `migrate_line` (`:446-1052`); `PresetHistory` (`:1052-1276`); rendering (`:1276-1428`); `Registry` (`:1428-1564`); encoding repair used by `contract.py` (`:1564-1695`); CLI (`:1695-1999`); selftest | encoding repair and layout migration (which belongs in `migrate.py`) inside the ledger store |
| `project.py` | 2,517 | the fact envelope and channel-id repair that also reads ledger files (`:69-285`, `:183-229`); `validate` (`:285-513`); the flaw/symptom model (`:513-694`); `Project` (`:766-1381`); CLI (`:1418-1794`); selftest | the flaw-map model and a cross-layer id repair that reads the ledger |

**The public surface TCC depends on, and whether it is named as a contract.** It is large and it is named nowhere
as one thing:
- **CLI:** `state/process.py <dir> <verb>` — 30 verbs (usage text `RT/state/process.py:2588-2693`, dispatch
  `:3564-4077`); `contract.py check --json` (`RT/contract.py:680-772`, `:1316-1334`); `deployment.py --json`;
  `S/scripts/autosound_ai.py critic|advisor|ask|doctor|key` with exit codes 0/1/2/3/4 and the stderr markers
  `>> REVIEW_FILE:` (`:2899`), `>> REVIEW_ROUTE:` (`:3031`, `:3261`, `:3309`), `>> PACKAGE_FILE:` (`:3342`).
- **JSON shapes:** a dozen `--json` outputs (§7); none carries a schema or version key except `resonalyze_vc`'s
  free-text `converter_version` (`RT/resonalyze_vc.py:120`).
- **Files:** `project.json`, `process/process-state.json`, `process/journal.jsonl` (24 event types,
  `RT/state/process.py:74-138`), `state/versions/v_NNN.json`, `state/slots.json`, `state/seals.json`,
  `dsp_profile.json` (+ `.draft.json`), `glossary.json`.
- **Library import:** the 14 modules TCC loads by path expose ~250 public top-level names plus `Process` (52 public
  methods), `Project` (21), `Glossary`, `PresetHistory`, `Registry`; no module defines `__all__`.
- **Environment:** ~22 `AUTOSOUND_*` variables plus `REW_API_URL` are read by the tools
  (`AUTOSOUND_PROJECT_DIR` alone in 35 places); none is listed anywhere as an interface.
- **Where it is written down today:** `RT/state/process-schema.md` has two "Front-end contract" sections
  (`:209`, `:234`) covering 4 of the 30 verbs; `RT/project-schema.md` and `RT/state/schema.md` describe the files
  but not who may rely on what; `CHANGELOG.md:209` says "For TCC: the contracts are on hub #233, #236, #237 and
  #238" — another repository; and `CHANGELOG.md:39-42` allows a patch to change a return contract if its
  Upgrading note says so in prose. A proposed single list is §7.

---

## 5. Findings

Each finding: severity · evidence at the base · what breaks and for whom · proposal with size (S = hours,
M = a day or two, L = more) · the test that would catch it. "Reproduced" means run here on a throwaway project.

### 5.1 The boundary with REW (question 2)

**What is right.** All REW traffic goes through one call site with a timeout — `urllib.request.urlopen(…,
timeout=_TIMEOUT_S)` at `RT/rew_api.py:36`, `_TIMEOUT_S = 5` at `:19` — and nothing else in `RT/` opens a
connection to REW. HTTP error bodies are carried on the exception (`:37-50`, tested `:871-901`); title lookups
are fresh and refuse a missing or ambiguous title (`:265-291`); `_ir_start_time` refuses instead of substituting
(`:424-429`); a non-percent IR unit is refused (`:453-456`); `capture-close` with REW down says "closing on the
record alone" and records `closed_against.rew: false` (`RT/state/process.py:4012-4017`, `:2268-2271`). There are
no retries anywhere, which is correct for a local server. The failures are in what callers make of the answers.

### T-1 · High · `capture-check` records titles REW never held as taken

- **Evidence:** `RT/state/process.py:2148-2153` — for **every** verdict, including `exists: False`,
  `round_.setdefault("taken", {}).setdefault(title, {...})`; `_is_taken` (`:819-822`) asks only "is there a dict and
  no `superseded_by`", so `_outstanding` (`:765-776`) drops the title and `capture-close` (`:4030-4031`) counts it
  taken.
- **Reproduced:** `REW_API_URL=http://127.0.0.1:9` (nothing listening), `capture-start 1 "m-L_1 (sw)" "m-R_1 (sw)"`,
  `capture-check` → "UNUSABLE … REW unreachable" for both; `process-state.json` then holds **both titles under
  `taken`**; `capture-close --no-rew` → "cap_001 closed: 2 taken, 0 skipped, 0 outstanding". The control without
  `capture-check` says "0 taken … 2 outstanding". With REW up and one title absent, the closed round lists that title
  as taken while `closed_against.missing` names it — the record contradicts itself.
- **Breaks:** the user and TCC (which routes process writes through this CLI): a round closes "complete" with no
  measurement behind a title; after close `unusable_captures` returns `[]`, so nothing flags it again; a later phase
  computes on a capture that was never taken.
- **Proposal (S):** keep verdicts in a separate `verified` map (or update only entries that already exist); never
  create `taken` from a check; if every verdict is "unreachable", raise and write nothing.
- **Test:** a round with two titles and a verifier returning `exists: False` for one → `capture_outstanding()` and
  `capture-close` still name it; with an "unreachable" verifier `process-state.json` is byte-identical afterwards.

### T-2 · Medium · "REW unreachable", "not in REW" and "REW answered an error" are one state, with no shared exit code

- **Evidence:** `RT/verify.py:74-77`, `:172-178` build `exists: False` + "REW unreachable: …" from a broad
  `except Exception`, so an HTTP 500, malformed JSON or an HTML page are all "unreachable"; `summary()` counts them as
  **missing** (`:405`); `render_session` prints `-- missing` with no reason (`:362`). `RT/contract.py:400-401`
  turns any exception into `{"reachable": false}`, the same shape as `--no-rew` (`:702-703`), and `ok`/`complete`
  ignore it (`:1330-1334`) → "OK — nothing to fix" with REW down, and an open capture round silently not checked.
  `RT/rew_tool.py:1827`, `:1902`, `:1910` report **any** exception as a REW API connection error (in Ukrainian).
  `RT/timebase.py` returns 2 for UNKNOWN, for REW down and for "nothing matched" (`:354`, `:376`, `:379`), and
  `{}` from `/measurements/{id}` reads as "RTA — not a fault … Safe to compare" (`:96`).
- **Exit codes with REW down (run by the auditing session):** `verify` 1 (same as an invalid capture) · `timebase --all` 2 · `contract
  check` 0 · `naming check` 1 with a traceback · `process capture-check` 1 (and T-1) · `capture-close` 0 ·
  `capture-import` 1, traceback · `ear_suspects`, `compare`, `spot_check`, `resonalyze_ir --id` 1, tracebacks.
- **No preflight:** no Python tool probes REW before working; `RT/intake.py:1149-1153` describes
  `rew.api_reachable` as "probed: a GET on localhost:4735", but no Python code performs it (only
  `install.sh:418`, `install.ps1:420`).
- **Breaks:** the user is told to re-measure what exists; TCC cannot tell "REW is closed" from "the capture is bad"
  from "the tool crashed".
- **Proposal (M):** one `RewUnavailable` exception raised by `_open` for connection errors and timeouts only, a
  separate `RewProtocolError` for 5xx/non-JSON/wrong shape, a third verdict state (`reachable: false, exists: None`)
  with its own count, and one reserved exit code for "REW unavailable" across tools; English messages.
- **Test:** point `REW_API_URL` at a closed port → `missing == 0`, `unreachable == N`, the reserved exit code; a fake
  answering 500 → "REW answered an error", not "unreachable".

### T-3 · Medium · `KeyError` means both "no such title" and "malformed payload"; callers say "missing — measure it"

- **Evidence:** `find_measurement_id` raises `KeyError` for a missing/ambiguous title (`RT/rew_api.py:286`, `:289`);
  payload access raises `KeyError` too — `data["magnitude"]` (`:361`, `:544`), `data["impulseResponse"]` (`:459`),
  `_ir_start_time` (`:426`). Callers that read every `KeyError` as "missing": `RT/eq_propose.py:922-929`,
  `RT/rew_tool.py:1061-1064`, `RT/predict.py:2186-2189`. `_get` returns any JSON with no shape check
  (`RT/rew_api.py:53-56`); `verify.verdict` documents "Never raises" (`RT/verify.py:60`) but a 200 whose body is a
  list, `null` or `{"message": …}` raises `AttributeError` (`rew_api.py:276-277`; `verify.py:78-80` catches only
  `KeyError`).
- **Reproduced by the auditing session (fake REW):** a listing with `w-L_1 (rta)` whose FR payload lacks `magnitude` → eq_propose: "'w-L_1
  (rta)' is missing, 'w-L_1 (sw)' is there … Measure it". Bodies `[]`, `null`, `{"message":…}` → traceback, exit 1.
- **Breaks:** the user re-measures something that exists; TCC gets a crash where a "REW answered nonsense" message
  belongs.
- **Proposal (M):** `MeasurementNotFound(KeyError)` for lookups, `RewProtocolError` for shape; `get_measurements`
  checks "dict of dicts"; switch the ~6 callers to catch the former only.
- **Test:** the fake above — eq_propose must not say "missing"; `verdict` on a list body returns an issue.

### T-4 · Medium · A sweep whose impulse response cannot be read passes as a usable capture

- **Evidence:** `RT/verify.py:153-155` — `except Exception: times, ir = None, None`; `:165` `out["valid"] = not
  out["issues"]`. The comment's reason ("an RTA legitimately has no impulse", `:147`) no longer applies: RTAs returned
  at `:97-104`. `check_captures` then records `verified.ok = True` (`RT/state/process.py:2154-2155`). Same pattern:
  `RT/ear_suspects.py:268`.
- **Reproduced by the auditing session:** IR endpoint answering 500 → `valid: True, issues: []`, exit 0; `peak_dB`, `pre_ringing_dB`,
  `capture_rate_hz` silently absent (so the capture-rate note is skipped too).
- **Breaks:** the user and TCC see a green row; the problem surfaces at time alignment.
- **Proposal (S):** for a swept capture, any IR failure other than REW's "no IR" answer is an issue.
- **Test:** stub `get_impulse_response` to raise on a sweep → `valid is False`.

### T-5 · Medium · `_create_version` aborts on one transient error after REW accepted the command, and accepts any single new measurement

- **Evidence:** the poll loop `RT/rew_api.py:602-606` has no `try` (the comment at `:565-567` itself warns that a
  caller retrying on the raise makes a second `-EP`); `:611` checks the new title against the source only when
  **more than one** new measurement appeared.
- **Reproduced by the auditing session (simulation):** one `URLError` mid-poll raised although the `-EP` was built; one unrelated new title
  (`tw-R_50 (sw)`) came back as `created_title` for `excess_phase_version(7)`.
- **Breaks:** TCC and sessions: a duplicate `-EP`, or another measurement's phase read as excess phase.
- **Proposal (S):** tolerate transport errors until the deadline; require the new title to start with the source
  title or end in `-EP`/`-MP`, else raise.
- **Test:** extend the existing `fake_rew` selftest with a listing that raises once and one that shows an unrelated
  title.

### T-6 · Low · The timeout is per socket operation, not per call; no batch abort; environment proxies apply to localhost

- **Evidence:** `RT/rew_api.py:19`, `:36`. A server trickling bytes made one call take 6.0 s under the 5 s
  timeout (unbounded in principle); `verify` with hanging per-measurement reads took 10.15 s for 2 titles and
  recorded each as `INVALID … unusable` with `exists: True`; `_create_version` blocks up to 20 s plus 5 s per poll
  (`:568-569`) — all measured by the auditing session. urllib honours `HTTP_PROXY`: on Linux with `NO_PROXY` unset, `GET http://localhost:4735/measurements`
  went to the proxy and its `{}` read as "REW holds 0" (macOS/Windows proxy handling unverified).
- **Breaks:** TCC calls from a QThread (the reason the timeout exists, `:15-18`); a corporate machine with a proxy
  variable sees an empty REW.
- **Proposal (M):** a per-call deadline over the whole read; abort a batch after the first transport failure; build
  the opener with `ProxyHandler({})` for REW.
- **Test:** the trickle fake must raise within ~5 s; with `HTTP_PROXY` set, the call still reaches the fake.

### T-7 · Low · The REW base URL is a module global that a library function overwrites for good

- **Evidence:** `BASE_URL` read once at import (`RT/rew_api.py:14`); `resonalyze_ir.fetch_rew(base_url=…)` assigns
  it and never restores it (`RT/resonalyze_ir.py:414-415`); `rew_api._selftest` replaces `urllib.request.urlopen`
  process-wide (`RT/rew_api.py:881-901`) and `S/scripts/smoke_test.py:105-108` runs that selftest in-process;
  `verify` (`:478-511`) and `contract` (`:1413-1420`) selftests patch module globals.
- **Breaks:** only a long-lived importer — TCC — where one call with another base URL redirects every later call in
  every thread (whether TCC calls these in-process is unverified).
- **Proposal (M):** pass a client/base URL explicitly; selftests patch `_open`, not urllib.
- **Test:** after `fetch_rew(base_url=X)`, `rew_api.BASE_URL` is unchanged.

---

### 5.2 State and concurrency (question 3)

**What is right.** Every project-file write in `RT/` names `encoding="utf-8"` (enforced by
`scripts/encoding-check.py`); single-writer saves rename into place; `Project.load` refuses an unreadable,
non-UTF-8 or non-object `project.json` (`RT/project.py:781-820`); snapshot reads (`RT/state/state.py:465-488`)
and `slots.json` reads (`:560-571`) refuse bad input; the journal is append-only and never rewritten (except by
`repair-encoding`); journal appends did not interleave on Linux even at 200 KB per event. What is missing is any
notion of a second writer, and, in a few readers, the line between "absent" and "unreadable".

**The writers** (none takes a lock, none fsyncs, none checks an expected revision; "fixed" = temp name
`<path>.tmp`):

| writer | file | how |
|---|---|---|
| `Process._write` `RT/state/process.py:2529-2539` | `process/process-state.json` | tmp **fixed** + `os.replace`; read-modify-write in every verb |
| `Process._append` `:2573-2581` | `process/journal.jsonl` | `open("a")`, one write per line, no newline guard |
| `Project.save` `RT/project.py:825-843` | `project.json` | tmp **fixed** (`:839`) + replace; `project_rev` bumped from memory (`:834-836`); ~20 callers incl. `intake.py`, `project_seed.py:485`, `migrate.py:317,488` |
| `PresetHistory.snapshot` `RT/state/state.py:1170-1208` | `state/versions/v_NNN.json` | number from a directory listing (`:1095-1098`), **plain `open("w")`, no `O_EXCL`** (`:1201`) |
| `_write_seals` `:725-729` / `_write_slots` `:574-582` | `state/seals.json`, `state/slots.json` | tmp **fixed** (`:726`, `:579`); RMW |
| `_set_head` `:1137`, `Registry._write` `:1484` (old layout) | `HEAD`, `registry.json` | plain write |
| `repair_version` `:847-874`, `repair_encoding` `:1661-1692` | ledger, any project text file | tmp **fixed** (`:866`, `:1682`); `repair_encoding` moves the original away first (`:1679`) |
| `dsp_profile.save_profile` `RT/dsp_profile.py:434-467`, `set_setting` `:766-788` | `dsp_profile.json` | **plain `open("w")`** (`:465`, `:785`) |
| `dsp_profile.save_draft` `:703-712` | `dsp_profile.draft.json` | tmp **fixed** (`:708`) |
| `apply.write_delta` / `write_sheet` `RT/state/apply.py:404-436`, `:511-526` | `state/proposals/`, `docs/sheets/` | plain write, OSError → None |
| `migrate._write_json` `RT/state/migrate.py:236-240`; `resonalyze_ir.write_v7` `RT/resonalyze_ir.py:345` | new `v_001`, v7 files | tmp **fixed** |
| `autosound_ai._persist_review` / `_write_package` `S/scripts/autosound_ai.py:2891`, `:2922` | `process/reviews/<ts>-<role>.md` | plain write, name to the second |

### T-8 · High · Every "atomic" writer uses the same fixed temp name, so two writers leave the file permanently unparseable

- **Evidence:** the **fixed** rows above — `RT/state/process.py:2533`, `RT/project.py:839`,
  `RT/state/state.py:579`, `:726`, `:866`, `:1682`, `RT/dsp_profile.py:708`, `RT/state/migrate.py:237`,
  `RT/resonalyze_ir.py:345`. This extends K-3 (which names only `process-state.json`) to every project file.
- **Reproduced:** two processes, each `Project(d).load()` → mutate → `save()` 150 times: `project.json` ended
  **unparseable in 4 of 4 runs** (`json.decoder.JSONDecodeError: Extra data: line 41 column 2`), with
  `FileNotFoundError` from the losing `os.replace`. The auditing session measured the same with two threads (9/10) —
  the shape of `intake_form`'s `ThreadingHTTPServer` (`RT/intake_form.py:1533`) — and saw 2,261 torn reads in 35,477
  by a concurrent reader (2,010 of them empty files).
- **Breaks:** the user — from then on every command refuses the project (`ProjectError`) until someone repairs the
  JSON by hand; TCC — torn reads while it renders, and a bricked project if it saves while a CLI run does.
- **Proposal (S–M):** one shared `atomic_write_json(path, data)` — `tempfile.mkstemp(dir=same dir)`, write, flush,
  `os.fsync`, `os.replace`, retry a Windows `PermissionError` briefly — used at every site above (and by
  `dsp_profile.save_profile`/`set_setting`, which are not atomic at all, T-13).
- **Test:** a selftest with two `multiprocessing` writers looping 200× on `Project.save` / `Process._write` plus a
  reader: the final file parses and the reader never sees an unparseable file. It fails today.

### T-9 · High · Two writers can bank the same ledger version; an "immutable" snapshot is overwritten in silence

- **Evidence:** `PresetHistory._next_version` takes "last listed + 1" (`RT/state/state.py:1095-1098`); `snapshot`
  writes with plain `open(path, "w")` (`:1201`) — no `O_EXCL`; seals and slots are read-modify-written after it
  (`:1203-1205`, `:1130-1135`).
- **Reproduced by the auditing session (2 × 150 snapshots):** 11 and 13 version numbers handed to both writers, each
  overwriting a banked snapshot; 162 seals for 279 files; 259 of 279 slot-history entries survived; `verify_seals`
  reported 0 problems.
- **Breaks:** `apply.propose`/`attest` from TCC and from a session at the same time: a settings sheet and a proposal
  cite a `v_NNN` whose content is now someone else's — the ledger's one promise.
- **Proposal (S–M):** allocate with `os.open(…, O_CREAT | O_EXCL)` in a loop, write content atomically, do the
  seals/slots RMW under the process lock (T-18).
- **Test:** a two-process snapshot race: returned versions distinct, files == returned, seals == files.

### T-10 · High · The phase gates let a project with unreadable `project.json` / `dsp_profile.json` advance, while `contract.py check --gate` refuses it

- **Evidence:** `_require_intake` promises "the SAME answer `contract.py check --gate` gives" (`RT/state/process.py:385-388`)
  but gates on `report.get("missing")` (`:403`) — files that do not *exist* — while `--gate` exits on
  `complete` (`RT/contract.py:1332-1333`). A checker that cannot load or raises is waved through (`:397-398`,
  `:401-402`, "a checker that raises must not become a wall"). The flaw-map gate returns on an unreadable
  `project.json` (`:338-339`, "contract.py's complaint, not this one"); the profile-facts gate returns on an
  unreadable `dsp_profile.json` (`:486-490`). That complaint never reaches a gate.
- **Reproduced:** `project.json` = `{"project": {`, `dsp_profile.json` = `{ broken`, a valid `glossary.json` and
  `state/FULL/v_001.json`: `enter-phase 0` → exit 0; after `target FULL house`, `enter-phase 1` → 0, `enter-phase 2`
  → 0; `contract.py check --gate` → **1**. A valid but *empty* project is refused at the same gates. The auditing
  session also showed one cp1251 byte in `project.json` (a `UnicodeDecodeError`, i.e. a `ValueError`) passing
  phases 0–2, and `project.json` = `[1,2]` passing phase 0 then crashing phase 1 with a traceback
  (`_flaw_map_entries`, `:215`, catches only `OSError`/`ValueError`).
- **Breaks:** the user and TCC: phase 1 computes delays without `dsp_processing_rate_hz`, phase 2 equalises with no
  flaw map — exactly what the gates exist to stop, on the file population (TCC-007, cp1251) most likely to have it.
- **Proposal (S):** gate on `complete` (or `not ok`); "cannot load / the checker raised" is a `ProcessError` naming
  the exception; the flaw-map and profile gates refuse a file that exists and cannot be read.
- **Test:** for each fixture above `enter_phase("1")` raises; a parity test — `enter_phase` refuses exactly when
  `contract --gate` exits 1 — over a small fixture matrix.

### T-11 · Medium · An unreadable `seals.json` reads as "no seals": verification passes, and the next bank erases every seal

- **Evidence:** `_read_seals` returns `{}` on `(OSError, ValueError)` (`RT/state/state.py:717-722`); `verify_seals`
  returns `[]` when there are no seals (`:760-762`); `snapshot` reads, adds its own key, rewrites (`:1203-1205`);
  `contract._unsealed` sees that the file exists and stays quiet (`RT/contract.py:208-219`).
- **Reproduced by the auditing sessions:** tamper `v_001` → detected; put a git conflict marker into `seals.json` →
  `state.py verify` exits 0, "every sealed version is as it was banked"; bank `v_002` → `seals.json` = `{v_002}`
  only, and the tampered `v_001` is invisible from then on.
- **Breaks:** the user, TCC, contract reports; a realistic trigger is a merge conflict — project folders are git
  repositories (K-4).
- **Proposal (S):** `{}` only on `FileNotFoundError`; otherwise raise; `snapshot` and `seal_all` refuse to write over
  an unreadable seals file.
- **Test:** seal, corrupt the file → `verify` exits non-zero and `snapshot()` raises with `seals.json` unchanged.

### T-12 · Medium · `project.json` lost update between a long-lived in-process `Project` and the CLI; `project_rev` is reused

- **Evidence:** `Project.save` bumps the caller's in-memory `project_rev` (`RT/project.py:834-836`) and never
  compares it with the disk, though the docstring promises the rev gives "ordering and equality" (`:830-832`);
  snapshots stamp that rev (`RT/state/state.py:1184`).
- **Reproduced by the auditing session:** an in-process object loads at rev 1, the CLI adds a flaw (rev 2), the
  object saves → rev 2 with 0 flaws; two different contents both carry rev 2.
- **Breaks:** TCC holding a `Project` across user actions while a session writes; snapshots then cite a rev that
  names two different fact sets.
- **Proposal (S):** `save(data, expected_rev=…)` that re-reads under the lock and refuses on mismatch.
- **Test:** the stale-object scenario raises.

### T-13 · Medium · `dsp_profile.json` is written in place, and a corrupt interview draft silently restarts blank

- **Evidence:** `save_profile` and `set_setting` write with plain `open(…, "w")` (`RT/dsp_profile.py:465`, `:785`);
  `load_draft` breaks out to an **empty** draft on `(OSError, ValueError)` (`:677-683`) and `set_field` saves it
  (`:799`).
- **Reproduced by the auditing sessions:** during 150 `save_profile` calls, 3,773 of 8,803 concurrent reads saw no
  processing rate (`state.py:308-312` reads it); a truncated draft beside a good profile → `dsp_profile.py draft`
  shows every question open, `set-field delay.max_ms 20` exits 0 and overwrites the draft with
  `{delay:{max_ms:20}, name: None, …}`. `finalize` does refuse it (exit 1), so no wrong number lands — the answers are
  lost.
- **Breaks:** a user mid-interview (session or TCC form).
- **Proposal (S):** atomic writes (T-8); `load_draft` refuses an existing unreadable draft, naming it.
- **Test:** good profile + corrupt draft → `set_field` raises and the draft bytes are unchanged.

### T-14 · Medium · A torn last journal line swallows the next event

- **Evidence:** `_append` writes `json.dumps(event) + "\n"` without checking that the file ends in a newline
  (`RT/state/process.py:2579-2580`); readers skip unparseable lines silently (`:997-1000`, `:249-252`).
- **Reproduced by the auditing session:** a partial last line, then `decision q2 "…"` → "recorded", exit 0; `events()`
  returns three events — q2 is glued to the torn line and gone.
- **Breaks:** the journal is the record a session resumes from; a crash mid-append (or a sync tool) costs the next
  event too, silently.
- **Proposal (S):** if the file does not end in `\n`, write one first; `events()` counts skipped lines and
  `contract.py` reports the count.
- **Test:** the scenario above — q2 must be readable.

### T-15 · Medium · Other checks that treat "cannot tell" as "no objection"

- **Evidence:**
  - `apply.evidence_problems`: an evidence file that exists but does not parse gives `doc = None`, nothing flagged
    (`RT/state/apply.py:95-101`) — `{"verdict": "BLOCK"}` is refused, the same file truncated is accepted.
  - `resonalyze_engine`: the stale-engine check returns `None` ("no complaint") when the mark is missing or
    unreadable (`RT/resonalyze_engine.py:239-241`); `_write_mark` swallows `OSError` (`:301-306`); `install_binary`
    writes `wrapper_sha256: None` (`:297`); `engine_command` then runs the prebuilt engine with no caveat (`:262`) —
    against `deployment.py`'s own rule that unknown is not agreement.
  - `predict`'s foreign-file guard: `except Exception: _hit = {}  # no answer is not a refusal`
    (`RT/predict.py:2167-2176`).
  - `naming`: with an unreadable `project.json`, switched-off channels come back active and name checks stop
    (`RT/naming.py:206-211`).
- **Breaks:** a structural move banks as "proposed" on a truncated verdict; desk variants run on an engine of
  unknown provenance presented as this checkout's.
- **Proposal (S each):** an existing file that does not parse is itself a problem; "cannot tell" returns a sentence
  carried into the output.
- **Test:** truncated verdict → `evidence_problems` non-empty; corrupt engine mark → `engine_command()[1]` names it.

### T-16 · Low · The journal's "written by" header is decided once per `Process` instance

- **Evidence:** `_stamp` marks the header once per instance (`RT/state/process.py:2565-2567`).
- **Reproduced by the auditing session:** TCC instance → CLI → the same TCC instance: the third event is attributed
  to the CLI's checkout sha.
- **Breaks:** provenance in a long-lived TCC process when a session on another checkout writes in between.
- **Proposal (S):** compare with the journal's last header on every append.
- **Test:** the interleaving above.

### T-17 · Low · No fsync, no Windows retry, and small windows

- **Evidence:** no `fsync` anywhere before `os.replace` (power loss in a car laptop can leave a zero-length file —
  which K-2 then reads as an empty process); no `PermissionError` retry around `os.replace`, which on Windows fails
  while another process holds the destination open (TCC's file watcher) — *unverified, no Windows here*;
  `repair_encoding` leaves the file absent between move and replace (`RT/state/state.py:1679-1690`); review files are
  named to the second (`S/scripts/autosound_ai.py:2891`, `:2922`) so two in one second overwrite;
  `state._project_rev` returns 0 for an unreadable `project.json` and stamps it into an immutable snapshot
  (`RT/state/state.py:342-350`, `:1184`).
- **Proposal (S):** folded into the shared writer (T-8); unique review names.
- **Test:** part of the T-8 selftest; a Windows CI run of it (T-46).

### T-18 · Medium · There is no lock protocol a front-end could share

- **Evidence:** no lock in `RT/` or `S/scripts/` (grep); TCC takes its **own** file lock around its `process.py`
  subprocess calls (review C, `T/core/process_writer.py:119-150`), which a session's CLI run never sees. K-3 is the
  process-state symptom; T-9 and T-12 are the same gap on the ledger and `project.json`.
- **Breaks:** TCC and a session writing the same project — the normal arrangement.
- **Proposal (M):** a skill-owned advisory lock (`<project>/.autosound.lock` via `fcntl.flock` / `msvcrt.locking`)
  held across load → write → append in `Process`, `Project.save` and `PresetHistory.snapshot`; a `revision` counter in
  `process-state.json` checked under it; documented in the contract (§7) so TCC takes the same lock instead of its
  own.
- **Test:** the two-process `add-step` race — plan == journal `step_added`, no exception — and the slow-verifier
  interleaving (an unlocked `capture-check` must wait for, not erase, a locked `capture-taken`).

---

### 5.3 The surface TCC depends on (question 1, continued)

**What is right.** All 14 modules TCC imports load by path from another working directory under a synthetic name
(probe run with `python3 -P` from `/tmp`, empty `PYTHONPATH`); no file I/O, subprocess, network, signal handler,
`atexit` hook, stdout output or exit happens at import; `console.install()` (which reconfigures stdout) runs only
under `if __name__ == "__main__"` in all 63 call sites; no `sys.exit` inside the library functions of those 14
modules; no module name shadows a stdlib name.

### T-19 · Medium · On TCC's by-path route, two lazy bare imports fail and five modules edit `sys.path` — so behaviour depends on import order

- **Evidence:** `RT/dsp_profile.py:318` and `:384` do a bare `import dsp_math` and the module never puts `rew_tool/`
  on `sys.path`; `save_profile` calls `annotate_modellable` inside `except ImportError:` (`:449-452`), so the failure
  is swallowed. `RT/rew_api.py:331` does a bare `import timebase`. Meanwhile `RT/project.py:40`,
  `RT/resonalyze_vc.py:95`, `RT/project_seed.py:71`, `RT/eq_export.py:50`, `RT/protective.py:75` each run
  `sys.path.insert(0, _HERE)` at import — the opposite of what `RT/state/process.py:535-539` says the front-end
  relies on ("loads these modules by explicit path precisely to keep names like `state` off the global import path").
- **Reproduced:** `dsp_profile` loaded alone by path → `annotate_modellable(...)` raises `ModuleNotFoundError: No
  module named 'dsp_math'` (and `save_profile` would stamp `modellable: null`); `rew_api` alone → `get_timing`
  raises `No module named 'timebase'`; load `project.py` first → `sys.path[0]` becomes `rew_tool/` and both work.
  The auditing session also showed duplicate module objects (`project._naming is tcc_naming` → False; two distinct
  `NamingError` classes, so an `except`/`isinstance` across them fails).
- **Breaks:** TCC: the content of `dsp_profile.json` and whether two calls work depend on which module was imported
  first; ~60 generic names (`project`, `naming`, `verify`, `windows`, `analysis`, `console`, …) sit ahead of TCC's own
  modules and site-packages for the life of the process. CI cannot see it — the runner executes each module as a
  script, so its folder is always `sys.path[0]` (T-27).
- **Proposal (M):** one by-path sibling loader (the one `process.py` already has) used for every sibling import; no
  import-time `sys.path` edits in importable modules (keep them under `__main__`).
- **Test:** T-27.

### T-20 · Medium · The DSP rate the model computes at is process-wide state, split across duplicate module copies

- **Evidence:** `RT/dsp_math.py:38` `_RATE = {"hz": FS, "source": "assumed"}`, bound by `bind_processing_rate`
  (`:50`); on a conflicting bind `dsp_profile.bind_model_rate` returns the profile's rate plus a note
  (`RT/dsp_profile.py:328-332`) while the model keeps the old one.
- **Reproduced by the auditing session:** binding a 48 kHz profile through `dsp_profile` set the bare `dsp_math`
  copy to `(48000, 'profile')`; TCC's own copy stayed `(96000, 'assumed')`; a second project at 96 kHz in the same
  process got `(96000.0, "this session already models at 48000 Hz…")` back while modelling stayed at 48 kHz.
  `RT/dsp_math.py:16-28` itself puts this error class at ~4.25 dB at 10 kHz.
- **Breaks:** harmless for the CLI (one project per process); for TCC — long-lived, several projects — **High if it
  models responses in-process** (not verifiable from this repo).
- **Proposal (S–M):** pass the rate explicitly, or make `bind_model_rate` return the rate actually in force and offer
  a reset scoped to a project.
- **Test:** load two copies, bind through `dsp_profile`, assert the rate the second copy sees; then bind a second
  project and assert the refusal is raised, not returned as a note.

### T-21 · Medium · `schema_version` is enforced for two files, accepted blindly for one, and never read for two

- **Evidence:** `project.json` (`RT/project.py:294`) and `process-state.json` (`RT/state/process.py:879`) refuse
  anything but 3 (newer → "unsupported", older → a migrate hint) — but `Process.load()` and `show` do not validate
  (K-2). The ledger check only wants an int (`RT/state/state.py:414-417`): 2, 4, 99 or missing all pass.
  `dsp_profile.json`'s version is never checked on read. The glossary's is written (`RT/naming.py:309`) and never
  read. `RT/state/process-schema.md:24` shows `"schema_version": 1`; the code writes 3.
- **Reproduced by the auditing session:** a v4 snapshot, written and sealed the normal way, gets `ok: True, legacy:
  False`, exit 0 from `contract.py check`.
- **Breaks:** an older pinned TCC — or an older skill copy on the same machine (`CLAUDE.md` "deployed more than
  once") — silently reads a ledger or profile written by a newer one.
- **Proposal (S–M):** one helper: refuse newer, hint migration for older, applied to every versioned file; fix the
  doc; a selftest that every format constant equals `contract.FORMAT_VERSION` (or is listed as deliberately apart).
- **Test:** a matrix {2, 3, 4, missing} × the files → refuse / migrate-hint / accept exactly as specified.

### T-22 · Medium · No JSON output is versioned, and the contract lives in pieces (one of them in another repository)

- **Evidence:** of the `--json` outputs (§7), only `resonalyze_vc` carries a version, as free text
  (`RT/resonalyze_vc.py:120`). `process-schema.md` documents 4 of 30 verbs as "Front-end contract" (`:209`,
  `:234`); the `contract.py check --json` key set is in no schema doc; five journal event types the code writes are
  missing from `process-schema.md` — `amp_gain_changed`, `capture_knobs`, `capture_protective`,
  `capture_superseded`, `listening_verdict`; the `>> REVIEW_FILE:` marker TCC parses is documented only in a code
  comment (`S/scripts/autosound_ai.py:2897-2899`); `CHANGELOG.md:209` puts "the contracts" on hub issues
  #233/#236/#237/#238; no module has `__all__`.
- **Breaks:** TCC learns a shape change by breaking (the way F-050 `plain`→`symptom` was found, review C §4);
  nothing tells a pinned TCC which shape it is reading.
- **Proposal (M):** an in-repo `CONTRACT.md` (§7 is a draft) plus a `docs-check`-style guard that every verb,
  `EV_*` constant and top-level `--json` key is listed in it; a `"contract": N` key in each machine output.
- **Test:** the guard, made to fail once by adding an undocumented event type.

### T-23 · Medium · Exit codes are overloaded: in `process.py`, 1 means refused, crashed, or "the answer is no"

- **Evidence:** `RT/state/process.py:4064-4066` maps `ProcessError` and a missing argument to 1; an uncaught
  exception also exits 1 (reproduced by the auditing session: `capture-protective w-L --hp abc LR 24` → `ValueError` traceback, exit 1); and
  1 is the *answer* of `check` (`:4060`), `capture-check` (`:3773`), `session-close` (`:3699`), `handoff`
  (`:3987`, `:3999`). Across tools 3 means "disagreement" (`deployment`), "refused" (`dsp_profile.py:1150`,
  `setup_import.py:384`, `state.py:1827`), "repair failed" (`contract.py:1308`) or "pick a model"
  (`autosound_ai`); 4 means "no identity", "knob refusal" (`verify_prediction.py:822`) or "reviewer refused"
  (`autosound_ai.py:3046`, `:3353`); 2 is usage except in `timebase.py:353` and `resonalyze_vc.py:1132` ("could not
  check"). No table exists.
- **Breaks:** TCC cannot tell a refusal it should show from a crash it should report, and must parse prose to know
  which.
- **Proposal (M):** a documented exit-code table (0 yes/done · 1 no/refused · 2 usage · one code for "REW
  unavailable" · one for "unexpected error") and a catch-all in `process._main` that gives unexpected exceptions
  their own code and a one-line message.
- **Test:** the crash above exits with the "unexpected" code; a table-driven test over each tool's documented codes.

### T-24 · Low · Library code that exits, prints, reads the environment, or speaks prose as data

- **Evidence:** `SystemExit` raised inside library functions — `resonalyze_engine.fetch_binary` (`:386`),
  `install_binary` (`:292`, `:295`), `flaw_map._load_from_rew` (`:227`, `:236`, `:250`) and `run` (`:267`),
  `migrate.import_current_state` (`:276`, `:285`), `rew_stub.measurements_from_v7_dir` (`:205`, `:215`);
  `Process.check_captures` prints `⚠ {rate_note}` (`RT/state/process.py:2209`) and `side_effect` prints on dry runs
  (`:111`, `:359`) — without `console.install()` a cp1252 stdout raises into the host; `_state_root` lets
  `$AUTOSOUND_STATE_ROOT` override the `project_dir` argument (`RT/state/process.py:564-566`) for every project in a
  multi-project process; `verify_prediction` derives its exit code from an English prefix of a prose verdict
  (`:823`); `handoff --json` returns a fixed Ukrainian word ("continue") as `next_message` (`:3986`).
- **Breaks:** a host that imports these (TCC) — a `SystemExit` passes straight through a host's `except Exception`
  and ends the process; a crash on a code-page stdout; cross-project leakage of one environment variable.
- **Proposal (S):** module exceptions converted to exit codes in `main`; return notes instead of printing; pass the
  state root explicitly; machine fields as enums.
- **Test:** an AST check in the suite: no `SystemExit`/`print` outside `main`/`_selftest` in the modules §7 lists as
  importable.

---

### 5.4 Tests (question 4)

**How it was measured** (by the auditing session; M10 re-run here). Function- and branch-level coverage of the union of all selftests (stdlib `trace`, plus
the verbs selftests run through `subprocess`), and **break-on-purpose**: 18 deliberate regressions made in a copy of
the tree (two of them controls), each followed by the relevant selftests, and 4 experiments on the runner itself.
**All 16 non-control regressions survived; both controls went red; all 4 runner experiments exposed a gap.**

| # | regression made in the copy | checks run | result |
|---|---|---|---|
| M1 | `process.py` skip gate removed (control) | process | **red** |
| M2 | CLI `session-start` ignores `resumed` | process, path_check | green |
| M2b | CLI `reviewer` role/model swapped | process | green |
| M3 | naming position regex `p[1-9]` → `p[1-8]` | naming, ellipsoid | green |
| M4 | `rew_api.set_filters` back to PUT with a bare array (what REW rejects) | rew_api, rew_stub | green |
| M4b | `set_equaliser` sends `{"name": model}` | rew_api, rew_stub | green |
| M5 | contract reports an invalid `project.json` as valid | contract | green |
| M6 | `state._validate_eq` drops the Q type check | state, apply | green |
| M7 | capabilities' flag regex can never match | capabilities | green |
| M8 | doc-commands `run_one` never refuses | doc-commands `--selftest` | green |
| M9c | a doc says the protective floor is 1.0×Fs (control) | docs-check | **red** |
| M9 | same, plus the constant written with a type annotation | docs-check, presweep_safety | green |
| M10 | `eq_export` ATF writer swaps gain and Q | eq_export, atf_eq, setup_import, path_check | green (**reproduced here**) |
| M11 | `# format-version: 8` deleted from `resonalyze_ir.py` | upstream-drift, resonalyze_ir | green |
| M12 | `deployment.report()` raises | deployment selftest green; `deployment.py` itself dies | green |
| M13 | `dsp_profile validate` skips validation | dsp_profile | green |
| M14 | `atf_eq` parser **and** writer swap gain and Q (mirrored) | atf_eq, eq_export, setup_import, path_check | green |
| M15 | ISO 226 63 Hz `L_U` −13 → −7 (80-phon contour at 63 Hz moves 98.36 → 92.39 dB) | equal_loudness, crossover_checks | green |
| R1 | the word "selftest" removed from `ellipsoid.py` | whole suite | dropped silently, 85 → 84 |
| R2 | a `sleep` in `analysis.py`'s selftest | whole suite | hung until killed |
| R3 | `rew_api` accepts only `selftest` | whole suite | "ok" with the usage text |
| R4 | no `uvx`/`ruff` on PATH | whole suite | "NOT RUN", not counted |

**What the selftests do well:** the `process.py` gates at the API level (M1 red); `generic_eq` and `atf_eq`
byte-exact against real REW/ATF exports; `phase_rotation` against upstream vectors; `rew_stub`'s RES-005 levels 20 dB
apart; protective/dsp_math anchored on definitions; the installer harness and `tag-check.sh --selftest` build real
signed tags in throwaway repos; failures name the break.

### T-25 · High · The ATF export can swap gain and Q with every selftest green

- **Evidence:** `RT/eq_export.py:449` and `:540` compare band **types** only (`[b.type for b in back] == ["PK",
  "LS_Q", "AP2"]`); `RT/atf_eq.py:159` checks the set of types; `RT/atf_eq.py:180` (`emitted == reference`) is
  byte-exact against a real export but goes through the module's own parser and writer — a mirrored mistake cancels.
- **Reproduced:** in a copy, `RT/eq_export.py:223` changed to `gain=row.get("q"), q=row.get("gain_db")` →
  `eq_export`, `atf_eq`, `setup_import`, `path_check` selftests all "OK".
- **Breaks:** the user pastes the ATF bank into the DSP: a −14.1 dB cut at Q 1.50 is written as +1.5 dB at
  Q −14.1 — the tool's final output, with no later check.
- **Proposal (S):** assert values, not types: the parsed reference's band 2 is `LS_Q 25.0 Hz −3.3 dB Q 0.7`; the PK
  row's exact text is `"1\tTrue\tManual\tPK\t2551.0\t-14.1\t1.50\t"`.
- **Test:** M10 and M14 above must go red.

### T-26 · High · The command-line layer of the session's main tools is almost never executed by a test

- **Evidence (never run by any selftest, in-process or by subprocess):**
  - `state/process.py` (`_main` `:3564`): `show`, `plan`, `enter-phase`, `add-step`, `start`, `done`, `skip`, `block`,
    `reviewer`, `target`, `decision`, `session-start`, `check`, `amp-gain`, `amp-changes`, `capture-taken`,
    `capture-import`, `capture-supersede`, `capture-skip` — 19 of 30 verbs; `Process.record_reviewer` (`:1195`) and
    `next_series` (`:1465`) never run at all;
  - `state/state.py` (`:1728`): `verification-set`, `seal`, `verify`, `repair-version`, `migrate-line`,
    `repair-encoding`, `set-active`, `render`, `log`, `diff`, `revert`;
  - `project.py` (`:1574`): 16 verbs incl. `show`, `set-channel`, `record-change`, `rename-channel`, `set-route`,
    `catch-up`; `dsp_profile.py` (`:1076`): all 14 verbs; `intake.py` `_main` (`:1635`): not at all; `naming.py`
    (`:1051`): `codes`, `name`, `parse`, `expect`, `next-series`, `check`; `contract.py` (`:1258`): `gaps`, `table`,
    `repair-encoding`; `rew_tool.py` (`:1752`): `analyze-batch`, `analyze-joints`; `deployment.report` (`:279`).
  - No `--json` output TCC reads has a golden key-set test (23 modules offer `--json`; only `handoff --json`,
    `verify_prediction`, `ear_suspects` are parsed by any test).
- **What survived:** M2, M2b, M13, and M12 — with `deployment.report` raising, `deployment.py` dies with a
  `KeyError` on every run while its selftest stays green; that is the command `SKILL.md` Pre-Session step 0 runs
  every session.
- **Breaks:** the session and TCC drive these tools by command line; an argument-parsing or rendering regression
  ships green.
- **Proposal (M):** one table-driven in-process `_main([...])` smoke per verb on a seeded temp project (asserting rc
  and one output token), and golden key sets for `contract.py check --json`, `deployment.py --json`, `process.py
  show`/`plan`/`handoff --json`.
- **Test:** M2, M2b, M12, M13 go red.

### T-27 · Medium · Nothing tests the way TCC loads the modules — and five modules cannot be loaded that way at all

- **Evidence:** `scripts/run-selftests.sh` runs each module as a script, so its folder is always `sys.path[0]` and
  every bare import resolves. Loaded by path from `/` with an empty `sys.path` (run here): `crossover_checks` →
  `No module named 'equal_loudness'`, `state/apply` → `No module named 'state'`, `target_bands` → `'target_curves'`,
  `target_curves` → `'naming'`, `xover_select` → `'dsp_math'` — plus the lazy failures in T-19. None of
  the five is on review C's list of what TCC imports today; whether TCC adds the folder to `sys.path` first is
  unverified.
- **Breaks:** TCC, the moment it imports one more module; and the duplicate-module and order effects of
  T-19 stay invisible.
- **Proposal (S):** a suite step that loads every module the contract (§7) lists as importable with
  `spec_from_file_location` in a fresh `python3 -P` from another directory, calls one function per module that
  touches a lazy import, and asserts `sys.path` and `sys.modules` are unchanged.
- **Test:** add a bare sibling import to one of them — the step must go red.

### T-28 · Medium · The runner has no timeout and no expected count; a skip, a dropout or a usage message counts as a pass

- **Evidence:** `scripts/run-selftests.sh:26` runs each check with no timeout and `checks.yml` sets no
  `timeout-minutes` (R2 hung); a file without the word "selftest" is skipped (`:96`, R1: 85 → 84, no message); the
  flag is chosen by grepping the file (`:103`) and rc 0 is the only pass criterion (`:27`), so a usage text exits 0 as
  "ok" (R3); a missing ruff prints "NOT RUN" and is counted in neither column (`:131`, R4); the total is printed
  (`:139`) but asserted nowhere. Selftests that return 0 when a dependency is missing: `RT/eq_gate.py:611-613` (no
  scipy), `RT/project_repo.py:147-148` (no git), part of `RT/resonalyze_vc.py` (`:1896`), and `S/scripts/upkeep.py:977` skips the hook
  block if the hook file is missing. CI installs matplotlib "so the plotting tool is tested" (`checks.yml:80-81`), but
  no selftest touches it (`predict.plot` never runs; `make_plot.py` has none); `S/scripts/smoke_test.py`, the
  documented post-install check (`CONTRIBUTING.md:31`), is not in the suite.
- **Breaks:** CI — the "two partial sets, each believing it was the whole" shape `CLAUDE.md` describes; a hang costs a
  full job timeout.
- **Proposal (S):** `timeout 300` per `run_one` and `timeout-minutes` on the jobs; fail on a `.py` without a selftest
  unless allow-listed (`make_plot.py`); require an "OK" marker in the last line; a counted SKIP state that fails in
  CI; assert a minimum count; count "ruff NOT RUN" as a failure in CI.
- **Test:** R1–R4 each turn the suite red.

### T-29 · Medium · The REW fakes encode the client's beliefs, not REW's answers; writes have no test

- **Evidence:** `rew_stub` serves every v7-derived IR with `startTime 0.0` (`RT/rew_stub.py:213`) — REW serves
  ≈ −0.99 s (`RT/predict.py:392`, `RT/rew_api.py:398-400`) — so `path_check`'s "must agree with the file branch"
  (`RT/path_check.py:523-560`) compares two identical representations; its listing carries `timeOfIRStartSeconds`,
  `timingReference`, `timingOffset` (`RT/rew_stub.py:80-95`, `:158`), which REW's listing does not
  (`RT/rew_api.py:179-183`, `:197-199`), so a stub RTA classifies `unknown` → swept → `valid: True`; it ignores
  `?smoothing` (`:155-167`) and answers writes 405 (`:176-179`); `testdata/` holds no recorded REW payload. In
  `rew_api`'s selftest `_get` is stubbed from the same documented beliefs; `_post`, `_put`, `_delete`,
  `set_filters`, `set_filter`, `set_equaliser`, `rename_measurement`, `delete_measurement`, `get_filters` are never
  executed (M4, M4b survived).
- **Reproduced by the auditing session:** reverting the RES-005 roll fix in `_spectrum_on_grid` (in process): error
  0.001 dB on stub-shaped data, **7.98 dB** on REW-shaped data (`startTime = −95629/fs`) — `path_check` cannot catch
  that regression.
- **Breaks:** CI's green says nothing about REW's real shapes; the K-1 class of bug cannot be tested at all.
- **Proposal (M):** record one live payload per endpoint (listing, FR, IR, filters) into `testdata/` as goldens; make
  the stub serve REW's shapes (no timing fields in the listing, REW-style notes/date, t0 ≈ 1 s in at a fractional
  sample, `smoothing` honoured); stub `_post`/`_put` and assert method, path and envelope including `gaindB`.
- **Test:** the pre-roll mutation must go red in `path_check`; M4/M4b red in `rew_api`.

### T-30 · Low · Three selftests talk to whatever REW is running on the developer's machine

- **Evidence:** `verify.py`'s selftest stubs `get_measurements`/`get_fr` but not `get_impulse_response`
  (`RT/verify.py:478-511`) and passes only because T-4 swallows the failure; `process.py`'s selftest
  runs `capture-close` without `--no-rew` (`RT/state/process.py:3059`); `path_check` runs `contract.py check` without
  `--no-rew` (`RT/path_check.py:319`). A logging fake on `REW_API_URL` recorded 2× `GET /measurements` and 1×
  `GET /measurements/2/impulse-response?normalised=false` during a full suite run. Also: the runner calls
  `verify.py selftest`; `verify.py --selftest` is silently taken as a measurement title.
- **Breaks:** a developer with REW open runs the suite against a live session; results can depend on it.
- **Proposal (S):** stub the IR, pass `--no-rew` in both places, and export `REW_API_URL=http://127.0.0.1:9` in the
  runner.
- **Test:** the suite against a logging fake records zero requests.

### T-31 · Medium · Checks that report OK when their input is missing (the repo's rule iii)

Run by the auditing session in a copy of the tree (each input removed, the check run):

| check | input removed | result |
|---|---|---|
| `scripts/docs-check.py:359-363` | protective-floor constant unreadable (`if margin is None or slope is None: return []`) | M9: annotate the constant and the doc rule goes silent |
| `scripts/docs-check.py:321` | every install line removed | rc 0 |
| `scripts/docs-check.py:235` | the `phases` directory | rc 0 (capabilities catches it elsewhere) |
| `scripts/html-data-check.py` | no HTML files | "OK — 0 file(s)", rc 0 |
| `scripts/i18n-check.py` | two of six translations | rc 0, "4 translation(s)" (fails only at zero, `:112`) |
| `scripts/tool-docs-check.py` | zero entries | rc 0 |
| `scripts/doc-commands-check.py` | `rew-tool-docs.md` | "91 lines parsed", ok |
| `scripts/upstream-drift.py:251-253` | no headers | "nothing is declared as a port", rc 0 — and M11 (a `# format-version` line deleted) stays green |
| `scripts/installer-consistency.py:323-325` | `$TccRepo` removed from `install.ps1` | rc 0 — `sh_tcc, _ = one(...)` throws the problem away |
| `RT/contract.py check /no/such/dir` | the project | "**OK — nothing to fix.**", rc 0; `--phase0-gate` also 0 |
| `RT/state/process.py /no/such/process check` | the process dir | "0 done step(s) without evidence", rc 0 |
| `RT/deployment.py /no/such/dir` | the project | "OK: one method" |
| `hooks/session-start.sh:15` | `plugin.json` unreadable | silent (= "set up") |

Correct on missing input: `changelog-index --check`, `secret-scan` on a non-repo, `encoding-check` on an empty dir,
`capabilities` on a missing/short board (`RT/capabilities.py:239`), `installer-consistency`'s README read and its
signature fixtures (§1 run 1).

- **Breaks:** CI and the user: the guard a rule was moved into (`CLAUDE.md`: "a rule written anywhere but in a check
  is the rule that already failed") stops guarding without a sound.
- **Proposal (S each):** every "nothing found" branch fails, or names the inputs it expected and exits non-zero in
  CI; `upstream-drift` asserts the real ports (`resonalyze_ir` format 8, `resonalyze_vc` format 10) are found.
- **Test:** each row above, run as a negative case in the checker's own selftest.

### T-32 · Medium · Three checkers can be fooled by text that merely contains the right words

- **Evidence:**
  - `RT/capabilities.py:177-182` — `if flag not in src` / `verb not in src`: a substring anywhere in the file,
    comments included; `_VERB` (`:116`) covers six modules; the selftest runs only on the live board (M7 survived).
  - `scripts/doc-commands-check.py` recognises only argparse's wording (`:157`) and counts a timeout as fine
    (`:152-153`), so a typo'd verb for a hand-parsed CLI — `naming.py <p> codez`, `contract.py <p> chek`,
    `project.py <p> flawz` — exits 2 with a usage block and is not flagged; its selftest never calls `run_one` (M8).
  - `scripts/installer-consistency.py`: changes that pass it (rc 0, mutation runs by the auditing session) — drop `--break-system-packages`
    from `install.ps1`; drop `--upgrade` from `install.sh`; change the fallback-to-`main` in one file only; TCC
    `--python 3.12` → `3.11`; remove `install.sh`'s exit on clone failure; pin `install-tcc.md` to `@v0.0.1`.
    `CLAUDE.md` calls the installers a triplet where "a claim checked in one file is not checked"; the uncompared
    decisions are listed in §5.5's evidence (T-34, T-37, T-44, T-45).
- **Proposal (S):** match flags/verbs against argparse definitions or dispatch tables, not raw text; treat rc 2 +
  `usage:` as a refusal; turn the mutation list into the consistency checker's selftest.
- **Test:** a fixture board with a bogus flag/verb/function → three problems; each installer mutation → red.

### T-33 · Medium · Selftests anchored on the implementation's own output

- **Evidence:** `RT/equal_loudness.py:123-129` anchors SPL == phon at 1 kHz only, then round-trips through its own
  inverse (`calibrate_phon` → `iso226_spl`) — M15 moved the 80-phon contour at 63 Hz by 6 dB and both
  `equal_loudness` and `crossover_checks` stayed green; naming's "grammar round-trips" let M3 (position `p9`
  unparseable) through `naming` and `ellipsoid`; `state._validate_eq`'s Q check can be deleted (M6); `contract.py`
  never tests an invalid `project.json` (`:118`, M5).
- **Breaks:** sub-bass loudness compensation, a position grammar and a ledger validator can change silently.
- **Proposal (S):** anchor `equal_loudness` on 3–4 published ISO 226:2003 values (e.g. 80 phon at 63 and 125 Hz); a
  naming case per grammar production; negative cases for `_validate_eq` and `check_project`.
- **Test:** M3, M5, M6, M15 go red.

No test exists for concurrent writers or for a corrupt `process-state.json` / `seals.json` / journal; the tests
named in T-8, T-9, T-11, T-14 and K-2 would be the first.

---

### 5.5 Installers, the hook and packaging (question 5)

**What is right.** `install.cmd` fetches `install.ps1` at the released tag (`install.cmd:38` →
`…/v3.1.1/install.ps1`); the catalogue pin `marketplace.json` → `e8dabf7` equals `v3.1.1^{commit}`, and `plugin.json` says
3.1.1 at both; the signing constants agree across `install.sh:69-71`, `install.ps1`, `upkeep.py:51-52` and
`allowed_signers`, and `v3.1.1` verifies against them (run here, with `gpg.ssh.program` pinned — see
T-35); both installers verify the method's tag on clone and on update, and TCC's tag before `uv` (with a
re-check right before it); `gh` downloads are checked against their release checksums, the Git-for-Windows
installer's Authenticode signer is checked, `uv` is fetched at a pinned version; the hook makes no network call,
writes nothing, runs in ~8 ms and exits 0 on every path. `installer-consistency.py` compares 33 decisions and runs
`install.sh`'s own `newest_on_channel`, `verify_tag`, `check_tcc_tag` and `tcc_tag_still_at` in a harness.

### T-34 · High · `install.sh` cannot install the Python libraries on a PEP 668 Python — and still ends "Installed"

- **Evidence:** `install.sh:1110` takes whatever `python3` is; outside a venv it runs `pip install --upgrade --user
  … -r requirements.txt` (`:1116`) with no `--break-system-packages` and no venv fallback. Its twin passes both
  (`install.ps1:1215`). On failure: a warning, later "numpy is NOT importable", and `say "Installed, with the
  warnings above."` (`:1562`) — exit 0.
- **Reproduced:** the exact flags against Ubuntu 24.04's `/usr/bin/python3.12` → `error: externally-managed-
  environment`, rc 1. The auditing session saw the same with a uv-managed 3.9 ("managed by uv").
- **Breaks:** Linux users on Debian 12+/Ubuntu 23.04+/Arch; macOS users whose `python3` is Homebrew's (which
  `install.sh` itself suggests installing when `python3` is broken); anyone with a uv `python3` first on PATH
  (`install.sh:784` puts `~/.local/bin` first); plugin users, whose `commands/setup.md` forbids the
  `--break-system-packages` workaround. A stock Mac with Apple's 3.9 is not affected. The method then fails at its
  first numpy import in the session.
- **Proposal (M):** when pip reports externally-managed, install into a dedicated venv (or a uv-managed 3.12, as
  Windows does) and point the method at it; or mirror `install.ps1`'s flags. Exit non-zero when numpy is not
  importable at the end (T-44).
- **Test:** a CI step on `ubuntu-24.04` running the cut-out pip block against `/usr/bin/python3` and asserting
  `import numpy`; ideally the same on `macos-latest` with Homebrew Python.

### T-35 · Medium · Every signature check inherits the user's `gpg.ssh.program`, so a signed release is refused — with the wrong diagnosis

- **Evidence:** `install.sh:876-877`, `install.ps1:936` and `S/scripts/upkeep.py:118-119` run `git -c
  gpg.format=ssh -c gpg.ssh.allowedSignersFile=… verify-tag` and pin nothing else, so a global
  `gpg.ssh.program` (a signing helper) is used for *verification*. `install.sh`'s classifier then matches the helper's
  message on `*"-Y"*` (`:885`) and blames git's age.
- **Reproduced against the real `v3.1.1` tag** with a sign-only `gpg.ssh.program` in `~/.gitconfig` (this
  sandbox's): `git … verify-tag v3.1.1` → rc 1; with `-c gpg.ssh.program=ssh-keygen` → `Good "git" signature for
  ayukhno`. `install.sh`'s own `verify_tag`, cut out and run: *"the signature of v3.1.1 could not be checked here --
  it is not installed … this git (git version 2.43.0) may be too old to check one: 2.34 or newer is needed"*; with a
  clean `HOME`: "✓ v3.1.1 is signed by the skill's author". `upkeep.py selftest` fails the same way (§1 run 2)
  because `verify_tag` does not pass its `env` to git (`:118` vs `:105`) — the only place the isolation leaks, and
  the only reason this surfaced.
- **Why the tests miss it:** `installer-consistency.py` runs the installers' functions with
  `GIT_CONFIG_GLOBAL=/dev/null` (`scripts/installer-consistency.py:196-197`) — it isolates exactly what a user's
  machine does not.
- **Breaks:** fails closed (no security loss), but blocks install and update for any developer whose git signs
  through a helper (whether 1Password's `op-ssh-sign` verifies is unverified), and tells them to upgrade a git that is
  new enough.
- **Proposal (S):** add `-c gpg.ssh.program=ssh-keygen` in all three paths;
  pass `env` in `upkeep.verify_tag`; don't classify on a bare `-Y`.
- **Test:** the harness gains one case with a global config whose `gpg.ssh.program` is a script that exits 1 — the
  signed tag must still pass.

### T-36 · Medium · Tags and releases are mutable, so the signature protects neither the one-liner nor the engine binaries

- **Evidence (repository settings, not code):** the `v3.1.1` release reports `"immutable": false` (GitHub API,
  read here); the auditing session read the rulesets — one, `protect-main` (deletion, non-fast-forward on
  `refs/heads/main`), nothing on tags — and `immutable-releases` `{"enabled": false}`. Yet `engine-binaries.yml:14`,
  `:124`, `:133` reason "with immutable releases on". The README one-liners (`README.md:52`, `:57`) and
  `install.cmd:38` fetch the installer by tag name from raw.githubusercontent — the installer itself is verified by
  nothing. `fetch_binary` checks the engine zip only against `SHA256SUMS` from the same release
  (`RT/resonalyze_engine.py:369-386`) — integrity, not authenticity; replace both and the check passes.
- **Breaks:** the threat signing was added for ("someone holds the token"): a moved tag serves a different
  `install.sh`/`install.ps1`; a replaced asset pair serves a different engine.
- **Proposal:** a tag ruleset blocking update/deletion of `refs/tags/v*` and `beta-v*`, and immutable releases on
  (settings, S); sign `SHA256SUMS` with the release key (`ssh-keygen -Y sign`) in `engine-binaries.yml` and verify it
  in `fetch_binary` against the embedded key (M).
- **Test:** `tag-check.sh` (or the hub preflight) queries `rulesets` and `immutable-releases` and fails when off; a
  `fetch_binary` selftest with a tampered zip + regenerated sums must refuse.

### T-37 · Medium · When no release tag can be read, both installers install an unverified `main` — the method and TCC

- **Evidence:** `install.sh:1026` `[ -z "$SKILL_REF" ] && SKILL_REF="main"` (`install.ps1:1125`); TCC
  `install.sh:1271-1274` "installing from the default branch instead, which has no signature to check"
  (`install.ps1:1351`); a non-release name passes `settled_by_name` unchecked (`install.sh:856-858`,
  `install.ps1:915`). On a re-run this moves an already verified clone to `main` (`:1043-1045`). `upkeep.py:379-380`
  fails closed in the same situation.
- **Breaks:** anyone hit by a transient `git ls-remote` failure gets unreleased code with no signature; also the
  path an attacker who can delete tags would use.
- **Proposal (S):** stop non-zero and leave the existing copy alone; allow `main` only with an explicit
  `--skill-ref main` / `--tcc-ref main`.
- **Test:** the signing harness runs the selection block with a stub `git ls-remote` that returns nothing → refusal.

### T-38 · Medium · Re-running the installer does not recreate a missing `~/.claude/skills/autosound-tuning`

- **Evidence:** the update branch (`install.sh:1043-1045`) checks out and never links; the link is made only in the
  fresh-clone branch (`:1053-1056`). Same in `install.ps1:1142-1149` (no `New-Item -ItemType Junction`).
- **Reproduced by the auditing session** (the block `:1030-1058` run alone with the clone present and no link): no
  link afterwards; the run ends "Installed, with the warnings above", while the last screen says "Update everything:
  run this same install line again".
- **Breaks:** a user who removed the link (or whose cleanup tool did) — the session no longer sees the skill.
- **Proposal (S):** after the update, create the link if missing, in both installers.
- **Test:** the cut-out block with `SKILL_SRC/.git` present and no link → the link exists.

### T-39 · Medium · On Windows the "not set up" note probably never goes away

- **Evidence:** `plugin_ready` appends `f"v{version}\n"` in text mode (`S/scripts/upkeep.py:254-255`) — `\r\n` on
  Windows; the hook tests it with `grep -qxF "v$version"` (`hooks/session-start.sh:16`).
- **Reproduced by the auditing session (Linux GNU grep):** a CRLF line → the hook still prints the note; LF → silent. That Git-for-Windows
  grep behaves the same is *unverified*. The upkeep selftest skips the hook on Windows (`S/scripts/upkeep.py:977`,
  `os.name != "nt"`) and never tests "ready → silent" on any platform.
- **Breaks:** a Windows plugin user is told on every session start that setup is missing, after running it.
- **Proposal (S):** `newline="\n"` in `plugin_ready`; `tr -d '\r'` in the hook.
- **Test:** write the ready file with CRLF, run the hook, assert silence — on the Windows CI job.

### T-40 · Medium · A plugin user who has a .NET SDK gets no engine

- **Evidence:** the default `auto` engine policy builds when an SDK is present (`install.sh:1135-1139`,
  `install.ps1:1243`); the build runs `git -C <repo> submodule update` (`RT/resonalyze_engine.py:410`); a plugin copy
  has no `.git`.
- **Reproduced by the auditing session** on a `git archive` copy with a stub `dotnet`: "not built: fetching
  vendor/Resonalyze failed: fatal: not a git repository". Build output under `engines/resonalyze/bin/…` would also
  make a later `upkeep.py verify-copy` of that copy refuse ("not in the release").
- **Proposal (S):** in `--plugin` / `-Plugin` mode treat `auto` as fetch.
- **Test:** a `build()` selftest on a copy with no `.git`; a read check in `installer-consistency.py` for the
  plugin-mode branch.

### T-41 · Medium · The reviewer-key guard passes whenever git errors

- **Evidence:** `S/scripts/autosound_ai.py:117-118` — `if subprocess.run([… "rev-parse", "--is-inside-work-tree"],
  …).returncode != 0: return` — any failure reads as "not a repository"; no timeout (`:117`, `:119`, `:124`).
  `CLAUDE.md` names this guard as one of the three carriers of "a key never leaves a repository".
- **Reproduced by the auditing session:** in a repo owned by another uid, git 2.43 answers "dubious ownership"
  (rc 128); the guard returns and the run continues; after `chown`, the same untracked, unignored `.critic-env` is
  refused with rc 2.
- **Breaks:** users on Windows-VM shared folders (the author's Parallels/UTM setup), external drives, WSL `/mnt/c` —
  where the commit is later made from the host, where git works. The `secret-scan --staged` hook would still catch it
  if installed on that machine.
- **Proposal (S):** pass only on "not a git repository"; any other git failure → refuse ("cannot ask git whether this
  file is ignored"); add a timeout.
- **Test:** a fake `git` on PATH exiting 128 with "dubious ownership" → exit 2.

### T-42 · Low · `deployment.py` misidentifies a plugin copy that sits inside another git repository

- **Evidence:** `git -C root rev-parse HEAD` (`RT/deployment.py:80-90`, used at `:166-168`) finds an *enclosing*
  repository, so the commit Claude Code recorded for the plugin (`installed_plugins.json`) is ignored;
  `RT/deployment.py:125` hard-codes `~/.claude/plugins` (Claude Code's `CLAUDE_CODE_PLUGIN_CACHE_DIR` ignored —
  effect untested).
- **Reproduced by the auditing session:** a fake `HOME` that is a git repo → the plugin row showed the home repo's
  HEAD instead of `e8dabf7` → a false "disagree", exit 3.
- **Breaks:** users who keep `~/.claude` under git (a documented practice) get a refusal at Pre-Session step 0.
- **Proposal (S):** trust HEAD only if `rev-parse --show-toplevel` equals the root.
- **Test:** the scenario above as a selftest case.

### T-43 · Low · On Linux, `install.sh` creates `~/.bash_profile`, which hides `~/.profile`

- **Evidence:** `profile_rc` picks `$HOME/.bash_profile` for bash (`install.sh:378-382`), appended at `:411`.
- **Reproduced by the auditing session (scratch `HOME`):** before, a login shell read `~/.profile` → `~/.bashrc`;
  after, `~/.bashrc` is no longer loaded; non-login GNOME terminals never read `~/.bash_profile`.
- **Proposal (S):** on Linux, write to `~/.profile` (or `~/.bashrc`); keep `.bash_profile` for macOS bash.
- **Test:** cut-out `add_to_path` in a `HOME` with only `.profile` → no `.bash_profile` appears.

### T-44 · Low · A degraded install exits 0; the two installers disagree on a failed clone

- **Evidence:** "Installed, with the warnings above" and exit 0 (`install.sh:1562`, `install.ps1:1635`); a failed
  clone exits 1 in `install.sh` (`:1052`) but only warns in `install.ps1` (`:1166`); the engine fetch returns 4 for
  both "this release carries none" and "unreachable" (`RT/resonalyze_engine.py:2936`), which the installers record in
  the receipt as "carries no engine for this machine" (`install.sh:1174`, `install.ps1:1290`), and every re-run
  downloads ~30 MB again.
- **Breaks:** TCC's installer report and any wrapper that reads the exit code; `setup.md`'s plugin flow.
- **Proposal (S):** a distinct non-zero exit when anything required failed; one rule for a failed clone; a separate
  exit for "unreachable"; skip the download when the same pin is installed.
- **Test:** add the exit-code expectations to the harness.

### T-45 · Low · Smaller installer and packaging points

- **Receipt hash empty for the one-liners:** `install.sh:1773` hashes `"$0"` (= `bash` under `curl | bash`);
  `install.ps1:1814` only when `$PSCommandPath` is set (not under `irm | iex`) — the receipt's purpose (S-049) is
  lost on the main path. *Proposal:* embed a version constant.
- **Three rules for "is a release tag":** a glob in `install.sh:856-857` (accepts `v3.1.1-x`, then checks its
  signature), a regex in `install.ps1:915` (calls it "not a release — no signature to check" and installs it), and
  `S/scripts/upkeep.py:110` (refuses). Only reachable with an explicit ref. *Proposal:* one regex, refuse.
- **Clone by branch, verify by tag:** a fresh `git clone --branch REF` takes a *branch* of that name over the tag;
  the check reads `refs/tags/REF`. Fails closed in the shallow case; defence in depth: assert `HEAD ==
  refs/tags/REF^{commit}` after the check.
- **`commands/install-tcc.md:20`** pins TCC `v1.1.0` with no signature check and no `--python 3.12` (which
  `install.sh:1245` calls "not optional"); `v1.1.1` exists; `:27` says `installer-consistency.py` compares its tag
  with the installer's — the checker only checks that *a* tag is present (`scripts/installer-consistency.py:686`).
- **Hook on Windows without Git Bash** (per Claude Code's hook docs — not run): `bash "…/session-start.sh"` fails,
  without blocking, and a plugin-only user is never told to run setup. And an unreadable `plugin.json` makes the hook
  silent (`hooks/session-start.sh:15`) — a missing input reads as "set up".
- **`ADVANCED.md:99`** says the method runs on uv's Python 3.12 — true on Windows only; `install.sh` uses any
  `python3`. **`--yes`** (used by `setup.md`) auto-answers "update installed tools", i.e. updates Claude Code from
  inside a running Claude Code session (`install.sh:1472`) — effect not checked.
- **Plugin vs clone (for the record):** a plugin user gets the repo's files at the catalogue sha — skill, hooks,
  commands, installers, engine sources — and no Python libraries, engine, TCC or PATH line until
  `/autosound-tuning:setup` (which runs `install.sh --plugin --terminal --yes`, verifies the copy against its signed
  release, then installs — so T-34 and T-40 apply). `vendor/Resonalyze` is empty in a plugin copy
  (inferred from `verify-copy`'s design; whether Claude Code fetches submodules is unverified).

---

### 5.6 CI (question 6)

| workflow / job | trigger | runs | platform |
|---|---|---|---|
| `checks` / `gate` | push to `main`, PR, manual | on push: skips the rest if a green PR run exists on the same sha; any API problem → run (fails open) | ubuntu |
| `checks` / `selftests` | gate says run | `pip install --upgrade numpy scipy matplotlib`; `scripts/run-selftests.sh` (85 checks); `bash -n install.sh`; `ruff check` 0.12.0 | ubuntu, Python 3.12 |
| `checks` / `engine` | gate says run | Resonalyze submodule at the pin; .NET SDK from `global.json`; `resonalyze_engine.py build` + `smoke` | ubuntu, 3.12 |
| `checks` / `installers-windows` | gate says run | `installer-consistency.py`; `install.ps1` parses; DPAPI key-store round trip | windows, 3.12 |
| `engine-binaries` / `build` | `v3.*` tag push, manual | `dotnet publish` win-x64, win-arm64, osx-arm64; macOS codesign verify; synthetic smoke per binary | windows, windows-arm, macos |
| `engine-binaries` / `attach` | tag push only | zip, `SHA256SUMS`, draft → upload → publish | ubuntu |

**Never run in CI:** `install.sh`/`install.ps1` end to end (not even `--dry-run`); `uv`/TCC installation; the
`rew_tool` selftests on Windows or macOS; any Python but 3.12; `upkeep.py clone/verify-copy/plugin-ready` on
Windows; the hook on Windows, and its "ready → silent" path anywhere; a real engine download; the real-tree halves
of `doc-commands-check.py --run`, `tool-docs-check.py`, `upstream-drift.py` (against the upstream); a run on a
`beta-v*` candidate tag.

### T-46 · Medium · The method's code is tested on Linux with Python 3.12 only

- **Evidence:** `.github/workflows/checks.yml:76`, `:127`, `:150` (`python-version: "3.12"`); the Windows job runs
  `installer-consistency.py` and a parse, not `run-selftests.sh`; there is no macOS job in `checks.yml`.
  `install.sh:1110` installs into whatever `python3` is — Apple's 3.9 on a stock Mac (its own comment) — and TCC runs
  the same modules on Windows.
- **Measured here:** Python 3.9.23 → 85/85; 3.8.20 → 84/85 (`scripts/secret-scan.py:121`). So nothing is broken
  today; the gap is regression risk, plus the Windows-only behaviours above (T-39, T-17) that no
  run would see.
- **Proposal (S):** a `3.9` entry in the selftests matrix; `run-selftests.sh` on `windows-latest` (the Windows job already
  sets `PYTHONUTF8`) and on `macos-latest` with `/usr/bin/python3` + `pip --user`; state the minimum (`3.9`) in
  `requirements.txt` and the installers.
- **Test:** the matrix itself; a deliberate 3.10-only construct must turn the 3.9 job red.

### T-47 · Low · Checks that read the real tree run in CI only as their own selftest

- **Evidence:** `run-selftests.sh` runs `doc-commands-check.py --selftest` (`:68`) and `tool-docs-check.py
  --selftest` (`:69`) — the selftests build their own fixtures and never read the real documents; the real-tree runs
  (`doc-commands-check.py --run`: 34 run, 91 skipped; `tool-docs-check.py`: "47 module entries · 0 wrong · 37 without
  a dependency line") are manual. `upstream-drift.py` is designed to exit 2 on drift "so a CI step can warn without
  failing" (its docstring) and has no CI step; a scheduled job (network, `gh` compare API or `--fetch`) could run it.
  `S/scripts/skill_metrics.sh` fails and is wired nowhere (F15).
- **Breaks:** the documents drift (F2's `rew-tool-docs.md:80`, F18's 16 missing modules) with a green CI.
- **Proposal (S):** run the real-tree modes in `run-selftests.sh` (warn-only where a doc cannot be fixed yet), add a
  scheduled `upstream-drift.py` job, and delete or wire `skill_metrics.sh`.
- **Test:** the runner's count goes up by the new lines; break one doc command and see it red.

### T-48 · Low · A beta candidate can be tagged on a commit CI never ran on

- **Evidence:** work branches run no CI on push (`checks.yml` triggers: push to `main`, PR, manual —
  `CLAUDE.md` "Releasing"); `checks.yml` has no tag trigger; `engine-binaries.yml` triggers on `v3.*` only. Beta users
  install `beta-v*` candidates (`install.sh` beta channel). "CI green on the tagged commit" is enforced only by the
  hub's preflight, outside this repo (not verified).
- **Proposal (S):** `tag-check.sh --candidate` asks the API for a green `checks` run on the commit, or `checks.yml`
  runs on `beta-v*` tag pushes.
- **Test:** `tag-check.sh --candidate` on a commit with no run refuses (selftest with a stubbed API answer).

---

### 5.7 Elsewhere: subprocesses and the helper scripts

The census behind §5.1–5.3: **496 `except` handlers** in `RT/` and `S/scripts/`, 177 of them inside selftests
asserting a refusal; of the **319 in production code**, 60 raise or exit non-zero, 154 return a default or pass, 27
warn and continue, 51 put the error into a result, 27 other; 89 are `except Exception`, none bare. Most of the 154
defaults are reads of optional facts and are benign (fail closed later, or are display-only); the ones that are not
are the findings above (T-10, T-11, T-13, T-4, T-15,
T-41, K-2). Encoding: zero text `open()` without `encoding=` in `RT/` (enforced); 19 in `S/scripts/`, all
inside selftests. No `verify=False`/`CERT_NONE` anywhere; local servers bind to 127.0.0.1; the AI-API calls have
timeouts and send the Gemini key as a header, not in the URL.

### T-49 · Low · Subprocesses and downloads with no timeout, beyond the known `gh`

- **Evidence (production code; selftest-only calls omitted):** `RT/resonalyze_engine.py:134`, `:139` (git, in
  `pin()`, also called by `run_engine`), `:410` (`git submodule update` — network), `:414` (`dotnet build`), `:432`
  (the engine run); `RT/path_check.py:142` (python child); `S/scripts/autosound_ai.py:117`, `:119`, `:124` (git, in
  the key guard on the critic path), `:257`, `:261`, `:267` (`pbcopy`/`clip`/`xclip` via `communicate()`), `:2650`
  (`xattr`); `S/scripts/upkeep.py:285` (git) and `:594` (`urllib.request.urlretrieve`, no timeout);
  `S/scripts/issue_triage.py:43`, `:60`, `:190`, `:207` (gh). With a timeout, for contrast: `RT/deployment.py:83`
  (3 s), `RT/project_repo.py:41`, `:51`, `RT/provenance.py:91`, `S/scripts/upkeep.py:66` (the `run()` wrapper —
  the model to copy).
- **Breaks:** a desk run in TCC wedged by a stuck engine or `dotnet build`; a key check that hangs on a network
  filesystem.
- **Proposal (S–M):** route every call through a `run()` like `upkeep.py`'s (timeout → a return code, never a hang);
  `urlopen(timeout=)` in place of `urlretrieve`; also `tarfile.extractall(filter="data")` at `S/scripts/upkeep.py:607`.
- **Test:** a fake engine that sleeps → `run_engine` times out within the bound.

### T-50 · Low · Helper scripts that report success they did not have

- `copy_to_clipboard` never checks the return code (`S/scripts/autosound_ai.py:254-270`): a failing `xclip` still
  prints "✓ package copied" (in Ukrainian) (reproduced by the auditing session with a fake `xclip` exiting 1); on Windows the
  package goes to `clip` as UTF-8 without a BOM, which probably garbles the Ukrainian text (*unverified*).
- `S/scripts/issue_triage.py:60-63` returns `[]` when `gh` fails and then prints "nothing new!" (in Ukrainian) and exits 0 (`:220-223`).
- `autosound_ai.py --help` / `-h` → "unknown task: --help" (in Ukrainian), exit 1 (`:3114-3116`; F6 in §2), and the usage line
  (`:3051`) omits the `key` and `selftest` subcommands that exist.
- **Proposal (S):** check return codes; send UTF-16LE to `clip`; exit 1 when the source could not be read; `-h`.
- **Test:** a fake `xclip` exiting 1 → `copy_to_clipboard` returns False; a fake `gh` failing → exit 1.

---

## 6. Top 10, ranked by value over risk

Value = what stops going wrong for the user or TCC; risk = how likely the change itself breaks something (size,
reach, whether TCC must change in step). Known items are included where they are fixed by the same change.

| # | change | fixes | size | why this rank |
|---|---|---|---|---|
| 1 | **Strict reads at the gates and in `Process.load`**: "exists but unreadable" refuses; `_require_intake` gates on `complete`; a checker that cannot load or raises is a refusal | T-10, K-2 | S | the gates are the method's main enforcement and are open today on exactly the damaged-file population; a parity test with `contract --gate` keeps them honest; no behaviour change for a healthy project |
| 2 | **One `atomic_write_json` with a unique temp name** (+ fsync, + Windows retry) at every writer | T-8, T-17, part of K-3 | S–M | turns "a concurrent save bricks the project" into at worst a lost update; identical behaviour for a single writer |
| 3 | **`capture-check` stops creating `taken` entries** | T-1 | S | a corrupting write on every check with REW closed; a few lines in one function |
| 4 | **Assert ATF values, not types** | T-25 | S | test-only, zero runtime risk, guards the text the user pastes into the DSP |
| 5 | **Pin `gpg.ssh.program=ssh-keygen` in the three verify paths** (and pass `env` in `upkeep.verify_tag`) | T-35 | S | one `-c` per path; unblocks every install/update on a machine with a signing helper; the harness gains the case it isolates away today |
| 6 | **Tag ruleset + immutable releases** (settings), then a signed `SHA256SUMS` | T-36 | S (settings) + M | the settings half is free and closes the "moved tag serves another installer" path the signing was meant to close |
| 7 | **`seals.json`, the DSP draft and the journal stop reading damage as absence** (raise on unreadable; newline guard on append) | T-11, T-13, T-14 | S | three small refusals; each restores a protection the code already claims |
| 8 | **Ledger versions allocated with `O_EXCL`** (then the skill-owned lock + revision) | T-9, then T-18, T-12, K-3 | S, then M | `O_EXCL` alone ends silent overwrites of immutable snapshots; the lock is the bigger, riskier half because TCC must take the same one — schedule it with TCC |
| 9 | **`install.sh` handles PEP 668** (venv or uv 3.12 fallback) and exits non-zero when numpy is missing | T-34, T-44 | M | high value (current Linux, Homebrew Macs, plugin setup) but an installer change: needs the macOS and Linux runs the triplet rule asks for |
| 10 | **Test plumbing:** runner timeout + expected count + no silent skips; the by-path import probe; a CLI smoke per verb; recorded REW goldens | T-28, T-27, T-26, T-29 | S–M | no runtime risk; turns the 16 surviving mutations, the 4 runner gaps and the TCC import route into red runs |

Next in line: K-1 (REW write validation and read-back), T-37, T-41, K-6 + T-21 +
T-22 (the contract, §7), T-19, T-23, T-2, T-46.

---

## 7. The contract TCC relies on — proposed list, for the owner to adopt or not

What TCC uses today, written as the promises a `CONTRACT.md` would make. Each item says where it is defined now and
whether it is documented. Adopting it means: the list lives in the repo, a check holds the code to it (T-22's
guard), and a change to any item is named in the CHANGELOG's Upgrading note with the contract number bumped.

1. **Identity.** A `CONTRACT_VERSION` integer in one module, printed by `contract.py version --json` →
   `{contract_version, format_version, skill_version, sha}`. *Today:* none (K-6); the version is `plugin.json`'s,
   found by walking up from the skill folder (`RT/deployment.py:93-110`).
2. **`state/process.py <process-dir> <verb>`** — the 30 verbs in the usage text (`RT/state/process.py:2588-2693`):
   `show, plan, enter-phase, add-step, start, done, skip, block, reviewer, target, decision, session-start,
   session-close [--check], session-reopen, capture-start, capture-check [--session], capture-taken,
   capture-import, amp-gain, amp-changes, capture-knobs [--amend], capture-protective [--amend],
   listening-verdict, listening-verdicts, capture-supersede, handoff [--json], capture-skip, capture-close
   [--no-rew], check, selftest`. Exit codes: 0 done/yes · 1 refused/no (reason on stderr) · 2 usage · **a distinct
   code for an unexpected error** (proposed, T-23). Machine output: `show` → `{schema_version, updated,
   active_phase, phases, plan, capture, targets, reviewer}`; `plan` → `[{id, name, status, source, attempt, skip,
   phase, evidence, covers}]`; `handoff --json` → `{ok, missing, phase, resume, warnings, next_message}`.
   *Documented:* 4 verbs (`process-schema.md:209-243`).
3. **`contract.py check <dir> [--json] [--no-rew] [--gate | --phase0-gate]`** — exit 0/1/2; top-level keys
   `complete, cross_checks{…}, encoding_damaged, files[]{file, exists, schema_version, valid, issues, …}, id_fix,
   inherited, legacy, line_layout, map_ready, missing, ok, project_dir, prose, reply_language,
   reply_language_source, repo, row_gaps, sources_gone, sources_gone_where, to_confirm, unsealed`, plus the REW
   block, which must distinguish *skipped* from *unreachable* (T-2). *Documented:* no.
4. **`deployment.py [<project>] [--json]`** — `{verdict, summary, deployments[{path, exists, root, sha, version,
   ref, branch, origin, link, plugin?}]}`; exit 0 one method · 3 disagreement · 4 no identity · 2 usage
   (`RT/deployment.py:49`, `SKILL.md:80`). *Documented:* yes.
5. **`S/scripts/autosound_ai.py critic|advisor|ask|doctor|key`** — exit 0 ok · 1 error · 2 key file would be taken
   by git · 3 a model must be picked · 4 reviewer refused/failed; stderr markers `>> REVIEW_FILE: <rel>` (`:2899`),
   `>> REVIEW_ROUTE: omp|api|cli` (`:3031`, `:3261`, `:3309`), `>> PACKAGE_FILE:` (`:3342`); review files under
   `process/reviews/`. *Documented:* exit codes 3/4 only (`setup-critic-channel.md`).
6. **Other machine outputs TCC may read** — each to carry `"contract": N`: `naming.py <proj> parse` →
   `{code, code_current, modifier, position, control, version, version_n, method, params, inverted, title, note}`;
   `project_seed.py --json` → `{ok, written, channels, amps, flaws, questions, profile_open, problem, repo}` and
   `--describe --json` → `{car, dsp, channels, flaws}`; `verify --json` → `{summary, measurements, session?}`;
   `verify_prediction --json` (verdict as an enum, not prose — T-24); `predict --json`; `timebase
   --json`; `eq_propose --json`; `resonalyze_vc --json`. *Documented:* prose in `rew-tool-docs.md`, no key lists.
7. **Files and their versions** — with one read rule for all (refuse newer, migration hint for older —
   T-21):
   `project.json` (3, `RT/project.py:49`); `process/process-state.json` (3, `RT/state/process.py:45`; the doc says
   1); `process/journal.jsonl` (no version; events `{at, type, …}`, 24 types `RT/state/process.py:74-138`, five of
   them undocumented; a `written_by` header with `skill_sha`); `state/versions/v_NNN.json` (3,
   `RT/state/state.py:62`; immutable once written), `state/slots.json`, `state/seals.json` (unversioned);
   `dsp_profile.json` (3 + `skill_sha`, `RT/dsp_profile.py:57`, `:459`) and `dsp_profile.draft.json`;
   `glossary.json` (1, `RT/naming.py:309`).
8. **How to write them** — the atomic-write protocol (T-8) and the lock (T-18): which file to lock,
   for how long, and that every writer (TCC in-process, TCC via CLI, a session's CLI) takes it. *Today:* none; TCC's
   own lock is invisible to the CLI.
9. **The importable modules** — an explicit list (today TCC loads 14: `rew_api`, `state/state`, `state/process`,
   `naming`, `dsp_profile`, `project`, `dsp_math`, `resonalyze_vc`, `project_seed`, `eq_export`, `protective`,
   `listening`, `gates/side_effect`, `car_profile`), each with `__all__`, and the guarantees: loadable by path from any
   directory; no `sys.path` edit; no stdout; no `SystemExit`; no process-wide state that outlives a call (or it is
   named, like the DSP rate — T-20). Or the opposite decision: TCC uses the CLI only, and this item is
   empty. *Today:* undocumented; T-19, T-27.
10. **Environment variables** — `AUTOSOUND_PROJECT_DIR`, `AUTOSOUND_STATE_ROOT`, `AUTOSOUND_SKILL_ROOT` (the copy a
    front-end declares), `REW_API_URL`, `AUTOSOUND_NO_GH`, `AUTOSOUND_KEYSTORE`, `AUTOSOUND_CRITIC_*`,
    `AUTOSOUND_SKIP_TAG_VERIFY` (developer only) — each with a stated precedence against explicit arguments (today
    `$AUTOSOUND_STATE_ROOT` silently overrides an explicit project in `RT/state/process.py:564-566`). *Today:* ~22 variables, listed nowhere.
11. **REW write semantics** — what `set_filters`/`set_filter`/`rename_measurement` guarantee after they return
    (read back and verified — K-1).
12. **Compatibility policy** — what a patch may change in items 1–11 (today `CHANGELOG.md:39-42` allows a
    return-contract change in a patch with a prose warning) and where the TCC-facing notes live (today partly on
    hub issues, `CHANGELOG.md:209`).

---

## 8. What I could not check, and why

- **REW itself.** No REW here; a fake HTTP server stood in. Unverified live: that `PUT /measurements/{id}` clears
  notes on a rename (K-1); REW's exact payload shapes (no recorded payload exists to compare with — T-29);
  REW under a slow machine.
- **Windows.** No PowerShell, no Git Bash, no DPAPI here. Unverified: `os.replace` raising `PermissionError` while
  TCC's watcher holds a file (T-17); Git-for-Windows `grep` on a CRLF ready file (T-39); the hook
  without Git Bash; `clip` and UTF-8; journal appends under concurrent writers on NTFS; any run of `install.ps1`
  (only read; CI parses it).
- **macOS.** No Apple Python 3.9.6 (pip 21.2.4, LibreSSL), no Homebrew Python (PEP 668 inferred from Homebrew's
  policy, reproduced on Ubuntu), no `pbcopy`, BSD tools, codesign.
- **TCC.** `ayukhno/autosound-tcc` was not read: cloning it was not permitted in this session. Unverified: whether TCC imports
  `dsp_profile` before `project` (T-19), models responses in-process (T-20), builds a
  preview on `seed()` (K-4), holds a `Project` across user actions (T-12), or adds `rew_tool/` to
  `sys.path` itself. Its lock (`process_writer.py:119-150`) is cited from the 2026-09-09 review, not read.
- **GitHub settings.** `immutable: false` on the `v3.1.1` release was read here through the API; the ruleset list
  and `immutable-releases` were read by a parallel auditing session — they are settings, not code, and can change
  without a commit.
- **The installers end to end.** Not run (they install software); functions and blocks were cut out and run with a
  scratch `HOME`. The .NET engine build (`engine` CI job) was not reproduced — no SDK here.
- **Whether a given signing helper verifies.** T-35 is reproduced with this sandbox's sign-only helper;
  whether 1Password's `op-ssh-sign` (common on macOS) also refuses `-Y verify` is not known here.
- **History.** The checkout is shallow (50 commits); fix commits in §2 were found in a full scratch clone at the same
  commit.
- **Reproductions by parallel sessions.** This audit was run with parallel read-only sessions on the same commit;
  results marked "reproduced by the auditing session" are theirs, with commands and fixtures kept in the scratch
  directory; results marked "reproduced" were re-run for this report. Line numbers were re-checked at the base in
  both cases.
