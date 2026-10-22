# ui/settings.py
"""Settings page — system info, options, and about."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ec_access import get_lockdown_status
from ui.helpers import (
    build_verified_device_url, build_verified_device_text,
    open_url_async, copy_to_clipboard,
)
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, SUCCESS_COLOR, WARNING_COLOR, GPU_COLOR,
    make_label, make_card,
)


class SettingsPage(Gtk.Box):
    """Settings page with system info and options.

    Args:
        model: ModelConfig instance
        ec: ECAccess instance
        window: Gtk.Window instance (for updating title on read-only toggle)
        on_read_only_changed: callback(bool) when read-only mode changes
    """

    def __init__(self, model, ec, window=None, on_read_only_changed=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._ec = ec
        self._model = model
        self._window = window
        self._on_read_only_changed = on_read_only_changed

        lockdown = get_lockdown_status()

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
            ("Lockdown", lockdown),
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

            val_color = TEXT_PRIMARY
            if value in ("Detected",) or "Supported" in str(value):
                val_color = SUCCESS_COLOR
            elif value == "none":
                val_color = SUCCESS_COLOR
            elif value in ("integrity", "confidentiality"):
                val_color = WARNING_COLOR
            elif value == "active":
                val_color = SUCCESS_COLOR
            elif "read-only" in str(value):
                val_color = TEXT_SECONDARY

            val_label = make_label(str(value), color=val_color, size=12)
            grid.attach(val_label, 1, row_idx, 1, 1)

        info_card.pack_start(grid, False, False, 0)
        self._info_grid = grid
        self._ec_row_idx = 3  # row index of "EC Access"
        self.pack_start(info_card, False, False, 0)

        # --- Options card ---
        opts_card = make_card()
        opts_card.pack_start(make_label("Options", size=13, bold=True), False, False, 0)

        # Read-only mode toggle
        ro_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ro_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ro_left.pack_start(make_label("Read-only mode", size=12), False, False, 0)
        ro_left.pack_start(
            make_label("Disable all EC writes (monitoring only)", color=TEXT_MUTED, size=10),
            False, False, 0,
        )
        ro_row.pack_start(ro_left, True, True, 0)

        self._ro_switch = Gtk.Switch()
        self._ro_switch.set_active(ec.is_read_only)
        self._ro_switch.set_valign(Gtk.Align.CENTER)
        self._ro_switch.connect("state-set", self._on_read_only_toggled)
        ro_row.pack_end(self._ro_switch, False, False, 0)
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

        # --- Community & Device Feedback card ---
        community_card = make_card()
        community_card.pack_start(
            make_label("Device Verification & Community", size=13, bold=True),
            False, False, 0,
        )
        community_card.pack_start(
            make_label(
                "Working well on your machine? Submit a 1-click report to verify your laptop model on GitHub.",
                color=TEXT_MUTED, size=11,
            ),
            False, False, 0,
        )

        chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        chip_box.set_margin_top(4)
        chip_box.set_margin_bottom(2)
        status_badge = Gtk.Label()
        status_badge.set_markup(
            f'<span foreground="{SUCCESS_COLOR}" font_desc="11" weight="bold">'
            f'✓ Active Model: {model.model_name} ({model.board_name}, {model.group})</span>'
        )
        chip_box.pack_start(status_badge, False, False, 0)
        community_card.pack_start(chip_box, False, False, 0)

        # Action buttons row
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_row.set_margin_top(4)

        confirm_btn = Gtk.Button(label="✓ Confirm on GitHub")
        confirm_btn.get_style_context().add_class("accent-btn")

        copy_btn = Gtk.Button(label="Copy Details")
        copy_btn.get_style_context().add_class("secondary-btn")

        action_row.pack_start(confirm_btn, False, False, 0)
        action_row.pack_start(copy_btn, False, False, 0)

        feedback_label = Gtk.Label()
        feedback_label.set_valign(Gtk.Align.CENTER)
        action_row.pack_start(feedback_label, False, False, 8)

        community_card.pack_start(action_row, False, False, 0)

        def _on_confirm_clicked(_):
            url = build_verified_device_url(model)
            open_url_async(url)
            feedback_label.set_markup(
                f'<span foreground="{SUCCESS_COLOR}" font_desc="11">Opened GitHub in browser!</span>'
            )
            GLib.timeout_add_seconds(3, lambda: (feedback_label.set_text("") or False))

        def _on_copy_clicked(_):
            report_text = build_verified_device_text(model)
            copy_to_clipboard(report_text)
            copy_btn.set_label("Copied!")
            GLib.timeout_add_seconds(2, lambda: (copy_btn.set_label("Copy Details") or False))

        confirm_btn.connect("clicked", _on_confirm_clicked)
        copy_btn.connect("clicked", _on_copy_clicked)

        # Links row
        links_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        links_box.set_margin_top(8)

        def _make_link(title, uri):
            btn = Gtk.LinkButton(uri=uri, label=title)
            btn.get_style_context().add_class("link-btn")
            return btn

        links_box.pack_start(_make_link("★ Star on GitHub", "https://github.com/gsriram24/FrostCenter"), False, False, 0)
        links_box.pack_start(_make_link("💬 Community Discussions", "https://github.com/gsriram24/FrostCenter/discussions"), False, False, 0)
        links_box.pack_start(_make_link("🐛 Report an Issue", "https://github.com/gsriram24/FrostCenter/issues"), False, False, 0)

        community_card.pack_start(links_box, False, False, 0)
        self.pack_start(community_card, False, False, 0)

        # --- About card ---
        about_card = make_card()
        about_label = Gtk.Label()
        about_label.set_markup(
            f'<span foreground="{TEXT_MUTED}" font_desc="11">'
            f'FrostCenter\n'
            f'<span font_desc="10">MSI laptop fan control for Linux · 130+ models supported</span>'
            f'</span>'
        )
        about_label.set_justify(Gtk.Justification.CENTER)
        about_label.set_halign(Gtk.Align.CENTER)
        about_card.pack_start(about_label, False, False, 4)
        self.pack_start(about_card, False, False, 0)

    def _on_read_only_toggled(self, switch, state):
        """Toggle read-only mode live."""
        self._ec.is_read_only = state

        # Update window title
        if self._window:
            title = f"FrostCenter — {self._model.model_name}"
            if state:
                title += " [READ-ONLY]"
            self._window.set_title(title)

        # Update EC Access row in info grid
        ec_val = self._info_grid.get_child_at(1, self._ec_row_idx)
        if ec_val:
            ec_val.set_markup(
                f'<span foreground="{TEXT_SECONDARY if state else SUCCESS_COLOR}" '
                f'font_desc="12" weight="normal">'
                f'/dev/port ({"read-only" if state else "active"})</span>'
            )

        # Notify other pages
        if self._on_read_only_changed:
            self._on_read_only_changed(state)

        return False
