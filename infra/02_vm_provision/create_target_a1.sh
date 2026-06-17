#!/bin/bash
# =============================================================================
# create_target_a1.sh — Deploy Target Host A1
# =============================================================================
# Run on:  Node 'its' (MUST be same node as defender-a for port mirroring)
# Creates: VM 101 (target-a1) on VLAN 10
#
# Lightweight Alpine VM that receives attack + benign traffic.
# =============================================================================
set -euo pipefail

VMID=101
NAME="target-a1"
VLAN=10

echo "============================================"
echo " Deploying Target Host A1 — VM $VMID"
echo " Node: its | VLAN: $VLAN"
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
echo "  After OS install, bind hookscript: qm set $VMID --hookscript local:snippets/mirror-hook-a.sh"
