#!/usr/bin/env python3
"""
TVI Network Automation Script - Step 9
Infrastructure-as-Code (IaC) Provisioning & Backup Engine
Supports Cisco IOS / IOS-XE switches in TVI Multi-Site Topology.
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from getpass import getpass

try:
    from netmiko import (
        ConnectHandler,
        NetmikoTimeoutException,
        NetmikoAuthenticationException,
    )
except ImportError:
    print("[ERROR] 'netmiko' library is not installed.")
    print("Please activate your virtualenv or run: pip install -r requirements.txt")
    sys.exit(1)

# Base Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "inventory.yaml")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# 1. Setup Logging
log_file = os.path.join(LOG_DIR, "automation.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger("TVI_Automation")
if not logger.handlers:
    logger.addHandler(console_handler)

# 2. Desired Configuration Baseline
BASELINE_CONFIGS = [
    "ntp server 10.10.254.1",
    "banner motd ^C Unauthorized access to TVI Corporate Infrastructure is prohibited. ^C",
    "logging buffered 64000 informational",
]

TARGET_VLANS = {
    "10": "EXEC_FINANCE",
    "20": "RND_ENGINEERING",
    "30": "LOGISTICS_OPS",
    "99": "MANAGEMENT",
}


def load_inventory(filepath=INVENTORY_FILE):
    """Load and validate devices from inventory.yaml."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Inventory file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "devices" not in data:
        raise ValueError("Invalid inventory format: missing 'devices' root key.")
    return data["devices"]


def get_credentials():
    """Retrieve credentials from environment or interactive prompt."""
    username = os.environ.get("TVI_USER")
    password = os.environ.get("TVI_PASS")

    if not username:
        username = input("Enter SSH Username [default: admin]: ").strip() or "admin"
    if not password:
        password = getpass("Enter SSH Password: ")

    return username, password


def backup_device(net_connect, hostname):
    """Capture running-config and ip interface brief with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = os.path.join(BACKUP_DIR, f"{hostname}_{timestamp}_backup.cfg")

    running_config = net_connect.send_command("show running-config")
    int_brief = net_connect.send_command("show ip interface brief")

    with open(backup_filename, "w", encoding="utf-8") as bf:
        bf.write(f"! TVI CONFIGURATION BACKUP - {hostname}\n")
        bf.write(f"! TIMESTAMP: {timestamp}\n")
        bf.write("! " + "=" * 60 + "\n\n")
        bf.write("! --- IP INTERFACE BRIEF ---\n")
        bf.write(int_brief + "\n\n")
        bf.write("! --- RUNNING CONFIGURATION ---\n")
        bf.write(running_config)

    logger.info(f"[{hostname}] Backup saved to {os.path.basename(backup_filename)}")
    return backup_filename


def get_missing_vlans(net_connect):
    """Inspect current switch VLAN database to ensure idempotency."""
    vlan_output = net_connect.send_command("show vlan brief")
    commands_to_send = []

    for vlan_id, vlan_name in TARGET_VLANS.items():
        # If VLAN ID is missing or name doesn't match
        if vlan_id not in vlan_output:
            commands_to_send.extend([f"vlan {vlan_id}", f"name {vlan_name}"])
        else:
            # Check if name is present on the same line
            line_match = [line for line in vlan_output.splitlines() if line.startswith(f"{vlan_id} ") or line.startswith(f"{vlan_id}\t")]
            if line_match and vlan_name not in line_match[0]:
                commands_to_send.extend([f"vlan {vlan_id}", f"name {vlan_name}"])

    return commands_to_send


def provision_device(device_info, username, password):
    """Connect to a single device, backup state, and deploy idempotent configuration."""
    hostname = device_info.get("hostname", "Unknown")
    ip = device_info["ip"]
    device_type = device_info.get("device_type", "cisco_ios")
    port = device_info.get("port", 22)

    logger.info(f"Connecting to {hostname} ({ip}:{port})...")

    conn_params = {
        "device_type": device_type,
        "host": ip,
        "username": username,
        "password": password,
        "port": port,
        "timeout": 12,
        "session_log": os.path.join(LOG_DIR, f"{hostname}_session.log"),
    }

    try:
        with ConnectHandler(**conn_params) as net_connect:
            net_connect.enable()
            logger.info(f"[{hostname}] SSH connection established successfully.")

            # 1. State Capture & Backup
            backup_device(net_connect, hostname)

            # 2. Idempotent VLAN Provisioning
            vlan_commands = get_missing_vlans(net_connect)
            if vlan_commands:
                logger.info(f"[{hostname}] Deploying missing VLANs: {vlan_commands}")
                vlan_out = net_connect.send_config_set(vlan_commands)
                logger.debug(f"[{hostname}] VLAN config output:\n{vlan_out}")
            else:
                logger.info(f"[{hostname}] All required corporate VLANs already present (Idempotent: No change).")

            # 3. Baseline Push (NTP, Banner, Logging)
            logger.info(f"[{hostname}] Applying baseline system configuration...")
            baseline_out = net_connect.send_config_set(BASELINE_CONFIGS)
            logger.debug(f"[{hostname}] Baseline config output:\n{baseline_out}")

            # 4. Save Running Configuration
            net_connect.send_command("write memory")
            logger.info(f"[{hostname}] Running-config committed to NVRAM (write memory).")

            return True

    except NetmikoTimeoutException:
        err = f"[{hostname}] Connection TIMEOUT to {ip}:{port}. Check node status or EVE routing."
        logger.error(err)
        return False
    except NetmikoAuthenticationException:
        err = f"[{hostname}] Authentication FAILED for user '{username}'. Check credentials."
        logger.error(err)
        return False
    except Exception as exc:
        err = f"[{hostname}] Unexpected error: {str(exc)}"
        logger.error(err, exc_info=True)
        return False


def main():
    print("=" * 65)
    print(" TechViet Innovations (TVI) - Network Automation Engine")
    print(" Automated Provisioning, Idempotency & Backup (Step 9)")
    print("=" * 65)

    try:
        devices = load_inventory()
    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
        sys.exit(1)

    username, password = get_credentials()

    total = len(devices)
    success = 0
    failed = 0

    print(f"\nDiscovered {total} device(s) in inventory. Beginning provisioning run...\n")

    for dev in devices:
        res = provision_device(dev, username, password)
        if res:
            success += 1
        else:
            failed += 1
        print("-" * 50)

    summary = (
        f"\nAutomation Run Summary:\n"
        f"  Total Devices : {total}\n"
        f"  Success       : {success}\n"
        f"  Failed        : {failed}\n"
        f"Check '{log_file}' for complete execution audit trail."
    )
    print(summary)
    logger.info(summary.replace("\n", " | "))

    if failed > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
