"""Guard installer identity, user data isolation, and read-only uninstall verification."""
import re
import unittest
from pathlib import Path
from tools.verify_release import ROOT

class InstallerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nsi = (ROOT / 'installer/MontaSpace.nsi').read_text(encoding='utf-8')
        cls.bat = (ROOT / 'build_installer.bat').read_text(encoding='utf-8')
        cls.verify = (ROOT / 'verify_uninstall.bat').read_text(encoding='utf-8')
        cls.config = (ROOT / 'app/config.py').read_text(encoding='utf-8')
        cls.meta = (ROOT / 'windows_version_info.txt').read_text(encoding='utf-8')

    def test_version_matches(self):
        self.assertIn('APP_VERSION = "0.8.5"', self.config)
        self.assertIn('!define PRODUCT_VERSION "0.8.5"', self.nsi)
        self.assertIn('VIProductVersion "0.8.5.0"', self.nsi)
        self.assertIn('filevers=(0, 8, 5, 0)', self.meta)
        self.assertIn('prodvers=(0, 8, 5, 0)', self.meta)
        self.assertIn('MontaSpace_Setup_0.8.5.exe', self.bat)

    def test_app_specific_registry_and_paths(self):
        self.assertIn('InstallLocation" "$INSTDIR"', self.nsi)
        self.assertIn('Uninstall\\MontaSpace"', self.nsi)
        self.assertIn('InstallDir "$LOCALAPPDATA\\Programs\\MontaSpace"', self.nsi)
        self.assertNotIn('MontaSpaceStudio', self.nsi)

    def test_uninstall_does_not_delete_media_or_foreign_cache(self):
        body = self.nsi.split('Section "Uninstall"')[1]
        self.assertNotIn('$DOCUMENTS', body.upper())
        self.assertNotIn('MontaSpaceStudio', body)
        self.assertNotIn('video-posters', body)
        self.assertNotIn('RMDir /r "$LOCALAPPDATA"', body)
        self.assertNotIn('RMDir /r "$PROFILE"', body)
        self.assertIn('RMDir /r "$INSTDIR"', body)

    def test_uninstall_verifier_is_read_only(self):
        self.assertIn('exit /b %FAIL%', self.verify)
        self.assertIn('reg query ', self.verify)
        self.assertNotRegex(self.verify.lower(), r'(?m)^\s*(?:del|erase|rmdir|rd|reg delete)\b')

    def test_build_preserves_repository(self):
        self.assertIn('tools\\verify_release.py', self.bat)
        self.assertIn('run_regression_tests.bat', self.bat)
        for protected in ('.git', '.venv'):
            self.assertNotRegex(self.bat.lower(), rf'(?im)^(?:rmdir|rd|del)\s+.*{re.escape(protected)}')

if __name__ == '__main__':
    unittest.main()
