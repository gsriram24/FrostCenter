# OpenFreezeCenter UI Overhaul — Design Spec

## Overview

Redesign the OFC GUI from a minimal GTK3 fixed-layout window into a polished, Dragon Center-inspired application with sidebar navigation, real-time graphs, an interactive fan curve editor, and themed dark styling.

**Constraints:**
- GTK3 + Cairo only (no matplotlib, no web tech)
- PyGObject must be the only GUI dependency (pre-installed on Bazzite)
- Backend files untouched: `ec_access.py`, `model_config.py`, `models/database.json`
- Must handle models with and without GPU, with and without battery threshold support

## Visual Direction

**Hybrid: clean system-monitor layout with gaming accent colors and subtle glow effects.**

### Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Background (main) | Dark navy | `#12121e` |
| Background (cards) | Dark slate | `#1a1a2e` |
| Background (elevated) | Mid slate | `#2d2d44` |
| Border | Subtle | `#2d2d44` |
| Text primary | Light grey | `#cccccc` |
| Text secondary | Mid grey | `#888888` |
| Text muted | Dark grey | `#666666` |
| CPU accent | Red | `#ff4655` |
| GPU accent | Cyan | `#00d4ff` |
| Warning/Battery | Orange | `#ff8c00` |
| Success | Green | `#00e57a` |

### Typography & Effects
- System font (GTK default), weights via CSS
- Large temperature numbers (equivalent to ~36px) with colored text-shadow glow
- Small labels in uppercase with letter-spacing for section headers
- Card borders with 10px border-radius
- Subtle gradient fills under graph lines

## Layout Architecture

### Window Structure

```
+----------------------------------------------------------+
|  [Sidebar 160px]  |  [Content Area - fills remaining]    |
|                    |                                      |
|  Dashboard         |  (active page content)               |
|  Fan Control       |                                      |
|  Battery *         |                                      |
|  Settings          |                                      |
|                    |                                      |
|  [Profile: Auto]   |                                      |
+----------------------------------------------------------+
```

* Battery page hidden if `model.battery_threshold_addr is None`

**GTK implementation:**
- `Gtk.Box(orientation=HORIZONTAL)` as main container
- Sidebar: `Gtk.Box(orientation=VERTICAL)` with fixed width (160px via `set_size_request`)
- Content: `Gtk.Stack` with `Gtk.StackSidebar`-style custom sidebar buttons
- Profile selector: sits at bottom of sidebar, always visible regardless of active page

**Fluid resizing:**
- Sidebar: fixed 160px width
- Content area: `expand=True, fill=True` — takes all remaining space
- Stat cards: `Gtk.Box(homogeneous=True)` — equal width
- All graphs: `Gtk.DrawingArea` with Cairo, coordinates computed as ratios of allocated width/height in `draw` handler
- Fan curve points: positioned as percentage of drawing area dimensions
- Window default size: 900x550, minimum size: 700x450

## Page Designs

### 1. Dashboard Page

**Purpose:** At-a-glance monitoring of all thermal data.

**Components (top to bottom):**

1. **Stat cards row** — two cards side by side (CPU, GPU)
   - Each card shows:
     - Label ("CPU" / "GPU") in accent color, uppercase, small
     - Min/Max in muted accent color, top-right
     - Current temperature: large number with accent glow
     - Fan RPM: bottom row, label + value
   - GPU card hidden if `model.has_gpu is False`
   - If no GPU: single CPU card spans full width

2. **Temperature history graph** — rolling 60-second line chart
   - `Gtk.DrawingArea` with Cairo drawing
   - CPU: solid red line with gradient fill below
   - GPU: solid cyan line with gradient fill below (hidden if no GPU)
   - Y-axis: 25°C to 100°C (auto-scales if readings exceed)
   - X-axis: last 60 seconds, grid lines every 15 seconds
   - Legend in top-right corner
   - Data stored as `collections.deque(maxlen=120)` (one reading per 500ms poll)

3. **Fan RPM history graph** — rolling 60-second line chart
   - Same structure as temp graph
   - Dashed lines to visually differentiate from temp graph
   - Y-axis: 0 to 6000 RPM (auto-scales)
   - CPU red dashed, GPU cyan dashed

### 2. Fan Control Page

**Purpose:** Select fan profiles and customize fan curves.

**Components (top to bottom):**

1. **Profile toggle buttons** — horizontal row of buttons
   - One button per available fan mode from `model.fan_modes` + "Cooler Boost"
   - Active profile highlighted with accent border + background tint
   - Cooler Boost is a separate toggle (not mutually exclusive with profiles) — rendered as an orange toggle button to the right, visually separated. When active, it overrides fan speeds regardless of selected profile.
   - Clicking a profile button: calls `fan_profile()`, updates EC, saves to `user_config.json`
   - Only "Advanced" profile enables the curve editor below

