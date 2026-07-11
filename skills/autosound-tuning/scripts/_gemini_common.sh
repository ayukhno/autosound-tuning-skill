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
# Sourced if present so a user pins CLI/model/paths ONCE, not on every call.
for _env in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do
  if [[ -f "$_env" ]]; then set -a; . "$_env"; set +a; break; fi
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
# CRITIC defaults to PRO: a Flash critic praises and misses obvious problems
# (field-observed) — one stronger model beats pages of "don't praise" prompt
# text. Flash stays the default for routine advisor pings + the FALLBACK when
# Pro quota is dry (agy Starter: weekly Flash+Pro group limit). Override per
# role via GEMINI_CRITIC_MODEL / GEMINI_ADVISOR_MODEL.
gemini_default_model() {
  case "$GEMINI_FLAVOR" in
    gemini) echo "gemini-2.5-flash" ;;
    *)      echo "Gemini 3.5 Flash (Medium)" ;;
  esac
}
gemini_default_critic_model() {
  case "$GEMINI_FLAVOR" in
    gemini) echo "gemini-2.5-pro" ;;
    *)      echo "Gemini 3.1 Pro (High)" ;;
  esac
}

die() { echo "${SCRIPT_NAME:-gemini}: $*" >&2; exit 1; }

gemini_preflight() {
  [[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT
  → run the intake to create rew_analitic/data-contract-template.md, or set PROJECT_MIRROR"
  [[ -f "$CONTEXT" ]] || die "context not found: $CONTEXT
  → copy your project's autosound_context.md into rew_analitic/, or set PROJECT_MIRROR"
  [[ -n "$GEMINI_BIN" ]] || die "no Gemini CLI on PATH — install the official one:
  npm i -g @google/gemini-cli   (then 'gemini'; see references/tooling/setup-critic-channel.md)"
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

# gemini_doctor — one-shot preflight: diagnose the WHOLE channel + run a live smoke,
# so setup traps surface in ONE command instead of serially (a real cold-start hit
# ~6 papercuts here). Invoked via the wrappers' `--doctor` flag.
gemini_doctor() {
  local ok=1 envf bin
  echo "== Gemini reviewer channel — doctor =="
  if [[ -z "${GEMINI_BIN:-}" ]]; then
    echo "✗ CLI: none on PATH. Fix: brew install --cask antigravity-cli (agy, default) OR npm i -g @google/gemini-cli"; ok=0
  else
    bin="$(command -v "$GEMINI_BIN" 2>/dev/null || echo "$GEMINI_BIN")"
    echo "✓ CLI: $GEMINI_BIN → $bin  (flavor=$GEMINI_FLAVOR · model='$(gemini_default_model)' · extra='${GEMINI_EXTRA_ARGS}')"
    if [[ "$(uname)" == Darwin && -e "$bin" ]] && xattr -p com.apple.quarantine "$bin" >/dev/null 2>&1; then
      echo "✗ quarantine: $bin is Gatekeeper-quarantined. Fix: xattr -dr com.apple.quarantine \"$bin\""; ok=0
    fi
  fi
  envf=""; for e in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do [[ -f "$e" ]] && { envf="$e"; break; }; done
  if [[ -n "$envf" ]]; then
    if ( set -a; . "$envf" ) 2>/tmp/_ce_err; then echo "✓ .critic-env: $envf parses"
    else echo "✗ .critic-env: $envf SYNTAX error — quote model names with spaces/parens, e.g. GEMINI_CRITIC_MODEL=\"Gemini 3.5 Flash (Medium)\":"; sed 's/^/    /' /tmp/_ce_err; ok=0; fi
    rm -f /tmp/_ce_err
  else echo "· .critic-env: none (defaults; optional — cp scripts/.critic-env.example rew_analitic/.critic-env)"; fi
  [[ -f "$CONTRACT" ]] && echo "✓ contract: $CONTRACT" || { echo "✗ contract: $CONTRACT not found — run intake or set PROJECT_MIRROR"; ok=0; }
  [[ -f "$CONTEXT"  ]] && echo "✓ context:  $CONTEXT"  || { echo "✗ context:  $CONTEXT not found — copy autosound_context.md into rew_analitic/ or set PROJECT_MIRROR"; ok=0; }
  if [[ -n "${GEMINI_BIN:-}" ]]; then
    echo "— live smoke (1 line) —"
    local sf out; sf="$(mktemp)"; printf 'reply with exactly: channel works' > "$sf"
    out="$(_run_model "$(gemini_default_model)" "$sf" || true)"; rm -f "$sf"
    if [[ -z "${out//[[:space:]]/}" ]]; then echo "✗ smoke: EMPTY → quota exhausted (agy weekly Starter tier?) or lost auth. agy: run 'agy' in a REAL terminal to log in / check the weekly countdown. gemini: set GEMINI_API_KEY (the OAuth tier is deprecated)."; ok=0
    elif _is_quota_error "$out"; then echo "✗ smoke: model/quota error → $(printf '%s' "$out" | head -1)"; ok=0
    else echo "✓ smoke: $(printf '%s' "$out" | head -1)"; fi
  fi
  echo "== $([[ $ok = 1 ]] && echo 'ALL GOOD ✓' || echo 'ISSUES ABOVE ✗ — fix and re-run --doctor') =="
  [[ $ok = 1 ]]
}
