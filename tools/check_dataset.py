"""
check_dataset.py — Inspect ramdisk flow label distribution on a defender node.

Usage (SCP to defender, then run):
    python3 check_dataset.py [--flows-dir /mnt/ramdisk/flows]

Labels:
    0: Normal  |  1: Botnet  |  2: Exfiltration  |  3: BruteForce  |  4: DoS
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append("/root")
import client


def main():
    parser = argparse.ArgumentParser(description="Inspect ramdisk flow label distribution")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    args = parser.parse_args()

    csv_files = sorted(Path(args.flows_dir).glob("*.csv"))
    if not csv_files:
        print("No CSV files found in", args.flows_dir)
        sys.exit(1)

    dfs = []
    for f in csv_files:
        try:
            df_item = pd.read_csv(f)
            if not df_item.empty:
                dfs.append(df_item)
        except Exception:
            pass

    if not dfs:
        print("No valid flow records found in", args.flows_dir)
        sys.exit(1)

    df = pd.concat(dfs, ignore_index=True)
    df["label"] = df.apply(client.assign_label, axis=1)

    label_names = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}

    print(f"Total flows: {len(df)}")
    print(f"CSV files:   {len(csv_files)}")
    print(f"\nLabel distribution:")
    for label in range(5):
        count = len(df[df["label"] == label])
        name = label_names.get(label, "Unknown")
        bar = "█" * min(count // 10, 50)
        print(f"  {label} ({name:>13s}): {count:>5d}  {bar}")

    # Show sample flows for each class
    for label in range(5):
        class_df = df[df["label"] == label]
        if not class_df.empty:
            print(f"\nSample Class {label} ({label_names[label]}) flows:")
            print(class_df[["src_ip", "dst_ip", "src_port", "dst_port", "protocol"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
