@echo off
call "%~dp0..\_env.bat"
REM 启动M2批量测试GUI
REM M2版本：重构硬编码规则引擎，无分数累积+阈值保护

echo ========================================
echo 掼蛋AI批量对战系统 - M2版本
echo ========================================
echo.
echo 配置：YiFei M2 vs lalala一等奖AI
echo 队伍A：yf1_m2 (0号) + yf2_m2 (2号)
echo 队伍B：lalala client3 (1号) + client4 (3号)
echo.
echo M2核心改进（对比M1）：
echo   - 保护逻辑内联在按牌型分发的处理器中（lalala风格）
echo   - 不加载共享TeammateProtectionStrategy（去掉分数累积+阈值）
echo   - PASS次数降级链完整（pass_num>=5 -> special, >=7 -> bomb）
echo   - 队友剩牌<=4时只出刚好大1（精确边界控制）
echo   - 开局主动恢复一手出完检查
echo   - 所有改动限制在M2专用文件，不碰共用层
echo.
echo 正在启动GUI...
echo ========================================
echo.

py scripts/gui/batch_executor_gui_m2.py

pause