2. **Fan curve editor** — interactive graph
   - `Gtk.DrawingArea` with Cairo + mouse event handling
   - CPU/GPU tab buttons (top-right of card) — switches which curve is shown
   - Graph: X-axis = temperature (°C), Y-axis = fan speed (%)
   - 7 control points connected by lines, gradient fill below
   - Points rendered as circles (hollow when idle, filled when hovered/selected)
   - **Click a point** → popover appears with:
     - "Point N" label
     - Temperature display (°C) — read-only, set by EC's 6 temp threshold registers
     - Speed input field (%) — editable via `Gtk.SpinButton` (range 0-150)
     - Value applies on Enter key or focus-out (no Apply button)
     - Popover closes on click-outside or Escape
   - **"Now" indicator**: dashed vertical line at current temperature, labeled at bottom
   - Disabled (greyed out) when profile is not "Advanced"

3. **Temperature history graph** — compact version of Dashboard's temp graph
   - Smaller height, provides context while tuning curves
   - Shows current temp values in legend

### 3. Battery Page

**Purpose:** Configure battery charge threshold.

**Visibility:** Entire page (and sidebar entry) hidden if `model.battery_threshold_addr is None`.

**Components:**

1. **Charge threshold card**
   - Header: "Charge Threshold" + description text
   - Visual battery icon with fill level matching current threshold
   - Large percentage display in orange accent
   - Threshold selector: clickable buttons for 50%, 60%, 70%, 80%, 90%, 100%
   - Active threshold highlighted in orange
   - Clicking writes to EC immediately via `ec.write_byte(model.battery_threshold_addr, value + 128)`

2. **Info card**
   - Bullet points explaining battery health benefits
   - Orange bullet markers

### 4. Settings Page

**Purpose:** System info and configuration options.

**Components:**

1. **System information card**
   - Grid layout: label (grey) + value (white)
   - Fields: Model name, Board name, Config group, EC access method, Available fan modes, GPU status, Battery control status
   - All auto-populated from `ModelConfig`

2. **Options card**
   - Read-only mode toggle (switch widget)
     - When enabled: disables all EC writes, shows "[READ-ONLY]" in window title
     - Requires app restart to take effect (or could toggle `ec._read_only` live)
   - Update interval display (currently fixed at 500ms, shown as info)

3. **About card**
   - App name, description, model count ("130+ MSI models supported")

## File Structure

```
OFC.py                  # Entry point: window, sidebar, page switching, EC init
ui/
  __init__.py           # Package init
  theme.py              # Color constants, CSS provider setup, style helpers
  widgets.py            # Reusable widgets: RollingGraph, StatCard, FanCurveGraph
  dashboard.py          # Dashboard page (Gtk.Box subclass)
  fan_control.py        # Fan control page (Gtk.Box subclass)
  battery.py            # Battery page (Gtk.Box subclass)
  settings.py           # Settings page (Gtk.Box subclass)
```

### File Responsibilities

**`OFC.py`** (~120 lines)
- Parse args, init `ModelConfig`, `ECAccess`, load `user_config`
- Create main `Gtk.Window`, set dark CSS theme
- Build sidebar with navigation buttons + profile selector
- Create `Gtk.Stack` with page instances
- Start `GLib.timeout_add(500, update_callback)` that calls `page.update()` on each page
- Handle cleanup on destroy

**`ui/theme.py`** (~80 lines)
- Color constants (all hex values from palette above)
- `apply_theme(window)` — loads CSS provider with dark background, card styles, font sizes
- Helper: `make_label(text, color, size)` — creates a styled `Gtk.Label`
- Helper: `make_card_box()` — creates a styled `Gtk.Box` with card appearance

**`ui/widgets.py`** (~300 lines)
- `RollingGraph(Gtk.DrawingArea)` — reusable rolling line chart
  - Constructor: `RollingGraph(max_points=120, y_min=0, y_max=100, lines=[{color, dashed}])`
  - `add_point(line_index, value)` — appends value, triggers redraw
  - `do_draw(cr, width, height)` — Cairo rendering: axes, grid, lines, gradient fill, legend
- `StatCard(Gtk.Box)` — temperature + RPM display card
  - Constructor: `StatCard(label, color)`
  - `update(temp, min_temp, max_temp, rpm)`
- `FanCurveEditor(Gtk.DrawingArea)` — interactive fan curve graph
  - Constructor: `FanCurveEditor(color, on_speed_changed)`
  - `set_curve(speeds)` — set the 7 speed values
  - `set_current_temp(temp)` — update the "Now" indicator
  - Handles: `button-press-event` for point selection, popover display
  - Popover: `Gtk.Popover` with two `Gtk.SpinButton` inputs (temp, speed)
  - Values applied on popover close or Enter key

