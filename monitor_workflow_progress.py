"""监控工作流进度"""
import json
import time
from pathlib import Path
from datetime import datetime

print("="*60)
print("工作流进度监控")
print("="*60)

# 检查工作流状态
status_file = Path("models/m1_workflow_status.json")
if status_file.exists():
    with open(status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    print(f"\n工作流状态: {status.get('status')}")
    print(f"当前迭代: {status.get('current_iteration', 0)}/{status.get('max_iterations', 10)}")
    print(f"目标胜率: {status.get('target_win_rate', 0)*100:.1f}%")
    timestamp = status.get('timestamp', '')
    if timestamp:
        print(f"最后更新: {timestamp[:19]}")
else:
    print("\n工作流状态文件不存在，可能正在初始化...")

# 检查训练历史
training_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_file.exists():
    with open(training_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    if isinstance(history, list) and len(history) > 0:
        latest = history[-1]
        print(f"\n最新训练记录:")
        print(f"  Epoch: {latest.get('epoch')}")
        print(f"  总损失: {latest.get('total_loss', 0):,.2f}")
        print(f"  预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}/512")
        print(f"  真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"  预测比例: {latest.get('prediction_ratio', 0):.2f}倍")
        
        # 检查修复效果
        print(f"\n修复效果检查:")
        if latest.get('total_loss', 0) < 10000:
            print(f"  [通过] 损失值已降至合理范围: {latest.get('total_loss', 0):,.2f}")
        else:
            print(f"  [警告] 损失值仍然较高: {latest.get('total_loss', 0):,.2f}")
        
        if latest.get('avg_predicted_cards', 0) < 20:
            print(f"  [通过] 预测卡牌数已降至合理范围: {latest.get('avg_predicted_cards', 0):.2f}")
        else:
            print(f"  [警告] 预测卡牌数仍然较高: {latest.get('avg_predicted_cards', 0):.2f}")
        
        if latest.get('prediction_ratio', 0) < 10:
            print(f"  [通过] 预测比例已降至合理范围: {latest.get('prediction_ratio', 0):.2f}倍")
        else:
            print(f"  [警告] 预测比例仍然较高: {latest.get('prediction_ratio', 0):.2f}倍")

# 检查工作流历史
workflow_file = Path("models/m1_training_workflow_history.json")
if workflow_file.exists():
    with open(workflow_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    history = data.get('workflow_history', [])
    if history:
        latest = history[-1]
        print(f"\n最新迭代:")
        print(f"  迭代: {latest.get('iteration')}")
        print(f"  胜率: {latest.get('win_rate', 0):.2%}")
        print(f"  状态: {latest.get('status', 'unknown')}")

print("\n" + "="*60)
print("提示: 运行 'python monitor_workflow_progress.py' 可随时查看进度")
print("="*60)
