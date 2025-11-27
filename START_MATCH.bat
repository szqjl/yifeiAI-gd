@echo off
chcp 65001 >nul
echo ========================================
echo 掼蛋AI比赛启动脚本
echo ========================================
echo.
echo 队伍配置：
echo   队伍A (座位0和2): Test1.py + Test2.py (知识库增强)
echo   队伍B (座位1和3): client3.py + client4.py (一等奖代码)
echo.
echo ========================================
echo.

REM 检查服务器是否运行
echo [1/5] 检查服务器状态...
tasklist /FI "IMAGENAME eq guandan_offline_v1006.exe" 2>NUL | find /I /N "guandan_offline_v1006.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ✓ 服务器已运行
) else (
    echo ✗ 服务器未运行！
    echo.
    echo 请先启动服务器：
    echo   路径: D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe
    echo.
    pause
    exit /b 1
)

echo.
echo [2/5] 准备启动客户端...
echo.

cd /d D:\guandanscore\YiFeiAI-GD

REM 启动客户端1 (Test1.py - 座位0 - 队伍A)
echo [3/5] 启动客户端1 (Test1.py - 座位0 - 队伍A)...
start "Client1-Test1-Seat0" cmd /k "title Client1-Test1-Seat0 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\Test1.py"
timeout /t 3 /nobreak >nul

REM 启动客户端2 (client3.py - 座位1 - 队伍B)
echo [4/5] 启动客户端2 (client3.py - 座位1 - 队伍B)...
start "Client2-First3-Seat1" cmd /k "title Client2-First3-Seat1 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\first_prize\client3.py"
timeout /t 3 /nobreak >nul

REM 启动客户端3 (Test2.py - 座位2 - 队伍A)
echo [5/5] 启动客户端3 (Test2.py - 座位2 - 队伍A)...
start "Client3-Test2-Seat2" cmd /k "title Client3-Test2-Seat2 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\Test2.py"
timeout /t 3 /nobreak >nul

REM 启动客户端4 (client4.py - 座位3 - 队伍B)
echo [6/5] 启动客户端4 (client4.py - 座位3 - 队伍B)...
start "Client4-First4-Seat3" cmd /k "title Client4-First4-Seat3 && cd /d D:\guandanscore\YiFeiAI-GD && python src\communication\first_prize\client4.py"

echo.
echo ========================================
echo ✓ 所有客户端已启动！
echo ========================================
echo.
echo 座位分配：
echo   座位0: Test1.py    (队伍A - 知识库增强)
echo   座位1: client3.py  (队伍B - 一等奖代码)
echo   座位2: Test2.py    (队伍A - 知识库增强)
echo   座位3: client4.py  (队伍B - 一等奖代码)
echo.
echo 队友关系：
echo   队伍A: 座位0 (Test1) ←→ 座位2 (Test2)
echo   队伍B: 座位1 (client3) ←→ 座位3 (client4)
echo.
echo 提示：
echo   - 4个CMD窗口已打开，每个窗口运行一个客户端
echo   - 可以在各个窗口中查看客户端运行日志
echo   - 关闭任意窗口将停止对应的客户端
echo.
pause
