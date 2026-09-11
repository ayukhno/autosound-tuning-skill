#!/usr/bin/env bash
# _reviewer_prompt.sh — the reviewer's prompt, assembled ONE way for every vendor's wrapper
# ({gemini,claude,codex}_critic.sh). SOURCED, not executed. `autosound_ai.py` assembles the same
# blocks from the same `reviewer-prompt.txt`.
#
# One role, not two (the Arbiter's ruling, 2026-09-11; hub SKL-032, skill#27). The Critic and the
# Advisor used to be two wrappers with two prompts and two model slots, and that split cost a day:
# TCC reported "the critic does not answer", every fix went into the critic, and the one failing
# was the advisor — the critic had answered all along. The 09.09 review had kept them apart for a
# real reason: opposite memory contracts (the critic read nothing, the advisor read a memory file).
# Resolved here rather than lost: the memory file is read whenever it exists. It lives on disk like
# the context does, so "the reviewer re-reads everything from disk" still holds, and the file's own
# discipline (CONFIRMED vs OPEN, review-loop.md) is what keeps it from pre-deciding a question.

REVIEWER_PROMPT_HEAD="$(dirname "${BASH_SOURCE[0]}")/reviewer-prompt.txt"
# The file keeps its old name: projects already have one, and renaming it would drop what is in it.
ADVISOR_MEMORY="${ADVISOR_MEMORY:-${PROJECT_MIRROR:-$PWD/rew_analitic}/depth-advisor-memory.md}"

# The model variables of the second slot are no longer read. Said once, on stderr, only when one
# is actually set — a value sitting in an old .critic-env would otherwise look like it still steers.
reviewer_retired_notice() {
  local v
  for v in GEMINI_ADVISOR_MODEL AUTOSOUND_ADVISOR_MODEL CLAUDE_ADVISOR_MODEL CODEX_ADVISOR_MODEL; do
    [[ -n "${!v:-}" ]] && echo ">> note: $v='${!v}' is no longer read — the Critic and the Advisor are one reviewer with one model; set ${v/ADVISOR/CRITIC} instead" >&2
  done
  return 0
}

# reviewer_prompt <package.md> [trace.csv] — the whole prompt on stdout.
reviewer_prompt() {
  local pkg="$1" trace="${2:-}"
  cat "$REVIEWER_PROMPT_HEAD"
  printf '\n====== DATA CONTRACT (the protocol) ======\n'
  cat "$CONTRACT"
  printf '\n\n====== AUTOSOUND CONTEXT (the single source of truth) ======\n'
  cat "$CONTEXT"
  if [[ -f "$ADVISOR_MEMORY" ]]; then
    printf '\n\n====== REVIEWER MEMORY (confirmed facts and open questions from earlier rounds) ======\n'
    cat "$ADVISOR_MEMORY"
  fi
  printf '\n\n====== GENERATOR PACKAGE (review this) ======\n'
  cat "$pkg"
  if [[ -n "$trace" && -f "$trace" ]]; then
    printf '\n\n====== ATTACHED TRACE (decimated, to verify the reading of the data) ======\n'
    cat "$trace"
  fi
}
