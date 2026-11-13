@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo FAIL: Missing .venv\Scripts\python.exe
  exit /b 2
)
set "COUNT=%~1"
if "%COUNT%"=="" set "COUNT=25"
".venv\Scripts\python.exe" "tools\stress_test.py" %COUNT%
if errorlevel 1 (
  echo FAIL: Stress test did not pass.
  exit /b 1
)
echo PASS: %COUNT%-image stress test completed.
exit /b 0
