# Installing and Updating the Autosound Tuning Skill

This document describes how to install, update, and set up the `autosound-tuning` skill.

## Installation Methods

**One supported way to install 3.x: the installer** (the user's decision, 2026-09-16 —
docs/SIMPLIFICATION-2026-09-16.md §7.4). The plugin catalogue is pinned at 2.8.3 and moves only with
3.1.0; until then two install stories were one too many.

### 1. The installer (recommended — the only supported path for 3.x)
The one-liner is in `README.md` §Install (it names the current release, and `scripts/docs-check.py`
keeps every README and FAQ on the same tag): `install.sh` on macOS/Linux, `install.ps1` on Windows. It
clones the method at the newest `v3.*` release into `~/.claude/skills/.autosound-tuning-src` and links
`~/.claude/skills/autosound-tuning` at it — a clone plus a symlink, done for you.

* **Update:** run the same one-liner again; it moves the clone to the newest release.
* **Options:** `install.sh --help` / `install.ps1 -Help` (the method only with `--terminal`, the
  GitHub backup with `--github`, the beta channel below).
* **Phase 1's desk engine comes with it on a machine that cannot build one.** The engine is a
  self-contained binary attached to the tag's own release (~30 MB, one per platform); the installer
  fetches it **only when there is no .NET SDK** to build the wrapper from, checks it against the
  release's `SHA256SUMS`, and says which way it went. `--engine` / `-Engine` fetches it anyway,
  `--no-engine` / `-NoEngine` never. A release that carries no archive for this platform or this
  engine pin — only `win-x64`, `win-arm64` and `osx-arm64` are built — is said out loud, and the
  SDK route stands. By hand later, from the method's own folder:
  `python3 rew_tool/resonalyze_engine.py fetch-binary --tag v3.0.57` (or `install-binary --from <zip>`
  for a file you already have). `--uninstall` removes the engine with the rest.

---

### 2. Developer / Author Setup
A clone + a symlink of the inner `skills/autosound-tuning` into `~/.claude/skills/` (edits go live;
update = `git pull`). This is what the installer does, pointed at your own checkout.

> [!WARNING]
> Never `git clone` the whole repo *into* `~/.claude/skills/autosound-tuning/` — `SKILL.md` then sits one level too deep → "Unknown skill"; symlink the **inner** `skills/autosound-tuning` instead.

---

### 3. Found installed some other way
* **As a Claude Code plugin** (`/plugin install autosound-tuning`): that catalogue entry is pinned at
  **2.8.3**, not 3.x. Offer to switch to the installer (§1) and remove the plugin
  (`/plugin uninstall autosound-tuning`), or two copies of the method answer to one name —
  `deployment.py` below names both.
* **As a plain file copy:** offer to switch to the installer as well; a copy updated by hand drifts.

---

## Verify the install (one command)

