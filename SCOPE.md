# FL-CL Project Scope & Boundary Specification

> **Document Status**: Authoritative Reference & Anti-Scope-Creep Baseline  
> **Academic Context**: Undergraduate Thesis in Telecommunications Engineering  
> **Author**: Rafli Alif Ihza Hartono  
> **Department**: Department of Electrical Engineering, Faculty of Intelligent Electrical and Informatics Technology (F-ELECTICS)  
> **Institution**: Institut Teknologi Sepuluh Nopember (ITS), Surabaya, Indonesia  
> **Repository**: `rhaffle87/fl-cl`

---

## 1. Executive Summary & Purpose

This document establishes the **formal boundaries, claim space, and non-goals** of the `fl-cl` project. It serves as the primary safeguard against **scope creep**, ensuring that all engineering efforts, experiment designs, tooling, and documentation directly support the undergraduate thesis:

> **Thesis Title**: *Hybrid Federated-Continual Learning for Collaborative Cyber Defense on Encrypted Networks: A Systematic End-to-End Architecture on Heterogeneous Proxmox Clusters*

Any proposed feature, script, dataset ingestion, or architectural modification must satisfy the criteria defined in this document. If a proposed task does not directly advance the 4 core claims or 6 architectural dimensions, it is classified as **out-of-scope** and must not be implemented.

---

## 2. The 4 Bounded Research Claims (Claim Space)

As codified in [`docs/10_arguments.md`](docs/10_arguments.md) and [`docs/paper/research_paper.md`](docs/paper/research_paper.md), this research makes exactly **four empirically bounded, scope-limited claims**:

| Claim | What It Claims (In-Scope) | What It Explicitly Does NOT Claim (Out-of-Scope) |
| :--- | :--- | :--- |
| **C1: Forgetting Resistance** | Class-weighted Elastic Weight Consolidation (EWC) and Gradient Episodic Memory (GEM/A-GEM) prevent minority-class recall collapse (specifically Botnet $BWT$) under non-stationary sequential traffic streams. | Does NOT claim EWC alone is universally sufficient without class-weighting or replay; does NOT claim unconstrained lifelong adaptation across infinite open-ended tasks without capacity limits. |
| **C2: Collaborative Privacy** | Federated Learning (Flower over gRPC) transmits only model parameter weights ($\theta$), preventing raw network packet captures (PCAPs) from traversing organizational boundaries; complemented by batch-level DP-SGD ($\sigma \le 0.20, C=1.0$). | Does NOT claim cryptographic security equivalent to Secure Multi-Party Computation (SMPC) or Fully Homomorphic Encryption (FHE); does NOT claim immunity to theoretical white-box gradient reconstruction attacks in multi-party collusion. |
| **C3: Byzantine Robustness** | Robust aggregation algorithms (TrimmedMean $\beta=0.1$, FedMedian, Krum) isolate parameter deviations and neutralize up to 20% local training data label poisoning on edge defender nodes. | Does NOT claim resilience against $>33\%$ Byzantine compromised clients in a federation; does NOT claim Byzantine guarantees when $K < 2f + 1$ without fallback aggregation (e.g. FedMedian). |
| **C4: Encrypted Traffic Detection** | 32-dimensional NFStream flow metadata (TLS handshake fingerprints JA3/JA4, packet timing SPLT/PIAT, byte ratios, TCP flags) classifies 5 threat classes without payload decryption. | Does NOT claim open-world zero-day discovery, payload decryption, deep packet inspection (DPI), or Advanced Persistent Threat (APT) actor attribution. |

---

## 3. Threat Model & Classification Taxonomy

### 3.1 Canonical 5-Class Threat Model (Strictly Bounded)
The project is strictly scoped as an **Encrypted Traffic Flow Classifier** operating on 5 canonical classes mapped to the MITRE ATT&CK framework:

| Class ID | Class Name | MITRE ATT&CK Mapping | Behavioral Signature & Detection Mechanism | Penalty Weight ($w_c$) |
| :---: | :--- | :--- | :--- | :---: |
| **0** | **Normal** | N/A | Benign HTTPS browsing, API telemetry, legitimate SSH sessions. | `1.0` |
| **1** | **Botnet** | `T1071` (Standard App Layer Protocol) | Periodic C2 beaconing with randomized timing jitter on ports 8080/8888/9000 (Ares/Mirai profile). | `250.0` |
| **2** | **Exfiltration** | `T1048` (Exfil Over Alternative Protocol) | High-entropy DNS TXT queries tunneling data over port 53 / DoH channels. | `2.0` |
| **3** | **BruteForce** | `T1110` (Brute Force) | High-frequency, small-packet SSH/FTP authentication bursts on ports 22/21. | `5.0` |
| **4** | **DoS** | `T1498` (Network Denial of Service) | Low-and-slow Slowloris connection exhaustion on port 80/443; volumetric TCP/UDP floods. | `50.0` |

