# OpenFreezeCenter UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal fixed-layout GTK3 GUI with a polished, sidebar-navigated application featuring real-time Cairo graphs, an interactive fan curve editor, and dark themed styling with MSI red/cyan accents.

**Architecture:** Multi-file UI package (`ui/`) with each page as a separate module. `OFC.py` becomes a thin entry point that wires together backend (`ec_access`, `model_config`) and UI pages via a `Gtk.Stack`. All custom rendering (graphs, fan curves, battery icon) uses Cairo on `Gtk.DrawingArea`. The existing `fan_profile()`, `speed_checker()`, and `safe_read_*()` helper functions move into a shared `ui/helpers.py` so pages can import them.

**Tech Stack:** Python 3, GTK3 (gi.repository: Gtk, Gdk, GLib, Pango, PangoCairo), Cairo, collections.deque

**Spec:** `docs/superpowers/specs/2026-04-10-ui-overhaul-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ui/__init__.py` | Create | Empty package init |
| `ui/theme.py` | Create | Color constants, CSS provider, label/card helpers |
| `ui/helpers.py` | Create | `safe_read_byte()`, `safe_read_rpm()`, `fan_profile()`, `speed_checker()` — shared EC helpers extracted from current OFC.py |
| `ui/widgets.py` | Create | `RollingGraph`, `StatCard` reusable widgets |
| `ui/fan_curve_editor.py` | Create | `FanCurveEditor` — interactive Cairo fan curve graph with click-to-edit popovers |
| `ui/dashboard.py` | Create | `DashboardPage` — stat cards + temp/RPM rolling graphs |
| `ui/fan_control.py` | Create | `FanControlPage` — profile buttons + fan curve editor + compact temp graph |
| `ui/battery.py` | Create | `BatteryPage` — threshold buttons + battery icon |
| `ui/settings.py` | Create | `SettingsPage` — system info grid + options |
| `OFC.py` | Rewrite | Thin entry point: init backend, build window + sidebar + stack, start timer |
| `install.sh` | Modify | Add `cp -r` for `ui/` directory |

---

### Task 1: Create `ui/__init__.py` and `ui/theme.py`

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/theme.py`

The theme module is the foundation — every other UI file imports colors and helpers from it.

- [ ] **Step 1: Create the `ui/` package**

Create the empty package init:

```python
# ui/__init__.py
```

- [ ] **Step 2: Create `ui/theme.py` with color constants and CSS**

```python
# ui/theme.py
"""Color palette, CSS theme, and widget helper functions."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

# --- Color palette (spec: Design Spec > Color Palette) ---
BG_MAIN = "#12121e"
BG_CARD = "#1a1a2e"
BG_ELEVATED = "#2d2d44"
BORDER = "#2d2d44"
TEXT_PRIMARY = "#cccccc"
TEXT_SECONDARY = "#888888"
TEXT_MUTED = "#666666"
CPU_COLOR = "#ff4655"
GPU_COLOR = "#00d4ff"
WARNING_COLOR = "#ff8c00"
SUCCESS_COLOR = "#00e57a"


def hex_to_rgba(hex_color, alpha=1.0):
    """Convert '#rrggbb' to (r, g, b, a) floats for Cairo."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return (r, g, b, alpha)


# Pre-computed Cairo RGBA tuples
CPU_RGBA = hex_to_rgba(CPU_COLOR)
GPU_RGBA = hex_to_rgba(GPU_COLOR)
WARNING_RGBA = hex_to_rgba(WARNING_COLOR)
BG_MAIN_RGBA = hex_to_rgba(BG_MAIN)
BG_CARD_RGBA = hex_to_rgba(BG_CARD)
BORDER_RGBA = hex_to_rgba(BORDER)
TEXT_MUTED_RGBA = hex_to_rgba(TEXT_MUTED)
GRID_RGBA = hex_to_rgba(BG_ELEVATED, 0.5)


