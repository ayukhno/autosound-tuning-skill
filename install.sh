#!/usr/bin/env bash
# Autosound tuning — installer for macOS (and Linux).
#
# One line puts everything a first tune needs on the machine. It asks its questions up front, in
# one screen, then runs on its own, and ends with the sign-ins — the only part that is genuinely
# the person's to do. What it installs, into the home folder (Apple's tools go where Apple puts
# them):
#
#   * Claude Code               the AI that runs the method                claude.ai/install.sh
#   * the tuning method         the newest 3.x tag        github.com/ayukhno/autosound-tuning-skill
#   * numpy, scipy, matplotlib  the method's own tools need them, into the user site
#   * uv + Python 3.12 + TCC    the Autosound TCC desktop app, and a double-clickable .app
#   * agy                       Google's Antigravity CLI — Gemini as the second AI, the reviewer
#   * gh                        GitHub's CLI, only if asked — backs up a project's record
#   * Command Line Tools        macOS only, when missing — Apple's git. The one part that needs an
#                               administrator password, asked once, at the start.
#
# What it will not do, and will not pretend to:
#
#   * press the sign-in buttons. TCC and the method drive YOUR `claude` login (and your agy and gh
#     logins); per the Agent SDK's terms a product may not offer a claude.ai login of its own. The
#     sign-ins run at the end, in your browser, and are yours.
#   * touch a project folder — not on install, not on --uninstall, not with --yes.
#   * replace a skill directory it did not create.
#
# Usage:
#   ./install.sh                     everything above; asks once, then runs on its own
#   ./install.sh --terminal          the method only, no desktop app (~700 MB less)
#   ./install.sh --no-reviewer       without the Gemini reviewer
#   ./install.sh --github            with the GitHub CLI (default: asks); --no-github: without
#   ./install.sh --no-omp            without omp, which offers TCC every non-Claude model
#   ./install.sh --dry-run           say what it would do, change nothing
#   ./install.sh --yes               yes to every question; sign-ins are printed, not run
#   ./install.sh --skill-ref v3.0.3  a specific skill version (default: the newest 3.x tag)
#   ./install.sh --uninstall         remove what this script installed — NEVER your projects
#   ./install.sh --uninstall --all   also uv, Claude Code and ~/.claude, agy/gh/omp when this
#                                    script installed them, and every --user pip package. For
#                                    resetting a test machine. Asks first.
set -euo pipefail

SKILL_REPO="https://github.com/ayukhno/autosound-tuning-skill.git"
#: The same repository without the `.git` — what a person opens in a browser, not what git clones.
SKILL_REPO_URL="${SKILL_REPO%.git}"
TCC_REPO="https://github.com/ayukhno/autosound-tcc"
SKILL_HOME="${HOME}/.claude/skills/autosound-tuning"
# The repo lives beside the skill and the skill POINTS at it. Cloning and then moving the
# subdirectory out (the obvious way) leaves a plain folder with no `.git`, so a second run cannot
# update it and the user is stuck on whatever version they first installed — found by running this
# script twice (2026-08-12). A checkout plus a symlink also makes `git -C … checkout v3.0.1` the
# whole of an upgrade, and matches what the README already teaches for staying on 2.x.
SKILL_SRC="${HOME}/.claude/skills/.autosound-tuning-src"
# Everything this script installs lands in one folder: uv, claude, agy, gh, omp, and the app's own
# command. One folder means one PATH line, however many of them there are — the second directory
# (/opt/homebrew/bin) is gone with Homebrew, and with it the day `agy` installed and was not found.
LOCAL_BIN="${HOME}/.local/bin"
# What THIS script put on the machine, one name per line. --uninstall removes what is listed here
# and nothing else: a tool the person already had — their own uv, their own agy — is never ours to
# delete, however sure we are of what it is (an installer deleted a Homebrew uv on 2026-08-13).
MANIFEST="${HOME}/.local/share/autosound/installer-manifest"
APP="${HOME}/Applications/Autosound TCC.app"
DESKTOP_LINK="${HOME}/Desktop/Autosound TCC.app"

MODE="tcc"
WANT_REVIEWER=1
#: Resolved after the options are read, because it follows the MODE: omp is what fills TCC's model
#: picker with everything that is not Claude, so it belongs with the app and means nothing without
#: it. It was opt-in (`--with-omp`) and that was wrong in the one way an option cannot fix — the
#: person who would want it is the person who does not know the flag exists, and a clean install
#: left them with a picker that offers two vendors and no clue why (user, 2026-08-19, installing
#: on a second Mac from the README's own one-liner). Now: on with the app, `--no-omp` to leave it
#: out, and named on the one screen that lists everything before anything downloads.
WANT_OMP="auto"
WANT_GITHUB="ask"
UNINSTALL=0
REMOVE_ALL=0
DRY_RUN=0
ASSUME_YES=0
SKILL_REF=""
# Saved before anything is installed: the uv step exports ~/.local/bin into THIS script's PATH so
# the rest of the run can call what it just installed. That made the summary print "✓
# autosound-tcc installed" to somebody whose own shell could not find it, because the check was
# asking the wrong PATH (2026-08-13).
PATH_AS_INHERITED="$PATH"

usage() {
  # A heredoc, not `sed` over "$0": under `curl … | bash` there is no file behind $0 to read.
  cat <<'USAGE'
Autosound tuning — installer for macOS (and Linux)

  install.sh                     everything: Claude Code, the method, the TCC app, the Gemini
                                 reviewer; asks once, then runs on its own
  install.sh --terminal          the method only, no desktop app (~700 MB less)
  install.sh --no-reviewer       without the Gemini reviewer
  install.sh --github            with the GitHub CLI (default: asks); --no-github: without
  install.sh --no-omp            without omp, which offers TCC every non-Claude model (metered)
  install.sh --dry-run           say what it would do, change nothing
  install.sh --yes               yes to every question; sign-ins are printed, not run
  install.sh --skill-ref v3.0.3  a specific skill version (default: the newest 3.x tag)
  install.sh --uninstall         remove what this script installed — NEVER your projects
  install.sh --uninstall --all   also uv, Claude Code and ~/.claude, agy/gh/omp when this script
                                 installed them, and every --user pip package. Asks first.

Through the one-liner, options go after `bash -s --`:
  curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash -s -- --terminal
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --terminal)    MODE="terminal" ;;
    --tcc)         MODE="tcc" ;;
    --no-reviewer) WANT_REVIEWER=0 ;;
    --reviewer)    WANT_REVIEWER=1 ;;
    --with-omp)    WANT_OMP=1 ;;   # kept: it was the way to ask for omp before it was default
    --no-omp)      WANT_OMP=0 ;;
    --github)      WANT_GITHUB=1 ;;
    --no-github)   WANT_GITHUB=0 ;;
    --uninstall)   UNINSTALL=1 ;;
    --all)         REMOVE_ALL=1 ;;
    --dry-run)     DRY_RUN=1 ;;
    --yes|-y)      ASSUME_YES=1 ;;
    --skill-ref)   SKILL_REF="${2:-}"; shift ;;
    --help|-h)     usage; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

# omp follows the app — see `WANT_OMP` above. `--terminal` is the method in a plain terminal, where
# the model is Claude Code's own and a picker for TCC's models has nothing to pick for.
# An `if`, not `[ … ] && …`: this script runs under `set -e`, where a top-level test that comes out
# false is an exit status and ends the install.
if [ "$WANT_OMP" = "auto" ]; then
  if [ "$MODE" = "tcc" ]; then WANT_OMP=1; else WANT_OMP=0; fi
fi

