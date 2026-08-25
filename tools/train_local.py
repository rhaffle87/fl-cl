"""
train_local.py — Standalone Local Training & Confusion Matrix Diagnostic Utility.

Trains the CyberDefenseNet backbone locally on an edge defender's ramdisk flow dataset
(outside the distributed Flower FL loop) to diagnose classification convergence or label imbalance.

Usage:
    python3 tools/train_local.py [--flows-dir /mnt/ramdisk/flows] [--epochs 40] [--model-type cnn]
"""

import argparse
import sys
import os
from pathlib import Path
from collections import Counter

# Standard path resolution
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src" / "defender"))
sys.path.insert(0, str(repo_root / "src"))
sys.path.append("/root")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.utils.data import DataLoader, TensorDataset

import client
from model import get_model

LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}


def main():
    parser = argparse.ArgumentParser(description="Standalone local defender training with confusion matrix")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory on ramdisk (default: /mnt/ramdisk/flows)")
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs (default: 40)")
    parser.add_argument("--lr", type=float, default=0.005, help="Learning rate (default: 0.005)")
    parser.add_argument("--dos-threshold-ms", type=float, default=2000.0, help="DoS flow duration threshold in ms (default: 2000.0)")
    parser.add_argument("--model-type", default="cnn", choices=["mlp", "cnn", "transformer"], help="Model architecture type (default: cnn)")
    args = parser.parse_args()

    print("========================================================================")
    print("       FL-CL Standalone Local Defender Training Diagnostic Suite")
    print("========================================================================")
    print(f"[*] Loading ramdisk flows from: {args.flows_dir}")
    try:
        X, y = client.load_ramdisk_flows(args.flows_dir, dos_threshold_ms=args.dos_threshold_ms)
    except Exception as e:
        print(f"[FAIL] Error loading flows: {e}")
        sys.exit(1)

    print(f"[*] Loaded X shape: {X.shape}, y shape: {y.shape}")
    print(f"[*] Label distribution: {dict(Counter(y.numpy()))}")

    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = get_model(args.model_type, input_dim=X.shape[1], num_classes=5).to(device)

    optimizer = Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    print(f"\n[*] Training {args.model_type.upper()} locally for {args.epochs} epochs on {device}...")
    model.train()
    for epoch in range(args.epochs):
        total_loss, correct, total = 0.0, 0, 0
        for X_batch, y_batch in dataloader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * X_batch.size(0)
            _, predicted = torch.max(outputs, 1)
            correct += (predicted == y_batch).sum().item()
            total += y_batch.size(0)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:>3d}/{args.epochs} — Loss: {total_loss/total:.4f}  Acc: {correct/total:.4f}")

    # Evaluate: confusion matrix + per-class accuracy
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for X_batch, y_batch in DataLoader(dataset, batch_size=128, shuffle=False):
            outputs = model(X_batch.to(device))
            _, predicted = torch.max(outputs, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(y_batch.numpy())

    print("\nConfusion Matrix:")
    cm = pd.crosstab(
        pd.Series(all_targets, name="Actual"),
        pd.Series(all_preds, name="Predicted"),
        margins=True,
    )
    print(cm.to_string())

    print("\nPer-class Accuracy:")
    for label in range(5):
        mask = np.array(all_targets) == label
        if mask.sum() > 0:
            acc = (np.array(all_preds)[mask] == label).sum() / mask.sum()
            print(f"  {label} ({LABEL_NAMES[label]:>13s}): {acc:.4f}  ({mask.sum()} samples)")
        else:
            print(f"  {label} ({LABEL_NAMES[label]:>13s}): N/A     (0 samples)")

    print("\n[OK] Local training diagnostic complete.")
    print("========================================================================\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
