# ui/fan_curve_editor.py
"""Interactive fan curve editor — Cairo graph with click-to-edit popovers."""

import math

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, PangoCairo
import cairo

from ui.theme import (
    BG_CARD_RGBA, BORDER_RGBA, TEXT_MUTED_RGBA, GRID_RGBA,
    TEXT_MUTED, hex_to_rgba,
)


class FanCurveEditor(Gtk.Box):
    """Interactive fan curve editor with Cairo graph and click-to-edit popovers.

    Args:
        color: hex accent color for the curve
        temps: list of 6 temperature thresholds (read-only, from EC)
        speeds: list of 7 speed values (editable, 0-150)
        on_speed_changed: callback(index, new_speed) called when user edits a speed
    """

    MARGIN_LEFT = 40
    MARGIN_RIGHT = 16
    MARGIN_TOP = 12
    MARGIN_BOTTOM = 28
    POINT_RADIUS = 7
    HIT_RADIUS = 14  # click detection radius

    def __init__(self, color, temps, speeds, on_speed_changed=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.color = color
        self.rgba = hex_to_rgba(color)
        self.temps = list(temps)   # 6 temp thresholds
        self.speeds = list(speeds) # 7 speed values
        self.on_speed_changed = on_speed_changed
        self.current_temp = 0
        self._hovered = -1
        self._selected = -1
        self._enabled = True

        # Drawing area
        self._da = Gtk.DrawingArea()
        self._da.set_size_request(-1, 220)
        self._da.connect("draw", self._on_draw)
        self._da.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self._da.connect("button-press-event", self._on_click)
        self._da.connect("motion-notify-event", self._on_motion)
        self._da.connect("leave-notify-event", self._on_leave)
        self.pack_start(self._da, True, True, 0)

        # Popover for editing
        self._popover = Gtk.Popover()
        self._popover.set_relative_to(self._da)
        self._popover.set_position(Gtk.PositionType.TOP)
        self._popover.connect("closed", self._on_popover_closed)

        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pop_box.set_margin_start(12)
        pop_box.set_margin_end(12)
        pop_box.set_margin_top(10)
        pop_box.set_margin_bottom(10)

        self._pop_title = Gtk.Label()
        self._pop_title.set_halign(Gtk.Align.START)
        pop_box.pack_start(self._pop_title, False, False, 0)

        fields = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Temperature (read-only display)
        temp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        temp_box.pack_start(Gtk.Label(label="Temp (°C)"), False, False, 0)
        self._pop_temp_label = Gtk.Label()
        self._pop_temp_label.set_halign(Gtk.Align.CENTER)
        temp_box.pack_start(self._pop_temp_label, False, False, 0)
        fields.pack_start(temp_box, False, False, 0)

        # Speed (editable)
        speed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        speed_box.pack_start(Gtk.Label(label="Speed (%)"), False, False, 0)
        self._pop_speed = Gtk.SpinButton.new_with_range(0, 150, 1)
        self._pop_speed.connect("value-changed", self._on_spin_changed)
        self._pop_speed.connect("activate", lambda w: self._popover.popdown())
        speed_box.pack_start(self._pop_speed, False, False, 0)
        fields.pack_start(speed_box, False, False, 0)

        pop_box.pack_start(fields, False, False, 0)
        self._popover.add(pop_box)
        pop_box.show_all()

    def set_curve(self, speeds):
        """Update the 7 speed values and redraw."""
        self.speeds = list(speeds)
        self._da.queue_draw()

    def set_temps(self, temps):
        """Update the 6 temperature thresholds and redraw."""
        self.temps = list(temps)
        self._da.queue_draw()

    def set_current_temp(self, temp):
        """Update the 'Now' temperature indicator."""
        self.current_temp = temp
        self._da.queue_draw()

    def set_enabled(self, enabled):
        """Enable or disable interaction (greyed out when disabled)."""
        self._enabled = enabled
        self._da.set_sensitive(enabled)
        self._da.queue_draw()

    def _get_point_coords(self, width, height):
        """Compute pixel coordinates for the 7 control points."""
        ml, mr, mt, mb = self.MARGIN_LEFT, self.MARGIN_RIGHT, self.MARGIN_TOP, self.MARGIN_BOTTOM
        gw = width - ml - mr
        gh = height - mt - mb
        if gw <= 0 or gh <= 0:
            return []

        # X positions: 7 points evenly spread across the temp range
        # Point 0 is the base (below first temp threshold), points 1-6 map to temps[0-5]
        temp_min = self.temps[0] - 10 if self.temps else 30
        temp_max = self.temps[-1] + 5 if self.temps else 100
        temp_range = temp_max - temp_min
        if temp_range <= 0:
            temp_range = 1

        point_temps = [temp_min] + self.temps  # 7 temp values for 7 points

        coords = []
        for i in range(7):
            x = ml + ((point_temps[i] - temp_min) / temp_range) * gw
            y_frac = self.speeds[i] / 150.0
            y = mt + (1 - y_frac) * gh
            coords.append((x, y, point_temps[i]))
        return coords

    def _on_draw(self, widget, cr):
        alloc = self._da.get_allocation()
        w, h = alloc.width, alloc.height
        ml, mr, mt, mb = self.MARGIN_LEFT, self.MARGIN_RIGHT, self.MARGIN_TOP, self.MARGIN_BOTTOM
        gw = w - ml - mr
        gh = h - mt - mb

        # Background
        cr.set_source_rgba(*BG_CARD_RGBA)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        if gw <= 0 or gh <= 0:
            return

        alpha_mult = 1.0 if self._enabled else 0.3

        # Y-axis labels and grid
        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription.from_string("Sans 9")
        layout.set_font_description(font_desc)

        for pct in [0, 25, 50, 75, 100]:
            y = mt + (1 - pct / 100.0) * gh
            # Grid line
            if pct > 0 and pct < 100:
                cr.set_source_rgba(*GRID_RGBA)
                cr.set_dash([4, 4])
                cr.move_to(ml, y)
                cr.line_to(ml + gw, y)
                cr.stroke()
                cr.set_dash([])
            # Label
            cr.set_source_rgba(*TEXT_MUTED_RGBA)
            layout.set_text(f"{pct}%", -1)
            lw, lh = layout.get_pixel_size()
            cr.move_to(ml - lw - 6, y - lh / 2)
            PangoCairo.show_layout(cr, layout)

        # X-axis temp labels
        coords = self._get_point_coords(w, h)
        if not coords:
            return

        for i, (px, py, pt) in enumerate(coords):
            cr.set_source_rgba(*TEXT_MUTED_RGBA)
            layout.set_text(f"{int(pt)}°", -1)
            lw, lh = layout.get_pixel_size()
            cr.move_to(px - lw / 2, mt + gh + 4)
            PangoCairo.show_layout(cr, layout)

        # Gradient fill under curve
        cr.move_to(coords[0][0], coords[0][1])
        for cx, cy, _ in coords[1:]:
            cr.line_to(cx, cy)
        cr.line_to(coords[-1][0], mt + gh)
        cr.line_to(coords[0][0], mt + gh)
        cr.close_path()
        grad = cairo.LinearGradient(0, mt, 0, mt + gh)
        grad.add_color_stop_rgba(0, self.rgba[0], self.rgba[1], self.rgba[2], 0.15 * alpha_mult)
        grad.add_color_stop_rgba(1, self.rgba[0], self.rgba[1], self.rgba[2], 0.0)
        cr.set_source(grad)
        cr.fill()

        # Curve line
        cr.set_line_width(2.5)
        cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], alpha_mult)
        cr.move_to(coords[0][0], coords[0][1])
        for cx, cy, _ in coords[1:]:
            cr.line_to(cx, cy)
        cr.stroke()

        # Control points
        for i, (px, py, _) in enumerate(coords):
            if i == self._selected:
                # Outer glow
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], 0.3 * alpha_mult)
                cr.arc(px, py, self.POINT_RADIUS + 3, 0, 2 * math.pi)
                cr.fill()
                # Filled point
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], alpha_mult)
                cr.arc(px, py, self.POINT_RADIUS, 0, 2 * math.pi)
                cr.fill()
                # White border
                cr.set_source_rgba(1, 1, 1, alpha_mult)
                cr.set_line_width(2)
                cr.arc(px, py, self.POINT_RADIUS, 0, 2 * math.pi)
                cr.stroke()
            elif i == self._hovered:
                # Larger hollow
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], 0.2 * alpha_mult)
                cr.arc(px, py, self.POINT_RADIUS + 2, 0, 2 * math.pi)
                cr.fill()
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], alpha_mult)
                cr.set_line_width(2.5)
                cr.arc(px, py, self.POINT_RADIUS, 0, 2 * math.pi)
                cr.stroke()
            else:
                # Normal hollow
                cr.set_source_rgba(*BG_CARD_RGBA)
                cr.arc(px, py, self.POINT_RADIUS, 0, 2 * math.pi)
                cr.fill()
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], alpha_mult)
                cr.set_line_width(2.5)
                cr.arc(px, py, self.POINT_RADIUS, 0, 2 * math.pi)
                cr.stroke()

        # "Now" temperature indicator
        if self.current_temp > 0 and coords:
            temp_min = coords[0][2]
            temp_max = coords[-1][2]
            temp_range = temp_max - temp_min
            if temp_range > 0:
                now_x = ml + ((self.current_temp - temp_min) / temp_range) * gw
                now_x = max(ml, min(ml + gw, now_x))
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], 0.4 * alpha_mult)
                cr.set_dash([4, 4])
                cr.set_line_width(2)
                cr.move_to(now_x, mt)
                cr.line_to(now_x, mt + gh)
                cr.stroke()
                cr.set_dash([])

                # Label
                cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], 0.7 * alpha_mult)
                layout.set_text(f"Now: {self.current_temp}°C", -1)
                lw, lh = layout.get_pixel_size()
                cr.move_to(now_x - lw / 2, mt + gh + 14)
                PangoCairo.show_layout(cr, layout)

    def _hit_test(self, mx, my):
        """Return index of point near (mx, my), or -1."""
        alloc = self._da.get_allocation()
        coords = self._get_point_coords(alloc.width, alloc.height)
        for i, (px, py, _) in enumerate(coords):
            if math.hypot(mx - px, my - py) <= self.HIT_RADIUS:
                return i
        return -1

    def _on_click(self, widget, event):
        if not self._enabled:
            return
        idx = self._hit_test(event.x, event.y)
        if idx >= 0:
            self._selected = idx
            self._show_popover(idx)
        else:
            self._selected = -1
            self._popover.popdown()
        self._da.queue_draw()

    def _on_motion(self, widget, event):
        if not self._enabled:
            return
        idx = self._hit_test(event.x, event.y)
        if idx != self._hovered:
            self._hovered = idx
            self._da.queue_draw()

    def _on_leave(self, widget, event):
        if self._hovered != -1:
            self._hovered = -1
            self._da.queue_draw()

    def _show_popover(self, idx):
        """Show the edit popover positioned near point idx."""
        alloc = self._da.get_allocation()
        coords = self._get_point_coords(alloc.width, alloc.height)
        if idx >= len(coords):
            return

        px, py, pt = coords[idx]
        rect = Gdk.Rectangle()
        rect.x = int(px)
        rect.y = int(py)
        rect.width = 1
        rect.height = 1
        self._popover.set_pointing_to(rect)

        self._pop_title.set_markup(
            f'<span weight="bold" font_desc="11">Point {idx + 1}</span>'
        )
        self._pop_temp_label.set_markup(
            f'<span font_desc="13" weight="bold">{int(pt)}°C</span>'
        )
        self._pop_speed.set_value(self.speeds[idx])
        self._popover.popup()

    def _on_spin_changed(self, spin):
        if self._selected < 0:
            return
        new_val = int(spin.get_value())
        self.speeds[self._selected] = new_val
        self._da.queue_draw()
        if self.on_speed_changed:
            self.on_speed_changed(self._selected, new_val)

    def _on_popover_closed(self, popover):
        self._selected = -1
        self._da.queue_draw()
