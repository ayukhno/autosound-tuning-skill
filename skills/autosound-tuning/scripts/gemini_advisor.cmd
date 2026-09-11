@echo off
set "PYCMD=python"
where py >nul 2>nul && set "PYCMD=py -3"
set "arg=%~1"
if "%arg%"=="--doctor" (
    %PYCMD% "%~dp0autosound_ai.py" doctor
) else if "%arg%"=="doctor" (
    %PYCMD% "%~dp0autosound_ai.py" doctor
) else (
    %PYCMD% "%~dp0autosound_ai.py" critic %*
)
