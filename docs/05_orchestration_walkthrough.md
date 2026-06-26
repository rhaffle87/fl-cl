# FL-CL Orchestration & Threat Simulation Walkthrough

> **Role in the documentation set**: This document provides a thorough, step-by-step guide to executing the automated Federated Continual Learning pipeline. It explains every node, every script, and every phase of the orchestration process. For the underlying architecture, see [02_architecture.md](02_architecture.md). For infrastructure deployment, see [04_deployment_walkthrough.md](04_deployment_walkthrough.md).

---

## 1. Network Topology Reference

All nodes sit on a flat Layer 2 network over the Proxmox bridge `vmbr1` using the `10.10.0.0/16` subnet. Logical separation is achieved through IP prefixing, not routing.

```
                        ┌───────────────────────────────┐
                        │      FL Aggregator (LXC 300)  │
                        │         10.10.130.10          │
                        │  Runs: server.py, MLflow      │
                        └───────────────┬───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
┌─────────────┴─────────────┐           │           ┌─────────────┴─────────────┐
│   Organization A Zone     │           │           │   Organization B Zone     │
│                           │           │           │                           │
│  Defender A (VM 310)      │           │           │  Defender B (VM 320)      │
│    10.10.130.11           │           │           │    10.10.130.12           │
│  Runs: extractor.py,      │           │           │  Runs: extractor.py,      │
│        client.py          │           │           │        client.py          │
│  Captures via: ens19      │           │           │  Captures via: ens19      │
│         ▲ (mirror)        │           │           │         ▲ (mirror)        │
│         │                 │           │           │         │                 │
│  Target A1 (VM 311)       │           │           │  Target B1 (VM 321)       │
│    10.10.110.15           │           │           │    10.10.120.15           │
│  Runs: busybox httpd      │           │           │  Runs: busybox httpd      │
└───────────────────────────┘           │           └───────────────────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        │  Traffic Generator (VM 400)   │
                        │       10.10.140.10            │
                        │  Runs: attack_flow.py         │
                        └───────────────────────────────┘
```

### Node Summary Table

| Node | VM/CT ID | IP Address | OS | Purpose |
|:-----|:---------|:-----------|:---|:--------|
| fl-aggregator | LXC 300 | `10.10.130.10` | Ubuntu 24.04 | Flower server + MLflow tracker |
| defender-a | VM 310 | `10.10.130.11` | Ubuntu 24.04 | Traffic capture + EWC training (Org A) |
| target-a1 | VM 311 | `10.10.110.15` | Alpine Linux | Victim HTTP server (Org A) |
| defender-b | VM 320 | `10.10.130.12` | Ubuntu 24.04 | Traffic capture + EWC training (Org B) |
| target-b1 | VM 321 | `10.10.120.15` | Alpine Linux | Victim HTTP server (Org B) |
| traffic-gen | VM 400 | `10.10.140.10` | Kali Linux | Offensive traffic simulator |

---

## 2. Source Code Layout

Scripts are grouped into folders by their deployment target VM:

```
src/
├── aggregator/          # → FL Aggregator (LXC 300)  10.10.130.10
│   ├── server.py        #   Flower server + MLflow logging
│   └── model.py         #   CyberDefenseNet model definition
│
├── defender/             # → Defender A (VM 310) + Defender B (VM 320)
│   ├── client.py         #   Flower client with Avalanche EWC
│   ├── cl_strategy.py    #   EWC continual learning strategy
│   ├── model.py          #   CyberDefenseNet model definition
│   └── extractor.py      #   NFStream traffic feature extractor
│
├── traffic_gen/          # → Traffic Generator (VM 400)  10.10.140.10
│   └── attack_flow.py    #   Offensive scenario simulator
│
└── orchestrate.py        # → Local workstation (Windows host)
```

> `model.py` exists in both `aggregator/` and `defender/` because both the server and clients need the identical `CyberDefenseNet` architecture definition.

---

## 3. Script-by-Script Deep Dive

### 3.1 `src/aggregator/model.py` & `src/defender/model.py` — The Shared Neural Network

**Deployed to:** Aggregator (LXC 300), Defender A (VM 310), Defender B (VM 320)

Defines `CyberDefenseNet`, a 3-layer Multi-Layer Perceptron (MLP):

