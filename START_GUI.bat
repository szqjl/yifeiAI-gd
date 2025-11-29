@echo off
chcp 65001 >nul
cls
echo ========================================
echo 掼蛋AI批量对战系统 - 图形界面
echo ========================================
echo.
echo 正在启动GUI...
echo 提示: GUI窗口将在新窗口中打开
echo       关闭GUI窗口后，此窗口会自动关闭
echo.

REM 启动GUI（会阻塞直到GUI关闭）
py batch_executor_gui.py

REM 检查退出码
if errorlevel 1 (
    echo.
    echo ========================================
    echo GUI异常退出！
    echo ========================================
    echo.
    echo 可能的原因:
    echo 1. Python未安装或未添加到PATH
    echo 2. 缺少必要的依赖包  
    echo 3. 程序执行出错
    echo.
    echo 解决方法:
    echo 1. 确认Python已安装: py --version
    echo 2. 安装依赖: py -m pip install -r requirements.txt
    echo 3. 重新运行并查看错误信息
    echo.
    pause
) else (
    echo.
    echo GUI已正常关闭
)
