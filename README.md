# FL-CL: Hybrid Federated-Continual Learning for Collaborative Cyber Defense

A privacy-preserving, forgetting-resistant intrusion detection system deployed on a 3-node Proxmox VE cluster. Combines **Federated Learning** (cross-organizational model training without sharing raw data) with **Continual Learning** (adapting to new threats without forgetting old ones) on **Encrypted Traffic Analysis** metadata.

---

## Project Structure

```text
fl-cl/
├── README.md                     <- You are here
├── TECH_STACK.md                 <- Complete technology inventory
│
├── configs/                      <- Experiment configurations
│   ├── experiment.yaml           <- Reproducible hyperparams, topology, notifications
│   ├── baseline_feature_stats.json <- Baseline Z-score scaling statistics
│   └── experiments/              <- Specialized experiment configs (GEM, Dropout, ColdStart, Poisoning)
│
├── data/                         <- Organized local datasets, databases, exports, and reports
│   ├── db/                       <- Local MLflow SQLite databases (mlflow.db)
│   ├── exports/                  <- Synced experiment run exports and plots
│   ├── models/                   <- Local PyTorch checkpoints (.pt) & MODEL_CARD.md
│   ├── plots/                    <- Fact-checked visualization figures (.png, .svg)
│   ├── references/               <- Reference research papers (.pdf)
│   └── reports/                  <- Consolidated technical results reports (.md, .csv)
│
├── docs/                         <- System documentation & Architecture Decision Records
│   ├── decisions/                <- Formal Architecture Decision Records (ADR-001 to ADR-006)
│   ├── paper/                    <- IEEE LaTeX manuscript, BibTeX citations & vector figures
│   ├── 01_prerequisites.md       <- Hardware, datasets, traffic tools
│   ├── 02_architecture.md        <- Conceptual blueprint & C4 diagrams
│   ├── 03_deployment.md          <- Step-by-step cluster setup
│   ├── 04_orchestration.md       <- Training and attack execution
│   ├── 05_continual.md           <- End-to-end FCL technical explanation
│   ├── 06_training.md            <- Training guidebook, CLI flags, MLOps perks
│   ├── 07_troubleshooting.md     <- Cluster-specific fixes & failure modes ledger
│   ├── 08_reference.md           <- Comprehensive API and module reference
│   ├── 09_glossary.md            <- Domain model & technical terminology glossary
│   └── 10_arguments.md           <- Defense dossier & rebuttals
│
├── infra/                        <- Infrastructure-as-Code (shell scripts)
│   ├── 01_host_config/           <- PVE hypervisor-level configuration
│   ├── 02_vm_provision/          <- VM/CT creation scripts
│   ├── 03_hookscripts/           <- Proxmox lifecycle hookscripts
│   └── 04_guest_setup/           <- In-VM software provisioning
│
├── tools/                        <- Governance, benchmarking, test suites, and deployment
│   ├── deploy_clean_testbed.py   <- Clean MLflow DB & target leftover flows/logs/processes
│   └── deploy_setup_targets.py   <- Configure challenging target SSH passwords
│
├── src/                          <- Python application code
│   ├── aggregator/               <- FL Aggregator (LXC 300)
│   │   ├── alerts.py             <- Real-time Byzantine & drift incident dispatcher
│   │   ├── dashboard.py          <- Aggregator live dashboard
│   │   ├── google_sheets_webhook.js <- Google Apps Script WebApp webhook handler
│   │   ├── server.py             <- Flower server + MLflow + checkpointing
│   │   └── sheets_sync.py        <- Google Sheets Webhook async telemetry dispatcher
│   ├── defender/                 <- Defender clients (VM 310 & 320)
│   │   ├── client.py             <- Flower FL client + Avalanche CL
│   │   ├── cl_strategy.py        <- EWC & GEM continual learning
│   │   ├── extractor.py          <- NFStream flow feature extraction (tmpfs RAMDisk)
│   │   ├── inference_loop.py     <- Real-time flow classification loop (101k flows/sec)
│   │   └── model.py              <- Model factory (MLP, 1D-CNN, Transformer)
│   ├── traffic_gen/              <- Traffic Generator (VM 400)
│   │   └── attack_flow.py        <- Offensive scenario simulator
│   ├── notifications.py          <- Telegram webhook notifications
│   ├── orchestrate.py            <- Local workstation orchestrator
│   └── sweep.py                  <- Hyperparameter grid search controller
│
└── tools/                        <- Diagnostic, benchmarking & validation utilities
    ├── audit_codebase.py         <- Comprehensive AST and codebase invariant auditor
    ├── audit_docs.py             <- Markdown documentation and figure link validator
    ├── benchmark_byzantine.py    <- Multi-aggregator Byzantine robustness benchmark
    ├── benchmark_cross_dataset.py <- Heterogeneous generalization benchmark (shift simulator)
    ├── benchmark_dp.py           <- Differential Privacy noise sensitivity sweep
    ├── benchmark_latency.py      <- PyTorch FP32 vs INT8 inference throughput benchmark
    ├── benchmark_onnx.py         <- Multi-runtime (PyTorch vs ONNX Runtime) latency benchmark
    ├── check_dataset.py          <- Inspect ramdisk flow label distribution
    ├── check_features.py         <- Per-class feature statistics
    ├── check_network_stability.py <- Automated network stability, ARP collision, MTU & service health auditor
    ├── deploy_testbed.py         <- Automated multi-track testbed deployment runner
    ├── export_onnx.py            <- ONNX model graph exporter
    ├── generate_llm_report.py    <- Post-training local LLM threat report generator
    ├── generate_paper_figures.py <- Publication vector figure generator
    ├── generate_paper_pdf.py     <- Academic LaTeX paper compiler
    ├── plot_cicids2017.py        <- CIC-IDS2017 dataset visualization suite
    ├── plot_metrics.py           <- Post-training convergence plot generator
    ├── regenerate_figures.py     <- Standardized IEEE 300 DPI figure regenerator
    ├── sync_sheets_webhook.py    <- Google Sheets Webhook CLI exporter & synchronizer
    ├── test_attack_gen.py        <- Attack generation engine test suite
    ├── test_comprehensive.py     <- Comprehensive unit and integration test suite
    ├── test_local_train.py       <- Local training loop verification test
    ├── test_models.py            <- Architecture, TorchScript, INT8 & pruning tests
    ├── test_onnx_edge.py         <- Edge ONNX inference loop verification test
    ├── train_local.py            <- Standalone training + confusion matrix
    ├── train_quarantine_continual.py <- Quarantine self-healing retraining loop
    ├── validate_bwt.py           <- Standardized BWT validation suite with signatures
    ├── validate_model.py         <- Pre-deployment model validation gate
    └── validate_promotion.py     <- Automated CI/CD validation & registry promotion gate
```

