# Advanced Setup

For those at home in a terminal: other ways to install and run the method, the installer's options, versions, and setting up the reviewer by hand. To start, the [README](README.md) and the [FAQ](FAQ.md) are enough.

---

## Table of Contents

- [Other Ways to Use the Method](#other-ways-to-use-the-method)
  - [Can I run the method entirely in Gemini?](#can-i-run-the-method-entirely-in-gemini)
- [The Installer](#the-installer)
  - [Updating, Locking Version, and Uninstallation](#updating-locking-version-and-uninstallation)
  - [Where are the components installed?](#where-are-the-components-installed)
- [The Plugin for Claude Code](#the-plugin-for-claude-code)
- [Versions and the 2.x Line](#versions-and-the-2x-line)
  - [How do I check the currently installed version?](#how-do-i-check-the-currently-installed-version)
  - [How do I stay on the stable 2.x line?](#how-do-i-stay-on-the-stable-2x-line)
  - [Switching from 2.x to 3.x](#switching-from-2x-to-3x)
- [The Reviewer by Hand](#the-reviewer-by-hand)
  - [agy: installation and the model](#agy-installation-and-the-model)
  - [agy through Google Cloud's ADC (the free trial: $300 for 90 days)](#agy-through-google-clouds-adc-the-free-trial-300-for-90-days)
  - [Fallback Option: Direct Gemini API Key](#fallback-option-direct-gemini-api-key)
- [Working in a Terminal](#working-in-a-terminal)
  - [Working with Two Windows (Terminal + Graphics)](#working-with-two-windows-terminal--graphics)
  - [Project Folder Structure and Backup](#project-folder-structure-and-backup)
  - [Where can I find the full list of capabilities?](#where-can-i-find-the-full-list-of-capabilities)

---

## Other Ways to Use the Method

The recommended way is version 3.x with the TCC desktop app ([FAQ](FAQ.md#getting-started)). The others:

- 💻 **Option 2 · Version 3.x in Terminal (Claude Code or Headless Plugin)**  
  The same method core, calculation tools, and automation, but text-based in a terminal session. Installed with the `--terminal` flag, or as a Claude Code plugin from this repository's catalog — then `/autosound-tuning:setup` in the first session brings the tools (README, «Already in Claude Code? As a plugin»).
  - **Requirements:** macOS or Windows, Claude Pro/Max, REW beta with API enabled, without TCC.
  - **Pros:** Maximum execution speed, zero GUI overhead, ideal for console lovers. Projects are 100% compatible with TCC.

- 📁 **Option 3 · The 2.x Line**  
  The classic plugin for Claude Code, on the `2.x` branch (version 2.8.x). The catalog installs 3.x from v3.1.0 on; the 2.x line is added by its branch (below, «How do I stay on the stable 2.x line?»).
  - **Requirements:** Claude Pro, REW beta with API enabled, working in a terminal session.
  - **Pros:** A fixed algorithm that receives only critical bug fixes, with no new features added.
  - **Cons:** Manual state tracking in text Markdown files (`dsp-state-current.md`), no "Desk-First" automated virtual prediction, and no modern calculation tools.

- 🌐 **Option 4 · Web Chat (No Software Installation)**  
  A fully manual, step-by-step tuning workflow via the [manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  - **Requirements:** Google AI Studio or any web chat with an AI of your choice.
  - **Pros:** Requires no software or developer tool installations on your computer.
  - **Cons:** Every step is executed manually (copying prompts, exporting text files from REW yourself), with no API integration and no verification of calculations by local scripts.

### Can I run the method entirely in Gemini?
Yes. Other AIs can drive the run through `omp` (installed only on request with `--with-omp` / `-WithOmp`), at your own risk.

You can also run Gemini manually in a web chat session:

> Clone `https://github.com/ayukhno/autosound-tuning-skill`, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Standard web chat lacks context management, so precision can degrade over long sessions. For a manual run, see the [manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

---

## The Installer

**Options:**

| What it does | macOS | Windows |
|---|---|---|
| models other than Claude, through `omp` | `--with-omp` | `-WithOmp` |
| the project backup on GitHub (a private repository; the keys stay out of it) | `--github` | `-GitHub` |
| the method without the app (terminal only) | `--terminal` | `-Terminal` |
| show the plan and change nothing | `--dry-run` | `-DryRun` |

With options — for example `omp` and the GitHub backup — on macOS:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.0/install.sh | bash -s -- --with-omp --github
```
and on Windows, as two lines:
```powershell
$i = irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.0/install.ps1
& ([scriptblock]::Create($i)) -WithOmp -GitHub
```

### Updating, Locking Version, and Uninstallation
- **Updating the skill:** You can update the skill directly inside TCC, or simply re-run the installation command in a terminal. The script downloads the newest `v3.*` release tag, checks its signature, and does not touch your project files. A plugin updates with `claude plugin update autosound-tuning`; the next session then offers `/autosound-tuning:setup` once more, which checks the new version against its signed release.
- **Updating TCC:** TCC's update button provides the update command to run in a terminal (TCC cannot overwrite its own executable while running).
- **Options:** Pass options after `bash -s --` on macOS or `& ([scriptblock]::Create((irm …)))` on Windows: `--terminal` / `-Terminal` (no TCC), `--github` / `-GitHub` (GitHub project backup), `--with-omp` / `-WithOmp` (other AIs through omp), `--dry-run` / `-DryRun`.
- **Locking version:** `--skill-ref` and `--tcc-ref` (`-SkillRef` and `-TccRef` on Windows) pin the method and TCC to the versions released together — quote the two as a pair or not at all; a mixed pair is untested. To stay on the 2.8.x line: `claude plugin marketplace add ayukhno/autosound-tuning-skill#2.x` then `claude plugin install autosound-tuning`.
- **Uninstallation:** Run the installer with `--uninstall` (`-Uninstall`); `--all` also removes uv, Claude Code, and `~/.claude`, and `agy`/`gh`/`omp` when the installer put them there — it asks first. Your project folders are never deleted.

For details on installer options, see the [README](README.md#how-to-install-and-start).

### Where are the components installed?
All files are stored within your user profile:

| Component | Installation Path | Purpose |
| :--- | :--- | :--- |
| **Claude Code** | Official Anthropic directory | Drives the session |
| **The method** | `~/.claude/skills/.autosound-tuning-src`, linked as `~/.claude/skills/autosound-tuning` (a plugin install: Claude Code's plugin folder) | The method's checkout, and the name Claude Code finds it under |
| **Python 3.12** | `~/.local/bin/python3` (through `uv`) | Runs the method's local tools |
| **TCC** | User folder & Desktop shortcut | The desktop app and an isolated Python 3.12 environment |
| **`agy` tool** | User profile | Google CLI tool for communication with the Gemini reviewer |
| **Reviewer config** | `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` on Windows) | The reviewer's model and optional API key — outside every project |
| **`gh`, `omp`** | User profile — only when asked (`--github`, `--with-omp`) | GitHub backup helper; other AIs through omp |

---

## The Plugin for Claude Code

**Already in Claude Code?** The method also installs as a plugin:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
A plugin brings the method's files only: in the first session type **`/autosound-tuning:setup`** — it checks the plugin against its signed release and installs the rest. The TCC desktop app is not included this way; add it with `/autosound-tuning:setup app` (or `/autosound-tuning:install-tcc`).

---

## Versions and the 2.x Line

### How do I check the currently installed version?
- **By the command used:** The single-line installation script (`curl … | bash` or `irm … | iex`) installs **3.x**. A plugin shows its version in `claude plugin list`: **3.1.0** and later from the catalog, **2.8.x** from the `2.x` branch.
- **By the contents of the project folder:** If the folder contains a file named `dsp-state-current.md`, it is a **2.x** project. If the folder contains machine-readable files `project.json` and `process-state.json`, it is a **3.x** project.
- **Through TCC:** Go to *Diagnostics → Installation*.

### How do I stay on the stable 2.x line?
From v3.1.0 the catalog installs **3.x**: an installed plugin moves to 3.x on `claude plugin update` (or on marketplace auto-update). To stay on 2.x, add the catalog on the `2.x` branch so it follows that branch only:

```bash
claude plugin marketplace add ayukhno/autosound-tuning-skill#2.x
claude plugin install autosound-tuning
```
If the main catalog is already added, remove it first (see «Switching from 2.x to 3.x» below): both carry the same name.

### Switching from 2.x to 3.x
Only one such plugin can be active in the system at a time. Before installing version 3.x — by the installer or as a plugin from the main catalog — uninstall the old 2.x version in a terminal:

```
claude plugin uninstall autosound-tuning
claude plugin marketplace remove autosound-tuning-skill
```

After installing version 3.x, migrate an existing car project into the new format using the migrator:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <path-to-old-project> --into <path-to-new-project>
```
Verify channel mappings and speaker specs after running the migration. With the plugin, the migrator is inside the plugin's own folder — ask the session to run it.

---

## The Reviewer by Hand

### agy: installation and the model
The official **Antigravity CLI (`agy`)** needs no API key — you authenticate in the browser with your Google account.

- **Installation:** The installer sets this up by default. Depending on the system, other installers may ask for permission; this is normal. For manual installation, run:
  - macOS: `curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - Windows: `irm https://antigravity.google/cli/install.ps1 | iex`
- **Login:** Run `agy` in a new terminal, log in in the browser with your Google account, then return to the console and type `/quit`.
- **Pick the reviewer's model:** There is no default. Put an ID from `agy models` (a Pro `-high` tier, or Flash `-high` if Pro is not offered) into the reviewer's config file, `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` on Windows):
   ```env
   AUTOSOUND_CRITIC_MODEL=gemini-3.1-pro-high
   ```
  TCC sets it from its own picker. If `agy` reports that the model is not supported in your location, pick another ID from the list. When signed in through Google Cloud ADC, use `gemini-3.8-flash-high`.
- **Check:**
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py doctor
   ```
  `doctor` names the model, CLI, and key it found, makes one short live call, and prints the fix for anything wrong.

### agy through Google Cloud's ADC (the free trial: $300 for 90 days)
If AI Studio does not provide an API key (for example with a new account), Google Cloud's Application Default Credentials (ADC) are the alternative. `agy` signs in with them.

- In **console.cloud.google.com**: set up the free trial and create a project.
- Install Google Cloud's command-line tool: on macOS `brew install --cask gcloud-cli`, on Windows the Google Cloud SDK installer. Depending on the system, other installers may ask for permission; this is normal.
- Sign in, point it at the project, switch on Vertex AI and create the ADC file:
   ```bash
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   gcloud services enable aiplatform.googleapis.com
   gcloud auth application-default login --project <PROJECT_ID>
   ```
  On Google's consent page tick **Select all** (without the Cloud Platform scope, authentication fails). The file lands in `~/.config/gcloud/` (`%APPDATA%\gcloud\` on Windows).
- Tell `agy` to use it. Add this line to the reviewer's config file, `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` on Windows), which every run of the method reads, including TCC runs:
   ```env
   AGY_ADC_AUTH=true
   ```
  The installer offers to write this line when it finds the ADC file. For `agy` in your own terminal, also add `export AGY_ADC_AUTH=true` to `~/.zshrc` (on Windows: `setx AGY_ADC_AUTH true`).
- Pick the reviewer model. Under ADC, Pro at its high tier is not offered, so use `gemini-3.8-flash-high`:
   ```env
   AUTOSOUND_CRITIC_MODEL=gemini-3.8-flash-high
   ```
- Check with `doctor`: it confirms the Google Cloud ADC sign-in and makes one short live call.

### Fallback Option: Direct Gemini API Key
If `agy` is not available to you, or you exhaust its quotas, you can use a Gemini API key directly. With a key present the reviewer calls the API **first**, and `agy` only if that call fails.

- Get an API key at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** — current keys start with `AQ.`.
- Store it once with the reviewer's own command:
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py key set google
   # Windows: python3 "$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py" key set google
   ```
  The command prompts for the key securely and stores it in your system credential store. Do not put keys in a shell profile or a project file: every program can read them there, and TCC started from the Dock does not see a shell profile.
- Name a model the key can call: `doctor` prints the key's own list (for example `gemini-pro-latest`). Its IDs differ from `agy`'s.

> [!TIP]
> If no channel answers, the reviewer refuses (exit code 4): it lists why, saves the package into the project's `process/reviews/`, and copies it to the clipboard — paste it into any AI chat.

---

## Working in a Terminal

### Working with Two Windows (Terminal + Graphics)

TCC and the session read and write the same project files. With the session in a terminal, TCC's **Control mode** keeps TCC beside it as a monitor — the session's journal, the tables and the panels ([FAQ](FAQ.md#control-mode-the-session-in-a-terminal)).

### Project Folder Structure and Backup
Your project directory stores the full configuration and tuning history of your vehicle:

| File / Folder | Contents | Purpose |
| :--- | :--- | :--- |
| **`project.json`** | System configuration | Speaker channels, DSP outputs, profile, mic specs, target curve. |
| **`state/versions/` + `slots.json`** | Version registry | Chronological history of crossovers, delays, levels, and EQ. |
| **`process/process-state.json`** | Process status | Active phase tracking and verification logs. |
| **`autosound_context.md`** | Vehicle context | Car dictionary, install layout, cabin notes. |
| **`*.txt` / `*.json`** | Curves & DSP exports | Target curves and generated EQ parameter files. |

> [!IMPORTANT]
> **Preserve local `.mdat` copies:** Large REW `.mdat` files stay out of git; keep your local copies. For a private backup of the project folder to GitHub, install with `--github` (`-GitHub` on Windows) and ask the session to back the project up: it offers the repository, creates nothing without your yes, and knows what stays out.

### Where can I find the full list of capabilities?
A full overview of every tool and command is located in the Capabilities board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).  
Filter commands with: `python3 ~/.claude/skills/autosound-tuning/rew_tool/capabilities.py find "phase"`.
