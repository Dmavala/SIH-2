"""
Feature Extraction Module for Voice Cloning / Deepfake Speech Detection System.

Provides:
1. Phase-Aware Dual-Channel Spectrogram (Branch 2):
   - Channel 0: Log-magnitude STFT
   - Channel 1: Instantaneous Frequency Deviation (time-derivative of unwrapped phase)
2. Hand-Crafted Temporal & Biological Artifacts (Branch 3, 23 dimensions total):
   - Silence pattern dynamics (4 dims)
   - Breathing pattern detection in 100-1000Hz pause regions (3 dims)
   - Pitch Jitter and Shimmer micro-perturbation analysis (4 dims)
   - Long-term spectral distribution statistics (4 dims)
   - Sub-band energy temporal variance across 8 frequency bands (8 dims)
"""

import numpy as np
import scipy.signal
import scipy.stats
import torch


def compute_stft(audio: np.ndarray, n_fft: int = 512, hop_length: int = 256, win_length: int = 512):
    """
    Computes Short-Time Fourier Transform (STFT) with Hann window.
    
    Args:
        audio: 1D float32 numpy array.
        n_fft: FFT window size.
        hop_length: Number of audio samples between adjacent STFT columns.
        win_length: Window size.
        
    Returns:
        Complex STFT matrix of shape (n_fft // 2 + 1, num_frames).
    """
    if len(audio) < n_fft:
        audio = np.pad(audio, (0, n_fft - len(audio)), mode='constant')
        
    window = np.hanning(win_length)
    # Center padding equivalent to standard STFT
    pad_amount = n_fft // 2
    padded_audio = np.pad(audio, (pad_amount, pad_amount), mode='reflect')
    
    num_frames = 1 + (len(padded_audio) - n_fft) // hop_length
    frames = np.lib.stride_tricks.as_strided(
        padded_audio,
        shape=(num_frames, n_fft),
        strides=(padded_audio.strides[0] * hop_length, padded_audio.strides[0])
    )
    
    windowed_frames = frames * window
    stft = np.fft.rfft(windowed_frames, n=n_fft, axis=-1).T
    return stft


def compute_phase_spectrogram(
    audio: np.ndarray,
    sr: int = 16000,
    n_fft: int = 512,
    hop_length: int = 256,
    win_length: int = 512,
    target_frames: int = 251
) -> np.ndarray:
    """
    Computes Dual-Channel Phase-Aware Spectrogram for Branch 2 (ResNet-18).
    
    Channel 0: Log-magnitude STFT: log(magnitude + 1e-6)
    Channel 1: Instantaneous Frequency Deviation (time-derivative of unwrapped phase)
    
    Args:
        audio: 1D numpy array of audio samples (float32, [-1.0, 1.0]).
        sr: Sampling rate (16000 Hz).
        n_fft: FFT window size.
        hop_length: Hop length between frames.
        win_length: Window size.
        target_frames: Fixed number of temporal frames (default 251 for 4s at 16kHz).
        
    Returns:
        2-channel tensor of shape (2, 257, target_frames), normalized per channel.
    """
    if isinstance(audio, torch.Tensor):
        audio = audio.detach().cpu().numpy()
    audio = np.asarray(audio, dtype=np.float32).flatten()
    
    stft = compute_stft(audio, n_fft=n_fft, hop_length=hop_length, win_length=win_length)
    mag = np.abs(stft)
    phase = np.angle(stft)
    
    # Channel 0: Log-magnitude spectrogram
    log_mag = np.log(mag + 1e-6)
    
    # Channel 1: Instantaneous Frequency Deviation (time derivative of unwrapped phase)
    # Unwrap phase along the time axis (axis 1)
    unwrapped_phase = np.unwrap(phase, axis=-1)
    # Compute first difference along time axis: dPhase / dt
    if unwrapped_phase.shape[1] > 1:
        ifd = np.diff(unwrapped_phase, axis=-1)
        # Pad last column by edge duplication to maintain exact shape match
        ifd = np.pad(ifd, ((0, 0), (0, 1)), mode='edge')
    else:
        ifd = np.zeros_like(unwrapped_phase)
        
    # Align temporal length to target_frames
    if log_mag.shape[1] < target_frames:
        pad_width = target_frames - log_mag.shape[1]
        log_mag = np.pad(log_mag, ((0, 0), (0, pad_width)), mode='constant')
        ifd = np.pad(ifd, ((0, 0), (0, pad_width)), mode='constant')
    elif log_mag.shape[1] > target_frames:
        log_mag = log_mag[:, :target_frames]
        ifd = ifd[:, :target_frames]
        
    # Normalize Channel 0 (Zero mean, unit variance)
    mag_mean = np.mean(log_mag)
    mag_std = np.std(log_mag) + 1e-6
    norm_log_mag = (log_mag - mag_mean) / mag_std
    
    # Normalize Channel 1 (Zero mean, unit variance)
    ifd_mean = np.mean(ifd)
    ifd_std = np.std(ifd) + 1e-6
    norm_ifd = (ifd - ifd_mean) / ifd_std
    
    dual_channel = np.stack([norm_log_mag, norm_ifd], axis=0).astype(np.float32)
    return dual_channel


