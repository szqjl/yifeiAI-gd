@echo off
REM M1策略系统快捷测试 - CMD版本
REM 在CMD窗口中运行此脚本

echo ========================================
echo M1策略系统快捷测试
echo ========================================
echo.
echo 正在运行测试脚本...
echo.

cd /d "%~dp0"
python test_m1_strategy_quick.py

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.
pause

