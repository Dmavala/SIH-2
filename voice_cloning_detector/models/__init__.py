"""
Models package for Voice Cloning / Deepfake Speech Detection System.
"""

from .branch1_ssl import Branch1SSL
from .branch2_phase import Branch2PhaseResNet
from .branch3_temporal import Branch3Temporal
from .ensemble import EnsembleVoiceCloningDetector

__all__ = [
    "Branch1SSL",
    "Branch2PhaseResNet",
    "Branch3Temporal",
    "EnsembleVoiceCloningDetector",
]
