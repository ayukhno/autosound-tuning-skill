# Autosound tuning — installer for Windows.
#
# The mirror of install.sh. Same two choices, same refusals, same order:
#
#   1. the SKILL      — the tuning method, plus the Python packages its tools import.
#   2. the SKILL + TCC — plus the Tuning Command Center desktop app.
#
# What it will not do: log you in (the session is yours — see `claude auth login` at the end),
# install anything from the network without asking, or touch a skill directory it did not create.
#
# NOT YET RUN ON WINDOWS. Written against the documented behaviour of winget, uv and Claude Code
# and mirrored line for line from the macOS script, which is tested — but no part of this file has
# executed on a Windows machine. It prints what it is about to do at every step so that a first
# run shows exactly where it stops. Please report where it does.
#
# Usage:
#   .\install.ps1                     ask which of the two
#   .\install.ps1 -Terminal           the skill only
#   .\install.ps1 -Tcc                the skill and the desktop app
#   .\install.ps1 -DryRun             say what it would do, change nothing
#   .\install.ps1 -SkillRef v3.0.1    a specific skill version (default: the newest 3.x tag)
#   .\install.ps1 -Uninstall          remove what this script installed — NEVER your projects

[CmdletBinding()]
param(
    [switch]$Terminal,
    [switch]$Tcc,
    [switch]$DryRun,
    [switch]$Uninstall,
    [switch]$Yes,
    [string]$SkillRef = ""
)

$ErrorActionPreference = "Stop"

$SkillRepo = "https://github.com/ayukhno/autosound-tuning-skill.git"
$TccRepo   = "https://github.com/ayukhno/autosound-tcc"
$SkillHome = Join-Path $HOME ".claude\skills\autosound-tuning"
# The checkout lives beside the skill and the skill points at it — see install.sh for why moving
# the subdirectory out instead leaves something no later run can update.
$SkillSrc  = Join-Path $HOME ".claude\skills\.autosound-tuning-src"

