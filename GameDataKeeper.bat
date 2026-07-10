@echo off
cd /d "%~dp0"

:: Try Python exe first
if exist "dist\GameDataKeeper.exe" (
    start "" "dist\GameDataKeeper.exe"
    exit
)

:: Try running Python directly
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" python main.py
    exit
)

:: Fallback: PowerShell CLI
echo Python not found. Running CLI version...
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0scripts\core.ps1"
pause
