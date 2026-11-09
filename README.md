# MontaSpace

**Version:** 0.7.3 (development build)  
**Developer / Publisher:** BC Shin Studio  
**Website:** https://www.bcshinstudio.com  
**Copyright:** © 2026 BC Shin Studio. All rights reserved.

MontaSpace is a lightweight, frameless Windows visual workspace for arranging pictures freely. Video support is planned for a future version.

## Features

- Insert or drag/drop JPG, PNG, BMP, and WebP images.
- Move, resize, rotate, crop, and arrange overlapping image layers.
- Undo, redo, duplicate and select all images.
- Save linked projects (`.mspace`) or portable projects with embedded images (`.mspacepack`).
- Right-click anywhere on the whiteboard for file commands, image actions, **About MontaSpace**, and **Performance Info**.

## Developer setup

Place the package contents in a folder such as `C:\Users\baech\Projects\montaspace`. Keep your existing `.venv/` if already installed. Otherwise:

```cmd
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## Build a portable Windows executable

Run `build_windows.bat` **on Windows as a developer**. It uses PyInstaller to produce `dist\MontaSpace\MontaSpace.exe`. Distribute the **entire** `dist\MontaSpace` directory, including `_internal`; it is not a one-file installer. End users do not need this `.bat` file or Python.

The build script embeds the MontaSpace `.ico` as the executable icon and embeds `windows_version_info.txt` as Windows Explorer file metadata (Company, Product, File Version and Copyright). The same icon is applied to the application window and taskbar through PySide6. Taskbar or shortcut icon display can be subject to Windows caching and must be tested on Windows.

### Where the icon is used

- `assets/MontaSpace.ico` — the **one** visual branding asset in this source package.
- During source runs: window/taskbar icon in the Qt application.
- After EXE build: EXE file icon, application/taskbar icon.
- No photographs, promotional collages, banners, splash screens or extra interface decorations are bundled or displayed.

## BC Shin Studio and rights

MontaSpace was developed by **BC Shin Studio**.

**© 2026 BC Shin Studio. All rights reserved.**

This notice applies to the MontaSpace software and project materials to the extent legally protectable. It does not claim ownership of user-imported images or third-party components. Users retain ownership and responsibility for images they insert. The program's name should be cleared for trademark conflicts before public release; a copyright notice alone does not establish trademark rights.

The application uses Python and PySide6/Qt, which have separate licenses. Before redistribution, review PySide6/Qt licensing obligations (including relevant LGPL provisions) and distribute applicable third-party notices/licenses. This development package is not a legal clearance or a complete public-release compliance bundle.

## Files to keep

- `main.py` — application
- `assets/MontaSpace.ico` — launcher icon
- `README.md` — project information
- `requirements.txt` — dependencies
- `windows_version_info.txt` — Windows EXE metadata
- `build_windows.bat` — developer build tool
- `.gitignore` — optional Git exclusions
- `.venv/` — your existing Python environment (not distributed)

Generated `build/`, `dist/`, and `MontaSpace.spec` can be recreated. Do not delete original photos or `.mspace`/`.mspacepack` projects when cleaning generated output.

## Version history

- **0.7.3** — BC Shin Studio attribution in application and README; Windows EXE file-property metadata; launcher icon packaging.
- **0.7.2** — branded About dialog and runtime icon integration.
- **0.7.1** — fixed Windows process RAM reporting.

**Status:** Python syntax validated; Windows GUI and PyInstaller output must be tested on a Windows machine.
