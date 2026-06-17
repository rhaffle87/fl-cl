"""
model.py — CyberDefenseNet: Multi-Layer Perceptron for Encrypted Traffic Classification

Maps 32 scaled ETA features (JA3 fingerprints, SPLT statistics, flow entropy)
to 5 threat classes: Normal, Botnet, Exfiltration, BruteForce, DoS.

Deploy on: Defender VMs (VM 100, VM 200)
Input:     Feature vectors from extractor.py → /mnt/ramdisk/flows/
Output:    Class predictions for network flow classification
"""

import torch.nn as nn


class CyberDefenseNet(nn.Module):
    """
    3-layer MLP with dropout regularization.

    Architecture:
        Input (32) → FC(64) → ReLU → Dropout(0.2) → FC(32) → ReLU → FC(5)

    The input dimension (32) corresponds to the scaled feature vector produced
    by extractor.py. The 5 output classes map to:
        0: Normal (benign HTTPS/SSH traffic)
        1: Botnet (C2 beaconing patterns)
        2: Exfiltration (DNS-over-HTTPS tunneling, data theft)
        3: BruteForce (SSH/RDP credential stuffing)
        4: DoS (volumetric floods, Slowloris)
    """

    def __init__(self, input_dim: int = 32, num_classes: int = 5):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_classes),
        )

    def forward(self, x):
        return self.fc(x)
