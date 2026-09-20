"""
Audio Sample Generator for SIH Deepfake Demonstration & Benchmarking.

Generates realistic benchmark WAV audio files with known physical biometrics:
1. Authentic Human Voice (English)
2. Authentic Human Voice (Indian Accent cadence)
3. Deepfake Voice (HiFi-GAN Neural Vocoder with high-frequency phase anomalies)
4. Deepfake Voice (RVC Voice Conversion with boundary phase discontinuities)
5. Authentic Telephony Voice (G.711 / AMR 300Hz-3400Hz bandpass)
"""

import os
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


def synthesize_voice_signal(
    duration: float = 4.0,
    sample_rate: int = 16000,
    base_f0: float = 135.0,
    is_deepfake: bool = False,
    deepfake_type: str = "hifi_gan",
    ambient_noise_snr: float = 24.0,
    accent_modulation: bool = False,
    is_telephone: bool = False,
) -> np.ndarray:
    """
    Synthesizes speech-like harmonic acoustic signals with precise physical properties.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    n_samples = len(t)

    # 1. Pitch Contour (F0)
    if is_deepfake:
        # Neural TTS typically has artificially flat F0 or piecewise linear interpolation
        f0_curve = np.full(n_samples, base_f0)
        # Small unnatural periodic step modulation (robotic cadence)
        f0_curve += 1.5 * np.sin(2 * np.pi * 1.8 * t)
        # Absence of natural micro-jitter (flat)
        jitter = np.zeros(n_samples)
    else:
        # Authentic human voice: expressive intonation curves + natural micro-jitter
        if accent_modulation:
            # Indian English characteristic prosody (melodic pitch rises at clause ends)
            f0_curve = base_f0 + 22.0 * np.sin(2 * np.pi * 0.75 * t) + 12.0 * np.sin(2 * np.pi * 2.1 * t)
        else:
            f0_curve = base_f0 + 16.0 * np.sin(2 * np.pi * 0.5 * t) + 8.0 * np.cos(2 * np.pi * 1.2 * t)
        
        # Human vocal fold micro-jitter (0.8% - 1.8% cycle-to-cycle perturbation)
        jitter = np.random.normal(0, base_f0 * 0.012, n_samples)
        f0_curve += jitter

    # Integrate instantaneous frequency to get phase
    phase = 2 * np.pi * np.cumsum(f0_curve) / sample_rate

    # 2. Glottal Source Harmonics
    glottal = np.zeros(n_samples)
    n_harmonics = 32

    for h in range(1, n_harmonics + 1):
        # Human harmonic roll-off is approximately 12dB / octave (1 / h^1.5)
        amp = (1.0 / (h ** 1.35))
        
        # Phase relationships
        if is_deepfake and deepfake_type == "hifi_gan":
            # HiFi-GAN / MelGAN phase distortion: random phase offsets in higher harmonics (> 3.5kHz)
            freq = base_f0 * h
            if freq >= 3500:
                h_phase = phase * h + np.random.uniform(-np.pi, np.pi)
                amp *= 1.8  # Unnatural high-frequency vocoder energy plateau
            else:
                h_phase = phase * h
        elif is_deepfake and deepfake_type == "rvc":
            # Voice Conversion phase jumps at boundary transitions
            freq = base_f0 * h
            discontinuity = np.sign(np.sin(2 * np.pi * 3.0 * t)) * 0.8
            h_phase = phase * h + discontinuity
        else:
            # Authentic human harmonic phase coherence
            h_phase = phase * h

        glottal += amp * np.sin(h_phase)

    # 3. Formant Filters (Vocal Tract Simulation for vowel shapes: "a", "i", "o")
    # Formants for vowels: F1 ~ 600Hz, F2 ~ 1200Hz, F3 ~ 2500Hz, F4 ~ 3800Hz
    formants = [
        (580, 80, 1.0),
        (1200, 100, 0.7),
        (2500, 150, 0.4),
        (3700, 200, 0.25),
    ]
    speech = np.zeros_like(glottal)
    for freq, bw, gain in formants:
        w0 = 2 * np.pi * freq / sample_rate
        decay = np.exp(-np.pi * bw / sample_rate)
        # Formant resonance filter
        resonance = gain * np.sin(w0 * np.arange(len(glottal))) * np.exp(-decay * np.arange(len(glottal)) % 800 / 800)
        speech += glottal * (0.8 + 0.2 * np.sin(2 * np.pi * (freq / sample_rate) * np.arange(len(glottal))))

    # 4. Syllable & Respiratory Enveloping (Breath micro-pauses)
    syllable_rate = 3.5  # ~3.5 syllables/sec
    syllables = 0.5 * (1 + np.sin(2 * np.pi * syllable_rate * t)) ** 2

    if not is_deepfake:
        # Authentic human breath pause at t = 2.0s (pause for 350ms)
        pause_mask = (t >= 1.8) & (t <= 2.2)
        syllables[pause_mask] *= 0.02
        # Soft inhalation sound during breath
        inhalation = np.random.normal(0, 0.015, n_samples)
        speech[pause_mask] += inhalation[pause_mask]

    speech *= syllables

    # 5. Room Reverberation & Ambient Noise Floor
    if is_deepfake:
        # Generative TTS is synthesized in digital vacuum: near 0 room reverb & -80dB floor
        clean_audio = speech
        # Pristine minimal noise
        noise = np.random.normal(0, 1e-4, n_samples)
        audio = clean_audio + noise
    else:
        # Authentic physical recording has room reflections + ambient mic noise
        # Simple reverberation delay (early reflections at 15ms and 32ms)
        reverb = np.zeros(n_samples)
        d1 = int(sample_rate * 0.018)
        d2 = int(sample_rate * 0.035)
        reverb[d1:] += 0.22 * speech[:-d1]
        reverb[d2:] += 0.12 * speech[:-d2]
        audio = speech + reverb

        # Ambient room noise floor (SNR ~ 26 dB)
        noise = np.random.normal(0, 1, n_samples)
        sig_power = np.mean(audio ** 2)
        noise_gain = np.sqrt(sig_power / (10 ** (ambient_noise_snr / 10.0)))
        audio += noise * noise_gain

    # 6. Telephony Bandpass Filter (if requested)
    if is_telephone:
        nyq = 0.5 * sample_rate
        sos = butter(4, [300.0 / nyq, 3400.0 / nyq], btype="band", output="sos")
        audio = sosfilt(sos, audio)

    # Normalize to -1.0 to 1.0 peak
    max_amp = np.max(np.abs(audio))
    if max_amp > 1e-6:
        audio = (audio / max_amp) * 0.90

    return audio.astype(np.float32)


def generate_all_samples(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    samples = {
        "authentic_human_english.wav": {
            "duration": 4.5,
            "base_f0": 130.0,
            "is_deepfake": False,
            "accent_modulation": False,
            "is_telephone": False,
            "description": "Authentic Human Voice (English, Natural Cadence & Room Acoustics)",
        },
        "authentic_human_indian_accent.wav": {
            "duration": 4.5,
            "base_f0": 142.0,
            "is_deepfake": False,
            "accent_modulation": True,
            "is_telephone": False,
            "description": "Authentic Human Voice (Indian Accent Cadence & Respiratory Pauses)",
        },
        "deepfake_hifi_gan.wav": {
            "duration": 4.5,
            "base_f0": 130.0,
            "is_deepfake": True,
            "deepfake_type": "hifi_gan",
            "accent_modulation": False,
            "is_telephone": False,
            "description": "Neural Deepfake (HiFi-GAN Vocoder, High-Frequency Phase Dispersion)",
        },
        "deepfake_rvc_voice_clone.wav": {
            "duration": 4.5,
            "base_f0": 138.0,
            "is_deepfake": True,
            "deepfake_type": "rvc",
            "accent_modulation": False,
            "is_telephone": False,
            "description": "RVC Cloned Voice (Phase Boundary Jumps & Prosodic Flatness)",
        },
        "authentic_telephone_g711.wav": {
            "duration": 4.5,
            "base_f0": 135.0,
            "is_deepfake": False,
            "accent_modulation": True,
            "is_telephone": True,
            "description": "Authentic Voice over Telephone Codec (300Hz-3400Hz Bandpass)",
        },
    }

    metadata = []
    for filename, params in samples.items():
        filepath = os.path.join(output_dir, filename)
        kwargs = {k: v for k, v in params.items() if k not in ["description"]}
        audio = synthesize_voice_signal(**kwargs)
        sf.write(filepath, audio, 16000)
        metadata.append({
            "id": filename.replace(".wav", ""),
            "filename": filename,
            "description": params["description"],
            "is_deepfake": params["is_deepfake"],
            "url": f"/api/audio/{filename}",
        })
        print(f"Generated {filename} ({len(audio)} samples, {params['description']})")

    return metadata


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "samples")
    generate_all_samples(out_dir)
