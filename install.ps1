# Autosound tuning -- installer for Windows.
#
# The mirror of install.sh, in the same two blocks: everything a person does happens at the start
# (one screen that names every download, one optional question, one "Go ahead?", and -- only when
# Git for Windows is missing -- one Windows permission dialog) or at the end (the sign-ins, in
# order, each explained before it runs). Nothing in between needs anybody at the keyboard.
#
# What it installs, into your user profile unless said otherwise:
#
#   * Git for Windows           git for the method, Git Bash for Claude Code's Bash tool. The
#                               one part that installs machine-wide and shows a permission (UAC)
#                               dialog, once. winget, or the official installer if winget is missing.
#   * Claude Code               the AI that runs the method              claude.ai/install.ps1
#   * uv, and a Python 3.12     uv installs Python; that Python is `python3` for the method's tools
#                               (Windows ships no python3, only a Store shortcut that pretends to)
#   * the tuning method         the newest 3.x tag        github.com/ayukhno/autosound-tuning-skill
#   * numpy, scipy, matplotlib  the method's own tools need them, into the user site
#   * Autosound TCC             the desktop app, plus Desktop and Start Menu shortcuts
#   * agy                       Google's Antigravity CLI -- Gemini as the second AI, the reviewer
#   * gh                        GitHub's CLI, only if asked -- backs up a project's record
#
# What it will not do: press the sign-in buttons (the sessions are yours; per the Agent SDK's
# terms a product may not offer a claude.ai login of its own), touch a project folder, or replace
# a skill directory it did not create.
#
# Run on Windows 11 (25H2, a Parallels VM) on 2026-08-17: a fresh unattended install and
# -Uninstall -All, twice over, then the interactive form with all three sign-ins (Claude in the
# browser, agy's TUI, gh's device code) -- transcripts read line by line. Not yet exercised there:
# REW detection on a machine that has REW. Windows PowerShell 5.1 (what every Windows ships) or PowerShell 7 -- no syntax newer than
# 5.1 is used here on purpose. Run it through install.cmd (double-click), or:
#
#   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
#   & ([scriptblock]::Create((irm <same url>))) -Terminal      # with options
#
# Usage:
#   .\install.ps1                     everything above; asks once, then runs on its own
#   .\install.ps1 -Terminal           the method only, no desktop app (~700 MB less)
#   .\install.ps1 -NoReviewer         without the Gemini reviewer
#   .\install.ps1 -GitHub             with the GitHub CLI, for the project backup (default: without)
#   .\install.ps1 -WithOmp            with omp, which offers TCC every non-Claude model (default: without)
#   .\install.ps1 -NoEngine           without Phase 1's desk engine (default: fetched only when this
#   .\install.ps1 -Engine             machine has no .NET SDK to build it from; -Engine fetches anyway)
#   .\install.ps1 -DryRun             say what it would do, change nothing
#   .\install.ps1 -Plugin             run from inside a plugin copy (/plugin install): the method IS that copy,
#                                     checked against its signed release, not cloned (W-6 #120)
#   .\install.ps1 -Yes                yes to every question; sign-ins are printed, not run
#   .\install.ps1 -SkillRef v3.1.0    a specific skill version (default: the newest 3.x tag)
#   .\install.ps1 -Channel beta       also release candidates: for the app, and in a SECOND copy of the
#                                     method that only an app asking for beta runs -- the terminal's
#                                     copy stays on releases (default: stable, releases only;
#                                     -SkillRef sets the terminal's copy, -TccRef the app)
#   .\install.ps1 -TccRef v1.1.0      the app version released WITH that one -- quote the two
#                                     together or not at all; a mixed pair is untested
#   .\install.ps1 -Uninstall          remove what this script installed -- NEVER your projects
#   .\install.ps1 -Uninstall -All     also uv, Claude Code and ~\.claude, agy/gh/omp when this
#                                     script installed them, and every --user pip package. Asks first.

[CmdletBinding()]
param(
    [switch]$Terminal,
    [switch]$Tcc,
    [switch]$NoReviewer,
    [switch]$WithOmp,   # the way to ask for omp -- it comes only when asked (2026-09-17)
    [switch]$NoOmp,     # the default since 2026-09-17; still accepted
    [switch]$GitHub,
    [switch]$NoGitHub,
    [switch]$Engine,    # fetch the prebuilt desk engine even where the .NET SDK could build one
    [switch]$NoEngine,  # never fetch it
    [switch]$DryRun,
    [switch]$Plugin,    # W-6 #120: the method is the plugin copy this script sits in
    [switch]$Yes,
    [string]$SkillRef = "",
    [string]$TccRef = "",
    [string]$Channel = "stable",
    [switch]$Uninstall,
    [switch]$All,
    [switch]$Help,
    [string]$Log = ""
)
# -Log <file>: a full transcript, for reading a run that happened on somebody else's machine. A
# `| Tee-Object` on the outside sees none of this script's own lines (they go to the host, not
# the pipeline), which is how the first Windows log arrived holding two errors and nothing else.
$AutosoundTranscriptOn = $false
if ($Log) { try { Start-Transcript -Path $Log -Force | Out-Null; $AutosoundTranscriptOn = $true } catch { Write-Host "  (no transcript: $($_.Exception.Message))" } }

# How the installer stops early. Run as a FILE -- install.cmd uses -File -- `exit` is right: it ends
# that powershell.exe and hands install.cmd the code. Run as the README one-liner (`irm ... | iex`,
# or a scriptblock) there is no file, and `exit` ends the user's OWN PowerShell: the window closed
# over the very line that said why it stopped (2026-09-13). So there Stop-Installer only records the
# code, and the call site's `return` ends the script -- every call site is at the script's top
# level, where `return` does exactly that. The code is left in $global:AutosoundInstallExit, which
# install.cmd's download path reads, and in $LASTEXITCODE. scripts/installer-consistency.py fails on
# a bare `exit` anywhere else, and on a Stop-Installer call without its `; return`.
$AutosoundRunAsFile = [bool]$PSCommandPath
if (-not $AutosoundRunAsFile) { $global:AutosoundInstallExit = 0 }
# The codes (#142), install.sh's: 0 ready -- 1 stopped before the end, a refusal, an error or an interruption: what was
# done before it stays (Git, Claude Code, uv, Python, perhaps the method), and a stop before the method's step leaves
# the method as it was -- 2 a usage error -- 3 installed, NOT ready, the missing parts named.
# A stop (1) writes the receipt as `stopped`; the end writes its own before its 3; 0 and 2 here write none.
function Stop-Installer {
    param([int]$Code)
    if ($Code -eq 1) { Write-Receipt "stopped" }
    if ($AutosoundTranscriptOn) { try { Stop-Transcript | Out-Null } catch { $null = $_ } }
    if ($AutosoundRunAsFile) { exit $Code }
    $global:AutosoundInstallExit = $Code
    $global:LASTEXITCODE = $Code
}
# The installer's RECEIPT (S-049, #142) -- install.sh's write_receipt, the same fields in the same order: which
# install.ps1 ran (its version; its sha256 when it ran as a file), for which method tag, what it did about the engine,
# the python3 the method runs on, and how the run ended -- ready, not ready (`missing` names the parts) or stopped.
# `doctor` reads it back. Never in a dry run; a receipt that cannot be written stops nothing.
function Write-Receipt {
    param([string]$Status)
    if ($DryRun) { return }
    $file = "install-receipt.json"
    try {
        $rd = Join-Path $env:LOCALAPPDATA "autosound"
        $file = Join-Path $rd "install-receipt.json"
        New-Item -ItemType Directory -Force -Path $rd -ErrorAction Stop | Out-Null
        $sha = ""
        # .NET's SHA256, not Get-FileHash (R50, #142): Get-FileHash comes from a script module, which a Windows PowerShell
        # started under PowerShell 7's PSModulePath cannot load -- and its error cost the whole receipt. Its own guard: a
        # hash that fails costs the hash, not the receipt.
        if ($PSCommandPath) {
            try {
                $hasher = [System.Security.Cryptography.SHA256]::Create()
                try { $sha = -join ($hasher.ComputeHash([System.IO.File]::ReadAllBytes($PSCommandPath)) | ForEach-Object { $_.ToString("x2") }) }
                finally { $hasher.Dispose() }
            } catch { $sha = "" }
        }
        $py = Join-Path $LocalBin "python3.exe"
        $python = "no python3"
        if (Test-Path $py) {
            $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
            $ver = "$(& $py -c "import platform; print(platform.python_version())" 2>$null)".Trim()
            $ErrorActionPreference = $prev
            $python = if ($ver) { "$py $ver" } else { "$py does not run" }
        }
        $engine = if ($EngineDid) { $EngineDid } else { "not reached" }
        # What the method's step left as it was, when it did (#142) -- not a tag this run never installed.
        $ref = if ($MethodLeft) { $MethodLeft } else { "$SkillRef" }
        $receipt = [ordered]@{ installer = "install.ps1"; installer_sha256 = $sha; method_ref = $ref;
                               mode = "$Mode"; at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ");
                               platform = "Windows-$env:PROCESSOR_ARCHITECTURE"; engine = $engine;
                               installer_version = $InstallerVersion; status = $Status;
                               missing = [string[]]@($script:Missing); python = $python }
        $receipt | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -ErrorAction Stop $file
    } catch {
        # Said once, the file and why (#142): kept quiet, `doctor` read an earlier run's receipt as this one's. -ErrorAction
        # Stop above: Set-Content's error is not a terminating one, and passed this catch by. It stops nothing.
        Warn "the receipt was not written ($(Pretty $file)): $($_.Exception.Message)"
    }
}
# What the run leaves not ready, by short names (#142) -- install.sh's MISSING. Each check that finds a part not ready
# says why and adds it with Add-Missing, which names a part once; the end reads this list and nothing else. $script:
# wherever it is read or written, as $script:SignatureRefused is.
$script:Missing = @()
# What the method's step left as it was, when it did (#142): a link that is not this script's, or anything else at the
# link's place. The receipt's method_ref says that -- install.sh's METHOD_LEFT.
$MethodLeft = ""
function Add-Missing {
    param([string]$Name)
    if ($script:Missing -notcontains $Name) { $script:Missing += $Name }
}

# Native commands (git, winget, uv, claude...) write ordinary progress to stderr, and under
# `$ErrorActionPreference = "Stop"` Windows PowerShell 5.1 turns that into a terminating error the
# moment it is redirected. So: Continue, and every step checks its own result instead.
#
# "Every step checks its own result" was a PROMISE until 2026-09-07; this is the audit that made
# it a statement (HUB-042). Every external call in this file, and what checks it:
#
#   winget install Git.Git        `Have git` right after, then `exit 1` -- the strongest of the lot
#   Invoke-WebRequest (Git .exe)  try/catch -> Warn, then the same `Have git` gate
#   uv installer (irm | iex)      Invoke-Upstream returns the CHILD's exit code; `Have uv` after
#   uv python install 3.12        `Test-Path $Py3` after; Warn naming what will not run
#   uv tool install autosound-tcc return value read into `if` -- the one that always was
#   git fetch / git checkout      both return values read, then HEAD vs the tag's commit compared
#   git init + fetch (new copy)   each return value read; HEAD vs the tag's commit after the checkout
#   pip install -r requirements   `python3 -c "import numpy, scipy"` after -- the produce, not the code
#   claude / agy / gh installers  `Have <tool>` after each; absence is a Warn, not a stop
#   Remove-Item (the --uninstall  DELIBERATELY unchecked. The goal is "gone"; a file that was not
#   branch, 12 of the 19 `Run`     there is the goal already, and every one carries
#   calls in this file)           -ErrorAction SilentlyContinue for exactly that reason.
#
# The rule this leaves behind: a new external call either reads its result, or carries a line
# saying why its failure is safe. `Run` returns a boolean -- piping it to Out-Null is the way to
# say "I do not care", and it should be visible when that is what you mean.
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
# Windows PowerShell 5.1 still defaults to TLS 1.0/1.1 for web requests, which GitHub and most of
# the download hosts below refuse. One line, once, before the first `irm`.
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { $null = $_ }  # PowerShell 7 has no such default

$SkillRepo    = "https://github.com/ayukhno/autosound-tuning-skill.git"
$SkillRepoUrl = $SkillRepo -replace '\.git$', ''
# Which tags this installer considers installable — the supported line, stated once so a consumer
# can READ the policy instead of re-deriving it from the pipeline below. Same rule as install.sh's
# SKILL_TAG_GLOB and TCC's updater; when the supported line moves, this is the line that moves.
$SkillTagGlob = "v3.*"
# The beta channel's candidates for the same line (hub RELEASE-CHANNEL.md s11): "beta-" + the line's
# glob. The different first letter keeps a candidate out of $SkillTagGlob, so the stable channel --
# the default, and TCC's updater -- never sees one. Same value as SKILL_BETA_GLOB in install.sh.
$SkillBetaGlob = "beta-v3.*"
# Release tags are signed by the method's author (skill #99, hub #82 HUB-031) -- see install.sh for why the key is
# here and not read from the tag. Same values as install.sh and scripts/upkeep.py (installer-consistency.py).
$SkillSigningPrincipal = "ayukhno"
$SkillSigningKey       = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHLm4x1yz9JbFfBlxdQA8vR8yYMupVktswes3CL7QE1y"
$SkillSignedFrom       = "v3.0.64"
# The app's tags are signed with the same key, from its own first signed tag (TCC's core/signed_tags.py, skill #101),
# and checked the same way before uv installs one. Same value as TCC_SIGNED_FROM in install.sh.
$TccSignedFrom         = "v0.1.45"
# Where a local change to the installed clone is kept before the update resets it (skill #91). Same as install.sh.
$LocalChanges = Join-Path $HOME ".claude\skills\autosound-local-changes"
# The app's supported line -- `v*`, not `v3.*`: the app versions independently of the method.
$TccTagGlob   = "v*"
# ...and the app's candidates, the same way.
$TccBetaGlob   = "beta-v*"
#: The uv release this installer pins. Must equal UV_VERSION in install.sh.
$UvVersion    = "0.12.10"
#: This installer's own version, for its receipt (#142): the sha256 there is empty under `irm | iex`. Must equal
#: install.sh's INSTALLER_VERSION and .claude-plugin/plugin.json's version; the release's bookkeeping moves all three.
$InstallerVersion = "3.1.2"
$TccRepo      = "https://github.com/ayukhno/autosound-tcc"
$SkillHome    = Join-Path $HOME ".claude\skills\autosound-tuning"
# The checkout lives beside the skill and the skill points at it (a junction) -- see install.sh
# for why moving the subdirectory out instead leaves something no later run can update.
$SkillSrc     = Join-Path $HOME ".claude\skills\.autosound-tuning-src"
# The beta channel's copy, beside it and with no junction pointing at it -- see install.sh
# (SKILL_BETA_SRC, autosound-hub #145) for why the terminal and a beta app cannot share one checkout.
$SkillBetaSrc = Join-Path $HOME ".claude\skills\.autosound-tuning-beta"
# Where uv, Claude Code, gh and the app's own commands land -- the same folder on every platform.
$LocalBin     = Join-Path $HOME ".local\bin"
# What THIS script put on the machine, one name per line. -Uninstall removes what is listed here
# and nothing else: a tool the person already had is never ours to delete.
$Manifest     = Join-Path $HOME ".local\share\autosound\installer-manifest"
# `GetFolderPath` follows a redirected Desktop (OneDrive) where a literal ~\Desktop would not.
$DesktopDir   = [Environment]::GetFolderPath("Desktop")
if (-not $DesktopDir) { $DesktopDir = Join-Path $HOME "Desktop" }
$ProgramsDir  = [Environment]::GetFolderPath("Programs")
if (-not $ProgramsDir) { $ProgramsDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs" }
$DesktopLnk   = Join-Path $DesktopDir "Autosound TCC.lnk"
$ProgramsLnk  = Join-Path $ProgramsDir "Autosound TCC.lnk"
$RewLnk       = Join-Path $DesktopDir "REW (API on).lnk"
# Downloads go under the profile, not under %TEMP%: on the first Windows test machine %TEMP% was
# an 8.3 short path (C:\Users\OB8CD~1.YUK\...) that PowerShell then refused to resolve, so the gh
# download failed at the very first step. The profile path itself was fine.
$Scratch      = Join-Path $HOME ".cache\autosound-installer"

if ($Help) {
@"
Autosound tuning -- installer for Windows

  install.ps1                     everything: Git for Windows, Claude Code, uv + Python, the
                                  method, the TCC app, the Gemini reviewer; asks once, then runs
  install.ps1 -Terminal           the method only, no desktop app (~700 MB less)
  install.ps1 -NoReviewer         without the Gemini reviewer
  install.ps1 -GitHub             with the GitHub CLI, for the project backup (default: without)
  install.ps1 -WithOmp            with omp, which offers TCC every non-Claude model (metered; default: without)
  install.ps1 -NoEngine           without Phase 1's desk engine; -Engine fetches it even where the
                                  .NET SDK could build it (default: fetched only when there is no SDK)
  install.ps1 -DryRun             say what it would do, change nothing
  install.ps1 -Plugin             from inside a plugin copy (/plugin install): the method is that copy,
                                  checked against its signed release, not cloned
  install.ps1 -Yes                yes to every question; sign-ins are printed, not run
  install.ps1 -SkillRef v3.1.0    a specific skill version (default: the newest 3.x tag)
  install.ps1 -Channel beta       also release candidates: for the app, and in a SECOND copy of
                                  the method that only an app asking for beta runs -- the
                                  terminal's copy stays on releases (default: stable)
  install.ps1 -TccRef v1.1.0      the app version released WITH that one -- quote the two
                                  together or not at all; a mixed pair is untested
  install.ps1 -Uninstall          remove what this script installed -- NEVER your projects
  install.ps1 -Uninstall -All     also uv, Claude Code and ~\.claude, agy/gh/omp when this
                                  script installed them, and every --user pip package. Asks first.

Through the one-liner, options go on the scriptblock:
  & ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1))) -Terminal
