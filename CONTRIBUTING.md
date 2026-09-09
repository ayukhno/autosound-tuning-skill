# Contributing

Thanks for your interest in the project! Below are the minimal steps and rules to get your contribution accepted quickly.

## Language / localization policy
- Primary language: English. Please write issues, PR titles, and descriptions in English where possible to help the widest audience and contributors.
- **English is the source and it is mandatory; a translation may lag.** A change lands in English and
  is finished there — nothing is held back waiting for three other languages. The machine-read
  references (`references/patterns/listening-cheat-sheet*.md`, `test-tracks*.md`) are built for that:
  ids are shared, only the free text differs, and `rew_tool/listening.py` falls back to English marked
  `translated: False` so a panel shows a real line rather than an empty one. Filling a language in is
  welcome and is tracked as its own task, never as a blocker.
- Translations are welcome: add them as README.<lang>.md (for example README.uk.md) or link them from the main README. Localized discussion or case studies may be written in the respective language, but summaries and key actions should be in English.
- **`README` and `FAQ` are the exception that is kept in step**, because they are the front door:
  `scripts/i18n-check.py` (in `run-selftests.sh`) compares what can be compared without knowing the
  languages — the sequence of heading levels, and the commands inside fenced blocks, where only
  `<placeholders>` may differ. A translation deliberately behind says so in its own first lines with
  the words `Translation lags the English original:` and its divergences print as notes instead of
  failing the run; silence is what fails. The guard sees divergence BETWEEN languages only — all
  four lagging the code together looks perfect to it, and that stays a person's judgement.

## Quickstart (local development)
1. Clone the repository and create a branch:
   ```bash
   git clone https://github.com/ayukhno/autosound-tuning-skill.git
   cd autosound-tuning-skill
   git checkout -b fix/short-description
   ```
2. Run the smoke test (offline, stdlib-only — no dependencies to install):
   ```bash
   python skills/autosound-tuning/scripts/smoke_test.py
   ```
3. If your change affects skill triggering, see `skills/autosound-tuning/evals/README.md` for the trigger eval set and how to run it.

## Branching and commits
- Use branch prefixes: `fix/`, `feat/`, `docs/`, `chore/`.
- Keep commit messages short and clear. Conventional Commits are encouraged but not required.

## Pull requests
Before opening a PR, make sure you have:
- Updated the documentation if behavior changed.
- Run the smoke test (and evals, if relevant) and fixed any failures.
- Added a CHANGELOG entry for user-visible changes — and if you added a version section, run
  `python3 scripts/changelog-index.py` so the index table at the top of the file carries it. The
  table is generated, never hand-edited: `--check` runs in the suite and fails on a stale one.
- **Touched an installer? Touch all three.** `install.sh`, `install.ps1` and `install.cmd` carry the
  same decisions in three languages, and a change made in one is a divergence, not a fix. Run
  `python3 scripts/installer-consistency.py` — it compares the constants that must match and fails
  when they drift. It checks values, not logic: a pass does not mean the three files still *do* the
  same thing, so read all three anyway.
- **Touched an HTML tool? Text from outside is data, never markup.** In
  `target_curves_visualizer.html` a curve's name arrives from three places the page does not
  control — the dropped file's **name**, a `# NTT: Name` line inside its **body**, and the
  `#curve=` **link fragment** — and every panel prints that name (readout, comparison table,
  deviation report, card). It reaches the DOM only as `textContent` or through `esc()`; our own
  markup is the string that value is pasted into. And **a helper whose name does not say
  "escaped" must not be the last thing a foreign value passes through**: `cleanLabel()` strips
  the trailing `(loaded)` bookkeeping, looked like a sanitiser, and a curve named
  `<img src=x onerror=alert(1)>` executed (autosound-hub `HUB-040`). `scripts/html-data-check.py`
  fails the suite on the direct form and on any call to `cleanLabel()` outside `labelHtml()`; it
  is a lint, not dataflow, so the end-to-end proof stays a browser. Run by a person, not by CI:
  `node scripts/xss-proof-visualizer.mjs <the .html>` drops that file name, that name inside a
  file body and that name in a `#curve=` link into headless Chrome and reports whether the text
  stayed text — or drop such a file by hand and read the card.
