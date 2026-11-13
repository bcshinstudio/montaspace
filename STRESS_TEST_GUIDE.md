# MontaSpace v0.8.5 — Performance Stress Test

Keep .venv and .git. Extract the patch into your existing MontaSpace project folder.

## All three sizes (recommended)

    run_stress_suite.bat

Runs 25, 50 and 100 synthetic 1800x1200 JPEG images. Each size is measured in a new
Python process to avoid memory carryover. Uses temporary files and does not touch
personal images or project files. Tests insertion, linked/portable project save and
reopen, image count and saved transforms. Any error fails the run.

Reports (JSON and CSV) are written to:

    %USERPROFILE%\Documents\MontaSpace_Test_Reports

## Single size

    run_stress_test.bat 25

This prints a report to the console but does not save a report file. For saved reports,
use the full suite.

## Report fields

Time fields are measured wall-clock seconds, including disk activity. Memory metrics
are Windows process measurements. null means the OS did not provide that metric.
These numbers are not a universal pass/fail threshold: compare identical counts and
machine conditions with a previous version. Disk, CPU, RAM and OS caching influence
results. Automated PASS confirms correctness for the scenarios, not performance parity
with Studio nor all manual GUI behavior.

## Qt-free tooling tests

    .venv\Scripts\python.exe -m unittest discover -s tests -p test_stress_tools.py -v

This runner intentionally fails if its child test fails, skips the report, or writes
invalid metrics. GUI stress execution requires installed PySide6 on Windows.
