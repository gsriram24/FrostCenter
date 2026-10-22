#!/usr/bin/env python3
"""Standalone MSI Hardware & EC Simulator for FrostCenter.

Allows running and testing the full FrostCenter GTK3 user interface on any PC,
virtual machine, or WSL environment without needing an MSI laptop or /dev/port.

Usage:
    python3 tests/simulate_frostcenter.py               # Runs full UI with simulated Raider GE75 (MS-17E9)
    python3 tests/simulate_frostcenter.py --board MS-16R4  # Runs with simulated GF63 Thin
    python3 tests/simulate_frostcenter.py --unmapped     # Tests the "Model Not Found" diagnostic window
    python3 tests/simulate_frostcenter.py --read-only    # Runs in read-only monitoring mode
"""

import argparse
import random
import sys
import os

# Ensure repo root is on sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from model_config import ModelConfig, load_user_config
from ui.theme import apply_theme, CPU_COLOR, make_label
from ui.dashboard import DashboardPage
from ui.fan_control import FanControlPage
from ui.battery import BatteryPage
from ui.settings import SettingsPage
from ui.helpers import open_url_async, build_verified_device_url
from OFC import _show_model_not_found_window, _update_profile_indicator, _on_sidebar_clicked


class MockECAccess:
    """In-memory simulation of the MSI Embedded Controller (EC) memory space (0x00-0xFF)."""

    def __init__(self, model, read_only=False):
        self.is_read_only = read_only
        self.model = model
        self.reg = bytearray(256)

        # Realistic initial sensor readings
        self.reg[model.cpu_temp_addr] = 46                     # 46 °C
        self.reg[model.cpu_fan_speed_pct_addr] = 38            # 38 %
        
        # Raw RPM word: RPM = divisor // raw -> raw = divisor // RPM
        raw_cpu = model.rpm_divisor // 2450
        self.reg[model.cpu_fan_rpm_addr] = (raw_cpu >> 8) & 0xFF
        self.reg[model.cpu_fan_rpm_addr + 1] = raw_cpu & 0xFF

        if model.has_gpu and model.gpu_temp_addr is not None:
            self.reg[model.gpu_temp_addr] = 41                 # 41 °C
            self.reg[model.gpu_fan_speed_pct_addr] = 32        # 32 %
            raw_gpu = model.rpm_divisor // 2100
            self.reg[model.gpu_fan_rpm_addr] = (raw_gpu >> 8) & 0xFF
            self.reg[model.gpu_fan_rpm_addr + 1] = raw_gpu & 0xFF

        # Initial fan curves (default speeds)
        for i, addr in enumerate(model.cpu_fan_curve_speed_addrs):
            self.reg[addr] = [0, 25, 40, 55, 70, 85, 100][i]
        if model.has_gpu and model.gpu_fan_curve_speed_addrs:
            for i, addr in enumerate(model.gpu_fan_curve_speed_addrs):
                self.reg[addr] = [0, 25, 40, 55, 70, 85, 100][i]

        # Cooler boost bit off initially
        self.reg[model.cooler_boost_addr] = 0

        # Battery threshold (default 80%)
        if model.battery_threshold_addr is not None:
            self.reg[model.battery_threshold_addr] = 80

    def read_byte(self, addr):
        return self.reg[addr]

    def write_byte(self, addr, value):
        if self.is_read_only:
            return
        self.reg[addr] = value & 0xFF
        # If cooler boost toggled on, jump fan speeds
        cb_on = bool(self.reg[self.model.cooler_boost_addr] & (1 << self.model.cooler_boost_bit))
        if cb_on:
            self.reg[self.model.cpu_fan_speed_pct_addr] = 150
            raw_cb = self.model.rpm_divisor // 5600
            self.reg[self.model.cpu_fan_rpm_addr] = (raw_cb >> 8) & 0xFF
            self.reg[self.model.cpu_fan_rpm_addr + 1] = raw_cb & 0xFF

    def read_word(self, addr):
        return (self.read_byte(addr) << 8) | self.read_byte(addr + 1)

    def tick(self):
        """Called periodically to simulate small sensor fluctuations in hardware."""
        # Slight jitter in CPU/GPU temp (+/- 1 degree)
        cur_cpu = self.reg[self.model.cpu_temp_addr]
        self.reg[self.model.cpu_temp_addr] = max(38, min(85, cur_cpu + random.choice([-1, 0, 1])))
        
        # RPM minor fluctuation
        cb_on = bool(self.reg[self.model.cooler_boost_addr] & (1 << self.model.cooler_boost_bit))
        target_rpm = 5600 if cb_on else 2400
        cur_rpm = target_rpm + random.randint(-40, 40)
        raw = self.model.rpm_divisor // max(100, cur_rpm)
        self.reg[self.model.cpu_fan_rpm_addr] = (raw >> 8) & 0xFF
        self.reg[self.model.cpu_fan_rpm_addr + 1] = raw & 0xFF

    def close(self):
        pass


