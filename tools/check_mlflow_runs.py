"""
tools/inspect_mlflow_runs.py — Deep inspection and readable scorecard of all MLflow runs in SQLite DB.
"""
import argparse
from pathlib import Path

import os
import sqlite3
import pandas as pd
from datetime import datetime

def inspect_all_runs():
    db_path = "/root/mlflow.db" if os.path.exists("/root/mlflow.db") else "mlflow.db"
    if not os.path.exists(db_path):
        # Fallback to local snapshot if present
        if os.path.exists("data/matrix_mlflow.db"):
            db_path = "data/matrix_mlflow.db"
        else:
            print("[ERROR] Database file not found.")
            return

    conn = sqlite3.connect(db_path)

    # 1. Fetch Experiment Metadata
    exp_query = "SELECT experiment_id, name, artifact_location FROM experiments ORDER BY experiment_id"
    df_exp = pd.read_sql_query(exp_query, conn)

    # 2. Fetch Runs and Parameters
    runs_query = """
    SELECT r.run_uuid, r.experiment_id, r.status, r.start_time, r.end_time,
           p_model.value AS model_type,
           p_cl.value AS cl_strategy,
           p_agg.value AS aggregation_strategy,
           p_dp.value AS dp_enabled,
           p_lr.value AS lr,
           p_bs.value AS batch_size
    FROM runs r
    LEFT JOIN params p_model ON r.run_uuid = p_model.run_uuid AND p_model.key = 'model_type'
    LEFT JOIN params p_cl ON r.run_uuid = p_cl.run_uuid AND p_cl.key = 'cl_strategy'
    LEFT JOIN params p_agg ON r.run_uuid = p_agg.run_uuid AND p_agg.key = 'aggregation_strategy'
    LEFT JOIN params p_dp ON r.run_uuid = p_dp.run_uuid AND p_dp.key = 'dp_enabled'
    LEFT JOIN params p_lr ON r.run_uuid = p_lr.run_uuid AND p_lr.key = 'lr'
    LEFT JOIN params p_bs ON r.run_uuid = p_bs.run_uuid AND p_bs.key = 'batch_size'
    WHERE r.status = 'FINISHED'
    ORDER BY r.start_time DESC
    """
    df_runs = pd.read_sql_query(runs_query, conn)

    # 3. Fetch Latest Metrics
    metrics_query = """
    SELECT run_uuid, key, value FROM metrics
    WHERE key IN (
        'accuracy', 'loss', 'crucial_model_performance',
        'accuracy_class_0', 'accuracy_class_1', 'accuracy_class_2', 'accuracy_class_3', 'accuracy_class_4',
        'f1_class_0', 'f1_class_1', 'f1_class_2', 'f1_class_3', 'f1_class_4',
        'client_A_dataset_jsd', 'client_B_dataset_jsd', 'client_A_weight_drift', 'client_B_weight_drift',
        'model_quantized_bytes', 'communication_bytes'
    )
    """
    df_metrics = pd.read_sql_query(metrics_query, conn)
    latest_metrics = df_metrics.groupby(["run_uuid", "key"]).last().reset_index()
    pivoted_m = latest_metrics.pivot(index="run_uuid", columns="key", values="value").reset_index()

    df_full = pd.merge(df_runs, pivoted_m, on="run_uuid", how="left")

    # Format timestamps and durations
    df_full["duration_s"] = ((df_full["end_time"] - df_full["start_time"]) / 1000.0).round(1)
    df_full["start_dt"] = pd.to_datetime(df_full["start_time"], unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")

    # Generate Markdown Report
    os.makedirs("docs/reports", exist_ok=True)
    report_file = "docs/reports/mlflow_runs_inspection.md"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# FL-CL MLflow Full Runs Inspection & Standardization Scorecard\n\n")
        f.write(f"- **Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Total Finished Runs Audited**: `{len(df_full)}`\n")
        f.write(f"- **Database**: `{db_path}`\n\n")

        f.write("## 1. Experiment Registry Overview\n\n")
        f.write("| ID | Experiment Name | Total Finished Runs | Artifact Location |\n")
        f.write("|:---|:---|:---:|:---|\n")
        for _, exp in df_exp.iterrows():
            count = len(df_full[df_full["experiment_id"] == exp["experiment_id"]])
            f.write(f"| `{exp['experiment_id']}` | **{exp['name']}** | `{count}` | `{exp['artifact_location']}` |\n")
        f.write("\n---\n\n")

        f.write("## 2. Detailed Run Scorecard (Formatted by Experiment)\n\n")
        
        for exp_id in sorted(df_full["experiment_id"].unique()):
            exp_name = df_exp[df_exp["experiment_id"] == exp_id]["name"].values[0]
            sub_df = df_full[df_full["experiment_id"] == exp_id]
            f.write(f"### Experiment {exp_id}: {exp_name} ({len(sub_df)} Runs)\n\n")
            f.write("| Run ID | Model | CL Strategy | Aggregator | DP | Accuracy | Loss | Macro F1 | Duration | Benign Acc | SSH Acc | DoS Acc | Exfil Acc | Botnet Acc |\n")
            f.write("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

            for _, row in sub_df.iterrows():
                run_short = f"`{row['run_uuid'][:8]}`"
                model = row.get("model_type") or "N/A"
                cl = row.get("cl_strategy") or "N/A"
                agg = row.get("aggregation_strategy") or "N/A"
                dp = "ON" if str(row.get("dp_enabled")).lower() == "true" else "OFF"
                
                acc = f"{row['accuracy']*100:.2f}%" if pd.notnull(row.get("accuracy")) else "N/A"
                loss = f"{row['loss']:.4f}" if pd.notnull(row.get("loss")) else "N/A"
                f1 = f"{row['crucial_model_performance']*100:.2f}%" if pd.notnull(row.get("crucial_model_performance")) else "N/A"
                dur = f"{row['duration_s']:.0f}s" if pd.notnull(row.get("duration_s")) else "N/A"
                
                c0 = f"{row['accuracy_class_0']*100:.1f}%" if pd.notnull(row.get("accuracy_class_0")) else "—"
                c1 = f"{row['accuracy_class_1']*100:.1f}%" if pd.notnull(row.get("accuracy_class_1")) else "—"
                c2 = f"{row['accuracy_class_2']*100:.1f}%" if pd.notnull(row.get("accuracy_class_2")) else "—"
                c3 = f"{row['accuracy_class_3']*100:.1f}%" if pd.notnull(row.get("accuracy_class_3")) else "—"
                c4 = f"{row['accuracy_class_4']*100:.1f}%" if pd.notnull(row.get("accuracy_class_4")) else "—"

                f.write(f"| {run_short} | `{model}` | `{cl}` | `{agg}` | `{dp}` | **{acc}** | {loss} | {f1} | {dur} | {c0} | {c1} | {c2} | {c3} | {c4} |\n")
            f.write("\n")

    print(f"[SUCCESS] Exported detailed inspection of {len(df_full)} runs to {report_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLflow Active and Completed Run Diagnostics Inspector")
    _ = parser.parse_args()
    inspect_all_runs()
