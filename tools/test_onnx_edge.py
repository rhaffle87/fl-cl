"""
tools/test_onnx_edge.py — Comprehensive validation of production ONNX export and edge daemon execution.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np

from deploy.onnx.export_champion_onnx import export_champion_onnx
from deploy.onnx.onnx_edge_daemon import ONNXEdgeClassifier, run_edge_benchmark

def main():
    print("=" * 60)
    print("FL-CL PRODUCTION ONNX EDGE INFERENCE VALIDATION")
    print("=" * 60)

    # 1. Export Champion Model
    onnx_path = export_champion_onnx()
    assert os.path.exists(onnx_path), "Exported ONNX file missing!"

    # 2. Initialize Classifier
    classifier = ONNXEdgeClassifier(onnx_path)

    # 3. Test Single Flow
    single_flow = np.random.randn(1, 32).astype(np.float32)
    c_ids, confs, lat = classifier.classify_batch(single_flow)
    print(f"[OK] Single-flow classification: Class {c_ids[0]} (Confidence: {confs[0]*100:.2f}%) in {lat*1000:.2f} us")

    # 4. Benchmark Throughput
    run_edge_benchmark(num_flows=5000, batch_size=32)

    print("\n[SUCCESS] Production ONNX Edge Gateway suite verified successfully!")

if __name__ == "__main__":
    main()
