@echo off
title AoE2 AI Coach
cd /d "%~dp0"

:: =========================================================================
:: [OPTIONEEL] Vul hier je in-game spelersnaam in als je die niet telkens
:: wilt selecteren (bijv. set PLAYER_NAME=DJaystar9083).
:: Laat leeg om de coach interactief te laten vragen welke speler te coachen.
:: =========================================================================
set PLAYER_NAME=

:: Controleer of virtual environment bestaat
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtuele omgeving niet gevonden in 'venv'.
    echo Maak eerst een venv aan of installeer de vereisten.
    pause
    exit /b 1
)

:: Stel extra player argument in als PLAYER_NAME is ingevuld
set PLAYER_ARG=
if not "%PLAYER_NAME%"=="" (
    set PLAYER_ARG=--player "%PLAYER_NAME%"
)

:: Als een bestand op run.bat is gesleept, geef dat mee via %*
if "%~1"=="" (
    venv\Scripts\python.exe main.py coach %PLAYER_ARG%
) else (
    venv\Scripts\python.exe main.py coach "%~1" %PLAYER_ARG%
)

echo.
echo Druk op een toets om dit venster te sluiten...
pause >nul
