#!/bin/bash
# Golden Nest Backend Startup Script
# This script must be run from the backend/ directory

# Check if we're in the correct directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: This script must be run from the backend/ directory"
    echo "💡 Usage: cd backend && ./run.sh"
    exit 1
fi

# Determine Python command (prefer python3)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Verify Python version is 3.x
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d. -f1)
if [ "$PYTHON_VERSION" != "3" ]; then
    echo "❌ Error: Python 3 is required, but found Python $PYTHON_VERSION"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies need to be installed or updated
DEPS_INSTALLED=true
if [ ! -f "venv/.deps_installed" ] || [ "requirements.txt" -nt "venv/.deps_installed" ]; then
    DEPS_INSTALLED=false
elif ! python -c "import uvicorn" 2>/dev/null; then
    DEPS_INSTALLED=false
fi

if [ "$DEPS_INSTALLED" = false ]; then
    echo "⚠️  Dependencies need to be installed. Installing..."
    pip install -r requirements.txt
    touch venv/.deps_installed
    echo "✅ Dependencies installed"
fi

# Start the backend server
echo "🚀 Starting Golden Nest backend server..."
echo "📍 Server will be available at: http://127.0.0.1:8000"
echo "📚 API documentation: http://127.0.0.1:8000/api/docs"
echo ""
uvicorn app.main:app --reload --port 8000
