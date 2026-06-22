#!/bin/bash
# =============================================================================
# mirror-hook-a.sh — Port Mirroring: Target A1 (VM 311) → Defender A (VM 310)
# =============================================================================
# Deploy to:  /var/lib/vz/snippets/mirror-hook-a.sh  on Node 'its'
# Bind with:  qm set 311 --hookscript local:snippets/mirror-hook-a.sh
#
# How it works:
#   Proxmox fires this script at VM lifecycle events. On 'post-start',
#   it configures tc (traffic control) rules to copy all packets from the
#   target VM's TAP interface to the defender VM's capture TAP interface.
#   This survives VM reboots because the hookscript re-applies rules
#   every time the target VM starts.
# =============================================================================

vmid=$1
phase=$2

# Only act on VM 311 post-start
if [ "$vmid" != "311" ] || [ "$phase" != "post-start" ]; then
    exit 0
fi

SOURCE="tap311i0"   # Target A1's net0 on vmbr1
MIRROR="tap310i1"   # Defender A's net1 (capture) on vmbr1

echo "$(date '+%F %T') [mirror-hook-a] VM $vmid $phase — configuring $SOURCE → $MIRROR"

# Wait for TAP interfaces to register in the bridge
sleep 3

# Verify interfaces exist
if ! ip link show "$SOURCE" &>/dev/null; then
    echo "[mirror-hook-a] ERROR: $SOURCE not found. Aborting."
    exit 1
fi
if ! ip link show "$MIRROR" &>/dev/null; then
    echo "[mirror-hook-a] ERROR: $MIRROR not found. Aborting."
    exit 1
fi

# Enable promiscuous mode
ip link set dev "$SOURCE" promisc on
ip link set dev "$MIRROR" promisc on

# Clear any stale rules
tc qdisc del dev "$SOURCE" ingress 2>/dev/null || true
tc qdisc del dev "$SOURCE" root 2>/dev/null || true

# Ingress mirror: packets arriving at the target → copied to defender
tc qdisc add dev "$SOURCE" handle ffff: ingress
tc filter add dev "$SOURCE" parent ffff: protocol all u32 match u32 0 0 \
    action mirred egress mirror dev "$MIRROR"

# Egress mirror: packets leaving the target → copied to defender
tc qdisc add dev "$SOURCE" root handle 1: prio
tc filter add dev "$SOURCE" parent 1: protocol all u32 match u32 0 0 \
    action mirred egress mirror dev "$MIRROR"

echo "$(date '+%F %T') [mirror-hook-a] ✓ Port mirroring active: $SOURCE → $MIRROR"
