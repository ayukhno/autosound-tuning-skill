---
description: Install the Tuning Command Center (TCC), the optional desktop app for this skill
argument-hint: "optional: cli — install without the window"
---

# Install the Tuning Command Center

The user asked to install **TCC** — the desktop app that shows this project's DSP state, its
measurements and its curves while a session runs. It is optional: this skill works on its own in a
terminal, and everything below is an addition, never a requirement.

Do not install anything before showing the exact command and getting a "yes".

## What you are installing

TCC ships in pieces, because two of them are hundreds of megabytes and both are choices:

| you want | command |
|---|---|
| the window, driven by Claude (the usual one) | `uv tool install --python 3.12 --constraints https://raw.githubusercontent.com/ayukhno/autosound-tcc/<tag>/constraints.txt 'autosound-tcc[gui,claude] @ git+https://github.com/ayukhno/autosound-tcc@<tag>'` |
| the window, driven by Gemini/Codex through `omp` | `uv tool install --python 3.12 --constraints https://raw.githubusercontent.com/ayukhno/autosound-tcc/<tag>/constraints.txt 'autosound-tcc[gui] @ git+https://github.com/ayukhno/autosound-tcc@<tag>'` |
| no window — CLI and the MCP server only | `uv tool install --python 3.12 --constraints https://raw.githubusercontent.com/ayukhno/autosound-tcc/<tag>/constraints.txt 'autosound-tcc @ git+https://github.com/ayukhno/autosound-tcc@<tag>'` |

**`<tag>` is TCC's newest release, read when you run this** — the one the installers pick:
`git ls-remote --tags --refs https://github.com/ayukhno/autosound-tcc` lists them; take the highest `vX.Y.Z` (a `v` and
three numbers, compared as numbers — `v1.1.10` above `v1.1.9`; never a `beta-…` candidate). If the list cannot be read, stop and say so: never install without a tag.
This skill names no TCC version on purpose: TCC pins the skill it was built with, never the reverse, which is why the
skill is released first (W-11). **The tag is not decoration.** Without it `uv` takes the repository's default branch,
and the two ways into TCC — this command and the installers — stop giving the same app (SCR-054, HUB-030). The
installers also check the tag's signature, which this page does not. **Nor is `--python 3.12`:** without it `uv` takes
whatever Python it finds, and an older one fails as a broken package. **Nor is `--constraints`:** it holds TCC's
dependencies to the versions that tag was tested with (its `constraints.txt`), as the installers and TCC's own updater
do; without it `uv` resolves them afresh. What `scripts/installer-consistency.py` checks here: no line names a TCC
version, each installs `<tag>` with `--python 3.12` and that tag's constraints, and the page says how `<tag>` is read.

Roughly 678 MB, 394 MB and 29 MB installed. Default to the first, since this command is being run
from inside Claude Code. If `$ARGUMENTS` contains `cli`, use the third.

## Steps

1. **Check `uv` is there:** `uv --version`. If it is not, do not improvise a substitute — point at
   <https://docs.astral.sh/uv/getting-started/installation/> and stop. `uv` is the recommended
   route specifically because it installs a suitable Python itself, which is the failure most
   people hit on Windows.
2. **Read `<tag>`:** `git ls-remote --tags --refs https://github.com/ayukhno/autosound-tcc`, the highest `vX.Y.Z`
   compared as numbers (above). Unreadable — no network, no git — is a stop, said as it is.
3. **Show the command you are about to run, `<tag>` filled in, and ask.** This writes to the user's machine and puts
   executables on their PATH. It is their decision, not yours.
4. **Run it.** It takes a few minutes: the Qt wheel is large.
5. **Check it landed:** `autosound-tcc --help`. If the shell cannot find the command, `uv` put it
   in a directory that is not on PATH — `uv tool update-shell` fixes that, and it needs a new
   terminal afterwards.
6. **Tell the user how to start it**, and that it opens on a project folder: `autosound-tcc
   --project-dir .` from the project they are tuning.

## Things worth saying, and not guessing about

- **TCC needs this skill; this skill does not need TCC.** TCC reads the files this skill writes.
  It finds the skill automatically when it is installed as a plugin (as it is now, if this command
  is running) or at `~/.claude/skills/autosound-tuning`. If the user keeps it somewhere else, the
  variable is `AUTOSOUND_SKILL_DIR`.
- **TCC does not log in to anything.** For Claude it uses the user's own authenticated `claude`
  session. Installing TCC does not create an account, a key or a bill of its own.
- **It writes nothing to the DSP.** TCC is read-only against the processor; automated writes are
  deliberately out of scope until the safety work behind them is done. Do not tell the user
  otherwise, even in passing.
- If the install fails, report what actually failed. Do not retry with `--force`, do not fall back
  to `pip install --break-system-packages`, and do not install into the system Python.