_CSS = f"""
window {{
    background-color: {BG_MAIN};
}}
.sidebar {{
    background-color: {BG_CARD};
}}
.sidebar-btn {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    padding: 12px 20px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
.sidebar-btn:hover {{
    background-color: {BG_ELEVATED};
}}
.sidebar-btn.active {{
    color: {CPU_COLOR};
    font-weight: 600;
    background-color: rgba(255, 70, 85, 0.08);
    border-left-color: {CPU_COLOR};
}}
.card {{
    background-color: {BG_CARD};
    border-radius: 10px;
    border: 1px solid {BORDER};
    padding: 16px;
}}
.profile-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 16px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
.profile-btn:hover {{
    background-color: rgba(255, 70, 85, 0.15);
}}
.profile-btn.active {{
    background-color: rgba(255, 70, 85, 0.13);
    border-color: {CPU_COLOR};
    color: {CPU_COLOR};
    font-weight: 600;
}}
.boost-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 16px;
    color: {WARNING_COLOR};
    font-size: 12px;
}}
.boost-btn.active {{
    background-color: rgba(255, 140, 0, 0.13);
    border-color: {WARNING_COLOR};
    font-weight: 600;
}}
.threshold-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 14px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
.threshold-btn.active {{
    background-color: rgba(255, 140, 0, 0.13);
    border-color: {WARNING_COLOR};
    color: {WARNING_COLOR};
    font-weight: 600;
}}
.profile-indicator {{
    background-color: rgba(255, 70, 85, 0.13);
    border: 1px solid rgba(255, 70, 85, 0.4);
    border-radius: 6px;
    padding: 6px 12px;
    color: {CPU_COLOR};
    font-size: 12px;
}}
""".encode()


def apply_theme(window):
    """Load the dark CSS theme onto the given window's screen."""
    provider = Gtk.CssProvider()
    provider.load_from_data(_CSS)
    screen = window.get_screen()
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def make_label(text, color=TEXT_PRIMARY, size=12, bold=False, uppercase=False):
    """Create a styled Gtk.Label."""
    label = Gtk.Label()
    weight = "bold" if bold else "normal"
    display = text.upper() if uppercase else text
    markup = f'<span foreground="{color}" font_desc="{size}" weight="{weight}">{display}</span>'
    label.set_markup(markup)
    label.set_halign(Gtk.Align.START)
    label.set_valign(Gtk.Align.CENTER)
    return label


