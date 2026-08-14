# FCL Production Training & Benchmarking Results Report

**Execution Date**: August 14, 2026  
**Infrastructure**: 3-Node Physical Proxmox VE Cluster (`10.10.130.10`)  
**Git Commit**: `91eb7e1`  
**Formatting Standard**: Standard Markdown Tables (strictly emoji-free)

---

## 1. Executive Summary

This report documents the finalized empirical performance of the 5 core experiment series (`quick_test.yaml`, `baseline.yaml`, `dp_sgd.yaml`, `data_poisoning.yaml`, `robust_agg.yaml`) and the 4-tier benchmark suite (`benchmark_quick.yaml`, `benchmark_balanced.yaml`, `benchmark_stressed.yaml`, `benchmark_realworld.yaml`) executed directly on the physical 3-node Proxmox VE testbed (`10.10.130.10`).

| Parameter | Value |
| :--- | :--- |
| **Model Backbone** | 1D-CNN (`CyberDefenseCNN`) |
| **Input Dimensions** | 32 scaled ETA features |
| **Output Classes** | 5 (Normal, Botnet, DNS Exfil, SSH Brute Force, DoS) |
| **CL Strategy** | Elastic Weight Consolidation (EWC) |
| **EWC $\lambda$** | `0.8` – `2.0` |
| **Aggregation Strategies** | FedAvg & TrimmedMean ($\beta=0.1$) with Adaptive `FedMedian` Fallback |
| **Class Weights** | `[1.0, 15.0, 2.0, 4.0, 15.0]` |
| **Telegram Notifications** | Configured & Live Verified (`HTTP 200 OK`) |

---

## 2. Core Experiments Master Scorecard

| Experiment Config | FL Aggregation | Security & Privacy Settings | Server Acc | Val Acc | DoS F1 Score | Validation Gate | MLflow Version & CI/CD Action |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`quick_test.yaml`** | FedAvg | Clean Baseline | 99.59% | 99.48% | 0.9951 | [PASS] PASS | Promoted Version 19 (`champion`) |
| **`baseline.yaml`** | FedAvg | Clean Baseline | 99.72% | 99.64% | 0.9815 | [PASS] PASS | Promoted Version 20 (`champion`) |
| **`dp_sgd.yaml`** | FedAvg | DP ($\sigma=0.3$, Clip 5.0) | 99.51% | 99.59% | 0.9776 | [PASS] PASS | Promoted Version 21 (`champion`) |
| **`data_poisoning.yaml`** | FedAvg | 20% Defender A Poison | 92.45% | 99.69% | 0.9891 | [PASS] PASS | Promoted Version 22 (`champion`) |
| **`robust_agg.yaml`** | **TrimmedMean** ($\beta=0.1$) | 20% Defender A Poison | 92.31% | **99.64%** | **0.9675** | [PASS] PASS | **Promoted Version 23 (`champion`)** |

---

## 3. Automated 4-Tier Benchmark Suite Master Scorecard

| Benchmark Tier | Config File | Capture Window | FL Rounds | EWC $\lambda$ | Aggregation | Security / DP Settings | Val Acc | Validation Gate Result | MLflow Version |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tier 1 (Quick)** | `benchmark_quick.yaml` | 30s | 2 | 0.5 | FedAvg | Clean Baseline | **99.44%** | [PASS] PASS | Promoted Version 24 (`champion`) |
| **Tier 2 (Balanced)** | `benchmark_balanced.yaml` | 60s | 5 | 0.8 | FedAvg | Clean Baseline | 99.40% | [FAIL] FAIL | Candidate Version 25 (`challenger`) |
| **Tier 3 (Stressed)** | `benchmark_stressed.yaml` | 90s | 15 | 2.0 | FedAvg | Clean Baseline | **99.66%** | [PASS] PASS | Promoted Version 26 (`champion`) |
| **Tier 4 (Real-World)** | `benchmark_realworld.yaml` | 90s | 10 | 2.0 | TrimmedMean | DP ($\sigma=0.15$), 20% Poison | 78.30% | [FAIL] FAIL | Candidate Version 27 (`challenger`) |


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
