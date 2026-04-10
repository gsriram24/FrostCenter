#!/usr/bin/python3
"""FrostCenter — MSI laptop fan control and monitoring for Linux."""

import argparse
import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ec_access import ECAccess, ECAccessError, get_lockdown_status
from model_config import ModelConfig, ModelNotFoundError, load_user_config

from ui.theme import apply_theme, CPU_COLOR, WARNING_COLOR, make_label
from ui.dashboard import DashboardPage
from ui.fan_control import FanControlPage
from ui.battery import BatteryPage
from ui.settings import SettingsPage


def _show_error_dialog(title, message):
    """Show a GTK error dialog and return."""
    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def main():
    parser = argparse.ArgumentParser(description="FrostCenter — MSI laptop fan control")
    parser.add_argument('--read-only', action='store_true',
                        help='Start in read-only mode (monitoring only, no EC writes)')
    args = parser.parse_args()

    # --- Initialize backend ---
    try:
        model = ModelConfig()
    except ModelNotFoundError as e:
        _show_error_dialog(
            "Model Not Found",
            f"Board '{e.board_name}' is not in the database.\n\n"
            f"{len(e.available_boards)} known boards available.\n"
            "Run 'cat /sys/class/dmi/id/board_name' and open an issue on GitHub."
        )
        sys.exit(1)
    except Exception as e:
        _show_error_dialog("Configuration Error", str(e))
        sys.exit(1)

    print(f"Detected: {model.model_name} ({model.board_name}, group {model.group})")

    # Check lockdown status
    lockdown = get_lockdown_status()

    try:
        ec = ECAccess(read_only=args.read_only)
    except ECAccessError as e:
        if lockdown in ('integrity', 'confidentiality'):
            _show_error_dialog(
                "EC Access Blocked",
                f"Kernel lockdown is set to '{lockdown}' (Secure Boot).\n\n"
                "/dev/port is blocked — FrostCenter cannot read or write EC registers.\n\n"
                "To fix: disable Secure Boot in BIOS, or set lockdown to 'none'.\n"
                "Check: cat /sys/kernel/security/lockdown"
            )
        else:
            _show_error_dialog("EC Access Error", str(e))
        sys.exit(1)

    user_cfg = load_user_config()

    # --- Build window ---
    read_only = ec.is_read_only
    title = f"FrostCenter — {model.model_name}"
    if read_only:
        title += " [READ-ONLY]"
    window = Gtk.Window(title=title)
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

    def _on_read_only_changed(state):
        """Called when read-only toggle is flipped in Settings."""
        fan_control_page.set_read_only(state)
        if battery_page:
            battery_page.set_read_only(state)

    settings_page = SettingsPage(model, ec, window=window,
                                  on_read_only_changed=_on_read_only_changed)
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
