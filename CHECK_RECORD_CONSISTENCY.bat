@echo off
REM 游戏记录一致性检查工具
cd /d "%~dp0"
if "%1"=="" (
    python check_game_record_consistency.py
) else (
    python check_game_record_consistency.py "%1"
)
pause

