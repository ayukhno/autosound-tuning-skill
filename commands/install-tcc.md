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
| the window, driven by Claude (the usual one) | `uv tool install 'autosound-tcc[gui,claude] @ git+https://github.com/ayukhno/autosound-tcc'` |
| the window, driven by Gemini/Codex through `omp` | `uv tool install 'autosound-tcc[gui] @ git+https://github.com/ayukhno/autosound-tcc'` |
| no window — CLI and the MCP server only | `uv tool install 'autosound-tcc @ git+https://github.com/ayukhno/autosound-tcc'` |

Roughly 678 MB, 394 MB and 29 MB installed. Default to the first, since this command is being run
from inside Claude Code. If `$ARGUMENTS` contains `cli`, use the third.

## Steps

1. **Check `uv` is there:** `uv --version`. If it is not, do not improvise a substitute — point at
   <https://docs.astral.sh/uv/getting-started/installation/> and stop. `uv` is the recommended
   route specifically because it installs a suitable Python itself, which is the failure most
   people hit on Windows.
2. **Show the command you are about to run, and ask.** This writes to the user's machine and puts
   executables on their PATH. It is their decision, not yours.
3. **Run it.** It takes a few minutes: the Qt wheel is large.
4. **Check it landed:** `autosound-tcc --help`. If the shell cannot find the command, `uv` put it
   in a directory that is not on PATH — `uv tool update-shell` fixes that, and it needs a new
   terminal afterwards.
5. **Tell the user how to start it**, and that it opens on a project folder: `autosound-tcc
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
