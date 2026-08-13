#!/usr/bin/env bash
# Autosound tuning — installer for macOS and Linux.
#
# Two things can be installed and they are separate on purpose:
#
#   1. the SKILL      — the tuning method. Plain Python, and its own `requirements.txt`: `numpy`
#                       is imported at module scope by five of its tools, so they do not load
#                       without it. Works on its own, in a terminal, with no desktop app.
#   2. the SKILL + TCC — plus the Tuning Command Center, the desktop app that shows the project's
#                       state and curves while a session runs. It never works without the skill.
#
# What this script will not do, and will not pretend to:
#
#   * log you in. TCC and the skill drive YOUR authenticated `claude` session; per the Agent SDK's
#     terms a product may not offer a claude.ai login of its own. Step 1 is always yours.
#   * install anything from the network without asking first.
#   * touch an existing skill directory it did not create — a symlink there is somebody's working
#     tree, and replacing it under them would be worse than the problem this solves.
#
# Usage:
#   ./install.sh                     ask which of the two
#   ./install.sh --terminal          the skill only
#   ./install.sh --tcc               the skill and the desktop app
#   ./install.sh --dry-run           say what it would do, change nothing
#   ./install.sh --skill-ref v3.0.0  a specific skill version (default: the newest 3.x tag)
#   ./install.sh --uninstall         remove what this script installed — NEVER your projects
#   ./install.sh --uninstall --all   also remove uv, Claude Code and ~/.claude, and every
#                                    --user pip package. For resetting a test machine; on a
#                                    working one each of those is a real loss. Asks first.
set -euo pipefail

SKILL_REPO="https://github.com/ayukhno/autosound-tuning-skill.git"
TCC_REPO="https://github.com/ayukhno/autosound-tcc"
SKILL_HOME="${HOME}/.claude/skills/autosound-tuning"
# The repo lives beside the skill and the skill POINTS at it. Cloning and then moving the
# subdirectory out (the obvious way) leaves a plain folder with no `.git`, so a second run cannot
# update it and the user is stuck on whatever version they first installed — found by running this
# script twice (2026-08-12). A checkout plus a symlink also makes `git -C … checkout v3.0.1` the
# whole of an upgrade, and matches what the README already teaches for staying on 2.x.
SKILL_SRC="${HOME}/.claude/skills/.autosound-tuning-src"

MODE=""
UNINSTALL=0
REMOVE_ALL=0
# Saved before anything is installed: the uv step exports ~/.local/bin into THIS script's PATH so
# the rest of the run can call what it just installed. That made the summary print "✓
# autosound-tcc installed" to somebody whose own shell could not find it, because the check was
# asking the wrong PATH (2026-08-13).
PATH_AS_INHERITED="$PATH"
user_shell_sees() {
  case ":$PATH_AS_INHERITED:" in *:"$1":*) return 0 ;; *) return 1 ;; esac
}
DRY_RUN=0
SKILL_REF=""
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --terminal) MODE="terminal" ;;
    --uninstall) UNINSTALL=1 ;;
    --all)      REMOVE_ALL=1 ;;
    --tcc)      MODE="tcc" ;;
    --dry-run)  DRY_RUN=1 ;;
    --yes|-y)   ASSUME_YES=1 ;;
    --skill-ref) SKILL_REF="${2:-}"; shift ;;
    --help|-h)  sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '%s\n' "$*"; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

