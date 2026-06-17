#!/usr/bin/env bash
# gemini_critic.sh — Claude→Gemini "Critic" channel for autosound tuning.
#
# Sends a Generator package to Gemini acting as the CRITIC (Challenger), per
# data-contract-template.md. Injects the Data Contract + the PROJECT's
# autosound_context as system framing so Gemini answers grounded + in format.
#
# Usage:
#   gemini_critic.sh <package.md> [trace.csv]
#
# Args:
#   package.md   Generator package (the §3 format from the contract).
#   trace.csv    Optional decimated trace attached for point-checking the data.
#
# Config — set inline, via env, or once in rew_analitic/.critic-env
# (see references/setup-critic-channel.md). All resolved in _gemini_common.sh:
#   GEMINI_BIN            CLI to use (auto: agy → gemini)
#   GEMINI_CRITIC_MODEL   primary model (default per CLI; agy "Gemini 3.5 Flash (Medium)" · gemini gemini-2.5-flash)
#   GEMINI_FALLBACK_MODEL fallback when the primary is exhausted/unavailable
#   GEMINI_EXTRA_ARGS     extra CLI flags (auto: --skip-trust for @google/gemini-cli)
#   PROJECT_MIRROR        project docs dir (default: $PWD/rew_analitic)  ← context/contract live here
#   AUTOSOUND_DIR         author's iCloud canon (audit-log home; context fallback only)
set -euo pipefail
SCRIPT_NAME="gemini_critic"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_gemini_common.sh"

PKG="${1:-}"; TRACE="${2:-}"
[[ -n "$PKG" ]] || die "usage: gemini_critic.sh <package.md> [trace.csv]"
[[ -f "$PKG" ]] || die "package not found: $PKG"
gemini_preflight

PRIMARY_MODEL="${GEMINI_CRITIC_MODEL:-$(gemini_default_model)}"
FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-$(gemini_default_model)}"

PROMPT_FILE="$(mktemp -t autosound_critic.XXXXXX)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  cat <<'HDR'
SYSTEM ROLE — ТИ КРИТИК (Challenger) у дводмодельному циклі налаштування авто-звуку.
Завдання: знайти акустичні ризики й хибні припущення в ПРОПОЗИЦІЇ Генератора.
Машина / DSP / стан системи — у блоці AUTOSOUND CONTEXT нижче; спирайся лише на нього, не припускай інше авто.
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

gemini_run "$PRIMARY_MODEL" "$FALLBACK_MODEL" "$PROMPT_FILE" "критик"
