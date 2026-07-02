"""
model.py — CyberDefenseNet: Multi-Layer Perceptron for Encrypted Traffic Classification

Maps 32 scaled ETA features (JA3 fingerprints, SPLT statistics, flow entropy)
to 5 threat classes: Normal, Botnet, Exfiltration, BruteForce, DoS.

Deploy on: Defender VMs (VM 310, VM 320)
Input:     Feature vectors from extractor.py → /mnt/ramdisk/flows/
Output:    Class predictions for network flow classification
"""

import torch
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


class CyberDefenseCNN(nn.Module):
    """
    1D-CNN for sequential/temporal feature classification of flow statistics.
    Reshapes input (32) to (batch, 1, 32).
    """

    def __init__(self, input_dim: int = 32, num_classes: int = 5):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),  # size: 16
            nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),  # size: 8
        )
        self.fc = nn.Sequential(
            nn.Linear(32 * 8, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        # x shape: (batch, 32)
        x = x.unsqueeze(1)  # shape: (batch, 1, 32)
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)


class CyberDefenseTransformer(nn.Module):
    """
    Transformer-based classifier for flow features.
    Treats the 32 input dimensions as 8 tokens of dimension 4.
    """

    def __init__(self, input_dim: int = 32, num_classes: int = 5):
        super().__init__()
        self.token_len = 8
        self.token_dim = 4
        self.d_model = 32

        # Project each 4-dim token to d_model space
        self.input_projection = nn.Linear(self.token_dim, self.d_model)
        self.pos_encoder = nn.Parameter(torch.randn(1, self.token_len, self.d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.d_model,
            nhead=4,
            dim_feedforward=64,
            dropout=0.1,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = nn.Sequential(
            nn.Linear(self.d_model, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, num_classes),
        )

    def forward(self, x):
        # x shape: (batch, 32)
        batch_size = x.size(0)
        # Reshape to (batch, 8, 4)
        x = x.view(batch_size, self.token_len, self.token_dim)
        # Project to d_model
        x = self.input_projection(x)  # (batch, 8, d_model)
        # Add positional encoding
        x = x + self.pos_encoder
        # Run transformer
        x = self.transformer(x)  # (batch, 8, d_model)
        # Global average pooling over sequence dimension
        x = x.mean(dim=1)  # (batch, d_model)
        return self.fc(x)


def get_model(model_type: str = "mlp", input_dim: int = 32, num_classes: int = 5):
    """
    Model factory for creating threat classifiers.
    """
    m_type = model_type.lower()
    if m_type == "mlp":
        return CyberDefenseNet(input_dim, num_classes)
    elif m_type == "cnn":
        return CyberDefenseCNN(input_dim, num_classes)
    elif m_type == "transformer":
        return CyberDefenseTransformer(input_dim, num_classes)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

