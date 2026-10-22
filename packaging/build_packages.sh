#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"

VERSION=$(python3 -c "import sys; sys.path.insert(0, '$ROOT_DIR'); from version import __version__; print(__version__)")
echo "=== Building FrostCenter v$VERSION packages ==="
mkdir -p "$DIST_DIR"

# 1. Build Universal Standalone Archive (.tar.gz)
echo "[1/3] Building universal standalone archive: frostcenter-$VERSION.tar.gz ..."
TAR_DIR="$(mktemp -d)/frostcenter-$VERSION"
mkdir -p "$TAR_DIR/models" "$TAR_DIR/ui" "$TAR_DIR/assets" "$TAR_DIR/packaging"

cp "$ROOT_DIR/OFC.py" "$TAR_DIR/"
cp "$ROOT_DIR/ec_access.py" "$TAR_DIR/"
cp "$ROOT_DIR/model_config.py" "$TAR_DIR/"
cp "$ROOT_DIR/version.py" "$TAR_DIR/"
cp "$ROOT_DIR/install.sh" "$TAR_DIR/"
cp "$ROOT_DIR/LICENSE" "$TAR_DIR/"
cp "$ROOT_DIR/README.md" "$TAR_DIR/"
cp "$ROOT_DIR/CONTRIBUTING.md" "$TAR_DIR/"
cp "$ROOT_DIR/models/database.json" "$TAR_DIR/models/"
cp "$ROOT_DIR"/ui/*.py "$TAR_DIR/ui/"
cp "$ROOT_DIR"/assets/*.svg "$TAR_DIR/assets/" 2>/dev/null || true
cp -r "$ROOT_DIR/packaging"/* "$TAR_DIR/packaging/"

tar -czf "$DIST_DIR/frostcenter-$VERSION.tar.gz" -C "$(dirname "$TAR_DIR")" "frostcenter-$VERSION"
rm -rf "$(dirname "$TAR_DIR")"
echo "  -> Created $DIST_DIR/frostcenter-$VERSION.tar.gz"

# 2. Build Debian package (.deb)
if command -v dpkg-deb >/dev/null 2>&1; then
    echo "[2/3] Building Debian package: frostcenter_${VERSION}_all.deb ..."
    DEB_ROOT="$(mktemp -d)/frostcenter_${VERSION}_all"
    mkdir -p "$DEB_ROOT/DEBIAN"
    mkdir -p "$DEB_ROOT/usr/bin"
    mkdir -p "$DEB_ROOT/usr/share/frostcenter/models"
    mkdir -p "$DEB_ROOT/usr/share/frostcenter/ui"
    mkdir -p "$DEB_ROOT/usr/share/applications"
    mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps"
    mkdir -p "$DEB_ROOT/usr/share/polkit-1/actions"
    mkdir -p "$DEB_ROOT/usr/share/metainfo"

    # Control metadata
    cp "$ROOT_DIR/packaging/debian/control" "$DEB_ROOT/DEBIAN/"
    cp "$ROOT_DIR/packaging/debian/postinst" "$DEB_ROOT/DEBIAN/"
    cp "$ROOT_DIR/packaging/debian/postrm" "$DEB_ROOT/DEBIAN/"
    chmod 755 "$DEB_ROOT/DEBIAN/postinst" "$DEB_ROOT/DEBIAN/postrm"

    # Application files
    install -m 755 "$ROOT_DIR/packaging/frost" "$DEB_ROOT/usr/bin/frost"
    install -m 644 "$ROOT_DIR/OFC.py" "$DEB_ROOT/usr/share/frostcenter/"
    install -m 644 "$ROOT_DIR/ec_access.py" "$DEB_ROOT/usr/share/frostcenter/"
    install -m 644 "$ROOT_DIR/model_config.py" "$DEB_ROOT/usr/share/frostcenter/"
    install -m 644 "$ROOT_DIR/version.py" "$DEB_ROOT/usr/share/frostcenter/"
    install -m 644 "$ROOT_DIR/models/database.json" "$DEB_ROOT/usr/share/frostcenter/models/"
    install -m 644 "$ROOT_DIR"/ui/*.py "$DEB_ROOT/usr/share/frostcenter/ui/"

    # Desktop, icon, polkit, and appstream
    install -m 644 "$ROOT_DIR/packaging/io.github.gsriram24.frostcenter.desktop" "$DEB_ROOT/usr/share/applications/"
    if [ -f "$ROOT_DIR/assets/frostcenter.svg" ]; then
        install -m 644 "$ROOT_DIR/assets/frostcenter.svg" "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/"
    fi
    install -m 644 "$ROOT_DIR/packaging/polkit/io.github.gsriram24.frostcenter.policy" "$DEB_ROOT/usr/share/polkit-1/actions/"
    install -m 644 "$ROOT_DIR/packaging/metainfo/io.github.gsriram24.frostcenter.metainfo.xml" "$DEB_ROOT/usr/share/metainfo/"

    dpkg-deb --build "$DEB_ROOT" "$DIST_DIR/frostcenter_${VERSION}_all.deb"
    rm -rf "$(dirname "$DEB_ROOT")"
    echo "  -> Created $DIST_DIR/frostcenter_${VERSION}_all.deb"
else
    echo "[2/3] Skipping .deb: dpkg-deb not installed."
fi

# 3. Build RPM package (.rpm)
if command -v rpmbuild >/dev/null 2>&1; then
    echo "[3/3] Building RPM package: frostcenter-$VERSION-1.noarch.rpm ..."
    RPM_TOP="$(mktemp -d)/rpmbuild"
    mkdir -p "$RPM_TOP/BUILD" "$RPM_TOP/RPMS" "$RPM_TOP/SOURCES" "$RPM_TOP/SPECS" "$RPM_TOP/SRPMS"
    
    cp "$DIST_DIR/frostcenter-$VERSION.tar.gz" "$RPM_TOP/SOURCES/"
    cp "$ROOT_DIR/packaging/rpm/frostcenter.spec" "$RPM_TOP/SPECS/"

    rpmbuild --nodeps --define "_topdir $RPM_TOP" -bb "$RPM_TOP/SPECS/frostcenter.spec"
    cp "$RPM_TOP"/RPMS/noarch/*.rpm "$DIST_DIR/"
    rm -rf "$(dirname "$RPM_TOP")"
    echo "  -> Created $DIST_DIR/frostcenter-$VERSION-1.noarch.rpm"
else
    echo "[3/3] Skipping .rpm: rpmbuild not installed (handled by CI/RPM distros)."
fi

echo ""
echo "=== Build Complete! Packages in $DIST_DIR: ==="
ls -lh "$DIST_DIR"
