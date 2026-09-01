# tools/sync_sheets_webhook.py — Google Sheets Webhook Sync CLI.
#
# Syncs FL-CL benchmark CSVs and live evaluation records directly to Google Sheets via
# a Google Apps Script WebApp endpoint (Option 2).
#
# Usage:
# # 1. Test webhook connection
# python tools/sync_sheets_webhook.py --url "https://script.google.com/macros/s/.../exec" --test
#
# # 2. Sync all benchmark CSVs in data/reports/benchmarks/ into separate sheet tabs
# python tools/sync_sheets_webhook.py --url "https://script.google.com/macros/s/.../exec" --sync-all
#
# # 3. Use environment variable GSHEETS_WEBHOOK_URL
# export GSHEETS_WEBHOOK_URL="https://script.google.com/macros/s/.../exec"
# python tools/sync_sheets_webhook.py --sync-all

import argparse
import csv
import glob
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aggregator.sheets_sync import (
    _post_json,
    send_table_sync,
)


def get_default_url(cli_url: str = None) -> str:
    if cli_url:
        return cli_url
    if "GSHEETS_WEBHOOK_URL" in os.environ and os.environ["GSHEETS_WEBHOOK_URL"]:
        return os.environ["GSHEETS_WEBHOOK_URL"]
    if (
        "GOOGLE_SHEETS_WEBHOOK_URL" in os.environ
        and os.environ["GOOGLE_SHEETS_WEBHOOK_URL"]
    ):
        return os.environ["GOOGLE_SHEETS_WEBHOOK_URL"]
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GSHEETS_WEBHOOK_URL=") or line.startswith(
                    "GOOGLE_SHEETS_WEBHOOK_URL="
                ):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    return ""


def sync_csv_file(url: str, csv_path: str, sheet_name: str = None) -> bool:
    """Read a CSV and sync its contents to a worksheet tab."""
    path = Path(csv_path)
    if not path.exists():
        print(f"[!] CSV not found: {csv_path}")
        return False

    if not sheet_name:
        sheet_name = path.stem.replace("_", " ").title()[:30]

    with open(path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print(f"[!] File is empty: {csv_path}")
        return False

    headers = rows[0]
    data_rows = rows[1:]

    print(f"[*] Syncing '{path.name}' -> Tab '{sheet_name}' ({len(data_rows)} rows)...")
    return send_table_sync(url, sheet_name, headers, data_rows, clear_existing=True)


def sync_all_reports(url: str, reports_dir: str = None) -> None:
    """Sync all CSV benchmark files in data/reports/benchmarks/."""
    if not reports_dir:
        reports_dir = str(PROJECT_ROOT / "data" / "reports" / "benchmarks")

    csv_files = sorted(glob.glob(os.path.join(reports_dir, "*.csv")))
    if not csv_files:
        print(f"[!] No CSV files found in {reports_dir}")
        return

    print("=" * 65)
    print(f"  SYNCING {len(csv_files)} BENCHMARK CSVs TO GOOGLE SHEETS")
    print("=" * 65)

    success_count = 0
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        # Format clean tab name (e.g., 'byzantine_robustness_benchmark.csv' -> 'Byzantine Robustness')
        tab_name = (
            filename.replace("_benchmark", "")
            .replace("_report", "")
            .replace(".csv", "")
            .replace("_", " ")
            .title()[:30]
        )
        if sync_csv_file(url, file_path, tab_name):
            success_count += 1

    print("=" * 65)
    print(
        f"[SUCCESS] Synced {success_count}/{len(csv_files)} benchmark reports to Google Sheets."
    )
    print("=" * 65)


def run_test(url: str) -> None:
    """Send test round metric and test table to verify webhook functionality."""
    print(f"[*] Testing webhook endpoint: {url}")

    # 1. Test single round metric (synchronous)
    payload_metric = {
        "action": "round_metric",
        "sheet": "Live_Rounds",
        "data": {
            "round": 100,
            "loss": 0.4201,
            "accuracy_pct": 99.30,
            "macro_f1": 0.9936,
            "f1_normal_0": 0.9995,
            "f1_botnet_1": 1.0000,
            "f1_exfil_2": 0.9985,
            "f1_bruteforce_3": 1.0000,
            "f1_dos_4": 0.9703,
            "strategy": "TrimmedMean",
            "model_type": "cnn",
            "dataset_rejections": 0,
        },
    }
    ok1 = _post_json(url, payload_metric)
    if ok1:
        print("  [OK] Successfully posted test round metric to 'Live_Rounds'")
    else:
        print("  [FAIL] Failed to post test round metric.")

    # 2. Test promotion event
    payload_promo = {
        "action": "champion_promotion",
        "sheet": "Model_Promotions",
        "data": {
            "round": 100,
            "model": "1D-CNN (CyberDefenseCNN)",
            "passed": True,
            "f1_scores": {
                "Normal": 0.9995,
                "Botnet": 1.00,
                "DNS Exfil": 0.998,
                "SSH Brute": 1.00,
                "DoS": 0.970,
            },
            "reason": "All 5 threat class F1 scores exceed production gate thresholds.",
        },
    }
    ok2 = _post_json(url, payload_promo)
    if ok2:
        print("  [OK] Successfully posted test promotion event to 'Model_Promotions'")
    else:
        print("  [FAIL] Failed to post test promotion event.")


def main():
    parser = argparse.ArgumentParser(description="FL-CL Google Sheets Webhook Sync CLI")
    parser.add_argument(
        "--url",
        default="",
        help="Google Apps Script WebApp URL (or set GSHEETS_WEBHOOK_URL env)",
    )
    parser.add_argument(
        "--sync-all",
        action="store_true",
        help="Sync all CSV benchmark reports in data/reports/benchmarks/",
    )
    parser.add_argument("--file", default="", help="Path to a single CSV file to sync")
    parser.add_argument(
        "--sheet", default="", help="Custom sheet tab name for the file"
    )
    parser.add_argument(
        "--test", action="store_true", help="Send test round and promotion events"
    )
    args = parser.parse_args()

    webhook_url = get_default_url(args.url)
    if not webhook_url:
        print("[!] Error: No Google Sheets webhook URL provided.")
        print(
            "    Pass --url 'https://script.google.com/macros/s/.../exec' or set GSHEETS_WEBHOOK_URL."
        )
        sys.exit(1)

    if args.test:
        run_test(webhook_url)
    elif args.file:
        sync_csv_file(webhook_url, args.file, args.sheet)
    elif args.sync_all:
        sync_all_reports(webhook_url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
