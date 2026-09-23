"""
AEGIS Training Package — real-data anti-spoofing training pipeline.

Modules:
    asvspoof  — ASVspoof 2019/2021 LA dataset loading + synthetic fallback
                (includes on-the-fly telephony/noise augmentation)
    train     — supervised training of AASIST & RawNet2 with EER evaluation

Usage:
    python -m backend.training.train --data-dir /path/ASVspoof2019_LA --epochs 30
"""

from backend.training.asvspoof import build_file_list, ASVspoofDataset  # noqa: F401
