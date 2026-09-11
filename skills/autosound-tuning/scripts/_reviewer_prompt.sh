#!/usr/bin/env bash
# _reviewer_prompt.sh — the reviewer's prompt, assembled ONE way for every vendor's wrapper
# ({gemini,claude,codex}_critic.sh). SOURCED, not executed. `autosound_ai.py` assembles the same
# blocks from the same files.
#
# One channel, one model, three TASKS (the Arbiter's ruling, 2026-09-11; hub SKL-032, skill#27).
# Layers, and which task gets which:
#   assets/interaction-contract.md   every task — how the Generator and the Reviewer talk; NOT tuning
#   reviewer-tuning.txt              critic, advisor — the tuning rules; the regulated part
#   reviewer-task-<task>.txt         the task itself — the only thing the tasks do not share
#   DATA CONTRACT + AUTOSOUND CONTEXT critic, advisor — required (the wrapper refuses without them)
#   REVIEWER MEMORY                  critic, advisor — whenever the project has one
# `ask` is a plain question — a translation, a letter's wording — so it needs no tuning contract and
# works in a folder that has not been through the intake; a project context, if there is one, rides
# along as background.
#
# Why the Critic and the Advisor are one channel: they used to be two wrappers with two prompts and
# two model slots, and that split cost a day — TCC reported "the critic does not answer", every fix
# went into the critic, and the one failing was the advisor. The 09.09 review had kept them apart
# for a real reason: opposite memory contracts (the critic read nothing, the advisor read a memory
# file). Resolved rather than lost: the memory file is read on every tuning task whenever it exists.
# It lives on disk like the context does, so "the reviewer re-reads everything from disk" still
# holds, and the file's own discipline (CONFIRMED vs OPEN, review-loop.md) keeps it from deciding.

_REVIEWER_DIR="$(dirname "${BASH_SOURCE[0]}")"
REVIEWER_CONTRACT="$_REVIEWER_DIR/../assets/interaction-contract.md"
# Which task this call is. `*_advisor.sh` sets `advisor`; `ask` is set by the caller. Anything else
# is refused rather than guessed, because the task text is what the reviewer answers.
REVIEW_TASK="${AUTOSOUND_REVIEW_TASK:-critic}"
case "$REVIEW_TASK" in critic|advisor|ask) ;; *) echo "reviewer: unknown task '$REVIEW_TASK' (critic|advisor|ask)" >&2; exit 1;; esac
REVIEWER_TASK_FILE="$_REVIEWER_DIR/reviewer-task-$REVIEW_TASK.txt"
# The file keeps its old name: projects already have one, and renaming it would drop what is in it.
ADVISOR_MEMORY="${ADVISOR_MEMORY:-${PROJECT_MIRROR:-$PWD/rew_analitic}/depth-advisor-memory.md}"

# Tuning tasks are regulated: no contract or no context, no call. `ask` is not.
reviewer_is_tuning() { [[ "$REVIEW_TASK" != ask ]]; }

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
  printf '====== INTERACTION CONTRACT (how we work together — every task) ======\n'
  cat "$REVIEWER_CONTRACT"
  printf '\n'
  if reviewer_is_tuning; then
    cat "$_REVIEWER_DIR/reviewer-tuning.txt"
    printf '\n'
  fi
  cat "$REVIEWER_TASK_FILE"
  if reviewer_is_tuning; then
    printf '\n====== DATA CONTRACT (the tuning protocol) ======\n'
    cat "$CONTRACT"
    printf '\n\n====== AUTOSOUND CONTEXT (the single source of truth) ======\n'
    cat "$CONTEXT"
    if [[ -f "$ADVISOR_MEMORY" ]]; then
      printf '\n\n====== REVIEWER MEMORY (confirmed facts and open questions from earlier rounds) ======\n'
      cat "$ADVISOR_MEMORY"
    fi
    printf '\n\n====== GENERATOR PACKAGE (review this) ======\n'
  else
    if [[ -f "$CONTEXT" ]]; then
      printf '\n====== PROJECT CONTEXT (background only) ======\n'
      cat "$CONTEXT"
    fi
    printf "\n\n====== GENERATOR'S QUESTION ======\n"
  fi
  cat "$pkg"
  if [[ -n "$trace" && -f "$trace" ]]; then
    printf '\n\n====== ATTACHED TRACE (decimated, to verify the reading of the data) ======\n'
    cat "$trace"
  fi
}
