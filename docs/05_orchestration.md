# FL-CL Orchestration & Threat Simulation Walkthrough

> **Role in the documentation set**: This document provides a thorough, step-by-step guide to executing the automated Federated Continual Learning pipeline. It explains every node, every script, and every phase of the orchestration process. For the underlying architecture, see [02_architecture.md](02_architecture.md). For infrastructure deployment, see [04_deployment.md](04_deployment.md).

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

## 2. Source Code & Tools Layout

Scripts are grouped into logical folders based on their role and deployment targets:

```
fl-cl/
├── configs/
│   └── experiment.yaml    # Central configuration file for hyperparameters & topology
│
├── runs/
│   ├── clean_testbed.py   # Wipes state and stops processes across testbed nodes
│   └── setup_ssh_targets.py # Dynamically creates admin users with non-trivial passwords on targets
│
├── src/
│   ├── aggregator/        # → FL Aggregator (LXC 300)  10.10.130.10
│   │   └── server.py      #   Flower server + MLflow logging + checkpointing
│   │
│   ├── defender/          # → Defender A (VM 310) + Defender B (VM 320)
│   │   ├── client.py      #   Flower client with Avalanche EWC
│   │   ├── cl_strategy.py #   EWC continual learning strategy (class-weighted)
│   │   ├── model.py       #   CyberDefenseNet model definition (single source of truth)
│   │   └── extractor.py   #   NFStream traffic feature extractor
│   │
│   ├── traffic_gen/       # → Traffic Generator (VM 400)  10.10.140.10
│   │   └── attack_flow.py #   Offensive scenario simulator (multi-round botnet beaconing)
│   │
│   ├── notifications.py   # Telegram webhook notifications helper
│   └── orchestrate.py     # Master orchestrator running on local workstation
│
└── tools/                 # → Diagnostics & Pre-deployment Validation
    ├── check_dataset.py   # Inspect label distributions on ramdisk
    ├── check_features.py  # Compute feature statistics per class to check overlap
    ├── enable_wal.py      # Enable WAL mode on MLflow SQLite database
    ├── local_train.py     # Local training diagnostic tool with confusion matrix
    ├── plot_metrics.py    # Post-training convergence plot generator (per-class)
    └── validate_model.py  # Model validation gate (asserts minimum per-class F1 score)
```

> The model definition is centralized in `src/defender/model.py`. The orchestrator copies this single source of truth to the aggregator container and all defender VMs during initialization.

---

## 3. Script-by-Script Deep Dive

### 3.1 `src/defender/model.py` — The Shared Neural Network

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
4. **Batches flows into CSV files** (default: 500 flows per file) and writes them to `/mnt/ramdisk/flows/`.

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
| `ewc_lambda` | 0.25 (configurable via YAML) | Regularization strength balancing plasticity vs. stability |
| `class_weights` | `[8.0, 20.0, 3.0, 15.0, 10.0]` | Per-class loss weights to boost underperforming threat classes |
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
/opt/flower-env/bin/python3 server.py --rounds 100 --min-clients 2 --mlflow-uri http://localhost:5000
```
- Waits for at least 2 clients (Defender A + Defender B) before starting each round
- Opens an MLflow experiment called `FL-CL-CyberDefense`
- Binds to `0.0.0.0:8080` for gRPC client connections

---

### 3.6 `src/traffic_gen/attack_flow.py` — Threat Scenario Simulator

**Deployed to:** Traffic Generator (VM 400, Kali Linux)

A CLI utility that generates one of five traffic patterns against a target IP:

#### Mode: `benign`
```bash
~/traffic-env/bin/python3 attack_flow.py --mode benign --target 10.10.110.15 --duration 30
```
Sends HTTP GET requests to the target's port 80 every 0.3 seconds for the specified duration. Generates normal web browsing patterns that the model should classify as class `0`.

#### Mode: `ssh`
```bash
~/traffic-env/bin/python3 attack_flow.py --mode ssh --target 10.10.110.15 --duration 30
```
Launches `hydra` with the `fasttrack.txt` wordlist against the target's SSH service (port 22). Generates rapid, failed authentication attempts that the model should classify as class `3`.

#### Mode: `slowloris`
```bash
~/traffic-env/bin/python3 attack_flow.py --mode slowloris --target 10.10.110.15 --duration 30 --port 80
```
Runs `slowloris` with 100 concurrent sockets, sending partial HTTP headers to hold connections open. Generates DoS patterns that the model should classify as class `4`.

#### Mode: `dns_exfil`
```bash
~/traffic-env/bin/python3 attack_flow.py --mode dns_exfil --target 10.10.110.15 --duration 30
```
Sends crafted DNS-like UDP packets to port 53, simulating data exfiltration via DNS tunneling. Generates patterns that the model should classify as class `2`.

#### Mode: `botnet`
```bash
~/traffic-env/bin/python3 attack_flow.py --mode botnet --target 10.10.110.15 --duration 30
```
Opens persistent TCP sessions on C2 ports (8080/8888/9000) with multi-round HTTP-based heartbeats. Generates beaconing patterns that the model should classify as class `1`.

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
python src/orchestrate.py --key "~/.ssh/id_ed25519" --config configs/experiment.yaml
```

