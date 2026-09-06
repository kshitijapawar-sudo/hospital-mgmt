@echo off
cd /d "%~dp0"
title MediCare HMS Launcher
echo ===================================================
echo             MediCare HMS Launcher                 
echo ===================================================
echo.
echo 1. Starting database ^& application server...
start "MediCare HMS Server" cmd /k "cd backend && python server.py"

echo 2. Waiting for server to initialize...
timeout /t 2 >nul

echo 3. Opening MediCare HMS in browser...
start http://localhost:5000

echo.
echo System launched successfully!
echo - Keep the "MediCare HMS Server" window open while using the app.
echo - For mobile access over Wi-Fi, check the IP address shown in the server window.
echo.
timeout /t 4 >nul
exit

