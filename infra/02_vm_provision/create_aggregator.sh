#!/bin/bash
# =============================================================================
# create_aggregator.sh — Deploy FL Aggregator LXC Container
# =============================================================================
# Run on:  Node 'pve' (hypervisor shell as root)
# Creates: LXC 300 (fl-aggregator) on VLAN 130
#
# Prerequisites:
#   - Ubuntu 24.04 template downloaded:
#     pveam update && pveam download local ubuntu-24.04-standard_24.04-1_amd64.tar.zst
#   - VLAN awareness enabled on vmbr1 (run 01_host_config/enable_vlan.sh)
#   - Snippet storage enabled (run 01_host_config/enable_snippets.sh)
# =============================================================================
set -euo pipefail

CTID=300
HOSTNAME="fl-aggregator"
TEMPLATE="local:vztmpl/ubuntu-24.04-standard_24.04-1_amd64.tar.zst"

echo "============================================"
echo " Deploying FL Aggregator — LXC $CTID"
echo " Node: pve | VLAN: 130 | IP: 10.10.10.130"
echo "============================================"

# Check if template exists
if ! pveam list local | grep -q "ubuntu-24.04"; then
    echo "[!] Template not found. Downloading..."
    pveam update
    pveam download local ubuntu-24.04-standard_24.04-1_amd64.tar.zst
fi

# Check if CT already exists
if pct status $CTID &>/dev/null; then
    echo "[!] LXC $CTID already exists. Skipping creation."
    echo "    To recreate: pct destroy $CTID --purge && bash $0"
    exit 1
fi

echo "[1/3] Creating LXC container..."
pct create $CTID $TEMPLATE \
    --cores 4 \
    --memory 8192 \
    --swap 2048 \
    --hostname $HOSTNAME \
    --ostype ubuntu \
    --rootfs local-lvm:50 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --net1 name=eth1,bridge=vmbr1,tag=130,ip=10.10.10.130/24 \
    --onboot 1 \
    --unprivileged 1

echo "[2/3] Starting container..."
pct start $CTID

echo "[3/3] Verifying..."
sleep 3
pct status $CTID

echo ""
echo "✓ LXC $CTID ($HOSTNAME) deployed successfully."
echo "  Enter with:  pct enter $CTID"
echo "  Then run:    bash /root/setup_aggregator.sh  (after copying 04_guest_setup/)"