---

## Quick Start — Run an Experiment

### Prerequisites

- SSH access to all 6 VMs from your local workstation
- Python environments provisioned on remote nodes (see `infra/04_guest_setup/`)

### 1. Pre-flight Setup & Cleanup

First, configure your `.env` file at the root of the project with your credentials and SSH private key path:

```env
# Telegram notifications credentials
TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
SSH_KEY_PATH="C:\Users\Username\.ssh\id_ed25519"

# Google Sheets Webhook Integration (Google Apps Script WebApp)
GSHEETS_WEBHOOK_URL="https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"

# Ollama AI Reporting Configuration
OLLAMA_ENDPOINT="https://YOUR_OLLAMA_SERVER_HOSTNAME"
OLLAMA_KEY="YOUR_OLLAMA_KEY"
OLLAMA_MODEL="llama3.1:8b"
```

Prepare the testbed by executing the helper scripts (which auto-load settings from `.env`):

```bash
# Configure "admin" user with a challenging wordlist password on targets
python tools/deploy_setup_targets.py

# Reset MLflow database, clear active flow CSVs, logs, and processes
python tools/deploy_clean_testbed.py
```

### 2. Execute Training Run

Run the simulation and federated training. The pipeline supports two MLOps modes (`experimental` or `production`) and production strategies (`resume` or `fresh`):

