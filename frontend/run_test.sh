#!/bin/bash
# Golden Nest Frontend Temporary Testing Script for AI
# Uses port 5174 for isolated testing, auto-cleanup after test

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: This script must be run from the frontend/ directory"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    npm install >/dev/null 2>&1
fi

# Check if temp test port 5174 is already in use
if lsof -Pi :5174 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":5174 " | grep "LISTEN" >/dev/null; then
    echo "⚠️  Test port 5174 already in use, cleaning up..."
    if command -v lsof &> /dev/null; then
        kill -9 $(lsof -ti:5174) 2>/dev/null
    else
        fuser -k 5174/tcp 2>/dev/null
    fi
    sleep 2
fi

# Start temp frontend on port 5174
echo "🧪 Starting TEMPORARY frontend test server on port 5174..."
echo "📍 Test server at: http://localhost:5174"
echo "⏱️  Will auto-cleanup after testing"
echo ""

# Start in background with custom port and save PID
nohup npm run dev -- --port 5174 > /dev/null 2>&1 &
TEST_PID=$!
echo $TEST_PID > .frontend_test_pid

sleep 3
echo "✅ Test frontend ready on port 5174 (PID: $TEST_PID)"
