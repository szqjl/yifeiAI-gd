"""详细检查训练进度"""
import json
from pathlib import Path
from datetime import datetime

print("="*60)
print("M1训练进度详细报告")
print("="*60)

# 1. 工作流状态
print("\n1. 工作流状态")
print("-"*60)
status_file = Path("models/m1_workflow_status.json")
if status_file.exists():
    with open(status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    print(f"状态: {status.get('status')}")
    print(f"当前迭代: {status.get('current_iteration', 0)}/{status.get('max_iterations', 10)}")
    print(f"目标胜率: {status.get('target_win_rate', 0)*100:.1f}%")
    print(f"成功: {'是' if status.get('success') else '否'}")
    timestamp = status.get('timestamp', '')
    if timestamp:
        print(f"最后更新: {timestamp[:19]}")
else:
    print("工作流状态文件不存在")

# 2. 工作流迭代历史
print("\n2. 工作流迭代历史")
print("-"*60)
workflow_file = Path("models/m1_training_workflow_history.json")
if workflow_file.exists():
    with open(workflow_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    history = data.get('workflow_history', [])
    print(f"总迭代次数: {len(history)}")
    if history:
        print("\n最近3次迭代:")
        for i in history[-3:]:
            print(f"  迭代{i.get('iteration')}: 胜率={i.get('win_rate', 0):.2%}, 状态={i.get('status', 'unknown')}, 时间={i.get('timestamp', 'unknown')[:19]}")

# 3. 训练历史
print("\n3. 训练历史")
print("-"*60)
training_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_file.exists():
    with open(training_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if isinstance(history, list) and len(history) > 0:
        latest = history[-1]
        first = history[0]
        
        print(f"训练轮数: {len(history)} epochs")
        print(f"\n最新Epoch ({latest.get('epoch')}):")
        print(f"  总损失: {latest.get('total_loss', 0):,.2f}")
        print(f"  动作损失: {latest.get('action_loss', 0):,.2f}")
        print(f"  预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}/512")
        print(f"  真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"  预测比例: {latest.get('prediction_ratio', 0):.2f}倍")
        print(f"  学习率: {latest.get('learning_rate', 0):.6f}")
        
        print(f"\n训练趋势 (Epoch 1 -> {latest.get('epoch')}):")
        print(f"  总损失: {first.get('total_loss', 0):,.0f} -> {latest.get('total_loss', 0):,.0f}")
        print(f"  预测比例: {first.get('prediction_ratio', 0):.2f} -> {latest.get('prediction_ratio', 0):.2f}倍")
        print(f"  预测卡牌数: {first.get('avg_predicted_cards', 0):.2f} -> {latest.get('avg_predicted_cards', 0):.2f}")
        
        # 问题分析
        print(f"\n问题分析:")
        if latest.get('avg_predicted_cards', 0) >= 512:
            print(f"  [严重] 模型预测了所有512张卡牌")
            print(f"         阈值设置可能无效，需要进一步降低")
        if latest.get('prediction_ratio', 0) > 10:
            print(f"  [严重] 预测比例过高（{latest.get('prediction_ratio', 0):.2f}倍）")
            print(f"         需要增加过度预测惩罚")
        if latest.get('total_loss', 0) > 10000:
            print(f"  [警告] 损失值仍然较高（{latest.get('total_loss', 0):,.2f}）")
            print(f"         可能需要调整学习率或损失函数参数")

# 4. 训练代码参数
print("\n4. 训练代码参数")
print("-"*60)
code_file = Path("src/train/stage7_optimized_training.py")
if code_file.exists():
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 检查阈值设置
    if "threshold = torch.clamp(base_threshold * 0.01, 0.001, 0.1)" in code:
        print("  阈值设置: clamp(base_threshold * 0.01, 0.001, 0.1)")
        print("  [需要改进] 应进一步缩小到 0.0001-0.01")
    elif "threshold = torch.clamp(base_threshold * 0.001, 0.0001, 0.01)" in code:
        print("  阈值设置: clamp(base_threshold * 0.001, 0.0001, 0.01)")
        print("  [已改进] 阈值范围已缩小")
    
    # 检查惩罚参数
    if "over_prediction_penalty=1000.0" in code:
        print("  过度预测惩罚: 1000.0")
        print("  [需要改进] 应增加到 5000.0")
    elif "over_prediction_penalty=5000.0" in code:
        print("  过度预测惩罚: 5000.0")
        print("  [已改进] 惩罚已增加")
    
    # 检查学习率
    if "learning_rate: float = 0.00005" in code:
        print("  学习率: 0.00005")
        print("  [需要改进] 应降低到 0.00001")
    elif "learning_rate: float = 0.00001" in code:
        print("  学习率: 0.00001")
        print("  [已改进] 学习率已降低")

# 5. 模型文件
print("\n5. 模型文件")
print("-"*60)
model_file = Path("models/bc_model_stage7_optimized.pth")
if model_file.exists():
    size_mb = model_file.stat().st_size / 1024 / 1024
    mtime = datetime.fromtimestamp(model_file.stat().st_mtime)
    print(f"模型文件: {model_file.name}")
    print(f"文件大小: {size_mb:.2f} MB")
    print(f"修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("模型文件: 不存在")

# 6. 自动重启系统状态
print("\n6. 自动重启系统")
print("-"*60)
print("提示: 运行 'python scripts/workflow/auto_restart_workflow.py' 启动自动重启系统")
print("或运行 'START_AUTO_RESTART_WORKFLOW.bat'")

print("\n" + "="*60)
print("检查完成")
print("="*60)
