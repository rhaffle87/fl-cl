#!/bin/bash
# =============================================================================
# create_traffic_gen.sh — Deploy Traffic Generator VM (Kali Linux)
# =============================================================================
# Run on:  Node 'node2' (hypervisor shell as root)
# Creates: VM 400 (traffic-gen) on VLAN 140
#
# Runs: Metasploit, Hydra, Slowloris, tcpreplay, Selenium
# =============================================================================
set -euo pipefail

VMID=400
NAME="traffic-gen"
VLAN=140

echo "============================================"
echo " Deploying Traffic Generator — VM $VMID"
echo " Node: node2 | VLAN: $VLAN"
echo "============================================"

if qm status $VMID &>/dev/null; then
    echo "[!] VM $VMID already exists. Skipping."
    exit 1
fi

qm create $VMID \
    --name $NAME \
    --cores 4 \
    --memory 4096 \
    --ostype l26 \
    --net0 virtio,bridge=vmbr0 \
    --net1 virtio,bridge=vmbr1 \
    --scsihw virtio-scsi-pci \
    --scsi0 local-lvm:50,discard=on \
    --ide2 local:iso/kali-linux-2024.4-installer-amd64.iso,media=cdrom \
    --boot order='ide2;scsi0'

echo "✓ VM $VMID ($NAME) created. Start with: qm start $VMID"
echo "  After OS install, run 04_guest_setup/setup_traffic_gen.sh inside the VM."
