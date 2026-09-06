@echo off
cd /d "%~dp0"
title MediCare HMS - Server (Auto-Update ON)
echo ===================================================
echo   MediCare HMS - Starting server with auto-update
echo ===================================================
echo   Leave this window open. It will:
echo    - Start the hospital app for this PC and any device
echo      on the same Wi-Fi (doctor's laptop, other PCs)
echo    - Automatically check for developer updates and
echo      apply them without you doing anything
echo ===================================================
echo.
python auto_update.py
if errorlevel 1 (
    echo.
    echo Something went wrong. If it says "python is not recognized",
    echo install Python from https://www.python.org/downloads/ and
    echo tick "Add Python to PATH" during setup.
    echo.
    echo If it says this folder is not a git repository, see
    echo DEPLOYMENT_GUIDE.md - the project must be cloned with
    echo "git clone", not unzipped, on this PC.
    pause
)
