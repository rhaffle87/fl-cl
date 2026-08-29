"""
tools/audit_mlflow_standardization.py — Deep audit and standardization check for all MLflow runs in SQLite DB.
"""

import sqlite3
import json
import os
import sys

def audit_mlflow():
    db_path = "/root/mlflow.db" if os.path.exists("/root/mlflow.db") else "mlflow.db"
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return None

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    report = {
        "experiments": [],
        "total_runs": 0,
        "finished_runs": 0,
        "abnormal_runs": [],
        "missing_params": [],
        "missing_metrics": [],
        "standardization_score": 100.0,
        "matrix_runs_count": 0,
        "by_model": {},
        "by_cl": {},
        "by_agg": {}
    }

    # 1. Audit Experiments
    cur.execute("SELECT experiment_id, name, artifact_location, lifecycle_stage FROM experiments")
    for row in cur.fetchall():
        report["experiments"].append({
            "id": row[0], "name": row[1], "artifact_loc": row[2], "stage": row[3]
        })

    # 2. Total & Status Audit
    cur.execute("SELECT run_uuid, experiment_id, status, start_time, end_time FROM runs")
    runs = cur.fetchall()
    report["total_runs"] = len(runs)

    for r in runs:
        run_id, exp_id, status, start, end = r
        if status == "FINISHED":
            report["finished_runs"] += 1
        else:
            report["abnormal_runs"].append({
                "run_id": run_id, "exp_id": exp_id, "status": status
            })

    # 3. Parameter Alignment Check
    required_params = ["model_type", "cl_strategy", "aggregation_strategy"]
    cur.execute("SELECT run_uuid, key, value FROM params")
    params_by_run = {}
    for r_id, k, v in cur.fetchall():
        if r_id not in params_by_run:
            params_by_run[r_id] = {}
        params_by_run[r_id][k] = v

    for r in runs:
        r_id = r[0]
        p = params_by_run.get(r_id, {})
        for req in required_params:
            if req not in p:
                report["missing_params"].append({"run_id": r_id, "missing": req})
                break

    # 4. Metrics Alignment Check
    cur.execute("SELECT run_uuid, key, value FROM metrics")
    metrics_by_run = {}
    for r_id, k, v in cur.fetchall():
        if r_id not in metrics_by_run:
            metrics_by_run[r_id] = {}
        metrics_by_run[r_id][k] = v

    # 5. Categorize Matrix Runs
    for r_id, p in params_by_run.items():
        m_type = p.get("model_type")
        cl = p.get("cl_strategy")
        agg = p.get("aggregation_strategy")
        
        if m_type:
            report["by_model"][m_type] = report["by_model"].get(m_type, 0) + 1
        if cl:
            report["by_cl"][cl] = report["by_cl"].get(cl, 0) + 1
        if agg:
            report["by_agg"][agg] = report["by_agg"].get(agg, 0) + 1

    # Compute score
    deductions = len(report["abnormal_runs"]) * 1.5 + len(report["missing_params"]) * 0.5
    report["standardization_score"] = max(0.0, 100.0 - deductions)

    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    audit_mlflow()