# Anything the person still has to do lands here instead of being announced mid-log. A single
# instruction inside eighty lines of install output is an instruction nobody carries out: the
# `claude auth login` line was printed and lost on a real first install (2026-08-13). One record
# per step: first line is the sentence, lines starting with ">" are commands to copy.
NEXT_STEPS="$(mktemp)"
trap 'rm -f "$NEXT_STEPS"' EXIT
# uv installs itself into ~/.local/bin, which is exactly the folder that is NOT on PATH on a fresh
# machine. Trusting `command -v uv` made --uninstall report "autosound-tcc not installed by uv"
# about a TCC it had installed twenty minutes earlier, and walk away leaving it there (2026-08-13).
UV=""
find_uv() {
  UV="$(command -v uv 2>/dev/null || true)"
  [ -n "$UV" ] || { [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"; }
  [ -n "$UV" ]
}

# Telling somebody to paste a line into a file they have never opened is not help, it is a
# handoff. The line is written here instead. What CANNOT be done from a child process is change
# the PATH of the terminal that launched it — no script can — so the next step says how to pick it
# up rather than pretending it already took effect.
PATH_STEP_ADDED=0
add_to_path() {
  _dir="$1"
  [ "$PATH_STEP_ADDED" = 1 ] && return 0   # the app and claude share ~/.local/bin; say it once
  PATH_STEP_ADDED=1
  case "$SHELL" in
    */bash) _rc="$HOME/.bash_profile" ;;
    */fish) _rc="" ;;   # fish has its own syntax and its own config; not ours to guess at
    *)      _rc="$HOME/.zshrc" ;;
  esac
  if [ -z "$_rc" ]; then
    next_step "Add $_dir to your PATH — your shell is fish, whose config this script will not" \
              "guess at:" \
              ">fish_add_path $_dir"
    return
  fi
  if [ -f "$_rc" ] && grep -qF '.local/bin' "$_rc" 2>/dev/null; then
    say "  $_rc already mentions .local/bin — not touching it"
  else
    # Write the directory we were ASKED about, not a hardcoded one — announcing
    # "adding /opt/homebrew/bin" and then writing ~/.local/bin is how a fix becomes a lie.
    # Kept as literal $HOME when it is under the home directory, so the profile stays portable
    # between machines with different usernames.
    case "$_dir" in
      "$HOME"/*) _written="\$HOME/${_dir#$HOME/}" ;;
      *)         _written="$_dir" ;;
    esac
    say "  adding $_dir to $_rc"
    run sh -c "printf '\n# added by the autosound installer\nexport PATH=\"$_written:\$PATH\"\n' >> '$_rc'"
  fi
  next_step "Pick up the change. A script cannot alter the PATH of the terminal that started it," \
            "so this shell still cannot find what was installed — open a new terminal, or run:" \
            ">source $_rc"
}

next_step() { printf '@@\n' >> "$NEXT_STEPS"; for l in "$@"; do printf '%s\n' "$l" >> "$NEXT_STEPS"; done; }

# macOS ships /usr/bin/git and /usr/bin/python3 as shims that exist whether or not the Command Line
# Tools behind them do. `command -v` therefore ALWAYS finds them, the "git is not installed" branch
# below could never fire on a Mac, and a genuinely clean machine failed inside `git clone` instead
# of being told to run xcode-select. Ask xcode-select directly: it answers without popping the
# install dialog, which `git --version` would do during a mere detection pass.
usable() {
  have "$1" || return 1
  case "$(uname -s)" in
    Darwin) case "$1" in git|python3) xcode-select -p >/dev/null 2>&1 ;; *) return 0 ;; esac ;;
    *) return 0 ;;
  esac
}

run() {
  if [ "$DRY_RUN" = 1 ]; then say "  would run: $*"; return 0; fi
  "$@"
}

# Ask before anything that reaches the network or writes outside this script's own scratch.
# Defaults to NO: an installer that proceeds on a stray keypress is one nobody can run carefully.
#
# Reads from /dev/tty, not stdin. The documented way to run this is
# `curl -fsSL … | bash -s -- --tcc`, which occupies stdin with the script itself — so a plain
# `read` gets EOF and every question silently answers "no", skipping the very installs it was
# asked to do. INSTALLER-TZ §2.2 concluded from this that a shell installer must not ask at all;
# the narrower fix is to ask the TERMINAL rather than stdin, which keeps the confirmations that
# stop this script fetching things behind somebody's back.
confirm() {
  [ "$ASSUME_YES" = 1 ] && return 0
  [ "$DRY_RUN" = 1 ] && { say "  would ask: $1"; return 1; }
  if ! ( : < /dev/tty ) 2>/dev/null; then
    warn "no terminal to ask on — skipping: $1"
    warn "re-run with --yes to accept, or without a pipe to be asked"
    return 1
  fi
  printf '  %s [y/N] ' "$1" > /dev/tty
  read -r answer < /dev/tty
  # The prompt goes to /dev/tty so it survives `curl | bash`, which means a `| tee` transcript
  # would show an installer that ran things with no question in sight. Recorded AFTERWARDS, with
  # the answer: printing the question first put it on screen twice under tee, once from the log
  # and once from the terminal, which is how a two-line question turned into a wall.
  case "$answer" in
    [yY]*) [ -t 1 ] || say "  $1 yes"; return 0 ;;
    *)     [ -t 1 ] || say "  $1 no";  return 1 ;;
  esac
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
        say "  removing the link and the checkout it points at"
        run rm -f "$SKILL_HOME"
        run rm -rf "$SKILL_SRC"
        ;;
      *) warn "$SKILL_HOME points at $target — not ours, left alone" ;;
    esac
  elif [ -d "$SKILL_HOME" ]; then
    warn "$SKILL_HOME is a real directory this script did not create — left alone"
  else
    say "  no skill installed by this script"
  fi

  if find_uv && "$UV" tool list 2>/dev/null | grep -q '^autosound-tcc'; then
    say "  removing autosound-tcc"
    run "$UV" tool uninstall autosound-tcc
  else
    say "  autosound-tcc not installed by uv"
  fi

  APP="$HOME/Applications/Autosound TCC.app"
  if [ -d "$APP" ]; then say "  removing $APP"; run rm -rf "$APP"; fi
  # The Desktop shortcut goes with it, or it stays behind pointing at nothing. Only if it is a
  # symlink — this script only ever makes one of those, and a real folder there is somebody else's.
  if [ -L "$HOME/Desktop/Autosound TCC.app" ]; then
    say "  removing the Desktop shortcut"
    run rm -f "$HOME/Desktop/Autosound TCC.app"
  fi

  # Without --all these stay, and each for a reason: the Python packages are shared with anything
  # else using that interpreter, Claude Code belongs to its own installer and is probably used for
  # other work, and ~/.claude is the person's own configuration. --all exists for one job —
  # resetting a test machine to run the install again — so it asks first, in full sentences,
  # because on a working machine every line of it is a real loss.
  if [ "$REMOVE_ALL" = 1 ]; then
    USER_SITE="$(python3 -m site --user-base 2>/dev/null || true)"
    say ""
    say "  --all also removes, and none of these were made only for tuning:"
    say "    • uv, its downloaded Pythons and tools   ~/.local/bin/uv, ~/.local/share/uv"
    say "    • Claude Code and ALL of its configuration, history, skills and plugins   ~/.claude"
    [ -n "$USER_SITE" ] && say "    • every package you ever pip-installed with --user   $USER_SITE"
    say ""
    say "  Your project folders are still untouched. Nothing below reaches them."
    if confirm "Remove all of that too?"; then
      # ONLY the copy this script would have installed. Using the uv that `find_uv` resolves off
      # PATH deleted a Homebrew-managed uv in testing — an installer must never remove a tool it
      # did not install, however confident it is that it knows what the tool is (2026-08-13).
      if [ -e "$HOME/.local/bin/uv" ] || [ -d "$HOME/.local/share/uv" ]; then
        say "  removing uv from ~/.local"
        run rm -rf "$HOME/.local/bin/uv" "$HOME/.local/bin/uvx" "$HOME/.local/share/uv"
      elif find_uv; then
        say "  leaving $UV alone — this script did not install it"
      fi
      if [ -e "$HOME/.local/bin/claude" ] || [ -d "$HOME/.claude" ]; then
        say "  removing Claude Code and ~/.claude"
        run rm -rf "$HOME/.local/bin/claude" "$HOME/.claude"
      fi
      if [ -n "$USER_SITE" ] && [ -d "$USER_SITE" ]; then
        say "  removing $USER_SITE"
        run rm -rf "$USER_SITE"
      fi
      # Named rather than deleted. `env`/`env.fish` are the cargo-dist PATH snippet, written by
      # uv's installer and by others of the same family (rustup among them), and nothing in the
      # file says which. Removing a file this script cannot prove it created is the mistake that
      # cost a Homebrew uv earlier today. They are inert unless sourced.
      leftovers=""
      for f in env env.fish; do
        [ -e "$HOME/.local/bin/$f" ] && leftovers="$leftovers ~/.local/bin/$f"
      done
      if [ -n "$leftovers" ]; then
        say ""
        say "  Left behind, on purpose:$leftovers"
        say "  A PATH snippet uv writes, and so do other installers — nothing identifies whose it"
        say "  is, so it is yours to delete. It does nothing unless a shell sources it."
      fi
      # We write this line now, so we take it back. Only ours: it is found by the marker comment
      # this script puts above it, never by matching PATH lines generally — somebody else's PATH
      # edit in their own shell profile is not ours to delete.
      for _rc in "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc"; do
        if [ -f "$_rc" ] && grep -qF '# added by the autosound installer' "$_rc"; then
          say "  removing the PATH line this installer added to $_rc"
          if [ "$DRY_RUN" = 0 ]; then
            _tmp="$(mktemp)"
            grep -vF -e '# added by the autosound installer' \
                     -e 'export PATH="$HOME/.local/bin:$PATH"' "$_rc" > "$_tmp" && mv "$_tmp" "$_rc"
          fi
        fi
      done
      say ""
      say "  Gone. The Command Line Tools stay — nothing here installed them."
      say "  A PATH line you added yourself is left alone; only the one marked as this"
      say "  installer's is removed."
    else
      say "  Left alone."
    fi
  else
    say ""
    say "  Left in place on purpose: the Python packages (shared with everything else using that"
    say "  interpreter), Claude Code (its own installer owns it), and ~/.claude (yours)."
    say "  Re-run with --uninstall --all to remove those too."
  fi
  say "  Every tuning project you have is untouched."
  exit 0
fi

# ── what is already here ──────────────────────────────────────────────────────
step "Looking at what you already have"
for tool in git uv claude python3; do
  if usable "$tool"; then say "  ✓ $tool  $(command -v "$tool")"
  elif have "$tool"; then say "  – $tool  a macOS shim only — the Command Line Tools are not installed"
  else say "  – $tool  not found"; fi
done

if [ -z "$MODE" ] && [ "$UNINSTALL" = 0 ]; then
  if ! ( : < /dev/tty ) 2>/dev/null; then
    echo "no --terminal or --tcc given and no terminal to ask on." >&2
    echo "  curl -fsSL <url> | bash -s -- --terminal    the method only" >&2
    echo "  curl -fsSL <url> | bash -s -- --tcc         with the desktop app" >&2
    exit 2
  fi
  say ""
  say "  1) Terminal only — the tuning method, no desktop app (~30 MB)"
  say "  2) Terminal + TCC — plus the desktop app with the DSP tree, plan and curves (~680 MB)"
  printf '  Which? [1/2] ' > /dev/tty
  read -r choice < /dev/tty
  case "$choice" in 2) MODE="tcc" ;; *) MODE="terminal" ;; esac
fi
# The reviewer is asked for HERE, next to the mode, because it is the same kind of question — what
# do you want — and because its answer changes the download list below. A second vendor arguing
# with the first is most of what makes this method work, so it is worth one question; and it is
# genuinely optional, so it is worth asking rather than assuming.
WANT_REVIEWER=0
if [ "$UNINSTALL" = 0 ] && ! have agy && ! have omp && ! have gemini; then
  say ""
  say "  Optional: a second AI (Gemini) that argues with the first before you type anything into"
  say "  the DSP. It is where most of the value is."
  if ! have brew; then
    say "  Needs Homebrew: a few hundred MB, and your admin password. Saying no changes nothing"
    say "  else, and you can add it later."
  fi
  # No DRY_RUN guard: `confirm` already answers "would ask" and declines in a dry run, and with
  # --yes it accepts — which is what makes `--yes --dry-run` able to preview this branch at all.
  if confirm "Set up Gemini as the reviewer?"; then WANT_REVIEWER=1; fi
fi

say ""
say "Installing: $([ "$MODE" = tcc ] && echo 'the skill and TCC' || echo 'the skill only')"

# ONE question, here, instead of two buried forty lines apart. The rule was never to fetch and run
# anything without asking, and that rule stands — but a prompt that arrives mid-scroll, after the
# person has already chosen --tcc and while somebody else's installer is printing, collects a
# reflex `y` rather than a decision. Everything that will be downloaded is named once, before any
# of it happens, while they are still reading.
if [ "$DRY_RUN" = 0 ]; then
  say ""
  say "  This downloads and runs, from the internet:"
  say "    • the tuning method             github.com/ayukhno/autosound-tuning-skill"
  say "    • numpy, scipy, matplotlib      pypi.org, into your own user site"
  if ! have claude; then say "    • Claude Code                   claude.ai/install.sh"; fi
  if [ "$MODE" = "tcc" ]; then
    if ! have uv; then say "    • uv, and a Python of its own   astral.sh/uv/install.sh"; fi
    say "    • the desktop app               github.com/ayukhno/autosound-tcc"
  fi
  if [ "$WANT_REVIEWER" = 1 ]; then
    if ! have brew; then
      say "    • Homebrew                      brew.sh, and it will ask for your password"
    fi
    say "    • Antigravity, Google's CLI     the Gemini reviewer, via Homebrew"
  fi
  if [ "$MODE" = "tcc" ]; then
    say "    • a shortcut on your Desktop     pointing at the app it builds"
  fi
  say "    • one line in your shell profile so your shell can find what it installed"
  say ""
  say "  It touches no project folder and logs you in nowhere."
  if confirm "Go ahead?"; then
    # Consent given once, in full. The per-step prompts would now be asking the same question
    # again in a worse moment, so they are satisfied.
    ASSUME_YES=1
  else
    say ""
    say "  Nothing installed. Re-run when you want to."
    exit 0
  fi
fi

# ── git: required, and not something to install behind someone's back ─────────
if ! usable git; then
  step "git is required and is not installed"
  case "$(uname -s)" in
    Darwin) say "  Run this, click Install in the dialog, then run this script again:"
            say "      xcode-select --install" ;;
    *)      say "  Install git with your package manager, then run this script again." ;;
  esac
  exit 1
fi

# ── the skill ─────────────────────────────────────────────────────────────────
step "The tuning skill"
if [ -z "$SKILL_REF" ]; then
  # The newest 3.x tag. Asked for by name rather than "main": main is where development lands,
  # and an installer should put you on a release unless you say otherwise.
  SKILL_REF="$(git ls-remote --tags --refs "$SKILL_REPO" 'v3.*' 2>/dev/null \
      | awk -F/ '{print $NF}' | sort -V | tail -1)"
  [ -z "$SKILL_REF" ] && SKILL_REF="main"
fi
say "  version: $SKILL_REF"

ours=0
if [ -L "$SKILL_HOME" ]; then
  target="$(cd "$(dirname "$SKILL_HOME")" && readlink "$SKILL_HOME")"
  case "$target" in "$SKILL_SRC"/*) ours=1 ;; esac
fi

if [ -L "$SKILL_HOME" ] && [ "$ours" = 0 ]; then
  # Somebody's own working tree, wired up on purpose. Leave it, say so, move on. Replacing it
  # would be worse than whatever this script was asked to fix.
  warn "$SKILL_HOME is a symlink to $(readlink "$SKILL_HOME")"
  warn "left exactly as it is — that is somebody's checkout, not this script's to replace"
elif [ -d "$SKILL_HOME" ] && [ ! -L "$SKILL_HOME" ]; then
  warn "$SKILL_HOME is a real directory this script did not create — left alone."
  warn "move it aside and re-run if you want this script to manage it."
elif [ -d "$SKILL_SRC/.git" ]; then
  say "  already installed — updating to $SKILL_REF"
  run git -C "$SKILL_SRC" fetch --tags --quiet origin
  run git -c advice.detachedHead=false -C "$SKILL_SRC" checkout --quiet "$SKILL_REF"
else
  say "  installing into $SKILL_SRC, linked from $SKILL_HOME"
  run mkdir -p "$(dirname "$SKILL_HOME")"
  # Not `run`, because this one call needs its stderr filtered. A shallow clone of an ANNOTATED
  # tag makes git print `warning: refs/tags/vX.Y.Z <sha> is not a commit!` — it is complaining that
  # the tag OBJECT is not a commit, which is what an annotated tag is. Verified harmless: HEAD
  # lands on exactly what the tag peels to. Dropped because the word "warning" during a first
  # install reads as something the person did wrong. Every other line of stderr survives, and a
  # real failure still stops the script.
  if [ "$DRY_RUN" = 1 ]; then
    say "  would run: git clone --branch $SKILL_REF --depth 1 $SKILL_REPO $SKILL_SRC"
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
  fi
  if [ "$DRY_RUN" = 0 ]; then
    rm -f "$SKILL_HOME"
    ln -s "$SKILL_SRC/skills/autosound-tuning" "$SKILL_HOME"
  fi
fi

# ── what the skill's own tools need ───────────────────────────────────────────
# The reason this script exists, ahead of anything about models (INSTALLER-TZ §0): put the wall
# up front instead of letting it arrive mid-tune. `numpy` is imported at module scope by
# `curve_view`, `dsp_math`, `eq_gate`, `make_plot` and `xover_select` — without it they do not
# import at all. `scipy` and `matplotlib` are lazy, and cost one feature rather than a session.
step "What the skill's tools need"
# Resolve through the symlink when there is one. The `|| SKILL_REAL=` is load-bearing: under
# `set -e` an assignment whose command substitution fails takes the whole script down, and on a
# machine with no ~/.claude/skills yet — every clean install, and EVERY --dry-run, where the clone
# above only printed itself — the first `cd` fails. The installer used to die here without a word,
# one line after printing this step's header (found on a clean M1, 2026-08-13).
SKILL_REAL="$(cd "$(dirname "$SKILL_HOME")" 2>/dev/null && cd "$(readlink "$SKILL_HOME" 2>/dev/null || echo "$SKILL_HOME")" 2>/dev/null && pwd)" || SKILL_REAL=""
REQS="${SKILL_REAL:-$SKILL_HOME}/requirements.txt"
[ -f "$REQS" ] || REQS="$SKILL_HOME/requirements.txt"
# A dry run has no requirements.txt on disk because nothing was cloned. That is not "nothing to
# install" — a real run would have it — so do not say so, and go on to report the interpreter,
# which is the most useful thing a dry run can tell you about this step.
if [ ! -f "$REQS" ] && [ "$DRY_RUN" != 1 ]; then
  warn "no requirements.txt beside the skill — skipping (nothing to install from)"
elif ! usable python3; then
  warn "no python3 — the skill's tools cannot run at all until there is one"
else
  # WHICH interpreter: the one `python3` resolves to, because that is literally how the method
  # invokes its tools (`python3 rew_tool/...` in SKILL.md). Not TCC's venv — different process.
  #
  # HOW depends on what that interpreter is. On a stock Mac it is Apple's 3.9 at /usr/bin/python3,
  # whose site-packages live under /Library and need root — `uv pip install --python` there fails
  # with "Permission denied", which is correct and must not be worked around with sudo. `--user`
  # writes to ~/Library/Python/3.9/…, which that interpreter already has on its path. Inside a
  # venv the reverse holds: `--user` is refused outright. So ask the interpreter which it is.
  [ -f "$REQS" ] || say "  not on disk yet — the clone above puts it at $REQS"
  PY_BIN="$(command -v python3)"
  say "  target interpreter: $PY_BIN ($("$PY_BIN" -V 2>&1))"
  if "$PY_BIN" -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)' 2>/dev/null; then
    say "  a virtualenv — installing into it"
    run "$PY_BIN" -m pip install --quiet --no-warn-script-location --disable-pip-version-check -r "$REQS" \
      || warn "install failed — see above"
  else
    say "  a system interpreter — installing into your user site, never into /Library"
    run "$PY_BIN" -m pip install --quiet --user --no-warn-script-location --disable-pip-version-check -r "$REQS" \
      || warn "install failed — see above"
  fi
fi

# ── Claude Code: named, never installed silently ──────────────────────────────
step "Claude Code"
if have claude; then
  say "  ✓ $(claude --version 2>/dev/null || echo present)"
else
  say "  Not installed. The skill and TCC both drive YOUR authenticated session — they cannot"
  say "  log in for you, and nothing here can change that."
  if confirm "Run the official installer (curl -fsSL https://claude.ai/install.sh | sh)?"; then
    run sh -c 'curl -fsSL https://claude.ai/install.sh | sh'
  else
    say "  Skipped. When you want it:  curl -fsSL https://claude.ai/install.sh | sh"
  fi
fi

# ── the reviewer, only if it was asked for above ──────────────────────────────
if [ "$WANT_REVIEWER" = 1 ]; then
  step "The reviewer (Gemini, through Google's Antigravity CLI)"
  # Homebrew writes to /opt/homebrew and needs sudo, which needs an Administrator account. Asking
  # first, because the alternative is what happened on a real machine: the installer ran, Homebrew
  # printed "Need sudo access on macOS", and the whole thing stopped there — no uv, no app, no
  # summary, because an OPTIONAL extra had failed (2026-08-13).
  if ! have brew && ! id -Gn 2>/dev/null | tr ' ' '\n' | grep -qx admin; then
    warn "Homebrew needs an Administrator account and this one is not; skipping the reviewer."
    WANT_REVIEWER=0
  fi
  if [ "$WANT_REVIEWER" = 1 ] && ! have brew; then
    # NOT `NONINTERACTIVE=1`. That switch does not mean "do not pause", it means "never prompt" —
    # so instead of asking for the password it refuses outright. Homebrew needs a real terminal
    # for both its RETURN pause and sudo, and `curl | bash` has already taken stdin, so hand it
    # /dev/tty explicitly. `|| true` because the reviewer is optional and must never take the
    # install down with it; the check below decides what to say.
    say "  installing Homebrew first — it will ask for your admin password"
    if [ "$DRY_RUN" = 0 ]; then
      sh -c '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/tty' || true
    else
      say "  would run: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
    for d in /opt/homebrew/bin /usr/local/bin; do
      [ -x "$d/brew" ] && export PATH="$d:$PATH"
    done
  fi
  if [ "$WANT_REVIEWER" = 1 ] && have brew; then
    # Same reasoning: a cask that fails to install is a missing reviewer, not a failed install.
    if [ "$DRY_RUN" = 0 ]; then brew install --cask antigravity-cli || true
    else say "  would run: brew install --cask antigravity-cli"; fi
    # Gatekeeper quarantines anything a browser or a cask brought in; the CLI then refuses to
    # start with a dialog that reads like malware and is not (setup-critic-channel.md §1).
    if [ "$DRY_RUN" = 0 ] && command -v agy >/dev/null 2>&1; then
      xattr -dr com.apple.quarantine "$(command -v agy)" 2>/dev/null || true
    fi
    next_step "Sign the reviewer in — once, and it needs one thing from you first: the Project" \
              "ID (not the name, not the number) from aistudio.google.com/app/apikey. Then run" \
              "this, paste the ID, and open the link it prints:" \
              ">agy"
  elif [ "$WANT_REVIEWER" = 1 ]; then
    warn "Homebrew is not available — the reviewer was not installed. Nothing else is affected."
    next_step "Set the reviewer up by hand when you have time. The steps, including a free" \
              "browser-only route that needs no CLI at all:" \
              ">open $SKILL_HOME/references/tooling/setup-critic-channel.md"
  fi
fi

# ── TCC ───────────────────────────────────────────────────────────────────────
if [ "$MODE" = "tcc" ]; then
  step "uv (installs its own Python, which is why it is the recommended route)"
  if find_uv; then
    say "  ✓ $("$UV" --version)"
  elif confirm "Install uv (curl -LsSf https://astral.sh/uv/install.sh | sh)?"; then
    run sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    export PATH="$HOME/.local/bin:$PATH"
  else
    # Was `exit 0`, which threw away the checks AND the next-steps list: someone who declined uv
    # ended up with a working skill, no confirmation of it, and no idea what to do (2026-08-13).
    # Declining the app is not a reason to stop talking to them — degrade to the terminal install.
    say "  Skipped — TCC needs it. Carrying on with the method alone, which is fully usable."
    MODE="terminal"
  fi
fi

if [ "$MODE" = "tcc" ]; then
  step "Tuning Command Center"
  # `--python` is not optional here. Without it `uv tool install` used the system interpreter —
  # 3.9.6 on a stock macOS — and refused with "does not satisfy Python>=3.11", which reads as a
  # broken package rather than a missing Python. Naming a version makes uv fetch one, which is the
  # entire reason uv is the recommended route (found by running this, 2026-08-12).
  find_uv || UV=uv
  run "$UV" tool install --python 3.12 --upgrade "autosound-tcc[gui,claude] @ git+${TCC_REPO}"

  # Where uv actually put it, which is not always `~/.local/bin`.
  TCC_BIN="$(command -v autosound-tcc || true)"
  [ -z "$TCC_BIN" ] && [ -x "${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/autosound-tcc" ] \
      && TCC_BIN="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/autosound-tcc"

  if [ "$(uname -s)" = "Darwin" ]; then
    step "A double-clickable app"
    # NOT relative to $0: under `curl … | bash` that is "bash", so dirname gives whatever folder
    # the person happened to be standing in, so the bundle was silently skipped for everyone who
    # installed the recommended way — it looked for scripts/make-macos-app.sh under their current
    # working directory (found on a clean M1, 2026-08-13). The clone above always has it.
    builder="$SKILL_SRC/scripts/make-macos-app.sh"
    [ -f "$builder" ] || builder="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/scripts/make-macos-app.sh"
    if [ "$DRY_RUN" = 1 ]; then
      say "  would build ~/Applications/Autosound TCC.app"
    elif [ -x "$builder" ] && [ -n "$TCC_BIN" ]; then
      run "$builder" "$HOME/Applications" "$TCC_BIN"
      # A symlink rather than a Finder alias: it double-clicks the same, and `rm` removes it,
      # where an alias is an opaque blob only Finder can make sense of. The person asked for an
      # icon they can see without opening a folder first, and ~/Applications is not on the Desktop.
      if [ "$DRY_RUN" = 0 ] && [ -d "$HOME/Desktop" ] && [ ! -e "$HOME/Desktop/Autosound TCC.app" ]; then
        ln -s "$HOME/Applications/Autosound TCC.app" "$HOME/Desktop/Autosound TCC.app" 2>/dev/null \
          && say "  and a shortcut on your Desktop"
      fi
    else
      warn "skipped: $([ -n "$TCC_BIN" ] && echo "no $builder" || echo "autosound-tcc not found")"
    fi
  fi
fi

# ── did it work ───────────────────────────────────────────────────────────────
step "Checking"
ok=1
if [ -f "$SKILL_HOME/rew_tool/contract.py" ]; then
  say "  ✓ skill installed, and it is the 3.x line"
  if python3 -c "import numpy" 2>/dev/null; then
    say "  ✓ numpy is importable — the skill's tools will load"
  else
    warn "numpy is NOT importable by $(command -v python3 || echo python3): crossover selection,"
    warn "the EQ gate, the DSP maths and plot rendering will fail when the method reaches them."
    ok=0
  fi
elif [ -f "$SKILL_HOME/rew_tool/rew_api.py" ]; then
  warn "the skill at $SKILL_HOME is the 2.x line — TCC cannot drive it"
  ok=0
elif [ "$DRY_RUN" = 0 ]; then
  warn "no skill at $SKILL_HOME"
  ok=0
fi
if [ "$MODE" = "tcc" ] && [ "$DRY_RUN" = 0 ]; then
  TCC_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"
  TCC_AT="$TCC_DIR/autosound-tcc"
  if have autosound-tcc && user_shell_sees "$TCC_DIR"; then
    say "  ✓ autosound-tcc installed"
  elif [ -x "$TCC_AT" ] || have autosound-tcc; then
    # It used to say "✓ installed" here. It is installed, and typing its name still answers
    # "command not found", which is a worse first minute than an honest warning.
    warn "autosound-tcc is installed at $TCC_AT but that folder is not on your PATH."
    add_to_path "$TCC_DIR"
    ok=0
  else
    warn "autosound-tcc is not installed"
    ok=0
  fi
fi
# Resolved the same way as the app, and for the same reason: in --terminal mode nothing exports
# ~/.local/bin into this script's PATH, so `have claude` was false immediately after the official
# installer had put claude there, and the summary said "claude is not installed" about a Claude it
# had just watched install itself.
CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
if [ -z "$CLAUDE_BIN" ] && [ -x "$HOME/.local/bin/claude" ]; then CLAUDE_BIN="$HOME/.local/bin/claude"; fi
if [ -n "$CLAUDE_BIN" ]; then
  if ! user_shell_sees "$(dirname "$CLAUDE_BIN")"; then
    warn "claude is installed at $CLAUDE_BIN but that folder is not on your PATH."
    add_to_path "$(dirname "$CLAUDE_BIN")"
    ok=0
  fi
  # The only account this whole thing needs. GitHub is not one: both repositories are public and
  # nothing here pushes, so `git clone https://…` is anonymous and there is no token to arrange.
  if "$CLAUDE_BIN" auth status 2>/dev/null | grep -q '"loggedIn": *true'; then
    say "  ✓ claude is signed in"
  else
    warn "claude is installed but not signed in."
    next_step "Sign in to Claude. This is the one step nothing can do for you: the session is" \
              "yours, not this tool's." \
              ">claude auth login"
    ok=0
  fi
else
  warn "claude is not installed; nothing can run a session without it"
  next_step "Install Claude Code, then sign in:" \
            ">curl -fsSL https://claude.ai/install.sh | sh" \
            ">claude auth login"
  ok=0
fi

# The reviewer is a second model on purpose — cross-vendor review is the point — but it is
# optional and it is not this script's to install. Reported, never arranged.
# Same blindness as uv had: a reviewer sitting in ~/.local/bin while that folder is off PATH is
# not a working reviewer, because the skill invokes it by bare name — but "none found" is the
# wrong thing to tell someone who installed one. Distinguish the two.
# The trailing `true` is not decoration. When none of the three is present the loop's last command
# fails, the substitution inherits that status, and `set -e` kills the script mid-summary — which
# is exactly what happened on a machine with no reviewer installed: the log ended after the claude
# line and the whole next-steps list was never printed (2026-08-13). Second time today.
reviewers_on_path="$(for b in agy omp gemini; do have "$b" && printf '%s ' "$b"; done; true)"
reviewers_off_path="$(for b in agy omp gemini; do have "$b" || { [ -x "$HOME/.local/bin/$b" ] && printf '%s ' "$b"; }; done; true)"
if [ -n "$reviewers_on_path" ]; then
  # Found, not verified, and the difference is not pedantic: a real machine carried an `agy` that
  # was three lines of `exec gemini "$@"` with no gemini installed behind it, and this line called
  # it a working reviewer (2026-08-13). Actually invoking the CLI to check would mean running an
  # unknown binary that may prompt or hang, so the claim is narrowed to what was established, and
  # the skill's own doctor — which does test a live round trip — is offered.
  say "  ✓ found a reviewer CLI ($reviewers_on_path)"
  next_step "Check the reviewer really answers. Finding the command is not the same as it" \
            "working, and a wrapper pointing at a CLI you no longer have looks identical:" \
            ">$SKILL_HOME/scripts/gemini_critic.sh --doctor"
elif [ -n "$reviewers_off_path" ]; then
  warn "$(printf '%s' "$reviewers_off_path")is installed in ~/.local/bin, which is not on your PATH,"
  warn "so nothing can call it. The PATH step below fixes this and the app in one line."
  PATH_FIX_NEEDED=1
else
  say "  – no reviewer CLI found. Reviews fall back to the clipboard, which works."
  next_step "Add a second AI as reviewer, when you have a spare hour. One model proposing and a" \
            "different vendor's arguing is what makes this method worth running; Gemini is the" \
            "one it is built around. Setup, and the omp route if you prefer it:" \
            ">open ~/.claude/skills/autosound-tuning/references/tooling/setup-critic-channel.md"
fi

# REW is not ours to install, but it is the one thing without which nothing measures. A closed REW
# at install time is normal, so this is worded as a reminder rather than a fault.
if ! curl -fsS --max-time 2 -o /dev/null http://localhost:4735/version 2>/dev/null; then
  next_step "Switch on REW's API — nothing can read a measurement without it. In REW open" \
            "Preferences → API and tick \"Start the API when REW starts\", so it is on every" \
            "time. That panel then reads \"API server is running on port 4735\"."
fi

next_step "Optional, and worth it: a free GitHub account. Your project folder is weeks of" \
          "decisions — the ledger, the journal, the config backups — and the skill offers to" \
          "keep it in a private repository when you start one. The sweeps stay on your disk."


# The first tune is a step like any other, and it goes last so the list ends where the person
# actually wants to be.
if [ "$MODE" = "tcc" ]; then
  next_step "Start. Make a folder for the car — everything about it lives there — and open it:" \
            ">mkdir -p ~/Autosound/my-car" \
            ">autosound-tcc --project-dir ~/Autosound/my-car" \
            "Then say what you want, in the panel on the right, in any language:" \
            "\"let's tune this car from scratch\"."
else
  next_step "Start. Make a folder for the car — everything about it lives there — and open it:" \
            ">mkdir -p ~/Autosound/my-car && cd ~/Autosound/my-car" \
            ">claude" \
            "Then say what you want, in any language: \"tune a new car from scratch\"."
fi

say ""
if [ "$ok" = 1 ]; then say "Installed."; else say "Installed, with the warnings above."; fi

if [ -s "$NEXT_STEPS" ]; then
  printf '\n\033[1m==> What to do next\033[0m\n'
  awk '/^@@$/ { n++; first=1; print ""; next }
       first == 1 { printf "  %d. %s\n", n, $0; first=0; next }
       /^>/ { printf "         %s\n", substr($0, 2); next }
       { printf "     %s\n", $0 }' "$NEXT_STEPS"
  printf '\n'
fi
