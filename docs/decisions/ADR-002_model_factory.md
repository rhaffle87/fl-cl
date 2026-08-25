# ADR-002: Dynamic Multi-Backbone Model Architecture Factory

## Status
Accepted

## Date
2026-08-15

## Context
Encrypted Network Traffic Analysis (ETA) requires versatile model backbones to accommodate varied edge deployment constraints:
1. **Ultra-low latency microcontrollers / edge routers**: Require sub-millisecond inference and tiny memory footprints (<20 KB).
2. **High-throughput gateway defenders**: Require temporal feature extraction across sequential packet bursts (e.g., packet inter-arrival times, SPLT metrics).
3. **High-precision cloud/aggregation analyzers**: Benefit from self-attention over tokenized flow metadata for contextual correlation.

To prevent codebase fragmentation, the system requires a unified model factory (`get_model`) capable of dynamically instantiating backbones without hardcoded tensor shapes.

## Decision
We implement a unified backbone factory in `src/defender/model.py` providing three distinct architectures:

### 1. `CyberDefenseCNN` (1D Convolutional Neural Network)
- **Design**: 2-stage 1D convolutions (`Conv1d(1, 16, k=3) -> MaxPool1d(2) -> Conv1d(16, 32, k=3) -> MaxPool1d(2)`) followed by an adaptive dense classifier.
- **Dynamic Dimension Computation**: Resolves the fully connected input dimension dynamically via a dummy forward pass during `__init__`, eliminating hardcoded tensor shapes:
 ```python
 with torch.no_grad():
 dummy_out = self.conv(torch.zeros(1, 1, input_dim))
 self.fc_input_dim = dummy_out.numel()
 ```
- **Role**: Production Default (`champion-cnn`). Best overall robustness and feature temporal filtering.

### 2. `CyberDefenseTransformer` (Self-Attention Tokenizer)
- **Design**: Projects 32-dimensional flow vectors into $T=8$ tokens of dimension $D=4$, adds learned positional encodings, and processes via 2-layer `nn.TransformerEncoder` with 4-head multi-head self-attention.
- **Mathematical Invariant**:
 ```python
 assert token_len * token_dim == input_dim
 ```
- **Role**: High-Precision Champion (`champion` / `champion-transformer`). Achieves lowest training loss (0.0119–0.0146) and 1.54x INT8 dynamic quantization speedup.

### 3. `CyberDefenseNet` (3-Layer Multi-Layer Perceptron)
- **Design**: Feedforward network `Linear(32, 64) -> ReLU -> Dropout(0.2) -> Linear(64, 32) -> ReLU -> Linear(32, 5)`.
- **Role**: Ultra-Lightweight Baseline (`champion-mlp`). 0.017 MB state dict size; 633,600 flows/sec peak throughput on CPU.

## Alternatives Considered

### 1. Recurrent Neural Networks (LSTM / GRU)
- **Pros**: Natural fit for sequential packet series.
- **Cons**: Poor parallelization on edge CPUs; high inference latency (>1.5 ms per batch); gradient explosion when combined with Avalanche continual learning loss penalties.
- **Rejected**: 1D-CNN provides equal or superior spatial-temporal extraction at 5x higher throughput.

### 2. Monolithic Model Class with Conditional Flags
- **Pros**: Single class definition.
- **Cons**: Convoluted `forward()` methods with runtime branching; breaks PyTorch TorchScript JIT graph tracing.
- **Rejected**: Distinct clean `nn.Module` subclasses behind a factory function preserve TorchScript exportability and clean separation of concerns.

## Consequences

### Positive
- **Flexibility**: Deployers can switch model backbones seamlessly via `--model-type cnn|transformer|mlp` or `experiment.yaml`.
- **Deployment Portability**: All three architectures export cleanly to standalone TorchScript (`.pt`) and support 8-bit dynamic quantization (`torch.ao.quantization.quantize_dynamic`).
- **Zero Shape Breakage**: Preserving the dummy pass shape calculator prevents crashes across arbitrary feature dimension sweeps.

### Negative / Trade-offs
- Transformer architecture requires input dimension to be exactly divisible by `token_len * token_dim = 32`.
