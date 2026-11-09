#!/usr/bin/env bash
# ==========================================================
# Run inside EVE-NG VM as root
# Fixes permissions and validates image directory structure
# ==========================================================

echo "=== TVI EVE-NG Node & Directory Verification ==="

QEMU_DIR="/opt/unetlab/addons/qemu"

if [ ! -d "$QEMU_DIR" ]; then
    echo "[!] Error: Not running inside EVE-NG (missing $QEMU_DIR)"
    exit 1
fi

echo "[*] Checking router image folder ($QEMU_DIR/vios-152M3)..."
if [ -d "$QEMU_DIR/vios-152M3" ]; then
    ls -lh "$QEMU_DIR/vios-152M3"
else
    echo "[!] Warning: Folder 'vios-152M3' not found in $QEMU_DIR."
fi

echo "[*] Checking switch image folder ($QEMU_DIR/viosl2-1524)..."
if [ -d "$QEMU_DIR/viosl2-1524" ]; then
    ls -lh "$QEMU_DIR/viosl2-1524"
else
    echo "[!] Warning: Folder 'viosl2-1524' not found in $QEMU_DIR."
fi

echo "[*] Running unl_wrapper fixpermissions..."
/opt/unetlab/wrapper/unl_wrapper -a fixpermissions

echo "=== Done! Permissions have been restored ==="
