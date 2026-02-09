@echo off
setlocal enabledelayedexpansion
REM Golden Nest Frontend Startup Script for Windows
REM This script must be run from the frontend\ directory

REM Check if we're in the correct directory
if not exist "package.json" (
    echo ❌ Error: This script must be run from the frontend\ directory
    echo 💡 Usage: cd frontend ^&^& run.bat
    exit /b 1
)

REM Check Node.js version
node --version 2>nul | findstr /R "v" >nul
if errorlevel 1 (
    echo ❌ Error: Node.js is required. Please install Node.js from https://nodejs.org/
    exit /b 1
)

REM Check if port 5173 is already in use
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    REM Port is in use, check who started it
    if exist ".frontend_owner" (
        set /p OWNER=<.frontend_owner
        if "!OWNER!"=="AI" (
            REM AI started it, user can terminate and restart
            echo ⚠️  Frontend server started by AI is running on port 5173
            echo 🔄 Terminating AI service and starting user service...
            for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
                taskkill /F /PID %%a >nul 2>&1
            )
            timeout /t 2 /nobreak >nul
            del .frontend_owner >nul 2>&1
        ) else (
            REM User started it, show info and exit
            echo ℹ️  Frontend server is already running on port 5173
            echo 📍 Access it at: http://localhost:5173
            echo 💡 Server is already started by you
            pause
            exit /b 0
        )
    ) else (
        REM Unknown owner, ask user
        echo ⚠️  Frontend server is already running on port 5173
        echo 📍 Access it at: http://localhost:5173
        set /p "CHOICE=Terminate and restart? (Y/N): "
        if /i "!CHOICE!"=="Y" (
            for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
                taskkill /F /PID %%a >nul 2>&1
            )
            timeout /t 2 /nobreak >nul
        ) else (
            exit /b 0
        )
    )
)

REM Mark this service as USER started
echo USER>.frontend_owner

REM Check if node_modules exists
if not exist "node_modules" (
    echo ⚠️  Dependencies not found. Installing...
    call npm install
    if errorlevel 1 (
        echo ❌ Error: Failed to install dependencies
        exit /b 1
    )
    echo ✅ Dependencies installed
) else (
    echo ✅ Dependencies already installed
)

REM Start the development server
echo 🚀 Starting Golden Nest frontend server...
echo 📍 Server will be available at: http://localhost:5173
echo.
call npm run dev
