#!/bin/bash
# =============================================================================
# setup_traffic_gen.sh — Software provisioning for Traffic Generator (VM 400)
# =============================================================================
# Run INSIDE: VM 400 (traffic-gen / Kali Linux) as root
#
# Installs: tcpreplay, hydra, metasploit (pre-installed on Kali),
#           selenium, chromium-driver, locust, slowloris
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

echo "[3/5] Setting up Python automation environment..."
# Create the virtual environment
python3 -m venv ~/traffic-env

# Activate the virtual environment
source ~/traffic-env/bin/activate

# Upgrade pip inside the environment
pip install --upgrade pip

# Install all Python dependencies inside the environment (including slowloris)
pip install \
    slowloris \
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
echo "Usage notes:"
echo "  To run your Python tools (locust, slowloris), remember to activate the environment first:"
echo "  source ~/traffic-env/bin/activate"
echo ""
echo "Usage examples:"
echo "  # Replay benchmark PCAP over flat L2 network interface (eth1)"
echo "  tcpreplay --intf1=eth1 --multiplier=2.0 --loop=5 /datasets/CIC-IDS2017-Friday.pcap"
echo ""
echo "  # SSH test"
echo "  hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://${TARGET_A_HOST:-10.10.110.15}"
echo ""
echo "  # HTTPS slowloris (inside venv)"
echo "  slowloris ${TARGET_A_HOST:-10.10.110.15} -p 443"
