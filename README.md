# MontaSpace v0.8.5 — Photo-only workspace

MontaSpace is the lightweight image-only edition of MontaSpace Studio, published by BC Shin Studio. It does not require video decoding or multimedia libraries.

## Improvements brought over from Studio
- Eight photo edge/corner editing grips with consistent on-screen sizes at any zoom level.
- Improved edge hit detection and crop handles, while keeping photo rotation.
- Performance Info now includes Windows private committed memory alongside working set, peak and estimated preview pixels.
- Portable and linked project output is verified *before* replacing an existing file; portable archives reject duplicate entries on open.
- New automated regression runner, with Qt-free logic checks and real GUI smoke tests.

## Run and test on Windows

Keep your existing `.venv` virtual environment when copying this update over your project.

```bat
run_regression_tests.bat
run_stress_test.bat 25
run_stress_test.bat 50
run_stress_test.bat 100
.venv\Scripts\python.exe main.py
```

A missing PySide6 installation, failed test, or timeout makes the regression runner exit unsuccessfully. Tests use disposable images and projects. See `docs/AUTOMATED_REGRESSION_TESTS.md`.

## Windows installer

After completing Windows regression and stress tests, install free NSIS and PyInstaller in your existing `.venv`, then run `build_installer.bat`. The build verifies release metadata, reruns regressions, and retains the standalone build for inspection. Output: `installer-output\MontaSpace_Setup_0.8.5.exe`. Windows packaging cannot run in a Linux-only environment.

## Project compatibility

`.mspace` and `.mspacepack` project formats are **unchanged**. MontaSpace remains image-only. Studio video project formats are distinct (`.mstudio`, `.mstudiopack`).

Version 0.8.5 is a **candidate for Windows validation**, not a certified public release.

## Release readiness

Run `.venv\Scripts\python.exe tools\verify_release.py` to check version consistency. Complete `docs/testing/INSTALLER_TEST_CHECKLIST.txt` before GitHub publication.
