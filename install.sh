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
#   * Command Line Tools        macOS only, when missing — Apple's git. Installed through APPLE'S
#                               OWN window, which this script opens and waits for: whatever it asks
#                               for, it asks in its own dialog. No password passes through anything
#                               we wrote (see the note at `xcode-select --install` below).
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
#   ./install.sh --github            with the GitHub CLI, for the project backup (default: without)
#   ./install.sh --with-omp          with omp, which offers TCC every non-Claude model (default: without)
#   ./install.sh --no-engine         without Phase 1's desk engine (default: fetched only when this
#   ./install.sh --engine            machine has no .NET SDK to build it from; --engine fetches anyway)
#   ./install.sh --dry-run           say what it would do, change nothing
#   ./install.sh --plugin            run from inside a plugin copy (/plugin install): the method IS that copy, so
#                                    it is checked against its signed release and not cloned; everything else as
#                                    usual (W-6 #120) -- what /autosound-tuning:setup runs
#   ./install.sh --yes               yes to every question; sign-ins are printed, not run
#   ./install.sh --skill-ref v3.1.0  a specific skill version (default: the newest 3.x tag)
#   ./install.sh --channel beta      also release candidates: for the app, and in a SECOND copy of the
#                                    method that only an app asking for beta runs -- the terminal's
#                                    copy stays on releases (default: stable, releases only;
#                                    --skill-ref sets the terminal's copy, --tcc-ref the app)
#   ./install.sh --tcc-ref v1.1.0    the app version released WITH that one — quote the two
#                                    together or not at all; a mixed pair is untested
#   ./install.sh --uninstall         remove what this script installed — NEVER your projects
#   ./install.sh --uninstall --all   also uv, Claude Code and ~/.claude, agy/gh/omp when this
#                                    script installed them, and every --user pip package. For
#                                    resetting a test machine. Asks first.
set -euo pipefail

SKILL_REPO="https://github.com/ayukhno/autosound-tuning-skill.git"
#: The same repository without the `.git` — what a person opens in a browser, not what git clones.
SKILL_REPO_URL="${SKILL_REPO%.git}"
# Which tags this installer considers installable — the supported line, stated once so a consumer
# can READ the policy instead of re-deriving it from the pipeline below. It is the same rule
# install.ps1 and TCC's updater apply; when the supported line moves, this is the line that moves.
SKILL_TAG_GLOB="v3.*"
# The beta channel's candidates for the same line (hub RELEASE-CHANNEL.md §11): `beta-` + the line's
# glob. The different first letter is what keeps a candidate out of SKILL_TAG_GLOB, so the stable
# channel -- the default, and TCC's updater -- never sees one.
SKILL_BETA_GLOB="beta-v3.*"
# Release tags are signed by the method's author (skill #99, hub #82 HUB-031): whoever holds the account's token
# can push a tag, and only the laptop holds the key. The key is HERE, not read from the tag being checked -- a
# tag's own copy would vouch for itself. Same values as install.ps1 and scripts/upkeep.py (installer-consistency.py
# compares them). A tag before SKILL_SIGNED_FROM predates signing: it installs, and the line says so.
SKILL_SIGNING_PRINCIPAL="ayukhno"
SKILL_SIGNING_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHLm4x1yz9JbFfBlxdQA8vR8yYMupVktswes3CL7QE1y"
SKILL_SIGNED_FROM="v3.0.64"
# The app's tags are signed with the same key, from its own first signed tag (TCC's core/signed_tags.py, skill #101),
# and checked the same way before uv installs one. Same value as install.ps1 (installer-consistency.py compares them).
TCC_SIGNED_FROM="v0.1.45"
# Where a local change to the installed clone is kept before the update resets it (skill #91). Same as upkeep.py.
LOCAL_CHANGES="${HOME}/.claude/skills/autosound-local-changes"
# The app's supported line. It is `v*` and not `v3.*` because the app versions independently of the
# method -- they are different products that ship together, and pinning them to one number is the
# coupling SCR-055 is arguing about, not a thing to bake in here.
TCC_TAG_GLOB="v*"
# ...and the app's candidates, the same way.
TCC_BETA_GLOB="beta-v*"
#: The uv release this installer pins. See the note beside the download for how to raise it.
UV_VERSION="0.12.10"
#: This installer's own version, written into its receipt (#142): the sha256 there is empty under `curl | bash`, where
#: no file stands behind $0. Held equal to install.ps1's $InstallerVersion and to .claude-plugin/plugin.json's version
#: by installer-consistency.py; the release's bookkeeping moves all three.
INSTALLER_VERSION="3.1.2"
TCC_REPO="https://github.com/ayukhno/autosound-tcc"
SKILL_HOME="${HOME}/.claude/skills/autosound-tuning"
# The repo lives beside the skill and the skill POINTS at it. Cloning and then moving the
# subdirectory out (the obvious way) leaves a plain folder with no `.git`, so a second run cannot
# update it and the user is stuck on whatever version they first installed — found by running this
# script twice (2026-08-12). A checkout plus a symlink also makes `git -C … checkout v3.0.1` the
# whole of an upgrade, and matches what the README already teaches for staying on 2.x.
SKILL_SRC="${HOME}/.claude/skills/.autosound-tuning-src"
# The beta channel's copy of the method, BESIDE that one and with no link pointing at it
# (autosound-hub #145). The terminal runs releases and a session an app starts on beta runs a
# candidate; while both read one checkout, `--channel beta` moved the terminal too. An app runs
# this copy by path -- installer-consistency.py compares it with install.ps1 and prints it for them.
SKILL_BETA_SRC="${HOME}/.claude/skills/.autosound-tuning-beta"
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
#: omp fills TCC's model picker with everything that is not Claude, billed per use. It comes ONLY
#: with `--with-omp` (the user, 2026-09-17, closing issue #25). The history, so the next change is
#: made knowing it: opt-in first; on with the app from 2026-08-19 (the person who wants it does not
#: know the flag exists) and again 2026-09-09; opt-in again now -- the README names the flag at the
#: install step, the plan screen offers it, and omp is still the one foreign script left that can
#: be neither signed nor checksummed.
WANT_OMP=0
#: `gh` comes only when asked for with `--github` -- no question on the way (the user, 2026-09-16:
#: every question an install asks is a branch nobody has walked on Windows). A machine that already
#: has `gh` keeps getting its backup sign-in at the end, as before.
WANT_GITHUB="auto"
#: Phase 1's desk engine: a self-contained binary, one per platform, attached to the tag's own
#: release (hub `RELEASE-CHANNEL.md` §12). `auto` fetches it ONLY on a machine with no .NET SDK --
#: a machine that can build one loses nothing by waiting for first use, and a machine that cannot
#: would otherwise discover that in the middle of a tune. `--engine` fetches it anyway, `--no-engine`
#: never. The name is computed by the method from its own engine pin and this platform, so nothing
#: here lists a release; a tag that carries none for that pair is an answer, said out loud.
WANT_ENGINE="auto"
#: Where a fetched engine lands -- `resonalyze_engine.installed_dir()` owns this path; the line here
#: is the uninstaller's, so what this script put on the machine can come off it.
ENGINE_HOME="${HOME}/.local/share/autosound/engines"
UNINSTALL=0
REMOVE_ALL=0
DRY_RUN=0
ASSUME_YES=0
SKILL_REF=""
#: `--plugin` (W-6 #120): the folder `/plugin install` made, which this script sits in, and the version it names.
WANT_PLUGIN=0
PLUGIN_ROOT=""
PLUGIN_VERSION=""
# stable (the default): releases only. beta: releases AND release candidates, for trying a version
# before it is released -- for the app, and in the method's second copy (SKILL_BETA_SRC); the
# terminal's copy stays on releases either way. --skill-ref sets the terminal's copy, --tcc-ref the app.
CHANNEL="stable"
# Same idea for the app: empty means "the newest release", not "whatever is on main".
# Resolved beside the install itself, where the app is actually asked for.
TCC_REF=""
#: The parts this run leaves not ready, by their short names, ", "-joined (#142): each check that finds one says why
#: and adds it with `missing`; `finish` reads this and nothing else -- empty is exit 0, anything else exit 3.
MISSING=""
#: Set by `stop` and `finish` as they end the run (#142): `going_ahead`'s EXIT trap leaves an exit that came through
#: them as it is, and makes any other one a stop.
ENDED=""
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
  install.sh --github            with the GitHub CLI, for the project backup (default: without)
  install.sh --with-omp          with omp, which offers TCC every non-Claude model (metered; default: without)
  install.sh --no-engine         without Phase 1's desk engine; --engine fetches it even where the
                                 .NET SDK could build it (default: fetched only when there is no SDK)
  install.sh --dry-run           say what it would do, change nothing
  install.sh --yes               yes to every question; sign-ins are printed, not run
  install.sh --skill-ref v3.1.0  a specific skill version (default: the newest 3.x tag)
  install.sh --channel beta      also release candidates: for the app, and in a SECOND copy of
                                 the method that only an app asking for beta runs -- the
                                 terminal's copy stays on releases (default: stable)
  install.sh --tcc-ref v1.1.0    the app version released WITH that one — quote the two
                                 together or not at all; a mixed pair is untested
  install.sh --uninstall         remove what this script installed — NEVER your projects
  install.sh --uninstall --all   also uv, Claude Code and ~/.claude, agy/gh/omp when this script
                                 installed them, and every --user pip package. Asks first.

Through the one-liner, options go after `bash -s --`:
  curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.46/install.sh | bash -s -- --terminal
USAGE
}

