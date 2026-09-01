# validate_promotion.py — CI/CD Automated Model Validation Gate and Champion Promotion Utility.
#
# Queries MLflow for the latest registered model version under the 'challenger' alias,
# runs the validation gate (tools/validate_model.py) locally or remotely on defender nodes,
# and promotes the version to the 'champion' alias if per-class F1 and accuracy bounds pass.
#
# Usage:
# python3 tools/validate_promotion.py [--model-name CyberDefenseNet] [--mlflow-uri http://10.10.130.10:5000]

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Standard path resolution
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "src" / "defender"))
sys.path.insert(0, str(repo_root / "src" / "aggregator"))

import mlflow

from src.notifications import TelegramNotifier


def load_env(env_name: str = ".env"):
    """Load environment variables from .env searching upward from the script directory."""
    current_dir = Path(__file__).resolve().parent
    while True:
        env_path = current_dir / env_name
        if env_path.exists():
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
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent


# Load environment variables
load_env()


def get_git_key_path():
    """Find default private key location on Windows/Linux."""
    env_path = os.environ.get("SSH_KEY_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    home = os.path.expanduser("~")
    for name in ["id_rsa", "id_ed25519"]:
        p = os.path.join(home, ".ssh", name)
        if os.path.exists(p):
            return p
    return None


def run_remote_cmd(ip, command, key_path=None):
    """Run ssh command on defender node."""
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5"]
    if key_path:
        ssh_cmd += ["-i", key_path]
    ssh_cmd += [f"root@{ip}", command]
    return subprocess.run(ssh_cmd, capture_output=True, text=True)


def scp_file_to_remote(ip, local_path, remote_path, key_path=None):
    """SCP file to defender node."""
    scp_cmd = ["scp", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5"]
    if key_path:
        scp_cmd += ["-i", key_path]
    scp_cmd += [str(local_path), f"root@{ip}:{remote_path}"]
    return subprocess.run(scp_cmd, capture_output=True, text=True)


def safe_print(text):
    """Print text safely, replacing characters that cannot be encoded by stdout."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "ascii"
        encoded = text.encode(encoding, errors="replace")
        decoded = encoded.decode(encoding)
        print(decoded)


def format_validation_logs_to_markdown(
    validation_output, version_num, validation_passed
):
    summary = f"### Model Version v{version_num} Validation Report\n\n"

    lines = validation_output.split("\n")
    overall_acc = "N/A"
    avg_loss = "N/A"
    total_samples = "N/A"
    checkpoint_path = "N/A"
    flows_dir = "N/A"

    per_class_rows = []
    confusion_matrix_lines = []
    in_per_class = False
    in_confusion = False
    status_msg = ""

    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue

        if "Loading checkpoint:" in line_strip:
            checkpoint_path = line_strip.split("Loading checkpoint:")[-1].strip()
        elif "Loading flows from:" in line_strip:
            flows_dir = line_strip.split("Loading flows from:")[-1].strip()
        elif "Overall Accuracy:" in line_strip:
            overall_acc = line_strip.split(":")[-1].strip()
        elif "Average Loss:" in line_strip:
            avg_loss = line_strip.split(":")[-1].strip()
        elif "Total Samples:" in line_strip:
            total_samples = line_strip.split(":")[-1].strip()
        elif "Per-class Validation:" in line_strip:
            in_per_class = True
            in_confusion = False
        elif "Confusion Matrix:" in line_strip:
            in_per_class = False
            in_confusion = True
        elif "VALIDATION PASSED" in line_strip or "VALIDATION FAILED" in line_strip:
            status_msg = line_strip
            in_per_class = False
            in_confusion = False
        else:
            if in_per_class:
                if "---" in line_strip or "Class" in line_strip:
                    continue
                parts = line_strip.split()
                if len(parts) >= 6:
                    per_class_rows.append(parts)
            elif in_confusion:
                confusion_matrix_lines.append(line)

    # Build Overall Metrics Table
    summary += "#### Overall Metrics\n"
    summary += "| Metric | Value |\n"
    summary += "| :--- | :--- |\n"
    status_emoji = "**PASS**" if validation_passed else "**FAIL**"
    summary += f"| **Validation Status** | {status_emoji} |\n"
    summary += f"| **Overall Accuracy** | `{overall_acc}` |\n"
    summary += f"| **Average Loss** | `{avg_loss}` |\n"
    summary += f"| **Total Samples** | `{total_samples}` |\n"
    summary += f"| **Checkpoint** | `{checkpoint_path}` |\n"
    summary += f"| **Flows Source** | `{flows_dir}` |\n\n"

    # Build Per-Class Table
    if per_class_rows:
        summary += "#### Per-Class Performance\n"
        summary += "| Class | Accuracy | F1 Score | Threshold | Status | Samples |\n"
        summary += "| :--- | :---: | :---: | :---: | :---: | :---: |\n"
        for row in per_class_rows:
            if len(row) >= 6:
                cls_name = " ".join(row[:-5])
                acc, f1, thresh, status, samples = (
                    row[-5],
                    row[-4],
                    row[-3],
                    row[-2],
                    row[-1],
                )
                status_fmt = (
                    "**PASS**"
                    if status == "PASS"
                    else "**FAIL**" if status == "FAIL" else f"**{status}**"
                )
                summary += f"| **{cls_name}** | {acc} | {f1} | {thresh} | {status_fmt} | {samples} |\n"
        summary += "\n"

    # Build Confusion Matrix Code Block
    if confusion_matrix_lines:
        summary += "#### Confusion Matrix\n"
        summary += "```text\n"
        summary += "\n".join(confusion_matrix_lines).strip() + "\n"
        summary += "```\n\n"

    if status_msg:
        summary += f"**Conclusion**: `{status_msg}`\n"

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="CI/CD Model Promotion Gate & Challenger Validation"
    )
    parser.add_argument(
        "--model-name",
        default="CyberDefenseNet",
        help="Registered model name in MLflow (default: CyberDefenseNet)",
    )
    parser.add_argument(
        "--mlflow-uri",
        default="http://10.10.130.10:5000",
        help="MLflow Tracking Server URI",
    )
    parser.add_argument(
        "--defender-ip",
        default="10.10.130.11",
        help="Defender VM IP for validation run",
    )
    parser.add_argument(
        "--flows-dir",
        default="/mnt/ramdisk/flows",
        help="Flow CSV folder on defender ramdisk",
    )
    args = parser.parse_args()

    # Load notifications credentials
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    notifier = TelegramNotifier(
        tg_token, tg_chat_id, enabled=bool(tg_token and tg_chat_id)
    )

    # Configure MLflow
    mlflow_uri = os.environ.get("MLFLOW_TRACKING_URI", args.mlflow_uri)
    mlflow.set_tracking_uri(mlflow_uri)
    client = mlflow.tracking.MlflowClient()

    print(f"[CI/CD] Querying MLflow registry at: {mlflow_uri}")
    try:
        challenger_version = client.get_model_version_by_alias(
            args.model_name, "challenger"
        )
    except Exception as e:
        print(f"[CI/CD] No candidate version with alias 'challenger' found: {e}")
        print("[CI/CD] Nothing to validate. Exiting.")
        sys.exit(0)

    version_num = challenger_version.version
    run_id = challenger_version.run_id
    print(
        f"[CI/CD] Found candidate 'challenger' Model Version: v{version_num} (Run ID: {run_id})"
    )

    # Download scripted TorchScript artifact
    print("[CI/CD] Downloading candidate TorchScript model from MLflow...")
    temp_dir = Path("/tmp/candidate_download")
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        artifact_path = client.download_artifacts(
            run_id=run_id, path="model/model_latest_scripted.pt", dst_path=str(temp_dir)
        )
    except Exception as e:
        print(f"[CI/CD] Error downloading scripted artifact: {e}")
        try:
            artifact_path = client.download_artifacts(
                run_id=run_id, path="model/model_latest.pt", dst_path=str(temp_dir)
            )
        except Exception as e2:
            print(
                f"[CI/CD] Critical error: failed to download model weights from MLflow: {e2}"
            )
            sys.exit(1)

    print(f"[CI/CD] Downloaded model path: {artifact_path}")

    # Determine execution environment (local on defender vs remote over SSH)
    is_local_defender = (
        os.path.exists(args.flows_dir)
        and (repo_root / "tools" / "validate_model.py").exists()
    )
    key_path = get_git_key_path()

    validation_passed = False
    validation_output = ""

    if is_local_defender:
        print("[CI/CD] Running validation locally on defender node...")
        local_val_script = str(repo_root / "tools" / "validate_model.py")
        run_cmd = [
            sys.executable,
            local_val_script,
            "--checkpoint",
            artifact_path,
            "--flows-dir",
            args.flows_dir,
        ]
        result = subprocess.run(run_cmd, capture_output=True, text=True)
        validation_output = result.stdout + "\n" + result.stderr
        validation_passed = result.returncode == 0
    else:
        print(
            f"[CI/CD] Transferring checkpoint and running validation remotely on defender ({args.defender_ip})..."
        )
        remote_dest = "/tmp/candidate_scripted.pt"

        # SCP checkpoint to defender
        scp_res = scp_file_to_remote(
            args.defender_ip, artifact_path, remote_dest, key_path=key_path
        )
        if scp_res.returncode != 0:
            print(f"[CI/CD] SCP checkpoint transfer failed:\n{scp_res.stderr}")
            sys.exit(1)

        # SCP validate_model.py to defender
        local_script = str(repo_root / "tools" / "validate_model.py")
        scp_script_res = scp_file_to_remote(
            args.defender_ip, local_script, "~/validate_model.py", key_path=key_path
        )
        if scp_script_res.returncode != 0:
            print(
                f"[CI/CD] SCP validate_model.py transfer failed:\n{scp_script_res.stderr}"
            )
            sys.exit(1)

        # Run validate_model.py on defender
        remote_cmd = f"~/fl-cl-env/bin/python3 ~/validate_model.py --checkpoint {remote_dest} --flows-dir {args.flows_dir}"
        result = run_remote_cmd(args.defender_ip, remote_cmd, key_path=key_path)
        validation_output = result.stdout + "\n" + result.stderr
        validation_passed = result.returncode == 0

    print("\n" + "=" * 62)
    print("                    VALIDATION LOGS")
    print("=" * 62)
    safe_print(validation_output.strip())
    print("=" * 62)

    eval_metrics = {"run_id": run_id, "tracking_uri": mlflow_uri}
    for line in validation_output.split("\n"):
        if "Overall Accuracy:" in line:
            try:
                eval_metrics["overall_accuracy"] = float(line.split(":")[-1].strip())
            except ValueError:
                pass
        if "Average Loss:" in line:
            try:
                eval_metrics["average_loss"] = float(line.split(":")[-1].strip())
            except ValueError:
                pass

    md_desc = format_validation_logs_to_markdown(
        validation_output, version_num, validation_passed
    )

    if validation_passed:
        print(
            f"\n[CI/CD] SUCCESS: Promoting model version {version_num} to 'champion' alias..."
        )
        client.set_registered_model_alias(
            name=args.model_name, alias="champion", version=str(version_num)
        )

        success_desc = f"**Model version v{version_num} promoted to 'champion' via CI/CD Pipeline**.\n\n{md_desc}"
        client.update_model_version(
            name=args.model_name, version=str(version_num), description=success_desc
        )

        notifier.notify_promotion(
            model_name=args.model_name,
            version=int(version_num),
            metrics=eval_metrics,
            rationale=f"Model Version v{version_num} passed all validation thresholds on production flow dataset.",
        )
        sys.exit(0)
    else:
        print(
            f"\n[CI/CD] FAIL: Model version {version_num} failed validation thresholds."
        )
        client.set_tag(run_id, "validation_status", "FAILED")

        failure_desc = f"**Model version v{version_num} failed validation via CI/CD Pipeline**.\n\n{md_desc}"
        client.update_model_version(
            name=args.model_name, version=str(version_num), description=failure_desc
        )

        notifier.notify_promotion_failure(
            model_name=args.model_name,
            candidate_version=int(version_num),
            metrics=eval_metrics,
            failure_reason="One or more per-class validation metrics fell below acceptable production thresholds.",
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