### 3.2 Out-of-Distribution (OOD) Fallback Boundary
* **In-Scope**: Energy-based Out-of-Distribution scoring ($E(x; T) = -T \log \sum_c \exp(f_c(x)/T)$) used strictly as an anomalous traffic gate to flag unmodeled traffic for quarantine.
* **Out-of-Scope**: Multi-class classification of novel zero-day attacks into new dynamic classes during production runtime.

---

## 4. Data & Traffic Strategy Scope

### 4.1 In-Scope Data Strategy
The research relies on a **dual-source data strategy** feeding the 32-dimensional ETA pipeline:
1. **Live Physical Cluster Generation (`VM 400`)**:
   - Offensive attack generation via `src/traffic_gen/attack_flow.py` and standard security tools (Hydra, Slowloris, Python raw sockets, DNS exfiltration).
   - Benign background traffic generation (Selenium, curl loops).
2. **Standard Benchmark Dataset Replay (`tcpreplay`)**:
   - **`CIC-IDS2017`**: Baseline for multi-day temporal Continual Learning task sequencing (Monday through Friday captures).
   - **`USTC-TFC2016`**: Baseline for encrypted malware vs. benign application flow verification.
3. **In-Memory RAMDisk Pipeline**:
   - `NFStream` feature extraction (`src/defender/extractor.py`) capturing live on `ens19` and serializing 32-dim flow records to volatile tmpfs (`/mnt/ramdisk/flows/`).

### 4.2 Explicit Non-Goals & Out-of-Scope Data Work
> [!WARNING]
> **Anti-Scope-Creep Mandate**:
> - **NO Generic Multi-Dataset Data Platforms**: Building an open-ended, universal ETL ingestion platform to parse arbitrary external datasets (e.g. UNSW-NB15, TON_IoT, BoT-IoT, NSL-KDD, Edge-IIoTset) is **OUT OF SCOPE**.
> - **NO Changing the 5-Class Taxonomy**: The neural architectures and loss functions are mathematically formulated for $C=5$. Expanding $C$ to 10, 20, or arbitrary numbers is outside the thesis scope.
> - **NO Payload Re-Inspection**: Raw packet payload analysis, DPI, or regex string matching is strictly forbidden. All features must be flow metadata.

---

## 5. Hardware, Infrastructure & Testbed Scope

### 5.1 Physical Cluster Hardware (Fixed Boundary)
The physical testbed is deployed across a 3-node enterprise Proxmox VE cluster:
* **Node `its`** (Dell PowerEdge R630, 2x Intel Xeon E5-2650 v4, 64 GB RAM): Hosts Aggregator (`LXC 300`), Defender A (`VM 310`), Target A (`VM 311`).
* **Node `node2`** (Dell PowerEdge R630, 2x Intel Xeon E5-2680 v3, 64 GB RAM): Hosts Defender B (`VM 320`), Target B (`VM 321`).
* **Node `pve`** (Dell PowerEdge R760xs, Intel Xeon Silver 4410Y, 64 GB RAM): Hosts Traffic Generator (`VM 400`).

### 5.2 Network & Mirroring Workaround (Core Infrastructure Artifact)
* **Flat Layer-2 Network**: Bridges `vmbr0` (management `10.10.130.0/24`) and `vmbr1` (capture VLANs `10.10.110.0/24`, `10.10.120.0/24`, `10.10.140.0/24`).
* **Hookscript Port Mirroring**: Perl hookscript (`infra/pve-portmirror-hookscript.pl`) managing ephemeral TAP interfaces on VM boot/shutdown.

### 5.3 Federation Scale Boundary
* **Physical Testbed**: Bounded to **$K=2$ defender clients** (`defender-a`, `defender-b`).
* **Simulation Benchmark**: Bounded to **$N=5$ simulated clients** for Byzantine tolerance verification (`tools/benchmark_byzantine.py`).
* **Out-of-Scope**: Scaling to massive multi-tenant federations ($K \ge 50$), mobile device federations, or cross-cloud WAN meshes.

---

## 6. Software Architecture & Model Scope

### 6.1 Neural Backbones (`src/defender/model.py`)
Exactly three architectures are evaluated to assess the accuracy-latency tradeoff:
1. **1D-CNN (`CyberDefenseCNN`)**: Champion architecture; feature extraction via 1D convolutions with dynamic FC dimension calculation.
2. **MLP (`CyberDefenseNet`)**: Lightweight baseline feedforward network.
3. **Transformer (`CyberDefenseTransformer`)**: Tabular self-attention encoder (`token_len=4, token_dim=8, input_dim=32`).

