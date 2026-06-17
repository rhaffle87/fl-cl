# Prerequisites & Lab Preparation Guide: FL-CL Cyber Defense

> **Role in the documentation set**: This document specifies the hardware, network equipment, benchmark datasets, traffic generation tools, and MLOps environment required *before* deploying the testbed. For the conceptual architecture these prerequisites support, see [research_architecture.md](research_architecture.md). For the cluster-specific deployment steps, see [workaround_specs.md](workaround_specs.md). For the fully integrated research paper, see [fl_cl_research_paper.md](fl_cl_research_paper.md) (this document corresponds to Paper Chapter 3 Section 3.1, Chapter 5 Section 5.1, and Chapter 8 Section 8.3).

---

## 1. Hardware & System Requirements

The testbed runs across a 3-node Proxmox VE cluster hosting 6 VMs/LXCs totaling ~26 vCPUs, 46 GB RAM, and 320 GB disk. Your hardware choices determine the complexity of models you can train and the fidelity of traffic capture.

### A. Compute & Acceleration (CPU/GPU)
*   **GPU Passthrough (Recommended):** Deep learning models used for Encrypted Traffic Analysis—particularly 1D-CNNs or LSTMs applied to SPLT (Sequence of Packet Lengths and Times) features—train significantly faster on GPUs.
    *   **Action:** Allocate a consumer GPU (e.g., NVIDIA RTX 3060/4060 or Tesla T4/P4) for PCIe passthrough to one of the defender VMs. Configure `vfio` drivers on the PVE host. The workload placement in [workaround_specs.md](workaround_specs.md) Section 2 allocates Defender A (VM 100) to node `its`, which is the recommended GPU passthrough host.
*   **RAM Capacity:**
    *   **Minimum:** 32 GB per node (PVE overhead + VM allocations).
    *   **Recommended:** 64 GB+ per node. Each defender VM requires 16 GB to load large network flow datasets into PyTorch memory during training.
*   **Storage Speed (SSD/NVMe):**
    *   Continuous flow extraction via NFStream (see [research_architecture.md](research_architecture.md) Section 4) and model checkpointing create sustained disk I/O. **Do not use HDDs.** Use NVMe SSDs or SSD arrays behind the RAID controller (Dell PERC H755 on the current cluster). The RAM disk buffer described in [workaround_specs.md](workaround_specs.md) Section 3.B further mitigates I/O contention.

---

## 2. Network Infrastructure (Physical Lab Integration)

The testbed operates entirely within virtualized Proxmox networks by default. However, if you plan to capture and defend against *real* physical network traffic (extending beyond synthetic VM-generated flows):

*   **Managed Network Switch:** A switch supporting **L2 Managed Port Mirroring / SPAN** and **802.1Q VLANs** (e.g., Ubiquiti UniFi, TP-Link JetStream, or Cisco Catalyst). This mirrors traffic from physical devices into a dedicated NIC on the Proxmox server, complementing the virtual `tc`-based port mirroring described in [research_architecture.md](research_architecture.md) Section 3.
*   **Multi-Port NIC on PVE Server:** An Intel-based dual-port or quad-port Gigabit Ethernet PCIe card (e.g., Intel i350-T4) configured in bridged mode, providing dedicated physical interfaces for each VLAN. The current cluster uses LACP-bonded interfaces (`bond0`) on nodes `its` and `node2`; see [workaround_specs.md](workaround_specs.md) Section 1.C for bridge reconciliation details.
*   **Hardware TAP (Optional):** An inline network TAP (e.g., Throwing Star LAN Tap or Dualcomm) for passive capture between router and modem without requiring switch-level SPAN configuration.

---

## 3. Data Collections & Replay Datasets

Training an AI-based intrusion detection system requires labeled network traffic. The testbed supports two data strategies: offline benchmark replay and live synthetic generation (Section 4). Both feed into the NFStream ETA pipeline described in [research_architecture.md](research_architecture.md) Section 4. *(Paper: Chapter 5, Section 5.1A)*

### Standard Encrypted Traffic Datasets
*   **USTC-TFC2016:** 10 categories of encrypted malware traffic and 10 categories of benign traffic. Provides the foundational multi-class classification baseline for the 5-class model defined in [research_architecture.md](research_architecture.md) Section 5.1.
*   **CIC-IDS2017 / CIC-IDS2018:** Raw PCAP captures of multi-day network activity with structured labels for DoS, DDoS, brute force, and web attacks. The temporal span across multiple days enables realistic Continual Learning task sequencing—each day's traffic can constitute a distinct CL task that exercises the EWC anti-forgetting mechanism.
*   **CIRA-CIC-DoHBrw-2020:** Specialized dataset focusing on DNS-over-HTTPS (DoH) exfiltration—a particularly challenging encrypted channel where the malicious payload is indistinguishable from standard HTTPS at the packet level, requiring flow-level statistical analysis.

