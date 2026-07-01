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

def load_env(env_name: str = ".env"):
    """Load environment variables from a .env file searching upward from the script directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_path = os.path.join(current_dir, env_name)
        if os.path.exists(env_path):
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
            break
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent

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


def validate_sanitized_inputs(
    rounds, cl_strategy, lambda_ewc, gem_patterns, gem_memory_strength, duration,
    weights_str, lr, momentum, batch_size, experiment_name, dos_threshold,
    mlops_mode, production_strategy, jsd_threshold, gate_action, baseline_class_dist,
    poison_client_ids, poison_rate, poison_from_class, poison_to_class,
    dp_noise_multiplier, dp_max_grad_norm, aggregation_strategy, trimmed_mean_beta,
    aggregator_ip, def_a_ip, def_b_ip, target_a_ip, target_b_ip, traffic_gen_ip
):
    """
    Validate that all configuration values are clean and conform to their expected types and boundaries,
    ensuring resilience against command injection or bad inputs.
    """
    import re
    
    # 1. Type and value validations
    assert isinstance(rounds, int) and 0 < rounds <= 1000, f"Invalid rounds: {rounds}"
    
    cl_strategy = str(cl_strategy).upper()
    assert cl_strategy in ("EWC", "GEM", "NAIVE"), f"Invalid CL strategy: {cl_strategy}"
    
    assert isinstance(lambda_ewc, (int, float)) and 0.0 <= lambda_ewc <= 100.0, f"Invalid lambda_ewc: {lambda_ewc}"
    assert isinstance(gem_patterns, int) and 0 < gem_patterns <= 10000, f"Invalid gem_patterns: {gem_patterns}"
    assert isinstance(gem_memory_strength, (int, float)) and 0.0 <= gem_memory_strength <= 10.0, f"Invalid gem_memory_strength: {gem_memory_strength}"
    assert isinstance(duration, int) and 0 < duration <= 3600, f"Invalid simulation duration: {duration}"
    
    # 2. Check string patterns via regex
    # class_weights must be a comma-separated list of positive floats/ints: "12.0,3.0,3.0,15.0,1.0"
    if not re.match(r"^\d+(\.\d+)?(,\d+(\.\d+)?)*$", weights_str):
        raise ValueError(f"Invalid class weights format: {weights_str}")
        
    assert isinstance(lr, (int, float)) and 0.0 < lr <= 1.0, f"Invalid learning rate: {lr}"
    assert isinstance(momentum, (int, float)) and 0.0 <= momentum <= 1.0, f"Invalid momentum: {momentum}"
    assert isinstance(batch_size, int) and 0 < batch_size <= 2048, f"Invalid batch_size: {batch_size}"
    
    # experiment_name can only contain alphanumeric characters, hyphens, and underscores (safe for paths/shells)
    if not re.match(r"^[a-zA-Z0-9_\-]+$", experiment_name):
        raise ValueError(f"Invalid experiment name (must be alphanumeric/hyphen/underscore): {experiment_name}")
        
    assert isinstance(dos_threshold, (int, float)) and 0 <= dos_threshold <= 100000, f"Invalid dos_threshold: {dos_threshold}"
    
    mlops_mode = str(mlops_mode).lower()
    assert mlops_mode in ("experimental", "production"), f"Invalid mlops_mode: {mlops_mode}"
    
    production_strategy = str(production_strategy).lower()
    assert production_strategy in ("resume", "scratch"), f"Invalid production_strategy: {production_strategy}"
    
    assert isinstance(jsd_threshold, (int, float)) and 0.0 <= jsd_threshold <= 1.0, f"Invalid jsd_threshold: {jsd_threshold}"
    
    gate_action = str(gate_action).lower()
    assert gate_action in ("abort", "quarantine", "alert"), f"Invalid gate_action: {gate_action}"
    
    # baseline_class_dist: "2000,10,200,50,100"
    if not re.match(r"^\d+(,\d+)*$", baseline_class_dist):
        raise ValueError(f"Invalid baseline_class_distribution: {baseline_class_dist}")
        
    # poison_client_ids must contain only valid letters/numbers
    for cid in poison_client_ids:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", str(cid)):
            raise ValueError(f"Invalid client ID for poisoning: {cid}")
            
    assert isinstance(poison_rate, (int, float)) and 0.0 <= poison_rate <= 1.0, f"Invalid poison_rate: {poison_rate}"
    assert isinstance(poison_from_class, int) and 0 <= poison_from_class < 5, f"Invalid poison_from_class: {poison_from_class}"
    assert isinstance(poison_to_class, int) and 0 <= poison_to_class < 5, f"Invalid poison_to_class: {poison_to_class}"

    assert isinstance(dp_noise_multiplier, (int, float)) and 0.0 <= dp_noise_multiplier <= 10.0, f"Invalid dp_noise_multiplier: {dp_noise_multiplier}"
    assert isinstance(dp_max_grad_norm, (int, float)) and 0.0 <= dp_max_grad_norm <= 100.0, f"Invalid dp_max_grad_norm: {dp_max_grad_norm}"
    
    aggregation_strategy = str(aggregation_strategy)
    assert aggregation_strategy in ("FedAvg", "FedMedian", "Krum", "TrimmedMean"), f"Invalid aggregation strategy: {aggregation_strategy}"
    assert isinstance(trimmed_mean_beta, (int, float)) and 0.0 <= trimmed_mean_beta <= 0.5, f"Invalid trimmed_mean_beta: {trimmed_mean_beta}"

    # Verify IP formats to block remote shell IP injection hacks
    ip_regex = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    for ip in (aggregator_ip, def_a_ip, def_b_ip, target_a_ip, target_b_ip, traffic_gen_ip):
        if not re.match(ip_regex, str(ip)):
            raise ValueError(f"Malformed node IP address: {ip}")


def safe_print(text):
    """Prints text safely bypassing Windows CP1252/Unicode encoding constraints."""
    import sys
    try:
        enc = sys.stdout.encoding or "utf-8"
        print(str(text).encode(enc, errors="replace").decode(enc))
    except Exception:
        try:
            print(str(text).encode("ascii", errors="ignore").decode())
        except Exception:
            pass


# ─── Remote Node ─────────────────────────────────────────────────────────────

class RemoteNode:
    def __init__(self, name, ip, username="root", key_path=None):
        self.name = name
        self.ip = ip
        self.username = username
        self.key_path = key_path
        self.procs = []

    def _get_ssh_opts(self):
        opts = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            "-o", "ServerAliveInterval=10",
            "-o", "ServerAliveCountMax=3"
        ]
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
            return subprocess.run(ssh_cmd, capture_output=True, text=True, encoding="utf-8")

    def scp_file(self, local_path, remote_path):
        opts = self._get_ssh_opts()
        scp_cmd = ["scp"] + opts + [local_path, f"{self.username}@{self.ip}:{remote_path}"]
        print(f"[{self.name}] Transferring {local_path} -> {remote_path}")
        return subprocess.run(scp_cmd, capture_output=True, text=True, encoding="utf-8")

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


def get_dataset_hash(node: RemoteNode) -> str:
    """Compute a SHA-256 hash of the flow CSVs on the remote node's ramdisk."""
    res = node.run_cmd("find /mnt/ramdisk/flows/ -name '*.csv' -type f -exec sha256sum {} + | sort | sha256sum")
    out = res.stdout.strip()
    if out:
        return out.split()[0]
    return "empty_or_unknown"



