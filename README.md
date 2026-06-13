# Autosound Tuning Skill

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

## Requirements

- **Claude Code** (or claude.ai with skills).
- **REW** with the API server enabled (`localhost:4735`), a calibrated measurement mic.
- Your **DSP's software** and a way to load EQ into it (file import ideal; for 30+ DSPs without import, see [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Optional:** a second AI model as the "Critic" (any vendor — the roles are vendor-agnostic). Without it, a human plays the reviewer; the process still holds.

## Install

```bash
git clone https://github.com/ayukhno/autosound-tuning-skill.git
# into a project, e.g. symlink both skills:
ln -s "$PWD/autosound-tuning-skill/skills/autosound-tuning" your-project/.claude/skills/autosound-tuning
ln -s "$PWD/autosound-tuning-skill/skills/review-loop"      your-project/.claude/skills/review-loop
```

Then open Claude Code in your project and say e.g. *«налаштуй нову машину з нуля»* / *"tune a new car from scratch"* — the skill starts with **intake** (`references/project-intake.md`): quickstart, equipment + goals interview, target-curve choice (no default — chosen with you), install verification, and project-file generation.

## Contributing your experience

This skill is designed to **learn from every tune.** If a technique worked (or the skill was wrong, or you found a DSP/car quirk), open a **[field-feedback issue](../../issues/new?template=field-feedback.md)** — there's a template. **Method and equipment classes only — no personal data, no full measurements.** Confirmed lessons get folded into the skill and the `knowledge/` profiles (with attribution). Tips that contradict existing findings are kept as *variants*, not deletions — a different cabin may make them right.

## License

[CC BY-SA 4.0](LICENSE) — use it, adapt it, share it; keep derivatives open and give attribution. It's a method/knowledge work, so share-alike keeps the community's accumulated experience open.
