#!/usr/bin/env bash
# gemini_critic.sh — Claude→Gemini "Critic" channel for autosound tuning.
#
# Sends a Generator package to Gemini acting as the CRITIC (Challenger),
# per data-contract-template.md. Injects the Data Contract + autosound_context
# as system framing so Gemini answers grounded and in the contract format.
#
# Usage:
#   gemini_critic.sh <package.md> [trace.csv]
#
# Args:
#   package.md   Generator package (the §3 format from the contract).
#   trace.csv    Optional decimated trace attached for point-checking the data.
#
# Env overrides:
#   GEMINI_CRITIC_MODEL   primary model (default: gemini-pro-latest)
#   GEMINI_FALLBACK_MODEL fallback when Pro quota is exhausted (default: gemini-flash-latest)
#   AUTOSOUND_DIR         where the contract/context/audit live
#                         (default: iCloud _AI/Autosound)
#
# Behavior:
#   - Tries the Pro model first. On daily-quota exhaustion it transparently
#     retries on Flash and tags the output so you know which model spoke.
#   - Appends a one-line audit record (timestamp, package, model) to audit-trail.md.
set -euo pipefail

AUTOSOUND_DIR="${AUTOSOUND_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound}"

# Project-local mirror (resilience): contract + context are REQUIRED to run; if
# iCloud hasn't synced (or is offline) a missing file would kill the critic
# channel. Fall back to the copies committed in the repo (rew_analitic/).
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_MIRROR="${PROJECT_MIRROR:-$(cd "$_SCRIPT_DIR/../../../.." && pwd)/rew_analitic}"

CONTRACT="$AUTOSOUND_DIR/data-contract-template.md"
[[ -f "$CONTRACT" ]] || CONTRACT="$PROJECT_MIRROR/data-contract-template.md"
CONTEXT="$AUTOSOUND_DIR/autosound_context.md"
[[ -f "$CONTEXT" ]] || CONTEXT="$PROJECT_MIRROR/autosound_context.md"
AUDIT="$AUTOSOUND_DIR/audit-trail.md"
# Default = Flash: reliable + free on both auth methods, snappy, strong critic.
# Opt into Pro on a hard call:  GEMINI_CRITIC_MODEL=gemini-3-pro-preview ./gemini_critic.sh …
#   (Pro needs free Code-Assist capacity to be available, or billing on the API key.
#    If the chosen Pro model is exhausted, we auto-fall back to FALLBACK_MODEL.)
# Note: with OAuth (Code Assist) auth use concrete model ids — the "-latest"
# aliases (gemini-pro-latest/gemini-flash-latest) are AI-Studio-only and 404 here.
PRIMARY_MODEL="${GEMINI_CRITIC_MODEL:-Gemini 3.5 Flash (Medium)}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-Gemini 3.5 Flash (Medium)}"

die() { echo "gemini_critic: $*" >&2; exit 1; }

PKG="${1:-}"
TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: gemini_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
[[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT"
[[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT"
command -v agy >/dev/null || die "agy CLI not on PATH"

PROMPT_FILE="$(mktemp -t autosound_critic.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  cat <<'HDR'
SYSTEM ROLE — ТИ КРИТИК (Challenger) у дводмодельному циклі налаштування авто-звуку.
Завдання: знайти акустичні ризики й хибні припущення в ПРОПОЗИЦІЇ Генератора.
Правила:
  • НЕ хвали. Не погоджуйся за замовчуванням.
  • Заперечення мають бути ФАЛЬСИФІКОВАНИМИ (перевірюваними на слух/виміром), не «вайбом».
  • Думай фізикою салону + психоакустикою, а не математикою ідеальних фільтрів.
  • Памʼятай: all-pass плоский по АЧХ — будь-яка зміна АЧХ іде через СУМАЦІЮ джерел.
Відповідай СТРОГО у форматі «Критик → Генератор» з §4 Контракту, українською.

====== DATA CONTRACT (регламент) ======
HDR
  cat "$CONTRACT"
  printf '\n\n====== AUTOSOUND CONTEXT (єдина точка правди) ======\n'
  cat "$CONTEXT"
  printf '\n\n====== ПАКЕТ ГЕНЕРАТОРА (це й критикуй) ======\n'
  cat "$PKG"
  if [[ -n "$TRACE" && -f "$TRACE" ]]; then
    printf '\n\n====== ПРИКРІПЛЕНИЙ ТРЕЙС (проріджений, для звірки прочитання даних) ======\n'
    cat "$TRACE"
  fi
} > "$PROMPT_FILE"

run_model() {
  # $1 = model name. Prints raw Gemini output; filters CLI startup noise.
  # Run from a neutral cwd (the temp dir holding the prompt) so a project-level
  # GEMINI.md is NOT auto-loaded into critic calls — the wrapper already injects
  # all context explicitly. GEMINI.md stays purely for interactive `gemini` use.
  ( cd "$(dirname "$PROMPT_FILE")" && agy --model "$1" -p "$(cat "$PROMPT_FILE")" ) 2>&1 \
    | grep -viE '^(Ripgrep is not available|\[STARTUP\]|update_topic\()'
}

is_quota_error() {
  # Covers both API-key (quota/429) and OAuth/Code-Assist (capacity/exhausted)
  # exhaustion, plus bad-alias 404s so we still fall back to a working model.
  grep -qiE 'quota|capacity|exhausted|RESOURCE_EXHAUSTED|TerminalQuotaError|ModelNotFound|not found|429' <<<"$1"
}

echo ">> Критик: $PRIMARY_MODEL" >&2
OUT="$(run_model "$PRIMARY_MODEL" || true)"
USED="$PRIMARY_MODEL"

if is_quota_error "$OUT"; then
  echo ">> Pro-квота вичерпана → фолбек на $FALLBACK_MODEL" >&2
  OUT="$(run_model "$FALLBACK_MODEL" || true)"
  USED="$FALLBACK_MODEL (fallback)"
fi

printf '%s\n' "$OUT"
printf '\n— [критик: %s]\n' "$USED"

# Audit trail (best-effort; never fail the run on logging)
{
  printf '%s | critic=%s | package=%s%s\n' \
    "$(date '+%Y-%m-%d %H:%M')" "$USED" "$(basename "$PKG")" \
    "${TRACE:+ | trace=$(basename "$TRACE")}"
} >> "$AUDIT" 2>/dev/null || true
