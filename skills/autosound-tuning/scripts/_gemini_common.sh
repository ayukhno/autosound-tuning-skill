#!/usr/bin/env bash
# _gemini_common.sh — shared plumbing for the Gemini reviewer channel
# (gemini_critic.sh + gemini_advisor.sh). This file is SOURCED, not executed.
#
# It does three things both wrappers need identically:
#   1. locate the Contract + the PROJECT's Context (project-local FIRST)
#   2. detect the Gemini CLI (agy / @google/gemini-cli) + its model & flags
#   3. run a prompt with primary→fallback model retry and log the audit trail
#
# Why project-local first: the skill is installed GLOBALLY and shared across
# cars, so the only reliable "which project am I tuning" signal is the directory
# you launch Claude from (CWD). A stale iCloud/_AI copy from ANOTHER car must
# NOT hijack the Critic — that silently leaks the wrong vehicle's context (the
# real "Critic cited sessions that never happened" bug). Override any path via
# env or a .critic-env file — see references/setup-critic-channel.md.

# --- optional per-machine / per-project config -----------------------------
# Sourced if present so a user pins CLI/model/paths ONCE, not on every call.
for _env in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do
  if [[ -f "$_env" ]]; then set -a; . "$_env"; set +a; break; fi
done

# --- where the docs live ----------------------------------------------------
# PROJECT_MIRROR = the project you're tuning RIGHT NOW (= CWD/rew_analitic).
# AUTOSOUND_DIR  = the author's iCloud single-source-of-truth (audit-log home;
#                  used for Context/Contract ONLY as a last-resort fallback).
PROJECT_MIRROR="${PROJECT_MIRROR:-$PWD/rew_analitic}"
AUTOSOUND_DIR="${AUTOSOUND_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound}"

CONTRACT="$PROJECT_MIRROR/data-contract-template.md"
[[ -f "$CONTRACT" ]] || CONTRACT="$AUTOSOUND_DIR/data-contract-template.md"
CONTEXT="$PROJECT_MIRROR/autosound_context.md"
[[ -f "$CONTEXT" ]] || CONTEXT="$AUTOSOUND_DIR/autosound_context.md"
# Audit: append to iCloud canon if that dir exists, else keep it project-local.
if [[ -d "$AUTOSOUND_DIR" ]]; then AUDIT="$AUTOSOUND_DIR/audit-trail.md"
else AUDIT="$PROJECT_MIRROR/audit-trail.md"; fi

# --- Gemini CLI detection ---------------------------------------------------
# Zero-config for both rigs: the author's `agy` (Antigravity) wins when present;
# a fresh user who `npm i -g @google/gemini-cli` gets `gemini`. Force either by
# setting GEMINI_BIN (e.g. in .critic-env). DON'T symlink agy→gemini — just let
# detection pick gemini; that keeps the model ids + flags correct for each CLI.
if [[ -z "${GEMINI_BIN:-}" ]]; then
  if command -v agy >/dev/null 2>&1; then GEMINI_BIN=agy
  elif command -v gemini >/dev/null 2>&1; then GEMINI_BIN=gemini
  else GEMINI_BIN=""; fi
fi
GEMINI_FLAVOR="$(basename "${GEMINI_BIN:-none}")"

# Per-CLI extra args: @google/gemini-cli refuses headless runs in an "untrusted"
# directory unless --skip-trust is passed; agy has no such flag.
if [[ -z "${GEMINI_EXTRA_ARGS:-}" ]]; then
  case "$GEMINI_FLAVOR" in
    gemini) GEMINI_EXTRA_ARGS="--skip-trust" ;;
    *)      GEMINI_EXTRA_ARGS="" ;;
  esac
fi

# Per-CLI default model. agy uses human-readable labels (`agy models`);
# @google/gemini-cli uses API ids (`gemini models` / the docs). Flash is the
# default (free + snappy + strong critic); opt into Pro per call via the
# role model env (GEMINI_CRITIC_MODEL / GEMINI_ADVISOR_MODEL).
gemini_default_model() {
  case "$GEMINI_FLAVOR" in
    gemini) echo "gemini-2.5-flash" ;;
    *)      echo "Gemini 3.5 Flash (Medium)" ;;
  esac
}

die() { echo "${SCRIPT_NAME:-gemini}: $*" >&2; exit 1; }

gemini_preflight() {
  [[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT
  → run the intake to create rew_analitic/data-contract-template.md, or set PROJECT_MIRROR"
  [[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT
  → copy your project's autosound_context.md into rew_analitic/, or set PROJECT_MIRROR"
  [[ -n "$GEMINI_BIN" ]] || die "no Gemini CLI on PATH — install the official one:
  npm i -g @google/gemini-cli   (then 'gemini'; see references/setup-critic-channel.md)"
}

# _run_model <model> <prompt_file> — prints raw Gemini output, strips CLI noise.
# Runs from the prompt's dir so a stray project GEMINI.md isn't auto-loaded
# (the wrapper already injects all context explicitly).
_run_model() {
  ( cd "$(dirname "$2")" && "$GEMINI_BIN" --model "$1" $GEMINI_EXTRA_ARGS -p "$(cat "$2")" ) 2>&1 \
    | grep -viE '^(Ripgrep is not available|\[STARTUP\]|update_topic\()'
}

_is_quota_error() {
  # Covers API-key (quota/429) + OAuth/Code-Assist (capacity/exhausted) limits,
  # plus bad-model 404s, so we still fall back to a working model.
  grep -qiE 'quota|capacity|exhausted|RESOURCE_EXHAUSTED|TerminalQuotaError|ModelNotFound|not found|429' <<<"$1"
}

# gemini_run <primary> <fallback> <prompt_file> <role_label>
# Runs primary, falls back on quota/unavailable, prints output + which model
# spoke, and appends a one-line audit record (best-effort).
gemini_run() {
  local primary="$1" fallback="$2" pf="$3" role="$4" out used
  echo ">> ${role}: $primary  [cli=$GEMINI_FLAVOR]" >&2
  out="$(_run_model "$primary" "$pf" || true)"; used="$primary"
  if _is_quota_error "$out"; then
    echo ">> $primary unavailable/exhausted → falling back to $fallback" >&2
    out="$(_run_model "$fallback" "$pf" || true)"; used="$fallback (fallback)"
  fi
  if [[ -z "${out//[[:space:]]/}" ]]; then
    echo ">> WARNING: empty reply from $GEMINI_FLAVOR ($used) — the CLI may be broken/unauthed (a silent break). Smoke-test it; see references/setup-critic-channel.md (e.g. pin GEMINI_BIN=gemini in .critic-env)." >&2
  fi
  printf '%s\n' "$out"
  printf '\n— [%s: %s]\n' "$role" "$used"
  { printf '%s | %s=%s | package=%s%s\n' "$(date '+%Y-%m-%d %H:%M')" \
      "$role" "$used" "$(basename "${PKG:-?}")" "${TRACE:+ | trace=$(basename "$TRACE")}"; } \
    >> "$AUDIT" 2>/dev/null || true
}
