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
import secrets
import logging
import numpy as np
import soundfile as sf
from collections import defaultdict, deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Deque

from backend.pipeline.audit_store import AuditStore
from backend.pipeline.prevention import PreventionManager
from backend.pipeline.stream_processor import StreamProcessor
from backend.models.detector import DeepfakeDetector
from backend.pipeline.forensic_dossier import generate_bsa_certificate, verify_certificate
from backend.pipeline.dossier_pdf import render_pdf_bytes, render_html
from backend.pipeline.audio_intelligence import transcribe_audio_data, analyze_speech_semantics
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deepfake-backend")

app = FastAPI(
    title="Real-Time Audio Deepfake Detection & Prevention API",
    version="1.0.0",
    description="SIH Audio Anti-Spoofing & In-Call Defense Platform",
)

# Enable CORS for local development and operator dashboard.
# Production (AEGIS_ENV=prod) restricts origins via AEGIS_CORS_ORIGINS env var.
if settings.env == "prod" and not settings.server.cors_origins:
    raise RuntimeError(
        "AEGIS_ENV=prod requires AEGIS_CORS_ORIGINS to be set (comma-separated dashboard origins). "
        "Wildcard CORS with credentials is not permitted for government deployments."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins or ["https://aegis.gov.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Security middleware: optional API-key gate (prod posture) + rate limiting
# ---------------------------------------------------------------------------
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(key: str, limit_per_minute: int) -> bool:
    """Sliding-window limiter. Returns True if allowed."""
    if not settings.rate_limit.enabled or limit_per_minute <= 0:
        return True
    now = time.time()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= limit_per_minute:
        return False
    bucket.append(now)
    return True


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path

    # 1) Optional API-key authentication (exempting health/docs)
    if settings.auth.enabled and not any(path == p or path.startswith(p + "/") for p in settings.auth.exempt_paths):
        key = request.headers.get("x-api-key", "")
        if not settings.auth.api_key or not secrets.compare_digest(key, settings.auth.api_key):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing X-API-Key"})

    # 2) Rate limiting on abuse-prone endpoints
    ip = _client_ip(request)
    if path.startswith("/api/verify-otp") and not _rate_limit(f"otp:{ip}", settings.rate_limit.otp_verify_per_minute):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Slow down."})
    if path.startswith("/api/analyze-file") and not _rate_limit(f"analyze:{ip}", settings.rate_limit.analyze_per_minute):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Slow down."})
    if path.startswith("/api/trigger-challenge") and not _rate_limit(f"chal:{ip}", settings.rate_limit.challenge_per_minute):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Slow down."})

    return await call_next(request)


# Global Prevention Manager, Evidence Store & Shared Detector instance
prevention_manager = PreventionManager()
evidence_store = prevention_manager.store  # shared AuditStore (hash-chained)
global_detector = DeepfakeDetector()

SAMPLES_DIR = settings.paths.samples_dir

# Active WebSocket stream registry (for concurrent-session capping)
_ws_sessions: set = set()

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


class DossierRequest(BaseModel):
    session_id: str
    threat_score: float
    status: str
    forensics: Dict[str, Any]
    anomalies: Optional[List[str]] = []
    model_consensus: Optional[Dict[str, Any]] = None
    case_metadata: Optional[Dict[str, Any]] = None
    transcript: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Audio Deepfake Detection Engine",
        "version": "1.0.0",
        "env": settings.env,
        "timestamp": time.time(),
        "active_model": global_detector.model_type.upper(),
        "engine": "3-Branch Ensemble (Wav2Vec2 + Phase ResNet + Bio MLP)",
        "device": str(global_detector.device),
        "target_latency_ms": "<50ms",
    }


VALID_MODELS = {"ensemble", "aasist", "rawnet"}


@app.post("/api/set-model")
def set_model(req: SetModelRequest):
    if req.model.lower() not in VALID_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{req.model}'. Valid options: {sorted(VALID_MODELS)}",
        )
    global_detector.set_model_type(req.model)
    return {
        "success": True,
        "active_model": global_detector.model_type.upper(),
        "device": str(global_detector.device),
    }


