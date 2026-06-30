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
| `--lambda-ewc` | Float | EWC regularization strength ($\lambda$) | `0.1` |
| `--lr` | Float | Learning rate of client optimizers | `0.005` |
| `--momentum` | Float | SGD momentum multiplier | `0.9` |
| `--batch-size` | Integer | Client training batch size | `32` |
| `--dos-threshold-ms` | Integer | Duration threshold (ms) to label flows as DoS | `2000` |
| `--class-weights` | String | Comma-separated class weight multipliers | `2.0,150.0,3.0,7.0,18.0` |
| `--parent-run-id` | String | Link this execution as a child run inside an MLflow sweep parent | None |

### B. Running a Parameter Sweep (Hyperparameter Grid)
Use `src/sweep.py` to automate multiple grid search experiments sequentially.

```bash
# Verify the sweep combinations without executing
python src/sweep.py --config configs/sweep_grid.yaml --dry-run

# Run the complete sweep
python src/sweep.py --config configs/sweep_grid.yaml --key "path/to/ssh/key"
```

The sweep manager parses `configs/sweep_grid.yaml` and executes `orchestrate.py` for each parameter set, grouping the children under a single MLflow Parent Run.

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
On validation rounds, the aggregator automatically decides whether to promote the model using strict criteria:
- **Per-class F1-score**: Evaluates each class individually.
- **Catastrophic Forgetting Prevention**: Verifies that Backward Transfer (BWT) $\ge 0$. Any drop below 0 is flagged as forgetting and blocks promotion.
- **Communication Budget**: Rejects models with client-aggregator transmission overhead $> 200$ MB.

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
