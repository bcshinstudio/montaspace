"""Qt-free guardrails for HEIC import and reliable packaging."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HEICIntegrationContracts(unittest.TestCase):
    def test_decoder_has_real_pillow_heif_fallback(self):
        source = (ROOT / 'app/imaging.py').read_text()
        for required in ('from pillow_heif import register_heif_opener',
                         'from PIL import Image, ImageOps', 'ImageOps.exif_transpose',
                         'QImage.Format.Format_RGBA8888', 'image.copy()',
                         'PREVIEW_MAX_EDGE', 'return _pillow_preview(filename)'):
            self.assertIn(required, source)

    def test_dragdrop_reports_failures(self):
        """Preserve image import and show a warning for every local-file failure."""
        source = (ROOT / 'app/canvas.py').read_text()
        enter = source.split('    def dragEnterEvent(self, event):', 1)[1].split('    def dragMoveEvent(', 1)[0]
        move = source.split('    def dragMoveEvent(self, event):', 1)[1].split('    def dropEvent(', 1)[0]
        drop = source.split('    def dropEvent(self, event):', 1)[1].split('    def wheelEvent(', 1)[0]

        # Both drag phases accept local files regardless of extension, allowing
        # unsupported files to reach dropEvent and trigger user feedback.
        for phase in (enter, move):
            self.assertIn('_has_local_drop_urls(event)', phase)
            self.assertIn('event.acceptProposedAction()', phase)
            self.assertIn('event.ignore()', phase)
        self.assertIn('url.isLocalFile()', source)

        self.assertIn('SUPPORTED_EXTENSIONS', drop)
        self.assertIn('self.add_image(source, pos)', drop)
        self.assertIn('unsupported.append(', drop)
        self.assertIn('failed_images.append(', drop)
        self.assertIn('folders.append(', drop)
        self.assertIn('QMessageBox.warning(', drop)
        self.assertIn('MontaSpace Studio', drop)
        self.assertIn('event.acceptProposedAction()', drop)
        self.assertIn('event.ignore()', drop)

    def test_dependencies_and_installer_collection(self):
        requirements = (ROOT / 'requirements.txt').read_text()
        self.assertIn('pillow-heif', requirements)
        self.assertIn('Pillow', requirements)
        for batch in ('build_installer.bat', 'build_windows.bat'):
            contents = (ROOT / batch).read_text()
            self.assertIn('--collect-all pillow_heif', contents)
            self.assertIn('tools\\check_image_codecs.py', contents)
        self.assertTrue((ROOT / 'tools/check_image_codecs.py').exists())


if __name__ == '__main__':
    unittest.main()
