"""
check_features.py — Per-class feature statistics for FL-CL flow data.

Compares flow-level feature distributions across all 5 attack classes to
identify feature overlap (classes that the model cannot separate).

Usage (SCP to defender, then run):
    python3 check_features.py [--flows-dir /mnt/ramdisk/flows]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append("/root")
import client


LABEL_NAMES = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}

FEATURE_COLS = [
    "bidirectional_packets", "bidirectional_bytes", "duration_ms",
    "src2dst_packets", "src2dst_bytes", "dst2src_packets", "dst2src_bytes",
    "src2dst_mean_piat_ms", "dst2src_mean_piat_ms", "dst_port",
]


def load_flows(flows_dir):
    csv_files = sorted(Path(flows_dir).glob("*.csv"))
    if not csv_files:
        print("No CSV files found in", flows_dir)
        sys.exit(1)

    dfs = []
    for f in csv_files:
        try:
            d = pd.read_csv(f)
            if not d.empty:
                dfs.append(d)
        except Exception:
            pass

    if not dfs:
        print("No valid flow records found in", flows_dir)
        sys.exit(1)

    df = pd.concat(dfs, ignore_index=True)
    df["label"] = df.apply(client.assign_label, axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(description="Per-class feature statistics")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--compare", nargs=2, type=int, metavar=("A", "B"),
                        help="Compare two specific classes (e.g. --compare 1 4)")
    args = parser.parse_args()

    df = load_flows(args.flows_dir)
    available_features = [c for c in FEATURE_COLS if c in df.columns]

    if args.compare:
        classes = args.compare
    else:
        classes = sorted(df["label"].unique())

    for label in classes:
        sub = df[df["label"] == label][available_features]
        name = LABEL_NAMES.get(label, "Unknown")
        print(f"\n{'='*60}")
        print(f"LABEL {label} — {name} (n={len(sub)})")
        print(f"{'='*60}")
        for col in available_features:
            s = sub[col]
            print(f"  {col:>25s}:  mean={s.mean():>10.2f}  std={s.std():>10.2f}  "
                  f"min={s.min():>8.0f}  max={s.max():>8.0f}")

    # Port distribution summary
    print(f"\n{'='*60}")
    print("dst_port distribution per class")
    print(f"{'='*60}")
    for label in classes:
        name = LABEL_NAMES.get(label, "Unknown")
        ports = df[df["label"] == label]["dst_port"].value_counts().head(5)
        port_str = ", ".join([f"{p}({c})" for p, c in ports.items()])
        print(f"  {label} ({name:>13s}): {port_str}")


if __name__ == "__main__":
    main()