# ── small tools ───────────────────────────────────────────────────────────────
say()    { printf '%s\n' "$*"; }
step()   { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn()   { printf '  ! %s\n' "$*" >&2; }
have()   { command -v "$1" >/dev/null 2>&1; }
on_mac() { [ "$(uname -s)" = "Darwin" ]; }
# Paths on screen with the home folder as `~`. A person reads "~/.zshrc" as a place; the same
# path spelled out from /Users reads as a warning.
# shellcheck disable=SC2088  # the tilde is for display, not for the shell to expand
pretty() { case "$1" in "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;; *) printf '%s' "$1" ;; esac; }
# The documented way to run this is `curl … | bash`, which occupies stdin with the script itself.
# So every question, and every program that needs a keyboard, talks to the TERMINAL, not stdin —
# a plain `read` gets EOF and every question silently answers "no" (INSTALLER-TZ §2.2 concluded
# from this that a shell installer must not ask at all; asking the terminal is the narrower fix).
tty_ok() { ( : < /dev/tty ) 2>/dev/null; }
run() {
  if [ "$DRY_RUN" = 1 ]; then say "  would run: $*"; return 0; fi
  "$@"
}
in_local_bin() { [ -x "$LOCAL_BIN/$1" ]; }
# uv installs itself into ~/.local/bin, which is exactly the folder that is NOT on PATH on a fresh
# machine. Trusting `command -v` alone made --uninstall report "not installed by uv" about a TCC
# it had installed twenty minutes earlier, and walk away leaving it there (2026-08-13). Same for
# every other tool this script puts there.
find_bin() {  # prints the path of a tool, on PATH or in ~/.local/bin; fails when neither
  _b="$(command -v "$1" 2>/dev/null || true)"
  [ -n "$_b" ] || { in_local_bin "$1" && _b="$LOCAL_BIN/$1"; }
  [ -n "$_b" ] && printf '%s' "$_b"
}
manifest_add() {
  [ "$DRY_RUN" = 1 ] && return 0
  mkdir -p "$(dirname "$MANIFEST")"
  grep -qx "$1" "$MANIFEST" 2>/dev/null || printf '%s\n' "$1" >> "$MANIFEST"
}
manifest_has() { grep -qx "$1" "$MANIFEST" 2>/dev/null; }

# One question, one answer, on the terminal. `default` is what Enter means, and what a run with
# no terminal or a dry run takes. Recorded on stdout afterwards when stdout is not the terminal
# (a `| tee` transcript), because the prompt itself went to /dev/tty and would otherwise be
# missing from the log — and recorded AFTERWARDS with the answer, not before, or a tee'd run
# shows every question twice.
ask() {  # ask "<question>" y|n
  _q="$1"; _d="${2:-n}"
  [ "$ASSUME_YES" = 1 ] && return 0
  if [ "$DRY_RUN" = 1 ]; then
    say "  would ask: $_q  (taking the default: $_d)"
    [ "$_d" = y ]; return
  fi
  if ! tty_ok; then
    warn "no terminal to ask on — taking the default ($_d) for: $_q"
    warn "re-run with --yes to accept everything, or without a pipe to be asked"
    [ "$_d" = y ]; return
  fi
  if [ "$_d" = y ]; then _hint="[Y/n]"; else _hint="[y/N]"; fi
  printf '  %s %s ' "$_q" "$_hint" > /dev/tty
  read -r _a < /dev/tty || _a=""
  case "$_a" in
    [yY]*) _r=0 ;;
    [nN]*) _r=1 ;;
    "")    if [ "$_d" = y ]; then _r=0; else _r=1; fi ;;
    *)     _r=1 ;;
  esac
  if [ ! -t 1 ]; then
    if [ "$_r" = 0 ]; then say "  $_q yes"; else say "  $_q no"; fi
  fi
  return "$_r"
}
# "Enter to do it now, s to skip" — for the sign-ins, which need a browser and a person. Never
# under --yes (an unattended run has nobody to click Authorize) and never without a terminal.
offer() {  # offer "<prompt>"; 0 = do it now
  [ "$ASSUME_YES" = 1 ] && return 1
  [ "$DRY_RUN" = 1 ] && return 1
  tty_ok || return 1
  printf '     %s ' "$1" > /dev/tty
  read -r _a < /dev/tty || _a="s"
  case "$_a" in [sSnN]*) return 1 ;; *) return 0 ;; esac
}

# macOS ships /usr/bin/git and /usr/bin/python3 as shims that exist whether or not the Command Line
# Tools behind them do. `command -v` therefore ALWAYS finds them, and a genuinely clean machine
# failed inside `git clone` instead of being told what was missing. Ask xcode-select directly: it
# answers without popping the install dialog, which `git --version` would do during a mere
# detection pass.
usable() {
  have "$1" || return 1
  if on_mac; then
    case "$1" in git|python3) xcode-select -p >/dev/null 2>&1 ;; *) return 0 ;; esac
  fi
}
clt_present() { if on_mac; then xcode-select -p >/dev/null 2>&1; else return 0; fi; }
is_admin()    { id -Gn 2>/dev/null | tr ' ' '\n' | grep -qx admin; }

# The one password. Apple's Command Line Tools install through `softwareupdate`, which needs root;
# it is asked for here, once, at the start, and a background ticket keeps it valid for the length
# of the download — so nothing later in the run stops to ask for anything. Dropped again at exit.
SUDO_OK=0
SUDO_KEEPALIVE=""
get_sudo() {
  tty_ok || return 1
  say "  Your Mac password now — Apple's Command Line Tools (git) need it. Nothing else here does."
  if sudo -v -p '  Password: '; then
    SUDO_OK=1
    ( while kill -0 "$$" 2>/dev/null; do sudo -n true 2>/dev/null || exit 0; sleep 50; done ) &
    SUDO_KEEPALIVE=$!
    return 0
  fi
  warn "could not confirm the password — Apple's own installer window will be used instead."
  return 1
}
cleanup() {
  [ -n "$SUDO_KEEPALIVE" ] && kill "$SUDO_KEEPALIVE" 2>/dev/null
  [ "$SUDO_OK" = 1 ] && sudo -k 2>/dev/null
  return 0
}
trap cleanup EXIT

# Telling somebody to paste a line into a file they have never opened is not help, it is a
# handoff. The line is written here instead. What CANNOT be done from a child process is change
# the PATH of the terminal that launched it — no script can — so the terminal-only start step says
# to open a new window rather than pretending it already took effect.
user_shell_sees() { case ":$PATH_AS_INHERITED:" in *:"$1":*) return 0 ;; *) return 1 ;; esac; }
profile_rc() {
  case "$SHELL" in
    */bash) printf '%s' "$HOME/.bash_profile" ;;
    */fish) printf '' ;;   # fish has its own syntax and its own config; not ours to guess at
    *)      printf '%s' "$HOME/.zshrc" ;;
  esac
}
# Look for what we WRITE as well as the expanded path: our line says $HOME/.local/bin, Claude's and
# agy's installers write the expanded form. Any of them will do — the folder is the same.
profile_has() {
  _prc="$(profile_rc)"
  [ -n "$_prc" ] && [ -f "$_prc" ] || return 1
  case "$1" in
    "$HOME"/*) _pw="\$HOME/${1#"$HOME"/}" ;;
    *)         _pw="$1" ;;
  esac
  grep -qF "$_pw" "$_prc" 2>/dev/null || grep -qF "$1" "$_prc" 2>/dev/null
}
FISH_PATH_HINT=""
add_to_path() {
  _dir="$1"
  _rc="$(profile_rc)"
  if [ -z "$_rc" ]; then FISH_PATH_HINT="fish_add_path $_dir"; return 0; fi
  # Silent when the line is already there — from an earlier run, or from Claude's or agy's own
  # installer, which both write one. Kept as literal $HOME when under the home directory, so the
  # profile stays portable between machines with different usernames.
  case "$_dir" in
    "$HOME"/*) _written="\$HOME/${_dir#"$HOME"/}" ;;
    *)         _written="$_dir" ;;
  esac
  if ! profile_has "$_dir"; then
    say ""
    say "  one line in $(pretty "$_rc"), so every new terminal finds $(pretty "$_dir")"
    run sh -c "printf '# added by the autosound installer\nexport PATH=\"$_written:\$PATH\"\n' >> '$_rc'"
  fi
  return 0
}

# REW is not ours to install, but it is the one thing without which nothing measures. Both facts
# feed the Start section: whether the app is here at all, and whether its API answers.
rew_api_on() { curl -fsS --max-time 2 -o /dev/null http://localhost:4735/version 2>/dev/null; }
rew_app_found() {
  on_mac || return 1
  for d in "/Applications/REW.app" "/Applications/REW/REW.app" "$HOME/Applications/REW.app" "$HOME/Applications/REW/REW.app"; do
    [ -d "$d" ] && return 0
  done
  # Anywhere else: Spotlight, by bundle id. Silent and fast when Spotlight is on; empty when off.
  [ -n "$(mdfind "kMDItemCFBundleIdentifier == 'roomeqwizard*'" 2>/dev/null | head -1)" ]
}
agy_status() {  # prints the account, or "set up", when the reviewer is already configured
  # Read off disk, not by running `agy`: the CLI is interactive — it opens its own screen and
  # waits — so there is nothing to ask it that does not take over the terminal.
  #
  # THREE signals, because the sign-in does not land in one place. The first version of this
  # looked only at `oauth_creds.json` and still offered the sign-in on a Mac that had done it
  # (user, 2026-08-19) — that file is the shape Google's own `gemini` CLI writes, which agy is a
  # fork of and shares a config folder with; a machine with only agy on it need not have one.
  # So also: agy's own state file, which records that its setup screens have been walked, and an
  # API key in the environment, which is a way the reviewer runs just as well as a login.
  #
  # Only the ACCOUNT is ever read. No credential file is opened for its contents — the two
  # `[ -s ]` tests ask whether a file exists and is not empty, and nothing more.
  _a=""
  if [ -s "$HOME/.gemini/oauth_creds.json" ]; then
    _a="$(sed -n 's/.*"active": *"\([^"]*\)".*/\1/p' "$HOME/.gemini/google_accounts.json" \
          2>/dev/null | head -1)"
    printf '%s' "${_a:-set up}"
    return 0
  fi
  if grep -q 'agent_onboarding_completed: *true' \
       "$HOME/.gemini/antigravity/antigravity_state.pbtxt" 2>/dev/null; then
    printf 'set up'
    return 0
  fi
  if [ -n "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}" ]; then
    printf 'an API key in your environment'
    return 0
  fi
  return 1
}

