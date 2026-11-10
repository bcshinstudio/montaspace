# MontaSpace

**Version:** 0.8.0 — Step 8 structural refactor (Windows verification pending)  
**Developer / Publisher:** BC Shin Studio  
**Website:** https://www.bcshinstudio.com  
**Copyright:** © 2026 BC Shin Studio. All rights reserved.

MontaSpace is a lightweight, frameless Windows visual workspace for arranging images. Video support remains planned, not implemented.

## What's changed in Step 8

Only internal organization and version metadata were intentionally changed. The v0.7.3 behavior should remain unchanged; this **has not yet been confirmed on Windows**.

- `main.py`: minimal application launcher
- `app/window.py`: frameless Qt window, shortcuts, About and diagnostics
- `app/canvas.py`: whiteboard scene, context menu, layers, drop handling
- `app/image_item.py`: move / resize / rotate / non-destructive crop
- `app/project.py`: existing `.mspace` / `.mspacepack` format, unchanged (`version: 1`)
- `app/history.py`: Undo/Redo state snapshots
- `app/imaging.py`: preview image decoding
- `app/performance.py`: working-set measurement
- `app/config.py`: settings, version, icon asset path

## Installation into your local project

**Do not delete your old project folder.** First create a backup or use Git to preserve v0.7.3. Close MontaSpace. Copy the ZIP's contents *into* `C:\Users\baech\Projects\montaspace`, replacing matching files, and **keep the existing `.venv` folder and `.git` folder**. The ZIP contains neither. Existing `.mspace` and `.mspacepack` files or original photos should never be deleted.

To run on Windows:

```cmd
cd C:\Users\baech\Projects\montaspace
.venv\Scripts\python.exe main.py
```

If dependencies are missing:

```cmd
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Features retained from v0.7.3

- JPG, PNG, BMP, WebP insertion (file picker and drag/drop)
- Frameless window movement (Alt+drag) and native edge resizing
- Individual image move, resize, rotate, Ctrl+wheel scaling
- Non-destructive crop; overlapping-image selection and layer arrangement
- Undo/Redo, duplicate, select all and delete
- Linked `.mspace` and portable `.mspacepack` projects
- About and Performance Info dialogs
- BC Shin Studio credits and Windows application icon

## Test before committing

1. Launch, inspect About (0.8.0), and verify the icon and memory reporting.
2. Insert photos; move, resize, rotate, Ctrl+wheel zoom, crop and recrop.
3. Test overlapping image selection, front/back ordering and crop priority.
4. Undo/Redo, duplicate, select all and delete.
5. Open **existing v0.7.3** `.mspace` and `.mspacepack` files.
6. Save new linked and portable projects, close and reopen them.
7. Test unsaved-change confirmation when closing, New, and Open.
8. After above pass, run `build_windows.bat` to build `dist\MontaSpace\MontaSpace.exe` and test separately.

## Packaging

`build_windows.bat` uses PyInstaller on Windows to create a portable **one-folder** executable. The full `dist\MontaSpace` folder is needed for distribution. This is not a Windows installer. The EXE uses `assets\MontaSpace.ico` and `windows_version_info.txt` (version 0.8.0).

## Licensing and project rights

© 2026 BC Shin Studio. All rights reserved. User-supplied images are not owned by BC Shin Studio. Python, PySide6/Qt and PyInstaller have independent licenses; review applicable redistribution obligations before a public release. Trademark clearance and code signing are separate steps.

## Version history

- **0.8.0** — Split the monolithic application into modules; no planned behavior changes.
- **0.7.3** — Publisher attribution, Windows EXE metadata, official icon, working baseline tagged in Git.

## Git tip

Do not replace the `.git` directory. After Windows tests pass, check `git status`, then commit the new modules. Do **not** overwrite the existing `v0.7.3` Git tag.
