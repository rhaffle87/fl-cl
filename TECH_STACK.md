# Tech Stack — FL-CL Cyber Defense Lab

Complete technology inventory organized by system layer. Each entry specifies the technology, its version requirement, where it runs, what it does, and the install command.

---

## Layer 1: Hypervisor (PVE Host Nodes)

These run directly on the bare-metal Proxmox VE hosts (`its`, `node2` - Dell PowerEdge R630; `pve` - Dell PowerEdge R760xs).

| Technology | Version | Purpose | Install / Enable |
| :--- | :--- | :--- | :--- |
| **Proxmox VE** | 8.x | Type-1 hypervisor for VM/CT management | Pre-installed on bare metal |
| **Linux Bridge (`vmbr0`, `vmbr1`)** | Kernel built-in | Virtual network switching between VMs | Configured in `/etc/network/interfaces` |
| **Flat L2 Subnetting** | Kernel module / IP Routing | Logical subnets on flat L2 vmbr1 to bypass switch VLAN constraints | Subnet mask /16 (`10.10.0.0/16`) on vmbr1 |
| **LACP Bond (`bond0`)** | Kernel module | Link aggregation on nodes `its` and `node2` | Configured in `/etc/network/interfaces` |
| **tc (Traffic Control)** | iproute2 | Port mirroring — copies target VM traffic to defender capture interface | `apt install iproute2` (pre-installed) |
| **Proxmox Hookscripts** | PVE built-in | Auto-execute scripts on VM lifecycle events (post-start) | `pvesm set local --content ...,snippets` |
| **LVM-Thin** | lvm2 | Thin-provisioned storage with fast snapshot/rollback | PVE default storage layout |
| **Corosync** | 3.x | Cluster quorum and node health | Pre-installed with PVE |
| **ifupdown2** | 0.x | Hot-reload network config without reboot | `apt install ifupdown2` |
| **Dell PERC H755 / H730** | Firmware | Hardware RAID controllers | Hardware — no software install |

---

## Layer 2: Guest Operating Systems

| VM/CT | OS | Version | Purpose |
| :--- | :--- | :--- | :--- |
| LXC 300 (`fl-aggregator`) | Ubuntu Server | 24.04 LTS | Lightweight container for FL server + MLflow |
| VM 310 (`defender-a`) | Ubuntu Server | 24.04 LTS | Full VM for GPU passthrough + ML training |
| VM 320 (`defender-b`) | Ubuntu Server | 24.04 LTS | Full VM for parallel defender |
| VM 311 (`target-a1`) | Alpine Linux | 3.20 | Minimal OS as attack/traffic target |
| VM 321 (`target-b1`) | Alpine Linux | 3.20 | Minimal OS as attack/traffic target |
| VM 400 (`traffic-gen`) | Kali Linux | 2024.4 | Pre-loaded with offensive security tools |

---

## Layer 3: Networking & Communication Protocols

| Technology | Purpose | Where |
| :--- | :--- | :--- |
| **Subnet Zone A** (10.10.110.0/16) | Organization A logical subnet | VM 310, VM 311 |
| **Subnet Zone B** (10.10.120.0/16) | Organization B logical subnet | VM 320, VM 321 |
| **Subnet Zone FL** (10.10.130.0/16) | FL Aggregation logical subnet | LXC 300 |
| **Subnet Zone Traffic** (10.10.140.0/16) | Traffic generation logical subnet | VM 400 |
| **gRPC over TLS** | FL weight sync (Flower protocol) | Defenders ↔ Aggregator |
| **TCP/8080** | Flower server port | LXC 300 |
| **TCP/5000** | MLflow tracking UI | LXC 300 |
| **TCP/6006** | TensorBoard UI | VM 310, VM 320 |

---

## Layer 4: Python ML / Continual Learning Stack (Defender VMs)

These packages run inside VM 310 and VM 320.

| Package | Version | Purpose | Install |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11+ | Runtime environment | `apt install python3 python3-venv` |
| **PyTorch** | 2.x | Deep learning backbone (`CyberDefenseCNN`, `CyberDefenseNet`, `CyberDefenseTransformer`) | `pip install torch --index-url .../cpu` |
| **TorchScript** | 2.x | JIT-compiled dynamic computation graph for low-latency inference | Built into PyTorch |
| **ONNX Runtime** | 1.19+ | High-throughput CPU inference engine (AVX2/AVX-512 SIMD acceleration) | `pip install onnxruntime` |
| **Avalanche** | 0.5+ | Continual Learning library (EWC with class-weighted loss and GEM projection) | `pip install avalanche-lib` |
| **Flower (flwr)** | 1.x | Federated Learning client lifecycle | `pip install flwr` |
| **Opacus** | 1.x | Client-side Differential Privacy (DP-SGD gradient clipping and noise injection) | `pip install opacus` |
| **NFStream** | 6.x | Encrypted traffic feature extraction (SPLT, PIAT, JA3/JA4 flow statistics) | `pip install nfstream` |
| **scikit-learn** | 1.x | StandardScaler, classification metrics (F1, precision, recall) | `pip install scikit-learn` |
| **pandas** | 2.x | High-speed vectorized DataFrame operations for flow records | `pip install pandas` |
| **numpy** | 1.x / 2.x | Multi-dimensional numerical array computation | `pip install numpy` |
| **libpcap** | System lib | Packet capture backend for NFStream | `apt install libpcap-dev` |
| **tcpdump** | System tool | Verify mirrored traffic on capture interface | `apt install tcpdump` |

---

## Layer 5: Python Aggregator Stack (LXC 300)

