@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: Check if silent mode
set "SILENT=0"
if "%1"=="/silent" set "SILENT=1"

if "%SILENT%"=="0" (
    echo ======================================================
    echo         Flower AI Agent - One Click Stop
    echo ======================================================
    echo.
    echo [INFO] Stopping services...
    echo.
)

:: Kill backend process (port 8000)
if "%SILENT%"=="0" echo [INFO] Stopping backend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        if "%SILENT%"=="0" echo [INFO] Backend stopped (PID: %%a)
    )
)

:: Kill frontend process (port 8501)
if "%SILENT%"=="0" echo [INFO] Stopping frontend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        if "%SILENT%"=="0" echo [INFO] Frontend stopped (PID: %%a)
    )
)

:: Kill any remaining Python processes related to our app
if "%SILENT%"=="0" echo [INFO] Cleaning up remaining processes...
taskkill /FI "WINDOWTITLE eq Flower AI Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Flower AI Frontend*" /F >nul 2>&1

:: Wait a moment
timeout /t 2 /nobreak >nul

if "%SILENT%"=="0" (
    echo.
    echo ======================================================
    echo         Services Stopped!
    echo ======================================================
    echo.
    echo Press any key to exit...
    pause >nul
)
