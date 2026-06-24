#!/bin/bash
# =============================================================================
# enable_promisc.sh — Deploy Persistent Promiscuous Mode on LACP Bonds/Bridges
# =============================================================================
# Run on: Node 'its' and Node 'node2' (hypervisor shells as root)
#
# This script creates and enables a systemd service that enforces promiscuous
# mode on physical NICs, LACP bonds, and bridges prior to VM boot. This prevents
# LACP renegotiation link flaps and Corosync cluster timeouts when VM capture
# interfaces go live in promiscuous mode.
# =============================================================================
set -euo pipefail

echo "============================================"
echo " Configuring Persistent Promiscuous Mode"
echo "============================================"

# Identify physical interfaces in the bond (default to eno1/eno3 on 'its', eno1/eno2 on 'node2')
HOSTNAME=$(hostname)
PHYSICAL_NICS=()

if [[ "$HOSTNAME" == "its" ]]; then
    PHYSICAL_NICS=("eno1" "eno3")
elif [[ "$HOSTNAME" == "node2" ]]; then
    PHYSICAL_NICS=("eno1" "eno3")
else
    # Auto-detect interfaces in bond0 as fallback
    if [ -d "/sys/class/net/bond0/bonding" ]; then
        PHYSICAL_NICS=($(ls /sys/class/net/bond0/lower_* 2>/dev/null | sed 's|.*/lower_||'))
    fi
fi

if [ ${#PHYSICAL_NICS[@]} -eq 0 ]; then
    echo "[!] No physical NICs identified for bond0. Fallback configuration."
    PHYSICAL_NICS=("eno1" "eno3")
fi

echo "[1/3] Generating promisc-bond.service..."
SERVICE_FILE="/etc/systemd/system/promisc-bond.service"

cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Pre-enable promiscuous mode on bond0/vmbr1 for VM capture interfaces
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
EOF

# Append ExecStart lines for each interface
for nic in "${PHYSICAL_NICS[@]}"; do
    echo "ExecStart=/sbin/ip link set dev $nic promisc on" >> "$SERVICE_FILE"
done

cat << EOF >> "$SERVICE_FILE"
ExecStart=/sbin/ip link set dev bond0 promisc on
ExecStart=/sbin/ip link set dev vmbr1 promisc on

[Install]
WantedBy=multi-user.target
EOF

echo "[2/3] Reloading systemd daemon..."
systemctl daemon-reload

echo "[3/3] Enabling and starting promisc-bond.service..."
systemctl enable promisc-bond.service
systemctl restart promisc-bond.service

echo ""
echo "=== Verification ==="
for dev in "${PHYSICAL_NICS[@]}" bond0 vmbr1; do
    if ip link show dev "$dev" | grep -q "PROMISC"; then
        echo "  ✓ $dev is in PROMISC mode"
    else
        echo "  ✗ $dev is NOT in PROMISC mode"
    fi
done

echo ""
echo "✓ Persistent promiscuous mode service configured and activated."
