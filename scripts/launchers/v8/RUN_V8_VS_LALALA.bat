@echo off
call "%~dp0..\_env.bat"
REM V8 vs lalala 批跑 — 新平台 OpenGuanDan (guandan.exe, 端口 8181)
REM 用法: RUN_V8_VS_LALALA.bat [局数]
REM   默认 3；推荐 3 / 9 / 12（须为 3 的倍数）

set "GAMES=3"
if not "%~1"=="" set "GAMES=%~1"

echo ========================================
echo V8 vs lalala 批跑 - %GAMES% 局 (OpenGuanDan)
echo 队伍A: yf1_v8 + yf2_v8 ^| 队伍B: lalala client3 + client4
echo 平台: openguandan (guandan.exe :8181)
echo ========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py "%REPO_ROOT%\scripts\launchers\v8\run_v8_vs_lalala_games.py" --games %GAMES% --platform openguandan
) else (
    python "%REPO_ROOT%\scripts\launchers\v8\run_v8_vs_lalala_games.py" --games %GAMES% --platform openguandan
)

set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
    echo.
    echo [ERROR] 批跑退出码 %EC%
    pause
)
exit /b %EC%
