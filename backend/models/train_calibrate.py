"""
AASIST & RawNet2 Neural Calibration & Pre-Training Pipeline.

Trains the learnable SincConv filters, Spectro-Temporal Graph Attention Networks,
and Residual GRU layers on diverse authentic human speech and synthetic deepfake waveforms.
"""

import os
import random
import numpy as np
import torch
import torch.nn as nn
from scipy.signal import butter, sosfilt
import soundfile as sf

from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2


def generate_audio_sample(
    duration: float = 2.0,
    sample_rate: int = 16000,
    is_deepfake: bool = False,
    deepfake_type: str = "hifi_gan",
    base_f0: float = 140.0,
    ambient_snr: float = 28.0,
    is_telephony: bool = False,
) -> np.ndarray:
    """
    Generates a 2.0-second 16kHz audio waveform with known physical/neural biometrics.
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # 1. Pitch Contour & Micro-Jitter
    if is_deepfake:
        # Neural TTS: flat pitch contour or robotic periodic step, lack of vocal micro-jitter
        f0_curve = np.full(n_samples, base_f0)
        f0_curve += 0.8 * np.sin(2 * np.pi * 1.5 * t)
        jitter = np.zeros(n_samples)
    else:
        # Authentic human: natural intonation contour + cycle-to-cycle vocal fold micro-jitter
        f0_curve = base_f0 + 18.0 * np.sin(2 * np.pi * 0.8 * t) + 10.0 * np.cos(2 * np.pi * 1.6 * t)
        jitter = np.random.normal(0, base_f0 * 0.014, n_samples)
        f0_curve += jitter

    f0_curve = np.clip(f0_curve, 60.0, 450.0)
    phase = 2 * np.pi * np.cumsum(f0_curve) / sample_rate

    # 2. Harmonics
    n_harmonics = 32
    glottal = np.zeros(n_samples)
    for h in range(1, n_harmonics + 1):
        amp = 1.0 / (h ** 1.35)
        freq = base_f0 * h
        if is_deepfake and deepfake_type == "hifi_gan" and freq >= 3200:
            # Neural vocoder phase dispersion & high-band energy plateau
            h_phase = phase * h + np.random.uniform(-np.pi, np.pi)
            amp *= 1.7
        elif is_deepfake and deepfake_type == "rvc":
            # Voice conversion boundary discontinuity
            discontinuity = np.sign(np.sin(2 * np.pi * 3.0 * t)) * 0.7
            h_phase = phase * h + discontinuity
        else:
            h_phase = phase * h
        glottal += amp * np.sin(h_phase)

    # 3. Formant filter simulation
    vowel_types = [
        [(580, 80, 1.0), (1200, 100, 0.7), (2500, 150, 0.4), (3700, 200, 0.25)],  # /a/
        [(280, 60, 1.0), (2250, 90, 0.6), (3000, 120, 0.3), (3800, 180, 0.2)],    # /i/
        [(350, 70, 1.0), (850, 80, 0.7), (2400, 140, 0.3), (3500, 180, 0.2)],     # /u/
        [(500, 80, 1.0), (1800, 100, 0.6), (2600, 130, 0.35), (3700, 190, 0.2)],  # /e/
    ]
    formants = random.choice(vowel_types)
    speech = np.zeros_like(glottal)
    for f_center, bw, gain in formants:
        decay = np.exp(-np.pi * bw / sample_rate)
        speech += glottal * gain * (0.7 + 0.3 * np.sin(2 * np.pi * (f_center / sample_rate) * np.arange(n_samples)))

    # 4. Telephony Simulation if requested
    if is_telephony:
        sos = butter(4, [300, 3400], btype="bandpass", fs=sample_rate, output="sos")
        speech = sosfilt(sos, speech)

    # 5. Room Acoustics & Noise Floor
    speech_power = np.mean(speech ** 2) + 1e-9
    noise_power = speech_power / (10 ** (ambient_snr / 10.0))
    noise = np.random.normal(0, np.sqrt(noise_power), n_samples)
    audio = speech + noise

    # Peak normalize to [-1.0, 1.0]
    peak = np.max(np.abs(audio)) + 1e-6
    return (audio / peak).astype(np.float32)


def build_dataset(n_samples: int = 300, sample_rate: int = 16000):
    """
    Constructs balanced dataset of authentic human and synthetic deepfake waveforms.
    """
    X = []
    y = []

    # Include existing real samples if available
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "demo_audio", "samples")
    if os.path.exists(samples_dir):
        for fname in os.listdir(samples_dir):
            if fname.endswith(".wav"):
                fpath = os.path.join(samples_dir, fname)
                audio, sr = sf.read(fpath)
                if len(audio) >= 32000:
                    for offset in range(0, len(audio) - 32000 + 1, 16000):
                        chunk = audio[offset : offset + 32000].astype(np.float32)
                        peak = np.max(np.abs(chunk)) + 1e-6
                        chunk = chunk / peak
                        label = 1 if "deepfake" in fname else 0
                        X.append(chunk)
                        y.append(label)

    # Generate synthetic diverse dataset
    for i in range(n_samples):
        is_df = (i % 2 == 1)
        base_f0 = random.uniform(85.0, 270.0)
        df_type = random.choice(["hifi_gan", "rvc", "hifi_gan"])
        snr = random.uniform(18.0, 42.0)
        is_tel = random.random() < 0.25

        wav = generate_audio_sample(
            duration=2.0,
            sample_rate=sample_rate,
            is_deepfake=is_df,
            deepfake_type=df_type,
            base_f0=base_f0,
            ambient_snr=snr,
            is_telephony=is_tel,
        )
        X.append(wav)
        y.append(1 if is_df else 0)

    X = np.stack(X, axis=0)
    y = np.array(y, dtype=np.int64)
    return torch.from_numpy(X).float(), torch.from_numpy(y).long()


def train_models():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[TRAIN] Training AASIST & RawNet2 on {device}...")

    X, y = build_dataset(n_samples=320)
    dataset_size = len(X)
    print(f"[DATASET] Total samples: {dataset_size} (Bona Fide: {torch.sum(y == 0).item()}, Spoof: {torch.sum(y == 1).item()})")

    # Train AASIST
    print("\n--- Training AASIST (Spectro-Temporal GAT) ---")
    aasist = AASIST(sample_rate=16000).to(device)
    optimizer = torch.optim.AdamW(aasist.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    batch_size = 16
    epochs = 15
    indices = np.arange(dataset_size)

    for ep in range(epochs):
        np.random.shuffle(indices)
        total_loss = 0.0
        correct = 0
        aasist.train()

        for b_start in range(0, dataset_size, batch_size):
            b_idx = indices[b_start : b_start + batch_size]
            b_x = X[b_idx].to(device)
            b_y = y[b_idx].to(device)

            optimizer.zero_grad()
            logits = aasist(b_x)
            loss = criterion(logits, b_y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(b_idx)
            preds = torch.argmax(logits, dim=1)
            correct += torch.sum(preds == b_y).item()

        acc = correct / dataset_size * 100.0
        avg_loss = total_loss / dataset_size
        if (ep + 1) % 5 == 0 or ep == epochs - 1:
            print(f"Epoch {ep+1:02d}/{epochs} - Loss: {avg_loss:.4f} - Accuracy: {acc:.1f}%")

    # Save AASIST weights
    weights_dir = os.path.dirname(__file__)
    aasist_path = os.path.join(weights_dir, "aasist_weights.pt")
    torch.save(aasist.state_dict(), aasist_path)
    print(f"[SAVED] AASIST weights saved to {aasist_path}")

    # Train RawNet2
    print("\n--- Training RawNet2 (SincNet + Feature Map Scaling) ---")
    rawnet = RawNet2(sample_rate=16000).to(device)
    optimizer = torch.optim.AdamW(rawnet.parameters(), lr=1e-3, weight_decay=1e-4)

    for ep in range(epochs):
        np.random.shuffle(indices)
        total_loss = 0.0
        correct = 0
        rawnet.train()

        for b_start in range(0, dataset_size, batch_size):
            b_idx = indices[b_start : b_start + batch_size]
            b_x = X[b_idx].to(device)
            b_y = y[b_idx].to(device)

            optimizer.zero_grad()
            logits = rawnet(b_x)
            loss = criterion(logits, b_y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(b_idx)
            preds = torch.argmax(logits, dim=1)
            correct += torch.sum(preds == b_y).item()

        acc = correct / dataset_size * 100.0
        avg_loss = total_loss / dataset_size
        if (ep + 1) % 5 == 0 or ep == epochs - 1:
            print(f"Epoch {ep+1:02d}/{epochs} - Loss: {avg_loss:.4f} - Accuracy: {acc:.1f}%")

    # Save RawNet2 weights
    rawnet_path = os.path.join(weights_dir, "rawnet_weights.pt")
    torch.save(rawnet.state_dict(), rawnet_path)
    print(f"[SAVED] RawNet2 weights saved to {rawnet_path}")


if __name__ == "__main__":
    train_models()
