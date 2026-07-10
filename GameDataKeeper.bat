@echo off
cd /d "%~dp0"
powershell.exe -STA -ExecutionPolicy Bypass -NoProfile -File "%~dp0scripts\gui.ps1"
pause
