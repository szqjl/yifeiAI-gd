@echo off
REM Phase 5: 将工作目录设为仓库根（从 scripts\launchers\ 任意子目录调用）
set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"
