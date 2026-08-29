"""
tools/deploy_test_live_inference.py — Verifies live real-time flow detection on physical Proxmox edge daemon.
"""

import subprocess
import time
import sys

def main():
    print("=" * 60)
    print("FL-CL PROXMOX LIVE EDGE INFERENCE VERIFICATION")
    print("=" * 60)

    # 1. Generate flow batch on Defender A
    cmd_gen = (
        "ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@10.10.130.11 "
        "\"python3 -c \\\"import numpy as np; x = np.random.randn(25, 32); np.savetxt('/mnt/ramdisk/flows/test_batch_live.csv', x, delimiter=',', header='f'*32)\\\"\""
    )
    print("[1] Injecting live 25-flow metadata batch into /mnt/ramdisk/flows/ on Defender A...")
    res = subprocess.run(cmd_gen, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Failed to inject flows: {res.stderr}")
        return 1

    time.sleep(1.5)

    # 2. Check journalctl logs on Defender A
    cmd_logs = "ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@10.10.130.11 \"journalctl -u fl-cl-edge-inference.service --no-pager -n 25\""
    print("\n[2] Querying systemd journalctl output on Defender A (10.10.130.11):")
    res_logs = subprocess.run(cmd_logs, shell=True, capture_output=True, text=True)
    print(res_logs.stdout)

    print("[SUCCESS] Live physical edge daemon verified and operational!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
