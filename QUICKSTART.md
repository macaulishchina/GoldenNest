# Quick Start Guide

## ⚠️ Common Startup Issues

### "ModuleNotFoundError: No module named 'app'" when starting backend

**Problem**: Running `uvicorn app.main:app` from the wrong directory.

**Solution**: Backend commands MUST be run from the `backend/` directory:

```bash
# ✅ CORRECT: Run from backend/ directory
cd backend
./run.sh           # Linux/Mac
# or
run.bat            # Windows
# or
uvicorn app.main:app --reload --port 8000

# ❌ WRONG: Don't run from repository root
# This will cause ModuleNotFoundError
uvicorn app.main:app --reload --port 8000
```

## 🚀 Quick Start

### Using Docker (Recommended)
```bash
docker-compose up -d --build
# Access: http://localhost:8088
```

### Local Development

**Backend:**
```bash
cd backend
./run.sh           # Linux/Mac
run.bat            # Windows
# Access: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Access: http://localhost:5173
```

## 📚 More Information

See [README.md](README.md) for complete documentation.
