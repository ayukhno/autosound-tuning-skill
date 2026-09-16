# TODO — maintainer's backlog

Work that is understood but not yet due. Not the roadmap: `ROADMAP.md` is product direction for
people who use the method, this is engineering debt for whoever maintains it. An item here carries
**what would make it due**, because an item whose trigger is "when someone remembers" is the kind
that gets found again three months later as a surprise.

## How an item is closed

**An item dies with a status line, never by being deleted.** Every item carries `**Status**:` on
the line under its heading — `open` · `doing` · `done` · `dropped` — and a closed one keeps its
text where it stands, with what closed it written into that line.

Deleting is what this file did until 2026-09-06, because no item had yet been closed and the form
had never been needed. It loses the one thing worth keeping: a deleted item is indistinguishable
from an item that never existed. The counter changes and nobody sees a "done" — the history stays
in git, and the board that reads this file (autosound-hub, `scripts/board-collect.py`) does not
read git. The form comes from hub HUB-024; the shape of the status line is the board's, so that
this file is read rather than guessed at.

**A `done` line carries a COMMAND, not a description** — the same rule as closing a ticket on the
bus (`hub:governance/PROTOCOL.md` §4.3): something another person re-runs to see the claim for
themselves. "Snapped the proposal to the sample grid" is a description and is worth nothing;
`python3 rew_tool/state/apply.py … --sheet` is the claim. `dropped` carries the reason it will not
be done — and specifically why it cannot be fixed by doing the work, since anything else is just
`open` with a tired author.

    ## S-007 · Something that was due and is now finished
    **Status**: done 2026-09-06 · `scripts/run-selftests.sh` (53/53) · commit `abc1234`

The `**Due when:**` line stays as it was written. An item that turned out to be due for a reason
nobody predicted keeps its original trigger and says so in the status line: what actually brought
it in is worth more than a tidy record.

---

## S-001 · `deployment.py` cannot tell a DECLARED pin from a split

**Status**: open

**Due when:** the first tuning project is pinned to a version and still being worked on. Not before.

**State today.** `rew_tool/deployment.py` refuses (exit 3) whenever two reachable deployments are
different commits. That is right for a split nobody chose, and wrong for a pin somebody chose on
purpose: a run held at `v3.0.33` for reproducibility will be refused every session, on the thing it
is doing correctly. A check that cries wolf on a deliberate arrangement teaches people to skip it —
and this module's own `verdict()` already carries that argument, in the paragraph explaining why
the grouping key is the sha and not the path. The same reasoning applies one level up, and this
item is where it lands.

**The form is already decided**, and it is the one shape on this machine that never drifted:
`autosound-tcc` carries the skill as a submodule, so the CONSUMER records the sha it expects and
git compares the record against what is checked out. Generalise that:

* the project records the version it is pinned to — a field beside the other project facts
  (`rew_tool/project.py`, `project.json`), not a new file and not a second place;
* a reachable deployment matching the record reads as **agreement**, not disagreement;
* a deployment that does NOT match the record is a harder failure than today's exit 3 — the run
  says which version its numbers were computed on, and something else is on the path;
* a project with no record behaves exactly as now. Absent is not the same as satisfied, and a
  silent default would put this module back where it started.

**What must not happen:** the pin becoming declarable in a file nobody compares against. That is
the failure this module was written for — the 2026-08-13 rule about the personal symlink lived in
a memory file, was contradicted by `install.sh:774`, and nothing noticed for thirteen days. A
declaration is only worth having where a check reads it.

**Trigger is live, not written down:** `deployment.py` already names this gap in its refusal when
one of the disagreeing checkouts is held (`DETACHED`), and points here. It arrives with the case.

**Raised** 2026-08-29, out of autosound-hub HUB-006, by the person whose run was pinned.

---

## S-002 · A proposed delay is printed in ms the device cannot hold

**Status**: open

**Due when:** the first alignment sheet is entered by hand and the verdict is read at a tweeter
joint — or when the delay quantiser's direction (below) is measured, whichever comes first.

**State today.** The Helix quantises a typed delay to a **whole sample** at the processing rate
(10.4167 µs at 96 kHz; bench 2026-09-02, fact 3): 0.05 ms lands on 5 samples = 0.0521 ms. The
settings sheet (`state/apply.py`) keeps ms as the source of truth and derives samples for the rate,
so the samples column IS what the device holds — but `predict --align` searches on a 1000/rate grid
and reports `tau_ms` to four decimals, and `setup_import` checks a transcription against the
profile's `step_ms` (0.01), which is the UI's entry step and not the grid the device keeps. Worst
case half a sample per channel, 5.2 µs — 1.8 mm, or 19° at 10 kHz. Small, real, and unstated.

