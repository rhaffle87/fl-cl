"""
notifications.py — Telegram webhook notifications for FL-CL pipeline.

Sends run status updates (start, complete, fail) to a Telegram bot.
Used by the orchestrator to notify when experiments finish or error out.
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime


def escape_html(text: str) -> str:
    """Escapes special characters to be safe for Telegram HTML parse_mode."""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class TelegramNotifier:
    """Lightweight Telegram bot notifier (no external dependencies)."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and bool(chat_id)

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured Telegram chat.

        Returns True on success, False on failure (never raises).
        """
        if not self.enabled:
            return False

        url = self.API_URL.format(token=self.bot_token)
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[telegram] Warning: failed to send notification: {e}")
            return False

    def notify_start(self, experiment_name: str, rounds: int, config_summary: str = "", 
                     mlops_mode: str = "experimental", git_commit: str = "unknown"):
        """Notify that an FL-CL experiment has started with a professional HTML MLOps alert format."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        name_esc = escape_html(experiment_name)
        mode_esc = escape_html(mlops_mode.upper())
        rounds_esc = escape_html(str(rounds))
        commit_esc = escape_html(git_commit[:8] if git_commit else "unknown")
        time_esc = escape_html(timestamp)
        
        msg = (
            f"📊 <b>[MLOps Pipeline] FL-CL Training Initiated</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🔹 Environment:</b> <code>Proxmox-Testbed</code>\n"
            f"<b>🔹 Experiment:</b> <code>{name_esc}</code>\n"
            f"<b>🔹 MLOps Mode:</b> <code>{mode_esc}</code>\n"
            f"<b>🔹 Federated Rounds:</b> <code>{rounds_esc}</code>\n"
            f"<b>🔹 Git Commit:</b> <code>{commit_esc}</code>\n"
            f"<b>🔹 Started At:</b> <code>{time_esc}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if config_summary:
            config_esc = escape_html(config_summary)
            msg += f"⚙️ <b>Execution Parameters:</b>\n<pre>{config_esc}</pre>\n"
            
        return self.send(msg, parse_mode="HTML")

    def notify_complete(self, experiment_name: str, accuracy: float, loss: float,
                        class_accuracies: dict = None, duration_min: float = 0,
                        run_id: str = None, mlflow_uri: str = None, experiment_id: str = None):
        """Notify that an FL-CL experiment completed successfully with professional metrics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        name_esc = escape_html(experiment_name)
        acc_esc = escape_html(f"{accuracy * 100:.2f}%")
        loss_esc = escape_html(f"{loss:.4f}")
        time_esc = escape_html(timestamp)
        duration_esc = escape_html(f"{duration_min:.1f} minutes" if duration_min > 0 else "N/A")
        run_esc = escape_html(run_id[:8] if run_id else "N/A")
        
        msg = (
            f"🟢 <b>[MLOps Pipeline] FL-CL Training Completed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🔹 Environment:</b> <code>Proxmox-Testbed</code>\n"
            f"<b>🔹 Experiment:</b> <code>{name_esc}</code>\n"
            f"<b>🔹 Status:</b> <code>SUCCESS</code>\n\n"
            f"📊 <b>Global Evaluation Metrics:</b>\n"
            f"• <b>Overall Accuracy:</b> <code>{acc_esc}</code>\n"
            f"• <b>Final Aggregated Loss:</b> <code>{loss_esc}</code>\n"
            f"• <b>Total Duration:</b> <code>{duration_esc}</code>\n"
            f"• <b>MLflow Run ID:</b> <code>{run_esc}</code>\n\n"
        )
        
        if class_accuracies:
            names = {0: "Normal", 1: "Botnet", 2: "Exfil", 3: "SSH-BF", 4: "DoS"}
            msg += "📈 <b>Per-Class Accuracy Breakdown:</b>\n"
            for cls, acc in sorted(class_accuracies.items()):
                name = names.get(cls, f"Class {cls}")
                percent = acc * 100
                bar_len = int(acc * 10)
                bar = "█" * bar_len + "░" * (10 - bar_len)
                name_padded = f"{name:<8s}"
                msg += f"• <code>{escape_html(name_padded)}</code>: <code>{percent:6.2f}%</code> <code>[{bar}]</code>\n"
            msg += "\n"
            
        if run_id and mlflow_uri and experiment_id:
            base_uri = mlflow_uri.rstrip("/")
            run_url = f"{base_uri}/#/experiments/{experiment_id}/runs/{run_id}"
            msg += (
                f"🔗 <b>Dashboard Link:</b>\n"
                f"• <a href=\"{run_url}\">Open MLflow Dashboard</a>\n\n"
            )
            
        msg += (
            f"📅 <b>Completed At:</b> <code>{time_esc}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        return self.send(msg, parse_mode="HTML")

    def notify_failure(self, experiment_name: str, error: str, round_num: int = 0, duration_min: float = 0):
        """Notify that an FL-CL experiment failed with detailed diagnostics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        name_esc = escape_html(experiment_name)
        time_esc = escape_html(timestamp)
        
        round_info = f"• <b>Failed at Round:</b> <code>{round_num}</code>\n" if round_num > 0 else ""
        duration_info = f"• <b>Elapsed Time:</b> <code>{duration_min:.1f} minutes</code>\n" if duration_min > 0 else ""
        
        error_esc = escape_html(error[:800])
        msg = (
            f"🔴 <b>[MLOps Pipeline] FL-CL Training Failed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🔹 Environment:</b> <code>Proxmox-Testbed</code>\n"
            f"<b>🔹 Experiment:</b> <code>{name_esc}</code>\n"
            f"<b>🔹 Status:</b> <code>FAILED</code>\n"
            f"{round_info}"
            f"{duration_info}\n"
            f"💥 <b>Failure Diagnostics & Stacktrace:</b>\n"
            f"<pre>{error_esc}</pre>\n\n"
            f"📅 <b>Failed At:</b> <code>{time_esc}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        return self.send(msg, parse_mode="HTML")