# The newest tag on the beta channel (hub RELEASE-CHANNEL.md §11.2), from tag names on stdin. A
# release sorts as (X,Y,Z,1,0) and a candidate as (X,Y,Z,0,N): v3.1.0 above beta-v3.1.0-rc2, rc10
# above rc2, and a candidate for v3.1.0 above v3.0.49. `sort -V` cannot say this -- it puts every
# `beta-` name after every `v` one. A name of neither shape is not installable and is dropped.
# scripts/installer-consistency.py cuts THIS function out and runs it on fixed names.
newest_on_channel() {
  awk '
    /^v[0-9]+\.[0-9]+\.[0-9]+$/ {
      split(substr($0, 2), v, "."); print v[1] + 0, v[2] + 0, v[3] + 0, 1, 0, $0; next
    }
    /^beta-v[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+$/ {
      s = substr($0, 7); i = index(s, "-rc"); split(substr(s, 1, i - 1), v, ".")
      print v[1] + 0, v[2] + 0, v[3] + 0, 0, substr(s, i + 3) + 0, $0
    }
  ' | sort -n -k1,1 -k2,2 -k3,3 -k4,4 -k5,5 | tail -n 1 | awk '{print $6}'
}

# Is <name> a release tag -- `vX.Y.Z`, or a candidate's `beta-vX.Y.Z-rcN` -- and nothing else? The one rule (T-45,
# #142), here as in install.ps1's Test-ReleaseTag and upkeep.py's is_release_tag; installer-consistency.py holds the
# three to one table of names. ASCII digits and the whole name: matched in the C locale, since glibc's regex reads a
# range such as [0-9] by the locale's collation, not by code point -- in a subshell, so the rest of the run keeps the
# person's locale. newest_on_channel's awk keeps its own pair of patterns, the same two.
is_release_tag() {  # is_release_tag <name>: 0 when it is a release tag
  ( LC_ALL=C
    [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || [[ "$1" =~ ^beta-v[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+$ ]] )
}

while [ $# -gt 0 ]; do
  case "$1" in
    --terminal)    MODE="terminal" ;;
    --tcc)         MODE="tcc" ;;
    --no-reviewer) WANT_REVIEWER=0 ;;
    --reviewer)    WANT_REVIEWER=1 ;;
    --with-omp)    WANT_OMP=1 ;;
    --no-omp)      WANT_OMP=0 ;;   # the default since 2026-09-17; still accepted
    --engine)      WANT_ENGINE=1 ;;
    --no-engine)   WANT_ENGINE=0 ;;
    --github)      WANT_GITHUB=1 ;;
    --no-github)   WANT_GITHUB=0 ;;
    --uninstall)   UNINSTALL=1 ;;
    --all)         REMOVE_ALL=1 ;;
    --dry-run)     DRY_RUN=1 ;;
    --plugin)      WANT_PLUGIN=1 ;;
    --yes|-y)      ASSUME_YES=1 ;;
    --skill-ref)   SKILL_REF="${2:-}"; shift ;;
    --channel)     CHANNEL="${2:-}"; shift ;;
    --tcc-ref)     TCC_REF="${2:-}"; shift ;;
    --help|-h)     usage; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done
case "$CHANNEL" in
  stable|beta) ;;
  *) echo "unknown channel: '$CHANNEL' (stable or beta)" >&2; exit 2 ;;
esac
# --plugin (W-6 #120): the method is the plugin copy this script sits in -- `/plugin install` put the files there, and
# a copy of files brings none of what the method runs on. This run brings that, and checks the copy against its
# signed release instead of cloning one (upkeep.py verify-copy, #121).
if [ "$WANT_PLUGIN" = 1 ]; then
  PLUGIN_ROOT="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || PLUGIN_ROOT=""
  PLUGIN_VERSION="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$PLUGIN_ROOT/.claude-plugin/plugin.json" 2>/dev/null | head -1)"
  if [ -z "$PLUGIN_ROOT" ] || [ -z "$PLUGIN_VERSION" ] || [ -d "$PLUGIN_ROOT/.git" ]; then
    echo "--plugin runs the installer inside a plugin copy -- the folder /plugin install made, with" \
         ".claude-plugin/plugin.json and no .git; this is not one: ${PLUGIN_ROOT:-?}" >&2
    exit 2
  fi
  if [ "$UNINSTALL" = 1 ] || [ -n "$SKILL_REF" ] || [ "$CHANNEL" = "beta" ]; then
    echo "--plugin sets up this plugin copy (v$PLUGIN_VERSION); --uninstall, --skill-ref and --channel beta are" \
         "for the installer's own copy of the method" >&2
    exit 2
  fi
fi

# omp follows the app — see `WANT_OMP` above. `--terminal` is the method in a plain terminal, where
# the model is Claude Code's own and a picker for TCC's models has nothing to pick for.
# An `if`, not `[ … ] && …`: this script runs under `set -e`, where a top-level test that comes out
# false is an exit status and ends the install.
if [ "$WANT_OMP" = 1 ] && [ "$MODE" != "tcc" ]; then
  # omp serves the app's model picker; with no app it has nothing to serve.
  printf '%s\n' "  --with-omp: omp is for the app's model picker, and --terminal installs no app -- left out."
  WANT_OMP=0
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
    case "$1" in git|python3) xcode-select -p >/dev/null 2>&1 && runs_ok "$1" ;; *) return 0 ;; esac
  fi
}
# Presence is not working (hub #192). On the Arbiter's Mac `xcode-select -p` answered and Apple said
# the tools were installed, while /usr/bin/git died on `xcrun: unable to load libxcrun` -- the only
# git on the machine. Once xcode-select answers, the tools are there and running one cannot open
# Apple's dialog, so it is run once and a failure is kept with what it printed.
RUNS_OK_SAID=""
runs_ok() {  # runs_ok <tool>; 0 = it ran
  _ro="$("$1" --version 2>&1)" && return 0
  RUNS_OK_SAID="$(printf '%s' "$_ro" | head -2)"
  return 1
}
broken_tool() {  # broken_tool <tool>: present, the tools installed, and it does not run
  on_mac && have "$1" && xcode-select -p >/dev/null 2>&1 && ! runs_ok "$1"
}
clt_present() { if on_mac; then xcode-select -p >/dev/null 2>&1; else return 0; fi; }

# ── how the run ends (#142) ───────────────────────────────────────────────────
# The exit code a script reads: 0 ready · 1 stopped -- the method was not installed or not changed (the steps before
# it, Apple's tools and Claude Code, may have run) · 2 a usage error, before anything ran · 3 installed, NOT ready, the
# missing parts named. A stop and the end each write the receipt; a usage error writes none; from the consent on, the
# receipt says `stopped` until one of them does (`going_ahead`).

# <text> as a JSON string: `\` and `"` escaped, control characters dropped. sed, byte by byte, and not ${var//}: bash
# 5.2's patsub_replacement gives `&` and `\` in a replacement meanings of their own.
json_str() {  # json_str <text>
  printf '"%s"' "$(printf '%s' "$1" | LC_ALL=C tr -d '\001-\037' | LC_ALL=C sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
}

# The installer's RECEIPT (S-049, #142): which install.sh ran -- its version, and its sha256 when it ran as a file --
# for which method tag, what it did about the engine, the python3 the method runs on, and how the run ended: `ready`,
# `not ready` (`missing` names the parts) or `stopped`. Answering "why is there no engine on this MacBook" took four
# exchanges, because nothing on the machine said which installer had run -- an old bookmarked URL installs old logic
# while the method itself updates to the newest tag. `doctor` reads it back. Its fields, in their order, are
# install.ps1's; JSON from python3 when one runs, and built here when none does -- the engine's line is a tool's own
# words. Written by `stop` and `finish`, never in a dry run; a receipt that cannot be written stops nothing.
write_receipt() {  # write_receipt ready|"not ready"|stopped
  [ "${DRY_RUN:-0}" = 1 ] && return 0
  _wr_status="$1"; _wr_ver=""; _wr_json=""
  _wr_dir="${XDG_DATA_HOME:-$HOME/.local/share}/autosound"
  mkdir -p "$_wr_dir" 2>/dev/null || return 0
  _wr_sha="$( (shasum -a 256 "$0" 2>/dev/null || sha256sum "$0" 2>/dev/null) | awk '{print $1}')" || _wr_sha=""
  if usable python3; then
    _wr_ver="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)" || _wr_ver=""
    _wr_python="$(command -v python3) ${_wr_ver:-does not run}"
  elif have python3; then
    _wr_python="$(command -v python3) does not run"
  else
    _wr_python="no python3"
  fi
  set -- install.sh "$_wr_sha" "${SKILL_REF:-}" "${MODE:-}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
         "$(uname -s)-$(uname -m)" "${ENGINE_DID:-not reached}" "${INSTALLER_VERSION:-}" "$_wr_status" \
         "${MISSING:-}" "$_wr_python"
  if [ -n "$_wr_ver" ]; then
    _wr_json="$(python3 -c 'import json, sys
keys = ("installer", "installer_sha256", "method_ref", "mode", "at", "platform", "engine", "installer_version",
        "status", "missing", "python")
receipt = dict(zip(keys, sys.argv[1:]))
receipt["missing"] = [part for part in receipt["missing"].split(", ") if part]
print(json.dumps(receipt))' "$@" 2>/dev/null)" || _wr_json=""
  fi
  if [ -z "$_wr_json" ]; then
    _wr_list=""; _wr_rest="${MISSING:-}"
    while [ -n "$_wr_rest" ]; do
      _wr_one="${_wr_rest%%, *}"
      if [ "$_wr_one" = "$_wr_rest" ]; then _wr_rest=""; else _wr_rest="${_wr_rest#*, }"; fi
      _wr_list="${_wr_list:+$_wr_list, }$(json_str "$_wr_one")"
    done
    _wr_fmt='{"installer": %s, "installer_sha256": %s, "method_ref": %s, "mode": %s, "at": %s, "platform": %s, '
    _wr_fmt="$_wr_fmt"'"engine": %s, "installer_version": %s, "status": %s, "missing": [%s], "python": %s}'
    # shellcheck disable=SC2059  # the format is the two lines above, never a value
    _wr_json="$(printf "$_wr_fmt" "$(json_str "$1")" "$(json_str "$2")" "$(json_str "$3")" "$(json_str "$4")" \
      "$(json_str "$5")" "$(json_str "$6")" "$(json_str "$7")" "$(json_str "$8")" "$(json_str "$9")" "$_wr_list" \
      "$(json_str "${11}")")"
  fi
  printf '%s\n' "$_wr_json" 2>/dev/null >"$_wr_dir/install-receipt.json" || true
  return 0
}

# A stop: each line said, the receipt written as `stopped`, and the run ends with <code> -- 1, the method not installed
# or not changed. Inside $(...) (pick_method_ref's) the receipt is written from the subshell; the caller carries the
# code out.
stop() {  # stop <code> <line> [<line>...]
  _st_code="$1"; shift
  for _st_line in "$@"; do warn "$_st_line"; done
  write_receipt stopped
  ENDED=1
  exit "$_st_code"
}

# A part this run leaves not ready, by its short name: numpy, scipy, the method, the method (2.x line), the beta copy,
# TCC, Claude Code -- the names install.ps1's Add-Missing records. The check that calls it has said why; a part already
# named is named once.
is_missing() { case ", ${MISSING:-}, " in *", $1, "*) return 0 ;; *) return 1 ;; esac; }
missing() { is_missing "$1" || MISSING="${MISSING:+$MISSING, }$1"; }

