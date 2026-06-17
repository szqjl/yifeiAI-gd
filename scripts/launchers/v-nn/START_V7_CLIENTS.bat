@echo off
call "%~dp0..\_env.bat"
REM V7 Client Start Script - Sequential startup for proper team assignment
REM Using Ultimate Win Rate Model

echo ========================================
echo V7 Client Startup - Ultimate Win Rate
echo ========================================
echo.
echo Startup Order (for team assignment):
echo   1. yf1_v7      (1st connect -^> Position 0)
echo   2. client3     (2nd connect -^> Position 1)
echo   3. yf2_v7      (3rd connect -^> Position 2)
echo   4. client4     (4th connect -^> Position 3)
echo.
echo Team Assignment:
echo   Team A (0+2): yf1_v7 + yf2_v7 (Ultimate Win Rate)
echo   Team B (1+3): lalala client3 + client4
echo.
echo ========================================
echo.

REM Check server status
echo Checking server status...
netstat -an | findstr "23456" > nul
if errorlevel 1 (
    echo.
    echo [WARNING] Server may not be running!
    echo Please start server first: server\guandan_offline_v1006.exe 10
    echo.
    echo Press any key to continue with client startup, or Ctrl+C to cancel...
    pause > nul
) else (
    echo [OK] Server is running
)

echo.
echo Starting clients...
echo ========================================
echo.

REM 1. Start yf1_v7 (Position 0)
echo [1/4] Starting yf1_v7 (Target: Position 0)...
start "yf1_v7 (Pos 0)" cmd /k "cd /d %REPO_ROOT% && python src/communication/yf1_v7.py"
echo   Waiting 3 seconds...
timeout /t 3 /nobreak > nul
echo.

REM 2. Start lalala client3 (Position 1)
echo [2/4] Starting lalala client3 (Target: Position 1)...
start "lalala_client3 (Pos 1)" cmd /k "cd /d %REPO_ROOT% && python src/communication/run_lalala_client3.py"
echo   Waiting 3 seconds...
timeout /t 3 /nobreak > nul
echo.

REM 3. Start yf2_v7 (Position 2)
echo [3/4] Starting yf2_v7 (Target: Position 2)...
start "yf2_v7 (Pos 2)" cmd /k "cd /d %REPO_ROOT% && python src/communication/yf2_v7.py"
echo   Waiting 3 seconds...
timeout /t 3 /nobreak > nul
echo.

REM 4. Start lalala client4 (Position 3)
echo [4/4] Starting lalala client4 (Target: Position 3)...
start "lalala_client4 (Pos 3)" cmd /k "cd /d %REPO_ROOT% && python src/communication/run_lalala_client4.py"
echo.

echo ========================================
echo All clients started!
echo ========================================
echo.
echo Tips:
echo   - Check each window to confirm position assignment
echo   - Expected: yf1_v7=Pos0, client3=Pos1, yf2_v7=Pos2, client4=Pos3
echo   - Team A (0+2): yf1_v7 + yf2_v7 (Ultimate Win Rate)
echo   - Team B (1+3): lalala client3 + client4
echo   - Check game_scores.json or use GUI for match results
echo.
echo Press any key to close this window...
pause > nul