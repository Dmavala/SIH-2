"""
Dataset loading for real anti-spoofing training.

Supports:
1. ASVspoof 2019 LA / 2021 LA layout:
       <root>/LA/ASVspoof2019_LA_train/flac/*.flac
       <root>/LA/ASVspoof2019_LA_train/trial_metadata.txt   (or .cm.txt style)
   Protocol parsing auto-detects the key column (contains 'bonafide') and the
   filename column (ends with the audio stem). Works for both the 5-column
   2019 format and the 2021 trial-metadata format.
2. Generic folder layout:
       <root>/real|bonafide/*.(wav|flac)
       <root>/fake|spoof/*.(wav|flac)
3. Synthetic fallback (for CI / smoke tests only — produces the same
   procedural audio used previously; NEVER for evaluation claims).
"""

import os
import glob
import random
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

from backend.config import settings
from backend.features.augmentations import apply_telephony_filter

AUDIO_EXTS = (".flac", ".wav", ".mp3", ".ogg")
# Task separation (important):
#   The deepfake engines learn SYNTHETIC-VOICE vs REAL-VOICE. Content-based
#   corpora (scam calls vs normal calls) contain real human audio on BOTH
#   sides. "normal"/call folders ARE valid bonafide data (real telephony
#   speech) and are labelled real; "scam"/"fraud" folders are real human
#   scammer recordings — labelling them fake teaches the detector that real
#   telephony speech is synthetic, so they are deliberately NOT labelled.
#   Fraud *content* is the semantics layer's job (audio_intelligence).
BONA_ALIASES = {"bonafide", "real", "genuine", "authentic", "human", "legit",
                "normal", "normal_calls"}
SPOOF_ALIASES = {"spoof", "spoofed", "fake", "synthetic", "deepfake", "clone"}


def _parse_protocol(path: str) -> Dict[str, int]:
    """
    Parses an ASVspoof-style protocol/metadata file into {stem: 0|1}
    (0 = bonafide, 1 = spoof). Auto-detects column roles.
    """
    labels: Dict[str, int] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            lower = [p.lower() for p in parts]
            key_col = next((i for i, p in enumerate(lower)
                            if p in BONA_ALIASES or p in SPOOF_ALIASES), None)
            if key_col is None:
                continue
            label = 0 if lower[key_col] in BONA_ALIASES else 1
            # Filename column: first column that looks like a trial id
            name_col = next((i for i, p in enumerate(parts)
                             if i != key_col and (p.lower().endswith(AUDIO_EXTS) or "-" in p or "_" in p)),
                            0)
            stem = parts[name_col]
            for ext in AUDIO_EXTS:
                if stem.lower().endswith(ext):
                    stem = stem[: -len(ext)]
                    break
            labels[stem] = label
    return labels


def build_file_list(data_dir: str) -> List[Tuple[str, int]]:
    """
    Discovers (path, label) pairs. Preference order:
      1) any protocol/metadata txt next to audio folders
      2) folder-name heuristics (real/ vs fake/)
    Returns [] when nothing found (caller can fall back to synthetic).
    """
    data_dir = os.path.abspath(data_dir)
    if not os.path.isdir(data_dir):
        return []

    # 1) Protocol-driven
    protocols = glob.glob(os.path.join(data_dir, "**", "*trial_metadata*.txt"), recursive=True) + \
                glob.glob(os.path.join(data_dir, "**", "*protocol*.txt"), recursive=True) + \
                glob.glob(os.path.join(data_dir, "**", "*.cm.txt"), recursive=True)
    if protocols:
        labels = _parse_protocol(protocols[0])
        pairs: List[Tuple[str, int]] = []
        for path in glob.glob(os.path.join(data_dir, "**", "*.*"), recursive=True):
            if path.lower().endswith(AUDIO_EXTS):
                stem = os.path.splitext(os.path.basename(path))[0]
                if stem in labels:
                    pairs.append((path, labels[stem]))
        if pairs:
            return pairs

    # 2) Folder-name heuristics (exact segment match — substring matching
    #    mislabels e.g. test_REALworld_samples as bonafide)
    pairs = []
    for path in glob.glob(os.path.join(data_dir, "**", "*.*"), recursive=True):
        if not path.lower().endswith(AUDIO_EXTS):
            continue
        label = _label_for_path(path)
        if label is not None:
            pairs.append((path, label))
    return pairs


