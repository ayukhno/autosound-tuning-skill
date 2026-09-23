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

**Status**: dropped 2026-09-22 · not the product's: the Arbiter, «це не проблема Продукту, це задача для моєї роботи. поки не проблема прибрати руками в кінці вехі» — a draft is cleared by hand at the end of a wave, and nothing in the method changes · was: deferred 2026-09-22 · W-2 review, the Arbiter: «що не включемо — то зрозуміти причину і відкласти» · the fix is a harness permission or a line in hub `RELEASE-CHANNEL.md` — process, which waits for the review between waves (`WAVES.md` §4); comes back when a release needs a draft cleared · was: open — noted 2026-09-17 on #173, where the user ran the command by hand.

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
**Status**: done 2026-09-23 · on the Windows 11 arm64 VM, no .NET SDK, by the Arbiter: `install.ps1` at v3.0.60 → "installed: resonalyze-engine-b0ce9fb-win-arm64.zip from v3.0.60, sha256 checked" + "the engine runs: Auto crossover on a 3-channel test set in 4.6 s"; `python3 …\rew_tool\resonalyze_engine.py smoke` → `smoke[resonalyze_engine] OK` (with the LR24 base). Found on the way: skill #60 (Codex/Claude CLI prompt as an argument on Windows), #61 (deliverables into docs/), #62 (the installer's TCC upgrade over a launcher uv does not own breaks the app); `py -3` is not the installer's Python (use `python3`) · was: doing 2026-09-18

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

**Status**: deferred 2026-09-23 · returns after the 3.1.x line is released (the Arbiter, 2026-09-23: «S-021 відкласти на після 3.1.х») · the feature half is in v3.0.60 (`resonalyze_engine.py smoke`, `variant_front.py --selftest`) · was: open 2026-09-23
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

**Status**: done 2026-09-23 · W-2 package C · `python3 skills/autosound-tuning/rew_tool/resonalyze_engine.py --selftest` (the S-022 block): a fetched engine carries `WRAPPER.json` with the tag and this checkout's wrapper digest; `engine_command` builds this checkout's wrapper when the SDK is there, and otherwise runs the old one and SAYS so; `doctor` names it · was: open 2026-09-18 · **W-2 package C** (`docs/PLAN-W-2.md`) · · met while building #38's full variant: the wrapper changed, and the run
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

---

## S-023 · SCR-059 is done in `main` and has no tag: close the ticket, or wait for one?

**Status**: done 2026-09-22 · `git merge-base --is-ancestor 9de1085 v3.0.59 && echo in` → in; hub `#178` closed with that line at the W-2 review (W-1 said it would close with that tag) · was: waiting 2026-09-19 · the work is in `9de1085` (`rew_tool/intake.py` — the intake's fields,
enumerations and couples as data, the gate's list read off `contract.GATE_REQUIRED`, and the writer for
the car / channel map / measurement chain), the whole suite green (78/78), the CHANGELOG entry under
`## [Unreleased]`. Hub `#178` is still `accepted` — the question was put to the Arbiter and the session
stopped before it was answered.

**Due when:** the Arbiter answers. Three ways, and the first is the one recommended:

1. **Close `#178` now, let the tag come with the wave.** TCC vendors the method by sha, so its half
   (the form) can be built against `9de1085` today and pinned to the tag when the wave cuts one. The
   receipt names the commit and the run, which is what a proof line owes.
2. **Hold it in work until `v3.0.59` exists.** Honest about "released", but TCC does not learn its half
   is ready and waits for nothing.
3. **Cut the release now** — branch, PR with the full CI, `ff-only`, `tag-check.sh v3.0.59`. An hour or
   two, and outside the wave's order; only worth it if the tag is needed on a machine today.

**What is NOT owed here.** Nothing in the method waits on this: the module, its selftest, the board row,
`phase_-1_intake.md` §0.6 and the schema doc all landed together. This item is the bus's bookkeeping and
the release's timing, not unfinished work.

---

## S-024 · An imported fact keeps saying `measured`, so the intake cannot tell a copy from a measurement

**Status**: done 2026-09-20 · W-1 package C · `python3 skills/autosound-tuning/rew_tool/project.py selftest` (mark-imported keeps the value and the time it was measured there) · `python3 skills/autosound-tuning/rew_tool/contract.py selftest` (reported, gates nothing) — the METHOD's half; TCC writes the import record under hub `#185`. Found 2026-09-19 in the export package
`passat-b8-2026-car-2026-09-18.zip` (tcc 0.1.41, method 3.0.58): its seven `channels[].fs_hz` facts carry
`"source": "measured"` with the source build's `at` (`2026-08-21T15:18:52`), and land that way in a project
created on 18.09 on another machine. TCC's half rides as hub `#185`.

**Due when:** TCC writes the import record and the imported provenance asked for in `#185`. Until then the
method has no way to read what it is looking at, and this session watched the cost: the skill's opening
report had to INFER the seed from the folder's history and then handed the user a contradiction
(project named `EPY-Sep2026`, inherited `preference-profile.md` describing a competition tune that calls
EPY its opposite) as a decision for him — when it was not his choice at all, but a consequence of the copy.

**What the method owes, once the record exists:**

1. **Read the import record, do not guess the seed.** A section the user deliberately excluded (the cabin
   flaws, in this case) is «to be measured here», not «missing» — and today those two are indistinguishable.
2. **An imported `fs_hz` is closed by the Arbiter's word, not by a second impedance run.** The user's
   decision 2026-09-19: «галочка вмикнута (стоїть) — імпеданс складна штука і міряти його другий раз це
   подвиг». So the gate must NOT demand a remeasurement, and a protective HPF may be derived from an
   imported Fs — but the fact stays marked as imported, and any report that uses it names where the number
   came from and when it was measured there.

---

## S-025 · `hardware.controls` mixes the control module's knobs with the processor's features, and accepts any key

**Status**: done 2026-09-22 · W-2 package A · `python3 skills/autosound-tuning/rew_tool/project.py . selftest` (the S-025 block: `realcenter` refused as a processor feature, `VirtualX` refused without the person's word, `SubRC` / `RemoteToneControl` / a user's own `HU bass` accepted); the rule is written in `project-schema.md` and `naming-and-structure.md` · was: open 2026-09-19 · **W-2 package A** (`docs/PLAN-W-2.md`) · · W-1 collection · the user, on the six entries the export carries: «не лізь
туди, там ще складніша логіка роботи — просто OFF для налаштування».

**Due when:** the intake touches `hardware.controls` again. The rule to carry is ONE line — during tuning
the control module is OFF (TC/RTC, FX) — and the method does not model the module's logic, its modes or
what a step is worth.

What was measured on the package: `hardware.controls` holds `RTC`, `RealCenter`, `RearRC`,
`RemoteToneControl`, `SubRC`, `VirtualX`, and (a) the Conductor is ONE physical knob whose modes cycle by
press — volume → sub → rear → tone — so four of those «controls» are modes of one knob, while `RealCenter`
and `VirtualX` are processor features, not knobs at all; (b) the knob set is a property of the control
module (a Conductor; other modules carry other knobs) and is itself configurable, so it can be asked but
never assumed; (c) `VirtualX` is not in the bundled DSP profile's feature list
(`knowledge/dsp/profiles/audiotec-fischer-helix-dsp-ultra-s.json`: RealCenter, DynamicBass, SubXpander,
ActiveToneControl, RemoteToneControl, SubRC, RearRC), and nothing refused the unknown key; (d) the values
are not positions but decision history, dates and measurement numbers.

**Not owed:** modelling the module. The user closed that explicitly.

---

## S-026 · The level a series was measured at lives in the taste profile, and is unreadable as a quantity

**Status**: done 2026-09-23 · W-2 package E · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (`capture-start … --level "-25 dB rel. max" --level-read-as "7 lamps"` recorded on the round; a level with no dB refused); `process-schema.md` documents it · was: open 2026-09-19 · **W-2 package E** (`docs/PLAN-W-2.md`) · · W-1 collection · `preference-profile.md` line 28 of the exported
`passat-b8-2026`: «Суддівський рівень: 7 лампочок майстра, ГП USB → Douk U2 → оптика», while the scale sits
in the prose of a different field — `hardware.controls.SubRC`: «майстер: 60 дБ кроками 1 дБ, лампочка = 5
дБ, у лампочці 5 кроків яскравості».

**Due when:** the next capture round is opened on a car whose level is set on a Conductor.

