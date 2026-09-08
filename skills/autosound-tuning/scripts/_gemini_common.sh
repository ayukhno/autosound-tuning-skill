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
# you launch Claude from (CWD). A stale copy from ANOTHER project must
# NOT hijack the Critic — that silently leaks the wrong vehicle's context (the
# real "Critic cited sessions that never happened" bug). Override any path via
# env or a .critic-env file — see references/tooling/setup-critic-channel.md.

# --- optional per-machine / per-project config -----------------------------
# READ as KEY=VALUE. Never sourced.
#
# This file used to be run through `.` with `set -a`. That meant a project someone else wrote --
# a clone, a copy off a stick, a folder a customer sent -- executed arbitrary shell the moment you
# started the reviewer. Nothing in here needs a shell: it is a list of names and values, and that
# is now all it can be (HUB-025).
_critic_load() {                                   # $1 = file
  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"        # ltrim
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == export\ * ]] && line="${line#export }"
    [[ "$line" != *=* ]] && continue
    # A value that can RUN something is not a value. These three are how a config file turns
    # into a shell script; a line carrying one is dropped, and said out loud rather than ignored.
    if [[ "$line" == *'$('* || "$line" == *'`'* || "$line" == *';'* ]]; then
      printf 'critic-env: рядок відкинуто (виконуваний вміст): %s\n' "${line%%=*}" >&2
      continue
    fi
    key="${line%%=*}"; val="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    val="${val#"${val%%[![:space:]]*}"}"           # ltrim
    val="${val%"${val##*[![:space:]]}"}"           # rtrim
    if [[ ${#val} -ge 2 && ( "$val" == \"*\" || "$val" == \'*\' ) ]]; then
      val="${val:1:${#val}-2}"                     # one layer of matching quotes
    fi
    export "$key=$val"
  done < "$1"
}

# WHERE the key lives, and why it is not in the project. The project folder is the one the README
# tells you to back up to a private GitHub -- so a secret kept there is a secret one `git push`
# away from leaving, and `.gitignore` does not stop `git add -f`, a folder copy, or a backup that
# is not git at all. The per-machine file is the first line; `.gitignore` (seeded by
# project_seed.py) is the second.
#
# Both are read, machine first, so a project can still pin non-secret things -- models,
# GEMINI_BIN, PROJECT_MIRROR -- and an existing project-local file keeps working unchanged.
if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then _critic_machine="$XDG_CONFIG_HOME/autosound/critic-env"
else                                     _critic_machine="$HOME/.config/autosound/critic-env"; fi
for _env in "$_critic_machine" "${APPDATA:+$APPDATA/autosound/critic-env}" \
            "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do
  [[ -n "$_env" && -f "$_env" ]] && _critic_load "$_env"
done

# --- where the docs live ----------------------------------------------------
# PROJECT_MIRROR = the project you're tuning RIGHT NOW (= CWD/rew_analitic).
# AUTOSOUND_DIR  = an OPTIONAL cross-project canon dir (UNSET by default; set it
#                  yourself in .critic-env for a shared Context/audit home).
PROJECT_MIRROR="${PROJECT_MIRROR:-$PWD/rew_analitic}"
AUTOSOUND_DIR="${AUTOSOUND_DIR:-}"

CONTRACT="$PROJECT_MIRROR/data-contract-template.md"
[[ -f "$CONTRACT" || -z "$AUTOSOUND_DIR" ]] || CONTRACT="$AUTOSOUND_DIR/data-contract-template.md"
CONTEXT="$PROJECT_MIRROR/autosound_context.md"
[[ -f "$CONTEXT" || -z "$AUTOSOUND_DIR" ]] || CONTEXT="$AUTOSOUND_DIR/autosound_context.md"
# Audit: project-local by default; the $AUTOSOUND_DIR canon only if you set one.
if [[ -n "$AUTOSOUND_DIR" && -d "$AUTOSOUND_DIR" ]]; then AUDIT="$AUTOSOUND_DIR/audit-trail.md"
else AUDIT="$PROJECT_MIRROR/audit-trail.md"; fi

# --- Gemini CLI detection ---------------------------------------------------
# Zero-config for both rigs: the author's `agy` (Antigravity) wins when present;
# a fresh user who `npm i -g @google/gemini-cli` gets `gemini`. Force either by
# setting GEMINI_BIN (e.g. in .critic-env). DON'T symlink agy→gemini — just let
# detection pick gemini; that keeps the model ids + flags correct for each CLI.
#
# ⚠️ The `gemini` CLI's OWN sign-in is CLOSED (2026-09-08, gemini-cli 0.50.0, both models):
#
#   Error authenticating: IneligibleTierError: This client is no longer supported for Gemini
#   Code Assist for individuals. To continue using Gemini, please migrate to the Antigravity
#   suite of products: https://antigravity.google
#
# Google shut the free OAuth tier the CLI signed in with; `agy` is what replaced it. A key does
# NOT reopen it as installed: with a fresh AQ.-shaped GEMINI_API_KEY in the environment the same
# 0.50.0 still went to its sign-in (`_doSetupUser`) and printed the text above (probed
# 2026-09-08) -- the CLI's stored auth mode decides, not the variable. So `gemini` is detected
# only so that the closed path is NAMED: `_is_dead_cli_error` recognises the words and the
# wrapper says "the path is closed, use agy" instead of falling back to a second model on the
# same closed door (hub PAS-004: ~10 minutes of diagnosis in a car, on a fact one line can carry).
# A GEMINI_API_KEY still has a use -- the direct API in `autosound_ai.py` -- which is why the
# doctor checks the key at all.
# What the key was before any config file was read -- the doctor tells a stale shell export
# from a file value with it.
_GEMINI_KEY_FROM_SHELL="${GEMINI_API_KEY:-}"
if [[ -z "${GEMINI_BIN:-}" ]]; then
  if command -v agy >/dev/null 2>&1; then GEMINI_BIN=agy
  elif command -v gemini >/dev/null 2>&1; then GEMINI_BIN=gemini
  else GEMINI_BIN=""; fi
fi
GEMINI_FLAVOR="$(basename "${GEMINI_BIN:-none}")"

# Catch a FAKE agy = a symlink `agy → gemini` (the #1 setup trap, e.g. from an
# earlier attempt): we'd otherwise pick agy model-ids + flags but actually invoke
# gemini → "untrusted dir" error + wrong model. Resolve the symlink chain; if it
# lands on gemini, run as the GEMINI flavor (right ids + --skip-trust) and nudge
# toward installing the real Antigravity CLI.
if [[ "$GEMINI_FLAVOR" == agy ]]; then
  _agy_p="$(command -v agy 2>/dev/null || true)"; _agy_r="$_agy_p"
  for _ in 1 2 3 4 5; do [[ -L "$_agy_r" ]] || break; _agy_r="$(readlink "$_agy_r")"; done
  case "$(basename "${_agy_r:-}")" in
    *gemini*)
      echo ">> WARNING: 'agy' on PATH is a symlink to gemini ($_agy_p → $_agy_r), NOT real Antigravity — using the gemini flavor (right model ids + --skip-trust). For real agy: brew install --cask antigravity-cli (references/tooling/setup-critic-channel.md §1)." >&2
      GEMINI_FLAVOR=gemini ;;
  esac
fi

# Per-CLI extra args: @google/gemini-cli refuses headless runs in an "untrusted"
# directory unless --skip-trust is passed; agy has no such flag.
if [[ -z "${GEMINI_EXTRA_ARGS:-}" ]]; then
  case "$GEMINI_FLAVOR" in
    gemini) GEMINI_EXTRA_ARGS="--skip-trust" ;;
    *)      GEMINI_EXTRA_ARGS="" ;;
  esac
fi

# Per-CLI default model. agy uses human-readable labels (`agy models`);
# @google/gemini-cli uses API ids (`gemini models` / the docs).
# BOTH review roles default to PRO: a Flash reviewer praises, misses obvious
# problems, and — as an advisor — will endorse both sides of the very question
# it was asked to settle (field-observed). One stronger model beats pages of
# "don't praise" prompt text. Flash is the FALLBACK only, for when Pro quota is
# dry (agy Starter: weekly Flash+Pro group limit); the fallback prints a warning
# because a weak round reads like a strong one. Override per role via
# GEMINI_CRITIC_MODEL / GEMINI_ADVISOR_MODEL.
# ⚠️ Model NAMES drift, and the drift finished. `agy models` prints two columns —
# the slug id on the left, the display label on the right — and BOTH were accepted
# until they were not. On agy 1.1.12 the label is rejected outright:
#
#   Error: invalid model selection (--model "Gemini 3.5 Flash (Medium)"):
#   model … is not recognized as a known model or custom model in settings
#
# even though that exact label is what `agy models` shows. Slug ids only, then
# (found on a clean install, 2026-08-13). `agy models` remains the way to check;
# as of that date it also offers gemini-3.6-flash-* , which is newer than the
# advisor default here and has not been used for a tune.
gemini_default_model() {
  case "$GEMINI_FLAVOR" in
    gemini) echo "gemini-2.5-flash" ;;
    *)      echo "gemini-3.5-flash-medium" ;;
  esac
}
gemini_default_critic_model() {
  case "$GEMINI_FLAVOR" in
    gemini) echo "gemini-2.5-pro" ;;
    *)      echo "gemini-3.1-pro-high" ;;
  esac
}

