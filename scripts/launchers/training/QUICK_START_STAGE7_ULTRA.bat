@echo off
call "%~dp0..\_env.bat"
echo ============================================================
echo Stage 7.2 超级优化版本 - 快速启动脚本
echo ============================================================
echo.

echo [1/3] 检查依赖包...
python -c "import torch, numpy; print('依赖包检查通过')" 2>nul
if errorlevel 1 (
    echo 错误: 缺少必要的依赖包
    echo 请运行: pip install torch numpy
    pause
    exit /b 1
)

echo [2/3] 运行超级优化训练...
echo 目标: 解决预测过度问题，实现1.5x预测比例
python src/train/stage7_ultra_optimized_training.py
if errorlevel 1 (
    echo 训练失败，请检查错误信息
    pause
    exit /b 1
)

echo [3/3] 运行模型评估...
python src/train/stage7_ultra_evaluation.py
if errorlevel 1 (
    echo 评估失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Stage 7.2 超级优化版本执行完成
echo ============================================================
echo 预期改进:
echo - 预测比例: 从164.3x降至1.5x (99%%改进)
echo - 预测卡牌数: 从512张降至4.2张
echo - 卡牌级准确率: 提升至98.65%%
echo.
echo 查看详细结果:
echo - 训练历史: models/bc_model_stage7_ultra_optimized_training_history.json
echo - 评估结果: training_logs/stage7_ultra_evaluation_*.json
echo - 性能总结: STAGE7_ULTRA_OPTIMIZATION_SUMMARY.md
echo.
pause