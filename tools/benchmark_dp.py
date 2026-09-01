# benchmark_dp.py — Differential Privacy Noise Sensitivity Curve Suite
#
# Evaluates model convergence, loss, and per-class F1 score retention under varying
# client DP noise multipliers (sigma in [0.0, 0.01, 0.05, 0.10, 0.20]) and max grad norm 1.0.

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "defender"))

from model import get_model

REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_synthetic_threat_stream(n_samples=2000, input_dim=32):
    # Class distribution: 0: 75% (Normal), 1: 3% (Botnet), 2: 12% (Exfil), 3: 5% (BruteForce), 4: 5% (DoS)
    probs = [0.75, 0.03, 0.12, 0.05, 0.05]
    y = np.random.choice(5, size=n_samples, p=probs)

    # Class centroids with realistic cluster separation
    centers = {
        0: np.zeros(input_dim),
        1: np.array([2.5 if i % 2 == 0 else -1.5 for i in range(input_dim)]),
        2: np.array([-2.0 if i % 3 == 0 else 1.8 for i in range(input_dim)]),
        3: np.array([3.0 if i < 16 else -2.0 for i in range(input_dim)]),
        4: np.array([4.0 if i % 4 == 0 else 0.5 for i in range(input_dim)]),
    }

    X = np.zeros((n_samples, input_dim), dtype=np.float32)
    for i in range(n_samples):
        c = y[i]
        noise = np.random.randn(input_dim).astype(np.float32) * 0.8
        X[i] = centers[c] + noise

    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.int64)


def evaluate_dp_curve():
    print("========================================================================")
    print("       FL-CL Differential Privacy Sensitivity Benchmark Suite")
    print("========================================================================")

    noise_multipliers = [0.0, 0.01, 0.05, 0.10, 0.20]
    device = torch.device("cpu")
    input_dim = 32
    num_classes = 5

    X_train, y_train = generate_synthetic_threat_stream(
        n_samples=3000, input_dim=input_dim
    )
    X_val, y_val = generate_synthetic_threat_stream(n_samples=1000, input_dim=input_dim)

    train_ds = TensorDataset(X_train, y_train)
    val_ds = TensorDataset(X_val, y_val)
    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)

    results = []

    for sigma in noise_multipliers:
        print(
            f"\n[*] Evaluating DP Noise Multiplier sigma = {sigma:.2f} (max_grad_norm=1.0)..."
        )
        torch.manual_seed(42)
        np.random.seed(42)

        model = get_model("cnn", input_dim=input_dim, num_classes=num_classes)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
        criterion = nn.CrossEntropyLoss()

        epochs = 5
        train_loss = 0.0

        for epoch in range(epochs):
            model.train()
            running_loss = 0.0
            for bx, by in train_loader:
                optimizer.zero_grad()
                out = model(bx)
                loss = criterion(out, by)
                loss.backward()

                # DP Gradient Clipping and Noise Injection
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                if sigma > 0.0:
                    noise_std = (sigma * 1.0) / 32
                    for p in model.parameters():
                        if p.grad is not None:
                            noise = torch.randn_like(p.grad) * noise_std
                            p.grad.add_(noise)

                optimizer.step()
                running_loss += loss.item() * len(by)

            train_loss = running_loss / len(train_ds)

        # Evaluate on validation dataset
        model.eval()
        with torch.no_grad():
            val_preds = model(X_val).argmax(dim=1).numpy()
            val_targets = y_val.numpy()

        acc = accuracy_score(val_targets, val_preds)
        macro_f1 = f1_score(val_targets, val_preds, average="macro", zero_division=0)
        f1_per_class = f1_score(val_targets, val_preds, average=None, zero_division=0)

        # Calculate empirical privacy guarantee epsilon estimate (RDP approximation)
        # epsilon ~ sqrt(2 * log(1/delta) * q^2 * T) / sigma for small sigma
        q = 32 / len(train_ds)
        T = epochs * len(train_loader)
        if sigma > 0.0:
            delta = 1e-5
            eps_approx = np.sqrt(2 * np.log(1.0 / delta) * (q**2) * T) / sigma
            eps_val = round(float(eps_approx), 2)
        else:
            eps_val = "Infinity (No DP)"

        res = {
            "dp_noise_multiplier": sigma,
            "epsilon_approx_delta_1e5": eps_val,
            "final_train_loss": round(train_loss, 4),
            "val_accuracy": round(acc * 100, 2),
            "macro_f1": round(macro_f1, 4),
            "f1_normal_0": round(f1_per_class[0], 4),
            "f1_botnet_1": round(f1_per_class[1] if len(f1_per_class) > 1 else 0.0, 4),
            "f1_exfil_2": round(f1_per_class[2] if len(f1_per_class) > 2 else 0.0, 4),
            "f1_bruteforce_3": round(
                f1_per_class[3] if len(f1_per_class) > 3 else 0.0, 4
            ),
            "f1_dos_4": round(f1_per_class[4] if len(f1_per_class) > 4 else 0.0, 4),
        }
        results.append(res)

        print(
            f"  sigma = {sigma:4.2f} | Loss: {train_loss:.4f} | Accuracy: {acc*100:6.2f}% | "
            f"Macro F1: {macro_f1:.4f} | Botnet F1: {res['f1_botnet_1']:.4f}"
        )

    df = pd.DataFrame(results)
    out_csv = REPORTS_DIR / "privacy_utility_curve.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[OK] Saved privacy-utility curve to: {out_csv}")
    print("========================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Differential Privacy (DP-SGD) Sensitivity and Epsilon Sweeper"
    )
    _ = parser.parse_args()
    evaluate_dp_curve()
