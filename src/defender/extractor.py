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
from pathlib import Path

import pandas as pd
from nfstream import NFStreamer


def extract_features(interface: str, out_dir: str, batch_size: int = 500):
    """
    Stream flows from a network interface and write batched feature CSVs.

    Args:
        interface:  Network interface to capture from (e.g., ens19)
        out_dir:    Output directory for flow CSVs (should be on tmpfs)
        batch_size: Number of flows per output file
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    streamer = NFStreamer(
        source=interface,
        promisc=True,
        snapshot_len=1536,
        idle_timeout=120,
        active_timeout=1800,
        accounting_mode=3,  # Enable SSL/TLS metadata extraction
    )

    batch = []
    batch_num = 0

    print(f"[extractor] Capturing on {interface} → {out_dir}")
    print(f"[extractor] Batch size: {batch_size} flows per file")

    for flow in streamer:
        features = {
            # --- TLS Handshake Features ---
            "ja3_hash": flow.src_to_dst_ja3 or "",
            "ja3s_hash": flow.dst_to_src_ja3 or "",
            "sni": flow.requested_server_name or "",
            "application": flow.application_name or "",
            # --- Flow Statistics ---
            "bidirectional_packets": flow.bidirectional_packets,
            "bidirectional_bytes": flow.bidirectional_bytes,
            "duration_ms": flow.bidirectional_duration_ms,
            # --- Directional Metrics ---
            "src2dst_packets": flow.src2dst_packets,
            "src2dst_bytes": flow.src2dst_bytes,
            "dst2src_packets": flow.dst2src_packets,
            "dst2src_bytes": flow.dst2src_bytes,
            # --- Timing ---
            "src2dst_mean_piat_ms": getattr(flow, "src2dst_mean_piat_ms", 0),
            "dst2src_mean_piat_ms": getattr(flow, "dst2src_mean_piat_ms", 0),
            # --- Metadata ---
            "src_ip": flow.src_ip,
            "dst_ip": flow.dst_ip,
            "src_port": flow.src_port,
            "dst_port": flow.dst_port,
            "protocol": flow.protocol,
        }
        batch.append(features)

        if len(batch) >= batch_size:
            batch_num += 1
            filename = os.path.join(out_dir, f"flows_{batch_num:06d}.csv")
            df = pd.DataFrame(batch)
            df.to_csv(filename, index=False)
            print(f"[extractor] Wrote {len(batch)} flows → {filename}")
            batch = []

    # Flush remaining flows
    if batch:
        batch_num += 1
        filename = os.path.join(out_dir, f"flows_{batch_num:06d}.csv")
        pd.DataFrame(batch).to_csv(filename, index=False)
        print(f"[extractor] Wrote {len(batch)} flows → {filename}")


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
    args = parser.parse_args()

    extract_features(args.interface, args.out_dir, args.batch_size)


if __name__ == "__main__":
    main()