- **Run `scripts/run-selftests.sh`** — the installer check plus every `rew_tool` module's own
  selftest, 69 in all (2026-09-09; the runner prints the current count itself —
  `scripts/run-selftests.sh | tail -1`, and that command is the answer, not this number). It needs
  `numpy` and `scipy` (`dsp_math` and `eq_gate` import scipy by name, and the `dsp_math` selftest
  designs crossovers). CI runs this exact script on push and PR, so a green run here is a green run
  there.
- **Deliberately without a selftest:** `make_plot.py`. It renders one synthetic PNG for a
  one-off experiment (does a model read a picture of a curve better than the numbers?), and
  covering it would mean adding `matplotlib` to CI for a module no part of the method calls. A
  new module without a selftest needs a line here saying why — an empty one is worse than the
  honest exception.
- **Run `uvx ruff@0.12.0 check`.** CI runs it too, and it fails the build. Which rule classes are
  on and why the rest are off is written in `pyproject.toml`, next to the choice.

PR checklist:
- [ ] Tests / smoke test pass locally (if applicable)
- [ ] `scripts/run-selftests.sh` passes locally (it includes the installer check)
- [ ] Description explains the change and motivation
- [ ] Documentation / CHANGELOG updated (if needed)

## Licensing of contributions
By submitting a PR you agree to license your contribution under the repository's licenses: documentation — CC BY-SA 4.0 (see LICENSE); code and scripts — MIT (see LICENSE-CODE). To simplify rights management, please add a DCO sign-off to your commits:

- Sign each commit with `git commit -s` (this adds a line like `Signed-off-by: Your Name <you@example.com>`).

If you would prefer to sign a Contributor License Agreement (CLA) instead of DCO, mention it in the PR and we will agree on a format.

## License header for code files
Add a short header at the top of key scripts (for example in `skills/autosound-tuning/rew_tool/*.py` and `skills/autosound-tuning/scripts/*`):

```python
# Copyright (c) 2026, ayukhno
# Licensed under the MIT License. See LICENSE-CODE for details.
```

## Reporting a security issue
Do not report vulnerabilities in public issues or discussions. See [SECURITY.md](SECURITY.md) for the reporting process.

## Additional notes
- If your contribution includes third-party materials, make sure you have the right to submit them under the project's licenses, or state the licensing constraints in the PR (see `LICENSES/NOTICE.md`).
- Questions? Open a discussion or an issue with the `question` label.

---

# Maintainer notes — decisions about the method itself

These sections used to sit in `references/`, the folder a tuning session loads while it works. They
are not tuning steps: they are how the method's own internals were decided, and who signed each one.
A session in a car paid tokens for them on every phase and never acted on one. They live here now,
and the reference files carry a summary plus a pointer back (moved 2026-09-09, release review).

### ENTERABLE and MODELLABLE are two questions — never one field

A capability list gets asked two different things by two different callers, and they need opposite
answers:

* a tool that **VALIDATES** something a person already chose asks *can the device be given this?*
* a tool that **PROPOSES** asks *can we predict what it does?*

Chebyshev on a Helix answers yes to the first and no to the second: the processor accepts the
family, an experiment was run and could not identify its mathematics, so the ripple is unidentified
and the filter is not DETERMINED. Validating an entered one as enterable is correct. Recommending
one is not — a search that offers a filter we cannot predict is worse than a search that offers
nothing, because the tuner enters it and then neither party can account for the result.

**They live in different places, and that is the whole fix.** *Enterable* is a fact about a
PROCESSOR and belongs in its `dsp_profile.json`. *Modellable* is a fact about US — which
realisations this code has and trusts — and belongs in `dsp_math.MODELLABLE_FAMILIES`. Putting
"we cannot model this" into a device profile would be recording our own limitation in a file that
describes somebody's hardware, identical across every copy of that profile and stale the day our
maths improves. `dsp_math.options_for(profile_types)` is the intersection, and a proposing tool
should search that rather than either list alone.

