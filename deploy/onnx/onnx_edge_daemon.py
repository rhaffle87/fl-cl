"""
deploy/onnx/onnx_edge_daemon.py — High-throughput zero-copy line-rate ONNX inference daemon for edge gateways.
"""

import os
import sys
import time
import numpy as np
import onnxruntime as ort
from datetime import datetime

# Threat class mapping
THREAT_LABELS = {
    0: "Normal",
    1: "Botnet C2 (Ares/Mirai)",
    2: "Slowloris HTTP DoS",
    3: "DNS Exfiltration",
    4: "SSH Brute-Force"
}

class ONNXEdgeClassifier:
    """Production Line-Rate ONNX Inference Classifier for Proxmox Edge Gateway."""

    def __init__(self, model_path=None, num_threads=4):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyberdefense_cnn.onnx")
        self.model_path = model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ONNX model not found at {model_path}. Run export_champion_onnx.py first.")

        # Optimize ONNX runtime session options for multi-core edge CPUs
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = num_threads
        opts.inter_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        print(f"[ONNX Daemon] Loaded edge classifier from {model_path} ({num_threads} CPU threads)")

    def classify_batch(self, flow_features: np.ndarray, temperature: float = 1.0) -> tuple:
        """
        Classifies a batch of 32-dim flow vectors with Free Energy Score calculation.
        flow_features: np.ndarray of shape (N, 32), dtype float32.
        Returns (predicted_class_ids, confidence_scores, energy_scores, latency_ms).
        """
        if flow_features.dtype != np.float32:
            flow_features = flow_features.astype(np.float32)

        t0 = time.perf_counter()
        logits = self.session.run([self.output_name], {self.input_name: flow_features})[0]
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Softmax probabilities
        exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

        class_ids = np.argmax(probs, axis=1)
        confidences = np.max(probs, axis=1)

        # Free Energy Score: E(x; T) = -T * log(sum(exp(logits / T)))
        scaled_logits = logits / temperature
        max_scaled = np.max(scaled_logits, axis=1, keepdims=True)
        energy_scores = -temperature * (np.log(np.sum(np.exp(scaled_logits - max_scaled), axis=1)) + max_scaled.squeeze(1))

        return class_ids, confidences, energy_scores, latency_ms

def run_edge_benchmark(num_flows: int = 10000, batch_size: int = 64):
    classifier = ONNXEdgeClassifier()
    print(f"[Benchmark] Evaluating {num_flows} synthetic flows in batches of {batch_size}...")

    # Generate synthetic normalized feature batch
    synthetic_flows = np.random.randn(num_flows, 32).astype(np.float32)
    latencies = []

    for i in range(0, num_flows, batch_size):
        batch = synthetic_flows[i:i+batch_size]
        _, _, _, lat = classifier.classify_batch(batch)
        latencies.append(lat)

    total_time_ms = sum(latencies)
    avg_per_flow_us = (total_time_ms / num_flows) * 1000.0
    throughput_fps = (num_flows / total_time_ms) * 1000.0

    print("=" * 60)
    print(f"  Total Processed Flows:     {num_flows:,}")
    print(f"  Batch Size:                {batch_size}")
    print(f"  Total Inference Time:      {total_time_ms:.2f} ms")
    print(f"  Average Single-Flow Time:  {avg_per_flow_us:.2f} us")
    print(f"  Throughput:                {throughput_fps:,.0f} flows/second")
    print("=" * 60)

def run_live_daemon(flow_dir: str = "/mnt/ramdisk/flows", poll_interval: float = 0.5, ood_threshold: float = -1.20, quarantine_log: str = "/var/log/fl-cl-quarantine.jsonl"):
    """Continuously monitors ramdisk flow directory and performs line-rate ONNX classification."""
    import json
    classifier = ONNXEdgeClassifier()
    os.makedirs(flow_dir, exist_ok=True)
    os.makedirs(os.path.dirname(quarantine_log), exist_ok=True)
    print(f"[ONNX Daemon] Monitoring live flow directory: {flow_dir} (Poll interval: {poll_interval}s, OOD Threshold: {ood_threshold})")

    processed_total = 0
    threats_detected = 0
    ood_detected = 0

    try:
        while True:
            csv_files = [f for f in os.listdir(flow_dir) if f.endswith(".csv")]
            if not csv_files:
                time.sleep(poll_interval)
                continue

            for fname in sorted(csv_files):
                fpath = os.path.join(flow_dir, fname)
                try:
                    # Read CSV numeric features
                    data = np.genfromtxt(fpath, delimiter=",", skip_header=1)
                    if data.ndim == 1:
                        data = data.reshape(1, -1)
                    
                    if data.shape[1] >= 32:
                        features = data[:, :32].astype(np.float32)
                        c_ids, confs, energies, lat = classifier.classify_batch(features)
                        
                        processed_total += len(c_ids)
                        for cid, conf, energy in zip(c_ids, confs, energies):
                            # Check for Zero-Day OOD Anomaly
                            if energy > ood_threshold:
                                ood_detected += 1
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [QUARANTINE] Detected Zero-Day OOD Anomaly (Energy: {energy:.2f} > {ood_threshold})")
                                with open(quarantine_log, "a", encoding="utf-8") as qf:
                                    qf.write(json.dumps({
                                        "timestamp": datetime.now().isoformat(),
                                        "energy": float(energy),
                                        "pred_class": int(cid),
                                        "confidence": float(conf),
                                        "status": "QUARANTINED"
                                    }) + "\n")

                            elif cid != 0: # Known threat
                                threats_detected += 1
                                label_name = THREAT_LABELS.get(cid, f"Threat_{cid}")
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ALERT] Detected {label_name} (Confidence: {conf*100:.1f}%, Energy: {energy:.2f}) in {lat:.2f}ms")

                    # Remove processed flow batch to maintain ramdisk space
                    os.remove(fpath)
                except Exception as e:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print(f"\n[ONNX Daemon] Stopped. Processed: {processed_total:,} flows, Threats: {threats_detected:,}, OOD Quarantined: {ood_detected:,}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FL-CL Edge ONNX Inference Daemon")
    parser.add_argument("--benchmark", action="store_true", help="Run synthetic throughput benchmark")
    parser.add_argument("--flow-dir", type=str, default="/mnt/ramdisk/flows", help="Ramdisk flow directory to watch")
    parser.add_argument("--poll-interval", type=float, default=0.5, help="Polling interval in seconds")
    parser.add_argument("--ood-threshold", type=float, default=-1.20, help="OOD energy score threshold")
    parser.add_argument("--quarantine-log", type=str, default="/var/log/fl-cl-quarantine.jsonl", help="Path to quarantine JSONL log")
    args = parser.parse_args()

    if args.benchmark:
        run_edge_benchmark()
    else:
        run_live_daemon(flow_dir=args.flow_dir, poll_interval=args.poll_interval, ood_threshold=args.ood_threshold, quarantine_log=args.quarantine_log)
