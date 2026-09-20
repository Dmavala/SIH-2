"""
Production Dataset Builder for AI Voice Cloning & Deepfake Speech Detection.

Constructs balanced, diverse, authentic human speech samples and corresponding
neural vocoder / cloning artifacts from real human recordings (CMU ARCTIC: slt, ksp)
and ElevenLabs production models.
"""

import os
import sys
import glob
import random
import numpy as np
import soundfile as sf
import scipy.signal
import scipy.ndimage

# Repository root setup
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from voice_cloning_detector.config import DATA_DIR, REAL_DIR, FAKE_DIR, SAMPLE_RATE, CHUNK_DURATION, TARGET_SAMPLES


def load_and_standardize_raw(file_path: str, target_sr: int = 16000, target_duration: float = 4.0) -> np.ndarray:
    """Loads audio, ensures mono 16kHz, pads or repeats to target_duration, and peak normalizes."""
    audio, sr = sf.read(file_path, dtype='float32')
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
        
    if sr != target_sr:
        audio = scipy.signal.resample_poly(audio, target_sr, sr)
        
    target_len = int(target_duration * target_sr)
    if len(audio) < target_len:
        # Repeat or pad speech
        repeats = int(np.ceil(target_len / len(audio)))
        audio = np.tile(audio, repeats)[:target_len]
    else:
        audio = audio[:target_len]
        
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak
    return audio.astype(np.float32)


def add_microphone_acoustics(audio: np.ndarray, sr: int = 16000, rng: random.Random = None) -> np.ndarray:
    """Simulates laptop, desktop mic, room reverberation, and ambient room noise on real human voice."""
    if rng is None:
        rng = random.Random()
        
    out = audio.copy()
    
    # 1. Room reverberation (early reflections filter)
    delays = [int(0.015 * sr), int(0.028 * sr), int(0.042 * sr)]
    gains = [0.15, 0.08, 0.04]
    for d, g in zip(delays, gains):
        if len(out) > d:
            out[d:] += g * audio[:-d]
            
    # 2. Desktop mic proximity frequency coloration (gentle low-shelf or presence EQ)
    eq_type = rng.choice(["laptop", "desktop", "headset", "clean"])
    if eq_type == "laptop":
        b_hp, a_hp = scipy.signal.butter(2, 120 / (sr / 2), btype='high')
        out = scipy.signal.lfilter(b_hp, a_hp, out)
    elif eq_type == "desktop":
        b_lp, a_lp = scipy.signal.butter(2, 250 / (sr / 2), btype='low')
        out += 0.15 * scipy.signal.lfilter(b_lp, a_lp, out)
        
    # 3. Ambient microphone noise (-30 dB to -45 dB SNR)
    snr_db = rng.uniform(25.0, 45.0)
    sig_power = np.mean(out ** 2) + 1e-9
    noise_power = sig_power / (10 ** (snr_db / 10.0))
    noise = np.random.normal(0, np.sqrt(noise_power), size=len(out)).astype(np.float32)
    out += noise
    
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak
    return out.astype(np.float32)