```bash
# Execute training in experimental mode (cold start, registers model with 'challenger' alias)
python src/orchestrate.py --mlops-mode experimental

# Execute training in production mode with a resume strategy (warm-starts training using the latest 'champion' model version)
python src/orchestrate.py --mlops-mode production --production-strategy resume

# Execute training in production mode from scratch (cold start, registers new model and promotes to 'champion' alias on finish)
python src/orchestrate.py --mlops-mode production --production-strategy fresh
```

The orchestrator will automatically:

1. Clean up old processes on nodes
2. SCP current source code to remote VMs
3. Launch target HTTP services, extractors, MLflow, and Flower server (with proper MLOps and strategy configuration flags)
4. Run simulated attack stages (benign, SSH, Slowloris, DNS exfil, botnet)
5. Verify data quality gate (all 5 classes present)
6. Launch Flower clients for training
7. Save model checkpoints, warm-start if resuming, and register the final best model using MLflow 3.x LoggedModel entities with appropriate Model Version Aliases
8. Notify via Telegram upon completion or failure

### 3. Execute Hyperparameter Sweep

To systematically run a grid search over multiple hyperparameter combinations, execute the sweep controller:

```bash
# Run a quick sweep to verify the pipeline, database connectivity, and model promotion gates
python src/sweep.py --config configs/sweep_verify.yaml

# Run the complete hyperparameter grid search
python src/sweep.py --config configs/sweep_grid.yaml
```

The sweep controller will:

1. Iterate over every hyperparameter combination in the configuration file.
2. Initialize a parent run in MLflow to record the search space.
3. Nest each training run under the parent run (linking them via `parent-run-id`).
4. Ensure standard output utilizes UTF-8 encoding on Windows to prevent console emoji errors.

---

## Performance & Throughput Benchmarks

Empirically validated using [`tools/benchmark_onnx.py`](tools/benchmark_onnx.py) and [`tools/benchmark_latency.py`](tools/benchmark_latency.py) across 200 evaluation repetitions on multi-core CPU architectures:

| Architecture | Batch Size | PyTorch FP32 Latency | TorchScript JIT Latency | ONNX Runtime Latency | ONNX Peak Throughput |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CyberDefenseCNN** *(Champion)* | **1 (Single Flow)** | 17.47 µs / flow | 16.32 µs / flow | **13.23 µs / flow** | **75,565 flows / sec** |
| | **16 (Edge Burst)** | 1.96 µs / flow | 1.88 µs / flow | **1.09 µs / flow** | **915,221 flows / sec** |
| | **64 (Mini-Batch)** | 1.01 µs / flow | 0.93 µs / flow | **0.44 µs / flow** | **2,291,019 flows / sec** |
| | **256 (Volumetric)**| 0.91 µs / flow | 0.80 µs / flow | **0.32 µs / flow** | **3,115,286 flows / sec** |
| **CyberDefenseNet (MLP)** | **1 (Single Flow)** | 18.49 µs / flow | 15.54 µs / flow | **10.96 µs / flow** | **91,241 flows / sec** |
| | **256 (Volumetric)**| 0.26 µs / flow | 0.22 µs / flow | **0.18 µs / flow** | **5,502,306 flows / sec** |
| **CyberDefenseTransformer** | **1 (Single Flow)** | 22.72 µs / flow | 19.98 µs / flow | **16.71 µs / flow** | **59,850 flows / sec** |
| | **256 (Volumetric)**| 1.49 µs / flow | 1.27 µs / flow | **0.58 µs / flow** | **1,725,584 flows / sec** |

---

## Security, Privacy & Byzantine Resilience

Empirically validated across Byzantine adversarial scenarios ([`tools/benchmark_byzantine.py`](tools/benchmark_byzantine.py)) and Differential Privacy sweeps ([`tools/benchmark_dp.py`](tools/benchmark_dp.py)):