def make_card():
    """Create a Gtk.Box styled as a card container."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.get_style_context().add_class("card")
    return box
```

- [ ] **Step 3: Verify the theme module loads without errors**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "from ui.theme import apply_theme, CPU_COLOR, make_label, make_card, hex_to_rgba; print('theme OK')"
```

Expected: `theme OK`

- [ ] **Step 4: Commit**

```bash
git add ui/__init__.py ui/theme.py
git commit -m "feat(ui): add theme module with color palette and CSS"
```

---

### Task 2: Create `ui/helpers.py` — shared EC helper functions

**Files:**
- Create: `ui/helpers.py`

Extract `safe_read_byte()`, `safe_read_rpm()`, `fan_profile()`, `speed_checker()`, and profile constants from the current `OFC.py` into a shared module. These functions need `ec`, `model`, and `user_cfg` references, which we'll pass explicitly rather than using globals.

- [ ] **Step 1: Create `ui/helpers.py`**

```python
# ui/helpers.py
"""Shared EC helper functions for fan control and monitoring."""

from ec_access import ECTimeoutError
from model_config import save_user_config

BASIC_SPEED = [[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]]

PROFILE_DISPLAY = {
    "auto": "Auto",
    "silent": "Silent",
    "basic": "Basic",
    "advanced": "Advanced",
}


def safe_read_byte(ec, addr):
    """Read a byte from EC, return 0 on error."""
    try:
        return ec.read_byte(addr)
    except ECTimeoutError:
        return 0


def safe_read_rpm(ec, model, addr):
    """Read fan RPM from EC. Returns 0 if fan is stopped or on error."""
    try:
        raw = ec.read_word(addr)
        if raw == 0:
            return 0
        return model.rpm_divisor // raw
    except (ECTimeoutError, ZeroDivisionError):
        return 0


def speed_checker(speeds, offset):
    """Clamp fan speeds (with offset) to 0-150 range."""
    result = [row[:] for row in speeds]
    for row in range(len(result)):
        for col in range(7):
            val = result[row][col] + offset
            result[row][col] = max(0, min(150, val))
    return result


def fan_profile(ec, model, profile_name, speeds=None):
    """Write a fan profile to the EC. No-op if ec is read-only."""
    if ec.is_read_only:
        return

    if profile_name == "cooler_booster":
        current = ec.read_byte(model.cooler_boost_addr)
        ec.write_byte(model.cooler_boost_addr, current | (1 << model.cooler_boost_bit))
    else:
        current = ec.read_byte(model.cooler_boost_addr)
        ec.write_byte(model.cooler_boost_addr, current & ~(1 << model.cooler_boost_bit))

        mode_value = model.fan_modes.get(profile_name)
        if mode_value is not None:
            ec.write_byte(model.fan_mode_addr, mode_value)

        if speeds and model.has_gpu:
            for i in range(7):
                ec.write_byte(model.cpu_fan_curve_speed_addrs[i], speeds[0][i])
                ec.write_byte(model.gpu_fan_curve_speed_addrs[i], speeds[1][i])
        elif speeds:
            for i in range(7):
                ec.write_byte(model.cpu_fan_curve_speed_addrs[i], speeds[0][i])


def apply_profile(ec, model, user_cfg, profile_name):
    """Apply a named profile — resolves speeds from user_cfg and writes to EC."""
    if profile_name == "auto":
        fan_profile(ec, model, "auto", speed_checker(user_cfg["auto_speed"], 0))
    elif profile_name == "basic":
        offset = max(-30, min(30, user_cfg["basic_offset"]))
        fan_profile(ec, model, "basic", speed_checker(BASIC_SPEED, offset))
    elif profile_name == "advanced":
        fan_profile(ec, model, "advanced", speed_checker(user_cfg["adv_speed"], 0))
    elif profile_name == "silent":
        fan_profile(ec, model, "silent")
    elif profile_name == "cooler_booster":
        fan_profile(ec, model, "cooler_booster")

    user_cfg["profile"] = profile_name
    save_user_config(user_cfg)
```

- [ ] **Step 2: Verify it imports cleanly**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "from ui.helpers import safe_read_byte, safe_read_rpm, fan_profile, apply_profile, PROFILE_DISPLAY; print('helpers OK')"
```

Expected: `helpers OK`

- [ ] **Step 3: Commit**

```bash
git add ui/helpers.py
git commit -m "feat(ui): extract EC helper functions into ui/helpers.py"
```

---

### Task 3: Create `ui/widgets.py` — RollingGraph and StatCard

**Files:**
- Create: `ui/widgets.py`

These are the core reusable drawing widgets used by Dashboard and Fan Control pages.

- [ ] **Step 1: Create `ui/widgets.py`**

```python
# ui/widgets.py
"""Reusable Cairo-based widgets: RollingGraph and StatCard."""

import math
from collections import deque

import gi
gi.require_version('Gtk', '3.0')
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
```

- [ ] **Step 2: Verify widgets import and construct without a display**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "
import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk
from ui.widgets import RollingGraph, StatCard
g = RollingGraph(lines=[{'color': '#ff4655', 'label': 'CPU', 'dashed': False}], y_min=0, y_max=100, y_label='°C')
g.add_point(0, 55)
print(f'RollingGraph OK, points: {len(g.data[0])}')
print('widgets OK')
"
```

Expected: `RollingGraph OK, points: 1` and `widgets OK`

- [ ] **Step 3: Commit**

```bash
git add ui/widgets.py
git commit -m "feat(ui): add RollingGraph and StatCard Cairo widgets"
```

---

### Task 4: Create `ui/fan_curve_editor.py`

**Files:**
- Create: `ui/fan_curve_editor.py`

This is the most complex widget — a Cairo-drawn fan curve with clickable control points and `Gtk.Popover` for editing speed values.

- [ ] **Step 1: Create `ui/fan_curve_editor.py`**

```python
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
```

- [ ] **Step 2: Verify it imports**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "
import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk
from ui.fan_curve_editor import FanCurveEditor
e = FanCurveEditor('#ff4655', [50,60,70,75,82,88], [0,40,48,56,64,72,80])
e.set_current_temp(72)
e.set_enabled(False)
print('FanCurveEditor OK')
"
```

Expected: `FanCurveEditor OK`

- [ ] **Step 3: Commit**

```bash
git add ui/fan_curve_editor.py
git commit -m "feat(ui): add interactive FanCurveEditor with Cairo and popovers"
```

---

### Task 5: Create `ui/dashboard.py`

**Files:**
- Create: `ui/dashboard.py`

- [ ] **Step 1: Create `ui/dashboard.py`**

```python
# ui/dashboard.py
"""Dashboard page — stat cards and rolling temperature/RPM graphs."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ui.theme import CPU_COLOR, GPU_COLOR, make_label, make_card
from ui.widgets import RollingGraph, StatCard
from ui.helpers import safe_read_byte, safe_read_rpm


