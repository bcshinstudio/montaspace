"""Run MontaSpace GUI regression tests, surfacing discovery/import errors."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

suite = unittest.defaultTestLoader.discover(
    start_dir=str(ROOT / "tests"),
    pattern="test_gui_*.py",
    top_level_dir=str(ROOT),
)
found = suite.countTestCases()
expected = 6
print(f"Discovered {found} GUI test entries (minimum required: {expected})", flush=True)

# Run even when discovery yielded fewer than expected: unittest represents
# import/discovery failures as _FailedTest objects, whose traceback is visible
# only when the suite executes.
result = unittest.TextTestRunner(verbosity=2).run(suite)

if result.errors or result.failures:
    print(f"FAIL: {len(result.errors)} errors and {len(result.failures)} failures", flush=True)
    raise SystemExit(1)
if result.skipped:
    print(f"FAIL: {len(result.skipped)} GUI tests were skipped", flush=True)
    raise SystemExit(2)
if found < expected or result.testsRun < expected:
    print(f"FAIL: expected at least {expected} executed GUI tests, got {result.testsRun}", flush=True)
    raise SystemExit(2)
print(f"PASS: {result.testsRun} GUI tests executed with zero skips/errors", flush=True)
