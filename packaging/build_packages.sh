#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"

# Allow VERSION to be passed as an argument or environment variable, fallback to version.py
VERSION="${1:-${VERSION:-$(python3 -c "import sys; sys.path.insert(0, '$ROOT_DIR'); from version import __version__; print(__version__)")}}"

if [ -z "$VERSION" ]; then
    echo "ERROR: Could not determine version string."
    exit 1
fi

echo "=== Building FrostCenter v$VERSION packages ==="
mkdir -p "$DIST_DIR"

# 1. Build Universal Standalone Archive (.tar.gz)
echo "[1/3] Building universal standalone archive: frostcenter-$VERSION.tar.gz ..."
TAR_DIR="$(mktemp -d)/frostcenter-$VERSION"
mkdir -p "$TAR_DIR/models" "$TAR_DIR/ui" "$TAR_DIR/assets" "$TAR_DIR/packaging"

cp "$ROOT_DIR/OFC.py" "$TAR_DIR/"
cp "$ROOT_DIR/ec_access.py" "$TAR_DIR/"
cp "$ROOT_DIR/model_config.py" "$TAR_DIR/"
cp "$ROOT_DIR/install.sh" "$TAR_DIR/"
cp "$ROOT_DIR/LICENSE" "$TAR_DIR/"
cp "$ROOT_DIR/README.md" "$TAR_DIR/"
cp "$ROOT_DIR/CONTRIBUTING.md" "$TAR_DIR/"
cp "$ROOT_DIR/models/database.json" "$TAR_DIR/models/"
cp "$ROOT_DIR"/ui/*.py "$TAR_DIR/ui/"
cp "$ROOT_DIR"/assets/*.svg "$TAR_DIR/assets/" 2>/dev/null || true
cp -r "$ROOT_DIR/packaging"/* "$TAR_DIR/packaging/"

# Stamp version.py in standalone archive
cat <<EOF > "$TAR_DIR/version.py"
"""FrostCenter version definition."""

__version__ = "$VERSION"
APP_NAME = "FrostCenter"
EOF

# Dynamically stamp manifests inside standalone archive
sed -i "s/^Version:.*/Version: $VERSION/" "$TAR_DIR/packaging/debian/control"
sed -i "s/^Version:.*/Version:        $VERSION/" "$TAR_DIR/packaging/rpm/frostcenter.spec"
sed -i "s/^pkgver=.*/pkgver=$VERSION/" "$TAR_DIR/packaging/arch/PKGBUILD"
sed -i "s/\"FrostCenter [0-9.]*\"/\"FrostCenter $VERSION\"/" "$TAR_DIR/packaging/frost.1"
if ! grep -q "version=\"$VERSION\"" "$TAR_DIR/packaging/metainfo/io.github.gsriram24.frostcenter.metainfo.xml"; then
    TODAY=$(date +%Y-%m-%d)
    sed -i "/<releases>/a \    <release version=\"$VERSION\" date=\"$TODAY\">\n      <description>\n        <p>FrostCenter release $VERSION.</p>\n      </description>\n    </release>" "$TAR_DIR/packaging/metainfo/io.github.gsriram24.frostcenter.metainfo.xml"
fi

# Sanitize line endings and file permissions
find "$TAR_DIR" -type f -exec sed -i 's/\r$//' {} +
find "$TAR_DIR" -type d -exec chmod 755 {} +
find "$TAR_DIR" -type f -exec chmod 644 {} +
chmod 755 "$TAR_DIR/install.sh" "$TAR_DIR/packaging/frost" "$TAR_DIR/packaging/build_packages.sh"

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
    mkdir -p "$DEB_ROOT/usr/share/doc/frostcenter"
    mkdir -p "$DEB_ROOT/usr/share/man/man1"

    # Control metadata - dynamically inject version
    cp "$ROOT_DIR/packaging/debian/control" "$DEB_ROOT/DEBIAN/"
    sed -i "s/^Version:.*/Version: $VERSION/" "$DEB_ROOT/DEBIAN/control"
    cp "$ROOT_DIR/packaging/debian/postinst" "$DEB_ROOT/DEBIAN/"
    cp "$ROOT_DIR/packaging/debian/postrm" "$DEB_ROOT/DEBIAN/"
    sed -i 's/\r$//' "$DEB_ROOT/DEBIAN/control" "$DEB_ROOT/DEBIAN/postinst" "$DEB_ROOT/DEBIAN/postrm"
    chmod 755 "$DEB_ROOT/DEBIAN/postinst" "$DEB_ROOT/DEBIAN/postrm"

    # Documentation & Copyright (Debian Policy §12.5, §12.7)
    install -m 644 "$ROOT_DIR/packaging/debian/copyright" "$DEB_ROOT/usr/share/doc/frostcenter/copyright"
    
    # Changelog: ensure version $VERSION is present at top
    CHANGELOG_TMP="$(mktemp)"
    if ! grep -q "^frostcenter ($VERSION" "$ROOT_DIR/packaging/debian/changelog"; then
        RFC_DATE=$(date -R 2>/dev/null || date +"%a, %d %b %Y %H:%M:%S +0000")
        cat <<EOF > "$CHANGELOG_TMP"