After a clone / `git pull` / plugin update — or on a fresh machine (Windows/macOS/Linux) — run the
smoke test to confirm the deterministic tooling works here (versioned state, apply-change gate, the
issue-#5 multi-slot integrity, side-effect / pre-sweep gates). Offline + stdlib-only; it also prints
an INFO line on the reviewer channel (local CLI / API key) without failing on it:
```
python3 skills/autosound-tuning/scripts/smoke_test.py     # exit 0 = healthy · SMOKE_VERBOSE=1 for tracebacks
```

## Which method is actually running here (one command)

Several shapes can be present **at the same time**, and that is normal: a plugin
install pinned by sha, a developer symlink into a clone that moves with `main`, a per-project
`.claude/skills/autosound-tuning` a run keeps detached at a tag so its numbers stay reproducible.
Nothing is wrong with having several. What goes wrong is that none of them says which it is — so a
project's scripts can compute on one version while the session advises from another, both working,
neither complaining. (Measured on the author's machine 2026-08-29: scripts on `v3.0.33`, session on
`3.0.36`, working tree on `3.0.37`.)

```
python3 rew_tool/deployment.py                 # this copy and the personal ~/.claude one
python3 rew_tool/deployment.py <project-dir>   # ... plus that project's own pin
```

It prints every deployment it can reach with its version, its checkout and whether that checkout is
held still (`DETACHED`) or moving (a branch name), and it **refuses** — exit 3 — when two of them
are different commits. A copy that cannot say which checkout it is exits 4 instead: unknown is not
agreement.

It does not tell you which one to prefer, on purpose. Which candidate wins is decided by the loader
doing the asking — Claude Code's skill loader and a script's `sys.path` are two mechanisms with two
rules — so the fact worth reporting is the disagreement, which is true whichever one wins.

### Two channels on one machine

`install.sh --channel beta` (`install.ps1 -Channel beta`) keeps **two** checkouts, and a terminal
never loads the second one (autosound-hub #145):

| copy | where | on | loaded by |
|---|---|---|---|
| the terminal's | `~/.claude/skills/.autosound-tuning-src`, linked from `~/.claude/skills/autosound-tuning` | the newest release, `v3.*` | Claude Code in a terminal |
| the beta channel's | `~/.claude/skills/.autosound-tuning-beta` — **no link** | the newest of `v3.*` and `beta-v3.*` | a front-end that asks for beta, by path |

`python3 scripts/installer-consistency.py --print SKILL_BETA_SRC` prints the second path (relative
to the home folder), so a consumer reads it instead of copying it.

A front-end that runs the beta copy does two things, and the method checks the second:

1. loads the skill from `~/.claude/skills/.autosound-tuning-beta/skills/autosound-tuning` (TCC: as
   its plugin directory);
2. sets `AUTOSOUND_SKILL_ROOT` to that same folder in the session's environment. `deployment.py`
   then requires the copy it runs from and the project's link to BE that checkout, and reports a
   personal copy at another commit as the terminal's channel instead of refusing. Without the
   variable the personal copy is a disagreement as before — a beta session that forgets it is
   refused at step 0, not silently mixed.

Still the front-end's to get right:

- **The project's own link.** `<project>/.claude/skills/autosound-tuning` is read by a terminal
  session in that project too. Pointed at the beta copy, it hands the candidate to the terminal.
- **Moving the beta copy** is the same two commands as the terminal's: `git -C <copy> fetch --depth 1
  origin <tag>`, then `git -C <copy> checkout FETCH_HEAD`.
- **Python packages** come from the terminal copy's `requirements.txt`. A candidate that adds one
  needs `python3 -m pip install -r <copy>/skills/autosound-tuning/requirements.txt`.

## Troubleshooting

- **Antigravity / agy sandbox — state snapshots vanish.** Some agent environments restrict certain file writes to the session's own directory (observed on Antigravity: an artifact-write outside `…/brain/<session>/` was refused). If versioned snapshots don't land where you expect, point `AUTOSOUND_STATE_ROOT` inside the project and verify it's writable **from within the session**: `python3 rew_tool/state/state.py selftest` (must print `selftest OK`); confirm the root actually fills after the first `apply.py propose`.
- **Reviewer CLI inside an agent session.** A reviewer CLI (agy/claude) started from *inside* another agent session deadlocks chronically (agent-inside-agent; observed ~15/20 field sessions), so `autosound_ai.py` does not start one there: the call is refused (exit 4) with the next rung — run it from a **separate terminal**, give the reviewer a key (the direct API works inside a session), or take the clipboard. Outside a session a CLI that does not answer is stopped after `AUTOSOUND_CLI_TIMEOUT` (default 300 s). See [setup-critic-channel.md](references/tooling/setup-critic-channel.md) §3.
- **A tool/file looks MISSING, or the skill seems to contradict its own docs — symlink-blind search (Lesson 2026-07-08).** The dev/author install is a **symlink** (`~/.claude/skills/autosound-tuning` → the repo), and a plain `find` does **not** traverse a symlink on macOS → a false "this file/tool doesn't exist". **Real incident:** `rew_tool/target_bands.py` was declared a "gap" while it existed and was documented as the solution; the whole session then went the wrong way on that false premise. **Fix:** before concluding anything is missing or broken, re-check with `find -L` / `ls`, or resolve the install to the real checkout the symlink points at — `readlink -f ~/.claude/skills/autosound-tuning` (`Get-Item … | Select Target` on Windows) — and search THERE, never a symlink-blind `find`; when the code contradicts the docs, read the actual source.
  - ⚠️ **Why the damage is systemic, not one file.** A symlink-blind search silently hides *arbitrary* skill content across BOTH tiers — e.g. the always-loaded **sample-rate** guardrail in `SKILL.md` (DSP-agnostic: samples at the wrong native rate ruin the alignment) *and* the equipment-specific value it points to (`knowledge/dsp/helix-dsp-ultra-s.md`: Helix native rate = 96 kHz) — none of which the user ever saw flagged. So the moment you notice a symlink-blind read, treat your whole view of the skill as **partial**: re-resolve the install, re-load from the canonical path, and treat conclusions reached earlier in the session as suspect until re-checked — don't just patch the one visible symptom.
  - **When it's a real discrepancy, the operational rule (ASK the Arbiter → fix/inbox or wait/file-issue) lives in `SKILL.md` guardrails.** The issue-triage / auto-answer side (`scripts/issue_triage.py`) is intentionally still WIP — asking + filing + an honest "wait" is the part that must always happen.

For details on distribution, versions, and how experience flows back, see [feedback-loop.md](references/core/feedback-loop.md).
