# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, draft)](ROADMAP.md)

**In one line:** an AI tuning assistant for your car. It reads your REW measurements, designs the
tune at the desk from one capture session, and walks you through crossovers, time alignment, phase
and EQ one checked change at a time.

- **Works with REW**: pulls your measurements over its API and hands the finished EQ back as a
  file your DSP imports.
- **Designs at the desk, verifies in the car** *(3.x)*: one disciplined capture session, then every
  crossover, delay and filter is chosen on the *predicted* sum of your own measured drivers, and
  the car gets one short visit to confirm it.
- **Diagnoses before it fixes**: maps the cabin's reflections, nulls and driver resonances from the
  baseline before proposing a single change, and tells a dip that EQ can fill from a null that it
  cannot.
- **Never touches your processor**: nothing changes in the car unless you put it there. That does
  not mean retyping: the Helix PC-Tool imports the exported EQ in one go, REW's Generic format
  covers most other processors, and a
  [copy-paste helper](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) covers the ones
  without file import, such as Musway, ESX and Zapco.
- **Knows the craft**: target curves, protective filters, a phase-first order, a step-by-step
  process, and which test track to listen to for what.
- **Learns your setup**: accumulates knowledge about your car and gear, only with your consent.

## Proven in competition

Tuned with the **2.x line** of this method, my own car took four awards in 2026:

- **1st in Einsteiger 5000 — AYA, Lemgo, 30 May 2026.** Graph analysis and Gemini's advice: the
  workflow that later became this skill.
- **1st in Amateur 5000 — AYA, Horst, 25 July 2026.** The next class up, with the skill itself
  and my own ears.
- **2nd in Amateur 5000 — AYA, Schmallenberg, 15 August 2026.** A different sound judge than in
  July; his score card is the input for the next round.
- **3rd in SQ Entry Unlimited — EMMA Sound Off 2026, Schmallenberg, 15 August 2026.** First
  outing under the EMMA ruleset, same day and same tune as the AYA above.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA May 2026 Einsteiger 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA July 2026 Amateur 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" width="100" alt="AYA August 2026 Amateur 5000, 2nd place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" width="60" alt="EMMA Sound Off 2026 SQ Entry Unlimited, 3rd place">
</p>

*Your award could be here too.*

> [!CAUTION]
> AI can get numbers wrong. Always double-check crossover frequencies, slopes, and EQ values in
> your DSP before unmuting, especially on tweeters, and start at a low volume.

## Choose how you want to use it

Five ways in, from "try it in a browser tonight" to "the whole thing in a desktop window". They
are the same method; what differs is how much of it is automated, how proven it is, and what it
costs you in setup. **The awards above were won on path 2.**

