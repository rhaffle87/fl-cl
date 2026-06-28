"""
cl_strategy.py — Elastic Weight Consolidation (EWC) Continual Learning Strategy

Wraps the CyberDefenseNet model with Avalanche's EWC strategy to prevent
catastrophic forgetting when training on sequential attack tasks.

The ewc_lambda parameter (default: 0.4) balances:
  - Plasticity: ability to learn new attack patterns
  - Stability: retention of previously learned attack signatures

Deploy on: Defender VMs (VM 310, VM 320)
"""

import torch
from torch.optim import SGD
from torch.nn import CrossEntropyLoss
from avalanche.training.supervised import EWC


def get_continual_learner(model, device, ewc_lambda: float = 0.4, class_weights=None, lr: float = 0.01, momentum: float = 0.9):
    """
    Create an EWC-equipped continual learner.

    Args:
        model:         CyberDefenseNet instance
        device:        torch.device (cpu or cuda)
        ewc_lambda:    Regularization strength. Higher = more stability (less forgetting),
                       lower = more plasticity (faster adaptation). Tune via MLflow.
        class_weights: List of 5 floats for class weights.
        lr:            Learning rate for the local SGD optimizer.
        momentum:      Momentum for the local SGD optimizer.

    Returns:
        Avalanche EWC strategy object with train() and eval() methods.
    """
    if class_weights is None:
        class_weights = [12.0, 3.0, 3.0, 15.0, 1.0]
    
    weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)

    return EWC(
        model=model,
        optimizer=SGD(model.parameters(), lr=lr, momentum=momentum),
        criterion=CrossEntropyLoss(weight=weights_tensor),
        ewc_lambda=ewc_lambda,
        train_mb_size=32,
        train_epochs=1,
        eval_mb_size=32,
        device=device,
    )

