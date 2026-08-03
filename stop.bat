@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: Silent mode: skip banners and pause (used by restart.bat as "stop.bat /silent")
set "SILENT=0"
if /i "%1"=="/silent" set "SILENT=1"

if "%SILENT%"=="0" (
    echo ============================================================
    echo           Flower AI Agent - Shutdown Script
    echo ============================================================
    echo.
)

:: ------------------------------------------------------------
:: 1. Stop backend (port 8000)
:: ------------------------------------------------------------
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING') do (
    set "FOUND=1"
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        if "%SILENT%"=="0" echo [INFO] Backend stopped. PID %%a
    ) else (
        if "%SILENT%"=="0" echo [WARN] Backend process PID %%a could not be stopped.
    )
)
if "!FOUND!"=="0" if "%SILENT%"=="0" echo [INFO] Backend is not running.

:: ------------------------------------------------------------
:: 2. Stop frontend (port 8501)
:: ------------------------------------------------------------
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501 " ^| findstr LISTENING') do (
    set "FOUND=1"
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        if "%SILENT%"=="0" echo [INFO] Frontend stopped. PID %%a
    ) else (
        if "%SILENT%"=="0" echo [WARN] Frontend process PID %%a could not be stopped.
    )
)
if "!FOUND!"=="0" if "%SILENT%"=="0" echo [INFO] Frontend is not running.

:: ------------------------------------------------------------
:: 3. Fallback: kill leftover console windows by title
:: ------------------------------------------------------------
taskkill /FI "WINDOWTITLE eq Flower AI Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Flower AI Frontend*" /F >nul 2>&1

:: ------------------------------------------------------------
:: 4. Give processes a moment to release the ports
::    (ping delay works even with redirected stdin; "timeout" does not)
:: ------------------------------------------------------------
ping -n 3 127.0.0.1 >nul

if "%SILENT%"=="0" (
    echo.
    echo ============================================================
    echo           All Services Stopped!
    echo ============================================================
    echo.
    echo   Use start.bat to start them again.
    echo.
    echo ============================================================
    echo.
    pause
)
