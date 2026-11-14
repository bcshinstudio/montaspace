"""Qt-free behavior tests for MontaSpace's actual Canvas drop handlers.

Run with: python -m unittest discover -s tests -p 'test_montaspace_dragdrop.py' -v
"""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


class Mime:
    def __init__(self, urls):
        self._urls = urls

    def urls(self):
        return self._urls

    def hasUrls(self):
        return bool(self._urls)


class Url:
    def __init__(self, path, local=True):
        self.path = str(path)
        self.local = local

    def isLocalFile(self):
        return self.local

    def toLocalFile(self):
        return self.path


class Point:
    def __init__(self):
        self._x = 0
        self._y = 0

    def toPoint(self):
        return self

    def x(self):
        return self._x

    def y(self):
        return self._y

    def setX(self, value):
        self._x = value

    def setY(self, value):
        self._y = value


class DropEvent:
    def __init__(self, urls):
        self.mime = Mime(urls)
        self.accepted = False
        self.ignored = False

    def mimeData(self):
        return self.mime

    def position(self):
        return Point()

    def acceptProposedAction(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


def load_handlers():
    """Compile only the real drag handlers: no fake reimplementation of them."""
    tree = ast.parse((ROOT / 'app/canvas.py').read_text(encoding='utf-8'))
    canvas = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Canvas')
    names = {'_has_local_drop_urls', 'dragEnterEvent', 'dragMoveEvent', 'dropEvent'}
    funcs = [node for node in canvas.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(funcs) != len(names):
        raise AssertionError('Drag/drop handler set is incomplete')
    cls = ast.ClassDef(name='CanvasHandlers', bases=[], keywords=[], body=funcs, decorator_list=[])
    script = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    warning = Mock()
    scope = {
        'Path': Path,
        'SUPPORTED_EXTENSIONS': {'.jpg', '.png', '.heic'},
        'QMessageBox': type('MessageBox', (), {'warning': warning}),
    }
    exec(compile(script, '<extracted Canvas handlers>', 'exec'), scope)
    return scope['CanvasHandlers'], warning


class DragDropTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        cls, self.warning = load_handlers()
        self.canvas = cls()
        self.canvas.mapToScene = lambda value: value
        self.canvas.add_image = Mock(return_value=True)

    def file(self, name):
        path = self.folder / name
        path.write_bytes(b'example')
        return path

    def test_unsupported_video_warns(self):
        video = self.file('movie.mp4')
        event = DropEvent([Url(video)])
        self.canvas.dragEnterEvent(event)
        self.assertTrue(event.accepted)
        self.canvas.dropEvent(event)
        self.assertTrue(event.accepted)
        self.canvas.add_image.assert_not_called()
        message = self.warning.call_args.args[2]
        self.assertIn('movie.mp4', message)
        self.assertIn('MontaSpace Studio', message)

    def test_supported_image_imports_without_warning(self):
        jpg = self.file('photo.JPG')
        event = DropEvent([Url(jpg)])
        self.canvas.dragEnterEvent(event)
        self.canvas.dragMoveEvent(event)
        self.canvas.dropEvent(event)
        self.assertTrue(event.accepted)
        self.canvas.add_image.assert_called_once()
        self.warning.assert_not_called()

    def test_mixed_drop_imports_image_and_warns_once(self):
        jpg, video = self.file('photo.jpg'), self.file('movie.mov')
        event = DropEvent([Url(jpg), Url(video)])
        self.canvas.dropEvent(event)
        self.canvas.add_image.assert_called_once()
        self.warning.assert_called_once()
        self.assertIn('movie.mov', self.warning.call_args.args[2])

    def test_unreadable_supported_image_warns(self):
        png = self.file('broken.png')
        self.canvas.add_image.return_value = False
        self.canvas.dropEvent(DropEvent([Url(png)]))
        self.assertIn('broken.png', self.warning.call_args.args[2])

    def test_folder_warns(self):
        folder = self.folder / 'folder'
        folder.mkdir()
        self.canvas.dropEvent(DropEvent([Url(folder)]))
        self.assertIn('Folders cannot be inserted', self.warning.call_args.args[2])

    def test_missing_file_warns(self):
        missing = self.folder / 'missing.jpg'
        self.canvas.dropEvent(DropEvent([Url(missing)]))
        self.assertIn('missing.jpg', self.warning.call_args.args[2])

    def test_nonlocal_urls_ignored(self):
        event = DropEvent([Url('https://example.org/photo.jpg', local=False)])
        self.canvas.dragEnterEvent(event)
        self.canvas.dragMoveEvent(event)
        self.canvas.dropEvent(event)
        self.assertTrue(event.ignored)
        self.assertFalse(event.accepted)
        self.warning.assert_not_called()
        self.canvas.add_image.assert_not_called()

    def test_empty_drop_ignored(self):
        event = DropEvent([])
        self.canvas.dragEnterEvent(event)
        self.canvas.dropEvent(event)
        self.assertTrue(event.ignored)
        self.warning.assert_not_called()


if __name__ == '__main__':
    unittest.main()
