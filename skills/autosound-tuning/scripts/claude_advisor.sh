#!/usr/bin/env bash
# claude_advisor.sh — the ADVISOR task on the one reviewer channel (claude_critic.sh).
#
# The Critic and the Advisor are one channel with one model (the Arbiter's ruling, 2026-09-11;
# hub SKL-032, skill#27); what differs is the task — check a proposal vs search for a solution to
# an open question — and that is only the TASK block of the prompt (reviewer-task-advisor.txt).
# Everything else — the wrapper, the model, the memory file, --doctor — is the one channel's.
AUTOSOUND_REVIEW_TASK=advisor exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/claude_critic.sh" "$@"