```
Input (32 features) → Linear(64) → ReLU → Dropout(0.2) → Linear(32) → ReLU → Linear(5 classes)
```

* **32 input features** come from NFStream's flow metadata (packet counts, byte volumes, inter-arrival times, JA3 hashes converted to numeric representations).
* **5 output classes** correspond to threat categories:

| Class ID | Label | Example Traffic |
|:---------|:------|:----------------|
| 0 | Normal | Benign HTTPS browsing, SSH admin sessions |
| 1 | Botnet | C2 beaconing on ports 8080/8888/9000 |
| 2 | Exfiltration | DNS tunneling on port 53 |
| 3 | BruteForce | Automated SSH login attempts on port 22 |
| 4 | DoS | Slowloris HTTP floods on port 80/443 |

**Why this matters:** Every node in the system shares this identical model architecture. The Flower server aggregates weight updates that match this exact shape, and the EWC strategy on clients preserves the Fisher Information matrix computed over these same parameters.

---

### 3.2 `src/defender/extractor.py` — Packet-to-Feature Pipeline

**Deployed to:** Defender A (VM 310), Defender B (VM 320)  
**Runs on interface:** `ens19` (the SPAN/mirror capture port)

This script is a **long-running daemon** that:

1. **Binds to the mirror interface** (`ens19`) using NFStream in promiscuous mode.
2. **Reconstructs packets into flows** — grouping related packets by 5-tuple (src IP, dst IP, src port, dst port, protocol) with idle/active timeouts.
3. **Extracts 17 metadata features** per flow, including:
   - TLS handshake fingerprints (`ja3_hash`, `ja3s_hash`)
   - Flow statistics (`bidirectional_packets`, `bidirectional_bytes`, `duration_ms`)
   - Directional metrics (`src2dst_packets`, `dst2src_bytes`)
   - Timing (`src2dst_mean_piat_ms`, `dst2src_mean_piat_ms`)
   - Connection metadata (`src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`)
4. **Batches flows into CSV files** (default: 100 flows per file) and writes them to `/mnt/ramdisk/flows/`.

**Why RAM disk?** The `/mnt/ramdisk/` is a 4 GB tmpfs mount. Writing to RAM avoids disk I/O contention on the shared RAID controller, which is critical when the extractor is processing hundreds of flows per second during attack scenarios.

**Example output file** (`/mnt/ramdisk/flows/flows_000001.csv`):
```csv
ja3_hash,ja3s_hash,sni,application,bidirectional_packets,bidirectional_bytes,...,src_ip,dst_ip,src_port,dst_port,protocol
abc123,def456,example.com,SSL.TLS,42,8192,...,10.10.140.10,10.10.110.15,54321,80,6
```

---

### 3.3 `src/defender/cl_strategy.py` — Elastic Weight Consolidation (EWC)

**Deployed to:** Defender A (VM 310), Defender B (VM 320)

This module creates an Avalanche EWC strategy object that wraps the `CyberDefenseNet` model. Key configuration:

| Parameter | Value | Purpose |
|:----------|:------|:--------|
| `optimizer` | SGD (lr=0.01, momentum=0.9) | Stochastic gradient descent for local weight updates |
| `criterion` | CrossEntropyLoss | Standard multi-class classification loss |
| `ewc_lambda` | 0.4 (default, tunable) | Regularization strength balancing plasticity vs. stability |
| `train_mb_size` | 32 | Mini-batch size during local training |
| `train_epochs` | 1 | Single epoch per federated round to limit drift |

**How EWC prevents catastrophic forgetting:**
1. After training on Task A (e.g., BruteForce detection), EWC computes a **Fisher Information Matrix** — identifying which neural network weights are most important for Task A.
2. When Task B arrives (e.g., DoS detection), EWC adds a penalty term to the loss function that discourages large changes to Task-A-critical weights.
3. The `ewc_lambda` parameter controls penalty strength. Higher values = more stability (better retention of old tasks), lower values = more plasticity (faster adaptation to new threats).

---

### 3.4 `src/defender/client.py` — Federated Learning Client with CL Integration

**Deployed to:** Defender A (VM 310), Defender B (VM 320)

