@echo off
cd /d "%~dp0"

:: Try packaged exe first
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

echo Python not found. Please install Python or run the packaged exe.
pause
