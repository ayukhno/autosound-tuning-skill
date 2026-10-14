# W-10 · v3.1.4 — the ledger (the arm without the engine, hub H-022)

The wave is built without `superpowers` (`hub/bin/role skill --no-SP`, the Arbiter's word 2026-10-14: «робимо зараз
без залучання скіла superpowers і потім проаналізуємо швидкість і якість»). Every PR of the wave carries
`Engine: none`. This file holds what H-022 compares: speed from `ok` to merge, agent runs, findings, fix rounds and
red CI runs, per group. Times are UTC.

## Milestones

| when | what |
|---|---|
| 2026-10-14 07:20 | `ok` on all 23 issues (#149, #150, #153–#173) |
| 2026-10-14 07:25 | five code maps started (sonnet · medium), one per group |
| 2026-10-14 07:31 | `docs/PLAN-W-10.md` written by the session from the maps; waits for «го» |
| 2026-10-14 07:34 | the Arbiter: #169 off the wave (a deferred task), no phone page; the plan cut to 19 tasks for 22 issues |

## Agent runs

| # | role | model · effort | group | started | ended | result |
|---|---|---|---|---|---|---|
| 1 | code map | sonnet · medium | Captures | 07:25 | 07:28 | 144 s, 43 tool calls, 133k tokens |
| 2 | code map | sonnet · medium | Installers + Windows CI | 07:25 | 07:27 | 128 s, 42 tool calls, 102k tokens |
| 3 | code map | sonnet · medium | Silent failures 3 + Windows text | 07:25 | 07:30 | 185 s, 57 tool calls, 127k tokens |
| 4 | code map | sonnet · medium | Agent start | 07:25 | 07:26 | 76 s, 28 tool calls, 67k tokens |
| 5 | code map | sonnet · medium | Method text | 07:25 | 07:27 | 84 s, 26 tool calls, 63k tokens |

## Per group

| group | issues | plan | built | group seats: Important+ | fix rounds | red CI | merged |
|---|---|---|---|---|---|---|---|
| Captures | #153–#156 | | | | | | |
| Windows | #158 | | | | | | |
| Installers | #157, #160–#164, #171, #172 | | | | | | |
| Agent start | #149, #150, #170 | | | | | | |
| Silent failures 3 | #159, #165–#167 | | | | | | |
| Method text | #168, #173 | | | | | | |