This is the core bridge between Flower (Federated Learning) and Avalanche (Continual Learning). It implements the `CyberDefenseClient` class that Flower calls during each round.

#### Data Loading Pipeline (`load_ramdisk_flows`)
1. Reads all CSV files from `/mnt/ramdisk/flows/`
2. Selects numeric feature columns and scales them with `StandardScaler`
3. Pads or truncates feature vectors to exactly 32 dimensions (matching `CyberDefenseNet` input)
4. Calls `assign_label()` on each row to generate threat labels

#### Dynamic Threat Labeling (`assign_label`)
Instead of pre-labeled datasets, this function inspects raw flow metadata to assign labels at runtime:

| Condition | Assigned Label |
|:----------|:---------------|
| Traffic involves port 22 and originates from Traffic Gen IP | `3` (BruteForce) |
| Traffic involves port 80/443 and originates from Traffic Gen IP | `4` (DoS) |
| Traffic involves port 8080/8888/9000 from Traffic Gen IP | `1` (Botnet) |
| Traffic involves port 53 from Traffic Gen IP | `2` (Exfiltration) |
| All other traffic | `0` (Normal) |

#### Per-Round Flower Client Lifecycle
For each federated round, Flower calls these methods in sequence:

1. **`set_parameters()`** — Receives the global model weights from the aggregator and loads them into the local `CyberDefenseNet`.
2. **`fit()`** — Loads fresh flow CSVs from ramdisk, wraps them into an Avalanche experience, and calls `self.cl.train(experience)` to run one epoch of EWC-regularized training. Returns updated weights and sample count.
3. **`evaluate()`** — Runs a PyTorch evaluation loop over the same flow data. Computes:
   - Overall accuracy and loss
   - Per-class accuracy for all 5 threat categories
   - Returns metrics dictionary to the server for aggregation

---

### 3.5 `src/aggregator/server.py` — Federated Aggregator with MLflow Logging

**Deployed to:** FL Aggregator (LXC 300)

Runs the Flower gRPC server and implements a custom `MLflowFedAvg` strategy.

#### Custom Strategy: `MLflowFedAvg`
Inherits from Flower's built-in `FedAvg` (Federated Averaging). After each evaluation round:
1. Calls `super().aggregate_evaluate()` to compute weighted-average metrics across all clients
2. Logs the aggregated `loss` to MLflow with the round number as the step
3. Logs every metric key (including `accuracy`, `accuracy_class_0` through `accuracy_class_4`) to MLflow

#### Weighted Class-Wise Aggregation (`weighted_avg`)
When clients report different dataset sizes, naive averaging would be misleading. This function:
1. Weights each client's accuracy by its sample count
2. Computes per-class accuracies separately, skipping clients that report `-1.0` (sentinel for "no samples of this class")
3. Returns a single dictionary of globally aggregated metrics

#### Server Startup
```bash
python3 server.py --rounds 10 --min-clients 2 --mlflow-uri http://localhost:5000
```
- Waits for at least 2 clients (Defender A + Defender B) before starting each round
- Opens an MLflow experiment called `FL-CL-CyberDefense`
- Binds to `0.0.0.0:8080` for gRPC client connections

---

### 3.6 `src/traffic_gen/attack_flow.py` — Threat Scenario Simulator

**Deployed to:** Traffic Generator (VM 400, Kali Linux)

A CLI utility that generates one of three traffic patterns against a target IP:

#### Mode: `benign`
```bash
python3 attack_flow.py --mode benign --target 10.10.110.15 --duration 30
```
Sends HTTP GET requests to the target's port 80 every 0.5 seconds for the specified duration. Generates normal web browsing patterns that the model should classify as class `0`.

#### Mode: `ssh`
```bash
python3 attack_flow.py --mode ssh --target 10.10.110.15 --duration 30
```
Launches `hydra` with the `fasttrack.txt` wordlist against the target's SSH service (port 22). Generates rapid, failed authentication attempts that the model should classify as class `3`.

#### Mode: `slowloris`
```bash
python3 attack_flow.py --mode slowloris --target 10.10.110.15 --duration 30 --port 80
```
Runs `slowloris` with 100 concurrent sockets, sending partial HTTP headers to hold connections open. Generates DoS patterns that the model should classify as class `4`.

