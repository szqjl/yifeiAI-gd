@echo off
REM 启动M1批量测试GUI
REM 使用全新的硬编码规则引擎M1版本进行批量对战测试

echo ========================================
echo 掼蛋AI批量对战系统 - M1版本
echo ========================================
echo.
echo 配置：YiFei M1 vs lalala一等奖AI
echo 队伍A：yf1_m1 (0号) + yf2_m1 (2号)
echo 队伍B：lalala client3 (1号) + client4 (3号)
echo.
echo 特性：硬编码规则引擎
echo   - 5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
echo   - 主动/被动出牌分离
echo   - 完善的策略逻辑（整合策略函数和知识库文档）
echo   - 完全独立于V5/V6版本
echo   - WebSocket配置化连接（自动重连、心跳保活）
echo.
echo 正在启动GUI...
echo ========================================
echo.

py batch_executor_gui.py

pause

