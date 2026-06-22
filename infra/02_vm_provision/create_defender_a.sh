#!/bin/bash
# =============================================================================
# create_defender_a.sh — Deploy Defender Node A VM
# =============================================================================
# Run on:  Node 'its' (hypervisor shell as root)
# Creates: VM 310 (defender-a) on VLAN 110
#
# This VM runs: NFStream capture, PyTorch model, Avalanche EWC, Flower client
# Dual NIC: net0=vmbr0 (mgmt/internet), net1=vmbr1 VLAN 110 (capture interface)
#
# Prerequisites:
#   - Ubuntu 24.04 ISO uploaded to local storage
#   - VLAN awareness enabled on vmbr1
# =============================================================================
set -euo pipefail

VMID=310
NAME="defender-a"
VLAN=110

echo "============================================"
echo " Deploying Defender Node A — VM $VMID"
echo " Node: its | VLAN: $VLAN"
echo "============================================"

if qm status $VMID &>/dev/null; then
    echo "[!] VM $VMID already exists. Skipping."
    exit 1
fi

echo "[1/2] Creating VM..."
qm create $VMID \
    --name $NAME \
    --cores 8 \
    --memory 16384 \
    --balloon 8192 \
    --cpu host \
    --sockets 1 \
    --ostype l26 \
    --net0 virtio,bridge=vmbr0 \
    --net1 virtio,bridge=vmbr1,tag=$VLAN \
    --scsihw virtio-scsi-pci \
    --scsi0 local-lvm:100,discard=on \
    --ide2 local:iso/ubuntu-24.04.1-live-server-amd64.iso,media=cdrom \
    --boot order='ide2;scsi0' \
    --onboot 1

echo "[2/2] Verifying..."
qm config $VMID | grep -E "^(name|cores|memory|net)"

echo ""
echo "✓ VM $VMID ($NAME) created. Start with: qm start $VMID"
echo "  Install Ubuntu, then run 04_guest_setup/setup_defender.sh inside the VM."
