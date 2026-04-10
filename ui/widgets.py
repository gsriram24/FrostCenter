# ui/widgets.py
"""Reusable Cairo-based widgets: RollingGraph and StatCard."""

import math
from collections import deque

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Pango, PangoCairo
import cairo

from ui.theme import (
    BG_CARD_RGBA, BORDER_RGBA, TEXT_MUTED_RGBA, GRID_RGBA,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    hex_to_rgba, make_label,
)


class RollingGraph(Gtk.DrawingArea):
    """A real-time rolling line chart rendered with Cairo.

    Args:
        lines: list of dicts, each with:
            - 'color': hex color string (e.g. '#ff4655')
            - 'label': display name (e.g. 'CPU')
            - 'dashed': bool, whether to use dashed line style
        y_min: minimum y-axis value
        y_max: maximum y-axis value
        y_label: label for y-axis unit (e.g. '°C', 'RPM')
        max_points: number of data points to retain (default 120 = 60s at 500ms)
    """

    MARGIN_LEFT = 40
    MARGIN_RIGHT = 16
    MARGIN_TOP = 12
    MARGIN_BOTTOM = 20

    def __init__(self, lines, y_min=0, y_max=100, y_label="", max_points=120):
        super().__init__()
        self.lines = lines
        self.y_min = y_min
        self.y_max = y_max
        self.y_label = y_label
        self.max_points = max_points
        self.data = [deque(maxlen=max_points) for _ in lines]
        self.set_size_request(-1, 140)
        self.connect("draw", self._on_draw)

    def add_point(self, line_index, value):
        """Append a data point to the given line. Call queue_draw() after all lines updated."""
        self.data[line_index].append(value)

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height
        ml, mr, mt, mb = self.MARGIN_LEFT, self.MARGIN_RIGHT, self.MARGIN_TOP, self.MARGIN_BOTTOM
        gw = w - ml - mr  # graph area width
        gh = h - mt - mb  # graph area height

        # Background
        cr.set_source_rgba(*BG_CARD_RGBA)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        if gw <= 0 or gh <= 0:
            return

        # Auto-scale y_max if data exceeds it
        actual_max = self.y_max
        for d in self.data:
            if d:
                actual_max = max(actual_max, max(d) * 1.1)
        y_range = actual_max - self.y_min
        if y_range <= 0:
            y_range = 1

        # Y-axis labels and grid lines
        num_grid = 4
        cr.set_line_width(1)
        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription.from_string("Sans 9")
        layout.set_font_description(font_desc)

        for i in range(num_grid + 1):
            frac = i / num_grid
            y = mt + frac * gh
            val = actual_max - frac * y_range

            # Grid line
            if i > 0 and i < num_grid:
                cr.set_source_rgba(*GRID_RGBA)
                cr.set_dash([4, 4])
                cr.move_to(ml, y)
                cr.line_to(ml + gw, y)
                cr.stroke()
                cr.set_dash([])

            # Label
            cr.set_source_rgba(*TEXT_MUTED_RGBA)
            label_text = f"{int(val)}{self.y_label}"
            layout.set_text(label_text, -1)
            lw, lh = layout.get_pixel_size()
            cr.move_to(ml - lw - 6, y - lh / 2)
            PangoCairo.show_layout(cr, layout)

        # Draw each data line
        for idx, line_cfg in enumerate(self.lines):
            points = self.data[idx]
            if len(points) < 2:
                continue

            rgba = hex_to_rgba(line_cfg['color'])
            n = len(points)
            coords = []
            for i, val in enumerate(points):
                x = ml + (i / (self.max_points - 1)) * gw
                y_frac = (val - self.y_min) / y_range
                y = mt + (1 - y_frac) * gh
                y = max(mt, min(mt + gh, y))
                coords.append((x, y))

            # Gradient fill under line
            cr.move_to(coords[0][0], coords[0][1])
            for cx, cy in coords[1:]:
                cr.line_to(cx, cy)
            cr.line_to(coords[-1][0], mt + gh)
            cr.line_to(coords[0][0], mt + gh)
            cr.close_path()
            grad = cairo.LinearGradient(0, mt, 0, mt + gh)
            grad.add_color_stop_rgba(0, rgba[0], rgba[1], rgba[2], 0.25)
            grad.add_color_stop_rgba(1, rgba[0], rgba[1], rgba[2], 0.0)
            cr.set_source(grad)
            cr.fill()

            # Line
            cr.set_line_width(2)
            cr.set_source_rgba(*rgba)
            if line_cfg.get('dashed'):
                cr.set_dash([6, 4])
            else:
                cr.set_dash([])
            cr.move_to(coords[0][0], coords[0][1])
            for cx, cy in coords[1:]:
                cr.line_to(cx, cy)
            cr.stroke()
            cr.set_dash([])

        # Legend (top-right)
        legend_x = ml + gw
        legend_y = mt + 4
        layout.set_font_description(Pango.FontDescription.from_string("Sans 9"))
        for idx, line_cfg in enumerate(self.lines):
            rgba = hex_to_rgba(line_cfg['color'])
            label_text = line_cfg['label']
            layout.set_text(label_text, -1)
            lw, lh = layout.get_pixel_size()
            legend_x -= lw + 20

            # Color dash
            cr.set_source_rgba(*rgba)
            cr.set_line_width(2)
            if line_cfg.get('dashed'):
                cr.set_dash([4, 3])
            cr.move_to(legend_x, legend_y + lh / 2)
            cr.line_to(legend_x + 12, legend_y + lh / 2)
            cr.stroke()
            cr.set_dash([])

            # Text
            cr.move_to(legend_x + 15, legend_y)
            PangoCairo.show_layout(cr, layout)