function Say  { param($m) Write-Host "  $m" }
function Step { param($m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Warn { param($m) Write-Host "  ! $m" -ForegroundColor Yellow }
function Have { param($n) [bool](Get-Command $n -ErrorAction SilentlyContinue) }

function Run {
    param([scriptblock]$Block, [string]$Label)
    if ($DryRun) { Say "would run: $Label"; return }
    & $Block
}

# Defaults to NO, like the macOS script: an installer that proceeds on a stray keypress is one
# nobody can run carefully.
function Confirm-Step {
    param($Question)
    if ($Yes) { return $true }
    if ($DryRun) { Say "would ask: $Question"; return $false }
    $answer = Read-Host "  $Question [y/N]"
    return $answer -match '^[yY]'
}

# ── uninstall ─────────────────────────────────────────────────────────────────
if ($Uninstall) {
    Step "Removing what this script installed"
    Say "Your PROJECT FOLDERS are never touched — not by this, not with -Yes, not ever."
    Say "They hold measurements that took hours in a car and cannot be reproduced."
    Write-Host ""

    if (Test-Path $SkillHome) {
        $item = Get-Item $SkillHome -Force
        $target = ($item.Target -join "")
        if ($item.LinkType -in @("SymbolicLink","Junction") -and $target -like "$SkillSrc*") {
            Say "removing the junction and the checkout it points at"
            # Remove-Item on a junction deletes the LINK, not the target — but only with -Force
            # and without -Recurse descending into it, which is why the two go separately.
            Run { Remove-Item $SkillHome -Force } "remove junction"
            Run { Remove-Item $SkillSrc -Recurse -Force } "remove checkout"
        } elseif ($item.LinkType) {
            Warn "$SkillHome points at $target — not ours, left alone"
        } else {
            Warn "$SkillHome is a real directory this script did not create — left alone"
        }
    } else { Say "no skill installed by this script" }

    if ((Have uv) -and ((uv tool list 2>$null) -join "`n") -match '^autosound-tcc') {
        Say "removing autosound-tcc"
        Run { uv tool uninstall autosound-tcc } "uv tool uninstall"
    } else { Say "autosound-tcc not installed by uv" }

    $lnk = Join-Path ([System.Environment]::GetFolderPath("Programs")) "Autosound TCC.lnk"
    if (Test-Path $lnk) { Say "removing the Start Menu shortcut"; Run { Remove-Item $lnk -Force } "remove shortcut" }

    Write-Host ""
    Say "Left in place on purpose: the Python packages (shared with everything else using that"
    Say "interpreter), Claude Code (its own installer owns it), and ~\.claude (yours)."
    Say "Every tuning project you have is untouched."
    exit 0
}

# ── what is already here ──────────────────────────────────────────────────────
Step "Looking at what you already have"
foreach ($tool in @("git", "uv", "claude", "python")) {
    if (Have $tool) { Say "OK   $tool  $((Get-Command $tool).Source)" }
    else            { Say "--   $tool  not found" }
}

$Mode = ""
if ($Tcc)      { $Mode = "tcc" }
elseif ($Terminal) { $Mode = "terminal" }
else {
    Write-Host ""
    Say "1) Terminal only — the tuning method, no desktop app"
    Say "2) Terminal + TCC — plus the desktop app with the DSP tree, plan and curves (~680 MB)"
    $choice = Read-Host "  Which? [1/2]"
    if ($choice -eq "2") { $Mode = "tcc" } else { $Mode = "terminal" }
}
Write-Host ""
Say "Installing: $(if ($Mode -eq 'tcc') { 'the skill and TCC' } else { 'the skill only' })"

# ── git ───────────────────────────────────────────────────────────────────────
if (-not (Have git)) {
    Step "git is required and is not installed"
    if (Have winget) {
        if (Confirm-Step "Install it with winget (winget install --id Git.Git -e)?") {
            Run { winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements } "winget install Git.Git"
            # winget updates the machine PATH, not this process's copy of it.
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path","User")
        }
    }
    if (-not (Have git)) {
        Warn "install git and run this again — https://git-scm.com/download/win"
        exit 1
    }
}

# ── the skill ─────────────────────────────────────────────────────────────────
Step "The tuning skill"
if (-not $SkillRef) {
    # The newest 3.x tag, by name rather than "main": main is where development lands, and an
    # installer should put you on a release unless you say otherwise.
    $tags = (git ls-remote --tags --refs $SkillRepo "v3.*") 2>$null |
            ForEach-Object { ($_ -split "/")[-1] } |
            Sort-Object { [version]($_ -replace '^v','') }
    if ($tags) { $SkillRef = $tags[-1] } else { $SkillRef = "main" }
}
Say "version: $SkillRef"

$linkExists = Test-Path $SkillHome
$isOurs = $false
if ($linkExists) {
    $item = Get-Item $SkillHome -Force
    $isLink = $item.LinkType -in @("SymbolicLink", "Junction")
    if ($isLink -and $item.Target -and ($item.Target -join "") -like "$SkillSrc*") { $isOurs = $true }
    if ($isLink -and -not $isOurs) {
        Warn "$SkillHome points at $($item.Target) — left exactly as it is."
        Warn "that is somebody's checkout, not this script's to replace."
    } elseif (-not $isLink) {
        Warn "$SkillHome is a real directory this script did not create — left alone."
        Warn "move it aside and re-run if you want this script to manage it."
    }
}

if ((-not $linkExists) -or $isOurs) {
    if (Test-Path (Join-Path $SkillSrc ".git")) {
        Say "already installed — updating to $SkillRef"
        Run { git -C $SkillSrc fetch --tags --quiet origin } "git fetch"
        Run { git -c advice.detachedHead=false -C $SkillSrc checkout --quiet $SkillRef } "git checkout $SkillRef"
    } else {
        Say "installing into $SkillSrc, linked from $SkillHome"
        Run { New-Item -ItemType Directory -Force -Path (Split-Path $SkillHome) | Out-Null } "mkdir"
        Run { git -c advice.detachedHead=false clone --quiet --branch $SkillRef --depth 1 $SkillRepo $SkillSrc } "git clone"
        if (-not $DryRun) {
            if (Test-Path $SkillHome) { Remove-Item $SkillHome -Force -Recurse }
            # A JUNCTION, not a symlink: junctions work for directories without Developer Mode or
            # an elevated prompt, which symlinks on Windows still require (INSTALLER-TZ §3).
            New-Item -ItemType Junction -Path $SkillHome -Target (Join-Path $SkillSrc "skills\autosound-tuning") | Out-Null
        }
    }
}

# ── what the skill's own tools need ───────────────────────────────────────────
# The reason this script exists, ahead of anything about models (INSTALLER-TZ §0). `numpy` is
# imported at module scope by five of the skill's tools; without it they do not import at all.
Step "What the skill's tools need"
$reqs = Join-Path $SkillHome "requirements.txt"
if (-not (Test-Path $reqs)) {
    Warn "no requirements.txt beside the skill — skipping"
} elseif (-not (Have python)) {
    if (Have winget) {
        if (Confirm-Step "Python is not installed. Install it (winget install Python.Python.3.12)?") {
            Run { winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements } "winget install Python"
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path","User")
            Warn "a NEW terminal may be needed before python is on PATH"
        }
    }
    if (-not (Have python)) { Warn "no python — the skill's tools cannot run until there is one" }
} else {
    $py = (Get-Command python).Source
    Say "target interpreter: $py ($(& python -V 2>&1))"
    # Unlike macOS there is no Apple system python to protect: a winget/python.org install is
    # user-writable, so a plain install lands where it should. `--user` inside a venv is refused,
    # so ask the interpreter, exactly as the macOS script does.
    $inVenv = (& python -c "import sys; print(1 if sys.prefix != sys.base_prefix else 0)") -eq "1"
    if ($inVenv) {
        Say "a virtualenv — installing into it"
        Run { & python -m pip install --quiet -r $reqs } "pip install -r requirements.txt"
    } else {
        Say "installing into your user site"
        Run { & python -m pip install --quiet --user -r $reqs } "pip install --user -r requirements.txt"
    }
}

# ── Claude Code ───────────────────────────────────────────────────────────────
Step "Claude Code"
if (Have claude) {
    Say "OK   $(& claude --version 2>&1)"
} else {
    Say "Not installed. The skill and TCC drive YOUR authenticated session — they cannot log in"
    Say "for you, and nothing here can change that."
    if (Confirm-Step "Run the official installer (irm https://claude.ai/install.ps1 | iex)?") {
        Run { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression } "irm claude install"
    } else {
        Say "Skipped. When you want it:  irm https://claude.ai/install.ps1 | iex"
    }
}

# ── TCC ───────────────────────────────────────────────────────────────────────
if ($Mode -eq "tcc") {
    Step "uv (installs its own Python, which is why it is the recommended route)"
    if (Have uv) {
        Say "OK   $(& uv --version)"
    } elseif (Confirm-Step "Install uv (irm https://astral.sh/uv/install.ps1 | iex)?") {
        Run { Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression } "irm uv install"
        $env:Path = "$HOME\.local\bin;$env:Path"
    } else {
        Say "Skipped — TCC cannot be installed without it. The skill above still works."
        exit 0
    }

    Step "Tuning Command Center"
    # `--python` is not optional: without it uv picks whatever interpreter it finds, which may be
    # older than TCC requires, and the failure reads as a broken package rather than as a missing
    # Python (seen on macOS with the system 3.9).
    Run { uv tool install --python 3.12 --upgrade "autosound-tcc[gui,claude] @ git+$TccRepo" } "uv tool install autosound-tcc"

    Step "A Start Menu shortcut"
    if (-not $DryRun) {
        $exe = (Get-Command autosound-tcc -ErrorAction SilentlyContinue).Source
        if (-not $exe) { $exe = Join-Path $HOME ".local\bin\autosound-tcc.exe" }
        if (Test-Path $exe) {
            $programs = [System.Environment]::GetFolderPath("Programs")
            $lnk = Join-Path $programs "Autosound TCC.lnk"
            $shell = New-Object -ComObject WScript.Shell
            $shortcut = $shell.CreateShortcut($lnk)
            # Points at the INSTALLED binary, so `uv tool upgrade` updates the shortcut's target
            # too — the same reason the macOS bundle execs rather than copies.
            $shortcut.TargetPath = $exe
            $shortcut.Description = "Autosound Tuning Command Center"
            $shortcut.Save()
            Say "created: $lnk"
        } else {
            Warn "autosound-tcc not found — no shortcut. `uv tool update-shell` then a new terminal."
        }
    } else { Say "would create a Start Menu shortcut" }
}

# ── did it work ───────────────────────────────────────────────────────────────
Step "Checking"
$ok = $true
if (Test-Path (Join-Path $SkillHome "rew_tool\contract.py")) {
    Say "OK   skill installed, and it is the 3.x line"
    if (Have python) {
        & python -c "import numpy" 2>$null
        if ($LASTEXITCODE -eq 0) { Say "OK   numpy is importable — the skill's tools will load" }
        else {
            Warn "numpy is NOT importable: crossover selection, the EQ gate, the DSP maths and"
            Warn "plot rendering will fail when the method reaches them."
            $ok = $false
        }
    }
} elseif (Test-Path (Join-Path $SkillHome "rew_tool\rew_api.py")) {
    Warn "the skill at $SkillHome is the 2.x line — TCC cannot drive it"
    $ok = $false
} elseif (-not $DryRun) {
    Warn "no skill at $SkillHome"
    $ok = $false
}

if (Have claude) {
    $status = (& claude auth status 2>$null) -join ""
    if ($status -match '"loggedIn"\s*:\s*true') { Say "OK   claude is signed in" }
    else {
        Warn "claude is installed but NOT signed in — run ``claude auth login``."
        Warn "this is the one step that cannot be automated: the session is yours."
        $ok = $false
    }
} else {
    Warn "claude is not installed; nothing can run a session without it"
    $ok = $false
}

Write-Host ""
if ($ok) {
    Say "Done. Open a project folder and run:"
    if ($Mode -eq "tcc") { Say "    autosound-tcc --project-dir ." }
    Say "    claude          # then ask it to tune your car"
} else {
    Say "Finished with the warnings above — read them before starting a session."
}
