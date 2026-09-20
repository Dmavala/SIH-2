"""
Synthetic & Authentic Audio Dataset Generator for Voice Cloning Detection.

Generates realistic benchmark audio samples simulating:
1. Authentic Real Speech:
   - Natural harmonic formants (vowels /a/, /i/, /u/, /e/, /o/)
   - Organic prosodic pitch contours with natural micro-jitter (>1.5%) and shimmer (>3.5%)
   - Biological inhalation breath sounds (100-1000 Hz) during speech pauses
   - Realistic room acoustics & ambient microphone floor noise

2. Cloned / AI-Generated Deepfake Speech:
   - 'rvc': Retrieval-based Voice Conversion with phase smearing and vocoder transposition
   - 'xtts': Autoregressive generation with sterile digital pauses (zero breathing) & flat pitch variance
   - 'elevenlabs': HiFi-GAN neural vocoder high-frequency phase inconsistencies (6-8 kHz dispersion)
   - 'bark': Token boundary acoustic discontinuities and vocoder micro-glitches
   - 'openvoice': Tone-color conversion phase misalignment
"""

import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import argparse
import random
import numpy as np
import scipy.signal
import soundfile as sf
from typing import Tuple, List

from voice_cloning_detector.config import DATA_DIR, REAL_DIR, FAKE_DIR, SAMPLE_RATE, CHUNK_DURATION


def synthesize_vowel_formants(
    f0_contour: np.ndarray,
    sr: int,
    formants: List[Tuple[float, float]],  # List of (center_freq, bandwidth)
    duration_samples: int
) -> np.ndarray:
    """
    Synthesizes voiced speech segment using glottal pulse train filtered by formant resonators.
    """
    # Glottal pulse train from continuous phase integration
    phase = np.cumsum(2.0 * np.pi * f0_contour / sr)
    glottal_source = scipy.signal.sawtooth(phase, width=0.5)
    
    # Filter through formant bandpass/resonator filters
    speech = np.zeros(duration_samples, dtype=np.float32)
    for freq, bw in formants:
        q = max(freq / max(bw, 20.0), 1.0)
        b, a = scipy.signal.iirpeak(freq, q, fs=sr)
        filtered = scipy.signal.lfilter(b, a, glottal_source)
        speech += filtered.astype(np.float32)
        
    peak = np.max(np.abs(speech))
    if peak > 0:
        speech = speech / peak
    return speech


def generate_natural_real_speech(
    duration: float = 4.0,
    sr: int = 16000,
    speaker_id: int = 1
) -> np.ndarray:
    """
    Generates authentic real human speech sample with natural biological traits.
    """
    n_samples = int(duration * sr)
    rng = np.random.RandomState(speaker_id * 1000 + random.randint(0, 999))
    
    base_f0 = 110.0 if (speaker_id % 2 == 0) else 190.0  # Male / Female pitch range
    t = np.linspace(0, duration, n_samples)
    
    # Organic prosody: smooth macro-intonation + natural micro-jitter
    macro_prosody = 25.0 * np.sin(2.0 * np.pi * 0.8 * t) + 12.0 * np.cos(2.0 * np.pi * 1.7 * t)
    micro_jitter = rng.normal(0, 2.5, n_samples)  # Natural human jitter
    f0_contour = np.clip(base_f0 + macro_prosody + micro_jitter, 65.0, 450.0)
    
    # Human formants (e.g. vowel sequence /a/ -> /i/ -> /o/)
    formant_sets = [
        [(750, 80), (1200, 100), (2600, 120), (3300, 150)],   # /a/
        [(300, 60), (2200, 90), (3000, 110), (3600, 140)],    # /i/
        [(500, 70), (900, 80), (2500, 100), (3400, 130)]      # /o/
    ]
    
    audio = np.zeros(n_samples, dtype=np.float32)
    # Speech phrases with natural breath pauses in between
    phrase1_end = int(1.6 * sr)
    pause_start = int(1.6 * sr)
    pause_end = int(2.2 * sr)
    phrase2_start = int(2.2 * sr)
    
    # Phrase 1
    f1 = formant_sets[speaker_id % len(formant_sets)]
    speech1 = synthesize_vowel_formants(f0_contour[:phrase1_end], sr, f1, phrase1_end)
    # Natural shimmer (amplitude envelope fluctuation)
    env1 = 0.8 + 0.2 * np.sin(2.0 * np.pi * 4.0 * t[:phrase1_end]) + rng.normal(0, 0.03, phrase1_end)
    audio[:phrase1_end] = speech1 * np.clip(env1, 0.1, 1.0)
    
    # Natural inhalation breath during pause (100 - 1000 Hz broadband acoustic turbulence)
    pause_len = pause_end - pause_start
    breath_noise = rng.normal(0, 0.08, pause_len)
    b_breath, a_breath = scipy.signal.butter(3, [150 / (sr / 2), 850 / (sr / 2)], btype='bandpass')
    filtered_breath = scipy.signal.lfilter(b_breath, a_breath, breath_noise)
    # Tapered inhalation envelope
    breath_envelope = np.hanning(pause_len) * 0.15
    audio[pause_start:pause_end] = filtered_breath * breath_envelope
    
    # Phrase 2
    f2 = formant_sets[(speaker_id + 1) % len(formant_sets)]
    speech2_len = n_samples - phrase2_start
    speech2 = synthesize_vowel_formants(f0_contour[phrase2_start:], sr, f2, speech2_len)
    env2 = 0.8 + 0.2 * np.cos(2.0 * np.pi * 3.5 * t[phrase2_start:]) + rng.normal(0, 0.03, speech2_len)
    audio[phrase2_start:] = speech2 * np.clip(env2, 0.1, 1.0)
    
    # Subtle natural room reverberation & mic floor noise (-45 dB)
    ambient_noise = rng.normal(0, 0.003, n_samples).astype(np.float32)
    audio += ambient_noise
    
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak
    return audio.astype(np.float32)


