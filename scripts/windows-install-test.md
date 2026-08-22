# Windows install test — what to run, and what a pass looks like

`install.ps1` and `install.cmd` are written as mirrors of `install.sh` and are **not executed by
whoever writes them** — there is no PowerShell on that machine. Every Windows change therefore ships
untested until somebody runs this. Written for v3.0.16, whose two installer changes (SCR-054, the
app installed by tag; SCR-056, the app making its own shortcuts) are the first that have never been
run on Windows at all.

Run it in a Windows VM with a network. Nothing needs installing first — the script installs its own
prerequisites. **Report the whole console output**, not a summary: the interesting failures here are
lines that did *not* appear.

---

## 1. Dry run — changes nothing

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1))) -DryRun -Yes
```

| look for | pass | fail means |
|---|---|---|
| `version v3.0.16` (or newer) | the method's tag resolved | the tag glob or `ls-remote` is broken |
| `version v0.1.13` (or newer) | **the app's tag resolved — this is SCR-054** | fell through to the default branch |
| `could not read the app's releases` | **must NOT appear** | SCR-054's resolution failed; the run continues from the default branch, which is the old behaviour |
| `would create "Autosound TCC" shortcuts…` | the shortcut step is reached | mode detection or `$TccExe` logic is wrong |

## 1a. The UPGRADE case — better than a fresh install, if you have a machine with an old build

A VM that already carries an older method and app exercises more than a clean install does: the
fetch-by-name update path, the app moving from an untagged build to a tagged one, and — the ordering
that matters most — the app being **upgraded before** its `--install-desktop` is called. A machine
sitting on TCC 0.1.11 has no `--install-desktop` at all; the run only works because the app is
replaced first. That sequence has never been executed.

Record the starting state (`autosound-tcc --version` prints it), run the same command as §2, then:

| check | pass |
|---|---|
| the method's version afterwards | ≥ 3.0.16, from `~/.claude/skills/.autosound-tuning-src/.claude-plugin/plugin.json` |
| the app's version afterwards | ≥ 0.1.13 |
| shortcuts | created — **even though the app that was installed when the run started could not create them** |
| the old checkout | updated in place, not duplicated beside itself |

Reference starting state from a real VM (2026-08-22): method `3.0.11`, TCC `0.1.11` (`eeac97cc`),
Windows 11, uv 0.12.5, python 3.12.14 — that machine had `agy`/`gemini`/`codex` absent, which is
fine: the reviewer step is optional and must not stop the run.

## 2. Real install

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1)))
```

Or download and double-click `install.cmd` — the same run, for somebody who does not open PowerShell.
Worth doing **at least once**, because `install.cmd` hardcodes the URL it fetches `install.ps1` from
and nothing else exercises that line.

This is the SCR-056 test:

1. `OK   "Autosound TCC" on your Desktop and in the Start Menu` — and no warning after it.
2. **Both shortcuts exist** — Desktop and Start Menu.
3. **The icon is TCC's, not the generic one.** If it is generic there must be a line saying
   `(with the generic icon — TCC's own was not found in the installed package)`. An icon with that
   line, or a generic icon without it, are both defects — the second is the more interesting one,
   because it means the phrase match broke (see *the string coupling* below).
4. Double-clicking a shortcut **starts the app**, with no console window behind it.
5. Shortcut → Properties → Target points at `autosound-tcc-gui.exe` under the installed bin
   directory, **not** at a temp path. This is what makes `uv tool upgrade` move the shortcut too.

## 3. An older app ref — the deliberate gap

```powershell
& ([scriptblock]::Create((irm …install.ps1))) -TccRef v0.1.12
```

Expected: the app installs, and **no shortcuts are created**, because `--install-desktop` does not
exist before v0.1.13. It must **say so** — a warning, not silence and not a crash. There is no
fallback by decision, not by oversight (v3.0.16's Upgrading note).

## 4. Uninstall

```powershell
& ([scriptblock]::Create((irm …install.ps1))) -Uninstall
```

Both shortcuts go; a shortcut somebody else made under the same name stays.

---

## Known-suspicious spots, and one that turned out to be fine

- **`$LASTEXITCODE` after `& $TccExe --install-desktop 2>&1 | Out-String`** — flagged as the likeliest
  break and it is **not one**: `Out-String` is a cmdlet and does not touch `$LASTEXITCODE`, so a
  native exe's code survives the pipeline. The actual PowerShell trap is `$?`, which after a pipeline
  reports on the *cmdlet*, not the exe — and this script does not use `$?` here. (Established by TCC,
  2026-08-22.) Left written down because the wrong worry costs a tester an hour.
- **`2>&1` from a native command under `$ErrorActionPreference = "Stop"`** becomes a terminating
  error in PowerShell 5.1. Already handled at the top of `install.ps1`; the comment there says so.
- **The string coupling.** Both installers detect a missing icon by matching the phrase `no icon` in
  the app's output. Today it matches on both platforms. It is the same class of coupling SCR-056
  removed at the module level, reduced to a string: reword it on the app's side and the warning
  silently stops appearing, with no error anywhere. Both sides carry a comment saying those two words
  are load-bearing. The durable fix is a machine-readable signal from the app; until then this is an
  agreement, not a mechanism.
