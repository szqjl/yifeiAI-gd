@echo off
call "%~dp0..\_env.bat"
chcp 65001 >nul
REM V7 Ultimate Win Rate GUI - Complete System Startup
REM Auto-start server and configure V7 vs lalala battle

echo ========================================
echo V7 Ultimate Win Rate GUI - One-Click Start
echo ========================================
echo.
echo Battle Config:
echo   Team A: yf1_v7 + yf2_v7 (Ultimate Win Rate Engine)
echo   Team B: lalala client3 + client4
echo   Model: bc_model_ultimate_win_rate.pth (84.3%% score)
echo.

REM Check model status
if exist "models\bc_model_ultimate_win_rate.pth" (
    echo ? Ultimate Win Rate Model: LOADED
) else (
    echo ? Ultimate Win Rate Model: NOT FOUND - Will use rule engine
)
echo.

REM Check and start server
echo Checking server status...
netstat -an | findstr "23456" > nul
if errorlevel 1 (
    echo Starting server...
    start "Guandan Server" /min cmd /c "%REPO_ROOT%\offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe 10"
    timeout /t 8 /nobreak > nul
    echo Server started.
) else (
    echo Server already running.
)
echo.

REM lalala ?????????? LALALA_DIR?? client3.py / client4.py????? run_lalala_client*.py
if defined LALALA_DIR (
    echo Configuring lalala clients for port 23456 in %LALALA_DIR%...
    powershell -Command "(Get-Content '%LALALA_DIR%\client3.py') -replace 'ws://127.0.0.1:9618/game/gd/client1', 'ws://127.0.0.1:23456/game/client3' | Set-Content '%LALALA_DIR%\client3.py'"
    powershell -Command "(Get-Content '%LALALA_DIR%\client4.py') -replace 'ws://127.0.0.1:9618/game/gd/client4', 'ws://127.0.0.1:23456/game/client4' | Set-Content '%LALALA_DIR%\client4.py'"
    echo Clients configured.
) else (
    echo [SKIP] ??? LALALA_DIR?????????? src/communication/run_lalala_client3.py ?
)
echo.

echo Starting V7 Ultimate Win Rate Battle GUI...
echo ========================================

py scripts/v7/start_v7_gui.py

pause