Two faults, and the second is the one that bites. First, the level at which a series was captured is a
CONDITION OF THE SERIES, not taste — and it was sitting in the one file that (the user's decision
2026-09-19, hub `#185`) must never travel to another project, so it disappears exactly when a new build
needs it. Second, «7 лампочок» is not a quantity: to read it in dB you need three more facts the file does
not hold — twelve lamps, five 1 dB steps per lamp, the top lamp is 0 dB. The user supplied them 19.09, so
the arithmetic is now closed: **7 lamps = −25 dB rel. max** (the eighth lamp starts with the next step).

**The shape:** the round records the level as a quantity — `−25 dB rel. max` — with «7 лампочок майстра» kept
as how it is read off the Conductor, not as the number itself.

---

## S-027 · A prose source line is read as a path, and the intake reports the file as gone

**Status**: done 2026-09-22 · W-2 package A · `python3 skills/autosound-tuning/rew_tool/contract.py selftest` (the `sources` block now carries `autosound-measurements/.../{README.md,manifest.json} (…)` and `/data/…/irs_48/*.json`, and `sources_gone` still holds only the two literal paths) · was: open 2026-09-19 · **W-2 package A** (`docs/PLAN-W-2.md`) · · W-1 collection · `project.json.sources` holds
`autosound-measurements/.../2026-08-20_front-set-02/{README.md,manifest.json,dsp-state.json} (стан DSP та
стенда під час baseline)` — a brace list of three files inside a prose citation. The skill's opening report
in `EPY-Sep2026` named it as `.../{README.md` and said it «more does not exist».

**Due when:** the intake checks a source line's existence. Either it parses the brace list, or — better —
it does not treat a `sources` line as a path at all: the field is prose with a note in parentheses, and
three of the six lines in that file are not paths to begin with (`REW-сесія new-logic-EPY.mdat: імпеданс-свіпи (imp) → виміряні Fs`).

---

## S-028 · The session's `python3` dies on `xcrun` in an x86_64 shell, and the doctor does not name it

**Status**: done 2026-09-23 · W-2 package C · `python3 skills/autosound-tuning/scripts/autosound_ai.py selftest` (`machine_lines`: a shell under Rosetta and a git that does not run are named, with `arch -arm64` and `brew install git`); `doctor` prints them first · was: open 2026-09-19 · **W-2 package C** (`docs/PLAN-W-2.md`) · · W-1 collection · the skill session working on `EPY-Sep2026` had to run every
command as `arch -arm64 /usr/bin/python3` and told the user so as a footnote: its shell was running as
x86_64, where `python3` falls over on `xcrun`.

**Due when:** the doctor block is next touched. The finding is that the session diagnosed this itself and
carried the workaround by hand — `selftest`/`doctor` said nothing, so the next session on that machine
starts by rediscovering it.

---

## S-029 · A session said the user closed the question window; no window had appeared

**Status**: done 2026-09-20 · W-1 package A · `grep -n "did not reach him is NOTHING AT ALL" skills/autosound-tuning/references/core/feedback-loop.md` — found 2026-09-19, the user, on the reply he got in `EPY-Sep2026` after the
cleanup: «в відповіді побачив ось таку фразу "Вікно питань ви закрили — лишаю їх текстом, відповісте як
зручно." — а вікна не було».

**Due when:** the method next says how to ask. `references/core/feedback-loop.md` tells a session to ask
closed questions with ready options (`AskUserQuestion`), and says nothing about the case where the call
does not reach the user — so this session filled the gap by inventing an action the user never took.

**The rule to write:** the questioning MECHANISM is never retold, and its outcome is never attributed to the
user. A question that did not reach him is not «you closed it» — it is nothing at all: the questions go into
the text, with no claim about why. Same class as hub `CLAUDE.md` «відмова механізму не переказується», with
the extra harm that here the retelling named the user as its cause, and he had to correct a report about
himself.

---

## S-030 · The input that does not stick is AUX, and the trigger named in the knowledge row is the wrong one

**Status**: done 2026-09-22 · W-2 package A · `grep -n "The measurement input does not hold" skills/autosound-tuning/knowledge/dsp/helix-dsp-ultra-s.md` and `grep -n "re-check it after every configuration write" skills/autosound-tuning/SKILL.md` · was: open 2026-09-19 · **W-2 package A** (`docs/PLAN-W-2.md`) · · W-1 collection · the user, correcting the row this session's reply quoted to
him: switching the input from BT to AUX does not hold — at the next configuration write or DSP reconnection
the input stands at BT again. So it hits exactly ONE input: AUX, which is where the Scarlett feeds the
measurement signal. «запиши це собі як задачку виправити потім».

**Due when:** the knowledge row or the pre-session checklist is next touched.

