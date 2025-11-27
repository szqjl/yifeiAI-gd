@echo off
chcp 65001 >nul
title 测试lalala客户端适配器
color 0E

echo.
echo ╔════════════════════════════════════════╗
echo ║     测试lalala客户端适配器             ║
echo ╚════════════════════════════════════════╝
echo.

echo [测试步骤]
echo 1. 检查lalala目录是否存在
echo 2. 测试导入lalala客户端
echo 3. 显示可用的客户端
echo.

python -c "from src.communication.lalala_adapter import *; print('✓ 适配器导入成功')"

if errorlevel 1 (
    echo.
    echo ❌ 适配器测试失败
    echo.
    echo 可能原因:
    echo 1. D:\NYGD\lalala 目录不存在
    echo 2. lalala目录中缺少client1-4.py文件
    echo 3. 缺少ws4py库: pip install ws4py
    echo.
) else (
    echo.
    echo ✓ 适配器测试成功！
    echo.
    echo 现在可以在GUI中使用lalala客户端:
    echo   src/communication/run_lalala_client1.py
    echo   src/communication/run_lalala_client2.py
    echo   src/communication/run_lalala_client3.py
    echo   src/communication/run_lalala_client4.py
    echo.
)

pause