def extract_silence_patterns(
    audio: np.ndarray,
    sr: int = 16000,
    hop_length: int = 256,
    frame_length: int = 512
) -> np.ndarray:
    """
    Extracts silence pattern statistics (Branch 3):
    1. silence_ratio: Fraction of non-speech frames
    2. mean_silence_duration: Mean length of pauses (seconds)
    3. std_silence_duration: Std deviation of pause lengths (AI speech has robotic regular pauses)
    4. silence_segment_count: Total pause segments
    """
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if len(audio) < frame_length:
        return np.zeros(4, dtype=np.float32)
        
    # Compute Short-Time RMS Energy
    num_frames = 1 + (len(audio) - frame_length) // hop_length
    frames = np.lib.stride_tricks.as_strided(
        audio,
        shape=(num_frames, frame_length),
        strides=(audio.strides[0] * hop_length, audio.strides[0])
    )
    rms = np.sqrt(np.mean(frames ** 2, axis=-1) + 1e-8)
    
    # Dynamic energy threshold for silence
    peak_rms = np.percentile(rms, 95)
    silence_thresh = max(peak_rms * 0.08, 0.005)
    is_silent = rms < silence_thresh
    
    silence_ratio = float(np.mean(is_silent))
    
    # Find contiguous silence blocks
    silent_runs = []
    current_run = 0
    for s in is_silent:
        if s:
            current_run += 1
        else:
            if current_run > 0:
                silent_runs.append(current_run * hop_length / sr)
                current_run = 0
    if current_run > 0:
        silent_runs.append(current_run * hop_length / sr)
        
    if len(silent_runs) > 0:
        mean_duration = float(np.mean(silent_runs))
        std_duration = float(np.std(silent_runs))
        count = float(len(silent_runs))
    else:
        mean_duration = 0.0
        std_duration = 0.0
        count = 0.0
        
    return np.array([silence_ratio, mean_duration, std_duration, count], dtype=np.float32)


