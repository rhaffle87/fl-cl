---
name: fl-cl-proxmox-ops
description: Manage, health-check, deploy, and troubleshoot the 3-node Proxmox VE testbed infrastructure (LXC/VMs, RAMDisk tmpfs, gRPC networking) for FL-CL.
---

# FL-CL Proxmox VE Operations Skill

This skill guides agents through managing, auditing, deploying, and debugging the Proxmox VE virtualization testbed for distributed Federated Learning and intrusion detection evaluation.

---

## 1. Cluster Topology & Network Map

```text
+-------------------------------------------------------------------------------+
|                             Proxmox VE Cluster                                |
|                                                                               |
|  +---------------------+   +---------------------+   +---------------------+  |
|  | LXC 300: Aggregator |   |  VM 310: Defender-A |   |  VM 320: Defender-B |  |
|  | 10.10.130.10        |   |  10.10.130.11       |   |  10.10.130.12       |  |
|  | - Flower gRPC :8080 |   | - Flower Client     |   | - Flower Client     |  |
|  | - MLflow      :5000 |   | - NFStream Sniffer  |   | - NFStream Sniffer  |  |
|  | - Prometheus  :9091 |   | - Avalanche EWC/GEM |   | - Avalanche EWC/GEM |  |
|  | - RAMDisk (/mnt/..) |   | - RAMDisk (/mnt/..) |   | - RAMDisk (/mnt/..) |  |
|  +---------------------+   +---------------------+   +---------------------+  |
|             ^                         ^                         ^             |
|             |                         |                         |             |
|             +-------------------------+-------------------------+             |
|                          VLAN 130 Isolated L2 Overlay                         |
+-------------------------------------------------------------------------------+
```

---

## 2. Standard Operations Procedures

### Step 1: Health-Check the Testbed
Execute the cluster health verification script to test socket reachability, ping latency, and port availability:
```bash
python .agents/skills/fl-cl-proxmox-ops/scripts/check_cluster_health.py
```

### Step 2: Zero-Persistence RAMDisk Verification
To guarantee cybersecurity audit compliance (zero persistent storage of unencrypted raw network PCAPs):
```bash
# Verify tmpfs mount on client nodes
ssh root@10.10.130.11 "df -T /mnt/ramdisk | grep tmpfs"
ssh root@10.10.130.12 "df -T /mnt/ramdisk | grep tmpfs"
```

### Step 3: Remote Code Synchronization & Deployment
Deploy latest codebase artifacts from the development station to the nodes:
```bash
# Sync defender code to clients
rsync -avz --exclude '.git' --exclude '__pycache__' src/ root@10.10.130.11:/opt/fl-cl/src/
rsync -avz --exclude '.git' --exclude '__pycache__' src/ root@10.10.130.12:/opt/fl-cl/src/

# Sync aggregator code to server
rsync -avz --exclude '.git' --exclude '__pycache__' src/ root@10.10.130.10:/opt/fl-cl/src/
```

### Step 4: Service Management
Manage background daemon processes across cluster nodes:
```bash
# Start Aggregator Server
ssh root@10.10.130.10 "cd /opt/fl-cl && python src/aggregator/server.py --port 8080 > /var/log/fl-server.log 2>&1 &"

# Start Defender Clients
ssh root@10.10.130.11 "cd /opt/fl-cl && python src/defender/client.py --server 10.10.130.10:8080 --client-id 0 > /var/log/fl-client-0.log 2>&1 &"
ssh root@10.10.130.12 "cd /opt/fl-cl && python src/defender/client.py --server 10.10.130.10:8080 --client-id 1 > /var/log/fl-client-1.log 2>&1 &"
```

---

## 3. Node Inventory & Service Matrix

| Node ID | Hostname | Role | IP Address | Active Services / Ports |
| :--- | :--- | :--- | :--- | :--- |
| **LXC 300** | `fl-aggregator` | Central Server | `10.10.130.10` | gRPC `8080`, MLflow `5000`, Prometheus `9091` |
| **VM 310** | `defender-a` | Edge Defender 1 | `10.10.130.11` | Client Worker, NFStream Sniffer, FastAPI `:8000` |
| **VM 320** | `defender-b` | Edge Defender 2 | `10.10.130.12` | Client Worker, NFStream Sniffer, FastAPI `:8000` |
| **VM 330** | `attacker` | Threat Simulator| `10.10.130.13` | Scapy / Tcpreplay traffic generator |

---

## 4. Diagnostics & Failure Recovery

1. **gRPC Connection Refused (8080)**:
   - Check if LXC 300 firewall allows TCP 8080: `iptables -L -n | grep 8080`
   - Check if server is listening: `netstat -tlpn | grep 8080`
2. **tmpfs Out of Memory**:
   - Flush processed flow batches: `rm -f /mnt/ramdisk/flows/*.csv /mnt/ramdisk/flows/*.parquet`
3. **Packet Sniffing Permission Error**:
   - Ensure NFStream runs with `CAP_NET_RAW` / `CAP_NET_ADMIN` or as root.
