# Contributing

Thanks for your interest in the project! Below are the minimal steps and rules to get your contribution accepted quickly.

## Language / localization policy
- Primary language: English. Please write issues, PR titles, and descriptions in English where possible to help the widest audience and contributors.
- Translations are welcome: add them as README.<lang>.md (for example README.uk.md) or link them from the main README. Localized discussion or case studies may be written in the respective language, but summaries and key actions should be in English.

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

PR checklist:
- [ ] Tests / smoke test pass locally (if applicable)
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
