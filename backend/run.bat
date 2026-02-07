@echo off
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

REM Start the backend server
echo 🚀 Starting Golden Nest backend server...
echo 📍 Server will be available at: http://127.0.0.1:8000
echo 📚 API documentation: http://127.0.0.1:8000/api/docs
echo.
uvicorn app.main:app --reload --port 8000