# The run's last statement: the verdict, last on screen, then the receipt, the plugin's note and the exit code -- 0
# `Installed.`, or 3 `Installed, NOT ready: <names>` with a line for each saying what to do. A dry run did nothing: it
# says so and ends 0, with no receipt.
finish() {
  say ""
  if [ "${DRY_RUN:-0}" = 1 ]; then say "Nothing was installed — this was a dry run."; ENDED=1; exit 0; fi
  if [ -z "${MISSING:-}" ]; then
    say "Installed."
    write_receipt ready
    # --plugin: this version is verified and set up -- the plugin's SessionStart hook stops offering the setup (#120).
    # Only here: an install that is not ready keeps the note coming back.
    if [ -n "${PLUGIN_ROOT:-}" ]; then
      python3 "$SKILL_HOME/scripts/upkeep.py" plugin-ready --root "$PLUGIN_ROOT" \
        || warn "could not write down that v$PLUGIN_VERSION is set up -- the next session will offer the setup again"
    fi
    ENDED=1
    exit 0
  fi
  say "Installed, NOT ready: $MISSING"
  _fi_rest="$MISSING"
  while [ -n "$_fi_rest" ]; do
    _fi_one="${_fi_rest%%, *}"
    if [ "$_fi_one" = "$_fi_rest" ]; then _fi_rest=""; else _fi_rest="${_fi_rest#*, }"; fi
    case "$_fi_one" in
      numpy|scipy)
        warn "$_fi_one is not importable by $(command -v python3 2>/dev/null || echo python3) -- the libraries' step" \
             "above says why; install it for that python3, then run this again" ;;
      "the method")
        warn "no tuning method at $(pretty "$SKILL_HOME") -- the method's step above says why; run this again" ;;
      "the method (2.x line)")
        warn "$(pretty "$SKILL_HOME") is the 2.x line, which TCC cannot drive -- move it aside, then run this again" ;;
      "the beta copy")
        warn "no beta channel copy on this run's candidate at $(pretty "$SKILL_BETA_SRC") -- an app asking for beta" \
             "runs an older one, or nothing; the beta block above says why; run this again" ;;
      TCC)
        warn "the app was not installed${TCC_REFUSED:+: $TCC_REFUSED} -- the app's block above says why; the method" \
             "is installed and works without it" ;;
      "Claude Code")
        warn "Claude Code is not installed; nothing can run a session without it -- when the network is back:" \
             " curl -fsSL https://claude.ai/install.sh | sh" ;;
      *) warn "$_fi_one" ;;
    esac
  done
  [ -z "${PLUGIN_ROOT:-}" ] || warn "the plugin's set-up note comes back at the next session until an install is ready"
  write_receipt "not ready"
  ENDED=1
  exit 3
}

# The consent, given once and in full: nothing below asks again until the sign-ins, which are offers, not questions --
# and `ASSUME_YES` is left as the person set it, because "yes to every question" also tells the sign-in block to print
# commands instead of opening a browser (setting it here made every interactive install end with "run this later",
# 2026-08-17). Declined -- or no terminal to ask on and no --yes, which takes the default -- it is a stop, 1, nothing
# installed (#142): it ended 0, which a script read as ready. A dry run is not asked.
consent() {
  [ "$DRY_RUN" = 1 ] && return 0
  ask "Go ahead?" n && return 0
  say ""
  stop 1 "Nothing installed. Re-run when you want to."
}

# From here the run is going ahead (#142). The receipt says `stopped` until `stop` or `finish` writes how the run
# ended: an end neither reaches -- a failure under `set -e`, Ctrl-C, a kill -- leaves no earlier run's `ready` standing.
# Bash 3.2 runs no EXIT trap on Ctrl-C; the receipt written here says `stopped` all the same.
going_ahead() {
  write_receipt stopped
  trap unplanned_end EXIT
}
# going_ahead's EXIT trap: an end that came through neither `stop` nor `finish` is a stop, 1 -- a failing command's own
# code is not the table's 2 or 3. Whatever $? says: under bash 3.2 an unbound variable (`set -u`) reaches this trap as
# 0, and without it the run would end 0, ready.
unplanned_end() {
  _ue_rc=$?
  [ -n "${ENDED:-}" ] && return 0
  stop 1 "stopped (exit $_ue_rc) -- the lines above say where; run this again"
}

# THIS SCRIPT NEVER ASKS FOR YOUR PASSWORD. It used to: `sudo -v` read the password straight out
# of a `curl … | bash` pipe, and a background loop re-stamped the ticket every 50 seconds to keep
# it alive for the download. It worked, and that is the problem — typing a root password into a
# script you have not read is a habit an installer should not be teaching, and a pipe is the worst
# place to learn it (HUB-030).
#
# Apple's Command Line Tools still need root. They are installed through Apple's OWN window
# instead, which was already here as the fallback: `xcode-select --install` opens it, macOS asks
# for whatever it needs in its own dialog, and this script waits. One extra click, no password
# passing through anything we wrote.

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
# agy through Google Cloud's ADC (hub #234): the credentials file, the machine's critic-env -- the one place every run
# of the method reads, the app's included (`autosound_ai.py` `agy_sign_in`) -- and whether the switch is on.
adc_file() { printf '%s' "${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"; }
critic_env_path() { printf '%s' "${XDG_CONFIG_HOME:-$HOME/.config}/autosound/critic-env"; }
adc_switch_on() { [ "${AGY_ADC_AUTH:-}" = true ] || grep -qx 'AGY_ADC_AUTH=true' "$(critic_env_path)" 2>/dev/null; }
critic_env_set_adc() {  # AGY_ADC_AUTH=true into the critic-env, once; the file stays the person's (600)
  _ce="$(critic_env_path)"
  grep -qx 'AGY_ADC_AUTH=true' "$_ce" 2>/dev/null && return 0
  mkdir -p "$(dirname "$_ce")" || return 1
  [ -f "$_ce" ] || : > "$_ce"
  chmod 600 "$_ce" 2>/dev/null || true
  [ -s "$_ce" ] && [ -n "$(tail -c1 "$_ce")" ] && printf '\n' >> "$_ce"
  printf '# agy signs in through Google Cloud ADC (hub #234) -- written by the installer\nAGY_ADC_AUTH=true\n' >> "$_ce"
}

