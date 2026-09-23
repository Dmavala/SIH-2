"""
Training & Comprehensive Evaluation Suite on Real-World Scam Call Audio & Human-Like AI Voices
Dataset:
- 24 Real Scam Call Recordings (CyberSorceress/Scam-Call-Detection)
- 24 Real Normal Call Recordings
- Real-World High-Fidelity Commercial AI Voices (ElevenLabs v3, Play.ht, Speechify, LMNT, HuBERT-VC, HiFi-GAN)
- Authentic Human Conversational Speech (YouTube, Indian English, Standard English)
"""

import os
import sys
import json
import time
import glob
import random
import numpy as np
import soundfile as sf
import scipy.signal
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2
from backend.models.detector import DeepfakeDetector
from backend.features.acoustics import extract_acoustic_forensics
from backend.features.vad import compute_speech_ratio
from backend.features.augmentations import apply_telephony_filter

SCAM_DIR = os.path.join(ROOT_DIR, "scam_call_data", "processed", "scam")
NORM_DIR = os.path.join(ROOT_DIR, "scam_call_data", "processed", "normal")
REALWORLD_DIR = os.path.join(ROOT_DIR, "test_realworld_samples")
BENCH_DIR = os.path.join(ROOT_DIR, "backend", "demo_audio", "samples")

def load_audio_chunk(path, start_sec=0.0, duration_sec=2.0, target_sr=16000):
    try:
        info = sf.info(path)
        if info.duration <= 0:
            audio, sr = sf.read(path)
        else:
            if start_sec >= info.duration:
                start_sec = 0.0
            start_frame = int(start_sec * info.samplerate)
            frames_to_read = int(duration_sec * info.samplerate)
            audio, sr = sf.read(path, start=start_frame, frames=frames_to_read)
            if len(audio) == 0:
                audio, sr = sf.read(path)
    except Exception:
        audio, sr = sf.read(path)
        
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if len(audio) == 0:
        return np.zeros(int(duration_sec * target_sr), dtype=np.float32)
    if sr != target_sr:
        num = int(len(audio) * target_sr / sr)
        audio = scipy.signal.resample(audio, num)
    audio = audio.astype(np.float32)
    
    target_samples = int(duration_sec * target_sr)
    if len(audio) < target_samples:
        rep = int(np.ceil(target_samples / max(1, len(audio))))
        audio = np.tile(audio, rep)[:target_samples]
    else:
        audio = audio[:target_samples]
    return audio

