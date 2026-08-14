import subprocess
import os
import glob
import json
import re

EXPERIMENTS_DIR = "configs/experiments/"
EXPORTS_DIR = "exports/"
RESULTS_FILE = "scratch/final_metrics.json"

# Configurations to sweep
SWEEP_VALUES = [0.2, 0.5, 0.8]
CORE_CONFIGS = ["baseline.yaml", "dp_sgd.yaml", "data_poisoning.yaml", "robust_agg.yaml"]

# Quick test overrides
CLI_OVERRIDES = [
    "--duration", "15",
    "--rounds", "3"
]

def run_experiment(config_file, lambda_ewc=None):
    cmd = ["python", "src/orchestrate.py", "--config", os.path.join(EXPERIMENTS_DIR, config_file)]
    cmd.extend(CLI_OVERRIDES)
    if lambda_ewc is not None:
        cmd.extend(["--lambda-ewc", str(lambda_ewc)])
    
    print(f"[*] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[!] Error running {config_file}:\n{result.stderr}")
        return None
        
    return extract_metrics()

def get_latest_export():
    dirs = glob.glob(os.path.join(EXPORTS_DIR, "*"))
    dirs.sort(key=os.path.getmtime)
    if not dirs:
        return None
    return dirs[-1]

def extract_metrics():
    latest_export = get_latest_export()
    if not latest_export:
        return None
        
    summary_file = os.path.join(latest_export, "run_summary.md")
    if not os.path.exists(summary_file):
        return None
        
    metrics = {}
    with open(summary_file, "r") as f:
        for line in f:
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    key = parts[1].strip()
                    val = parts[2].strip()
                    try:
                        metrics[key] = float(val)
                    except ValueError:
                        pass
    return metrics

def calculate_avg_f1(metrics):
    f1_keys = [k for k in metrics.keys() if k.startswith("f1_class_")]
    if not f1_keys:
        return 0.0
    return sum(metrics[k] for k in f1_keys) / len(f1_keys)

def main():
    print("=== Phase 1: Hyperparameter Sweep (ewc_lambda) ===")
    sweep_results = {}
    for l_ewc in SWEEP_VALUES:
        print(f"\n--- Testing ewc_lambda = {l_ewc} ---")
        metrics = run_experiment("baseline.yaml", lambda_ewc=l_ewc)
        if metrics:
            avg_f1 = calculate_avg_f1(metrics)
            sweep_results[l_ewc] = {"metrics": metrics, "avg_f1": avg_f1}
            print(f"-> Average F1: {avg_f1:.4f}")
        else:
            print("-> Failed to extract metrics.")
            
    if not sweep_results:
        print("[!] Sweep failed completely.")
        return

    best_lambda = max(sweep_results.keys(), key=lambda k: sweep_results[k]["avg_f1"])
    print(f"\n[+] Best ewc_lambda found: {best_lambda}")
    
    print("\n=== Phase 2: Core Experiments Execution ===")
    final_results = {}
    
    for config in CORE_CONFIGS:
        print(f"\n--- Running core experiment: {config} ---")
        metrics = run_experiment(config, lambda_ewc=best_lambda)
        if metrics:
            final_results[config] = {
                "avg_f1": calculate_avg_f1(metrics),
                "accuracy": metrics.get("accuracy", 0.0),
                "loss": metrics.get("loss", 0.0),
                "bwt_class_4": metrics.get("bwt_class_4", 0.0) # Tracking forgetting for DoS
            }
            print(f"-> Accuracy: {final_results[config]['accuracy']:.4f}")
        else:
            print("-> Failed to extract metrics.")
            
    print(f"\n=== Phase 3: Exporting Results ===")
    with open(RESULTS_FILE, "w") as f:
        json.dump(final_results, f, indent=4)
        
    print(f"Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()