### Byzantine Attack Resilience Matrix
| Attack Scenario | FedAvg Accuracy | FedMedian Accuracy | Krum Accuracy | TrimmedMean ($\beta=0.10$) Accuracy | Defense Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Baseline** | 99.40% | 99.40% | 99.40% | **99.40%** | Baseline parity |
| **10% Label Poisoning** | 99.40% | 99.40% | 99.40% | **99.40%** | 0.00% degradation |
| **20% Label Poisoning** | 99.40% | 99.40% | 99.40% | **99.40%** | 0.00% degradation |
| **50% Label Poisoning** | 99.20% (-0.2%) | 99.40% | 99.40% | **99.40%** | Poisoning neutralized |
| **Sign-Flipping Gradient Attack** | 79.40% (-20.0%) | 99.40% | 99.40% | **99.40%** | Attack completely eliminated |
| **Gaussian Noise Attack ($\sigma=2.0$)** | 80.40% (-19.0%) | 99.40% | 99.40% | **99.40%** | Noise filtered cleanly |

### Differential Privacy Guarantee (DP-SGD)
- **Clipping Norm**: $C = 1.0$ (bounded maximum gradient sensitivity).
- **Target Privacy Budget**: $(\epsilon = 6.08, \delta = 10^{-5})$ at noise multiplier $\sigma = 0.30$.
- **Utility Retention**: **99.40% Test Accuracy** and **0.9937 Macro F1** preserved under privacy noise injection.

---

## Standards & Regulatory Compliance Matrix

| Standard / Regulation | Compliance Mandate | FL-CL Architectural Implementation | Verification Tool / Artifact |
| :--- | :--- | :--- | :--- |
| **UU PDP No. 27/2022** *(Art. 65–66)* | Strict prohibition against transferring raw personal network data outside jurisdiction boundaries. | **Zero Raw Flow Transmission**: Raw packets and IP payloads remain isolated in local volatile tmpfs RAMDisks (`/mnt/ramdisk/flows/`). Only privacy-preserving gradient weights leave the node. | [`src/defender/client.py`](src/defender/client.py) & [ADR-004](docs/decisions/ADR-004_federated_aggregation.md) |
| **GDPR (EU 2016/679)** *(Art. 5, 25, 32)* | Data minimization, purpose limitation, and Privacy by Design via cryptographic anonymization. | **DP-SGD & Batch Aggregation**: In-place gradient clipping and DP noise injection mathematically prevent gradient inversion or flow reconstruction. | [`tools/benchmark_dp.py`](tools/benchmark_dp.py) & [`privacy_utility_curve.csv`](data/reports/benchmarks/privacy_utility_curve.csv) |
| **NIST SP 800-94 / 800-145** | Standards for Intrusion Detection and Prevention Systems (IDPS) and behavioral telemetry. | **32-Dimensional Statistical Representation**: Classifies threats using behavioral flow metadata (SPLT, PIAT, byte ratios) without inspecting encrypted payloads. | [`src/defender/extractor.py`](src/defender/extractor.py) & [`baseline_feature_stats.json`](configs/baseline_feature_stats.json) |
| **MITRE ATT&CK** | Standardized adversary tactic and technique classification. | **Threat Coverage**: T1498 (Network DoS / Slowloris), T1110 (Brute Force / SSH), T1048 (Exfiltration over DNS), T1071 (Application Layer C2 Beaconing). | [`src/traffic_gen/attack_flow.py`](src/traffic_gen/attack_flow.py) & [ADR-007](docs/decisions/ADR-007_attack_engines.md) |
| **ISO/IEC 27001 / 27701** | Information Security & Privacy Information Management System governance. | **Cryptographic Lineage & Checksums**: SHA-256 dataset lineage graphs, Git commit tagging, and immutable MLflow artifact logging. | [`src/orchestrate.py`](src/orchestrate.py) & [`tools/audit_codebase.py`](tools/audit_codebase.py) |
| **RFC 1035 / 793 / 7230** | DNS, TCP state machines, and HTTP/1.1 wire protocol specifications. | **Dual-Engine Protocol Conformance**: Modular `--engine auto|kali|python` generator creates compliant DNS query datagrams and TCP multi-round sessions. | [`src/traffic_gen/attack_flow.py`](src/traffic_gen/attack_flow.py) & [`tools/test_attack_gen.py`](tools/test_attack_gen.py) |

