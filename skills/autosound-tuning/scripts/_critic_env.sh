#!/usr/bin/env bash
# _critic_env.sh — how every reviewer wrapper reads its configuration and its key.
#
# ONE loader, sourced by _gemini_common.sh, _claude_common.sh and _codex_common.sh. It used to be
# one careful loader (Gemini) and two careless copies: the Claude and Codex wrappers RAN the file
# through `. "$_env"` with `set -a`, so a `.critic-env` from a project someone else wrote executed
# arbitrary shell the moment the reviewer started — the exact thing HUB-025 removed from the third
# wrapper — and neither of them looked at the per-machine key file at all, so a key stored the way
# the docs ask for it was invisible and the channel reported itself unreachable. Found in the
# 2026-09-09 release review; the fix is that there is now only one of these to get right.

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
# A project-local file that carries a KEY and that git would take -- tracked, or not ignored --
# is refused, not read. The user's rule (2026-09-08): a file that can carry a key MUST be ignored
# so it never reaches GitHub; a wrapper that reads it anyway is the wrapper that lets it ride.
# Only the project-local files: the machine file is outside every repository by construction.
_critic_guard() {                                  # $1 = file inside the project
  local dir rel
  grep -qE '^\s*(export\s+)?[A-Z_]*API_KEY\s*=' "$1" || return 0        # no key in it: fine
  command -v git >/dev/null 2>&1 || return 0
  dir="$(cd "$(dirname "$1")" && pwd)"
  git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0   # not a repository
  rel="$(basename "$1")"
  if git -C "$dir" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1; then
    echo "critic-env: $1 carries a key AND is TRACKED by git -- refusing to run." >&2
    echo "  fix: git rm --cached '$1'; add '$(basename "$1")' to .gitignore; move the key to ~/.config/autosound/critic-env; ROTATE the key (it is in the history)." >&2
    return 1
  fi
  if ! git -C "$dir" check-ignore -q -- "$rel"; then
    echo "critic-env: $1 carries a key and git would ADD it (not in .gitignore) -- refusing to run." >&2
    echo "  fix: add '$(basename "$1")' to the repository's .gitignore -- or move the key to ~/.config/autosound/critic-env (setup-critic-channel.md §3)." >&2
    return 1
  fi
  return 0
}
for _env in "$_critic_machine" "${APPDATA:+$APPDATA/autosound/critic-env}" \
            "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do
  [[ -n "$_env" && -f "$_env" ]] || continue
  case "$_env" in
    "$PWD"/*) _critic_guard "$_env" || { [[ "${BASH_SOURCE[0]}" != "$0" ]] && return 1 2>/dev/null || exit 1; } ;;
  esac
  _critic_load "$_env"
done
