@echo off
chcp 65001 >nul 2>&1

echo ======================================================
echo         Flower AI Agent - Restart
echo ======================================================
echo.

:: Run stop script
echo [INFO] Stopping existing services...
call "%~dp0stop.bat" /silent

:: Wait a moment
timeout /t 3 /nobreak >nul

:: Run start script
echo [INFO] Starting services...
call "%~dp0start.bat"