"@ | Write-Host
    Stop-Installer 0; return
}

if ($Channel -notin @("stable", "beta")) {
    Write-Host "unknown channel: '$Channel' (stable or beta)"
    Stop-Installer 2; return
}
# -Plugin (W-6 #120): the method is the plugin copy this script sits in -- `/plugin install` put the files there, and
# a copy of files brings none of what the method runs on. This run brings that, and checks the copy against its signed
# release instead of cloning one (upkeep.py verify-copy, #121). The same rule as install.sh's --plugin.
$PluginRoot = ""; $PluginVersion = ""
if ($Plugin) {
    $PluginRoot = "$PSScriptRoot"
    $pluginJson = if ($PluginRoot) { Join-Path $PluginRoot ".claude-plugin\plugin.json" } else { "" }
    if ($pluginJson -and (Test-Path $pluginJson)) {
        try { $PluginVersion = [string]((Get-Content $pluginJson -Raw | ConvertFrom-Json).version) } catch { $PluginVersion = "" }
    }
    if (-not $PluginRoot -or -not $PluginVersion -or (Test-Path (Join-Path $PluginRoot ".git"))) {
        Write-Host ("-Plugin runs the installer inside a plugin copy -- the folder /plugin install made, with " +
                    ".claude-plugin\plugin.json and no .git; this is not one: $(if ($PluginRoot) { $PluginRoot } else { '?' })")
        Stop-Installer 2; return
    }
    if ($Uninstall -or $SkillRef -or $Channel -eq "beta") {
        Write-Host ("-Plugin sets up this plugin copy (v$PluginVersion); -Uninstall, -SkillRef and -Channel beta are " +
                    "for the installer's own copy of the method")
        Stop-Installer 2; return
    }
}
$Mode         = if ($Terminal -and -not $Tcc) { "terminal" } else { "tcc" }   # -Tcc is the default, kept for old command lines
$WantReviewer = -not $NoReviewer
# omp only with -WithOmp (the user, 2026-09-17, issue #25) -- the history is in install.sh's note.
$WantOmp      = [bool]$WithOmp -and -not $NoOmp
if ($WantOmp -and $Mode -ne "tcc") {
    Write-Host "  -WithOmp: omp is for the app's model picker, and -Terminal installs no app -- left out."   # Say is defined below
    $WantOmp = $false
}
# gh only with -GitHub, no question on the way (the user, 2026-09-16) -- see the note in install.sh.
$WantGitHub   = if ($GitHub) { "1" } elseif ($NoGitHub) { "0" } else { "auto" }
# Phase 1's desk engine: "auto" fetches the prebuilt binary ONLY where there is no .NET SDK to build
# one from -- the reasoning is in install.sh's note beside WANT_ENGINE, and both installers must make
# the same call or a Mac and a PC end up with different machines.
$WantEngine   = if ($Engine) { "1" } elseif ($NoEngine) { "0" } else { "auto" }
# Where a fetched engine lands on Windows -- `resonalyze_engine.installed_dir()` owns this path
# (%LOCALAPPDATA%); the line here is the uninstaller's.
$EngineHome   = Join-Path $env:LOCALAPPDATA "autosound\engines"

