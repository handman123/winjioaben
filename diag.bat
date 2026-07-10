@echo off
echo ============================================
echo   GameDataKeeper Diagnostic Tool
echo ============================================
echo.
echo If you can see this, bat file works OK.
echo.
echo [1/3] Current dir: %CD%
echo [2/3] Script dir: %~dp0
echo.
echo [3/3] Testing PowerShell...
powershell.exe -NoProfile -Command "Write-Host 'PowerShell works OK' -ForegroundColor Green"
echo PowerShell exit code: %ERRORLEVEL%
echo.
echo ============================================
echo Diagnostic done. Please screenshot this.
echo ============================================
pause
