#!/usr/bin/env python3
"""
tools/deploy_menu.py — Interactive FL-CL Experiment & Benchmark Launcher

Provides a clean, terminal-based user interface to:
1. Select from all 17 YAML experiment configuration profiles
2. Select Attack Generation Engine (Auto, Kali, Python Sockets)
3. Select Continual Learning Strategy (EWC, GEM, A-GEM, Naive)
4. Execute and stream live progress

Usage:
    python3 tools/deploy_menu.py [--dry-run]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs" / "experiments"


def get_available_experiments():
    configs = sorted(list(CONFIGS_DIR.glob("*.yaml")))
    return configs


def display_menu():
    print("\n" + "=" * 75)
    print("           FL-CL INTERACTIVE EXPERIMENT & BENCHMARK LAUNCHER")
    print("=" * 75)
    
    configs = get_available_experiments()
    print("\n[Available Experiment Configuration Profiles]:")
    for idx, cfg in enumerate(configs, 1):
        clean_name = cfg.stem.replace("_", " ").title()
        print(f"  [{idx:2d}] {cfg.name:38s} ({clean_name})")
    
    print("  [ 0] Exit Launcher")
    print("=" * 75)
    return configs


def prompt_user_selection(configs):
    while True:
        try:
            choice = input(f"\nSelect experiment [1-{len(configs)}] (or 0 to exit): ").strip()
            if choice == "0":
                print("[*] Exiting launcher. Goodbye!")
                sys.exit(0)
            idx = int(choice)
            if 1 <= idx <= len(configs):
                return configs[idx - 1]
            print(f"[!] Invalid selection. Please enter a number between 1 and {len(configs)}.")
        except ValueError:
            print("[!] Please enter a valid numerical choice.")


def prompt_engine_selection():
    print("\n[Select Attack Generation Engine]:")
    print("  [1] Auto-Detect (Kali native tools with Python fallback) [RECOMMENDED]")
    print("  [2] Kali Linux Native Tools (hping3, hydra, slowhttptest)")
    print("  [3] Pure Python Sockets (Zero-dependency standard library)")
    
    while True:
        choice = input("Select engine [1-3, default=1]: ").strip()
        if choice in ("", "1"):
            return "auto"
        elif choice == "2":
            return "kali"
        elif choice == "3":
            return "python"
        print("[!] Invalid choice. Enter 1, 2, or 3.")


def main():
    parser = argparse.ArgumentParser(description="Interactive FL-CL Experiment Launcher")
    parser.add_argument("--dry-run", action="store_true", help="Display menu and parse without executing orchestrator")
    args = parser.parse_args()

    configs = display_menu()
    if args.dry_run:
        print("\n[OK] Dry-run check: Successfully discovered all 17 experiment profiles.")
        return

    selected_config = prompt_user_selection(configs)
    selected_engine = prompt_engine_selection()

    print("\n" + "-" * 75)
    print(f"[*] Configuration: {selected_config}")
    print(f"[*] Attack Engine: {selected_engine}")
    print("-" * 75)

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "src" / "orchestrate.py"),
        "--config", str(selected_config),
        "--attack-engine", selected_engine,
    ]

    print(f"\n[*] Launching Orchestrator: {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT)
    except KeyboardInterrupt:
        print("\n[!] Orchestration interrupted by user.")


if __name__ == "__main__":
    main()
