#!/usr/bin/env python3
"""
tools/audit_all.py — Unified Pre-Commit Quality & Fact-Checking Runner

Executes the full static analysis, codebase invariant, configuration schema,
and documentation link integrity verification suites in a single command:
1. tools/audit_codebase.py
2. tools/audit_docs.py

Returns exit code 0 if all tests pass, 1 if any error is detected.
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd, desc):
    print(f"[*] Running: {desc}...")
    result = subprocess.run([sys.executable] + cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"\n[FAIL] {desc} encountered errors (exit code: {result.returncode})")
        return False
    print(f"[PASS] {desc} completed successfully.\n")
    return True


def main():
    print("=" * 70)
    print("       FL-CL UNIFIED PRE-COMMIT QUALITY & AUDITING SUITE")
    print("=" * 70 + "\n")

    steps = [
        (["tools/audit_codebase.py"], "Codebase & Config Invariant Auditor"),
        (["tools/audit_docs.py"], "Documentation Link & Figure Validator"),
    ]

    all_passed = True
    for cmd, desc in steps:
        passed = run_command(cmd, desc)
        if not passed:
            all_passed = False
            break

    if not all_passed:
        print("=" * 70)
        print("[BLOCKER] Pre-commit audit failed! Please resolve issues before commit.")
        print("=" * 70)
        sys.exit(1)

    print("=" * 70)
    print("[SUCCESS] All codebase, config, and documentation audits passed!")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unified Pre-Commit Quality & Fact-Checking Runner"
    )
    _ = parser.parse_args()
    main()
