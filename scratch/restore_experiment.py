import sqlite3
import os

db_paths = [
    '/root/mlflow.db',
    '/root/mlflow/mlflow.db',
    '/opt/mlflow/mlflow.db',
    'mlflow.db'
]

db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    # default to /root/mlflow.db if none exist
    db_path = '/root/mlflow.db'

print(f"Opening database: {db_path}")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check if experiments table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments';")
if not cur.fetchone():
    print("Error: experiments table not found in this database.")
    conn.close()
    exit(1)

# Get all experiments
cur.execute('SELECT experiment_id, name, lifecycle_stage FROM experiments')
rows = cur.fetchall()
print("Current Experiments in Database:")
for row in rows:
    print(f"  ID: {row[0]}, Name: {row[1]}, Stage: {row[2]}")

# Restore deleted experiments
print("\nRestoring experiments 'FL-CL-CyberDefense' and 'FL-CL-EWC-Baseline' to active stage...")
cur.execute("UPDATE experiments SET lifecycle_stage = 'active' WHERE name IN ('FL-CL-CyberDefense', 'FL-CL-EWC-Baseline')")
restored_count = cur.rowcount
print(f"Restored {restored_count} experiments.")

# Restore associated runs
cur.execute("UPDATE runs SET lifecycle_stage = 'active' WHERE experiment_id IN (SELECT experiment_id FROM experiments WHERE name IN ('FL-CL-CyberDefense', 'FL-CL-EWC-Baseline'))")
restored_runs = cur.rowcount
print(f"Restored {restored_runs} associated runs.")

conn.commit()

print("\nAfter Restoration:")
cur.execute('SELECT experiment_id, name, lifecycle_stage FROM experiments')
for row in cur.fetchall():
    print(f"  ID: {row[0]}, Name: {row[1]}, Stage: {row[2]}")

conn.close()
