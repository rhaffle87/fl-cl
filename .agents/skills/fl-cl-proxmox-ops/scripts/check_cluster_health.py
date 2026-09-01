#!/usr/bin/env python3
"""
check_cluster_health.py
=======================
Audits connectivity and service availability across the FL-CL Proxmox VE testbed nodes.
"""

import argparse
import socket

NODES = [
    {
        "id": "LXC 300",
        "name": "fl-aggregator",
        "ip": "10.10.130.10",
        "ports": [
            (8080, "Flower gRPC"),
            (5000, "MLflow UI"),
            (9091, "Prometheus Gateway"),
        ],
    },
    {
        "id": "VM 310",
        "name": "defender-a",
        "ip": "10.10.130.11",
        "ports": [(22, "SSH"), (8000, "Inference API")],
    },
    {
        "id": "VM 320",
        "name": "defender-b",
        "ip": "10.10.130.12",
        "ports": [(22, "SSH"), (8000, "Inference API")],
    },
    {
        "id": "VM 330",
        "name": "attacker",
        "ip": "10.10.130.13",
        "ports": [(22, "SSH")],
    },
]


def check_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def run_health_check(timeout: float = 1.0) -> bool:
    print(f"{'='*75}")
    print(f"FL-CL Proxmox VE Testbed Health Audit (Timeout: {timeout}s)")
    print(f"{'='*75}")
    print(
        f"{'Node ID':<10} | {'Hostname':<15} | {'IP Address':<15} | {'Service':<18} | {'Status'}"
    )
    print(f"{'-'*75}")

    all_reachable = True

    for node in NODES:
        node_id = node["id"]
        hostname = node["name"]
        ip = node["ip"]

        for port, service_name in node["ports"]:
            is_open = check_port(ip, port, timeout=timeout)
            status_str = "[OK] OPEN" if is_open else "[WARN] CLOSED/UNREACHABLE"
            if not is_open:
                all_reachable = False
            print(
                f"{node_id:<10} | {hostname:<15} | {ip:<15} | {f'{service_name} (:{port})':<18} | {status_str}"
            )

    print(f"{'='*75}")
    if all_reachable:
        print(
            "[AUDIT SUCCESS] All cluster nodes and services are active and reachable."
        )
    else:
        print(
            "[AUDIT NOTICE] Some remote testbed services are unreachable (expected if running outside the Proxmox L2 VLAN)."
        )

    return all_reachable


def main():
    parser = argparse.ArgumentParser(
        description="Audit FL-CL Proxmox VE cluster health."
    )
    parser.add_argument(
        "--timeout", type=float, default=0.5, help="Socket connect timeout in seconds"
    )
    args = parser.parse_args()

    run_health_check(timeout=args.timeout)


if __name__ == "__main__":
    main()
