"""
src/aggregator/alerts.py — Real-Time Incident & Governance Alert Dispatcher (Telegram)

Dispatches real-time security alerts via Telegram Bot API using Python standard
library (urllib.request) with zero external dependencies and strictly no emoji characters.
Credentials are automatically resolved from environment variables or the project-root .env file.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
    except Exception as e:
        print(f"[alerts] Warning: Failed to parse .env file: {e}")


# Load environment variables on import
load_env_file()


def get_telegram_config():
    """Retrieve Telegram credentials from environment."""
    return {
        "telegram_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
    }


def escape_html(text: str) -> str:
    """Escapes special characters for safe Telegram HTML formatting."""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Send message via Telegram Bot API without emojis."""
    if not token or not chat_id or "YOUR_TELEGRAM" in token:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        print(f"[alerts] Telegram dispatch error: {e}")
        return False


def send_alert(title: str, body: str, level: str = "INFO") -> bool:
    """
    Dispatch clean textual alert to Telegram (no emoji).
    """
    cfg = get_telegram_config()
    level_tag = f"[{level.upper()}]"
    title_esc = escape_html(title)
    body_esc = escape_html(body)
    tg_text = f"<b>{level_tag} FL-CL: {title_esc}</b>\n\n{body_esc}"

    if cfg["telegram_token"] and cfg["telegram_chat_id"]:
        return send_telegram_message(cfg["telegram_token"], cfg["telegram_chat_id"], tg_text)
    return False


def send_byzantine_alert(client_id: str, anomaly_type: str, weight_drift: float, strategy: str) -> bool:
    """Alert on Byzantine parameter poisoning or anomaly detection."""
    title = f"Byzantine Attack Detected on Client {client_id}"
    body = (
        f"- Anomaly Type: {anomaly_type}\n"
        f"- L2 Parameter Drift: {weight_drift:.4f}\n"
        f"- Defense Strategy: {strategy} (Isolation Active)"
    )
    return send_alert(title, body, level="CRITICAL")


def send_promotion_alert(model_name: str, version: int, metrics: dict) -> bool:
    """Alert on autonomous MLOps Champion promotion."""
    title = f"New Production Champion Promoted: {model_name} (v{version})"
    metrics_str = "\n".join([f"- {k}: {v}" for k, v in metrics.items()])
    body = f"Model checkpoint successfully passed all validation gates.\n\n{metrics_str}"
    return send_alert(title, body, level="SUCCESS")


def send_drift_alert(client_id: str, round_num: int, jsd_score: float, threshold: float = 0.60) -> bool:
    """Alert on JSD covariate shift data quality gate rejection."""
    title = f"Data Quality Gate Tripped (Client {client_id})"
    body = (
        f"- Federated Round: {round_num}\n"
        f"- JSD Divergence: {jsd_score:.4f} (Threshold: {threshold:.2f})\n"
        f"- Action: Local training batch skipped & snapshotted to quarantine."
    )
    return send_alert(title, body, level="WARNING")


def send_sweep_alert(
    sweep_name: str,
    total_runs: int,
    peak_acc: float,
    min_loss: float,
    peak_f1: float,
    pareto_point: str = "1D-CNN + A-GEM + TrimmedMean",
) -> bool:
    """Alert on completed hyperparameter sweep."""
    title = f"Sweep Completed: {sweep_name}"
    body = (
        f"- Total Evaluated Runs: {total_runs} (100% Finished)\n"
        f"- Peak Accuracy: {peak_acc * 100:.2f}%\n"
        f"- Minimum Loss: {min_loss:.4f}\n"
        f"- Peak Macro F1: {peak_f1 * 100:.2f}%\n"
        f"- Optimal Pareto Frontier: {pareto_point}\n"
        f"- Tracking Dashboard: http://10.10.130.10:5000"
    )
    return send_alert(title, body, level="SUCCESS")

