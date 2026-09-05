# Antigravity & Gemini Workspace Guide: FL-CL

Welcome! This document outlines key context, conventions, architecture details, and verification commands to help you navigate and develop inside the `fl-cl` repository.

---

## 0. Authoritative Research Scope & Anti-Scope-Creep Boundary

> [!IMPORTANT]
> **Mandatory Scope Gatekeeper**: All implementations, experiments, datasets, and refactorings must strictly conform to [`scope.md`](file:///e:/Projects/fl-cl/scope.md) and [`.agents/rules/scope.md`](file:///e:/Projects/fl-cl/.agents/rules/scope.md).
>
> * **The 4 Bounded Claims**:
>   - **C1: Forgetting Resistance**: Botnet $BWT$ recovery via class-weighted EWC ($\lambda=1.0$) and episodic memory GEM ($P=512$).
>   - **C2: Collaborative Privacy**: Parameter-only Flower FL exchange + batch DP-SGD ($\sigma=0.30, C=1.0$).
>   - **C3: Byzantine Robustness**: TrimmedMean ($\beta=0.1$) & FedMedian isolating up to 20% malicious label flipping.
>   - **C4: Encrypted Traffic Detection**: 32-dimensional NFStream flow metadata without payload decryption or DPI.
> * **Canonical 5-Class Threat Model**: `0: Normal`, `1: Botnet`, `2: Exfiltration`, `3: BruteForce`, `4: DoS`. Never modify or expand $C$ beyond 5.
> * **Explicit Non-Goals**: No open-ended generic multi-dataset data platforms, no payload decryption / DPI, no duplicate experiment orchestrators bypassing `src/orchestrate.py`.
> * **Decision Gate**: If a proposed change does not pass all 5 criteria in the Anti-Scope-Creep Decision Matrix ([`scope.md`](file:///e:/Projects/fl-cl/scope.md#8-anti-scope-creep-decision-matrix-gatekeeper)), reject it immediately.

---

## 1. Project Overview

`fl-cl` is a hybrid **Federated Learning (FL)** and **Continual Learning (CL)** intrusion detection system designed to analyze encrypted network traffic metadata across a 3-node Proxmox VE cluster.

* **Federated Learning (FL)**: Orchestrated via **Flower** (`flwr`), enabling clients to collaboratively train a shared model without transmitting raw network flows.
* **Continual Learning (CL)**: Powered by **Avalanche** (`avalanche-lib`), implementing a class-weighted **Elastic Weight Consolidation (EWC)** strategy to defend against catastrophic forgetting of historical traffic classes.
* **Feature Extraction**: Done via **NFStream**, converting live raw packets into tabular flow features.

---

## 2. Directory Structure

```text
fl-cl/
 docs/ # Technical documentation & papers
 configs/ # Hyperparameter sweeps & experiment setups
 src/ # Core Python codebase
 aggregator/ # Flower Server & MLflow dashboard
 defender/ # Flower Clients, EWC strategies, and Models
 client.py # FL Client lifecycle wrapper
 cl_strategy.py # Avalanche EWC implementation
 extractor.py # NFStream extraction engine
 model.py # CyberDefenseNet backbones & factory
 orchestrate.py # Simulation pipeline controller
 tools/ # Evaluation & diagnostics utilities
 scratch/ # Local test scripts & verification suites
```

---

## 3. Core Architecture Details

### Model Architecture (`src/defender/model.py`)

The factory function `get_model(model_type, input_dim, num_classes, **kwargs)` dynamic-instantiates one of three backbones:

1. **MLP (`mlp` / `CyberDefenseNet`)**: Standard feedforward network with configurable hidden dimensions.
2. **1D-CNN (`cnn` / `CyberDefenseCNN`)**: A convolutional feature extractor. Resolves linear fully connected input dimensions dynamically using a dummy forward pass rather than hardcoded dimensions:

 ```python
 with torch.no_grad():
 dummy_out = self.conv(torch.zeros(1, 1, input_dim))
 self.fc_input_dim = dummy_out.numel()
 ```

3. **Transformer (`transformer` / `CyberDefenseTransformer`)**: Projects inputs into token embeddings and applies self-attention. It enforces mathematical integrity with:

 ```python
 assert token_len * token_dim == input_dim
 ```

### Continual Learning Strategy (`src/defender/cl_strategy.py`)

Applies custom class-weighted EWC penalty calculations. It ensures that the importance weights computed for the network parameters are scaled in proportion to the frequency of traffic classes inside the current batch.

---

## 4. Key Rules and Guidelines

> [!IMPORTANT]
> **YAGNI Compliance**: Do not introduce unnecessary abstractions, extra libraries, or complex nested classes. Keep the design flat, transparent, and direct.

<!-- -->

> [!TIP]
> **No Hardcoded Shapes**: When modifying the CNN backbone or adding layers, always preserve the dummy forward pass shape calculator to ensure arbitrary hyperparameter combinations don't crash the grid search pipeline.

<!-- -->

> [!WARNING]
> **Standard Libraries & PyTorch Primitives First (Ponytail Rule)**: Avoid wrapper libraries for model utilities. Favor native `torch` modules (e.g. `nn.TransformerEncoderLayer`, `nn.Linear`) over custom implementations.

<!-- -->

> [!IMPORTANT]
> **Script Placement & Organization**: Always place single-use, temporary, or exploratory scripts strictly in `scratch/`. The `tools/` directory is reserved exclusively for significant, reusable, production-grade utilities (benchmarking, evaluation, auditing, and system operations).

---

## 5. Verification & Testing

Always validate the architectural changes and training loop before committing. Use the pre-existing test suites in the `tools/` directory:

### Run Model Verification Suite

Checks model forward pass compatibility, TorchScript compilation, 8-bit dynamic quantization, and Fisher-guided pruning.

```bash
python tools/test_models.py
```

### Run Local Training Verification

Verifies end-to-end training convergence on a synthetic/dummy 5-class traffic flow dataset.

```bash
python tools/test_local_train.py
```

### Run Network Stability & Health Verification

Audits SSH latency, duplicate IP collisions on `vmbr0`, MTU 1280, TCP MSS 1220 clamping, persistent sysctl keepalives, and live service endpoints (Ollama HTTPS & MLflow) across `ollama-server` and `fl-aggregator`.

```bash
python tools/check_network_stability.py
```

---

## 6. Agent Skills & Operational Automation

The project includes specialized agent skills under `.agents/skills/` tailored for Proxmox cluster operations, MLOps governance, and Continual Learning diagnostics:

1. **`fl-cl-experiment-runner`**: Experiment YAML config validation, hyperparameter sweep execution, and MLflow run tracing.
   - Script: `python .agents/skills/fl-cl-experiment-runner/scripts/validate_config.py --config <config.yaml>`
2. **`fl-cl-proxmox-ops`**: PVE bare-metal health checks, VM/LXC state auditing, Corosync quorum, and port-mirroring diagnostics.
   - Script: `python .agents/skills/fl-cl-proxmox-ops/scripts/check_cluster_health.py`
3. **`fl-cl-mlops-governance`**: ADR-006 compliance auditing (CLI standards, docstrings, logger migration, model card freshness).
   - Script: `python .agents/skills/fl-cl-mlops-governance/scripts/audit_tool_compliance.py`
4. **`fl-cl-continual-learning`**: EWC/GEM backward transfer ($BWT$), catastrophic forgetting verification, and stability checks.
   - Script: `python .agents/skills/fl-cl-continual-learning/scripts/diagnose_forgetting.py`
5. **`fl-cl-edge-inference-opt`**: Eager FP32 vs TorchScript JIT vs INT8 dynamic quantization latency profiling on CPU edge constraints.
   - Script: `python .agents/skills/fl-cl-edge-inference-opt/scripts/profile_inference.py --model cnn`
6. **`fl-cl-dataset-intelligence`**: Statistical profiling, schema mapping, cross-dataset generalization, and benchmark scorecard generation.
   - Script: `python .agents/skills/fl-cl-dataset-intelligence/scripts/profile_datasets.py --all`

