#!/usr/bin/env bash
# The plugin's start-of-session note (W-6 #120). A plugin install copies the method's files and nothing it runs on,
# and Claude Code runs no script at install time; this runs at the start of a session instead, reads one file, and
# prints a note into the session's context ONLY while this plugin version is not set up on the machine -- the
# installer in plugin mode (`/autosound-tuning:setup`) checks the copy against its signed release, installs the tools,
# and writes the version into `~/.config/autosound/plugin-ready` (`upkeep.py plugin-ready`). Silent otherwise, and
# silent for a checkout (a `.git` beside it identifies itself: `deployment.py`).
#
# No Python, no network, no probing of tools: a session start must not open macOS's Command Line Tools dialog or wait
# on a download. What is missing is the installer's business, said by the installer.
root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)}"
[ -d "$root/.git" ] && exit 0
version="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$root/.claude-plugin/plugin.json" 2>/dev/null | head -1)"
[ -n "$version" ] || exit 0
grep -qxF "v$version" "${HOME}/.config/autosound/plugin-ready" 2>/dev/null && exit 0
cat <<NOTE
autosound-tuning plugin v$version is not set up on this machine yet: this copy has not been checked against its signed
release, and the tools the method runs on (Python libraries, the reviewer, the desk engine) come with its installer,
not with the plugin. When the person asks for anything the method runs -- a measurement, a tune, the reviewer -- say
so first and offer /autosound-tuning:setup; run the method's scripts after it, or only if they decline knowing this.
NOTE
exit 0
