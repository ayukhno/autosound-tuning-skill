# TODO — maintainer's backlog

Work that is understood but not yet due. Not the roadmap: `ROADMAP.md` is product direction for
people who use the method, this is engineering debt for whoever maintains it. An item here carries
**what would make it due**, because an item whose trigger is "when someone remembers" is the kind
that gets found again three months later as a surprise.

## How an item is closed

**An item dies with a status line, never by being deleted.** Every item carries `**Status**:` on
the line under its heading — `open` · `doing` · `waiting` · `deferred` · `done` · `dropped` — and a
closed one keeps its text where it stands, with what closed it written into that line.

The board reads the **first word** after `**Status**:` (hub `PROTOCOL.md` §4.10, HUB-066); the rest of
the line is free text. Two words are not open work and are not closed either: **`waiting`** — released,
waiting for the user's test (the line names the version and what to test); **`deferred`** — put off by
the user's word (the line quotes it and says what would bring it back). `done` and `dropped` close;
any other word is open work.

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

**Status**: deferred 2026-09-17 · the user, at the wave's review: "agreed — and recall we had the `frozen` mode, this seems to be about such cases"; it comes back with the first `frozen` run (hub `docs/PLAN.md` §8)

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

**The case already has a name** (the user, 2026-09-17): hub `docs/PLAN.md` §8 `frozen` — a competition run on its own
repo, the method's pin fixed for the whole run. Its pin is the declaration this item wants read; the hub has not built
the mode yet (`hub-join-machine`, `hub-add-project`), so the first `frozen` run is when this is due.

**Trigger is live, not written down:** `deployment.py` already names this gap in its refusal when
one of the disagreeing checkouts is held (`DETACHED`), and points here. It arrives with the case.

**Raised** 2026-08-29, out of autosound-hub HUB-006, by the person whose run was pinned.

---

## S-002 · A proposed delay is printed in ms the device cannot hold

**Status**: dropped 2026-09-17 · handed to research: `gh issue view 156 --repo ayukhno/autosound-hub` (SKL-039) — the user: a research question, not skill work until a measurement or an RFC comes back through the skill's gate; the text below stays as the question's record

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

**Status**: dropped 2026-09-17 · handed to research: `gh issue view 156 --repo ayukhno/autosound-hub` (SKL-039) — the user: a research question, not skill work until a measurement or an RFC comes back through the skill's gate; the text below stays as the question's record

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

**Status**: dropped 2026-09-17 · handed to research: `gh issue view 156 --repo ayukhno/autosound-hub` (SKL-039) — the user: a research question, not skill work until a measurement or an RFC comes back through the skill's gate; the text below stays as the question's record

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

**Status**: dropped 2026-09-17 · handed to research: `gh issue view 156 --repo ayukhno/autosound-hub` (SKL-039) — the user: a research question, not skill work until a measurement or an RFC comes back through the skill's gate; the text below stays as the question's record

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

**Status**: dropped 2026-09-17 · handed to research: `gh issue view 156 --repo ayukhno/autosound-hub` (SKL-039) — the user: a research question, not skill work until a measurement or an RFC comes back through the skill's gate; the text below stays as the question's record

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
**Status**: done 2026-09-17 · `grep -n "REW-EQ-CopyPaste-Assistant" README.md` — the README's first list says the EQ is loaded, not retyped (the user asked for README and FAQ to be current, English first; commit `6fa281a`)

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
**Status**: dropped 2026-09-17 · the beta channel is not being developed (the user: releases go out as tags, and no `beta-v3.*-rc` is planned), so the trigger never comes; `Select-NewestOnChannel` stays as it is, read by `scripts/installer-consistency.py`

**Due:** when the first `beta-v3.*-rc1` is published.

`Select-NewestOnChannel` in `install.ps1` is READ by `scripts/installer-consistency.py` (its tag shapes
and sort key), not run: CI runs `install.sh`'s `newest_on_channel` on six fixed cases, on Linux and,
since v3.0.51, on `windows-latest` too — the bash half both times. The Windows VM run of 2026-09-13
went through the beta branch with no candidate published, so it could only return the newest release.

