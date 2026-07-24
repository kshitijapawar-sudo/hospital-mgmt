@echo off
cd /d "%~dp0"
title MediCare HMS Launcher
echo ===================================================
echo             MediCare HMS Launcher                 
echo ===================================================
echo.
echo 1. Starting backend database server...
start "MediCare HMS Server" cmd /c "cd backend && python server.py"

echo 2. Waiting for server to start...
timeout /t 2 >nul

echo 3. Launching frontend interface in browser...
start "" "frontend\index.html"

echo.
echo Setup complete. Close the "MediCare HMS Server" window when you want to stop the server.
echo.
timeout /t 3 >nul
exit
