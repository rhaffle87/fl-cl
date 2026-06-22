#!/bin/bash
# =============================================================================
# mirror-hook-b.sh — Port Mirroring: Target B1 (VM 321) → Defender B (VM 320)
# =============================================================================
# Deploy to:  /var/lib/vz/snippets/mirror-hook-b.sh  on Node 'node2'
# Bind with:  qm set 321 --hookscript local:snippets/mirror-hook-b.sh
# =============================================================================

vmid=$1
phase=$2

if [ "$vmid" != "321" ] || [ "$phase" != "post-start" ]; then
    exit 0
fi

SOURCE="tap321i0"   # Target B1's net0 on vmbr1
MIRROR="tap320i1"   # Defender B's net1 (capture) on vmbr1

echo "$(date '+%F %T') [mirror-hook-b] VM $vmid $phase — configuring $SOURCE → $MIRROR"

sleep 3

if ! ip link show "$SOURCE" &>/dev/null; then
    echo "[mirror-hook-b] ERROR: $SOURCE not found. Aborting."
    exit 1
fi
if ! ip link show "$MIRROR" &>/dev/null; then
    echo "[mirror-hook-b] ERROR: $MIRROR not found. Aborting."
    exit 1
fi

ip link set dev "$SOURCE" promisc on
ip link set dev "$MIRROR" promisc on

tc qdisc del dev "$SOURCE" ingress 2>/dev/null || true
tc qdisc del dev "$SOURCE" root 2>/dev/null || true

tc qdisc add dev "$SOURCE" handle ffff: ingress
tc filter add dev "$SOURCE" parent ffff: protocol all u32 match u32 0 0 \
    action mirred egress mirror dev "$MIRROR"

tc qdisc add dev "$SOURCE" root handle 1: prio
tc filter add dev "$SOURCE" parent 1: protocol all u32 match u32 0 0 \
    action mirred egress mirror dev "$MIRROR"

echo "$(date '+%F %T') [mirror-hook-b] ✓ Port mirroring active: $SOURCE → $MIRROR"