die() { echo "${SCRIPT_NAME:-gemini}: $*" >&2; exit 1; }

gemini_preflight() {
  [[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT
  → run the intake to create rew_analitic/data-contract-template.md, or set PROJECT_MIRROR"
  [[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT
  → copy your project's autosound_context.md into rew_analitic/, or set PROJECT_MIRROR"
  [[ -n "$GEMINI_BIN" ]] || die "no Gemini CLI on PATH — install Antigravity:
  brew install --cask antigravity-cli   (then 'agy' once to log in; references/tooling/setup-critic-channel.md §1)
  (the old @google/gemini-cli sign-in is closed since 2026-09-08, a key in the environment did not reopen it)"
  if [[ "$GEMINI_FLAVOR" == gemini && -z "${GEMINI_API_KEY:-}" ]]; then
    echo ">> WARNING: $(_dead_cli_message)" >&2
  fi
}

# The closed path, recognised by the words Google prints for it. Kept apart from
# `_is_quota_error`: a quota error is worth a fallback model, this is not -- the second model
# fails at the same sign-in, and falling back only doubles the wait before the real answer.
_is_dead_cli_error() {
  grep -qiE 'IneligibleTierError|no longer supported for Gemini Code Assist|migrate to the Antigravity' <<<"$1"
}
_dead_cli_message() {
  printf '%s' "шлях gemini CLI закрито Google (IneligibleTierError, 2026-09-08: «This client is no longer supported for Gemini Code Assist for individuals … migrate to the Antigravity suite»; ключ в оточенні його не відкриває — перевірено) — використовуй agy: brew install --cask antigravity-cli, потім 'agy' для входу; ключ GEMINI_API_KEY у ~/.config/autosound/critic-env живить прямий API (autosound_ai.py), не цей CLI (setup-critic-channel.md §1–§3)"
}

# What shape a GEMINI_API_KEY has: `AQ.` + 53 chars is the format AI Studio issues now (seen
# 2026-09-08); `AIza` + 39 was the format before it, and a key of that shape sitting in a shell's
# environment while the profile already holds a new one is exactly how a working key reads as
# API_KEY_INVALID (the session's environment does not follow ~/.zshrc after it started).
_key_format() {
  local k="$1"
  if [[ "$k" == AQ.* && ${#k} -eq 53 ]]; then echo "current (AQ.…, 53 chars)"
  elif [[ "$k" == AIza* && ${#k} -eq 39 ]]; then echo "OLD format (AIza…, 39 chars) — AI Studio issues AQ.… keys now; if the profile holds a new one, this shell has not seen it"
  else echo "unrecognised shape (${#k} chars)"; fi
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
  if _is_dead_cli_error "$out"; then
    echo ">> ✗ $(_dead_cli_message)" >&2
    echo ">>   ($GEMINI_FLAVOR said: $(printf '%s' "$out" | grep -iE 'IneligibleTierError|no longer supported' | head -1 | cut -c1-160))" >&2
    echo ">>   The fallback model is NOT tried: it fails at the same sign-in." >&2
    printf '\n— [%s: %s — no reply: the gemini CLI path is closed, use agy]\n' "$role" "$used"
    return 2
  fi
  if _is_quota_error "$out"; then
    echo ">> ⚠️  $primary unavailable/exhausted → FALLING BACK to $fallback" >&2
    echo ">>    A fallback model is weaker at judging METHOD validity: it tends to agree" >&2
    echo ">>    with the package it was handed and can endorse both sides of the open" >&2
    echo ">>    question. Treat this round as advisory, and re-run on the primary model" >&2
    echo ">>    before banking anything that rests on it." >&2
    out="$(_run_model "$fallback" "$pf" || true)"; used="$fallback (fallback)"
  fi
  if [[ -z "${out//[[:space:]]/}" ]]; then
    echo ">> WARNING: $GEMINI_FLAVOR returned an EMPTY reply ($used) — most often the CLI's QUOTA is exhausted (e.g. Antigravity 'Starter' has a weekly Gemini-group limit that hits 0% → empty exit-0, NO error text → not caught as a quota error above), or it lost auth. Check the CLI's quota (\`agy\` shows a weekly limit + refresh countdown); then either switch to a model group that still has quota (GEMINI_*_MODEL) or to the other CLI (pin GEMINI_BIN=gemini in rew_analitic/.critic-env). See references/tooling/setup-critic-channel.md." >&2
  fi
  printf '%s\n' "$out"
  printf '\n— [%s: %s]\n' "$role" "$used"
  { printf '%s | %s=%s | package=%s%s\n' "$(date '+%Y-%m-%d %H:%M')" \
      "$role" "$used" "$(basename "${PKG:-?}")" "${TRACE:+ | trace=$(basename "$TRACE")}"; } \
    >> "$AUDIT" 2>/dev/null || true
  # Full round transcript → review-log (session reconstruction / observability). Disable with REVIEW_LOG=.
  local rlog="${REVIEW_LOG-$PROJECT_MIRROR/review-log.md}"
  if [[ -n "$rlog" ]]; then
    {
      printf '\n---\n## %s · %s · %s · package=%s%s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$role" "$used" "$(basename "${PKG:-?}")" "${TRACE:+ · trace=$(basename "$TRACE")}"
      if grep -qiE '/clear|re-?anchor|drift|дрейф|ре-анкор|перечита' <<<"$out"; then
        printf '> ⚠️ DRIFT-FLAG: reviewer flagged possible Generator drift (re-anchor / clear)\n'
      fi
      printf '\n### Package (Generator → reviewer)\n```\n%s\n```\n\n### Reply (reviewer → Generator)\n%s\n' \
        "$(cat "${PKG:-/dev/null}" 2>/dev/null)" "$out"
    } >> "$rlog" 2>/dev/null || true
  fi
}

# gemini_selfcheck — offline: the recognisers on the words they exist for, and the doctor's
# closed-path branches driven by a stubbed CLI. No network, no quota. Wired as
# `gemini_critic.sh --selftest` and into scripts/run-selftests.sh.
gemini_selfcheck() {
  local dead='Error authenticating: IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals. To continue using Gemini, please migrate to the Antigravity suite of products: https://antigravity.google'
  _is_dead_cli_error "$dead" || { echo "selfcheck: the closed-path text was not recognised"; return 1; }
  _is_dead_cli_error "channel works" && { echo "selfcheck: a good reply read as the closed path"; return 1; }
  _is_quota_error "$dead" && { echo "selfcheck: the closed path read as a quota error (it would fall back)"; return 1; }
  _is_quota_error "Error: 429 RESOURCE_EXHAUSTED" || { echo "selfcheck: a quota error was not recognised"; return 1; }
  [[ "$(_key_format "AQ.$(printf 'x%.0s' $(seq 1 50))")" == current* ]] || { echo "selfcheck: AQ. key shape"; return 1; }
  [[ "$(_key_format "AIza$(printf 'x%.0s' $(seq 1 35))")" == OLD* ]] || { echo "selfcheck: AIza key shape"; return 1; }
  [[ "$(_key_format "nonsense")" == unrecognised* ]] || { echo "selfcheck: odd key shape"; return 1; }
  # The doctor, on a CLI that answers the smoke with the closed-path text: it must NAME the
  # path, not report an answered smoke or a quota. Driven through the same functions the real
  # run uses, with only the CLI call and the key probe stubbed.
  local saved_bin="$GEMINI_BIN" saved_flavor="$GEMINI_FLAVOR" saved_key="${GEMINI_API_KEY:-}" report
  GEMINI_BIN=gemini; GEMINI_FLAVOR=gemini; unset GEMINI_API_KEY
  _run_model() { printf '%s\n' "$dead"; }
  report="$(gemini_doctor 2>&1 || true)"
  unset -f _run_model
  GEMINI_BIN="$saved_bin"; GEMINI_FLAVOR="$saved_flavor"
  [[ -n "$saved_key" ]] && export GEMINI_API_KEY="$saved_key"
  grep -q 'gemini without a GEMINI_API_KEY' <<<"$report" || { echo "selfcheck: the doctor did not name a key-less gemini CLI"; printf '%s\n' "$report"; return 1; }
  grep -q '✗ smoke: шлях gemini CLI закрито' <<<"$report" || { echo "selfcheck: the doctor did not name the closed path in the smoke"; printf '%s\n' "$report"; return 1; }
  grep -q '✓ smoke' <<<"$report" && { echo "selfcheck: the closed path passed as a smoke"; return 1; }
  # And gemini_run on the same CLI: the message, no fallback attempt, a non-zero return.
  local calls=0 pf; pf="$(mktemp)"; printf 'x' > "$pf"
  _run_model() { calls=$((calls + 1)); printf '%s\n' "$dead"; }
  GEMINI_FLAVOR=gemini
  report="$(gemini_run gemini-2.5-pro gemini-2.5-flash "$pf" critic 2>&1)"; local rc=$?
  unset -f _run_model; rm -f "$pf"; GEMINI_FLAVOR="$saved_flavor"
  [[ $rc -eq 2 ]] || { echo "selfcheck: gemini_run returned $rc on the closed path, expected 2"; return 1; }
  grep -q 'закрито Google' <<<"$report" || { echo "selfcheck: gemini_run did not name the closed path"; return 1; }
  grep -q 'FALLING BACK' <<<"$report" && { echo "selfcheck: gemini_run fell back on the closed path"; return 1; }
  echo "selftest[gemini-channel] OK -- IneligibleTierError recognised (and not as a quota), key shapes AQ./AIza/odd told apart, the doctor names a key-less gemini CLI and the closed path in its smoke, gemini_run stops at the closed door without a fallback (rc 2)"
}

# gemini_doctor — one-shot preflight: diagnose the WHOLE channel + run a live smoke,
# so setup traps surface in ONE command instead of serially (a real cold-start hit
# ~6 papercuts here). Invoked via the wrappers' `--doctor` flag.
gemini_doctor() {
  local ok=1 chan_ok=0 key_ok=1 proj_ok=1 envf bin
  echo "== Gemini reviewer channel — doctor =="
  if [[ -z "${GEMINI_BIN:-}" ]]; then
    echo "✗ CLI: none on PATH. Fix: brew install --cask antigravity-cli (agy; the old @google/gemini-cli sign-in is closed — it needs a GEMINI_API_KEY now)"; ok=0
  else
    bin="$(command -v "$GEMINI_BIN" 2>/dev/null || echo "$GEMINI_BIN")"
    echo "✓ CLI: $GEMINI_BIN → $bin  (flavor=$GEMINI_FLAVOR · critic='${GEMINI_CRITIC_MODEL:-$(gemini_default_critic_model)}' · advisor='${GEMINI_ADVISOR_MODEL:-$(gemini_default_model)}' · extra='${GEMINI_EXTRA_ARGS}')"
    if [[ "$(uname)" == Darwin && -e "$bin" ]] && xattr -p com.apple.quarantine "$bin" >/dev/null 2>&1; then
      echo "✗ quarantine: $bin is Gatekeeper-quarantined. Fix: xattr -dr com.apple.quarantine \"$bin\""; ok=0
    fi
    if [[ "$GEMINI_FLAVOR" == gemini && -z "${GEMINI_API_KEY:-}" ]]; then
      echo "✗ CLI: gemini without a GEMINI_API_KEY — $(_dead_cli_message)"; ok=0
    fi
  fi
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    echo "· key: GEMINI_API_KEY is set — $(_key_format "$GEMINI_API_KEY")"
    if [[ -n "$_GEMINI_KEY_FROM_SHELL" && "$_GEMINI_KEY_FROM_SHELL" == "${GEMINI_API_KEY}" ]]; then
      echo "  ⚠ it came from this shell's environment, not from a critic-env file: a key changed in ~/.zshrc after this session started is NOT what this session holds (setup-critic-channel.md §3)"
    fi
    if command -v curl >/dev/null 2>&1; then
      # One GET that costs nothing (a model listing), the key never printed: the code says live
      # or not, and API_KEY_INVALID in the body is the old-key-in-a-new-world case by name.
      # The key travels as a header read from a 0600 file -- not in the URL and not in argv,
      # where `ps`, a shell trace or a proxy log would have it (the same rule as HUB-025).
      local kc kb kh; kb="$(mktemp)"; kh="$(mktemp)"; chmod 600 "$kh"
      printf 'x-goog-api-key: %s\n' "$GEMINI_API_KEY" > "$kh"
      kc="$(curl -s -m 10 -o "$kb" -w '%{http_code}' -H @"$kh" "https://generativelanguage.googleapis.com/v1beta/models" 2>/dev/null || echo 000)"
      rm -f "$kh"
      case "$kc" in
        200) echo "✓ key: GET /v1beta/models → 200 (the key is live)";;
        000) echo "· key: GET /v1beta/models → no answer (offline?) — not checked";;
        *)   echo "✗ key: GET /v1beta/models → HTTP $kc$(grep -o 'API_KEY_INVALID' "$kb" | head -1 | sed 's/^/ /') — a new key from https://aistudio.google.com/apikey into ~/.config/autosound/critic-env, then re-run; if the file already holds a new one, unset the shell's export"; ok=0; key_ok=0;;
      esac
      rm -f "$kb"
    fi
  fi
  envf=""; for e in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do [[ -f "$e" ]] && { envf="$e"; break; }; done
  if [[ -n "$envf" ]]; then
    if ( set -a; . "$envf" ) 2>/tmp/_ce_err; then echo "✓ .critic-env: $envf parses"
    else echo "✗ .critic-env: $envf SYNTAX error — quote model names with spaces/parens, e.g. GEMINI_CRITIC_MODEL=\"Gemini 3.5 Flash (Medium)\":"; sed 's/^/    /' /tmp/_ce_err; ok=0; fi
    rm -f /tmp/_ce_err
  else echo "· .critic-env: none (defaults; optional — cp scripts/.critic-env.example rew_analitic/.critic-env)"; fi
  [[ -f "$CONTRACT" ]] && echo "✓ contract: $CONTRACT" || { echo "✗ contract: $CONTRACT not found — run intake or set PROJECT_MIRROR"; ok=0; proj_ok=0; }
  [[ -f "$CONTEXT"  ]] && echo "✓ context:  $CONTEXT"  || { echo "✗ context:  $CONTEXT not found — copy autosound_context.md into rew_analitic/ or set PROJECT_MIRROR"; ok=0; proj_ok=0; }
  if [[ -n "${GEMINI_BIN:-}" ]]; then
    echo "— live smoke (1 line) —"
    local sf out; sf="$(mktemp)"; printf 'reply with exactly: channel works' > "$sf"
    out="$(_run_model "$(gemini_default_model)" "$sf" || true)"; rm -f "$sf"
    if [[ -z "${out//[[:space:]]/}" ]]; then echo "✗ smoke: EMPTY → quota exhausted (agy weekly Starter tier?) or lost auth. agy: run 'agy' in a REAL terminal to log in / check the weekly countdown. gemini: set GEMINI_API_KEY (its own sign-in is closed, see above)."; ok=0
    elif _is_dead_cli_error "$out"; then echo "✗ smoke: $(_dead_cli_message)"; ok=0
    elif _is_quota_error "$out"; then echo "✗ smoke: model/quota error → $(printf '%s' "$out" | head -1)"; ok=0
    # The smoke asked for exact words; anything else is a failure, however cheerful it looks.
    # This used to pass ANY non-empty reply, so `Error: invalid model selection …` was reported
    # as "✓ smoke: Error: …" in the same run that ended with ISSUES ABOVE (2026-08-13).
    elif ! printf '%s' "$out" | grep -qi 'channel works'; then
      echo "✗ smoke: the reviewer answered, but not with what it was asked for →"
      printf '%s' "$out" | head -3 | sed 's/^/    /'
      ok=0
    else echo "✓ smoke: $(printf '%s' "$out" | head -1)"; chan_ok=1; fi
  fi
  # The channel and the project are two verdicts, and merging them read badly at the exact moment
  # the hard part started working: "✓ smoke: channel works" followed by "ISSUES ABOVE ✗", where
  # the issues were two project files missing because the doctor was run from a home directory
  # rather than from a car (2026-08-13).
  # ...and it read badly a second time when the key was the ✗ and the folder was a car: the
  # footer blamed "project files" for a key that had answered API_KEY_INVALID (2026-09-08). So
  # the footer names what failed, and only what failed.
  if [[ $ok = 1 ]]; then echo "== ALL GOOD ✓ =="
  elif [[ ${chan_ok:-1} = 1 ]]; then
    echo "== The reviewer channel works ✓ — what failed above:"
    [[ $proj_ok = 1 ]] || echo "   · project files: this is not a car's folder — run this again from inside one to check those too"
    [[ $key_ok = 1 ]]  || echo "   · the API key: the agy channel does not need it, the direct-API path (autosound_ai.py) does — fix it or drop the stale export"
    [[ $proj_ok = 1 && $key_ok = 1 ]] && echo "   · see the ✗ lines"
    echo "=="
  else
    echo "== ISSUES ABOVE ✗ — fix and re-run --doctor =="
  fi
  [[ $ok = 1 ]]
}
