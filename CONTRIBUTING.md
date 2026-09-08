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
- Added a CHANGELOG entry for user-visible changes.
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
  selftest, 67 in all (2026-09-09; the runner prints the current count itself —
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
