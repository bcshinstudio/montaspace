"""Qt-free unit tests for stress test validation and runner failure behavior."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.stress_common import TIMING_KEYS, validate_count, validate_report, save_summary
from tools.run_stress_suite import run_suite


def valid_report(count=25):
    out = {'version': '0.8.5', 'images': count, 'image_dimensions': '1800x1200',
           'linked_size_mb': 0.01, 'portable_size_mb': 2.3}
    out.update({key: 0.02 for key in TIMING_KEYS})
    return out


class StressToolsTests(unittest.TestCase):
    def test_count(self):
        for n in (1, 25, 50, 100):
            self.assertEqual(validate_count(n), n)
        for n in (-1, 0, 101, 4.2, '25', True):
            with self.assertRaises(ValueError):
                validate_count(n)

    def test_valid_report(self):
        validate_report(valid_report(), 25)

    def test_missing_timing_rejected(self):
        report = valid_report()
        del report['portable_open_seconds']
        with self.assertRaises(ValueError):
            validate_report(report, 25)

    def test_wrong_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_report(valid_report(50), 25)

    def test_nan_timing_rejected(self):
        report = valid_report()
        report['insert_seconds'] = float('nan')
        with self.assertRaises(ValueError):
            validate_report(report, 25)

    def test_summary_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_summary([valid_report()], Path(tmp), 'test')
            self.assertTrue(all(p.is_file() for p in paths))
            self.assertEqual(json.loads(paths[0].read_text())[0]['images'], 25)
            self.assertIn('images', paths[1].read_text())

    def test_runner_accepts_three_valid_child_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / 'success.py'
            fake.write_text(
                'import json, sys\n'
                'from pathlib import Path\n'
                'count=int(sys.argv[1])\n'
                'report={"version":"0.8.5","images":count,"image_dimensions":"1800x1200",'
                '"linked_size_mb":0.01,"portable_size_mb":0.1}\n'
                'for k in '+repr(TIMING_KEYS)+': report[k]=0.1\n'
                'Path(sys.argv[3]).write_text(json.dumps(report))\n'
            )
            result = run_suite(sys.executable, fake, root, counts=(25, 50, 100))
            self.assertEqual([x['images'] for x in result], [25, 50, 100])
            self.assertEqual(len(list(root.glob('*Summary*.csv'))), 1)

    def test_runner_rejects_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / 'bad.py'
            fake.write_text('import sys\nfrom pathlib import Path\nPath(sys.argv[3]).write_text("not json")\n')
            with self.assertRaises(RuntimeError):
                run_suite(sys.executable, fake, root, counts=(25,))

    def test_runner_rejects_failed_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'fail.py'
            fake.write_text('raise SystemExit(3)\n')
            with self.assertRaises(RuntimeError):
                run_suite(sys.executable, fake, Path(tmp), counts=(25,))

    def test_runner_rejects_missing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'empty.py'
            fake.write_text('print("pretending to pass")\n')
            with self.assertRaises(RuntimeError):
                run_suite(sys.executable, fake, Path(tmp), counts=(25,))


if __name__ == '__main__':
    unittest.main()