claude_status() {  # prints "email (plan)" when signed in; fails otherwise
  _c="$(find_bin claude || true)"; [ -n "$_c" ] || return 1
  _s="$("$_c" auth status 2>/dev/null || true)"
  printf '%s' "$_s" | grep -q '"loggedIn": *true' || return 1
  _e="$(printf '%s' "$_s" | sed -n 's/.*"email": *"\([^"]*\)".*/\1/p' | head -1)"
  _p="$(printf '%s' "$_s" | sed -n 's/.*"subscriptionType": *"\([^"]*\)".*/\1/p' | head -1)"
  printf '%s%s' "${_e:-signed in}" "${_p:+ ($_p)}"
}

# ── uninstall ─────────────────────────────────────────────────────────────────
if [ "$UNINSTALL" = 1 ]; then
  step "Removing what this script installed"
  say "  Your PROJECT FOLDERS are never touched — not by this, not with --yes, not ever."
  say "  They hold measurements that took hours in a car and cannot be reproduced."
  say ""

  # The skill, but ONLY the checkout this script made. A symlink pointing anywhere else is
  # somebody's working tree and stays, for the same reason install refuses to overwrite it.
  if [ -L "$SKILL_HOME" ]; then
    target="$(readlink "$SKILL_HOME")"
    case "$target" in
      "$SKILL_SRC"/*)
        say "  removing the tuning method (the link and the checkout it points at)"
        run rm -f "$SKILL_HOME"
        run rm -rf "$SKILL_SRC"
        ;;
      *) warn "$SKILL_HOME points at $target — not ours, left alone" ;;
    esac
  elif [ -d "$SKILL_HOME" ]; then
    warn "$SKILL_HOME is a real directory this script did not create — left alone"
  else
    say "  no tuning method installed by this script"
  fi

  UV="$(find_bin uv || true)"
  if [ -n "$UV" ] && "$UV" tool list 2>/dev/null | grep -q '^autosound-tcc'; then
    say "  removing autosound-tcc"
    run "$UV" tool uninstall autosound-tcc
  else
    say "  autosound-tcc is not installed"
  fi
  if [ -d "$APP" ]; then say "  removing $(pretty "$APP")"; run rm -rf "$APP"; fi
  # The Desktop shortcut goes with it, or it stays behind pointing at nothing. Only if it is a
  # symlink — this script only ever makes one of those, and a real folder there is somebody else's.
  if [ -L "$DESKTOP_LINK" ]; then say "  removing the Desktop shortcut"; run rm -f "$DESKTOP_LINK"; fi

  # Without --all these stay, and each for a reason: the Python packages are shared with anything
  # else using that interpreter, Claude Code / agy / gh belong to their own installers and may be
  # in use for other work, and ~/.claude is the person's own configuration. --all exists for one
  # job — resetting a test machine to run the install again — so it asks first, in full sentences,
  # because on a working machine every line of it is a real loss.
  if [ "$REMOVE_ALL" = 1 ]; then
    USER_SITE="$(python3 -m site --user-base 2>/dev/null || true)"
    say ""
    say "  --all also removes, and none of these were made only for tuning:"
    say "    • uv, its downloaded Pythons, tools and cache   ~/.local/bin/uv, ~/.local/share/uv, ~/.cache/uv"
    say "    • Claude Code and ALL of its configuration, history, skills and plugins"
    say "                                                   ~/.claude, ~/.claude.json, ~/.local/share/claude"
    for t in agy gh omp; do
      manifest_has "$t" && say "    • $t, which this script installed, and its settings   ~/.local/bin/$t"
    done
    say "    • TCC's own settings and log                    ~/.config/autosound-tcc, ~/Library/Logs/autosound-tcc"
    [ -n "$USER_SITE" ] && say "    • every package you ever pip-installed with --user   $(pretty "$USER_SITE")"
    say ""
    say "  Your project folders are still untouched. Nothing below reaches them."
    if ask "Remove all of that too?" n; then
      # ONLY the copy this script would have installed — never a uv found elsewhere on PATH.
      if [ -e "$LOCAL_BIN/uv" ] || [ -d "$HOME/.local/share/uv" ]; then
        say "  removing uv from ~/.local, and its cache"
        run rm -rf "$LOCAL_BIN/uv" "$LOCAL_BIN/uvx" "$HOME/.local/share/uv" "$HOME/.cache/uv" "$HOME/.config/uv"
      elif [ -n "$UV" ]; then
        say "  leaving $UV alone — this script did not install it"
      fi
      # The native install keeps its versions under ~/.local/share/claude and its state in
      # ~/.claude.json; ~/.local/bin/claude is only the launcher. Removing the launcher alone left
      # 300 MB behind on a "reset" machine (sandbox, 2026-08-17).
      if [ -e "$LOCAL_BIN/claude" ] || [ -d "$HOME/.claude" ] || [ -d "$HOME/.local/share/claude" ]; then
        say "  removing Claude Code, ~/.claude and ~/.claude.json"
        run rm -rf "$LOCAL_BIN/claude" "$HOME/.claude" "$HOME/.claude.json" "$HOME/.local/share/claude" "$HOME/.cache/claude"
      fi
      for t in agy gh omp; do
        if manifest_has "$t" && [ -e "$LOCAL_BIN/$t" ]; then
          say "  removing $t"
          run rm -f "$LOCAL_BIN/$t"
          case "$t" in
            agy) run rm -rf "$HOME/.cache/antigravity" "$HOME/.gemini/antigravity-cli" ;;
            gh)  run rm -rf "$HOME/.config/gh" ;;
          esac
        elif [ -e "$LOCAL_BIN/$t" ]; then
          say "  leaving $(pretty "$LOCAL_BIN")/$t alone — this script did not install it"
        fi
      done
      if [ -d "$HOME/.config/autosound-tcc" ] || [ -d "$HOME/Library/Logs/autosound-tcc" ]; then
        say "  removing TCC's settings and log"
        run rm -rf "$HOME/.config/autosound-tcc" "$HOME/Library/Logs/autosound-tcc"
      fi
      if [ -n "$USER_SITE" ] && [ -d "$USER_SITE" ]; then
        say "  removing $(pretty "$USER_SITE")"
        run rm -rf "$USER_SITE"
      fi
      # We write this line, so we take it back. Only ours: found by the marker comment this script
      # puts above it, never by matching PATH lines generally — Claude's and agy's installers write
      # their own PATH lines and those are theirs.
      for _rc in "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc"; do
        if [ -f "$_rc" ] && grep -qF '# added by the autosound installer' "$_rc"; then
          say "  removing the PATH line this installer added to $(pretty "$_rc")"
          if [ "$DRY_RUN" = 0 ]; then
            _tmp="$(mktemp)"
            awk '/^# added by the autosound installer$/ { skip = 1; next }
                 skip == 1 { skip = 0; next }
                 { print }' "$_rc" > "$_tmp" && mv "$_tmp" "$_rc"
          fi
        fi
      done
      run rm -f "$MANIFEST"
      [ "$DRY_RUN" = 1 ] || rmdir "$(dirname "$MANIFEST")" 2>/dev/null || true
      # Named rather than deleted. `env`/`env.fish` are the cargo-dist PATH snippet, written by
      # uv's installer and by others of the same family, and nothing in the file says which.
      leftovers=""
      for f in env env.fish; do
        [ -e "$LOCAL_BIN/$f" ] && leftovers="$leftovers ~/.local/bin/$f"
      done
      say ""
      say "  Gone. The Command Line Tools stay: Apple's, and used by far more than this."
      if [ -n "$leftovers" ]; then
        say "  Left behind, on purpose:$leftovers — a PATH snippet uv writes, and so do other"
        say "  installers; nothing identifies whose it is, so it is yours to delete. It does"
        say "  nothing unless a shell sources it."
      fi
    else
      say "  Left alone."
    fi
  else
    say ""
    say "  Left in place on purpose: the Python packages (shared with everything else using that"
    say "  interpreter), Claude Code, agy, gh (their own installers own them), and ~/.claude (yours)."
    say "  Re-run with --uninstall --all to remove those too."
  fi
  say "  Every tuning project you have is untouched."
  exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# BLOCK 1 — look, ask, get the password. Everything a person has to do before the end is here.
# ═════════════════════════════════════════════════════════════════════════════
step "Autosound tuning — installer"

HAVE_CLT=1;    clt_present || HAVE_CLT=0
HAVE_CLAUDE=0; find_bin claude >/dev/null && HAVE_CLAUDE=1
HAVE_UV=0;     find_bin uv >/dev/null && HAVE_UV=1
HAVE_AGY=0;    find_bin agy >/dev/null && HAVE_AGY=1
HAVE_GH=0;     find_bin gh >/dev/null && HAVE_GH=1
HAVE_OMP=0;    find_bin omp >/dev/null && HAVE_OMP=1
REW_APP=0;     rew_app_found && REW_APP=1
REW_API=0;     rew_api_on && REW_API=1

say "  Already on this machine:"
if on_mac; then
  if [ "$HAVE_CLT" = 1 ]; then say "    ✓ Apple's Command Line Tools (git)"; else say "    – Apple's Command Line Tools (git)   will install"; fi
elif ! usable git; then
  step "git is required and is not installed"
  say "  Install git with your package manager, then run this again."
  exit 1
fi
if [ "$HAVE_CLAUDE" = 1 ]; then say "    ✓ Claude Code"; else say "    – Claude Code                        will install"; fi
if [ "$MODE" = "tcc" ]; then
  if [ "$HAVE_UV" = 1 ]; then say "    ✓ uv (installs the app's own Python)"; else say "    – uv, Python 3.12, the TCC app       will install"; fi
fi
if [ "$WANT_REVIEWER" = 1 ]; then
  if [ "$HAVE_AGY" = 1 ]; then say "    ✓ Gemini reviewer (agy)"; else say "    – Gemini reviewer (agy)              will install"; fi
fi
if [ "$REW_API" = 1 ]; then say "    ✓ REW, and its API is on"
elif [ "$REW_APP" = 1 ]; then say "    ✓ REW — its API is off; the last screen says where to switch it on"
elif on_mac; then say "    – REW not found — install a BETA from roomeqwizard.com/beta.html (the release has no API)"
fi

# One optional question, and it goes here because the answer changes the download list below.
# Private by default, never automatic: pushing somebody's car, DSP and measurements anywhere is an
# outward-facing action, and it needs their word (SCR-049).
# ...and only when there is something to decide. `gh` already on the machine means the answer was
# given on an earlier run (or by whoever installed it), and asking again on every re-run is a
# question with no download behind it — a re-run to fix an icon walked the person back through it
# (user, 2026-08-19). Nothing outward-facing rides on this: the installer never pushes a project
# anywhere; it installs a command, and that command is already here (SCR-049 is about the pushing).
if [ "$WANT_GITHUB" = "ask" ] && [ "$HAVE_GH" = 1 ]; then
  WANT_GITHUB=1
fi
if [ "$WANT_GITHUB" = "ask" ]; then
  say ""
  say "  Optional: back each car's record up to a free, private GitHub repository — the ledger of"
  say "  every setting, the journal, the DSP config backups. Weeks of decisions, a few kilobytes,"
  say "  and the one thing a dead disk does not give back. Needs a free GitHub account; installs"
  say "  GitHub's gh command. The measurements themselves stay on your disk either way."
  if ask "Back projects up to GitHub?" n; then WANT_GITHUB=1; else WANT_GITHUB=0; fi
fi

# ONE screen naming everything that will be downloaded, before any of it happens, while the person
# is still reading — not a prompt that arrives mid-scroll while somebody else's installer is
# printing, which collects a reflex `y` rather than a decision. Printed in a dry run too; only the
# question is skipped, since there is nothing to consent to when nothing will happen.
say ""
say "  This installs:"
_mb=100   # the method and its three Python packages
if [ "$HAVE_CLAUDE" = 0 ]; then
  say "    • Claude Code — the AI that runs the method              claude.ai"; _mb=$((_mb + 200))
fi
say "    • the tuning method — its references and tools           github.com/ayukhno/autosound-tuning-skill"
say "    • numpy, scipy, matplotlib — the method's own tools       pypi.org"
if [ "$MODE" = "tcc" ]; then
  if [ "$HAVE_UV" = 1 ]; then
    say "    • Autosound TCC — the desktop app, ~700 MB                github.com/ayukhno/autosound-tcc"
  else
    say "    • uv, a Python 3.12 of its own, and Autosound TCC —       astral.sh,"
    say "      the desktop app, ~700 MB together                       github.com/ayukhno/autosound-tcc"
  fi
  _mb=$((_mb + 700))
  on_mac && say "    • \"Autosound TCC.app\" in ~/Applications, and a shortcut to it on your Desktop"
fi
if [ "$WANT_REVIEWER" = 1 ] && [ "$HAVE_AGY" = 0 ]; then
  say "    • Gemini as the second AI, the reviewer — Google's agy   antigravity.google"; _mb=$((_mb + 100))
fi
if [ "$WANT_GITHUB" = 1 ] && [ "$HAVE_GH" = 0 ]; then
  say "    • gh, GitHub's command — for the project backup           github.com/cli/cli"; _mb=$((_mb + 50))
fi
if [ "$WANT_OMP" = 1 ] && [ "$HAVE_OMP" = 0 ]; then
  say "    • omp — offers TCC every non-Claude model (metered)       omp.sh"; _mb=$((_mb + 150))
fi
if on_mac && [ "$HAVE_CLT" = 0 ]; then
  say "    • Apple's Command Line Tools — git, about 1 GB             Apple; asks your Mac password once"
  _mb=$((_mb + 1000))
fi
say "    • one line in your shell profile, so a terminal can find what was installed"
say ""
if [ "$_mb" -ge 1000 ]; then _size="about $((_mb / 1000)).$(( (_mb % 1000) / 100 )) GB"; else _size="about $_mb MB"; fi
if on_mac && [ "$HAVE_CLT" = 0 ]; then
  say "  Everything goes into your home folder; Apple's tools go where Apple puts them. It signs"
  say "  you in nowhere — that comes at the end, in your browser — and never touches a project folder."
  say "  Downloads $_size; 10 to 20 minutes. After the password you can walk away."
else
  say "  Everything goes into your home folder. It signs you in nowhere — that comes at the end,"
  say "  in your browser — and never touches a project folder."
  say "  Downloads $_size; a few minutes. Nothing more is asked until the end."
fi
say ""
_opts=""
[ "$MODE" = "tcc" ]       && _opts="$_opts --terminal (no app),"
[ "$WANT_REVIEWER" = 1 ]  && _opts="$_opts --no-reviewer,"
[ "$WANT_GITHUB" = 1 ]    && _opts="$_opts --no-github,"
[ "$WANT_OMP" = 1 ]       && _opts="$_opts --no-omp,"
if [ -n "$_opts" ]; then
  say "  To leave something out, answer n and re-run with an option:${_opts%,}. --help lists them all."
fi
if [ "$DRY_RUN" = 0 ]; then
  # Consent given once, in full. Nothing below asks again until the sign-ins, which are offers,
  # not questions — and `ASSUME_YES` is left as the person set it, because "yes to every question"
  # is also what tells the sign-in block to print commands instead of opening a browser (setting it
  # here made every interactive install end with "run this later", 2026-08-17).
  if ! ask "Go ahead?" n; then
    say ""
    say "  Nothing installed. Re-run when you want to."
    exit 0
  fi
fi

# Everything below lands in ~/.local/bin, and every installer that follows checks whether that
# folder is on PATH — Claude's prints a "run this echo >> ~/.zshrc" note when it is not, uv's and
# omp's say the same in their words. Putting it on THIS script's PATH first keeps them quiet and
# lets each later step call what the earlier one installed. The person's own shell is a separate
# question, answered by `add_to_path` at the end and by `PATH_AS_INHERITED` in the checks.
[ "$DRY_RUN" = 1 ] || mkdir -p "$LOCAL_BIN" 2>/dev/null || true
export PATH="$LOCAL_BIN:$PATH"

# The password, right after the consent and before anything downloads — so the one interruption
# comes while the person is still at the keyboard, not twelve minutes in.
if on_mac && [ "$HAVE_CLT" = 0 ]; then
  if [ "$DRY_RUN" = 1 ]; then
    say "  would ask for your Mac password (for the Command Line Tools)"
  elif is_admin; then
    get_sudo || true
  else
    say "  This account is not an administrator, so Apple's own installer window will be used"
    say "  for the Command Line Tools — it may ask for an administrator's name and password."
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# UNATTENDED — from here to the checks, nothing needs a person.
# ═════════════════════════════════════════════════════════════════════════════

# ── Apple's Command Line Tools: git, and the python3 behind the shim ──────────
if on_mac && [ "$HAVE_CLT" = 0 ]; then
  step "Apple's Command Line Tools (git)"
  if [ "$DRY_RUN" = 1 ]; then
    say "  would run: softwareupdate -l, then softwareupdate -i \"Command Line Tools for Xcode-…\" (as administrator)"
    say "  and if that finds nothing: xcode-select --install, waiting for the window to finish"
  else
    if [ "$SUDO_OK" = 1 ]; then
      # The same route Homebrew's installer takes: a placeholder file makes `softwareupdate` list
      # the Command Line Tools, and `-i` installs them with no window and no click.
      say "  Asking Apple's servers which version to install — this can take a minute…"
      _ph="/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress"
      sudo touch "$_ph" 2>/dev/null || true
      _label="$(softwareupdate -l 2>/dev/null \
                 | grep -B 1 -E 'Command Line Tools' \
                 | awk -F'*' '/^ *\*/ {print $2}' \
                 | sed -e 's/^ *Label: //' -e 's/^ *//' \
                 | sort -V | tail -n1)" || _label=""
      if [ -n "$_label" ]; then
        say "  Installing \"$_label\" — 5 to 15 minutes, nothing to do meanwhile."
        sudo softwareupdate -i "$_label" || true
        sudo xcode-select --switch /Library/Developer/CommandLineTools 2>/dev/null || true
      else
        warn "Apple's servers did not list the Command Line Tools — using the installer window instead."
      fi
      sudo rm -f "$_ph" 2>/dev/null || true
    fi
    if ! clt_present; then
      say "  Apple's own installer window opens now. Click Install, then Agree, and let it finish —"
      say "  this waits for it. (Do not pick \"Get Xcode\": that is 12 GB and not needed.)"
      xcode-select --install >/dev/null 2>&1 || true
      _waited=0
      until clt_present; do
        sleep 10; _waited=$((_waited + 10))
        [ $((_waited % 120)) -eq 0 ] && say "  still waiting for the Command Line Tools… ($((_waited / 60)) min)"
        if [ "$_waited" -ge 2400 ]; then
          warn "40 minutes and no Command Line Tools. When that window has finished, run the same"
          warn "install line again — everything already downloaded stays."
          exit 1
        fi
      done
    fi
    say "  ✓ installed"
  fi
fi

# ── Claude Code ───────────────────────────────────────────────────────────────
step "Claude Code"
CLAUDE_BIN="$(find_bin claude || true)"
if [ -n "$CLAUDE_BIN" ]; then
  say "  ✓ $("$CLAUDE_BIN" --version 2>/dev/null || echo present)"
else
  say "  the official installer, claude.ai/install.sh:"
  if run sh -c 'curl -fsSL https://claude.ai/install.sh | sh'; then
    in_local_bin claude && manifest_add claude
  else
    warn "Claude Code did not install. Nothing can run a session without it; when the network is"
    warn "back:  curl -fsSL https://claude.ai/install.sh | sh"
  fi
  CLAUDE_BIN="$(find_bin claude || true)"
fi

# ── the tuning method ─────────────────────────────────────────────────────────
step "The tuning method"
if [ -z "$SKILL_REF" ]; then
  # The newest 3.x tag. Asked for by name rather than "main": main is where development lands,
  # and an installer should put you on a release unless you say otherwise.
  SKILL_REF="$(git ls-remote --tags --refs "$SKILL_REPO" 'v3.*' 2>/dev/null \
      | awk -F/ '{print $NF}' | sort -V | tail -1)" || SKILL_REF=""
  [ -z "$SKILL_REF" ] && SKILL_REF="main"
fi
say "  version $SKILL_REF"

ours=0
if [ -L "$SKILL_HOME" ]; then
  target="$(cd "$(dirname "$SKILL_HOME")" && readlink "$SKILL_HOME")"
  case "$target" in "$SKILL_SRC"/*) ours=1 ;; esac
fi
if [ -L "$SKILL_HOME" ] && [ "$ours" = 0 ]; then
  # Somebody's own working tree, wired up on purpose. Leave it, say so, move on.
  warn "$SKILL_HOME is a symlink to $(readlink "$SKILL_HOME")"
  warn "left exactly as it is — that is somebody's checkout, not this script's to replace"
elif [ -d "$SKILL_HOME" ] && [ ! -L "$SKILL_HOME" ]; then
  warn "$SKILL_HOME is a real directory this script did not create — left alone."
  warn "move it aside and re-run if you want this script to manage it."
elif [ -d "$SKILL_SRC/.git" ]; then
  say "  already installed — updating to $SKILL_REF"
  # Fetch the ref BY NAME. The checkout was made with `--depth 1 --branch <tag>`, so it contains
  # that tag and nothing else; FETCH_HEAD is whatever was just fetched, so this handles a tag, a
  # branch or a sha the same way (2026-08-13).
  run git -C "$SKILL_SRC" fetch --quiet --depth 1 origin "$SKILL_REF"
  run git -c advice.detachedHead=false -C "$SKILL_SRC" checkout --quiet FETCH_HEAD
else
  say "  into ~/.claude/skills/autosound-tuning"
  if [ "$DRY_RUN" = 0 ]; then mkdir -p "$(dirname "$SKILL_HOME")"; fi
  # Not `run`, because this one call needs its stderr filtered. A shallow clone of an ANNOTATED
  # tag makes git print `warning: refs/tags/vX.Y.Z <sha> is not a commit!` — it is complaining
  # that the tag OBJECT is not a commit, which is what an annotated tag is. Verified harmless.
  # Dropped because the word "warning" during a first install reads as something the person did
  # wrong. Every other line of stderr survives, and a real failure still stops the script.
  if [ "$DRY_RUN" = 1 ]; then
    say "  would run: git clone --branch $SKILL_REF --depth 1 $SKILL_REPO $(pretty "$SKILL_SRC")"
  else
    _err="$(mktemp)"
    if git -c advice.detachedHead=false clone --quiet --branch "$SKILL_REF" --depth 1 \
         "$SKILL_REPO" "$SKILL_SRC" 2>"$_err"; then
      grep -v 'is not a commit!' "$_err" >&2 || true
    else
      cat "$_err" >&2; rm -f "$_err"
      echo "clone failed — see above" >&2; exit 1
    fi
    rm -f "$_err"
    rm -f "$SKILL_HOME"
    ln -s "$SKILL_SRC/skills/autosound-tuning" "$SKILL_HOME"
  fi
fi

# ── what the method's own tools need ──────────────────────────────────────────
# The reason this script exists, ahead of anything about models (INSTALLER-TZ §0): put the wall
# up front instead of letting it arrive mid-tune. `numpy` is imported at module scope by five of
# the tools — without it they do not import at all. `scipy` and `matplotlib` are lazy, and cost
# one feature rather than a session.
step "What the method's tools need (numpy, scipy, matplotlib)"
# Resolve through the symlink when there is one. The `|| SKILL_REAL=` is load-bearing: under
# `set -e` an assignment whose command substitution fails takes the whole script down, and on a
# machine with no ~/.claude/skills yet — every clean install, and EVERY --dry-run — the first `cd`
# fails (found on a clean M1, 2026-08-13).
SKILL_REAL="$(cd "$(dirname "$SKILL_HOME")" 2>/dev/null && cd "$(readlink "$SKILL_HOME" 2>/dev/null || echo "$SKILL_HOME")" 2>/dev/null && pwd)" || SKILL_REAL=""
REQS="${SKILL_REAL:-$SKILL_HOME}/requirements.txt"
[ -f "$REQS" ] || REQS="$SKILL_HOME/requirements.txt"
if [ ! -f "$REQS" ] && [ "$DRY_RUN" != 1 ]; then
  warn "no requirements.txt beside the method — skipping (nothing to install from)"
elif [ "$DRY_RUN" = 1 ] && on_mac && [ "$HAVE_CLT" = 0 ]; then
  # In a dry run on a Mac with no Command Line Tools there is no python3 to name yet — the tools
  # above would have brought Apple's. Describe the plan rather than the machine.
  say "  would run: python3 -m pip install --user -r requirements.txt  (Apple's python3, once the tools above are in)"
elif ! usable python3; then
  warn "no python3 — the method's tools cannot run at all until there is one"
else
  # WHICH interpreter: the one `python3` resolves to, because that is literally how the method
  # invokes its tools (`python3 rew_tool/...`). Not TCC's venv — different process.
  # HOW depends on what that interpreter is. On a stock Mac it is Apple's 3.9 at /usr/bin/python3,
  # whose site-packages live under /Library and need root — `--user` writes to ~/Library/Python
  # instead, which that interpreter already has on its path. Inside a venv the reverse holds:
  # `--user` is refused outright. So ask the interpreter which it is.
  PY_BIN="$(command -v python3)"
  say "  into $PY_BIN ($("$PY_BIN" -V 2>&1))"
  if "$PY_BIN" -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)' 2>/dev/null; then
    run "$PY_BIN" -m pip install --quiet --no-warn-script-location --disable-pip-version-check -r "$REQS" \
      || warn "install failed — see above"
  else
    run "$PY_BIN" -m pip install --quiet --user --no-warn-script-location --disable-pip-version-check -r "$REQS" \
      || warn "install failed — see above"
  fi
fi

# ── the desktop app ───────────────────────────────────────────────────────────
TCC_BIN=""
UV=""
if [ "$MODE" = "tcc" ]; then
  step "Autosound TCC — the desktop app"
  UV="$(find_bin uv || true)"
  if [ -n "$UV" ]; then
    say "  ✓ $("$UV" --version 2>/dev/null || echo uv) — installs the app's own Python"
  else
    say "  uv first (astral.sh/uv/install.sh) — it brings a Python 3.12 of its own, so nothing on"
    say "  this machine has to be the right version:"
    if run sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --quiet'; then
      export PATH="$LOCAL_BIN:$PATH"
      in_local_bin uv && manifest_add uv
      UV="$(find_bin uv || true)"
    else
      warn "uv did not install; without it there is no app. Carrying on with the method alone,"
      warn "which is fully usable — the app can be added by re-running this later."
      MODE="terminal"
    fi
  fi
fi
if [ "$MODE" = "tcc" ]; then
  say "  the app and what it needs, about 700 MB — a few minutes, no output until it is done…"
  # `--python` is not optional here. Without it `uv tool install` used the system interpreter —
  # 3.9.6 on a stock macOS — and refused with "does not satisfy Python>=3.11", which reads as a
  # broken package rather than a missing Python (2026-08-12).
  [ -n "$UV" ] || UV=uv
  if run "$UV" tool install --quiet --python 3.12 --upgrade "autosound-tcc[gui,claude] @ git+${TCC_REPO}"; then
    # Where uv actually put it, which is not always `~/.local/bin`.
    TCC_BIN="$(command -v autosound-tcc 2>/dev/null || true)"
    [ -z "$TCC_BIN" ] && [ -x "${UV_TOOL_BIN_DIR:-$LOCAL_BIN}/autosound-tcc" ] \
        && TCC_BIN="${UV_TOOL_BIN_DIR:-$LOCAL_BIN}/autosound-tcc"
    [ "$DRY_RUN" = 1 ] || say "  ✓ installed"
  else
    warn "the app did not install — see above. The method alone still works; re-run this later"
    warn "to add the app."
  fi

  if on_mac; then
    # NOT relative to $0: under `curl … | bash` that is "bash", so dirname gives whatever folder the
    # person happened to be standing in (found on a clean M1, 2026-08-13). The clone above always
    # has the builder.
    builder="$SKILL_SRC/scripts/make-macos-app.sh"
    [ -f "$builder" ] || builder="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/scripts/make-macos-app.sh"
    if [ "$DRY_RUN" = 1 ]; then
      say "  would build \"$(pretty "$APP")\" and a shortcut on your Desktop"
    elif [ -x "$builder" ] && [ -n "$TCC_BIN" ]; then
      # The builder's own report (path, unsigned-and-that-is-fine) is for whoever runs it by hand;
      # here one line says the same thing. Its one note worth passing on is a missing icon.
      _bout="$("$builder" "$HOME/Applications" "$TCC_BIN" 2>&1)" && _brc=0 || _brc=$?
      if [ "$_brc" = 0 ]; then
        _shortcut=""
        # A symlink rather than a Finder alias: it double-clicks the same, and `rm` removes it.
        # Made AFTER the builder has registered the bundle with Launch Services, and touched
        # afterwards: Finder draws a shortcut from the target's registered icon, so a link made
        # before the registration is a link drawn with the blank placeholder — which is exactly
        # what a second Mac showed on a clean install (user, 2026-08-19).
        # An EXISTING shortcut of ours is replaced, not left alone. Finder caches an icon against
        # the item that has it, so a link first drawn when the bundle had no icon keeps the blank
        # tile even after the bundle is fixed and registered — it took a Get Info to refresh
        # (user, 2026-08-19, re-running with the icon fix in). A link made a moment ago is an item
        # Finder has never drawn, so it asks Launch Services, which now has the answer.
        # Only ever a SYMLINK, and only one pointing at our own app: anything else on the Desktop
        # under that name is somebody's file and stays.
        if [ -L "$DESKTOP_LINK" ] && [ "$(readlink "$DESKTOP_LINK")" = "$APP" ]; then
          rm -f "$DESKTOP_LINK"
        fi
        if [ -d "$HOME/Desktop" ] && [ ! -e "$DESKTOP_LINK" ] && [ ! -L "$DESKTOP_LINK" ]; then
          ln -s "$APP" "$DESKTOP_LINK" 2>/dev/null && _shortcut=", and a shortcut on your Desktop"
        elif [ -L "$DESKTOP_LINK" ]; then
          _shortcut=", and the shortcut on your Desktop"
        fi
        say "  ✓ \"Autosound TCC.app\" in ~/Applications$_shortcut"
        # A warning, not an aside in brackets. It used to be one, and it scrolled past unread on
        # the one install where it mattered: the person sees a blank white icon days later and has
        # no way back to the line that explained it (user, 2026-08-19).
        case "$_bout" in
          *"no icon"*)
            warn "the app has no icon — TCC's own was not found in the installed package."
            warn "Everything works; to fix just the icon, re-run this installer."
            ;;
        esac
      else
        printf '%s\n' "$_bout" >&2
        warn "the double-clickable app was not built; the command still works:  autosound-tcc"
      fi
    elif [ -n "$TCC_BIN" ]; then
      warn "no app builder at $builder — the command still works:  autosound-tcc"
    fi
  fi
fi

# ── the reviewer: Gemini, through Google's own CLI ────────────────────────────
AGY_BIN=""
if [ "$WANT_REVIEWER" = 1 ]; then
  step "Gemini as the second AI — Google's Antigravity CLI (agy)"
  AGY_BIN="$(find_bin agy || true)"
  if [ -n "$AGY_BIN" ]; then
    say "  ✓ already here: $(pretty "$AGY_BIN")"
  else
    # Google's own installer: a signed binary into ~/.local/bin, quarantine cleared by the script
    # itself, no package manager and no password. It also writes a PATH line to the shell profile.
    # Its output is kept back until it is done: it logs its own setup through glog, so every
    # ordinary line arrives prefixed "ERROR: logging before google.Init" — five lines that read as
    # five failures to somebody who has just been told to trust this. On success one line says
    # what happened; on failure the whole transcript is shown, since then it is the evidence.
    say "  the official installer, antigravity.google/cli/install.sh (about a minute)…"
    if [ "$DRY_RUN" = 1 ]; then
      say "  would run: sh -c curl -fsSL https://antigravity.google/cli/install.sh | bash"
    else
      _out="$(mktemp)"
      if sh -c 'curl -fsSL https://antigravity.google/cli/install.sh | bash' >"$_out" 2>&1 && in_local_bin agy; then
        manifest_add agy
        AGY_BIN="$LOCAL_BIN/agy"
        _v="$(sed -n 's/.*Latest available version: *//p' "$_out" | head -1)"
        say "  ✓ agy${_v:+ $_v} → $(pretty "$LOCAL_BIN")/agy"
      else
        cat "$_out" >&2
        warn "the reviewer did not install. The tune works without it — reviews go to the clipboard —"
        warn "and it can be added later:  curl -fsSL https://antigravity.google/cli/install.sh | bash"
      fi
      rm -f "$_out"
    fi
  fi
fi

# ── omp: with the app, unless it was turned down ──────────────────────────────
if [ "$WANT_OMP" = 1 ]; then
  step "omp — every non-Claude model for TCC's picker (metered)"
  if find_bin omp >/dev/null; then
    say "  ✓ already here"
  elif run sh -c 'curl -fsSL https://omp.sh/install.sh | sh'; then
    in_local_bin omp && manifest_add omp
  else
    warn "omp did not install; TCC's picker offers Claude, and Gemini through agy, without it."
  fi
fi

# ── gh: only when asked ───────────────────────────────────────────────────────
GH_BIN=""
if [ "$WANT_GITHUB" = 1 ]; then
  step "gh — GitHub's command, for the project backup"
  GH_BIN="$(find_bin gh || true)"
  if [ -n "$GH_BIN" ]; then
    say "  ✓ already here: $(pretty "$GH_BIN")"
  elif [ "$DRY_RUN" = 1 ]; then
    say "  would download the newest gh release from github.com/cli/cli into $(pretty "$LOCAL_BIN")/gh"
  else
    # Straight from GitHub's releases: a signed binary, no package manager. The `latest` page
    # redirects to the current tag, which names the file.
    _ver="$(curl -fsSLI -o /dev/null -w '%{url_effective}' https://github.com/cli/cli/releases/latest 2>/dev/null \
              | sed 's#.*/tag/v##')" || _ver=""
    case "$(uname -m)" in arm64|aarch64) _arch=arm64 ;; *) _arch=amd64 ;; esac
    _tmp="$(mktemp -d)"
    _got=0
    if [ -n "$_ver" ]; then
      if on_mac; then
        _asset="gh_${_ver}_macOS_${_arch}.zip"
        curl -fsSL -o "$_tmp/$_asset" "https://github.com/cli/cli/releases/download/v${_ver}/${_asset}" \
          && unzip -q "$_tmp/$_asset" -d "$_tmp" && _got=1
      else
        _asset="gh_${_ver}_linux_${_arch}.tar.gz"
        curl -fsSL -o "$_tmp/$_asset" "https://github.com/cli/cli/releases/download/v${_ver}/${_asset}" \
          && tar -xzf "$_tmp/$_asset" -C "$_tmp" && _got=1
      fi
    fi
    if [ "$_got" = 1 ] && mkdir -p "$LOCAL_BIN" && cp "$_tmp"/gh_*/bin/gh "$LOCAL_BIN/gh" 2>/dev/null; then
      chmod +x "$LOCAL_BIN/gh"
      manifest_add gh
      GH_BIN="$LOCAL_BIN/gh"
      say "  ✓ gh $_ver → $(pretty "$LOCAL_BIN")/gh"
    else
      warn "gh did not download. The backup can be set up later; see the last screen."
    fi
    rm -rf "$_tmp"
  fi
fi

# ── one PATH line, for every terminal opened from now on ──────────────────────
# Everything above went into ~/.local/bin. Claude's and agy's installers write a PATH line for it
# themselves; this covers the machine where neither ran (both already present, or --terminal with
# --no-reviewer). Silent when a line is already there, whoever wrote it.
if ! user_shell_sees "$LOCAL_BIN"; then add_to_path "$LOCAL_BIN"; fi

# ═════════════════════════════════════════════════════════════════════════════
# BLOCK 2 — check, sign in, start. The rest of what a person does, in one place.
# ═════════════════════════════════════════════════════════════════════════════
step "Checking"
ok=1
[ "$DRY_RUN" = 1 ] && say "  (the machine as it stands — nothing above was actually done)"
if [ -f "$SKILL_HOME/rew_tool/contract.py" ]; then
  if python3 -c "import numpy" 2>/dev/null; then
    say "  ✓ the tuning method (3.x), and its tools load"
  else
    say "  ✓ the tuning method (3.x)"
    warn "numpy is NOT importable by $(command -v python3 || echo python3): crossover selection,"
    warn "the EQ gate, the DSP maths and plot rendering will fail when the method reaches them."
    ok=0
  fi
elif [ -f "$SKILL_HOME/rew_tool/rew_api.py" ]; then
  warn "the skill at $SKILL_HOME is the 2.x line — TCC cannot drive it"
  ok=0
elif [ "$DRY_RUN" = 0 ]; then
  warn "no tuning method at $SKILL_HOME"
  ok=0
fi
if [ "$MODE" = "tcc" ] && [ "$DRY_RUN" = 0 ]; then
  if on_mac && [ -d "$APP" ]; then
    _where="in ~/Applications"; [ -L "$DESKTOP_LINK" ] && _where="$_where, and on your Desktop"
    say "  ✓ Autosound TCC — \"Autosound TCC.app\" $_where"
  elif [ -n "$TCC_BIN" ] || find_bin autosound-tcc >/dev/null; then
    say "  ✓ Autosound TCC — the command:  autosound-tcc"
  else
    warn "Autosound TCC is not installed"
    ok=0
  fi
fi
CLAUDE_BIN="$(find_bin claude || true)"
if [ -n "$CLAUDE_BIN" ]; then
  say "  ✓ Claude Code"
elif [ "$DRY_RUN" = 0 ]; then
  warn "Claude Code is not installed; nothing can run a session without it"
  ok=0
fi
if [ "$WANT_REVIEWER" = 1 ] && [ "$DRY_RUN" = 0 ]; then
  AGY_BIN="$(find_bin agy || true)"
  if [ -n "$AGY_BIN" ]; then
    say "  ✓ Gemini reviewer (agy) — installed; sign in below"
  else
    say "  – no Gemini reviewer; reviews fall back to the clipboard, which works"
  fi
fi
if [ "$WANT_GITHUB" = 1 ] && [ "$DRY_RUN" = 0 ]; then
  GH_BIN="$(find_bin gh || true)"
  if [ -n "$GH_BIN" ]; then say "  ✓ gh — for the project backup"; else say "  – gh did not install; see the last screen"; fi
fi
if [ "$REW_API" = 1 ]; then say "  ✓ REW's API is on"
elif [ "$REW_APP" = 1 ]; then say "  – REW's API is off — switching it on is the first Start step"
elif on_mac; then say "  – REW not found — installing it is the first Start step"
fi
say ""
if [ "$DRY_RUN" = 1 ]; then
  say "Nothing was installed — this was a dry run."
elif [ "$ok" = 1 ]; then
  say "Installed."
else
  say "Installed, with the warnings above."
fi

# ── sign in ───────────────────────────────────────────────────────────────────
# Every first install on every machine ends here, and none of it can be done for the person: the
# sessions are theirs, not this tool's. So it happens now, in sequence, each step explained just
# before it runs — not as a line printed and lost inside eighty lines of install output, which is
# how `claude auth login` went uncarried-out on a real first install (2026-08-13).
CLAUDE_SIGNED=""
AGY_SKIPPED=0
GH_SKIPPED=0
# What the closing screens talk about: in a real run, what is on the machine now; in a dry run,
# what the plan would have put there — a dry run that reports "no reviewer" about a machine it
# was told not to touch describes the wrong thing.
REVIEWER_IN=0; { [ -n "$AGY_BIN" ] || { [ "$DRY_RUN" = 1 ] && [ "$WANT_REVIEWER" = 1 ]; }; } && REVIEWER_IN=1
GH_IN=0;       { [ -n "$GH_BIN" ]  || { [ "$DRY_RUN" = 1 ] && [ "$WANT_GITHUB" = 1 ]; }; }   && GH_IN=1
if [ "$DRY_RUN" = 1 ]; then
  step "Sign in — the part that is yours"
  say "  (a real run does this here, in order, each step explained before it runs:)"
  say "  1. Claude — required: the browser opens, you sign in and click Authorize"
  [ "$REVIEWER_IN" = 1 ] && say "  2. Gemini reviewer — optional: Enter runs agy's own sign-in, s skips it"
  [ "$GH_IN" = 1 ]       && say "  3. GitHub — optional: Enter runs gh auth login --web, s skips it"
else
  step "Sign in — the part that is yours"
  # Interactive when there is a person at a terminal; otherwise (--yes, or no terminal) each
  # step is the command to run later, in one line — an unattended run has nobody to click
  # Authorize, and a browser opening out of nowhere is worse than a line to copy.
  INTERACTIVE=0
  if [ "$ASSUME_YES" = 0 ] && tty_ok; then INTERACTIVE=1; fi
  n=1
  # 1. Claude — required.
  if [ -n "$CLAUDE_BIN" ]; then
    CLAUDE_SIGNED="$(claude_status || true)"
    if [ -n "$CLAUDE_SIGNED" ]; then
      say "  $n. Claude: ✓ signed in as $CLAUDE_SIGNED"
    elif [ "$INTERACTIVE" = 1 ]; then
      say "  $n. Claude — required. Your browser will open: sign in to your Claude account (a Pro or"
      say "     Max subscription is what runs the method) and click Authorize, then come back here."
      if offer "Enter opens the browser · s = later:"; then
        "$CLAUDE_BIN" auth login < /dev/tty || true
        CLAUDE_SIGNED="$(claude_status || true)"
        if [ -n "$CLAUDE_SIGNED" ]; then say "     ✓ signed in as $CLAUDE_SIGNED"
        else say "     – not signed in yet. Later, in a terminal:  claude auth login"; fi
      else
        say "     Later, in a terminal:  claude auth login"
      fi
    else
      say "  $n. Claude — required. In a terminal:  claude auth login"
      say "     (your browser opens; sign in to your Claude account — Pro or Max — and click Authorize)"
    fi
    n=$((n + 1))
  fi
  # 2. The reviewer — optional, once. Its first run is Google's own setup (colours, workspace
  # trust, the browser sign-in, and on some accounts a Project ID), so it is described in full
  # and then handed the terminal.
  _agy_seen="$(agy_status || true)"
  if [ -n "$AGY_BIN" ] && [ -n "$_agy_seen" ]; then
    # Already set up — the same courtesy Claude and GitHub get two steps either side of this one.
    # It used to offer the sign-in on every run, so a re-run to fix something else walked the
    # person back through Google's setup screens (user, 2026-08-19, re-running to fix an icon).
    #
    # Two sentences, because the three signals do not say the same thing: an account name is a
    # sign-in, the rest is "configured, and here is how to check". Claiming a sign-in this script
    # cannot see would be worse than one extra line.
    case "$_agy_seen" in
      *@*) say "  $n. Gemini reviewer: ✓ signed in as $_agy_seen" ;;
      *)   say "  $n. Gemini reviewer: ✓ already set up ($_agy_seen). To check it:  agy" ;;
    esac
    n=$((n + 1))
  elif [ -n "$AGY_BIN" ]; then
    say "  $n. Gemini reviewer — optional, once. Have a Google account ready. What happens:"
    say "       agy opens; press Enter through its two setup screens; your browser asks you to sign"
    say "       in with Google. If it then asks for a Project ID, copy it from"
    say "       aistudio.google.com/app/apikey (the ID, not the name). When it says you're in, type /quit"
    if [ "$INTERACTIVE" = 1 ] && offer "Enter = sign in now · s = later:"; then
      "$AGY_BIN" < /dev/tty || true
      say "     Done. If it ever answers with \"Agent Platform API has not been used\", the message"
      say "     carries a link — open it, press Enable, wait a minute."
    else
      AGY_SKIPPED=1
      say "     Later, in a terminal:  agy"
    fi
    n=$((n + 1))
  fi
  # 3. GitHub — optional.
  if [ -n "$GH_BIN" ]; then
    if "$GH_BIN" auth status >/dev/null 2>&1; then
      say "  $n. GitHub: ✓ signed in"
    else
      say "  $n. GitHub — optional. Your browser opens with a one-time code; sign in and paste it."
      if [ "$INTERACTIVE" = 1 ] && offer "Enter = sign in now · s = later:"; then
        "$GH_BIN" auth login --hostname github.com --git-protocol https --web < /dev/tty || true
      else
        GH_SKIPPED=1
        say "     Later, in a terminal:  gh auth login --web"
      fi
    fi
    n=$((n + 1))
  fi
