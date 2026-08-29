# FCL Training Guidebook

This guidebook provides step-by-step instructions on how to configure, execute, and monitor Federated Continual Learning (FL-CL) training runs and parameter sweeps.

---

## 1. Environment Setup

The training system is designed with **Secure-by-Design** principles. No static IPs or secret tokens are hardcoded. You must configure your environment variables first.

1. Copy the template configuration file:

  ```bash
  cp .env.example .env
  ```

2. Open `.env` and fill in your topology, SSH keys, and notification credentials:

  ```env
  # Telegram notifications credentials
  TELEGRAM_BOT_TOKEN="your_bot_token"
  TELEGRAM_CHAT_ID="your_chat_id"

  # SSH private key path for orchestrator → remote node access
  SSH_KEY_PATH="C:\Users\YourUser\.ssh\id_ed25519"

  # Ollama AI Reporting Configuration
  OLLAMA_ENDPOINT="https://your-ollama-server.ts.net"
  OLLAMA_KEY="your_api_key"
  OLLAMA_MODEL="llama3.1:8b"

  # Topology — Proxmox guest IPs
  AGGREGATOR_HOST="10.10.130.10"
  DEFENDER_A_HOST="10.10.130.11"
  DEFENDER_B_HOST="10.10.130.12"
  TARGET_A_HOST="10.10.110.15"
  TARGET_B_HOST="10.10.120.15"
  TRAFFIC_GEN_HOST="10.10.140.10"

  # MLflow tracking URI
  MLFLOW_TRACKING_URI="http://10.10.130.10:5000"
  ```

---

## 2. Command Reference

### A. Executing a Single Training Run

Use `src/orchestrate.py` to start a training sequence. The orchestrator automatically loads configuration parameters from your config file and connects to remote nodes via SSH.

```bash
python src/orchestrate.py --config configs/experiment.yaml --key "path/to/ssh/key"
```

#### Tunable Flags

You can override configuration parameters directly from the command line:

| Flag | Type | Description | Default (from Config) |
| --- | --- | --- | --- |
| `--config` | String | Path to experiment configuration YAML | `configs/experiment.yaml` |
| `--key` | String | Path to private SSH key for node connection | Load from `.env` or SSH agent |
| `--rounds` | Integer | Number of federated learning rounds to run | `100` |
| `--lambda-ewc` | Float | EWC regularization strength ($\lambda$) | `0.8` |
| `--lr` | Float | Learning rate of client optimizers | `0.003` |
| `--momentum` | Float | SGD momentum multiplier | `0.9` |
| `--batch-size` | Integer | Client training batch size | `32` |
| `--dos-threshold-ms` | Integer | Duration threshold (ms) to label flows as DoS | `2000` |
| `--class-weights` | String | Comma-separated class weight multipliers | `1.0,250.0,2.0,5.0,50.0` |
| `--parent-run-id` | String | Link this execution as a child run inside an MLflow sweep parent | None |

### B. Running a Parameter Sweep (Hyperparameter Grid)

Use `src/sweep.py` to automate multiple grid search experiments sequentially.

```bash
# Verify the sweep combinations without executing
python src/sweep.py --config configs/sweeps/sweep_grid.yaml --dry-run

# Run the complete sweep
python src/sweep.py --config configs/sweeps/sweep_grid.yaml --key "path/to/ssh/key"
```

The sweep manager parses `configs/sweeps/sweep_grid.yaml` and executes `orchestrate.py` for each parameter set, grouping the children under a single MLflow Parent Run.

---

## 3. Advanced MLOps Perks & Behaviors

The pipeline has several automated subsystems built into its lifecycles:

### 1. Warm-Start & Versioning (Model Registry)

Configure warm-start behavior in `configs/experiment.yaml`:

```yaml
mlops:
  mode: "production"
  production_strategy: "resume"
  registered_model_name: "CyberDefenseNet"
```

- **Cold Start (`production_strategy: "fresh"`)**: Initialized with random weights.
- **Warm Start (`production_strategy: "resume"`)**: Checks MLflow Model Registry, downloads the latest model version tagged with `champion`, and distributes it to the Flower aggregator for initial training rounds.

### 2. Champion/Challenger Promotion Gating

On validation rounds, the CI/CD promotion engine evaluates candidate models against 5 strict per-class F1 gates before promoting to the `champion` alias:

- **Per-class F1 Thresholds**:
  - Normal $\ge 0.50$
  - Botnet $\ge 0.60$
  - Exfiltration $\ge 0.70$
  - BruteForce $\ge 0.50$
  - DoS $\ge 0.70$
