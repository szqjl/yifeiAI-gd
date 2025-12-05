@echo off
chcp 65001 >nul
REM ============================================================
REM 掼蛋AI训练GUI启动脚本（优化版）
REM 版本: 2.0
REM 更新: 2025-12-05
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo 掼蛋AI训练GUI工具
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python！
    echo.
    echo 请确保已安装Python 3.7或更高版本，并添加到系统PATH中。
    echo.
    pause
    exit /b 1
)

echo [信息] 检测到Python环境
python --version
echo.

REM 检查必要的目录
if not exist "src\train\training_gui.py" (
    echo [错误] 找不到训练GUI脚本！
    echo 请确保在项目根目录运行此脚本。
    echo.
    pause
    exit /b 1
)

if not exist "game_records" (
    echo [警告] 训练数据目录不存在，将自动创建...
    mkdir game_records
)

if not exist "models" (
    echo [警告] 模型目录不存在，将自动创建...
    mkdir models
)

if not exist "training_logs" (
    echo [警告] 训练日志目录不存在，将自动创建...
    mkdir training_logs
)

echo [信息] 环境检查完成
echo.

REM 显示优化后的默认参数
echo ============================================================
echo 优化后的训练参数（默认值）
echo ============================================================
echo 训练轮数: 50轮（已优化）
echo 批次大小: 64（已优化）
echo 学习率: 0.0003（已优化）
echo 预测阈值: 0.3（已优化）
echo 学习率衰减: 每10轮衰减50%%（已启用）
echo Dropout: 0.2（已启用）
echo ============================================================
echo.

REM 启动训练GUI
echo [信息] 正在启动训练GUI工具...
echo.

python src/train/training_gui.py

REM 检查启动结果
if errorlevel 1 (
    echo.
    echo [警告] Python命令失败，尝试使用python3...
    python3 src/train/training_gui.py
    
    if errorlevel 1 (
        echo.
        echo ============================================================
        echo [错误] 无法启动训练GUI！
        echo ============================================================
        echo.
        echo 可能的原因：
        echo 1. Python未正确安装或未添加到PATH
        echo 2. 缺少必要的Python包（torch, tkinter等）
        echo 3. 训练GUI脚本文件损坏
        echo.
        echo 解决方案：
        echo 1. 检查Python安装：python --version
        echo 2. 安装依赖：pip install torch numpy gymnasium
        echo 3. 检查文件完整性
        echo.
        pause
        exit /b 1
    )
)

REM 如果GUI正常关闭，显示提示
echo.
echo ============================================================
echo 训练GUI已关闭
echo ============================================================
echo.
echo 提示：
echo - 训练日志保存在 training_logs\ 目录
echo - 训练完成的模型保存在 models\ 目录
echo - 建议训练完成后运行评估脚本：
echo   python src/train/evaluate_model.py
echo.

pause