agy_status() {  # prints the account, or "set up", when the reviewer is already configured
  # Read off disk, not by running `agy`: the CLI is interactive — it opens its own screen and
  # waits — so there is nothing to ask it that does not take over the terminal.
  #
  # SEVERAL signals, because the sign-in does not land in one place, and every version of this
  # function so far has missed one:
  #   1. `oauth_creds.json` — the shape Google's own `gemini` CLI writes. agy is a fork of it and
  #      shares the folder, but a machine with ONLY agy on it need not have this file (that was
  #      the first miss: a Mac that had signed in was offered the sign-in again, 2026-08-19).
  #   2. `antigravity/antigravity_state.pbtxt` — the Antigravity **IDE**'s state.
  #   3. `antigravity-cli/jetski_state.pbtxt` — the **CLI**'s own, and the second miss: this
  #      installer installs the CLI, not the IDE, so on a machine that only ever had `agy` there
  #      is no `antigravity/` folder at all and only this one exists (user, on Windows 11,
  #      2026-08-19: `~/.gemini` held exactly `antigravity-cli` and `config`). It records the
  #      post-onboarding screens that were walked.
  #   4. `config/projects/` — agy writes a project file once one has been chosen, which is a
  #      thing that only happens after signing in.
  #   (An exported API key is NOT a sign of this. It used to be the fifth signal, and on a machine
  #   that never signed in it made this report the reviewer as set up and skip the sign-in, while
  #   agy, which signs in with the account, never reads the key -- hub #187, 2026-09-19.)
  #
  # Only the ACCOUNT is ever read. No credential file is opened for its contents — the `[ -s ]`
  # tests ask whether a file exists and is not empty, and nothing more.
  #   0. Google Cloud's ADC (hub #234): agy signs in with it when AGY_ADC_AUTH=true reaches it and the file exists --
  #      the existence only, like the rest.
  if [ -s "$(adc_file)" ] && adc_switch_on; then
    printf 'ADC (Google Cloud)'
    return 0
  fi
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
  if grep -q 'POST_ONBOARDING_STEP_TYPE' \
       "$HOME/.gemini/antigravity-cli/jetski_state.pbtxt" 2>/dev/null; then
    printf 'set up'
    return 0
  fi
  if [ -n "$(find "$HOME/.gemini/config/projects" -name '*.json' 2>/dev/null | head -1)" ]; then
    printf 'set up'
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
  # The beta channel's copy has no link to judge ownership by. Its name is the claim: this script
  # makes that folder, and nothing but this script and an app moving it writes there.
  if [ -d "$SKILL_BETA_SRC" ]; then
    say "  removing the beta channel's copy of the method"
    run rm -rf "$SKILL_BETA_SRC"
  fi
  # Phase 1's desk engine, one folder per pin and platform. Nothing but the method writes there,
  # and ~30 MB left behind is not a courtesy -- it is a binary nobody can account for later.
  if [ -d "$ENGINE_HOME" ]; then
    say "  removing Phase 1's desk engine ($(pretty "$ENGINE_HOME"))"
    run rm -rf "$ENGINE_HOME"
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

say "  What is here, and what will be installed:"
if on_mac; then
  if [ "$HAVE_CLT" = 1 ] && broken_tool git; then
    step "Apple's Command Line Tools are installed, but git does not run"
    stop 1 "it said: $RUNS_OK_SAID" \
           "A macOS update can leave the tools like this. A working git:  brew install git" \
           "(this installer and the app pick /opt/homebrew/bin first), then run this again."
  elif [ "$HAVE_CLT" = 1 ]; then say "    ✓ Apple's Command Line Tools (git)"; else say "    – Apple's Command Line Tools (git)   will install"; fi
elif ! usable git; then
  step "git is required and is not installed"
  stop 1 "Install git with your package manager, then run this again."
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
# `gh` already on the machine means the answer was given on an earlier run (or by whoever installed
# it), so its backup sign-in stays offered; otherwise it comes only with `--github`. Nothing
# outward-facing rides on this: the installer never pushes a project anywhere (SCR-049).
if [ "$WANT_GITHUB" = "auto" ]; then
  if [ "$HAVE_GH" = 1 ]; then WANT_GITHUB=1; else WANT_GITHUB=0; fi
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
if [ -n "$PLUGIN_ROOT" ]; then
  say "    • the tuning method — this plugin, v$PLUGIN_VERSION, checked against its signed release (not cloned)"
else
  say "    • the tuning method — its references and tools           github.com/ayukhno/autosound-tuning-skill"
fi
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
if [ -n "$_opts" ]; then
  say "  To leave something out, answer n and re-run with an option:${_opts%,}. --help lists them all."
fi
if [ "$MODE" = "tcc" ] && [ "$WANT_OMP" = 0 ] && [ "$HAVE_OMP" = 0 ]; then
  say "  Optional: --with-omp also installs omp, so the app can offer models other than Claude"
  say "  (billed per use; nothing goes through it unless you pick such a model)."
fi
if [ "$WANT_GITHUB" = 0 ]; then
  say "  Optional: --github also installs GitHub's gh, to back each car's record up to a free, private"
  say "  repository — the ledger, the journal, the DSP config backups; the measurements stay on your disk."
fi
consent
going_ahead

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
    say "  would open Apple's own installer window for the Command Line Tools (one click)"
  else
    say "  Apple's Command Line Tools are missing. Its own installer window opens in a moment —"
    say "  one click there, and this script waits for it. No password is typed into this script."
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# UNATTENDED — from here to the checks, nothing needs a person.
# ═════════════════════════════════════════════════════════════════════════════

# ── Apple's Command Line Tools: git, and the python3 behind the shim ──────────
if on_mac && [ "$HAVE_CLT" = 0 ]; then
  step "Apple's Command Line Tools (git)"
  if [ "$DRY_RUN" = 1 ]; then
    say "  would run: xcode-select --install, then wait for Apple's window to finish"
  else
    # The `softwareupdate -i` route that used to live here needed the root ticket this script no
    # longer takes. It bought a windowless install; it cost a password typed into a pipe.
    if ! clt_present; then
      say "  Apple's own installer window opens now. Click Install, then Agree, and let it finish —"
      say "  this waits for it. (Do not pick \"Get Xcode\": that is 12 GB and not needed.)"
      xcode-select --install >/dev/null 2>&1 || true
      _waited=0
      until clt_present; do
        sleep 10; _waited=$((_waited + 10))
        [ $((_waited % 120)) -eq 0 ] && say "  still waiting for the Command Line Tools… ($((_waited / 60)) min)"
        if [ "$_waited" -ge 2400 ]; then
          stop 1 "40 minutes and no Command Line Tools. When that window has finished, run the same" \
                 "install line again — everything already downloaded stays."
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
# What can be said of <ref> by its name alone, each said on a line (skill #99, #101). 0 = settled, nothing to check:
# a dry run, AUTOSOUND_SKIP_TAG_VERIFY=1, a name that is not a release (only ever one named with --skill-ref or
# --tcc-ref: installed, and said UNSIGNED), a tag before <first signed tag>. 1 = its signature has to be checked.
# TCC's `_verdict_by_name`: the app's tag is fetched only when it must be.
settled_by_name() {  # settled_by_name <ref> <first signed tag>
  _sn_ref="$1"; _sn_from="$2"
  if [ "$DRY_RUN" = 1 ]; then say "  would check the signature of $_sn_ref"; return 0; fi
  if [ "${AUTOSOUND_SKIP_TAG_VERIFY:-}" = 1 ]; then
    warn "the signature of $_sn_ref is NOT checked: AUTOSOUND_SKIP_TAG_VERIFY=1 is set (a developer's switch)"
    return 0
  fi
  # Only the rule's own "no" settles a name: any other failure of it goes on to the signature, which refuses.
  _sn_rel=0; is_release_tag "$_sn_ref" || _sn_rel=$?
  if [ "$_sn_rel" = 1 ]; then
    warn "$_sn_ref is not a release: it is installed UNSIGNED, unchecked"
    return 0
  fi
  [ "$_sn_rel" = 0 ] || return 1
  _sn_ver="${_sn_ref#beta-}"; _sn_ver="${_sn_ver%%-rc*}"
  if [ "$(printf '%s\n%s\n' "$_sn_from" "$_sn_ver" | sort -V | head -1)" != "$_sn_from" ]; then
    say "  $_sn_ref predates signed tags (they start at $_sn_from) -- installed without a signature check"
    return 0
  fi
  return 1
}

# Is <ref>, fetched into <dir>, a signed release (skill #99)? 0 = yes -- or it is settled by its name, above. 1 = it
# is not, and nothing may be installed from it. <first signed tag> and <whose> are the method's unless given: the
# app's own tags pass TCC_SIGNED_FROM and "TCC" (skill #101).
#   A good signature is one answer only (T-35, #142): git's exit 0 and ssh-keygen's line `Good "git" signature for
# <principal> with ...`, whatever the person's git or GPG configuration says. ssh-keygen is named for the check, so a
# sign-only helper set as gpg.ssh.program (1Password's, for one) is not asked to verify; and git picks the verifier
# from the signature, not from gpg.format, so an OpenPGP tag the person's own gpg calls good exits 0 with "Good" too.
# gpg.minTrustLevel is held at `fully`, git's rating of a key in allowed_signers: a person's `ultimate` made git refuse
# every good release, with the Good line printed. It loosens nothing -- the sentence still decides.
verify_tag() {  # verify_tag <dir> <ref> [<first signed tag> <whose>]
  _vt_dir="$1"; _vt_ref="$2"; _vt_from="${3:-$SKILL_SIGNED_FROM}"; _vt_whose="${4:-the skill}"
  settled_by_name "$_vt_ref" "$_vt_from" && return 0
  _vt_signers="$(mktemp)"
  printf '%s namespaces="git" %s\n' "$SKILL_SIGNING_PRINCIPAL" "$SKILL_SIGNING_KEY" > "$_vt_signers"
  _vt_rc=0
  _vt_said="$(git -C "$_vt_dir" -c gpg.format=ssh -c gpg.ssh.program=ssh-keygen -c gpg.minTrustLevel=fully \
                -c gpg.ssh.allowedSignersFile="$_vt_signers" verify-tag "$_vt_ref" 2>&1)" || _vt_rc=$?
  rm -f "$_vt_signers"
  if [ "$_vt_rc" = 0 ] && printf '%s\n' "$_vt_said" \
       | grep -q "^Good \"git\" signature for $SKILL_SIGNING_PRINCIPAL with "; then
    say "  ✓ $_vt_ref is signed by $_vt_whose's author"; return 0
  fi
  # A git that cannot check is not a bad signature (TCC's `_CANNOT_CHECK`) -- git's own sentences, whole, never a
  # word of them: a bare "-Y" matched a signing helper's text and blamed git's age. Before 2.34 git does not know
  # gpg.format=ssh; from 2.34 it names an ssh-keygen older than OpenSSH 8.2 (which has no -Y) in a sentence of its
  # own; with no ssh-keygen it cannot run one ("spawn" in Git for Windows). Refused all the same.
  case "$_vt_said" in
    *"unsupported value for gpg.format"*|*"ssh-keygen -Y find-principals/verify"*|*"illegal option -- Y"*|\
    *"unknown option -- Y"*|*"cannot run ssh-keygen"*|*"cannot spawn ssh-keygen"*)
      warn "the signature of $_vt_ref could not be checked here -- it is not installed:"
      printf '%s\n' "$_vt_said" | tail -2 | sed 's/^/      /' >&2
      warn "this git ($(git --version 2>/dev/null)) or its ssh-keygen may be too old to check one:" \
           "git 2.34 or newer, with OpenSSH 8.2 or newer, is needed"
      return 1 ;;
  esac
  warn "the signature of $_vt_ref does not check out -- it is not installed:"
  printf '%s\n' "$_vt_said" | tail -2 | sed 's/^/      /' >&2
  warn "a release of $_vt_whose is signed by its author; this one is not, or not by that key."
  return 1
}

# The installed clone has changes somebody made by hand -- a session patching a crash on the Windows VM (skill
# #91). They used to stop every update with "check the network". Now they are kept as a patch by the NEW tag's
# upkeep.py (fetched and verified: the clone's own version may predate the script), sent to the skill only on the
# person's word, and the clone is reset so the update can go ahead.
keep_local() {  # keep_local <dir> <what>; 0 = kept and reset, 1 = left as it was
  _kl_dir="$1"; _kl_what="$2"
  warn "$_kl_what has local changes -- somebody edited the installed copy:"
  git -C "$_kl_dir" status --porcelain --untracked-files=all | cut -c4- | sed 's/^/      /' >&2
  if [ "$DRY_RUN" = 1 ]; then say "  would keep them as a patch in $(pretty "$LOCAL_CHANGES"), then reset"; return 0; fi
  _kl_py="$(command -v python3 || true)"
  _kl_tmp="$(mktemp -d)"
  for _kl_f in scripts/upkeep.py rew_tool/gates/side_effect.py rew_tool/console.py; do
    mkdir -p "$_kl_tmp/skills/autosound-tuning/$(dirname "$_kl_f")"
    git -C "$_kl_dir" show "FETCH_HEAD:skills/autosound-tuning/$_kl_f" \
      > "$_kl_tmp/skills/autosound-tuning/$_kl_f" 2>/dev/null || true
  done
  if [ -z "$_kl_py" ] || [ ! -s "$_kl_tmp/skills/autosound-tuning/scripts/upkeep.py" ]; then
    warn "they cannot be kept automatically here (no python3, or the new version has no upkeep.py)."
    warn "keep them yourself (git -C $(pretty "$_kl_dir") stash), then run this again; nothing was changed."
    rm -rf "$_kl_tmp"; return 1
  fi
  say "  they are kept as a patch in $(pretty "$LOCAL_CHANGES") before the update -- nothing is lost."
  say "  Sent to the skill as an issue, the patch tells its author what had to be fixed by hand."
  _kl_send=""
  if offer "Enter = send it · s = keep it only here:"; then _kl_send="--send"; fi
  if "$_kl_py" "$_kl_tmp/skills/autosound-tuning/scripts/upkeep.py" --clone "$_kl_dir" keep-local ${_kl_send:+"$_kl_send"}; then
    rm -rf "$_kl_tmp"; return 0
  fi
  rm -rf "$_kl_tmp"
  warn "the changes were not kept, so nothing was reset or updated -- see above."
  return 1
}

# Is HEAD in <dir> the commit <rev> names? Both asked of git; a HEAD it cannot name (a copy with nothing checked out
# yet) is not.
head_is() {  # head_is <dir> <rev>
  _hi_at="$(git -C "$1" rev-parse --verify --quiet HEAD 2>/dev/null)" || _hi_at=""
  [ -n "$_hi_at" ] && [ "$_hi_at" = "$(git -C "$1" rev-parse --verify --quiet "$2" 2>/dev/null)" ]
}