class DashboardPage(Gtk.Box):
    """Dashboard page with stat cards and real-time graphs.

    Args:
        model: ModelConfig instance
    """

    def __init__(self, model):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.model = model

        # Stat cards row
        cards_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cards_row.set_homogeneous(True)

        self.cpu_card = StatCard("CPU", CPU_COLOR)
        cards_row.pack_start(self.cpu_card, True, True, 0)

        self.gpu_card = None
        if model.has_gpu:
            self.gpu_card = StatCard("GPU", GPU_COLOR)
            cards_row.pack_start(self.gpu_card, True, True, 0)

        self.pack_start(cards_row, False, False, 0)

        # Temperature history graph
        temp_lines = [{'color': CPU_COLOR, 'label': 'CPU', 'dashed': False}]
        if model.has_gpu:
            temp_lines.append({'color': GPU_COLOR, 'label': 'GPU', 'dashed': False})
        self.temp_graph = RollingGraph(
            lines=temp_lines, y_min=25, y_max=100, y_label="°C"
        )
        temp_card = make_card()
        temp_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        temp_header.pack_start(make_label("Temperature History", size=12, bold=True), False, False, 0)
        temp_header.pack_end(make_label("Last 60 seconds", color="#666666", size=10), False, False, 0)
        temp_card.pack_start(temp_header, False, False, 0)
        temp_card.pack_start(self.temp_graph, True, True, 0)
        self.pack_start(temp_card, True, True, 0)

        # Fan RPM history graph
        rpm_lines = [{'color': CPU_COLOR, 'label': 'CPU', 'dashed': True}]
        if model.has_gpu:
            rpm_lines.append({'color': GPU_COLOR, 'label': 'GPU', 'dashed': True})
        self.rpm_graph = RollingGraph(
            lines=rpm_lines, y_min=0, y_max=6000, y_label=""
        )
        rpm_card = make_card()
        rpm_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        rpm_header.pack_start(make_label("Fan Speed History", size=12, bold=True), False, False, 0)
        rpm_header.pack_end(make_label("Last 60 seconds", color="#666666", size=10), False, False, 0)
        rpm_card.pack_start(rpm_header, False, False, 0)
        rpm_card.pack_start(self.rpm_graph, True, True, 0)
        self.pack_start(rpm_card, True, True, 0)

    def update(self, ec):
        """Called every 500ms to read EC and update displays."""
        cpu_temp = safe_read_byte(ec, self.model.cpu_temp_addr)
        cpu_rpm = safe_read_rpm(ec, self.model, self.model.cpu_fan_rpm_addr)

        self.cpu_card.update(cpu_temp, cpu_rpm)
        self.temp_graph.add_point(0, cpu_temp)
        self.rpm_graph.add_point(0, cpu_rpm)

        if self.model.has_gpu and self.gpu_card:
            gpu_temp = safe_read_byte(ec, self.model.gpu_temp_addr)
            gpu_rpm = safe_read_rpm(ec, self.model, self.model.gpu_fan_rpm_addr)
            self.gpu_card.update(gpu_temp, gpu_rpm)
            self.temp_graph.add_point(1, gpu_temp)
            self.rpm_graph.add_point(1, gpu_rpm)

        self.temp_graph.queue_draw()
        self.rpm_graph.queue_draw()
