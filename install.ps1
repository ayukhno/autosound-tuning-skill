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
#   .\install.ps1 -GitHub             with the GitHub CLI (default: asks); -NoGitHub: without
#   .\install.ps1 -NoOmp              without omp, which offers TCC every non-Claude model
#   .\install.ps1 -DryRun             say what it would do, change nothing
#   .\install.ps1 -Yes                yes to every question; sign-ins are printed, not run
#   .\install.ps1 -SkillRef v3.0.33   a specific skill version (default: the newest 3.x tag)
#   .\install.ps1 -TccRef v0.1.22     the app version released WITH that one -- quote the two
#                                     together or not at all; a mixed pair is untested
#   .\install.ps1 -Uninstall          remove what this script installed -- NEVER your projects
#   .\install.ps1 -Uninstall -All     also uv, Claude Code and ~\.claude, agy/gh/omp when this
#                                     script installed them, and every --user pip package. Asks first.

[CmdletBinding()]
param(
    [switch]$Terminal,
    [switch]$Tcc,
    [switch]$NoReviewer,
    [switch]$WithOmp,   # kept: the way to ask for omp before it came with the app
    [switch]$NoOmp,
    [switch]$GitHub,
    [switch]$NoGitHub,
    [switch]$DryRun,
    [switch]$Yes,
    [string]$SkillRef = "",
    [string]$TccRef = "",
    [switch]$Uninstall,
    [switch]$All,
    [switch]$Help,
    [string]$Log = ""
)
# -Log <file>: a full transcript, for reading a run that happened on somebody else's machine. A
# `| Tee-Object` on the outside sees none of this script's own lines (they go to the host, not
# the pipeline), which is how the first Windows log arrived holding two errors and nothing else.
if ($Log) { try { Start-Transcript -Path $Log -Force | Out-Null } catch { Write-Host "  (no transcript: $($_.Exception.Message))" } }

# Native commands (git, winget, uv, claude...) write ordinary progress to stderr, and under
# `$ErrorActionPreference = "Stop"` Windows PowerShell 5.1 turns that into a terminating error the
# moment it is redirected. So: Continue, and every step checks its own result instead.
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
# The app's supported line -- `v*`, not `v3.*`: the app versions independently of the method.
$TccTagGlob   = "v*"
$TccRepo      = "https://github.com/ayukhno/autosound-tcc"
$SkillHome    = Join-Path $HOME ".claude\skills\autosound-tuning"
# The checkout lives beside the skill and the skill points at it (a junction) -- see install.sh
# for why moving the subdirectory out instead leaves something no later run can update.
$SkillSrc     = Join-Path $HOME ".claude\skills\.autosound-tuning-src"
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
  install.ps1 -GitHub             with the GitHub CLI (default: asks); -NoGitHub: without
  install.ps1 -NoOmp              without omp, which offers TCC every non-Claude model (metered)
  install.ps1 -DryRun             say what it would do, change nothing
  install.ps1 -Yes                yes to every question; sign-ins are printed, not run
  install.ps1 -SkillRef v3.0.33   a specific skill version (default: the newest 3.x tag)
  install.ps1 -TccRef v0.1.22     the app version released WITH that one -- quote the two
                                  together or not at all; a mixed pair is untested
  install.ps1 -Uninstall          remove what this script installed -- NEVER your projects
  install.ps1 -Uninstall -All     also uv, Claude Code and ~\.claude, agy/gh/omp when this
                                  script installed them, and every --user pip package. Asks first.

Through the one-liner, options go on the scriptblock:
  & ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1))) -Terminal
"@ | Write-Host
    exit 0
}

$Mode         = if ($Terminal -and -not $Tcc) { "terminal" } else { "tcc" }   # -Tcc is the default, kept for old command lines
$WantReviewer = -not $NoReviewer
# omp comes WITH the app now (2026-08-19, same change as install.sh): it is what fills TCC's
# model picker with everything that is not Claude, so it belongs with the app and means
# nothing without it. -NoOmp leaves it out; -Terminal never brings it.
$WantOmp      = if ($NoOmp) { $false } elseif ($WithOmp) { $true } else { $Mode -eq "tcc" }
$WantGitHub   = if ($GitHub) { "1" } elseif ($NoGitHub) { "0" } else { "ask" }

