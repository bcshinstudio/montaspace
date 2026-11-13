@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe - create the Python environment first.
  exit /b 2
)
".venv\Scripts\python.exe" "tools\run_regressions.py"
exit /b %errorlevel%