This is the sub's 20–300 Hz UI range in mirror image. There, one field answering two questions
would have made a tool REFUSE something possible; here it makes a tool PROPOSE something
unpredictable. Same defect, opposite damage — so when a list is about to be consulted, ask which
of the two questions is being put to it.

### The intersection is now CACHED in the profile — and why that is not the thing forbidden above

Everything above holds, with one narrowing bought on 2026-09-05 (autosound-hub `RES-003`, from
`research`). The paragraph before this one forbids writing "we cannot model this" into a device
profile, for two good reasons: it records our limitation in a file describing somebody's hardware,
and it goes stale the day our maths improves. Both are objections to a **hand-written** marker, and
both were right about one.

What they did not cover is the reader who never runs our code. `options_for` is the intersection —
but a consumer reading `crossover_filters.types` straight off the JSON sees the family, its full
order ladder, and nothing at all. That is not hypothetical: `research` was that consumer, walked
`types` with its own loop, and its pilot recorded **`CHEBYSHEV12` as a winning crossover** after
modelling it with an invented ripple. The rule existed and could not be seen.

So each family now carries `modellable` + `modellable_note`, and the two objections are answered by
**how** it gets there rather than by argument:

* **it is generated, never typed** — `dsp_profile.annotate_modellable` derives it from
  `dsp_math.options_for`, and `save_profile` stamps it on every write. There is no second opinion
  to maintain, only a cached one;
* **stale fails the build** — `dsp_profile`'s selftest re-derives the marker for every bundled
  profile and compares. The day our maths improves, a profile still saying `false` stops CI with
  the family named, which is the opposite of quietly going stale;
* **absent still means ASK** — a profile written before the stamp carries no marker, and `None` is
  not `false`. A consumer that finds nothing does what every consumer did before: calls
  `options_for`. `dsp_profile.modellable_families(profile)` returns exactly that tri-state.

The decision stays in one place. What is in the data is its shadow, and a shadow that cannot drift
without stopping the build is not a second source of truth — it is the first one, made visible to
somebody standing outside the code.

### The one refusal that withholds a NUMBER

Written 2026-09-01 (`autosound-hub#31`). Everything in §2 says where a tool is **silent**. This says
where the method **refuses**, and it exists because that row was the *behaviour* and not the
*decision*: three commands leaned on a refusal nobody had signed, which is a mechanism that looks
ratified because it acts ratified.

**One verdict, one condition.** `protective.should_de_embed(record, channel, baseline=True)` returns
`("check", …)` for a channel that is **not marked raw, has no round record, and was captured at
baseline** — before any crossover existed. Nothing else in the method refuses on this ground.
`predict.de_embed_solos` is what enforces it: the channel is left out of `solos` and a note
`"<code>: REFUSED — …"` is added.

| command | when it can fire | what the caller gets instead of a number |
|---|---|---|
| `predict …` | only with `--baseline` | the channel is out of the prediction and out of any joint that uses it; `<code>: refused -- see notes` on stderr |
| `eq_propose --solos …` | always — baseline is passed unconditionally | no EQ package for that channel; `<code>: refused at de-embed …` on stderr in **both** modes (since 2026-09-01; before that it was invisible under `--json`, and the channel simply vanished from the proposal) |
| `flaw_map --solos …` | always | no flaw rows for it; `refused at de-embed (no recorded protective state): <codes>` in the report |

Every other channel proceeds, no exit code changes, and nothing is guessed on the refused one.

**What it never refuses** — worth listing together, because "it refuses on principle" is the fear:

- a **working** capture — the default is `no`, and that is an answer rather than a shrug;
- a capture **marked raw** — that one gets de-embedded, which is the whole point;
- a baseline capture **with a round record** — the record answers the question;
- a file older than the `protectiveState` mark (writer ≤ 3.0.27) — read as unfiltered, said out loud.