| Package | Version | Purpose | Install |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11+ | Runtime environment | `apt install python3 python3-venv` |
| **Flower (flwr)** | 1.x | Federated Learning server (`FedAvg`, `TrimmedMean`, `FedMedian`, `Krum`) | `pip install flwr` |
| **MLflow** | 3.x | Centralized experiment tracking, metric logging, LoggedModel entities | `pip install mlflow` |
| **matplotlib** | 3.x | Headless rendering of per-round evaluation confusion matrix heatmaps | `pip install matplotlib` |

---

## Layer 6: Traffic Generation Stack (VM 400 — Kali Linux)

| Tool | Purpose | Engine Mode | Install |
| :--- | :--- | :--- | :--- |
| **attack_flow.py** | Modular threat scenario simulator | `--engine auto\|kali\|python` | Native Python script |
| **Hydra** | High-speed SSH authentication brute-forcing | Kali Engine | `apt install hydra` |
| **Ncrack** | Network authentication cracking tool for SSH services | Kali Engine | `apt install ncrack` |
| **Medusa** | Parallel modular login brute-forcer | Kali Engine | `apt install medusa` |
| **SlowHTTPTest** | Application-layer Slowloris / Slow POST DoS tool | Kali Engine | `apt install slowhttptest` |
| **hping3** | TCP/UDP volumetric flood and SYN flood simulator | Kali Engine | `apt install hping3` |
| **Slowloris** | Python keep-alive socket DoS simulator | Python Engine | `pip install slowloris` |
| **Scapy** | Custom packet crafting for high-entropy DNS exfiltration and C2 beaconing | Kali / Python | `pip install scapy` |
| **Iodine** | IPv4 DNS tunneling and data exfiltration utility | Kali Engine | `apt install iodine` |
| **Metasploit Framework** | C2 beaconing and reverse HTTPS shell simulation | Kali Engine | Pre-installed on Kali |
| **tcpreplay** | Replay benchmark PCAP datasets over flat L2 bridge | Replay Mode | `apt install tcpreplay` |
| **Selenium / Chromium** | Headless browser for realistic benign HTTPS web browsing | Benign Mode | `pip install selenium` |
| **Locust** | High-volume concurrent HTTP/HTTPS load generation | Benign Mode | `pip install locust` |

---

## Layer 7: Benchmark Datasets

| Dataset | Content | Use Case |
| :--- | :--- | :--- |
| **USTC-TFC2016** | 10 malware + 10 benign encrypted traffic classes | Multi-class baseline training |
| **CIC-IDS2017** | Multi-day captures with DoS, DDoS, brute force labels | CL task sequencing across temporal sessions |
| **CIC-IDS2018** | Extended version with additional attack scenarios | Supplementary CL tasks |
| **CIRA-CIC-DoHBrw-2020** | DNS-over-HTTPS exfiltration vs. benign DoH | Advanced encrypted channel detection |

---

## Layer 8: I/O & Storage Optimization

| Technology | Purpose | Where |
| :--- | :--- | :--- |
| **tmpfs RAM Disk** (4 GB) | Buffer NFStream flow writes to eliminate disk I/O contention | Inside VM 310, VM 320 at `/mnt/ramdisk` |
| **LVM-Thin Snapshots** | Fast VM checkpoint and rollback for experiment reproducibility | PVE host storage pool (`local-lvm`) |
| **CSV Storage** | Tabular format for batched flow records | `/mnt/ramdisk/flows/*.csv` |

---

## Layer 9: MLOps, CI/CD & Observability

| Tool | Purpose | Where | Port |
| :--- | :--- | :--- | :--- |
| **MLflow** | Centralized experiment tracking (loss, accuracy, BWT, confusion matrices) | LXC 300 | 5000 |
| **TensorBoard** | Weight distributions, gradient norms, activation statistics | VM 310, VM 320 | 6006 |
| **Ollama** | Local LLM inference engine for threat reports (`llama3.1:8b`) | LXC / Tailscale Node | 11435 |
| **Nginx Reverse Proxy** | Dual-key authenticated endpoint proxying local Ollama APIs | Tailscale Node | 443 / 80 |
| **Model Promotion Gate** | Automated CI/CD promotion evaluating recall, latency, and drift | `tools/validate_promotion.py` | Local / Remote |

---

## Layer 10: Standards & Statutory Compliance Stack

| Framework / Standard | Governance Layer | Verified Implementation |
| :--- | :--- | :--- |
| **UU PDP No. 27/2022** *(Art. 65–66)* | Statutory Privacy Law | Zero raw flow transfer; strictly local feature extraction on tmpfs RAMDisk. |
| **GDPR (EU 2016/679)** *(Art. 5, 25, 32)* | Statutory Privacy Law | DP-SGD ($\sigma=0.30, C=1.0$) with Moments Accountant $(\epsilon=6.08, \delta=10^{-5})$. |
| **NIST SP 800-94 / 800-145** | Cybersecurity Standard | 32-dimensional behavioral flow telemetry without payload inspection. |
| **MITRE ATT&CK Enterprise** | Threat Classification | T1498 (DoS), T1110 (BruteForce), T1048 (DNS Exfiltration), T1071 (C2 Beaconing). |
| **ISO/IEC 27001 / 27701** | ISMS / PIMS Management | SHA-256 dataset lineage graphs, Git commit tagging, and audit trail validation. |
| **RFC 1035 / 793 / 7230** | Wire Protocol Standard | Compliant DNS datagram formatting, TCP state handling, and HTTP/1.1 transports. |
