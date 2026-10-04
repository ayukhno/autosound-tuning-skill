# Audit of the instructions the model reads — 2026-10-04

**Base: commit `7b3232b`** (`main` on 2026-10-04; `git describe` → `v3.1.1-7-g7b3232b`). Every
`file:line` below is at that commit. Paths are relative to `skills/autosound-tuning/` unless they start
with a repo-root name (`README*`, `FAQ*`, `ADVANCED.md`, `CHANGELOG.md`, `scripts/`, `commands/`,
`hooks/`, `.claude-plugin/`, `docs/`).

**Lens.** What the model reads (SKILL.md, references, knowledge, assets, the reviewer's prompt files,
evals, commands, the plugin and skill descriptions, the READMEs): when it reads it, what it costs, and
whether it says one thing. Whether the tuning method is *right* (acoustics, targets, thresholds) is out
of scope.

**Mode.** Read-only. Nothing in the repository changed except this file. Outside the repository: a
symlink `~/.claude/skills/autosound-tuning` was created in the session container so that a fresh
`claude -p` could be asked what it sees (removed at the end), and throwaway projects lived in the
session scratchpad.

**Quotes** from the repository are verbatim, including the Ukrainian strings the skill and its tools
print. An English gloss follows each in square brackets.

**Token estimates** are `characters ÷ 4` (Python `len()` of the decoded text). For SKILL.md the
`words × 1.3` figure is given beside it as a cross-check; the two differ by about a third on this
text, which is dense with paths and code. Cyrillic text costs more tokens per character than this
estimate assumes.

**How it was done.** I read SKILL.md, every phase file, and the core files on the routes. Five
read-only sweeps ran in parallel. I re-checked the claims this report leans on; in §5, ✓ marks
the quotes I re-read myself:
- the prior review's A+B findings;
- its D+E findings;
- documented commands against the parsers, in the files no checker scans;
- duplicates and dangling references;
- README language drift.

I also ran:
- the repo's four documentation checkers, plus `doc-commands-check.py --run`;
- `claude plugin validate`;
- a fresh session asked to quote the description it is shown;
- two small trigger probes (11 queries, one run each, `--model sonnet`);
- per-verb `--help` probes of `process.py`, on scratch projects.

---

## 0. Verdict in one paragraph

The 2026-09-09 review's **sequence** findings, the ones that broke a session, are almost all fixed:
- the capture round is opened;
- virtual-first records the target and the flaw map before Phase 1;
- `enter-phase -1` comes first;
- `registry render` takes `--root`;
- the reviewer step closes against a file;
- there is one contract and one reviewer ladder.

Two things went the other way.
1. **Size.** SKILL.md grew from 25.3 KB to 36.4 KB, about 8.9K tokens. Since 09-09 the always-on rules
   no longer fit Claude Code's 5,000-token re-attach budget after auto-compaction. What each phase
   reads grew 18–54 % (35–54 % in Phases −1 to 3): virtual-first.md doubled to 39 KB and is still read "alongside" in four
   phases, and naming-and-structure.md doubled to 35 KB.
2. **New contradictions entered the text that is always loaded or always sent:**
   - the model is told the plugin route is the 2.x line and to uninstall it (I-1);
   - the reviewer is told that the prose is its single source of truth (I-2);
   - SKILL.md still says the owner's sentence gates Phase 0 (I-11);
   - a renumbering of virtual-first left its pointers aimed at the wrong steps (I-6).

The trigger works: no false positives and full recall in 11 probes. The description is still 1,808
characters against a 1,024 limit, and the last 272 never reach the model.

---

## 1. The repo's own checkers — verdicts

| checker | verdict at `7b3232b` | what it covers / misses |
|---|---|---|
| `scripts/docs-check.py` | `docs OK — 8 rule(s)`, exit 0 | Eight phrase rules: data-not-instructions, phase-source, references-orphans, capture-round-opened, state-source, ledger-root, install-ref, protective-floor. None of the findings below is one of those eight phrases. |
| `scripts/doc-commands-check.py` | `125 documented command line(s) found in 2 document(s)`, exit 0 | **Scans only `capabilities.md` and `rew-tool-docs.md`** (`scripts/doc-commands-check.py:39-40`). SKILL.md, the phase files, core, knowledge and assets are not scanned (I-17). |
| `scripts/doc-commands-check.py --run` | `34 run, 91 skipped (writing, or a partial reference), 0 refused by argparse`, exit 0 | Skips every writing verb, which is where I-15 lives. |
| `scripts/tool-docs-check.py` | `47 module entries · 0 wrong · 37 without a dependency line`, exit 0 | Module ↔ doc existence only. |
| `scripts/i18n-check.py` | `i18n OK — 2 document(s), 6 translation(s)`, exit 0 | Root README/FAQ only. Compares heading-level sequence and fenced code blocks (`scripts/i18n-check.py:48-62,89-106`). It is blind to prose, tables, inline code, links, anchors, numbers, deleted paragraphs and a deleted translation: the README sweep's probe on a scratch copy (six such drifts in `README.uk.md`, `FAQ.pl.md` removed) still printed OK, exit 0. |
| `claude plugin validate .` | passed with 2 warnings: `id` unknown in `marketplace.json`; root `CLAUDE.md` not loaded as plugin context | Does **not** check the description length (I-4). |

---

## 2. The 2026-09-09 review, finding by finding (this lens)

Status at `7b3232b`: **FIXED**, **OPEN** (still there), **CHANGED** (partly fixed or a new form),
**MOOT** (the file or section is gone). Review files: `docs/review-2026-09-09/review-{A,B,D,E}-*.md`.
Findings that live in installer code or in TCC are left out unless they reach a text the model reads.

### 2.1 Review A — phases and sequence

| # | finding (09-09) | status | evidence at `7b3232b` |
|---|---|---|---|
| A1 | "improve" −1→3→4 fails `enter-phase 3` | FIXED | `references/phases/virtual-first.md:21-61` "Two ways in… The same phases"; `:59` "Do **not** improvise a shorter phase order" |
| A2 | virtual-first builds the flaw map in 1.1 and never records `target` | FIXED | `virtual-first.md:150-157` (0.8: target + flaw map before Phase 1); `:163-167` 1.1 reads it |
| A3 | capture round never opened | FIXED | `phase_0_baseline.md:66`, `virtual-first.md:113`, `capture-session-sheet.md:44` |
| A4 | `enter-phase -1` seventh, not first | FIXED | `phase_-1_intake.md:37` "Entry condition, before step 0" |
| A5 | happy-paths B reads the changelog / a nonexistent block | CHANGED | `core/happy-paths.md:25` now machine files first; `:28` "▶️ NEXT STEPS list" is still defined nowhere; still no `deployment.py` step |
| A6 | "path" means three things | OPEN (and against decision §9 item 3) | `core/project-intake.md:142` "### Path: virtual-first or iterative"; `core/process-phases.md:55` "Phase −1 picks it (or the iterative fallback)"; banners `phase_0/1/2/3:5` "If Phase −1 chose…"; vs `virtual-first.md:72` "There is no separate 'iterative path' to choose" → I-12 |
| A7 | Phase-0 exit is two gates, but the text says "one command" | OPEN | `phase_0_baseline.md:196` "one command, not a memory"; `enter-phase 1` does not run `--phase0-gate` (an evidence-less row: `--phase0-gate` exit 1, `enter-phase 1` exit 0) |
| A8 | plain `check` where the gate needs `--gate` | OPEN (moved) | `phase_-1_intake.md:167` "`contract.py check <project>` — should report every machine file present" vs `:15` "**`--gate`, not plain `check`**", in the same file |
| A9 | two step numberings | CHANGED (worse) | → I-6 |
| A10 | "Phase 6" | OPEN | `core/process-phases.md:39` "Phase-5/6 ear check"; `phase_-1_intake.md:142` "a Phase-6 voicing move" |
| A11 | `eq_propose --rta` | OPEN | `phase_3_control.md:7`; `eq_propose.py --help` has no `--rta` |
| A12 | `python3 rew_tool.py …` from the skill root | OPEN | `phase_1_foundation.md:119`, `phase_2_eq.md:30,79` ("can't open file …/rew_tool.py") |
| A13 | `scripts/docs-check.py` named as skill-relative | OPEN | `core/process-phases.md:22,36`; `tooling/installation.md:12` |
| A14 | "Three tools, three artifacts" heads a list of four | OPEN | `phase_0_baseline.md:108` vs `:120` "These four" |
| A15 | prose inside the code fence hides `target` | OPEN | `phase_0_baseline.md:44-47` |
| A16 | "as described in Phase 1"; Cyrillic in English text | OPEN | `phase_0_baseline.md:61` "ВЧ/СЧ [tweeters/mids] as described in Phase 1"; `phase_1_foundation.md:49` "(фіксована логіка)" [fixed logic]; `core/project-intake.md:104` "(Правило розкриття стику)" [the junction-exposure rule] |
| A17 | no phase file says `enter-phase N` first | CHANGED | fixed for −1 only (`phase_-1_intake.md:37`). `virtual-first.md:113-122` opens the round at 0.0 and logs Phase 0 after 0.1, so the round is stamped `"phase": "-1"` (reproduced) → I-7 |
| A18 | no CLI ↔ TCC tool map | CHANGED | both roads given in `phase_-1_intake.md:37,39`. `SKILL.md:98` still lists 11 tools and says "THAT is the call"; `check_captures` is named nowhere; no table |
| A19 | happy-paths A writes prose only | OPEN | `core/happy-paths.md:11` "Write the answers into the project's `autosound_context.md`"; "pick a target curve" in −1 also contradicts `phase_-1_intake.md:15` |
| A20 | entry into Phase 5 said three ways | CHANGED (worse) | centre/rear now also in Phase 2d → I-10 |
| A21 | mixed link styles | OPEN | `virtual-first.md:104`, `capture-session-sheet.md:3` (sibling-relative) |
| A22 | Helix specifics in generic phases | OPEN | → I-13 |
| A-dup | protective filter "in the recording" ×5 | OPEN | home `core/project-intake.md:108`; full copies `phase_0_baseline.md:83`, `phase_1_foundation.md:40` (which still says "One home for the rule"), `phase_2_eq.md:79`, `core/capabilities.md:56` |
| A-dup | knobs outside the DSP ×3 | OPEN | `phase_-1_intake.md:179-188`; `phase_0_baseline.md:85-96`; `virtual-first.md:307-313` |
| A-dup | "the ear does not verify a map row" ×3 | OPEN | `phase_4_listening.md:3`; `phase_0_baseline.md:162-170`, `:210-214` |
| A-cut | the 20-row cut table | 1 of 20 done | only "(This line used to say…)" removed. "Write the PROCESS" is now bullets, and its why moved to `core/why-these-rules.md`. Six rows **grew**: virtual-first 1.5→1.7 sub-points 3,482→3,796 B; `phase_1:46-56` 1,713→2,073; `phase_2:77,79` 2,630→3,236; `phase_4:66-76` 2,917→3,445; `process-phases.md:10-36` 1,630→2,218; `capture-check` text 2,190→1,758 split over two places |

### 2.2 Review B — commands against the CLI

| # | finding (09-09) | status | evidence at `7b3232b` |
|---|---|---|---|
| B1 | the sample `done -1.2 "get_tcc_state…"` is refused | FIXED, but new defect | `core/project-intake.md:43-46`: `doctor \| tee` → `reviewer … --review` → `done -1.2 <file>`. The pipe hides doctor's exit code → I-16 |
| B2 | `registry render` without `--root` | FIXED (docs and code) | `SKILL.md:82,97`, `core/happy-paths.md:25`, `phase_-1_intake.md:165`. Without `--root`, state.py now exits 2 "no ledger at 'state'" |
| B3 | `contract.py check` never says "predates a schema field" | OPEN | `SKILL.md:82`. A legacy `sample_rate_hz` plus an untiered channel gives exit 0 and no hint, while `catch-up --dry-run` would fix both |
| B4 | `rew_tool.py` shorthand | OPEN | = A12; `core/capabilities.md:66,112` |
| B5 | `analyze-joints --from-state` without `--state-root` | OPEN | `core/capabilities.md:66` → "active slot не задано в registry (state); вкажи --preset" [active slot not set in registry (state); give --preset], exit 1 |
| B6 | `find_bundled(vendor, model)` / "answers `None`" | OPEN | `core/project-intake.md:163` (argparse "invalid choice"; real output is "no exact match"). Correct form at `phase_-1_intake.md:163` |
| B7 | `dsp_profile.py <new> …`, project before the verb | OPEN | `core/intake-from-prose.md:60` |
| B8 | repo-level scripts named as if under the skill root | CHANGED | universal contract gone. `core/capabilities.md:193-194`, `core/process-phases.md:22,36`, `tooling/installation.md:12,94`, `tooling/setup-critic-channel.md:180`, `core/naming-and-structure.md:169` remain |
| B9 | `reviewer.model/.reachable` exist only when `configured` | OPEN (doc side) | `core/project-intake.md:16-17`, `phase_-1_intake.md:41` "check `reviewer.reachable`"; `configured` is named nowhere |
| B10 | no MCP twin for `capture-protective/-knobs`, `reviewer`, `target`, `listening-verdict`, `session-close` | OPEN (doc side) | `SKILL.md:98` unchanged; only `call_critic` was added (`SKILL.md:197`) |

