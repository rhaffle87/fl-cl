"""
server.py — Flower Federated Averaging Aggregator Server

Orchestrates global model training by collecting and averaging weight updates
from all defender client nodes via gRPC and logging metrics to MLflow.

MLOps features:
  - Model checkpointing (saves best model by loss)
  - TorchScript export for deployment validation
  - Full experiment config logged as MLflow artifact
  - Git commit hash tagged for traceability

Deploy on: FL Aggregator (LXC 300)
Usage:
    python3 server.py --rounds 100 --min-clients 2 --mlflow-uri http://localhost:5000
"""

import argparse
import os
import subprocess
import json
import shutil
import sqlite3
from collections import OrderedDict
from pathlib import Path

import flwr as fl
import mlflow
import mlflow.artifacts
import torch

from model import CyberDefenseNet


@mlflow.trace(name="weighted_avg")
def weighted_avg(metrics):
    """Aggregate overall and class-wise accuracy metrics weighted by dataset size."""
    total_samples = sum([n for n, _ in metrics])
    if total_samples == 0:
        return {"accuracy": 0.0}

    # Aggregate overall accuracy
    accs = [n * m["accuracy"] for n, m in metrics]
    avg_accuracy = sum(accs) / total_samples

    aggregated_metrics = {"accuracy": avg_accuracy}

    # Aggregate class-wise accuracies (0: Normal, 1: Botnet, 2: Exfiltration, 3: BruteForce, 4: DoS)
    for i in range(5):
        class_key = f"accuracy_class_{i}"
        class_vals = []
        class_weights = []
        for n, m in metrics:
            val = m.get(class_key, -1.0)
            if val >= 0.0:  # Skip clients that had zero samples for this class
                class_vals.append(val)
                class_weights.append(n)
        if sum(class_weights) > 0:
            aggregated_metrics[class_key] = sum([w * v for w, v in zip(class_weights, class_vals)]) / sum(class_weights)
        else:
            aggregated_metrics[class_key] = -1.0

    # Aggregate class-wise F1 scores
    for i in range(5):
        f1_key = f"f1_class_{i}"
        f1_vals = []
        f1_weights = []
        for n, m in metrics:
            val = m.get(f1_key, -1.0)
            if val >= 0.0:
                f1_vals.append(val)
                f1_weights.append(n)
        if sum(f1_weights) > 0:
            aggregated_metrics[f1_key] = sum([w * v for w, v in zip(f1_weights, f1_vals)]) / sum(f1_weights)
        else:
            aggregated_metrics[f1_key] = -1.0

    return aggregated_metrics


