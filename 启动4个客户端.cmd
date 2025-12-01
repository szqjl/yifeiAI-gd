@echo off
chcp 65001 >nul
title 启动4个客户端 - 掼蛋AI V5
color 0A
cls

echo ========================================
echo 启动4个客户端 - 掼蛋AI V5 vs lalala
echo ========================================
echo.
echo 队伍A (YiFei V5):
echo   客户端1: yf1_v5.py (0号位)
echo   客户端3: yf2_v5.py (2号位)
echo.
echo 队伍B (lalala):
echo   客户端2: run_lalala_client3.py (1号位)
echo   客户端4: run_lalala_client4.py (3号位)
echo.
echo ========================================
echo.

cd /d D:\YiFeiAI-GD

echo [1/4] 启动客户端1 (yf1_v5.py - 0号位)...
start "客户端1: yf1_v5" cmd /k "python src\communication\yf1_v5.py"
timeout /t 3 /nobreak >nul

echo [2/4] 启动客户端2 (run_lalala_client3.py - 1号位)...
start "客户端2: lalala_client3" cmd /k "python src\communication\run_lalala_client3.py"
timeout /t 3 /nobreak >nul

echo [3/4] 启动客户端3 (yf2_v5.py - 2号位)...
start "客户端3: yf2_v5" cmd /k "python src\communication\yf2_v5.py"
timeout /t 3 /nobreak >nul

echo [4/4] 启动客户端4 (run_lalala_client4.py - 3号位)...
start "客户端4: lalala_client4" cmd /k "python src\communication\run_lalala_client4.py"

echo.
echo ========================================
echo 所有客户端已启动！
echo ========================================
echo.
echo 提示:
echo - 每个客户端会在独立的窗口中运行
echo - 窗口标题包含客户端编号和名称
echo - 确保服务器已启动并显示 "Ready for connect"
echo - 4个客户端连接后，游戏将自动开始
echo.
pause


