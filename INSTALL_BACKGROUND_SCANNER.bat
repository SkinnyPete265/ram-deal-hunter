@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-LocalScanner.ps1"
echo.
if errorlevel 1 echo Setup did not finish. Review errors above and logs\local-scanner.log.
pause
