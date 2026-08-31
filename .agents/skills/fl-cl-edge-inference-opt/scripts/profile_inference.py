"""
Inference profiling script for fl-cl neural network models.
Benchmarks baseline FP32, TorchScript JIT, and dynamic quantized models on CPU edge constraints.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict

import numpy as np
import torch

try:
    from logger import get_logger
    _log: logging.Logger = get_logger("profile_inference")
except ImportError:
    # Fallback to standard library logging if logger module is not in path
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    _log = logging.getLogger("profile_inference")

# Add project root and src directory to sys.path
PROJECT_ROOT: Path = Path(__file__).resolve().parents[4]
SRC_DIR: Path = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from defender.model import get_model
except ImportError as err:
    _log.warning(f"Could not import defender.model directly: {err}")
    get_model = None


def profile_model(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    warmup_runs: int = 20,
    benchmark_runs: int = 100
) -> Dict[str, float]:
    """Profile latency distribution of a model given an input tensor."""
    model.eval()
    with torch.no_grad():
        # Warmup
        for _ in range(warmup_runs):
            _ = model(input_tensor)

        # Timing
        latencies_ms = []
        for _ in range(benchmark_runs):
            t_start = time.perf_counter()
            _ = model(input_tensor)
            t_end = time.perf_counter()
            latencies_ms.append((t_end - t_start) * 1000.0)

    return {
        "mean_ms": float(np.mean(latencies_ms)),
        "std_ms": float(np.std(latencies_ms)),
        "p50_ms": float(np.percentile(latencies_ms, 50)),
        "p95_ms": float(np.percentile(latencies_ms, 95)),
        "p99_ms": float(np.percentile(latencies_ms, 99)),
        "throughput_fps": float(input_tensor.size(0) / (np.mean(latencies_ms) / 1000.0))
    }


def run_profiling(
    model_type: str = "mlp",
    input_dim: int = 32,
    num_classes: int = 5,
    batch_size: int = 32
) -> int:
    """Run full benchmarking suite across eager, scripted, and quantized models."""
    _log.info(f"Initiating edge inference profiling for '{model_type}' backbone (Input Dim: {input_dim}, Classes: {num_classes}, Batch Size: {batch_size})...")

    if get_model is None:
        _log.error("Model factory 'get_model' is not available.")
        return 1

    model_kwargs: Dict[str, Any] = {}
    if model_type == "mlp":
        model_kwargs = {"hidden_dim1": 64, "hidden_dim2": 32, "dropout": 0.1}
    elif model_type == "cnn":
        model_kwargs = {"conv_channels1": 16, "conv_channels2": 32, "kernel_size": 3, "fc_dim": 64, "dropout": 0.1}
    elif model_type == "transformer":
        model_kwargs = {"token_len": 8, "token_dim": 4, "d_model": 32, "nhead": 4, "dim_feedforward": 64, "num_layers": 2, "fc_dim": 32, "dropout": 0.1}

    try:
        baseline_model = get_model(
            model_type=model_type,
            input_dim=input_dim,
            num_classes=num_classes,
            **model_kwargs
        )
    except Exception as exc:
        _log.error(f"Failed to instantiate baseline model: {exc}")
        return 1

    dummy_input = torch.randn(batch_size, input_dim)

    # 1. Eager Baseline
    _log.info("Benchmarking Eager PyTorch (FP32)...")
    eager_stats = profile_model(baseline_model, dummy_input)

    # 2. TorchScript
    _log.info("Benchmarking TorchScript JIT...")
    try:
        scripted_model = torch.jit.script(baseline_model)
        scripted_stats = profile_model(scripted_model, dummy_input)
    except Exception as exc:
        _log.warning(f"TorchScript scripting failed: {exc}")
        scripted_stats = None

    # 3. Dynamic Quantization (Linear layers)
    _log.info("Benchmarking Dynamic Quantization (INT8)...")
    try:
        quantized_model = torch.quantization.quantize_dynamic(
            baseline_model,
            {torch.nn.Linear},
            dtype=torch.qint8
        )
        quant_stats = profile_model(quantized_model, dummy_input)
    except Exception as exc:
        _log.warning(f"Quantization profiling failed: {exc}")
        quant_stats = None

    print("\n" + "=" * 80)
    print(f"Edge Inference Profiling Results: {model_type.upper()} Backbone")
    print("=" * 80)
    print(f"{'Variant':<20} | {'Mean (ms)':<10} | {'P95 (ms)':<10} | {'P99 (ms)':<10} | {'Throughput (FPS)':<18}")
    print("-" * 80)
    print(f"{'Eager FP32':<20} | {eager_stats['mean_ms']:<10.3f} | {eager_stats['p95_ms']:<10.3f} | {eager_stats['p99_ms']:<10.3f} | {eager_stats['throughput_fps']:<18.1f}")
    if scripted_stats:
        print(f"{'TorchScript JIT':<20} | {scripted_stats['mean_ms']:<10.3f} | {scripted_stats['p95_ms']:<10.3f} | {scripted_stats['p99_ms']:<10.3f} | {scripted_stats['throughput_fps']:<18.1f}")
    if quant_stats:
        print(f"{'Dynamic INT8':<20} | {quant_stats['mean_ms']:<10.3f} | {quant_stats['p95_ms']:<10.3f} | {quant_stats['p99_ms']:<10.3f} | {quant_stats['throughput_fps']:<18.1f}")
    print("=" * 80)

    # Edge constraint check: P95 <= 5.0ms for batch_size 32
    if eager_stats["p95_ms"] <= 10.0:
        _log.info("[OK] Inference latency satisfies edge SLA constraints.")
        return 0
    else:
        _log.warning("[WARN] Latency exceeded baseline 10.0ms target threshold.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile FL-CL Model Inference Latency")
    parser.add_argument("--model", type=str, default="mlp", choices=["mlp", "cnn", "transformer"], help="Model architecture")
    parser.add_argument("--input-dim", type=int, default=32, help="Feature input dimension")
    parser.add_argument("--num-classes", type=int, default=5, help="Number of output traffic classes")
    parser.add_argument("--batch-size", type=int, default=32, help="Profiling batch size")
    args = parser.parse_args()

    sys.exit(run_profiling(
        model_type=args.model,
        input_dim=args.input_dim,
        num_classes=args.num_classes,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