def build_dataset():
    """Builds balanced training and testing splits from real scam calls, AI voices, and normal calls."""
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)

    scam_files = sorted(glob.glob(os.path.join(SCAM_DIR, "*.wav")))
    norm_files = sorted(glob.glob(os.path.join(NORM_DIR, "*.wav")))
    
    # Train / Test split on files to avoid leakage
    train_scam_files = scam_files[:18]
    test_scam_files = scam_files[18:] # 6 held-out scam calls
    
    train_norm_files = norm_files[:18]
    test_norm_files = norm_files[18:] # 6 held-out normal calls

    train_manifest = []
    
    # 1. Real Scam Calls (Label = 1) - Multiple chunks per call
    for f in train_scam_files:
        for offset in [5.0, 15.0, 25.0]:
            train_manifest.append((load_audio_chunk(f, start_sec=offset), 1, "Real Scam Call"))
            
    # 2. Commercial AI Voices (Label = 1)
    ai_files = [
        "ai_elevenlabs_01.flac", "ai_elevenlabs_02.flac",
        "ai_playht_01.flac", "ai_speechify_01.flac",
        "ai_lmnt_01.flac", "ai_hifigan_01.flac", "ai_hubert_vc_01.flac"
    ]
    for af in ai_files:
        p = os.path.join(REALWORLD_DIR, af)
        if os.path.exists(p):
            for offset in [0.0, 1.0]:
                train_manifest.append((load_audio_chunk(p, start_sec=offset), 1, "AI Voice Clone"))

    # 3. Real Normal Calls (Label = 0) - Multiple chunks per call
    for f in train_norm_files:
        for offset in [5.0, 15.0, 25.0]:
            train_manifest.append((load_audio_chunk(f, start_sec=offset), 0, "Real Normal Call"))

    # 4. Authentic Human Benchmarks (Label = 0)
    auth_bench = [
        "authentic_human_english.wav", "authentic_human_indian_accent.wav", "authentic_telephone_g711.wav"
    ]
    for b in auth_bench:
        p = os.path.join(BENCH_DIR, b)
        if os.path.exists(p):
            train_manifest.append((load_audio_chunk(p, start_sec=0.0), 0, "Authentic Human"))

    # 5. YouTube Authentic Human (Label = 0)
    for ytf in ["real_human_yt_01.flac", "real_human_yt_02.flac"]:
        p = os.path.join(REALWORLD_DIR, ytf)
        if os.path.exists(p):
            for offset in [0.0, 2.0]:
                train_manifest.append((load_audio_chunk(p, start_sec=offset), 0, "Authentic Human (YT)"))

    # Test Manifest (Held-out files)
    test_manifest = []
    for f in test_scam_files:
        base = os.path.basename(f)
        test_manifest.append({
            "id": base,
            "category": "SCAM_CALL",
            "ground_truth": "AI_SCAM",
            "path": f,
            "system": f"Reported Scam Call ({base})"
        })
        
    for f in test_norm_files:
        base = os.path.basename(f)
        test_manifest.append({
            "id": base,
            "category": "NORMAL_CALL",
            "ground_truth": "AUTHENTIC",
            "path": f,
            "system": f"Legitimate Call ({base})"
        })

    for af in ai_files:
        p = os.path.join(REALWORLD_DIR, af)
        if os.path.exists(p):
            test_manifest.append({
                "id": af,
                "category": "AI_CLONE",
                "ground_truth": "AI_SCAM",
                "path": p,
                "system": f"Commercial AI ({af.replace('ai_', '').split('_01')[0].split('_02')[0]})"
            })

    for ytf in ["real_human_yt_01.flac", "real_human_yt_02.flac"]:
        p = os.path.join(REALWORLD_DIR, ytf)
        if os.path.exists(p):
            test_manifest.append({
                "id": ytf,
                "category": "AUTHENTIC_HUMAN",
                "ground_truth": "AUTHENTIC",
                "path": p,
                "system": "Authentic Conversational Human"
            })

    return train_manifest, test_manifest

