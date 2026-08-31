"""
tools/deploy_setup_targets.py — Target VM SSH Credential Configuration Utility

Configures the 'admin' benchmark user on Target VMs (10.10.110.15, 10.10.120.15)
with password credentials selected from the Hydra wordlist on the traffic generator VM.

Usage:
    python tools/deploy_setup_targets.py --config configs/experiment.yaml
"""

import argparse
import json
import os
from pathlib import Path
import shlex
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
    return subprocess.run(ssh_cmd, capture_output=True, text=True)


def setup_targets(config_path: Path, key_path: str, password_index: int) -> None:
    print(f"[*] Loading config from {config_path}...")
    config = load_config(config_path)
    topology = config.get("topology", {})

    traffic_gen = topology.get("traffic_gen", os.environ.get("TRAFFIC_GEN_HOST", "10.10.140.10"))
    target_a = topology.get("target_a", os.environ.get("TARGET_A_HOST", "10.10.110.15"))
    target_b = topology.get("target_b", os.environ.get("TARGET_B_HOST", "10.10.120.15"))

    selected_password = "spring2014"

    # 1. Fetch password from traffic generator wordlist
    print(f"[*] Attempting to read wordlist from traffic generator ({traffic_gen})...")
    wordlist_path = "/usr/share/wordlists/fasttrack.txt"
    cmd_read = f"head -n 100 {wordlist_path} || true"
    res = run_ssh(traffic_gen, cmd_read, key_path=key_path)

    if res.stdout and len(res.stdout.strip()) > 0:
        words = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        if len(words) > password_index:
            selected_password = words[password_index]
            print(f"[+] Loaded password index {password_index} from traffic generator: '{selected_password}'")
        else:
            print(f"[!] Password index {password_index} out of range ({len(words)} words). Using fallback.")
    else:
        print(f"[!] Could not read wordlist from {traffic_gen}. Using fallback: '{selected_password}'")

    print(f"\n[*] Selected Target password: '{selected_password}'")

    # 2. Configure admin user on target_a and target_b
    for target_name, target_ip in [("target-a", target_a), ("target-b", target_b)]:
        print(f"\n=== Configuring {target_name} ({target_ip}) ===")
        escaped_admin_pw = shlex.quote(f"admin:{selected_password}")
        setup_cmds = (
            f"(id -u admin &>/dev/null || adduser -D -s /bin/sh admin || useradd -m -s /bin/bash admin) && "
            f"echo {escaped_admin_pw} | chpasswd && "
            f"sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config && "
            f"(/etc/init.d/sshd restart || rc-service sshd restart || systemctl restart sshd || systemctl restart ssh || service ssh restart) && "
            f"echo 'SUCCESS'"
        )

        res = run_ssh(target_ip, setup_cmds, key_path=key_path)
        if "SUCCESS" in res.stdout:
            print(f"[+] Successfully configured admin user on {target_name} ({target_ip})")
        else:
            print(f"[!] Configuration output on {target_name}:\n{res.stderr}\n{res.stdout}")

    # 3. Save target credentials locally for reference
    credentials = {
        "username": "admin",
        "password": selected_password,
        "targets": [target_a, target_b]
    }

    cred_file = PROJECT_ROOT / "data" / "target_credentials.json"
    cred_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cred_file, "w", encoding="utf-8") as f:
        json.dump(credentials, f, indent=4)

    print(f"\n[+] Credentials saved: data/target_credentials.json")


def main():
    parser = argparse.ArgumentParser(description="Configure Target SSH Credentials for Hydra Testing")
    parser.add_argument("--config", default="configs/experiment.yaml", help="Path to experiment config YAML")

    default_key = os.path.expanduser("~/.ssh/id_ed25519")
    if not os.path.exists(default_key) and os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
        default_key = os.path.expanduser("~/.ssh/id_rsa")
    default_key = os.environ.get("SSH_KEY_PATH") or default_key

    parser.add_argument("--key", default=default_key, help="Path to private SSH key")
    parser.add_argument("--password-index", type=int, default=45, help="Index of password in fasttrack.txt")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = PROJECT_ROOT / cfg_path

    if not cfg_path.exists():
        print(f"[!] Config file not found: {cfg_path}")
        sys.exit(1)

    setup_targets(cfg_path, args.key, args.password_index)


if __name__ == "__main__":
    main()
