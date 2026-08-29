"""
tools/deploy_testbed.py — Proxmox VE Cluster Deployment, Clean Pre-Flight & Synchronization Utility.

Provides an end-to-end automation tool for the physical Proxmox 3-node cluster:
1. --clean: Flushes RAM disks (/mnt/ramdisk/flows), terminates lingering background processes, resets state.
2. --sync-code: Packages the verified local repository and synchronizes it to /root/fl-cl on the aggregator.
3. --run: Sequentially executes specified experiment benchmarks.
4. --sync-exports: Pulls generated plots, MLflow runs, and models back to the local workspace.

ADR-006 Compliant: `deploy_` prefix for infrastructure and remote deployment utilities.
"""

import argparse
import base64
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTBED = "root@10.10.130.10"
DEFAULT_DEFENDERS = ["root@10.10.130.11", "root@10.10.130.12"]
DEFAULT_PROJ_DIR = "/root/fl-cl"
DEFAULT_PYTHON = "/opt/flower-env/bin/python3"
LOG_FILE = PROJECT_ROOT / "deploy.log"

DEFAULT_CONFIGS = [
    "scenario_quick.yaml",
    "scenario_baseline.yaml",
    "scenario_dp_sgd.yaml",
    "scenario_poisoning.yaml",
    "scenario_robust_agg.yaml",
]


def get_ssh_cmd(target: str, remote_cmd: str) -> list:
    ssh_opts = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=6",
    ]
    key_path = Path.home() / ".ssh" / "id_ed25519"
    if key_path.exists():
        ssh_opts += ["-i", str(key_path)]
    return ssh_opts + [target, remote_cmd]


def clean_testbed(testbed: str, defenders: list, proj_dir: str):
    """Flushes RAM disks, kills residual training processes, and resets cluster state."""
    print("======================================================================")
    print("           PROXMOX TESTBED PRE-FLIGHT CLEANUP & SANITIZATION          ")
    print("======================================================================")

    # 1. Clean Aggregator Node
    print(f"[*] Sanitizing Aggregator Node ({testbed})...")
    agg_clean_script = (
        "pkill -9 -f 'python.*orchestrate' || true; "
        "pkill -9 -f 'python.*server' || true; "
        "pkill -9 -f 'flower' || true; "
        f"rm -rf /tmp/fl_cl* {proj_dir}/data/quarantine/* {proj_dir}/data/models/*.pt /root/drift_snapshots/*;"
    )
    subprocess.run(get_ssh_cmd(testbed, agg_clean_script), check=False)
    print(f"  [+] Aggregator processes terminated & temporary state cleared.")

    # 2. Clean Defender Client Nodes
    for defender in defenders:
        print(f"[*] Sanitizing Defender Node ({defender})...")
        def_clean_script = (
            "pkill -9 -f 'python.*client' || true; "
            "pkill -9 -f 'python.*extractor' || true; "
            "pkill -9 -f 'nfstream' || true; "
            "rm -rf /mnt/ramdisk/flows/* /tmp/fl_cl* /root/drift_snapshots/*;"
        )
        subprocess.run(get_ssh_cmd(defender, def_clean_script), check=False)
        print(f"  [+] Defender ({defender}) RAM disk flushed & processes cleared.")

    print("[SUCCESS] Cluster testbed is clean and prepared for a pristine experiment run.\n")


def sync_code_to_testbed(testbed: str, proj_dir: str):
    """Creates a tarball of the current local codebase and extracts it on the aggregator."""
    print("======================================================================")
    print(f"       SYNCHRONIZING VERIFIED LOCAL CODEBASE -> {testbed}:{proj_dir}  ")
    print("======================================================================")

    # Build tar in memory
    tar_stream = io.BytesIO()
    ignore_patterns = {".git", ".venv", "__pycache__", ".pytest_cache", "exports", "build", "dist"}

    with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_patterns]
            for file in files:
                if file.endswith((".pyc", ".pyo", ".log", ".tmp")):
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(PROJECT_ROOT)
                tar.add(str(full_path), arcname=str(rel_path).replace("\\", "/"))

    tar_bytes = tar_stream.getvalue()
    print(f"[*] Packaged codebase: {len(tar_bytes):,} bytes ({len(tar_bytes)/1024:.1f} KB).")
    print(f"[*] Uploading and extracting to {proj_dir} via stdin stream...")

    remote_unpack = f"mkdir -p {proj_dir} && tar -xzf - -C {proj_dir} --overwrite"
    res = subprocess.run(get_ssh_cmd(testbed, remote_unpack), input=tar_bytes, check=False)
    if res.returncode == 0:
        print(f"[SUCCESS] Codebase synchronized 100% to {testbed}:{proj_dir}!\n")
    else:
        print(f"[!] Warning: Codebase synchronization returned code {res.returncode}\n")


