# The October 2026 audit volume — the skill's plan

Hub #252 (HUB-080), 2026-10-04. Supersedes the "record in the pool" route of #250. **A plan, not a build**: no code
changed for it, no milestone issue opened, the W-8 pool not rewritten. Nothing here is built before the Arbiter's
`ok` on the task, at its wave's milestone (hub `WAVES.md` §1). **Updated for hub #254 (HUB-082):** the rows settled
with TCC's plan (tcc `c8e9e3d`, hub `docs/AUDIT-PLANS-MATCH-2026-10.md` §2) are answered in §8 and carried into §3–§7.

**The volume** (hub `docs/AUDIT-INDEX-2026-10.md`): S1 the instructions (branch `claude/relaxed-ritchie-pk2nci`,
`docs/AUDIT-INSTRUCTIONS-2026-10-04.md`, I-1…I-31), S2 the tooling (branch `claude/charming-faraday-dcn0ez`,
`docs/AUDIT-TOOLING-2026-10-04.md`, T-1…T-50, K-1…K-6, §7), S3 the user's path (private — cited here by
its IDs only, P1…P11), and TCC's two (TA the GUI, TB the whole app). The skill owns S1, S2 and S3's text proposals
(P1, P3, P4, P6, P9, P10), and defines the contract (J1), the lock (J2) and the refusals (J3) that TCC plans against.

**Base.** S1, S2 and S3 read the skill at `7b3232b`, which is still `main` today
(`git rev-list --count 7b3232b..origin/main` → 0). So no finding can be "fixed since": every verdict below is
*holds*, *partly* or *wrong*, read at the code as it stands.

**How it was made** (the Arbiter: «хочу задіяти агентів в аналізі і складанні плана»): four read-only verification
agents (sonnet), one per area; the grouping by this session; for each M/L group, two or three architecture agents
(opus) with different focuses — the smallest change, clean architecture, balance; a test-gap read of the modules the
groups touch; and a coverage read of this file against the finding list. The agents' notes stay outside the tree.

---

## 1. Questions only the Arbiter can answer

Each with the advice first. None of them stops the first wave's safe groups (§5); each stops the group named.

1. ~~How the method's modules find each other~~ — **not a question any more**: it is technical, and TCC's need
   (§8 M4) settles it. Decided: the sibling loader `rew_tool/siblings.py` (not a package). Every documented
   `python3 rew_tool/x.py` line keeps working and TCC's copies join without a TCC release.
2. **Which Python runs the method on macOS and Linux (T-34).** In every case J6a (W-9) makes an install that
   cannot import numpy say "not ready" (exit 3) instead of "Installed". Then: (a) uv's Python 3.12 becomes the
   `python3` in `~/.local/bin`, as Windows already does (`install.ps1:876-885`, `:1215`); (b) keep whatever `python3`
   is on PATH and print a remedy; (c) a venv owned by the method plus a wrapper. **Advice: (a).** `~/.local/bin` is the
   only folder that comes first on all three PATHs that matter today — the installer's, TCC's launcher's, the session
   shell's — so the three stop picking different interpreters; stock Macs leave the Python 3.9 library set that CI
   never tests. Cost: it takes over `python3` in the person's own shells (said on screen; the uninstaller removes it).
   The ban on `--break-system-packages` (`commands/setup.md:54-55`, `install-tcc.md:59-60`) stays, worded "on a
   system Python": uv's own Python is not one.
3. **Centre and rear: Phase 2d or Phase 5 (I-10).** **Advice:** level and arrival in 2d, as part of the technical
   base; voicing and envelopment in 5. The other file points to the one home.
4. **Phase 3's two verdicts when the reviewer runs solo (I-9).** **Advice:** "two independent verdicts —
   cross-vendor in mode A; in B and C the ladder's best reachable rung, named in the lock's record".
5. **Light touch (I-8)** has no route the gates allow. **Advice:** five lines in virtual-first's "Two ways in": the
   phase it enters, a recorded `decision` that waives the flaw map, the one capture it needs. No gate change.