| Argument | Default | Description |
|:---------|:--------|:------------|
| `--key` | System default | Path to your SSH private key |
| `--config` | `configs/experiment.yaml` | Path to YAML experiment configuration |
| `--rounds` | 100 | Number of federated averaging rounds (overrides config) |
| `--lambda-ewc` | 0.25 | EWC regularization strength (overrides config) |
| `--duration` | 60 | Duration (seconds) of each attack stage (overrides config) |
| `--mlops-mode` | `experimental` | MLOps Mode (`experimental` or `production`). Configures model version naming, registration behavior, and dashboard tagging. |
| `--production-strategy` | `resume` | Action strategy for `production` mode: `resume` (warm-start from the existing `champion` model version) or `fresh` (cold-start a new model version). |

> [!TIP]
> **Security Best Practice**: To avoid storing sensitive credentials in plain-text inside `configs/experiment.yaml`, you can either create a `.env` file at the root of the repository or export them as environment variables on your workstation before running the orchestrator:
> 
> **Option A: Local `.env` File (Recommended)**
> Create a `.env` file at the project root (ignored by Git):
> ```env
> TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
> TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
> SSH_KEY_PATH="C:\Users\Username\.ssh\id_ed25519"
> ```
> 
> **Option B: Environment Variables**
> ```powershell
> $env:TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
> $env:TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
> $env:SSH_KEY_PATH="C:\Users\Username\.ssh\id_ed25519"
> ```
> The orchestrator and target scripts will automatically detect and load these values.


