"""
notifications.py — Telegram webhook notifications for FL-CL pipeline.

Sends run status updates (start, complete, fail) to a Telegram bot.
Used by the orchestrator to notify when experiments finish or error out.
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime


class TelegramNotifier:
    """Lightweight Telegram bot notifier (no external dependencies)."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and bool(chat_id)

    def send(self, message: str, parse_mode: str = "Markdown") -> bool:
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
        """Notify that an FL-CL experiment has started with a professional MLOps alert format."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        msg = (
            f"🚀 *[RUNNING] FL-CL Pipeline Start Alert*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 *Experiment:* `{experiment_name}`\n"
            f"🔹 *MLOps Mode:* `{mlops_mode.upper()}`\n"
            f"🔹 *Rounds:* `{rounds}`\n"
            f"🔹 *Git Commit:* `{git_commit[:8]}`\n"
            f"🔹 *Timestamp:* `{timestamp}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if config_summary:
            msg += f"⚙️ *Configuration Parameters:*\n```\n{config_summary}\n```\n"
            
        return self.send(msg)

    def notify_complete(self, experiment_name: str, accuracy: float, loss: float,
                        class_accuracies: dict = None, duration_min: float = 0,
                        run_id: str = None, mlflow_uri: str = None, experiment_id: str = None):
        """Notify that an FL-CL experiment completed successfully with professional metrics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        msg = (
            f"✅ *[SUCCESS] FL-CL Pipeline Completion Alert*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 *Experiment:* `{experiment_name}`\n"
            f"🔹 *Accuracy:* `{accuracy:.4f}` (`{accuracy*100:.2f}%`)\n"
            f"🔹 *Loss:* `{loss:.4f}`\n"
        )
        
        if duration_min > 0:
            msg += f"🔹 *Duration:* `{duration_min:.1f} minutes`\n"
            
        if run_id:
            msg += f"🔹 *MLflow Run ID:* `{run_id[:8]}...`\n"
            if mlflow_uri and experiment_id:
                base_uri = mlflow_uri.rstrip("/")
                run_url = f"{base_uri}/#/experiments/{experiment_id}/runs/{run_id}"
                msg += f"🔗 [Open MLflow Dashboard]({run_url})\n"
                
        msg += f"🔹 *Timestamp:* `{timestamp}`\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if class_accuracies:
            names = {0: "Normal", 1: "Botnet", 2: "Exfil", 3: "SSH-BF", 4: "DoS"}
            msg += "*📊 Per-Class Accuracy Evaluation:*\n"
            for cls, acc in sorted(class_accuracies.items()):
                name = names.get(cls, f"Class {cls}")
                percent = acc * 100
                bar_len = int(acc * 10)
                bar = "█" * bar_len + "░" * (10 - bar_len)
                msg += f"• `{name:>8s}`: `{percent:6.2f}%` `[{bar}]`\n"
                
        return self.send(msg)

    def notify_failure(self, experiment_name: str, error: str, round_num: int = 0, duration_min: float = 0):
        """Notify that an FL-CL experiment failed with detailed diagnostics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        msg = (
            f"❌ *[FAILED] FL-CL Pipeline Failure Alert*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 *Experiment:* `{experiment_name}`\n"
        )
        if round_num > 0:
            msg += f"🔹 *Failed at Round:* `{round_num}`\n"
        if duration_min > 0:
            msg += f"🔹 *Elapsed Time:* `{duration_min:.1f} minutes`\n"
            
        msg += (
            f"🔹 *Timestamp:* `{timestamp}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💥 *Error Stacktrace:*\n"
            f"```\n{error[:500]}\n```"
        )
        return self.send(msg)
