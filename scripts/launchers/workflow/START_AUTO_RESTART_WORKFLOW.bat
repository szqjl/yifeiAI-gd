@echo off
call "%~dp0..\_env.bat"
chcp 65001 >nul
REM M1训练工作流自动重启系统
REM 自动检测、分析、改进、重启，循环直到达成目标

echo ==========================================
echo M1训练工作流自动重启系统
echo 功能：自动检测、分析、改进、重启
echo 目标：M1战胜client（胜率^>50%%）
echo ==========================================
echo.

echo 系统将自动：
echo   1. 检测工作流状态
echo   2. 分析训练结果
echo   3. 根据问题自动改进训练代码
echo   4. 重启工作流
echo   5. 循环直到达成目标
echo.

echo 提示：运行以下命令可查看进度：
echo   python scripts/workflow/monitor_workflow_progress.py
echo.

REM 运行自动重启系统
python scripts/workflow/auto_restart_workflow.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo ✅ 自动重启系统完成
    echo ==========================================
) else (
    echo.
    echo ==========================================
    echo ⚠️ 自动重启系统异常退出
    echo 请检查日志了解详情
    echo ==========================================
)

pause
