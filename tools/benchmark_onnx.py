"""
benchmark_onnx_latency.py — Multi-Runtime Edge Inference Benchmark

Compares PyTorch FP32, PyTorch Dynamic INT8, and ONNX Runtime CPU execution provider
across varied batch sizes (1, 16, 64, 256) for all three model backbones.
"""

import os
import sys
import time
import json
from pathlib import Path
import torch
import numpy as np
import pandas as pd
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "defender"))

from model import get_model

MODELS_DIR = PROJECT_ROOT / "data" / "models"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def benchmark_model_runtimes(model_type: str, batch_sizes=[1, 16, 64, 256], num_runs=500):
    print(f"\n[*] Benchmarking '{model_type}' across runtimes...")
    input_dim = 32
    num_classes = 5

    # 1. PyTorch FP32 & Scripted
    py_model = get_model(model_type, input_dim=input_dim, num_classes=num_classes)
    py_model.eval()
    scripted_model = torch.jit.script(py_model)

    # 2. PyTorch Dynamic INT8
    try:
        q_model = torch.ao.quantization.quantize_dynamic(py_model, {torch.nn.Linear}, dtype=torch.qint8)
        q_model.eval()
    except Exception:
        q_model = py_model

    # 3. ONNX Runtime Session
    onnx_path = MODELS_DIR / f"cyberdefense_{model_type}.onnx"
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    ort_session = ort.InferenceSession(str(onnx_path), sess_options=opts, providers=["CPUExecutionProvider"])
    ort_input_name = ort_session.get_inputs()[0].name

    results = []

    for bs in batch_sizes:
        dummy_tensor = torch.randn(bs, input_dim, dtype=torch.float32)
        dummy_numpy = dummy_tensor.numpy()

        # Warmup
        for _ in range(20):
            _ = scripted_model(dummy_tensor)
            try:
                _ = q_model(dummy_tensor)
            except Exception:
                pass
            _ = ort_session.run(None, {ort_input_name: dummy_numpy})

        # Benchmark PyTorch FP32
        t0 = time.perf_counter()
        with torch.no_grad():
            for _ in range(num_runs):
                _ = scripted_model(dummy_tensor)
        t1 = time.perf_counter()
        torch_fp32_latency_us = ((t1 - t0) / (num_runs * bs)) * 1e6
        torch_fp32_fps = (num_runs * bs) / (t1 - t0)

        # Benchmark PyTorch Dynamic INT8
        t0_q = time.perf_counter()
        with torch.no_grad():
            for _ in range(num_runs):
                try:
                    _ = q_model(dummy_tensor)
                except Exception:
                    _ = scripted_model(dummy_tensor)
        t1_q = time.perf_counter()
        torch_int8_latency_us = ((t1_q - t0_q) / (num_runs * bs)) * 1e6
        torch_int8_fps = (num_runs * bs) / (t1_q - t0_q)

        # Benchmark ONNX Runtime
        t0_ort = time.perf_counter()
        for _ in range(num_runs):
            _ = ort_session.run(None, {ort_input_name: dummy_numpy})
        t1_ort = time.perf_counter()
        ort_latency_us = ((t1_ort - t0_ort) / (num_runs * bs)) * 1e6
        ort_fps = (num_runs * bs) / (t1_ort - t0_ort)

        speedup_ort_vs_fp32 = ort_fps / torch_fp32_fps if torch_fp32_fps > 0 else 1.0

        results.append({
            "model": model_type,
            "batch_size": bs,
            "torch_fp32_us": round(torch_fp32_latency_us, 2),
            "torch_fp32_fps": round(torch_fp32_fps, 1),
            "torch_int8_us": round(torch_int8_latency_us, 2),
            "torch_int8_fps": round(torch_int8_fps, 1),
            "onnx_runtime_us": round(ort_latency_us, 2),
            "onnx_runtime_fps": round(ort_fps, 1),
            "speedup_ort_vs_torch": round(speedup_ort_vs_fp32, 2)
        })

        print(f"  Batch {bs:3d} | Torch FP32: {torch_fp32_latency_us:6.2f} us ({torch_fp32_fps:9,.0f} f/s) | "
              f"ONNX Runtime: {ort_latency_us:6.2f} us ({ort_fps:9,.0f} f/s) [Speedup: {speedup_ort_vs_fp32:.2f}x]")

    return results


def main():
    print("========================================================================")
    print("     FL-CL Multi-Runtime Latency & Throughput Benchmark Suite")
    print("========================================================================")

    all_results = []
    for m in ["cnn", "transformer", "mlp"]:
        res = benchmark_model_runtimes(m)
        all_results.extend(res)

    df = pd.DataFrame(all_results)
    out_csv = REPORTS_DIR / "multi_runtime_latency_report.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[OK] Benchmark completed. Saved multi-runtime report to: {out_csv}")
    print("========================================================================\n")


if __name__ == "__main__":
    main()
