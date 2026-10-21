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
| Captures | 1 | opus · medium | T5 #184 implementer |

## Findings per vendor

| seat | vendor | findings | real | real the other missed |
|---|---|---|---|---|
| plan review | Codex | 17 (1 blocker, 9 important, 7 minor) | 17 — the four spot-checked on the code (1, 3, 5, 6) hold; the rest taken as stated | — (no Claude seat beside it) |
| Reviewer group (T10–T11) | Opus | 6 (2 important, 4 minor) | 2 important checked on the code: TCC's `_codex_refusal` needs Codex's banner (tcc `critic.py:826`), and no test through a real caller; all 6 taken into one fix round | — |
| CI group (T12) | Opus | 5 (2 important, 3 minor) | both important shown by mutation on a copy (save outside the hold passed 10/10); all 5 taken | — |
