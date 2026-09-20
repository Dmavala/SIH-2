"""
Training Pipeline for 3-Branch Voice Cloning / Deepfake Speech Detector.

Features:
- Joint multi-task optimization across all 3 branches + ensemble score
- Optimizer: AdamW (lr=1e-4, weight_decay=0.01)
- Scheduler: CosineAnnealingWarmRestarts (T_0=10)
- Loss: Binary Cross-Entropy with Label Smoothing (0.05)
- Early Stopping: Tracked on Validation EER (Equal Error Rate) with patience=7
- Automatic checkpointing: Best model saved to checkpoints/best_model.pt
- Generates train/val metrics history (JSON + Plots)
"""

import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import glob
import json
import random
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_curve, auc

from voice_cloning_detector.config import (
    REAL_DIR, FAKE_DIR, CHECKPOINTS_DIR, REPORTS_DIR,
    BATCH_SIZE, LEARNING_RATE, WEIGHT_DECAY, EPOCHS, PATIENCE,
    LABEL_SMOOTHING, COSINE_T0, DEVICE
)
from voice_cloning_detector.dataset import VoiceCloningDataset, split_by_speaker
from voice_cloning_detector.models.ensemble import EnsembleVoiceCloningDetector


def compute_eer(y_true: np.ndarray, y_scores: np.ndarray):
    """
    Computes Equal Error Rate (EER) and the optimal threshold where FAR == FRR.
    """
    if len(np.unique(y_true)) < 2:
        return 0.5, 0.5
        
    fpr, tpr, thresholds = roc_curve(y_true, y_scores, pos_label=1)
    fnr = 1.0 - tpr
    idx = int(np.nanargmin(np.abs(fnr - fpr)))
    eer = float((fpr[idx] + fnr[idx]) / 2.0)
    eer_thresh = float(thresholds[idx]) if idx < len(thresholds) else 0.5
    return eer, eer_thresh


def build_file_records(real_dir: str, fake_dir: str):
    """
    Scans real and fake audio directories, parses speaker IDs and generator labels.
    """
    records = []
    
    # Real files
    real_paths = glob.glob(os.path.join(real_dir, "*.wav")) + glob.glob(os.path.join(real_dir, "*.mp3"))
    for p in real_paths:
        base = os.path.basename(p)
        parts = base.split("_")
        if len(parts) > 2 and parts[1] == "human":
            speaker = parts[2]
        elif len(parts) > 1:
            speaker = parts[1]
        else:
            speaker = "spk_real"
        records.append({
            "path": p,
            "label": 0.0,
            "speaker": speaker,
            "generator": "real"
        })
        
    # Fake files
    fake_paths = glob.glob(os.path.join(fake_dir, "*.wav")) + glob.glob(os.path.join(fake_dir, "*.mp3"))
    for p in fake_paths:
        base = os.path.basename(p)
        parts = base.split("_")
        gen = parts[1] if len(parts) > 1 else "synthetic"
        speaker = parts[2] if len(parts) > 2 else "spk_fake"
        records.append({
            "path": p,
            "label": 1.0,
            "speaker": speaker,
            "generator": gen
        })
        
    return records


