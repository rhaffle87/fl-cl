"""
server.py — Flower Federated Averaging Aggregator Server

Orchestrates global model training by collecting and averaging weight updates
from all defender client nodes via gRPC.

Deploy on: FL Aggregator (LXC 300)
Usage:
    python3 server.py --rounds 10 --min-clients 2
"""

import argparse

import flwr as fl


def weighted_avg(metrics):
    """Aggregate accuracy metrics weighted by dataset size."""
    accs = [n * m["accuracy"] for n, m in metrics]
    total = [n for n, _ in metrics]
    if sum(total) == 0:
        return {"accuracy": 0.0}
    return {"accuracy": sum(accs) / sum(total)}


def main():
    parser = argparse.ArgumentParser(description="FL-CL Aggregator Server")
    parser.add_argument("--address", default="0.0.0.0:8080", help="Server bind address")
    parser.add_argument("--rounds", type=int, default=10, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, default=2, help="Minimum clients per round")
    args = parser.parse_args()

    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=args.min_clients,
        min_evaluate_clients=args.min_clients,
        min_available_clients=args.min_clients,
        evaluate_metrics_aggregation_fn=weighted_avg,
    )

    print(f"[server] Starting Flower aggregator on {args.address}")
    print(f"[server] Rounds: {args.rounds} | Min clients: {args.min_clients}")

    fl.server.start_server(
        server_address=args.address,
        config=fl.server.ServerConfig(num_rounds=args.rounds),
        strategy=strategy,
    )


if __name__ == "__main__":
    main()
