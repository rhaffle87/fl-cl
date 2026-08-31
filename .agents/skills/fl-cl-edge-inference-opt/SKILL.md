---
name: fl-cl-edge-inference-opt
description: Guide for edge model optimization, dynamic quantization (PyTorch/torchao), Fisher-guided pruning, and TorchScript JIT compilation for microVM edge deployment in fl-cl.
---

# Edge Inference Optimization Skill (`fl-cl-edge-inference-opt`)

## Overview
This skill provides standardized methodologies, benchmarks, and scripts for optimizing neural network backbones (`MLP`, `1D-CNN`, `Transformer`) for edge deployment on lightweight Proxmox Alpine/Debian nodes.

---

## 1. Core Optimization Pipelines

### A. TorchScript JIT Compilation
Converts eager PyTorch models into optimized TorchScript IR for high-throughput C++ / Python runtime execution.
```python
import torch
scripted_model = torch.jit.script(model)
torch.jit.save(scripted_model, "checkpoints/champion_scripted.pt")
```

### B. 8-Bit Dynamic Quantization (`torch.quantization` / `torchao`)
Quantizes linear layers from FP32 (`float32`) to INT8 (`qint8`), reducing model memory footprint by ~70% and improving CPU inference latency.
```python
quantized_model = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},
    dtype=torch.qint8
)
```

### C. Fisher-Guided Gradient Pruning
Prunes parameters with lowest Fisher information diagonal entries:
```python
from defender.pruning import apply_fisher_pruning
pruned_model = apply_fisher_pruning(model, fisher_diag, prune_fraction=0.20)
```

---

## 2. Verification & Latency Profiling

Run the inference latency profiler to benchmark models against production constraints (P95 Latency $\le$ 2.0ms):
```bash
python .agents/skills/fl-cl-edge-inference-opt/scripts/profile_inference.py --model mlp --batch-size 32
```

---

## 3. Reference Architecture
See [references/optimization_matrix.md](file:///e:/Projects/fl-cl/.agents/skills/fl-cl-edge-inference-opt/references/optimization_matrix.md) for empirical latency and memory tradeoffs across architectures.
