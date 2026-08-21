# FL-CL Project Context

> Workspace-scoped rule file. All agents working in this repository must read and internalize this context before taking action.
> Last updated: 2026-08-16

---

## Project Identity

| Field | Value |
| :--- | :--- |
| **Project name** | `fl-cl` — Hybrid Federated-Continual Learning Cyber Defense |
| **Author** | Rafli Alif Ihza Hartono |
| **Institution** | Institut Teknologi Sepuluh Nopember (ITS), Surabaya, Indonesia |
| **Department** | Telecommunications Engineering, F-ELECTICS |
| **Purpose** | Undergraduate thesis: collaborative IDS on encrypted networks via FL+CL |
| **Language** | Python 3.11+ |
| **Primary docs** | `docs/paper/research_paper.md` (thesis monograph), `docs/arguments.md` (defense dossier) |

---

## Directory Structure

The workspace root is `fl-cl/`. Key directories and their purpose:

- `.agents/rules/` — Agent workspace rules (this file + ponytail.md)
- `configs/` — All experiment YAML configs and baseline feature stats
- `configs/experiments/` — 16 named experiment configs (baseline, dp_sgd, robust_agg, gem_botnet, etc.)
- `data/reports/` — Empirical training results (`training_results_report.md`)
- `docs/` — All documentation (thesis chapters, ADRs, arguments dossier, support figures)
- `docs/paper/research_paper.md` — Full thesis monograph (primary paper)
- `docs/arguments.md` — Thesis defense dossier (21 attack categories)
- `docs/decisions/` — Architecture Decision Records ADR-001 to ADR-005
- `infra/` — PVE host configs, VM provision scripts, hookscripts, guest setup
- `src/aggregator/server.py` — Flower FL server, FedAvg/TrimmedMean, MLflow tracking
- `src/defender/model.py` — CyberDefenseNet (MLP), CyberDefenseCNN, CyberDefenseTransformer + factory
- `src/defender/cl_strategy.py` — Avalanche EWC/GEM CL strategy + BWT computation
- `src/defender/client.py` — Flower FL client, DP-SGD, local training loop
- `src/defender/extractor.py` — NFStream ETA feature extraction engine
- `src/defender/inference_loop.py` — Real-time per-flow inference + alert dispatch
- `src/orchestrate.py` — Master training pipeline controller (entry point)
- `tools/` — Evaluation, CI/CD, benchmarking, plotting utilities
- `tools/ci_cd_promote.py` — MLflow model promotion gate automation
- `tools/benchmark_inference_latency.py` — FP32 vs INT8 throughput benchmarking
- `tools/bwt_eval_suite.py` — Backward Transfer Metric evaluation suite
- `scratch/` — Local test scripts only, NOT production code

---

## Tech Stack by Layer

### Layer 1 — Hypervisor (Bare Metal PVE Hosts: `its`, `node2`, `pve`)

| Technology | Version | Role |
| :--- | :--- | :--- |
| Proxmox VE | 8.x | Type-1 hypervisor; VM and LXC management |
| Linux Bridge (vmbr0, vmbr1) | kernel | Virtual L2 switching between guests |
| Flat L2 Subnetting | 10.10.0.0/16 | Bypasses unmanaged switch VLAN limitations |
| LACP Bond (bond0) | kernel module | Link aggregation on nodes `its` and `node2` |
| tc (Traffic Control) | iproute2 | Port-mirror: copies target VM traffic to defender capture NIC |
| Proxmox Hookscripts | PVE built-in | Re-establish tc mirred rules on every VM post-start |
| LVM-Thin | lvm2 | Thin-provisioned storage + fast snapshot/rollback |
| Corosync | 3.x | Cluster quorum and node health heartbeat |
| Dell PERC H755 | Hardware | RAID controller; 1.20 TB logical volume presented to LVM |

### Layer 2 — Guest Operating Systems

