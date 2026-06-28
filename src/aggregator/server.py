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
from collections import OrderedDict
from pathlib import Path

import flwr as fl
import mlflow
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
        self.latest_loss = 0.0
        self.latest_accuracy = 0.0
        self.latest_metrics = {}
        Path(self.checkpoint_dir).mkdir(parents=True, exist_ok=True)

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

            # Checkpoint best model
            if loss < self.best_loss:
                self.best_loss = loss
                self.best_round = server_round
                mlflow.log_metric("best_loss", loss, step=server_round)
                mlflow.log_metric("best_round", server_round, step=server_round)
                print(f"[server] ★ New best model at round {server_round} (loss={loss:.4f})")

        return aggregated_result

    @mlflow.trace(name="aggregate_fit")
    def aggregate_fit(self, server_round, results, failures):
        aggregated = super().aggregate_fit(server_round, results, failures)

        # Save model checkpoint from aggregated parameters
        if aggregated is not None:
            parameters, config = aggregated
            ndarrays = fl.common.parameters_to_ndarrays(parameters)

            model = CyberDefenseNet()
            state_dict = OrderedDict(
                {k: torch.tensor(v) for k, v in zip(model.state_dict().keys(), ndarrays)}
            )
            model.load_state_dict(state_dict, strict=True)

            # Save PyTorch checkpoint
            ckpt_path = os.path.join(self.checkpoint_dir, f"model_round_{server_round:04d}.pt")
            torch.save(model.state_dict(), ckpt_path)

            # Save latest checkpoint (always overwrite)
            latest_path = os.path.join(self.checkpoint_dir, "model_latest.pt")
            torch.save(model.state_dict(), latest_path)

            # Export TorchScript for deployment validation
            if self.export_torchscript:
                model.eval()
                scripted = torch.jit.script(model)
                ts_path = os.path.join(self.checkpoint_dir, "model_latest_scripted.pt")
                scripted.save(ts_path)

            if server_round % 10 == 0:
                print(f"[server] Checkpoint saved: {ckpt_path}")

        return aggregated