class StatCard(Gtk.Box):
    """A temperature + RPM display card with large number and min/max.

    Args:
        label: display name ('CPU' or 'GPU')
        color: hex accent color
    """

    def __init__(self, label, color):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.get_style_context().add_class("card")
        self.color = color
        self._min = 999
        self._max = 0

        # Top row: label + min/max
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._label = make_label(label, color, size=11, bold=True, uppercase=True)
        top_row.pack_start(self._label, False, False, 0)
        self._minmax_label = make_label("", color + "88", size=9)
        self._minmax_label.set_halign(Gtk.Align.END)
        top_row.pack_end(self._minmax_label, False, False, 0)
        self.pack_start(top_row, False, False, 0)

        # Large temp number
        self._temp_label = Gtk.Label()
        self._temp_label.set_markup(
            f'<span foreground="{color}" font_desc="32" weight="bold">--</span>'
            f'<span foreground="{color}88" font_desc="16">°C</span>'
        )
        self._temp_label.set_halign(Gtk.Align.START)
        self.pack_start(self._temp_label, False, False, 0)

        # Bottom row: fan RPM
        rpm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        rpm_row.pack_start(make_label("Fan", TEXT_SECONDARY, size=11), False, False, 0)
        self._rpm_label = make_label("-- RPM", color, size=12, bold=True)
        self._rpm_label.set_halign(Gtk.Align.END)
        rpm_row.pack_end(self._rpm_label, False, False, 0)
        self.pack_start(rpm_row, False, False, 0)

    def update(self, temp, rpm):
        """Update displayed values. Tracks min/max internally."""
        if temp > 0:
            if temp < self._min:
                self._min = temp
            if temp > self._max:
                self._max = temp

        self._temp_label.set_markup(
            f'<span foreground="{self.color}" font_desc="32" weight="bold">{temp}</span>'
            f'<span foreground="{self.color}88" font_desc="16">°C</span>'
        )
        self._minmax_label.set_markup(
            f'<span foreground="{self.color}88" font_desc="9">'
            f'Min {self._min} / Max {self._max}</span>'
        )
        self._rpm_label.set_markup(
            f'<span foreground="{self.color}" font_desc="12" weight="bold">{rpm} RPM</span>'
        )