# -- small tools ------------------------------------------------------------------------------
function Say  { param($m) Write-Host "  $m" }
function Step { param($m) Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Warn { param($m) Write-Host "  ! $m" -ForegroundColor Yellow }
function Have { param($n) [bool](Get-Command $n -ErrorAction SilentlyContinue) }
# Is $Name a release tag -- vX.Y.Z, or a candidate's beta-vX.Y.Z-rcN -- and nothing else? The one rule (T-45, #142),
# here as in install.sh's is_release_tag and upkeep.py's is_release_tag; installer-consistency.py holds the three to one
# table of names, reading these two patterns as .NET does. -cmatch: case kept. [0-9], not \d: \d takes any script's
# digits. \z, not $: $ lets a trailing newline through.
function Test-ReleaseTag {
    param([string]$Name)
    return ($Name -cmatch '^v[0-9]+\.[0-9]+\.[0-9]+\z' -or $Name -cmatch '^beta-v[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+\z')
}
# The newest tag on the beta channel (hub RELEASE-CHANNEL.md s11.2). A release sorts as
# (X,Y,Z,1,0) and a candidate as (X,Y,Z,0,N): v3.1.0 above beta-v3.1.0-rc2, rc10 above rc2, and a
# candidate for v3.1.0 above v3.0.49. [version] cannot say this -- it throws on a "beta-" name. A
# name of neither shape is not installable and is dropped: the two shapes are Test-ReleaseTag's, with
# the numbers captured. Same order as newest_on_channel in install.sh, which installer-consistency.py
# RUNS; this half is only read there, not run.
function Select-NewestOnChannel {
    param([string[]]$Names)
    $keyed = @(foreach ($n in $Names) {
        if ($n -cmatch '^v([0-9]+)\.([0-9]+)\.([0-9]+)\z') {
            [pscustomobject]@{ Name = $n; X = [int]$Matches[1]; Y = [int]$Matches[2]; Z = [int]$Matches[3]; R = 1; N = 0 }
        } elseif ($n -cmatch '^beta-v([0-9]+)\.([0-9]+)\.([0-9]+)-rc([0-9]+)\z') {
            [pscustomobject]@{ Name = $n; X = [int]$Matches[1]; Y = [int]$Matches[2]; Z = [int]$Matches[3]; R = 0; N = [int]$Matches[4] }
        }
    })
    if ($keyed.Count -eq 0) { return $null }
    return @($keyed | Sort-Object X, Y, Z, R, N)[-1].Name
}
# Paths on screen with the profile as `~`: a person reads "~\.zshrc" as a place; the same path
# spelled out from C:\Users reads as a warning.
function Pretty { param($p) if ($p -and $p.StartsWith($HOME)) { "~" + $p.Substring($HOME.Length) } else { $p } }
# A native command that could not start -- not there, not a program -- sets no exit code (#142): the code is cleared
# first, and only one that was set, and is 0, is a success; it read the 0 set beforehand, and a python3 that could not
# start "installed" the libraries. Every `Run` whose answer is read runs a native command; the uninstaller's, which run
# cmdlets, send their answer to Out-Null.
function Run {
    param([scriptblock]$Block, [string]$Label)
    if ($DryRun) { Say "would run: $Label"; return $true }
    $global:LASTEXITCODE = $null
    try { & $Block } catch { Warn "$Label did not run: $($_.Exception.Message)"; return $false }
    return ($null -ne $LASTEXITCODE -and $LASTEXITCODE -eq 0)
}
# A probe of a native command whose stderr is part of the answer -- `gh auth status` when nobody
# is signed in, `python3 -c "import numpy"` when it is missing -- must not paint a red
# NativeCommandError block on the screen and in the transcript, which `2>$null` alone did not
# prevent under Windows PowerShell 5.1 (first Windows run, 2026-08-17). Silence everything, keep
# the exit code; the caller says what it means.
function Test-Quiet {
    param([scriptblock]$Block)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    # As in Run (#142): a command that could not start is no answer of 0 -- it set no exit code at all.
    $global:LASTEXITCODE = $null
    try { & $Block 2>&1 | Out-Null } catch { $ErrorActionPreference = $prev; return $false }
    $ErrorActionPreference = $prev
    return ($null -ne $LASTEXITCODE -and $LASTEXITCODE -eq 0)
}
# The upstream one-liners (`irm <url> | iex`) run in a CHILD PowerShell, never in this one: two of
# them end with `exit` on failure and one with `throw`, and inside our process an `exit` in their
# code ends this script mid-way with no check and no message. A child process turns that into an
# exit code we can read. Windows PowerShell 5.1 is always there, and every one of them supports it.
function Invoke-Upstream {
    param([string]$Url, [string]$Label, [switch]$Capture)
    if ($DryRun) { Say "would run: irm $Url | iex   ($Label)"; return $true }
    # Say whose script this is and what is about to run, every time and in one place -- these are
    # the four calls in the whole installer that execute code we did not write, and a person
    # watching the screen should be able to see that happen (HUB-031).
    Say "  the official installer, $($Url -replace '^https://','')"
    $cmd = "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; irm '$Url' -UseBasicParsing | iex"
    $global:LASTEXITCODE = 0
    if ($Capture) {
        $script:UpstreamOutput = @(& powershell -NoProfile -ExecutionPolicy Bypass -Command $cmd 2>&1 | Out-String -Stream)
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -Command $cmd
    }
    return ($LASTEXITCODE -eq 0)
}
$script:UpstreamOutput = @()
# Installers write to the registry PATH (uv, agy, winget for Git); this process's copy of PATH
# does not follow. Re-read it after each of them, so the next step can call what the last one
# installed and the checks describe the machine as a NEW window will see it.
function Sync-ProcessPath {
    $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $u = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$LocalBin;$m;$u"
}
# The PATH a NEW window gets: the machine's entries, then the user's -- how Windows builds it. This
# window's own PATH was rebuilt with ~\.local\bin first (Sync-ProcessPath), so Get-Command here
# answers for this window only, and that is how the Store's python3 shortcut hid behind a working
# install until a new window was opened (skill TODO S-016, the Windows VM, 2026-09-17).
function Get-NewWindowCommand {
    param($name)
    $dirs = (@([Environment]::GetEnvironmentVariable("Path", "Machine"),
               [Environment]::GetEnvironmentVariable("Path", "User")) -join ";") -split ";"
    foreach ($d in $dirs) {
        if (-not $d) { continue }
        try { $p = Join-Path ([Environment]::ExpandEnvironmentVariables($d)) "$name.exe" } catch { continue }
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}
# ~\.local\bin at the FRONT of the user PATH, where uv's own installer means it to be. Windows keeps
# its WindowsApps folder in the user PATH too, and a python3.exe THERE is a Store shortcut that opens
# the Store instead of running anything: when it comes first, every `python3` the method runs in a
# new window -- and in Claude Code's Bash tool -- is that shortcut (S-016). Written through the
# registry so the value keeps its REG_EXPAND_SZ kind and every %VAR% entry stays as it was; setting
# and clearing a variable through .NET is what tells running programs that the environment changed.
function Set-LocalBinFirst {
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
    if (-not $key) { return $false }
    try {
        $raw = [string]$key.GetValue("Path", "", [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
        $want = $LocalBin.TrimEnd("\")
        $same = { param($e) ([Environment]::ExpandEnvironmentVariables($e)).TrimEnd("\") -ieq $want }
        $parts = @($raw -split ";" | Where-Object { $_ -ne "" })
        if ($parts.Count -gt 0 -and (& $same $parts[0])) { return $false }
        $rest = @($parts | Where-Object { -not (& $same $_) })
        $key.SetValue("Path", ((@($LocalBin) + $rest) -join ";"), [Microsoft.Win32.RegistryValueKind]::ExpandString)
    } finally { $key.Close() }
    [Environment]::SetEnvironmentVariable("AUTOSOUND_PATH_CHANGED", "1", "User")
    [Environment]::SetEnvironmentVariable("AUTOSOUND_PATH_CHANGED", $null, "User")
    return $true
}
# A tool on PATH, or in one of the folders the installers above use -- because right after an
# install, before the PATH refresh, `Get-Command` alone says "not found" about a tool that is
# there (the same blindness the macOS script had for ~/.local/bin, 2026-08-13).
function Find-Bin {
    param($name)
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($dir in @($LocalBin, (Join-Path $env:LOCALAPPDATA "agy\bin"), (Join-Path $env:LOCALAPPDATA "omp"))) {
        $p = Join-Path $dir "$name.exe"
        if (Test-Path $p) { return $p }
    }
    return $null
}
function Add-ManifestEntry {
    param($name)
    if ($DryRun) { return }
    New-Item -ItemType Directory -Force -Path (Split-Path $Manifest) | Out-Null
    if (-not (Test-ManifestEntry $name)) { Add-Content -Path $Manifest -Value $name }
}
function Test-ManifestEntry {
    param($name)
    (Test-Path $Manifest) -and ((Get-Content $Manifest) -contains $name)
}
# One question, one answer. `Default` is what Enter means, and what -Yes / -DryRun take.
function Ask {
    param($Question, $Default = "n")
    if ($Yes) { return $true }
    if ($DryRun) { Say "would ask: $Question  (taking the default: $Default)"; return ($Default -eq "y") }
    $hint = if ($Default -eq "y") { "[Y/n]" } else { "[y/N]" }
    $a = Read-Host "  $Question $hint"
    if ($a -match '^[yY]') { return $true }
    if ($a -match '^[nN]') { return $false }
    if ($a -eq "") { return ($Default -eq "y") }
    return $false
}
# "Enter to do it now, s to skip" -- for the sign-ins, which need a browser and a person. Never
# under -Yes: an unattended run has nobody to click Authorize.
function Offer {
    param($Prompt)
    if ($Yes -or $DryRun) { return $false }
    $a = Read-Host "     $Prompt"
    return -not ($a -match '^[sSnN]')
}
function Test-RewApi {
    # A TCP connect, not an HTTP request: a closed port is the normal state at install time, and
    # a failed Invoke-WebRequest leaves a "TerminatingError" line in every transcript.
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $ok = $c.ConnectAsync("127.0.0.1", 4735).Wait(1500) -and $c.Connected
        $c.Close()
        return [bool]$ok
    } catch { return $false }
}
# REW's executable, when REW is installed: the default place first, then wherever its uninstall
# entry says. The path matters beyond detection: `roomeqwizard.exe -api` is REW's own switch for
# starting with the API up, so the installer puts a "REW (API on)" shortcut on the Desktop.
#
# Corrected 2026-08-19: this used to say Windows had no "start the API when REW starts" box and
# the macOS build did. It was not a platform difference -- it was a VERSION difference. The API
# arrived in the 5.40 betas; the release build (V5.31.3) has no API tab at all, which is what the
# first Windows machine had. On a beta the panel is identical on both platforms (user's
# screenshot). The shortcut stays: it is one click that cannot be forgotten, and it works whether
# or not the box is ticked.
function Get-RewExe {
    foreach ($p in @((Join-Path $env:ProgramFiles "REW\roomeqwizard.exe"), (Join-Path $env:ProgramFiles "REW\REW.exe"))) {
        if (Test-Path $p) { return $p }
    }
    foreach ($k in @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
                     "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
                     "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*")) {
        $hit = Get-ItemProperty $k -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "REW*" -or $_.DisplayName -like "Room EQ Wizard*" } | Select-Object -First 1
        if ($hit) {
            foreach ($cand in @($hit.InstallLocation, $hit.DisplayIcon)) {
                if (-not $cand) { continue }
                $cand = "$cand" -replace ',\d+$', '' -replace '"', ''
                if ($cand -like "*.exe" -and (Test-Path $cand)) { return $cand }
                $exe = Join-Path $cand "roomeqwizard.exe"
                if (Test-Path $exe) { return $exe }
            }
            return "found"   # installed, executable not located: detection still counts
        }
    }
    return $null
}
function Test-RewApp { return [bool](Get-RewExe) }
# agy through Google Cloud's ADC (hub #234): the credentials file, the machine's critic-env -- the one place every run
# of the method reads, the app's included (autosound_ai.py agy_sign_in) -- and whether the switch is on.
function Get-AdcFile {
    if ($env:GOOGLE_APPLICATION_CREDENTIALS) { return $env:GOOGLE_APPLICATION_CREDENTIALS }
    return (Join-Path $env:APPDATA "gcloud\application_default_credentials.json")
}
function Get-CriticEnvPath { return (Join-Path $env:APPDATA "autosound\critic-env") }
function Test-AdcSwitch {
    if ($env:AGY_ADC_AUTH -eq "true") { return $true }
    $ce = Get-CriticEnvPath
    if (Test-Path $ce) { return [bool](Select-String -Path $ce -Pattern '^AGY_ADC_AUTH=true$' -Quiet) }
    return $false
}
function Set-CriticEnvAdc {  # AGY_ADC_AUTH=true into the critic-env, once; UTF-8 without a BOM, as the method reads it
    $ce = Get-CriticEnvPath
    if ((Test-Path $ce) -and (Select-String -Path $ce -Pattern '^AGY_ADC_AUTH=true$' -Quiet)) { return $true }
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path $ce) | Out-Null
        $text = "# agy signs in through Google Cloud ADC (hub #234) -- written by the installer`nAGY_ADC_AUTH=true`n"
        if ((Test-Path $ce) -and (Get-Item $ce).Length -gt 0 -and -not ((Get-Content $ce -Raw).EndsWith("`n"))) { $text = "`n" + $text }
        [System.IO.File]::AppendAllText($ce, $text, (New-Object System.Text.UTF8Encoding $false))
        return $true
    } catch { return $false }
}

function Get-AgyStatus {  # the account, or "set up", when the reviewer is already configured
    # Read off disk, not by running `agy`: the CLI is interactive -- it opens its own screen and
    # waits -- so there is nothing to ask it that does not take over the terminal.
    #
    # SEVERAL signals, because the sign-in does not land in one place and every version of this so
    # far has missed one:
    #   1. oauth_creds.json -- what Google's own gemini-cli writes; agy shares the folder, but a
    #      machine with only agy on it need not have the file (macOS, 2026-08-19: a machine that
    #      had signed in was offered the sign-in again, because only this was checked).
    #   2. antigravity\antigravity_state.pbtxt -- the Antigravity IDE's state.
    #   3. antigravity-cli\jetski_state.pbtxt -- the CLI's own, and the second miss: this installer
    #      installs the CLI, so a machine that only ever had agy has no antigravity\ folder at all
    #      (user, Windows 11, 2026-08-19: ~\.gemini held exactly antigravity-cli and config).
    #   4. config\projects\*.json -- written once a project has been chosen, which happens after
    #      signing in.
    #   (An exported API key is NOT a sign of this: it used to be the fifth signal, and on a machine
    #   that never signed in it skipped the sign-in while agy never reads the key -- hub #187.)
    #   0. Google Cloud's ADC (hub #234): agy signs in with it when AGY_ADC_AUTH=true reaches it and the file
    #      exists -- the existence only, like the rest.
    # Only the ACCOUNT is ever read -- no credential file is opened for its contents.
    $adc = Get-AdcFile
    if ((Test-Path $adc) -and ((Get-Item $adc).Length -gt 0) -and (Test-AdcSwitch)) { return "ADC (Google Cloud)" }
    $creds = Join-Path $HOME ".gemini\oauth_creds.json"
    if ((Test-Path $creds) -and ((Get-Item $creds).Length -gt 0)) {
        $accounts = Join-Path $HOME ".gemini\google_accounts.json"
        if (Test-Path $accounts) {
            $raw = (Get-Content $accounts -Raw -ErrorAction SilentlyContinue)
            if ($raw -match '"active"\s*:\s*"([^"]*)"') { return $Matches[1] }
        }
        return "set up"
    }
    $state = Join-Path $HOME ".gemini\antigravity\antigravity_state.pbtxt"
    if (Test-Path $state) {
        $raw = (Get-Content $state -Raw -ErrorAction SilentlyContinue)
        if ($raw -match 'agent_onboarding_completed:\s*true') { return "set up" }
    }
    $cliState = Join-Path $HOME ".gemini\antigravity-cli\jetski_state.pbtxt"
    if (Test-Path $cliState) {
        $raw = (Get-Content $cliState -Raw -ErrorAction SilentlyContinue)
        if ($raw -match 'POST_ONBOARDING_STEP_TYPE') { return "set up" }
    }
    $projects = Join-Path $HOME ".gemini\config\projects"
    if (Test-Path $projects) {
        if (Get-ChildItem $projects -Filter *.json -ErrorAction SilentlyContinue | Select-Object -First 1) {
            return "set up"
        }
    }
    return $null
}
function Get-ClaudeStatus {  # "email (plan)" when signed in, else $null
    $c = Find-Bin claude
    if (-not $c) { return $null }
    $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
    $s = (& $c auth status 2>$null) -join ""
    $ErrorActionPreference = $prev
    if ($s -notmatch '"loggedIn"\s*:\s*true') { return $null }
    $e = if ($s -match '"email"\s*:\s*"([^"]*)"') { $Matches[1] } else { "signed in" }
    $p = if ($s -match '"subscriptionType"\s*:\s*"([^"]*)"') { " ($($Matches[1]))" } else { "" }
    return "$e$p"
}
# The newest release from a GitHub repository, and one of its assets, without a token: the API
# allows sixty anonymous calls an hour, and this makes one.
function Get-LatestAsset {
    param($Repo, $Pattern)
    try {
        $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -UseBasicParsing
        $asset = $rel.assets | Where-Object { $_.name -match $Pattern } | Select-Object -First 1
        if ($asset) { return @{ Version = $rel.tag_name; Name = $asset.name; Url = $asset.browser_download_url } }
    } catch { $null = $_ }  # offline, rate-limited, or the API changed: the caller says what that means
    return $null
}
$Arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "amd64" }

# -- uninstall --------------------------------------------------------------------------------
if ($Uninstall) {
    Sync-ProcessPath
    Step "Removing what this script installed"
    Say "Your PROJECT FOLDERS are never touched -- not by this, not with -Yes, not ever."
    Say "They hold measurements that took hours in a car and cannot be reproduced."
    Write-Host ""

    if (Test-Path $SkillHome) {
        $item = Get-Item $SkillHome -Force
        $target = ($item.Target -join "")
        if ($item.LinkType -in @("SymbolicLink", "Junction") -and $target -like "$SkillSrc*") {
            Say "removing the tuning method (the junction and the checkout it points at)"
            # NOT Remove-Item: on Windows PowerShell 5.1 it treats the junction as a folder with
            # children and stops to ask "Are you sure?" -- which no -Yes answers, so an unattended
            # run hung there (first Windows uninstall, 2026-08-17). .NET's Directory.Delete removes
            # the LINK and leaves the target alone; the checkout is then removed on its own.
            Run { [System.IO.Directory]::Delete($SkillHome) } "remove junction" | Out-Null
            Run { Remove-Item $SkillSrc -Recurse -Force } "remove checkout" | Out-Null
        } elseif ($item.LinkType) {
            Warn "$SkillHome points at $target -- not ours, left alone"
        } else {
            Warn "$SkillHome is a real directory this script did not create -- left alone"
        }
    } else { Say "no tuning method installed by this script" }
    # The beta channel's copy has no junction to judge ownership by. Its name is the claim: this
    # script makes that folder, and nothing but this script and an app moving it writes there.
    if (Test-Path $SkillBetaSrc) {
        Say "removing the beta channel's copy of the method"
        Run { Remove-Item $SkillBetaSrc -Recurse -Force } "remove beta checkout" | Out-Null
    }
    # Phase 1's desk engine, one folder per pin and platform. Nothing but the method writes there,
    # and ~30 MB left behind is not a courtesy -- it is a binary nobody can account for later.
    if ($EngineHome -and (Test-Path $EngineHome)) {
        Say "removing Phase 1's desk engine ($(Pretty $EngineHome))"
        Run { Remove-Item $EngineHome -Recurse -Force } "remove the desk engine" | Out-Null
    }

    $uv = Find-Bin uv
    if ($uv -and (((& $uv tool list 2>$null) -join "`n") -match 'autosound-tcc')) {
        Say "removing autosound-tcc"
        Run { & $uv tool uninstall autosound-tcc } "uv tool uninstall autosound-tcc" | Out-Null
    } else { Say "autosound-tcc is not installed" }
    foreach ($lnk in @($DesktopLnk, $ProgramsLnk)) {
        if (Test-Path $lnk) { Say "removing $(Pretty $lnk)"; Run { Remove-Item $lnk -Force } "remove shortcut" | Out-Null }
    }
    if (Test-Path $RewLnk) {
        # Only when it is the one this script makes: REW's exe with -api. Anything else there is
        # somebody's own shortcut with the same name.
        $r = (New-Object -ComObject WScript.Shell).CreateShortcut($RewLnk)
        if ($r.TargetPath -like "*roomeqwizard*" -and $r.Arguments -match '-api') {
            Say "removing $(Pretty $RewLnk)"; Run { Remove-Item $RewLnk -Force } "remove REW shortcut" | Out-Null
        }
    }

    # Without -All these stay, and each for a reason: Git for Windows, Claude Code, agy and gh
    # belong to their own installers and may be in use for other work; ~\.claude is the person's
    # own configuration. -All exists for one job -- resetting a test machine -- so it asks first.
    if ($All) {
        $py = Join-Path $LocalBin "python3.exe"
        $userSite = if (Test-Path $py) { (& $py -m site --user-base 2>$null) } else { $null }
        Write-Host ""
        Say "-All also removes, and none of these were made only for tuning:"
        Say "  * uv, its downloaded Pythons, tools and cache   ~\.local\bin\uv.exe, ~\.local\share\uv, %LOCALAPPDATA%\uv"
        Say "  * Claude Code and ALL of its configuration, history, skills and plugins"
        Say "                                                   ~\.claude, ~\.claude.json, ~\.local\share\claude"
        foreach ($t in @("agy", "gh", "omp")) { if (Test-ManifestEntry $t) { Say "  * $t, which this script installed, and its settings" } }
        Say "  * TCC's own settings and log                    %APPDATA%\autosound-tcc, %LOCALAPPDATA%\autosound-tcc"
        if ($userSite) { Say "  * every package pip installed with --user       $(Pretty $userSite)" }
        Say "  Git for Windows stays: it is used by far more than this (winget uninstall Git.Git removes it)."
        Write-Host ""
        Say "Your project folders are still untouched. Nothing below reaches them."
        if (Ask "Remove all of that too?" "n") {
            if ((Test-Path (Join-Path $LocalBin "uv.exe")) -or (Test-Path (Join-Path $HOME ".local\share\uv"))) {
                Say "removing uv from ~\.local, and its cache"
                Run { Remove-Item (Join-Path $LocalBin "uv.exe"), (Join-Path $LocalBin "uvx.exe"), (Join-Path $LocalBin "uvw.exe") -Force -ErrorAction SilentlyContinue
                      Remove-Item (Join-Path $HOME ".local\share\uv"), (Join-Path $env:LOCALAPPDATA "uv"), (Join-Path $env:APPDATA "uv") -Recurse -Force -ErrorAction SilentlyContinue
                      # The python launchers uv put beside itself for --default.
                      Get-ChildItem $LocalBin -Filter "python*.exe" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
                    } "remove uv" | Out-Null
            }
            if ((Test-Path (Join-Path $LocalBin "claude.exe")) -or (Test-Path (Join-Path $HOME ".claude"))) {
                Say "removing Claude Code, ~\.claude and ~\.claude.json"
                Run { Remove-Item (Join-Path $LocalBin "claude.exe") -Force -ErrorAction SilentlyContinue
                      Remove-Item (Join-Path $HOME ".claude"), (Join-Path $HOME ".claude.json"), (Join-Path $HOME ".local\share\claude") -Recurse -Force -ErrorAction SilentlyContinue
                    } "remove Claude Code" | Out-Null
            }
            if (Test-ManifestEntry "agy") {
                Say "removing agy"
                Run { Remove-Item (Join-Path $env:LOCALAPPDATA "agy"), (Join-Path $env:LOCALAPPDATA "antigravity"), (Join-Path $HOME ".gemini\antigravity-cli") -Recurse -Force -ErrorAction SilentlyContinue } "remove agy" | Out-Null
            }
            if (Test-ManifestEntry "gh") {
                Say "removing gh"
                Run { Remove-Item (Join-Path $LocalBin "gh.exe") -Force -ErrorAction SilentlyContinue
                      Remove-Item (Join-Path $env:APPDATA "GitHub CLI") -Recurse -Force -ErrorAction SilentlyContinue } "remove gh" | Out-Null
            }
            if (Test-ManifestEntry "omp") {
                Say "removing omp"
                Run { Remove-Item (Join-Path $env:LOCALAPPDATA "omp"), (Join-Path $HOME ".omp") -Recurse -Force -ErrorAction SilentlyContinue } "remove omp" | Out-Null
            }
            $tccDirs = @((Join-Path $env:APPDATA "autosound-tcc"), (Join-Path $env:LOCALAPPDATA "autosound-tcc"), (Join-Path $HOME ".config\autosound-tcc")) | Where-Object { Test-Path $_ }
            if ($tccDirs) {
                Say "removing TCC's settings and log"
                Run { Remove-Item $tccDirs -Recurse -Force -ErrorAction SilentlyContinue } "remove TCC settings" | Out-Null
            }
            if ($userSite -and (Test-Path $userSite)) {
                Say "removing $(Pretty $userSite)"
                Run { Remove-Item $userSite -Recurse -Force -ErrorAction SilentlyContinue } "remove user site" | Out-Null
            }
            Run { Remove-Item $Manifest -Force -ErrorAction SilentlyContinue } "remove manifest" | Out-Null
            Write-Host ""
            Say "Gone. The PATH entries the installers added (uv's, agy's) are left as they are: harmless"
            Say "when the folders are empty, and not this script's to edit."
        } else { Say "Left alone." }
    } else {
        Write-Host ""
        Say "Left in place on purpose: Git for Windows, Claude Code, uv and its Python, agy, gh (their"
        Say "own installers own them), the Python packages, and ~\.claude (yours)."
        Say "Re-run with -Uninstall -All to remove those too."
    }
    Say "Every tuning project you have is untouched."
    Stop-Installer 0; return
}

# =============================================================================================
# BLOCK 1 -- look, ask. Everything a person has to do before the end is here.
# =============================================================================================
Step "Autosound tuning -- installer"

# See the machine as a NEW window would: a PowerShell started from a console that was open before
# an earlier install inherits that console's PATH, and reported Git for Windows as missing --
# and promised a permission dialog -- on a machine that had it (VM, third run, 2026-08-17).
Sync-ProcessPath
$HaveGit    = [bool](Have git)
$HaveClaude = [bool](Find-Bin claude)
$HaveUv     = [bool](Find-Bin uv)
$HaveAgy    = [bool](Find-Bin agy)
$HaveGh     = [bool](Find-Bin gh)
$HaveOmp    = [bool](Find-Bin omp)
$HavePy3    = Test-Path (Join-Path $LocalBin "python3.exe")
# The app's launchers, where `uv tool install` puts them -- the plan used to promise "will install"
# for an app installed a minute earlier (S-009).
$HaveTcc    = (Test-Path (Join-Path $LocalBin "autosound-tcc-gui.exe")) -or (Test-Path (Join-Path $LocalBin "autosound-tcc.exe"))
$RewExe     = Get-RewExe
$RewApp     = [bool]$RewExe
$RewApi     = Test-RewApi

Say "What is here, and what will be installed:"
if ($HaveGit)    { Say "  OK   Git for Windows (git, Git Bash)" } else { Say "  --   Git for Windows (git, Git Bash)   will install" }
if ($HaveClaude) { Say "  OK   Claude Code" }                       else { Say "  --   Claude Code                        will install" }
if ($HaveUv)     { Say "  OK   uv (installs Python)" }              else { Say "  --   uv, and a Python 3.12             will install" }
if ($Mode -eq "tcc") {
    if ($HaveTcc) { Say "  OK   Autosound TCC, the desktop app -- updates to its newest release" }
    else          { Say "  --   Autosound TCC, the desktop app     will install" }
}
if ($WantReviewer) {
    if ($HaveAgy) { Say "  OK   Gemini reviewer (agy)" } else { Say "  --   Gemini reviewer (agy)              will install" }
}
if ($RewApi)      { Say "  OK   REW, and its API is on" }
elseif ($RewApp)  { Say "  OK   REW -- its API is off; a shortcut that starts REW with it on goes on your Desktop" }
else              { Say "  --   REW not found -- install a BETA from roomeqwizard.com/beta.html (the release has no API)" }

# `gh` already on the machine means the answer was given on an earlier run, so its backup sign-in
# stays offered; otherwise it comes only with -GitHub. Nothing outward-facing rides on it: the
# installer never pushes a project anywhere (SCR-049).
if ($WantGitHub -eq "auto") { $WantGitHub = if ($HaveGh) { "1" } else { "0" } }

# ONE screen naming everything that will be downloaded, before any of it happens.
Write-Host ""
Say "This installs:"
$mb = 100
if (-not $HaveGit)    { Say "  * Git for Windows -- git, and Git Bash for Claude Code    git-scm.com; one permission dialog"; $mb += 60 }
if (-not $HaveClaude) { Say "  * Claude Code -- the AI that runs the method              claude.ai"; $mb += 200 }
if (-not $HaveUv)     { Say "  * uv, and a Python 3.12 of its own                        astral.sh"; $mb += 60 }
elseif (-not $HavePy3){ Say "  * a Python 3.12, through uv                               astral.sh"; $mb += 40 }
if ($PluginRoot) {
    Say "  * the tuning method -- this plugin, v$PluginVersion, checked against its signed release (not cloned)"
} else {
    Say "  * the tuning method -- its references and tools           github.com/ayukhno/autosound-tuning-skill"
}
Say "  * numpy, scipy, matplotlib -- the method's own tools       pypi.org"
if ($Mode -eq "tcc") {
    Say "  * Autosound TCC -- the desktop app, ~700 MB                github.com/ayukhno/autosound-tcc"
    Say "  * `"Autosound TCC`" shortcuts on your Desktop and in the Start Menu"
    $mb += 700
}
if ($WantReviewer -and -not $HaveAgy) { Say "  * Gemini as the second AI, the reviewer -- Google's agy   antigravity.google"; $mb += 100 }
if ($WantGitHub -eq "1" -and -not $HaveGh) { Say "  * gh, GitHub's command -- for the project backup           github.com/cli/cli"; $mb += 50 }
if ($WantOmp -and -not $HaveOmp) { Say "  * omp -- offers TCC every non-Claude model (metered)       omp.sh"; $mb += 150 }
Write-Host ""
$size = if ($mb -ge 1000) { "about $([math]::Floor($mb / 1000)).$([math]::Floor(($mb % 1000) / 100)) GB" } else { "about $mb MB" }
if (-not $HaveGit) {
    Say "Everything goes into your user profile except Git, which installs for the whole PC and"
    Say "asks Windows' permission once (a dialog: click Yes). It signs you in nowhere -- that comes at"
    Say "the end, in your browser -- and never touches a project folder."
    Say "Downloads $size; 5 to 15 minutes. After the dialog you can walk away."
} else {
    Say "Everything goes into your user profile. It signs you in nowhere -- that comes at the end,"
    Say "in your browser -- and never touches a project folder."
    Say "Downloads $size; a few minutes. Nothing more is asked until the end."
}
Write-Host ""
$opts = @()
if ($Mode -eq "tcc")   { $opts += "-Terminal (no app)" }
if ($WantReviewer)     { $opts += "-NoReviewer" }
if ($WantGitHub -eq "1") { $opts += "-NoGitHub" }
if ($opts.Count -gt 0) { Say "To leave something out, answer n and re-run with an option: $($opts -join ', '). -Help lists them all." }
if ($Mode -eq "tcc" -and -not $WantOmp -and -not $HaveOmp) {
    Say "Optional: -WithOmp also installs omp, so the app can offer models other than Claude"
    Say "(billed per use; nothing goes through it unless you pick such a model)."
}
if ($WantGitHub -eq "0") {
    Say "Optional: -GitHub also installs GitHub's gh, to back each car's record up to a free, private"
    Say "repository -- the ledger, the journal, the DSP config backups; the measurements stay on your disk."
}
# Declined -- or no console to ask on and no -Yes, which takes the default -- it is a stop, 1, nothing installed (#142):
# it ended 0, which a script read as ready. install.sh's consent.
if (-not $DryRun) {
    if (-not (Ask "Go ahead?" "n")) {
        Write-Host ""
        Warn "Nothing installed. Re-run when you want to."
        Stop-Installer 1; return
    }
}
# From here the run is going ahead (#142): the receipt says `stopped` until the end writes how the run ended, so a
# terminating error, Ctrl-C or a closed window leaves no earlier run's `ready` standing -- install.sh's going_ahead.
Write-Receipt "stopped"
if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $LocalBin | Out-Null }
$env:Path = "$LocalBin;$env:Path"

# =============================================================================================
# UNATTENDED -- from here to the checks, nothing needs a person (one dialog for Git, right now).
# =============================================================================================

# -- Git for Windows ---------------------------------------------------------------------------
if (-not $HaveGit) {
    Step "Git for Windows"
    Say "Windows will ask for permission (a dialog: click Yes). Nothing else here asks for anything."
    if (Have winget) {
        Say "through winget..."
        Run { winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements --silent } "winget install --id Git.Git" | Out-Null
    } else {
        # No winget (older Windows 10, or a Store-less build): the official installer, silently.
        $g = Get-LatestAsset "git-for-windows/git" ("^Git-.*-" + $(if ($Arch -eq "arm64") { "arm64" } else { "64-bit" }) + "\.exe$")
        if ($g) {
            Say "through the official installer, $($g.Name)..."
            if (-not $DryRun) {
                New-Item -ItemType Directory -Force -Path $Scratch | Out-Null
                $tmp = Join-Path $Scratch $g.Name
                try {
                    Invoke-WebRequest -Uri $g.Url -OutFile $tmp -UseBasicParsing
                    Unblock-File $tmp -ErrorAction SilentlyContinue
                    # CHECK WHO SIGNED IT before running it as an installer. git-for-windows
                    # publishes no checksums file, but every .exe in the release is Authenticode
                    # signed -- and this is a download we hand straight to Start-Process, which is
                    # the strongest thing this script does with a file off the internet (HUB-031).
                    $sig = Get-AuthenticodeSignature -FilePath $tmp
                    $who = "$($sig.SignerCertificate.Subject)"
                    if ($sig.Status -ne "Valid") {
                        Warn "the Git installer is NOT validly signed (status: $($sig.Status)) -- not running it."
                        Warn "install Git for Windows yourself from git-scm.com/download/win"
                    } elseif ($who -notmatch "Johannes Schindelin|Git for Windows") {
                        # Valid but somebody else's: a signature proves a signer, and this is not
                        # the signer we came for.
                        Warn "the Git installer is signed by someone unexpected -- not running it."
                        Warn "signer: $who"
                    } else {
                        Say "  signature OK ($(($who -split ',')[0]))"
                        Start-Process -FilePath $tmp -ArgumentList "/VERYSILENT", "/NORESTART" -Wait
                    }
                } catch { Warn "the Git installer did not run: $($_.Exception.Message)" }
                Remove-Item $tmp -Force -ErrorAction SilentlyContinue
            } else { Say "would run: $($g.Name) /VERYSILENT /NORESTART" }
        } else {
            Warn "neither winget nor GitHub answered; install Git for Windows from git-scm.com/download/win"
        }
    }
    Sync-ProcessPath
    if (Have git) { Say "OK   $(& git --version)" }
    elseif (-not $DryRun) {
        Warn "git is still not found. Install Git for Windows from git-scm.com/download/win, open a NEW"
        Warn "window, and run this again. Nothing below works without it."
        Stop-Installer 1; return
    }
}

# -- Claude Code -------------------------------------------------------------------------------
Step "Claude Code"
$ClaudeBin = Find-Bin claude
if ($ClaudeBin) {
    Say "OK   $(& $ClaudeBin --version 2>$null)"
} else {
    # Invoke-Upstream says whose script runs, so the step does not say it first (skill #96: it read twice).
    if (Invoke-Upstream "https://claude.ai/install.ps1" "Claude Code") {
        Sync-ProcessPath
        if (Test-Path (Join-Path $LocalBin "claude.exe")) { Add-ManifestEntry "claude" }
    }
    $ClaudeBin = Find-Bin claude
    if ($ClaudeBin) { Say "OK   $(& $ClaudeBin --version 2>$null)" }
    elseif (-not $DryRun) {
        Warn "Claude Code did not install. Nothing can run a session without it; when the network is"
        Warn "back:  irm https://claude.ai/install.ps1 | iex"
    }
}

# -- uv, and the Python behind `python3` --------------------------------------------------------
# Windows ships no python3. It ships a Store shortcut CALLED python3.exe, which opens the Store
# when the method's tools call it. uv installs a real one and puts python3.exe in ~\.local\bin, at
# the FRONT of the user PATH -- so the method's `python3 rew_tool\...` finds Python, in a terminal
# and inside Claude Code's Bash tool alike.
Step "uv, and Python 3.12"
$Uv = Find-Bin uv
if ($Uv) {
    Say "OK   $(& $Uv --version 2>$null)"
} else {
    # PINNED -- see the same note in install.sh; the two versions must match, and
    # installer-consistency.py fails when they drift. The URL Invoke-Upstream prints carries the pin.
    if (Invoke-Upstream "https://astral.sh/uv/$UvVersion/install.ps1" "uv") {
        Sync-ProcessPath
        if (Test-Path (Join-Path $LocalBin "uv.exe")) { Add-ManifestEntry "uv" }
    }
    $Uv = Find-Bin uv
    if ($Uv) { Say "OK   $(& $Uv --version 2>$null)" }
    # A dry run installed nothing; describe the plan, not the machine.
    if (-not $Uv -and $DryRun) { $Uv = "uv" }
}
$Py3 = Join-Path $LocalBin "python3.exe"
if ($Uv) {
    if (Test-Path $Py3) {
        Say "OK   $(& $Py3 -V 2>&1) at $(Pretty $Py3)"
    } else {
        Say "Python 3.12, as this profile's python, python3 and python3.12..."
        Run { & $Uv python install 3.12 --default --quiet } "uv python install 3.12 --default" | Out-Null
        if (Test-Path $Py3) { Say "OK   $(& $Py3 -V 2>&1) at $(Pretty $Py3)" }
        elseif (-not $DryRun) { Warn "python3.exe did not appear in $(Pretty $LocalBin); the method's tools will not run until it does." }
    }
} elseif (-not $DryRun) {
    Warn "uv did not install; without it there is no Python for the method's tools and no app."
}
# What a NEW window will run for `python3` -- not this window, whose PATH this script rebuilt.
if (Test-Path $Py3) {
    $NewPy = Get-NewWindowCommand "python3"
    if (-not $NewPy -or ($NewPy -ine $Py3)) {
        $was = if ($NewPy) { $NewPy } else { "nothing" }
        if ($DryRun) { Say "would move $(Pretty $LocalBin) to the front of your user PATH: a new window's python3 is $was" }
        elseif (Set-LocalBinFirst) { Say "OK   $(Pretty $LocalBin) now leads your user PATH -- a new window's python3 was $was" }
    }
}

# -- the tuning method -------------------------------------------------------------------------
# Put a checkout of the method at $Dir on $Ref (Sync-MethodCheckout, below): move it when it is already a checkout,
# make one when there is none. ONE function for both copies -- the terminal's and the beta channel's
# (autosound-hub #145) -- the mirror of checkout_method in install.sh. $true unless the copy is not on $Ref: a new
# copy not made, or refused, or removed; an update refused for its signature, or put back; an update not made -- its
# fetch failed, or its local changes could not be kept -- which leaves the copy where it was (R32, #142).
# What can be said of $Ref by its name alone, each said on a line (skill #99, #101): $true -- settled, nothing to
# check (a dry run, AUTOSOUND_SKIP_TAG_VERIFY=1, a name that is not a release -- only ever one named with -SkillRef or
# -TccRef: installed, and said UNSIGNED -- a tag before $SignedFrom); $false -- its signature has to be checked. The
# mirror of settled_by_name in install.sh.
function Test-SettledByName {
    param([string]$Ref, [string]$SignedFrom)
    if ($DryRun) { Say "would check the signature of $Ref"; return $true }
    if ($env:AUTOSOUND_SKIP_TAG_VERIFY -eq "1") {
        Warn "the signature of $Ref is NOT checked: AUTOSOUND_SKIP_TAG_VERIFY=1 is set (a developer's switch)"
        return $true
    }
    if (-not (Test-ReleaseTag $Ref)) { Warn "$Ref is not a release: it is installed UNSIGNED, unchecked"; return $true }
    $ver = ($Ref -replace '^beta-', '') -replace '-rc[0-9]+\z', ''
    if ([version]($ver -replace '^v', '') -lt [version]($SignedFrom -replace '^v', '')) {
        Say "$Ref predates signed tags (they start at $SignedFrom) -- installed without a signature check"
        return $true
    }
    return $false
}

# Is $Ref, fetched into $Dir, a signed release (skill #99)? $true -- or it is settled by its name, above; $false --
# nothing may be installed from it. $SignedFrom and $Whose are the method's unless given: the app's own tags pass
# $TccSignedFrom and "TCC" (skill #101). The mirror of verify_tag in install.sh.
#   A good signature is one answer only (T-35, #142): git's success and ssh-keygen's line 'Good "git" signature for
# <principal> with ...', whatever the person's git or GPG configuration says. ssh-keygen is named for the check, so a
# sign-only helper set as gpg.ssh.program is not asked to verify; and git picks the verifier from the signature, not
# from gpg.format, so an OpenPGP tag the person's own gpg calls good says "Good" too. gpg.minTrustLevel is held at
# `fully`, git's rating of a key in allowed_signers: a person's `ultimate` refused every good release.
function Test-TagSignature {
    param([string]$Dir, [string]$Ref, [string]$SignedFrom = $SkillSignedFrom, [string]$Whose = "the skill")
    if (Test-SettledByName $Ref $SignedFrom) { return $true }
    $signers = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($signers, "$SkillSigningPrincipal namespaces=`"git`" $SkillSigningKey`n")
    # Under "Continue" (the script's own setting), not "SilentlyContinue": Windows PowerShell 5.1 drops a native
    # program's stderr records at SilentlyContinue BEFORE `2>&1` can merge them, and git says both "Good" and every
    # reason on stderr -- the VM refused beta-v3.0.64-rc1 with no reason printed at all (2026-09-29).
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    # $null, not 0 (#142): a git that could not start sets no code, and must not read as one that said yes.
    $global:LASTEXITCODE = $null
    $out = @(& git -C $Dir -c gpg.format=ssh -c gpg.ssh.program=ssh-keygen -c gpg.minTrustLevel=fully -c "gpg.ssh.allowedSignersFile=$signers" verify-tag $Ref 2>&1)
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $prev
    Remove-Item $signers -Force -ErrorAction SilentlyContinue
    $said = ($out | ForEach-Object { "$_" }) -join "`n"
    # Case-sensitive (-cmatch; -match is not), as install.sh's grep and case are.
    $good = '(?m)^Good "git" signature for ' + [regex]::Escape($SkillSigningPrincipal) + ' with '
    if ($rc -eq 0 -and $said -cmatch $good) { Say "OK   $Ref is signed by $Whose's author"; return $true }
    # A git that cannot check is not a bad signature -- git's own sentences, whole, as install.sh reads them: each at
    # the START of a line, after git's own prefix (#142). A signer's OpenPGP user id is printed inside gpg's line, and
    # one that read "cannot run ssh-keygen" made a forged tag read as a machine that cannot check.
    if ($said -cmatch '(?m)^(?:(?:error|fatal): (?:unsupported value for gpg\.format|ssh-keygen -Y find-principals/verify|cannot (?:run|spawn) ssh-keygen)|(?:ssh-keygen: )?(?:illegal|unknown) option -- Y)') {
        Warn "the signature of $Ref could not be checked here -- it is not installed:"
        $out | Select-Object -Last 2 | ForEach-Object { Write-Host "      $_" }
        Warn "this git ($(& git --version 2>$null)) or its ssh-keygen may be too old to check one: git 2.34 or newer, with OpenSSH 8.2 or newer, is needed"
        return $false
    }
    Warn "the signature of $Ref does not check out -- it is not installed:"
    $out | Select-Object -Last 2 | ForEach-Object { Write-Host "      $_" }
    Warn "a release of $Whose is signed by its author; this one is not, or not by that key."
    return $false
}

# The app's tag is checked like the method's before uv installs it (skill #101) -- the mirror of check_tcc_tag in
# install.sh and of TCC's own updater: the one tag is fetched into a temporary BARE repository and verified there.
# $true -- install it, and $script:TccSha is the commit the verified tag names ("" when nothing was verified); $false
# -- it is not installed. Under $Scratch, not %TEMP%: see the note beside $Scratch.
$script:TccSha = ""
function Test-TccTag {
    param([string]$Ref)
    $script:TccSha = ""
    if (Test-SettledByName $Ref $TccSignedFrom) { return $true }
    $repo = Join-Path $Scratch ("tcc-tag-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $repo | Out-Null
    # Under "Continue", as in Test-TagSignature: git says every reason on stderr.
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $global:LASTEXITCODE = $null
    $said = @(& git init --quiet --bare $repo 2>&1)
    if ($LASTEXITCODE -eq 0) {
        $said = @(& git -C $repo fetch --quiet --no-tags --depth 1 $TccRepo "+refs/tags/${Ref}:refs/tags/${Ref}" 2>&1)
    }
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($rc -ne 0) {
        Warn "could not fetch $Ref to check its signature -- it is not installed:"
        $said | Select-Object -Last 2 | ForEach-Object { Write-Host "      $_" }
        Remove-Item $repo -Recurse -Force -ErrorAction SilentlyContinue
        return $false
    }
    $verified = Test-TagSignature $repo $Ref $TccSignedFrom "TCC"
    if ($verified) { $script:TccSha = "$(& git -C $repo rev-parse --verify --quiet "refs/tags/${Ref}^{commit}" 2>$null)".Trim() }
    Remove-Item $repo -Recurse -Force -ErrorAction SilentlyContinue
    if (-not $verified) { return $false }
    # Fail closed, as TCC does: a verified tag whose commit git cannot name is not installed unpinned.
    if (-not $script:TccSha) { Warn "git names no commit for $Ref, verified a moment ago -- it is not installed"; return $false }
    return $true
}
# Does $Ref still name $Sha? TCC's "moved" check, right before uv -- see tcc_tag_still_at in install.sh.
function Test-TccTagStillAt {
    param([string]$Ref, [string]$Sha)
    $peeled = @(& git ls-remote $TccRepo "refs/tags/${Ref}^{}" 2>$null)
    $now = if ($peeled.Count -gt 0) { ("$($peeled[0])" -split "\s+")[0] } else { "" }
    return ($now -eq $Sha)
}

# The installed clone has changes somebody made by hand (skill #91; the Windows VM, 2026-09-27). Kept as a patch by
# the NEW tag's upkeep.py, sent to the skill only on the person's word, then the clone is reset -- see keep_local in
# install.sh. $true = kept and reset, $false = left as it was.
function Save-LocalChanges {
    param([string]$Dir, [string]$What)
    Warn "$What has local changes -- somebody edited the installed copy:"
    & git -C $Dir status --porcelain --untracked-files=all 2>$null | ForEach-Object { Write-Host "      $($_.Substring(3))" }
    if ($DryRun) { Say "would keep them as a patch in $(Pretty $LocalChanges), then reset"; return $true }
    # `git archive`, not `git show`: PowerShell 5 decodes a native program's output with the console's code page,
    # so the files would arrive with every non-ASCII character changed. A zip carries the bytes as they are.
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("autosound-upkeep-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp "upkeep.zip"
    $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
    & git -C $Dir archive --format=zip -o $zip FETCH_HEAD skills/autosound-tuning/scripts/upkeep.py `
        skills/autosound-tuning/rew_tool/gates/side_effect.py skills/autosound-tuning/rew_tool/console.py 2>&1 | Out-Null
    $ErrorActionPreference = $prev
    if (Test-Path $zip) { Expand-Archive -Path $zip -DestinationPath $tmp -Force }
    $tool = Join-Path $tmp "skills\autosound-tuning\scripts\upkeep.py"
    if (-not (Test-Path $Py3) -or -not (Test-Path $tool)) {
        Warn "they cannot be kept automatically here (no python3, or the new version has no upkeep.py)."
        Warn "keep them yourself (git -C $(Pretty $Dir) stash), then run this again; nothing was changed."
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        return $false
    }
    Say "they are kept as a patch in $(Pretty $LocalChanges) before the update -- nothing is lost."
    Say "Sent to the skill as an issue, the patch tells its author what had to be fixed by hand."
    $send = @()
    if (Offer "Enter = send it / s = keep it only here") { $send = @("--send") }
    $global:LASTEXITCODE = 0
    # To the screen, not into this function's answer: its lines would make any answer read as "kept" (R32, #142).
    & $Py3 $tool --clone $Dir keep-local @send | Out-Host
    $kept = ($LASTEXITCODE -eq 0)
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    if (-not $kept) { Warn "the changes were not kept, so nothing was reset or updated -- see above." }
    return $kept
}

# Is HEAD in $Dir the commit $Rev names? Both asked of git; a HEAD it cannot name (nothing checked out yet) is not.
# The mirror of head_is in install.sh.
function Test-HeadIs {
    param([string]$Dir, [string]$Rev)
    $at   = "$(& git -C $Dir rev-parse --verify --quiet HEAD 2>$null)".Trim()
    $want = "$(& git -C $Dir rev-parse --verify --quiet $Rev 2>$null)".Trim()
    return [bool]($at -and $at -eq $want)
}

# An update that does not land leaves refs/tags as it found them (R48, #142): the tag its fetch wrote into $Dir is
# deleted again -- or, when a local tag of that name was there before, given its old value back (the fetch's `+`
# overwrote it). The mirror of put_tag_back in install.sh.
function Restore-Tag {
    param([string]$Dir, [string]$TagRef, [string]$Had)
    if ($DryRun -or -not $TagRef) { return }
    $global:LASTEXITCODE = $null
    if ($Had) { & git -C $Dir update-ref $TagRef $Had 2>&1 | Out-Null } else { & git -C $Dir update-ref -d $TagRef 2>&1 | Out-Null }
    if ($LASTEXITCODE -ne 0) { Warn "$TagRef could not be put back as it was in $(Pretty $Dir)" }
}

# $script:SignatureRefused tells the caller that a copy was refused for its signature, not for the network, and
# $script:NotTheTag that HEAD was not $Ref after its checkout: a new copy is removed, an update put back.
$script:SignatureRefused = $false
$script:NotTheTag = $false
# A copy is the tag it checked (T-45, #142) -- see checkout_method in install.sh. A release is fetched INTO refs/tags
# and checked out from there, and HEAD is held to that tag's commit; any other name (a branch, a sha, named with
# -SkillRef and installed UNSIGNED) is fetched by name and checked out from FETCH_HEAD. `${Ref}`, braced: "$Ref:refs"
# would read as a scoped variable. An update that does not land leaves refs/tags as it found them (Restore-Tag, R48),
# and `--no-tags` fetches the one tag asked for, not every tag on the same commit -- a refused one's siblings among them.
function Sync-MethodCheckout {
    param([string]$Dir, [string]$Ref, [string]$What)
    $spec = $Ref; $want = 'FETCH_HEAD^{commit}'; $tagRef = ""
    if (Test-ReleaseTag $Ref) { $spec = "+refs/tags/${Ref}:refs/tags/${Ref}"; $want = "refs/tags/${Ref}^{commit}"; $tagRef = "refs/tags/${Ref}" }
    if (Test-Path (Join-Path $Dir ".git")) {
        # A dry run on Windows without Git has no git to ask (#142).
        if ($DryRun -and -not (Have git)) { Say "would fetch $Ref into $(Pretty $Dir), check it, and check it out (no git yet)"; return $true }
        $had = ""
        if ($tagRef) { $had = "$(& git -C $Dir rev-parse --verify --quiet $tagRef 2>$null)".Trim() }
        # CHECKED, both of them, and the mirror of install.sh. Unchecked, a network blip or a
        # moved ref left the method on the previous version while this script printed
        # "updating to <ref>" and carried on -- the one failure mode where the user is told the
        # opposite of what happened (HUB-042).
        $fetched  = Run { & git -C $Dir fetch --quiet --no-tags --depth 1 origin $spec } "git fetch $Ref"
        if (-not $fetched) {
            Warn "could not fetch $Ref for $What -- it is STILL at $(& git -C $Dir describe --tags --always 2>$null)."
            Warn "check the network, then run this script again; nothing was changed."
            return $false
        }
        # What was fetched is checked before anything of it runs or is checked out (skill #99), and local
        # changes are kept as a patch rather than refused with the wrong reason (skill #91).
        if (-not (Test-TagSignature $Dir $Ref)) { Restore-Tag $Dir $tagRef $had; $script:SignatureRefused = $true; return $false }
        # What changed in the copy, read WITH its exit code (#142): a status that fails -- a broken submodule says "not a
        # git repository" -- read as a clean tree, and the forced put-back below then dropped a hand edit the checkout
        # had refused to overwrite. A status that cannot be read is a stop: nothing of the copy is touched. Under
        # "Continue", as in Test-TagSignature: git says why on stderr.
        $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $global:LASTEXITCODE = $null
        $status = @(& git -C $Dir status --porcelain --untracked-files=all 2>&1)
        $statusRc = $LASTEXITCODE
        $ErrorActionPreference = $prev
        $changed = @($status | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] })
        if ($statusRc -ne 0) {
            Warn "could not read what changed in $What -- git status failed (code $statusRc); nothing was changed:"
            $status | Where-Object { $_ -is [System.Management.Automation.ErrorRecord] } | Select-Object -Last 2 | ForEach-Object { Write-Host "      $_" }
            Restore-Tag $Dir $tagRef $had
            return $false
        }
        # The put-back may force only over a tree it has seen clean: read empty here, or read again empty once the
        # local changes were kept and the copy reset.
        $force = @("--force")
        if ($changed.Count -gt 0) {
            if (-not (Save-LocalChanges $Dir $What)) { Restore-Tag $Dir $tagRef $had; return $false }
            $force = @()
            $global:LASTEXITCODE = $null
            $again = @(& git -C $Dir status --porcelain --untracked-files=all 2>$null)
            if ($LASTEXITCODE -eq 0 -and $again.Count -eq 0) { $force = @("--force") }
        }
        $was = "$(& git -C $Dir rev-parse --verify --quiet HEAD 2>$null)".Trim()
        Run { & git -c advice.detachedHead=false -C $Dir checkout --quiet $want } "git checkout $want" | Out-Null
        if ($DryRun -or (Test-HeadIs $Dir $want)) { return $true }
        # Put back: over a tree seen clean before this checkout, --force drops only what a checkout that broke off left
        # behind; over any other, the put-back is not forced.
        if ($was) { & git -c advice.detachedHead=false -C $Dir checkout --quiet @force $was 2>&1 | Out-Null }
        Restore-Tag $Dir $tagRef $had
        Warn "the update did not take: HEAD was not $Ref after the checkout; $What is back at $(& git -C $Dir describe --tags --always 2>$null)."
        $script:NotTheTag = $true
        return $false
    }
    if ($DryRun) { Say "would fetch $Ref into $(Pretty $Dir), check it, and check it out"; return $true }
    # Made here, so removed here when it fails -- an empty folder already at that path too, which holds nothing to lose
    # (`git clone` takes an empty one as well); one with anything in it is not touched.
    if ((Test-Path $Dir) -and @(Get-ChildItem -LiteralPath $Dir -Force -ErrorAction SilentlyContinue).Count -gt 0) {
        Warn "$(Pretty $Dir) is there, and is not a checkout -- move it aside, then run this again"
        return $false
    }
    # Under "Continue", as in Test-TccTag: git says every reason on stderr.
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $global:LASTEXITCODE = $null
    $said = @(& git init --quiet $Dir 2>&1)
    if ($LASTEXITCODE -eq 0) { $said = @(& git -C $Dir remote add origin $SkillRepo 2>&1) }
    if ($LASTEXITCODE -eq 0) { $said = @(& git -C $Dir fetch --quiet --no-tags --depth 1 origin $spec 2>&1) }
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($rc -ne 0) {
        $said | ForEach-Object { Write-Host "  $_" }
        Remove-Item $Dir -Recurse -Force -ErrorAction SilentlyContinue
        return $false
    }
    # Checked before anything of it is checked out (skill #99), and removed when it fails: nothing unverified stays.
    if (-not (Test-TagSignature $Dir $Ref)) {
        $script:SignatureRefused = $true
        Remove-Item $Dir -Recurse -Force -ErrorAction SilentlyContinue
        return $false
    }
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    @(& git -c advice.detachedHead=false -C $Dir checkout --quiet $want 2>&1) | ForEach-Object { Write-Host "  $_" }
    $ErrorActionPreference = $prev
    if (Test-HeadIs $Dir $want) { return $true }
    Warn "the new copy is not $Ref after its checkout -- it is removed; nothing was installed."
    $script:NotTheTag = $true
    Remove-Item $Dir -Recurse -Force -ErrorAction SilentlyContinue
    return $false
}

# The tags $Repo lists for $Globs, names only; nothing, with $script:TagsWhy saying why, when none could be read (#142):
# git's own last line -- a proxy's certificate, a host that does not resolve -- which every stop and refusal over an
# unreadable list carries; they said "no network?" over a network that had answered. Or "no git yet": a dry run on
# Windows without Git gets this far. The one reader of a release tag list here; Test-TccTagStillAt's ls-remote is the
# app's "moved" check. install.sh's read_tags.
$script:TagsWhy = ""
function Read-ReleaseTags {
    param([string]$Repo, [string[]]$Globs)
    $script:TagsWhy = ""
    if (-not (Have git)) { $script:TagsWhy = "no git yet"; return @() }
    # Under "Continue", as in Test-TagSignature: git says why on stderr, which 5.1 drops at SilentlyContinue.
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $global:LASTEXITCODE = $null
    $out = @(& git ls-remote --tags --refs $Repo @Globs 2>&1 | ForEach-Object { "$_" })
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($rc -ne 0) {
        $why = @($out | Where-Object { $_ -notmatch 'refs/tags/' -and $_.Trim() }) | Select-Object -Last 1
        $script:TagsWhy = if ($why) { "$why".Trim() } else { "git ls-remote ended $rc and said nothing -- no network?" }
        return @()
    }
    return @($out | Where-Object { $_ -match 'refs/tags/' } | ForEach-Object { ($_ -split "/")[-1] })
}

# The method's version (T-37, #142) -- the mirror of pick_method_ref in install.sh: the name given with -SkillRef (a
# name that is not a release is said UNSIGNED), or the newest release tag; $null when none could be read, and the
# caller stops -- an empty ls-remote installed an unchecked `main`. A dry run changes nothing, so there an unreadable
# list is said and the run goes on (#142): it stopped a dry run on Windows without Git, blaming the network. The stop
# itself is the caller's: Stop-Installer's `return` ends the script only from its top level.
function Select-MethodRef {
    param([string]$Given)
    if ($Given) {
        if (-not (Test-ReleaseTag $Given)) { Warn "$Given is not a release: it is installed UNSIGNED, unchecked" }
        return $Given
    }
    # Release-shaped tags only (skill #108): a `v3.x` sorted above every release and installed unchecked.
    $tags = @(@(Read-ReleaseTags $SkillRepo @($SkillTagGlob)) | Where-Object { Test-ReleaseTag $_ } |
              Sort-Object { [version]($_ -replace '^v', '') })
    if ($tags.Count -gt 0) { return $tags[-1] }
    if (-not $script:TagsWhy) { $script:TagsWhy = "the remote lists no $SkillTagGlob release" }
    if ($DryRun) {
        Warn "would install the newest $SkillTagGlob release (not readable here: $($script:TagsWhy))"
        return $SkillTagGlob
    }
    return $null
}

Step "The tuning method"
if ($PluginRoot) {
    # The plugin's copy is the method: checked, not cloned, and every later step reads it where it is.
    $SkillHome = Join-Path $PluginRoot "skills\autosound-tuning"
    $SkillRef = "v$PluginVersion"
    Say "this plugin: $SkillRef at $(Pretty $PluginRoot)"
    if ($DryRun) {
        Say "would check it against its signed release: python3 upkeep.py verify-copy --root $(Pretty $PluginRoot)"
    } elseif (-not (Test-Path $Py3)) {
        Warn "stopped: python3 is needed to check this plugin copy against its signed release, and there is none"
        Stop-Installer 1; return
    } else {
        # verify-copy's 4 is a copy that could not be checked here -- no network, git failed -- and its 3 one that is not
        # as signed (#142): they shared 3 and one sentence, which sent a person offline to reinstall a good plugin.
        & $Py3 (Join-Path $SkillHome "scripts\upkeep.py") verify-copy --root $PluginRoot
        if ($LASTEXITCODE -eq 4) {
            Warn "stopped: this plugin copy could not be checked against its signed release here -- see above (no network?); nothing was installed; run this again when GitHub answers"
            Stop-Installer 1; return
        }
        if ($LASTEXITCODE -ne 0) {
            Warn "stopped: this plugin copy is not $SkillRef as its author signed it -- see above; nothing was installed"
            Stop-Installer 1; return
        }
    }
} else {
# The newest 3.x tag unless one is named, by name rather than "main": main is where development
# lands, and an installer should put you on a release unless you say otherwise. On EITHER channel:
# this is the copy Claude Code in a terminal loads, and the terminal runs releases (autosound-hub
# #145). A candidate goes into its own copy, below.
$SkillRef = Select-MethodRef $SkillRef
if (-not $SkillRef) {
    Warn "could not read the method's release tags ($($script:TagsWhy)) -- nothing was installed or changed for the method; run again when GitHub answers, or name a tag with -SkillRef"
    Stop-Installer 1; return
}
Say "version $SkillRef"
# The link's place, seen with Get-Item -Force, not Test-Path (T-38, #142): Test-Path says False for a dangling junction,
# which then read as missing -- the update said "made again" over a New-Item that fails. A link that is not ours,
# dangling or not, is left and warned about, as install.sh does.
$entry = Get-Item $SkillHome -Force -ErrorAction SilentlyContinue
$linkExists = [bool]$entry
$isOurs = $false
if ($entry) {
    $isLink = $entry.LinkType -in @("SymbolicLink", "Junction")
    if ($isLink -and $entry.Target -and (($entry.Target -join "") -like "$SkillSrc*")) { $isOurs = $true }
    # What is left as it was goes into the receipt's method_ref (#142): it named the tag picked, never put there.
    if ($isLink -and -not $isOurs) {
        $gone = if (Test-Path $SkillHome) { "" } else { ", which is not there" }
        Warn "$SkillHome points at $($entry.Target)$gone -- left exactly as it is."
        Warn "that is somebody's checkout, not this script's to replace."
        $MethodLeft = "left as it was: a link to $($entry.Target), not this installer's"
    } elseif (-not $isLink) {
        $kind = if ($entry.PSIsContainer) { "real directory" } else { "file" }
        Warn "$SkillHome is a $kind this script did not create -- left alone."
        Warn "move it aside and re-run if you want this script to manage it."
        $MethodLeft = "left as it was: a $kind this installer did not make"
    }
}
if ((-not $linkExists) -or $isOurs) {
    if (Test-Path (Join-Path $SkillSrc ".git")) {
        Say "already installed -- updating to $SkillRef"
        $updated = Sync-MethodCheckout $SkillSrc $SkillRef "the method"
        if ($script:SignatureRefused) {
            Warn "stopped: $SkillRef is not a signed release of the method -- see above; the installed one is untouched"
            Stop-Installer 1; return
        }
        if ($script:NotTheTag) {
            Warn "stopped: the method could not be put on $SkillRef -- see above; it is back where it was"
            Stop-Installer 1; return
        }
        if (-not $updated) {
            # R32: not fetched, or local changes not kept -- the copy is where it was, and that is a stop, as a failed
            # new copy.
            Warn "update failed -- see above"
            Stop-Installer 1; return
        }
        # T-38 (#142): a re-run repairs the junction. Removed -- by hand, by a tidy-up -- it left the method installed
        # and invisible to Claude Code, while every re-run said "updating". Only a missing one: a link that is not
        # ours, or a real folder, was left and warned about above, as for a new copy. install.sh's update branch.
        if (-not $linkExists) {
            if ($DryRun) {
                Say "would make the missing junction ~\.claude\skills\autosound-tuning again"
            } else {
                Say "the junction ~\.claude\skills\autosound-tuning was missing -- made again"
                New-Item -ItemType Junction -Path $SkillHome -Target (Join-Path $SkillSrc "skills\autosound-tuning") | Out-Null
            }
        }
    } else {
        Say "into ~\.claude\skills\autosound-tuning"
        if (-not $DryRun) { New-Item -ItemType Directory -Force -Path (Split-Path $SkillHome) | Out-Null }
        $cloned = Sync-MethodCheckout $SkillSrc $SkillRef "the method"
        if ($cloned -and -not $DryRun) {
            # What is here is ours (a junction into the copy, dangling or not) or nothing: anything else was left above.
            if ($entry) {
                if ($entry.LinkType) { [System.IO.Directory]::Delete($SkillHome) } else { Remove-Item $SkillHome -Force -Recurse }
            }
            # A JUNCTION, not a symlink: junctions work for directories without Developer Mode
            # or an elevated prompt, which symlinks on Windows still require (INSTALLER-TZ section 3).
            New-Item -ItemType Junction -Path $SkillHome -Target (Join-Path $SkillSrc "skills\autosound-tuning") | Out-Null
        } elseif ($script:SignatureRefused) {
            Warn "stopped: $SkillRef is not a signed release of the method -- see above"
            Stop-Installer 1; return
        } elseif (-not $cloned) {
            # A stop, as in install.sh: nothing below can use a method that is not here (T-44, #142).
            Warn "clone failed -- see above"
            Stop-Installer 1; return
        }
    }
}

# The beta channel's copy (autosound-hub #145): the newest release OR candidate, in a checkout of
# its own that no junction points at. Claude Code in a terminal never loads it; an app that asks
# for beta runs it by path and declares it in AUTOSOUND_SKILL_ROOT. A failure here is no stop -- the
# terminal's method above is already in place -- but the copy the channel was asked for is not this
# run's candidate, so it counts as missing (R38, #142): the run ends 3, not 0. install.sh's beta block.
if ($Channel -eq "beta") {
    $betaRef = $null
    $names = @(Read-ReleaseTags $SkillRepo @($SkillTagGlob, $SkillBetaGlob))
    if (-not $script:TagsWhy) {
        $betaRef = Select-NewestOnChannel $names
        if (-not $betaRef) { $script:TagsWhy = "the remote lists no release or candidate" }
    }
    if (-not $betaRef) {
        Warn "could not read the method's candidates ($($script:TagsWhy)) -- the beta channel's copy was left as it is"
        Add-Missing "the beta copy"
    } else {
        Say "beta channel: $betaRef in $(Pretty $SkillBetaSrc) -- only an app that asks for beta runs it"
        if (-not (Sync-MethodCheckout $SkillBetaSrc $betaRef "the beta channel's copy")) {
            Warn "the beta channel's copy is not on $betaRef -- see above; the terminal's method is not affected"
            Add-Missing "the beta copy"
        }
    }
}

}   # not -Plugin

# -- what the method's tools need --------------------------------------------------------------
Step "What the method's tools need (numpy, scipy, matplotlib)"
$reqs = Join-Path $SkillHome "requirements.txt"
if ($DryRun -and -not (Test-Path $reqs)) {
    Say "would run: python3 -m pip install --user -r requirements.txt  (into uv's Python 3.12)"
} elseif (-not (Test-Path $reqs)) {
    Warn "no requirements.txt beside the method -- skipping (nothing to install from)"
} elseif (-not (Test-Path $Py3)) {
    Warn "no python3 -- the method's tools cannot run at all until there is one"
} else {
    # Into the user site (%APPDATA%\Python\Python312\site-packages), not into uv's own folder: uv
    # treats its Pythons as its own and may replace them on upgrade; the user site survives that.
    # `--break-system-packages` is pip's name for "I know": uv marks its Pythons EXTERNALLY-MANAGED
    # (PEP 668) and pip refuses even --user without it (first Windows run, 2026-08-17). With the
    # flag and --user nothing under uv's tree is touched.
    Say "into $(Pretty $Py3)"
    # CHECKED by what it was supposed to produce. install.sh has warned on a failed pip since it
    # was written; this side did not, so a machine that could not reach PyPI finished the install
    # looking successful and only said so much later, as a selftest failing on `import numpy`
    # with nothing pointing back here (HUB-042).
    # `--upgrade` (skill #98): without it a machine kept the libraries it got first while CI tests the newest.
    $pipOk = Run { & $Py3 -m pip install --quiet --upgrade --user --break-system-packages --no-warn-script-location --disable-pip-version-check -r $reqs } "python3 -m pip install --upgrade --user -r requirements.txt"
    if (-not $DryRun) {
        $haveDeps = Test-Quiet { & $Py3 -c "import numpy, scipy" }
        if (-not $haveDeps) {
            Warn "numpy/scipy did not install -- the method's tools will fail on import."
            Warn "retry by hand:  `"$Py3`" -m pip install --user --break-system-packages -r `"$reqs`""
        } elseif (-not $pipOk) {
            # pip said no, the imports say yes: they were already there. Worth one line, because
            # "pip failed" with everything working is the kind of thing people re-run for hours.
            Say "  (pip reported an error, but numpy and scipy import fine -- already installed)"
        }
    }
}

# -- Phase 1's desk engine ----------------------------------------------------------------------
# Two ways to have one, and the method takes whichever is there: the prebuilt archive attached to
# the tag's own release (~30 MB, nothing else needed) or the .NET SDK, which builds the wrapper on
# first use. The method computes the file's name from its own engine pin and this platform, checks
# what arrives against the release's SHA256SUMS and refuses a file that does not match -- so this
# step names the tag and reads back what the method says it did. Same decision as install.sh.
Step "Phase 1's desk engine"
$EnginePy = Join-Path $SkillHome "rew_tool\resonalyze_engine.py"
$HaveDotnet = (Have dotnet) -or (Test-Path (Join-Path $HOME ".dotnet\dotnet.exe"))
# T-40 (#142): the SDK builds the wrapper from the method's own checkout -- `git submodule update` fetches the fork --
# and a plugin copy is none (no .git above it): there "auto" fetches the prebuilt engine, as where there is no SDK.
$MethodIsCheckout = -not ($PluginRoot -and -not (Test-Path (Join-Path $PluginRoot ".git")))
$EngineDid = "not reached"
if ($WantEngine -eq "0") {
    $EngineDid = "not fetched: -NoEngine"
    # A plugin copy is no checkout the SDK builds from (T-40): there only the fetch gives an engine (#142).
    if ($MethodIsCheckout) { Say "-NoEngine: not fetched. It builds from the .NET SDK on first use, or later with" }
    else { Say "-NoEngine: not fetched. A plugin copy cannot build one; Phase 1's desk step waits for it, or later with" }
    Say "  `"$Py3`" `"$EnginePy`" fetch-binary --tag $SkillRef"
} elseif ($WantEngine -eq "auto" -and $MethodIsCheckout -and $HaveDotnet -and -not $DryRun -and (Test-Path $Py3) -and (Test-Path $EnginePy)) {
    # The Arbiter, 2026-09-23: the engine is installed WITH the skill and checked -- built now, not on first use.
    Say "the .NET SDK is here -- building the engine from the method's own checkout now, then running it once"
    Say "(-Engine fetches the prebuilt one instead: no build, no SDK needed)"
    $global:LASTEXITCODE = 0
    $engineSaid = (& $Py3 $EnginePy check --build 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0) {
        $EngineDid = "built from the .NET SDK and checked: it runs"
        Say $engineSaid
    } else {
        $EngineDid = "built or run failed: $(($engineSaid -split "`n")[-1])"
        Warn "the engine did not build or run -- the method is installed and works; Phase 1's desk step waits for it:"
        Warn $engineSaid
    }
} elseif ($WantEngine -eq "auto" -and $MethodIsCheckout -and $HaveDotnet) {
    $EngineDid = "not built: the .NET SDK is here and builds it on first use"
    Say "the .NET SDK is here -- the engine builds from the method's own checkout on first use"
} elseif (-not (Test-Path $Py3)) {
    $EngineDid = "not fetched: no working python3"
    Warn "no python3 -- the engine cannot be fetched; the method's tools cannot run either (above)"
} elseif ($DryRun) {
    Say "would run: python3 $(Pretty $EnginePy) fetch-binary --tag $SkillRef"
} elseif (-not (Test-Path $EnginePy)) {
    $EngineDid = "not fetched: the method's checkout was not where this script expected it"
    Warn "no $(Pretty $EnginePy) -- the method's checkout is not where this script expects it;"
    Warn "the engine was not fetched, and Phase 1's desk step will ask for one when it is reached"
} else {
    if (-not $MethodIsCheckout -and $HaveDotnet) {
        Say "the .NET SDK is here, but a plugin copy is no checkout to build the engine from -- fetching it"
    }
    Say "~30 MB for $SkillRef, checked against the release's SHA256SUMS"
    $global:LASTEXITCODE = 0
    & $Py3 $EnginePy fetch-binary --tag $SkillRef
    $engineRc = $LASTEXITCODE
    # fetch-binary's answers (T-44, #142), written into the receipt in install.sh's words: 0 installed -- fetched now,
    # or already here from this tag, with nothing downloaded -- · 3 refused · 4 none for this machine · 5 no answer;
    # anything else, something went wrong, and the install carries on regardless.
    if ($engineRc -eq 0) {
        $EngineDid = "installed for $SkillRef and checked against SHA256SUMS"
        # ...and run once: a file that matches its checksum can still fail to start on this machine.
        $global:LASTEXITCODE = 0
        $engineSaid = (& $Py3 $EnginePy check 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0) {
            $EngineDid = "$EngineDid; it runs"
            Say $engineSaid
        } else {
            $EngineDid = "$EngineDid; but it does not run: $(($engineSaid -split "`n")[-1])"
            Warn "the engine was fetched but does not run here -- Phase 1's desk step waits for it:"
            Warn $engineSaid
            # The same tag's engine is not downloaded again while it is there (fetch-binary's 0): this is the way to.
            Warn "to fetch it again, remove $(Pretty $EngineHome) (the engines this script fetched) and run this again"
        }
    }
    if ($engineRc -eq 3) {
        $EngineDid = "refused: the archive for $SkillRef does not match its SHA256SUMS -- nothing installed"
        Warn "the engine's archive for $SkillRef does not match its SHA256SUMS -- refused, nothing installed;"
        Warn "the method is installed and works; Phase 1's desk step is the part that waits for an engine"
    } elseif ($engineRc -eq 4) {
        $EngineDid = "not fetched: $SkillRef carries no engine for this machine"
        if ($MethodIsCheckout) {
            Say "so the engine builds from the .NET SDK when there is one; nothing else is affected"
        } else {
            Say "and a plugin copy cannot build one -- Phase 1's desk step waits for an engine; nothing else is affected"
        }
    } elseif ($engineRc -eq 5) {
        $EngineDid = "not fetched: the release could not be reached -- run the installer again later"
        Warn "the release could not be reached -- run the installer again later; the method is installed and works,"
        Warn "and Phase 1's desk step is the part that waits for an engine"
    } elseif ($engineRc -ne 0) {
        $EngineDid = "not fetched: fetch-binary failed (code $engineRc)"
        Warn "the engine was not fetched (code $engineRc) -- the method is installed and works;"
        Warn "Phase 1's desk step is the part that waits for an engine"
    }
}

