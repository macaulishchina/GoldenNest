@echo off
REM Golden Nest Frontend Startup Script for AI Testing
REM This script marks the service as AI-started

setlocal enabledelayedexpansion

REM Check if we're in the correct directory
if not exist "package.json" (
    echo ❌ Error: This script must be run from the frontend\ directory
    exit /b 1
)

REM Check Node.js
node --version 2>nul | findstr /R "v" >nul
if errorlevel 1 (
    echo ❌ Error: Node.js is required
    exit /b 1
)

REM Install dependencies if needed
if not exist "node_modules" (
    echo ⚠️  Installing dependencies...
    call npm install
)

REM Check if port 5173 is already in use
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    REM Port is in use, check who started it
    if exist ".frontend_owner" (
        set /p OWNER=<.frontend_owner
        if "!OWNER!"=="USER" (
            REM User started it, reuse it
            echo ℹ️  Frontend server already running (started by user)
            echo 📍 Reusing existing service at: http://localhost:5173
            exit /b 0
        ) else (
            REM AI started it, already running
            echo ℹ️  Frontend server already running (started by AI)
            echo 📍 Service available at: http://localhost:5173
            exit /b 0
        fi
    ) else (
        REM Unknown owner, reuse it
        echo ℹ️  Frontend server already running
        echo 📍 Reusing existing service at: http://localhost:5173
        exit /b 0
    )
)

REM Mark this service as AI started
echo AI>.frontend_owner

REM Start the development server
echo 🤖 Starting frontend server for AI testing...
echo 📍 Server at: http://localhost:5173
start /B npm run dev
timeout /t 3 /nobreak >nul
