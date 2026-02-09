@echo off
REM Golden Nest Backend Startup Script for AI Testing
REM This script marks the service as AI-started

setlocal enabledelayedexpansion

REM Check if we're in the correct directory
if not exist "app\main.py" (
    echo ❌ Error: This script must be run from the backend\ directory
    exit /b 1
)

REM Check Python version
python --version 2>nul | findstr /R "Python 3\." >nul
if errorlevel 1 (
    echo ❌ Error: Python 3 is required
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo ⚠️  Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies if needed
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo ⚠️  Installing dependencies...
    pip install -r requirements.txt
)

REM Check if port 8000 is already in use
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    REM Port is in use, check who started it
    if exist ".backend_owner" (
        set /p OWNER=<.backend_owner
        if "!OWNER!"=="USER" (
            REM User started it, reuse it
            echo ℹ️  Backend server already running (started by user)
            echo 📍 Reusing existing service at: http://127.0.0.1:8000
            exit /b 0
        ) else (
            REM AI started it, already running
            echo ℹ️  Backend server already running (started by AI)
            echo 📍 Service available at: http://127.0.0.1:8000
            exit /b 0
        fi
    ) else (
        REM Unknown owner, reuse it
        echo ℹ️  Backend server already running
        echo 📍 Reusing existing service at: http://127.0.0.1:8000
        exit /b 0
    )
)

REM Mark this service as AI started
echo AI>.backend_owner

REM Start the backend server
echo 🤖 Starting backend server for AI testing...
echo 📍 Server at: http://127.0.0.1:8000
echo 🔄 Database auto-migration enabled
start /B uvicorn app.main:app --reload --port 8000
timeout /t 3 /nobreak >nul
