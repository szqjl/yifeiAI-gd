@echo off
call "%~dp0..\_env.bat"
REM V7 Auto Start Script - Ultimate Win Rate Model

echo ========================================
echo V7 System Auto Start - Ultimate Win Rate
echo ========================================
echo.

if exist "%REPO_ROOT%\models\bc_model_ultimate_win_rate.pth" (
    echo [OK] Model found: models\bc_model_ultimate_win_rate.pth
) else if exist "%REPO_ROOT%\models\v-nn\bc_model_ultimate_win_rate.pth" (
    echo [OK] Model found: models\v-nn\bc_model_ultimate_win_rate.pth
) else (
    echo [WARNING] Ultimate win rate model not found - rule fallback
    echo.
)

echo Checking server status...
netstat -an | findstr "23456" > nul
if errorlevel 1 (
    echo [START] Server not running, starting server...
    echo.

    if defined SERVER_EXE (
        start "Guandan Server" cmd /k ""%SERVER_EXE%" 12"
    ) else if exist "D:\guandanscore\guandan-offline-serve\windows\guandan_offline_v1006.exe" (
        start "Guandan Server" cmd /k "cd /d "D:\guandanscore\guandan-offline-serve\windows" && guandan_offline_v1006.exe 12"
    ) else if exist "%REPO_ROOT%\guandan_offline_v1006\windows\guandan_offline_v1006.exe" (
        start "Guandan Server" cmd /k "cd /d "%REPO_ROOT%\guandan_offline_v1006\windows" && guandan_offline_v1006.exe 12"
    ) else if exist "%REPO_ROOT%\offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe" (
        start "Guandan Server" cmd /k "cd /d "%REPO_ROOT%\offline_platform\guandan_offline_v1006\windows" && guandan_offline_v1006.exe 12"
    ) else (
        echo [ERROR] Server exe not found. Set SERVER_EXE or edit config/v7_paths.yaml
        pause
        exit /b 1
    )

    echo Waiting for server startup (15 seconds)...
    timeout /t 15 /nobreak > nul
    echo.
) else (
    echo [OK] Server is running
    echo.
)

echo Starting V7 clients...
call "%REPO_ROOT%\START_V7_CLIENTS.bat"

echo.
echo ========================================
echo V7 System Started!
echo ========================================
pause > nul
