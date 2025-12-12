@echo off
echo ========================================
echo 阶段1紧急修复：完整实施阶段1方案
echo ========================================
echo 紧急修复内容（阶段1完整实施）：
echo - 方案G-1：预测数量惩罚权重：0.2 → 1.0
echo - 方案G-2：重新启用Top-K损失（权重0.5）
echo - 方案I-1：学习率调度：StepLR → CosineAnnealingLR
echo ========================================

cd /d d:\YiFeiAI-GD

echo 正在训练新模型（50 epochs）...
python src/train/pretrain.py

echo.
echo ========================================
echo 训练完成，开始评估...
echo ========================================

echo 正在评估模型性能...
python src/train/evaluate_baseline.py

echo.
echo ========================================
echo 评估完成，请查看结果
echo ========================================
pause