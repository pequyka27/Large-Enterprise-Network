"""Offline regression tests for P4 automation and security configuration."""

import contextlib
import io
import ipaddress
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from Automation import auto_provision as automation


class FakeSwitch:
    """Model only the IOS commands used by the provisioning workflow."""

    def __init__(self):
        self.vlans = {}
        self.baseline = []
        self.startup = ""
        self.config_batches = []
        self.save_count = 0
        self.reject_config = False
        self.ignore_config = False
        self.save_response = "[OK]"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def enable(self):
        pass

    def exit_config_mode(self):
        pass

    def send_command(self, command, **kwargs):
        if command == "show running-config":
            return "hostname TEST-SW\n" + "\n".join(self.baseline)
        if command == "show startup-config":
            return self.startup
        if command == "show ip interface brief":
            return "Vlan99 192.168.1.10 YES manual up up"
        if command == "show vlan brief":
            return "\n".join(
                f"{vlan_id:>4} {name:<32} active"
                for vlan_id, name in self.vlans.items()
            )
        raise AssertionError(f"Unexpected command: {command}")

    def send_config_set(self, commands, **kwargs):
        self.config_batches.append(commands)
        if self.reject_config:
            # A previous command may have succeeded before IOS rejects one.
            self.vlans["10"] = "PARTIAL"
            return "% Invalid input detected at '^' marker."
        if self.ignore_config:
            return ""
        current_vlan = None
        for command in commands:
            if command.startswith("vlan "):
                current_vlan = command.split()[1]
            elif command.startswith("name "):
                self.vlans[current_vlan] = command.split()[1]
            elif command == "exit":
                current_vlan = None
            else:
                if current_vlan is not None:
                    raise AssertionError("Global command sent in VLAN configuration mode")
                self.baseline.append(command)
        return ""

    def save_config(self):
        self.save_count += 1
        if self.save_response == "[OK]":
            self.startup = self.send_command("show running-config")
        return self.save_response


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.backups = root / "backups"
        self.logs = root / "logs"
        for name, value in (("BACKUP_DIR", self.backups), ("LOG_DIR", self.logs)):
            patcher = patch.object(automation, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.device = {"hostname": "TEST-SW", "ip": "192.168.1.10", "port": 22}
        self.switch = FakeSwitch()
        self.connection = patch.object(automation, "ConnectHandler", return_value=self.switch)
        self.connect = self.connection.start()
        self.addCleanup(self.connection.stop)

    def provision(self, **kwargs):
        return automation.provision_device(
            self.device, "test-user", "unused-in-mocked-connection", **kwargs
        )

    def test_second_run_sends_no_configuration_and_keeps_distinct_backups(self):
        self.assertTrue(self.provision())
        self.assertTrue(self.provision())
        self.assertEqual(self.switch.vlans, automation.TARGET_VLANS)
        self.assertEqual(len(self.switch.config_batches), 1)
        self.assertEqual(self.switch.save_count, 1)
        files = list(self.backups.glob("*.cfg"))
        self.assertEqual(len(files), 4)
        self.assertEqual(len(list(self.backups.glob("*_before_*.cfg"))), 2)
        self.assertEqual(len(list(self.backups.glob("*_after_*.cfg"))), 2)
        self.assertTrue(all("IP INTERFACE BRIEF" in file.read_text() for file in files))

    def test_vlan_id_and_name_are_matched_exactly(self):
        self.switch.vlans = dict(automation.TARGET_VLANS)
        del self.switch.vlans["10"]
        del self.switch.vlans["99"]
        self.switch.vlans["20"] = "RND_ENGINEERING_OLD"
        commands = automation.get_missing_vlans(self.switch)
        self.assertEqual(commands, [
            "vlan 10", "name EXEC_FINANCE", "exit",
            "vlan 20", "name RND_ENGINEERING", "exit",
            "vlan 99", "name MANAGEMENT", "exit",
        ])

    def test_banner_renderings_and_numeric_logging_level_are_idempotent(self):
        for delimiter in ("#", "^C", "\x03"):
            with self.subTest(delimiter=repr(delimiter)):
                config = (
                    "ntp server 10.10.254.1 prefer\n"
                    f"banner motd {delimiter}\n {automation.BANNER_TEXT} \n{delimiter}\n"
                    "logging buffered 64000 6\n"
                )
                self.assertEqual(automation.get_missing_baseline(config), [])
        self.assertEqual(automation.get_missing_baseline(""), automation.BASELINE_CONFIGS)

    def test_dry_run_only_reads_and_creates_backups(self):
        self.assertTrue(self.provision(dry_run=True))
        self.assertEqual(self.switch.config_batches, [])
        self.assertEqual(self.switch.save_count, 0)
        self.assertEqual(self.switch.vlans, {})
        self.assertEqual(len(list(self.backups.glob("*.cfg"))), 2)

    def test_cli_failure_is_not_saved_and_partial_state_is_backed_up(self):
        self.switch.reject_config = True
        with self.assertLogs(automation.logger, level="ERROR"):
            self.assertFalse(self.provision())
        self.assertEqual(self.switch.save_count, 0)
        self.assertEqual(len(list(self.backups.glob("*_before_*.cfg"))), 1)
        self.assertEqual(len(list(self.backups.glob("*_failed_*.cfg"))), 1)
        self.switch.reject_config = False
        self.assertTrue(self.provision())
        self.assertEqual(self.switch.vlans, automation.TARGET_VLANS)
        self.assertEqual(self.switch.save_count, 1)

    def test_verification_failure_is_not_saved(self):
        self.switch.ignore_config = True
        with self.assertLogs(automation.logger, level="ERROR"):
            self.assertFalse(self.provision())
        self.assertEqual(self.switch.save_count, 0)

    def test_save_failure_returns_failure(self):
        self.switch.save_response = "%Error writing nvram:startup-config"
        with self.assertLogs(automation.logger, level="ERROR"):
            self.assertFalse(self.provision())
        self.assertEqual(len(list(self.backups.glob("*_failed_*.cfg"))), 1)

    def test_retry_recovers_failed_save_without_reapplying_configuration(self):
        self.switch.save_response = "%Error writing nvram:startup-config"
        with self.assertLogs(automation.logger, level="ERROR"):
            self.assertFalse(self.provision())
        self.switch.save_response = "[OK]"
        self.assertTrue(self.provision())
        self.assertTrue(self.provision())
        self.assertEqual(len(self.switch.config_batches), 1)
        self.assertEqual(self.switch.save_count, 2)

    def test_missing_startup_and_unsaved_vlan_names_require_save(self):
        self.switch.startup = "%Error opening nvram:startup-config (No such file or directory)"
        self.assertTrue(automation.startup_needs_save(self.switch, ""))
        self.switch.startup = "\n".join(automation.BASELINE_CONFIGS)
        running = self.switch.startup + "\nvlan 10\n name EXEC_FINANCE\n"
        self.assertTrue(automation.startup_needs_save(self.switch, running))

    def test_show_command_error_is_not_treated_as_an_empty_vlan_database(self):
        with patch.object(self.switch, "send_command", return_value="\n% Invalid input detected"):
            with self.assertRaisesRegex(RuntimeError, "Invalid input"):
                automation.get_missing_vlans(self.switch)

    def test_atomic_backup_failure_leaves_no_partial_file(self):
        with patch.object(automation.os, "replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                automation.backup_device(self.switch, "TEST-SW")
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_backups_with_the_same_timestamp_do_not_overwrite_each_other(self):
        with patch.object(automation, "datetime") as clock:
            clock.now.return_value.strftime.return_value = "SAME_TIMESTAMP"
            first = automation.backup_device(self.switch, "TEST-SW")
            second = automation.backup_device(self.switch, "TEST-SW")
        self.assertNotEqual(first, second)
        self.assertTrue(Path(first).exists())
        self.assertTrue(Path(second).exists())

    def test_device_filter_selects_only_requested_switch(self):
        with (
            patch.object(automation, "setup_logging"),
            patch.object(automation, "get_credentials", return_value=("test-user", "unused")),
            patch.object(automation, "provision_device", return_value=True) as provision,
        ):
            self.assertEqual(automation.main(["--device", "HCMC-CORE-SW01", "--dry-run"]), 0)
        self.assertEqual(provision.call_count, 1)
        self.assertEqual(provision.call_args.args[0]["hostname"], "HCMC-CORE-SW01")
        self.assertTrue(provision.call_args.kwargs["dry_run"])

    def test_connection_and_authentication_failures_are_reported(self):
        for error in (automation.NetmikoTimeoutException, automation.NetmikoAuthenticationException):
            with self.subTest(error=error.__name__):
                self.connect.side_effect = error("mock failure")
                with self.assertLogs(automation.logger, level="ERROR"):
                    self.assertFalse(self.provision())

    def test_main_continues_after_failed_device(self):
        devices = [self.device, dict(self.device, hostname="SECOND", ip="192.168.1.11")]
        with (
            patch.object(automation, "load_inventory", return_value=devices),
            patch.object(automation, "setup_logging"),
            patch.object(automation, "get_credentials", return_value=("test-user", "unused")),
            patch.object(automation, "provision_device", side_effect=[False, True]) as provision,
        ):
            self.assertEqual(automation.main([]), 2)
            self.assertEqual(provision.call_count, 2)

    def test_offline_check_does_not_connect_or_request_credentials(self):
        with (
            patch.object(automation, "get_credentials") as credentials,
            patch.object(automation, "setup_logging") as logging_setup,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(automation.main(["--check-inventory"]), 0)
        self.connect.assert_not_called()
        credentials.assert_not_called()
        logging_setup.assert_not_called()

    def test_device_filter_is_checked_before_connecting(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(automation.main(["--device", "UNKNOWN"]), 1)
        self.connect.assert_not_called()


class InventoryTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.yaml"
            path.write_text(yaml.safe_dump(data), encoding="utf-8")
            return automation.load_inventory(path)

    def test_existing_inventory_and_remote_port_mapping(self):
        self.assertEqual(len(automation.load_inventory()), 6)
        data = {"devices": [
            {"hostname": "ONE", "ip": "100.64.12.126", "port": "2222"},
            {"hostname": "TWO", "ip": "100.64.12.126", "port": 2223},
        ]}
        self.assertEqual(self.load(data)[0]["port"], 2222)

    def test_dns_and_ipv6_endpoints_are_supported(self):
        data = {"devices": [
            {"hostname": "ONE", "ip": "Leader.Example.ts.net"},
            {"hostname": "TWO", "ip": "2001:db8::10"},
        ]}
        self.assertEqual(self.load(data)[0]["ip"], "leader.example.ts.net")
        self.assertEqual(self.load(data)[1]["ip"], "2001:db8::10")

    def test_invalid_inventory_is_rejected(self):
        device = {"hostname": "ONE", "ip": "192.168.1.10"}
        invalid = [
            None, [], {}, {"devices": []}, {"devices": [None]},
            {"devices": [device, device]},
            {"devices": [device, dict(device, hostname="TWO")]},
        ]
        for field, values in {
            "hostname": ("../outside", "", None),
            "ip": ("invalid address", "192.168.1.999", "", 123, None),
            "port": (0, 65536, True, 22.5, "22.0", None),
            "device_type": ("cisco_ios_telnet", None),
        }.items():
            invalid.extend({"devices": [dict(device, **{field: value})]} for value in values)
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)


class SecurityConfigTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1] / "Configurations"

    def config(self, filename):
        matches = list(self.ROOT.rglob(filename))
        self.assertEqual(len(matches), 1)
        return matches[0].read_text(encoding="utf-8").split("! [P4]", 1)[1]

    def test_nat_exempts_internal_destinations_and_permits_local_internet(self):
        for hostname, site in (("HCMC-EDGE", "10.10"), ("HANOI-RND", "10.20"), ("DANANG-LOG", "10.30")):
            with self.subTest(hostname=hostname):
                config = self.config(f"{hostname}-RTR01.cfg")
                acl = config.split("ip access-list extended NAT_INSIDE\n", 1)[1].split("!", 1)[0]
                rules = [line.split() for line in acl.splitlines() if line.strip()]

                def permits(source, destination):
                    for action, protocol, source_net, source_wildcard, *target in rules:
                        source_network = ipaddress.IPv4Network(f"{source_net}/{source_wildcard}")
                        destination_network = ipaddress.IPv4Network("0.0.0.0/0")
                        if target != ["any"]:
                            destination_network = ipaddress.IPv4Network(f"{target[0]}/{target[1]}")
                        if (
                            ipaddress.IPv4Address(source) in source_network
                            and ipaddress.IPv4Address(destination) in destination_network
                        ):
                            return action == "permit"
                    return False

                self.assertTrue(permits(f"{site}.4.10", "8.8.8.8"))
                self.assertFalse(permits(f"{site}.4.10", "10.20.0.10"))
                self.assertFalse(permits(f"{site}.4.10", "192.168.2.10"))
                self.assertFalse(permits("192.168.1.10", "8.8.8.8"))
                self.assertNotIn("ip access-list standard NAT_INSIDE", config)

    def test_guest_policies_are_attached_to_all_guest_gateways(self):
        for filename, interface in (
            ("HCMC-DIST-SW01.cfg", "Vlan40"),
            ("HCMC-DIST-SW02.cfg", "Vlan40"),
            ("HANOI-RND-RTR01.cfg", "GigabitEthernet0/1.40"),
            ("DANANG-LOG-RTR01.cfg", "GigabitEthernet0/1.40"),
        ):
            with self.subTest(filename=filename):
                config = self.config(filename)
                acl = config.split("ip access-list extended GUEST_IN\n", 1)[1].split("!", 1)[0]
                self.assertIn("permit udp any eq bootpc any eq bootps", acl)
                for protocol in ("udp", "tcp"):
                    dns = f"permit {protocol} any host 10.10.254.1 eq domain"
                    self.assertLess(acl.index(dns), acl.index("deny ip any 10.0.0.0"))
                self.assertLess(acl.index("deny ip any 192.168.0.0"), acl.index("permit ip any any"))
                self.assertIn(f"interface {interface}\n ip access-group GUEST_IN in\n ipv6 traffic-filter GUEST_V6_IN in", config)
                self.assertIn("deny ipv6 any 2001:db8:7a1::/48", config)
                self.assertIn("permit icmp any any nd-ns", config)

    def test_branch_access_security_trusts_only_uplinks(self):
        for filename, uplink in (
            ("HANOI-RND-SW02.cfg", "Port-channel1"),
            ("DANANG-LOG-SW01.cfg", "GigabitEthernet0/0"),
        ):
            with self.subTest(filename=filename):
                config = self.config(filename)
                self.assertIn("ip dhcp snooping vlan 10,20,30,40", config)
                self.assertIn("no ip dhcp snooping information option", config)
                self.assertIn("ip arp inspection vlan 10,20,30,40", config)
                self.assertIn(f"interface {uplink}\n ip dhcp snooping trust\n ip arp inspection trust", config)
                for port in ("GigabitEthernet1/0", "GigabitEthernet1/1"):
                    block = re.search(rf"interface {port}\n(.*?)(?=\n!)", config, re.S).group(1)
                    self.assertIn("switchport port-security maximum 2", block)
                    self.assertIn("switchport port-security violation restrict", block)
                    self.assertIn("switchport port-security mac-address sticky", block)
                    self.assertNotIn("snooping trust", block)
                    self.assertNotIn("inspection trust", block)


if __name__ == "__main__":
    unittest.main()