**The price of cancelling it.** Exactly one class of error comes back: rotation belonging to the
measuring rig, read as the car's phase. On the reference car's own protective set, with this
module's maths — HPF `LR4 @100` still owes ~52° at 320 Hz; LPF `LR4 @500` ~53.5° at 160 Hz. So a
junction three-ish times away from a protective corner carries about fifty degrees that is not the
car's. Live, on the same data through the same engine: the `w/m` left junction read **−49°** with
the protective filter left in and **+3°** with it removed (cross-check runs 3/4, 2026-08-18) — the
distance between "badly out of phase, fix it" and "leave it alone".

**Why a refusal and not a warning.** The omission cannot be detected in the data: a protective
`LR4 @100` and a designed `LR4 @100` are the same filter. The only thing that betrays it is *when*
the sweep was taken, and only a person knows whether the button was missed. A number produced
anyway looks exactly like a good one — which is why the answer is withheld rather than flagged.

**Signed off: the user, 2026-09-01 — the refusal stands.** In their own words, the design is this:
when curves are captured there is a place to declare a protective filter on a driver **with its
parameters**, and that declaration is exactly what tells the analysis to take it out; **no
declaration means a working capture**. It was specified that way for both consumers at once — TCC's
interface, and this method's logic, maths and terminal mode.

The baseline case above is the **one named exception** to that rule, and it was put to the author as
an exception and kept: at baseline an unmarked capture is *not* read as working — the method
withholds the number for that channel and asks a person. Cancelling it now takes a decision of the
same weight, not an edit. Recorded here because until this line existed the mechanism had authority
with no author (`autosound-hub#31`, split out of `#22`).

### How experience flows back into the skill

- `community-inbox/` (both `setups/` and `case-studies/`) is processed by **this maintenance loop** (harvest → correlate → fold): each item is checked against the skill; the origin tag `[source: <body>/<author>]` is kept.
- **Contradicts our conclusions → a VARIANT, not a deletion** (maintenance loop rule §2: a different geometry/cabin can make the tip right).
- **Hardware experience accumulates into the skill's profile library** (each new entry = **copy the blank `_TEMPLATE.md` and fill it**, so the structure/discipline is consistent):
  - `knowledge/cars/<body>.md` — the cabin map: PART A body-physics / PART B verify-only anomalies and the standing install (placement, aim, passives, enclosure), quirks (template `knowledge/cars/_TEMPLATE.md`; worked example — the Passat B8, de-identified). ⛔ **Never the tune's settings** — no crossovers, delays, EQ, polarities or levels, however well they worked: this base collects physics and how the build is put together, not solutions (`knowledge-architecture.md`);
  - `knowledge/dsp/<dsp>.md` — the capability profile (layers, EQ-exchange format, presets, quirks) (template `knowledge/dsp/_TEMPLATE.md`; worked example — `helix-dsp-ultra-s.md`).
  - `knowledge/approaches.md` — the **classifier of whole-system schemes** (crossover/slope approaches as variants tagged by setup context + success story + confidence + any competition result). Each finished tune **appends** the scheme it used; this is the seed of a public, community-rated classifier. ⚠️ A scheme is bound to ITS setup — never a format→slope recipe.
  At a new car's intake the skill **checks first** whether a profile of this body/DSP already exists (`project-intake.md §4`), and `knowledge/approaches.md` for schemes that worked on a similar setup (a shortlist of hypotheses, not facts).
- Thanks: a contributor line in the CHANGELOG.

### The truth model, as it was written in prose (superseded)

Every living project must have a **declared** answer to "where the truth lives", or the documents quietly diverge:
- **Canon** = the stable distillation (system, conventions, key conclusions, disproven hypotheses). Updated **at milestones**, not every session.
- **Live state** = separate files (the config state, a changelog with a resume block, the detailed round log, the decision audit-trail). Updated every session.
- Mirrors / fallbacks — explicitly marked ("SNAPSHOT", "mirror of the canon") with a pointer to the original.
- The truth model is **written identically at every entry point** (canon, the README, the skill) — a new session, from any side, sees the same scheme.
