@echo off
REM Cleanup script to kill all temporary test servers
REM Kills services on test ports 8001 (backend) and 5174 (frontend)

echo 🧹 Cleaning up temporary test servers...

REM Kill backend test server (port 8001)
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo 🔴 Stopping backend test server on port 8001...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    echo ✅ Backend test server stopped
) else (
    echo ℹ️  No backend test server running on port 8001
)

REM Kill frontend test server (port 5174)
netstat -ano | findstr ":5174" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo 🔴 Stopping frontend test server on port 5174...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5174" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    echo ✅ Frontend test server stopped
) else (
    echo ℹ️  No frontend test server running on port 5174
)

REM Clean up PID files
del backend\.backend_test_pid 2>nul
del frontend\.frontend_test_pid 2>nul

echo.
echo ✨ Cleanup complete!
