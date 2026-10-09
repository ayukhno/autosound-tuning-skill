---
description: Set up what this plugin's method runs on — Python libraries, the reviewer, the desk engine — and check the plugin against its signed release
argument-hint: "optional: app — also the TCC desktop app"
---

# Set up the tuning method's tools

A plugin install copies this method's files and nothing else. The method's tools need more: numpy, scipy and
matplotlib in a working Python, a second AI as the reviewer (Gemini through `agy`), and Phase 1's desk engine where
the machine cannot build it. The plugin's own installer brings those, in **plugin mode**: the method is this plugin,
so it is **checked against its signed release** — every file, against the tag its author signed — and not cloned
again. A copy that does not match is not set up, and the installer says which files differ.

Do not run anything before showing the exact command and getting a "yes". It installs software on the user's
machine; that is their decision.

## The command

The installer is in this plugin: `${CLAUDE_PLUGIN_ROOT}`. Pick the line for the operating system:

| system | command |
|---|---|
| macOS, Linux | `bash "${CLAUDE_PLUGIN_ROOT}/install.sh" --plugin --terminal --yes` |
| Windows | `powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/install.ps1" -Plugin -Terminal -Yes` |

- `--terminal` / `-Terminal` leaves out the desktop app (about 700 MB). If `$ARGUMENTS` contains `app`, drop it:
  the installer then installs TCC as well. TCC is optional; `/autosound-tuning:install-tcc` is the other way in.
- `--yes` / `-Yes` is needed here: this runs inside Claude Code, where the installer cannot ask its questions. With
  it, sign-ins are **printed, not run** — they are the user's, in their own browser.
- Add `--dry-run` / `-DryRun` first if the user wants to see the plan without changing anything.

## Steps

1. **Show the line for this system and ask.** Say what it installs (above) and that it checks the plugin first.
2. **Run it.** A few minutes; the libraries and the engine are the large part.
3. **If it stopped on the check**, the line says which of two things happened — say that one, plainly, and stop:
   - «this plugin copy is not vX.Y.Z as its author signed it»: the files named are not what the author released.
     The way out is to reinstall the plugin, or to install with the installer from the README.
   - «this plugin copy could not be checked against its signed release here»: nothing was judged — the release did not
     answer (no network, a proxy), or git failed; the line above it says which. The copy may be fine: run the setup
     again when GitHub answers. Do not reinstall over it for this.

   Do not work around the check either way (`AUTOSOUND_SKIP_TAG_VERIFY` is a developer's switch).
4. **Relay the sign-ins it printed** as commands the user runs with the `!` prefix in this prompt — `! agy` for the
   reviewer, `! gh auth login` if they asked for the backup — and say they open a browser.
5. **Check the reviewer:** `python3 "${CLAUDE_PLUGIN_ROOT}/skills/autosound-tuning/scripts/autosound_ai.py" doctor`.
   On Windows use the Python the installer put in: `& "$HOME\.local\bin\python3.exe" …` — a bare `python3` there
   can be the Microsoft Store shortcut, which does nothing.

When it finishes ready (`Installed.`, exit 0), the plugin's start-of-session note stops asking for this setup until
the plugin updates to a new version; a new version is checked and set up the same way. When it ends `Installed, NOT
ready: …` (exit 3), the note keeps coming back: relay the parts it names, each with what its line says to do.

## Things worth saying, and not guessing about

- **The method's tools work in a terminal too.** This setup puts them where the method finds them; nothing here is
  tied to this session.
- **Nothing logs in on the user's behalf.** The reviewer, GitHub and Claude Code each use the user's own sign-in.
- **It writes nothing to the DSP.** Do not tell the user otherwise, even in passing.
- If the install fails, report what actually failed. Do not retry with `--force`, do not fall back to
  `pip install --break-system-packages`, and do not install into the system Python by other means.