`knowledge/dsp/helix-dsp-ultra-s.md` line 13 (Presets) records the symptom as «switching can silently reset
the INPUT to another card — check the input after every switch (Pre-session #4)». The symptom is real; the
trigger is not the one the Arbiter sees on his own machine. Preset switching is what got blamed, and a check
tied to it fires at the wrong moments and misses the ones that matter.

**The shape:** the row says what was observed — AUX is not retained across a configuration write or a
reconnect, and the fallback is BT — and the check moves from «after every preset switch» to «after every
configuration write, every reconnect, and before every series», because the input that silently disappears
is the MEASUREMENT input. A series captured after it reverted is a series through the wrong path.

---

## S-031 · A plan step carries a COUNT, and has nowhere to carry what it covers

**Status**: done 2026-09-20 · W-1 package A · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (the `covers` block) · `add-step <id> <name> --covers a,b,c` — found 2026-09-19, the user, on the plan rendered in TCC's window: «ось такий
пункт в плані зовсім не зрозумілий» — the step reads `Закрити відкриті поля: project.json (8) і
dsp_profile.json (5)` and nothing else. Thirteen fields, named nowhere he can see.

**Due when:** the plan's steps are next written or rendered.

Two halves, and the second is why rewording alone will not fix it:

1. **The names exist and were dropped.** `project.py <dir> open-questions` and `dsp_profile.py
   open-questions` print the unresolved facts as dotted paths, and the same session had already named
   several of them in the chat («вхід для свіпів, гейни трьох підсилювачів, моделі драйверів тилу
   r-L/r-R»; profile: «чи всі яруси перелічені», the 60-band budget). The plan — the one artefact the
   Arbiter acts on — kept only the two counts.
2. **A step has no field for its content.** `state/process.py` `add_step` writes `id`, `name`, `status`,
   `source`, `attempt`, `skip`, `phase`, `evidence`. There is no `covers`/`detail`, so the substance can
   only be crammed into the title, and a front-end that renders a checkbox list has nothing else to show.

**The shape:** the name names the things — the first two or three and `+N` — AND the step gains a `covers`
list (the dotted paths, as `open-questions` prints them) that a window can expand and a session can tick off
mechanically. Same class as hub `CLAUDE.md` §9.20 and the Arbiter's standing rule: a bare number is not a
subject. When `covers` exists, TCC's window renders it — that half rides on a ticket, not on this item.

---

## S-032 · A different reference seat is a different PROJECT, not an option inside one

**Status**: done 2026-09-20 · `python3 skills/autosound-tuning/rew_tool/project.py selftest` (the six, written once, a second different one refused with the route out) · `python3 skills/autosound-tuning/rew_tool/intake.py selftest` (the field writes through that writer) · `project.py <dir> project-type` · **CONFIRMED by the Arbiter**, and he widened it: «проект може бути тільки одного типу: водій, пасажир, обидва, всі, задній пасажир ліворуч, задній пасажир праворуч. робимо». So the seat is not an enum with three values inside a project — it is WHAT THE PROJECT IS, with six of them, and «all seats» is one of the six rather than the exception he had guessed at. Taken into the next wave. Found 2026-09-19 · W-1 collection · the user, from the test: tuning the stage for the PASSENGER
means taking every raw curve again and walking the whole process, so it belongs in its own project rather
than as a setting in an existing one. He adds, as a guess and not a decision: the «for ALL seats»
configuration is probably the same — and it is **not** to be confused with the FULL preset, which is about
the rears and surround.

**Due when:** the intake's seat question is next touched, or a second seat is actually tuned.

What the method says today: `goal.reference_seat` is an enum inside ONE project —
`{driver | driver_and_passenger | all_seats}` — coupled with `car.drive_side` in the `seat` couple
(`rew_tool/intake.py`), and that couple exists because «driver only» was corrected to «driver and front
passenger» five minutes later and a recorded decision had to be voided. The coupling fixed the FORM; this
finding says the fix was too small. A seat is not a field that can be corrected — changing it invalidates
the measurement base, which is what the voided decision was really telling us.

**The six types, settled 2026-09-20** (his words, verbatim): `водій` · `пасажир` · `обидва` ·
`всі` · `задній пасажир ліворуч` · `задній пасажир праворуч`. **A project is of exactly one of
them.** Two things follow that the earlier text left open: «for all seats» is NOT the exception —
it is one type among six, so the guess in the first paragraph is answered; and the rear seats are
named individually, left and right, because on an asymmetric install they are not one place.

**What it changes, now that he has confirmed it:** the seat stops being a revisable answer and becomes part of
what a project IS; presets stay what they are (SQ/FULL live in one project on one measurement base — FULL is
rears and surround, not a seat); and the car package from hub `#185` gets its clearest use — starting the
passenger's project from the driver's DESCRIPTION (car, channel map, DSP, mic, amps) with none of its
measurements, which is exactly the class split that ticket asks for.

---

## S-033 · The intake as a form the skill itself serves — Ukrainian prototype first

**Status**: done 2026-09-22 · W-2 package A · the form the skill serves: `python3 skills/autosound-tuning/rew_tool/intake_form.py selftest` → `selftest OK (intake_form) — 75 fields in one table …`; built in eight rounds with the Arbiter (`docs/DESIGN-2026-09-22-intake-simplified.md`) · was: open 2026-09-19 · **W-2 package A** (`docs/PLAN-W-2.md`) · · W-1 collection · the Arbiter's decisions, taken in conversation 19.09. The
intake is 71 fields, 38 of them required (`rew_tool/intake.py`, SCR-059), and today they are asked in chat:
a front-end cannot render them, and the car half has twice arrived as free text AFTER the gate refused.

**Due when:** the wave's review takes it; the spec below is what was settled, not a plan that starts itself.

**Where it lives — the skill, not TCC.** The page and a small local server are generated from `FIELDS` /
`COUPLINGS`, and TCC opens that page in a webview. The Arbiter, 19.09: the intake is needed beyond TCC —
a terminal session must be able to hand a person a form too. One renderer, one definition; TCC writes no
questions of its own, which is the drift that the car package already cost us (hub `#185`).

**The shape as settled:**

- **Three kinds of control, because the fields are three kinds.** 30 fields carry an enumeration → pick
  lists and checkboxes. 22 are per entity (12 per channel, 4 per tier, 4 per amp, 1 per virtual channel,
  1 per control) → a TABLE, not a flat form; on the Passat that is 12 columns by 20 rows. 23 are typed
  free text, and some of them are valuable precisely because they are (`goal.wishes`, `constraints`,
  reference tracks).
- **The 7 couplings render as ONE control each.** That is the whole fix for the voided seat decision.
- **Probes, not questions:** `rew.api_reachable`, `rew.input_clip_checked`, `dsp.readable` are things the
  tool can answer; a form that asks them asks the person to do the tool's job. Same class as S-030's AUX
  input — a check, not a question.
- **Colours are computed, nothing new is bookkept:** red = required by the gate and empty
  (`gate_requirements()`), yellow = optional and empty, green = filled (`open-questions` says which).
- **Groups and tabs:** the 8 groups can be asked one at a time without walking the whole intake, as long as
  a couple is not torn apart; the full form stays reachable on tabs. `target_curve` (10 fields, 1 required)
  is taste and belongs at Phase 5, not at the intake.
- **The form never closes the gate.** The gate is `contract.py check --gate`; the page shows its verdict.
- **Writing goes through the writers that exist** — `intake.save()/save_car()/save_channel()/save_amp()` —
  and the session reads the result from the project's files, not from the chat.

**Language — the Arbiter's decision 19.09:** the prototype is in **Ukrainian**, because he proofreads it
himself; the other languages come before the release, and the Advisor helps with them. This is the one part
a form cannot get for free: the session translates the method's English questions on the fly, a static page
cannot, so the labels ship as DATA (a label per language beside each field), the way `README`/`FAQ` already
live in four languages under `scripts/i18n-check.py`.

**TCC's half rides as a ticket when the page exists** — opening it, and rendering a plan step's `covers`
(S-031) in the same window.

---

## S-034 · The feedback rail can only CREATE an issue, so commenting goes around it

**Status**: done 2026-09-20 · W-1 package D · `python3 skills/autosound-tuning/rew_tool/gates/side_effect.py --selftest` (post_comment: repo from CHANNELS, the issue number verified) — found 2026-09-19, the session on the test machine, after sending five
findings: the gateway does not comment, only create, so it sent the four comments with raw `gh`,
taking the repository out of `side_effect.CHANNELS` rather than из its own head and checking every
returned URL against it.

**Due when:** the next finding has to be added to an issue that already exists.

That session did the careful thing, and the carefulness is the point: `gates/side_effect.py` exists
because a model once invented a plausible repository and reported a fabricated issue URL (skill `#23`).
Its rail is `post_feedback` → `gh issue create --repo <hardcoded>` with the returned URL verified. There
is no `post_comment`, so «add this to #39» has **no guarded path at all** — and the way round it is a
raw `gh` call with the target chosen by whoever is typing, which is the exact shape the rail refuses.

**The shape:** a `post_comment(issue_url_or_number, body_file, channel=…)` beside `post_feedback` —
same closed `CHANNELS`, same `guarded_run`, same returned-URL verification (the comment URL carries the
repo and the issue number, so it verifies the same way). `--repo` never comes from the caller.

---

## S-035 · Every feedback issue from one car gets the same title, and the 24-hour dedup guard eats the second one

**Status**: done 2026-09-20 · W-1 package D · `python3 skills/autosound-tuning/rew_tool/gates/side_effect.py --selftest` (two findings from one car are two titles) — found 2026-09-19, the session on the test machine: «Заголовок шлюз складає
з авто+DSP, ігноруючи назву в тілі» — both new issues arrived as `Feedback: VW Passat B8 · Helix DSP
Ultra S` and were renamed by hand right after creation.

**Due when:** two findings are sent from one car inside a day — which is what a test session IS.

`side_effect.post_feedback` builds `title = f"Feedback: {car} · {dsp}"` and the body's own heading is
never read. Renaming afterwards is not the whole cost: the function also guards against double-posting
with `_recent_duplicate(title, …)` over `_DEDUP_HOURS` (24 h), and since the title does not vary, the
SECOND finding from the same car in one day is refused as a duplicate of the first. On 19.09 that did
not bite only because the session renamed each issue immediately after it was created — an accident of
its own tidiness, not a property of the rail.

**The shape:** take the title from the caller (the body's first heading is the obvious source), keep
`car · dsp` as a suffix or a label so the provenance survives, and let the dedup guard compare what is
actually distinguishing. A guard keyed on a constant is not a guard.

---

## S-036 · A protective record cannot tell a considered OFF from a front-end's bulk default

**Status**: done 2026-09-20 · W-1 package C · `python3 skills/autosound-tuning/rew_tool/protective.py --selftest` (a bulk default is a question) · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (sources, a channel outside the round refused, and the amendment path) — found 2026-09-19, the session on the test machine refused to accept what
TCC wrote: «Під час імпорту TCC записав `протектив = OFF` на всі 10 каналів за одну секунду, включно з
тилом поза раундом», while the Arbiter's words were the opposite — the filters were in the chain. It
recorded the need for his word instead of writing the fact, which is the right call: a false `OFF`
means a filtered sweep is later read as bare.

**Due when:** the next round is marked by a front-end rather than by hand.

`state/process.py set_protective` is deliberate about this: `"OFF"` is an ANSWER («swept with nothing
in the chain»), and a channel left out is «nobody said», which `protective.should_de_embed(...,
baseline=True)` answers `check` for. What the record cannot carry is WHO said it. Ten channels in one
second is a default being written as ten answers, and every later reader — `predict`, `analyze-joints
--process`, `eq_propose` — takes them as the Arbiter's word. Two smaller things fall out of the same
write: the record accepts a channel the round never captured (the rear), because `set_protective`
checks the open round but not the round's own `expected` list; and a bulk write leaves no trace that it
WAS bulk.

**The shape:** provenance on the record, the way `fs_hz` carries it — `source: user | front_end |
default` — and `should_de_embed` treating a front-end default as `check`, not as an answer. Same class
as S-024: a fact whose origin is not written reads as everybody's word.

---

## S-037 · The Arbiter's read of the form prototype — eight points, and two of them are not about the form

**Status**: done 2026-09-22 · W-2 package A · his eight points, each against the page rendered by `intake_form.py render <empty project> --lang uk`: 1 there are no tabs, one page opens · 2 the AI's language is the interface's (round 5, his decision) · 3 and 4 the reviewer channel and the directory are derived, not asked · 5 the examples are gone from the car labels (`Модель`, `Покоління`, in uk/en/de/pl) · 6 the drive side sits in the second block, with the car and the seat · 7 the DSP is picked from the bundled library · 8 the capability block is asked only for a processor the library lacks (`/new-dsp`). The `car_identity` label reads «Машина: чотири частини однієї назви» · was: open 2026-09-19 · **W-2 package A** (`docs/PLAN-W-2.md`) · · W-1 collection · his review of `intake_form.py`'s first page 19.09,
deferred by his own word to a session of its own: «давай це в окрему сесію відкладемо — тут
потенціал». Nothing below is implemented; this item is what that session starts from.

**Due when:** that session opens. S-033 holds the spec it is changing.

1. **Open the first page.** No tab is active until the URL carries a hash — the page should land on
   the first group.
2. **Two languages, not one.** The AI's language and the person's can differ — measured in practice,
   his words. The interface language is TCC's when TCC is there; the form may show it, not own it.
   Today `project.language` is one field and the page assumes it answers both.
3. **The reviewer channel is a CHOICE from what is available**, like picking a base model — not a
   line of free text. And it may already be settled before the intake (see 4).
4. **«Where does this project live» is not a question.** The skill knows the directory it was
   started in; asking it is asking a person to retype what the tool holds. He puts 3 and 4 together:
   both look like things settled when the PROJECT is created, and the intake should simply know them.
5. **Drop the examples from the labels.** `Модель (назва на шильдику — Passat)` → the model is
   obvious; `Покоління (серія випуску — B8)` → drop `B8`. An example in a label reads as part of the
   question.
6. **`Ліво- чи правостороннє кермо` goes to the TOP of the page.** It is coupled with the reference
   seat for a reason, and it shapes every asymmetry decision that follows.
7. **The DSP is picked from the library** — `knowledge/dsp/profiles/` via `dsp_profile.py
   list-bundled` / `find-bundled` — and only a processor that is NOT there is typed in by hand.
   The vendor is not required: the model settles it.
8. **«Можливості DSP» is not a user's question.** His words: it looks like clutter that complicates
   the process — check it. And the questions after it come with no choice at all (`dsp.tiers`,
   `max_count`, `eq`, `crossovers`, `delays`, `presets` are free text).

**What 7 and 8 are really saying, and it is one thing.** The capability block is the DSP profile's
interview, and the method's own rule is that it is asked ONLY when the library has no exact
vendor+model match (`project-intake.md` §4, `dsp_profile.find-bundled` refuses to approximate). The
Helix DSP Ultra S IS in the library. So the form is putting thirteen questions to a person that a
bundled profile already answers — the interview is the fallback, and the prototype renders it as the
default. Fixing that removes most of the free-text fields he was reacting to.

Also from the same reading: the Ukrainian label for `car_identity` was `Машина — одна особа`, which
reads as "one person". It is `the four parts are one identity` — «чотири частини однієї назви».

---

## S-038 · After the raw capture the session ANALYSED the arrivals, and Phase 1 exists to do exactly that

**Status**: done 2026-09-20 · W-1 package A · `grep -rn "what the CHECK said" skills/autosound-tuning/references/phases/` — found 2026-09-19, the Arbiter, reading the dialogue that followed the raw
sweeps: «щось забагато розмови! навіщо аналіз затримок, як там ціла математика на наступних кроках, а
базу перевірили функціями».

**Due when:** `phase_0_baseline.md`'s post-capture step is next touched.

What happened: `capture-check --session` ran and answered — 8 sweeps usable, 8 RTA unchecked, levels,
arrivals, no `ctl1`/`ctl3` so the session drift is unknown. That is the verdict, and it came from the
functions. The session then added a prose reading ON TOP of it: right-side mids and tweeters arriving
~1.2 ms later, converted to ~41 cm and called plausible for a left-hand-drive driver's seat; a warning
that the midbasses differ by only 0.2 ms (~7 cm) with its own confidence disclaimer about the broad
impulse peak; and a note that this is «a candidate for cross-check in Phase 1».

**Why that last line is the tell.** It is a candidate for Phase 1 because Phase 1 is where the reading
belongs — `predict --align` and `arrival_triangulate` do it through a window, with the trust gate, the
alias rules and the ILL-POSED verdict said out loud. A prose reading at Phase 0 has none of those
guards, which is why the session had to hedge it. A hedged number in the dialogue is worse than no
number: the Arbiter now carries a half-conclusion into a phase that would have produced a whole one.

**Seen twice, so it is structural.** The same midbass reading — «the two midbass drivers reach the mic
only 0.2 ms apart … I'll cross-check this before using it» — came back in a FRESH session after the
Arbiter cleared the chat at the phase boundary. A habit that survives a clear is not a session's whim:
it is coming from the method's own text or from what the tools hand back.

**The shape:** after the check, the session says WHAT THE CHECK SAID — how many captures are usable,
what is flagged, what could not be checked and why, and the drift record — and stops. The arrivals are
in the round; interpreting them is Phase 1's work, by the tools built for it. Same house rule as the
hub's «відмова механізму не переказується», in the other direction: a function's verdict is not
re-derived in prose.

---

## S-039 · A capture recorded under a mistyped title cannot be removed from the round

**Status**: done 2026-09-20 · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (the S-039 block: the wrong row stays, stops counting, and the corrected title is recorded) · `capture-supersede <wrong> <right> [reason]` — found 2026-09-19, from the same report: a ghost `r-R_1 (se)` — a typo
that was fixed in REW, while the round kept the original.

**Due when:** the next round takes a capture whose title is wrong.

`state/process.py` has `record_capture` and `skip_capture`, and nothing that drops or renames a
capture already taken. The plan's steps solved the same problem years-equivalent ago and solved it
well — `supersede` keeps a step in the plan, dimmed, never removed (SCR-004), so «we tried this twice»
survives. A round's captures have no such move, so the only states are «taken» and «never mentioned»,
and a typo becomes permanent evidence of a measurement that does not exist.

**The shape:** the same one the plan already uses — the mistyped capture stays in the round, marked
superseded, naming the title it was corrected to. Not deletion: a round that quietly loses a row is a
round nobody can audit.

---

## S-040 · The report says «сію v_001», and the Arbiter had to ask what that means

**Status**: done 2026-09-20 · W-1 package A · `grep -n "1a. The words a report uses" skills/autosound-tuning/references/core/naming-and-structure.md` — found 2026-09-19, his question, mid-wave: «а що означає "сію" ось тут
"Записую ручки на раунд і рішення, потім сію `v_001`"? і що таке v_ серія?».

**Due when:** the reports are next read for language.

The word is the method's own English carried across untranslated: `phase_-1_intake.md` §153 says «the
first ledger snapshot — **seed** it with every tier the DSP profile declares», and the session rendered
`seed` as «сію». It is not wrong; it is a metaphor the reader does not share, and it cost a stop in the
middle of a wave to unpack. `v_NNN` got the same treatment — used as if it were common ground.

**The Arbiter's own wording, 19.09:** «тобто "записую в ДСП", конфігурація v_001». Two things to keep
straight when it is adopted. The DIRECTION: nothing is written INTO the processor by the method — the
person types the settings in PC-Tool and the ledger records what stands there — so the phrase is
«записую, що зараз у ДСП: конфігурація `v_001`». And the COLLISION: «конфігурація» already means
something else in Phase 1, where a whole configuration is a candidate set of crossovers and delays the
engine searches as one (skill `#38`). Either `v_NNN` takes «конфігурація» and Phase 1 says «варіант»,
or `v_NNN` is «стан ДСП» and the Phase-1 word stays. His call; one word cannot carry both in one report.

**The shape:** a report names the thing, not the metaphor — «записую перший знімок реєстру (`v_001`)» —
and the first time a project's report mentions the ledger, it says in one clause what it is: the full
DSP state banked as an immutable version, not the measurement `_N`. Once per project, not once per
message.

---

## S-041 · Phase −1 walked end to end is hard work, and the dialogue is most of the weight

**Status**: done 2026-09-20 · W-1 package A · closes with the four it covers — `grep -n "A step reply is THREE things" skills/autosound-tuning/SKILL.md` — found 2026-09-19, the Arbiter, having gone through the whole of Phase −1
himself: «я пройшов фазу −1 і це, я тобі скажу, ГЕМОР!!! дуже складно». Two things settled by him in
the same breath — the intake gets simplified, that part is not a question; and the DIALOGUE gets cut,
because the explanations in it are not the user's business. The session transcript follows and becomes
this item's evidence.

**Due when:** the transcript arrives. Nothing is designed before it: the point of reading it is to see
WHERE the weight actually sits, not to guess.

This is the umbrella over four findings already in this wave, and they are all the same complaint seen
from different sides: the form that would replace the chat (S-033) and the eight faults in its first
page (S-037); the arrivals the session analysed at the reader's expense after the raw capture (S-038);
and the method's own English spoken untranslated, which stopped him mid-wave (S-040). Read together
they say the phase asks a person to carry the method's internals — its vocabulary, its capability
interview, its reasoning — while the only thing he owes it is the facts about his car.

---

## S-042 · Channel ids were minted in a notation the method does not have, and the parser does not refuse it

**Status**: done 2026-09-22 · W-2 package A · `python3 skills/autosound-tuning/rew_tool/naming.py . parse "w_L_1 (sw)"` → refused, naming `w-L`; `python3 skills/autosound-tuning/rew_tool/project.py . selftest` (the S-042 block: `fix-ids` plans, holds an id the ledger keys rows by, and writes only on `--apply`); `contract.py check car/passat-b8-2026 --no-rew` lists the six ids with the command to offer. Found on the way: the Passat's six ids are ALSO in `previous_names`, so a rename stands behind them; they are flagged for the notation all the same · was: open 2026-09-19 · **W-2 package A** (`docs/PLAN-W-2.md`) · the Arbiter at the W-2 review: «для мене правильна назва через "-" давай кругом зробимо так» — the hyphen is the notation everywhere; the Passat's six ids and its other live names go to the car role as hub `#196` (SKL-050) · and a session that meets such ids asks and offers to fix them in the session (the Arbiter: «запитати користувача і запропонувати привести все до ладу прямо в сесії»): the list first, then `project.py <project> fix-ids --apply` on his OK · · W-1 collection · the Arbiter, after the gate refused on his machine:
«подивись нотацію і пропонуй назви в нотації (здається так і було) і перевір розбор назв, щоб там була
та сама нотація». The session that hit it described two resolvers reading identity from different
places; measured here, it is narrower and worse.

**Due when:** the naming grammar or `channel_id` is next touched.

**What is on disk** (`car/passat-b8-2026`, read 2026-09-19): the channel codes are the documented
notation — `sw`, `w-L/R`, `m-L/R`, `tw-L/R`, `r-L/R`, `c` — while `channels[].id` carries `w_L`, `m_L`,
`tw_L` … for six of them and is **absent** for `sw` and `c`; the ledger keys its rows by the CODE
(`state/FULL/v_001.json`: `c`, `m-L`, `m-R`, `r-L`, `r-R`, `sw`, `tw-L`, `tw-R`, `w-L`, `w-R`). So
`channel_id()` answers `w_L` where the ledger holds `w-L`, and nothing renamed anything.

That contradicts the id's own contract (`project.py channel_id`): the id **defaults to today's code**
precisely so that a project which renames nothing cannot tell the difference, and the two diverge only
after a rename. Here they diverge with no rename, because somebody minted ids in `snake_case`. An id in
another notation is a second name for the same channel — which is the thing the id was introduced to
abolish.

**And the parser does not hold the line:** `naming.py parse "w_L_1 (sw)"` returns
`{"code": "w_L", "code_current": "w_L", "version": "1"}` — no refusal, and the code it reports exists in
no glossary. `_` is the series separator, so a code containing one is split on the LAST underscore and
whatever precedes it becomes a channel name. The grammar's prose home says codes look like `w-L`
(`naming-and-structure.md` §3); the code has no such rule.

**Two levels, and the Arbiter separated them 19.09:** «це назва проекту і не має відношення до назв
кривих». The CURVE names are REW titles (`w-L_1 (sw)`) — that is where the grammar and the parser live.
The names INSIDE the project — a channel's `id`, the project folder — are project data and do not reach
a title. This item mixed them; below, the parser half is the curves' and the id half is the project's,
and they are fixed in different places.

**The notation, proposed as he asked:**

- A channel is written the same everywhere a person or a file sees it: `sw`, `w-L/R`, `m-L/R`,
  `tw-L/R`, `r-L/R`, `c` — plus `sw-f`/`sw-r` and `c-H`/`c-L` where the car has them. A hyphen carries
  the side or the variant; an underscore never appears inside a code.
- `_` is reserved for the series (`_49`) and appears in a title only there.
- `id` equals the code at birth and never changes; after a rename the CODE moves and the id stays —
  in the same notation it was born in.
- `parse` refuses a code with `_` in it, and resolves the code against the glossary and
  `previous_names` instead of returning whatever sat before the last underscore.
- The six ids already on disk in the other notation are data, not code: correcting them is the
  Arbiter's call, and the check that would have caught them is `id` ∈ {code} ∪ `previous_names`.

---

## S-043 · Phase 0 asked for a whole-system sum, which its own capture plan never listed — FIXED

**Status**: done 2026-09-19 · W-1 collection · the Arbiter, reading the session's Phase-0 plan: step
0.5 («Сума `ALL_1` / `ALL+C_1`») «чомусь потребує п.0.5, хоч це абсурд зараз міряти будь-які суми —
виправ в скілі».

He is right twice over. **Nothing is aligned at Phase 0** — no delays, no tuned crossovers — so `ALL_1`
measures the unaligned system and answers a question nobody asked. And on this car it could not be
taken at all: the protective high-passes sit below 1.1 × Fs, so the pre-sweep safety gate refuses any
new sweep through the mids and tweeters. The demand also contradicted the method's own capture plan,
which lists Phase 0 as solos and the whole-system captures at the verify pass
(`naming-and-structure.md` §3).

**Fixed, not just recorded** (his instruction): `phase_0_baseline.md`'s centre bullet now captures the
centre like any other channel and says plainly that the with/without-centre SUM is not a Phase-0
capture, pointing at `ALL_final` / `ALL+C_final` where an aligned state exists to check the prediction
against; and `naming-and-structure.md` §3's Phase-3 row now names `ALL+C_final (rta)` beside
`ALL_final`, so the two documents say one thing.

---

## S-044 · A phase boundary has no cleanup procedure, and the session cannot clear itself

**Status**: done 2026-09-20 · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (the S-044 block: it refuses over an open round and a todo step, then prints the resume line) · `process.py <project>/process handoff` — found 2026-09-19, the Arbiter asked the session what to do about clearing
after Phase −1 and there is no such procedure — «раніше ми обговорювали, що добре кожну фазу починати з
чистої сесії — що можемо зробити?».

**Due when:** the next phase boundary. It is a mechanism question, not a prose one.

What exists today: the session can neither restart itself nor `/clear` — it said so and improvised the
rest well (it recorded the phase, named what is on disk, told him which REW session to keep open and
what to say afterwards). TCC keys its sessions BY PHASE, so the next launch in a new phase already
opens a fresh one. What is missing is the half that makes clearing safe: nothing CHECKS that everything
the next session needs is on disk before the chat is thrown away.

**The shape: a handoff that refuses.** `process.py <project>/process handoff` verifies, and prints one
resume line when it passes: the phase is recorded; every plan step of the closing phase is done,
skipped with a reason, or superseded; no capture round is left open; the ledger HEAD exists for the
active preset; the ▶️ CONTINUE block and the phase's decisions are written. Refuse — naming what is
missing — and the session keeps working instead of the Arbiter losing a chat that held the only copy.
The line it prints is what he says next («продовжуй»), plus what must stay open (the REW session with
the round's captures), so the instruction is not improvised twice.

TCC's half is one offer at the boundary — «почати фазу з чистої сесії» — and it already has the
session-per-phase key it needs; it rides as a ticket once the command exists.

---

## S-045 · After `/clear` the session came back in English: the language has no machine home

**Status**: done 2026-09-20 · W-1 package B · `python3 rew_tool/project.py <project> language` (exit 3 = unanswered) · `python3 rew_tool/contract.py check <project>` prints it above the file table · selftests in `project.py` and `contract.py` — found 2026-09-19, the Arbiter, right after clearing by hand at the phase
boundary: «після очистки мова переключилась на англійську».

**Due when:** immediately after S-044's handoff — clearing is the moment this bites, and the two are
one story.

Measured: `intake.field("project.language")` carries `writes: None` and `lands: "a recorded decision
(-1.1) + every project file"`, and `car/passat-b8-2026/project.json` has no `language` key at all. So a
fresh session has nowhere to READ it: the conversation that settled it is gone, the recorded decision is
free text that nothing in the start sequence goes looking for, and `happy-paths.md` §1 and SKILL.md's
pre-session — the two places that say what to reconcile before speaking — do not mention the language.
The only remaining source is the front-end's own report (`get_tcc_state` carries `language`), and it did
not reach this session.

**Corrected the same day, and it moves the root.** The next session's own report said: «This session
was started with English as the project language, but TCC's record says Ukrainian (your decision #1).
You may want to align that in TCC.» So the front-end's record WAS there, the session READ it, NAMED the
mismatch — and answered in English anyway, then advised him to go fix it in the app. Storage is half the
fault; the other half is that nothing makes a session act on what it just read about the person it is
talking to. A read value that changes nothing is not a setting, it is trivia.

**Why the damage is disproportionate to the fix:** the first reply is already in the wrong language, so
the person's first act after a clean start is to correct the machine about himself.

**The shape:** `project.json` carries the language, `intake.save` writes it like any other confirmed
answer, and the pre-session reconcile reads it BEFORE the first reply — a front-end's report still wins
when it is there, because the app is where the person actually set it. Two fields, not one, if his
S-037 point 2 stands: the AI's language and the person's can differ.

---

## S-046 · The reply reports everything the session checked, and the reader has to find the one line that is for him

**Status**: done 2026-09-20 · W-1 package A · `grep -n "A step reply is THREE things" skills/autosound-tuning/SKILL.md` — found 2026-09-19, the Arbiter, handing over a whole session reply: «ось
приклад зайвої інформації». It is the first message after a clean start, and the exhibit is kept below
because the item is about proportion, which a paraphrase destroys.

**Due when:** the reporting rule is next written — with S-038 and S-040, which are the same failure in
smaller pieces.

**What the reader owed**, on his own reading: he is at step 0.6, it is desk work, it needs no new
measurements — start it or not. Three lines.

**What arrived:** the method version matching on both sides · the project-file check being clean · the
only saved DSP state and the fact that nothing was agreed-and-unentered · REW being open with all eight
solos · the full list of the four still-open steps · why Phase 1 will not open · a preview dump of 44
proposed flaw rows with per-channel counts and three caveats about them, before any of it was asked for
· the midbass arrival reading again (S-038) · a four-row table of protective minima for a sweep that is
blocked anyway · three sub-points on why that sweep cannot be verified · two «small things in the
files» · and finally the question.

**The rule, in his own correction (19.09): A CHECK THAT PASSED COSTS ONE WORD — «Зроблено».** Not
silence: he wants to see that the checks ran, and he does not want a paragraph each. So the whole
reconcile is one line — the checks, done — and a check that FAILED is the only one that gets sentences,
and gets them in the useful form: **what to do about it, or the options to choose from, with the one I
recommend named first and why** (his standing rule for menus). The draft below said silence; his version
is better, because a session that says nothing about its checks is indistinguishable from one that
skipped them.

**What that replaces:** The version match,
the clean project file, the open REW session, the ledger HEAD — four sentences in the exhibit, one word
between them under the rule. Same for a tool preview nobody asked for: `flaw_map --rew 1` was run to see, not to
report, and 44 rows with counts per channel is a working note, not an answer.

**The shape:** a step reply is three things — where we are (one line, the checks folded into it as
«зроблено»), what is next and what it needs (one line), and the question that actually needs him. A
failed check replaces the second line: what it blocks, and what to do — or the options, recommendation
first. Everything else — the inventory, the caveats, the previews, the reasoning — is available on
request and lives in the files it came from. Same family as the hub's rule that a mechanism's refusal is
not retold: here it is the mechanism's SUCCESS that is not retold.

---

## S-047 · The flaw map writes «the question was not asked» on every row, and has no way to ask it

**Status**: done 2026-09-20 · W-1 package D · `python3 skills/autosound-tuning/rew_tool/flaw_map.py --selftest` (the request) · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (the phase gate) — found 2026-09-19, the Arbiter: «чому скіл сам не запитав про такий
замір?» — after offering, unprompted, the nine-position sweep set he already had on disk
(`9points-mes.mdat`, 63 sweeps `<ch> p1…p9_49 (sw)`).

**Due when:** the flaw map is next run on a project with no ellipsoid.

The session's own account is honest and incomplete: it says the method tells it to ask the owner for
the measurement that settles a hypothesis — the first example named there being a set of positions —
and that it substituted the moving-mic RTA because that was already on disk, then wrote 43 rows marked
«stays put — assumed». True, and it is the second time this wave that a rule living only in prose did
not fire (S-038, S-046 are the same shape).

**What makes this one sharp:** the TOOL already knows. `flaw_map.py` says it in its own words —
«absence of positions does not mean "stays"; it means the question was not asked» — and stamps every
such row `no positions measured -- staying is ASSUMED, not shown`, `status: hypothesis`. So the missing
question is computed, written 43 times, and carried nowhere. Meanwhile the reader for that data exists
(`ellipsoid.py`), and the way to express the request exists too: when he finally asked, the session
opened `cap_006` with 63 expected titles in the grammar, correctly, in one move.

**The shape:** a run that produced ASSUMED rows ends with the request, not with the rows — the channels
affected, the titles that would settle them (`<ch> p1…p9_<N> (sw)`), and the offer to open the round
(`capture-start`). The phase does not close while assumed rows exist and no request is on record. And
one sentence earlier in the phase — «чи є у вас заміри позицій?» — would have found this file before 43
hypotheses were written from a substitute.

---

## S-048 · Another project's series number walks into this one, and nothing says it is foreign

**Status**: done 2026-09-20 · W-1 package C · `python3 skills/autosound-tuning/rew_tool/state/process.py selftest` (a foreign series refused until its origin is on record) — found 2026-09-19, the Arbiter, on the nine-position file the session was
about to take in: «а ще 49 сесія це ж з попереднього проекту — запиши що це треба правити».

**Due when:** measurements are next brought into a project from outside it.

The session saw it and said it — «це серія `_49` зі старого проєкту, не червнева `_1`, на якій стоїть
карта» — and then opened round `cap_006` **as series 49**, with 63 expected titles `<ch> p1…p9_49 (sw)`,
which writes another project's numbering into this project's record as if it were its own.

`_N` is project-scoped in fact and nowhere in writing: `naming-and-structure.md` §3 defines `_N` as the
series number and spends a paragraph separating it from the ledger's `v_NNN`, but never says the number
belongs to ONE project. Two projects both have a `_49` and they mean different DSP states on different
days. Joining a foreign `_49` to a flaw map built on this project's `_1` is the same class as S-024's
imported `fs_hz`: data from another build arriving with nothing on it that says so.

**The shape:** captures that come from outside the project are recorded with their ORIGIN — the project
they were taken in and the series they were `_N` of — and this project gives them its own series for
anything it will join. A round refuses a series number that is not this project's unless that origin is
on record; `naming.py` says `_N` is scoped to the project in the same breath as it says it is not
`v_NNN`. The acoustic question the session asked — was anything changed in the install between the two
dates — stays a question for the Arbiter; this one is mechanical and should never have reached him.

---

## S-049 · No desk engine on the test MacBook, and nothing said so until Phase 1.3

**Status**: done 2026-09-23 · W-2 package C · the second half: `install.sh` and `install.ps1` write `install-receipt.json` (which installer, its sha256, the method tag, the time, the platform, what it did about the engine), and `doctor` reads it back in one line or says there is none (`autosound_ai.py selftest`, the S-049 block) · was: open 2026-09-20 · **W-2 package C** (`docs/PLAN-W-2.md`) · · W-1 package D · `python3 skills/autosound-tuning/rew_tool/resonalyze_engine.py --selftest` (engine_status builds nothing) — FIRST HALF only; the installer receipt stays W-2, and this item stays open for it — found 2026-09-19, the Arbiter: «ось що бачу на MacBook Pro — немає
рушия!». The session had to stop at step 1.3 (crossover variants) and ask him to install one, mid-tune.

**Due when:** the version installed there is known — that is the one fact this item is missing.

Measured here: `v3.0.58`'s `install.sh` already carries the engine logic (`WANT_ENGINE`, `auto` =
fetch where the machine has no .NET SDK to build from), and the release carries the right asset —
`resonalyze-engine-b0ce9fb-osx-arm64.zip` with `SHA256SUMS`. `v3.0.57`'s installer has none of it. The
session reported that machine has neither a prebuilt engine nor .NET, which under `auto` is exactly the
case that fetches. So either the install there predates 18.09, or the fetch did not run — and either
way it was silent.

**The part that is a fault regardless of the root:** `install.sh`'s own comment says the reason for
fetching is that a person «would otherwise discover that in the middle of a tune». He discovered it in
the middle of a tune. A guarantee whose failure is only visible at the moment it was meant to prevent
is not a guarantee: the engine's presence belongs in `doctor`/`selftest`, named on a machine BEFORE a
project opens, and a fetch that fails during install has to be loud rather than left for Phase 1 to
find.

**Answered at the machine, 2026-09-20.** `deployment.py` there: method `3.0.58` (`66f6bdf`), both copies
in step. The engine is present NOW — `~/.local/share/autosound/engines/resonalyze/b0ce9fb/osx-arm64` —
because the SESSION offered to install it mid-tune and he agreed, not because the installer did it.
`dotnet --version`: absent. And the installer «не казав нічого» about the engine.

That settles the root: `v3.0.58`'s installer speaks in EVERY branch of its engine step — «the .NET SDK is
here», «~30 MB for <tag>, checked against the release's SHA256SUMS», or a warning — while `v3.0.57`'s has
no engine step at all. Silence on a machine with no .NET means the install.sh that RAN was older than the
feature: the `curl` URL pins the installer, so an old bookmark installs old logic while the skill itself
updates to the newest tag. **The fetch is not broken.**

**Two real defects remain, and they split across waves:**

1. **The method never checks the engine itself** — `doctor`/`selftest` say nothing about it, so a machine
   that installed before the feature stays quiet until Phase 1.3 asks for a crossover search. One line in
   the doctor: present or absent, the pin, the platform, and how to get it. **Taken into W-1** (his
   decision 2026-09-20) — it is the line that would have replaced this whole exchange.
2. **The installer leaves no receipt** — nothing on the machine says which `install.sh` ran or what it did
   about the engine, which is why answering this took four exchanges instead of one command. **W-2.**

---

## S-050 · W-1: collection is closed — what the review has to decide

**Status**: done 2026-09-20 · the review happened, the scope was settled at four packages, and the wave shipped — `git show v3.0.59 --stat`. The eleven items it did NOT take stay open in this file and are W-2's collection (the Arbiter, 2026-09-20: he will not test until they land, and the intake form S-033/S-037 is the one thing that may wait beyond them, as its own session). Found 2026-09-19 · the Arbiter closed the wave's first step with «на сьогодні все, збір
закінчено». Written as the to-do for later, and nothing was started after his word.

**Due when:** he opens the review (WAVES.md §1 step 2).

**What is in the pool:** S-024 … S-049 — twenty-six items, one of them already done (S-043, the
whole-system sum removed from Phase 0 at his instruction). On the bus: hub `#185` (what a car package
may carry, per class, his decisions of 19.09) and `#186` (four things nobody has decided), plus a
comment on `#185` carrying the import's name-store half. In the skill's own repo: `#47` from the test
session, and `#38` untouched.

**What the review owes, in the order the items force:**

1. **The milestone.** None exists in either repo and none was opened here on purpose: `W-1` is read,
   not agreed (`WAVES.md` §1), and its five lines need the decisions this review makes (hub `#180`).
2. **The reporting rule** — S-046 with S-038, S-040, S-041 under it. It is the one change that touches
   every session on every car, and it is cheap: a passed check costs one word.
3. **The intake**, which he settled twice over: simplified (S-041) and served as a form (S-033), with
   the eight points of his first reading (S-037) and the two that are not about the form at all — the
   reviewer channel and the project directory belong to project creation, and the DSP capability block
   should never be asked for a processor the library already describes.
4. **Provenance**, the shape shared by S-024, S-036, S-042, S-045 and S-048: an imported Fs, a bulk
   `OFF`, a minted id, the language, a foreign `_N` — five facts whose ORIGIN is not written, each read
   later as somebody's word.
5. **The mechanisms that carry a rule instead of prose** — S-047 (the flaw map cannot ask for what it
   needs), S-044 (a handoff that refuses), S-034/S-035 (the feedback rail), S-039 (supersede a capture).
6. **S-049 needs two lines from him first** (the version on that MacBook, what the installer said);
   until then it cannot be split into «an old install» and «the fetch is broken».

**Not for this wave unless he says so:** the branch `w1` carries the form prototype and the
whole pool. It has no PR: what ships in W-1 is the review's call, not the branch's.

## S-051 · A driver's mount and aim, as the method's own model — an idea, not a question yet

**Status**: dropped 2026-09-22 · the Arbiter: «варіанти списком скасували» — the mount and the aim are not lists to choose from. The intake's free text is the model (`channels[].install`, `hardware.description`), and the session reads it where an aim changes the reading (W-2 A.7), so no work turns this idea into a feature · was: deferred 2026-09-22 · W-2 review, the Arbiter: «що не включемо — то зрозуміти причину і відкласти» · an idea — nothing computes from mount or aim; comes back when a tool starts using them · the free text IS read: W-2 package A.7 has the session read `channels[].install` / `hardware.description` where an aim changes the reading (the Arbiter's example: «направлено на водія в вухо») · was: idea 2026-09-22 · the Arbiter, reviewing the intake form: «що таке "Підніжка"?», and a list
of what real installs have. Not on the form: nothing in the method computes from a mount or an aim
today, and his rule is not to ask what we cannot compute («все це в інше, як ідея»). The intake keeps
`channel_map.position` and `channel_map.enclosure` in its data (`place="memo"`); the person describes
them in «Інше обладнання»'s free text.

**His list, as he gave it.** Where: the kick zone (low, by the pedals), behind the pedals (seen on
Mercedes), the C-pillar, and the ones the enum already has (door, A-pillar, dash, deck, rear shelf,
under the seat, trunk). **Where it points, separately**: at the driver, the middle of the cabin, the
windshield, into the cabin, towards the trunk lid, into the trunk, other.

**Due when:** a tool starts using mount or aim, e.g. to predict path length and reflections from the
geometry, or to weight a driver's off-axis response in the junction verdict. Then the two lists become
two questions, where and aim, and not before.

## S-052 · Intake review of 2026-09-22: where it stopped

**Status**: done 2026-09-22 · W-2 package A · item 1 answered and written: `grep -n "Whatever is still empty is asked in Phase 0" skills/autosound-tuning/references/phases/phase_-1_intake.md` and `grep -n "If it is empty, ask after the baseline" skills/autosound-tuning/references/phases/phase_0_baseline.md`; items 2–5 went into the W-2 composition (`docs/PLAN-W-2.md`) · was: open 2026-09-22 · **W-2 package A** (`docs/PLAN-W-2.md`) · the W-2 review of the same day took items 2–4 into the wave and closed `#47`/`#49`; item 1 answered the same day (below); what keeps this open is package A's prose for it · eight rounds with the Arbiter on the intake form, all on branch
`wave-2026-09-20` (`b882676` … `1075c65`), decisions in `docs/DESIGN-2026-09-22-intake-simplified.md`.
The branch has no PR; what ships is the next review's call.

Left for later:
1. **Answered at the W-2 review, 2026-09-22:** «ми в форму інтейка це вже додали. хай там і буде. але
   якщо не задано, то так запитати». The curve and the goal/taste questions stay on the form, and Phase 0
   asks, after the baseline, whatever is still empty (`docs/PLAN-W-2.md` A.2).
2. **TCC's half:** hub `#194` (SKL-049, how to start and stop the form) and `#193` (SKL-048, the
   seat chosen in the copy dialog).
