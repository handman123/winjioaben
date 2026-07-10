@echo off
cd /d "%~dp0"
echo === Step 1: Install dependencies ===
pip install psutil pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo pip failed. Make sure Python is installed and added to PATH.
    echo Download: https://www.python.org/downloads/
    echo Check: "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo.
echo === Step 2: Build exe ===
pyinstaller --onefile --windowed --hidden-import psutil --name GameDataKeeper main.py
echo.
echo === Done ===
echo Output: dist\GameDataKeeper.exe
pause
