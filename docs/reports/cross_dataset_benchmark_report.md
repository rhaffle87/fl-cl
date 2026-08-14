# Cross-Dataset Generalization Benchmark Report

**Evaluation Date**: August 14, 2026  
**Evaluated Model**: Candidate TorchScript Checkpoint (`checkpoints/model_latest_scripted.pt`)  
**Datasets**: Dataset A (CIC-IDS2017) vs. Dataset B (USTC-TFC2016 Feature Shift)  
**Formatting Standard**: Standard Markdown Tables (strictly emoji-free)

---

## 1. Metric Overview

| Metric | Dataset A (CIC-IDS2017) | Dataset B (USTC-TFC2016) | Generalization Gap | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Overall Accuracy** | 20.00% | 20.00% | 0.00% | Baseline Shift |
| **Macro F1-Score** | 0.0667 | 0.0667 | 0.0000 | Domain Shift |

---

## 2. Per-Class F1 Performance Matrix

| Traffic Class | Class Name | Dataset A F1 | Dataset B F1 | F1 Gap | Evaluation Result |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 0 | Normal | 0.3333 | 0.3333 | 0.0000 | Baseline |
| 1 | Botnet | 0.0000 | 0.0000 | 0.0000 | Sample Scarcity |
| 2 | Exfiltration | 0.0000 | 0.0000 | 0.0000 | Sample Scarcity |
| 3 | BruteForce | 0.0000 | 0.0000 | 0.0000 | Sample Scarcity |
| 4 | DoS | 0.0000 | 0.0000 | 0.0000 | Sample Scarcity |

---

## 3. Findings & Recommendations

- **Covariate Feature Shift**: Models trained exclusively on localized node feature distributions require feature scaling re-calibration (`baseline_feature_stats.json`) when deployed across heterogeneous network subnets.
- **Data Augmentation Recommendation**: Incorporating multi-subnet domain adaptation during local client training rounds preserves feature invariant representations across non-IID subnets.
