#!/bin/bash
# Golden Nest Backend Startup Script for AI Testing
# This script marks the service as AI-started

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

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "⚠️  Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":8000 " | grep "LISTEN" >/dev/null; then
    # Port is in use, check who started it
    if [ -f ".backend_owner" ]; then
        OWNER=$(cat .backend_owner)
        if [ "$OWNER" = "USER" ]; then
            # User started it, reuse it
            echo "ℹ️  Backend server already running (started by user)"
            echo "📍 Reusing existing service at: http://127.0.0.1:8000"
            exit 0
        else
            # AI started it, already running
            echo "ℹ️  Backend server already running (started by AI)"
            echo "📍 Service available at: http://127.0.0.1:8000"
            exit 0
        fi
    else
        # Unknown owner, reuse it
        echo "ℹ️  Backend server already running"
        echo "📍 Reusing existing service at: http://127.0.0.1:8000"
        exit 0
    fi
fi

# Mark this service as AI started
echo "AI" > .backend_owner

# Start the backend server in background
echo "🤖 Starting backend server for AI testing..."
echo "📍 Server at: http://127.0.0.1:8000"
echo "🔄 Database auto-migration enabled"
nohup uvicorn app.main:app --reload --port 8000 > /dev/null 2>&1 &
sleep 3
