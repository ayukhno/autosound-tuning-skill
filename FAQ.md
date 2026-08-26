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

* 🖥️ **Option 1 · Version 3.x in Graphical Window (Autosound TCC)**
  The most automated and visual path. The installer sets up Claude Code, Python, the core method, the graphical UI, and the automatic AI reviewer.
  * **Requirements:** macOS or Windows, paid Claude Pro/Max, REW beta with API enabled, ~700 MB free disk space.
  * **Pros:** You see the system tree, measurement curves, step-by-step plan, and chat window in a single interface. The state is saved automatically, and any action in the version registry can be undone with a single click.
  * **Cons:** The graphical app is still young and currently in beta testing.

* 💻 **Option 2 · Version 3.x in Terminal**
  The exact same modern core and level of automation, but the interaction is entirely text-based in the console. Set up via the installer with the `--terminal` flag.
  * **Requirements:** The same subscriptions and REW with API, but without the graphical UI.
  * **Pros:** Maximum execution speed, minimal system resource consumption. Projects are fully compatible with the graphical TCC app (you can open the same folder in the GUI later).

* 🏆 **Option 3 · The 2.x Line (The Proven Champion)**
  The stable plugin for Claude Code, permanently locked on version `v2.8.3` (branch `2.x`). Tuned with this exact algorithm, the author's own car took four EMMA and AYA awards in 2026.
  * **Requirements:** Paid Claude Pro, REW beta with API enabled, working in the terminal.
  * **Pros:** A time-tested, competition-proven, absolutely stable algorithm. It receives only critical bug fixes, with no new features added by design.
  * **Cons:** No automatic state tracking by the machine (everything is managed manually in text Markdown files), no "Desk-First" approach, and no modern calculation tools.