# Put a checkout of the method at <dir> on <ref>: move it when it is already a checkout, make one
# when there is none. ONE function for both copies -- the terminal's and the beta channel's
# (autosound-hub #145) -- so a lesson learned on one cannot miss the other. <what> names the copy
# in a warning.
#   A copy is the tag it checked (T-45, #142). A release is fetched INTO refs/tags/<ref> and checked out from there,
# and HEAD is then held to that tag's commit: `git clone --branch <ref>` took a branch of the same name over the tag,
# and the check read the tag. In refs/tags `describe` names it too: fetched by bare name, a tag stored no ref, and the
# copy was named by a bare sha ("the terminal stays on bc6423e", Windows VM, 2026-09-14). Any other name -- a branch
# or a sha, only ever one named with --skill-ref, and installed UNSIGNED -- is fetched by name and checked out from
# FETCH_HEAD. Against the COMMIT (`^{commit}`): an annotated tag, every release, is a tag object that HEAD never equals.
#   0 = done; 1 = nothing was fetched or kept -- no new copy was made (the fetch failed, or something that is not a
# checkout is at <dir>), or an update was not made and the copy is where it was (its fetch failed, or its local changes
# could not be kept: a warning once, and the run ended "Installed." on the old version -- R32, #142); 2 = <ref>'s
# signature did not check out, nothing of it checked out; 3 = HEAD was not <ref> after the checkout: a new copy is
# removed, an update put back.
checkout_method() {
  _co_dir="$1"; _co_ref="$2"; _co_what="$3"
  _co_spec="$_co_ref"; _co_want="FETCH_HEAD^{commit}"
  if is_release_tag "$_co_ref"; then
    _co_spec="+refs/tags/$_co_ref:refs/tags/$_co_ref"; _co_want="refs/tags/$_co_ref^{commit}"
  fi
  if [ -d "$_co_dir/.git" ]; then
    # CHECKED, both of them. Unchecked, a network blip or a moved ref left the method sitting on
    # the previous version while this script printed "updating to <ref>" and carried on -- the one
    # failure mode where the user is told the opposite of what happened (HUB-042).
    if ! run git -C "$_co_dir" fetch --quiet --depth 1 origin "$_co_spec"; then
      warn "could not fetch $_co_ref for $_co_what -- it is STILL at" \
           "$(git -C "$_co_dir" describe --tags --always 2>/dev/null || echo unknown)."
      warn "check the network, then re-run this script; nothing was changed."
      return 1
    fi
    # What was fetched is checked before anything of it runs or is checked out (skill #99), and a clone with
    # local changes is kept as a patch rather than refused with the wrong reason (skill #91).
    verify_tag "$_co_dir" "$_co_ref" || return 2
    if [ -n "$(git -C "$_co_dir" status --porcelain --untracked-files=all 2>/dev/null)" ]; then
      keep_local "$_co_dir" "$_co_what" || return 1
    fi
    _co_was="$(git -C "$_co_dir" rev-parse --verify --quiet HEAD 2>/dev/null)" || _co_was=""
    run git -c advice.detachedHead=false -C "$_co_dir" checkout --quiet "$_co_want" || true
    if [ "$DRY_RUN" = 1 ] || head_is "$_co_dir" "$_co_want"; then return 0; fi
    # Put back: the tree was clean before this checkout (local changes are kept above first), so --force drops only
    # what a checkout that broke off left behind.
    [ -z "$_co_was" ] || git -c advice.detachedHead=false -C "$_co_dir" checkout --quiet --force "$_co_was" || true
    warn "the update did not take: HEAD was not $_co_ref after the checkout; $_co_what is back at" \
         "$(git -C "$_co_dir" describe --tags --always 2>/dev/null || echo unknown)."
    return 3
  fi
  if [ "$DRY_RUN" = 1 ]; then
    say "  would fetch $_co_ref into $(pretty "$_co_dir"), check it, and check it out"
    return 0
  fi
  # Made here, so removed here when it fails -- never a folder that was at that path before: `git clone` refused one.
  if [ -e "$_co_dir" ] && { [ ! -d "$_co_dir" ] || [ -n "$(ls -A "$_co_dir" 2>/dev/null)" ]; }; then
    warn "$(pretty "$_co_dir") is there, and is not a checkout -- move it aside, then run this again"
    return 1
  fi
  if ! git init --quiet "$_co_dir" || ! git -C "$_co_dir" remote add origin "$SKILL_REPO" \
     || ! git -C "$_co_dir" fetch --quiet --depth 1 origin "$_co_spec"; then
    rm -rf "$_co_dir"; return 1
  fi
  # Checked before anything of it is checked out (skill #99), and removed when it fails: nothing unverified stays.
  verify_tag "$_co_dir" "$_co_ref" || { rm -rf "$_co_dir"; return 2; }
  git -c advice.detachedHead=false -C "$_co_dir" checkout --quiet "$_co_want" || true
  head_is "$_co_dir" "$_co_want" && return 0
  warn "the new copy is not $_co_ref after its checkout -- it is removed; nothing was installed."
  rm -rf "$_co_dir"
  return 3
}

# The method's version (T-37, #142): the name given with --skill-ref, or the newest release tag. A release goes on to
# its signature; any other name -- a branch, a sha -- is installed as it stands, and said. When no release tag can be
# read and none was named, nothing is installed: an empty `ls-remote` (no network, a proxy) installed an unchecked
# `main`, and moved a copy already verified onto it. The ref is all that goes to stdout -- the caller takes it with
# $(...) -- and installer-consistency.py runs this with a `git` that has no network.
pick_method_ref() {  # pick_method_ref <the --skill-ref name, or "">
  if [ -n "$1" ]; then
    is_release_tag "$1" || warn "$1 is not a release: it is installed UNSIGNED, unchecked"
    printf '%s\n' "$1"
    return 0
  fi
  # Release-shaped tags only (skill #108): `sort -V` put a `v3.x` above every release.
  _pm_ref="$(git ls-remote --tags --refs "$SKILL_REPO" "$SKILL_TAG_GLOB" 2>/dev/null \
      | awk -F/ '{print $NF}' | newest_on_channel)" || _pm_ref=""
  if [ -z "$_pm_ref" ]; then
    _pm_why="could not read the method's release tags (no network?) -- nothing was installed or changed for the method;"
    stop 1 "$_pm_why run again when GitHub answers, or name a tag with --skill-ref"
  fi
  printf '%s\n' "$_pm_ref"
}

step "The tuning method"
if [ -n "$PLUGIN_ROOT" ]; then
  # The plugin's copy is the method: checked, not cloned, and every later step reads it where it is.
  SKILL_HOME="$PLUGIN_ROOT/skills/autosound-tuning"
  SKILL_REF="v$PLUGIN_VERSION"
  say "  this plugin: $SKILL_REF at $(pretty "$PLUGIN_ROOT")"
  if [ "$DRY_RUN" = 1 ]; then
    say "  would check it against its signed release: python3 upkeep.py verify-copy --root $(pretty "$PLUGIN_ROOT")"
  elif ! usable python3; then
    stop 1 "stopped: python3 is needed to check this plugin copy against its signed release, and it does not run here"
  elif python3 "$SKILL_HOME/scripts/upkeep.py" verify-copy --root "$PLUGIN_ROOT"; then
    :
  else
    stop 1 "stopped: this plugin copy is not $SKILL_REF as its author signed it -- see above; nothing was installed"
  fi
else
  # The newest 3.x tag unless one is named. Asked for by name rather than "main": main is where
  # development lands, and an installer should put you on a release unless you say otherwise. On
  # EITHER channel: this is the copy Claude Code in a terminal loads, and the terminal runs releases
  # (autosound-hub #145). A candidate goes into its own copy, below.
  # $(...) is a subshell: the stop inside it has said why and written the receipt, and `stop $?` carries its code out
  # as this shell's own stop -- a bare exit here would read to going_ahead's trap as a failure nobody explained.
  SKILL_REF="$(pick_method_ref "$SKILL_REF")" || stop $?
fi
if [ -z "$PLUGIN_ROOT" ]; then
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
  _co_rc=0; checkout_method "$SKILL_SRC" "$SKILL_REF" "the method" || _co_rc=$?
  if [ "$_co_rc" = 2 ]; then stop 1 "stopped: $SKILL_REF is not a signed release of the method -- see above; the installed one is untouched"; fi
  # R32: not fetched, or local changes not kept -- the copy is where it was, and that is a stop, as a failed new copy.
  if [ "$_co_rc" = 1 ]; then stop 1 "update failed -- see above"; fi
  if [ "$_co_rc" != 0 ]; then stop 1 "stopped: the method could not be put on $SKILL_REF -- see above; it is back where it was"; fi
  # T-38 (#142): a re-run repairs the link. Removed -- by hand, by a tidy-up -- it left the method installed and
  # invisible to Claude Code, while every re-run said "updating". Only a missing one: a link that is not ours, or a
  # real folder, was left and warned about above, as for a new copy.
  if [ ! -L "$SKILL_HOME" ]; then
    if [ "$DRY_RUN" = 1 ]; then
      say "  would make the missing link ~/.claude/skills/autosound-tuning again"
    else
      say "  the link ~/.claude/skills/autosound-tuning was missing — made again"
      rm -f "$SKILL_HOME"
      ln -s "$SKILL_SRC/skills/autosound-tuning" "$SKILL_HOME"
    fi
  fi
else
  say "  into ~/.claude/skills/autosound-tuning"
  if [ "$DRY_RUN" = 0 ]; then mkdir -p "$(dirname "$SKILL_HOME")"; fi
  _co_rc=0; checkout_method "$SKILL_SRC" "$SKILL_REF" "the method" || _co_rc=$?
  if [ "$_co_rc" = 2 ]; then stop 1 "stopped: $SKILL_REF is not a signed release of the method -- see above"; fi
  if [ "$_co_rc" != 0 ]; then stop 1 "clone failed — see above"; fi
  if [ "$DRY_RUN" = 0 ]; then
    rm -f "$SKILL_HOME"
    ln -s "$SKILL_SRC/skills/autosound-tuning" "$SKILL_HOME"
  fi
fi

