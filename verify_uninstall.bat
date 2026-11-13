@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
rem Read-only checks. Usage: verify_uninstall.bat ["custom-install-folder"]
rem No application data or user projects will be deleted by this tool.
set "CUSTOM_DIR=%~1"
set "FAIL=0"
echo === MontaSpace uninstallation verification ===
call :checkdir "%LOCALAPPDATA%\Programs\MontaSpace" "Default installation folder"
if defined CUSTOM_DIR call :checkdir "%CUSTOM_DIR%" "Custom installation folder"
call :checkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\MontaSpace" "Start Menu shortcuts"
call :checkfile "%USERPROFILE%\Desktop\MontaSpace.lnk" "User Desktop shortcut"
call :checkfile "%PUBLIC%\Desktop\MontaSpace.lnk" "Public Desktop shortcut"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\MontaSpace" >nul 2>&1
if not errorlevel 1 (
  echo FAIL: Uninstall registry entry still exists.
  set "FAIL=1"
) else (
  echo PASS: Uninstall registry entry absent.
)
if "%FAIL%"=="0" (
  echo PASS: Checked uninstall locations are clean.
) else (
  echo FAIL: Some checked locations remain.
)
exit /b %FAIL%
:checkdir
if exist "%~1\" (
  echo FAIL: %~2 remains: "%~1"
  set "FAIL=1"
) else (
  echo PASS: %~2 absent.
)
exit /b 0
:checkfile
if exist "%~1" (
  echo FAIL: %~2 remains: "%~1"
  set "FAIL=1"
) else (
  echo PASS: %~2 absent.
)
exit /b 0
