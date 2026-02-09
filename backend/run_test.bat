@echo off
REM Golden Nest Backend Temporary Testing Script for AI
REM Uses port 8001 for isolated testing, auto-cleanup after test

setlocal enabledelayedexpansion

REM Check if we're in the correct directory
if not exist "app\main.py" (
    echo ❌ Error: This script must be run from the backend\ directory
    exit /b 1
)

REM Check Python
python --version 2>nul | findstr /R "Python 3\." >nul
if errorlevel 1 (
    echo ❌ Error: Python 3 is required
    exit /b 1
)

REM Setup virtual environment if needed
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat

REM Install dependencies if needed
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    pip install -r requirements.txt >nul 2>&1
)

REM Check if temp test port 8001 is already in use
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  Test port 8001 already in use, cleaning up...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

REM Start temp backend on port 8001
echo 🧪 Starting TEMPORARY backend test server on port 8001...
echo 📍 Test server at: http://127.0.0.1:8001
echo 🔄 Database auto-migration enabled
echo ⏱️  Will auto-cleanup after testing
echo.

REM Save PID for cleanup
start /B uvicorn app.main:app --reload --port 8001
timeout /t 3 /nobreak >nul

REM Save the PID to a file for cleanup
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo %%a > .backend_test_pid
)

echo ✅ Test backend ready on port 8001
