# W-10 candidates — outside the audit, and what earlier waves left

**Status:** a ranking for the Arbiter's review, 2026-10-14, on his word «вибери всі задачі 1) які поза аудитом, 2) які
залишились з попередніх хвиль. прорангуй і оціни». W-10 is collecting; nothing here is built, and no milestone is open.
Every item was checked unfixed at `dcb77da`.

Sources: the bus queue `to:skill` (hub #247 #258 #259 #261 #269 #274 #278, deferred #113), this repo's issues (#149
#150, deferred #26), `docs/TODO.md` (S-103 the W-9 pool, S-101 the W-8 pool, S-099, S-098, the older deferred items).

**The order.** 1) what breaks work in the car now; 2) small and unblocking; 3) found in real use on 13.10; 4) the
installers; 5) edges and silent failures; 6) new text and features; 7) research. The four lines follow `WAVES.md` §1
step 2; `Risk: high` is data writes, locks, signatures, installers and the method/TCC seam, and it sets the process
weight (`hub:seam`). Complexity: XS < 1 h · S ~1–2 h · M ~half a day · L a day or more.

## To build — ranked

| # | item | source | class | risk | complexity | model | group |
|---|---|---|---|---|---|---|---|
| 1 | A round matches titles as raw strings: `w-R_01` taken, `w-R_1` still «outstanding» — the agent asks for a capture already taken | hub #269 TCC-054 | defect | high (round state, TCC's cards) | S | opus | Captures |
| 2 | `capture-check` judges a sub sweep over 20–20000 Hz and calls it truncated: a correct capture reads red in the gate and in TCC | hub #247 TCC-049 | defect | high (gate verdict at the seam) | M | opus | Captures |
| 3 | A level before the method (`sw_3 86dB (sw)`) is refused; the Arbiter ruled 06.10: read both, write after | hub #261 TCC-053 | defect | high (naming grammar, TCC reads it) | S | opus | Captures |
| 4 | A series with a letter (`sw_E3`, `ALL+C+FX_A3`) is all «not in the grammar» — the method's own call which form | hub #259 TCC-052 | defect | high (naming grammar) | M | opus | Captures |
| 5 | Ubuntu install ends «NOT ready: Claude Code»: Claude's installer piped to `sh` (dash) — one word, `bash` | S-103 | defect | high (installer) | XS | opus | Installers |
| 6 | Three selftests fail on Windows (`\\?\` prefix, a doubled-backslash repr), and the Windows CI job runs only a few — then the gate asks for it by name | hub #274 TCC-055 + #278 ask 1 | defect + infra | ordinary | S | opus | Windows |
| 7 | Codex does not see the skill at project start (no `AGENTS.md`/`.agents/skills`) nor TCC's MCP | #149 (Passat session 13.10) | feature | high if it writes into the project | M | opus | Agent start |
| 8 | A short capability map near the top of SKILL.md; the feedback route easy to miss. SKILL.md has 10 bytes left — cut first | #150 (13.10) + S-103 | docs | ordinary | M | opus | Agent start |
| 9 | `AUTOSOUND_PROJECT_DIR` set, `PROJECT_MIRROR` unset: the mirror is `$PWD/rew_analitic` — another car's context can be read | S-103 | defect | high (data) | S | opus | Silent failures 3 |
| 10 | A stop before anything changed (a declined consent too) replaces the last real install's receipt | S-103 | defect | high (installer) | S | opus | Installers |
| 11 | `install.ps1` run as PowerShell 5.1 under pwsh 7 inherits its `PSModulePath`: `Get-FileHash`, `Expand-Archive` can fail | S-103 | defect | high (installer) | S–M | opus | Installers |
| 12 | `install.cmd` started from PowerShell reads as double-clicked: «Finished with exit code N» and a `pause` | S-103 | defect | high (installer) | S | opus | Installers |
| 13 | The installers' help shows a one-liner pinned to v3.0.46 (`install.sh`) or `main` (`install.ps1`) | S-099 | defect | ordinary (help text) | XS | sonnet (trial) | Installers |
| 14 | `--skill-ref <branch>` says «UNSIGNED» twice; the dry-run placeholders need the "would …" wording | S-103 | defect | high (installer) | S | opus | Installers |
| 15 | `predict --rew --project` with REW down ends in a traceback; lenient `for_project` raises on inner shapes; no exit 70 | S-103 | defect | ordinary (TCC reads it) | S | opus | Silent failures 3 |
| 16 | Under TCC the clipboard route can record one review round twice | S-103 | defect | high (seam) | S | opus | Silent failures 3 |
| 17 | On Windows `subprocess.run(timeout=…)` waits without bound when `gh`'s grandchild holds the pipe | S-103 | defect | ordinary | M | opus | Silent failures 3 |
| 18 | Remote Control: start on the computer, tune from the phone — how the method plans for its time limits | hub #258 HUB-084 | feature (text) | ordinary | M | opus | Method text |
| 19 | «Learn to listen»: a `learn` route on streaming tracks, AYA tracks marked adapted/basic, the phone plan page as a mechanism | hub #113 PAS-005 | feature | ordinary | L | opus + the Advisor | Method text |
| 20 | The trigger eval cannot measure the TCC bug-report queries (0/3) nor resume inside a project | S-103 | infra | ordinary | M | opus | Agent start |
| 21 | Stable picks keep `beta-…` out by glob alone; a `^v` filter makes it explicit | S-103 | infra | high (installer) | XS | sonnet (trial) | Installers |
| 22 | `json_str` (install.sh) passes invalid UTF-8 through when there is no python3 | S-103 | defect | high (installer) | S | opus | Installers |
| 23 | A boost path for `eq_propose` (`--allow-boost` changes nothing today) | S-101 | research | — | L | research first | — |

**Groups** (one theme, one review per group, `hub:seam`): **Captures** 1–4 — all `Risk: high`, the full loop; **Windows**
6; **Installers** 5, 10–14, 21, 22 — all `Risk: high`; **Agent start** 7, 8, 20; **Silent failures 3** 9, 15–17;
**Method text** 18, 19.

**Advice for the cut:** Captures + Windows + item 5 + Agent start's 7 and 8 — what the car and TCC hit now, about
8–10 h of machine time; Installers and Silent failures 3 next wave, unless the Arbiter wants them now; 18–23 after.

## Not to build — waiting for a run or not due

- **S-017** existing-tune analysis: built in v3.0.65, waits for the Arbiter's walk on the Passat after AYA 17.10.
- **S-021** Phase 1's variants end to end on a fresh system: waits for a run.
- **S-055** the min-phase verdict on real data: waits for the next ellipsoid round in the car.
- **S-059** TCC's upgrade path, third case on the VM: waits for the Arbiter's test.
- **S-001** a declared pin vs a split: returns with the first `frozen` run.
- **#26** workflow orchestration: a 3.2.x candidate.
- **hub #278** asks 2 and 3: process, recorded in S-103; nothing to build.

## Left out as audit

The audit closed at its minimum (`docs/AUDIT-2026-10-CLOSE.md`, both items TCC's). Its closed items come back only as
findings from use: J1b, J1c, J3b, J4b (a per-call REW deadline, kept as a small pool task), J5, J6b–J6d, S3, S4b, S5,
J7's rest — including S-103's README/FAQ «two visits» line (P1). S-100 stays the audit's record.
