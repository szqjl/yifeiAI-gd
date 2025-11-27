@echo off
chcp 65001 >nul
echo ========================================
echo 掼蛋AI 100场比赛启动脚本
echo ========================================
echo.

REM 步骤1：关闭所有相关进程
echo [1/5] 清理环境...
taskkill /F /IM guandan_offline_v1006.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul
echo ✓ 环境清理完成
echo.

REM 步骤2：启动服务器
echo [2/5] 启动服务器（100场游戏）...
echo.
echo 请在新窗口中运行以下命令：
echo   cd /d D:\guandan_offline_v1006\windows
echo   guandan_offline_v1006.exe 100
echo.
echo 重要提示：
echo   1. 请确认服务器输出中显示的游戏次数是否为100
echo   2. 等待看到 "Ready for connect." 提示
echo   3. 如果显示的游戏次数不是100，请检查服务器配置
echo.
start "Guandan Server" cmd /k "cd /d D:\guandan_offline_v1006\windows && guandan_offline_v1006.exe 100"
echo.
echo 等待服务器启动...
timeout /t 15 /nobreak >nul

REM 步骤3：检查服务器是否运行
echo [3/5] 检查服务器状态...
tasklist /FI "IMAGENAME eq guandan_offline_v1006.exe" 2>NUL | find /I /N "guandan_offline_v1006.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ✓ 服务器已运行
) else (
    echo ✗ 服务器未运行！
    echo.
    echo 请手动启动服务器：
    echo   路径: D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe 100
    echo.
    pause
    exit /b 1
)

echo.
echo [4/5] 准备启动客户端...
echo.

cd /d D:\guandanscore\YiFeiAI-GD

REM 启动客户端1 (Test1.py - 座位0 - 队伍A)
echo [5/5] 启动客户端1 (Test1.py - 座位0 - 队伍A)...
start "Client1-Test1-Seat0" cmd /k "title Client1-Test1-Seat0 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\Test1.py"
timeout /t 3 /nobreak >nul

REM 启动客户端2 (client3.py - 座位1 - 队伍B)
echo 启动客户端2 (client3.py - 座位1 - 队伍B)...
start "Client2-First3-Seat1" cmd /k "title Client2-First3-Seat1 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\first_prize\client3.py"
timeout /t 3 /nobreak >nul

REM 启动客户端3 (Test2.py - 座位2 - 队伍A)
echo 启动客户端3 (Test2.py - 座位2 - 队伍A)...
start "Client3-Test2-Seat2" cmd /k "title Client3-Test2-Seat2 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\Test2.py"
timeout /t 3 /nobreak >nul

REM 启动客户端4 (client4.py - 座位3 - 队伍B)
echo 启动客户端4 (client4.py - 座位3 - 队伍B)...
start "Client4-First4-Seat3" cmd /k "title Client4-First4-Seat3 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\first_prize\client4.py"

echo.
echo ========================================
echo ✓ 所有客户端已启动！
echo ========================================
echo.
echo 队伍配置：
echo   队伍A (座位0和2): Test1.py + Test2.py (知识库增强)
echo   队伍B (座位1和3): client3.py + client4.py (一等奖代码)
echo.
echo 游戏设置：
echo   目标场数: 100场
echo   当前进度: 请查看服务器窗口
echo.
echo 监控提示：
echo   - 请观察服务器窗口中的游戏进度
echo   - 如果游戏在3场后停止，请检查服务器配置
echo   - 查看客户端窗口是否有错误信息
echo.
echo 如果游戏提前结束：
echo   1. 检查服务器窗口显示的游戏次数设置
echo   2. 查看 CHECK_MATCH_STATUS.md 文件获取诊断步骤
echo   3. 尝试手动启动服务器并确认参数
echo.
pause
