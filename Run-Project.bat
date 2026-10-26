@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        ".venv\Scripts\python.exe" run_project.py %1
        exit /b
    )
)
set "PLANNER_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PLANNER_PYTHON%" (
    "%PLANNER_PYTHON%" run_project.py %1
    exit /b
)
echo A working Python environment is required. Follow README.md to create .venv.
exit /b 1
