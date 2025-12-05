@echo off
chcp 65001 > nul

:: 增强游戏回放生成器批处理文件

:start
cls
echo. 增强游戏回放生成器
echo.==============================================
echo.

:: 检查Python环境
echo. 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo. 错误: 未找到Python环境，请确保已安装Python
    echo. 按任意键退出...
    pause >nul
    exit /b 1
)

:: 生成增强回放文件
echo. 正在生成增强回放文件...
echo.
python enhance_replay.py

:: 检查是否生成成功
if errorlevel 1 (
    echo.
    echo. 错误: 生成增强回放文件失败
    echo. 按任意键退出...
    pause >nul
    exit /b 1
)

echo.
echo. 增强回放文件生成成功！
echo.
echo. 按任意键启动GUI回放...
pause >nul

:: 启动GUI回放
echo. 正在启动GUI回放...
echo.
python replay_gui.py

:end
pause >nul