| # | Path | What you need | What you get | The catch |
| :-- | :--- | :--- | :--- | :--- |
| **1** | **Web chat, nothing installed** — the [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) branch | A browser, free Gemini or any chat, REW to measure and export | The method's steps as copy-paste prompts; a passport file with your car's settings, rewritten in full at each step | You do all the work by hand: no REW automation, no memory between steps, no second AI reviewing. Free, and the weakest of the five |
| **2** | **2.x — the proven line** ⭐ [`v2.8.3`](https://github.com/ayukhno/autosound-tuning-skill/releases/tag/v2.8.3), branch [`2.x`](https://github.com/ayukhno/autosound-tuning-skill/tree/2.x) | Claude Code + a paid Claude plan, REW beta with its API on, one `/plugin install` | The full iterative method: REW read over its API, the analysis scripts, the Generator ↔ Critic ↔ Arbiter loop. **The four awards above were tuned with it** | Terminal only, no desktop app. The project is prose, so what is in force is re-read rather than machine-checked, and the desk-first path and the newer tools are not there. Fixes only from here on |
| **3** | **3.x in a terminal** — the [one-line installer](#getting-started) | The same, plus five minutes for the installer, which brings Claude Code and Python itself | Everything in 2.x, plus: the project as data (a ledger you can revert in one step), the desk-first path, gated EQ, an entry control, tools that refuse when their input is missing, and updates that reach you as tags | A pre-release: in its final full-tune check before 3.1.0. Terminal |
| **4** | **3.x in a window** — the same installer, which brings [TCC](https://github.com/ayukhno/autosound-tcc) | The same, and ~700 MB of disk | Path 3, plus the DSP tree, your REW curves, the plan and the AI side by side in a desktop window — macOS and Windows | The app is early. Models other than Claude come through `omp` and are metered separately |
| **5** | **Gemini as the driver** | An agentic Gemini session with file and shell access | Point it at the repository and it follows the method | A bootstrap, not an install; Gemini drifts on long sessions, and there is no second opinion unless you arrange one |

**In short.** Want to try the method for free before anything else — path 1. Want exactly what
took the awards — **path 2**, and no update will move you off it. Want the desk-first path and
don't mind a pre-release — path 3, or path 4 if you would rather see it than type it. Paths 2, 3
and 4 all read your car through REW's API and never write into your DSP.

The details of each — what the installer puts where, what changed in 3.x, and how to move from
one path to another — are in the [FAQ](FAQ.md#choosing-a-path).

## Table of contents

- [Choose how you want to use it](#choose-how-you-want-to-use-it)
- [Who it's for](#who-its-for)
- [What you need](#what-you-need)
- [Getting started](#getting-started)
- [How a tune goes](#how-a-tune-goes)
- [What a session sounds like](#what-a-session-sounds-like)
- [Which models to use](#which-models-to-use)
- [The math under the hood](#the-math-under-the-hood)
- [What's in here](#whats-in-here)
- [Reporting a problem](#reporting-a-problem)
- [Contributing your experience](#contributing-your-experience)
- [Support](#support)
- [License](#license)

## Who it's for

For anyone building sound in their own car and learning the craft. It is your exoskeleton: it
carries the knowledge and the experience, you bring the ears and the hands on the DSP.

Tuning is an avalanche. There are more methods, parameters and rules of thumb than anyone holds in
their head, and it is easy to dive into one detail and lose the whole picture. The skill holds the
knowledge, points at the few changes that matter, and keeps the trade-off between soundstage and
tonal balance in view. Your ear is the final judge.

It covers a full tune: from a new project through crossovers, time alignment, phase, per-channel
and summed EQ, and imaging, to voicing to taste, plus the optional spatial layers (a complementary
**center-fill** and a differential **rear-fill**, both field-validated). Every change runs through
a **Generator ↔ Critic ↔ Arbiter** review loop: one AI proposes, another challenges, you decide.

## What you need

**A clean machine is the expected case.** No programming tools — Python, git, Claude Code — have to
be there first: the installer below brings them, along with the method, the desktop app and the
Gemini reviewer.

What it cannot bring is the tuning half, because that part is yours:

- **[REW](https://www.roomeqwizard.com/) — a beta build**, with its API switched on. Everything the
  skill knows about your car arrives through it, and **the API is in the betas only**: the release
  version (V5.31.3, July 2024) has no *API* tab in its preferences at all, and that is the one a web
  search hands you. Take the build from
  [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) — the downloads live at
  AV NIRVANA, the REW forum. Then in REW: open *Preferences → API*, tick **Start the API when REW
  starts** and press **Start server**; the panel then reads *"API server is running on port 4735"*,
  and from then on it comes up with REW. That panel is the same on macOS and Windows; on Windows the
  installer also puts a **REW (API on)** shortcut on your Desktop, which starts REW with the API on
  in one click. **Keep REW open** while you tune: the method reads the measurements from the running
  window over that API, not from exported files.
- **A calibrated measurement microphone, and a DSP you can type into.** Any processor works. For
  phase and timing, XLR with a physical loopback beats USB:
  [why, in the FAQ](FAQ.md#measuring-phase--time-alignment-umik-1-vs-xlr-microphones).
- **A paid Claude subscription (Pro or Max).** See
  [the plans and what a session costs](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026).
- **Connectivity where the car is parked.** The AI runs in the cloud, so an underground car park
  with no signal stops the conversation — arrange mobile data or Wi-Fi before the session. The
  scripts and the measurements themselves do not need the network; the conversation does.

A second AI as reviewer is optional and is where most of the value comes from. The installer
brings Google's `agy` for it and offers the sign-in at the end; without one the skill runs solo and
tells you so, and you can add one later.

**A GitHub account is worth having, and it is not needed to install.** Installing asks you to log
in nowhere, and both repositories are public. The reason to have one is your own project, and it
is not the raw sweeps: those run 16 to 112 MB apiece, they stay on your disk, and if you ever
needed them again you would re-measure. What is worth keeping is everything you *concluded* — the
ledger of every crossover, delay, gain and filter, the journal of how you got there, the DSP
config backups that restore the tune, the target curves and the analysis notes. Small files, and
no amount of re-measuring brings them back. The installer asks whether you want them backed up to
a **private** GitHub repository, and if so puts GitHub's `gh` in place and signs it in; the backup
itself happens when you tell the AI to back the project up — it knows what stays out. A free
account covers it.

## Getting started

*(This is paths 3 and 4 of [the chooser](#choose-how-you-want-to-use-it). For path 2 — the line
that won the awards — the two plugin commands are in [the 2.x README](https://github.com/ayukhno/autosound-tuning-skill/blob/2.x/README.md#getting-started).)*

One line installs everything: Claude Code, the method, the
[TCC desktop app](https://github.com/ayukhno/autosound-tcc), Gemini as the reviewer, and `omp`,
which is what lets the app offer models other than Claude. It shows what is already on the
machine, lists everything it will download and where from, asks once — and then runs on its own
for ten to twenty minutes. The one interruption comes right after that question: on a Mac that has
never been used for programming it asks for your Mac password, once, for Apple's Command Line
Tools; on Windows it shows one permission dialog, for Git. At the end it signs you in, in your
browser: Claude first (that one is required), then the reviewer and GitHub if you want them — each
on Enter, or later.

**macOS** — open Terminal (⌘-Space, type "terminal", Enter) and paste:

```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
```

**Windows** — open PowerShell (Start, type "powershell", Enter) and paste:

```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
```

To leave something out: `--terminal` (no app), `--no-reviewer`, `--no-github` or `--no-omp`,
after `bash -s --` on macOS; on Windows the same four as `-Terminal`, `-NoReviewer`, `-NoGitHub`,
`-NoOmp` on the form `& ([scriptblock]::Create((irm <that url>))) -Terminal`. Running the same
line again updates everything; `--uninstall` / `-Uninstall` removes what it installed and never a
project folder.

Then start. Make a folder for the car — everything about that car will live in it, so copying the
folder copies the whole tune — and open it either way:

**In a terminal.** Open a *new* terminal window (the one you installed from cannot see what was
just installed), then:

```sh
mkdir -p ~/Autosound/my-car && cd ~/Autosound/my-car
```

```sh
claude
```

*Then start tuning by saying:* **"tune a new car from scratch"**.

**In the app.** Double-click **Autosound TCC** on your Desktop, *Browse…* to the folder (a new,
empty one is right), pick the models — Claude Opus (SDK) as *AI main*, Gemini Pro (High) as *AI
critic* — press *Open*, and say the same thing in the panel on the right, in any language:
*"let's tune this car from scratch"*.

The two are one project, not two: the method writes the project's files and the app reads them,
so you can work in the window one day and the terminal the next.

> **Triggering: include a car-audio word.** The skill wakes on *what you ask*, so a bare `resume`
> will not fire it, because it could mean any project. Add one domain word: **"resume my car-audio
> tune"**, **"continue tuning the car"**, **"what's my current DSP / crossover state"**, or in your
> own language («продовжити тюн авто», „Auto-DSP weiter einmessen", „wróćmy do strojenia car
> audio"). Same for a fresh start: name the car or the audio, not just "help me".

> **Set the model and the effort before that first message.** They are fixed for the session and
> nothing raises them later. As of August 2026: **Claude Opus at `xhigh`**, with **Gemini Pro
> (High)** reviewing. [Why the cheaper combinations fail quietly](#which-models-to-use).

Coming from the **2.x plugin**, or want to drive with **Gemini** instead? Both are in the FAQ:
[moving from 2.x to 3.x](FAQ.md#moving-from-2x-to-3x) (remove the plugin first — two skills of the
same name both stay active), and [Gemini as the driver](FAQ.md#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code).

## How a tune goes

The 3.x path puts the car at the ends and the desk in the middle. Two visits to the car, one
sitting at the desk between them; the ledger on disk is the one source of truth, and every proposal
lands there as a version you can revert in one step.

1. **Intake, at the desk.** The car, the drivers, the DSP and what it can do, the microphone, and
   the target curve — agreed before anyone sits in the car, so that nothing there is a surprise.
2. **One capture session, in the car.** Every driver alone, with *protective* filters only — a
   high-pass on the mids and tweeters and nothing else — so the recording carries the driver and
   the cabin, not a tune. A door woofer swept with no low-pass sounds harsh at the top; that is
   cone breakup, it is what the sweep is there to measure, and nothing is being damaged. Sweeps
   and an MMM pass in one go, plus a few control positions around the head. Before you leave the
   car, the round is checked: are all the drivers there, did the first and last sweep stay put,
   is the protective set on record.
3. **Design, at the desk.** Crossovers, levels, delays and polarity are chosen on the summed
   response *predicted* from your measured drivers with the DSP's own filters — every joint scored
   by how little it loses, and an alignment that sits a whole cycle off is named as such. EQ comes
   as packages, in this order: a driver's own resonances (only where the peak stays put across the
   control positions and is minimum-phase), left/right shape, then tone toward the target. Cuts
   only, unless you say otherwise. Each package is one decision and one ledger version; the result
   is an export file for the DSP.
4. **Verification, in the car — short.** You enter the sheet. An entry control confirms that the
   car hears what the desk predicted, driver by driver, or names the one that does not and why.
   Then what the desk cannot do: fine EQ on the moving-mic average, and A/B by one band at a
   time, with the method turning *"it cuts the ear"* or *"it booms"* into a ranked short list of
   suspects — three rounds at most.
5. **Listening.** Test tracks, a cheat-sheet of what to listen for, and the verdict written down
   against the version that earned it.
6. **Taste.** Presets on a virtual layer, so the technical tune underneath stays intact.

In the app, the same path is what you see: the DSP tree, the curves REW measured, the plan with
its steps, the ledger's versions, and the AI in the side panel. The app reads the files the method
writes, so a step taken in the terminal shows in the window and the other way round.

When the desk and the car disagree, the path falls back to the iterative loop that won the awards,
and the ledger records where. The whole path, phase by phase, is
[`references/phases/virtual-first.md`](skills/autosound-tuning/references/phases/virtual-first.md);
the phase files behind it are listed in [`SKILL.md`](skills/autosound-tuning/SKILL.md).

## What a session sounds like

Three voices: **you** at the listening seat, **Claude** driving the process, **Gemini** challenging
every move. A short illustration of the loop on the desk-first path — the shape of the exchange,
not a transcript:

> **You (Arbiter):** The bass is thin, and it pulls to the passenger side.
>
> **Claude (Generator):** Before any EQ: in the predicted sum, the sub-to-midbass joint at 80 Hz sits 4 dB below either driver on its own. That is a timing question, not a tone one. Two delays fit the magnitude equally well — 3.4 ms, and 3.4 minus one whole cycle.
>
> **Gemini (Critic):** Then say which one the arrival supports. A candidate a full cycle off looks identical at the joint and falls apart an octave above it.
>
> **Claude:** The arrival read from the measured impulse says 3.4 ms; its twin loses 2 dB at 300 Hz. Taking 3.4 — banked as a version you can revert in one step.
>
> **You:** Entered. Centred now — but one note booms.
>
> **Claude:** The entry control says the car agrees with the desk to 0.6 dB, so it is not the alignment. 63 Hz stands still across all nine positions around your head, which makes it the cabin, and a cabin mode is EQ's to cut: one band, −4 dB, Q 3, on the midbass pair.
>
> **Gemini:** Agreed, and check the sub is not being asked for the same cut twice — the two overlap below 80.
>
> **You:** Better. Leaving it.

Each step there is a number the tools computed rather than a rule of thumb, and each is a version
in the ledger, revertable in one step. A real session written up with every number — a hard call on
a cabin mode, resolved through this loop — is in
[the case study](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md).

## Which models to use

**Generator: Claude Opus, at `xhigh` effort. Reviewer: Gemini Pro (High).** That is the one
combination this method has been driven with end to end. Anything else is an experiment you are
running, and worth reading as one.

It matters because of the *shape* of the failure. **A weaker model does not stop with an error, it
agrees with you.** One documented run closed phases −1 through 3 in a single sitting and reported
crossover points, delays to 0.1 ms, EQ "within ±0.5 dB", and a listening verdict, on a car nobody
had sat in. Nothing in that transcript looked broken. It simply wasn't a tune.

| Mode | Setup | Reliability |
| :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude drives, Gemini reviews | Highest: two perspectives, slower per decision |
| **B: Solo drive** | one model drives and reviews itself | Lower: one perspective, and its numbers want checking by hand |

Which model to drive with, from my experience so far:

* **Opus**, the default for tuning. It holds a long session together and decides where a weaker
  model stops to ask. `xhigh` is the floor; on the hard turns, run it at Max effort.
* **Sonnet**, not for a complex tune. Cautious, and it loses the thread once facts have to be
  synthesised across a long session. Fine for short, bounded steps.
* **Fable**, for research. Where the task is to find a new approach rather than apply a known one,
  it has produced the best ideas here.
* **Gemini**, as the Critic, on a Pro tier. As a driver under the current rules it is unverified.

Models and tiers shift from month to month, so treat this as a starting point rather than a
verdict, and try them yourself. What does not move is the shape of the failure: whatever you pick,
a model asked to think less will not tell you so. Setup details, including a free browser-based
reviewer through Google AI Studio, are in the [FAQ](FAQ.md).

## The math under the hood

A library of local scripts crunches the large data sets, so the models never spend tokens on them
and never guess a number they could compute:

- **A cabin and install flaw map, built before any tuning.** Door nulls, reflections and left/right
  "pockets" that no stereo EQ can fill are found in the first sweeps, so the EQ plan works *around*
  the cabin instead of fighting it.
- **The sum is predicted, not hoped for.** Any pair of drivers is summed from their measured
  responses with the DSP's filters in place; delay and polarity are chosen by how little the joint
  loses, the candidate a whole cycle off is named, and four independent timing reads must agree
  before any delay is touched.
- **No driver is ever asked to fight physics.** A fillable dip and an interference null look alike
  on a chart; an excess-phase test tells them apart, and only the fillable one may be boosted.
- **The curve is trusted at the width where it is true.** The spread across the positions around
  the head, measured in *your* car, says which features stay put (the driver) and which move with
  the microphone (the seat), and sets how narrow a filter may be, band by band.
- **EQ is proposed as packages through gates**, resonances → left/right shape → tone, cuts only by
  default; *"it cuts the ear"* becomes a short list of suspects ranked by how loud the ear hears
  them, each with one A/B.
- **Every proposed filter is simulated on your own measured responses** before you type it in,
  scored under small delay and level drift so it survives the real world rather than winning at
  one razor point, and confirmed by an entry control once entered.
- **A check whose input is missing fails.** It never reports "no objection" for want of data —
  no delay from a single estimator, no EQ on a capture round that drifted, no round without its
  protective filters on record.

Everything the method can do, by what you want rather than by file name, is on one board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md) —
67 capabilities in 13 directions, each with the command, what it needs and refuses without, and
where the reasoning lives. A checker in the test suite keeps the board honest against the code.
Every `rew_tool` module carries its own `--selftest`, anchored to definitions rather than to its
own output, and [`scripts/run-selftests.sh`](scripts/run-selftests.sh) runs them all.

## What's in here

```
autosound-tuning-skill/
├── install.sh · install.ps1 · install.cmd    the installer, for macOS and Windows
├── skills/autosound-tuning/                  the skill (a Claude Code plugin)
│   ├── SKILL.md         entry point — process map, session lifecycle, roles
│   ├── references/      the doctrine: core/ (capabilities board, review loop, what the tools
│   │                    refuse …), phases/ (−1…5, virtual-first), patterns/, tooling/
│   ├── knowledge/       accumulated car & DSP profiles (cars/, dsp/)
│   ├── rew_tool/        REW bridge, analysis, prediction and verification, EQ proposals,
│   │                    the ledger and the process — each module with a --selftest
│   ├── scripts/         the Advisor / Critic channel (Gemini, Claude, Codex)
│   ├── evals/           does the skill wake on the right request
│   └── curves.html      target-curve visualizer
├── scripts/             release checks: run-selftests.sh, tag-check.sh, installer-consistency.py
├── community-inbox/     case studies and contributed experience
└── CHANGELOG.md         every tag, with an Upgrading note
```

▶ **[Open the target-curve visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)** — drag in your own curve or a standard one from the [Nono Tuning Tool](https://nonotuningtool.com), right-click any point for a frequency-character guide, and compare curves side by side. One self-contained file, so it works offline; use Save As to keep a copy.

The independent-review method (Critic/Advisor/Arbiter, anti-anchoring) is written up in
[`references/core/review-loop.md`](skills/autosound-tuning/references/core/review-loop.md).

The desktop app is its own repository, [autosound-tcc](https://github.com/ayukhno/autosound-tcc);
the installer brings the newest tag of each — the app's, and the method's `v3.*` — and installs
the method into `~/.claude/skills/autosound-tuning`, where Claude Code finds it. Which app version
and which method version you are on is in the app under *Diagnostics → Installation*.

## Reporting a problem

Anything that broke, was wrong, or stopped you: **[open an issue](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose)**
— the beta-report form has fields for what happened and for the versions. It is the method's own
inbox; problems with the desktop app go [in the app's repository](https://github.com/ayukhno/autosound-tcc/issues/new/choose),
and TCC fills half that form in for you (*Diagnostics → Installation → Report a problem*). An issue
is answerable, and a message in a chat is not.

## Contributing your experience

The skill learns from every tune: it gathers feedback right in the terminal as you work, not via a
form. At wrap-up, once you are happy with the sound, it asks what helped, what was off, and any
DSP or car quirk you hit. Then, **with your explicit consent**, it offers to share the
*generalizable* lessons, to grow the shared method and the `knowledge/` library.

It captures **method and equipment classes only**: cabin behaviour, the gear class, which
techniques worked. **Never personal data, never full measurements.** You see exactly what is shared
and opt in per item. Confirmed lessons fold into the skill with attribution.

## Support

The skill is **free and open** (CC BY-SA) and always will be. Nothing is gated behind a payment. If
it helped and you would like to say thanks, there are two voluntary channels:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank jar](https://send.monobank.ua/jar/8wThVcodjm)** — one tap, no account; takes Apple Pay, Google Pay, Visa, Mastercard.

## License

[CC BY-SA 4.0](LICENSE): use it, adapt it, share it; keep derivatives open and attribute. It is a
method and knowledge work, so share-alike keeps the community's experience open.

Code and scripts (`rew_tool/`, `scripts/`, and other .py/.sh files) are under the
[MIT License](LICENSE-CODE). Third-party assets are listed in [LICENSES/NOTICE.md](LICENSES/NOTICE.md).