def main():
    parser = argparse.ArgumentParser(description="FrostCenter UI Simulator")
    parser.add_argument('--board', default='MS-16R4',
                        help='Board name to simulate from database.json (default: MS-16R4)')
    parser.add_argument('--unmapped', action='store_true',
                        help='Simulate an unmapped board to test the Model Not Found dialog')
    parser.add_argument('--read-only', action='store_true',
                        help='Simulate running in read-only mode')
    args = parser.parse_args()

    if args.unmapped:
        print("[Simulator] Simulating unmapped board with live EC probe: MS-9999...")
        import ui.helpers
        ui.helpers.read_dmi_value = lambda name: {
            "board_name": "MS-9999",
            "product_name": "Titan GT77 HX 13VI (Simulated)",
            "sys_vendor": "Micro-Star International Co., Ltd.",
        }.get(name, "Unknown")

        ui.helpers.run_read_only_diagnostic = lambda: (
            "CPU temp (0x68):             48 C\n"
            "CPU fan % (0x71):            35 %\n"
            "CPU fan RPM raw (0xcc/0xcd): 2450 (approx 2450 RPM)\n"
            "GPU temp (0x80):             41 C\n"
            "GPU fan % (0x73):            30 %\n"
            "GPU fan RPM raw (0xc8/0xc9): 2100 (approx 2100 RPM)\n"
            "Fan mode (0xd2):             0x0d\n"
            "Fan mode (0xf4):             0x0d\n"
            "Cooler boost (0x98):         0x00\n"
            "Battery threshold (0xef):    0x50 (80%)"
        )
        _show_model_not_found_window("MS-9999", 130)
        return

    print(f"[Simulator] Loading simulated MSI hardware for board: {args.board}")
    model = ModelConfig(board_override=args.board)
    ec = MockECAccess(model, read_only=args.read_only)
    user_cfg = load_user_config()

    title = f"FrostCenter [SIMULATOR] — {model.model_name} ({model.board_name})"
    if ec.is_read_only:
        title += " [READ-ONLY]"

    window = Gtk.Window(title=title)
    window.set_default_size(950, 580)
    window.set_size_request(720, 480)
    window.connect("destroy", Gtk.main_quit)
    apply_theme(window)

    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    window.add(main_box)

    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sidebar.get_style_context().add_class("sidebar")
    sidebar.set_size_request(160, -1)

    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_transition_duration(150)

    # Instantiate UI pages
    dashboard_page = DashboardPage(model)
    stack.add_named(dashboard_page, "dashboard")

    fan_control_page = FanControlPage(
        model, ec, user_cfg,
        on_profile_changed=lambda name: _update_profile_indicator(profile_label, name),
    )
    stack.add_named(fan_control_page, "fan_control")

    battery_page = None
    if model.battery_threshold_addr is not None:
        battery_page = BatteryPage(model, ec, user_cfg)
        stack.add_named(battery_page, "battery")

    def _on_read_only_changed(state):
        fan_control_page.set_read_only(state)
        if battery_page:
            battery_page.set_read_only(state)

    settings_page = SettingsPage(model, ec, window=window,
                                 on_read_only_changed=_on_read_only_changed)
    stack.add_named(settings_page, "settings")

    # Navigation buttons
    sidebar_buttons = {}
    pages = [("Dashboard", "dashboard"), ("Fan Control", "fan_control")]
    if model.battery_threshold_addr is not None:
        pages.append(("Battery", "battery"))
    pages.append(("Settings", "settings"))

    for display_name, page_name in pages:
        btn = Gtk.Button(label=display_name)
        btn.get_style_context().add_class("sidebar-btn")
        btn.connect("clicked", _on_sidebar_clicked, page_name, stack, sidebar_buttons)
        sidebar.pack_start(btn, False, False, 0)
        sidebar_buttons[page_name] = btn

    sidebar_buttons["dashboard"].get_style_context().add_class("active")
    sidebar.pack_start(Gtk.Box(), True, True, 0)

    profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    profile_box.set_margin_start(20)
    profile_box.set_margin_end(20)
    profile_box.set_margin_bottom(10)
    profile_box.pack_start(make_label("Profile", color="#444444", size=10), False, False, 0)
    profile_label = Gtk.Label()
    profile_label.get_style_context().add_class("profile-indicator")
    _update_profile_indicator(profile_label, user_cfg.get("profile", "auto"))
    profile_box.pack_start(profile_label, False, False, 0)
    sidebar.pack_start(profile_box, False, False, 0)

    # Sidebar footer: verification (if unverified) & GitHub star
    footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    footer_box.set_margin_start(14)
    footer_box.set_margin_end(14)
    footer_box.set_margin_bottom(14)

    if not getattr(model, 'is_verified', False):
        verify_btn = Gtk.Button(label="⚡ Verify Device")
        verify_btn.get_style_context().add_class("sidebar-verify-btn")
        verify_btn.set_tooltip_text("Help verify this laptop model on GitHub")
        verify_btn.connect("clicked", lambda _: open_url_async(build_verified_device_url(model)))
        footer_box.pack_start(verify_btn, False, False, 0)

    star_btn = Gtk.Button(label="★ Star on GitHub")
    star_btn.get_style_context().add_class("sidebar-star-btn")
    star_btn.set_tooltip_text("Support FrostCenter on GitHub")
    star_btn.connect("clicked", lambda _: open_url_async("https://github.com/gsriram24/FrostCenter"))
    footer_box.pack_start(star_btn, False, False, 0)

    sidebar.pack_start(footer_box, False, False, 0)

    main_box.pack_start(sidebar, False, False, 0)
    sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    main_box.pack_start(sep, False, False, 0)
    main_box.pack_start(stack, True, True, 0)

    # 500ms update loop to refresh gauges and animate dials
    def update_callback():
        ec.tick()
        dashboard_page.update(ec)
        fan_control_page.update(ec)
        return True

    GLib.timeout_add(500, update_callback)

    window.show_all()
    print("[Simulator] GTK window running. Enjoy testing!")
    Gtk.main()


if __name__ == "__main__":
    main()
