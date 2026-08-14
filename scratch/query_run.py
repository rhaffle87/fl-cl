import os
import mlflow
from mlflow.tracking import MlflowClient

def load_env(env_name: str = ".env"):
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

load_env()
tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(tracking_uri)

client = MlflowClient()
run_id = "b774d90b4a304dce9ca2393f0af2f4a9"
try:
    history = client.get_metric_history(run_id, "loss")
    print(f"Number of rounds logged for run {run_id}: {len(history)}")
    if history:
        steps = [h.step for h in history]
        print(f"Steps/Rounds: {steps}")
        print(f"Last loss: {history[-1].value} at step {history[-1].step}")
except Exception as e:
    print(f"Error querying history: {e}")
