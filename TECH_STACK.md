# Tech Stack — FL-CL Cyber Defense Lab

Complete technology inventory organized by system layer. Each entry specifies the technology, its version requirement, where it runs, what it does, and the install command.

---

## Layer 1: Hypervisor (PVE Host Nodes)

These run directly on the bare-metal Proxmox VE hosts (`its`, `node2`, `pve`).

| Technology | Version | Purpose | Install / Enable |
|:---|:---|:---|:---|
| **Proxmox VE** | 8.x | Type-1 hypervisor for VM/CT management | Pre-installed on bare metal |
| **Linux Bridge (`vmbr0`, `vmbr1`)** | Kernel built-in | Virtual network switching between VMs | Configured in `/etc/network/interfaces` |
| **802.1Q VLAN Tagging** | Kernel module | Isolate organizational networks (VLAN 10/20/30/40) | `bridge-vlan-aware yes` in `/etc/network/interfaces` |
| **LACP Bond (`bond0`)** | Kernel module | Link aggregation on nodes `its` and `node2` | Configured in `/etc/network/interfaces` |
| **tc (Traffic Control)** | iproute2 | Port mirroring — copies target VM traffic to defender capture interface | `apt install iproute2` (pre-installed) |
| **Proxmox Hookscripts** | PVE built-in | Auto-execute scripts on VM lifecycle events (post-start) | `pvesm set local --content ...,snippets` |
| **LVM-Thin** | lvm2 | Thin-provisioned storage with fast snapshot/rollback | PVE default storage layout |
| **Corosync** | 3.x | Cluster quorum and node health | Pre-installed with PVE |
| **ifupdown2** | 0.x | Hot-reload network config without reboot | `apt install ifupdown2` |
| **Dell PERC H755** | Firmware | Hardware RAID controller (1.20 TB logical volume) | Hardware — no software install |

---

## Layer 2: Guest Operating Systems

| VM/CT | OS | Version | Purpose |
|:---|:---|:---|:---|
| LXC 300 (`fl-aggregator`) | Ubuntu Server | 24.04 LTS | Lightweight container for FL server + MLflow |
| VM 100 (`defender-a`) | Ubuntu Server | 24.04 LTS | Full VM for GPU passthrough + ML training |
| VM 200 (`defender-b`) | Ubuntu Server | 24.04 LTS | Full VM for parallel defender |
| VM 101 (`target-a1`) | Alpine Linux | 3.20 | Minimal OS as attack/traffic target |
| VM 201 (`target-b1`) | Alpine Linux | 3.20 | Minimal OS as attack/traffic target |
| VM 400 (`traffic-gen`) | Kali Linux | 2024.2 | Pre-loaded with offensive security tools |

---

## Layer 3: Networking

| Technology | Purpose | Where |
|:---|:---|:---|
| **VLAN 10** (10.10.10.0/24) | Organization A network | VM 100, VM 101 |
| **VLAN 20** (10.10.20.0/24) | Organization B network | VM 200, VM 201 |
| **VLAN 30** (10.10.30.0/24) | FL Aggregation zone | LXC 300 |
| **VLAN 40** (10.10.40.0/24) | Traffic generation zone | VM 400 |
| **gRPC over TLS** | FL weight sync (Flower protocol) | Defenders ↔ Aggregator |
| **TCP/8080** | Flower server port | LXC 300 |
| **TCP/5000** | MLflow tracking UI | LXC 300 |
| **TCP/6006** | TensorBoard UI | VM 100, VM 200 |

---

## Layer 4: Python ML/FL-CL Stack (Defender VMs)

These packages run inside VM 100 and VM 200.

| Package | Version | Purpose | Install |
|:---|:---|:---|:---|
| **Python** | 3.11+ | Runtime | `apt install python3 python3-venv` |
| **PyTorch** | 2.x | Deep learning framework (CyberDefenseNet MLP) | `pip install torch --index-url .../cpu` |
| **Avalanche** | 0.5+ | Continual Learning library (EWC strategy) | `pip install avalanche-lib` |
| **Flower (flwr)** | 1.x | Federated Learning client | `pip install flwr` |
| **NFStream** | 6.x | Encrypted traffic feature extraction (JA3, flow stats) | `pip install nfstream` |
| **scikit-learn** | 1.x | StandardScaler, metrics (F1, precision, recall) | `pip install scikit-learn` |
| **pandas** | 2.x | DataFrame operations for flow records | `pip install pandas` |
| **numpy** | 1.x | Numerical arrays | `pip install numpy` |
| **TensorBoard** | 2.x | Training visualization | `pip install tensorboard` |
| **libpcap** | System lib | Packet capture backend for NFStream | `apt install libpcap-dev` |
| **tcpdump** | System tool | Verify mirrored traffic on capture interface | `apt install tcpdump` |

