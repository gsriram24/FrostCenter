# FrostCenter

MSI laptop fan control and thermal monitoring for Linux.

Dark-themed GTK3 app with real-time temperature graphs, interactive fan curve editor, and battery charge threshold control — no Windows required.

![Python](https://img.shields.io/badge/python-3.8+-blue)
![GTK](https://img.shields.io/badge/GTK-3.0-green)
![License](https://img.shields.io/badge/license-GPL--3.0-orange)

## Features

- **Dashboard** — Live CPU/GPU temperature and fan RPM with rolling 60-second graphs
- **Fan Control** — Switch between Auto, Silent, Basic, and Advanced profiles. Interactive fan curve editor for Advanced mode with click-to-edit control points
- **Cooler Boost** — One-click toggle for maximum fan speed
- **Battery Threshold** — Set charge limit (50–100%) to preserve battery health
- **130+ MSI models** — Auto-detects your laptop from the board name

## Requirements

- MSI laptop (see [Supported Models](#supported-models))
- Linux with `/dev/port` access (Secure Boot must be disabled or in permissive mode)
- Python 3.8+
- PyGObject + GTK3

## Installation

```bash
git clone https://github.com/gsriram24/FrostCenter.git
cd FrostCenter
chmod +x install.sh
./install.sh
```

The installer checks dependencies and copies files to `~/.local/share/ofc/`. It creates a `frost` launcher in `~/.local/bin/`.

### Installing dependencies

If PyGObject/GTK3 isn't installed:

| Distro | Command |
|--------|---------|
| Fedora | `sudo dnf install python3-gobject gtk3` |
| Bazzite/Immutable | `rpm-ostree install python3-gobject gtk3` then reboot |
| Ubuntu/Debian | `sudo apt install python3-gi gir1.2-gtk-3.0` |
| Arch | `sudo pacman -S python-gobject gtk3` |

## Usage

```bash
frost
# or directly:
sudo python3 OFC.py
```

Root access is required for EC register access via `/dev/port`.

### Read-only mode

To monitor temperatures and fan speeds without writing to the EC:

```bash
frost --read-only
```

You can also toggle read-only mode live from the Settings page. When enabled, all profile buttons, fan curve editing, cooler boost, and battery threshold controls are disabled.

### Secure Boot / Kernel Lockdown

FrostCenter requires access to `/dev/port`, which is blocked when kernel lockdown is active (typically due to Secure Boot). Check your status:

```bash
cat /sys/kernel/security/lockdown
```

If it shows `[integrity]` or `[confidentiality]`, you need to disable Secure Boot in your BIOS settings. If it shows `[none]`, you're good to go. The app will show a clear error dialog if access is blocked.

## Supported Models

Auto-detection reads `/sys/class/dmi/id/board_name` and looks it up in the built-in database. **130+ MSI boards** are supported across 21 configuration groups:

| Family | Examples |
|--------|----------|
| GF series | GF63, GF65 Thin, GF75 Thin |
| GL series | GL62M, GL63, GL65, GL73, GL75 |
| GE series | GE62, GE63, GE66, GE72, GE75, GE76 Raider |
| GP series | GP62, GP63, GP65, GP66, GP73, GP75, GP76 Leopard |
| GS series | GS40, GS43, GS63, GS65, GS66, GS73, GS75 Stealth |
| GT series | GT62, GT72 Dominator, GT75 |
| Modern | Modern 14/15 A10, B10, B13, H |
| Prestige | Prestige 13/14/15/16 Evo |
| Creator | Creator 15/16/17 |
| Katana/Cyborg | Katana GF66, Cyborg 15 |
| Vector/Crosshair | Vector GP66/76, Crosshair 15/16/17 HX |
| Stealth/Titan | Stealth 14/16 Studio, Titan 18 HX |
| Summit | Summit E13/E16 Flip |
| Alpha/Bravo | Alpha 15/17, Bravo 15/17 |

If your model isn't detected, run `cat /sys/class/dmi/id/board_name` and open an issue with the output.

## How It Works

FrostCenter communicates with the laptop's Embedded Controller (EC) through `/dev/port` using the ACPI EC protocol (ports `0x62` data, `0x66` command/status). This is the same interface that MSI's Windows tools use — no custom kernel modules required.

## Project Structure

```
OFC.py              Entry point — window, sidebar, page switching
ec_access.py        EC read/write via /dev/port
model_config.py     Auto-detection, JSON database loading, user config
models/database.json  130+ MSI board definitions
ui/
  theme.py          Color palette, CSS, widget helpers
  helpers.py        EC helper functions (safe reads, profile switching)
  widgets.py        RollingGraph, StatCard (Cairo-drawn)
  fan_curve_editor.py  Interactive fan curve with click-to-edit popovers
  dashboard.py      Dashboard page
  fan_control.py    Fan control page
  battery.py        Battery threshold page
  settings.py       Settings page
```

## Tested On

| Device | OS | Status |
|--------|----|--------|
| MSI GF65 Thin 10UE (MS-16W2) | Bazzite 6.17.7 (Fedora Atomic) | Working |

If you've tested FrostCenter on your setup, feel free to open a PR adding your device to this table.

## Disclaimer

**FrostCenter writes directly to your laptop's Embedded Controller (EC) registers.** While the addresses and values used are based on well-documented open-source projects (msi-ec, isw) and match what MSI's own Windows tools do, **incorrect EC writes can potentially cause hardware damage, system instability, or void your warranty.**

- **Use at your own risk.** The authors are not responsible for any damage to your hardware.
- **Back up your current EC state** by noting your fan speeds and battery threshold before making changes.
- **Start with read-only mode** (Settings page) on untested models to verify temperature/RPM readings are correct before enabling writes.
- If your model is not in the database, do **not** manually force a different model's config group — the register addresses may differ.

## Credits

Built on data from:
- [msi-ec](https://github.com/BeardOverflow/msi-ec) — Linux kernel module for MSI EC (config groups and board mappings)
- [isw](https://github.com/YoyPa/isw) — MSI fan control tool (default fan curves)
- [OpenFreezeCenter](https://github.com/YoCodingMonster/OpenFreezeCenter) — Original project by YoCodingMonster

## License

GPL-3.0
