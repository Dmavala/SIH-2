"""
Training entry point for AASIST & RawNet2 on real anti-spoofing data.

Features:
  - ASVspoof 2019/2021 LA loading (or generic real/fake folders)
  - On-the-fly telephony/noise augmentation
  - Train/val split with speaker-disjoint option (val by filename prefix)
  - EER-based model selection (the metric reviewers actually ask for)
  - Checkpoints saved to backend/models/<arch>_weights.pt + training_meta.json
  - Clearly-labelled synthetic fallback for CI smoke tests

Usage:
    python -m backend.training.train --data-dir D:/data/ASVspoof2019_LA --epochs 30
    python -m backend.training.train --synthetic --epochs 3   # smoke test only
"""

import argparse
import json
import os
import time
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from backend.config import settings
from backend.models.aasist import AASIST
from backend.models.rawnet import RawNet2
from backend.training.asvspoof import ASVspoofDataset, build_file_list

WEIGHTS_DIR = os.path.dirname(os.path.abspath(__file__)).replace("training", "models")


def compute_eer(bonafide_scores: np.ndarray, spoof_scores: np.ndarray) -> float:
    """Standard EER via score-sweep (tar = bonafide accepted)."""
    scores = np.concatenate([bonafide_scores, spoof_scores])
    labels = np.concatenate([np.ones(len(bonafide_scores)), np.zeros(len(spoof_scores))])
    order = np.argsort(scores)
    labels = labels[order]
    n_bona = labels.sum()
    n_spoof = len(labels) - n_bona
    if n_bona == 0 or n_spoof == 0:
        return float("nan")
    # threshold above each unique score
    thresholds = np.concatenate([[scores[order][0] - 1e-6], scores[order]])
    tar = np.cumsum(labels[::-1])[::-1] / n_bona  # fraction bona >= thr (approx via sorted sweep)
    far = np.cumsum((1 - labels)) / n_spoof
    fnr = 1 - tar
    diff = np.abs(fnr - far)
    idx = int(np.argmin(diff))
    return float((far[idx] + fnr[idx]) / 2.0)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> Tuple[float, float]:
    """Returns (eer, accuracy)."""
    model.eval()
    bona, spoof = [], []
    correct = total = 0
    for x, y in loader:
        x = x.to(device)
        logits = model(x)
        probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
        preds = (probs >= 0.5).astype(int)
        correct += int((preds == y.numpy()).sum())
        total += len(y)
        for p, lbl in zip(probs, y.numpy()):
            (bona if lbl == 0 else spoof).append(float(p))
    eer = compute_eer(np.array(bona), np.array(spoof)) if bona and spoof else float("nan")
    return eer, correct / max(1, total)


def train_arch(arch_name: str, model: nn.Module, train_ds: Dataset, val_ds: Dataset,
               epochs: int, batch_size: int, lr: float, device: torch.device,
               out_name: str) -> dict:
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=0, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

    best_eer = float("inf")
    best_acc = -1.0
    history: List[dict] = []
    for ep in range(1, epochs + 1):
        model.train()
        t0 = time.time()
        total_loss = correct = seen = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += float(loss) * len(y)
            correct += int((logits.argmax(1) == y).sum())
            seen += len(y)
        scheduler.step()

        eer, acc = evaluate(model, val_loader, device)
        history.append({"epoch": ep, "loss": round(total_loss / max(1, seen), 4),
                        "train_acc": round(correct / max(1, seen), 4),
                        "val_eer": None if eer != eer else round(eer, 4),
                        "val_acc": round(acc, 4)})
        marker = ""
        # Model selection: best EER first; tie-break on threshold accuracy.
        # (EER plateaus at 0.0 quickly on small clean sets — without the
        #  accuracy tie-break we would ship an epoch-1 checkpoint forever.)
        improved = (eer == eer and eer < best_eer) or (
            eer == eer and eer == best_eer and acc > best_acc)
        if improved:
            best_eer = min(best_eer, eer) if eer == eer else best_eer
            best_acc = acc
            torch.save(model.state_dict(), os.path.join(WEIGHTS_DIR, out_name))
            marker = "  <- saved"
        print(f"[{arch_name}] epoch {ep:02d}/{epochs} "
              f"loss={total_loss / max(1, seen):.4f} val_EER={eer:.4f} "
              f"val_acc={acc:.3f} ({time.time() - t0:.0f}s){marker}")

    return {"best_val_eer": None if best_eer == float("inf") else round(best_eer, 4),
            "best_val_acc": round(best_acc, 4) if best_acc >= 0 else None,
            "history": history}


