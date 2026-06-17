#!/bin/bash
# =============================================================================
# enable_snippets.sh — Allow hookscript storage on PVE local storage
# =============================================================================
# Run on: ALL 3 nodes (its, node2, pve)
#
# Usage:
#   chmod +x enable_snippets.sh
#   sudo ./enable_snippets.sh
# =============================================================================
set -euo pipefail

echo "[1/2] Enabling snippet content type on 'local' storage..."
pvesm set local --content backup,vztmpl,iso,snippets

echo "[2/2] Creating snippets directory..."
mkdir -p /var/lib/vz/snippets

echo "✓ Snippet storage enabled. Hookscripts can now be stored in /var/lib/vz/snippets/"
