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
print("=== Querying Registered Model Aliases ===")
try:
    model = client.get_registered_model("CyberDefenseNet")
    print(f"Model Name: {model.name}")
    print(f"Tags: {model.tags}")
    print(f"Aliases in registered model: {model.aliases if hasattr(model, 'aliases') else 'No aliases attribute'}")
    
    # Try to resolve champion alias
    try:
        champion_ver = client.get_model_version_by_alias("CyberDefenseNet", "champion")
        print(f"[FOUND] Alias 'champion' points to Version: {champion_ver.version} (Run ID: {champion_ver.run_id})")
    except Exception as e:
        print(f"[NOT FOUND] Alias 'champion' failed: {e}")
        
except Exception as e:
    print(f"Error: {e}")
