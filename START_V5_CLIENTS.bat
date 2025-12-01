@echo off
REM V5客户端启动脚本 - 按顺序启动确保正确的队伍分配
REM 参考V4的机制：服务器等待15秒，客户端间隔3秒

echo ========================================
echo 掼蛋AI对战 - V5客户端启动
echo ========================================
echo.
echo 启动顺序（确保队伍分配）:
echo   1. yf1_v5      (第1个连接 -^> 0号位)
echo   2. client3     (第2个连接 -^> 1号位)
echo   3. yf2_v5      (第3个连接 -^> 2号位)
echo   4. client4     (第4个连接 -^> 3号位)
echo.
echo 队伍分配:
echo   Team A (0+2): yf1_v5 + yf2_v5
echo   Team B (1+3): lalala client3 + client4
echo.
echo ========================================
echo.

REM 检查服务器是否运行
echo 正在检查服务器状态...
netstat -an | findstr "23456" > nul
if errorlevel 1 (
    echo.
    echo [警告] 服务器可能未启动！
    echo 请先启动服务器: server\guandan_offline_v1006.exe 10
    echo.
    echo 按任意键继续启动客户端，或 Ctrl+C 取消...
    pause > nul
) else (
    echo [OK] 服务器已运行
)

echo.
echo 开始启动客户端...
echo ========================================
echo.

REM 1. 启动 yf1_v5 (0号位)
echo [1/4] 启动 yf1_v5 (目标: 0号位)...
start "yf1_v5 (0号位)" cmd /k "cd /d %~dp0 && python src/communication/yf1_v5.py"
echo   等待 3 秒...
timeout /t 3 /nobreak > nul
echo.

REM 2. 启动 lalala client3 (1号位)
echo [2/4] 启动 lalala client3 (目标: 1号位)...
start "lalala_client3 (1号位)" cmd /k "cd /d %~dp0 && python src/communication/run_lalala_client3.py"
echo   等待 3 秒...
timeout /t 3 /nobreak > nul
echo.

REM 3. 启动 yf2_v5 (2号位)
echo [3/4] 启动 yf2_v5 (目标: 2号位)...
start "yf2_v5 (2号位)" cmd /k "cd /d %~dp0 && python src/communication/yf2_v5.py"
echo   等待 3 秒...
timeout /t 3 /nobreak > nul
echo.

REM 4. 启动 lalala client4 (3号位)
echo [4/4] 启动 lalala client4 (目标: 3号位)...
start "lalala_client4 (3号位)" cmd /k "cd /d %~dp0 && python src/communication/run_lalala_client4.py"
echo.

echo ========================================
echo 所有客户端已启动！
echo ========================================
echo.
echo 提示:
echo   - 查看各个窗口确认位置分配
echo   - 预期: yf1_v5=0号, client3=1号, yf2_v5=2号, client4=3号
echo   - Team A (0+2): yf1_v5 + yf2_v5
echo   - Team B (1+3): lalala client3 + client4
echo   - 游戏结束后查看 game_scores.json 或使用 GUI 查看战绩
echo.
echo 按任意键关闭此窗口...
pause > nul
