@echo off
call "%~dp0..\_env.bat"
echo ========================================
echo V7终极胜率导向系统完整启动
echo ========================================
echo.
echo 此脚本将按正确顺序启动：
echo 1. 服务器 (guandan_offline_v1006.exe)
echo 2. yf1_v7 客户端
echo 3. client3 客户端  
echo 4. yf2_v7 客户端
echo 5. client4 客户端
echo.
echo 请确保：
echo - 服务器路径正确
echo - 所有客户端文件存在
echo - 端口23456未被占用
echo.
pause

python scripts/launchers/v7/start_v7_complete.py

pause