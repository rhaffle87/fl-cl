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

### Model Registry Aliases
Semantic identifiers assigned in the MLflow Model Registry:
- `champion`: The production-active model version.
- `challenger`: Newly trained candidate model pending automated validation gate execution.
- `champion-transformer`: Dedicated alias for the high-precision self-attention backbone.
- `champion-cnn`: Dedicated alias for the 1D-CNN temporal feature extractor.
- `champion-mlp`: Dedicated alias for the ultra-low latency feedforward backbone.

### ONNX Runtime
An open-source, cross-platform inference engine (Microsoft) that executes models in the Open Neural Network Exchange (`.onnx`) format. On x86-64 CPUs, it uses AVX2 SIMD vectorization to accelerate matrix multiplications, delivering up to **9.64x** throughput over vanilla PyTorch FP32 at batch size 16 for `CyberDefenseCNN`.

### Dynamic INT8 Quantization
A model compression technique that converts 32-bit floating-point (`FP32`) linear layer weights to 8-bit integers (`INT8`), reducing memory footprint by **50%** (93 KB → 46 KB for `CyberDefenseCNN`). Runtime scale factors are computed per-batch, which introduces overhead on small batches ($N \le 64$). Use ONNX Runtime for maximum edge throughput instead.

---

## 5. Privacy and Security Terminology

### Differential Privacy (DP) and DP-SGD
**Differential Privacy** provides a mathematical guarantee that the output of an algorithm does not significantly change if any single training record is added or removed. **DP-SGD** (Abadi et al., 2016) achieves this during neural network training by:
1. Clipping per-sample gradients to a maximum norm $C$ (configured: $C = 1.0$).
2. Adding calibrated Gaussian noise $\mathcal{N}(0, \sigma^2 C^2 I)$ to the aggregate gradient before the weight update.

The noise multiplier $\sigma$ controls the privacy-utility tradeoff:

| $\sigma$ | Accuracy | Botnet F1 | Interpretation |
| :---: | :---: | :---: | :--- |
| 0.00 | 99.64% | 0.7119 | No privacy bound |
| 0.10 | 99.61% | 0.7085 | Low-noise regime |
| 0.20 | 99.51% | 0.6980 | **Production deployment** (all gates pass) |
| 0.30 | 99.10% | 0.6450 | High-privacy degradation |

Implemented via native PyTorch batch-level gradient clipping (`torch.nn.utils.clip_grad_norm_`, $C=1.0$) and calibrated Gaussian noise injection on parameter gradients in `src/defender/cl_strategy.py`.

### Fisher Information Matrix Collapse
A failure mode of Elastic Weight Consolidation under extreme class imbalance. The Fisher diagonal $F_i$ is estimated via expectation over the training dataset:
$$F_i = \mathbb{E}_{(x,y) \sim \mathcal{D}} \left[ \left( \frac{\partial \log p(y|x,\theta)}{\partial \theta_i} \right)^2 \right]$$
When the training batch contains ~2000 Normal flows and ~12 Botnet flows, $F_{\text{Normal}} \gg F_{\text{Botnet}} \approx 0$. Botnet-sensitive weights receive near-zero EWC penalty and are overwritten by subsequent tasks, resulting in **BWT = -0.8544** and **0% Botnet recall**. GEM eliminates this failure by replacing the Fisher penalty with direct gradient projection constraints.

### Non-IID (Non-Independently and Identically Distributed)
A data heterogeneity condition in federated learning where each client's local dataset has a different class distribution. In `fl-cl`, Defender A primarily observes SSH brute-force and benign traffic, while Defender B observes DoS and C2 beaconing. Neither node has sufficient Botnet samples in isolation. FL aggregation allows cross-organization knowledge transfer, enabling each defender to detect threat classes it has not directly observed.

### GEM Memory Strength (`gem_memory_strength`, $s$)
A scalar hyperparameter (range: 0.0–1.0) controlling the strictness of the GEM gradient projection margin constraint. Lower values enforce tighter projection, reducing false positives at the cost of slightly higher gradient correction overhead.

| $s$ | Botnet Recall | Botnet F1 | FP Rate | Status |
| :---: | :---: | :---: | :---: | :--- |
| 0.5 | 100% | 0.5275 | Moderate | Initial recovery (v33) |
| 0.2 | 100% | **0.6905** | **Low** | **Production tuned (v34)** |

### TrimmedMean Beta ($\beta$)
The fraction of extreme client updates trimmed per coordinate before averaging. At $\beta = 0.10$ with $K = 2$ clients, exactly $\lfloor 0.10 \times 2 \rfloor = 0$ values are trimmed per coordinate — meaning TrimmedMean's resilience in this 2-client setup derives from the sorting step aligning outlier detection, not from literal trimming. The production champion (v35) was validated under this constraint: **99.53% accuracy, 100% Botnet recall** against 20% label poisoning.

### Backward Transfer (BWT) — Extended
A signed scalar metric for per-task forgetting. Extended interpretation table:

| BWT Range | Meaning | Observed In |
| :--- | :--- | :--- |
| $\approx 0.000$ | No forgetting — perfect stability | Normal, Exfil, DoS across all tracks |
| $-0.01$ to $-0.10$ | Mild forgetting — acceptable | SSH BruteForce (EWC baseline) |
| $-0.50$ to $-0.90$ | Severe forgetting — GEM required | Botnet (EWC baseline: -0.8544) |
| $= 0.000$ after GEM | Full recovery | Botnet (GEM v33/v34: 100% recall) |

---

## 6. Benchmark Datasets

### USTC-TFC2016
A benchmark dataset from the University of Science and Technology of China containing 10 malware traffic classes and 10 benign application classes, all captured as encrypted flows. Used in `fl-cl` for multi-class baseline training to establish the 5-class threat taxonomy.

### CIC-IDS2017 / CIC-IDS2018
Intrusion detection datasets from the Canadian Institute for Cybersecurity. CIC-IDS2017 spans Monday–Friday with distinct attack profiles per day (DoS, DDoS, brute force, web attacks, infiltration), making it ideal for sequencing Continual Learning tasks across temporal sessions. CIC-IDS2018 extends the attack diversity.

### CIRA-CIC-DoHBrw-2020
A dataset capturing DNS-over-HTTPS (DoH) traffic from both malicious exfiltration tools and legitimate DoH browsers. Used in `fl-cl` to train the DNS Exfiltration threat class against benign HTTPS-tunneled DNS.

