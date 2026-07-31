@echo off
chcp 65001 >nul
call "%~dp0..\_env.bat"
REM v7Dan vs DanZero 批跑 — 真身；根目录 RUN_V7DAN_VS_DANZERO.bat 为 stub
REM 用法: RUN_V7DAN_VS_DANZERO.bat [局数]
REM   默认 3；推荐 3 / 9 / 12（须为 3 的倍数）
REM   队A: yf1_v7dan + yf2_v7dan（v7 引擎 v7Dan 身份）
REM   队B: DanZero client3 + client4（未接模型时为占位策略）

set "GAMES=3"
if not "%~1"=="" set "GAMES=%~1"

echo ========================================
echo v7Dan vs DanZero 批跑 - %GAMES% 局
echo 队伍A: yf1_v7dan + yf2_v7dan ^| 队伍B: DanZero client3 + client4
echo ========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py "%REPO_ROOT%\scripts\launchers\v7dan\run_v7dan_vs_danzero_games.py" --games %GAMES%
) else (
    python "%REPO_ROOT%\scripts\launchers\v7dan\run_v7dan_vs_danzero_games.py" --games %GAMES%
)

set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
    echo.
    echo [ERROR] 批跑退出码 %EC%
    pause
)
exit /b %EC%
