#!/usr/bin/env bash
# gemini_critic.sh — Claude→Gemini "Critic" channel for autosound tuning.
#
# Sends a Generator package to Gemini acting as the CRITIC (Challenger), per
# data-contract-template.md. Injects the Data Contract + the PROJECT's
# autosound_context as system framing so Gemini answers grounded + in format.
#
# Usage:
#   gemini_critic.sh <package.md> [trace.csv]
#
# Args:
#   package.md   Generator package (the §3 format from the contract).
#   trace.csv    Optional decimated trace attached for point-checking the data.
#
# Config — set inline, via env, or once in rew_analitic/.critic-env
# (see references/setup-critic-channel.md). All resolved in _gemini_common.sh:
#   GEMINI_BIN            CLI to use (auto: agy → gemini)
#   GEMINI_CRITIC_MODEL   primary model (default per CLI; agy "Gemini 3.5 Flash (Medium)" · gemini gemini-2.5-flash)
#   GEMINI_FALLBACK_MODEL fallback when the primary is exhausted/unavailable
#   GEMINI_EXTRA_ARGS     extra CLI flags (auto: --skip-trust for @google/gemini-cli)
#   PROJECT_MIRROR        project docs dir (default: $PWD/rew_analitic)  ← context/contract live here
#   AUTOSOUND_DIR         author's iCloud canon (audit-log home; context fallback only)
set -euo pipefail
SCRIPT_NAME="gemini_critic"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_gemini_common.sh"

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: gemini_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
gemini_preflight

PRIMARY_MODEL="${GEMINI_CRITIC_MODEL:-$(gemini_default_model)}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-$(gemini_default_model)}"

PROMPT_FILE="$(mktemp -t autosound_critic.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  cat <<'HDR'
SYSTEM ROLE — YOU ARE THE CRITIC (Challenger) in a two-model car-audio tuning loop.
Task: find acoustic risks and false assumptions in the Generator's PROPOSAL.
The car / DSP / system state is in the AUTOSOUND CONTEXT block below; rely only on it, don't assume a different car.
Rules:
  • DON'T praise. Don't agree by default.
  • Objections must be FALSIFIABLE (testable by ear/measurement), not "a vibe".
  • Think in cabin physics + psychoacoustics, not the math of ideal filters.
  • Remember: an all-pass is flat in FR — any FR change comes through source SUMMATION.
Respond STRICTLY in the "Critic → Generator" format from Contract §4, in the language of the AUTOSOUND CONTEXT below (the project's language).

====== DATA CONTRACT (the protocol) ======
HDR
  cat "$CONTRACT"
  printf '\n\n====== AUTOSOUND CONTEXT (the single source of truth) ======\n'
  cat "$CONTEXT"
  printf '\n\n====== GENERATOR PACKAGE (critique this) ======\n'
  cat "$PKG"
  if [[ -n "$TRACE" && -f "$TRACE" ]]; then
    printf '\n\n====== ATTACHED TRACE (decimated, to verify the reading of the data) ======\n'
    cat "$TRACE"
  fi
} > "$PROMPT_FILE"

gemini_run "$PRIMARY_MODEL" "$FALLBACK_MODEL" "$PROMPT_FILE" "critic"
