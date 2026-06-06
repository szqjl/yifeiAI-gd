@echo off
chcp 65001 >nul
REM 启动 V7 批量测试 GUI（写法对标 START_M1_GUI.bat）
REM 服务器由 batch_executor 自动拉起，勿在此 bat 里重复启动

cd /d "%~dp0"

echo ========================================
echo 掼蛋AI批量对战系统 - V7版本
echo ========================================
echo.
echo 配置：YiFei V7 vs lalala一等奖AI
echo 队伍A：yf1_v7 (0号) + yf2_v7 (2号)
echo 队伍B：lalala client3 (1号) + client4 (3号)
echo.
echo 特性：终极胜率导向引擎 V7
echo   - 模型决策 + 规则回退
echo   - 路径见 config/v7_paths.yaml
echo   - 批跑局数建议 3 / 9 / 12（须为 3 的倍数）
echo.
echo 正在启动 GUI...
echo ========================================
echo.

py batch_executor_gui_v7.py

pause
