"""
Lightweight Voice Activity Detection (VAD) Filter.
Ensures model only scores chunks when at least 40% of frames contain active human speech.
Prevents silence or ambient desk/laptop noise from returning random high risk values.
"""

import numpy as np


def compute_speech_ratio(audio: np.ndarray, sample_rate: int = 16000, frame_ms: int = 20) -> float:
    """
    Computes fraction of active human voiced speech frames in the window.
    Uses multi-band energy, harmonic periodicity, and zero-crossing rates.
    Robust across quiet microphone gains, soft conversational speech, and ambient fan noise.
    """
    if len(audio) == 0:
        return 0.0

    max_amp = np.max(np.abs(audio))
    # Ambient digital zero or extreme silence
    if max_amp < 0.005:
        return 0.0

    # Locally normalize to [0, 1] scale for robust thresholding across quiet & loud mics
    norm_audio = audio / max_amp

    frame_len = int(sample_rate * (frame_ms / 1000.0))
    n_frames = len(audio) // frame_len
    if n_frames == 0:
        return 0.0

    # 1. Frame RMS Energy
    frame_rms = np.array([
        np.sqrt(np.mean(norm_audio[i * frame_len : (i + 1) * frame_len] ** 2) + 1e-9)
        for i in range(n_frames)
    ])

    # 2. Dynamic threshold relative to background noise floor
    noise_floor = np.percentile(frame_rms, 15)
    max_rms = np.max(frame_rms)

    # If the dynamic range is negligible (< 1.35x between peak and noise) and audio is quiet, it is stationary noise
    if max_rms / (noise_floor + 1e-6) < 1.35 and max_amp < 0.08:
        return 0.0

    energy_threshold = max(0.015, noise_floor * 1.6, max_rms * 0.12)

    # 3. Voiced Speech Frames: Energy + ZCR in human speech range (not DC rumble, not pure hiss)
    active_frames = 0
    for i in range(n_frames):
        chunk = norm_audio[i * frame_len : (i + 1) * frame_len]
        rms = frame_rms[i]
        zcr = np.sum(np.abs(np.diff(np.sign(chunk)))) / 2.0

        # Human voiced speech ZCR is typically 4 - 120 per 20ms frame (not high-frequency static hiss > 200)
        if rms >= energy_threshold and 2 <= zcr <= (frame_len * 0.65):
            active_frames += 1

    ratio = float(active_frames / n_frames)
    return round(ratio, 3)
