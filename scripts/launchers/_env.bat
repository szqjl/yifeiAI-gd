@echo off
REM Set working directory to repo root (called from scripts\launchers\*)
set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"

REM Activate venv if available (PyTorch etc. are installed here)
if exist "%REPO_ROOT%\venv\Scripts\activate.bat" (
    call "%REPO_ROOT%\venv\Scripts\activate.bat"
)
