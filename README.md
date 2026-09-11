# AI Autosound Tuning Assistant (Autosound Tuning Skill)

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

**In simple terms:** This is your personal AI car audio tuning master. You want a perfect soundstage and a smooth tonal balance, but graphs, phases, and delays seem too complicated? This assistant will take care of the hard parts. It reads your microphone measurements and guides you step-by-step to perfect sound.

- **You measure — AI calculates:** It works together with REW software, analyzes your cabin acoustics, and proposes exact settings for EQ, crossovers, and time alignment.
- **Minimum time in the car:** The main calculations are done at your desk at home. You only do the initial measurements in the car, and then return with ready-to-use numbers to listen to the result and dive into deep tuning step-by-step.
- **Writes nothing to your DSP — you enter it:** The assistant never touches your processor directly. It only shows you numbers and graphs; you make the decision and enter them manually.
- **Not a regular chat:** The project state and all settings are saved to files on your disk, so nothing is "forgotten" between sessions and you can always roll back a step.
- **Two AIs — a reviewer is part of the method:** one AI proposes settings, a second one criticises and checks them. What is optional is the *automatic channel* (a local script that passes packages between them); the reviewer's *role* is not — without a second opinion the method is noticeably worse, and where no channel can be set up you paste the package into any other AI's chat by hand, or read it yourself. But the final judge is your ear: you listen and decide, instead of just blindly approving their ideas.
- **Works with facts:** A check lacking data will refuse to proceed. The AI doesn't guess settings — if the measurements are done incorrectly or are insufficient, a specific check will simply refuse to calculate and will stop.

## Proven in Competitions

With version 2.x of this method, the author's car took four awards in 2026 at **EMMA** and **AYA** championships (the first award was won before it was bundled into a skill, using AI hints from the same graphs, which inspired this project). The latest version 3.x (with a graphical interface) is currently in beta and hasn't proven itself in competitions yet, so for a guaranteed result, many choose to stick with the time-tested version 2.8.x.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" height="120" alt="AYA May 2026, Einsteiger 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" height="120" alt="AYA July 2026, Amateur 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" height="120" alt="AYA August 2026, Amateur 5000, 2nd place">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" height="120" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3rd place">
</p>

*Your system can sound like a champion too!*

> [!CAUTION]
> AI is an assistant, but the responsibility is yours. A manually entered number with a typo can burn a tweeter. Always check crossover frequencies before unmuting the sound, and always start at a low volume.

## What You Need to Start

You don't need to be a programmer — the app installs with a single command. But regarding hardware and subscriptions, you'll need the following:

1. **Measurement microphone** (e.g., UMIK-1, or preferably an XLR microphone with a sound interface and physical loopback).
2. **Processor (DSP)** in your car.
3. **REW (Room EQ Wizard) software** — **beta version** is required (the current release build, V5.31.3 of July 2024, has no API at all — check Help → About before you start). Get the beta build from [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html). After launching REW, go to *Preferences → API*, check **Start the API when REW starts**, and click **Start server**.
4. **Paid Claude subscription (Pro or Max)** — this AI does the heavy lifting and solves complex math problems. This is the supported path, and the graphical app is built for it. A run driven entirely by another AI is possible but manual, and you give up the second opinion that the method leans on — see the FAQ, "Can I run the method entirely in Gemini?". Without internet near the car, the session won't work either way.

*(We also recommend having a free GitHub account to automatically back up your tuning history in a private repository. Your Gemini API key does **not** travel with that backup: it lives outside the project, in `~/.config/autosound/critic-env` — `%APPDATA%\autosound\critic-env` on Windows — and a new project is created with a `.gitignore` that keeps the project-local config out of git as well.)*

## How to Install and Start (Version 3.x — Beta)

