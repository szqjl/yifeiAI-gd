@echo off
chcp 65001 >nul
title 掼蛋AI批量对战系统 - GUI测试启动
color 0A
cls

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║          掼蛋AI批量对战系统 - GUI测试启动                 ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo.

echo [步骤 1/4] 检查Python环境...
echo ────────────────────────────────────────
py --version 2>nul
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo.
    echo 请安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo ✅ Python环境正常
echo.

echo [步骤 2/4] 检查GUI模块...
echo ────────────────────────────────────────
py -c "import tkinter; print('✅ GUI模块正常')" 2>nul
if errorlevel 1 (
    echo ❌ tkinter模块检查失败
    echo.
    echo 可能原因:
    echo 1. tkinter未安装（通常Python自带）
    echo.
    echo 尝试重新安装Python，确保勾选tkinter组件
    echo.
    pause
    exit /b 1
)
echo.

echo [步骤 3/4] 启动GUI...
echo ────────────────────────────────────────
echo.
echo 提示:
echo  • GUI窗口将在几秒钟内打开
echo  • 如果没有打开，请查看下方的错误信息
echo  • 关闭GUI窗口后，此窗口会显示退出信息
echo.
echo 正在启动...
echo.

REM 启动GUI并捕获输出
py test_gui_launch.py

echo.
echo [步骤 4/4] 完成
echo ────────────────────────────────────────

if errorlevel 1 (
    echo ❌ GUI启动失败
    echo.
    echo 请查看上方的错误信息
) else (
    echo ✅ GUI已正常关闭
)

echo.
echo ════════════════════════════════════════
echo.
pause
