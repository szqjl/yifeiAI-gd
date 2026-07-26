@echo off
call "%~dp0..\_env.bat"
REM V8 vs V8 自对弈批跑 — 全员 V8 客户端，最强对手压力测试
REM 用法: RUN_V8_VS_V8.bat [局数]
REM   默认 3；推荐 3 / 9 / 12

set "GAMES=3"
if not "%~1"=="" set "GAMES=%~1"

echo ========================================
echo V8 vs V8 自对弈 - %GAMES% 局 (OpenGuanDan)
echo 队伍A: yf1_v8 + yf2_v8 ^& 队伍B: yf1_v8 + yf2_v8（同引擎对撞）
echo 平台: openguandan (guandan.exe :8181)
echo ========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py "%REPO_ROOT%\scripts\launchers\v8\run_v8_vs_v8_games.py" --games %GAMES%
) else (
    python "%REPO_ROOT%\scripts\launchers\v8\run_v8_vs_v8_games.py" --games %GAMES%
)

set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
    echo.
    echo [ERROR] 批跑退出码 %EC%
    pause
)
exit /b %EC%