#!/usr/bin/python3
"""OpenFreezeCenter — MSI laptop fan control and monitoring for Bazzite Linux."""

import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ec_access import ECAccess, ECAccessError
from model_config import ModelConfig, ModelNotFoundError, load_user_config

from ui.theme import apply_theme, CPU_COLOR, make_label
from ui.dashboard import DashboardPage
from ui.fan_control import FanControlPage
from ui.battery import BatteryPage
from ui.settings import SettingsPage


def main():
    # --- Initialize backend ---
    try:
        model = ModelConfig()
    except ModelNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"Your board: {e.board_name}", file=sys.stderr)
        print(f"Known boards ({len(e.available_boards)}):", file=sys.stderr)
        for b in e.available_boards[:20]:
            board_info = e.database["boards"][b]
            print(f"  {b} - {board_info['name']}", file=sys.stderr)
        if len(e.available_boards) > 20:
            print(f"  ... and {len(e.available_boards) - 20} more", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR loading model config: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Detected: {model.model_name} ({model.board_name}, group {model.group})")

    try:
        ec = ECAccess()
    except ECAccessError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    user_cfg = load_user_config()

    # --- Build window ---
    window = Gtk.Window(title=f"OFC — {model.model_name}")
    window.set_default_size(900, 550)
    window.set_size_request(700, 450)
    window.connect("destroy", Gtk.main_quit)
    apply_theme(window)

    # Main horizontal layout: sidebar + content stack
    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    window.add(main_box)

    # --- Sidebar ---
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sidebar.get_style_context().add_class("sidebar")
    sidebar.set_size_request(160, -1)

    # Content stack
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_transition_duration(150)

    # Create pages
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

    settings_page = SettingsPage(model, ec)
    stack.add_named(settings_page, "settings")

    # Sidebar navigation buttons
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

    # Set Dashboard as active
    sidebar_buttons["dashboard"].get_style_context().add_class("active")

    # Spacer to push profile indicator to bottom
    sidebar.pack_start(Gtk.Box(), True, True, 0)

    # Profile indicator at bottom of sidebar
    profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    profile_box.set_margin_start(20)
    profile_box.set_margin_end(20)
    profile_box.set_margin_bottom(16)
    profile_box.pack_start(make_label("Profile", color="#444444", size=10), False, False, 0)
    profile_label = Gtk.Label()
    profile_label.get_style_context().add_class("profile-indicator")
    _update_profile_indicator(profile_label, user_cfg.get("profile", "auto"))
    profile_box.pack_start(profile_label, False, False, 0)
    sidebar.pack_start(profile_box, False, False, 0)

    main_box.pack_start(sidebar, False, False, 0)

    # Separator between sidebar and content
    sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    main_box.pack_start(sep, False, False, 0)

    main_box.pack_start(stack, True, True, 0)

    # --- Update timer ---
    def update_callback():
        dashboard_page.update(ec)
        fan_control_page.update(ec)
        return True  # keep running

    GLib.timeout_add(500, update_callback)

    # --- Show and run ---
    window.show_all()
    Gtk.main()

    # Cleanup
    ec.close()


def _on_sidebar_clicked(button, page_name, stack, buttons):
    """Handle sidebar navigation button click."""
    stack.set_visible_child_name(page_name)
    for name, btn in buttons.items():
        ctx = btn.get_style_context()
        if name == page_name:
            ctx.add_class("active")
        else:
            ctx.remove_class("active")


def _update_profile_indicator(label, profile_name):
    """Update the profile indicator label in the sidebar."""
    from ui.helpers import PROFILE_DISPLAY
    display = PROFILE_DISPLAY.get(profile_name, profile_name.title())
    label.set_markup(
        f'<span foreground="{CPU_COLOR}" font_desc="12">{display}</span>'
    )


if __name__ == "__main__":
    main()
