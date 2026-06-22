#!/bin/bash
# =============================================================================
# setup_defender.sh — Software provisioning for Defender Nodes (VM 310 / 320)
# =============================================================================
# Run INSIDE: VM 310 (defender-a) or VM 320 (defender-b) as root/sudo user
#
# Installs:  Python 3, PyTorch (CPU), Avalanche (CL), Flower (FL client),
#            NFStream (ETA), scikit-learn, pandas, TensorBoard
# Configures: tmpfs RAM disk for flow capture I/O buffering
# =============================================================================
set -euo pipefail

echo "============================================"
echo " Defender Node Setup"
echo "============================================"

# --- System packages ---
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "[2/7] Installing system dependencies..."
sudo apt install -y \
    python3 python3-pip python3-venv \
    libpcap-dev \
    tcpdump \
    git curl wget \
    build-essential

# --- RAM Disk for NFStream I/O buffering ---
echo "[3/7] Configuring tmpfs RAM disk (4 GB)..."
sudo mkdir -p /mnt/ramdisk
if mountpoint -q /mnt/ramdisk; then
    echo "  RAM disk already mounted."
else
    sudo mount -t tmpfs -o size=4G tmpfs /mnt/ramdisk
fi
# Make persistent across reboots
if ! grep -q "/mnt/ramdisk" /etc/fstab; then
    echo "tmpfs /mnt/ramdisk tmpfs size=4G 0 0" | sudo tee -a /etc/fstab
fi
sudo mkdir -p /mnt/ramdisk/flows

# --- Python environment ---
echo "[4/7] Creating Python virtual environment..."
python3 -m venv ~/fl-cl-env
source ~/fl-cl-env/bin/activate

echo "[5/7] Installing PyTorch (CPU)..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

echo "[6/7] Installing ML & FL-CL stack..."
pip install \
    avalanche-lib \
    flwr \
    nfstream \
    scikit-learn \
    pandas \
    numpy \
    tensorboard

echo "[7/7] Verifying installation..."
python3 -c "import torch; print(f'PyTorch:    {torch.__version__}')"
python3 -c "import avalanche; print(f'Avalanche:  {avalanche.__version__}')"
python3 -c "import flwr; print(f'Flower:     {flwr.__version__}')"
python3 -c "import nfstream; print(f'NFStream:   {nfstream.__version__}')"

echo ""
echo "============================================"
echo " ✓ Defender node setup complete"
echo "============================================"
echo ""
echo "Quick start commands:"
echo "  source ~/fl-cl-env/bin/activate"
echo "  python3 extractor.py --interface ens19 --out-dir /mnt/ramdisk/flows/"
echo "  python3 client.py --server 10.10.130.10:8080 --client-id A"
echo ""
echo "Verify capture interface receives mirrored traffic:"
echo "  sudo tcpdump -i ens19 -c 10"
