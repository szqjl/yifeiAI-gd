@echo off
REM V8 Client Start Script - Room-based startup (CREATE_ROOM → JOIN_ROOM)

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
cd /d "%REPO%"

echo ========================================
echo V8 Client Startup - Ultimate Win Rate (OpenGuanDan)
echo ========================================
echo.
echo Startup Order (room-based):
echo   1. yf1_v8     (CREATE_ROOM → seat 0)
echo   2. yf2_v8     (JOIN_ROOM  → seat 2)  [Team: yf1 + yf2]
echo   3. client3    (JOIN_ROOM  → seat 1)  [Team: lalala]
echo   4. client4    (JOIN_ROOM  → seat 3)  [Team: lalala]
echo.
echo Team Assignment:
echo   Team A (0+2): yf1_v8 + yf2_v8 (Ultimate Win Rate)
echo   Team B (1+3): lalala client3 + client4
echo.
echo ========================================
echo.

REM Check server status
echo Checking server status...
netstat -an | findstr "8181" > nul
if errorlevel 1 (
    echo.
    echo [WARNING] Server may not be running!
    echo Please start server first: offline_platform\openguandan_latest\guandan.exe
    echo.
    echo Press any key to continue with client startup, or Ctrl+C to cancel...
    pause > nul
) else (
    echo [OK] Server is running on port 8181
)

echo.
echo Starting clients (room-based)...
echo ========================================
echo.

REM 1. Start yf1_v8 (CREATE_ROOM, seat 0)
echo [1/4] Starting yf1_v8 (CREATE_ROOM, seat 0)...
start "yf1_v8 (Seat 0 - Creator)" cmd /k "cd /d %REPO% && python src/communication/yf1_v8.py --platform openguandan --role creator --games 10"
echo   Waiting 5 seconds for room creation...
timeout /t 5 /nobreak > nul
echo.

REM 2. Start yf2_v8 (JOIN_ROOM, seat 2)
echo [2/4] Starting yf2_v8 (JOIN_ROOM, seat 2)...
start "yf2_v8 (Seat 2)" cmd /k "cd /d %REPO% && python src/communication/yf2_v8.py --platform openguandan --role joiner"
echo   Waiting 3 seconds...
timeout /t 3 /nobreak > nul
echo.

REM 3. Start lalala client3 (JOIN_ROOM, seat 1)
echo [3/4] Starting lalala client3 (JOIN_ROOM, seat 1)...
start "lalala_client3 (Seat 1)" cmd /k "cd /d %REPO% && python src/communication/v8_lalala_adapter.py client3 --platform openguandan --role joiner"
echo   Waiting 3 seconds...
timeout /t 3 /nobreak > nul
echo.

REM 4. Start lalala client4 (JOIN_ROOM, seat 3)
echo [4/4] Starting lalala client4 (JOIN_ROOM, seat 3)...
start "lalala_client4 (Seat 3)" cmd /k "cd /d %REPO% && python src/communication/v8_lalala_adapter.py client4 --platform openguandan --role joiner"
echo.

echo ========================================
echo All clients started!
echo ========================================
echo.
echo Tips:
echo   - yf1_v8 creates room and writes tmp/.v8_room_id
echo   - Other clients read tmp/.v8_room_id and JOIN_ROOM
echo   - Team A (0+2): yf1_v8 + yf2_v8 (Ultimate Win Rate)
echo   - Team B (1+3): lalala client3 + client4
echo   - Check v8_vs_lalala_scores.json for match results
echo.
echo Press any key to close this window...
pause > nul
