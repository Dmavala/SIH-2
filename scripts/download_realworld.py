import os
import urllib.request
import soundfile as sf
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_realworld_samples")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://huggingface.co/datasets/garystafford/deepfake-audio-detection/resolve/main/"

SAMPLES = [
    # --- AI VOICES (COMMERCIAL & SOTA) ---
    {
        "id": "elevenlabs_sample_1",
        "system": "ElevenLabs",
        "category": "AI_SYNTHETIC",
        "path": "fake/el_0001_c_part_002.flac",
        "filename": "ai_elevenlabs_01.flac",
        "description": "ElevenLabs high-fidelity neural voice clone with realistic cadence."
    },
    {
        "id": "elevenlabs_sample_2",
        "system": "ElevenLabs",
        "category": "AI_SYNTHETIC",
        "path": "fake/el_0001_part_001.flac",
        "filename": "ai_elevenlabs_02.flac",
        "description": "ElevenLabs conversational speech utterance."
    },
    {
        "id": "playht_sample_1",
        "system": "Play.ht",
        "category": "AI_SYNTHETIC",
        "path": "fake/po_0001_c_part_001.flac",
        "filename": "ai_playht_01.flac",
        "description": "Play.ht expressive generative voice model."
    },
    {
        "id": "speechify_sample_1",
        "system": "Speechify",
        "category": "AI_SYNTHETIC",
        "path": "fake/sp_0001_c_part_006.flac",
        "filename": "ai_speechify_01.flac",
        "description": "Speechify neural voice reader with commercial prosody."
    },
    {
        "id": "lmnt_sample_1",
        "system": "LMNT",
        "category": "AI_SYNTHETIC",
        "path": "fake/lv_0001_c_part_018.flac",
        "filename": "ai_lmnt_01.flac",
        "description": "LMNT ultra-low latency generative speech model."
    },
    {
        "id": "hifigan_sample_1",
        "system": "HiFi-GAN",
        "category": "AI_SYNTHETIC",
        "path": "fake/hg_0001_c_part_005.flac",
        "filename": "ai_hifigan_01.flac",
        "description": "HiFi-GAN neural vocoder synthesis."
    },
    {
        "id": "hubert_vc_sample_1",
        "system": "HuBERT-VC",
        "category": "AI_SYNTHETIC",
        "path": "fake/hu_0001_c_part_012.flac",
        "filename": "ai_hubert_vc_01.flac",
        "description": "HuBERT-based discrete acoustic unit voice conversion."
    },

    # --- REAL HUMAN VOICES (GROUND TRUTH) ---
    {
        "id": "real_human_yt_1",
        "system": "Authentic Human",
        "category": "AUTHENTIC_HUMAN",
        "path": "real/yt_0000_part_001.flac",
        "filename": "real_human_yt_01.flac",
        "description": "Authentic human speech from real-world conversational interview."
    },
    {
        "id": "real_human_yt_2",
        "system": "Authentic Human",
        "category": "AUTHENTIC_HUMAN",
        "path": "real/yt_0000_part_002.flac",
        "filename": "real_human_yt_02.flac",
        "description": "Authentic human speech with organic room acoustics and respiration."
    },
]

print("=" * 70)
print("DOWNLOADING REAL-WORLD AI VOICES & AUTHENTIC SAMPLES FROM HUGGINGFACE")
print("=" * 70)

downloaded_samples = []
for s in SAMPLES:
    dest_path = os.path.join(OUTPUT_DIR, s["filename"])
    url = BASE_URL + s["path"] + "?download=true"
    print(f"Fetching [{s['system']}] -> {s['filename']}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        
        info = sf.info(dest_path)
        print(f"  -> Saved: {info.duration:.2f}s | {info.samplerate}Hz | {info.channels}ch | {os.path.getsize(dest_path)} bytes")
        s["local_path"] = dest_path
        s["duration"] = round(info.duration, 2)
        s["samplerate"] = info.samplerate
        downloaded_samples.append(s)
    except Exception as e:
        print(f"  -> Error: {e}")

print("\n" + "=" * 70)
print(f"DOWNLOAD COMPLETE: {len(downloaded_samples)}/{len(SAMPLES)} samples ready for testing.")
print("=" * 70)