3. **Sessions review:** skill `#58` (the Antigravity session vs the Opus one, a two-tier plan P1–P12).
4. **Pool:** `#47` and `#49` are unpinned from the closed W-1 milestone and wait for the next wave's
   composition. `#48` is closed with evidence (v3.0.59).
5. **Reviewer channel on this Mac:** the Gemini API key is invalid (HTTP 400), so the advisor ran through
   `agy` with `AUTOSOUND_ALLOW_NESTED_CLI=1`. A valid key, or a pinned
   `AUTOSOUND_CRITIC_MODEL`, removes that detour.

## S-053 · Versions are numbered once per project, and a preset is the slot a version is fixed in

**Status**: done 2026-09-22 · W-2 package R · `python3 skills/autosound-tuning/rew_tool/state/state.py selftest` (the per-project line, `migrate-line` plan → a stopped move resumed → `--apply`, the active slot keeping its numbers, a half-moved root refused both ways, `variant new/switch` copying nothing); tried on a copy of the Passat's `state/` (SQ `v_001…v_063` kept, FULL → `v_064…v_070`, content identical); the reader contract and the build are on hub `#195` · was: open 2026-09-22 · **W-2 package R** (`docs/PLAN-W-2.md`) · hub `#195` (TCC-025) asks for the same thing, and tcc needs it in this wave; the reader contract goes on `#195` first · written down at the W-2 review:
the item had no home in this file. It lived only in `docs/PLAN-W-1.md` §A.3 as "W-2, not this wave",
and tcc left per-project version numbering out of its own W-2 because this migration does not exist
(tcc `docs/PLAN-W-2.md`, *Not included*).

