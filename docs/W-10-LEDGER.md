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

## Agent runs

| # | role | model · effort | group | started | ended | result |
|---|---|---|---|---|---|---|
| 1 | code map | sonnet · medium | Captures | 07:25 | | |
| 2 | code map | sonnet · medium | Installers + Windows CI | 07:25 | | |
| 3 | code map | sonnet · medium | Silent failures 3 + Windows text | 07:25 | | |
| 4 | code map | sonnet · medium | Agent start | 07:25 | | |
| 5 | code map | sonnet · medium | Method text | 07:25 | | |

## Per group

| group | issues | plan | built | group seats: Important+ | fix rounds | red CI | merged |
|---|---|---|---|---|---|---|---|
| Captures | #153–#156 | | | | | | |
| Windows | #158 | | | | | | |
| Installers | #157, #160–#164, #171, #172 | | | | | | |
| Agent start | #149, #150, #170 | | | | | | |
| Silent failures 3 | #159, #165–#167 | | | | | | |
| Method text | #168, #169, #173 | | | | | | |
