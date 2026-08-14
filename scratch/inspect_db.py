import os
import sqlite3
import subprocess

key_path = r"C:\Users\Rafli Alif\.ssh\id_ed25519"
aggregator_ip = "10.10.130.10"
local_db = "mlflow_temp_inspect.db"

# 1. Back up database remotely
print("[*] Backing up remote MLflow database...")
backup_cmd = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no root@{aggregator_ip} "python3 -c \\"import sqlite3; src = sqlite3.connect(\'/root/mlflow.db\'); dst = sqlite3.connect(\'/tmp/mlflow_backup.db\'); src.backup(dst); dst.close(); src.close()\\""'
subprocess.run(backup_cmd, shell=True, check=True)

# 2. Download backup via SCP
print("[*] Downloading remote MLflow database backup...")
scp_cmd = f'scp -i "{key_path}" -o StrictHostKeyChecking=no root@{aggregator_ip}:/tmp/mlflow_backup.db "{local_db}"'
subprocess.run(scp_cmd, shell=True, check=True)

# 3. Clean up remote backup
cleanup_remote_cmd = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no root@{aggregator_ip} "rm -f /tmp/mlflow_backup.db"'
subprocess.run(cleanup_remote_cmd, shell=True, check=True)

# 4. Connect and inspect
conn = sqlite3.connect(local_db)
cur = conn.cursor()

# Get latest run
cur.execute("SELECT run_uuid, name, start_time FROM runs ORDER BY start_time DESC LIMIT 1")
run_row = cur.fetchone()
if not run_row:
    print("[!] No runs found.")
    conn.close()
    sys.exit(1)

run_id, run_name, start_time = run_row
print(f"[*] Latest run ID: {run_id} ({run_name}) started at {start_time}")

# Get all unique keys logged in this run and their step ranges
cur.execute("SELECT key, COUNT(*), MIN(step), MAX(step), MIN(value), MAX(value) FROM metrics WHERE run_uuid = ? GROUP BY key", (run_id,))
print("\nMetrics summary in DB:")
print("Key | Count | Min Step | Max Step | Min Value | Max Value")
print("-" * 70)
for row in cur.fetchall():
    print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")

# Get best_loss, best_round, final_best_loss, final_best_round specific values
cur.execute("SELECT key, value, step FROM metrics WHERE run_uuid = ? AND key IN ('best_loss', 'best_round', 'final_best_loss', 'final_best_round') ORDER BY step ASC", (run_id,))
print("\nSpecific best metrics logged:")
for row in cur.fetchall():
    print(f"  {row[0]} = {row[1]} at step {row[2]}")

conn.close()
if os.path.exists(local_db):
    os.remove(local_db)
