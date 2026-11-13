"""Qt-free tests for project integrity and shared Studio edge geometry."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from app.edge_hit import hit_rect_edge
from app.project_reliability import verify_staged_project


class EdgeHitTests(unittest.TestCase):
    def test_corners(self):
        for x, y, expected in [(10, 20, 'tl'), (110, 20, 'tr'),
                               (10, 100, 'bl'), (110, 100, 'br')]:
            self.assertEqual(hit_rect_edge(x, y, 10, 20, 110, 100), expected)

    def test_edges(self):
        for x, y, expected in [(10, 60, 'left'), (110, 60, 'right'),
                               (60, 20, 'top'), (60, 100, 'bottom')]:
            self.assertEqual(hit_rect_edge(x, y, 10, 20, 110, 100), expected)

    def test_outside(self):
        self.assertIsNone(hit_rect_edge(400, 400, 10, 20, 110, 100))
        self.assertIsNone(hit_rect_edge(10, 20, 110, 100, 0, 0))

    def test_small_rect_edges_remain_accessible(self):
        self.assertEqual(hit_rect_edge(15, 30, 10, 20, 20, 40), 'left')


class StagedProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = {'source': 'images/picture.png', 'x': 1, 'y': 2,
                       'scale': 1, 'rotation': 0, 'crop': [0, 0, 20, 20], 'z': 0}

    def payload(self, portable):
        obj = {'format': 'MontaSpace', 'version': 1, 'images': [self.record]}
        if portable:
            obj['portable'] = True
        return obj

    def test_valid_linked(self):
        p = self.root / 'project.mspace'
        p.write_text(json.dumps(self.payload(False)))
        verify_staged_project(p, 1, False)

    def test_valid_portable(self):
        p = self.root / 'project.mspacepack'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('project.json', json.dumps(self.payload(True)))
            z.writestr('images/picture.png', b'test')
        verify_staged_project(p, 1, True)

    def test_missing_embedded_rejected(self):
        p = self.root / 'missing.mspacepack'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('project.json', json.dumps(self.payload(True)))
        with self.assertRaises(ValueError):
            verify_staged_project(p, 1, True)

    def test_duplicate_embedded_rejected(self):
        p = self.root / 'duplicate.mspacepack'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('project.json', json.dumps(self.payload(True)))
            z.writestr('images/picture.png', b'one')
            z.writestr('images/picture.png', b'two')
        with self.assertRaises(ValueError):
            verify_staged_project(p, 1, True)

    def test_wrong_format_and_count_rejected(self):
        p = self.root / 'project.mspace'
        p.write_text(json.dumps(self.payload(False)))
        with self.assertRaises(ValueError):
            verify_staged_project(p, 2, False)
        p.write_text(json.dumps({'format': 'Studio', 'version': 1, 'images': [self.record]}))
        with self.assertRaises(ValueError):
            verify_staged_project(p, 1, False)

    def test_invalid_json(self):
        p = self.root / 'corrupt.mspace'
        p.write_text('not-json')
        with self.assertRaises(ValueError):
            verify_staged_project(p, 1, False)


if __name__ == '__main__':
    unittest.main()
