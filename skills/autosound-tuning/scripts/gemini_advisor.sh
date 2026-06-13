#!/usr/bin/env bash
# gemini_advisor.sh — Claude↔Gemini "Advisor-Expert" channel (depth/staging work).
#
# Variant of gemini_critic.sh where Gemini plays ADVISOR-EXPERT (Радник-Експерт),
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
# Env overrides:
#   GEMINI_ADVISOR_MODEL  primary model (default: gemini-2.5-flash)
#   GEMINI_FALLBACK_MODEL fallback (default: gemini-2.5-flash)
#   ADVISOR_MEMORY        session-memory file (default: project rew_analitic/depth-advisor-memory.md)
#   AUTOSOUND_DIR         contract/context/audit location (default: iCloud _AI/Autosound)
set -euo pipefail

AUTOSOUND_DIR="${AUTOSOUND_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound}"
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_MIRROR="${PROJECT_MIRROR:-$(cd "$_SCRIPT_DIR/../../../.." && pwd)/rew_analitic}"

CONTRACT="$AUTOSOUND_DIR/data-contract-template.md"
[[ -f "$CONTRACT" ]] || CONTRACT="$PROJECT_MIRROR/data-contract-template.md"
CONTEXT="$AUTOSOUND_DIR/autosound_context.md"
[[ -f "$CONTEXT" ]] || CONTEXT="$PROJECT_MIRROR/autosound_context.md"
AUDIT="$AUTOSOUND_DIR/audit-trail.md"
ADVISOR_MEMORY="${ADVISOR_MEMORY:-$PROJECT_MIRROR/depth-advisor-memory.md}"

PRIMARY_MODEL="${GEMINI_ADVISOR_MODEL:-Gemini 3.5 Flash (Medium)}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-Gemini 3.5 Flash (Medium)}"

die() { echo "gemini_advisor: $*" >&2; exit 1; }

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: gemini_advisor.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
[[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT"
[[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT"
command -v agy >/dev/null || die "agy CLI not on PATH"

PROMPT_FILE="$(mktemp -t autosound_advisor.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  cat <<'HDR'
SYSTEM ROLE — ТИ РАДНИК-ЕКСПЕРТ (Advisor-Expert) у спільній роботі над ГЛИБИНОЮ та ШИРИНОЮ сцени авто-звуку (Passat B8, Helix DSP Ultra S, фронт-only цей етап).
Це СПІЛЬНА робота колег, не змагання. Claude = Оркестратор/Генератор, ти = Радник-Експерт, користувач = Арбітр.

Твоя роль (ширша за Критика):
  • Приноси ГЛИБОКУ експертизу зі staging/depth + найкращі практики спільнот (DIYMA, bestcaraudio, EMMA-суддівство).
  • Не лише шукай ризики — ПРОПОНУЙ конкретні рішення і порядок кроків.
  • Будуй НА аналізі Генератора (доповнюй/уточнюй), а не лише спростовуй.
  • Чесно називай і ризик, і де фізична стеля (A-pillar СЧ near-coplanar — глибина обмежена розташуванням).
  • Заперечення/поради — ФАЛЬСИФІКОВАНІ (перевірюваність на слух/виміром), не «вайб».
  • Думай фізикою салону + психоакустикою (precedence/Haas, ILD/ITD/IPD, відбиття скла), не математикою ідеальних фільтрів.
  • Памʼятай: all-pass плоский по АЧХ — зміна АЧХ лише через СУМАЦІЮ джерел; all-pass НЕ заповнює магнітудний нуль.
  • Якщо тобі для поради БРАКУЄ даних або потрібне рішення Арбітра — СФОРМУЛЮЙ питання до користувача (Claude передасть).

МАЄШ ПАМʼЯТЬ СЕСІЇ (нижче блок «ПАМʼЯТЬ РАДНИКА») — це накопичені рішення/дані попередніх раундів. Спирайся на неї, не повторюй уже узгоджене, нарощуй.

Відповідай українською, структуровано: (1) оцінка пропозиції, (2) ризики/застереження (фальсифіковані), (3) конкретні поради + порядок, (4) питання до Арбітра якщо є.

====== DATA CONTRACT (регламент, формат пакета §3) ======
HDR
  cat "$CONTRACT"
  printf '\n\n====== AUTOSOUND CONTEXT (єдина точка правди) ======\n'
  cat "$CONTEXT"
  if [[ -f "$ADVISOR_MEMORY" ]]; then
    printf '\n\n====== ПАМʼЯТЬ РАДНИКА (накопичені рішення/дані сесій depth) ======\n'
    cat "$ADVISOR_MEMORY"
  fi
  printf '\n\n====== ПАКЕТ ГЕНЕРАТОРА (Claude) — обговори як Радник ======\n'
  cat "$PKG"
  if [[ -n "$TRACE" && -f "$TRACE" ]]; then
    printf '\n\n====== ПРИКРІПЛЕНИЙ ТРЕЙС (проріджений) ======\n'
    cat "$TRACE"
  fi
} > "$PROMPT_FILE"

run_model() {
  ( cd "$(dirname "$PROMPT_FILE")" && agy --model "$1" -p "$(cat "$PROMPT_FILE")" ) 2>&1 \
    | grep -viE '^(Ripgrep is not available|\[STARTUP\]|update_topic\()'
}
is_quota_error() { grep -qiE 'quota|capacity|exhausted|RESOURCE_EXHAUSTED|TerminalQuotaError|ModelNotFound|not found|429' <<<"$1"; }

echo ">> Радник: $PRIMARY_MODEL" >&2
OUT="$(run_model "$PRIMARY_MODEL" || true)"; USED="$PRIMARY_MODEL"
if is_quota_error "$OUT"; then
  echo ">> Pro-квота вичерпана → фолбек на $FALLBACK_MODEL" >&2
  OUT="$(run_model "$FALLBACK_MODEL" || true)"; USED="$FALLBACK_MODEL (fallback)"
fi
printf '%s\n' "$OUT"
printf '\n— [радник: %s]\n' "$USED"
{ printf '%s | advisor=%s | package=%s%s\n' "$(date '+%Y-%m-%d %H:%M')" "$USED" "$(basename "$PKG")" "${TRACE:+ | trace=$(basename "$TRACE")}"; } >> "$AUDIT" 2>/dev/null || true
