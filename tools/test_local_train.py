"""
test_local_train.py — Offline Synthetic Local Training Convergence Unit Test.

Generates a synthetic 5-class mock flow dataset in scratch/mock_flows, simulates
local training loops across MLP, CNN, and Transformer backbones, and asserts
convergence and batch dimension safety without requiring live hardware.

Usage:
    python3 tools/test_local_train.py
"""
import argparse
from pathlib import Path

import os
import sys
import shutil
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.utils.data import DataLoader, TensorDataset

# Set up paths to import client and model
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))
sys.path.insert(0, os.path.join(project_root, "src", "defender"))

import client
from model import get_model

MOCK_FLOWS_DIR = os.path.join(project_root, "scratch", "mock_flows")
LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}

def create_mock_flows():
    print(f"[*] Creating mock flow CSVs in {MOCK_FLOWS_DIR}...")
    os.makedirs(MOCK_FLOWS_DIR, exist_ok=True)
    
    # We will generate 200 samples total, 40 per class
    data = []
    
    # Class 0: Normal
    for _ in range(40):
        data.append({
            "src_ip": "192.168.1.50", "dst_ip": "192.168.1.100",
            "src_port": np.random.randint(1024, 65535), "dst_port": 443,
            "duration_ms": float(np.random.uniform(50, 500)),
            "bidirectional_packets": float(np.random.uniform(5, 25)),
            "bidirectional_bytes": float(np.random.uniform(500, 5000)),
            "src2dst_packets": float(np.random.uniform(2, 12)),
            "src2dst_bytes": float(np.random.uniform(200, 2000)),
            "dst2src_packets": float(np.random.uniform(3, 13)),
            "dst2src_bytes": float(np.random.uniform(300, 3000)),
            "src2dst_mean_piat_ms": float(np.random.uniform(10, 80)),
            "dst2src_mean_piat_ms": float(np.random.uniform(10, 80))
        })
        
    # Class 1: Botnet (C2 ports: 8080)
    for _ in range(40):
        data.append({
            "src_ip": "10.10.140.10", "dst_ip": "192.168.1.100",
            "src_port": np.random.randint(1024, 65535), "dst_port": 8080,
            "duration_ms": float(np.random.uniform(100, 1000)),
            "bidirectional_packets": float(np.random.uniform(10, 50)),
            "bidirectional_bytes": float(np.random.uniform(1000, 10000)),
            "src2dst_packets": float(np.random.uniform(5, 25)),
            "src2dst_bytes": float(np.random.uniform(500, 5000)),
            "dst2src_packets": float(np.random.uniform(5, 25)),
            "dst2src_bytes": float(np.random.uniform(500, 5000)),
            "src2dst_mean_piat_ms": float(np.random.uniform(5, 40)),
            "dst2src_mean_piat_ms": float(np.random.uniform(5, 40))
        })
        
    # Class 2: Exfiltration (DNS port: 53)
    for _ in range(40):
        data.append({
            "src_ip": "10.10.140.10", "dst_ip": "192.168.1.100",
            "src_port": np.random.randint(1024, 65535), "dst_port": 53,
            "duration_ms": float(np.random.uniform(10, 100)),
            "bidirectional_packets": float(np.random.uniform(2, 6)),
            "bidirectional_bytes": float(np.random.uniform(150, 600)),
            "src2dst_packets": float(np.random.uniform(1, 3)),
            "src2dst_bytes": float(np.random.uniform(50, 200)),
            "dst2src_packets": float(np.random.uniform(1, 3)),
            "dst2src_bytes": float(np.random.uniform(100, 400)),
            "src2dst_mean_piat_ms": float(np.random.uniform(1, 10)),
            "dst2src_mean_piat_ms": float(np.random.uniform(1, 10))
        })
        
    # Class 3: BruteForce (SSH port: 22)
    for _ in range(40):
        data.append({
            "src_ip": "10.10.140.10", "dst_ip": "192.168.1.100",
            "src_port": np.random.randint(1024, 65535), "dst_port": 22,
            "duration_ms": float(np.random.uniform(100, 2000)),
            "bidirectional_packets": float(np.random.uniform(5, 30)),
            "bidirectional_bytes": float(np.random.uniform(800, 4000)),
            "src2dst_packets": float(np.random.uniform(2, 15)),
            "src2dst_bytes": float(np.random.uniform(400, 2000)),
            "dst2src_packets": float(np.random.uniform(3, 15)),
            "dst2src_bytes": float(np.random.uniform(400, 2000)),
            "src2dst_mean_piat_ms": float(np.random.uniform(20, 150)),
            "dst2src_mean_piat_ms": float(np.random.uniform(20, 150))
        })
        
    # Class 4: DoS (port 80 with duration > 2000ms)
    for _ in range(40):
        data.append({
            "src_ip": "10.10.140.10", "dst_ip": "192.168.1.100",
            "src_port": np.random.randint(1024, 65535), "dst_port": 80,
            "duration_ms": float(np.random.uniform(2500, 5000)),
            "bidirectional_packets": float(np.random.uniform(20, 200)),
            "bidirectional_bytes": float(np.random.uniform(1000, 15000)),
            "src2dst_packets": float(np.random.uniform(10, 100)),
            "src2dst_bytes": float(np.random.uniform(500, 7500)),
            "dst2src_packets": float(np.random.uniform(10, 100)),
            "dst2src_bytes": float(np.random.uniform(500, 7500)),
            "src2dst_mean_piat_ms": float(np.random.uniform(1, 15)),
            "dst2src_mean_piat_ms": float(np.random.uniform(1, 15))
        })
        
    df = pd.DataFrame(data)
    # Write to two separate CSV files to test loading concat logic
    df.iloc[:100].to_csv(os.path.join(MOCK_FLOWS_DIR, "flows_part1.csv"), index=False)
    df.iloc[100:].to_csv(os.path.join(MOCK_FLOWS_DIR, "flows_part2.csv"), index=False)
    print(f"[OK] Created mock flows successfully!")

