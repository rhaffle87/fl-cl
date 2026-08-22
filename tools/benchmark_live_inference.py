"""
benchmark_live_inference.py — Real-Time Dual-Node Edge Inference Benchmark (Track B)

Executes concurrent real-time flow classification benchmarking on defender-a (10.10.130.11)
and defender-b (10.10.130.12) physical nodes using PyTorch TorchScript models (FP32 vs INT8).
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DEFENDER_NODES = {
    "defender-a": "10.10.130.11",
    "defender-b": "10.10.130.12",
}

BENCH_SCRIPT = PROJECT_ROOT / "scratch" / "remote_inference_bench.py"


def run_node_benchmark(node_name, node_ip):
    print(f"[*] Deploying and running benchmark on {node_name} ({node_ip})...")
    # SCP script to remote node
    scp_cmd = ["scp", str(BENCH_SCRIPT), f"root@{node_ip}:/root/remote_inference_bench.py"]
    try:
        scp_res = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=15)
        if scp_res.returncode != 0:
            return {"node": node_name, "ip": node_ip, "status": "FAILED_SCP", "error": scp_res.stderr}
    except Exception as e:
        return {"node": node_name, "ip": node_ip, "status": "FAILED_SCP", "error": str(e)}

    # SSH run with virtualenv python or fallback to system python
    run_cmd = [
        "ssh", "-o", "BatchMode=yes", f"root@{node_ip}",
        "if [ -f /root/fl-cl-env/bin/python3 ]; then /root/fl-cl-env/bin/python3 /root/remote_inference_bench.py; else python3 /root/remote_inference_bench.py; fi"
    ]
    try:
        res = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            output = res.stdout
            if "BENCHMARK_JSON_START" in output:
                json_str = output.split("BENCHMARK_JSON_START")[1].split("BENCHMARK_JSON_END")[0].strip()
                data = json.loads(json_str)
                return {"node": node_name, "ip": node_ip, "status": "SUCCESS", "metrics": data}
        return {"node": node_name, "ip": node_ip, "status": "ERROR", "error": res.stderr or res.stdout}
    except Exception as e:
        return {"node": node_name, "ip": node_ip, "status": "FAILED", "error": str(e)}


def main():
    print("========================================================================")
    print("       Dual-Node Real-Time Edge Inference Benchmark (Track B)")
    print("========================================================================")
    
    results = []
    total_fps = 0
    total_int8_fps = 0

    for name, ip in DEFENDER_NODES.items():
        res = run_node_benchmark(name, ip)
        results.append(res)
        if res["status"] == "SUCCESS":
            m = res["metrics"]
            total_fps += m["fp32_throughput_fps"]
            total_int8_fps += m["int8_throughput_fps"]
            print(f"  [OK] {name} ({ip}):")
            print(f"       FP32 Throughput : {m['fp32_throughput_fps']:,.1f} flows/sec | Avg Latency: {m['fp32_latency_us']:.2f} us")
            print(f"       INT8 Throughput : {m['int8_throughput_fps']:,.1f} flows/sec | Avg Latency: {m['int8_latency_us']:.2f} us")
            print(f"       INT8 Speedup    : {m['quantization_speedup']:.2f}x")
        else:
            print(f"  [FAIL] {name} ({ip}): {res.get('error')}")

    print("\n------------------------------------------------------------------------")
    print(f"Aggregate Cluster Throughput (FP32) : {total_fps:,.1f} flows/sec")
    print(f"Aggregate Cluster Throughput (INT8) : {total_int8_fps:,.1f} flows/sec")
    print("========================================================================\n")

    # Write metrics to JSON file for report synthesis
    out_file = PROJECT_ROOT / "scratch" / "dual_node_inference_results.json"
    with open(out_file, "w") as f:
        json.dump({
            "nodes": results,
            "aggregate_fp32_fps": total_fps,
            "aggregate_int8_fps": total_int8_fps
        }, f, indent=2)
    print(f"Saved benchmark results to: {out_file}")


if __name__ == "__main__":
    main()
