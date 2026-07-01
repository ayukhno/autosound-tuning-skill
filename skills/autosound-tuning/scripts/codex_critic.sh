#!/usr/bin/env bash
# codex_critic.sh — Codex-based "Critic" channel for autosound tuning.
#
# Sends a Generator package to Codex acting as the CRITIC (Challenger), per
# data-contract-template.md. Injects the Data Contract + the PROJECT's
# autosound_context as system framing so Codex answers grounded + in format.
#
# Usage:
#   codex_critic.sh <package.md> [trace.csv]
#
# Args:
#   package.md   Generator package (the §3 format from the contract).
#   trace.csv    Optional decimated trace attached for point-checking the data.
#
set -euo pipefail
SCRIPT_NAME="codex_critic"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_codex_common.sh"

# Preflight: `codex_critic.sh --doctor` diagnoses CLI/context + runs a live smoke.
if [[ "${1:-}" == "--doctor" ]]; then codex_doctor && exit 0 || exit 1; fi

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: codex_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
codex_preflight

PRIMARY_MODEL="${CODEX_CRITIC_MODEL:-}"

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

codex_run "$PRIMARY_MODEL" "$PROMPT_FILE" "critic"
