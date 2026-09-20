"""
FastAPI Real-Time Deepfake Detection & In-Call Prevention Server.

Endpoints:
- WebSocket /ws/audio-stream: Live 16kHz PCM streaming inference & telemetry.
- POST /api/analyze-file: Multi-track file upload forensic analysis.
- GET /api/samples: Pre-loaded benchmark audio samples (authentic & synthetic).
- POST /api/verify-otp: Out-of-band challenge resolution.
- POST /api/quarantine: Immediate call termination & line isolation.
- GET /api/audit-log: Real-time incident forensic stream.
"""

import os
import io
import time
import uuid
import json
import logging
import numpy as np
import soundfile as sf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.pipeline.prevention import PreventionManager
from backend.pipeline.stream_processor import StreamProcessor
from backend.models.detector import DeepfakeDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deepfake-backend")

app = FastAPI(
    title="Real-Time Audio Deepfake Detection & Prevention API",
    version="1.0.0",
    description="SIH Audio Anti-Spoofing & In-Call Defense Platform",
)

# Enable CORS for local development and operator dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Prevention Manager & Shared Detector instance
prevention_manager = PreventionManager()
global_detector = DeepfakeDetector()

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "demo_audio", "samples")


class VerifyOTPRequest(BaseModel):
    session_id: str
    otp_code: str


class QuarantineRequest(BaseModel):
    session_id: str
    reason: Optional[str] = "Operator terminated line due to critical deepfake threat"


class ChallengeRequest(BaseModel):
    session_id: str
    trigger_risk: float
    reason: str


class SetModelRequest(BaseModel):
    model: str  # 'aasist' or 'rawnet'


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Audio Deepfake Detection Engine",
        "version": "1.0.0",
        "timestamp": time.time(),
        "active_model": global_detector.model_type.upper(),
        "engine": "3-Branch Ensemble (Wav2Vec2 + Phase ResNet + Bio MLP)",
        "device": str(global_detector.device),
        "target_latency_ms": "<50ms",
    }


@app.post("/api/set-model")
def set_model(req: SetModelRequest):
    global_detector.set_model_type(req.model)
    return {
        "success": True,
        "active_model": global_detector.model_type.upper(),
        "device": str(global_detector.device),
    }


@app.get("/api/samples")
def get_samples():
    """Lists preloaded benchmark audio samples for zero-setup demonstration."""
    sample_manifest = [
        {
            "id": "authentic_human_english",
            "name": "Authentic Human Voice (English)",
            "filename": "authentic_human_english.wav",
            "is_deepfake": False,
            "description": "Natural vocal fold micro-jitter, room acoustics (-36dB), human breathing cadence.",
            "url": "/api/audio/authentic_human_english.wav",
        },
        {
            "id": "authentic_human_indian_accent",
            "name": "Authentic Human Voice (Indian Accent)",
            "filename": "authentic_human_indian_accent.wav",
            "is_deepfake": False,
            "description": "Natural Indian English prosodic cadence, vocal fold jitter, room reverberation.",
            "url": "/api/audio/authentic_human_indian_accent.wav",
        },
        {
            "id": "authentic_telephone_g711",
            "name": "Authentic Voice (Telephone G.711 / AMR)",
            "filename": "authentic_telephone_g711.wav",
            "is_deepfake": False,
            "description": "Authentic speech through 300Hz-3400Hz telephone bandpass filter.",
            "url": "/api/audio/authentic_telephone_g711.wav",
        },
        {
            "id": "deepfake_hifi_gan",
            "name": "Neural Deepfake (HiFi-GAN Vocoder)",
            "filename": "deepfake_hifi_gan.wav",
            "is_deepfake": True,
            "description": "Severe high-frequency phase dispersion, flattened pitch variance, pristine silence.",
            "url": "/api/audio/deepfake_hifi_gan.wav",
        },
        {
            "id": "deepfake_rvc_voice_clone",
            "name": "RVC Voice Conversion Clone",
            "filename": "deepfake_rvc_voice_clone.wav",
            "is_deepfake": True,
            "description": "Voice conversion phase jumps, unnatural boundary clipping, pristine room disconnect.",
            "url": "/api/audio/deepfake_rvc_voice_clone.wav",
        },
    ]
    return sample_manifest


