@echo off
setlocal enabledelayedexpansion
REM Stage 7 鲁棒性增强训练启动脚本

echo ========================================
echo 掼蛋AI Stage 7 鲁棒性增强训练
echo ========================================
echo.
echo 主要改进:
echo   1. 解决稳定性问题 - 防止连续对战中的性能崩溃
echo   2. 修复预测过度问题 - 大幅减少预测卡牌数量  
echo   3. 增强数据利用 - 优化特征工程和损失函数
echo   4. 提升决策质量 - 改进模型架构和训练策略
echo.
echo 技术特性:
echo   - 残差连接 + BatchNorm 提升稳定性
echo   - 自适应焦点损失函数解决预测过度
echo   - 多任务学习 (动作+策略+阈值)
echo   - 余弦退火学习率调度
echo   - 梯度裁剪防止梯度爆炸
echo.
echo ========================================
echo.

REM 检查Python环境
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或不在PATH中
    pause
    exit /b 1
)

REM 检查必要的包
echo 检查依赖包...
python -c "import torch, numpy, json, pathlib" > nul 2>&1
if errorlevel 1 (
    echo [错误] 缺少必要的Python包
    echo.
    echo 请安装以下依赖包:
    echo   pip install torch numpy
    echo.
    echo 如果使用conda:
    echo   conda install pytorch numpy -c pytorch
    echo.
    set /p install_deps="是否现在安装依赖包? (y/n): "
    if /i "!install_deps!"=="y" (
        echo 正在安装依赖包...
        pip install torch numpy
        if errorlevel 1 (
            echo [错误] 依赖包安装失败
            pause
            exit /b 1
        )
        echo [OK] 依赖包安装成功
    ) else (
        echo 请手动安装依赖包后重新运行
        pause
        exit /b 1
    )
)

REM 检查数据目录
if not exist "game_records" (
    echo [错误] 训练数据目录 'game_records' 不存在
    echo 请先准备训练数据
    pause
    exit /b 1
)

REM 创建必要目录
if not exist "models" mkdir models
if not exist "training_logs" mkdir training_logs

echo [OK] 环境检查通过
echo.

REM 开始训练
echo 开始 Stage 7 训练...
echo ========================================
echo.

REM 设置环境变量指定使用V6客户端（Stage 7对应V6版本）
set CLIENT_VERSION=v6

cd src\train
python stage7_robust_training.py

echo.
echo ========================================
echo Stage 7 训练完成！
echo.

REM 询问是否立即评估
set /p run_eval="是否立即运行评估? (y/n): "
if /i "%run_eval%"=="y" (
    echo.
    echo 开始 Stage 7 评估...
    echo ========================================
    python stage7_evaluation.py
    echo.
    echo 评估完成！
)

echo.
echo 训练和评估结果保存在:
echo   - 模型文件: models/bc_model_stage7_robust.pth
echo   - 训练历史: models/bc_model_stage7_robust_training_history.json  
echo   - 评估结果: training_logs/stage7_evaluation_*.json
echo.
echo 按任意键退出...
pause > nul