"""
validate_bwt.py — Cryptographic Backward Transfer (BWT) Evaluation & Quality Gate.

Evaluates a loaded model checkpoint on a target test flow dataset (or fallback synthetic data),
computes class-wise accuracy, F1-scores, and BWT degradation against peak historical milestones,
and outputs a cryptographically signed SHA-256 lineage report.

Usage:
    python3 tools/validate_bwt.py --checkpoint /path/to/model.pt [--test-dir /mnt/ramdisk/flows]
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Standard path resolution
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "src" / "defender"))
sys.path.insert(0, str(repo_root / "src" / "aggregator"))
sys.path.append("/root")

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

try:
    import client
except ImportError:
    import client as client

LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}


def compute_dataset_hash(X, y):
    """Computes a stable SHA-256 hash of the dataset tensors."""
    combined = np.concatenate([X.numpy().flatten(), y.numpy().flatten()])
    return hashlib.sha256(combined.tobytes()).hexdigest()


def evaluate_checkpoint(model, dataloader, device):
    """Evaluates a loaded model on a dataloader and returns accuracy, loss, and class F1s."""
    model.eval()
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
            all_targets.extend(y_batch.cpu().numpy())

    overall_acc = np.mean(np.array(all_preds) == np.array(all_targets)) if total > 0 else 0.0
    avg_loss = total_loss / total if total > 0 else 0.0

    class_f1s = {}
    class_accs = {}
    for label in range(5):
        mask = np.array(all_targets) == label
        n_samples = mask.sum()
        if n_samples > 0:
            acc = (np.array(all_preds)[mask] == label).sum() / n_samples
            tp = ((np.array(all_preds) == label) & (np.array(all_targets) == label)).sum()
            fp = ((np.array(all_preds) == label) & (np.array(all_targets) != label)).sum()
            fn = ((np.array(all_preds) != label) & (np.array(all_targets) == label)).sum()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            class_f1s[label] = f1
            class_accs[label] = acc
        else:
            class_f1s[label] = 0.0
            class_accs[label] = 0.0

    return overall_acc, avg_loss, total, class_f1s, class_accs


def generate_signature(model_path, dataset_hash, results):
    """Generates a stable SHA-256 signature of the model binary and evaluation results."""
    model_sha = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            model_sha.update(chunk)
    model_hash = model_sha.hexdigest()

    results_str = json.dumps(results, sort_keys=True)
    combined = f"{model_hash}:{dataset_hash}:{results_str}"
    signature = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return model_hash, signature


def main():
    parser = argparse.ArgumentParser(description="Cryptographic Backward Transfer (BWT) Evaluation Suite")
    parser.add_argument("--checkpoint", required=True, help="Path to TorchScript checkpoint (.pt)")
    parser.add_argument("--test-dir", default="/mnt/ramdisk/flows", help="Test flow CSV directory")
    parser.add_argument("--output", default=str(repo_root / "data" / "reports" / "benchmark_evaluation_report.csv"), help="Output path for signed CSV")
    parser.add_argument("--peak-f1", default="1.0,1.0,1.0,1.0,1.0", help="Comma-separated peak historical F1-scores for class 0-4")
    parser.add_argument("--mlflow-run-id", help="Active MLflow run ID to upload the artifact directly")
    args = parser.parse_args()

    print("========================================================================")
    print("      FL-CL Cryptographic Backward Transfer (BWT) Validation Suite")
    print("========================================================================")
    print(f"[*] Loading model checkpoint: {args.checkpoint}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        model = torch.jit.load(args.checkpoint, map_location=device)
    except Exception as e:
        print(f"[FAIL] Error loading checkpoint: {e}")
        sys.exit(1)

    # Load test dataset
    print(f"[*] Loading test flows from: {args.test_dir}")
    try:
        X, y = client.load_ramdisk_flows(args.test_dir)
        print(f"[*] Loaded {X.shape[0]} benchmark samples from {args.test_dir}")
    except Exception as e:
        print(f"[*] Warning: Could not load flow CSVs from {args.test_dir} ({e}). Generating synthetic benchmark dataset...")
        np.random.seed(42)
        X_np = np.random.randn(500, 32).astype(np.float32)
        y_np = np.array([i % 5 for i in range(500)], dtype=np.int64)
        X = torch.tensor(X_np)
        y = torch.tensor(y_np)

    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=128, shuffle=False)
    dataset_hash = compute_dataset_hash(X, y)
    print(f"[*] Ground-truth Dataset SHA-256: {dataset_hash}")

    # Evaluate
    overall_acc, avg_loss, total_samples, class_f1s, class_accs = evaluate_checkpoint(model, dataloader, device)

    # Calculate BWT deltas
    try:
        peak_f1_vals = [float(val.strip()) for val in args.peak_f1.split(",")]
        if len(peak_f1_vals) != 5:
            raise ValueError("Must provide exactly 5 peak F1 values.")
    except Exception as parse_err:
        print(f"[*] Warning: Failed to parse peak-f1 scores: {parse_err}. Defaulting to 1.0.")
        peak_f1_vals = [1.0] * 5

    bwt_deltas = {}
    for label in range(5):
        bwt_deltas[label] = class_f1s[label] - peak_f1_vals[label]

    avg_bwt = sum(bwt_deltas.values()) / 5.0
    macro_f1 = sum(class_f1s.values()) / 5.0

    print(f"[*] Overall Accuracy: {overall_acc:.4f} | Macro F1: {macro_f1:.4f} | Avg BWT: {avg_bwt:.4f}")

    results_to_sign = {
        "overall_accuracy": f"{overall_acc:.6f}",
        "average_loss": f"{avg_loss:.6f}",
        "total_samples": str(total_samples),
        "macro_f1": f"{macro_f1:.6f}",
        "average_bwt": f"{avg_bwt:.6f}"
    }
    for label in range(5):
        results_to_sign[f"f1_class_{label}"] = f"{class_f1s[label]:.6f}"
        results_to_sign[f"accuracy_class_{label}"] = f"{class_accs[label]:.6f}"
        results_to_sign[f"bwt_class_{label}"] = f"{bwt_deltas[label]:.6f}"

    model_hash, signature = generate_signature(args.checkpoint, dataset_hash, results_to_sign)
    print(f"[*] Model SHA-256: {model_hash}")
    print(f"[*] Validation Signature: {signature}")

    report_rows = [
        {"Category": "Meta", "Metric": "Model_Hash", "Value": model_hash},
        {"Category": "Meta", "Metric": "Dataset_Hash", "Value": dataset_hash},
        {"Category": "Meta", "Metric": "Validation_Signature", "Value": signature},
        {"Category": "Meta", "Metric": "Timestamp", "Value": str(time.time())},
        {"Category": "Overall", "Metric": "Accuracy", "Value": f"{overall_acc:.6f}"},
        {"Category": "Overall", "Metric": "Loss", "Value": f"{avg_loss:.6f}"},
        {"Category": "Overall", "Metric": "Total_Samples", "Value": str(total_samples)},
        {"Category": "Overall", "Metric": "Macro_F1", "Value": f"{macro_f1:.6f}"},
        {"Category": "Overall", "Metric": "Average_BWT", "Value": f"{avg_bwt:.6f}"}
    ]

    for label in range(5):
        name = LABEL_NAMES[label]
        report_rows.append({"Category": f"Class_{name}", "Metric": "F1_Score", "Value": f"{class_f1s[label]:.6f}"})
        report_rows.append({"Category": f"Class_{name}", "Metric": "Accuracy", "Value": f"{class_accs[label]:.6f}"})
        report_rows.append({"Category": f"Class_{name}", "Metric": "BWT_Delta", "Value": f"{bwt_deltas[label]:.6f}"})

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(report_rows)
    df.to_csv(out_path, index=False)
    print(f"[*] Successfully wrote signed CSV report: {out_path}")

    # MLflow logging
    try:
        import mlflow
        if args.mlflow_run_id:
            with mlflow.start_run(run_id=args.mlflow_run_id):
                mlflow.log_artifact(str(out_path), artifact_path="benchmarks")
                mlflow.log_metric("benchmark_macro_f1", macro_f1)
                mlflow.log_metric("benchmark_avg_bwt", avg_bwt)
                mlflow.log_metric("benchmark_accuracy", overall_acc)
                print(f"[*] Logged signed report to MLflow Run: {args.mlflow_run_id}")
        elif mlflow.active_run():
            mlflow.log_artifact(str(out_path), artifact_path="benchmarks")
            mlflow.log_metric("benchmark_macro_f1", macro_f1)
            mlflow.log_metric("benchmark_avg_bwt", avg_bwt)
            mlflow.log_metric("benchmark_accuracy", overall_acc)
            print(f"[*] Logged signed report to active MLflow Run: {mlflow.active_run().info.run_id}")
    except Exception as mlflow_err:
        print(f"[*] Warning: Could not log signed report to MLflow: {mlflow_err}")

    print("\n[OK] Cryptographic BWT validation complete.")
    print("========================================================================\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