---

## Layer 5: Python Aggregator Stack (LXC 300)

| Package | Version | Purpose | Install |
|:---|:---|:---|:---|
| **Python** | 3.11+ | Runtime | `apt install python3 python3-venv` |
| **Flower (flwr)** | 1.x | Federated Learning server (FedAvg) | `pip install flwr` |
| **MLflow** | 2.x | Experiment tracking, metric logging | `pip install mlflow` |

---

## Layer 6: Traffic Generation Stack (VM 400 — Kali Linux)

| Tool | Purpose | Install |
|:---|:---|:---|
| **Metasploit Framework** | C2 beaconing, reverse HTTPS shells | Pre-installed on Kali |
| **Hydra** | SSH/RDP brute-force attacks | `apt install hydra` |
| **hping3** | TCP/UDP flood, DDoS simulation | `apt install hping3` |
| **Slowloris** | HTTP slow-connection DoS | `pip install slowloris` |
| **tcpreplay** | Replay benchmark PCAP datasets | `apt install tcpreplay` |
| **tcprewrite** | Rewrite IPs/MACs in PCAPs for testbed addressing | Bundled with tcpreplay |
| **Selenium** | Headless browser for benign HTTPS traffic | `pip install selenium` |
| **Chromium Driver** | Browser backend for Selenium | `apt install chromium-driver` |
| **Locust** | High-volume HTTP/HTTPS load generation | `pip install locust` |
| **T-Rex (Cisco)** | Stateful L4–L7 packet generation at scale | Manual install from trex-tgn.cisco.com |

---

## Layer 7: Benchmark Datasets

| Dataset | Content | Use Case |
|:---|:---|:---|
| **USTC-TFC2016** | 10 malware + 10 benign encrypted traffic classes | Multi-class baseline training |
| **CIC-IDS2017** | Multi-day captures with DoS, DDoS, brute force labels | CL task sequencing across temporal sessions |
| **CIC-IDS2018** | Extended version with additional attack scenarios | Supplementary CL tasks |
| **CIRA-CIC-DoHBrw-2020** | DNS-over-HTTPS exfiltration vs. benign DoH | Advanced encrypted channel detection |

---

## Layer 8: I/O & Storage Optimization

| Technology | Purpose | Where |
|:---|:---|:---|
| **tmpfs RAM Disk** (4 GB) | Buffer NFStream flow writes to avoid RAID I/O contention | Inside VM 100, VM 200 at `/mnt/ramdisk` |
| **LVM-Thin Snapshots** | Fast VM checkpoint/rollback for experiment reproducibility | PVE host storage pool (`local-lvm`) |
| **Parquet** | Columnar storage format for batched flow records | `/mnt/ramdisk/flows/` → persistent storage |

---

## Layer 9: MLOps & Observability

| Tool | Purpose | Where | Port |
|:---|:---|:---|:---|
| **MLflow** | Centralized experiment tracking (loss, accuracy, BWT per round) | LXC 300 | 5000 |
| **TensorBoard** | Weight distributions, gradient norms, activation statistics | VM 100, VM 200 | 6006 |
| **Weights & Biases** | Cloud-hosted alternative for team collaboration | Any (cloud) | — |

---

## Optional: GPU Acceleration

| Technology | Purpose | Install |
|:---|:---|:---|
| **NVIDIA Driver** | GPU compute on host | `apt install nvidia-driver` on PVE host |
| **vfio / IOMMU** | PCIe GPU passthrough to VMs | Enable in BIOS + kernel params |
| **NVIDIA CUDA Toolkit** | GPU compute inside VM | Install inside defender VM |
| **PyTorch CUDA** | GPU-accelerated training | `pip install torch --index-url .../cu121` |
