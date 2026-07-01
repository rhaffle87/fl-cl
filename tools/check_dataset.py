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
import numpy as np
import pandas as pd

sys.path.append("/root")
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src" / "defender"))
import client


def jensen_shannon_divergence(p, q):
    """Compute the Jensen-Shannon Divergence between two distributions using base 2."""
    p = np.array(p, dtype=float)
    q = np.array(q, dtype=float)
    
    p_sum = np.sum(p)
    q_sum = np.sum(q)
    
    p = p / p_sum if p_sum > 0 else np.zeros_like(p)
    q = q / q_sum if q_sum > 0 else np.zeros_like(q)
    
    if np.sum(p) == 0 or np.sum(q) == 0:
        return 1.0
        
    m = 0.5 * (p + q)
    
    def kl_div(x, y):
        with np.errstate(divide='ignore', invalid='ignore'):
            val = np.where(x > 0, x * np.log2(x / np.where(y > 0, y, 1.0)), 0.0)
            val = np.nan_to_num(val, nan=0.0, posinf=0.0, neginf=0.0)
        return np.sum(val)
        
    jsd = 0.5 * kl_div(p, m) + 0.5 * kl_div(q, m)
    return float(np.clip(jsd, 0.0, 1.0))


def main():
    parser = argparse.ArgumentParser(description="Inspect ramdisk flow label distribution")
    parser.add_argument("--flows-dir", default="/mnt/ramdisk/flows", help="Flow CSV directory")
    parser.add_argument("--json", action="store_true", help="Output JSON report with counts and JSD status")
    parser.add_argument("--dos-threshold-ms", type=float, default=2000.0, help="DoS flow duration threshold in ms")
    parser.add_argument("--baseline", default=None, help="Comma-separated relative baseline counts (e.g. 2,150,3,7,18)")
    parser.add_argument("--js-threshold", type=float, default=0.6, help="JSD threshold for rejecting batch")
    args = parser.parse_args()

    csv_files = sorted(Path(args.flows_dir).glob("*.csv"))
    if not csv_files:
        if args.json:
            import json
            print(json.dumps({"error": "No CSV files found", "status": "FAIL"}))
        else:
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
        if args.json:
            import json
            print(json.dumps({"error": "No valid flow records", "status": "FAIL"}))
        else:
            print("No valid flow records found in", args.flows_dir)
        sys.exit(1)

    df = pd.concat(dfs, ignore_index=True)
    df["label"] = df.apply(client.assign_label, axis=1, dos_threshold_ms=args.dos_threshold_ms)

    counts = df["label"].value_counts().to_dict()
    counts_full = {i: int(counts.get(i, 0)) for i in range(5)}

    jsd_val = None
    status = "PASS"

    if args.baseline:
        try:
            baseline_vals = [float(x.strip()) for x in args.baseline.split(",")]
            if len(baseline_vals) != 5:
                raise ValueError("Baseline must contain exactly 5 class values.")
            
            p = [counts_full[i] for i in range(5)]
            jsd_val = jensen_shannon_divergence(p, baseline_vals)
            if jsd_val > args.js_threshold:
                status = "FAIL"
        except Exception as e:
            sys.stderr.write(f"Error calculating JSD: {e}\n")
            jsd_val = None

    if args.json:
        import json
        out_dict = {
            "counts": counts_full,
            "js_divergence": jsd_val,
            "status": status
        }
        print(json.dumps(out_dict))
        sys.exit(2 if status == "FAIL" else 0)

    label_names = {0: "Normal", 1: "Botnet", 2: "Exfiltration", 3: "BruteForce", 4: "DoS"}

    print(f"Total flows: {len(df)}")
    print(f"CSV files:   {len(csv_files)}")
    if jsd_val is not None:
        print(f"Jensen-Shannon Divergence: {jsd_val:.4f} (Threshold: {args.js_threshold})")
        print(f"Quality Gate Status:       {status}")
    print(f"\nLabel distribution:")
    for label in range(5):
        count = counts_full[label]
        name = label_names.get(label, "Unknown")
        bar = "█" * min(count // 10, 50)
        print(f"  {label} ({name:>13s}): {count:>5d}  {bar}")

    # Show sample flows for each class
    for label in range(5):
        class_df = df[df["label"] == label]
        if not class_df.empty:
            print(f"\nSample Class {label} ({label_names[label]}) flows:")
            print(class_df[["src_ip", "dst_ip", "src_port", "dst_port", "protocol"]].head(5).to_string(index=False))

    sys.exit(2 if status == "FAIL" else 0)


if __name__ == "__main__":
    main()