### 2.3 Review D — protocol core

| # | finding (09-09) | status | evidence at `7b3232b` |
|---|---|---|---|
| D1 | state source named 8 ways | FIXED, residuals | `SKILL.md:82,97`; `assets/data-contract-template.md:32-37`. Residuals: `SKILL.md:28` ("state lives in `autosound_context.md`"); `assets/data-contract-template.md:4`; **the reviewer's own prompt** `scripts/reviewer-tuning.txt:1` → I-2 |
| D2 | two contracts; the Critic gets the old one | FIXED (one file), new form | a project copy shadows the skill's → I-5 |
| D3 | sub-agent reviewer allowed and forbidden | FIXED | `SKILL.md:58,198`; `core/review-loop.md:21`; `tooling/setup-critic-channel.md:405-411`. Residual: `core/process-control.md:26` "Gemini as Advisor — ONE reviewer call per round" vs `core/review-loop.md:39` "Critic — the round's default" |
| D4 | three ladders | FIXED | one list, `tooling/setup-critic-channel.md:372-414`. `SKILL.md:198` and `core/project-intake.md:89` repeat it in full rather than point to it |
| D5 | "reviewer optional" vs "role not optional" | CHANGED | `SKILL.md:193` "works with a single AI too" vs `:198` "Never silently solo"; the one-sentence fix was not added. Related: I-9 |
| D6 | who writes audit-trail; two homes for critique text | CHANGED | critique text now has one carrier, `process/reviews/` (`SKILL.md:101`). `core/review-loop.md:84` "The canonical decision log" contradicts the same file's `:13-17` and `phase_-1_intake.md:174` ("the journal wins") |
| D7 | lessons go to 5 addresses; `skill-inbox.md` is dead | CHANGED | the inbox now has a reader, `scripts/harvest_inbox.py` (`SKILL.md:122`). Still 5 carriers |
| D8 | "round" has 4 senses | CHANGED | defined in `core/review-loop.md:50-53`, not followed: `:78` "Max **3 rounds**", `SKILL.md:196` "Up to 3 rounds" |
| D9 | role rotation | CHANGED | `assets/data-contract-template.md:26` "No role rotation", but `:155` "(rotate afterward)" remains |
| D10 | path classifier contradicted by its own home | OPEN | = A6 → I-12 |
| D11 | three "how much to redo" classifiers | CHANGED | `goal.mode` with three values exists; Level 0 vs "read the DSP first" still conflict → I-8 |
| D12 | process-control.md holds other files' rules | OPEN | `core/process-control.md:63-97` (stopping, a copy of `SKILL.md:84-90`), `:99-119`. 9,044 B |
| D13 | knowledge-architecture describes the prose era | CHANGED | row 5 fixed; row 3 (`core/knowledge-architecture.md:12`) still prose |
| D14 | dangling references (9) | 4 FIXED, 2 CHANGED, 3 OPEN | open: "Pre-session §4/#4" (`core/preset-strategy.md:16`, `core/project-intake.md:160-161`, `knowledge/dsp/_TEMPLATE.md:13-14`, `knowledge/dsp/musway-m6v4.md:28`); `target-curve-*` memory (`core/naming-and-structure.md:191,198`); `references/core/…` links from inside core (`core/process-control.md:7,46`) |
| D16 | review-loop Wing 1 is maintainer material | OPEN | `core/review-loop.md:9-29`, still read first |
| D17 | estimator-scope §1b/§2a are developer docs | FIXED | moved to `CONTRIBUTING.md:116-225` |
| D18 | feedback-loop carries the author's side | CHANGED | cut to a pointer; donation block `core/feedback-loop.md:37-41` remains |
| D19 | SKILL.md repeats itself | OPEN (worse) | `SKILL.md:58` and `:193` both carry "stateless on-demand call that re-reads state from disk"; the file is 36,379 B → I-3 |
| D-merge | 7 rename/merge proposals (driver, scope, Level, round, ladder, two names) | 2 done, 2 partial, 3 not done | ladder: one list; reviewer: "one channel, three tasks". `mode`, Path and Level 0 unchanged |
| D-size | core 154,966 B → target 85–90 KB | **173,858 B** (+12 %) | `core/naming-and-structure.md` 17,438 → 35,474; `core/feedback-loop.md` 16,455 → 20,025; `core/estimator-scope.md` 19,583 → 13,847 (the only cut) |

### 2.4 Review E — the user's side and the trigger

| # | finding (09-09) | status | evidence at `7b3232b` |
|---|---|---|---|
| E1 | Mac password: three answers | FIXED | `README*.md:48`, `FAQ*.md:94` |
| E2 | install command: README tag vs FAQ `main` | FIXED | `v3.1.1` in README*:52,57 and FAQ*:92,104; held by `scripts/docs-check.py` (install-ref) |
| E3 | second AI "optional" vs "CORE" | CHANGED | `README.md:11` now honest. `FAQ.md:65` and `ADVANCED.md:154` "needs no API key" still omit the Project ID / Enable API steps (`tooling/setup-critic-channel.md:48-54`) |
| E4–E7, E11, E14–E16, E18a/c/e/f | key location, subscription options, omp default, backup "automatically", sign-ins, version pair, "68 capabilities", ROADMAP, `--terminal`, button, checkout, migrate | FIXED | — |
| E8 | "a shared knowledge base" | OPEN | `README.md:107` (×4 languages) |
| E9 | effort `xhigh`: no terminal how-to | OPEN | `FAQ.md:137,145` |
| E10 | "just a series of sweeps" | CHANGED | `README.md:101` honest, but no duration |
| E12 | description cut in the listing | CHANGED (worse) | 1,738 → 1,808 chars; cut at 1,536 → I-4 |
| E13 | disk space | CHANGED | `FAQ.md:74` "TCC adds about 700 MB"; no total |
| E18b | `/plugin` vs `claude plugin` | CHANGED | the model-read `tooling/installation.md:42-44` still uses the `/plugin` form, and → I-1 |
| E18d | "Antigravity access" | FIXED in FAQ | `tooling/setup-critic-channel.md:443` (UK block) keeps it |
| E19 | English calques | CHANGED | `README.md:121` "Good sound!", `:92` "lead you by the hand" |
| E20 | setup-critic-channel mixes user and model voices | OPEN | UK FAQ block `tooling/setup-critic-channel.md:418-449`; and `brew --cask` (`:8`) vs `curl` script (`ADVANCED.md:157`) |
| E-lang | divergence table (13 rows) | 11 FIXED / MOOT, 2 OPEN | open: installer phrase (out of lens); FAQ skeleton matches (29 headings ×4) |

---

## 3. Q1 — the loading map

### 3.1 What is loaded before anything is asked

| what | when | cost |
|---|---|---|
| The skill's listing entry (`name` + `description`, cut at 1,536 chars) | **every turn of every session** on a machine where the skill is installed, about car audio or not | ≈ 1,550 chars ≈ **390 tokens** |
| The two slash commands' descriptions (`commands/setup.md:2`, `commands/install-tcc.md:2`) | every turn | ≈ 260 chars ≈ 65 tokens |
| `hooks/session-start.sh` note | session start, only on a plugin copy not yet set up (`:13-16` exit silently otherwise) | 0, or ≈ 115 tokens |
| Project `CLAUDE.md` written by `project_repo.py init` → `project_seed.write_claude_md` (`rew_tool/project_seed.py:299`) | every turn inside a project folder | ≈ 900 chars ≈ 230 tokens |
| **SKILL.md** body | on trigger: once per session, and once **per phase**, because `SKILL.md:130` makes a phase boundary the place where the chat is cleared | 33,631 chars ≈ **8.4K tokens** (words × 1.3 ≈ 6.2K); whole file with frontmatter 35,524 chars ≈ 8.9K |
| Pre-Session reconcile outputs (`deployment.py`, `contract.py check`, `process.py show`, `state.py … registry render`, `project.py show`) | every start (`SKILL.md:80-82`) | ≈ 4.4K chars ≈ 1.1K tokens on an **empty** project (measured); larger on a real one (not measured) |

**Re-attach after compaction.** Claude Code keeps only **the first 5,000 tokens** of an invoked skill
when a long conversation is summarised: "re-attaches the most recent invocation of each skill after
the summary, keeping the first 5,000 tokens of each" (code.claude.com/docs/en/skills). In SKILL.md
that point falls at **line 130** by chars/4, or **line 176** by words × 1.3. Under either estimate,
`## 🛠️ Review Channel` (`:191`) and `## ✍️ Output Style` (`:203`) are not re-attached. Under
chars/4, `## 🧭 Phase Sliding Window` (`:128`) and most of the Reference Map go too → I-3.

### 3.2 Per phase — what the text tells the model to read

Rule of the house: "Load **ONLY** the active phase's reference file + the next adjacent one"
(`SKILL.md:132`). Then each file orders more. "Ordered" means an explicit order (read / alongside /
follow / entry condition / "do not restate — read them"); routed-only `see …` pointers are not counted.

| phase | files ordered (tokens, chars/4) | ≈ tokens today | same set at 09-09 (bytes) → today (bytes) |
|---|---|---|---|
| **−1** | SKILL 8.9K · `phase_-1_intake` 8.2K · `phase_0_baseline` 6.8K (adjacent) · `core/project-intake` 6.3K (§0/§3/§4; `:91` "this whole file + Phase 0") · `virtual-first` 9.6K (`phase_-1:5`, −1.4) · `capture-session-sheet` 2.2K (−1.4) · `tooling/setup-critic-channel` 9.6K (step 2, `phase_-1:41`) · `core/naming-and-structure` 8.7K (step-5 gate, §3, §1a) · `core/review-loop` 2.5K (`project-intake:87` "read it before the first review round") · `knowledge/dsp/<vendor>` e.g. Helix 5.7K (`SKILL.md:149` "LOOK HERE FIRST") | **≈ 68.5K** | 119,146 → 171,177 (+44 %) |
| **0** | SKILL · `phase_0` · `phase_1` 5.4K · `virtual-first` (`phase_0:5` "Read … alongside") · `capture-session-sheet` (`:7`) · `naming-and-structure` (`:34` "Follow") · `project-intake` §3 1.8K (`:83`) | **≈ 43.2K** | 114,492 → 176,297 (+54 %) |
| **1** | SKILL · `phase_1` · `phase_2` 5.0K · `virtual-first` (`:5`) · `project-intake` §3 (entry gate `:11`) · `tooling/rew-api-quirks` 8.2K (`:44` "Read … 'Timing'") · `core/filter-types-car-audio` 4.1K (`:68` "refer to") | **≈ 42.9K** | 83,985 → 124,704 (+48 %) |
| **2** | SKILL · `phase_2` · `phase_3` 1.7K · `virtual-first` (`:5`) · `core/diagnostic-techniques` 16.6K (`:22`, §13/§3/§9) · `patterns/listening-cheat-sheet` 3.6K (`:93` protocol) · `core/analysis-playbook` 4.3K (`:107`) | **≈ 49.7K** | 68,134 → 102,532 (+50 %) |
| **3** | SKILL · `phase_3` · `phase_4` 2.9K · `virtual-first` (`:5`) · `core/review-loop` (`:21`) · `analysis-playbook` (`:39` "method in") · `patterns/test-tracks` 6.1K (`:48`) | **≈ 35.9K** | 62,915 → 93,731 (+49 %) |
| **4** | SKILL · `phase_4` · `phase_5` 2.0K · `listening-cheat-sheet` + `test-tracks` (`:40` "read them") · `core/feedback-loop` 4.9K (close, `:73`) · `patterns/staging-depth` 2.2K (`:17`) · `analysis-playbook` (`:50`) | **≈ 34.8K** | 81,117 → 95,403 (+18 %) |
| **5** | SKILL · `phase_5` · `patterns/voicing-by-ear` 2.7K (`:23` "refer to") · `core/preference-profile` 0.6K · `core/preset-strategy` 1.2K · `diagnostic-techniques` (`:77`, §20 of a 67 KB file with no index) | **≈ 32.0K** | 33,424 → 44,630 (+34 %) |

