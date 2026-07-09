# Installing and Updating the Autosound Tuning Skill

This document describes how to install, update, and set up the `autosound-tuning` skill.

## Installation Methods

### 1. Claude Code Plugin (Recommended)
This skill ships as a **Claude Code plugin** (the `autosound-tuning-skill` repo is a single-plugin marketplace). Run these commands **one by one** (do not copy and paste them together, as Claude Code's prompt is interactive and pasting them together deadlocks):
```bash
/plugin marketplace add ayukhno/autosound-tuning-skill
```

```bash
/plugin install autosound-tuning
```

```bash
/reload-plugins
```

* **Update:** `/plugin update autosound-tuning` (or re-install from the marketplace). The plugin bundles the whole skill — `references/` (incl. the review-loop method, now `references/core/review-loop.md`), `scripts/`, `rew_tool/`, `knowledge/`.

---

### 2. Developer / Author Setup
A clone + a symlink of the inner `skills/autosound-tuning` into `~/.claude/skills/` also works (edits go live; update = `git pull`). 

> [!WARNING]
> Never `git clone` the whole repo *into* `~/.claude/skills/autosound-tuning/` — `SKILL.md` then sits one level too deep → "Unknown skill"; symlink the **inner** `skills/autosound-tuning` instead.

---

### 3. Plain File Copy (Legacy fallback)
If you find this installed as a **plain file copy** that the user wants to keep updated, we recommend offering to switch to the plugin (above) to avoid manual copying/clone-syncing over it each time which can lead to drift.

---

## Verify the install (one command)

After a clone / `git pull` / plugin update — or on a fresh machine (Windows/macOS/Linux) — run the
smoke test to confirm the deterministic tooling works here (versioned state, apply-change gate, the
issue-#5 multi-slot integrity, side-effect / pre-sweep gates). Offline + stdlib-only; it also prints
an INFO line on the reviewer channel (local CLI / API key) without failing on it:
```
python skills/autosound-tuning/scripts/smoke_test.py     # exit 0 = healthy · SMOKE_VERBOSE=1 for tracebacks
```

## Troubleshooting

- **Antigravity / agy sandbox — state snapshots vanish.** Some agent environments restrict certain file writes to the session's own directory (observed on Antigravity: an artifact-write outside `…/brain/<session>/` was refused). If versioned snapshots don't land where you expect, point `AUTOSOUND_STATE_ROOT` inside the project and verify it's writable **from within the session**: `python rew_tool/state/state.py selftest` (must print `selftest OK`); confirm the root actually fills after the first `apply.py propose`.
- **Reviewer CLI hangs inside an agent session.** Spawning a reviewer CLI (agy/claude) from *inside* another agent session deadlocks chronically (agent-inside-agent; observed ~15/20 field sessions). `autosound_ai.py` kills a hung CLI after `AUTOSOUND_CLI_TIMEOUT` (default 120 s) and falls back to Clipboard Mode — but the reliable pattern is running reviewer wrappers from a **separate terminal**. See [process-control.md](file:///skills/autosound-tuning/references/core/process-control.md).
- **A tool/file looks MISSING, or the skill seems to contradict its own docs — symlink-blind search (Lesson 2026-07-08).** The dev/author install is a **symlink** (`~/.claude/skills/autosound-tuning` → the repo), and a plain `find` does **not** traverse a symlink on macOS → a false "this file/tool doesn't exist". **Real incident:** `rew_tool/target_bands.py` was declared a "gap" while it existed and was documented as the solution; the whole session then went the wrong way on that false premise. **Fix:** before concluding anything is missing or broken, re-check with `find -L` / `ls` / the CANONICAL repo path (`…/dev/Claude/autosound-tuning-skill/skills/autosound-tuning`), never a symlink-blind `find`; when the code contradicts the docs, read the actual source.
  - ⚠️ **Why the damage is systemic, not one file.** A symlink-blind search silently hides *arbitrary* skill content across BOTH tiers — e.g. the always-loaded **sample-rate** guardrail in `SKILL.md` (DSP-agnostic: samples at the wrong native rate ruin the alignment) *and* the equipment-specific value it points to (`knowledge/dsp/helix-dsp-ultra-s.md`: Helix native rate = 96 kHz) — none of which the user ever saw flagged. So the moment you notice a symlink-blind read, treat your whole view of the skill as **partial**: re-resolve the install, re-load from the canonical path, and treat conclusions reached earlier in the session as suspect until re-checked — don't just patch the one visible symptom.
  - **When it's a real discrepancy, the operational rule (ASK the Arbiter → fix/inbox or wait/file-issue) lives in `SKILL.md` guardrails.** The issue-triage / auto-answer side (`scripts/issue_triage.py`) is intentionally still WIP — asking + filing + an honest "wait" is the part that must always happen.

For details on distribution, versions, and how experience flows back, see [feedback-loop.md](file:///skills/autosound-tuning/references/core/feedback-loop.md).
