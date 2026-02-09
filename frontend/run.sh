#!/bin/bash

# Check if running from the frontend directory
if [ ! -f "package.json" ]; then
    echo "Error: Please run this script from the frontend directory"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed or not in PATH"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

echo "Node.js version:"
node --version
echo "npm version:"
npm --version

# Check if port 5173 is already in use
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep ":5173 " | grep "LISTEN" >/dev/null; then
    # Port is in use, check who started it
    if [ -f ".frontend_owner" ]; then
        OWNER=$(cat .frontend_owner)
        if [ "$OWNER" = "AI" ]; then
            # AI started it, user can terminate and restart
            echo "⚠️  Frontend server started by AI is running on port 5173"
            echo "🔄 Terminating AI service and starting user service..."
            if command -v lsof &> /dev/null; then
                kill -9 $(lsof -ti:5173) 2>/dev/null
            else
                fuser -k 5173/tcp 2>/dev/null
            fi
            sleep 2
            rm -f .frontend_owner
        else
            # User started it, show info and exit
            echo "ℹ️  Frontend server is already running on port 5173"
            echo "📍 Access it at: http://localhost:5173"
            echo "💡 Server is already started by you"
            exit 0
        fi
    else
        # Unknown owner, ask user
        echo "⚠️  Frontend server is already running on port 5173"
        echo "📍 Access it at: http://localhost:5173"
        read -p "Terminate and restart? (y/N): " CHOICE
        if [ "$CHOICE" = "y" ] || [ "$CHOICE" = "Y" ]; then
            if command -v lsof &> /dev/null; then
                kill -9 $(lsof -ti:5173) 2>/dev/null
            else
                fuser -k 5173/tcp 2>/dev/null
            fi
            sleep 2
        else
            exit 0
        fi
    fi
fi

# Mark this service as USER started
echo "USER" > .frontend_owner

# Install dependencies
echo ""
echo "Installing dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Start the development server
echo ""
echo "Starting frontend development server on http://0.0.0.0:5173"
echo ""
npm run dev
