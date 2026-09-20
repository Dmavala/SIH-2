# AI-Powered Voice Cloning & Deepfake Speech Detection System

An enterprise-grade, state-of-the-art deepfake speech and voice cloning detection pipeline in Python. Accurately discriminates authentic human speech from AI-generated or cloned speech produced by modern generative audio systems including **RVC, XTTS-v2, OpenVoice, ElevenLabs, Fish Speech, and Bark**.

---

## The Core Attack Anatomy & Forensic Detection

Modern neural vocoders and autoregressive TTS models bypass naive "mel-spectrogram + CNN" detectors because their spectral magnitude distributions appear realistic. However, they leave unmistakable mathematical and biological artifacts:

1. **Phase Inconsistency & Incoherence:**
   Neural vocoders (HiFi-GAN, MelGAN, BigVGAN) reconstruct phase artificially from mel-spectrograms. This creates unnatural distributions and phase jumps at higher frequencies ($>4$ kHz).
2. **Biological Respiration Absences:**
   Human speech requires biological respiration. Before phrases and sentences, authentic speakers produce natural inhalation breath sounds (broadband acoustic friction concentrated between $100$ Hz and $1000$ Hz). AI speech exhibits unnaturally sterile digital silence between utterances.
3. **Micro-Prosody Flatness (Jitter & Shimmer):**
   Human vocal folds produce natural cycle-to-cycle perturbation in fundamental frequency (Jitter $> 1.0\%$) and peak amplitude (Shimmer $> 3.5\%$). Synthetic models produce unnaturally flat or mathematically rigid pitch trajectories.

---

## 3-Branch Ensemble Architecture

```
                                  [Raw Audio 16kHz]
                                          |
          +-------------------------------+-------------------------------+
          |                               |                               |
          v                               v                               v
+-------------------+           +-------------------+           +-------------------+
|     Branch 1      |           |     Branch 2      |           |     Branch 3      |
|  Wav2Vec 2.0 SSL  |           | Phase ResNet-18   |           | Temporal/Bio MLPs |
|  (Frozen Backbone)|           | Dual-Channel STFT |           | 23 Hand-Crafted   |
|   Weight: 0.50    |           |   Weight: 0.30    |           |   Weight: 0.20    |
+-------------------+           +-------------------+           +-------------------+
          |                               |                               |
          v                               v                               v
      P_fake_1                        P_fake_2                        P_fake_3
          |                               |                               |
          +-------------------------------+-------------------------------+
                                          |
                                          v
                    Final Risk Score = 0.50*P1 + 0.30*P2 + 0.20*P3
                    Decision: REAL (Score <= 0.50) | FAKE (Score > 0.50)
                    Confidence = |Score - 0.50| * 200%
```

### Branch 1: Self-Supervised Feature Extractor (Weight = 0.50)
- **Backbone**: `facebook/wav2vec2-base` (FROZEN parameters).
- **Multi-Layer Representation**: Learnable softmax weights dynamically combine the representations of the last 4 transformer hidden layers.
- **Classifier Head**: `Linear(768, 256) -> LayerNorm -> ReLU -> Dropout(0.3) -> Linear(256, 1) -> Sigmoid`.

### Branch 2: Phase-Aware Spectrogram Classifier (Weight = 0.30)
- **Dual-Channel Input**:
  - *Channel 0*: Log-magnitude STFT ($\log |S(f, t)| + \epsilon$).
  - *Channel 1*: Instantaneous Frequency Deviation ($\Delta \text{unwrap}(\phi(f, t)) / \Delta t$).
- **Backbone**: ResNet-18 adapted for 2 input channels with ImageNet weight transfer.
- **Classifier Head**: `Linear(512, 128) -> LayerNorm -> ReLU -> Dropout(0.3) -> Linear(128, 1) -> Sigmoid`.

