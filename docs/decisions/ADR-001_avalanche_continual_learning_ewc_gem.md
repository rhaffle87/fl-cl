# ADR-001: Continual Learning Strategy — Avalanche EWC and GEM Integration

## Status
Accepted

## Date
2026-08-15

## Context
In decentralized edge intrusion detection systems (IDS), defender nodes face non-stationary, streaming encrypted network traffic. Network threats arrive sequentially in discrete bursts (e.g., Benign $\rightarrow$ SSH Brute Force $\rightarrow$ Slowloris DoS $\rightarrow$ DNS Exfiltration $\rightarrow$ C2 Botnet).

Standard gradient descent training on newly observed traffic classes leads to **catastrophic forgetting** — the degradation of model accuracy on previously learned attack patterns. The project requires a continual learning (CL) mechanism operating at the edge under the following constraints:
1. **Zero Raw Packet Transmit**: Raw network packets cannot be transmitted across nodes for centralized replay.
2. **Edge Hardware Budget**: Defenders run on low-resource VMs (2 vCPUs, 4 GB RAM) without discrete GPUs.
3. **Avalanche Framework Compatibility**: Direct integration with standard continual learning research frameworks (`avalanche-lib`).

## Decision
We implement a hybrid continual learning strategy using **Elastic Weight Consolidation (EWC)** as the primary baseline, augmented with **Gradient Episodic Memory (GEM)** for sparse minority-class threat protection.

### Implementation Architecture (`src/defender/cl_strategy.py`)
1. **EWC (Elastic Weight Consolidation)**:
 - Calculates the diagonal of the empirical Fisher Information Matrix $F_i$ after each task experience $k-1$:
 $$L_{\text{EWC}}(\theta) = L_{\text{current}}(\theta) + \sum_{i} \frac{\lambda}{2} F_{i} (\theta_i - \theta_{k-1, i}^*)^2$$
 - Configurable regularization parameter $\lambda_{\text{EWC}} \in [0.4, 1.2]$ (production default: $0.8$).
 - Normalized per-class CrossEntropyLoss weighting ($w_{\text{Botnet}} = 8.0\text{--}15.0$) to scale minority gradients.
2. **GEM (Gradient Episodic Memory)**:
 - Maintains an episodic replay buffer of $P = 512$ exemplary patterns per experience.
 - Constrains candidate gradient $g$ against prior experience gradients $g_k$:
 $$\langle g, g_k \rangle \ge 0 \quad \forall k < t$$
 - Projects $g$ via Quadratic Programming if a gradient violation $\langle g, g_k \rangle < 0$ is detected, ensuring non-negative backward transfer.

## Alternatives Considered

### 1. Naive Fine-Tuning (No Regularization)
- **Pros**: Zero computational overhead; fastest training time.
- **Cons**: Catastrophic forgetting is severe. Accuracy on historical traffic classes dropped from 99.8% to <20% within 2 attack phases.
- **Rejected**: Fails core operational requirement of multi-threat defense.

### 2. Full Experience Replay (Raw Packet Flow Replay)
- **Pros**: High retention across all classes.
- **Cons**: High memory and disk footprint; risk of data leakage; violates decentralized privacy principles.
- **Rejected**: Memory buffers exceed edge VM RAM limits during prolonged volumetric floods.

### 3. Synaptic Intelligence (SI) / Memory Aware Synapses (MAS)
- **Pros**: Parameter regularization without explicit Fisher matrix sampling.
- **Cons**: Path-integral path computation in SI is unstable under batch-level federated model averaging.
- **Rejected**: EWC and GEM demonstrated significantly higher numerical stability across FL aggregation rounds.

## Consequences

### Positive
- **Stability**: Retention of historical threat signatures with backward transfer $|\text{BWT}| < 0.002$ for majoritarian classes over 100 rounds.
- **Minority Recovery**: GEM completely recovered Botnet recall from 0% (under EWC with sparse data) to 100.00% (24/24 validation samples).
- **Lightweight**: Model parameters update locally in <150 ms per batch without requiring persistent raw flow storage.

### Negative / Trade-offs
- EWC without replay remains vulnerable to minority class collapse if flow samples during an attack stage are extremely sparse (<15 flows).
- GEM introduces a small quadratic programming optimization step during local backpropagation when memory constraints are active.
