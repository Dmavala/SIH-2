#!/usr/bin/env bash
# AEGIS Voice-Sentinel launcher — runs backend + serves built frontend on one port.
# Configuration is env-driven: see .env.example (all values optional for dev).

set -e

PORT=${PORT:-8000}

echo "================================================================="
echo "  AEGIS VOICE-SENTINEL: Audio Deepfake Detection & Defense"
echo "================================================================="
echo "  Backend API + Dashboard : http://localhost:$PORT"
echo "  Config                  : .env (see .env.example)"
echo "  Tests                   : python -m unittest discover -s tests"
echo "================================================================="

# Build the frontend once if the dashboard assets are missing
if [ ! -f "frontend/dist/index.html" ]; then
    echo "Frontend build not found — building dashboard..."
    (cd frontend && npm ci && npm run build)
fi

# Find Python with required dependencies
PYTHON_BIN="python3"
if [ -x "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
    PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
fi

# Run the FastAPI backend (serves the built frontend from frontend/dist)
exec "$PYTHON_BIN" -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
