#!/usr/bin/env python3
"""
setup_ssh_targets.py — Sets up a test user "admin" on targets with a challenging password
selected dynamically from the traffic generator's Hydra wordlist.
"""
import argparse
import json
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
    return subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)

def main():
    parser = argparse.ArgumentParser(description="Configure Target SSH Credentials for Hydra Testing")
    parser.add_argument("--config", default="configs/experiment.yaml", help="Path to experiment config YAML")
    # Dynamic cross-platform fallback for default SSH key
    default_key = os.path.expanduser("~/.ssh/id_ed25519")
    if not os.path.exists(default_key) and os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
        default_key = os.path.expanduser("~/.ssh/id_rsa")
    default_key = os.environ.get("SSH_KEY_PATH") or default_key

    parser.add_argument("--key", default=default_key, help="Path to private SSH key")
    parser.add_argument("--password-index", type=int, default=45, help="Index of password in fasttrack.txt (0-indexed)")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"[!] Config file not found: {args.config}")
        sys.exit(1)

    print(f"[*] Loading config from {args.config}...")
    config = load_config(args.config)
    topology = config.get("topology", {})

    traffic_gen = topology.get("traffic_gen", "10.10.140.10")
    target_a = topology.get("target_a", "10.10.110.15")
    target_b = topology.get("target_b", "10.10.120.15")

    selected_password = "spring2014" # Default fallback password (present in fasttrack.txt)

    # 1. Fetch password from traffic generator wordlist
    print(f"[*] Attempting to read wordlist from traffic generator ({traffic_gen})...")
    wordlist_path = "/usr/share/wordlists/fasttrack.txt"
    cmd_read = f"head -n 100 {wordlist_path} || true"
    res = run_ssh(traffic_gen, cmd_read, key_path=args.key)
    
    if res.stdout and len(res.stdout.strip()) > 0:
        words = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        if len(words) > args.password_index:
            selected_password = words[args.password_index]
            print(f"[+] Successfully loaded password index {args.password_index} from traffic generator: '{selected_password}'")
        else:
            print(f"[!] Wordlist read succeeded, but index {args.password_index} out of range (total words: {len(words)}). Using fallback.")
    else:
        print(f"[!] Could not read wordlist from traffic generator VM (path: {wordlist_path}). Sticking with default fallback: '{selected_password}'")

    print(f"\n[*] Selected Target password: '{selected_password}'")

    # 2. Configure admin user on target_a and target_b
    for target_name, target_ip in [("target-a", target_a), ("target-b", target_b)]:
        print(f"\n=== Configuring {target_name} ({target_ip}) ===")
        
        # Bash commands to:
        # - Create user 'admin' if not exists
        # - Set admin password
        # - Force SSH configuration to support PasswordAuthentication
        # - Restart SSH service
        setup_cmds = (
            f"(id -u admin &>/dev/null || adduser -D -s /bin/sh admin || useradd -m -s /bin/bash admin) && "
            f"echo 'admin:{selected_password}' | chpasswd && "
            f"sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config && "
            f"(/etc/init.d/sshd restart || rc-service sshd restart || systemctl restart sshd || systemctl restart ssh || service ssh restart) && "
            f"echo 'SUCCESS'"
        )
        
        res = run_ssh(target_ip, setup_cmds, key_path=args.key)
        if "SUCCESS" in res.stdout:
            print(f"[+] Successfully created/configured admin user on {target_name} ({target_ip})")
        else:
            print(f"[!] Configuration failed or returned unexpected output on {target_name}:\n{res.stderr}\n{res.stdout}")

    # 3. Save target credentials locally for reference
    credentials = {
        "username": "admin",
        "password": selected_password,
        "targets": [target_a, target_b]
    }
    
    cred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_credentials.json")
    with open(cred_file, "w") as f:
        json.dump(credentials, f, indent=4)
        
    print(f"\n[+] Credentials saved locally for reference: runs/target_credentials.json")

if __name__ == "__main__":
    main()
