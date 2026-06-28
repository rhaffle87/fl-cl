"""
orchestrate.py — Master Orchestration Script for FL-CL Testbed

Coordinates the end-to-end Federated Continual Learning pipeline:
  1. Loads experiment config from YAML for reproducibility.
  2. Sends Telegram notification on start.
  3. Synchronizes updated python scripts to remote VMs via SCP.
  4. Sets up target HTTP services.
  5. Launches feature extraction on defender nodes.
  6. Starts Flower server with MLflow logging on the aggregator container.
  7. Launches attack scenarios sequentially from the traffic generator.
  8. Runs data quality gate — verifies all classes are present.
  9. Launches Flower clients to train and evaluate.
  10. Sends Telegram notification on completion or failure.
  11. Cleans up all background processes gracefully.

Runs on: Local workstation (Windows host) with access to standard 'ssh' and 'scp'.
"""

import argparse
import subprocess
import time
import sys
import os

def load_env(env_path: str = ".env"):
    """Load environment variables from a .env file if it exists."""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val

# Load local environment variables
load_env()

# Add src/ to path for notifications import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notifications import TelegramNotifier


# ─── Config Loading ─────────────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    """Load experiment configuration from YAML file."""
    try:
        import yaml
    except ImportError:
        # Fallback: basic YAML parsing for simple configs
        print("[!] PyYAML not installed locally. Using default config values.")
        return {}

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_config_value(config: dict, *keys, default=None):
    """Safely traverse nested config dict."""
    current = config
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current if current is not None else default


# ─── Remote Node ─────────────────────────────────────────────────────────────

class RemoteNode:
    def __init__(self, name, ip, username="root", key_path=None):
        self.name = name
        self.ip = ip
        self.username = username
        self.key_path = key_path
        self.procs = []

    def _get_ssh_opts(self):
        opts = ["-o", "StrictHostKeyChecking=no"]
        if self.key_path:
            opts += ["-i", self.key_path]
        return opts

    def run_cmd(self, command, background=False, log_name=None):
        opts = self._get_ssh_opts()
        if background:
            if not log_name:
                if "server.py" in command:
                    log_name = "flower-server.log"
                elif "mlflow" in command:
                    log_name = "mlflow.log"
                elif "client.py" in command:
                    log_name = "flower-client.log"
                elif "extractor.py" in command:
                    log_name = "extractor.log"
                elif "attack_flow.py" in command:
                    log_name = "attack_flow.log"
                else:
                    log_name = f"{self.name}.log"
            full_command = f"nohup {command} > /tmp/{log_name} 2>&1 &"
            ssh_cmd = ["ssh", "-n"] + opts + [f"{self.username}@{self.ip}", full_command]
            print(f"[{self.name}] Spawning background (logs -> /tmp/{log_name}): {command}")
            proc = subprocess.Popen(ssh_cmd)
            self.procs.append(proc)
            return proc
        else:
            ssh_cmd = ["ssh", "-n"] + opts + [f"{self.username}@{self.ip}", command]
            print(f"[{self.name}] Running: {command}")
            return subprocess.run(ssh_cmd, capture_output=True, text=True)

    def scp_file(self, local_path, remote_path):
        opts = self._get_ssh_opts()
        scp_cmd = ["scp"] + opts + [local_path, f"{self.username}@{self.ip}:{remote_path}"]
        print(f"[{self.name}] Transferring {local_path} -> {remote_path}")
        return subprocess.run(scp_cmd, capture_output=True, text=True)

    def cleanup(self, kill_mlflow=False):
        opts = self._get_ssh_opts()
        pattern = "server.py|client.py|extractor.py|attack_flow.py|busybox httpd|normal_traffic_loop|curl|simple_httpd.sh|nc"
        if kill_mlflow:
            pattern += "|mlflow"
        kill_cmd = f"pkill -f '{pattern}' || killall -9 nc || true"
        print(f"[{self.name}] Cleaning up background processes...")
        ssh_cmd = ["ssh", "-n"] + opts + [f"{self.username}@{self.ip}", kill_cmd]
        subprocess.run(ssh_cmd, capture_output=True)



