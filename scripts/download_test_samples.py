import os
import urllib.request
import soundfile as sf

BASE_URL = "https://huggingface.co/datasets/kzhou/voice_cloning_style_transfer/resolve/main/"

SAMPLES_TO_DOWNLOAD = [
    # 1. Real Human Speech (Ground Truth)
    {
        "id": "real_human_spk001_s1",
        "category": "REAL_HUMAN",
        "generator": "Human (Speaker 001)",
        "path": "original/preprocessed_sentences/sentence_1_valid/speaker_001_sentence_1.wav",
        "output_name": "real_human_speaker_001.wav"
    },
    {
        "id": "real_human_spk002_s1",
        "category": "REAL_HUMAN",
        "generator": "Human (Speaker 002)",
        "path": "original/preprocessed_sentences/sentence_1_valid/speaker_002_sentence_1.wav",
        "output_name": "real_human_speaker_002.wav"
    },
    # 2. ElevenLabs Voice Clone (State-of-the-Art Neural Clone)
    {
        "id": "elevenlabs_clone_spk001_s1",
        "category": "AI_CLONE",
        "generator": "ElevenLabs v3",
        "path": "cloned/elevenlabs/cloned_elevenlabs_speaker_001_sentence_1.wav",
        "output_name": "elevenlabs_clone_speaker_001.wav"
    },
    {
        "id": "elevenlabs_clone_spk002_s1",
        "category": "AI_CLONE",
        "generator": "ElevenLabs v3",
        "path": "cloned/elevenlabs/cloned_elevenlabs_speaker_002_sentence_1.wav",
        "output_name": "elevenlabs_clone_speaker_002.wav"
    },
    # 3. Coqui XTTS-v2 Voice Clone (Autoregressive Voice Clone)
    {
        "id": "coqui_xtts_clone_spk001_s1",
        "category": "AI_CLONE",
        "generator": "Coqui XTTS-v2",
        "path": "cloned/coqui_xtts/cloned_coqui_xtts_speaker_001_sentence_1.wav",
        "output_name": "coqui_xtts_clone_speaker_001.wav"
    },
    {
        "id": "coqui_xtts_clone_spk002_s1",
        "category": "AI_CLONE",
        "generator": "Coqui XTTS-v2",
        "path": "cloned/coqui_xtts/cloned_coqui_xtts_speaker_002_sentence_1.wav",
        "output_name": "coqui_xtts_clone_speaker_002.wav"
    },
    # 4. Chatterbox Voice Clone
    {
        "id": "chatterbox_clone_spk001_s1",
        "category": "AI_CLONE",
        "generator": "Chatterbox",
        "path": "cloned/chatterbox/cloned_chatterbox_speaker_001_sentence_1.wav",
        "output_name": "chatterbox_clone_speaker_001.wav"
    }
]

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_downloaded_samples")
os.makedirs(output_dir, exist_ok=True)

print(f"Downloading {len(SAMPLES_TO_DOWNLOAD)} audio samples into: {output_dir}\n")

downloaded = []
for item in SAMPLES_TO_DOWNLOAD:
    url = BASE_URL + item["path"] + "?download=true"
    dest = os.path.join(output_dir, item["output_name"])
    print(f"Downloading [{item['category']}] {item['generator']} -> {item['output_name']}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        
        # Verify with soundfile
        info = sf.info(dest)
        print(f"  ✓ Saved ({info.duration:.2f}s, {info.samplerate}Hz, {info.channels}ch, {os.path.getsize(dest)} bytes)")
        item["local_path"] = dest
        item["duration"] = round(info.duration, 2)
        item["samplerate"] = info.samplerate
        downloaded.append(item)
    except Exception as e:
        print(f"  ✗ Failed: {e}")

print(f"\nSuccessfully downloaded {len(downloaded)}/{len(SAMPLES_TO_DOWNLOAD)} test samples.")
