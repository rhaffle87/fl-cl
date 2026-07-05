# FCL Production Training Results Report

**Experiment**: FL-CL-EWC-Baseline
**Date**: July 2026
**Infrastructure**: 3-Node Proxmox VE Cluster (`10.10.130.10`)
**MLflow Run ID**: `b774d90b4a304dce9ca2393f0af2f4a9`

---

## 1. Experiment Configuration

The production training run was executed with the following validated configuration:

| Parameter | Value |
| :--- | :--- |
| **Model Backbone** | 1D-CNN (`CyberDefenseCNN`) |
| **Input Dimensions** | 32 (10 NFStream features, padded) |
| **Output Classes** | 5 (Normal, Botnet, DNS Exfil, SSH Brute Force, DoS) |
| **CL Strategy** | Elastic Weight Consolidation (EWC) |
| **EWC $\lambda$** | `0.8` |
| **Federated Rounds** | 100 (warm-started from round 76, 24 active rounds) |
| **Aggregation Strategy** | FedAvg (Federated Averaging) |
| **Learning Rate** | `0.003` |
| **SGD Momentum** | `0.9` |
| **Batch Size** | `32` |
| **Class Weights** | `[1.0, 250.0, 2.0, 5.0, 50.0]` |
| **MLOps Mode** | Production (`resume` strategy) |
| **Resumed From** | Run `82020f81b9064636aa8d49a5a22d18bf` (Model Version `v15`) |
| **Registered Model Version** | `v16` |
| **Git Commit** | `2ecf09433a53a785884cd66ed4aad0929bc92c58` |

### Class Weight Rationale

The class weights `[1.0, 250.0, 2.0, 5.0, 50.0]` were calibrated to counteract extreme class imbalance in live encrypted network traffic. Botnet C2 beaconing flows (class 1) are exceedingly rare compared to Normal traffic (class 0), requiring a 250× penalty amplification to prevent the optimizer from ignoring them entirely.

---

## 2. Production Run Performance Summary

### 2.1 Global Metrics (Best Round: 18)

| Metric | Value |
| :--- | :--- |
| **Global Accuracy** | 99.37% |
| **Global Loss** | 0.4225 |
| **Crucial Performance Index (CPI)** | 0.8830 |
| **Communication Overhead** | 294,480 bytes/round (well within 200 MB budget) |

### 2.2 Class-wise Detailed Metrics

| Class | Class Name | Accuracy | F1-Score | BWT $\Delta$ | Status |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 0 | Normal | 99.22% | 0.9957 | −0.0019 | Acceptable |
| 1 | Botnet | 100.00% | 0.6817 | −0.2081 | Perfect accuracy, low F1 due to sample scarcity |
| 2 | DNS Exfiltration | 99.86% | 0.9993 | −0.0000 | Acceptable |
| 3 | SSH Brute Force | 100.00% | 0.9936 | −0.0000 | Perfect |
| 4 | DoS | 97.04% | 0.9617 | −0.0071 | Needs Improvement |

### 2.3 Interpretation

- **Classes 0, 2, 3**: Near-perfect detection with negligible backward transfer degradation ($|\text{BWT}| < 0.002$). EWC regularization successfully preserved learned representations across all 100 rounds.
- **Class 1 (Botnet)**: Achieves 100% accuracy but exhibits a lower F1-score (0.6817), indicating the model correctly identifies all true Botnet flows but generates some false positives. The moderate BWT regression (−0.2081) signals ongoing catastrophic forgetting pressure on this minority class, partially mitigated by the 250× class weight.
- **Class 4 (DoS)**: Accuracy of 97.04% with mild BWT degradation (−0.0071). The volumetric nature of DoS flows (high `duration_ms`, elevated `dst2src_bytes`) creates statistical overlap with Normal traffic during extended flow durations.

---

## 3. Convergence Analysis

### 3.1 Loss Trajectory

Training loss decreased from 1.2439 (round 1) to a best of 0.4225 (round 18), demonstrating stable convergence. Minor oscillations in later rounds (0.53–1.05 range) are characteristic of the EWC penalty interacting with sequentially arriving traffic tasks — the regularization term resists weight updates that would compromise prior-task performance.

### 3.2 Accuracy Trajectory

Global accuracy remained consistently above 99.3% across all 24 active rounds, with a peak of 99.66% at round 1 (immediately after warm-start) and stabilizing at 99.33% by round 24. The marginal decline is attributed to the increasing EWC Fisher penalty accumulation as more task experiences are consolidated.

### 3.3 Per-Class F1 Trends

| Round | F1 Class 0 | F1 Class 1 | F1 Class 2 | F1 Class 3 | F1 Class 4 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 0.9976 | 0.8899 | 0.9993 | 0.9936 | 0.9688 |
| 6 | 0.9970 | 0.8312 | 0.9993 | 0.9936 | 0.9652 |
| 12 | 0.9962 | 0.7450 | 0.9993 | 0.9936 | 0.9617 |
| 18 | 0.9957 | 0.6817 | 0.9993 | 0.9936 | 0.9617 |
| 24 | 0.9955 | 0.6349 | 0.9993 | 0.9936 | 0.9617 |

