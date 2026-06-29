import os
import sys
import json
import requests
import argparse
from mlflow.tracking import MlflowClient

def load_env(env_path: str = ".env"):
    """Load environment variables from a .env file if it exists."""
    if not os.path.exists(env_path):
        # Resolve relative to project root if run from subdirectories
        resolved_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", env_path))
        if os.path.exists(resolved_path):
            env_path = resolved_path
        else:
            return
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

# Load local environment variables
load_env()

def generate_llm_analysis(run_id, final_metrics, lambda_ewc, rounds):
    """Queries the local LLM model via the Tailscale Ollama proxy."""
    endpoint = os.getenv("OLLAMA_ENDPOINT")
    key = os.getenv("OLLAMA_KEY")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b-base")

    if not endpoint or not key:
        print("[!] Warning: OLLAMA_ENDPOINT or OLLAMA_KEY is not set in .env. Skipping LLM report generation.")
        return None

    url = f"{endpoint.rstrip('/')}/api/generate"
    headers = {
        "x-fcl-key": key,
        "Content-Type": "application/json"
    }

    # Clean up metrics for readability in prompt
    formatted_metrics = {}
    for k, v in final_metrics.items():
        try:
            formatted_metrics[k] = round(float(v), 6)
        except (ValueError, TypeError):
            formatted_metrics[k] = v

    prompt = f"""
    You are an expert AI Security MLOps Analyzer assisting in evaluating a Federated Continual Learning (FL-CL) run.
    The goal is to detect threat simulations while ensuring the model does not suffer from catastrophic forgetting.

    Run Configuration:
    - MLflow Run ID: {run_id}
    - Total Rounds: {rounds}
    - Continual Learning Strategy: Avalanche Elastic Weight Consolidation (EWC)
    - EWC Lambda: {lambda_ewc}

    Final Aggregated Training Metrics:
    {json.dumps(formatted_metrics, indent=2)}

    Please write a structured evaluation report containing:
    1. **Executive Summary**: A brief, high-level evaluation of this experiment.
    2. **Convergence Analysis**: Assessment of global loss drop and overall validation accuracy.
    3. **Catastrophic Forgetting Assessment**: Analyze if newer tasks/threat classes (such as DoS, Botnets, or SSH Brute force) caused performance degradation in previously learned tasks (like Normal traffic or DNS Exfiltration).
    4. **MLOps Recommendations**: Concrete advice on hyperparameter tuning (e.g. should EWC lambda be adjusted?) or changes to training rounds for the next run.

    Keep the report professional, analytical, and formatted in clean markdown without any surrounding conversational text (just return the markdown report).
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_thread": 4
        }
    }


    try:
        print(f"[*] Querying local AI model '{model}' at '{endpoint}'...")
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            print(f"[!] Warning: Ollama API returned status code {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[!] Warning: Failed to query Ollama proxy: {e}")
        return None

def append_and_upload_report(run_dir, run_id, final_metrics, lambda_ewc, rounds, aggregator_ip):
    """Generates the LLM report, appends it to run_summary.md, and uploads to MLflow."""
    summary_path = os.path.join(run_dir, "run_summary.md")
    if not os.path.exists(summary_path):
        print(f"[!] Warning: Run summary file '{summary_path}' not found. Cannot append LLM analysis.")
        return False

    analysis = generate_llm_analysis(run_id, final_metrics, lambda_ewc, rounds)
    if not analysis:
        print("[!] LLM analysis generation skipped or failed. Run summary remains unchanged.")
        return False

    # Get model name again for heading reference
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b-base")
    print(f"[*] Appending local AI analysis ({model}) to {summary_path}...")
    try:
        with open(summary_path, "a") as f:
            f.write("\n---\n\n")
            f.write(f"## Local AI Threat Analysis ({model})\n\n")
            f.write(analysis)
            f.write("\n")
    except Exception as e:
        print(f"[!] Failed to write to {summary_path}: {e}")
        return False

    # Upload to remote MLflow dashboard via MlflowClient
    tracking_uri = f"http://{aggregator_ip}:5000"
    print(f"[*] Connecting to remote MLflow tracker at {tracking_uri}...")
    try:
        import mlflow
        mlflow.set_tracking_uri(tracking_uri)
        os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
        client = MlflowClient(tracking_uri=tracking_uri)
        print(f"[*] Uploading updated 'run_summary.md' as artifact to MLflow run '{run_id}'...")
        client.log_artifact(run_id, summary_path)
        print("[OK] Artifact successfully registered in MLflow dashboard.")
        return True
    except Exception as e:
        print(f"[!] Warning: Failed to upload artifact to MLflow: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate local LLM analysis report and upload to MLflow.")
    parser.add_argument("--run-dir", required=True, help="Path to the run export directory containing run_summary.md")
    parser.add_argument("--run-id", required=True, help="Active MLflow Run ID")
    parser.add_argument("--metrics-json", required=True, help="JSON string representing final metrics dictionary")
    parser.add_argument("--lambda-ewc", type=float, default=0.1, help="EWC lambda configuration")
    parser.add_argument("--rounds", type=int, default=100, help="Total training rounds")
    parser.add_argument("--ip", default="10.10.130.10", help="Aggregator IP address")
    args = parser.parse_args()

    try:
        metrics = json.loads(args.metrics_json)
    except Exception as e:
        print(f"[!] Error parsing metrics JSON string: {e}")
        sys.exit(1)

    success = append_and_upload_report(
        run_dir=args.run_dir,
        run_id=args.run_id,
        final_metrics=metrics,
        lambda_ewc=args.lambda_ewc,
        rounds=args.rounds,
        aggregator_ip=args.ip
    )
    sys.exit(0 if success else 1)
