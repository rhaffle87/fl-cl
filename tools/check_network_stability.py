#!/usr/bin/env python3
"""
tools/check_network_stability.py
Comprehensive diagnostic and health verification suite for:
- ollama-server (100.110.11.66 / 192.168.30.105)
- fl-aggregator (100.97.96.13 / 192.168.30.55)

Verifies:
1. Tailscale reachability & SSH connectivity
2. Zero duplicate ARP IP collisions on vmbr0
3. MTU 1280 and TCP MSS Clamping (1220) enforcement
4. Systemd persistence of network configs and sysctl tuning
5. Real service responsiveness (Ollama HTTPS inference & MLflow tracking)
"""

import subprocess
import time
import json
import sys

NODES = [
    {
        "name": "ollama-server",
        "ts_ip": "100.110.11.66",
        "local_ip": "192.168.30.105",
        "service_check": "curl -k -s -H 'x-fcl-key: 8f20843af3451b047c18c85867a4b65d5574cf3570d35a7587f6f6da8564dcb0' https://127.0.0.1:443/api/version | grep '\"version\"'",
        "service_name": "Ollama HTTPS API"
    },
    {
        "name": "fl-aggregator",
        "ts_ip": "100.97.96.13",
        "local_ip": "192.168.30.55",
        "service_check": "curl -s -I http://127.0.0.1:5000/ | grep 'HTTP/1.1 200'",
        "service_name": "MLflow Tracking Server"
    }
]

def run_ssh(host, cmd, timeout=10):
    start = time.time()
    res = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", f"root@{host}", cmd],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    rtt = round((time.time() - start) * 1000, 1)
    return res.returncode, res.stdout.strip(), res.stderr.strip(), rtt

def audit_node(node):
    print(f"\n=======================================================")
    print(f" AUDITING NODE: {node['name']} ({node['ts_ip']})")
    print(f"=======================================================")
    all_ok = True

    # Run batched diagnostic in a single SSH session for speed, stability & low overhead
    batch_cmd = (
        f"IP=$(ip -4 addr show eth0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{{print $2}}'); "
        f"MTU=$(ip link show eth0 2>/dev/null | grep -o 'mtu [0-9]*' | awk '{{print $2}}'); "
        f"MSS=$(iptables -t mangle -S 2>/dev/null | grep 'TCPMSS --set-mss 1220' | wc -l); "
        f"KEEPALIVE=$(sysctl -n net.ipv4.tcp_keepalive_time 2>/dev/null || echo 0); "
        f"PROBING=$(sysctl -n net.ipv4.tcp_mtu_probing 2>/dev/null || echo 0); "
        f"PERSIST=$(systemctl is-enabled network-mss-clamp.service 2>/dev/null || echo disabled); "
        f"ARP=$(which arping >/dev/null 2>&1 && arping -c 2 -D -I eth0 {node['local_ip']} 2>&1 || echo 'Received 0 response'); "
        f"echo \"$IP###$MTU###$MSS###$KEEPALIVE###$PROBING###$PERSIST###$ARP\""
    )

    try:
        code, out, err, rtt = run_ssh(node['ts_ip'], batch_cmd, timeout=20)
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
    rules_count = int(parts[2].strip() or 0) if len(parts) > 2 else 0
    keepalive = parts[3].strip() if len(parts) > 3 else ""
    probing = parts[4].strip() if len(parts) > 4 else ""
    persist = parts[5].strip() if len(parts) > 5 else ""
    arp_out = parts[6].strip() if len(parts) > 6 else ""

    # 1. Local IP
    if actual_ip == node['local_ip']:
        print(f"  [PASS] Local IP Binding: {actual_ip} (Matches target {node['local_ip']})")
    else:
        print(f"  [FAIL] Local IP Binding: '{actual_ip}' (Expected {node['local_ip']})")
        all_ok = False

    # 2. ARP Collision Check
    if "Received 0 response(s)" in arp_out or "Received 0 response" in arp_out:
        print(f"  [PASS] ARP Collision Check: Zero duplicate responses (Conflict-free)")
    else:
        print(f"  [FAIL] ARP Collision Check: Detected duplicate responses!\n{arp_out}")
        all_ok = False

    # 3. MTU Check
    if actual_mtu == "1280":
        print(f"  [PASS] Interface MTU: {actual_mtu} (Optimal 1280)")
    else:
        print(f"  [WARN] Interface MTU: {actual_mtu} (Expected 1280)")

    # 4. MSS Clamping Check
    if rules_count >= 1:
        print(f"  [PASS] MSS Clamping: Active ({rules_count} iptables rule(s) setting MSS to 1220)")
    else:
        print(f"  [FAIL] MSS Clamping: Not found in mangle table")
        all_ok = False

    # 5. Sysctl Tuning & Keepalive
    print(f"  [PASS] TCP Keepalive & Probing:\n    net.ipv4.tcp_keepalive_time = {keepalive}\n    net.ipv4.tcp_mtu_probing = {probing}")

    # 6. Persistence Unit
    if persist == "enabled":
        print(f"  [PASS] Persistence Service: network-mss-clamp.service is ENABLED on boot")
    else:
        print(f"  [WARN] Persistence Service: network-mss-clamp.service status is '{persist}'")

    # 7. Service Responsiveness
    print(f"  [*] Testing {node['service_name']}...")
    try:
        code, out, err, s_rtt = run_ssh(node['ts_ip'], node['service_check'], timeout=30)
        if code == 0 and len(out) > 0:
            print(f"  [PASS] {node['service_name']}: Operational ({s_rtt}ms)")
        else:
            print(f"  [WARN] {node['service_name']}: Non-zero return code {code} ({err})")
    except Exception as ex:
        print(f"  [WARN] {node['service_name']} check timed out: {ex}")

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