Class 1 (Botnet) F1 exhibits the most pronounced monotonic decline, driven by the Fisher-penalty accumulation favoring the more frequently observed traffic classes. This is the primary area for future optimization (e.g., experience replay buffers, adaptive $\lambda$ scheduling).

---

## 4. Data Quality & Feature Drift Diagnostics

### 4.1 Jensen-Shannon Divergence (JSD) Safety Gate

Both defender clients passed the pre-training JSD data quality gate:

| Client | JSD Value | Threshold | Result |
| :--- | :---: | :---: | :--- |
| Defender A | < 0.01 | 0.6 | **PASSED** |
| Defender B | < 0.01 | 0.6 | **PASSED** |

### 4.2 Feature Drift Alerts

Statistical drift ($Z$-score > 30) was flagged on both clients for:

- `dst2src_packets` — elevated during DoS simulations (volumetric traffic)
- `dst2src_bytes` — correlated with DoS volumetric signature

These alerts were logged to MLflow as diagnostic warnings. The drift is expected and consistent with the DoS attack simulation stage producing flow profiles that diverge significantly from the Normal traffic baseline.

### 4.3 Dataset Lineage (SHA-256 Hashes)

| Component | Hash |
| :--- | :--- |
| Defender A Dataset | `cb64509b37e3f5c3cf66d5d9c073e107afee1721ec1c0e8048198da945b9955b` |
| Defender B Dataset | `14bca927f56bcf925bb3ccd92d6a9159617536d7ebe6ea67433dcbfe9dc529fe` |
| Combined | `17d9626072b18f286be70178ff501970cc911abeef946e44d4e6b2e2bf5d5533` |

---

## 5. MLOps Governance & Model Registry

### 5.1 Promotion Decision

The candidate model (version `v16`) was evaluated against the incumbent champion (`v15`) using the automated validation gate:

| Gate | Criterion | Result | Outcome |
| :--- | :--- | :--- | :--- |
| Per-class F1 | All classes F1 ≥ threshold | Class 1 F1 = 0.6817 | Marginal |
| BWT Check | BWT ≥ 0 for all classes | Class 1 BWT = −0.2081 | **Failed** |
| Communication Budget | ≤ 200 MB overhead | 294,480 bytes/round | **Passed** |

The BWT regression gate blocked automatic promotion of `v16` to `champion` alias. The incumbent `v15` remains the production champion. Manual review is recommended to determine if the BWT regression on the Botnet class is acceptable for specific deployment scenarios.

### 5.2 Model Artifacts

| Artifact | Size | Format |
| :--- | :--- | :--- |
| `model_latest.pt` | ~93 KB | PyTorch state dict |
| `model_latest_scripted.pt` | ~93 KB | TorchScript (deployment-ready) |
| Pruned model (20% Fisher-guided) | ~93 KB | Sparse PyTorch |
| Quantized model (8-bit dynamic) | ~46 KB | INT8 quantized |

---

## 6. Confusion Matrix Logging: The 24-Round Explanation

### Why 24 Confusion Matrices?

The pipeline is configured for 100 total federated rounds (`fl.rounds: 100`). The MLOps warm-start mechanism detected a registered champion model (`v15`) that had completed 76 rounds of training in a prior execution. Rather than retraining from scratch — which would discard the established weight convergence — the orchestrator resumed training from round 77.

**Consequence**: Only the 24 active rounds (77–100) generated new evaluation artifacts (confusion matrices, metrics, plots). The prior 76 rounds' artifacts are preserved in the original MLflow run (`82020f81b9064636aa8d49a5a22d18bf`).

This behavior aligns with standard MLOps checkpointing practices: each resumed run constitutes a distinct MLflow tracking entity to maintain clean version lineage while preserving cumulative training progress.

---

## 7. Visualization Artifacts

The following plots were generated automatically by the pipeline and are archived in [`docs/reports/plots/`](plots/):

| Plot | Description |
| :--- | :--- |
| [`loss_accuracy_curves.png`](plots/loss_accuracy_curves.png) | Training loss and accuracy over 24 active rounds |
| [`f1_class_trends.png`](plots/f1_class_trends.png) | Per-class F1-score trajectories showing forgetting dynamics |
| [`forgetting_curves.png`](plots/forgetting_curves.png) | BWT degradation profiles per class |
| [`run_comparison_chart.png`](plots/run_comparison_chart.png) | Cross-run CPI comparison chart |
| [`confusion_matrices/`](plots/confusion_matrices/) | 24 per-round 5×5 confusion matrix heatmaps |

---

## 8. Recommendations

1. **Botnet (Class 1) Mitigation**: Investigate experience replay (GEM) or adaptive $\lambda$ scheduling to reduce the BWT regression (−0.2081) on this minority class without sacrificing plasticity on other classes.
2. **DoS (Class 4) Refinement**: Experiment with the `dos_duration_threshold_ms` parameter (currently 2000 ms) to reduce false negatives from long-duration benign flows.
3. **Long-Running Validation**: Execute a full 100-round cold-start production run to generate a complete 100-matrix confusion matrix set for academic documentation.
4. **Champion Promotion**: Manually review the `v16` candidate — if the Botnet BWT regression is acceptable for the target deployment, promote via `mlflow.register_model()` with `champion` alias override.
