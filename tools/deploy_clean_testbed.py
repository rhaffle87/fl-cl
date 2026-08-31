"""
tools/deploy_clean_testbed.py — Cluster Environment & State Cleanup Utility

Wipes MLflow SQLite tracking databases, resets RAMDisk flow buffers, terminates
stale defender/extractor processes, and cleans network services across the 3-node
Proxmox VE testbed (aggregator, defenders, targets, traffic generator).

Usage:
    python tools/deploy_clean_testbed.py --config configs/experiment.yaml
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env(env_name: str = ".env") -> None:
    """Load environment variables from a .env file searching upward from repo root."""
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")


load_env()


def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_ssh(ip: str, command: str, username: str = "root", key_path: str = None) -> subprocess.CompletedProcess:
    opts = ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5"]
    if key_path:
        opts += ["-i", key_path]

    ssh_cmd = ["ssh", "-n"] + opts + [f"{username}@{ip}", command]
    print(f"[{ip}] Running: {command}")
    return subprocess.run(ssh_cmd, capture_output=True, text=True)


def clean_testbed(config_path: Path, key_path: str) -> None:
    print(f"[*] Loading topology configuration from {config_path}...")
    config = load_config(config_path)
    topology = config.get("topology", {})

    aggregator = topology.get("aggregator", "10.10.130.10")
    def_a = topology.get("defender_a", "10.10.130.11")
    def_b = topology.get("defender_b", "10.10.130.12")
    target_a = topology.get("target_a", "10.10.110.15")
    target_b = topology.get("target_b", "10.10.120.15")
    traffic_gen = topology.get("traffic_gen", "10.10.140.10")

    print("\n=== Cleaning Aggregator Node ===")
    cmds = [
        "systemctl stop mlflow || true",
        "rm -f /root/mlflow.db /root/mlflow.db-shm /root/mlflow.db-wal",
        "rm -rf /opt/mlflow-artifacts/*",
        "systemctl start mlflow",
        "systemctl is-active mlflow || true"
    ]
    for cmd in cmds:
        res = run_ssh(aggregator, cmd, key_path=key_path)
        if res.stdout:
            print(f"  Stdout: {res.stdout.strip()}")
        if res.stderr:
            print(f"  Stderr: {res.stderr.strip()}")

    print("\n=== Cleaning Defender Nodes ===")
    for defender in [def_a, def_b]:
        cmds = [
            "pkill -f 'client.py|extractor.py|flower' || true",
            "rm -rf /mnt/ramdisk/flows/*",
            "df -h /mnt/ramdisk || true"
        ]
        for cmd in cmds:
            res = run_ssh(defender, cmd, key_path=key_path)
            if "df -h" in cmd and res.stdout:
                print(f"  RAM Disk usage:\n{res.stdout.strip()}")

    print("\n=== Cleaning Target Nodes ===")
    for target in [target_a, target_b]:
        cmds = [
            "pkill -9 -f 'simple_httpd.sh|nc' || killall -9 nc || true",
            "rm -f /tmp/httpd.log",
            "ss -tulpn | grep :80 || true"
        ]
        for cmd in cmds:
            res = run_ssh(target, cmd, key_path=key_path)
            if "ss -tulpn" in cmd and res.stdout:
                print(f"  Remaining listeners:\n{res.stdout.strip()}")

    print("\n=== Cleaning Traffic Generator Node ===")
    cmds = [
        "pkill -9 -f 'slowloris|hydra|attack_flow.py' || true",
        "rm -f /root/*.log"
    ]
    for cmd in cmds:
        run_ssh(traffic_gen, cmd, key_path=key_path)

    print("\n[+] Testbed cleanup successfully completed!")


def main():
    parser = argparse.ArgumentParser(description="Clean FL-CL Proxmox VE Testbed Environment")
    parser.add_argument("--config", default="configs/experiment.yaml", help="Path to experiment config YAML")

    default_key = os.path.expanduser("~/.ssh/id_ed25519")
    if not os.path.exists(default_key) and os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
        default_key = os.path.expanduser("~/.ssh/id_rsa")
    default_key = os.environ.get("SSH_KEY_PATH") or default_key

    parser.add_argument("--key", default=default_key, help="Path to private SSH key")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = PROJECT_ROOT / cfg_path

    if not cfg_path.exists():
        print(f"[!] Config file not found: {cfg_path}")
        sys.exit(1)

    clean_testbed(cfg_path, args.key)


if __name__ == "__main__":
    main()
