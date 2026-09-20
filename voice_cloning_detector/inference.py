"""
Inference Module for Voice Cloning / Deepfake Speech Detection System.

Features:
- Sub-5-second CPU inference on 4-second clips
- Supports single file, batch directory, or streaming sliding-window voting
- Outputs overall decision (REAL vs FAKE), confidence score, branch score breakdown,
  and biological/acoustic diagnostics (breathing, silence, jitter, shimmer)
- Rich CLI interface with color-coded formatting
"""

import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import time
import glob
import json
import argparse
import numpy as np
import torch
from typing import Dict, Any, List

from voice_cloning_detector.config import (
    CHECKPOINTS_DIR, SAMPLE_RATE, CHUNK_DURATION,
    TARGET_SAMPLES, DECISION_THRESHOLD, DEVICE
)
from voice_cloning_detector.dataset import load_and_standardize_audio, slice_into_chunks
from voice_cloning_detector.models.ensemble import EnsembleVoiceCloningDetector


class VoiceCloningInferenceEngine:
    """
    Production-ready Inference Engine for Voice Cloning Detection.
    """
    def __init__(
        self,
        checkpoint_path: str = None,
        device: torch.device = DEVICE,
        threshold: float = DECISION_THRESHOLD
    ):
        self.device = device
        self.threshold = threshold
        self.model = EnsembleVoiceCloningDetector(threshold=threshold, device=device)
        
        # Load best trained weights if available
        if checkpoint_path is None:
            checkpoint_path = os.path.join(CHECKPOINTS_DIR, "best_model.pt")
            
        if os.path.exists(checkpoint_path):
            print(f"[InferenceEngine] Loading model weights from {checkpoint_path}...")
            ckpt = torch.load(checkpoint_path, map_location=device)
            self.model.load_state_dict(ckpt["model_state_dict"], strict=False)
        else:
            print(f"[InferenceEngine] Warning: Checkpoint not found at {checkpoint_path}. Using initialized weights.")
            
        self.model.eval()
        
    def predict_file(
        self,
        file_path: str,
        overlap_seconds: float = 2.0
    ) -> Dict[str, Any]:
        """
        Analyzes an audio file across all sliding windows and aggregates decisions.
        
        Args:
            file_path: Absolute or relative path to audio file.
            overlap_seconds: Hop overlap between consecutive 4-second windows.
            
        Returns:
            Dictionary with aggregated prediction, confidence, per-branch scores,
            latency, and per-chunk analysis.
        """
        start_time = time.time()
        
        # 1. Load and resample audio
        audio = load_and_standardize_audio(file_path, target_sr=SAMPLE_RATE)
        total_duration = len(audio) / SAMPLE_RATE
        
        # 2. Slice into 4-second chunks
        overlap_samples = int(overlap_seconds * SAMPLE_RATE)
        chunks = slice_into_chunks(audio, chunk_samples=TARGET_SAMPLES, overlap_samples=overlap_samples)
        
        chunk_results = []
        scores = []
        b1_scores = []
        b2_scores = []
        b3_scores = []
        
        for idx, chunk in enumerate(chunks):
            res = self.model.predict_clip(chunk, sr=SAMPLE_RATE)
            chunk_results.append({
                "chunk_index": idx,
                "start_time_sec": round(idx * (CHUNK_DURATION - overlap_seconds), 2),
                "score": round(res["final_score"], 4),
                "prediction": res["prediction"],
                "confidence": round(res["confidence"], 2),
                "branch1_ssl": round(res["branch_scores"]["branch1_ssl"], 4),
                "branch2_phase": round(res["branch_scores"]["branch2_phase"], 4),
                "branch3_temporal": round(res["branch_scores"]["branch3_temporal"], 4),
                "diagnostics": res["diagnostics"]
            })
            scores.append(res["final_score"])
            b1_scores.append(res["branch_scores"]["branch1_ssl"])
            b2_scores.append(res["branch_scores"]["branch2_phase"])
            b3_scores.append(res["branch_scores"]["branch3_temporal"])
            
        # Aggregate across chunks (mean pooling of prediction scores)
        mean_score = float(np.mean(scores))
        mean_b1 = float(np.mean(b1_scores))
        mean_b2 = float(np.mean(b2_scores))
        mean_b3 = float(np.mean(b3_scores))
        
        overall_prediction = "FAKE" if mean_score > self.threshold else "REAL"
        overall_confidence = float(np.clip(abs(mean_score - 0.50) * 200.0, 0.0, 100.0))
        
        elapsed_time = time.time() - start_time
        
        # Aggregate diagnostics from first chunk or mean
        sample_diag = chunk_results[0]["diagnostics"] if chunk_results else {}
        
        return {
            "file": file_path,
            "duration_seconds": round(total_duration, 2),
            "chunks_analyzed": len(chunks),
            "overall_prediction": overall_prediction,
            "overall_score": round(mean_score, 4),
            "confidence_percentage": round(overall_confidence, 2),
            "branch_scores": {
                "branch1_ssl": round(mean_b1, 4),
                "branch2_phase": round(mean_b2, 4),
                "branch3_temporal": round(mean_b3, 4)
            },
            "diagnostics": sample_diag,
            "latency_seconds": round(elapsed_time, 3),
            "latency_per_chunk_seconds": round(elapsed_time / max(len(chunks), 1), 3),
            "chunk_breakdown": chunk_results
        }

    def predict_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        Runs batch prediction over all audio files in a directory.
        """
        extensions = ["*.wav", "*.mp3", "*.flac", "*.ogg", "*.m4a"]
        audio_files = []
        for ext in extensions:
            audio_files.extend(glob.glob(os.path.join(dir_path, ext)))
            
        print(f"[InferenceEngine] Found {len(audio_files)} audio files in {dir_path}")
        results = []
        for audio_file in sorted(audio_files):
            res = self.predict_file(audio_file)
            results.append(res)
            print(f"  {os.path.basename(audio_file):<35} -> {res['overall_prediction']:<5} (Conf: {res['confidence_percentage']:.1f}%, Score: {res['overall_score']:.3f}, Latency: {res['latency_seconds']:.2f}s)")
        return results


def main():
    parser = argparse.ArgumentParser(description="Voice Cloning / Deepfake Speech Detection CLI")
    parser.add_argument("--audio", type=str, help="Path to single audio file to analyze")
    parser.add_argument("--dir", type=str, help="Path to directory containing audio files")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to trained checkpoint (.pt)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    
    engine = VoiceCloningInferenceEngine(checkpoint_path=args.checkpoint)
    
    if args.audio:
        if not os.path.exists(args.audio):
            print(f"Error: File '{args.audio}' does not exist.")
            sys.exit(1)
        res = engine.predict_file(args.audio)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("\n" + "="*50)
            print("   VOICE CLONING DETECTION RESULT")
            print("="*50)
            print(f"Audio File:      {res['file']}")
            print(f"Duration:        {res['duration_seconds']} s (analyzed in {res['chunks_analyzed']} chunk(s))")
            print(f"Inference Time:  {res['latency_seconds']} s ({res['latency_per_chunk_seconds']} s/chunk)")
            print("-" * 50)
            status_color = "\033[91m" if res['overall_prediction'] == "FAKE" else "\033[92m"
            reset_color = "\033[0m"
            print(f"PREDICTION:      {status_color}{res['overall_prediction']}{reset_color}")
            print(f"CONFIDENCE:      {res['confidence_percentage']:.1f}%")
            print(f"PROBABILITY:     {res['overall_score']:.4f} (Threshold: 0.50)")
            print("-" * 50)
            print("BRANCH BREAKDOWN:")
            print(f"  Branch 1 (Wav2Vec2 SSL)    [Weight 50%]: {res['branch_scores']['branch1_ssl']:.4f}")
            print(f"  Branch 2 (Phase ResNet-18) [Weight 30%]: {res['branch_scores']['branch2_phase']:.4f}")
            print(f"  Branch 3 (Temporal/Bio)    [Weight 20%]: {res['branch_scores']['branch3_temporal']:.4f}")
            print("-" * 50)
            print("ACOUSTIC ARTIFACTS:")
            diag = res['diagnostics']
            print(f"  Breaths Detected:       {diag.get('breath_segment_count', 0)}")
            print(f"  Silence Ratio:          {diag.get('silence_ratio', 0.0)*100:.1f}%")
            print(f"  Pitch Jitter (local):   {diag.get('jitter_local', 0.0):.4f}")
            print(f"  Pitch Shimmer (local):  {diag.get('shimmer_local', 0.0):.4f}")
            print("="*50 + "\n")
            
    elif args.dir:
        if not os.path.exists(args.dir):
            print(f"Error: Directory '{args.dir}' does not exist.")
            sys.exit(1)
        results = engine.predict_directory(args.dir)
        if args.json:
            print(json.dumps(results, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