**Due when:** W-2, package R. It goes with skill `#58` P2 (variants inside the ledger, no project-local
switch scripts) and P1 (a banked version is immutable).

**The model, the Arbiter's (settled 2026-09-20):** a version `v_NNN` is the full set in the processor,
numbered once per PROJECT. A preset is the DSP slot a version is FIXED in (`01` before the competition,
`02` the test one). A slot holds one version at a time, and several versions pass through it while
testing.

**What the files do instead:** `state/<preset>/v_NNN.json` is a separate line per slot, so two slots
both hold a `v_001`, and there is no «put this version in that slot» move. The passat's own registry
note says the relationship in prose it cannot verify («FULL — копія SQ … синхронізація після v11.0
не підтверджена»). Until this lands a report names the version with its slot (`SQ v_007`,
`docs/PLAN-W-1.md` §A.3).

**Done when:** a project has one version line, a preset records which version it holds and since when,
an existing project migrates with nothing lost (the old per-slot files kept as history), and
`contract.py check` reads the new shape.


## S-055 · The min-phase verdict meets real data, and decides the dips below Schroeder

**Status**: open 2026-09-23 · waits for the next ellipsoid round on the Passat · from
`docs/RESEARCH-2026-09-23-min-phase-verdict.md` §5 and decision 39 in `docs/W-2-DECISIONS.md`.