### Traffic Replay Tooling
Download these datasets as PCAPs and replay them on the traffic generator VM (VM 400) using:
*   **`tcpreplay`**: Replays PCAPs at configurable speeds over the virtual bridge interface, allowing defender nodes to process labeled attack traffic in real-time.
*   **`tcprewrite`**: Rewrites source/destination IPs and MACs in PCAPs to match the testbed's VLAN addressing scheme before replay.

Example replay command on VM 400:
```bash
tcpreplay --intf1=eth0 --multiplier=2.0 --loop=5 /datasets/CIC-IDS2017-Friday.pcap
```

Each replayed dataset constitutes a CL task. By replaying CIC-IDS2017 (brute force) first, then USTC-TFC2016 (malware), then CIRA-CIC-DoHBrw-2020 (DoH exfiltration), the testbed creates the sequential, non-stationary data stream that the Avalanche EWC strategy is designed to handle.

---

## 4. Traffic Generation & Simulation Engines

For generating custom, real-time threat flows and benign background noise that complement the benchmark dataset replays. These tools run on the traffic generator VM (VM 400) and target VMs (VM 101, 201). *(Paper: Chapter 5, Section 5.1B)*

### Benign Background Traffic Generators
*   **Locust / Wrk:** Generate high-throughput HTTP/HTTPS load against target VMs, producing realistic TLS flow metadata with varied request patterns.
*   **Selenium / Puppeteer (Headless Browsers):** Scripts running inside target VMs (VM 101, VM 201) that mimic human browsing behavior—search queries, streaming, social media—generating realistic TLS flow metadata with natural timing jitter and varied JA3 fingerprints.

### Attack Frameworks
*   **Hydra:** SSH brute-force tool generating rapid, small-packet authentication flows with distinctive SPLT signatures.
*   **Slowloris / hping3:** HTTP/HTTPS flood tools creating long-held connection patterns distinguishable by flow duration and packet-count ratios.
*   **Metasploit / Cobalt Strike / Sliver:** C2 frameworks generating encrypted reverse-shell or HTTPS beaconing profiles. These produce periodic, regular-interval encrypted callbacks with characteristic JA3 fingerprints that the ETA pipeline can learn to detect.
*   **T-Rex (Cisco):** Stateful and stateless packet generator for high-volume L4–L7 encrypted stream generation at scale.

### Attack-to-CL-Task Mapping

Each attack campaign constitutes a distinct Continual Learning task. The recommended task sequence:

| Task Order | Attack Type | Tool | CL Purpose |
|:---|:---|:---|:---|
| Task 1 | SSH Brute Force | Hydra | Baseline detection training |
| Task 2 | HTTPS C2 Beaconing | Metasploit | Test adaptation without forgetting Task 1 |
| Task 3 | DoH Exfiltration | Custom scripts / CIRA dataset | Test retention of Tasks 1–2 under new distribution |
| Task 4 | DDoS Flood | hping3 / T-Rex | Stress-test EWC under high-volume non-stationary input |

---

## 5. Software Stack & MLOps Environment

### A. Python Environment
Set up a standardized virtual environment (`venv`) across all defender nodes and the aggregator. The dependency stack aligns with the code components in [research_architecture.md](research_architecture.md) Section 5:

```bash
# Deep learning framework (model.py)
pip install torch torchvision torchaudio

# Continual learning suite (cl_strategy.py)
pip install avalanche-lib

# Federated learning framework (client.py, server.py)
pip install flwr

# Feature extraction from encrypted traffic (extractor.py)
pip install nfstream

# Data engineering & evaluation
pip install scikit-learn pandas numpy
```

For detailed installation steps inside each VM, see [workaround_specs.md](workaround_specs.md) Section 4, Phase 4.

### B. MLOps & Experiment Tracking
In a federated-continual learning environment, tracking model checkpoints, task drift, and per-node validation accuracies is essential for evaluating the system's resistance to catastrophic forgetting. *(Paper: Chapter 8, Section 8.3)*

*   **MLflow:** Deploy a local MLflow tracking server on the aggregator LXC (LXC 300). Each defender VM logs per-round metrics (loss, accuracy per task, Backward Transfer) to the central server, enabling side-by-side comparison of forgetting curves across organizations.
    ```bash
    # On aggregator (LXC 300):
    pip install mlflow
    mlflow server --host 0.0.0.0 --port 5000
    ```
*   **Weights & Biases (W&B):** Alternative cloud-hosted tracker for teams preferring managed infrastructure. Particularly useful for visualizing how Defender A's accuracy on Task 1 (SSH brute-force) changes when Defender B introduces Task 2 (C2 beaconing) through federated aggregation.
*   **TensorBoard:** Standard local visualizer for monitoring weight distributions, gradient norms, and per-layer activation statistics during CL training.
    ```bash
    pip install tensorboard
    tensorboard --logdir ~/fl-cl-env/runs/ --port 6006
    ```

The observability stack closes the feedback loop: metrics inform tuning decisions (e.g., adjusting `ewc_lambda` in [research_architecture.md](research_architecture.md) Section 5.2, modifying aggregation frequency in Section 5.4, or rebalancing traffic ratios in this document's Section 4).
