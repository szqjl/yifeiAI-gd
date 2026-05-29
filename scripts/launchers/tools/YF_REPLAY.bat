@echo off
call "%~dp0..\_env.bat"
REM YiFei AI 掼蛋统一回放系统

echo ========================================
echo YiFei AI 掼蛋回放系统
echo ========================================
echo.
echo 功能：
echo   - 显示所有四个玩家的起始手牌
echo   - 清晰回放比赛全过程
echo   - 突出显示yf玩家的决策
echo   - 支持播放、暂停、快进、慢放等控制
echo.
echo 正在启动GUI...
echo ========================================
echo.

REM 检查Python环境
py --version > nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或不在PATH中
    echo 请确保已安装Python并添加到系统PATH
    pause
    exit /b 1
)

REM 检查tkinter模块
py -c "import tkinter" > nul 2>&1
if errorlevel 1 (
    echo [错误] tkinter模块未安装
    echo 请安装Python的tkinter模块
    pause
    exit /b 1
)

REM 启动回放系统
python scripts/tools/yf_replay.py

if errorlevel 1 (
    echo.
    echo [错误] 回放系统启动失败
    echo 请检查错误信息
    pause
    exit /b 1
)

pause