---

### 3.7 `src/orchestrate.py` — Master Controller

**Runs on:** Your local Windows workstation

This script automates the entire pipeline by issuing SSH/SCP commands to all 6 nodes. It uses a `RemoteNode` class that wraps the native OpenSSH client (no Python dependencies like `paramiko` required).

#### `RemoteNode` Class
Each node is defined with a name, IP, username, and optional SSH key:
```python
aggregator = RemoteNode("fl-aggregator", "10.10.130.10", "root", args.key)
def_a      = RemoteNode("defender-a",    "10.10.130.11", "root", args.key)
def_b      = RemoteNode("defender-b",    "10.10.130.12", "root", args.key)
target_a   = RemoteNode("target-a1",     "10.10.110.15", "root", args.key)
target_b   = RemoteNode("target-b1",     "10.10.120.15", "root", args.key)
traffic_gen = RemoteNode("traffic-gen",  "10.10.140.10", "root", args.key)
```

Key methods:
- **`run_cmd(command, background=False)`** — Executes a command via SSH. If `background=True`, wraps it in `nohup ... &` so the process survives after SSH disconnects.
- **`scp_file(local, remote)`** — Copies a file from your workstation to the remote node.
- **`cleanup()`** — Kills all testbed-related processes on the node (`pkill -f 'server.py|client.py|...'`).

---

## 4. Step-by-Step Execution Procedure

### Prerequisites
Before running the orchestrator, ensure:
1. All target VMs (`311`, `321`) are booted and their lifecycle hookscripts have applied traffic mirroring rules
2. Your workstation SSH key is authorized on all 6 nodes (password-less `ssh root@10.10.130.10` must work)
3. Software stacks are installed on each node (see `infra/04_guest_setup/setup_defender.sh`)

### Step 1: Launch the Orchestrator

From your Windows workstation, open a terminal in the `fl-cl` project directory:

```powershell
python src/orchestrate.py --rounds 10 --lambda-ewc 0.4 --duration 30
```

| Argument | Default | Description |
|:---------|:--------|:------------|
| `--key` | System default | Path to your SSH private key |
| `--rounds` | 10 | Number of federated averaging rounds |
| `--lambda-ewc` | 0.4 | EWC regularization strength |
| `--duration` | 30 | Duration (seconds) of each attack stage |

### Step 2: Phase 1 — Process Cleanup

The orchestrator SSHs into **every node** and runs:
```bash
pkill -f 'server.py|client.py|extractor.py|attack_flow.py|busybox httpd' || true
```
This ensures no stale processes from a previous run interfere.

### Step 3: Phase 2 — Source Code Synchronization

The orchestrator copies the latest scripts from your workstation to each node's home directory:

| Destination Node | Files Transferred |
|:-----------------|:------------------|
| fl-aggregator (`10.10.130.10`) | `server.py`, `model.py` |
| defender-a (`10.10.130.11`) | `client.py`, `cl_strategy.py`, `model.py`, `extractor.py` |
| defender-b (`10.10.130.12`) | `client.py`, `cl_strategy.py`, `model.py`, `extractor.py` |
| traffic-gen (`10.10.140.10`) | `attack_flow.py` |

### Step 4: Phase 3 — Target Server Initialization

On **Target A1** (`10.10.110.15`) and **Target B1** (`10.10.120.15`):
```bash
mkdir -p /tmp/www && echo 'Target A1 Benign Server' > /tmp/www/index.html
busybox httpd -p 80 -h /tmp/www
```
This starts a lightweight HTTP server so benign traffic generation has something to connect to, and attack tools like Slowloris have a real service to target.

### Step 5: Phase 4 — Traffic Extraction Daemons

On **Defender A** (`10.10.130.11`) and **Defender B** (`10.10.130.12`):
```bash
~/fl-cl-env/bin/python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/ --batch-size 100
```
This starts the NFStream capture daemon in the background. It immediately begins listening on the SPAN mirror interface `ens19` and writing flow CSVs to the RAM disk. The `--batch-size 100` means a new CSV file is created every 100 flows.

### Step 6: Phase 5 — MLflow & Flower Server Boot

On **FL Aggregator** (`10.10.130.10`):

