"""
Global Configuration and Hyperparameters for Voice Cloning Detector.
"""

import os
import torch

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REAL_DIR = os.path.join(DATA_DIR, "real")
FAKE_DIR = os.path.join(DATA_DIR, "fake")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "checkpoints")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REAL_DIR, exist_ok=True)
os.makedirs(FAKE_DIR, exist_ok=True)
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Hardware Device (CPU is fully supported and eliminates MPS SDPA attention limitations)
DEVICE = torch.device("cpu")

# Audio Preprocessing Specs
SAMPLE_RATE = 16000
CHUNK_DURATION = 4.0  # 4-second chunks
TARGET_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)  # 64,000 samples

# STFT & Spectrogram Parameters for Branch 2
N_FFT = 512
HOP_LENGTH = 256
WIN_LENGTH = 512

# Branch 1: Self-Supervised Feature Extractor
SSL_MODEL_NAME = "facebook/wav2vec2-base"
SSL_HIDDEN_DIM = 768
SSL_NUM_LAST_LAYERS = 4
SSL_CLASSIFIER_HIDDEN = 256
SSL_DROPOUT = 0.3

# Branch 2: Phase-Aware ResNet-18
RESNET_IN_CHANNELS = 2  # Channel 0: Log-Magnitude, Channel 1: Instantaneous Frequency Deviation
RESNET_FC_HIDDEN = 128
RESNET_DROPOUT = 0.3

# Branch 3: Hand-Crafted Temporal Artifact Features
# Total features extracted:
# 1. Silence pattern analysis (4 features: ratio, mean duration, std duration, count)
# 2. Breathing detection (3 features: breath count, breath energy ratio, breath regularity)
# 3. Pitch jitter & shimmer (4 features: pitch mean, pitch std, jitter_local, shimmer_local)
# 4. Long-term spectral statistics (4 features: centroid, bandwidth, skewness, kurtosis)
# 5. Sub-band energy variance across 8 sub-bands (8 features)
TEMPORAL_FEATURE_DIM = 23
TEMPORAL_FC_HIDDEN = 128
TEMPORAL_DROPOUT = 0.3

# Ensemble Weights & Decision
DEFAULT_BRANCH_WEIGHTS = [0.50, 0.30, 0.20]
DECISION_THRESHOLD = 0.50

# Training Hyperparameters
BATCH_SIZE = 16  # Efficient for CPU/MPS
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 0.01
EPOCHS = 50
PATIENCE = 7
LABEL_SMOOTHING = 0.05
COSINE_T0 = 10

# Data Splits
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