---

## MLOps & Security Features

| Feature | Implementation |
| :-------- | :--------------- |
| **Experiment Config** | `configs/experiment.yaml` — all params in one YAML, logged as MLflow artifact |
| **Modular Attack Engines** | `src/traffic_gen/attack_flow.py` — supports `--engine auto|kali|python` with automated tool discovery |
| **Byzantine Robustness** | Aggregator strategy supports `FedMedian`, `TrimmedMean`, and `Krum` coordinate-wise and distance-based filtering |
| **Differential Privacy** | Client-side DP-SGD via **Opacus** wrapping optimizer, tracking privacy budget metrics ($\epsilon, \delta$) |
| **Adversarial Poisoning** | Simulated label-flipping attacks on configured clients via `--poison-enabled` and `--poison-rate` |
| **NaN/Inf Sanitization** | Aggregator guard sanitizes NaN/Inf updates to `0.0` before global model assembly |
| **Gradient Safety** | Custom optimizer wrapper enforces gradient clipping limit of `1.0` during client backpropagation |
| **Hyperparameter Sweeps** | Grid search via `src/sweep.py` with parent-child run nesting in MLflow |
| **Dataset Provenance** | SHA-256 client flow file checksum hashing, logged as parameters and nested `dataset_lineage.json` graph artifact |
| **Automated Validation Gate** | Validates candidate models against per-class F1 thresholds, BWT forgetting check, and communication overhead budget for automated registry promotion |
| **Model Checkpointing** | Best model saved per round to `/opt/mlflow-artifacts/checkpoints/` |
| **Model Registry** | MLflow 3.x LoggedModel entities registered to central Model Registry |
| **Registry Governance** | Transitioned from deprecated stages to Model Version Aliases (`champion` for production, `challenger` for experimental models) |
| **Evaluation Tables** | Class-wise accuracies logged as JSON datasets via `mlflow.log_table()` |
| **Programmatic Tags & Notes** | Run tagged with MLOps parameters, git commit, parent versions, and structured markdown summaries in `mlflow.note.content` |
| **TorchScript Export** | Production model exported for deployment validation |
| **Data Quality Gate** | Pre-training label distribution check on both defenders |
| **Model Validation** | `tools/validate_model.py` — per-class F1 score thresholds |
| **BWT Validation Suite** | `tools/validate_bwt.py` — computes BWT deltas with SHA-256 validation signing |
| **Model Promotion Gate** | `tools/validate_promotion.py` — automated candidate evaluation & champion promotion |
| **Generalization Benchmark** | `tools/benchmark_cross_dataset.py` — cross-dataset validation under simulated covariate shift |
| **Confusion Matrix Tracking** | Per-round 5x5 matrix summation at aggregator with automated MLflow heatmap plots |
| **Class-Weighted Loss** | Per-class weights `[1.0, 250.0, 2.0, 5.0, 50.0]` for imbalanced data |
| **Experiment Tracking** | MLflow at `http://10.10.130.10:5000` with git hash tagging, parameters, and metrics tracking |
| **Google Sheets Live Sync** | Real-time live round metrics (`Live_Rounds`), promotion events (`Model_Promotions`), and bulk benchmark table exports via Google Apps Script Webhook |
| **Notifications** | Telegram bot for start/complete/fail alerts and governance incidents |

---

## Diagnostic & Operational Tools

The `tools/` directory is governed by **ADR-006** (Prefix Taxonomy & Standardization). All utilities support standard `--help` and work both locally and via SCP on defender nodes:

