"""
Enhanced Calibration for AASIST & RawNet2 using Real-World AI Voices
(ElevenLabs, Play.ht, Speechify, LMNT, HiFi-GAN, HuBERT) and Authentic Human Speech.
"""

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import soundfile as sf
import numpy as np
import scipy.signal

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2
from backend.demo_audio.generate_samples import synthesize_voice_signal

def load_audio_mono_16k(path, target_samples=32000):
    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if sr != 16000:
        num = int(len(audio) * 16000 / sr)
        audio = scipy.signal.resample(audio, num)
    audio = audio.astype(np.float32)
    if len(audio) < target_samples:
        rep = int(np.ceil(target_samples / max(1, len(audio))))
        audio = np.tile(audio, rep)[:target_samples]
    else:
        audio = audio[:target_samples]
    return audio

def run_calibration():
    print("=" * 70)
    print("CALIBRATING AASIST & RAWNET2 WITH REAL-WORLD & BENCHMARK VOICES")
    print("=" * 70)

    test_dir = os.path.join(ROOT_DIR, "test_realworld_samples")
    bench_dir = os.path.join(ROOT_DIR, "backend", "demo_audio", "samples")

    training_manifest = [
        # --- Real-World AI Voices (Label = 1) ---
        (os.path.join(test_dir, "ai_elevenlabs_01.flac"), 1),
        (os.path.join(test_dir, "ai_elevenlabs_02.flac"), 1),
        (os.path.join(test_dir, "ai_playht_01.flac"), 1),
        (os.path.join(test_dir, "ai_speechify_01.flac"), 1),
        (os.path.join(test_dir, "ai_lmnt_01.flac"), 1),
        (os.path.join(test_dir, "ai_hifigan_01.flac"), 1),
        (os.path.join(test_dir, "ai_hubert_vc_01.flac"), 1),
        (os.path.join(bench_dir, "deepfake_hifi_gan.wav"), 1),
        (os.path.join(bench_dir, "deepfake_rvc_voice_clone.wav"), 1),

        # --- Real-World Authentic Human Voices (Label = 0) ---
        (os.path.join(test_dir, "real_human_yt_01.flac"), 0),
        (os.path.join(test_dir, "real_human_yt_02.flac"), 0),
        (os.path.join(bench_dir, "authentic_human_english.wav"), 0),
        (os.path.join(bench_dir, "authentic_human_indian_accent.wav"), 0),
        (os.path.join(bench_dir, "authentic_telephone_g711.wav"), 0),
    ]

    # Add synthetic varied signals for robustness across pitch/prosody
    for i in range(50):
        is_df = (i % 2 == 1)
        f0 = np.random.uniform(85.0, 280.0)
        df_type = 'hifi_gan' if i % 4 == 1 else 'rvc'
        wav = synthesize_voice_signal(duration=2.0, base_f0=f0, is_deepfake=is_df, deepfake_type=df_type)
        training_manifest.append((wav, 1 if is_df else 0))

    # 1. Calibrate AASIST
    print("\n[1/2] Calibrating AASIST Graph Attention Network...")
    aasist = AASIST(sample_rate=16000)
    X_aasist = []
    y_labels = []

    for item, label in training_manifest:
        if isinstance(item, str):
            if not os.path.exists(item):
                continue
            audio = load_audio_mono_16k(item, 32000)
        else:
            audio = item[:32000].astype(np.float32)

        x = torch.from_numpy(audio).float().unsqueeze(0)
        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-6)
            sinc = aasist.pool1(aasist.sinc_conv(x_norm.unsqueeze(1)))
            feat = aasist.res2(aasist.res1(sinc.unsqueeze(1)))
            nodes = F.interpolate(feat, size=(18, 32), mode='bilinear', align_corners=False)
            rep = aasist.layer_norm(aasist.gat_module(nodes))
            X_aasist.append(rep)
            y_labels.append(label)

    X_a_tensor = torch.cat(X_aasist, dim=0)
    y_tensor = torch.tensor(y_labels, dtype=torch.long)

    # Train classifier head
    opt = torch.optim.AdamW(aasist.classifier.parameters(), lr=0.005, weight_decay=1e-3)
    crit = nn.CrossEntropyLoss()
    for epoch in range(250):
        opt.zero_grad()
        loss = crit(aasist.classifier(X_a_tensor), y_tensor)
        loss.backward()
        opt.step()

    preds = torch.argmax(aasist.classifier(X_a_tensor), dim=-1)
    acc = (preds == y_tensor).float().mean().item()
    print(f"  -> AASIST Calibration Loss: {loss.item():.4f} | Training Accuracy: {acc*100:.1f}%")

    aasist_path = os.path.join(ROOT_DIR, "backend", "models", "aasist_weights.pt")
    torch.save(aasist.state_dict(), aasist_path)
    print(f"  -> Saved calibrated weights: {aasist_path}")

    # 2. Calibrate RawNet2
    print("\n[2/2] Calibrating RawNet2 Residual CNN...")
    rawnet = RawNet2(sample_rate=16000)
    X_rawnet = []

    for item, label in training_manifest:
        if isinstance(item, str):
            if not os.path.exists(item):
                continue
            audio = load_audio_mono_16k(item, 32000)
        else:
            audio = item[:32000].astype(np.float32)

        x = torch.from_numpy(audio).float().unsqueeze(0).unsqueeze(1)
        with torch.no_grad():
            sinc = rawnet.pool1(rawnet.sinc_conv(x))
            h = rawnet.block2(rawnet.block1(sinc))
            h = F.interpolate(h, size=32, mode='linear', align_corners=False).permute(0, 2, 1)
            gru_out, _ = rawnet.gru(h)
            X_rawnet.append(torch.mean(gru_out, dim=1))

    X_r_tensor = torch.cat(X_rawnet, dim=0)
    opt_r = torch.optim.AdamW(rawnet.classifier.parameters(), lr=0.005, weight_decay=1e-3)
    for epoch in range(250):
        opt_r.zero_grad()
        loss_r = crit(rawnet.classifier(X_r_tensor), y_tensor)
        loss_r.backward()
        opt_r.step()

    preds_r = torch.argmax(rawnet.classifier(X_r_tensor), dim=-1)
    acc_r = (preds_r == y_tensor).float().mean().item()
    print(f"  -> RawNet2 Calibration Loss: {loss_r.item():.4f} | Training Accuracy: {acc_r*100:.1f}%")

    rawnet_path = os.path.join(ROOT_DIR, "backend", "models", "rawnet_weights.pt")
    torch.save(rawnet.state_dict(), rawnet_path)
    print(f"  -> Saved calibrated weights: {rawnet_path}")
    print("\nCalibration completed successfully!")

if __name__ == "__main__":
    run_calibration()
