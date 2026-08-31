"""
extractor.py — NFStream-based Encrypted Traffic Analysis (ETA) Feature Extractor

Captures mirrored traffic from the capture interface (ens19) and extracts
flow-level metadata features (JA3 fingerprints, packet statistics, timing).
Output is written to the tmpfs RAM disk at /mnt/ramdisk/flows/ to avoid
I/O contention on the shared RAID controller.

Deploy on: Defender VMs (VM 310, VM 320)
Usage:
    python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/
"""

import argparse
import os
import time
import sys
import signal
from pathlib import Path
import numpy as np
import pandas as pd
try:
    from logger import get_logger
    _log = get_logger("extractor")
except ImportError:
    try:
        from src.logger import get_logger
        _log = get_logger("extractor")
    except ImportError:
        import logging
        _log = logging.getLogger("extractor")

try:
    from nfstream import NFStreamer
except ImportError:
    NFStreamer = None


class WelfordNormalizer:
    """
    Online Streaming Welford Algorithm for dynamic feature standardization.
    Computes numerically stable online running mean and variance over streaming flow batches,
    enabling dynamic adaptation to non-standard MTUs, Jumbo frames, and asymmetric WAN links.
    """
    def __init__(self, num_features: int = 32):
        self.num_features = num_features
        self.count = 0
        self.mean = np.zeros(num_features, dtype=np.float32)
        self.M2 = np.zeros(num_features, dtype=np.float32)

    def update(self, x: np.ndarray):
        """
        Update running statistics with a new flow vector or batch of vectors (N, D).
        """
        x = np.asarray(x, dtype=np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        for row in x:
            self.count += 1
            delta = row - self.mean
            self.mean += delta / self.count
            delta2 = row - self.mean
            self.M2 += delta * delta2

    @property
    def variance(self) -> np.ndarray:
        if self.count < 2:
            return np.ones(self.num_features, dtype=np.float32)
        return np.maximum(self.M2 / (self.count - 1), 1e-6)

    @property
    def std(self) -> np.ndarray:
        return np.sqrt(self.variance)

    def normalize(self, x: np.ndarray) -> np.ndarray:
        """
        Standardize flow features via Z-score using current online running mean and std.
        """
        return (x - self.mean) / (self.std + 1e-8)


def calculate_energy_score(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """
    Compute Free Energy score E(x; T) from unnormalized model logits for Out-of-Distribution (OOD) detection:
        E(x; T) = -T * log(sum_{c=1}^C exp(f_c(x) / T))
    
    Known In-Distribution flows produce large negative energy (E << 0).
    Novel zero-day / anomalous flows produce high energy (E >= tau_ood).
    """
    logits = np.asarray(logits, dtype=np.float64)
    scaled_logits = logits / max(temperature, 1e-6)
    
    # Numerically stable LogSumExp:
    if scaled_logits.ndim == 1:
        max_val = np.max(scaled_logits)
        lse = max_val + np.log(np.sum(np.exp(scaled_logits - max_val)))
        return -temperature * lse
    else:
        max_val = np.max(scaled_logits, axis=-1, keepdims=True)
        lse = max_val.squeeze(-1) + np.log(np.sum(np.exp(scaled_logits - max_val), axis=-1))
        return -temperature * lse



def extract_features(interface: str, out_dir: str, batch_size: int = 500, streaming_norm: bool = False):
    """
    Stream flows from a network interface and write batched feature CSVs.

    Args:
        interface:  Network interface to capture from (e.g., ens19)
        out_dir:    Output directory for flow CSVs (should be on tmpfs)
        batch_size: Number of flows per output file
    """
    if out_dir.startswith("/mnt/ramdisk") and sys.platform.startswith("linux"):
        if os.path.exists("/mnt/ramdisk") and not os.path.ismount("/mnt/ramdisk"):
            _log.warning("[extractor] WARNING: /mnt/ramdisk is not mounted as tmpfs! Potential disk I/O contention.")

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    streamer = NFStreamer(
        source=interface,
        promiscuous_mode=True,
        snapshot_length=1536,
        idle_timeout=10,      # Emit flow records quickly (was 120)
        active_timeout=60,    # Force-flush long-lived connections (was 1800)
        n_dissections=20,     # Enable deep packet inspection for TLS metadata
    )

    batch = []
    batch_num = 0
    last_write_time = time.time()

    def handle_signal(signum, frame):
        _log.info(f"\n[extractor] Received signal {signum}. Flushing remaining {len(batch)} flows...")
        if batch:
            nonlocal batch_num
            batch_num += 1
            filename = os.path.join(out_dir, f"flows_{batch_num:06d}.csv")
            pd.DataFrame(batch).to_csv(filename, index=False)
            _log.info(f"[extractor] Wrote remaining flows → {filename}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    _log.info(f"[extractor] Capturing on {interface} → {out_dir}")
    _log.info(f"[extractor] Batch size: {batch_size} flows per file (or max 5 seconds wait)")

    for flow in streamer:
        features = {
            # --- TLS Handshake Features ---
            "ja3_hash": getattr(flow, "src_to_dst_ja3", "") or "",
            "ja3s_hash": getattr(flow, "dst_to_src_ja3", "") or "",
            "sni": getattr(flow, "requested_server_name", "") or "",
            "application": getattr(flow, "application_name", "") or "",
            # --- Flow Statistics ---
            "bidirectional_packets": getattr(flow, "bidirectional_packets", 0),
            "bidirectional_bytes": getattr(flow, "bidirectional_bytes", 0),
            "duration_ms": getattr(flow, "bidirectional_duration_ms", 0),
            # --- Directional Metrics ---
            "src2dst_packets": getattr(flow, "src2dst_packets", 0),
            "src2dst_bytes": getattr(flow, "src2dst_bytes", 0),
            "dst2src_packets": getattr(flow, "dst2src_packets", 0),
            "dst2src_bytes": getattr(flow, "dst2src_bytes", 0),
            # --- Timing ---
            "src2dst_mean_piat_ms": getattr(flow, "src2dst_mean_piat_ms", 0),
            "dst2src_mean_piat_ms": getattr(flow, "dst2src_mean_piat_ms", 0),
            # --- Metadata ---
            "src_ip": getattr(flow, "src_ip", ""),
            "dst_ip": getattr(flow, "dst_ip", ""),
            "src_port": getattr(flow, "src_port", 0),
            "dst_port": getattr(flow, "dst_port", 0),
            "protocol": getattr(flow, "protocol", 0),
        }
        batch.append(features)

        current_time = time.time()
        if len(batch) >= batch_size or (current_time - last_write_time >= 5.0):
            batch_num += 1
            filename = os.path.join(out_dir, f"flows_{batch_num:06d}.csv")
            pd.DataFrame(batch).to_csv(filename, index=False)
            _log.info(f"[extractor] Wrote {len(batch)} flows → {filename}")
            batch = []
            last_write_time = current_time

    # Flush remaining flows
    if batch:
        batch_num += 1
        filename = os.path.join(out_dir, f"flows_{batch_num:06d}.csv")
        pd.DataFrame(batch).to_csv(filename, index=False)
        _log.info(f"[extractor] Wrote {len(batch)} flows → {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="NFStream ETA Feature Extractor for FL-CL Cyber Defense"
    )
    parser.add_argument(
        "--interface", "-i",
        default="ens19",
        help="Capture interface (default: ens19)"
    )
    parser.add_argument(
        "--out-dir", "-o",
        default="/mnt/ramdisk/flows",
        help="Output directory for flow CSVs (default: /mnt/ramdisk/flows)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int, default=500,
        help="Flows per output file (default: 500)"
    )
    parser.add_argument(
        "--streaming-norm",
        action="store_true",
        help="Enable online Streaming Welford Algorithm for dynamic feature normalization"
    )
    args = parser.parse_args()

    extract_features(args.interface, args.out_dir, args.batch_size, streaming_norm=args.streaming_norm)


if __name__ == "__main__":
    main()
