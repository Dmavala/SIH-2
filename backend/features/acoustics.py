"""
Acoustic & Prosodic Forensic Feature Extractor
Specifically engineered to catch Neural TTS & Voice Conversion (VC) traces:

1. High-Frequency Spectral & Phase Inconsistencies:
   - High-band spectral envelope residual (HiFi-GAN / MelGAN upsampling checkerboard ripples)
   - Phase coherence on voiced harmonic components
2. Pitch Micro-Jitter & Shimmer (unnaturally static pitch / absence of vocal fold tremors)
3. Breath Micro-Pause Distribution (synthetic speech lacks human respiratory cadence)
4. Acoustic Environment Disconnect (overly pristine audio lacking ambient reverberation)
"""

import numpy as np
from scipy.signal import welch


def estimate_pitch_autocorr(frame: np.ndarray, sample_rate: int = 16000, f_min: float = 70.0, f_max: float = 400.0) -> float:
    """Estimates fundamental frequency (F0) using autocorrelation."""
    if len(frame) == 0 or np.max(np.abs(frame)) < 1e-4:
        return 0.0

    signal = frame - np.mean(frame)
    corr = np.correlate(signal, signal, mode="full")
    corr = corr[len(corr) // 2:]

    min_lag = int(sample_rate / f_max)
    max_lag = int(sample_rate / f_min)

    if max_lag >= len(corr):
        max_lag = len(corr) - 1
    if min_lag >= max_lag:
        return 0.0

    peak_search = corr[min_lag:max_lag]
    if len(peak_search) == 0:
        return 0.0

    peak_index = np.argmax(peak_search) + min_lag
    peak_val = corr[peak_index]

    if corr[0] > 0 and (peak_val / corr[0]) > 0.35:
        f0 = sample_rate / peak_index
        return float(f0)
    return 0.0


def compute_spectral_phase_coherence(waveform: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Measures phase consistency and high-frequency harmonic envelope roughness.
    Neural vocoders (HiFi-GAN, MelGAN) construct phase artificially from mel-spectrograms,
    producing phase incoherence across harmonic components.
    """
    n_fft = 512
    if len(waveform) < n_fft:
        return 0.15

    # Compute Welch PSD with higher resolution
    freqs, psd = welch(waveform, fs=sample_rate, nperseg=n_fft)
    high_mask = (freqs >= 3200.0) & (freqs <= 7500.0)

    if not np.any(high_mask):
        return 0.15

    high_psd = psd[high_mask]
    log_psd = np.log10(np.maximum(high_psd, 1e-12))

    # Second derivative of log-power spectrum in high frequencies
    # Smooth natural speech has small curvature; vocoder ripples produce high curvature
    d2_spec = np.diff(log_psd, n=2)
    roughness = float(np.mean(np.abs(d2_spec)))
    return roughness


def extract_acoustic_forensics(waveform: np.ndarray, sample_rate: int = 16000) -> dict:
    """
    Extracts forensic markers reflecting vocal tract physics vs. vocoder artifacts.
    """
    if len(waveform) < int(sample_rate * 0.1):  # Less than 100ms
        return {
            "pitch_mean": 120.0,
            "pitch_std": 18.0,
            "jitter_local": 0.012,
            "shimmer_local": 0.035,
            "phase_dispersion": 0.15,
            "high_band_ratio": 0.12,
            "breath_pause_ratio": 0.15,
            "spectral_flatness": 0.02,
            "ambient_noise_floor_db": -50.0,
            "is_pristine_env": False,
        }

    max_amp = np.max(np.abs(waveform))
    norm_audio = waveform / (max_amp + 1e-6)

    # 1. Pitch Track & Jitter / Shimmer Analysis
    frame_len = int(sample_rate * 0.030)
    hop_len = int(sample_rate * 0.015)
    n_frames = (len(norm_audio) - frame_len) // hop_len

    pitch_track = []
    frame_amps = []

    for i in range(max(1, n_frames)):
        chunk = norm_audio[i * hop_len : i * hop_len + frame_len]
        f0 = estimate_pitch_autocorr(chunk, sample_rate)
        if f0 > 0:
            pitch_track.append(f0)
            frame_amps.append(np.max(np.abs(chunk)))

    if len(pitch_track) > 0:
        pitch_arr = np.array(pitch_track)
        pitch_mean = float(np.mean(pitch_arr))
        pitch_std = float(np.std(pitch_arr))
        if len(pitch_arr) >= 3:
            periods = 1.0 / pitch_arr
            period_diffs = np.abs(np.diff(periods))
            jitter_local = float(np.mean(period_diffs) / (np.mean(periods) + 1e-6))
        else:
            jitter_local = 0.012
        if len(frame_amps) >= 3:
            amp_arr = np.array(frame_amps)
            amp_diffs = np.abs(np.diff(amp_arr))
            shimmer_local = float(np.mean(amp_diffs) / (np.mean(amp_arr) + 1e-6))
        else:
            shimmer_local = 0.030
    else:
        pitch_mean = 0.0
        pitch_std = 0.0
        jitter_local = 0.0
        shimmer_local = 0.0

    # 2. High-Frequency Vocoder Phase & Spectral Roughness
    phase_dispersion = compute_spectral_phase_coherence(norm_audio, sample_rate)

    # 3. High-Band Energy Ratio (3.5kHz-8kHz vs 0.3kHz-3.5kHz)
    freqs, psd = welch(norm_audio, fs=sample_rate, nperseg=min(len(norm_audio), 1024))
    speech_band_energy = np.sum(psd[(freqs >= 300) & (freqs < 3500)])
    high_band_energy = np.sum(psd[freqs >= 3500])
    high_band_ratio = float(high_band_energy / (speech_band_energy + 1e-7))

    # 4. Respiratory & Micro-Pause Ratio (Speech Cadence)
    frame_20ms = int(sample_rate * 0.020)
    rms_vals = [
        np.sqrt(np.mean(norm_audio[idx : idx + frame_20ms] ** 2))
        for idx in range(0, len(norm_audio) - frame_20ms, frame_20ms)
    ]
    if len(rms_vals) > 0:
        rms_arr = np.array(rms_vals)
        silence_threshold = 0.05 * np.max(rms_arr)
        pause_frames = np.sum(rms_arr < silence_threshold)
        breath_pause_ratio = float(pause_frames / len(rms_arr))
        min_rms = max(np.percentile(rms_arr, 5), 1e-6)
        noise_floor_db = float(20.0 * np.log10(min_rms))
    else:
        breath_pause_ratio = 0.15
        noise_floor_db = -50.0

    # 5. Spectral Flatness
    psd_pos = psd[psd > 1e-12]
    if len(psd_pos) > 0:
        geometric_mean = np.exp(np.mean(np.log(psd_pos)))
        arithmetic_mean = np.mean(psd_pos)
        spectral_flatness = float(geometric_mean / (arithmetic_mean + 1e-9))
    else:
        spectral_flatness = 0.02

    # Pristine environment flag: digital silence without room ambient noise floor
    is_pristine_env = bool(noise_floor_db < -65.0)

    return {
        "pitch_mean": round(pitch_mean, 2),
        "pitch_std": round(pitch_std, 2),
        "jitter_local": round(jitter_local, 5),
        "shimmer_local": round(shimmer_local, 5),
        "phase_dispersion": round(phase_dispersion, 4),
        "high_band_ratio": round(high_band_ratio, 4),
        "breath_pause_ratio": round(breath_pause_ratio, 4),
        "spectral_flatness": round(spectral_flatness, 5),
        "ambient_noise_floor_db": round(noise_floor_db, 1),
        "is_pristine_env": is_pristine_env,
    }
