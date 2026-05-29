@echo off
call "%~dp0..\_env.bat"
REM Stage 7 快速启动脚本

echo ========================================
echo 掼蛋AI Stage 7 快速启动
echo ========================================
echo.

REM 检查Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 请先安装Python
    pause
    exit /b 1
)

REM 检查基本依赖
python -c "import torch, numpy" > nul 2>&1
if errorlevel 1 (
    echo [提示] 缺少依赖包，正在尝试安装...
    pip install torch numpy
    if errorlevel 1 (
        echo [错误] 依赖包安装失败
        echo 请手动运行: pip install torch numpy
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

echo [OK] 环境检查通过，开始训练...
echo.

REM 切换到训练目录并启动
cd src\train
python stage7_robust_training.py

if errorlevel 1 (
    echo.
    echo [错误] 训练过程中出现错误
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo.
echo [成功] Stage 7 训练完成！
echo.

REM 询问是否评估
set /p run_eval="是否运行评估? (y/n): "
if /i "%run_eval%"=="y" (
    echo 开始评估...
    python stage7_evaluation.py
    echo 评估完成！
)

echo.
echo 结果文件:
echo   - 模型: ../../models/bc_model_stage7_robust.pth
echo   - 训练历史: ../../models/bc_model_stage7_robust_training_history.json
echo   - 评估结果: ../../training_logs/stage7_evaluation_*.json
echo.
pause