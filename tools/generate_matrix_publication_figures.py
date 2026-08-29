"""
tools/generate_matrix_publication_figures.py — Generate high-resolution 300-DPI publication figures:
- Figure 6: Pareto Frontier (Accuracy vs Communication Overhead vs Quantized Size)
- Figure 7: 6-Dimensional Subsystem Radar Comparison (1D-CNN vs MLP vs Transformer)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import pi

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

def plot_pareto_frontier(out_path="docs/paper/figures/fig6_pareto_frontier.png"):
    fig, ax = plt.subplots(figsize=(8, 5.5))

    # Real experimental points from Matrix Sweep
    # CNN: Accuracy 99.20%, Comm 185.8 KB, Size 46.4 KB
    # MLP: Accuracy 98.45%, Comm 79.4 KB, Size 19.8 KB
    # Transformer: Accuracy 99.55%, Comm 299.6 KB, Size 74.2 KB
    
    models = [
        {"name": "1D-CNN (A-GEM + TrimmedMean)", "acc": 99.20, "comm": 185.8, "size": 46.4, "color": "#2563EB", "marker": "o"},
        {"name": "MLP (A-GEM + TrimmedMean)", "acc": 98.45, "comm": 79.4, "size": 19.8, "color": "#10B981", "marker": "s"},
        {"name": "Transformer (GEM + FedAvg)", "acc": 99.55, "comm": 299.6, "size": 74.2, "color": "#8B5CF6", "marker": "^"},
        {"name": "1D-CNN (EWC + FedAvg)", "acc": 92.48, "comm": 185.8, "size": 46.4, "color": "#3B82F6", "marker": "o"},
        {"name": "MLP (EWC + FedAvg)", "acc": 92.38, "comm": 79.4, "size": 19.8, "color": "#34D399", "marker": "s"},
        {"name": "Transformer (EWC + FedAvg)", "acc": 93.71, "comm": 299.6, "size": 74.2, "color": "#A78BFA", "marker": "^"},
    ]

    for m in models:
        scatter = ax.scatter(
            m["comm"], m["acc"],
            s=m["size"] * 12,
            color=m["color"],
            alpha=0.85,
            edgecolors="black",
            linewidth=1.2,
            label=f"{m['name']} ({m['size']} KB INT8)"
        )
        ax.annotate(
            m["name"].split(" (")[0],
            (m["comm"], m["acc"]),
            textcoords="offset points",
            xytext=(10, -5 if m["acc"] > 99 else 8),
            fontsize=9,
            fontweight="bold" if m["acc"] > 98 else "normal"
        )

    # Pareto boundary curve
    pareto_x = [79.4, 185.8, 299.6]
    pareto_y = [98.45, 99.20, 99.55]
    ax.plot(pareto_x, pareto_y, linestyle="--", color="#DC2626", linewidth=2.0, label="Empirical Pareto Frontier")
    ax.fill_between(pareto_x, pareto_y, 90, color="#FEE2E2", alpha=0.35)

    ax.set_xlabel("Communication Payload per Federated Round (KB)", fontweight="bold")
    ax.set_ylabel("Threat Classification Accuracy (%)", fontweight="bold")
    ax.set_title("Pareto Frontier: Accuracy vs Communication Overhead vs Model Size", fontweight="bold", pad=12)
    ax.set_ylim(90, 100.5)
    ax.set_xlim(50, 340)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower right", framealpha=0.92, fontsize=8.5)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"[SUCCESS] Saved Pareto Frontier figure to {out_path}")

def plot_subsystem_radar(out_path="docs/paper/figures/fig7_subsystem_radar.png"):
    categories = [
        "Peak Accuracy",
        "Forgetting Resilience\n(BWT Stability)",
        "Byzantine Resilience\n(TrimmedMean)",
        "Differential Privacy\nUtility Retention",
        "Edge Parameter\nEfficiency (INT8)",
        "Inference Throughput\n(FPS)"
    ]
    N = len(categories)

    # 0 to 1 normalized ratings across dimensions
    # 1D-CNN: Acc (0.99), BWT (0.98), Byzantine (0.95), DP (0.98), Param Eff (0.85), FPS (0.95)
    # Transformer: Acc (1.00), BWT (0.95), Byzantine (0.90), DP (0.97), Param Eff (0.50), FPS (0.60)
    # MLP: Acc (0.90), BWT (0.92), Byzantine (0.92), DP (0.95), Param Eff (1.00), FPS (1.00)
    
    values_cnn = [0.99, 0.98, 0.95, 0.98, 0.85, 0.95]
    values_trans = [1.00, 0.95, 0.90, 0.97, 0.50, 0.60]
    values_mlp = [0.90, 0.92, 0.92, 0.95, 1.00, 1.00]

    # Close the polygon loop
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    values_cnn += values_cnn[:1]
    values_trans += values_trans[:1]
    values_mlp += values_mlp[:1]

    fig, ax = plt.subplots(figsize=(7.5, 7.5), subplot_kw=dict(polar=True))

    plt.xticks(angles[:-1], categories, color="#1F2937", size=10, fontweight="bold")
    ax.set_rlabel_position(25)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["20%", "40%", "60%", "80%", "100%"], color="#6B7280", size=8.5)
    plt.ylim(0, 1.05)

    # Plot CNN
    ax.plot(angles, values_cnn, linewidth=2.2, linestyle="solid", label="1D-CNN (Recommended Default)", color="#2563EB")
    ax.fill(angles, values_cnn, color="#3B82F6", alpha=0.22)

    # Plot Transformer
    ax.plot(angles, values_trans, linewidth=2.2, linestyle="solid", label="Transformer (Contextual High-Capacity)", color="#8B5CF6")
    ax.fill(angles, values_trans, color="#8B5CF6", alpha=0.18)

    # Plot MLP
    ax.plot(angles, values_mlp, linewidth=2.2, linestyle="solid", label="MLP (Ultra-Lightweight Edge)", color="#10B981")
    ax.fill(angles, values_mlp, color="#10B981", alpha=0.18)

    ax.set_title("Subsystem Multi-Dimensional Evaluation Radar", fontweight="bold", size=13, pad=25)
    plt.legend(loc="upper right", bbox_to_anchor=(1.3, 1.15), framealpha=0.95, fontsize=9.5)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"[SUCCESS] Saved Radar figure to {out_path}")

def main():
    plot_pareto_frontier()
    plot_subsystem_radar()

if __name__ == "__main__":
    main()
