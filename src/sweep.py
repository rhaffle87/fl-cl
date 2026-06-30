import os
import sys
import yaml
import argparse
import itertools
import subprocess
from datetime import datetime
import mlflow

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

# Prevent Windows Unicode/emoji console encoding errors
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="FCL Hyperparameter Sweep Controller")
    parser.add_argument("--config", default="configs/sweep_grid.yaml", help="Sweep configuration YAML file")
    parser.add_argument("--key", default=None, help="Path to SSH private key")
    parser.add_argument("--dry-run", action="store_true", help="Print sweep combinations without executing")
    args = parser.parse_args()

    # Locate sweep config
    config_path = args.config
    if not os.path.exists(config_path):
        # Check parent folder relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", args.config)
        if not os.path.exists(config_path):
            print(f"[!] Error: Sweep config file not found at {args.config} or {config_path}")
            sys.exit(1)

    config = load_yaml(config_path)
    exp_config = config.get("experiment", {})
    sweep_config = config.get("sweep", {})
    
    exp_name = exp_config.get("name", "FCL-Sweep")
    parameters_dict = sweep_config.get("parameters", {})
    
    # Generate grid combinations
    keys = list(parameters_dict.keys())
    values_list = [parameters_dict[k] for k in keys]
    combinations = list(itertools.product(*values_list))
    
    print(f"[*] Loaded sweep config from {config_path}")
    print(f"[*] Sweep parameters: {list(keys)}")
    print(f"[*] Total combinations to run: {len(combinations)}")
    
    if args.dry_run:
        print("\n=== Dry Run: Parameter Combinations ===")
        for idx, combo in enumerate(combinations):
            param_map = dict(zip(keys, combo))
            print(f"Run {idx + 1}/{len(combinations)}: {param_map}")
        return

    # Set up MLflow
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://10.10.130.10:5000")
    mlflow.set_tracking_uri(tracking_uri)
    
    try:
        mlflow.set_experiment(exp_name)
    except Exception as e:
        print(f"[!] Warning: Could not set MLflow experiment to '{exp_name}': {e}")
        print("[*] Proceeding without remote MLflow parent tracking.")

    # Start parent run
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parent_run_name = f"Sweep-Parent-{timestamp}"
    
    parent_run = None
    parent_run_id = ""
    try:
        parent_run = mlflow.start_run(run_name=parent_run_name, tags={"sweep_parent": "true"})
        parent_run_id = parent_run.info.run_id
        print(f"[*] Started MLflow Parent Run: {parent_run_name} (ID: {parent_run_id})")
        # Log sweep metadata
        mlflow.log_params({f"sweep_space_{k.replace('.', '_')}": str(v) for k, v in parameters_dict.items()})
    except Exception as e:
        print(f"[!] Warning: Failed to start parent MLflow run: {e}")
        print("[*] Proceeding with child runs only.")

    try:
        for idx, combo in enumerate(combinations):
            param_map = dict(zip(keys, combo))
            print(f"\n==================================================")
            print(f"[*] Executing Run {idx + 1}/{len(combinations)}")
            print(f"[*] Parameters: {param_map}")
            print(f"==================================================")
            
            # Map parameters to orchestrate.py arguments
            cmd = ["python", "src/orchestrate.py"]
            if args.key:
                cmd.extend(["--key", args.key])
            if parent_run_id:
                cmd.extend(["--parent-run-id", parent_run_id])
                
            for k, val in param_map.items():
                if k == "cl.ewc_lambda":
                    cmd.extend(["--lambda-ewc", str(val)])
                elif k == "training.lr":
                    cmd.extend(["--lr", str(val)])
                elif k == "training.batch_size":
                    cmd.extend(["--batch-size", str(val)])
                elif k == "fl.rounds":
                    cmd.extend(["--rounds", str(val)])
                elif k == "training.class_weights":
                    weights_str = ",".join(map(str, val)) if isinstance(val, list) else str(val)
                    cmd.extend(["--class-weights", weights_str])
            
            print(f"[*] Command: {' '.join(cmd)}")
            try:
                # Run the orchestrator
                subprocess.run(cmd, check=True)
                print(f"[+] Run {idx + 1} completed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"[!] Error: Run {idx + 1} failed with exit code {e.returncode}")
                # Continue with the next combination in grid search
                continue
    finally:
        if parent_run:
            mlflow.end_run()
            print(f"[*] Ended MLflow Parent Run: {parent_run_name}")

if __name__ == "__main__":
    main()