def extract_breathing_patterns(
    audio: np.ndarray,
    sr: int = 16000,
    hop_length: int = 256,
    n_fft: int = 512
) -> np.ndarray:
    """
    Extracts breathing artifact features (Branch 3):
    Human speech exhibits biological inhalation sounds before utterances (concentrated in 100-1000 Hz),
    whereas neural vocoders and cloned speech produce unnaturally sterile digital silence or artifacts.
    
    Returns:
    1. breath_segment_count: Number of inhalation candidate events
    2. breath_energy_ratio: Ratio of 100-1000Hz energy in non-speech regions
    3. breath_regularity: Variance of breath timing intervals
    """
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if len(audio) < n_fft:
        return np.zeros(3, dtype=np.float32)
        
    stft = compute_stft(audio, n_fft=n_fft, hop_length=hop_length, win_length=n_fft)
    mag = np.abs(stft)  # shape: (257, num_frames)
    
    # Frequency bins for 100 Hz to 1000 Hz
    freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    breath_band_mask = (freqs >= 100) & (freqs <= 1000)
    high_band_mask = (freqs > 2000)
    
    total_energy = np.sum(mag ** 2, axis=0) + 1e-8
    breath_energy = np.sum(mag[breath_band_mask, :] ** 2, axis=0)
    high_energy = np.sum(mag[high_band_mask, :] ** 2, axis=0)
    
    # Identify non-speech low-energy regions (potential breathing locations)
    peak_energy = np.percentile(total_energy, 90)
    pause_mask = (total_energy < peak_energy * 0.15) & (total_energy > peak_energy * 0.001)
    
    if np.any(pause_mask):
        pause_breath_energy = breath_energy[pause_mask]
        pause_total_energy = total_energy[pause_mask]
        pause_high_energy = high_energy[pause_mask]
        
        # Breath is characterized by mid-band dominance without high-frequency harshness
        breath_candidates = (pause_breath_energy > pause_high_energy * 1.5) & (pause_breath_energy > 1e-5)
        breath_count = float(np.sum(breath_candidates))
        breath_ratio = float(np.sum(pause_breath_energy) / (np.sum(pause_total_energy) + 1e-8))
        
        # Timing regularity between detected breath events
        breath_indices = np.where(breath_candidates)[0]
        if len(breath_indices) > 1:
            intervals = np.diff(breath_indices) * (hop_length / sr)
            breath_regularity = float(np.std(intervals))
        else:
            breath_regularity = 0.0
    else:
        breath_count = 0.0
        breath_ratio = 0.0
        breath_regularity = 0.0
        
    return np.array([breath_count, breath_ratio, breath_regularity], dtype=np.float32)


def extract_pitch_jitter_shimmer(
    audio: np.ndarray,
    sr: int = 16000,
    hop_length: int = 256,
    frame_length: int = 512
) -> np.ndarray:
    """
    Extracts pitch dynamics, Jitter, and Shimmer (Branch 3):
    1. f0_mean: Mean fundamental frequency
    2. f0_std: Pitch variability (prosody expressiveness)
    3. jitter_local: Cycle-to-cycle frequency perturbation (flat/robotic in neural vocoders)
    4. shimmer_local: Cycle-to-cycle amplitude perturbation
    """
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if len(audio) < frame_length * 2:
        return np.zeros(4, dtype=np.float32)
        
    num_frames = 1 + (len(audio) - frame_length) // hop_length
    frames = np.lib.stride_tricks.as_strided(
        audio,
        shape=(num_frames, frame_length),
        strides=(audio.strides[0] * hop_length, audio.strides[0])
    )
    
    # Lag bounds for human pitch: 65 Hz to 500 Hz
    min_lag = int(sr / 500)
    max_lag = int(sr / 65)
    
    f0_list = []
    amp_list = []
    
    for frame in frames:
        # Autocorrelation pitch extraction
        frame_norm = frame - np.mean(frame)
        sq_sum = np.sum(frame_norm ** 2)
        if sq_sum < 1e-5:
            continue
            
        corr = np.correlate(frame_norm, frame_norm, mode='full')
        corr = corr[len(frame_norm) - 1:]
        
        if len(corr) > max_lag:
            search_region = corr[min_lag:max_lag]
            peak_lag = min_lag + np.argmax(search_region)
            peak_val = corr[peak_lag] / (sq_sum + 1e-8)
            
            # Voiced threshold: correlation peak > 0.40
            if peak_val > 0.40 and peak_lag > 0:
                pitch = sr / float(peak_lag)
                f0_list.append(pitch)
                amp_list.append(np.max(np.abs(frame)))
                
    if len(f0_list) >= 4:
        f0_arr = np.array(f0_list, dtype=np.float32)
        amp_arr = np.array(amp_list, dtype=np.float32)
        periods = 1.0 / f0_arr
        
        f0_mean = float(np.mean(f0_arr))
        f0_std = float(np.std(f0_arr))
        
        # Local Jitter: relative period-to-period difference
        jitter = float(np.mean(np.abs(np.diff(periods))) / (np.mean(periods) + 1e-8))
        
        # Local Shimmer: relative amplitude-to-amplitude difference
        shimmer = float(np.mean(np.abs(np.diff(amp_arr))) / (np.mean(amp_arr) + 1e-8))
    else:
        f0_mean = 0.0
        f0_std = 0.0
        jitter = 0.0
        shimmer = 0.0
        
    return np.array([f0_mean, f0_std, jitter, shimmer], dtype=np.float32)