fi

# ── start ─────────────────────────────────────────────────────────────────────
step "Start"
n=1
if [ "$REW_API" = 0 ]; then
  if [ "$REW_APP" = 1 ] || ! on_mac; then
    say "  $n. In REW: Preferences → API: tick \"Start the API when REW starts\" and press \"Start server\"."
    say "     The panel then reads \"API server is running on port 4735\" — no restart needed. Nothing"
    say "     measures without it."
    # The one that costs an evening: the API is a beta feature, and Preferences has no API tab at
    # all in the release build. Somebody who searched the web for REW has the release build and is
    # now looking for a tab that is not there (user, on Windows, 2026-08-19).
    say "     No \"API\" tab there? That is the RELEASE build (V5.31.3), which has no API. Get a beta:"
    say "     roomeqwizard.com/beta.html — the downloads are at AV NIRVANA, the REW forum."
  else
    say "  $n. Install REW — and it must be a BETA build: the release version (V5.31.3, July 2024)"
    say "     has no API at all, and that is the one a web search gives you. roomeqwizard.com/beta.html,"
    say "     downloads hosted at AV NIRVANA. Then in REW: Preferences → API: tick \"Start the API"
    say "     when REW starts\" and press \"Start server\". Nothing measures without it."
  fi
  n=$((n + 1))