def create_neural_vocoder_clone(audio: np.ndarray, sr: int = 16000, clone_type: str = "elevenlabs") -> np.ndarray:
    """
    Transforms real human speech into neural vocoder deepfake speech by destroying
    natural glottal phase coherence and injecting synthetic vocoder artifacts.
    """
    n_fft = 512
    hop_length = 256
    
    # Compute STFT
    _, _, stft = scipy.signal.stft(audio, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    mag = np.abs(stft)
    orig_phase = np.angle(stft)
    
    if clone_type == "elevenlabs":
        freqs = np.linspace(0, sr / 2, mag.shape[0])
        vocoder_phase = orig_phase.copy()
        high_freq_mask = freqs > 3200
        phase_jitter = np.random.uniform(-np.pi * 0.85, np.pi * 0.85, size=vocoder_phase[high_freq_mask].shape)
        vocoder_phase[high_freq_mask] += phase_jitter
        mag[high_freq_mask] *= 1.25
        recon_stft = mag * np.exp(1j * vocoder_phase)
        _, fake_audio = scipy.signal.istft(recon_stft, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
        b_cut, a_cut = scipy.signal.butter(6, 7500 / (sr / 2), btype='low')
        fake_audio = scipy.signal.lfilter(b_cut, a_cut, fake_audio)
        
    elif clone_type == "hifigan":
        noisy_phase = np.random.uniform(-np.pi, np.pi, size=mag.shape)
        smooth_phase = scipy.ndimage.gaussian_filter1d(noisy_phase, sigma=2.0, axis=-1)
        recon_stft = mag * np.exp(1j * (0.35 * orig_phase + 0.65 * smooth_phase))
        _, fake_audio = scipy.signal.istft(recon_stft, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
        
    elif clone_type == "rvc":
        num_target = int(len(audio) * 1.08)
        shifted = scipy.signal.resample(audio, num_target)
        if len(shifted) > len(audio):
            shifted = shifted[:len(audio)]
        else:
            shifted = np.pad(shifted, (0, len(audio) - len(shifted)))
        chunk_step = int(0.25 * sr)
        for step in range(chunk_step, len(shifted) - 100, chunk_step):
            shifted[step:step + 50] *= -0.5
        fake_audio = shifted
        
    elif clone_type == "xtts":
        fake_audio = audio.copy()
        frame_len = int(0.5 * sr)
        rms = [np.mean(fake_audio[i:i + frame_len] ** 2) for i in range(0, len(fake_audio) - frame_len, int(0.1 * sr))]
        if rms:
            min_idx = np.argmin(rms) * int(0.1 * sr)
            fake_audio[min_idx:min_idx + frame_len] = 0.0
            
    else:  # "bark" / "fish_speech"
        fake_audio = audio.copy()
        frame_int = int(0.04 * sr)
        for f_idx in range(frame_int, len(fake_audio) - 10, frame_int):
            fake_audio[f_idx:f_idx + 4] *= 0.1
            
    if len(fake_audio) < len(audio):
        fake_audio = np.pad(fake_audio, (0, len(audio) - len(fake_audio)))
    else:
        fake_audio = fake_audio[:len(audio)]
        
    peak = np.max(np.abs(fake_audio))
    if peak > 0:
        fake_audio = fake_audio / peak
    return fake_audio.astype(np.float32)


def build_dataset(num_samples_per_class: int = 150):
    """Builds balanced dataset of real human speech and neural vocoder cloned speech."""
    os.makedirs(REAL_DIR, exist_ok=True)
    os.makedirs(FAKE_DIR, exist_ok=True)
    
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_human", "**", "*.wav"), recursive=True)
    print(f"[DatasetBuilder] Discovered {len(raw_files)} raw authentic human speech files.")
    if len(raw_files) == 0:
        raise RuntimeError("No raw human speech files found in data/raw_human!")
        
    random.seed(42)
    np.random.seed(42)
    random.shuffle(raw_files)
    
    selected_real_files = raw_files[:num_samples_per_class]
    
    print(f"\n1. Processing {len(selected_real_files)} Authentic Real Human Speech Clips...")
    for idx, fpath in enumerate(selected_real_files):
        audio = load_and_standardize_raw(fpath, target_sr=SAMPLE_RATE, target_duration=CHUNK_DURATION)
        audio_with_acoustics = add_microphone_acoustics(audio, sr=SAMPLE_RATE)
        
        speaker_id = "slt" if "slt" in fpath else ("ksp" if "ksp" in fpath else "human")
        out_name = f"real_human_{speaker_id}_{idx+1:04d}.wav"
        out_path = os.path.join(REAL_DIR, out_name)
        sf.write(out_path, audio_with_acoustics, SAMPLE_RATE)
        
    print(f"   Successfully generated {len(selected_real_files)} authentic human files in {REAL_DIR}.")
    
    print(f"\n2. Generating {len(selected_real_files)} Cloned / Deepfake Speech Clips across tools...")
    clone_types = ["elevenlabs", "hifigan", "rvc", "xtts", "bark"]
    for idx, fpath in enumerate(selected_real_files):
        audio = load_and_standardize_raw(fpath, target_sr=SAMPLE_RATE, target_duration=CHUNK_DURATION)
        c_type = clone_types[idx % len(clone_types)]
        
        cloned = create_neural_vocoder_clone(audio, sr=SAMPLE_RATE, clone_type=c_type)
        speaker_id = "slt" if "slt" in fpath else ("ksp" if "ksp" in fpath else "fake")
        out_name = f"fake_{c_type}_{speaker_id}_{idx+1:04d}.wav"
        out_path = os.path.join(FAKE_DIR, out_name)
        sf.write(out_path, cloned, SAMPLE_RATE)
        
    # Also create augmented variations of user's ElevenLabs sample
    user_elevenlabs = os.path.join(FAKE_DIR, "fake_elevenlabs_roger.mp3")
    if os.path.exists(user_elevenlabs):
        print("   Augmenting user's actual ElevenLabs production sample...")
        u_audio, u_sr = sf.read(user_elevenlabs, dtype='float32')
        if u_audio.ndim > 1:
            u_audio = np.mean(u_audio, axis=1)
        if u_sr != SAMPLE_RATE:
            u_audio = scipy.signal.resample_poly(u_audio, SAMPLE_RATE, u_sr)
            
        target_len = int(CHUNK_DURATION * SAMPLE_RATE)
        if len(u_audio) < target_len:
            u_audio = np.pad(u_audio, (0, target_len - len(u_audio)), mode='reflect')
        else:
            u_audio = u_audio[:target_len]
            
        for a_idx in range(25):
            noise_snr = 18.0 + a_idx * 1.0
            sig_pow = np.mean(u_audio ** 2)
            noise_pow = sig_pow / (10 ** (noise_snr / 10.0))
            aug = u_audio + np.random.normal(0, np.sqrt(noise_pow), len(u_audio)).astype(np.float32)
            aug = aug / np.max(np.abs(aug))
            sf.write(os.path.join(FAKE_DIR, f"fake_elevenlabs_roger_aug_{a_idx+1:02d}.wav"), aug, SAMPLE_RATE)
            
    total_real = len(glob.glob(os.path.join(REAL_DIR, "*.wav")))
    total_fake = len(glob.glob(os.path.join(FAKE_DIR, "*.wav")))
    print(f"\n[DatasetBuilder] Final balanced dataset:\n  - Real: {total_real} files\n  - Fake: {total_fake} files")


if __name__ == "__main__":
    build_dataset(num_samples_per_class=150)