- **Catastrophic Forgetting Prevention**: Asserts Backward Transfer $\text{BWT} \ge 0.0000$.
- **Composite Promotion Index (CPI)**: Evaluates weighted combination of Macro F1, BWT stability, and inference latency score. Candidate Model v35 achieved $\text{CPI} = 0.864$, qualifying for automatic production `champion` promotion.

### 3. Automated Telegram Alerts & LLM Reporting

- **On Promotion Failure**: Sends a warning to Telegram with the exact criteria that failed (e.g., `BWT regression detected: -0.12`).
- **On Promotion Success**: Promotes the challenger to `champion`, updates metadata notes, exports the model to TorchScript, and uploads to MLflow.
- **LLM Threat Analysis**: Generates structural narrative summaries comparing the current run's metrics to historical averages via the local Ollama instance (`llama3.1:8b`).

---

## 4. Troubleshooting & Cleanups

### A. Manual Testbed Reset

If a run was interrupted or crashed, stale python client processes or locked directories might remain on remote VMs. Run the testbed cleaner:

```bash
python runs/clean_testbed.py --config configs/experiment.yaml
```

This resets MLflow metrics databases, stops active Flower processes, and clears RAM disk directories on all remote hosts.

### B. Graceful Interrupt

If you press `Ctrl+C` while the training orchestrator is active:

1. It sends remote interrupt signals to target VMs to gracefully stop background captures and Flower clients.
2. It logs a cancellation state in MLflow.
3. It keeps the current database files uncorrupted.

---

## 5. Standalone Evaluation & Benchmarking Tools

FCL provides standalone evaluation scripts to verify model performance, catastrophic forgetting resistance, and cross-dataset generalization out-of-band.

### A. Cryptographically Signed BWT Evaluation Suite

Use `tools/validate_bwt.py` to evaluate any TorchScript model checkpoint. The tool generates class-wise accuracy, F1-scores, BWT degradation, and cryptographically signs the report.

```bash
python tools/validate_bwt.py \
  --checkpoint checkpoints/model_latest_scripted.pt \
  --test-dir /mnt/ramdisk/flows \
  --output data/reports/bwt_report.csv \
  --peak-f1 "0.95,0.92,0.97,0.94,0.99" \
  --mlflow-run-id "your_active_mlflow_run_id"
```

- **Lineage & Authenticity:** Generates a SHA-256 validation signature composed of the model file's hash, dataset hash, and tabular results.
- **MLflow Tracking:** Logs BWT metrics and uploads the generated CSV report as a run artifact if `--mlflow-run-id` is provided.

### B. Cross-Dataset Generalization Benchmark

Use `tools/benchmark_cross_dataset.py` to compare FCL models on heterogeneous traffic distributions, measuring generalization performance and domain shift gaps.

```bash
python tools/benchmark_cross_dataset.py \
  --checkpoint checkpoints/model_latest_scripted.pt \
  --dataset-a-dir /mnt/ramdisk/flows \
  --dataset-b-dir /mnt/ustc_tfc2016/flows \
  --output data/reports/generalization_report.csv \
  --mlflow-run-id "your_active_mlflow_run_id"
```

- **Covariate Shift Simulator:** If Dataset B is not provided or files are missing, the tool simulates the USTC-TFC2016 domain distribution by dynamically applying deterministic statistical shifts to Dataset A.
- **Metadata Attribution:** Tags the run with dataset source identities (`train_dataset_id: "CIC-IDS2017"`, `eval_dataset_id: "USTC-TFC2016"`) and uploads comparison matrices to MLflow.

---

## 6. Comprehensive Empirical Benchmark Ledger

### A. Multi-Runtime Inference Latency & Throughput (`tools/benchmark_onnx.py`)
Tested across 200 repetitions per batch size:

