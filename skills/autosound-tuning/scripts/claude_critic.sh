#!/usr/bin/env bash
# claude_critic.sh — Claude-based reviewer channel for autosound tuning.
#
# Sends a Generator package to Claude acting as the REVIEWER (Critic-Advisor: one role,
# one model — claude_advisor.sh is only a second door to this script). The prompt is assembled
# by _reviewer_prompt.sh: the role, the Data Contract, the PROJECT's autosound_context, the
# reviewer memory if the project has one, then the package.
#
# Usage:
#   claude_critic.sh <package.md> [trace.csv]
#
# Args:
#   package.md   Generator package (the §3 format from the contract).
#   trace.csv    Optional decimated trace attached for point-checking the data.
#
set -euo pipefail
SCRIPT_NAME="claude_critic"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claude_common.sh"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_reviewer_prompt.sh"

# Preflight: `claude_critic.sh --doctor` diagnoses CLI/context + runs a live smoke.
if [[ "${1:-}" == "--doctor" ]]; then claude_doctor && exit 0 || exit 1; fi

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: claude_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
claude_preflight

PRIMARY_MODEL="${CLAUDE_CRITIC_MODEL:-}"

PROMPT_FILE="$(mktemp -t autosound_critic.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

reviewer_retired_notice
reviewer_prompt "$PKG" "$TRACE" > "$PROMPT_FILE"

claude_run "$PRIMARY_MODEL" "$PROMPT_FILE" "critic"
