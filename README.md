# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md)

**In one line:** a Claude skill that helps you tune car audio — it reads your REW measurements, analyzes them, recommends settings, and can push EQ back into REW.

- 📊 **Works with REW** over its API — pulls measurements, loads EQ filters back in
- 🎯 **Knows the craft** — target curves, tuning practices, a step-by-step process
- 🎧 **Test tracks** — what to listen for and on which track (descriptions, not audio)
- 🚗 **Learns your setup** — accumulates car & gear knowledge, only with your consent

It covers a full tune — from a new project (equipment + goals interview, target-curve choice, install checks) through crossovers, time alignment, phase, per-channel and summed EQ, and imaging, to taste voicing — driven by a Generator ↔ Critic ↔ Arbiter review loop. It's **method, not machine**: no car's measurements or DSP state live here (those stay in your project), so it works on **any car / any DSP**.

> Built and battle-tested on a VW Passat B8 / Helix DSP Ultra S (an AYA competition win); the car/DSP specifics are isolated into a profile + a `knowledge/` library, so a new project is just "pick the inputs."

## What's in here

```
skills/
├── autosound-tuning/   the main skill
│   ├── SKILL.md        entry point — process map, session lifecycle, roles
│   ├── references/     on-demand docs (phases, diagnostics, EQ, filters, staging,
│   │                   test tracks, REW API, Helix, intake, feedback …)
│   ├── knowledge/      accumulated car & DSP profiles (cars/, dsp/)
│   └── scripts/        example Critic-channel rig tooling (optional)
└── review-loop/        sibling skill: independent-review orchestration
```

The two are a **pair** — `autosound-tuning` uses `review-loop` for the review protocol. Install both.

## Getting started — new to Claude Code?

This skill runs in **Claude Code**, a terminal tool. Tuning is iterative (measure → analyze → change → re-measure) over text/numeric data, so a terminal + git — parsing, scripting, full change history — fit far better than the web app.

**1. Install Claude Code** (macOS / zsh; needs Node.js 18+ and a paid Claude plan — Pro / Max / Team / Enterprise):
```bash
node --version                                   # Node.js 18 or newer
mkdir -p ~/.npm-global && npm config set prefix '~/.npm-global'
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
npm install -g @anthropic-ai/claude-code
claude --version                                 # verify
```

**2. Create a project folder and launch:**
```bash
mkdir ~/car-audio-setup && cd ~/car-audio-setup
claude                                            # first run opens the browser to log in
```

**3. Start simple.** An empty folder, your first REW export dropped in as-is, one append-only notes log — let subfolders appear when you actually need them.

**4. Your first message = "step 0".** Describe your system: car + speaker layout (ways, sub?), DSP model, measurement gear, and whether you have measurements yet. The skill takes it from there — and **first asks your preferred working language** (EN · UK · DE · PL) so the conversation and your project files come out in it.

## Requirements

- **Claude Code** (or claude.ai with skills).
- **REW** with the API server on (`localhost:4735`) and a calibrated mic.
- Your **DSP's software** + a way to load EQ (file import ideal; for 30+ DSPs without it, see [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Optional:** a second AI model as the "Critic" (any vendor). Without it a human reviews; the process still holds.

## Install

**Easiest — ask Claude to do it.** Open Claude Code and say:

> *"Clone https://github.com/ayukhno/autosound-tuning-skill into a temp folder, then copy the two **inner** folders `skills/autosound-tuning` and `skills/review-loop` into `~/.claude/skills/`, so each `SKILL.md` lands directly at `~/.claude/skills/<name>/SKILL.md`. Don't clone the whole repo into the skills folder."*

Install **both** (they're a pair) at **user level — `~/.claude/skills/`** (available everywhere, recommended) or **project level — `<project>/.claude/skills/`** (keeps one car's repo self-contained).

> ⚠️ **The one mistake to avoid:** don't `git clone` the repo *into* `~/.claude/skills/autosound-tuning/`. That nests `SKILL.md` a level too deep and Claude reports **`Unknown skill`**. Always copy the **inner** `skills/*` folders so `SKILL.md` sits *directly* under the skill folder.

**Manual:**
```bash
git clone https://github.com/ayukhno/autosound-tuning-skill.git
cp -R autosound-tuning-skill/skills/autosound-tuning ~/.claude/skills/
cp -R autosound-tuning-skill/skills/review-loop      ~/.claude/skills/
# verify — each must print the path (SKILL.md directly under the skill folder):
ls ~/.claude/skills/autosound-tuning/SKILL.md
ls ~/.claude/skills/review-loop/SKILL.md
```

**Then start a fresh Claude Code session** (skills load at startup) and say e.g. *"tune a new car from scratch"* — the skill begins with **intake**: quickstart, equipment + goals interview, target-curve choice (chosen with you), install checks, project-file generation. *(If `Unknown skill` or it never triggers — almost always the nesting above; re-copy the inner `skills/*` folders and restart.)*

## Contributing your experience

The skill **learns from every tune — gathering feedback right in the terminal as you work, not via a form.** At wrap-up (Phase 7) it asks what helped, what was off, and any DSP/car quirk you hit — then, **with your explicit consent**, offers to share the *generalizable* lessons (to grow the shared method + the `knowledge/` library).

It captures **method + equipment classes only** — cabin behavior, the DSP/gear class, which techniques worked. **Never personal data, never full measurements;** you see exactly what's shared and opt in per item. Confirmed lessons fold into the skill with attribution; contradicting tips are kept as *variants*, not deleted. *(Prefer GitHub? Open a [field-feedback issue](../../issues/new?template=field-feedback.md) — same rule.)*

## Support

The skill is **free and open** (CC BY-SA) and always will be — nothing is gated behind a payment. If it helped and you'd like to say thanks, there's a **voluntary tip jar**, no pressure:

☕ **[Support this skill — Monobank jar](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

One tap, no account; the page also takes foreign cards (Apple/Google Pay, Visa/Mastercard).

## License

[CC BY-SA 4.0](LICENSE) — use it, adapt it, share it; keep derivatives open and attribute. It's a method/knowledge work, so share-alike keeps the community's experience open.
