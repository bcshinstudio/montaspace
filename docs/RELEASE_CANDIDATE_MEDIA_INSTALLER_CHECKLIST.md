# MontaSpace v0.8.6 — Windows installer candidate

This source is not a published release. The user has already tested development-environment media decoding and editing. Installer-bound regression is **not** yet verified.

1. Keep your existing `.venv` and `.git` when copying source updates into your Windows project. Do not copy over or delete them.
2. From project folder: `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. Run `run_regression_tests.bat` and ensure **no skipped required GUI tests**.
4. Run `build_installer.bat`. The script verifies image decoder availability; runs regression tests; bundles pillow-heif; builds NSIS installer; checks presence and minimal size; then removes only generated `build/` and `dist/` directories. On failure those directories remain for diagnostics.
5. Verify installer in `installer-output/` is the correct version and does not conflict with previous versions. Install and launch **the installed executable**, not `main.py`.
6. Import JPEG, PNG, BMP, WebP, GIF (first frame), TIFF, HEIC and AVIF, including via drag-and-drop. Verify image editing and linked/portable save/reopen using installed app.
7. Confirm uninstall removes application files without deleting media projects.
8. Confirm `installer-output/` retains the installer; `build/` and `dist/` are absent after successful build. Test a deliberately failing prerequisite separately and ensure source is untouched.
9. Record results and SHA-256 checksums. Do not publish or replace GitHub release before actual installed-app testing passes.