# -- the desktop app ---------------------------------------------------------------------------
$TccExe = $null
# Why the app's tag was not installed, when it was not (skill #101); said in its block, in the checks, and last.
$TccRefused = ""
if ($Mode -eq "tcc") {
    Step "Autosound TCC -- the desktop app"
    if (-not $Uv) {
        Warn "no uv, so no app. The method alone still works; re-run this later to add the app."
        # The app was asked for: not ready without it (#142), though the checks below no longer look for it.
        $Mode = "terminal"; Add-Missing "TCC"
    } elseif ((@(Get-Process -Name "autosound-tcc*" -ErrorAction SilentlyContinue).Count -gt 0) -and -not $DryRun) {
        # A RUNNING app holds its files on Windows (skill #62), so it is left as it is, with the reason -- and this is
        # asked FIRST (skill #64): the size line and the version used to print before it, and read as a download
        # that never started.
        Warn "Autosound TCC is running, so its files are in use. Close it and run this line again; the app was left as it is."
    } else {
        Say "the app and what it needs, about 700 MB -- a few minutes, no output until it is done..."
        # `--python` is not optional: without it uv picks whatever interpreter it finds, and the
        # failure reads as a broken package rather than a missing Python.
        # BY TAG, exactly as the method is above -- and exactly as install.sh does it. With no
        # ref, `git+URL` means HEAD of the default branch, so a fresh install handed somebody
        # unfinished work while the app's own update button offered the newest release. The two
        # ways of getting the app have to agree (SCR-054).
        $tccHow = ""
        if (-not $TccRef) {
            $globs = @($TccTagGlob)
            if ($Channel -eq "beta") { $globs = @($TccTagGlob, $TccBetaGlob); $tccHow = " (beta channel)" }
            $names = @(Read-ReleaseTags $TccRepo $globs)
            if (-not $script:TagsWhy) {
                if ($Channel -eq "beta") { $TccRef = Select-NewestOnChannel $names }
                else {
                    # Release-shaped tags only, as the method's (skill #108).
                    $tccTags = @($names | Where-Object { Test-ReleaseTag $_ } | Sort-Object { [version]($_ -replace '^v', '') })
                    if ($tccTags.Count -gt 0) { $TccRef = $tccTags[-1] }
                }
                if (-not $TccRef) { $script:TagsWhy = "the remote lists no release" }
            }
            # A dry run changes nothing, so an unreadable list stops nothing (#142): what a real run would install, as the
            # method's step says it -- it said "could not read the app's release tags (no git yet) -- run again".
            if (-not $TccRef -and $DryRun) {
                Warn "would install the newest app release (not readable here: $($script:TagsWhy))"
                $TccRef = $TccTagGlob
            }
        }
        if ($TccRef) {
            $TccSpec = "autosound-tcc[gui,claude] @ git+$TccRepo@$TccRef"
            Say "version $TccRef$tccHow"
            # Its signature, before uv sees it (skill #101). A tag that does not check out is not installed, and the
            # method's install goes on without it. A name that is not a release (-TccRef) is said UNSIGNED there.
            if (-not (Test-TccTag $TccRef)) { $TccRefused = "$TccRef could not be shown to be a signed release of TCC" }
        } else {
            # No tag could be read -- no network, no git: the app is not installed (T-37, #142). Its default branch was,
            # with nothing checked. The method goes on without it, and the checks below count the app as missing.
            $TccRefused = "could not read the app's release tags ($($script:TagsWhy)) -- run again when GitHub answers, or name a tag with -TccRef"
        }
        if (-not $TccRefused -and $script:TccSha -and -not (Test-TccTagStillAt $TccRef $script:TccSha)) {
            $TccRefused = "$TccRef changed after its signature was checked, or the server did not answer"
        }
        # skill #62: a launcher uv did not put there (TCC's own updater did) makes `uv tool install --upgrade` refuse
        # ("Executable already exists"), and on the Windows VM that refusal left the old app unable to start. So uv
        # is asked first: a tool it lists is upgraded, a launcher it does not own is replaced, and said. A running app
        # never gets this far (above).
        $tccForce = @()
        if (-not $TccRefused -and $HaveTcc -and -not ((& $Uv tool list 2>$null | Out-String) -match '(?m)^autosound-tcc ')) {
            $tccForce = @("--force")
            Say "the app's launcher here was not put there by uv (TCC's own updater did) -- replacing it"
        }
        if ($TccRefused) {
            Warn "the app is not installed: $TccRefused."
            Warn "The method is installed and works without it; the end of this run says so again."
        } elseif (Run { & $Uv tool install --quiet --python 3.12 --upgrade @tccForce $TccSpec } "uv tool install autosound-tcc[gui,claude]") {
            Sync-ProcessPath
            # The windowed launcher when the package has one (no console window behind the app),
            # the console one otherwise.
            foreach ($n in @("autosound-tcc-gui.exe", "autosound-tcc.exe")) {
                $p = Join-Path $LocalBin $n
                if (Test-Path $p) { $TccExe = $p; break }
            }
            if ($TccExe) { Say "OK   installed" } elseif (-not $DryRun) { Warn "autosound-tcc.exe did not appear in $(Pretty $LocalBin)" }
        } elseif (-not $DryRun) {
            Warn "the app did not install -- see above. The method alone still works; re-run this later."
        }
    }
}
if ($Mode -eq "tcc" -and ($TccExe -or $DryRun)) {
    if ($DryRun) {
        Say "would create `"Autosound TCC`" shortcuts on the Desktop and in the Start Menu"
    } else {
        # The app makes its OWN shortcuts: `autosound-tcc --install-desktop` writes both .lnk files
        # pointing at the installed launcher, with TCC's own icon (SCR-056). What this replaces
        # reached across the repository boundary to read `autosound_tcc.app.APP_ICO` by name out of
        # a private module -- rename it there and the icon would have disappeared here with no
        # error on either side. The half that owns the icon now places it, and this script reads an
        # exit code. Needs the app at v0.1.13 or newer, which the tag resolution above installs.
        # The exit code goes with the warning (hub #229): the next failure in the field names itself.
        $global:LASTEXITCODE = 0
        $out = (& $TccExe --install-desktop 2>&1 | Out-String).Trim()
        $rc = $LASTEXITCODE
        if ($rc -eq 0) {
            Say "OK   `"Autosound TCC`" on your Desktop and in the Start Menu"
            # See install.sh: this matches TCC's OUTPUT by phrase. The two words are load-bearing
            # on both sides by agreement, not by anything enforcing it.
            if ($out -match "no icon") {
                Say "     (with the generic icon -- TCC's own was not found in the installed package)"
            }
        } else {
            if ($out) { Write-Host $out }
            Warn "the shortcuts were not created (the app returned $rc). The command still works:  autosound-tcc"
        }
    }
}

