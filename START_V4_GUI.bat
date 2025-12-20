@echo off
REM 启动V4批量测试GUI
REM 使用HybridDecisionEngineV4进行批量对战测试

echo ========================================
echo 掼蛋AI批量对战系统 - V4版本
echo ========================================
echo.
echo 配置：YiFei V4 vs lalala一等奖AI
echo 队伍A：yf1_v4 (0号) + yf2_v4 (2号)
echo 队伍B：lalala client3 (1号) + client4 (3号)
echo.
echo 特性：4层决策保护机制
echo   Layer 1: lalala Strategy
echo   Layer 2: DecisionEngine
echo   Layer 3: Knowledge Enhanced
echo   Layer 4: Random (保底)
echo.
echo 正在启动GUI...
echo ========================================
echo.

python batch_executor_gui.py

pause
