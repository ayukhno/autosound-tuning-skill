# FAQ — Frequently Asked Questions on Car Audio Tuning

🇬🇧 **English** · 🇩🇪 [Deutsch](FAQ.de.md) · 🇵🇱 [Polski](FAQ.pl.md) · 🇺🇦 [Українська](FAQ.uk.md) · 📘 [TCC full guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

Real questions on the way from installing to a tuned car. The [README](README.md) is the short version; [Advanced Setup](ADVANCED.md) covers the terminal, other ways to install, versions and setting the reviewer up by hand.

---

## Table of Contents

- [Words Used Here](#words-used-here)
- [Getting Started](#getting-started)
  - [Before you start](#before-you-start)
  - [Which way should I start?](#which-way-should-i-start)
  - [Automatic Installation](#automatic-installation)
  - [From installation to the car](#from-installation-to-the-car)
  - [Updating](#updating)
- [Safety and AI Models](#safety-and-ai-models)
  - [What does the method categorically refuse to do?](#what-does-the-method-categorically-refuse-to-do)
  - [Which AI models are officially supported?](#which-ai-models-are-officially-supported)
- [Graphical Desktop App Autosound TCC](#graphical-desktop-app-autosound-tcc)
  - [What is it and do I need it?](#what-is-it-and-do-i-need-it)
  - [Control mode: the session in a terminal](#control-mode-the-session-in-a-terminal)
  - [Updates and Bug Reporting](#updates-and-bug-reporting)
- [The AI Reviewer](#the-ai-reviewer)
  - [If the reviewer does not answer](#if-the-reviewer-does-not-answer)
- [Performing Measurements](#performing-measurements)
  - [Phase Measurement: XLR Microphones vs. USB (UMIK-1/2)](#phase-measurement-xlr-microphones-vs-usb-umik-12)
  - [Can I measure phase with a UMIK-1?](#can-i-measure-phase-with-a-umik-1)
  - [Rules for Naming Measurements in REW](#rules-for-naming-measurements-in-rew)
  - [Capture Session: Why protective filters only?](#capture-session-why-protective-filters-only)
- [Target Curves](#target-curves)
  - [How do I create and configure my own target curve?](#how-do-i-create-and-configure-my-own-target-curve)
- [Project on Disk and DSP](#project-on-disk-and-dsp)
  - [Compatibility with Processors and Filter Import to DSP](#compatibility-with-processors-and-filter-import-to-dsp)
  - [Working with Passive Crossovers (Tweeter + Midrange on one channel)](#working-with-passive-crossovers-tweeter--midrange-on-one-channel)
  - [Backup](#backup)

---

## Words Used Here

- **The method (the skill):** the tuning instructions and tools Claude follows. It runs inside **Claude Code**, a Claude program on your computer — not the chat in your browser.
- **The session:** one conversation with Claude about your car, in TCC's chat window or in a terminal.
- **TCC:** the desktop app (Autosound TCC) that shows your project and runs the session for you.
- **The reviewer:** a second AI (Gemini) that checks every proposal before you see it. **The package:** the text bundle with a proposal that goes to the reviewer.
- **API (in REW):** the connection through which the method reads your measurements from REW. It has to be switched on in REW.
- **Sweep:** REW's test tone, played through one speaker. **RTA (MMM):** a measurement taken while you move the microphone slowly around your head.
- **Driver:** one speaker. **Fs:** a driver's resonance frequency, from its datasheet.
- **HPF / LPF:** high-pass / low-pass filter — the filters on the DSP that keep low or high frequencies away from a driver.
- **dBFS:** the level meter in REW; 0 dBFS is the top.

---

## Getting Started

### Before you start

- **A laptop** — it goes into the car for the measurements.
- **A measurement microphone:** a **UMIK-1 is enough** (an XLR microphone with an audio interface is more precise). Download its calibration file by the serial number from the maker's site and load it in REW.
- **A wire from the laptop to the DSP** — AUX 3.5 mm, USB audio or optical. Not Bluetooth: its delay changes between sweeps.
- **A DSP** in your car.
- **REW beta**, installed **before** the installer (on Windows the installer then adds a **REW (API on)** shortcut to your Desktop). Get it at [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html); the release build has no API.
- **A paid Claude subscription (Pro or Max)** at [claude.ai](https://claude.ai) — the installer signs you in with it.
- **A Google account** — for the Gemini reviewer; you sign in once in the browser.
- **Your drivers' Fs** from their datasheets — for the protective filters. No datasheet (factory speakers)? Tell the AI; the method can also measure it.

<a id="four-paths-of-usage"></a>

### Which way should I start?

- 🖥️ **Option 1 · Version 3.x in Graphical Window (Autosound TCC) — [Recommended]**  
  The most automated and visual path. The installer sets up Claude Code, the method with its Python libraries, the TCC desktop app, and the Gemini reviewer (agy).
  - **Requirements:** macOS or Windows, Claude Pro/Max, REW beta with API enabled; TCC adds about 700 MB to the download.
  - **Pros:** You see the system tree, measurement curves, step-by-step plan, and chat window in a single interface. State is saved automatically on disk, and actions in the version registry are tracked.
  - **Cons:** TCC is younger than the method.

Other ways — version 3 in a terminal only or as a Claude Code plugin, staying on the older 2.x line, or a web chat — are in [Advanced Setup](ADVANCED.md#other-ways-to-use-the-method).

> [!NOTE]
> You are not locked into a single choice: projects of the 3.x line open seamlessly in both a terminal session and TCC.

### Automatic Installation
You will need a laptop, a measurement microphone, a DSP processor in the car, and a **Claude Pro or Max** account.

<details>
<summary><b>Instructions for macOS</b></summary>

- Open **Terminal** (press `Cmd + Space` → type `Terminal` → press `Enter`).
- Paste the following command and press `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.sh | bash
   ```
- Depending on the system, other installers may ask for permission; this is normal. Wait 10–20 minutes the first time on a Mac without the developer tools, 5–15 on Windows without Git, a few minutes otherwise.

</details>

<details>
<summary><b>Instructions for Windows</b></summary>

- Open **Windows PowerShell** (press Start → type `powershell` → press `Enter`).
- Paste the following command and press `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.ps1 | iex
   ```
- Depending on the system, other installers may ask for permission; this is normal. Wait 5–15 minutes the first time on Windows without Git, a few minutes otherwise. The script creates a **REW (API on)** shortcut on your Desktop.

</details>

How the run ended is in its exit code: `0` ready · `1` stopped before the end — a refusal, an error or an interruption; what was done before it stays, and the last lines say what (a stop before the method's step leaves the method as it was) · `2` a wrong option to `install.sh`, or a bad `-Channel` or `-Plugin` to `install.ps1` (PowerShell itself refuses an option it does not know, with `1`) · `3` installed but not ready, the last lines naming what is missing and what to do.

### From installation to the car

1. **Sign in.** The installer's last step opens your browser twice: Claude, then Google for the reviewer (and GitHub if you asked for it). Skipped one? Run the installer again — it offers the sign-ins again.
2. **Start REW** with its API on: on Windows from the **REW (API on)** shortcut; on macOS in REW *Preferences → API* tick **Start the API when REW starts** and click **Start server** (once).
3. **Open TCC**, create an empty folder for your car (e.g. `MyCarTuning`) and select it.
4. **Pick the models** at the bottom of TCC's window: **AI main** — Claude Opus, **Effort** — x-high (the default), **AI critic** — Gemini Pro (High), or Gemini Flash (High) if Pro is not offered to you. For fine tuning in the car later, switch **AI main** there to the most capable model (today Claude Fable).
5. **Type** in TCC's chat: **"tune a new car from scratch"**. The AI asks about your system and your goals, then plans the measurements.
6. **In the car** (the first of two visits), TCC lists each measurement by name under *In focus now*. Take it in REW under that name, then press **⬇** to read it in. When all are in, press **Done**.
7. **At the desk** the AI designs the tune; **back in the car** (the second visit) you enter the numbers into the DSP, check them and fine-tune by ear. Two visits make the tune; fine-tuning by ear after it takes as many visits as you like.

### Updating

Update inside TCC, or run the installation command again: it installs the newest release, checks its signature, and does not touch your project folders. TCC's own update button gives the command to run (TCC cannot replace itself while it runs). More options: [Advanced Setup](ADVANCED.md#the-installer).

---

## Safety and AI Models

### What does the method categorically refuse to do?
- **Writing parameters directly into your DSP** — entering values into the processor software always remains your action.
- **Calculating delays based on auto-delay tools or cross-correlation** — acoustic delays are inspected manually from the initial rise of the impulse response ($t_0$). Auto-delay estimation tools in REW are strictly forbidden.
- **Boosting frequencies in acoustic nulls (cancellation zones)** — cancellation dips are caused by boundary reflections, not the speaker itself. Filling them with EQ is futile: a boost only loads the amplifier and speaker and changes nothing at the listening position. The method caps any boost at +6 dB, and a dip that would need more is almost certainly a cancellation. Dips that are safe to correct are identified using *Excess phase* analysis in REW.
- **Proceeding with compromised measurements** — detected timing drift or missing protective filters will be flagged before proceeding.

---

### Which AI models are officially supported?
- 🧠 **Primary Model (Generator):** **Claude Opus** (configured with `xhigh` effort level or higher; `max` for hard steps). Fine tuning in the car is best done with the most capable model (today Claude Fable). Other AIs can also drive the run through `omp` (installed only on request, with `--with-omp`) — at your own risk.
- 👁️ **AI Reviewer (Critic):** **Gemini Pro (High)** via Google Antigravity (`agy`), or **Gemini Flash (High)** where Pro (High) is not offered. With a Google Cloud sign-in (ADC, the free trial) the reviewer model is **Gemini 3.8 Flash (High)** (`gemini-3.8-flash-high`).
- 🛠️ **Other reviewers:** TCC's picker also offers Codex (and, with `--with-omp`, other models) for the reviewer's role.
- 🧪 **Tested by the author:** Gemini through Antigravity (`agy`) as the main AI in a terminal, with Codex as the reviewer and TCC in [Control mode](#control-mode-the-session-in-a-terminal).

*As of September 2026.* Models change fast, so take the names here as examples: TCC and the method read the current list from each provider and offer what is available today. If a model named here is refused, pick another from that list.

> [!IMPORTANT]
> **Keep Claude's effort level at `xhigh` or higher (`max` for hard steps).**  
> The author did the fine tuning in the car on Claude Fable 5.

---

## Graphical Desktop App Autosound TCC

### What is it and do I need it?
[TCC](https://github.com/ayukhno/autosound-tcc) lets you work in a graphical window on macOS and Windows. You see the speaker tree, REW graphs, step-by-step plan, and chat on one screen. TCC is optional — you can tune a car entirely in the session, as all project data is saved in standard files on disk.

📘 [TCC in eight screens (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · [The TCC window, panel by panel (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

### Control mode: the session in a terminal

For a session that runs in a terminal — with Claude Code, or with another AI such as Gemini through `agy`. **Control mode** (in TCC's header) moves TCC to the right half of the screen and leaves the rest to the terminal: you type in the terminal, and TCC shows what the session writes (*Monitoring*), the tables and your panels. **Done** and **Listening** reach the session as signals; **Active TCC** brings the full window back.

📘 [Control mode in the TCC guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md#control-mode)

### Updates and Bug Reporting
TCC checks for skill and TCC updates.

To report issues:
- On GitHub: report UI bugs on the [TCC GitHub repository](https://github.com/ayukhno/autosound-tcc/issues), and tuning issues on the [skill repository](https://github.com/ayukhno/autosound-tuning-skill/issues).
- Without a GitHub account: ask the session ("report a bug") or use TCC's report window; reports go to the author through a Google Form.

---

## The AI Reviewer

The two-AI review cycle (Generator ↔ Gemini Critic) catches mistakes a single model misses. It runs automatically in the background through a local script — no manual copying is needed.

The automatic channel is optional, but the review itself is not: without a channel set up, you paste the review package into another AI's chat by hand. Skipping the review entirely is the single biggest quality loss in the method.

### If the reviewer does not answer

> [!TIP]
> If no channel answers, the reviewer refuses (exit code 4): it lists why, saves the package into the project's `process/reviews/`, and copies it to the clipboard — paste it into any AI chat. Then paste the reviewer's reply back into the session's chat.

Setting the reviewer up by hand — the model, Google Cloud's ADC, an API key: [Advanced Setup](ADVANCED.md#the-reviewer-by-hand).

---

## Performing Measurements

### Phase Measurement: XLR Microphones vs. USB (UMIK-1/2)
- **XLR Microphones (Behringer ECM8000, Beyerdynamic MM1, etc.):** Connected through an external audio interface with a hardware loopback cable (an output patched straight back into a free input). This gives an exact hardware timing reference.
- **USB Microphones (UMIK-1 / UMIK-2):** Connected directly via USB. They lack a physical loopback and need an acoustic timing reference.
- **Audio Connection:** Use a physical wire (AUX 3.5 mm, direct USB audio, or optical). Avoid Bluetooth for sweeps: wireless delay changes between sweeps and degrades timing accuracy.

---

### Can I measure phase with a UMIK-1?
**Yes.** Use the **Acoustic Timing Reference** in REW. Before playing the measurement sweep, REW plays a short chirp through the speaker chosen as the timing reference to set the zero timing point.

> [!WARNING]
> **Take measurements with mic on a tripod, and repeat the control sweep at the end!**
> - **Cabin air temperature drift:** Sound speed shifts with cabin temperature and changes arrival times.
> - **Tripod placement:** Place the mic at ear height for the reference seat. Do not move the tripod until the sweep block is done (~25 minutes).
> - **Control sweep:** Measuring the opening channel (`ctl1`) and repeating it at the end (`ctl3`) checks for timing drift before closing the round.

For detailed REW configuration for USB microphones, refer to the video guide: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

---

### Rules for Naming Measurements in REW

With TCC, every measurement a step needs is listed by name under *In focus now*: take it in REW under exactly that name, then press **⬇**. Working in a terminal, you name them yourself. Either way, the skill finds measurements strictly by their names in REW:

- `m-L_1 (sw)` — channel `m-L` (left midrange), measurement series `1`, sweep measurement.
- `m-L_1 (rta)` — moving-mic RTA measurement for the same speaker.
- `tw-L_1 (sw)`, `w-R_1 (sw)`, `sw_1 (sw)` — left tweeter, right woofer (midbass), subwoofer.
- `L_1 (rta)`, `ALL_1 (rta)` — sum RTA of the complete left side or the entire system.
- `m-L p5_1 (sw)` — the speaker at spatial checkpoint `p5` (also read as `m-L_1 (sw) p5`).
- `m-L-ctl1_1 (sw)` and `m-L-ctl3_1 (sw)` — timing control: the first opens the speaker series, the second closes it; there is no `ctl2` (typed in the car as `m-L_1ctl` and `m-L_1rep`, they mean the same).
- `m-L_final (sw)` — verification measurement after saving final parameters.
- `w-L (imp)` — impedance measurement of a driver (carries no series number).
- Text after the method makes it another measurement of the same series: `r-L_17 (sw) noXO` is not `r-L_17 (sw)`.

Titles are matched exactly as typed. If a title does not match what the step expects, the session asks you instead of guessing.

The complete measurement flow is described in [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md).

---

### Capture Session: Why protective filters only?
> [!IMPORTANT]
> **REW must remain open during the entire process:** the skill reads curves directly from the active REW window via the API, not from files exported to disk.
>
> **Protective filters STAY ON during capture:** High-pass filters (HPF) on fragile tweeters and midranges must remain active in the DSP to protect them during measurement sweeps.

- **Protective Filter Rule:** The protective HPF must be **$\ge 1.1 \times Fs$ (recommended up to $1.5 \times Fs$), with a slope of $\ge 24$ dB/oct** (LR4 or BW4). If $Fs$ is unknown, look up the manufacturer datasheet value and state it in the project.
- **Other DSP processing disabled:** Operating EQ (empty), delays (set to 0), and polarities (normal) must be clean. Measure each driver on its own. Record each protective filter during the capture round (TCC asks; in a terminal the session records it): the method takes it back out before reading joint phase. A channel recorded as `OFF` is read as it is.
- **Levels in dBFS:** Set sweep volume so the peak of the loudest driver (subwoofer) is $-5\dots-10$ dBFS, and the quietest driver is well above the ambient cabin noise floor. Mute all inactive channels in your DSP software, and keep the sound card and head-unit volume unchanged for the whole session.
- **Midbass sweep sound:** A midbass measured without an LPF produces a harsh, raspy sound at high frequencies during the sweep. This is normal cone breakup at the top of its range; the driver is not damaged.

---

## Target Curves

### How do I create and configure my own target curve?
A target curve gives you a starting sound balance. You refine it by ear after the base tune.

- **Select from established curves:** Choose from calibrated targets — SQ-Comp-Ref (the method's competition curve), ResoNix, Audiofrog, Harman, Jazzi, and Whitledge — based on what you like to hear. The script `target_bands.py` calculates per-driver target shapes from your chosen curve and crossover points.
- **Draw manually:** Use the free [Nono Tuning Tool](https://nonotuningtool.com) (*Custom Target Curve* section) to shape a response and export a `.txt` target file.
- **Compare online:** Use the Target Curve Visualizer to compare curves (SQ-Comp-Ref, your own from REW, and standard curves from Nono Tuning Tool):  
  👉 **[Open Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)**. Right-clicking any point on the chart explains what that frequency range does to the sound.

📘 [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

---

## Project on Disk and DSP

### Compatibility with Processors and Filter Import to DSP
> [!IMPORTANT]
> The method calculates the filters. Delays and gains are entered **manually**, and so are crossovers, unless a paste tool takes them from the Extended export below. A file import carries only **EQ**.

- **Audiotec Fischer (Helix / MATCH / BRAX):** Generates a ready-to-import Full EQ file that DSP PC-Tool loads for all channels in one step.
- **Other DSP Processors:** Exports REW Generic EQ files (20 slots), or Generic/Extended with the crossovers inline. For fast parameter entry into other DSP software, use [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
- **Compatibility Check:** Before exporting, the method checks every computed filter against the limits of your DSP model (available bands, sampling rate, filter types) and flags any deviations.
- **OEM Head Units:** Bypass factory head units using a clean digital or analog input (DAP, USB, optical) into the DSP, rather than trying to de-equalize factory tone and loudness processing.

---

### Working with Passive Crossovers (Tweeter + Midrange on one channel)
A pair of drivers sharing a passive crossover is treated as **a single shared DSP channel**: it receives one measurement, a shared delay, a shared gain, and one set of EQ filters.

Everything else works as usual. No software can align time or phase between the tweeter and midrange inside that passive group: for that, each driver needs its own DSP channel.

---

### Backup

Large REW `.mdat` files stay on your computer: keep them. For a private backup of the project folder on GitHub, install with `--github` (`-GitHub` on Windows) and ask the session to back the project up — it creates nothing without your yes. What is in the folder: [Advanced Setup](ADVANCED.md#project-folder-structure-and-backup).
