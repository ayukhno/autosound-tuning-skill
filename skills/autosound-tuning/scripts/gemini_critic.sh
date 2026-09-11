#!/usr/bin/env bash
# gemini_critic.sh — Claude→Gemini reviewer channel for autosound tuning.
#
# Sends a Generator package to Gemini acting as the REVIEWER (Critic-Advisor: one role, one
# model — gemini_advisor.sh is only a second door to this script). The prompt is assembled by
# _reviewer_prompt.sh: the role, the Data Contract, the PROJECT's autosound_context, the reviewer
# memory if the project has one, then the package.
#
# Usage:
#   gemini_critic.sh <package.md> [trace.csv]
#
# Args:
#   package.md   Generator package (the §3 format from the contract).
#   trace.csv    Optional decimated trace attached for point-checking the data.
#
# Config — set inline, via env, or once in rew_analitic/.critic-env
# (see references/tooling/setup-critic-channel.md). All resolved in _gemini_common.sh:
#   GEMINI_BIN            CLI to use (auto: agy → gemini)
#   GEMINI_CRITIC_MODEL   THE reviewer model — no default: unset, the wrapper prints `agy models` and
#                         stops (exit 3). The name is the Arbiter's; a name kept here ages out.
#   GEMINI_FALLBACK_MODEL fallback when the primary is exhausted — only if you set it
#   GEMINI_EXTRA_ARGS     extra CLI flags (auto: --skip-trust for @google/gemini-cli)
#   PROJECT_MIRROR        project docs dir (default: $PWD/rew_analitic)  ← context/contract live here
#   AUTOSOUND_DIR         OPTIONAL cross-project canon dir (audit/context fallback; unset by default)
set -euo pipefail
SCRIPT_NAME="gemini_critic"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_gemini_common.sh"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_reviewer_prompt.sh"

# Preflight: `gemini_critic.sh --doctor` diagnoses CLI/symlink/quarantine/.critic-env/
# context + runs a live smoke, so setup traps surface in ONE shot.
if [[ "${1:-}" == "--doctor" ]]; then gemini_doctor && exit 0 || exit 1; fi
# Offline: the channel's recognisers and the doctor's closed-path branches, no CLI call.
if [[ "${1:-}" == "--selftest" ]]; then gemini_selfcheck && exit 0 || exit 1; fi

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: gemini_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
gemini_preflight

reviewer_retired_notice
# One model, named by the Arbiter — never by this file. Not named → the CLI's own list, and stop.
PRIMARY_MODEL="$(gemini_require_model)"
# A weaker model is never picked for you: the fallback runs only when YOU named one.
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-}"

PROMPT_FILE="$(mktemp -t autosound_critic.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT
reviewer_prompt "$PKG" "$TRACE" > "$PROMPT_FILE"

gemini_run "$PRIMARY_MODEL" "$FALLBACK_MODEL" "$PROMPT_FILE" "critic"
