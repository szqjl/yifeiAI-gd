@echo off
call "%~dp0..\_env.bat"
REM V7 Auto Start Script - Ultimate Win Rate Model

echo ========================================
echo V7 System Auto Start - Ultimate Win Rate
echo ========================================
echo.

REM Check if model exists
if not exist "models\bc_model_ultimate_win_rate.pth" (
    echo [WARNING] Ultimate win rate model not found!
    echo Model path: models\bc_model_ultimate_win_rate.pth
    echo Will use rule engine as fallback
    echo.
)

REM Check if server is running
echo Checking server status...
netstat -an | findstr 23456 > nul
if %errorlevel% neq 0 (
    echo [START] Server not running, starting server...
    echo.
    if defined SERVER_EXE (
        start "Guandan Server" cmd /k ""%SERVER_EXE%" 10"
    ) else (
        start "Guandan Server" cmd /k "cd /d %REPO_ROOT%\offline_platform\guandan_offline_v1006\windows && guandan_offline_v1006.exe 10"
    )
    echo Waiting for server startup (15 seconds)...
    timeout /t 15 /nobreak > nul
    echo.
) else (
    echo [OK] Server is running
    echo.
)

REM Start clients
echo Starting V7 clients...
call "%~dp0START_V7_CLIENTS.bat"

echo.
echo ========================================
echo V7 System Started!
echo ========================================
echo.
echo System Info:
echo   - Server: 127.0.0.1:23456
echo   - Team A: yf1_v7 + yf2_v7 (Ultimate Win Rate)
echo   - Team B: lalala client3 + client4
echo   - Model: bc_model_ultimate_win_rate.pth
echo.
echo Press any key to close...
pause > nul