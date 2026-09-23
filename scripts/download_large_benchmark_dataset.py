"""
Download Large-Scale Benchmark Dataset from Hugging Face:
- 60 Commercial & SOTA AI Voice Clones (ElevenLabs, Play.ht, Speechify, LMNT, HiFi-GAN, HuBERT)
- 60 Authentic Real Human Conversational Speech Recordings
Total: 120 curated audio samples from 'garystafford/deepfake-audio-detection' (1,866 audio repository).
"""

import os
import sys
import json
import urllib.request
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "large_benchmark_data")
os.makedirs(os.path.join(OUTPUT_DIR, "fake"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "real"), exist_ok=True)

HF_API_URL = "https://huggingface.co/api/datasets/garystafford/deepfake-audio-detection"
HF_RESOLVE_BASE = "https://huggingface.co/datasets/garystafford/deepfake-audio-detection/resolve/main/"

def fetch_file_list():
    print("[1/3] Querying Hugging Face repository manifest...")
    req = urllib.request.Request(HF_API_URL, headers={"User-Agent": "AEGIS-Voice-Sentinel/2.0"})
    with urllib.request.urlopen(req) as r:
        info = json.loads(r.read().decode())
    files = [s['rfilename'] for s in info.get('siblings', []) if s['rfilename'].endswith('.flac')]
    return files

def download_file(rel_path, target_dir):
    url = HF_RESOLVE_BASE + rel_path
    local_path = os.path.join(target_dir, os.path.basename(rel_path))
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        return local_path
    
    headers = {"User-Agent": "AEGIS-Voice-Sentinel/2.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp, open(local_path, "wb") as out_f:
            out_f.write(resp.read())
        return local_path
    except Exception as e:
        print(f"    [WARN] Failed to download {rel_path}: {e}")
        return None

def main():
    print("=" * 80)
    print("SOURCING LARGE-SCALE BENCHMARK AUDIO FROM HUGGING FACE VOICE DATABASE")
    print("=" * 80)
    
    all_files = fetch_file_list()
    fake_files = [f for f in all_files if f.startswith("fake/")]
    real_files = [f for f in all_files if f.startswith("real/")]
    
    print(f"Total available repository files: {len(fake_files)} synthetic | {len(real_files)} authentic")
    
    # Stratify by synthetic systems: el, po, sp, lv, hg, hu
    systems = {
        "el": ("ElevenLabs v3", 10),
        "po": ("Play.ht", 10),
        "sp": ("Speechify", 10),
        "lv": ("LMNT", 10),
        "hg": ("HiFi-GAN", 10),
        "hu": ("HuBERT-VC", 10)
    }
    
    download_manifest = []
    
    print("\n[2/3] Downloading stratified SOTA AI voice samples (60 files)...")
    for prefix, (sys_name, target_count) in systems.items():
        candidates = [f for f in fake_files if f.split("/")[1].startswith(prefix)][:target_count]
        print(f"  -> Downloading {len(candidates)} samples for {sys_name} ({prefix})...")
        downloaded = 0
        for cand in candidates:
            p = download_file(cand, os.path.join(OUTPUT_DIR, "fake"))
            if p:
                downloaded += 1
                download_manifest.append({
                    "id": os.path.basename(p),
                    "system": sys_name,
                    "category": "AI_SYNTHETIC",
                    "path": p,
                    "label": 1
                })
        print(f"     Downloaded {downloaded}/{len(candidates)} files.")
        
    print("\n[3/3] Downloading authentic human conversational speech samples (60 files)...")
    real_candidates = real_files[:60]
    downloaded_real = 0
    for cand in real_candidates:
        p = download_file(cand, os.path.join(OUTPUT_DIR, "real"))
        if p:
            downloaded_real += 1
            download_manifest.append({
                "id": os.path.basename(p),
                "system": "Authentic Human",
                "category": "AUTHENTIC_HUMAN",
                "path": p,
                "label": 0
            })
    print(f"  -> Downloaded {downloaded_real}/{len(real_candidates)} authentic human files.")
    
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(download_manifest, f, indent=2)
        
    print("\n" + "=" * 80)
    print(f"LARGE-SCALE BENCHMARK DATASET READY: {len(download_manifest)} audio files downloaded.")
    print(f"Manifest saved to: {manifest_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
