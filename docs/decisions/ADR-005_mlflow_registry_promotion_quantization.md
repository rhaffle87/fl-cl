# ADR-005: Automated CI/CD Model Promotion Gate, Backward Transfer Tracking, and INT8 Quantization

## Status
Accepted

## Date
2026-08-15

## Context
Deploying continual federated learning models to edge defense gateways without automated quality gates creates severe operational risks:
1. **Silent Catastrophic Regressions**: A newly trained global model might achieve high overall accuracy on dominant traffic (Normal/Exfiltration) while completely failing to detect rare zero-day threats (Botnet/BruteForce).
2. **Backward Transfer (BWT) Violations**: Newly trained rounds might cause negative backward transfer (catastrophic forgetting) on previously consolidated attack signatures.
3. **Edge Deployment Latency & Footprint**: Edge defenders need deployment-ready compiled graphs (TorchScript) and optimized low-precision formats (INT8 dynamic quantization) without external Python runtime dependencies.

## Decision
We establish an automated CI/CD validation gate and model registry promotion lifecycle in `tools/ci_cd_promote.py` and `src/orchestrate.py`:

### 1. Multi-Gate Promotion Pipeline
Candidate model versions registered as `challenger` in MLflow are transferred to an independent physical defender node and validated against held-out ramdisk flow datasets before promotion:

| Gate | Validation Metric | Pass Criterion | Rationale |
| :--- | :--- | :---: | :--- |
| **Gate 1: Per-Class F1** | Per-Class F1 Score | $\text{F1}_c \ge \text{Threshold}_c$ | Ensures minority classes (Botnet, DoS) meet strict precision/recall bounds (e.g. $\text{F1}_{\text{Botnet}} \ge 0.60$). |
| **Gate 2: Backward Transfer** | $\text{BWT}_c = R_{T, c} - R_{c, c}$ | $\text{BWT}_c \ge -0.20$ | Blocks models with catastrophic forgetting on previously learned threat stages. |
| **Gate 3: Network Budget** | Communication bytes/round | $\le 200\text{ MB}$ | Verifies FL parameter payload fits edge bandwidth limits. |

### 2. Multi-Backbone Production Aliases
Models meeting all gate criteria are promoted with explicit semantic aliases in `data/db/mlflow.db`:
- `champion`: Active cluster-wide production model (v35 / v29 Transformer).
- `champion-transformer`: High-precision self-attention model (v29, 99.63% accuracy, 0.0146 loss).
- `champion-cnn`: 1D-CNN temporal feature extractor (v26 / v35).
- `champion-mlp`: Ultra-lightweight MLP backbone (v30).

### 3. Automatic Export-Time Quantization & Compilation
Every validated candidate automatically produces:
1. `model_latest_scripted.pt`: Standalone TorchScript JIT artifact for C++ / LibTorch edge deployment.
2. `model_quantized.pt`: 8-bit dynamic INT8 quantized artifact (`torch.ao.quantization.quantize_dynamic`), reducing memory footprint by **50%** (from 93 KB to 46 KB).
3. Sparse Fisher Pruned Model: 20% Fisher-guided unstructured parameter pruning.

## Alternatives Considered

### 1. Manual Promotion via Human Review
- **Pros**: Subjective discretion.
- **Cons**: High latency (>hours); fails to scale across autonomous continuous learning loops; subjective bias allows silent regressions.
- **Rejected**: Fully automated mathematical gates ensure objective zero-regression guarantees.

### 2. Overall Accuracy Gate Only
- **Pros**: Simple scalar check ($\text{Acc} \ge 99\%$).
- **Cons**: Highly misleading on imbalanced IDS data. A model predicting 100% Normal and 0% Botnet still achieves 99.2% overall accuracy.
- **Rejected**: Per-class F1 and BWT checks are strictly mandatory.

## Consequences

### Positive
- **Zero Silent Failures**: Automated gate successfully caught and blocked candidate `v16` (BWT regression) and `v31` (dropout collapse) from reaching production.
- **Promoted Integrity**: Only robust models meeting all criteria (e.g., v35 under TrimmedMean, v29 Transformer) achieve the `champion` alias.
- **Immediate Edge Compatibility**: Edge inference loop (`inference_loop.py`) can hot-reload `model_latest_scripted.pt` dynamically on disk changes.

### Negative / Trade-offs
- Validation gate requires ~30–45 seconds of compute on a defender node immediately following FL training.
