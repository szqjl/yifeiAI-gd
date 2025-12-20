@echo off
chcp 65001 >nul
echo ============================================================
echo YF掼蛋V6客户端对战测试
echo ============================================================
echo.

REM 服务器路径
set SERVER_PATH=D:\geminicard\guandan_offline_v1006.exe
if not exist "%SERVER_PATH%" (
    echo [错误] 找不到游戏服务器: %SERVER_PATH%
    pause
    exit /b 1
)

echo [1/4] 启动游戏服务器 (10局)...
start "GameServer" "%SERVER_PATH%" 10
timeout /t 5 /nobreak >nul

echo [2/4] 启动V6客户端1 (yf1)...
start "YF1_V6" python src/communication/yf1_v5.py
timeout /t 3 /nobreak >nul

echo [3/4] 启动V6客户端2 (yf2)...
start "YF2_V6" python src/communication/yf2_v5.py
timeout /t 3 /nobreak >nul

echo [4/4] 启动lalala对手客户端...
start "Lalala3" python src/communication/run_lalala_client3.py
timeout /t 2 /nobreak >nul
start "Lalala4" python src/communication/run_lalala_client4.py

echo.
echo ============================================================
echo 所有客户端已启动！
echo 游戏将自动进行10局对战。
echo 结果将保存到 game_scores.json
echo ============================================================
echo.
echo 按任意键关闭此窗口（不会影响正在运行的游戏）...
pause >nul
