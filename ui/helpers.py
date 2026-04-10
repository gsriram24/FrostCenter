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
