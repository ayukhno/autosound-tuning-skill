# Acceptance act 2 — skill W-12 · v3.3.0 release candidate

> The second acceptance run, at `17dd70e`. Its two findings were fixed at `fb9ddb5` and its scripts re-run on that head; the numbers are in the ledger.

Candidate: `wave-2026-10-30` at `17dd70e`. Fresh session, 2026-11-09. The tree was not changed (`git status` clean and HEAD `17dd70e`, checked at the end). The real home was not written (mtimes of `~/.claude`, `~/.claude/skills`, `~/.local/bin`, `~/.claude/skills/autosound-tuning` unchanged from before the first command). This act reports and decides nothing.

Working files, all under `hub/scratch/skill/accept2/`: logs in `logs/`, scripts, synthetic curves and projects in `work/`, clean HOME in `home/`. Curves are synthetic: `work/synth_solos.py` (the first act's generator, same seeds), `work/synth2.py` (a 2-way with a front sub).

## Verdicts

| area | verdict |
|---|---|
| **The blend, §9 `--move lower`, row → ledger** | **BROKEN on the runbook's command.** The row's `delta` writes `eq: []` over the EQ the chain fitted, while the woofers' HP and gain stay; the banked version re-scores 0.00 / 0.00 oct against the row's 1.32 / 1.84. New, B1. |
| **A row banked on a ledger that already holds a tune (`improve_existing`)** | **Banks as written, scores differently, in silence.** Field by field it is exact. The row's numbers do not hold when an undecided field sits on a joint's own channel: a 20 Hz BW12 subsonic left in the ledger takes the bass joint from 3.62 / 3.81 to 0.00 / 1.67 oct. Nothing says so. New, B2. |
| A1, the row's delta losing the carried EQ | **Fixed.** On the described path from a raw ledger, every banked field equals the row and every joint re-scores to the row's numbers. |
| Main test, field by field | **Passes.** 32 decided fields equal, 16 undecided kept, 0 differences, on both planted ledgers. |
| Main test, re-score | **Passes on a raw ledger** (within 0.04 oct or dB). **On a planted ledger the joints the planted fields touch do not reproduce** (B2). |
| Joint-by-joint runbook, §5 to §8 | Works end to end on the words: three joints, each `delta`, candidate, earn, `attest`. |
| 2-way with a front sub | Works, with and without `--align`; the row banks and re-scores. The runbook has no command line for this joint. |
| `--fixed` chain from a row with no `--align` | Works once a row exists; on the defaults that run comes back empty. |
| Version bench | Works: `table`, `loudness` through real `mosqito`, `lr-phase`, `round-check`. Its widths are not the row's widths (N1). |
| `project_repo.py save` | Works against a bare remote, four refusals seen. |
| Offer on the form (A4) | Fixed, four languages. |
| A2, A3, A6 | Fixed. Residue of A2 below. |
| A5 | Refusal's phrase fixed. Three small items unchanged. |
| A7 | Unchanged. |
| Clean-HOME install | Dry run clean; candidate placed as the installer places it; a real run not made. |

## 1. The first act's findings at this head

| finding | state | evidence |
|---|---|---|
| **A1** top row's delta loses the woofers' EQ | **fixed** | `work/joints/joint-midrange-tweeter.json` row 1: `w-L` delta `eq` has 4 bands, equal to its `channels`. `logs/compare-walk-r3.txt`: `RESULT differences: 0; decided fields 32; undecided kept 16`. Re-score below. |
| **A2** third joint empty on the runbook's command | **fixed in the runbook** | §5's command now carries `--front-lp`, and two paragraphs say what to do. Walked `--front-lp LR 24 1800` (twice the tweeter's Fs of 900 Hz): mid-tweeter 160 rows, `woofer-midrange joint held 1.21/2.01 oct (was 1.23/2.03)`. |
| A2 friction: empty run, retry, "every row above" | **fixed** | The first act's row reproduces the empty table (`logs/walk-14-empty.txt`); a second run on the same `--out` gives rc 0, no `--overwrite` refusal, no "Every row above". |
| A2 residue: candidates "not looked at" while the table is empty | **not changed** | Same run: `not looked at, past the shortlist 3314` beside zero rows. |
| **A3** a `REFUSE` row banks | **fixed** | Bass table has 0 `REFUSE`. Note: `the high-pass floor 57.2 Hz (1.1 x the woofer's Fs 52 Hz) took out the high-pass corners under it … 40, 45, 50, 57 Hz`. `--hp-bounds 40:50` refuses: `no filter pair left … above the floor 57.2 Hz`. `rew-tool-docs.md` and the runbook now agree. |
| **A4** form shows no needs/gives | **fixed** | `logs/walk-10-form.txt`: all four languages render what each way needs and gives, on the page. |
| **A5** the sheet's phrase against the refusal's | **fixed** | The refusal now prints `decision "ellipsoid positions: nine points skipped; the joints run on one point"`. `process._positions_asked` matches "ellipsoid" (`process.py:476`, read, not run through the gate). |
| A5 block B order against the round's order | **not changed** | The sheet is unchanged since the first act. |
| A5 `--plan` needs 63 titles typed | **not changed** | No helper. |
| A5 `intake.py set` traceback on a bad enum | **not changed** | `intake.py set … goal.desk_approach by_ear` → `__main__.IntakeError: goal.desk_approach is one of …`, a traceback. |
| **A6** `round-check` flags an exact sum | **fixed** | `ALL` still reads 1.79 / 7.10 windowed, 0.00 / 0.00 whole record, not flagged: `over 1 dB rms on both readings: none`. Planted errors are flagged on both readings: mid inverted in `L` 4.48 / 4.49, a woofer +6 dB in `ALL` 4.21 / 3.80. |
| **A7** `attest` on nothing proposed | **not changed** | `attest v_001` → `🟢 v_002 on SQ: applied nothing proposed`, banks a version. |
| A7 `contract.py check` and the running REW | not re-checked | Depends on the live REW. |
| #206 log tail before `pkill` | **fixed in the text** | `install.sh:1927`: `first save the end of its log (tail -50 ~/Library/Logs/autosound-tcc/tcc.log)`. Not seen against a live TCC. |
| #196 optional `docs-check` rule | **not built** | `git diff v3.2.0 HEAD -- scripts/docs-check.py` is empty. Marked optional in the issue. |
| #197, #200 decoder halves | **not built** | By the Arbiter's word, as the first act said. |

The first act's other "done" rows were not re-walked, except where the walk below passes through them.

## 2. The walk

**Install.** `HOME=accept2/home ./install.sh --terminal --dry-run`, rc 0, 78 lines, nothing written outside that HOME (`logs/install-dry.txt`). A real run reaches outside it (`upkeep.py` on the tools on PATH, sign-ins), so it was not made. The candidate was cloned at `17dd70e` to `$HOME/.claude/skills/.autosound-tuning-src`, with the two links the installer makes. Python: `venv-mosqito`.

**The joints, on the runbook's words** (3-way + centre + sub, nine points; `logs/walk-3-bass.txt`, `walk-4-wm.txt`, `walk-5-mt.txt`):

| joint | rows | time, peak RSS |
|---|---|---|
| bass | 116 | 10 s, 162 MB |
| woofer-mid `--fixed bass@1 --align --front-lp LR 24 1800` | 3 | 198 s, 377 MB |
| mid-tweeter `--fixed wm@1` | 160 | 12 s, 199 MB |

Each row went through `propose --on HEAD` → candidate → `attest` refused on the candidate as §7 says → `propose {} --on <candidate> --evidence --reviewed` → `attest` (`logs/walk-7-chain.txt`). The reviewer's file was a stand-in; no reviewer was called. Field comparison per row, 0 differences each (`logs/compare-walk-r{1,2,3}.txt`). `attest` left the fields as banked.

**Re-score from the banked versions, raw ledger.** `work/rescore.py` takes the chains the bench reads from the ledger and recomputes the search's own numbers: width on one crossing per side, power sum on the row's band (`logs/walk-9-rescore.txt`).

| joint | row | banked |
|---|---|---|
| bass (v_002, the bass row) | 3.62 / 3.81 oct | 3.62 / 3.81 |
| bass held under wm (v_005) | 3.57 / 3.85 | 3.57 / 3.85 |
| w-L ↔ m-L (v_005) | 1.23 / 2.03 | 1.23 / 2.03 |
| w-R ↔ m-R (v_005) | 1.74 / 2.34 | 1.74 / 2.34 |
| wm held under mt (v_008) | L 1.21 / 2.01, R 1.73 / 2.32 | same |
| m-L ↔ tw-L sum, left, right, centre (v_008) | +2.08 +1.89 +1.91 +2.41 | +2.07 +1.90 +1.94 +2.37 |
| m-R ↔ tw-R (v_008) | +2.23 +2.11 +2.19 +2.38 | +2.24 +2.15 +2.18 +2.38 |

**Main test: the top row of the last joint on a ledger already holding fields the rows did not decide.** `setup_import` banked v_001 with: `c` EQ, gain −4, INV, delay 1.5; `tw-L` EQ and gain −3; `tw-R` EQ and gain −2; `sw` EQ and a 20 Hz BW24 high-pass. Ledger B adds `w-L` INV. Row 1 of mid-tweeter banked `--on HEAD`.

Field by field, `logs/compare-main-A.txt` and `-B.txt`: `RESULT differences: 0; decided fields 32; undecided kept 16`, both ledgers. Everything the row decided is equal. Everything it did not is as the ledger had it, the channel `c` whole. `sw` polarity, gain, LP and delay are the row's; `sw` HP and EQ the ledger's.

Re-score of that version (`logs/rescore-main-A.txt`, `-B.txt`, and one field at a time in `logs/walk-12-isolate.txt`, `walk-19b-subsonic.txt`):

| planted, nothing else | bass joint, row 3.62 / 3.81 | w-L ↔ m-L, row 1.21 / 2.01 | m-L ↔ tw-L, row sum +2.08 |
|---|---|---|---|
| none (raw ledger) | 3.57 / 3.85 | 1.21 / 2.01 | +2.07 |
| `sw` EQ, PK 45 Hz −4 dB Q4 | 1.98 / 2.93 | 1.21 / 2.01 | +2.07 |
| `sw` HP 20 Hz BW24 | 0.00 / 0.00 | 1.21 / 2.01 | +2.07 |
| `sw` HP 20 Hz BW12 | 0.00 / 1.67 | not re-printed | not re-printed |
| `sw` HP 15 Hz BW12 | 0.00 / 1.82 | not re-printed | not re-printed |
| `tw-L` gain −3 dB | 3.57 / 3.85 | 1.21 / 2.01 | +1.89 |
| `tw-L` EQ PK 5 kHz −2 dB | 3.57 / 3.85 | 1.21 / 2.01 | +2.07 |
| `w-L` INV | 0.00 / 0.00 | **0.00 / 0.00** | +2.07 |

**2-way with a front sub** (`sw-f`, `logs/walk-21-2way-joints.txt`): bass 120 rows, `--joint woofer-tweeter --fixed bass@1` 41 rows. `--align` 60 rows. Banked: 0 differences each; top-joint sums within 0.10 dB of the row (no align, the centre group is the 0.10), 0.03 dB (align). §1 mentions this joint in a sentence; §5's table has no command for it. The mid-tweeter command works with the joint's name changed.

**`--fixed` chain from a row with no `--align`** (`logs/walk-13a`, `walk-14-noalign`, `walk-23-noalign-chain`). The woofer-mid run with `--front-lp LR 24 1800` on the defaults returns no rows: `leak limit 34568, no crossing 101, no in-phase band 4258, dip 77, the bass joint below could not be held 33, not looked at, past the shortlist 6455`. The first act's no-align run was empty too. Loosened to get a row (`--no-leak --no-dip --bass-drop 6`, narrower bounds), the chain goes through: mid-tweeter 93 rows, 0 field differences. No EQ is stated on the woofers, and the row prints their empty EQ as it was. `wm` re-scores 1.25 / 1.42 against the row's 1.26 / 1.42. The bass joint reads 0.00 / 0.00 as that row said it would, under my `--bass-drop 6`.

**Bench.** `table` on the banked versions: mid-tweeter sums within 0.05 dB of the row. `loudness` with real `mosqito`: v_005 −0.55 dB, v_010 −0.62 dB against v_002, labelled Zwicker. `lr-phase` and `round-check` as in the table in section 1 (`logs/walk-8-bench-clean.txt`, `walk-16-bench2.txt`).

**`project_repo.py save`** against a bare local remote (`logs/walk-6-repo.txt`): `✗ no remote`, `✓ would send … 25 files`, `✓ sent to origin: commit … (25 files) and 1 waiting commit; 1 housekeeping file stays out`, `✗ nothing to send`, `✗ pull first: the remote has 1 commit this copy does not. Nothing changed`, `✓ sent` after the pull. `.critic-env` and the skill link not in `git ls-tree` of the remote.

## 3. New

### B1. `--move lower`: the row wipes the fitted EQ and banks as something else

§9's command, on the chain's `v_010`, §7's banking (`logs/walk-13c-move-lower.txt`, `walk-14-move.txt`, `walk-17-wmfixed.txt`):

| `--fixed` | rows | what the row's delta says | re-score of the banked version | sheet |
|---|---|---|---|---|
| the mid-tweeter row (`--fixed mt@1 --move lower`) | 71 | `w-L: {lp, ta_ms, eq: []}`; no `hp`, no `gain_db` | w-L ↔ m-L 0.00 / 0.00 against the row's 1.32 / 1.84; bass 0.00 / 0.00 | `w-L EQ bands: PK 265.12 … → (no bands)` |
| the woofer-mid row (`--fixed wm@1 --move lower`, narrowed bounds) | 80 | `w-L` and `m-L` both `eq: []`, no gains, no mid LP | 0.00 / 0.00 against 1.33 / 2.95; mt sum −3.17 against +2.08 | EQ cleared on all four |
| mid-tweeter + bass row, full grid | 0 | no rows | | |
| woofer-mid + bass row, full grid | 0 | no rows | | |

What happens: with one `--fixed` row the woofers are searched raw (`channels.w-L = {hp: null, gain_db: null, eq: []}`), which the row states. `eq_stated` takes the `--fixed` row's stated EQ on channels this run does not hold (`joint_search.py:3936`, `set(eq_bands) | _eq_decided(fixed_rows)`), so `_ledger_delta` (line 2991) writes `eq: []` for them. `hp` and `gain_db` are absent, so the ledger's stay. The banked woofer therefore has the old HP and gain and no EQ: neither what was scored nor what the ledger had.

Control: the same row banked on the raw v_001, where the ledger has no HP, gain or EQ on the woofers, re-scores exactly (1.32 / 1.84, 1.62 / 1.96, `logs/walk-24-move-on-raw.txt`). The row is honest about a raw chain; the delta is wrong on any version that has the woofers set. Against the runbook: §7, "What a row did not decide stays out of its delta and the ledger keeps its own"; "An `--align` that fitted no cuts states `eq: []`". No `--align` ran here. The table's "Every row above also takes" does not list the woofers, and the note only says the bass joint is not in the model. The sheet does show the bands going to none.

`--move upper` was not walked. Both ways of holding the bass came back empty on this synthetic car, so §9 with the bass row held could not be walked on the default grid.

### B2. On a ledger that already holds a tune, the row's numbers are not the banked version's

The search does not read the ledger: `joint_search.py` has no path to the ledger's versions outside its selftests, so a row is computed from the raw solos and the `--fixed` rows only. §7's rule keeps every undecided field. Both are as written. Together, on a car whose HEAD is the current tune, the banked version plays differently from the row, by the amounts in the table above. Worst case by size: `w-L` INV takes the joint to 0.00 / 0.00, and the row's `channels` reads `NORM` while the ledger's INV stays (the printed table does not show the woofers' polarity). Most likely case: a subsonic on the sub, in the ledger and not in the row. The recipe's own BW12 at 15–20 Hz takes the bass joint's worst point to 0.00. Not on this path: a raw v0, whose undecided fields are neutral.

Nothing tells the person. `propose` prints only the changes; §7 says the ledger keeps its own and does not say that the row's numbers assumed those fields neutral. `goal.mode: improve_existing` and §7's "the current tune on a car that is already tuned" put this on the described path. A person can avoid it by first putting those fields to neutral on the HEAD a row is banked on; nothing in the runbook says to.

Which fields it can be, by the row's own delta: the sub's HP and EQ, the woofers' polarity, the tweeters' gain, EQ and LP.

### N1. Misleads a little: the bench's widths are not the row's widths

The same banked version v_005: bench `w-L ↔ m-L 1.47 / 2.29`, `w-R ↔ m-R 1.95 / 2.48`; the row and my re-score 1.23 / 2.03 and 1.74 / 2.34. Bass: bench 2.91 / 3.00 (it stops at ±1.5 oct, `WIDTH_SPAN_OCT`), the row 3.62 / 3.81. The bench takes a crossing per point (`version_bench.py:946`), the search one per side. Neither the runbook nor `rew-tool-docs.md` says the two read differently, and §7 sends a person from one to the other. The cause of the 0.2 oct is my reading of the code; I did not isolate it further.

### N2. Hinders: two empty tables with thousands of candidates "not looked at"

See A2's residue and the no-align run above: `6455 not looked at` beside zero rows. I did not establish whether `--shortlist` would give rows there.

## Not checked

- Real REW, a real car, the Passat replay at this head. All curves here are synthetic, one generator, two layouts.
- A real install: `pip --user`, the engine fetch, `upkeep`, sign-ins, the desktop app, Windows, `pwsh`.
- `--move upper`, and §9 with a bass row held (no rows on the default grid here).
- `--single-point` above the bass, the stage conditions' off-flags, a DSP other than the Helix, `goal.desk_approach: both` with the real engine.
- The reviewer's file was a stand-in; `autosound_ai.py critic` was not called.
- `propose` with no `--on` after a candidate, `variant switch`, TCC's side, a live TCC during an update: not re-walked.
- The whole test suite, by instruction. CI was not read at this head.