def run_data_quality_check(defender_node: RemoteNode, dos_threshold: float = 2000) -> dict:
    """Check label distribution on a defender's ramdisk. Returns {label: count}."""
    result = defender_node.run_cmd(f"~/fl-cl-env/bin/python3 ~/check_dataset.py --json --dos-threshold-ms {dos_threshold}")
    try:
        import json
        output = result.stdout.strip()
        if not output:
            if result.stderr:
                print(f"[{defender_node.name}] Command stderr:\n{result.stderr}")
            return {}
        # Parse the JSON string
        raw_counts = json.loads(output)
        # Convert keys to integers
        return {int(k): int(v) for k, v in raw_counts.items()}
    except Exception as e:
        print(f"[{defender_node.name}] Failed to parse output: {e}")
        print(f"[{defender_node.name}] stdout: {result.stdout}")
        print(f"[{defender_node.name}] stderr: {result.stderr}")
        return {}


def run_post_training_plots_and_report(key_path, aggregator_ip, experiment_name, rounds, lambda_ewc):
    """Dynamically imports and executes the metrics plotter, generating a run summary report."""
    print("\n=== Phase 8b: Generating Post-Training Plots and Reports ===")
    try:
        import sys
        import os
        import time

        # Add tools/ directory to system path
        tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)

        from plot_metrics import run_plotting

        # Create a unique directory for this specific run in exports/
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        clean_name = experiment_name.replace(" ", "_").replace(":", "_").replace("/", "_")
        run_dir_name = f"{clean_name}_{timestamp}"
        
        exports_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports"))
        run_dir = os.path.join(exports_base_dir, run_dir_name)
        plots_dir = os.path.join(run_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        print(f"[*] Exporting results to folder: {run_dir}")
        print("[*] Retrieving metrics and plotting convergence graphs...")
        results = run_plotting(
            key_path=key_path,
            aggregator_ip=aggregator_ip,
            local_db="mlflow_temp.db",
            output_dir=plots_dir
        )

        run_id = results.get("run_id")
        final_metrics = results.get("final_metrics", {})
        exported_plots = results.get("exported_plots", {})

        # Generate Markdown Summary Report inside the specific run directory
        summary_path = os.path.join(run_dir, "run_summary.md")
        print(f"[*] Writing training run summary report to {summary_path}...")

        with open(summary_path, "w") as f:
            f.write(f"# FL-CL Experiment Run Summary: {experiment_name}\n\n")
            f.write(f"- **MLflow Run ID**: `{run_id}`\n")
            f.write(f"- **Total FL Rounds**: `{rounds}`\n")
            f.write(f"- **Continual Learning (EWC) Lambda**: `{lambda_ewc}`\n")
            f.write(f"- **Generated At**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Final Metrics Summary\n")
            f.write("| Metric | Value |\n")
            f.write("|:---|:---|\n")
            for key, val in sorted(final_metrics.items()):
                if key != "Round":
                    try:
                        f.write(f"| {key} | {float(val):.6f} |\n")
                    except (ValueError, TypeError):
                        f.write(f"| {key} | {val} |\n")
            f.write("\n")

            f.write("## Convergence Plots per Traffic Class\n")
            f.write("Click on each class below to view its convergence plot (incorporating Loss, Global Accuracy, and Class Accuracy):\n\n")
            for display_name, plot_file in sorted(exported_plots.items()):
                f.write(f"### {display_name} Convergence Plot\n")
                f.write(f"![{display_name} Accuracy Plot](plots/{plot_file})\n\n")

        print(f"[OK] Visual report generated successfully at {summary_path}")

    except ImportError as ie:
        print(f"[!] Warning: Could not run automated plotting because dependencies are missing: {ie}")
    except Exception as e:
        print(f"[!] Warning: Automated plotting failed: {e}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FL-CL Testbed Orchestrator")
    parser.add_argument("--key", default=None, help="Path to SSH private key")
    parser.add_argument("--rounds", type=int, default=None, help="FL rounds (overrides config)")
    parser.add_argument("--lambda-ewc", type=float, default=None, help="EWC lambda (overrides config)")
    parser.add_argument("--duration", type=int, default=None, help="Attack stage duration in seconds (overrides config)")
    parser.add_argument("--config", default="configs/experiment.yaml", help="Experiment config file")
    parser.add_argument("--mlops-mode", default=None, choices=["experimental", "production"], help="MLOps mode (experimental or production)")
    parser.add_argument("--production-strategy", default=None, choices=["resume", "fresh"], help="Production strategy (resume or fresh)")
    args = parser.parse_args()

    # Load config — CLI args override YAML values
    config = {}
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", args.config)
    if os.path.exists(config_path):
        config = load_config(config_path)
        print(f"[*] Loaded config: {config_path}")
    elif os.path.exists(args.config):
        config = load_config(args.config)
        config_path = args.config
        print(f"[*] Loaded config: {args.config}")
    else:
        print(f"[!] Config not found at {args.config}. Using CLI defaults.")
        config_path = None

    rounds = args.rounds or get_config_value(config, "fl", "rounds", default=10)
    lambda_ewc = args.lambda_ewc or get_config_value(config, "cl", "ewc_lambda", default=0.4)
    duration = args.duration or get_config_value(config, "simulation", "attack_duration_seconds", default=30)
    class_weights = get_config_value(config, "training", "class_weights", default=[12.0, 3.0, 3.0, 15.0, 1.0])
    weights_str = ",".join(map(str, class_weights))
    lr = get_config_value(config, "training", "lr", default=0.01)
    momentum = get_config_value(config, "training", "momentum", default=0.9)
    experiment_name = get_config_value(config, "experiment", "name", default="FL-CL-Run")
    dos_threshold = get_config_value(config, "labeling", "dos_duration_threshold_ms", default=2000)
    mlops_mode = args.mlops_mode or get_config_value(config, "mlops", "mode", default="experimental")
    production_strategy = args.production_strategy or get_config_value(config, "mlops", "production_strategy", default="resume")

    # Set up Telegram notifications (prioritize environment variables for security)
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN") or get_config_value(config, "notifications", "telegram", "bot_token", default="")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID") or get_config_value(config, "notifications", "telegram", "chat_id", default="")
    tg_enabled = get_config_value(config, "notifications", "telegram", "enabled", default=False)
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        tg_enabled = True
    notifier = TelegramNotifier(bot_token=tg_token, chat_id=tg_chat_id, enabled=tg_enabled)

    # Determine the key path to use for remote node communication
    default_key = os.path.expanduser("~/.ssh/id_ed25519")
    if not os.path.exists(default_key) and os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
        default_key = os.path.expanduser("~/.ssh/id_rsa")
    key_path = args.key or os.environ.get("SSH_KEY_PATH") or default_key

    # Define all remote nodes
    aggregator = RemoteNode("fl-aggregator",
                            get_config_value(config, "topology", "aggregator", default="10.10.130.10"),
                            "root", key_path)
    def_a = RemoteNode("defender-a",
                       get_config_value(config, "topology", "defender_a", default="10.10.130.11"),
                       "root", key_path)
    def_b = RemoteNode("defender-b",
                       get_config_value(config, "topology", "defender_b", default="10.10.130.12"),
                       "root", key_path)
    target_a = RemoteNode("target-a1",
                          get_config_value(config, "topology", "target_a", default="10.10.110.15"),
                          "root", key_path)
    target_b = RemoteNode("target-b1",
                          get_config_value(config, "topology", "target_b", default="10.10.120.15"),
                          "root", key_path)
    traffic_gen = RemoteNode("traffic-gen",
                             get_config_value(config, "topology", "traffic_gen", default="10.10.140.10"),
                             "root", key_path)

    nodes = [aggregator, def_a, def_b, target_a, target_b, traffic_gen]

    print(f"\n{'='*60}")
    print(f"  FL-CL Orchestrator - {experiment_name}")
    print(f"  Rounds: {rounds} | EWC lambda: {lambda_ewc} | Duration: {duration}s")
    print(f"{'='*60}\n")

    start_time = time.time()

    # Retrieve git commit hash for notification and tagging
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
    except Exception:
        pass

    # Notify start
    notifier.notify_start(
        experiment_name=experiment_name,
        rounds=rounds,
        config_summary=f"EWC lambda={lambda_ewc}, Duration={duration}s",
        mlops_mode=mlops_mode,
        git_commit=git_commit
    )

    print("=== Phase 1: Cleaning up any old testbed processes ===")
    for node in nodes:
        if node.name == "fl-aggregator":
            res = node.run_cmd("systemctl is-active --quiet mlflow")
            if res.returncode == 0:
                print("[fl-aggregator] MLflow systemd service is active. Skipping MLflow process cleanup.")
                node.cleanup(kill_mlflow=False)
            else:
                node.cleanup(kill_mlflow=True)
        else:
            node.cleanup(kill_mlflow=True)
            if node.name in ["defender-a", "defender-b"]:
                print(f"[{node.name}] Cleaning up ramdisk flows directory...")
                node.run_cmd("rm -rf /mnt/ramdisk/flows/* || true")

    try:
        print("\n=== Phase 2: Synchronizing source code to remote nodes ===")
        # Aggregator files — model.py comes from defender/ (single source of truth)
        aggregator.scp_file("src/aggregator/server.py", "~/server.py")
        aggregator.scp_file("src/defender/model.py", "~/model.py")

        # Send experiment config to aggregator for MLflow artifact logging
        if config_path and os.path.exists(config_path):
            aggregator.scp_file(config_path, "~/experiment.yaml")

        # Defender A files
        def_a.scp_file("src/defender/client.py", "~/client.py")
        def_a.scp_file("src/defender/cl_strategy.py", "~/cl_strategy.py")
        def_a.scp_file("src/defender/model.py", "~/model.py")
        def_a.scp_file("src/defender/extractor.py", "~/extractor.py")
        def_a.scp_file("tools/check_dataset.py", "~/check_dataset.py")

        # Defender B files
        def_b.scp_file("src/defender/client.py", "~/client.py")
        def_b.scp_file("src/defender/cl_strategy.py", "~/cl_strategy.py")
        def_b.scp_file("src/defender/model.py", "~/model.py")
        def_b.scp_file("src/defender/extractor.py", "~/extractor.py")
        def_b.scp_file("tools/check_dataset.py", "~/check_dataset.py")

        # Traffic Generator files
        traffic_gen.scp_file("src/traffic_gen/attack_flow.py", "~/attack_flow.py")

        # Target files
        target_a.scp_file("src/traffic_gen/simple_httpd.sh", "/tmp/simple_httpd.sh")
        target_b.scp_file("src/traffic_gen/simple_httpd.sh", "/tmp/simple_httpd.sh")

        print("\n=== Phase 3: Launching Benign Target Servers (simple_httpd.sh) ===")
        target_a.run_cmd("chmod +x /tmp/simple_httpd.sh && nohup /tmp/simple_httpd.sh >/dev/null 2>&1 &", background=True)
        target_b.run_cmd("chmod +x /tmp/simple_httpd.sh && nohup /tmp/simple_httpd.sh >/dev/null 2>&1 &", background=True)

        print("\n=== Phase 3b: Generating Normal Traffic from Defender Nodes ===")
        # Defender IPs (10.10.130.11/12) are NOT the traffic_gen IP (10.10.140.10),
        # so assign_label() classifies these flows as class 0 (Normal).
        # Use background=True (nohup mode) so the loop fully detaches without blocking orchestration.
        target_a_ip = get_config_value(config, "topology", "target_a", default="10.10.110.15")
        target_b_ip = get_config_value(config, "topology", "target_b", default="10.10.120.15")
        print(f"[*] Spawning Normal traffic from defender nodes (curl -> {target_a_ip}, {target_b_ip})...")
        def_a.run_cmd(
            f"bash -c 'while true; do normal_traffic_loop=1; curl -s -o /dev/null http://{target_a_ip}/ http://{target_b_ip}/ --max-time 3 --connect-timeout 2; sleep 0.5; done'",
            background=True,
            log_name="normal-traffic-a.log"
        )
        def_b.run_cmd(
            f"bash -c 'while true; do normal_traffic_loop=1; curl -s -o /dev/null http://{target_a_ip}/ http://{target_b_ip}/ --max-time 3 --connect-timeout 2; sleep 0.5; done'",
            background=True,
            log_name="normal-traffic-b.log"
        )

        print("\n=== Phase 4: Launching NFStream Traffic Extractors ===")
        def_a.run_cmd("~/fl-cl-env/bin/python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/ --batch-size 500", background=True)
        def_b.run_cmd("~/fl-cl-env/bin/python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/ --batch-size 500", background=True)

        print("\n=== Phase 5: Launching MLflow & Flower Server ===")
        # Check if mlflow systemd service is active
        res = aggregator.run_cmd("systemctl is-active --quiet mlflow")
        if res.returncode == 0:
            print("[fl-aggregator] MLflow is already running persistently as a systemd service.")
        else:
            print("[fl-aggregator] MLflow systemd service not active. Launching ad-hoc background process...")
            aggregator.run_cmd("/opt/flower-env/bin/mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db --allowed-hosts '*' --cors-allowed-origins '*' --x-frame-options NONE --disable-security-middleware", background=True)
            time.sleep(3)

        # Start FL server with config artifact logging
        config_arg = "--config-file ~/experiment.yaml" if config_path else ""
        server_proc = aggregator.run_cmd(
            f"/opt/flower-env/bin/python3 server.py --rounds {rounds} --min-clients 2 --mlflow-uri http://localhost:5000 {config_arg} --mlops-mode {mlops_mode} --production-strategy {production_strategy} --git-commit {git_commit}",
            background=True
        )

        print("\n=== Phase 6: Starting Threat Simulation Stages ===")
        # target_a_ip and target_b_ip already defined in Phase 3b above

        # 1. Benign background traffic from traffic-gen (labeled DoS/port-80 by assign_label)
        #    Real Normal flows come from defender nodes in Phase 3b above.
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode benign --target {target_a_ip} --duration {duration}", background=True)
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode benign --target {target_b_ip} --duration {duration}", background=True)
        time.sleep(duration // 3)  # Shorter wait — we rely on defender curl for Normal class

        # 2. SSH Brute Force — extended wait to generate more SSH-BF (class 3) samples
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode ssh --target {target_a_ip} --duration {duration}", background=True)
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode ssh --target {target_b_ip} --duration {duration}", background=True)
        time.sleep(duration)  # Full duration wait for SSH to generate more flows

        # 3. Slowloris DoS — extended wait to generate more DoS (class 4) samples
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode slowloris --target {target_a_ip} --duration {duration} --port 80", background=True)
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode slowloris --target {target_b_ip} --duration {duration} --port 80", background=True)
        time.sleep(duration)  # Full duration wait for DoS flows to accumulate

        # 4. DNS Exfiltration — shortened wait to avoid over-dominating dataset
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode dns_exfil --target {target_a_ip} --duration {duration}", background=True)
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode dns_exfil --target {target_b_ip} --duration {duration}", background=True)
        time.sleep(duration // 3)  # Shorter wait — Exfil over-represented in data

        # 5. C2 Botnet Beaconing
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode botnet --target {target_a_ip} --duration {duration}", background=True)
        traffic_gen.run_cmd(f"~/traffic-env/bin/python3 attack_flow.py --mode botnet --target {target_b_ip} --duration {duration}", background=True)
        time.sleep(duration)

        print("\n=== Phase 6b: Waiting for flow data to accumulate on ramdisk ===")
        print("[*] Polling defender-a ramdisk until at least one CSV appears (timeout: 120s)...")
        ramdisk_ready = False
        for _ in range(24):
            check = def_a.run_cmd("ls /mnt/ramdisk/flows/*.csv 2>/dev/null | wc -l")
            count = check.stdout.strip()
            if count and int(count) > 0:
                print(f"[OK] Ramdisk ready - {count} CSV file(s) found on defender-a. Proceeding.")
                ramdisk_ready = True
                break
            print("[~] No flow CSVs yet. Waiting 5s...")
            time.sleep(5)
        if not ramdisk_ready:
            print("[!] WARNING: Ramdisk still empty after 120s. Clients will train on empty data this round.")

        print("\n=== Phase 6c: Data Quality Gate ===")
        for node_name, node in [("defender-a", def_a), ("defender-b", def_b)]:
            label_counts = run_data_quality_check(node, dos_threshold=dos_threshold)
            if label_counts:
                label_names = {0: "Normal", 1: "Botnet", 2: "Exfil", 3: "SSH-BF", 4: "DoS"}
                total = sum(label_counts.values())
                print(f"[{node_name}] Flow distribution ({total} total):")
                for label in range(5):
                    count = label_counts.get(label, 0)
                    name = label_names.get(label, "?")
                    print(f"  Class {label} ({name:>7s}): {count}")
                missing = [label_names[i] for i in range(5) if label_counts.get(i, 0) == 0]
                if missing:
                    print(f"[{node_name}] [!] WARNING: Missing classes: {', '.join(missing)}")
            else:
                print(f"[{node_name}] [!] WARNING: Could not read label distribution")

        print("\n=== Phase 7: Launching Flower Clients on Defender Nodes ===")
        def_a.run_cmd(f"~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id A --ewc-lambda {lambda_ewc} --class-weights {weights_str} --lr {lr} --momentum {momentum} --dos-threshold-ms {dos_threshold}", background=True)
        def_b.run_cmd(f"~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id B --ewc-lambda {lambda_ewc} --class-weights {weights_str} --lr {lr} --momentum {momentum} --dos-threshold-ms {dos_threshold}", background=True)

        stopped_early = False
        print("\n=== Phase 8: Monitoring Training Loop Convergence ===")
        print("[*] Waiting for Flower server rounds to complete. Press Ctrl+C to terminate gracefully early.")
        start_wait = time.time()
        timeout = max(600, rounds * 25)
        print(f"[*] Monitoring loop active. Max timeout set to {timeout}s ({timeout/60:.1f} minutes).")
        try:
            while time.time() - start_wait < timeout:
                status = aggregator.run_cmd("pgrep -f '[s]erver.py'")
                if not status.stdout.strip():
                    print("[OK] Flower server has completed its rounds.")
                    break
                time.sleep(5)
                sys.stdout.write(".")
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\n[!] Ctrl+C detected. Gracefully stopping training early...")
            stopped_early = True
            # Terminate clients first so they stop attempting to communicate
            print("[*] Stopping Flower clients...")
            for client_node in [def_a, def_b]:
                client_node.run_cmd("pkill -f 'client.py'")
            # Terminate server.py with SIGTERM to trigger its SystemExit cleanup logic
            print("[*] Stopping Flower server...")
            aggregator.run_cmd("pkill -f 'server.py'")
            print("[*] Waiting 5 seconds for server to finalize metrics and checkpoints...")
            time.sleep(5)

        elapsed_min = (time.time() - start_time) / 60.0

        # Fetch metrics summary from aggregator
        accuracy = 0.0
        loss = 0.0
        class_accuracies = {}
        run_id = None
        experiment_id = None
        
        # Wait a moment for server.py to write the metrics file
        time.sleep(2)
        metrics_res = aggregator.run_cmd("cat /tmp/flower-server-metrics.json 2>/dev/null")
        if metrics_res.stdout.strip():
            try:
                import json
                metrics_data = json.loads(metrics_res.stdout.strip())
                accuracy = float(metrics_data.get("accuracy", 0.0))
                loss = float(metrics_data.get("loss", 0.0))
                raw_classes = metrics_data.get("class_accuracies", {})
                class_accuracies = {int(k): float(v) for k, v in raw_classes.items()}
                run_id = metrics_data.get("run_id")
                experiment_id = metrics_data.get("experiment_id")
                print(f"\n[aggregator] Training summary fetched successfully:")
                print(f"  Final Accuracy: {accuracy*100:.2f}% | Final Loss: {loss:.4f}")
                print(f"  Best Loss: {metrics_data.get('best_loss', 0.0):.4f} at round {metrics_data.get('best_round', 0)}")
            except Exception as e:
                print(f"\n[!] Failed to parse training metrics JSON: {e}")

        # Notify completion
        exp_name_modified = f"{experiment_name} (Stopped Early)" if stopped_early else experiment_name
        notifier.notify_complete(
            experiment_name=exp_name_modified,
            accuracy=accuracy,
            loss=loss,
            class_accuracies=class_accuracies,
            duration_min=elapsed_min,
            run_id=run_id,
            mlflow_uri=f"http://{aggregator.ip}:5000",
            experiment_id=experiment_id,
        )

        # Trigger automated plots and report generation
        run_post_training_plots_and_report(
            key_path=key_path,
            aggregator_ip=aggregator.ip,
            experiment_name=exp_name_modified,
            rounds=rounds,
            lambda_ewc=lambda_ewc
        )

    except KeyboardInterrupt:
        print("\n[!] User interrupted the execution. Starting cleanup.")
        elapsed_min = (time.time() - start_time) / 60.0
        notifier.notify_failure(experiment_name, "User interrupted (KeyboardInterrupt)", duration_min=elapsed_min)
    except Exception as e:
        print(f"\n[!] Orchestration error: {e}")
        elapsed_min = (time.time() - start_time) / 60.0
        notifier.notify_failure(experiment_name, str(e), duration_min=elapsed_min)
    finally:
        print("\n=== Phase 9: Cleaning up remote background processes ===")
        for node in nodes:
            node.cleanup(kill_mlflow=False)

        elapsed_min = (time.time() - start_time) / 60.0
        print(f"\n[OK] Orchestration workflow finished in {elapsed_min:.1f} minutes.")
        print("Check MLflow dashboard at http://10.10.130.10:5000 to verify continual learning metrics.")


if __name__ == "__main__":
    main()
