#!/usr/bin/env bash
# ==========================================================
# TVI Enterprise Network - Linux/macOS Environment Setup Script
# ==========================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=========================================================="
echo "  TVI Enterprise Network - Environment Setup (Linux/macOS)"
echo "=========================================================="

# Check Python 3
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Python 3 is not installed. Please install python3 and python3-venv."
    exit 1
fi

echo "[+] Using $($PYTHON_CMD --version)"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating virtual environment at '$VENV_DIR'..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "[+] Virtual environment created."
else
    echo "[+] Virtual environment already exists at '$VENV_DIR'."
fi

# Install dependencies
echo "[*] Installing dependencies from requirements.txt..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

# Verify
echo "[*] Verifying netmiko and pyyaml..."
"$VENV_DIR/bin/python" -c "import netmiko; import yaml; print(f'Netmiko: {netmiko.__version__}'); print(f'PyYAML: {yaml.__version__}')"

echo "=========================================================="
echo "  Setup completed! To activate the environment run:"
echo "    source .venv/bin/activate"
echo "  To run automation:"
echo "    python Automation/auto_provision.py"
echo "=========================================================="