@app.post("/api/generate-dossier")
def create_forensic_dossier(req: DossierRequest):
    """
    Generates a Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 compliant
    Forensic Evidence Certificate for Indian Law Enforcement Agencies (LEAs).
    """
    certificate = generate_bsa_certificate(
        session_id=req.session_id,
        threat_score=req.threat_score,
        status=req.status,
        forensics=req.forensics,
        anomalies=req.anomalies or [],
        model_consensus=req.model_consensus or {},
        case_metadata=req.case_metadata,
        transcript=req.transcript,
        ai_analysis=req.ai_analysis,
    )
    # Persist for evidence retrieval (survives restarts, hash-verifiable metadata)
    evidence_store.save_dossier(certificate["legal_header"]["dossier_id"],
                                req.session_id, certificate)
    prevention_manager.log_event(
        event_type="DOSSIER_GENERATED",
        session_id=req.session_id,
        details=f"Forensic dossier {certificate['legal_header']['dossier_id']} generated and sealed.",
        severity="INFO",
    )
    return certificate


@app.get("/api/samples")
def get_samples():
    """
    Benchmark sample manifest — REAL recordings only.

    Sources (built via scripts/build_real_demo_samples.py):
      - Authentic speech : large_benchmark_data/real (human YouTube speech)
      - Authentic telephony: scam_call_data/processed/normal (real call audio)
      - SOTA deepfakes   : large_benchmark_data/fake (ElevenLabs / Play.ht / HiFi-GAN)
      - Scam calls       : scam_call_data/processed/scam (reported scam recordings)

    Entries are served only if the file exists on disk, so deployments can
    add/remove scenario WAVs without code changes.
    """
    sample_manifest = [
        # --- Real reported scam calls ---
        {
            "id": "scam_digital_arrest",
            "name": "🚨 [SCAM] Digital Arrest (Real Reported Call)",
            "filename": "real_scam_digital_arrest.wav",
            "is_deepfake": True,
            "category": "INDIAN_SCAM_CALL",
            "description": "Real reported scam recording: caller impersonating police/CBI applying psychological coercion (digital arrest extortion pattern).",
            "url": "/api/audio/real_scam_digital_arrest.wav",
        },
        {
            "id": "scam_customs_narcotics",
            "name": "🚨 [SCAM] Customs / Narcotics Threat (Real Reported Call)",
            "filename": "real_scam_customs_narcotics.wav",
            "is_deepfake": True,
            "category": "INDIAN_SCAM_CALL",
            "description": "Real reported scam recording: fraudulent customs official claiming contraband intercepted in victim's parcel.",
            "url": "/api/audio/real_scam_customs_narcotics.wav",
        },
        {
            "id": "scam_bank_kyc_fraud",
            "name": "🚨 [SCAM] Bank KYC Expiry Phish (Real Reported Call)",
            "filename": "real_scam_kyc_fraud.wav",
            "is_deepfake": True,
            "category": "INDIAN_SCAM_CALL",
            "description": "Real reported scam recording: high-pressure banking fraud claiming account/card suspension.",
            "url": "/api/audio/real_scam_kyc_fraud.wav",
        },
        # --- SOTA synthetic vocoders & voice clones (real generator output) ---
        {
            "id": "deepfake_elevenlabs",
            "name": "🔴 [DEEPFAKE] ElevenLabs v3 (SOTA TTS)",
            "filename": "real_deepfake_elevenlabs.wav",
            "is_deepfake": True,
            "category": "AI_VOICE_CLONE",
            "description": "Real output from ElevenLabs v3 neural TTS — SOTA commercial voice synthesis.",
            "url": "/api/audio/real_deepfake_elevenlabs.wav",
        },
        {
            "id": "deepfake_playht",
            "name": "🔴 [DEEPFAKE] Play.ht (SOTA TTS)",
            "filename": "real_deepfake_playht.wav",
            "is_deepfake": True,
            "category": "AI_VOICE_CLONE",
            "description": "Real output from Play.ht neural TTS.",
            "url": "/api/audio/real_deepfake_playht.wav",
        },
        {
            "id": "deepfake_hifigan",
            "name": "🔴 [DEEPFAKE] HiFi-GAN (Neural Vocoder)",
            "filename": "real_deepfake_hifigan.wav",
            "is_deepfake": True,
            "category": "AI_VOICE_CLONE",
            "description": "Real HiFi-GAN neural vocoder output — high-frequency phase dispersion artifact class.",
            "url": "/api/audio/real_deepfake_hifigan.wav",
        },
        # --- Authentic human benchmarks (real recordings) ---
        {
            "id": "authentic_human_speech",
            "name": "🟢 [AUTHENTIC] Real Human Speech (Benchmark Clip)",
            "filename": "real_authentic_speech.wav",
            "is_deepfake": False,
            "category": "AUTHENTIC_HUMAN",
            "description": "Real human speech recording from the in-repo authentic benchmark corpus.",
            "url": "/api/audio/real_authentic_speech.wav",
        },
        {
            "id": "authentic_human_accent",
            "name": "🟢 [AUTHENTIC] Real Human Speech #2",
            "filename": "real_authentic_indian_accent.wav",
            "is_deepfake": False,
            "category": "AUTHENTIC_HUMAN",
            "description": "Second real human speech recording — natural prosody, breath cadence, room acoustics.",
            "url": "/api/audio/real_authentic_indian_accent.wav",
        },
        {
            "id": "authentic_telephony",
            "name": "🟢 [AUTHENTIC] Real Citizen Phone Call",
            "filename": "real_authentic_telephony.wav",
            "is_deepfake": False,
            "category": "AUTHENTIC_HUMAN",
            "description": "Real telephone call audio (telephony band-limitation present) — the hardest legitimate class.",
            "url": "/api/audio/real_authentic_telephony.wav",
        },
    ]
    # Only advertise samples that actually exist on disk
    available = [s for s in sample_manifest if os.path.exists(os.path.join(SAMPLES_DIR, s["filename"]))]
    return available


