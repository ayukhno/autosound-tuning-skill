# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, draft)](ROADMAP.md)

**In one line:** a Claude skill that guides you toward clean, transparent, balanced sound in *your* car. It brings the whole craft to your specific setup, reads your REW measurements, and helps you choose each change.

- **Works with REW**: pulls measurements over its API, writes computed EQ filters back into REW for you to export to your DSP
- **Diagnoses before it fixes**: maps EQ-able frequencies, acoustic reflections (phase cancellations), and driver distortion floors from your baseline before proposing any crossover or EQ change
- **Knows the craft**: target curves, tuning practices, a step-by-step process
- **Test tracks**: what to listen for and on which track (descriptions, not audio)
- **Learns your setup**: accumulates car & gear knowledge, only with your consent

> [!CAUTION]
> AI can get numbers wrong. Always double-check crossover frequencies, slopes, and EQ values in your DSP before unmuting, especially on tweeters, and start at a low volume.

## Table of Contents

- [Who it's for & Why](#who-its-for--why)
- [What real work and synergy between different AIs looks like](#what-real-work-and-synergy-between-different-ais-looks-like)
- [Getting Started](#getting-started)
- [Recommended Models, Modes & My Take](#recommended-models-modes--my-take)
- [Full Setup & FAQ](#full-setup--faq)
- [What's in here](#whats-in-here)
- [Contributing your experience](#contributing-your-experience)
- [Support](#support)
- [License](#license)

## Who it's for & Why

* **Who it's for:** For those building sound in their car and learning this craft. It's your exoskeleton: it carries the craft's knowledge and experience, you bring the ears and the hands on the DSP.
* **Why:** Tuning is an avalanche: too many methods, parameters, and rules of thumb to hold in your head, and it's easy to dive into one detail and lose the whole picture. The skill is your navigator: it holds the knowledge, points to the few changes that matter, and keeps the soundstage-versus-tonal-balance trade-off in view. Your ear is the final judge.

It covers a full tune: from a new project through crossovers, time alignment, phase, per-channel and summed EQ, and imaging, to voicing to taste — plus the optional spatial layers (a complementary **center-fill** and a differential **rear-fill**, both field-validated recipes). Every change runs through a **Generator ↔ Critic ↔ Arbiter** review loop: one AI proposes, another challenges, you decide.

## What real work and synergy between different AIs looks like

Three voices: **you** at the listening seat, **Claude** driving the process, **Gemini** challenging every move.

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

About forty minutes from "it booms" to "the sub is on the hood" — a problem that usually eats weeks of forum-guided trial and error. Every participant caught something the others missed, and the loop resolved all of it. The full technical version, with every number: [the case study](case-study-mode-a-bass-2026-07-15.md).

**The math under the hood** — a library of scripts that crunches huge data sets locally, so it never burns model tokens on it:

- **A cabin & install flaw map, built before any tuning** — door nulls, reflections, and L/R "pockets" no stereo EQ can fill are mapped from the first sweeps, so EQ plans *around* the cabin instead of fighting it;
- **Multi-scale curve reading** — each curve is read at three "distances" (trend → shape → fine detail), and each finding goes to the tool that owns it: voicing, verification, a surgical cut, or "leave it, that's the room";
- **Jitter-robust phase summation** — crossover-joint fixes are scored under small delay/level drift, so they survive the real world instead of winning at one razor point;
- **Hardware-verified filter models** — every proposed EQ/all-pass is simulated on your *measured* responses before you type it in;
- **An excess-phase "boostability" gate** — tells a fillable dip from an interference null, so no driver is ever asked to fight physics;
- **Four-estimator arrival triangulation** — four independent timing reads must agree before any delay is touched;
- **Fundamental-aware distortion reading** — THD spikes are checked against the fundamental's level, so a room null is never misdiagnosed as a broken driver.

## Getting Started

This skill runs as a plugin for **Claude Code** (the official terminal agent by Anthropic). If you don't have it yet, the FAQ below has copy-paste macOS/Windows install steps; a paid Claude subscription is required, and the FAQ covers the cost paths. It also explains [why a full session uses fewer tokens than you'd expect](FAQ.md#why-a-full-session-uses-fewer-tokens-than-youd-expect).

Inside your active Claude Code session, run these commands **one by one** (do not copy and paste them together):

```bash
/plugin marketplace add ayukhno/autosound-tuning-skill
```

```bash
/plugin install autosound-tuning
```

```bash
/reload-plugins
```

*Then start tuning by saying:* **"tune a new car from scratch"**.

> **Triggering — include a car-audio word.** The skill wakes on *what you ask*, so a bare `resume` on its own won't fire it (too generic — it could mean any project). Add one domain word: **"resume my car-audio tune"**, **"continue tuning the car"**, **"what's my current DSP / crossover state"** (or in your language — «продовжити тюн авто», „Auto-DSP weiter einmessen", „wróćmy do strojenia car audio"). Same for a fresh start: name the car/audio, not just "help me".

**Starting under Gemini as the driver:** not quite as fast as Claude Code, at least not yet. There is no plugin installer for it, but the quickest path is to point an agentic Gemini session (Antigravity CLI, or any Gemini setup with file and shell access) at the repo and ask it directly:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

See the FAQ for more detail.

## Recommended Models, Modes & My Take

The skill supports two ways to run it, ranked by reliability. Pick based on how much the tune matters versus how much setup you want to do:

| Mode | Setup | Reliability | Trade-off |
| :--- | :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude drives (Sonnet 5 / Fable 5), Gemini reviews (a Pro tier — currently 3.1 Pro — for hard acoustic calls, Flash for routine) | Highest | Two AIs to configure; catches more, slower per decision |
| **B: Solo drive (Claude or Gemini)** | One model drives and reviews itself; escalate to a stronger tier for tough calls (Claude Opus 4.8, or a higher Gemini tier) | Lower, and it depends on which model you pick | One perspective; Gemini solo gives bold, non-standard proposals but needs its numbers double-checked by hand |

**My own experience so far** (this is just my experience for now; once more people have tuned with it, I want this to be community experience, not only mine):

* **Claude drives, Gemini reviews (Mode A):** stable, but moves in small steps, so it can feel a bit slow. You need to pay at least for Claude. Free Gemini works too, but it sometimes hits its limits. One more thing I noticed: Sonnet is reliable but cautious, and tends to stop and ask things that Opus would often just decide on its own, faster. On the plus side, Sonnet is thriftier with tokens, so you hit usage limits less often.
* **Gemini drives, with Claude or a stronger Gemini model as the reviewer:** much faster. After two full measurement rounds, I already had a first working version. But later in the session, it can start to hallucinate or lose track of earlier decisions, to the point where I wanted to switch back to Claude. I have not tried this with free Gemini, because of the limits — lifting Gemini's free-tier rate limits needs a paid Google Cloud billing account (the [FAQ's cost paths](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026) cover the current deposit / free-credit details, which change often). If you pay for API access either way, Mode A ends up cheaper overall.
* **The manual step-by-step version (no local scripts):** it works, but the copy-paste process is stressful. You have to be careful not to lose any value along the way. After trying a full session with real memory between messages, it takes effort to go back to this.
* **Which model to trust as driver, so far:** **Claude Opus** has given the most consistently stable results. **Sonnet 5** works but still comes across as less sure of itself in this role — worth double-checking its calls for now. **Fable 5** has produced the best results of any model: it audited and rebuilt the skill while running a full tuning session (see [audit-fable-2026-07-11.md](audit-fable-2026-07-11.md)), then drove a second full in-car session on the simplified rules — that build is currently the best-sounding result I have. **Gemini** lost some capability as the process rules grew more complex; after the audit simplified them, Gemini 3.1 Pro proved itself again in the **Critic** role, while Gemini as the *driver* under the new rules is still unverified — feedback from the community is welcome here.

## Full Setup & FAQ

Need help setting up Claude Code, running on **Windows**, configuring the **Gemini Critic** (including a free, browser-based workspace via **Google AI Studio**), or choosing a microphone?

See our **[FAQ.md](FAQ.md)**.

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

▶ **[Open the target-curve visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=en)** (or open `skills/autosound-tuning/curves.html` locally) — drag in your own curve or a standard one from the [Nono Tuning Tool](https://nonotuningtool.com), right-click any point on the chart for a frequency-character guide, and compare curves side by side. It's a single self-contained file (works offline) — use your browser's **Save As** to keep your own copy; the built-in curves and drag-drop importing keep working.

The independent-review method (Critic/Advisor/Arbiter, anti-anchoring) is bundled as `references/core/review-loop.md`; the [case study](case-study-mode-a-bass-2026-07-15.md) shows it working on a real hard call.

A separate, stateless web-chat version of the method, with no local install, lives on the [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) branch.

## Contributing your experience

The skill learns from every tune: it gathers feedback right in the terminal as you work, not via a form. At wrap-up (once you're happy with the sound) it asks what helped, what was off, and any DSP/car quirk you hit, then, **with your explicit consent**, offers to share the *generalizable* lessons (to grow the shared method + the `knowledge/` library).

It captures **method + equipment classes only**: cabin behavior, the DSP/gear class, which techniques worked. **Never personal data, never full measurements;** you see exactly what's shared and opt in per item. Confirmed lessons fold into the skill with attribution.

## Support

The skill is **free and open** (CC BY-SA) and always will be. Nothing is gated behind a payment. If it helped and you'd like to say thanks, there are two voluntary channels:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank jar](https://send.monobank.ua/jar/8wThVcodjm)** — one tap, no account; takes Apple Pay, Google Pay, Visa, Mastercard.

## License

[CC BY-SA 4.0](LICENSE): use it, adapt it, share it; keep derivatives open and attribute. It's a method/knowledge work, so share-alike keeps the community's experience open.

Code and scripts (`rew_tool/`, `scripts/`, and other .py/.sh files) are under the [MIT License](LICENSE-CODE). Third-party assets are listed in [LICENSES/NOTICE.md](LICENSES/NOTICE.md).
