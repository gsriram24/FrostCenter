# ui/helpers.py
"""Shared EC helper functions for fan control and monitoring."""

import os
import platform
import threading
import urllib.parse
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


# --- System Info & Community Helpers ---

def get_system_info():
    """Retrieve user OS distribution, kernel version, and desktop environment."""
    distro = "Linux"
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        distro = line.split('=', 1)[1].strip('"\n')
                        break
        elif os.name == 'nt':
            distro = f"Windows {platform.release()}"
    except Exception:
        pass
    kernel = platform.release()
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'Standard')
    return distro, kernel, desktop


def read_dmi_value(name):
    """Read a specific DMI value from sysfs, returning stripped string or 'Unknown'."""
    path = f"/sys/class/dmi/id/{name}"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return "Unknown"


def open_url_async(url):
    """Open a URL in the user's default browser asynchronously without blocking the UI."""
    def _open():
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening browser URL: {e}")
    threading.Thread(target=_open, daemon=True).start()


def copy_to_clipboard(text):
    """Copy text to the system clipboard via GTK if available."""
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, Gdk
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        return True
    except Exception:
        return False


def run_read_only_diagnostic():
    """Perform a safe, read-only ACPI EC probe across standard diagnostic registers."""
    try:
        fd = os.open('/dev/port', os.O_RDWR)
    except Exception as err:
        return (
            f"Note: Could not open /dev/port ({err}).\n"
            "To collect full EC registers, run FrostCenter with root privileges:\n"
            "  sudo python3 OFC.py"
        )
    try:
        EC_SC, EC_DATA = 0x66, 0x62
        def rp(p): return os.pread(fd, 1, p)[0]
        def wp(p, v): os.pwrite(fd, bytes([v]), p)
        def ibf():
            for _ in range(500):
                if not (rp(EC_SC) & 0x02): return
            raise TimeoutError('IBF timeout')
        def obf():
            for _ in range(500):
                if rp(EC_SC) & 0x01: return
            raise TimeoutError('OBF timeout')
        def rb(r):
            ibf(); wp(EC_SC, 0x80); ibf(); wp(EC_DATA, r); ibf(); obf(); return rp(EC_DATA)
        def rw(r): return (rb(r) << 8) | rb(r + 1)

        lines = [
            f"CPU temp (0x68):             {rb(0x68)} C",
            f"CPU fan % (0x71):            {rb(0x71)} %",
            f"CPU fan RPM raw (0xcc/0xcd): {rw(0xcc)}",
            f"GPU temp (0x80):             {rb(0x80)} C",
            f"GPU fan % (0x73):            {rb(0x73)} %",
            f"GPU fan RPM raw (0xc8/0xc9): {rw(0xc8)}",
            f"Fan mode (0xd2):             {hex(rb(0xd2))}",
            f"Fan mode (0xf4):             {hex(rb(0xf4))}",
            f"Cooler boost (0x98):         {hex(rb(0x98))}",
        ]
        return "\n".join(lines)
    except Exception as err:
        return f"Error reading EC registers: {err}"
    finally:
        try:
            os.close(fd)
        except Exception:
            pass


def build_verified_device_text(model):
    """Generate markdown verification text for a working laptop."""
    distro, kernel, desktop = get_system_info()
    battery_supported = getattr(model, 'battery_threshold_addr', None) is not None
    return f"""### Device Verification Report

- **Device / Model:** {model.model_name}
- **Board Name:** `{model.board_name}`
- **Config Group:** `{model.group}`
- **Operating System:** {distro}
- **Kernel:** {kernel}
- **Desktop Environment:** {desktop}

### Confirmed Functionality
- [x] Hardware identified and loaded correctly
- [x] Real-time CPU & GPU temperatures/fan speeds read accurately
- [x] Custom fan curve editing and profiles working
- [x] Cooler Boost toggle working
- [{"x" if battery_supported else " "}] Battery charge threshold limit

*Submitted via FrostCenter In-App Feedback*"""


def build_verified_device_url(model):
    """Build pre-filled GitHub issue URL for a verified working device."""
    title = f"Device Report: {model.model_name} ({model.board_name})"
    body = build_verified_device_text(model)
    params = urllib.parse.urlencode({"title": title, "body": body, "labels": "device-report"})
    return f"https://github.com/gsriram24/FrostCenter/issues/new?{params}"


def build_model_missing_url(board_name, product_name, diagnostic_text):
    """Build pre-filled GitHub issue URL for an unmapped model with diagnostic output."""
    distro, kernel, desktop = get_system_info()
    title = f"Model Missing: {product_name or 'MSI Laptop'} ({board_name})"
    body = f"""### MSI Board / Model Name
{board_name}

### Product Name
{product_name or 'Unknown'}

### Operating System
{distro} ({kernel})

### FrostCenter Version
latest

### EC Diagnostic Output
```shell
{diagnostic_text}
```

### Bug Description
Board `{board_name}` is not in FrostCenter database.

*Submitted via FrostCenter Diagnostic Reporter*"""
    params = urllib.parse.urlencode({"title": title, "body": body})
    return f"https://github.com/gsriram24/FrostCenter/issues/new?{params}"

