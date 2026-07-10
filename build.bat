@echo off
REM Build the single-file WenglorMEL Rental System exe.
REM Double-click this file, or run it from a terminal. No venv activation needed.

REM cd to this script's own folder so it works no matter where it's launched from.
cd /d "%~dp0"

echo Building WenglorMEL Rental System 2.2.0 ...
echo.

"bnrs\Scripts\python.exe" -m PyInstaller --noconfirm "WenglorMEL Rental System 2.2.0.spec"

echo.
if errorlevel 1 (
    echo BUILD FAILED - see the messages above.
) else (
    echo BUILD OK  ->  dist\WenglorMEL Rental System 2.2.0.exe
)
echo.
pause
