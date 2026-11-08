@echo off
setlocal
cd /d "%~dp0" || (
    echo Could not open the RAM Deal Hunter folder.
    pause
    exit /b 1
)

:scan_again
echo.
echo ========================================
echo RAM Deal Hunter - manual home scan
echo ========================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Run-LocalScan.ps1"
if errorlevel 1 (
    echo.
    echo Scan encountered an error. Check logs\local-scanner.log.
)

echo.
choice /C YN /N /M "Run another scan? [Y/N] "
if errorlevel 2 goto done
if errorlevel 1 goto scan_again

:done
echo Closing RAM Deal Hunter manual scanner.
endlocal
