"""
Full-system evaluation — runs the *deployed* code path (DeepfakeDetector ->
multi-engine consensus) over real in-repo corpora and writes an honest
benchmark report JSON that /api/benchmark-report serves.

No synthetic test signals, no cherry-picked files: every clip discovered in
--data-dir is scored, and every number in the report is measured on this
machine at run time.

Usage:
    python scripts/run_full_evaluation.py \
        --data-dir large_benchmark_data,scam_call_data,test_realworld_samples \
        --output full_benchmark_report.json
"""

import argparse
import json
import os
import sys
import time
from collections import Counter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import soundfile as sf

from backend.config import settings
from backend.models.detector import DeepfakeDetector
from backend.training.asvspoof import build_file_list

POSITIVE_DIRS = {"real", "bonafide", "normal", "authentic", "human", "genuine"}
NEGATIVE_DIRS = {"fake", "spoof", "scam", "synthetic", "fraud"}


def ground_truth_for(rel_path: str) -> str:
    parts = {p.lower() for p in rel_path.replace("\\", "/").split(os.sep)}
    if parts & POSITIVE_DIRS:
        return "REAL"
    if parts & NEGATIVE_DIRS:
        return "FAKE"
    return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run honest full-system benchmark")
    parser.add_argument(
        "--data-dir",
        default="large_benchmark_data,test_realworld_samples",
        help="Comma-separated dataset roots (only synthetic-vs-real labeled corpora)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON (default: config paths.benchmark_report)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max files (smoke)")
    parser.add_argument("--max-seconds", type=float, default=20.0,
                        help="Audio seconds analysed per file")
    args = parser.parse_args()

    out_path = args.output or settings.paths.benchmark_report

    roots = [r.strip() for r in args.data_dir.split(",") if r.strip()]
    files = []  # (abs_path, ground_truth, dataset_root)
    for root in roots:
        if not os.path.isdir(root):
            print(f"[eval] WARNING: data root not found: {root}")
            continue
        for path, label in build_file_list(root):
            files.append((path, "REAL" if label == 0 else "FAKE", root))
    if args.limit:
        files = files[: args.limit]

    if not files:
        print("[eval] No audio found — nothing to do.")
        sys.exit(1)

    detector = DeepfakeDetector()
    print(f"[eval] Engine: {detector.model_type}, "
          f"AASIST={'loaded' if detector.aasist else 'MISSING'}, "
          f"RawNet={'loaded' if detector.rawnet else 'MISSING'}")

    results = []
    lat_ms = []
    t_start = time.time()
    for i, (path, gt, root) in enumerate(files):
        try:
            audio, sr = sf.read(path, dtype="float32", always_2d=True)
            audio = audio.mean(axis=1)
            if sr != 16000:
                import scipy.signal as sps
                audio = sps.resample_poly(audio, 16000, sr).astype(np.float32)
                sr = 16000
            if audio.size > int(args.max_seconds * sr):
                # centre crop keeps speech-heavy middles, drops silent tails
                keep = int(args.max_seconds * sr)
                start = max(0, (audio.size - keep) // 2)
                audio = audio[start:start + keep]

            t0 = time.perf_counter()
            outcome = detector.analyze_audio(audio, sr)
            dt = (time.perf_counter() - t0) * 1000.0
            lat_ms.append(dt)

            results.append({
                "file": os.path.relpath(path, ROOT_DIR),
                "dataset": root,
                "ground_truth": gt,
                "verdict": outcome.get("status", "ERROR"),
                "risk": round(float(outcome.get("risk_score", 0.0)), 2),
                "latency_ms": round(dt, 2),
            })
        except Exception as exc:  # unreadable file — record honestly
            results.append({
                "file": os.path.relpath(path, ROOT_DIR),
                "dataset": root,
                "ground_truth": gt,
                "verdict": "ERROR",
                "error": str(exc)[:200],
            })
        if (i + 1) % 25 == 0:
            print(f"[eval] {i + 1}/{len(files)} scored...")

    evaluable = [r for r in results if r["ground_truth"] in ("REAL", "FAKE")
                 and r["verdict"] != "ERROR"]

    def ok(r):
        if r["ground_truth"] == "REAL":
            return not r["verdict"].startswith("CRITICAL")  # real audio never auto-flagged
        return not r["verdict"].startswith("AUTHENTIC")    # attacks never pass as real

    n_safe = sum(1 for r in evaluable if ok(r))
    n_crisp = sum(1 for r in evaluable
                  if r["verdict"].startswith("AUTHENTIC") or r["verdict"].startswith("CRITICAL"))
    n_correct_crisp = sum(1 for r in evaluable
                          if ok(r) and (r["verdict"].startswith("AUTHENTIC")
                                        or r["verdict"].startswith("CRITICAL")))

    real_rows = [r for r in evaluable if r["ground_truth"] == "REAL"]
    fake_rows = [r for r in evaluable if r["ground_truth"] == "FAKE"]
    real_scores = [r["risk"] for r in real_rows if "risk" in r]
    fake_scores = [r["risk"] for r in fake_rows if "risk" in r]

    real_ok = sum(1 for r in real_rows if ok(r))
    fake_ok = sum(1 for r in fake_rows if ok(r))

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "machine_note": "Measured on the deployment machine; CPU-only inference.",
        "engine": {
            "model_type": detector.model_type,
            "aasist_loaded": bool(detector.aasist),
            "rawnet_loaded": bool(detector.rawnet),
        },
        "dataset": {
            "roots": roots,
            "files_total": len(results),
            "files_evaluable": len(evaluable),
            "real_clips": len(real_rows),
            "fake_clips": len(fake_rows),
        },
        "safety_properties": {
            "real_audio_auto_flagged": len(real_rows) - real_ok,
            "attacks_passing_as_authentic": len(fake_rows) - fake_ok,
            "crisp_verdicts": n_crisp,
            "crisp_and_correct": n_correct_crisp,
            "escalations_to_review": len(evaluable) - n_crisp,
        },
        "risk_stats": {
            "real_mean": round(float(np.mean(real_scores)), 2) if real_scores else None,
            "real_max": round(float(np.max(real_scores)), 2) if real_scores else None,
            "fake_mean": round(float(np.mean(fake_scores)), 2) if fake_scores else None,
            "fake_min": round(float(np.min(fake_scores)), 2) if fake_scores else None,
        },
        "file_analysis_latency_ms": {
            "note": "Wall time to fully analyse one file (all 2s windows + consensus). NOT the stream per-frame latency, which is much lower.",
            "mean": round(float(np.mean(lat_ms)), 2) if lat_ms else None,
            "p95": round(float(np.percentile(lat_ms, 95)), 2) if lat_ms else None,
            "max": round(float(np.max(lat_ms)), 2) if lat_ms else None,
            "files_measured": len(lat_ms),
        },
        "verdict_counts": dict(Counter(r["verdict"] for r in evaluable)),
        "per_dataset": {
            root: {
                "verdict_counts": dict(Counter(r["verdict"] for r in results
                                               if r["dataset"] == root and r["verdict"] != "ERROR")),
            }
            for root in roots
        },
        "results": results,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print()
    print("=" * 64)
    print(f"EVALUATION COMPLETE -> {out_path}")
    print(f"  clips scored        : {len(results)} ({len(evaluable)} evaluable)")
    print(f"  real audio flagged  : {len(real_rows) - real_ok}  (target 0)")
    print(f"  attacks passing     : {len(fake_rows) - fake_ok}  (target 0)")
    print(f"  crisp verdicts      : {n_crisp}/{len(evaluable)} "
          f"({n_correct_crisp} correct)")
    print(f"  escalated to review : {len(evaluable) - n_crisp}")
    print(          f"latency mean/p95/max: {report['file_analysis_latency_ms']['mean']}/"
          f"{report['file_analysis_latency_ms']['p95']}/{report['file_analysis_latency_ms']['max']} ms (per file)")
    print("=" * 64)


if __name__ == "__main__":
    main()