@app.get("/api/audio/{filename}")
def serve_audio_file(filename: str):
    file_path = os.path.join(SAMPLES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Sample audio file not found")
    return FileResponse(file_path, media_type="audio/wav")


@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...), telephony_mode: bool = Form(False)):
    """
    Accepts an uploaded audio file and performs complete forensic deepfake analysis.
    """
    contents = await file.read()
    try:
        audio_data, sample_rate = sf.read(io.BytesIO(contents))
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)  # Convert to mono
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            import scipy.signal
            num_samples = int(len(audio_data) * 16000 / sample_rate)
            audio_data = scipy.signal.resample(audio_data, num_samples)
            sample_rate = 16000
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode audio file: {str(e)}")

    analysis = global_detector.analyze_audio(
        audio_data.astype(np.float32),
        sample_rate=sample_rate,
        apply_telephony=telephony_mode,
    )

    # Downsample waveform for visual preview
    step = max(1, len(audio_data) // 128)
    preview = audio_data[::step][:128].tolist()

    return {
        "filename": file.filename,
        "duration_sec": round(len(audio_data) / sample_rate, 2),
        "analysis": analysis,
        "waveform_preview": preview,
    }


@app.post("/api/trigger-challenge")
def trigger_challenge(req: ChallengeRequest):
    record = prevention_manager.issue_challenge(
        session_id=req.session_id,
        trigger_risk=req.trigger_risk,
        reason=req.reason,
    )
    return record


@app.post("/api/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    result = prevention_manager.verify_challenge(req.session_id, req.otp_code)
    return result


@app.post("/api/quarantine")
def quarantine_call(req: QuarantineRequest):
    result = prevention_manager.quarantine_session(req.session_id, req.reason)
    return result


@app.get("/api/audit-log")
def get_audit_log():
    return prevention_manager.get_audit_log()


@app.websocket("/ws/audio-stream")
async def websocket_audio_stream(websocket: WebSocket):
    """
    Bi-directional streaming WebSocket endpoint.
    Accepts:
      - Binary frames: 16kHz PCM audio bytes
      - Text frames (JSON): configuration commands (e.g. set_telephony, reset, ping)
    Returns:
      - Real-time detection telemetry JSON every 500ms
    """
    await websocket.accept()
    session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
    processor = StreamProcessor(
        session_id=session_id,
        prevention_manager=prevention_manager,
        detector=global_detector,
        sample_rate=16000,
        window_duration=2.0,
        hop_duration=0.5,
    )

    prevention_manager.log_event(
        event_type="CALL_CONNECTED",
        session_id=session_id,
        details=f"VoIP audio interceptor stream attached. Live biometric analysis active.",
        severity="INFO",
    )

    # Send initial session handshake
    await websocket.send_text(json.dumps({
        "type": "HANDSHAKE",
        "session_id": session_id,
        "sample_rate": 16000,
        "window_duration": 2.0,
        "hop_duration": 0.5,
    }))

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                telemetry = processor.ingest_pcm_bytes(message["bytes"])
                if telemetry:
                    telemetry["type"] = "TELEMETRY"
                    await websocket.send_text(json.dumps(telemetry))

            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    cmd = data.get("command")

                    if cmd == "SET_TELEPHONY":
                        enabled = bool(data.get("enabled", False))
                        processor.set_telephony_mode(enabled)
                        await websocket.send_text(json.dumps({
                            "type": "CONFIG_ACK",
                            "telephony_mode": enabled,
                        }))

                    elif cmd == "RESET_BUFFER":
                        processor.threat_aggregator.reset()
                        processor.is_frozen = False
                        processor.challenge_triggered = False
                        await websocket.send_text(json.dumps({
                            "type": "RESET_ACK",
                            "session_id": session_id,
                        }))

                    elif cmd == "PING":
                        await websocket.send_text(json.dumps({"type": "PONG", "timestamp": time.time()}))

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        prevention_manager.log_event(
            event_type="CALL_DISCONNECTED",
            session_id=session_id,
            details="Audio stream interceptor terminated session.",
            severity="INFO",
        )
        logger.info(f"WebSocket session disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {e}")


# Mount production frontend build if available
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