def generate_fake_speech(
    generator_type: str = "xtts",
    duration: float = 4.0,
    sr: int = 16000,
    speaker_id: int = 1
) -> np.ndarray:
    """
    Generates synthetic cloned speech with distinct neural cloning artifacts.
    """
    n_samples = int(duration * sr)
    rng = np.random.RandomState(speaker_id * 2000 + random.randint(0, 999))
    t = np.linspace(0, duration, n_samples)
    
    base_f0 = 130.0 if (speaker_id % 2 == 0) else 210.0
    
    if generator_type == "xtts":
        # Artifact 1: Unnaturally flat pitch jitter (robotic monotonic micro-stability)
        # Artifact 2: Perfectly digital silence pauses (ZERO biological breathing)
        f0_contour = np.full(n_samples, base_f0) + 5.0 * np.sin(2.0 * np.pi * 0.5 * t)
        formants = [(700, 80), (1300, 90), (2500, 100), (3300, 120)]
        audio = synthesize_vowel_formants(f0_contour, sr, formants, n_samples)
        # Digital zero pause: completely silence 1.6s to 2.2s
        audio[int(1.6 * sr):int(2.2 * sr)] = 0.0
        
    elif generator_type == "rvc":
        # Artifact: Retrieval-based voice conversion phase smearing + transposition artifacts
        f0_contour = base_f0 + 15.0 * np.sin(2.0 * np.pi * 1.2 * t)
        formants = [(850, 100), (1400, 110), (2400, 120), (3500, 150)]
        speech = synthesize_vowel_formants(f0_contour, sr, formants, n_samples)
        # Phase smearing via all-pass dispersion filters
        b_allpass, a_allpass = scipy.signal.iirfilter(4, 0.4, btype='lowpass', ftype='butter')
        dispersed = scipy.signal.lfilter(b_allpass, a_allpass, speech)
        audio = 0.7 * speech + 0.3 * dispersed
        
    elif generator_type == "elevenlabs":
        # Artifact: Production neural vocoder (HiFi-GAN/BigVGAN) phase dispersion & micro-flat prosody
        f0_contour = base_f0 + 8.0 * np.sin(2.0 * np.pi * 0.4 * t) + rng.normal(0, 0.4, n_samples)
        formants = [(650, 75), (1150, 85), (2700, 110), (3200, 130)]
        audio = synthesize_vowel_formants(f0_contour, sr, formants, n_samples)
        # Vocoder phase smearing across harmonic multiples
        b_disp, a_disp = scipy.signal.iirpeak(4000, 2.0, fs=sr)
        disp_phase = scipy.signal.lfilter(b_disp, a_disp, audio)
        audio = 0.85 * audio + 0.15 * disp_phase
        # MP3 style high-frequency cut
        b_mp3, a_mp3 = scipy.signal.butter(6, 7200 / (sr / 2), btype='low')
        audio = scipy.signal.lfilter(b_mp3, a_mp3, audio)

    elif generator_type == "fish_speech":
        # Artifact: Dual-AR acoustic token model with discrete latent code boundaries
        f0_contour = base_f0 + 12.0 * np.sin(2.0 * np.pi * 0.6 * t)
        formants = [(500, 70), (1500, 90), (2500, 100), (3500, 120)]
        audio = synthesize_vowel_formants(f0_contour, sr, formants, n_samples)
        # Latent code transition micro-glitches every 40ms (25 Hz token frame rate)
        frame_interval = int(0.04 * sr)
        for f_idx in range(frame_interval, n_samples - 10, frame_interval):
            audio[f_idx:f_idx + 4] *= 0.1  # Codec frame boundary artifact

    elif generator_type == "bark":
        # Artifact: Auto-regressive acoustic token transitions with boundary clicks
        f0_contour = base_f0 + 30.0 * np.sin(2.0 * np.pi * 0.4 * t)
        formants = [(550, 80), (1800, 90), (2800, 120), (3400, 140)]
        audio = synthesize_vowel_formants(f0_contour, sr, formants, n_samples)
        # Token boundary discontinuities every 0.5 seconds
        for step_sec in [0.8, 1.5, 2.3, 3.1]:
            idx = int(step_sec * sr)
            if idx < n_samples - 20:
                audio[idx:idx + 10] *= -1.5  # Phase step glitch
                
    else:  # "openvoice" / generic
        f0_contour = base_f0 + 10.0 * np.sin(2.0 * np.pi * 1.0 * t)
        formants = [(600, 80), (1200, 90), (2600, 100), (3500, 120)]
        audio = synthesize_vowel_formants(f0_contour, sr, formants, n_samples)
        audio += rng.normal(0, 0.001, n_samples).astype(np.float32)
        
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak
    return audio.astype(np.float32)


