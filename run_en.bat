@echo off
title AoE2 AI Coach (English)
cd /d "%~dp0"

:: =========================================================================
:: [OPTIONAL] Set your in-game player name here if you want to skip selecting
:: it every time (e.g. set PLAYER_NAME=DJaystar9083).
:: Leave empty to let the coach interactively ask which player to coach.
:: =========================================================================
set PLAYER_NAME=

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in 'venv'.
    echo Please make sure the venv is set up properly.
    pause
    exit /b 1
)

:: Set player argument if PLAYER_NAME is defined
set PLAYER_ARG=
if not "%PLAYER_NAME%"=="" (
    set PLAYER_ARG=--player "%PLAYER_NAME%"
)

:: If a file was dragged onto run_en.bat, pass it as argument
if "%~1"=="" (
    venv\Scripts\python.exe main.py coach --lang en %PLAYER_ARG%
) else (
    venv\Scripts\python.exe main.py coach "%~1" --lang en %PLAYER_ARG%
)

echo.
echo Press any key to close this window...
pause >nul