# The beta channel's copy (autosound-hub #145): the newest release OR candidate, in a checkout of
# its own that no link points at. Claude Code in a terminal never loads it; an app that asks for
# beta runs it by path and declares it in AUTOSOUND_SKILL_ROOT, which rew_tool/deployment.py
# checks. A failure here is no stop -- the terminal's method above is already in place -- but the copy the channel was
# asked for is not this run's candidate, so it counts as missing (R38, #142): the run ends 3, not 0.
if [ "$CHANNEL" = "beta" ]; then
  SKILL_BETA_REF="$(git ls-remote --tags --refs "$SKILL_REPO" "$SKILL_TAG_GLOB" "$SKILL_BETA_GLOB" 2>/dev/null \
      | awk -F/ '{print $NF}' | newest_on_channel)" || SKILL_BETA_REF=""
  if [ -z "$SKILL_BETA_REF" ]; then
    warn "could not read the method's candidates -- the beta channel's copy was left as it is"
    missing "the beta copy"
  else
    say "  beta channel: $SKILL_BETA_REF in $(pretty "$SKILL_BETA_SRC") -- only an app that asks for beta runs it"
    if ! checkout_method "$SKILL_BETA_SRC" "$SKILL_BETA_REF" "the beta channel's copy"; then
      warn "the beta channel's copy is not on $SKILL_BETA_REF -- see above; the terminal's method is not affected"
      missing "the beta copy"
    fi
  fi
fi
fi   # not --plugin

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
elif broken_tool python3; then
  warn "python3 is here and the Command Line Tools are installed, but it does not run:"
  warn "  $RUNS_OK_SAID"
  warn "  brew install python gives a working one; the method's tools cannot run until then"
elif ! usable python3; then
  warn "no python3 — the method's tools cannot run at all until there is one"
else
  # WHICH interpreter: the one `python3` resolves to, because that is literally how the method
  # invokes its tools (`python3 rew_tool/...`). Not TCC's venv — different process.
  # HOW depends on what that interpreter is. On a stock Mac it is Apple's 3.9 at /usr/bin/python3,
  # whose site-packages live under /Library and need root — `--user` writes to ~/Library/Python
  # instead, which that interpreter already has on its path. Inside a venv the reverse holds:
  # `--user` is refused outright. So ask the interpreter which it is.
  # `--upgrade` (skill #98): without it a machine kept whatever numpy, scipy and matplotlib it got first, while CI
  # tests the newest -- every updated machine ran on a set nobody had tested.
  PY_BIN="$(command -v python3)"
  say "  into $PY_BIN ($("$PY_BIN" -V 2>&1))"
  _pip_ok=1
  if "$PY_BIN" -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)' 2>/dev/null; then
    run "$PY_BIN" -m pip install --quiet --upgrade --no-warn-script-location --disable-pip-version-check -r "$REQS" \
      || _pip_ok=0
  else
    run "$PY_BIN" -m pip install --quiet --upgrade --user --no-warn-script-location --disable-pip-version-check -r "$REQS" \
      || _pip_ok=0
  fi
  # Judged by what it was to produce (#142), as install.ps1 judges it: pip's own code is not the answer -- it fails
  # over libraries that are already there, and Ubuntu's own python3 refuses `--user` outright (externally managed).
  # What is missing counts in the checks below.
  if [ "$DRY_RUN" != 1 ]; then
    if ! "$PY_BIN" -c "import numpy, scipy" 2>/dev/null; then
      warn "numpy/scipy did not install -- the method's tools will fail on import."
    elif [ "$_pip_ok" = 0 ]; then
      say "  (pip reported an error, but numpy and scipy import fine -- already installed)"
    fi
  fi
fi

# ── Phase 1's desk engine ─────────────────────────────────────────────────────
# Two ways to have one, and the method takes whichever is there: this archive (~30 MB, nothing else
# needed) or the .NET SDK, which builds the wrapper on first use. See WANT_ENGINE above for why the
# default fetches only where there is no SDK. The method computes the file's name itself, checks
# what arrives against the release's SHA256SUMS, and refuses a file that does not match -- so this
# step names the tag and reads back what the method says it did.
step "Phase 1's desk engine"
ENGINE_PY="${SKILL_REAL:-$SKILL_HOME}/rew_tool/resonalyze_engine.py"
have_dotnet() { find_bin dotnet >/dev/null 2>&1 || [ -x "$HOME/.dotnet/dotnet" ]; }
# T-40 (#142): the SDK builds the wrapper from the method's own checkout -- `git submodule update` fetches the fork --
# and a plugin copy is none (no .git above it): there `auto` fetches the prebuilt engine, as where there is no SDK.
METHOD_IS_CHECKOUT=1
if [ -n "$PLUGIN_ROOT" ] && [ ! -e "$PLUGIN_ROOT/.git" ]; then METHOD_IS_CHECKOUT=0; fi
ENGINE_DID=""
if [ "$WANT_ENGINE" = 0 ]; then
  ENGINE_DID="not fetched: --no-engine"
  say "  --no-engine: not fetched. It builds from the .NET SDK on first use, or later with"
  say "    python3 $(pretty "$ENGINE_PY") fetch-binary --tag $SKILL_REF"
elif [ "$WANT_ENGINE" = "auto" ] && [ "$METHOD_IS_CHECKOUT" = 1 ] && have_dotnet && [ "$DRY_RUN" = 0 ] && usable python3 \
     && [ -f "$ENGINE_PY" ]; then
  # The Arbiter, 2026-09-23: the engine is installed WITH the skill and checked -- built now, not on first use.
  say "  the .NET SDK is here — building the engine from the method's own checkout now, then running it once"
  say "  (--engine fetches the prebuilt one instead: no build, no SDK needed)"
  if ENGINE_SAID="$(python3 "$ENGINE_PY" check --build 2>&1)"; then
    ENGINE_DID="built from the .NET SDK and checked: it runs"
    say "$ENGINE_SAID"
  else
    ENGINE_DID="built or run failed: $(printf '%s' "$ENGINE_SAID" | tail -1)"
    warn "the engine did not build or run — the method is installed and works; Phase 1's desk step waits for it:"
    warn "$(printf '%s' "$ENGINE_SAID" | tail -3)"
  fi
elif [ "$WANT_ENGINE" = "auto" ] && [ "$METHOD_IS_CHECKOUT" = 1 ] && have_dotnet; then
  ENGINE_DID="not built: the .NET SDK is here and builds it on first use"
  say "  the .NET SDK is here — the engine builds from the method's own checkout on first use"
elif ! usable python3; then
  ENGINE_DID="not fetched: no working python3"
  warn "no python3 — the engine cannot be fetched; the method's tools cannot run either (above)"
elif [ "$DRY_RUN" = 1 ]; then
  say "  would run: python3 $(pretty "$ENGINE_PY") fetch-binary --tag $SKILL_REF"
elif [ ! -f "$ENGINE_PY" ]; then
  ENGINE_DID="not fetched: the method's checkout was not where this script expected it"
  warn "no $(pretty "$ENGINE_PY") — the method's checkout is not where this script expects it;"
  warn "the engine was not fetched, and Phase 1's desk step will ask for one when it is reached"
else
  [ "$METHOD_IS_CHECKOUT" = 1 ] || ! have_dotnet \
    || say "  the .NET SDK is here, but a plugin copy is no checkout to build the engine from — fetching it"
  say "  ~30 MB for $SKILL_REF, checked against the release's SHA256SUMS"
  ENGINE_RC=0
  python3 "$ENGINE_PY" fetch-binary --tag "$SKILL_REF" || ENGINE_RC=$?
  # fetch-binary's answers (T-44, #142), written into the receipt in install.ps1's words: 0 installed -- fetched now, or
  # already here from this tag, with nothing downloaded -- · 3 refused · 4 none for this machine · 5 no answer.
  case "$ENGINE_RC" in
    0) ENGINE_DID="installed for $SKILL_REF and checked against SHA256SUMS"
       # ...and run once: a file that matches its checksum can still fail to start on this machine.
       if ENGINE_SAID="$(python3 "$ENGINE_PY" check 2>&1)"; then
         ENGINE_DID="$ENGINE_DID; it runs"
         say "$ENGINE_SAID"
       else
         ENGINE_DID="$ENGINE_DID; but it does not run: $(printf '%s' "$ENGINE_SAID" | tail -1)"
         warn "the engine was fetched but does not run here — Phase 1's desk step waits for it:"
         warn "$(printf '%s' "$ENGINE_SAID" | tail -3)"
       fi ;;
    3) ENGINE_DID="refused: the archive for $SKILL_REF does not match its SHA256SUMS -- nothing installed"
       warn "the engine's archive for $SKILL_REF does not match its SHA256SUMS — refused, nothing installed;"
       warn "the method is installed and works; Phase 1's desk step is the part that waits for an engine" ;;
    4) ENGINE_DID="not fetched: $SKILL_REF carries no engine for this machine"
       say "  so the engine builds from the .NET SDK when there is one; nothing else is affected" ;;
    5) ENGINE_DID="not fetched: the release could not be reached -- run the installer again later"
       warn "the release could not be reached -- run the installer again later; the method is installed and works,"
       warn "and Phase 1's desk step is the part that waits for an engine" ;;
    *) ENGINE_DID="not fetched: fetch-binary failed (code $ENGINE_RC)"
       warn "the engine was not fetched (code $ENGINE_RC) — the method is installed and works;"
       warn "Phase 1's desk step is the part that waits for an engine" ;;
  esac
fi

# ── the desktop app ───────────────────────────────────────────────────────────
# The app's tag is checked like the method's before uv installs it (skill #101, hub #224 TCC-038): uv checks no
# signature. The mirror of TCC's own updater (core/updates.py `check_tcc_tag`): there is no clone of TCC on disk, so
# the one tag is fetched into a temporary BARE repository and verified there. 0 = install it, and TCC_SHA is the
# commit the verified tag names -- "" when nothing was verified (settled by its name); 1 = it is not installed.
check_tcc_tag() {  # check_tcc_tag <ref>
  _ct_ref="$1"; TCC_SHA=""
  settled_by_name "$_ct_ref" "$TCC_SIGNED_FROM" && return 0
  _ct_git="$(mktemp -d)"
  _ct_rc=0
  _ct_said="$(git init --quiet --bare "$_ct_git" 2>&1 &&
              git -C "$_ct_git" fetch --quiet --no-tags --depth 1 "$TCC_REPO" "+refs/tags/$_ct_ref:refs/tags/$_ct_ref" 2>&1)" \
    || _ct_rc=$?
  if [ "$_ct_rc" != 0 ]; then
    warn "could not fetch $_ct_ref to check its signature -- it is not installed:"
    printf '%s\n' "$_ct_said" | tail -2 | sed 's/^/      /' >&2
    rm -rf "$_ct_git"; return 1
  fi
  if ! verify_tag "$_ct_git" "$_ct_ref" "$TCC_SIGNED_FROM" "TCC"; then rm -rf "$_ct_git"; return 1; fi
  TCC_SHA="$(git -C "$_ct_git" rev-parse --verify --quiet "refs/tags/$_ct_ref^{commit}" 2>/dev/null)" || TCC_SHA=""
  rm -rf "$_ct_git"
  # Fail closed, as TCC does: a verified tag whose commit git cannot name is not installed unpinned.
  [ -n "$TCC_SHA" ] || { warn "git names no commit for $_ct_ref, verified a moment ago -- it is not installed"; return 1; }
}
# Does <ref> still name <sha>? TCC's "moved" check (core/updates.py `tcc_install_script`), right before uv: uv asks
# for the tag by NAME -- the name is what TCC reads back as its version -- so the name must still peel to the commit
# that was verified. A tag moved since, a lightweight one put in its place (no ^{} line) or no answer: no.
tcc_tag_still_at() {  # tcc_tag_still_at <ref> <sha>
  [ "$(git ls-remote "$TCC_REPO" "refs/tags/$1^{}" 2>/dev/null | cut -f1)" = "$2" ]
}

