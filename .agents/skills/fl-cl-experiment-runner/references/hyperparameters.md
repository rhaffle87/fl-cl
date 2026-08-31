# FL-CL Hyperparameter & Experiment Reference Guide

## 1. Validated Experiment Hyperparameters

The following configurations have been empirically tested and validated on the 3-node Proxmox testbed:

### Baseline (Cold Start, 100 Rounds)
- **File**: `configs/experiments/baseline_coldstart_100r.yaml`
- **Model**: `cnn` (`CyberDefenseCNN`)
- **Rounds**: `100`
- **Learning Rate**: `0.003`
- **CL Strategy**: `EWC` ($\lambda = 1.0$)
- **Aggregator**: `TrimmedMean` (beta = 0.2)
- **Top Accuracy**: `99.88%`
- **Weight Payload**: `294.5 KB / round`

### Differential Privacy (DP-SGD)
- **File**: `configs/experiments/dp_sgd.yaml`
- **DP Noise Multiplier ($\sigma$)**: `0.30`
- **Max Grad Norm ($C$)**: `1.0`
- **Target Delta ($\delta$)**: `1e-5`
- **Accuracy Retention**: `99.51%` (loss of < 0.3% vs clean baseline)

### Continual Learning Recovery (GEM)
- **File**: `configs/experiments/benchmark_gem_botnet.yaml`
- **CL Strategy**: `GEM`
- **Memory Strength**: `0.20`
- **Patterns per Experience**: `500`
- **Botnet Recall**: `100%` recovery after DoS/BruteForce drift

---

## 2. Loss Weight Formulation

For handling severe class imbalance (e.g. DNS Exfiltration and Botnet flows):

$$\text{Loss} = \sum_{c=0}^4 w_c \cdot \mathcal{L}_{CE}(y_c, \hat{y}_c)$$

Recommended `training.class_weights`:
- `[1.0, 15.0, 2.0, 4.0, 15.0]` (Normal: 1.0, Botnet: 15.0, Exfiltration: 2.0, BruteForce: 4.0, DoS: 15.0)
