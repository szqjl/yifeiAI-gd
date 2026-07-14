@echo off
call "%~dp0..\_env.bat"
echo ========================================
echo V8 终极胜率导向系统完整启动 (OpenGuanDan)
echo ========================================
echo.
echo 此脚本将按正确顺序启动：
echo 1. 服务器 (guandan.exe) - 端口 8181
echo 2. yf1_v8 客户端 - 创建房间 (CREATE_ROOM)
echo 3. client3 客户端 - 加入房间 (JOIN_ROOM)
echo 4. yf2_v8 客户端 - 加入房间 (JOIN_ROOM)
echo 5. client4 客户端 - 加入房间 (JOIN_ROOM)
echo.
echo 请确保：
echo - guandan.exe 位于 offline_platform/openguandan_latest/
echo - 所有客户端文件存在
echo - 端口 8181 未被占用
echo.
pause

python scripts/launchers/v8/start_v8_complete.py

pause