TCC_BIN=""
UV=""
# Why the app's tag was not installed, when it was not (skill #101); said in its block, in the checks, and last.
TCC_REFUSED=""
TCC_SHA=""
if [ "$MODE" = "tcc" ]; then
  step "Autosound TCC — the desktop app"
  UV="$(find_bin uv || true)"
  if [ -n "$UV" ]; then
    say "  ✓ $("$UV" --version 2>/dev/null || echo uv) — installs the app's own Python"
  else
    say "  uv first (astral.sh/uv/install.sh) — it brings a Python 3.12 of its own, so nothing on"
    say "  this machine has to be the right version:"
    # PINNED. `astral.sh/uv/install.sh` is whatever uv released this morning; the versioned URL
    # is the same file at a fixed point, and it is the vendor's own (HUB-031). We cannot sign
    # somebody else's script -- we can stop it from changing under us between two runs of the
    # same installer. To raise it: check github.com/astral-sh/uv/releases and commit the new
    # number here AND in install.ps1; installer-consistency.py fails if the two drift apart.
    say "  from astral.sh, uv's own installer, pinned at $UV_VERSION"
    if run sh -c "curl -LsSf https://astral.sh/uv/$UV_VERSION/install.sh | sh -s -- --quiet"; then
      export PATH="$LOCAL_BIN:$PATH"
      in_local_bin uv && manifest_add uv
      UV="$(find_bin uv || true)"
    else
      warn "uv did not install; without it there is no app. Carrying on with the method alone,"
      warn "which is fully usable — the app can be added by re-running this later."
      # The app was asked for: not ready without it (#142), though the checks below no longer look for it.
      MODE="terminal"; missing TCC
    fi
  fi
fi
if [ "$MODE" = "tcc" ]; then
  say "  the app and what it needs, about 700 MB — a few minutes, no output until it is done…"
  # `--python` is not optional here. Without it `uv tool install` used the system interpreter —
  # 3.9.6 on a stock macOS — and refused with "does not satisfy Python>=3.11", which reads as a
  # broken package rather than a missing Python (2026-08-12).
  [ -n "$UV" ] || UV=uv
  # The app is asked for BY TAG, exactly as the method is above. With no ref, `git+URL` means HEAD
  # of the default branch: a fresh install handed somebody unfinished work, and the app's own
  # update button -- which pins the newest tag -- then read that build as ahead of every release.
  # The two ways of getting the app have to agree, or "update" and "install" mean different
  # things on the same machine (SCR-054).
  TCC_REF_HOW=""
  if [ -z "$TCC_REF" ] && [ "$CHANNEL" = "beta" ]; then
    TCC_REF="$(git ls-remote --tags --refs "$TCC_REPO" "$TCC_TAG_GLOB" "$TCC_BETA_GLOB" 2>/dev/null \
        | awk -F/ '{print $NF}' | newest_on_channel)" || TCC_REF=""
    TCC_REF_HOW=" (beta channel)"
  elif [ -z "$TCC_REF" ]; then
    # Release-shaped tags only, as the method's (skill #108).
    TCC_REF="$(git ls-remote --tags --refs "$TCC_REPO" "$TCC_TAG_GLOB" 2>/dev/null \
        | awk -F/ '{print $NF}' | newest_on_channel)" || TCC_REF=""
  fi
  if [ -n "$TCC_REF" ]; then
    TCC_SPEC="autosound-tcc[gui,claude] @ git+${TCC_REPO}@${TCC_REF}"
    say "  version $TCC_REF$TCC_REF_HOW"
    # Its signature, before uv sees it (skill #101). A tag that does not check out is not installed, and the
    # method's install goes on without it. A name that is not a release (--tcc-ref) is said UNSIGNED there.
    check_tcc_tag "$TCC_REF" || TCC_REFUSED="$TCC_REF could not be shown to be a signed release of TCC"
  else
    # No tag could be read -- no network, a proxy: the app is not installed (T-37, #142). Its default branch was, with
    # nothing checked. The method goes on without it, and the checks below count the app as missing.
    TCC_REFUSED="could not read the app's release tags (no network?) -- run again when GitHub answers, or name a tag with --tcc-ref"
  fi
  if [ -z "$TCC_REFUSED" ] && [ -n "$TCC_SHA" ] && ! tcc_tag_still_at "$TCC_REF" "$TCC_SHA"; then
    TCC_REFUSED="$TCC_REF changed after its signature was checked, or the server did not answer"
  fi
  # skill #62: a launcher uv did not put there (TCC's own updater did) makes `uv tool install --upgrade` refuse
  # ("Executable already exists"), and on the Windows VM the refusal left the old app unable to start. So the
  # upgrade asks uv first: a tool it lists is upgraded, and a launcher it does not own is replaced, and said.
  TCC_FORCE=""
  if [ -z "$TCC_REFUSED" ] \
     && { [ -n "$(find_bin autosound-tcc 2>/dev/null || true)" ] || [ -e "${UV_TOOL_BIN_DIR:-$LOCAL_BIN}/autosound-tcc" ]; } \
     && ! "$UV" tool list 2>/dev/null | grep -q '^autosound-tcc '; then
    TCC_FORCE="--force"
    say "  the app's launcher here was not put there by uv (TCC's own updater did) — replacing it"
  fi
  if [ -n "$TCC_REFUSED" ]; then
    warn "the app is not installed: $TCC_REFUSED."
    warn "The method is installed and works without it; the end of this run says so again."
  elif run "$UV" tool install --quiet --python 3.12 --upgrade $TCC_FORCE "$TCC_SPEC"; then
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
    # The app builds ITSELF: `autosound-tcc --install-desktop` makes the bundle in ~/Applications,
    # registers it with Launch Services and puts the shortcut on the Desktop (SCR-056). What this
    # replaces was two guesses across a repository boundary. The builder was a script in THIS repo
    # found by path -- `$SKILL_SRC/scripts/…` with a fallback to `dirname $0`, which under
    # `curl … | bash` is whatever folder the person was standing in, and it once failed to be found
    # on a clean M1 (2026-08-13). And the icon came out of TCC's own package, read by name from
    # here; renaming it there would have removed the icon silently, with no error on either side.
    # Now the half that owns those details does the work, and this script reads an exit code.
    # Needs the app at v0.1.13 or newer, which is what the tag resolution above installs.
    if [ "$DRY_RUN" = 1 ]; then
      say "  would build \"$(pretty "$APP")\" and a shortcut on your Desktop"
    elif [ -n "$TCC_BIN" ]; then
      _bout="$("$TCC_BIN" --install-desktop 2>&1)" && _brc=0 || _brc=$?
      if [ "$_brc" = 0 ]; then
        _shortcut=""; [ -L "$DESKTOP_LINK" ] && _shortcut=", and a shortcut on your Desktop"
        say "  ✓ \"Autosound TCC.app\" in ~/Applications$_shortcut"
        # A warning, not an aside in brackets. It used to be one, and it scrolled past unread on
        # the one install where it mattered: the person sees a blank white icon days later and has
        # no way back to the line that explained it (user, 2026-08-19).
        # ⚠️ This matches TCC's OUTPUT by phrase, which is the same coupling SCR-056 removed at the
        # module level, reduced to a string: reword it there and this warning silently stops
        # appearing, with no error on either side. The two words "no icon" are load-bearing and
        # they know it (a comment on their side says so). If it ever needs to be firmer, they have
        # offered a machine-readable signal -- take it, and free the phrase on both sides.
        case "$_bout" in
          *"no icon"*)
            warn "the app has no icon — TCC's own was not found in the installed package."
            warn "Everything works; to fix just the icon, re-run this installer."
            ;;
        esac
      else
        printf '%s\n' "$_bout" >&2
        warn "the double-clickable app was not built (the app returned $_brc); the command still works:  autosound-tcc"
      fi
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
  # Every third-party script here says whose it is and what is about to run, before it runs --
  # the other three already did; this was the one that just went (HUB-031).
  elif say "  the official installer, omp.sh/install.sh:" && \
       run sh -c 'curl -fsSL https://omp.sh/install.sh | sh'; then
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
    # Straight from GitHub's releases, and CHECKED against the checksums the same release
    # publishes. Before this, whatever the download produced was made executable and put on PATH
    # unexamined -- a truncated transfer or a proxy handing back something else would have been
    # installed with the same confidence as the real thing (HUB-031). The checksum does not prove
    # who built it; it proves we got what that release says it has, which is the part we can
    # check without a signature.
    _ver="$(curl -fsSLI -o /dev/null -w '%{url_effective}' https://github.com/cli/cli/releases/latest 2>/dev/null \
              | sed 's#.*/tag/v##')" || _ver=""
    case "$(uname -m)" in arm64|aarch64) _arch=arm64 ;; *) _arch=amd64 ;; esac
    _tmp="$(mktemp -d)"
    _got=0
    if [ -n "$_ver" ]; then
      if on_mac; then _asset="gh_${_ver}_macOS_${_arch}.zip"
      else            _asset="gh_${_ver}_linux_${_arch}.tar.gz"
      fi
      _base="https://github.com/cli/cli/releases/download/v${_ver}"
      if curl -fsSL -o "$_tmp/$_asset" "$_base/${_asset}" &&
         curl -fsSL -o "$_tmp/checksums.txt" "$_base/gh_${_ver}_checksums.txt"; then
        # sha256sum on Linux, shasum -a 256 on a Mac. If NEITHER is there we do not install:
        # "could not check" is not "checked", and this is the one place where saying so costs a
        # backup feature nobody has set up yet.
        _want="$(awk -v a="$_asset" '$2 == a {print $1}' "$_tmp/checksums.txt")"
        _have=""
        if command -v sha256sum >/dev/null 2>&1; then _have="$(sha256sum "$_tmp/$_asset" | awk '{print $1}')"
        elif command -v shasum   >/dev/null 2>&1; then _have="$(shasum -a 256 "$_tmp/$_asset" | awk '{print $1}')"
        fi
        if [ -z "$_want" ] || [ -z "$_have" ]; then
          warn "gh: could not check the download (no checksum line, or no sha256 tool) — not installing it."
        elif [ "$_want" != "$_have" ]; then
          warn "gh: the download does NOT match the checksum GitHub publishes for it — not installing."
          warn "expected $_want"
          warn "got      $_have"
        else
          say "  checksum OK ($(printf '%.12s' "$_have")…)"
          if on_mac; then unzip -q "$_tmp/$_asset" -d "$_tmp" && _got=1
          else            tar -xzf "$_tmp/$_asset" -C "$_tmp" && _got=1
          fi
        fi
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

