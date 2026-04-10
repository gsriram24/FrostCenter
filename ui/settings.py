# ui/settings.py
"""Settings page — system info, options, and about."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, SUCCESS_COLOR,
    make_label, make_card,
)


class SettingsPage(Gtk.Box):
    """Settings page with system info and options.

    Args:
        model: ModelConfig instance
        ec: ECAccess instance
    """

    def __init__(self, model, ec):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)

        # --- System information card ---
        info_card = make_card()
        info_card.pack_start(make_label("System Information", size=13, bold=True), False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(8)
        grid.set_margin_top(8)

        info_rows = [
            ("Model", model.model_name),
            ("Board", model.board_name),
            ("Config Group", model.group),
            ("EC Access", f"/dev/port ({'read-only' if ec.is_read_only else 'active'})"),
            ("Fan Modes", ", ".join(model.fan_modes.keys())),
            ("GPU", "Detected" if model.has_gpu else "Not detected"),
            ("Battery Ctrl",
             f"Supported (0x{model.battery_threshold_addr:02X})"
             if model.battery_threshold_addr is not None
             else "Not supported"),
        ]

        for row_idx, (label, value) in enumerate(info_rows):
            lbl = make_label(label, color=TEXT_MUTED, size=12)
            grid.attach(lbl, 0, row_idx, 1, 1)

            # Color active/detected values green
            val_color = TEXT_PRIMARY
            if value in ("Detected", "active") or "Supported" in str(value):
                val_color = SUCCESS_COLOR
            elif "read-only" in str(value):
                val_color = TEXT_SECONDARY

            val_label = make_label(str(value), color=val_color, size=12)
            grid.attach(val_label, 1, row_idx, 1, 1)

        info_card.pack_start(grid, False, False, 0)
        self.pack_start(info_card, False, False, 0)

        # --- Options card ---
        opts_card = make_card()
        opts_card.pack_start(make_label("Options", size=13, bold=True), False, False, 0)

        # Read-only mode display
        ro_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ro_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ro_left.pack_start(make_label("Read-only mode", size=12), False, False, 0)
        ro_left.pack_start(
            make_label("Disable all EC writes (monitoring only)", color=TEXT_MUTED, size=10),
            False, False, 0,
        )
        ro_row.pack_start(ro_left, True, True, 0)

        ro_switch = Gtk.Switch()
        ro_switch.set_active(ec.is_read_only)
        ro_switch.set_sensitive(False)  # Display only — requires restart
        ro_switch.set_valign(Gtk.Align.CENTER)
        ro_row.pack_end(ro_switch, False, False, 0)
        opts_card.pack_start(ro_row, False, False, 8)

        # Update interval display
        interval_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        iv_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        iv_left.pack_start(make_label("Update interval", size=12), False, False, 0)
        iv_left.pack_start(
            make_label("How often to poll EC registers", color=TEXT_MUTED, size=10),
            False, False, 0,
        )
        interval_row.pack_start(iv_left, True, True, 0)
        interval_row.pack_end(make_label("500ms", size=12), False, False, 0)
        opts_card.pack_start(interval_row, False, False, 8)

        self.pack_start(opts_card, False, False, 0)

        # --- About card ---
        about_card = make_card()
        about_label = Gtk.Label()
        about_label.set_markup(
            f'<span foreground="{TEXT_MUTED}" font_desc="11">'
            f'OpenFreezeCenter for Bazzite\n'
            f'<span font_desc="10">EC access via /dev/port · 130+ MSI models supported</span>'
            f'</span>'
        )
        about_label.set_justify(Gtk.Justification.CENTER)
        about_label.set_halign(Gtk.Align.CENTER)
        about_card.pack_start(about_label, False, False, 4)
        self.pack_start(about_card, False, False, 0)