**The form:** snap a proposal to `round(ms × rate / 1000)` samples before it is printed, print the
ms the device will actually hold beside the ms that was asked for, and make `setup_import`'s grid
check use the sample grid when the profile says `delay.sample_quantised`. **Not before** the
direction is known: the two fractions measured (4.800 and 30.720 samples) both sat above the
half-sample, so rounding and truncation upward are not separated (`_open_questions` in the Helix
profile) — a snap in the wrong direction is a whole sample off, worse than no snap.

**Raised** 2026-09-05 from the Resonalyze-fork bench handoff (fact 3).

## S-003 · `apf1_response` models the typed corner; the Helix places a lower one

**Status**: open

**Due when:** an AP1 band is prescribed on this hardware above ~2 kHz, or a second processor is
measured and the deviation turns out to be Helix-specific.

**State today.** Four points, one rig: typed 250 / 1000 / 4000 / 8000 Hz land at 248.8 / 993.2 /
3936 / 7611.6 (−0.5 / −0.7 / −1.6 / −4.9 %); AP2 in the same session within 0.05 %. The shape is a
clean first-order all-pass, so it is the frequency and not the form, and no simple law fits — not a
constant percentage, not an offset, not the un-prewarped substitution (7824 at 8 kHz). Cost of
modelling the typed value: 0.4° at 1 kHz, 0.9° at 4 kHz, 3.0° at 8 kHz. The method already prefers
AP2 (REW cannot mirror AP1 either), so today this is a documented deviation
(`helix-phase-allpass.md` §3, the `apf1_response` docstring), not a wrong number in a tune.

**The form, if it becomes due:** a per-profile correction table (typed → placed) read by
`eq_complex` for `APF1` on a profile that carries it — not a law, since none fits, and not a global
change, since it is one processor's. Four points are too few to interpolate honestly between; the
bench would need the octaves in between first.

**Raised** 2026-09-05 from the same handoff (fact 1).

## S-004 · The phase control's ceiling is known at one rate

**Status**: open

**Due when:** a 48 kHz Audiotec-Fischer unit (a MATCH, or an older HELIX) is on a bench.

**State today.** `phase_rotation.MAX_CORNER_FRACTION = 3/16` — 18 kHz at 96 kHz. Three
recoveries at two references gave 18007–18010 Hz, which is 3/16 of the rate AND an absolute 18 kHz
within the spread; one rate cannot separate them. The rate-relative reading is taken (as Resonalyze
does); on a 48 kHz unit it predicts a 9 kHz ceiling where the absolute reading predicts 18 kHz, and
every setting at a reference above ~500 Hz would differ between the two. **One measurement decides
it**: any capped setting at a high reference on a 48 kHz device — the fitted corner is either 9 kHz
or 18 kHz. The constant is the one line to correct; the selftest's 48 kHz case (9 kHz, 7674 Hz for
90° at 5 kHz) is the assertion that would flip with it.

**Raised** 2026-09-05 from the same handoff (§1).

## S-005 · The alias guard reads the whole record; above 1 kHz the record is the cabin

**Status**: open

**Due when:** a mid↔tweeter junction proposed by `predict.py align` lands 0.75 cycles or more from
a tune verified by ear and measurement. The record already carries `chosen`, `arrival_ms` and
`cycles_off`, so the case arrives with its own evidence.

**State today.** `align_joints` does not trust the sum-loss score alone: `arrival_difference_ms`
(the band-limited matched-filter envelope of A·conj(B)) says where the physical delay is, and a
score optimum 0.75 cycles or more away from it is recorded as an alias while the physical candidate
is proposed. That is the right shape — Resonalyze's #128 (`bd51791`) arrived at the same one — and
#128 measured its limit: at junctions above ~1 kHz a correlation over the FULL record is dominated
by the cabin, and in half of seven archived cabins' 1.3–2.9 kHz cells its extremum sat 3.4–4.7
periods from the owner's tune while passing every trust gate. Their fix reads the seed off
direct-sound cuts (one to two periods behind each wavefront) and, where two witnesses disagree by
a hair, lets the coherence bands vote. Our witness is validated at the bottom (an 88 Hz sub 12 ms
late, where one cycle is 11.4 ms) and on one mid↔tweeter junction (0.9 ms read where the impulse
peaks were 0.9 apart); nothing here has measured it across cabins at 2 kHz. **The score cannot be
the tiebreaker:** on #128's own numbers the alias scores HIGHER than the hand tune on `score_db`
(v6 L: −2.24 against −2.33), so a wrong witness is not caught by the ranking.

**What it is not:** a reason to port their search. The direct-sound cut is a property of the
MEASUREMENT — a gate on the solos before they reach `predict` — and the cheapest first move is to
read the arrival on gated solos and compare: one junction, one cabin, before any code.

**Raised** 2026-09-05 while reading the four upstream commits behind the re-pin of `sum_loss`
(CHANGELOG, Unreleased).

