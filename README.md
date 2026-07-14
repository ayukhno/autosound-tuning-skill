# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · [FAQ](FAQ.md)

**In one line:** a Claude skill that guides you toward clean, transparent, balanced sound in *your* car. It brings the whole craft to your specific setup, reads your REW measurements, and helps you choose each change.

- **Works with REW**: pulls measurements over its API, writes computed EQ filters back into REW for you to export to your DSP
- **Diagnoses before it fixes**: maps EQ-able frequencies, acoustic reflections (phase cancellations), and driver distortion floors from your baseline before proposing any crossover or EQ change
- **Knows the craft**: target curves, tuning practices, a step-by-step process
- **Test tracks**: what to listen for and on which track (descriptions, not audio)
- **Learns your setup**: accumulates car & gear knowledge, only with your consent

> [!CAUTION]
> AI can get numbers wrong. Always double-check crossover frequencies, slopes, and EQ values in your DSP before unmuting, especially on tweeters, and start at a low volume.

## Who it's for & Why

* **Who it's for:** For those building sound in their car and learning this craft. It's your exoskeleton (powered by your hearing and actions where direct software interfaces don't exist) that manages knowledge and experience so you can tune your car's audio.
* **Why:** Tuning is an avalanche: too many methods, parameters, and rules of thumb to hold in your head, and it's easy to dive into one detail and lose the whole picture. The skill is your navigator: it holds the knowledge, points to the few changes that matter, and keeps the soundstage-versus-tonal-balance trade-off in view. Your ear is the final judge.

It covers a full tune, from a new project through crossovers, time alignment, phase, per-channel and summed EQ, imaging, to voicing to taste, driven by a **Generator ↔ Critic ↔ Arbiter** review loop.

## Getting Started

This skill runs as a plugin for **Claude Code** (the official terminal agent by Anthropic). If you don't have it yet, the FAQ below has copy-paste macOS/Windows install steps (a paid Claude subscription is required; see the FAQ for cost paths).

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

## Recommended Models, Modes & My Take

The skill supports two ways to run it, ranked by reliability. Pick based on how much the tune matters versus how much setup you want to do:

| Mode | Setup | Reliability | Trade-off |
| :--- | :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude Sonnet 5 drives, Gemini reviews (2.5 Pro for hard acoustic calls, 2.5 Flash for routine) | Highest | Two AIs to configure; catches more, slower per decision |
| **B: Solo drive (Claude or Gemini)** | One model drives and reviews itself; escalate to a stronger tier for tough calls (Claude Opus 4.8, or a higher Gemini tier) | Lower, and it depends on which model you pick | One perspective; Gemini solo gives bold, non-standard proposals but needs its numbers double-checked by hand |

**My own experience so far** (this is just my experience for now; once more people have tuned with it, I want this to be community experience, not only mine):

* **Claude drives, Gemini reviews (Mode A):** stable, but moves in small steps, so it can feel a bit slow. You need to pay at least for Claude. Free Gemini works too, but it sometimes hits its limits. One more thing I noticed: Sonnet is reliable but cautious, and tends to stop and ask things that Opus would often just decide on its own, faster.
* **Gemini drives, with Claude or a stronger Gemini model as the reviewer:** much faster. After two full measurement rounds, I already had a first working version. But later in the session, it can start to hallucinate or lose track of earlier decisions, to the point where I wanted to switch back to Claude. I have not tried this with free Gemini, because of the limits — lifting Gemini's free-tier rate limits needs a paid Google Cloud billing account (the [FAQ's cost paths](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026) cover the current deposit / free-credit details, which change often). If you pay for API access either way, Mode A ends up cheaper overall.
* **The manual step-by-step version (no local scripts):** it works, but the copy-paste process is stressful. You have to be careful not to lose any value along the way. After trying a full session with real memory between messages, it takes effort to go back to this.

**Starting under Gemini as the driver:** not quite as fast as Claude Code, at least not yet. There is no plugin installer for it, but the quickest path is to point an agentic Gemini session (Antigravity CLI, or any Gemini setup with file and shell access) at the repo and ask it directly:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

See the FAQ for more detail.

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

The independent-review method (Critic/Advisor/Arbiter, anti-anchoring) is bundled as `references/core/review-loop.md`.

A separate, stateless web-chat version of the method, with no local install, lives on the [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) branch.

## Contributing your experience

The skill learns from every tune: it gathers feedback right in the terminal as you work, not via a form. At wrap-up (once you're happy with the sound) it asks what helped, what was off, and any DSP/car quirk you hit, then, **with your explicit consent**, offers to share the *generalizable* lessons (to grow the shared method + the `knowledge/` library).

It captures **method + equipment classes only**: cabin behavior, the DSP/gear class, which techniques worked. **Never personal data, never full measurements;** you see exactly what's shared and opt in per item. Confirmed lessons fold into the skill with attribution.

## Support

The skill is **free and open** (CC BY-SA) and always will be. Nothing is gated behind a payment. If it helped and you'd like to say thanks, there are two voluntary channels:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank jar](https://send.monobank.ua/jar/8wThVcodjm)** (Apple Pay, Google Pay, ...)

One tap, no account; the page also takes cards — Apple Pay, Google Pay, Visa, Mastercard.

## License

[CC BY-SA 4.0](LICENSE): use it, adapt it, share it; keep derivatives open and attribute. It's a method/knowledge work, so share-alike keeps the community's experience open.
