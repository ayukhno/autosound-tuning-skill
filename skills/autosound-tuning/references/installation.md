# Installing and Updating the Autosound Tuning Skill

This document describes how to install, update, and set up the `autosound-tuning` skill.

## Installation Methods

### 1. Claude Code Plugin (Recommended)
This skill ships as a **Claude Code plugin** (the `autosound-tuning-skill` repo is a single-plugin marketplace). The canonical install is **one command — no manual copy, no nesting traps:**
```bash
/plugin marketplace add ayukhno/autosound-tuning-skill
/plugin install autosound-tuning
```

* **Update:** `/plugin update autosound-tuning` (or re-install from the marketplace). The plugin bundles the whole skill — `references/` (incl. the review-loop method, now `references/review-loop.md`), `scripts/`, `rew_tool/`, `knowledge/`.

---

### 2. Developer / Author Setup
A clone + a symlink of the inner `skills/autosound-tuning` into `~/.claude/skills/` also works (edits go live; update = `git pull`). 

> [!WARNING]
> Never `git clone` the whole repo *into* `~/.claude/skills/autosound-tuning/` — `SKILL.md` then sits one level too deep → "Unknown skill"; symlink the **inner** `skills/autosound-tuning` instead.

---

### 3. Plain File Copy (Legacy fallback)
If you find this installed as a **plain file copy** that the user wants to keep updated, we recommend offering to switch to the plugin (above) to avoid manual copying/clone-syncing over it each time which can lead to drift.

For details on distribution, versions, and how experience flows back, see [feedback-loop.md](file:///skills/autosound-tuning/references/feedback-loop.md).
