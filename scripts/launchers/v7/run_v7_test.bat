@echo off
chcp 65001 >nul
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
cd /d "%REPO%"

echo ========================================
echo V7端到端测试 - V7 vs lalala
echo ========================================
echo.

echo 启动服务器...
if exist "%REPO%\guandan_offline_v1006\windows\guandan_offline_v1006.exe" (
    start "服务器" "%REPO%\guandan_offline_v1006\windows\guandan_offline_v1006.exe" 12
) else if exist "%REPO%\offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe" (
    start "服务器" "%REPO%\offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe" 12
) else (
    echo [ERROR] 未找到 guandan_offline_v1006.exe
    pause
    exit /b 1
)

timeout /t 10 /nobreak > nul

echo 启动 yf1_v7 (玩家0)...
start "yf1_v7" cmd /k "cd /d %REPO% && python src\communication\yf1_v7.py"
timeout /t 3 /nobreak > nul

echo 启动 lalala_client3 (玩家1)...
start "lalala_client3" cmd /k "cd /d %REPO% && python src\communication\run_lalala_client3.py"
timeout /t 3 /nobreak > nul

echo 启动 yf2_v7 (玩家2)...
start "yf2_v7" cmd /k "cd /d %REPO% && python src\communication\yf2_v7.py"
timeout /t 3 /nobreak > nul

echo 启动 lalala_client4 (玩家3)...
start "lalala_client4" cmd /k "cd /d %REPO% && python src\communication\run_lalala_client4.py"

echo.
echo 所有客户端已启动。测试结束后请手动关闭窗口。
pause
