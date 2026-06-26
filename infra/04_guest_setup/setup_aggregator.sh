#!/bin/bash
# =============================================================================
# setup_aggregator.sh — Software provisioning for FL Aggregator (LXC 300)
# =============================================================================
# Run INSIDE: LXC 300 (fl-aggregator) as root
#
# Installs:  Python 3, Flower (FL server), MLflow (experiment tracking)
# =============================================================================
set -euo pipefail

echo "============================================"
echo " FL Aggregator Setup — LXC 300"
echo "============================================"

echo "[1/5] Updating system packages..."
apt update && apt upgrade -y

echo "[2/5] Installing system dependencies..."
apt install -y python3 python3-pip python3-venv git curl

echo "[3/5] Creating Python virtual environment..."
python3 -m venv /opt/flower-env
source /opt/flower-env/bin/activate

echo "[4/5] Installing Python packages..."
pip install --upgrade pip
pip install flwr          # Federated Learning server
pip install mlflow        # Experiment tracking

echo "[5/5] Verifying installation..."
python3 -c "import flwr; print(f'Flower version: {flwr.__version__}')"
python3 -c "import mlflow; print(f'MLflow version: {mlflow.__version__}')"

echo ""
echo "============================================"
echo " ✓ Aggregator setup complete"
echo "============================================"
echo ""
echo "Quick start commands:"
echo "  source /opt/flower-env/bin/activate"
echo "  python3 ~/server.py                                 # Start FL server"
echo "  mlflow server --host 0.0.0.0 --port 5000            # Start MLflow UI"
echo ""
echo "Orchestration copies server files to ~/ (root's home directory)."
