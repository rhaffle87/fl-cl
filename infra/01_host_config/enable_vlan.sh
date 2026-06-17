#!/bin/bash
# =============================================================================
# enable_vlan.sh — Enable VLAN awareness on vmbr1
# =============================================================================
# Run on: Node 'its' and Node 'pve' (already enabled on 'node2')
# Requires: ifupdown2 installed on the host
#
# Usage:
#   chmod +x enable_vlan.sh
#   sudo ./enable_vlan.sh
# =============================================================================
set -euo pipefail

BRIDGE="vmbr1"
CONFIG="/etc/network/interfaces"

echo "[1/3] Checking current VLAN awareness on $BRIDGE..."
if grep -q "bridge-vlan-aware yes" "$CONFIG"; then
    echo "  ✓ VLAN awareness already enabled on $BRIDGE. No changes needed."
    exit 0
fi

echo "[2/3] Enabling VLAN awareness in $CONFIG..."
cp "$CONFIG" "${CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
sed -i "/iface $BRIDGE inet manual/a \\        bridge-vlan-aware yes" "$CONFIG"

echo "[3/3] Applying network configuration (no reboot required)..."
ifup --force "$BRIDGE"

echo ""
echo "=== Verification ==="
bridge vlan show "$BRIDGE"
echo ""
echo "✓ VLAN awareness enabled on $BRIDGE successfully."
