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
from ui.helpers import open_url_async, build_verified_device_url
from version import __version__


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


def _show_model_not_found_window(board_name, available_count):
    """Show an interactive, non-blocking window when a board is not in the database."""
    from ui.helpers import (
        read_dmi_value, run_read_only_diagnostic,
        build_model_missing_url, open_url_async, copy_to_clipboard,
    )
    from ui.theme import (
        apply_theme, make_card, make_label,
        WARNING_COLOR, SUCCESS_COLOR, TEXT_PRIMARY, TEXT_MUTED,
    )

    product_name = read_dmi_value("product_name")
    sys_vendor = read_dmi_value("sys_vendor")

    dialog = Gtk.Window(title="FrostCenter — Model Not Found")
    dialog.set_default_size(600, 480)
    dialog.set_position(Gtk.WindowPosition.CENTER)
    dialog.connect("destroy", Gtk.main_quit)
    apply_theme(dialog)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    main_box.set_margin_start(24)
    main_box.set_margin_end(24)
    main_box.set_margin_top(20)
    main_box.set_margin_bottom(20)
    dialog.add(main_box)

    # Header section
    hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    hdr_badge = Gtk.Label()
    hdr_badge.set_markup(f'<span foreground="{WARNING_COLOR}" font_desc="18" weight="bold">⚠</span>')
    hdr.pack_start(hdr_badge, False, False, 0)

    hdr_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    hdr_text.pack_start(make_label("Model Not in Database", color=WARNING_COLOR, size=14, bold=True), False, False, 0)
    hdr_text.pack_start(
        make_label(f"Board '{board_name}' was detected, but its EC profile is not yet mapped ({available_count} known boards in database).",
                   color=TEXT_MUTED, size=11),
        False, False, 0
    )
    hdr.pack_start(hdr_text, True, True, 0)
    main_box.pack_start(hdr, False, False, 0)

    # Hardware detection summary card
    info_card = make_card()
    info_card.pack_start(make_label("Detected Hardware", size=12, bold=True), False, False, 0)
    info_grid = Gtk.Grid()
    info_grid.set_column_spacing(16)
    info_grid.set_row_spacing(6)
    info_grid.set_margin_top(4)

    rows = [
        ("Board Name", board_name),
        ("Product Name", product_name),
        ("Manufacturer", sys_vendor),
    ]
    for idx, (lbl, val) in enumerate(rows):
        info_grid.attach(make_label(lbl, color=TEXT_MUTED, size=11), 0, idx, 1, 1)
        info_grid.attach(make_label(val, color=TEXT_PRIMARY, size=11), 1, idx, 1, 1)

    info_card.pack_start(info_grid, False, False, 0)
    main_box.pack_start(info_card, False, False, 0)

    # Diagnostic Output Section
    diag_card = make_card()
    diag_card.pack_start(make_label("EC Diagnostic Probe (Read-Only)", size=12, bold=True), False, False, 0)
    diag_card.pack_start(
        make_label("Safe, read-only ACPI registers used to map fan and temperature control.",
                   color=TEXT_MUTED, size=10),
        False, False, 0
    )

    diag_text = run_read_only_diagnostic()
    scroller = Gtk.ScrolledWindow()
    scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroller.set_min_content_height(110)

    text_view = Gtk.TextView()
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    text_view.set_monospace(True)
    text_view.get_style_context().add_class("mono-box")
    text_view.get_buffer().set_text(diag_text)
    scroller.add(text_view)
    diag_card.pack_start(scroller, True, True, 4)
    main_box.pack_start(diag_card, True, True, 0)

    # Action footer
    btn_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    submit_btn = Gtk.Button(label="Open Request on GitHub")
    submit_btn.get_style_context().add_class("accent-btn")

    copy_btn = Gtk.Button(label="Copy Diagnostic")
    copy_btn.get_style_context().add_class("secondary-btn")

    close_btn = Gtk.Button(label="Close")
    close_btn.get_style_context().add_class("secondary-btn")

    btn_bar.pack_start(submit_btn, False, False, 0)
    btn_bar.pack_start(copy_btn, False, False, 0)

    status_lbl = Gtk.Label()
    status_lbl.set_valign(Gtk.Align.CENTER)
    btn_bar.pack_start(status_lbl, False, False, 6)

    btn_bar.pack_end(close_btn, False, False, 0)
    main_box.pack_start(btn_bar, False, False, 0)

    def _on_submit(_):
        url = build_model_missing_url(board_name, product_name, diag_text)
        open_url_async(url)
        status_lbl.set_markup(f'<span foreground="{SUCCESS_COLOR}" font_desc="11">Opened browser!</span>')
        GLib.timeout_add_seconds(3, lambda: (status_lbl.set_text("") or False))

    def _on_copy(_):
        copy_to_clipboard(diag_text)
        copy_btn.set_label("Copied!")
        GLib.timeout_add_seconds(2, lambda: (copy_btn.set_label("Copy Diagnostic") or False))

    submit_btn.connect("clicked", _on_submit)
    copy_btn.connect("clicked", _on_copy)
    close_btn.connect("clicked", lambda _: dialog.destroy())

    dialog.show_all()
    Gtk.main()


def main():
    parser = argparse.ArgumentParser(description="FrostCenter — MSI laptop fan control")
    parser.add_argument('-v', '--version', action='version', version=f"FrostCenter {__version__}")
    parser.add_argument('--read-only', action='store_true',
                        help='Start in read-only mode (monitoring only, no EC writes)')
    args = parser.parse_args()

    # --- Initialize backend ---
    try:
        model = ModelConfig()
    except ModelNotFoundError as e:
        _show_model_not_found_window(e.board_name, len(e.available_boards))
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

    fan_control_page = FanControlPage(model, ec, user_cfg)
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

    # Spacer to push footer to bottom
    sidebar.pack_start(Gtk.Box(), True, True, 0)

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





if __name__ == "__main__":
    main()