## S-006 · The junction ripple is read, not scored

**Status**: open

**Due when:** a real junction reads `sum_loss_avg_db` better than −0.5 dB with `sum_ripple_db`
above 3 dB — a pair that adds coherently into a hump. Until one does, the number has not earned a
place in the ranking.

**State today.** `dsp_math.sum_loss` returns `ripple_db` (upstream `MeasureJunctionSpectrum`,
`56b07c8` / #172): the log-weighted RMS of the summed level about its mean over the junction band.
`predict` prints it in the junction table beside score and worst null. `score_db` does not see it
and `align_sum_loss` does not search on it. Upstream's own reason for the number — "two drivers
both wide open at the corner sum coherently into a 6 dB hump and lose nothing" — is a CROSSOVER
question, not a delay one: at fixed crossovers the phase-blind sum |A|+|B| does not move with
delay, so the only part of the ripple a delay search could change is the loss, which the score
already reads. Where it would matter here is `xover_select`, which ranks realizations against a
target and not by junction reading. On measured solos the ripple also carries the room, so a
threshold set on a synthetic pair would be wrong in a car; the trigger above is a real case, not a
number.

**Raised** 2026-09-05, same reading as S-005.

## S-007 · The README never says the EQ reaches the processor without retyping it
**Status**: open

**Due:** in the documentation pass before v3.1.0, when the READMEs are reworked for the release.

"Writes nothing to your DSP — you enter it" reads as "type every filter in by hand", and that is not
the work it is. REW exports the EQ as a file the Helix PC-Tool imports in one go, and for processors
without a file import (Musway, ESX, Zapco) the
[REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) pastes it.
Today `FAQ.md` links the assistant and nothing in `main` mentions the Helix import or which processors
the helper covers.

Where it came from: the unmerged branch `docs/readme-review` (2026-08-17, nine commits, last
`18eee3b`), whose README said: *"Never touches your processor: nothing changes in the car unless you
put it there. That does not mean retyping everything: REW exports your EQ as a file the Helix PC-Tool
imports in one go, and a copy-paste helper covers processors without file import, such as Musway,
ESX and Zapco."* The rest of that branch is superseded (two awards of five, English only); this item
keeps the one point worth keeping.

Done looks like: that point beside "writes nothing to your DSP" in all four READMEs, checked against
the tools as they stand then — whether the Helix PC-Tool still imports REW's file, and which
processors the helper covers.

## S-008 · `install.ps1`'s beta order has not yet met a real candidate
**Status**: open

**Due:** when the first `beta-v3.*-rc1` is published.

`Select-NewestOnChannel` in `install.ps1` is READ by `scripts/installer-consistency.py` (its tag shapes
and sort key), not run: CI runs `install.sh`'s `newest_on_channel` on six fixed cases, on Linux and,
since v3.0.51, on `windows-latest` too — the bash half both times. The Windows VM run of 2026-09-13
went through the beta branch with no candidate published, so it could only return the newest release.

Done looks like: `install.ps1 -Channel beta -DryRun` on Windows naming `beta-v3.1.0-rc1` over `v3.0.x`,
and `v3.1.0` over its own candidates once released — or `installers-windows` in CI running the
PowerShell function itself on the same six cases, which would close this before any candidate exists.

## S-009 · `install.ps1` lists the app as "will install" right after installing it
**Status**: open

**Found** 2026-09-14 on the Windows VM, in one PowerShell window: the `-Channel beta` run from `v3.0.52`
ended "OK   installed" and "OK   Autosound TCC -- on your Desktop and in the Start Menu"; the next run
of the same line (from branch `test-fixes-2026-09-14`) opened with "--   Autosound TCC, the desktop app
will install". Recorded only — not diagnosed (hub `governance/WAVES.md` §1).

Done looks like: a second run in the same window lists the app as already on the machine.

## S-010 · A terminal window pops up during the Windows install
**Status**: open

**Found** 2026-09-14 on the Windows VM, running `install.ps1 -Channel beta` from branch
`test-fixes-2026-09-14`: during the install a terminal window appears — the user recognises it as the one
the app opens at its own start. Whether that is expected is not known yet; whose it is (`install.ps1`
calling the app, or the app itself) is for the wave review. Recorded only (hub `governance/WAVES.md` §1).

**When:** right after the app step prints "version v0.1.39 (beta channel)" and "OK   installed" — before
the line about the Desktop and Start Menu shortcuts.

Done looks like: the install either shows no such window, or says what it is when it opens.

## S-011 · Close the wave on branch `test-fixes-2026-09-14`
**Status**: done 2026-09-16 · `git ls-remote --tags origin v3.0.53` · merged `--ff-only` into `main`

**Due:** when the user says the wave is tested (hub `governance/WAVES.md` §1).

On the branch: the false "the update did not take" fix (confirmed on the Windows VM), CI once per wave
(hub #149, HUB-065), the findings S-009 and S-010, one title parser (#39: #33, #34, hub #152), the records that
could not hold what the method teaches (#40: #29, #30, #31, #32, #36), and one reviewer door
(#41: #28, hub #150; the shell wrappers are gone). Left: the review with the user of what goes in,
the full suite, the version bump and CHANGELOG entry on the branch, one PR, `--ff-only` into `main`,
the tag. Hub #149 closes after that merge, once the `gate` job on `main` is seen skipping the tests.

## S-012 · Run v3.0.53 on the Windows VM
**Status**: open

**Due:** 2026-09-17 — the user's word ("the Windows run, for tomorrow"). v3.0.53 is published with
one `install.ps1` line changed that no VM has run, and the reviewer fix of hub TCC-014 was proven on
macOS only. Each command below is one line, for a PowerShell paste.

1. **Update an install that has v3.0.52:**
   `irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.53/install.ps1 | iex`
   — the Checking step names `v3.0.53`, no "the update did not take" warning, and the last block
   prints `python3 "C:\Users\<you>\.claude\skills\autosound-tuning\scripts\autosound_ai.py" doctor`.
2. **That line, pasted as printed** — `doctor` runs (PowerShell quoting holds) and names the channel.
3. **The reviewer through `agy`, from an ordinary PowerShell, not inside Claude Code** (the fix of
   TCC-014: the prompt goes on stdin, nothing for agy to read):
   `$env:AUTOSOUND_PROJECT_DIR="C:\Users\<you>\_autosound\testTCC8"; $env:AUTOSOUND_CRITIC_MODEL="gemini-3.8-flash-low"; "Translate into Ukrainian, one word: stage" | Out-File -Encoding utf8 $env:TEMP\q.md; python3 "$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py" ask $env:TEMP\q.md`
   — an answer and `>> REVIEW_FILE: process\reviews\…-ask.md` in the project, no `read_file` denial,
   exit 0.
4. **Nothing left in the method's checkout:**
   `git -C "$HOME\.claude\skills\.autosound-tuning-src" status --short` — empty.
5. **What S-009 and S-010 look like on this version** — does the plan still say "will install" for
   the app right after installing it, and does a terminal window still pop up? Write down what is
   seen, under those items.

6. **The wave branch's installer, dry** (gh comes only with `-GitHub` now, no question):
   `& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/wave-2026-09-16/install.ps1))) -DryRun -Terminal`
   — no "Back projects up to GitHub?" question; on a machine without `gh` an "Optional: -GitHub also
   installs GitHub's gh…" line under the plan; with `-GitHub` added, gh is in the plan.

Done when each numbered line has its observation written here, with the VM and the date.

## S-013 · Each REW reader names the smoothing it reads
**Status**: open

**Due:** with the user — which tool reads what is a method decision, not a code one.

`rew_api.get_fr(mid, smoothing=…)` asks REW for a smoothing on the read and leaves the Arbiter's view
alone (hub TCC-015, 2026-09-16). The callers below still call it without one, so what they compute
depends on what the person has set for viewing — a 1/6 view and a 1/24 view give different numbers:

- `rew_tool.py:286` (`analyze-batch`, band means), `:663-664` and `:706` (joints), `:787`
- `verify.py:99` (the post-sweep checks), `verify_prediction.py:135`, `ear_suspects.py:259`, `spot_check.py:80`

Raw (`"None"`) answers linear, ~55k points per sweep, so a band MEAN over it weighs the treble more
than today's log-spaced points do — a tool that averages over points cannot just switch. Recommended
per tool, for the user to confirm: `"1/48"` where a tool wants today's log-spaced shape without the
view's smoothing (`analyze-batch`, joints, `verify`), `"1/6"` where it reads tone (`ear_suspects`),
`"None"` where it does its own smoothing (`verify_prediction`). Done when every call names one and a
selftest pins the query each tool sends.

## S-014 · `omp` opt-in — asked once more, with its history
**Status**: open

**Due:** 2026-09-17, a question for the user before anything changes.

On 2026-09-16 the user chose "gh off, omp only with a flag" from a menu (docs/SIMPLIFICATION-2026-09-16.md
§7). The gh half is done on `wave-2026-09-16`. The omp half would reverse a decision taken twice —
2026-08-19 and 2026-09-09 — for a reason the menu did not show: *the person who wants omp is the person
who does not know the flag exists* (issue #25, and the comment above `WANT_OMP` in `install.sh`). What
changed since: the README and FAQ now name `omp` and `--no-omp` at the install step (issue #25's
2026-09-09 comment). Ask: keep omp on with the app, or make it `--with-omp` only. Close #25 either way.
