@echo off
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
    echo ✓ Ultimate Win Rate Model: LOADED
) else (
    echo ✗ Ultimate Win Rate Model: NOT FOUND - Will use rule engine
)
echo.

REM Check and start server
echo Checking server status...
netstat -an | findstr "23456" > nul
if errorlevel 1 (
    echo Starting server...
    start "Guandan Server" /min cmd /c "D:\guandanscore\guandan_offline_v1006\windows\guandan_offline_v1006.exe 10"
    timeout /t 8 /nobreak > nul
    echo Server started.
) else (
    echo Server already running.
)
echo.

REM Fix lalala client ports
echo Configuring lalala clients for port 23456...
powershell -Command "(Get-Content 'D:\NYGD\lalala\client3.py') -replace 'ws://127.0.0.1:9618/game/gd/client1', 'ws://127.0.0.1:23456/game/client3' | Set-Content 'D:\NYGD\lalala\client3.py'"
powershell -Command "(Get-Content 'D:\NYGD\lalala\client4.py') -replace 'ws://127.0.0.1:9618/game/gd/client4', 'ws://127.0.0.1:23456/game/client4' | Set-Content 'D:\NYGD\lalala\client4.py'"
echo Clients configured.
echo.

echo Starting V7 Ultimate Win Rate Battle GUI...
echo ========================================

cd /d "%~dp0"
py scripts/v7/start_v7_gui.py

pause