#!/usr/bin/env bash
# _codex_common.sh — shared plumbing for the Codex reviewer channel
# (codex_critic.sh + codex_advisor.sh). This file is SOURCED, not executed.

# --- optional per-machine / per-project config -----------------------------
for _env in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do
  if [[ -f "$_env" ]]; then set -a; . "$_env"; set +a; break; fi
done

PROJECT_MIRROR="${PROJECT_MIRROR:-$PWD/rew_analitic}"
AUTOSOUND_DIR="${AUTOSOUND_DIR:-}"   # OPTIONAL cross-project canon dir; unset by default

CONTRACT="$PROJECT_MIRROR/data-contract-template.md"
[[ -f "$CONTRACT" ]] || CONTRACT="$AUTOSOUND_DIR/data-contract-template.md"
CONTEXT="$PROJECT_MIRROR/autosound_context.md"
[[ -f "$CONTEXT" ]] || CONTEXT="$AUTOSOUND_DIR/autosound_context.md"

if [[ -d "$AUTOSOUND_DIR" ]]; then AUDIT="$AUTOSOUND_DIR/audit-trail.md"
else AUDIT="$PROJECT_MIRROR/audit-trail.md"; fi

CODEX_BIN="${CODEX_BIN:-codex}"

die() { echo "${SCRIPT_NAME:-codex}: $*" >&2; exit 1; }

codex_preflight() {
  [[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT"
  [[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT"
  command -v "$CODEX_BIN" >/dev/null 2>&1 || die "no Codex CLI on PATH — install/link Codex (codex)"
}

_run_codex() {
  local prompt_file="$1" model="${2:-}"
  local out_f; out_f="$(mktemp -t codex_out.XXXXXX)"
  
  if [[ -n "$model" ]]; then
    # Run codex non-interactively with model, save clean output to temp file
    "$CODEX_BIN" exec -m "$model" --ephemeral --output-last-message "$out_f" - < "$prompt_file" >/dev/null 2>&1
  else
    # Run codex non-interactively with default model, save clean output to temp file
    "$CODEX_BIN" exec --ephemeral --output-last-message "$out_f" - < "$prompt_file" >/dev/null 2>&1
  fi
  
  cat "$out_f"
  rm -f "$out_f"
}

codex_run() {
  local model="${1:-}" pf="$2" role="$3" out
  local display_model="${model:-default}"
  echo ">> ${role}: codex ($display_model)" >&2
  out="$(_run_codex "$pf" "$model")"
  printf '%s\n' "$out"
  printf '\n— [%s: codex (%s)]\n' "$role" "$display_model"
  { printf '%s | %s=codex(%s) | package=%s%s\n' "$(date '+%Y-%m-%d %H:%M')" \
      "$role" "$display_model" "$(basename "${PKG:-?}")" "${TRACE:+ | trace=$(basename "$TRACE")}"; } \
    >> "$AUDIT" 2>/dev/null || true
}

codex_doctor() {
  local ok=1 bin
  echo "== Codex reviewer channel — doctor =="
  bin="$(command -v "$CODEX_BIN" 2>/dev/null || echo "$CODEX_BIN")"
  if [[ -z "$bin" ]]; then
    echo "✗ CLI: none on PATH. Fix: ln -s /Applications/Codex.app/Contents/Resources/codex ~/.local/bin/codex"; ok=0
  else
    echo "✓ CLI: $CODEX_BIN → $bin"
  fi
  [[ -f "$CONTRACT" ]] && echo "✓ contract: $CONTRACT" || { echo "✗ contract: $CONTRACT not found"; ok=0; }
  [[ -f "$CONTEXT"  ]] && echo "✓ context:  $CONTEXT"  || { echo "✗ context:  $CONTEXT not found"; ok=0; }
  
  if command -v "$CODEX_BIN" >/dev/null 2>&1; then
    echo "— live smoke (1 line) —"
    local sf out; sf="$(mktemp)"; printf 'reply with exactly: channel works' > "$sf"
    out="$(_run_codex "$sf")"; rm -f "$sf"
    if [[ -z "${out//[[:space:]]/}" ]]; then
      echo "✗ smoke: EMPTY reply (is Codex authenticated? Run 'codex doctor')"
      ok=0
    else
      echo "✓ smoke: $(printf '%s' "$out" | head -1)"
    fi
  fi
  echo "== $([[ $ok = 1 ]] && echo 'ALL GOOD ✓' || echo 'ISSUES ABOVE ✗ — fix and re-run --doctor') =="
  [[ $ok = 1 ]]
}
