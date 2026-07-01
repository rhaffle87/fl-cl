"""
check_features.py — Per-class feature statistics for FL-CL flow data.

Compares flow-level feature distributions across all 5 attack classes to
identify feature overlap (classes that the model cannot separate).

Usage (SCP to defender, then run):
    python3 check_features.py [--flows-dir /mnt/ramdisk/flows]
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append("/root")
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src" / "defender"))
import client


LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}

FEATURE_COLS = [
    "bidirectional_packets", "bidirectional_bytes", "duration_ms",
    "src2dst_packets", "src2dst_bytes", "dst2src_packets", "dst2src_bytes",
    "src2dst_mean_piat_ms", "dst2src_mean_piat_ms", "dst_port",
]


def load_flows(flows_dir):
    csv_files = sorted(Path(flows_dir).glob("*.csv"))
    if not csv_files:
        print("No CSV files found in", flows_dir)
        sys.exit(1)

    dfs = []
    for f in csv_files:
        try:
            d = pd.read_csv(f)
            if not d.empty:
                dfs.append(d)
        except Exception:
            pass

    if not dfs:
        print("No valid flow records found in", flows_dir)
        sys.exit(1)

    df = pd.concat(dfs, ignore_index=True)
    df["label"] = df.apply(client.assign_label, axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(description="Per-class feature statistics and drift detector")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--compare", nargs=2, type=int, metavar=("A", "B"),
                        help="Compare two specific classes (e.g. --compare 1 4)")
    parser.add_argument("--baseline-json", default="configs/baseline_feature_stats.json",
                        help="Path to baseline feature statistics JSON file")
    parser.add_argument("--z-threshold", type=float, default=3.0,
                        help="Z-score threshold above which drift is flagged")
    parser.add_argument("--mlflow", action="store_true", help="Log feature stats and drift metrics to MLflow")
    parser.add_argument("--mlflow-uri", default="http://10.10.130.10:5000", help="MLflow server URI")
    parser.add_argument("--run-id", default=None, help="MLflow active run ID to log directly inside")
    parser.add_argument("--round", type=int, default=0, help="Current training round (global step)")
    parser.add_argument("--tensorboard", action="store_true", help="Write feature histograms to TensorBoard")
    parser.add_argument("--tb-log-dir", default="runs/feature_drift", help="TensorBoard log directory")
    args = parser.parse_args()

    df = load_flows(args.flows_dir)
    available_features = [c for c in FEATURE_COLS if c in df.columns]

    if args.compare:
        classes = args.compare
    else:
        classes = sorted(df["label"].unique())

    # Load baseline stats
    baseline_stats = {}
    if args.baseline_json:
        baseline_path = Path(args.baseline_json)
        if baseline_path.exists():
            try:
                import json
                with open(baseline_path, "r") as f:
                    baseline_stats = json.load(f)
            except Exception as e:
                sys.stderr.write(f"Failed to load baseline JSON: {e}\n")
        else:
            sys.stderr.write(f"Baseline JSON path {args.baseline_json} does not exist. Skipping Z-score comparisons.\n")

    drift_detected = False
    current_stats = {}
    mlflow_metrics = {}

    for label in classes:
        sub = df[df["label"] == label][available_features]
        name = LABEL_NAMES.get(label, "Unknown")
        current_stats[str(label)] = {}
        
        print(f"\n{'='*70}")
        print(f"LABEL {label} — {name} (n={len(sub)})")
        print(f"{'='*70}")
        
        class_baseline = baseline_stats.get(str(label), {})
        
        for col in available_features:
            s = sub[col]
            mean_val = float(s.mean()) if len(sub) > 0 else 0.0
            std_val = float(s.std()) if len(sub) > 1 else 0.0
            min_val = float(s.min()) if len(sub) > 0 else 0.0
            max_val = float(s.max()) if len(sub) > 0 else 0.0
            
            current_stats[str(label)][col] = {
                "mean": mean_val,
                "std": std_val
            }
            
            z_score = None
            z_str = ""
            
            if col in class_baseline:
                b_mean = class_baseline[col].get("mean", 0.0)
                b_std = class_baseline[col].get("std", 1.0)
                if b_std > 0:
                    z_score = (mean_val - b_mean) / b_std
                    z_str = f"  Z-score={z_score:>6.2f}"
                    mlflow_metrics[f"drift_z_class_{label}_{col}"] = z_score
                    
                    if abs(z_score) > args.z_threshold:
                        drift_detected = True
                        z_str += " ⚠️ DRIFT DETECTED"
            
            mlflow_metrics[f"feature_mean_class_{label}_{col}"] = mean_val
            mlflow_metrics[f"feature_std_class_{label}_{col}"] = std_val
            
            print(f"  {col:>25s}:  mean={mean_val:>10.2f}  std={std_val:>10.2f}  "
                  f"min={min_val:>8.0f}  max={max_val:>8.0f}{z_str}")

    # Port distribution summary
    print(f"\n{'='*70}")
    print("dst_port distribution per class")
    print(f"{'='*70}")
    for label in classes:
        name = LABEL_NAMES.get(label, "Unknown")
        ports = df[df["label"] == label]["dst_port"].value_counts().head(5)
        port_str = ", ".join([f"{p}({c})" for p, c in ports.items()])
        print(f"  {label} ({name:>13s}): {port_str}")

    # Log to MLflow
    if args.mlflow:
        try:
            import mlflow
            # Ensure tracking URI is set
            mlflow.set_tracking_uri(args.mlflow_uri)
            
            def log_to_run():
                for metric_name, val in mlflow_metrics.items():
                    mlflow.log_metric(metric_name, val, step=args.round)
                
                # Log JSON report as artifact
                import json
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    stat_file = Path(tmpdir) / f"feature_stats_round_{args.round}.json"
                    with open(stat_file, "w") as f:
                        json.dump(current_stats, f, indent=2)
                    mlflow.log_artifact(str(stat_file), artifact_path="feature_drift_reports")
            
            if args.run_id:
                with mlflow.start_run(run_id=args.run_id):
                    log_to_run()
            else:
                if mlflow.active_run() is None:
                    mlflow.set_experiment("FL-CL-CyberDefense")
                    with mlflow.start_run():
                        log_to_run()
                else:
                    log_to_run()
            print("Feature drift metrics logged successfully to MLflow.")
        except Exception as e:
            sys.stderr.write(f"Failed to log to MLflow: {e}\n")

    # Log to TensorBoard
    if args.tensorboard:
        try:
            from torch.utils.tensorboard import SummaryWriter
            writer = SummaryWriter(log_dir=args.tb_log_dir)
            for label in classes:
                sub = df[df["label"] == label][available_features]
                if not sub.empty:
                    for col in available_features:
                        writer.add_histogram(f"Features_Class_{label}/{col}", sub[col].values, global_step=args.round)
            writer.close()
            print(f"TensorBoard histograms written to {args.tb_log_dir}")
        except Exception as e:
            sys.stderr.write(f"Failed to log to TensorBoard: {e}\n")

    # Exit code: 2 if drift detected, 0 otherwise
    sys.exit(2 if drift_detected else 0)


if __name__ == "__main__":
    main()
