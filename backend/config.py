"""
Central Configuration for AEGIS Voice-Sentinel.

Every tunable value is sourced from environment variables (with safe defaults for
local development). Deployments for Government of India (MHA / I4C / DoT / RBI)
MUST set production values via environment — never by editing source code.

Usage:
    from backend.config import settings
    settings.prevention.challenge_threshold

A `.env` file at the project root is loaded automatically (python-dotenv).
See `.env.example` for the full documented list.
"""

import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env_list(name: str, default: str) -> List[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class AudioSettings:
    sample_rate: int = _env_int("AEGIS_SAMPLE_RATE", 16000)
    window_duration: float = _env_float("AEGIS_WINDOW_DURATION", 2.0)
    hop_duration: float = _env_float("AEGIS_HOP_DURATION", 0.5)
    # Speech-band filter edges
    highpass_hz: float = _env_float("AEGIS_HIGHPASS_HZ", 80.0)
    lowpass_hz: float = _env_float("AEGIS_LOWPASS_HZ", 7500.0)
    # VAD silence gates
    silence_rms: float = _env_float("AEGIS_SILENCE_RMS", 0.008)
    silence_speech_ratio: float = _env_float("AEGIS_SILENCE_SPEECH_RATIO", 0.12)
    silence_speech_ratio_hard: float = _env_float("AEGIS_SILENCE_SPEECH_RATIO_HARD", 0.04)
    silence_peak: float = _env_float("AEGIS_SILENCE_PEAK", 0.012)


@dataclass
class RiskThresholds:
    """Classification & prevention thresholds (0-100 risk scale)."""
    critical: float = _env_float("AEGIS_RISK_CRITICAL", 75.0)          # >= CRITICAL_SYNTHETIC
    suspicious: float = _env_float("AEGIS_RISK_SUSPICIOUS", 40.0)      # >= SUSPICIOUS_ANOMALY
    anomaly_flag: float = _env_float("AEGIS_RISK_ANOMALY_FLAG", 50.0)  # anomaly flagging floor
    # Prevention challenge triggers
    challenge_smoothed: float = _env_float("AEGIS_CHALLENGE_SMOOTHED", 75.0)
    challenge_instant: float = _env_float("AEGIS_CHALLENGE_INSTANT", 88.0)
    challenge_instant_floor: float = _env_float("AEGIS_CHALLENGE_INSTANT_FLOOR", 50.0)
    # Dossier / legal determination
    dossier_deepfake: float = _env_float("AEGIS_DOSSIER_DEEPFAKE", 60.0)


@dataclass
class ConsensusSettings:
    """
    Multi-model decision policy. A government/forensic system must NEVER output a
    confident verdict when its engines disagree — it must abstain (INCONCLUSIVE)
    and escalate to a human analyst.
    """
    enabled: bool = _env_bool("AEGIS_CONSENSUS_ENABLED", True)
    # If |score_a - score_b| exceeds this (0-100), models are deemed in conflict
    disagreement_margin: float = _env_float("AEGIS_CONSENSUS_DISAGREEMENT", 30.0)
    # Mean score must exceed this to call FAKE, or fall below (100 - inconclusive_band ...)
    fake_threshold: float = _env_float("AEGIS_CONSENSUS_FAKE", 70.0)
    real_threshold: float = _env_float("AEGIS_CONSENSUS_REAL", 35.0)
    # Scores inside this band around no-decision => INCONCLUSIVE
    inconclusive_low: float = _env_float("AEGIS_CONSENSUS_INCONCLUSIVE_LOW", 35.0)
    inconclusive_high: float = _env_float("AEGIS_CONSENSUS_INCONCLUSIVE_HIGH", 70.0)
    # Engine weights for the fused score (normalize internally).
    # Tune on a held-out dev set: give stronger engines more weight.
    weight_aasist: float = _env_float("AEGIS_CONSENSUS_W_AASIST", 0.5)
    weight_rawnet: float = _env_float("AEGIS_CONSENSUS_W_RAWNET", 0.5)


@dataclass
class DatabaseSettings:
    """Evidence persistence. 'memory' keeps legacy in-process behaviour (dev only)."""
    backend: str = os.getenv("AEGIS_DB_BACKEND", "sqlite")  # sqlite | postgres | memory
    sqlite_path: str = os.getenv("AEGIS_DB_SQLITE_PATH",
                                 os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                              "data", "aegis_evidence.db"))
    postgres_dsn: str = os.getenv("AEGIS_DB_POSTGRES_DSN", "")
    echo: bool = _env_bool("AEGIS_DB_ECHO", False)


