#!/usr/bin/env bash
# sync.sh — pull the latest skill files from the development copy into this repo.
#
# The skill is developed in-place inside a tuning project (its daily home);
# this repo is the clean PUBLICATION of it. Run this to refresh the repo from
# the source, review the diff, then commit/push.
#
# Source override:  SKILL_SRC=/path/to/.claude/skills ./sync.sh
# Default source:   ~/Documents/car-audio/.claude/skills
#
# What it copies:   skills/autosound-tuning + skills/review-loop
# What it excludes:  .DS_Store, *-workspace (eval scratch), and (via .gitignore)
#                    any project data that must never be published.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SKILL_SRC:-$HOME/Documents/car-audio/.claude/skills}"

[[ -d "$SRC/autosound-tuning" ]] || { echo "source not found: $SRC/autosound-tuning" >&2; exit 1; }

echo "Syncing from: $SRC"
rsync -a --delete --exclude='.DS_Store' --exclude='*-workspace' \
  "$SRC/autosound-tuning" "$REPO/skills/"
rsync -a --delete --exclude='.DS_Store' \
  "$SRC/review-loop" "$REPO/skills/"

echo
echo "Done. Review and commit:"
echo "  cd \"$REPO\" && git add -A && git status"
echo "  git diff --cached    # check NOTHING project-specific leaked"
echo "  git commit -m 'sync: <what changed>' && git push"
