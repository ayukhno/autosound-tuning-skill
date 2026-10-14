# W-10 · v3.1.4 — the ledger (the arm without the engine, hub H-022)

The wave is built without `superpowers` (`hub/bin/role skill --no-SP`, the Arbiter's word 2026-10-14: «робимо зараз
без залучання скіла superpowers і потім проаналізуємо швидкість і якість»). Every PR of the wave carries
`Engine: none`. This file holds what H-022 compares: speed from `ok` to merge, agent runs, findings, fix rounds and
red CI runs, per group. Times are UTC.

## Milestones

| when | what |
|---|---|
| 2026-10-14 07:20 | `ok` on all 23 issues (#149, #150, #153–#173); #169 lost it at 07:33 (deferred), so 22 |
| 2026-10-14 07:25 | five code maps started (sonnet · medium), one per group |
| 2026-10-14 07:31 | `docs/PLAN-W-10.md` written by the session from the maps; waits for «го» |
| 2026-10-14 07:34 | the Arbiter: #169 off the wave (a deferred task), no phone page; the plan cut to 19 tasks for 22 issues |
| 2026-10-14 07:57 | «го» (the Arbiter: «155,156,154,163 — беремо. 168 … інформування та стандартні засоби … го!») |
| 2026-10-14 10:25 | PR #174 opened (`Engine: none`); its CI run 38549352727 is the release's test run |
| 2026-10-14 ~10:35 | PR #174's CI run 38549352727 green on all five jobs; main fast-forwarded to `a5dd51d` (PR merged) |
| 2026-10-14 ~10:38 | the candidate `beta-v3.1.4-rc1` on `a5dd51d` (tag-check --candidate: 5 of 5; Good "git" signature) |
| 2026-10-14 ~10:40 | hub #283 (SKL-073) to TCC: N2 as its re-pin PR run on three systems + the seam list; hub #278 closed done |
| 2026-10-14 ~11:00 | the Arbiter's VM run on rc1 (Windows-ARM64) — see below |
| 2026-10-14 11:36 | TCC's N2 answer on hub #283 (TCC PR #214, run 38555923376): every failure TCC's (the re-pin, tcc #200) or a likely flake; the skill's own: none blocking, three optional |
| 2026-10-14 ~11:45 | the Arbiter: «rc2, тоді реліз» — the three optional in rc2, then the release |
| 2026-10-14 12:08 | the candidate `beta-v3.1.4-rc2` on `ac9faa3` (PR #175, CI green after one Windows rerun) |
| 2026-10-14 ~12:12 | the release bookkeeping on Haiku · xhigh (`71a56cf`), reviewed on opus: 0 defects |
| 2026-10-14 12:20 | `beta-v3.1.4-rc3` on `71a56cf`, then **v3.1.4** on the same commit (see N2 below) |
| 2026-10-14 ~12:25 | the milestone closed (22 issues, each with its receipt); hub #247, #258, #259, #261, #269, #274 closed done |

## The Arbiter's VM run on rc1

2026-10-14 ~11:00 UTC, Windows-ARM64. `install.cmd` double-clicked from `C:\w10 rc1!` (a space and a `!`) — the window
held, «Finished with exit code 0»; `.\install.cmd -DryRun` from PowerShell — no pause, exit 0; the candidate installed
by the README's two-line form with `-SkillRef beta-v3.1.4-rc1` — exit 0, receipt `ready`, `method_ref` the candidate,
`missing: []`, `codex_link: kept` (made by the double-click run, whose local install.ps1 was the candidate's); the
junction `~\.agents\skills\autosound-tuning` → `~\.claude\skills\.autosound-tuning-src\skills\autosound-tuning`;
Codex lists `autosound-tuning:autosound-tuning` (the prefix looks like a plugin's — not proven to come from the link).
#161's 5.1-under-pwsh-7 run skipped: no pwsh 7 on the VM; the Windows CI's probe covers it.

## N2 on rc1 and rc2

TCC's re-pin PR #214 at `a5dd51d` (run 38555923376): macOS 17, Ubuntu 18, Windows 21 failures, each named with its
owner on hub #283. TCC's: gap 1 (#153, key matching — 11 tests), gap 3 (#154, the window's own band — 6), the hub #274
xfail now XPASS (3), all for the re-pin (tcc #200); one Ubuntu flake (a git child racing a temp folder's cleanup).
The skill's, optional, all three in rc2: `installer-consistency`'s #161 `module-path-pwsh` case expected the
Documents entry first where `GetFolderPath('MyDocuments')` says `''` (TCC's tests set `USERPROFILE` to a bare folder;
the reset rightly leaves the entry out); two invalid escapes in that script's docstrings (`\M`, `\i`); no `### Upgrading`
line for #153. rc2 changes only that script and CHANGELOG — no new N2.

rc3: the release bookkeeping had to close S-099 (#163) for `pool-closed`, and S-099's old status line names no
version, so `promotes` refused the release as rc2 plus bookkeeping. The preflight's own way — «cut rc3» — on the
bookkeeping commit `71a56cf` (CI run 38561983012 green on all five jobs); v3.1.4 promotes rc3 with nothing beside it.
The CHANGELOG and S-104 say rc2 plus the bookkeeping, which is what rc3 is.

## The Haiku trial

The Arbiter, 2026-10-14: «для механічних задач спробувати Хайку 5.5». `hub:seam` names a Sonnet trial for mechanical
work; this wave runs Haiku 5.5 instead — #163 at high, the release bookkeeping's version bumps at xhigh (the Arbiter: «як
медіум для Хайку маловато — можна спробувати хай чи екстрахай — треба зрозуміти можливість нової моделі»), each
reviewed on opus. Counted per task: defects the review finds, rework rounds, time. The result goes to the hub (H-019) at the wave's
end.

| task | effort | time | defects (Important / Minor) | rework |
|---|---|---|---|---|
| #163 help one-liner | high | 147 s, 89k tokens (the first turn); with its rework 285 s, ≈110k | 0 / 2 (+1 pool-worthy) | one round, by Haiku, all three done (`518b55b`) |
| release bookkeeping (15 files, 28 pins, 3 versions, CHANGELOG heading + index, two status lines) | xhigh | ~110 s, 77k tokens, 11 tool uses | 0 / 0 | none; it caught the brief's own miscount (26 pins → 28) |

The result for H-019: on mechanical work from a brief that holds the exact text, Haiku 5.5 at high and xhigh needed no
Important fix; at xhigh it checked the brief against the tree and reported the difference instead of following it.

## Agent runs

In all (the independent evaluation's count from the session transcript, 2026-10-14): 47 runs — 45 `Agent`
calls and 2 seen only by their notification — and 28 resumes by `SendMessage`; hub #284's «≈ 66» is the same order.
A resumed agent's tokens below are its cumulative total, not the round's, where a row says so.

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
| 40 | fix round Installers T5 T7 T9 (resumed) | opus · high | Installers | 08:29 | 08:49 | 1010 s, 377k tokens cumulative for the resumed agent (the round ≈110k); `7a4b723` `d0fad70` `fdf548d` `b5cb0ab`, + `eb3cc4c` (bounded_run kept local) and `ac4b0a2` (#158 CI: job `installers-windows`) |
| 41 | Captures group fix: process.py part (T1's implementer) | opus · high | Captures | 08:37 | 08:47 | 557 s; `1efad5c`; TCC unaffected by the OK line's band suffix (it re-reads state, not stdout — checked by the controller) |
| 42 | Captures group fix: naming.py part (T2/T3's implementer) | opus · high | Captures | 08:37 | 08:39 | `291dea7`; 461 old titles unchanged; verified live by the controller |
| 43 | Captures group fix: verify part (T4's implementer) | opus · high | Captures | 08:37 | 08:39 | `43a3d6a` `a6ed7cc` `df65abc` |
| 44 | task review T13 #159 | opus · high | Silent failures 3 | 08:37 | 08:40 | 1 Important (cwd's .critic-env still read and applied), 3 Minor |
| 45 | task review T15 #166 | opus · high | Silent failures 3 | 08:37 | 08:42 | 1 Important (a duplicate keeps the weaker record), 4 Minor; TCC's clipboard record confirmed (no review path) |
| 46 | task review T14 #165 | opus · high | Silent failures 3 | 08:37 | 08:42 | 1 CRITICAL (rew_tool selftest red at the commit — the implementer reported green; the controller reproduced exit 70), 1 Important (strict glossary silently accepts a malformed one), 2 Minor |
| 47 | fix round Silent failures 3: T13 T14 T15 + project_io (resumed) | opus · high | Silent failures 3 | 08:42 | 08:54 | `8f1a332` `f991c10` `5cfe825` `c65c8fd`; exit codes checked per module this time |
| 48 | re-review of the Captures group fix | opus · high | Captures | 08:47 | 08:53 | group fix accepted; 2 Minor (the AMBIGUOUS fix not in the stored issue — TCC's card shows issues; a window between two REW reads) |
| 49 | group seat: silent failures (also the fixes' re-review) | opus · high | Installers | 08:49 | 08:55 | 3 Important (keep-local's reset before the arm; the #161 guard matches SQL Server's path — CI red there; continue-on-error hides Windows selftests), 4 Minor |
| 50 | group seat: tests | opus · high | Installers | 08:49 | 08:58 | 5 Important (the #161 check; #157 fooled by sh -c; #164 dry-run checkout never run; #161 child path never run; #171 ps1 case passes on old code), many Minor |
| 51 | group seat: silent failures (also the fixes' re-review) | opus · high | Silent failures 3 + Windows | 08:54 | 09:00 | 1 Important — a REGRESSION from T15's fix round (the `-answer` strip joins two reviews; one critique dropped), 4 Minor |
| 52 | group seat: tests | opus · high | Silent failures 3 + Windows | 08:54 | 08:59 | 3 Important (#166 tested with a record TCC does not send — the real one still gives two; #158's readlink stand-in doubles the prefix on Windows; #167's CLI check passes on the old code), 11 Minor |
| 53 | implementer T17b #149 (the installers' Codex link) | opus · high | Agent start | 08:54 | 09:06 | `67789c5`; 11 sh cases + a mutation test; ps1 cases wait for Windows CI |
| 54 | group fix round Silent failures 3 + Windows text (resumed) | opus · high | Silent failures 3 + Windows |  | 09:14 | `0d7db2c` (#166 the five rules) `c98a06c` `42cf66f` `cd5a6cc` `06a7176`; exit codes 0 per module; ruff, encoding-check clean |
| 55 | group fix round Installers (resumed) | opus · high | Installers | 09:06 | 09:25 | 1114 s, 465k tokens cumulative (the round ≈88k); 11 commits `40a4d47`..`404b6d4`, `99bddb2`, + the #167 shell=True CI step `694ef37` |
| 56 | task review T17b #149 | opus · high | Agent start | 09:06 | 09:10 | no Important; 6 Minor (ownership by prefix; a failed link under --codex; doctor; repoint gap) |
| 57 | group seat: silent failures | opus · high | Agent start | 09:06 | 09:12 | 4 Important (a moved rule nobody reads; project-context eval queries cannot fail; AGENTS/CLAUDE.md say the gate does what it does not; a stale Codex link off PATH), 4 Minor |
| 58 | group seat: tests | opus · high | Agent start | 09:06 | 09:11 | 3 Important (#170 index keying untested; #149 ps1 link never run; the uninstall only read), 6 Minor |
| 59 | Agent start group fix (a1): SKILL.md, capabilities (T18's implementer) | opus · medium | Agent start |  | 09:14 | `c54ce26`; SKILL.md 17,416 bytes before the Map |
| 60 | Agent start group fix (a2): the trigger eval (T20's implementer) | opus · medium | Agent start | 09:12 | 09:15 | `78da32e`; 68 queries (62 neutral, 17 project) |
| 61 | Agent start group fix (a3): project seed (T17a's implementer) | opus · high | Agent start | 09:12 | 09:14 | `5170fb7`; the gate's sentence made true; existing projects keep the old one |
| 62 | the trigger eval, three live runs (claude -p, sonnet-4-6, 3 workers) | — | Agent start | 09:15 | 09:36 | run 1: 52/68 (439 s) — all 16 misses are neutral should-fire (recall 10/26), no false fire, project 11/11; runs 2 and 3 void (one query each gave no result in 120 s — load); two runs to repeat; runs 4–5 (2 workers): run 4 52/68 again, run 5 void — two whole runs agree, 14 of 16 misses the same |
| 63 | T17b fix round (b) (resumed) | opus · high | Agent start | 09:25 | 09:38 | 796 s; `f2af045` — (b) all eight, and CI run 2's: 8.3 short paths, Invoke-Upstream returned output+True as success (a real bug), the consistency script's FAIL recap |
| 64 | FINAL branch review, origin/main..0078659 | fable · high | the wave | 09:47 | 10:00 | 689 s, 262k tokens; NOT ready: 1 Critical (the Windows selftests claim unproven — continue-on-error hid 62 of 67 failing), 5 Important (Upgrading short; the Codex manifest's encoding 5.1↔7; the link's repoint wording; the level's spelling; the eval README), 4 Minor; the four groups hold end to end; a TCC must-know list |
| 65 | final fix: installers I2, M3, M1 (resumed) | opus · high | Installers | 10:00 | 10:06 | `7fe8a15` (the manifest read and written as UTF-8 one way) `d4250f3` (armed after a real change) `f7fbf1f` |
| 66 | Windows selftests to green, then the step required (resumed; may push and dispatch CI) | opus · high | Windows | 10:05 | ~10:20 | `4796d49`: bounded_run (a test's CRLF; the interrupt raised twice), contract (a test's CRLF), project_io.remove_tree for git's read-only files; handed back before its run ended — the controller read it and made the step required |

## Quality notes

- **A false green (T14, #165).** The implementer's report said every changed module's selftest passed; the task
  review ran rew_tool.py's selftest at 5104af8 and got exit 70, and the controller reproduced it at HEAD. Caught by the
  task review, before any group seat or CI.
- **A second regression made by a fix (T15, #166).** The task review's Minor «strip `-answer` too» was taken
  literally; the `-answer` file exists only when `<base>.md` is ANOTHER writer's review, so the two collapsed and a
  critique was dropped. The group seat caught it by probe.
- **A regression made by a fix (T2, #155).** The fix round of d23d73e recased the level's unit and gave one capture two
  keys; the re-review caught it; fixed in 306bd4c, verified live.
- **CI found a real defect no review had (#161).** `Invoke-Upstream` returned the child's printed output together with
  True — an array that counts as success whatever the child's exit code; found by the file:// child probe the test seat
  asked for, fixed in `f2af045`.
- **Repo-wide checks not run locally.** The implementers ran their modules' selftests, not `encoding-check` or ruff,
  which only the full runner runs; CI found three such defects. From then on every fixer runs both on its files.
- **Fixes that did not reach the end (T1, #153).** The first build stored the typed title correctly but the check
  still asked REW the list's spelling; the task review caught it; the group seats found three more behaviour gaps at
  the joins of #153/#154/#155.

## CI runs

| run | when | head | why | result |
|---|---|---|---|---|
| 38537781090 | 08:49 | `f991c10` | `workflow_dispatch` — the wave touches Windows (checks.yml's own rule) | red: installers-windows at the #161 probe (SQL Server's path; later steps skipped); selftests — encoding-check (side_effect, bounded_run: fixed `33b84cf`) and ruff (installer-consistency `import json`); installers-ubuntu, engine, gate green |
| 38542204702 | 09:25 | `99bddb2` | after the Installers' and SF3's group fixes | red, further on: installers-windows passed the #161 probe; its consistency step fails T17b's six ps1 Codex-link cases (8.3 short paths) and the file:// upstream-child probe; Ubuntu selftests — installers and tag-check (a Linux-only case; the runner's 12-line tail cut the FAIL line); installers-ubuntu, engine, gate green |
| 38543860362 | 09:38 | `f2af045` | after T17b's fix round | red, narrower: Windows passed its consistency step (the Codex-link and module-path cases green there) and failed the #162 RunAs probe (an elevated child's answer not yet written); Ubuntu — the ps1 Codex cases ran under the image's pwsh, where no junction exists (the hidden Linux-only failure); fixed by the controller `0078659` |
| 38544832522 | 09:46 | `0078659` | the two harness fixes | GREEN on all five jobs — but the Windows selftests step (continue-on-error) failed almost every module: the manifest checked out CRLF, `--selftest\r`; fixed `d3b3ec2` |
| 38545884702 | 09:55 | `d3b3ec2` | the CR fix | green on all five jobs; the Windows selftests step really ran: 61 of 67 pass — bounded_run (CRLF, the interrupt's tree kill), contract (a copy counted twice), and four temp-folder leaks (git's read-only files) fail |
| 38547555900 | ~10:15 | `4796d49` | the six Windows fixes (dispatched by their implementer) | red: installers-windows at its consistency step — the #160 Claude-step case's empty stand-in is not executable under MSYS; every later step skipped; fixed by the controller `580ba0d` |
| 38548157486 | ~10:15 | `80ac1c3` | the six Windows fixes + the MSYS stand-in | **GREEN on all five jobs; the Windows rew_tool selftests: all 67 checks passed** — continue-on-error removed next |
| 38549352727 | ~10:25 | `a5dd51d` | PR #174 | green on all five jobs (the release's test run) |
| 38558929626 | ~11:50 | `ac9faa3` | PR #175 (rc2) | attempt 1 red: installers-windows, the two-writers selftest starved (S-104's pool); attempt 2 (that job rerun) green on all five |
| 38561983012 | 12:11 | `71a56cf` | the release bookkeeping, push to main | green on all five jobs |

## Per group

| group | issues | plan | built | group seats: Important+ | fix rounds | red CI | merged |
|---|---|---|---|---|---|---|---|
| Captures | #153–#156 | PLAN-W-10 T1–T4 | `5f4a22c` `bf54719` · `bebab42` `b2eb99f` `74bbdfb` `d23d73e` `306bd4c` · `3a6eeb3` `a4dc01f` · group fix `1efad5c` `291dea7` `43a3d6a` `a6ed7cc` `df65abc` | task reviews 5 Important; seats 7 Important (3 behaviour) | 3 per task + 1 group | | 2026-10-14 ~10:35 |
| Windows | #158 | with Silent failures 3 | one implementer and one seat pair with SF3 — see that row | | | | 2026-10-14 ~10:35 |
| Installers | #157, #160–#164, #171, #172 | PLAN-W-10 T5–T9 | see Agent runs | task reviews 5 Important · seats 8 (silent-failure 3, tests 5) · CI found `Invoke-Upstream` counting output as success, which no review saw | 4 | 38537781090 (the #161 probe), 38543860362 (the RunAs probe), 38547555900 (the MSYS stand-in) | 2026-10-14 ~10:35 |
| Agent start | #149, #150, #170 | PLAN-W-10 T17a, T17b, #170 | see Agent runs | task reviews 2 Important (T17a) · seats 7 (silent-failure 4, tests 3) | 3 | 38542204702 (T17b's ps1 Codex-link cases, 8.3 short paths) | 2026-10-14 ~10:35 |
| Silent failures 3 | #159, #165–#167 (+ #158) | PLAN-W-10 T12–T16 | see Agent runs | task reviews 1 Critical (T14's selftest red where its implementer reported green) + 3 Important · seats 4 (silent-failure 1 — a regression the T15 fix made, tests 3) | 3 | 38545884702 (green, but the Windows selftests step failed 6 of 67; fixed in `4796d49`) | 2026-10-14 ~10:35 |
| Method text | #168, #173 | — (docs) | `4e03328` `0efbbe8` `8895f6a` · `f4ad845` `3046d55` | 5 Important (docs review) | 1 | | 2026-10-14 ~10:35 |
