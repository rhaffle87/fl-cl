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
        Input (input_dim) → FC(hidden_dim1) → ReLU → Dropout(dropout) → FC(hidden_dim2) → ReLU → FC(num_classes)
    """

    def __init__(
        self,
        input_dim: int = 32,
        num_classes: int = 5,
        hidden_dim1: int = 64,
        hidden_dim2: int = 32,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, hidden_dim1),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.ReLU(),
            nn.Linear(hidden_dim2, num_classes),
        )

    def forward(self, x):
        return self.fc(x)


class CyberDefenseCNN(nn.Module):
    """
    1D-CNN for sequential/temporal feature classification of flow statistics.
    Reshapes input (input_dim) to (batch, 1, input_dim).
    """

    def __init__(
        self,
        input_dim: int = 32,
        num_classes: int = 5,
        conv_channels1: int = 16,
        conv_channels2: int = 32,
        kernel_size: int = 3,
        fc_dim: int = 64,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(
                1,
                conv_channels1,
                kernel_size=kernel_size,
                stride=1,
                padding=kernel_size // 2,
            ),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(
                conv_channels1,
                conv_channels2,
                kernel_size=kernel_size,
                stride=1,
                padding=kernel_size // 2,
            ),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )

        # Dynamically compute fc input dimension
        with torch.no_grad():
            dummy_out = self.conv(torch.zeros(1, 1, input_dim))
            self.fc_input_dim = dummy_out.numel()

        self.fc = nn.Sequential(
            nn.Linear(self.fc_input_dim, fc_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(self, x):
        # x shape: (batch, input_dim)
        x = x.unsqueeze(1)  # shape: (batch, 1, input_dim)
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)


class CyberDefenseTransformer(nn.Module):
    """
    Transformer-based classifier for flow features.
    Treats the input_dim dimensions as token_len tokens of dimension token_dim.
    """

    def __init__(
        self,
        input_dim: int = 32,
        num_classes: int = 5,
        token_len: int = 8,
        token_dim: int = 4,
        d_model: int = 32,
        nhead: int = 4,
        dim_feedforward: int = 64,
        num_layers: int = 2,
        fc_dim: int = 32,
        dropout: float = 0.1,
    ):
        super().__init__()
        assert (
            token_len * token_dim == input_dim
        ), f"token_len ({token_len}) * token_dim ({token_dim}) must equal input_dim ({input_dim})"
        self.token_len = token_len
        self.token_dim = token_dim
        self.d_model = d_model

        # Project each token_dim token to d_model space
        self.input_projection = nn.Linear(self.token_dim, self.d_model)
        self.pos_encoder = nn.Parameter(torch.randn(1, self.token_len, self.d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Sequential(
            nn.Linear(self.d_model, fc_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(self, x):
        # x shape: (batch, input_dim)
        batch_size = x.size(0)
        # Reshape to (batch, token_len, token_dim)
        x = x.view(batch_size, self.token_len, self.token_dim)
        # Project to d_model
        x = self.input_projection(x)  # (batch, token_len, d_model)
        # Add positional encoding
        x = x + self.pos_encoder
        # Run transformer
        x = self.transformer(x)  # (batch, token_len, d_model)
        # Global average pooling over sequence dimension
        x = x.mean(dim=1)  # (batch, d_model)
        return self.fc(x)


def get_model(
    model_type: str = "mlp", input_dim: int = 32, num_classes: int = 5, **kwargs
):
    """
    Model factory for creating threat classifiers.
    """
    m_type = model_type.lower()
    if m_type == "mlp":
        return CyberDefenseNet(
            input_dim=input_dim, num_classes=num_classes, **kwargs
        )
    elif m_type == "cnn":
        return CyberDefenseCNN(
            input_dim=input_dim, num_classes=num_classes, **kwargs
        )
    elif m_type == "transformer":
        return CyberDefenseTransformer(
            input_dim=input_dim, num_classes=num_classes, **kwargs
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")


