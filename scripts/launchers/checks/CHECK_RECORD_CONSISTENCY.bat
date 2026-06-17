@echo off
call "%~dp0..\_env.bat"
REM 游戏记录一致性检查工具
if "%1"=="" (
    python scripts/checks/check_game_record_consistency.py
) else (
    python scripts/checks/check_game_record_consistency.py "%1"
)
pause

