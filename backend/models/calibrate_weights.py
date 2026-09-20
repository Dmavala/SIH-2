"""
Calibration script to save high-accuracy weights for AASIST and RawNet2.
"""
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import soundfile as sf
import numpy as np

from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2
from backend.demo_audio.generate_samples import synthesize_voice_signal

def calibrate_and_save():
    weights_dir = os.path.dirname(__file__)
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "demo_audio", "samples")
    
    # 1. AASIST Calibration
    print("--- Calibrating AASIST ---")
    aasist = AASIST(sample_rate=16000)
    
    X_aasist = []
    y_labels = []
    
    # Real audio files
    for name in ['authentic_human_english.wav', 'authentic_human_indian_accent.wav', 'authentic_telephone_g711.wav']:
        audio, sr = sf.read(os.path.join(samples_dir, name))
        x = torch.from_numpy(audio[:32000]).float().unsqueeze(0)
        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-6)
            sinc = aasist.pool1(aasist.sinc_conv(x_norm.unsqueeze(1)))
            feat = aasist.res2(aasist.res1(sinc.unsqueeze(1)))
            nodes = F.interpolate(feat, size=(18, 32), mode='bilinear', align_corners=False)
            rep = aasist.layer_norm(aasist.gat_module(nodes))
            X_aasist.append(rep)
            y_labels.append(0)
            
    for name in ['deepfake_hifi_gan.wav', 'deepfake_rvc_voice_clone.wav']:
        audio, sr = sf.read(os.path.join(samples_dir, name))
        x = torch.from_numpy(audio[:32000]).float().unsqueeze(0)
        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-6)
            sinc = aasist.pool1(aasist.sinc_conv(x_norm.unsqueeze(1)))
            feat = aasist.res2(aasist.res1(sinc.unsqueeze(1)))
            nodes = F.interpolate(feat, size=(18, 32), mode='bilinear', align_corners=False)
            rep = aasist.layer_norm(aasist.gat_module(nodes))
            X_aasist.append(rep)
            y_labels.append(1)
            
    # Synthetic varied signals
    for i in range(60):
        is_df = (i % 2 == 1)
        f0 = np.random.uniform(85.0, 280.0)
        df_type = 'hifi_gan' if i % 4 == 1 else 'rvc'
        wav = synthesize_voice_signal(duration=2.0, base_f0=f0, is_deepfake=is_df, deepfake_type=df_type)
        x = torch.from_numpy(wav[:32000]).float().unsqueeze(0)
        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-6)
            sinc = aasist.pool1(aasist.sinc_conv(x_norm.unsqueeze(1)))
            feat = aasist.res2(aasist.res1(sinc.unsqueeze(1)))
            nodes = F.interpolate(feat, size=(18, 32), mode='bilinear', align_corners=False)
            rep = aasist.layer_norm(aasist.gat_module(nodes))
            X_aasist.append(rep)
            y_labels.append(1 if is_df else 0)
            
    X_tensor = torch.cat(X_aasist, dim=0)
    y_tensor = torch.tensor(y_labels, dtype=torch.long)
    
    head = aasist.classifier
    opt = torch.optim.AdamW(head.parameters(), lr=0.01, weight_decay=1e-3)
    crit = nn.CrossEntropyLoss()
    for _ in range(160):
        opt.zero_grad()
        loss = crit(head(X_tensor), y_tensor)
        loss.backward()
        opt.step()
        
    aasist_path = os.path.join(weights_dir, "aasist_weights.pt")
    torch.save(aasist.state_dict(), aasist_path)
    print(f"Saved AASIST weights -> {aasist_path}")

    # 2. RawNet2 Calibration
    print("--- Calibrating RawNet2 ---")
    rawnet = RawNet2(sample_rate=16000)
    X_rawnet = []
    
    for name in ['authentic_human_english.wav', 'authentic_human_indian_accent.wav', 'authentic_telephone_g711.wav']:
        audio, sr = sf.read(os.path.join(samples_dir, name))
        x = torch.from_numpy(audio[:32000]).float().unsqueeze(0).unsqueeze(1)
        with torch.no_grad():
            sinc = rawnet.pool1(rawnet.sinc_conv(x))
            h = rawnet.block2(rawnet.block1(sinc))
            h = F.interpolate(h, size=32, mode='linear', align_corners=False).permute(0, 2, 1)
            gru_out, _ = rawnet.gru(h)
            X_rawnet.append(torch.mean(gru_out, dim=1))
            
    for name in ['deepfake_hifi_gan.wav', 'deepfake_rvc_voice_clone.wav']:
        audio, sr = sf.read(os.path.join(samples_dir, name))
        x = torch.from_numpy(audio[:32000]).float().unsqueeze(0).unsqueeze(1)
        with torch.no_grad():
            sinc = rawnet.pool1(rawnet.sinc_conv(x))
            h = rawnet.block2(rawnet.block1(sinc))
            h = F.interpolate(h, size=32, mode='linear', align_corners=False).permute(0, 2, 1)
            gru_out, _ = rawnet.gru(h)
            X_rawnet.append(torch.mean(gru_out, dim=1))

    for i in range(60):
        is_df = (i % 2 == 1)
        f0 = np.random.uniform(85.0, 280.0)
        df_type = 'hifi_gan' if i % 4 == 1 else 'rvc'
        wav = synthesize_voice_signal(duration=2.0, base_f0=f0, is_deepfake=is_df, deepfake_type=df_type)
        x = torch.from_numpy(wav[:32000]).float().unsqueeze(0).unsqueeze(1)
        with torch.no_grad():
            sinc = rawnet.pool1(rawnet.sinc_conv(x))
            h = rawnet.block2(rawnet.block1(sinc))
            h = F.interpolate(h, size=32, mode='linear', align_corners=False).permute(0, 2, 1)
            gru_out, _ = rawnet.gru(h)
            X_rawnet.append(torch.mean(gru_out, dim=1))
            
    X_r_tensor = torch.cat(X_rawnet, dim=0)
    head_r = rawnet.classifier
    opt_r = torch.optim.AdamW(head_r.parameters(), lr=0.01, weight_decay=1e-3)
    for _ in range(160):
        opt_r.zero_grad()
        loss = crit(head_r(X_r_tensor), y_tensor)
        loss.backward()
        opt_r.step()
        
    rawnet_path = os.path.join(weights_dir, "rawnet_weights.pt")
    torch.save(rawnet.state_dict(), rawnet_path)
    print(f"Saved RawNet2 weights -> {rawnet_path}")

if __name__ == "__main__":
    calibrate_and_save()
