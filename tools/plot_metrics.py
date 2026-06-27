import os
import sys
import sqlite3
import subprocess
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def run_plotting(key_path, aggregator_ip, local_db="mlflow_temp.db", run_id_arg=None, output_dir=None):
    """
    Backs up the remote MLflow database, downloads it, queries metrics for a given or latest run,
    generates individual convergence plots for 5 traffic classes, and cleans up.
    Returns a dictionary with run metadata, final metrics, and relative filenames of generated plots.
    """
    if output_dir is None:
        # Default to exports/plots relative to the workspace (assuming script is in tools/)
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "plots"))
    os.makedirs(output_dir, exist_ok=True)

    # 1. Back up database remotely using Python's sqlite3 backup API
    print(f"[*] Backing up remote MLflow database on {aggregator_ip}...")
    backup_cmd = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no root@{aggregator_ip} "python3 -c \\"import sqlite3; src = sqlite3.connect(\'/root/mlflow.db\'); dst = sqlite3.connect(\'/tmp/mlflow_backup.db\'); src.backup(dst); dst.close(); src.close()\\""'
    subprocess.run(backup_cmd, shell=True, check=True)

    # 2. Download backup via SCP
    print(f"[*] Downloading remote MLflow database backup to {local_db}...")
    scp_cmd = f'scp -i "{key_path}" -o StrictHostKeyChecking=no root@{aggregator_ip}:/tmp/mlflow_backup.db "{local_db}"'
    subprocess.run(scp_cmd, shell=True, check=True)

    # 3. Delete remote backup file
    cleanup_remote_cmd = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no root@{aggregator_ip} "rm -f /tmp/mlflow_backup.db"'
    subprocess.run(cleanup_remote_cmd, shell=True, check=True)

    # 4. Query metrics
    conn = sqlite3.connect(local_db)
    cur = conn.cursor()

    if run_id_arg:
        run_id = run_id_arg
        cur.execute("SELECT 1 FROM runs WHERE run_uuid = ?", (run_id,))
        if not cur.fetchone():
            conn.close()
            if os.path.exists(local_db):
                os.remove(local_db)
            raise ValueError(f"Run ID {run_id} not found in the database.")
    else:
        cur.execute("SELECT run_uuid FROM runs ORDER BY start_time DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            conn.close()
            if os.path.exists(local_db):
                os.remove(local_db)
            raise ValueError("No runs found in the MLflow database.")
        run_id = row[0]
    
    print(f"[*] Processing run: {run_id}")

    cur.execute("SELECT key, value, step FROM metrics WHERE run_uuid = ? ORDER BY step ASC, key ASC", (run_id,))
    metrics_data = cur.fetchall()

    records = {}
    for key, value, step in metrics_data:
        if step not in records:
            records[step] = {"Round": step}
        records[step][key] = value

    df = pd.DataFrame(list(records.values()))
    if df.empty:
        conn.close()
        if os.path.exists(local_db):
            os.remove(local_db)
        raise ValueError(f"No metrics found for run {run_id}.")
        
    df = df.sort_values("Round")

    # 5. Plot and Export Metrics Individually
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    classes = {
        "accuracy_class_0": ("Normal", "class_0_normal", "#10ac84"),
        "accuracy_class_1": ("Botnet", "class_1_botnet", "#5f27cd"),
        "accuracy_class_2": ("DNS Exfil", "class_2_dns_exfil", "#ff9f43"),
        "accuracy_class_3": ("SSH Brute Force", "class_3_ssh_brute_force", "#ff6b6b"),
        "accuracy_class_4": ("DoS", "class_4_dos", "#48dbfb")
    }

    # Clean up any old combined metrics plot
    old_combined = os.path.join(output_dir, "metrics_plot.png")
    if os.path.exists(old_combined):
        os.remove(old_combined)

    exported_plots = {}
    for col, (display_name, file_suffix, color) in classes.items():
        if col not in df.columns:
            continue
            
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
        
        # Plot 1: Loss
        if "loss" in df.columns:
            ax1.plot(df["Round"], df["loss"], color='#ff7675', label='Global Loss', linewidth=2, marker='o', markersize=3)
        ax1.set_title(f"FL-CL Metrics: {display_name} (Run: {run_id[:8]})", fontsize=14, fontweight='bold', pad=15)
        ax1.set_ylabel("Loss", fontsize=12, fontweight='bold')
        ax1.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        # Plot 2: Global Accuracy
        global_acc = df["accuracy"] if "accuracy" in df.columns else df.get("val_accuracy", df.get("acc", []))
        if len(global_acc) > 0:
            ax2.plot(df["Round"], global_acc, color='#0984e3', label='Global Accuracy', linewidth=2, marker='s', markersize=3)
        ax2.set_ylabel("Global Accuracy", fontsize=12, fontweight='bold')
        ax2.set_ylim(-0.05, 1.05)
        ax2.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9)
        ax2.grid(True, linestyle='--', alpha=0.6)
        
        # Plot 3: Class Specific Accuracy
        ax3.plot(df["Round"], df[col], color=color, label=f'{display_name} Accuracy', linewidth=2.5, marker='x', markersize=4)
        ax3.set_xlabel("FL Round", fontsize=12, fontweight='bold')
        ax3.set_ylabel("Class Accuracy", fontsize=12, fontweight='bold')
        ax3.set_ylim(-0.05, 1.05)
        ax3.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9)
        ax3.grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        filename = f"{file_suffix}.png"
        out_file = os.path.join(output_dir, filename)
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        # Save filename for reporting
        exported_plots[display_name] = filename
        print(f"[OK] Exported plot to {out_file}")

    # Extract final step metrics
    last_row = df.iloc[-1].to_dict()
    
    # Cleanup
    conn.close()
    if os.path.exists(local_db):
        os.remove(local_db)
        
    return {
        "run_id": run_id,
        "final_metrics": last_row,
        "exported_plots": exported_plots
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export and plot MLflow metrics for FL-CL experiments.")
    parser.add_argument("--key", default=r"~/.ssh/id_ed25519", help="Path to SSH private key")
    parser.add_argument("--ip", default="10.10.130.10", help="Aggregator IP address")
    parser.add_argument("--db", default="mlflow_temp.db", help="Local temporary DB name")
    parser.add_argument("--run-id", default=None, help="Specific Run ID to plot (defaults to latest)")
    parser.add_argument("--output-dir", default=None, help="Directory to save the generated plots")
    args = parser.parse_args()

    try:
        results = run_plotting(args.key, args.ip, args.db, args.run_id, args.output_dir)
        print("\n=== Metrics Export Completed Successfully ===")
        print(f"Run ID: {results['run_id']}")
        print("Final Metrics:")
        for k, v in results['final_metrics'].items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"\n[!] Error during metrics plotting: {e}")
        sys.exit(1)
