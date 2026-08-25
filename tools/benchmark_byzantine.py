"""
benchmark_byzantine.py — Multi-Aggregator Byzantine Robustness Benchmark

Benchmarks FedAvg, TrimmedMean, FedMedian, Krum, MultiKrum, and Bulyan across:
1. Clean federated baseline
2. 20% Label Flip Attack (Byzantine Client B)
3. 40% Coordinated Multi-Client Label Flip Attack
4. Gaussian Gradient Poisoning Attack (variance = 1.0)
"""

import sys
import os
import copy
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "defender"))
from model import get_model

REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_threat_data(n_samples=2500, input_dim=32):
    probs = [0.75, 0.04, 0.11, 0.05, 0.05]
    y = np.random.choice(5, size=n_samples, p=probs)
    centers = {
        0: np.zeros(input_dim),
        1: np.array([2.5 if i % 2 == 0 else -1.5 for i in range(input_dim)]),
        2: np.array([-2.0 if i % 3 == 0 else 1.8 for i in range(input_dim)]),
        3: np.array([3.0 if i < 16 else -2.0 for i in range(input_dim)]),
        4: np.array([4.0 if i % 4 == 0 else 0.5 for i in range(input_dim)])
    }
    X = np.zeros((n_samples, input_dim), dtype=np.float32)
    for i in range(n_samples):
        c = y[i]
        X[i] = centers[c] + np.random.randn(input_dim).astype(np.float32) * 0.75
    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.int64)


def aggregate_weights(weights_list, strategy="FedAvg", beta=0.1):
    n = len(weights_list)
    if strategy == "FedAvg":
        ndarrays = []
        for l in range(len(weights_list[0])):
            stacked = np.stack([w[l] for w in weights_list], axis=0)
            ndarrays.append(np.mean(stacked, axis=0))
        return ndarrays

    elif strategy == "FedMedian":
        ndarrays = []
        for l in range(len(weights_list[0])):
            stacked = np.stack([w[l] for w in weights_list], axis=0)
            ndarrays.append(np.median(stacked, axis=0))
        return ndarrays

    elif strategy == "TrimmedMean":
        k = int(np.floor(beta * n))
        ndarrays = []
        for l in range(len(weights_list[0])):
            stacked = np.stack([w[l] for w in weights_list], axis=0)
            sorted_stacked = np.sort(stacked, axis=0)
            if k > 0 and 2 * k < n:
                trimmed = sorted_stacked[k:-k]
            else:
                trimmed = sorted_stacked
            ndarrays.append(np.mean(trimmed, axis=0))
        return ndarrays

    elif strategy == "Krum":
        f = max(0, int((n - 3) / 2))
        flat_weights = [np.concatenate([arr.flatten() for arr in w]) for w in weights_list]
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i, j] = np.linalg.norm(flat_weights[i] - flat_weights[j])
        scores = []
        for i in range(n):
            sorted_dists = np.sort(distances[i])
            num_neighbors = max(1, n - f - 1)
            scores.append(np.sum(sorted_dists[1:num_neighbors]))
        best_idx = int(np.argmin(scores))
        return weights_list[best_idx]

    elif strategy == "MultiKrum":
        f = max(0, int((n - 3) / 2))
        flat_weights = [np.concatenate([arr.flatten() for arr in w]) for w in weights_list]
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i, j] = np.linalg.norm(flat_weights[i] - flat_weights[j])
        scores = []
        for i in range(n):
            sorted_dists = np.sort(distances[i])
            num_neighbors = max(1, n - f - 1)
            scores.append(np.sum(sorted_dists[1:num_neighbors]))
        m = max(1, n - f)
        top_m_indices = np.argsort(scores)[:m]
        selected_weights = [weights_list[idx] for idx in top_m_indices]
        ndarrays = []
        for l in range(len(weights_list[0])):
            stacked = np.stack([w[l] for w in selected_weights], axis=0)
            ndarrays.append(np.mean(stacked, axis=0))
        return ndarrays

    elif strategy == "Bulyan":
        f = max(0, int((n - 3) / 2))
        flat_weights = [np.concatenate([arr.flatten() for arr in w]) for w in weights_list]
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i, j] = np.linalg.norm(flat_weights[i] - flat_weights[j])
        scores = []
        for i in range(n):
            sorted_dists = np.sort(distances[i])
            num_neighbors = max(1, n - f - 1)
            scores.append(np.sum(sorted_dists[1:num_neighbors]))
        theta = max(1, n - 2 * f)
        selected_indices = np.argsort(scores)[:theta]
        selected_weights = [weights_list[idx] for idx in selected_indices]
        ndarrays = []
        for l in range(len(weights_list[0])):
            stacked = np.stack([w[l] for w in selected_weights], axis=0)
            sorted_stacked = np.sort(stacked, axis=0)
            k_trim = max(0, int(np.floor(0.1 * len(selected_weights))))
            if k_trim > 0 and 2 * k_trim < len(selected_weights):
                trimmed = sorted_stacked[k_trim:-k_trim]
            else:
                trimmed = sorted_stacked
            ndarrays.append(np.mean(trimmed, axis=0))
        return ndarrays

    return weights_list[0]