class MLflowFedAvg(fl.server.strategy.FedAvg):
    """Custom FedAvg strategy with MLflow logging, checkpointing, and TorchScript export."""

    def __init__(self, checkpoint_dir: str = "/opt/mlflow-artifacts/checkpoints",
                 export_torchscript: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.checkpoint_dir = checkpoint_dir
        self.export_torchscript = export_torchscript
        self.best_loss = float("inf")
        self.best_round = 0
        self.best_accuracy = 0.0
        self.best_metrics = {}
        self.latest_loss = 0.0
        self.latest_accuracy = 0.0
        self.latest_metrics = {}
        
        # New MLOps sweep metrics tracking
        self.peak_f1 = {i: 0.0 for i in range(5)}
        self.history_records = []
        self.fit_clients = 0
        
        # Calculate parameter size in bytes (float32 = 4 bytes)
        dummy_model = CyberDefenseNet()
        self.param_bytes = sum(p.numel() * 4 for p in dummy_model.parameters())

        # Security audit: enforce strict 0700 owner-only permissions on directories
        try:
            os.makedirs(self.checkpoint_dir, mode=0o700, exist_ok=True)
            os.chmod(self.checkpoint_dir, 0o700)
        except Exception as e:
            print(f"[server] Warning: Could not enforce directory permissions on {self.checkpoint_dir}: {e}")

    @mlflow.trace(name="aggregate_evaluate")
    def aggregate_evaluate(self, server_round, results, failures):
        aggregated_result = super().aggregate_evaluate(server_round, results, failures)
        if aggregated_result:
            loss, metrics = aggregated_result
            accuracy = metrics.get("accuracy", 0.0)
            self.latest_loss = loss
            self.latest_accuracy = accuracy
            self.latest_metrics = metrics

            print(f"[server] Round {server_round} Aggregated Loss: {loss:.4f} | Accuracy: {accuracy:.4f}")
            mlflow.log_metric("loss", loss, step=server_round)
            for k, v in metrics.items():
                mlflow.log_metric(k, v, step=server_round)

            # Estimate and log communication bytes (2 directions: server->client, client->server)
            comm_bytes = 2 * self.param_bytes * self.fit_clients
            mlflow.log_metric("communication_bytes", float(comm_bytes), step=server_round)

            # Calculate and log BWT deltas, and keep peak F1 up to date
            for i in range(5):
                f1_key = f"f1_class_{i}"
                f1_val = metrics.get(f1_key, -1.0)
                if f1_val >= 0.0:
                    # Update peak F1
                    self.peak_f1[i] = max(self.peak_f1[i], f1_val)
                    # BWT delta
                    bwt_delta = f1_val - self.peak_f1[i]
                    mlflow.log_metric(f"bwt_class_{i}", bwt_delta, step=server_round)
                    metrics[f"bwt_class_{i}"] = bwt_delta
                else:
                    metrics[f"bwt_class_{i}"] = -1.0

            # Record round details for history table
            record = {
                "round": int(server_round),
                "loss": float(loss),
                "accuracy": float(accuracy),
                "communication_bytes": int(comm_bytes)
            }
            for i in range(5):
                record[f"f1_class_{i}"] = float(metrics.get(f"f1_class_{i}", -1.0))
                record[f"bwt_class_{i}"] = float(metrics.get(f"bwt_class_{i}", -1.0))
            self.history_records.append(record)

            # Checkpoint best model
            if loss < self.best_loss:
                self.best_loss = loss
                self.best_round = server_round
                self.best_accuracy = accuracy
                self.best_metrics = metrics.copy()
                mlflow.log_metric("best_loss", loss, step=server_round)
                mlflow.log_metric("best_round", server_round, step=server_round)
                print(f"[server] ★ New best model at round {server_round} (loss={loss:.4f})")

        return aggregated_result

    @mlflow.trace(name="aggregate_fit")
    def aggregate_fit(self, server_round, results, failures):
        self.fit_clients = len(results)
        aggregated = super().aggregate_fit(server_round, results, failures)

        # Save model checkpoint from aggregated parameters
        if aggregated is not None:
            parameters, config = aggregated
            ndarrays = fl.common.parameters_to_ndarrays(parameters)

            # Security + stability guard: sanitize NaN/Inf values before checkpointing
            sanitized_arrays = []
            total_nan = 0
            for arr in ndarrays:
                import numpy as np
                nan_count = np.isnan(arr).sum() + np.isinf(arr).sum()
                if nan_count > 0:
                    total_nan += int(nan_count)
                    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
                sanitized_arrays.append(arr)
            if total_nan > 0:
                print(f"[server] WARNING: Aggregated weights contained {total_nan} NaN/Inf values at round {server_round}. Sanitized to zero.")

            model = CyberDefenseNet()
            state_dict = OrderedDict(
                {k: torch.tensor(v) for k, v in zip(model.state_dict().keys(), sanitized_arrays)}
            )
            model.load_state_dict(state_dict, strict=True)

            # Save PyTorch checkpoint
            ckpt_path = os.path.join(self.checkpoint_dir, f"model_round_{server_round:04d}.pt")
            torch.save(model.state_dict(), ckpt_path)
            # Security audit: enforce strict 0600 owner-only permissions on weights
            os.chmod(ckpt_path, 0o600)

            # Save latest checkpoint (always overwrite)
            latest_path = os.path.join(self.checkpoint_dir, "model_latest.pt")
            torch.save(model.state_dict(), latest_path)
            os.chmod(latest_path, 0o600)

            # Export TorchScript for deployment validation
            if self.export_torchscript:
                model.eval()
                scripted = torch.jit.script(model)
                ts_path = os.path.join(self.checkpoint_dir, "model_latest_scripted.pt")
                scripted.save(ts_path)
                os.chmod(ts_path, 0o600)

            if server_round % 10 == 0:
                print(f"[server] Checkpoint saved: {ckpt_path}")

        return aggregated



def get_git_hash(cli_commit=None):
    """Get current git commit hash for run traceability."""
    if cli_commit and cli_commit != "unknown":
        return cli_commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def enable_sqlite_wal(db_path: str = "/root/mlflow.db"):
    """Enable SQLite WAL (Write-Ahead Logging) mode for performance optimization."""
    if not os.path.exists(db_path):
        db_path = "mlflow.db"

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            mode = cursor.fetchone()[0]
            conn.close()
            print(f"[server] SQLite WAL Mode enabled: {mode} (on {db_path})")
            return True
        except Exception as e:
            print(f"[server] Warning: Could not enable WAL mode: {e}")
    else:
        print(f"[server] SQLite DB not found at {db_path}, skipping WAL optimization.")
    return False


def sanitize_config(config_path: str) -> str:
    """Sanitize sensitive credentials from config and write to a safe tmp file."""
    try:
        import yaml
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Redact telegram bot token if present
        if isinstance(config, dict) and "notifications" in config:
            tg_conf = config["notifications"].get("telegram", {})
            if isinstance(tg_conf, dict) and "bot_token" in tg_conf and tg_conf["bot_token"]:
                tg_conf["bot_token"] = "[REDACTED]"
        
        sanitized_path = "/tmp/sanitized_experiment.yaml"
        with open(sanitized_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        return sanitized_path
    except Exception as e:
        print(f"[server] Warning: Sanitization failed: {e}. Logging original config.")
        return config_path


def main():
    parser = argparse.ArgumentParser(description="FL-CL Aggregator Server")
    parser.add_argument("--address", default="0.0.0.0:8080", help="Server bind address")
    parser.add_argument("--rounds", type=int, default=10, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, default=2, help="Minimum clients per round")
    parser.add_argument("--mlflow-uri", default="http://localhost:5000", help="MLflow tracking URI")
    parser.add_argument("--checkpoint-dir", default="/opt/mlflow-artifacts/checkpoints",
                        help="Directory to save model checkpoints")
    parser.add_argument("--config-file", default="", help="Experiment config YAML to log as artifact")
    parser.add_argument("--git-commit", default="unknown", help="Git commit hash from orchestrator workstation")
    parser.add_argument("--mlops-mode", default="experimental", choices=["experimental", "production"],
                        help="MLops mode (experimental or production)")
    parser.add_argument("--production-strategy", default="resume", choices=["resume", "fresh"],
                        help="Production warm-start checkpoint strategy")
    parser.add_argument("--parent-run-id", default="", help="MLflow parent run ID for sweep tracking")
    parser.add_argument("--dataset-hash", default="", help="SHA-256 hash of the defender datasets")
    parser.add_argument("--lr", type=float, default=0.01, help="Training learning rate")
    parser.add_argument("--batch-size", type=int, default=32, help="Training batch size")
    parser.add_argument("--ewc-lambda", type=float, default=0.4, help="EWC lambda")
    parser.add_argument("--class-weights", default="12.0,3.0,3.0,15.0,1.0", help="Comma-separated class weights")
    args = parser.parse_args()

    # Performance optimization: enable SQLite Write-Ahead Logging
    enable_sqlite_wal()

    # Set up MLflow
    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment("FL-CL-CyberDefense")
    mlflow.enable_system_metrics_logging()

    # Security audit: restrict directory permissions
    try:
        os.makedirs(args.checkpoint_dir, mode=0o700, exist_ok=True)
        os.chmod(args.checkpoint_dir, 0o700)
    except Exception as e:
        print(f"[server] Warning: Could not enforce base checkpoint directory permissions: {e}")

    # MLOps Warm-Start Checkpoint Resumption
    initial_parameters = None
    resumed_from_version = None
    resumed_from_run_id = None
    latest_ckpt_path = os.path.join(args.checkpoint_dir, "model_latest.pt")
    
    if args.production_strategy == "resume":
        if args.mlops_mode == "production":
            # Attempt to download the champion checkpoint from MLflow registry using model version alias
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient(tracking_uri=args.mlflow_uri)
                model_name = "CyberDefenseNet"
                print(f"[server] Production Warm-Start: Querying MLflow Model Registry for '{model_name}' alias 'champion'...")
                model_version_details = client.get_model_version_by_alias(model_name, "champion")
                resumed_from_version = model_version_details.version
                resumed_from_run_id = model_version_details.run_id
                
                print(f"[server] Production Warm-Start: Downloading model_latest.pt from run {resumed_from_run_id}...")
                downloaded_path = mlflow.artifacts.download_artifacts(
                    run_id=resumed_from_run_id,
                    artifact_path="model/model_latest.pt"
                )
                if downloaded_path and os.path.exists(downloaded_path):
                    latest_ckpt_path = downloaded_path
                    print(f"[server] Production Warm-Start: Successfully downloaded champion weights to {downloaded_path}")
            except Exception as e:
                print(f"[server] Registry lookup for 'champion' failed ({e}). Falling back to local check.")
        else:
            print(f"[server] Experimental Warm-Start: Checking local checkpoint {latest_ckpt_path}...")

        if os.path.exists(latest_ckpt_path):
            print(f"[server] Warm-Start: Loading weights from {latest_ckpt_path}")
            try:
                model = CyberDefenseNet()
                # Security audit: use weights_only=True to prevent arbitrary code execution
                model.load_state_dict(torch.load(latest_ckpt_path, map_location="cpu", weights_only=True))
                
                ndarrays = [val.cpu().numpy() for _, val in model.state_dict().items()]
                initial_parameters = fl.common.ndarrays_to_parameters(ndarrays)
                
                # If we didn't query the registry successfully but loaded locally, try to read local metadata
                if not resumed_from_version:
                    latest_meta_path = os.path.join(args.checkpoint_dir, "model_latest_metadata.json")
                    if os.path.exists(latest_meta_path):
                        with open(latest_meta_path, "r") as f:
                            meta = json.load(f)
                            resumed_from_version = meta.get("model_version")
                            resumed_from_run_id = meta.get("run_id")
            except Exception as e:
                print(f"[server] Failed to load latest checkpoint: {e}. Starting fresh.")
                initial_parameters = None
        else:
            print("[server] Warm-Start: No prior checkpoint found. Initializing new model weights.")
    else:
        print("[server] Fresh Start: Ignored prior checkpoints. Initializing new model weights from scratch.")

    print(f"[server] Starting Flower aggregator on {args.address}")
    print(f"[server] Rounds: {args.rounds} | Min clients: {args.min_clients}")
    print(f"[server] MLflow Server: {args.mlflow_uri}")
    print(f"[server] Checkpoints Base Directory: {args.checkpoint_dir}")
    print(f"[server] MLOps Mode: {args.mlops_mode} | Production Strategy: {args.production_strategy}")

    with mlflow.start_run(run_name="FL-CL-Orchestrated-Run") as run:
        # Write run ID to a temporary file so orchestrator can retrieve it
        try:
            with open("/tmp/current_run_id.txt", "w") as f:
                f.write(run.info.run_id)
        except Exception as e:
            print(f"[server] Warning: Could not write current run ID file: {e}")

        # Define run-specific checkpoint directory to isolate outputs
        run_checkpoint_dir = os.path.join(args.checkpoint_dir, run.info.run_id)
        
        # Instantiate strategy inside the MLflow run context
        strategy = MLflowFedAvg(
            checkpoint_dir=run_checkpoint_dir,
            export_torchscript=True,
            initial_parameters=initial_parameters,
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=args.min_clients,
            min_evaluate_clients=args.min_clients,
            min_available_clients=args.min_clients,
            evaluate_metrics_aggregation_fn=weighted_avg,
        )

        # Link child run to parent run in MLflow if parent run ID is provided
        if args.parent_run_id:
            mlflow.set_tag("mlflow.parentRunId", args.parent_run_id)
            print(f"[server] Linked child run to parent run ID: {args.parent_run_id}")

        # Performance optimization: batch log parameters and tags (reduces REST calls to 2)
        params = {
            "fl_rounds": args.rounds,
            "min_clients": args.min_clients,
            "lr": args.lr,
            "batch_size": args.batch_size,
            "ewc_lambda": args.ewc_lambda,
            "class_weights": args.class_weights
        }
        if args.dataset_hash:
            params["dataset_hash"] = args.dataset_hash
            print(f"[server] Registered dataset hash parameter: {args.dataset_hash}")
        mlflow.log_params(params)

        tags = {
            "git_commit": get_git_hash(args.git_commit),
            "mlops_mode": args.mlops_mode,
            "production_strategy": args.production_strategy if args.mlops_mode == "production" else "N/A",
            "warm_started": "True" if initial_parameters is not None else "False"
        }
        if resumed_from_run_id:
            tags["resumed_from_run_id"] = resumed_from_run_id
        if resumed_from_version:
            tags["resumed_from_version"] = str(resumed_from_version)
        mlflow.set_tags(tags)

        # Construct initial run description (notes) with rich markdown information
        run_desc = (
            f"### Federated Continual Learning Run\n"
            f"- **MLOps Mode**: `{args.mlops_mode.upper()}`\n"
            f"- **Production Strategy**: `{args.production_strategy if args.mlops_mode == 'production' else 'N/A'}`\n"
            f"- **Git Commit**: `{get_git_hash(args.git_commit)}`\n"
            f"- **FL Rounds**: `{args.rounds}`\n"
            f"- **Warm Started**: `{'True' if initial_parameters is not None else 'False'}`\n"
        )
        if resumed_from_run_id:
            run_desc += f"- **Resumed From Run ID**: `{resumed_from_run_id}` (Version `{resumed_from_version}`)\n"
        
        mlflow.set_tag("mlflow.note.content", run_desc)

        # Log config file as sanitized artifact if provided
        if args.config_file and os.path.exists(args.config_file):
            sanitized_path = sanitize_config(args.config_file)
            mlflow.log_artifact(sanitized_path, artifact_path="config")
            print(f"[server] Logged sanitized config artifact: {sanitized_path}")

        try:
            fl.server.start_server(
                server_address=args.address,
                config=fl.server.ServerConfig(num_rounds=args.rounds),
                strategy=strategy,
            )
        except (KeyboardInterrupt, SystemExit):
            print("\n[server] [!] Caught termination signal. Initiating graceful early shutdown...")

        # Log final best checkpoint as MLflow artifact using MLflow 3.x LoggedModel entities
        # Determine the best checkpoint path from best_round
        best_round_filename = f"model_round_{strategy.best_round:04d}.pt"
        run_best_ckpt = os.path.join(run_checkpoint_dir, best_round_filename)
        # Fallback if best_round file doesn't exist
        if not os.path.exists(run_best_ckpt):
            run_best_ckpt = os.path.join(run_checkpoint_dir, "model_latest.pt")
        
        if os.path.exists(run_best_ckpt):
            import pandas as pd
            import numpy as np

            # Instantiate and load model safely
            model = CyberDefenseNet()
            model.load_state_dict(torch.load(run_best_ckpt, map_location="cpu", weights_only=True))
            model.eval()

            # Create dummy input example to define signature
            input_example = np.random.randn(1, 32).astype(np.float32)

            # Log PyTorch model with parameters
            model_info = mlflow.pytorch.log_model(
                pytorch_model=model,
                artifact_path="cyber_defense_model",
                registered_model_name="CyberDefenseNet",
                input_example=input_example,
                serialization_format="pickle"
            )
            new_version = model_info.registered_model_version
            print(f"[server] Logged model to artifact path. ID: {model_info.model_id} | Registry Version: {new_version}")

            # Inspect and retrieve LoggedModel
            logged_model = mlflow.get_logged_model(model_info.model_id)

            # Define dataset representation using MLflow 3.x Dataset entity
            dataset_summary = pd.DataFrame([
                {"class": "Normal", "defender_a": 22, "defender_b": 10},
                {"class": "Botnet", "defender_a": 10, "defender_b": 12},
                {"class": "Exfiltration", "defender_a": 581, "defender_b": 636},
                {"class": "BruteForce", "defender_a": 4, "defender_b": 30},
                {"class": "DoS", "defender_a": 2464, "defender_b": 1409}
            ])
            train_dataset = mlflow.data.from_pandas(dataset_summary, name="aggregated_training_flows")

            # Log final metrics linked to LoggedModel and training dataset
            mlflow.log_metrics(
                metrics={
                    "final_best_loss": strategy.best_loss,
                    "final_best_round": float(strategy.best_round),
                },
                model_id=logged_model.model_id,
                dataset=train_dataset
            )
            print(f"[server] Successfully linked model metrics to model_id: {logged_model.model_id}")

            # Update run description notes with final performance details
            try:
                run_desc += (
                    f"\n### Final Performance Summary\n"
                    f"- **Global Accuracy**: `{strategy.best_accuracy*100:.4f}%` (Best Round: `{strategy.best_round}`)\n"
                    f"- **Global Loss**: `{strategy.best_loss:.6f}`\n"
                    f"- **Class-wise Accuracies**:\n"
                )
                class_labels = {0: "Normal", 1: "Botnet", 2: "DNS Exfiltration", 3: "SSH Brute Force", 4: "DoS"}
                for i in range(5):
                    class_acc = strategy.best_metrics.get(f"accuracy_class_{i}")
                    if class_acc is not None:
                        run_desc += f"  - **{class_labels[i]}**: `{class_acc*100:.2f}%`\n"
                mlflow.set_tag("mlflow.note.content", run_desc)
                print("[server] Updated MLflow run description with final metrics summary.")
            except Exception as note_err:
                print(f"[server] Warning: Could not update run description note: {note_err}")

            # Log custom Evaluation Table to MLflow
            try:
                import pandas as pd
                class_labels = {0: "Normal", 1: "Botnet", 2: "DNS Exfiltration", 3: "SSH Brute Force", 4: "DoS"}
                eval_data = []
                for i in range(5):
                    class_acc = strategy.best_metrics.get(f"accuracy_class_{i}")
                    eval_data.append({
                        "class_id": i,
                        "class_name": class_labels[i],
                        "accuracy": float(class_acc) if class_acc is not None else 0.0,
                        "status": "Perfect" if class_acc == 1.0 else "Acceptable" if class_acc >= 0.99 else "Needs Improvement"
                    })
                eval_df = pd.DataFrame(eval_data)
                mlflow.log_table(data=eval_df, artifact_file="evaluation_metrics_summary.json")
                print("[server] Logged evaluation metrics summary table to MLflow.")

                if strategy.history_records:
                    history_df = pd.DataFrame(strategy.history_records)
                    mlflow.log_table(data=history_df, artifact_file="evaluation_history.json")
                    print("[server] Logged evaluation history table to MLflow.")
            except Exception as table_err:
                print(f"[server] Warning: Could not log evaluation table artifact: {table_err}")

            # Promote model to master checkpoint directory
            print(f"[server] Copying best checkpoint to master directory: {latest_ckpt_path}")
            shutil.copy(run_best_ckpt, latest_ckpt_path)
            os.chmod(latest_ckpt_path, 0o600)

            # Manage Model Registry tagging and promotion via MlflowClient
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                model_name = "CyberDefenseNet"
                
                # Update high-level registered model metadata (description and tags)
                registered_model_desc = (
                    "Global federated model for 5-class encrypted network intrusion detection. "
                    "Employs PyTorch (CyberDefenseNet architecture) combined with client-side Avalanche EWC "
                    "(Elastic Weight Consolidation) to adapt incrementally to new security threats without "
                    "forgetting historical signatures."
                )
                client.update_registered_model(
                    name=model_name,
                    description=registered_model_desc
                )
                client.set_registered_model_tag(model_name, "task", "Network Intrusion Detection")
                client.set_registered_model_tag(model_name, "framework", "PyTorch")
                client.set_registered_model_tag(model_name, "input_dim", "32")
                client.set_registered_model_tag(model_name, "classes", "0: Normal, 1: Botnet, 2: DNS Exfiltration, 3: SSH Brute Force, 4: DoS")
                client.set_registered_model_tag(model_name, "cl_strategy", "EWC")
                
                # Construct detailed model version description
                version_desc = (
                    f"MLOps Mode: {args.mlops_mode}\n"
                    f"Production Strategy: {args.production_strategy if args.mlops_mode == 'production' else 'N/A'}\n"
                    f"Git Commit: {get_git_hash(args.git_commit)}\n"
                    f"FL Rounds: {args.rounds}\n"
                    f"Evaluation Metrics at Best Round {strategy.best_round}:\n"
                    f"  - Overall Accuracy: {strategy.best_accuracy*100:.2f}%\n"
                    f"  - Aggregated Loss: {strategy.best_loss:.4f}\n"
                )
                class_labels = {0: "Normal", 1: "Botnet", 2: "DNS Exfiltration", 3: "SSH Brute Force", 4: "DoS"}
                for i in range(5):
                    class_acc = strategy.best_metrics.get(f"accuracy_class_{i}")
                    if class_acc is not None:
                        version_desc += f"  - Class {i} ({class_labels[i]}): {class_acc*100:.2f}%\n"
                
                client.update_model_version(
                    name=model_name,
                    version=str(new_version),
                    description=version_desc
                )

                # Set tags on model version object
                client.set_model_version_tag(model_name, str(new_version), "mlops_mode", args.mlops_mode)
                client.set_model_version_tag(model_name, str(new_version), "git_commit", get_git_hash(args.git_commit))
                client.set_model_version_tag(model_name, str(new_version), "accuracy", f"{strategy.best_accuracy:.6f}")
                client.set_model_version_tag(model_name, str(new_version), "loss", f"{strategy.best_loss:.6f}")
                client.set_model_version_tag(model_name, str(new_version), "fl_rounds", str(args.rounds))
                
                class_3_acc = strategy.best_metrics.get("accuracy_class_3")
                if class_3_acc is not None:
                    client.set_model_version_tag(model_name, str(new_version), "accuracy_class_3", f"{class_3_acc:.6f}")

                if resumed_from_version:
                    client.set_model_version_tag(model_name, str(new_version), "parent_version", str(resumed_from_version))
                if resumed_from_run_id:
                    client.set_model_version_tag(model_name, str(new_version), "resumed_from_run_id", str(resumed_from_run_id))
                
                # Assign model version aliases mindfully (MLflow 3.x aliases replace deprecated stages)
                if args.mlops_mode == "production":
                    # Retrieve current champion metrics if any
                    champ_accuracy = 0.0
                    champ_loss = float("inf")
                    try:
                        current_champ = client.get_model_version_by_alias(model_name, "champion")
                        # Read metrics from tags
                        champ_accuracy = float(current_champ.tags.get("accuracy", 0.0))
                        champ_loss = float(current_champ.tags.get("loss", float("inf")))
                        print(f"[server] Current Champion Version: {current_champ.version} | Accuracy: {champ_accuracy*100:.2f}% | Loss: {champ_loss:.4f}")
                    except Exception:
                        print("[server] No active champion model found in Model Registry.")

                    # Calculate average BWT for candidate best metrics
                    bwt_vals = []
                    for i in range(5):
                        bwt_val = strategy.best_metrics.get(f"bwt_class_{i}", -1.0)
                        f1_val = strategy.best_metrics.get(f"f1_class_{i}", -1.0)
                        if f1_val >= 0.0 and bwt_val != -1.0:
                            bwt_vals.append(bwt_val)
                    avg_bwt = sum(bwt_vals) / len(bwt_vals) if len(bwt_vals) > 0 else 0.0

                    # Validation Gate Criteria:
                    # 1. accuracy >= champion_accuracy - 0.005 (0.5% tolerance)
                    # 2. loss <= champion_loss + 0.05
                    # 3. average BWT >= -0.05
                    candidate_acc = strategy.best_accuracy
                    candidate_loss = strategy.best_loss
                    
                    acc_ok = candidate_acc >= (champ_accuracy - 0.005)
                    loss_ok = candidate_loss <= (champ_loss + 0.05)
                    bwt_ok = avg_bwt >= -0.05
                    
                    passed_gate = acc_ok and loss_ok and bwt_ok
                    
                    print(f"[server] Validation Gate Metrics Checklist:")
                    print(f"  - Overall Accuracy: candidate={candidate_acc:.6f}, champion={champ_accuracy:.6f} -> {'PASS' if acc_ok else 'FAIL'}")
                    print(f"  - Aggregated Loss: candidate={candidate_loss:.6f}, champion={champ_loss:.6f} -> {'PASS' if loss_ok else 'FAIL'}")
                    print(f"  - Average BWT Delta: candidate={avg_bwt:.6f} (threshold >= -0.05) -> {'PASS' if bwt_ok else 'FAIL'}")

                    if passed_gate:
                        print(f"[server] MLOps Promotion: Validation GATE PASSED. Promoting version {new_version} to 'champion'...")
                        client.set_registered_model_alias(
                            name=model_name,
                            alias="champion",
                            version=str(new_version)
                        )
                        # For backwards compatibility with older dashboard layouts, also set deprecated stage
                        try:
                            client.transition_model_version_stage(
                                name=model_name,
                                version=str(new_version),
                                stage="Production",
                                archive_existing_versions=True
                            )
                        except Exception:
                            pass
                    else:
                        print(f"[server] MLOps Promotion: Validation GATE FAILED. Assigning 'challenger' alias to version {new_version}...")
                        client.set_registered_model_alias(
                            name=model_name,
                            alias="challenger",
                            version=str(new_version)
                        )
                else:
                    print(f"[server] MLOps Promotion (experimental mode): Assigning 'challenger' alias to version {new_version}...")
                    client.set_registered_model_alias(
                        name=model_name,
                        alias="challenger",
                        version=str(new_version)
                    )
            except Exception as registry_err:
                print(f"[server] Warning: Model registry metadata tagging or promotion failed: {registry_err}")

            # Write model latest metadata json
            meta_data = {
                "run_id": run.info.run_id,
                "model_version": str(new_version)
            }
            latest_meta_path = os.path.join(args.checkpoint_dir, "model_latest_metadata.json")
            with open(latest_meta_path, "w") as f:
                json.dump(meta_data, f, indent=2)
            os.chmod(latest_meta_path, 0o600)
            print(f"[server] Updated master latest model metadata: {meta_data}")

        run_ckpt_path = os.path.join(run_checkpoint_dir, "model_latest.pt")
        if os.path.exists(run_ckpt_path):
            mlflow.log_artifact(run_ckpt_path, artifact_path="model")
            print(f"[server] Logged State Dict model artifact")
            
            # Copy to master directory
            master_ckpt_path = os.path.join(args.checkpoint_dir, "model_latest.pt")
            shutil.copy(run_ckpt_path, master_ckpt_path)
            os.chmod(master_ckpt_path, 0o600)

        run_ts_path = os.path.join(run_checkpoint_dir, "model_latest_scripted.pt")
        if os.path.exists(run_ts_path):
            mlflow.log_artifact(run_ts_path, artifact_path="model")
            print(f"[server] Logged TorchScript model artifact")
            
            # Copy to master directory
            master_ts_path = os.path.join(args.checkpoint_dir, "model_latest_scripted.pt")
            shutil.copy(run_ts_path, master_ts_path)
            os.chmod(master_ts_path, 0o600)

        # Write training summary JSON including run and experiment details
        summary = {
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "loss": strategy.best_loss if strategy.best_loss != float("inf") else strategy.latest_loss,
            "accuracy": strategy.best_accuracy if strategy.best_round > 0 else strategy.latest_accuracy,
            "best_loss": strategy.best_loss if strategy.best_loss != float("inf") else strategy.latest_loss,
            "best_round": strategy.best_round,
            "class_accuracies": {
                int(k.split("_")[-1]): float(v)
                for k, v in strategy.best_metrics.items()
                if k.startswith("accuracy_class_")
            } if strategy.best_round > 0 else {
                int(k.split("_")[-1]): float(v)
                for k, v in strategy.latest_metrics.items()
                if k.startswith("accuracy_class_")
            }
        }
        summary_path = "/tmp/flower-server-metrics.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"[server] Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