Each review round adds `assets/data-contract-template.md` (2.3K, `SKILL.md:61` "Full protocol"); the
first one also adds `tooling/setup-critic-channel.md` (9.6K).

**What moved the numbers since 09-09:**
- SKILL.md +11.1 KB, read in every phase;
- `virtual-first.md` 20,280 → 38,966 B, read in phases 0–3;
- `naming-and-structure.md` 17,438 → 35,474 B, read in −1 and 0;
- `phase_-1_intake.md` 2,993 → 33,588 B: the runbook moved there from `project-intake.md`
  (41,565 → 25,711 B), and −1 still reads both.

---

## 4. Q2 — progressive disclosure

**Does SKILL.md route?** Partly. Of its 35.5K characters:

| section | chars | ≈ tokens | what it is |
|---|---:|---:|---|
| frontmatter + title | 2,123 | 530 | description (I-4) |
| 📍 Resolving paths | 1,570 | 390 | routing — keep |
| 🏛️ Three Roles | 1,359 | 340 | routing + rule |
| 🔄 Pre-Session & Resume | 5,498 | 1,370 | rules, plus a 12-line language anecdote that is also in `core/why-these-rules.md:90-102` (`SKILL.md:67-78`) and a 2.4 KB close procedure (`:84-90`) copied in `core/process-control.md:63-97` |
| ⚠️ Core Guardrails | 9,228 | 2,310 | rules, plus detail that belongs to a phase: the capture-round mechanics (`:103`, ≈1.1 KB, skill #77–#80), the full `process.py` verb list (`:98-105`), the Helix virtual-channel example (`:97`) |
| 🧭 Phase Sliding Window | 2,584 | 650 | routing; `:141` carries stale step numbers (I-6) |
| 📁 Reference Map | 6,465 | 1,620 | 40 rows: routing, but most rows are "read when asked", one routes to a 494 KB HTML (I-26), one tells plugin users the wrong thing (I-1) |
| 🛠️ Review Channel | 2,508 | 630 | rules; repeats `:58` and the ladder in full |
| ✍️ Output Style | 4,190 | 1,050 | rules; Ukrainian-only canonical phrases (I-14) |

Measured by sentence (dates, `skill #`, hub ids, "a session that…", "used to…"), provenance is 13 %
of the body (≈ 4.3K chars). The 09-09 figure of 40 % was measured by paragraph, so the two numbers are
not comparable. Stories moved to `why-these-rules.md` on 09-09 have **come back**: the language
anecdote now sits in four files (I-19).

**Files read in every phase that could be read once:**
- SKILL.md: by design. It is the case for keeping it under the re-attach budget (I-3).
- `virtual-first.md`: 9.6K tokens in each of phases 0–3, about 38K per tune. Each phase needs
  ≈ 0.3–5.0K of it: the −1 / 0 / 1–2 / 3 sections are 1.2 / 4.7 / 20.0 / 2.9 K chars (I-18).
- the adjacent phase file read in full (2–7K per phase) when its Goal-node and gate (the first
  1.8–5.0 K chars) is what the boundary needs (I-18).
- `naming-and-structure.md` (8.7K) for the 2.4 K-char §1a word table that `SKILL.md:216` makes
  mandatory in every report (I-14, I-18).

**Never routed to (dead):**
- `patterns/test-tracks.de.md`, `test-tracks.pl.md`: no inbound reference. `rew_tool/listening.py`
  picks them by language, so they are tool data rather than dead. `SKILL.md:172` names only
  `test-tracks.uk.md`.
- `knowledge/dsp/musway-m6v4.md`: reachable only through the naming pattern at `SKILL.md:149`. That
  is fine.
- `patterns/target-curves/deviation-analysis-audit.md`: one inbound reference, not from a route.

**Routed to but missing:**
- `docs/DESIGN-2026-09-17-phase1-variants.md` (`phase_1_foundation.md:3,59`; `virtual-first.md:180`)
  lives at repo root, outside the skill root that `SKILL.md:32` makes every path relative to.
- `MANUAL.md` (`phase_1_foundation.md:105`) is Resonalyze's, not here.
- `diagnostic-techniques.md §50` (`phase_2_eq.md:77`): the file ends at §35.
- Scripts: `scripts/start_gemini_tuner.sh` (`core/driver-discipline.md:3`), `scripts/gemini_*.sh`
  (`core/review-loop.md:5`), and the prompt file named at `core/review-loop.md:75`. The real files
  are `scripts/autosound_ai.py`, `reviewer-tuning.txt` and `reviewer-task-*.txt`.
- More in I-27.

**Depth.** The official guidance is "Keep references one level deep from SKILL.md"
(platform.claude.com, *Skill authoring best practices*). Here the routes are three deep as a rule:
SKILL → phase → `virtual-first` / `project-intake` / `naming` → `diagnostic §N`. No reference file
has a table of contents, although 31 files exceed 12 KB and the same guidance asks for one in any file
over 100 lines (I-25).

---

## 5. Q3 — duplicates, contradictions, document vs CLI

### 5.1 The same rule, said differently

The duplicates sweep followed about 69 rules through every copy:
- **23 agree everywhere**: protective HPF ≥ 1.1 × Fs at ≥ 24 dB/oct, the ladder's order, Level 1/2/3,
  3/3 → disagreement table, evidence must resolve, ms canonical, `enter-phase` before the first
  question, ≤ 3 variants, L/R crossover symmetry, Schroeder 150–200 Hz, tolerance max(1 dB, 2σ), no
  sub-agent reviewer, and others;
- **46 differ or contradict**.

The ones a model is most likely to act on are below. ✓ marks a quote I re-read myself; the rest are
from the sweep.

| # | rule | copy A | copy B | verdict → finding |
|---|---|---|---|---|
| 1 | desk step numbers | `virtual-first.md:175,205,210,225` (1.3 crossovers, 1.4 coarse EQ, 1.5 joints, 1.6 levels) ✓ | `SKILL.md:141`; `phase_4_listening.md:47`; **`patterns/listening-cheat-sheet.md:47` "desk 1.3 = the joints, 1.4 = levels, 2.1 = the coarse EQ"** (the routing column every ❌ follows); `core/analysis-playbook.md:22`; `virtual-first.md:93,146` ✓ | contradict → I-6 |
| 2 | series spelling / number | `core/naming-and-structure.md:78` "one digit… never zero-padded" ✓; `capture-session-sheet.md:35` "the PROJECT's, never an example's" ✓ | `_01`/`_02` at `capture-session-sheet.md:58,86-89`, `virtual-first.md:129,137,366,370` ✓; `capture-start 1` at `phase_0_baseline.md:71`, `virtual-first.md:114` ✓ | contradict → I-7 |
| 3 | what `--plan` asks for in Phase 2 | `core/naming-and-structure.md:96,99` (Phase 2: `<ch>_2` solos + groups; `--plan` derives from this table) ✓ | `virtual-first.md:350-354` "A capture round… has no place in [Phase 2]: those are Phase 3's" ✓ | contradict → I-7 |
| 4 | centre and rear | Phase 2d: `phase_2_eq.md:3,114-115`, `SKILL.md:137`, `virtual-first.md:218,326-327` ✓ | Phase 5 only after the front satisfies: `phase_5_variations.md:54-56`, `SKILL.md:140`, `phase_3_control.md:67` ✓ | contradict → I-10 |
| 5 | how arrivals are read | `phase_1_foundation.md:48-49` "MUST inspect… manually in the REW GUI"; gate `:27` ✓ | `tooling/rew-api-quirks.md:44-45` "NOT a blanket 'go manual'… don't reflex-punt to the GUI", then `:47` "MANUALLY INSPECT"; `SKILL.md:215` "done by the tools built for it" ✓ | contradict, even inside one section → I-20 |
| 6 | is the path chosen | `phase_0/1/2/3:5`, `core/process-phases.md:55`, `core/project-intake.md:142` ✓ | `virtual-first.md:72` ✓ | contradict → I-12 |
| 7 | EQ boost policy | `SKILL.md:118` "max boost **+6 dB**"; `phase_2_eq.md:28` "Boost ceiling: +6 dB" ✓ | `phase_2_eq.md:49` "Cuts only"; `phase_1_foundation.md:105`, `virtual-first.md:208,328` "zero boosts" ✓ | differ: a ceiling on one path, a ban on the other, unlabelled |
| 8 | where the prose lives | `phase_-1_intake.md:158-174` project root (changelog, audit-trail, skill-inbox); `process.py:590-592` reads the changelog at root ✓ | `phase_3_control.md:65` "in the project's `rew_analitic/`"; `SKILL.md:122` `rew_analitic/skill-inbox.md`; `scripts/harvest_inbox.py:18-19` reads `rew_analitic/` ✓; two profile copies (`phase_-1_intake.md:177`) ✓ | contradict → I-21 |
| 9 | the reviewer's contract | `SKILL.md:61` ✓ | `phase_-1_intake.md:178`, `tooling/setup-critic-channel.md:353` ✓ | contradict → I-5 |
| 10 | the reviewer's truth | `assets/data-contract-template.md:32-37` ✓ | `scripts/reviewer-tuning.txt:1-2`, `scripts/autosound_ai.py:2983` ✓ | contradict → I-2 |
| 11 | which reviewer task per round | `core/review-loop.md:39` "Critic — the round's default" | `core/process-control.md:26` "Gemini as **Advisor** — ONE reviewer call per round" ✓ | differ |
| 12 | Phase 3 needs cross-vendor | `phase_3_control.md:17,19` ✓ | `core/process-control.md:17-35`; `SKILL.md:198` ✓ | contradict → I-9 |
| 13 | current DSP value | `SKILL.md:97` "Re-read the **ledger HEAD** before proposing" ✓ | `core/process-control.md:107` "Read the current value off the DSP screen… a level 'attested in the ledger' is a claim about the past" ✓ | contradict: two sources for one number |
| 14 | where knob/level state is written | `phase_0_baseline.md:85-92` `capture-knobs`, "not the measurement" ✓ | `core/process-control.md:109-113` "The system state belongs in the measurement… master · sub · effects · fill channel" ✓ | contradict |
| 15 | REW Time Offset | `phase_1_foundation.md:43-44,115` "Set a shared Time Offset… BEFORE reading phase" ✓ | `SKILL.md:106` "Never change… any display setting, to read it"; `capture-session-sheet.md:19` "offset 0" ✓ | contradict |
| 16 | owner's sentence and Phase 0 | `SKILL.md:82` ✓ | `phase_0_baseline.md:162-170,210-214`; `rew_tool/contract.py:1687` ✓ | contradict → I-11 |
| 17 | the reviewer's Trace IDs | `assets/data-contract-template.md:40` `m-L_split_320Hz_LR4`, `:156` `<channel>_baseline` ✓ | `core/naming-and-structure.md:72-78` grammar; `phase_0_baseline.md:32` "NOT 'baseline'" ✓ | contradict: the Critic is taught names the evidence resolver refuses |
| 18 | role rotation | `assets/data-contract-template.md:26` "No role rotation" ✓ | same file `:155` "(rotate afterward)" ✓ | contradict |
| 19 | when taste is asked | `phase_-1_intake.md:15` "taste is asked in Phase 0" ✓ | same file `:128-129` "taste in Phase 5" ✓; `core/preference-profile.md:29-31` | contradict |
| 20 | how the language is recorded | `SKILL.md:72`, `phase_-1_intake.md:40` `intake.save(…)`, step closed on `project.json` ✓ | `core/project-intake.md:40` `decision "dialogue language" "uk" -1.1`, closed on `autosound_context.md` ✓; and the step id `-1.2` is both "reviewer" (`project-intake.md:44`) and "new DSP" (`virtual-first.md:98`) ✓ | differ |
| 21 | order at stop | `SKILL.md:86-90`: record → car → nothing new ✓ | `phase_4_listening.md:75`: CONTINUE block → `session-close` → backup → GitHub issue ✓ | differ in order |
| 22 | the generated sheet | `SKILL.md:97`, `phase_3_control.md:65` "generated, not edited" ✓ | `phase_3_control.md:17` gate "changelog/dsp-state/audit-trail updated"; `phase_-1_intake.md:31` ✓ | differ |
| 23 | Phase-3 titles | `core/naming-and-structure.md:97` `<ch>_final (rta)` ✓ | `phase_3_control.md:29-33` `sw_final`… with no method ✓ | differ: evidence will not resolve |

Also differing (sweep), each a one-liner:
- delays vs all-pass at the joints: `phase_2_eq.md:20,74` vs `phase_1_foundation.md:105`, `virtual-first.md:211`;
- review before vs after banking: `core/happy-paths.md:40` vs `virtual-first.md:357-359`;
- glossary home: `core/naming-and-structure.md:3,198` vs `phase_-1_intake.md:171`;
- `target-curve-*` memory vs `process target`: `core/naming-and-structure.md:191,198` vs `phase_0_baseline.md:46`;
- RTA FFT: `capture-session-sheet.md:20-22` vs `core/analysis-playbook.md:51`;
- version labels by hand: `core/process-control.md:117-119` vs `core/naming-and-structure.md:182`;
- legacy ledger path as the source: `core/naming-and-structure.md:84`;
- Gemini ids: `tooling/setup-critic-channel.md:99` vs `:101`;
- key location: `:12-14` vs `:111-127`;
- a pinned model name: `:10`, `:451-453` vs `SKILL.md:199`;
- install by hand-copy: `core/feedback-loop.md:50` vs `tooling/installation.md:7-11`.

Five more pairs give **different numbers** for the same acoustic choice:
- sweep level: `core/project-intake.md:104` (−20 dBFS output) vs `capture-session-sheet.md:52` (−5…−10
  dBFS input peak). Two quantities with nothing saying which is which;
- smoothing for EQ: `patterns/car-eq-patterns.md:272` vs `core/diagnostic-techniques.md:145`;
- sibilance band: `phase_5_variations.md:42` vs `patterns/voicing-by-ear.md:54-59`;
- centre band: `phase_5_variations.md:59` vs `virtual-first.md:219`;
- crossover default family: `core/diagnostic-techniques.md:117` vs `core/filter-types-car-audio.md:103`.

Which number is right is out of scope. That two copies disagree is not.

### 5.2 Documents against the CLI

`doc-commands-check.py` scans 2 documents. The CLI sweep took the other 64 model-read documents:
- **194 distinct command forms** and Python-API families checked: `--help`, the hand-written
  parsers, runs on a throwaway project;
- **167 match, 27 do not** (23 rows below);
- every named Python function exists with the cited signature;
- TCC's 13 tool names could not be checked (§12).

| doc:line | as written | what happens | sev |
|---|---|---|---|
| `phase_3_control.md:7` | `eq_propose --rta` | `unrecognized arguments: --rta`; the real form is `--rew --ver N --part 2` | fails |
| `phase_1_foundation.md:119`; `phase_2_eq.md:30,79` | `python3 rew_tool.py analyze-…` | from the skill root: "can't open file …/rew_tool.py" (`rew_tool/rew_tool.py`) | fails |
| `phase_1_foundation.md:100` | `rew_tool.py analyze-batch --curves-dir <dir> --project <p>` | "the following arguments are required: pattern" | misleads |
| `tooling/helix-eq-export.md:23,31` | `python3 atf_eq.py …` | not at the skill root (`rew_tool/atf_eq.py`) | fails |
| `core/driver-discipline.md:3` | `scripts/start_gemini_tuner.sh` (+ `--refresh`) | file removed (shell wrappers gone, `599be46`) | fails |
| `core/review-loop.md:5` | `scripts/gemini_*.sh` | no such files | misleads |
| `SKILL.md:185`; `tooling/setup-critic-channel.md:103` | `--doctor` | `Невідома задача: --doctor` [unknown task] ✓; the verb is `doctor` | misleads |
| `SKILL.md:100` | `--covers <dotted paths>` | needs ONE comma-joined argument; space-separated keeps the first, drops the rest, exit 0. On `done`, `--covers x` is stored as evidence tokens | misleads |
| `core/naming-and-structure.md:186` | `project.py set-hardware <name> <value>` | `<project-dir>` missing; an unlisted control is refused without `--source user` | misleads |
| `core/intake-from-prose.md:60` | `dsp_profile.py <new> …` | "invalid choice" (verb first) | misleads |
| `core/project-intake.md:163` | `dsp_profile.py` → `find_bundled(vendor, model)`, "answers `None`" | verb is `find-bundled`; prints "no exact match" | cosmetic |
| `phase_-1_intake.md:163` | "bundled reference under `data/dsp_profiles/`" ✓ | no such dir; `knowledge/dsp/profiles/` | misleads |
| `core/naming-and-structure.md:78` | `naming.py name <code> <n> <method>` | `<project-dir>` missing → usage, exit 2 | cosmetic |
| `phase_-1_intake.md:87` | `intake.py set-car \| set-channel \| set <field> <value>` | `<project-dir>` missing | cosmetic |
| `virtual-first.md:103` | `contract.py check --gate` | no project, so `--gate` is taken as the path | cosmetic |
| `tooling/installation.md:57` | `python3 skills/autosound-tuning/scripts/smoke_test.py` | repo-root relative; from the skill root `scripts/smoke_test.py` | misleads |
| `tooling/installation.md:94`; `tooling/setup-critic-channel.md:178,180,182` | `scripts/installer-consistency.py`, `scripts/secret-scan.py`, `scripts/run-selftests.sh` | repo-level; do not resolve under `SKILL.md:32`'s rule | fails |
| `core/process-phases.md:22,36`; `tooling/installation.md:12`; `core/naming-and-structure.md:169`; `tooling/resonalyze-virtual-dsp.md:16,214` | `scripts/docs-check.py`, `encoding-check.py`, `upstream-drift.py` | repo-level, named as checks | cosmetic |
| `core/analysis-playbook.md:27` | `verify.py --session` | needs a title | cosmetic |
| `SKILL.md:86` | bare `skip` | refused without a reason or `--superseded-by`; no doc shows `skip <id> <reason>` | cosmetic |
| `SKILL.md:96` | `apply.py <project> propose <delta.json>` | correct, but the CLI's `--evidence`, `--reviewed`, `attest [v_NNN]` (`apply.py --help` ✓) appear in no document, so a structural move banked this way lands as a 🟠 candidate | misleads |
| `core/capabilities.md:66` | `analyze-joints --from-state` without `--state-root` | "active slot не задано… вкажи --preset" [not set… give --preset] (B5) | misleads |
| `SKILL.md:82` | "if that report says the project predates a schema field" | `contract.py` never says it (B3) | misleads |

**Verbs nobody routes to** (exist in the CLI, absent from every model-read document or present only
in a schema file):
- `process.py`: `amp-changes`, `capture-start --phase/--step/--level-read-as`,
  `capture-knobs --amend`, `capture-protective --source/--amend/--lp`, `capture-import`,
  `capture-supersede`, `handoff --json`;
- `project.py`: `set-path`, `flaw --t-ms`, `language --front-end`;
- `state.py`: `seal`, `verify`, `repair-version`, `variant …`, `config …`, `migrate-line --apply`;
- `apply.py`: `attest`, `--evidence`, `--reviewed` (the CLI form).

The sweep reports that, without `--phase`, `capture-start --plan` refuses in Phase −1 ("plan for phase
'-1' captures nothing"). That compounds I-7. I could not reproduce it without seeding a glossary.

**`process.py` verbs and `--help`**: see I-15. Writing verbs treat it as an argument.

---

## 6. Q4 — the trigger

**Length against the limits.**
- The `description` is **1,808 characters** (2,051 bytes) after YAML folding. At 09-09 it was 1,738.
- The Agent Skills limit is "Maximum 1,024 characters" (platform.claude.com, *Skill authoring best
  practices*).
- Claude Code cuts "the combined `description` and `when_to_use` text … at 1,536 characters in the
  skill listing" (code.claude.com/docs/en/skills).
- Checked empirically: a fresh `claude -p` asked to quote the entry returned exactly 1,536
  characters ending `…"report a b…`. This session's own listing ends the same way.
- `claude plugin validate` does not flag the length.
- `.claude-plugin/plugin.json` `description` (306 chars) is UI metadata and is not shown to the model.

**What the cut removes.** The 09-09 review found that DE/PL tuning phrases were cut. They now
survive: UK at char 1,058 and DE/PL by about 1,300. Cut now: the rest of the tooling block that starts
at char 1,525:
- "file an issue";
- "feedback package";
- "something in TCC is broken";
- «оформи ішью» [file an issue], «баг у TCC» [a bug in TCC], „Fehler melden", „zgłoś błąd" [report a bug];
- the clause "never through a hand-written `gh issue create`".

That clause's real home is `core/feedback-loop.md:58`, and the project `CLAUDE.md` repeats it, so
losing it costs little.

**Does it fire, and only then?** Two probe sets, one run each, `--model sonnet`, using
`evals/run_trigger_eval.py` on scratch eval files:

| probe | result |
|---|---|
| Bug report in TCC, EN / UK / DE / PL (all in the *cut* region) | 4/4 fired: "reporting a bug … on the Autosound TCC app" survives the cut and is enough |
| "file an issue in my react repo…", "report a bug to the python maintainers…" | 2/2 silent |
| Home-audio near-misses reusing the description's unqualified verbs: DIY bookshelf crossovers; REW living room + AVR delays; studio-monitor imaging; "what is a Linkwitz-Riley"; "Helix or Audison, which to buy" | 5/5 silent |

So the description is precise. Its costs are:
- ≈ 390 tokens on every turn of every session, audio or not;
- non-compliance with the 1,024 limit;
- 272 characters of text the model never sees.

The full 34-query set was **not** run here (§12).

**False negatives.**
1. A *pure status question* ("coming back — what's my current DSP state?") does not fire. The evals
   README documents this, 0/4 (`evals/README.md:53-59`).
2. A bare "let's continue" / «продовжимо» [let's continue] typed inside a car's project folder, with no car-audio
   word, cannot fire from the description. The project `CLAUDE.md` that `project_repo.py init`
   writes says "The method is the `autosound-tuning` skill" but does not tell the session to load it
   for every request there (`rew_tool/project_seed.py:299-308`, text in `CLAUDE_MD`).
3. Under TCC the opener drives the session. That was not checkable here (§12).

**What `evals/` covers:**
- 34 queries: 15 should-trigger, 19 should-not (`evals/trigger-eval-set.json`);
- scratch, casual EN, imaging, EMMA, MMM, house curve;
- UK/DE/PL asks and near-misses (home theatre ×3 languages, PC speakers);
- three resume phrasings;
- T-S / box / impedance only as negatives.

Gaps:
- **no case for the bug-report block** (the part being cut);
- no EN home-REW or home-crossover near-miss: the German `#31` is the only one;
- no "resume inside a project folder" case;
- no TCC-opener case.

`evals/README.md:3` still says "20 queries (10 should-trigger incl. the impedance/T-S…)". The
baselines at `:103-105` ("15/22") were measured on a different set. The README's newest dated full
run is 2026-08-26, on v3.0.31 (`:61-83`). → I-24.

---

## 7. Q5 — instructions that fight each other, or ask for a judgment with no input

Each is a finding below. In short:
- **Light touch has no route** (I-8). `goal.mode: light_touch` / Level 0 means "no capture session"
  and "skip the full DSP dump" (`virtual-first.md:56-57`, `core/project-intake.md:148`,
  `phase_-1_intake.md:114`). The same files forbid a shorter phase order (`virtual-first.md:59-61`)
  and say the DSP is read into the ledger first "either way" (`phase_-1_intake.md:5`). The gates
  demand a target and a flaw map. `core/intake-from-prose.md:73-75` adds "`enter-phase` at wherever
  the tune actually is", which the gates refuse.
- **Phase 3 requires two cross-vendor verdicts** (`phase_3_control.md:15,17,19,38-41`), while modes
  B and C are offered as legitimate (`core/process-control.md:17-35`) and the ladder ends in
  same-vendor and human rungs (`SKILL.md:198`) (I-9).
- **Centre and rear: Phase 2d or Phase 5?** (I-10)
- **The owner's sentence**: SKILL.md says it still gates Phase 0; the phase file and the code say it
  does not (I-11).
- **Joint order** inside Phase 2 is stated two ways (I-22).
- **Interview in chat, or hand over the form's URL?** (I-23)
- **A reply "ends with one of two things"** vs the three-line reply that ends with a question (I-29).
- **The reviewer is asked to anchor on prose** that the Generator is told to distrust (I-2).

---

## 8. Q6 — language versions

`README.md`, `README.uk.md`, `README.de.md` and `README.pl.md` are **in step with each other**:
- 121 lines each, and line N is the same paragraph in each;
- every fenced block is byte-identical;
- tags `v3.1.1` match `.claude-plugin/plugin.json`, `marketplace.json` and the latest tag;
- the first chat phrase is identical (README*:92, FAQ*:116).

Every row of the 09-09 divergence table is fixed or moot except the installer phrase (out of lens).

The drift is **against the method and the rest of the docs, in all four at once**, which
`scripts/i18n-check.py` cannot see:

| topic | where (×4 languages) | what |
|---|---|---|
| 2.8.x link | README*:16 → `FAQ*.md#four-paths-of-usage` "path 3" | the anchor now holds only Option 1; the 2.x line moved to `ADVANCED.md:38` (English only) |
| delays | FAQ*:130 "auto-delay tools or cross-correlation… strictly forbidden" | the method prescribes cross-correlation (`tooling/rew-api-quirks.md:56`) and Resonalyze's Auto delay (`virtual-first.md:51,220`) |
| lessons | README*:107 "sends generalized lessons to a shared knowledge base" | there is no such service; a local file the person sends (`core/feedback-loop.md:56-58`) |
| model names | README*:103, FAQ*:115,137,146 (all four) "Claude Fable (5)" | against the rule that no file keeps model names (`core/process-control.md:36-39`, `SKILL.md:199`) |
| plugin route | README*:80-85 say it installs 3.x | the model-read `tooling/installation.md` says the opposite → I-1 |

Cosmetic:
- `FAQ.de.md:84` leaves "or" untranslated;
- `README.de.md:89` uses "Schreibtisch" (the physical desk) for the computer desktop;
- `README.md:121` "Good sound!" and `:92` "lead you by the hand" remain.

**Translated references.**
- `patterns/listening-cheat-sheet.{uk,de,pl}.md` and `test-tracks.{uk,de,pl}.md` exist and
  `SKILL.md:172` marks them "may lag". `SKILL.md:172` names only `test-tracks.uk.md`.
- `phase_-1_intake.md:83` says intake labels exist only in Ukrainian ("Ukrainian is the one that
  exists today"). `rew_tool/intake_i18n/` has `en/de/pl/uk.json`, 23–31 KB each.
- The **report vocabulary** has only a Ukrainian column (I-14).

---

## 9. Findings

Severity: **High** = the model does the wrong thing to the user's system or advice in a normal
session; **Medium** = wrong step, wasted turn, or a judgment with no input; **Low** = cost or
confusion only. Size: **S** ≤ half a day, **M** ≤ 2 days, **L** more.

### I-1 · High · The model is told the plugin route is the 2.x line, and to uninstall it

**Evidence.**
- `tooling/installation.md:7-9`: "One supported way to install 3.x: the installer… The plugin
  catalogue is pinned at 2.8.3 and moves only with 3.1.0".
- `:11` "the only supported path for 3.x".
- `:42-45`: "that catalogue entry is pinned at **2.8.3**, not 3.x. Offer to switch to the installer
  (§1) and remove the plugin (`/plugin uninstall autosound-tuning`)".
- `SKILL.md:152` repeats "3.x: the installer only — the plugin catalogue is pinned at 2.8.3".
- Against these: `.claude-plugin/marketplace.json` pins `ref v3.1.1` / sha `e8dabf7`;
  `CHANGELOG.md:183` "the plugin catalogue moves from 2.8.3 to 3.x"; `README*.md:80-85`;
  `commands/setup.md`; `hooks/session-start.sh:17-21` offers `/autosound-tuning:setup`, which
  `installation.md` never mentions.

**Cost.** Every plugin user whose session reaches install, update or troubleshooting:
- `SKILL.md:123` routes "tool seems missing" there;
- `SKILL.md:152` routes "which copy is running" there.

That user is advised to uninstall a correct v3.1.1 and is never pointed to `/autosound-tuning:setup`.
`tooling/installation.md` was last touched in `a34c838` (2026-10-02), the day before v3.1.0 moved the
catalogue.

**Proposal.**
- Rewrite `installation.md` §1–§3 for the two supported routes: the installer, and the plugin plus
  `/autosound-tuning:setup [app]`.
- Fix `SKILL.md:152`.
- Add a `docs-check.py` rule: no model-read file may say "pinned at 2.8.3" while `marketplace.json`'s
  ref is `v3.*`.

**Size** S.

**Verify.**
- `grep -rn "2.8.3" skills/autosound-tuning` returns nothing.
- The new docs-check rule fails on today's tree and passes after the change.

### I-2 · High · The reviewer is told the prose is "the single source of truth"

**Evidence.**
- `scripts/reviewer-tuning.txt:1` "the AUTOSOUND CONTEXT is the single source of truth" and `:2`
  "Rely ONLY on the CONTEXT".
- `scripts/autosound_ai.py:2983` heads the injected file "AUTOSOUND CONTEXT (the single source of
  truth)".
- The same prompt then carries `assets/data-contract-template.md:32-37`: "The machine files are the
  truth; the prose is a view of it… `autosound_context.md`… is not a second source".
- `SKILL.md:82` tells the Generator the machine files win.
- `assets/data-contract-template.md:4` still says the contract is loaded "together with
  `autosound_context.md`".

**Cost.** The Critic's drift-watch (`assets/data-contract-template.md:23`) checks the proposal
"against the on-disk state", but the only state it is given and told to trust is prose that lags the
ledger. A correct proposal built on the ledger HEAD reads as drift. A stale prose number passes. One
prompt states both truth models.

**Proposal.**
- Rename the section to "PROJECT CONTEXT (prose view — the machine files win)".
- Change `reviewer-tuning.txt:1-2` to match.
- Make the package carry the ledger HEAD every time, as the contract already asks: `:39` "The current
  state rides in EVERY package".

**Size** S.

**Verify.**
- Assemble the prompt (`compile_prompt`) and grep for "single source of truth": one hit, the
  contract's.
- Add an assert beside the existing ones (`scripts/autosound_ai.py:1466-1483`).

### I-3 · High · SKILL.md outgrew the re-attach budget

**Evidence.**
- `SKILL.md` is 36,379 B, 223 lines: ≈ 8.9K tokens by chars/4, 6.6K by words × 1.3. It was 25,258 B
  at 09-09, and 32 commits since have touched it.
- Claude Code re-attaches "the first 5,000 tokens" of an invoked skill after a summary
  (code.claude.com/docs/en/skills).
- That point falls at `SKILL.md:130` (chars/4) or `:176` (words × 1.3).
- After a compaction the model keeps neither `## 🛠️ Review Channel` (`:191`: cadence, ladder, "never
  a background sub-agent") nor `## ✍️ Output Style` (`:203`: the three-line reply, "every number
  names where it came from").
- Under chars/4 it also loses `## 🧭 Phase Sliding Window` (`:128`: which file to load).
- Nothing tells the model to re-read SKILL.md or the phase file after a summary.

**Cost.** Long single-phase sessions — the capture day and the desk sitting — are where compaction
happens. The session then continues with half the always-on rules and none of the routing.

**Proposal.**
1. Order by need: paths → roles → Pre-Session → Phase Sliding Window → Review Channel → Output
   Style → Guardrails → Reference Map.
2. Add one line near the top: "After a context summary, re-read this file and the active phase file
   before acting."
3. Cut to ≤ 16 KB (≈ 4K tokens):
   - move the Reference Map's 40 rows to `references/INDEX.md`, keeping ≈ 8 route rows plus
     `capabilities.py find`;
   - move the language anecdote (`:74-78`), the close procedure (`:86`, home: `session-close`'s own
     output) and the capture mechanics (`:103`, home: `capture-session-sheet.md` Block 0) to their
     homes;
   - say the stateless-reviewer sentence once (`:58` = `:193`).
4. Add a docs-check rule: SKILL.md ≤ N bytes.

**Size** M.

**Verify.**
- Count SKILL.md's body with the API's token-counting endpoint, and check that `## ✍️ Output Style`
  starts before token 5,000.
- Eval: a long scripted session with a forced `/compact`, then a reviewer round. Does the reply keep
  three lines, and does the round use the door?

### I-4 · Medium · The description is 1,808 characters; the model sees 1,536

**Evidence.**
- `SKILL.md:3-23`.
- The limits and the empirical cut are in §6.
- The cut text is the tooling block (`:19-23`).

**Cost.**
- ≈ 390 tokens on every turn of every session wherever the skill is installed, with or without car
  audio. The cut 272 characters cost nothing because they are never shown.
- Non-compliance with the 1,024 spec.
- The probes show no recall loss today, so this is cost and compliance, not behaviour.

**Proposal.** ≤ 1,024 characters:
- drop the Nono licence parenthesis (`:10-11`, ≈ 130 chars; it belongs in the body or in
  `patterns/target-curves/README.md`);
- drop the example parentheses and the gate clause (`:23`, home: `core/feedback-loop.md:58`);
- keep the "car" qualifier on the verbs, one resume phrase, one phrase each for UK/DE/PL, and one
  tooling clause.

**Size** S.

**Verify.**
- `python3 evals/run_trigger_eval.py --eval-set evals/trigger-eval-set.json --skill-name
  autosound-tuning --model <m>`, plus the 11 probe queries in §6, before and after, on a machine
  without other car-audio skills (§12).
- A docs-check rule: the folded description is ≤ 1,024 characters.

### I-5 · Medium · A stale project copy of the contract outranks the skill's

**Evidence.**
- `scripts/autosound_ai.py:221-243` searches for `find_file` in this order: `rew_analitic/` → CWD →
  `$AUTOSOUND_DIR` → the skill's `assets/`.
- The skill tells the session to make that copy:
  - `phase_-1_intake.md:178` "`cp <skill>/assets/data-contract-template.md rew_analitic/`, then fill
    in the `<DSP>` placeholders";
  - `assets/data-contract-template.md:11` "When a project is created it's copied";
  - `tooling/setup-critic-channel.md:353` marks the copy preferred.
- `SKILL.md:61` promises "the same file the wrapper scripts inject into the reviewer, so what you read
  is what it was told".

**Cost.** The promise holds only until the first skill update after a project's intake. From then on
every contract change misses that project's Critic, while the Generator reads the new one. The
batch-package rule and `Origin` are examples of such changes.

**Proposal.**
- Stop copying.
- Keep the project-specific `<DSP>` facts in `autosound_context.md`, or in a small
  `rew_analitic/contract-local.md` appended *after* the skill's contract.
- Until then, `doctor` and `contract.py check` should name a project copy that differs from the
  skill's.

**Size** S/M.

**Verify.** Make a project with an edited copy and run `python3 scripts/autosound_ai.py doctor`. It
prints which contract it found (`:2545-2546`). After the change it must be the skill's file.

### I-6 · Medium · Step pointers aim at the wrong steps after virtual-first was renumbered

**Evidence.** `virtual-first.md` now numbers 1.3 crossovers, 1.4 coarse EQ, 1.5 joints, 1.6 levels
and 1.7 sums (`:175,205,210,225,272`). These pointers still use the old numbers:
- `SKILL.md:141`: "`predict --align` (1.3) · `eq_propose` (2.1 / 3.3)";
- `phase_4_listening.md:47`: "the joints (1.3), the levels (1.4), the coarse EQ (2.1)";
- `virtual-first.md:93`: "set in 1.3, checked on the prediction in 1.5";
- `virtual-first.md:146`: "Phase 1 reads them (1.3)";
- **`patterns/listening-cheat-sheet.md:47`**, the routing column every listening ❌ follows: "desk 1.3
  = the joints, 1.4 = levels, 2.1 = the coarse EQ, 3.3 = the fine EQ over MMM";
- `core/analysis-playbook.md:22`: "Junction delay / polarity at the DESK (virtual-first 1.3)".

Also, two different steps are both numbered **1.7** (`virtual-first.md:252` and `:272`).

**Cost.** A listening ❌ routed by `phase_4:47` to "the joints (1.3)" re-opens the crossover choice
instead of the joint delay. `add-step` ids taken from these numbers point at the wrong work.

**Proposal.**
- Renumber: 1.7a/1.7b, or 1.7/1.8.
- Write pointers as "1.5 joints", number plus name.
- Add a docs-check rule: every "(N.M)" that names virtual-first resolves to a step whose title
  contains the cited word.

**Size** S.

**Verify.** `grep -n "(1\.[0-9])" SKILL.md references -r` and check each by hand. The new rule fails
today.

### I-7 · Medium · A capture round is opened three ways, two with a hard-coded series, before its phase

**Evidence.**
- `SKILL.md:103`: `capture-start <N> --plan [titles...] [--optional <title>]`. "What it prints is
  the message to the Arbiter."
- Other recipes:
  - `phase_0_baseline.md:70-71`: `naming.py <project> expect 0 1` + `capture-start 1 "sw_1 (sw)"…`;
  - `virtual-first.md:113-114`: `capture-start 1 "<title>"…`;
  - `phase_-1_intake.md:165` "`capture-start 1 …`";
  - `capture-session-sheet.md:45-47`: `next-series`, then explicit titles.
- `capture-session-sheet.md:35-37`: "The series number is the PROJECT's, never an example's… a sheet
  that said `_2`… on a project at `_49`, brought 47 measurements back under the wrong number".
- Series format: `_1` (`phase_0_baseline.md:32,101`) vs `_01` (`virtual-first.md:129-139`,
  `capture-session-sheet.md:58-89`).
- `virtual-first.md:113-122` opens the round at 0.0 and logs Phase 0 after 0.1. Reproduced: the
  round is stamped `"phase": "-1"`.
- What `--plan` asks for is derived from `core/naming-and-structure.md:96,99`, which gives Phase 2
  the `_2` solos and group captures. The desk path says "A capture round… has no place in [Phase
  2]: those are Phase 3's" (`virtual-first.md:350-354`).

**Cost.**
- On an improve-existing project, or a second capture day, following phase 0 or virtual-first
  literally re-runs series 1. That is exactly the failure the sheet records.
- `--plan` (the newer, printed message) is reached only through SKILL.md.

**Proposal.**
- One recipe in one home (the sheet's Block 0): `enter-phase 0` → `naming.py next-series` →
  `capture-start <N> --plan`. Every other file gets a one-line pointer.
- One series format.

**Size** S.

**Verify.**
- On a scratch project already at series 49, follow `phase_0_baseline.md` §3 literally and read
  `process show`: series and phase stamp.
- A docs-check rule: no `capture-start 1` literal in `references/phases/`.

### I-8 · Medium · Light touch (Level 0) has no route the gates allow

**Evidence.**
- `core/project-intake.md:145-151` offers "light touch (Level 0)… skip reading/reversing the full
  DSP state".
- `virtual-first.md:56-57` "the third door… with no capture session". `:59-61` then forbids a shorter
  phase order, because "`enter-phase 3`… still meets the gates asking for a target curve and a flaw
  map".
- `phase_-1_intake.md:5` "Either way, whatever the DSP holds is read into the ledger first" vs
  `:114` "skip the full DSP dump".
- `core/intake-from-prose.md:73-75` "Then `enter-phase` at wherever the tune actually is". It never
  records `target`, so the gates refuse it (reproduced: −1→3 "phase 3 needs a target curve").

**Cost.**
- "I just want it a bit better" is a common ask, and the model has to improvise the route. That is
  what `virtual-first.md:59-61` warns against: hand-typed placeholders to pass a gate.
- The three-value `goal.mode` was meant to settle this.

**Proposal.** Write the light-touch route as five lines in `virtual-first.md` "Two ways in":
- which phase it enters;
- what stands in for the flaw map: a `hypothesis` row from the one measurement, or a recorded
  `decision` that waives it;
- the one capture it needs.

Or give the gate a recorded `decision mode=light_touch` exemption. Point `project-intake §4` and
`phase_-1:114` there.

**Size** S (text) / M (with a gate change).

**Verify.** Seed a project with `goal.mode light_touch`, follow the route literally, and check that
every `enter-phase` passes without a placeholder.

### I-9 · Medium · Phase 3 demands cross-vendor verdicts that modes B/C cannot produce

**Evidence.**
- `phase_3_control.md:15` "independent Claude + Gemini analyses".
- `:17` "**two independent (cross-vendor) verdicts**".
- `:19` "a single-perspective verdict (must be cross-vendor)".
- `:38-41` names Claude and Gemini.
- Against these: `core/process-control.md:17-35` (B "Claude solo", C "Gemini solo", "a legitimate
  choice"), and `SKILL.md:198`, a ladder whose lower rungs are same-vendor or the human.

**Cost.** In mode B or C the model reaches the lock with no instruction: it can block the lock, fake
a second vendor, or ignore the gate. Each is wrong for someone.

**Proposal.** One sentence in `phase_3:17`: "two independent verdicts — cross-vendor in mode A; in
B/C the ladder's best reachable rung, named in the lock's record". Drop the vendor names (`:15,38-41`)
in favour of Generator / reviewer.

**Size** S.

**Verify.** Read the text. An eval scripted in mode B, reaching Phase 3: does the lock record the
rung used?

### I-10 · Medium · Centre and rear are tuned in Phase 2d, and "only after the front satisfies" in Phase 5

**Evidence.**
- Phase 2d: `phase_2_eq.md:3,114-115` "**2d** the final tone to target, then the centre under
  everything, then the rear"; `SKILL.md:137`; `virtual-first.md:326-327`.
- Phase 5: `phase_5_variations.md:54-56` "⛔ Only once the FRONT satisfies (locked + user OK)";
  `SKILL.md:140`; `core/process-phases.md:53`; `phase_3_control.md:67`.

**Cost.**
- The model either tunes the centre before the lock, against the Phase 5 gate, or skips it in 2d,
  against Phase 2's "MUST" order (`phase_2:3`).
- The plan the panel shows differs by which file was read last.

**Proposal.** Decide once:
- either "centre/rear as part of the technical base (2d)";
- or "as variations (5)".

Make the other file a pointer. If both are meant, say which part belongs where: level and arrival in
2d, voicing and envelopment in 5.

**Size** S.

**Verify.** Grep for "centre" and "rear" across phases: one home, pointers elsewhere.

### I-11 · Medium · SKILL.md still says the owner's sentence gates Phase 0

**Evidence.**
- `SKILL.md:82`: `catch-up`… "does NOT close the phase-0 gate — the owner's own sentence is still
  owed".
- Against it:
  - `phase_0_baseline.md:162-170` "The symptom is a communication line, not evidence, and it is
    optional (the Arbiter's ruling, 2026-09-08)";
  - `:210-214` "Until 2026-09-08 this gate demanded the owner's *sentence*… The Arbiter's ruling
    moved it";
  - `rew_tool/contract.py:1687` `assert … "a symptom must not gate phase 0"`.
- `project.py catch-up --help` carries the same stale sentence.

**Cost.** The always-loaded file asks the model to collect owner sentences about things nobody has
heard yet. That is the invented-perception failure that the 09-08 ruling removed.

**Proposal.** Delete the clause, or say "it fills a `DRAFT:` symptom; nothing about the owner's line
gates Phase 0". Fix the same words in `project.py`'s help.

**Size** S.

**Verify.** `grep -rn "sentence is still owed"` returns nothing. A docs-check phrase rule.

### I-12 · Medium · "Path" is still a choice, against decision §9 item 3

**Evidence.**
- `core/project-intake.md:142-143` "### Path: virtual-first or iterative (an INTENT on top of the
  Level)".
- `core/process-phases.md:55` "Phase −1 picks it (or the iterative fallback)".
- The four banners `phase_0/1/2/3_*.md:5`: "**If** Phase −1 chose the virtual-first path… This file
  stays the authority on the iterative fallback".
- `phase_2_eq.md:32,98` "on the iterative path only".
- Against these: `virtual-first.md:72` "There is no separate 'iterative path' to choose", and the
  09-09 decision "one path: virtual-first with degradation"
  (`docs/REVIEW-2026-09-09-release-readiness.md` §9).

**Cost.**
- Every phase carries two runbooks, and the model does not know which to follow or whether it must
  read the 9.6K-token `virtual-first.md`.
- The step numbers differ between the two (I-6).

**Proposal.** Carry out §9 item 3:
- each phase file becomes the one path;
- the iterative content becomes the "Degradation" appendix of `virtual-first.md:401-417`, read only
  when the loss table says so;
- banners and the intake "Path" section go.

**Size** L (it is the biggest token saving too: I-18).

**Verify.**
- `grep -rn "iterative path\|chose the virtual-first" references` returns only the degradation
  appendix.
- Re-run the per-phase token table.

### I-13 · Medium · Generic phases assume a Helix: PC-Tool, `.pct6`, a virtual layer

**Evidence.**
- PC-Tool and `.pct6` in generic phases: `phase_0_baseline.md:58-61`; `phase_1_foundation.md:27,
  82-85` (`<prefix>_v1_foundation.pct6` in a *gate*); `core/project-intake.md:105`.
- The virtual layer assumed: `phase_2_eq.md:18,119` ("final target EQ on the **virtual layer**
  only"); `phase_5_variations.md:13,47-49` ("exclusively on the Virtual Layer").
- The fallback for a DSP without a virtual tier exists only in `core/project-intake.md:155` ("None →
  voicing = linked L=R on the output EQ").

**Cost.** On a Musway or any DSP without a virtual tier, the gates of Phases 1, 2 and 5 ask for things
the hardware cannot do, and the fallback is two files away.

**Proposal.** Write the phases in terms of the DSP profile ("the profile's voicing tier, else linked
L=R output EQ"). Name Helix specifics once each, as "(Helix: … → `knowledge/dsp/helix-dsp-ultra-s.md`)".

**Size** M.

**Verify.** Grep phases for `PC-Tool|pct6|Virtual Layer`: each hit sits behind a profile condition.

### I-14 · Medium · The report vocabulary exists only in Ukrainian

**Evidence.**
- `core/naming-and-structure.md:34` has a single column, "in the report (uk)".
- `SKILL.md:216` makes it mandatory: "speak those words, not synonyms for them".
- Canonical phrases appear only in Ukrainian at `SKILL.md:207` «перевірки: зроблено» [checks: done],
  `:220` «деталі?» [details?], `:221` «введи це» [enter this] / «виміряй ці N кривих» [measure these N
  curves]; `phase_-1_intake.md:141,165`;
  `phase_0_baseline.md:110`; `phase_1_foundation.md:15`.
- Against these: four officially checked languages (`core/project-intake.md:82-83`) and intake labels
  in four (`rew_tool/intake_i18n/`). `phase_-1_intake.md:83` claims only Ukrainian exists.

**Cost.** EN, DE and PL sessions translate on the fly. §1a exists to stop exactly that: «сію» ["I sow", for *seed*] cost a
stop mid-wave (S-040, `:29-31`).

**Proposal.** Put the word table, with the step-reply phrases, in the i18n data:
`rew_tool/intake_i18n/<lang>.json` → `report_words`, or a small `references/core/report-words.md`
with four columns. Have `contract.py check` print the recorded language's row under its "Reply
language" line. Fix `phase_-1:83`.

**Size** S/M.

**Verify.** A docs-check or `i18n` rule: every row has four non-empty cells. Then a DE session's first
reply uses the table's word.

### I-15 · Medium · `process.py` verbs treat `--help` as an argument, and some of them write

**Evidence.** Reproduced in scratch directories:

| command | result |
|---|---|
| `process.py <dir>/process capture-start --help` | prints "cap_001 open at --help", writes `docs/plans/_--help-capture.md` |
| `… session-close --help` | **records** a close (`journal.jsonl` created) |
| `… decision --help` and `… target --help` | "error: list index out of range" |

Only `process.py --help` with no verb prints usage. `SKILL.md:86` warns that `session-close` "is never
run to look". `doc-commands-check.py --run` skips writing verbs, so nothing catches this.

**Cost.** The natural way to learn a verb's syntax opens a bogus round, or closes the session in the
project's own journal.

**Proposal.**
- Code: any verb whose first argument is `-h` or `--help` prints that verb's line from the usage and
  exits 0.
- Docs: SKILL.md says "`process.py --help` lists every verb".

**Size** S.

**Verify.** The four commands above in a scratch directory leave no files. Add a selftest case.

### I-16 · Medium · The reviewer step closes on a failed doctor, and the doctor contradicts the method

**Evidence.**
- `core/project-intake.md:43-46`: `python3 scripts/autosound_ai.py doctor | tee
  <project>/rew_analitic/reviewer-check.md`, then `done -1.2 "rew_analitic/reviewer-check.md"`.
- The pipe returns `tee`'s status. Run here, `doctor` exits **1** with "ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗" [NEEDS FIXING] and
  the step still closes: the file exists, so the evidence resolves.
- That contradicts `:57-59` ("A reviewer the state reports as unreachable is not done: block that
  step").
- The same output says "Фаза 1.3 (пошук кросоверів) без нього не піде" [Phase 1.3 (the crossover search) will not run
  without it] about the desk engine, against
  `virtual-first.md:189-194` ("The engine is not required… Phase 1 then runs the per-driver way").
- It is in Ukrainian whatever the interface language.

**Cost.**
- A broken reviewer channel is recorded as checked, and is discovered in Phase 1 with a round
  waiting.
- The model relays a false "Phase 1 cannot run".

**Proposal.**
- Use `doctor > file; rc=$?`, then `done` on 0 and `block -1.2 "<first ✗ line>"` otherwise. Better, a
  `doctor --out FILE` that keeps the code.
- Fix the engine line.
- Print doctor's text in the recorded language.

**Size** S.

**Verify.** On a machine without a reviewer, following `project-intake.md:43-46` literally leaves
`-1.2` blocked, not done.

### I-17 · Medium · Commands in files no checker scans

**Evidence.**
- `scripts/doc-commands-check.py:39-40` scans only `core/capabilities.md` and `tooling/rew-tool-docs.md`.
- In the other 64 model-read documents, 27 of 194 command forms do not run as written (§5.2). Six
  fail outright: `eq_propose --rta`, `python3 rew_tool.py` ×3, `python3 atf_eq.py`,
  `start_gemini_tuner.sh`.
- Three are in the always-loaded SKILL.md: `--doctor` at `:185`, `--covers` at `:100`, "predates a
  schema field" at `:82`.
- The checker itself would pass two of the failures even if it scanned these files. It resolves a
  module by basename (`rew_tool.py` and `atf_eq.py` "exist"). It splits a placeholder that contains a
  space. It ignores a bare usage print with exit 2.

**Cost.** Each mismatch is a failed call and a turn spent re-reading `--help`. The `--covers` one
silently drops facts. The `apply.py` one leaves a banked change without its evidence.

**Proposal.**
- Point `DOCS` at `SKILL.md`, `references/**/*.md`, `knowledge/**/*.md` and `assets/*.md`.
- Resolve a module by the path as written, relative to the skill root.
- Treat placeholders as whole tokens.
- Count a usage print with exit 2 as a refusal.
- Fix the 23 rows.

**Size** S/M.

**Verify.** The extended `doc-commands-check.py --run` lists today's failures. After the fixes:
`0 refused`.

### I-18 · Medium · Per-phase reading grew 18–54 % in four weeks; most of it is avoidable

**Evidence.**
- The §3.2 table.
- The drivers: SKILL.md in every phase; `virtual-first.md` 9.6K "alongside" in phases 0–3
  (`phase_0/1/2/3:5`); the adjacent phase read in full (`SKILL.md:132`); `naming-and-structure.md`
  8.7K for a 2.4K word table; `diagnostic-techniques.md` 16.6K for one § (`phase_2:22`,
  `phase_5:77`).

**Cost.**
- About 43–69K tokens to start Phases −1 and 0, before any measurement is read.
- Each phase is its own session after a `/clear` (`SKILL.md:130`), so the whole bill recurs per phase.
- Dilution: the rule that matters sits among 40–70K tokens of other rules.

**Proposal.** In order of saving per hour of work:
1. I-3 (SKILL.md ≤ 16 KB).
2. Split `virtual-first.md` by phase: the 1–2 desk section, 20 KB, into `phase_1`/`phase_2`; keep a
   ≈ 7 KB overview with the loss table and degradation.
3. "Next adjacent phase" means its Goal-node and gate only, the first 1.8–5.0 K chars.
4. Move the §1a word table out of `naming-and-structure.md` (I-14).
5. Add a section index at the top of `diagnostic-techniques.md` so a § is grepped, not read whole.

Estimated tokens with all five:

| phase | today | after |
|---|---:|---:|
| −1 | 68.5K | ≈ 46K |
| 0 | 43.2K | ≈ 23K |
| 1 | 42.9K | ≈ 31K |
| 2 | 49.7K | ≈ 27K |
| 3 | 35.9K | ≈ 22K |
| 4 | 34.8K | ≈ 28K |
| 5 | 32.0K | ≈ 11K |

**Size** M/L (item 2 rides with I-12).

**Verify.** Re-run the per-phase measurement script (§3.2 method) and keep it as a check that prints
the table, so it does not age silently.

### I-19 · Medium · Doctrine duplicated again, and the copies drift

**Evidence.** §5.1: 46 rules stated differently in two or more places. The always-on ones repeat in
full:
- **The language rule and its anecdote**, four times: `SKILL.md:67-78`, `core/project-intake.md:61-83`,
  `phase_-1_intake.md:40`, `core/why-these-rules.md:90-102`. `why-these-rules.md:8-9` says the
  stories were moved *out* of SKILL.md on 09-09.
- **The stop procedure**, three times, in two orders: `SKILL.md:84-90`, `core/process-control.md:63-97`,
  `phase_4_listening.md:75`.
- **The protective filter "in the recording"**: five copies (§2.1 A-dup).
- **Knobs outside the DSP**: three.
- **"Stateless reviewer / drift-watch"**: twice inside SKILL.md (`:58`, `:193`), plus
  `assets/data-contract-template.md:23` and `core/driver-discipline.md:16`.
- **The cadence**: `SKILL.md:196` copies `core/review-loop.md:48-72`.

**Cost.**
- Tokens: SKILL.md's copies alone are ≈ 1.5K tokens.
- **Drift**: this audit's rows 1, 2, 4, 5, 7 and 13 are copies that were updated in one place.

**Proposal.**
- One home per rule. Every other copy becomes a one-line pointer.
- Add docs-check phrase rules for the rules that drifted most: boost policy, centre/rear phase, arrival
  method, series spelling, where the prose lives. The mechanism already exists for eight others
  (§1).

**Size** M.

**Verify.** The new docs-check rules fail on today's tree and pass after.

### I-20 · Medium · How to read an arrival: by hand in the GUI, or by the tool

**Evidence.**
- `phase_1_foundation.md:48-49`: "MUST inspect the impulse response graphs manually in the REW GUI,
  rather than trusting REW's automated numbers". The Phase 1 gate (`:27`) asks for "manually-inspected
  IR onsets".
- `tooling/rew-api-quirks.md:44-45` heads the section "NOT a blanket 'go manual'… don't reflex-punt to
  the GUI". Two lines later (`:47`) the same section says "⚠️ MANUALLY INSPECT IMPULSE GRAPHS".
- `SKILL.md:215`: "Reading the arrivals is Phase 1's work, done by the tools built for it
  (`predict --align`, `arrival_triangulate`)".
- On the L/R pair: `phase_1_foundation.md:53` "IR FIRST FRONT (leading edge)" vs
  `tooling/rew-api-quirks.md:56` "CROSS-CORRELATE the two IRs; don't threshold/onset-pick".
- Users read the opposite in `FAQ*.md:130`: cross-correlation "strictly forbidden".

**Cost.** The model sends the person to the GUI to eyeball onsets, or produces prose arrival numbers.
That is the hedged number `SKILL.md:215` forbids. It is also the most error-prone step for a
non-engineer.

**Proposal.**
- One sentence in `phase_1` and the quirks file: "the tools read arrivals (`predict --align` /
  `arrival_triangulate` / `analyze-joints`); the GUI is the cross-check when a tool says ILL-POSED or
  UNVERIFIED".
- Restate the gate in those terms.
- Fix FAQ*:130.

**Size** S.

**Verify.** Read. Then an eval prompt: "what delay for w-L?" in Phase 1 → the reply calls the tool
and does not open the GUI.

### I-21 · Medium · The prose files have two homes, and each tool reads a different one

**Evidence.**
- `phase_-1_intake.md:158-174` writes `tuning-changelog`, `audit-trail.md` and `skill-inbox.md` "in
  the new project's root".
- `rew_tool/state/process.py:590-592` (`_changelog_text`) reads the changelog at the root.
- `scripts/harvest_inbox.py:18-19` reads `rew_analitic/skill-inbox.md` and
  `rew_analitic/tuning-changelog*`.
- `SKILL.md:122` says `rew_analitic/skill-inbox.md`.
- `phase_3_control.md:65` puts changelog and audit-trail "in the project's `rew_analitic/`".
- `phase_-1_intake.md:177` keeps a **second copy** of `autosound_context.md` in `rew_analitic/`, the
  one the reviewer reads.

**Cost.** Whichever folder the model picks, one reader misses it:
- a changelog under `rew_analitic/` is invisible to `handoff`: with no file at the root, its
  CONTINUE-block check and the HEAD-drift warning (S-084) are **skipped silently**
  (`rew_tool/state/process.py:2461-2466`). That is the "missing input passes" shape `CLAUDE.md`
  forbids;
- a root inbox is never harvested;
- the profile is edited in one place while the Critic reads the other.

**Proposal.**
- One folder for each file, written once in `phase_-1 §5`.
- Make both readers look in that folder, with a fallback that warns.
- Drop the second profile copy: the reviewer door can read the root file.

**Size** S/M.

**Verify.** Seed a project per `phase_-1 §5`. Then `process.py … handoff` and `harvest_inbox.py
<project> --check` both find their files.

### I-22 · Low · Phase 2 states the joint-alignment order two ways

**Evidence.**
- `phase_2_eq.md:3` and `:65`: "the junctions of each side first, left and right apart, then the sub
  with the mids… on the iterative path this is where they are set".
- `:71`: "Midbass (Reference) → Subwoofer → Midrange → Tweeter", sub second.
- `virtual-first.md:210` 1.5 is bottom-up from the sub.

**Cost.** The iterative runbook gives two orders for one job.

**Proposal.** One order, in one place. The other line points to it.

**Size** S.

**Verify.** Read.

### I-23 · Low · Interview in chat, or hand over the form's URL?

**Evidence.**
- `phase_-1_intake.md:79-81`: "A terminal session hands a person that URL instead of asking the
  questions in chat".
- Against it:
  - `core/project-intake.md:29-30` "With no front-end, ask them exactly as written";
  - `phase_-1_intake.md:42` (step 3 "Interview");
  - `:108` "Ask in blocks".

**Cost.** In a plain terminal the model must choose. Either choice contradicts a file it has just
read.

**Proposal.** One sentence in §0.5 step 3: "terminal → `intake_form.py serve` and the URL; chat
questions only for what the form marks *not machine-readable*".

**Size** S.

**Verify.** Read.

### I-24 · Low · Evals: stale README, and no cases for the parts that changed

**Evidence.**
- `evals/README.md:3` "20 queries"; the set has 34 (15/19).
- `:103-105` baselines on a 22-query set.
- No case for the tooling and bug-report block.
- No EN home-REW near-miss (German `#31` only).
- No "resume inside a project folder" case.
- No TCC-opener case.
- The project `CLAUDE.md` (`rew_tool/project_seed.py`, `CLAUDE_MD`) does not tell a session to load
  the skill for every request in that folder.

**Cost.** Description edits (I-4) cannot be judged against a current baseline. The documented resume
gap (`evals/README.md:53-59`) stays open by design.

**Proposal.**
- Add the 11 probe queries of §6 plus two "resume in a project folder" cases.
- Re-run once and date the baseline in the README.
- Add one line to `CLAUDE_MD`: "Any request in this folder — including 'continue' or 'where were we'
  — starts by loading the `autosound-tuning` skill."
- Add a docs-check rule: the README's count equals `len(set)`.

**Size** S.

**Verify.** `run_trigger_eval.py` before and after.

### I-25 · Low · No reference has a table of contents; § pointers into a 67 KB file

**Evidence.**
- 31 files over 12 KB and none with a contents list. Among them: `core/diagnostic-techniques.md`
  (67.5 KB, 35 numbered §, cited by number from phases); `tooling/rew-tool-docs.md` (82 KB in 135
  lines, 5 headings); `core/capabilities.md` (52.6 KB).
- `phase_2_eq.md:77` cites a nonexistent "§50".
- Official guidance: "For reference files longer than 100 lines, include a table of contents at the
  top".

**Cost.** The model reads 16.6K tokens to find one §, or guesses.

**Proposal.** A one-line-per-§ index at the top of each file over 100 lines, generated by a script.
Fix `§50`.

**Size** S.

**Verify.** A docs-check rule: each file over 100 lines starts with an index, and every "§N" pointer
resolves.

### I-26 · Low · The Reference Map routes the model to a 494 KB HTML page, and to maintainer files

**Evidence.**
- `SKILL.md:158`: `patterns/target-curves/target_curves_visualizer.html`, "Interactive curve
  comparison". It is 494,522 B, ≈ 119K tokens if read.
- `SKILL.md:150`: `core/knowledge-architecture.md` is maintainer material (where knowledge belongs),
  routed in every session.

**Cost.** One curious read fills the context.

**Proposal.** Replace the row with "for the person: `curves.html` at the project root
(`phase_-1_intake.md:170`); never read it". Move maintainer rows to `CONTRIBUTING.md`.

**Size** S.

**Verify.** Read.

### I-27 · Low · Dangling and stale references

**Evidence.** Each is checked to exist or not.

*Dead scripts and files:*
- `core/driver-discipline.md:3` `scripts/start_gemini_tuner.sh`;
- `core/review-loop.md:5` `scripts/gemini_*.sh`;
- `core/review-loop.md:75`: a prompt file that does not exist (the real files are
  `scripts/reviewer-tuning.txt` and `reviewer-task-*.txt`);
- `phase_-1_intake.md:163` `data/dsp_profiles/` (really `knowledge/dsp/profiles/`).

*Nonexistent sections and phases:*
- "Phase 6": `core/process-phases.md:39`, `phase_-1_intake.md:142`;
- "Phase-4 method" for centre/rear: `phase_-1_intake.md:118`;
- `diagnostic-techniques §50`: `phase_2_eq.md:77`;
- `review-loop` "§5": `phase_3_control.md:21`; the table is in the contract's §5;
- `setup-critic-channel` "(§1–§4)": `tooling/setup-critic-channel.md:3`; there is no §4;
- "fatigue pass, item 7": `phase_4_listening.md:15`; there is no item 7;
- "(§23)" with no file: `virtual-first.md:135`.

*Retired carriers:*
- `target-curve-*` "project memory": `core/naming-and-structure.md:191,198`;
- "▶️ NEXT STEPS": `core/happy-paths.md:28`;
- "Pre-session #4 / §4", which is now STOPPING: `core/project-intake.md:160-161`,
  `phase_-1_intake.md:113`, `core/preset-strategy.md:3,16`, `knowledge/dsp/_TEMPLATE.md:13-14`,
  `knowledge/dsp/musway-m6v4.md:28`;
- "`process-phases.md` Phase 0" as the home of steps: `phase_-1_intake.md:35,196`,
  `core/naming-and-structure.md:3,25,198`; that file is now an index;
- "Nono per-band target generation": `core/process-phases.md:49`; it is now `target_bands.py`;
- "the ladder (SKILL.md)": `core/process-control.md:31`;
- "the pool": `SKILL.md:221`; undefined in the skill.

*Outside the skill root:*
- `docs/DESIGN-2026-09-17-phase1-variants.md`: `phase_1_foundation.md:3,59`, `virtual-first.md:180`.
  The name also collides with the project's `docs/` output folder.
- `MANUAL.md`: `phase_1_foundation.md:105`.
- `manual_step-by-step`: `phase_2_eq.md:77`.

*Stale facts:*
- `phase_-1_intake.md:83` "Ukrainian is the one that exists today" (four label files exist);
- `assets/data-contract-template.md:4` "Loaded as a system prompt into both chats at the session
  start".

*Link base* (`SKILL.md:32` declares every path skill-root-relative):
- 84 links in `references/**` resolve only from the skill root, so they break when rendered on GitHub;
- 22 resolve only relative to their own file (e.g. `virtual-first.md:104`,
  `capture-session-sheet.md:3`, `tooling/helix-vcp-workflow.md:5-6`, the translations), which
  breaks the declared rule.

**Cost.** Each is a dead end, or a model that invents the missing thing. The link base doubles every
lookup.

**Proposal.**
- Fix the list.
- Add a docs-check rule that resolves every backticked path and every `§N` against the skill root
  and fails on a miss, with an allow-list for project-runtime names.

**Size** S.

**Verify.** The rule fails today; after the fixes it passes.

### I-28 · Low · The gate report ends "OK — nothing to fix." under "phase 0 is not ready"

**Evidence.** Reproduced on an empty project: `contract.py check <p> --gate` exits 1, with
"▶ Nothing is wrong -- but phase 0 is not ready" at the top. At the bottom it prints "flaw map: every
row stands on a measurement" (vacuously, with no rows) and "**OK — nothing to fix.**". This was a
09-09 finding (summary §5) and is still open.

**Cost.** A model reading the tail reports "checks: done".

**Proposal.** The last line states the exit verdict ("NOT READY for phase 0 — 1 item"). An empty map
says "no rows".

**Size** S.

**Verify.** Run on an empty directory.

### I-29 · Low · Output-style rules that collide

**Evidence.**
- `SKILL.md:221` "A reply ends with one of two things (#58 P12): «введи це» [enter this]… or «виміряй ці N
  кривих» [measure these N curves]".
- Against it: `:205-211` ("3. The one question that actually needs him"), and the whole of Phase −1,
  which is questions.
- `:220` "no emoji and no praise" vs `:223` emoji section headings and `phase_4_listening.md:13`
  🟢/❌.

**Cost.** The model must choose which rule to break on most intake replies.

**Proposal.** Scope P12 to "a reply after a desk computation". Scope "no emoji" to tables of what he
types.

**Size** S.

**Verify.** Read.

### I-30 · Low · The instructions call the Arbiter "he"

**Evidence.**
- `SKILL.md:96` "the sheet he enters", `:207` "he wants to see", `:209` "needs him", `:211` "his
  standing rule".
- `phase_-1_intake.md` and `core/project-intake.md:75` ("he typed English").
- Many more across phases.

**Cost.** The skill is public. The model mirrors the pronoun to users who are not the author, and
author-specific anecdotes read as rules about "the user".

**Proposal.** "The Arbiter" or "they" in rules. Keep personal anecdotes in `why-these-rules.md`.

**Size** S.

**Verify.** `grep -nw "he\|him\|his"` over `SKILL.md` and `references/`.

### I-31 · Low · README/FAQ drift from the method, in all four languages

**Evidence.** §8 table:
- the path-3 link;
- the FAQ's cross-correlation ban;
- "shared knowledge base";
- "Claude Fable (5)".

`scripts/i18n-check.py` compares only heading levels and fenced blocks.

**Cost.**
- A reader is sent to a dead anchor.
- A tuner is told the method forbids what it prescribes.

**Proposal.**
- Fix the four rows.
- Extend i18n-check to inline code, link targets and numbers in prose.
- Add a README↔ADVANCED anchor check.

**Size** S.

**Verify.** i18n-check fails on the probe drifts listed in §1.

---

## 10. Top 10, ranked by value over risk

| rank | finding | why first | risk of the change |
|---:|---|---|---|
| 1 | **I-1** plugin route told to uninstall | wrong advice to every plugin user; text-only fix | none: two files and one docs-check rule |
| 2 | **I-2** reviewer's truth model | the second model anchors on the wrong source every round; two lines | low: prompt text, existing asserts |
| 3 | **I-11** owner's sentence in SKILL.md:82 | always-loaded contradiction of a signed ruling; one clause | none |
| 4 | **I-6** stale step pointers + duplicate 1.7 | routes fixes to the wrong step; numbers only | none |
| 5 | **I-16** doctor \| tee closes a failed check | a broken reviewer recorded as working | low: four lines of shell in a doc |
| 6 | **I-3** SKILL.md order + size + re-read line | protects every long session; the reorder alone is cheap | medium: moving text can drop a rule. Mitigate with a docs-check that every moved rule is still reachable |
| 7 | **I-7** one capture-round recipe | prevents wrong-series captures, a documented cost | low |
| 8 | **I-15** `--help` on `process.py` verbs | stops self-inflicted journal writes | low: argument guard + selftest |
| 9 | **I-4** description ≤ 1,024 | ≈ 140 tokens/turn on every session, spec compliance | medium: recall can move. Gate it on I-24's eval run |
| 10 | **I-9 / I-10 / I-8** route conflicts (solo modes at Phase 3, centre/rear placement, light touch) | removes judgments the model has no input for | medium: each needs the owner's decision first |

Next after these:
- I-20 and I-21: small text fixes, each removing a contradiction a session meets every tune;
- I-12 + I-18: one path, split virtual-first. The biggest saving and the biggest change.

---

## 11. Always-loaded cost, now and after the top proposals

| item | now | after I-3, I-4 (and I-18 for phases) |
|---|---:|---:|
| listing entry, every turn of every session | ≈ 390 tokens (1,536 chars shown of 1,808) | ≈ 255 tokens (≤ 1,024 chars) |
| slash-command descriptions, every turn | ≈ 65 | ≈ 65 |
| project `CLAUDE.md`, every turn in a project folder | ≈ 230 | ≈ 245 (+1 line, I-24) |
| SKILL.md body, per session (= per phase) | ≈ 8.4K by chars/4 (6.2K by words × 1.3) | ≈ 4.0K, and inside the 5,000-token re-attach |
| reconcile outputs at start | ≥ 1.1K (empty project) | unchanged |
| reading to start Phase 0 (SKILL + ordered files) | ≈ 43K | ≈ 23K |
| reading to start Phase −1 | ≈ 68K | ≈ 46K |

---

## 12. What I could not check, and why

- **The full trigger set (34 queries) was not run.** This container's account syncs a different
  car-audio skill (`rew-car-audio-tuning`, under `~/.claude/skills/synced/`), so a car-audio query
  could be answered by it instead. The recall figures would measure that collision, not this
  description. The 11 probes in §6 avoid the overlap: bug reports about TCC, and home-audio
  near-misses. They ran once each, and the README itself puts run-to-run spread at 2–3 per 22.
  A user with both skills installed has the same collision. That deserves its own check on the
  owner's machine.
- **Exact token counts.** chars/4 and words × 1.3 differ by about 30 % on SKILL.md. The re-attach
  finding holds under both. The API's token-counting endpoint was not used: no key in this
  container.
- **TCC.** The repo `ayukhno/autosound-tcc` is not in this session. Not checked:
  - the opener and system-prompt text TCC injects;
  - whether `get_tcc_state.reviewer.configured` still gates `model`/`reachable` (B9);
  - the MCP tool list against `SKILL.md:98` (B10);
  - which skill copy TCC loads.
- **Real-project reconcile cost.** Only an empty project was measured (≈ 1.1K tokens). A real
  project's `contract.py check` output depends on its map and ledger.
- **Behaviour after compaction (I-3)** is inferred from the documented budget and section offsets,
  not observed in a live session.
- **Windows and PowerShell** paths in the model-read docs were not exercised.
