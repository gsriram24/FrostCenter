#!/usr/bin/python3

import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ec_access import ECAccess, ECAccessError, ECTimeoutError
from model_config import ModelConfig, ModelNotFoundError, load_user_config, save_user_config

# --- Phase 2: Full control ---
READ_ONLY = False

# --- Initialize model detection and EC access ---

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
print(f"  CPU temp: 0x{model.cpu_temp_addr:02x}, RPM: 0x{model.cpu_fan_rpm_addr:02x}")
if model.has_gpu:
    print(f"  GPU temp: 0x{model.gpu_temp_addr:02x}, RPM: 0x{model.gpu_fan_rpm_addr:02x}")
print(f"  Fan mode: 0x{model.fan_mode_addr:02x}, modes: {list(model.fan_modes.keys())}")
if model.battery_threshold_addr is not None:
    print(f"  Battery threshold: 0x{model.battery_threshold_addr:02x}")
print(f"  Read-only mode: {READ_ONLY}")

try:
    ec = ECAccess(read_only=READ_ONLY)
except ECAccessError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

user_cfg = load_user_config()

# --- Fan profile management (disabled in Phase 1) ---

BASIC_SPEED = [[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]]

def fan_profile(profile_name, speeds=None):
    """Write a fan profile to the EC. Disabled in read-only mode."""
    if READ_ONLY:
        return

    if profile_name == "cooler_booster":
        # Set cooler boost bit
        current = ec.read_byte(model.cooler_boost_addr)
        ec.write_byte(model.cooler_boost_addr, current | (1 << model.cooler_boost_bit))
    else:
        # Clear cooler boost bit first
        current = ec.read_byte(model.cooler_boost_addr)
        ec.write_byte(model.cooler_boost_addr, current & ~(1 << model.cooler_boost_bit))

        # Set fan mode
        mode_value = model.fan_modes.get(profile_name)
        if mode_value is not None:
            ec.write_byte(model.fan_mode_addr, mode_value)

        # Write fan curve speeds if provided
        if speeds and model.has_gpu:
            for i in range(7):
                ec.write_byte(model.cpu_fan_curve_speed_addrs[i], speeds[0][i])
                ec.write_byte(model.gpu_fan_curve_speed_addrs[i], speeds[1][i])
        elif speeds:
            for i in range(7):
                ec.write_byte(model.cpu_fan_curve_speed_addrs[i], speeds[0][i])


def speed_checker(speeds, offset):
    """Clamp fan speeds (with offset) to 0-150 range."""
    result = [row[:] for row in speeds]  # deep copy
    for row in range(len(result)):
        for col in range(7):
            val = result[row][col] + offset
            result[row][col] = max(0, min(150, val))
    return result


# --- GUI callbacks (profile/battery selectors disabled in Phase 1) ---

PROFILE_NAMES = list(model.fan_modes.keys()) + ["cooler_booster"]
# Map display names
PROFILE_DISPLAY = {
    "auto": "Auto",
    "silent": "Silent",
    "basic": "Basic",
    "advanced": "Advanced",
    "cooler_booster": "Cooler Booster",
}


def profile_selection(combobox):
    """Handle fan profile selection change."""
    if READ_ONLY:
        return

    combo_model = combobox.get_model()
    active_iter = combobox.get_active_iter()
    display_name = combo_model[active_iter][0]

    # Find internal name from display name
    profile_name = None
    for key, disp in PROFILE_DISPLAY.items():
        if disp == display_name:
            profile_name = key
            break

    if not profile_name:
        return

    user_cfg["profile"] = profile_name
    save_user_config(user_cfg)

    if profile_name == "auto":
        fan_profile("auto", speed_checker(user_cfg["auto_speed"], 0))
    elif profile_name == "basic":
        offset = max(-30, min(30, user_cfg["basic_offset"]))
        fan_profile("basic", speed_checker(BASIC_SPEED, offset))
    elif profile_name == "advanced":
        fan_profile("advanced", speed_checker(user_cfg["adv_speed"], 0))
    elif profile_name == "silent":
        fan_profile("silent")
    elif profile_name == "cooler_booster":
        fan_profile("cooler_booster")


def bct_selection(combobox):
    """Handle battery charge threshold selection change."""
    if READ_ONLY:
        return
    if model.battery_threshold_addr is None:
        return

    combo_model = combobox.get_model()
    active_iter = combobox.get_active_iter()
    threshold = int(combo_model[active_iter][0])
    user_cfg["battery_threshold"] = threshold
    ec.write_byte(model.battery_threshold_addr, threshold + 128)
    save_user_config(user_cfg)


# --- Temperature/RPM monitoring ---

MIN_MAX = [100, 0, 100, 0]  # [cpu_min, cpu_max, gpu_min, gpu_max]


