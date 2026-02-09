@echo off
setlocal enabledelayedexpansion
REM Golden Nest Backend Startup Script for Windows
REM This script must be run from the backend\ directory

REM Check if we're in the correct directory
if not exist "app\main.py" (
    echo ❌ Error: This script must be run from the backend\ directory
    echo 💡 Usage: cd backend ^&^& run.bat
    exit /b 1
)

REM Check Python version
python --version 2>nul | findstr /R "Python 3\." >nul
if errorlevel 1 (
    echo ❌ Error: Python 3 is required. Please install Python 3.8 or higher.
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo ⚠️  Virtual environment not found. Creating one...
    python -m venv venv
    echo ✅ Virtual environment created
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies need to be installed or updated
set DEPS_INSTALLED=true
if not exist "venv\.deps_installed" set DEPS_INSTALLED=false
if exist "requirements.txt" (
    for /F %%i in ('dir /B /O:D "venv\.deps_installed" "requirements.txt" 2^>nul ^| find /C "requirements.txt"') do (
        if %%i GTR 0 set DEPS_INSTALLED=false
    )
)

REM Also check if uvicorn is actually installed
python -c "import uvicorn" 2>nul
if errorlevel 1 set DEPS_INSTALLED=false

if "%DEPS_INSTALLED%"=="false" (
    echo ⚠️  Dependencies need to be installed. Installing...
    pip install -r requirements.txt
    type nul > venv\.deps_installed
    echo ✅ Dependencies installed
)

REM Check if port 8000 is already in use
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    REM Port is in use, check who started it
    if exist ".backend_owner" (
        set /p OWNER=<.backend_owner
        if "!OWNER!"=="AI" (
            REM AI started it, user can terminate and restart
            echo ⚠️  Backend server started by AI is running on port 8000
            echo 🔄 Terminating AI service and starting user service...
            for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
                taskkill /F /PID %%a >nul 2>&1
            )
            timeout /t 2 /nobreak >nul
            del .backend_owner >nul 2>&1
        ) else (
            REM User started it, show info and exit
            echo ℹ️  Backend server is already running on port 8000
            echo 📍 Access it at: http://127.0.0.1:8000
            echo 📚 API documentation: http://127.0.0.1:8000/api/docs
            echo 💡 Server is already started by you
            pause
            exit /b 0
        )
    ) else (
        REM Unknown owner, ask user
        echo ⚠️  Backend server is already running on port 8000
        echo 📍 Access it at: http://127.0.0.1:8000
        set /p "CHOICE=Terminate and restart? (Y/N): "
        if /i "!CHOICE!"=="Y" (
            for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
                taskkill /F /PID %%a >nul 2>&1
            )
            timeout /t 2 /nobreak >nul
        ) else (
            exit /b 0
        )
    )
)

REM Mark this service as USER started
echo USER>.backend_owner

REM Start the backend server
echo 🚀 Starting Golden Nest backend server...
echo 📍 Server will be available at: http://127.0.0.1:8000
echo 📚 API documentation: http://127.0.0.1:8000/api/docs
echo 🔄 Database auto-migration enabled (will add missing columns)
echo.
uvicorn app.main:app --reload --port 8000
