@echo off
set "arg=%~1"
if "%arg%"=="--doctor" (
    python "%~dp0autosound_ai.py" doctor
) else if "%arg%"=="doctor" (
    python "%~dp0autosound_ai.py" doctor
) else (
    python "%~dp0autosound_ai.py" advisor %*
)
