"""
deploy_testbed.py — Proxmox VE Cluster Benchmark Deployment & Synchronization Utility.

Executes configured benchmark experiment suites sequentially on the Proxmox testbed
(aggregator: root@10.10.130.10) via passwordless SSH and synchronizes generated plots/reports.

Usage:
    python3 tools/deploy_testbed.py [--testbed root@10.10.130.10] [--configs scenario_quick.yaml scenario_baseline.yaml]
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

# Force UTF-8 output on Windows so Unicode log lines don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTBED = "root@10.10.130.10"
DEFAULT_PROJ_DIR = "/root/fl-cl"
DEFAULT_PYTHON = "/opt/flower-env/bin/python3"
LOG_FILE = PROJECT_ROOT / "deploy.log"

DEFAULT_CONFIGS = [
    "scenario_quick.yaml",
    "scenario_baseline.yaml",
    "scenario_dp_sgd.yaml",
    "scenario_poisoning.yaml",
    "scenario_robust_agg.yaml",
    "benchmark_tier1_quick.yaml",
    "benchmark_tier2_balanced.yaml",
    "benchmark_tier3_stressed.yaml",
    "benchmark_tier4_realworld.yaml",
]


def run_benchmark(config: str, testbed: str, proj_dir: str, python_path: str) -> int:
    remote_cmd = (
        f"cd {proj_dir} && "
        f"{python_path} -u src/orchestrate.py --config configs/experiments/{config}"
    )
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=6",
        testbed,
        remote_cmd,
    ]

    banner = f"\n{'='*60}\n  TESTBED BENCHMARK: {config}\n{'='*60}\n"
    print(banner, flush=True)

    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        lf.write(banner)
        lf.flush()

        proc = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lf.write(line)
            lf.flush()

        proc.stdout.close()
        return proc.wait()


def sync_exports(testbed: str, proj_dir: str):
    """Sync remote exports folder from testbed to local workspace via compressed archive."""
    import base64
    import io
    import tarfile

    local_exports = PROJECT_ROOT / "exports"
    local_exports.mkdir(parents=True, exist_ok=True)
    key_path = Path.home() / ".ssh" / "id_ed25519"

    ssh_opts = [
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
    ]
    if key_path.exists():
        ssh_opts += ["-i", str(key_path)]

    print("\n[*] Syncing generated plot & run exports from testbed to local workspace...", flush=True)
    try:
        tar_cmd = ["ssh"] + ssh_opts + [testbed, f"cd {proj_dir} && tar -czf /tmp/fl_cl_exports.tar.gz $(find exports -mindepth 1 -maxdepth 1 -type d -mtime -2)"]
        subprocess.run(tar_cmd, check=True, timeout=30)

        b64_cmd = ["ssh"] + ssh_opts + [testbed, "base64 /tmp/fl_cl_exports.tar.gz"]
        b64_output = subprocess.check_output(b64_cmd, timeout=60)
        raw_tar = base64.b64decode(b64_output)
        with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:gz") as tar:
            tar.extractall(path=str(PROJECT_ROOT))
        print("[+] Exports synchronized successfully to local exports/ directory!\n", flush=True)
    except Exception as e:
        print(f"[!] Warning: Could not sync exports folder: {e}\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Proxmox VE Cluster Benchmark Deployment & Sync Suite")
    parser.add_argument("--testbed", default=DEFAULT_TESTBED, help="Testbed aggregator SSH target (default: root@10.10.130.10)")
    parser.add_argument("--proj-dir", default=DEFAULT_PROJ_DIR, help="Remote project directory on aggregator")
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="Python interpreter on aggregator")
    parser.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS, help="List of experiment config YAMLs to execute")
    parser.add_argument("--sync-only", action="store_true", help="Only synchronize exports without running benchmarks")
    args = parser.parse_args()

    if args.sync_only:
        sync_exports(args.testbed, args.proj_dir)
        sys.exit(0)

    if LOG_FILE.exists():
        os.remove(LOG_FILE)

    print(f"[*] Benchmark suite starting on {args.testbed}")
    print(f"[*] Log file -> {LOG_FILE}\n")

    for cfg in args.configs:
        rc = run_benchmark(cfg, args.testbed, args.proj_dir, args.python)
        if rc != 0:
            print(f"\n[!] FAILED: {cfg} exited with code {rc}. Halting.", flush=True)
            sys.exit(rc)
        print(f"\n[+] DONE: {cfg}\n", flush=True)

    sync_exports(args.testbed, args.proj_dir)
    print("\n[*] All benchmark tiers completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