### Branch 3: Hand-Crafted Temporal & Biological Artifacts (Weight = 0.20)
Extracts a 23-dimensional acoustic and biological vector:
- **Silence Patterns (4 dims)**: Silence ratio, mean duration, standard deviation of duration, segment count.
- **Breathing Detection (3 dims)**: Inhalation count in non-speech regions, 100-1000 Hz pause energy ratio, regularity.
- **Pitch Jitter & Shimmer (4 dims)**: Fundamental frequency mean, standard deviation, cycle-to-cycle local jitter, cycle-to-cycle local shimmer.
- **Spectral Statistics (4 dims)**: Spectral centroid, bandwidth, skewness, and kurtosis.
- **Sub-Band Energy Variances (8 dims)**: Temporal variance across 8 sub-bands (0 to 8000 Hz).
- **Classifier**: `Linear(23, 128) -> LayerNorm -> ReLU -> Dropout(0.3) -> Linear(128, 1) -> Sigmoid`.

---

## Directory Structure

```
voice_cloning_detector/
├── config.py                 # System hyperparameters & audio specs
├── feature_extraction.py     # Phase STFT & 23D temporal feature extractors
├── dataset.py                # Audio loader, chunker, speaker-split & augmentations
├── generate_fake_data.py     # Multi-tool benchmark dataset generator (RVC, XTTS, etc.)
├── train.py                  # Joint multi-task training with early stopping on Val EER
├── evaluate.py               # EER, ROC-AUC, confusion matrix, per-generator report
├── inference.py              # CLI & batch inference (< 5s latency per clip)
├── demo.py                   # Interactive Streamlit Web UI
├── models/
│   ├── branch1_ssl.py        # Frozen Wav2Vec2 + multi-layer pooling
│   ├── branch2_phase.py      # Dual-channel Phase ResNet-18
│   ├── branch3_temporal.py   # 23D acoustic artifact classifier
│   └── ensemble.py           # 3-branch weighted decision fusion
├── tests/
│   └── test_components.py    # Unit tests for all modules
├── checkpoints/              # Saved model weights (best_model.pt)
├── data/
│   ├── real/                 # Authentic human speech clips
│   └── fake/                 # AI cloned speech clips
└── reports/                  # Evaluation JSON and PNG visualizations
```

---

## Quickstart & CLI Usage

### 1. Generate Synthetic Benchmark Dataset
```bash
python3 -m voice_cloning_detector.generate_fake_data --num_real 30 --num_fake 30
```

### 2. Run Single-File Inference
```bash
python3 -m voice_cloning_detector.inference --audio path/to/recording.wav
```

Output:
```
==================================================
   VOICE CLONING DETECTION RESULT
==================================================
Audio File:      path/to/recording.wav
Duration:        4.0 s (analyzed in 1 chunk(s))
Inference Time:  0.42 s (0.42 s/chunk)
--------------------------------------------------
PREDICTION:      FAKE
CONFIDENCE:      93.4%
PROBABILITY:     0.9672 (Threshold: 0.50)
--------------------------------------------------
BRANCH BREAKDOWN:
  Branch 1 (Wav2Vec2 SSL)    [Weight 50%]: 0.9810
  Branch 2 (Phase ResNet-18) [Weight 30%]: 0.9542
  Branch 3 (Temporal/Bio)    [Weight 20%]: 0.9520
--------------------------------------------------
ACOUSTIC ARTIFACTS:
  Breaths Detected:       0
  Silence Ratio:          15.2%
  Pitch Jitter (local):   0.0013
  Pitch Shimmer (local):  0.0078
==================================================
```

### 3. Launch Interactive Streamlit Web App
```bash
streamlit run voice_cloning_detector/demo.py
```

### 4. Train Model
```bash
python3 -m voice_cloning_detector.train --epochs 25 --batch_size 16 --lr 0.0001
```

### 5. Evaluate Performance
```bash
python3 -m voice_cloning_detector.evaluate
```
Reports generated:
- `reports/evaluation_report.json`
- `reports/roc_curve.png`
- `reports/confusion_matrix.png`
- `reports/generator_breakdown.png`