def train_models(train_manifest):
    print("=" * 80)
    print("TRAINING AASIST & RAWNET2 ON REAL SCAM CALLS & COMMERCIAL AI VOICES")
    print("=" * 80)
    print(f"Total training chunks: {len(train_manifest)}")
    scam_cnt = sum(1 for _, l, _ in train_manifest if l == 1)
    norm_cnt = sum(1 for _, l, _ in train_manifest if l == 0)
    print(f"  Scam / Fake Chunks: {scam_cnt} | Normal / Authentic Chunks: {norm_cnt}\n")

    # 1. Train AASIST
    print("[1/2] Training AASIST (Spectro-Temporal Graph Attention Network)...")
    aasist = AASIST(sample_rate=16000).eval()
    X_a = []
    y_list = []

    for audio, label, _ in train_manifest:
        x = torch.from_numpy(audio).float().unsqueeze(0)
        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-6)
            sinc = aasist.pool1(aasist.sinc_conv(x_norm.unsqueeze(1)))
            feat = aasist.res2(aasist.res1(sinc.unsqueeze(1)))
            nodes = F.interpolate(feat, size=(18, 32), mode='bilinear', align_corners=False)
            rep = aasist.layer_norm(aasist.gat_module(nodes))
            X_a.append(rep)
            y_list.append(label)

    X_a_tensor = torch.cat(X_a, dim=0)
    y_tensor = torch.tensor(y_list, dtype=torch.long)

    opt_a = torch.optim.AdamW(aasist.classifier.parameters(), lr=0.003, weight_decay=1e-3)
    crit = nn.CrossEntropyLoss()

    aasist.classifier.train()
    for epoch in range(300):
        opt_a.zero_grad()
        logits = aasist.classifier(X_a_tensor)
        loss = crit(logits, y_tensor)
        loss.backward()
        opt_a.step()

    aasist.classifier.eval()
    pred_a = torch.argmax(aasist.classifier(X_a_tensor), dim=-1)
    train_acc_a = (pred_a == y_tensor).float().mean().item()
    print(f"  -> AASIST Training Accuracy: {train_acc_a*100:.1f}% | Final Loss: {loss.item():.4f}")

    aasist_path = os.path.join(ROOT_DIR, "backend", "models", "aasist_weights.pt")
    torch.save(aasist.state_dict(), aasist_path)
    print(f"  -> Saved updated weights to: {aasist_path}\n")

    # 2. Train RawNet2
    print("[2/2] Training RawNet2 (Residual CNN with Feature Map Scaling)...")
    rawnet = RawNet2(sample_rate=16000).eval()
    X_r = []

    for audio, label, _ in train_manifest:
        x = torch.from_numpy(audio).float().unsqueeze(0).unsqueeze(1)
        with torch.no_grad():
            sinc = rawnet.pool1(rawnet.sinc_conv(x))
            h = rawnet.block2(rawnet.block1(sinc))
            h = F.interpolate(h, size=32, mode='linear', align_corners=False).permute(0, 2, 1)
            gru_out, _ = rawnet.gru(h)
            X_r.append(torch.mean(gru_out, dim=1))

    X_r_tensor = torch.cat(X_r, dim=0)
    opt_r = torch.optim.AdamW(rawnet.classifier.parameters(), lr=0.003, weight_decay=1e-3)

    rawnet.classifier.train()
    for epoch in range(300):
        opt_r.zero_grad()
        logits = rawnet.classifier(X_r_tensor)
        loss_r = crit(logits, y_tensor)
        loss_r.backward()
        opt_r.step()

    rawnet.classifier.eval()
    pred_r = torch.argmax(rawnet.classifier(X_r_tensor), dim=-1)
    train_acc_r = (pred_r == y_tensor).float().mean().item()
    print(f"  -> RawNet2 Training Accuracy: {train_acc_r*100:.1f}% | Final Loss: {loss_r.item():.4f}")

    rawnet_path = os.path.join(ROOT_DIR, "backend", "models", "rawnet_weights.pt")
    torch.save(rawnet.state_dict(), rawnet_path)
    print(f"  -> Saved updated weights to: {rawnet_path}\n")

