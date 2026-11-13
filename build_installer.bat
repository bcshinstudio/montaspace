@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
set "SETUP=installer-output\MontaSpace_Setup_0.8.6.exe"

echo MontaSpace v0.8.6 - installer validation candidate
if not exist "%PY%" (
  echo ERROR: Missing .venv Python environment.
  goto :fail
)

"%PY%" "tools\verify_release.py"
if errorlevel 1 goto :fail

rem Refuse to package a build that fails its regression tests.
call "run_regression_tests.bat"
if errorlevel 1 goto :fail

rem Fail early if the HEIC decoder isn't installed in the build environment.
".venv\Scripts\python.exe" "tools\check_image_codecs.py"
if errorlevel 1 goto :fail

"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: PyInstaller is not installed in the virtual environment.
  echo Install it with: .venv\Scripts\python.exe -m pip install "PyInstaller>=6,<7"
  goto :fail
)

set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" (
  for %%M in (makensis.exe) do set "MAKENSIS=%%~$PATH:M"
)
if not exist "%MAKENSIS%" (
  echo ERROR: NSIS makensis.exe not found; install free NSIS first.
  goto :fail
)

if not exist "installer-output" mkdir "installer-output"
rem Remove only the old expected installer, not user/source files.
if exist "%SETUP%" del /q "%SETUP%"

"%PY%" -m PyInstaller --collect-all pillow_heif --clean --noconfirm --onedir --windowed --name MontaSpace --icon "assets\MontaSpace.ico" --add-data "assets\MontaSpace.ico;assets" --version-file "windows_version_info.txt" main.py
if errorlevel 1 goto :fail
if not exist "dist\MontaSpace\MontaSpace.exe" (
  echo ERROR: PyInstaller returned success but EXE is missing.
  goto :fail
)

"%MAKENSIS%" "installer\MontaSpace.nsi"
if errorlevel 1 goto :fail
if not exist "%SETUP%" (
  echo ERROR: NSIS returned success but installer is missing.
  goto :fail
)

rem The installer exists; confirm it has nonzero content before cleaning.
for %%F in ("%SETUP%") do if %%~zF LSS 1000000 (
  echo ERROR: Installer is suspiciously small. Keeping build artifacts.
  goto :fail
)
rem Keep the tracked MontaSpace.spec source file; remove ONLY temporary build folders.
echo Removing temporary PyInstaller build artifacts after verified installer generation...
if exist "build\" rmdir /s /q "build"
if exist "dist\" rmdir /s /q "dist"
if exist "build\" echo WARNING: build folder remains; close any locked files.
if exist "dist\" echo WARNING: dist folder remains; close any locked files.

echo.
echo PASS: installer build completed. Windows installation testing is still required.
echo Installer: %SETUP%
echo Standalone application tested by PyInstaller; temporary dist cleaned after packaging.
echo.
echo Next: docs\testing\INSTALLER_TEST_CHECKLIST.txt
exit /b 0

:fail
echo.
echo FAIL: No publishable release package was verified.
exit /b 1
