# ui/battery.py
"""Battery page — charge threshold selector with battery icon."""

import math

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import cairo

from ui.theme import (
    WARNING_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BG_CARD_RGBA, BG_ELEVATED,
    hex_to_rgba, make_label, make_card,
)
from model_config import save_user_config


class BatteryPage(Gtk.Box):
    """Battery charge threshold configuration page.

    Args:
        model: ModelConfig instance
        ec: ECAccess instance
        user_cfg: user config dict
    """

    THRESHOLDS = [50, 60, 70, 80, 90, 100]

    def __init__(self, model, ec, user_cfg):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.model = model
        self.ec = ec
        self.user_cfg = user_cfg
        self._current = user_cfg.get("battery_threshold", 100)

        # --- Charge threshold card ---
        card = make_card()
        card.pack_start(make_label("Charge Threshold", size=13, bold=True), False, False, 0)
        card.pack_start(
            make_label("Limit maximum battery charge to extend battery lifespan",
                        color=TEXT_MUTED, size=11),
            False, False, 0,
        )

        # Battery icon + percentage display
        icon_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        icon_row.set_margin_top(8)

        self._battery_icon = Gtk.DrawingArea()
        self._battery_icon.set_size_request(80, 40)
        self._battery_icon.connect("draw", self._draw_battery)
        icon_row.pack_start(self._battery_icon, False, False, 0)

        pct_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._pct_label = Gtk.Label()
        self._pct_label.set_markup(
            f'<span foreground="{WARNING_COLOR}" font_desc="28" weight="bold">'
            f'{self._current}</span>'
            f'<span foreground="{WARNING_COLOR}88" font_desc="16">%</span>'
        )
        self._pct_label.set_halign(Gtk.Align.START)
        pct_box.pack_start(self._pct_label, False, False, 0)
        pct_box.pack_start(make_label("Charge limit", color=TEXT_MUTED, size=10), False, False, 0)
        icon_row.pack_start(pct_box, False, False, 0)

        card.pack_start(icon_row, False, False, 8)

        # Threshold selector buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._threshold_buttons = {}
        for val in self.THRESHOLDS:
            btn = Gtk.Button(label=f"{val}%")
            btn.get_style_context().add_class("threshold-btn")
            if val == self._current:
                btn.get_style_context().add_class("active")
            btn.connect("clicked", self._on_threshold_clicked, val)
            self._threshold_buttons[val] = btn
            btn_row.pack_start(btn, False, False, 0)

        card.pack_start(btn_row, False, False, 4)
        self.pack_start(card, False, False, 0)

        # --- Info card ---
        info_card = make_card()
        info_lines = [
            "Setting a threshold below 100% helps preserve long-term battery health",
            "The laptop will stop charging when the battery reaches this level",
            "Recommended: 80% for daily use on AC power",
        ]
        for line in info_lines:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            bullet = Gtk.Label()
            bullet.set_markup(f'<span foreground="{WARNING_COLOR}">&#8226;</span>')
            row.pack_start(bullet, False, False, 0)
            row.pack_start(make_label(line, color=TEXT_SECONDARY, size=11), False, False, 0)
            info_card.pack_start(row, False, False, 2)
        self.pack_start(info_card, False, False, 0)

    def _draw_battery(self, widget, cr):
        """Draw a battery icon with fill level."""
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height
        rgba = hex_to_rgba(WARNING_COLOR)

        # Battery body
        body_w = w - 8
        cr.set_source_rgba(*rgba)
        cr.set_line_width(2)
        cr.rectangle(1, 1, body_w, h - 2)
        cr.stroke()

        # Terminal nub
        cr.rectangle(body_w + 1, h * 0.25, 6, h * 0.5)
        cr.fill()

        # Fill level
        fill_frac = self._current / 100.0
        fill_w = (body_w - 4) * fill_frac
        grad = cairo.LinearGradient(2, 0, 2 + fill_w, 0)
        grad.add_color_stop_rgba(0, rgba[0], rgba[1], rgba[2], 0.4)
        grad.add_color_stop_rgba(1, rgba[0], rgba[1], rgba[2], 0.8)
        cr.set_source(grad)
        cr.rectangle(3, 3, fill_w, h - 6)
        cr.fill()

    def _on_threshold_clicked(self, button, value):
        if self.ec.is_read_only:
            return

        self._current = value
        self.ec.write_byte(self.model.battery_threshold_addr, value + 128)
        self.user_cfg["battery_threshold"] = value
        save_user_config(self.user_cfg)

        # Update button styles
        for val, btn in self._threshold_buttons.items():
            ctx = btn.get_style_context()
            if val == value:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

        # Update display
        self._pct_label.set_markup(
            f'<span foreground="{WARNING_COLOR}" font_desc="28" weight="bold">'
            f'{value}</span>'
            f'<span foreground="{WARNING_COLOR}88" font_desc="16">%</span>'
        )
        self._battery_icon.queue_draw()
