"""
Real-Time Streaming Voice Cloning & Deepfake Speech Detector.

Features:
- Sub-500ms real-time sliding window detection (2.0s - 4.0s window with 0.5s updates).
- Energy-based Voice Activity Detection (VAD) to ignore room silence / background noise.
- Live microphone audio ingestion via SoundDevice.
- Real-time audio stream simulation from files or benchmark samples.
- ANSI color-coded live terminal dashboard.
"""

import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import time
import queue
import argparse
import numpy as np
import soundfile as sf
import torch

from voice_cloning_detector.config import (
    CHECKPOINTS_DIR, SAMPLE_RATE, DECISION_THRESHOLD, DEVICE
)
from voice_cloning_detector.dataset import load_and_standardize_audio
from voice_cloning_detector.models.ensemble import EnsembleVoiceCloningDetector
from voice_cloning_detector.feature_extraction import (
    compute_phase_spectrogram,
    extract_all_temporal_features,
    extract_breathing_patterns,
    extract_pitch_jitter_shimmer
)


def filter_audio_band(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    4th order bandpass filter (80 Hz to 7500 Hz) to eliminate sub-80Hz laptop/mic mechanical rumble
    and ultra-high frequency soundcard noise.
    """
    import scipy.signal
    sos = scipy.signal.butter(4, [80, min(7500, sr // 2 - 100)], btype='bandpass', fs=sr, output='sos')
    return scipy.signal.sosfilt(sos, audio).astype(np.float32)


class RealTimeAudioStreamDetector:
    """
    Real-Time Sliding Window Detector for Voice Cloning & Deepfakes.
    """
    def __init__(
        self,
        checkpoint_path: str = None,
        window_duration: float = 4.0,   # 4.0 second sliding window for full acoustic resolution
        hop_duration: float = 0.5,      # 500ms update interval
        vad_energy_threshold: float = 0.020,
        vad_min_speech_ratio: float = 0.25,
        device: torch.device = DEVICE
    ):
        self.sr = SAMPLE_RATE
        self.window_duration = window_duration
        self.hop_duration = hop_duration
        self.window_samples = int(window_duration * self.sr)
        self.hop_samples = int(hop_duration * self.sr)
        self.vad_energy_threshold = vad_energy_threshold
        self.vad_min_speech_ratio = vad_min_speech_ratio
        self.device = device
        
        # Audio ring buffer and stream tracking
        self.buffer = np.zeros(self.window_samples, dtype=np.float32)
        self.samples_received = 0
        self.smoothed_score = None
        
        # Load Ensemble model
        if checkpoint_path is None:
            checkpoint_path = os.path.join(CHECKPOINTS_DIR, "best_model.pt")
            
        print(f"[RealTimeDetector] Initializing 3-Branch Ensemble on {device}...")
        self.model = EnsembleVoiceCloningDetector(device=device)
        if os.path.exists(checkpoint_path):
            print(f"[RealTimeDetector] Loading trained weights from {checkpoint_path}...")
            ckpt = torch.load(checkpoint_path, map_location=device)
            self.model.load_state_dict(ckpt["model_state_dict"], strict=False)
        else:
            print(f"[RealTimeDetector] Warning: Checkpoint {checkpoint_path} not found. Using initialized weights.")
        self.model.eval()

    def reset(self):
        """Resets the streaming buffer and temporal smoothing."""
        self.buffer = np.zeros(self.window_samples, dtype=np.float32)
        self.samples_received = 0
        self.smoothed_score = None
        
    def check_vad(self, audio_chunk: np.ndarray) -> bool:
        """
        Voice Activity Detector with mechanical rumble suppression.
        Returns True if at least vad_min_speech_ratio of the chunk contains human speech energy.
        """
        if len(audio_chunk) == 0:
            return False
            
        filt_chunk = filter_audio_band(audio_chunk, sr=self.sr)
        frame_len = 512
        if len(filt_chunk) < frame_len:
            return False
            
        num_frames = len(filt_chunk) // frame_len
        frames = filt_chunk[:num_frames * frame_len].reshape(num_frames, frame_len)
        frame_rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-8)
        speech_frames = np.sum(frame_rms > self.vad_energy_threshold)
        speech_ratio = speech_frames / float(num_frames)
        return speech_ratio >= self.vad_min_speech_ratio
        
    @torch.no_grad()
    def process_chunk(self, new_samples: np.ndarray) -> dict:
        """
        Appends new incoming audio chunk (e.g. 500ms) to sliding buffer and runs detection.
        
        Returns:
            Dict containing real-time detection results.
        """
        start_time = time.time()
        
        new_samples = np.asarray(new_samples, dtype=np.float32).flatten()
        n_new = len(new_samples)
        self.samples_received += n_new
        
        # Shift ring buffer left and append new samples
        if n_new >= self.window_samples:
            self.buffer = new_samples[-self.window_samples:].astype(np.float32)
        else:
            self.buffer = np.roll(self.buffer, -n_new)
            self.buffer[-n_new:] = new_samples.astype(np.float32)
            
        # Determine active speech history (avoids evaluating cold zeros during warmup)
        active_len = min(self.samples_received, self.window_samples)
        active_samples = self.buffer[-active_len:]
        
        # Check VAD on active recent audio
        has_speech = self.check_vad(active_samples)
        if not has_speech or active_len < int(0.8 * self.sr):
            return {
                "status": "IDLE / SILENCE",
                "speech_detected": False,
                "prediction": "IDLE",
                "final_score": 0.0,
                "confidence": 0.0,
                "latency_ms": round((time.time() - start_time) * 1000, 1),
                "branch1": 0.0,
                "branch2": 0.0,
                "branch3": 0.0,
                "breaths": 0,
                "jitter": 0.0
            }
            
        # Construct seamless 4.0-second slice without digital-zero step discontinuities
        if active_len < self.window_samples:
            repeats = int(np.ceil(self.window_samples / max(active_len, 1)))
            analysis_audio = np.tile(active_samples, repeats)[:self.window_samples]
        else:
            analysis_audio = self.buffer.copy()
            
        # Bandpass filter the active speech window to suppress mic rumble
        analysis_audio = filter_audio_band(analysis_audio, sr=self.sr)

        # Peak normalize the active speech window
        peak = np.max(np.abs(analysis_audio))
        if peak > 0:
            analysis_audio = analysis_audio / peak
            
        # Extract features and predict
        pred_res = self.model.predict_clip(analysis_audio, sr=self.sr)
        
        raw_score = pred_res["final_score"]
        
        # Temporal exponential moving average for smooth real-time tracking
        if self.smoothed_score is None:
            self.smoothed_score = raw_score
        else:
            self.smoothed_score = 0.60 * self.smoothed_score + 0.40 * raw_score
            
        smoothed_val = float(self.smoothed_score)
        prediction = "FAKE" if smoothed_val > DECISION_THRESHOLD else "REAL"
        confidence = float(np.clip(abs(smoothed_val - DECISION_THRESHOLD) * 200.0, 0.0, 100.0))
        
        b1_val = pred_res["branch_scores"]["branch1_ssl"]
        b2_val = pred_res["branch_scores"]["branch2_phase"]
        b3_val = pred_res["branch_scores"]["branch3_temporal"]
        breaths = pred_res["diagnostics"].get("breath_segment_count", 0)
        jitter = pred_res["diagnostics"].get("jitter_local", 0.0)
        
        elapsed_ms = (time.time() - start_time) * 1000.0
        
        return {
            "status": "ACTIVE SPEECH",
            "speech_detected": True,
            "prediction": prediction,
            "final_score": round(smoothed_val, 4),
            "confidence": round(confidence, 1),
            "latency_ms": round(elapsed_ms, 1),
            "branch1": round(b1_val, 3),
            "branch2": round(b2_val, 3),
            "branch3": round(b3_val, 3),
            "breaths": int(breaths),
            "jitter": round(float(jitter), 4)
        }


def format_cli_output(timestamp_str: str, res: dict) -> str:
    """Formats detection output with colors and progress meters."""
    if not res["speech_detected"]:
        return f"[{timestamp_str}] \033[90m[VAD: IDLE / SILENCE]\033[0m Waiting for human speech..."
        
    is_fake = res["prediction"] == "FAKE"
    pred_color = "\033[91;1m" if is_fake else "\033[92;1m"
    reset = "\033[0m"
    
    # Meter bar (20 chars)
    score = res["final_score"]
    bar_len = int(score * 20)
    meter = f"[{'█' * bar_len}{' ' * (20 - bar_len)}]"
    
    line = (
        f"[{timestamp_str}] {pred_color}[{res['prediction']:^4}]{reset} "
        f"Score: {pred_color}{score:.3f}{reset} {meter} | "
        f"Conf: {res['confidence']:4.1f}% | "
        f"B1(SSL): {res['branch1']:.2f} | B2(Phase): {res['branch2']:.2f} | B3(Bio): {res['branch3']:.2f} | "
        f"Jitter: {res['jitter']:.4f} | Breaths: {res['breaths']} | "
        f"Latency: {res['latency_ms']}ms"
    )
    return line


def run_microphone_stream(checkpoint_path: str = None):
    """
    Live real-time stream directly capturing from the system microphone.
    """
    import sounddevice as sd
    
    detector = RealTimeAudioStreamDetector(checkpoint_path=checkpoint_path)
    audio_queue = queue.Queue()
    
    hop_samples = int(detector.hop_duration * detector.sr)
    
    def callback(indata, frames, time_info, status):
        if status:
            print(f"Status: {status}", file=sys.stderr)
        # Average to mono and enqueue
        mono_chunk = np.mean(indata, axis=1) if indata.ndim > 1 else indata.flatten()
        audio_queue.put(mono_chunk.copy())
        
    print("\n" + "="*80)
    print("      🎙️ LIVE REAL-TIME VOICE CLONING / DEEPFAKE SPEECH MONITOR")
    print("="*80)
    print("Listening to microphone at 16,000 Hz...")
    print("Updates every 500ms using a 4-second sliding analysis window.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        with sd.InputStream(
            samplerate=detector.sr,
            channels=1,
            blocksize=hop_samples,
            callback=callback
        ):
            accumulated_samples = []
            while True:
                chunk = audio_queue.get()
                res = detector.process_chunk(chunk)
                t_str = time.strftime("%H:%M:%S")
                print(format_cli_output(t_str, res))
                sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n[RealTimeDetector] Stopped microphone stream.")


def run_file_stream_simulation(file_path: str, checkpoint_path: str = None):
    """
    Simulates real-time streaming of an audio file in 500ms packets.
    """
    detector = RealTimeAudioStreamDetector(checkpoint_path=checkpoint_path)
    audio = load_and_standardize_audio(file_path, target_sr=detector.sr)
    hop_samples = int(detector.hop_duration * detector.sr)
    
    print("\n" + "="*80)
    print(f"   🔴 SIMULATING REAL-TIME STREAMING: {os.path.basename(file_path)}")
    print("="*80)
    print(f"Total Duration: {len(audio)/detector.sr:.2f}s | Streaming in 500ms chunks...\n")
    
    total_chunks = len(audio) // hop_samples
    for i in range(total_chunks):
        chunk = audio[i * hop_samples:(i + 1) * hop_samples]
        res = detector.process_chunk(chunk)
        t_sec = i * detector.hop_duration
        t_str = f"{t_sec:04.1f}s"
        print(format_cli_output(t_str, res))
        time.sleep(detector.hop_duration)  # Exact real-time pacing!
        
    print("\n[RealTimeDetector] Simulation complete.")


def run_benchmark_simulation(checkpoint_path: str = None):
    """
    Simulates a live transition: streams 8 seconds of authentic human speech,
    then seamlessly switches to 8 seconds of AI-cloned speech to showcase real-time detection transition!
    """
    detector = RealTimeAudioStreamDetector(checkpoint_path=checkpoint_path)
    
    # Load 2 real clips and 2 fake clips
    from .config import REAL_DIR, FAKE_DIR
    real_files = sorted([os.path.join(REAL_DIR, f) for f in os.listdir(REAL_DIR) if f.endswith(".wav")])[:2]
    fake_files = sorted([os.path.join(FAKE_DIR, f) for f in os.listdir(FAKE_DIR) if f.endswith(".wav")])[:2]
    
    stream_sequence = [
        ("Authentic Human Speaker 1", real_files[0]),
        ("Authentic Human Speaker 2", real_files[1]),
        ("AI Voice Clone (Tool 1)", fake_files[0]),
        ("AI Voice Clone (Tool 2)", fake_files[1]),
    ]
    
    print("\n" + "="*85)
    print("   🔴 LIVE REAL-TIME STREAMING BENCHMARK: HUMAN -> AI CLONE TRANSITION")
    print("="*85)
    print("Demonstrating real-time sliding-window detection across changing speakers and AI clones.\n")
    
    hop_samples = int(detector.hop_duration * detector.sr)
    
    for label, fpath in stream_sequence:
        print(f"\n>>> [STREAMING FEED ACTIVE]: {label} ({os.path.basename(fpath)})")
        audio = load_and_standardize_audio(fpath, target_sr=detector.sr)
        n_chunks = len(audio) // hop_samples
        for i in range(n_chunks):
            chunk = audio[i * hop_samples:(i + 1) * hop_samples]
            res = detector.process_chunk(chunk)
            t_str = f"+{i * detector.hop_duration:03.1f}s"
            print(format_cli_output(t_str, res))
            time.sleep(0.3)  # Fast-paced real-time demonstration
            
    print("\n[RealTimeDetector] Benchmark sequence finished successfully.")


def main():
    parser = argparse.ArgumentParser(description="Real-Time Streaming Voice Cloning Detection")
    parser.add_argument("--mic", action="store_true", help="Stream from live microphone")
    parser.add_argument("--file", type=str, help="Simulate real-time streaming of an audio file")
    parser.add_argument("--benchmark", action="store_true", help="Simulate live transition from Real speech to Cloned speech")
    parser.add_argument("--checkpoint", type=str, default=None)
    args = parser.parse_args()
    
    if args.mic:
        run_microphone_stream(checkpoint_path=args.checkpoint)
    elif args.file:
        run_file_stream_simulation(args.file, checkpoint_path=args.checkpoint)
    elif args.benchmark:
        run_benchmark_simulation(checkpoint_path=args.checkpoint)
    else:
        # Default to benchmark simulation if no args given
        run_benchmark_simulation(checkpoint_path=args.checkpoint)


if __name__ == "__main__":
    main()
