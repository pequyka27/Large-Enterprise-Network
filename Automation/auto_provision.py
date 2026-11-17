#!/usr/bin/env python3
"""Back up and provision the TVI Cisco IOS switches over SSH."""
import argparse
import ipaddress
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

import yaml
from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)


SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
BACKUP_DIR = SCRIPT_DIR / "backups"
INVENTORY_FILE = SCRIPT_DIR / "inventory.yaml"
log_file = LOG_DIR / "automation.log"
logger = logging.getLogger("TVI_Automation")

BANNER_TEXT = "Unauthorized access to TVI Corporate Infrastructure is prohibited."
BASELINE_CONFIGS = [
    "ntp server 10.10.254.1",
    f"banner motd #{BANNER_TEXT}#",
    "logging buffered 64000 informational",
]
TARGET_VLANS = {
    "10": "EXEC_FINANCE",
    "20": "RND_ENGINEERING",
    "30": "LOGISTICS_OPS",
    "40": "GUEST",
    "99": "MANAGEMENT",
    "100": "HQ_TRANSIT",
    "999": "BLACKHOLE",
}
CLI_ERROR_PATTERN = (
    r"(?im)^\s*%\s*(?:Invalid|Incomplete|Ambiguous|Error|Access denied|"
    r"Authorization failed|Command authorization failed|Permission denied|"
    r"Failed|Unable|Cannot|Not enough|Bad|Unrecognized|Unknown command)"
)


