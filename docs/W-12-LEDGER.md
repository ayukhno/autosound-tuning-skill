# W-12 ledger

The numbers the plan's trial asks for (`docs/PLAN-W-12.md`). Filled from the first run.

## External reviewers

| when | reviewer | what | findings | real | in part | false | note |
|---|---|---|---|---|---|---|---|
| 2026-11-08 | Codex gpt-6-astra | #210's design | 14 | 13 | 1 | 0 | in part: it found the replay caches absent; they are in the local project, outside git |
| 2026-11-08 | Codex gpt-6-astra | the whole plan (11 issues) | 12 | 12 | 0 | 0 | plus lane F's 14 re-read: 7 taken in, 7 partial, those completed. Findings counted per task and lane; each checked at its main site |
| 2026-11-08 | Gemini 4 Argon High | T2 (#200 half), T3, T6, T7 | 12 | 9 | 2 | 1 | the Arbiter's word while Codex is out of tokens. In the excerpts-only package it claimed `record_decision` has no `@_locked` (it has, `process.py:3904`) and quoted a `finish_step(…, heard=None)` signature that is the plan's, not the code's; the false one was a hypothetical about `_read_slots`. 8's second half: `_set_head` updates in place |
| 2026-11-08 | Opus seat (`feature-dev:code-reviewer`, opus · high) | the same four tasks, the same plan text (`1167770`) | 19 | 19 | 0 | 0 | the whole tree, against Gemini's excerpts only; 8 min, 252K tokens |

Each checked at its main site. **Side by side on T2, T3, T6, T7:** found by both 6; by Opus only 13 (among them a failed push after the commit, a network call in `status`, an older copy refusing the key); by Gemini only 4 (the diff's shape, the delta's wrap and shallow merge, `_fmt_val`, `step_done`). One run on unequal inputs. The Arbiter, on it: «для коду беремо Опус. Джемені на переклади і роздумʼя, пошук ідей і тд.»

Minutes per call were not timed, except where noted.

## Claude seats on the code (the Opus seat, `feature-dev:code-reviewer`, opus · high)

The trial's weight, on the Arbiter's word: code passes on Opus, a narrow check of each fix round, Fable on the last fixes. Findings as counted by the seat, blocker / important / minor; each was checked at its main site before a fix.

| pass | B / I / M | what it caught that no local check had |
|---|---|---|
| installers (T9) | 1 / 0 / 3 | a test red on both non-Mac CI jobs (no `xcode-select` stand-in) |
| its narrow check | 0 / 0 / 1 | a refused install told to open a terminal |
| versions (T1–T3) | 2 / 4 / 4 | an unreviewed structural change reaching HEAD through `--on`; a selftest leaking temp folders |
| its narrow check | 0 / 3 / 2 | a candidate promoted by `variant switch`; a removed row not counted as a move |
| TCC contract (T4–T7) | 0 / 3 / 3 | `save` committing after a failed step; a key file reaching the remote |
| its narrow check | 0 / 0 / 5 | |
| `joint_search` slice 1 | 2 / 7 / 8 | two subs modelled and output differently; filters offered that the model does not build |
| its narrow check | 0 / 0 / 7 | |
| slice 2 | 1 / 11 / 7 | a `--fixed` row rewriting the sub's delay and polarity |
| its narrow check | 0 / 2 / 5 | |
| slice 3 | 1 / 6 / 6 | a printed row number not the one `--fixed` reads |
| `version_bench` | 2 / 6 / 8 | a pick from no curves; a channel left out with no word |
| narrow check of both | 0 / 3 / 1 | a crossing near 1 kHz with no upward leak test |
| the branch (final) | 0 / 5 / 5 | no step from a chosen row to a ledger version |
| Fable on the last fixes | 0 / 1 / 2 | a delta that would wipe a ledger's EQ and flip a polarity the search never decided |

**The alarm of the trial: a critical found only in acceptance (2026-11-09, `docs/W-12-ACCEPTANCE.md`).** A row's `delta` lost the EQ of a channel carried from a lower joint, so what banked was not what was scored (woofer↔mid 0.00 / 0.77 oct against 1.29 / 1.83). It was brought in by the session's own fix (`b92ab2f`) of Fable's finding, the last change before the PR: no test compared what is banked with what was scored, and no review pass ran after that fix. Fixed with a test that banks a whole chain and re-scores it. A rule for the PMO: acceptance runs after the last code change, and a fix to the last pass is reviewed like any other.

Replays on real curves caught what no reviewer did: the claim on C, the leak limit, an Fs floor above the reference tune's own mid HP, an empty default table.

## Backlog, named for the act

- `save`: a file `git rm --cached` by hand, covered by `.gitignore` but not by the housekeeping list, stops `save` at «could not commit» until a manual commit. Rare.
- A partial re-read of a candidate: the sheet still ends «run `attest`», and `attest` then refuses, naming `propose --on`. Safe, misleading.

## The replay on the Passat's curves (slice 1, a session's check)

- The history: candidate B, conditions off, 1.599 / 1.757 oct worst / median; the run had 1.60 / 1.76. Candidate C 0.983 / 0.999; the run 0.98 / 1.00. The scoring reproduces the run.
- The run's three candidates under the conditions all pass the leak. A relative limit, tried first, dropped one: it was replaced by the validated absolute limits, scaled only above a 65 Hz crossing.
- Every width peak is one delay step wide (C: 0.58 / 0.98 / 0.57 oct at 10.65 / 10.70 / 10.75 ms). Ranked by the width kept over ±0.10 ms, C has 0.55 and would rank 108 of 238; the Arbiter's ear chose it. The table describes; the ear decides.
- A shortlist by the reference-point width does not keep the run's own candidates; the top rows are of the same pattern (woofer HP above sub LP, the sub later). Not widened.
- Woofer↔mid and mid↔tweeter (later): the engine scores what the run scored, within 0.004 oct and 0.00 dB, on the run's own pairs and shifts. On mid↔tweeter the banked pairs sit near the top. On woofer↔mid at the defaults (same filters L and R, 1/6-oct corners) the rows are weak: margin 0.00, worst up to 0.23 oct against the run's 0.99, because the run's banked pairs have different filters L and R or corners off that grid. `--corners-per-side --no-same-family` admits them. So the defaults find the symmetric family; the runbook says so.
- Cost on these curves: 28.2 s, 112 MB with the conditions on; 45 s with them off. Slice 1's selftest: 41 s.

## Probes

- 2026-11-08, T8: `gemini-3.8-flash-high` under ADC, a one-line prompt: 4 of 4 answered, 3.0–7.6 s (agy 1.5.3). A large prompt on High is not tested.
- 2026-11-08: `gemini-4-argon-high` did not answer the one-line probe within 60 s once, after answering earlier the same day; `gemini-4-argon-medium` answered.

## For the PMO (hub-kit), the Arbiter's word 2026-11-08

To go into the end-of-wave ticket for the hub, and from it to the PMO advice. No write to hub-kit from here.

- **The code reviewer: `feature-dev:code-reviewer` on Opus (high), one fresh seat per group's diff, the whole tree open.** It is Anthropic's agent type and read-only. So far in this wave: 19 of 19 real on four tasks where Gemini 4 on excerpts had 9 real and 2 in part of 12, and 13 of Opus's findings were its alone; on the installer group a blocker a Mac could not show (a test red on both non-Mac CI jobs); on the versions group 2 blockers and 4 important, among them an unreviewed structural change reaching HEAD through the new `--on`.
- **The brief that made it work:** no finding without a `path:line` opened and quoted, an inventory of every site of a class, a severity, a «checked -> clean» row per category, a section for what could not be checked.
- **Split the work:** code to this seat; translations, thinking-through and ideas to Gemini.

