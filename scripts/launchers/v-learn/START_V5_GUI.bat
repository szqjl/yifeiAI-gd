@echo off
call "%~dp0..\_env.bat"
REM 启动V5批量测试GUI
REM 使用增强的RL集成和知识库应用的V5版本进行批量对战测试

echo ========================================
echo 掼蛋AI批量对战系统 - V5版本
echo ========================================
echo.
echo 配置：YiFei V5 vs lalala一等奖AI
echo 队伍A：yf1_v5 (0号) + yf2_v5 (2号)
echo 队伍B：lalala client3 (1号) + client4 (3号)
echo.
echo 特性：智能混合决策系统
echo   - RL决策引擎集成
echo   - 知识库增强决策
echo   - 规则引擎决策
echo   - 智能决策融合（RL + Knowledge + Rule-based）
echo   - WebSocket配置化连接（自动重连、心跳保活）
echo.
echo 正在启动GUI...
echo ========================================
echo.

REM 设置环境变量指定使用V5客户端
set CLIENT_VERSION=v5
py scripts/gui/batch_executor_gui.py

pause

