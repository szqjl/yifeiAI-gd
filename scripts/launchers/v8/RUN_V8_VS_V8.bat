@echo off
call "%~dp0..\_env.bat"
REM V8 vs V8 self-play batch run
REM Usage: RUN_V8_VS_V8.bat [games]
REM   default 3; recommended 3 / 9 / 12

set "GAMES=3"
if not "%~1"=="" set "GAMES=%~1"

echo ========================================
echo V8 vs V8 self-play - %GAMES% games (OpenGuanDan)
echo TeamA: yf1_v8 + yf2_v8 ^| TeamB: yf1_v8 + yf2_v8 (same engine collision)
echo Platform: openguandan (guandan.exe :8181)
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
    echo [ERROR] batch exit code %EC%
    pause
)
exit /b %EC%