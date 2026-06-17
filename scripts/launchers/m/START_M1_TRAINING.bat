@echo off
call "%~dp0..\_env.bat"
REM M1优化训练启动脚本
REM 目标：训练模型帮助M1战胜client

echo ==========================================
echo M1优化训练
echo ==========================================
echo.

echo 步骤1: 启动训练（使用MLflow监控）...
python src/train/stage7_optimized_training.py ^
    --monitor_backend mlflow ^
    --epochs 100 ^
    --batch_size 32 ^
    --learning_rate 0.00005 ^
    --monitor_project "m1-vs-client" ^
    --monitor_name "m1_training_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"

if %ERRORLEVEL% NEQ 0 (
    echo 训练失败，退出码: %ERRORLEVEL%
    pause
    exit /b 1
)

echo.
echo 训练完成！
echo.

echo 步骤2: 分析训练结果...
if exist "models\bc_model_stage7_optimized_training_history.json" (
    python src/train/training_optimizer.py --history "models\bc_model_stage7_optimized_training_history.json"
) else (
    echo 警告: 未找到训练历史文件
)

echo.
echo 步骤3: 评估模型效果...
if exist "models\bc_model_stage7_optimized.pth" (
    python src/train/m1_vs_client_evaluator.py --num_games 50 --opponent client --model_path "models\bc_model_stage7_optimized.pth"
) else (
    echo 警告: 未找到模型文件，请先完成训练
)

echo.
echo ==========================================
echo 训练流程完成
echo ==========================================
echo.
echo 下一步：
echo 1. 查看MLflow UI: mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
echo 2. 根据评估结果决定是否需要继续优化
echo 3. 如果胜率^<50%%，运行优化脚本调整参数
echo.
pause