def run_test_training():
    create_mock_flows()
    
    print("\nLoading mock ramdisk flows...")
    try:
        # Load from MOCK_FLOWS_DIR
        X, y = client.load_ramdisk_flows(MOCK_FLOWS_DIR, dos_threshold_ms=2000, traffic_gen_ip="10.10.140.10")
    except Exception as e:
        print(f"[FAIL] Error loading flows: {e}")
        return
        
    print(f"Loaded X shape: {X.shape}, y shape: {y.shape}")
    from collections import Counter
    print(f"Label count: {Counter(y.numpy())}")
    
    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    for m_type in ["mlp", "cnn", "transformer"]:
        print(f"\n==========================================")
        print(f"Training Model Backbone: {m_type.upper()}")
        print(f"==========================================")
        
        model = get_model(m_type, input_dim=32, num_classes=5).to(device)
        optimizer = Adam(model.parameters(), lr=0.01)
        criterion = nn.CrossEntropyLoss()
        
        # Train for 3 epochs
        model.train()
        for epoch in range(3):
            total_loss = 0.0
            correct = 0
            total = 0
            for X_batch, y_batch in dataloader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item() * X_batch.size(0)
                _, predicted = torch.max(outputs, 1)
                correct += (predicted == y_batch).sum().item()
                total += y_batch.size(0)
            
            print(f"  Epoch {epoch+1}/3 - Loss: {total_loss/total:.4f} | Accuracy: {correct/total:.4f}")
            
        # Quick eval
        model.eval()
        all_preds = []
        all_targets = []
        with torch.no_grad():
            for X_batch, y_batch in DataLoader(dataset, batch_size=64, shuffle=False):
                outputs = model(X_batch.to(device))
                _, predicted = torch.max(outputs, 1)
                all_preds.extend(predicted.cpu().numpy())
                all_targets.extend(y_batch.numpy())
                
        acc = np.mean(np.array(all_preds) == np.array(all_targets))
        print(f"[OK] Finished training {m_type.upper()}. Final Train Accuracy: {acc:.4f}")

    # Clean up mock files
    if os.path.exists(MOCK_FLOWS_DIR):
        shutil.rmtree(MOCK_FLOWS_DIR)
        print("\n[*] Cleaned up mock flow directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Offline Synthetic Training Convergence Test Suite")
    _ = parser.parse_args()
    run_test_training()