def run_post_training_plots_and_report(key_path, aggregator_ip, experiment_name, rounds, lambda_ewc, cl_strategy="EWC", gem_patterns=256, gem_memory_strength=0.5):
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
            f.write(f"- **Continual Learning Strategy**: `{cl_strategy}`\n")
            if cl_strategy.upper() == "EWC":
                f.write(f"- **EWC Lambda**: `{lambda_ewc}`\n")
            elif cl_strategy.upper() == "GEM":
                f.write(f"- **GEM Patterns Per Exp**: `{gem_patterns}`\n")
                f.write(f"- **GEM Memory Strength**: `{gem_memory_strength}`\n")
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

        # Call Local LLM Threat Analysis & MLflow Artifact Upload
        try:
            print("\n=== Phase 8c: Querying Local LLM for Report Analysis & Artifact Upload ===")
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tools_dir = os.path.join(project_root, "tools")
            if tools_dir not in sys.path:
                sys.path.insert(0, tools_dir)
            import generate_llm_report
            generate_llm_report.append_and_upload_report(
                run_dir=run_dir,
                run_id=run_id,
                final_metrics=final_metrics,
                lambda_ewc=lambda_ewc,
                rounds=rounds,
                aggregator_ip=aggregator_ip,
                cl_strategy=cl_strategy,
                gem_patterns=gem_patterns,
                gem_memory_strength=gem_memory_strength
            )
        except Exception as llm_err:
            print(f"[!] Warning: Local LLM reporting or artifact upload failed: {llm_err}")

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
    parser.add_argument("--lr", type=float, default=None, help="SGD learning rate (overrides config)")
    parser.add_argument("--momentum", type=float, default=None, help="SGD momentum (overrides config)")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size (overrides config)")
    parser.add_argument("--class-weights", default=None, help="Comma-separated class weights (overrides config)")
    parser.add_argument("--parent-run-id", default="", help="MLflow parent run ID for sweep tracking")
    parser.add_argument("--cl-strategy", default=None, help="CL strategy: EWC, GEM, Naive")
    parser.add_argument("--gem-patterns", type=int, default=None, help="GEM patterns per experience")
    parser.add_argument("--gem-memory-strength", type=float, default=None, help="GEM memory strength")
    parser.add_argument("--cl-task-sequence", default=None, help="CL task sequence trained (comma-separated, overrides config)")
    parser.add_argument("--cl-complexity-score", type=float, default=None, help="Sequence complexity score (overrides config)")
    parser.add_argument("--comm-overhead-budget", type=int, default=None, help="Communication overhead budget in bytes (overrides config)")
    parser.add_argument("--telegram-bot-token", default=None, help="Telegram bot token (overrides config)")
    parser.add_argument("--telegram-chat-id", default=None, help="Telegram chat ID (overrides config)")
    parser.add_argument("--telegram-enabled", action="store_true", help="Force enable Telegram notifications")
    
    # Theme E Security & Privacy parameters
    parser.add_argument("--poison-enabled", type=str, default=None, help="Enable label poisoning (true/false)")
    parser.add_argument("--poison-client-ids", default=None, help="Comma-separated client IDs to poison (e.g. A)")
    parser.add_argument("--poison-rate", type=float, default=None, help="Poison rate")
    parser.add_argument("--poison-from-class", type=int, default=None, help="Source class for poisoning")
    parser.add_argument("--poison-to-class", type=int, default=None, help="Target class for poisoning")
    parser.add_argument("--dp-enabled", type=str, default=None, help="Enable client Differential Privacy (true/false)")
    parser.add_argument("--dp-noise-multiplier", type=float, default=None, help="DP noise multiplier")
    parser.add_argument("--dp-max-grad-norm", type=float, default=None, help="DP max gradient norm")
    parser.add_argument("--aggregation-strategy", default=None, choices=["FedAvg", "FedMedian", "Krum", "TrimmedMean"], help="Robust aggregation strategy")
    parser.add_argument("--trimmed-mean-beta", type=float, default=None, help="Trimmed mean beta")
    args = parser.parse_args()

    # Load config — CLI args override YAML values
    config = {}
    config_file = args.config
    
    # Automatically fallback to local override configuration if available
    if config_file == "configs/experiment.yaml":
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "configs/local_experiment.yaml")
        if os.path.exists(local_path):
            config_file = "configs/local_experiment.yaml"
            print(f"[orchestrator] Using local configuration override: {config_file}")

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", config_file)
    if os.path.exists(config_path):
        config = load_config(config_path)
        print(f"[*] Loaded config: {config_path}")
    elif os.path.exists(config_file):
        config = load_config(config_file)
        config_path = config_file
        print(f"[*] Loaded config: {config_file}")
    else:
        print(f"[!] Config not found at {args.config}. Using CLI defaults.")
        config_path = None

    rounds = args.rounds or get_config_value(config, "fl", "rounds", default=10)
    cl_strategy = args.cl_strategy or get_config_value(config, "cl", "strategy", default="EWC")
    lambda_ewc = args.lambda_ewc or get_config_value(config, "cl", "ewc_lambda", default=0.4)
    gem_patterns = args.gem_patterns or get_config_value(config, "cl", "gem_patterns_per_exp", default=256)
    gem_memory_strength = args.gem_memory_strength or get_config_value(config, "cl", "gem_memory_strength", default=0.5)
    duration = args.duration or get_config_value(config, "simulation", "attack_duration_seconds", default=30)
    
    if args.class_weights:
        weights_str = args.class_weights
    else:
        class_weights = get_config_value(config, "training", "class_weights", default=[12.0, 3.0, 3.0, 15.0, 1.0])
        weights_str = ",".join(map(str, class_weights))
        
    lr = args.lr or get_config_value(config, "training", "lr", default=0.01)
    momentum = args.momentum or get_config_value(config, "training", "momentum", default=0.9)
    batch_size = args.batch_size or get_config_value(config, "training", "batch_size", default=32)
    
    experiment_name = get_config_value(config, "experiment", "name", default="FL-CL-Run")
    dos_threshold = get_config_value(config, "labeling", "dos_duration_threshold_ms", default=2000)
    mlops_mode = args.mlops_mode or get_config_value(config, "mlops", "mode", default="experimental")
    production_strategy = args.production_strategy or get_config_value(config, "mlops", "production_strategy", default="resume")

    cl_task_sequence = args.cl_task_sequence or get_config_value(config, "cl", "task_sequence", default="")
    cl_complexity_score = args.cl_complexity_score if args.cl_complexity_score is not None else get_config_value(config, "cl", "complexity_score", default=0.0)
    comm_overhead_budget = args.comm_overhead_budget if args.comm_overhead_budget is not None else get_config_value(config, "cl", "comm_overhead_budget", default=200000000)

    # Theme C Configs
    jsd_threshold = get_config_value(config, "data_quality", "jsd_threshold", default=0.6)
    gate_action = get_config_value(config, "data_quality", "gate_action", default="abort")
    baseline_stats_path = get_config_value(config, "data_quality", "baseline_stats_path", default="configs/baseline_feature_stats.json")
    baseline_class_dist = get_config_value(config, "data_quality", "baseline_class_distribution", default="2000,10,200,50,100")

    # Theme E Security & Privacy Configs
    if args.poison_enabled is not None:
        poison_enabled = args.poison_enabled.lower() in ("true", "1")
    else:
        poison_enabled = get_config_value(config, "security", "poison_enabled", default=False)

    if args.poison_client_ids is not None:
        poison_client_ids = [cid.strip() for cid in args.poison_client_ids.split(",") if cid.strip()]
    else:
        poison_client_ids = get_config_value(config, "security", "poison_client_ids", default=[])

    poison_rate = args.poison_rate if args.poison_rate is not None else get_config_value(config, "security", "poison_rate", default=0.2)
    poison_from_class = args.poison_from_class if args.poison_from_class is not None else get_config_value(config, "security", "poison_from_class", default=0)
    poison_to_class = args.poison_to_class if args.poison_to_class is not None else get_config_value(config, "security", "poison_to_class", default=4)

    if args.dp_enabled is not None:
        dp_enabled = args.dp_enabled.lower() in ("true", "1")
    else:
        dp_enabled = get_config_value(config, "security", "dp_enabled", default=False)

    dp_noise_multiplier = args.dp_noise_multiplier if args.dp_noise_multiplier is not None else get_config_value(config, "security", "dp_noise_multiplier", default=0.1)
    dp_max_grad_norm = args.dp_max_grad_norm if args.dp_max_grad_norm is not None else get_config_value(config, "security", "dp_max_grad_norm", default=1.0)

    aggregation_strategy = args.aggregation_strategy or get_config_value(config, "security", "aggregation_strategy", default="FedAvg")
    trimmed_mean_beta = args.trimmed_mean_beta if args.trimmed_mean_beta is not None else get_config_value(config, "security", "trimmed_mean_beta", default=0.1)

    # Set up Telegram notifications (prioritize environment variables for security)
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN") or args.telegram_bot_token or get_config_value(config, "notifications", "telegram", "bot_token", default="")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID") or args.telegram_chat_id or get_config_value(config, "notifications", "telegram", "chat_id", default="")
    tg_enabled = args.telegram_enabled or get_config_value(config, "notifications", "telegram", "enabled", default=False)
    if tg_token and tg_chat_id:
        tg_enabled = True
    notifier = TelegramNotifier(bot_token=tg_token, chat_id=tg_chat_id, enabled=tg_enabled)

    # Determine the key path to use for remote node communication
    default_key = os.path.expanduser("~/.ssh/id_ed25519")
    if not os.path.exists(default_key) and os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
        default_key = os.path.expanduser("~/.ssh/id_rsa")
    key_path = args.key or os.environ.get("SSH_KEY_PATH") or default_key

    # Define node IPs to pass to the validator
    aggregator_ip = get_config_value(config, "topology", "aggregator", default="10.10.130.10")
    def_a_ip = get_config_value(config, "topology", "defender_a", default="10.10.130.11")
    def_b_ip = get_config_value(config, "topology", "defender_b", default="10.10.130.12")
    target_a_ip = get_config_value(config, "topology", "target_a", default="10.10.110.15")
    target_b_ip = get_config_value(config, "topology", "target_b", default="10.10.120.15")
    traffic_gen_ip = get_config_value(config, "topology", "traffic_gen", default="10.10.140.10")

    # Run sanitization validation to prevent command injection
    validate_sanitized_inputs(
        rounds, cl_strategy, lambda_ewc, gem_patterns, gem_memory_strength, duration,
        weights_str, lr, momentum, batch_size, experiment_name, dos_threshold,
        mlops_mode, production_strategy, jsd_threshold, gate_action, baseline_class_dist,
        poison_client_ids, poison_rate, poison_from_class, poison_to_class,
        dp_noise_multiplier, dp_max_grad_norm, aggregation_strategy, trimmed_mean_beta,
        aggregator_ip, def_a_ip, def_b_ip, target_a_ip, target_b_ip, traffic_gen_ip
    )

    # Define all remote nodes
    aggregator = RemoteNode("fl-aggregator", aggregator_ip, "root", key_path)
    def_a = RemoteNode("defender-a", def_a_ip, "root", key_path)
    def_b = RemoteNode("defender-b", def_b_ip, "root", key_path)
    target_a = RemoteNode("target-a1", target_a_ip, "root", key_path)
    target_b = RemoteNode("target-b1", target_b_ip, "root", key_path)
    traffic_gen = RemoteNode("traffic-gen", traffic_gen_ip, "root", key_path)

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
        config_summary=f"Strategy={cl_strategy} (lambda={lambda_ewc} if EWC, patterns={gem_patterns} if GEM), Duration={duration}s",
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
        aggregator.scp_file("src/notifications.py", "~/notifications.py")

        # Send experiment config to aggregator for MLflow artifact logging
        if config_path and os.path.exists(config_path):
            aggregator.scp_file(config_path, "~/experiment.yaml")

        # Defender A files
        def_a.scp_file("src/defender/client.py", "~/client.py")
        def_a.scp_file("src/defender/cl_strategy.py", "~/cl_strategy.py")
        def_a.scp_file("src/defender/model.py", "~/model.py")
        def_a.scp_file("src/defender/extractor.py", "~/extractor.py")
        def_a.scp_file("tools/check_dataset.py", "~/check_dataset.py")
        def_a.scp_file("tools/check_features.py", "~/check_features.py")

        # Defender B files
        def_b.scp_file("src/defender/client.py", "~/client.py")
        def_b.scp_file("src/defender/cl_strategy.py", "~/cl_strategy.py")
        def_b.scp_file("src/defender/model.py", "~/model.py")
        def_b.scp_file("src/defender/extractor.py", "~/extractor.py")
        def_b.scp_file("tools/check_dataset.py", "~/check_dataset.py")
        def_b.scp_file("tools/check_features.py", "~/check_features.py")

        # Sync baseline stats for data quality drift checking
        if baseline_stats_path and os.path.exists(baseline_stats_path):
            def_a.scp_file(baseline_stats_path, "~/baseline_stats.json")
            def_b.scp_file(baseline_stats_path, "~/baseline_stats.json")

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

        # Start FL server with config artifact logging and hyperparameter overrides
        config_arg = "--config-file ~/experiment.yaml" if config_path else ""
        parent_run_arg = f"--parent-run-id {args.parent_run_id}" if args.parent_run_id else ""
        
        cl_args = f" --cl-strategy '{cl_strategy}' --gem-patterns {gem_patterns} --gem-memory-strength {gem_memory_strength}"
        if cl_task_sequence:
            cl_args += f" --cl-task-sequence '{cl_task_sequence}'"
        cl_args += f" --cl-complexity-score {cl_complexity_score}"
        cl_args += f" --comm-overhead-budget {comm_overhead_budget}"
        if tg_token:
            cl_args += f" --telegram-bot-token '{tg_token}'"
        if tg_chat_id:
            cl_args += f" --telegram-chat-id '{tg_chat_id}'"
        if tg_enabled:
            cl_args += " --telegram-enabled"

        # Theme E Server args
        server_sec_args = f" --aggregation-strategy '{aggregation_strategy}' --trimmed-mean-beta {trimmed_mean_beta}"

        server_proc = aggregator.run_cmd(
            f"/opt/flower-env/bin/python3 server.py --rounds {rounds} --min-clients 2 --mlflow-uri http://localhost:5000 {config_arg} --mlops-mode {mlops_mode} --production-strategy {production_strategy} --git-commit {git_commit} --ewc-lambda {lambda_ewc} --lr {lr} --batch-size {batch_size} --class-weights {weights_str} {parent_run_arg}{cl_args}{server_sec_args}",
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
        quality_gate_failed = False
        for node_name, node in [("defender-a", def_a), ("defender-b", def_b)]:
            # Run check_dataset.py with --baseline and --js-threshold to calculate JSD drift
            cmd = f"~/fl-cl-env/bin/python3 ~/check_dataset.py --json --dos-threshold-ms {dos_threshold} --baseline '{baseline_class_dist}' --js-threshold {jsd_threshold}"
            result = node.run_cmd(cmd)
            try:
                import json
                output = result.stdout.strip()
                if output:
                    res_dict = json.loads(output)
                    label_counts = res_dict.get("counts", {})
                    jsd_val = res_dict.get("js_divergence")
                    status = res_dict.get("status", "PASS")

                    label_names = {0: "Normal", 1: "Botnet", 2: "Exfil", 3: "SSH-BF", 4: "DoS"}
                    total = sum(label_counts.values()) if label_counts else 0
                    print(f"[{node_name}] Flow distribution ({total} total):")
                    for label in range(5):
                        count = label_counts.get(str(label), label_counts.get(label, 0))
                        name = label_names.get(label, "?")
                        print(f"  Class {label} ({name:>7s}): {count}")
                    
                    if jsd_val is not None:
                        print(f"[{node_name}] Jensen-Shannon Divergence: {jsd_val:.4f} (Threshold: {jsd_threshold})")
                    
                    if status == "FAIL":
                        print(f"[{node_name}] [FAIL] DATA QUALITY GATE FAILED: JSD {jsd_val:.4f} exceeds threshold {jsd_threshold}")
                        quality_gate_failed = True
                    else:
                        print(f"[{node_name}] [PASS] DATA QUALITY GATE PASSED")
                else:
                    print(f"[{node_name}] [!] WARNING: Empty response from data quality check")
                    quality_gate_failed = True
            except Exception as e:
                print(f"[{node_name}] [!] Error parsing data quality gate output: {e}")
                print(f"[{node_name}] stdout:")
                safe_print(result.stdout)
                print(f"[{node_name}] stderr:")
                safe_print(result.stderr)
                quality_gate_failed = True

        if quality_gate_failed:
            if gate_action == "abort":
                print(f"\n[!] CRITICAL: Data quality gate failed on pre-flight check. (Action: abort). Halting training pipeline.")
                notifier.notify_failure(experiment_name, "Data quality gate failed on pre-flight check (Action: abort)")
                for node in nodes:
                    node.cleanup(kill_mlflow=False)
                sys.exit(2)
            else:
                print(f"\n[!] WARNING: Data quality gate failed, but gate_action is set to '{gate_action}'. Proceeding with warnings.")

        print("\n=== Phase 6d: Computing Dataset Checksums for Provenance Lineage ===")
        hash_a = get_dataset_hash(def_a)
        hash_b = get_dataset_hash(def_b)
        import hashlib
        combined_hash_input = f"a:{hash_a}|b:{hash_b}"
        dataset_hash = hashlib.sha256(combined_hash_input.encode('utf-8')).hexdigest()
        print(f"[orchestrator] defender-a dataset hash: {hash_a}")
        print(f"[orchestrator] defender-b dataset hash: {hash_b}")
        print(f"[orchestrator] Combined dataset checksum: {dataset_hash}")

        # Get the active MLflow run ID from the aggregator
        run_id_res = aggregator.run_cmd("cat /tmp/current_run_id.txt 2>/dev/null")
        active_run_id = run_id_res.stdout.strip()
        if active_run_id:
            print(f"[orchestrator] Active MLflow run ID: {active_run_id}")
            local_script_path = "log_dataset_temp.py"
            with open(local_script_path, "w") as sf:
                sf.write(f"""import mlflow, json
mlflow.set_tracking_uri('http://localhost:5000')
client = mlflow.tracking.MlflowClient()
client.log_param('{active_run_id}', 'dataset_hash', '{dataset_hash}')
client.log_param('{active_run_id}', 'defender_a_hash', '{hash_a}')
client.log_param('{active_run_id}', 'defender_b_hash', '{hash_b}')
metadata = {{
    "defender_a_dataset_hash": "{hash_a}",
    "defender_b_dataset_hash": "{hash_b}",
    "combined_dataset_hash": "{dataset_hash}"
}}
with open('/tmp/dataset_lineage.json', 'w') as f:
    json.dump(metadata, f, indent=4)
client.log_artifact('{active_run_id}', '/tmp/dataset_lineage.json')
""")
            aggregator.scp_file(local_script_path, "~/log_dataset.py")
            aggregator.run_cmd("/opt/flower-env/bin/python3 ~/log_dataset.py")
            try:
                os.remove(local_script_path)
            except Exception:
                pass
            print("[orchestrator] Registered dataset checksums & logged lineage artifact to MLflow run.")
        else:
            print("[orchestrator] Warning: Could not retrieve active MLflow run ID. Skipping logging dataset hashes.")

        # Phase 6e: Run per-class feature drift diagnostics
        print("\n=== Phase 6e: Per-Class Feature Drift Diagnostic ===")
        for node_name, node in [("defender-a", def_a), ("defender-b", def_b)]:
            mlflow_args = ""
            if active_run_id:
                mlflow_args = f"--mlflow --run-id {active_run_id} --mlflow-uri http://{aggregator.ip}:5000"
            cmd = f"~/fl-cl-env/bin/python3 ~/check_features.py --baseline-json ~/baseline_stats.json {mlflow_args}"
            print(f"[{node_name}] Running feature drift diagnosis...")
            feat_res = node.run_cmd(cmd)
            safe_print(feat_res.stdout)
            if feat_res.stderr:
                print(f"[{node_name}] stderr:")
                safe_print(feat_res.stderr)
            if feat_res.returncode == 2:
                print(f"[{node_name}] [WARNING] FEATURE DRIFT WARNING: Significant statistical skew observed in features.")

        print("\n=== Phase 7: Launching Flower Clients on Defender Nodes ===")
        # Security arguments logic for client A
        client_a_sec_args = ""
        if poison_enabled and "A" in poison_client_ids:
            client_a_sec_args += f" --poison-enabled --poison-rate {poison_rate} --poison-from {poison_from_class} --poison-to {poison_to_class}"
        if dp_enabled:
            client_a_sec_args += f" --dp-enabled --dp-noise-multiplier {dp_noise_multiplier} --dp-max-grad-norm {dp_max_grad_norm}"

        # Security arguments logic for client B
        client_b_sec_args = ""
        if poison_enabled and "B" in poison_client_ids:
            client_b_sec_args += f" --poison-enabled --poison-rate {poison_rate} --poison-from {poison_from_class} --poison-to {poison_to_class}"
        if dp_enabled:
            client_b_sec_args += f" --dp-enabled --dp-noise-multiplier {dp_noise_multiplier} --dp-max-grad-norm {dp_max_grad_norm}"

        def_a.run_cmd(f"~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id A --cl-strategy '{cl_strategy}' --ewc-lambda {lambda_ewc} --gem-patterns {gem_patterns} --gem-memory-strength {gem_memory_strength} --class-weights {weights_str} --lr {lr} --momentum {momentum} --dos-threshold-ms {dos_threshold} --batch-size {batch_size} --baseline '{baseline_class_dist}' --js-threshold {jsd_threshold}{client_a_sec_args}", background=True)
        def_b.run_cmd(f"~/fl-cl-env/bin/python3 client.py --server 10.10.130.10:8080 --client-id B --cl-strategy '{cl_strategy}' --ewc-lambda {lambda_ewc} --gem-patterns {gem_patterns} --gem-memory-strength {gem_memory_strength} --class-weights {weights_str} --lr {lr} --momentum {momentum} --dos-threshold-ms {dos_threshold} --batch-size {batch_size} --baseline '{baseline_class_dist}' --js-threshold {jsd_threshold}{client_b_sec_args}", background=True)

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
            lambda_ewc=lambda_ewc,
            cl_strategy=cl_strategy,
            gem_patterns=gem_patterns,
            gem_memory_strength=gem_memory_strength
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
