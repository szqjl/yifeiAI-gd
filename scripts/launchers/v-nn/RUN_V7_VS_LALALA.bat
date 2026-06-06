@echo off
chcp 65001 >nul
call "%~dp0..\_env.bat"
REM V7 vs lalala 批跑 — 真身；根目录 RUN_V7_VS_LALALA.bat 为 stub
REM 用法: RUN_V7_VS_LALALA.bat [局数]
REM   默认 3；推荐 3 / 9 / 12（须为 3 的倍数）

set "GAMES=3"
if not "%~1"=="" set "GAMES=%~1"

echo ========================================
echo V7 vs lalala 批跑 - %GAMES% 局
echo 队伍A: yf1_v7 + yf2_v7 ^| 队伍B: lalala client3 + client4
echo ========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py "%REPO_ROOT%\run_v7_vs_lalala_games.py" --games %GAMES%
) else (
    python "%REPO_ROOT%\run_v7_vs_lalala_games.py" --games %GAMES%
)

set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
    echo.
    echo [ERROR] 批跑退出码 %EC%
    pause
)
exit /b %EC%
