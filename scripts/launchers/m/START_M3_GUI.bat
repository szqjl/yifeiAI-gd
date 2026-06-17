@echo off
call "%~dp0..\_env.bat"
REM 启动M3批量测试GUI
REM M3版本：忠实移植lalala决策引擎

echo ========================================
echo 掼蛋AI批量对战系统 - M3版本
echo ========================================
echo.
echo 配置：YiFei M3 vs lalala一等奖AI
echo 队伍A：yf1_m3 (0号) + yf2_m3 (2号)
echo 队伍B：lalala client3 (1号) + client4 (3号)
echo.
echo M3核心改进（对比M2）：
echo   - 完整移植lalala规则引擎（combine_handcards + choose_bomb + 多类型主动优先级）
echo   - 顺子/同花顺检测（突破M2仅单/对/三的瓶颈）
echo   - 精确炸弹阈值（按牌力打分而非简单≥4张=炸弹）
echo   - 主动出牌优先级链：rankone()-ranktwo()-rankthree()-rankfour()
echo   - PASS降级链完整 + T/J/Q连队规避还贡策略
echo   - 所有改动在M3专用文件，不碰共用层
echo.
echo 正在启动GUI...
echo ========================================
echo.

py scripts/gui/batch_executor_gui_m3.py

pause
