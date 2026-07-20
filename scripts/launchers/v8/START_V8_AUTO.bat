@echo off
call "%~dp0..\_env.bat"
REM V8 Auto Start Script - Ultimate Win Rate Model (OpenGuanDan)

echo ========================================
echo V8 System Auto Start - Ultimate Win Rate (OpenGuanDan)
echo ========================================
echo.

REM Check if server is running
echo Checking server status...
netstat -an | findstr 8181 > nul
if %errorlevel% neq 0 (
    echo [START] Server not running, starting server...
    echo.
    if defined SERVER_EXE (
        start "Guandan Server (V8)" cmd /k ""%SERVER_EXE%""
    ) else (
        start "Guandan Server (V8)" cmd /k "cd /d %REPO_ROOT%\offline_platform\openguandan_latest && guandan.exe"
    )
    echo Waiting for server to listen on port 8181 (15 seconds)...
    timeout /t 15 /nobreak > nul
    echo.
) else (
    echo [OK] Server is running on port 8181
    echo.
)

REM Start clients (room-based startup)
echo Starting V8 clients (room-based)...
echo.
echo Startup Order:
echo   1. yf1_v8     (CREATE_ROOM, seat 0)
echo   2. yf2_v8     (JOIN_ROOM,  seat 2)
echo   3. client3    (JOIN_ROOM,  seat 1)
echo   4. client4    (JOIN_ROOM,  seat 3)
echo.

REM 1. yf1_v8 (CREATE_ROOM, seat 0)
echo [1/4] Starting yf1_v8 (CREATE_ROOM, seat 0)...
start "yf1_v8 (Seat 0)" cmd /k "cd /d %REPO_ROOT% && python src/communication/yf1_v8.py --platform openguandan --role creator --games 10"
echo   Waiting 5s for room creation...
timeout /t 5 /nobreak > nul

REM 2. yf2_v8 (JOIN_ROOM, seat 2)
echo [2/4] Starting yf2_v8 (JOIN_ROOM, seat 2)...
start "yf2_v8 (Seat 2)" cmd /k "cd /d %REPO_ROOT% && python src/communication/yf2_v8.py --platform openguandan --role joiner"
echo   Waiting 3s...
timeout /t 3 /nobreak > nul

REM 3. lalala client3 (JOIN_ROOM, seat 1)
echo [3/4] Starting lalala client3 (JOIN_ROOM, seat 1)...
start "lalala_client3 (Seat 1)" cmd /k "cd /d %REPO_ROOT% && python src/communication/v8_lalala_adapter.py client3 --platform openguandan --role joiner"
echo   Waiting 3s...
timeout /t 3 /nobreak > nul

REM 4. lalala client4 (JOIN_ROOM, seat 3)
echo [4/4] Starting lalala client4 (JOIN_ROOM, seat 3)...
start "lalala_client4 (Seat 3)" cmd /k "cd /d %REPO_ROOT% && python src/communication/v8_lalala_adapter.py client4 --platform openguandan --role joiner"

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
