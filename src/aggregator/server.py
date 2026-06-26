"""
server.py — Flower Federated Averaging Aggregator Server

Orchestrates global model training by collecting and averaging weight updates
from all defender client nodes via gRPC and logging metrics to MLflow.

Deploy on: FL Aggregator (LXC 300)
Usage:
    python3 server.py --rounds 10 --min-clients 2 --mlflow-uri http://localhost:5000
"""

import argparse
import flwr as fl
import mlflow


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
    """Custom FedAvg strategy that logs metrics to MLflow after each evaluation round."""

    def aggregate_evaluate(self, server_round, results, failures):
        aggregated_result = super().aggregate_evaluate(server_round, results, failures)
        if aggregated_result:
            loss, metrics = aggregated_result
            print(f"[server] Round {server_round} Aggregated Loss: {loss:.4f} | Accuracy: {metrics.get('accuracy', 0.0):.4f}")
            mlflow.log_metric("loss", loss, step=server_round)
            for k, v in metrics.items():
                mlflow.log_metric(k, v, step=server_round)
        return aggregated_result


def main():
    parser = argparse.ArgumentParser(description="FL-CL Aggregator Server")
    parser.add_argument("--address", default="0.0.0.0:8080", help="Server bind address")
    parser.add_argument("--rounds", type=int, default=10, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, default=2, help="Minimum clients per round")
    parser.add_argument("--mlflow-uri", default="http://localhost:5000", help="MLflow tracking URI")
    args = parser.parse_args()

    # Set up MLflow
    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment("FL-CL-CyberDefense")

    strategy = MLflowFedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=args.min_clients,
        min_evaluate_clients=args.min_clients,
        min_available_clients=args.min_clients,
        evaluate_metrics_aggregation_fn=weighted_avg,
    )

    print(f"[server] Starting Flower aggregator on {args.address}")
    print(f"[server] Rounds: {args.rounds} | Min clients: {args.min_clients}")
    print(f"[server] MLflow Server: {args.mlflow_uri}")

    with mlflow.start_run(run_name="FL-CL-Orchestrated-Run"):
        fl.server.start_server(
            server_address=args.address,
            config=fl.server.ServerConfig(num_rounds=args.rounds),
            strategy=strategy,
        )


if __name__ == "__main__":
    main()
