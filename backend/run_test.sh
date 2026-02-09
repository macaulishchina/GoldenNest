#!/bin/bash
# Golden Nest Backend Temporary Testing Script for AI
# Uses port 8001 for isolated testing, auto-cleanup after test

# Check if we're in the correct directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: This script must be run from the backend/ directory"
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Setup virtual environment if needed
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import uvicorn" 2>/dev/null; then
    pip install -r requirements.txt >/dev/null 2>&1
fi

# Check if temp test port 8001 is already in use
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":8001 " | grep "LISTEN" >/dev/null; then
    echo "⚠️  Test port 8001 already in use, cleaning up..."
    if command -v lsof &> /dev/null; then
        kill -9 $(lsof -ti:8001) 2>/dev/null
    else
        fuser -k 8001/tcp 2>/dev/null
    fi
    sleep 2
fi

# Start temp backend on port 8001
echo "🧪 Starting TEMPORARY backend test server on port 8001..."
echo "📍 Test server at: http://127.0.0.1:8001"
echo "🔄 Database auto-migration enabled"
echo "⏱️  Will auto-cleanup after testing"
echo ""

# Start in background and save PID
nohup uvicorn app.main:app --reload --port 8001 > /dev/null 2>&1 &
TEST_PID=$!
echo $TEST_PID > .backend_test_pid

sleep 3
echo "✅ Test backend ready on port 8001 (PID: $TEST_PID)"
