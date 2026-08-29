#!/bin/bash
# =============================================================================
# setup_traffic_gen.sh — Software provisioning for Traffic Generator (VM 400)
# =============================================================================
# Run INSIDE: VM 400 (traffic-gen / Kali Linux) as root
#
# Installs: tcpreplay, hydra, ncrack, medusa, slowhttptest, hping3, scapy,
#           selenium, chromium-driver, locust, slowloris, metasploit
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

echo "[2/5] Installing traffic tools and attack binaries..."
apt install -y \
    tcpreplay \
    hydra \
    ncrack \
    medusa \
    slowhttptest \
    hping3 \
    iodine \
    chromium-driver \
    python3 python3-pip python3-venv python3-scapy

echo "[3/5] Setting up Python automation environment..."
# Create the virtual environment
python3 -m venv ~/traffic-env

# Activate the virtual environment
source ~/traffic-env/bin/activate

# Upgrade pip inside the environment
pip install --upgrade pip

# Install all Python dependencies inside the environment
pip install \
    slowloris \
    scapy \
    paramiko \
    selenium \
    locust \
    requests

echo "[4/5] Creating dataset directory..."
mkdir -p /datasets
echo "  Download benchmark PCAPs into /datasets/:"
echo "    - USTC-TFC2016:        https://github.com/yungshenglu/USTC-TFC2016"
echo "    - CIC-IDS2017:         https://www.unb.ca/cic/datasets/ids-2017.html"
echo "    - CIRA-CIC-DoHBrw-2020: https://www.unb.ca/cic/datasets/dohbrw-2020.html"

echo "[5/5] Verifying Metasploit & Attack Binaries..."
for tool in hydra ncrack slowhttptest hping3 msfconsole; do
    if command -v "$tool" &>/dev/null; then
        echo "  ✓ $tool available"
    else
        echo "  [!] $tool not found in system PATH"
    fi
done

echo ""
echo "============================================"
echo " ✓ Traffic generator setup complete"
echo "============================================"
echo ""
echo "Usage notes:"
echo "  To run traffic generation with modular engines (auto, kali, python):"
echo "  ~/traffic-env/bin/python3 ~/attack_flow.py --mode <mode> --target <target_ip> --engine auto"
echo ""