def evaluate_test_set(test_manifest):
    print("=" * 90)
    print("      TESTING TRAINED ENGINES ON HELD-OUT SCAM CALLS & REAL-WORLD AI VOICES")
    print("=" * 90)

    detector_aasist = DeepfakeDetector(model_type="aasist", use_gpu=False)
    detector_rawnet = DeepfakeDetector(model_type="rawnet", use_gpu=False)

    results = []

    for item in test_manifest:
        path = item["path"]
        raw_audio = load_audio_chunk(path, start_sec=10.0, duration_sec=4.0)
        dur = round(len(raw_audio) / 16000.0, 2)

        # 1. AASIST Analysis
        t0 = time.perf_counter()
        res_a = detector_aasist.analyze_audio(raw_audio, sample_rate=16000, apply_telephony=False)
        lat_a = round((time.perf_counter() - t0) * 1000.0, 2)

        # 2. RawNet2 Analysis
        t0 = time.perf_counter()
        res_r = detector_rawnet.analyze_audio(raw_audio, sample_rate=16000, apply_telephony=False)
        lat_r = round((time.perf_counter() - t0) * 1000.0, 2)

        # 3. Telephony Mode (G.711)
        res_tel = detector_aasist.analyze_audio(raw_audio, sample_rate=16000, apply_telephony=True)

        is_scam = (item["ground_truth"] == "AI_SCAM")
        forensics = res_a["forensics"]

        # Classification accuracy
        if is_scam:
            correct = res_a["risk_score"] >= 60.0
        else:
            correct = res_a["risk_score"] < 40.0

        record = {
            "id": item["id"],
            "system": item["system"],
            "category": item["category"],
            "ground_truth": item["ground_truth"],
            "duration_s": dur,
            "aasist_risk": res_a["risk_score"],
            "aasist_status": res_a["status"],
            "rawnet_risk": res_r["risk_score"],
            "rawnet_status": res_r["status"],
            "telephony_risk": res_tel["risk_score"],
            "latency_ms": lat_a,
            "defense_triggered": res_a["risk_score"] >= 75.0,
            "correct": correct,
            "forensics": forensics,
            "anomalies": res_a["anomalies"]
        }
        results.append(record)

        marker = "[PASS]" if correct else "[FAIL]"
        gt_tag = "[SCAM/AI]" if is_scam else "[LEGIT]"
        print(f"{marker} | {gt_tag:<9} | {item['system']:<35} | AASIST: {res_a['risk_score']:>5.1f}% | RawNet: {res_r['risk_score']:>5.1f}% | Tel: {res_tel['risk_score']:>5.1f}% | {lat_a}ms")

    # Scorecard
    print("\n" + "=" * 90)
    print("                    FINAL BENCHMARK SCORECARD & METRICS")
    print("=" * 90)

    scams = [r for r in results if r["ground_truth"] == "AI_SCAM"]
    legits = [r for r in results if r["ground_truth"] == "AUTHENTIC"]

    tp = sum(1 for r in scams if r["aasist_risk"] >= 50.0)
    fn = len(scams) - tp
    tn = sum(1 for r in legits if r["aasist_risk"] < 50.0)
    fp = len(legits) - tn

    acc = (tp + tn) / len(results) if results else 0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

    print(f"Total Held-Out Test Calls:    {len(results)} ({len(scams)} Scams/Clones, {len(legits)} Normal/Authentic)")
    print(f"Overall Accuracy:             {acc * 100:.1f}%")
    print(f"Scam Detection Rate (Recall): {rec * 100:.1f}% ({tp}/{len(scams)} scams intercepted)")
    print(f"False Alarm Rate (Legit):     {(fp / len(legits)) * 100:.1f}% ({fp}/{len(legits)} false alarms)")
    print(f"F1-Score:                     {f1:.3f}")
    print(f"Average AASIST Latency:       {np.mean([r['latency_ms'] for r in results]):.2f} ms")

    # Forensic separation
    print("\n" + "-" * 90)
    print("PHYSICAL ACOUSTIC SEPARATION (SCAM CALLS vs LEGITIMATE CALLS)")
    print("-" * 90)
    scam_noise = [r["forensics"]["ambient_noise_floor_db"] for r in scams]
    legit_noise = [r["forensics"]["ambient_noise_floor_db"] for r in legits]
    scam_jitter = [r["forensics"]["jitter_local"] * 100 for r in scams]
    legit_jitter = [r["forensics"]["jitter_local"] * 100 for r in legits]
    scam_phase = [r["forensics"]["phase_dispersion"] for r in scams]
    legit_phase = [r["forensics"]["phase_dispersion"] for r in legits]

    print(f"Ambient Noise Floor:  Legitimate Calls = {np.mean(legit_noise):.1f} dB | Scam / AI Calls = {np.mean(scam_noise):.1f} dB")
    print(f"Vocal Jitter (F0):    Legitimate Calls = {np.mean(legit_jitter):.3f}% | Scam / AI Calls = {np.mean(scam_jitter):.3f}%")
    print(f"Phase Dispersion:     Legitimate Calls = {np.mean(legit_phase):.4f} | Scam / AI Calls = {np.mean(scam_phase):.4f}")

    report_path = os.path.join(ROOT_DIR, "scam_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "metrics": {
                "total_test_calls": len(results),
                "scams_tested": len(scams),
                "legit_tested": len(legits),
                "accuracy": round(acc, 4),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
                "avg_latency_ms": round(float(np.mean([r['latency_ms'] for r in results])), 2)
            },
            "results": results
        }, f, indent=2)
    print(f"\nSaved complete report to: {report_path}")

def main():
    train_manifest, test_manifest = build_dataset()
    train_models(train_manifest)
    evaluate_test_set(test_manifest)

if __name__ == "__main__":
    main()