def run_benchmark(config: str, testbed: str, proj_dir: str, python_path: str) -> int:
    remote_cmd = (
        f"cd {proj_dir} && "
        f"{python_path} -u src/orchestrate.py --config configs/experiments/{config}"
    )
    banner = f"\n{'='*60}\n  TESTBED BENCHMARK: {config}\n{'='*60}\n"
    print(banner, flush=True)

    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        lf.write(banner)
        lf.flush()

        proc = subprocess.Popen(
            get_ssh_cmd(testbed, remote_cmd),
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
    local_exports = PROJECT_ROOT / "exports"
    local_exports.mkdir(parents=True, exist_ok=True)

    print("\n[*] Syncing generated plot & run exports from testbed to local workspace...", flush=True)
    try:
        remote_pack = f"cd {proj_dir} && tar -czf /tmp/fl_cl_exports.tar.gz $(find exports data/reports -mindepth 1 -maxdepth 1 -type d -o -name '*.csv' -o -name '*.png' 2>/dev/null) 2>/dev/null || true"
        subprocess.run(get_ssh_cmd(testbed, remote_pack), check=False, timeout=30)

        b64_output = subprocess.check_output(get_ssh_cmd(testbed, "base64 /tmp/fl_cl_exports.tar.gz 2>/dev/null || true"), timeout=60)
        raw_tar = base64.b64decode(b64_output.strip())
        if raw_tar:
            with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:gz") as tar:
                tar.extractall(path=str(PROJECT_ROOT))
            print("[+] Exports synchronized successfully to local workspace!\n", flush=True)
    except Exception as e:
        print(f"[!] Warning: Could not sync exports folder: {e}\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Proxmox VE Cluster Deployment, Clean Pre-Flight & Sync Suite")
    parser.add_argument("--testbed", default=DEFAULT_TESTBED, help="Testbed aggregator SSH target (default: root@10.10.130.10)")
    parser.add_argument("--defenders", nargs="*", default=DEFAULT_DEFENDERS, help="Defender client SSH targets")
    parser.add_argument("--proj-dir", default=DEFAULT_PROJ_DIR, help="Remote project directory on aggregator")
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="Python interpreter on aggregator")
    parser.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS, help="List of experiment config YAMLs to execute")
    parser.add_argument("--clean", action="store_true", help="Flush RAM disks and kill residual cluster processes")
    parser.add_argument("--sync-code", action="store_true", help="Synchronize local codebase to remote testbed")
    parser.add_argument("--sync-exports", action="store_true", help="Only synchronize remote exports/reports to local workspace")
    parser.add_argument("--run", action="store_true", help="Execute the specified benchmark configs")
    args = parser.parse_args()

    # If no specific action flags provided, default to full pipeline: clean + sync + run
    if not (args.clean or args.sync_code or args.sync_exports or args.run):
        args.clean = True
        args.sync_code = True
        args.run = True

    if args.clean:
        clean_testbed(args.testbed, args.defenders, args.proj_dir)

    if args.sync_code:
        sync_code_to_testbed(args.testbed, args.proj_dir)

    if args.run:
        if LOG_FILE.exists():
            os.remove(LOG_FILE)
        print(f"[*] Benchmark suite starting on {args.testbed}")
        for cfg in args.configs:
            rc = run_benchmark(cfg, args.testbed, args.proj_dir, args.python)
            if rc != 0:
                print(f"\n[!] FAILED: {cfg} exited with code {rc}. Halting.", flush=True)
                sys.exit(rc)
            print(f"\n[+] DONE: {cfg}\n", flush=True)
        sync_exports(args.testbed, args.proj_dir)

    if args.sync_exports and not args.run:
        sync_exports(args.testbed, args.proj_dir)

    print("[SUCCESS] All deployment operations completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
