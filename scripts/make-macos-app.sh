#!/usr/bin/env bash
# Build "Autosound TCC.app" — a macOS bundle around the already-installed `autosound-tcc`.
#
# **This is not a distributable installer and it needs no Apple Developer account.** A `.app` is a
# folder with a fixed layout; building one for yourself is free. The $99/year buys code signing
# and notarisation, which exist so that OTHER people do not see a Gatekeeper warning — not so that
# the app runs on the machine that built it.
#
# What the bundle buys, all of it small and none of it magic:
#
#   * launch from Spotlight or the Dock, with no terminal window left occupied
#   * its own icon and its own name in the menu bar, instead of "Python"
#   * a Dock entry that survives the app being the only thing on screen
#
# What it does NOT buy: a copy of the app. The bundle EXECS whatever `autosound-tcc` is on the
# system at launch time, so `uv tool upgrade` updates the app too. A bundle with its own frozen
# copy inside would be a second install to keep in step, which is the kind of duplication this
# project keeps paying for elsewhere.
set -euo pipefail

APP_DIR="${1:-$HOME/Applications}/Autosound TCC.app"
# `$2` is the binary, when the caller already knows where it landed. `uv` honours
# UV_TOOL_BIN_DIR, so "on PATH or in ~/.local/bin" is a guess that is wrong exactly when somebody
# has configured something (2026-08-12).
BIN="${2:-$(command -v autosound-tcc || echo "$HOME/.local/bin/autosound-tcc")}"

if [ ! -x "$BIN" ]; then
  echo "autosound-tcc is not installed (looked for it on PATH and in ~/.local/bin)." >&2
  echo "Install it first:  uv tool install 'autosound-tcc[gui,claude] @ git+https://github.com/ayukhno/autosound-tcc'" >&2
  exit 1
fi

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

# The icon belongs to TCC and ships inside its package, so this repository keeps no second copy to
# fall out of step. Finding it: the console script names the interpreter `uv` built the tool
# with, and that interpreter can say where the package landed. Guessing the uv layout with a glob
# would break the first time uv changes it.
#
# Two shapes of console script. When the interpreter's path is short and plain, uv writes it as
# the shebang. When it is long or has awkward characters — a long username, a folder with a space
# — uv writes a `#!/bin/sh` trampoline whose SECOND line is `'''exec' '<python>' "$0" "$@"`.
# Reading only the shebang made the icon depend on the length of the home path (found in a
# sandbox with a long one, 2026-08-17: Resources/ empty, "no icon found").
ICON_NAME=""
_py="$(sed -n '1s/^#!//p' "$BIN" 2>/dev/null | awk '{print $1}')"
case "$_py" in
  *python*) ;;
  *) _py="$(sed -n "2s/^'''exec' '\([^']*\)'.*/\1/p" "$BIN" 2>/dev/null)" ;;
esac
# Last resort: ask uv itself where its tools live.
if [ ! -x "$_py" ] && command -v uv >/dev/null 2>&1; then
  _py="$(uv tool dir 2>/dev/null)/autosound-tcc/bin/python"
fi
if [ -x "$_py" ]; then
  _icns="$("$_py" -c 'import autosound_tcc.app as a; print(a.APP_ICNS if a.APP_ICNS.is_file() else "")' 2>/dev/null || true)"
  if [ -n "$_icns" ] && [ -f "$_icns" ]; then
    cp "$_icns" "$APP_DIR/Contents/Resources/AutosoundTCC.icns"
    ICON_NAME="AutosoundTCC"
  fi
fi
[ -n "$ICON_NAME" ] || echo "note: no icon found in the installed package — the bundle gets the generic one." >&2

cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>            <string>Autosound TCC</string>
  <key>CFBundleDisplayName</key>     <string>Autosound TCC</string>
  <key>CFBundleIdentifier</key>      <string>dev.autosound.tcc</string>
  <key>CFBundleVersion</key>         <string>1</string>
  <key>CFBundleShortVersionString</key> <string>1.0</string>
  <key>CFBundlePackageType</key>     <string>APPL</string>
  <key>CFBundleExecutable</key>      <string>autosound-tcc</string>${ICON_NAME:+
  <key>CFBundleIconFile</key>        <string>$ICON_NAME</string>}
  <key>NSHighResolutionCapable</key> <true/>
  <!-- A regular foreground app: it owns a menu bar and a Dock tile. Without this a bundle around
       a script can end up as an accessory, which is how a window ends up with no way back to it
       once something else takes focus. -->
  <key>LSUIElement</key>             <false/>
  <key>NSRequiresAquaSystemAppearance</key> <false/>
</dict>
</plist>
PLIST

cat > "$APP_DIR/Contents/MacOS/autosound-tcc" <<LAUNCHER
#!/bin/bash
# Launch the INSTALLED binary rather than a copy: \`uv tool upgrade\` then updates this app too.
# Finder gives a bundle almost no PATH, so the usual install locations are named explicitly.
export PATH="\$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
BIN="\$(command -v autosound-tcc || echo "\$HOME/.local/bin/autosound-tcc")"
if [ ! -x "\$BIN" ]; then
  /usr/bin/osascript -e 'display alert "Autosound TCC is not installed" message "Run the installer again, or: uv tool install '"'"'autosound-tcc[gui,claude] @ git+https://github.com/ayukhno/autosound-tcc'"'"'"'
  exit 1
fi
# No --project-dir: TCC asks which project to open, and remembers the answer. A bundle cannot know
# which car you meant.
exec "\$BIN" "\$@"
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/autosound-tcc"

# Touch the bundle so Finder notices it changed — otherwise a rebuilt app keeps the old icon and
# the old name until the icon cache happens to refresh.
touch "$APP_DIR"

echo "Built: $APP_DIR"
echo "It runs: $BIN"
echo "Unsigned, which is fine for the machine that built it. Copying it to another Mac will show"
echo "a Gatekeeper warning there — right-click → Open once, or sign it, which is what the Apple"
echo "Developer account is actually for."
