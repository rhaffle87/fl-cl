# notifications.py — Telegram webhook notifications for FL-CL pipeline.
#
# Sends run status updates (start, complete, fail) to a Telegram bot.
# Used by the orchestrator to notify when experiments finish or error out.

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env_file():
    """Parse .env file if present in project root."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


load_env_file()


def escape_html(text: str) -> str:
    """Escapes special characters to be safe for Telegram HTML parse_mode."""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class TelegramNotifier:
    """Lightweight Telegram bot notifier (no external dependencies)."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(
        self, bot_token: str = None, chat_id: str = None, enabled: bool = True
    ):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

        # Disable notifications if placeholder values are used
        if (
            not self.bot_token
            or not self.chat_id
            or "YOUR_" in str(self.bot_token)
            or "YOUR_" in str(self.chat_id)
        ):
            self.enabled = False
        else:
            self.enabled = enabled

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured Telegram chat.

        Returns True on success, False on failure (never raises).
        """
        if not self.enabled:
            return False

        url = self.API_URL.format(token=self.bot_token)
        payload = json.dumps(
            {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            if e.code in (401, 404):
                self.enabled = False
            return False
        except Exception:
            return False

    def notify_start(
        self,
        experiment_name: str,
        rounds: int,
        config_summary: str = "",
        mlops_mode: str = "experimental",
        git_commit: str = "unknown",
    ):
        """Notify that an FL-CL experiment has started with a professional HTML MLOps alert format."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        name_esc = escape_html(experiment_name)
        mode_esc = escape_html(mlops_mode.upper())
        rounds_esc = escape_html(str(rounds))
        commit_esc = escape_html(git_commit[:8] if git_commit else "unknown")
        time_esc = escape_html(timestamp)

        msg = (
            f"<b>[MLOps Pipeline] FL-CL Training Initiated</b>\n"
            f"----------------------------------------\n"
            f"<b>Environment:</b> <code>Proxmox-Testbed</code>\n"
            f"<b>Experiment:</b> <code>{name_esc}</code>\n"
            f"<b>MLOps Mode:</b> <code>{mode_esc}</code>\n"
            f"<b>Federated Rounds:</b> <code>{rounds_esc}</code>\n"
            f"<b>Git Commit:</b> <code>{commit_esc}</code>\n"
            f"<b>Started At:</b> <code>{time_esc}</code>\n"
            f"----------------------------------------\n"
        )
        if config_summary:
            config_esc = escape_html(config_summary)
            msg += f"<b>Execution Parameters:</b>\n<pre>{config_esc}</pre>\n"

        return self.send(msg, parse_mode="HTML")

    def notify_complete(
        self,
        experiment_name: str,
        accuracy: float,
        loss: float,
        class_accuracies: dict = None,
        duration_min: float = 0,
        run_id: str = None,
        mlflow_uri: str = None,
        experiment_id: str = None,
    ):
        """Notify that an FL-CL experiment completed successfully with professional metrics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        name_esc = escape_html(experiment_name)
        acc_esc = escape_html(f"{accuracy * 100:.2f}%")
        loss_esc = escape_html(f"{loss:.4f}")
        time_esc = escape_html(timestamp)
        duration_esc = escape_html(
            f"{duration_min:.1f} minutes" if duration_min > 0 else "N/A"
        )
        run_esc = escape_html(run_id[:8] if run_id else "N/A")

        msg = (
            f"<b>[MLOps Pipeline] FL-CL Training Completed</b>\n"
            f"----------------------------------------\n"
            f"<b>Environment:</b> <code>Proxmox-Testbed</code>\n"
            f"<b>Experiment:</b> <code>{name_esc}</code>\n"
            f"<b>Status:</b> <code>SUCCESS</code>\n\n"
            f"<b>Global Evaluation Metrics:</b>\n"
            f"- <b>Overall Accuracy:</b> <code>{acc_esc}</code>\n"
            f"- <b>Final Aggregated Loss:</b> <code>{loss_esc}</code>\n"
            f"- <b>Total Duration:</b> <code>{duration_esc}</code>\n"
            f"- <b>MLflow Run ID:</b> <code>{run_esc}</code>\n\n"
        )

        if class_accuracies:
            names = {0: "Normal", 1: "Botnet", 2: "Exfil", 3: "SSH-BF", 4: "DoS"}
            msg += "<b>Per-Class Accuracy Breakdown:</b>\n"
            for cls, acc in sorted(class_accuracies.items()):
                name = names.get(cls, f"Class {cls}")
                percent = acc * 100
                bar_len = int(acc * 10)
                bar = "#" * bar_len + "." * (10 - bar_len)
                name_padded = f"{name:<8s}"
                msg += f"- <code>{escape_html(name_padded)}</code>: <code>{percent:6.2f}%</code> <code>[{bar}]</code>\n"
            msg += "\n"

        if run_id and mlflow_uri and experiment_id:
            base_uri = mlflow_uri.rstrip("/")
            run_url = f"{base_uri}/#/experiments/{experiment_id}/runs/{run_id}"
            msg += (
                f"<b>Dashboard Link:</b>\n"
                f'- <a href="{run_url}">Open MLflow Dashboard</a>\n\n'
            )

        msg += (
            f"<b>Completed At:</b> <code>{time_esc}</code>\n"
            f"----------------------------------------\n"
        )
        return self.send(msg, parse_mode="HTML")

    def notify_failure(
        self,
        experiment_name: str,
        error: str,
        round_num: int = 0,
        duration_min: float = 0,
    ):
        """Notify that an FL-CL experiment failed with detailed diagnostics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        name_esc = escape_html(experiment_name)
        time_esc = escape_html(timestamp)

        round_info = (
            f"- <b>Failed at Round:</b> <code>{round_num}</code>\n"
            if round_num > 0
            else ""
        )
        duration_info = (
            f"- <b>Elapsed Time:</b> <code>{duration_min:.1f} minutes</code>\n"
            if duration_min > 0
            else ""
        )

        error_esc = escape_html(error[:800])
        msg = (
            f"<b>[MLOps Pipeline] FL-CL Training Failed</b>\n"
            f"----------------------------------------\n"
            f"<b>Environment:</b> <code>Proxmox-Testbed</code>\n"
            f"<b>Experiment:</b> <code>{name_esc}</code>\n"
            f"<b>Status:</b> <code>FAILED</code>\n"
            f"{round_info}"
            f"{duration_info}\n"
            f"<b>Failure Diagnostics & Stacktrace:</b>\n"
            f"<pre>{error_esc}</pre>\n\n"
            f"<b>Failed At:</b> <code>{time_esc}</code>\n"
            f"----------------------------------------\n"
        )
        return self.send(msg, parse_mode="HTML")

    def notify_promotion(
        self, model_name: str, version: int, metrics: dict, rationale: str
    ):
        """Notify that a model has been promoted to Champion."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        model_esc = escape_html(model_name)
        ver_esc = escape_html(str(version))
        rat_esc = escape_html(rationale)
        time_esc = escape_html(timestamp)

        msg = (
            f"<b>[Model Governance] Champion Model Promoted</b>\n"
            f"----------------------------------------\n"
            f"<b>Model:</b> <code>{model_esc}</code>\n"
            f"<b>New Version:</b> <code>v{ver_esc}</code>\n"
            f"<b>Alias:</b> <code>champion</code> (Active in Production)\n"
            f"<b>Timestamp:</b> <code>{time_esc}</code>\n\n"
            f"<b>Gated Promotion Metrics:</b>\n"
        )
        for key, val in metrics.items():
            key_esc = escape_html(key)
            try:
                val_esc = escape_html(f"{float(val):.4f}")
            except (ValueError, TypeError):
                val_esc = escape_html(str(val))
            msg += f"- <b>{key_esc}:</b> <code>{val_esc}</code>\n"

        msg += (
            f"\n<b>Promotion Rationale:</b>\n"
            f"<pre>{rat_esc}</pre>\n"
            f"----------------------------------------\n"
        )
        return self.send(msg, parse_mode="HTML")

    def notify_promotion_failure(
        self,
        model_name: str,
        candidate_version: int,
        metrics: dict,
        failure_reason: str,
    ):
        """Notify that a model promotion gate failed."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        model_esc = escape_html(model_name)
        ver_esc = escape_html(str(candidate_version))
        reason_esc = escape_html(failure_reason)
        time_esc = escape_html(timestamp)

        msg = (
            f"<b>[Model Governance] Promotion Gate Failed</b>\n"
            f"----------------------------------------\n"
            f"<b>Model:</b> <code>{model_esc}</code>\n"
            f"<b>Candidate Version:</b> <code>v{ver_esc}</code>\n"
            f"<b>Action:</b> <code>Retaining Incumbent Champion</code>\n"
            f"<b>Timestamp:</b> <code>{time_esc}</code>\n\n"
            f"<b>Gated Candidate Metrics:</b>\n"
        )
        for key, val in metrics.items():
            key_esc = escape_html(key)
            try:
                val_esc = escape_html(f"{float(val):.4f}")
            except (ValueError, TypeError):
                val_esc = escape_html(str(val))
            msg += f"- <b>{key_esc}:</b> <code>{val_esc}</code>\n"

        msg += (
            f"\n<b>Failure Reason:</b>\n"
            f"<pre>{reason_esc}</pre>\n"
            f"----------------------------------------\n"
        )
        return self.send(msg, parse_mode="HTML")

    def notify_sweep_summary(
        self,
        sweep_name: str,
        total_runs: int,
        finished_runs: int,
        peak_accuracy: float,
        min_loss: float,
        peak_macro_f1: float,
        pareto_config: str = "1D-CNN + A-GEM + TrimmedMean",
        models_summary: dict = None,
        duration_min: float = 0,
        mlflow_uri: str = "http://10.10.130.10:5000",
    ):
        """Notify comprehensive summary for multi-run hyperparameter sweeps."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name_esc = escape_html(sweep_name)
        acc_esc = escape_html(f"{peak_accuracy * 100:.2f}%")
        loss_esc = escape_html(f"{min_loss:.4f}")
        f1_esc = escape_html(f"{peak_macro_f1 * 100:.2f}%")
        pareto_esc = escape_html(pareto_config)
        time_esc = escape_html(timestamp)
        dur_esc = escape_html(
            f"{duration_min:.1f} min" if duration_min > 0 else "Completed"
        )

        msg = (
            f"<b>[MLOps Sweep] Matrix Sweep Execution Summary</b>\n"
            f"----------------------------------------\n"
            f"<b>Environment:</b> <code>Proxmox-Cluster</code>\n"
            f"<b>Sweep Name:</b> <code>{name_esc}</code>\n"
            f"<b>Total Matrix Runs:</b> <code>{finished_runs}/{total_runs} (100% FINISHED)</code>\n"
            f"<b>Total Execution Time:</b> <code>{dur_esc}</code>\n\n"
            f"<b>Top Empirical Metrics:</b>\n"
            f"- <b>Peak Global Accuracy:</b> <code>{acc_esc}</code>\n"
            f"- <b>Lowest Convergence Loss:</b> <code>{loss_esc}</code>\n"
            f"- <b>Peak Macro F1 Score:</b> <code>{f1_esc}</code>\n"
            f"- <b>Recommended Pareto Frontier:</b> <code>{pareto_esc}</code>\n\n"
        )

        if models_summary:
            msg += "<b>Evaluated Backbone Distribution:</b>\n"
            for m_name, count in models_summary.items():
                m_esc = escape_html(m_name.upper())
                msg += f"- <code>{m_esc}</code>: <code>{count} combinations</code>\n"
            msg += "\n"

        if mlflow_uri:
            msg += f'<b>Tracking Dashboard:</b> <a href="{mlflow_uri}">{mlflow_uri}</a>\n\n'

        msg += (
            f"<b>Completed At:</b> <code>{time_esc}</code>\n"
            f"----------------------------------------\n"
        )
        return self.send(msg, parse_mode="HTML")
