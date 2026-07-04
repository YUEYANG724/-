@echo off
cd /d "%~dp0"
set PYTHON_EXE=C:\Users\28471\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe

if not exist "%PYTHON_EXE%" (
  echo Python not found: %PYTHON_EXE%
  pause
  exit /b 1
)

start "" http://127.0.0.1:5000/
"%PYTHON_EXE%" app.py
pause
