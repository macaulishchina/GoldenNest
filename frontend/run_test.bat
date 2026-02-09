@echo off
REM Golden Nest Frontend Temporary Testing Script for AI
REM Uses port 5174 for isolated testing, auto-cleanup after test

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
    call npm install >nul 2>&1
)

REM Check if temp test port 5174 is already in use
netstat -ano | findstr ":5174" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  Test port 5174 already in use, cleaning up...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5174" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

REM Start temp frontend on port 5174
echo 🧪 Starting TEMPORARY frontend test server on port 5174...
echo 📍 Test server at: http://localhost:5174
echo ⏱️  Will auto-cleanup after testing
echo.

REM Start with custom port
start /B npm run dev -- --port 5174
timeout /t 3 /nobreak >nul

REM Save the PID to a file for cleanup
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5174" ^| findstr "LISTENING"') do (
    echo %%a > .frontend_test_pid
)

echo ✅ Test frontend ready on port 5174
