# Antigravity & Gemini Workspace Guide: FL-CL

Welcome! This document outlines key context, conventions, architecture details, and verification commands to help you navigate and develop inside the `fl-cl` repository.

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

---

## 5. Verification & Testing

Always validate the architectural changes and training loop before committing. Use the pre-existing test suites in the `scratch/` directory:

### Run Model Verification Suite

Checks model forward pass compatibility, TorchScript compilation, 8-bit dynamic quantization, and Fisher-guided pruning.

```bash
python scratch/test_models.py
```

### Run Local Training Verification

Verifies end-to-end training convergence on a synthetic/dummy 5-class traffic flow dataset.

```bash
python scratch/test_local_train.py
```