#### MLOps Execution Modes
* **Experimental Mode (`--mlops-mode experimental`)**: Meant for training new models or hyperparameter tuning. The training proceeds as a cold-start (or warm-start if checkpoints exist), and the final registered model is assigned the `challenger` alias in MLflow.
* **Production Mode (`--mlops-mode production`)**: Meant for maintaining the production-grade model. Under this mode, the orchestrator handles lifecycle state promotions:
  * **Resume Strategy (`--production-strategy resume`)**: Checks the Model Registry for the version tagged with the `champion` alias. If present, it warm-starts the aggregator and client networks using this champion version's weights, ensuring continual learning continuity.
  * **Fresh Strategy (`--production-strategy fresh`)**: Ignores existing registry weights and cold-starts training from scratch. Upon completion, the new model is registered and automatically promoted to the `champion` alias (displacing any previous champion).


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
~/fl-cl-env/bin/python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/ --batch-size 500
```
This starts the NFStream capture daemon in the background. It immediately begins listening on the SPAN mirror interface `ens19` and writing flow CSVs to the RAM disk. The `--batch-size 500` means a new CSV file is created every 500 flows (or every 5 seconds, whichever comes first).

### Step 6: Phase 5 — MLflow & Flower Server Boot

On **FL Aggregator** (`10.10.130.10`):

First, the MLflow tracking server starts:
```bash
/opt/flower-env/bin/mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db --allowed-hosts '*' --cors-allowed-origins '*' --x-frame-options NONE --disable-security-middleware
```
The orchestrator waits 3 seconds for MLflow to initialize, then starts the Flower server:
```bash
/opt/flower-env/bin/python3 server.py --rounds 100 --min-clients 2 --mlflow-uri http://localhost:5000 --config-file ~/experiment.yaml --mlops-mode production --production-strategy resume --git-commit 2da6a4964aa6cdcf06937d80cec9006dc2d325a7
```
The new parameters control MLOps integration and registry behavior:
* `--config-file`: Optional path to the active experiment configuration YAML file, which is automatically saved as an MLflow run artifact.
* `--mlops-mode`: Either `experimental` or `production`. Controls the registration alias logic (`challenger` vs `champion`).
* `--production-strategy`: Either `resume` or `fresh`. Used under `production` mode to determine if training should warm-start from the registry's existing `champion` model weights, or cold-start from scratch.
* `--git-commit`: The current Git commit SHA-1 of the workstation codebase, which is dynamically logged as a run tag `git_commit` and detailed in the MLflow note.

The server now waits for 2 clients to connect before beginning round 1.


### Step 7: Phase 6 — Sequential Threat Simulation

On **Traffic Generator** (`10.10.140.10`), five attack stages are triggered in sequence:

**Stage 1 — Benign Traffic:**
```bash
~/traffic-env/bin/python3 attack_flow.py --mode benign --target 10.10.110.15 --duration 60
~/traffic-env/bin/python3 attack_flow.py --mode benign --target 10.10.120.15 --duration 60
```
HTTP GET requests every 0.3s to both targets. This generates class `0` (Normal) training data.

**Stage 2 — SSH Brute Force:**
```bash
~/traffic-env/bin/python3 attack_flow.py --mode ssh --target 10.10.110.15 --duration 60
~/traffic-env/bin/python3 attack_flow.py --mode ssh --target 10.10.120.15 --duration 60
```
Hydra dictionary attacks against SSH. This generates class `3` (BruteForce) training data.

**Stage 3 — Slowloris DoS:**
```bash
~/traffic-env/bin/python3 attack_flow.py --mode slowloris --target 10.10.110.15 --duration 60 --port 80
~/traffic-env/bin/python3 attack_flow.py --mode slowloris --target 10.10.120.15 --duration 60 --port 80
```
100-socket Slowloris flood. This generates class `4` (DoS) training data.

**Stage 4 — DNS Exfiltration:**
```bash
~/traffic-env/bin/python3 attack_flow.py --mode dns_exfil --target 10.10.110.15 --duration 60
~/traffic-env/bin/python3 attack_flow.py --mode dns_exfil --target 10.10.120.15 --duration 60
```
Rapid DNS-like UDP queries to port 53, simulating data exfiltration over DNS. This generates class `2` (Exfiltration) training data.

**Stage 5 — Botnet C2 Beaconing:**
```bash
~/traffic-env/bin/python3 attack_flow.py --mode botnet --target 10.10.110.15 --duration 60
~/traffic-env/bin/python3 attack_flow.py --mode botnet --target 10.10.120.15 --duration 60
```
Multi-round HTTP-like C2 heartbeat sessions on ports 8080/8888/9000. This generates class `1` (Botnet) training data.

### Step 8: Phase 7 — Flower Client Launch

On **Defender A** and **Defender B**:
```bash
~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id A --ewc-lambda 0.25
~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id B --ewc-lambda 0.25
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

This repeats for all configured rounds (default: 100).

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

### Programmatic Run Tags & Markdown Descriptions
The pipeline automatically tags every MLflow run with metadata describing its MLOps configuration:
* `mlops_mode`: `production` or `experimental`.
* `production_strategy`: `fresh` or `resume` (omitted if mode is experimental).
* `git_commit`: Workstation git commit SHA-1 hash for reproducibility.
* `warm_started`: `True` if initialized using weights from a previous version, otherwise `False`.
* `resumed_from_run_id`: The MLflow run ID of the model weights loaded (if warm-started).
* `resumed_from_version`: The Model Registry version number used as the warm-start base.

Additionally, a detailed, structured Markdown summary is generated and saved under the run's `mlflow.note.content` tag, displaying as the main description in the MLflow UI. This includes:
* **MLOps Metadata**: Execution mode, production strategy, workstation git commit, and warm-start indicator.
* **Warm-Start Pedigree**: Parent run ID and model version (if resuming).
* **Final Performance metrics**: Final global loss, best loss round, overall validation accuracy, and class-by-class accuracies.

