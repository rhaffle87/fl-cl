#!/usr/bin/env python3
"""
tools/deploy_benchmark_matrix.py — Automated Batch Benchmark & Matrix Evaluation Suite

Orchestrates sequential, unattended execution across multiple experiment configuration
tiers (Quick, Security, Continual Learning, Multi-Backbone, or All 17 Profiles).
Parses results and generates a consolidated comparison matrix at data/reports/benchmarks/batch_benchmark_matrix.csv.

Usage:
    python3 tools/deploy_benchmark_matrix.py [--tier quick|security|continual|backbone|all] [--dry-run]
"""

import argparse
import subprocess
import sys
import time
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

    file_list = TIER_MAP.get(tier_name) or []
    resolved = []
    for f in file_list:
        p = CONFIGS_DIR / f
        if p.exists():
            resolved.append(p)
    return resolved


def main():
    parser = argparse.ArgumentParser(
        description="FL-CL Batch Benchmark Matrix Evaluator"
    )
    parser.add_argument(
        "--tier",
        default="quick",
        choices=["quick", "security", "continual", "backbone", "all"],
        help="Benchmark tier to execute (default: quick)",
    )
    parser.add_argument(
        "--attack-engine",
        default="auto",
        choices=["auto", "kali", "python"],
        help="Attack generation engine",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate batch execution without launching remote cluster runners",
    )
    parser.add_argument(
        "--resume-failed",
        action="store_true",
        help="Skip configs that previously exited with SUCCESS in out-report",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds per configuration run (default: None)",
    )
    parser.add_argument(
        "--out-report",
        default="data/reports/benchmarks/batch_benchmark_matrix.csv",
        help="Destination CSV report path",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("       FL-CL AUTOMATED BATCH BENCHMARK MATRIX ORCHESTRATOR")
    print("=" * 80)

    configs = resolve_tier_configs(args.tier)
    print(
        f"[*] Target Tier: '{args.tier.upper()}' | Discovered {len(configs)} configuration profiles:"
    )
    for idx, cfg in enumerate(configs, 1):
        print(f"  [{idx:2d}] {cfg.name}")

    if not configs:
        print("[!] No configurations found for specified tier.")
        sys.exit(1)

    # Check for previously completed successful runs if resume requested
    completed_configs = set()
    out_path = Path(PROJECT_ROOT / args.out_report)
    if args.resume_failed and out_path.exists():
        try:
            prev_df = pd.read_csv(out_path)
            if "Config" in prev_df.columns and "Status" in prev_df.columns:
                completed_configs = set(
                    prev_df[prev_df["Status"] == "SUCCESS"]["Config"].tolist()
                )
                print(
                    f"[*] Resume active: Found {len(completed_configs)} previously successful runs to skip."
                )
        except Exception as e:
            print(f"[*] Warning: Could not parse previous report for resume ({e})")

    if args.dry_run:
        print(
            "\n[OK] Dry-run validation passed. All target configuration profiles exist and resolve."
        )
        if completed_configs:
            print(
                f"[*] Would skip {len(completed_configs)} already completed profiles."
            )
        print("=" * 80)
        return

    results = []
    print("\n[*] Commencing sequential benchmark matrix execution...")
    start_total_time = time.time()

    for idx, cfg in enumerate(configs, 1):
        if cfg.name in completed_configs:
            print(f"[*] Skipping completed run [{idx}/{len(configs)}]: {cfg.name}")
            results.append(
                {
                    "Tier": args.tier,
                    "Config": cfg.name,
                    "Attack_Engine": args.attack_engine,
                    "Status": "SUCCESS (SKIPPED)",
                    "Duration_sec": 0.0,
                    "Exit_Code": 0,
                }
            )
            continue

        print("\n" + "-" * 80)
        print(f"[*] Executing Run [{idx}/{len(configs)}]: {cfg.name}")
        print("-" * 80)

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "src" / "orchestrate.py"),
            "--config",
            str(cfg),
            "--attack-engine",
            args.attack_engine,
        ]

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=args.timeout,
            )
            elapsed = time.time() - t0
            status = "SUCCESS" if proc.returncode == 0 else "FAILED"
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            status = "TIMEOUT"
            exit_code = -1
            print(f"[!] Run exceeded timeout limit of {args.timeout}s.")

        print(f"[*] Completed in {elapsed:.2f}s | Exit Status: {status}")

        results.append(
            {
                "Tier": args.tier,
                "Config": cfg.name,
                "Attack_Engine": args.attack_engine,
                "Status": status,
                "Duration_sec": round(elapsed, 2),
                "Exit_Code": exit_code,
            }
        )

    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 80)
    print(f"[*] Batch matrix execution completed in {total_elapsed:.2f}s")
    print("=" * 80)

    df = pd.DataFrame(results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[OK] Batch Benchmark Matrix scorecard saved to: {out_path}")

    # Generate companion markdown summary
    md_summary_dir = PROJECT_ROOT / "data" / "reports" / "summaries"
    md_summary_dir.mkdir(parents=True, exist_ok=True)
    md_summary_path = md_summary_dir / "batch_benchmark_matrix.md"
    try:
        success_count = sum(1 for r in results if "SUCCESS" in r["Status"])
        total_runs = len(results)
        with open(md_summary_path, "w", encoding="utf-8") as f:
            f.write("# Batch Benchmark Matrix Execution Summary\n\n")
            f.write(f"- **Tier**: `{args.tier.upper()}`\n")
            f.write(f"- **Total Configurations**: {total_runs}\n")
            f.write(
                f"- **Success Rate**: {success_count}/{total_runs} ({(success_count/max(total_runs,1))*100:.1f}%)\n"
            )
            f.write(f"- **Total Duration**: {total_elapsed:.2f}s\n\n")
            f.write("## Detailed Results\n\n")
            f.write(
                "| # | Configuration Profile | Attack Engine | Status | Duration (s) | Exit Code |\n"
            )
            f.write("| :-: | :--- | :--- | :---: | :---: | :---: |\n")
            for idx, r in enumerate(results, 1):
                f.write(
                    f"| {idx} | `{r['Config']}` | {r['Attack_Engine']} | **{r['Status']}** | {r['Duration_sec']} | {r['Exit_Code']} |\n"
                )
        print(f"[OK] Companion Markdown summary saved to: {md_summary_path}\n")
    except Exception as md_err:
        print(f"[*] Warning: Could not write markdown summary: {md_err}\n")


if __name__ == "__main__":
    main()
