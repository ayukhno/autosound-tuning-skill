# W-12 ledger

The numbers the plan's trial asks for (`docs/PLAN-W-12.md`). Filled from the first run.

## External reviewers

| when | reviewer | what | findings | real | in part | false | note |
|---|---|---|---|---|---|---|---|
| 2026-11-08 | Codex gpt-6-astra | #210's design | 14 | 13 | 1 | 0 | in part: it found the replay caches absent; they are in the local project, outside git |
| 2026-11-08 | Codex gpt-6-astra | the whole plan (11 issues) | 12 | 12 | 0 | 0 | plus lane F's 14 re-read: 7 taken in, 7 partial, those completed. Findings counted per task and lane; each checked at its main site |
| 2026-11-08 | Gemini 4 Argon High | T2 (#200 half), T3, T6, T7 | 12 | 9 | 2 | 1 | the Arbiter's word while Codex is out of tokens. In the excerpts-only package it claimed `record_decision` has no `@_locked` (it has, `process.py:3904`) and quoted a `finish_step(…, heard=None)` signature that is the plan's, not the code's; the false one was a hypothetical about `_read_slots`. 8's second half: `_set_head` updates in place |

Minutes per call were not timed.
