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
| 2026-10-14 07:57 | «го» (the Arbiter: «155,156,154,163 — беремо. 168 … інформування та стандартні засоби … го!») |

## The Haiku trial

The Arbiter, 2026-10-14: «для механічних задач спробувати Хайку 5.5». `hub:seam` names a Sonnet trial for mechanical
work; this wave runs Haiku 5.5 instead — #163 at high, the release bookkeeping's version bumps at xhigh (the Arbiter: «як
медіум для Хайку маловато — можна спробувати хай чи екстрахай — треба зрозуміти можливість нової моделі»), each
reviewed on opus. Counted per task: defects the review finds, rework rounds, time. The result goes to the hub (H-019) at the wave's
end.

## Agent runs

| # | role | model · effort | group | started | ended | result |
|---|---|---|---|---|---|---|
| 1 | code map | sonnet · medium | Captures | 07:25 | 07:28 | 144 s, 43 tool calls, 133k tokens |
| 2 | code map | sonnet · medium | Installers + Windows CI | 07:25 | 07:27 | 128 s, 42 tool calls, 102k tokens |
| 3 | code map | sonnet · medium | Silent failures 3 + Windows text | 07:25 | 07:30 | 185 s, 57 tool calls, 127k tokens |
| 4 | code map | sonnet · medium | Agent start | 07:25 | 07:26 | 76 s, 28 tool calls, 67k tokens |
| 5 | code map | sonnet · medium | Method text | 07:25 | 07:27 | 84 s, 26 tool calls, 63k tokens |
| 6 | implementer T1 #153 | opus · high | Captures | 07:57 | 08:07 | `5f4a22c`; open points: capture-check by exact title, reconcile on old rounds, schema doc |
| 7 | implementer T2+T3 #155 #156 | opus · high | Captures | 07:57 | 08:04 | 340 s, 37 tool calls, 119k tokens; `bebab42` `b2eb99f` `74bbdfb` |
| 8 | implementer T4 #154 | opus · high | Captures | 07:57 | 08:01 | 198 s, 21 tool calls, 104k tokens; `3a6eeb3` |
| 9 | implementer T5–T7, T9 (#157 #172 #164 #171 #160 #161 #162) | opus · high | Installers | 07:57 | | |
| 10 | researcher T21 #173 | opus · medium | Method text | 07:57 | 08:06 | `f4ad845`; ~2700 words, proposal B (opt-in fill ≤ +3 dB) |
| 11 | implementer T18 #150 | opus · medium | Agent start | 08:00 | 08:02 | 121 s, 17 tool calls, 91k tokens; `117cc47` |
| 12 | implementer T20 #170 | opus · medium | Agent start | 08:00 | 08:05 | `655151a`; 62 queries, 11 new |
| 13 | implementer T22 #168 | opus · medium | Method text | 08:02 | 08:04 | 90 s, 15 tool calls, 88k tokens; `4e03328` |
| 14 | implementer T17a #149 | opus · high | Agent start | 08:02 | 08:08 | `4def84f` |
| 15 | task review T4 #154 | opus · high | Captures | 08:03 | 08:06 | no Critical/Important in code; 1 Important (docs), 3 Minor; the check_captures case is covered through verify() (process.py is T1's) |
| 16 | task review T2+T3 #155 #156 | opus · high | Captures | 08:05 | 08:07 | 140 s; T2 no Important (2 Minor); T3 1 Important (the D_ form drops a level), 3 Minor |
| 17 | docs review #168 #173 | opus · high | Method text | 08:06 | 08:11 | 5 Important (2 in #168, 3 in #173), 7 Minor; quotes and code refs all correct |
| 18 | fix round T4 #154 (the implementer resumed) | opus · high | Captures | 08:06 | 08:08 | `a4dc01f`; all three items |
| 19 | task review T1 #153 | opus · high | Captures | 08:07 | 08:10 | 2 Important (capture-check asks REW the list's title; check_captures writes un-normalised rows), 4 Minor |
| 20 | fix round T2+T3 (the implementer resumed) | opus · high | Captures | 08:07 | 08:09 | `d23d73e`; all four items |
| 21 | re-review T4 fix | opus · high | Captures | 08:08 | 08:09 | fix accepted, no regression |
| 22 | task review T17a #149 | opus · high | Agent start | 08:08 | 08:12 | 2 Important (OSError traceback; no next step when the skill is missing), 3 Minor |
| 23 | implementer T13, T16, T15, T14, T12 text (#159 #167 #166 #165 #158) | opus · high | Silent failures 3 + Windows | 08:09 | | |
| 24 | re-review T2+T3 fix | opus · high | Captures | 08:09 | 08:11 | four fixes accepted; 1 Important — a REGRESSION the fix made (the unit recased → two keys for one capture); 305 old titles unchanged |
| 25 | fix round T1 #153 (the implementer resumed) | opus · high | Captures | 08:10 | 08:16 | `bf54719`; all six (glossary: the fallback — contract._title_key reads none) |
| 26 | fix round T22 #168 (resumed) | opus · medium | Method text | 08:11 | 08:12 | `8895f6a`; all items; docs — no re-review |
| 27 | fix round T21 #173 (resumed) | opus · medium | Method text | 08:11 | 08:12 | `3046d55`; all items; docs — no re-review |
| 28 | fix of the regression T2 #155 (resumed) | opus · high | Captures | 08:11 | 08:12 | `306bd4c`; verified by the controller with a live probe (5 pairs share one key with their canonical form; old titles parse as before) — no re-review agent |
| 29 | fix round T17a #149 (resumed) | opus · high | Agent start | 08:12 | 08:14 | `f0616a2`; all five; verified by the controller live (6 folder cases: write, again, read-only, a folder, a dangling link, no project) — no re-review agent |
| 30 | re-review T1 fix | opus · high | Captures | 08:16 | 08:20 | fix accepted; 3 Minor → the group's fix round |
| 31 | group seat: silent failures | opus · high | Captures | 08:20 | | |
| 32 | group seat: tests | opus · high | Captures | 08:20 | | |

## Per group

| group | issues | plan | built | group seats: Important+ | fix rounds | red CI | merged |
|---|---|---|---|---|---|---|---|
| Captures | #153–#156 | | | | | | |
| Windows | #158 | | | | | | |
| Installers | #157, #160–#164, #171, #172 | | | | | | |
| Agent start | #149, #150, #170 | | | | | | |
| Silent failures 3 | #159, #165–#167 | | | | | | |
| Method text | #168, #173 | — (docs) | `4e03328` `0efbbe8` `8895f6a` · `f4ad845` `3046d55` | 5 Important (docs review) | 1 | | |
