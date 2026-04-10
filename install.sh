#!/bin/bash
set -e

# FrostCenter - Installer
# MSI laptop fan control for Linux via /dev/port (no kernel modules needed)

INSTALL_DIR="$HOME/.local/share/ofc"
BIN_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== FrostCenter ==="
echo ""

# Check for MSI laptop
VENDOR=$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || echo "unknown")
if ! echo "$VENDOR" | grep -qi "micro-star"; then
    echo "WARNING: This does not appear to be an MSI laptop."
    echo "  Vendor: $VENDOR"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Show detected model
BOARD=$(cat /sys/class/dmi/id/board_name 2>/dev/null || echo "unknown")
PRODUCT=$(cat /sys/class/dmi/id/product_name 2>/dev/null || echo "unknown")
echo "Detected: $PRODUCT ($BOARD)"

# Check /dev/port access
if [ ! -c /dev/port ]; then
    echo ""
    echo "ERROR: /dev/port not found."
    echo "This may happen if Secure Boot is enabled (kernel lockdown blocks port I/O)."
    echo "Check: cat /sys/kernel/security/lockdown"
    exit 1
fi

# Check Python3 + PyGObject
echo ""
echo "Checking dependencies..."
if python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" 2>/dev/null; then
    echo "  Python3 + PyGObject: OK"
else
    echo "  Python3 + PyGObject: NOT FOUND"
    echo ""
    echo "  Install PyGObject and GTK3 for your distro:"
    echo "    Fedora/Bazzite: sudo dnf install python3-gobject gtk3"
    echo "    Immutable:      rpm-ostree install python3-gobject gtk3 && reboot"
    echo "    Ubuntu/Debian:  sudo apt install python3-gi gir1.2-gtk-3.0"
    echo "    Arch:           sudo pacman -S python-gobject gtk3"
    exit 1
fi

# Install files
echo ""
echo "Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$INSTALL_DIR/ui"

cp "$SCRIPT_DIR/OFC.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ec_access.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/model_config.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/models/database.json" "$INSTALL_DIR/models/"
cp "$SCRIPT_DIR"/ui/*.py "$INSTALL_DIR/ui/"
if [ -f "$SCRIPT_DIR/LICENSE" ]; then
    cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/"
fi

echo "  Files copied."

# Create launcher script
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/frost" << 'LAUNCHER'
#!/bin/bash
# FrostCenter launcher (requires root for /dev/port access)
OFC_DIR="$HOME/.local/share/ofc"
exec sudo python3 "$OFC_DIR/OFC.py" "$@"
LAUNCHER
chmod +x "$BIN_DIR/frost"

echo "  Launcher created at $BIN_DIR/frost"

# Check if ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo ""
    echo "  NOTE: $BIN_DIR is not in your PATH."
    echo "  Add this to your ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "To run: frost"
echo "  (or: sudo python3 $INSTALL_DIR/OFC.py)"
echo ""
echo "Model: $PRODUCT ($BOARD)"