Done looks like: `install.ps1 -Channel beta -DryRun` on Windows naming `beta-v3.1.0-rc1` over `v3.0.x`,
and `v3.1.0` over its own candidates once released — or `installers-windows` in CI running the
PowerShell function itself on the same six cases, which would close this before any candidate exists.

## S-009 · `install.ps1` lists the app as "will install" right after installing it
**Status**: done 2026-09-17 · the branch's installer on the Windows VM: "OK   Autosound TCC, the desktop app -- updates to its newest release" on a machine with the app · commit `1b77afd`

**Found** 2026-09-14 on the Windows VM, in one PowerShell window: the `-Channel beta` run from `v3.0.52`
ended "OK   installed" and "OK   Autosound TCC -- on your Desktop and in the Start Menu"; the next run
of the same line (from branch `test-fixes-2026-09-14`) opened with "--   Autosound TCC, the desktop app
will install". Recorded only — not diagnosed (hub `governance/WAVES.md` §1).

**Seen again** 2026-09-17 on `v3.0.54` (S-012): the real run and the two app dry-runs after it, in one
window, each list "--   Autosound TCC, the desktop app     will install" while the real run ended "OK
installed". Recorded only.

Done looks like: a second run in the same window lists the app as already on the machine.

## S-010 · A terminal window pops up during the Windows install
**Status**: done 2026-09-17 · not seen on the stable channel during S-012's install (the user's watch; transcript `~/Downloads/тест/s012.txt`) — closed at the wave's review

**Found** 2026-09-14 on the Windows VM, running `install.ps1 -Channel beta` from branch
`test-fixes-2026-09-14`: during the install a terminal window appears — the user recognises it as the one
the app opens at its own start. Whether that is expected is not known yet; whose it is (`install.ps1`
calling the app, or the app itself) is for the wave review. Recorded only (hub `governance/WAVES.md` §1).

**When:** right after the app step prints "version v0.1.39 (beta channel)" and "OK   installed" — before
the line about the Desktop and Start Menu shortcuts.

**Not seen** 2026-09-17 on `v3.0.54` (S-012 step 1, the stable channel, app v0.1.39): no terminal window
during the install, by the user's watch. Found on the beta channel, not seen on the stable one; whether
that closes it is for the wave review.

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

## S-012 · Run v3.0.54 on the Windows VM
**Status**: done 2026-09-17 · the transcript `~/Downloads/тест/s012.txt` and step 2's output below · open from it: S-009 (seen again), S-015 (agy not reached)

**Due:** after the other S-items of this wave are done — the user's word on 2026-09-17 ("after Sxxx"), so one VM run covers the final state of `wave-2026-09-16`, released as v3.0.54 on 2026-09-17. First asked for 2026-09-17 ("the Windows run, for tomorrow"). v3.0.53 was published with
one `install.ps1` line changed that no VM has run, v3.0.54 with its `gh` and `omp` defaults, and the reviewer fix of hub TCC-014 was proven on
macOS only. Each command below is one line, for a PowerShell paste.

1. **Update an install that has v3.0.52 or v3.0.53:**
   `irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.54/install.ps1 | iex`
   — the Checking step names `v3.0.54`, no "the update did not take" warning, and the last block
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

6. **The released installer, dry** (gh comes only with `-GitHub` now, no question):
   `& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.54/install.ps1))) -DryRun -Terminal`
   — no "Back projects up to GitHub?" question; on a machine without `gh` an "Optional: -GitHub also
   installs GitHub's gh…" line under the plan; with `-GitHub` added, gh is in the plan.
7. **omp only with `-WithOmp`** (S-014), same dry-run form: without `-Terminal`, no omp in the plan and an
   "Optional: -WithOmp also installs omp…" line; with `-WithOmp`, omp in the plan; with `-WithOmp
   -Terminal`, the line "-WithOmp: omp is for the app's model picker … left out." at the top and no error.

