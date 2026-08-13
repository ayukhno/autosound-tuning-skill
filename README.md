# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, draft)](ROADMAP.md)

**In one line:** an AI tuning assistant for your car. It reads your REW measurements and takes you
through crossovers, time alignment, phase and EQ, one checked change at a time.

- **Works with REW**: pulls your measurements over its API, and writes computed EQ filters back
  into REW for you to export
- **Diagnoses before it fixes**: maps the cabin's reflections, nulls and driver distortion from
  your baseline sweeps before it proposes a single change
- **Never touches your processor**: you type every number into the DSP yourself, so nothing
  changes in the car without you
- **Knows the craft**: target curves, a phase-first EQ order, a step-by-step process, and which
  test track to listen to for what
- **Learns your setup**: accumulates knowledge about your car and gear, only with your consent

Tuned with this method, my own car took **1st in class at two AYA competitions in 2026**:
Einsteiger 5000 in May, with the graph-analysis-and-Gemini workflow that later became this skill,
then Amateur 5000 in July with the skill itself and my own ears.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA May 2026 Einsteiger 5000">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA Jul 2026 Amateur 5000">
</p>

> [!CAUTION]
> AI can get numbers wrong. Always double-check crossover frequencies, slopes, and EQ values in
> your DSP before unmuting, especially on tweeters, and start at a low volume.

