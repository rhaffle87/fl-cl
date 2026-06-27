"""
notifications.py — Telegram webhook notifications for FL-CL pipeline.

Sends run status updates (start, complete, fail) to a Telegram bot.
Used by the orchestrator to notify when experiments finish or error out.

Usage:
    from notifications import TelegramNotifier
    notifier = TelegramNotifier(bot_token="...", chat_id="...")
    notifier.send("Run completed with 95% accuracy")
"""

import urllib.request
import urllib.parse
import json


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

    def notify_start(self, experiment_name: str, rounds: int, config_summary: str = ""):
        """Notify that an FL-CL experiment has started."""
        msg = (
            f"🚀 *FL-CL Experiment Started*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Name:* `{experiment_name}`\n"
            f"🔄 *Rounds:* {rounds}\n"
        )
        if config_summary:
            msg += f"⚙️ *Config:*\n```\n{config_summary}\n```\n"
        return self.send(msg)

    def notify_complete(self, experiment_name: str, accuracy: float, loss: float,
                        class_accuracies: dict = None, duration_min: float = 0):
        """Notify that an FL-CL experiment completed successfully."""
        msg = (
            f"✅ *FL-CL Experiment Complete*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Name:* `{experiment_name}`\n"
            f"📊 *Accuracy:* `{accuracy:.4f}`\n"
            f"📉 *Loss:* `{loss:.4f}`\n"
        )
        if duration_min > 0:
            msg += f"⏱ *Duration:* `{duration_min:.1f} min`\n"
        if class_accuracies:
            names = {0: "Normal", 1: "Botnet", 2: "Exfil", 3: "SSH-BF", 4: "DoS"}
            msg += "\n*Per-class:*\n"
            for cls, acc in sorted(class_accuracies.items()):
                name = names.get(cls, f"Class {cls}")
                bar = "█" * int(acc * 10) if acc >= 0 else "N/A"
                msg += f"  `{name:>8s}: {acc:.2f}` {bar}\n"
        return self.send(msg)

    def notify_failure(self, experiment_name: str, error: str, round_num: int = 0):
        """Notify that an FL-CL experiment failed."""
        msg = (
            f"❌ *FL-CL Experiment Failed*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Name:* `{experiment_name}`\n"
        )
        if round_num > 0:
            msg += f"🔄 *Failed at round:* {round_num}\n"
        msg += f"💥 *Error:*\n```\n{error[:500]}\n```"
        return self.send(msg)
