"""检查工作流当前运行状态"""
import json
from pathlib import Path
from datetime import datetime

print("="*60)
print("工作流当前运行状态")
print("="*60)

# 1. 工作流状态
status_file = Path("models/m1_workflow_status.json")
if status_file.exists():
    with open(status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    
    print("\n1. 工作流状态:")
    print(f"   状态: {status.get('status')}")
    print(f"   当前迭代: {status.get('current_iteration', 0)}/{status.get('max_iterations', 10)}")
    print(f"   目标胜率: {status.get('target_win_rate', 0):.1%}")
    
    ts = status.get('timestamp', '')
    if ts:
        print(f"   更新时间: {ts[:19]}")
    
    if status.get('error'):
        print(f"   错误: {status.get('error')}")
    
    if status.get('step'):
        print(f"   当前步骤: {status.get('step')}")
    
    success = status.get('success')
    if success is not None:
        print(f"   成功: {'是' if success else '否'}")
else:
    print("\n1. 工作流状态: 状态文件不存在")

# 2. 工作流步骤说明
print("\n2. 工作流步骤:")
steps = [
    "步骤0: 检查/生成游戏记录（如果记录不足，自动运行M1与client对战）",
    "步骤1: 训练模型（使用MLflow监控）",
    "步骤1.5: 从MLflow读取实时指标并分析",
    "步骤2: 分析训练结果",
    "步骤3: 评估M1 vs Client胜率",
    "步骤4: 检查是否达到目标（胜率 >= 50%）",
    "步骤5: 优化参数和代码（如果未达标）"
]

current_step = status.get('step', 'unknown') if status_file.exists() else 'unknown'
for i, step in enumerate(steps, 0):
    marker = ">>> " if (current_step == 'game_generation' and i == 0) or \
                      (current_step == 'training' and i == 1) or \
                      (current_step == 'evaluation' and i == 3) else "    "
    print(f"{marker}{step}")

# 3. 迭代历史
history_file = Path("models/m1_training_workflow_history.json")
if history_file.exists():
    with open(history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    history = data.get('workflow_history', [])
    print(f"\n3. 迭代历史:")
    print(f"   已完成迭代: {len(history)}次")
    
    if history:
        print(f"\n   最近3次迭代:")
        for item in history[-3:]:
            print(f"     迭代{item.get('iteration')}: 胜率={item.get('win_rate', 0):.2%}, "
                  f"状态={item.get('status', 'unknown')}, "
                  f"时间={item.get('timestamp', '')[:19]}")

# 4. 最新训练记录
training_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_file.exists():
    with open(training_file, 'r', encoding='utf-8') as f:
        training_history = json.load(f)
    
    if isinstance(training_history, list) and len(training_history) > 0:
        latest = training_history[-1]
        print(f"\n4. 最新训练记录:")
        print(f"   Epoch: {latest.get('epoch')}")
        print(f"   总损失: {latest.get('total_loss', 0):,.2f}")
        print(f"   预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}/512")
        print(f"   真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"   预测比例: {latest.get('prediction_ratio', 0):.2f}x")
        print(f"   学习率: {latest.get('learning_rate', 0):.6f}")

# 5. 当前问题
if status_file.exists() and status.get('status') == 'error':
    print(f"\n5. 当前问题:")
    error = status.get('error', '未知错误')
    print(f"   错误: {error}")
    
    if 'game_generation' in status.get('step', ''):
        print(f"\n   问题分析:")
        print(f"   - 游戏对战生成步骤卡住")
        print(f"   - 可能原因：batch_executor卡住、服务器无响应、客户端连接失败")
        print(f"\n   建议:")
        print(f"   - 检查服务器和客户端进程")
        print(f"   - 手动清理残留进程后重新启动")
        print(f"   - 或等待工作流自动重试")

print("\n" + "="*60)
print("提示:")
print("  - 运行 'python monitor_workflow_progress.py' 查看实时进度")
print("  - 运行 'python scripts/checks/check_workflow_status.py' 查看详细状态")
print("  - 如果工作流卡住，可以手动重启")
print("="*60)