*Out-of-Scope*: Recurrent networks (RNN/LSTM/GRU), graph neural networks (GNN), or generative diffusion/LLM architectures.

### 6.2 Continual Learning Suite (`src/defender/cl_strategy.py`)
1. **Class-Weighted EWC**: Fisher Information Matrix weighted by inverse class frequency to resolve Botnet collapse ($F_{\text{Botnet}} \approx 0$).
2. **GEM / A-GEM**: Episodic memory replay buffer ($P=256\text{–}512, \gamma=0.2\text{–}0.5$) guaranteeing non-negative backward transfer ($BWT \ge 0$).

### 6.3 Federated Aggregation Suite (`src/aggregator/server.py`)
1. **FedAvg**: Baseline weighted parameter averaging.
2. **TrimmedMean**: Byzantine-robust coordinate-wise trimming ($\beta=0.1$).
3. **FedMedian**: Median aggregation fallback for $K=2$ physical nodes.
4. **Krum**: Multi-client distance-based outlier rejection.

### 6.4 Edge Inference Optimization (`tools/`)
* Model compilation via **TorchScript JIT** and **ONNX Runtime** (CPU execution provider).
* Post-training dynamic **INT8 quantization** (`torch.ao.quantization`).
* *Out-of-Scope*: Custom CUDA kernel authoring, ASIC/FPGA synthesis, or proprietary edge hardware runtimes (TensorRT, EdgeTPU).

---

## 7. MLOps, Governance & Tooling Scope

1. **ADR-006 Tooling Taxonomy**:
   - All tools in `tools/` must strictly follow the prefix conventions: `audit_`, `benchmark_`, `check_`, `deploy_`, `export_`, `generate_`, `plot_`, `test_`, `train_`, `validate_`.
2. **Centralized Configuration**:
   - All experiments are driven by declarative YAML configs in `configs/` (`configs/experiment.yaml`, `configs/experiments/*.yaml`, `configs/sweeps/*.yaml`).
3. **Observability**:
   - MLflow tracking server on Aggregator (`http://10.10.130.10:5000`).
   - Telegram operational alerting (`src/notifications.py`).
4. **Single Orchestration Pipeline**:
   - Master orchestrator is [`src/orchestrate.py`](src/orchestrate.py), coordinated with [`src/sweep.py`](src/sweep.py) for hyperparameter sweeps.
   - *Anti-Scope Creep*: Do NOT create duplicate orchestrators or parallel experiment engines that bypass `src/orchestrate.py`.

---

## 8. Anti-Scope-Creep Decision Matrix (Gatekeeper)

Before undertaking any development, benchmark, or documentation change, apply this 5-point test:

```text
[ ] 1. Does this directly support one of the 4 Bounded Claims (C1–C4)?
[ ] 2. Does this operate strictly within the 5-Class Threat Model?
[ ] 3. Does this utilize the canonical 32-dimensional ETA feature schema?
[ ] 4. Does this deploy onto or directly simulate the 3-node Proxmox testbed?
[ ] 5. Does this comply with ADR-006 and integrate with existing configs/ and src/?
```

* **If ALL 5 are YES**: The task is **IN-SCOPE**. Proceed with implementation.
* **If ANY is NO**: The task is **OUT-OF-SCOPE** (Scope Creep). Reject or re-scope immediately.

---

## 9. Alignment of Current Repository Assets

| Component | Status | Scope Alignment Rationale |
| :--- | :---: | :--- |
| `src/orchestrate.py` | **Core** | Central orchestrator for the 3-node Proxmox cluster; runs live campaigns and logs to MLflow. |
| `src/sweep.py` | **Core** | Multi-run grid sweep controller testing the 6 architectural dimensions. |
| `src/defender/` | **Core** | Implements the 3 neural backbones, class-weighted EWC, GEM, and NFStream flow extraction. |
| `src/aggregator/` | **Core** | Implements Flower FL server, robust aggregators (TrimmedMean, FedMedian), and dashboard. |
| `configs/experiments/`| **Core** | 17 pre-validated YAML configurations representing all thesis benchmarks. |
| `tools/` | **Core** | 46 ADR-006 compliant diagnostic, evaluation, and plotting utilities. |
| `datasets/CIC-IDS2017`| **Bounded**| Offline replay baseline for temporal continual learning task progression. |
| `datasets/USTC-TFC2016`| **Bounded**| Offline replay baseline for encrypted malware classification. |
| `datasets/UNSW, TON, CSE`| **Reference**| Historical/reference data. Ingesting these into a generic platform is **OUT-OF-SCOPE**. |
