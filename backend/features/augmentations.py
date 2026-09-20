"""
Audio Augmentations & Codec Robustness Layer
Addresses SIH Pitfall #1: Overfitting to clean studio audio.

Applies:
- G.711 / AMR Telephone Bandpass Filter (300Hz - 3400Hz)
- Background Acoustic Noise Injection
- Digital Codec Quantization & Dynamic Range Compression
"""

import numpy as np
from scipy.signal import butter, sosfilt


def butter_bandpass(lowcut: float = 300.0, highcut: float = 3400.0, fs: int = 16000, order: int = 4):
    """Generates Second-Order Sections (SOS) for telephone bandpass filter."""
    nyq = 0.5 * fs
    low = max(lowcut / nyq, 0.01)
    high = min(highcut / nyq, 0.99)
    sos = butter(order, [low, high], btype="band", output="sos")
    return sos


def apply_telephony_filter(audio: np.ndarray, fs: int = 16000) -> np.ndarray:
    """
    Simulates standard POTS / VoIP telephone codec bandwidth (300 Hz - 3.4 kHz).
    Essential to ensure deepfake detector doesn't collapse on cell phone calls.
    """
    if len(audio) < 16:
        return audio
    sos = butter_bandpass(300.0, 3400.0, fs=fs, order=4)
    filtered = sosfilt(sos, audio)
    return filtered.astype(np.float32)


def add_ambient_noise(audio: np.ndarray, snr_db: float = 20.0) -> np.ndarray:
    """
    Injects realistic Gaussian / pink background ambient noise at desired SNR.
    """
    signal_power = np.mean(audio ** 2)
    if signal_power < 1e-9:
        return audio

    noise = np.random.normal(0, 1, len(audio))
    noise_power = np.mean(noise ** 2)
    k = np.sqrt(signal_power / (10 ** (snr_db / 10.0) * (noise_power + 1e-9)))
    noisy_audio = audio + k * noise
    # Prevent clipping
    max_val = np.max(np.abs(noisy_audio))
    if max_val > 1.0:
        noisy_audio /= max_val
    return noisy_audio.astype(np.float32)


def simulate_codec_compression(audio: np.ndarray, bits: int = 8) -> np.ndarray:
    """
    Simulates low-bitrate quantization noise (e.g. mu-law / A-law 8-bit PCM).
    """
    max_val = np.max(np.abs(audio)) + 1e-6
    normalized = audio / max_val
    levels = 2 ** bits
    quantized = np.round(normalized * (levels / 2)) / (levels / 2)
    return (quantized * max_val).astype(np.float32)
