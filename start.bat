@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ============================================================
echo           Flower AI Agent - Startup Script
echo ============================================================
echo.

cd /d "%~dp0"

:: ------------------------------------------------------------
:: 1. Locate Python (prefer the project virtual environment)
:: ------------------------------------------------------------
set "PYTHON=python"
if exist "venv\Scripts\python.exe" (
    set "PYTHON=venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: venv
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found.
        echo         Please install Python 3.11+ or create a virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Using system Python
)

:: ------------------------------------------------------------
:: 2. Check .env configuration
:: ------------------------------------------------------------
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo         Copy .env.example to .env and fill in your API keys first.
    pause
    exit /b 1
)
echo [INFO] .env configuration found

:: ------------------------------------------------------------
:: 3. Check whether services are already running
:: ------------------------------------------------------------
set "BACKEND_RUNNING=0"
set "FRONTEND_RUNNING=0"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING') do set "BACKEND_RUNNING=1"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501 " ^| findstr LISTENING') do set "FRONTEND_RUNNING=1"

if "!BACKEND_RUNNING!"=="1" if "!FRONTEND_RUNNING!"=="1" (
    echo [WARN] Both services are already running.
    echo        Frontend: http://localhost:8501
    echo        Backend:  http://localhost:8000
    echo        Use stop.bat to stop them first.
    pause
    exit /b 0
)
if "!BACKEND_RUNNING!"=="1" echo [WARN] Backend port 8000 is already in use - frontend only will be started.
if "!FRONTEND_RUNNING!"=="1" echo [WARN] Frontend port 8501 is already in use - backend only will be started.

:: ------------------------------------------------------------
:: 4. Install / verify dependencies
:: ------------------------------------------------------------
echo [INFO] Checking dependencies...
"%PYTHON%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [INFO] Dependencies OK

:: ------------------------------------------------------------
:: 5. Start backend (FastAPI, port 8000)
:: ------------------------------------------------------------
if "!BACKEND_RUNNING!"=="0" (
    echo [INFO] Starting backend on port 8000...
    start "Flower AI Backend" cmd /k "cd /d %~dp0 && %PYTHON% run_backend.py"
    echo [INFO] Waiting for backend to boot...
    ping -n 6 127.0.0.1 >nul
) else (
    echo [SKIP] Backend already running
)

:: ------------------------------------------------------------
:: 6. Start frontend (Streamlit, port 8501)
:: ------------------------------------------------------------
if "!FRONTEND_RUNNING!"=="0" (
    echo [INFO] Starting frontend on port 8501...
    start "Flower AI Frontend" cmd /k "cd /d %~dp0 && %PYTHON% run_frontend.py"
) else (
    echo [SKIP] Frontend already running
)

echo.
echo ============================================================
echo           Services Started Successfully!
echo ============================================================
echo.
echo   Frontend:  http://localhost:8501
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo ============================================================
echo.
pause