def setup_logging():
    """Create log files only when the CLI actually starts an SSH run."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = logging.StreamHandler(sys.stdout)
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def load_inventory(filepath=INVENTORY_FILE):
    """Validate the complete inventory before connecting to any device."""
    with open(filepath, encoding="utf-8") as inventory_file:
        data = yaml.safe_load(inventory_file)
    if not isinstance(data, dict) or not isinstance(data.get("devices"), list):
        raise ValueError("Inventory must contain a 'devices' list.")
    if not data["devices"]:
        raise ValueError("Inventory must contain at least one device.")

    devices = []
    hostnames = set()
    endpoints = set()
    for index, item in enumerate(data["devices"], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Device {index} must be a mapping.")
        device = dict(item)
        hostname = device.get("hostname", "")
        if not isinstance(hostname, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*", hostname
        ):
            raise ValueError(f"Device {index} has an invalid hostname.")
        address = device.get("ip")
        if not isinstance(address, str):
            raise ValueError(f"[{hostname}] 'ip' must be an IP address or DNS hostname.")
        try:
            device["ip"] = str(ipaddress.ip_address(address))
        except ValueError as exc:
            labels = address.rstrip(".").split(".")
            invalid_labels = any(
                not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in labels
            )
            if invalid_labels or len(address) > 253 or all(label.isdecimal() for label in labels):
                raise ValueError(f"[{hostname}] Invalid IP address or DNS hostname: {address}") from exc
            device["ip"] = address.lower()
        port = device.get("port", 22)
        if isinstance(port, str) and port.isascii() and port.isdecimal():
            port = int(port)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError(f"[{hostname}] SSH port must be between 1 and 65535.")
        device["port"] = port
        device.setdefault("device_type", "cisco_ios")
        if device["device_type"] not in ("cisco_ios", "cisco_ios_ssh"):
            raise ValueError(f"[{hostname}] Only Cisco IOS SSH devices are supported.")
        endpoint = (device["ip"], port)
        if hostname.casefold() in hostnames or endpoint in endpoints:
            raise ValueError(f"[{hostname}] Duplicate hostname or SSH endpoint.")
        hostnames.add(hostname.casefold())
        endpoints.add(endpoint)
        devices.append(device)
    return devices


def get_credentials():
    """Read credentials from the environment or an interactive prompt."""
    username = os.environ.get("TVI_USER", "").strip()
    password = os.environ.get("TVI_PASS", "")
    if not username:
        username = input("Enter SSH Username [default: admin]: ").strip() or "admin"
    if not password:
        password = getpass("Enter SSH Password: ")
    if not password:
        raise ValueError("SSH password cannot be empty.")
    return username, password


def check_cli_response(output):
    """Treat IOS command failures as failed operations."""
    error = re.search(CLI_ERROR_PATTERN, output)
    if error:
        message = output[error.start():].strip().splitlines()[0]
        raise RuntimeError(f"IOS rejected a command: {message}")
    return output


def read_command(net_connect, command):
    return check_cli_response(net_connect.send_command(command, read_timeout=60))


def backup_device(net_connect, hostname, stage="before", running_config=None):
    """Publish a unique backup atomically after both show commands succeed."""
    if running_config is None:
        running_config = read_command(net_connect, "show running-config")
    int_brief = read_command(net_connect, "show ip interface brief")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=BACKUP_DIR,
            prefix=f"{hostname}_{timestamp}_{stage}_", suffix=".tmp", delete=False,
        ) as backup_file:
            temporary_path = Path(backup_file.name)
            backup_file.write(
                f"! TVI CONFIGURATION BACKUP - {hostname}\n"
                f"! TIMESTAMP UTC: {timestamp}\n! STAGE: {stage}\n\n"
                f"! --- IP INTERFACE BRIEF ---\n{int_brief}\n\n"
                f"! --- RUNNING CONFIGURATION ---\n{running_config}\n"
            )
        backup_path = temporary_path.with_suffix(".cfg")
        os.replace(temporary_path, backup_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    logger.info("[%s] Backup saved: %s", hostname, backup_path.name)
    return str(backup_path)


def get_missing_vlans(net_connect):
    """Match complete VLAN IDs and names, including IDs sharing a prefix."""
    vlan_output = read_command(net_connect, "show vlan brief")
    existing = dict(re.findall(r"(?m)^\s*(\d+)\s+(\S+)\s+\S+", vlan_output))
    commands = []
    for vlan_id, vlan_name in TARGET_VLANS.items():
        if existing.get(vlan_id) != vlan_name:
            commands.extend([f"vlan {vlan_id}", f"name {vlan_name}", "exit"])
    return commands


def get_missing_baseline(running_config):
    """Compare IOS running-config, including rendered banner delimiters."""
    lines = [line.strip() for line in running_config.splitlines()]
    commands = []
    if not any(
        re.match(r"ntp server\s+10\.10\.254\.1(?:\s|$)", line) for line in lines
    ):
        commands.append(BASELINE_CONFIGS[0])

    banner_text = None
    banner = re.search(r"(?m)^banner motd (\^.|[^\r\n])", running_config)
    if banner:
        end = running_config.find(banner.group(1), banner.end())
        if end >= 0:
            banner_text = running_config[banner.end():end].strip()
    if banner_text != BANNER_TEXT:
        commands.append(BASELINE_CONFIGS[1])
    if not any(
        re.fullmatch(r"logging buffered\s+64000\s+(?:informational|6)", line)
        for line in lines
    ):
        commands.append(BASELINE_CONFIGS[2])
    return commands


def startup_needs_save(net_connect, running_config):
    """Recover a previous failed save without reapplying correct commands."""
    startup_config = net_connect.send_command("show startup-config", read_timeout=60)
    if re.search(
        r"(?i)(non-volatile configuration memory is not present|"
        r"non-volatile configuration memory invalid|"
        r"error opening nvram:.*no such file)",
        startup_config,
    ):
        return True
    check_cli_response(startup_config)
    if get_missing_baseline(startup_config):
        return True
    # Some IOS images store VLANs in vlan.dat, while others also render them
    # in running/startup-config. Compare the VLANs rendered by this image.
    vlan_pattern = r"(?m)^vlan (\d+)\r?\n\s+name (\S+)"
    running_vlans = dict(re.findall(vlan_pattern, running_config))
    startup_vlans = dict(re.findall(vlan_pattern, startup_config))
    return any(
        vlan_id in running_vlans and startup_vlans.get(vlan_id) != vlan_name
        for vlan_id, vlan_name in TARGET_VLANS.items()
    )


def provision_device(device_info, username, password, dry_run=False):
    """Back up, plan, apply, verify and save one switch independently."""
    hostname = device_info.get("hostname", "Unknown")
    address = device_info["ip"]
    port = device_info.get("port", 22)
    logger.info("Connecting to %s (%s:%s)...", hostname, address, port)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # A distinct session log also prevents concurrent runs overwriting logs.
        with tempfile.NamedTemporaryFile(
            dir=LOG_DIR, prefix=f"{hostname}_", suffix="_session.log", delete=False,
        ) as session_file:
            session_log = session_file.name
        with ConnectHandler(
            device_type=device_info.get("device_type", "cisco_ios"),
            host=address, port=port, username=username, password=password,
            secret=os.environ.get("TVI_SECRET") or password,
            conn_timeout=12, auth_timeout=12, timeout=12,
            fast_cli=False, session_log=session_log,
        ) as net_connect:
            net_connect.enable()
            running_config = read_command(net_connect, "show running-config")
            backup_device(net_connect, hostname, "before", running_config)
            try:
                commands = get_missing_vlans(net_connect) + get_missing_baseline(running_config)
                if dry_run:
                    logger.info("[%s] DRY RUN planned commands: %s", hostname, commands)
                elif commands:
                    logger.info("[%s] Applying commands: %s", hostname, commands)
                    check_cli_response(net_connect.send_config_set(
                        commands, error_pattern=CLI_ERROR_PATTERN, read_timeout=60,
                    ))
                    verified_config = read_command(net_connect, "show running-config")
                    remaining = get_missing_vlans(net_connect) + get_missing_baseline(verified_config)
                    if remaining:
                        raise RuntimeError(
                            f"Configuration verification failed; remaining commands: {remaining}"
                        )
                    check_cli_response(net_connect.save_config())
                    logger.info("[%s] Verified and saved to NVRAM.", hostname)
                elif startup_needs_save(net_connect, running_config):
                    check_cli_response(net_connect.save_config())
                    logger.info("[%s] Saved pending desired configuration to NVRAM.", hostname)
                else:
                    logger.info("[%s] No changes needed (idempotent).", hostname)
            except Exception:
                # Commands can partially succeed. Preserve the observed state
                # for diagnosis and let the next run reconcile remaining work.
                try:
                    net_connect.exit_config_mode()
                    backup_device(net_connect, hostname, "failed")
                except Exception as backup_error:
                    logger.error("[%s] Failed-state backup unavailable: %s", hostname, backup_error)
                raise
            backup_device(net_connect, hostname, "after")
            return True
    except NetmikoTimeoutException:
        logger.error(
            "[%s] Connection TIMEOUT to %s:%s. Check EVE routing and node status.",
            hostname, address, port,
        )
    except NetmikoAuthenticationException:
        logger.error("[%s] Authentication FAILED. Check SSH and enable credentials.", hostname)
    except Exception as exc:
        logger.error("[%s] Operation FAILED (%s): %s", hostname, type(exc).__name__, exc)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_FILE)
    parser.add_argument("--device", action="append", help="Select a hostname; repeat to select several.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Read and back up devices, then log the plan without sending configuration.",
    )
    parser.add_argument(
        "--check-inventory", action="store_true", help="Validate inventory offline and exit."
    )
    args = parser.parse_args(argv)
    try:
        devices = load_inventory(args.inventory)
        if args.device:
            requested = set(args.device)
            unknown = requested - {device["hostname"] for device in devices}
            if unknown:
                raise ValueError(f"Unknown hostname(s): {', '.join(sorted(unknown))}")
            devices = [device for device in devices if device["hostname"] in requested]
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Inventory error: {exc}", file=sys.stderr)
        return 1
    if args.check_inventory:
        for device in devices:
            print(f"{device['hostname']} {device['ip']}:{device['port']} {device['device_type']}")
        print(f"Inventory valid: {len(devices)} device(s).")
        return 0

    setup_logging()
    try:
        username, password = get_credentials()
        success = 0
        for device in devices:
            if provision_device(device, username, password, dry_run=args.dry_run):
                success += 1
    except KeyboardInterrupt:
        logger.warning("Run interrupted by user.")
        return 130
    except (EOFError, ValueError) as exc:
        logger.error("Credentials unavailable: %s", exc)
        return 1
    failed = len(devices) - success
    logger.info(
        "Run summary: total=%s success=%s failed=%s dry_run=%s",
        len(devices), success, failed, args.dry_run,
    )
    if failed:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