fi
if [ "$MODE" = "tcc" ]; then
  if on_mac; then
    say "  $n. Double-click \"Autosound TCC\" on your Desktop."
  else
    say "  $n. Open a NEW terminal window and run:  autosound-tcc"
  fi
  say "     Browse… to a folder for the car — a new, empty one is right; everything about that car"
  say "     will live in it (for instance Autosound/my-car in your home folder)."
  say "     AI main: the Claude Opus line (SDK) · AI critic: the Gemini Pro (High) line. Open."
  n=$((n + 1))
  say "  $n. In the panel on the right, say what you want, in any language:"
  say "     \"let's tune this car from scratch\"."
else
  say "  $n. Open a NEW Terminal window — this one cannot see what was just installed — and run:"
  say "          mkdir -p ~/Autosound/my-car && cd ~/Autosound/my-car"
  say "          claude"
  n=$((n + 1))
  say "  $n. Say what you want, in any language: \"tune a new car from scratch\"."
fi
[ -n "$FISH_PATH_HINT" ] && say "  (your shell is fish — first:  $FISH_PATH_HINT)"

# ── when you have time ────────────────────────────────────────────────────────
step "When you have time"
if [ "$REVIEWER_IN" = 1 ]; then
  say "  • Check the reviewer really answers — finding the command is not the same as it working:"
  say "        $(pretty "$SKILL_HOME")/scripts/gemini_critic.sh --doctor"
  [ "$AGY_SKIPPED" = 1 ] && say "    (it needs the sign-in above first:  agy)"
