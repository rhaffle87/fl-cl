"""
orchestrate.py — Master Orchestration Script for FL-CL Testbed

Cocoordinates the end-to-end Federated Continual Learning pipeline:
  1. Synchronizes updated python scripts to remote VMs via SCP.
  2. Sets up target HTTP services.
  3. Launches feature extraction on defender nodes.
  4. Starts Flower server with MLflow logging on the aggregator container.
  5. Launches attack scenarios sequentially from the traffic generator.
  6. Launches Flower clients to train and evaluate, logging everything to MLflow.
  7. Cleans up all background processes gracefully.

Runs on: Local workstation (Windows host) with access to standard 'ssh' and 'scp'.
"""

import argparse
import subprocess
import time
import sys


class RemoteNode:
    def __init__(self, name, ip, username="root", key_path=None):
        self.name = name
        self.ip = ip
        self.username = username
        self.key_path = key_path
        self.procs = []

    def _get_ssh_opts(self):
        opts = "-o StrictHostKeyChecking=no"
        if self.key_path:
            opts += f" -i {self.key_path}"
        return opts

    def run_cmd(self, command, background=False):
        opts = self._get_ssh_opts()
        if background:
            # nohup and double-forking so that the ssh session can close without killing the job
            full_command = f"nohup {command} > /tmp/{self.name}.log 2>&1 &"
            ssh_cmd = f"ssh {opts} {self.username}@{self.ip} \"{full_command}\""
            print(f"[{self.name}] Spawning background: {command}")
            proc = subprocess.Popen(ssh_cmd, shell=True)
            self.procs.append(proc)
            return proc
        else:
            ssh_cmd = f"ssh {opts} {self.username}@{self.ip} \"{command}\""
            print(f"[{self.name}] Running: {command}")
            return subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)

    def scp_file(self, local_path, remote_path):
        opts = self._get_ssh_opts()
        scp_cmd = f"scp {opts} {local_path} {self.username}@{self.ip}:{remote_path}"
        print(f"[{self.name}] Transferring {local_path} -> {remote_path}")
        return subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)

    def cleanup(self):
        opts = self._get_ssh_opts()
        # Gracefully stop processes we launched by checking logs/pids
        # We kill server.py, client.py, extractor.py, attack_flow.py, busybox httpd
        kill_cmd = (
            "pkill -f 'server.py|client.py|extractor.py|attack_flow.py|busybox httpd' "
            "|| true"
        )
        print(f"[{self.name}] Cleaning up background processes...")
        subprocess.run(f"ssh {opts} {self.username}@{self.ip} \"{kill_cmd}\"", shell=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="FL-CL Testbed Orchestrator")
    parser.add_argument("--key", default=None, help="Path to SSH private key")
    parser.add_argument("--rounds", type=int, default=10, help="FL rounds")
    parser.add_argument("--lambda-ewc", type=float, default=0.4, help="EWC lambda")
    parser.add_argument("--duration", type=int, default=30, help="Attack stage duration (seconds)")
    args = parser.parse_args()

    # Define all remote nodes matching the flat L2 subnet schema
    aggregator = RemoteNode("fl-aggregator", "10.10.130.10", "root", args.key)
    def_a = RemoteNode("defender-a", "10.10.130.11", "root", args.key)
    def_b = RemoteNode("defender-b", "10.10.130.12", "root", args.key)
    target_a = RemoteNode("target-a1", "10.10.110.15", "root", args.key)
    target_b = RemoteNode("target-b1", "10.10.120.15", "root", args.key)
    traffic_gen = RemoteNode("traffic-gen", "10.10.140.10", "root", args.key)

    nodes = [aggregator, def_a, def_b, target_a, target_b, traffic_gen]

    print("\n=== Phase 1: Cleaning up any old testbed processes ===")
    for node in nodes:
        node.cleanup()

    print("\n=== Phase 2: Synchronizing source code to remote nodes ===")
    # Aggregator files (src/aggregator/ → LXC 300)
    aggregator.scp_file("src/aggregator/server.py", "~/server.py")
    aggregator.scp_file("src/aggregator/model.py", "~/model.py")

    # Defender A files (src/defender/ → VM 310)
    def_a.scp_file("src/defender/client.py", "~/client.py")
    def_a.scp_file("src/defender/cl_strategy.py", "~/cl_strategy.py")
    def_a.scp_file("src/defender/model.py", "~/model.py")
    def_a.scp_file("src/defender/extractor.py", "~/extractor.py")

    # Defender B files (src/defender/ → VM 320)
    def_b.scp_file("src/defender/client.py", "~/client.py")
    def_b.scp_file("src/defender/cl_strategy.py", "~/cl_strategy.py")
    def_b.scp_file("src/defender/model.py", "~/model.py")
    def_b.scp_file("src/defender/extractor.py", "~/extractor.py")

    # Traffic Generator files (src/traffic_gen/ → VM 400)
    traffic_gen.scp_file("src/traffic_gen/attack_flow.py", "~/attack_flow.py")

    print("\n=== Phase 3: Launching Benign Target Servers (busybox httpd) ===")
    # Target HTTP servers
    target_a.run_cmd("mkdir -p /tmp/www && echo 'Target A1 Benign Server' > /tmp/www/index.html")
    target_a.run_cmd("busybox httpd -p 80 -h /tmp/www")
    target_b.run_cmd("mkdir -p /tmp/www && echo 'Target B1 Benign Server' > /tmp/www/index.html")
    target_b.run_cmd("busybox httpd -p 80 -h /tmp/www")

    print("\n=== Phase 4: Launching NFStream Traffic Extractors ===")
    # Start extractor on Defender A & B capturing on ens19, outputting to ramdisk
    def_a.run_cmd("~/fl-cl-env/bin/python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/ --batch-size 100", background=True)
    def_b.run_cmd("~/fl-cl-env/bin/python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/ --batch-size 100", background=True)

    print("\n=== Phase 5: Launching MLflow & Flower Server ===")
    # Start MLflow tracker inside flower env
    aggregator.run_cmd("mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db", background=True)
    time.sleep(3) # Wait for MLflow to initialize
    # Start FL server
    server_proc = aggregator.run_cmd(
        f"python3 server.py --rounds {args.rounds} --min-clients 2 --mlflow-uri http://localhost:5000",
        background=True
    )

    print("\n=== Phase 6: Starting Threat Simulation Stages ===")
    # 1. Benign background traffic to Target A and B
    traffic_gen.run_cmd(f"python3 attack_flow.py --mode benign --target 10.10.110.15 --duration {args.duration}", background=True)
    traffic_gen.run_cmd(f"python3 attack_flow.py --mode benign --target 10.10.120.15 --duration {args.duration}", background=True)
    time.sleep(args.duration // 2)

    # 2. SSH Brute Force attacks targeting Target A and B
    traffic_gen.run_cmd(f"python3 attack_flow.py --mode ssh --target 10.10.110.15 --duration {args.duration}", background=True)
    traffic_gen.run_cmd(f"python3 attack_flow.py --mode ssh --target 10.10.120.15 --duration {args.duration}", background=True)
    time.sleep(args.duration // 2)

    # 3. Slowloris HTTPS Flooding targeting Target A and B
    traffic_gen.run_cmd(f"python3 attack_flow.py --mode slowloris --target 10.10.110.15 --duration {args.duration} --port 80", background=True)
    traffic_gen.run_cmd(f"python3 attack_flow.py --mode slowloris --target 10.10.120.15 --duration {args.duration} --port 80", background=True)
    time.sleep(args.duration)

    print("\n=== Phase 7: Launching Flower Clients on Defender Nodes ===")
    def_a.run_cmd(f"~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id A --ewc-lambda {args.lambda_ewc}", background=True)
    def_b.run_cmd(f"~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id B --ewc-lambda {args.lambda_ewc}", background=True)

    print("\n=== Phase 8: Monitoring Training Loop Convergence ===")
    print("[*] Waiting for Flower server rounds to complete. Press Ctrl+C to terminate early and clean up.")
    try:
        # Poll the server process or wait for a fixed duration to complete training rounds
        # Each round takes a few seconds to process, let's wait/poll
        start_wait = time.time()
        # We can poll every 5 seconds. If the training takes too long, we will timeout after 10 minutes.
        while time.time() - start_wait < 600:
            # Check if server process has exited (if running locally or remotely, we check via pgrep on aggregator)
            status = aggregator.run_cmd("pgrep -f 'server.py'")
            if not status.stdout.strip():
                print("[✓] Flower server has completed its rounds.")
                break
            time.sleep(5)
            sys.stdout.write(".")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n[!] User interrupted the execution. Starting cleanup.")

    print("\n=== Phase 9: Cleaning up remote background processes ===")
    for node in nodes:
        node.cleanup()

    print("\n[✓] Orchestration workflow finished successfully!")
    print("Check MLflow dashboard at http://10.10.130.10:5000 to verify continual learning metrics.")


if __name__ == "__main__":
    main()
