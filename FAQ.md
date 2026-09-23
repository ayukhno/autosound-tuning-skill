# FAQ — Frequently Asked Questions on Car Audio Tuning

Real user questions about installing and tuning your system with this tool. [README](README.md) is the short version; this page contains all the details.

---

## Table of Contents

- [Choosing a Path](#choosing-a-path)
  - [Four Paths of Usage](#four-paths-of-usage)
  - [Which option should I choose?](#which-option-should-i-choose)
  - [How do I check the currently installed version?](#how-do-i-check-the-currently-installed-version)
  - [How do I stay on the stable 2.x line?](#how-do-i-stay-on-the-stable-2x-line)
  - [Switching from 2.x to 3.x](#switching-from-2x-to-3x)
  - [Main changes in 3.x](#main-changes-in-3x)
- [Philosophy and Architecture: Why AI?](#philosophy-and-architecture-why-ai)
  - [Mission and Concept](#mission-and-concept)
  - [Why is this a specialized skill and not a regular chat?](#why-is-this-a-specialized-skill-and-not-a-regular-chat)
  - [Roadmap: Phases −1…5 and the "Desk-First" Approach](#roadmap-phases-15-and-the-desk-first-approach)
  - [What does the method categorically refuse to do?](#what-does-the-method-categorically-refuse-to-do)
  - [Which AI models are officially supported?](#which-ai-models-are-officially-supported)
  - [Subscription Options and AI Budget](#subscription-options-and-ai-budget)
  - [Why are actual token costs lower than expected?](#why-are-actual-token-costs-lower-than-expected)
- [Initial Installation (macOS and Windows)](#initial-installation-macos-and-windows)
  - [Automatic Installation](#automatic-installation)
  - [Where are the components installed?](#where-are-the-components-installed)
  - [First Launch and Account Login](#first-launch-and-account-login)
  - [Updating, Locking Version, and Uninstallation](#updating-locking-version-and-uninstallation)
- [Graphical Desktop App Autosound TCC](#graphical-desktop-app-autosound-tcc)
  - [What is it and do I need it?](#what-is-it-and-do-i-need-it)
  - [Working with Two Windows (Terminal + Graphics)](#working-with-two-windows-terminal--graphics)
  - [AI Models in the App](#ai-models-in-the-app)
  - [Updates and Bug Reporting](#updates-and-bug-reporting)
- [Standalone AI Reviewer Gemini/Antigravity](#standalone-ai-reviewer-geminiantigravity)
  - [Installation for macOS and Windows (Recommended)](#installation-for-macos-and-windows-recommended)
  - [Fallback Option: Direct Gemini API Key](#fallback-option-direct-gemini-api-key)
  - [Can I run the method entirely in Gemini?](#can-i-run-the-method-entirely-in-gemini)
- [Performing Measurements](#performing-measurements)
  - [Phase Measurement: XLR Microphones vs. USB (UMIK-1/2)](#phase-measurement-xlr-microphones-vs-usb-umik-12)
  - [Can I measure phase with a UMIK-1?](#can-i-measure-phase-with-a-umik-1)
  - [Rules for Naming Measurements in REW](#rules-for-naming-measurements-in-rew)
  - [Capture Session: Why protective filters only?](#capture-session-why-protective-filters-only)
  - [What are positions p1…p9 and control measurement ctl for?](#what-are-positions-p1p9-and-control-measurement-ctl-for)
- [Target Curves](#target-curves)
  - [How do I create and configure my own target curve?](#how-do-i-create-and-configure-my-own-target-curve)
- [Project on Disk and DSP](#project-on-disk-and-dsp)
  - [Project Folder Structure and Backup](#project-folder-structure-and-backup)
  - [Compatibility with Processors and Filter Import to DSP](#compatibility-with-processors-and-filter-import-to-dsp)
  - [Working with Passive Crossovers (Tweeter + Midrange on one channel)](#working-with-passive-crossovers-tweeter--midrange-on-one-channel)
  - [Where can I find the full list of capabilities?](#where-can-i-find-the-full-list-of-capabilities)

---

## Choosing a Path

### Four Paths of Usage

* 🖥️ **Option 1 · Version 3.x in Graphical Window (Autosound TCC) — [Recommended]**  
  The most automated and visual path. The installer sets up Claude Code, Python, the core method, the graphical UI, and the automatic AI reviewer.
  * **Requirements:** macOS or Windows, paid Claude Pro/Max, REW beta with API enabled; the app adds about 700 MB to the download.
  * **Pros:** You see the system tree, measurement curves, step-by-step plan, and chat window in a single interface. The state is saved automatically on disk, and actions in the version registry are tracked.
  * **Cons:** The graphical app is younger than the underlying tuning method and is currently in beta status.

* 💻 **Option 2 · Version 3.x in Terminal (Claude Code or Headless Plugin)**  
  The exact same modern core, calculation tools, and level of automation, but the interaction is text-based in the console. Installed with the `--terminal` flag (or via the Claude Code plugin).
  * **Requirements:** The same subscriptions and REW beta with API enabled, but without the graphical UI.
  * **Pros:** Maximum execution speed, zero GUI overhead, ideal for console lovers. Projects are 100% compatible with the graphical TCC app.

* 🏆 **Option 3 · The 2.x Line (The Proven Champion)**  
  The classic plugin for Claude Code, locked on version `v2.8.3` (branch `2.x`). Tuned with this algorithm, the author's car took awards in 2026 at EMMA and AYA championships.
  * **Requirements:** Paid Claude Pro, REW beta with API enabled, working in the terminal.
  * **Pros:** A fixed, competition-proven algorithm. Receives only critical bug fixes, with no new features added.
  * **Cons:** Manual state tracking in text Markdown files (`dsp-state-current.md`), no "Desk-First" automated virtual prediction, and no modern calculation tools.

* 🌐 **Option 4 · Web Chat (No Software Installation)**  
  A fully manual, step-by-step tuning workflow via the [manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  * **Requirements:** Free Google AI Studio or any web chat with an AI of your choice.
  * **Pros:** Entirely free. Requires no software or developer tool installations on your computer.
  * **Cons:** Every step is executed manually (copying prompts, exporting text files from REW yourself), no API integration, and no verification of calculations by local scripts.

---

### Which option should I choose?

* **You want maximum automation and visual feedback:** Choose **Option 1 (TCC)**.
* **You prefer the console and maximum speed:** Choose **Option 2 (3.x Terminal)**.
* **You want the legacy competition-proven plugin:** Choose **Option 3 (2.8.3)**.
* **You want to test the logic for free without local software:** Choose **Option 4 (Web Chat)**.

> [!NOTE]
> You are not locked into a single choice: projects of the 3.x line open seamlessly in both the console and the graphical TCC program.

---

### How do I check the currently installed version?

* **By the command used:** If you installed the plugin using the `/plugin install autosound-tuning` command inside Claude Code, you are using version **2.x**. If you ran the single-line installation script (`curl … | bash` or `irm … | iex`), you are using version **3.x**.
* **By the contents of the project folder:** If the folder contains a file named `dsp-state-current.md`, it is a **2.x** project. If the folder contains machine-readable files `project.json` and `process-state.json`, it is a **3.x** project.
* **Through the program interface:** In the TCC app, go to *Diagnostics → Installation*.

---

### How do I stay on the stable 2.x line?

The standard automatic plugin update will not transition you to version 3.x without your consent. However, if you want to completely freeze the version and locally control updates on the 2.x branch, clone the repository yourself:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Then run these two commands in a terminal:
```bash
claude plugin marketplace add ~/autosound-2x
claude plugin install autosound-tuning
```
Now your plugin points to your local folder. You can update it whenever needed with a simple `git -C ~/autosound-2x pull`.

---

### Switching from 2.x to 3.x

Only one such plugin can be active in the system at a time. Before installing version 3.x, make sure to uninstall the old 2.x version (in a terminal):

```
claude plugin uninstall autosound-tuning
claude plugin marketplace remove autosound-tuning-skill
```

After installing version 3.x, you can migrate an existing car project into the new machine format using the automatic migrator:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <path-to-old-project> --into <path-to-new-project>
```
*(Note: verify channel mappings and speaker specs after running the migration).*

---

### Main changes in 3.x

* 📦 **Project as a Data Structure:** All system parameters are saved on disk in `project.json` and `process/process-state.json`. The AI reads machine facts from disk rather than relying on chat memory.
* 🛋️ **The "Desk-First" Approach:** Instead of many trips to the car — **one disciplined session for the acoustic capture** (Phase 0) and **one short verification visit** (Phase 3). All analysis, crossover calculations, phase alignment, and EQ design are performed at your desk.
* 🧮 **Mathematical Verification:** Dedicated local Python scripts analyze curves against minimal phase loss, evaluate impulse arrival start, and check microphone timing stability.
* 🛑 **Structured Gateways:** If input measurements show excessive timing drift, missing channels, or violated safety limits, the system stops and names the problem before proceeding.

---

## Philosophy and Architecture: Why AI?

### Mission and Concept

We are building an **intellectual exoskeleton** for sound tuning. The human (Arbiter) always remains the key link — listening to the system, judging soundstage depth, height, and stability, and making the final decisions.

The AI handles routine calculations and cabin acoustics: it analyzes impulse arrivals, phase curves, computes time delays at crossover joins, and interacts with REW via the API, freeing up your time for the creative part of listening to music.

---

### Why is this a specialized skill and not a regular chat?

* **State Saved on Disk:** A standard AI chat forgets initial values, confuses volume levels, or alters crossover frequencies over a long session. Our system writes project state to disk. The AI reads this file on every step — its context is grounded in disk state, not chat buffer memory.
* **Specialized Acoustic Domain Knowledge:** The skill embeds strict safety rules for speaker protection, phase alignment logic, preconfigured target curves, and cabin acoustics heuristics that general AI models do not possess.
* **Local Processing via REW API:** Raw measurement data (thousands of points per curve) are processed locally by Python scripts in milliseconds. The AI receives only concise mathematical summaries in the chat, saving time and token budget.

---

### Roadmap: Phases −1…5 and the "Desk-First" Approach

| Phase | Where it takes place | What is being done | Stage Output |
| :--- | :--- | :--- | :--- |
| **−1 Preparation** | at the desk | Entering baseline setup (speaker channels, DSP outputs, DSP profile, mic, reference seat). About 17 answers up front; the rest is asked by the phase that needs it. | `project.json` and configuration files created. |
| **0 Capture** | in the car (1 time) | Measuring each speaker with **protective filters enabled** (sweeps on tripod `(sw)` and moving-mic `(rta)`). Finalizing target curve after capture. | Verified baseline measurement round and active target curve. |
| **1 Fundament** | at the desk | You describe your crossover wishes in your own words, and they are checked against the hard limits. The AI offers at most three crossover variants — the best the maths finds and the ones built from your wishes, each with its cost — and you choose. Driver resonances and a coarse per-driver EQ are handled here; levels, polarities and delays are read by hand from the start of each impulse; the sums are predicted and described. | Base system tuning in version registry. |
| **2 Equalizer** | at the desk | The second part of EQ, in **packages** and in this order: left/right pairs per band → the junctions of each side → sub with mids → each side whole → everything together → the centre → the rear. Default is **cuts only**, max 6 bands per channel. Each package is a single "yes/no" decision and a new registry version. | Ready-to-import EQ configuration for DSP. |
| **3 Verdict** | in the car (short) | Uploading parameters to DSP. Verification sweep automatically verifies if real measurements match mathematical predictions. Mandatory listening assessment. | A fully verified, locked technical tune. |
| **4 Listening** | in the car | Test tracks (EMMA/AYA discs, CarMus, Chesky) and a "what to listen for" cheat sheet. If something booms or sounds harsh, the skill lists suspect bands and tests them one at a time in A/B (three suspects × three rounds, then stop). | Listening verdicts linked to versions. |
| **5 Variations** | desk / in the car | Setting up additional presets (different music genres, alternate tuning flavor) on top of the technical base. | Additional sound presets in DSP. |

---

### What does the method categorically refuse to do?

* **Writing parameters directly into your DSP** — entering values into the processor software always remains your action.
* **Calculating delays based on auto-delay tools or cross-correlation** — acoustic delays are inspected manually from the initial rise of the impulse response ($t_0$). Auto-delay estimation tools in REW are strictly forbidden.
* **Boosting frequencies in acoustic nulls (cancellation zones)** — cancellation dips are caused by boundary reflections, not the speaker itself. Filling them with EQ is futile: a boost only loads the amplifier and speaker and changes nothing at the listening position. The method caps any boost at +6 dB, and a dip that would need more is almost certainly a cancellation. Dips that are safe to correct are identified using *Excess phase* analysis in REW.
* **Proceeding with compromised measurements** — detected timing drift between session control sweeps or missing protective filters will be flagged before proceeding.

---

### Which AI models are officially supported?

* 🧠 **Primary Model (Generator):** **Claude Opus** (configured with `xhigh` effort level; `max` for complex phase alignment).
* 👁️ **AI Reviewer (Critic):** **Gemini Pro (High)** via Google Antigravity (`agy`) or direct API key.
* 🛠️ **Other reviewers:** TCC's picker also offers Codex (and, with `--with-omp`, other models) for the reviewer's role. The Generator stays Claude.

*As of September 2026.* Model names change fast. If one named here is refused (for example, `agy` answers that the model is not supported in your location), pick another from `agy models`.

> [!IMPORTANT]
> **Do not lower Claude's effort level below `xhigh`.**  
> Weaker models or lower effort levels will not report errors — they quietly agree with incorrect inputs, hallucinate impossible acoustic parameters, or miss phase cancellation.

---

### Subscription Options and AI Budget

* **Option 1 (Recommended): Claude Pro ($20/mo) or Max + free Gemini via Antigravity (`agy`)**  
  The best balance of reliability and cost. The reviewer runs via Google's `agy` CLI signed in with your Google account. A flat subscription covers your sessions without a per-token meter, and it can be cancelled as soon as you finish tuning your car.
* **Option 2 (Pay-as-you-go API):**  
  Running the full tuning cycle solely through pay-as-you-go API tokens adds up quickly. The author's own measurement: Phases 0–2 alone, run through the pay-as-you-go Gemini API, cost about $20 — before any listening rounds. A fixed monthly subscription is noticeably more cost-effective.
* **Option 3 (Direct Gemini API Key):**  
  If Antigravity CLI quotas are exhausted, a free or paid API key from Google AI Studio can be used as a fallback. The key goes into the OS keystore (see [Fallback Option](#fallback-option-direct-gemini-api-key)).

---

### Why are actual token costs lower than expected?

1. Local Python scripts compress thousands of REW measurement points into concise mathematical summaries. Raw graphs are never dumped into chat.
2. The project state lives on disk, so the AI does not re-read entire conversational history on every query.
3. The sliding window principle is used — only data related to the currently active phase is loaded.

---

## Initial Installation (macOS and Windows)

### Automatic Installation

You will need a laptop, a measurement microphone, a DSP processor in the car, and a paid **Claude Pro or Max** subscription.

<details>
<summary><b>Instructions for macOS</b></summary>

1. Open **Terminal** (press `Cmd + Space` → type `Terminal` → press `Enter`).
2. Paste the following command and press `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.sh | bash
   ```
3. If Apple's Command Line Tools are missing, Apple's official installer window opens once — click Install. The script itself never asks for your password. Wait 10–20 minutes.

</details>

<details>
<summary><b>Instructions for Windows</b></summary>

1. Open **Windows PowerShell** (press Start → type `powershell` → press `Enter`).
2. Paste the following command and press `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.ps1 | iex
   ```
3. If Git is missing, allow its installation. The script will also create a **REW (API on)** shortcut on your Desktop.

</details>

---

### Where are the components installed?

All files are stored within your user profile:

| Component | Installation Path | Purpose |
| :--- | :--- | :--- |
| **Claude Code** | Official Anthropic directory | The main AI assistant guiding the process |
| **Tuning Method** | `~/.claude/skills/.autosound-tuning-src`, linked as `~/.claude/skills/autosound-tuning` | The method's checkout, and the name Claude Code finds it under |
| **Python 3.12** | `~/.local/bin/python3` (through `uv`) | Runs the method's local tools |
| **Autosound TCC** | User folder & Desktop shortcut | The graphical app and an isolated Python 3.12 environment |
| **`agy` tool** | User profile | Google CLI tool for fast communication with the Gemini Critic |
| **Reviewer config** | `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` on Windows) | The reviewer's model and optional API key — outside every project |
| **`gh`, `omp`** | User profile — only when asked (`--github`, `--with-omp`) | GitHub backup helper; alternative models |

---

### First Launch and Account Login

1. **Sign-ins at the end of install:** The installer signs you in to Claude (log in with your account in the browser and authorize), offers Gemini sign-in through `agy` (Enter signs in, `s` skips), and GitHub if `gh` is installed.
2. **Turn on REW's API:**  
   *Note: REW must be the beta version (current release V5.31.3 and earlier have no API).*  
   Go to *Preferences → API*, tick **Start the API when REW starts**, and click **Start server** (port `4735`). On Windows, start REW from the **REW (API on)** shortcut.
3. **Start Working:** Create an empty folder for your car (e.g., `MyCarTuning`). Open it in **Autosound TCC** (select Claude Opus and Gemini Pro) or in a terminal (`cd MyCarTuning`, then `claude`), and type in the chat: **"tune a new car from scratch"**.

---

### Updating, Locking Version, and Uninstallation

* **Updating the skill:** You can update the skill directly inside TCC, or simply re-run the installation command in a terminal. The script downloads the newest `v3.*` tag (the `v3.0.*` tags are pre-releases until 3.1.0; the competition-proven stable line is 2.8.x) and does not touch your project files.
* **Updating TCC:** TCC's in-app update button provides the update command to run in terminal (a running application cannot overwrite its own executable).
* **Options:** they go after `bash -s --` on macOS and after the `& ([scriptblock]::Create((irm …)))` form on Windows (both shown in the [README](README.md#how-to-install-and-start-version-3x--beta)): `--terminal` / `-Terminal` (no app), `--github` / `-GitHub`, `--with-omp` / `-WithOmp`, `--no-reviewer` / `-NoReviewer`, `--dry-run` / `-DryRun`.
* **Locking Version:** `--skill-ref` and `--tcc-ref` (`-SkillRef` and `-TccRef` on Windows) pin the method and the app to the versions released together — quote the two as a **pair** or not at all; a mixed pair is untested.
* **Uninstallation:** Run the installer with `--uninstall` (`-Uninstall`); `--all` also removes uv, Claude Code and `~/.claude`, and `agy`/`gh`/`omp` when the installer put them there — it asks first. Your project folders are never deleted.

---

## Graphical Desktop App Autosound TCC

### What is it and do I need it?

The [TCC](https://github.com/ayukhno/autosound-tcc) app lets you work in a graphical window on macOS and Windows. You see the system tree, REW graphs, step-by-step plan, and AI chat on a single screen. The app is optional — you can tune a car entirely via terminal, as all project data is saved in standard machine files on disk.

📘 [TCC in eight screens (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · [The TCC window, panel by panel (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

### Working with Two Windows (Terminal + Graphics)

The app and the terminal access the exact same project files. You can run your interactive session in terminal while keeping TCC open alongside as a real-time visual monitor: it displays the speaker tree, curve overlays, and version registry changes as they happen.

### AI Models in the App

The app uses your Claude subscription (via Anthropic SDK) and your Google account via `agy` for the AI reviewer. Model choices in TCC reflect recommended combinations. Alternative models via `omp` are only added if requested (`--with-omp`).

### Updates and Bug Reporting

TCC checks for skill and app updates. Report UI bugs on the [TCC GitHub repository](https://github.com/ayukhno/autosound-tcc/issues), and tuning math issues on the [skill repository](https://github.com/ayukhno/autosound-tuning-skill/issues).

---

## Standalone AI Reviewer Gemini/Antigravity

The two-AI review cycle (Generator ↔ Gemini Critic) catches mistakes a single model makes and does not see. It runs automatically in the background via a local script — no manual copying is needed. What is optional is this *automatic channel*, not the second opinion itself: with no channel set up you paste the package into another AI's chat by hand. Skipping the review entirely is the single biggest quality loss in the method.

### Installation for macOS and Windows (Recommended)

The official **Antigravity CLI (`agy`)** needs no API key — you authenticate in the browser with your Google account.

1. **Installation:** The installer sets this up automatically. For manual installation, run:
   * *macOS:* `curl -fsSL https://antigravity.google/cli/install.sh | bash`
   * *Windows:* `irm https://antigravity.google/cli/install.ps1 | iex`
2. **Login:** Run `agy` in a new terminal, log in in the browser with your Google account, then return to the console and type `/quit`.
3. **Pick the reviewer's model** — there is no default. Put an id from `agy models` (the left column; a Pro `-high` tier) into the reviewer's config file, `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` on Windows), as a line such as:
   ```env
   AUTOSOUND_CRITIC_MODEL=gemini-3.1-pro-high
   ```
   The app sets it from its own picker. If `agy` answers that the model is not supported in your location, pick another id from the list.
4. **Check:**
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py doctor
   ```
   `doctor` names the model, the CLI and the key it found, makes one short live call, and prints the fix for anything wrong.

---

### Fallback Option: Direct Gemini API Key

If `agy` is not available to you, or you exhaust its quotas, you can use a free Gemini API key directly. With a key present the reviewer calls the API **first**, and `agy` only if that call fails.

1. Get a free API key at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** — current keys start with `AQ.`.
2. Store it once with the reviewer's own command. It asks for the key without showing it and keeps it in the macOS Keychain (on Windows, in a store only your login opens; elsewhere, and whenever the store is unavailable, in the reviewer's config file with mode 600). A key line you write into `critic-env` by hand wins over the store. Never in a project folder, a shell profile or an environment variable: every program can read it there, and an app started from the Dock does not see it.
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py key set google
   # Windows: python3 "$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py" key set google
   ```
   A key already exported in `~/.zshrc` (or in the Windows user environment) moves with `… key move-shell`, which asks first. `… key status` shows where each key is, never the key.
3. Name a model the key can call: `doctor` prints the key's own list (for example `gemini-pro-latest`). Its ids differ from `agy`'s.

A project-local `.critic-env` that carries a key and that git would take is refused. `doctor` never prints the key, only its shape (`current` / `OLD`) and where it comes from.

> [!TIP]
> If no channel answers, the reviewer refuses (exit code 4): it lists why, saves the package into the project's `process/reviews/`, and copies it to the clipboard — paste it into any AI chat.

---

### Can I run the method entirely in Gemini?

Yes, but as a manual run rather than an automated pipeline. Prompt your Gemini session:

> Clone `https://github.com/ayukhno/autosound-tuning-skill`, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Because there is no sliding window mechanism in standard web chat, precision can degrade over long sessions. The supported zero-cost option is **Option 4** ([manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)).

---

## Performing Measurements

### Phase Measurement: XLR Microphones vs. USB (UMIK-1/2)

* **XLR Microphones (Behringer ECM8000, Beyerdynamic MM1, etc.):** Connected via an external audio interface with a **hardware loopback cable** (an output patched straight back into a free input). This gives a hardware-stable, sample-accurate time-of-arrival reference (one sample ≈ 10 µs at 96 kHz).
* **USB Microphones (UMIK-1 / UMIK-2):** Connected directly via USB. They have separate digital clocks from the audio interface and lack physical loopback, requiring an acoustic timing reference.
* **Audio Connection:** Use a physical wire (AUX 3.5 mm, direct USB audio, or optical). **Avoid Bluetooth for sweeps:** wireless connections introduce packet jitter and variable latency that degrade acoustic timing reference accuracy.

---

### Can I measure phase with a UMIK-1?

**Yes.** Use the **Acoustic Timing Reference** in REW. Before playing the measurement sweep, REW plays a short, high-frequency "chirp" through the output you choose as the timing reference, and that chirp is the zero point for the measured channel.

For detailed REW configuration for USB microphones, refer to the video guide: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Take measurements with mic on a tripod, and repeat the control sweep at the end!**
> * **Cabin air temperature drift:** Sound speed shifts with cabin temperature. A few degrees change shifts arrival times by tens of microseconds.
> * **Drift accumulates with each sweep:** one speaker measured 6 times in a row over 18 minutes shifted by one sample (10 µs, the same as moving the mic ~3.6 mm) — from running sweeps, not just from time passing.
> * **Tripod placement:** Place the mic at ear height for the **reference seat** defined in the project, indexed to physical marks, and do not move it until the block is done.
> * **Control sweep:** Measuring the opening channel (`ctl1`) and repeating it at the end (`ctl3`) lets the check name any timing drift before the round is closed; whether to retake is your call.

---

### Rules for Naming Measurements in REW

Calculation tools find measurements strictly by their names in REW:

* `m-L_1 (sw)` — channel `m-L` (left midrange), measurement series `1`, sweep measurement. A DSP state can have several series; the number is not the registry's version number either.
* `m-L_1 (rta)` — moving-mic RTA measurement for the same speaker.
* `tw-L_1 (sw)`, `w-R_1 (sw)`, `sw_1 (sw)` — left tweeter, right woofer (midbass), subwoofer.
* `L_1 (rta)`, `ALL_1 (rta)` — sum RTA of the complete left side or the entire system.
* `m-L p5_1 (sw)` — the speaker at spatial checkpoint `p5` (also read as `m-L_1 (sw) p5`).
* `m-L-ctl1_1 (sw)` and `m-L-ctl3_1 (sw)` — timing control: the first opens the speaker series, the second closes it; there is no `ctl2` (typed in the car as `m-L_1ctl` and `m-L_1rep`, they mean the same).
* `m-L_final (sw)` — verification measurement after saving final parameters.
* `w-L (imp)` — impedance measurement of a driver; it is not tied to a DSP state and carries no series number.
* Text after the method makes it **another measurement of the same series**: `r-L_17 (sw) noXO` is not `r-L_17 (sw)`.

Titles are matched exactly as typed. A title that does not match what the step expects is a question the AI asks you, never a guess.

The complete measurement flow is described in [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md).

---

### Capture Session: Why protective filters only?

> [!IMPORTANT]
> **REW must remain open during the entire process:** the skill reads curves directly from the active REW window via the API, not from files exported to disk.
>
> **Protective filters STAY ON during capture:** High-pass filters (HPF) on fragile tweeters and midranges must remain active in the DSP to protect them during measurement sweeps.

* **Protective Filter Rule:** The protective HPF must be **$\ge 1.1 \times Fs$ (recommended up to $1.5 \times Fs$), with a slope of $\ge 24$ dB/oct** (LR4 or BW4). If $Fs$ is unknown, look up the manufacturer datasheet value and state it in the project.
* **Active filters disabled:** Operating EQ (empty), delays (set to 0), and polarities (normal) must be clean. Record each protective filter on the capture round (the app asks; in a terminal the session records it): the tools then take it back out of that solo before reading joint phase. A channel recorded as `OFF` is read as it is.
* **Levels in dBFS:** Set sweep volume so the peak of the loudest driver (subwoofer) is $-5\dots-10$ dBFS, and the quietest driver is well above the ambient cabin noise floor. Check noise levels with engine off and with engine running. Mute all inactive channels in your DSP software, and keep the sound card and head-unit volume unchanged for the whole session.
* **Midbass sweep sound:** A midbass measured without an LPF will produce a harsh, raspy sound at high frequencies during the sweep. This is normal **cone breakup** at the top of its range; the driver is not damaged.

---

### What are positions p1…p9 and control measurement ctl for?

* **Telling driver and mounting resonances from cabin reflections:** Resonances remain stable when shifting mic position slightly (safe to EQ). Cabin reflection nulls shift frequency wildly — boosting them is futile.
* **Calculating EQ Q-factor limits:** Spatial variance across `p1…p9` determines safe equalizer Q-factor bounds.
* **Monitoring timing drift:** The opening and closing `ctl` sweeps detect clock or temperature drift during the session.

---

## Target Curves

### How do I create and configure my own target curve?

A target curve is an initial tonal hypothesis that you refine by ear after establishing the baseline technical tune.

1. **Select from established curves:** Choose from calibrated targets — SQ-Comp-Ref (the method's own), ResoNix, Audiofrog, Harman, Jazzi and Whitledge — by what you like to hear. The script `target_bands.py` calculates per-driver target shapes from your chosen curve and crossover points.
2. **Draw manually:** Use the free [Nono Tuning Tool](https://nonotuningtool.com) (*Custom Target Curve* section) to shape a response and export a `.txt` target file.
3. **Compare online:** Explore our interactive visualizer:  
   👉 **[Open Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)**. Right-clicking any point on the chart explains what that frequency range does to the sound.

📘 [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

---

## Project on Disk and DSP

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
> **Preserve local `.mdat` copies:** The method requires keeping a local copy of REW `.mdat` files at technical sign-off and session completion. Large `.mdat` files (16–112 MB each) stay out of git; your local copies must always be preserved. For a free private backup of the project folder to GitHub, install with `--github` (`-GitHub` on Windows) and ask the AI to back the project up: it offers the repository, creates nothing without your yes, and knows what stays out.

---

### Compatibility with Processors and Filter Import to DSP

> ⚠️ **Important:**  
> The method calculates the filters. Delays and gains are always entered **manually** by the tuner, and so are crossovers, unless a paste tool takes them from the Extended export below. A file import carries only the **EQ**.

* **Audiotec Fischer (Helix / MATCH / BRAX):** Generates a ready-to-import Full EQ file that DSP PC-Tool loads for all channels in one step.
* **Other DSP Processors:** Exports REW Generic EQ files (20 slots), or Generic/Extended with the crossovers inline. For fast parameter entry into other DSP software via keyboard macros, use the free [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
* **Compatibility Check:** Before exporting, scripts compare every computed filter against the limits of your DSP model (available bands, sampling rate, filter types) and flag any deviations.
* **OEM Head Units:** The recommended practice is to **bypass** factory head units using a clean direct digital or analog input (DAP, USB, optical) into the DSP, rather than attempting to de-equalize factory tone and loudness processing.

---

### Working with Passive Crossovers (Tweeter + Midrange on one channel)

A pair of drivers sharing a passive crossover is treated as **a single shared DSP channel**: it receives one measurement, a shared delay, a shared gain, and one set of EQ filters.

Everything else works as usual, and the combined response is physically correct — including any phase issues at the passive junction. What no software can do from the outside is align time or phase between the tweeter and midrange **inside** that passive group: for that, each driver needs its own DSP channel.

---

### Where can I find the full list of capabilities?

A detailed overview of every tool and command is located in the Capabilities board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).  
Filter commands with: `python3 ~/.claude/skills/autosound-tuning/rew_tool/capabilities.py find "phase"`.