elif [ "$WANT_REVIEWER" = 1 ]; then
  say "  • A second AI as reviewer is where most of the value is. Add it later:"
  say "        curl -fsSL https://antigravity.google/cli/install.sh | bash"
  say "    then sign in once with:  agy"
else
  say "  • A second AI as reviewer is where most of the value is (you passed --no-reviewer):"
  say "        curl -fsSL https://antigravity.google/cli/install.sh | bash"
fi
if [ "$GH_IN" = 1 ]; then
  [ "$GH_SKIPPED" = 1 ] && say "  • GitHub backup — sign in once:  gh auth login --web"
  # A how-to, not a promise: nothing in the method scripts this step yet (SCR-049), so the person
  # — or the AI, on their word — runs it. Private, and only ever on their say-so.
  say "  • Back a car up once its folder exists — say to the AI: \"back this project up to a private"
  say "    GitHub repository\". It knows what stays out (the sweeps) and uses gh for the rest."
elif [ "$WANT_GITHUB" = 0 ]; then
  say "  • Backing a car's record up to a private GitHub repository is free insurance against a"
  say "    dead disk. Re-run this line with --github when you want it."
fi
say "  • Update everything: run this same install line again."

# Last thing on screen: where this came from and where to say something about it. Somebody who
# has just installed two programs from a URL they were told to trust should not have to search for
# the projects they now have on their disk (user, after a clean install, 2026-08-13).
step "Where this lives"
say "  the tuning method   $SKILL_REPO_URL"
say "  the desktop app     $TCC_REPO"
say "  something wrong, or an idea — open an issue in whichever of the two it belongs to."
say ""