```

- [ ] **Step 2: Verify import**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "
import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk
from ui.dashboard import DashboardPage
print('dashboard OK')
"
```

Expected: `dashboard OK`

- [ ] **Step 3: Commit**

```bash
git add ui/dashboard.py
git commit -m "feat(ui): add Dashboard page with stat cards and rolling graphs"
```

---

### Task 6: Create `ui/fan_control.py`

**Files:**
- Create: `ui/fan_control.py`

- [ ] **Step 1: Create `ui/fan_control.py`**

```python
# ui/fan_control.py
"""Fan Control page — profile buttons, fan curve editor, temp graph."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ui.theme import (
    CPU_COLOR, GPU_COLOR, WARNING_COLOR, TEXT_SECONDARY,
    make_label, make_card,
)
from ui.widgets import RollingGraph
from ui.fan_curve_editor import FanCurveEditor
from ui.helpers import (
    safe_read_byte, apply_profile, PROFILE_DISPLAY,
)
from model_config import save_user_config


class FanControlPage(Gtk.Box):
    """Fan control page with profile buttons, curve editor, and temp graph.

    Args:
        model: ModelConfig instance
        ec: ECAccess instance
        user_cfg: user config dict (mutated in-place on profile change)
        on_profile_changed: callback(profile_name) to update sidebar indicator
    """

    def __init__(self, model, ec, user_cfg, on_profile_changed=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.model = model
        self.ec = ec
        self.user_cfg = user_cfg
        self.on_profile_changed = on_profile_changed
        self._profile_buttons = {}
        self._boost_button = None
        self._active_curve = "cpu"  # which curve is shown in editor

        # --- Profile toggle buttons ---
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        for mode_name in model.fan_modes:
            display = PROFILE_DISPLAY.get(mode_name, mode_name.title())
            btn = Gtk.Button(label=display)
            btn.get_style_context().add_class("profile-btn")
            btn.connect("clicked", self._on_profile_clicked, mode_name)
            self._profile_buttons[mode_name] = btn
            btn_row.pack_start(btn, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(4)
        sep.set_margin_end(4)
        btn_row.pack_start(sep, False, False, 0)

        # Cooler Boost toggle
        self._boost_button = Gtk.Button(label="Cooler Boost")
        self._boost_button.get_style_context().add_class("boost-btn")
        self._boost_button.connect("clicked", self._on_boost_clicked)
        btn_row.pack_start(self._boost_button, False, False, 0)

        self.pack_start(btn_row, False, False, 0)

        # Highlight the current profile
        self._update_profile_buttons(user_cfg.get("profile", "auto"))

        # --- Fan curve editor ---
        curve_card = make_card()

        curve_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        curve_header.pack_start(make_label("Fan Curve Editor", size=12, bold=True), False, False, 0)

        # CPU/GPU tabs (only if model has GPU)
        if model.has_gpu:
            tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            self._cpu_tab = Gtk.Button(label="CPU")
            self._cpu_tab.get_style_context().add_class("profile-btn")
            self._cpu_tab.get_style_context().add_class("active")
            self._cpu_tab.connect("clicked", self._on_curve_tab, "cpu")
            tab_box.pack_start(self._cpu_tab, False, False, 0)

            self._gpu_tab = Gtk.Button(label="GPU")
            self._gpu_tab.get_style_context().add_class("profile-btn")
            self._gpu_tab.connect("clicked", self._on_curve_tab, "gpu")
            tab_box.pack_start(self._gpu_tab, False, False, 0)

            curve_header.pack_end(tab_box, False, False, 0)

        curve_card.pack_start(curve_header, False, False, 0)

        # Subtitle
        curve_card.pack_start(
            make_label("Click a point to edit its speed value", color=TEXT_SECONDARY, size=10),
            False, False, 0,
        )

        # Read current fan curve temps from EC (6 temp thresholds)
        self._cpu_temps = [safe_read_byte(ec, a) for a in model.cpu_fan_curve_temp_addrs]
        self._cpu_speeds = [safe_read_byte(ec, a) for a in model.cpu_fan_curve_speed_addrs]
        if model.has_gpu:
            self._gpu_temps = [safe_read_byte(ec, a) for a in model.gpu_fan_curve_temp_addrs]
            self._gpu_speeds = [safe_read_byte(ec, a) for a in model.gpu_fan_curve_speed_addrs]

        self.curve_editor = FanCurveEditor(
            color=CPU_COLOR,
            temps=self._cpu_temps,
            speeds=self._cpu_speeds,
            on_speed_changed=self._on_cpu_speed_changed,
        )
        # Only enabled for "advanced" profile
        is_adv = user_cfg.get("profile", "auto") == "advanced"
        self.curve_editor.set_enabled(is_adv and not ec.is_read_only)
        curve_card.pack_start(self.curve_editor, True, True, 0)
        self.pack_start(curve_card, True, True, 0)

        # --- Compact temperature history graph ---
        temp_lines = [{'color': CPU_COLOR, 'label': 'CPU', 'dashed': False}]
        if model.has_gpu:
            temp_lines.append({'color': GPU_COLOR, 'label': 'GPU', 'dashed': False})
        self.temp_graph = RollingGraph(
            lines=temp_lines, y_min=25, y_max=100, y_label="°C"
        )
        self.temp_graph.set_size_request(-1, 100)
        temp_card = make_card()
        temp_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        temp_header.pack_start(make_label("Temperature History", size=12, bold=True), False, False, 0)
        self._temp_legend = make_label("", size=10)
        self._temp_legend.set_halign(Gtk.Align.END)
        temp_header.pack_end(self._temp_legend, False, False, 0)
        temp_card.pack_start(temp_header, False, False, 0)
        temp_card.pack_start(self.temp_graph, True, True, 0)
        self.pack_start(temp_card, False, False, 0)

    def update(self, ec):
        """Called every 500ms to update live temp display."""
        cpu_temp = safe_read_byte(ec, self.model.cpu_temp_addr)
        self.temp_graph.add_point(0, cpu_temp)
        self.curve_editor.set_current_temp(cpu_temp)

        legend_parts = [f'<span foreground="{CPU_COLOR}">CPU {cpu_temp}°C</span>']

        if self.model.has_gpu:
            gpu_temp = safe_read_byte(ec, self.model.gpu_temp_addr)
            self.temp_graph.add_point(1, gpu_temp)
            legend_parts.append(f'<span foreground="{GPU_COLOR}">GPU {gpu_temp}°C</span>')

        self._temp_legend.set_markup("  ".join(legend_parts))
        self.temp_graph.queue_draw()

    def _update_profile_buttons(self, active_name):
        """Highlight the active profile button."""
        for name, btn in self._profile_buttons.items():
            ctx = btn.get_style_context()
            if name == active_name:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

    def _on_profile_clicked(self, button, profile_name):
        if self.ec.is_read_only:
            return
        apply_profile(self.ec, self.model, self.user_cfg, profile_name)
        self._update_profile_buttons(profile_name)

        is_adv = profile_name == "advanced"
        self.curve_editor.set_enabled(is_adv)

        if self.on_profile_changed:
            self.on_profile_changed(profile_name)

    def _on_boost_clicked(self, button):
        if self.ec.is_read_only:
            return
        # Toggle cooler boost
        current = self.ec.read_byte(self.model.cooler_boost_addr)
        is_active = bool(current & (1 << self.model.cooler_boost_bit))

        if is_active:
            # Disable boost
            self.ec.write_byte(
                self.model.cooler_boost_addr,
                current & ~(1 << self.model.cooler_boost_bit)
            )
            self._boost_button.get_style_context().remove_class("active")
        else:
            # Enable boost
            self.ec.write_byte(
                self.model.cooler_boost_addr,
                current | (1 << self.model.cooler_boost_bit)
            )
            self._boost_button.get_style_context().add_class("active")

    def _on_curve_tab(self, button, which):
        """Switch between CPU and GPU fan curves."""
        self._active_curve = which
        if which == "cpu":
            self.curve_editor.set_temps(self._cpu_temps)
            self.curve_editor.set_curve(self._cpu_speeds)
            self.curve_editor.color = CPU_COLOR
            self.curve_editor.rgba = (0xFF/255, 0x46/255, 0x55/255, 1.0)
            self.curve_editor.on_speed_changed = self._on_cpu_speed_changed
            self._cpu_tab.get_style_context().add_class("active")
            self._gpu_tab.get_style_context().remove_class("active")
        else:
            self.curve_editor.set_temps(self._gpu_temps)
            self.curve_editor.set_curve(self._gpu_speeds)
            self.curve_editor.color = GPU_COLOR
            self.curve_editor.rgba = (0x00/255, 0xD4/255, 0xFF/255, 1.0)
            self.curve_editor.on_speed_changed = self._on_gpu_speed_changed
            self._gpu_tab.get_style_context().add_class("active")
            self._cpu_tab.get_style_context().remove_class("active")

    def _on_cpu_speed_changed(self, index, new_speed):
        """Write updated CPU fan speed to EC."""
        self._cpu_speeds[index] = new_speed
        self.ec.write_byte(self.model.cpu_fan_curve_speed_addrs[index], new_speed)

    def _on_gpu_speed_changed(self, index, new_speed):
        """Write updated GPU fan speed to EC."""
        self._gpu_speeds[index] = new_speed
        self.ec.write_byte(self.model.gpu_fan_curve_speed_addrs[index], new_speed)
```