def label_maker(text, x, y, offset, fixed):
    """Create a styled label and add it to the fixed container."""
    label = Gtk.Label()
    label.set_property("width-request", 80)
    label.set_property("height-request", 35)
    label.set_property("visible", True)
    label.set_property("can-focus", False)
    label.set_property("halign", Gtk.Align.CENTER)
    label.set_property("valign", Gtk.Align.CENTER)
    label.set_xalign(offset)
    label.set_property("margin-left", 0)
    label.set_property("margin-right", 10)
    label.set_label(text)
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data("""
    label {
        text-shadow: 0px 0px 10px rgba(0, 0, 0, 0.3);
    }
    """.encode())
    context = label.get_style_context()
    context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    fixed.put(label, x, y)
    fixed.add(label)


def safe_read_byte(addr):
    """Read a byte from EC, return 0 on error."""
    try:
        return ec.read_byte(addr)
    except ECTimeoutError:
        return 0


def safe_read_rpm(addr):
    """Read fan RPM from EC. Returns 0 if fan is stopped or on error."""
    try:
        raw = ec.read_word(addr)
        if raw == 0:
            return 0
        return model.rpm_divisor // raw
    except (ECTimeoutError, ZeroDivisionError):
        return 0


def update_label():
    """Periodic callback to update temperature and RPM displays."""
    CPU_TEMP = safe_read_byte(model.cpu_temp_addr)
    CPU_FAN_RPM = safe_read_rpm(model.cpu_fan_rpm_addr)

    parent_window.CPU_CURR_TEMP.set_text(str(CPU_TEMP))
    if MIN_MAX[0] > CPU_TEMP:
        MIN_MAX[0] = CPU_TEMP
    if MIN_MAX[1] < CPU_TEMP:
        MIN_MAX[1] = CPU_TEMP
    parent_window.CPU_MIN_TEMP.set_text(str(MIN_MAX[0]))
    parent_window.CPU_MAX_TEMP.set_text(str(MIN_MAX[1]))
    parent_window.CPU_FAN_RPM.set_text(str(CPU_FAN_RPM))

    if model.has_gpu:
        GPU_TEMP = safe_read_byte(model.gpu_temp_addr)
        GPU_FAN_RPM = safe_read_rpm(model.gpu_fan_rpm_addr)

        parent_window.GPU_CURR_TEMP.set_text(str(GPU_TEMP))
        if MIN_MAX[2] > GPU_TEMP:
            MIN_MAX[2] = GPU_TEMP
        if MIN_MAX[3] < GPU_TEMP:
            MIN_MAX[3] = GPU_TEMP
        parent_window.GPU_MIN_TEMP.set_text(str(MIN_MAX[2]))
        parent_window.GPU_MAX_TEMP.set_text(str(MIN_MAX[3]))
        parent_window.GPU_FAN_RPM.set_text(str(GPU_FAN_RPM))

    return True  # keep timer running


# --- Main GUI Window ---

def make_data_label(css_provider):
    """Create a styled data label for temperature/RPM values."""
    label = Gtk.Label()
    label.set_property("width-request", 80)
    label.set_property("height-request", 35)
    label.set_property("visible", True)
    label.set_property("can-focus", False)
    label.set_property("halign", Gtk.Align.CENTER)
    label.set_property("valign", Gtk.Align.CENTER)
    label.set_xalign(0.35)
    label.set_property("margin-left", 0)
    label.set_property("margin-right", 10)
    style = label.get_style_context()
    style.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return label