def run_benchmark():
    print("========================================================================")
    print("      FL-CL Byzantine-Robust Aggregators Comparative Benchmark")
    print("========================================================================")

    np.random.seed(42)
    torch.manual_seed(42)

    num_clients = 5
    num_rounds = 5
    input_dim = 32
    num_classes = 5

    X_val, y_val = generate_threat_data(n_samples=1000, input_dim=input_dim)
    val_targets = y_val.numpy()

    strategies = ["FedAvg", "TrimmedMean", "FedMedian", "Krum", "MultiKrum", "Bulyan"]
    scenarios = [
        ("Clean", 0, "none"),
        ("20% Label Flip (1 Attacker)", 1, "label_flip"),
        ("40% Label Flip (2 Attackers)", 2, "label_flip"),
        ("Gaussian Noise (1 Attacker)", 1, "gaussian_noise")
    ]

    results = []

    for scen_name, num_malicious, attack_type in scenarios:
        print(f"\n[*] Evaluating Scenario: {scen_name} (Malicious Clients: {num_malicious}/{num_clients})...")

        for strat in strategies:
            # Initialize global model
            global_model = get_model("cnn", input_dim=input_dim, num_classes=num_classes)
            
            for r in range(num_rounds):
                client_weights = []
                for cid in range(num_clients):
                    # Copy global weights
                    local_model = get_model("cnn", input_dim=input_dim, num_classes=num_classes)
                    local_model.load_state_dict(global_model.state_dict())
                    
                    # Generate client training data
                    X_c, y_c = generate_threat_data(n_samples=400, input_dim=input_dim)
                    
                    # Apply attack if client is malicious
                    if cid < num_malicious:
                        if attack_type == "label_flip":
                            # Flip Botnet (1) -> Normal (0)
                            y_c = torch.where(y_c == 1, torch.zeros_like(y_c), y_c)
                        elif attack_type == "gaussian_noise":
                            # Inject large Gaussian noise to gradients
                            pass

                    # Local training
                    optimizer = torch.optim.SGD(local_model.parameters(), lr=0.02)
                    criterion = nn.CrossEntropyLoss()
                    loader = DataLoader(TensorDataset(X_c, y_c), batch_size=32, shuffle=True)
                    
                    local_model.train()
                    for bx, by in loader:
                        optimizer.zero_grad()
                        out = local_model(bx)
                        loss = criterion(out, by)
                        loss.backward()
                        if cid < num_malicious and attack_type == "gaussian_noise":
                            for p in local_model.parameters():
                                if p.grad is not None:
                                    p.grad.add_(torch.randn_like(p.grad) * 2.0)
                        optimizer.step()

                    c_ndarrays = [p.detach().cpu().numpy() for p in local_model.parameters()]
                    client_weights.append(c_ndarrays)

                # Aggregate
                agg_ndarrays = aggregate_weights(client_weights, strategy=strat, beta=0.2)
                
                # Update global model
                with torch.no_grad():
                    for p, arr in zip(global_model.parameters(), agg_ndarrays):
                        p.copy_(torch.tensor(arr))

            # Evaluate global model on clean validation set
            global_model.eval()
            with torch.no_grad():
                preds = global_model(X_val).argmax(dim=1).numpy()

            acc = accuracy_score(val_targets, preds) * 100.0
            macro_f1 = f1_score(val_targets, preds, average="macro", zero_division=0)
            f1_per_class = f1_score(val_targets, preds, average=None, zero_division=0)
            botnet_f1 = f1_per_class[1] if len(f1_per_class) > 1 else 0.0

            res = {
                "scenario": scen_name,
                "strategy": strat,
                "val_accuracy": round(acc, 2),
                "macro_f1": round(macro_f1, 4),
                "botnet_f1": round(botnet_f1, 4),
                "normal_f1": round(f1_per_class[0], 4),
                "exfil_f1": round(f1_per_class[2], 4)
            }
            results.append(res)
            print(f"  [{strat:12s}] Acc: {acc:6.2f}% | Macro F1: {macro_f1:.4f} | Botnet F1: {botnet_f1:.4f}")

    df = pd.DataFrame(results)
    out_csv = REPORTS_DIR / "byzantine_robustness_benchmark.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[OK] Saved Byzantine robustness benchmark to: {out_csv}")
    print("========================================================================\n")


if __name__ == "__main__":
    run_benchmark()
