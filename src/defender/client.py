"""
client.py — Flower FL Client with Avalanche CL Integration

Bridges the local Continual Learning training loop (Avalanche EWC) to the
global Federated Learning aggregation (Flower FedAvg).

Per federated round:
  1. Receives global model weights from the aggregator (LXC 300)
  2. Trains locally on flows from /mnt/ramdisk/flows/ using EWC
  3. Returns updated weights to the aggregator via gRPC
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

class MyTensorDataset(TensorDataset):
    """Custom TensorDataset that exposes a targets field for Avalanche 0.6.0+ compatibility."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.targets = y

# Robust Avalanche Imports
make_tensor_classification_dataset = None
benchmark_from_datasets = None
tensor_benchmark = None
as_classification_dataset = None

try:
    from avalanche.benchmarks.utils import make_tensor_classification_dataset
except ImportError:
    pass

try:
    from avalanche.benchmarks.utils import as_classification_dataset
except ImportError:
    pass

try:
    from avalanche.benchmarks.scenarios.dataset_scenario import benchmark_from_datasets
except ImportError:
    try:
        from avalanche.benchmarks.generators import benchmark_from_datasets
    except ImportError:
        pass

try:
    from avalanche.benchmarks.generators import tensor_benchmark
except ImportError:
    pass


def assign_label(row):
    """
    Dynamically assign threat labels to flows based on source/destination IP and port fields:
        0: Normal (benign traffic)
        1: Botnet (C2 traffic on 8080/8888/9000)
        2: Exfiltration (DNS exfiltration on port 53)
        3: BruteForce (SSH brute force on port 22)
        4: DoS (volumetric floods / Slowloris on 80/443)
    """
    src_ip = str(row.get("src_ip", ""))
    dst_ip = str(row.get("dst_ip", ""))
    
    try:
        src_port = int(float(row.get("src_port", 0)))
    except (ValueError, TypeError):
        src_port = 0
        
    try:
        dst_port = int(float(row.get("dst_port", 0)))
    except (ValueError, TypeError):
        dst_port = 0

    traffic_gen_ip = "10.10.140.10"
    is_from_traffic_gen = (src_ip == traffic_gen_ip)
    is_to_traffic_gen = (dst_ip == traffic_gen_ip)

    if is_from_traffic_gen or is_to_traffic_gen:
        if dst_port == 22 or src_port == 22:
            return 3  # BruteForce
        elif dst_port in [80, 443] or src_port in [80, 443]:
            return 4  # DoS
        elif dst_port in [8080, 8888, 9000] or src_port in [8080, 8888, 9000]:
            return 1  # Botnet
        elif dst_port == 53 or src_port == 53:
            return 2  # Exfiltration
        else:
            return 4  # Default attack: DoS
    return 0  # Normal


