# W-11 · v3.2.0 — the ledger (the arm without the engine, hub H-022; the Codex trial)

The wave is built without `superpowers` (`hub/bin/role skill --no-SP`): every PR of the wave carries `Engine: none`.
It was to be the Codex trial (`hub:seam` «Models by role», the Arbiter 2026-10-21): the plan review, the group seats and
the final branch review on Codex `gpt-6-astra`. Only the plan review ran on it: Codex's limits ran out on 2026-10-21, and the
Arbiter moved the seats to Opus and the texts to Gemini.
This file holds what H-022 and H-019 compare: speed from `ok` to merge, agent runs, findings per vendor (all, real,
real the other seat missed), fix rounds and red CI runs, per group. Times are UTC.

## Milestones

| when | what |
|---|---|
| 2026-10-21 08:27 | milestone `W-11 · v3.2.0` (milestone 10) opened on the Arbiter's word; 14 issues #176–#189, `ok` on 13 |
| 2026-10-21 08:36 | #189 (item 12) `ok` after the discussion (the Arbiter: take it into W-11) |
| 2026-10-21 ~08:31 | four code maps started (sonnet · medium), one per lane's groups |
| 2026-10-21 08:40 | #190 opened from `/test-audit` (report only), no `ok` |
| 2026-10-21 ~08:45 | `docs/PLAN-W-11.md` written by the session from the maps; Codex's plan review started |
| 2026-10-21 ~08:55 | Codex's plan review back: 17 findings; checked against the code, taken into the plan; waits for «го» and the control answer |
| 2026-10-21 ~09:08 | «го» (the Arbiter); the control — the method adds it itself; #190 `ok`; Codex's limits out — the seats on Opus, text on Gemini |

## Agent runs

