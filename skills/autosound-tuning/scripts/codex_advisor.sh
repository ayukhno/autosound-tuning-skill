#!/usr/bin/env bash
# codex_advisor.sh — a second door to codex_critic.sh, not a second role.
#
# The Critic and the Advisor are ONE reviewer with one model (the Arbiter's ruling, 2026-09-11;
# hub SKL-032, skill#27). This file stays so that a runbook, an alias or a habit that calls it
# keeps working; everything — the prompt, the memory file, the model, --doctor — is the critic's.
echo ">> codex_advisor.sh → codex_critic.sh: the Advisor is the same reviewer now (one role, one model)" >&2
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/codex_critic.sh" "$@"
