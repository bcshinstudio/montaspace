"""Run fresh-process 25/50/100 image stress tests and save audited reports."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import subprocess
import sys
import time
from pathlib import Path

from tools.stress_common import COUNTS, save_summary, validate_report


def run_suite(python_exe: str, script: Path, output_dir: Path, counts=COUNTS) -> list[dict]:
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    results = []
    for count in counts:
        output = output_dir / f'MontaSpace_Stress_{timestamp}_{count}.json'
        print(f'\n=== MontaSpace {count} images (fresh process) ===', flush=True)
        cmd = [python_exe, str(script), str(count), '--output', str(output)]
        completed = subprocess.run(cmd, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f'{count}-image test failed with exit code {completed.returncode}')
        if not output.is_file():
            raise RuntimeError(f'{count}-image test did not create a report')
        try:
            result = json.loads(output.read_text(encoding='utf-8'))
            validate_report(result, count)
        except (ValueError, OSError) as exc:
            raise RuntimeError(f'Invalid {count}-image report: {exc}') from exc
        results.append(result)
        print(f'PASS: {count} images; insert {result["insert_seconds"]:.3f}s; '
              f'portable reopen {result["portable_open_seconds"]:.3f}s', flush=True)
    json_path, csv_path = save_summary(results, output_dir, timestamp)
    print(f'\nPASS: {len(results)} of {len(counts)} stress scenarios completed')
    print(f'JSON summary: {json_path}\nCSV summary: {csv_path}', flush=True)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path.home() / 'Documents' / 'MontaSpace_Test_Reports')
    args = parser.parse_args(argv)
    run_suite(sys.executable, Path(__file__).with_name('stress_test.py'), args.output_dir)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
