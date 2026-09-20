"""
Linear Frequency Cepstral Coefficients (LFCC) Feature Extractor
Critical for Audio Deepfake & Neural Vocoder Artifact Detection.

Unlike MFCC (which compresses high frequencies to mimic human psychoacoustics),
LFCC retains linear resolution across the entire spectrum (0 - Nyquist).
Neural vocoders (HiFi-GAN, MelGAN, WaveGrad, RVC) leave unnatural spectral phase
and energy traces in high-frequency bands (4kHz - 8kHz) that LFCC captures.
"""

import numpy as np
from scipy.fftpack import dct


def linear_filterbank(num_filters: int, n_fft: int, sample_rate: int, low_freq: float = 0.0, high_freq: float = None):
    """
    Constructs a linearly spaced triangular filterbank matrix.
    
    Args:
        num_filters: Number of linear filters (typically 40-70).
        n_fft: FFT window size (e.g., 512 or 1024).
        sample_rate: Audio sampling rate (typically 16000 Hz).
        low_freq: Lowest frequency bound in Hz (default: 0).
        high_freq: Highest frequency bound in Hz (default: sample_rate / 2).
    
    Returns:
        np.ndarray of shape (num_filters, n_fft // 2 + 1)
    """
    if high_freq is None:
        high_freq = sample_rate / 2.0

    num_bins = n_fft // 2 + 1
    # Linearly spaced frequency points
    linear_points = np.linspace(low_freq, high_freq, num_filters + 2)
    # Map Hz to FFT frequency bin indices
    bin_indices = np.floor((n_fft + 1) * linear_points / sample_rate).astype(int)
    bin_indices = np.clip(bin_indices, 0, num_bins - 1)

    filterbank = np.zeros((num_filters, num_bins), dtype=np.float32)

    for i in range(1, num_filters + 1):
        left = bin_indices[i - 1]
        center = bin_indices[i]
        right = bin_indices[i + 1]

        # Upward slope
        if center > left:
            filterbank[i - 1, left:center] = (np.arange(left, center) - left) / (center - left)
        # Downward slope
        if right > center:
            filterbank[i - 1, center:right] = (right - np.arange(center, right)) / (right - center)

    return filterbank


def compute_deltas(features: np.ndarray, width: int = 2) -> np.ndarray:
    """
    Computes delta (1st derivative) or delta-delta (2nd derivative) features
    along the time axis.
    """
    n_frames, n_feats = features.shape
    deltas = np.zeros_like(features)
    denom = 2 * sum(w ** 2 for w in range(1, width + 1))

    for w in range(1, width + 1):
        prev_f = np.roll(features, w, axis=0)
        prev_f[:w, :] = features[0, :]
        next_f = np.roll(features, -w, axis=0)
        next_f[-w:, :] = features[-1, :]
        deltas += w * (next_f - prev_f)

    deltas /= max(denom, 1e-6)
    return deltas


def extract_lfcc(
    waveform: np.ndarray,
    sample_rate: int = 16000,
    win_len: float = 0.025,
    hop_len: float = 0.010,
    n_fft: int = 512,
    num_filters: int = 60,
    num_ceps: int = 20,
    with_deltas: bool = True
) -> np.ndarray:
    """
    Extracts LFCC + Delta + Delta-Delta features from raw waveform.
    
    Args:
        waveform: 1D numpy array of audio samples (normalized -1 to 1).
        sample_rate: Sample rate in Hz.
        win_len: Analysis window length in seconds (default 25ms).
        hop_len: Analysis window hop step in seconds (default 10ms).
        n_fft: FFT size (default 512).
        num_filters: Number of linear filterbanks (default 60).
        num_ceps: Number of cepstral coefficients to keep (default 20).
        with_deltas: Append delta and delta-delta features (total 3 * num_ceps = 60).
        
    Returns:
        np.ndarray of shape (frames, features)
    """
    if len(waveform) == 0:
        return np.zeros((1, num_ceps * 3 if with_deltas else num_ceps), dtype=np.float32)

    # Frame parameters
    frame_length = int(round(win_len * sample_rate))
    frame_step = int(round(hop_len * sample_rate))

    # Pre-emphasis filter to boost high frequency vocoder artifacts
    pre_emphasis = 0.97
    emphasized = np.append(waveform[0], waveform[1:] - pre_emphasis * waveform[:-1])

    # Framing
    signal_length = len(emphasized)
    if signal_length <= frame_length:
        padded = np.pad(emphasized, (0, frame_length - signal_length), mode="constant")
        frames = padded[np.newaxis, :]
    else:
        num_frames = 1 + int(np.floor((signal_length - frame_length) / frame_step))
        indices = (
            np.tile(np.arange(0, frame_length), (num_frames, 1))
            + np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
        )
        frames = emphasized[indices]

    # Hamming window
    window = np.hamming(frame_length)
    frames *= window

    # Short-Time Fourier Transform Power Spectrum
    mag_frames = np.abs(np.fft.rfft(frames, n_fft))
    pow_frames = (1.0 / n_fft) * (mag_frames ** 2)

    # Linear Filterbank Energy
    fbank = linear_filterbank(num_filters, n_fft, sample_rate)
    filter_energies = np.dot(pow_frames, fbank.T)
    filter_energies = np.where(filter_energies == 0, np.finfo(float).eps, filter_energies)
    log_filter_energies = np.log(filter_energies)

    # Discrete Cosine Transform (DCT-II)
    lfcc_base = dct(log_filter_energies, type=2, axis=1, norm="ortho")[:, :num_ceps]

    if not with_deltas:
        return lfcc_base.astype(np.float32)

    delta1 = compute_deltas(lfcc_base)
    delta2 = compute_deltas(delta1)
    lfcc_full = np.concatenate([lfcc_base, delta1, delta2], axis=1)

    return lfcc_full.astype(np.float32)