# -- REW with its API on, one double-click away ------------------------------------------------
# Whether or not the API happens to be on right now: on Windows nothing keeps it on for the next
# launch, so the shortcut is worth having either way.
if ($RewExe -and $RewExe -ne "found") {
    Step "REW -- a shortcut that starts it with the API on"
    if ($DryRun) {
        Say "would create `"REW (API on)`" on the Desktop -> $RewExe -api"
    } else {
        try {
            $ws = New-Object -ComObject WScript.Shell
            $r = $ws.CreateShortcut($RewLnk)
            $r.TargetPath = $RewExe
            $r.Arguments = "-api"
            $r.WorkingDirectory = Split-Path $RewExe
            $r.IconLocation = "$RewExe,0"
            $r.Description = "REW with its API server started (port 4735)"
            $r.Save()
            Say "OK   `"REW (API on)`" on your Desktop -> roomeqwizard.exe -api"
        } catch { Warn "the REW shortcut was not created: $($_.Exception.Message)" }
    }
}

# -- the reviewer: Gemini, through Google's own CLI ---------------------------------------------
$AgyBin = $null
if ($WantReviewer) {
    Step "Gemini as the second AI -- Google's Antigravity CLI (agy)"
    $AgyBin = Find-Bin agy
    if ($AgyBin) {
        Say "OK   already here: $(Pretty $AgyBin)"
    } else {
        # Google's own installer: a signed exe into %LOCALAPPDATA%\agy\bin, unblocked by the
        # script itself, no admin. Its output is kept back until it is done: it logs its own setup
        # in a form that reads as errors ("ERROR: logging before google.Init ...").
        Say "about a minute..."
        if ($DryRun) {
            Say "would run: irm https://antigravity.google/cli/install.ps1 | iex"
        } else {
            Invoke-Upstream "https://antigravity.google/cli/install.ps1" "agy" -Capture | Out-Null
            $out = $script:UpstreamOutput
            Sync-ProcessPath
            $AgyBin = Find-Bin agy
            if ($AgyBin) {
                Add-ManifestEntry "agy"
                $v = ($out | Select-String -Pattern "Latest available version:\s*(\S+)" | Select-Object -First 1)
                $vs = if ($v) { " " + $v.Matches[0].Groups[1].Value } else { "" }
                Say "OK   agy$vs -> $(Pretty $AgyBin)"
            } else {
                $out | ForEach-Object { Write-Host $_ }
                Warn "the reviewer did not install. The tune works without it -- reviews go to the clipboard --"
                Warn "and it can be added later:  irm https://antigravity.google/cli/install.ps1 | iex"
            }
        }
    }
}

