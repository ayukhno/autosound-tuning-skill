#!/usr/bin/env bash
# gemini_advisor.sh — Claude↔Gemini "Advisor-Expert" channel (depth/staging work).
#
# Variant of gemini_critic.sh where Gemini plays ADVISOR-EXPERT,
# not pure Challenger: a collaborative peer who brings car-audio staging expertise
# + community best-practice, names acoustic risks AND proposes concrete solutions,
# builds on the Generator's analysis, and may pose questions back to the Arbiter.
#
# Adds SESSION MEMORY: a persistent file is injected each call so Gemini accumulates
# knowledge/decisions across rounds and sessions. Append to it after each round.
#
# Usage:
#   gemini_advisor.sh <package.md> [trace.csv]
#
# Config (see gemini_critic.sh header + references/setup-critic-channel.md):
#   GEMINI_ADVISOR_MODEL  primary model (default per CLI)
#   ADVISOR_MEMORY        session-memory file (default: $PROJECT_MIRROR/depth-advisor-memory.md)
#   + GEMINI_BIN / GEMINI_FALLBACK_MODEL / GEMINI_EXTRA_ARGS / PROJECT_MIRROR / AUTOSOUND_DIR
set -euo pipefail
SCRIPT_NAME="gemini_advisor"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_gemini_common.sh"

ADVISOR_MEMORY="${ADVISOR_MEMORY:-$PROJECT_MIRROR/depth-advisor-memory.md}"

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: gemini_advisor.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
gemini_preflight

PRIMARY_MODEL="${GEMINI_ADVISOR_MODEL:-$(gemini_default_model)}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-$(gemini_default_model)}"

PROMPT_FILE="$(mktemp -t autosound_advisor.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  cat <<'HDR'
SYSTEM ROLE — YOU ARE THE ADVISOR-EXPERT in a collaborative car-audio staging effort (width / depth / tonality).
The car / DSP / work stage (front-only or the full system) is in the AUTOSOUND CONTEXT block below. Rely ONLY on it: don't assume a different car, a different DSP, or driver geometry from memory.
This is COLLABORATIVE work between colleagues, not a contest. Claude = Orchestrator/Generator, you = Advisor-Expert, the user = Arbiter.

Your role (broader than the Critic's):
  • Bring DEEP staging/depth expertise + community best-practice (DIYMA, bestcaraudio, EMMA judging).
  • Don't only find risks — PROPOSE concrete solutions and an order of steps.
  • Build ON the Generator's analysis (extend/refine it), don't only refute.
  • Honestly name both the risk and where the PHYSICAL CEILING of driver placement is — but take its limits from THIS car's CONTEXT/measurements (mid-tweeter placement/coplanarity, distances), not from memory of another install.
  • Objections/advice — FALSIFIABLE (testable by ear/measurement), not "a vibe".
  • Think in cabin physics + psychoacoustics (precedence/Haas, ILD/ITD/IPD, glass reflections), not the math of ideal filters.
  • Remember: an all-pass is flat in FR — an FR change comes only through source SUMMATION; an all-pass does NOT fill a magnitude null.
  • If you lack data for advice or need an Arbiter decision — FORMULATE a question for the user (Claude will relay it).

YOU HAVE SESSION MEMORY (the "ADVISOR MEMORY" block below) — accumulated decisions/data from previous rounds. Rely on it, don't repeat what's already agreed, build on it.

Respond in the project's language (that of the AUTOSOUND CONTEXT below), structured: (1) assessment of the proposal, (2) risks/caveats (falsifiable), (3) concrete advice + order, (4) questions for the Arbiter if any.

====== DATA CONTRACT (the protocol, package format §3) ======
HDR
  cat "$CONTRACT"
  printf '\n\n====== AUTOSOUND CONTEXT (the single source of truth) ======\n'
  cat "$CONTEXT"
  if [[ -f "$ADVISOR_MEMORY" ]]; then
    printf '\n\n====== ADVISOR MEMORY (accumulated decisions/data from depth sessions) ======\n'
    cat "$ADVISOR_MEMORY"
  fi
  printf '\n\n====== GENERATOR PACKAGE (Claude) — discuss as the Advisor ======\n'
  cat "$PKG"
  if [[ -n "$TRACE" && -f "$TRACE" ]]; then
    printf '\n\n====== ATTACHED TRACE (decimated) ======\n'
    cat "$TRACE"
  fi
} > "$PROMPT_FILE"

gemini_run "$PRIMARY_MODEL" "$FALLBACK_MODEL" "$PROMPT_FILE" "advisor"