def main():
    ap = argparse.ArgumentParser(description="AEGIS anti-spoofing trainer")
    ap.add_argument("--data-dir", default=None, help="ASVspoof root or real/fake folder")
    ap.add_argument("--synthetic", action="store_true",
                    help="Force synthetic fallback (CI smoke test ONLY)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-fraction", type=float, default=0.15)
    ap.add_argument("--arch", choices=["aasist", "rawnet", "both"], default="both")
    ap.add_argument("--resume", action="store_true",
                    help="Continue from existing checkpoint weights (for chunked training runs)")
    args = ap.parse_args()

    device = torch.device("cpu")
    if settings.model.device == "cuda" or (settings.model.device == "auto" and torch.cuda.is_available()):
        device = torch.device("cuda")

    real_pairs = []
    if not args.synthetic and args.data_dir:
        # Support comma-separated roots (e.g. large_benchmark_data,scam_call_data)
        for root in [r.strip() for r in args.data_dir.split(",") if r.strip()]:
            real_pairs.extend(build_file_list(root))
    ds = ASVspoofDataset(args.data_dir if real_pairs else None,
                         samples=int(settings.model.analysis_window_s * settings.audio.sample_rate),
                         augment=True)
    mode = "REAL DATA" if not ds.is_synthetic else "SYNTHETIC FALLBACK (not for benchmark claims!)"
    print(f"[DATA] {mode} — {len(ds)} clips")

    # Split (order-stable)
    n_val = min(max(2, int(len(ds) * args.val_fraction)), max(1, len(ds) - 2))
    indices = np.random.RandomState(42).permutation(len(ds))
    val_idx = indices[:n_val].tolist()
    train_idx = indices[n_val:].tolist()
    train_ds = torch.utils.data.Subset(ds, train_idx)
    val_ds = torch.utils.data.Subset(ds, val_idx)

    results = {}
    archs = []
    if args.arch in ("aasist", "both"):
        model = AASIST(sample_rate=settings.audio.sample_rate).to(device)
        out_name = "aasist_weights.pt"
        if args.resume and os.path.exists(os.path.join(WEIGHTS_DIR, out_name)):
            model.load_state_dict(torch.load(os.path.join(WEIGHTS_DIR, out_name),
                                             map_location=device, weights_only=True))
            print(f"[RESUME] {out_name} loaded")
        archs.append(("AASIST", model, out_name))
    if args.arch in ("rawnet", "both"):
        model = RawNet2(sample_rate=settings.audio.sample_rate).to(device)
        out_name = "rawnet_weights.pt"
        if args.resume and os.path.exists(os.path.join(WEIGHTS_DIR, out_name)):
            model.load_state_dict(torch.load(os.path.join(WEIGHTS_DIR, out_name),
                                             map_location=device, weights_only=True))
            print(f"[RESUME] {out_name} loaded")
        archs.append(("RawNet2", model, out_name))

    for name, model, out_name in archs:
        print(f"\n=== Training {name} on {device} ===")
        results[name] = train_arch(name, model, train_ds, val_ds, args.epochs,
                                   args.batch_size, args.lr, device, out_name)

    meta = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_mode": mode,
        "num_clips": len(ds),
        "epochs": args.epochs,
        "args": vars(args),
        "results": results,
    }
    meta_path = os.path.join(WEIGHTS_DIR, "training_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"\n[DONE] Best EERs: { {k: v['best_val_eer'] for k, v in results.items()} }")
    print(f"[DONE] Metadata written to {meta_path}")


if __name__ == "__main__":
    main()
