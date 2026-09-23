"""
Build REAL demo samples for the dashboard from in-repo benchmark corpora.

Why: the previous demo WAVs were procedurally synthesized (sine-harmonic
constructions), which made the "authentic human" demo files fake and created a
circular evaluation. This script replaces them with real recordings:

  - Authentic human speech  <- large_benchmark_data/real (YouTube speech clips)
  - Authentic telephony     <- scam_call_data/processed/normal (real call audio)
  - SOTA TTS deepfakes      <- large_benchmark_data/fake (ElevenLabs, Play.ht, ...)
  - Scam call recordings    <- scam_call_data/processed/scam (first 45 s)

Outputs (16 kHz mono WAV) into backend/demo_audio/samples/, replacing the old
synthetic files. Run once from the project root:

    python scripts/build_real_demo_samples.py
"""

import glob
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "backend", "demo_audio", "samples")
TARGET_SR = 16000
MAX_SECONDS = 45.0


def load_mono_16k(path: str) -> np.ndarray:
    audio, sr = sf.read(path, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if sr != TARGET_SR:
        import scipy.signal
        audio = scipy.signal.resample(audio, int(len(audio) * TARGET_SR / sr))
    return audio.astype(np.float32)


def save(path: str, audio: np.ndarray) -> None:
    sf.write(path, audio, TARGET_SR, subtype="PCM_16")
    dur = len(audio) / TARGET_SR
    print(f"  wrote {os.path.basename(path):44s} {dur:6.1f}s  {os.path.getsize(path)//1024} KB")


def first_existing(patterns, fallback_duration=6.0):
    """Return first readable audio file matching any glob pattern."""
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            try:
                sf.info(p)
                return p
            except Exception:
                continue
    return None


def main() -> int:
    os.makedirs(SAMPLES, exist_ok=True)
    jobs = [
        # (output filename, [source glob candidates], trim_seconds)
        ("real_authentic_speech.wav",
         ["large_benchmark_data/real/yt_0000_part_001.flac",
          "large_benchmark_data/real/yt_0000_part_002.flac"], None),
        ("real_authentic_indian_accent.wav",
         ["large_benchmark_data/real/yt_0000_part_004.flac",
          "large_benchmark_data/real/yt_0000_part_005.flac"], None),
        ("real_authentic_telephony.wav",
         ["scam_call_data/processed/normal/normal_12.wav",
          "scam_call_data/processed/normal/normal_1.wav"], 20.0),
        ("real_deepfake_elevenlabs.wav",
         ["large_benchmark_data/fake/el_*_part_00[1-3].flac"], None),
        ("real_deepfake_playht.wav",
         ["large_benchmark_data/fake/po_*_part_00[1-3].flac"], None),
        ("real_deepfake_hifigan.wav",
         ["large_benchmark_data/fake/hg_*_part_00[1-3].flac"], None),
        ("real_scam_kyc_fraud.wav",
         ["scam_call_data/processed/scam/scam_1.wav"], 45.0),
        ("real_scam_digital_arrest.wav",
         ["scam_call_data/processed/scam/scam_2.wav"], 45.0),
        ("real_scam_customs_narcotics.wav",
         ["scam_call_data/processed/scam/scam_3.wav"], 45.0),
    ]

    missing = []
    for out_name, patterns, trim in jobs:
        src = first_existing(patterns)
        if src is None:
            missing.append((out_name, patterns))
            continue
        audio = load_mono_16k(src)
        if trim:
            audio = audio[: int(trim * TARGET_SR)]
        if len(audio) < int(2.0 * TARGET_SR):
            missing.append((out_name, patterns))
            continue
        save(os.path.join(SAMPLES, out_name), audio)

    if missing:
        print("\nMISSING sources for:")
        for name, pats in missing:
            print(f"  {name}  <- tried {pats}")
        return 1
    print("\nAll real demo samples built OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