# -- small tools ------------------------------------------------------------------------------
function Say  { param($m) Write-Host "  $m" }
function Step { param($m) Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Warn { param($m) Write-Host "  ! $m" -ForegroundColor Yellow }
function Have { param($n) [bool](Get-Command $n -ErrorAction SilentlyContinue) }
# Paths on screen with the profile as `~`: a person reads "~\.zshrc" as a place; the same path
# spelled out from C:\Users reads as a warning.
function Pretty { param($p) if ($p -and $p.StartsWith($HOME)) { "~" + $p.Substring($HOME.Length) } else { $p } }
function Run {
    param([scriptblock]$Block, [string]$Label)
    if ($DryRun) { Say "would run: $Label"; return $true }
    $global:LASTEXITCODE = 0
    & $Block
    return ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE)
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
    $global:LASTEXITCODE = 0
    try { & $Block 2>&1 | Out-Null } catch { $null = $_ }
    $ErrorActionPreference = $prev
    return ($LASTEXITCODE -eq 0)
}
# The upstream one-liners (`irm <url> | iex`) run in a CHILD PowerShell, never in this one: two of
# them end with `exit` on failure and one with `throw`, and inside our process an `exit` in their
# code ends this script mid-way with no check and no message. A child process turns that into an
# exit code we can read. Windows PowerShell 5.1 is always there, and every one of them supports it.
function Invoke-Upstream {
    param([string]$Url, [string]$Label, [switch]$Capture)
    if ($DryRun) { Say "would run: irm $Url | iex   ($Label)"; return $true }
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
    #   5. An API key in the environment: a way the reviewer runs just as well as a login.
    # Only the ACCOUNT is ever read -- no credential file is opened for its contents.
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
    if ($env:GEMINI_API_KEY -or $env:GOOGLE_API_KEY) { return "an API key in your environment" }
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
    exit 0
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
$RewExe     = Get-RewExe
$RewApp     = [bool]$RewExe
$RewApi     = Test-RewApi

Say "Already on this machine:"
if ($HaveGit)    { Say "  OK   Git for Windows (git, Git Bash)" } else { Say "  --   Git for Windows (git, Git Bash)   will install" }
if ($HaveClaude) { Say "  OK   Claude Code" }                       else { Say "  --   Claude Code                        will install" }
if ($HaveUv)     { Say "  OK   uv (installs Python)" }              else { Say "  --   uv, and a Python 3.12             will install" }
if ($Mode -eq "tcc") { Say "  --   Autosound TCC, the desktop app     will install" }
if ($WantReviewer) {
    if ($HaveAgy) { Say "  OK   Gemini reviewer (agy)" } else { Say "  --   Gemini reviewer (agy)              will install" }
}
if ($RewApi)      { Say "  OK   REW, and its API is on" }
elseif ($RewApp)  { Say "  OK   REW -- its API is off; a shortcut that starts REW with it on goes on your Desktop" }
else              { Say "  --   REW not found -- install a BETA from roomeqwizard.com/beta.html (the release has no API)" }

# One optional question, here because the answer changes the download list below (SCR-049) -- and
# only when there is something to decide. `gh` already on the machine means the answer was given on
# an earlier run, and asking again is a question with no download behind it (user, 2026-08-19).
# Nothing outward-facing rides on it: the installer never pushes a project anywhere.
if ($WantGitHub -eq "ask" -and $HaveGh) { $WantGitHub = "1" }
if ($WantGitHub -eq "ask") {
    Write-Host ""
    Say "Optional: back each car's record up to a free, private GitHub repository -- the ledger of"
    Say "every setting, the journal, the DSP config backups. Weeks of decisions, a few kilobytes,"
    Say "and the one thing a dead disk does not give back. Needs a free GitHub account; installs"
    Say "GitHub's gh command. The measurements themselves stay on your disk either way."
    if (Ask "Back projects up to GitHub?" "n") { $WantGitHub = "1" } else { $WantGitHub = "0" }
}

# ONE screen naming everything that will be downloaded, before any of it happens.
Write-Host ""
Say "This installs:"
$mb = 100
if (-not $HaveGit)    { Say "  * Git for Windows -- git, and Git Bash for Claude Code    git-scm.com; one permission dialog"; $mb += 60 }
if (-not $HaveClaude) { Say "  * Claude Code -- the AI that runs the method              claude.ai"; $mb += 200 }
if (-not $HaveUv)     { Say "  * uv, and a Python 3.12 of its own                        astral.sh"; $mb += 60 }
elseif (-not $HavePy3){ Say "  * a Python 3.12, through uv                               astral.sh"; $mb += 40 }
Say "  * the tuning method -- its references and tools           github.com/ayukhno/autosound-tuning-skill"
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
if ($WantOmp)          { $opts += "-NoOmp" }
if ($opts.Count -gt 0) { Say "To leave something out, answer n and re-run with an option: $($opts -join ', '). -Help lists them all." }
if (-not $DryRun) {
    if (-not (Ask "Go ahead?" "n")) {
        Write-Host ""
        Say "Nothing installed. Re-run when you want to."
        exit 0
    }
}
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
                    Start-Process -FilePath $tmp -ArgumentList "/VERYSILENT", "/NORESTART" -Wait
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
        exit 1
    }
}