# -- omp: with the app, unless it was turned down ------------------------------------------------
if ($WantOmp) {
    Step "omp -- every non-Claude model for TCC's picker (metered)"
    if (Find-Bin omp) { Say "OK   already here" }
    elseif (Invoke-Upstream "https://omp.sh/install.ps1" "omp") {
        Sync-ProcessPath
        if (Find-Bin omp) { Add-ManifestEntry "omp" }
    } elseif (-not $DryRun) { Warn "omp did not install; TCC's picker offers Claude, and Gemini through agy, without it." }
}

# -- gh: only when asked -----------------------------------------------------------------------
$GhBin = $null
if ($WantGitHub -eq "1") {
    Step "gh -- GitHub's command, for the project backup"
    $GhBin = Find-Bin gh
    if ($GhBin) {
        Say "OK   already here: $(Pretty $GhBin)"
    } elseif ($DryRun) {
        Say "would download the newest gh release from github.com/cli/cli into $(Pretty $LocalBin)\gh.exe"
    } else {
        $g = Get-LatestAsset "cli/cli" "^gh_.*_windows_$Arch\.zip$"
        $got = $false
        if ($g) {
            New-Item -ItemType Directory -Force -Path $Scratch | Out-Null
            $tmpz = Join-Path $Scratch $g.Name
            $tmpd = Join-Path $Scratch "gh-extract"
            try {
                Invoke-WebRequest -Uri $g.Url -OutFile $tmpz -UseBasicParsing
                # CHECKED against the checksums the same release publishes -- the Unix half of this
                # installer has done that since HUB-031, and this half was still unpacking whatever
                # came back: a truncated transfer or a proxy answering with something else would be
                # copied onto PATH with the same confidence as the real thing. The checksum does not
                # prove who built it; it proves we got what that release says it has.
                # "Could not check" is NOT "checked": with no checksum line we do not install, and
                # the only cost is a backup feature nobody has set up yet.
                $ver = $g.Version -replace "^v", ""
                # The asset URL ends with the asset's own name, so the checksums file sits beside it.
                # Built by cutting that name off rather than by a regex: one less thing to escape.
                $sumUrl = $g.Url.Substring(0, $g.Url.Length - $g.Name.Length) + "gh_${ver}_checksums.txt"
                $tmps = Join-Path $Scratch "gh_checksums.txt"
                Invoke-WebRequest -Uri $sumUrl -OutFile $tmps -UseBasicParsing
                # `<sha256>  gh_<ver>_windows_<arch>.zip` -- take the line naming OUR asset, then its
                # first field. No line for it means we cannot check, which is not the same as checked.
                $sumPattern = "\s" + [regex]::Escape($g.Name) + "\s*$"
                $sumLine = Get-Content $tmps | Where-Object { $_ -match $sumPattern } | Select-Object -First 1
                $want = if ($sumLine) { ($sumLine -split "\s+" | Select-Object -First 1) } else { "" }
                # Get-FileHash returns UPPERCASE hex, the file lists lowercase -- and PowerShell's
                # -ne on strings is case-INSENSITIVE, which is why this compares correctly. Do not
                # "fix" it into -cne without lowering both sides first.
                $have = (Get-FileHash -Path $tmpz -Algorithm SHA256).Hash
                if (-not $want) {
                    Warn "gh: the release publishes no checksum line for $($g.Name) -- not installing it."
                } elseif ($want -ne $have) {
                    Warn "gh: the download does NOT match the checksum GitHub publishes for it -- not installing."
                    Warn "expected $want"
                    Warn "got      $have"
                } else {
                    Say "  checksum OK ($($have.Substring(0,12))...)"
                    if (Test-Path $tmpd) { Remove-Item $tmpd -Recurse -Force }
                    Expand-Archive -Path $tmpz -DestinationPath $tmpd -Force
                    $exe = Get-ChildItem -Path $tmpd -Filter "gh.exe" -Recurse | Select-Object -First 1
                    if ($exe) {
                        Copy-Item $exe.FullName (Join-Path $LocalBin "gh.exe") -Force
                        Unblock-File (Join-Path $LocalBin "gh.exe") -ErrorAction SilentlyContinue
                        $got = $true
                    }
                }
                if (Test-Path $tmps) { Remove-Item $tmps -Force -ErrorAction SilentlyContinue }
            } catch { Warn "$($_.Exception.Message)" }
            foreach ($t in @($tmpz, $tmpd)) { if (Test-Path $t) { Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue } }
        }
        if ($got) {
            Add-ManifestEntry "gh"
            $GhBin = Join-Path $LocalBin "gh.exe"
            Say "OK   gh $($g.Version) -> $(Pretty $GhBin)"
        } else {
            Warn "gh did not download. The backup can be set up later; see the last screen."
        }
    }
}