### Evaluation Tables Logging
To resolve the limitations of flat scalar metrics (where class metrics are mixed across time), the server logs a class-wise evaluation table after every federated averaging round using `mlflow.log_table()`.

This creates a structured artifact file named `evaluation_metrics_summary.json` containing:
* `round`: The training round index.
* `accuracy`: Global model accuracy.
* `class_0_accuracy`, `class_1_accuracy`, etc.: Per-class accuracy metrics (sentinel `-1.0` is filtered out if no samples were evaluated).
* `class_0_samples`, `class_1_samples`, etc.: The count of test samples evaluated for each class during that round.

You can view, search, query, and plot this dataset directly from the MLflow run detail page's "Artifacts" tab.

### Expected Metrics Behavior & Anomalies

When evaluating results inside the MLflow dashboard or CSV exports:
1. **Skipped/Missing Class Columns (`accuracy_class_1`, `accuracy_class_2`)**:
   - Because Botnet (class 1) and DNS Exfiltration (class 2) traffic generator modes were previously not triggered during the standard orchestration flow. With the updated 5-stage pipeline, all classes should now be represented.
   - To avoid division-by-zero errors when calculating class accuracy for zero samples, the clients report a sentinel value of `-1.0`. The server filters this sentinel, resulting in omitted logs/columns for these classes.
2. **Extremely High Overall Accuracy (~99.9%) alongside Low/Zero Benign Accuracy (`accuracy_class_0`)**:
   - **Severe Class Imbalance**: The traffic generator produces thousands of malicious flows during active attack phases, whereas the benign flow generation runs yield a very small handful. As a result, the global validation accuracy is heavily dominated by the attack detection rates.
   - **Administrative Port 22 Overlap**: The heuristic labeling logic in `client.py` assigns Class 0 (Normal) to all non-attacker flows. However, the orchestrator script continuously issues administrative SSH connections on port 22 to check process statuses. Since these administrative flows share structural characteristics (port 22) with the SSH Brute Force attacks (Class 3), the model correctly notices the feature overlap and biases toward classifying all port 22 flows as malicious, lowering the benign class accuracy.

### 5.4 Post-Run Local LLM Analytics & Reporting

To automate the review of final training metrics and assist in detecting catastrophic forgetting or tuning hyperparameters, the pipeline integrates a local Ollama-based LLM analyst.

#### Configuration & Robust Resolution
The pipeline uses a standardized `load_env()` recursive upward path search across all orchestration and utility scripts. The local `.env` file located at the project root is dynamically discovered and loaded regardless of the script's current working directory:
```env
# Ollama AI Configuration
OLLAMA_ENDPOINT="https://YOUR_OLLAMA_SERVER_HOSTNAME"
OLLAMA_KEY="YOUR_OLLAMA_KEY"
OLLAMA_MODEL="llama3.1:8b"
```

#### Automation & Upload Flow
1. **Proxy Authentication**: The Ollama instance is protected by an Nginx reverse proxy requiring the custom `x-fcl-key` header.
2. **Analysis Generation**: When the master orchestrator completes training, it triggers `tools/generate_llm_report.py`.
3. **Instruct-style Prompting**: Because `llama3.1:8b` is an instruct-tuned model, the prompt is structured as a direct instructional request. This guides the model to produce a professional MLOps analysis report with structured sections without needing completion-style scaffolding.
4. **Optimized CPU Inference**: The query specifies `num_thread: 4` and passes `"num_predict": 512` to limit generated tokens. This prevents CPU-bound inference hangs/timeouts and ensures clean, sub-15-second report generation.
5. **MLflow Artifact Registration**: The returned analysis is appended to the run's `run_summary.md` report, and then programmatically uploaded to the MLflow server via the tracking API under the active run ID.

---

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
# On Aggregator:
ssh root@10.10.130.10 "cat /tmp/mlflow.log"
ssh root@10.10.130.10 "cat /tmp/flower-server.log"

# On Defenders:
ssh root@10.10.130.11 "cat /tmp/extractor.log"
ssh root@10.10.130.11 "cat /tmp/flower-client.log"

