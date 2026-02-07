#!/bin/bash
# Golden Nest Backend Startup Script
# This script must be run from the backend/ directory

# Check if we're in the correct directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: This script must be run from the backend/ directory"
    echo "💡 Usage: cd backend && ./run.sh"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "⚠️  Dependencies not installed. Installing..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Start the backend server
echo "🚀 Starting Golden Nest backend server..."
echo "📍 Server will be available at: http://127.0.0.1:8000"
echo "📚 API documentation: http://127.0.0.1:8000/api/docs"
echo ""
uvicorn app.main:app --reload --port 8000