```bash
# Check flow label distribution
scp tools/check_dataset.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/check_dataset.py"

# Analyze feature statistics per class
scp tools/check_features.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/check_features.py"

# Train locally and print confusion matrix
scp tools/train_local.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/train_local.py --epochs 40"

# Run multi-runtime latency and throughput benchmark (PyTorch vs TorchScript vs ONNX)
python tools/benchmark_onnx.py

# Run Byzantine robustness evaluation
python tools/benchmark_byzantine.py

# Run Differential Privacy sensitivity sweep
python tools/benchmark_dp.py

# Sync all benchmark CSV reports to Google Spreadsheet tabs
python tools/sync_sheets_webhook.py --sync-all

# Test Google Sheets Webhook endpoint connectivity
python tools/sync_sheets_webhook.py --test

# Run attack generation engine verification suite
python tools/test_attack_gen.py

# Validate a saved model checkpoint
scp tools/validate_model.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/validate_model.py --checkpoint /path/to/model.pt"

# Run standardized BWT evaluation suite with cryptographic signing
scp tools/validate_bwt.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/validate_bwt.py --checkpoint /path/to/model.pt"

# Run cross-dataset generalization benchmark under simulated shift
scp tools/benchmark_cross_dataset.py root@10.10.130.11:~/
ssh root@10.10.130.11 "~/fl-cl-env/bin/python3 ~/benchmark_cross_dataset.py --checkpoint /path/to/model.pt"
```

---

## Cluster Layout

| Node | VM ID | Hostname | Logical IP Subnet | Role |
| :--- | :--- | :--- | :--- | :--- |
| pve | 300 | fl-aggregator | `10.10.130.10/16` | Flower server, MLflow tracking |
| its | 310 | defender-a | `10.10.130.11/16` | NFStream + PyTorch + Avalanche + Flower client |
| its | 311 | target-a1 | `10.10.110.15/16` | Attack/benign traffic receiver |
| node2 | 320 | defender-b | `10.10.130.12/16` | Parallel defender (separate organization) |
| node2 | 321 | target-b1 | `10.10.120.15/16` | Attack/benign traffic receiver |
| node2 | 400 | traffic-gen | `10.10.140.10/16` | Kali Linux attack + benign traffic source |

---

## Documentation & Architecture Decision Records

| Document | Purpose |
| :--- | :--- |
| [Architecture Decision Records (ADRs)](docs/decisions/README.md) | Formal records of major technical decisions (ADR-001 to ADR-007) |
| [IEEE Research Manuscript (Markdown)](docs/paper/manuscript.md) | Publication-ready paper with mathematical proofs & embedded figures |
| [IEEE Research Manuscript (LaTeX)](docs/paper/manuscript.tex) | 2-column IEEE Transactions LaTeX package & BibTeX citations |
| [01 Prerequisites](docs/01_prerequisites.md) | Hardware, datasets, traffic generation tools |
| [02 Architecture](docs/02_architecture.md) | Conceptual blueprint, C4 diagrams, code components |
| [03 Deployment](docs/03_deployment.md) | Step-by-step cluster setup, provisioning, and installations |
| [04 Orchestration](docs/04_orchestration.md) | Detailed guide to training and attack execution |
| [05 Continual Federated Learning](docs/05_continual.md) | End-to-end technical explanation of how FCL works |
| [06 Training & MLOps Guide](docs/06_training.md) | Training guidebook, CLI reference, MLOps behaviors |
| [07 Troubleshooting & Workarounds](docs/07_troubleshooting.md) | Cluster-specific fixes, workarounds, and failure modes ledger |
| [08 API Reference](docs/08_reference.md) | Detailed technical reference for all Python classes, methods, and modules |
| [09 Domain Model & Glossary](docs/09_glossary.md) | Technical glossary of FL, CL, ETA, and MLOps domain terminology |
| [Tech Stack](TECH_STACK.md) | Full technology inventory per layer |
| [Security Policy & Compliance](SECURITY.md) | Comprehensive cryptographic, statutory (UU PDP, GDPR), and IDPS standards |
| [Production Training Report](data/reports/summaries/training_results_report.md) | Consolidated multi-track empirical results & benchmarks |
| [Thesis Defense Dossier](docs/10_arguments.md) | Comprehensive attack-and-rebuttal analysis across 21 challenge categories with empirical anchors and code evidence |