* 🌐 **Option 4 · Web Chat (No Software Installation)**
  A fully manual, step-by-step tuning workflow via the [manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  * **Requirements:** Free Google AI Studio or any web chat with an AI of your choice.
  * **Pros:** Entirely free. Requires no software or developer tool installations on your computer. Perfect for getting acquainted with the logic of the method.
  * **Cons:** Every step is executed manually (copying prompts, exporting text files from REW yourself), no API integration, and no automatic verification of calculations by local scripts.

---

### Which option should I choose?

* **You want maximum automation and graphics:** Choose **Option 1 (TCC)**.
* **You prefer the console without extra software:** Choose **Option 2 (3.x Terminal)**.
* **You want proven championship stability:** Choose **Option 3 (2.8.3)**.
* **You want to test the logic for free:** Choose **Option 4 (Web Chat)**.

> [!NOTE]
> You are not locked into a single choice: projects of the 3.x line open seamlessly in both the console and the graphical TCC program, and the transition from version 2.x to 3.x is fully automated.

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

Then, run these two commands inside Claude Code:
```bash
/plugin marketplace add ~/autosound-2x
/plugin install autosound-tuning
```
Now your plugin points to your local folder. You can update it whenever needed with a simple `git -C ~/autosound-2x pull`.

---

### Switching from 2.x to 3.x

Only one such plugin can be active in the system at a time. Before installing version 3.x, make sure to uninstall the old 2.x version in Claude Code:

```
/plugin uninstall autosound-tuning
/plugin marketplace remove autosound-tuning-skill
```

After installing the new version 3.x, you can migrate the current state of the car (active crossover filters, delays, levels, EQ, and DSP profile) into the new format using the automatic migrator:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <path-to-old-project> --into <path-to-new-project>
```

---

### Main changes in 3.x

* 📦 **Project as a Data Structure:** All system parameters are saved in `project.json` and `process-state.json`. The AI reads precise machine facts instead of trying to recall them from the chat history.
* 🛋️ **The "Desk-First" Approach:** Instead of many trips to the car — **one session for the full acoustic capture** (Phase 0) and **one short one to verify** (Phase 3). All further analysis, crossover frequency calculations, phase alignment, and equalizer setup are performed at your desk based on a highly accurate virtual prediction.
* 🧮 **Mathematical Verification:** Special local scripts analyze curves against the minimal phase loss criterion, limit equalizer Q-factor based on spatial measurement variance, and automatically detect microphone timing errors.
* 🛑 **Automatic Refusal:** If input measurements are contradictory, the microphone shows too high a timing error, or channels are missing, the system halts calculations and rejects the measurement round to prevent inaccurate or speaker-damaging results.

---

## Philosophy and Architecture: Why AI?

### Mission and Concept

We are building an **intellectual exoskeleton** for sound tuning. The human (Arbiter) always remains the key link — listening to the system, judging soundstage depth, height, and stability, and making the final decisions.

The AI handles the routine calculations and cabin physics: it analyzes phases, computes precise time delays at the crossover joins, and controls REW via the API, freeing up your time for the creative part of listening to music.

---

### Why is this a specialized skill and not a regular chat?

* **Eliminating Memory Drift:** Any standard AI chat begins to forget initial values, mix up volume levels, or confuse crossover frequencies after a few hours of conversation. Our system saves the current project state on your disk in `project.json`. The AI reads this file with every new query — its memory is not "recalled," but securely loaded from disk.
* **Specialized Domain Knowledge:** The skill embeds strict safety rules for tweeter protection, phase alignment algorithms, preconfigured target curves, and cabin acoustics analysis logic that general AI models know nothing about.
* **Local Processing via REW API:** Raw measurement data (thousands of points per curve) are processed by local Python scripts in milliseconds. The AI receives only a concise mathematical summary in the chat, which eliminates manual copy-paste errors and saves your token budget.

---

### Roadmap: Phases −1…5 and the "Desk-First" Approach

| Phase | Where it takes place | What is being done | Stage Output |
| :--- | :--- | :--- | :--- |
| **−1 Preparation** | at the desk | Entering car parameters, speaker details, DSP capabilities, and selecting a target curve. | `project.json` and configuration files created. |
| **0 Capture** | in the car (1 time) | Measuring each speaker individually with **protective filters only** (HPF); sweeps and moving-mic RTA. | A single, fully verified, high-quality measurement round. |
| **1 Fundament** | at the desk | Calculating crossover frequencies, levels, delays, and polarities based on phase prediction. | Base system tuning set up in the version registry. |
| **2 Equalizer** | at the desk | EQ is applied in **packages**: driver resonances → left/right matching → tone to target. Default is cuts only, max 6 bands per channel. Each package is a single "yes/no" decision and a new registry version. | Ready-to-import configuration files for your DSP. |
| **3 Verdict** | in the car (short) | Uploading parameters to DSP. Verification check automatically verifies if real measurements match the mathematical prediction. | A fully verified and locked technical tune. |
| **4 Listening** | in the car | Test tracks (EMMA/AYA discs, CarMus, Chesky) and a "what to listen for" cheat sheet. If something booms or sounds harsh, the skill lists suspects and fixes band by band in A/B tests (max 3 rounds). | Live listening verdicts linked to versions. |
| **5 Variations** | desk / in the car | Setting up additional presets (for different music genres, center channel, etc.) without altering the technical base. | Additional sound presets in the system. |

> [!NOTE]
> If real measurements in Phase 3 deviate from the mathematical prediction, the system automatically rolls back a step and switches to the classic, iterative step-by-step tuning algorithm.

---

### What does the method categorically refuse to do?

* **Writing parameters directly to your DSP** — entering values into the processor software always remains on your side.
* **Calculating delays based on a single measurement** — a minimum of 4 independent arrival-time evaluations is required.
* **Boosting frequencies in acoustic nulls (cancellation zones)** — these dips are caused by cabin wave interference, not the speaker itself. Smoothing them with EQ boosts is **physically impossible**: nothing changes at the listening position, while the speaker and amplifier get heavily overloaded. Dips that are safe to boost are distinguished by the system using *Excess phase* analysis in REW — only minimal-phase regions are corrected.
* **Working with low-quality measurements** — a detected microphone timing drift (temperature drift) or missing protective filters leads to immediate rejection of the entire measurement round.

---

### Which AI models are officially supported?

* 🧠 **Primary Model (Generator):** Claude Opus (configured with `xhigh` effort level for maximum reasoning).
* 👁️ **AI Reviewer (Critic):** Gemini Pro (High).

*As of August 2026.* AI technologies are evolving rapidly. If you are reading this much later, verify current recommendations for equivalent models.

> [!IMPORTANT]
> **Do not lower Claude's effort level below `xhigh`.**
> Weaker models or lower effort levels won't report errors — they will just silently agree with whatever you do and invent technically impossible parameters.

---

### Subscription Options and AI Budget

* **Option 1 (Recommended Basic): Claude Pro ($20/mo) + free Gemini as Critic**
  The best balance of reliability and cost. Use a free Gemini API key generated in Google AI Studio. The Claude Pro subscription can be cancelled as soon as you finish tuning your car.
* **Option 2 (Budget Compromise): Gemini Only ($10 prepay on Google Cloud)**
  Extremely inexpensive, but requires you to manually verify every single digit and regularly clear chat history with the `/clear` command before each new phase, as there is no independent critic to supervise.
* **Option 3 (Professional): Claude Pro ($20) + paid Gemini Cloud API**
  Completely free of any rate limit constraints or quota exhaustion. Optimal for professional, high-volume tuning of multiple vehicles.

---

### Why are actual token costs lower than expected?

1. Local Python scripts compress thousands of REW measurement points into short text summaries. Raw graphs are never sent to the chat.
2. The entire project history is saved on disk, so the AI does not need to read the entire chat from scratch for every query.
3. The sliding window principle is used — only data related to the currently active phase is loaded. You pay for **decisions**, not data transfer.

---

## Initial Installation (macOS and Windows)

### Automatic Installation

You will need a laptop, a measurement microphone, a DSP processor, and a paid **Claude Pro or Max** subscription.

<details>
<summary><b>Instructions for macOS</b></summary>

1. Open **Terminal** (press `Cmd + Space` → type `Terminal` → press `Enter`).
2. Paste the following command and press `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
   ```
3. The script may ask for your Mac password once to install the official Apple Command Line Tools (git). Wait 10–20 minutes.

</details>

<details>
<summary><b>Instructions for Windows</b></summary>

1. Open **Windows PowerShell** (press the `Windows key` → type `powershell` → press `Enter`).
2. Paste the following command and press `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
   ```
3. If Git is missing, click **Yes** to allow installation. The script will also create a convenient **REW (API on)** shortcut on your Desktop.

</details>

---

### Where are the components installed?

All files are stored strictly within your user profile:

| Component | Installation Path | Purpose |
| :--- | :--- | :--- |
| **Claude Code** | Official Anthropic directory | The main AI assistant guiding the process |
| **Tuning Method** | `~/.claude/skills/.autosound-tuning-src` | The folder where Claude Code searches for skills |
| **Autosound TCC** | User folder & Desktop shortcut | The graphical app and an isolated Python 3.12 environment |
| **`agy` tool** | User profile | Google CLI tool for fast background communication with the Gemini Critic |

---

### First Launch and Account Login

1. **Login to Claude:** At the end of the installation, the script will automatically run the `claude auth login` command. Log in with your paid account in the browser and click **Authorize**.
2. **Login to Gemini:** Run the `agy` command once in a new terminal window and log in with the Google account that has Antigravity access.
3. **Start Working:** Create an empty folder for your car files (e.g., `MyCarTuning`). Open it in **Autosound TCC** (via the *Browse…* button) or in a new terminal (`cd path` → type `claude`) and write in the chat: **"tune a new car from scratch"**. The AI will start asking questions and lead you by the hand.

---

### Updating, Locking Version, and Uninstallation

* **Updating:** Simply run the installation command again. The script will automatically download the latest tag `v3.*` (this is a pre-release, not a stable line — stable is 2.8.x) and won't affect your project files.
* **Locking Version:** Use the `--skill-ref v3.0.33` and `--tcc-ref v0.1.22` flags — quote them as a **pair**, since those two were released and tested together; a mixed pair is untested on macOS, or `-SkillRef` and `-TccRef` on Windows during installation.
* **Uninstallation:** Run the installer with the `--uninstall` flag (or add `--all` for a complete cleanup of development environments). Your project folders will never be deleted.

---

## Graphical Desktop App Autosound TCC

### What is it and do I need it?

The [TCC](https://github.com/ayukhno/autosound-tcc) app lets you work comfortably in a graphical window on macOS and Windows. You see the system tree, REW graphs, the step-by-step plan, and the AI chat on a single screen. The program is optional — you can fully tune a car via the Claude Code terminal, as all project data is saved in standard machine files on your disk. The app is younger than the tuning method itself and is currently in beta status.

### Working with Two Windows (Terminal + Graphics)

The app and the terminal access the exact same project files. You can switch freely between them: any steps or version configurations created in the console are immediately visible in the graphical UI and vice versa.

### AI Models in the App

The app uses your paid Claude subscription (via the official Anthropic SDK) and your free Google account via the local `agy` tool for the AI reviewer. Alternative models are available only if the `omp` system is activated (billed separately).

### Updates and Bug Reporting

The app updates automatically along with the mathematical core. You can check current versions in *Diagnostics → Installation*. Please report UI bugs using the *Report a problem* button on TCC's GitHub page, and tuning logic bugs on the skill's repository.

---

## Standalone AI Reviewer Gemini/Antigravity

The double-verification cycle (Generator ↔ Gemini Critic) completely eliminates subjective mathematical errors of the models. The critic catches things the primary AI misses. It runs automatically in the background via a local script — no manual copying is needed. While optional, this provides the greatest benefit for the final tuning result.

### Installation for macOS and Windows (Recommended)

The official **Antigravity CLI (`agy`)** from Google requires no API keys and uses a free OAuth login via the browser.

1. **Installation:** The installer sets this up automatically. For manual installation, run:
   * *macOS:* `curl -fsSL https://antigravity.google/cli/install.sh | bash`
   * *Windows:* `irm https://antigravity.google/cli/install.ps1 | iex`
2. **Login:** Run the `agy` command in a new terminal, log in in the browser with your Google account, then return to the console and type `/quit`.
3. **Test:** Verify operation with the `agy -p "Hello, world!"` command.

---

### Fallback Option: Direct Gemini API Key

On Linux systems or if you exhaust your Antigravity quotas, you can use free Gemini API keys directly:

1. Get a free API key at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**.
2. Create a text file named `.critic-env` inside your **project folder** (inside `rew_analitic/` or the directory you run the session from) and save:
   ```env
   GEMINI_API_KEY=your_key_here
   ```
3. Scripts will automatically detect the key and switch to direct HTTPS requests to the Gemini API.

> [!TIP]
> If neither the key nor the `agy` tool is found, the system will automatically fall back to background self-loops or prompt you to use Clipboard Mode.

---

### Can I run the method entirely in Gemini?

Yes, but as a manual run, not an automated installation. Tell your Gemini session (with file and terminal access):

> Clone `https://github.com/ayukhno/autosound-tuning-skill`, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Because there is no sliding window mechanism there, Gemini may gradually lose precision during long sessions. The most stable free option is **Option 4** (ready-made step-by-step prompts for [Google AI Studio](https://aistudio.google.com/) on the [manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)).

---

## Performing Measurements

### Phase Measurement: XLR Microphones vs. USB (UMIK-1/2)

* **XLR Microphones (Behringer ECM8000, Beyerdynamic MM1, etc.):** Connected via an external sound card. They allow the use of a **physical loopback** — a cable connecting a card output back into a free input. This gives the PC a hardware-stable, sample-accurate time-of-arrival reference.
* **USB Microphones (UMIK-1 / UMIK-2):** Connected directly to a USB port. They have no analog input, making a physical loopback cable impossible.

---

### Can I measure phase with a UMIK-1?

**Yes.** To get accurate phase data, use the **Acoustic Timing Reference** feature in REW. Before playing the sweep signal, the sound card plays a brief, high-frequency "chirp" through a selected speaker (usually the tweeter closest to the microphone), which serves as a temporal zero reference for the measured channel.

For detailed REW configuration for USB microphones, refer to the video guide: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Take all measurements in a single quick run and measure the first channel again at the end of the session!**
> * **Temperature drift destroys accuracy:** The speed of sound depends directly on the cabin air temperature. A shift of just a few degrees offsets the sound's arrival time by fractions of a millisecond. This is highly critical for phase-aligning midrange and tweeter drivers at crossover points.
> * **Drift accumulates with each measurement sweep:** A single speaker measured 6 times in a row over 18 minutes showed a delay shift of one sample (10 microseconds, corresponding to moving the mic by ~3.6 mm). The shift occurred due to executing sweeps, not just elapsed time.
> * **Always make a control measurement of the first speaker at the end:** The input check in version 3.x compares these two runs and rejects the entire measurement session if it detects unsafe temperature drift or a system timing offset.

---

### Rules for Naming Measurements in REW

Calculation tools look for correct charts strictly by their names in REW:

* `m-L_01 (sw)` — channel `m-L` (left midrange), measurement round `01`, sweep measurement.
* `m-L_01 (rta)` — moving-mic RTA measurement for the same speaker.
* `sw_01 (sw)`, `w-R_01 (sw)`, `tw-L_01 (sw)` — subwoofer, right woofer (midbass), left tweeter respectively.
* `L_01 (rta)`, `ALL_01 (rta)` — sum RTA measurement of the complete left side or the entire system.
* `m-L p5_01 (sw)` — speaker measured at a spatial checkpoint `p5` (alternatively named `m-L_01 (sw) p5`).
* `m-L-ctl1_01 (sw)` and `m-L-ctl3_01 (sw)` — timing control: the first opens the speaker series, the second closes it (can be named `m-L_01ctl` and `m-L_01rep` in the car).
* `m-L_final (sw)` — verification measurement after saving final parameters.

The complete measurement flow is described in [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md).

---

### Capture Session: Why protective filters only?

> [!IMPORTANT]
> **REW must remain open during the entire process:** the skill reads curves directly from the active REW window via the API, not from files exported to disk.

A capture session is a measurement of each individual speaker using **protective filters only** in the DSP (a High-Pass / HPF at a safe frequency for midranges and tweeters to prevent damage during loud sweeps). No active crossovers, delays, or EQ should be turned on — we need the pure physical response of the driver in the car's cabin. Calculation scripts automatically "subtract" the influence of the protective filter before calculating the target crossover, ensuring perfect phase prediction accuracy.

*Important:* Mute all inactive channels directly in your DSP software. Keep the sound card and radio volume absolutely stable throughout the session.

---

### What are positions p1…p9 and control measurement ctl for?

* **Determining the nature of dips and peaks:** Real speaker cabinet resonances remain stable on the graph when moving the microphone by a few centimeters (they are safe to fix with EQ). Acoustic nulls caused by cabin reflections shift wildly on the frequency axis — boosting them with EQ is useless and dangerous, so the AI ignores such regions.
* **Calculating EQ Q-factor:** The spread of measurements at positions `p1…p9` around the driver's head allows precise calculation of the safe equalizer Q-factor limit.
* **Compensating for timing drift:** Repeated measurements of the central `ctl` position allow the system to mathematically compensate for physical sound card timing drift during the session.

---

## Target Curves

### How do I create and configure my own target curve?

There is no single "correct" target curve — it is your initial working hypothesis, which you will adjust by ear after getting the baseline technical tune.

1. **Let the AI calculate it:** Describe your favorite music genres, preferred listening volume, and requests regarding famous target curves (e.g., *“take ResoNix Accurate as a base, but add +2 dB sub-bass and soften high frequencies”*) or sound complaints (*boomy, harsh, lack of space*). The script will generate the curve file, save it to the project folder, and compute individual target curves for each driver.
2. **Draw it manually:** Go to the free **Nono Tuning Tool** website ([nonotuningtool.com](https://nonotuningtool.com) → *Custom Target Curve* section), draw your curve with a mouse, export the `.txt` file, and save it to your project folder.
3. **Compare target graphs:** Use our interactive online visualizer:
   **[Open Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)**. Here you can compare your curve directly with SQ-Comp-Ref, ResoNix, Audiofrog, Harman, Jazzi, or Whitledge standards. Right-clicking any point on the chart displays an explanation of that frequency range's sonic impact.

---

## Project on Disk and DSP

### Project Folder Structure and Backup

A single folder on your disk contains complete documentation and configuration of your system:

| File / Folder | Contents | Purpose |
| :--- | :--- | :--- |
| **`project.json`** | System specifications | Speaker channels, DSP outputs, DSP profile, microphone specs, and the active target curve. |
| **`registry.json`** | Tuning version registry | Complete, chronological history of all crossovers, delays, volume levels, and EQ bands. |
| **`process-state.json`** | Current technical status | Information on the active phase of the process and successfully verified measurements. |
| **`autosound_context.md`** | Vehicle context and notes | Custom car audio dictionary, install features, and your listening notes. |
| **`*.txt` / `*.json`** | Target curves and DSP exports | Configuration files for import into your DSP and target curve files for REW. |

> [!IMPORTANT]
> **Take care to back up these small text and JSON files.**
> Extremely large REW `.mdat` measurement files (from 16 to 112 MB per file) do not need to be archived, as measurements can be redone at any time. Our installer offers an option to set up automated, free, and private backups of your project folder to GitHub.

---

### Compatibility with Processors and Filter Import to DSP

The skill computes precise filter parameters and saves them to a file:

* **Audiotec Fischer (Helix / MATCH / BRAX):** The processor family on which this method was designed and optimized. A ready-to-use Full EQ file is generated, which the official DSP PC-Tool imports with a single click for all channels simultaneously.
* **Other DSP processors:** A standard export file in REW Generic format (up to 20 EQ bands) or an extended crossover file is created. For convenient semi-automatic entry of parameters using keyboard macros, use the free tool: [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
* **Compatibility Check:** Before exporting, scripts automatically compare every computed filter against the real technical limits of your DSP model (available bands, sampling rate, filter types) and flag any deviations.

---

### Working with Passive Crossovers (Tweeter + Midrange on one channel)

A pair of speakers on a passive crossover is treated by the system as **a single shared channel**: it gets a single measurement, a shared delay, a shared volume level, and a single set of EQ bands.

Everything else works as usual, and the combined frequency response is physically correct — including any phase issues at the passive crossover junction. What no software can do from the outside, however, is align time delays or phase between the tweeter and midrange **inside** that passive group. For that, a fully active (channel-by-channel) system is absolutely required.

---

### Where can I find the full list of capabilities?

A detailed overview of all 68 capabilities and tools (with exact commands, abort conditions, development status, and scientific background) is located in the interactive Capabilities board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).
