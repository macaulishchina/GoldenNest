#!/bin/bash
# Cleanup script to kill all temporary test servers
# Kills services on test ports 8001 (backend) and 5174 (frontend)

echo "🧹 Cleaning up temporary test servers..."

# Kill backend test server (port 8001)
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":8001 " | grep "LISTEN" >/dev/null; then
    echo "🔴 Stopping backend test server on port 8001..."
    if command -v lsof &> /dev/null; then
        kill -9 $(lsof -ti:8001) 2>/dev/null
    else
        fuser -k 8001/tcp 2>/dev/null
    fi
    echo "✅ Backend test server stopped"
else
    echo "ℹ️  No backend test server running on port 8001"
fi

# Kill frontend test server (port 5174)
if lsof -Pi :5174 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":5174 " | grep "LISTEN" >/dev/null; then
    echo "🔴 Stopping frontend test server on port 5174..."
    if command -v lsof &> /dev/null; then
        kill -9 $(lsof -ti:5174) 2>/dev/null
    else
        fuser -k 5174/tcp 2>/dev/null
    fi
    echo "✅ Frontend test server stopped"
else
    echo "ℹ️  No frontend test server running on port 5174"
fi

# Clean up PID files
rm -f backend/.backend_test_pid 2>/dev/null
rm -f frontend/.frontend_test_pid 2>/dev/null

echo ""
echo "✨ Cleanup complete!"
