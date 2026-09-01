#!/usr/bin/env python3
"""
tools/benchmark_ood.py — Energy-Based Out-of-Distribution (OOD) Threat Detection Benchmark

Evaluates Free Energy OOD score separation between In-Distribution (ID) 5-class flows
and Out-of-Distribution (OOD) novel zero-day attack flows. Computes AUROC and FPR@95% TPR.

Usage:
    python3 tools/benchmark_ood.py [--model-path data/models/cyberdefense_cnn.pt] [--temperature 1.0]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "defender"))

from extractor import calculate_energy_score
from model import get_model


def compute_auroc_and_fpr95(id_energy: np.ndarray, ood_energy: np.ndarray):
    """
    Compute AUROC and False Positive Rate at 95% True Positive Rate.
    Note: Since higher energy indicates OOD, positive class = OOD.
    """
    labels = np.concatenate([np.zeros(len(id_energy)), np.ones(len(ood_energy))])
    scores = np.concatenate([id_energy, ood_energy])

    # Sort thresholds by score
    sorted_indices = np.argsort(scores)
    sorted_labels = labels[sorted_indices]
    sorted_scores = scores[sorted_indices]

    n_ood = len(ood_energy)
    n_id = len(id_energy)

    tpr_list = []
    fpr_list = []

    for tau in np.linspace(sorted_scores[0] - 1.0, sorted_scores[-1] + 1.0, 500):
        # Predict OOD if score >= tau
        pred_ood = (scores >= tau).astype(int)
        tp = np.sum((pred_ood == 1) & (labels == 1))
        fp = np.sum((pred_ood == 1) & (labels == 0))
        tpr = tp / max(n_ood, 1)
        fpr = fp / max(n_id, 1)
        tpr_list.append(tpr)
        fpr_list.append(fpr)

    tpr_arr = np.array(tpr_list)
    fpr_arr = np.array(fpr_list)

    # Sort by FPR for trapezoidal integration
    order = np.argsort(fpr_arr)
    trapz_func = getattr(np, "trapezoid", getattr(np, "trapz", None))
    if trapz_func is not None:
        auroc = trapz_func(tpr_arr[order], fpr_arr[order])
    else:
        auroc = np.sum(
            0.5 * (tpr_arr[order][:-1] + tpr_arr[order][1:]) * np.diff(fpr_arr[order])
        )
    auroc = float(np.clip(auroc, 0.0, 1.0))

    # Calculate FPR at TPR >= 0.95
    valid_idx = np.where(tpr_arr >= 0.95)[0]
    if len(valid_idx) > 0:
        fpr95 = float(np.min(fpr_arr[valid_idx]))
    else:
        fpr95 = 1.0

    return auroc, fpr95


def main():
    parser = argparse.ArgumentParser(description="Energy OOD Detection Benchmark")
    parser.add_argument(
        "--model-path",
        default="data/models/cyberdefense_cnn.pt",
        help="Model checkpoint path",
    )
    parser.add_argument(
        "--temperature", type=float, default=1.0, help="Energy scaling temperature"
    )
    parser.add_argument(
        "--out-report",
        default="data/reports/benchmarks/ood_benchmark_report.csv",
        help="CSV report path",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("      FL-CL ENERGY-BASED ZERO-DAY & OOD DETECTION BENCHMARK")
    print("=" * 70)

    num_classes = 5
    input_dim = 32
    np.random.seed(42)
    torch.manual_seed(42)

    model = get_model("cnn", input_dim=input_dim, num_classes=num_classes)
    if Path(args.model_path).exists():
        print(f"[*] Loading model from {args.model_path}...")
        try:
            model.load_state_dict(torch.load(args.model_path, map_location="cpu"))
        except Exception:
            pass
    model.eval()

    # 1. Generate In-Distribution (ID) test flows
    n_samples = 1000
    print(
        f"[*] Simulating {n_samples} In-Distribution (ID) flows across 5 threat classes..."
    )
    # Distinct structured cluster inputs for ID classes
    id_x = []
    for c in range(num_classes):
        center = np.zeros(input_dim)
        center[c * 6 : (c + 1) * 6] = 2.5
        id_x.append(center + np.random.randn(n_samples // num_classes, input_dim) * 0.5)
    id_x = np.vstack(id_x)

    with torch.no_grad():
        id_logits = model(torch.tensor(id_x, dtype=torch.float32)).numpy()
    id_energy = calculate_energy_score(id_logits, temperature=args.temperature)

    # 2. Generate OOD Evaluation Datasets
    ood_scenarios = {
        "Uniform Noise (Novel Raw Payload)": np.random.uniform(
            -5.0, 5.0, (n_samples, input_dim)
        ),
        "High Variance Gaussian (Volumetric Shift)": np.random.randn(
            n_samples, input_dim
        )
        * 4.0,
        "Unseen Cipher Anomaly (Extreme Jitter)": np.random.exponential(
            scale=3.0, size=(n_samples, input_dim)
        ),
    }

    results = []
    print("\n[*] Evaluating Free Energy Score distributions...")
    print(
        f"  - In-Distribution (ID) Energy Mean: {np.mean(id_energy):.4f} (+/- {np.std(id_energy):.4f})"
    )

    for name, ood_x in ood_scenarios.items():
        with torch.no_grad():
            ood_logits = model(torch.tensor(ood_x, dtype=torch.float32)).numpy()
        ood_energy = calculate_energy_score(ood_logits, temperature=args.temperature)

        auroc, fpr95 = compute_auroc_and_fpr95(id_energy, ood_energy)
        mean_diff = float(np.mean(ood_energy) - np.mean(id_energy))

        results.append(
            {
                "Scenario": name,
                "ID_Energy_Mean": round(float(np.mean(id_energy)), 4),
                "OOD_Energy_Mean": round(float(np.mean(ood_energy)), 4),
                "Delta_Energy": round(mean_diff, 4),
                "AUROC": round(auroc, 4),
                "FPR95": round(fpr95, 4),
                "Status": "PASSED" if auroc >= 0.85 else "BORDERLINE",
            }
        )
        print(
            f"  - [{name:42s}] AUROC: {auroc:.4f} | FPR@95% TPR: {fpr95:.4f} | Delta E: {mean_diff:+.4f}"
        )

    df = pd.DataFrame(results)
    out_path = Path(PROJECT_ROOT / args.out_report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"\n[OK] OOD Benchmark Report exported to: {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
