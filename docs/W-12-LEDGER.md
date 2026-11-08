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

## Probes

- 2026-11-08, T8: `gemini-3.8-flash-high` under ADC, a one-line prompt: 4 of 4 answered, 3.0–7.6 s (agy 1.5.3). A large prompt on High is not tested.
- 2026-11-08: `gemini-4-argon-high` did not answer the one-line probe within 60 s once, after answering earlier the same day; `gemini-4-argon-medium` answered.

## For the PMO (hub-kit), the Arbiter's word 2026-11-08

To go into the end-of-wave ticket for the hub, and from it to the PMO advice. No write to hub-kit from here.

- **The code reviewer: `feature-dev:code-reviewer` on Opus (high), one fresh seat per group's diff, the whole tree open.** It is Anthropic's agent type and read-only. So far in this wave: 19 of 19 real on four tasks where Gemini 4 on excerpts had 9 real and 2 in part of 12, and 13 of Opus's findings were its alone; on the installer group a blocker a Mac could not show (a test red on both non-Mac CI jobs); on the versions group 2 blockers and 4 important, among them an unreviewed structural change reaching HEAD through the new `--on`.
- **The brief that made it work:** no finding without a `path:line` opened and quoted, an inventory of every site of a class, a severity, a «checked -> clean» row per category, a section for what could not be checked.
- **Split the work:** code to this seat; translations, thinking-through and ideas to Gemini.

