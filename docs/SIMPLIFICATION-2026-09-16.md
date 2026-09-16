# Simplification review — 2026-09-16

Read-only. Four surveys over the tree at `9f0c7c5` (branch `test-fixes-2026-09-14`), the wave-1
findings (docs/BUGS-2026-09-11.md, docs/TODO.md S-001…S-011, hub #121–#125 and #150–#152, repo
issues #24–#38) and the 2026-09-09 release-readiness review. Nothing was changed; no ticket was
filed. Scope, by the user's decision: the model-facing documents, the code (`rew_tool/`,
`scripts/`) and the installers.

The question that started this — "would sub-agents, tool descriptions and a retrieval base
improve the skill?" — is answered in §5. The short answer: not before §2–§4, and mostly not in
that form.

## 0. Verdict

1. **The 09.09 review fixed the documents; wave 1 broke on the records.** 11 of its 14 top items
   are done. Of the 23 wave-1 findings it predicted 5; the other half — schema fields that do not
   exist, a title grammar two parsers read differently, a third-party CLI run headless in the
   wrong directory — a document review cannot reach. §1.
2. **The tester hits the same three things repeatedly.** `_N` filed three times (#34, #152, #37);
   "not a failure rendered as failure" twice (#29, #32); "the phenomenon is known, there is no
   field for it" three times (#30, #31, #36). One parser and one schema guard remove all eight.
3. **14 of 23 findings are solved by removing or merging something**, 9 by adding. The
   simplification plan is not a diet — it is: one home per rule, one parser per title, one entry
   for the reviewer, one reader for REW, one CI run for the Windows installer.
4. **Size is a cost without a measured failure.** Every phase reads more than on 09.09 (Phase −1:
   119 → 124 KB), the model-facing set is 442 KB not the ~180 KB assumed, and nobody in wave 1
   reported a size-shaped failure. Compression comes as a by-product of "one home", not as a goal.
5. **Not now:** a single `rew_tool` CLI, Workflow orchestration (#26), retrieval over past
   projects (blocked by #36). Reasons in §3.7, §5.

## 1. What the tester hits — the evidence base

Wave-1 findings clustered by cause, not by symptom. `simplify` = solved by removing/merging;
`add` = needs a feature. Cluster H (TCC-side, #121–#125, the TCC halves of #150) is out of scope.

| cluster | members | cause in one sentence | the one change | kind |
|---|---|---|---|---|
| A · the record cannot hold what the method teaches | #29 #30 #31 #32 #36 | a distinction the method makes (not-applicable, skipped-with-reason, L/R tilt, THD %, inherited) has no field on the way to disk, so the layer below reads it as failure or absence | no single change — five schema slots; what stops the next one is a **round-trip guard**: anything a producer computes must persist and print, or its selftest fails | add |
| B · title grammar: `_N` names three things | #33 #34 #152 #37 | one string encodes code / state / method / tag; `parse_name` accepts what `_title_version` drops; "config version" means the measured state, the ledger snapshot or a saved configuration | **one parser** returning a typed record and refusing what it cannot account for; `_N` redefined as "DSP state number" | simplify |
| C · a rule with more than one home | #35 #28 S-007, review §0 1–10 | docs and tools drift because the rule lives in both; the model follows whichever it read | extend the v3.0.47 pattern (one home + `docs-check`) to "the tool a phase names must accept the inputs the phase produces" | simplify |
| D · the reviewer is someone else's CLI, headless, in the wrong directory | #27 hub#130 #28 hub#150.1/.2/.4/.5 | the method drives a third-party CLI whose permission model, model list and cwd it does not control, and calls a failed call a result | **one wrapper** that runs in the project dir, preflights on the real call path, and never files or announces a "review" when nothing came back | simplify |
| E · Windows installer is hand-tested once per wave | S-008 S-009 S-010 #25 | `install.ps1`'s functions are read by CI (`installer-consistency.py`), not run | run the PowerShell functions on `windows-latest` (S-008's own "done" line) | add |
| F · REW treated as a GUI, not a data source | hub#151 #35 | desk tools take the shape the export pipeline produces, not what the live session holds; a session either cannot run them or changes the Arbiter's REW view | **one live REW reader** — raw, view-independent, never writing the view — behind every desk tool | simplify |
| G · method gaps | #38 #26 S-001…S-006 #24 | the capability does not exist yet | none; each is its own work and stays out of this plan | add |

Filed twice or more under different ids: `_N` (#34 ↔ #152 ↔ #37) · not-a-failure as failure
(#29 ↔ #32) · known phenomenon, no field (#30 ↔ #31 ↔ #36) · desk tool cannot take what REW
holds (#35 ↔ hub#151) · reviewer call dies into the clipboard (#27 ↔ hub#150.1, #28 its
documentation half) · wrapper writes relative to cwd (150.2 ↔ 150.4) · the Windows install says
something that isn't so (S-009 ↔ S-010, #21 before the wave).

## 2. Model-facing documents

### 2.1 Facts

- Set: `SKILL.md` 25,310 B + `references/core/` 20 files 303,238 B + `references/phases/` 9 files
  113,827 B = **442 KB** (`patterns/` and `tooling/` on top, on demand). Largest:
  `diagnostic-techniques.md` 67.5 KB · `rew-tool-docs.md` 60.2 KB · `project-intake.md` 42.9 KB ·
  `capabilities.md` 41.1 KB · `rew-api-quirks.md` 31.7 KB · `setup-critic-channel.md` 28.5 KB.
- Mandatory read per phase (SKILL.md + active + adjacent phase + what the phase file mandates),
  bytes now vs review 09.09: −1: 124,109 / 119,146 · 0: 120,089 / 114,492 · 1: 86,156 / 83,985 ·
  2: 70,463 / 68,134 · 3: 65,244 / 62,915 · 4: 81,216 / 81,117 · 5: 33,523 / 33,424. Every phase
  grew. `RELEASE-PLAN-3.1.0.md` relabelled the compression step "verifiability instead of
  compression" — a decision, and this review does not reopen it.
- No orphans, no missing files: all 20 core and 9 phase files are reachable from SKILL.md's
  Reference Map / Sliding Window; all 38 paths in the map resolve. `happy-paths.md` and
  `why-these-rules.md` have exactly one inbound link each.
- Narrative share ("bought on…", dated incidents): `SKILL.md` 2–5% (outsourced to
  `why-these-rules.md` on 09.09 — done) · `phase_0_baseline.md` 25–30% · `phase_1` 15% · `phase_2`
  15% · `review-loop.md` 35–40% · `why-these-rules.md` 70–75% by design.
- Existing guards: `scripts/docs-check.py`, `docs/review-2026-09-09/check_docs.py` (43 module
  bullets, 0 problems), `rew_tool/capabilities.py --selftest` (97 board rows, 0 problems). They
  check that named commands and flags **exist**; none checks that a rule has one home.

### 2.2 Rules with more than one home (top of 20 found)

| rule | copies | where |
|---|---|---|
| protective HPF ≥ 1.1×Fs @ ≥ 24 dB/oct is a hard floor | 8 | capabilities:26 · virtual-first:78,132 · phase_0:79 · capture-session-sheet:95 · phase_1:57 · phase_-1:27 · project-intake:127–128 |
| ledger / settings sheet is generated, never hand-edited; bank via `apply.propose` → `v_NNN` | 8 | SKILL:79 · naming-and-structure:40,133 · phase_1:74 · phase_3:65 · phase_5:50 · driver-discipline:13 · capabilities:146 |
| de-embed the protective filter before reading phase; unmarked baseline solo → refused | 7 | project-intake:133 · phase_0:81 · phase_1:37 · phase_2:77 · capabilities:58 · estimator-scope:118–127 · virtual-first:136 |
| machine files win over prose/chat | 6 | SKILL:65,111 · process-phases:12–21 · happy-paths:25 · review-loop:13–17 · knowledge-architecture:14 |
| round-based batch cadence; per-parameter looping is Level-2 only | 5 | SKILL:99 · phase_2:31 · happy-paths:39 · project-intake:162 · diagnostic-techniques:155 |
| drift-watchdog: reviewer re-reads disk; re-anchor or `/clear` + resume | 5 | SKILL:54,79,172 · driver-discipline:16 · process-control:26 |
| naming grammar `<code>_<vN> (sw\|rta)`; evidence must resolve | 5 | SKILL:82 · why-these-rules:18–23 · naming-and-structure:33 · capabilities:148 · project-intake:41–44 |
| reviewer fallback ladder | 4 + canonical | SKILL:54,177 · project-intake:58–59 · process-control:31 · canonical setup-critic-channel:250–283 |
| identical "🗺️ Virtual-first? … this file stays the authority" paragraph | 4 verbatim | phase_0:5 · phase_1:5 · phase_2:5 · phase_3:5 |
| L/R symmetry is the crossover default; fix asymmetry with EQ/gain | 4 | filter-types:156–164 · phase_1:58 · diagnostic-techniques:106,118 |
| side-effect gate on any GitHub post | 4 | feedback-loop:56,101 · capabilities:163 · driver-discipline:32 |
| Schroeder region: never boost a single-point dip | 3–4 | diagnostic-techniques:88 · phase_2:53 · estimator-scope:109 |

Twelve more at 2–3 copies (session-close order, re-entrant gates, token diet, absolute values,
fixed-slug lookup, prompt-injection defence, the Three Roles table).

Copies are how contradictions are born: cluster C is this table. The 09.09 review named it
("дублі-доктрини → один дім") and it was not done.

### 2.3 Live contradictions (verified in the tree)

1. **Ladder.** `SKILL.md:177` and `setup-critic-channel.md:256–271` give 6 rungs (wait → other
   vendor CLI → clipboard → same vendor higher tier → separate Claude session → human).
   `project-intake.md:58–59` calls its copy "one list" and gives 5 — the "wait" rung is missing.
   `review-loop.md:21` only points, so the clash is 2-way, not 3-way.
2. **Model classes.** `process-control.md:36–39`: "Model names are not maintained here … gave a
   table until 2026-09-09". `SKILL.md:162` (Reference Map) and `:178` still send the reader to
   `process-control.md §1` for "current defaults and per-task classes".
3. **phase_2 checkpoints.** Goal node (`phase_2_eq.md:18`): one critic checkpoint, a second after
   2b only if joint alignment was reworked. Runbook: "(1 of 2)" at :79 and "(2 of 2)" at :108,
   unconditional.
4. **`review-log.md` vs `audit-trail.md`.** `driver-discipline.md:30` says "check
   `review-log.md`"; the shell wrappers write `$PROJECT_MIRROR/review-log.md`
   (`_gemini_common.sh:244`, `_claude_common.sh:60`); nine other documents name the review record
   `audit-trail.md`. Whether these are one artifact or two is not stated anywhere.
5. **A number cited to a section that does not carry it.** `SKILL.md:99` attributes "EQ max boost
   +6 dB" to `phase_2_eq.md §2a`; that section has no numeric ceiling. The number lives only in
   `SKILL.md:99` and `happy-paths.md:39`.

### 2.4 Structure

- `phases/phase_-1_intake.md` is a 29-line stub; the Phase −1 procedure (interview, gates, file
  generation) is the 42.9 KB `core/project-intake.md` — the inverse of the core = doctrine /
  phases = procedure split that `knowledge-architecture.md:10` defines. `project-intake.md` is
  also the most linked file (13 inbound).
- `SKILL.md` "🏛️ Three Roles" (51–58) is a shorter copy of `review-loop.md:35–41` (no Cold-auditor
  row); "🛠️ Review Channel" (170–179) re-derives cadence, TWO-PASS and the ladder that
  `review-loop.md` and `setup-critic-channel.md §7` own.
- `analysis-playbook.md`'s tool table repeats `capabilities.md` rows (flaw_map :19/:24,
  xover_candidates :18/:25, `capture-check --session` :27/:50).
- `process-control.md`'s back half is capture/naming doctrine ("record and hardware drift apart",
  "version identifiers are a namespace"), not operating modes; overlaps `naming-and-structure.md`
  and `diagnostic-techniques.md`.
- Reference Map one-liner for `process-control.md` ("model classes") no longer matches the file.

### 2.5 Recommendation — documents

**One home per rule, checked.** Not a rewrite: for each of the 20 rules, pick the home (the file a
phase sends the model to first), keep one sentence + link everywhere else, and register the rule
in a small index (`references/core/rule-index.md` or a table inside `why-these-rules.md`: rule id ·
home · path:line). `docs-check.py` then fails when a rule id's sentence appears in full outside its
home. The mechanism already exists for commands; this is the same guard for doctrine.

Order, by what wave 1 touched: the ladder (contradiction 1, cluster D) → naming grammar (cluster B)
→ ledger/bank rule → HPF floor → de-embed rule → machine-files-win → drift-watchdog. Fix
contradictions 2–5 in the same pass (each is one edit).

Structural moves, each one commit: (a) make `project-intake.md` the Phase −1 file or move the
procedure into `phases/` and leave doctrine in core — choose one; (b) `SKILL.md` Three Roles and
Review Channel → pointers; (c) drop the 4× boilerplate paragraph in favour of one line in
`virtual-first.md`; (d) `analysis-playbook.md` tool table → link to the board; (e) split
`process-control.md`'s back half into `naming-and-structure.md`.

Expected by-product: SKILL.md −6…8 KB, Phase 0 read −15…20 KB. Not a target; do not chase §4 of
the 09.09 review until a session fails in a size-shaped way.

Narrative: `phase_0_baseline.md` at 25–30% is the one file where the 09.09 rule ("the rule stays,
the story becomes one sentence with a ticket id") was not applied. Apply it there; leave
`review-loop.md`'s history alone unless the file is being rewritten anyway.

## 3. Records and tooling

### 3.1 Facts

- `rew_tool/`: 54 modules, 33,794 lines; 11 modules > 800 lines (`predict.py` 2,550 ·
  `state/process.py` 2,232 · `resonalyze_vc.py` 1,949 · `project.py` 1,809 · `dsp_profile.py` 1,684
  · `state/state.py` 1,592 · `dsp_math.py` 1,525 · `contract.py` 1,227 · `rew_tool.py` 1,210 ·
  `resonalyze_ir.py` 916 · `verify_prediction.py` 885). **No orphans** (`capabilities.py
  --selftest`: 97 rows, 0 problems); `console.py` is the one undocumented module, by design.
- Entry points: per-module CLIs (`python3 rew_tool/<module>.py …`), 65 real subcommands across 6
  multi-verb modules; no `__main__`, no single CLI, no Makefile.
- Tests: no `tests/` dir; each module carries `_selftest()` (~1,660 asserts), run by
  `scripts/run-selftests.sh` (≈ 74 checks) and CI `checks.yml` on `ubuntu-latest`. Duplicate
  function names (`render` ×10, `report` ×5, `main`) are the one-file-one-CLI convention, not
  copy-paste; no `load_project`/`read_json`-style duplication found.
- Documentation gaps found by grep, missed by the board's verb regex: `dsp_profile.py reset-field`
  (`dsp_profile.py:1077`) is in no document; `naming.py codes` is in `rew-tool-docs.md` but not on
  the board.
- `scripts/`: 3 vendors × (critic + advisor) shell wrappers + 3 `_common.sh` (Gemini's is 476
  lines) + 3 `.cmd` + `autosound_ai.py` (1,154 lines, stdlib only). `autosound_ai.py` covers all
  three vendors, local CLI and direct API, clipboard mode, and all three roles; on Windows the
  `.cmd` files just exec it. The shell wrappers add per-vendor `--doctor` detail (macOS quarantine,
  "closed gemini-CLI" wording). Docs (`SKILL.md:176`, `setup-critic-channel.md`) recommend the
  shell wrappers first and `autosound_ai.py` as the fallback.

### 3.2 One parser for titles (cluster B — #33, #34, #152, #37)

Today `naming.parse_name` accepts a trailing tag that `_title_version` then drops, so a version
silently becomes `None` (#34, 16 titles), impedance sweeps have no legal title (#33, 7 of 102
refused), and the `_N` suffix is read by the tester as "the saved configuration" (#152) — the
opposite of the ledger's meaning. Change: one function that returns a typed record (code, DSP
state number, method, tag, kind) or a refusal naming the part it could not place; every consumer
(`process.py`, `contract.py`, `flaw_map.py`, `project.py`) takes the record, never the string.
Rename in docs: `_N` = **DSP state number** (`v_NNN` in the ledger), never "config version". Cost:
M (one module, four consumers, selftests). Removes four findings, three of them the same one.

### 3.3 Round-trip guard for the schema (cluster A — #29, #30, #31, #32, #36)

Five missing slots: `applicable` survives write (#29), `level_tilt` kind (#30), THD percentage
(#31), skipped-with-reason ≠ MISSING (#32), `inherited` provenance with a resolvable source path
(#36). Each is small; the guard is what matters: a selftest pattern "produce → write → read →
render must show every field the producer set", applied to `flaw_map`, `contract`, `process`
snapshots. Cost: S per slot, M for the guard. Note #36 is safety-relevant (an inherited Fs fed the
1.1×Fs protective filter) — first of the five.

### 3.4 One entry for the reviewer (cluster D)

`autosound_ai.py` is already the superset and the Windows path. Make it the only entry: the six
`.sh` wrappers become two-line shims (or go), the `--doctor` detail they carry moves into
`autosound_ai.py doctor`, and three behaviours are fixed in one place instead of six —
run in the **project** directory, never the checkout (150.2); a failed call returns a refusal, not
a "review" file plus advice to log it (150.4, 150.1); a pass-through for per-run CLI flags (150.5).
The docs then name one command. Cost: M. Removes six findings; makes the ladder (2.3 #1) shorter
to state.

### 3.5 One live REW reader (cluster F — hub#151, #35)

`rew_api.py` exists; the desk tools (`flaw_map.py`, `xover_candidates.py`) read the export
pipeline's v7 files instead, so a Phase-0 project whose solos live only in REW cannot run them
(#35), and a reader that refuses smoothed data makes the session toggle the user's 1/6-octave view
off and on (hub#151). Change: one function "give me raw, unsmoothed channel data for measurement X"
that reads the REW API view-independently and never writes the view; desk tools accept either
source. Cost: M. Prerequisite for anything in §5.

### 3.6 Small, one commit each

- Board verb regex → include `reset-field`; add `naming.py codes` to the board.
- `review-log.md` / `audit-trail.md`: decide one name and one writer (2.3 #4).

### 3.7 Not now

- **A single `rew_tool` CLI.** 97 board rows and 12+ SKILL.md calls name per-module commands; a
  merge is a large rename during waves for a gain (discoverability, one `--root`) nobody has asked
  for. Revisit when the board is machine-queried (§5).
- **Splitting the 11 large modules.** No finding points at their size; `predict.py` and
  `process.py` are large because the method is.

## 4. Installers

Facts: `install.sh` 1,368 lines, `install.ps1` 1,334 lines, mirrored by `installer-consistency.py`
in CI. Components: Claude Code, the skill (git clone + symlink/junction, not the plugin
marketplace), numpy (mandatory), uv + Python 3.12 + TCC (opt-out `--terminal`), `agy` (opt-out
`--no-reviewer`), `gh` (**asks** by default; used only for project backup), `omp` (opt-out, TCC
mode only), CLT / Git for Windows when missing. REW is never installed. `installation.md` (112
lines) describes a different path — the Claude Code plugin marketplace, pinned at 2.8.3 — so there
are two install stories and `deployment.py` + the beta channel exist to reconcile which copy is
loaded.

Recommendations:

1. **Run `install.ps1`'s functions on `windows-latest` in CI** (cluster E; S-008's own done line).
   Reporting bugs like S-009 ("will install" after installing) are visible only when the code runs.
   Cost: M (the functions need a dry-run seam). Removes S-009/S-010-class findings before the VM.
2. **Fewer interactive branches.** `gh` "asks" → a flag with a default (`--github` off; backup is
   opt-in). Decide #25 (omp opt-in) the same way. Every prompt is a Windows path nobody tested.
   Cost: S.
3. **One install story.** Either the plugin marketplace becomes the delivery for Claude-Code-only
   users at a 3.x pin (RELEASE-PLAN's "move the catalog pin off 2.8.3"), or `installation.md`
   describes the clone+symlink path only. Two stories cost `deployment.py` reconciliation,
   `installation.md`, and the beta-channel checkout. Decision for the user; recommendation: keep
   clone+symlink as the only supported path until the catalog pin moves, and say so in
   `installation.md`.
4. **Not now:** replacing two 1.3 K-line installers with one Python installer — Python is itself
   something the installer provides (uv), so the bootstrap must stay native.

## 5. Agents, tool descriptions, retrieval — the original question

- **Tool descriptions already exist**: the board (`capabilities.md`, 97 rows, selftest-checked) in
  the Claude Code path; ~30 MCP tools in TCC. Sub-skills or more agents would add a third
  description of the same commands — one more home for cluster C. What would help is the board
  being **queried instead of read**: `capabilities.py find "bank a change"` returning 3 rows, so a
  phase reads its own file and asks the board, instead of loading 41 KB. That is retrieval, without
  a base, over a file the tree already checks. Cost: S. Do it after §2.5, when the board is the only
  home for command doctrine.
- **Sub-agents as reviewer**: banned by the user's ruling of 09.09 (same-model blind spots, ~15/20
  deadlocks); the docs now agree (`setup-critic-channel.md §7`). Sub-agents as parallel hands for
  per-channel analysis is issue #26, deferred to 3.2; nothing in wave 1 argues for pulling it
  forward.
- **Retrieval over past projects** (the "similar car already tuned" case): the archive is
  `community-inbox/`, harvested by hand, and #36 shows why automatic reuse is unsafe today — an
  inherited fact with prose-only provenance reached a safety gate. Precondition: §3.3's provenance
  slot and a resolvable source. After that, the cheapest form is a script over `project.json` files
  (car, drivers, Fs, config class → path), not embeddings.
- **Retrieval over the method itself** (search instead of reading the 442 KB): the failures on
  record are contradictions and duplicates, and a search over contradicting files finds the
  contradiction faster. One home per rule first (§2.5); then the sliding window already is the
  retrieval.

## 6. Priority order

| # | change | cluster | removes | cost | where |
|---|---|---|---|---|---|
| 1 | one title parser, `_N` = DSP state number | B | #33 #34 #152 #37 | M | `rew_tool/naming.py` + 4 consumers; `naming-and-structure.md` |
| 2 | provenance slot + resolvable source; round-trip guard | A | #36 first; #29 #30 #31 #32 | S×5 + M | `project.py`, `flaw_map.py`, `contract.py`, `state/process.py` |
| 3 | one reviewer entry (`autosound_ai.py`), project-dir, honest failure, flag pass-through | D | #27 hub#130 #28 hub#150.1/.2/.4/.5 | M | `scripts/`, `setup-critic-channel.md`, `SKILL.md:176–178` |
| 4 | one home per rule + rule index + `docs-check`; fix contradictions 1–5 | C | #35 #28 S-007; prevents the next #27 | M | `references/core`, `references/phases`, `scripts/docs-check.py` |
| 5 | one live REW reader behind desk tools | F | hub#151 #35 | M | `rew_api.py`, `flaw_map.py`, `xover_candidates.py` |
| 6 | `install.ps1` functions run in CI; `gh`/omp flags, no prompts | E | S-009 S-010 #25 | M + S | `.github/workflows/checks.yml`, both installers |
| 7 | structural moves (a)–(e), phase_0 narrative | — | size by-product | S each | `SKILL.md`, `phases/`, `process-control.md` |
| 8 | board queried, not read | — | — | S | `capabilities.py` |

1–3 fit one wave. 4 and 7 are the same pass over the documents. G (method gaps) and #26 stay on
their own tracks.

## 7. Decisions — taken 2026-09-16

1. `_N` = "DSP state number" in docs and parser only; titles already on disk stay and are accepted.
   No migration. → #39.
2. Shell reviewer wrappers are deleted, not shimmed; `autosound_ai.py` is the one entry and
   carries their `--doctor` diagnostics. → #41.
3. Phase −1: the procedure moves to `phases/`, doctrine stays in `core/project-intake.md`.
4. Install story: clone+symlink only, until the catalog pin moves off 2.8.3; `installation.md`
   describes that path alone.
5. `gh` off by default, `--github` opts in; `omp` off by default, `--omp` opts in (closes #25 when
   done).
6. Tickets now: steps 1–3 only — #39 (parser), #40 (provenance + round-trip guard), #41 (reviewer
   entry). Steps 4–8 wait for that wave to land.