@app.get("/api/audio/{filename}")
def serve_audio_file(filename: str):
    # Defense-in-depth: restrict to plain .wav filenames inside SAMPLES_DIR
    if "/" in filename or "\\" in filename or ".." in filename or not filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Invalid sample filename")
    file_path = os.path.abspath(os.path.join(SAMPLES_DIR, filename))
    if not file_path.startswith(os.path.abspath(SAMPLES_DIR) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid sample path")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Sample audio file not found")
    return FileResponse(file_path, media_type="audio/wav")


@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...), telephony_mode: bool = Form(False)):
    """
    Accepts an uploaded audio file and performs complete forensic deepfake analysis.
    """
    contents = await file.read()
    if len(contents) > int(settings.server.max_upload_mb * 1024 * 1024):
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.server.max_upload_mb} MB analysis limit",
        )
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

    # Forensic file analysis: score ALL 2s windows (75% overlap), not just the final one.
    # Previously only the last window was analyzed, so files ending in silence
    # (e.g. 60s scam calls with a quiet tail) were misreported as IDLE / 0% risk.
    win = int(2.0 * sample_rate)
    hop = win // 4  # 0.5s hop -> 75% overlap
    scored = []
    if len(audio_data) < win:
        scored.append(global_detector.analyze_audio(
            audio_data.astype(np.float32), sample_rate=sample_rate, apply_telephony=telephony_mode))
    else:
        for start in range(0, len(audio_data) - win + 1, hop):
            w = audio_data[start : start + win]
            res = global_detector.analyze_audio(w.astype(np.float32), sample_rate=sample_rate,
                                                apply_telephony=telephony_mode)
            if not res.get("is_idle", False):
                scored.append(res)
    if not scored:
        scored = [global_detector.analyze_audio(
            audio_data[-win:].astype(np.float32), sample_rate=sample_rate, apply_telephony=telephony_mode)]

    # Aggregate: max window risk (forensic worst-case) + mean over voiced windows
    max_risk = max(s["risk_score"] for s in scored)
    mean_risk = round(sum(s["risk_score"] for s in scored) / len(scored), 1)
    worst = max(scored, key=lambda s: s["risk_score"])
    analysis = dict(worst)
    analysis["window_risk_max"] = max_risk
    analysis["window_risk_mean"] = mean_risk
    analysis["windows_scored"] = len(scored)
    analysis["windows_total"] = max(1, (len(audio_data) - win) // hop + 1) if len(audio_data) >= win else 1
    analysis["status"] = (
        "CRITICAL_SYNTHETIC" if max_risk >= settings.risk.critical
        else "SUSPICIOUS_ANOMALY" if max_risk >= settings.risk.suspicious
        else "AUTHENTIC_HUMAN"
    )

    duration_s = len(audio_data) / sample_rate
    if duration_s > settings.server.max_analyze_duration_s:
        raise HTTPException(
            status_code=413,
            detail=f"Audio duration {duration_s:.0f}s exceeds {settings.server.max_analyze_duration_s:.0f}s limit",
        )

    # Transcribe speech to text via true STT decoding
    stt_result = transcribe_audio_data(audio_data, sample_rate)

    # Perform AI Semantic Threat & Deception Analysis
    ai_analysis = analyze_speech_semantics(
        transcript=stt_result.get("text", ""),
        acoustic_risk=analysis.get("risk_score", 0.0),
    )

    # Downsample waveform for visual preview
    step = max(1, len(audio_data) // 128)
    preview = audio_data[::step][:128].tolist()

    return {
        "filename": file.filename,
        "duration_sec": round(len(audio_data) / sample_rate, 2),
        "analysis": analysis,
        "waveform_preview": preview,
        "transcript": stt_result.get("text", ""),
        "stt_info": {
            "status": stt_result.get("status"),
            "word_count": stt_result.get("word_count", 0),
            "stt_engine": stt_result.get("stt_engine", "Google Web Speech STT"),
            "error": stt_result.get("error"),
        },
        "ai_analysis": ai_analysis,
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


@app.get("/api/audit-verify")
def verify_audit_chain():
    """
    Tamper-evidence check: recomputes the full SHA-256 hash chain of the audit
    trail. Returns valid=false + the breaking event if any record was altered,
    inserted, or deleted (Section 63 BSA 2023 chain-of-custody support).
    """
    return evidence_store.verify_chain()


@app.get("/api/dossiers/{dossier_id}")
def get_dossier(dossier_id: str):
    """Retrieves a persisted forensic dossier by its ID (evidence retrieval)."""
    dossier = evidence_store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return dossier


@app.get("/api/dossiers/{dossier_id}/verify")
def verify_dossier(dossier_id: str):
    """
    Verifies the HMAC seal of a persisted dossier. Any post-issuance alteration
    of the certificate body invalidates the seal. (The officer's DSC/eSign
    remains the legal Section 63(4) signature step on top of this seal.)
    """
    dossier = evidence_store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    result = verify_certificate(dossier)
    return {"dossier_id": dossier_id, **result}


@app.get("/api/dossiers/{dossier_id}/export")
def export_dossier(dossier_id: str, format: str = "pdf"):
    """
    Export a persisted dossier as a print-ready document.
    format=pdf uses reportlab when installed; falls back to styled HTML
    (browser print-to-PDF) when it is not. format=html always returns HTML.
    """
    dossier = evidence_store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    fmt = format.lower()
    if fmt == "html":
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=render_html(dossier))
    pdf = render_pdf_bytes(dossier)
    if pdf is None:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=render_html(dossier))
    from fastapi.responses import Response
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dossier_id}.pdf"'},
    )


