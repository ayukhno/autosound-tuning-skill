#!/usr/bin/env bash
# _claude_common.sh — shared plumbing for the Claude reviewer channel
# (claude_critic.sh + claude_advisor.sh). This file is SOURCED, not executed.

# --- optional per-machine / per-project config -----------------------------
for _env in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do
  if [[ -f "$_env" ]]; then set -a; . "$_env"; set +a; break; fi
done

PROJECT_MIRROR="${PROJECT_MIRROR:-$PWD/rew_analitic}"
AUTOSOUND_DIR="${AUTOSOUND_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound}"

CONTRACT="$PROJECT_MIRROR/data-contract-template.md"
[[ -f "$CONTRACT" ]] || CONTRACT="$AUTOSOUND_DIR/data-contract-template.md"
CONTEXT="$PROJECT_MIRROR/autosound_context.md"
[[ -f "$CONTEXT" ]] || CONTEXT="$AUTOSOUND_DIR/autosound_context.md"

if [[ -d "$AUTOSOUND_DIR" ]]; then AUDIT="$AUTOSOUND_DIR/audit-trail.md"
else AUDIT="$PROJECT_MIRROR/audit-trail.md"; fi

CLAUDE_BIN="${CLAUDE_BIN:-claude}"

die() { echo "${SCRIPT_NAME:-claude}: $*" >&2; exit 1; }

claude_preflight() {
  [[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT"
  [[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT"
  command -v "$CLAUDE_BIN" >/dev/null 2>&1 || die "no Claude CLI on PATH — install Claude Code (claude)"
}

_run_claude() {
  local prompt_file="$1" model="${2:-}"
  # We disable all tools via --tools "" to make it non-interactive, print output, and disable session persistence.
  if [[ -n "$model" ]]; then
    "$CLAUDE_BIN" -m "$model" --tools "" --print --no-session-persistence - < "$prompt_file" 2>&1 \
      | grep -viE '^(Ripgrep is not available|\[STARTUP\]|update_topic\()'
  else
    "$CLAUDE_BIN" --tools "" --print --no-session-persistence - < "$prompt_file" 2>&1 \
      | grep -viE '^(Ripgrep is not available|\[STARTUP\]|update_topic\()'
  fi
}

claude_run() {
  local model="${1:-}" pf="$2" role="$3" out
  local display_model="${model:-default}"
  echo ">> ${role}: claude ($display_model)" >&2
  out="$(_run_claude "$pf" "$model")"
  if grep -qiE 'session limit|exhausted|quota|429' <<<"$out"; then
    echo ">> WARNING: Claude returned a session/quota limit error:" >&2
    echo "$out" >&2
  fi
  printf '%s\n' "$out"
  printf '\n— [%s: claude (%s)]\n' "$role" "$display_model"
  { printf '%s | %s=claude(%s) | package=%s%s\n' "$(date '+%Y-%m-%d %H:%M')" \
      "$role" "$display_model" "$(basename "${PKG:-?}")" "${TRACE:+ | trace=$(basename "$TRACE")}"; } \
    >> "$AUDIT" 2>/dev/null || true
}

claude_doctor() {
  local ok=1 bin
  echo "== Claude reviewer channel — doctor =="
  bin="$(command -v "$CLAUDE_BIN" 2>/dev/null || echo "$CLAUDE_BIN")"
  if [[ -z "$bin" ]]; then
    echo "✗ CLI: none on PATH. Fix: npm i -g @anthropic-ai/claude-code"; ok=0
  else
    echo "✓ CLI: $CLAUDE_BIN → $bin"
  fi
  [[ -f "$CONTRACT" ]] && echo "✓ contract: $CONTRACT" || { echo "✗ contract: $CONTRACT not found"; ok=0; }
  [[ -f "$CONTEXT"  ]] && echo "✓ context:  $CONTEXT"  || { echo "✗ context:  $CONTEXT not found"; ok=0; }
  
  if command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
    echo "— live smoke (1 line) —"
    local sf out; sf="$(mktemp)"; printf 'reply with exactly: channel works' > "$sf"
    out="$(_run_claude "$sf")"; rm -f "$sf"
    if grep -qiE 'session limit|exhausted|quota|429' <<<"$out"; then
      echo "✗ smoke: failed with limit/quota: $(printf '%s' "$out" | head -1)"
      ok=0
    elif [[ -z "${out//[[:space:]]/}" ]]; then
      echo "✗ smoke: EMPTY reply"
      ok=0
    else
      echo "✓ smoke: $(printf '%s' "$out" | head -1)"
    fi
  fi
  echo "== $([[ $ok = 1 ]] && echo 'ALL GOOD ✓' || echo 'ISSUES ABOVE ✗ — fix and re-run --doctor') =="
  [[ $ok = 1 ]]
}
