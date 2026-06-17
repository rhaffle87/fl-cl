"""
client.py — Flower FL Client with Avalanche CL Integration

Bridges the local Continual Learning training loop (Avalanche EWC) to the
global Federated Learning aggregation (Flower FedAvg).

Per federated round:
  1. Receives global model weights from the aggregator (LXC 300)
  2. Trains locally on flows from /mnt/ramdisk/flows/ using EWC
  3. Returns updated weights to the aggregator via gRPC

Deploy on: Defender VMs (VM 100, VM 200)
Usage:
    python3 client.py --server 10.10.10.130:8080 --client-id A
"""

import argparse
from collections import OrderedDict
from pathlib import Path

import flwr as fl
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from cl_strategy import get_continual_learner
from model import CyberDefenseNet


def load_ramdisk_flows(flows_dir: str = "/mnt/ramdisk/flows") -> TensorDataset:
    """
    Load all CSV flow files from the RAM disk and convert to a PyTorch dataset.

    Returns a TensorDataset with scaled features (X) and labels (y).
    Labels should be pre-assigned during traffic generation.
    """
    csv_files = sorted(Path(flows_dir).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No flow CSVs found in {flows_dir}")

    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)

    # Select numeric feature columns (exclude metadata like IPs, ports, SNI)
    feature_cols = [
        "bidirectional_packets", "bidirectional_bytes", "duration_ms",
        "src2dst_packets", "src2dst_bytes", "dst2src_packets", "dst2src_bytes",
        "src2dst_mean_piat_ms", "dst2src_mean_piat_ms",
    ]
    available_cols = [c for c in feature_cols if c in df.columns]

    X = df[available_cols].fillna(0).values.astype(np.float32)
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # Pad or truncate to match model input_dim (32)
    if X.shape[1] < 32:
        padding = np.zeros((X.shape[0], 32 - X.shape[1]), dtype=np.float32)
        X = np.hstack([X, padding])

    # Labels — default to 0 (Normal) if no label column exists
    if "label" in df.columns:
        y = df["label"].values.astype(np.int64)
    else:
        y = np.zeros(X.shape[0], dtype=np.int64)

    return TensorDataset(torch.tensor(X), torch.tensor(y))


class CyberDefenseClient(fl.client.NumPyClient):
    """Flower client wrapping the Avalanche CL training loop."""

    def __init__(self, net, cl_strategy, flows_dir):
        self.net = net
        self.cl = cl_strategy
        self.flows_dir = flows_dir

    def get_parameters(self, config):
        return [v.cpu().numpy() for _, v in self.net.state_dict().items()]

    def set_parameters(self, params):
        state = OrderedDict(
            {k: torch.tensor(v) for k, v in zip(self.net.state_dict().keys(), params)}
        )
        self.net.load_state_dict(state, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        try:
            dataset = load_ramdisk_flows(self.flows_dir)
            self.cl.train(dataset)
            print(f"[client] Trained on {len(dataset)} flows")
        except FileNotFoundError as e:
            print(f"[client] WARNING: {e}. Skipping training this round.")
        return self.get_parameters(config={}), len(dataset) if 'dataset' in dir() else 0, {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        try:
            dataset = load_ramdisk_flows(self.flows_dir)
            results = self.cl.eval(dataset)
            loss = float(results.get("Loss", 0.0))
            accuracy = float(results.get("Top1_Acc", 0.0))
            return loss, len(dataset), {"accuracy": accuracy}
        except FileNotFoundError:
            return 0.0, 0, {"accuracy": 0.0}


def main():
    parser = argparse.ArgumentParser(description="FL-CL Defender Client")
    parser.add_argument("--server", default="10.10.10.130:8080", help="Aggregator address")
    parser.add_argument("--client-id", default="A", help="Client identifier (A or B)")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--ewc-lambda", type=float, default=0.4, help="EWC regularization strength")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[client-{args.client_id}] Device: {device}")
    print(f"[client-{args.client_id}] Server: {args.server}")
    print(f"[client-{args.client_id}] Flows:  {args.flows_dir}")

    net = CyberDefenseNet().to(device)
    cl = get_continual_learner(net, device, ewc_lambda=args.ewc_lambda)

    fl.client.start_numpy_client(
        server_address=args.server,
        client=CyberDefenseClient(net, cl, args.flows_dir),
    )


if __name__ == "__main__":
    main()