class ParentWindow(Gtk.Window):
    def __init__(self):
        mode_str = "[READ-ONLY] " if READ_ONLY else ""
        Gtk.Window.__init__(self, title=f"OFC {mode_str}- {model.model_name}")
        self.set_default_size(300, 190)
        fixed = Gtk.Fixed()
        self.add(fixed)

        # CSS for text shadow
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
        label {
            text-shadow: 0px 0px 10px rgba(0, 0, 0, 0.3);
        }
        """.encode())

        # --- Profile selector ---
        profile_selector = Gtk.ComboBox()
        profile_list = Gtk.ListStore(str)
        active_index = 0
        for i, name in enumerate(PROFILE_NAMES):
            display = PROFILE_DISPLAY.get(name, name.title())
            profile_list.append([display])
            if name == user_cfg.get("profile", "auto"):
                active_index = i
        profile_selector.set_model(profile_list)
        cell_renderer = Gtk.CellRendererText()
        profile_selector.pack_start(cell_renderer, True)
        profile_selector.add_attribute(cell_renderer, "text", 0)
        profile_selector.set_active(active_index)
        profile_selector.connect("changed", profile_selection)
        profile_selector.set_sensitive(not READ_ONLY)  # Disabled in read-only mode
        profile_selector.set_property("width-request", 80)
        profile_selector.set_property("height-request", 35)
        fixed.put(profile_selector, 160, 10)
        fixed.add(profile_selector)

        # --- Header labels ---
        label_maker("Select a fan profile", 10, 10, 0.0, fixed)
        label_maker("CURRENT", 60, 50, 0.0, fixed)
        label_maker("MIN", 140, 50, 0.0, fixed)
        label_maker("MAX", 190, 50, 0.0, fixed)
        label_maker("FAN RPM", 240, 50, 0.0, fixed)
        label_maker("CPU", 10, 80, 0.0, fixed)
        if model.has_gpu:
            label_maker("GPU", 10, 110, 0.0, fixed)

        # --- CPU data labels ---
        self.CPU_CURR_TEMP = make_data_label(css_provider)
        self.CPU_CURR_TEMP.set_label(str(safe_read_byte(model.cpu_temp_addr)))
        fixed.put(self.CPU_CURR_TEMP, 60, 80)
        fixed.add(self.CPU_CURR_TEMP)

        self.CPU_MIN_TEMP = make_data_label(css_provider)
        self.CPU_MIN_TEMP.set_xalign(0.05)
        fixed.put(self.CPU_MIN_TEMP, 140, 80)
        fixed.add(self.CPU_MIN_TEMP)

        self.CPU_MAX_TEMP = make_data_label(css_provider)
        self.CPU_MAX_TEMP.set_xalign(0.05)
        fixed.put(self.CPU_MAX_TEMP, 190, 80)
        fixed.add(self.CPU_MAX_TEMP)

        self.CPU_FAN_RPM = make_data_label(css_provider)
        self.CPU_FAN_RPM.set_xalign(0.3)
        self.CPU_FAN_RPM.set_label(str(safe_read_rpm(model.cpu_fan_rpm_addr)))
        fixed.put(self.CPU_FAN_RPM, 240, 80)
        fixed.add(self.CPU_FAN_RPM)

        # --- GPU data labels (only if model has GPU) ---
        if model.has_gpu:
            self.GPU_CURR_TEMP = make_data_label(css_provider)
            self.GPU_CURR_TEMP.set_label(str(safe_read_byte(model.gpu_temp_addr)))
            fixed.put(self.GPU_CURR_TEMP, 60, 110)
            fixed.add(self.GPU_CURR_TEMP)

            self.GPU_MIN_TEMP = make_data_label(css_provider)
            self.GPU_MIN_TEMP.set_xalign(0.05)
            fixed.put(self.GPU_MIN_TEMP, 140, 110)
            fixed.add(self.GPU_MIN_TEMP)

            self.GPU_MAX_TEMP = make_data_label(css_provider)
            self.GPU_MAX_TEMP.set_xalign(0.05)
            fixed.put(self.GPU_MAX_TEMP, 190, 110)
            fixed.add(self.GPU_MAX_TEMP)

            self.GPU_FAN_RPM = make_data_label(css_provider)
            self.GPU_FAN_RPM.set_xalign(0.3)
            self.GPU_FAN_RPM.set_label(str(safe_read_rpm(model.gpu_fan_rpm_addr)))
            fixed.put(self.GPU_FAN_RPM, 240, 110)
            fixed.add(self.GPU_FAN_RPM)

        # --- Timer for updates ---
        GLib.timeout_add(500, update_label)

        # --- Battery charge threshold selector ---
        bct_y = 110 if not model.has_gpu else 150
        if model.battery_threshold_addr is not None:
            label_maker("Battery charge threshold", 10, bct_y, 0.0, fixed)

            bct_selector = Gtk.ComboBox()
            bct_list = Gtk.ListStore(str)
            for val in range(50, 101, 5):
                bct_list.append([str(val)])
            bct_selector.set_model(bct_list)
            bct_renderer = Gtk.CellRendererText()
            bct_selector.pack_start(bct_renderer, True)
            bct_selector.add_attribute(bct_renderer, "text", 0)
            # Set active to match current config
            bct_model = bct_selector.get_model()
            for index, row in enumerate(bct_model):
                if row[0] == str(user_cfg.get("battery_threshold", 100)):
                    bct_selector.set_active(index)
                    break
            bct_selector.connect("changed", bct_selection)
            bct_selector.set_sensitive(not READ_ONLY)  # Disabled in read-only mode
            bct_selector.set_property("width-request", 80)
            bct_selector.set_property("height-request", 35)
            fixed.put(bct_selector, 200, bct_y)
            fixed.add(bct_selector)


parent_window = ParentWindow()
parent_window.connect("destroy", Gtk.main_quit)
parent_window.show_all()
Gtk.main()

# Cleanup
ec.close()
