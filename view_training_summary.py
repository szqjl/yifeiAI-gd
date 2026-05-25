"""查看训练效果摘要"""
import json
from pathlib import Path

print("="*60)
print("M1训练效果摘要")
print("="*60)

# 训练历史
training_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_file.exists():
    with open(training_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if isinstance(history, list) and len(history) > 0:
        latest = history[-1]
        first = history[0]
        
        print(f"\n训练轮数: {len(history)} epochs")
        print(f"最新Epoch: {latest.get('epoch')}")
        print(f"\n关键指标:")
        print(f"  总损失: {latest.get('total_loss', 0):,.2f}")
        print(f"  预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}/512")
        print(f"  真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"  预测比例: {latest.get('prediction_ratio', 0):.2f}倍")
        
        print(f"\n训练趋势:")
        print(f"  损失: {first.get('total_loss', 0):,.0f} -> {latest.get('total_loss', 0):,.0f}")
        print(f"  预测比例: {first.get('prediction_ratio', 0):.2f} -> {latest.get('prediction_ratio', 0):.2f}倍")
        print(f"  真实卡牌数: {first.get('avg_true_cards', 0):.2f} -> {latest.get('avg_true_cards', 0):.2f}")

# 工作流状态
workflow_file = Path("models/m1_training_workflow_history.json")
if workflow_file.exists():
    with open(workflow_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    history = data.get('workflow_history', [])
    print(f"\n工作流迭代: {len(history)}次")
    if history:
        latest = history[-1]
        print(f"最新迭代: {latest.get('iteration')}")
        print(f"胜率: {latest.get('win_rate', 0):.2%}")
        print(f"状态: {latest.get('status', 'unknown')}")

print("\n" + "="*60)