- [ ] **Step 2: Verify import**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "
import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk
from ui.fan_control import FanControlPage
print('fan_control OK')
"
```

Expected: `fan_control OK`

- [ ] **Step 3: Commit**

```bash
git add ui/fan_control.py
git commit -m "feat(ui): add Fan Control page with profile buttons and curve editor"
```

---

### Task 7: Create `ui/battery.py`

**Files:**
- Create: `ui/battery.py`

- [ ] **Step 1: Create `ui/battery.py`**

```python
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
```

- [ ] **Step 2: Verify import**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "
import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk
from ui.battery import BatteryPage
print('battery OK')
"
```

Expected: `battery OK`

- [ ] **Step 3: Commit**

```bash
git add ui/battery.py
git commit -m "feat(ui): add Battery page with threshold buttons and Cairo icon"
```

---

### Task 8: Create `ui/settings.py`

**Files:**
- Create: `ui/settings.py`

- [ ] **Step 1: Create `ui/settings.py`**

```python
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
```

- [ ] **Step 2: Verify import**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 -c "
import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk
from ui.settings import SettingsPage
print('settings OK')
"
```

Expected: `settings OK`

- [ ] **Step 3: Commit**

```bash
git add ui/settings.py
git commit -m "feat(ui): add Settings page with system info and options"
```

---

### Task 9: Rewrite `OFC.py` — thin entry point

**Files:**
- Rewrite: `OFC.py`

This replaces the entire current `OFC.py` with a thin entry point that wires backend to UI.

- [ ] **Step 1: Rewrite `OFC.py`**

```python
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
```

- [ ] **Step 2: Run the app to verify it launches**

Run:
```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 OFC.py
```

Expected: Window opens with sidebar (Dashboard/Fan Control/Battery/Settings), Dashboard shows live CPU/GPU temps and graphs updating every 500ms. Close the window — should exit cleanly.

- [ ] **Step 3: Verify sidebar navigation works**

Click each sidebar button — Dashboard, Fan Control, Battery, Settings. Each page should render without errors.

- [ ] **Step 4: Verify fan curve editor works**

Navigate to Fan Control → click "Advanced" profile → click a curve point → popover appears → change speed value → close popover → point moves on graph.

- [ ] **Step 5: Verify battery threshold works**

Navigate to Battery → click a threshold button (e.g., 80%) → percentage updates, button highlights.

- [ ] **Step 6: Commit**

```bash
git add OFC.py
git commit -m "feat: rewrite OFC.py as thin entry point with sidebar navigation"
```

---

### Task 10: Update `install.sh` to copy `ui/` directory

**Files:**
- Modify: `install.sh:55-63`

- [ ] **Step 1: Add the `ui/` directory to install.sh**

After the existing `mkdir -p "$INSTALL_DIR/models"` line, add the ui directory creation and copy:

Find and replace in `install.sh` — change:

```bash
mkdir -p "$INSTALL_DIR/models"

