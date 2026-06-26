#!/bin/bash
# =============================================================================
# create_defender_b.sh — Deploy Defender Node B VM
# =============================================================================
# Run on:  Node 'node2' (hypervisor shell as root)
# Creates: VM 320 (defender-b) on VLAN 130
#
# Identical role to Defender A but simulates a separate organization.
# =============================================================================
set -euo pipefail

VMID=320
NAME="defender-b"
VLAN=130

echo "============================================"
echo " Deploying Defender Node B — VM $VMID"
echo " Node: node2 | VLAN: $VLAN"
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
    --net1 virtio,bridge=vmbr1 \
    --scsihw virtio-scsi-pci \
    --scsi0 local-lvm:100,discard=on \
    --ide2 local:iso/ubuntu-24.04.2-live-server-amd64.iso,media=cdrom \
    --boot order='ide2;scsi0' \
    --onboot 1

echo "[2/2] Verifying..."
qm config $VMID | grep -E "^(name|cores|memory|net)"

echo ""
echo "✓ VM $VMID ($NAME) created. Start with: qm start $VMID"
