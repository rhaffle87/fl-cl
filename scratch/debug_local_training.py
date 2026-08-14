import sys
import os
import torch
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from collections import OrderedDict

# Add current directory to path
sys.path.insert(0, os.path.expanduser("~"))

from model import CyberDefenseNet
from cl_strategy import get_continual_learner
from client import load_ramdisk_flows, get_experience

def debug():
    print("=== Diagnostic Start (with model_latest.pt) ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # 1. Load Flows
    try:
        X, y = load_ramdisk_flows("/mnt/ramdisk/flows")
        print(f"Loaded X shape: {X.shape}, y shape: {y.shape}")
        print(f"X has NaNs: {torch.isnan(X).any().item()}")
        print(f"y has NaNs: {torch.isnan(y.float()).any().item()}")
        print(f"X has Infs: {torch.isinf(X).any().item()}")
        print(f"y unique values: {torch.unique(y).tolist()}")
    except Exception as e:
        print(f"Failed to load ramdisk flows: {e}")
        return

    # 2. Check model initialization
    net = CyberDefenseNet().to(device)
    ckpt_path = "/tmp/model_latest.pt"
    if os.path.exists(ckpt_path):
        print(f"Loading weights from {ckpt_path}")
        net.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True))
    else:
        print(f"WARNING: Checkpoint {ckpt_path} not found!")

    # 3. Test basic forward and backward pass (No EWC)
    print("\n--- Testing standard training step (No EWC) ---")
    weights = [100.0, 150.0, 3.0, 80.0, 1.0]
    weights_tensor = torch.tensor(weights, dtype=torch.float32).to(device)
    weights_tensor = (weights_tensor / weights_tensor.sum()) * len(weights)
    criterion = torch.nn.CrossEntropyLoss(weight=weights_tensor)
    optimizer = torch.optim.SGD(net.parameters(), lr=0.005, momentum=0.9)

    X_batch = X[:32].to(device)
    y_batch = y[:32].to(device)

    print(f"Batch X shape: {X_batch.shape}, Batch y shape: {y_batch.shape}")

    outputs = net(X_batch)
    print(f"Outputs has NaNs: {torch.isnan(outputs).any().item()}")
    
    loss = criterion(outputs, y_batch)
    print(f"Loss value: {loss.item()}")
    
    optimizer.zero_grad()
    loss.backward()
    
    nan_grads = False
    for name, param in net.named_parameters():
        if param.grad is not None:
            has_nan = torch.isnan(param.grad).any().item()
            if has_nan:
                nan_grads = True
            print(f"  Grad {name} has NaNs: {has_nan}")
        else:
            print(f"  Grad {name} is None")

    if torch.isnan(loss) or nan_grads:
        print("WARNING: Standard SGD step produced NaN loss or gradients!")
    else:
        print("Standard SGD step completed successfully.")

    # 4. Test EWC strategy training
    print("\n--- Testing EWC Strategy training step ---")
    try:
        cl = get_continual_learner(
            net,
            device,
            ewc_lambda=1.0,
            class_weights=weights,
            lr=0.005,
            momentum=0.9
        )
        experience = get_experience(X, y)
        print("Running cl.train(experience)...")
        cl.train(experience)
        print("cl.train completed.")
        
        # Check model weights after EWC training
        nan_weights = False
        for name, param in net.named_parameters():
            has_nan = torch.isnan(param).any().item()
            if has_nan:
                nan_weights = True
            print(f"  Weight {name} has NaNs: {has_nan}")
        if nan_weights:
            print("WARNING: EWC training produced NaN weights!")
        else:
            print("EWC training completed successfully without NaNs.")
    except Exception as e:
        print(f"EWC training failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()
