"""
cl_strategy.py — Elastic Weight Consolidation (EWC) Continual Learning Strategy

Wraps the CyberDefenseNet model with Avalanche's EWC strategy to prevent
catastrophic forgetting when training on sequential attack tasks.

Research Citations:
- [1] Kirkpatrick, J., et al. (2017). Overcoming catastrophic forgetting in neural networks. PNAS.
  (Theoretical foundation for the EWC penalty mechanism applied below).
- [3] Lopez-Paz, D. & Ranzato, M. (2017). Gradient Episodic Memory for Continual Learning. NeurIPS.
  (Methodological foundation for GEM projection constraints on minority threat classes).

The ewc_lambda parameter (default: 0.8) balances:
  - Plasticity: ability to learn new attack patterns
  - Stability: retention of previously learned attack signatures

Deploy on: Defender VMs (VM 310, VM 320)
"""

import numpy as np
import torch
from torch.optim import SGD
from torch.nn import CrossEntropyLoss
try:
    from avalanche.training.supervised import EWC, Naive, GEM, AGEM
except ImportError:
    try:
        from avalanche.training.supervised import EWC, Naive, GEM
        AGEM = None
    except ImportError:
        EWC = None
        Naive = None
        GEM = None
        AGEM = None


class StandaloneAGEM:
    """
    Pure PyTorch A-GEM (Averaged Gradient Episodic Memory) gradient projection engine.
    Ensures O(d) linear Gram-Schmidt projection without quadratic programming solvers.
    """
    def __init__(self, patterns_per_exp: int = 128, sample_size: int = 64):
        self.patterns_per_exp = patterns_per_exp
        self.sample_size = sample_size
        self.memory_x = []
        self.memory_y = []

    def update_memory(self, dataset):
        for x, y in dataset:
            self.memory_x.append(x)
            self.memory_y.append(y)
            if len(self.memory_x) > self.patterns_per_exp:
                self.memory_x.pop(0)
                self.memory_y.pop(0)

    def project_gradients(self, model):
        if not self.memory_x:
            return
        device = next(model.parameters()).device
        indices = np.random.choice(len(self.memory_x), min(self.sample_size, len(self.memory_x)), replace=False)
        bx = torch.stack([self.memory_x[i] for i in indices]).to(device)
        by = torch.stack([self.memory_y[i] for i in indices]).to(device)

        # Extract current proposed gradient vector
        g_curr = []
        params_with_grad = []
        for p in model.parameters():
            if p.grad is not None:
                g_curr.append(p.grad.data.view(-1).clone())
                params_with_grad.append(p)
        if not g_curr:
            return
        g_curr_flat = torch.cat(g_curr)

        # Compute reference gradient on episodic memory
        model.zero_grad()
        out = model(bx)
        loss = torch.nn.functional.cross_entropy(out, by)
        loss.backward()

        g_ref = []
        for p in params_with_grad:
            if p.grad is not None:
                g_ref.append(p.grad.data.view(-1))
        if not g_ref:
            return
        g_ref_flat = torch.cat(g_ref)

        # Gram-Schmidt projection: if g_curr . g_ref < 0 -> project onto half-space
        dot_prod = torch.dot(g_curr_flat, g_ref_flat)
        if dot_prod < 0:
            ref_norm_sq = torch.dot(g_ref_flat, g_ref_flat) + 1e-12
            proj_g = g_curr_flat - (dot_prod / ref_norm_sq) * g_ref_flat
            offset = 0
            for p in params_with_grad:
                numel = p.numel()
                p.grad.data.copy_(proj_g[offset : offset + numel].view_as(p))
                offset += numel
        else:
            # Restore proposed gradient
            offset = 0
            for p in params_with_grad:
                numel = p.numel()
                p.grad.data.copy_(g_curr_flat[offset : offset + numel].view_as(p))
                offset += numel


# Alias for cross-platform imports
AGEM = StandaloneAGEM


# Gradient clip norm — prevents NaN loss from Fisher penalty or gradient explosion
_GRAD_CLIP_MAX_NORM = 1.0


def get_continual_learner(
    model,
    device,
    strategy_name: str = "EWC",
    ewc_lambda: float = 0.8,
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
        strategy_name:      Name of strategy ("EWC", "GEM", "AGEM", or "Naive")
        ewc_lambda:         Regularization strength for EWC.
        patterns_per_exp:   Number of patterns to store in memory per experience for GEM / A-GEM.
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
        class_weights = [1.0, 250.0, 2.0, 5.0, 50.0]
    
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
    elif strat in ("AGEM", "A-GEM"):
        print(f"[cl_strategy] Initializing A-GEM with patterns={patterns_per_exp}")
        if AGEM is not None:
            return AGEM(
                model=model,
                optimizer=optimizer,
                criterion=criterion,
                patterns_per_exp=patterns_per_exp,
                sample_size=batch_size,
                train_mb_size=batch_size,
                train_epochs=1,
                eval_mb_size=batch_size,
                device=device,
            )
        else:
            print("[cl_strategy] Avalanche AGEM not available; falling back to GEM with linear projection")
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

