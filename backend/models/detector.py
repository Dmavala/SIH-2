"""
End-to-End Deepfake Detection Engine with 3-Branch Ensemble & AASIST / RawNet.
Processes raw waveforms and phase spectrograms directly with hardware-calibrated VAD.

Models:
1. 3-Branch Ensemble (Wav2Vec2 SSL + Phase ResNet-18 + Temporal/Bio MLP) - Primary Engine
2. AASIST: Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks
3. RawNet2: Raw waveform CNN with Feature Map Scaling and Bi-GRU
4. Speech-Band VAD: Filters sub-80Hz laptop/fan rumble and verifies vocal energy
5. Explainable Forensic Telemetry: Pitch jitter, shimmer, phase dispersion, LFCC
"""

import os
import time
import numpy as np
import scipy.signal
import torch
from typing import Dict, Any, Optional

from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2
from backend.features.vad import compute_speech_ratio
from backend.features.lfcc import extract_lfcc
from backend.features.acoustics import extract_acoustic_forensics
from voice_cloning_detector.config import CHECKPOINTS_DIR, SAMPLE_RATE
from voice_cloning_detector.models.ensemble import EnsembleVoiceCloningDetector


def filter_speech_band(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    4th order bandpass filter (80 Hz to 7500 Hz) to eliminate sub-80Hz laptop/mic mechanical rumble
    and ultra-high frequency soundcard noise.
    """
    if len(audio) < 512:
        return audio.astype(np.float32)
    sos = scipy.signal.butter(4, [80, min(7500, sr // 2 - 100)], btype="bandpass", fs=sr, output="sos")
    return scipy.signal.sosfilt(sos, audio).astype(np.float32)


class DeepfakeDetector:
    """
    End-to-end Audio Anti-Spoofing Engine powered by the 3-Branch Ensemble,
    AASIST (Graph Attention Network), and RawNet2.
    """

    def __init__(self, model_type: str = "ensemble", use_gpu: bool = True):
        self.model_type = model_type.lower()
        if use_gpu and torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif use_gpu and torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        # 1. Initialize 3-Branch Ensemble (Primary Detector)
        # Note: Ensemble uses CPU for Wav2Vec2 compatibility across all platforms
        self.ensemble = EnsembleVoiceCloningDetector(device=torch.device("cpu"))
        ckpt_path = os.path.join(CHECKPOINTS_DIR, "best_model.pt")
        if os.path.exists(ckpt_path):
            ckpt = torch.load(ckpt_path, map_location="cpu")
            self.ensemble.load_state_dict(ckpt["model_state_dict"], strict=False)
            print(f"[DeepfakeDetector] Loaded 3-Branch Ensemble weights from {ckpt_path}")
        self.ensemble.eval()

        # 2. Initialize AASIST & RawNet2 fallback models
        self.aasist = AASIST(sample_rate=16000).to(self.device).eval()
        self.rawnet = RawNet2(sample_rate=16000).to(self.device).eval()

        self._warmup()

    def _warmup(self):
        with torch.no_grad():
            dummy = torch.randn(1, 32000, device=self.device)
            _ = self.aasist(dummy)
            _ = self.rawnet(dummy)
            if self.device.type == "mps":
                torch.mps.synchronize()

    def set_model_type(self, model_type: str):
        if model_type.lower() in ["ensemble", "aasist", "rawnet"]:
            self.model_type = model_type.lower()

    def forward_raw_model(self, waveform_tensor: torch.Tensor) -> float:
        """Runs forward inference on AASIST or RawNet."""
        if self.model_type == "rawnet":
            return self.rawnet.predict_spoof_prob(waveform_tensor)
        else:
            return self.aasist.predict_spoof_prob(waveform_tensor)

    def analyze_audio(
        self,
        waveform: np.ndarray,
        sample_rate: int = 16000,
        apply_telephony: bool = False
    ) -> Dict[str, Any]:
        """
        Complete forensic analysis pipeline on an audio frame with VAD and strict verification.
        """
        start_time = time.perf_counter()

        # 1. Downmix to mono if multi-channel
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=-1)

        # 2. Speech-Band Filter (Cuts sub-80Hz laptop fan/desk rumble and high frequency hiss)
        filtered_audio = filter_speech_band(waveform, sr=sample_rate)

        # 3. Sizing & Seamless Tiling (Native 2.0s to 4.0s analysis window)
        target_len = int(2.0 * sample_rate)  # 32000
        if len(filtered_audio) < target_len:
            reps = int(np.ceil(target_len / max(1, len(filtered_audio))))
            audio_chunk = np.tile(filtered_audio, reps)[:target_len].astype(np.float32)
        else:
            audio_chunk = filtered_audio[-target_len:].astype(np.float32)

        # 4. Telephony Simulation if requested
        if apply_telephony:
            from backend.features.augmentations import apply_telephony_filter
            audio_chunk = apply_telephony_filter(audio_chunk, fs=sample_rate)

        # 5. Voice Activity Detection (VAD) Filter
        rms_energy = float(np.sqrt(np.mean(audio_chunk ** 2)))
        speech_ratio = compute_speech_ratio(audio_chunk, sample_rate=sample_rate)
        min_val = float(np.min(audio_chunk))
        max_val = float(np.max(audio_chunk))

        # Ambient mic noise, fan hum, or silence sits at rms < 0.025 or speech_ratio < 0.35
        if rms_energy < 0.025 or speech_ratio < 0.35:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            if self.model_type == "aasist":
                arch_name = "AASIST (Graph Attention Network)"
            elif self.model_type == "rawnet":
                arch_name = "RawNet2 (SincNet + FMS)"
            else:
                arch_name = "3-Branch Ensemble (Wav2Vec2 + Phase ResNet + Bio)"

            return {
                "risk_score": 0.0,
                "threat_probability": 0.0,
                "raw_neural_prob": 0.0,
                "model_architecture": arch_name,
                "device": str(self.device),
                "status": "IDLE_SILENCE",
                "label": "IDLE / SILENCE (AWAITING SPEECH)",
                "color": "slate",
                "anomalies": [],
                "forensics": {
                    "pitch_mean": 0.0,
                    "pitch_std": 0.0,
                    "jitter_local": 0.0,
                    "shimmer_local": 0.0,
                    "phase_dispersion": 0.0,
                    "high_band_ratio": 0.0,
                    "breath_pause_ratio": 1.0,
                    "spectral_flatness": 0.0,
                    "ambient_noise_floor_db": round(20.0 * np.log10(max(1e-5, max_val)), 1),
                    "is_pristine_env": False,
                },
                "latency_ms": elapsed_ms,
                "speech_ratio": speech_ratio,
                "timestamp": time.time(),
            }

        # 6. Peak Normalization
        peak_amp = np.max(np.abs(audio_chunk))
        if peak_amp > 1e-4:
            norm_audio = (audio_chunk / peak_amp).astype(np.float32)
        else:
            norm_audio = audio_chunk

        # 7. Extract Forensic Telemetry for Dashboard Display
        acoustics = extract_acoustic_forensics(norm_audio, sample_rate=sample_rate)
        lfcc = extract_lfcc(norm_audio, sample_rate=sample_rate, num_filters=60, num_ceps=20)

        # 8. Neural Model Forward Pass
        if self.model_type == "ensemble":
            ens_res = self.ensemble.predict_clip(norm_audio, sr=sample_rate)
            pred = ens_res["prediction"]
            final_score = ens_res["final_score"]
            b1_val = ens_res["branch_scores"]["branch1_ssl"]
            b2_val = ens_res["branch_scores"]["branch2_phase"]
            b3_val = ens_res["branch_scores"]["branch3_temporal"]
            raw_neural_prob = float(final_score)

            # Calibrate risk score to standard 0-100% telemetry range
            if pred == "REAL":
                risk_score = round(float(np.clip(final_score * 25.0, 4.0, 32.0)), 1)
            else:
                risk_score = round(float(np.clip(80.0 + (final_score - 0.50) * 38.0, 80.0, 99.4)), 1)

            arch_label = "3-Branch Ensemble (Wav2Vec2 + Phase ResNet-18 + Bio MLP)"
        else:
            tensor_audio = torch.from_numpy(norm_audio).float().unsqueeze(0).to(self.device)
            raw_neural_prob = self.forward_raw_model(tensor_audio)
            risk_score = round(float(np.clip(raw_neural_prob * 100.0, 4.0, 99.4)), 1)
            arch_label = "AASIST (Graph Attention Network)" if self.model_type == "aasist" else "RawNet2"
            b1_val, b2_val, b3_val = raw_neural_prob, 0.0, 0.0

        # 9. Anomaly Flagging
        anomalies = []
        if risk_score >= 50.0:
            if b2_val > 0.45:
                anomalies.append("Phase ResNet-18: Severe High-Band Phase Dispersion (Vocoder Artifacts)")
            if b1_val > 0.63:
                anomalies.append("Wav2Vec2 SSL: Synthetic Latent Feature Embedding")
            if acoustics["pitch_mean"] > 70 and acoustics["jitter_local"] < 0.0035 and acoustics["pitch_std"] < 3.0:
                anomalies.append("Acoustic Prosody: Unnaturally Flat Pitch & Zero Vocal Jitter (TTS)")

        # Classification Badge
        if risk_score >= 75.0:
            status = "CRITICAL_SYNTHETIC"
            label = "SYNTHETIC VOICE DETECTED (HIGH CONFIDENCE)"
            color = "red"
        elif risk_score >= 40.0:
            status = "SUSPICIOUS_ANOMALY"
            label = "SUSPICIOUS ACOUSTIC ANOMALIES"
            color = "amber"
        else:
            status = "AUTHENTIC_HUMAN"
            label = "AUTHENTIC HUMAN BIOMETRICS"
            color = "green"
            anomalies = []

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return {
            "risk_score": risk_score,
            "threat_probability": round(risk_score / 100.0, 4),
            "raw_neural_prob": round(raw_neural_prob, 4),
            "model_architecture": arch_label,
            "device": str(self.device),
            "status": status,
            "label": label,
            "color": color,
            "anomalies": anomalies,
            "forensics": acoustics,
            "latency_ms": elapsed_ms,
            "speech_ratio": speech_ratio,
            "timestamp": time.time(),
        }
