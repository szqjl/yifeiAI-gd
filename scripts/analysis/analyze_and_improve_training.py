"""分析训练结果并自动改进训练代码，然后重启工作流"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

print("="*60)
print("训练结果分析与自动改进系统")
print("="*60)

# 1. 检查工作流状态
print("\n1. 检查工作流状态...")
status_file = Path("models/m1_workflow_status.json")
if status_file.exists():
    with open(status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    print(f"  状态: {status.get('status')}")
    print(f"  迭代: {status.get('current_iteration', 0)}/{status.get('max_iterations', 10)}")
    print(f"  成功: {'是' if status.get('success') else '否'}")
else:
    print("  工作流状态文件不存在")

# 2. 分析训练结果
print("\n2. 分析训练结果...")
training_file = Path("models/bc_model_stage7_optimized_training_history.json")
if not training_file.exists():
    print("  错误：训练历史文件不存在")
    sys.exit(1)

with open(training_file, 'r', encoding='utf-8') as f:
    history = json.load(f)

if not isinstance(history, list) or len(history) == 0:
    print("  错误：训练历史为空")
    sys.exit(1)

latest = history[-1]
first = history[0] if len(history) > 1 else latest

print(f"  最新Epoch: {latest.get('epoch')}")
print(f"  总损失: {latest.get('total_loss', 0):,.2f}")
print(f"  预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}/512")
print(f"  真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
print(f"  预测比例: {latest.get('prediction_ratio', 0):.2f}x")

# 识别问题
issues = []
improvements = []

pred_cards = latest.get('avg_predicted_cards', 0)
pred_ratio = latest.get('prediction_ratio', 0)
loss = latest.get('total_loss', 0)
true_cards = latest.get('avg_true_cards', 0)

if pred_cards >= 512:
    issues.append("模型预测了所有512张卡牌，阈值设置无效")
    improvements.append("进一步降低阈值范围（0.0001-0.01）")
    
if pred_ratio > 10:
    issues.append(f"预测比例过高（{pred_ratio:.2f}倍）")
    improvements.append("增加过度预测惩罚系数（5000.0）")
    
if loss > 10000:
    issues.append(f"损失值仍然较高（{loss:,.2f}）")
    improvements.append("降低学习率（0.00001）")

if true_cards < 1:
    issues.append(f"真实卡牌数过少（{true_cards:.2f}）")
    improvements.append("检查数据加载器，确保过滤PASS动作")

print(f"\n  发现 {len(issues)} 个问题:")
for i, issue in enumerate(issues, 1):
    print(f"    {i}. {issue}")

print(f"\n  改进建议:")
for i, improvement in enumerate(improvements, 1):
    print(f"    {i}. {improvement}")

# 3. 自动改进训练代码
print("\n3. 根据分析结果自动改进训练代码...")
code_file = Path("src/train/stage7_optimized_training.py")
if not code_file.exists():
    print("  错误：找不到训练代码文件")
    sys.exit(1)

with open(code_file, 'r', encoding='utf-8') as f:
    code = f.read()

original_code = code
modified = False

# 改进1: 降低阈值范围
if pred_cards >= 512:
    print("  改进1: 进一步降低阈值范围...")
    # 查找阈值计算代码
    patterns = [
        (r"threshold = torch\.clamp\(base_threshold \* 0\.01, 0\.001, 0\.1\)", 
         "threshold = torch.clamp(base_threshold * 0.001, 0.0001, 0.01)"),
        (r"threshold = torch\.clamp\(base_threshold \* 0\.001, 0\.0001, 0\.01\)",
         "threshold = torch.clamp(base_threshold * 0.0001, 0.00001, 0.001)"),  # 进一步降低
    ]
    
    for old_pattern, new_threshold in patterns:
        if re.search(old_pattern, code):
            code = re.sub(old_pattern, new_threshold, code)
            modified = True
            print(f"    [OK] 已将阈值范围进一步缩小")
            break

# 改进2: 增加过度预测惩罚
if pred_ratio > 10:
    print("  改进2: 增加过度预测惩罚系数...")
    # 查找惩罚参数
    penalty_patterns = [
        (r"over_prediction_penalty=288325\.1953125", "over_prediction_penalty=10000.0"),
        (r"over_prediction_penalty=5000\.0", "over_prediction_penalty=10000.0"),
        (r"over_prediction_penalty=1000\.0", "over_prediction_penalty=5000.0"),
    ]
    
    for old_pattern, new_penalty in penalty_patterns:
        if re.search(old_pattern, code):
            code = re.sub(old_pattern, new_penalty, code)
            modified = True
            print(f"    [OK] 已将过度预测惩罚更新为更高值")
            break

# 改进3: 降低学习率
if loss > 10000:
    print("  改进3: 降低学习率...")
    lr_patterns = [
        (r"learning_rate: float = 0\.00005", "learning_rate: float = 0.00001"),
        (r"learning_rate: float = 0\.00001", "learning_rate: float = 0.000005"),  # 进一步降低
    ]
    
    for old_pattern, new_lr in lr_patterns:
        if re.search(old_pattern, code):
            code = re.sub(old_pattern, new_lr, code)
            modified = True
            print(f"    [OK] 已将学习率进一步降低")
            break

# 改进4: 调整alpha和gamma
if pred_ratio > 10:
    print("  改进4: 调整损失函数alpha和gamma...")
    # 降低alpha，增加gamma
    alpha_patterns = [
        (r"alpha=4\.336808689942018", "alpha=0.05"),
        (r"alpha=0\.1", "alpha=0.05"),
    ]
    
    for old_pattern, new_alpha in alpha_patterns:
        if re.search(old_pattern, code):
            code = re.sub(old_pattern, new_alpha, code)
            modified = True
            print(f"    [OK] 已将alpha降低到0.05")
            break
    
    gamma_patterns = [
        (r"gamma=5\.0", "gamma=6.0"),
        (r"gamma=3\.0", "gamma=5.0"),
    ]
    
    for old_pattern, new_gamma in gamma_patterns:
        if re.search(old_pattern, code):
            code = re.sub(old_pattern, new_gamma, code)
            modified = True
            print(f"    [OK] 已将gamma增加到更高值")
            break

if modified:
    # 备份原文件
    backup_file = code_file.with_suffix('.py.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(original_code)
    print(f"  [OK] 已备份原文件到: {backup_file.name}")
    
    # 保存修改后的代码
    with open(code_file, 'w', encoding='utf-8') as f:
        f.write(code)
    print("  [OK] 训练代码已更新")
else:
    print("  [警告] 未找到需要修改的代码，可能需要手动调整")

# 4. 重启工作流
print("\n4. 重启工作流...")
cmd = [
    sys.executable,
    "src/train/m1_training_workflow.py",
    "--max_iterations", "10",
    "--target_win_rate", "0.50",
    "--min_games", "50",
    "--server_path", r"D:\GDAI\server\windows\guandan_offline_v1006.exe"
]

print(f"  执行命令: {' '.join(cmd)}")
print("  工作流将在后台运行...")

# 在后台启动工作流
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8',
    errors='replace'
)

print(f"  [OK] 工作流进程已启动，PID: {process.pid}")
print("\n提示：")
print("  - 运行 'python monitor_workflow_progress.py' 可查看实时进度")
print("  - 运行 'python scripts/checks/check_workflow_status.py' 可查看工作流状态")
print("  - 运行 'python auto_restart_workflow.py' 可启动自动重启系统")

print("\n" + "="*60)
print("分析、改进和重启完成")
print("="*60)
