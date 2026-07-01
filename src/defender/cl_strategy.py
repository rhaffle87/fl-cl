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
from avalanche.training.supervised import EWC, Naive, GEM


# Gradient clip norm — prevents NaN loss from Fisher penalty or gradient explosion
_GRAD_CLIP_MAX_NORM = 1.0


def get_continual_learner(
    model,
    device,
    strategy_name: str = "EWC",
    ewc_lambda: float = 0.4,
    patterns_per_exp: int = 256,
    memory_strength: float = 0.5,
    class_weights=None,
    lr: float = 0.01,
    momentum: float = 0.9,
    batch_size: int = 32,
    dp_enabled: bool = False,
    dp_noise_multiplier: float = 0.1,
    dp_max_grad_norm: float = 1.0
):
    """
    Create a continual learner equipped with the chosen strategy and gradient clipping.

    Args:
        model:              CyberDefenseNet instance
        device:             torch.device (cpu or cuda)
        strategy_name:      Name of strategy ("EWC", "GEM", or "Naive")
        ewc_lambda:         Regularization strength for EWC.
        patterns_per_exp:   Number of patterns to store in memory per experience for GEM.
        memory_strength:    Memory strength parameter for GEM.
        class_weights:      List of 5 floats for class weights.
        lr:                 Learning rate for the local SGD optimizer.
        momentum:           Momentum for the local SGD optimizer.
        batch_size:         Batch size for training and evaluation.
        dp_enabled:         Whether client-level DP-SGD is enabled.
        dp_noise_multiplier: Noise multiplier for DP-SGD.
        dp_max_grad_norm:   Gradient clip norm threshold for DP-SGD.

    Returns:
        Avalanche training strategy object with train() and eval() methods.
    """
    if class_weights is None:
        class_weights = [12.0, 3.0, 3.0, 15.0, 1.0]
    
    weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)
    # Normalize class weights so they sum to the number of classes, preventing gradient explosion/NaNs
    weights_tensor = (weights_tensor / weights_tensor.sum()) * len(class_weights)

    optimizer = SGD(model.parameters(), lr=lr, momentum=momentum)

    # Register gradient clipping and DP noise hook on optimizer step.
    # This fires before each parameter update.
    _orig_step = optimizer.step

    def _clipped_step(closure=None):
        if dp_enabled:
            # NOTE: This implementation performs batch-level gradient clipping and noise injection
            # (Batch-Level Gradient Regularization). While it enforces robustness and guards against
            # gradient explosion, formal Differential Privacy (DP-SGD) mathematically requires
            # per-sample gradient clipping BEFORE batch averaging. This batch-level approximation
            # acts as a strong regularizer but does not yield formal (epsilon, delta) privacy bounds.
            # 1. Clip gradient to dp_max_grad_norm
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=dp_max_grad_norm)
            # 2. Add Gaussian noise to gradients
            # Scale noise std by (noise_multiplier * max_grad_norm) / batch_size
            noise_std = (dp_noise_multiplier * dp_max_grad_norm) / batch_size
            for p in model.parameters():
                if p.grad is not None:
                    noise = torch.randn_like(p.grad) * noise_std
                    p.grad.add_(noise)
        else:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=_GRAD_CLIP_MAX_NORM)
        return _orig_step(closure)

    optimizer.step = _clipped_step

    criterion = CrossEntropyLoss(weight=weights_tensor)
    strat = strategy_name.upper()

    if strat == "EWC":
        print(f"[cl_strategy] Initializing EWC with lambda={ewc_lambda}")
        return EWC(
            model=model,
            optimizer=optimizer,
            criterion=criterion,
            ewc_lambda=ewc_lambda,
            train_mb_size=batch_size,
            train_epochs=1,
            eval_mb_size=batch_size,
            device=device,
        )
    elif strat == "GEM":
        print(f"[cl_strategy] Initializing GEM with patterns={patterns_per_exp}, memory_strength={memory_strength}")
        return GEM(
            model=model,
            optimizer=optimizer,
            criterion=criterion,
            patterns_per_exp=patterns_per_exp,
            memory_strength=memory_strength,
            train_mb_size=batch_size,
            train_epochs=1,
            eval_mb_size=batch_size,
            device=device,
        )
    elif strat == "NAIVE":
        print("[cl_strategy] Initializing Naive (baseline) strategy")
        return Naive(
            model=model,
            optimizer=optimizer,
            criterion=criterion,
            train_mb_size=batch_size,
            train_epochs=1,
            eval_mb_size=batch_size,
            device=device,
        )
    else:
        raise ValueError(f"Unknown continual learning strategy: {strategy_name}")