The criterion is settled from the sources and built (`eq_gate.min_phase_verdict`, `min_phase_across`).
Two things wait for measurements, and neither is a question for the Arbiter:

1. **The check.** For w-L and m-R, the 9 sweeps of one ellipsoid round, an `-EP` of each read at
   `smoothing=None`. Run the verdict at the w-L 90–127 Hz peak (expected MIN), the w-L ~150 Hz dip
   (the car record says NON, a research note says EQ-able) and the m-R ~645–662 Hz SBIR (expected NON),
   at ±1/6 and ±0.5 oct, with the channel delay. Record the residual per take, the floor and the verdict.
   This shows whether the 10° floor ever binds, whether ±0.5 misreads the peak, and settles 150 Hz.
2. **Then `flaw_map`'s dips below Schroeder.** `flaw_map.py` writes every one as `cabin_null / no_boost`.
   `diagnostic-techniques.md` §13 and `phase_2_eq.md:55` say a dip there can be a legitimate target.
   The verdict is the evidence that decides it: MIN on 2 of 3 returns is a boost candidate within the
   +6 dB ceiling, and NON stays `cabin_null`. Wired after item 1, since that item is what shows the
   verdict holds on this cabin.

## S-056 · The junction level step read over the SHARED band

**Status**: open 2026-09-23 · a candidate for the next wave · from decision 17 in `docs/W-2-DECISIONS.md`,
accepted by the Arbiter with this as the follow-up.

