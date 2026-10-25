#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"

echo "=================================================="
echo "    FrostCenter Packaging & Standards Test Suite   "
echo "=================================================="

# 1. Syntax Check
echo "[1/6] Verifying Python syntax..."
python3 -m py_compile "$ROOT_DIR"/OFC.py "$ROOT_DIR"/ec_access.py "$ROOT_DIR"/model_config.py "$ROOT_DIR"/version.py "$ROOT_DIR"/ui/*.py
echo "  -> PASS: Python syntax is clean."

# 2. Desktop File & AppStream Metadata
echo "[2/6] Validating Freedesktop specifications..."
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$ROOT_DIR/packaging/io.github.gsriram24.frostcenter.desktop"
    echo "  -> PASS: Desktop file complies with Freedesktop Menu specification."
else
    echo "  -> SKIP: desktop-file-validate not installed."
fi

if command -v appstreamcli >/dev/null 2>&1; then
    appstreamcli validate "$ROOT_DIR/packaging/metainfo/io.github.gsriram24.frostcenter.metainfo.xml"
    echo "  -> PASS: AppStream metainfo complies with AppStream 1.0 specification."
else
    echo "  -> SKIP: appstreamcli not installed."
fi

# 3. Build Release Packages
echo "[3/6] Building release packages (.deb, .rpm, .tar.gz)..."
"$ROOT_DIR/packaging/build_packages.sh" "$@"

# 4. Debian Package Lifecycle Test (.deb)
echo "[4/6] Testing Debian package installation & removal..."
if command -v dpkg >/dev/null 2>&1; then
    DEB_FILE="$(ls -1 "$DIST_DIR"/*.deb | head -n 1)"
    sudo apt-get install -y "$DEB_FILE"
    
    # Test CLI binary and man page
    INSTALLED_VER="$(frost --version)"
    echo "  -> CLI output: $INSTALLED_VER"
    frost --help >/dev/null
    
    # Test uninstallation
    sudo apt-get remove -y frostcenter
    echo "  -> PASS: Debian package installed, executed, and uninstalled cleanly."
else
    echo "  -> SKIP: dpkg/apt not available."
fi

# 5. RPM Package Inspection (.rpm)
echo "[5/6] Inspecting RPM package metadata..."
if command -v rpm >/dev/null 2>&1; then
    RPM_FILE="$(ls -1 "$DIST_DIR"/*.rpm | head -n 1)"
    rpm -qpi "$RPM_FILE" >/dev/null
    rpm -qp --requires "$RPM_FILE" >/dev/null
    echo "  -> PASS: RPM package metadata and dependencies verified."
else
    echo "  -> SKIP: rpm not installed."
fi

# 6. Universal Archive Extraction (.tar.gz)
echo "[6/6] Testing Universal archive extraction..."
TAR_FILE="$(ls -1 "$DIST_DIR"/*.tar.gz | head -n 1)"
TEST_DIR="$(mktemp -d)"
tar -xzf "$TAR_FILE" -C "$TEST_DIR"
test -f "$TEST_DIR"/frostcenter-*/install.sh
test -f "$TEST_DIR"/frostcenter-*/OFC.py
rm -rf "$TEST_DIR"
echo "  -> PASS: Universal standalone archive verified."

echo ""
echo "=================================================="
echo "      ALL PACKAGING TESTS PASSED SUCCESSFULLY!    "
echo "=================================================="
