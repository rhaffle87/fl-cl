"""
cl_strategy.py — Elastic Weight Consolidation (EWC) Continual Learning Strategy

Wraps the CyberDefenseNet model with Avalanche's EWC strategy to prevent
catastrophic forgetting when training on sequential attack tasks.

The ewc_lambda parameter (default: 0.4) balances:
  - Plasticity: ability to learn new attack patterns
  - Stability: retention of previously learned attack signatures

Deploy on: Defender VMs (VM 100, VM 200)
"""

from torch.optim import SGD
from torch.nn import CrossEntropyLoss
from avalanche.training.supervised import EWC


def get_continual_learner(model, device, ewc_lambda: float = 0.4):
    """
    Create an EWC-equipped continual learner.

    Args:
        model:      CyberDefenseNet instance
        device:     torch.device (cpu or cuda)
        ewc_lambda: Regularization strength. Higher = more stability (less forgetting),
                    lower = more plasticity (faster adaptation). Tune via MLflow.

    Returns:
        Avalanche EWC strategy object with train() and eval() methods.
    """
    return EWC(
        model=model,
        optimizer=SGD(model.parameters(), lr=0.01, momentum=0.9),
        criterion=CrossEntropyLoss(),
        ewc_lambda=ewc_lambda,
        train_mb_size=32,
        train_epochs=1,
        eval_mb_size=32,
        device=device,
    )