| ID | Hostname | OS | vCPU | RAM | IP | Role |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| LXC 300 | fl-aggregator | Ubuntu 24.04 LTS | 4 | 8 GB | 10.10.130.10 | Flower server + MLflow tracking |
| VM 310 | defender-a | Ubuntu 24.04 LTS | 8 | 16 GB | 10.10.130.11 | NFStream capture + PyTorch/Avalanche training + Flower client |
| VM 320 | defender-b | Ubuntu 24.04 LTS | 8 | 16 GB | 10.10.130.12 | Parallel defender (simulates separate organization) |
| VM 311 | target-a1 | Alpine Linux 3.20 | 1 | 1 GB | 10.10.110.15 | Attack/traffic target for defender-a |
| VM 321 | target-b1 | Alpine Linux 3.20 | 1 | 1 GB | 10.10.120.15 | Attack/traffic target for defender-b |
| VM 400 | traffic-gen | Kali Linux 2024.4 | 4 | 4 GB | 10.10.140.10 | Metasploit C2, Hydra, Selenium benign browsing |

### Layer 3 — Network Topology

vmbr0 (192.168.x.x) — Out-of-band management only  
vmbr1 (10.10.0.0/16) — All FL training + Corosync + data traffic

Subnet layout:
- 10.10.110.0/16 — Org A (defender-a + target-a1)
- 10.10.120.0/16 — Org B (defender-b + target-b1)
- 10.10.130.0/16 — FL backbone (aggregator + defenders)
- 10.10.140.0/16 — Traffic generation (traffic-gen)

Key ports:
- TCP/8080 — Flower gRPC (aggregator)
- TCP/5000 — MLflow tracking UI
- TCP/6006 — TensorBoard (per defender)
- TCP/443 — Ollama reverse proxy (Nginx/Tailscale)

### Layer 4 — Python ML/FL-CL Stack (Defender VMs 310 and 320)

| Package | Version | Purpose |
| :--- | :--- | :--- |
| Python | 3.11+ | Runtime |
| PyTorch | 2.x | Deep learning; all three model backbones |
| Avalanche (avalanche-lib) | 0.5+ | Continual Learning: EWC and GEM strategies |
| Flower (flwr) | 1.x | Federated Learning client; gRPC weight sync |
| Opacus | 1.x | Differential Privacy: DP-SGD gradient clipping and noise injection |
| NFStream | 6.x | Encrypted traffic feature extraction (JA3, flow statistics) |
| scikit-learn | 1.x | StandardScaler, F1/precision/recall metrics |
| pandas | 2.x | DataFrame operations on CSV flow records |
| numpy | 1.x | Numerical array operations |
| TensorBoard | 2.x | Weight/gradient distribution visualization |
| libpcap | system | Packet capture backend for NFStream |

### Layer 5 — Python Aggregator Stack (LXC 300)

| Package | Version | Purpose |
| :--- | :--- | :--- |
| Python | 3.11+ | Runtime |
| Flower (flwr) | 1.x | FL server; FedAvg / TrimmedMean / FedMedian aggregation |
| MLflow | 3.x | Experiment tracking, per-round metric logging, model registry |
| matplotlib | 3.x | Headless confusion matrix heatmap rendering |

### Layer 6 — Traffic Generation Stack (VM 400, Kali Linux)

| Tool | Purpose |
| :--- | :--- |
| Metasploit Framework | C2 beaconing, reverse HTTPS shells (Botnet class) |
| Hydra | SSH/RDP brute-force attacks (BruteForce class) |
| hping3 | TCP/UDP flood, DDoS simulation (DoS class) |
| Slowloris | HTTP slow-connection DoS (DoS class) |
| tcpreplay | Replay benchmark PCAP datasets at line rate |
| tcprewrite | Rewrite IPs/MACs in PCAPs for testbed addressing |
| Selenium + Chromium | Headless HTTPS browsing (Normal class) |
| Locust | High-volume HTTP/HTTPS load generation |

### Layer 7 — Benchmark Datasets

| Dataset | Content | Use |
| :--- | :--- | :--- |
| USTC-TFC2016 | 10 malware + 10 benign encrypted traffic classes | Multi-class baseline training |
| CIC-IDS2017 | Multi-day captures: DoS, DDoS, brute force, web attacks | CL task sequencing |
| CIC-IDS2018 | Extended attack scenarios | Supplementary CL tasks |
| CIRA-CIC-DoHBrw-2020 | DNS-over-HTTPS exfiltration vs. benign DoH | Encrypted channel detection |

### Layer 8 — I/O and Storage

| Technology | Purpose | Location |
| :--- | :--- | :--- |
| tmpfs RAM Disk (4 GB) | Buffer NFStream flow writes; avoids RAID I/O contention | /mnt/ramdisk inside VM 310, VM 320 |
| LVM-Thin Snapshots | Fast VM checkpoint/rollback for reproducibility | PVE local-lvm pool |
| CSV files | Batched flow records persisted after flush | /mnt/ramdisk/flows/ then LVM volume |