frostcenter ($VERSION-1) unstable; urgency=medium

  * Release version $VERSION.

 -- G Sriram <gsriram2403@gmail.com>  $RFC_DATE

EOF
        cat "$ROOT_DIR/packaging/debian/changelog" >> "$CHANGELOG_TMP"
    else
        cp "$ROOT_DIR/packaging/debian/changelog" "$CHANGELOG_TMP"
    fi
    gzip -9n -c "$CHANGELOG_TMP" > "$DEB_ROOT/usr/share/doc/frostcenter/changelog.gz"
    rm -f "$CHANGELOG_TMP"
    chmod 644 "$DEB_ROOT/usr/share/doc/frostcenter/changelog.gz"

    # Manual Page (Debian Policy §13.1) - dynamically stamped
    sed "s/\"FrostCenter [0-9.]*\"/\"FrostCenter $VERSION\"/" "$ROOT_DIR/packaging/frost.1" | gzip -9n -c > "$DEB_ROOT/usr/share/man/man1/frost.1.gz"
    chmod 644 "$DEB_ROOT/usr/share/man/man1/frost.1.gz"

    # Application files
    install -m 755 "$ROOT_DIR/packaging/frost" "$DEB_ROOT/usr/bin/frost"
    install -m 644 "$ROOT_DIR/OFC.py" "$DEB_ROOT/usr/share/frostcenter/"
    sed -i -e '/^#!\/usr\/bin\/python3/d' "$DEB_ROOT/usr/share/frostcenter/OFC.py"
    install -m 644 "$ROOT_DIR/ec_access.py" "$DEB_ROOT/usr/share/frostcenter/"
    install -m 644 "$ROOT_DIR/model_config.py" "$DEB_ROOT/usr/share/frostcenter/"
    
    # Injected version.py for runtime
    cat <<EOF > "$DEB_ROOT/usr/share/frostcenter/version.py"
"""FrostCenter version definition."""

__version__ = "$VERSION"
APP_NAME = "FrostCenter"
EOF

    install -m 644 "$ROOT_DIR/models/database.json" "$DEB_ROOT/usr/share/frostcenter/models/"
    install -m 644 "$ROOT_DIR"/ui/*.py "$DEB_ROOT/usr/share/frostcenter/ui/"

    # Desktop, icon, polkit, and appstream
    install -m 644 "$ROOT_DIR/packaging/io.github.gsriram24.frostcenter.desktop" "$DEB_ROOT/usr/share/applications/"
    if [ -f "$ROOT_DIR/assets/frostcenter.svg" ]; then
        install -m 644 "$ROOT_DIR/assets/frostcenter.svg" "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/"
    fi
    install -m 644 "$ROOT_DIR/packaging/polkit/io.github.gsriram24.frostcenter.policy" "$DEB_ROOT/usr/share/polkit-1/actions/"
    
    install -m 644 "$ROOT_DIR/packaging/metainfo/io.github.gsriram24.frostcenter.metainfo.xml" "$DEB_ROOT/usr/share/metainfo/"
    if ! grep -q "version=\"$VERSION\"" "$DEB_ROOT/usr/share/metainfo/io.github.gsriram24.frostcenter.metainfo.xml"; then
        TODAY=$(date +%Y-%m-%d)
        sed -i "/<releases>/a \    <release version=\"$VERSION\" date=\"$TODAY\">\n      <description>\n        <p>FrostCenter release $VERSION.</p>\n      </description>\n    </release>" "$DEB_ROOT/usr/share/metainfo/io.github.gsriram24.frostcenter.metainfo.xml"
    fi

    # Strip CRLF on installed scripts
    sed -i 's/\r$//' "$DEB_ROOT/usr/bin/frost"

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

    # Dynamically inject version into spec file
    sed -i "s/^Version:.*/Version:        $VERSION/" "$RPM_TOP/SPECS/frostcenter.spec"
    if ! grep -q "\- $VERSION-1" "$RPM_TOP/SPECS/frostcenter.spec"; then
        RPM_DATE=$(date +"%a %b %d %Y" 2>/dev/null || date +"%a %b %e %Y")
        sed -i "/%changelog/a * $RPM_DATE G Sriram <gsriram2403@gmail.com> - $VERSION-1\n- Release version $VERSION\n" "$RPM_TOP/SPECS/frostcenter.spec"
    fi

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
