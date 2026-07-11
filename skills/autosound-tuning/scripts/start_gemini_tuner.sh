#!/usr/bin/env bash
# start_gemini_tuner.sh — one-command solo-Gemini (mode C) session launcher.
#
# Solves two real papercuts of running Gemini as the DRIVER:
#   1. "Simple start": no manual repo-spelunking + a hand-typed bootstrap prompt —
#      this script assembles everything and (for the gemini CLI) just launches.
#   2. "Auto-hydration": Gemini forgetting to re-read state is the #1 solo failure
#      mode. gemini-cli auto-loads a GEMINI.md from the CWD — so we WRITE the
#      operating instructions + the CURRENT on-disk state into GEMINI.md at start.
#      Re-run with --refresh after /clear or after applying a DSP change.
#
# Usage (from the PROJECT directory — the car you're tuning):
#   start_gemini_tuner.sh            # hydrate GEMINI.md + launch the CLI
#   start_gemini_tuner.sh --refresh  # only regenerate GEMINI.md (no launch)
#
# Config: same env/.critic-env as the reviewer wrappers (GEMINI_BIN, PROJECT_MIRROR).
set -euo pipefail
SCRIPT_NAME="start_gemini_tuner"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_gemini_common.sh"

SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"   # …/skills/autosound-tuning
OUT="$PWD/GEMINI.md"
MARKER="<!-- autosound-tuning auto-hydrated context — regenerate via scripts/start_gemini_tuner.sh -->"

# Never clobber a hand-written GEMINI.md.
if [[ -f "$OUT" ]] && ! grep -qF "$MARKER" "$OUT"; then
  cp "$OUT" "$OUT.bak"
  echo ">> existing hand-written GEMINI.md backed up to GEMINI.md.bak" >&2
fi

# --- gather live state (best-effort: a fresh project simply has less) --------
_first_existing() { local f; for f in "$@"; do [[ -f "$f" ]] && { echo "$f"; return; }; done; }
STATE_FILE="$(_first_existing "$PROJECT_MIRROR"/dsp-state-current* "$PWD"/dsp-state-current* || true)"
CHANGELOG="$(_first_existing "$PROJECT_MIRROR"/tuning-changelog* "$PWD"/tuning-changelog* || true)"

{
  echo "$MARKER"
  echo "# Autosound tuning — session operating context (auto-generated $(date '+%Y-%m-%d %H:%M'))"
  echo
  echo "You are the **solo DRIVER (mode C)** of a car-audio tuning session."
  echo "1. Read and follow as your operating instructions: \`$SKILL_ROOT/SKILL.md\`"
  echo "2. Solo driver ⇒ ALSO load: \`$SKILL_ROOT/references/core/driver-discipline.md\`"
  echo "   (pull-based control; self-critique of round packages ONLY via a stateless"
  echo "   \`scripts/gemini_critic.sh <package.md>\` call — never in-context)."
  echo "3. Load only the ACTIVE phase file (+ next) per the Phase Sliding Window."
  echo
  if [[ -n "${CHANGELOG:-}" ]]; then
    echo "## ▶️ CONTINUE (top of $(basename "$CHANGELOG") at session start)"
    echo '```'
    awk '/▶️|CONTINUE/{f=1} f{print; if(++n>=30) exit}' "$CHANGELOG"
    echo '```'
    echo
  fi
  if [[ -n "${STATE_FILE:-}" ]]; then
    echo "## Current DSP state snapshot ($(basename "$STATE_FILE") — re-read from disk before ANY change; this copy ages)"
    echo '```'
    cat "$STATE_FILE"
    echo '```'
    echo
  fi
  [[ -z "${STATE_FILE:-}${CHANGELOG:-}" ]] && \
    echo "_No project state found yet (fresh project?) — start with Phase -1 intake._"
  echo
  echo "> After the Arbiter applies a DSP change or after /clear: re-run"
  echo "> \`$SCRIPT_DIR/start_gemini_tuner.sh --refresh\` so this file matches disk."
} > "$OUT"
echo ">> hydrated: $OUT $([[ -n "${STATE_FILE:-}" ]] && echo "(state: $(basename "$STATE_FILE"))" || echo "(no state yet)")" >&2

[[ "${1:-}" == "--refresh" ]] && exit 0

# --- launch -------------------------------------------------------------------
if [[ -z "$GEMINI_BIN" ]]; then
  die "no Gemini CLI on PATH — npm i -g @google/gemini-cli, then re-run (GEMINI.md is already hydrated)"
fi
case "$GEMINI_FLAVOR" in
  gemini)
    echo ">> launching $GEMINI_BIN (it auto-loads ./GEMINI.md)" >&2
    exec "$GEMINI_BIN" $GEMINI_EXTRA_ARGS ;;
  *)
    echo ">> $GEMINI_FLAVOR does not auto-load GEMINI.md — start it yourself and paste:" >&2
    echo "   Read $PWD/GEMINI.md and follow it as your operating instructions for this session." ;;
esac