### Layer 9 — MLOps and Observability

| Tool | Purpose | Port |
| :--- | :--- | :--- |
| MLflow | Centralized tracking: loss, accuracy, BWT, per-round metrics | 5000 |
| TensorBoard | Weight distributions, gradient norms, activation statistics | 6006 |
| Ollama (llama3.1:8b) | Local LLM for training narrative report generation | 11435 |
| Nginx + Tailscale | Reverse proxy for Ollama API with dual-key auth | 443/80 |
| Telegram Bot API | Real-time experiment milestone notifications | HTTP |

---

## Model Architectures

All models live in `src/defender/model.py`. Instantiate via `get_model(model_type, input_dim, num_classes, **kwargs)`.

**Contract:**
- Input: 32-dimensional Z-score normalized feature vector per network flow
- Output: 5-class logits [Normal, Botnet, Exfiltration, BruteForce, DoS]

**CyberDefenseNet (MLP) — model_type = "mlp"**
- Architecture: Input(32) -> FC(64) -> ReLU -> Dropout(0.2) -> FC(32) -> ReLU -> FC(5)
- Footprint: 0.017 MB | FP32 throughput: 633,619 flows/sec
- Use case: ultra-low-resource edge deployment

**CyberDefenseCNN (1D-CNN) — model_type = "cnn" — Production Champion**
- Architecture: Conv1d stack with two conv+pool stages; FC head with dynamically computed input dim
- fc_input_dim is computed via dummy forward pass; NEVER hardcode this value
- Footprint: 0.070 MB | FP32: 62,525 flows/sec | INT8: 55,068 flows/sec
- Best FL accuracy: 99.72%

**CyberDefenseTransformer — model_type = "transformer"**
- Architecture: Input reshaped to (8 tokens x 4 dim) -> Linear projection -> TransformerEncoder (nhead=4, 2 layers) -> GlobalAvgPool -> FC head
- Constraint enforced: assert token_len * token_dim == input_dim
- Footprint: 0.071 MB | INT8 speedup: 1.54x | Best FL accuracy: 99.63%

---

## Feature Engineering

NFStream extracts 18 raw flow features; after augmentation and Z-score scaling: 32 features.

Key columns:
- bidirectional_packets, bidirectional_bytes, duration_ms
- src2dst_packets, src2dst_bytes, dst2src_packets, dst2src_bytes
- src2dst_mean_piat_ms, dst2src_mean_piat_ms, dst_port
- JA3/JA4 fingerprint hashes (TLS handshake signatures)
- Flow entropy (Shannon entropy over payload byte distribution)
- SPLT-derived statistics (sequence of packet lengths and times)

Z-score normalization parameters live in `configs/baseline_feature_stats.json`. Do not recompute from local data — doing so causes client-side covariate shift across organizations.

---

## Experiment Configuration Schema

All experiments are YAML files under `configs/experiments/`. Master schema: `configs/experiment.yaml`.

Key config keys and their meaning:
- fl.rounds — Number of FL aggregation rounds
- fl.fraction_fit — Fraction of clients selected per round
- cl.strategy — "EWC" or "GEM"
- cl.ewc_lambda — EWC regularization strength (0.8 to 2.0 validated range)
- cl.gem_patterns_per_exp — GEM episodic memory buffer size per experience
- cl.gem_memory_strength — GEM gradient projection strength (0.2 production-tuned)
- security.poison_enabled — Toggle 20% label poisoning simulation
- security.dp_enabled — Toggle DP-SGD gradient privatization
- security.dp_noise_multiplier — sigma for Gaussian noise (0.30 production-validated)
- security.aggregation_strategy — "FedAvg", "TrimmedMean", "FedMedian", or "Krum"
- model.type — "mlp", "cnn", or "transformer"
- model.input_dim — 32 (fixed; matches NFStream feature count)
- model.num_classes — 5 (fixed; threat class taxonomy)
- training.lr — Learning rate (0.003 default)
- training.class_weights — Per-class loss weight vector (e.g. [1.0, 15.0, 2.0, 4.0, 15.0])
- mlops.mode — "experimental" (cold start) or "production" (warm start)

---

## Threat Class Taxonomy