We created an installer that downloads everything you need and sets up a convenient **graphical application (Autosound TCC)**. Along with the app it also installs **`omp`** — the piece that lets the app offer models other than Claude; those are **billed per use**, and nothing runs through it unless you pick such a model. If you would rather not have it, add `--no-omp` (macOS/Linux) or `-NoOmp` (Windows) to the command below; the terminal-only install never brings it. The process takes 10–20 minutes (on macOS, Apple's own installer window opens once for the developer tools — one click, and no password is typed into the script; on Windows, it will show a Git permission dialog).

**macOS** — open Terminal (press ⌘-Space, type "terminal", Enter) and paste:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.49/install.sh | bash
```

**Windows** — open PowerShell (press Start, type "powershell", Enter) and paste:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.49/install.ps1 | iex
```

**After installation:**
1. The **Autosound TCC** app will appear on your desktop. Open it.
2. Create a new empty folder for your car (e.g., `MyCarTuning`) and select it in the app.
3. **IMPORTANT:** Before your first message, make sure the effort level for **Claude Opus** is set to no lower than `xhigh` (this is the default value). For very complex steps, use `max`. This is critical: a weaker model doesn't stop with an error; it just agrees with you, leading to "silent failures" in your tuning. *Note: effort level changes apply only to the next session.*
4. Type in the app chat: **"tune a new car from scratch"**. The AI will start asking questions and lead you by the hand.

▶ **[Open Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)** — drag your curve or a standard one from [Nono Tuning Tool](https://nonotuningtool.com), compare graphs, and save it.

---

**Competition-Proven Version 2.8.x** — [path 3 in the FAQ](FAQ.md#four-paths-of-usage)

If you want to use the exact **2.8.x** version that won the competitions, it works exclusively through the terminal. Instead of the scripts above, run these two commands in a terminal with `claude` (Claude Code) already installed:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
*(If `claude` is not installed yet, you can add it via the official script: `curl -fsSL https://claude.ai/install.sh | sh`, or via npm as a fallback).*

## What the Tuning Process Looks Like

1. **Preparation at home:** You tell the AI about your system (which speakers, which processor).
2. **Measurements in the car (once):** one disciplined session, and the tune is then designed at the desk. You turn on the basic protective filters on your DSP and record each driver on its own — first a hand-held pass, then the same set from a **microphone on a tripod that does not move until the end**, with a control sweep opening and closing it so any drift is visible. Plan **~25 minutes for the mandatory part** (the tripod block) and up to about an hour if you also take the hand-held nine-position set that tells a cabin feature from a spot one. The exact sheet is in the method (`capture-session-sheet.md`); the app walks you through it block by block. *Note: a midbass without a low-pass filter (LPF) will sound harsh on top during a sweep — this is normal (cone breakup), do not stop the measurements.*
3. **Math at the desk:** You sit at your computer (without the car nearby). The AI analyzes measurements, joins the subwoofer to the midbass, evens out the soundstage, and calculates the EQ. The desk only predicts the results; the car then verifies them. If the desk's predictions do not match reality during verification — the system rolls back the steps.
4. **Enjoyment in the car:** You go back to the car, enter the ready numbers into the DSP, play test and favorite tracks, and enjoy. If something hums a little, "hurts the ear", or "the stage is off" — you tell the AI, and you pinpoint and correct the issue.

## Feedback, Support, and Privacy

**Privacy:** The skill learns from every tune and, only with your explicit consent, sends generalized lessons to a shared knowledge base. It never collects personal data and never sends full measurements.

**Issues and bugs:**
- If something is wrong with the tuning logic itself: [Open an issue on GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- If the issue is related to the GUI (Autosound TCC) — write to the [TCC app repository](https://github.com/ayukhno/autosound-tcc/issues/new/choose).

This tool is **completely free**. The code and scripts are licensed under **MIT**, and the documentation and method itself under **CC BY-SA 4.0**. 

**Credits:** part of the DSP maths follows the logic of [Resonalyze](https://github.com/DIMOSUS/Resonalyze) by DIMOSUS (MIT) — the junction sum-loss metric and the HELIX channel phase control are ports of it, so that a tuner moving between the two tools gets one answer per filter, not two. Details in [`LICENSES/NOTICE.md`](LICENSES/NOTICE.md).

If it saved you weeks of tuning time and you want to thank the author, you can do it here:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank Jar (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Good sound!**
