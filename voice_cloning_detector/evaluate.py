"""
Comprehensive Evaluation Suite for Voice Cloning / Deepfake Speech Detection System.

Calculates:
- Equal Error Rate (EER) and optimal threshold
- Accuracy, Precision, Recall, F1-Score, ROC-AUC
- Confusion Matrix (TN, FP, FN, TP)
- Per-Generator Performance Breakdown (RVC, XTTS, ElevenLabs, Bark, OpenVoice)
- Visualizations: ROC Curve, Confusion Matrix, and Generator Breakdown Bar Chart
"""

import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import glob
import json
import argparse
import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    roc_curve, auc, confusion_matrix
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from voice_cloning_detector.config import (
    CHECKPOINTS_DIR, REPORTS_DIR, REAL_DIR, FAKE_DIR,
    DECISION_THRESHOLD, DEVICE
)
from voice_cloning_detector.dataset import VoiceCloningDataset, split_by_speaker
from voice_cloning_detector.train import build_file_records, compute_eer
from voice_cloning_detector.models.ensemble import EnsembleVoiceCloningDetector


def evaluate_system(
    checkpoint_path: str = None,
    real_dir: str = REAL_DIR,
    fake_dir: str = FAKE_DIR,
    output_dir: str = REPORTS_DIR,
    device: torch.device = DEVICE
):
    """
    Evaluates detector on test split and outputs metrics, tables, and plots.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if checkpoint_path is None:
        checkpoint_path = os.path.join(CHECKPOINTS_DIR, "best_model.pt")
        
    records = build_file_records(real_dir, fake_dir)
    _, _, test_recs = split_by_speaker(records, train_ratio=0.70, val_ratio=0.15)
    
    # If test split is small or empty, evaluate on all records
    eval_recs = test_recs if len(test_recs) >= 4 else records
    print(f"Evaluating model on {len(eval_recs)} test audio samples...")
    
    test_ds = VoiceCloningDataset(eval_recs, augment=False)
    test_loader = DataLoader(test_ds, batch_size=8, shuffle=False)
    
    # Initialize and load model
    model = EnsembleVoiceCloningDetector(device=device)
    if os.path.exists(checkpoint_path):
        print(f"Loading weights from {checkpoint_path}...")
        ckpt = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"], strict=False)
    else:
        print(f"Checkpoint not found at {checkpoint_path}, evaluating with initialized weights.")
        
    model.eval()
    
    all_targets = []
    all_scores = []
    all_b1 = []
    all_b2 = []
    all_b3 = []
    all_generators = []
    
    with torch.no_grad():
        for batch in test_loader:
            wf = batch["waveform"].to(device)
            ps = batch["phase_spec"].to(device)
            tf = batch["temporal_feat"].to(device)
            labels = batch["label"]
            gens = batch["generator"]
            
            final_s, s1, s2, s3 = model(wf, ps, tf)
            
            all_scores.extend(final_s.cpu().squeeze(-1).tolist() if final_s.numel() > 1 else [final_s.cpu().item()])
            all_b1.extend(s1.cpu().squeeze(-1).tolist() if s1.numel() > 1 else [s1.cpu().item()])
            all_b2.extend(s2.cpu().squeeze(-1).tolist() if s2.numel() > 1 else [s2.cpu().item()])
            all_b3.extend(s3.cpu().squeeze(-1).tolist() if s3.numel() > 1 else [s3.cpu().item()])
            all_targets.extend(labels.tolist())
            all_generators.extend(gens)
            
    y_true = np.array(all_targets, dtype=int)
    y_scores = np.array(all_scores, dtype=float)
    y_pred = (y_scores > DECISION_THRESHOLD).astype(int)
    
    # Overall Performance Metrics
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
    eer, eer_thresh = compute_eer(y_true, y_scores)
    
    fpr, tpr, _ = roc_curve(y_true, y_scores, pos_label=1)
    roc_auc = auc(fpr, tpr)
    
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    
    # Per-Generator Breakdown
    gen_stats = {}
    unique_gens = sorted(list(set(all_generators)))
    for g in unique_gens:
        mask = np.array([gen == g for gen in all_generators])
        g_true = y_true[mask]
        g_pred = y_pred[mask]
        g_scores = y_scores[mask]
        
        g_acc = float(accuracy_score(g_true, g_pred))
        g_mean_score = float(np.mean(g_scores)) if len(g_scores) > 0 else 0.0
        
        gen_stats[g] = {
            "sample_count": int(np.sum(mask)),
            "accuracy": round(g_acc, 4),
            "mean_prediction_score": round(g_mean_score, 4)
        }
        
    summary_report = {
        "overall_metrics": {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "eer": round(float(eer), 4),
            "eer_threshold": round(float(eer_thresh), 4),
            "roc_auc": round(float(roc_auc), 4),
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp)
            }
        },
        "per_generator_breakdown": gen_stats
    }
    
    report_path = os.path.join(output_dir, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(summary_report, f, indent=2)
    print(f"Report saved to {report_path}")
    
    # 1. Plot ROC Curve
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="#2563eb", lw=2, label=f"ROC Curve (AUC = {roc_auc:.3f})")
    plt.plot([0, 1], [0, 1], color="#9ca3af", linestyle="--", lw=1.5, label="Chance")
    plt.scatter([eer], [1 - eer], color="#dc2626", zorder=5, label=f"EER = {eer*100:.1f}%")
    plt.title("Voice Cloning Detector - ROC Curve", fontsize=12, fontweight="bold")
    plt.xlabel("False Positive Rate (Real flagged as Fake)", fontsize=10)
    plt.ylabel("True Positive Rate (Fake correctly identified)", fontsize=10)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="lower right")
    plt.tight_layout()
    roc_plot_path = os.path.join(output_dir, "roc_curve.png")
    plt.savefig(roc_plot_path, dpi=150)
    plt.close()
    
    # 2. Plot Confusion Matrix
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Real", "Fake"],
                yticklabels=["Real", "Fake"], cbar=False)
    plt.title("Confusion Matrix", fontsize=12, fontweight="bold")
    plt.ylabel("Ground Truth")
    plt.xlabel("Ensemble Prediction")
    plt.tight_layout()
    cm_plot_path = os.path.join(output_dir, "confusion_matrix.png")
    plt.savefig(cm_plot_path, dpi=150)
    plt.close()
    
    # 3. Plot Per-Generator Breakdown
    fake_gens = [g for g in unique_gens if g != "real"]
    if fake_gens:
        gen_accs = [gen_stats[g]["accuracy"] * 100 for g in fake_gens]
        plt.figure(figsize=(7, 4))
        bars = plt.bar(fake_gens, gen_accs, color="#4f46e5", width=0.5)
        plt.ylim(0, 110)
        plt.ylabel("Detection Accuracy (%)")
        plt.title("Detection Accuracy by Cloning Generator / Vocoder", fontsize=12, fontweight="bold")
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{yval:.1f}%", ha='center', va='bottom', fontsize=9)
        plt.grid(axis="y", linestyle=":", alpha=0.6)
        plt.tight_layout()
        gen_plot_path = os.path.join(output_dir, "generator_breakdown.png")
        plt.savefig(gen_plot_path, dpi=150)
        plt.close()
        
    print("\n--- EVALUATION SUMMARY ---")
    print(f"Accuracy:  {acc*100:.2f}%")
    print(f"EER:       {eer*100:.2f}% (Threshold: {eer_thresh:.3f})")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"Precision: {prec*100:.2f}%")
    print(f"Recall:    {rec*100:.2f}%")
    print(f"F1-Score:  {f1:.4f}")
    print("--------------------------")
    return summary_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Voice Cloning Detector")
    parser.add_argument("--checkpoint", type=str, default=None)
    args = parser.parse_args()
    evaluate_system(checkpoint_path=args.checkpoint)
