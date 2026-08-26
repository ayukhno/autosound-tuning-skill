@echo off
setlocal EnableDelayedExpansion
REM ===========================================================================
REM  Autosound tuning -- Windows entry point.
REM
REM  Double-click this, or run it from cmd, or from PowerShell. All three work,
REM  and that is the whole reason this file exists (INSTALLER-TZ 2.1).
REM
REM  Two things it removes:
REM
REM    1. cmd cannot run a .ps1 at all -- it has no idea what one is, and a
REM       double-clicked .ps1 opens in Notepad. Double-clicking ALWAYS opens
REM       cmd.exe, so a .cmd is the one thing every Windows user can start.
REM
REM    2. PowerShell refuses to run a script a browser downloaded, under the
REM       default execution policy. Passing -ExecutionPolicy Bypass to a single
REM       invocation avoids that without changing any machine setting -- the
REM       policy for everything else stays exactly as it was.
REM
REM  Everything real happens in install.ps1. This file finds it and hands over,
REM  options included:  install.cmd -Terminal   install.cmd -NoReviewer
REM                     install.cmd -DryRun     install.cmd -Uninstall
REM
REM  To pin versions, pass BOTH as one pair -- they are released and tested
REM  together, and a mixed pair is untested:
REM    install.cmd -SkillRef v3.0.33 -TccRef v0.1.22
REM
REM  Plain ASCII on purpose: cmd reads this file in the console code page, and
REM  a stray non-ASCII byte in an echo line prints as junk.
REM ===========================================================================

set "PS1=%~dp0install.ps1"
set "PS1URL=https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1"

REM PowerShell 7 if it is here, Windows PowerShell 5.1 otherwise. 5.1 ships with
REM every supported Windows, so one of these always exists.
set "PS=powershell"
where pwsh >nul 2>&1 && set "PS=pwsh"

REM Was this double-clicked, or run from a prompt? When Explorer starts it, the
REM command line it was started with contains /c -- a prompt does not. It decides
REM one thing only: whether to hold the window open at the end so the output can
REM be read instead of vanishing.
set "DOUBLECLICKED="
echo %cmdcmdline% | find /i "%~nx0" >nul
if not errorlevel 1 echo %cmdcmdline% | find /i "/c" >nul && set "DOUBLECLICKED=1"

if exist "%PS1%" (
    echo Running %PS1%
    "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
) else (
    REM Only the .cmd was downloaded, so fetch the script it is a door to. Not
    REM saved to disk first: a saved copy would be quarantined and would go
    REM stale, and this way there is one source of truth for the real work.
    echo install.ps1 is not beside this file -- fetching it from GitHub
    "%PS%" -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; $s = irm '%PS1URL%' -UseBasicParsing; & ([scriptblock]::Create($s)) %*"
)

set "RC=%ERRORLEVEL%"
if defined DOUBLECLICKED (
    echo.
    echo Finished with exit code %RC%.
    pause
)
exit /b %RC%
