@echo off
call "%~dp0..\_env.bat"
REM V8 Auto Start Script - Ultimate Win Rate Model (OpenGuanDan)

echo ========================================
echo V8 System Auto Start - Ultimate Win Rate (OpenGuanDan)
echo ========================================
echo.

REM Check if server is running
echo Checking server status...
netstat -an | findstr "8181" > nul
if errorlevel 1 (
    echo [START] Server not running, starting server...
    echo.
    if defined SERVER_EXE (
        start "Guandan Server (V8)" cmd /k ""%SERVER_EXE%""
    ) else (
        start "Guandan Server (V8)" cmd /k "cd /d "%REPO_ROOT%\offline_platform\openguandan_latest" && guandan.exe"
    )
    echo Waiting for server to listen on port 8181 (15 seconds)...
    timeout /t 15 /nobreak > nul
    echo.
) else (
    echo [OK] Server is running on port 8181
    echo.
)

REM Start clients
echo Starting V8 clients (room-based)...
call "%~dp0START_V8_CLIENTS.bat"

echo.
echo ========================================
echo V8 System Started!
echo ========================================
echo.
echo System Info:
echo   - Server: 127.0.0.1:8181 (guandan.exe)
echo   - Team A: yf1_v8 + yf2_v8 (Ultimate Win Rate)
echo   - Team B: lalala client3 + client4
echo   - Room coordination: tmp/.v8_room_id
echo.
echo Press any key to close...
pause > nul