Done when each numbered line has its observation written here, with the VM and the date.

**Observations 2026-09-17** — the Windows VM (Parallels, ARM64), Windows PowerShell, in one window;
transcript `~/Downloads/тест/s012.txt` on the Mac:

1. Updated: the method block reads "version v3.0.54 / already installed -- updating to v3.0.54", no
   "the update did not take" warning, no GitHub question (gh is already here, so its sign-in came at the
   end and was skipped with `s`), and the `autosound_ai.py" doctor` line printed under "When you have
   time". The Checking step says "the tuning method (3.x)" and names no version on any run — the
   expectation above asked for more than it prints.
2. The printed line, pasted as is, ran (`doctor`, exit code 1). It names the channel — "▶ Рецензент:
   gemini-3.8-flash-low → провайдер google", "▶ Режим роботи: АВТОМАТИЧНИЙ (через API google)" — and ends
   "ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗" with: no `.critic-env`; "Контекст autosound_context.md НЕ ЗНАЙДЕНО"; key
   `GEMINI_API_KEY` found, "OLD format (AIza…, 39 chars)", its model list "HTTP Error 400"; "Знайдено
   локальний CLI" `gemini` for google, anthropic AND openai; the live call "API key not valid".
3. **agy was not reached.** Exit 4, a refusal as designed: the reasons were listed — "API google: … HTTP
   Error 400: Bad Request — API key not valid" and "CLI 'gemini': Warning: 256-color support not
   detected … Ripgrep is not available … Error when talking to Gemini API" — the package went to
   `process\reviews\2026-09-17T10-24-06-ask-package.md` and the clipboard, and nothing was filed as a
   review. The CLI rung ran `gemini`, so the stdin fix of TCC-014 is still unproven on Windows (S-015).
   The garbled Cyrillic and the NativeCommandError lines came from the probe's own `2>&1 | Out-Host`.
   **Re-run the same day, after the user environment was cleaned (S-015)**, in a new window, with the key
   file set aside for the one run so the API could not answer first: ">> Виклик локального CLI 'agy'
   (google)...", the answer "етап", `REVIEW_FILE: process\reviews\2026-09-17T10-51-40-ask.md`, exit 0 —
   agy took the prompt on stdin on Windows (TCC-014's fix).
4. `git status --short` in the method's checkout: empty.
5. S-009 seen again (under that item). S-010 not seen: no terminal window (under that item).
6. `-DryRun`: no question, no omp block, and neither "Optional:" line — omp and gh are both already on
   this VM (step 7 shows omp "OK   already here"), which is exactly what hides them; the hints themselves
   cannot be seen on this machine.
7. `-DryRun -GitHub -WithOmp`: the omp block ("omp -- every non-Claude model for TCC's picker
   (metered) / OK   already here") and the gh block in the plan. `-DryRun -WithOmp -Terminal`: first
   line "-WithOmp: omp is for the app's model picker, and -Terminal installs no app -- left out.", no
   omp block, no error.

## S-015 · On the Windows VM the reviewer's CLI rung runs `gemini`, not agy
**Status**: done 2026-09-17 · `python3 skills/autosound-tuning/scripts/autosound_ai.py selftest` (the doctor block) and `doctor` on the Windows VM: the key "з файлу …\autosound\critic-env", "✓ Живий виклик (API google)", "▶ Режим роботи: АВТОМАТИЧНИЙ (відповів API google)" · commit `1b77afd`. The forced-`GEMINI_BIN` ✗ is proven by the selftest only: the VM's variable was already gone

**Found** 2026-09-17 on the Windows VM, S-012 step 3, from an ordinary PowerShell:
`autosound_ai.py ask` with `AUTOSOUND_CRITIC_MODEL=gemini-3.8-flash-low` tried the Gemini API first
("HTTP Error 400: Bad Request — API key not valid"), then "Виклик локального CLI 'gemini' (google)",
whose output was the Gemini CLI's own ("256-color support not detected", "Ripgrep is not available.
Falling back to GrepTool.", "Error when talking to Gemini API"). The installer on the same run reported
"Gemini reviewer (agy) -- already set up" at `~\AppData\Local\agy\bin\agy.exe`. Exit 4 with the
reasons and the package, as designed. Recorded only — not diagnosed (hub `governance/WAVES.md` §1);
`doctor` on the same VM (S-012 step 2) lists "Знайдено локальний CLI" as `gemini` for google, anthropic and
openai alike and does not name agy; the key is `GEMINI_API_KEY` in the old `AIza…` format, refused with
HTTP 400.

**Where it comes from on this VM** (2026-09-17, the review): Windows' USER environment holds
`GEMINI_API_KEY` = `AIza…` (39 chars) and `GEMINI_BIN=gemini`; the Machine scope holds neither, and there
is no `critic-env` — the AQ key the user set up is in neither scope. `GEMINI_BIN` wins in `detect_cli` for
EVERY vendor, which is why `doctor` printed `gemini` for anthropic and openai too — without saying a
variable forced it. agy, asked in another window, reported the same `GEMINI_API_KEY` (`AIzaSy…`) as its
auth. In a new window `doctor` (through the full python path, see S-016) also said "Модель рецензента не
задано", listed the models, and still printed "▶ Режим роботи: АВТОМАТИЧНИЙ (через API google)" under
its ✗ lines; the window blinked once while it ran.

**After the user moved the key** into `%APPDATA%\autosound\critic-env` and removed both user variables,
`doctor` in a new window: the config file found, "Ключ живий: 41 моделей", "current (AQ.…, 53 chars)",
local CLI google `agy`, anthropic `claude`. It still ended ✗: `gemini-3.8-flash-low` — an `agy` id — is not
in the key's list (the API has `gemini-3.8-flash`), so the live call got HTTP 404. A round does the same with
a key present: a model the key cannot call stops it with the key's list (exit 3) and does NOT fall through to
agy — step 3 of S-012 reached agy only because the key file was set aside for that run. Left for the wave: `doctor` does not say that `GEMINI_BIN`
forced the CLI; it prints `~/.config/autosound/critic-env` as the place to pin a model on Windows too; it
prints "АВТОМАТИЧНИЙ (через API google)" under a failed live call; one model variable serves two doors
whose ids differ. Also seen: `install.sh --help` still shows a `v3.0.46` one-liner.

**Fixed on `wave-2026-09-17`** (`scripts/autosound_ai.py`, its selftest covers each): a key and a forced CLI say
where they came from — a config file, or the environment every program inherits; a `GEMINI_BIN` naming the
closed `gemini` while `agy` is on PATH is a ✗ that says to remove it; every hint names this platform's config
file (`%APPDATA%\autosound\critic-env` on Windows); a model the key cannot call also says the other door
(remove the key, and the CLI with its own ids answers); the live call walks the round's ladder — an API failure
hands over to the CLI, a model the key cannot call stops at the choice — and the mode line says what answered,
or that nothing did. Seen on the Mac too, the same afternoon: the old `AIza` key exported from `~/.zshrc`.

Done looks like: step 3 of S-012 answers through agy on this VM, or the refusal says why agy was not the
CLI it ran.

## S-016 · In a new PowerShell window after the install, `python3` is the Microsoft Store alias
**Status**: done 2026-09-17 · the branch's installer on the Windows VM: "~\.local\bin now leads your user PATH -- a new window's python3 was …\WindowsApps\python3.exe" and "OK   python3 in a new window is ~\.local\bin\python3.exe"; a NEW window: `python3 -V` → 3.12.14, `Get-Command python3 -All` lists `.local\bin` first · commit `1b77afd`

**Found** 2026-09-17 on the Windows VM, after S-012: the `doctor` line the installer prints, run in a NEW
window — "Python was not found; run without arguments to install from the Microsoft Store, or disable
this shortcut from Settings > Apps > Advanced app settings > App execution aliases.", exit 9009.
`Get-Command python3 -All`: `~\AppData\Local\Microsoft\WindowsApps\python3.exe` first, then
`~\.local\bin\python3.exe`. The USER PATH lists WindowsApps before `~\.local\bin`; the Machine PATH
holds neither. The installer's own window worked because the installer puts `~\.local\bin` first in
that window's PATH only (`Sync-ProcessPath`). `install.ps1`'s comment at its uv step says uv puts
`~\.local\bin` at the FRONT of the user PATH; on this VM (uv already installed before this run) it is
not. The method's tools call `python3`, in a terminal and in Claude Code's Bash tool alike.

Done looks like: in a new window after the install, `python3 -V` answers with the Python the installer
set up. The VM is left as found, so the fix can be checked on it.

## S-017 · Analysing a tune that already exists — noted, not started
**Status**: deferred 2026-09-17 · the user: "note it with the source, we do not go there yet"; it comes back when Phase 1's variants work on a fresh system and a tuner brings a car that is already tuned

**Due when:** Phase 1's variants (issue #38) work on a fresh system, and a tuner brings a car that is already
tuned. The user, 2026-09-17: "note it with the source, we do not go there yet".

**What Resonalyze has, read in the fork** (`Resonalyze-fork`, local): its AI bridge asks whether the user wants "a
look over a tune they already made" and judges every step against the user's tune, not the step before
(`docs/agent/AGENT_GUIDE.md:5-15`); its junction tune is "the crossover engine for a tune that already works" and
keeps the current crossover unless a candidate beats it by 0.5 dB (`REFERENCE.md:3334-3347`,
`dsp/CrossoverJunctionTuner.cs:242-248`). It has no importer for a whole third-party DSP project; only per-channel
PEQ banks travel, Helix's included (`MANUAL.md:991-996`).

## S-013 · Each REW reader names the smoothing it reads
**Status**: done 2026-09-17 · `scripts/run-selftests.sh` (73/73; `python3 skills/autosound-tuning/rew_tool/rew_api.py --selftest` holds every reader to its ask) · commits `c7c8e17`, `596a389` · decisions in `docs/RESEARCH-2026-09-17-reader-smoothing.md` §6

**Due:** research first — the user, 2026-09-17: "don't know, it needs researching". Done the same day:
live REW (nine positions × seven channels), math, REW's documentation, papers, practice. The user's
position from that conversation: `None` and `1/48` are one level, finer brings only interference —
the data agrees (§2.1). What each analysis asks is §6 of the research, for the user to decide
proposal by proposal. The recommendation below predates the research and is superseded by it.

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
**Status**: done 2026-09-17 · the user: "install by flag" · `python3 scripts/installer-consistency.py` (check 5a) · commit `317dd6e`

**Due:** 2026-09-17, a question for the user before anything changes.

On 2026-09-16 the user chose "gh off, omp only with a flag" from a menu (docs/SIMPLIFICATION-2026-09-16.md
§7). The gh half is done on `wave-2026-09-16`. The omp half would reverse a decision taken twice —
2026-08-19 and 2026-09-09 — for a reason the menu did not show: *the person who wants omp is the person
who does not know the flag exists* (issue #25, and the comment above `WANT_OMP` in `install.sh`). What
changed since: the README and FAQ now name `omp` and `--no-omp` at the install step (issue #25's
2026-09-09 comment). Ask: keep omp on with the app, or make it `--with-omp` only. Close #25 either way.

## S-018 · RES-013's guard misses the cells it was written for: above 1 kHz the score follows a lying witness
**Status**: done 2026-09-17 · research answered with RES-016 (hub `#172`): the guard reads a second witness, the 2-cycle direct-sound cut, and fires on the proposal a cycle from it, on the two witnesses half a cycle apart, on RES-013's disagreement, or -- with no cut -- on a whole cycle moved · `python3 skills/autosound-tuning/rew_tool/predict.py --selftest` (cases i, k, l, m) · `hub/scratch/skill/res013_check.py` → 0 of 10 missed, 0 false alarms · wave-2026-09-17b

**Due:** research's ticket on this, which the user said is being written. Not before — the rule is
theirs (hub `#168` is an `rfc`, `ROLES.md` §0), and this item is the measurement, not a redesign.

RES-013 as accepted is implemented and green (`commit b8d98d1`, hub `#168`): at or above 1 kHz a
whole-cycle disagreement between the sum-loss score and the arrival witness is recorded
`chosen="unverified"` instead of being resolved. Then its own falsification (a) was run against the
integrated code, on the BMW F30 archive research measured it on — `hub/scratch/skill/res013_check.py`
through research's own cell loader, `REW_TOOL=<this tree>/skills/autosound-tuning/rew_tool
~/dev/autosound/research/.venv/bin/python res013_check.py`:

| tune · side | proposal, cycles from the owner's tune | chosen |
|---|---|---|
| root · head90 R | −4.53 | score ← **unmarked** |
| v3 · session R | −0.86 | unverified |
| v3 · validated R | −0.83 | unverified |
| v5 · manual L | +1.03 | unverified |
| v5 · manual R | −3.98 | score ← **unmarked** |
| v6 · session R | −4.36 | score ← **unmarked** |

(the four left sides not listed sit within 0.1 cycles of the tune and pass as `score`.)

**3 of 10 cells still overrule the hand tune by ~4 cycles with nothing marked**, so falsification (a)
fires. The guard tests whether the two CANDIDATES disagree; in those three cells they AGREE with each
other — the full-record witness reads the right tweeter 2.6–2.9 ms late and the score's best goes
there with it. A guard on disagreement cannot see a witness the score follows. The numbers reproduce
research's own table (their score's best, cycles from tune: −4.52 / −0.84 / −0.85 / −3.97 / −4.37) to
the second decimal, so this is the rule's shape and not the harness.

**What would settle it (for research to decide, not this tree).** A criterion that does not rely on
the two candidates disagreeing — e.g. above 1 kHz mark `unverified` whenever the proposal moves the
junction a whole cycle or more from the delay the DSP already holds (that makes the metric 0 of 10,
at the price of asking for a pair measurement on every large first-time move). Reported to the user
2026-09-17; research's ticket is what this waits for.

## S-019 · The release role cannot run `gh release delete` itself: the harness refuses it

**Status**: open — noted 2026-09-17 on #173, where the user ran the command by hand.

Clearing the v3.0.56 draft needed `gh release delete v3.0.56 --repo ayukhno/autosound-tuning-skill
--yes`. Two walls, and only the second is ours to think about:

* `gh api -X DELETE .../releases/391041153` — refused by `guard-release.py`, correctly: `gh api`
  writes are content for every role, `release` included (`hub:governance/RELEASE-CHANNEL.md` §8.7).
  The path the guard leaves open is `gh release <sub>` from the `release` role.
* `gh release delete …` — passed the hub's guard and was then refused by Claude Code's own
  permission classifier as a destructive command. The user pasted it into the session instead
  (`! gh release delete …`), which is what actually deleted the release.

So the release role's one sanctioned write path currently needs a human keystroke every time. That
is not wrong — the release channel is content — but it is undocumented: nothing in the role's start
says "the delete will come back to you".

**What would make it due**: the next release that needs a draft cleared, or a `gh release edit`
/`upload` step landing in the same place. Then either a Bash permission rule for exactly
`gh release …` in this tree's settings, or a line in `RELEASE-CHANNEL.md` saying the last keystroke
is the user's by design.

## S-020 · The installers can fetch the engine archive now that a release carries it
**Status**: doing 2026-09-18 · built on `wave-2026-09-18`, the three decisions taken with the user: fetch only where there is no .NET SDK, `--engine` / `--no-engine` to override, a missing archive said out loud. `python3 skills/autosound-tuning/rew_tool/resonalyze_engine.py fetch-binary --tag v3.0.57` → installed, sha256 checked; `… resonalyze_engine.py smoke` then ran the whole synthetic set on the FETCHED engine; `bash install.sh --dry-run --terminal --engine` and `--no-engine` print the two branches; `python3 scripts/installer-consistency.py` (check 5c) holds the three installers to one decision. **Left, and it is what the Done-when asks for:** the installer's own step on a machine with no SDK — the Windows VM, on **`v3.0.58`** (tagged 2026-09-18; its release carries `resonalyze-engine-b0ce9fb-{win-x64,win-arm64,osx-arm64}.zip` and `SHA256SUMS`). What to run there: the README one-liner at that tag on a VM with no .NET SDK — the step should say it fetched ~30 MB and checked it — then `python3 rew_tool/resonalyze_engine.py smoke`, which should run with nothing built; and `-NoEngine` on a second run, which should refuse the fetch and say how to do it later

**Due when:** someone installs the method on a machine without the .NET SDK and wants Phase 1's desk
step. Not before — a person with the SDK loses nothing today.

**State today.** `v3.0.57`'s release carries three archives, each built AND run through the synthetic
set on its own runner, with `SHA256SUMS` beside them (hub HUB-070, `RELEASE-CHANNEL.md` §12):

```
resonalyze-engine-b0ce9fb-win-x64.zip · resonalyze-engine-b0ce9fb-win-arm64.zip · resonalyze-engine-b0ce9fb-osx-arm64.zip
```

The installers do not know they exist. `install.sh` / `install.ps1` / `install.cmd` put the method
in place; `resonalyze_engine.engine_command` then looks for a prebuilt engine in
`installed_dir()` — which is empty unless the person ran `install-binary --from <zip>` by hand —
and otherwise reaches for the SDK, or says by name that neither is there.

**The form, when it becomes due.** The file name is computable from the tag and the platform, which
is why §12 requires that shape: `resonalyze-engine-<pin>-<rid>.zip`, the pin being
`resonalyze_engine.ENGINE_PIN` and the rid `resonalyze_engine.rid()`. So an installer can fetch
exactly one file from the tag it is installing, check it against `SHA256SUMS`, and hand it to
`install_binary`. Three things to decide with the user first, because each is a change in what an
install DOES:

1. **Asked or default?** ≈30 MB per platform on every install, against an SDK build on first use.
2. **A platform with no archive** (`linux-*`, `osx-x64`, and any future rid): the installer must say
   which way it went, not silently fall back.
3. **A pin that has no archive on that tag** — the engine pin moves with the submodule, not with the
   tag, so a tag whose run did not attach (v3.0.56 is one) has none. The installer reads the pin
   from the tree it just installed and asks for that name; a 404 is then "build from the SDK", said
   out loud, not an error.

Done when an install on a machine without the SDK ends with a working prebuilt engine, the choice is
the person's, and `installer-consistency.py` holds the three installers to the same decision.

## S-021 · Phase 1's variants run end to end on a fresh system, and what a wish really costs

**Status**: waiting 2026-09-18 · issue #38's remaining piece. The second one is no longer a question
for the test to answer: the user asked for the full variant to be built without waiting for a car, and
it is (`wish_variants`, on `wave-2026-09-18`) — so what waits is the run itself, on **`v3.0.58`** (tagged
2026-09-18); the software side is in place
(`docs/DESIGN-2026-09-17-phase1-variants.md` §6: 1–4, 5a–5c, 6 all done, S-020 the last of them).

**Due when:** now — it waits for a run, not for work.

**What to test, in the order §1 puts it.** A car and a system the method has not seen, from intake:

1. **Intake and capture** (Phase −1, Phase 0) — one impulse per driver from the tripod, loopback,
   `Repetitions 4`; the machine files validate (`contract.py check <project> --gate` exits 0).
2. **The tuner's crossover wishes in free words**, no form — a sentence like "BE4 between tweeter and
   mid, BW2 between sub and midbass, not sure between midbass and mid".
3. **The best configuration first, then the wishes against it** —
   `python3 rew_tool/resonalyze_engine.py run <project> <set> --out <dir> --wishes "…"`. What to
   watch: the driver types come from the roles and not from the engine's suggestion; an edge under a
   fragile driver's Fs floor comes back REFUSED with the nearest allowed setting named; the rear fill
   that does not fit the device is lowered and said so; a wish that broke a limit is not computed and
   says why.
4. **Coarse EQ before the delays** (`eq_propose --part 1`), then the delays and levels with it in the
   chains, then the sums into the target-curve visualizer (`sums_export.py`).
5. **The description in words, and the choice** — two or three variants, what each buys and what it
   spends; nothing entered without the tuner's OK.

**What would say it works:** a tuner who has not built any of this gets to a DSP setting they accept,
without a session reaching for a tool by hand that the phase documents do not name, and without a
number that has to be explained away. **What would say it does not:** a step that needs the author to
run it, a refusal whose nearest allowed setting is wrong for the car, or a variant nobody can choose
between because the description does not say what it costs.

**6. What the run now judges — issue #38's second piece, built 2026-09-18.** A wish is no longer read
only as a PROBE (that one junction, each side after its own delay). Every computable wish is also run
as its own WHOLE CONFIGURATION: its edges written in, Auto delay again over the chain, every junction
then re-read, with the delays that moved and any polarity that flipped named
(`rew_tool/resonalyze_engine.py` `wish_variants`; `DESIGN-2026-09-17-phase1-variants.md` §6, 5b). On
the Passat that read differently from the probe in the part a tuner would have met in the car: the
BE4 wish flips BOTH tweeters' polarity, and the BW2 wish moves the whole chain by about 3.9 ms.

So the test is no longer asking whether to build it. It asks the two questions only a car answers:
**does the whole-configuration report let the tuner choose** — is "what this wish costs" said in
terms they can act on — and **does Phase 3's control measurement agree with it** on the variant they
picked. A disagreement there is a finding about the model, not about the report's shape.

One guard is deliberately missing, and the test does not need it: there is no golden for a variant.
`acceptance` models ONE engine run against recorded values, and a variant is a sequence of three, so
a golden means teaching that harness the sequence. The synthetic `smoke` (CI) and the module's
offline selftest hold the pass instead. Worth building when a second car needs the same guard.

## S-022 · A prebuilt engine is found by the FORK's pin, so a changed wrapper runs the old binary

**Status**: open 2026-09-18 · met while building #38's full variant: the wrapper changed, and the run
kept using the engine fetched from `v3.0.57` until it was deleted by hand.

**Due when:** a second person develops the wrapper, or a user updates the method by hand (a `git pull`
in the checkout rather than the installer) and the wrapper changed under the same fork pin.

`installed_dir()` is `…/engines/resonalyze/<ENGINE_PIN>/<rid>`, and `ENGINE_PIN` is the **fork's**
commit — the submodule's. The wrapper in `engines/resonalyze/*.cs` is ours and changes on its own; two
skill tags can carry one fork pin and two different wrappers, and `engine_command` prefers a prebuilt
engine over building this checkout. So a machine that has one runs the OLD wrapper, and says nothing:
the result's `pin` names the fork, which matches. An install or update through the installer overwrites
it (`fetch-binary` runs on every install), so the ordinary user is covered; a developer is not.

**The shape when it becomes due:** put the WRAPPER's own identity into the path or beside the binary —
the archive is built per tag, so the tag it came from is the honest name — and let `engine_command` say
which it is running when the two disagree. Not the fork pin alone.