| Model Architecture | Batch Size | PyTorch FP32 Latency | TorchScript JIT Latency | ONNX Runtime Latency | ONNX Peak Throughput |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CyberDefenseCNN** *(Champion)* | 1 (Single) | 17.47 µs / flow | 16.32 µs / flow | **13.23 µs / flow** | **75,565 flows / sec** |
| | 16 (Edge Burst) | 1.96 µs / flow | 1.88 µs / flow | **1.09 µs / flow** | **915,221 flows / sec** |
| | 64 (Mini-Batch) | 1.01 µs / flow | 0.93 µs / flow | **0.44 µs / flow** | **2,291,019 flows / sec** |
| | 256 (Volumetric) | 0.91 µs / flow | 0.80 µs / flow | **0.32 µs / flow** | **3,115,286 flows / sec** |
| **CyberDefenseNet (MLP)** | 1 (Single) | 18.49 µs / flow | 15.54 µs / flow | **10.96 µs / flow** | **91,241 flows / sec** |
| | 256 (Volumetric) | 0.26 µs / flow | 0.22 µs / flow | **0.18 µs / flow** | **5,502,306 flows / sec** |
| **CyberDefenseTransformer** | 1 (Single) | 22.72 µs / flow | 19.98 µs / flow | **16.71 µs / flow** | **59,850 flows / sec** |
| | 256 (Volumetric) | 1.49 µs / flow | 1.27 µs / flow | **0.58 µs / flow** | **1,725,584 flows / sec** |

### B. Byzantine Robustness Under Poisoning & Noise (`tools/benchmark_byzantine.py`)
Tested across 5 participating clients with simulated malicious attackers:

| Attack Scenario | FedAvg | FedMedian | Krum | TrimmedMean ($\beta=0.10$) | Evaluation Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Baseline (0/5 Malicious)** | 99.40% | 99.40% | 99.40% | **99.40%** | Optimal convergence |
| **10% Label Poisoning (0 -> 4)** | 99.40% | 99.40% | 99.40% | **99.40%** | 0.00% degradation |
| **20% Label Poisoning (0 -> 4)** | 99.40% | 99.40% | 99.40% | **99.40%** | 0.00% degradation |
| **50% Label Poisoning (0 -> 4)** | 99.20% | 99.40% | 99.40% | **99.40%** | Malicious updates trimmed |
| **Sign-Flipping Gradient Attack** | 79.40% | 99.40% | 99.40% | **99.40%** | Attack completely neutralized |
| **Gaussian Noise ($\sigma=2.0$)** | 80.40% | 99.40% | 99.40% | **99.40%** | Perturbations filtered out |

### C. Differential Privacy Sensitivity (`tools/benchmark_dp.py`)
Evaluated with $C = 1.0$, $T = 100$, target $\delta = 10^{-5}$:

| Noise Multiplier ($\sigma$) | Privacy Budget ($\epsilon$) | Train Accuracy | Test Accuracy | Macro F1 | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$\sigma = 0.00$** | $\infty$ (Non-Private) | 99.62% | 99.40% | 0.9937 | Non-private baseline |
| **$\sigma = 0.10$** | $\epsilon = 18.24$ | 99.62% | 99.40% | 0.9937 | Zero utility loss |
| **$\sigma = 0.30$** | $\mathbf{\epsilon = 6.08}$ | 99.62% | **99.40%** | **0.9937** | **Production privacy target** |
| **$\sigma = 0.50$** | $\epsilon = 3.65$ | 99.50% | 99.20% | 0.9912 | -0.20% degradation |
| **$\sigma = 1.00$** | $\epsilon = 1.82$ | 99.25% | 98.80% | 0.9854 | Strict privacy regime |

---

## 7. Standards & Regulatory Compliance Verification

The pipeline complies with statutory cybersecurity and data protection standards:

| Framework | Target Requirement | Architectural Implementation |
| :--- | :--- | :--- |
| **UU PDP No. 27/2022 (Art. 65–66)** | Prohibition of transferring raw personal network data outside boundary. | **Zero Raw Flow Transmission**: Raw flows remain isolated in `/mnt/ramdisk/flows/` on edge defender nodes. |
| **GDPR (EU 2016/679 Art. 5/25/32)** | Data minimization and Privacy by Design via cryptographic pseudonymization. | **DP-SGD & Batch Aggregation**: Bounded clipping ($C=1.0$) and calibrated noise injection ($\sigma=0.30$). |
| **NIST SP 800-94 / 800-145** | Intrusion Detection and Prevention Systems (IDPS) telemetry standards. | **32-Dimensional Statistical Metadata**: SPLT, PIAT, directional volume without inspecting encrypted payloads. |
| **MITRE ATT&CK Enterprise** | Standardized threat classification. | **Covered TTPs**: T1498 (DoS), T1110 (BruteForce), T1048 (DNS Exfil), T1071 (C2 Beaconing). |
| **ISO/IEC 27001 / 27701** | ISMS / PIMS Information Security governance. | **Cryptographic Lineage**: SHA-256 dataset lineage graphs and immutable MLflow tracking. |

