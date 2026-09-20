#!/usr/bin/env bash
# Real-Time Audio Deepfake Detection & In-Call Prevention System (SIH)
# Launcher script

set -e

PORT=${PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

echo "================================================================="
echo "  AEGIS VOICE-SENTINEL: Audio Deepfake Detection & Defense (SIH) "
echo "================================================================="
echo "Starting FastAPI Backend Engine on http://localhost:$PORT..."
echo "Features: LFCC + High-Frequency Phase Analysis + CNN-BiLSTM"
echo "Target Latency: < 50ms per frame | G.711 Telephony Codec Robust"
echo "================================================================="

# Check python demo samples exist, generate if needed
if [ ! -f "backend/demo_audio/samples/authentic_human_english.wav" ]; then
    echo "Generating demo audio benchmarks..."
    python3 backend/demo_audio/generate_samples.py
fi

# Run FastAPI backend (which also serves the frontend on http://localhost:8000)
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT --reload
