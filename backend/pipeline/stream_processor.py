"""
Real-Time Audio Ingestion & Chunking Layer.

- Handles streaming audio over WebSocket (16kHz PCM)
- Maintains sliding window buffer: 2.0s analysis window with 0.5s overlap
- Dispatches inference every 500ms (< 50ms execution)
- Coordinates with PreventionManager for automated threat responses
"""

import numpy as np
import time
from typing import Dict, Any, Optional

from backend.models.detector import DeepfakeDetector
from backend.pipeline.prevention import ThreatAggregator, PreventionManager


class StreamProcessor:
    """
    Session-level real-time audio stream ingestion and detection pipeline.
    """

    def __init__(
        self,
        session_id: str,
        prevention_manager: PreventionManager,
        detector: Optional[DeepfakeDetector] = None,
        sample_rate: int = 16000,
        window_duration: float = 2.0,  # 2.0 seconds window
        hop_duration: float = 0.5,     # 500ms hop step
        telephony_mode: bool = False,
    ):
        self.session_id = session_id
        self.prevention_manager = prevention_manager
        self.sample_rate = sample_rate
        self.window_samples = int(window_duration * sample_rate)
        self.hop_samples = int(hop_duration * sample_rate)
        self.telephony_mode = telephony_mode

        self.audio_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self.samples_since_last_eval = 0
        self.total_samples_received = 0

        self.detector = detector if detector is not None else DeepfakeDetector()
        self.threat_aggregator = ThreatAggregator(window_size=4, threshold_critical=80.0)
        self.is_frozen = False
        self.challenge_triggered = False

    def ingest_pcm_bytes(self, pcm_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Accepts raw 16-bit signed integer or float32 PCM bytes, buffers them,
        and triggers detection every hop_samples.
        """
        if len(pcm_bytes) == 0:
            return None

        # Determine format (int16 is 2 bytes per sample, float32 is 4 bytes)
        if len(pcm_bytes) % 2 == 0:
            int16_data = np.frombuffer(pcm_bytes, dtype=np.int16)
            float_data = int16_data.astype(np.float32) / 32768.0
        else:
            float_data = np.frombuffer(pcm_bytes[: len(pcm_bytes) - (len(pcm_bytes) % 4)], dtype=np.float32)

        return self.ingest_samples(float_data)

    def ingest_samples(self, samples: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Appends samples to sliding window buffer.
        If hop_samples have accumulated, runs analysis and returns telemetry.
        """
        n = len(samples)
        if n == 0:
            return None

        self.total_samples_received += n
        self.samples_since_last_eval += n

        # Slide buffer
        if n >= self.window_samples:
            self.audio_buffer = samples[-self.window_samples :].copy()
        else:
            self.audio_buffer = np.roll(self.audio_buffer, -n)
            self.audio_buffer[-n:] = samples

        # Check if hop interval reached and at least 1 second received
        if self.samples_since_last_eval >= self.hop_samples:
            self.samples_since_last_eval = 0
            if self.total_samples_received < self.sample_rate:
                return None
            return self.process_current_window()

        return None

    def process_current_window(self) -> Dict[str, Any]:
        """
        Executes deepfake analysis on current audio window.
        """
        # Only evaluate on actual samples received to avoid zero-padded silence artifacts
        valid_len = min(self.total_samples_received, self.window_samples)
        eval_buffer = self.audio_buffer[-valid_len:]

        # Run detection
        analysis = self.detector.analyze_audio(
            eval_buffer,
            sample_rate=self.sample_rate,
            apply_telephony=self.telephony_mode,
        )

        # Smooth threat score across temporal window
        instant_risk = analysis["risk_score"]
        is_idle = (analysis["status"] == "IDLE_SILENCE")
        smoothed_risk = self.threat_aggregator.update(instant_risk, is_idle=is_idle)
        analysis["smoothed_risk"] = smoothed_risk

        # In-Call Prevention Trigger (Sustained synthetic detection or instant high threat)
        challenge_info = None
        should_trigger = (smoothed_risk >= 75.0) or (instant_risk >= 88.0 and smoothed_risk >= 50.0)
        if should_trigger and not self.challenge_triggered:
            self.challenge_triggered = True
            self.is_frozen = True
            primary_reason = analysis["anomalies"][0] if analysis["anomalies"] else "High probability neural voice clone detected"
            challenge_info = self.prevention_manager.issue_challenge(
                session_id=self.session_id,
                trigger_risk=smoothed_risk,
                reason=primary_reason,
            )

        # Generate lightweight visualization telemetry for frontend
        # 1. Downsampled waveform for oscilloscope (64 points)
        step = max(1, len(self.audio_buffer) // 64)
        downsampled_wave = self.audio_buffer[::step][:64].tolist()

        # 2. FFT frequency spectrum magnitudes for waterfall (32 bands)
        fft_mag = np.abs(np.fft.rfft(self.audio_buffer[-512:]))[:32]
        fft_norm = (fft_mag / (np.max(fft_mag) + 1e-6)).tolist()

        return {
            "session_id": self.session_id,
            "instant_risk": instant_risk,
            "smoothed_risk": smoothed_risk,
            "status": analysis["status"],
            "label": analysis["label"],
            "color": analysis["color"],
            "anomalies": analysis["anomalies"],
            "forensics": analysis["forensics"],
            "latency_ms": analysis["latency_ms"],
            "waveform_preview": downsampled_wave,
            "spectral_preview": fft_norm,
            "is_frozen": self.is_frozen,
            "challenge": challenge_info,
            "timestamp": time.time(),
        }

    def set_telephony_mode(self, enabled: bool):
        self.telephony_mode = enabled