First, the MLflow tracking server starts:
```bash
mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db
```
The orchestrator waits 3 seconds for MLflow to initialize, then starts the Flower server:
```bash
python3 server.py --rounds 10 --min-clients 2 --mlflow-uri http://localhost:5000
```
The server now waits for 2 clients to connect before beginning round 1.

### Step 7: Phase 6 — Sequential Threat Simulation

On **Traffic Generator** (`10.10.140.10`), three attack stages are triggered in sequence:

**Stage 1 — Benign Traffic (first 15 seconds):**
```bash
python3 attack_flow.py --mode benign --target 10.10.110.15 --duration 30
python3 attack_flow.py --mode benign --target 10.10.120.15 --duration 30
```
HTTP GET requests every 0.5s to both targets. This generates class `0` (Normal) training data.

**Stage 2 — SSH Brute Force (starts at ~15 seconds):**
```bash
python3 attack_flow.py --mode ssh --target 10.10.110.15 --duration 30
python3 attack_flow.py --mode ssh --target 10.10.120.15 --duration 30
```
Hydra dictionary attacks against SSH. This generates class `3` (BruteForce) training data.

**Stage 3 — Slowloris DoS (starts at ~30 seconds):**
```bash
python3 attack_flow.py --mode slowloris --target 10.10.110.15 --duration 30 --port 80
python3 attack_flow.py --mode slowloris --target 10.10.120.15 --duration 30 --port 80
```
100-socket Slowloris flood. This generates class `4` (DoS) training data.

### Step 8: Phase 7 — Flower Client Launch

On **Defender A** and **Defender B**:
```bash
~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id A --ewc-lambda 0.4
~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id B --ewc-lambda 0.4
```

Each client:
1. Connects to the Flower server via gRPC on port 8080
2. Receives the current global model weights
3. Reads all flow CSVs from `/mnt/ramdisk/flows/`
4. Labels each flow dynamically using `assign_label()`
5. Wraps the data into an Avalanche experience
6. Trains for 1 epoch using EWC
7. Evaluates per-class accuracy
8. Returns updated weights and metrics to the aggregator

This repeats for all 10 configured rounds.

### Step 9: Phase 8 — Convergence Monitoring

The orchestrator polls the aggregator every 5 seconds:
```bash
pgrep -f 'server.py'
```
When the Flower server process exits (all rounds completed), the orchestrator prints `[✓] Flower server has completed its rounds.` If the process hasn't exited after 10 minutes, it times out. You can press `Ctrl+C` at any time to trigger early cleanup.

### Step 10: Phase 9 — Final Cleanup

The orchestrator SSHs into every node and terminates all background processes, leaving the environment clean for the next run.

---

## 5. Monitoring & Verification

### MLflow Dashboard
Open your browser to `http://10.10.130.10:5000` and select the `FL-CL-CyberDefense` experiment.

Key metrics to monitor across rounds:

| Metric | What It Shows | Healthy Trend |
|:-------|:--------------|:--------------|
| `loss` | Global aggregated validation loss | Decreasing over rounds |
| `accuracy` | Overall classification accuracy | Increasing toward 0.8+ |
| `accuracy_class_0` | Normal traffic detection rate | Stable (should not drop) |
| `accuracy_class_3` | BruteForce detection rate | Increasing after SSH attack stage |
| `accuracy_class_4` | DoS detection rate | Increasing after Slowloris stage |

**Detecting catastrophic forgetting:** If `accuracy_class_3` drops significantly after the Slowloris phase (Phase 6 Stage 3), it indicates the model is forgetting BruteForce patterns. Increase `--lambda-ewc` (e.g., to 0.6 or 0.8) and re-run.

### Manual SSH Checks

**Verify extractor is capturing flows:**
```bash
ssh root@10.10.130.11 "ls -la /mnt/ramdisk/flows/"
```

**Verify Flower server is listening:**
```bash
ssh root@10.10.130.10 "netstat -antp | grep 8080"
```

**Check remote process logs:**
```bash
ssh root@10.10.130.10 "cat /tmp/fl-aggregator.log"
ssh root@10.10.130.11 "cat /tmp/defender-a.log"
ssh root@10.10.140.10 "cat /tmp/traffic-gen.log"
```