W-2 prints each junction's level step as the two blocks' OWN-band levels plus their gains, lower minus
upper (`resonalyze_engine.level_steps`, from the engine's `bandLevelDb`). #50 asked for the difference
over the band the two SHARE. On a sloped plateau the own-band number is an approximation. The shared-band
reading needs a new engine field (the level of each member over the overlap, both sides) and new goldens,
which is a rebuilt engine, not a patch.

## S-057 · A five-line verdict block for every tool's output

**Status**: open 2026-09-23 · a candidate for the next wave · from decision 45 in `docs/W-2-DECISIONS.md`,
accepted by the Arbiter with this as the follow-up.

#57 P5 asked for compact output. W-2 made it where the issue measured it: `predict`'s notes collapse by text,
at most five show unless `--verbose`, and the missing-title error names the count and the three nearest titles.
The rest is a shape for every tool: a verdict block of at most five lines first, then the detail on request.
That is a redesign of every tool's output, not a patch.

## S-059 · v3.0.61's TCC upgrade path, run on the Windows VM

**Status**: open 2026-09-23 · his step · from skill #62, fixed in v3.0.61 (`git -C skill tag --contains c4fc023` →
`v3.0.61`).

Two runs of the install line on the VM, the same one-liner at v3.0.61:
1. **With TCC running.** Expected: "Autosound TCC is running, so its files are in use… left as it is", and in
   Checking "was here before and was not upgraded". The app still starts afterwards.