def get_git_hash():
    """Get current git commit hash for run traceability."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="FL-CL Aggregator Server")
    parser.add_argument("--address", default="0.0.0.0:8080", help="Server bind address")
    parser.add_argument("--rounds", type=int, default=10, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, default=2, help="Minimum clients per round")
    parser.add_argument("--mlflow-uri", default="http://localhost:5000", help="MLflow tracking URI")
    parser.add_argument("--checkpoint-dir", default="/opt/mlflow-artifacts/checkpoints",
                        help="Directory to save model checkpoints")
    parser.add_argument("--config-file", default="", help="Experiment config YAML to log as artifact")
    parser.add_argument("--mlops-mode", default="experimental", choices=["experimental", "production"],
                        help="MLOps mode (experimental or production)")
    parser.add_argument("--production-strategy", default="resume", choices=["resume", "fresh"],
                        help="Production warm-start checkpoint strategy")
    args = parser.parse_args()

    # Set up MLflow
    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment("FL-CL-CyberDefense")

    # MLOps Warm-Start Checkpoint Resumption
    initial_parameters = None
    resumed_from_version = None
    resumed_from_run_id = None
    latest_ckpt_path = os.path.join(args.checkpoint_dir, "model_latest.pt")
    
    if args.mlops_mode == "production":
        if args.production_strategy == "resume" and os.path.exists(latest_ckpt_path):
            print(f"[server] Production Warm-Start: Loading weights from {latest_ckpt_path}")
            try:
                model = CyberDefenseNet()
                model.load_state_dict(torch.load(latest_ckpt_path, map_location="cpu"))
                
                ndarrays = [val.cpu().numpy() for _, val in model.state_dict().items()]
                initial_parameters = fl.common.ndarrays_to_parameters(ndarrays)
                
                # Load metadata
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
            print("[server] Production Start: No prior checkpoint found or fresh flag active. Initializing new model weights.")
    else:
        print("[server] Experimental Cold-Start: Training a new model from scratch.")

    print(f"[server] Starting Flower aggregator on {args.address}")
    print(f"[server] Rounds: {args.rounds} | Min clients: {args.min_clients}")
    print(f"[server] MLflow Server: {args.mlflow_uri}")
    print(f"[server] Checkpoints Base Directory: {args.checkpoint_dir}")
    print(f"[server] MLOps Mode: {args.mlops_mode} | Production Strategy: {args.production_strategy}")

    with mlflow.start_run(run_name="FL-CL-Orchestrated-Run") as run:
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

        # Log experiment metadata
        mlflow.set_tag("git_commit", get_git_hash())
        mlflow.log_param("fl_rounds", args.rounds)
        mlflow.log_param("min_clients", args.min_clients)
        
        # Log MLOps params & tags
        mlflow.set_tag("mlops_mode", args.mlops_mode)
        mlflow.set_tag("production_strategy", args.production_strategy if args.mlops_mode == "production" else "N/A")
        mlflow.set_tag("warm_started", "True" if initial_parameters is not None else "False")
        if resumed_from_run_id:
            mlflow.set_tag("resumed_from_run_id", resumed_from_run_id)
        if resumed_from_version:
            mlflow.set_tag("resumed_from_version", str(resumed_from_version))

        # Log config file as artifact if provided
        if args.config_file and os.path.exists(args.config_file):
            mlflow.log_artifact(args.config_file, artifact_path="config")
            print(f"[server] Logged config artifact: {args.config_file}")

        fl.server.start_server(
            server_address=args.address,
            config=fl.server.ServerConfig(num_rounds=args.rounds),
            strategy=strategy,
        )

        # Log final best checkpoint as MLflow artifact using MLflow 3.x LoggedModel entities
        run_best_ckpt = os.path.join(run_checkpoint_dir, "model_latest.pt")
        if os.path.exists(run_best_ckpt):
            import pandas as pd
            import numpy as np

            # Instantiate and load model
            model = CyberDefenseNet()
            model.load_state_dict(torch.load(run_best_ckpt, map_location="cpu"))
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

            # Promote model to master checkpoint directory
            print(f"[server] Copying best checkpoint to master directory: {latest_ckpt_path}")
            shutil.copy(run_best_ckpt, latest_ckpt_path)

            # Manage Model Registry tagging and promotion via MlflowClient
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                model_name = "CyberDefenseNet"
                
                # Set tags on model version object
                client.set_model_version_tag(model_name, str(new_version), "mlops_mode", args.mlops_mode)
                if resumed_from_version:
                    client.set_model_version_tag(model_name, str(new_version), "parent_version", str(resumed_from_version))
                if resumed_from_run_id:
                    client.set_model_version_tag(model_name, str(new_version), "resumed_from_run_id", str(resumed_from_run_id))
                
                # If production mode, transition to Production stage and archive existing production versions
                if args.mlops_mode == "production":
                    print(f"[server] MLOps Promotion: Transitioning version {new_version} to 'Production'...")
                    client.transition_model_version_stage(
                        name=model_name,
                        version=str(new_version),
                        stage="Production",
                        archive_existing_versions=True
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
            print(f"[server] Updated master latest model metadata: {meta_data}")

        run_ts_path = os.path.join(run_checkpoint_dir, "model_latest_scripted.pt")
        if os.path.exists(run_ts_path):
            mlflow.log_artifact(run_ts_path, artifact_path="model")
            print(f"[server] Logged TorchScript model artifact")
            
            # Copy to master directory
            master_ts_path = os.path.join(args.checkpoint_dir, "model_latest_scripted.pt")
            shutil.copy(run_ts_path, master_ts_path)

        # Write training summary JSON
        summary = {
            "run_id": run.info.run_id,
            "loss": strategy.latest_loss,
            "accuracy": strategy.latest_accuracy,
            "best_loss": strategy.best_loss,
            "best_round": strategy.best_round,
            "class_accuracies": {
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