def train_model(
    real_dir: str = REAL_DIR,
    fake_dir: str = FAKE_DIR,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    lr: float = LEARNING_RATE,
    patience: int = PATIENCE,
    device: torch.device = DEVICE
):
    """
    Main training routine.
    """
    print(f"--- Starting Voice Cloning Detector Training on {device} ---")
    records = build_file_records(real_dir, fake_dir)
    print(f"Found {len(records)} total audio recordings.")
    if len(records) == 0:
        raise ValueError(f"No audio files found in {real_dir} or {fake_dir}!")
        
    train_recs, val_recs, test_recs = split_by_speaker(records, train_ratio=0.70, val_ratio=0.15)
    print(f"Splits: {len(train_recs)} Train | {len(val_recs)} Val | {len(test_recs)} Test")
    
    train_ds = VoiceCloningDataset(train_recs, augment=True)
    val_ds = VoiceCloningDataset(val_recs, augment=False)
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    
    # Initialize 3-Branch Ensemble
    model = EnsembleVoiceCloningDetector(device=device)
    
    # Optimizer only updates trainable parameters (Wav2Vec2 backbone stays FROZEN)
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=COSINE_T0)
    
    criterion = nn.BCELoss()
    
    best_val_eer = float("inf")
    patience_counter = 0
    history = []
    
    best_checkpoint_path = os.path.join(CHECKPOINTS_DIR, "best_model.pt")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        
        for batch in train_loader:
            wf = batch["waveform"].to(device)
            ps = batch["phase_spec"].to(device)
            tf = batch["temporal_feat"].to(device)
            labels = batch["label"].to(device).unsqueeze(1)
            
            # Label Smoothing: 0.0 -> 0.05, 1.0 -> 0.95
            smoothed_labels = labels * (1.0 - 2.0 * LABEL_SMOOTHING) + LABEL_SMOOTHING
            
            optimizer.zero_grad()
            
            final_score, s1, s2, s3 = model(wf, ps, tf)
            
            # Multi-Task Joint Loss: optimizes ensemble and each branch
            loss_final = criterion(final_score, smoothed_labels)
            loss_b1 = criterion(s1, smoothed_labels)
            loss_b2 = criterion(s2, smoothed_labels)
            loss_b3 = criterion(s3, smoothed_labels)
            
            total_loss = loss_final + 0.25 * loss_b1 + 0.25 * loss_b2 + 0.25 * loss_b3
            total_loss.backward()
            
            # Gradient clipping for stability
            torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
            
            optimizer.step()
            train_losses.append(total_loss.item())
            
        scheduler.step()
        avg_train_loss = float(np.mean(train_losses)) if train_losses else 0.0
        
        # Validation Evaluation
        model.eval()
        val_losses = []
        all_true = []
        all_pred_scores = []
        
        with torch.no_grad():
            for batch in val_loader:
                wf = batch["waveform"].to(device)
                ps = batch["phase_spec"].to(device)
                tf = batch["temporal_feat"].to(device)
                labels = batch["label"].to(device).unsqueeze(1)
                
                final_score, _, _, _ = model(wf, ps, tf)
                loss = criterion(final_score, labels)
                
                val_losses.append(loss.item())
                all_true.extend(labels.cpu().squeeze().tolist() if labels.numel() > 1 else [labels.cpu().item()])
                all_pred_scores.extend(final_score.cpu().squeeze().tolist() if final_score.numel() > 1 else [final_score.cpu().item()])
                
        avg_val_loss = float(np.mean(val_losses)) if val_losses else 0.0
        y_true_np = np.array(all_true)
        y_scores_np = np.array(all_pred_scores)
        y_pred_np = (y_scores_np > 0.50).astype(int)
        
        val_acc = accuracy_score(y_true_np, y_pred_np)
        val_prec, val_rec, val_f1, _ = precision_recall_fscore_support(y_true_np, y_pred_np, average='binary', zero_division=0)
        val_eer, val_eer_thresh = compute_eer(y_true_np, y_scores_np)
        
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "val_loss": round(avg_val_loss, 4),
            "val_accuracy": round(float(val_acc), 4),
            "val_precision": round(float(val_prec), 4),
            "val_recall": round(float(val_rec), 4),
            "val_f1": round(float(val_f1), 4),
            "val_eer": round(float(val_eer), 4),
            "val_eer_threshold": round(float(val_eer_thresh), 4)
        }
        history.append(epoch_metrics)
        
        print(f"Epoch [{epoch:02d}/{epochs}] "
              f"Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | "
              f"Val Acc: {val_acc*100:.1f}% | Val EER: {val_eer*100:.2f}% | Val F1: {val_f1:.3f}")
              
        # Early Stopping on Val EER
        if val_eer < best_val_eer:
            best_val_eer = val_eer
            patience_counter = 0
            # Save checkpoint
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "metrics": epoch_metrics,
                "weights": model.weights
            }, best_checkpoint_path)
            print(f"  --> Saved new best checkpoint (Val EER: {best_val_eer*100:.2f}%) to {best_checkpoint_path}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered after {patience} epochs without EER improvement.")
                break
                
    # Save training history
    history_file = os.path.join(REPORTS_DIR, "training_history.json")
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Training history saved to {history_file}")
    
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train 3-Branch Voice Cloning Detector")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
    parser.add_argument("--patience", type=int, default=PATIENCE)
    args = parser.parse_args()
    
    train_model(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, patience=args.patience)
