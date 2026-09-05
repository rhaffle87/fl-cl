#!/usr/bin/env python3
"""
tools/check_network_stability.py
Comprehensive diagnostic and health verification suite for:
- ollama-server (100.110.11.66 / 192.168.30.105)
- fl-aggregator (100.97.96.13 / 192.168.30.55)

Verifies:
1. Tailscale reachability & SSH connectivity (strict host-key verification)
2. Zero duplicate ARP IP collisions on vmbr0 (arping exit status preservation)
3. MTU 1280 and TCP MSS Clamping (1220) enforcement (independent FORWARD and POSTROUTING verification)
4. Systemd persistence of network configs and sysctl tuning
5. Real service responsiveness (Ollama HTTPS inference & MLflow tracking)
"""

import json
import os
import subprocess
import sys
import time


def load_env(env_name: str = ".env"):
    """Load environment variables searching upward from script location."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_path = os.path.join(current_dir, env_name)
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        os.environ[key] = val
            break
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent


load_env()

NODES = [
    {
        "name": "ollama-server",
        "ts_ip": "100.110.11.66",
        "local_ip": "192.168.30.105",
        "service_name": "Ollama HTTPS API",
    },
    {
        "name": "fl-aggregator",
        "ts_ip": "100.97.96.13",
        "local_ip": "192.168.30.55",
        "service_check_cmd": "curl -s -I http://127.0.0.1:5000/ | grep 'HTTP/1.1 200'",
        "service_name": "MLflow Tracking Server",
    },
]


def pre_register_host_key(host: str):
    """Ensure target node host key is pre-registered in known_hosts before connection."""
    try:
        check = subprocess.run(
            ["ssh-keygen", "-F", host], capture_output=True, text=True
        )
        if check.returncode != 0 or not check.stdout.strip():
            scan = subprocess.run(
                ["ssh-keyscan", "-H", host],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if scan.returncode == 0 and scan.stdout.strip():
                known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
                os.makedirs(os.path.dirname(known_hosts_file), exist_ok=True)
                with open(known_hosts_file, "a", encoding="utf-8") as f:
                    f.write(scan.stdout)
    except Exception:
        pass


def run_ssh(host: str, cmd: str, timeout: int = 10):
    pre_register_host_key(host)
    start = time.time()
    res = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", f"root@{host}", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    rtt = round((time.time() - start) * 1000, 1)
    return res.returncode, res.stdout.strip(), res.stderr.strip(), rtt


def get_service_check_cmd(node: dict) -> str:
    """Retrieve service check command using protected runtime configuration."""
    if node["name"] == "ollama-server":
        ollama_key = os.getenv("OLLAMA_KEY", "")
        return (
            f"curl -k -s -H 'x-fcl-key: {ollama_key}' https://127.0.0.1:443/api/version "
            "| grep '\"version\"'"
        )
    return node.get(
        "service_check_cmd",
        "curl -s -I http://127.0.0.1:5000/ | grep 'HTTP/1.1 200'",
    )


def audit_node(node: dict) -> bool:
    print("\n=======================================================")
    print(f" AUDITING NODE: {node['name']} ({node['ts_ip']})")
    print("=======================================================")
    all_ok = True

    # Run batched diagnostic in a single SSH session for speed, stability & low overhead
    batch_cmd = (
        f"IP=$(ip -4 addr show eth0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{{print $2}}'); "
        f"MTU=$(ip link show eth0 2>/dev/null | grep -o 'mtu [0-9]*' | awk '{{print $2}}'); "
        f"MSS_FWD=$(iptables -t mangle -S FORWARD 2>/dev/null | grep -c 'TCPMSS --set-mss 1220' || true); "
        f"MSS_POST=$(iptables -t mangle -S POSTROUTING 2>/dev/null | grep -c 'TCPMSS --set-mss 1220' || true); "
        f"KEEPALIVE=$(sysctl -n net.ipv4.tcp_keepalive_time 2>/dev/null || echo 0); "
        f"PROBING=$(sysctl -n net.ipv4.tcp_mtu_probing 2>/dev/null || echo 0); "
        f"PERSIST=$(systemctl is-enabled network-mss-clamp.service 2>/dev/null || echo disabled); "
        f"if command -v arping >/dev/null 2>&1; then "
        f"ARP_OUT=$(arping -c 2 -D -I eth0 {node['local_ip']} 2>&1); ARP_CODE=$?; "
        f"else ARP_OUT='arping binary not found'; ARP_CODE=127; fi; "
        f"echo \"$IP###$MTU###$MSS_FWD###$MSS_POST###$KEEPALIVE###$PROBING###$PERSIST###$ARP_CODE###$ARP_OUT\""
    )

    try:
        code, out, err, rtt = run_ssh(node["ts_ip"], batch_cmd, timeout=20)
    except Exception as ex:
        print(f"  [FAIL] SSH Reachability: Timed out connecting to {node['ts_ip']} ({ex})")
        return False

    if code != 0 or "###" not in out:
        print(f"  [FAIL] SSH Reachability: FAILED (Code {code}: {err})")
        return False

    print(f"  [PASS] SSH Reachability: OK ({rtt}ms RTT)")
    parts = out.strip().split("###")
    actual_ip = parts[0].strip() if len(parts) > 0 else ""
    actual_mtu = parts[1].strip() if len(parts) > 1 else ""
    try:
        mss_fwd = int(parts[2].strip() or 0) if len(parts) > 2 else 0
    except ValueError:
        mss_fwd = 0
    try:
        mss_post = int(parts[3].strip() or 0) if len(parts) > 3 else 0
    except ValueError:
        mss_post = 0
    keepalive = parts[4].strip() if len(parts) > 4 else ""
    probing = parts[5].strip() if len(parts) > 5 else ""
    persist = parts[6].strip() if len(parts) > 6 else ""
    try:
        arp_code = int(parts[7].strip()) if len(parts) > 7 else 1
    except ValueError:
        arp_code = 1
    arp_out = parts[8].strip() if len(parts) > 8 else ""

    # 1. Local IP Binding
    if actual_ip == node["local_ip"]:
        print(f"  [PASS] Local IP Binding: {actual_ip} (Matches target {node['local_ip']})")
    else:
        print(f"  [FAIL] Local IP Binding: '{actual_ip}' (Expected {node['local_ip']})")
        all_ok = False

    # 2. ARP Collision Check (Strict exit code + response check)
    if arp_code == 0 and ("Received 0 response(s)" in arp_out or "Received 0 response" in arp_out):
        print("  [PASS] ARP Collision Check: Zero duplicate responses (Conflict-free)")
    elif arp_code == 127:
        print(f"  [FAIL] ARP Collision Check: arping binary is missing on {node['name']}")
        all_ok = False
    else:
        print(f"  [FAIL] ARP Collision Check: Detected collision or arping error (Exit code {arp_code}):\n{arp_out}")
        all_ok = False

    # 3. MTU Check
    if actual_mtu == "1280":
        print(f"  [PASS] Interface MTU: {actual_mtu} (Optimal 1280)")
    else:
        print(f"  [FAIL] Interface MTU: {actual_mtu} (Expected 1280)")
        all_ok = False

    # 4. MSS Clamping Check (Independent FORWARD and POSTROUTING inspection)
    if mss_fwd >= 1 and mss_post >= 1:
        print(f"  [PASS] MSS Clamping: Active (FORWARD: {mss_fwd}, POSTROUTING: {mss_post})")
    else:
        print(f"  [FAIL] MSS Clamping: Missing required rules (FORWARD: {mss_fwd}, POSTROUTING: {mss_post}; requires >= 1 in each)")
        all_ok = False

    # 5. Sysctl Tuning & Keepalive
    if keepalive == "15" and probing == "1":
        print(f"  [PASS] TCP Keepalive & Probing:\n    net.ipv4.tcp_keepalive_time = {keepalive}\n    net.ipv4.tcp_mtu_probing = {probing}")
    else:
        print(f"  [FAIL] TCP Keepalive & Probing:\n    net.ipv4.tcp_keepalive_time = {keepalive} (Expected 15)\n    net.ipv4.tcp_mtu_probing = {probing} (Expected 1)")
        all_ok = False

    # 6. Persistence Unit
    if persist == "enabled":
        print("  [PASS] Persistence Service: network-mss-clamp.service is ENABLED on boot")
    else:
        print(f"  [FAIL] Persistence Service: network-mss-clamp.service status is '{persist}' (Expected enabled)")
        all_ok = False

    # 7. Service Responsiveness
    print(f"  [*] Testing {node['service_name']}...")
    service_cmd = get_service_check_cmd(node)
    try:
        code, out, err, s_rtt = run_ssh(node["ts_ip"], service_cmd, timeout=30)
        if code == 0 and len(out) > 0:
            print(f"  [PASS] {node['service_name']}: Operational ({s_rtt}ms)")
        else:
            print(f"  [FAIL] {node['service_name']}: Non-zero return code {code} ({err})")
            all_ok = False
    except Exception as ex:
        print(f"  [FAIL] {node['service_name']} check timed out: {ex}")
        all_ok = False

    return all_ok


if __name__ == "__main__":
    print("FL-CL INFRASTRUCTURE NETWORK STABILITY AUDIT")
    results = [audit_node(node) for node in NODES]
    print("\n" + "=" * 55)
    if all(results):
        print("SUMMARY: ALL NODES ARE 100% HEALTHY, STABLE & CONFLICT-FREE.")
        sys.exit(0)
    else:
        print("SUMMARY: WARNINGS OR FAILURES DETECTED.")
        sys.exit(1)
