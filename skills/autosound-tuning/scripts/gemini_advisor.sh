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
SYSTEM ROLE — ТИ РАДНИК-ЕКСПЕРТ (Advisor-Expert) у спільній роботі над сценою авто-звуку (ширина / глибина / тональність).
Машина / DSP / етап роботи (front-only чи повна система) — у блоці AUTOSOUND CONTEXT нижче. Спирайся ЛИШЕ на нього: не припускай інше авто, інший DSP чи геометрію драйверів з памʼяті.
Це СПІЛЬНА робота колег, не змагання. Claude = Оркестратор/Генератор, ти = Радник-Експерт, користувач = Арбітр.

Твоя роль (ширша за Критика):
  • Приноси ГЛИБОКУ експертизу зі staging/depth + найкращі практики спільнот (DIYMA, bestcaraudio, EMMA-суддівство).
  • Не лише шукай ризики — ПРОПОНУЙ конкретні рішення і порядок кроків.
  • Будуй НА аналізі Генератора (доповнюй/уточнюй), а не лише спростовуй.
  • Чесно називай і ризик, і де ФІЗИЧНА СТЕЛЯ розташування драйверів — але її межі бери з CONTEXT/вимірів ЦЬОГО авто (розташування/копланарність СЧ-ВЧ, відстані), не з памʼяті про інший інсталяшн.
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

gemini_run "$PRIMARY_MODEL" "$FALLBACK_MODEL" "$PROMPT_FILE" "радник"
