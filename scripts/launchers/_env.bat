@echo off
REM Set working directory to repo root (called from scripts\launchers\*)
set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"
