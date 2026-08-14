import sys
import os
import shutil
from unittest.mock import MagicMock

# 1. Mock flwr library to run on systems without it installed
mock_fl = MagicMock()
class MockFedAvg:
    def __init__(self, *args, **kwargs):
        self.checkpoint_dir = kwargs.get("checkpoint_dir", ".")
    def aggregate_evaluate(self, server_round, results, failures):
        return None

mock_fl.server.strategy.FedAvg = MockFedAvg
sys.modules['flwr'] = mock_fl
sys.modules['flwr.server'] = mock_fl.server
sys.modules['flwr.server.strategy'] = mock_fl.server.strategy

workspace_root = r"e:\Projects\fl-cl"
sys.path.append(os.path.join(workspace_root, "src"))
sys.path.append(os.path.join(workspace_root, "src/defender"))
sys.path.append(os.path.join(workspace_root, "src/aggregator"))

import numpy as np
import torch
import mlflow

from server import MLflowFedAvg, weighted_avg
from model import CyberDefenseNet

def test_confusion_matrix():
    print("[*] Running local verification for Task 1: Confusion Matrix Tracking")
    
    # Setup paths
    test_checkpoint_dir = os.path.join(workspace_root, "checkpoints", "test_run")
    os.makedirs(test_checkpoint_dir, exist_ok=True)

    # Mock client evaluation metrics
    client_1_metrics = {
        "accuracy": 0.8,
        "client_id": "client_1",
        "f1_class_0": 0.9,
        "f1_class_1": 0.8,
        "f1_class_2": 0.7,
        "f1_class_3": 0.8,
        "f1_class_4": 0.8,
    }
    for t in range(5):
        for p in range(5):
            client_1_metrics[f"cm_{t}_{p}"] = float(2.0 if t == p else 0.0)

    client_2_metrics = {
        "accuracy": 0.7,
        "client_id": "client_2",
        "f1_class_0": 0.8,
        "f1_class_1": 0.7,
        "f1_class_2": 0.6,
        "f1_class_3": 0.7,
        "f1_class_4": 0.7,
    }
    for t in range(5):
        for p in range(5):
            client_2_metrics[f"cm_{t}_{p}"] = float(4.0 if t == p else 0.0)

    results = [
        (10, client_1_metrics),
        (20, client_2_metrics)
    ]

    # Test aggregation logic
    aggregated = weighted_avg(results)
    print("[*] Aggregated metrics:")
    for key in sorted(aggregated.keys()):
        if "cm_" in key:
            print(f"  {key}: {aggregated[key]}")

    for i in range(5):
        assert aggregated[f"cm_{i}_{i}"] == 6.0, f"Expected cm_{i}_{i} to be 6.0 but got {aggregated[f'cm_{i}_{i}']}"
    print("[PASS] Aggregation logic correctly sums client confusion matrix counts.")

    # Setup mock MLflow run to test aggregate_evaluate figure generation
    mlflow.set_tracking_uri("file:///e:/Projects/fl-cl/mlruns")
    mlflow.set_experiment("verification_experiment")
    
    with mlflow.start_run() as run:
        # Instantiate strategy
        strategy = MLflowFedAvg(
            fraction_fit=1.0,
            min_fit_clients=2,
            min_available_clients=2,
            checkpoint_dir=test_checkpoint_dir
        )
        
        # Mock class fields
        strategy.fit_clients = 2
        
        # Prepare evaluation parameters
        loss = 0.5
        server_round = 1
        
        # Mock strategy base call
        MockFedAvg.aggregate_evaluate = lambda self, rnd, res, fail: (loss, aggregated)
        
        try:
            strategy.aggregate_evaluate(server_round, [], [])
            
            # Check if confusion matrix figure was generated
            cm_fig_path = os.path.join(test_checkpoint_dir, "plots", f"confusion_round_{server_round}.png")
            print(f"[*] Checking for file: {cm_fig_path}")
            if os.path.exists(cm_fig_path):
                print(f"[PASS] Heatmap successfully generated at: {cm_fig_path}")
            else:
                raise FileNotFoundError(f"Confusion matrix heatmap was not found at {cm_fig_path}")
                
        finally:
            pass

    # Cleanup test output dir
    if os.path.exists(test_checkpoint_dir):
        shutil.rmtree(test_checkpoint_dir)
        print("[*] Cleaned up temporary test directory.")

if __name__ == "__main__":
    test_confusion_matrix()
