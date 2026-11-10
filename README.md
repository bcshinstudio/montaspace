# MontaSpace v0.8.3 — Step 10 Windows installer

This package is the full v0.8.1 tested source plus the NSIS installer build kit.
The application version was increased to v0.8.3 only for installer distribution;
no project format or editing behavior was intentionally changed.

## Installation on your development machine
1. **Back up** `C:\Users\baech\Projects\montaspace` or commit your current changes.
2. Close MontaSpace. Extract/copy this package's **contents** into the existing project folder.
   Do not delete `.git` or `.venv`, and do not copy ZIP contents one folder too deep.
3. Double-click **build_installer.bat** in the MontaSpace folder.
   It runs PyInstaller then the installed NSIS compiler.
4. Output: `installer-output\MontaSpace_Setup_0.8.3.exe`.
5. Run the output setup, select optional desktop shortcut, and test per
   `INSTALLER_TEST_CHECKLIST.txt`.

Installer: per-user directory `%LOCALAPPDATA%\Programs\MontaSpace` with no
administrator permissions normally needed; Windows Settings uninstaller and Start
menu shortcut. It does **not** install Python on a target PC: PyInstaller bundles
app dependencies into the executable folder within the installer.

Project files (`.mspace`, `.mspacepack`) saved elsewhere (e.g. Documents) are not
removed by uninstall. Do not save personal projects inside the application install
folder, since uninstall removes that folder and all its contents.

This installer is **unsigned**; SmartScreen may warn on download. Do not advise
others to bypass warnings. Proper code signing is a separate public-release step.

NSIS and PyInstaller can build the installer without an NSIS commercial license.

### Testing limitations
Python source and archive can be syntax/integrity checked here. The Windows NSIS
compiler and PyInstaller build must be run and validated on your Windows machine.
Do not tag/publish v0.8.3 until Windows installer/uninstaller tests pass.


## v0.8.3: Resizing and window usability

- Resize from all four edges and all four corners; corners are easier to grab.
- Move the pointer near the border to see the appropriate resize cursor and a
  subtle blue edge/corner indicator. No permanent frame is added.
- Alt + left-drag moves the window; right-click still opens the image menu.
- Existing projects and image editing workflows remain unchanged.

Windows GUI behavior needs to be validated on your PC before creating a new installer.
