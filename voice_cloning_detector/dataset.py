"""
Audio Dataset and Data Augmentation Pipeline for Voice Cloning Detection.

Features:
- Standardizes audio to 16,000 Hz, mono, float32 [-1.0, 1.0].
- Chunks audio into fixed 4.0-second slices (64,000 samples).
- Robust acoustic augmentations:
  - Additive background noise (SNR 10-30 dB)
  - Codec simulation / frequency band limiting
  - Downsampling & upsampling (e.g. 8kHz telephony simulation)
  - Random amplitude scaling (0.8x - 1.2x)
- Speaker-disjoint train / validation / test splits to prevent identity leakage.
"""

import os
import glob
import random
import numpy as np
import soundfile as sf
import scipy.signal
import torch
from torch.utils.data import Dataset
from typing import List, Dict, Tuple, Optional, Any

from .feature_extraction import compute_phase_spectrogram, extract_all_temporal_features
from .config import SAMPLE_RATE, CHUNK_DURATION, TARGET_SAMPLES


def load_and_standardize_audio(
    file_path: str,
    target_sr: int = SAMPLE_RATE
) -> np.ndarray:
    """
    Loads any audio file, converts to mono, resamples to target_sr, and peak-normalizes.
    
    Args:
        file_path: Path to audio file (.wav, .mp3, .flac, .ogg, etc.).
        target_sr: Target sample rate (default 16000).
        
    Returns:
        1D float32 numpy array normalized to [-1.0, 1.0].
    """
    try:
        audio, sr = sf.read(file_path, dtype='float32')
    except Exception:
        # Fallback to librosa if soundfile fails on non-wav formats
        import librosa
        audio, sr = librosa.load(file_path, sr=target_sr, mono=True)
        
    # Convert stereo to mono
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
        
    # Resample if needed using anti-aliased band-limited filter
    if sr != target_sr:
        try:
            import torchaudio.transforms as T
            resampler = T.Resample(orig_freq=sr, new_freq=target_sr)
            audio_t = torch.from_numpy(np.ascontiguousarray(audio, dtype=np.float32)).float()
            audio = resampler(audio_t).numpy()
        except Exception:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        
    # Filter mechanical rumble below 80 Hz (common in laptop mics and AC hum)
    if len(audio) > 512:
        try:
            sos = scipy.signal.butter(4, [80, min(7500, target_sr // 2 - 100)], btype='bandpass', fs=target_sr, output='sos')
            audio = scipy.signal.sosfilt(sos, audio).astype(np.float32)
        except Exception:
            pass

    # Peak normalization to [-1.0, 1.0]
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak
        
    return audio.astype(np.float32)


def slice_into_chunks(
    audio: np.ndarray,
    chunk_samples: int = TARGET_SAMPLES,
    overlap_samples: int = 0
) -> List[np.ndarray]:
    """
    Slices audio waveform into fixed-length chunks. Pads with reflect or zeros if shorter.
    """
    if len(audio) < chunk_samples:
        # Seamless acoustic tiling to preserve natural phase continuity
        repeats = int(np.ceil(chunk_samples / max(len(audio), 1)))
        padded = np.tile(audio, repeats)[:chunk_samples]
        return [padded]
        
    step = chunk_samples - overlap_samples
    chunks = []
    for start in range(0, len(audio) - chunk_samples + 1, step):
        chunk = audio[start:start + chunk_samples]
        chunks.append(chunk)
        
    if len(chunks) == 0:
        chunks.append(audio[:chunk_samples])
        
    return chunks


# Augmentations
def apply_additive_noise(audio: np.ndarray, snr_db_range: Tuple[float, float] = (10.0, 30.0)) -> np.ndarray:
    """Adds white or pink noise at random SNR."""
    snr_db = random.uniform(snr_db_range[0], snr_db_range[1])
    sig_power = np.mean(audio ** 2) + 1e-10
    noise_power = sig_power / (10 ** (snr_db / 10.0))
    noise = np.random.normal(0, np.sqrt(noise_power), size=len(audio)).astype(np.float32)
    augmented = audio + noise
    # Re-normalize
    peak = np.max(np.abs(augmented))
    if peak > 0:
        augmented = augmented / peak
    return augmented


def apply_codec_simulation(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Simulates telephony or lossy codec cutoff via lowpass filtering (e.g. 3400Hz or 6000Hz)."""
    cutoff = random.choice([3400, 5000, 6500])
    nyquist = sr / 2
    norm_cutoff = min(cutoff / nyquist, 0.95)
    b, a = scipy.signal.butter(4, norm_cutoff, btype='low')
    filtered = scipy.signal.filtfilt(b, a, audio)
    peak = np.max(np.abs(filtered))
    if peak > 0:
        filtered = filtered / peak
    return filtered.astype(np.float32)


def apply_random_resampling(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Downsamples to lower rate (8kHz or 12kHz) and resamples back to 16kHz."""
    down_sr = random.choice([8000, 11025, 12000])
    down_samples = int(len(audio) * (down_sr / sr))
    downsampled = scipy.signal.resample(audio, down_samples)
    upsampled = scipy.signal.resample(downsampled, len(audio))
    return upsampled.astype(np.float32)


def apply_amplitude_gain(audio: np.ndarray) -> np.ndarray:
    """Random volume scaling."""
    gain = random.uniform(0.7, 1.3)
    return np.clip(audio * gain, -1.0, 1.0).astype(np.float32)


def augment_audio(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Applies a random mixture of training augmentations."""
    if random.random() < 0.4:
        audio = apply_additive_noise(audio)
    if random.random() < 0.3:
        audio = apply_codec_simulation(audio, sr=sr)
    if random.random() < 0.2:
        audio = apply_random_resampling(audio, sr=sr)
    if random.random() < 0.3:
        audio = apply_amplitude_gain(audio)
    return audio


class VoiceCloningDataset(Dataset):
    """
    Multi-Branch PyTorch Dataset for Voice Cloning and Deepfake Audio.
    
    Each item returns:
    - waveform: (64000,) float32 tensor
    - phase_spec: (2, 257, 251) float32 tensor
    - temporal_feat: (23,) float32 tensor
    - label: float32 scalar (0.0 for REAL, 1.0 for FAKE)
    - metadata: dict
    """
    def __init__(
        self,
        samples: List[Dict[str, Any]],
        augment: bool = False,
        sr: int = SAMPLE_RATE
    ):
        self.samples = samples
        self.augment = augment
        self.sr = sr
        
    def __len__(self) -> int:
        return len(self.samples)
        
    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = self.samples[idx]
        
        # If audio is already preloaded array, use it; otherwise load from file
        if "audio" in item:
            audio = item["audio"].copy()
        else:
            audio = load_and_standardize_audio(item["path"], target_sr=self.sr)
            # Ensure target length
            if len(audio) < TARGET_SAMPLES:
                repeats = int(np.ceil(TARGET_SAMPLES / max(len(audio), 1)))
                audio = np.tile(audio, repeats)[:TARGET_SAMPLES]
            elif len(audio) > TARGET_SAMPLES:
                audio = audio[:TARGET_SAMPLES]
                
        if self.augment:
            audio = augment_audio(audio, sr=self.sr)
            
        label_val = float(item["label"])  # 0.0 for REAL, 1.0 for FAKE
        generator = item.get("generator", "real" if label_val == 0.0 else "synthetic")
        
        # Extract dual-channel spectrogram for Branch 2
        phase_spec = compute_phase_spectrogram(audio, sr=self.sr, target_frames=251)
        
        # Extract 23D temporal feature vector for Branch 3
        temporal_feat = extract_all_temporal_features(audio, sr=self.sr)
        
        return {
            "waveform": torch.from_numpy(audio),
            "phase_spec": torch.from_numpy(phase_spec),
            "temporal_feat": torch.from_numpy(temporal_feat),
            "label": torch.tensor(label_val, dtype=torch.float32),
            "generator": generator,
            "path": item.get("path", "")
        }


def split_by_speaker(
    file_records: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Splits file records into train, validation, and test sets based on speaker ID
    to prevent identity leakage across splits.
    """
    rng = random.Random(seed)
    # Group records by speaker
    speaker_map = {}
    for rec in file_records:
        spk = rec.get("speaker", "unknown")
        if spk not in speaker_map:
            speaker_map[spk] = []
        speaker_map[spk].append(rec)
        
    speakers = list(speaker_map.keys())
    rng.shuffle(speakers)
    
    num_speakers = len(speakers)
    train_end = max(1, int(num_speakers * train_ratio))
    val_end = max(train_end + 1, int(num_speakers * (train_ratio + val_ratio)))
    
    train_speakers = set(speakers[:train_end])
    val_speakers = set(speakers[train_end:val_end])
    test_speakers = set(speakers[val_end:])
    
    train_records = [r for s in train_speakers for r in speaker_map[s]]
    val_records = [r for s in val_speakers for r in speaker_map[s]]
    test_records = [r for s in test_speakers for r in speaker_map[s]]
    
    # If any set is empty due to small number of speakers, fall back to record-level split
    if len(val_records) == 0 or len(test_records) == 0:
        rng.shuffle(file_records)
        n = len(file_records)
        t_end = int(n * train_ratio)
        v_end = int(n * (train_ratio + val_ratio))
        return file_records[:t_end], file_records[t_end:v_end], file_records[v_end:]
        
    return train_records, val_records, test_records