cp "$SCRIPT_DIR/OFC.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ec_access.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/model_config.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/models/database.json" "$INSTALL_DIR/models/"
```

To:

```bash
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$INSTALL_DIR/ui"

cp "$SCRIPT_DIR/OFC.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ec_access.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/model_config.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/models/database.json" "$INSTALL_DIR/models/"
cp "$SCRIPT_DIR"/ui/*.py "$INSTALL_DIR/ui/"
```

- [ ] **Step 2: Verify the install script syntax**

Run:
```bash
bash -n /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite/install.sh && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "fix: update install.sh to include ui/ package"
```

---

### Task 11: Final integration test

- [ ] **Step 1: Run the full application**

```bash
cd /run/media/sriram/Sriram/Programming/OpenFreezeCenter-Bazzite && sudo python3 OFC.py
```

**Verify all of the following:**

1. Window opens at 900x550 with dark theme
2. Sidebar shows: Dashboard, Fan Control, Battery (if supported), Settings
3. Profile indicator at bottom of sidebar shows current profile
4. **Dashboard**: CPU/GPU stat cards with live temps, two rolling graphs updating
5. **Fan Control**: Profile buttons, fan curve editor (enabled only in Advanced), compact temp graph
6. **Battery**: Threshold buttons, battery icon, clicking changes threshold
7. **Settings**: System info populated correctly, read-only toggle shown
8. Window is resizable — graphs stretch proportionally, no overflow
9. Close window — exits cleanly with no errors

- [ ] **Step 2: Test no-GPU behavior**

This can be verified by reading the code paths — if `model.has_gpu is False`:
- No GPU stat card on Dashboard
- No GPU lines on graphs
- No GPU tab on fan curve editor
- Single-fan display

- [ ] **Step 3: Commit all remaining changes**

```bash
git add -A
git status
git commit -m "feat: complete UI overhaul with sidebar nav, Cairo graphs, fan curve editor"
```