@dataclass
class AuthSettings:
    """Optional API-key gate for operator endpoints (required posture for prod)."""
    enabled: bool = _env_bool("AEGIS_AUTH_ENABLED", False)
    api_key: str = os.getenv("AEGIS_API_KEY", "")
    # Endpoints exempt from the API-key requirement
    exempt_paths: List[str] = field(default_factory=lambda: [
        "/api/health", "/api/audit-log", "/docs", "/openapi.json", "/redoc",
    ])


@dataclass
class RateLimitSettings:
    """Simple in-memory sliding-window rate limiter (per client IP)."""
    enabled: bool = _env_bool("AEGIS_RATE_LIMIT_ENABLED", True)
    otp_verify_per_minute: int = _env_int("AEGIS_RATE_OTP_PER_MIN", 10)
    analyze_per_minute: int = _env_int("AEGIS_RATE_ANALYZE_PER_MIN", 20)
    challenge_per_minute: int = _env_int("AEGIS_RATE_CHALLENGE_PER_MIN", 30)


@dataclass
class WSSettings:
    """WebSocket hardening limits."""
    max_frame_bytes: int = _env_int("AEGIS_WS_MAX_FRAME_BYTES", 65536)  # 64KB (~2s of 16-bit PCM)
    max_sessions: int = _env_int("AEGIS_WS_MAX_SESSIONS", 64)
    receive_timeout_s: float = _env_float("AEGIS_WS_RECV_TIMEOUT", 300.0)


@dataclass
class PreventionSettings:
    challenge_ttl_seconds: int = _env_int("AEGIS_CHALLENGE_TTL", 180)
    max_otp_attempts: int = _env_int("AEGIS_MAX_OTP_ATTEMPTS", 3)
    otp_length: int = _env_int("AEGIS_OTP_LENGTH", 6)
    audit_log_size: int = _env_int("AEGIS_AUDIT_LOG_SIZE", 100)
    threat_window: int = _env_int("AEGIS_THREAT_WINDOW", 8)
    threat_threshold_critical: float = _env_float("AEGIS_THREAT_THRESHOLD_CRITICAL", 80.0)
    idle_hold_frames: int = _env_int("AEGIS_IDLE_HOLD_FRAMES", 12)
    # ThreatAggregator temporal dynamics (tunable smoothing behaviour)
    idle_hold_decay: float = _env_float("AEGIS_AGG_IDLE_HOLD_DECAY", 0.995)
    idle_decay: float = _env_float("AEGIS_AGG_IDLE_DECAY", 0.94)
    idle_peak_decay: float = _env_float("AEGIS_AGG_IDLE_PEAK_DECAY", 0.95)
    peak_hold_floor: float = _env_float("AEGIS_AGG_PEAK_HOLD_FLOOR", 40.0)
    peak_blend_keep: float = _env_float("AEGIS_AGG_PEAK_BLEND_KEEP", 0.85)
    ewma_base: float = _env_float("AEGIS_AGG_EWMA_BASE", 1.25)


@dataclass
class ServerSettings:
    host: str = os.getenv("AEGIS_HOST", "0.0.0.0")
    port: int = _env_int("AEGIS_PORT", 8000)
    # Security: NEVER use "*" with allow_credentials=True in production.
    cors_origins: List[str] = field(default_factory=lambda: _env_list(
        "AEGIS_CORS_ORIGINS",
        "*" if os.getenv("AEGIS_ENV", "dev") != "prod" else "",
    ))
    reload: bool = _env_bool("AEGIS_RELOAD", False)
    # Uploaded file analysis guard rails
    max_upload_mb: float = _env_float("AEGIS_MAX_UPLOAD_MB", 25.0)
    max_analyze_duration_s: float = _env_float("AEGIS_MAX_ANALYZE_DURATION_S", 300.0)