# On Traffic Generator:
ssh root@10.10.140.10 "cat /tmp/attack_flow.log"
```

---

## 6. Model Registry Governance & Aliases

To establish a strict promotion logic and track model lineage, the aggregator uses modern MLflow 3.x **Model Version Aliases** instead of legacy stages (`Production`, `Staging`, etc.). All registered versions are saved to the central registry under the registered model name `CyberDefenseNet`.

### Promotion Rules by MLOps Mode
* **Experimental Mode (`--mlops-mode experimental`)**:
  - The model is registered to the registry under a new version number.
  - The new version is automatically tagged with the **`challenger`** alias, indicating it is under testing.
* **Production Mode (`--mlops-mode production`)**:
  - The model is registered under a new version number.
  - The new version is automatically promoted to the **`champion`** alias.
  - MLflow automatically removes the `champion` alias from any previous model version and assigns it to this newly promoted version, enforcing a single current production model.

### Warm-Starting from Registry Champion
When a training run is launched with `--mlops-mode production --production-strategy resume`, the server checks the Model Registry for the version labeled `champion`:
1. It queries the MLflow Model Registry for the version labeled with the `champion` alias.
2. It downloads the state dict checkpoint `model_latest.pt` from that run's artifacts.
3. The server loads these weights and distributes them as the initial parameters in Round 1 of the new training run, warm-starting the continual learning process.
4. The resulting run registers its final model as a new version and takes over the `champion` alias.

### Retrieving Models Programmatically
Downstream client services or deployment agents can query the latest active champion model via the MLflow Client API:

```python
import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri("http://10.10.130.10:5000")
client = MlflowClient()

# Get champion version metadata
champion_meta = client.get_model_version_by_alias(
    name="CyberDefenseNet",
    alias="champion"
)
print(f"Active Champion Version: {champion_meta.version} (Run ID: {champion_meta.run_id})")

# Load champion model directly
model_uri = f"models:/CyberDefenseNet@champion"
loaded_model = mlflow.pytorch.load_model(model_uri)
```

---

## 7. Hyperparameter Sweep Controller

To optimize FCL performance (e.g., EWC stability penalty $\lambda$, learning rate, class weights) without manual scheduling, the pipeline includes `src/sweep.py`.

### 7.1 Sweep Configuration & Schema
The controller accepts a sweep YAML config (e.g., `configs/sweep_grid.yaml` or `configs/sweep_verify.yaml`):

```yaml
experiment:
  name: "FL-CL-Hyperparameter-Sweep"
  mlops_mode: "production"
  production_strategy: "fresh"

grid:
  cl:
    ewc_lambda: [0.1, 0.25, 0.5, 0.8]
  training:
    lr: [0.005, 0.01, 0.02]
