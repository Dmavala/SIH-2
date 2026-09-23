import os
import sys
import json
import numpy as np
import soundfile as sf
import scipy.signal
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2
from voice_cloning_detector.models.ensemble import EnsembleVoiceCloningDetector
from backend.features.acoustics import extract_acoustic_forensics
from backend.features.vad import compute_speech_ratio

def load_audio(path, target_sr=16000):
    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if sr != target_sr:
        num = int(len(audio) * target_sr / sr)
        audio = scipy.signal.resample(audio, num)
    return audio.astype(np.float32)

aasist = AASIST(sample_rate=16000).eval()
rawnet = RawNet2(sample_rate=16000).eval()
ensemble = EnsembleVoiceCloningDetector(device=torch.device("cpu")).eval()

samples = [
    ("ElevenLabs #1", "test_realworld_samples/ai_elevenlabs_01.flac", "AI"),
    ("ElevenLabs #2", "test_realworld_samples/ai_elevenlabs_02.flac", "AI"),
    ("Play.ht", "test_realworld_samples/ai_playht_01.flac", "AI"),
    ("Speechify", "test_realworld_samples/ai_speechify_01.flac", "AI"),
    ("LMNT", "test_realworld_samples/ai_lmnt_01.flac", "AI"),
    ("HiFi-GAN", "test_realworld_samples/ai_hifigan_01.flac", "AI"),
    ("HuBERT-VC", "test_realworld_samples/ai_hubert_vc_01.flac", "AI"),
    ("Human (YouTube #1)", "test_realworld_samples/real_human_yt_01.flac", "REAL"),
    ("Human (YouTube #2)", "test_realworld_samples/real_human_yt_02.flac", "REAL"),
    ("Bench Human (Indian)", "backend/demo_audio/samples/authentic_human_indian_accent.wav", "REAL"),
    ("Bench Human (English)", "backend/demo_audio/samples/authentic_human_english.wav", "REAL"),
    ("Bench HiFi-GAN", "backend/demo_audio/samples/deepfake_hifi_gan.wav", "AI"),
    ("Bench RVC", "backend/demo_audio/samples/deepfake_rvc_voice_clone.wav", "AI"),
]

print(f"{'Sample Name':<22} | {'GT':<4} | {'AASIST':<8} | {'RawNet2':<8} | {'Ens-Total':<9} | {'B1(SSL)':<8} | {'B2(Phase)':<9} | {'B3(Bio)':<8} | {'Noise(dB)':<9} | {'Ens Pred':<8}")
print("-" * 115)

for name, rel_path, gt in samples:
    full_path = os.path.join(ROOT_DIR, rel_path)
    if not os.path.exists(full_path):
        continue
    audio = load_audio(full_path, 16000)
    
    # Pad or tile to 32000 for AASIST/RawNet
    target_len = 32000
    if len(audio) < target_len:
        rep = int(np.ceil(target_len / len(audio)))
        audio_32k = np.tile(audio, rep)[:target_len]
    else:
        audio_32k = audio[:target_len]
        
    t_audio = torch.from_numpy(audio_32k).unsqueeze(0).float()
    
    # AASIST
    with torch.no_grad():
        logits_a = aasist(t_audio)
        prob_a = float(torch.softmax(logits_a, dim=-1)[0, 1].item())
        
    # RawNet2
    with torch.no_grad():
        logits_r = rawnet(t_audio)
        prob_r = float(torch.softmax(logits_r, dim=-1)[0, 1].item())
        
    # Ensemble (Wav2Vec2 + Phase ResNet + Bio MLP)
    try:
        ens_res = ensemble.predict_clip(audio, sr=16000)
        ens_score = ens_res["final_score"]
        b1 = ens_res["branch_scores"]["branch1_ssl"]
        b2 = ens_res["branch_scores"]["branch2_phase"]
        b3 = ens_res["branch_scores"]["branch3_temporal"]
        pred = ens_res["prediction"]
    except Exception as e:
        ens_score = -1.0
        b1, b2, b3 = -1.0, -1.0, -1.0
        pred = f"ERR:{e}"

    forensics = extract_acoustic_forensics(audio, 16000)
    noise_db = forensics["ambient_noise_floor_db"]
    
    print(f"{name:<22} | {gt:<4} | {prob_a*100:>6.1f}%  | {prob_r*100:>6.1f}%  | {ens_score*100:>7.1f}%  | {b1*100:>6.1f}%  | {b2*100:>7.1f}%  | {b3*100:>6.1f}%  | {noise_db:>7.1f}dB | {pred:<8}")