@app.get("/api/benchmark-report")
def get_benchmark_report():
    report_path = settings.paths.benchmark_report
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "pending", "message": "Benchmark report not yet generated."}


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
    # DoS hardening: cap concurrent streaming sessions
    if len(_ws_sessions) >= settings.ws.max_sessions:
        await websocket.close(code=1013, reason="Server at maximum concurrent sessions")
        return
    await websocket.accept()
    _ws_sessions.add(websocket)
    session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
    processor = StreamProcessor(
        session_id=session_id,
        prevention_manager=prevention_manager,
        detector=global_detector,
        sample_rate=settings.audio.sample_rate,
        window_duration=settings.audio.window_duration,
        hop_duration=settings.audio.hop_duration,
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
        "sample_rate": settings.audio.sample_rate,
        "window_duration": settings.audio.window_duration,
        "hop_duration": settings.audio.hop_duration,
    }))

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                pcm = message["bytes"]
                # Frame-size guard: reject oversized binary frames (DoS vector)
                if len(pcm) > settings.ws.max_frame_bytes:
                    await websocket.send_text(json.dumps({
                        "type": "ERROR", "detail":
                        f"Frame exceeds {settings.ws.max_frame_bytes} byte limit",
                    }))
                    continue
                try:
                    telemetry = processor.ingest_pcm_bytes(pcm)
                except Exception as proc_err:
                    # One bad frame must not kill the session
                    logger.warning(f"Frame processing error in {session_id}: {proc_err}")
                    await websocket.send_text(json.dumps({
                        "type": "ERROR", "detail": "Frame processing failed; stream continues",
                    }))
                    continue
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
                        processor.reset()
                        prevention_manager.resolve_challenge(session_id)
                        await websocket.send_text(json.dumps({
                            "type": "RESET_ACK",
                            "session_id": session_id,
                        }))
                        await websocket.send_text(json.dumps({
                            "type": "TELEMETRY",
                            "session_id": session_id,
                            "instant_risk": 0.0,
                            "smoothed_risk": 0.0,
                            "status": "IDLE_SILENCE",
                            "label": "MONITORING - AWAITING SPEECH",
                            "color": "slate",
                            "is_idle": True,
                            "anomalies": [],
                            "forensics": None,
                            "latency_ms": 0.0,
                            "waveform_preview": [],
                            "spectral_preview": [],
                            "is_frozen": False,
                            "challenge": None,
                            "timestamp": time.time(),
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
    finally:
        _ws_sessions.discard(websocket)


# Mount production frontend build if available
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
    )


