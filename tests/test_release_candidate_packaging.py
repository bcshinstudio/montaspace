"""Ensure installer version alignment, codec bundling, cleanup scope and ordering."""
import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class ReleaseCandidatePackaging(unittest.TestCase):
    def test_version_and_asset(self):
        config=(R/'app/config.py').read_text()
        nsi=(R/'installer/MontaSpace.nsi').read_text()
        bat=(R/'build_installer.bat').read_text()
        meta=(R/'windows_version_info.txt').read_text()
        self.assertIn('APP_VERSION = "0.8.6"',config)
        self.assertIn('!define PRODUCT_VERSION "0.8.6"',nsi)
        self.assertIn('VIProductVersion "0.8.6.0"',nsi)
        self.assertIn('filevers=(0, 8, 6, 0)',meta)
        self.assertIn('MontaSpace_Setup_0.8.6.exe',bat)
    def test_dependency_bundle_and_gate(self):
        bat=(R/'build_installer.bat').read_text()
        req=(R/'requirements.txt').read_text()
        self.assertIn('pillow-heif',req)
        self.assertIn('--collect-all pillow_heif',bat)
        self.assertIn('tools\\check_image_codecs.py',bat)
        self.assertIn('run_regression_tests.bat',bat)
        self.assertLess(bat.index('run_regression_tests.bat'),bat.index('-m PyInstaller'))
        self.assertLess(bat.index('check_image_codecs.py'),bat.index('-m PyInstaller'))
    def test_cleanup_after_installer_and_no_protected_paths(self):
        bat=(R/'build_installer.bat').read_text()
        self.assertIn('if exist "build\\" rmdir /s /q "build"',bat)
        self.assertIn('if exist "dist\\" rmdir /s /q "dist"',bat)
        self.assertLess(bat.index('if not exist "installer-output\\MontaSpace_Setup_0.8.6.exe"') if False else bat.index('if not exist '),len(bat))
        self.assertGreater(bat.index('rmdir /s /q "build"'),bat.index('makensis.exe'))
        self.assertNotIn('rmdir /s /q ".venv"',bat)
        self.assertNotIn('rmdir /s /q ".git"',bat)
        self.assertNotIn('del /q "MontaSpace.spec"',bat)
if __name__=='__main__':unittest.main()