# -- the tools that were already here: updated on the person's word (skill #97, hub #219) ------------
# See install.sh: each tool is installed only when missing, so each kept its first version; the update is the skill's
# one path (upkeep.py tools), each tool the way it was installed. Only what was here before this run.
$hadTools = @()
if ($HaveClaude) { $hadTools += "claude" }
if ($HaveOmp)    { $hadTools += "omp" }
if ($HaveAgy)    { $hadTools += "agy" }
if ($HaveGh)     { $hadTools += "gh" }
if ($hadTools.Count -gt 0) {
    Step "The tools that were already here: $($hadTools -join ', ')"
    $upkeep = Join-Path $SkillHome "scripts\upkeep.py"
    $only = @(); foreach ($t in $hadTools) { $only += @("--only", $t) }
    if ($DryRun) { Say "would ask, then run: python3 $(Pretty $upkeep) tools $($only -join ' ')" }
    elseif (-not (Test-Path $Py3) -or -not (Test-Path $upkeep)) { Warn "no python3 or no upkeep.py beside the method -- the tools are left as they are" }
    elseif (Ask "Update them to their newest versions (each the way it was installed)?" "y") {
        $global:LASTEXITCODE = 0
        & $Py3 $upkeep tools @only
        if ($LASTEXITCODE -ne 0) { Warn "not every tool updated -- see above; each one that did not still works as it was" }
    } else { Say "left as they are; the next run of this script asks again" }
}

# =============================================================================================
# BLOCK 2 -- check, sign in, start. The rest of what a person does, in one place.
# =============================================================================================
Step "Checking"
# Each part that is not ready is said here and named with Add-Missing; the end, last, gives the verdict (#142).
if ($DryRun) { Say "(the machine as it stands -- nothing above was actually done)" }
if (Test-Path (Join-Path $SkillHome "rew_tool\contract.py")) {
    # The libraries, judged by importing them with the python3 the method runs on (#142): numpy and scipy are what its
    # tools run on, matplotlib only draws their plots.
    $numpyOk = $false; $scipyOk = $false; $mplOk = $false
    if (Test-Path $Py3) {
        $numpyOk = Test-Quiet { & $Py3 -c "import numpy" }
        $scipyOk = Test-Quiet { & $Py3 -c "import scipy" }
        $mplOk = Test-Quiet { & $Py3 -c "import matplotlib" }
    }
    if ($numpyOk -and $scipyOk) { Say "OK   the tuning method (3.x), and its tools load" }
    else { Say "OK   the tuning method (3.x)" }
    if (-not $numpyOk) {
        Warn "numpy is NOT importable by python3: crossover selection, the EQ gate, the DSP maths and"
        Warn "plot rendering will fail when the method reaches them."
        Add-Missing "numpy"
    }
    if (-not $scipyOk) {
        Warn "scipy is NOT importable by python3: crossover design, the EQ gate and the EQ proposals"
        Warn "will fail when the method reaches them."
        Add-Missing "scipy"
    }
    if (-not $mplOk) { Warn "matplotlib is NOT importable by python3: the method's plots will not be drawn; the rest runs." }
    if (Test-Path $Py3) {
        $NewPy = Get-NewWindowCommand "python3"
        if ($NewPy -and ($NewPy -ieq $Py3)) { Say "OK   python3 in a new window is $(Pretty $Py3)" }
        else {
            $was = if ($NewPy) { $NewPy } else { "not found" }
            Warn "python3 in a NEW window is $was, not $(Pretty $Py3) -- the method's tools will not run there."
            Warn "Run this installer again, or switch python3 off in Settings > Apps > Advanced app settings > App execution aliases."
            Add-Missing "python3 in a new window"
        }
    }
} elseif (Test-Path (Join-Path $SkillHome "rew_tool\rew_api.py")) {
    Warn "the skill at $SkillHome is the 2.x line -- TCC cannot drive it"; Add-Missing "the method (2.x line)"
} elseif (-not $DryRun) {
    Warn "no tuning method at $SkillHome"; Add-Missing "the method"
}
if ($Channel -eq "beta" -and -not $DryRun) {
    if (-not (Test-Path (Join-Path $SkillBetaSrc "skills\autosound-tuning\rew_tool\contract.py"))) {
        Warn "no beta channel copy at $(Pretty $SkillBetaSrc) -- an app asking for beta has nothing to run"; Add-Missing "the beta copy"
    } elseif ($script:Missing -notcontains "the beta copy") {   # not on this run's candidate: the beta block said so
        $betaAt = (& git -C $SkillBetaSrc describe --tags --always 2>$null)
        $termAt = if (Test-Path (Join-Path $SkillSrc ".git")) { (& git -C $SkillSrc describe --tags --always 2>$null) } else { "?" }
        Say "OK   the beta channel's copy, $betaAt -- for the app; the terminal stays on $termAt"
    }
}
if ($Mode -eq "tcc" -and -not $DryRun) {
    if ($TccRefused) {
        # Refused or unreadable over an app from before: install.sh's line for it, the one below for a failed upgrade.
        if ($HaveTcc) { Warn "Autosound TCC was here before and was not upgraded this time: $TccRefused -- it is left as it was" }
        else { Warn "Autosound TCC was not installed: $TccRefused" }
        Add-Missing "TCC"
    }
    elseif ($TccExe -and (Test-Path $DesktopLnk)) { Say "OK   Autosound TCC -- on your Desktop and in the Start Menu" }
    elseif ($TccExe) { Say "OK   Autosound TCC -- the command:  autosound-tcc" }
    elseif ($HaveTcc) { Warn "Autosound TCC was here before and was not upgraded this time (above) -- it is left as it was"; Add-Missing "TCC" }
    else { Warn "Autosound TCC is not installed"; Add-Missing "TCC" }
}
$ClaudeBin = Find-Bin claude
if ($ClaudeBin) { Say "OK   Claude Code" }
elseif (-not $DryRun) { Warn "Claude Code is not installed; nothing can run a session without it"; Add-Missing "Claude Code" }
if ($WantReviewer -and -not $DryRun) {
    $AgyBin = Find-Bin agy
    if ($AgyBin) { Say "OK   Gemini reviewer (agy) -- installed; sign in below" }
    else { Say "--   no Gemini reviewer; reviews fall back to the clipboard, which works" }
}
if ($WantGitHub -eq "1" -and -not $DryRun) {
    $GhBin = Find-Bin gh
    if ($GhBin) { Say "OK   gh -- for the project backup" } else { Say "--   gh did not install; see the last screen" }
}
if ($RewApi)     { Say "OK   REW's API is on" }
elseif ($RewApp) { Say "--   REW's API is off -- switching it on is the first Start step" }
else             { Say "--   REW not found -- installing it is the first Start step" }

