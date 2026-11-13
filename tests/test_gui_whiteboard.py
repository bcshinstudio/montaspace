"""Real Qt regression tests (requires PySide6; use run_regression_tests.bat)."""
import tempfile
import unittest
from pathlib import Path

# Import failures must remain visible. A missing application module or a
# broken application import is a test failure, NOT a reason to skip tests.
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from app.window import MontaSpace


class WhiteboardSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.qt_app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='montaspace-regression-')
        self.root = Path(self.temp.name)
        image = QImage(120, 80, QImage.Format.Format_RGB32)
        image.fill(QColor('#487cb0'))
        self.photo = self.root / 'test_photo.png'
        self.assertTrue(image.save(str(self.photo)))
        self.board = MontaSpace()
        self.board.show()
        self.qt_app.processEvents()

    def tearDown(self):
        self.board.confirm_discard_changes = lambda: True
        self.board.new_project()
        self.board.close()
        self.board.deleteLater()
        self.qt_app.processEvents()
        self.temp.cleanup()

    def add_photo(self):
        self.assertTrue(self.board.canvas.add_image(str(self.photo), QPointF(50, 60)))
        return self.board.canvas.image_stack()[0]

    def test_insert_undo_redo(self):
        self.add_photo()
        self.board.perform_undo()
        self.assertEqual(len(self.board.canvas.image_stack()), 0)
        self.board.perform_redo()
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_crop_rotate_and_duplicate(self):
        item = self.add_photo()
        item.setRotation(30)
        item.setScale(1.25)
        item.start_crop()
        item.crop_rect = QRectF(10, 8, 60, 45)
        item.end_crop(True)
        self.assertEqual(item.rotation(), 30)
        self.assertEqual(item.scale(), 1.25)
        self.assertEqual(item.crop_rect.width(), 60)
        item.setSelected(True)
        self.board.canvas.duplicate_selected()
        self.assertEqual(len(self.board.canvas.image_stack()), 2)
        self.board.perform_undo()
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_reused_preview(self):
        first = self.add_photo()
        self.assertTrue(self.board.canvas.add_image(str(self.photo)))
        second = [i for i in self.board.canvas.image_stack() if i is not first][0]
        self.assertEqual(first.pixmap.cacheKey(), second.pixmap.cacheKey())

    def test_linked_roundtrip(self):
        item = self.add_photo()
        item.setRotation(15)
        item.setScale(1.4)
        target = self.root / 'saved.mspace'
        self.assertTrue(self.board._write_project(target))
        self.assertTrue(self.board._read_project(target))
        restored = self.board.canvas.image_stack()[0]
        self.assertAlmostEqual(restored.rotation(), 15)
        self.assertAlmostEqual(restored.scale(), 1.4)

    def test_portable_roundtrip(self):
        self.add_photo()
        target = self.root / 'saved.mspacepack'
        self.assertTrue(self.board._write_project(target))
        self.assertTrue(self.board._read_project(target))
        self.assertEqual(len(self.board.canvas.image_stack()), 1)

    def test_new_clears_board(self):
        self.add_photo()
        self.board.confirm_discard_changes = lambda: True
        self.board.new_project()
        self.assertFalse(self.board.canvas.image_stack())

if __name__ == '__main__':
    unittest.main()
