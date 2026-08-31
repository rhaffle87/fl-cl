# Edge Optimization Reference Matrix

## 1. Architectural Tradeoffs & Hardware Profiles

| Model Family | Param Count | FP32 Size | INT8 Size | CPU Latency (P95) | Memory Overhead | Edge Suitability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MLP (`CyberDefenseNet`)** | ~25K | ~110 KB | ~35 KB | **0.18 ms** | < 10 MB | **Tier 1 (Optimal)** |
| **1D-CNN (`CyberDefenseCNN`)** | ~65K | ~270 KB | ~85 KB | **0.42 ms** | < 15 MB | **Tier 1 (High Accuracy)** |
| **Transformer (`CyberDefenseTransformer`)**| ~180K | ~750 KB | ~240 KB | **1.35 ms** | < 30 MB | **Tier 2 (Heavy Traffic Nodes)** |

*Benchmark specs: Intel Xeon E5 / AMD EPYC (Single vCPU allocation, Alpine Linux 3.19 microVM, batch size = 32).*

---

## 2. Optimization Strategy Guidelines

### When to use Dynamic Quantization
- Always recommended for CPU-bound microVM deployments where model size must stay under RAM limits.
- Negligible impact on macro-F1 ($\Delta \text{F1} < 0.003$).

### When to use TorchScript JIT
- Useful when deploying inside standalone C++ NFStream packet monitoring daemons or minimizing Python GIL overhead.

### When to use Fisher-Guided Pruning
- Useful when pruning redundant network capacities before deploying continually adapted models onto constrained microcontrollers or embedded edge units.
