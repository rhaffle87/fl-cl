# src/aggregator/sheets_sync.py — Google Spreadsheet Webhook Integration (Option 2).
#
# Asynchronously pushes real-time federated learning round telemetry, benchmark tables,
# and champion promotion governance events to Google Sheets via a Google Apps Script WebApp.

import json
import threading
import urllib.error
import urllib.request
from typing import Any, Dict, List

try:
    from logger import get_logger

    _log = get_logger("sheets_sync")
except ImportError:
    try:
        from src.logger import get_logger

        _log = get_logger("sheets_sync")
    except ImportError:
        import logging

        _log = logging.getLogger("sheets_sync")


def _post_json(url: str, payload: Dict[str, Any], timeout: float = 12.0) -> bool:
    """Send JSON POST request to Google Apps Script Webhook with full redirect support."""
    if not url:
        return False
    try:
        import requests

        resp = requests.post(url, json=payload, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return True
        elif resp.status_code == 401:
            _log.error(
                "[sheets_sync] Error 401 Unauthorized: Ensure Web App deployment access is set to 'Anyone' in Google Apps Script."
            )
            return False
        else:
            _log.info(
                f"[sheets_sync] Webhook returned status {resp.status_code}: {resp.text[:200]}"
            )
            return False
    except ImportError:
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status in (200, 302)
        except Exception as e:
            _log.error(f"[sheets_sync] Warning: Webhook dispatch error: {e}")
            return False
    except Exception as e:
        _log.error(f"[sheets_sync] Warning: Webhook dispatch error: {e}")
        return False


def dispatch_async(url: str, payload: Dict[str, Any]) -> None:
    """Fire-and-forget asynchronous dispatch in a daemon thread."""
    if not url:
        return
    t = threading.Thread(target=_post_json, args=(url, payload), daemon=True)
    t.start()


def send_round_metric(
    webhook_url: str,
    server_round: int,
    loss: float,
    accuracy: float,
    metrics: Dict[str, Any],
    strategy_name: str = "FedAvg",
    model_type: str = "cnn",
) -> None:
    """
    Dispatch single-round evaluation metrics to Google Sheets.
    """
    if not webhook_url:
        return

    payload = {
        "action": "round_metric",
        "sheet": "Live_Rounds",
        "data": {
            "round": int(server_round),
            "loss": round(float(loss), 4),
            "accuracy_pct": round(
                float(accuracy) * (100.0 if float(accuracy) <= 1.0 else 1.0), 2
            ),
            "macro_f1": round(
                float(
                    metrics.get(
                        "crucial_model_performance", metrics.get("macro_f1", 0.0)
                    )
                ),
                4,
            ),
            "f1_normal_0": round(float(metrics.get("f1_class_0", -1.0)), 4),
            "f1_botnet_1": round(float(metrics.get("f1_class_1", -1.0)), 4),
            "f1_exfil_2": round(float(metrics.get("f1_class_2", -1.0)), 4),
            "f1_bruteforce_3": round(float(metrics.get("f1_class_3", -1.0)), 4),
            "f1_dos_4": round(float(metrics.get("f1_class_4", -1.0)), 4),
            "strategy": strategy_name,
            "model_type": model_type,
            "dataset_rejections": int(metrics.get("dataset_rejections_count", 0)),
        },
    }
    dispatch_async(webhook_url, payload)


def send_table_sync(
    webhook_url: str,
    sheet_name: str,
    headers: List[str],
    rows: List[List[Any]],
    clear_existing: bool = True,
) -> bool:
    """
    Sync an entire table / dataframe to a designated worksheet tab.
    Synchronous execution suitable for batch scripts.
    """
    if not webhook_url:
        _log.error("[sheets_sync] Error: No Google Sheets webhook URL provided.")
        return False

    payload = {
        "action": "sync_table",
        "sheet": sheet_name,
        "clear": clear_existing,
        "headers": headers,
        "rows": rows,
    }
    success = _post_json(webhook_url, payload, timeout=20.0)
    if success:
        _log.info(f"[sheets_sync] [OK] Synced {len(rows)} rows to tab '{sheet_name}'")
    return success


def send_promotion_event(
    webhook_url: str,
    server_round: int,
    champion_model: str,
    per_class_f1: Dict[str, float],
    passed: bool,
    reason: str = "",
) -> None:
    """Dispatch champion model promotion event to Google Sheets."""
    if not webhook_url:
        return

    payload = {
        "action": "champion_promotion",
        "sheet": "Model_Promotions",
        "data": {
            "round": int(server_round),
            "model": champion_model,
            "passed": passed,
            "f1_scores": per_class_f1,
            "reason": reason,
        },
    }
    dispatch_async(webhook_url, payload)
