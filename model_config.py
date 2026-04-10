"""
MSI laptop model detection, EC register address resolution, and user config.

Auto-detects the MSI laptop model via DMI board_name, looks up EC register
addresses from the JSON database, and manages user runtime configuration.
"""

import json
import os


# Paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATABASE_PATH = os.path.join(_SCRIPT_DIR, "models", "database.json")
_USER_CONFIG_PATH = os.path.join(_SCRIPT_DIR, "user_config.json")
_DMI_BOARD_NAME = "/sys/class/dmi/id/board_name"
_DMI_SYS_VENDOR = "/sys/class/dmi/id/sys_vendor"
_DMI_PRODUCT_NAME = "/sys/class/dmi/id/product_name"


def _read_dmi(path):
    """Read a DMI sysfs file, return stripped string or None."""
    try:
        with open(path) as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError):
        return None


def _parse_hex(value):
    """Parse a hex string like '0xef' to int. Pass through ints and None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return int(value, 16)


def _parse_hex_list(values):
    """Parse a list of hex strings to a list of ints."""
    return [_parse_hex(v) for v in values]


def _parse_hex_dict(d):
    """Parse a dict with hex string values to int values."""
    return {k: _parse_hex(v) for k, v in d.items()}


class ModelConfig:
    """Resolved EC register configuration for the detected MSI laptop model.

    Attributes:
        board_name: DMI board name (e.g., "MS-16W2")
        model_name: Human-readable model name (e.g., "GF65 Thin 10UE")
        group: Config group ID (e.g., "G1_7")
        has_gpu: Whether the model has a dedicated GPU

        # Common addresses (same for all MSI models)
        cpu_temp_addr: EC register for CPU temperature
        gpu_temp_addr: EC register for GPU temperature (None if no GPU)
        cpu_fan_speed_pct_addr: EC register for CPU fan speed %
        gpu_fan_speed_pct_addr: EC register for GPU fan speed % (None if no GPU)
        cpu_fan_curve_speed_addrs: List of 7 EC registers for CPU fan curve speeds
        gpu_fan_curve_speed_addrs: List of 7 EC registers for GPU fan curve speeds
        cpu_fan_curve_temp_addrs: List of 6 EC registers for CPU fan curve temps
        gpu_fan_curve_temp_addrs: List of 6 EC registers for GPU fan curve temps
        cooler_boost_addr: EC register for cooler boost toggle
        cooler_boost_bit: Bit number within cooler boost register

        # Per-group addresses (vary between model generations)
        fan_mode_addr: EC register for fan mode control
        fan_modes: Dict mapping mode name to EC value (e.g., {"auto": 0x0d})
        battery_threshold_addr: EC register for battery charge limit (None if unsupported)
        cpu_fan_rpm_addr: EC register for CPU fan RPM (2 bytes)
        gpu_fan_rpm_addr: EC register for GPU fan RPM (None if no GPU)
        rpm_divisor: Divisor for RPM calculation (RPM = divisor / raw_value)

        # Optional
        default_fan_curve: Dict with default fan curve data, or None
    """

    def __init__(self, database_path=None, board_override=None):
        """Detect model and resolve EC addresses.

        Args:
            database_path: Path to database.json (default: models/database.json)
            board_override: Force a specific board name instead of auto-detecting
        """
        db_path = database_path or _DATABASE_PATH
        with open(db_path) as f:
            db = json.load(f)

        # Detect or override board name
        if board_override:
            self.board_name = board_override
        else:
            self.board_name = _read_dmi(_DMI_BOARD_NAME)

        if not self.board_name:
            raise RuntimeError(
                "Could not read board name from DMI. "
                "Specify board_override manually."
            )

        # Look up board in database
        board_entry = db["boards"].get(self.board_name)
        if not board_entry:
            available = sorted(db["boards"].keys())
            raise ModelNotFoundError(self.board_name, available, db)

        self.model_name = board_entry["name"]
        self.group = board_entry["group"]

        # Look up group configuration
        group_conf = db["groups"].get(self.group)
        if not group_conf:
            raise RuntimeError(
                f"Config group '{self.group}' for board '{self.board_name}' "
                f"not found in database."
            )

        self.has_gpu = group_conf.get("has_gpu", True)

        # Resolve common addresses
        common = db["_common"]
        self.cpu_temp_addr = _parse_hex(common["cpu_temp"])
        self.gpu_temp_addr = _parse_hex(common["gpu_temp"]) if self.has_gpu else None
        self.cpu_fan_speed_pct_addr = _parse_hex(common["cpu_fan_speed_pct"])
        self.gpu_fan_speed_pct_addr = _parse_hex(common["gpu_fan_speed_pct"]) if self.has_gpu else None
        self.cpu_fan_curve_speed_addrs = _parse_hex_list(common["cpu_fan_curve_speeds"])
        self.gpu_fan_curve_speed_addrs = _parse_hex_list(common["gpu_fan_curve_speeds"]) if self.has_gpu else None
        self.cpu_fan_curve_temp_addrs = _parse_hex_list(common["cpu_fan_curve_temps"])
        self.gpu_fan_curve_temp_addrs = _parse_hex_list(common["gpu_fan_curve_temps"]) if self.has_gpu else None
        self.cooler_boost_addr = _parse_hex(common["cooler_boost_addr"])
        self.cooler_boost_bit = common["cooler_boost_bit"]

        # Resolve per-group addresses
        self.fan_mode_addr = _parse_hex(group_conf["fan_mode_addr"])
        self.fan_modes = _parse_hex_dict(group_conf["fan_modes"])
        self.battery_threshold_addr = _parse_hex(group_conf.get("battery_threshold_addr"))
        self.cpu_fan_rpm_addr = _parse_hex(group_conf["cpu_fan_rpm_addr"])
        self.gpu_fan_rpm_addr = _parse_hex(group_conf["gpu_fan_rpm_addr"]) if self.has_gpu else None
        self.rpm_divisor = group_conf.get("rpm_divisor", 478000)

        # Load default fan curve if available
        fan_curves = db.get("default_fan_curves", {})
        self.default_fan_curve = fan_curves.get(self.board_name)

    def __repr__(self):
        return (
            f"ModelConfig(board={self.board_name!r}, model={self.model_name!r}, "
            f"group={self.group!r}, has_gpu={self.has_gpu})"
        )


class ModelNotFoundError(Exception):
    """Raised when the detected board is not in the database."""

    def __init__(self, board_name, available_boards, database):
        self.board_name = board_name
        self.available_boards = available_boards
        self.database = database
        super().__init__(
            f"Board '{board_name}' not found in database. "
            f"Known boards: {len(available_boards)}"
        )


def get_system_info():
    """Return a dict of DMI system info for display/debugging."""
    return {
        "board_name": _read_dmi(_DMI_BOARD_NAME),
        "sys_vendor": _read_dmi(_DMI_SYS_VENDOR),
        "product_name": _read_dmi(_DMI_PRODUCT_NAME),
    }


# --- User Config ---

_DEFAULT_USER_CONFIG = {
    "board_override": None,
    "profile": "auto",
    "auto_speed": [[0, 40, 48, 56, 64, 72, 80], [0, 48, 56, 64, 72, 79, 86]],
    "adv_speed": [[0, 40, 48, 56, 64, 72, 80], [0, 48, 56, 64, 72, 79, 86]],
    "basic_offset": 0,
    "battery_threshold": 100,
}


def load_user_config(path=None):
    """Load user config from JSON, creating defaults if missing."""
    config_path = path or _USER_CONFIG_PATH
    if os.path.exists(config_path):
        with open(config_path) as f:
            cfg = json.load(f)
        # Merge with defaults for any missing keys
        for key, default_val in _DEFAULT_USER_CONFIG.items():
            if key not in cfg:
                cfg[key] = default_val
        return cfg
    return dict(_DEFAULT_USER_CONFIG)


def save_user_config(config, path=None):
    """Save user config to JSON."""
    config_path = path or _USER_CONFIG_PATH
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