2. **With TCC closed.** Expected: "OK installed". TCC is uv's now, so there is no `--force`.
The not-owned case (a launcher TCC's own updater put there) comes back by itself after the next in-app update of
TCC. Then run the install line once: expected "the app's launcher here was not put there by uv … replacing it",
then "OK installed", and the app starts.

## S-058 · The reviewer key through TCC on the other MacBook

**Status**: done 2026-09-23 · the Arbiter moved the key through TCC's menu (v0.1.43, hub #197), and a critic call from TCC answered in 69 s, where on 19.09 the same call came back empty (his report, TCC's own session line) · was: ready 2026-09-23

The Arbiter wants the key checked through TCC, since TCC is where "the key in ~/.zshrc is not seen" came from.
On this MacBook the move is done and checked (`key status`: keystore, AQ., 53; `doctor`: the key is live).
On the other one, after TCC's release: update the skill to `v3.0.60` or later, then in a NEW Terminal tab run
`autosound_ai.py key status`, then `key move-shell` (or `key set google`). Close any editor holding `~/.zshrc` first:
nano saving an older buffer put the key back here once. Then open TCC from the Dock and check that its reviewer
indicator reads the keystore (#197). Run one review. Until TCC's release, its own vendored skill reads the key only
from `critic-env`, so the key stays there for that TCC.

## S-054 · W-2 · v3.0.60: released

**Status**: done 2026-09-23 · `git -C skill tag --contains 03ba97c` → `v3.0.60`; PR #59 merged `--ff-only`, `scripts/tag-check.sh v3.0.60` → all 4 checks passed (the channel 14/14); milestone `W-2 · v3.0.60` closed with its 9 issues; hub #185 #186 #187 #192 #195 #199 #200 #201 closed with their proof lines · **left, his steps:** S-020 (the Windows VM run at v3.0.60), S-021 (the passenger-seat project on the Passat), the car role's hub #196; TCC's halves ride hub #197 #198 · was: waiting 2026-09-23

**Due when:** he is back. In this order:
1. **The decisions log first** (his word: «завтра почнемо з принятих тобою рішень»): `docs/W-2-DECISIONS.md`. Row 33 is reverted. Rows 34 and 44 were answered 23.09 (row 46: a desk result is evidence, and the car verifies several changes at once). Row 41 was never a real question: the method already sets a junction's phase from sweeps and checks the sum with RTA (`docs/RESEARCH-2026-09-23-junction-alignment-measurement.md`). **The rows the session marked (8, 18, 39, 40) were answered 23.09 and are built**: the CLI wait grows with the job (8); levels are always the DSP's, and an amp gain he turns is recorded (18); the min-phase verdict is settled from the sources (39, research note; its real-data check is S-055); with no crossover type set, an LR24 base goes on the front (40). His second point on row 8, the reviewer's key, is researched (`docs/RESEARCH-2026-09-23-reviewer-keys.md`). On his choice it is built in W-2: `autosound_ai.py key set|status|rm|move-shell`, the Keychain and DPAPI. TCC's half is hub #197. **The whole log was reviewed with him on 23.09** (rows 1–46); follow-ups are S-055, S-056 and S-057. His word for the merge and the tag came the same day.
2. **The merge and the tag**, on his word: `git merge --ff-only` into `main`, push, `scripts/tag-check.sh v3.0.60`, the tag. Then close the milestone and the issues it names, and close hub #178/#185/#186/#187/#192/#195 with the tag as the proof line.
3. **His two runs**: S-020 (the Windows VM, no .NET SDK: the README one-liner at v3.0.60, then `resonalyze_engine.py smoke`, then `-NoEngine`), and S-021 (a passenger-seat project on the Passat, Phase −1 → the trade-off front).
4. **The car role's half**: hub #196 (the Passat's ids, its gain step `0.1`).