# ── the tools that were already here: updated on the person's word (skill #97, hub #219) ──
# Every tool above is installed only when it is missing, so each one kept its first version for good: omp stayed
# at 17.3.8 with 18.2.4 out (the Arbiter's second Mac, 2026-09-27). The update is the skill's one path, the one TCC
# calls too -- `upkeep.py tools`: each tool the way it was installed (Homebrew, its own `update`, gh's release).
# Only what was here before this run: a tool installed a minute ago is already the newest.
_had_tools=""
[ "$HAVE_CLAUDE" = 1 ] && _had_tools="$_had_tools claude"
[ "$HAVE_OMP" = 1 ] && _had_tools="$_had_tools omp"
[ "$HAVE_AGY" = 1 ] && _had_tools="$_had_tools agy"
[ "$HAVE_GH" = 1 ] && _had_tools="$_had_tools gh"
if [ -n "$_had_tools" ]; then
  step "The tools that were already here:$_had_tools"
  _upkeep="${SKILL_REAL:-$SKILL_HOME}/scripts/upkeep.py"
  _only=""
  for _t in $_had_tools; do _only="$_only --only $_t"; done
  if [ "$DRY_RUN" = 1 ]; then
    say "  would ask, then run: python3 $(pretty "$_upkeep") tools$_only"
  elif ! usable python3 || [ ! -f "$_upkeep" ]; then
    warn "no python3 or no upkeep.py beside the method -- the tools are left as they are"
  elif ask "Update them to their newest versions (each the way it was installed)?" y; then
    # shellcheck disable=SC2086  # _only is a list of flags on purpose
    python3 "$_upkeep" tools $_only \
      || warn "not every tool updated -- see above; each one that did not still works as it was"
  else
    say "  left as they are; the next run of this script asks again"
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
# Each part that is not ready is said here and named with `missing`; `finish`, last, gives the verdict (#142).
[ "$DRY_RUN" = 1 ] && say "  (the machine as it stands — nothing above was actually done)"
if [ -f "$SKILL_HOME/rew_tool/contract.py" ]; then
  # The libraries, judged by importing them with the python3 the method runs on (#142): numpy and scipy are what its
  # tools run on, matplotlib only draws their plots.
  _py_seen="$(command -v python3 || echo python3)"
  _numpy=0; usable python3 && python3 -c "import numpy" 2>/dev/null && _numpy=1
  _scipy=0; usable python3 && python3 -c "import scipy" 2>/dev/null && _scipy=1
  if [ "$_numpy$_scipy" = 11 ]; then
    say "  ✓ the tuning method (3.x), and its tools load"
  else
    say "  ✓ the tuning method (3.x)"
  fi
  if [ "$_numpy" = 0 ]; then
    warn "numpy is NOT importable by $_py_seen: crossover selection,"
    warn "the EQ gate, the DSP maths and plot rendering will fail when the method reaches them."
    missing numpy
  fi
  if [ "$_scipy" = 0 ]; then
    warn "scipy is NOT importable by $_py_seen: crossover design, the EQ gate"
    warn "and the EQ proposals will fail when the method reaches them."
    missing scipy
  fi
  if ! { usable python3 && python3 -c "import matplotlib" 2>/dev/null; }; then
    warn "matplotlib is NOT importable by $_py_seen: the method's plots will not be drawn; the rest runs."
  fi
elif [ -f "$SKILL_HOME/rew_tool/rew_api.py" ]; then
  warn "the skill at $SKILL_HOME is the 2.x line — TCC cannot drive it"
  missing "the method (2.x line)"
elif [ "$DRY_RUN" = 0 ]; then
  warn "no tuning method at $SKILL_HOME"
  missing "the method"
fi
if [ "$CHANNEL" = "beta" ] && [ "$DRY_RUN" = 0 ]; then
  if [ ! -f "$SKILL_BETA_SRC/skills/autosound-tuning/rew_tool/contract.py" ]; then
    warn "no beta channel copy at $(pretty "$SKILL_BETA_SRC") — an app asking for beta has nothing to run"
    missing "the beta copy"
  elif ! is_missing "the beta copy"; then   # not on this run's candidate: the beta block said so, and counted it
    say "  ✓ the beta channel's copy, $(git -C "$SKILL_BETA_SRC" describe --tags --always 2>/dev/null || echo '?') — for the app; the terminal stays on $(git -C "$SKILL_SRC" describe --tags --always 2>/dev/null || echo '?')"
  fi
fi
if [ "$MODE" = "tcc" ] && [ "$DRY_RUN" = 0 ]; then
  if [ -n "$TCC_REFUSED" ]; then
    # Before the ✓ lines: an app from an earlier run would read as this run's.
    _kept=""; { [ -d "$APP" ] || find_bin autosound-tcc >/dev/null; } && _kept=" -- the one already here is left as it was"
    warn "Autosound TCC was not installed: $TCC_REFUSED$_kept"
    missing TCC
  elif on_mac && [ -d "$APP" ]; then
    _where="in ~/Applications"; [ -L "$DESKTOP_LINK" ] && _where="$_where, and on your Desktop"
    say "  ✓ Autosound TCC — \"Autosound TCC.app\" $_where"
  elif [ -n "$TCC_BIN" ] || find_bin autosound-tcc >/dev/null; then
    say "  ✓ Autosound TCC — the command:  autosound-tcc"
  else
    warn "Autosound TCC is not installed"
    missing TCC
  fi
fi
CLAUDE_BIN="$(find_bin claude || true)"
if [ -n "$CLAUDE_BIN" ]; then
  say "  ✓ Claude Code"
elif [ "$DRY_RUN" = 0 ]; then
  warn "Claude Code is not installed; nothing can run a session without it"
  missing "Claude Code"
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
    if [ -n "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}" ]; then
      # hub #187: a key in the shell profile is not the reviewer's sign-in, and it sends every
      # review to the API, where agy's model names (…-high) do not exist.
      say "  $n. A Gemini API key is exported in your shell. agy does not use it; it signs in with your"
      say "     Google account (below). A session TCC starts does not see a shell key, and every program"
      say "     can read it there. To keep it for the reviewer, move it into the macOS Keychain (asks first):"
      say "       python3 $(pretty "$SKILL_HOME")/scripts/autosound_ai.py key move-shell"
    fi
    _adc_done=0
    if [ -s "$(adc_file)" ]; then
      # hub #234: a machine with Google Cloud's credentials can give the reviewer those instead of a Google
      # account sign-in -- offered, never assumed: ADC may bill a Cloud project the person keeps for other work.
      say "  $n. Gemini reviewer through Google Cloud's ADC: this machine has its credentials ($(pretty "$(adc_file)"))."
      say "     agy uses them once AGY_ADC_AUTH=true is in $(pretty "$(critic_env_path)") -- the file every run reads, the app's too."
      if offer "Enter = write that line · s = no, the Google account sign-in below:"; then
        if critic_env_set_adc; then _adc_done=1; say "     ✓ written -- the reviewer signs in through ADC"
        else warn "could not write $(pretty "$(critic_env_path)") -- the Google account sign-in below still works"; fi
      else
        say "     (later: add the line AGY_ADC_AUTH=true to that file)"
      fi
    fi
    if [ "$_adc_done" = 0 ]; then
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
    say "     Or Google Cloud's free trial through ADC, no Google AI subscription: the FAQ, «agy through Google Cloud's ADC»."
    fi   # not ADC
    n=$((n + 1))
  fi
  # 3. GitHub — optional.
  if [ -n "$GH_BIN" ]; then
    # The Arbiter, 2026-09-23 (hub #199): GitHub wanted means GitHub set up -- signed in AND git pushing through it.
    # `gh auth setup-git` makes git use gh's sign-in for github.com; each project's first commit and the private
    # backup's `gh repo create` are the method's, per project, on the user's yes (`rew_tool/project_repo.py`).
    if "$GH_BIN" auth status >/dev/null 2>&1; then
      "$GH_BIN" auth setup-git >/dev/null 2>&1 || true
      say "  $n. GitHub: ✓ signed in, and git pushes through it"
    else
      say "  $n. GitHub — optional. Your browser opens with a one-time code; sign in and paste it."
      if [ "$INTERACTIVE" = 1 ] && offer "Enter = sign in now · s = later:"; then
        "$GH_BIN" auth login --hostname github.com --git-protocol https --web < /dev/tty || true
        "$GH_BIN" auth status >/dev/null 2>&1 && "$GH_BIN" auth setup-git >/dev/null 2>&1 || true
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
  # skill #71: agy refuses Pro in some regions; the run must not end naming a model the person cannot get.
  say "     (If agy says Pro is not supported where you are, pick a Gemini Flash (High) line instead.)"
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
  say "        python3 $(pretty "$SKILL_HOME")/scripts/autosound_ai.py doctor"
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

# Where this came from and where to say something about it. Somebody who has just installed two programs from a URL
# they were told to trust should not have to search for the projects they now have on their disk (user, after a clean
# install, 2026-08-13).
step "Where this lives"
say "  the tuning method   $SKILL_REPO_URL"
say "  the desktop app     $TCC_REPO"
say "  something wrong, or an idea — open an issue in whichever of the two it belongs to."

# Last on screen, the verdict and what each missing part needs -- the app's refusal among them, which does not stop
# the run (skill #101) -- rather than left in a block that has scrolled away; then the receipt, the plugin's note and
# the exit code (#142).
finish