> [!NOTE]
> **Prefer a window to a terminal?** [TCC](https://github.com/ayukhno/autosound-tcc), the companion
> desktop app, runs this same method in a desktop window: the DSP tree, your REW curves, the plan,
> and the AI in a side panel. It installs from the same command below. It is early, and the method
> in a terminal is the proven path.

## Table of contents

- [Who it's for](#who-its-for)
- [What you need](#what-you-need)
- [Getting started](#getting-started)
- [What a session actually sounds like](#what-a-session-actually-sounds-like)
- [Which models to use](#which-models-to-use)
- [The math under the hood](#the-math-under-the-hood)
- [What's in here](#whats-in-here)
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

| | why | notes |
| :-- | :-- | :-- |
| **[Claude Code](https://claude.com/claude-code)** | the skill runs inside it | a paid Claude subscription is required; the [FAQ covers the plans and what a session costs](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026) |
| **[REW](https://www.roomeqwizard.com/)**, with its API on | this is where measurements come from | open *Preferences → API* in REW and check that `localhost:4735` answers |
| **a calibrated measurement microphone** | ears alone cannot see a 40 Hz null | XLR with a physical loopback is best for phase; [UMIK-1 vs XLR in the FAQ](FAQ.md#measuring-phase--time-alignment-umik-1-vs-xlr-microphones) |
| **a DSP you can type into** | the skill proposes, you enter | any processor works; the one shipped device profile so far is Helix DSP Ultra S |
| **a second AI as reviewer** | optional, and most of the value | without one it runs solo and says so; [how to add one](FAQ.md) |

## Getting started

Install in a terminal, with one line:

```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash -s -- --terminal
```

To install the [TCC desktop app](https://github.com/ayukhno/autosound-tcc) as well, use `--tcc`
instead of `--terminal`. The installer explains each step before it runs it, and installs Claude
Code itself if you do not have it.

Then make a folder for the car, and start:

```sh
mkdir -p ~/Autosound/my-car && cd ~/Autosound/my-car
```

```sh
claude
```

*Then start tuning by saying:* **"tune a new car from scratch"**.

Everything about that car lives in that one folder, so copying the folder copies the whole tune.

> **Triggering: include a car-audio word.** The skill wakes on *what you ask*, so a bare `resume`
> will not fire it, because it could mean any project. Add one domain word: **"resume my car-audio
> tune"**, **"continue tuning the car"**, **"what's my current DSP / crossover state"**, or in your
> own language («продовжити тюн авто», „Auto-DSP weiter einmessen", „wróćmy do strojenia car
> audio"). Same for a fresh start: name the car or the audio, not just "help me".

> **Set the model and the effort before that first message.** They are fixed for the session and
> nothing raises them later. As of August 2026: **Claude Opus at `xhigh`**, with **Gemini Pro
> (High)** reviewing. [Why the cheaper combinations fail quietly](#which-models-to-use).

<details>
<summary>Other ways in: Gemini as the driver, or the 2.x plugin you may already have</summary>

**Under Gemini as the driver.** There is no plugin installer, but you can point an agentic Gemini
session (Antigravity CLI, or any Gemini setup with file and shell access) at the repository:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`,
> and follow that method as your operating instructions for this session.

**Already installed the 2.x plugin?** Then you are on the 2.x line, it stays supported, and no
update will move you off it: the marketplace entry names an exact commit rather than a branch.
Your existing projects stay readable there.

The line above installs 3.x, which stores a project as machine-readable files instead of prose,
records the process, and is what TCC reads. One skill per machine: two plugins shipping a skill of
the same name both stay active, and which one answers is anybody's guess. So remove the plugin
first, inside Claude Code:

```
/plugin uninstall autosound-tuning
```

```
/plugin marketplace remove autosound-tuning-skill
```

Your 2.x projects are not converted. 3.x imports the car's **current** state into a **new**
project and leaves the old one untouched:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <old-project> --into <new-project>
```

Channels and their output slots, crossovers, delays, gains, polarity, EQ and the DSP profile move
across. The journal and older snapshots stay behind, deliberately: 2.x never recorded which facts
were in force when, so carrying its history would mean inventing it.
</details>

## What a session actually sounds like

Three voices: **you** at the listening seat, **Claude** driving the process, **Gemini** challenging
every move.

> **You (Arbiter):** The double bass booms a bit. And when I nudged the delays by ear, the bass got better — let's enter my values?
>
> **Claude (Generator):** Checked against fresh measurements first: your delays are already optimal — your ear liked something else. The real culprits are two narrow door resonances and a hot left side. I propose three surgical cuts.
>
> **Gemini (Critic):** Objection: one of those cuts sits inside a crossover joint — it can break the summation there.
>
> **Claude:** Verified on the measurements — that joint actually gets *better*. But your doubt made me look deeper, and you're onto something: it's not just the woofer, the midrange is hot there too. Revised plan: each driver gets its own cut.
>
> **Gemini:** Now agreed.
>
> **You:** Entered. The boom is gone… but the subwoofer now localizes behind me!
>
> **Claude:** My miss — two of my filters overlap and cut deeper than intended. Softening one.
>
> **You:** Bass is back up front — but it sits low. I want it up on the windshield, where it used to be.
>
> **Claude:** The old defect was what propped the image up. We won't bring the defect back — a gentle symmetric EQ lift on both midranges instead, so the height returns without the skew.
>
> **You:** …The sub is on the hood! Leaving it.

About forty minutes from "it booms" to "the sub is on the hood", on a problem that usually eats
weeks of forum-guided trial and error. Every participant caught something the others missed. The
full technical version, with every number, is in
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

A library of local scripts crunches the large data sets, so the models never spend tokens on them:

- **A cabin and install flaw map, built before any tuning.** Door nulls, reflections and left/right
  "pockets" that no stereo EQ can fill are found in the first sweeps, so the EQ plan works *around*
  the cabin instead of fighting it.
- **Four independent timing reads must agree** before any delay is touched.
- **No driver is ever asked to fight physics.** A fillable dip and an interference null look alike
  on a chart; a phase test tells them apart, and only the fillable one gets boosted.
- **Every proposed filter is simulated on your own measured responses** before you type it in, and
  scored under small delay and level drift so it survives the real world rather than winning at one
  razor point.

## What's in here

```
autosound-tuning-skill/        a Claude Code plugin
└── skills/autosound-tuning/    the skill
    ├── SKILL.md        entry point — process map, session lifecycle, roles
    ├── references/     on-demand docs (phases, diagnostics, EQ, filters, staging,
    │                   test tracks, REW API, Helix, the review method, intake …)
    ├── knowledge/      accumulated car & DSP profiles (cars/, dsp/)
    ├── rew_tool/       REW API bridge, analysis, target-curve generation, versioned state
    ├── scripts/        Critic/Advisor channel wrappers (Gemini, Claude, Codex)
    └── curves.html     target-curve visualizer
```

▶ **[Open the target-curve visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)** — drag in your own curve or a standard one from the [Nono Tuning Tool](https://nonotuningtool.com), right-click any point for a frequency-character guide, and compare curves side by side. One self-contained file, so it works offline; use Save As to keep a copy.

The independent-review method (Critic/Advisor/Arbiter, anti-anchoring) is written up in
`references/core/review-loop.md`. A stateless web-chat version of the method, with no local
install, lives on the [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) branch.

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
