"""Ensure the preflight catches mismatched version metadata."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from tools.verify_release import ROOT, verify


class ReleasePreflightTests(unittest.TestCase):
    def test_current_release_consistent(self):
        self.assertEqual(verify(ROOT), [])

    def test_detects_mismatch_in_numeric_version(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["main.py", "requirements.txt", "assets/MontaSpace.ico",
                         "app/config.py", "app/window.py", "windows_version_info.txt",
                         "installer/MontaSpace.nsi", "build_installer.bat",
                         "run_regression_tests.bat", "run_stress_suite.bat",
                         "tests/test_gui_whiteboard.py", "tools/run_gui_tests_strict.py",
                         "README.md", "verify_uninstall.bat",
                         "tests/test_installer_contract.py",
                         "tests/test_import_contract.py"]:
                dst = root / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dst)
            version = root / "windows_version_info.txt"
            version.write_text(version.read_text().replace("filevers=(0, 8, 5, 0)",
                                                        "filevers=(0, 8, 4, 0)"))
            self.assertTrue(any("filevers=" in x for x in verify(root)))


if __name__ == "__main__":
    unittest.main()
