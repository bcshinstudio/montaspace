# MontaSpace v0.8.5 / Studio v0.6.1 synchronization audit

## Inputs and scope
- Original photo-only ZIP `montaspace(2).zip` (v0.8.4 snapshot)
- Studio ZIP `montaspace2(3).zip` (v0.6.1 snapshot)
- Reconstructed v0.8.5 from the prior full regression ZIP, memory import patch, GUI diagnostics fix, stress-test suite and release-preparation patch.
- User-provided Windows test logs: regression 16/16, stress 25/50/100, build succeeded and six installation checks passed **before** this installer-metadata correction.

## Comparison matrix
| Area | Category | Observation / outcome |
|---|---|---|
| Image preview, resize/crop and edge geometry | Shared | `image_item.py`, `imaging.py`, `edit_handles.py`, `edge_hit.py`, and `history.py` match Studio source byte-for-byte in v0.8.5. |
| Main whiteboard controls | Shared with adaptations | `canvas.py` / `window.py` differ because Studio manages videos, player state, native Qt playback and additional gestures. The feature-by-feature parity of every GUI gesture is not certified by source identity alone. Existing six GUI tests + user manual tests cover principal image workflows. |
| Project persistence | Intentional difference | `.mspace`/`.mspacepack` must remain distinct from Studio `.mstudio`/`.mstudiopack`. Studio's missing-media relocation helpers are not safely transferable without GUI and format-specific integration. |
| Persistent video thumbnail cache | Studio-only | Studio uses `video_poster.py` and optional uninstall cache cleanup. Original photo-only MontaSpace does not create that video cache. No cache cleanup checkbox added. |
| Installer identity / metadata | Shared gap corrected | Added `InstallLocation` HKCU registry field; other version metadata previously corrected for v0.8.5. |
| Installer/uninstall verification | Shared gap corrected | Added app-specific read-only `verify_uninstall.bat` and 5 installer contract checks. Automated preflight now requires these files. |
| Performance statistics | Shared, adapted | `memory_private_mb` brought over earlier; Windows stress reports passed 25/50/100. Linux/macOS measurements not verified. |
| Studio video playback, A/B looping, thumbnails, decoder, volume, timeline | Studio-only | Not appropriate for original image-only MontaSpace. |
| Studio resize overlay rewrite | Deferred, not silently copied | Studio uses a custom paint-based `ResizeHint` and extra canvas/window integration. Direct copy would break original's QWidget-based overlay. A separate design/test effort would be necessary if a corresponding defect is observed. |
| macOS and Linux | Not certified | Platform-specific build, path, install and GUI checks remain future work. |

## Quality gates
1. Run static compile and Qt-free tests; run mandatory GUI and installer contract tests on Windows.
2. Build fresh installer only after preflight and regression tests pass.
3. Verify install, start, About, linked/portable open-save, app diagnostics, uninstall and read-only uninstall checker.
4. Validate external project files survive uninstall/reinstall; do not store projects inside installer-owned install directory.
5. Do not publish until the **new** installer (not the previous one) passes these checks.

## Open issues / caveats
- This audit covers inspected shared modules, installer scripts, tests, and source-level feature differences. It is not proof of full functional parity; differences involving video and GUI event handling need platform verification.
- `RMDir /r "$INSTDIR"` recursively deletes the application's installation folder. This is standard for an application-owned directory but users must not save projects inside it.
- Native uninstall registry/shortcut checks are Windows-only and must be run after uninstall on a real PC.
- Windows 0.8.5 build logs from the previous installer do not certify the installer rebuilt with the new registry metadata.
- The source ZIPs include large local virtual environments; they are intentionally excluded from the deliverable.

- Added a Qt-free static import-contract test so missing local imports such as `memory_private_mb` fail before packaging.
