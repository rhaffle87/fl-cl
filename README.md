# FL-CL: Hybrid Federated-Continual Learning for Collaborative Cyber Defense

A privacy-preserving, forgetting-resistant intrusion detection system deployed on a 3-node Proxmox VE cluster. Combines **Federated Learning** (cross-organizational model training without sharing raw data) with **Continual Learning** (adapting to new threats without forgetting old ones) on **Encrypted Traffic Analysis** metadata.

---

## Project Structure

```
fl-cl/
├── README.md                     ← You are here
├── TECH_STACK.md                 ← Complete technology inventory
│
├── docs/                         ← Research documentation
│   ├── 00_research_paper.md      ← Full integrated paper (Chapters 1–9)
│   ├── 01_prerequisites.md       ← Hardware, datasets, traffic tools
│   ├── 02_architecture.md        ← Conceptual blueprint & diagrams
│   └── 03_workarounds.md         ← Cluster-specific fixes & deployment
│
├── infra/                        ← Infrastructure-as-Code (shell scripts)
│   ├── 01_host_config/           ← PVE hypervisor-level configuration
│   │   ├── hosts.txt             ← Standardized /etc/hosts template
│   │   ├── enable_vlan.sh        ← Enable VLAN awareness on vmbr1
│   │   └── enable_snippets.sh    ← Enable hookscript storage
│   │
│   ├── 02_vm_provision/          ← VM/CT creation scripts
│   │   ├── create_aggregator.sh  ← LXC 300 on node pve
│   │   ├── create_defender_a.sh  ← VM 100 on node its
│   │   ├── create_defender_b.sh  ← VM 200 on node node2
│   │   ├── create_target_a1.sh   ← VM 101 on node its
│   │   ├── create_target_b1.sh   ← VM 201 on node node2
│   │   └── create_traffic_gen.sh ← VM 400 on node node2
│   │
│   ├── 03_hookscripts/           ← Proxmox lifecycle hookscripts
│   │   ├── mirror-hook-a.sh      ← Port mirror: VM 101 → VM 100
│   │   └── mirror-hook-b.sh      ← Port mirror: VM 201 → VM 200
│   │
│   └── 04_guest_setup/           ← In-VM software provisioning
│       ├── setup_aggregator.sh   ← Python + Flower + MLflow
│       ├── setup_defender.sh     ← Python + PyTorch + Avalanche + NFStream
│       └── setup_traffic_gen.sh  ← tcpreplay + Hydra + Metasploit + Selenium
│
└── src/                          ← Python application code
    ├── model.py                  ← CyberDefenseNet (PyTorch MLP)
    ├── cl_strategy.py            ← EWC continual learning wrapper
    ├── extractor.py              ← NFStream flow feature extraction
    ├── client.py                 ← Flower FL client + Avalanche CL
    └── server.py                 ← Flower FL aggregator server
```

---

## Quick Start — Deployment Order

> Every script includes usage instructions in its header comments.

### Step 1: Host Configuration (run on ALL 3 PVE nodes as root)
```bash
# Apply unified hostname resolution
cp hosts.txt /etc/hosts

# Enable VLAN awareness on vmbr1
chmod +x enable_vlan.sh && ./enable_vlan.sh

# Enable hookscript storage
chmod +x enable_snippets.sh && ./enable_snippets.sh
```

### Step 2: Provision VMs (run on the designated hypervisor node)
```bash
# On node 'pve':
bash create_aggregator.sh

# On node 'its':
bash create_defender_a.sh
bash create_target_a1.sh

# On node 'node2':
bash create_defender_b.sh
bash create_target_b1.sh
bash create_traffic_gen.sh
```

### Step 3: Deploy Hookscripts (run on hypervisor nodes)
```bash
# On node 'its':
cp mirror-hook-a.sh /var/lib/vz/snippets/
chmod +x /var/lib/vz/snippets/mirror-hook-a.sh
qm set 101 --hookscript local:snippets/mirror-hook-a.sh

# On node 'node2':
cp mirror-hook-b.sh /var/lib/vz/snippets/
chmod +x /var/lib/vz/snippets/mirror-hook-b.sh
qm set 201 --hookscript local:snippets/mirror-hook-b.sh
```

### Step 4: Install Software (run inside each guest VM)
```bash
# Inside LXC 300:  bash setup_aggregator.sh
# Inside VM 100:   bash setup_defender.sh
# Inside VM 200:   bash setup_defender.sh
# Inside VM 400:   bash setup_traffic_gen.sh
```

### Step 5: Copy source code to VMs and run
```bash
# On aggregator (LXC 300):
source /opt/flower-env/bin/activate
python3 server.py --rounds 10 --min-clients 2

# On defender VMs (VM 100 & 200):
source ~/fl-cl-env/bin/activate
python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/
python3 client.py --server 10.10.10.130:8080 --client-id A   # (or B)
```

---

## Cluster Layout

| Node | VM ID | Hostname | VLAN | Role |
|:---|:---|:---|:---|:---|
| pve | 300 | fl-aggregator | 30 | Flower server, MLflow tracking |
| its | 100 | defender-a | 10 | NFStream + PyTorch + Avalanche + Flower client |
| its | 101 | target-a1 | 10 | Attack/benign traffic receiver |
| node2 | 200 | defender-b | 20 | Parallel defender (separate organization) |
| node2 | 201 | target-b1 | 20 | Attack/benign traffic receiver |
| node2 | 400 | traffic-gen | 40 | Kali Linux attack + benign traffic source |

---

## Documentation

| Document | Purpose |
|:---|:---|
| [Research Paper](docs/00_research_paper.md) | Complete integrated paper (Chapters 1–9) |
| [Prerequisites](docs/01_prerequisites.md) | Hardware, datasets, traffic generation tools |
| [Architecture](docs/02_architecture.md) | Conceptual blueprint, diagrams, code components |
| [Workarounds](docs/03_workarounds.md) | Cluster-specific fixes and step-by-step deployment |
| [Tech Stack](TECH_STACK.md) | Full technology inventory per layer |
