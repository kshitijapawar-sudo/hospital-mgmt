@echo off
cd /d "%~dp0"
title MediCare HMS Server
echo Starting MediCare HMS backend server...
echo.
python server.py
if errorlevel 1 (
    echo.
    echo If you see "python is not recognized", install Python from https://www.python.org/downloads/
    echo and make sure to check "Add Python to PATH" during setup.
    pause
)