**`ui/dashboard.py`** (~100 lines)
- `DashboardPage(Gtk.Box)` containing:
  - Stat cards (CPU, optionally GPU)
  - Temperature `RollingGraph`
  - Fan RPM `RollingGraph`
- `update(ec, model)` method called every 500ms

**`ui/fan_control.py`** (~150 lines)
- `FanControlPage(Gtk.Box)` containing:
  - Profile toggle buttons row
  - `FanCurveEditor` with CPU/GPU tab switcher
  - Compact temperature `RollingGraph`
- `update(ec, model)` method for live temp updates
- Profile button click handlers that call `fan_profile()` and save config

**`ui/battery.py`** (~80 lines)
- `BatteryPage(Gtk.Box)` containing:
  - Battery icon (Cairo drawn), percentage display
  - Threshold button row
- Click handler writes to EC and saves config

**`ui/settings.py`** (~70 lines)
- `SettingsPage(Gtk.Box)` containing:
  - System info grid (populated from `ModelConfig`)
  - Read-only toggle
  - About section

## Data Flow

```
GLib.timeout (500ms)
  → OFC.py update_callback()
    → ec.read_byte(model.cpu_temp_addr) → cpu_temp
    → ec.read_word(model.cpu_fan_rpm_addr) → cpu_rpm
    → ec.read_byte(model.gpu_temp_addr) → gpu_temp (if has_gpu)
    → ec.read_word(model.gpu_fan_rpm_addr) → gpu_rpm (if has_gpu)
    → dashboard_page.update(cpu_temp, cpu_rpm, gpu_temp, gpu_rpm)
    → fan_control_page.update(cpu_temp, gpu_temp)
```

```
User clicks profile button (Fan Control page)
  → fan_control.py profile_clicked()
    → fan_profile(name, speeds) → ec.write_byte(...)
    → user_cfg["profile"] = name → save_user_config()
    → update sidebar profile indicator
```

```
User clicks fan curve point (Fan Control page)
  → FanCurveEditor button-press-event
    → show Gtk.Popover at point position
    → user edits speed value → Enter/focus-out
    → on_speed_changed callback
    → ec.write_byte(model.cpu_fan_curve_speed_addrs[i], value)
    → redraw curve
```

```
User clicks battery threshold (Battery page)
  → battery.py threshold_clicked()
    → ec.write_byte(model.battery_threshold_addr, value + 128)
    → user_cfg["battery_threshold"] = value → save_user_config()
    → update visual indicator
```

## Cairo Graph Rendering Details

### RollingGraph draw cycle

```python
def do_draw(self, cr, width, height):
    # 1. Clear background (card color)
    # 2. Draw Y-axis labels (text at fixed x, spaced by height)
    # 3. Draw horizontal grid lines (dashed, muted color)
    # 4. For each data line:
    #    a. Compute x,y for each point (x = ratio of width, y = ratio of height)
    #    b. Draw gradient fill (LinearGradient from line color @ 0.3 to transparent)
    #    c. Draw line (set_dash if dashed, stroke with line color)
    # 5. Draw legend (top-right)
    # 6. Draw X-axis time labels
```

### FanCurveEditor draw cycle

```python
def do_draw(self, cr, width, height):
    # 1. Clear background
    # 2. Draw axes and grid
    # 3. Draw gradient fill under curve
    # 4. Draw curve line connecting 7 points
    # 5. Draw control points:
    #    - Normal: hollow circle (stroke only)
    #    - Hovered: larger hollow circle
    #    - Selected: filled circle with outer glow
    # 6. Draw "Now" temperature indicator (dashed vertical line + label)
    # 7. If a point is selected, position Gtk.Popover near it
```

## Edge Cases

- **No GPU**: Hide GPU stat card, hide GPU lines on graphs, hide GPU tab in fan curve editor. Single-fan models show only CPU data.
- **No battery threshold**: Hide Battery page entirely and remove from sidebar.
- **EC timeout during read**: `safe_read_byte()` / `safe_read_rpm()` return last known value (or 0). Graph continues with stale data rather than gaps.
- **Window too small**: Minimum size 700x450 enforced. Graphs degrade gracefully (fewer grid lines, smaller labels).
- **Read-only mode**: Profile buttons and fan curve editor disabled (greyed out + tooltip). Battery buttons disabled. Monitoring still works.
- **Cooler Boost**: Separate from fan modes — it's a bit toggle on register 0x98. Can be active alongside any profile. Button turns orange when active.

## What's NOT in scope

- System tray / background daemon
- Auto-start on boot
- Custom theme switching (light mode)
- Exporting graph data
- Multiple fan curve presets/profiles (beyond the EC's built-in modes)
- Notification on thermal events