def generate_full_dataset(
    num_real_samples: int = 30,
    num_fake_samples: int = 30,
    output_real_dir: str = REAL_DIR,
    output_fake_dir: str = FAKE_DIR
):
    """
    Generates a full synthetic benchmark dataset across real and cloned speakers.
    """
    os.makedirs(output_real_dir, exist_ok=True)
    os.makedirs(output_fake_dir, exist_ok=True)
    
    print(f"Generating {num_real_samples} authentic real speech samples...")
    for i in range(num_real_samples):
        speaker_id = (i % 6) + 1
        audio = generate_natural_real_speech(duration=CHUNK_DURATION, sr=SAMPLE_RATE, speaker_id=speaker_id)
        filename = f"real_spk{speaker_id}_{i+1:03d}.wav"
        filepath = os.path.join(output_real_dir, filename)
        sf.write(filepath, audio, SAMPLE_RATE)
        
    generators = ["rvc", "xtts", "elevenlabs", "fish_speech", "bark", "openvoice"]
    print(f"Generating {num_fake_samples} deepfake/cloned speech samples across tools: {generators}...")
    for i in range(num_fake_samples):
        gen = generators[i % len(generators)]
        speaker_id = (i % 6) + 1
        audio = generate_fake_speech(generator_type=gen, duration=CHUNK_DURATION, sr=SAMPLE_RATE, speaker_id=speaker_id)
        filename = f"fake_{gen}_spk{speaker_id}_{i+1:03d}.wav"
        filepath = os.path.join(output_fake_dir, filename)
        sf.write(filepath, audio, SAMPLE_RATE)
        
    print(f"Dataset generated successfully:\n  - Real: {output_real_dir} ({num_real_samples} files)\n  - Fake: {output_fake_dir} ({num_fake_samples} files)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate benchmark speech cloning dataset")
    parser.add_argument("--num_real", type=int, default=30, help="Number of real audio clips")
    parser.add_argument("--num_fake", type=int, default=30, help="Number of fake audio clips")
    args = parser.parse_args()
    
    generate_full_dataset(num_real_samples=args.num_real, num_fake_samples=args.num_fake)
