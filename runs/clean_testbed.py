#!/usr/bin/env python3
"""
clean_testbed.py — Thorough testbed cleanup script.
Wipes MLflow DB/artifacts, and removes leftover flows, logs, and processes on all nodes.
"""
import argparse
import os
import subprocess
import sys
import yaml

def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def run_ssh(ip, command, username="root", key_path=None):
    opts = "-o StrictHostKeyChecking=no -o ConnectTimeout=5"
    if key_path:
        opts += f" -i \"{key_path}\""
    
    ssh_cmd = f"ssh -n {opts} {username}@{ip} \"{command}\""
    print(f"[{ip}] Running: {command}")
    return subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)

def main():
    parser = argparse.ArgumentParser(description="Clean FL-CL Testbed Environment")
    parser.add_argument("--config", default="configs/experiment.yaml", help="Path to experiment config YAML")
    parser.add_argument("--key", default="~/.ssh/id_ed25519", help="Path to private SSH key")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"[!] Config file not found: {args.config}")
        sys.exit(1)

    print(f"[*] Loading topology configuration from {args.config}...")
    config = load_config(args.config)
    topology = config.get("topology", {})

    aggregator = topology.get("aggregator", "10.10.130.10")
    def_a = topology.get("defender_a", "10.10.130.11")
    def_b = topology.get("defender_b", "10.10.130.12")
    target_a = topology.get("target_a", "10.10.110.15")
    target_b = topology.get("target_b", "10.10.120.15")
    traffic_gen = topology.get("traffic_gen", "10.10.140.10")

    print("\n=== Cleaning Aggregator Node ===")
    # Stop mlflow service, delete SQLite database and artifact files, then restart mlflow service
    cmds = [
        "systemctl stop mlflow || true",
        "rm -f /root/mlflow.db /root/mlflow.db-shm /root/mlflow.db-wal",
        "rm -rf /opt/mlflow-artifacts/*",
        "systemctl start mlflow",
        "systemctl is-active mlflow || true"
    ]
    for cmd in cmds:
        res = run_ssh(aggregator, cmd, key_path=args.key)
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
            res = run_ssh(defender, cmd, key_path=args.key)
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
            res = run_ssh(target, cmd, key_path=args.key)
            if "ss -tulpn" in cmd and res.stdout:
                print(f"  Remaining listeners:\n{res.stdout.strip()}")

    print("\n=== Cleaning Traffic Generator Node ===")
    cmds = [
        "pkill -9 -f 'slowloris|hydra|attack_flow.py' || true",
        "rm -f /root/*.log"
    ]
    for cmd in cmds:
        run_ssh(traffic_gen, cmd, key_path=args.key)

    print("\n[+] Testbed cleanup successfully completed!")

if __name__ == "__main__":
    main()
