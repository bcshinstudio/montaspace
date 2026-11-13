# MontaSpace v0.8.5 — Automated regression testing

Run `run_regression_tests.bat` from the Windows project root using the existing PySide6 `.venv`.

**Qt-free tests** (`test_pure_reliability.py`): edge/corner geometry, tiny rectangles, linked/portable project verification, duplicate/missing archive members, incorrect formats and invalid JSON. Run on any Python 3.11+ with `python -m unittest discover -s tests -p test_pure_*.py -v`.

**Real GUI tests** (`test_gui_whiteboard.py`): photo insert, Undo/Redo, crop/rotate, duplicate, shared preview storage, linked/portable save and reload, and New. Creates temporary images and projects only. The runner uses offscreen Qt and **fails** if PySide6 is missing (it will not report GUI tests as PASS).

**Stress benchmark**: the existing `run_stress_test.bat 25`, `50`, `100` tests cover large boards, save/load and memory measurement.

**Manual release checks on Windows:** interactive corner/edge crop and resize, rotation handle, context menus/overlapping photos, linked and portable file dialogs, reopening an older project, installer launch/uninstall, and the resulting UI at different display scaling. Test on a Mac separately when macOS packaging work begins.

The provided package was checked in a Linux environment without PySide6: pure tests and syntax checks could run, real Qt tests and Windows installer checks could not. Do not label it fully tested until those Windows checks pass.
