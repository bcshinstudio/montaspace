"""Isolated MontaSpace GUI stress benchmark, one fresh process per image count.

Run with project .venv Python: python tools/stress_test.py 25 --output <path>
All generated images and projects stay in a temporary directory and are deleted.
A machine-readable report is written only after the benchmark has passed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.stress_common import validate_count, validate_report


def seconds(start: float) -> float:
    return round(time.perf_counter() - start, 5)


def size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 5)


def safe_memory(fn):
    try:
        value = fn()
        return round(value, 3) if value is not None and math.isfinite(value) else None
    except OSError:
        return None


def run(count: int) -> dict:
    validate_count(count)
    # Import Qt only after validating CLI args, allowing Qt-free checks of helpers.
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication
    from app.config import APP_VERSION
    from app.performance import (memory_working_set_mb, memory_peak_working_set_mb,
                                 memory_private_mb)
    from app.window import MontaSpace

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    board = MontaSpace()
    width, height = 1800, 1200
    try:
        with tempfile.TemporaryDirectory(prefix='montaspace-stress-') as directory:
            folder = Path(directory)
            start = time.perf_counter()
            files = []
            for index in range(count):
                image = QImage(width, height, QImage.Format.Format_RGB32)
                image.fill(QColor.fromHsv((index * 37) % 360, 170, 210))
                filename = folder / f'stress_{index:03d}.jpg'
                if not image.save(str(filename), 'JPEG', 83):
                    raise RuntimeError(f'Image generation failed: {filename.name}')
                files.append(filename)
            generate = seconds(start)

            start = time.perf_counter()
            for index, filename in enumerate(files):
                if not board.canvas.add_image(str(filename), QPointF(0, 0), record_undo=False):
                    raise RuntimeError(f'Image insertion failed: {filename.name}')
            insert = seconds(start)
            app.processEvents()
            if len(board.canvas.image_stack()) != count:
                raise AssertionError('Inserted image count mismatch')
            inserted_ram = safe_memory(memory_working_set_mb)

            # Apply unique positions and transforms to exercise metadata persistence.
            for i, item in enumerate(board.canvas.image_stack()):
                item.setPos((i % 10) * 105, (i // 10) * 75)
                item.setRotation((i % 5) * 3)
                item.setScale(0.65 + (i % 3) * 0.1)
            expected = board.project_snapshot()

            linked = folder / 'stress.mspace'
            start = time.perf_counter()
            if not board._write_project(linked):
                raise AssertionError('Linked save failed')
            linked_save = seconds(start)
            portable = folder / 'stress.mspacepack'
            start = time.perf_counter()
            if not board._write_project(portable):
                raise AssertionError('Portable save failed')
            portable_save = seconds(start)
            if not linked.is_file() or not portable.is_file():
                raise AssertionError('Saved project file is missing')

            start = time.perf_counter()
            if not board._read_project(linked):
                raise AssertionError('Linked reopen failed')
            linked_open = seconds(start)
            if len(board.canvas.image_stack()) != count:
                raise AssertionError('Linked reopen image count mismatch')
            if board.project_snapshot() != expected:
                raise AssertionError('Linked reopen changed image transforms or sources')

            start = time.perf_counter()
            if not board._read_project(portable):
                raise AssertionError('Portable reopen failed')
            portable_open = seconds(start)
            if len(board.canvas.image_stack()) != count:
                raise AssertionError('Portable reopen image count mismatch')
            # Embedded images are extracted to temp paths, so compare geometry, not source.
            actual = board.project_snapshot()
            for before, after in zip(expected, actual):
                for key in ('x', 'y', 'scale', 'rotation', 'crop', 'z'):
                    if before[key] != after[key]:
                        raise AssertionError(f'Portable reopen changed {key}')

            app.processEvents()
            result = {
                'version': APP_VERSION, 'images': count,
                'image_dimensions': f'{width}x{height}',
                'generate_seconds': generate, 'insert_seconds': insert,
                'linked_save_seconds': linked_save,
                'portable_save_seconds': portable_save,
                'linked_open_seconds': linked_open,
                'portable_open_seconds': portable_open,
                'working_set_after_insert_mb': inserted_ram,
                'working_set_after_test_mb': safe_memory(memory_working_set_mb),
                'peak_working_set_mb': safe_memory(memory_peak_working_set_mb),
                'private_memory_mb': safe_memory(memory_private_mb),
                'linked_size_mb': size_mb(linked),
                'portable_size_mb': size_mb(portable),
            }
            validate_report(result, count)
            return result
    finally:
        # Never display unsaved-project prompts during automated teardown.
        board.confirm_discard_changes = lambda: True
        board.new_project()
        board.close()
        board.deleteLater()
        app.processEvents()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('count', type=int, help='Number of test images (1 to 100)')
    parser.add_argument('--output', type=Path, help='Write verified JSON report to this path')
    args = parser.parse_args(argv)
    validate_count(args.count)
    result = run(args.count)
    data = json.dumps(result, indent=2) + '\n'
    print(data)
    if args.output is not None:
        # Parent runner passes a dedicated result path, not the source tree.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding='utf-8')
        print(f'Validated report: {args.output}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'STRESS TEST FAILED: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