def _label_for_path(path: str) -> Optional[int]:
    """Label for a file path, or None when undeterminable.

    Priority: exact directory-segment match (real/, fake/, scam/, ...), then
    filename-prefix heuristics for mixed folders (ai_*.flac vs real_*.flac).
    """
    parts = [p.lower() for p in os.path.normpath(path).split(os.sep)]
    for seg in parts[:-1]:  # directory segments only, never the filename
        if seg in BONA_ALIASES:
            return 0
        if seg in SPOOF_ALIASES:
            return 1
    stem = os.path.splitext(parts[-1])[0].lower()
    if stem.startswith(("ai_", "synth", "fake_", "spoof_", "clone_")):
        return 1
    if stem.startswith(("real", "human", "bonafide", "genuine")):
        return 0
    return None


def _load_audio(path: str, target_sr: int) -> Optional[np.ndarray]:
    try:
        import soundfile as sf
        audio, sr = sf.read(path, dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        if sr != target_sr:
            import scipy.signal
            audio = scipy.signal.resample(audio, int(len(audio) * target_sr / sr))
        return audio.astype(np.float32)
    except Exception:
        return None


class ASVspoofDataset(Dataset):
    """
    Real-audio anti-spoofing dataset with on-the-fly augmentation.
    Falls back to the procedural synthetic generator when no real files exist,
    clearly flagged via `is_synthetic=True` (results from this mode must never
    be quoted as real-world performance).

    `data_dir` may be a single root or a list of roots (merged).
    Loaded audio is cached in memory — clips are small (seconds) and epochs
    re-read every item.
    """

    def __init__(self, data_dir=None, samples: int = 32000,
                 augment: bool = True, synthetic_fallback: int = 400, seed: int = 42):
        self.samples = samples
        self.augment = augment
        self.rng = random.Random(seed)

        roots: List[str] = []
        if data_dir:
            if isinstance(data_dir, (list, tuple)):
                roots = [d for d in data_dir if d]
            else:
                roots = [d.strip() for d in str(data_dir).split(",") if d.strip()]

        pairs: List[Tuple[str, int]] = []
        for root in roots:
            pairs.extend(build_file_list(root))
        self.pairs = pairs
        self.is_synthetic = not self.pairs

        if self.is_synthetic:
            from backend.models.train_calibrate import generate_audio_sample
            self._gen = generate_audio_sample
            self.pairs = [("synthetic", i % 2) for i in range(synthetic_fallback)]

        self._cache: Dict[int, np.ndarray] = {}

    def __len__(self):
        return len(self.pairs)

    def _fix_length(self, audio: np.ndarray) -> np.ndarray:
        n = self.samples
        if len(audio) >= n:
            start = self.rng.randint(0, len(audio) - n)
            return audio[start:start + n]
        reps = int(np.ceil(n / max(1, len(audio))))
        return np.tile(audio, reps)[:n]

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        path, label = self.pairs[idx]
        if self.is_synthetic:
            audio = self._gen(duration=self.samples / 16000.0,
                              is_deepfake=(label == 1))
        else:
            if idx not in self._cache:
                raw = _load_audio(path, settings.audio.sample_rate)
                self._cache[idx] = raw if raw is not None \
                    else np.zeros(self.samples, dtype=np.float32)
            audio = self._cache[idx]

        audio = self._fix_length(np.asarray(audio))

        if self.augment:
            audio = self._apply_augment(audio)

        # Peak normalize
        peak = float(np.max(np.abs(audio))) + 1e-6
        audio = (audio / peak).astype(np.float32)
        return torch.from_numpy(audio), label

    def _apply_augment(self, audio: np.ndarray) -> np.ndarray:
        r = self.rng.random()
        # Telephony bandpass on 30% of samples (G.711 robustness)
        if r < 0.30:
            audio = apply_telephony_filter(audio, fs=settings.audio.sample_rate)
        # Additive Gaussian noise on 25%
        if self.rng.random() < 0.25:
            snr_db = self.rng.uniform(10.0, 35.0)
            sig_p = float(np.mean(audio ** 2)) + 1e-9
            noise_p = sig_p / (10 ** (snr_db / 10.0))
            audio = audio + np.random.normal(0, np.sqrt(noise_p), len(audio)).astype(np.float32)
        # Random gain on 20%
        if self.rng.random() < 0.20:
            audio = audio * self.rng.uniform(0.4, 1.4)
        # Soft clipping (codec saturation) on 10%
        if self.rng.random() < 0.10:
            audio = np.tanh(audio * 1.8)
        return audio.astype(np.float32)
