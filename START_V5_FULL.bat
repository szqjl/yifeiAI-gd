@echo off
REM V5完整启动脚本 - 启动服务器和所有客户端
REM 参考V4机制：服务器等待15秒，客户端间隔3秒

echo ========================================
echo 掼蛋AI对战系统 - V5完整启动
echo ========================================
echo.
echo 版本: V5 (增强混合决策)
echo 对战: YiFei V5 vs lalala
echo.
echo 特性:
echo   - RL决策引擎集成
echo   - 知识库增强决策
echo   - 关键规则层
echo   - 智能决策融合
echo.
echo ========================================
echo.

REM 检查服务器文件
if not exist "server\guandan_offline_v1006.exe" (
    echo [错误] 服务器文件不存在: server\guandan_offline_v1006.exe
    echo.
    pause
    exit /b 1
)

REM 询问游戏场数
set /p GAME_COUNT="请输入游戏场数 (默认: 10): "
if "%GAME_COUNT%"=="" set GAME_COUNT=10

echo.
echo 配置:
echo   - 游戏场数: %GAME_COUNT%
echo   - 服务器等待: 15秒
echo   - 客户端间隔: 3秒
echo.
echo 按任意键开始启动...
pause > nul
echo.

REM 1. 启动服务器
echo ========================================
echo [1/5] 启动服务器...
echo ========================================
start "掼蛋服务器" cmd /k "cd /d %~dp0\server && guandan_offline_v1006.exe %GAME_COUNT%"
echo   服务器已启动，等待 15 秒让服务器就绪...
timeout /t 15 /nobreak
echo.

REM 2. 启动 yf1_v5 (0号位)
echo ========================================
echo [2/5] 启动 yf1_v5 (目标: 0号位)
echo ========================================
start "yf1_v5 (0号位)" cmd /k "cd /d %~dp0 && python src/communication/yf1_v5.py"
echo   等待 3 秒...
timeout /t 3 /nobreak
echo.

REM 3. 启动 lalala client3 (1号位)
echo ========================================
echo [3/5] 启动 lalala client3 (目标: 1号位)
echo ========================================
start "lalala_client3 (1号位)" cmd /k "cd /d %~dp0 && python src/communication/run_lalala_client3.py"
echo   等待 3 秒...
timeout /t 3 /nobreak
echo.

REM 4. 启动 yf2_v5 (2号位)
echo ========================================
echo [4/5] 启动 yf2_v5 (目标: 2号位)
echo ========================================
start "yf2_v5 (2号位)" cmd /k "cd /d %~dp0 && python src/communication/yf2_v5.py"
echo   等待 3 秒...
timeout /t 3 /nobreak
echo.

REM 5. 启动 lalala client4 (3号位)
echo ========================================
echo [5/5] 启动 lalala client4 (目标: 3号位)
echo ========================================
start "lalala_client4 (3号位)" cmd /k "cd /d %~dp0 && python src/communication/run_lalala_client4.py"
echo.

echo ========================================
echo 启动完成！
echo ========================================
echo.
echo 所有组件已启动:
echo   [√] 服务器 (游戏场数: %GAME_COUNT%)
echo   [√] yf1_v5 (0号位)
echo   [√] lalala client3 (1号位)
echo   [√] yf2_v5 (2号位)
echo   [√] lalala client4 (3号位)
echo.
echo 队伍分配:
echo   Team A (0+2): yf1_v5 + yf2_v5
echo   Team B (1+3): lalala client3 + client4
echo.
echo 提示:
echo   - 游戏将自动开始
echo   - 查看各个窗口确认位置分配
echo   - 游戏结束后查看 game_scores.json
echo   - 或使用 START_V5_GUI.bat 查看战绩
echo.
echo 按任意键关闭此窗口...
pause > nul
