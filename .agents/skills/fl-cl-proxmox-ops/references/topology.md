# Proxmox VE Testbed Architecture & Network Specifications

## 1. Virtualization Host Specs
- **Hypervisor**: Proxmox VE 8.x
- **Host CPU**: AMD Ryzen / Intel Core with hardware virtualization enabled (SVM/VT-x)
- **Overlay Network**: Linux Bridge `vmbr1` assigned to VLAN `130`
- **Subnet**: `10.10.130.0/24` (No public internet exposure for defender internal mesh)

---

## 2. Container & Virtual Machine Specifications

### LXC 300: `fl-aggregator`
- **OS**: Debian 12 Bookworm (Unprivileged Container)
- **vCPU / RAM**: 4 vCPUs / 8 GB RAM
- **IP**: `10.10.130.10`
- **Mounts**: `/mnt/ramdisk` (`tmpfs`, 4GB max)
- **Roles**: Runs Flower central gRPC server (`8080`), MLflow tracking server (`5000`), and Prometheus pushgateway (`9091`).

### VM 310: `defender-a` (Site Alpha)
- **OS**: Ubuntu Server 22.04 LTS (KVM)
- **vCPU / RAM**: 4 vCPUs / 8 GB RAM
- **IP**: `10.10.130.11`
- **Mounts**: `/mnt/ramdisk` (`tmpfs`, 4GB max)
- **Roles**: Live NFStream passive network sniffer on interface `eth1`, Avalanche Continual Learning client, FastAPI local inference endpoint (`8000`).

### VM 320: `defender-b` (Site Beta)
- **OS**: Ubuntu Server 22.04 LTS (KVM)
- **vCPU / RAM**: 4 vCPUs / 8 GB RAM
- **IP**: `10.10.130.12`
- **Mounts**: `/mnt/ramdisk` (`tmpfs`, 4GB max)
- **Roles**: Live NFStream passive network sniffer on interface `eth1`, Avalanche Continual Learning client, FastAPI local inference endpoint (`8000`).

### VM 330: `attacker`
- **OS**: Kali Linux / Debian 12
- **vCPU / RAM**: 2 vCPUs / 4 GB RAM
- **IP**: `10.10.130.13`
- **Roles**: Traffic replay via `tcpreplay` and malicious attack generation (Mirai botnet, Slowloris DoS, Hydra brute force, DNS exfiltration).

---

## 3. Storage Hierarchy & Compliance

| Location | Filesystem | Persistence | Purpose |
| :--- | :--- | :--- | :--- |
| `/opt/fl-cl/` | `ext4` | Persistent | Python source code, model architectures, configs |
| `/opt/fl-cl/models/`| `ext4` | Persistent | Trained global checkpoints & TorchScript models |
| `/mnt/ramdisk/` | `tmpfs` | **Ephemeral (RAM)** | Raw PCAP capture buffers, extracted flow CSVs/Parquets |
| `/var/log/fl-cl/` | `ext4` | Persistent | Structured JSON application logs |
