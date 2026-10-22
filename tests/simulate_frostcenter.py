#!/usr/bin/env python3
"""Hardware & Environment Simulator for FrostCenter.

Simulates the Linux hardware environment (DMI sysfs and ACPI EC registers)
so that the real OFC.py application runs directly on Windows/WSL or any non-MSI PC.

Zero UI code is defined in this file. 100% of the UI is executed by OFC.py.

Usage:
    python3 tests/simulate_frostcenter.py                  # Raider GE75 (MS-17E9)
    python3 tests/simulate_frostcenter.py --board MS-16R4  # GF63 Thin (unverified)
    python3 tests/simulate_frostcenter.py --board MS-16W2  # GF65 Thin (verified)
    python3 tests/simulate_frostcenter.py --unmapped        # Model not in database
    python3 tests/simulate_frostcenter.py --read-only       # Read-only mode
"""

import argparse
import os
import random
import sys

# Ensure repo root is on sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import ec_access
import model_config
import ui.helpers
import OFC

_CURRENT_BOARD = "MS-17E9"


class MockECAccess:
    """In-memory simulation of the MSI Embedded Controller (EC) memory space (0x00-0xFF)."""

    def __init__(self, read_only=False):
        self._read_only = read_only
        self.reg = bytearray(256)

        try:
            self.model = model_config.ModelConfig(board_override=_CURRENT_BOARD)
        except Exception:
            self.model = None

        if self.model:
            self.reg[self.model.cpu_temp_addr] = 46
            self.reg[self.model.cpu_fan_speed_pct_addr] = 38
            raw_cpu = self.model.rpm_divisor // 2450
            self.reg[self.model.cpu_fan_rpm_addr] = (raw_cpu >> 8) & 0xFF
            self.reg[self.model.cpu_fan_rpm_addr + 1] = raw_cpu & 0xFF

            if self.model.has_gpu and self.model.gpu_temp_addr is not None:
                self.reg[self.model.gpu_temp_addr] = 41
                self.reg[self.model.gpu_fan_speed_pct_addr] = 32
                raw_gpu = self.model.rpm_divisor // 2100
                self.reg[self.model.gpu_fan_rpm_addr] = (raw_gpu >> 8) & 0xFF
                self.reg[self.model.gpu_fan_rpm_addr + 1] = raw_gpu & 0xFF

            if self.model.cooler_boost_addr is not None:
                self.reg[self.model.cooler_boost_addr] = 0x00
            if self.model.fan_mode_addr is not None:
                self.reg[self.model.fan_mode_addr] = self.model.fan_modes.get("auto", 0x0d)
            if self.model.battery_threshold_addr is not None:
                self.reg[self.model.battery_threshold_addr] = 80

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    @property
    def is_read_only(self):
        return self._read_only

    @is_read_only.setter
    def is_read_only(self, value):
        self._read_only = bool(value)

    def read_byte(self, register):
        if self.model:
            if register == self.model.cpu_temp_addr:
                val = self.reg[register] + random.randint(-1, 1)
                return max(35, min(95, val))
            if self.model.has_gpu and register == self.model.gpu_temp_addr:
                val = self.reg[register] + random.randint(-1, 1)
                return max(30, min(90, val))
        return self.reg[register]

    def read_word(self, register):
        if self.model:
            if register == self.model.cpu_fan_rpm_addr:
                rpm = max(800, 2450 + random.randint(-40, 40))
                return self.model.rpm_divisor // rpm
            if self.model.has_gpu and register == self.model.gpu_fan_rpm_addr:
                rpm = max(800, 2100 + random.randint(-40, 40))
                return self.model.rpm_divisor // rpm
        high = self.read_byte(register)
        low = self.read_byte((register + 1) % 256)
        return (high << 8) | low

    def write_byte(self, register, value):
        if self._read_only:
            raise RuntimeError("Write operations disabled in read-only mode.")
        self.reg[register] = value & 0xFF


def main():
    global _CURRENT_BOARD
    parser = argparse.ArgumentParser(description="FrostCenter Hardware Simulator — runs real OFC.py")
    parser.add_argument('--board', default='MS-17E9',
                        help='Simulate a specific MSI motherboard ID (e.g., MS-16R4, MS-16W2)')
    parser.add_argument('--unmapped', action='store_true',
                        help='Simulate an unmapped/unsupported laptop to test the Diagnostic Reporter')
    parser.add_argument('--read-only', action='store_true',
                        help='Run FrostCenter in read-only monitoring mode')
    args = parser.parse_args()

    if args.unmapped:
        _CURRENT_BOARD = "MS-UNKNOWN-999"
        mock_product = "Prestige 16 AI Studio B1VFG"
    else:
        _CURRENT_BOARD = args.board
        mock_product = f"MSI Laptop ({args.board})"

    # --- Hardware & Environment Mocks ---
    # 1. Mock DMI sysfs queries
    model_config._read_dmi = lambda path: _CURRENT_BOARD

    def _mock_read_dmi_value(name):
        if name == "board_name":
            return _CURRENT_BOARD
        elif name == "product_name":
            return mock_product
        elif name == "sys_vendor":
            return "Micro-Star International Co., Ltd."
        return "Unknown"

    ui.helpers.read_dmi_value = _mock_read_dmi_value

    # 2. Mock kernel lockdown status
    ec_access.get_lockdown_status = lambda: 'none'
    OFC.get_lockdown_status = lambda: 'none'

    # 3. Mock ACPI EC access (/dev/port)
    ec_access.ECAccess = MockECAccess
    OFC.ECAccess = MockECAccess

    # 4. Mock diagnostic probe if unmapped
    if args.unmapped:
        ui.helpers.run_read_only_diagnostic = lambda: (
            "CPU temp (0x68):             48 C\n"
            "CPU fan % (0x71):            35 %\n"
            "CPU fan RPM raw (0xcc/0xcd): 195\n"
            "GPU temp (0x80):             42 C\n"
            "GPU fan % (0x73):            30 %\n"
            "GPU fan RPM raw (0xc8/0xc9): 227\n"
            "Fan mode (0xd2):             0x0d\n"
            "Fan mode (0xf4):             0x0d\n"
            "Cooler boost (0x98):         0x00"
        )

    print(f"[Simulator] Environment injected for board '{_CURRENT_BOARD}'. Handing over to OFC.py...")

    # Pass through arguments to OFC.py
    ofc_argv = [sys.argv[0]]
    if args.read_only:
        ofc_argv.append('--read-only')
    sys.argv = ofc_argv

    # Execute the true, unmodified OFC.py
    OFC.main()


if __name__ == "__main__":
    main()
