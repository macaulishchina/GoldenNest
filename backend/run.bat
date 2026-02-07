@echo off
REM Golden Nest Backend Startup Script for Windows
REM This script must be run from the backend\ directory

REM Check if we're in the correct directory
if not exist "app\main.py" (
    echo ❌ Error: This script must be run from the backend\ directory
    echo 💡 Usage: cd backend ^&^& run.bat
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

REM Check if dependencies are installed
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo ⚠️  Dependencies not installed. Installing...
    pip install -r requirements.txt
    echo ✅ Dependencies installed
)

REM Start the backend server
echo 🚀 Starting Golden Nest backend server...
echo 📍 Server will be available at: http://127.0.0.1:8000
echo 📚 API documentation: http://127.0.0.1:8000/api/docs
echo.
uvicorn app.main:app --reload --port 8000
