"""Qt-free validation and reporting helpers for MontaSpace stress tests."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

COUNTS = (25, 50, 100)
TIMING_KEYS = (
    'generate_seconds', 'insert_seconds', 'linked_save_seconds',
    'portable_save_seconds', 'linked_open_seconds', 'portable_open_seconds',
)
FIELDS = ('version', 'images', 'image_dimensions', 'working_set_after_insert_mb',
          'working_set_after_test_mb', 'peak_working_set_mb', 'private_memory_mb',
          'linked_size_mb', 'portable_size_mb', *TIMING_KEYS)


def validate_count(count: int) -> int:
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError('Image count must be an integer from 1 to 100')
    return count


def validate_report(data: dict, expected_count: int) -> None:
    if not isinstance(data, dict):
        raise ValueError('Benchmark output must be a JSON object')
    if data.get('images') != expected_count or type(data.get('images')) is not int:
        raise ValueError(f'Wrong image count in report (expected {expected_count})')
    if not isinstance(data.get('version'), str) or not data['version']:
        raise ValueError('Missing application version')
    for key in TIMING_KEYS:
        v = data.get(key)
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            raise ValueError(f'Invalid or missing timing: {key}')
    for key in ('working_set_after_insert_mb', 'working_set_after_test_mb',
                'peak_working_set_mb', 'private_memory_mb', 'linked_size_mb',
                'portable_size_mb'):
        v = data.get(key)
        if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v < 0):
            raise ValueError(f'Invalid memory/size value: {key}')
    if data.get('linked_size_mb') is None or data.get('portable_size_mb') is None:
        raise ValueError('Project sizes must be recorded')


def save_summary(reports: list[dict], folder: Path, timestamp: str) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / f'MontaSpace_Stress_Summary_{timestamp}.json'
    csv_path = folder / f'MontaSpace_Stress_Summary_{timestamp}.csv'
    json_path.write_text(json.dumps(reports, indent=2) + '\n', encoding='utf-8')
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(reports)
    return json_path, csv_path
