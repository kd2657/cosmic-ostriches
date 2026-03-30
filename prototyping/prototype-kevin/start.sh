#!/usr/bin/env bash

# The Local Minima - Startup Script
echo "Starting The Local Minima..."

# 1. Source API keys if .env exists
if [ -f "backend/.env" ]; then
    echo "Loading environment variables from backend/.env..."
    # Export all variables from .env
    export $(grep -v '^#' backend/.env | xargs)
else
    echo "⚠️ Warning: No backend/.env file found."
    echo "Make sure to create one with your NEWSAPI_KEY. See backend/.env.example."
fi

# Function to safely kill background processes on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# 2. Start Backend
echo "Starting FastAPI Backend on port 8000..."
cd backend
# Explicitly use the uv virtual environment python
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 3. Start Frontend
echo "Starting Next.js Frontend on port 3000..."
cd frontend
npm run dev -- -p 3000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "✅ The Local Minima is running!"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend:  http://localhost:8000"
echo "========================================="
echo "Press Ctrl+C to stop both servers."

# Wait indefinitely so the trap stays alive
wait