| group | runs | model | what |
|---|---|---|---|
| (plan) | 4 | sonnet · medium | code maps: rounds and levels; installers; captures, journal, CI; reviewer, text, agent start |
| (plan) | 1 | codex gpt-6-astra · high | the plan review |
| Captures | 0 | session | T3 #182 built by the session (test red first) — `caf055d` |
| CI (T15) | 0 + 1 | session; opus · medium | #190: `band_target` retired by the session (`31c7ec7`); the lock sweep, report only |
| Reviewer | 1 | opus · medium | T10 #178 implementer — `27bf446` |
| Reviewer | 1 | sonnet · medium | T11 #186 implementer, the Sonnet trial — `1162dab`, green first time, nothing contradicting the map |
| CI | 1 | opus · medium | T12 #185 implementer — `0ce1c76` |
| Captures | 1 | opus · high | T4 #183 implementer — `cf8d05a` |
| Reviewer | 1 | opus · high | group seat (`pr-test-analyzer`) on T10–T11 |
| CI | 1 | opus · high | group seat (`pr-test-analyzer`) on T12, with mutations on copies |
| Reviewer | 1 | opus · medium | T10 fix round (resumed) |
| CI | 1 | opus · medium | T12 fix round (resumed) |
| Captures | 1 | opus · high | T4 task review (`silent-failure-hunter`) |
| Captures | 1 | opus · medium | T5 #184 implementer — `5a16e1c` |
| Captures | 1 | opus · high | T4 fix round (resumed) — `ff41e77` |
| Captures | 1 | opus · high | T4 fix re-review (`silent-failure-hunter`): no regression; loose ends by the session `11dda2c` |
| Captures | 1 | opus · high | group seat (`pr-test-analyzer`) on T3–T5 — fixes wait for T1 (process.py) |
| Journal | 1 | opus · high | T6 #187 implementer — `ce3d5a1` |
| Journal | 1 | opus · high | group seat (`silent-failure-hunter`) |
| Journal | 1 | opus · high | T6 fix round (resumed) — `2dc6875` |
| Journal | 1 | opus · high | T6 fix re-review; its follow-up by the session `1561e10` (the retry 2 s, inside TCC's 5 s) |
| Installers | 1 | opus · high | T7 #179 implementer — `e276a4c` |
| Installers | 1 | opus · high | T7 task review |
| Installers | 1 | opus · high | T7 fix round (resumed) — `46358c5` |
| Installers | 1 | opus · high | T7 fix re-review: 2 regressions (Ubuntu CI red; the EXIT trap could delete an inherited path's parent) |
| Installers | 1 | opus · high | T7 second fix (resumed) — `8ae4e17` |
| Installers | 1 | opus · high | T8 #180 implementer — `2dd4c2f` |
| Installers | 1 | opus · high | T8 task review |
| Installers | 1 | opus · high | T8 fix round (resumed) — `96cf29c` |
| Installers | 1 | opus · high | T8 fix re-review: 1 regression (leftovers from before the call counted as a change) |
| Installers | 1 | opus · high | T8 second fix (resumed) |
| Installers | 1 | opus · medium | T9 #181 implementer — `1c2bd89` |
| Rounds and levels | 1 | opus · high | T1 #176 implementer — `c2f6e2a` `7587a0a` `b0c2d49` `bf54b0d` (~29 min) |
| Rounds and levels | 1 | opus · high | T1 task review: 1 critical (a required capture turned into the control), 5 important |
| Rounds and levels | 1 | opus · high | T1 fix round (resumed) — `ff1deb7` `23b301d` `8bc04f9` |
| Rounds and levels | 1 | opus · high | T1 fix re-review: 1 high (rounds from before `control_added`), the slope-blind reach |
| Rounds and levels | 1 | opus · high | T1 second fix (resumed) — `8793fd3` `aa747ef` |
| Rounds and levels | 1 | opus · high | T2 #177 implementer — `2af8721` |
| Rounds and levels | 1 | opus · high | T2 task review: unplanned takes leaking into the session probe |
| Rounds and levels | 1 | opus · high | T2 fix (resumed) — `fd9a499` (without it a false LEVEL −5 dB) |
| Rounds and levels | 2 | opus · high | group seats (silent-failure, test-analyzer) on T1–T2 |
| Rounds and levels | 1 | opus · high | group fix round (resumed T1) — `4b80724` `a69904f` `5fd1a00` |
| Rounds and levels | 1 | opus · high | group fix re-review: the control judged against the base never gives a verdict after a time alignment; LEVEL noise |
| Rounds and levels | 1 | opus · high | third fix (resumed T1): the control against the PREVIOUS round, as the bench did — `eb4da50` `e9a9a3b` `f00fa3d` `3327af3` |
| Rounds and levels | 1 | opus · high | third fix re-review: 2 high (a re-taken series against itself; a previous control never taken) |
| Rounds and levels | 1 | opus · high | fourth fix (resumed T1) — `a245774` `497c3ab` `e7ea437` |
| Captures | 1 | opus · high | T16 #191 implementer — `22d8988` |
| Captures | 1 | opus · high | T16 review: the brief's own mistake (a listed title kept off `optional`) reverted; a superseded bad optional hidden |
| Captures | 1 | opus · high | T16 fix (resumed) — `f77cdde` |
| Captures | 1 | opus · medium | Captures group fix round (resumed T4) — `9f658c7` (the drift read the wrong take) |
| Installers | 1 | opus · high | group seat: no defect, 3 test gaps — it also downloaded pwsh and ran the Windows cases on the Mac, which popped Cursor up on the user's screen (now forbidden in every brief) |
| Installers | 1 | opus · high | group fix round (resumed T8) — `0da8199` |
| Agent start | 0 | session | T14 #189: four eval runs (sonnet-5-5 ×3, opus-5-5 ×1), 26/26 neutral recall every run; the description stays — `30d2655` |
| (end) | 1 | opus · high | the final branch review |
| Method text | 0 | session + Advisor (Gemini) | T13 #188: English by the session `c939da0`; uk/de/pl from gemini-3.8-flash-high on its second ask (quota spent at the first) `e18a6c0` |

## Findings per vendor

| seat | vendor | findings | real | real the other missed |
|---|---|---|---|---|
| plan review | Codex | 17 (1 blocker, 9 important, 7 minor) | 17 — the four spot-checked on the code (1, 3, 5, 6) hold; the rest taken as stated | — (no Claude seat beside it) |
| Reviewer group (T10–T11) | Opus | 6 (2 important, 4 minor) | 2 important checked on the code: TCC's `_codex_refusal` needs Codex's banner (tcc `critic.py:826`), and no test through a real caller; all 6 taken into one fix round | — |
| CI group (T12) | Opus | 5 (2 important, 3 minor) | both important shown by mutation on a copy (save outside the hold passed 10/10); all 5 taken | — |
| T4 task review | Opus | 7 (1 important, 6 minor) | 1 important: TCC shows «Start REW» for the new 69 — sent to TCC (SKL-081, hub #299); 5 minor taken | — |
| T4 fix re-review | Opus | 4 (2 low, 2 nit) | no regression; 2 nits + 1 doc line by the session; one «nit» fix did not work (the date kept as the string «None») — found by the Captures seat | — |
| Captures group (T3–T5) | Opus | 5 (2 important, 3 minor) | 2 important: CONTRACT.md's 69 (fixed `b8eefb2`), no `--session` test with a moved list; 1 minor: the None-date fix ineffective | — |
| Journal group (T6) | Opus | 6 (1 important, 5 minor) | 1 important: the rule hid a real change of writer (a copy with no git) — fixed by the timeout flag | — |
| T6 fix re-review | Opus | 4 (1 medium, 3 low) | the 10 s retry past TCC's 5 s lock wait — cut to 2 s | — |
| T7 task review | Opus | 8 (1 important, 7 minor) | all taken | — |
| T7 fix re-review | Opus | 6 (1 high, 1 medium, 3 low, 1 note) | 2 regressions of the fix, both real (reproduced) | — |
| T8 task review | Opus | 5 (1 medium, 4 low) | all taken; the medium (no receipt during the download) became save-and-restore | — |
| T8 fix re-review | Opus | 6 (2 medium, 4 low) | 1 regression of the fix (pre-existing leftovers), 1 readability (winget's output on 5.1) | — |
| T1 task review | Opus | 13 (1 critical, 5 important, 7 minor) | all real; the critical reproduced (phase 3 plan `ALL_5 (rta)`) | — |
| T1 fix re-review | Opus | 8 (1 high, 3 medium, 4 low) | the high was dev-build only; the slope-blind ½-octave reach real | — |
| T2 task review | Opus | 6 (1 medium, 5 low) | the medium real (the session probe counted unplanned takes) | — |
| Rounds group, silent-failure | Opus | 11 (4 important, 7 minor) | all real (LEVEL line silent on doubts; full-range channels reached no band) | — |
| Rounds group, tests | Opus | 9 | the bench's full chain untested end to end; TCC keys unpinned | — |
| Rounds group fix re-review | Opus | 7 (2 high, 2 medium) | both highs a design flaw: the control judged against the base | — |
| T1 third fix re-review | Opus | 6 (2 high, 2 medium) | both highs hid a real chain change | — |
| T16 review | Opus | 4 (1 high, 1 medium) | the high was the session's brief (outside #191), reverted | — |
| Installers group | Opus | 6 (1 important, 5 minor) | test gaps, no defect | — |
