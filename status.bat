@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ======================================================
echo         Flower AI Agent - Service Status
echo ======================================================
echo.

set "backend_running=0"
set "frontend_running=0"

:: Check backend (port 8000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    set "backend_running=1"
    set "backend_pid=%%a"
)

:: Check frontend (port 8501)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    set "frontend_running=1"
    set "frontend_pid=%%a"
)

echo   Service Status:
echo   ------------------------------------------------------
if "%backend_running%"=="1" (
    echo   [RUNNING] Backend Server    - Port 8000 (PID: %backend_pid%)
) else (
    echo   [STOPPED] Backend Server    - Port 8000
)

if "%frontend_running%"=="1" (
    echo   [RUNNING] Frontend Server   - Port 8501 (PID: %frontend_pid%)
) else (
    echo   [STOPPED] Frontend Server   - Port 8501
)

echo   ------------------------------------------------------
echo.

:: Show access URLs if running
if "%backend_running%"=="1" (
    echo   Access URLs:
    echo   - Frontend:  http://localhost:8501
    echo   - Backend:   http://localhost:8000
    echo   - API Docs:  http://localhost:8000/docs
) else (
    echo   Services are not running.
    echo   Run start.bat to start the services.
)

echo.
echo ======================================================
echo.
echo Press any key to exit...
pause >nul
