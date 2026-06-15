# Autosound Tuning Skill

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 [Polski](README.pl.md)

**In one line:** a Claude skill that helps you tune car audio — it reads your REW measurements, analyzes them, recommends settings, and can push EQ back into REW.

- 📊 **Works with REW** over its API — pulls measurements, loads EQ filters back in
- 🎯 **Knows the craft** — target curves, tuning practices, and a built-in step-by-step tuning process
- 🎧 **Test tracks** — what to listen for and on which track (the descriptions, not the audio)
- 🚗 **Learns your setup** — accumulates car & gear knowledge from a tuning angle (only with your consent)

A [Claude](https://claude.com/claude-code) **skill** for tuning a car-audio DSP with [REW](https://www.roomeqwizard.com/) — from a brand-new project (equipment + goals interview, target-curve choice, install verification) through crossovers, time alignment, phase, per-channel and summed EQ, imaging/staging, to client-preference voicing. It encodes a measured **method** (Generator ↔ Critic ↔ Arbiter review loop) plus a growing library of hard-won diagnostic techniques.

The skill is **method, not machine.** No car's measurements or DSP state live here — those stay in the tuner's own project. This repo ships the reusable process so it works on **any car / any DSP**.

> Built and battle-tested on a VW Passat B8 / Helix DSP Ultra S (an AYA competition win), but the car/DSP specifics are isolated into a profile + a `knowledge/` library so a new project is just "pick the inputs."

## What's in here

```
skills/
├── autosound-tuning/      the main skill
│   ├── SKILL.md           entry point (process map, session lifecycle, roles)
│   ├── references/        on-demand docs: phases, diagnostics, EQ patterns,
│   │                      filter types, staging/depth, competition, test tracks,
│   │                      voicing-by-ear, REW API, Helix specifics, intake, feedback
│   ├── knowledge/         accumulated car & DSP profiles (cars/, dsp/)
│   └── scripts/           example Critic-channel implementation (optional rig tooling)
└── review-loop/           sibling skill: independent-review orchestration (vendor-agnostic)
```

The two skills are a **pair** — `autosound-tuning` references `review-loop` for the review protocol. Install both.

## Getting started — new to Claude Code / the terminal?

This skill runs in **Claude Code**, a terminal tool. If you've only used desktop/web chat before, here's the one-time setup. *(Other languages: [Deutsch](README.de.md) · [Polski](README.pl.md).)*

**Why Claude Code (not the web app / Cowork):** tuning is iterative — measure → analyze → change → re-measure — over text/numeric data (REW CSV/text exports, DSP configs, iteration logs). A terminal + git gives you parsing, scripting, and a full change history. Cowork is oriented to file operations in other apps — overkill here.

**1. Install Claude Code** (macOS / zsh; needs Node.js 18+ and a paid Claude plan — Pro / Max / Team / Enterprise; the free plan won't work):
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

**3. Don't over-structure.** Start with an empty folder. Drop in your first REW export (`.txt`/`.csv`) as-is, keep one markdown notes log (append-only), and let folders (`measurements/`, `configs/`, `eq-log/`) appear when you actually need them.

**4. Your first message = "step 0".** Describe your system in one message: car + speaker layout (how many ways, sub?), DSP model (Helix / Audison / other), measurement gear (mic, interface), and whether you already have measurements or are starting from the hardware. The skill takes it from there — and **first asks your preferred working language** (English / your native, if supported: EN · UK · DE · PL) so the conversation and your project files come out in it. Then: intake → signal-chain check → mic calibration → first sweep → …

(Then install the skill itself — next section.)

## Requirements

- **Claude Code** (or claude.ai with skills).
- **REW** with the API server enabled (`localhost:4735`), a calibrated measurement mic.
- Your **DSP's software** and a way to load EQ into it (file import ideal; for 30+ DSPs without import, see [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Optional:** a second AI model as the "Critic" (any vendor — the roles are vendor-agnostic). Without it, a human plays the reviewer; the process still holds.

## Install

**Easiest — let Claude install it for you.** Open Claude Code and just ask, for example:

> *"Install the `autosound-tuning` skill and its `review-loop` companion from https://github.com/ayukhno/autosound-tuning-skill into my user-level skills folder (`~/.claude/skills/`) so it's available everywhere."*

Claude clones the repo and places **both** skills (they're a pair) where you choose:

- **User-level — `~/.claude/skills/`** *(recommended)*: available in **every** folder you open Claude Code in. Pick this if you'll tune more than one car or want it always on hand.
- **Project-level — `<your-project>/.claude/skills/`**: only inside that one project. Pick this to keep a single car's repo self-contained.

**Or do it manually:**
```bash
git clone https://github.com/ayukhno/autosound-tuning-skill.git
# user-level (available everywhere):
cp -R autosound-tuning-skill/skills/autosound-tuning ~/.claude/skills/
cp -R autosound-tuning-skill/skills/review-loop      ~/.claude/skills/
# …or project-level: cp -R the same two folders into  your-project/.claude/skills/
```

Then open Claude Code in your project and say e.g. *"tune a new car from scratch"* — the skill starts with **intake** (`references/project-intake.md`): quickstart, equipment + goals interview, target-curve choice (no default — chosen with you), install verification, and project-file generation. *(It first asks your preferred working language — you can run the whole local project in your own language; English here is just the skill's internal method.)*

## Contributing your experience

The skill **learns from every tune — and it gathers that feedback right in the terminal, while you work, not via a form to fill in.** At wrap-up (Phase 7) it runs a short closing ritual: asks what actually helped, what was off, and any DSP/car quirk you hit — then, **with your explicit consent**, offers to share the *generalizable* lessons.

**What the final survey is for, and what it collects:** to grow the shared method + the `knowledge/` library. It captures **method + equipment classes only** — the car body/cabin behavior, the DSP/processor and gear class, and which techniques worked. **Never personal data, never full measurements.** You see exactly what would be shared and opt in (or out) per item.

Confirmed lessons get folded into the skill and the `knowledge/` car/DSP profiles (with attribution). Tips that contradict existing findings are kept as *variants*, not deletions — a different cabin may make them right.

*(Prefer GitHub? You can still open a [field-feedback issue](../../issues/new?template=field-feedback.md) — same rule: method/equipment classes only.)*

## License

[CC BY-SA 4.0](LICENSE) — use it, adapt it, share it; keep derivatives open and give attribution. It's a method/knowledge work, so share-alike keeps the community's accumulated experience open.
