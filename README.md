# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · [FAQ](FAQ.md)

**In one line:** a Claude skill that guides you toward clean, transparent, balanced sound in *your* car — it brings the whole craft to your specific setup, reads your REW measurements, and helps you choose each change.

- 📊 **Works with REW** over its API — pulls measurements, loads EQ filters back in
- 🎯 **Knows the craft** — target curves, tuning practices, a step-by-step process
- 🎧 **Test tracks** — what to listen for and on which track (descriptions, not audio)
- 🚗 **Learns your setup** — accumulates car & gear knowledge, only with your consent

## Getting Started

This skill runs as a plugin for **Claude Code** (the official terminal agent by Anthropic).

### 1. Quick Installation

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

### 2. Comprehensive Setup & FAQ

Need help setting up Claude Code, running on **Windows**, configuring the **Gemini Critic** (including a completely free, browser-based workspace via **Google AI Studio**), or choosing a microphone?

👉 Refer directly to our comprehensive **[FAQ.md](FAQ.md)**.


## Recommended models

The skill runs a two-role loop — a **Driver** (Generator/Orchestrator) proposes, a **Critic/Advisor** stress-tests — so the models are **complementary, not competing**:

| Role | Recommended | Why |
| :--- | :--- | :--- |
| **Driver** — steers the session, reads REW, proposes values | **Claude Sonnet 5** | Reliable, structured, cost-efficient, an accurate data parser — the backbone of the process. Escalate to **Claude Opus 4.8** for crossover strategy, 3-way deadlocks, and final technical verdicts. |
| **Critic / Advisor** — challenges assumptions, cabin-physics depth | **Gemini** (2.5 Pro for hard acoustic calls, 2.5 Flash for routine) | Cross-vendor anti-anchoring + creative acoustic depth. Caveat: it can drift on long autonomous sessions — keep it on-demand and re-anchor from disk. |

**Which is "better"?** Neither — it's about the seat. **Claude Sonnet 5 is the dependable driver**; **Gemini is a high-value, low-cost second-vendor critic** (a different vendor catches more than a same-vendor peer). If you run just one, drive with Sonnet 5 and let the reviewer role fall back to a higher-tier Claude. Per-task detail → `SKILL.md` (Model Selection); operating modes → `references/core/process-control.md`.


## What's in here

```
autosound-tuning-skill/        a Claude Code plugin
└── skills/autosound-tuning/    the skill
    ├── SKILL.md        entry point — process map, session lifecycle, roles
    ├── references/     on-demand docs (phases, diagnostics, EQ, filters, staging,
    │                   test tracks, REW API, Helix, the review method, intake …)
    ├── knowledge/      accumulated car & DSP profiles (cars/, dsp/)
    └── scripts/        example Critic-channel rig tooling (optional)
```

One skill — the independent-review method (Critic/Advisor/Arbiter, anti-anchoring) is bundled as `references/core/review-loop.md`.

## Who it's for & Why

* **Who it's for:** For those building sound in their car and learning this craft. It's your exoskeleton which—powered by your hearing and actions where direct software interfaces don't exist—manages knowledge and experience to tune the car audio of your dreams.
* **Why:** Tuning is an avalanche — too many methods, parameters, and rules of thumb to hold in your head, and it's easy to dive into one detail and lose the whole picture. The skill is your navigator: it holds the knowledge, points to the few changes that matter, and keeps the soundstage-versus-tonal-balance trade-off in view. Your ear is the final judge.

It covers a full tune — from a new project through crossovers, time alignment, phase, per-channel and summed EQ, imaging, to voicing to taste — driven by a **Generator ↔ Critic ↔ Arbiter** review loop.

## Contributing your experience

The skill learns from every tune — gathering feedback right in the terminal as you work, not via a form. At wrap-up (once you're happy with the sound) it asks what helped, what was off, and any DSP/car quirk you hit — then, **with your explicit consent**, offers to share the *generalizable* lessons (to grow the shared method + the `knowledge/` library).

It captures **method + equipment classes only** — cabin behavior, the DSP/gear class, which techniques worked. **Never personal data, never full measurements;** you see exactly what's shared and opt in per item. Confirmed lessons fold into the skill with attribution.

## Support

The skill is **free and open** (CC BY-SA) and always will be — nothing is gated behind a payment. If it helped and you'd like to say thanks, there's a **voluntary tip jar**, no pressure:

☕ **[Support this skill — Monobank jar](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

One tap, no account; the page also takes foreign cards (Apple/Google Pay, Visa/Mastercard).

## License

[CC BY-SA 4.0](LICENSE) — use it, adapt it, share it; keep derivatives open and attribute. It's a method/knowledge work, so share-alike keeps the community's experience open.