# -- sign in -----------------------------------------------------------------------------------
$AgySkipped = $false
$GhSkipped = $false
$ReviewerIn = [bool]$AgyBin -or ($DryRun -and $WantReviewer)
$GhIn = [bool]$GhBin -or ($DryRun -and $WantGitHub -eq "1")
if ($DryRun) {
    Step "Sign in -- the part that is yours"
    Say "(a real run does this here, in order, each step explained before it runs:)"
    Say "1. Claude -- required: the browser opens, you sign in and click Authorize"
    if ($ReviewerIn) { Say "2. Gemini reviewer -- optional: Enter runs agy's own sign-in, s skips it" }
    if ($GhIn)       { Say "3. GitHub -- optional: Enter runs gh auth login --web, s skips it" }
} else {
    Step "Sign in -- the part that is yours"
    $interactive = -not $Yes
    $n = 1
    if ($ClaudeBin) {
        $signed = Get-ClaudeStatus
        if ($signed) {
            Say "$n. Claude: OK   signed in as $signed"
        } elseif ($interactive) {
            Say "$n. Claude -- required. Your browser will open: sign in to your Claude account (a Pro or"
            Say "   Max subscription is what runs the method) and click Authorize, then come back here."
            if (Offer "Enter opens the browser / s = later") {
                & $ClaudeBin auth login
                $signed = Get-ClaudeStatus
                if ($signed) { Say "   OK   signed in as $signed" } else { Say "   --   not signed in yet. Later, in a terminal:  claude auth login" }
            } else { Say "   Later, in a terminal:  claude auth login" }
        } else {
            Say "$n. Claude -- required. In a terminal:  claude auth login"
            Say "   (your browser opens; sign in to your Claude account -- Pro or Max -- and click Authorize)"
        }
        $n++
    }
    $agySeen = Get-AgyStatus
    if ($AgyBin -and $agySeen) {
        # Already set up -- the same courtesy Claude and GitHub get either side of this step. It
        # used to offer the sign-in on every run, so a re-run to fix something else walked the
        # person back through Google's setup screens (user, 2026-08-19, on macOS). Two sentences,
        # because an account name is a sign-in and the other signals are "configured, and here is
        # how to check" -- claiming a sign-in this script cannot see would be worse.
        if ($agySeen -like "*@*") { Say "$n. Gemini reviewer: OK   signed in as $agySeen" }
        else { Say "$n. Gemini reviewer: OK   already set up ($agySeen). To check it:  agy" }
        $n++
    }
    elseif ($AgyBin) {
        if ($env:GEMINI_API_KEY -or $env:GOOGLE_API_KEY) {
            # hub #187: a key in the environment is not the reviewer's sign-in, and it sends every
            # review to the API, where agy's model names (...-high) do not exist.
            Say "$n. A Gemini API key is set in your environment. agy does not use it; it signs in with"
            Say "   your Google account (below). A session TCC starts may not see it, and every program"
            Say "   can read it there. To keep it for the reviewer, move it into the Windows store (asks first):"
            Say "      python3 `"$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py`" key move-shell"
        }
        $adcDone = $false
        $adc = Get-AdcFile
        if ((Test-Path $adc) -and ((Get-Item $adc).Length -gt 0)) {
            # hub #234: offered, never assumed -- ADC may bill a Cloud project the person keeps for other work.
            Say "$n. Gemini reviewer through Google Cloud's ADC: this machine has its credentials ($(Pretty $adc))."
            Say "   agy uses them once AGY_ADC_AUTH=true is in $(Pretty (Get-CriticEnvPath)) -- the file every run reads, the app's too."
            if ($interactive -and (Offer "Enter = write that line / s = no, the Google account sign-in below")) {
                if (Set-CriticEnvAdc) { $adcDone = $true; Say "   OK   written -- the reviewer signs in through ADC" }
                else { Warn "could not write $(Pretty (Get-CriticEnvPath)) -- the Google account sign-in below still works" }
            } else { Say "   (later: add the line AGY_ADC_AUTH=true to that file)" }
        }
        if (-not $adcDone) {
        Say "$n. Gemini reviewer -- optional, once. Have a Google account ready. What happens:"
        Say "     agy opens; press Enter through its two setup screens; your browser asks you to sign"
        Say "     in with Google. If it then asks for a Project ID, copy it from"
        Say "     aistudio.google.com/app/apikey (the ID, not the name). When it says you're in, type /quit"
        if ($interactive -and (Offer "Enter = sign in now / s = later")) {
            & $AgyBin
            Say "   Done. If it ever answers with `"Agent Platform API has not been used`", the message"
            Say "   carries a link -- open it, press Enable, wait a minute."
        } else { $AgySkipped = $true; Say "   Later, in a terminal:  agy" }
        Say "   Or Google Cloud's free trial through ADC, no Google AI subscription: the FAQ, `"agy through Google Cloud's ADC`"."
        }   # not ADC
        $n++
    }
    if ($GhBin) {
        # The Arbiter, 2026-09-23 (hub #199): GitHub wanted means GitHub set up -- signed in AND git pushing
        # through it. Each project's first commit and its private backup are the method's (rew_tool\project_repo.py).
        if (Test-Quiet { & $GhBin auth status }) {
            Test-Quiet { & $GhBin auth setup-git } | Out-Null
            Say "$n. GitHub: OK   signed in, and git pushes through it"
        }
        else {
            Say "$n. GitHub -- optional. Your browser opens with a one-time code: sign in, paste it, and answer"
            Say "   Yes when gh asks to authenticate Git with your GitHub credentials."
            if ($interactive -and (Offer "Enter = sign in now / s = later")) {
                & $GhBin auth login --hostname github.com --git-protocol https --web
                if (Test-Quiet { & $GhBin auth status }) { Test-Quiet { & $GhBin auth setup-git } | Out-Null }
            } else { $GhSkipped = $true; Say "   Later, in a terminal:  gh auth login --web" }
        }
        $n++
    }
}

# -- start -------------------------------------------------------------------------------------
Step "Start"
$n = 1
if (-not $RewApi) {
    if ($RewApp -and (Test-Path $RewLnk)) {
        Say "$n. In REW: Preferences -> API: tick `"Start the API when REW starts`" and press `"Start server`"."
        Say "   The panel then reads `"API server is running on port 4735`" -- no restart needed."
        Say "   Or start REW from the `"REW (API on)`" shortcut on your Desktop, which does the same in one"
        Say "   click. Nothing measures without it."
        Say "   No `"API`" tab in REW's preferences at all? That is the RELEASE build (V5.31.3), which has"
        Say "   no API -- and it is what a web search gives you. Get a beta: roomeqwizard.com/beta.html"
        Say "   (downloads at AV NIRVANA, the REW forum), then run this installer once more."
    } elseif ($RewApp) {
        Say "$n. In REW: Preferences -> API: tick `"Start the API when REW starts`" and press `"Start server`","
        Say "   or run  `"$RewExe`" -api  -- REW's own switch. Nothing measures without it."
        Say "   No `"API`" tab in REW's preferences at all? That is the RELEASE build (V5.31.3), which has"
        Say "   no API. Get a beta: roomeqwizard.com/beta.html (downloads at AV NIRVANA, the REW forum)."
    } else {
        Say "$n. Install REW -- it must be a BETA build: the release version (V5.31.3, July 2024) has no"
        Say "   API at all, and that is the one a web search hands you. roomeqwizard.com/beta.html,"
        Say "   downloads at AV NIRVANA, the REW forum. Then run this installer once more: it puts a"
        Say "   `"REW (API on)`" shortcut on your Desktop. (Or in REW: Preferences -> API -> `"Start server`","
        Say "   every time.) Nothing measures without it."
    }
    $n++
}
if ($Mode -eq "tcc") {
    Say "$n. Double-click `"Autosound TCC`" on your Desktop."
    Say "   Browse... to a folder for the car -- a new, empty one is right; everything about that car"
    Say "   will live in it (for instance Autosound\my-car in your user folder)."
    Say "   AI main: the Claude Opus line (SDK) / AI critic: the Gemini Pro (High) line. Open."
    # skill #71: agy refuses Pro in some regions; the run must not end naming a model the person cannot get.
    Say "   (If agy says Pro is not supported where you are, pick a Gemini Flash (High) line instead.)"
    $n++
    Say "$n. In the panel on the right, say what you want, in any language:"
    Say "   `"let's tune this car from scratch`"."
} else {
    Say "$n. Open a NEW PowerShell window -- this one cannot see what was just installed -- and run:"
    Say "        mkdir ~\Autosound\my-car; cd ~\Autosound\my-car"
    Say "        claude"
    $n++
    Say "$n. Say what you want, in any language: `"tune a new car from scratch`"."
}

# -- when you have time ------------------------------------------------------------------------
Step "When you have time"
if ($ReviewerIn) {
    Say "* Check the reviewer really answers -- finding the command is not the same as it working:"
    Say "      python3 `"$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py`" doctor"
    if ($AgySkipped) { Say "  (it needs the sign-in above first:  agy)" }
} elseif ($WantReviewer) {
    Say "* A second AI as reviewer is where most of the value is. Add it later:"
    Say "      irm https://antigravity.google/cli/install.ps1 | iex"
    Say "  then sign in once with:  agy"
} else {
    Say "* A second AI as reviewer is where most of the value is (you passed -NoReviewer):"
    Say "      irm https://antigravity.google/cli/install.ps1 | iex"
}
if ($GhIn) {
    if ($GhSkipped) { Say "* GitHub backup -- sign in once:  gh auth login --web" }
    # A how-to, not a promise: nothing in the method scripts this step yet (SCR-049).
    Say "* Back a car up once its folder exists -- say to the AI: `"back this project up to a private"
    Say "  GitHub repository`". It knows what stays out (the sweeps) and uses gh for the rest."
} elseif ($WantGitHub -eq "0") {
    Say "* Backing a car's record up to a private GitHub repository is free insurance against a"
    Say "  dead disk. Re-run this with -GitHub when you want it."
}
if ($RewApi -and $RewExe -and $RewExe -ne "found") {
    Say "* Next time, start REW from the `"REW (API on)`" shortcut on your Desktop: on Windows the API"
    Say "  does not stay on by itself between launches, and that shortcut starts REW with it on."
}
Say "* Update everything: run this same install line again."

Step "Where this lives"
Say "the tuning method   $SkillRepoUrl"
Say "the desktop app     $TccRepo"
Say "something wrong, or an idea -- open an issue in whichever of the two it belongs to."

# -- the end (#142): install.sh's finish, in this file's terms ----------------------------------
# Last on screen, the verdict and what each missing part needs -- the app's refusal among them, which does not stop
# the run (skill #101) -- rather than left in a block that has scrolled away; then the receipt, the plugin's note and
# the code: 0 "Installed.", or 3 "Installed, NOT ready: <names>". A dry run did nothing: it says so, and ends 0.
$ok = $script:Missing.Count -eq 0
Write-Host ""
if ($DryRun) { Write-Host "Nothing was installed -- this was a dry run." }
elseif ($ok) { Write-Host "Installed." }
else {
    Write-Host "Installed, NOT ready: $($script:Missing -join ', ')"
    foreach ($part in $script:Missing) {
        switch ($part) {
            { $_ -in @("numpy", "scipy") } {
                Warn "$part is not importable by $(Pretty $Py3) -- the libraries' step above says why; install it for that python3, then run this again"
            }
            "python3 in a new window" {
                Warn "python3 in a new window is not $(Pretty $Py3) -- run this again, or switch python3 off in Settings > Apps > Advanced app settings > App execution aliases"
            }
            "the method" {
                # A link that is not this script's, to nothing (#142): what to remove -- run again, it is left again.
                $e = Get-Item $SkillHome -Force -ErrorAction SilentlyContinue
                if ($e -and $e.LinkType -and -not (Test-Path $SkillHome)) {
                    Warn "$(Pretty $SkillHome) is a link to $($e.Target), which is not there, and this installer leaves a link it did not make -- remove that link, and the next run of this installer makes its own"
                } else {
                    Warn "no tuning method at $(Pretty $SkillHome) -- the method's step above says why; run this again"
                }
            }
            "the method (2.x line)" {
                Warn "$(Pretty $SkillHome) is the 2.x line, which TCC cannot drive -- move it aside, then run this again"
            }
            "the beta copy" {
                Warn "no beta channel copy on this run's candidate at $(Pretty $SkillBetaSrc) -- an app asking for beta runs an older one, or nothing; the beta block above says why; run this again"
            }
            "TCC" {
                # One reason -- the refusal's, or the block's -- and "not upgraded" when an app from before stays (#142).
                $why = if ($TccRefused) { $TccRefused } else { "the app's block above says why" }
                if ($HaveTcc -and -not $TccExe) { Warn "the app was not upgraded -- the one from before is left as it was: $why; the method is installed and works without it" }
                else { Warn "the app was not installed: $why; the method is installed and works without it" }
            }
            "Claude Code" {
                Warn "Claude Code is not installed; nothing can run a session without it -- when the network is back:  irm https://claude.ai/install.ps1 | iex"
            }
            default { Warn $part }
        }
    }
    if ($PluginRoot) { Warn "the plugin's set-up note comes back at the next session until an install is ready" }
}
if (-not $DryRun) {
    $status = if ($ok) { "ready" } else { "not ready" }
    Write-Receipt $status
}
# -Plugin: this version is verified and set up -- the plugin's SessionStart hook stops offering the setup (#120). Only
# on a ready install: on any other the note keeps coming back, and the setup is offered again.
if ($ok -and $PluginRoot -and -not $DryRun -and (Test-Path $Py3)) {
    & $Py3 (Join-Path $SkillHome "scripts\upkeep.py") plugin-ready --root $PluginRoot
    if ($LASTEXITCODE -ne 0) { Warn "could not write down that v$PluginVersion is set up -- the next session will offer the setup again" }
}
if (-not $ok -and -not $DryRun) {
    Stop-Installer 3; return
}
# The normal end. Run as a file the process ending closes a -Log transcript; run as the one-liner
# the session goes on, so the transcript is stopped here rather than left recording it.
if ($AutosoundTranscriptOn) { try { Stop-Transcript | Out-Null } catch { $null = $_ } }