```

### 7.2 Parent-Child Nesting Architecture
When running the sweep controller:
1. **Parent Run Creation**: The controller creates a single parent run in MLflow named after the experiment (e.g., `Sweep: [Timestamp]`). This run is tagged with the parameter search space grid.
2. **Child Runs Execution**: For every parameter combination, `sweep.py` invokes `src/orchestrate.py` passing `--parent-run-id` and the specific hyperparameter values.
3. **Lineage linking**: The orchestrator propagates `parent_run_id` to the Flower aggregator server, which opens its MLflow run nested inside the parent run. This preserves complete experiment lineage for multi-dimensional sweeps.

---

## 8. Dataset Provenance & Hashing

To ensure full reproducibility and detect dataset drift, the orchestrator automatically generates a lineage map of the client training data.

### 8.1 SHA-256 Provenance Calculation
Before starting the training loop, the orchestrator:
1. SSHs to Defender A (`10.10.130.11`) and Defender B (`10.10.130.12`).
2. Iterates over all flow CSV files in `/mnt/ramdisk/flows/` to calculate their individual SHA-256 hashes.
3. Generates a combined, sorting-stable SHA-256 digest of the entire file collection for each client (e.g., `defender_a_hash`, `defender_b_hash`).
   - Done remotely via: `find /mnt/ramdisk/flows/ -name '*.csv' -type f -exec sha256sum {} + | sort | sha256sum`

### 8.2 Lineage Graph Logging
1. These individual hashes are logged as MLflow parameters on the run: `defender_a_hash` and `defender_b_hash`.
2. A combined run-level dataset provenance hash is calculated by hashing the concatenated client digests:
   $$\text{combined\_hash} = \text{SHA-256}(\text{hash\_A} \mathbin{\Vert} \text{hash\_B})$$
3. A JSON schema artifact `dataset_lineage.json` is generated and saved with the MLflow run. This file documents:
   - Workstation git commit SHA-1
   - Path to local CSVs on client nodes
   - Individual client hashes
   - Timestamp and sample counts per client node.

---

## 9. Automated Validation Gate & Promotion

To enforce strict quality control in the automated MLOps pipeline, candidate models must satisfy rigorous continual learning validation gates in `server.py` before being promoted to `champion`.

### 9.1 Validation Gate Criteria
The gate checks the candidate model's validation metrics using three key dimensions:

1. **Per-Class F1 Gating**: Rather than naive accuracy, the model must surpass specific F1 thresholds on all classes:
   - Class 0 (Normal): $\text{F1} \ge 0.50$
   - Class 1 (Botnet): $\text{F1} \ge 0.60$
   - Class 2 (Exfiltration): $\text{F1} \ge 0.70$
   - Class 3 (BruteForce): $\text{F1} \ge 0.50$
   - Class 4 (DoS): $\text{F1} \ge 0.70$
2. **Backward Transfer (BWT) Forgetting Gate**: To prevent catastrophic forgetting, the Backward Transfer (BWT) for each individual class must not regress:
   $$\text{BWT}_{\text{class}\_i} \ge 0.0 \quad \text{for all } i \in [0, 4] \text{ where evaluation data exists}$$
3. **Communication Overhead Budget**: The total network bytes exchanged during training rounds must be within the defined budget (default: 200,000,000 bytes):
   $$\text{Bytes}_{\text{total}} \le \text{Budget}$$

### 9.2 Registry Promotion & Notifications Control
* **Pass**: If the candidate satisfies all gates:
  - It is promoted to the **`champion`** alias in the MLflow Model Registry.
  - The model is exported as a TorchScript artifact `CyberDefenseNet.pt`.
  - A successful promotion Telegram notification is sent with the task sequence and final metrics.
* **Fail**: If any threshold is violated:
  - The model remains registered but retains the **`challenger`** alias.
  - The specific reasons for rejection are tagged on the MLflow run (`rejection_reason`).
  - An HTML-formatted Telegram alert is dispatched detailing the exact class or parameter that caused the failure.

---

## 10. Federated Data Quality Gates & Feature Drift Diagnostics

To protect the federated continual learning pipeline from training on corrupted or out-of-distribution batches, the platform implements automated data quality gates.

### 10.1 Pre-Flight Data Quality Checks (JSD Gate)
Before launching the training loop in each round:
1. The orchestrator calls `tools/check_dataset.py` on client nodes to calculate the label frequency counts.
2. It measures the **Jensen-Shannon Divergence (JSD)** of the client's current flow distribution against the configured `baseline_class_distribution` (from `configs/experiment.yaml`).
3. If the calculated JSD exceeds the `jsd_threshold` (default: 0.6) and the config specifies `gate_action: "abort"`, the orchestrator immediately alerts operators via Telegram and shuts down the pipeline with exit code 2.

### 10.2 Client-Side Real-Time Training Gate
During active client execution:
1. In the `fit()` hook, the client recalculates the current JSD drift before running the Avalanche training cycle.
2. If the current batch JSD exceeds `js_threshold`, the client skips training for that round and immediately uploads its un-modified parameters to the aggregator.
3. The client sets the telemetry indicators `"dataset_rejected": 1.0` and `"dataset_jsd"` to report real-time drift metadata back to the Flower server.

### 10.3 Post-Flight Feature Drift Diagnostics (Z-Scores)
To audit feature-level distributions:
1. The orchestrator runs `tools/check_features.py` on the client nodes.
2. It compares the mean/standard deviation of active features against `baseline_stats.json` on a per-class basis.
3. It flags feature drift using standard **Z-scores**:
   $$Z_f = \frac{\mu_{\text{active}, f} - \mu_{\text{baseline}, f}}{\sigma_{\text{baseline}, f}}$$
4. If $|Z_f| \ge 3.0$, a feature drift warning is logged.
5. The statistics are pushed to MLflow, and feature distribution histograms are streamed to TensorBoard under `runs/feature_drift` for deep statistical debugging.


