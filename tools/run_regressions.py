"""MontaSpace regression runner: skip-free, strict GUI certification."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(label, args, env, timeout):
    print(f"\n=== {label} ===", flush=True)
    try:
        outcome = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"FAIL: {label} timed out", flush=True)
        return False
    except OSError as exc:
        print(f"FAIL: {label}: {exc}", flush=True)
        return False
    print(f"{'PASS' if outcome.returncode == 0 else 'FAIL'}: {label}", flush=True)
    return outcome.returncode == 0

def main():
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # Offscreen avoids creating desktop windows during unattended testing.
    env.setdefault('QT_QPA_PLATFORM', 'offscreen')
    fast = run('Qt-free reliability and geometry tests',
               ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_pure_*.py', '-v'], env, 60)
    if not run('PySide6 GUI prerequisite',
               ['-c', 'from PySide6.QtWidgets import QApplication; print("QtWidgets available")'], env, 20):
        print('FAIL: PySide6 QtWidgets unavailable. GUI tests cannot be certified.', flush=True)
        return 2
    gui = run('Real Qt whiteboard smoke tests (all six required)',
              ['tools/run_gui_tests_strict.py'], env, 120)
    contract = run('Installer and release contract tests',
                   ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_installer_contract.py', '-v'], env, 60)
    preflight = run('Release preflight unit tests',
                    ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_release_preflight.py', '-v'], env, 60)
    imports = run('Static application import contracts',
                  ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_import_contract.py', '-v'], env, 60)
    if fast and gui and contract and preflight and imports:
        print('PASS: all regression suites completed (no GUI skips)', flush=True)
        return 0
    print('FAIL: review errors before release', flush=True)
    return 1

if __name__ == '__main__':
    raise SystemExit(main())
