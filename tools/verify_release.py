"""Static preflight checks for the Windows MontaSpace release. No third-party modules."""
import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    root = Path(root)
    errors = []
    required = ["main.py", "requirements.txt", "assets/MontaSpace.ico",
                "app/config.py", "app/window.py", "windows_version_info.txt",
                "installer/MontaSpace.nsi", "build_installer.bat",
                "run_regression_tests.bat", "run_stress_suite.bat",
                "verify_uninstall.bat", "tests/test_installer_contract.py",
                "tests/test_import_contract.py",
                "tests/test_gui_whiteboard.py", "tools/run_gui_tests_strict.py"]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"Missing required file: {name}")
    if errors:
        return errors

    config = (root / "app/config.py").read_text(encoding="utf-8")
    parsed = ast.parse(config)
    versions = [node.value.value for node in parsed.body
                if isinstance(node, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in node.targets)
                and isinstance(node.value, ast.Constant)]
    if len(versions) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", versions[0]):
        return ["APP_VERSION missing or invalid in app/config.py"]
    version = versions[0]
    parts = tuple(map(int, version.split("."))) + (0,)
    info = (root / "windows_version_info.txt").read_text(encoding="utf-8")
    nsis = (root / "installer/MontaSpace.nsi").read_text(encoding="utf-8")
    build = (root / "build_installer.bat").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""

    for name in ("filevers", "prodvers"):
        expected = f"{name}=({', '.join(map(str, parts))})"
        if expected not in info:
            errors.append(f"windows_version_info.txt: expected {expected}")
    for name in ("FileVersion", "ProductVersion"):
        expected = f"StringStruct('{name}', '{version}.0')"
        if expected not in info:
            errors.append(f"windows_version_info.txt: expected {expected}")
    for expected in [f'!define PRODUCT_VERSION "{version}"',
                     f'VIProductVersion "{version}.0"',
                     f'VIAddVersionKey "FileVersion" "{version}.0"',
                     f'VIAddVersionKey "ProductVersion" "{version}"']:
        if expected not in nsis:
            errors.append(f"installer/MontaSpace.nsi: missing {expected}")
    expected_installer = f"MontaSpace_Setup_{version}.exe"
    if expected_installer not in build:
        errors.append(f"build_installer.bat: expected installer {expected_installer}")
    if f"v{version}" not in readme:
        errors.append(f"README.md: version v{version} not found")
    if 'WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"' not in nsis:
        errors.append("installer/MontaSpace.nsi: missing InstallLocation registry entry")
    if 'MontaSpaceStudio' in nsis:
        errors.append("installer/MontaSpace.nsi: unexpected Studio reference")
    if (root / "assets/MontaSpace.ico").stat().st_size < 100:
        errors.append("assets/MontaSpace.ico: suspiciously small")
    return errors


def main():
    errors = verify()
    if errors:
        for err in errors:
            print("FAIL:", err)
        return 1
    print("PASS: release files, Windows numeric/string versions, NSIS metadata and installer name match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
