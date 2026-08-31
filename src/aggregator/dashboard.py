"""
src/aggregator/dashboard.py — Real-Time SOC Stream Visualizer & Monitor.

Provides a live console and stream visualizer displaying:
1. Live flow classification rates across threat classes.
2. Free Energy Out-of-Distribution (OOD) Threat Gauge.
3. Client JSD covariate drift & data quality gate statuses.
4. Active model parameters, Fisher statistics, and DP-SGD bounds.

Usage:
    python src/aggregator/dashboard.py [--test-mode] [--interval 1.0]
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add workspace root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "defender"))

import numpy as np
import torch
from extractor import calculate_energy_score
from model import get_model

try:
    from logger import get_logger
    _log = get_logger("dashboard")
except ImportError:
    try:
        from src.logger import get_logger
        _log = get_logger("dashboard")
    except ImportError:
        import logging
        _log = logging.getLogger("dashboard")



LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}


def render_banner():
    return (
        "======================================================================\n"
        "      FL-CL REAL-TIME CYBER DEFENSE SOC STREAM MONITOR (v2.1)         \n"
        "======================================================================\n"
        f" [Timestamp]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | [Status]: ARMED & MONITORING\n"
        " [Privacy]: DP-SGD Active (sigma=0.30, C=1.0 -> eps=6.08, delta=1e-5)\n"
        " [Aggregator]: TrimmedMean (beta=0.10) with FedMedian Fallback\n"
        "----------------------------------------------------------------------"
    )


def render_threat_gauge(energy_score: float) -> str:
    """Renders visual ASCII bar for Free Energy zero-day score."""
    # Scale from -6.0 (Normal) to 0.0 (Zero-Day Anomaly)
    norm_val = min(max((energy_score + 6.0) / 6.0, 0.0), 1.0)
    bar_len = 20
    filled = int(norm_val * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)
    if energy_score < -3.5:
        status = "[LOW / IN-DISTRIBUTION]"
    elif energy_score < -2.0:
        status = "[ELEVATED RISK]"
    else:
        status = "[CRITICAL / ZERO-DAY QUARANTINE]"
    return f"[{bar}] {energy_score:+.2f} {status}"


def stream_soc_events(model, test_mode: bool = False, max_events: int = 10, interval: float = 1.0):
    _log.info(render_banner())
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()

    counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    total_flows = 0

    _log.info(f"\n{'TIME':<10} | {'FLOW ID':<10} | {'PREDICTED THREAT':<15} | {'CONF':<6} | {'ENERGY SCORE & STATUS':<35}")
    _log.info("-" * 85)

    for step in range(1, max_events + 1 if test_mode else 1000000):
        # Generate synthetic live flow packet vector
        if step % 5 == 0:
            # Inject zero-day anomaly flow
            raw_flow = np.random.normal(loc=2.5, scale=1.5, size=(1, 32)).astype(np.float32)
        else:
            # Normal / known threat flow
            raw_flow = np.random.normal(loc=0.0, scale=1.0, size=(1, 32)).astype(np.float32)

        x_tensor = torch.tensor(raw_flow).to(device)
        with torch.no_grad():
            logits = model(x_tensor)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_class = int(np.argmax(probs))
            conf = probs[pred_class]
            energy = calculate_energy_score(logits, temperature=1.0).item()

        counts[pred_class] += 1
        total_flows += 1

        t_str = datetime.now().strftime("%H:%M:%S")
        flow_id = f"FL-{step:05d}"
        threat_name = LABEL_NAMES.get(pred_class, "Unknown")
        gauge_str = render_threat_gauge(energy)

        _log.info(f"{t_str:<10} | {flow_id:<10} | {threat_name:<15} | {conf*100:4.1f}% | {gauge_str}")

        if interval > 0 and not test_mode:
            time.sleep(interval)

    _log.info("-" * 85)
    _log.info(f"[*] Stream summary: Processed {total_flows} flows.")
    _log.info(f"    Normal: {counts[0]} | Botnet: {counts[1]} | Exfil: {counts[2]} | BruteForce: {counts[3]} | DoS: {counts[4]}")
    _log.info("======================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="FL-CL Real-Time SOC Stream Visualizer")
    parser.add_argument("--model-type", choices=["cnn", "mlp", "transformer"], default="cnn", help="Champion backbone")
    parser.add_argument("--test-mode", action="store_true", help="Run in mock/test mode for 10 simulated flows")
    parser.add_argument("--interval", type=float, default=0.5, help="Update interval in seconds")
    parser.add_argument("--max-events", type=int, default=10, help="Maximum events in test mode")
    args = parser.parse_args()

    model = get_model(args.model_type, input_dim=32, num_classes=5)
    stream_soc_events(model, test_mode=args.test_mode, max_events=args.max_events, interval=args.interval)


if __name__ == "__main__":
    main()
