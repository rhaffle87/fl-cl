"""
deploy_to_testbed.py
Run all 4 benchmark suites sequentially on the Proxmox testbed
(aggregator: root@10.10.130.10) via passwordless SSH.

Order: quick -> balanced -> stressed -> realworld
"""

import subprocess
import sys
import os

# Force UTF-8 output on Windows so Unicode log lines don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TESTBED  = "root@10.10.130.10"
PROJ_DIR = "/root/fl-cl"
PYTHON   = "/opt/flower-env/bin/python3"
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "deploy.log")

CONFIGS = [
    "quick_test.yaml",
    "baseline.yaml",
    "dp_sgd.yaml",
    "data_poisoning.yaml",
    "robust_agg.yaml",
    "benchmark_quick.yaml",
    "benchmark_balanced.yaml",
    "benchmark_stressed.yaml",
    "benchmark_realworld.yaml",
]

def run(config: str) -> int:
    remote_cmd = (
        f"cd {PROJ_DIR} && "
        f"{PYTHON} -u src/orchestrate.py --config configs/experiments/{config}"
    )
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=6",
        TESTBED,
        remote_cmd,
    ]

    banner = f"\n{'='*60}\n  TESTBED BENCHMARK: {config}\n{'='*60}\n"
    print(banner, flush=True)

    with open(LOG_FILE, "a") as lf:
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


def sync_exports():
    """Sync remote exports folder from testbed to local workspace."""
    local_exports = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports"))
    os.makedirs(local_exports, exist_ok=True)
    scp_cmd = [
        "scp",
        "-r",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        f"{TESTBED}:{PROJ_DIR}/exports/*",
        local_exports,
    ]
    print("\n[*] Syncing generated plot & run exports from testbed to local workspace...", flush=True)
    try:
        subprocess.run(scp_cmd, check=True)
        print("[+] Exports synchronized successfully to local exports/ directory!\n", flush=True)
    except Exception as e:
        print(f"[!] Warning: Could not sync exports folder: {e}\n", flush=True)


def main():
    # Wipe previous deploy.log so results are fresh
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    print(f"[*] Benchmark suite starting on {TESTBED}")
    print(f"[*] Log file -> {os.path.abspath(LOG_FILE)}\n")

    for cfg in CONFIGS:
        rc = run(cfg)
        if rc != 0:
            print(f"\n[!] FAILED: {cfg} exited with code {rc}. Halting.", flush=True)
            sys.exit(rc)
        print(f"\n[+] DONE: {cfg}\n", flush=True)

    sync_exports()
    print("\n[*] All benchmark tiers completed successfully!", flush=True)


if __name__ == "__main__":
    main()

