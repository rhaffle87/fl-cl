#!/usr/bin/env python3
"""
tools/deploy_benchmark_matrix.py — Automated Batch Benchmark & Matrix Evaluation Suite

Orchestrates sequential, unattended execution across multiple experiment configuration
tiers (Quick, Security, Continual Learning, Multi-Backbone, or All 17 Profiles).
Parses results and generates a consolidated comparison matrix at data/reports/batch_benchmark_matrix.csv.

Usage:
    python3 tools/deploy_benchmark_matrix.py [--tier quick|security|continual|backbone|all] [--dry-run]
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs" / "experiments"

TIER_MAP = {
    "quick": [
        "benchmark_tier1_quick.yaml",
        "scenario_quick.yaml",
    ],
    "security": [
        "scenario_poisoning.yaml",
        "benchmark_poisoning_dp.yaml",
        "scenario_robust_agg.yaml",
        "scenario_dp_sgd.yaml",
    ],
    "continual": [
        "benchmark_gem_botnet.yaml",
        "benchmark_gem_precision.yaml",
        "benchmark_dropout.yaml",
    ],
    "backbone": [
        "benchmark_backbone_mlp.yaml",
        "benchmark_backbone_transformer.yaml",
        "production_baseline_100r.yaml",
    ],
    "all": None,  # All discovered files
}


def resolve_tier_configs(tier_name: str):
    if tier_name == "all":
        return sorted(list(CONFIGS_DIR.glob("*.yaml")))
    
    file_list = TIER_MAP.get(tier_name, [])
    resolved = []
    for f in file_list:
        p = CONFIGS_DIR / f
        if p.exists():
            resolved.append(p)
    return resolved


def main():
    parser = argparse.ArgumentParser(description="FL-CL Batch Benchmark Matrix Evaluator")
    parser.add_argument(
        "--tier",
        default="quick",
        choices=["quick", "security", "continual", "backbone", "all"],
        help="Benchmark tier to execute (default: quick)"
    )
    parser.add_argument("--attack-engine", default="auto", choices=["auto", "kali", "python"], help="Attack generation engine")
    parser.add_argument("--dry-run", action="store_true", help="Simulate batch execution without launching remote cluster runners")
    parser.add_argument("--out-report", default="data/reports/batch_benchmark_matrix.csv", help="Destination CSV report path")
    args = parser.parse_args()

    print("=" * 80)
    print("       FL-CL AUTOMATED BATCH BENCHMARK MATRIX ORCHESTRATOR")
    print("=" * 80)

    configs = resolve_tier_configs(args.tier)
    print(f"[*] Target Tier: '{args.tier.upper()}' | Discovered {len(configs)} configuration profiles:")
    for idx, cfg in enumerate(configs, 1):
        print(f"  [{idx:2d}] {cfg.name}")

    if not configs:
        print("[!] No configurations found for specified tier.")
        sys.exit(1)

    if args.dry_run:
        print("\n[OK] Dry-run validation passed. All target configuration profiles exist and resolve.")
        print("=" * 80)
        return

    results = []
    print("\n[*] Commencing sequential benchmark matrix execution...")
    start_total_time = time.time()

    for idx, cfg in enumerate(configs, 1):
        print("\n" + "-" * 80)
        print(f"[*] Executing Run [{idx}/{len(configs)}]: {cfg.name}")
        print("-" * 80)

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "src" / "orchestrate.py"),
            "--config", str(cfg),
            "--attack-engine", args.attack_engine,
        ]

        t0 = time.time()
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        elapsed = time.time() - t0

        status = "SUCCESS" if proc.returncode == 0 else "FAILED"
        print(f"[*] Completed in {elapsed:.2f}s | Exit Status: {status}")

        results.append({
            "Tier": args.tier,
            "Config": cfg.name,
            "Attack_Engine": args.attack_engine,
            "Status": status,
            "Duration_sec": round(elapsed, 2),
            "Exit_Code": proc.returncode,
        })

    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 80)
    print(f"[*] Batch matrix execution completed in {total_elapsed:.2f}s")
    print("=" * 80)

    df = pd.DataFrame(results)
    out_path = Path(PROJECT_ROOT / args.out_report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[OK] Batch Benchmark Matrix scorecard saved to: {out_path}\n")


if __name__ == "__main__":
    main()