| Class ID | Label | MITRE ATT&CK | Traffic Profile | Difficulty |
| :---: | :--- | :--- | :--- | :--- |
| 0 | Normal | N/A | Benign user traffic | Baseline |
| 1 | Botnet | T1071 | Low-volume, stealthy, bidirectional asymmetric | Hard |
| 2 | DNS Exfiltration | T1048 | Ultra-low-volume, high DNS query rate | Very Hard |
| 3 | SSH Brute Force | T1110 | High packet rate, repetitive, short flows | Easy |
| 4 | DoS | T1498 | Volumetric, one-directional, high bytes/sec | Easy |

---

## MLOps Promotion Gate

Per-class F1 thresholds enforced by `tools/ci_cd_promote.py`. ALL must pass for `champion` alias assignment.

| Class | Threshold | Champion v35 (20% poison) |
| :--- | :---: | :---: |
| Normal | >= 0.50 | 0.997 |
| Botnet | >= 0.60 | 0.667 |
| Exfiltration | >= 0.70 | 0.999 |
| BruteForce | >= 0.50 | 0.995 |
| DoS | >= 0.70 | 0.981 |

---

## Architecture Decision Records (ADRs)

Formal records in `docs/decisions/`:

| ADR | Title | Primary File |
| :--- | :--- | :--- |
| ADR-001 | Avalanche EWC and GEM Integration | src/defender/cl_strategy.py |
| ADR-002 | Dynamic Multi-Backbone Model Architecture Factory | src/defender/model.py |
| ADR-003 | NFStream ETA + tmpfs RAMDisk Storage | src/defender/extractor.py |
| ADR-004 | Flower FL Architecture + TrimmedMean Robust Aggregation | src/aggregator/server.py |
| ADR-005 | Automated CI/CD Promotion Gate + INT8 Quantization | tools/ci_cd_promote.py |

---

## Key Conventions and Hard Constraints

**YAGNI**: Do not introduce extra wrapper classes, base classes, or abstraction layers unless they already exist. Keep design flat, transparent, and direct.

**No Hardcoded Shapes (CNN Rule)**: When modifying CyberDefenseCNN or adding layers, always preserve the dynamic fc_input_dim calculation via dummy forward pass. Never replace with a hardcoded integer — this breaks the hyperparameter sweep pipeline.

**Standard Libraries First (Ponytail Rule)**: Use native PyTorch modules (nn.TransformerEncoderLayer, nn.Linear, nn.Conv1d) over third-party reimplementations.

**No Raw Data Crossing Org Boundary**: Raw PCAP files and flow records never leave their originating VM. Only model weight updates traverse the network via Flower gRPC.

**Configs Are the Source of Truth**: All experiment parameters live in YAML configs under `configs/experiments/`. Never hardcode tunables in Python source files.

**Scratch Is Not Production**: `scratch/` contains local test scripts. They are not imported by production code.

**Verify Before Claiming Done**:
```
python scratch/test_models.py        # Forward pass + TorchScript + quantization check
python scratch/test_local_train.py   # End-to-end training convergence on synthetic data
```

---

## Empirical Baselines (Source of Truth)

All numbers from `data/reports/training_results_report.md`. Do not estimate or invent these.

| Metric | Value | Source |
| :--- | :---: | :--- |
| Best FL accuracy (1D-CNN, baseline) | 99.72% | baseline.yaml — MLflow v20 |
| Best FL accuracy (100-round cold-start) | 99.88% | baseline_coldstart_100r.yaml |
| DP-SGD accuracy retention (sigma=0.30) | 99.51% | dp_sgd.yaml — MLflow v21 |
| Poisoning neutralization accuracy | 99.53% | benchmark_poisoning_dp.yaml — MLflow v35 |
| EWC Botnet BWT (50% dropout) | -0.7751 | benchmark_dropout.yaml — MLflow v31 |
| EWC Botnet BWT (100-round) | -0.8544 | baseline_coldstart_100r.yaml |
| GEM Botnet recall recovery | 100% | benchmark_gem_botnet.yaml — MLflow v33 |
| GEM tuned Botnet F1 | 0.6905 | benchmark_gem_precision.yaml — MLflow v34 |
| Aggregate cluster throughput (FP32) | 101,258 flows/sec | Dual-node live inference bench |
| Per-flow inference latency (defender-a) | 17.47 us | tools/benchmark_inference_latency.py |
| FL weight payload per round | 294.5 KB | baseline_coldstart_100r.yaml |
