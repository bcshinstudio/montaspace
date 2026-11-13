@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo FAIL: Missing .venv\Scripts\python.exe
  exit /b 2
)
".venv\Scripts\python.exe" -m unittest discover -s tests -p test_stress_tools.py
if errorlevel 1 (
  echo FAIL: Stress-tool unit tests did not pass.
  exit /b 1
)
".venv\Scripts\python.exe" "tools\run_stress_suite.py" %*
if errorlevel 1 (
  echo FAIL: Stress suite did not pass. See failure above.
  exit /b 1
)
echo PASS: All three MontaSpace stress scenarios passed.
exit /b 0
