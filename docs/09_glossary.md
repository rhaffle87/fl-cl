# Domain Model & Technical Glossary

A centralized reference defining the domain concepts, mathematical formulations, and engineering terminology used across the `fl-cl` codebase.

---

## 1. Continual Learning (CL) Concepts

### Catastrophic Forgetting
The tendency of artificial neural networks to completely and abruptly overwrite previously learned knowledge when trained sequentially on new data distributions. In `fl-cl`, catastrophic forgetting occurs when defender nodes trained on new attack stages (e.g., DNS Exfiltration) lose detection accuracy on prior threats (e.g., SSH Brute Force or Botnet).

### Plasticity-Stability Dilemma
The trade-off between a model's ability to adapt to newly emerging network threat patterns (**plasticity**) versus preserving established detection representations of historical traffic classes (**stability**). Controlled in EWC via the hyperparameter $\lambda_{\text{EWC}}$.

### Elastic Weight Consolidation (EWC)
A regularization-based continual learning algorithm that slows down learning on parameters deemed critical to previous tasks. Criticality is quantified by the diagonal of the empirical **Fisher Information Matrix** $F_i$:
$$L(\theta) = L_{\text{new}}(\theta) + \sum_i \frac{\lambda}{2} F_i (\theta_i - \theta_{A, i}^*)^2$$

### Gradient Episodic Memory (GEM)
An episodic memory continual learning strategy that stores a subset of exemplary patterns $P$ per experience in an episodic buffer. During backpropagation on task $t$, candidate gradient $g$ is projected to ensure it does not increase loss on any prior task $k < t$:
$$\langle g, g_k \rangle \ge 0 \quad \forall k < t$$
If $\langle g, g_k \rangle < 0$, GEM solves a Quadratic Programming (QP) problem to find the closest projected gradient satisfying all memory constraints.

### Backward Transfer (BWT)
A quantitative measure of how learning new tasks influences performance on previously learned tasks. For $T$ sequential tasks, the BWT of task $i$ is defined as:
$$\text{BWT}_i = R_{T, i} - R_{i, i}$$
where $R_{T, i}$ is accuracy on task $i$ after training on task $T$, and $R_{i, i}$ is accuracy immediately after training on task $i$.
- $\text{BWT} < 0$: Catastrophic forgetting has occurred.
- $\text{BWT} \ge 0$: Knowledge retention or positive backward transfer.

---

## 2. Federated Learning (FL) Concepts

### Flower (`flwr`)
An open-source federated learning framework that manages decentralized client-server gRPC communication, local model weight dispatch, and global parameter aggregation.

### Federated Averaging (`FedAvg`)
The standard federated optimization algorithm where the central server aggregates client weights weighted by the number of local training samples $n_k$:
$$\theta_{t+1} = \sum_{k=1}^K \frac{n_k}{N} \theta_{t+1}^k$$

### TrimmedMean Robust Aggregation
A Byzantine-resilient aggregation strategy that sorts model parameter updates coordinate-wise across all responding clients and trims the top and bottom $\beta$ fraction (e.g., $\beta = 0.10$) before computing the mean. Discards malicious or poisoned parameter updates from Byzantine nodes.

### Label Poisoning Attack
An adversarial attack where a compromised edge client manipulates training labels (e.g., changing true Botnet samples to Normal) to inject backdoors or degrade detection sensitivity in the global aggregated model.

### Jensen-Shannon Divergence (JSD) Dataset Drift Gate
A symmetric, bounded statistical distance measure ($0 \le \text{JSD} \le 1$) computed between the current client feature distribution and the baseline training feature profile. If $\text{JSD} > 0.60$, the client data is flagged for distribution shift.

---

## 3. Encrypted Traffic Analysis (ETA) Concepts

### NFStream
A high-performance Python framework for fast, flexible, and expressive network traffic analysis, providing deep packet inspection, TLS handshake extraction, and flow aggregation.

### JA3 / JA3S TLS Handshake Fingerprints
An MD5 hash representation of specific parameters in the TLS Client Hello (`ja3`) and Server Hello (`ja3s`) packets (SSL version, accepted ciphers, extensions, elliptic curves, and point formats). Allows identification of client applications even when network payloads are fully encrypted.

### SPLT (Sequence of Packet Lengths and Times)
Statistical features capturing the sequential dynamics of packet lengths, directional volume ratios, and inter-arrival intervals within a bidirectional network session.

### tmpfs In-Memory RAMDisk
A temporary file storage facility located entirely in volatile virtual memory (`/mnt/ramdisk/flows/`), eliminating disk I/O bottlenecks during 100k+ packets/sec capture.

---

## 4. MLOps & Deployment Terminology

### TorchScript JIT
A statically typed intermediate representation of PyTorch models that can be serialized (`.pt`) and executed in high-performance C++ runtimes (LibTorch) without requiring a Python interpreter.

### Dynamic INT8 Quantization
A model compression technique that converts 32-bit floating-point (`FP32`) linear layer weights to 8-bit integers (`INT8`), reducing memory footprint by **50%** while executing fast integer matrix multiplication.

### Model Registry Aliases
Semantic identifiers assigned in the MLflow Model Registry:
- `champion`: The production-active model version.
- `challenger`: Newly trained candidate model pending automated validation gate execution.
- `champion-transformer`: Dedicated alias for the high-precision self-attention backbone.
- `champion-cnn`: Dedicated alias for the 1D-CNN temporal feature extractor.
- `champion-mlp`: Dedicated alias for the ultra-low latency feedforward backbone.
