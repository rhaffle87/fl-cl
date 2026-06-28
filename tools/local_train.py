"""
local_train.py — Standalone local training + confusion matrix.

Trains the CyberDefenseNet model locally on a defender's ramdisk data
(outside the Flower FL loop) to diagnose classification issues.

Usage (SCP to defender, then run):
    python3 local_train.py [--flows-dir /mnt/ramdisk/flows] [--epochs 40]
"""

import argparse
import sys

sys.path.append("/root")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from collections import Counter
from torch.optim import Adam
from torch.utils.data import DataLoader, TensorDataset

import client
from model import CyberDefenseNet

LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}


def main():
    parser = argparse.ArgumentParser(description="Local training with confusion matrix")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs")
    parser.add_argument("--lr", type=float, default=0.005, help="Learning rate")
    parser.add_argument("--dos-threshold-ms", type=float, default=2000.0, help="DoS flow duration threshold in ms")
    args = parser.parse_args()

    print("Loading ramdisk flows...")
    try:
        X, y = client.load_ramdisk_flows(args.flows_dir, dos_threshold_ms=args.dos_threshold_ms)
    except Exception as e:
        print(f"Error loading flows: {e}")
        return

    print(f"Loaded X shape: {X.shape}, y shape: {y.shape}")
    print(f"Label count: {Counter(y.numpy())}")

    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CyberDefenseNet().to(device)
    optimizer = Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    print(f"\nTraining model locally for {args.epochs} epochs...")
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


if __name__ == "__main__":
    main()
