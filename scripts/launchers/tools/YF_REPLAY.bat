@echo off
call "%~dp0..\_env.bat"
chcp 65001 >nul 2>&1

echo ========================================
echo YiFei AI Replay GUI
echo ========================================
echo.

py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python and add to PATH.
    pause
    exit /b 1
)

py -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tkinter not available.
    pause
    exit /b 1
)

REM Usage: YF_REPLAY.bat "game_records\<game_id> [yf1_m3]-[opponent_1_3]-[1]-[2].json"
REM Note: space required between game_id and [yf1_m3]
py scripts/tools/yf_replay.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
    echo.
    echo [ERROR] Replay failed with exit code %EXITCODE%
    pause
)
exit /b %EXITCODE%
