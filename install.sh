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
DRY_RUN=0
SKILL_REF=""
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --terminal) MODE="terminal" ;;
    --uninstall) UNINSTALL=1 ;;
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
  case "$answer" in [yY]*) return 0 ;; *) return 1 ;; esac
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

  if have uv && uv tool list 2>/dev/null | grep -q '^autosound-tcc'; then
    say "  removing autosound-tcc"
    run uv tool uninstall autosound-tcc
  else
    say "  autosound-tcc not installed by uv"
  fi

  APP="$HOME/Applications/Autosound TCC.app"
  if [ -d "$APP" ]; then say "  removing $APP"; run rm -rf "$APP"; fi

  # Deliberately NOT removed, and each for a reason:
  #   * numpy/scipy/matplotlib — shared with everything else that uses this interpreter.
  #   * Claude Code — installed by its own installer, and probably used for other work.
  #   * ~/.claude — the user's own configuration.
  say ""
  say "  Left in place on purpose: the Python packages (shared with everything else using that"
  say "  interpreter), Claude Code (its own installer owns it), and ~/.claude (yours)."
  say "  Every tuning project you have is untouched."
  exit 0
fi

# ── what is already here ──────────────────────────────────────────────────────
step "Looking at what you already have"
for tool in git uv claude python3; do
  if have "$tool"; then say "  ✓ $tool  $(command -v "$tool")"; else say "  – $tool  not found"; fi
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
say ""
say "Installing: $([ "$MODE" = tcc ] && echo 'the skill and TCC' || echo 'the skill only')"

# ── git: required, and not something to install behind someone's back ─────────
if ! have git; then
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
  run git -c advice.detachedHead=false clone --quiet --branch "$SKILL_REF" --depth 1 \
      "$SKILL_REPO" "$SKILL_SRC"
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
REQS="$(cd "$(dirname "$SKILL_HOME")" 2>/dev/null && cd "$(readlink "$SKILL_HOME" 2>/dev/null || echo "$SKILL_HOME")" 2>/dev/null && pwd)/requirements.txt"
[ -f "$REQS" ] || REQS="$SKILL_HOME/requirements.txt"
if [ ! -f "$REQS" ]; then
  warn "no requirements.txt beside the skill — skipping (nothing to install from)"
elif ! have python3; then
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
  PY_BIN="$(command -v python3)"
  say "  target interpreter: $PY_BIN ($("$PY_BIN" -V 2>&1))"
  if "$PY_BIN" -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)' 2>/dev/null; then
    say "  a virtualenv — installing into it"
    run "$PY_BIN" -m pip install --quiet -r "$REQS" \
      || warn "install failed — see above"
  else
    say "  a system interpreter — installing into your user site, never into /Library"
    run "$PY_BIN" -m pip install --quiet --user -r "$REQS" \
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

# ── TCC ───────────────────────────────────────────────────────────────────────
if [ "$MODE" = "tcc" ]; then
  step "uv (installs its own Python, which is why it is the recommended route)"
  if have uv; then
    say "  ✓ $(uv --version)"
  elif confirm "Install uv (curl -LsSf https://astral.sh/uv/install.sh | sh)?"; then
    run sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    export PATH="$HOME/.local/bin:$PATH"
  else
    say "  Skipped — TCC cannot be installed without it. The skill above still works."
    exit 0
  fi

  step "Tuning Command Center"
  # `--python` is not optional here. Without it `uv tool install` used the system interpreter —
  # 3.9.6 on a stock macOS — and refused with "does not satisfy Python>=3.11", which reads as a
  # broken package rather than a missing Python. Naming a version makes uv fetch one, which is the
  # entire reason uv is the recommended route (found by running this, 2026-08-12).
  run uv tool install --python 3.12 --upgrade "autosound-tcc[gui,claude] @ git+${TCC_REPO}"

  # Where uv actually put it, which is not always `~/.local/bin`.
  TCC_BIN="$(command -v autosound-tcc || true)"
  [ -z "$TCC_BIN" ] && [ -x "${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/autosound-tcc" ] \
      && TCC_BIN="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/autosound-tcc"

  if [ "$(uname -s)" = "Darwin" ]; then
    step "A double-clickable app"
    builder="$(cd "$(dirname "$0")" && pwd)/scripts/make-macos-app.sh"
    if [ "$DRY_RUN" = 1 ]; then
      say "  would build ~/Applications/Autosound TCC.app"
    elif [ -x "$builder" ] && [ -n "$TCC_BIN" ]; then
      run "$builder" "$HOME/Applications" "$TCC_BIN"
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
  if have autosound-tcc || [ -x "$HOME/.local/bin/autosound-tcc" ]; then
    say "  ✓ autosound-tcc installed"
  else
    warn "autosound-tcc is not on PATH — uv may need: uv tool update-shell (then a new terminal)"
    ok=0
  fi
fi
if have claude; then
  # The only account this whole thing needs. GitHub is not one: both repositories are public and
  # nothing here pushes, so `git clone https://…` is anonymous and there is no token to arrange.
  if claude auth status 2>/dev/null | grep -q '"loggedIn": *true'; then
    say "  ✓ claude is signed in"
  else
    warn "claude is installed but NOT signed in — run \`claude auth login\` (or just \`claude\`)."
    warn "this is the one step that cannot be automated: the session is yours, not this tool's."
    ok=0
  fi
else
  warn "claude is not installed; nothing can run a session without it"
  ok=0
fi

# The reviewer is a second model on purpose — cross-vendor review is the point — but it is
# optional and it is not this script's to install. Reported, never arranged.
if have agy || have omp || have gemini; then
  say "  ✓ a reviewer route is available ($(for b in agy omp gemini; do have $b && printf '%s ' $b; done))"
else
  say "  – no reviewer CLI found (agy / omp / gemini). Reviews will fall back to the clipboard,"
  say "    which works; a second vendor reviewing the first is what makes the loop worth having."
fi

say ""
if [ "$ok" = 1 ]; then
  say "Done. Open a project folder and run:"
  [ "$MODE" = "tcc" ] && say "    autosound-tcc --project-dir ." || true
  say "    claude          # then ask it to tune your car"
else
  say "Finished with the warnings above — read them before starting a session."
fi
