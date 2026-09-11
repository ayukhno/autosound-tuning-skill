#!/usr/bin/env bash
# codex_critic.sh — Codex-based reviewer channel for autosound tuning.
#
# Sends a Generator package to Codex acting as the REVIEWER (Critic-Advisor: one role,
# one model — codex_advisor.sh is only a second door to this script). The prompt is assembled
# by _reviewer_prompt.sh: the role, the Data Contract, the PROJECT's autosound_context, the
# reviewer memory if the project has one, then the package.
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
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_reviewer_prompt.sh"

# Preflight: `codex_critic.sh --doctor` diagnoses CLI/context + runs a live smoke.
if [[ "${1:-}" == "--doctor" ]]; then codex_doctor && exit 0 || exit 1; fi

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: codex_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
codex_preflight

PRIMARY_MODEL="${CODEX_CRITIC_MODEL:-}"

PROMPT_FILE="$(mktemp -t autosound_critic.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

reviewer_retired_notice
reviewer_prompt "$PKG" "$TRACE" > "$PROMPT_FILE"

codex_run "$PRIMARY_MODEL" "$PROMPT_FILE" "critic"