def load_ramdisk_flows(flows_dir: str = "/mnt/ramdisk/flows"):
    """
    Load all CSV flow files from the RAM disk and convert to PyTorch tensors.
    """
    csv_files = sorted(Path(flows_dir).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No flow CSVs found in {flows_dir}")

    dfs = []
    for f in csv_files:
        try:
            df_item = pd.read_csv(f)
            if not df_item.empty:
                dfs.append(df_item)
        except Exception:
            pass  # Ignore empty or locked files

    if not dfs:
        raise FileNotFoundError(f"No valid flow records found in {flows_dir}")

    df = pd.concat(dfs, ignore_index=True)
    if df.empty:
        raise FileNotFoundError(f"Combined flow dataframe is empty in {flows_dir}")

    # Select feature columns: flow statistics + dst_port (critical for class separation)
    feature_cols = [
        "bidirectional_packets", "bidirectional_bytes", "duration_ms",
        "src2dst_packets", "src2dst_bytes", "dst2src_packets", "dst2src_bytes",
        "src2dst_mean_piat_ms", "dst2src_mean_piat_ms",
        "dst_port",
    ]
    available_cols = [c for c in feature_cols if c in df.columns]

    X = df[available_cols].fillna(0).values.astype(np.float32)
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # Pad or truncate to match model input_dim (32)
    if X.shape[1] < 32:
        padding = np.zeros((X.shape[0], 32 - X.shape[1]), dtype=np.float32)
        X = np.hstack([X, padding])
    elif X.shape[1] > 32:
        X = X[:, :32]

    # Assign labels dynamically based on IP and port fields
    df["label"] = df.apply(assign_label, axis=1)
    y = df["label"].values.astype(np.int64)

    return torch.tensor(X), torch.tensor(y)


def get_experience(x_tensor, y_tensor):
    """Wraps PyTorch tensors into an Avalanche experience object."""
    if tensor_benchmark is not None:
        bm = tensor_benchmark(
            train_tensors=[(x_tensor, y_tensor)],
            test_tensors=[(x_tensor, y_tensor)]
        )
        return bm.train_stream[0]

    # For Avalanche 0.6.0+
    if as_classification_dataset is not None and benchmark_from_datasets is not None:
        td = MyTensorDataset(x_tensor, y_tensor)
        ds = as_classification_dataset(td)
        bm = benchmark_from_datasets(
            train=[ds],
            test=[ds]
        )
        return bm.train_stream[0]

    if make_tensor_classification_dataset is not None and benchmark_from_datasets is not None:
        av_dataset = make_tensor_classification_dataset(
            dataset_tensors=(x_tensor, y_tensor)
        )
        bm = benchmark_from_datasets(
            train=[av_dataset],
            test=[av_dataset]
        )
        return bm.train_stream[0]

    raise ImportError("No valid Avalanche dataset generators or benchmarks found.")


import mlflow


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

    @mlflow.trace(name="client_fit")
    def fit(self, parameters, config):
        self.set_parameters(parameters)
        num_samples = 0
        try:
            X, y = load_ramdisk_flows(self.flows_dir)
            num_samples = len(X)
            experience = get_experience(X, y)
            self.cl.train(experience)
            print(f"[client] Trained on {num_samples} flows")
        except FileNotFoundError as e:
            print(f"[client] WARNING: {e}. Skipping training this round (no flows yet).")
        # Return at least 1 so FedAvg aggregate_inplace never divides by zero
        # when all clients have an empty ramdisk (e.g. extractor not ready yet).
        return self.get_parameters(config={}), max(num_samples, 1), {}

    @mlflow.trace(name="client_evaluate")
    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        try:
            X, y = load_ramdisk_flows(self.flows_dir)
            dataset = TensorDataset(X, y)
            dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

            self.net.eval()
            total_loss = 0.0
            correct = 0
            total = 0
            criterion = torch.nn.CrossEntropyLoss()
            device = next(self.net.parameters()).device

            class_correct = {i: 0 for i in range(5)}
            class_total = {i: 0 for i in range(5)}

            with torch.no_grad():
                for X_batch, y_batch in dataloader:
                    X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                    outputs = self.net(X_batch)
                    loss = criterion(outputs, y_batch)
                    total_loss += loss.item() * X_batch.size(0)
                    _, predicted = torch.max(outputs, 1)
                    correct += (predicted == y_batch).sum().item()
                    total += y_batch.size(0)

                    for label in range(5):
                        label_mask = (y_batch == label)
                        class_total[label] += label_mask.sum().item()
                        class_correct[label] += ((predicted == y_batch) & label_mask).sum().item()

            avg_loss = total_loss / total if total > 0 else 0.0
            accuracy = correct / total if total > 0 else 0.0

            class_accuracies = {}
            for label in range(5):
                if class_total[label] > 0:
                    class_accuracies[f"accuracy_class_{label}"] = class_correct[label] / class_total[label]
                else:
                    class_accuracies[f"accuracy_class_{label}"] = -1.0  # Sentinel for no samples

            metrics = {
                "accuracy": accuracy,
                **class_accuracies
            }
            return avg_loss, total, metrics
        except FileNotFoundError:
            return 0.0, 0, {"accuracy": 0.0}


def main():
    parser = argparse.ArgumentParser(description="FL-CL Defender Client")
    parser.add_argument("--server", default="10.10.130.10:8080", help="Aggregator address")
    parser.add_argument("--client-id", default="A", help="Client identifier (A or B)")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--ewc-lambda", type=float, default=0.4, help="EWC regularization strength")
    parser.add_argument("--class-weights", default="12.0,3.0,3.0,15.0,1.0", help="Comma-separated class weights")
    parser.add_argument("--lr", type=float, default=0.01, help="SGD learning rate")
    parser.add_argument("--momentum", type=float, default=0.9, help="SGD momentum")
    args = parser.parse_args()

    # Set up MLflow
    mlflow.set_tracking_uri("http://10.10.130.10:5000")
    mlflow.set_experiment("FL-CL-CyberDefense")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[client-{args.client_id}] Device: {device}")
    print(f"[client-{args.client_id}] Server: {args.server}")
    print(f"[client-{args.client_id}] Flows:  {args.flows_dir}")
    print(f"[client-{args.client_id}] SGD lr: {args.lr} | momentum: {args.momentum}")

    net = CyberDefenseNet().to(device)
    
    weights = [float(w) for w in args.class_weights.split(",")]
    cl = get_continual_learner(
        net, 
        device, 
        ewc_lambda=args.ewc_lambda, 
        class_weights=weights,
        lr=args.lr,
        momentum=args.momentum
    )

    fl.client.start_numpy_client(
        server_address=args.server,
        client=CyberDefenseClient(net, cl, args.flows_dir),
    )


if __name__ == "__main__":
    main()