6. **The car walk (S3's own advice).** P2 (one sheet per visit), P5 (the two loop modes), P7 (a state check first)
   and P8 (a return list) change what you hold in the car, and P1 asks where the desk's scene A/B goes. **Advice:**
   walk them once on the next car visit before anything is written; the scene A/B moves to Phase 3. The one-path
   move (group S3) waits for the same walk, because it rewrites the same phase files.
7. **A live pass at REW before J4a is tagged** (~15 minutes on a real REW setup): a −3 dB PK through `set_filters` read back,
   the `gain` trap, REW quit → `capture-check` exits 69, the payloads saved as test goldens. **Advice:** at the next
   collection session; until then J4a's read-back tolerances are guesses.

---

## 2. Verification

Counts: **S2** 56 findings (T-1…T-50, K-1…K-6) — 52 hold, 4 partly, 0 wrong. **S1** 31 (I-1…I-31) — 27 hold,
4 partly, 0 wrong. **S3** (skill-side facts of the six text proposals) — 5 hold, 1 partly. **S2 §2** (the
2026-09-09 review's open rows) — all hold except F2 and G1 (partly) and F12 (not recounted). A finding that "holds"
holds at the lines the report cites; corrections are listed where the line, the size or the proposal was wrong.

### 2.1 S2 — the tooling

| ID | verdict | correction at `7b3232b`, or what the report missed |
|---|---|---|
| K-1 | holds | TCC's `write_rew_filters` will read back too (TB-F4): one side reads back, not both. A key whitelist must be checked against TCC's payload first. |
| K-2 | holds | **M, not S.** `Process.load()` has ~12 read-only callers outside `process.py` (`flaw_map.py:244,445`, `predict.py:2220`, `eq_propose.py:1042`, `rew_tool.py:1874`, `project_seed.py:343`, `resonalyze_ir.py:664`, `naming.py:1083`, `ear_suspects.py:189`, `verify_prediction.py:794`, `project.py:1571`, `contract.py:188,1378`): strict reading is opt-in, strict for writers and `contract`, decided per reader. |
| K-3 | holds | — (the cure is T-18) |
| K-4 | holds | The preview must also skip `Project.save` (`project_seed.py:485`) and `.gitignore` (`:491`). `project_seed.describe()` (`:172`, `--describe`) is already a no-write preview. |
| K-5 | holds | Call sites are `side_effect.py:188, 267, 270, 382, 477, 530, 608`. |
| K-6 | holds | `contract.py:69-80` already holds a `CONTRACT` table printed by `contract.py table`: extend it. |
| T-1 | holds | `capture-close` re-runs `check_captures` on taken titles (`process.py:4023-4029`): the fix covers that path too. |
| T-2 | holds | **M-L.** Callers that read any failure as "missing" or "unreachable": `verify.py:75,108,154,173,263`, `contract.py:400`, `timebase.py:374`, `process.py:4015,4028`, `rew_tool.py:1226,1233,1238,1247,1827,1902,1910,1934`, `predict.py:2175`, `bind.py:89`, `ear_suspects.py:268`, `level_offsets.py:295`; `URLError` is uncaught at `flaw_map.py:233`, `eq_propose.py:922`. |
| T-3 | holds | **12+ sites, not ~6:** `eq_propose.py:922,925,935,1035,1058`, `rew_tool.py:734,1061,1478,1929`, `predict.py:2186`, `flaw_map.py:233,284`, `verify.py:80`. |
| T-4 | holds | RTAs already return early (`verify.py:97-104`); REW's "no impulse response" (404, `rew_stub.py:171-172`) is the one answer to let through. |
| T-5 | holds | — |
| T-6 | partly | The proposal is wrong as written: `ProxyHandler({})` for every host breaks a REW on another machine, which `rew_api.py:11` supports. Bypass the proxy for loopback only. |
| T-7 | partly | Overstated: `rew_api`'s selftest restores `urlopen` in a `finally`. Missed: `resonalyze_ir.py:641` and `rew_stub.py:258,304,316` also assign `BASE_URL`; `flaw_map.py:437-452` saves and restores it — the pattern to copy. |
| T-8 | partly | The writer list is incomplete: `autosound_ai.py:479` (`_dpapi_write`) and `:2296` (`_write_private`) use the same fixed temp name; plain writes at `state.py:1137`, `setup_import.py:285,299,310,338`, `project_seed.py:306,321`, `intake_form.py:1851`, `path_check.py:409,438,442,602`. |
| T-9 | holds | — |
| T-10 | holds | Gating on `complete` pulls in everything `check_project` marks incomplete: the parity test is required, not optional. |
| T-11 | holds | `seal_all` (`state.py:747-755`) reads the same way: three call sites. |
| T-12 | holds | 53 `.save(` calls in 9 files: `expected_rev` opt-in, or the change is M. |
| T-13 | holds | `load_draft` uses `break`, so a corrupt draft also skips the good `dsp_profile.json` it would start from. |
| T-14 | holds | — |
| T-15 | holds | Four unrelated sites sharing one rule. |
| T-16 | holds | — |
| T-17 | holds | — |
| T-18 | holds | **M-L.** The lock covers every `Process` verb, `Project.save`, `PresetHistory.snapshot`, seals/slots, `dsp_profile` — and must **not** be held across the 5 s REW call in `check_captures` (a revision check at write time instead). |
| T-19 | holds | **M-L:** ~38 sibling imports across the importable modules; **six** of TCC's modules edit `sys.path` at import (`verify.py:33` too); function-level inserts put bare `state`/`process` on the path (`project.py:1389,1568`, `eq_export.py:585`, `project_seed.py:340`, `naming.py:1081`, `flaw_map.py:242`, `contract.py:92`); six private loaders exist (`process.py:416,448,516,549`, `state.py:256`, `dsp_profile.py:348`). |
| T-20 | holds | Add an explicit rate; do not turn the returned note into a raise silently. |
| T-21 | holds | Interacts with K-2: whether `Process.load()` validates. |
| T-22 | holds | — |
| T-23 | holds | 0/1/2 keep their meaning; only an "unexpected error" code and a "REW unavailable" code are new. |
| T-24 | holds | Also `side_effect.py:262,525` print. Precedence differs between tools: `state.py` lets `--root` win over the environment (`:2621`), `process.py` lets the environment win (`:564-566`) — written down, not flipped without TCC. |
| T-25 | holds | The writer line is `eq_export.py:221-223`; the Generic/Extended path already checks values (`:534-535`). |
| T-26 | holds | `process.py`'s selftest drives some verbs (`:2958`, `:2977`, `:3059`, `:3304`, `:3218`, `:3537`). A smoke over ~100 verbs with golden key sets is M-L. |
| T-27 | holds | (mechanism read; not re-run) |
| T-28 | holds | — |
| T-29 | holds | Recording real payloads needs a live REW once. |
| T-30 | holds | — |
| T-31 | holds | `i18n-check.py:110-115` (not `:112`). |
| T-32 | holds | `capabilities.py:178-183`. |
| T-33 | holds | (mechanism read; not re-run) |
| T-34 | holds | **L, not M.** The method is invoked as a literal `python3 rew_tool/…` everywhere (`install.sh:1102-1103`, SKILL.md, the hook, TCC's lookup); a venv or a uv Python means every invocation must find that interpreter. `--break-system-packages` on a system Python is forbidden by `commands/install-tcc.md:59-60`. |
| T-35 | holds | `install.ps1:943` shares the bare `-Y` classifier (`-cmatch`); `upkeep.py:821` isolates in its selftest too. |
| T-36 | holds (code half) | Settings not checkable from the repo. Candidates (`beta-v*`) get no engine release: the workflow triggers on `v3.*` only. |
| T-37 | holds | — |
| T-38 | holds | — |
| T-39 | holds | `upkeep.py:973` reads the ready file in text mode, so the selftest would hide CRLF even if it ran on Windows. |
| T-40 | holds | — |
| T-41 | holds | — |
| T-42 | holds | — |
| T-43 | holds | — |
| T-44 | holds | The exit design touches both installers, the checker and TCC's reading: M. |
| T-45 | holds | `install-tcc.md:27-28`'s claim is false: `installer-consistency.py:686` only asks that *a* tag be present. |
| T-46 | holds | — |
| T-47 | holds | — |
| T-48 | partly | `tag-check.sh:292-314` already hands "CI green on the commit" to the hub preflight (HUB-057/059); the in-repo proposal would bring back the second reader that HUB-059 removed. **Dropped** (§6). |
| T-49 | holds | Also `upkeep.py:980` (the hook run, no timeout). |
| T-50 | holds | Also `issue_triage.py:217-218` (no `gh` → `None`, exit 0). |

**S2 §7, the contract list:** the 30 verbs are complete and right; `selftest` takes no process directory; a missing
argument exits 1, not 2; plan rows can carry `blocked_reason`; `contract.py check --json`'s 21 top-level keys are
exactly the real ones, the REW block is `cross_checks.rew`, and `cross_checks` also holds `glossary_vs_ledgers`,
`tiers_vs_profile`, `proposals_on_disk`, `deliverables_outside_docs`, `continue_head`; `autosound_ai.py key` exits 2
too; the `skill_sha` stamp is `dsp_profile.py:461`. **TCC imports 15 modules, not 14** — `verify.py` is the fifteenth
(TCC `core/vendor_loader.py`, `_VENDORED`, at `f58d208`).

### 2.2 S1 — the instructions

| ID | verdict | correction at `7b3232b`, or what the report missed |
|---|---|---|
| I-1 … I-5 | hold | I-2's existing asserts are `autosound_ai.py:1479-1480`. |
| I-6 | holds | **More stale than listed:** the route rows c01–c16 of `patterns/listening-cheat-sheet.md` (e.g. `:54`, `:66`; c16 says "protection filters (1.2)", and 1.2 is now the tuner's wishes) and its `.uk/.de/.pl` copies; `core/estimator-scope.md:115`. `phase_1_foundation.md:7` already uses the new numbers. |
| I-7 … I-9 | hold | — |
| I-10 | partly | `SKILL.md:140` and `core/process-phases.md:53` only *list* centre/rear under Phase 5; the gate itself is `phase_5_variations.md:56` and `phase_3_control.md:67`. |
| I-11, I-12 | hold | — |
| I-13 | partly | `core/project-intake.md:105` says "Helix/DSP software", not PC-Tool or `.pct6`. |
| I-14 | holds | — |
| I-15 | holds | Re-run here: `session-close --help` exits 0 and writes `session_closed` into the journal; `capture-start --help` opens `cap_001 at --help` and writes `docs/plans/_--help-capture.md`; `decision --help` and `target --help` exit 1 with "list index out of range". |
| I-16, I-17 | hold | I-16's engine line is `autosound_ai.py:2817`; I-17's `--doctor` refusal is `:3115`. |
| I-18 | partly | The drivers hold; the token table was not recomputed. |
| I-19 … I-27 | hold | §5.1's rows without their own number hold as sub-items of I-19; the delays-or-all-pass conflict is really `phase_2_eq.md:20,74` against `virtual-first.md:210-213`; the key-location rows are `setup-critic-channel.md:15-20` against `:111-134` (re-read here; S1 gives `:12-14`/`:111-127`). |
| I-28 | holds | Re-run here: `contract.py check <empty> --gate --no-rew` exits 1 and ends "**OK — nothing to fix.**". |
| I-29, I-30 | hold | — |
| I-31 | partly | The 2.x line is `ADVANCED.md:39`. |

### 2.3 S3's text proposals — the skill-side facts

| ID | verdict | what the skill says today |
|---|---|---|
| P1 | holds | The desk sends the user to the car without naming a visit (`virtual-first.md:269`, `:331`; `listening-cheat-sheet.md:66`; `phase_4_listening.md:45`), and the scene A/B inside desk step 2.1 (`virtual-first.md:330-336`) contradicts "a listening or a control series has no place in it" (`:353-354`). |
| P3 | holds | No slot-naming rule; "memory" is never used for a DSP slot; `phase_5_variations.md:49` "Preset 2"; `naming-and-structure.md:39,184-185`; `preset-strategy.md:12-16`. |
| P4 | partly | Much is there (`listening-cheat-sheet.md:128-145` one flaw three answers, `:147-175` A-B-B-A, `virtual-first.md:384` three suspects, `competition.md:101` the master volume); missing: the block format, the one-decision limit, a level field on `listening-verdict` (`process.py:1960`). |
| P6 | holds | = I-6. |
| P9 | holds | Nothing places the reviewer relative to the car; `SKILL.md:196` and `virtual-first.md:388` put Phase 3's verdicts in the car session. **Naming collision:** the two loop modes need names other than the reviewer modes A/B/C that `core/process-control.md` owns. |
| P10 | holds | README `:8`, `:101`, `:103` and FAQ `:117-118` give no visit count. |

### 2.4 S2 §2 — the 2026-09-09 review's open rows

F4, F5, F7, F9, F11, F13, F14, F15, F16, F17, F18, B3–B8, C2, E-time, E-pair and the "also from those files" rows hold.
F2 partly (`capabilities.md:41` is fixed; `rew-tool-docs.md:80` still lacks `--session`). G1 partly (`skip` now needs a reason; but `autosound_ai.py:2900-2901` still only prints an instruction to run
`process.py … reviewer …`, so the reviewer record depends on the model obeying — placed in J8). F12 not recounted. F15: `capabilities.py:106` calls `skill_metrics.sh` a usage-metrics script; it
is a complexity guard. E-time: `install.sh:744` and README `:48` say 10–20 minutes, `install.ps1:750` 5–15.

---

## 3. Groups

A group is findings that share one solution (hub `hub:seam`). Each carries the four assessment lines of hub
`WAVES.md` §1 (class · model · risk · complexity); "opus" builds, "Fable" reviews risky code at the end (the
Arbiter's rule, 2026-09-30). Every task starts with its test, written red first. Where the architects disagreed,
the options are named with the advice; the choice is the Arbiter's.

**Before any group: the runner must be able to fail** (group S4a). Today `scripts/run-selftests.sh` skips a file
without the word "selftest" silently (`:96`), takes a usage print as a pass (`:27`, `:103`), has no timeout (`:26`)
and counts "NOT RUN" nowhere (`:131`) — and J1 edits every module it runs. The two test-gap reads both put this first.

### Joint groups — TCC plans its side against these

#### J1 · The contract and the handshake

- **Findings:** K-6, T-19, T-20, T-21 (the version half), T-22, T-24, T-27, S2 §7. TCC: TB-F2, TB-F6, TB-F7.
- **Settled already** (hub, 2026-10-04): TCC writes through the method's commands and reads by import; the contract
  writes that down. TCC imports 15 modules (§2.1).
- **Design (advised, question 1 (a)):** `CONTRACT_VERSION` — an int literal beside `FORMAT_VERSION` in
  `contract.py:48`, readable from any tag by `git show` without running code; `python3 rew_tool/contract.py version
  --json` as the handshake (a child process, so it works even when imports are broken; an older method answers usage
  and exit 2 = "contract 0" — pinned by a test first); an `IMPORTABLE` table beside `CONTRACT` (`:69-80`) listing the
  15 modules and the ~40 names TCC reads, with their signatures; `rew_tool/CONTRACT.md` with S2 §7's twelve items,
  each marked *guaranteed* or *planned, wave N*. The bump rule: a breaking change to a listed item bumps the number,
  only in a minor (a `### Breaking` entry, which the hub preflight already refuses on a patch); additions do not bump.
  The loader `siblings.py`: one module object per file, adopting any copy already in `sys.modules` by real path,
  registered before it runs and removed if it fails, under one lock — this ends the two `NamingError` classes TCC
  sees today. **Contract 1 = the v3.1.x surface TCC lists** (its plan §9); what J1a–J4a add is additive under 1
  (§8 M5). The `sys.path` edits of the importable closure go in J1b, by W-10 (§8 M4); the rest in J1c.
- **Weighed:** the clean variant (a package, `contract-surface.json`, `CONTRACT_MIN`) — not taken: the package is
  the widest diff here, and `CONTRACT_MIN` is covered by TCC's own rule that a bump waits for a TCC release that
  accepts it (§8 M6). The smallest variant — kept its signature pins in `IMPORTABLE` instead of `__all__` on every
  module.
- **J1a (first wave):** (1) the `version` verb and the constant; (2) `CONTRACT.md` and `IMPORTABLE`, with TCC's names,
  plus a guard (`scripts/contract-guard.py`, run by the runner) that holds the literals, the tables and the promised
  names; (3) `siblings.py`; (4) convert the sites that break today — `dsp_profile.py:318,384,348`, `rew_api.py:331`
  and `timebase`, `process.py`'s four loaders, `state.py:256` — and mark the six modules that pass the probe as
  clean. Tests first: the by-path probe from a temp folder under `python3 -P` (red today: `annotate_modellable`
  raises `ModuleNotFoundError`), each loader returns a real object and a deleted sibling raises, one `NamingError`.
  **infra · opus · medium** (shared module objects change what tests that patch globals see) **· M.**
- **J1b (W-10):** (1) the rest of the importable closure onto the loader (`contract.py` first, it unblocks
  `process.py`); (2) then, with the guard counting zero bare sibling imports in the closure, **no module TCC imports —
  nor any module they load in-process — edits `sys.path` at import or call time**: `verify.py:33`, `project.py:40,
  1389,1568`, `naming.py:1081`, `project_seed.py:71,340`, `eq_export.py:50,585`, `resonalyze_vc.py:95`,
  `protective.py:75` (§8 M4); (3) T-24 notes returned instead of printed, environment precedence written down, not
  flipped; (4) the readers TCC asks for (its §4.1 item 6): `Process.capture_history()` in the state-slice shape,
  `is_taken` and `outstanding` public, `capture_superseded` and the closed event's `outstanding` documented; a public
  `PresetHistory` path accessor in place of the `_path` TCC calls; (5) `CONTRACT.md` complete (T-22). Not built:
  a `"contract"` key in outputs, T-20 (§6). **infra · opus · medium · L.**
- **J1c (W-11):** the modules outside the closure (CLI-only) keep their `sys.path` edits only under `__main__`; the
  bare-name alias goes; the guard forbids both. TCC's prerequisite is already met: its conftest re-points a bare
  `sys.modules['rew_api']` (`tests/conftest.py:208-210`) — after J1c there is none, the branch goes dead and nothing
  breaks; the patch that matters goes through `vendor_loader.load_rew_api()` (`:214`). **infra · opus · medium · S.**

#### J2 · Writers and the lock

- **Findings:** T-8, T-17, T-9, T-14, T-12, T-18, K-3. TCC: TB-F9, TA-1 (the lock wait on the GUI thread).
- **Settled by both architects, against the hub's map:** the lock lives only inside the skill's writers; **TCC never
  takes it.** TCC holds its own `flock` for the whole child run (`process_writer.py:159-178`, up to 120 s for
  `capture-check`); a child that took a shared lock would wait on its own parent. An "already held" token in the
  environment is out: `vendor_loader.child_env()` copies all of it into the agent's Bash. Every TCC write already
  goes through skill code (the CLIs, and `Project.save` from `car_library.py:140-150`), so the lock reaches TCC
  without a TCC change — and **J2 does not have to ship in one wave on both sides**. TCC deletes its own lock in the
  commit that re-pins to J2b's tag; that also clears TA-1's 120 s wait and cancels TB-F9's Windows half.
- **Design (advised):** one stdlib module, `rew_tool/project_io.py`, loaded under one `sys.modules` name:
  `atomic_write_json/text` (a unique temp name opened exclusively — `mkstemp` would make `project.json` 0600 — then
  flush, `fsync`, `os.replace`, a short `PermissionError` retry on Windows); `create_exclusive` (`O_EXCL`, for ledger
  versions); `project_lock` (`<project>/.autosound/write.lock` with its own `.gitignore`, `flock`/`msvcrt.locking`,
  re-entrant; a held lock waits `AUTOSOUND_LOCK_TIMEOUT_S` — default 10 s, set per call by TCC, never in
  `child_env()` — then exits **75**, "busy, nothing written, safe to retry", with a `busy:` line naming the lock
  (§8 M1)); `read_json` (absent → default; anything else → `Unreadable`,
  which is **not** a `ValueError`, or today's `except (OSError, ValueError)` blocks would swallow it again). No
  revision counter in `process-state.json`: every read-modify-write loads inside the lock, and a new field would
  change what TCC's own fold reads. The lock is never held across REW, git or `gh`: `check_captures` reads REW
  unlocked, then re-loads and merges under the lock by round id.
- **Weighed:** smallest (lock in the first wave, functions only) against balance (atomic writes first, the lock a
  wave later). Advised: balance's staging and file layout, with smallest's exclusive-open temp name. **One open
  point for the Fable review:** a filesystem that cannot lock (a Parallels shared folder, SMB, a cloud folder) —
  smallest warns and writes unlocked, balance refuses. Advised: write, with a visible line naming the folder; a
  refusal would stop every write on the VM's shared folders.
- **J2a (first wave, with J3a — one shared module):** (1) the atomic writer; (2) every fixed-temp writer through it
  (`process.py:2533`, `project.py:839`, `state.py:579,726,866,1682,1137,1484`, `dsp_profile.py:465,708,785`,
  `migrate.py:237`, `resonalyze_ir.py:345`, `autosound_ai.py:479,2296`), unique review names, and a scan that no
  `".tmp"` literal or `os.replace` remains outside `project_io`; (3) T-9 `O_EXCL` ledger versions; (4) T-14 the
  journal's newline guard. Tests first: a foreign `<state>.tmp` left untouched (red today); a half-written file leaves
  the old one byte-identical (fault injected through the writer, not by patching `open`). **defect · opus · low**
  (same bytes for one writer) **· S–M.**
- **J2b:** (1) `project_lock`; (2) every `Process` verb under it, `check_captures` and `enter_phase` split around
  their slow calls; (3) `Project.save` takes the rev from disk under the lock, and a `Project.update(fn)` — TCC's
  `car_library` moves to it; no `expected_rev` (§6); (4) ledger snapshot, seals, slots, `state.py config save`,
  `intake.py set-car` and the `dsp_profile` writers under it — every writer CLI TCC runs; (5) contract §8 and `process-schema.md:203`; a `PROTOCOL = 1` literal TCC reads as text to know a copy locks
  itself. Tests: two processes (`spawn`, never `fork`) synchronised by events, not sleeps; a held lock makes a child
  CLI exit 75 "busy" with the files byte-identical; a Windows CI step, because `msvcrt` runs nowhere else; a VM run
  before the tag. T-8's Windows retry is already out with J2a — never later than the lock (TCC's condition).
  TCC adopts the lock in its own W-11 (its lane and the lock together); an older TCC with this tag is safe (§8 M2).
  **defect · opus + Fable · high · M.**

#### J3 · Unreadable is not empty

- **Findings:** K-2, T-10, T-11, T-13, T-15, T-17 (`_project_rev`), T-21 (the read rule), I-28. TCC: TB-F5, TB-F3.
- **Design (both architects):** strictness is opt-in — `Process.load(strict=True)` — because ~12 read-only callers
  and TCC's screen rely on today's default; `_write` refuses to replace an existing unreadable file, which protects
  every write verb at once; strict reads in `contract.check_process`, `show` and `session-close`.
- **Settled with TCC (§8 M2):** the hub withdrew its "or TCC's screen breaks". It does not break: TCC already passes refusals through verbatim and renders `valid: false`; without its change it
  still shows an empty plan as today — but `_write`'s guard stops the overwrite. TCC's better display (the reason
  instead of an empty plan) can follow in its next wave.
- **J3a (first wave, with J2a):** (1) `read_json`/`Unreadable` over a matrix — absent, empty, truncated, a cp1251
  byte, a BOM, `[1,2]`, a directory; (2) K-2 as above; (3) T-11 seals and `_project_rev` strict; (4) T-13 the draft
  refuses instead of `break`ing to a blank one; (5) T-10's unreadable half — a checker that raises or a file that
  cannot be read refuses (this reverses `process.py:397-402`'s "must not become a wall", by design); (6) I-28 the gate
  report's last line states the verdict; (7) T-21's refusal of a newer schema in `Process.load(strict=True)`,
  `PresetHistory` and `load_profile` (TCC's §4.1 item 4). Tests first: today's fresh-project path pinned (no file → empty state);
  a torn journal line still skipped; then `{trunc` → `enter-phase -1` exits 1, bytes unchanged.
  **defect · opus + Fable · medium** (existing damage in the cp1251 population surfaces; every refusal names the
  repair command) **· M.**
- **J3b:** T-10 gating on `complete` with a parity test against `contract --gate`; T-21 `check_schema` for the
  glossary, migration hints for older files, every format constant equal to `FORMAT_VERSION`; T-15's four sites; every external `Process.load` caller states `strict=` (a scan
  refuses a bare call). **defect · opus · medium · M.**

#### J4 · REW: three states, two new exit codes, a write that reads back

- **Findings:** T-1, T-2, T-3, T-4, T-5, T-6, T-7, K-1, T-23, T-29. TCC: TB-F4, TA-3, TA-5.
- **Design (advised: the smallest variant's first wave):** exit codes 0/1/2 keep their meaning, 3 and 4 stay per
  tool; three new, from sysexits, none used by any tool today: **69** REW unavailable (nothing written), **70**
  unexpected error, **75** busy (reserved here, raised by J2b's lock — §8 M1). An unknown `--flag` on any
  `process.py` verb is a usage error (exit 2), never absorbed as titles or reason text (N19 from TCC's plan,
  `process.py:3602-3609`, `:3706-3730`). `process._main` gets the catch-all. REW exceptions live in `rew_api.py` itself (a new sibling import would
  break TCC's by-path load): `RewUnavailable` (also an `OSError`), `RewProtocolError` (also a `ValueError`),
  `MeasurementNotFound`/`AmbiguousTitle` (still `KeyError`, same words — TCC reads them), `RewWriteMismatch`; matched
  by an attribute, never by class across module copies (`rew_api` is loaded three times today). `verify` gains a
  third state; `capture-check` with REW down exits 69 and writes nothing; a check never creates `taken` for a title
  REW does not hold, while a title REW does hold still becomes taken (capture-close's own rule, skill #77 — a
  deliberate departure from S2's "never"). K-1: keys refused before any request, the filters read back and compared,
  a missing slot is truncation; **the skill reads back, TCC does not.**
- **Weighed:** the balance variant converts a payload `KeyError` into `RewProtocolError` in the first wave — the
  smallest variant shows that crashes every caller that catches only `KeyError` until they migrate, so it waits for
  J4b. Taken from balance: a key **denylist** (`gain`, `gain_db`, `freq`, `f`, `Q`), not an allow-list, until the live
  pass shows REW's real key set; and its client design for J4b.
- **J4a (first wave):** (1) the exit table and catch-all; (2) the exceptions, a `_fetch` that covers the read
  timeout, the listing's shape check; (3) `verify`'s states and T-4; (4) T-1, with N17 from TCC's plan —
  `unusable_captures`, `capture-check`'s print loop and the closing event's `taken` ignore `superseded_by`
  (`process.py:2223-2231`, `:3759-3769`, `:2276`) and move to `_is_taken`; (5) K-1; (6) N19's usage rule; (7) the
  table in both usage texts and the CHANGELOG. Tests first: today's `KeyError` wording and the `capture-close` REW-down exit 0 pinned;
  then a real closed port (not a patched function) → exit 69 with state and journal byte-identical; a local
  `http.server` answering 500, HTML, `[]`; `capture-protective --hp abc` → 70; a `gain` entry refused with zero
  requests counted at the handler. Before the tag: question 7's live pass. **defect · opus · medium · M.**
- **J4b:** one per-call deadline over connect and read; the proxy bypassed for loopback only (`rew_api.py:11`
  supports a REW on another host); a thread-local base URL (`BASE_URL` stays readable — TCC reads it); T-5; the
  12+ callers of §2.1 narrowed and payload errors moved to `RewProtocolError`; 69/70 in every tool's main; T-29 the
  stub serves REW's recorded shapes. Selftests move from patching `urlopen` to `_fetch` first, or the new opener
  sends them to the network — **TCC's fixture `tests/test_rew_api_shapes.py` too** (§4 N9). `BASE_URL` stays a
  readable, assignable module name (TCC's conftest and `rew_bridge` use it). **defect · opus · medium · M–L.**

#### J5 · The seed preview

- **Finding:** K-4. TCC: TA-1's part (a seed into a temp folder on every typing pause).
- **Answered by TCC's plan (§4.1 item 9):** `describe()` does not cover the dialog; TCC needs a real dry run.
  `seed(..., dry_run=True)` with no git, no `gh`, no `Project.save` (`:485`), no `.gitignore` (`:491`), whose
  record carries the Fs count; the module's lazy imports moved to the top. Before TCC's W-12.
  **feature · opus · low · S.**

#### J6 · Trust what users install

- **Findings:** T-34, T-35, T-37, T-38, T-39, T-40, T-43, T-44, T-45, T-46, F17, E-time, E-pair, T-36 (code half).
  TCC: TB-F1, TB-F10, TB-F13.
- **Found on the way:** (a) **TCC reads neither the installer's exit code nor its receipt** — only the skill's doctor
  reads the receipt (`autosound_ai.py:2779-2806`); TCC reads `upkeep.py --json libs`. A new exit code needs no TCC
  change. (b) **To check first:** `install.sh:880`, `install.ps1:941` and `upkeep.py:121` accept any line containing
  "Good"; git picks the verifier from the signature, not from `gpg.format`, so a tag signed with any key in the
  person's GPG keyring may pass. Read from git's design, **not reproduced** — the first test of J6a decides it. TCC
  already requires `Good "git" signature`. (c) `plugin-ready` is written even after "Installed, with the warnings
  above" (`install.sh:1780`, `install.ps1:1823`), so a broken plugin install is never told again.
- **J6a (W-9):** (1) tests first in `installer-consistency.py`: the signing cases under a hostile global git
  config, a stub `git` printing "Good signature from", an empty `ls-remote` → exit 1 with the clone untouched, one
  table of tag names answered the same by both installers and `upkeep`, the exit-code table, E-time/E-pair compared;
  (2) T-35 `gpg.ssh.program` pinned in all three paths, classification on git's own sentences, only `Good "git"
  signature for <principal>` accepted; (3) T-37 no readable tag stops (exit 1), `main` only by an explicit flag and
  printed as unsigned, one release-tag rule (T-45), HEAD checked against the tag after a clone, `install-tcc.md`
  pinned to the paired TCC with `--python 3.12`; (4) the exit contract — 0 ready · 1 stopped, nothing changed · 2
  usage · **3 installed, not ready** with the missing parts named — the receipt's `status`, `missing`, `python`,
  `installer_version` (replacing the hash that is empty under `curl | bash`), plugin-ready only on 0, the library
  install judged by importing, T-38 the link recreated, T-40, T-39, T-44's engine codes; (5) a CI step on
  ubuntu-24.04 against `/usr/bin/python3` expecting exit 3. A VM run before the tag. **defect · opus · medium**
  (exit 3 is new; an offline install now stops) **· M.**
- **J6b (after question 2):** the interpreter (advised: uv's 3.12 as `python3`), T-43, F17/T-46 — CI on Python 3.9 and
  3.12, macOS and Ubuntu jobs asserting the login shell's `python3`. **infra · opus · medium · M–L.**
- **J6c:** T-36's code half — `SHA256SUMS` signed with the release key and checked in `fetch_binary` (the settings half
  is the hub's and the Arbiter's, §4). **infra · opus · low · M.**
- **J6d (W-12, with TCC — §8 M10):** TB-F1 — the installers read `constraints.txt` from the verified TCC tag and pass
  `-c`; a tag without the file installs as today and says so once. Safe before TCC ships the file, so both land in
  W-12 in either order. **infra · opus · low · S.**

#### J7 · The user's path — the text

- **Findings:** P1, P3, P4, P6 (= I-6, built in S1), P9, P10. The car family P2, P5, P7, P8 waits for question 6.
- P3 the slot rule in prose (`naming-and-structure.md` §1a/§5, `preset-strategy.md`, `phase_5_variations.md:49`);
  P9 one line in Review Channel and `review-loop.md`: no reviewer call inside a car session; P10 the visit count in
  README and FAQ, four languages (translations through the Advisor); P1 the visits block, after question 6; P4 the
  A/B block and the one-decision limit, plus a level field on `listening-verdict` (`process.py:1960`, code).
  **Naming:** the two loop modes need words other than A/B/C — `process-control.md` owns those for the reviewer.
  **docs (P4: feature) · opus · low · S.**

#### J8 · What the model is told

- **Findings, the skill's side:** I-2 (the reviewer is told the prose is its truth), I-5 (a stale project copy of the
  contract outranks the skill's), I-21 (two homes for the prose files; `handoff` and `harvest_inbox` read different
  folders). **TCC checks its side:** the opener and system prompt, `get_tcc_state.reviewer.configured` (09-09 B9), the
  MCP tool list against `SKILL.md:98` (B10), which skill copy it loads, and TB-F8 (its own older DSP profiles).
- I-2: the injected section renamed "prose view — the machine files win", `reviewer-tuning.txt:1-2` to match, the
  ledger HEAD in every package, an assert that the phrase occurs once. I-5: stop copying the contract into projects;
  until then `doctor` and `contract.py check` name a copy that differs. I-21: one folder per file, both readers look
  there, a fallback that warns. Riding along: the contract template's own contradictions — the Trace IDs it teaches
  that the resolver refuses (§5.1 row 17), "no role rotation" against "rotate afterward" (row 18) — and the reviewer
  task per round (row 11, `review-loop.md:39` against `process-control.md:26`); and G1's open half: the door records
  the `reviewer` step itself instead of printing an instruction to run it (`autosound_ai.py:2900-2901`).
  **defect · opus · low · S–M.**

### The skill's own groups

#### S1 · Contradictions a session meets on every tune

- **Findings:** I-1, I-11, I-6/P6, I-7, I-15, I-16, I-20, I-23, I-29; §5.1 rows 7 (boost policy), 13 (ledger HEAD
  against the DSP screen), 15 (Time Offset — check first whether the readers take an offset), 21 (the stop order).
- Both text architects: fix these sentences **before** any cut, so the cut moves corrected text and its rule list is
  written once. Interim for I-12 (smallest variant): the four "If Phase −1 chose…" banners become one identical
  sentence — the order of work is virtual-first's, sections marked iterative apply only when its Degradation routes
  there.
- Tasks: (1) checks first — step pointers resolve to a step whose title holds the cited word, no duplicate step ids,
  no `capture-start 1` in the phase files, phrase rules for I-11 and the arrival method; (2) I-1 `installation.md`
  and `SKILL.md:152`; (3) I-11 and `project.py catch-up`'s help; (4) I-6 the second 1.7 becomes 1.8, pointers as
  "1.5 joints" in four languages (renumber nothing else — the journal and TCC carry step ids); (5) I-7 one capture
  recipe in the sheet's Block 0; (6) I-20 "the tools read arrivals; the GUI is the cross-check on ILL-POSED or
  UNVERIFIED"; (7) I-16 the doctor's exit code kept, its engine line fixed, and I-15 `--help` on any verb prints that
  verb's line and writes nothing; (8) I-23, I-29, the one-path sentence, and the remaining §5.1 rows — 7 boost, 13 ledger HEAD vs screen, 14 knob
  state, 15 Time Offset, 19 when taste is asked, 20 how the language is recorded and the double `-1.2`, 21 stop order,
  22 the generated sheet, 23 Phase-3 titles — with the one-liners on delays vs all-pass, review before or after
  banking, the RTA FFT and installing by hand-copy; the sweep-level pair gets both quantities named (output dBFS vs
  input peak); and the TCC facts its plan corrected — `SKILL.md:98`'s tool map (TCC has `session_close`,
  `set_target`, `capture_knobs`; `capture-protective` and `listening-verdict` are UI-only; `reviewer` is written by
  `call_critic`) and `reviewer.reachable`, present as null when not configured, with `model`/`ready` absent
  (`core/project-intake.md:16-17`, `phase_-1_intake.md:41`). **docs · opus · low · S.**

#### S2 · SKILL.md back under the re-attach budget

- **Findings:** I-3, I-4, I-24, I-26, I-14, I-19 (SKILL.md's own copies), I-25 (the § index atop
  `diagnostic-techniques.md`, the §50 pointer), I-30 (in the sentences rewritten), F15.
- **Facts the cut must respect:** `docs-check` rule `references-orphans` wants every reference named in SKILL.md
  (`docs-check.py:176`); it anchors the "⚠️ Core Guardrails" heading and the PHASE_SOURCE sentence; code prints
  pointers into the docs (`process.py:3688` "EXIT CHECKLIST (SKILL.md)", `:687`, `resonalyze_engine.py:1778`).
- **Weighed:** balance (reorder, cut to 16,000 characters, a `references/INDEX.md`, a move-check script and a rule
  ledger) against smallest (keep the order, the Reference Map last, ≤ 17,500 bytes before it, a rule manifest inside
  `docs-check.py`, no new files). **Advised: smallest for this group** — the rules come to ≈ 4.4K tokens, inside the
  re-attach budget, with no file added — **plus balance's move-check** (every removed sentence appears elsewhere or is
  named as dropped in the commit).
- Tasks: (1) checks — the rule manifest, the budget (description ≤ 1,024 characters, the map last), a reading-cost
  script with today's table as the baseline; `skill_metrics.sh` retired (it is wired nowhere and fails on its own
  cap); (2) the cut — the language anecdote, the close procedure, the capture mechanics, the step-id detail, the
  Helix example, the history lines to their homes; the next phase read only to its Goal-node; (3) I-24 the evals
  current, then I-4: three trigger runs before and three after on the owner's Mac without the other car-audio skill;
  (4) I-14 a four-column report-word table (translations through the Advisor); (5) I-26; (6) I-25's generated §
  index for `diagnostic-techniques.md`. **Ask TCC first** whether it
  quotes or injects SKILL.md sections. **docs · opus · medium** (a moved rule weakens in a phase that does not read its
  new home; a description cut can move recall) **· M.**
- Per full tune (S1 §3.2, §11): ≈ 307K tokens today → ≈ 265K after S2 (the architects' estimate: the SKILL.md cut
  plus the next phase read only to its Goal-node) → ≈ 188K after S3.

#### S3 · One path; virtual-first split by phase

- **Findings:** I-12, I-18, I-13, I-22, I-19 (the rest), I-25, and the text answers to questions 3–5.
- Carries out the 2026-09-09 decision ("one path: virtual-first with degradation", review §9 item 3) — decided, not
  reversed. The iterative text goes to `references/phases/degraded-desk.md`; each phase file opens with its Goal-node
  and gate; `goal.design_path` stays as data (TCC and old projects read it) and is no longer asked as a choice.
  Moves are pure and checked by the rule ledger. **Waits for question 6's walk** and for the joint groups that edit
  phase files. **docs · opus · medium-high · L.**

#### S4 · Tests that can fail

- **S4a (first, before J1):** T-28 the runner — an expected count, no silent skip, a final OK line required, a
  timeout per module, "NOT RUN" counted and failing in CI; T-30 `REW_API_URL` pointed at a dead port in the runner and
  `--no-rew` where selftests reach REW; T-25 the ATF export checked by values; T-33 values anchored on published
  ISO 226 points, one case per naming production, negative cases for `_validate_eq` and `check_project`. New tests are
  separate functions: every selftest today is one function, and its first failing assert hides the rest.
  **infra · opus · low · S–M.**
- **S4b:** T-26 a smoke run per CLI verb on a seeded project and golden key sets for `contract`, `deployment`,
  `process show/plan/handoff`; T-31 a checker with no input fails; T-32 checkers matched against parsers, not text;
  T-47 the real-tree modes in the runner and a scheduled `upstream-drift`. **infra · opus · low · M.**

#### S5 · Documents against the commands, and dead references

- **Findings:** I-17, I-27, I-25 (the § pointers), I-31, the S2 §2 rows F2, F4, F5, F7, F9, F11–F14, F16, F18, B3–B8,
  C2, G1 (the `skip` example) and the "also" rows; FAQ:130 (I-20's user half); S1 §5.2's verbs nobody routes to;
  §5.1's one-liners on the key location, the Gemini ids, a pinned model name, the glossary home, the
  `target-curve-*` memory, version labels by hand and the legacy ledger path.
- `doc-commands-check.py` widened to every model-read document (modules by the path written, placeholders as whole
  tokens, a usage exit 2 as a refusal), then the rows fixed; a path-and-§ resolver, then I-27 fixed; the reviewer-
  channel setup file cleaned (F4, F5, F14; the `printf … >` line at `:10` that overwrites the machine key file; the
  closed `gemini` CLI at `:294`; the key-location and model-name one-liners); `rew-tool-docs.md` (F2, F7, F12, F13,
  F18, the API-connectivity duplicate at `:5-11`, the change history inside it); `capabilities.md:173`;
  `rew-api-quirks.md:7`; `--help` that says how to read the output in `eq_propose`, `ear_suspects`, `ellipsoid`, and
  `rew_tool.py --help` in English; the verbs nobody routes to (`process.py` `amp-changes`, `capture-import`,
  `capture-supersede`, …; `project.py` `set-path`; `state.py` `seal`, `verify`, `repair-version`, `variant`, `config`;
  `apply.py` `attest`, `--evidence`, `--reviewed`) named where a session would look; README and FAQ in four languages
  (I-31) and `i18n-check` extended to inline code, links and numbers. **docs · opus · low · M.**

#### S6 · Subprocesses and helper scripts

- **Findings:** K-5, T-49, T-50 (= the 09-09 F6: `autosound_ai.py --help`), T-41, T-42, F8 (`DEFAULT_CURVES_DIR` is
  still the author's folder, `rew_tool.py:22-24`).
- One `run()` with a timeout, modelled on `upkeep.py:66`, for every subprocess (K-5, T-49, and `upkeep.py:980`); the
  clipboard and `issue_triage` report failure (T-50); the key guard refuses on any git error but "not a repository"
  (T-41); `deployment.py` trusts HEAD only when the repository's top is the copy's root (T-42); no author's folder as
  a default — the curves folder is given or found, else the tool says so (F8).
  **defect · opus · low · S.**

---

## 4. Dependencies on TCC

The hub matches this list with TCC's. "Wave" is the skill's; TCC's work lands in its own next wave after the skill's
tag, unless marked *before*.

**What the skill needs from TCC**

| # | what | for | when |
|---|---|---|---|
| N1 | The ~40 names TCC reads from the skill's modules (its AST inventory) | J1a `IMPORTABLE` | **delivered** — TCC's plan §9 |
| N2 | TCC's suite run against the J1a and J4a candidates (`AUTOSOUND_SKILL_DIR` at the candidate) | shared module objects; new exception types | **before** those tags |
| N3 | Whether TCC quotes or injects SKILL.md sections | S2's cut | **before** S2 |
| N4 | Whether `project_seed.describe()` covers the New-project dialog | J5 | **answered** — no; a dry run (§3 J5) |
| N5 | J8's checks on TCC's side: opener, system prompt, `reviewer.configured`, the MCP tool list, which skill copy | J8 | with J8 |
| N6 | Which of P2/P5/P7/P8 TCC's screens already carry | J7 | after question 6's walk |
| N7 | A `constraints.txt` with each TCC tag | J6d (TB-F1) | W-12, either order (§8 M10) |
| N8 | Agreement on rewording `goal.design_path`'s question (`intake.py:99,1188`, four i18n files) | S3 | before S3 |
| N9 | TCC's `tests/test_rew_api_shapes.py` patches `urllib.request.urlopen`; it moves to `rew_api._fetch` | J4b (the new opener bypasses `urlopen`) | **before** J4b's tag |

**What TCC gets from the skill**

| # | what | closes for TCC | wave |
|---|---|---|---|
| R1 | `CONTRACT_VERSION = 1` (= the v3.1.x surface), readable from a tag with `ast`; `contract.py version --json` for diagnostics | TB-F2: a handshake instead of three files existing; the updater picks the newest tag it supports | J1a |
| R2 | `siblings.py`, one module object per file | the duplicate `NamingError`; TCC's `vendor_loader` goes through it | J1a |
| R3 | Exit codes 69/70 and 75 reserved, unknown flags refused (N19), the REW states, the read-back in `set_filters`, N17 | TB-F4: `write_rew_filters` returns `applied: false` with the reason; **no second read-back in TCC**; `tests/test_rew_api_shapes.py:54-67` must answer GET /filters with what was written — **blocking for TCC's re-pin** | J4a |
| R4 | `Process.load(strict=True)`, the overwrite guard, newer schemas refused in three readers | TB-F5: TCC shows the reason, not an empty plan; `report_phase` stops telling the agent to `enter_phase` | J3a |
| R5 | The lock inside the skill's writers; exit 75 «busy»; `AUTOSOUND_LOCK_TIMEOUT_S` per call; `PROTOCOL = 1` | TB-F9 cancelled; TA-1's lock wait gone: TCC deletes `_exclusive` and `_THREAD_LOCK` in the commit that re-pins; **TCC never holds `.autosound/write.lock`** | J2b |
| R6 | The read-only module list with guarantees, no `sys.path` edit in it, `capture_history()`, public `is_taken`/`outstanding`, a `PresetHistory` path accessor | TB-F6: TCC calls the skill's readers instead of its own folds, with parity tests; T-19 gone for TCC | J1b (W-10) |
| R7 | The installers' exit 3 and receipt | nothing required (TCC reads neither) | J6a |
| R8 | — | TB-F8 (D-1): TCC uses `dsp_profile.find_bundled`'s own library; nothing new from the skill | — |

**On the skill's side, nothing to do:** C3 (09-09) — `capture-check --session` stays in the CLI
(`process.py:2637`); reaching it is TCC's.

**TCC's twin of a skill finding:** T-35 — `updates.py:830` verifies tags without pinning `gpg.ssh.program`, and its
classifier matches a bare "-Y" (`:767-773`). Same fix, TCC's own wave.

**For the hub:** (1) J2 and J3: each side's half is safe alone — §8 M2. (2) T-36's settings half — a tag ruleset on `refs/tags/v*` and `beta-v*`, immutable releases on — is the
Arbiter's flip (AUDIT-INDEX §3). (3) T-48 stays with the hub's preflight (§6).

---

## 5. The order across waves

A proposal for the milestones; each wave's milestone takes what the Arbiter gives `ok`, task by task. W-8 is in
collection; this plan is an input to its milestone, not the milestone.

| wave | groups | why here |
|---|---|---|
| **W-8** | S4a · J4a (with question 7's live pass; N17, N19, the exit table with 75 reserved) · J2a + J3a · J1a (contract 1) · S1 | the runner first; then the defects that corrupt a record or report a false success (a capture counted taken, a flat filter "applied", a bricked `project.json`, unreadable read as empty); the handshake TCC plans against; the wrong advice read on every tune. All of it is invisible to, or additive for, today's TCC. |
| **W-9** | J2b (Fable) · J6a · J8 · J7 (P3, P9, P10) · S2 · S6 | the lock once J2a/J3a are out (TCC adopts it in its W-11; each half safe alone, §8 M2); honest installs and the signature rule; what the model is told; SKILL.md under the budget once S1's sentences are right. |
| **W-10** | J1b (no `sys.path` edit in TCC's modules) · J4b · S4b · S5 · J5 | the wide, mechanical moves once the guards from W-8 hold them; TCC's «joint 1» re-pins onto them. |
| **W-11** | J1c · J3b · S3 · J6b · J6c · J7 (P1, P4, the car family) | the steps that need a decision or a walk first (questions 2, 3–6), and the last `sys.path` removal. |
| **W-12** | J6d (constraints, with TCC) | TCC's G4 part 2 lands in the same wave (§8 M10). |

---

## 6. Not worth doing, and why

- **T-48's in-repo check** for CI on a candidate — the hub preflight already runs `ci-green` for candidates
  (`tag-check.sh:292-314`); HUB-059 removed exactly such a second reader after the two disagreed. Its other option,
  `checks.yml` running on `beta-v*` tag pushes, would report after the tag is out — the preflight's check comes before.
- **T-6's `ProxyHandler({})` for every host** — breaks a REW on another machine (`rew_api.py:11`). Loopback only (J4b).
- **T-7's `urlopen` part** — the selftest already restores it in a `finally`. Only the `BASE_URL` part is real (J4b).
- **T-16** — every TCC write to the process state is a fresh CLI process, and no long-lived in-process `Process`
  writer exists. Revisit if one appears.
- **Converters for the other two filter dialects (K-1)** — no in-repo caller writes filters; the key refusal makes a
  wrong mapping loud.
- **A revision field in `process-state.json`** — every read-modify-write runs under the lock (J2b); a new field changes
  what TCC's own fold reads.
- **`__all__` on every module (~250 names)** — the contract lists what front ends use, with signatures.
- **What TCC said it does not need** (its §4.1; §8 M6): a `"contract": N` key in JSON outputs (one handshake per copy
  is enough); `CONTRACT_MIN`, SINCE/SURFACE tables; a `--lock-timeout` flag (an older `process.py` would read it as
  data — the environment variable carries the wait); lock tokens, pids, read locks; `expected_rev` on `Project.save`
  (`Project.update` under the lock covers the one in-process writer, `car_library`); contract promises for the CLIs
  TCC imports instead (`naming parse`, `verify --json`, `verify_prediction`, `predict`, `timebase`, `eq_propose`,
  `resonalyze_vc --json`), for `deployment.py --json`, and for `session-reopen`, `capture-import`, `amp-gain`,
  `amp-changes`, `selftest` — they stay documented as the skill's own, not as front-end promises.
- **T-20** — TCC binds no DSP rate in-process (its plan §1), and the CLI models one project per process. Revisit if a
  host models two projects in one process.
- **TCC holding the skill's lock, or an "already held" token in the environment** — a deadlock, and a token that
  leaks into the agent's Bash (J2).
- **`--break-system-packages` on a system or Homebrew Python** — forbidden by the method's own docs; question 2's (a)
  uses it only on uv's own Python.
- **Translating `capture-check`'s existing Ukrainian lines in J4a** — TCC parses them; they move later with TCC told.
- **`skill_metrics.sh` as it is** — wired nowhere, fails its own 1,500-word cap; the budget check in S2 replaces it.
- **P11** (a pre-tune journey for an install change) — not the skill's text share in this volume, and S3 itself puts it
  later; it waits for a real install change to give it a first artefact.
- **Which of the four conflicting acoustic numbers is right** (S1 §5.1: EQ smoothing, sibilance band, centre band,
  default crossover family) — the method's question, outside both audits' lens; the copies are made to agree with
  whichever the method settles (one home per rule), but this plan does not choose. The fifth pair, the sweep level, is
  two quantities left unnamed; group S1's task 8 names them.

---

## 7. Coverage — every finding placed

| finding | group |
|---|---|
| K-1 | J4a |
| K-2 | J3a |
| K-3 | J2b |
| K-4 | J5 |
| K-5 | S6 |
| K-6 | J1a |
| T-1 … T-5 | J4a (T-2, T-3 callers: J4b; T-5: J4b) |
| T-6, T-7 | J4b (parts dropped, §6) |
| T-8, T-9, T-14, T-17 | J2a (T-17's `_project_rev`: J3a; T-14 sits under J3 in the hub's map) |
| T-10 | J3a (unreadable half), J3b (`complete` parity) |
| T-11, T-13 | J3a |
| T-12, T-18 | J2b |
| T-15 | J3b |
| T-16 | dropped (§6) |
| T-19 | J1a (TCC's modules), J1b (the rest), J1c (`sys.path`) |
| T-22, T-24 | J1b |
| T-20 | dropped (§6) |
| T-21 | J1b (versioned outputs), J3b (`check_schema`) |
| T-23 | J4a |
| T-25, T-28, T-30, T-33 | S4a |
| T-26, T-31, T-32, T-47 | S4b |
| T-27 | J1a |
| T-29 | J4b |
| T-34 | J6a (honest exit), J6b (the interpreter) |
| T-35, T-37, T-38, T-39, T-40, T-44, T-45 | J6a |
| T-36 | J6c (code half); settings — hub and the Arbiter (§4) |
| T-41, T-42, T-49, T-50, F8 | S6 |
| T-43, T-46 | J6b |
| T-48 | dropped (§6) |
| S2 §7 | J1a (version, list), J1b (shapes), J2b (§8 the lock), J4a (exit codes) |
| I-1, I-6, I-7, I-11, I-15, I-16, I-20, I-23, I-29 | S1 |
| I-2, I-5, I-21 | J8 |
| I-3, I-4, I-14, I-24, I-26 | S2 |
| I-8, I-9, I-10 | questions 3–5, then S3 (text) |
| I-12, I-13, I-18, I-22 | S3 |
| I-17, I-27, I-31 | S5 |
| I-19 | S2 (SKILL.md's copies), S3 (the rest); §5.1's unnumbered rows: S1 (7, 13, 14, 15, 19, 20, 21, 22, 23; delays/all-pass, review timing, RTA FFT, hand-copy, sweep level), J8 (11, 17, 18), S5 (key location, Gemini ids, model name, glossary home, `target-curve-*`, version labels, legacy ledger path); the four acoustic pairs dropped (§6) |
| I-25 | S2 (the `diagnostic-techniques` index), S5 (§ pointers), S3 (the other indexes) |
| I-28 | J3a |
| I-30 | S2 (rewritten sentences) |
| P1, P3, P4, P9, P10 | J7 |
| P6 | S1 (= I-6) |
| P2, P5, P7, P8 | question 6, then J7 |
| S2 §2 rows (F2, F4, F5, F7, F9, F11–F14, F16, F18, B3–B8, C2, G1's `skip`, the "also" rows) | S5 |
| G1's reviewer record | J8 |
| F6 | S6 (= T-50) |
| C3 (09-09) | TCC's (§4) |
| S1 §5.2 verbs nobody routes to | S5 |
| P11 | dropped (§6) |
| TCC's N17, N19 | J4a |
| TCC's N20 (`verify.py:33`) | J1b |
| TCC's B9/B10 corrections | S1 |
| F15 | S2 (retired) |
| F17, E-time, E-pair | J6a (E-time, E-pair), J6b (F17) |
| TB/TA joint items | §4 |

---

## 8. Settled with TCC — hub #254 (AUDIT-PLANS-MATCH §2)

One round, through the hub. Rows marked *both* carry the skill's position; the hub matches it with TCC's.

- **M1 · busy exit code and wait — agreed with TCC.** A held lock waits `AUTOSOUND_LOCK_TIMEOUT_S` (seconds; default
  10 when unset; a value that does not parse is a usage error, exit 2, naming the variable — a missing input fails
  loudly), then exits **75** with one `busy:` line naming the lock file: nothing written, safe to retry. 75 is sysexits'
  `EX_TEMPFAIL`, beside 69 and 70 in J4a's table; no tool in the skill returns 69, 70 or 75 today
  (`grep -rnE '(return|exit|sys\.exit)\(? *(69|70|75)\b'` over `*.py`, `*.sh`, `*.ps1` → nothing). TCC sets the
  variable per writer call, never through `child_env()` (its point: the omp session inherits `child_env()`). Every
  writer CLI TCC runs returns it: `state/process.py`, `dsp_profile.py`, `state/state.py config save`,
  `intake.py set-car`. No `--lock-timeout` flag (§6).
- **M2 · J2/J3 staging — the skill's position (both).** Same wave on both sides is the **target**, not a gate: each
  half is safe alone, so neither side's tag waits for the other's.
  - *J3, a new skill with today's TCC:* the strict read is opt-in, so `Process.load()` keeps today's default and TCC
    shows an empty plan as today; the next write is refused by `_write`'s guard instead of erasing the plan. TCC
    already treats any non-zero exit as a failure and shows its text (tcc `core/process_writer.py:186-193`), parses
    `contract.py check --json` whatever the exit (`core/contract_check.py:234-240`) and renders `valid: false`
    (`:78`). Nothing regresses; the data is protected a wave earlier.
  - *J2, a new skill with today's TCC:* TCC's own lock is a different file, `process/.process-write.lock`
    (`core/process_writer.py:49`), so its `flock` around a child that takes `.autosound/write.lock` cannot deadlock —
    it only keeps today's serialisation. A busy child answers 75, which today's TCC shows as a failure line.
  - *A new TCC with an older skill:* TCC's own plan §5.4 probes `PROTOCOL = 1` per copy and keeps its legacy lock for
    a method that does not lock itself.
  - So the skill plans J2a/J3a in W-8 and J2b in W-9; TCC shows the refusals in its W-10 and adopts the lock in its
    W-11, as its plan says. T-8's Windows retry ships with J2a — before the lock's tag, as TCC requires.
- **M4 · `sys.path` edits — agreed to TCC's date (both).** By W-10 (J1b) none of TCC's 15 modules, nor anything they
  load in-process, edits `sys.path` at import or call time (§3 J1b lists the sites). `siblings.py` from W-8 (J1a)
  gives one module object per file — one `NamingError` — but does not remove `rew_tool/` from the front of TCC's
  `sys.path`; that stays as today until W-10, no worse. J1c (W-11) keeps only the CLI-only modules and the bare-name
  alias. **J1c's prerequisite is already met on TCC's side:** its conftest re-points a bare `sys.modules['rew_api']`
  (`tests/conftest.py:208-210`) — a dead branch after J1c, nothing breaks — and patches through
  `vendor_loader.load_rew_api()` (`:214`), which stays valid. The prerequisite that is real comes with J4b, not J1c:
  TCC's `tests/test_rew_api_shapes.py` patches `urllib.request.urlopen`, which the new opener bypasses (§4 N9).
- **M5 · contract 1 — confirmed.** `CONTRACT_VERSION = 1` means the v3.1.x surface TCC lists in its plan §9; everything
  J1a–J4a add is additive under 1 (new exit codes, new exception subclasses of the old types, opt-in strictness, a
  usage error for an unknown flag a correct caller never sends). TCC can ship `KNOWN_CONTRACT = 1` in its W-9. A bump
  to 2 comes only on a breaking change, only in a minor, and only after a TCC release that accepts 2 is out.
- **M6 · what TCC does not need — trimmed.** Out of J1b: the `"contract"` key in outputs, `CONTRACT_MIN` and
  SINCE/SURFACE tables, `expected_rev`, a `--lock-timeout` flag, contract promises for the CLIs TCC imports, for
  `deployment.py --json` and for the five verbs (§6). T-20 dropped: no caller in the skill models two projects in one
  process. Kept, because TCC asks for them: the readers and the `PresetHistory` accessor (J1b).
- **M8 · TCC's findings in the skill's code — taken.** N17 → J4a (read at `process.py:2223-2231`, `:3759-3769`,
  `:2276`: a superseded entry counts as taken in all three); N19 → J4a (read at `process.py:3602-3609`, `:3706-3730`:
  the hand parser pulls out the flags it knows and passes the rest on as titles or reason text); N20 → J1b; B9 and
  B10's corrections → S1; K-4's preview without `Project.save` and `.gitignore`, with the Fs count → J5.
- **M10 · constraints order — one wave (both).** J6d in W-12 with TCC's G4 part 2: the installers read
  `constraints.txt` from the verified TCC tag when it is there and install as today otherwise, so the order inside the
  wave does not matter.
- **For information, no evidence against:** M3 (TCC's answer to N2), M7 (TCC reads the literal with `ast`; the verb
  stays, for diagnostics), M9 (TCC answers N3 and N8; N4 is answered by its §4.1 item 9).
