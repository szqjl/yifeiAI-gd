#!/bin/bash
# M1优化训练脚本（WSL/Linux）；Windows 对等入口：scripts/launchers/m/START_M1_TRAINING.bat
# 目标：训练模型帮助M1战胜client

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

echo "=========================================="
echo "M1优化训练流程"
echo "=========================================="

# 1. 启动训练（使用MLflow监控）
echo "步骤1: 启动训练..."
python src/train/stage7_optimized_training.py \
    --monitor_backend mlflow \
    --epochs 100 \
    --batch_size 32 \
    --learning_rate 0.00005 \
    --monitor_project "m1-vs-client" \
    --monitor_name "m1_training_$(date +%Y%m%d_%H%M%S)"

TRAINING_EXIT_CODE=$?

if [ $TRAINING_EXIT_CODE -ne 0 ]; then
    echo "训练失败，退出码: $TRAINING_EXIT_CODE"
    exit 1
fi

echo "训练完成！"

# 2. 分析训练结果
echo ""
echo "步骤2: 分析训练结果..."
MODEL_PATH="models/bc_model_stage7_optimized.pth"
HISTORY_PATH="models/bc_model_stage7_optimized_training_history.json"

if [ -f "$HISTORY_PATH" ]; then
    python src/train/training_optimizer.py --history "$HISTORY_PATH"
else
    echo "警告: 未找到训练历史文件: $HISTORY_PATH"
fi

# 3. 评估模型效果
echo ""
echo "步骤3: 评估模型效果..."
python src/train/m1_vs_client_evaluator.py \
    --num_games 50 \
    --opponent client \
    --model_path "$MODEL_PATH"

echo ""
echo "=========================================="
echo "训练流程完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 查看MLflow UI: mlflow ui --backend-store-uri file:///$(pwd)/logs/mlruns"
echo "2. 根据评估结果决定是否需要继续优化"
echo "3. 如果胜率<50%，运行优化脚本调整参数"
