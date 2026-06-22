#!/bin/bash
# =============================================================================
# create_target_b1.sh — Deploy Target Host B1
# =============================================================================
# Run on:  Node 'node2' (MUST be same node as defender-b for port mirroring)
# Creates: VM 321 (target-b1) on VLAN 120
# =============================================================================
set -euo pipefail

VMID=321
NAME="target-b1"
VLAN=120

echo "============================================"
echo " Deploying Target Host B1 — VM $VMID"
echo " Node: node2 | VLAN: $VLAN"
echo "============================================"

if qm status $VMID &>/dev/null; then
    echo "[!] VM $VMID already exists. Skipping."
    exit 1
fi

qm create $VMID \
    --name $NAME \
    --cores 1 \
    --memory 1024 \
    --ostype l26 \
    --net0 virtio,bridge=vmbr1,tag=$VLAN \
    --scsihw virtio-scsi-pci \
    --scsi0 local-lvm:10,discard=on \
    --ide2 local:iso/alpine-virt-3.20.0-x86_64.iso,media=cdrom \
    --boot order='ide2;scsi0'

echo "✓ VM $VMID ($NAME) created."
echo "  After OS install, bind hookscript: qm set $VMID --hookscript local:snippets/mirror-hook-b.sh"
