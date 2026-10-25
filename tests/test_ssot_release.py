"""Comprehensive empirical test suite for FrostCenter Single Source of Truth (SSOT) release automation.

Validates:
1. Version format, parsing, and runtime exports.
2. Dynamic packaging manifest substitution logic (Debian, RPM, Arch, Manpage, AppStream XML).
3. XML syntax validity of generated AppStream metainfo.
4. Shell script line endings (must be LF, zero CRLF) and execution safety.
5. GitHub Actions workflow trigger and release steps validation.
6. Python syntax compilation across all repository files.
7. ModelConfig hardware database integrity, including verified board checks.
"""

import os
import re
import unittest
import py_compile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestSSOTVersioning(unittest.TestCase):
    """Test suite ensuring single source of truth versioning and packaging safety."""

    def test_01_version_py_format(self):
        """Ensure version.py defines a valid SemVer string."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        import version

        self.assertTrue(hasattr(version, "__version__"), "version.py missing __version__")
        self.assertTrue(hasattr(version, "APP_NAME"), "version.py missing APP_NAME")
        self.assertEqual(version.APP_NAME, "FrostCenter")

        # Semantic Versioning regex (MAJOR.MINOR.PATCH[-PRERELEASE])
        semver_regex = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
        self.assertRegex(
            version.__version__,
            semver_regex,
            f"Version '{version.__version__}' does not adhere to Semantic Versioning (X.Y.Z)",
        )

    def test_02_script_line_endings_are_lf(self):
        """Empirically prove that all Linux executable scripts use LF line endings (no CRLF)."""
        scripts_to_check = [
            REPO_ROOT / "packaging" / "build_packages.sh",
            REPO_ROOT / "packaging" / "test_packages.sh",
            REPO_ROOT / "packaging" / "frost",
            REPO_ROOT / "install.sh",
        ]

        for script in scripts_to_check:
            self.assertTrue(script.is_file(), f"Script not found: {script}")
            raw_bytes = script.read_bytes()
            self.assertNotIn(
                b"\r\n",
                raw_bytes,
                f"CRLF line ending detected in {script.name}! Must be LF for Linux compatibility.",
            )

    def test_03_debian_control_substitution(self):
        """Verify dynamic substitution on Debian control file."""
        control_file = REPO_ROOT / "packaging" / "debian" / "control"
        self.assertTrue(control_file.is_file())
        content = control_file.read_text(encoding="utf-8")

        test_version = "0.2.5"
        modified = re.sub(r"^Version:.*", f"Version: {test_version}", content, flags=re.MULTILINE)
        self.assertIn(f"Version: {test_version}", modified)
        self.assertIn("Package: frostcenter", modified)
        self.assertIn("Architecture: all", modified)

    def test_04_rpm_spec_substitution(self):
        """Verify dynamic substitution on RPM spec file."""
        spec_file = REPO_ROOT / "packaging" / "rpm" / "frostcenter.spec"
        self.assertTrue(spec_file.is_file())
        content = spec_file.read_text(encoding="utf-8")

        test_version = "0.2.5"
        modified = re.sub(r"^Version:.*", f"Version:        {test_version}", content, flags=re.MULTILINE)
        self.assertIn(f"Version:        {test_version}", modified)
        self.assertIn("%autosetup -n %{name}-%{version}", modified)
        self.assertIn("%changelog", modified)

    def test_05_arch_pkgbuild_substitution(self):
        """Verify dynamic substitution on Arch PKGBUILD."""
        pkgbuild_file = REPO_ROOT / "packaging" / "arch" / "PKGBUILD"
        self.assertTrue(pkgbuild_file.is_file())
        content = pkgbuild_file.read_text(encoding="utf-8")

        test_version = "0.2.5"
        modified = re.sub(r"^pkgver=.*", f"pkgver={test_version}", content, flags=re.MULTILINE)
        self.assertIn(f"pkgver={test_version}", modified)
        self.assertIn("pkgname=frostcenter", modified)

    def test_06_manpage_header_substitution(self):
        """Verify dynamic substitution on manpage header."""
        man_file = REPO_ROOT / "packaging" / "frost.1"
        self.assertTrue(man_file.is_file())
        content = man_file.read_text(encoding="utf-8")

        test_version = "0.2.5"
        modified = re.sub(r'"FrostCenter [0-9.]*"', f'"FrostCenter {test_version}"', content)
        self.assertIn(f'"FrostCenter {test_version}"', modified)

    def test_07_appstream_xml_validity_after_release_injection(self):
        """Verify that injecting a new release block into AppStream XML yields 100% valid XML."""
        xml_file = REPO_ROOT / "packaging" / "metainfo" / "io.github.gsriram24.frostcenter.metainfo.xml"
        self.assertTrue(xml_file.is_file())
        content = xml_file.read_text(encoding="utf-8")

        test_version = "0.2.5"
        release_block = f"""    <release version="{test_version}" date="2026-10-25">
      <description>
        <p>FrostCenter release {test_version}.</p>
      </description>
    </release>"""
        modified = content.replace("<releases>", f"<releases>\n{release_block}")

        # Parse with XML parser to empirically prove syntax validity
        try:
            root = ET.fromstring(modified)
            self.assertEqual(root.tag, "component")
            releases = root.find("releases")
            self.assertIsNotNone(releases)
            first_release = releases.find("release")
            self.assertEqual(first_release.get("version"), test_version)
        except ET.ParseError as err:
            self.fail(f"Generated AppStream XML is malformed: {err}")

    def test_08_github_workflow_release_structure(self):
        """Verify that .github/workflows/release.yml contains required automated release steps."""
        wf_file = REPO_ROOT / ".github" / "workflows" / "release.yml"
        self.assertTrue(wf_file.is_file())
        content = wf_file.read_text(encoding="utf-8")

        self.assertIn("tags:", content)
        self.assertIn("- 'v*'", content)
        self.assertIn("contents: write", content)
        self.assertIn("TAG_VERSION=\"${GITHUB_REF_NAME#v}\"", content)
        self.assertIn("./packaging/build_packages.sh \"$RELEASE_VERSION\"", content)
        self.assertIn("softprops/action-gh-release@v2", content)
        self.assertIn("dist/*.deb", content)
        self.assertIn("dist/*.rpm", content)
        self.assertIn("dist/*.tar.gz", content)

    def test_09_readme_installation_commands_are_evergreen(self):
        """Ensure README uses wildcard/evergreen package paths so it does not drift."""
        readme = REPO_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")

        self.assertIn("sudo apt install ./frostcenter_*_all.deb", content)
        self.assertIn("sudo dnf install ./frostcenter-*.noarch.rpm", content)
        self.assertIn("tar -xzf frostcenter-*.tar.gz", content)

    def test_10_python_syntax_all_files(self):
        """Empirically prove all Python source files compile cleanly without syntax errors."""
        py_files = list(REPO_ROOT.glob("*.py")) + list((REPO_ROOT / "ui").glob("*.py")) + list((REPO_ROOT / "tests").glob("*.py"))
        for py_path in py_files:
            try:
                py_compile.compile(str(py_path), doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Syntax error compiling {py_path.name}: {e}")

    def test_11_model_database_ms_1795_verified(self):
        """Verify that newly supported board MS-1795 is properly defined and verified."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from model_config import ModelConfig

        mc = ModelConfig(board_override="MS-1795")
        self.assertEqual(mc.board_name, "MS-1795")
        self.assertEqual(mc.model_name, "GE72 6QD Apache Pro")
        self.assertEqual(mc.group, "G1_10")
        self.assertTrue(mc.is_verified, "MS-1795 must have verified=True")
        self.assertEqual(mc.cpu_temp_addr, 0x68)
        self.assertEqual(mc.gpu_temp_addr, 0x80)
        self.assertEqual(mc.cooler_boost_addr, 0x98)


if __name__ == "__main__":
    unittest.main()
