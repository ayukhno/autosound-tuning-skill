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

| task | effort | time | defects (Important / Minor) | rework |
|---|---|---|---|---|
| #163 help one-liner | high | 147 s, 89k tokens | 0 / 2 (+1 pool-worthy) | one round, by Haiku, all three done (`518b55b`) |

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
| 9 | implementer T5–T7, T9 (#157 #172 #164 #171 #160 #161 #162) | opus · high | Installers | 07:57 | 08:22 | 1328 s, 100 tool calls, 266k tokens; `c02fd32` `cb20b50` `2007ca7` `c4f6fda`; ps1 cases unrun (no pwsh here) |
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
| 23 | implementer T13, T16, T15, T14, T12 text (#159 #167 #166 #165 #158) | opus · high | Silent failures 3 + Windows | 08:09 | 08:37 | 1653 s, 160 tool calls, 310k tokens; `f8e97f7` `6cd0755` `c3144ca` `5104af8` `7f28c01`; TCC records the clipboard call with no review path — an ask for the candidate's ticket |
| 24 | re-review T2+T3 fix | opus · high | Captures | 08:09 | 08:11 | four fixes accepted; 1 Important — a REGRESSION the fix made (the unit recased → two keys for one capture); 305 old titles unchanged |
| 25 | fix round T1 #153 (the implementer resumed) | opus · high | Captures | 08:10 | 08:16 | `bf54719`; all six (glossary: the fallback — contract._title_key reads none) |
| 26 | fix round T22 #168 (resumed) | opus · medium | Method text | 08:11 | 08:12 | `8895f6a`; all items; docs — no re-review |
| 27 | fix round T21 #173 (resumed) | opus · medium | Method text | 08:11 | 08:12 | `3046d55`; all items; docs — no re-review |
| 28 | fix of the regression T2 #155 (resumed) | opus · high | Captures | 08:11 | 08:12 | `306bd4c`; verified by the controller with a live probe (5 pairs share one key with their canonical form; old titles parse as before) — no re-review agent |
| 29 | fix round T17a #149 (resumed) | opus · high | Agent start | 08:12 | 08:14 | `f0616a2`; all five; verified by the controller live (6 folder cases: write, again, read-only, a folder, a dangling link, no project) — no re-review agent |
| 30 | re-review T1 fix | opus · high | Captures | 08:16 | 08:20 | fix accepted; 3 Minor → the group's fix round |
| 31 | group seat: silent failures | opus · high | Captures | 08:20 | 08:25 | 3 Important (the own-range check compares REW to itself and the band never reaches the person; a stale as_in_rew; a refused title recorded with no reason), 4 Minor |
| 32 | group seat: tests | opus · high | Captures | 08:20 | 08:25 | 4 Important (3 are behaviour: a check before capture-taken; a before-form list offers the wrong rename; a superseded row hides a standing one), 3 Minor |
| 33 | task review T5 #157 #172 | opus · high | Installers | 08:22 | 08:25 | 1 Important (macOS iconv passes bytes above U+10FFFF), 2 Minor |
| 34 | task review T6 #164 #171 | opus · high | Installers | 08:22 | 08:27 | no Critical/Important; 3 Minor |
| 35 | task review T7 #160 | opus · high | Installers | 08:22 | 08:26 | 1 Important (a no-change stop after consent still replaces the receipt), 3 Minor |
| 36 | task review T9 #161 #162 | opus · high | Installers | 08:22 | 08:29 | 3 Important (the reset rewrites the person's own window; the CI probe may not prove the bad path reached 5.1; CI can test the double-click forms), 5 Minor |
| 37 | implementer T8 #163 — the Haiku trial | haiku · high | Installers | 08:22 | 08:24 | 147 s, 17 tool calls, 89k tokens; `089d3b3`; red first (5), then green; CRLF kept |
| 38 | review of the Haiku T8 (trial count) | opus · high | Installers | 08:24 | 08:28 | no Important, no functional defect; 2 Minor in the checker (~10 min), 1 pool-worthy (the header comment's `main`); the trailer names Opus — the brief's fault, not Haiku's |
| 39 | Haiku T8 rework (resumed) | haiku · high | Installers | 08:28 | 08:31 | `518b55b`; all three, each red on a scratch copy first |
| 40 | fix round Installers T5 T7 T9 (resumed) | opus · high | Installers | 08:31 | | |
| 41 | Captures group fix: process.py part (T1's implementer) | opus · high | Captures | 08:37 | | |
| 42 | Captures group fix: naming.py part (T2/T3's implementer) | opus · high | Captures | 08:37 | 08:39 | `291dea7`; 461 old titles unchanged; verified live by the controller |
| 43 | Captures group fix: verify part (T4's implementer) | opus · high | Captures | 08:37 | 08:39 | `43a3d6a` `a6ed7cc` `df65abc` |
| 44 | task review T13 #159 | opus · high | Silent failures 3 | 08:37 | 08:40 | 1 Important (cwd's .critic-env still read and applied), 3 Minor |
| 45 | task review T15 #166 | opus · high | Silent failures 3 | 08:37 | 08:42 | 1 Important (a duplicate keeps the weaker record), 4 Minor; TCC's clipboard record confirmed (no review path) |
| 46 | task review T14 #165 | opus · high | Silent failures 3 | 08:37 | 08:42 | 1 CRITICAL (rew_tool selftest red at the commit — the implementer reported green; the controller reproduced exit 70), 1 Important (strict glossary silently accepts a malformed one), 2 Minor |
| 47 | fix round Silent failures 3: T13 T14 T15 + project_io (resumed) | opus · high | Silent failures 3 | 08:42 | | |

## Quality notes

- **A false green (T14, #165).** The implementer's report said every changed module's selftest passed; the task
  review ran rew_tool.py's selftest at 5104af8 and got exit 70, and the controller reproduced it at HEAD. Caught by the
  task review, before any group seat or CI.
- **A regression made by a fix (T2, #155).** The fix round of d23d73e recased the level's unit and gave one capture two
  keys; the re-review caught it; fixed in 306bd4c, verified live.
- **Fixes that did not reach the end (T1, #153).** The first build stored the typed title correctly but the check
  still asked REW the list's spelling; the task review caught it; the group seats found three more behaviour gaps at
  the joins of #153/#154/#155.

## Per group

| group | issues | plan | built | group seats: Important+ | fix rounds | red CI | merged |
|---|---|---|---|---|---|---|---|
| Captures | #153–#156 | | | | | | |
| Windows | #158 | | | | | | |
| Installers | #157, #160–#164, #171, #172 | | | | | | |
| Agent start | #149, #150, #170 | | | | | | |
| Silent failures 3 | #159, #165–#167 | | | | | | |
| Method text | #168, #173 | — (docs) | `4e03328` `0efbbe8` `8895f6a` · `f4ad845` `3046d55` | 5 Important (docs review) | 1 | | |
