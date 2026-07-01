"""
validate_model.py — Pre-deployment model validation gate.

Loads a saved TorchScript checkpoint, runs inference on ramdisk flows,
and asserts minimum per-class accuracy thresholds. Returns exit code 0
(pass) or 1 (fail) for scripting.

Usage (SCP to defender, then run):
    python3 validate_model.py --checkpoint /path/to/model.pt [--flows-dir /mnt/ramdisk/flows]
"""

import argparse
import sys

sys.path.append("/root")

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

import client

LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}

# Minimum acceptable per-class F1 score for deployment
MIN_F1_THRESHOLDS = {
    0: 0.50,  # Normal
    1: 0.60,  # Botnet
    2: 0.70,  # Exfiltration
    3: 0.50,  # BruteForce
    4: 0.70,  # DoS
}


def main():
    parser = argparse.ArgumentParser(description="Model validation gate")
    parser.add_argument("--checkpoint", required=True, help="Path to TorchScript model (.pt)")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--dos-threshold-ms", type=float, default=2000.0, help="DoS flow duration threshold in ms")
    args = parser.parse_args()

    print(f"Loading checkpoint: {args.checkpoint}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.jit.load(args.checkpoint, map_location=device)
    model.eval()

    print(f"Loading flows from: {args.flows_dir}")
    try:
        X, y = client.load_ramdisk_flows(args.flows_dir, dos_threshold_ms=args.dos_threshold_ms)
    except FileNotFoundError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=128, shuffle=False)

    all_preds, all_targets = [], []
    total_loss, total = 0.0, 0
    criterion = torch.nn.CrossEntropyLoss()

    with torch.no_grad():
        for X_batch, y_batch in dataloader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            total_loss += loss.item() * X_batch.size(0)
            total += y_batch.size(0)
            _, predicted = torch.max(outputs, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(y_batch.numpy())

    overall_acc = np.mean(np.array(all_preds) == np.array(all_targets))
    avg_loss = total_loss / total if total > 0 else 0.0

    print(f"\nOverall Accuracy: {overall_acc:.4f}")
    print(f"Average Loss:    {avg_loss:.4f}")
    print(f"Total Samples:   {total}")

    # Per-class validation
    passed = True
    print(f"\nPer-class Validation:")
    print(f"  {'Class':>15s}  {'Accuracy':>8s}  {'F1 Score':>8s}  {'Threshold':>9s}  {'Status':>6s}  {'Samples':>7s}")
    print(f"  {'-'*15}  {'-'*8}  {'-'*8}  {'-'*9}  {'-'*6}  {'-'*7}")

    for label in range(5):
        mask = np.array(all_targets) == label
        n_samples = mask.sum()
        if n_samples > 0:
            acc = (np.array(all_preds)[mask] == label).sum() / n_samples
            
            # Calculate F1 score
            tp = ((np.array(all_preds) == label) & (np.array(all_targets) == label)).sum()
            fp = ((np.array(all_preds) == label) & (np.array(all_targets) != label)).sum()
            fn = ((np.array(all_preds) != label) & (np.array(all_targets) == label)).sum()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            threshold = MIN_F1_THRESHOLDS[label]
            status = "PASS" if f1 >= threshold else "FAIL"
            if status == "FAIL":
                passed = False
            print(f"  {LABEL_NAMES[label]:>15s}  {acc:>8.4f}  {f1:>8.4f}  {threshold:>9.2f}  {status:>6s}  {n_samples:>7d}")
        else:
            print(f"  {LABEL_NAMES[label]:>15s}  {'N/A':>8s}  {'N/A':>8s}  {MIN_F1_THRESHOLDS[label]:>9.2f}  {'SKIP':>6s}  {0:>7d}")

    # Confusion matrix
    print("\nConfusion Matrix:")
    cm = pd.crosstab(
        pd.Series(all_targets, name="Actual"),
        pd.Series(all_preds, name="Predicted"),
        margins=True,
    )
    print(cm.to_string())

    if passed:
        print("\n✓ VALIDATION PASSED — model meets all per-class thresholds")
        sys.exit(0)
    else:
        print("\n✗ VALIDATION FAILED — one or more classes below threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
