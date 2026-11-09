# Acceptance act — skill W-12 · v3.3.0 release candidate

> The first acceptance run, at `44039bc`. The findings were fixed on the branch afterwards; the ledger says which.

Candidate: `wave-2026-10-30` at `44039bc90ea10b4402c3d822fab40e78e8a9ae93`, PR #211. CI at that head: gate, selftests, engine, installers-ubuntu, installers-windows all SUCCESS (one earlier red on the branch, `4e1b689`: `FAILED: 1 of 105 -- tag-check`, fixed by the head commit).
Fresh session, 2026-11-09. The tree was not changed (`git status` clean, HEAD as above, checked at the end). The real home was not written. Walk logs: `hub/scratch/skill/accept/logs/`; synthetic capture and scripts: `hub/scratch/skill/accept/work/`.
This act reports. It decides nothing.

## Verdicts

**ALARM — one critical finding, found only in acceptance (no review, selftest or CI had it).**

| area | verdict |
|---|---|
| **Joint tools: row → ledger (#210)** | **BROKEN on the documented path.** The mid-tweeter row's `delta` drops the woofers' EQ that the same row's table and `channels` carry; the banked version is not the row that was scored. Details below, A1. |
| Joint-by-joint runbook | Works to the second joint. At the third joint the runbook's own command gave **no rows** on the defaults; the way out is only in the tool's note, not in the runbook (A2). Two more places mislead (A3, A5). |
| Offer at the first step (#210 ask 1) | **In part.** Question, three choices, four languages, route line all work. The form shows no needs/gives, in any language (A4). |
| Version bench (#210) | Works: `table`, `loudness` (Zwicker through real `mosqito`, ISO 226 without it), `lr-phase`. `round-check` flags an exact sum at its default window (A6). |
| Capture: nine points, naming, rounds (#198, T15) | Works as written; small wording differences. |
| Versions ledger (#199, #197, #200, #201) | Works in the walk. The decoder halves of #197/#200 are not built, by the Arbiter's word. |
| TCC contract (#202, #203, #204) | Works in the walk; `capture-check`'s `rew` field against live REW not walked. |
| Installers (#205, #206) | #205's closing reason holds for the line break, weaker for Flash High. #206 built; not seen against a live TCC. |
| Texts (#196, #207, #208, #209) | Done, except #196's optional `docs-check` rule, not built. |
| Clean-HOME install | Dry run clean. A real run was not made (it reaches outside HOME); the candidate was placed the way the installer places it. |

## A. Findings from the walk

### A1. CRITICAL — the top row's delta loses the woofers' EQ

`references/phases/joint-by-joint.md` §7: "Every row of `joint-<name>.json` carries `delta` … The top joint's row carries the channels below it. Write it to a file".

Walk: bass row → woofer-mid `--align` (the runbook's command) → mid-tweeter row → `delta` → `propose --on HEAD`.

From `joint-midrange-tweeter.json`, row 1 (`logs/walk-14-eqloss.txt`):

```
w-L eq in channels: 4 eq in delta: 0
w-R eq in channels: 4 eq in delta: 0
```

The table the person reads says the opposite: "Every row above also takes … `w-L: gain -1.20 dB; HP BE36@90; LP BW42@238; EQ PK 265.12 Hz -6.0 dB Q 0.7, PK 557.67 Hz -6.0 dB Q 0.7, …`". The gain in the delta (−1.2 dB) already assumes those cuts. The settings sheet then has no EQ row for the woofers, in silence.

Effect, same row through `version_bench.py table`:

| version | sub↔woofer width | w-L↔m-L width | w-R↔m-R width |
|---|---|---|---|
| the row as the search scored it (`lower_joint`) | held | 1.29 / 1.83 oct | 1.69 / 1.86 oct |
| `delta` as written (v_002) | 0.89 / 0.92 | **0.00 / 0.77** | 0.39 / 0.67 |
| `delta` + the EQ from the row's own `channels` | 3.00 / 3.00 | 1.48 / 1.93 | 1.69 / 1.88 |

Cause: `joint_search.py:2935-2938`, `_undecided`: `return no_polarity, [code for code in channels if code not in ctx["eq"]]`. At the mid-tweeter joint the carried woofers are not in `ctx["eq"]`, so their held EQ counts as "not decided". Introduced by the last fix, `b92ab2f` (the function before it wrote `eq` whenever the row stated one), which answered Fable's "a delta that would wipe a ledger's EQ". The woofer-mid row's own delta is right (it holds `eq` for `w-L`). A path without `--align` has no EQ to lose.

Whether this also bites a 2-way's woofer-tweeter row was not run.

### A2. Hinders — the third joint comes back empty on the runbook's command

§5's mid-tweeter command, `--fixed <wm.json>@<N>`, on the synthetic car:

```
No variant came through the limits. Reasons, counted: leak limit (either side) 19964, no crossing in the window 42, not looked at, past the shortlist 3314, the joint below fell past its limit 390
```

The tool's note names the way: "a row searched without this low-pass reads a fall under any (run that joint with --front-lp, or raise --lower-drop)". Neither flag is in `joint-by-joint.md` (only in `rew-tool-docs.md`). I followed both: `--lower-drop 6.0` gives 176 rows ("woofer-midrange joint held 0.00/1.10 oct (was 1.25/1.81)"); woofer-mid re-run with `--front-lp LR 36 1600`, then the same mid-tweeter command on defaults, gives 48 rows, joint held 1.29/1.83. The ±30° band really moves under a mid low-pass, so this is expected of the search. What is missing is the sentence in the runbook, and a guess of the mid's LP before that joint is searched. Synthetic curves; on real ones not known. Also 3314 candidates stayed "not looked at" while the table is empty.

Related friction: the empty run writes a zero-row `joint-midrange-tweeter.json`, and the retry on the same `--out` prints its table and then refuses, exit 3: "the table above was not written: … already there, with the @N numbers recorded from it: give another --out, or --overwrite". There are no @N in an empty file. "Every row above also takes" is printed with no rows above.

### A3. Misleads — a row marked `REFUSE` banks without a word

Bass table, woofer Fs 52 Hz: row #8, `HP BW36@40`, column `Fs` = `REFUSE`. It has a `delta`, and `propose` banked it (`v_003`, sheet row `w-L | HP | OFF → 40 BW 36`) with no Fs advisory. The runbook, head and §6: "Only two things are hard: … driver safety (the Fs floors)", "A hard limit (Fs floors, …) has no flag to loosen". `rew-tool-docs.md` is narrower: "the hard Fs floor (1.1 × Fs on a mid's or a tweeter's high-pass)", and `xover_wishes.FRAGILE_ROLES` leaves woofers out. Two documents disagree, and the word `REFUSE` in a table of offers says something the tool does not do.

### A4. In part — the offer shows no needs and no gives on the form

Rendered with `intake_form.model`/`render`, all four languages: question and three labels, nothing else ("How should the desk work be done — joint by joint, with the Resonalyze engine, or both? Joint by joint (search and compare) Resonalyze engine Both, then pick the best"). The text with needs, gives and "one car" is only in the field's `note` (`intake.py fields --json`, English) and `project-intake.md` §4, which a session reads. `intake_form._field_html` prints no note for this field. A person on the form or in TCC, whose first step is that same page (plan T16), chooses blind unless the session says it.

### A5. Small mismatches in the words

- The sheet: "The exact phrase is the one `joint_search.py --single-point` asks for", giving `ellipsoid positions: nine points skipped; …`. The refusal prints `nine points skipped; the joints run on one point`. Both pass (the check is `SINGLE_POINT_SKIP_WORDS = "nine points skipped"`). But the refusal's phrase holds neither "ellipsoid" nor "position", so `process._positions_asked` (the flaw-map gate) would not count it unless the person's answer does. Not run through the flaw-map gate.
- Sheet block B has the RTA first, then the points; the round prints points, then RTA, with `<- switch: hand-held → RTA` inside what the sheet calls one hand-held block.
- `--plan` needs the 63 point titles typed on one line, as the sheet says; no helper builds them.
- `intake.py set … goal.desk_approach by_ear` ends in a traceback (`IntakeError` not caught), for any enum field; the form cannot send it.

### A6. Hinders — `round-check` flags an exact sum at its default window

Sums built by adding the solos' impulses (`work/w15_sums.py`): `ALL` at the default window, `rms 1.79, max 7.10  FLAG`; with `--whole-record`, `0.00 0.00`. `L` and `R` read 0.06 / 0.01. A planted 1 dB error on `Ws` reads 0.50 and is not flagged. So on this set the window alone produced the flag on the widest sum. One synthetic case; cause not traced further; not replayed on real curves.

### A7. Seen, not new

REW is running on this machine with the Passat's file. `contract.py check` read its list (read-only) and reported `round cap_001: 79 of 80 captured (REW, read now)` for a temp project with one capture recorded, beside its warning that "another build's data cannot be told apart". `attest v_001` on a version with nothing proposed banked `v_002`, "applied nothing proposed" (hit by my own script; origin not checked).

## B. Each issue's asks

Strict: an ask met in part is "no", with what is missing. Quotes are from the candidate or from walk output.

### #196 EMMA reference
| ask | state | evidence |
|---|---|---|
| The reference resolves to `EMMA/positions` (2026 tr.2–6) | done | `project-intake.md:151`: "EMMA positions: its `EMMA/positions` row, EMMA 2026 tr"; no `emma-2024` left in `references/` |
| A track from a profile is matched with its year; no year or a contradiction is said | done | `test-tracks.md:25`: "first matched to a row below **with its year**; a profile that gives no year, or contradicts the row, is pointed out to the user" |
| Optional: `docs-check` resolves track references | **no** | `git diff v3.2.0 HEAD -- scripts/docs-check.py` is empty. Marked optional in the issue and plan |

### #197 input gain
| ask | state | evidence |
|---|---|---|
| Optional `input_gain_db`, missing = 0, no migration | done | `schema.md:167-174`; v_001 with none reads "0 dB → -0.3 dB" |
| Not asked, not required, not printed at 0 | done | absent from `intake.py fields`; v_001's sheet has no such row |
| A change is an ordinary row, no reviewer | done | `v_006` 🟡 proposed: "Preset \| Input gain \| 0 dB → -0.3 dB" with no reviewer |
| Loudness between versions includes it | done | −3 dB trim: "v_003 -3.00 dB … its input takes +3.00 dB"; "the preset's input gain -3 dB is in these chains, once" |
| `attest` compares with the decoded file | **no** | no decoder in this wave (plan T2, the Arbiter 2026-11-08); the issue says "once the decoder reads the input gain" |

### #198 points group
| ask | state | evidence |
|---|---|---|
| Third kind, label `Points (sw)`, order solo → group → points → rta | done | round output: "Solo (sw) … Points (sw) … Solo (rta)" |
| Tripod → hand-held counted and written in the plan | done | `docs/plans/_1-capture.md`: "Points (sw)   <- switch: tripod → hand-held" |
| TCC shows the column | not checked | TCC's side; said on hub #331 |

### #199 propose after a candidate
| ask | state | evidence |
|---|---|---|
| Refuse | done | "error: the newest version v_002 is a candidate not in the slot; this delta would land on HEAD v_001 — pass --on v_002 to build on the candidate, or --on HEAD", exit 1 |
| `on=<version>` / HEAD | done | `--on v_002` and `--on HEAD` both walked |
| Candidate + fix, reviewed, banks as a placed proposal | done | `propose {} --on v_002 --evidence … --reviewed review.md` → "🟡 proposed v_004"; `attest` → 🟢 |
| Sheet names the base | done | "v_004 = v_002 + this change. Old → New is against v_001, the last version placed in the slot" |

### #200 preset settings tier
| ask | state | evidence |
|---|---|---|
| Tier (input, sources, fx, rtc, conductor, bt), missing = defaults | done | `schema.md:173`; v_009 `{"fx":{"realcenter":true},"input_gain_db":-0.3,…}` |
| Never asked at defaults | done | no intake field; no row at default |
| Legacy «FX» reads as RealCenter; DynBass/SubX have no alias, unknown | done | `naming-and-structure.md:94`; sheet: "Preset \| Dynamic Bass \| unknown → on" |
| Diff, sheet, propose treat them as fields, no reviewer | done | `state.py diff`: "Preset-level: Input gain … RealCenter: off → on" |
| `attest` from a decoded `.pct6` fills and checks | **no** | no decoder in this wave (plan T2); fields are by hand, the check is the screen |
| The source file on the tier | done | `attest --source-file` → v_009 `source_file` with name, path, md5, saved, pctool, device, read_at, compared |
| Loudness includes `input_gain_db` | done | as #197 |
| The TCC issue filed | done | hub #324 (`ayukhno`); shape posted 2026-11-08 |
| TCC tab and section | not checked | TCC's W-12 |

### #201 in the DSP now
| ask | state | evidence |
|---|---|---|
| Decide and name the field | done | `slots[slot].loaded = {version, since, source}`: `attest` writes `"source": "attest"`; `state.py loaded SQ v_007 --source …` → "v_007 in the DSP … HEAD is v_009"; posted on hub #325 |
| Say what HEAD means with proposals after the applied one | done | `schema.md:219`: "HEAD is the pointer; `loaded` is a dated claim; neither is a mirror" |

### #202 a step's note
| ask | state | evidence |
|---|---|---|
| `add_step` takes `{do, expect, if_not}`, kept in state and journal | done | `note` in `process-state.json`; journal `step_added` with it |
| Closing keeps the answer beside `expect` | done | `done … --heard` → `"answer": "voice a bit left, fine"` |
| `session-close` lists steps with `expect` and no answer | done | "NO ANSWER 0.M listen: no answer yet / expected: bass even" |

### #203 four guarantees
| ask | state | evidence |
|---|---|---|
| `--round` refused under the lock | done for `capture-taken`, `capture-protective`, walked; `capture-check` by flag table only | "error: round cap_999 was closed or replaced after it was read (cap_001 is the open round now) -- nothing was written" |
| REW-error lines pinned | done | `CONTRACT.md:33`: "`error: REW answered with an error: <REW's words> -- nothing was written`", "`error: REW's measurement list was not read (<why>) -- nothing was recorded`" |
| Verdict says REW answered an error | done in code; not walked live | `verify.py:135,240,301`; `process.py:3453,3619` carry it into checks and the event |
| §3 out of «planned»; `rew_state` in `IMPORTABLE` | done | `CONTRACT.md:119`: "guaranteed (W-12, #203)"; `contract.py:128` |

### #204 save and status
| ask | state | evidence |
|---|---|---|
| `save`: commit tuning files, push, refuse with a reason; `--dry-run` | done | bare remote: "✓ sent to origin: commit 05d48e3 (8 files) and 1 waiting commit"; "✗ no remote: …"; "✗ nothing to send: …"; "✗ pull first: the remote has 1 commit this copy does not. Nothing changed", exit 1; dry run changed nothing |
| `status --json` splits files, lists ahead and the remote head | done | `"changes":{"tuning":[…],"housekeeping":[".sessions.log"]}`, `"remote_head":{hash,time}`. `ahead` non-empty not seen in the walk (selftest only) |
| Who sends | done | `"sends": "session"` on a project `init` seeded |
| The skill link never goes | done | link present in the folder; `git ls-tree` of the remote has none; `.critic-env` stayed out too |

### #205 closed with no code
| ask | state | evidence |
|---|---|---|
| Re-check Flash High; if it hangs, name the guides' tier | **reason holds for one-line probes only** | ledger: "4 of 4 answered, 3.0–7.6 s … A large prompt on High is not tested". Installer and FAQ text unchanged, `install.sh:2485`. S-109's complaint was a one-line hang, so a one-line probe does answer it. The installer still names Flash (High) while the ADC guide names Medium; that is the issue's "if it still hangs" branch, not taken. Probes not repeated |
| Relayed output ends with a line break | **no; the reason holds** | `install.ps1:452`: `function Step { param($m) Write-Host ""; Write-Host "==> $m" …}`. The empty `Write-Host` ends a line left open, so the recorded cause cannot join two `==>` lines. Whether the symptom was on screen is unknown (the Arbiter: «не витрачаємо») |

### #206 a running TCC
| ask | state | evidence |
|---|---|---|
| Stop it or tell the user | done, by telling; not seen with a live TCC | `install.sh:1920-1927`: "Autosound TCC is running. Close it and run this line again; the app was left as it is."; the method is updated before this point |
| If again: the log tail before `pkill` | **no** | the warning goes straight to `pkill -f bin/autosound-tcc`; nothing asks for the log tail |

### #207 READMEs
| ask | state | evidence |
|---|---|---|
| «3.x» in all four | done | README.md:16 "Version 3.x, with a graphical interface, is the current release."; uk, de, pl alike |

### #208 ringing and THD
| ask | state | evidence |
|---|---|---|
| Board's words, with a `find` check in the selftest | done | `find` for THD, harmonics, ringing, дзвін, затухання, decay lands right; waterfall/CSD/RT60: "not read by any tool: open the view in REW's own window"; coherence: "not read"; selftest asserts added |
| A row for the single-measurement report | done | `find "single measurement report"` → `rew_tool.py` with no arguments |
| SKILL.md's row and the playbook's ringing row | done | SKILL.md Map: "…distortion (THD), excess phase, impedance, RTA, ringing."; `analysis-playbook.md:12` names `ear_suspects.py` and the diagnostics page |

### #209 agy announcement
| ask | state | evidence |
|---|---|---|
| `probe_wait()` in the f-string | done | `autosound_ai.py:6247`: "(до {probe_wait()} с)" |

### #210 joint by joint
| ask | state | evidence |
|---|---|---|
| Offered at the first step, by name | done | `goal.desk_approach`, three values, `when: now`, no default; a bad value refused |
| With what it needs and gives | **no** | not on the form (A4); in the field's note and `project-intake.md` §4 only |
| A runbook: order, align-then-cross, space and metric per joint, conditions, tournament, blend | **no: written, but §5 does not carry a person past the third joint and §7's "carries the channels below it" is not true of the EQ** | `phases/joint-by-joint.md`; A1, A2 |
| Sub↔woofer search | done | walked: 28,900 pairs, 14 s, 152 MB |
| Woofer↔mid with flatten-first and decay | done | walked: 45,495 pairs, 200 s, 353 MB; "Decay (reported, not ranked)", "Aligned first" |
| Mid↔tweeter on the nine-point power sum | done | walked: 11 s, 187 MB; ear groups "from the fixed order of the points, checked against the arrivals" |
| Stage conditions as options | done | L−R offset held at +1.57 / +1.37 / +1.15 ms, flags in `--help`; the same-polarity and same-family rows in every table. Off-flags not walked |
| L-vs-R phase | done | `lr-phase`: acoustic centre, nine, electrical |
| Loudness match | done | Zwicker via real `mosqito`; with it blocked: install line and ISO 226 "less exact when the versions differ in the bass" |
| Round-level check | **no** | runs, but flags an exact sum at the default window (A6) |
| The offer's route | done | all nine mode × approach combinations of `handoff` as designed, e.g. "The route: the joints by `references/phases/joint-by-joint.md` at the desk (goal.desk_approach joint_by_joint)." |
| A row reaches the ledger | **no** | A1 |
| Lessons from the ear | done | §11, all three |

## C. Install and the walk

**Dry run:** `HOME=<clean> ./install.sh --terminal --dry-run`, exit 0, 78 lines, nothing outside the clean HOME written (only Apple Python's own cache inside it). It offers `v3.2.0`, the latest tag; `--skill-ref 44039bc` says "is not a release: it is installed UNSIGNED, unchecked". `INSTALLER_VERSION="3.3.0"`, `$InstallerVersion = "3.3.0"`, `plugin.json` 3.3.0.

**Not run for real, because it reaches outside that HOME:** `upkeep.py tools --only claude --only omp --only agy --only gh` works on the tools found on PATH (the real `~/.local/bin/agy`, Homebrew's `gh`), and the sign-ins open a browser. Instead: the candidate cloned to `~/.claude/skills/.autosound-tuning-src`, links `~/.claude/skills/autosound-tuning` and `~/.agents/skills/autosound-tuning`, as the installer makes them. `pip --user` and the engine fetch were not exercised; numpy 2.0.2, scipy 1.13.1 and `mosqito` came from `scratch/skill/venv-mosqito` (Python 3.9.6, the same as the Mac's stock one). The machine's own python3 has no numpy.

**Walked, in a temp project, synthetic impulses (3-way + centre + sub, geometry-derived arrivals, protective filters in the recording):** phase −1 and intake through `intake.py` / `project.py`; `project_repo.py init` (seeds `CLAUDE.md`, `AGENTS.md`, `.gitignore`; `project_seed.py` itself needs a source project and was only read); `setup_import.py --write` as v0; `handoff`; `naming.py`; `capture-start --plan` with 63 point titles; the three joints up the stack with `--fixed`; refusals (no points, `--single-point` with and without its record, an answer opening with "no"); `propose --on HEAD`, candidate, earned, `attest`; `version_bench` table, loudness, lr-phase, round-check; `save` against a bare remote, with refusals.

## D. Who found what

From `docs/W-12-LEDGER.md` and this act. B / I / M = blocker / important / minor as the seat counted them.

| stage | what was found | critical | fate |
|---|---|---|---|
| Plan review, Codex | whole plan 12, #210's design 14 | structural promotion through `--on` | taken in |
| Side by side, Gemini 4 / Opus seat, T2 T3 T6 T7 | 12 (9 real) / 19 (19 real) | a failed push after the commit, a network call in `status`, an older copy refusing the key (Opus only) | fixed |
| Installers, Opus seat | 1 / 0 / 3 | a test red on both non-Mac CI jobs | fixed |
| Versions, Opus seat | 2 / 4 / 4 | an unreviewed structural change reaching HEAD through `--on` | fixed |
| Its narrow check | 0 / 3 / 2 | a candidate promoted by `variant switch` | fixed |
| TCC contract, Opus seat | 0 / 3 / 3 | `save` committing after a failed step; a key file reaching the remote | fixed |
| `joint_search` slices 1–3, Opus seat | 2/7/8, 1/11/7, 1/6/6 | two subs modelled differently; a `--fixed` row rewriting the sub; a printed row number not the one `--fixed` reads | fixed |
| `version_bench`, Opus seat | 2 / 6 / 8 | a pick from no curves; a channel left out in silence | fixed |
| Branch, final Opus seat | 0 / 5 / 5 | no step from a chosen row to a ledger version | fixed |
| Fable on the last fixes | 0 / 1 / 2 | a delta wiping a ledger's EQ and flipping an undecided polarity | fixed, and **the fix introduced A1** |
| Replays on real curves, session | 4 | the claim on C, the leak limit, an Fs floor above the reference tune's mid HP, an empty default table | fixed or corrected in the text |
| CI on the head, branch | 1 red, `tag-check` | none | fixed by `44039bc` |
| **Acceptance** | **A1: the top row's delta drops the woofers' EQ** | **yes, and found by no earlier stage** | open |
| Acceptance | A2 third joint empty on the runbook's command; A3 `REFUSE` row banks; A4 form without needs/gives; A6 `round-check` false flag | no | open |
| Acceptance | A5 wording; #196's optional rule; #206's log tail | no | open |
| Backlog in the ledger | `save` and a file `git rm --cached` by hand; a partial re-read's sheet ending in `attest` | no | named, not taken |

The ledger's own trial tables (per group: runs, wall clock, commits; CI by workflow; the estimate) are not in `docs/W-12-LEDGER.md` at this head. "Who found what" is filled here only.

## E. Not checked

- Real REW and a real car; a real capture; the Passat replay on this head.
- A real install: `pip --user`, the engine fetch, `upkeep`, sign-ins, the desktop app, Windows, `pwsh`. The `os.name` gates stayed on.
- A live TCC during an update (#206); TCC's column, tab and picture (#198, #200, hub #331).
- Flash High under ADC: the ledger's probes were not repeated.
- `capture-check` and the `rew` field against a REW error; `capture-check --round` live.
- A push to GitHub (`save` used a local bare remote).
- `--move` (the blend, §9), `--single-point` above the bass, the stage conditions' off-flags, a 2-way, a front sub, a DSP other than the Helix, `goal.desk_approach: both` with the real engine.
- `project_seed.py` as a run (read only), and the flaw-map gate against the refusal's phrase (A5).
- The whole test suite, by instruction. Reviews and CI were read, not repeated.
