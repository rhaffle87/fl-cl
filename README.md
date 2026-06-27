# FL-CL: Hybrid Federated-Continual Learning for Collaborative Cyber Defense

A privacy-preserving, forgetting-resistant intrusion detection system deployed on a 3-node Proxmox VE cluster. Combines **Federated Learning** (cross-organizational model training without sharing raw data) with **Continual Learning** (adapting to new threats without forgetting old ones) on **Encrypted Traffic Analysis** metadata.

---

## Project Structure

```
fl-cl/
├── README.md                     ← You are here
├── TECH_STACK.md                 ← Complete technology inventory
│
├── configs/                      ← Experiment configuration
│   └── experiment.yaml           ← Reproducible hyperparams, topology, notifications
│
├── docs/                         ← Research documentation
│   ├── 00_research_paper.md      ← Full integrated paper (Chapters 1–9)
│   ├── 01_prerequisites.md       ← Hardware, datasets, traffic tools
│   ├── 02_architecture.md        ← Conceptual blueprint & diagrams
│   ├── 03_workarounds.md         ← Cluster-specific fixes & deployment
│   ├── 04_deployment_walkthrough.md  ← Step-by-step cluster setup
│   └── 05_orchestration_walkthrough.md ← Training and attack execution
│
├── infra/                        ← Infrastructure-as-Code (shell scripts)
│   ├── 01_host_config/           ← PVE hypervisor-level configuration
│   ├── 02_vm_provision/          ← VM/CT creation scripts
│   ├── 03_hookscripts/           ← Proxmox lifecycle hookscripts
│   └── 04_guest_setup/           ← In-VM software provisioning
│
├── src/                          ← Python application code
│   ├── aggregator/               ← FL Aggregator (LXC 300)
│   │   └── server.py             ← Flower server + MLflow + checkpointing
│   ├── defender/                 ← Defender clients (VM 310 & 320)
│   │   ├── client.py             ← Flower FL client + Avalanche CL
│   │   ├── cl_strategy.py        ← EWC continual learning (class-weighted)
│   │   ├── extractor.py          ← NFStream flow feature extraction
│   │   └── model.py              ← CyberDefenseNet (single source of truth)
│   ├── traffic_gen/              ← Traffic Generator (VM 400)
│   │   └── attack_flow.py        ← Offensive scenario simulator
│   ├── notifications.py          ← Telegram webhook notifications
│   └── orchestrate.py            ← Local workstation orchestrator
│
└── tools/                        ← Diagnostic & validation utilities
    ├── check_dataset.py          ← Inspect ramdisk flow label distribution
    ├── check_features.py         ← Per-class feature statistics
    ├── local_train.py            ← Standalone training + confusion matrix
    └── validate_model.py         ← Pre-deployment model validation gate
```

---

## Quick Start — Run an Experiment

### Prerequisites
- SSH access to all 6 VMs from your local workstation
- Python environments provisioned on remote nodes (see `infra/04_guest_setup/`)

### Option 1: Config-driven (recommended)
Edit `configs/experiment.yaml` to set your hyperparameters, then:
```bash
python src/orchestrate.py --key /path/to/ssh_key --config configs/experiment.yaml
```

### Option 2: CLI overrides
```bash
python src/orchestrate.py \
  --key /path/to/ssh_key \
  --rounds 100 \
  --lambda-ewc 0.4 \
  --duration 30
```

The orchestrator will:
1. Clean up old processes on all nodes
2. SCP source code to remote VMs
3. Launch target HTTP services, extractors, MLflow, and Flower server
4. Run 5 attack stages (benign, SSH, Slowloris, DNS exfil, botnet)
5. Run data quality gate (verify all 5 classes present)
6. Launch Flower clients for federated training
7. Save model checkpoints + TorchScript export on aggregator
8. Send Telegram notification on completion/failure

---

## MLOps Features

| Feature | Implementation |
|:--------|:---------------|
| **Experiment Config** | `configs/experiment.yaml` — all params in one YAML, logged as MLflow artifact |
| **Model Checkpointing** | Best model saved per round to `/opt/mlflow-artifacts/checkpoints/` |
| **TorchScript Export** | Production model exported for deployment validation |
| **Data Quality Gate** | Pre-training label distribution check on both defenders |
| **Model Validation** | `tools/validate_model.py` — per-class accuracy thresholds |
| **Class-Weighted Loss** | Inverse-frequency weights `[10, 3, 3, 8, 1]` for imbalanced data |
| **Experiment Tracking** | MLflow at `http://10.10.130.10:5000` with git hash tagging |
| **Notifications** | Telegram bot for start/complete/fail alerts |

---

## Diagnostic Tools

SCP any tool to a defender VM and run:

```bash
# Check flow label distribution
scp tools/check_dataset.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/check_dataset.py"

# Analyze feature statistics per class
scp tools/check_features.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/check_features.py"

# Train locally and print confusion matrix
scp tools/local_train.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/local_train.py --epochs 40"

# Validate a saved model checkpoint
scp tools/validate_model.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/validate_model.py --checkpoint /path/to/model.pt"
```

---

## Cluster Layout

| Node | VM ID | Hostname | Logical IP Subnet | Role |
|:---|:---|:---|:---|:---|
| pve | 300 | fl-aggregator | `10.10.130.10/16` | Flower server, MLflow tracking |
| its | 310 | defender-a | `10.10.130.11/16` | NFStream + PyTorch + Avalanche + Flower client |
| its | 311 | target-a1 | `10.10.110.15/16` | Attack/benign traffic receiver |
| node2 | 320 | defender-b | `10.10.130.12/16` | Parallel defender (separate organization) |
| node2 | 321 | target-b1 | `10.10.120.15/16` | Attack/benign traffic receiver |
| node2 | 400 | traffic-gen | `10.10.140.10/16` | Kali Linux attack + benign traffic source |

---

## Documentation

| Document | Purpose |
|:---|:---|
| [Research Paper](docs/00_research_paper.md) | Complete integrated paper (Chapters 1–9) |
| [Prerequisites](docs/01_prerequisites.md) | Hardware, datasets, traffic generation tools |
| [Architecture](docs/02_architecture.md) | Conceptual blueprint, diagrams, code components |
| [Workarounds](docs/03_workarounds.md) | Cluster-specific fixes and step-by-step configurations |
| [Deployment Walkthrough](docs/04_deployment_walkthrough.md) | Step-by-step cluster setup, provisioning, and installations |
| [Orchestration Walkthrough](docs/05_orchestration_walkthrough.md) | Detailed walkthrough of training and attack execution |
| [Tech Stack](TECH_STACK.md) | Full technology inventory per layer |
