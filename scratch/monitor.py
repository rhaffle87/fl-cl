import subprocess
import time
import re
import sys

def get_latest_round():
    cmd = [
        "ssh", "-n", "-o", "StrictHostKeyChecking=no",
        "-i", "C:\\Users\\Rafli Alif\\.ssh\\id_ed25519",
        "root@10.10.130.10",
        "tail -n 30 /tmp/flower-server.log"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return f"Error running SSH: {res.stderr.strip()}"
        
        # Find all occurrences of [ROUND XX]
        matches = re.findall(r"\[ROUND\s+(\d+)\]", res.stdout)
        if matches:
            latest = int(matches[-1])
            return latest
        
        # Also check if it's compiling/saving at the end
        if "Validation Gate" in res.stdout or "MLOps Promotion" in res.stdout or "Wrote summary" in res.stdout:
            return "Promoting/Finished"
            
        return "No round match found"
    except Exception as e:
        return f"Exception: {e}"

def is_server_running():
    cmd = [
        "ssh", "-n", "-o", "StrictHostKeyChecking=no",
        "-i", "C:\\Users\\Rafli Alif\\.ssh\\id_ed25519",
        "root@10.10.130.10",
        "pgrep -f '[s]erver.py'"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False

print("Starting FL-CL Training Monitor...")
print("================================")

consecutive_not_running = 0
while True:
    running = is_server_running()
    rnd = get_latest_round()
    
    status_str = "Running" if running else "Not Running"
    print(f"[{time.strftime('%H:%M:%S')}] Server Status: {status_str} | Latest Round: {rnd}")
    
    if not running:
        consecutive_not_running += 1
        if consecutive_not_running >= 3:
            print("Server has stopped running. Exiting monitor.")
            break
    else:
        consecutive_not_running = 0
        
    time.sleep(30)