def extract_spectral_statistics(
    audio: np.ndarray,
    sr: int = 16000,
    n_fft: int = 512,
    hop_length: int = 256
) -> np.ndarray:
    """
    Extracts long-term spectral shape statistics (Branch 3):
    1. centroid_mean: Center of spectral mass
    2. bandwidth_mean: Spectral spread
    3. spectral_skewness: Spectral asymmetry across frequencies
    4. spectral_kurtosis: Spectral peakedness
    """
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if len(audio) < n_fft:
        return np.zeros(4, dtype=np.float32)
        
    stft = compute_stft(audio, n_fft=n_fft, hop_length=hop_length, win_length=n_fft)
    mag = np.abs(stft)  # shape: (257, num_frames)
    freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    
    # Spectral Centroid per frame
    mag_sum = np.sum(mag, axis=0) + 1e-8
    centroids = np.sum(freqs[:, None] * mag, axis=0) / mag_sum
    centroid_mean = float(np.mean(centroids))
    
    # Spectral Bandwidth per frame
    diff = (freqs[:, None] - centroids[None, :]) ** 2
    bandwidths = np.sqrt(np.sum(diff * mag, axis=0) / mag_sum)
    bandwidth_mean = float(np.mean(bandwidths))
    
    # Average spectrum across all frames
    avg_spectrum = np.mean(mag, axis=1)
    skewness = float(scipy.stats.skew(avg_spectrum))
    kurtosis = float(scipy.stats.kurtosis(avg_spectrum))
    
    return np.array([centroid_mean, bandwidth_mean, skewness, kurtosis], dtype=np.float32)


def extract_subband_energy_variance(
    audio: np.ndarray,
    sr: int = 16000,
    n_fft: int = 512,
    hop_length: int = 256,
    num_bands: int = 8
) -> np.ndarray:
    """
    Extracts sub-band energy temporal variance across 8 frequency bands (Branch 3):
    Linear bands spanning 0 Hz to Nyquist (8000 Hz).
    Vocoders often exhibit unnatural high-frequency energy dispersion or static band variance.
    
    Returns:
        8-dimensional float32 vector of temporal energy variances per band.
    """
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if len(audio) < n_fft:
        return np.zeros(num_bands, dtype=np.float32)
        
    stft = compute_stft(audio, n_fft=n_fft, hop_length=hop_length, win_length=n_fft)
    mag_sq = (np.abs(stft)) ** 2  # Energy: (257, num_frames)
    
    num_bins = n_fft // 2 + 1
    bins_per_band = num_bins // num_bands
    
    band_variances = []
    for b in range(num_bands):
        start_bin = b * bins_per_band
        end_bin = (b + 1) * bins_per_band if b < num_bands - 1 else num_bins
        
        band_energy_per_frame = np.sum(mag_sq[start_bin:end_bin, :], axis=0)
        # Log energy for numerical stabilization
        log_band_energy = np.log(band_energy_per_frame + 1e-8)
        band_var = float(np.var(log_band_energy))
        band_variances.append(band_var)
        
    return np.array(band_variances, dtype=np.float32)


def extract_all_temporal_features(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    Extracts all 23 hand-crafted temporal and biological artifact features for Branch 3.
    
    Breakdown:
    - Silence patterns (4 dims)
    - Breathing detection (3 dims)
    - Pitch Jitter & Shimmer (4 dims)
    - Spectral statistics (4 dims)
    - Sub-band energy variances (8 dims)
    
    Returns:
        23-dimensional normalized float32 numpy array.
    """
    silence_feat = extract_silence_patterns(audio, sr=sr)
    breath_feat = extract_breathing_patterns(audio, sr=sr)
    pitch_feat = extract_pitch_jitter_shimmer(audio, sr=sr)
    spectral_feat = extract_spectral_statistics(audio, sr=sr)
    subband_feat = extract_subband_energy_variance(audio, sr=sr)
    
    concatenated = np.concatenate([
        silence_feat,
        breath_feat,
        pitch_feat,
        spectral_feat,
        subband_feat
    ]).astype(np.float32)
    
    # Replace any potential NaNs or Infs with zero
    cleaned = np.nan_to_num(concatenated, nan=0.0, posinf=0.0, neginf=0.0)
    return cleaned
