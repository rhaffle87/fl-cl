import os
import sys
import mlflow
from mlflow.tracking import MlflowClient

# Initialize tracking URI from env
tracking_uri = "http://localhost:5000"
mlflow.set_tracking_uri(tracking_uri)

run_id = "82020f81b9064636aa8d49a5a22d18bf"
checkpoint_dir = f"/opt/mlflow-artifacts/checkpoints/{run_id}"

print(f"Checking files in local checkpoint directory: {checkpoint_dir}")
model_latest = os.path.join(checkpoint_dir, "model_latest.pt")
model_scripted = os.path.join(checkpoint_dir, "model_latest_scripted.pt")

if not os.path.exists(model_latest):
    print(f"Error: {model_latest} not found!")
    sys.exit(1)

client = MlflowClient()

# Check run status and metadata
try:
    run = client.get_run(run_id)
    print(f"Found run: {run_id} (Status: {run.info.status})")
except Exception as e:
    print(f"Error finding run {run_id}: {e}")
    sys.exit(1)

# Log artifacts to the run
print("Logging checkpoint artifacts to run...")
with mlflow.start_run(run_id=run_id):
    mlflow.log_artifact(model_latest, artifact_path="model")
    if os.path.exists(model_scripted):
        mlflow.log_artifact(model_scripted, artifact_path="model")
    print("[OK] Logged checkpoints as MLflow artifacts")

# Register model
print("Registering model to Model Registry...")
model_uri = f"runs:/{run_id}/model"
# Wait, since mlflow.pytorch.log_model wasn't run on this run, we can register the model version directly using client.create_model_version
# Wait, or we can use mlflow.register_model. Let's see if we can do client.create_model_version with the artifact path.
try:
    # First check if the registered model exists
    try:
        client.get_registered_model("CyberDefenseNet")
    except Exception:
        client.create_registered_model("CyberDefenseNet")
        
    model_version = client.create_model_version(
        name="CyberDefenseNet",
        source=f"runs:/{run_id}/model",
        run_id=run_id
    )
    print(f"[OK] Registered model version: {model_version.version}")
    
    # Update champion alias
    print("Setting alias 'champion' to version", model_version.version)
    client.set_registered_model_alias(
        name="CyberDefenseNet",
        alias="champion",
        version=str(model_version.version)
    )
    print("[OK] Champion alias updated!")
except Exception as e:
    print(f"Error registering model/alias: {e}")
    sys.exit(1)
