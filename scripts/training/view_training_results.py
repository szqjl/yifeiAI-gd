"""查看训练日志和训练效果"""
import json
from pathlib import Path
from datetime import datetime

print("="*60)
print("M1训练效果分析报告")
print("="*60)

# 1. 工作流状态
print("\n1. 工作流状态")
print("-"*60)
workflow_status_file = Path("models/m1_workflow_status.json")
if workflow_status_file.exists():
    with open(workflow_status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    print(f"状态: {status.get('status')}")
    print(f"当前迭代: {status.get('current_iteration')}/{status.get('max_iterations')}")
    print(f"目标胜率: {status.get('target_win_rate', 0)*100:.1f}%")
    print(f"最后更新: {status.get('timestamp', 'unknown')[:19]}")
    print(f"成功: {'是' if status.get('success') else '否'}")

# 2. 工作流迭代历史
print("\n2. 工作流迭代历史")
print("-"*60)
workflow_history_file = Path("models/m1_training_workflow_history.json")
if workflow_history_file.exists():
    with open(workflow_history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    history = data.get('workflow_history', [])
    print(f"总迭代次数: {len(history)}")
    if history:
        print("\n最近5次迭代:")
        for i in history[-5:]:
            print(f"  迭代{i.get('iteration')}: 胜率={i.get('win_rate', 0):.2%}, 状态={i.get('status', 'unknown')}, 时间={i.get('timestamp', 'unknown')[:19]}")

# 3. 训练历史详细分析
print("\n3. 训练历史详细分析")
print("-"*60)
training_history_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_history_file.exists():
    with open(training_history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if isinstance(history, list) and len(history) > 0:
        latest = history[-1]
        first = history[0]
        
        print(f"训练轮数: {len(history)} epochs")
        print(f"\n最新Epoch ({latest.get('epoch')}):")
        print(f"  总损失: {latest.get('total_loss', 0):,.2f}")
        print(f"  动作损失: {latest.get('action_loss', 0):,.2f}")
        print(f"  策略损失: {latest.get('strategy_loss', 0):.4f}")
        print(f"  阈值损失: {latest.get('threshold_loss', 0):.6f}")
        print(f"  预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}")
        print(f"  真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"  预测比例: {latest.get('prediction_ratio', 0):.2f}倍")
        print(f"  学习率: {latest.get('learning_rate', 0):.6f}")
        print(f"  Epoch时间: {latest.get('epoch_time', 0):.2f}秒")
        
        print(f"\n训练趋势 (Epoch 1 -> {latest.get('epoch')}):")
        loss_change = ((latest.get('total_loss', 0) - first.get('total_loss', 0)) / first.get('total_loss', 0) * 100) if first.get('total_loss', 0) > 0 else 0
        print(f"  总损失: {first.get('total_loss', 0):,.2f} -> {latest.get('total_loss', 0):,.2f} ({loss_change:+.1f}%)")
        print(f"  预测比例: {first.get('prediction_ratio', 0):.2f} -> {latest.get('prediction_ratio', 0):.2f}倍")
        print(f"  真实卡牌数: {first.get('avg_true_cards', 0):.2f} -> {latest.get('avg_true_cards', 0):.2f}")
        print(f"  预测卡牌数: {first.get('avg_predicted_cards', 0):.2f} -> {latest.get('avg_predicted_cards', 0):.2f}")
        
        # 分析问题
        print(f"\n问题分析:")
        if latest.get('prediction_ratio', 0) > 100:
            print(f"  [警告] 预测比例过高 ({latest.get('prediction_ratio', 0):.2f}倍)")
            print(f"     模型预测了 {latest.get('avg_predicted_cards', 0):.2f} 张卡牌，但真实只有 {latest.get('avg_true_cards', 0):.2f} 张")
        if latest.get('total_loss', 0) > 1e9:
            print(f"  [警告] 损失值异常高 ({latest.get('total_loss', 0):,.2f})")
            print(f"     可能是过度预测惩罚过大导致")
        if latest.get('avg_true_cards', 0) < 1.0:
            print(f"  [警告] 真实卡牌数偏低 ({latest.get('avg_true_cards', 0):.2f})")
            print(f"     可能仍有太多空样本或数据质量问题")
        if latest.get('avg_predicted_cards', 0) >= 512:
            print(f"  [警告] 模型预测了所有卡牌 ({latest.get('avg_predicted_cards', 0):.2f}/512)")
            print(f"     说明模型没有学到稀疏性约束")

# 4. 模型文件
print("\n4. 模型文件")
print("-"*60)
model_file = Path("models/bc_model_stage7_optimized.pth")
if model_file.exists():
    size_mb = model_file.stat().st_size / 1024 / 1024
    print(f"模型文件: {model_file.name}")
    print(f"文件大小: {size_mb:.2f} MB")
    print(f"存在: 是")
else:
    print("模型文件: 不存在")

# 5. 游戏记录
print("\n5. 游戏记录")
print("-"*60)
game_records_dir = Path("game_records")
if game_records_dir.exists():
    records = list(game_records_dir.glob("*.json"))
    yf1_records = list(game_records_dir.glob("*yf1_m1*.json"))
    print(f"总游戏记录: {len(records)}")
    print(f"yf1_m1记录: {len(yf1_records)}")
    if yf1_records:
        latest_record = max(yf1_records, key=lambda p: p.stat().st_mtime)
        print(f"最新记录: {latest_record.name}")
        mtime = datetime.fromtimestamp(latest_record.stat().st_mtime)
        print(f"修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

print("\n" + "="*60)
print("分析完成")
print("="*60)
