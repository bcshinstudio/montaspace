# MontaSpace

**Version:** 0.8.1 — Step 9 performance and stability update  
**Publisher:** BC Shin Studio  
**Website:** https://www.bcshinstudio.com  
**Copyright:** © 2026 BC Shin Studio. All rights reserved.

MontaSpace is a lightweight, frameless Windows workspace for freely arranging, resizing, rotating, cropping, and layering images. Video playback remains a future feature.

## Changes from verified v0.8.0

- Reuse already decoded Qt image data when inserting the same photo multiple times; independent crop/transform controls are preserved. Does not create an unbounded background cache.
- Performance Info now includes peak process RAM (since launch) and undo-history entries.
- `run_stress_test.bat` and `tools/stress_test.py`: optional, isolated performance tests generating 25–100 **temporary synthetic images**. Measure image insertion, linked/portable save and reopen times, and RAM. Outputs JSON results to `Documents\MontaSpace_Test_Reports`.
- Updated About/version metadata to 0.8.1. No changes to `.mspace` or `.mspacepack` schema (still format version 1).

## Update instructions

Keep your existing `.git` and `.venv` folders. Close MontaSpace first. Extract ZIP and copy the included files/folders into `C:\Users\baech\Projects\montaspace`, merging existing directories. **Never delete the entire existing folder** to install an update. Preserve any personal saved projects and original photos.

Run: `.venv\Scripts\python.exe main.py`

## Performance testing

Close MontaSpace first, then run these commands from the project directory:

```cmd
run_stress_test.bat 25
run_stress_test.bat 50
```

Optional on a machine with sufficient memory: `run_stress_test.bat 100`

The test creates synthetic JPEGs and temporary test project files in the system temporary directory; it does **not** access personal photos or overwrite user projects. Results are saved as JSON in the Documents folder. Peak working-set measurements are Windows-specific.

The test can briefly use substantial RAM: preview images up to 1600 px per edge are deliberately not reduced further because that might change UI quality. A larger preview and many distinct photographs can consume hundreds of MB or more.

## Features

Drag and drop PNG/JPEG/BMP/WebP; select, move, resize, rotate, Ctrl+wheel resize; non-destructive cropping; overlap-aware layer ordering; Undo/Redo; duplicate, select all, delete; linked and portable projects; frameless window; Windows process memory reporting.

## Windows build

Run `build_windows.bat` to build the optional portable one-folder `dist\MontaSpace` executable. Users receive this full folder, not the build script. Commercial installer planning remains separate.

## Licensing

© 2026 BC Shin Studio. All rights reserved. User-supplied photographs remain their owners' property. Python, PySide6/Qt, and PyInstaller have independent licensing requirements; review these before public redistribution.

## Version history

- **0.8.1**: performance diagnostics, shared previews for repeated image files, opt-in stress test.
- **0.8.0**: verified modular refactor.
- **0.7.3**: publisher/icon stable baseline.
