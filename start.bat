@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ======================================================
echo         Flower AI Agent - One Click Start
echo ======================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

:: Set project directory
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please configure .env file first.
    pause
    exit /b 1
)

:: Install dependencies (全量安装，避免 --no-deps 漏装传递依赖)
echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet

:: Start backend in new window
echo [INFO] Starting backend server on port 8000...
start "Flower AI Backend" cmd /k "cd /d "%PROJECT_DIR%" && python run_backend.py"

:: Wait for backend to start
echo [INFO] Waiting for backend to start...
ping -n 6 127.0.0.1 >nul

:: Start frontend in new window
echo [INFO] Starting frontend on port 8501...
start "Flower AI Frontend" cmd /k "cd /d "%PROJECT_DIR%" && python run_frontend.py"

echo.
echo ======================================================
echo         Services Started!
echo ======================================================
echo.
echo   Frontend:  http://localhost:8501
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo ======================================================
echo.
echo Press any key to exit this window...
pause >nul
