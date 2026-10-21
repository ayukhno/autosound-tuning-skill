# W-11 · v3.2.0 — the ledger (the arm without the engine, hub H-022; the Codex trial)

The wave is built without `superpowers` (`hub/bin/role skill --no-SP`): every PR of the wave carries `Engine: none`.
It is also the Codex trial (`hub:seam` «Models by role», the Arbiter 2026-10-21): the plan review, the group seats and
the final branch review run on Codex `gpt-6-astra`; on the first `Risk: high` group the two Opus seats run beside it.
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

## Agent runs

| group | runs | model | what |
|---|---|---|---|
| (plan) | 4 | sonnet · medium | code maps: rounds and levels; installers; captures, journal, CI; reviewer, text, agent start |
| (plan) | 1 | codex gpt-6-astra · high | the plan review |

## Findings per vendor

| seat | vendor | findings | real | real the other missed |
|---|---|---|---|---|
| plan review | Codex | 17 (1 blocker, 9 important, 7 minor) | 17 — the four spot-checked on the code (1, 3, 5, 6) hold; the rest taken as stated | — (no Claude seat beside it) |