# -- Claude Code -------------------------------------------------------------------------------
Step "Claude Code"
$ClaudeBin = Find-Bin claude
if ($ClaudeBin) {
    Say "OK   $(& $ClaudeBin --version 2>$null)"
} else {
    Say "the official installer, claude.ai/install.ps1:"
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
    Say "the official installer, astral.sh/uv/install.ps1:"
    if (Invoke-Upstream "https://astral.sh/uv/install.ps1" "uv") {
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

# -- the tuning method -------------------------------------------------------------------------
Step "The tuning method"
if (-not $SkillRef) {
    # The newest 3.x tag, by name rather than "main": main is where development lands, and an
    # installer should put you on a release unless you say otherwise.
    $tags = @()
    if (Have git) {
        $tags = @((& git ls-remote --tags --refs $SkillRepo $SkillTagGlob 2>$null) |
                  ForEach-Object { ($_ -split "/")[-1] } |
                  Sort-Object { [version]($_ -replace '^v', '') })
    }
    if ($tags.Count -gt 0) { $SkillRef = $tags[-1] } else { $SkillRef = "main" }
}
Say "version $SkillRef"
$linkExists = Test-Path $SkillHome
$isOurs = $false
if ($linkExists) {
    $item = Get-Item $SkillHome -Force
    $isLink = $item.LinkType -in @("SymbolicLink", "Junction")
    if ($isLink -and $item.Target -and (($item.Target -join "") -like "$SkillSrc*")) { $isOurs = $true }
    if ($isLink -and -not $isOurs) {
        Warn "$SkillHome points at $($item.Target) -- left exactly as it is."
        Warn "that is somebody's checkout, not this script's to replace."
    } elseif (-not $isLink) {
        Warn "$SkillHome is a real directory this script did not create -- left alone."
        Warn "move it aside and re-run if you want this script to manage it."
    }
}
if ((-not $linkExists) -or $isOurs) {
    if (Test-Path (Join-Path $SkillSrc ".git")) {
        Say "already installed -- updating to $SkillRef"
        # Fetch the ref BY NAME: the clone was made with --depth 1 --branch <tag>, so it holds
        # that tag and nothing else; FETCH_HEAD is whatever was just fetched.
        Run { & git -C $SkillSrc fetch --quiet --depth 1 origin $SkillRef } "git fetch $SkillRef" | Out-Null
        Run { & git -c advice.detachedHead=false -C $SkillSrc checkout --quiet FETCH_HEAD } "git checkout FETCH_HEAD" | Out-Null
    } else {
        Say "into ~\.claude\skills\autosound-tuning"
        if (-not $DryRun) {
            New-Item -ItemType Directory -Force -Path (Split-Path $SkillHome) | Out-Null
            # A shallow clone of an ANNOTATED tag makes git print "warning: refs/tags/vX.Y.Z <sha>
            # is not a commit!" -- it is complaining that the tag OBJECT is not a commit, which is
            # what an annotated tag is; HEAD lands on exactly what the tag peels to. Under Windows
            # PowerShell that one line arrived as a red NativeCommandError block (2026-08-17).
            # Everything else git says survives.
            $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
            $gitOut = @(& git -c advice.detachedHead=false clone --quiet --branch $SkillRef --depth 1 $SkillRepo $SkillSrc 2>&1)
            $ErrorActionPreference = $prev
            $gitOut | ForEach-Object { "$_" } | Where-Object { $_ -and ($_ -notmatch 'is not a commit!') } | ForEach-Object { Write-Host "  $_" }
            if (Test-Path (Join-Path $SkillSrc "skills\autosound-tuning")) {
                if (Test-Path $SkillHome) {
                    $old = Get-Item $SkillHome -Force
                    if ($old.LinkType) { [System.IO.Directory]::Delete($SkillHome) } else { Remove-Item $SkillHome -Force -Recurse }
                }
                # A JUNCTION, not a symlink: junctions work for directories without Developer Mode
                # or an elevated prompt, which symlinks on Windows still require (INSTALLER-TZ section 3).
                New-Item -ItemType Junction -Path $SkillHome -Target (Join-Path $SkillSrc "skills\autosound-tuning") | Out-Null
            } else {
                Warn "clone failed -- is the network up? Nothing below can use the method until it is here."
            }
        } else { Say "would run: git clone --branch $SkillRef --depth 1 $SkillRepo $(Pretty $SkillSrc)" }
    }
}

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
    Run { & $Py3 -m pip install --quiet --user --break-system-packages --no-warn-script-location --disable-pip-version-check -r $reqs } "python3 -m pip install --user -r requirements.txt" | Out-Null
}

# -- the desktop app ---------------------------------------------------------------------------
$TccExe = $null
if ($Mode -eq "tcc") {
    Step "Autosound TCC -- the desktop app"
    if (-not $Uv) {
        Warn "no uv, so no app. The method alone still works; re-run this later to add the app."
        $Mode = "terminal"
    } else {
        Say "the app and what it needs, about 700 MB -- a few minutes, no output until it is done..."
        # `--python` is not optional: without it uv picks whatever interpreter it finds, and the
        # failure reads as a broken package rather than a missing Python.
        # BY TAG, exactly as the method is above -- and exactly as install.sh does it. With no
        # ref, `git+URL` means HEAD of the default branch, so a fresh install handed somebody
        # unfinished work while the app's own update button offered the newest release. The two
        # ways of getting the app have to agree (SCR-054).
        if (-not $TccRef) {
            $tccTags = @()
            if (Get-Command git -ErrorAction SilentlyContinue) {
                $tccTags = @((& git ls-remote --tags --refs $TccRepo $TccTagGlob 2>$null) |
                             ForEach-Object { ($_ -split "/")[-1] } |
                             Sort-Object { [version]($_ -replace '^v', '') })
            }
            if ($tccTags.Count -gt 0) { $TccRef = $tccTags[-1] }
        }
        if ($TccRef) {
            $TccSpec = "autosound-tcc[gui,claude] @ git+$TccRepo@$TccRef"
            Say "version $TccRef"
        } else {
            # No network, no git, or no tags yet. The default branch still installs, and saying so
            # is better than stopping over a version number.
            $TccSpec = "autosound-tcc[gui,claude] @ git+$TccRepo"
            Warn "could not read the app's releases -- installing from the default branch instead"
        }
        if (Run { & $Uv tool install --quiet --python 3.12 --upgrade $TccSpec } "uv tool install autosound-tcc[gui,claude]") {
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
        $out = (& $TccExe --install-desktop 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0) {
            Say "OK   `"Autosound TCC`" on your Desktop and in the Start Menu"
            # See install.sh: this matches TCC's OUTPUT by phrase. The two words are load-bearing
            # on both sides by agreement, not by anything enforcing it.
            if ($out -match "no icon") {
                Say "     (with the generic icon -- TCC's own was not found in the installed package)"
            }
        } else {
            if ($out) { Write-Host $out }
            Warn "the shortcuts were not created. The command still works:  autosound-tcc"
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
        Say "the official installer, antigravity.google/cli/install.ps1 (about a minute)..."
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
                if (Test-Path $tmpd) { Remove-Item $tmpd -Recurse -Force }
                Expand-Archive -Path $tmpz -DestinationPath $tmpd -Force
                $exe = Get-ChildItem -Path $tmpd -Filter "gh.exe" -Recurse | Select-Object -First 1
                if ($exe) {
                    Copy-Item $exe.FullName (Join-Path $LocalBin "gh.exe") -Force
                    Unblock-File (Join-Path $LocalBin "gh.exe") -ErrorAction SilentlyContinue
                    $got = $true
                }
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

# =============================================================================================
# BLOCK 2 -- check, sign in, start. The rest of what a person does, in one place.
# =============================================================================================
Step "Checking"
$ok = $true
if ($DryRun) { Say "(the machine as it stands -- nothing above was actually done)" }
if (Test-Path (Join-Path $SkillHome "rew_tool\contract.py")) {
    $numpyOk = $false
    if (Test-Path $Py3) { $numpyOk = Test-Quiet { & $Py3 -c "import numpy" } }
    if ($numpyOk) { Say "OK   the tuning method (3.x), and its tools load" }
    else {
        Say "OK   the tuning method (3.x)"
        Warn "numpy is NOT importable by python3: crossover selection, the EQ gate, the DSP maths and"
        Warn "plot rendering will fail when the method reaches them."
        $ok = $false
    }
} elseif (Test-Path (Join-Path $SkillHome "rew_tool\rew_api.py")) {
    Warn "the skill at $SkillHome is the 2.x line -- TCC cannot drive it"; $ok = $false
} elseif (-not $DryRun) {
    Warn "no tuning method at $SkillHome"; $ok = $false
}
if ($Mode -eq "tcc" -and -not $DryRun) {
    if ($TccExe -and (Test-Path $DesktopLnk)) { Say "OK   Autosound TCC -- on your Desktop and in the Start Menu" }
    elseif ($TccExe) { Say "OK   Autosound TCC -- the command:  autosound-tcc" }
    else { Warn "Autosound TCC is not installed"; $ok = $false }
}
$ClaudeBin = Find-Bin claude
if ($ClaudeBin) { Say "OK   Claude Code" }
elseif (-not $DryRun) { Warn "Claude Code is not installed; nothing can run a session without it"; $ok = $false }
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
Write-Host ""
if ($DryRun) { Write-Host "Nothing was installed -- this was a dry run." }
elseif ($ok) { Write-Host "Installed." }
else         { Write-Host "Installed, with the warnings above." }

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
            if (Offer "Enter opens the browser / s = later:") {
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
        Say "$n. Gemini reviewer -- optional, once. Have a Google account ready. What happens:"
        Say "     agy opens; press Enter through its two setup screens; your browser asks you to sign"
        Say "     in with Google. If it then asks for a Project ID, copy it from"
        Say "     aistudio.google.com/app/apikey (the ID, not the name). When it says you're in, type /quit"
        if ($interactive -and (Offer "Enter = sign in now / s = later:")) {
            & $AgyBin
            Say "   Done. If it ever answers with `"Agent Platform API has not been used`", the message"
            Say "   carries a link -- open it, press Enable, wait a minute."
        } else { $AgySkipped = $true; Say "   Later, in a terminal:  agy" }
        $n++
    }
    if ($GhBin) {
        if (Test-Quiet { & $GhBin auth status }) { Say "$n. GitHub: OK   signed in" }
        else {
            Say "$n. GitHub -- optional. Your browser opens with a one-time code: sign in, paste it, and answer"
            Say "   Yes when gh asks to authenticate Git with your GitHub credentials."
            if ($interactive -and (Offer "Enter = sign in now / s = later:")) {
                & $GhBin auth login --hostname github.com --git-protocol https --web
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
    Say "* Check the reviewer really answers -- finding the command is not the same as it working."
    Say "  In Git Bash (Start Menu -> Git -> Git Bash):"
    Say "      ~/.claude/skills/autosound-tuning/scripts/gemini_critic.sh --doctor"
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
Write-Host ""