@dataclass
class ModelSettings:
    device: str = os.getenv("AEGIS_DEVICE", "auto")  # auto | cpu | cuda | mps
    default_model: str = os.getenv("AEGIS_DEFAULT_MODEL", "aasist")
    analysis_window_s: float = _env_float("AEGIS_ANALYSIS_WINDOW_S", 2.0)
    risk_floor: float = _env_float("AEGIS_RISK_FLOOR", 4.0)
    risk_ceiling: float = _env_float("AEGIS_RISK_CEILING", 99.4)
    idle_risk: float = _env_float("AEGIS_IDLE_RISK", 6.0)
    # 3-Branch Ensemble mixing weights (was hardcoded [0.50, 0.30, 0.20])
    ensemble_weights: List[float] = field(default_factory=lambda: [
        _env_float("AEGIS_ENSEMBLE_W1", 0.50),
        _env_float("AEGIS_ENSEMBLE_W2", 0.30),
        _env_float("AEGIS_ENSEMBLE_W3", 0.20),
    ])


@dataclass
class PathsSettings:
    """Filesystem locations (overridable for read-only / containerised deployments)."""
    project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_dir: str = os.getenv(
        "AEGIS_SAMPLES_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "backend", "demo_audio", "samples"))
    benchmark_report: str = os.getenv(
        "AEGIS_BENCHMARK_REPORT",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "full_benchmark_report.json"))
    data_dir: str = os.getenv("AEGIS_DATA_DIR",
                              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                           "data"))


@dataclass
class DossierSettings:
    agency: str = os.getenv("AEGIS_AGENCY", "Indian Cyber Crime Coordination Centre (I4C) / State Cyber Cell")
    police_station: str = os.getenv("AEGIS_POLICE_STATION", "Cyber Crime Police Station, Special Cell")
    officer: str = os.getenv("AEGIS_OFFICER", "Inspector (Cyber Forensic Division)")
    dossier_version: str = os.getenv("AEGIS_DOSSIER_VERSION", "1.0.0")


@dataclass
class STTSettings:
    language: str = os.getenv("AEGIS_STT_LANGUAGE", "en-IN")
    engine: str = os.getenv("AEGIS_STT_ENGINE", "google")
    api_key: str = os.getenv("AEGIS_STT_API_KEY", "")


@dataclass
class Settings:
    env: str = os.getenv("AEGIS_ENV", "dev")
    audio: AudioSettings = field(default_factory=AudioSettings)
    risk: RiskThresholds = field(default_factory=RiskThresholds)
    consensus: ConsensusSettings = field(default_factory=ConsensusSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    auth: AuthSettings = field(default_factory=AuthSettings)
    rate_limit: RateLimitSettings = field(default_factory=RateLimitSettings)
    ws: WSSettings = field(default_factory=WSSettings)
    prevention: PreventionSettings = field(default_factory=PreventionSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    paths: PathsSettings = field(default_factory=PathsSettings)
    dossier: DossierSettings = field(default_factory=DossierSettings)
    stt: STTSettings = field(default_factory=STTSettings)

    def validate(self) -> List[str]:
        """Deployment sanity checks. Returns list of human-readable problems."""
        problems: List[str] = []
        if self.env == "prod":
            if not self.server.cors_origins or self.server.cors_origins == ["*"]:
                problems.append("AEGIS_ENV=prod requires AEGIS_CORS_ORIGINS (no wildcards).")
            if not self.auth.enabled or not self.auth.api_key:
                problems.append("AEGIS_ENV=prod requires AEGIS_AUTH_ENABLED=1 and AEGIS_API_KEY.")
            if self.db.backend == "memory":
                problems.append("AEGIS_ENV=prod must persist evidence: set AEGIS_DB_BACKEND=sqlite|postgres.")
            if self.server.reload:
                problems.append("AEGIS_RELOAD must be 0 in prod.")
        if self.auth.enabled and not self.auth.api_key:
            problems.append("AEGIS_AUTH_ENABLED=1 but AEGIS_API_KEY is empty.")
        if self.db.backend == "postgres" and not self.db.postgres_dsn:
            problems.append("AEGIS_DB_BACKEND=postgres but AEGIS_DB_POSTGRES_DSN is empty.")
        w = self.model.ensemble_weights
        if abs(sum(w) - 1.0) > 0.05:
            problems.append(f"Ensemble weights must sum to ~1.0 (got {w}).")
        return problems


settings = Settings()
