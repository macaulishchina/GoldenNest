#!/bin/bash
# Golden Nest Frontend Startup Script for AI Testing
# This script marks the service as AI-started

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
    echo "⚠️  Installing dependencies..."
    npm install
fi

# Check if port 5173 is already in use
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":5173 " | grep "LISTEN" >/dev/null; then
    # Port is in use, check who started it
    if [ -f ".frontend_owner" ]; then
        OWNER=$(cat .frontend_owner)
        if [ "$OWNER" = "USER" ]; then
            # User started it, reuse it
            echo "ℹ️  Frontend server already running (started by user)"
            echo "📍 Reusing existing service at: http://localhost:5173"
            exit 0
        else
            # AI started it, already running
            echo "ℹ️  Frontend server already running (started by AI)"
            echo "📍 Service available at: http://localhost:5173"
            exit 0
        fi
    else
        # Unknown owner, reuse it
        echo "ℹ️  Frontend server already running"
        echo "📍 Reusing existing service at: http://localhost:5173"
        exit 0
    fi
fi

# Mark this service as AI started
echo "AI" > .frontend_owner

# Start the development server in background
echo "🤖 Starting frontend server for AI testing..."
echo "📍 Server at: http://localhost:5173"
nohup npm run dev > /dev/null 2>&1 &
sleep 3
